// DM_NVN_SSBO_OBS: read-only provenance of one vertex program's storage-buffer slots (diagnostic only).
// Pure decision and formatting helpers, so the logic can be unit-tested without Metal. No allocation, no GPU object,
// no guest memory read. The caller (nvn_mtl.m) owns the real prog_t and the replay state.
#pragma once
#include <stdint.h>
#include <string.h>

#define SSBO_OBS_SLOTS 16
#define SSBO_OBS_STAGES 6        // real prog_t capacity: nvn_obj.h has sd[6], ProgramSetShaders rejects n > 6
#define SSBO_OBS_MAXKEYS 8       // record bound: never truncate a larger nstage and call it complete

typedef struct { uint8_t known, index; uint64_t frame, seq; } ssbo_obs_binding;
typedef struct {
    int mode;                    // 0 off, 1 armed, 2 closed (done, invalid or format error)
    uint8_t key[8];
    uint8_t skips, unknown, invalid, done;
    uint64_t obs_seq, bind_seq, frame, pass_counter;
    ssbo_obs_binding lb[SSBO_OBS_SLOTS];   // vertex stage only; updated by real OP_BIND_SSBO
} ssbo_obs_state;

enum { SSBO_OBS_NIL = 0, SSBO_OBS_HIT, SSBO_OBS_UNKNOWN, SSBO_OBS_NO_TARGET, SSBO_OBS_INVALID_COUNT };

// 16 lowercase hex digits -> key bytes. Returns 1 on success, 0 for absent or malformed (caller logs once and closes).
static int ssbo_obs_parse(const char *v, uint8_t key[8]) {
    if (!v || !*v) return 0;
    if (strlen(v) != 16) return 0;
    for (int i = 0; i < 16; i++) {
        char c = v[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    for (int i = 0; i < 8; i++) {
        unsigned hi = (unsigned)((v[2*i] <= '9') ? v[2*i] - '0' : v[2*i] - 'a' + 10);
        unsigned lo = (unsigned)((v[2*i+1] <= '9') ? v[2*i+1] - '0' : v[2*i+1] - 'a' + 10);
        key[i] = (uint8_t)((hi << 4) | lo);
    }
    return 1;
}

// nstage 0 or beyond the real capacity is invalid, never truncated into "all cached" or "target absent".
static int ssbo_obs_verdict(unsigned nstage, unsigned cap, unsigned known, int hit) {
    if (nstage == 0 || nstage > cap) return SSBO_OBS_INVALID_COUNT;
    if (hit >= 0) return SSBO_OBS_HIT;
    return known == nstage ? SSBO_OBS_NO_TARGET : SSBO_OBS_UNKNOWN;
}

// Real bind: stage 0 only, index < 16; anything else is ignored (no pollution of the vertex table).
static void ssbo_obs_note_bind(ssbo_obs_state *s, unsigned stage, unsigned index, uint64_t frame, uint64_t seq) {
    if (s->mode != 1 || stage != 0 || index >= SSBO_OBS_SLOTS) return;
    ssbo_obs_binding *b = &s->lb[index];
    b->known = 1; b->index = (uint8_t)index; b->frame = frame; b->seq = seq;
}

// candidates: raw non-zero addr only; a zero addr with a real bind is an explicit unbind, not "unknown".
static int ssbo_obs_candidates(const uint64_t addr[SSBO_OBS_SLOTS]) {
    int n = 0; for (int i = 0; i < SSBO_OBS_SLOTS; i++) if (addr[i]) n++;
    return n;
}

// Bounded formatting: returns the snprintf length, or -1 when it does not fit (caller logs a format error and closes).
static int ssbo_obs_fmt_slot(char *b, size_t n, int i, uint64_t addr, uint64_t size, const ssbo_obs_binding *lb) {
    int r = lb->known
        ? snprintf(b, n, "[ssbo-obs] slot%02d addr=%#llx size=%llu bind=real-index%d frame=%llu seq=%llu%s", i,
                   (unsigned long long)addr, (unsigned long long)size, (int)lb->index,
                   (unsigned long long)lb->frame, (unsigned long long)lb->seq, addr ? "" : " explicit-unbind")
        : snprintf(b, n, "[ssbo-obs] slot%02d addr=%#llx size=%llu bind=unknown-provenance", i,
                   (unsigned long long)addr, (unsigned long long)size);
    return (r < 0 || (size_t)r >= n) ? -1 : r;
}
