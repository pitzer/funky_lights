import argparse
import json
import asyncio
import os
from aiofile import async_open

from core.pattern_cache import PatternCache
from patterns import pattern_config


class PatternCodeGenerator:
    def __init__(self, pattern_config, led_config, animation_rate, code_folder):
        self.patterns = {}
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.animation_rate = animation_rate
        self.code_folder = code_folder

    def patterns_for_caching(self):
        for d in self.pattern_config:
            for pattern_id, _ in d.items():
                yield pattern_id

    def code_file_path(self, pattern_id):
        return os.path.join(self.code_folder, str(pattern_id) + '_pattern.cpp')

    async def generate_code_for_pattern(self, pattern, pattern_id, max_pattern_duration):
        delta = 1.0 / self.animation_rate
        num_animation_steps = int(max_pattern_duration * self.animation_rate)
        code_file = self.code_file_path(pattern_id)

        print("Generating code pattern %s of type %s" %
              (pattern_id, type(pattern).__name__))

        segment_data = ", ".join(str(len(s.colors)) for s in pattern.segments)

        pixel_data = ""
        for animation_index in range(num_animation_steps):
            await pattern.animate(delta)
            for segment in pattern.segments:
                for color in segment.colors:
                    pixel_data += "{{ {}, {}, {} }}, ".format(
                        color[0], color[1], color[2])
            pixel_data += "\n    "

        num_segments = len(pattern.segments)
        code = f"""
#include \"cached_pattern.h\"

static const uint32_t {pattern_id}_num_leds_per_segment[] = {{ {segment_data} }};
static const PATTERN_ATTRIBUTE_LARGE_CONST CRGB {pattern_id}_pixels[] = {{
    {pixel_data}
}};

constexpr cached_pattern_t {pattern_id} = {{
    .color_ordering = WS2811_RGB,
    .animation_steps = {num_animation_steps},
    .num_segments = {num_segments},
    .num_leds_per_segment = {pattern_id}_num_leds_per_segment,
    .num_pixels = sizeof({pattern_id}_pixels) / sizeof(CRGB),
    .pixels = {pattern_id}_pixels,
}};
CHECK_CACHED_PATTERN({pattern_id});"""

        # Write code file
        async with async_open(code_file, 'w', encoding='utf-8') as afp:
            await afp.write(code)

    async def generate_code(self, patterns, max_pattern_duration):
        for pattern_id in self.patterns_for_caching():
            pattern = patterns[pattern_id]
            await self.generate_code_for_pattern(pattern, pattern_id, max_pattern_duration)


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--led_config", type=argparse.FileType('r'),
                        default="../config/led_config_bed.json", help="LED config file")
    parser.add_argument("-a", "--animation_rate", type=int,
                        default=10, help="The target animation rate in Hz")
    parser.add_argument("-f", "--force_update", action='store_true',
                        help="Forces update of all cached patterns. Otherwise will only update missing or incomplete patterns.")
    parser.add_argument("-m", "--max_cached_pattern_duration", type=int, default=30,
                        help="The maximum duration a pattern is cached for")
    parser.add_argument("-c", "--code_folder", type=str, default="/Users/pitzer/Documents/workspace/funkled/is_bed/src/cached_patterns",
                        help="The folder to output code files")
    args = parser.parse_args()
    led_config = json.load(args.led_config)

    generator = PatternCodeGenerator(pattern_config.BED_CONFIG,
                                     led_config, args.animation_rate, 
                                     args.code_folder)

    # Initialize all patterns
    patterns = {}
    for d in pattern_config.BED_CONFIG:
        for pattern_id, (cls, params) in d.items():
            pattern = cls()
            for key in params:
                setattr(pattern.params, key, params[key])
            pattern.prepareSegments(led_config)
            pattern.initialize()
            patterns[pattern_id] = pattern

    await generator.generate_code(patterns, args.max_cached_pattern_duration)

asyncio.run(main())
