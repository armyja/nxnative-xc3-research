"""The real build entry, stopped by the geometry preflight, and what it must not touch.

A synthetic game profile (DM_GAMES_DIR, outside the repository), a synthetic map and package, and a stand-in
translator that only records that it was asked to run: no real translation, no Metal compile, no game assets.
Run: python3 dm/gfx/tests/test_dmsh_build_entry.py
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '../../..'))
TOOLS = os.path.join(REPO, 'dm/gfx/tools')
BUILD = os.path.join(TOOLS, 'dmsh_build.py')
CHAIN = os.path.join(TOOLS, 'dmsh_chain.py')
PY = sys.executable
CTL_SIZE = 0x880
CODE_SIZE = 0x60


def dotnet_root():
    """Where a .NET runtime actually is, so the build's own tool check can start the translator."""
    root = os.environ.get('DOTNET_ROOT_ARM64') or os.environ.get('DOTNET_ROOT')
    if root and os.path.isdir(root):
        return root
    for base in ('/opt/homebrew/Cellar/dotnet', '/usr/local/share/dotnet', os.path.expanduser('~/.dotnet')):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base), reverse=True):
            cand = os.path.join(base, name, 'libexec') if os.path.isdir(os.path.join(base, name, 'libexec')) else os.path.join(base, name)
            if os.path.isdir(os.path.join(cand, 'shared')):
                return cand
        if os.path.isdir(os.path.join(base, 'shared')):
            return base
    return None


def record(code_stage_magic):
    """One build record: 'BTCDBTCD' + 0x30 header, then the code area, then the control section."""
    code = bytes.fromhex(code_stage_magic) + bytes(CODE_SIZE - 4)
    ctl = bytearray(CTL_SIZE)
    ctl[0:4] = bytes.fromhex('34127698')
    struct.pack_into('<I', ctl, 0x20, CTL_SIZE)
    struct.pack_into('<I', ctl, 0x700, len(code))      # c1 starts at the end: empty
    struct.pack_into('<I', ctl, 0x704, len(code))
    head = bytearray(0x38)
    head[0:8] = b'BTCDBTCD'
    struct.pack_into('<2I', head, 0x28, len(ctl), len(code))
    return bytes(head) + code + bytes(ctl)


class Entry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix='dmsh_entry_')
        cls.profdir = os.path.join(cls.root, 'prof')
        cls.tid = '0999999999999999'
        prof = os.path.join(cls.profdir, cls.tid)
        os.makedirs(prof)
        # the profile constants do not reach the guard; they are copied so the script gets past its own checks
        src = os.path.join(REPO, 'dm/games/0100A5C00D162000/game.tsv')
        shutil.copyfile(src, os.path.join(prof, 'game.tsv'))
        cls.keys = {'vs': 'kv0', 'ps': 'kp0', 'cs': 'kc0', 'gs': 'kg0'}
        rows = ['# kind: evidence  synthetic rows for the entry test']
        for st in ('vs', 'ps', 'cs', 'gs'):
            rows.append(f'{st}_pkg.bin\t0\t{"pixel" if st == "ps" else st}\t{cls.keys[st]}\tpc0')
        with open(os.path.join(prof, 'shader_map.tsv'), 'w') as f: f.write('\n'.join(rows) + '\n')
        for name in ('shader_map.tsv.conflicts.tsv', 'shader_facts.tsv', 'shader_pairs.tsv'):
            with open(os.path.join(prof, name), 'w') as f: f.write('# empty\n')
        # the header the build insists on holding the current chain version
        cls.env_base = dict(os.environ, DM_GAME=cls.tid, DM_GAMES_DIR=cls.profdir)
        r = subprocess.run([PY, CHAIN, '--header'], env=cls.env_base, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        # a package with one record per stage, each named after the stage the build reads from name[:2]
        cls.pkg = os.path.join(cls.root, 'pkg'); os.makedirs(cls.pkg)
        for st, magic in (('vs', '78563412'), ('ps', '78563412'), ('cs', '79563412'), ('gs', '78563412')):
            with open(os.path.join(cls.pkg, f'{st}_pkg.bin'), 'wb') as f: f.write(record(magic))
        # A stand-in translator in a copy of the real tool directory: check_tools fingerprints the DLLs beside the
        # executable and asks it for its source sha, so the wrapper must answer that query and must be the only
        # thing that runs when a real translation would have started.
        cls.xdir = os.path.join(cls.root, 'xbin')
        shutil.copytree(os.path.join(TOOLS, 'dmsh_xlate_bin'), cls.xdir)
        cls.fake = os.path.join(cls.xdir, 'dmsh_xlate')
        os.unlink(cls.fake)
        with open(cls.fake, 'w') as f:
            f.write('#!/bin/sh\n'
                    'if [ "$1" = "--source-sha" ]; then echo 38a1c0b4e3ebd5fa; exit 0; fi\n'
                    'touch "$XLATE_RAN"\nexit 1\n')
        os.chmod(cls.fake, 0o755)
        cls.dotnet = dotnet_root()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def run_build(self, out, *keys, iosout=None):
        env = dict(self.env_base, XLATE=self.fake, XLATE_RAN=os.path.join(self.root, 'ran'),
                   DMSH_CAS=os.path.join(self.root, 'cas'))
        for k in list(env):
            if k.startswith(('XLATE_DEBUG', 'XLATE_REDUCED')): env.pop(k)
        if not os.path.exists(env['XLATE_RAN']): pass
        else: os.unlink(env['XLATE_RAN'])
        for k in ('DOTNET_ROOT', 'DOTNET_ROOT_ARM64'):
            env.pop(k, None)
        if self.dotnet:
            env['DOTNET_ROOT'] = env['DOTNET_ROOT_ARM64'] = self.dotnet
        if iosout: env['IOSOUT'] = iosout
        r = subprocess.run([PY, BUILD, self.pkg, out, *keys], env=env, capture_output=True, text=True)
        return r, env['XLATE_RAN']

    def test_geometry_selection_is_refused_and_leaves_nothing(self):
        out = os.path.join(self.root, 'o1'); ios = os.path.join(self.root, 'i1')
        r, ran = self.run_build(out, self.keys['gs'], iosout=ios)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unsupported geometry stage', r.stdout + r.stderr)
        self.assertIn(self.keys['gs'], r.stdout + r.stderr)
        self.assertIn('gs_pkg.bin#0', r.stdout + r.stderr)
        self.assertFalse(os.path.exists(out), 'a rejected build must not create the output directory')
        self.assertFalse(os.path.exists(ios), 'a rejected build must not create the iOS output directory')
        self.assertFalse(os.path.exists(ran), 'a rejected build must not call the translator')

    def test_selecting_everything_with_geometry_is_refused(self):
        out = os.path.join(self.root, 'o2')
        r, ran = self.run_build(out, iosout=os.path.join(self.root, 'i2'))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unsupported geometry stage', r.stdout + r.stderr)
        self.assertFalse(os.path.exists(out))
        self.assertFalse(os.path.exists(ran))

    def test_a_cached_geometry_entry_does_not_bypass_the_guard(self):
        out = os.path.join(self.root, 'o3')
        cache = os.path.join(out, 'cas', 'index'); os.makedirs(cache)
        with open(os.path.join(cache, self.keys['gs'] + '.json'), 'w') as f: f.write('{"digest":"x"}')
        r, ran = self.run_build(out, self.keys['gs'])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('unsupported geometry stage', r.stdout + r.stderr)
        self.assertFalse(os.path.exists(ran), 'the cache must not be consulted')
        self.assertEqual(sorted(os.listdir(cache)), [self.keys['gs'] + '.json'], 'the cache is untouched')

    def test_an_explicit_subset_passes_the_preflight(self):
        # No geometry selected: the run must get past the guard and reach the per-key work. The output library
        # directory is created after the guard, so its existence is the observable, and the stand-in translator
        # records whether the run reached translation.
        out = os.path.join(self.root, 'o4'); ios = os.path.join(self.root, 'i4')
        r, ran = self.run_build(out, self.keys['vs'], self.keys['ps'], iosout=ios)
        self.assertNotIn('unsupported geometry stage', r.stdout + r.stderr)
        libs = [d for d in os.listdir(out)] if os.path.isdir(out) else []
        self.assertTrue(any(d.startswith('b-') for d in libs), 'the build passed the guard and created its library directory')
        self.assertTrue(os.path.isdir(ios), 'the iOS output directory is created once the guard is passed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
