#!/usr/bin/env python3
"""Refill a shader library from a run's DM_NVN_SHDUMP dumps.

The host saves each shader it cannot find as <key>.ctl (0x880-byte control section) and <key>.code (the code area).
This tool turns those dumps into the package records, map rows and pairs the offline builder needs, skips what the
project deliberately refuses (geometry stages), reports what it has no source bytes for, and then rebuilds the
library through the normal entry point.

Usage:
  dmsh_refill.py --dumps RUN/shdump --containers SAMPLE_DIR [SAMPLE_DIR ...] \
                 --profile PROFILE_DIR --pkg PKG_DIR --out OUT_DIR [--dry-run] [--j 1] \
                 [--allow-dump-only]

With --allow-dump-only, a dumped key that no container holds is packaged from the dump itself and labelled
runtime_dump#<n>: the dump is the shader the game actually handed the driver, so it is a real source, just without a
container/program label. The stage then comes from the control section: offset 0x714 is 0 for vertex and 1 for pixel,
which held for all 132 container-labelled dumps and the six added later (138 checked, no exception).

Container samples are the *.wishp (SPCH) files a previous extraction produced: a dumped key is only buildable when the
same bytes exist in one of them, because the dump itself carries no program/entry context. Keys without a container
match, and geometry stages, are reported and never guessed.
"""
import argparse, collections, hashlib, json, os, struct, subprocess, sys, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spch

# The two helpers below mirror dm/gfx/tools/shader_split.py (skey / ctl_len / check). They are inlined on purpose:
# shader_split pulls in the game-profile machinery at import time, and this tool must run without a chosen profile
# (it receives the profile as an argument and only reads its tables).
CTL_MAGIC, GFX_MAGIC, CS_MAGIC = bytes.fromhex('34127698'), bytes.fromhex('78563412'), bytes.fromhex('79563412')


def ctl_len(ctl):
    n = struct.unpack_from('<I', ctl, 0x20)[0]
    return n if 0x760 <= n < 0x880 else 0x880


def skey(ctl, code):
    return hashlib.sha256(ctl[:ctl_len(ctl)] + code).hexdigest()[:16]


def check(stage, ctl, code):
    if ctl[:4] != CTL_MAGIC or len(ctl) < ctl_len(ctl): return 'bad control section'
    if struct.unpack_from('<I', ctl, 0x704)[0] != len(code): return 'control +0x704 does not match the code length'
    return None
ss = types.SimpleNamespace(skey=skey, check=lambda _w, st, c, d: check(st, c, d))


HERE = os.path.dirname(os.path.abspath(__file__))


def read_dumps(d):
    out, bad = {}, []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.ctl'): continue
        key = name[:-4]; ctl = open(os.path.join(d, name), 'rb').read()
        code_path = os.path.join(d, key + '.code')
        code = open(code_path, 'rb').read() if os.path.exists(code_path) else b''
        if len(ctl) < 0x880 or ctl[:4] != spch.CTL_MAGIC: bad.append((key, 'bad control section')); continue
        n = struct.unpack_from('<I', ctl, 0x704)[0]
        if not code or n != len(code): bad.append((key, f'code missing or length {n} != {len(code)}')); continue
        if skey(ctl, code) != key: bad.append((key, 'key does not recompute')); continue
        out[key] = (ctl, code)
    return out, bad


def index_containers(paths):
    idx = {}
    for p in paths:
        data = open(p, 'rb').read()
        name = os.path.basename(p)[:-6]
        progs = collections.defaultdict(dict)
        try:
            shaders = spch.shaders(data, name)
        except Exception as e:
            print(f'  container {name}: skipped ({e})'); continue
        for where, st, ctl, code in shaders:
            lab = where.rpartition('#SPCH#')[2].split('@')[0]
            si, pi, ei, stage = lab.split(':')
            progs[(si, pi)][stage] = (ei, ctl, code)
        for (si, pi), d in progs.items():
            for stage, (ei, ctl, code) in d.items():
                k = skey(ctl, code)
                if k not in idx:
                    idx[k] = dict(container=os.path.basename(p), si=si, pi=pi, ei=ei, stage=stage,
                                  ctl=ctl, code=code, chain={s: v[0] for s, v in d.items()})
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dumps', required=True); ap.add_argument('--containers', nargs='+', required=True)
    ap.add_argument('--profile', required=True); ap.add_argument('--pkg', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--j', default='1')
    ap.add_argument('--allow-dump-only', action='store_true')
    a = ap.parse_args()

    dumps, bad = read_dumps(a.dumps)
    print(f'dumps: {len(dumps)} usable, {len(bad)} unusable')
    for k, why in bad: print(f'  unusable {k}: {why}')

    map_path = os.path.join(a.profile, 'shader_map.tsv')
    pairs_path = os.path.join(a.profile, 'shader_pairs.tsv')
    have = set()
    for ln in open(map_path):
        c = ln.rstrip('\n').split('\t')
        if not ln.startswith('#') and len(c) > 4: have.add(c[3])

    idx = index_containers(a.containers)
    new, no_source, refused = {}, {}, {}
    for k, (ctl, code) in dumps.items():
        if k in have: continue
        hit = idx.get(k)
        if not hit:
            if a.allow_dump_only:
                stage = 'ps' if ctl[0x714] == 1 else 'vs' if ctl[0x714] == 0 else None
                if stage is None: no_source[k] = f'no container and control 0x714 = {ctl[0x714]}'; continue
                new[k] = dict(container=None, si=None, pi=None, ei=None, stage=stage,
                              ctl=ctl, code=code, chain=None)
                continue
            no_source[k] = 'not in any container sample'; continue
        if hit['stage'] == 'gs': refused[k] = f"geometry stage ({hit['container']} slct{hit['si']} program{hit['pi']})"; continue
        if hit['stage'] not in ('vs', 'ps', 'cs'): refused[k] = f"unsupported stage {hit['stage']}"; continue
        new[k] = hit

    print(f'already in map: {len(have)}; new buildable: {len(new)}; no source: {len(no_source)}; refused: {len(refused)}')
    for k, why in refused.items(): print(f'  refused {k}: {why}')

    if not a.dry_run and new:
        os.makedirs(a.pkg, exist_ok=True)
        rows = []
        for k, h in sorted(new.items()):
            head = bytearray(0x38); head[0:8] = b'BTCDBTCD'
            struct.pack_into('<2I', head, 0x28, len(h['ctl']), len(h['code']))
            base = os.path.splitext(h['container'])[0] + f"_s{h['si']}p{h['pi']}" if h['container'] else 'runtime_dump'
            fn = f"{h['stage']}_{base}.bin"
            open(os.path.join(a.pkg, fn), 'wb').write(bytes(head) + h['code'] + h['ctl'])
            src = (f"{os.path.splitext(h['container'])[0]}#{h['si']}:{h['pi']}:{h['ei']}:{h['stage']}"
                   if h['container'] else f"runtime_dump#{k}:{h['stage']}")
            rows.append(f"{fn}\t0\t{'vertex' if h['stage'] == 'vs' else 'pixel' if h['stage'] == 'ps' else 'compute'}\t{k}\t{src}")
        with open(map_path, 'a') as f: f.write('\n'.join(rows) + '\n')
        pr = collections.defaultdict(dict)
        for k, h in new.items(): pr[(h['container'], h['si'], h['pi'])][h['stage']] = k
        with open(pairs_path, 'a') as f:
            for (c, si, pi), d in sorted(pr.items()):
                if 'vs' in d and 'ps' in d: f.write(f"{d['vs']} {d['ps']}\n")
        print(f'packaged {len(rows)} records into {a.pkg}')

    report = dict(new={k: dict(container=v['container'], slct=v['si'], program=v['pi'], entry=v['ei'], stage=v['stage'], chain=v['chain']) for k, v in new.items()},
                  no_source=no_source, refused=refused, unusable={k: w for k, w in bad})
    os.makedirs(a.out, exist_ok=True)
    json.dump(report, open(os.path.join(a.out, 'refill.json'), 'w'), indent=1)
    if a.dry_run or not new:
        print('dry run or nothing to add: library not rebuilt'); return 0
    env = dict(os.environ)
    subprocess.run([sys.executable, os.path.join(HERE, 'dmsh_chain.py'), '--header'], check=True, env=env)
    keys = sorted(k for k in (have | set(new)))
    cmd = [sys.executable, os.path.join(HERE, 'dmsh_build.py'), a.pkg, a.out] + keys
    e2 = dict(env, J=str(a.j))
    r = subprocess.run(cmd, env=e2)
    print(f'build rc={r.returncode} ({len(keys)} keys)')
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
