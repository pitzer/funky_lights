import argparse
import json
import logging
import time
import sys
import asyncio
import serial_asyncio
import websockets
import functools
import time
import traceback

from funky_lights import connection, messages
from core.pattern_selector import PatternSelector
from core.opc import connect_to_opc
from core.websockets import TextureWebSocketsServer, PatternMixWebSocketsServer
from patterns import pattern_config

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(asctime)s,%(msecs)d %(filename)s(%(lineno)d) %(funcName)s: %(message)s",
    datefmt="%H:%M:%S",
)


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
        print('Writer connection created')
        asyncio.ensure_future(self.serve())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')


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
        last_init_time = time.time() - 2.0
        while True:
            # Initialize lights every second (should only affect lights that are in bootloader mode)
            if (time.time() - last_init_time) > 1.0:
                await self.initialize_lights()
                last_init_time = time.time()

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
        cur_animation_time = time.time()
        next_animation_time = cur_animation_time + animation_time_delta
        prev_log_time = cur_animation_time
        log_counter = 0

        while True:
            cur_animation_time = next_animation_time
            next_animation_time = cur_animation_time + animation_time_delta

            # Skip a frame if falling too far behind
            if time.time() > next_animation_time:
                print("Falling behind. Skipping frame.")
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

            # Output update rate to console
            log_counter += 1
            cur_log_time = time.time()
            log_time_delta = cur_log_time - prev_log_time
            if log_time_delta > 1.0 / self._LOG_RATE:
                print("Animation FPS: %.1f" % (log_counter / log_time_delta))
                log_counter = 0
                prev_log_time = cur_log_time

            # Sleep for the remaining time
            await asyncio.sleep(max(0, next_animation_time - time.time()))



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

    args = parser.parse_args()

    led_config = json.load(args.led_config)
    bus_config = json.load(args.bus_config)
    dmx_config = json.load(args.dmx_config)

    futures = []

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
                server_port=opc['server_port']))
    
    # Wait forever
    try:
        results = await asyncio.gather(
            *futures,
            return_exceptions=False
        )
        print(results)
    except Exception as e:
        print('An exception has occured.')
        print(traceback.format_exc())


asyncio.run(main())
