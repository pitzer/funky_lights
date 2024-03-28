import asyncio
import struct
import sys


class OpenPixelControlProtocol(asyncio.Protocol):
    def __init__(self, generator, object_id):
        super().__init__()
        self.transport = None
        self.opc = None
        self.generator = generator
        self.object_id = object_id
        self.verbose = False


    def _debug(self, m):
        if self.verbose:
            print('    %s' % str(m))


    def connection_made(self, transport):
        """Store the OpenPixelControl transport and schedule the task to send data.
        """
        self.transport = transport
        asyncio.ensure_future(self.serve())
        print('OpenPixelControlClient.send() scheduled')


    def connection_lost(self, exc):
        print('OpenPixelControlClient closed')


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

        header = struct.pack("BBBB", channel, command, len_hi_byte, len_lo_byte)

        pieces = [ struct.pack( "BBB",
                     min(255, max(0, int(r))),
                     min(255, max(0, int(g))),
                     min(255, max(0, int(b)))) for r, g, b in pixels ]

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
            led_segments = await asyncio.shield(self.generator.result)
            for object_id, segments in led_segments.items():
                # Only push pixels for this objects
                if object_id != self.object_id:
                    continue
            
                self._debug('Sending OPC packet to object: %s' % object_id)
                for channel, segment in enumerate(segments):
                    self.put_pixels(segment.colors, channel+1)
