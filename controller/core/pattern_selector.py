import asyncio
import functools
import lpminimk3
import time

from core.pattern_cache import PatternCache

def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner


class PatternSelector:
    def __init__(self, pattern_config, led_config, args, pattern_cache):
        self.pattern_config = pattern_config
        self.led_config = led_config
        self.enable_cache = args.enable_cache
        self.pattern_cache = pattern_cache

        # Selected patterns
        self.patterns = []
        self.current_pattern_index = 0
        self.pattern_start_time = time.time()

        # Launchpad
        self.button_to_pattern_index_map = {}
        self.pattern_index_to_button_map = {}
        self.launchpad = None
        self.buttons_active = []
        self.buttons_pressed = []

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

        if self.enable_cache:
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
    def poll(self):
        button_event = self.launchpad.panel.buttons().poll_for_event()
        if button_event and button_event.type == lpminimk3.ButtonEvent.PRESS:
            self.buttons_pressed.append(button_event.button.name)
        elif button_event and button_event.type == lpminimk3.ButtonEvent.RELEASE:
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
            return

        for button in self.launchpad.panel.buttons():
            button.led.color = self._LED_COLOR_INACTIVE
        while True:
            # Wait for a button press/release
            await self.poll()
