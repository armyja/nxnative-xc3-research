// Unit tests for the pure part of DM_NVN_SSBO_OBS (no Metal, no replay). The wiring is checked separately.
#include <assert.h>
#include <stdio.h>
#include "../nvn_ssboobs.h"

static int fails;
#define CK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok   %s\n", m); } while (0)

int main(void) {
    uint8_t key[8];
    // parse
    CK(!ssbo_obs_parse(NULL, key), "absent value rejected");
    CK(!ssbo_obs_parse("", key), "empty value rejected");
    CK(!ssbo_obs_parse("4bae5b8abd3bec7", key), "15 digits rejected");
    CK(!ssbo_obs_parse("4bae5b8abd3bec7fg", key), "non-hex rejected");
    CK(!ssbo_obs_parse("4BAE5B8ABD3BEC7F", key), "uppercase rejected (lowercase only)");
    CK(ssbo_obs_parse("4bae5b8abd3bec7f", key), "valid 16 lowercase hex accepted");
    CK(key[0] == 0x4b && key[7] == 0x7f, "key bytes decoded");

    // verdict: 0, capacity, beyond capacity, partial cache
    CK(ssbo_obs_verdict(0, SSBO_OBS_STAGES, 0, -1) == SSBO_OBS_INVALID_COUNT, "nstage 0 is invalid, not absent");
    CK(ssbo_obs_verdict(6, SSBO_OBS_STAGES, 6, -1) == SSBO_OBS_NO_TARGET, "6 of 6 cached without hit: no target");
    CK(ssbo_obs_verdict(7, SSBO_OBS_STAGES, 7, -1) == SSBO_OBS_INVALID_COUNT, "7 entries beyond capacity is invalid, never truncated");
    CK(ssbo_obs_verdict(2, SSBO_OBS_STAGES, 1, -1) == SSBO_OBS_UNKNOWN, "partial cache without hit: identity unknown");
    CK(ssbo_obs_verdict(2, SSBO_OBS_STAGES, 1, 0) == SSBO_OBS_HIT, "hit holds even when another entry is unknown");
    CK(ssbo_obs_verdict(2, SSBO_OBS_STAGES, 2, 1) == SSBO_OBS_HIT, "hit at index 1");

    // bind updates: stage 0 only, index < 16, and provenance retained
    ssbo_obs_state s; memset(&s, 0, sizeof s); s.mode = 1;
    ssbo_obs_note_bind(&s, 1, 0, 10, 1);
    CK(!s.lb[0].known, "fragment-stage bind does not pollute the vertex table");
    ssbo_obs_note_bind(&s, 0, 16, 10, 2);
    CK(!s.lb[0].known && !s.lb[15].known, "index 16 rejected");
    ssbo_obs_note_bind(&s, 0, 0, 10, 3);
    CK(s.lb[0].known && s.lb[0].frame == 10 && s.lb[0].seq == 3, "vertex bind recorded with frame and sequence");
    ssbo_obs_note_bind(&s, 0, 0, 20, 9);
    CK(s.lb[0].frame == 20 && s.lb[0].seq == 9, "later bind updates provenance");
    s.mode = 2; ssbo_obs_note_bind(&s, 0, 1, 30, 10);
    CK(!s.lb[1].known, "closed diagnostic records no binds");

    // candidates and explicit unbind
    uint64_t addr[16]; memset(addr, 0, sizeof addr);
    CK(ssbo_obs_candidates(addr) == 0, "no non-zero addr: zero candidates");
    addr[3] = 0x1000; CK(ssbo_obs_candidates(addr) == 1, "one non-zero addr: unique candidate");
    addr[9] = 0x2000; CK(ssbo_obs_candidates(addr) == 2, "two non-zero addrs: ambiguous input");
    char b[200];
    ssbo_obs_binding unb = {1, 3, 40, 11};
    CK(ssbo_obs_fmt_slot(b, sizeof b, 3, 0, 128, &unb) > 0 && strstr(b, "explicit-unbind"), "zero addr with a real bind is an explicit unbind");
    ssbo_obs_binding none = {0, 0, 0, 0};
    CK(ssbo_obs_fmt_slot(b, sizeof b, 4, 0, 0, &none) > 0 && strstr(b, "unknown-provenance"), "no observed bind is unknown-provenance, not never-bound");
    CK(ssbo_obs_fmt_slot(b, sizeof b, 15, 0xdeadbeefcafeull, 4096, &unb) > 0 && strstr(b, "slot15"), "worst-case slot fits");
    CK(ssbo_obs_fmt_slot(b, 8, 0, 0x1000, 16, &unb) < 0, "short buffer reports failure, not a truncated success");

    printf("fails: %s\n", fails ? "yes" : "none");
    return fails ? 1 : 0;
}
