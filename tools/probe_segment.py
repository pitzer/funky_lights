#!/usr/bin/env python3
"""Light known LED indices on one segment, to map index order onto hardware.

The LED geometry in config/led_config.json comes from a CAD polyline, and a
polyline says nothing about where one physical strip ends and the next begins.
Where a run is wired as two strips joined by a jumper, that junction is
invisible in the config -- `dome` happens to show a 44.5cm gap, but `head` was
resampled at a uniform 52mm and shows nothing at all.

This walks a lit dot along a segment, printing each index as it lights, so the
junction can be read off the sculpture directly.

IMPORTANT: stop the controller first. Two processes writing the same boards
interleave frames and neither display is trustworthy:

    sudo supervisorctl stop funky_lights_controller_cached_mode

Examples:
    # walk a white dot along the head, half a second per LED
    python tools/probe_segment.py --segment head --walk --delay 0.5

    # walk, pausing for a keypress at each LED
    python tools/probe_segment.py --segment head --walk --step

    # light one range green and another red, to check a split point
    python tools/probe_segment.py --segment head --range 0:48 --range 49:64

    # light a single index
    python tools/probe_segment.py --segment head --range 32:32
"""
import argparse
import json
import os
import socket
import struct
import time

OPC_SET_PIXEL_COLORS = 0
COLORS = [
    ("white",  (255, 255, 255)),
    ("red",    (255, 0, 0)),
    ("green",  (0, 255, 0)),
    ("blue",   (0, 0, 255)),
    ("yellow", (255, 255, 0)),
    ("cyan",   (0, 255, 255)),
]


def build_message(channel, pixels):
    n = len(pixels) * 3
    out = bytearray(struct.pack("BBBB", channel, OPC_SET_PIXEL_COLORS,
                                n // 256, n % 256))
    for r, g, b in pixels:
        out += bytes((r, g, b))
    return bytes(out)


def parse_range(text, limit):
    lo, _, hi = text.partition(':')
    lo = int(lo)
    hi = int(hi) if hi else lo
    if lo < 0 or hi >= limit or hi < lo:
        raise SystemExit(f"range {text!r} is outside 0..{limit - 1}")
    return lo, hi


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--segment", required=True, help="segment name, e.g. head")
    ap.add_argument("--led_config", default=os.path.join(root, "config/led_config.json"))
    ap.add_argument("--bus_config", default=os.path.join(root, "config/bus_config.json"))
    ap.add_argument("--walk", action="store_true", help="walk one lit LED along the segment")
    ap.add_argument("--step", action="store_true", help="with --walk, advance on Enter instead of a timer")
    ap.add_argument("--delay", type=float, default=0.4, help="seconds per LED when walking")
    ap.add_argument("--range", action="append", default=[],
                    help="light indices LO:HI, repeatable; each gets its own colour")
    ap.add_argument("--start", type=int, default=0, help="index to start walking from")
    args = ap.parse_args()

    led = json.load(open(args.led_config))
    bus = json.load(open(args.bus_config))
    seg = next((s for s in led['led_segments'] if s['name'] == args.segment), None)
    if seg is None:
        raise SystemExit(f"no segment {args.segment!r}. Available: "
                         + ", ".join(s['name'] for s in led['led_segments']))

    board = next((b for b in bus['led_busses'] if seg['uid'] in b['uids']), None)
    if board is None:
        raise SystemExit(f"segment {args.segment} is not on any bus")
    channel = board['uids'].index(seg['uid']) + 1
    n = seg.get('physical_num_leds', seg['num_leds'])
    ip, port = board['opc']['server_ip'], board['opc']['server_port']

    print(f"segment {args.segment}: uid {seg['uid']}, {n} pixels, "
          f"{board['name']} channel {channel} at {ip}:{port}")

    sock = socket.create_connection((ip, port), timeout=5)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def show(pixels):
        sock.sendall(build_message(channel, pixels))

    try:
        if args.range:
            pixels = [(0, 0, 0)] * n
            for i, spec in enumerate(args.range):
                lo, hi = parse_range(spec, n)
                name, rgb = COLORS[i % len(COLORS)]
                for j in range(lo, hi + 1):
                    pixels[j] = rgb
                print(f"  {lo}..{hi} -> {name}")
            show(pixels)
            print("holding. ctrl-C to clear and exit.")
            while True:
                time.sleep(1)
                show(pixels)          # keep refreshing; the board idles to a ramp
        elif args.walk:
            print("walking. ctrl-C to stop.\n"
                  "note the index where the dot jumps to a different part of the run.")
            for i in range(args.start, n):
                pixels = [(0, 0, 0)] * n
                pixels[i] = (255, 255, 255)
                show(pixels)
                print(f"  index {i}", flush=True)
                if args.step:
                    input("    press Enter for the next LED ")
                else:
                    time.sleep(args.delay)
        else:
            raise SystemExit("pass --walk or --range (see --help)")
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        show([(0, 0, 0)] * n)
        sock.close()
        print("cleared.")


if __name__ == '__main__':
    main()
