from patterns.pattern import Pattern
import numpy as np
import math


class StaticColorPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.color = (255, 0, 0)
        
    def initialize(self):
        for segment in self.segments:
            segment.colors[:] = self.params.color

    async def animate(self, delta):
        return

                
class BreathingColorPattern(StaticColorPattern):
    def __init__(self):
        super().__init__()
        self.params.breath_period_s = 10.0
        self.params.breath_amplitude_percent = 0.5
        self.breath_time = 0

    def initialize(self):
        super().initialize()

    def clip(value, min_val, max_val):
        """Clips a value within a specified range."""
        return max(min_val, min(value, max_val))

    async def animate(self, delta):
        self.breath_time =  (self.breath_time + delta) % self.params.breath_period_s
        rad = self.breath_time * math.pi * 2 / self.params.breath_period_s
        brightness = math.sin(rad) * self.params.breath_amplitude_percent * 255

        for segment in self.segments:
          segment.colors[:] = np.clip(np.array(self.params.color) + brightness, 0, 255)