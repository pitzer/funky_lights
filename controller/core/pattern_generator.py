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
        self.pattern_manager = PatternManager(pattern_config.DEFAULT_CONFIG, args)
        self.objects_ids = []
        self.pattern_selectors_leds = {}
        self.pattern_selectors_solids = {}
        self.pattern_mixes = {}

        # Pattern selectors
        for o in config['objects']:
            object_id = o['id']
            self.objects_ids.append(object_id)

            # LED patterns
            if 'led_config' in o.keys():
                led_config_file = open(o['led_config'])
                led_config = json.load(led_config_file)
                selector = PatternSelector(
                    self.pattern_manager, led_config, None, args)
                selector.current_pattern_id = o['led_pattern_id']
                self.pattern_selectors_leds[object_id] = selector

            # Solid patterns
            if 'solid_config' in o.keys():
                solid_config_file = open(o['solid_config'])
                solid_config = json.load(solid_config_file)
                selector = PatternSelector(
                    self.pattern_manager, solid_config, None, args)
                selector.current_pattern_id = o['solid_pattern_id']
                self.pattern_selectors_solids[object_id] = selector

        self._LOG_RATE = 1.0


    def update_pattern_selection(self, animation_time):
        for object_id in self.objects_ids:
            if object_id in self.pattern_selectors_leds:
                selector = self.pattern_selectors_leds[object_id]
                selector.update(animation_time)

            if object_id in self.pattern_selectors_solids:
                selector = self.pattern_selectors_solids[object_id]
                selector.update(animation_time)


    async def update_segments(self):
        led_segments = {}
        solid_segments = {}
        for object_id in self.objects_ids:
            if object_id in self.pattern_selectors_leds:
                selector = self.pattern_selectors_leds[object_id]
                mixer = selector.pattern_mix
                await mixer.update()
                led_segments[object_id] = mixer.segments

            if object_id in self.pattern_selectors_solids:
                selector = self.pattern_selectors_solids[object_id]
                mixer = selector.pattern_mix
                await mixer.update()
                solid_segments[object_id] = mixer.segments

        return led_segments, solid_segments


    async def run(self):
        await self.pattern_manager.initialize_patterns()
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
            self.update_pattern_selection(cur_animation_time)
            await self.pattern_manager.animate(animation_time_delta)
            led_segments, solid_segments =  await self.update_segments()
            self.pattern_manager.clear_selected_patterns()

            # Update results future for processing by IO
            self.result.set_result((self.objects_ids, led_segments, solid_segments))
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
