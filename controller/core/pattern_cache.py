from patterns.pattern import Pattern
from aiofile import async_open
import hashlib
import json
import math
import os
import pickle


def hash_led_config(led_config):
    led_config_bytes = bytearray(json.dumps(led_config, sort_keys=True).encode('ascii'))
    return hashlib.sha256(led_config_bytes).hexdigest()


def cache_pattern_folder(led_config_hash, pattern_id): 
    return os.path.join(os.path.expanduser('~'), 'pattern_cache', str(led_config_hash), pattern_id)


def cache_file_path(led_config_hash, pattern_id, animation_index):
    animation_index_low = math.floor(animation_index / 1000) * 1000
    animation_index_high = math.floor(animation_index / 1000 + 1) * 1000 - 1
    animation_index_folder = '%06d-%06d' % (animation_index_low, animation_index_high)
    filename = '%06d.p' % animation_index
    return os.path.join(
        cache_pattern_folder(led_config_hash, pattern_id), animation_index_folder, filename)


def cache_index_path(led_config_hash, pattern_id):
    return os.path.join(cache_pattern_folder(led_config_hash, pattern_id), 'index.json')


class CachedPattern(Pattern):
    def __init__(self, led_config_hash, pattern_id, num_animation_steps):
        super().__init__()
        self.led_config_hash = led_config_hash
        self.pattern_id = pattern_id
        self.num_animation_steps = num_animation_steps
        self.current_animation_index = 0
        
    def reset(self):
        self.current_animation_index = 0

    def initialize(self):
        index_file = cache_index_path(self.led_config_hash, self.pattern_id)
        with open(index_file, 'r') as f:
            cache_index = json.load(f)
            self.num_animation_steps = cache_index["animation_steps"]
        
    async def animate(self, delta):
        cache_file = cache_file_path(
            self.led_config_hash, self.pattern_id, self.current_animation_index)
        
        async with async_open(cache_file, 'rb') as afp:
            bytes = await afp.read()
            segment_colors = pickle.loads(bytes)
            for i, segment in enumerate(self.segments):
                segment.colors = segment_colors[i]

        self.current_animation_index = (self.current_animation_index + 1) % self.num_animation_steps


class PatternCache:
    def __init__(self, pattern_config, led_config, animation_rate):
        self.patterns = {}
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.animation_rate = animation_rate
        self.led_config_hash = hash_led_config(led_config)
        print("LED config hash: " + str(self.led_config_hash))

    def patterns_for_caching(self):
        for d in self.pattern_config:
            for pattern_id, _ in d.items():
                yield pattern_id

    async def initialize_patterns(self):
        self.patterns = {}
        for pattern_id in self.patterns_for_caching():
            index_file = cache_index_path(self.led_config_hash, pattern_id)
            if not os.path.exists(index_file):
                print("WARNING: no cache found for pattern %s" % pattern_id)
                continue
            with open(index_file, 'r') as f:
                cache_index = json.load(f)
                num_animation_steps = cache_index["animation_steps"]
                cached_pattern = CachedPattern(self.led_config_hash, pattern_id, num_animation_steps)
                cached_pattern.prepareSegments(self.led_config)
                cached_pattern.initialize()
                cached_pattern.params.include_segments = cache_index["include_segments"]
                cached_pattern.params.exclude_segments = cache_index["exclude_segments"]
                cached_pattern.params.led_masks = cache_index["segment_masks"]
                self.patterns[pattern_id] = cached_pattern

    async def build_cache_for_pattern(self, pattern, pattern_id, max_pattern_duration, force_update):
        delta = 1.0 / self.animation_rate
        num_animation_steps = int(max_pattern_duration * self.animation_rate)
        index_file = cache_index_path(self.led_config_hash, pattern_id)
        if (force_update or not os.path.exists(index_file)):
            print("Caching pattern %s of type %s" % (pattern_id, type(pattern).__name__))
            for animation_index in range(num_animation_steps):
                await pattern.animate(delta)
                segment_colors = []
                for segment in pattern.segments:
                    segment_colors.append(segment.colors)

                cache_file = cache_file_path(
                    self.led_config_hash, pattern_id, animation_index)
                os.makedirs(os.path.dirname(cache_file), exist_ok=True)
                async with async_open(cache_file, 'wb') as afp:
                    bytes = pickle.dumps(segment_colors)
                    await afp.write(bytes)
            
            # Write cache index file
            with open(index_file, 'w', encoding='utf-8') as f:
                cache_index = {
                    "animation_steps": num_animation_steps,
                    "include_segments": pattern.params.include_segments,
                    "exclude_segments": pattern.params.exclude_segments,
                    "segment_masks": pattern.params.segment_masks,
                }
                json.dump(cache_index, f, ensure_ascii=False, indent=4)

    async def build_cache(self, patterns, max_pattern_duration, force_update=False):
        for pattern_id in self.patterns_for_caching():
            pattern = patterns[pattern_id]
            await self.build_cache_for_pattern(pattern, pattern_id, max_pattern_duration, force_update)
