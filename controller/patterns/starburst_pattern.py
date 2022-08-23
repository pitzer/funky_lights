from random import random
from patterns.pattern import PatternUV, UVGrid
import numpy as np


class Block():
    def __init__(self, u, v, size, color, x_inc = 0, y_inc = 0, speed = 0):
        self.u = u
        self.v = v
        self.size = size
        self.color= color
        self.u_inc = x_inc
        self.v_inc = y_inc
        self.speed = speed

class StarburstPattern(PatternUV):
    def __init__(self, width = 100, height = 100):
        super().__init__()
        self.params.color = np.array([255, 255, 255], dtype=np.uint8)
        self.params.background_color = np.array([0, 0, 0], dtype=np.uint8)
        self.params.decay_param = 0.95
        self.width = width
        self.height = height
        self.center = [self.width/2, self.height/2]
        self.box_size = 4
        self.num_bursts = 300

    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.grid = UVGrid(self.width, self.height)
        for u in range(self.width):
            for v in range(self.height):
                self.grid.coordinates[u][v] = self.params.background_color
        self.bursts = []
        for burst in range(self.num_bursts):
            picker = np.random.randint(0, 4)
            burst = Block(
                self.center[0], 
                self.center[1], 
                self.box_size, 
                self.params.color
                )
            if picker == 0:
                burst.u_inc = np.random.randint(0,self.width)
                burst.v_inc = 0
            elif picker == 1:
                burst.u_inc = np.random.randint(0,self.width)
                burst.v_inc = self.height
            elif picker == 2:
                burst.u_inc = 0
                burst.v_inc = np.random.randint(0,self.height)
            elif picker == 3:
                burst.u_inc = self.width
                burst.v_inc = np.random.randint(0,self.height)
            burst.speed = np.random.random()*2
            
            self.bursts.append(burst)
            self.grid.paintArea([burst.u, (burst.u + burst.size)], [burst.v, (burst.v + burst.size)], burst.color)
        
        self.applyGrid(self.grid)
    
    def reset(self):
        super().reset()
        self.initialize()

    async def animate(self, delta):
        for u in range(self.width):
            for v in range(self.height):
                self.grid.coordinates[u][v] = self.params.background_color
        
        for burst in self.bursts:
            burst.speed = burst.speed * self.params.decay_param
            burst.u += ((burst.u_inc - burst.u) * (1- 1/self.params.decay_param)) * burst.speed
            burst.v += ((burst.v_inc - burst.v) * (1- 1/self.params.decay_param)) * burst.speed
            self.grid.paintArea([burst.u, burst.u + burst.size], [burst.v, burst.v + burst.size], burst.color)

        
        for u in range(self.width):
            for v in range(self.height):
                self.grid.coordinates[u][v] =  self.params.decay_param * self.grid.coordinates[u][v] + \
                        (1 - self.params.decay_param) * self.params.background_color
        self.applyGrid(self.grid)

