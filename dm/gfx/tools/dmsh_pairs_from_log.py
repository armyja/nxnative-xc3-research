#!/usr/bin/env python3
"""Recover the real vertex/pixel pairs from a run's pass records.

The host's DM_NVN_PASSDUMP emits, per pass, a "K <pass> st<N> key=<shader>" line for every stage it binds. That is
the only place a stage pair can be read for shaders that exist only as runtime dumps: those have no container
program, so shader_pairs.tsv never learned about them and vs_pad never ran for them.

Usage: dmsh_pairs_from_log.py <boot.log> [output.tsv]
Prints (or writes) one "<vs key> <ps key>" line per distinct pair, plus a summary on stderr.
"""
import collections, re, sys

K = re.compile(r'\[pass\] F(\d+) K (\d+) st(\d+) key=([0-9a-f]{16})')
PATH = re.compile(r'\[pass\] F(\d+) pass (\d+) .*?P (\d+)')     # unused, kept for reference


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    log = sys.argv[1]
    stages = collections.defaultdict(dict)      # (frame, pass) -> {stage index: key}
    for ln in open(log, errors='replace'):
        m = K.search(ln)
        if m:
            f, p, st, key = m.group(1), m.group(2), int(m.group(3)), m.group(4)
            stages[(f, p)][st] = key
    pairs = set()
    for (_f, _p), d in stages.items():
        if 0 in d and 1 in d: pairs.add((d[0], d[1]))
    order = sorted(pairs)
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'w') as f:
            f.write('# pairs recovered from DM_NVN_PASSDUMP K records (real draw-time stage combinations)\n')
            for v, p in order: f.write(f'{v} {p}\n')
    print(f'passes with two stages: {sum(1 for d in stages.values() if 0 in d and 1 in d)}; distinct pairs: {len(order)}',
          file=sys.stderr)
    for v, p in order: print(v, p)


if __name__ == '__main__':
    main()
