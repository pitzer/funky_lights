import asyncio
from functools import reduce
import numpy as np
from operator import add
import websockets


class TextureWebSocketsServer:
    def __init__(self, pattern_generator):
        self.pattern_generator = pattern_generator
        self.TEXTURE_WIDTH = 128
        self.TEXTURE_HEIGHT = 128
        self.TEXTURE_SIZE = self.TEXTURE_WIDTH * self.TEXTURE_HEIGHT * 4

    async def PrepareTextureMsg(self, segments):
        out = np.zeros(self.TEXTURE_SIZE, dtype=np.uint8)
        r = np.concatenate([segment.colors[:, 0] for segment in segments], axis=None)
        g = np.concatenate([segment.colors[:, 1] for segment in segments], axis=None)
        b = np.concatenate([segment.colors[:, 2] for segment in segments], axis=None)
        color_bytes = reduce(add, [segment.num_leds for segment in segments]) * 4
        out[:color_bytes:4] = r
        out[1:color_bytes:4] = g
        out[2:color_bytes:4] = b
        return bytearray(out)

    async def serve(self, websocket, path):
        while True:
            segments = await asyncio.shield(self.pattern_generator.result)
            try:
                await websocket.send(await self.PrepareTextureMsg(segments))
            except websockets.ConnectionClosed as exc:
                break
