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
* Validation happens before anything is written, and a refusal changes nothing. Publishing is a recoverable sequence,
  not a cross-file transaction: packages first (unique names, so removing what this run added undoes them), then the
  map and the pairs through a temporary file each with the previous contents kept in memory. If a rename fails the
  previous tables are written back; if even that fails the run says so instead of claiming success.
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
    if not code: return 'empty code area'
    if struct.unpack_from('<I', ctl, 0x704)[0] != len(code): return 'control +0x704 does not match the code length'
    return None


def code_stage(code):
    """The stage the code area itself declares, read the way the production parser reads it (spch._stage_of):
    compute shaders by their magic, graphics shaders by the SPH header's stage bits. None when it is not a stage this
    project can name."""
    if len(code) < 0x34: return None
    try:
        return spch._stage_of(code, '0', 'refill', '0', '0')
    except Exception:
        return None


def ctl_stage_hint(ctl):
    """The empirical control byte, kept only as a cross-check: 0 = vertex, 1 = pixel, anything else unknown."""
    return STAGE_BYTE.get(ctl[0x714])


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
        if not os.path.isfile(p): continue          # a directory or a glob that matched nothing is not a container
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
    cs = code_stage(code)
    if cs is None: return 'code area does not declare a stage this project knows'
    if stage and cs != stage: return f'code stage {cs} is not {stage}'
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


MAP_STAGE = {'vertex': 'vs', 'pixel': 'ps', 'compute': 'cs'}


def validate_map(map_path, pkgdir):
    """Every row of an existing map, checked against the package it names: the whole map, not just the keys.

    A row is accepted only when the file exists, the offset is inside it, and the bytes hash back to the row's key with
    the stage its own code area declares. Rows that share one file+offset with different keys are a corruption signal.
    """
    keys, problems, seen = set(), [], {}
    if not os.path.exists(map_path): return keys, problems
    for n, ln in enumerate(open(map_path), 1):
        if ln.startswith('#') or not ln.strip(): continue
        c = ln.rstrip('\n').split('\t')
        if len(c) < 5: problems.append(f'row {n}: expected 5 columns, got {len(c)}'); continue
        fn, off_s, stage_col, key, _src = c[0], c[1], c[2], c[3], c[4]
        stage = MAP_STAGE.get(stage_col)
        if stage is None: problems.append(f'row {n}: unknown stage column {stage_col!r}'); continue
        try: off = int(off_s)
        except ValueError: problems.append(f'row {n}: offset {off_s!r} is not a number'); continue
        path = os.path.join(pkgdir, fn)
        if not os.path.exists(path): problems.append(f'row {n}: package {fn} is missing'); continue
        blob = open(path, 'rb').read()
        if off < 0 or off >= len(blob): problems.append(f'row {n}: offset {off} outside {fn} ({len(blob)} bytes)'); continue
        why = package_verify(blob[off:], key, stage)
        if why: problems.append(f'row {n}: {key} in {fn}@{off}: {why}'); continue
        prev = seen.setdefault((fn, off), key)
        if prev != key: problems.append(f'row {n}: {fn}@{off} is claimed by {prev} and {key}')
        keys.add(key)
    return keys, problems


def validate_pairs(pairs_path, keys):
    problems = []
    if not os.path.exists(pairs_path): return problems
    for n, ln in enumerate(open(pairs_path), 1):
        if ln.startswith('#') or not ln.strip(): continue
        c = ln.split()
        if len(c) < 2: problems.append(f'pairs row {n}: expected two keys'); continue
        if c[0] not in keys or c[1] not in keys:
            problems.append(f'pairs row {n}: {c[0]} {c[1]} references a key the map does not verify')
    return problems


# ---------------------------------------------------------------- selftest
def selftest():
    """Exercise the rules on synthetic data shaped like the real formats: no game files, no compiler, no containers."""
    fail = []
    def want(cond, what):
        if not cond: fail.append(what)

    def synth(stage, salt, tail=b''):
        """A control section and a code area with a real SPH header (magic + stage bits), so the checks under test see
        the format they will see in production rather than eight arbitrary bytes."""
        ctl = bytearray(0x880); ctl[0:4] = CTL_MAGIC
        struct.pack_into('<I', ctl, 0x20, 0x880)
        code = bytearray(0x40) + bytearray(tail)
        if stage == 'cs':
            code[0:4] = CS_MAGIC
        else:
            code[0:4] = GFX_MAGIC
            bit = {'vs': 1, 'hs': 2, 'ds': 3, 'gs': 4, 'ps': 5}[stage]
            struct.pack_into('<I', code, 0x30, bit << 10)
        struct.pack_into('<I', ctl, 0x704, len(code))
        ctl[0x714] = {'vs': 0, 'ps': 1}.get(stage, 2)
        ctl[0x800] = salt
        return bytes(ctl), bytes(code)

    # 1. packages carry the key in their name, verify, and dump-only shaders never invent a pair
    dumps = {}
    for i, sb in enumerate(('vs', 'vs', 'ps', 'ps')):
        ctl, code = synth(sb, 10 + i); dumps[skey(ctl, code)] = (ctl, code, sb)
    want(len(dumps) == 4, 'four synthetic dumps should have four distinct keys')
    names = {package_name(st, k, None) for k, (ctl, code, st) in dumps.items()}
    want(len(names) == 4, 'dump-only packages must have four distinct names')
    for k, (ctl, code, st) in dumps.items():
        want(package_verify(package_bytes(ctl, code), k, st) is None, f'package for {k} should verify')
    want(strict_pairs([])[0] == set(), 'no entries must not produce pairs')

    # 2. the code area decides the stage; the control byte is only a cross-check
    bad_ctl, _ = synth('vs', 1)
    _, bad_code = synth('vs', 1); bad_code = b'BADCODE!' + bad_code[8:]
    want(code_stage(bad_code) is None, 'a code area with a bad magic declares no stage')
    want(package_verify(package_bytes(bad_ctl, bad_code), skey(bad_ctl, bad_code), 'vs') is not None,
         'the supervisor counterexample (valid control, +0x704 = 8, code BADCODE!) must be refused')
    short_ctl, _ = synth('vs', 2); short_ctl = bytearray(short_ctl); short_code = b'\x78\x56\x34\x12'
    struct.pack_into('<I', short_ctl, 0x704, len(short_code))
    want(package_verify(package_bytes(short_ctl, short_code), skey(short_ctl, short_code), 'vs') is not None,
         'a code area shorter than an SPH header must be refused')
    empty_ctl, _ = synth('vs', 3); empty_ctl = bytearray(empty_ctl)
    struct.pack_into('<I', empty_ctl, 0x704, 0)
    want(package_verify(package_bytes(empty_ctl, b''), skey(empty_ctl, b''), 'vs') is not None,
         'an empty code area must be refused')
    v_ctl, v_code = synth('vs', 4); p_ctl, p_code = synth('ps', 5)
    want(package_verify(package_bytes(v_ctl, v_code), skey(v_ctl, v_code), 'ps') is not None,
         'a vertex code area declared as pixel must be refused')
    # compute is a real stage: it verifies as cs and is refused when declared as something else
    c_ctl, c_code = synth('cs', 6)
    want(code_stage(c_code) == 'cs', 'a compute code area declares cs')
    want(package_verify(package_bytes(c_ctl, c_code), skey(c_ctl, c_code), 'cs') is None,
         'a compute package must verify when it is declared compute')
    want(package_verify(package_bytes(c_ctl, c_code), skey(c_ctl, c_code), 'ps') is not None,
         'a compute package declared as pixel must be refused')
    want(ctl_stage_hint(c_ctl) is None, 'the empirical control byte does not name compute')

    # 3. strict pairing: one ordered [vs, ps] of one program, nothing else
    v = Entry('c.wishp', '1', '2', '0', 'vs', *synth('vs', 1))
    p = Entry('c.wishp', '1', '2', '1', 'ps', *synth('ps', 2))
    g = Entry('c.wishp', '1', '2', '1', 'gs', *synth('gs', 3))
    want(strict_pairs([v, p])[0] == {(v.key, p.key)}, '[vs, ps] should pair')
    want(strict_pairs([v, g])[0] == set(), 'a [vs, gs] program must not pair')
    pr, why = strict_pairs([v, g, p])
    want(pr == set() and 'gs' in ''.join(why.values()), '[vs, gs, ps] must not pair')
    pr, why = strict_pairs([v, p, Entry('c.wishp', '1', '2', '2', 'ps', *synth('ps', 4))])
    want(pr == set() and 'duplicate' in ''.join(why.values()), 'duplicate stage must be refused, not merged')
    want(strict_pairs([v, p, Entry('d.wishp', '1', '2', '1', 'ps', *synth('ps', 5))])[0] == {(v.key, p.key)},
         'entries of another container must not join this program')

    # 4. a tampered package is caught
    k0 = list(dumps)[0]
    blob = bytearray(package_bytes(*dumps[k0][:2])); blob[0x41] ^= 0xff
    want(package_verify(bytes(blob), k0, None) is not None, 'tampered package must not verify')

    # 5. profile mismatch is refused
    root0 = tempfile.mkdtemp(prefix='refill-prof-')
    old_env = {k: os.environ.get(k) for k in ('DM_GAME', 'DM_GAMES_DIR')}
    try:
        os.environ['DM_GAME'] = 'TESTGAME'; os.environ['DM_GAMES_DIR'] = root0
        resolve_profile(os.path.join(root0, 'TESTGAME'))
        try:
            resolve_profile(os.path.join(root0, 'somewhere_else')); fail.append('a profile other than DM_GAMES_DIR/DM_GAME must be refused')
        except Refuse: pass
    finally:
        for k, v_ in old_env.items():
            if v_ is None: os.environ.pop(k, None)
            else: os.environ[k] = v_
        shutil.rmtree(root0, ignore_errors=True)

    # 6. the real CLI, end to end, without a compiler
    root = tempfile.mkdtemp(prefix='refill-cli-')
    try:
        prof = os.path.join(root, 'profile', 'TESTGAME'); os.makedirs(prof)
        open(os.path.join(prof, 'game.tsv'), 'w').write('nvn_tex_base\t0x20\n')
        open(os.path.join(prof, 'shader_map.tsv'), 'w').write('# file\toffset\tstage\tkey\tsource\n')
        open(os.path.join(prof, 'shader_pairs.tsv'), 'w').write('# vs ps\n')
        empty = os.path.join(root, 'containers'); os.makedirs(empty)
        dumps_dir = os.path.join(root, 'shdump'); os.makedirs(dumps_dir)
        env = dict(os.environ, DM_GAME='TESTGAME', DM_GAMES_DIR=os.path.join(root, 'profile'))
        cmd = [sys.executable, os.path.abspath(__file__), '--dumps', dumps_dir, '--containers', empty,
               '--profile', prof, '--pkg', os.path.join(root, 'pkg'), '--out', os.path.join(root, 'out'),
               '--allow-dump-only', '--no-build']

        def put(stage, salt):
            ctl, code = synth(stage, salt); k = skey(ctl, code)
            open(os.path.join(dumps_dir, k + '.ctl'), 'wb').write(ctl)
            open(os.path.join(dumps_dir, k + '.code'), 'wb').write(code)
            return k

        made = [put('vs', 20), put('vs', 21), put('ps', 22), put('ps', 23)]
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 0, f'CLI run should succeed, got {r.returncode}: {r.stdout[-300:]}')
        rows = [ln.split('\t') for ln in open(os.path.join(prof, 'shader_map.tsv')) if not ln.startswith('#')]
        want(len(rows) == 4, f'four map rows expected, got {len(rows)}')
        want(len({x[0] for x in rows}) == 4, 'four map rows must name four different packages')
        want(all(any(x[3] == k for x in rows) for k in made), 'every synthetic key must have a map row')
        for fn, off, st, k, src in rows:
            want(package_verify(open(os.path.join(root, 'pkg', fn), 'rb').read()[int(off):], k, None) is None,
                 f'CLI package {fn} must verify for {k}')
        want(open(os.path.join(prof, 'shader_pairs.tsv')).read().strip() == '# vs ps',
             'dump-only shaders must not produce pairs')
        before = {x[0]: hashlib.sha256(open(os.path.join(root, 'pkg', x[0]), 'rb').read()).hexdigest() for x in rows}
        k5 = put('vs', 30)
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 0, 'incremental CLI run should succeed')
        rows2 = [ln.split('\t') for ln in open(os.path.join(prof, 'shader_map.tsv')) if not ln.startswith('#')]
        want(len(rows2) == 5, f'five map rows after the incremental round, got {len(rows2)}')
        want(all(hashlib.sha256(open(os.path.join(root, 'pkg', fn), 'rb').read()).hexdigest() == h
                 for fn, h in before.items()), 'existing packages must not change, byte for byte')

        # a map row that does not verify must stop the run before anything is written
        map_p = os.path.join(prof, 'shader_map.tsv')
        good = open(map_p).read()
        open(map_p, 'w').write(good + 'ps_runtime_deadbeefdeadbeef.bin\t0\tpixel\tdeadbeefdeadbeef\truntime_dump#deadbeefdeadbeef:ps\n')
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 2 and open(map_p).read().endswith('deadbeefdeadbeef:ps\n'), 'a bad existing row must be refused')
        want(open(os.path.join(prof, 'shader_pairs.tsv')).read().strip() == '# vs ps', 'a refusal must not touch pairs')
        open(map_p, 'w').write(good)
        # a package with the same name but different bytes must be refused, not overwritten
        rows = [ln.split('\t') for ln in open(map_p) if not ln.startswith('#')]
        victim = os.path.join(root, 'pkg', rows[0][0])
        keep = open(victim, 'rb').read()
        open(victim, 'wb').write(b'X' * len(keep))
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
        want(r.returncode == 2, 'a same-named package with different bytes must be refused')
        open(victim, 'wb').write(keep)
        # the publish path: an injected failure between the two renames must leave the profile as it was, and must not
        # delete a package that was already there before the run (the reported P1)
        map_before, pairs_before = open(map_p).read(), open(os.path.join(prof, 'shader_pairs.tsv')).read()
        pre_ctl, pre_code = synth('vs', 40)           # already has its package: this run must reuse it, not own it
        pre_key, pre_blob = skey(pre_ctl, pre_code), package_bytes(pre_ctl, pre_code)
        pre_fn = package_name('vs', pre_key, None)
        open(os.path.join(dumps_dir, pre_key + '.ctl'), 'wb').write(pre_ctl)
        open(os.path.join(dumps_dir, pre_key + '.code'), 'wb').write(pre_code)
        open(os.path.join(root, 'pkg', pre_fn), 'wb').write(pre_blob)
        new_key = put('ps', 41)                      # genuinely new: this run creates it and must remove it on rollback
        r = subprocess.run(cmd, env=dict(env, DM_REFILL_TEST_FAIL='pairs'), capture_output=True, text=True)
        want(r.returncode == 3, f'injected publish failure should report rc 3, got {r.returncode}')
        want(open(map_p).read() == map_before, 'the map must be recovered after a failed publish')
        want(open(os.path.join(prof, 'shader_pairs.tsv')).read() == pairs_before, 'pairs must be untouched after a failed publish')
        want(os.path.exists(os.path.join(root, 'pkg', pre_fn)), 'a package that existed before the run must survive a rollback')
        want(open(os.path.join(root, 'pkg', pre_fn), 'rb').read() == pre_blob, 'that package must keep its exact bytes')
        want(not os.path.exists(os.path.join(root, 'pkg', package_name('ps', new_key, None))),
             'the package this run created must be removed by the rollback')
        # a --profile the build does not read is refused before writing
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
    have, map_problems = validate_map(map_path, a.pkg)
    if map_problems:
        print(f'refused: the existing map has {len(map_problems)} row(s) that do not verify; not writing anything')
        for p_ in map_problems[:8]: print(f'  {p_}')
        return 2
    pair_problems = validate_pairs(pairs_path, have)
    if pair_problems:
        print(f'refused: the existing pairs file has {len(pair_problems)} entr(ies) that do not verify; not writing anything')
        for p_ in pair_problems[:8]: print(f'  {p_}')
        return 2
    have_pairs = set()
    if os.path.exists(pairs_path):
        for ln in open(pairs_path):
            if ln.strip() and not ln.startswith('#'): have_pairs.add(tuple(ln.split()[:2]))

    entries, skipped = scan_containers(a.containers)
    for n, why in skipped: print(f'  container {n}: skipped ({why})')
    idx, conflict = index_entries(entries)
    for k, (a1, a2) in conflict.items():
        print(f'  [REFUSE] key {k} appears twice in the containers with different bytes: {a1} vs {a2}')
    pair_set, unpairable = strict_pairs(entries)

    new, no_source, refused = {}, {}, {}
    for k, (ctl, code) in dumps.items():
        if k in have: continue
        hit = idx.get(k)
        if k in conflict:
            refused[k] = 'the containers declare this key twice with different bytes'
            continue
        if not hit:
            if not a.allow_dump_only: no_source[k] = 'not in any container sample'; continue
            st = code_stage(code)
            if st not in ('vs', 'ps'):
                no_source[k] = f'no container and the code area declares {st or "no known stage"}: not guessed'
                print(f'  [WARN] {k}: no container, code stage {st}; left out instead of guessing')
                continue
            # the control byte is only a cross-check here, never the proof of the stage
            hint = ctl_stage_hint(ctl)
            if hint is not None and hint != st:
                refused[k] = f'code says {st} but control +0x714 says {hint}: refusing rather than choosing'
                continue
            new[k] = dict(entry=None, stage=st, ctl=ctl, code=code)
            continue
        if hit.stage == 'gs': refused[k] = f'geometry stage ({hit.container} slct{hit.si} program{hit.pi})'; continue
        if hit.stage not in STAGE_COL: refused[k] = f'unsupported stage {hit.stage}'; continue
        why = check(hit.ctl, hit.code)
        if why: refused[k] = f'container entry does not validate: {why}'; continue
        if code_stage(hit.code) != hit.stage:
            refused[k] = f'container says {hit.stage} but its code area says {code_stage(hit.code)}'; continue
        # the container entry and the runtime dump must describe the same code; only the control tail may differ, because
        # the key covers ctl[:ctl_len] and nothing else
        if hit.code != code:
            refused[k] = 'container code bytes differ from the runtime dump'
            continue
        if hit.ctl[:ctl_len(hit.ctl)] != ctl[:ctl_len(ctl)]:
            refused[k] = 'container control bytes differ from the runtime dump'
            continue
        if hit.ctl != ctl:
            print(f'  note {k}: control tail beyond +{ctl_len(ctl):#x} differs from the runtime dump (not hashed); container bytes kept')
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
    created, map_old, pairs_old = [], None, None
    try:
        rows, placed = [], {}
        for k, v in sorted(new.items()):
            blob = package_bytes(v['ctl'], v['code'])
            why = package_verify(blob, k, v['stage'])
            if why: raise Refuse(f'package for {k} failed verification: {why}')
            fn = package_name(v['stage'], k, v['entry'])
            if fn in placed and placed[fn] != blob: raise Refuse(f'two different shaders want the package name {fn}')
            placed[fn] = blob
            open(os.path.join(tmp, fn), 'wb').write(blob)
            rows.append((fn, k, v['stage'],
                         f"{v['entry'].container}#{v['entry'].si}:{v['entry'].pi}:{v['entry'].ei}:{v['entry'].stage}"
                         if v['entry'] else f"runtime_dump#{k}:{v['stage']}"))
        new_pairs = []
        for vs, ps in sorted(pair_set):
            if vs in new or ps in new:
                if vs not in (have | set(new)) or ps not in (have | set(new)):
                    raise Refuse(f'pair {vs} {ps} would reference a key missing from the map')
                new_pairs.append((vs, ps))
        # Pre-check every target before touching the profile. A package that is already there with the same bytes is
        # left completely alone: it is not replaced (its inode and timestamps stay), and it is never added to `created`,
        # because a rollback must only remove files this run actually made. The earlier version replaced it and
        # recorded it, so a failed publish deleted a package that had existed before the run.
        os.makedirs(a.pkg, exist_ok=True)
        reuse = set()
        for fn, blob in placed.items():
            dst = os.path.join(a.pkg, fn)
            if not os.path.exists(dst): continue
            if open(dst, 'rb').read() != blob:
                raise Refuse(f'{dst} already exists with different bytes')
            reuse.add(fn)
        # publish: only the genuinely new packages, each through its own temporary file, then the two tables. The
        # previous table contents are kept in memory so a failed rename can put them back. Recoverable sequence, not a
        # cross-file filesystem transaction.
        strays = []
        for fn in placed:
            if fn in reuse: continue
            dst = os.path.join(a.pkg, fn); tmp_dst = dst + f'.tmp{os.getpid()}'
            try:
                shutil.copyfile(os.path.join(tmp, fn), tmp_dst); os.replace(tmp_dst, dst); created.append(dst)
            except OSError:
                strays.append(tmp_dst); raise
            finally:
                for s_ in strays:
                    try: os.unlink(s_)
                    except OSError: pass
                strays = []
        if reuse: print(f'reused {len(reuse)} package(s) that were already present with identical bytes')
        map_old = open(map_path).read() if os.path.exists(map_path) else ''
        pairs_old = open(pairs_path).read() if os.path.exists(pairs_path) else ''
        map_add = ''.join(f"{fn}\t0\t{STAGE_COL[st]}\t{k}\t{src}\n" for fn, k, st, src in rows)
        np_add = ''.join(f'{x} {y}\n' for x, y in new_pairs if (x, y) not in have_pairs)
        mt, pt = map_path + f'.tmp{os.getpid()}', pairs_path + f'.tmp{os.getpid()}'
        open(mt, 'w').write(map_old + map_add)
        open(pt, 'w').write(pairs_old + np_add)
        os.replace(mt, map_path)
        if os.environ.get('DM_REFILL_TEST_FAIL') == 'pairs':      # test hook: prove the rollback path runs
            raise OSError('injected failure between the two renames')
        try:
            os.replace(pt, pairs_path)
        except OSError:
            open(map_path, 'w').write(map_old)                    # put the map back before reporting the failure
            raise
        print(f'packaged {len(rows)} records, {len(new_pairs)} pairs')
    except Refuse as e:
        for f_ in created:
            try: os.unlink(f_)
            except OSError: pass
        print(f'refused: {e} (profile left as it was)'); return 2
    except OSError as e:
        removed = 0
        for f_ in created:
            try: os.unlink(f_); removed += 1
            except OSError: pass
        restored = True
        if map_old is not None:
            try: open(map_path, 'w').write(map_old)
            except OSError: restored = False; print(f'  [RED] could not restore {map_path}; it may hold the new rows')
        if pairs_old is not None:
            try: open(pairs_path, 'w').write(pairs_old)
            except OSError: restored = False; print(f'  [RED] could not restore {pairs_path}')
        if restored:
            print(f'publish failed: {e}; previous map and pairs restored, {removed} package(s) this run added removed, '
                  f'{len(placed) - removed} unchanged')
        else:
            print(f'publish failed: {e}; RECOVERY INCOMPLETE (see the [RED] lines above) - inspect the profile')
        return 3
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
