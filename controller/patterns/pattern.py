import numpy as np
import sys


class Segment:
    def __init__(self, uid, num_leds, led_positions):
        self.uid = uid
        self.num_leds = num_leds
        self.colors = np.array([[255, 0, 0] for i in range(num_leds)], dtype=np.ubyte)
        self.led_positions = np.array(led_positions)

class Pattern:
    class PatternParameters:
        pass

    def __init__(self):
        self.segments = []
        self.params = self.PatternParameters()

    def prepareSegments(self, led_config):
        for s in led_config['led_segments']:
            segment = Segment(s['uid'], s['num_leds'], s['led_positions'])
            self.segments.append(segment)

    def initialize(self):
        pass
        
    async def animate(self, delta):
        pass

class UVGrid():
    def __init__(self, width, height):
        self.width = width
        self.height = height
<<<<<<< HEAD
        self.coordinates = np.array([[[0, 0, 0] for j in range(
            self.height)] for i in range(self.width)], dtype=np.uint8)
        #self.mesh = np.meshgrid(np.arange(self.width), np.arange(self.height), [0,0,0])
=======
        self.coordinates = np.array([[[0,0,0] for j in range(self.height)] for i in range(self.width)], dtype=np.ubyte)
>>>>>>> cdad1ed (dmx config file)
    
    def paintPoint(self, u, v, color):  
        u, v = int(u), int(v)
        if u < self.width and v < self.height:
            self.coordinates[u][v] = color
    
    def paintMesh(self, mesh, color):
        positions = np.array(mesh).reshape(2,-1).T
        for e in positions:
            self.paintPoint(e[0], e[1], color)
    
    #Paint a defined area of the grid one color
    def paintArea(self, u, v, color):
        u_range = np.arange(int(u[0]), int(u[1]), 1)
        v_range = np.arange(int(v[0]), int(v[1]), 1)
        
        #create grid of positions
        self.paintMesh(np.meshgrid(u_range, v_range), color)

    #Apply one color to entire grid
    def paintAll(self, color):
        self.coordinates = [[color for j in range(self.height)] for i in range(self.width)]
    

class PatternUV(Pattern):
   
    def __init__(self):
        super().__init__()
    
    def applyGrid(self, grid):
        for segment in self.segments:
            for i, color in enumerate(segment.colors):
                uv = segment.uv[i]
                np.copyto(color, grid.coordinates[uv[1]][uv[0]])

    def generateUVCoordinates(self, width, height, offset_u=0, offset_v=0):
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

        # Shift 3D points so that min(y) and min(z) are at the origin
        offset = np.array([-min_y, -min_z])
        # Scale y and z axis to [0, 1].
        # Note: the axis are scaled independently which could lead to distortions
        scale = np.array([(height - 1) / (max_y - min_y),
                          (width - 1) / (max_z - min_z)])
        for segment in self.segments:
            uv = []
            for p in segment.led_positions:
                pm = np.multiply(p[1:] + offset, scale).astype(int)
                u = int(height) - 1 - pm[0] + offset_u
                v = pm[1] + offset_v
                uv.append(np.array([u, v]))
            segment.uv = np.array(uv)

    def initialize(self):
        pass
        
    def animate(self, delta):
        pass