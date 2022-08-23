from patterns.pattern import PatternUV, UVGrid
import numpy as np


class CheckersPattern(PatternUV):
    def __init__(self, width = 100, height = 100):
        super().__init__()
        self.params.color = np.array([255, 255, 255], dtype=np.uint8)
        self.params.background_color = np.array([0, 0, 0], dtype=np.uint8)
        self.params.decay_param = 0.95
        self.width = width
        self.height = height
        self.box_size = 10
        
    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.grid = UVGrid(self.width, self.height)
        for u in range(self.width):
            for v in range(self.height):
                if (u//self.box_size) % 2 == (v//self.box_size) % 2:
                    self.grid.coordinates[u][v] = self.params.color
                else:
                    self.grid.coordinates[u][v] = self.params.background_color
        self.applyGrid(self.grid)
    
    def reset(self):
        super().reset()
        self.initialize()

    async def animate(self, delta):
        for u in range(self.width):
            for v in range(self.height):
                self.grid.coordinates[u][v] =  self.params.decay_param * self.grid.coordinates[u][v] + \
                        (1 - self.params.decay_param) * self.params.background_color
        self.applyGrid(self.grid)

