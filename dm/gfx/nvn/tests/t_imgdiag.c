// Behaviour test for the image-binding diagnostic. Drives the same functions the renderer calls; no GPU, no guest.
#include "nvn_imgdiag.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fails;
#define CHECK(c, m) do { if (!(c)) { printf("FAIL: %s\n", m); fails++; } } while (0)

static void keys_of(imgdiag_snapshot *s, const char *const *hex, int n) {
    s->nkeys = n;
    for (int i = 0; i < n; i++) imgdiag_parse_key(hex[i], s->keys[i]);
}

int main(void) {
    uint8_t k[8], t[8];

    // 1. key parsing: exactly 16 hex digits, nothing else
    CHECK(imgdiag_parse_key("4bae5b8abd3bec7f", k) && k[0] == 0x4b && k[7] == 0x7f, "valid key parses");
    CHECK(!imgdiag_parse_key("4bae5b8abd3bec7", k), "15 digits rejected");
    CHECK(!imgdiag_parse_key("4bae5b8abd3bec7f0", k), "17 digits rejected");
    CHECK(!imgdiag_parse_key("4bae5b8abd3bec7g", k), "non-hex rejected");
    CHECK(!imgdiag_parse_key("", k), "empty rejected");

    // 2. arming: default off, invalid disables, valid arms
    unsetenv("DM_NVN_IMGBIND"); imgdiag_reset();
    CHECK(!imgdiag_arm() && !imgdiag_armed(), "off by default");
    setenv("DM_NVN_IMGBIND", "not-a-key", 1); imgdiag_reset();     // reset, else the earlier decision is cached
    CHECK(!imgdiag_arm() && !imgdiag_armed(), "invalid key does not arm");
    CHECK(!imgdiag_arm(), "invalid stays disabled on a second call (decision is latched)");
    imgdiag_reset();
    setenv("DM_NVN_IMGBIND", "4bae5b8abd3bec7f", 1);
    CHECK(imgdiag_arm() && imgdiag_armed(), "valid key arms");

    // 3. target matching among shader-data entries (index 0 must work: a single pixel shader lives at index 0)
    imgdiag_parse_key("4bae5b8abd3bec7f", t);
    { uint8_t one[1][8]; imgdiag_parse_key("4bae5b8abd3bec7f", one[0]);
      CHECK(imgdiag_find_key((const uint8_t (*)[8])one, 1, t) == 0, "single entry at index 0 matches"); }
    { uint8_t two[2][8]; imgdiag_parse_key("aaaaaaaaaaaaaaaa", two[0]); imgdiag_parse_key("4bae5b8abd3bec7f", two[1]);
      CHECK(imgdiag_find_key((const uint8_t (*)[8])two, 2, t) == 1, "match at index 1"); }
    { uint8_t none[1][8]; imgdiag_parse_key("bbbbbbbbbbbbbbbb", none[0]);
      CHECK(imgdiag_find_key((const uint8_t (*)[8])none, 1, t) == -1, "absent key"); }

    // 4. classification: zero slots, exactly one, several
    imgdiag_snapshot s; memset(&s, 0, sizeof s);
    CHECK(!strcmp(imgdiag_classify(&s), "no-image-state"), "all-zero is no-image-state");
    s.slot[3].handle = 0x12345;
    CHECK(!strcmp(imgdiag_classify(&s), "unique-candidate"), "one non-zero is unique-candidate");
    s.slot[7].handle = 0x99;
    CHECK(!strcmp(imgdiag_classify(&s), "ambiguous"), "two non-zero is ambiguous");

    // 5. source metadata: only the fragment stage, only slots the command covers, and an old slot keeps its own source
    imgdiag_note_bind(1, 0, 1, 100, 1);      // frame 100 writes slot 0 only
    imgdiag_note_bind(1, 4, 2, 200, 2);      // frame 200 writes slots 4 and 5
    imgdiag_note_bind(0, 9, 1, 300, 3);      // vertex stage: ignored
    imgdiag_slot src[IMGDIAG_SLOTS]; imgdiag_copy_sources(src);
    CHECK(src[0].write_frame == 100 && src[0].write_count == 1, "slot 0 keeps the first command as its source");
    CHECK(src[4].write_frame == 200 && src[5].write_cmd == 2, "slots 4/5 from the second command");
    CHECK(src[9].write_frame == 0, "vertex-stage bind records nothing");
    CHECK(src[1].write_frame == 0, "a slot not covered by any command has no source");

    // 6. conditional-rendering skips are counted separately from an actual draw
    imgdiag_note_skipped(); imgdiag_note_skipped();
    CHECK(imgdiag_skipped() == 2, "skipped draws counted");

    // 7. the record: one buffer, every key and every non-zero slot, and it fits
    memset(&s, 0, sizeof s);
    const char *hex[] = { "aaaaaaaaaaaaaaaa", "4bae5b8abd3bec7f" };
    keys_of(&s, hex, 2); s.hit_index = 1; s.keys_cached = 1; s.frame = 7; s.pass = 9; s.match = 1; s.bindseq = 3;
    s.slot[0].handle = 0xdead; s.slot[0].registered = 1; s.slot[0].fmt = 71; s.slot[0].w = 960; s.slot[0].h = 544;
    s.slot[5].handle = 0xbeef;
    char buf[IMGDIAG_REC];
    size_t n = imgdiag_format(buf, sizeof buf, &s, t, "test");
    CHECK(n > 0 && n < sizeof buf, "record fits");
    CHECK(strstr(buf, "4bae5b8abd3bec7f*") != NULL, "hit key marked");
    CHECK(strstr(buf, "slot 0 ") && strstr(buf, "960x544"), "slot 0 with descriptor");
    CHECK(strstr(buf, "slot 5 "), "slot 5 listed");
    CHECK(strstr(buf, "class=ambiguous"), "classification present");
    CHECK(!strstr(buf, "slot 1 "), "zero slots omitted");
    // a buffer too small must be refused rather than truncating into the middle of a record
    CHECK(imgdiag_format(buf, 40, &s, t, "test") == 0, "short buffer refused");

    // 8. full 32 slots and 6 keys must still fit the record, and a short buffer must be refused, not truncated
    memset(&s, 0, sizeof s);
    const char *six[] = { "aaaaaaaaaaaaaaaa", "bbbbbbbbbbbbbbbb", "cccccccccccccccc",
                          "dddddddddddddddd", "eeeeeeeeeeeeeeee", "4bae5b8abd3bec7f" };
    keys_of(&s, six, 6); s.hit_index = 5; s.match = 1; s.bindseq = 2; s.noid = 0;
    for (int i = 0; i < IMGDIAG_SLOTS; i++) {
        s.slot[i].handle = 0xffffffffffffffffull; s.slot[i].serial = 18446744073709551615ull;
        s.slot[i].registered = 1; s.slot[i].fmt = 0xffff; s.slot[i].w = s.slot[i].h = s.slot[i].depth = 65535;
        s.slot[i].type = 255; s.slot[i].write_frame = 18446744073709551615ull; s.slot[i].write_cmd = 18446744073709551615ull;
        s.slot[i].write_stage = 5; s.slot[i].write_first = 31; s.slot[i].write_count = 32;
    }
    n = imgdiag_format(buf, sizeof buf, &s, t, "max");
    CHECK(n > 0 && n < sizeof buf, "worst case (32 slots, 6 keys, maximum field values) fits");
    CHECK(!strcmp(imgdiag_classify(&s), "ambiguous"), "32 non-zero slots classify as ambiguous");
    CHECK(imgdiag_format(buf, 4096, &s, t, "max") == 0, "the old 4096 bound is not enough, and is refused");

    // 9. one-shot: after disarming, the same match must not fire again
    imgdiag_disarm();
    CHECK(!imgdiag_armed(), "disarmed after one record");

    printf(fails ? "t_imgdiag: %d failure(s)\n" : "t_imgdiag: ok\n", fails);
    return fails != 0;
}
