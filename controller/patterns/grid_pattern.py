from patterns.pattern import Pattern
import patterns.palettes as palettes
import numpy as np
import sys
import math


#Create a class that acts as a 2D abstraction on the elephant
class Grid():
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.coordinates = [[[0,0,0] for j in range(self.height)] for i in range(self.width)]
    
    def _paint(self, x, y, color):  
        x, y = int(x), int(y)
        if x < self.width and y < self.height:
            self.coordinates[x][y] = color
    
    def _paintmesh(self, mesh, color):
        positions = np.array(mesh).reshape(2,-1).T
        for e in positions:
            self._paint(e[0], e[1], color)
    
    #Paint a defined area of the grid one color
    #TODO: extend to allow passing an array of colors
    def colorArea(self, x1, x2, y1, y2, color):
        x1, x2, y1, y2 = int(x1), int(x2), int(y1), int(y2)
        x_range = np.arange(x1, x2, 1)
        y_range = np.arange(y1, y2, 1)
        #create grid of positions, translate back into list of coordinates
        self._paintmesh(np.meshgrid(x_range, y_range), color)

    #Paint a circle with a defined radius and center points
    #WARNING: memory intensive and given the number of LEDs, we really can't see the edges of the circle. Use colorArea instead.
    def colorCircle(self, x, y, r, color):
        x_range = np.arange(x-r, x+r, 1)
        y_range = np.arange(y-r, y+r, 1)
        grid = np.meshgrid(x_range, y_range)
        circle = np.sqrt(((grid[0]-r)**2 + (grid[1]-r)**2))
        self._paintmesh(circle, color)

    #Apply one color to entire grid
    def colorAll(self, color):
        self.coordinates = [[color for j in range(self.height)] for i in range(self.width)]
    
#Apply grid color map to Segments
def applyGrid(segments, grid):
    for segment in segments:
        for i, color in enumerate(segment.colors):
            uv = segment.uv[i]
            np.copyto(color, grid.coordinates[uv[1]][uv[0]])

class GridPattern(Pattern):
    def  __init__(self):
        super().__init__()
        self.width = 100
        self.height = 100
        self.grid = Grid(self.width, self.height)


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
                u = clamp(0, u, self.width)
                v = clamp(0, v, self.height)
                uv.append(np.array([u, v]))
            segment.uv = np.array(uv)
    
    def initialize(self, startingGrid=None):        
        self.generateCoordinates(self.width, self.height)
        if startingGrid:
            self.grid = startingGrid  
            applyGrid(self.segments, self.grid)
 
    def colorArea(self, x1, x2, y1, y2, color):
        self.grid.update(x1, x2, y1, y2, color)
    

    def animate(self):
        applyGrid(self.segments, self.grid)