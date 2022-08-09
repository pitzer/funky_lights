from patterns.pattern import Pattern
import numpy as np

class ColorRollPattern(Pattern):
    def __init__(self):
        super().__init__()

    def initialize(self):
        PATTERN_SIZE = 30
        PATTERN_SIZE_HALF = int(PATTERN_SIZE / 2)

        for segment in self.segments:
            for i in range(PATTERN_SIZE_HALF):
                if i >= segment.num_leds:
                    break 
                col = int(i / PATTERN_SIZE_HALF * 255)
                segment.colors[i] = [col, 255 - col, 0]
            for i in range(PATTERN_SIZE_HALF, PATTERN_SIZE):
                if i >= segment.num_leds:
                    break
                col = int(255 - ((i - PATTERN_SIZE_HALF) / PATTERN_SIZE_HALF * 255))
                segment.colors[i] = [col, 255 - col, 0]
            for i in range(PATTERN_SIZE, segment.num_leds):
                if i >= segment.num_leds:
                    break
                col = 0
                segment.colors[i] = [col, 255 - col, 0]

    def animate(self, delta):
        for segment in self.segments:
            segment.colors = np.roll(segment.colors, 1, axis=0)