import asyncio
import functools


def run_in_executor(f):
    """Run a blocking function on the default thread pool.

    Lives here rather than in pattern_selector so that patterns can use it
    without importing that module, which pulls in lpminimk3 and pyserial.
    """
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner
