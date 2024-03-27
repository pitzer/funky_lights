import asyncio
import base64
from functools import reduce
import json
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
            led_segments = await asyncio.shield(self.pattern_generator.result)
            object_materials = []
            for object_id, segments in led_segments.items():
                object_material = {}
                object_material['object_id'] = object_id
                texture_bytes = await self.PrepareTextureMsg(segments)
                encoded_data = base64.b64encode(texture_bytes)
                object_material['texture_data'] = encoded_data.decode("utf-8")
                
                object_materials.append(object_material)

            try:
                await websocket.send(json.dumps(object_materials))
            except websockets.ConnectionClosed as exc:
                break


class PatternMixWebSocketsServer:
    def __init__(self, pattern_generator):
        self.pattern_generator = pattern_generator

    async def serve(self, websocket, path):
        while True:
            pattern_mix = await asyncio.shield(self.pattern_generator.pattern_mix)
            try:
                await websocket.send(json.dumps(pattern_mix))
            except websockets.ConnectionClosed as exc:
                break
