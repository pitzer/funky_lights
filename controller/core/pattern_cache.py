from math import floor
from patterns.pattern import Pattern
from aiofile import async_open
from copy import deepcopy
import hashlib
import json
import math
import os
import pickle


def hash_led_config(led_config):
    led_config_bytes = bytearray(json.dumps(led_config, sort_keys=True).encode('ascii'))
    return hashlib.sha256(led_config_bytes).hexdigest()


def cache_pattern_folder(led_config_hash, pattern_index): 
    return os.path.join('/tmp', 'pattern_cache', str(led_config_hash), str(pattern_index))


def cache_file_path(led_config_hash, pattern_index, animation_index):
    animation_index_low = math.floor(animation_index / 1000) * 1000
    animation_index_high = math.floor(animation_index / 1000 + 1) * 1000 - 1
    animation_index_folder = '%06d-%06d' % (animation_index_low, animation_index_high)
    filename = '%06d.p' % animation_index
    return os.path.join(
        cache_pattern_folder(led_config_hash, pattern_index), animation_index_folder, filename)


class CachedPattern(Pattern):
    def __init__(self, num_animation_steps, led_config_hash, pattern_index):
        super().__init__()
        self.num_animation_steps = num_animation_steps
        self.led_config_hash = led_config_hash
        self.pattern_index = pattern_index
        self.current_animation_index = 0

    async def animate(self, delta):
        cache_file = cache_file_path(
            self.led_config_hash, self.pattern_index, self.current_animation_index)
        async with async_open(cache_file, 'rb') as afp:
            bytes = await afp.read()
            segment_colors = pickle.loads(bytes)
            for i, segment in enumerate(self.segments):
                segment.colors = segment_colors[i]

        self.current_animation_index = (self.current_animation_index + 1) % self.num_animation_steps


class PatternCache:
    def __init__(self, pattern_config, led_config, args):
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.animation_rate = args.animation_rate
        self.led_config_hash = hash_led_config(led_config)
        print("LED config hash: " + str(self.led_config_hash))

    async def build_cache(self, patterns, max_pattern_duration):
        cached_patterns = []
        delta = 1.0 / self.animation_rate
        num_animation_steps = int(max_pattern_duration * self.animation_rate)
        
        for pattern_index, _ in enumerate(self.pattern_config):
            pattern = patterns[pattern_index]

            # Animate pattern and cache color arrays for each step
            print("Caching pattern %d of type %s" % (pattern_index, type(pattern).__name__))
            cached_pattern = CachedPattern(num_animation_steps, self.led_config_hash, pattern_index)
            cached_pattern.prepareSegments(self.led_config)
        
            # Update only patterns that are not already cached
            if not os.path.exists(cache_pattern_folder(self.led_config_hash, pattern_index)):
                for animation_index in range(num_animation_steps):
                    await pattern.animate(delta)
                    segment_colors = []
                    for segment in pattern.segments:
                        segment_colors.append(deepcopy(segment.colors))

                    cache_file = cache_file_path(
                        self.led_config_hash, pattern_index, animation_index)
                    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                    async with async_open(cache_file, 'wb') as afp:
                        bytes = pickle.dumps(segment_colors)
                        await afp.write(bytes)

            # Add to cache and sync
            cached_patterns.append(cached_pattern)

        return cached_patterns
