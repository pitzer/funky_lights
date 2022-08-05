import json
import time
import sys
import asyncio
import lpminimk3 
import serial_asyncio
import websockets
import functools
import time

from funky_lights import connection, messages
from patterns import pattern_config


WEB_SOCKET_PORT = 5678
TEXTURE_WIDTH = 128
TEXTURE_HEIGHT = 128
TEXTURE_SIZE = TEXTURE_WIDTH * TEXTURE_HEIGHT * 4


def PrepareTextureMsg(segments):
    msg = []
    texture_size = TEXTURE_SIZE
    for segment in segments:
        for color in segment.colors:
            msg += [color[0], color[1], color[2], 255]
    # Added padding to the end of the buffer to fill the full texture
    msg += [0] * (texture_size - len(msg))
    return bytearray(msg)


def run_in_executor(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner


async def ws_serve(websocket, generator):
    while True:
        segments = await asyncio.shield(generator.result)
        try:
            await websocket.send(PrepareTextureMsg(segments))
        except websockets.ConnectionClosed as exc:
            break


class SerialWriter(asyncio.Protocol):
    def __init__(self, generator, uids):
        super().__init__()
        self.transport = None
        self.generator = generator
        self.uids = uids

    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        print('Writer connection created')
        asyncio.ensure_future(self.serve())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')

    async def serve(self):
        while True:
            segments = await asyncio.shield(self.generator.result)
            for segment in segments:
                if segment.uid in self.uids:
                    self.transport.serial.write(
                        messages.PrepareLedMsg(segment.uid, segment.colors))


class LaunchPadHandler:
    def __init__(self):
        self.lp = None
        self.buttons_active = []
        self.buttons_pressed = []
        self.LED_COLOR_ACTIVE = 100
        self.LED_COLOR_INACTIVE = 0

    def activate_button(self, button_name):
        if not self.lp: 
            return
        button_group = self.lp.panel.buttons(button_name)
        for button in button_group:
            button.led.color = self.LED_COLOR_ACTIVE
            if not button in self.buttons_active:
                self.buttons_active.append(button)
    
    def deactivate_button(self, button_name):
        if not self.lp:
            return
        button_group = self.lp.panel.buttons(button_name)
        for button in button_group:
            button.led.color = self.LED_COLOR_INACTIVE
            if button in self.buttons_active:
                self.buttons_active.remove(button)

    def handle_event(self, button_event):
        if button_event and button_event.type == lpminimk3.ButtonEvent.PRESS:
            self.buttons_pressed.append(button_event.button.name)
        elif button_event and button_event.type == lpminimk3.ButtonEvent.RELEASE:
            pass

    @run_in_executor
    def poll(self):
        self.handle_event(self.lp.panel.buttons().poll_for_event())

    async def run(self):
        available_lps = lpminimk3.find_launchpads()
        if available_lps:
            self.lp = available_lps[0]  # Use the first available launchpad
            self.lp.open()  # Open device for reading and writing on MIDI interface (by default)
            self.lp.mode = lpminimk3.Mode.PROG  # Switch to the programmer mode
        else:
            print(f"No launchpad found.")
            return

        for button in self.lp.panel.buttons():
            button.led.color = self.LED_COLOR_INACTIVE
        while True:
            # Wait for a button press/release
            await self.poll()


class PatternGenerator:
    def __init__(self, led_config, launchpad):
        self.launchpad = launchpad
        self.result = asyncio.Future()
        self.patterns = []
        self.current_pattern_index = 0
        self.button_to_pattern_index_map = {}
        self.pattern_index_to_button_map = {}

        for i, (button, cls, params) in enumerate(pattern_config.DEFAULT_CONFIG):
            pattern = cls()
            for key in params:
                setattr(pattern, key, params[key])
            pattern.prepareSegments(led_config)
            pattern.initialize()
            self.patterns.append(pattern)
            self.button_to_pattern_index_map[button] = i
            self.pattern_index_to_button_map[i] = button

    async def tick(self, pattern, delta):
        pattern.animate(delta)

    async def run(self):
        ANIMATION_RATE = 20
        FPS_UPDATE_RATE = 1
        MAX_PATTERN_DURATION = 120

        prev_animation_time = time.time() - 1.0 / ANIMATION_RATE
        prev_pattern_time = time.time()
        start_time = time.time()
        counter = 0
        while True:
            cur_animation_time = time.time()

            # Check if a button was pressed on launchpad to change the pattern
            if self.launchpad.buttons_pressed:
                button = self.launchpad.buttons_pressed[-1]
                if button in self.button_to_pattern_index_map:
                    # Deactivate button corresponding to previous pattern
                    self.launchpad.deactivate_button(
                        self.pattern_index_to_button_map[self.current_pattern_index])
                    # Update pattern index based on button press
                    self.current_pattern_index = self.button_to_pattern_index_map[button]
                    prev_pattern_time = cur_animation_time
                self.launchpad.buttons_pressed.clear()
            
            # Check if max pattern time is exceeded
            if (cur_animation_time - prev_pattern_time) > MAX_PATTERN_DURATION:
                # Deactivate button corresponding to previous pattern
                self.launchpad.deactivate_button(
                    self.pattern_index_to_button_map[self.current_pattern_index])
                # Rotate patterns
                self.current_pattern_index = (
                    self.current_pattern_index + 1) % len(self.patterns)
                prev_pattern_time = cur_animation_time

            # Activate button corresponding to current pattern
            self.launchpad.activate_button(
                self.pattern_index_to_button_map[self.current_pattern_index])

            pattern = self.patterns[self.current_pattern_index]

            # Process animation
            await self.tick(pattern, cur_animation_time - prev_animation_time)

            # Update future for processing by IO
            self.result.set_result(pattern.segments)
            self.result = asyncio.Future()
            prev_animation_time = cur_animation_time

            # Sleep for the remaining time
            processing_time = time.time() - cur_animation_time
            await asyncio.sleep(max(0, 1.0/ANIMATION_RATE - processing_time))

            # Output update rate to console
            counter += 1
            if (time.time() - start_time) > 1.0 / FPS_UPDATE_RATE:
                print("Animation FPS: %.1f" % (counter / (time.time() - start_time)))
                counter = 0
                start_time = time.time()


async def main():
    led_config_file = '../config/led_config.json'
    if len(sys.argv) > 1:
        led_config_file = sys.argv[1]
    bus_config_file = '../config/bus_config.json'
    if len(sys.argv) > 2:
        bus_config_file = sys.argv[2]

    with open(led_config_file, 'r') as f:
        led_config = json.load(f)
    with open(bus_config_file, 'r') as f:
        bus_config = json.load(f)

    # Launchpad handler
    launchpad_handler = LaunchPadHandler()
    asyncio.create_task(launchpad_handler.run())

    # Start pattern generator
    pattern_generator = PatternGenerator(led_config, launchpad_handler)
    asyncio.create_task(pattern_generator.run())
    
    # Start WS server
    ws_serve_handler = functools.partial(ws_serve, generator=pattern_generator)
    await websockets.serve(ws_serve_handler, '127.0.0.1', WEB_SOCKET_PORT)

    # Start serial
    loop = asyncio.get_event_loop()
    for bus in bus_config['led_busses']:
        # Start the light app
        serial_port = connection.InitializeController(bus['device'], baudrate=bus['baudrate'])
        serial_port.close()

        # Start async serial handlers
        serial_serve_handler = functools.partial(
            SerialWriter, generator=pattern_generator, uids=bus['uids'])
        await serial_asyncio.create_serial_connection(
            loop, serial_serve_handler, bus['device'], baudrate=bus['baudrate'])
    
    # Wait forever
    await asyncio.Event().wait()


asyncio.run(main())
