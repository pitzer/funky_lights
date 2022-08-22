from patterns.pattern import Pattern, PatternUV
import patterns.palettes as palettes
import math
import numpy as np
import random
import sys
import colorsys as colorsys

# COOLING: How much does the air cool as it rises?
# Less cooling = taller flames.  More cooling = shorter flames.
# Default 550
COOLING = 600

# SPARKING: What chance(out of 255) is there that a new spark will be lit?
# Higher chance = more roaring fire.  Lower chance = more flickery fire.
# Default 120, suggested range 50-200.
SPARKING = 120


# Unused color conversion function
def convert_color(hsv):
    rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2])
    return [int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255)]

def extrapolate_color(rgb):
    hsv = colorsys.rgb_to_hsv(rgb[0]/255, rgb[1]/255, rgb[2]/255)
    h = hsv[0]
    palette = [[0,0,0], [h,1,0.13], [h, 1, 0.53], [h, 1, 1], [(h+0.066)%1,1,1], [(h+0.03)%1,0.2,1]]
    return np.array([convert_color(i) for i in palette], dtype=np.uint8)


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
        self.heat = {}
        for segment in self.segments:
            self.heat[segment] = np.array(
                [0 for i in range(segment.num_leds)], np.uint8)

    async def animate(self, delta):
        for segment in self.segments:
            heat = self.heat[segment]
            # Update heat
            updateHeat(heat)
            # Map from heat cells to LED colors
            for j in range(segment.num_leds):
                colorindex = (float)(
                    heat[j] * (self.params.palette.shape[0] - 1)) / 256
                segment.colors[j] = getPalColor(self.params.palette, colorindex)


class FirePatternUV(PatternUV):
    def __init__(self):
        super().__init__()
        if hasattr(self.params, 'color'):
            self.params.palette = extrapolate_color(self.params.color)
        else:
            self.params.palette = palettes.FIRE
        self.params.width = 2
        self.params.height = 100

    def initialize(self):
        if hasattr(self.params, 'color'):
            self.params.palette = extrapolate_color(self.params.color)
        else:
            self.params.palette = palettes.FIRE
        self.palette_size = self.params.palette.shape[0]
        self.frame = np.zeros((self.params.height, self.params.width, 3), np.uint8)
        self.heat = [np.array([0 for i in range(self.params.height)])
                     for i in range(self.params.width)]
        self.generateUVCoordinates(self.params.width, self.params.height)

    async def animate(self, delta):
        #Check for color changes
        if hasattr(self.params, 'color'):
            self.params.palette = extrapolate_color(self.params.color)
        else:
            self.params.palette = palettes.FIRE
        for i in range(self.params.width):
            heat = self.heat[i]
            # Update heat
            updateHeat(heat)
            # Map from heat cells to LED colors
            for j in range(self.params.height):
                color_index = (float)(heat[j] * (self.palette_size - 1)) / 256
                color = getPalColor(self.params.palette, color_index)
                # Mirror along horizontal axis so fire starts from the bottom
                self.frame[self.params.height - 1 - j, i] = color

        # Copy to segments
        for segment in self.segments:
            i = 0
            for color in segment.colors:
                uv = segment.uv[i]
                np.copyto(color, self.frame[uv[0], uv[1]])
                i += 1
