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
        # Decay every LED at once. The sparkle draws stay a per-LED loop on
        # purpose: they consume the stdlib random stream one call per LED, so
        # replacing them with np.random would change the sequence. The cost was
        # in the numpy scalar arithmetic above, not in random().
        n = self.segment.num_leds
        self.segment.colors[:] = (
            self.params.decay_param * self.segment.colors
            + (1 - self.params.decay_param) * self.params.background_color)
        hits = np.fromiter(
            (random.random() <= self.params.sparkle_probability for _ in range(n)),
            dtype=bool, count=n)
        self.segment.colors[hits] = self.params.color