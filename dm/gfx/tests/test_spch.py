"""SPCH ('.wishp') prefix-chain regression: synthetic containers with closed-form expectations, no game files.

Each container is built byte by byte here, so every case states its own layout and the parser is checked
against that layout rather than against its own arithmetic. A program's entries are a prefix chain: entry i
starts where entries 0..i-1 ended, so entry i describes one new stage and the last entry's sizes are running
totals. Run: python3 dm/gfx/tests/test_spch.py
"""
import os
import struct
import sys
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


def build(stages_per_program, xv4_start=0, unk_start=0, nslct=1, slct_gap=0):
    """A container whose single Slct holds `stages_per_program` programs.

    `stages_per_program` is a list of programs; each program is a list of stage codes in order. The sizes of
    every entry are derived from the codes the caller passed, so the prefix is consistent by construction and
    the expectations in the tests are the literal values the builder wrote.
    """
    code_blob, ctl_blob, progs = b'', b'', []
    code_cursor = xv4_start
    ctl_cursor = unk_start
    code_blob += bytes(xv4_start)
    ctl_blob += bytes(unk_start)
    marker = 0
    for stages in stages_per_program:
        entries, code_prefix, ctl_prefix = [], 0, 0
        for code in stages:
            ctl = make_ctl(len(code), marker)
            marker += 1
            entries.append((code_prefix, len(code), ctl_prefix, CTL_SIZE, code, ctl))
            code_blob += code
            ctl_blob += ctl
            code_prefix += len(code)
            ctl_prefix += CTL_SIZE
        progs.append(entries)
        code_cursor += code_prefix
        ctl_cursor += ctl_prefix
    slct_len = sum(len(s) for s in stages_per_program)
    # Slct: header 0x48, program table 8 bytes per program, then the NVSD bodies
    table_off = 0x48
    body_off = table_off + 8 * len(progs)
    bodies, recs, at = b'', b'', body_off
    for entries in progs:
        nv = bytearray(NVSD_SIZE)
        struct.pack_into('<II', nv, 0x18, 0x80, len(entries))
        for k, (vx, fx, vu, fu, _c, _k) in enumerate(entries):
            struct.pack_into('<5I', nv, 0x80 + 0x14 * k, 1, vx, fx, vu, fu)
        recs += struct.pack('<II', at, NVSD_SIZE)
        bodies += bytes(nv)
        at += NVSD_SIZE
    slct = bytearray(0x48)
    slct[0:4] = b'SLCT'
    struct.pack_into('<I', slct, 0x10, len(progs))
    struct.pack_into('<I', slct, 0x14, table_off)
    struct.pack_into('<II', slct, 0x28, unk_start, ctl_cursor - unk_start)
    struct.pack_into('<II', slct, 0x30, xv4_start, code_cursor - xv4_start)
    slct = bytes(slct) + recs + bodies
    # No statement about slct total size is needed by the parser beyond the walk; the windows are from the
    # builder's own cursors, so a walk that lands anywhere else fails.
    tab_off = 0x48
    slct_sec_off = tab_off + 8 * nslct
    xv4_off = slct_sec_off + len(slct) + slct_gap
    unk_off = xv4_off + len(code_blob)
    hdr = bytearray(0x48)
    hdr[0:4] = b'HCPS'
    struct.pack_into('<I', hdr, 0x04, 1010)
    struct.pack_into('<II', hdr, 0x08, tab_off, nslct)
    struct.pack_into('<II', hdr, 0x18, slct_sec_off, len(slct))
    struct.pack_into('<II', hdr, 0x20, xv4_off, len(code_blob))
    struct.pack_into('<II', hdr, 0x28, unk_off, len(ctl_blob))
    return bytes(hdr) + struct.pack('<II', 0, 0) + slct + bytes(slct_gap) + code_blob + ctl_blob


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
        out = spch.shaders(build([p0, p1], xv4_start=0x40, unk_start=0x20), 'x')
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

    def test_window_must_close(self):
        d = bytearray(build([[_sph(1)]], xv4_start=0, unk_start=0))
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
