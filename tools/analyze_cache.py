#!/usr/bin/env python3
"""Find patterns whose cached frames flash, and say which segments and how fast.

In cached mode every frame the sculpture shows was rendered once by
create_pattern_cache.py and pickled. So a pattern that flashes on the sculpture
has that flashing baked into its cache files, and it can be found by reading
them -- no need to watch the piece and guess.

Reports, per pattern, the mean frame-to-frame colour change and how much of the
run is spent in large jumps. A pattern that alternates between rendering and
blanking shows a high jump fraction and an obvious period.

    python tools/analyze_cache.py                     # every cached pattern
    python tools/analyze_cache.py --pattern 4x0 -v    # per-frame detail for one
"""
import argparse
import json
import math
import os
import pickle
import sys

import numpy as np

# Rendered by their own pattern and painted over the base, so they are excluded
# from the "everything except the eyes" comparison.
EYE_UIDS = {271, 272}


def cache_root(led_config_path):
    cfg = json.load(open(led_config_path))
    blob = bytearray(json.dumps(cfg, sort_keys=True).encode('ascii'))
    import hashlib
    h = hashlib.sha256(blob).hexdigest()
    return os.path.join(os.path.expanduser('~'), 'pattern_cache', h), h, cfg


def frame_path(root, pattern_id, i):
    lo = math.floor(i / 1000) * 1000
    hi = math.floor(i / 1000 + 1) * 1000 - 1
    return os.path.join(root, pattern_id, '%06d-%06d' % (lo, hi), '%06d.p' % i)


def load_frames(root, pattern_id, limit=None):
    index = os.path.join(root, pattern_id, 'index.json')
    if not os.path.exists(index):
        return None, None
    n = json.load(open(index))['animation_steps']
    if limit:
        n = min(n, limit)
    out = []
    for i in range(n):
        p = frame_path(root, pattern_id, i)
        if not os.path.exists(p):
            break
        with open(p, 'rb') as f:
            out.append(pickle.loads(f.read()))
    return out, n


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(here)
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--led_config', default=os.path.join(root_dir, 'config/led_config.json'))
    ap.add_argument('--pattern', help='only this pattern id')
    ap.add_argument('--limit', type=int, default=400, help='frames to read per pattern')
    ap.add_argument('-v', '--verbose', action='store_true', help='per-frame deltas')
    ap.add_argument('--threshold', type=float, default=40.0,
                    help='mean per-channel change that counts as a jump (0-255)')
    args = ap.parse_args()

    root, h, cfg = cache_root(args.led_config)
    uids = [s['uid'] for s in cfg['led_segments']]
    names = {s['uid']: s['name'] for s in cfg['led_segments']}
    keep = [i for i, u in enumerate(uids) if u not in EYE_UIDS]

    print('cache: %s' % root)
    if not os.path.isdir(root):
        sys.exit('no cache for this led_config hash (%s...). Rebuild it.' % h[:12])

    ids = [args.pattern] if args.pattern else sorted(
        d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))

    print('\n%-6s %7s %10s %10s %8s  %s' %
          ('id', 'frames', 'mean d', 'p99 d', 'jump%', 'verdict'))
    flagged = []
    for pid in ids:
        frames, n = load_frames(root, pid, args.limit)
        if not frames:
            print('%-6s %7s  no cache' % (pid, '-'))
            continue

        # Mean absolute change per LED between consecutive frames, eyes excluded.
        deltas = []
        for a, b in zip(frames, frames[1:]):
            pa = np.concatenate([a[i].astype(np.int16) for i in keep])
            pb = np.concatenate([b[i].astype(np.int16) for i in keep])
            deltas.append(float(np.abs(pb - pa).mean()))
        deltas = np.array(deltas)
        if not len(deltas):
            continue
        # Absolute threshold, deliberately not derived from this pattern's own
        # median: when half the frames are flashing the median is dragged up
        # and a relative threshold outruns the very signal it is looking for.
        # At 20fps a normal pattern moves a few units per frame; a segment
        # slamming between black and full is 255.
        thresh = args.threshold
        jump = float((deltas > thresh).mean()) * 100
        verdict = 'ok'
        if jump > 10:
            verdict = 'FLASHES -- %.0f%% of frames jump' % jump
            flagged.append((pid, deltas, thresh))
        elif jump > 2 or deltas.mean() > 25:
            verdict = 'suspect'
        print('%-6s %7d %10.2f %10.2f %7.1f%%  %s' %
              (pid, len(frames), deltas.mean(), np.percentile(deltas, 99), jump, verdict))

        if args.verbose:
            for i, d in enumerate(deltas):
                mark = '  <== jump' if d > thresh else ''
                print('     frame %4d -> %4d : %7.2f%s' % (i, i + 1, d, mark))

    for pid, deltas, thresh in flagged:
        print('\n=== %s ===' % pid)
        big = np.where(deltas > thresh)[0]
        runs, start = [], big[0]
        for a, b in zip(big, big[1:]):
            if b != a + 1:
                runs.append((start, a)); start = b
        runs.append((start, big[-1]))
        # A single stray frame is usually a real cut in the source video, not a
        # fault. Only sustained bursts are worth timing.
        sustained = [r for r in runs if r[1] - r[0] + 1 >= 5]
        print('  %d bursts of large jumps (%d sustained):' % (len(runs), len(sustained)))
        for a, b in (sustained or runs)[:12]:
            print('     frames %4d..%-4d  (%.1fs..%.1fs at 20fps, %.1fs long)'
                  % (a, b, a / 20, b / 20, (b - a + 1) / 20))
        if len(sustained) > 1:
            gaps = [sustained[i + 1][0] - sustained[i][0] for i in range(len(sustained) - 1)]
            print('  burst period: %.1f s (%.0f frames)' % (np.mean(gaps) / 20, np.mean(gaps)))
        # which segments move during a burst?
        print('  worst segments during the first burst:')
        a = runs[0][0]
        fa, fb = load_frames(root, pid, a + 2)[0][a:a + 2]
        per = [(float(np.abs(fb[i].astype(np.int16) - fa[i].astype(np.int16)).mean()),
                names[uids[i]]) for i in keep]
        for v, nm in sorted(per, reverse=True)[:6]:
            print('     %-16s mean delta %6.1f' % (nm, v))


if __name__ == '__main__':
    main()
