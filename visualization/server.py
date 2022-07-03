import crc8
import json
import serial
import time
import sys
import asyncio
import websockets
import functools
import time

MAGIC = 0x55
CMD_LEDS = 1
WEB_SOCKET_PORT = 5678

def UInt16ToBytes(val):
    bytes = val.to_bytes(2, byteorder='little', signed=False)
    return [bytes[0], bytes[1]]

def RgbToBits(rgbs):
    """ Convert RGB value given as a 3-tuple to a list of two bytes that can
        be sent to the LEDs. We pack data as 16 bits:
            RRRRRGGGGGGBBBBB
    Args:
    rgbs: list of rgb tuples
    Returns:
    a list of bytes
    """
    out = []
    for rgb in rgbs:
        r, g, b = rgb
        out += [((g << 3) & 0xE0) | ((b >> 3) & 0x1F), (r & 0xF8) | ((g >> 5) & 0x07)]
    return out

def PrepareLedMsg(bar_uid, rgbs):
    """ Prepare a message from a list of RGB colors
    Args:
    serial: Serial port object. Should be already initialized
    bar_uid: UID of the bar to which we want to send the message
    rgbs: list of rgb tuples
    Returns:
    a bytearray, ready to send on the serial port
    """
    header = [MAGIC, bar_uid, len(rgbs), CMD_LEDS]
    data = RgbToBits(rgbs)
    crc_compute = crc8.crc8()
    crc_compute.update(bytearray(data))
    crc = [crc_compute.digest()[0]]
    msg = header + data + crc
    return bytearray(msg)

def PrepareLedSegmentsMsg(segments):
    header = [MAGIC, len(segments)]
    data = []
    for segment in segments:
        data += [segment.uid]
        data += UInt16ToBytes(len(segment.colors)) 
        data += [CMD_LEDS]
        data += RgbToBits(segment.colors)
    crc_compute = crc8.crc8()
    crc_compute.update(bytearray(data))
    crc = [crc_compute.digest()[0]]
    msg = header + data + crc
    return bytearray(msg)

async def ws_serve(websocket, generator):
    while True:
        pattern = await asyncio.shield(generator.pattern)
        try:
            await websocket.send(pattern)
        except websockets.ConnectionClosed as exc:
            break

class Segment:
    def __init__(self, uid, num_leds):
        self.uid = uid
        self.num_leds = num_leds
        self.colors = [(255, 0, 0) for i in range(num_leds)]

class PatternGenerator:
    def __init__(self, led_config):
        self.pattern = asyncio.Future()
        self.led_config = led_config
        self.segments = []
        PATTERN_SIZE = 30
        for s in led_config['led_segments']:
            segment = Segment(s['uid'], s['num_leds'])
            for i in range(int(PATTERN_SIZE / 2)):
                col = int(i / int(PATTERN_SIZE / 2) * 255)
                segment.colors[i] = (col, 255 - col, 0)
            for i in range(int(PATTERN_SIZE / 2), PATTERN_SIZE):
                col = int(255 - ((i - int(PATTERN_SIZE / 2))/ int(PATTERN_SIZE / 2) * 255))
                segment.colors[i] = (col, 255 - col, 0)
            for i in range(PATTERN_SIZE, segment.num_leds):
                col = 0
                segment.colors[i] = (col, 255 - col, 0)
            self.segments.append(segment)

    async def tick(self, delta):
        for segment in self.segments:
            segment.colors = segment.colors[1:] + segment.colors[:1]

    async def run(self):
        while True:
            await self.tick(1.0)
            self.pattern.set_result(PrepareLedSegmentsMsg(self.segments))
            self.pattern = asyncio.Future()
            await asyncio.sleep(0.1)


async def main():
    # led_config_file = './visualization/led_config.json'
    led_config_file = 'led_config.json'
    if len(sys.argv) > 1:
        led_config_file = int(sys.argv[1])
    with open(led_config_file, 'r') as f:
        led_config = json.load(f)

    # Start pattern generator
    pattern_generator = PatternGenerator(led_config)
    asyncio.create_task(pattern_generator.run())

    # Start WS server
    ws_serve_handler = functools.partial(ws_serve, generator=pattern_generator)
    await websockets.serve(ws_serve_handler, '127.0.0.1', WEB_SOCKET_PORT)

    # Wait forever
    await asyncio.Event().wait()


asyncio.run(main())