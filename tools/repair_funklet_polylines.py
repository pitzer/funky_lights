"""
One-shot repair of scrambled point order in config/funklet/funklet_actual.csv.

Why this was needed
-------------------
generate_csv_from_fusion_sketch.py merges the selected Fusion entities in the wrong
order. Its MERGE_RESULTS loop walks the selection backwards:

    for i in range(len(segments) - 1, 0, -1):
        other = segments.pop(i)
        merge_segment.merge(other)          # extends with other.points[1:]

so entities land as [first, last, last-1, ... , second], and merge() unconditionally
drops each one's leading point on the assumption it duplicates the previous last point.
When the order is wrong that assumption is false, so the polyline ends up out of sequence
and a real point is silently lost each time.

The `length` column is unaffected - the exporter writes it from the summed true entity
lengths before the merge touches any points - so it is an independent check on every
repair below, and each one is asserted against it.

This does NOT touch:
  - head (uid 25): its jump across the midline is a real wire between two LED lines
  - the dome's front arc: also a wire run, see the dome entry below
  - ear_right / leg_front_right: their point order was already correct

Run once from the repo root:  python tools/repair_funklet_polylines.py [--apply]
Re-running after --apply is a no-op: every repair is checked and skipped if already done.
"""

import argparse
import ast
import csv
import sys

import numpy as np

CSV_PATH = 'config/funklet/funklet_actual.csv'
UID, NAME, NUM_LEDS, LENGTH, REVERSED, OFFSET, SUB_COMPONENT, NUM_ADDRESSABLE, BUS, STATUS, POINTS = range(11)


def destub_and_close(p):
    """[a,b,a,c,d,...] -> [b,a,c,d,...,b].

    The merge left the first entity's two points reversed at the head of the list with
    its start point duplicated at index 2. Putting b in front and re-closing the loop
    restores the original traversal.
    """
    assert np.linalg.norm(p[0] - p[2]) < 1e-6, 'expected p[0] == p[2]'
    fixed = np.vstack([p[1][None], p[0][None], p[3:]])
    return np.vstack([fixed, fixed[0]])


def repairs(rows_by_name):
    """name -> (new points, expected length, why)."""
    out = {}

    # ear_left: confirmed by mirror symmetry, not just length - the repaired arc sequence
    # is exactly ear_right's reversed, and the coordinates mirror about x=0.
    p = rows_by_name['ear_left']
    out['ear_left'] = (destub_and_close(p), 3.44,
                       'destub + close; exact mirror of ear_right')

    # leg_front_left: same defect. Runs top-front -> down the front -> around the foot ->
    # up the back, which is already the wanted direction.
    p = rows_by_name['leg_front_left']
    out['leg_front_left'] = (destub_and_close(p), 4.17,
                             'destub + close; matches leg_front_right pitch')

    # dome base ring: every arc is exactly 0.409 m, so the true circle order is
    # [0],[3],[4]..[14],[1] closing on [0] - 14 arcs, 5.73 m, the full length column.
    # But the LEDs only cover part of it: they start by the left front leg, run around
    # the BACK, and stop by the right front leg, with a wire across the front. So we keep
    # only that arc - indices 14 down to 3 - and drop the front arc the wire spans.
    p = rows_by_name['dome']
    out['dome'] = (p[3:][::-1], 4.50,
                   'LED-covered arc only: left front leg -> around the back -> right front leg')

    # dome_1 / dome_2: the over-the-top arcs, reordered so they ascend from the ring's
    # wire landing at the front base, over the top, and down the back.
    p = rows_by_name['dome_1']
    out['dome_1'] = (np.vstack([p[0], p[1], p[3], p[2]]), 1.48,
                     'reordered to ascend front base -> over the top')
    p = rows_by_name['dome_2']
    out['dome_2'] = (np.vstack([p[0], p[1], p[4], p[3], p[2]]), 1.96,
                     'reordered to continue over the top -> down the back')
    return out


def path_length(p):
    return float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='write the repairs back to the CSV')
    args = parser.parse_args()

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader if r]

    by_name = {}
    for row in rows:
        by_name.setdefault(row[NAME], np.array(ast.literal_eval(row[POINTS]), dtype=float))

    try:
        planned = repairs(by_name)
    except AssertionError as exc:
        sys.exit('Already repaired, or unexpected input (%s). Nothing written.' % exc)

    failures = []
    for name, (points, expected, why) in planned.items():
        actual = path_length(points)
        ok = abs(actual - expected) < 0.015
        print('%-16s %.2f m (expect %.2f) %-4s %s' %
              (name, actual, expected, 'OK' if ok else 'FAIL', why))
        if not ok:
            failures.append(name)
    if failures:
        sys.exit('Length check failed for %s - refusing to write.' % ', '.join(failures))

    if not args.apply:
        print('\ndry run - pass --apply to write %s' % CSV_PATH)
        return

    for row in rows:
        if row[NAME] in planned:
            points, expected, _ = planned[row[NAME]]
            row[POINTS] = repr([[float(v) for v in q] for q in points])
            row[LENGTH] = '%.2f' % path_length(points)

    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)
    print('\nwrote %s' % CSV_PATH)


if __name__ == '__main__':
    main()
