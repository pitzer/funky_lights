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

        # Everything below is frame-invariant, so it is computed once here
        # rather than 10,000 times per frame. This used to be a 100x100 Python
        # loop doing an np.sqrt, a colorsys.hsv_to_rgb and an array allocation
        # per cell -- ~75ms a frame against a 50ms budget on a laptop, and
        # several times that on the Pi. Because it runs synchronously on the
        # event loop it stalled OPC output for every segment at once, which on
        # the sculpture looks like all the strips flashing together. Only the
        # eyes escaped it: they are a replace pattern painted afterwards.
        #
        # The distance from centre never changes, so the ring index each cell
        # reads is fixed.
        u = np.arange(self.width).reshape(-1, 1)
        v = np.arange(self.height).reshape(1, -1)
        d = np.sqrt((u - self.center[0])**2 + (v - self.center[1])**2)
        self._ring_index = d.astype(int)

        # The spectrum is only ever a rotation of the same `width` hues, so
        # every colour the pattern can ever show is in this table. It is built
        # from the spectrum's own values rather than recomputing i/width, so
        # the floats -- and therefore the truncation in astype(int) -- match
        # the original exactly.
        self._rgb_lut = np.array(
            [(np.array(colorsys.hsv_to_rgb(h, 1, 0.8)) * 255).astype(int)
             for h in self.spectrum], dtype=np.ubyte)

        # Rolled in lockstep with self.spectrum, so _hue_index[i] is always the
        # LUT row for spectrum[i].
        self._hue_index = np.arange(self.width)

        self.applyGrid(self.grid)  
    
    async def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        # One gather in place of the double loop.
        self.grid.coordinates[:] = self._rgb_lut[self._hue_index[self._ring_index]]

        self.spectrum = np.roll(self.spectrum, 1)
        self._hue_index = np.roll(self._hue_index, 1)
        self.applyGrid(self.grid)
        self.cumulative_delta = 0
