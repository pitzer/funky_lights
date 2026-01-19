from patterns.pattern import Pattern
from patterns.pattern import PatternUV, UVGrid
from collections import namedtuple
import math
import numpy as np


ZoneSegment = namedtuple(
    'ZoneSegment', ['name', 'segment_index', 'offset', 'num_leds'])

POST_RL_SEGMENT = 0
POST_RR_SEGMENT = 1
POST_FL_SEGMENT = 2
POST_FR_SEGMENT = 3
HEADBOARD_SEGMENT = 4

headboard_segments = [
    ZoneSegment("Top left", HEADBOARD_SEGMENT, 0, 10),
    ZoneSegment("Cross Top Left", HEADBOARD_SEGMENT, 10, 8),
    ZoneSegment("Top Middle", HEADBOARD_SEGMENT, 18, 8),
    ZoneSegment("Cross Top Right", HEADBOARD_SEGMENT, 26, 8),
    ZoneSegment("Top Right", HEADBOARD_SEGMENT, 34, 10),
    ZoneSegment("Right", HEADBOARD_SEGMENT, 44, 14),
    ZoneSegment("Bottom Right", HEADBOARD_SEGMENT, 58, 10),
    ZoneSegment("Cross Bottom Right", HEADBOARD_SEGMENT, 68, 8),
    ZoneSegment("Bottom Middle", HEADBOARD_SEGMENT, 76, 8),
    ZoneSegment("Cross Bottom Left", HEADBOARD_SEGMENT, 84, 8),
    ZoneSegment("Bottom left", HEADBOARD_SEGMENT, 92, 10),
    ZoneSegment("Left", HEADBOARD_SEGMENT, 102, 14)
]

cage_segments = [
    ZoneSegment("Cage RL Left", POST_RL_SEGMENT, 0, 12),
    ZoneSegment("Cage RL Right", POST_RL_SEGMENT, 12, 12),
    ZoneSegment("Cage RR Left", POST_RR_SEGMENT, 0, 12),
    ZoneSegment("Cage RR Right", POST_RR_SEGMENT, 12, 12),
    ZoneSegment("Cage FL Left", POST_FL_SEGMENT, 0, 12),
    ZoneSegment("Cage FL Right", POST_FL_SEGMENT, 12, 12),
    ZoneSegment("Cage FR Left", POST_FR_SEGMENT, 0, 12),
    ZoneSegment("Cage FR Right", POST_FR_SEGMENT, 12, 12)
]

front_segments = [
    ZoneSegment("Front FL Right", POST_FL_SEGMENT, 24, 21),
    ZoneSegment("Front FL Left", POST_FL_SEGMENT, 45, 21),
    ZoneSegment("Front FL Right", POST_FR_SEGMENT, 24, 21),
    ZoneSegment("Front FL Left", POST_FR_SEGMENT, 45, 21)
]

center_segments = [
    ZoneSegment("Center RL Right", POST_RL_SEGMENT, 24, 21),
    ZoneSegment("Center RL Left", POST_RL_SEGMENT, 45, 21),
    ZoneSegment("Center RL Right", POST_RR_SEGMENT, 24, 21),
    ZoneSegment("Center RL Left", POST_RR_SEGMENT, 45, 21),
    ZoneSegment("Center FL Right", POST_FL_SEGMENT, 66, 21),
    ZoneSegment("Center FL Left", POST_FL_SEGMENT, 87, 21),
    ZoneSegment("Center FR Right", POST_FR_SEGMENT, 66, 21),
    ZoneSegment("Center Fr Left", POST_FR_SEGMENT, 87, 21)
]

class StaticColorPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.headboard_color = (255, 0, 0)
        self.params.center_color = (0, 255, 0)
        self.params.front_color = (0, 0, 255)
        self.params.cage_color = (255, 0, 255)
        
    def initialize(self):
        # Headboard
        for s in headboard_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.headboard_color

        # Center
        for s in center_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.center_color
        
        # Front
        for s in front_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.front_color
        
        # Cage
        for s in cage_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.cage_color 


    async def animate(self, delta):
        return
    

class BreathingColorPattern(StaticColorPattern):
    def __init__(self):
        super().__init__()
        self.params.breath_period_s = 5.0
        self.params.breath_amplitude_percent = 0.1
        self.breath_time = 0

    def initialize(self):
        super().initialize()

    def clip(value, min_val, max_val):
        """Clips a value within a specified range."""
        return max(min_val, min(value, max_val))

    async def animate(self, delta):
        self.breath_time =  (self.breath_time + delta) % self.params.breath_period_s
        rad = self.breath_time * math.pi * 2 / self.params.breath_period_s
        brightness = math.sin(rad) * self.params.breath_amplitude_percent * 255

        # Headboard
        headboard_color = np.array(self.params.headboard_color)
        for s in headboard_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(headboard_color + brightness, 0, 255)

        # Center
        center_color = np.array(self.params.center_color)
        for s in center_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(center_color + brightness, 0, 255)
        
        # Front
        front_color = np.array(self.params.front_color)
        for s in front_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(front_color + brightness, 0, 255)
        
        # Cage
        cage_color = np.array(self.params.cage_color)
        for s in cage_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(cage_color + brightness, 0, 255)


class RipplePattern(PatternUV):
    def __init__(self, width=100, height=100):
        super().__init__()
        # Frequency of color change (in Hz)
        self.fps = 40
        self.offset = 0
        self.width = width
        self.height = height
    
    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.grid = UVGrid(self.width, self.height)
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.spectrum = np.arange(0, 1, 1/self.width)        
        self.applyGrid(self.grid)  
    
    async def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        self.spectrum = np.roll(self.spectrum, 1)  
        self.applyGrid(self.grid)
        self.cumulative_delta = 0