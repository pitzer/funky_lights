from patterns.pattern import PatternUV, UVGrid
import patterns.palettes as palettes
import numpy as np
import colorsys as colorsys

class RainbowPattern(PatternUV):
    def __init__(self, width=100, height=100):
        super().__init__()
        # Frequency of color change (in Hz)
        self.fps = 2
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
    
    def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        for x1 in range(self.width):
            rgb = colorsys.hsv_to_rgb((x1*self.spectrum[x1]/self.width), 1, 0.8)
            rgb_int = (np.array(rgb)*255).astype(int)
            self.grid.paintArea([x1, x1+1], [1, self.height], rgb_int)
        
        self.spectrum = np.roll(self.spectrum, 1)  
        self.applyGrid(self.grid)