from patterns.pattern import Pattern
from copy import deepcopy
import hashlib
import json
import shelve


class CachedPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.colors_timeseries = []
        self.current_index = 0

    def animate(self, delta):
        segment_colors = self.colors_timeseries[self.current_index]
        for i, segment in enumerate(self.segments):
            segment.colors = segment_colors[i]
        self.current_index = (self.current_index + 1) % len(self.colors_timeseries)


class PatternCache:
    def __init__(self, pattern_config, led_config, args):
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.animation_rate = args.animation_rate
        
        led_config_hash = hashlib.sha256(bytearray(json.dumps(
            self.led_config, sort_keys=True).encode('ascii'))).hexdigest()
        print("LED config hash: " + str(led_config_hash))
        self.cache = shelve.open('/tmp/pattern_cache_' + str(led_config_hash))

    def build_cache(self, max_pattern_duration):
        patterns = []
        for pattern_index, config in enumerate(self.pattern_config):
            pattern_index = str(pattern_index)
            if not pattern_index in self.cache:
                # Initialize pattern
                (_, cls, params) = config
                pattern = cls()
                for key in params:
                    setattr(pattern.params, key, params[key])
                pattern.prepareSegments(self.led_config)
                pattern.initialize()

                # Animate pattern to created cached colors
                print("Caching pattern %s of type %s" % (pattern_index, type(pattern).__name__))
                cached_pattern = CachedPattern()
                cached_pattern.prepareSegments(self.led_config)
                cached_pattern.initialize()
                duration = 0
                delta = 1.0 / self.animation_rate
                while duration <= max_pattern_duration:
                    pattern.animate(delta)
                    segment_colors = []
                    for segment in pattern.segments:
                        segment_colors.append(deepcopy(segment.colors))
                    cached_pattern.colors_timeseries.append(segment_colors)
                    duration += delta

                # Add to cache and sync
                self.cache[pattern_index] = cached_pattern
                self.cache.sync()
                patterns.append(cached_pattern)
            else:
                pattern = self.cache[pattern_index]
                patterns.append(pattern)
        
        return patterns
