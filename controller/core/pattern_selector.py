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

        # Pattern rotation and related
        self.current_pattern_id = self.pattern_rotation[0]
        self.pattern_start_time = time.time()
        self.pattern_rotation_index = 0
        self.current_pattern_eye_id = self.pattern_eyes[0]
        self.current_effect_pattern_ids = []
        self.replace_pattern_ids = [self.current_pattern_eye_id]

        # Pattern mixer
        self.pattern_mix = PatternMix(self.patterns, self.pattern_cache)

        # Launchpad
        self.launchpad = None
        self.buttons_active = []
        self.buttons_pressed = []
        self.buttons_released = []

        # Launchpad color constants
        self._LED_COLOR_ROTATION_ACTIVE = lpminimk3.colors.ColorPalette.Red.SHADE_1
        self._LED_COLOR_ROTATION_INACTIVE = lpminimk3.colors.ColorPalette.Red.SHADE_9
        self._LED_COLOR_MANUAL_ACTIVE = lpminimk3.colors.ColorPalette.Green.SHADE_1
        self._LED_COLOR_MANUAL_INACTIVE = lpminimk3.colors.ColorPalette.Green.SHADE_43
        self._LED_COLOR_EFFECTS_ACTIVE = lpminimk3.colors.ColorPalette.Blue.SHADE_1
        self._LED_COLOR_EFFECTS_INACTIVE = lpminimk3.colors.ColorPalette.Blue.SHADE_17
        self._LED_COLOR_EYES_ACTIVE = lpminimk3.colors.ColorPalette.Violet.SHADE_1
        self._LED_COLOR_EYES_INACTIVE = lpminimk3.colors.ColorPalette.Violet.SHADE_29

        # DMX
        self.dmx = None
        self.channels = bytearray(dmx_config['universe_size'])
        self.color = np.array([0, 0, 0])

        # Pattern Mix Subscriber
        self.pattern_mix_updates = []


    def get_pattern_mix(self):
        return {
            'current_pattern_id': self.current_pattern_id,
            'replace_pattern_ids': self.replace_pattern_ids,
            'current_effect_pattern_ids': self.current_effect_pattern_ids,
        }


    def all_patterns_configs(self):
        for d in self.pattern_config:
            for pattern_id, config in d.items():
                yield pattern_id, config


    def maybe_cached_pattern(self, pattern_id):
        if self.pattern_cache and pattern_id in self.pattern_cache.patterns:
            return self.pattern_cache.patterns[pattern_id]
        else:
            return self.patterns[pattern_id]


    async def initializePatterns(self):
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
            while button in self.current_effect_pattern_ids:
                self.current_effect_pattern_ids.remove(button)
            self.maybe_cached_pattern(button).reset()
        else:
            self.activateButton(button)
            self.current_effect_pattern_ids.append(button)


    def handle_eye_buttons(self, button, pattern_time):
        if self.current_pattern_eye_id:
            # Deactivate eye pattern
            self.deactivateButton(button)
            while button in self.replace_pattern_ids:
                self.replace_pattern_ids.remove(button)
            self.current_pattern_eye_id = None

        else:
            # Activate eye pattern
            self.activateButton(button)
            self.replace_pattern_ids.append(button)     
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

    def handle_pattern_mix_updates(self, pattern_time):
        for pattern_mix in self.pattern_mix_updates:
            # Handle current_pattern_id
            pid = pattern_mix['current_pattern_id']
            if pid in self.patterns:
                if pid != self.current_pattern_id:
                    self.pattern_start_time = pattern_time
                self.current_pattern_id = pid
            
            # Handle replace_pattern_ids
            self.replace_pattern_ids.clear()
            for pid in pattern_mix['replace_pattern_ids']:
                if pid in self.patterns:
                    self.replace_pattern_ids.append(pid)
            
            # Handle removed effects and reset
            for pid in self.current_effect_pattern_ids:
                if pid not in pattern_mix['current_effect_pattern_ids']:
                    self.maybe_cached_pattern(pid).reset()

            # Update current_effect_pattern_ids    
            self.current_effect_pattern_ids.clear()
            for pid in pattern_mix['current_effect_pattern_ids']:
                if pid  in self.patterns:
                    self.current_effect_pattern_ids.append(pid)

         # Clear updates
        self.pattern_mix_updates.clear()

    def update(self, pattern_time):
        self.handle_pattern_mix_updates(pattern_time)
        self.handle_buttons(pattern_time)
        self.handle_pattern_timer(pattern_time)
        
        if self.dmx:
            self.patterns[self.current_pattern_id].params.color = self.color

        self.pattern_mix.update_mix(
            base_pattern_ids=[self.current_pattern_id], 
            replace_pattern_ids=self.replace_pattern_ids,
            mix_pattern_ids=self.current_effect_pattern_ids)

        return self.pattern_mix
   

    def activateButton(self, button_name):
        if not button_name:
            return
        if not button_name in self.buttons_active:
            self.buttons_active.append(button_name)
        if self.launchpad:
            if button_name in self.pattern_rotation:
                button_color = self._LED_COLOR_ROTATION_ACTIVE
            elif button_name in self.pattern_manual:
                button_color = self._LED_COLOR_MANUAL_ACTIVE
            elif button_name in self.pattern_effects:
                button_color = self._LED_COLOR_EFFECTS_ACTIVE
            elif button_name in self.pattern_eyes:
                button_color = self._LED_COLOR_EYES_ACTIVE
            else:
                button_color = 0

            button_group = self.launchpad.panel.buttons(button_name)
            for button in button_group:
                button.led.color = button_color


    def deactivateButton(self, button_name):
        if not button_name:
            return
        while button_name in self.buttons_active:
            self.buttons_active.remove(button_name)
        if self.launchpad:
            if button_name in self.pattern_rotation:
                button_color = self._LED_COLOR_ROTATION_INACTIVE
            elif button_name in self.pattern_manual:
                button_color = self._LED_COLOR_MANUAL_INACTIVE
            elif button_name in self.pattern_effects:
                button_color = self._LED_COLOR_EFFECTS_INACTIVE
            elif button_name in self.pattern_eyes:
                button_color = self._LED_COLOR_EYES_INACTIVE
            else:
                button_color = 0

            button_group = self.launchpad.panel.buttons(button_name)
            for button in button_group:
                button.led.color = button_color        


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


    def initializeLaunchpadButtons(self):
        for button in self.launchpad.panel.buttons():
            if button.name in self.pattern_rotation:
                if button.name in self.buttons_active:
                    button.led.color = self._LED_COLOR_ROTATION_ACTIVE
                else:
                    button.led.color = self._LED_COLOR_ROTATION_INACTIVE
            elif button.name in self.pattern_manual:
                if button.name in self.buttons_active:
                    button.led.color = self._LED_COLOR_MANUAL_ACTIVE
                else:
                    button.led.color = self._LED_COLOR_MANUAL_INACTIVE
            elif button.name in self.pattern_effects:
                if button.name in self.buttons_active:
                    button.led.color = self._LED_COLOR_EFFECTS_ACTIVE
                else:
                    button.led.color = self._LED_COLOR_EFFECTS_INACTIVE
            elif button.name in self.pattern_eyes:
                if button.name in self.buttons_active:
                    button.led.color = self._LED_COLOR_EYES_ACTIVE
                else:
                    button.led.color = self._LED_COLOR_EYES_INACTIVE
            else: 
                button.led.color = 0
            
    
    @run_in_executor
    def launchpadListener(self):
        # Outer loop to find launchpads
        while True:
            try:
                available_lps = lpminimk3.find_launchpads()
                if available_lps:
                    # Use the first available launchpad
                    self.launchpad = available_lps[0]
                    # Open device for reading and writing on MIDI interface (by default)
                    self.launchpad.open()
                    self.launchpad.mode = lpminimk3.Mode.PROG  # Switch to the programmer mode
                    print('Connected to launchpad device.')
                else:
                    # sleep for 1 second and continue
                    time.sleep(1)
                    continue
            except Exception as err:
                print(f"Unexpected {err=}, {type(err)=} while connecting to launchpad.")
                # sleep for 1 second and continue
                time.sleep(1)
                continue
            
            # Initialize button colors
            self.initializeLaunchpadButtons()

            # Inner loop for polling button presses
            while self.launchpad.is_open():
                # Check if device is still connected
                if not self.launchpad.device_inquiry():
                    print('Launchpad disconnected.')
                    self.launchpad.close()
                    time.sleep(1)
                    break

                # Wait for a controller event
                button_event = self.launchpad.panel.buttons().poll_for_event(timeout=10)
                if not button_event:
                    continue
                if button_event.type == lpminimk3.ButtonEvent.PRESS:
                    self.buttons_pressed.append(button_event.button.name)
                elif button_event.type == lpminimk3.ButtonEvent.RELEASE:
                    self.buttons_released.append(button_event.button.name)



    async def patternMixWSListener(self, uri):
        async for websocket in websockets.connect(uri):
            try:
                res = await websocket.recv()
                pattern_mix = json.loads(res)
                self.pattern_mix_updates.append(pattern_mix)
            except websockets.ConnectionClosed:
                continue


    async def launchpadWSListener(self, websocket, path):
        while True:
            try:
                res = await websocket.recv()
                event = json.loads(res)
                if event["type"] == "button_pressed":
                    self.buttons_pressed.append(event["button"])
                elif event["type"] == "button_released":
                    self.buttons_released.append(event["button"])
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
            