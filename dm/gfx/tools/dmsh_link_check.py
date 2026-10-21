#!/usr/bin/env python3
"""Report vertex/pixel interface mismatches in a translated shader library.

Metal links stages by [[user(locnN)]] location. A pixel shader that reads a component the vertex shader never
writes gets whatever the vertex stage left there; the translator initialises every output to (0,0,0,1) and the
vertex body then writes what its own control section asked for. When a stage pair is translated without the
program context that describes the whole interface (a shader recovered only from a runtime dump), the two sides
can disagree about how many components a location carries - the vertex writes .x, the pixel reads .y/.z, and the
draw comes out missing channels (or black).

This tool reads the built MSL for a set of pairs and reports, per pair, which components each side uses.

Usage: dmsh_link_check.py <build dir> <chain dir> [shader_pairs.tsv]   (pairs file: "<vs key> <ps key>" per line)
"""
import os, re, sys, collections

USER = re.compile(r'float([1-4]?)\s+(\w+)\s*\[\[user\(locn(\d+)\)\]\]')


def varying_use(path):
    """location -> components the stage actually produces/consumes; the translator's default initialisation
    (out.x = float4(0,0,0,1), the value an unwritten component reads) is not counted as a write."""
    src = open(path).read()
    field_loc = {m.group(2): int(m.group(3)) for m in USER.finditer(src)}
    comp = collections.defaultdict(set)
    for m in re.finditer(r'\b(out|in)\.(\w+)\.([xyzw])\b', src):
        loc = field_loc.get(m.group(2))
        if loc is not None: comp[loc].add(m.group(3))
    for m in re.finditer(r'\b(out|in)\.(\w+)\s*=\s*float4\(([^)]*)\)', src):
        loc = field_loc.get(m.group(2))
        if loc is None: continue
        try: vals = [float(v) for v in m.group(3).split(',')]
        except ValueError: vals = []
        if vals == [0.0, 0.0, 0.0, 1.0]: continue       # initialisation, not data
        comp[loc] |= set('xyzw')
    return field_loc, comp


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    out, pairs_path = sys.argv[1], (sys.argv[3] if len(sys.argv) > 3 else None)
    pairs = []
    if pairs_path and os.path.exists(pairs_path):
        for ln in open(pairs_path):
            if ln.strip() and not ln.startswith('#'): pairs.append(tuple(ln.split()[:2]))
    if not pairs:
        raise SystemExit('no pairs given')
    bad = 0; compared = 0
    for vs, ps in pairs:
        vf, pf = os.path.join(out, vs + '_b.metal'), os.path.join(out, ps + '_b.metal')
        if not (os.path.exists(vf) and os.path.exists(pf)):
            print(f'{vs} -> {ps}: skipped (MSL not both present)'); continue
        compared += 1
        vd, vu = varying_use(vf); pd, pu = varying_use(pf)
        issues = []
        for loc, want in sorted(pu.items()):
            got = vu.get(loc, set())
            miss = want - got
            if miss: issues.append(f'locn{loc}: ps uses {"".join(sorted(want))}, vs writes {"".join(sorted(got)) or "-"}')
        if issues:
            bad += 1
            print(f'{vs} -> {ps}: {len(issues)} mismatch(es)')
            for i in issues[:4]: print(f'    {i}')
    print(f'pairs compared: {compared} of {len(pairs)}, with mismatches: {bad}')


if __name__ == '__main__':
    main()
