import asyncio
import functools
import struct
import sys


async def connect_to_opc(loop, object_id, pattern_generator, server_ip, server_port):
    reconnect_interval = 5.0  # In seconds
    while True:
        on_con_lost = loop.create_future()

        print(f'Connecting to OPC server at {server_ip}:{server_port}')
        opc_factory = functools.partial(
            OpenPixelControlProtocol,
            generator=pattern_generator,
            object_id=object_id,
            on_con_lost=on_con_lost)
        try:
            transport, protocol = await loop.create_connection(opc_factory, server_ip, server_port)
        except Exception as exc:
            print(f'Could not connect to OPC server: {exc}. Retrying in {reconnect_interval} seconds.')
            await asyncio.sleep(reconnect_interval)
            continue

        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await on_con_lost
        finally:
            transport.close()
        print(
            f'OPC connection to {server_ip}:{server_port} closed. Retrying in {reconnect_interval} seconds.')
        await asyncio.sleep(reconnect_interval)


class OpenPixelControlProtocol(asyncio.Protocol):
    def __init__(self, generator, object_id, on_con_lost):
        super().__init__()
        self.transport = None
        self.opc = None
        self.generator = generator
        self.object_id = object_id
        self.verbose = False
        self.on_con_lost = on_con_lost

    def _debug(self, m):
        if self.verbose:
            print('    %s' % str(m))

    def connection_made(self, transport):
        """Store the OpenPixelControl transport and schedule the task to send data.
        """
        self.transport = transport
        asyncio.ensure_future(self.serve())

    def connection_lost(self, exc):
        print('OpenPixelControlProtocol closed')
        self.on_con_lost.set_result(True)

    def put_pixels(self, pixels, channel=0):
        """Send the list of pixel colors to the OPC server on the given channel.

        channel: Which strand of lights to send the pixel colors to.
            Must be an int in the range 0-255 inclusive.
            0 is a special value which means "all channels".

        pixels: A list of 3-tuples representing rgb colors.
            Each value in the tuple should be in the range 0-255 inclusive. 
            For example: [(255, 255, 255), (0, 0, 0), (127, 0, 0)]
            Floats will be rounded down to integers.
            Values outside the legal range will be clamped.

        Will establish a connection to the server as needed.

        On successful transmission of pixels, return True.
        On failure (bad connection), return False.

        The list of pixel colors will be applied to the LED string starting
        with the first LED.  It's not possible to send a color just to one
        LED at a time (unless it's the first one).

        """
        self._debug('put_pixels: connecting')
        is_closing = self.transport.is_closing()
        if is_closing:
            self._debug('put_pixels: not connected.  ignoring these pixels.')
            return False

        # build OPC message
        len_hi_byte = int(len(pixels)*3 / 256)
        len_lo_byte = (len(pixels)*3) % 256
        command = 0  # set pixel colors from openpixelcontrol.org

        header = struct.pack("BBBB", channel, command,
                             len_hi_byte, len_lo_byte)

        pieces = [struct.pack("BBB",
                              min(255, max(0, int(r))),
                              min(255, max(0, int(g))),
                              min(255, max(0, int(b)))) for r, g, b in pixels]

        if sys.version_info[0] == 3:
            # bytes!
            message = header + b''.join(pieces)
        else:
            # strings!
            message = header + ''.join(pieces)

        self._debug('put_pixels: sending pixels to server')
        self.transport.write(message)

        return True

    async def serve(self):
        while True:
            results = await asyncio.shield(self.generator.result)
            for object_id, result in results.items():
                # Only push pixels for this objects
                if object_id != self.object_id:
                    continue

                self._debug('Sending OPC packet to object: %s' % object_id)
                for channel, segment in enumerate(result.led_segments):
                    if channel > 7:
                        continue
                    self.put_pixels(segment.colors, channel+1)
