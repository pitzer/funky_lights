from patterns.grid_pattern import GridPattern
import patterns.palettes as palettes
import numpy as np
import colorsys as colorsys

class RainbowPattern(GridPattern):
    def __init__(self):
        super().__init__()
        # Frequency of color change (in Hz)
        self.fps = 2
        self.offset = 0
    
    def initialize(self):
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.spectrum = np.arange(0, 1, 1/self.width)        
        super().initialize(self.grid)
    
    
    def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        for x1 in range(self.width):
            rgb = colorsys.hsv_to_rgb((x1*self.spectrum[x1]/self.width), 1, 0.8)
            rgb_int = (np.array(rgb)*255).astype(int)
            self.grid.colorArea(x1, x1+1, 1, self.height, rgb_int)
        
        self.spectrum = np.roll(self.spectrum, 1)  
        super().animate()

        
