from patterns.pattern import Pattern
import numpy as np

class PatternMix(Pattern):
    def __init__(self, pattern_manager):
        super().__init__()
        self.pattern_manager = pattern_manager
        self.base_patterns = []
        self.mix_patterns = []
        self.replace_patterns = []

    def get_patterns_from_id(self, pattern_ids):
        selected_patterns = []
        for pattern_id in pattern_ids:
            pattern = self.pattern_manager.pattern(pattern_id)
            selected_patterns.append(pattern)
        return selected_patterns

    def set_mix(self, base_pattern_ids, replace_pattern_ids, mix_pattern_ids):
        self.base_patterns = self.get_patterns_from_id(base_pattern_ids)
        self.replace_patterns = self.get_patterns_from_id(replace_pattern_ids)
        self.mix_patterns = self.get_patterns_from_id(mix_pattern_ids)

    async def update(self):
        # Zero out colors
        for segment in self.segments:
            segment.colors[:] = 0

        # Base
        for pattern in self.base_patterns:
            for segment, mix_segment in zip(self.segments, pattern.segments):
                if mix_segment.mask:
                    # Mask available, copy masked LEDs only
                    m = mix_segment.mask
                    segment.colors[m.start:m.end] = mix_segment.colors[m.start:m.end]
                else:
                    # No mask, copy everything
                    np.copyto(segment.colors, mix_segment.colors)

        # Replace
        for pattern in self.replace_patterns:
            included_segments = list(pattern.getSegments())
            for segment, mix_segment in zip(self.segments, pattern.segments):
                if mix_segment in included_segments:
                    if mix_segment.mask:
                        # Mask available, copy masked LEDs only
                        m = mix_segment.mask
                        segment.colors[m.start:m.end] = mix_segment.colors[m.start:m.end]
                    else:
                        # No mask, copy everything
                        np.copyto(segment.colors, mix_segment.colors)

        # Mix
        for pattern in self.mix_patterns:
            for segment, mix_segment in zip(self.segments, pattern.segments):
                tmp = 255 - mix_segment.colors  # a temp uint8 array here
                np.putmask(segment.colors, tmp < segment.colors, tmp)  # a temp bool array here
                if mix_segment.mask:
                    # Mask available, copy masked LEDs only
                    m = mix_segment.mask
                    segment.colors[m.start:m.end] += mix_segment.colors[m.start:m.end]
                else:
                    # No mask, copy everything
                    segment.colors += mix_segment.colors

        return self.segments
