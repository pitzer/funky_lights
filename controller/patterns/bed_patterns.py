from patterns.pattern import Pattern
from patterns.pattern import PatternUV, UVGrid
from .utils import expandKeys, scaleColors
from collections import namedtuple
import math
import numpy as np
from copy import deepcopy


ZoneSegment = namedtuple(
    'ZoneSegment', ['name', 'segment_index', 'offset', 'num_leds', 'circuit_dir'])

POST_RL_SEGMENT = 0
POST_RR_SEGMENT = 1
POST_FL_SEGMENT = 2
POST_FR_SEGMENT = 3
HEADBOARD_SEGMENT = 4

CIRCUIT_DIR_STRAIGHT = 0
CIRCUIT_DIR_REVERSE = 1
CIRCUIT_DIR_NONE = 2

headboard_segments = [
    ZoneSegment("Bottom Left"       , HEADBOARD_SEGMENT, 0 , 10 , CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Cross Bottom Left" , HEADBOARD_SEGMENT, 10 , 8 , CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cross Top Right"   , HEADBOARD_SEGMENT, 68 , 8 , CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Top Right"         , HEADBOARD_SEGMENT, 58 , 10, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Right"             , HEADBOARD_SEGMENT, 44 , 14, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Bottom Right"      , HEADBOARD_SEGMENT, 34 , 10, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cross Bottom Right", HEADBOARD_SEGMENT, 26 , 8 , CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cross Top Left"    , HEADBOARD_SEGMENT, 84 , 8 , CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Top Left"          , HEADBOARD_SEGMENT, 92 , 10, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Left"              , HEADBOARD_SEGMENT, 102, 14, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Bottom Middle"     , HEADBOARD_SEGMENT, 18 , 8 , CIRCUIT_DIR_NONE),
    ZoneSegment("Top Middle"        , HEADBOARD_SEGMENT, 76 , 8 , CIRCUIT_DIR_NONE),
]

cage_segments = [
    ZoneSegment("Cage RL Outer", POST_RL_SEGMENT, 0 , 12, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Cage RL Inner", POST_RL_SEGMENT, 12, 12, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Cage RR Inner", POST_RR_SEGMENT, 12, 12, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cage RR Outer", POST_RR_SEGMENT, 0 , 12, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cage FR Outer", POST_FR_SEGMENT, 0 , 12, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Cage FR Inner", POST_FR_SEGMENT, 12, 12, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Cage FL Inner", POST_FL_SEGMENT, 12, 12, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Cage FL Outer", POST_FL_SEGMENT, 0 , 12, CIRCUIT_DIR_REVERSE),
]

front_segments = [
    ZoneSegment("Front FL Outer", POST_FL_SEGMENT, 24, 21, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Front FL Inner", POST_FL_SEGMENT, 45, 21, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Front FR Inner", POST_FR_SEGMENT, 45, 21, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Front FR Outer", POST_FR_SEGMENT, 24, 21, CIRCUIT_DIR_REVERSE),
]

center_segments = [
    ZoneSegment("Center RL Outer", POST_RL_SEGMENT, 45, 21, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Center RL Inner", POST_RL_SEGMENT, 24, 21, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Center RR Inner", POST_RR_SEGMENT, 24, 21, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Center RR Outer", POST_RR_SEGMENT, 45, 21, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Center FR Outer", POST_FR_SEGMENT, 87, 21, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Center FR Inner", POST_FR_SEGMENT, 66, 21, CIRCUIT_DIR_REVERSE),
    ZoneSegment("Center FL Inner", POST_FL_SEGMENT, 66, 21, CIRCUIT_DIR_STRAIGHT),
    ZoneSegment("Center FL Outer", POST_FL_SEGMENT, 87, 21, CIRCUIT_DIR_STRAIGHT),
]

all_segments = headboard_segments + cage_segments + front_segments + center_segments

class ZonedPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.pattern_defs = []
        self.patterns = {}

    def prepareSegments(self, led_config):
        # Create our own segments
        super().prepareSegments(led_config)
    
    def getSegments(self):
        for pattern in self.patterns:
            for segment in pattern.getSegments():
                yield segment

    def initialize(self):
        # Create the sub-patterns
        # If a key is of the form "zone1+zone2", split it and apply the pattern to both zones
        self.params.pattern_defs = expandKeys(self.params.pattern_defs, ["headboard", "center", "front", "cage"])
        for zone, (cls, params) in self.params.pattern_defs.items():
            pattern = cls()
            for key in params:
                setattr(pattern.params, key, params[key])
            pattern.segments = deepcopy(self.segments)
            pattern.initialize()
            self.patterns[zone] = pattern

    async def animate(self, delta):
        mapping = [("headboard", headboard_segments),
                   ("center", center_segments),
                   ("front", front_segments),
                   ("cage", cage_segments)]
        # copy the color values, zone by zone
        for zone, segments in mapping:
            if zone in self.patterns:
                await self.patterns[zone].animate(delta)
                for s in segments:
                    segment_dst = self.segments[s.segment_index]
                    segment_src = self.patterns[zone].segments[s.segment_index]
                    start = s.offset
                    end = s.offset + s.num_leds
                    segment_dst.colors[start:end] = segment_src.colors[start:end]
        

class StaticColorPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.color = (255, 255, 255)
        
    def initialize(self):
        for s in all_segments:
            segment = self.segments[s.segment_index]
            segment.colors[s.offset:s.offset + s.num_leds] = self.params.color

    async def animate(self, delta):
        return
    

class BreathingColorPattern(StaticColorPattern):
    def __init__(self):
        super().__init__()
        self.params.period_s = 5.0
        self.params.amplitude_pct = 1.0
        self.params.vary_segments = False
        self.params.type = "sine"
        self.params.color = (255, 255, 255)
        self.breath_time = 0

    def initialize(self):
        super().initialize()

    def clip(value, min_val, max_val):
        """Clips a value within a specified range."""
        return max(min_val, min(value, max_val))

    async def animate(self, delta):
        self.breath_time += delta

        # For each segment, we create use a slightly different period and starting
        # phase to create a more dynamic effect.
        period = float(self.params.period_s)
        phase_offset = 0
        for segment in self.segments:
            phase = (self.breath_time * math.pi * 2 / period + phase_offset) % (2 * math.pi)
            if self.params.type == "ramp_and_hold":
                if phase < math.pi / 2:
                    brightness = (1.0 + math.sin(phase * 2 - np.pi / 2)) / 2.0
                elif phase < math.pi:
                    brightness = 1.0
                elif phase < 3 * math.pi / 2:
                    brightness = (1.0 + math.sin((phase - math.pi) * 2 + math.pi / 2)) / 2.0
                else:
                    brightness = 0.0
            elif self.params.type == "sine":
                brightness = (1.0 + math.sin(phase)) / 2.0
            elif self.params.type == "single_pulse":
                if phase < 2.0 * math.pi / 4:
                    brightness = math.sin(phase * 2) ** 2 
                else:
                    brightness = 0.0
            elif self.params.type == "double_pulse":
                if phase < 2.0 * math.pi / 3:
                    brightness = math.sin(phase * 3) ** 2 
                else:
                    brightness = 0.0
            else:
                raise ValueError(f"Invalid breathing pattern type: {self.params.type}")
            segment.colors = scaleColors(self.params.color, np.full((segment.num_leds,), brightness), self.params.amplitude_pct)
            if self.params.vary_segments:
                phase_offset += 3.0
                period += self.params.period_s / 20.0

class CircuitPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.period_s = 20.0
        self.params.amplitude_pct = 1.0
        self.params.color = (255, 255, 255)
        self.params.pulse_width = 15
        self.params.zones = ["headboard", "center", "front", "cage"]
        self.time = 0

    def initialize(self):
        pass

    async def animate(self, delta):
        self.time += delta
        period = self.params.period_s
        progress = (self.time % period) / period
        segments = []
        if "headboard" in self.params.zones:
            segments += headboard_segments
        if "center" in self.params.zones:
            segments += center_segments
        if "front" in self.params.zones:
            segments += front_segments
        if "cage" in self.params.zones:
            segments += cage_segments

        total_leds = sum(segment.num_leds for segment in segments if segment.circuit_dir != CIRCUIT_DIR_NONE)
        pulse_position = progress * total_leds
        current_led = 0
        for segment in segments:
            ctrl_segment = self.segments[segment.segment_index]
            if segment.circuit_dir == CIRCUIT_DIR_NONE:
                continue
            if segment.circuit_dir == CIRCUIT_DIR_STRAIGHT:
                led_range = range(segment.offset, segment.offset + segment.num_leds)
            elif segment.circuit_dir == CIRCUIT_DIR_REVERSE:
                led_range = range(segment.offset + segment.num_leds - 1, segment.offset - 1, -1)

            indexes = np.arange(segment.num_leds)
            distances = np.abs(current_led + indexes - pulse_position)
            current_led += segment.num_leds
            distances[distances > total_leds / 2] = total_leds - distances[distances > total_leds / 2]
            intensities = np.clip(1.0 - distances / self.params.pulse_width, 0, 1)
            ctrl_segment.colors[led_range] = scaleColors(np.array(self.params.color), intensities, self.params.amplitude_pct)



