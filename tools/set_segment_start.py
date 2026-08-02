"""
Inspect and set where an LED run starts.

The `reversed` and `offset` columns of the segment CSV decide which physical end of a
run carries LED 0, and - for runs that close on themselves - where in the loop the strip
enters. This turns "the strip now enters here" into those two values so they don't have
to be counted by hand off the piece.

LED positions are resampled exactly the way generate_led_config_funklet.ipynb does it, so
the indices printed here are the indices that end up in led_config.json.

    # current LED 0, direction, spacing and closure gap for every segment
    python tools/set_segment_start.py --csv config/funklet/funklet_actual.csv --report

    # what reversed/offset puts LED 0 nearest a point? add --apply to write it back
    python tools/set_segment_start.py --csv config/funklet/funklet_actual.csv \
        --segment ear_right --near -0.60,2.40,-0.60 --apply
"""

import argparse
import ast
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import led_config_utils

# Column indices of the segment CSV, in the order generate_csv_from_fusion_sketch.py writes them.
UID, NAME, NUM_LEDS, LENGTH, REVERSED, OFFSET, SUB_COMPONENT, NUM_ADDRESSABLE, BUS, STATUS, POINTS = range(11)

# Left/right counterparts. Their LED spacing should agree; a mismatch means one side's
# polyline is wrong, which is how the doubled-back stubs on the left legs were found.
MIRROR_PAIRS = [
    ('leg_front_left', 'leg_front_right'),
    ('leg_back_left', 'leg_back_right'),
    ('ear_left', 'ear_right'),
]

# A rotation only means something if the run closes on itself. Anything with a bigger
# closure gap than this many LED spacings would wrap LEDs across open space.
CLOSURE_TOLERANCE_LEDS = 1.5


def read_rows(path):
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        return header, [row for row in reader if row]


def points_of(row):
    return np.array(ast.literal_eval(row[POINTS]), dtype=float)


def path_length(points):
    if len(points) < 2:
        return 0.0
    return float(np.linalg.norm(np.diff(points, axis=0), axis=1).sum())


def led_positions(row, reverse=None, offset=None):
    """Resample a row to its addressable LED count, mirroring the notebook's pipeline."""
    points = points_of(row)
    num_leds = int(row[NUM_ADDRESSABLE])
    if len(points) < 2 or num_leds < 1:
        return np.zeros((0, 3))

    nodes = prev = None
    for point in points:
        node = led_config_utils.Node(p=np.array(point))
        if nodes is None:
            nodes = node
        if prev is not None:
            prev.next = node
        prev = node

    length = led_config_utils.line_segments_length(nodes)
    positions = led_config_utils.trace_line_segments(nodes, num_leds, 0.0, length / num_leds)

    # The notebook reverses first, then rotates - keep that order.
    if reverse is None:
        reverse = row[REVERSED] == 'TRUE'
    if reverse:
        positions = np.flip(positions, axis=0)

    offset = int(row[OFFSET]) if offset is None else offset
    offset %= positions.shape[0]
    if offset:
        positions = np.concatenate((positions[offset:], positions[:offset]), axis=0)
    return positions


def coincident_pairs(points):
    """Non-adjacent identical points - the signature of a doubled-back selection in Fusion.

    A closed loop legitimately repeats its first point at the end, so that one pair is
    not a defect and is excluded.
    """
    last = len(points) - 1
    return [(i, j)
            for i in range(len(points))
            for j in range(i + 2, len(points))
            if not (i == 0 and j == last)
            and np.linalg.norm(points[i] - points[j]) < 1e-6]


def describe(position):
    x, y, z = position
    side = 'L' if x < -0.15 else ('R' if x > 0.15 else 'ctr')
    depth = 'front' if z < -0.3 else ('back' if z > 0.3 else 'mid')
    return '%s/%s' % (side, depth)


def report(rows):
    spacing_by_name = {}
    print('%-6s %-16s %5s %8s %9s %9s  %-22s %s' %
          ('uid', 'name', 'leds', 'path(m)', 'cm/led', 'gap(m)', 'LED 0', 'notes'))

    for row in rows:
        points = points_of(row)
        num_leds = int(row[NUM_ADDRESSABLE])
        length = path_length(points)
        spacing = length / num_leds if num_leds else 0.0
        gap = float(np.linalg.norm(points[0] - points[-1])) if len(points) else 0.0
        spacing_by_name.setdefault(row[NAME], spacing)

        positions = led_positions(row)
        first = positions[0] if len(positions) else np.zeros(3)

        notes = []
        dup = coincident_pairs(points)
        if dup:
            i, j = dup[0]
            stub = path_length(points[i:j + 1])
            notes.append('DOUBLED-BACK idx %d==%d, %.2fm (~%d leds) traversed twice'
                         % (i, j, stub, round(stub / spacing) if spacing else 0))
        if spacing and gap > CLOSURE_TOLERANCE_LEDS * spacing:
            notes.append('open run (gap ~%.1f leds) - rotating would wrap LEDs across it'
                         % (gap / spacing))
        if int(row[OFFSET]) and spacing and gap > CLOSURE_TOLERANCE_LEDS * spacing:
            notes.append('!! offset set on an open run')

        print('%-6s %-16s %5d %8.2f %9.1f %9.3f  (%+.2f,%+.2f,%+.2f) %-6s %s' %
              (row[UID], row[NAME], num_leds, length, spacing * 100, gap,
               first[0], first[1], first[2], describe(first), '; '.join(notes)))

    print()
    for left, right in MIRROR_PAIRS:
        if left in spacing_by_name and right in spacing_by_name:
            a, b = spacing_by_name[left], spacing_by_name[right]
            flag = '' if abs(a - b) < 0.005 else '   <-- MISMATCH, one polyline is wrong'
            print('mirror %-16s %.1f cm/led  vs  %-16s %.1f cm/led%s'
                  % (left, a * 100, right, b * 100, flag))


def solve_start(rows, name, target, force_reverse):
    matches = [r for r in rows if r[NAME] == name]
    if not matches:
        sys.exit('No segment named %r. Try --report to list them.' % name)
    if len(matches) > 1:
        sys.exit('%d rows named %r; disambiguate the CSV first.' % (len(matches), name))
    row = matches[0]

    points = points_of(row)
    num_leds = int(row[NUM_ADDRESSABLE])
    spacing = path_length(points) / num_leds
    gap = float(np.linalg.norm(points[0] - points[-1]))

    reverse = force_reverse if force_reverse is not None else (row[REVERSED] == 'TRUE')
    positions = led_positions(row, reverse=reverse, offset=0)
    index = int(np.linalg.norm(positions - target, axis=1).argmin())
    distance = float(np.linalg.norm(positions[index] - target))

    print('%s (uid %s): %d leds, %.1f cm/led, closure gap %.3f m' %
          (name, row[UID], num_leds, spacing * 100, gap))
    print('  nearest LED to target is index %d, %.3f m away' % (index, distance))
    print('  -> reversed=%s  offset=%d' % ('TRUE' if reverse else 'FALSE', index))
    if index and gap > CLOSURE_TOLERANCE_LEDS * spacing:
        print('  WARNING: this run is open (gap ~%.1f leds). Rotating it wraps that many'
              % (gap / spacing))
        print('           LEDs across empty space. Prefer expressing the new start with')
        print('           reversed alone, or fix the polyline.')
    return row, reverse, index


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--csv', required=True, help='segment CSV, e.g. config/funklet/funklet_actual.csv')
    parser.add_argument('--report', action='store_true', help='summarise every segment')
    parser.add_argument('--segment', help='segment name to solve a start point for')
    parser.add_argument('--near', help='target point as x,y,z in meters')
    parser.add_argument('--reverse', dest='reverse', action='store_true', default=None,
                        help='force reversed=TRUE before solving')
    parser.add_argument('--no-reverse', dest='reverse', action='store_false',
                        help='force reversed=FALSE before solving')
    parser.add_argument('--apply', action='store_true', help='write the result back to the CSV')
    args = parser.parse_args()

    header, rows = read_rows(args.csv)

    if args.report or not args.segment:
        report(rows)
        return

    if not args.near:
        sys.exit('--segment needs --near x,y,z')
    target = np.array([float(v) for v in args.near.split(',')])
    if target.shape != (3,):
        sys.exit('--near must be three comma-separated numbers')

    row, reverse, offset = solve_start(rows, args.segment, target, args.reverse)

    if args.apply:
        row[REVERSED] = 'TRUE' if reverse else 'FALSE'
        row[OFFSET] = str(offset)
        with open(args.csv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print('  wrote %s' % args.csv)
    else:
        print('  (dry run - pass --apply to write it)')


if __name__ == '__main__':
    main()
