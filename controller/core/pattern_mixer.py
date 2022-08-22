from patterns.pattern import Pattern
import numpy as np

class PatternMix(Pattern):
    def __init__(self, patterns, pattern_cache):
        super().__init__()
        self.patterns = patterns
        self.pattern_cache = pattern_cache
        self.base_patterns = []
        self.mix_patterns = []
        self.replace_patterns = []

    def get_patterns_from_id(self, pattern_ids):
        selected_patterns = []
        for pattern_id in pattern_ids:
            if self.pattern_cache and pattern_id in self.pattern_cache.patterns:
                selected_patterns.append(self.pattern_cache.patterns[pattern_id])
            else:
                selected_patterns.append(self.patterns[pattern_id])
        return selected_patterns

    def update_mix(self, base_pattern_ids, replace_pattern_ids, mix_pattern_ids):
        self.base_pattern_ids = self.get_patterns_from_id(base_pattern_ids)
        self.replace_patterns = self.get_patterns_from_id(replace_pattern_ids)
        self.mix_patterns = self.get_patterns_from_id(mix_pattern_ids)

    async def animate(self, delta):
        # Zero out colors
        for segment in self.segments:
            segment.colors[:] = 0

        # Base
        for pattern in self.base_pattern_ids:
            await pattern.animate(delta)
            for segment, mix_segment in zip(self.segments, pattern.segments):
                np.copyto(segment.colors, mix_segment.colors)

        # Replace
        for pattern in self.replace_patterns:
            await pattern.animate(delta)
            included_segments = list(pattern.getSegments())
            for segment, mix_segment in zip(self.segments, pattern.segments):
                if mix_segment in included_segments:
                    np.copyto(segment.colors, mix_segment.colors)

        # Mix mix
        for pattern in self.mix_patterns:
            await pattern.animate(delta)
            for segment, mix_segment in zip(self.segments, pattern.segments):
                tmp = 255 - mix_segment.colors  # a temp uint8 array here
                np.putmask(segment.colors, tmp < segment.colors, tmp)  # a temp bool array here
                segment.colors += mix_segment.colors


