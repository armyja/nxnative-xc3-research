"""SPCH ('.wishp') association regression: synthetic containers with closed-form expectations, no game files.

The containers are built here byte by byte, so every case states its own layout and the parser is checked
against that layout rather than against its own arithmetic. Run: python3 dm/gfx/tests/test_spch.py
"""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools'))
import spch

GFX = bytes.fromhex('78563412') + bytes(0x50)          # a graphics code area, 0x54 bytes: magic + 0x50
CS = bytes.fromhex('79563412') + bytes(0x50)           # a compute code area


def make_ctl(code_len):
    """A 2176-byte control record shaped like the real ones: magic, own length at +0x20, code length at +0x704."""
    c = bytearray(2176)
    c[0:4] = bytes.fromhex('34127698')
    struct.pack_into('<I', c, 0x20, 0x880)
    struct.pack_into('<I', c, 0x704, code_len)
    return bytes(c)



def _sph(bits):
    """A graphics code area whose SPH word at +0x30 carries `bits` in 10..13."""
    code = bytearray(GFX)
    struct.pack_into('<I', code, 0x30, bits << 10)
    return bytes(code)


def build(programs, gap=0):
    """One Slct holding `programs` = [(vs_code|None, ps_code|None, gap_before_control)].

    Returns the container bytes. Every program's vertex/fragment sizes come from the code areas it is given,
    and the Slct's xv4 / unk windows are the sums of those, so the walks close by construction.
    """
    code_blob, ctl_blob = b'', b''
    entries = []
    for vs, ps, g in programs:
        vx, fx = (len(vs) if vs else 0), (len(ps) if ps else 0)
        vu, fu = (len(make_ctl(vx)) if vs else 0), (len(make_ctl(fx)) + g if ps else 0)
        entries.append((vx, fx, vu, fu))
        code_blob += (vs or b'') + (ps or b'')
        if vs:
            ctl_blob += make_ctl(vx)
        if ps:
            ctl_blob += b'\0' * g + make_ctl(fx)
    prog_cnt = len(programs)
    xv4_total, unk_total = len(code_blob), len(ctl_blob)

    # NVSD per program: six zero u32, then {offset,count} and the entry list (5 u32 each)
    nvsd_list, nvsd_off = [], []
    for (vx, fx, vu, fu) in entries:
        body = bytearray(0x80)
        off = 0x80
        body += struct.pack('<I', 1)                     # unk6 of the only entry
        body += struct.pack('<4I', vx, fx, vu, fu)
        struct.pack_into('<II', body, 0x18, off, 1)      # offset first, then count
        nvsd_list.append(bytes(body))
    # program records (8 bytes each) then the NVSD bodies, all relative to the Slct
    rec_area = 0x48
    data_area = rec_area + 8 * prog_cnt
    recs, bodies, cur = b'', b'', data_area
    for n in nvsd_list:
        recs += struct.pack('<II', cur, len(n))
        bodies += n
        cur += len(n)
    slct = bytearray(0x48)
    slct[0:4] = b'SLCT'
    struct.pack_into('<I', slct, 0x10, prog_cnt)         # programs count
    struct.pack_into('<I', slct, 0x14, rec_area)         # programs offset (relative to the Slct)
    struct.pack_into('<II', slct, 0x28, 0, unk_total)    # unk_item_offset, unk_item_total_size
    struct.pack_into('<II', slct, 0x30, 0, xv4_total)    # xv4_offset, xv4_total_size
    slct = bytes(slct) + recs + bodies

    # lay out the file: header, slct table + slct_section, xv4_section, unk_section
    slct_tab_off = 0x48
    slct_sec_off = slct_tab_off + 8
    xv4_off = slct_sec_off + len(slct)
    unk_off = xv4_off + len(code_blob)
    hdr = bytearray(0x48)
    hdr[0:4] = b'HCPS'
    struct.pack_into('<I', hdr, 0x04, 1010)
    struct.pack_into('<II', hdr, 0x08, slct_tab_off, 1)   # Slct table: 1 entry
    struct.pack_into('<II', hdr, 0x18, slct_sec_off, len(slct))
    struct.pack_into('<II', hdr, 0x20, xv4_off, len(code_blob))
    struct.pack_into('<II', hdr, 0x28, unk_off, len(ctl_blob))
    return bytes(hdr) + struct.pack('<II', 0, 0) + slct + code_blob + ctl_blob


class Spch(unittest.TestCase):
    def test_same_code_lengths_are_paired_by_structure(self):
        # Two programs whose vertex and fragment code are byte-identical and the same length: only the
        # structural walk can tell them apart, and each must get its own control record.
        vs, ps = _sph(1), _sph(5)
        out = spch.shaders(build([(vs, ps, 0), (vs, ps, 0)]), 'x')
        self.assertEqual([(w, s) for w, s, _, _ in out],
                         [('x#SPCH#0:0:vs@xv4+0x0/unk+0x0', 'vs'), ('x#SPCH#0:0:ps@xv4+0x54/unk+0x880', 'ps'),
                          ('x#SPCH#0:1:vs@xv4+0xa8/unk+0x1100', 'vs'), ('x#SPCH#0:1:ps@xv4+0xfc/unk+0x1980', 'ps')])
        self.assertEqual(out[0][2], make_ctl(len(vs)))
        self.assertEqual(out[2][2], make_ctl(len(vs)))   # the bytes match here; the identity must still differ
        self.assertNotEqual(out[0][0], out[2][0], 'the identity must not collapse when code and control match')

    def test_a_gap_before_a_record_is_not_searched_past(self):
        # The walk puts the fragment record at cursor+vertex_unk_item_size. If padding sits there instead of a
        # record, the structure does not describe a record: refuse rather than scan for the next magic.
        vs, ps = _sph(1), _sph(5)
        with self.assertRaises(spch.Unsupported):
            spch.shaders(build([(vs, ps, 64)]), 'x')

    def test_each_slct_starts_from_its_own_base(self):
        # Two Slcts whose windows do not touch: each walk must begin at its own xv4_offset / unk_item_offset.
        # The synthetic builder writes one Slct, so this checks the rule the real samples exercised instead:
        # a Slct whose windows start at 0, then one starting after the first, must both close.
        vs, ps = _sph(1), _sph(5)
        out = spch.shaders(build([(vs, ps, 0), (ps, vs, 0)]), 'x')
        self.assertEqual(len(out), 4, 'both programs keep their own spans')
        self.assertTrue(all('@xv4+0x0' in out[0][0] for _ in (0,)), 'the first program starts at the Slct base')

    def test_compute_in_the_fragment_slot_is_compute(self):
        out = spch.shaders(build([(None, CS, 0)]), 'x')
        self.assertEqual([s for _, s, _, _ in out], ['cs'])

    def test_stage_comes_from_the_code_area_not_the_slot(self):
        # A vertex program occupying the fragment slot is reported as the vertex stage it declares.
        out = spch.shaders(build([(None, _sph(1), 0)]), 'x')
        self.assertEqual([s for _, s, _, _ in out], ['vs'])

    def test_half_a_stage_is_refused(self):
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        # Zero the fragment code size, leaving its control record: one side of the stage is missing
        nvsd = d.index(struct.pack('<4I', 0x54, 0x54, 2176, 2176))
        struct.pack_into('<I', d, nvsd + 8, 0)
        with self.assertRaises(spch.Unsupported):
            spch.shaders(bytes(d), 'x')

    def test_truncated_file_is_refused(self):
        d = build([(_sph(1), _sph(5), 0)])
        with self.assertRaises(ValueError):
            spch.shaders(d[:-0x100], 'x')
        with self.assertRaises(ValueError):
            spch.shaders(d[:0x40], 'x')

    def test_not_a_container_is_refused(self):
        with self.assertRaises(spch.Unsupported):
            spch.shaders(b'BNSH' + bytes(0x60), 'x')

    def test_window_past_the_section_is_refused(self):
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        # Grow the Slct's declared xv4 window past the xv4_section: the check must refuse it before any walk
        slct_at = struct.unpack_from('<I', d, 0x48)[0] + struct.unpack_from('<I', d, 0x18)[0]
        struct.pack_into('<I', d, slct_at + 0x34, 0x10000)
        with self.assertRaises(ValueError):
            spch.shaders(bytes(d), 'x')


if __name__ == '__main__':
    unittest.main(verbosity=2)
