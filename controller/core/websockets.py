import asyncio
import websockets


class TextureWebSocketsServer:
    def __init__(self, pattern_generator):
        self.pattern_generator = pattern_generator
        self.TEXTURE_WIDTH = 128
        self.TEXTURE_HEIGHT = 128
        self.TEXTURE_SIZE = self.TEXTURE_WIDTH * self.TEXTURE_HEIGHT * 4

    async def PrepareTextureMsg(self, segments):
        msg = []
        texture_size = self.TEXTURE_SIZE
        for segment in segments:
            for color in segment.colors:
                msg += [color[0], color[1], color[2], 255]
        # Added padding to the end of the buffer to fill the full texture
        msg += [0] * (texture_size - len(msg))
        return bytearray(msg)

    async def serve(self, websocket, path):
        while True:
            segments = await asyncio.shield(self.pattern_generator.result)
            try:
                await websocket.send(await self.PrepareTextureMsg(segments))
            except websockets.ConnectionClosed as exc:
                break


class LaunchpadWebSocketsServer:
    def __init__(self, pattern_selector):
        self.pattern_selector = pattern_selector

    async def serve(self, websocket, path):
        while True:
            segments = await asyncio.shield(self.pattern_generator.result)
            try:
                await websocket.receive(await self.PrepareTextureMsg(segments))
            except websockets.ConnectionClosed as exc:
                break