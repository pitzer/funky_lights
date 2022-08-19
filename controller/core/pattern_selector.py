import asyncio
import functools
import json
import lpminimk3
import time
import serial
import numpy as np
import websockets

from core.pattern_cache import PatternCache

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

        # Selected patterns
        self.patterns = []
        self.palettes = []
        self.current_pattern_index = 0
        self.pattern_start_time = time.time()

        # Launchpad
        self.button_to_pattern_index_map = {}
        self.pattern_index_to_button_map = {}
        self.launchpad = None
        self.buttons_active = []
        self.buttons_pressed = []

        #DMX
        self.dmx = None
        self.channels = bytearray(dmx_config['universe_size'])
        self.color = np.array([0, 0, 0])

        # Constants
        self._LED_COLOR_ACTIVE = 100
        self._LED_COLOR_INACTIVE = 0
        self._MAX_PATTERN_DURATION = 600

    async def initializePatterns(self):
        for i, (button, cls, params) in enumerate(self.pattern_config):
            pattern = cls()
            for key in params:
                setattr(pattern.params, key, params[key])
            pattern.prepareSegments(self.led_config)
            pattern.initialize()
            self.patterns.append(pattern)
            self.button_to_pattern_index_map[button] = i
            self.pattern_index_to_button_map[i] = button   

        if self.args.enable_cache:
            # This replaces all patterns by a cached version of themselves
            self.patterns = await self.pattern_cache.build_cache(self.patterns, self._MAX_PATTERN_DURATION)

    def update(self, pattern_time):
        # Check if any launchpad button was pressed to change the pattern
        if self.buttons_pressed:
            # Only consider the last button for now.
            # Might be fun to consider multiple patterns at some point.
            button = self.buttons_pressed[-1]
            # Deactivate button corresponding to previous pattern
            self.deactivateButton(
                self.pattern_index_to_button_map[self.current_pattern_index])
            # Activate button corresponding to current pattern
            self.activateButton(button)
            # Clear button presses
            self.buttons_pressed.clear()
            # Update pattern index based on button press
            self.current_pattern_index = self.button_to_pattern_index_map[button]
            self.pattern_start_time = pattern_time

        # Check if max pattern time is exceeded
        if (pattern_time - self.pattern_start_time) > self._MAX_PATTERN_DURATION:
            # Deactivate button corresponding to previous pattern
            self.deactivateButton(
                self.pattern_index_to_button_map[self.current_pattern_index])
            # Rotate patterns
            self.current_pattern_index = (
                self.current_pattern_index + 1) % len(self.patterns)
            # Activate button corresponding to current pattern
            self.activateButton(
                self.pattern_index_to_button_map[self.current_pattern_index])
            self.pattern_start_time = pattern_time
        
        if self.dmx:
            self.patterns[self.current_pattern_index].params.color = self.color
        
        return self.patterns[self.current_pattern_index]

    def activateButton(self, button_name):
        if not button_name in self.buttons_active:
            self.buttons_active.append(button_name)
        if self.launchpad:
            button_group = self.launchpad.panel.buttons(button_name)
            for button in button_group:
                button.led.color = self._LED_COLOR_ACTIVE

    def deactivateButton(self, button_name):
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
                pass               
    
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
            print(f"No launchpad found.")
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
        if self.dmx:
            self.dmx.isOpen()
        
        while True:
            # Wait for a controller event
            await self.dmxPoll()
            