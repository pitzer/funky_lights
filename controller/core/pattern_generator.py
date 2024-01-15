import asyncio
import json
import time

from core.pattern_selector import PatternSelector
from patterns import pattern_config


class PatternGenerator:
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.result = asyncio.Future()
        self.objects_ids = []
        self.pattern_selectors = {}
        self.pattern_mixes = {}

        # Pattern selectors
        for o in config['objects']:
            object_id = o['id']
            self.objects_ids.append(object_id)
            led_config_file = open(o['led_config'])
            led_config = json.load(led_config_file)
            pattern_selector = PatternSelector(
                pattern_config.DEFAULT_CONFIG, led_config, None, args)
            pattern_selector.current_pattern_id = o['pattern_id']
            self.pattern_selectors[object_id] = pattern_selector

            if args.enable_pattern_mix_publisher:
                self.pattern_mixes[object_id] = asyncio.Future()

        self._LOG_RATE = 1.0


    async def initializePatterns(self):
        for pattern_selector in self.pattern_selectors.values():
            await pattern_selector.initializePatterns()

    async def tick(self, pattern, delta):
        await pattern.animate(delta)

    async def run(self):
        await self.initializePatterns()
        animation_time_delta = 1.0 / self.args.animation_rate
        cur_animation_time = time.time()
        next_animation_time = cur_animation_time + animation_time_delta
        prev_log_time = cur_animation_time
        log_counter = 0

        while True:
            cur_animation_time = next_animation_time
            next_animation_time = cur_animation_time + animation_time_delta

            # Skip a frame if falling too far behind
            if time.time() > next_animation_time:
                print("Falling behind. Skipping frame.")
                continue
            
            # Animate patterns
            segments = {}
            for object_id in self.objects_ids:
                pattern_selector = self.pattern_selectors[object_id]

                # Update pattern selection
                pattern = pattern_selector.update(cur_animation_time)

                # Update results future for processing by IO
                if self.args.enable_pattern_mix_publisher:
                    pattern_mix = self.pattern_mixes[object_id]
                    pattern_mix.set_result(
                        pattern_selector.get_pattern_mix())
                    pattern_mix = asyncio.Future()

                # Process animation
                await self.tick(pattern, animation_time_delta)

                # Stash results in a dictionary
                segments[object_id] = pattern.segments

            # Update results future for processing by IO
            self.result.set_result(segments)
            self.result = asyncio.Future()

            # Output update rate to console
            log_counter += 1
            cur_log_time = time.time()
            log_time_delta = cur_log_time - prev_log_time
            if log_time_delta > 1.0 / self._LOG_RATE:
                print("Animation FPS: %.1f" % (log_counter / log_time_delta))
                log_counter = 0
                prev_log_time = cur_log_time

            # Sleep for the remaining time
            await asyncio.sleep(max(0, next_animation_time - time.time()))
