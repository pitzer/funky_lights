import asyncio
import functools
import json
import lpminimk3
import time
import serial
import numpy as np
import websockets

from core.pattern_cache import PatternCache
    

class PatternManager:
    def __init__(self, pattern_config, led_config, args):
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.args = args

        # Pattern cache
        self.enable_cache = args.enable_cache
        self.cached_patterns = []
        if args.enable_cache:
            self.pattern_cache = PatternCache(pattern_config, led_config, args)
        else:
            self.pattern_cache = None

        # Dict of all patterns
        self.patterns = {}

        # List of pattern ids per group
        self.pattern_rotation = list(pattern_config.rotation.keys())
        self.pattern_manual = list(pattern_config.manual.keys())
        self.pattern_effects = list(pattern_config.special_effects.keys())
        self.pattern_eyes = list(pattern_config.eyes.keys())
        self.pattern_all = [pattern_id for pattern_id, _ in self.all_patterns_configs()]
        self.pattern_selected = []
   
    def all_patterns_configs(self):
        for d in self.pattern_config:
            for pattern_id, config in d.items():
                yield pattern_id, config


    async def initialize_patterns(self):
        # Initialize all patterns
        for pattern_id, (cls, params) in self.all_patterns_configs():
            pattern = cls()
            for key in params:
                setattr(pattern.params, key, params[key])
            pattern.prepareSegments(self.led_config)
            pattern.initialize()
            self.patterns[pattern_id] = pattern  
        
        # Initialize cached patterns
        if self.args.enable_cache:
            await self.pattern_cache.initialize_patterns()

        # Initialize pattern mix
        self.pattern_mix.prepareSegments(self.led_config)
        self.pattern_mix.initialize()


    def _maybe_cached_pattern(self, pattern_id):
        if self.pattern_cache and pattern_id in self.pattern_cache.patterns:
            return self.pattern_cache.patterns[pattern_id]
        else:
            return self.patterns[pattern_id]
    

    def pattern(self, pattern_id):
        return self._maybe_cached_pattern(pattern_id)


    def reset_pattern(self, pattern_id):
        self.pattern(pattern_id).reset()


    def select_patterns(self, pattern_ids):
        self.pattern_selected.append(pattern_ids)
    

    def clear_selected_patterns(self):
        self.pattern_selected.clear()


    async def animate(self, delta):
        for pattern_id in self.pattern_selected:
            await self.pattern(pattern_id).animate(delta)