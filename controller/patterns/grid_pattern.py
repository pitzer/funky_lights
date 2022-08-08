from patterns.pattern import Pattern
import patterns.palettes as palettes
import numpy as np
import sys

palette = palettes.BLUES


#Create a class that acts as a 2D abstraction on the elephant
class Grid():
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.coordinates = [[[0,0,0] for j in range(height)] for i in range(width)]
    
    def update (self, x1, x2, y1, y2, color):
        for x in range(x2-x1):
            if x1 + x < self.width:
                for y in range(y2-y1):
                    if y1 + y < self.height:
                        self.coordinates[x1 + x][y1 + y] = color
        return self

    #Apply one color to entire grid
    def colorAll(self, color):
        self.coordinates = [[color for j in range(self.height)] for i in range(self.width)]
        return self
    
#Apply grid color map to Segments
def applyGrid(segments, grid):
    for segment in segments:
        for i, color in enumerate(segment.colors):
            uv = segment.uv[i]
            np.copyto(color, grid.coordinates[uv[0]][uv[1]])

class GridPattern(Pattern):
    def  __init__(self):
        super().__init__()
        self.test_int = 1

    def generateCoordinates(self, width=100, height=100):
        max_x = max_y = max_z = sys.float_info.min
        min_x = min_y = min_z = sys.float_info.max
        for segment in self.segments:
            for p in segment.led_positions:
                max_x = max(max_x, p[0])
                min_x = min(min_x, p[0])
                max_y = max(max_y, p[1])
                min_y = min(min_y, p[1])
                max_z = max(max_z, p[2])
                min_z = min(min_z, p[2])
        offset = np.array([-min_y, -min_z])
        scale = np.array([(height - 1) / (max_y - min_y),
                         (width - 1) / (max_z - min_z)])
        for segment in self.segments:
            uv = []
            for p in segment.led_positions:
                pm = np.multiply(p[1:] + offset, scale).astype(int)
                u = int(height) - 1 - pm[0]
                v = pm[1]

                def clamp(minimum, x, maximum):
                    return max(minimum, min(x, maximum))
                u = clamp(0, u, self.height)
                v = clamp(0, v, self.width)
                uv.append(np.array([u, v]))
            segment.uv = np.array(uv)
    
    def initialize(self, startingGrid=None):
        self.palette_size = palette.shape[0]
        
        self.generateCoordinates(self.width, self.height)
        if startingGrid:
            self.grid = startingGrid  
        else:
            self.grid = Grid(self.width, self.height)
        applyGrid(self.segments, self.grid)
 
    
    def animate(self, delta):
        self.grid = self.grid.update(0, self.test_int, 0, self.test_int, [255,255,0])
        # Copy to segments
        applyGrid(self.segments, self.grid)
        self.test_int +=1