import asyncio
import functools
import json
import lpminimk3
import time
import serial
import numpy as np
import websockets
from serial.tools import list_ports
import threading 

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
        self.current_pattern_eye_id = None
        self.current_effect_pattern_ids = []

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
        self.dmxConnected = asyncio.Event()


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
    def controllerPoll(self):
        
        if self.launchpad:
            button_event = self.launchpad.panel.buttons().poll_for_event()
            if button_event and button_event.type == lpminimk3.ButtonEvent.PRESS:
                self.buttons_pressed.append(button_event.button.name)
            elif button_event and button_event.type == lpminimk3.ButtonEvent.RELEASE:
                self.buttons_released.append(button_event.button.name)               


    @run_in_executor
    def dmxPoll(self): 
        try:
            if self.dmx:
                #Check for waiting messages from DMX controller
                print("Polling DMX")
                if self.dmx.inWaiting() > 0:
                    bytes = self.dmx.read_until(expected = bytearray([self.dmx_config['start_byte']]))
                    while self.dmx.inWaiting() > 0:
                        self.channels = self.dmx.read_until(expected = bytearray([self.dmx_config['stop_byte']]))
                    self.color = parse_dmx(self.channels, self.dmx_config['universe_size'], self.color)
                else:
                    pass 
        except Exception as e:
            print("DMX read error: " + str(e)) 
    
    async def check_presence(self, correct_port, flag, interval=1):
        while True:
            print("Checking presence")
            found = False
            ports = list(list_ports.comports())
            for port in ports:
                if port.name.split(".")[1] == correct_port:
                    found = True
                    continue 
            if found:
                print("Device connected")
                await time.sleep(interval)
            else:
                print ("Device has been disconnected!")
                flag.clear()
                #asyncio.current_task().cancel()
                #raise Exception("Device has been disconnected!")
                break
            
    

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
                if button.name in self.pattern_rotation:
                    button.led.color = self._LED_COLOR_ROTATION_INACTIVE
                elif button.name in self.pattern_manual:
                    button.led.color = self._LED_COLOR_MANUAL_INACTIVE
                elif button.name in self.pattern_effects:
                    button.led.color = self._LED_COLOR_EFFECTS_INACTIVE
                elif button.name in self.pattern_eyes:
                    button.led.color = self._LED_COLOR_EYES_INACTIVE
                else: 
                    button.led.color = 0
        
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
                elif event["type"] == "button_released":
                    self.buttons_released.append(event["button"])
            except websockets.ConnectionClosed as exc:
                break
    
    async def dmxListener(self):
        #Check for connected DMX controller
        while True:
            try:
                self.dmx = serial.Serial(self.dmx_config['device'], baudrate = self.dmx_config['baudrate'], stopbits = self.dmx_config['stop_bits'])
            except:
                #print("DMX controller not found")
                await asyncio.sleep(1)
                self.dmx = None
                continue
            if self.dmx:
                self.dmx.isOpen()
                self.dmxConnected.set()
                port_trunc = self.dmx.port.split(".")[1]
                #monitor = threading.Thread(target = self.check_presence, args = (port_trunc, self.dmxConnected))
                #monitor.start()
                loop = asyncio.get_event_loop()
                task = asyncio.run_coroutine_threadsafe(self.check_presence(port_trunc, self.dmxConnected), loop)

                while self.dmxConnected.is_set():
                    # Wait for a controller event
                    self.dmxPoll()
            await asyncio.sleep(1)