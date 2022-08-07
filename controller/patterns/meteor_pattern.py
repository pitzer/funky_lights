from patterns.pattern import Pattern
import numpy as np
import random


class MeteorPatternSegment():
    def __init__(self, segment, params):
        self.segment = segment
        self.params = params
        self.meteor_position = 0

    def fadeToBlack(self, c, fadeValue):
        for i in range(len(c)):
            c[i] = 0 if (c[i] <= 10) else int(c[i]-(c[i]*fadeValue/256))
        return c

    def animate(self, delta):
        # fade brightness all LEDs one step
        for color in self.segment.colors:
            if (not self.params.meteorRandomDecay) or (random.randint(0, 10) > 5):
                color = self.fadeToBlack(color, self.params.meteorTrailDecay)
        # draw meteor
        for j in range(self.params.meteorSize):
            k = self.meteor_position - j
            if (k < self.segment.num_leds) and (k >= 0):
                self.segment.colors[k] = self.params.meteorColor

        self.meteor_position = (self.meteor_position + 1) % (
            2 * self.segment.num_leds)


class MeteorPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.meteorRandomDecay = True
        self.params.meteorSize = 10
        self.params.meteorTrailDecay = 64
        self.params.meteorColor = np.array([255, 255, 255])

    def initialize(self):
        self.pattern_segments = []
        for segment in self.segments:
            self.pattern_segments.append(
                MeteorPatternSegment(segment, self.params))

    def animate(self, delta):
        for pattern_segment in self.pattern_segments:
            pattern_segment.animate(delta)
