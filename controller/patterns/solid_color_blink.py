from patterns.pattern import Pattern
import numpy as np

PALETTE_TROPICAL = np.array([[242, 207, 51], [245, 112, 76], [32, 158, 179], [240, 167, 141]])

class SolidColorBlinkPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.palette = None
        self.current_color_index = 0
        self.fps = 0.5
        self.cumulative_delta = 1000

    def initialize(self):
        pass

    def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return
        self.current_color_index = (self.current_color_index + 1) % self.palette.shape[0]
        for segment in self.segments:
            for color in segment.colors:
                np.copyto(color, self.palette[self.current_color_index])
        self.cumulative_delta = 0