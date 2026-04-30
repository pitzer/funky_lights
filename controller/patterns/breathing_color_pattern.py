from patterns.pattern import Pattern
from .utils import scaleColors

import numpy as np

class BreathingColorPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.period_s = 5.0
        self.params.amplitude_pct = 1.0
        self.params.vary_segments = False
        self.params.type = "sine"
        self.params.color = (255, 255, 255)
        self.breath_time = 0

    def initialize(self):
        super().initialize()

    def clip(value, min_val, max_val):
        """Clips a value within a specified range."""
        return max(min_val, min(value, max_val))

    async def animate(self, delta):
        self.breath_time += delta

        # For each segment, we create use a slightly different period and starting
        # phase to create a more dynamic effect.
        period = float(self.params.period_s)
        phase_offset = 0
        for segment in self.segments:
            phase = (self.breath_time * np.pi * 2 / period + phase_offset) % (2 * np.pi)
            if self.params.type == "static":
                brightness = 1.0
            elif self.params.type == "ramp_and_hold":
                if phase < np.pi / 2:
                    brightness = (1.0 + np.sin(phase * 2 - np.pi / 2)) / 2.0
                elif phase < np.pi:
                    brightness = 1.0
                elif phase < 3 * np.pi / 2:
                    brightness = (1.0 + np.sin((phase - np.pi) * 2 + np.pi / 2)) / 2.0
                else:
                    brightness = 0.0
            elif self.params.type == "sine":
                brightness = (1.0 + np.sin(phase)) / 2.0
            elif self.params.type == "single_pulse":
                if phase < 2.0 * np.pi / 4:
                    brightness = np.sin(phase * 2) ** 2 
                else:
                    brightness = 0.0
            elif self.params.type == "double_pulse":
                if phase < 2.0 * np.pi / 3:
                    brightness = np.sin(phase * 3) ** 2 
                else:
                    brightness = 0.0
            else:
                raise ValueError(f"Invalid breathing pattern type: {self.params.type}")
            segment.colors = scaleColors(self.params.color, np.full((segment.num_leds,), brightness), self.params.amplitude_pct)
            if self.params.vary_segments:
                phase_offset += 3.0
                period += self.params.period_s / 20.0
