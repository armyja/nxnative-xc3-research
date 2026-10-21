#!/usr/bin/env python3
"""Recover the real vertex/pixel pairs from a run's pass records.

The host's DM_NVN_PASSDUMP emits, per pass, a "K <pass> st<N> key=<shader>" line for every stage it binds. That is
the only place a stage pair can be read for shaders that exist only as runtime dumps: those have no container
program, so shader_pairs.tsv never learned about them and vs_pad never ran for them.

A pass pairs only when it holds exactly one vertex and one pixel key. A pass that binds several programs (several
draws, or a program change mid-pass) is reported as ambiguous and never paired: taking "the last key of each stage"
would invent combinations that were never bound together, which is how three such pairs reached a profile before this
rule existed.

Usage: dmsh_pairs_from_log.py <boot.log> [output.tsv] [--selftest]
Prints (or writes) one "<vs key> <ps key>" line per distinct pair, plus a summary on stderr.
"""
import collections, os, re, sys

K = re.compile(r'\[pass\] F(\d+) K (\d+) st(\d+) key=([0-9a-f]{16})')
PATH = re.compile(r'\[pass\] F(\d+) pass (\d+) .*?P (\d+)')     # unused, kept for reference


def pairs_from_log(path):
    """(pairs, ambiguous): a pair needs a pass with exactly one vertex and one pixel key."""
    seen = collections.defaultdict(list)        # (frame, pass) -> [(stage, key), ...] in file order
    for ln in open(path, errors='replace'):
        m = K.search(ln)
        if m: seen[(m.group(1), m.group(2))].append((int(m.group(3)), m.group(4)))
    pairs, ambiguous = set(), []
    for ident, binds in seen.items():
        vs = [k for st, k in binds if st == 0]; ps = [k for st, k in binds if st == 1]
        if len(vs) == 1 and len(ps) == 1 and len(binds) == 2: pairs.add((vs[0], ps[0]))
        elif len(vs) > 1 or len(ps) > 1: ambiguous.append((ident, binds))   # a pass with one stage only is just incomplete
    return pairs, ambiguous


def selftest():
    import tempfile
    fail = []
    def case(lines, want_pairs, want_ambiguous, what):
        with tempfile.NamedTemporaryFile('w', suffix='.log', delete=False) as f:
            f.write('\n'.join(lines) + '\n'); path = f.name
        try:
            pairs, amb = pairs_from_log(path)
            if pairs != want_pairs or len(amb) != want_ambiguous:
                fail.append(f'{what}: got pairs={sorted(pairs)} ambiguous={len(amb)}')
        finally:
            os.unlink(path)
    a, b, c, d = 'a' * 16, 'b' * 16, 'c' * 16, 'd' * 16
    case([f'[pass] F1 K 5 st0 key={a}', f'[pass] F1 K 5 st1 key={b}'], {(a, b)}, 0, 'one clean pass')
    case([f'[pass] F1 K 5 st0 key={a}', f'[pass] F1 K 5 st1 key={b}',
          f'[pass] F1 K 5 st0 key={c}', f'[pass] F1 K 5 st1 key={d}'], set(), 1, 'two programs in one pass')
    case([f'[pass] F1 K 5 st0 key={a}', f'[pass] F1 K 5 st0 key={c}', f'[pass] F1 K 5 st1 key={b}'], set(), 1,
         'two vertex keys and one pixel key')
    case([f'[pass] F1 K 5 st0 key={a}', f'[pass] F2 K 5 st1 key={b}'], set(), 0, 'stages in different passes')
    for f in fail: print(f'FAIL: {f}')
    print(f'selftest: {len(fail)} failure(s)')
    return 1 if fail else 0


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    if sys.argv[1] == '--selftest': return selftest()
    log = sys.argv[1]
    out = next((x for x in sys.argv[2:] if not x.startswith('-')), None)
    pairs, ambiguous = pairs_from_log(log)
    order = sorted(pairs)
    if out:
        with open(out, 'w') as f:
            f.write('# pairs recovered from DM_NVN_PASSDUMP K records: one vertex and one pixel key in the same pass\n')
            for v, p in order: f.write(f'{v} {p}\n')
    print(f'pairs: {len(order)}; ambiguous passes (several programs, not paired): {len(ambiguous)}', file=sys.stderr)
    for (fr, pa), binds in ambiguous[:5]:
        print(f'  ambiguous F{fr} pass {pa}: {binds}', file=sys.stderr)
    for v, p in order: print(v, p)


if __name__ == '__main__':
    main()
