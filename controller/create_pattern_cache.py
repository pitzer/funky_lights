import argparse
import json
import asyncio

from core.pattern_cache import PatternCache
from patterns import pattern_config


async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--config", type=argparse.FileType('r'), default="/home/pi/impossible_dialogue/config/head_config.json", 
                        help="LED config file")
    parser.add_argument("-a", "--animation_rate", type=int,
                        default=20, help="The target animation rate in Hz")
    parser.add_argument("-f", "--force_update", action='store_true',
                        help="Forces update of all cached patterns. Otherwise will only update missing or incomplete patterns.")
    parser.add_argument("-m", "--max_cached_pattern_duration", type=int, default=60,
                        help="The maximum duration a pattern is cached for")
    args = parser.parse_args()
    config = json.load(args.config)

    for o in config['objects']:
        object_id = o['id']
        if not 'led_config' in o.keys():
            continue
        led_config_file = open(o['led_config'])
        led_config = json.load(led_config_file)
        cache = PatternCache(pattern_config.DEFAULT_CONFIG,
                            led_config, args.animation_rate)

        # Initialize all patterns
        patterns = {}
        for d in pattern_config.DEFAULT_CONFIG:
            for pattern_id, (cls, params) in d.items():
                pattern = cls()
                for key in params:
                    setattr(pattern.params, key, params[key])
                pattern.prepareSegments(led_config)
                pattern.initialize()
                patterns[pattern_id] = pattern
        print(object_id)
        await cache.build_cache(patterns, args.max_cached_pattern_duration, args.force_update)

asyncio.run(main())
