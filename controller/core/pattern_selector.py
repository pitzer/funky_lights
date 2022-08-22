import asyncio
import functools
import json
import lpminimk3
import time
import serial
import numpy as np
import websockets

from core.pattern_cache import PatternCache
from core.pattern_mixer import PatternMix

def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner

def parse_dmx(channels, size, color = np.array([0,0,0])):
    offset = 4
    assigned_ch = 1
    all = np.array([])
    parse_ch = assigned_ch + offset
    for x in range(size):
        try:
            color[x-1] = channels[parse_ch + x]
        except:
            continue
    return color
    


class PatternSelector:
    def __init__(self, pattern_config, led_config, dmx_config, args):
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.dmx_config = dmx_config
        self.args = args

        # Pattern cache
        self.enable_cache = args.enable_cache
        if args.enable_cache:
            self.pattern_cache = PatternCache(pattern_config, led_config, args)
        else:
            self.pattern_cache = None

        # Selected patterns
        self.patterns = {}
        self.current_pattern_id = list(pattern_config.rotation.keys())[0]
        self.pattern_start_time = time.time()
        self.pattern_rotation = []
        self.pattern_rotation_index = 0
        self.pattern_all = []
        self.pattern_manual = []
        self.pattern_effects = []
        self.pattern_eyes = []
        self.current_pattern_eye_id = None
        self.current_effect_pattern_ids = []
        self.pattern_mix = PatternMix(self.patterns, self.pattern_cache)

        # Launchpad
        self.launchpad = None
        self.buttons_active = []
        self.buttons_pressed = []
        self.buttons_released = []

        # DMX
        self.dmx = None
        self.channels = bytearray(dmx_config['universe_size'])
        self.color = np.array([0, 0, 0])

        # Constants
        self._LED_COLOR_ACTIVE = 100
        self._LED_COLOR_INACTIVE = 0


    def all_patterns_configs(self):
        for d in self.pattern_config:
            for pattern_id, config in d.items():
                yield pattern_id, config


    async def initializePatterns(self):
        # Initialize all patterns
        for pattern_id, (cls, params) in self.all_patterns_configs():
            pattern = cls()
            for key in params:
                setattr(pattern.params, key, params[key])
            pattern.prepareSegments(self.led_config)
            pattern.initialize()
            self.patterns[pattern_id] = pattern  
        
        # Initialize rotation 
        self.pattern_all = [pattern_id for pattern_id, _ in self.all_patterns_configs()]
        self.pattern_rotation = list(self.pattern_config.rotation.keys())
        self.pattern_manual = list(self.pattern_config.manual.keys())
        self.pattern_effects = list(self.pattern_config.special_effects.keys())
        self.pattern_eyes = list(self.pattern_config.eyes.keys())
        
        # Initialize cached patterns
        if self.args.enable_cache:
            await self.pattern_cache.initialize_patterns()

        # Initialize pattern mix
        self.pattern_mix.prepareSegments(self.led_config)
        self.pattern_mix.initialize()

    def handle_rotation_buttons(self, button, pattern_time):
        # Deactivate button corresponding to previous pattern
        self.deactivateButton(self.current_pattern_id)
        # Update rotation index if the selected pattern is on rotation
        self.pattern_rotation_index = self.pattern_rotation.index(button)
        # Activate button corresponding to current pattern
        self.activateButton(button)
        # Update pattern index based on button press
        self.current_pattern_id = button
        self.pattern_start_time = pattern_time    


    def handle_manual_buttons(self, button, pattern_time):
        # Deactivate button corresponding to previous pattern
        self.deactivateButton(self.current_pattern_id)
        # Activate button corresponding to current pattern
        self.activateButton(button)
        # Update pattern index based on button press
        self.current_pattern_id = button
        self.pattern_start_time = pattern_time


    def handle_effect_buttons(self, button, pattern_time, released=False):
        if released:
            self.deactivateButton(button)
            self.current_effect_pattern_ids.remove(button)
            self.patterns[button].reset()
        else:
            self.activateButton(button)
            self.current_effect_pattern_ids.append(button)


    def handle_eye_buttons(self, button, pattern_time):
        if button == self.current_pattern_eye_id:
            # Deactivate eye pattern
            self.deactivateButton(button)
            self.current_pattern_eye_id = None
        else:
            if self.current_pattern_eye_id:
                self.deactivateButton(self.current_pattern_eye_id)
            # Activate button corresponding to current pattern
            self.activateButton(button)
            # Update pattern index based on button press
            self.current_pattern_eye_id = button


    def handle_buttons(self, pattern_time):
        # Only consider the last button for now.
        # Might be fun to consider multiple patterns at some point.
        for button in self.buttons_pressed:
            if button in self.pattern_rotation:
                self.handle_rotation_buttons(button, pattern_time)
            elif button in self.pattern_manual:
                self.handle_manual_buttons(button, pattern_time)
            elif button in self.pattern_effects:
                self.handle_effect_buttons(button, pattern_time)
            elif button in self.pattern_eyes:
                self.handle_eye_buttons(button, pattern_time)

        for button in self.buttons_released:
            if button in self.pattern_effects:
                self.handle_effect_buttons(button, pattern_time, released=True)

         # Clear button presses
        self.buttons_pressed.clear()
        self.buttons_released.clear()

    def handle_pattern_timer(self, pattern_time):
        # Check if max pattern time is exceeded
        if (pattern_time - self.pattern_start_time) < self.args.pattern_rotation_time:
            return

        # Deactivate button corresponding to previous pattern
        self.deactivateButton(self.current_pattern_id)
        # Rotate patterns
        self.pattern_rotation_index = (self.pattern_rotation_index + 1) % len(self.pattern_rotation)
        # Activate button corresponding to current pattern
        self.activateButton(self.pattern_rotation[self.pattern_rotation_index])
        self.current_pattern_id = self.pattern_rotation[self.pattern_rotation_index]
        self.pattern_start_time = pattern_time


    def update(self, pattern_time):
        self.handle_buttons(pattern_time)
        self.handle_pattern_timer(pattern_time)
        
        if self.dmx:
            self.patterns[self.current_pattern_id].params.color = self.color
        
        replace_pattern_ids = []
        if self.current_pattern_eye_id:
            replace_pattern_ids.append(self.current_pattern_eye_id)
        self.pattern_mix.update_mix(
            base_pattern_ids=[self.current_pattern_id], 
            replace_pattern_ids=replace_pattern_ids,
            mix_pattern_ids=self.current_effect_pattern_ids)

        return self.pattern_mix


    def activateButton(self, button_name):
        if not button_name:
            return
        if not button_name in self.buttons_active:
            self.buttons_active.append(button_name)
        if self.launchpad:
            button_group = self.launchpad.panel.buttons(button_name)
            for button in button_group:
                button.led.color = self._LED_COLOR_ACTIVE


    def deactivateButton(self, button_name):
        if not button_name:
            return
        if button_name in self.buttons_active:
            self.buttons_active.remove(button_name)
        if self.launchpad:
            button_group = self.launchpad.panel.buttons(button_name)
            for button in button_group:
                button.led.color = self._LED_COLOR_INACTIVE


    @run_in_executor
    def controllerPoll(self):
        
        if self.launchpad:
            button_event = self.launchpad.panel.buttons().poll_for_event()
            if button_event and button_event.type == lpminimk3.ButtonEvent.PRESS:
                self.buttons_pressed.append(button_event.button.name)
            elif button_event and button_event.type == lpminimk3.ButtonEvent.RELEASE:
                self.buttons_released.append(button_event.button.name)               


    @run_in_executor
    def dmxPoll(self): 

        if self.dmx:
            #Check for waiting messages from DMX controller
            if self.dmx.inWaiting() > 0:
                bytes = self.dmx.read_until(expected = bytearray([self.dmx_config['start_byte']]))
                while self.dmx.inWaiting() > 0:
                    self.channels = self.dmx.read_until(expected = bytearray([self.dmx_config['stop_byte']]))
                self.color = parse_dmx(self.channels, self.dmx_config['universe_size'], self.color)
            else:
                pass    


    async def launchpadListener(self):
        
        available_lps = lpminimk3.find_launchpads()
        if available_lps:
            # Use the first available launchpad
            self.launchpad = available_lps[0]
            # Open device for reading and writing on MIDI interface (by default)
            self.launchpad.open()
            self.launchpad.mode = lpminimk3.Mode.PROG  # Switch to the programmer mode
        else:
            print("Launchpad controller not found.")
            return
        if self.launchpad:
            for button in self.launchpad.panel.buttons():
                button.led.color = self._LED_COLOR_INACTIVE
        
        while True:
            # Wait for a controller event
            await self.controllerPoll()


    async def launchpadWSListener(self, websocket, path):
        while True:
            try:
                res = await websocket.recv()
                event = json.loads(res)
                if event["type"] == "button_pressed":
                    self.buttons_pressed.append(event["button"])
            except websockets.ConnectionClosed as exc:
                break


    async def dmxListener(self):
        #Check for connected DMX controller
        try:
            self.dmx = serial.Serial(self.dmx_config['device'], baudrate = self.dmx_config['baudrate'], stopbits = self.dmx_config['stop_bits'])
        except:
            print("DMX controller not found")
            return
        if self.dmx:
            self.dmx.isOpen()
        
        while True:
            # Wait for a controller event
            await self.dmxPoll()
            