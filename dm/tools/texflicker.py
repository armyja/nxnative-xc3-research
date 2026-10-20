#!/usr/bin/env python3
"""Report draws whose font-atlas binding flickers across frames.

Reads a host log with [texhash] lines:
  [texhash] F<frame> draw #<ord> binds an R8Unorm font atlas at slot <k> (serial <s>)
For every frame-internal draw ordinal, prints the frames it bound a font atlas and the frames it did
not, between the first and last frame where that ordinal was seen binding one. A draw that binds on
some frames and not on others is the "A over the head" signature: the same draw position samples the
font atlas only sometimes (stale handle / wrong binding).
"""
import re, sys
from collections import defaultdict

pat = re.compile(r'\[texhash\] F(\d+) draw #(\d+) binds an R8Unorm font atlas at slot (\d+) \(serial (\d+)\)')

def main(path):
    seen = defaultdict(dict)   # ord -> frame -> serial
    frames = set()
    for line in open(path, errors='replace'):
        m = pat.search(line)
        if not m:
            continue
        f, o, slot, ser = (int(x) for x in m.groups())
        seen[o][f] = (slot, ser)
        frames.add(f)
    if not frames:
        print('no font-atlas lines'); return
    lo, hi = min(frames), max(frames)
    flips = 0
    for o in sorted(seen):
        fs = seen[o]
        first, last = min(fs), max(fs)
        miss = [f for f in range(first, last + 1) if f not in fs]
        sers = {s for _, s in fs.values()}
        if miss:
            flips += 1
            print(f'draw #{o}: binds font atlas on {len(fs)} frames {first}..{last}, missing on {len(miss)}'
                  f' (first miss {miss[0]}), serials {sorted(sers)}')
    if not flips:
        print(f'no flicker: {len(seen)} draw positions bind the font atlas consistently over frames {lo}..{hi}')

if __name__ == '__main__':
    main(sys.argv[1])
