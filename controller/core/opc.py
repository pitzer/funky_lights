import asyncio
import functools
import logging
import random
import socket
import struct
import time
import numpy as np


# Reconnect policy.
#
# This used to be a flat 5 second sleep before any retry, which turned any brief
# interruption into a 5-10 second freeze: a board holds its last frame for the
# whole interval, so the outage is fully visible on the sculpture.
# Start fast and back off only if the link is genuinely down.
INITIAL_RECONNECT_DELAY = 0.25  # In seconds
MAX_RECONNECT_DELAY = 5.0  # In seconds
# Without a timeout, a SYN to a board that fell off the network sits in kernel
# retries for over a minute, leaving that whole bus dark.
CONNECT_TIMEOUT = 2.0  # In seconds
# How long a connection must survive before we treat the link as healthy again.
STABLE_CONNECTION_TIME = 5.0  # In seconds

# Write buffer high/low water marks, roughly three frames. A frame that is
# seconds late is worthless on an LED sculpture, so we drop rather than queue.
WRITE_BUFFER_HIGH = 8192  # In bytes
WRITE_BUFFER_LOW = 2048  # In bytes

# How long queued data may sit undelivered before we give up on the connection.
# A board that browns out or resets does not send an RST -- it just stops
# acknowledging -- so nothing else would tell us it is gone.
WRITE_STALL_TIMEOUT = 2.0  # In seconds
# Linux-only kernel equivalent of the above. The default is ~15 minutes of
# retransmits, during which that half of the sculpture holds its last frame.
TCP_USER_TIMEOUT_MS = 5000
# Cap the kernel send buffer. Left at the default, the kernel happily absorbs
# hundreds of KB -- many seconds of frames -- before the write buffer above ever
# grows, which hides a dead board for as long as it takes to fill. A bus sends
# ~50 KB/s, so this is well under a second of slack.
SOCKET_SEND_BUFFER = 32768  # In bytes

OPC_SET_PIXEL_COLORS = 0


def _configure_socket(sock):
    """Tune an OPC socket so that a vanished board is noticed quickly."""
    # Each frame is a couple of KB split over 6-8 channels. Without NODELAY,
    # Nagle holds those small writes waiting for an ACK and frames coalesce
    # across frame boundaries.
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SOCKET_SEND_BUFFER)

    if hasattr(socket, 'TCP_USER_TIMEOUT'):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_USER_TIMEOUT,
                        TCP_USER_TIMEOUT_MS)

    # Backstop only: keepalive probes never fire while we are writing every
    # frame, so this matters only if the stream ever goes quiet.
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    for name, value in (('TCP_KEEPIDLE', 5), ('TCP_KEEPINTVL', 2),
                        ('TCP_KEEPCNT', 3)):
        if hasattr(socket, name):
            sock.setsockopt(socket.IPPROTO_TCP, getattr(socket, name), value)


def collapse_colors(colors, target):
    """Average an (N, 3) colour array down to (target, 3) contiguous groups.

    Used where a segment's sample points outnumber its physical LEDs. Taking
    colors[:target] instead would sample a single point of the pattern, which
    on a moving video changes completely every frame and looks like random
    flicker; the mean over the area the fixture occupies tracks the pattern.
    """
    colors = np.asarray(colors)
    if target >= len(colors) or target < 1:
        return colors
    groups = np.array_split(colors.astype(np.uint16), target)
    out = np.array([g.mean(axis=0) for g in groups])
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def _next_delay(delay):
    """Return the next backoff delay, capped at MAX_RECONNECT_DELAY."""
    return min(MAX_RECONNECT_DELAY, delay * 2)


async def _sleep_with_jitter(delay):
    """Sleep for delay, jittered, so both busses don't retry in lockstep."""
    await asyncio.sleep(delay + random.uniform(0, 0.1 * delay))


async def connect_to_opc(generator, uids, server_ip, server_port,
                         swap_red_green=False):
    loop = asyncio.get_event_loop()
    reconnect_delay = INITIAL_RECONNECT_DELAY
    while True:
        on_con_lost = loop.create_future()

        logging.info(
            f'Connecting to OPC server at {server_ip}:{server_port}')
        opc_factory = functools.partial(
            OpenPixelControlProtocol,
            generator=generator,
            uids=uids,
            on_con_lost=on_con_lost,
            swap_red_green=swap_red_green)
        try:
            transport, protocol = await asyncio.wait_for(
                loop.create_connection(opc_factory, server_ip, server_port),
                timeout=CONNECT_TIMEOUT)
        except Exception as exc:
            logging.warning(
                f'Could not connect to OPC server {server_ip}:{server_port}: {exc!r}. '
                f'Retrying in {reconnect_delay:.2f} seconds.')
            await _sleep_with_jitter(reconnect_delay)
            reconnect_delay = _next_delay(reconnect_delay)
            continue

        connected_at = loop.time()

        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await on_con_lost
        finally:
            transport.close()

        # Only reset the backoff once a connection has proven stable. A board
        # that accepts and immediately closes would otherwise spin us in a hot
        # reconnect loop.
        if (loop.time() - connected_at) >= STABLE_CONNECTION_TIME:
            reconnect_delay = INITIAL_RECONNECT_DELAY

        logging.warning(
            f'OPC connection to {server_ip}:{server_port} closed. '
            f'Retrying in {reconnect_delay:.2f} seconds.')
        await _sleep_with_jitter(reconnect_delay)
        reconnect_delay = _next_delay(reconnect_delay)



class OpenPixelControlProtocol(asyncio.Protocol):
    def __init__(self, generator, uids, on_con_lost, swap_red_green=False):
        super().__init__()
        self.swap_red_green = swap_red_green
        self.transport = None
        self.opc = None
        self.generator = generator
        self.uids = uids
        self.verbose = False
        self.on_con_lost = on_con_lost
        self.peer = None
        self._serve_task = None
        self._paused = False
        self._dropped_frames = 0
        self._drained_at = time.monotonic()

    def _debug(self, m):
        if self.verbose:
            logging.debug('    %s' % str(m))

    def connection_made(self, transport):
        """Store the OpenPixelControl transport and schedule the task to send data.
        """
        self.transport = transport
        self.peer = transport.get_extra_info('peername')

        sock = transport.get_extra_info('socket')
        if sock is not None:
            _configure_socket(sock)
        transport.set_write_buffer_limits(
            high=WRITE_BUFFER_HIGH, low=WRITE_BUFFER_LOW)

        logging.info(f'OPC connection established to {self.peer}')
        self._serve_task = asyncio.ensure_future(self.serve())

    def connection_lost(self, exc):
        # exc is None for a clean FIN (the board closed us), ConnectionResetError
        # for an RST (board reset or its socket overflowed), and a timeout/OSError
        # when the link itself died. Worth logging: it separates a board problem
        # from a network problem.
        logging.warning(f'OPC connection to {self.peer} lost: {exc!r}')

        # Without this the serve() task outlives the connection, and every
        # reconnect leaks another copy still waking 20 times a second.
        if self._serve_task is not None:
            self._serve_task.cancel()
            self._serve_task = None

        if not self.on_con_lost.done():
            self.on_con_lost.set_result(True)

    def pause_writing(self):
        """Called by asyncio once the write buffer passes the high water mark."""
        self._paused = True
        logging.warning(
            f'OPC write buffer to {self.peer} is full '
            f'({self.transport.get_write_buffer_size()} bytes); dropping frames.')

    def resume_writing(self):
        """Called by asyncio once the write buffer drains to the low water mark."""
        self._paused = False
        logging.warning(
            f'OPC write buffer to {self.peer} drained after dropping '
            f'{self._dropped_frames} frame(s).')
        self._dropped_frames = 0

    def build_message(self, pixels, channel=0):
        """Build an OPC 'set pixel colors' message for a single channel.

        channel: Which strand of lights to send the pixel colors to.
            Must be an int in the range 0-255 inclusive.
            0 is a special value which means "all channels".

        pixels: An (N, 3) array of rgb colors. Values outside 0-255 are clamped.

        The colors are applied to the LED string starting with the first LED.
        It's not possible to send a color just to one LED at a time (unless it's
        the first one).
        """
        colors = np.asarray(pixels)
        if colors.dtype != np.uint8:
            colors = np.clip(colors, 0, 255).astype(np.uint8)
        colors = np.ascontiguousarray(colors)

        num_bytes = colors.size
        header = struct.pack("BBBB", channel, OPC_SET_PIXEL_COLORS,
                             num_bytes // 256, num_bytes % 256)
        return header + colors.tobytes()

    def put_pixels(self, pixels, channel=0):
        """Send the list of pixel colors to the OPC server on the given channel.

        On successful transmission of pixels, return True.
        On failure (bad connection), return False.
        """
        if not self.can_write():
            self._debug('put_pixels: not connected.  ignoring these pixels.')
            return False

        self._debug('put_pixels: sending pixels to server')
        self.transport.write(self.build_message(pixels, channel))
        return True

    def can_write(self):
        """True if the transport is open and not backed up."""
        return not self.transport.is_closing() and not self._paused

    def write_has_stalled(self):
        """True if queued data has not drained for WRITE_STALL_TIMEOUT.

        On a healthy link the buffer returns to empty between frames. If it
        stays non-empty the board has stopped acknowledging -- which is what a
        brownout or a board reset looks like from here, since neither sends an
        RST. Without this the kernel retransmits for minutes while that half of
        the sculpture holds its last frame.
        """
        if self.transport.get_write_buffer_size() == 0:
            self._drained_at = time.monotonic()
            return False
        return (time.monotonic() - self._drained_at) > WRITE_STALL_TIMEOUT

    async def serve(self):
        self._drained_at = time.monotonic()
        while True:
            segments = await asyncio.shield(self.generator.result)

            # Checked before the can_write() bail-out below: once the buffer is
            # full we stop writing, so this is the only thing that would notice.
            if self.write_has_stalled():
                logging.error(
                    f'OPC writes to {self.peer} stalled for over '
                    f'{WRITE_STALL_TIMEOUT}s '
                    f'({self.transport.get_write_buffer_size()} bytes queued). '
                    f'Assuming the board is gone; forcing a reconnect.')
                self.transport.abort()
                return

            if not self.can_write():
                # Skip the whole frame, including serializing it.
                self._dropped_frames += 1
                continue

            # Build the entire frame and issue a single write. One write per
            # channel meant 6-8 syscalls per frame per bus, and gave Nagle the
            # chance to hold the tail of a frame back.
            messages = []
            for segment in segments:
                if segment.uid in self.uids:
                    channel = self.uids.index(segment.uid) + 1
                    colors = segment.colors
                    physical = getattr(segment, 'physical_num_leds',
                                       segment.num_leds)
                    if physical != len(colors):
                        # Returns a new array, so the segment itself is
                        # untouched and the visualiser still sees every
                        # sample point.
                        colors = collapse_colors(colors, physical)
                    if self.swap_red_green:
                        # Board-local correction for firmware built with the
                        # wrong colour order. Fancy indexing returns a copy, so
                        # the segment itself is untouched -- other buses and the
                        # visualiser must still see the original.
                        colors = colors[:, [1, 0, 2]]
                    messages.append(self.build_message(colors, channel))

            if messages:
                self.transport.write(b''.join(messages))
