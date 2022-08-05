from patterns.pattern import Pattern
import patterns.palettes as palettes
import numpy as np

class CrossfadePattern(Pattern):
    def __init__(self):
        super().__init__()
        self.palette = palettes.BLUES
        self.palette_rotated = np.roll(self.palette, 2, axis=0)

        self.SEG_LEN = 100
        self.DOWN = 1

        # Frequency of segment length change (in Hz)
        self.fps = 25

    def initialize(self):
        self.segment_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        for segment in self.segments:
            len = segment.colors.shape[0]
            for x, color in enumerate(segment.colors):
                if (x / len) <  (self.SEG_LEN / 100):
                    np.copyto(color, self.palette[self.current_color_index])
                else:
                    np.copyto(color, self.palette_rotated[self.current_color_index]) 
        pass

    def animate(self, delta):

        self.segment_delta += delta
        if self.segment_delta < 1 / self.fps:
            return

        for segment in self.segments:
            len = segment.colors.shape[0]
            for x, color in enumerate(segment.colors):
                if (x / len) <  (self.SEG_LEN / 100):
                    np.copyto(color, self.palette[self.current_color_index])
                else:
                    np.copyto(color, self.palette_rotated[self.current_color_index])

        
        if self.DOWN == 1:
            self.SEG_LEN -= 1 
        else: 
            self.SEG_LEN += 1
        
        # Only transition colors when direction is changing
        if self.SEG_LEN == 1:
            self.palette_rotated = np.roll(self.palette_rotated, 1, axis=0)
            self.palette = np.roll(self.palette, 1, axis=0)
            self.DOWN = 0

        if self.SEG_LEN == 100:
            self.palette_rotated = np.roll(self.palette_rotated, 1, axis=0)
            self.palette = np.roll(self.palette, 1, axis=0)
            self.DOWN = 1

        # Reset time
        self.segment_delta = 0