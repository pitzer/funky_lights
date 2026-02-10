from patterns.pattern import PatternUV
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
        self.params.color = None
        self.params.horizontal_blur = None

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

    async def animate(self, delta):
        # Slow down or speed up frame processing if fps is set
        if self.params.fps:
            delta = delta + self.prev_delta
            frame_delta = int(self.params.fps * delta)
            self.prev_delta = delta - frame_delta / (self.params.fps)
            if frame_delta <= 0:
                return
            self.current_frame = self.current_frame + frame_delta
            self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        else:
            self.current_frame += 1

        ret, frame = self.video.read()
        if ret == False:
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            return

        # Optional horizontal blur to make patterns more visible when sampled at low resolution
        if self.params.horizontal_blur:
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.params.horizontal_blur, 1))
            frame = cv2.dilate(frame, horizontal_kernel)

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # If we were given a color, replace all the pixels with that color but keep the brightness from the video
        if self.params.color:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            normalized = gray / 255.0
            frame = np.zeros_like(frame)
            for i in range(3):
                frame[:, :, i] = np.clip(normalized * self.params.color[i], 0, 255)


        for segment in self.getSegments():
            for i, color in enumerate(segment.colors):
                np.copyto(color, frame[segment.uv[i][0], segment.uv[i][1]])
