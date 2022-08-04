from patterns.pattern import Pattern
import math
import numpy as np
import random
import sys

# COOLING: How much does the air cool as it rises?
# Less cooling = taller flames.  More cooling = shorter flames.
# Default 550
COOLING = 600

# SPARKING: What chance(out of 255) is there that a new spark will be lit?
# Higher chance = more roaring fire.  Lower chance = more flickery fire.
# Default 120, suggested range 50-200.
SPARKING = 120

# Approximate "black body radiation" palette, akin to the FastLED 'HeatColor' function. 
# Recommend that you use values 0-240 rather than the usual 0-255, as the last 15 colors 
# will be 'wrapping around' from the hot end to the cold end, which looks wrong.
PALETTE_HEAT = np.array(
    [(0x00, 0x00, 0x00), (0xFF, 0x00, 0x00), (0xFF, 0xFF, 0x00), (0xFF, 0xFF, 0xCC)])
PALETTE_FIRE = np.array([(0x00, 0x00, 0x00), (0x22, 0x00, 0x00), (
    0x88, 0x00, 0x00), (0xFF, 0x00, 0x00), (0xFF, 0x66, 0x00), (0xFF, 0xCC, 0x00)])
PALETTE_COOL = np.array(
    [(0x00, 0x00, 0xFF), (0x00, 0x99, 0xDD), (0x44, 0x44, 0x88), (0x99, 0x00, 0xDD)])


def interpolate(color1, color2, x):
    return x * (color2 - color1) + color1


def getPalColor(palette, i):
    palette_size = palette.shape[0]
    i0 = int(i % palette_size)
    i1 = int((i+1) % palette_size)

    # decimal part is used to interpolate between the two colors
    t0 = i - math.trunc(i)

    return interpolate(palette[i0], palette[i1], t0)


def updateHeat(heat):
    # Step 1.  Cool down every cell a little
    rMax = int(COOLING / len(heat)) + 2
    for i in range(len(heat)):
        heat[i] = max(heat[i] - random.randint(0, rMax), 0)

    # Step 2.  Heat from each cell drifts 'up' and diffuses a little
    for k in range(len(heat) - 1, 2, -1):
        heat[k] = (heat[k - 1] + heat[k - 2] + heat[k - 3]) / 3

    # Step 3.  Randomly ignite new 'sparks' of heat near the bottom
    if random.randint(0, 255) < SPARKING:
        y = random.randint(0, 7)
        heat[y] = min(heat[y] + random.randint(160, 255), 255)

    return heat


class FirePattern(Pattern):
    def __init__(self):
        super().__init__()

    def initialize(self):
        # Initialize array if necessary
        self.heat = {}
        self.palette = PALETTE_FIRE
        for segment in self.segments:
            self.heat[segment] = np.array([0 for i in range(segment.num_leds)])

    def animate(self, delta):
        for segment in self.segments:
            heat = self.heat[segment]
            # Update heat
            updateHeat(heat)
            # Map from heat cells to LED colors
            for j in range(segment.num_leds):
                colorindex = (float)(
                    heat[j] * (self.palette.shape[0] - 1)) / 256
                segment.colors[j] = getPalColor(self.palette, colorindex)


class FirePatternUV(Pattern):
    def __init__(self):
        super().__init__()

    def generateUVCoordinates(self, width, height):
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

    def initialize(self):
        # Initialize array if necessary
        self.heat = {}
        self.palette = PALETTE_FIRE
        self.palette_size = self.palette.shape[0]
        self.width = 2
        self.height = 100
        self.frame = np.zeros((self.height, self.width, 3), np.uint8)
        self.heat = [np.array([0 for i in range(self.height)])
                     for i in range(self.width)]
        self.generateUVCoordinates(self.width, self.height)

    def animate(self, delta):
        for i in range(self.width):
            heat = self.heat[i]
            # Update heat
            updateHeat(heat)
            # Map from heat cells to LED colors
            for j in range(self.height):
                color_index = (float)(heat[j] * (self.palette_size - 1)) / 256
                color = getPalColor(self.palette, color_index)
                # Mirror along horizontal axis so fire starts from the bottom
                self.frame[self.height - 1 - j, i] = color

        # Copy to segments
        for segment in self.segments:
            i = 0
            for color in segment.colors:
                uv = segment.uv[i]
                np.copyto(color, self.frame[uv[0], uv[1]])
                i += 1
