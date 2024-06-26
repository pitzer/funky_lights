import asyncio
import serial_asyncio

from funky_lights import connection, messages


class SerialWriter(asyncio.Protocol):
    def __init__(self, generator, uids, color_format):
        super().__init__()
        self.transport = None
        self.generator = generator
        self.uids = uids
        self.color_format = color_format

    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        print('Writer connection created')
        asyncio.ensure_future(self.serve())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')

    async def initialize_lights(self):
        serial = self.transport.serial
        current_baudrate = serial.baudrate
        await asyncio.sleep(0.05)
        # Start application
        serial.baudrate = connection.BOOTLOADER_BAUDRATE
        serial.write(messages.PrepareStartLedControllerMsg(
            messages.BROADCAST_UID))
        await asyncio.sleep(0.01)
        # Change application baudrate to current_baudrate
        serial.baudrate = connection.START_BAUDRATE
        prescaler = int(16000000 / current_baudrate)
        serial.write(messages.PrepareBaudrateMsg(
            messages.BROADCAST_UID, prescaler))
        await asyncio.sleep(0.01)
        # Return to normal operations
        serial.baudrate = current_baudrate

    async def serve(self):
        last_init_time = time.time() - 2.0
        while True:
            # Initialize lights every second (should only affect lights that are in bootloader mode)
            if (time.time() - last_init_time) > 1.0:
                await self.initialize_lights()
                last_init_time = time.time()

            # Send color messages
            segments = await asyncio.shield(self.generator.result)
            for segment in segments:
                if segment.uid in self.uids:
                    self.transport.serial.write(
                        messages.PrepareLedMsg(segment.uid, segment.colors, self.color_format))
