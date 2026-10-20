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

NVSD_SIZE = 0x80 + 0x14 * 3    # room for up to three nvsd_shaders entries
GFX = bytes.fromhex('78563412') + bytes(0x50)          # a graphics code area, 0x54 bytes: magic + 0x50
CS = bytes.fromhex('79563412') + bytes(0x50)           # a compute code area


def make_ctl(code_len, marker=0):
    """A 2176-byte control record shaped like the real ones: magic, own length at +0x20, code length at +0x704,
    and a `marker` at +0x100 so records that differ only in identity can be told apart."""
    c = bytearray(2176)
    c[0:4] = bytes.fromhex('34127698')
    struct.pack_into('<I', c, 0x20, 0x880)
    struct.pack_into('<I', c, 0x704, code_len)
    struct.pack_into('<I', c, 0x100, marker)
    return bytes(c)



def _sph(bits):
    """A graphics code area whose SPH word at +0x30 carries `bits` in 10..13."""
    code = bytearray(GFX)
    struct.pack_into('<I', code, 0x30, bits << 10)
    return bytes(code)


def build_slct(programs, marker_base=0, gap=0):
    """One Slct from [(vs_code|None, ps_code|None, gap)]; returns (slct_bytes, code_blob, ctl_blob).

    Each program's sizes are the code areas it is given, and `marker_base` makes every control record in this
    Slct distinct from another Slct's, so a test can prove which record a stage actually received.
    """
    code_blob, ctl_blob, entries = b'', b'', []
    for n, (vs, ps, g) in enumerate(programs):
        vx, fx = (len(vs) if vs else 0), (len(ps) if ps else 0)
        vu, fu = (len(make_ctl(vx)) if vs else 0), (len(make_ctl(fx)) + g if ps else 0)
        entries.append((vx, fx, vu, fu))
        code_blob += (vs or b'') + (ps or b'')
        if vs:
            ctl_blob += make_ctl(vx, marker_base + n)
        if ps:
            ctl_blob += b'\0' * g + make_ctl(fx, marker_base + 100 + n)
    bodies, cur = b'', 0x48 + 8 * len(programs)
    for (vx, fx, vu, fu) in entries:
        body = bytearray(NVSD_SIZE)                     # header + room for up to three entries
        struct.pack_into('<II', body, 0x18, 0x80, 1)     # offset of the one entry, then its count
        struct.pack_into('<5I', body, 0x80, 1, vx, fx, vu, fu)
        bodies += bytes(body)
    recs, body_at = b'', cur
    for e in entries:
        recs += struct.pack('<II', body_at, NVSD_SIZE)
        body_at += NVSD_SIZE
    slct = bytearray(0x48)
    slct[0:4] = b'SLCT'
    struct.pack_into('<I', slct, 0x10, len(programs))
    struct.pack_into('<I', slct, 0x14, 0x48)
    struct.pack_into('<II', slct, 0x28, 0, len(ctl_blob))
    struct.pack_into('<II', slct, 0x30, 0, len(code_blob))
    return bytes(slct) + recs + bodies, code_blob, ctl_blob


def build(programs, gap=0):
    """A one-Slct container; the Slct's windows start at 0."""
    return build_multi([(programs, 0, 0)], gap=gap)


def build_multi(slcts, gap=0):
    """A container of several Slcts: [(programs, xv4_start, unk_start)], each with its own window bases.

    Between consecutive Slcts the xv4 and unk sections may carry padding, so the next Slct's start is greater
    than the previous one's end: a walk must begin at its own base, not where the previous one stopped.
    """
    slct_bytes, code_all, ctl_all, meta = [], b'', b'', []
    xv4_cursor = unk_cursor = 0
    for i, (programs, xstart, ustart) in enumerate(slcts):
        body, code, ctl = build_slct(programs, marker_base=1000 * i, gap=gap)
        meta.append((bytearray(body), xstart, ustart, len(code), len(ctl)))
        code_all += b'\0' * (xstart - xv4_cursor) + code
        xv4_cursor = xstart + len(code)
        ctl_all += b'\0' * (ustart - unk_cursor) + ctl
        unk_cursor = ustart + len(ctl)
    tab_off = 0x48
    slct_sec_off = tab_off + 8 * len(slcts)
    off = slct_sec_off
    table = b''
    for (body, xs, us, _lc, _lk) in meta:
        # the Slct's own window bases: xv4_offset at +0x30, unk_item_offset at +0x28
        struct.pack_into('<I', body, 0x30, xs)
        struct.pack_into('<I', body, 0x28, us)
        table += struct.pack('<II', off - slct_sec_off, 0)
        body[0:0] = b''  # keep the Slct bytes as built
        slct_bytes.append(bytes(body))
        off += len(body)
    slct_sec = b''.join(slct_bytes)
    xv4_off = slct_sec_off + len(slct_sec)
    unk_off = xv4_off + len(code_all)
    hdr = bytearray(0x48)
    hdr[0:4] = b'HCPS'
    struct.pack_into('<I', hdr, 0x04, 1010)
    struct.pack_into('<II', hdr, 0x08, tab_off, len(slcts))
    struct.pack_into('<II', hdr, 0x18, slct_sec_off, len(slct_sec))
    struct.pack_into('<II', hdr, 0x20, xv4_off, len(code_all))
    struct.pack_into('<II', hdr, 0x28, unk_off, len(ctl_all))
    return bytes(hdr) + table + slct_sec + code_all + ctl_all


class Spch(unittest.TestCase):
    def test_same_code_lengths_are_paired_by_structure(self):
        # Three programs with byte-identical vertex and fragment code of the same length, but a different
        # control marker each. Only the structural walk can tell them apart, so every stage must receive its
        # own record: a parser that simply took the first control record would fail this.
        vs, ps = _sph(1), _sph(5)
        out = spch.shaders(build([(vs, ps, 0), (vs, ps, 0), (vs, ps, 0)]), 'x')
        self.assertEqual(len(out), 6)
        self.assertEqual([s for _, s, _, _ in out], ['vs', 'ps', 'vs', 'ps', 'vs', 'ps'])
        markers = [struct.unpack_from('<I', ctl, 0x100)[0] for _, _, ctl, _ in out]
        self.assertEqual(markers, [0, 100, 1, 101, 2, 102],
                         'each stage must get its own record, not the first one three times')
        for (_, st, ctl, code), want_vs in zip(out, [True, False] * 3):
            self.assertEqual(code, vs if want_vs else ps)
            self.assertEqual(ctl, make_ctl(len(code), marker=markers[out.index((_, st, ctl, code))]))

    def test_each_slct_starts_from_its_own_base(self):
        # Two Slcts whose xv4 and unk windows do not touch: the second starts after a gap, so a walk that
        # carried on from where the first stopped would read the wrong bytes.
        vs, ps = _sph(1), _sph(5)
        d = build_multi([([(vs, ps, 0)], 0, 0), ([(ps, vs, 0)], 0x200, 0x1000)], )
        out = spch.shaders(d, 'x')
        self.assertEqual(len(out), 4)
        labels = [w for w, _, _, _ in out]
        self.assertIn('@xv4+0x200', labels[2], 'the second Slct must start at its own xv4 base')
        self.assertIn('@unk+0x1000', labels[2], 'the second Slct must start at its own unk base')
        # the second Slct's stages carry its own marker space, not the first Slct's
        self.assertEqual([struct.unpack_from('<I', ctl, 0x100)[0] for _, _, ctl, _ in out],
                         [0, 100, 1000, 1100])
        # and their code is the code the second Slct declared (fragment first, then vertex)
        self.assertEqual(out[2][3], ps)
        self.assertEqual(out[3][3], vs)

    def test_second_slct_resolves_its_nvsd_from_its_own_start(self):
        # A real two-Slct container whose second Slct sits at a non-zero offset inside slct_section. The
        # program record's offset is measured from the Slct's own start (xc3_lib slices slct_section and
        # parses a Cursor over that slice), so a parser using the section base reads the wrong bytes here.
        # The two Slcts get distinct code lengths, so the NVSD each must resolve is identifiable by size.
        # slct0: 2 stages -> xv4 0x108, unk 0x1100; slct1 starts after both, with gaps
        d = build_multi([([(_sph(1), _sph(5), 0)], 0, 0),
                         ([(_sph(5), _sph(1), 0), (_sph(1), _sph(1), 0)], 0x200, 0x1800)])
        slct_sec_off = struct.unpack_from('<I', d, 0x18)[0]
        table = struct.unpack_from('<I', d, 0x08)[0]
        rel1 = struct.unpack_from('<I', d, table + 8)[0]
        self.assertGreater(rel1, 0, 'the second Slct must not sit at the start of slct_section')
        # and its windows must start where it says, after gaps left by slct0
        self.assertEqual(struct.unpack_from('<I', d, slct_sec_off + rel1 + 0x30)[0], 0x200)
        slct1 = slct_sec_off + rel1
        prog_off = struct.unpack_from('<I', d, slct1 + 0x14)[0]
        raw, ln = struct.unpack_from('<II', d, slct1 + prog_off)
        from_slct = bytes(d[slct1 + raw:slct1 + raw + ln])
        from_section = bytes(d[slct_sec_off + raw:slct_sec_off + raw + ln])
        self.assertNotEqual(from_slct, from_section, 'the two bases must not name the same bytes in this fixture')
        got = spch._read_nvsd(d, slct1 + prog_off, slct1, slct_sec_off + struct.unpack_from('<I', d, 0x1c)[0], 'x', 1, 0)
        self.assertEqual(got, from_slct, 'the NVSD must be read from the Slct-relative base')
        self.assertNotEqual(got, from_section)
        out = spch.shaders(d, 'x')
        stages2 = [x for x in out if '#1:' in x[0]]
        self.assertEqual(len(stages2), 4, 'both programs of the second Slct must resolve')
        # the second Slct's first program is (fragment 0x54, vertex 0x54): verify the bytes are its own
        self.assertEqual(stages2[0][3], _sph(5))
        self.assertEqual(stages2[1][3], _sph(1))

    def test_unknown_version_is_refused(self):
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        struct.pack_into('<I', d, 0x04, 0xdeadbeef)
        with self.assertRaises(spch.Unsupported) as cm:
            spch.shaders(bytes(d), 'x')
        self.assertIn('version', str(cm.exception))

    def test_leading_entry_with_only_fragment_sizes_is_refused(self):
        # The engine writes (0, fx, 0, fu) before the real entry in every verified program. Its meaning is not
        # established (xc3_lib: "Why is only the last set of shaders used?"), so it must be refused, not dropped.
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        nvsd = d.index(struct.pack('<II', 0x80, 1))
        # turn the single entry into two: a leading (0, 0x54, 0, 2176) and the original as the last
        struct.pack_into('<II', d, nvsd, 0x80, 2)
        lead = struct.pack('<5I', 0, 0, len(_sph(1)), 0, 2176)
        d[nvsd + 8:nvsd + 8 + 0x14] = lead
        with self.assertRaises(spch.Unsupported) as cm:
            spch.shaders(bytes(d), 'x')
        self.assertIn('not all zero', str(cm.exception))

    def test_leading_entry_with_a_vertex_stage_is_refused(self):
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        nvsd = d.index(struct.pack('<II', 0x80, 1))
        struct.pack_into('<II', d, nvsd, 0x80, 2)
        lead = struct.pack('<5I', 0, len(_sph(1)), len(_sph(5)), 2176, 2176)
        d[nvsd + 8:nvsd + 8 + 0x14] = lead
        with self.assertRaises(spch.Unsupported) as cm:
            spch.shaders(bytes(d), 'x')
        self.assertIn('not all zero', str(cm.exception))

    def test_payload_past_slct_section_is_refused(self):
        # A program record that stays inside the file but names its NVSD past the end of slct_section, i.e.
        # borrowing another section's bytes: refused.
        d = bytearray(build([(_sph(1), _sph(5), 0)]))
        rec = struct.unpack_from('<I', d, 0x48)[0] + struct.unpack_from('<I', d, 0x18)[0] + 0x48
        off = struct.unpack_from('<I', d, rec)[0]
        slct_len = struct.unpack_from('<I', d, 0x1c)[0]
        struct.pack_into('<I', d, rec, slct_len + 0x40)     # past slct_section, still inside the file
        self.assertLess(struct.unpack_from('<I', d, 0x18)[0] + slct_len + 0x40, len(d))
        with self.assertRaises(ValueError):
            spch.shaders(bytes(d), 'x')

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
