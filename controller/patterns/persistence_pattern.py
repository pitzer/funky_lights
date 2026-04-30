from .utils import expandKeys, scaleColors
from .pattern import Pattern
from copy import deepcopy
import numpy as np

class PersistencePattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.sub_pattern_def = None
        self.params.fade_factor = 0.95
        self.params.color_fade_factor = 0.8
        self.params.color = None
        self.sub_pattern = {}

    def prepareSegments(self, led_config):
        # Create our own segments
        super().prepareSegments(led_config)
    
    def getSegments(self):
        if not self.sub_pattern:
            raise ValueError("Sub-pattern not initialized")
        for segment in self.sub_pattern.getSegments():
            yield segment

    def initialize(self):
        # Create the sub-pattern
        cls, params = self.params.sub_pattern_def
        self.sub_pattern = cls()
        for key in params:
            setattr(self.sub_pattern.params, key, params[key])
        self.sub_pattern.segments = deepcopy(self.segments)
        self.sub_pattern.initialize()

    async def animate(self, delta):
        if not self.sub_pattern:
            raise ValueError("Sub-pattern not initialized")
        await self.sub_pattern.animate(delta)
        for i in range(len(self.segments)):
            segment_dst = self.segments[i]
            segment_src = self.sub_pattern.segments[i]
            start = 0
            end = segment_src.colors.shape[0]
            # Add the color
            updated = np.any(segment_src.colors[start:end, :] > 0, axis=1)
            new_colors = segment_src.colors[start:end][updated].astype(float) + segment_dst.colors[start:end][updated].astype(float)
            segment_dst.colors[start:end][updated] = np.clip(new_colors, 0, 255).astype(np.uint8)
            # Fade out all the LEDs
            segment_dst.colors[start:end] = segment_dst.colors[start:end] * self.params.fade_factor
            # If a color is specified, steer the color toward that color
            if self.params.color is not None:
                brightness_adjust = np.mean(segment_dst.colors[start:end], axis=1) / np.mean(self.params.color)
                new_colors = segment_dst.colors[start:end].astype(float) * self.params.color_fade_factor + self.params.color * brightness_adjust[:, np.newaxis] * (1 - self.params.color_fade_factor)
                segment_dst.colors[start:end] = np.clip(new_colors, 0, 255).astype(np.uint8)
        
