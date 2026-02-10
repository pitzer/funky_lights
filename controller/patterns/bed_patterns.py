from patterns.pattern import Pattern
from patterns.pattern import PatternUV, UVGrid
from .utils import expandKeys
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
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.color

    async def animate(self, delta):
        return
    

class BreathingColorPattern(StaticColorPattern):
    def __init__(self):
        super().__init__()
        self.params.period_s = 5.0
        self.params.amplitude_pct = 0.5
        self.params.vary_segments = True
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
        phase = 0
        for s in all_segments:
            segment = self.segments[s.segment_index]
            rad = self.breath_time * math.pi * 2 / period + phase
            if self.params.type == "ramp_and_hold":
                if rad % (2 * math.pi) < math.pi / 4:
                    brightness = 1.0 + math.sin(rad * 2) * self.params.amplitude_pct
                elif rad % (2 * math.pi) < math.pi:
                    brightness = 1.0 + self.params.amplitude_pct
                elif rad % (2 * math.pi) < 5 * math.pi / 4:
                    brightness = 1.0 + math.sin((rad - math.pi) * 2 + math.pi / 2) * self.params.amplitude_pct
                else:
                    brightness = 1.0
            elif self.params.type == "sine":
                brightness = 1.0 + math.sin(rad) * self.params.amplitude_pct
            else:
                raise ValueError(f"Invalid breathing pattern type: {self.params.type}")
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(np.array(self.params.color) * brightness, 0, 255)
            if self.params.vary_segments:
                phase += 3.0
                period += self.params.period_s / 20.0

class RipplePattern(PatternUV):
    def __init__(self, width=100, height=100):
        super().__init__()
        # Frequency of color change (in Hz)
        self.fps = 40
        self.offset = 0
        self.width = width
        self.height = height
    
    def initialize(self):
        self.generateUVCoordinates(self.width, self.height)
        self.grid = UVGrid(self.width, self.height)
        self.cumulative_delta = 1000  # set to an arbitrary high value
        self.current_color_index = 0
        self.spectrum = np.arange(0, 1, 1/self.width)        
        self.applyGrid(self.grid)  
    
    async def animate(self, delta):
        self.cumulative_delta += delta
        if self.cumulative_delta < 1 / self.fps:
            return

        self.spectrum = np.roll(self.spectrum, 1)  
        self.applyGrid(self.grid)
        self.cumulative_delta = 0

class CircuitPattern(Pattern):
    def __init__(self):
        super().__init__()
        self.params.period_s = 20.0
        self.params.amplitude_pct = 0.5
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
            for i in led_range:
                distance = abs(current_led - pulse_position)
                if distance > total_leds / 2:
                    distance = total_leds - distance
                if distance < self.params.pulse_width:
                    pulse_intensity = (1.0 - distance / self.params.pulse_width) * self.params.amplitude_pct
                    brightness = pulse_intensity
                else:
                    brightness = 0.0
                ctrl_segment.colors[i] = np.clip(np.array(self.params.color) * brightness, 0, 255)
                current_led += 1




class MotionPattern(Pattern):
    """
    Motion pattern implementing:
    - Headboard: Ultra-slow breath (16-20s cycle, ±4-6% brightness)
    - Bed Posts: Orbital circuit (18-24s cycle, clockwise processional)
    - Bench: Center-outward ripple (8-10s cycle, ±10%)
    - Cage: Subtle heartbeat (double pulse with rest)
    """
    def __init__(self):
        super().__init__()
        # Headboard parameters
        self.params.headboard_breath_period = 18.0  # 16-20 seconds
        self.params.headboard_amplitude = 0.50  # ±50% brightness
        self.params.headboard_color = np.array([48, 44, 96]) * 2.0  # Indigo / Blue-Violet
        
        # Bed posts orbital circuit parameters
        self.params.orbital_period = 21.0  # 18-24 seconds per circuit
        self.params.orbital_brightness_delta = 0.5  # ±50% brightness pulse
        self.params.post_color = np.array([72, 36, 94]) * 2.0  # Deep Plum
        
        # Bench ripple parameters
        self.params.bench_ripple_period = 9.0  # 8-10 seconds
        self.params.bench_amplitude = 0.50  # ±10%
        self.params.bench_color = np.array([98, 56, 130]) * 1.5 # Bruised Violet
        
        # Cage heartbeat parameters
        self.params.cage_pulse_duration = 1.5  # 1.5 seconds per pulse
        self.params.cage_pause_duration = 4.5  # 4-5 seconds pause
        self.params.cage_amplitude = 0.50  # ±50% brightness
        self.params.cage_color = np.array([42, 18, 58]) * 2.0  # Abyss Purple
        
        self.time = 0
        
    def initialize(self):
        # Initialize all segments to their base colors
        # Headboard
        for s in headboard_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.headboard_color
        
        # Cage
        for s in cage_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.cage_color
        
        # Center (bench)
        for s in center_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.bench_color
        
        # Front (bench continuation)
        for s in front_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = self.params.bench_color
    
    async def animate(self, delta):
        self.time += delta
        
        # 1. Headboard - Ultra-slow breath (sine wave)
        self._animate_headboard_breath()
        
        # 2. Bed Posts - Orbital circuit (clockwise processional)
        self._animate_orbital_circuit()
        
        # 3. Bench - Center-outward ripple
        self._animate_bench_ripple()
        
        # 4. Cage - Subtle heartbeat (double pulse)
        self._animate_cage_heartbeat()
    
    def _animate_headboard_breath(self):
        """Ultra-slow sine wave breath on headboard"""
        period = self.params.headboard_breath_period
        rad = (self.time * 2 * math.pi) / period
        brightness = 1.0 + math.sin(rad) * self.params.headboard_amplitude
        for s in headboard_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(
                    np.array(self.params.headboard_color) * brightness, 0, 255)
    
    def _animate_orbital_circuit(self):
        """Clockwise processional circuit around bed posts"""
        period = self.params.orbital_period
        # Progress through the circuit (0 to 1)
        progress = (self.time % period) / period

        # Define the orbital path: RL (rear-left) -> RR -> FR -> FL -> back to RL
        # Each post has 66 LEDs (0-23 cage, 24-65 center/front)
        # We'll create a smooth pulse that travels around
        post_order = [
            (POST_RL_SEGMENT, 24, 66),  # Rear Left (start at LED 24, non-cage)
            (POST_RR_SEGMENT, 24, 66),  # Rear Right
            (POST_FR_SEGMENT, 66, 108),  # Front Right
            (POST_FL_SEGMENT, 66, 108),  # Front Left
        ]
        
        total_leds_in_circuit = sum(end - start for _, start, end in post_order)
        pulse_position = progress * total_leds_in_circuit
        pulse_width = 15  # Width of the brightness pulse in LEDs
        current_led = 0
        for seg_idx, start_offset, end_offset in post_order:
            segment = self.segments[seg_idx]
            num_leds = end_offset - start_offset
            
            for i in range(start_offset, end_offset):
                # Calculate distance from pulse center
                distance = abs(current_led - pulse_position)
                # Handle wraparound
                if distance > total_leds_in_circuit / 2:
                    distance = total_leds_in_circuit - distance
                
                # Calculate brightness based on distance from pulse
                if distance < pulse_width:
                    pulse_intensity = (1.0 - distance / pulse_width) * self.params.orbital_brightness_delta
                    brightness = pulse_intensity
                else:
                    brightness = 0.0
                segment.colors[i] = np.clip(
                    np.array(self.params.post_color) * brightness, 0, 255)
                current_led += 1

    def _animate_bench_ripple(self):
        """Center-outward ripple on bench segments"""
        ripple_time = self.time % 5.0

        for s in front_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):









                
                brightnesses = rippleBrightnesses(
                    num_leds=s.num_leds,
                    center_index=s.num_leds / 2.0,
                    time=ripple_time,
                    period=self.params.bench_ripple_period / 10.0,
                    speed=10.0,  # Speed of ripple expansion in LEDs/second
                    decay_time=1.0,  # Time for ripple to decay by 50%
                    decay_leds=10.0  # Number of LEDs over which ripple decays to 50%
                )


                segment.colors[i] = np.clip(
                    np.array(self.params.bench_color) * (1.0 - brightnesses[i - s.offset]), 0, 255)

    
    def _animate_cage_heartbeat(self):
        """Double pulse heartbeat pattern on cage"""
        # Total cycle: pulse (1.5s) + pulse (1.5s) + pause (4.5s) = 7.5s
        pulse_duration = self.params.cage_pulse_duration
        pause_duration = self.params.cage_pause_duration
        cycle_time = 2 * pulse_duration + pause_duration
        
        t = self.time % cycle_time
        
        # Determine which phase we're in
        if t < pulse_duration:
            # First pulse - rise and fall
            pulse_progress = t / pulse_duration
            brightness = 1.0 + math.sin(pulse_progress * math.pi) * self.params.cage_amplitude
        elif t < 2 * pulse_duration:
            # Second pulse - rise and fall
            pulse_progress = (t - pulse_duration) / pulse_duration
            brightness = 1.0 + math.sin(pulse_progress * math.pi) * self.params.cage_amplitude
        else:
            # Pause phase
            brightness = 1.0
        
        for s in cage_segments:
            segment = self.segments[s.segment_index]
            for i in range(s.offset, s.offset + s.num_leds):
                segment.colors[i] = np.clip(
                    np.array(self.params.cage_color) * brightness, 0, 255)

