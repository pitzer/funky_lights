from patterns.pattern import PatternUV, UVGrid
import patterns.palettes as palettes
import numpy as np

class Block():
    def __init__(self, u, v, size, color, x_inc, y_inc):
        self.u = u
        self.v = v
        self.size = size
        self.color= color
        self.u_inc = x_inc
        self.v_inc = y_inc

class BouncingBlocksPattern(PatternUV):
    def __init__(self):
        super().__init__()
        self.palette = palettes.COOL
        # Frequency of color change (in Hz)
        self.fps = 30
        self.num_blocks = 10
        #starting positions
        self.u1 = 50
        self.v1 = 1
        self.u_inc = 1
        self.v_inc = 0.5
        self.size = 10
        self.width = 100
        self.height = 100
    
    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.grid = UVGrid(self.width, self.height)
        self.grid.paintAll(self.palette[self.current_color_index])
        self.blocks = []
        for block in range(self.num_blocks):
            xi = np.random.random()
            yi = np.random.random()
            cur_block = Block(
                np.random.randint(0,self.width),
                np.random.randint(0,self.height),
                self.size,
                self.palette[self.current_color_index+1],
                xi if xi > 0.5 else -xi,
                yi if yi < 0.5 else -yi
            )
            self.blocks = np.append(self.blocks, cur_block)
            self.grid.paintArea([xi, xi+self.size], [yi, yi+self.size], self.palette[self.current_color_index+1])
        self.applyGrid(self.grid)
    

    def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        self.grid.paintAll(self.palette[self.current_color_index])

        for block in self.blocks:
            u2 = block.u + block.size
            v2 = block.v + block.size
            block.u += block.u_inc
            block.v += block.v_inc

            if block.u >= self.width or block.u <=0:
                block.u_inc = block.u_inc * -1
            if block.v >= self.height or block.v <=0:
                block.v_inc = block.v_inc * -1
            
            self.grid.paintArea([block.u, u2], [block.v, v2], self.palette[self.current_color_index+1])

        self.applyGrid(self.grid)
        self.cumulative_delta = 0