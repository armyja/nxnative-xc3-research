"""Storage-buffer rw comes from the pinned BufferUsageFlags Write bit, not from MSL text.

The production reflect() lives in dmsh_build.py, which runs a build when imported, so this test extracts the
function from its source with ast and drives it with synthetic MSL and reflection data. No import of dmsh_build,
no game assets, no profile.

Ground truth is the pinned ABI, not the mask in the implementation: the vendored
dm/third_party/ryujinx/src/Ryujinx.Graphics.Shader/BufferUsageFlags.cs declares
    [Flags] enum BufferUsageFlags : byte { None = 0, Write = 1 << 0 }
and ResourceManager.cs sets Write only when the storage-buffer slot is written. Bit 1 is not a defined flag:
the 0/1/2/3 cases below pin what bit 0 means (and that an unknown bit alone is not Write); they do not claim the
pinned enum has any other member.

The flags=1 case is the counterexample for the old `flags & 2` mask: it returned rw False and fails this test.
Run: python3 dm/gfx/tests/test_reflect_sbuf_rw.py
"""
import ast
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '../../..'))
BUILD = os.path.join(REPO, 'dm/gfx/tools/dmsh_build.py')

WRITE = 1  # pinned Ryujinx BufferUsageFlags.Write = 1 << 0
# 2 is not a defined flag; it is only here to show that the old mask's bit is not the Write bit.
EXPECT_RW = {0: False, WRITE: True, 2: False, WRITE | 2: True}


def production_reflect():
    """The real function from dmsh_build.py, compiled without importing the module (import would start a build)."""
    source = open(BUILD, encoding='utf-8').read()
    tree = ast.parse(source, BUILD)
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'reflect')
    namespace = {'re': re, 'SSBO': {'vs': 0x110, 'ps': 0x510, 'cs': 0}}
    exec(compile(ast.get_source_segment(source, fn), BUILD, 'exec'), namespace)
    return namespace['reflect']


def msl(*members, body=()):
    text = 'struct spvDescriptorSetBuffer0 {\n' + ''.join('    %s\n' % m for m in members) + '};\n'
    return text + ''.join('    %s\n' % line for line in body)


def res(*rows):
    """rows: (binding, cb_slot, cb_offset_words, flags)"""
    return {'sbufs': [{'binding': b, 'slot': 0, 'cb_slot': cb, 'cb_offset': off, 'flags': flags}
                      for b, cb, off, flags in rows]}


class ReflectSbufRw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reflect = staticmethod(production_reflect())

    def sbufs(self, source, data, stage='ps'):
        return [e for e in self.reflect('synthetic', stage, source, data) if e['kind'] == 'sbuf']

    def test_write_bit_comes_from_flags_not_msl_text(self):
        """Store, atomic and read-only bodies give the same rw: the MSL text is not a writer detector."""
        bodies = (
            (),
            ('(*spvDescriptorSet0.fp_s0)._m0[0] = 0u;',),
            ('atomic_store_explicit((device atomic_uint*)&fp_s0._m0[0], 0u, memory_order_relaxed);',),
        )
        for body in bodies:
            for flags, want in EXPECT_RW.items():
                source = msl('device _15* fp_s0 [[id(0)]];', body=body)
                got = self.sbufs(source, res((1, 0, 324, flags)))[0]
                self.assertIs(got['rw'], want, f'flags={flags} body={body!r}')
                self.assertIsInstance(got['rw'], bool)

    def test_flags_one_is_a_writer(self):
        """The case the old `flags & 2` mask got wrong."""
        got = self.sbufs(msl('device _15* fp_s0 [[id(0)]];'), res((1, 0, 324, WRITE)))[0]
        self.assertIs(got['rw'], True)
        self.assertEqual(got['reg'], 0)   # rw and reg are separate: this binding also resolves here

    def test_binding_sorted_index_and_reg(self):
        """The response is sorted by binding before index lookup; index 0..2 are vp_s0..2, not file order."""
        source = msl('device _25* vp_s0 [[id(0)]];', 'device _25* vp_s1 [[id(1)]];', 'device _25* vp_s2 [[id(2)]];')
        data = res((3, 0, 76, WRITE), (1, 0, 68, 0), (2, 0, 72, WRITE))
        got = [(b['index'], b['reg'], b['rw']) for b in self.sbufs(source, data, 'vs')]
        self.assertEqual(got, [(0, 0, False), (1, 1, True), (2, 2, True)])

    def test_rw_is_independent_of_slot_resolution(self):
        """A writer with no resolvable reg is still rw; a reader with a resolvable reg stays read-only."""
        source = msl('device _15* fp_s0 [[id(0)]];', 'device _15* fp_s1 [[id(1)]];', 'device _15* fp_s2 [[id(2)]];')
        data = res((1, 0, 324, WRITE), (2, 1, 328, 0), (3, 1, 332, WRITE))
        a, b, c = self.sbufs(source, data)
        self.assertEqual((a['reg'], a['rw']), (0, True))
        self.assertEqual((b['reg'], b['rw']), (None, False))
        self.assertEqual((c['reg'], c['rw']), (None, True))

    def test_missing_metadata_keeps_previous_semantics(self):
        """A storage buffer the response does not describe stays unresolved and read-only."""
        got = self.sbufs(msl('device _15* fp_s2 [[id(0)]];'), res((1, 0, 324, WRITE)))[0]
        self.assertIsNone(got['reg'])
        self.assertIs(got['rw'], False)


if __name__ == '__main__':
    unittest.main()
