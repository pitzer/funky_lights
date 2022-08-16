from patterns.pattern import Pattern
import numpy as np
import random


class SparklePattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.color = np.array([255, 255, 255], dtype=np.uint8)
        self.params.background_color = np.array([0, 0, 0], dtype=np.uint8)
        self.params.sparkle_probability = 0.001
        self.params.decay_param = 0.95

    def initialize(self):
        self.pattern_segments = []
        for segment in self.segments:
            pattern_segment = SparklePatternSegment(segment, self.params)
            pattern_segment.initialize()
            self.pattern_segments.append(pattern_segment)

    async def animate(self, delta):
        for pattern_segment in self.pattern_segments:
            await pattern_segment.animate(delta)


class SparklePatternSegment(Pattern):
    def __init__(self, segment, params):
        self.segment = segment
        self.params = params

    def initialize(self):
        np.copyto(self.segment.colors, np.array(
            [self.params.background_color for i in range(self.segment.num_leds)]))

    async def animate(self, delta):
        for i in range(self.segment.num_leds):
             # Decay all LEDs
            self.segment.colors[i] = self.params.decay_param * self.segment.colors[i] + \
                    (1 - self.params.decay_param) * self.params.background_color
            # Sparkle random lights
            if random.random() <= self.params.sparkle_probability:
                self.segment.colors[i] = self.params.color