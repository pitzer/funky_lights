import asyncio
import json
import time

from core.pattern_manager import PatternManager
from core.pattern_selector import PatternSelector
from patterns import pattern_config


class PatternGenerator:
    def __init__(self, args, config):
        self.args = args
        self.config = config
        self.result = asyncio.Future()
        self.object_ids = []
        self.pattern_managers = {}
        self.pattern_selectors = {}

        for o in config['objects']:
            object_id = o['id']
            if not 'led_config' in o.keys():
                continue

            self.object_ids.append(object_id)
                            
            led_config_file = open(o['led_config'])
            led_config = json.load(led_config_file)

            pattern_manager = PatternManager(pattern_config.DEFAULT_CONFIG, led_config, args)
            self.pattern_managers[object_id] = pattern_manager

            selector = PatternSelector(
                pattern_manager, led_config, None, args)
            selector.current_pattern_id = o['led_pattern_id']
            self.pattern_selectors[object_id] = selector

        self._LOG_RATE = 1.0


    async def run(self):
        for object_id in self.object_ids:
            await self.pattern_managers[object_id].initialize_patterns()
            await self.pattern_selectors[object_id].initialize()

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
            
            # Pattern animation pipeline
            led_segments = {}
            for object_id in self.object_ids:
                selector = self.pattern_selectors[object_id]
                patterns = selector.update(cur_animation_time)
                
                manager = self.pattern_managers[object_id] 
                manager.update_pattern_selection(patterns)
                await manager.animate(animation_time_delta)

                mixer = selector.pattern_mix
                segments = await mixer.update()
                led_segments[object_id] = segments

            # Update results future for processing by IO
            self.result.set_result(led_segments)
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
