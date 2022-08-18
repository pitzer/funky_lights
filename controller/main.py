import argparse
import json
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
from patterns import pattern_config


WEB_SOCKET_PORT = 5678
TEXTURE_WIDTH = 128
TEXTURE_HEIGHT = 128
TEXTURE_SIZE = TEXTURE_WIDTH * TEXTURE_HEIGHT * 4


def PrepareTextureMsg(segments):
    msg = []
    texture_size = TEXTURE_SIZE
    for segment in segments:
        for color in segment.colors:
            msg += [color[0], color[1], color[2], 255]
    # Added padding to the end of the buffer to fill the full texture
    msg += [0] * (texture_size - len(msg))
    return bytearray(msg)


async def ws_serve(websocket, generator):
    while True:
        segments = await asyncio.shield(generator.result)
        try:
            await websocket.send(PrepareTextureMsg(segments))
        except websockets.ConnectionClosed as exc:
            break


class SerialWriter(asyncio.Protocol):
    def __init__(self, generator, uids):
        super().__init__()
        self.transport = None
        self.generator = generator
        self.uids = uids

    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        print('Writer connection created')
        asyncio.ensure_future(self.serve())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')

    async def serve(self):
        start_time = time.time()
        counter = 0
        while True:
            segments = await asyncio.shield(self.generator.result)
            for segment in segments:
                if segment.uid in self.uids:
                    self.transport.serial.write(
                        messages.PrepareLedMsg(segment.uid, segment.colors))
            # Output update rate to console
            counter += 1
            if (time.time() - start_time) > 1.0:
                print("Serial FPS: %.1f" %
                      (counter / (time.time() - start_time)))
                counter = 0
                start_time = time.time()


class PatternGenerator:
    def __init__(self, patter_selector, color_selector=None):
        self.patter_selector = patter_selector
        self.color_selector = color_selector
        self.result = asyncio.Future()

        self._ANIMATION_RATE = 20
        self._FPS_UPDATE_RATE = 1

    async def tick(self, pattern, delta):
        await pattern.animate(delta)

    async def run(self):
        await self.patter_selector.initializePatterns()
        prev_animation_time = time.time() - 1.0 / self._ANIMATION_RATE
        start_time = time.time()
        counter = 0
        while True:
            cur_animation_time = time.time()
            pattern = self.patter_selector.update(cur_animation_time)

            # Process animation
            await self.tick(pattern, cur_animation_time - prev_animation_time)

            # Update future for processing by IO
            self.result.set_result(pattern.segments)
            self.result = asyncio.Future()
            prev_animation_time = cur_animation_time

            # Sleep for the remaining time
            processing_time = time.time() - cur_animation_time
            await asyncio.sleep(max(0, 1.0/self._ANIMATION_RATE - processing_time))

            # Output update rate to console
            counter += 1
            if (time.time() - start_time) > 1.0 / self._FPS_UPDATE_RATE:
                print("Animation FPS: %.1f" % (counter / (time.time() - start_time)))
                counter = 0
                start_time = time.time()


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--led_config", type=argparse.FileType('r'),
                        default="../config/led_config.json", help="LED config file")
    parser.add_argument("-b", "--bus_config", type=argparse.FileType('r'),
                        default="../config/bus_config.json", help="Bus config file")
    parser.add_argument("-c", "--enable_cache", action='store_true', help="Enable pattern caching")
    parser.add_argument("-a", "--animation_rate", type=int, default=20, help="The target animation rate in Hz")
    parser.add_argument("-d", "--dmx_config", type=argparse.FileType('r'),
                        default="../config/dmx_config_enttec.json", help="DMX config file")
    
    args = parser.parse_args()

    led_config = json.load(args.led_config)
    bus_config = json.load(args.bus_config)
    dmx_config = json.load(args.dmx_config)

    futures = []

<<<<<<< HEAD
    
    pattern_selector = PatternSelector(pattern_config.DEFAULT_CONFIG, led_config)
<<<<<<< HEAD
    futures.append(pattern_selector.launchpadListener())
=======
    # Launchpad handler
=======
    # Pattern selector
    pattern_selector = PatternSelector(pattern_config.DEFAULT_CONFIG, led_config, dmx_config, args)
>>>>>>> cdad1ed (dmx config file)
    futures.append(pattern_selector.launchpadListener())
    #DMX handler
    futures.append(pattern_selector.dmxListener())
>>>>>>> 946076f (Move dmx controller to its own subroutine)

    # Start pattern generator
    pattern_generator = PatternGenerator(pattern_selector)
    futures.append(pattern_generator.run())
    
    # Start WS server
    ws_serve_handler = functools.partial(ws_serve, generator=pattern_generator)
    futures.append(websockets.serve(ws_serve_handler, '0.0.0.0', WEB_SOCKET_PORT))

    # Start serial
    loop = asyncio.get_event_loop()
    for bus in bus_config['led_busses']:
        # Start the light app
        serial_port = connection.InitializeController(bus['device'], baudrate=bus['baudrate'])
        serial_port.close()

        # Start async serial handlers
        serial_serve_handler = functools.partial(
            SerialWriter, generator=pattern_generator, uids=bus['uids'])
        futures.append(serial_asyncio.create_serial_connection(
            loop, serial_serve_handler, bus['device'], baudrate=bus['baudrate']))
    
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
