from patterns.pattern import Pattern
import numpy as np


class SegmentIdPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.color = np.array([255, 255, 255], dtype=np.uint8)

    def reset(self):
        for pattern_segment in self.pattern_segments:
            pattern_segment.reset()
        
    def initialize(self):
        self.pattern_segments = []
        for i, segment in enumerate(self.segments):
            pattern_segment = SegmentIdPatternSegment(segment, self.params)
            pattern_segment.initialize()
            pattern_segment.segment_index = i
            self.pattern_segments.append(pattern_segment)

    async def animate(self, delta):
        for pattern_segment in self.pattern_segments:
            await pattern_segment.animate(delta)


class SegmentIdPatternSegment(Pattern):
    def __init__(self, segment, params):
        super().__init__()
        self.segment = segment
        self.params = params

    async def animate(self, delta):
        self.segment.colors[:self.segment_index] = self.params.color
                