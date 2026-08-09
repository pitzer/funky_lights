from patterns.pattern import PatternUV
from core.async_utils import run_in_executor
import cv2
import numpy as np


class Rect():
    def __init__(self, u, v, width, height):
        self.u = u
        self.v = v
        self.width = width
        self.height = height


class VideoPattern(PatternUV):
    def __init__(self):
        super().__init__()
        self.params.file = ''
        self.params.crop = None
        self.params.fps = None

    def initialize(self):
        self.video = cv2.VideoCapture(self.params.file)
        video_width = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
        video_height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.current_frame = 0
        self.prev_delta = 0

        if self.params.crop:
            if self.params.crop.u + self.params.crop.height > video_height:
                raise ValueError('Crop window out of bounds (height)')

            if self.params.crop.v + self.params.crop.width > video_width:
                raise ValueError('Crop window out of bounds (width)')

            width = self.params.crop.width
            height = self.params.crop.height
            offset_u = self.params.crop.u
            offset_v = self.params.crop.v
        else:
            width = video_width
            height = video_height
            offset_u = 0
            offset_v = 0

        self.generateUVCoordinates(width, height, offset_u, offset_v)

    @run_in_executor
    def _decode_frame(self, delta):
        """Decode one frame. Runs on a worker thread, not the event loop.

        Every OpenCV call in here blocks -- seeking in particular, which has to
        decode forward from a keyframe. Left on the event loop it stalls frame
        generation and every OPC write with it. cv2 releases the GIL, so this is
        real parallelism rather than just deferral.

        Returns an RGB frame, or None if there is nothing new to show.
        """
        # Slow down or speed up frame processing if fps is set
        if self.params.fps:
            delta = delta + self.prev_delta
            frame_delta = int(self.params.fps * delta)
            self.prev_delta = delta - frame_delta / (self.params.fps)
            if frame_delta <= 0:
                return None
            self.current_frame = self.current_frame + frame_delta
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        else:
            self.current_frame += 1

        ret, frame = self.video.read()
        if ret == False:
            # End of file: rewind and skip a frame rather than showing stale
            # pixels. The next tick starts from the beginning.
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            return None

        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    async def animate(self, delta):
        frame = await self._decode_frame(delta)
        if frame is None:
            return

        # Gather every LED's pixel in one vectorised lookup. This was a Python
        # loop with an np.copyto per LED -- 1443 iterations per frame on
        # Funklet, which cost more than the decode did.
        for segment in self.getSegments():
            uv = segment.uv
            # colors[:] rather than colors = ... so the array identity survives;
            # PatternMix and the OPC writers hold references to it.
            segment.colors[:] = frame[uv[:, 0], uv[:, 1]]
