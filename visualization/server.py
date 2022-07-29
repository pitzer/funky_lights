import json
import time
import sys
import asyncio
import serial_asyncio
import websockets
import functools
import time

from funky_lights import connection, messages
from patterns.rg_transition_pattern import RGTRansitionPattern
from patterns.video_pattern import VideoPattern, Rect

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
    def __init__(self, generator, bus):
        super().__init__()
        self.transport = None
        self.generator = generator
        self.bus = bus

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
        while True:
            segments = await asyncio.shield(self.generator.result)
            for segment in segments:
                if segment.bus == self.bus:
                    self.transport.serial.write(
                        messages.PrepareLedMsg(segment.uid, segment.colors))

class PatternGenerator:
    def __init__(self, led_config):
        self.result = asyncio.Future()
        config = [
            (VideoPattern, dict(file='media/butter_churn.mp4',
             fps=20, crop=Rect(60, 60, 60, 60))),
            (VideoPattern, dict(file='media/psychill1.mp4',
             fps=20, crop=Rect(60, 130, 60, 60))),
            (VideoPattern, dict(file='media/psychill2.mp4',
             fps=20, crop=Rect(60, 130, 60, 60))),
            (RGTRansitionPattern, dict()),
            (VideoPattern, dict(file='media/milkdrop.mp4',
             fps=20, crop=Rect(60, 130, 60, 60)))
        ]

        self.patterns = []
        self.current_pattern_index = 0
        for cls, params in config:
            pattern = cls()
            for key in params:
                setattr(pattern, key, params[key])
            pattern.prepareSegments(led_config)
            pattern.initialize()
            self.patterns.append(pattern)

    async def tick(self, pattern, delta):
        pattern.animate(delta)

    async def run(self):
        ANIMATION_RATE = 20
        FPS_UPDATE_RATE = 1
        PATTERN_DURATION = 10

        prev_animation_time = time.time() - 1.0 / ANIMATION_RATE
        prev_pattern_time = time.time()
        start_time = time.time()
        counter = 0
        while True:
            cur_animation_time = time.time()

            # Rotate patterns
            if (cur_animation_time - prev_pattern_time) > PATTERN_DURATION:
                self.current_pattern_index = (
                    self.current_pattern_index + 1) % len(self.patterns)
                prev_pattern_time = cur_animation_time
            pattern = self.patterns[self.current_pattern_index]

            # Process animation
            await self.tick(pattern, cur_animation_time - prev_animation_time)

            # Update future for processing by IO
            self.result.set_result(pattern.segments)
            self.result = asyncio.Future()
            prev_animation_time = cur_animation_time

            # Sleep for the remaining time
            processing_time = time.time() - cur_animation_time
            await asyncio.sleep(max(0, 1.0/ANIMATION_RATE - processing_time))

            # Output update rate to console
            counter += 1
            if (time.time() - start_time) > 1.0 / FPS_UPDATE_RATE:
                print("Animation FPS: ", counter / (time.time() - start_time))
                counter = 0
                start_time = time.time()


async def main():
    # led_config_file = './visualization/led_config.json'
    led_config_file = 'led_config.json'
    if len(sys.argv) > 1:
        led_config_file = sys.argv[1]
    bus_config_file = 'bus_config.json'
    if len(sys.argv) > 2:
        bus_config_file = sys.argv[2]

    with open(led_config_file, 'r') as f:
        led_config = json.load(f)
    with open(bus_config_file, 'r') as f:
        bus_config = json.load(f)
        
    # Start pattern generator
    pattern_generator = PatternGenerator(led_config)
    asyncio.create_task(pattern_generator.run())

    # Start WS server
    ws_serve_handler = functools.partial(ws_serve, generator=pattern_generator)
    await websockets.serve(ws_serve_handler, '127.0.0.1', WEB_SOCKET_PORT)

    # Start serial
    loop = asyncio.get_event_loop()
    for bus in bus_config['led_busses']:
        # Start the light app
        serial_port = connection.InitializeController(bus['device'], baudrate=bus['baudrate'])
        serial_port.close()

        # Start async serial handlers
        serial_serve_handler = functools.partial(
            SerialWriter, generator=pattern_generator, bus=bus['name'])
        await serial_asyncio.create_serial_connection(
            loop, serial_serve_handler, bus['device'], baudrate=bus['baudrate'])
    
    # Wait forever
    await asyncio.Event().wait()


asyncio.run(main())
