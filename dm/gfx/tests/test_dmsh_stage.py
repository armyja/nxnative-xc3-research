"""Geometry preflight for the offline build, and where it sits on the real build path.

The guard itself is behavioural; the placement assertions read dmsh_build.py's own source, because the build
script exits on a tool-fingerprint check long before the selection when the translator is not built, so it
cannot be launched here. Run: python3 dm/gfx/tests/test_dmsh_stage.py
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.join(HERE, '../tools')
sys.path.insert(0, TOOLS)
import dmsh_stage

BUILD = os.path.join(TOOLS, 'dmsh_build.py')


class Preflight(unittest.TestCase):
    def loc(self, **names):
        """A mapping: key → (record name, offset), the same shape dmsh_build keeps in `loc`."""
        return {k: (v, 0x100) for k, v in names.items()}

    def test_selected_geometry_is_refused(self):
        loc = self.loc(a1='vs_group', a2='ps_group', a3='gs_group')
        bad = dmsh_stage.unsupported(['a1', 'a3'], loc, {})
        self.assertEqual(len(bad), 1)
        key, src, stage = bad[0]
        self.assertEqual((key, stage), ('a3', 'gs'))
        self.assertEqual(src, 'gs_group#256')
        lines = dmsh_stage.refusal_lines(bad)
        self.assertEqual(len(lines), 1)
        self.assertIn('a3', lines[0])
        self.assertIn('gs_group#256', lines[0])
        self.assertIn('unsupported geometry stage', lines[0])
        self.assertTrue(lines[0].startswith('[RED] '))

    def test_selecting_everything_that_has_geometry_is_refused(self):
        loc = self.loc(a1='vs_g', a2='ps_g', a3='gs_g')
        self.assertEqual(len(dmsh_stage.unsupported(sorted(loc), loc, {})), 1)

    def test_a_map_holding_geometry_does_not_block_a_subset(self):
        # The map contains a geometry record, but the build was asked for vertex / pixel / compute only.
        loc = self.loc(a1='vs_g', a2='ps_g', a3='gs_g', a4='cs_g')
        self.assertEqual(dmsh_stage.unsupported(['a1', 'a2', 'a4'], loc, {}), [])

    def test_embedded_rows_take_their_stage_from_the_table(self):
        # An embedded main row's name does not start with a stage; the mapping table supplies it, as job_for does.
        loc = {'e1': ('main.rodata@0x1000', 0x1000), 'e2': ('main.rodata@0x2000', 0x2000)}
        self.assertEqual(dmsh_stage.unsupported(['e1'], loc, {'e1': 'vs'}), [])
        bad = dmsh_stage.unsupported(['e2'], loc, {'e2': 'gs'})
        self.assertEqual([k for k, _, _ in bad], ['e2'])

    def test_the_table_overrides_a_package_name(self):
        # The mapping table wins over name[:2] exactly as stage_of.get(key, name[:2]) does.
        loc = self.loc(a1='gs_named_but_vertex')
        self.assertEqual(dmsh_stage.unsupported(['a1'], loc, {'a1': 'vs'}), [])
        self.assertEqual([k for k, _, _ in dmsh_stage.unsupported(['a1'], loc, {'a1': 'gs'})], ['a1'])

    def test_no_key_means_every_key(self):
        # dmsh_build turns an empty selection into "all": the guard is handed that same list.
        loc = self.loc(a1='vs_g', a2='gs_g')
        keys = sorted(loc)
        self.assertEqual([k for k, _, _ in dmsh_stage.unsupported(keys, loc, {})], ['a2'])

    def test_the_guard_never_shells_out(self):
        # Refusing must not reach the translator or the Metal compiler: this module has no way to.
        src = open(os.path.join(TOOLS, 'dmsh_stage.py'), encoding='utf-8').read()
        for word in ('subprocess', 'os.system', 'xcrun', 'metallib', 'XLATE'):
            self.assertNotIn(word, src)


class Placement(unittest.TestCase):
    """Where the guard sits in dmsh_build.py, read from the script itself."""

    def setUp(self):
        self.lines = open(BUILD, encoding='utf-8').read().split('\n')

    def index_of(self, needle, after=0):
        for i in range(after, len(self.lines)):
            if needle in self.lines[i]: return i
        return -1

    def test_build_imports_and_calls_the_guard(self):
        imports = [l for l in self.lines[:25] if l.startswith('sys.path.insert')]
        self.assertTrue(imports and 'dmsh_stage' in imports[0], 'the build must import the guard module')
        self.assertGreaterEqual(self.index_of('dmsh_stage.unsupported('), 0)
        self.assertGreaterEqual(self.index_of('sys.exit(1)', after=self.index_of('dmsh_stage.unsupported(')), 0)

    def test_the_guard_runs_before_the_cache_and_any_output(self):
        sel = self.index_of('keys = sorted(want)')
        call = self.index_of('dmsh_stage.unsupported(')
        makedirs = self.index_of('os.makedirs(out, exist_ok=True)')
        lookup = self.index_of('cache_lookup(', after=sel)     # the call inside the loop, not the definition
        prefill = self.index_of('MTL.fill(', after=sel)
        self.assertGreaterEqual(sel, 0)
        self.assertGreater(call, sel, 'the guard must run after the selection is known')
        self.assertLess(call, makedirs, 'a refusal must not create the output directory first')
        self.assertLess(call, lookup, 'a cached geometry entry must not be reached')
        self.assertLess(call, prefill, 'a refusal must not import libraries into the compile cache first')


if __name__ == '__main__':
    unittest.main(verbosity=2)
