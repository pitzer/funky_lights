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
        # Board as a broadcast comparison rather than a 100x100 Python loop.
        u = np.arange(self.width).reshape(-1, 1)
        v = np.arange(self.height).reshape(1, -1)
        light = ((u // self.box_size) % 2) == ((v // self.box_size) % 2)
        self.grid.coordinates[:] = np.where(
            light[..., None], self.params.color, self.params.background_color)
        self.applyGrid(self.grid)
    
    def reset(self):
        super().reset()
        self.initialize()

    async def animate(self, delta):
        # Each cell decays from its own previous value only, so the per-cell
        # loop this replaces was pure overhead: 10,000 iterations a frame,
        # synchronously on the event loop. That is enough to stall OPC output
        # for every segment at once -- the same fault that made the whole
        # sculpture flash together when RainbowWavesPattern came round.
        # Float maths and the truncation on assignment into the ubyte grid are
        # unchanged, so the output is byte for byte what it was.
        self.grid.coordinates[:] = (
            self.params.decay_param * self.grid.coordinates
            + (1 - self.params.decay_param) * self.params.background_color)
        self.applyGrid(self.grid)
