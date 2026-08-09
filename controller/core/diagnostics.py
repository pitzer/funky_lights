import asyncio
import logging
import sys
import threading
import time
import traceback


class LoopStallDetector:
    """Detect and diagnose stalls of the asyncio event loop.

    An asyncio task stamps a heartbeat; a daemon *thread* checks it. The thread
    is the point -- when the loop is blocked nothing on it can report the fact,
    so the watchdog has to live outside it.

    On a stall it dumps the main thread's stack, which names the exact line that
    is blocking. That is the difference between "something froze for 27 seconds"
    and "video_pattern.py:61 was in video.read()".
    """

    def __init__(self, threshold=1.0, interval=0.1):
        self.threshold = threshold
        self.interval = interval
        self._beat = time.monotonic()
        self._wall = time.time()
        self._main_thread_id = threading.main_thread().ident
        self._stalled = False
        self._stall_started = 0.0

    async def heartbeat(self):
        """Run as an asyncio task; the only thing that touches the loop."""
        while True:
            self._beat = time.monotonic()
            self._wall = time.time()
            await asyncio.sleep(self.interval)

    def _dump_main_stack(self):
        frame = sys._current_frames().get(self._main_thread_id)
        if frame is None:
            return "  (main thread stack unavailable)"
        return "".join(traceback.format_stack(frame))

    def _watch(self):
        while True:
            time.sleep(self.interval)
            now = time.monotonic()
            gap = now - self._beat

            if gap > self.threshold and not self._stalled:
                self._stalled = True
                self._stall_started = self._beat
                logging.error(
                    "EVENT LOOP STALLED for %.1fs -- main thread is here:\n%s",
                    gap, self._dump_main_stack())
            elif gap <= self.threshold and self._stalled:
                self._stalled = False
                logging.warning("event loop recovered after %.1fs",
                                now - self._stall_started)

            # A wall clock that jumps relative to the monotonic clock means NTP
            # stepped it. Harmless now that the frame scheduler is monotonic,
            # but it used to freeze every LED, so it is worth seeing.
            drift = abs((time.time() - self._wall) - gap)
            if drift > 0.5 and not self._stalled:
                logging.warning(
                    "WALL CLOCK STEP: %+.1fs against the monotonic clock", drift)

    def start(self):
        threading.Thread(target=self._watch, daemon=True,
                         name="loop-stall-detector").start()
        logging.info("stall detector armed (threshold %.1fs)", self.threshold)
