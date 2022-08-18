from patterns.pattern import Pattern
import numpy as np


class TheaterChasePattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.foreground_color = np.array([255, 0, 0], dtype=np.uint8)
        self.params.background_color = np.array([0, 0, 0], dtype=np.uint8)
        self.params.speed = 1.5
        self.params.step_size = 3

    def initialize(self):
        self.pattern_segments = []
        if hasattr(self.params, 'color'):
            self.params.foreground_color = self.params.color
        for segment in self.segments:
            pattern_segment = TheaterChasePatternSegment(segment, self.params)
            pattern_segment.initialize()
            self.pattern_segments.append(pattern_segment)

    async def animate(self, delta):
        if hasattr(self.params, 'color'):
            self.params.foreground_color = self.params.color
        for pattern_segment in self.pattern_segments:
            await pattern_segment.animate(delta)


class TheaterChasePatternSegment(Pattern):
    def __init__(self, segment, params):
        self.segment = segment
        self.params = params
        self.current_offset_fraction = 0

    def initialize(self):
        np.copyto(self.segment.colors, np.array(
            [self.params.background_color for i in range(self.segment.num_leds)]))

    async def animate(self, delta):
        current_offset = int(self.current_offset_fraction *
                             self.params.step_size)
        new_offset_fraction = self.current_offset_fraction + delta * self.params.speed
        while new_offset_fraction >= 1.0:
            new_offset_fraction -= 1.0
        new_offset = int(new_offset_fraction * self.params.step_size)

        # Reset offset leds to background color
        for i in range(current_offset, self.segment.num_leds, self.params.step_size):
            self.segment.colors[i] = self.params.background_color

        # Set new offset leds to foreground color
        for i in range(new_offset, self.segment.num_leds, self.params.step_size):
            self.segment.colors[i] = self.params.foreground_color

        self.current_offset_fraction = new_offset_fraction
