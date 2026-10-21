// Diagnostic-only helper for DM_NVN_PSOFAIL_RT_MULTI: fixed-key parsing, per-key signature de-duplication and bounded
// record accounting. No GPU object, no shader materialization, no guest read, no cache/PSO change.
#ifndef NVN_PSORT_MULTI_H
#define NVN_PSORT_MULTI_H
#include <stdint.h>
#include <string.h>

#define PSM_MAX_KEYS 6
#define PSM_MAX_RECORDS 12
#define PSM_MAX_SIGS 2
#define PSM_SIG_WORDS 17          // cfmt[8] + map_enabled + lmap[8]

typedef struct {
    char key[17];
    uint32_t sig[PSM_MAX_SIGS][PSM_SIG_WORDS];
    int nrec;
    int done;                    // terminal (limit note / diagnostic error / global cap)
    int cached_note;
    int limit_note;
} psm_key;

typedef struct {
    int mode;                    // 0 off, 1 armed, 2 closed
    int n;
    int global_records;
    int global_note;
    psm_key k[PSM_MAX_KEYS];
} psm_state;

static inline int psm_hex16(const char *s) {
    if (!s) return 0;
    for (int i = 0; i < 16; i++) {
        char c = s[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    return s[16] == 0;
}
static inline int psm_hex16n(const char *s) {
    for (int i = 0; i < 16; i++) {
        char c = s[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return 0;
    }
    return 1;
}

// Returns 0 for off/armed, -1 for invalid multi (closed), -2 for single/multi conflict (both disabled).
static inline int psm_parse(psm_state *st, const char *single, const char *multi) {
    memset(st, 0, sizeof *st);
    int hs = single && single[0], hm = multi && multi[0];
    if (hs && hm) { st->mode = 2; return -2; }
    if (!hm) { st->mode = 0; return 0; }
    int n = 0;
    const char *p = multi;
    while (*p) {
        const char *q = strchr(p, ',');
        size_t len = q ? (size_t)(q - p) : strlen(p);
        if (len != 16 || n >= PSM_MAX_KEYS || !psm_hex16n(p)) { st->mode = 2; return -1; }
        char key[17]; memcpy(key, p, 16); key[16] = 0;
        for (int i = 0; i < n; i++) if (!memcmp(st->k[i].key, key, 16)) { st->mode = 2; return -1; }
        memcpy(st->k[n].key, key, 17); n++;
        if (!q) break;
        p = q + 1;
        if (!*p) { st->mode = 2; return -1; }
    }
    if (n < 1 || n > PSM_MAX_KEYS) { st->mode = 2; return -1; }
    st->mode = 1; st->n = n;
    return 0;
}

static inline void psm_sig(uint32_t out[PSM_SIG_WORDS], const uint32_t cfmt[8], int map_enabled, const uint8_t lmap[8]) {
    for (int i = 0; i < 8; i++) out[i] = cfmt[i];
    out[8] = map_enabled ? 1u : 0u;
    for (int i = 0; i < 8; i++) out[9 + i] = lmap[i];
}

// Returns 1 for a new record, 0 for a silent duplicate, -1 for the per-key third-signature limit, -2 for the global
// record limit, -3 when this key is already terminal.
static inline int psm_accept(psm_state *st, int i, const uint32_t sig[PSM_SIG_WORDS]) {
    if (st->mode != 1 || i < 0 || i >= st->n) return -3;
    psm_key *k = &st->k[i];
    if (k->done) return -3;
    if (k->nrec >= PSM_MAX_SIGS) {
        if (!k->limit_note) { k->limit_note = 1; k->done = 1; return -1; }
        return -3;
    }
    if (st->global_records >= PSM_MAX_RECORDS) {
        if (!st->global_note) {
            st->global_note = 1;
            for (int j = 0; j < st->n; j++) st->k[j].done = 1;
            return -2;
        }
        return -3;
    }
    for (int s = 0; s < k->nrec; s++) if (!memcmp(k->sig[s], sig, sizeof(uint32_t) * PSM_SIG_WORDS)) return 0;
    memcpy(k->sig[k->nrec], sig, sizeof(uint32_t) * PSM_SIG_WORDS);
    k->nrec++;
    st->global_records++;
    return 1;
}

static inline int psm_cached_note(psm_state *st, int i) {
    if (st->mode != 1 || i < 0 || i >= st->n || st->k[i].done) return 0;
    if (st->k[i].cached_note) return 0;
    st->k[i].cached_note = 1;
    return 1;
}

static inline void psm_error(psm_state *st, int i) {
    if (st->mode == 1 && i >= 0 && i < st->n) st->k[i].done = 1;
}

static inline int psm_find(const psm_state *st, const char *fs_key) {
    if (st->mode != 1 || !fs_key) return -1;
    for (int i = 0; i < st->n; i++) {
        if (!strncmp(fs_key, st->k[i].key, 16) && (fs_key[16] == 0 || !strcmp(fs_key + 16, "_b"))) return i;
    }
    return -1;
}
#endif
