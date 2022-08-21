from patterns.pattern import Pattern
import numpy as np

class CalibrationPattern(Pattern):
    def __init__(self):
        super().__init__()

    async def animate(self, delta):
        WHITE = np.array([255, 255, 255], dtype=np.uint8)
        BLACK = np.array([0, 0, 0], dtype=np.uint8)
        for segment in self.segments:
            segment.colors[0] = WHITE
            for color in segment.colors[1:]:
                np.copyto(color, BLACK)