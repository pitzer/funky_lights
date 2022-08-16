from patterns.pattern import PatternUV, UVGrid
import patterns.palettes as palettes
import numpy as np
import colorsys as colorsys

class RainbowWavesPattern(PatternUV):
    def __init__(self, width=100, height=100):
        super().__init__()
        # Frequency of color change (in Hz)
        self.fps = 40
        self.offset = 0
        self.width = width
        self.height = height
        self.center = [self.width/2, self.height/2]
    
    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.grid = UVGrid(self.width, self.height)
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.spectrum = np.arange(0, 1, 1/self.width)        
        self.applyGrid(self.grid)  
    
    async def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        for u in range(self.width):
            for v in range(self.height):
                d = np.sqrt((u-self.center[0])**2 + (v-self.center[1])**2)
                rgb = colorsys.hsv_to_rgb((self.spectrum[int(d)]), 1, 0.8)
                rgb_int = (np.array(rgb)*255).astype(int)
                self.grid.coordinates[u][v] = rgb_int
        
        self.spectrum = np.roll(self.spectrum, 1)  
        self.applyGrid(self.grid)
        self.cumulative_delta = 0