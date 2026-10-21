"""SPCH ('.wishp') prefix-chain regression: synthetic containers with closed-form expectations, no game files.

Each container is built byte by byte here, so every case states its own layout and the parser is checked
against that layout rather than against its own arithmetic. A program's entries are a prefix chain: entry i
starts where entries 0..i-1 ended, so entry i describes one new stage and the last entry's sizes are running
totals. Run: python3 dm/gfx/tests/test_spch.py
"""
import os
import struct
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools'))
import spch

CTL_SIZE = 2176
NVSD_SIZE = 0x80 + 0x14 * 4          # header + room for four nvsd_shaders entries


def _sph(bits, fill=0):
    """A graphics code area, 0x54 bytes, whose SPH word at +0x30 carries `bits` in 10..13."""
    code = bytearray(bytes.fromhex('78563412') + bytes(0x50))
    struct.pack_into('<I', code, 0x30, bits << 10)
    struct.pack_into('<I', code, 0x40, fill)     # a filler so equal-length stages still differ in content
    return bytes(code)


def _cs(fill=0):
    """A compute code area, 0x54 bytes."""
    code = bytearray(bytes.fromhex('79563412') + bytes(0x50))
    struct.pack_into('<I', code, 0x40, fill)
    return bytes(code)


def make_ctl(code_len, marker):
    """A control record shaped like the real ones: magic at +0, own length at +0x20, code length at +0x704,
    and a marker at +0x100 so two records that differ only in identity can be told apart."""
    c = bytearray(CTL_SIZE)
    c[0:4] = bytes.fromhex('34127698')
    struct.pack_into('<I', c, 0x20, CTL_SIZE)
    struct.pack_into('<I', c, 0x704, code_len)
    struct.pack_into('<I', c, 0x100, marker)
    return bytes(c)


def _slct_body(programs, xv4_start, unk_start):
    """One Slct's bytes, plus the code and control blobs its entries reference.

    The Slct's own offsets are relative to its start, so this body does not depend on where the Slct sits in
    slct_section. `xv4_start` / `unk_start` are the windows in section coordinates.
    """
    entries_by_prog, code_blob, ctl_blob, marker = [], b'', b'', 0
    code_prefix = ctl_prefix = 0
    for stages in programs:
        entries = []
        prog_code = prog_ctl = 0
        for st in stages:
            # a plain bytes entry gets its own record; a (code, marker) tuple reuses that marker's record, so
            # two programs can be built that genuinely share one control section
            if isinstance(st, tuple):
                code, use = st
            else:
                code, use = st, marker
                marker += 1
            ctl = make_ctl(len(code), use)
            entries.append((prog_code, len(code), prog_ctl, CTL_SIZE))
            code_blob += code
            ctl_blob += ctl
            prog_code += len(code)
            prog_ctl += CTL_SIZE
        entries_by_prog.append(entries)
        code_prefix += prog_code
        ctl_prefix += prog_ctl
    table_off = 0x48
    at = table_off + 8 * len(entries_by_prog)
    recs, bodies = b'', b''
    for entries in entries_by_prog:
        nv = bytearray(NVSD_SIZE)
        struct.pack_into('<II', nv, 0x18, 0x80, len(entries))
        for k, (vx, fx, vu, fu) in enumerate(entries):
            struct.pack_into('<5I', nv, 0x80 + 0x14 * k, 1, vx, fx, vu, fu)
        recs += struct.pack('<II', at, NVSD_SIZE)
        bodies += bytes(nv)
        at += NVSD_SIZE
    slct = bytearray(0x48)
    slct[0:4] = b'SLCT'
    struct.pack_into('<I', slct, 0x10, len(entries_by_prog))
    struct.pack_into('<I', slct, 0x14, table_off)
    struct.pack_into('<II', slct, 0x28, unk_start, ctl_prefix)
    struct.pack_into('<II', slct, 0x30, xv4_start, code_prefix)
    return bytes(slct) + recs + bodies, code_blob, ctl_blob


def build_slcts(specs, slct_pad=0):
    """A container of several Slcts: specs = [{'programs': [[codes…]], 'xv4': n, 'unk': n}].

    The code and control blobs are placed at each Slct's declared window start, so a Slct that sits at a
    non-zero offset in slct_section must have its NVSD resolved relative to its own start.
    """
    bodies, code_parts, ctl_parts = [], [], []
    xv4_cursor = unk_cursor = 0
    code_all, ctl_all = b'', b''
    for spec in specs:
        body, code, ctl = _slct_body(spec['programs'], spec['xv4'], spec['unk'])
        bodies.append(body)
        # place this Slct's code at its declared window start
        code_all += bytes(spec['xv4'] - xv4_cursor) + code
        xv4_cursor = spec['xv4'] + len(code)
        ctl_all += bytes(spec['unk'] - unk_cursor) + ctl
        unk_cursor = spec['unk'] + len(ctl)
    tab_off = 0x48
    slct_sec_off = tab_off + 8 * len(specs)
    table = b''.join(struct.pack('<II', sum(len(b) + slct_pad for b in bodies[:i]), 0)
                     for i in range(len(specs)))
    slct_sec = (bytes(slct_pad)).join(bodies)
    xv4_off = slct_sec_off + len(slct_sec)
    unk_off = xv4_off + len(code_all)
    hdr = bytearray(0x48)
    hdr[0:4] = b'HCPS'
    struct.pack_into('<I', hdr, 0x04, 1010)
    struct.pack_into('<II', hdr, 0x08, tab_off, len(specs))
    struct.pack_into('<II', hdr, 0x18, slct_sec_off, len(slct_sec))
    struct.pack_into('<II', hdr, 0x20, xv4_off, len(code_all))
    struct.pack_into('<II', hdr, 0x28, unk_off, len(ctl_all))
    return bytes(hdr) + table + slct_sec + code_all + ctl_all


def build(programs, xv4=0, unk=0):
    """A one-Slct container; `programs` is a list of programs, each a list of stage codes."""
    return build_slcts([{'programs': programs, 'xv4': xv4, 'unk': unk}])


class Prefix(unittest.TestCase):
    def test_two_entries_are_vertex_and_pixel(self):
        vs, ps = _sph(1, 1), _sph(5, 2)
        out = spch.shaders(build([[vs, ps]]), 'x')
        self.assertEqual([(s, c) for _, s, _, c in out], [('vs', vs), ('ps', ps)])
        self.assertEqual([k for _, _, k, _ in out], [make_ctl(len(vs), 0), make_ctl(len(ps), 1)])

    def test_three_entries_are_vertex_geometry_and_pixel(self):
        # The prefix model must read all three, not treat the last entry's totals as one vertex stage.
        vs, gs, ps = _sph(1, 1), _sph(4, 2), _sph(5, 3)
        out = spch.shaders(build([[vs, gs, ps]]), 'x')
        self.assertEqual([s for _, s, _, _ in out], ['vs', 'gs', 'ps'])
        self.assertEqual([c for _, _, _, c in out], [vs, gs, ps])
        self.assertEqual([struct.unpack_from('<I', k, 0x100)[0] for _, _, k, _ in out], [0, 1, 2])

    def test_single_entry_compute(self):
        cs = _cs(7)
        out = spch.shaders(build([[cs]]), 'x')
        self.assertEqual([(s, c) for _, s, _, c in out], [('cs', cs)])

    def test_second_program_reads_its_own_storage(self):
        # The regression for the base bug: a second program in the same Slct must start after the first
        # program's total, not at the Slct base. The two programs carry different stages with different
        # content, so reading program 0's bytes for program 1 cannot pass.
        p0 = [_sph(1, 0xA0), _sph(5, 0xB0)]
        p1 = [_sph(1, 0xC0), _sph(4, 0xD0), _sph(5, 0xE0)]
        out = spch.shaders(build([p0, p1], xv4=0x40, unk=0x20), 'x')
        self.assertEqual([s for _, s, _, _ in out], ['vs', 'ps', 'vs', 'gs', 'ps'])
        self.assertEqual([c for _, _, _, c in out], [p0[0], p0[1], p1[0], p1[1], p1[2]])
        labels = [w for w, _, _, _ in out]
        self.assertIn('#0:0:0:', labels[0])
        self.assertIn('#0:1:0:', labels[2])
        # program 1 sits after program 0's total (0x54+0x54 = 0xA8) plus the declared start
        self.assertIn(f'@xv4+{0x40 + 0xa8:#x}', labels[2])
        self.assertIn(f'/unk+{0x20 + 2 * CTL_SIZE:#x}', labels[2])
        self.assertEqual([struct.unpack_from('<I', k, 0x100)[0] for _, _, k, _ in out], [0, 1, 2, 3, 4])

    def test_same_code_content_still_gets_its_own_record(self):
        # Identical code in two entries: the records must still be the ones written for each position.
        a = _sph(1, 0x11)
        out = spch.shaders(build([[a, a]]), 'x')
        self.assertEqual([struct.unpack_from('<I', k, 0x100)[0] for _, _, k, _ in out], [0, 1])
        self.assertEqual([c for _, _, _, c in out], [a, a])

    def test_two_slcts_resolve_their_own_nvsd(self):
        # Two real Slcts, the second at a non-zero offset in slct_section with its own gapped windows. Its
        # program record and NVSD are relative to its own start, so a parser using the section base reads the
        # wrong bytes; each Slct's stages carry distinct content so that cannot pass.
        a0, a1 = _sph(1, 0x11), _sph(5, 0x22)
        b0, b1 = _sph(1, 0x33), _sph(5, 0x44)
        d = build_slcts([{'programs': [[a0, a1]], 'xv4': 0x40, 'unk': 0x20},
                         {'programs': [[b0, b1]], 'xv4': 0x300, 'unk': 0x1200}], slct_pad=0x40)
        slct_sec = struct.unpack_from('<I', d, 0x18)[0]
        table = struct.unpack_from('<I', d, 0x08)[0]
        rel0 = struct.unpack_from('<I', d, table)[0]
        rel1 = struct.unpack_from('<I', d, table + 8)[0]
        self.assertEqual(rel0, 0)
        self.assertGreater(rel1, 0, 'the second Slct must not sit at the start of slct_section')
        out = spch.shaders(d, 'x')
        self.assertEqual([(s, c) for _, s, _, c in out], [('vs', a0), ('ps', a1), ('vs', b0), ('ps', b1)])
        labels = [w for w, _, _, _ in out]
        self.assertIn('#SPCH#1:0:0:', labels[2])
        # the second Slct's windows, in section coordinates
        slct1 = slct_sec + rel1
        self.assertEqual(struct.unpack_from('<I', d, slct1 + 0x30)[0], 0x300)
        self.assertEqual(struct.unpack_from('<I', d, slct1 + 0x28)[0], 0x1200)
        self.assertIn('@xv4+0x300', labels[2])
        self.assertIn('/unk+0x1200', labels[2])

    def test_window_must_close(self):
        d = bytearray(build([[_sph(1)]], xv4=0, unk=0))
        # grow the Slct's declared xv4 window: the program can no longer land on its end
        slct_at = struct.unpack_from('<I', d, 0x18)[0]
        struct.pack_into('<I', d, slct_at + 0x30, 0)
        struct.pack_into('<I', d, slct_at + 0x34, 0x1000)
        with self.assertRaises(ValueError):
            spch.shaders(bytes(d), 'x')

    def test_broken_prefix_is_refused(self):
        # Move the second entry's vx off the end of the first entry: not the prefix layout.
        d = bytearray(build([[_sph(1), _sph(5)]]))
        pair = d.index(struct.pack('<II', 0x80, 2))
        # entries start at pair+0x68; entry 1's vx is at +0x14 within the entry, +0x04 within the entry
        struct.pack_into('<I', d, pair + 0x68 + 0x14 + 0x04, 0x54 + 4)
        with self.assertRaises(spch.Unsupported) as cm:
            spch.shaders(bytes(d), 'x')
        self.assertIn('prefix', str(cm.exception))

    def test_control_length_mismatch_is_refused(self):
        # The control record must state the same code length as the entry's span.
        d = bytearray(build([[_sph(1), _sph(5)]]))
        unk_off = struct.unpack_from('<I', d, 0x28)[0]
        struct.pack_into('<I', d, unk_off + CTL_SIZE + 0x704, 4)
        with self.assertRaises(spch.Unsupported):
            spch.shaders(bytes(d), 'x')

    def test_half_a_stage_is_refused(self):
        d = bytearray(build([[_sph(1)]]))
        pair = d.index(struct.pack('<II', 0x80, 1))
        struct.pack_into('<I', d, pair + 0x68 + 0x10, 0)   # zero the control span, keep the code
        with self.assertRaises(spch.Unsupported):
            spch.shaders(bytes(d), 'x')

    def test_unknown_version_is_refused(self):
        d = bytearray(build([[_sph(1)]]))
        struct.pack_into('<I', d, 0x04, 0xdeadbeef)
        with self.assertRaises(spch.Unsupported) as cm:
            spch.shaders(bytes(d), 'x')
        self.assertIn('version', str(cm.exception))

    def test_payload_past_slct_section_is_refused(self):
        d = bytearray(build([[_sph(1)]]))
        slct_sec = struct.unpack_from('<I', d, 0x18)[0]
        slct_len = struct.unpack_from('<I', d, 0x1c)[0]
        struct.pack_into('<I', d, slct_sec + 0x48, slct_len + 0x40)
        self.assertLess(slct_sec + slct_len + 0x40, len(d))
        with self.assertRaises(ValueError):
            spch.shaders(bytes(d), 'x')

    def test_truncated_and_foreign_input_are_refused(self):
        d = build([[_sph(1)]])
        with self.assertRaises(ValueError):
            spch.shaders(d[:0x40], 'x')
        with self.assertRaises(Unsupported := spch.Unsupported):
            spch.shaders(b'BNSH' + bytes(0x60), 'x')


def shader_split():
    """The real module, with a stub game profile: the profile supplies source-group rules that the pairing
    does not read, and stubbing it keeps this file independent of any game's profile."""
    tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools')
    if tools not in sys.path: sys.path.insert(0, tools)
    if 'game' not in sys.modules:
        stub = types.ModuleType('game')
        class Profile:
            @staticmethod
            def pairs(_key): return {}
            @staticmethod
            def get(_key, default=None): return default
            @staticmethod
            def table(_name): return {}
        stub.load = lambda: Profile()
        sys.modules['game'] = stub
    import shader_split
    return shader_split


class Pairing(unittest.TestCase):
    def setUp(self):
        self.ss = shader_split()

    def pairs_of(self, d):
        found = []
        self.ss.scan_blob(d, 'rom', found)
        return found, self.ss.pairs_of(found)

    def test_plain_program_pairs_its_two_keys(self):
        vs, ps = _sph(1, 0x11), _sph(5, 0x22)
        found, pairs = self.pairs_of(build([[vs, ps]]))
        k = self.ss.skey
        self.assertEqual(pairs, {(k(make_ctl(len(vs), 0), vs), k(make_ctl(len(ps), 1), ps))})
        self.assertEqual(len(found), 2, 'the integration path must see both stages')

    def test_two_programs_do_not_cross_pair(self):
        a, b = _sph(1, 0x11), _sph(5, 0x22)
        c, e = _sph(1, 0x33), _sph(5, 0x44)
        _, pairs = self.pairs_of(build([[a, b], [c, e]]))
        k = self.ss.skey
        want = {(k(make_ctl(len(a), 0), a), k(make_ctl(len(b), 1), b)),
                (k(make_ctl(len(c), 2), c), k(make_ctl(len(e), 3), e))}
        self.assertEqual(pairs, want)
        for x in want:
            self.assertNotIn((x[0], want.pop() if False else x[1]), set())

    def test_shared_vertex_different_pixel_keeps_both_pairs(self):
        vs = _sph(1, 0x77)
        p1, p2 = _sph(5, 0x88), _sph(5, 0x99)
        # the same vertex record in both programs: the vertex key is identical, the pixel keys differ
        _, pairs = self.pairs_of(build([[(vs, 0), (p1, 5)], [(vs, 0), (p2, 6)]]))
        k = self.ss.skey
        kv = k(make_ctl(len(vs), 0), vs)
        self.assertEqual(len(pairs), 2)
        self.assertEqual({a for a, _ in pairs}, {kv})
        self.assertEqual({b for _, b in pairs}, {k(make_ctl(len(p1), 5), p1), k(make_ctl(len(p2), 6), p2)})

    def test_geometry_chain_makes_no_direct_pair(self):
        vs, gs, ps = _sph(1, 0x11), _sph(4, 0x22), _sph(5, 0x33)
        found, pairs = self.pairs_of(build([[vs, gs, ps]]))
        self.assertEqual(pairs, set(), 'a chain through geometry is not a direct vs/ps pipeline')
        prog = [(w, st) for w, st, _, _ in found]
        self.assertEqual([st for _, st in prog], ['vs', 'gs', 'ps'])
        self.assertEqual(len(prog), 3, 'every stage of the chain is still reported')

    def test_single_stage_programs_do_not_pair(self):
        _, pairs = self.pairs_of(build([[_sph(1)], [_cs(0x55)]]))
        self.assertEqual(pairs, set())

    def test_repeated_stage_is_refused(self):
        found = []
        self.ss.scan_blob(build([[_sph(1, 1), _sph(1, 2)]]), 'rom', found)
        with self.assertRaises(SystemExit):
            self.ss.spch_pairs(found)

    def test_foreign_labels_are_not_programs(self):
        found = [('a#SPCH#not-a-identity', 'vs', make_ctl(4, 0), _sph(1)),
                 ('plain#BNSH@0x10', 'vs', make_ctl(4, 0), _sph(1))]
        self.assertEqual(self.ss.spch_pairs(found), set())

    def test_a_name_containing_the_marker_still_resolves(self):
        # rpartition takes the last marker, so a source name that contains one is not mis-split.
        found = [('a#SPCH#b#SPCH#0:0:0:vs@xv4+0x0/unk+0x0', 'vs', make_ctl(len(_sph(1)), 0), _sph(1)),
                 ('a#SPCH#b#SPCH#0:0:1:ps@xv4+0x54/unk+0x880', 'ps', make_ctl(len(_sph(5)), 1), _sph(5))]
        self.assertEqual(len(self.ss.spch_pairs(found)), 1)

    def _scan_file(self, progs):
        """Write the container as a real file and run the production entry, not scan_blob directly."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'probe.wishp')
            with open(path, 'wb') as f: f.write(build(progs))
            return self.ss.scan_file((path, 'rom/probe.wishp'))

    def test_scan_file_reaches_the_spch_parser(self):
        # The pre-filter in scan_file decides whether a file is scanned at all; an SPCH container must pass it.
        vs, ps = _sph(1, 0x11), _sph(5, 0x22)
        rel, keys, pairs, trees = self._scan_file([[vs, ps]])
        k = self.ss.skey
        self.assertEqual(len(keys), 2, 'the production entry must extract both stages')
        self.assertEqual({v[1] for v in keys.values()}, {'vs', 'ps'})
        self.assertEqual(pairs, {(k(make_ctl(len(vs), 0), vs), k(make_ctl(len(ps), 1), ps))})
        # the key carries the same bytes the parser produced
        by_stage = {v[1]: v for v in keys.values()}
        self.assertEqual(by_stage['vs'][3], vs)
        self.assertEqual(by_stage['ps'][3], ps)

    def test_scan_file_keeps_a_geometry_chain_but_pairs_nothing(self):
        vs, gs, ps = _sph(1, 0x11), _sph(4, 0x22), _sph(5, 0x33)
        rel, keys, pairs, trees = self._scan_file([[vs, gs, ps]])
        self.assertEqual({v[1] for v in keys.values()}, {'vs', 'gs', 'ps'}, 'every stage keeps its key')
        self.assertEqual(pairs, set())
        self.assertEqual({v[3] for v in keys.values()}, {vs, gs, ps})

    def test_scan_file_still_skips_files_it_never_scanned(self):
        # The pre-filter must keep skipping ordinary files: only the container magics it knows send a file on.
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'plain.bin')
            with open(path, 'wb') as f: f.write(bytes(0x200))
            rel, keys, pairs, trees = self.ss.scan_file((path, 'rom/plain.bin'))
            self.assertEqual((rel, keys, pairs, trees), ('rom/plain.bin', {}, set(), {}))

    def test_scan_file_refuses_a_broken_container(self):
        # A container the parser refuses must stop the run, not come back as an empty success.
        d = bytearray(build([[_sph(1)]]))
        struct.pack_into('<I', d, 0x04, 0xdeadbeef)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'probe.wishp')
            with open(path, 'wb') as f: f.write(bytes(d))
            with self.assertRaises(SystemExit):
                self.ss.scan_file((path, 'rom/probe.wishp'))

    def test_bnsh_variations_are_unchanged(self):
        # the pre-existing path still pairs by '#var' labels and does not read SPCH ones
        found = [('x#BNSH@0x10#var0', 'vs', make_ctl(4, 0), _sph(1)),
                 ('x#BNSH@0x10#var0', 'ps', make_ctl(4, 1), _sph(5)),
                 ('y#SPCH#0:0:0:vs@xv4+0x0/unk+0x0', 'vs', make_ctl(4, 2), _sph(1)),
                 ('y#SPCH#0:0:1:ps@xv4+0x54/unk+0x880', 'ps', make_ctl(4, 3), _sph(5))]
        k = self.ss.skey
        self.assertEqual(self.ss.var_pairs(found),
                         {(k(make_ctl(4, 0), _sph(1)), k(make_ctl(4, 1), _sph(5)))})
        self.assertEqual(self.ss.spch_pairs(found),
                         {(k(make_ctl(4, 2), _sph(1)), k(make_ctl(4, 3), _sph(5)))})
        self.assertEqual(len(self.ss.pairs_of(found)), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
