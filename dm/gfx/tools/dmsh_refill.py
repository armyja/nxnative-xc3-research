#!/usr/bin/env python3
"""Refill a shader library from a run's DM_NVN_SHDUMP dumps.

The host saves every shader it cannot find as <key>.ctl (the 0x880-byte control section) and <key>.code (the code
area). This tool turns those dumps into the packages, map rows and pairs the offline builder needs, refuses what the
project refuses (geometry stages), reports what has no source bytes, and rebuilds through the normal entry point.

Rules this tool keeps, because getting them wrong silently corrupts a library:

* One package per key, and its name carries the key. A package is verified as it is written: the header, both
  lengths, the control's own length field, the key recomputed from the bytes, and the stage byte. A map row may only
  point at a package that passed that check, so "the key was found in a container" is never accepted on its own.
* A container program pairs only when its entries are exactly the ordered [vs, ps] of one program (same container,
  same slct/program) with no duplicate stage, no geometry stage and no extra stage. Anything else is reported and
  left unpaired.
* A shader that exists only as a runtime dump never gets a pair invented for it: the dump carries no draw context, so
  a pair would be a guess. Runtime pairs must come from reviewed evidence (see dmsh_pairs_from_log.py), not from here.
* Every output is written to a temporary directory and validated before the profile is touched, so a failure never
  leaves a half-updated map, pairs file or package directory.
* The profile named by --profile must be the one DM_GAME/DM_GAMES_DIR resolve to. Otherwise the map would be written
  into a profile the chain/build never reads, so that is refused before anything is written.

Usage:
  dmsh_refill.py --dumps RUN/shdump --containers SAMPLE_DIR [SAMPLE_DIR ...] \
                 --profile PROFILE_DIR --pkg PKG_DIR --out OUT_DIR [--dry-run] [--j 1] \
                 [--allow-dump-only] [--selftest]
"""
import argparse, collections, hashlib, json, os, re, shutil, struct, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spch

CTL_MAGIC, GFX_MAGIC, CS_MAGIC = bytes.fromhex('34127698'), bytes.fromhex('78563412'), bytes.fromhex('79563412')
HERE = os.path.dirname(os.path.abspath(__file__))
STAGE_BYTE = {0: 'vs', 1: 'ps'}          # control +0x714: an empirical rule, asserted, never generalised
STAGE_COL = {'vs': 'vertex', 'ps': 'pixel', 'cs': 'compute'}


class Refuse(Exception):
    """An input that must not be packaged; the message is shown to the operator."""


# ---------------------------------------------------------------- shader helpers
def ctl_len(ctl):
    n = struct.unpack_from('<I', ctl, 0x20)[0]
    return n if 0x760 <= n < 0x880 else 0x880


def skey(ctl, code):
    return hashlib.sha256(ctl[:ctl_len(ctl)] + code).hexdigest()[:16]


def check(ctl, code):
    if len(ctl) < 0x880 or ctl[:4] != CTL_MAGIC: return 'bad control section'
    if len(ctl) < ctl_len(ctl): return 'control shorter than its own length field'
    if struct.unpack_from('<I', ctl, 0x704)[0] != len(code): return 'control +0x704 does not match the code length'
    return None


def stage_of(ctl):
    v = ctl[0x714]
    return STAGE_BYTE.get(v)


# ---------------------------------------------------------------- inputs
def read_dumps(d):
    """key -> (ctl, code) for every dump that validates; unreadable dumps are reported, never guessed."""
    out, bad = {}, []
    for name in sorted(os.listdir(d)):
        if not name.endswith('.ctl'): continue
        key = name[:-4]; ctl = open(os.path.join(d, name), 'rb').read()
        cp = os.path.join(d, key + '.code')
        code = open(cp, 'rb').read() if os.path.exists(cp) else b''
        why = check(ctl, code)
        if why: bad.append((key, why)); continue
        if skey(ctl, code) != key: bad.append((key, 'key does not recompute')); continue
        out[key] = (ctl, code)
    return out, bad


class Entry:
    __slots__ = ('container', 'si', 'pi', 'ei', 'stage', 'ctl', 'code', 'key')
    def __init__(self, container, si, pi, ei, stage, ctl, code):
        self.container, self.si, self.pi, self.ei, self.stage = container, si, pi, ei, stage
        self.ctl, self.code = ctl, code
        self.key = skey(ctl, code)
    def ident(self):
        return (self.container, self.si, self.pi)


def scan_containers(paths):
    """Every stage entry of every container, in file order. Duplicates are kept so they can be reported."""
    entries, skipped = [], []
    for p in paths:
        try:
            shaders = spch.shaders(open(p, 'rb').read(), os.path.basename(p)[:-6])
        except Exception as e:
            skipped.append((os.path.basename(p), str(e))); continue
        for where, st, ctl, code in shaders:
            lab = where.rpartition('#SPCH#')[2].split('@')[0]
            try: si, pi, ei, stage = lab.split(':')
            except ValueError: skipped.append((os.path.basename(p), f'unparsable label {lab}')); continue
            entries.append(Entry(os.path.basename(p), si, pi, ei, stage, ctl, code))
    return entries, skipped


def index_entries(entries):
    """key -> entry (first occurrence wins; the key is a hash, so a second occurrence must be identical bytes)."""
    idx, conflict = {}, {}
    for e in entries:
        old = idx.get(e.key)
        if old is None: idx[e.key] = e; continue
        if old.ctl != e.ctl or old.code != e.code:
            conflict[e.key] = (f'{old.container}#{old.si}:{old.pi}:{old.ei}:{old.stage}',
                               f'{e.container}#{e.si}:{e.pi}:{e.ei}:{e.stage}')
    return idx, conflict


def program_entries(entries):
    groups = collections.defaultdict(list)
    for e in entries: groups[(e.container, e.si, e.pi)].append(e)
    return groups


def strict_pairs(entries):
    """(vs, ps) pairs that are structurally justified, plus the reasons other programs were not paired."""
    pairs, why = set(), {}
    for ident, es in sorted(program_entries(entries).items()):
        name = f'{ident[0]}#{ident[1]}:{ident[2]}'
        stages = [e.stage for e in es]
        if len(set(stages)) != len(stages): why[name] = f'duplicate stage {stages}'; continue
        if 'gs' in stages or 'hs' in stages or 'ds' in stages: why[name] = f'geometry stage in {stages}'; continue
        if stages != ['vs', 'ps']: why[name] = f'not an ordered [vs, ps] program: {stages}'; continue
        pairs.add((es[0].key, es[1].key))
    return pairs, why


# ---------------------------------------------------------------- packages
def package_bytes(ctl, code):
    head = bytearray(0x38); head[0:8] = b'BTCDBTCD'
    struct.pack_into('<2I', head, 0x28, len(ctl), len(code))
    return bytes(head) + code + ctl


def package_verify(blob, key, stage):
    """Read a package back the way the builder does and prove it carries exactly this key and stage."""
    if len(blob) < 0x38 or blob[:8] != b'BTCDBTCD': return 'package header'
    ctl_n, code_n = struct.unpack_from('<2I', blob, 0x28)
    if len(blob) != 0x38 + code_n + ctl_n: return 'package length'
    code = blob[0x38:0x38 + code_n]; ctl = blob[0x38 + code_n:]
    why = check(ctl, code)
    if why: return why
    if skey(ctl, code) != key: return 'package key does not recompute'
    if stage and stage_of(ctl) != stage: return f'package stage byte {ctl[0x714]} is not {stage}'
    return None


def package_name(stage, key, entry):
    """The key is part of the name, so two shaders can never share (and overwrite) one package."""
    if entry is None: return f'{stage}_runtime_{key}.bin'
    base = os.path.splitext(entry.container)[0]
    return f'{stage}_{base}_s{entry.si}p{entry.pi}_e{entry.ei}_{key}.bin'


# ---------------------------------------------------------------- profile / environment
def expected_profile():
    """The profile DM_GAME/DM_GAMES_DIR resolve to, the same way dmsh_chain.py resolves it."""
    game = os.environ.get('DM_GAME')
    if not game: return None, 'DM_GAME is not set'
    root = os.environ.get('DM_GAMES_DIR') or os.path.join(HERE, '..', '..', 'games')
    return os.path.realpath(os.path.join(root, game)), None


def resolve_profile(arg):
    want, err = expected_profile()
    if err: raise Refuse(f'cannot resolve the build profile: {err}')
    got = os.path.realpath(arg)
    if got != want: raise Refuse(f'--profile {got} is not the profile the build will read ({want})')
    return want


# ---------------------------------------------------------------- selftest
def selftest():
    """Exercise the rules on synthetic data: no game files, no compiler, no containers."""
    fail = []
    def want(cond, what):
        if not cond: fail.append(what)

    def synth(stage_byte, salt):
        ctl = bytearray(0x880); ctl[0:4] = CTL_MAGIC
        struct.pack_into('<I', ctl, 0x20, 0x880); struct.pack_into('<I', ctl, 0x704, 8)
        ctl[0x714] = stage_byte
        code = bytes([salt]) * 8
        ctl[0x800] = salt
        return bytes(ctl), code

    # 1. two dump-only VS and two PS: four distinct packages, correct hashes, no invented pair
    dumps = {}
    for i, sb in enumerate((0, 0, 1, 1)):
        ctl, code = synth(sb, 10 + i); dumps[skey(ctl, code)] = (ctl, code)
    want(len(dumps) == 4, 'four synthetic dumps should have four distinct keys')
    names = set()
    for k, (ctl, code) in dumps.items():
        st = stage_of(ctl)
        blob = package_bytes(ctl, code)
        want(package_verify(blob, k, st) is None, f'package for {k} should verify')
        names.add(package_name(st, k, None))
    want(len(names) == 4, 'dump-only packages must have four distinct names')
    want(strict_pairs([]) [0] == set(), 'no entries must not produce pairs')

    # 2. strict pairing only for an ordered [vs, ps] of one program
    v = Entry('c.wishp', '1', '2', '0', 'vs', *synth(0, 1))
    p = Entry('c.wishp', '1', '2', '1', 'ps', *synth(1, 2))
    g = Entry('c.wishp', '1', '2', '1', 'gs', *synth(2, 3))
    pr, _ = strict_pairs([v, p]); want(pr == {(v.key, p.key)}, '[vs, ps] should pair')
    pr, why = strict_pairs([v, g]); want(pr == set(), 'a [vs, gs] program must not pair')
    pr, why = strict_pairs([v, g, p]); want(pr == set() and 'gs' in ''.join(why.values()), '[vs, gs, ps] must not pair')
    pr, why = strict_pairs([v, p, Entry('c.wishp', '1', '2', '2', 'ps', *synth(1, 4))])
    want(pr == set() and 'duplicate' in ''.join(why.values()), 'duplicate stage must be refused, not merged')
    pr, _ = strict_pairs([v, p, Entry('d.wishp', '1', '2', '1', 'ps', *synth(1, 5))])
    want(pr == {(v.key, p.key)}, 'entries of another container must not join this program')

    # 3. a tampered package must be caught
    blob = bytearray(package_bytes(*dumps[list(dumps)[0]]))
    blob[0x40] ^= 0xff
    want(package_verify(bytes(blob), list(dumps)[0], None) is not None, 'tampered package must not verify')

    # 4. profile mismatch is refused
    os.environ.setdefault('DM_GAME', '010074F013262000')
    os.environ['DM_GAMES_DIR'] = tempfile.mkdtemp()
    try:
        resolve_profile(os.path.join(os.environ['DM_GAMES_DIR'], '010074F013262000'))
        resolve_profile(os.path.join(os.environ['DM_GAMES_DIR'], 'somewhere_else'))
        fail.append('a profile other than DM_GAMES_DIR/DM_GAME must be refused')
    except Refuse:
        pass
    finally:
        shutil.rmtree(os.environ['DM_GAMES_DIR'], ignore_errors=True)

    # 5. the real CLI, end to end, without a compiler: four dump-only shaders, then an incremental round
    root = tempfile.mkdtemp(prefix='refill-cli-')
    try:
        prof = os.path.join(root, 'profile', 'TESTGAME'); os.makedirs(prof)
        open(os.path.join(prof, 'game.tsv'), 'w').write('nvn_tex_base\t0x20\n')
        open(os.path.join(prof, 'shader_map.tsv'), 'w').write('# file\toffset\tstage\tkey\tsource\n')
        open(os.path.join(prof, 'shader_pairs.tsv'), 'w').write('# vs ps\n')
        empty = os.path.join(root, 'containers'); os.makedirs(empty)
        dumps = os.path.join(root, 'shdump'); os.makedirs(dumps)
        made = []
        for i, sb in enumerate((0, 0, 1, 1)):
            ctl, code = synth(sb, 20 + i); k = skey(ctl, code); made.append(k)
            open(os.path.join(dumps, k + '.ctl'), 'wb').write(ctl)
            open(os.path.join(dumps, k + '.code'), 'wb').write(code)
        env = dict(os.environ, DM_GAME='TESTGAME', DM_GAMES_DIR=os.path.join(root, 'profile'))
        cmd = [sys.executable, os.path.abspath(__file__), '--dumps', dumps, '--containers', empty,
               '--profile', prof, '--pkg', os.path.join(root, 'pkg'), '--out', os.path.join(root, 'out'),
               '--allow-dump-only', '--no-build']
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 0, f'CLI run should succeed, got {r.returncode}: {r.stdout[-300:]}')
        rows = [ln.split('\t') for ln in open(os.path.join(prof, 'shader_map.tsv')) if not ln.startswith('#')]
        want(len(rows) == 4, f'four map rows expected, got {len(rows)}')
        want(len({x[0] for x in rows}) == 4, 'four map rows must name four different packages')
        want(all(any(x[3] == k for x in rows) for k in made), 'every synthetic key must have a map row')
        for fn, _off, _st, k, _src in rows:
            blob = open(os.path.join(root, 'pkg', fn), 'rb').read()
            want(package_verify(blob, k, None) is None, f'CLI package {fn} must verify for {k}')
        want(open(os.path.join(prof, 'shader_pairs.tsv')).read().strip() == '# vs ps',
             'dump-only shaders must not produce pairs')
        before = {x[0]: os.path.getsize(os.path.join(root, 'pkg', x[0])) for x in rows}
        # incremental: a fifth shader must be added, the four existing packages untouched
        ctl, code = synth(0, 30); k5 = skey(ctl, code)
        open(os.path.join(dumps, k5 + '.ctl'), 'wb').write(ctl)
        open(os.path.join(dumps, k5 + '.code'), 'wb').write(code)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 0, 'incremental CLI run should succeed')
        rows2 = [ln.split('\t') for ln in open(os.path.join(prof, 'shader_map.tsv')) if not ln.startswith('#')]
        want(len(rows2) == 5, f'five map rows after the incremental round, got {len(rows2)}')
        want(all(os.path.getsize(os.path.join(root, 'pkg', fn)) == sz for fn, sz in before.items()),
             'existing packages must not be rewritten')
        # a profile the build does not read must be refused and left untouched
        other = os.path.join(root, 'other'); os.makedirs(other)
        open(os.path.join(other, 'shader_map.tsv'), 'w').write('# untouched\n')
        i = cmd.index('--profile')
        r = subprocess.run(cmd[:i + 1] + [other] + cmd[i + 2:], env=env, capture_output=True, text=True)
        want(r.returncode == 2 and open(os.path.join(other, 'shader_map.tsv')).read() == '# untouched\n',
             'a mismatched --profile must be refused before writing')
    finally:
        shutil.rmtree(root, ignore_errors=True)

    for f in fail: print(f'FAIL: {f}')
    print(f'selftest: {len(fail)} failure(s)')
    return 1 if fail else 0


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dumps'); ap.add_argument('--containers', nargs='*')
    ap.add_argument('--profile'); ap.add_argument('--pkg'); ap.add_argument('--out')
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--j', default='1')
    ap.add_argument('--allow-dump-only', action='store_true'); ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--no-build', action='store_true')   # write and verify the inputs, then stop (used by the tests)
    a = ap.parse_args()
    if a.selftest: return selftest()
    if not (a.dumps and a.containers is not None and a.profile and a.pkg and a.out):
        ap.error('--dumps, --containers, --profile, --pkg and --out are required')

    try:
        profile = resolve_profile(a.profile)
    except Refuse as e:
        print(f'refused: {e}'); return 2

    dumps, bad = read_dumps(a.dumps)
    print(f'dumps: {len(dumps)} usable, {len(bad)} unusable')
    for k, why in bad: print(f'  unusable {k}: {why}')

    map_path = os.path.join(profile, 'shader_map.tsv')
    pairs_path = os.path.join(profile, 'shader_pairs.tsv')
    have, have_pairs = set(), set()
    for ln in open(map_path):
        c = ln.rstrip('\n').split('\t')
        if not ln.startswith('#') and len(c) > 4: have.add(c[3])
    if os.path.exists(pairs_path):
        for ln in open(pairs_path):
            if ln.strip() and not ln.startswith('#'): have_pairs.add(tuple(ln.split()[:2]))

    entries, skipped = scan_containers(a.containers)
    for n, why in skipped: print(f'  container {n}: skipped ({why})')
    idx, conflict = index_entries(entries)
    for k, (a1, a2) in conflict.items(): print(f'  [WARN] key {k} appears twice with different bytes: {a1} vs {a2}')
    pair_set, unpairable = strict_pairs(entries)

    new, no_source, refused = {}, {}, {}
    for k, (ctl, code) in dumps.items():
        if k in have: continue
        hit = idx.get(k)
        if not hit:
            if not a.allow_dump_only: no_source[k] = 'not in any container sample'; continue
            st = stage_of(ctl)
            if st is None:
                no_source[k] = f'no container and control 0x714 = {ctl[0x714]} (not 0/1): stage unknown, not guessed'
                print(f'  [WARN] {k}: control 0x714 = {ctl[0x714]}, expected 0 (vs) or 1 (ps); left out instead of guessing')
                continue
            new[k] = dict(entry=None, stage=st, ctl=ctl, code=code)
            continue
        if hit.stage == 'gs': refused[k] = f'geometry stage ({hit.container} slct{hit.si} program{hit.pi})'; continue
        if hit.stage not in STAGE_COL: refused[k] = f'unsupported stage {hit.stage}'; continue
        why = check(hit.ctl, hit.code)
        if why: refused[k] = f'container entry does not validate: {why}'; continue
        new[k] = dict(entry=hit, stage=hit.stage, ctl=hit.ctl, code=hit.code)

    print(f'already in map: {len(have)}; new buildable: {len(new)}; no source: {len(no_source)}; refused: {len(refused)}')
    for k, why in refused.items(): print(f'  refused {k}: {why}')
    for name, why in unpairable.items():
        if any(e.key in new for e in program_entries(entries).get(tuple(re.split('[#:]', name)), [])):
            print(f'  not paired: {name}: {why}')

    # ---- everything below is prepared in a temp dir and only then moved into place
    report = dict(new={k: dict(stage=v['stage'],
                               source=(f"{v['entry'].container}#{v['entry'].si}:{v['entry'].pi}:{v['entry'].ei}:{v['entry'].stage}"
                                       if v['entry'] else f'runtime_dump#{k}:{v["stage"]}')) for k, v in new.items()},
                  no_source=no_source, refused=refused, unusable={k: w for k, w in bad},
                  pairs=sorted(pair_set & {(x, y) for x, y in pair_set if x in new or y in new}))
    os.makedirs(a.out, exist_ok=True)
    json.dump(report, open(os.path.join(a.out, 'refill.json'), 'w'), indent=1)
    if a.dry_run or not new:
        print('dry run or nothing to add: nothing written, library not rebuilt'); return 0

    tmp = tempfile.mkdtemp(prefix='refill-')
    try:
        rows, placed = [], {}
        for k, v in sorted(new.items()):
            blob = package_bytes(v['ctl'], v['code'])
            why = package_verify(blob, k, v['stage'])
            if why: raise Refuse(f'package for {k} failed verification: {why}')
            fn = package_name(v['stage'], k, v['entry'])
            open(os.path.join(tmp, fn), 'wb').write(blob)
            rows.append((fn, k, v['stage'],
                         f"{v['entry'].container}#{v['entry'].si}:{v['entry'].pi}:{v['entry'].ei}:{v['entry'].stage}"
                         if v['entry'] else f'runtime_dump#{k}:{v["stage"]}'))
            placed[fn] = blob
        # a pair may only be written when both ends are in the final map and both came from one program
        new_pairs = []
        for vs, ps in sorted(pair_set):
            if vs in new or ps in new:
                if vs not in (have | set(new)) or ps not in (have | set(new)):
                    raise Refuse(f'pair {vs} {ps} would reference a key missing from the map')
                new_pairs.append((vs, ps))
        # no existing package may be silently replaced by different bytes
        os.makedirs(a.pkg, exist_ok=True)
        for fn, blob in placed.items():
            dst = os.path.join(a.pkg, fn)
            if os.path.exists(dst) and open(dst, 'rb').read() != blob:
                raise Refuse(f'{dst} already exists with different bytes')
        for fn, blob in placed.items(): shutil.copyfile(os.path.join(tmp, fn), os.path.join(a.pkg, fn))
        map_add = ''.join(f"{fn}\t0\t{STAGE_COL[st]}\t{k}\t{src}\n" for fn, k, st, src in rows)
        with open(map_path + '.tmp', 'w') as f:
            f.write(open(map_path).read()); f.write(map_add)
        np_add = ''.join(f'{x} {y}\n' for x, y in new_pairs if (x, y) not in have_pairs)
        with open(pairs_path + '.tmp', 'w') as f:
            f.write(open(pairs_path).read() if os.path.exists(pairs_path) else ''); f.write(np_add)
        os.replace(map_path + '.tmp', map_path); os.replace(pairs_path + '.tmp', pairs_path)
        print(f'packaged {len(rows)} records, {len(new_pairs)} pairs')
    except Refuse as e:
        print(f'refused: {e} (nothing written)'); return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if a.no_build:
        print('--no-build: inputs written and verified, chain/build skipped'); return 0
    env = dict(os.environ)
    subprocess.run([sys.executable, os.path.join(HERE, 'dmsh_chain.py'), '--header'], check=True, env=env)
    keys = sorted(have | set(new))
    r = subprocess.run([sys.executable, os.path.join(HERE, 'dmsh_build.py'), a.pkg, a.out] + keys,
                       env=dict(env, J=str(a.j)))
    print(f'build rc={r.returncode} ({len(keys)} keys)')
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
