from sqlalchemy import between
from patterns.pattern import Pattern
import cv2 
import numpy as np
import sys
import matplotlib.pyplot as plt

class Rect():
    def __init__(self, u, v, width, height):
        self.u = u
        self.v = v
        self.width = width
        self.height = height

class VideoPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.file = ''
        self.crop = None
        self.fps = 20

    def initialize(self):
        self.video = cv2.VideoCapture(self.file)
        self.video_width  = self.video.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.video_height = self.video.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.current_frame = 0
        self.prev_delta = 0

        if self.crop is None:
            self.crop = Rect(0, 0, self.video_width, self.video_height)
        max_x = max_y = max_z = sys.float_info.min
        min_x = min_y = min_z = sys.float_info.max
        for segment in self.segments:
            for p in segment.led_positions:
                max_x = max(max_x, p[0])
                min_x = min(min_x, p[0])
                max_y = max(max_y, p[1])
                min_y = min(min_y, p[1])
                max_z = max(max_z, p[2])
                min_z = min(min_z, p[2])

        offset = np.array([-min_y, -min_z])
        scale = np.array([(self.crop.height - 1) / (max_y - min_y), (self.crop.width - 1) / (max_z - min_z)]) 
        for segment in self.segments:
            uv = []
            for p in segment.led_positions:
                pm = np.multiply(p[1:] + offset, scale).astype(int)
                u = int(self.crop.height) - 1 - pm[0] + self.crop.u
                v = pm[1] + self.crop.v
                def clamp(minimum, x, maximum):
                    return max(minimum, min(x, maximum))
                u = clamp(0, u, self.video_height)
                v = clamp(0, v, self.video_width)
                uv.append(np.array([u, v]))
            segment.uv = np.array(uv)
    
    def animate(self, delta):
        delta = delta + self.prev_delta
        frame_delta = int(self.fps * delta)
        self.prev_delta = delta - frame_delta / (self.fps)
        if frame_delta <= 0:
            return

        self.current_frame = self.current_frame + frame_delta
        self.video.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret,frame = self.video.read() 
        if ret == False:
            print('rewinding')
            self.video.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.current_frame = 0
            return
            
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        for segment in self.segments:  
            i = 0
            for color in segment.colors:
                np.copyto(color, frame[segment.uv[i][0], segment.uv[i][1]])
                i = i + 1