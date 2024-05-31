#!/usr/bin/env python3
"""A test script that uses sounddevice and asyncio generators for blocks of audio data.

You need Python 3.7 or newer to run this.

"""
import argparse
import asyncio
import queue
import sys

import numpy as np
import sounddevice as sd
import soundfile as sf


def int_or_str(text):
    """Helper function for argument parsing."""
    try:
        return int(text)
    except ValueError:
        return text

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument(
    '-l', '--list-devices', action='store_true',
    help='show list of audio devices and exit')
args, remaining = parser.parse_known_args()
if args.list_devices:
    print(sd.query_devices())
    parser.exit(0)
parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
    parents=[parser])
parser.add_argument(
    '-d', '--device', type=int_or_str,
    help='input device (numeric ID or substring)')
parser.add_argument(
    '-r', '--samplerate', type=int, default=44100, help='sampling rate')
parser.add_argument(
    '-c', '--channels', type=int, default=2, help='number of input channels')
parser.add_argument(
    '-b', '--blocksize', type=int, default=1024,
    help='block size (default: %(default)s)')
parser.add_argument(
    '-q', '--buffersize', type=int, default=1000,
    help='number of blocks used for buffering (default: %(default)s)')
args = parser.parse_args(remaining)
if args.blocksize == 0:
    parser.error('blocksize must not be zero')
if args.buffersize < 1:
    parser.error('buffersize must be at least 1')
args = parser.parse_args(remaining)


async def inputstream_generator(q_out, filename):
    """Generator that yields blocks of input data as NumPy arrays."""
    while True:
        with sf.SoundFile(filename) as f:
            for block in f.blocks(blocksize=args.blocksize, dtype='float32'):
                print(filename)
                await q_out.put(block)


async def streammixer_generator(q_out, input_streams):
    """Generator that yields blocks of input data as NumPy arrays."""
    while True:
        stream_data = np.ndarray((len(input_streams), args.blocksize, args.channels), dtype='float32')
        # Get a block from each stream
        for (i, stream) in enumerate(input_streams):
            data = await stream.get()
            stream_data[i, :] = data
        
        # Average streams
        out = stream_data.mean(axis=0)
        print("mix")
        await q_out.put(out)


async def outputstream_generator(q_in):
    """Generator that yields blocks of input/output data as NumPy arrays.

    The output blocks are uninitialized and have to be filled with
    appropriate audio signals.

    """
    event = asyncio.Event()
    loop = asyncio.get_event_loop()

    def callback(outdata, frames, time, status):
        assert frames == args.blocksize
        if status.output_underflow:
            print('Output underflow: increase blocksize?', file=sys.stderr)
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackAbort
        assert not status
        try:
            data = q_in.get_nowait()
        except asyncio.QueueEmpty:
            print('Buffer is empty: increase buffersize?', file=sys.stderr)
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackAbort
        if len(data) < len(outdata):
            outdata[:len(data)] = data
            outdata[len(data):] = b'\x00' * (len(outdata) - len(data))
            loop.call_soon_threadsafe(event.set)
            raise sd.CallbackStop
        else:
            print("output")
            outdata[:] = data

    stream = sd.OutputStream(
        samplerate=args.samplerate, blocksize=args.blocksize,
        device=args.device, channels=args.channels, dtype='float32',
        callback=callback, finished_callback=event.set)
    with stream:
        await event.wait()


async def main(** kwargs):
    q_in1 = asyncio.Queue(maxsize=args.buffersize)
    q_in2 = asyncio.Queue(maxsize=args.buffersize)
    q_in3 = asyncio.Queue(maxsize=args.buffersize)
    q_in4 = asyncio.Queue(maxsize=args.buffersize)
    q_mix = asyncio.Queue(maxsize=args.buffersize)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(inputstream_generator(q_in1, '1.wav'))
        tg.create_task(inputstream_generator(q_in2, '2.wav'))
        tg.create_task(inputstream_generator(q_in3, '3.wav'))
        tg.create_task(inputstream_generator(q_in4, '4.wav'))
        tg.create_task(streammixer_generator(q_mix, [q_in1, q_in2, q_in3, q_in4]))
        tg.create_task(outputstream_generator(q_mix))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit('\nInterrupted by user')
