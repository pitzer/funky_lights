import argparse
import json
import logging
import logging.handlers
import os
import queue
import time
import sys
import asyncio
import serial_asyncio
import websockets
import functools

from funky_lights import connection, messages
from core.pattern_selector import PatternSelector
from core.diagnostics import LoopStallDetector
from core.opc import connect_to_opc
from core.websockets import TextureWebSocketsServer, PatternMixWebSocketsServer
from patterns import pattern_config

LOG_FORMAT = "%(levelname)s %(asctime)s,%(msecs)03d %(filename)s(%(lineno)d) %(funcName)s: %(message)s"
LOG_DATE_FORMAT = "%H:%M:%S"


class NonBlockingStreamHandler(logging.StreamHandler):
    """Console handler that drops records rather than blocking.

    The controller is usually launched from an SSH terminal, so its stderr is a
    pty at the far end of a network link. A stalled tty makes an ordinary
    write() block. Losing a console line is fine; the file handler keeps the
    full record.
    """

    def emit(self, record):
        try:
            super().emit(record)
        except BlockingIOError:
            pass


class DroppingQueueHandler(logging.handlers.QueueHandler):
    """Hand records to the logging thread, dropping them if it falls behind.

    An unbounded queue would grow without limit while the disk is unavailable.
    A dropped log line is a far better outcome than a frozen sculpture.
    """

    def enqueue(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            pass


def setup_logging(log_file):
    """Log without ever blocking the event loop.

    Every handler runs on a background thread behind a queue. This matters more
    than it sounds: writing to the log file is a write to the SD card, and a
    card that stalls -- which this hardware does -- blocks the calling thread
    inside flush(). With the handler on the event loop that froze frame
    generation and every OPC connection for as long as the card took to answer,
    observed at over ten seconds. The loop now only ever enqueues.
    """
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    handlers = []

    console = NonBlockingStreamHandler()
    console.setFormatter(formatter)
    handlers.append(console)
    try:
        os.set_blocking(console.stream.fileno(), False)
    except (AttributeError, OSError, ValueError):
        # Not a real fd (pytest capture, a pipe we don't own). Nothing to do.
        pass

    if log_file:
        log_file = os.path.expanduser(log_file)
        os.makedirs(os.path.dirname(log_file) or '.', exist_ok=True)
        rotating = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=20 * 1024 * 1024, backupCount=5)
        rotating.setFormatter(formatter)
        handlers.append(rotating)

    # Bounded: a few seconds of records at the rate this logs. Past that the
    # disk is clearly not coming back quickly and dropping is the right call.
    record_queue = queue.Queue(maxsize=2000)
    root.addHandler(DroppingQueueHandler(record_queue))

    listener = logging.handlers.QueueListener(
        record_queue, *handlers, respect_handler_level=True)
    listener.daemon = True
    listener.start()
    return listener


class SerialWriter(asyncio.Protocol):
    def __init__(self, generator, uids, color_format):
        super().__init__()
        self.transport = None
        self.generator = generator
        self.uids = uids
        self.color_format = color_format

    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        asyncio.ensure_future(self.serve())
        logging.info('Serial writer connected and scheduled')

    def connection_lost(self, exc):
        logging.warning(f'Serial writer closed: {exc!r}')


    async def initialize_lights(self):
        serial = self.transport.serial
        current_baudrate = serial.baudrate
        await asyncio.sleep(0.05)
        # Start application
        serial.baudrate = connection.BOOTLOADER_BAUDRATE
        serial.write(messages.PrepareStartLedControllerMsg(messages.BROADCAST_UID))
        await asyncio.sleep(0.01)
        # Change application baudrate to current_baudrate
        serial.baudrate = connection.START_BAUDRATE
        prescaler = int(16000000 / current_baudrate)
        serial.write(messages.PrepareBaudrateMsg(messages.BROADCAST_UID, prescaler))
        await asyncio.sleep(0.01)
        # Return to normal operations
        serial.baudrate = current_baudrate
        

    async def serve(self):
        last_init_time = time.monotonic() - 2.0
        while True:
            # Initialize lights every second (should only affect lights that are in bootloader mode)
            if (time.monotonic() - last_init_time) > 1.0:
                await self.initialize_lights()
                last_init_time = time.monotonic()

            # Send color messages
            segments = await asyncio.shield(self.generator.result)
            for segment in segments:
                if segment.uid in self.uids:
                    self.transport.serial.write(
                        messages.PrepareLedMsg(segment.uid, segment.colors, self.color_format))


class PatternGenerator:
    def __init__(self, args, pattern_selector):
        self.args = args
        self.pattern_selector = pattern_selector
        self.result = asyncio.Future()

        if args.enable_pattern_mix_publisher:
            self.pattern_mix = asyncio.Future()

        self._LOG_RATE = 1.0

    async def tick(self, pattern, delta):
        await pattern.animate(delta)

    async def run(self):
        await self.pattern_selector.initializePatterns()
        animation_time_delta = 1.0 / self.args.animation_rate
        # The schedule must run on the monotonic clock, because that is what
        # asyncio.sleep() uses. Driving it from time.time() meant an NTP step
        # (a Pi has no RTC, and resyncs after every network reconnect) turned
        # the sleep below into a multi-second freeze on every LED.
        cur_animation_time = time.monotonic()
        next_animation_time = cur_animation_time + animation_time_delta
        prev_log_time = cur_animation_time
        log_counter = 0
        skipped_frames = 0

        while True:
            cur_animation_time = next_animation_time
            next_animation_time = cur_animation_time + animation_time_delta

            # Skip a frame if falling too far behind. Resync to the clock rather
            # than chasing a deadline that is already in the past, and always
            # yield so the IO tasks keep running while we recover. The old bare
            # `continue` skipped the only await in this loop, so recovery from a
            # stall of T seconds spun 20*T synchronous iterations, each one
            # printing to the terminal -- and a print to a stalled tty blocks.
            now = time.monotonic()
            if now > next_animation_time:
                skipped_frames += int(
                    (now - next_animation_time) / animation_time_delta) + 1
                next_animation_time = now + animation_time_delta
                await asyncio.sleep(0)
                continue

            # Update pattern selection
            pattern = self.pattern_selector.update(cur_animation_time)

            # Update results future for processing by IO
            if self.args.enable_pattern_mix_publisher:
                self.pattern_mix.set_result(self.pattern_selector.get_pattern_mix())
                self.pattern_mix = asyncio.Future()

            # Process animation
            await self.tick(pattern, animation_time_delta)

            # Update results future for processing by IO
            self.result.set_result(pattern.segments)
            self.result = asyncio.Future()

            # Output update rate to the log
            log_counter += 1
            cur_log_time = time.monotonic()
            log_time_delta = cur_log_time - prev_log_time
            if log_time_delta > 1.0 / self._LOG_RATE:
                logging.info("Animation FPS: %.1f", log_counter / log_time_delta)
                if skipped_frames:
                    # Rate limited: a stall must not turn into a logging storm.
                    logging.warning(
                        "Fell behind: skipped %d frame(s) over the last %.1fs",
                        skipped_frames, log_time_delta)
                    skipped_frames = 0
                log_counter = 0
                prev_log_time = cur_log_time

            # Sleep for the remaining time
            await asyncio.sleep(max(0, next_animation_time - time.monotonic()))



async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--led_config", type=argparse.FileType('r'), default="../config/led_config.json", 
                        help="LED config file")
    parser.add_argument("-b", "--bus_config", type=argparse.FileType('r'), default="../config/bus_config.json", 
                        help="Bus config file")
    parser.add_argument("-c", "--enable_cache", action='store_true', 
                        help="Enable pattern caching")
    parser.add_argument("-a", "--animation_rate", type=int, default=20, 
                        help="The target animation rate in Hz")
    parser.add_argument("--enable_dmx", action='store_true', 
                        help="Enables support for a DMX device")
    parser.add_argument("--dmx_config", type=argparse.FileType('r'), default="../config/dmx_config_enttec.json", 
                        help="DMX config file")
    parser.add_argument("--ws_port_texture", type=int, default=5678, 
                        help="The WebSockets port for the texture server")
    parser.add_argument("--enable_launchpad", action='store_true', 
                        help="Enables support for a USB launchpad device")
    parser.add_argument("--ws_port_launchpad", type=int, default=5679, 
                        help="The WebSockets port for the launchpad server")
    parser.add_argument("--pattern_rotation_time", type=int, default=600, 
                        help="The maximum duration a pattern is displayed before rotating to the next.")
    parser.add_argument("--enable_pattern_mix_publisher", action='store_true', 
                        help="Enables a WebSockets server to publish the pattern mix")
    parser.add_argument("--pattern_mix_publish_port", type=int, default=5680, 
                        help="The WebSockets port for the pattern mix publisher")
    parser.add_argument("--enable_pattern_mix_subscriber", action='store_true', 
                        help="Enables a WebSockets client to subscribe to a pattern mix")
    parser.add_argument("--pattern_mix_subscribe_uri", default='ws://funkypi.wlan:5680',
                        help="The WebSockets URI for the pattern mix subscriber")
    parser.add_argument("--log_file", default='~/funklet.log',
                        help="Rotating log file. Pass an empty string to disable.")
    parser.add_argument("--stall_threshold", type=float, default=1.0,
                        help="Log a stack dump if the event loop blocks for "
                             "longer than this, in seconds. 0 disables.")

    args = parser.parse_args()

    setup_logging(args.log_file)

    led_config = json.load(args.led_config)
    bus_config = json.load(args.bus_config)
    dmx_config = json.load(args.dmx_config)

    futures = []

    # Watchdog. Cheap -- a 0.1s heartbeat and a sleeping thread -- and it is
    # the only thing that can report a blocked event loop, since anything on
    # the loop is blocked too.
    if args.stall_threshold > 0:
        detector = LoopStallDetector(threshold=args.stall_threshold)
        detector.start()
        futures.append(detector.heartbeat())

    # Pattern selector
    pattern_selector = PatternSelector(pattern_config.DEFAULT_CONFIG, led_config, dmx_config, args)

    # Launchpad handler
    if args.enable_launchpad:
        futures.append(pattern_selector.launchpadListener())

    #DMX handler
    if args.enable_dmx:
        futures.append(pattern_selector.dmxListener())

    # Start pattern generator
    pattern_generator = PatternGenerator(args, pattern_selector)
    futures.append(pattern_generator.run())
    
    # WS servers for the web visualization
    ws_texture = TextureWebSocketsServer(pattern_generator)
    futures.append(websockets.serve(ws_texture.serve,
                   '0.0.0.0', args.ws_port_texture))
    futures.append(websockets.serve(pattern_selector.launchpadWSListener,
                   '0.0.0.0', args.ws_port_launchpad))

    # Publisher and subscriber for pattern mix
    if args.enable_pattern_mix_publisher:
        ws_pattern_mix_publish = PatternMixWebSocketsServer(pattern_generator) 
        futures.append(websockets.serve(ws_pattern_mix_publish.serve, '0.0.0.0', args.pattern_mix_publish_port))
    
    if args.enable_pattern_mix_subscriber:
        futures.append(pattern_selector.patternMixWSListener(args.pattern_mix_subscribe_uri))

    # Start serial
    loop = asyncio.get_event_loop()
    for bus in bus_config['led_busses']:
        if "device" in bus:
            # Start the light app
            serial_port = connection.InitializeController(bus['device'], baudrate=bus['baudrate'])
            serial_port.close()

            # Start async serial handlers
            serial_serve_handler = functools.partial(
                SerialWriter, 
                generator=pattern_generator, 
                uids=bus['uids'], 
                color_format=messages.ColorFormat[bus['color_format']])
            futures.append(serial_asyncio.create_serial_connection(
                loop, serial_serve_handler, bus['device'], baudrate=bus['baudrate']))

        if "opc" in bus:
            opc = bus["opc"]
            futures.append(connect_to_opc(
                generator=pattern_generator,
                uids=bus['uids'],
                server_ip=opc['server_ip'],
                server_port=opc['server_port'],
                swap_red_green=bus.get('swap_red_green', False),
                skip_leds=bus.get('skip_leds')))
    
    # Wait forever
    try:
        results = await asyncio.gather(
            *futures,
            return_exceptions=False
        )
        logging.info('All tasks finished: %s', results)
    except Exception:
        # Exit non-zero so supervisor restarts us (autorestart=true) instead of
        # leaving the sculpture dark. See deploy/funklet-supervisor.conf.
        logging.exception('The controller stopped due to an unhandled exception.')
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
