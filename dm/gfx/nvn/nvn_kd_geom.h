// Minimal offline-testable helper for the [kd-geom] diagnostic: identity of the program actually bound to the
// geometry stage on a keydump-matched draw. Read-only: the caller passes S.bst[2]; the key callback must be
// lookup-only (prog_key_cached). Nothing here allocates, touches Metal, reads guest memory or changes state.
#ifndef NVN_KD_GEOM_H
#define NVN_KD_GEOM_H
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define KDG_MAX_KEYS 6

typedef int (*kdg_key_cached_fn)(const void *prog, unsigned index, uint8_t key[8]);

typedef struct {
    int present;                 // S.bst[2] != NULL
    uint64_t serial;             // source serial when present
    unsigned nstage;             // source prog_t.nstage (input count, not a stage number)
    unsigned nkeys;              // min(nstage, 6) processed
    unsigned cached;             // lookup-only hits among nkeys
    uint8_t have[KDG_MAX_KEYS];
    uint8_t key[KDG_MAX_KEYS][8];
    int indexed;                 // drawkind indexed vs direct
    int indirect;                // command ind != 0
    int prim;                    // original NVN primitive enum value
    int count, instances, base_instance;
} kdg_info;

// Builds only from the supplied pointer and lookup-only callback. nstage == 0 or > 6 => keys unavailable
// (no per-index lookup), matching "nil/nstage0/>capacity". Indirect arguments are never read: counts are marked
// diagnostic-only in the formatter; this function only records the scalar fields it was given.
static inline int kdg_build(kdg_info *o, const void *gs, unsigned nstage, uint64_t serial,
                            int indexed, int indirect, int prim, int count, int instances, int base_instance,
                            kdg_key_cached_fn cached_key) {
    if (!o) return 0;
    memset(o, 0, sizeof *o);
    o->indexed = indexed; o->indirect = indirect; o->prim = prim;
    o->count = count; o->instances = instances; o->base_instance = base_instance;
    if (!gs) return 1;                       // source=none, no lookup
    o->present = 1; o->serial = serial; o->nstage = nstage;
    if (nstage == 0 || nstage > KDG_MAX_KEYS) return 1;   // unavailable, no lookup
    o->nkeys = nstage;
    for (unsigned i = 0; i < o->nkeys; i++) {
        uint8_t k[8];
        if (cached_key && cached_key(gs, i, k)) { o->have[i] = 1; memcpy(o->key[i], k, 8); o->cached++; }
    }
    return 1;
}

static inline int kdg_format(char *b, size_t cap, const kdg_info *o, uint64_t frame, uint64_t pass) {
    if (!b || !cap || !o) return 0;
    char keys[KDG_MAX_KEYS * 18 + 32]; size_t at = 0; int r;
    if (!o->present) {
        r = snprintf(keys, sizeof keys, "none");
    } else if (o->nstage == 0 || o->nstage > KDG_MAX_KEYS) {
        r = snprintf(keys, sizeof keys, "unavailable");
    } else {
        r = snprintf(keys, sizeof keys, "[");
        if (r < 0 || (size_t)r >= sizeof keys) return 0;
        at = (size_t)r;
        for (unsigned i = 0; i < o->nkeys; i++) {
            char one[20];
            if (o->have[i]) r = snprintf(one, sizeof one, "%s%02x%02x%02x%02x%02x%02x%02x%02x", i ? "," : "",
                                         o->key[i][0],o->key[i][1],o->key[i][2],o->key[i][3],o->key[i][4],o->key[i][5],o->key[i][6],o->key[i][7]);
            else r = snprintf(one, sizeof one, "%sunknown", i ? "," : "");
            if (r < 0 || (size_t)r >= sizeof one || at + (size_t)r >= sizeof keys) return 0;
            memcpy(keys + at, one, (size_t)r); at += (size_t)r;
        }
        if (at + 2 > sizeof keys) return 0;
        keys[at++] = ']'; keys[at] = 0;
    }
    if (r < 0 || (size_t)r >= sizeof keys) return 0;
    const char *counts = o->indirect ? "count=unavailable instances=unavailable base_instance=unavailable"
                                     : NULL;
    if (counts) {
        r = snprintf(b, cap, "[kd-geom] F%llu pass %llu source=%s/%llu nstage=%u cached=%u/%u drawkind=%s prim=%d %s indirect=%d keys=%s",
                     (unsigned long long)frame, (unsigned long long)pass, o->present ? "present" : "none",
                     (unsigned long long)(o->present ? o->serial : 0), o->nstage, o->cached, o->nkeys,
                     o->indexed ? "indexed" : "direct", o->prim, counts, o->indirect, keys);
    } else {
        r = snprintf(b, cap, "[kd-geom] F%llu pass %llu source=%s/%llu nstage=%u cached=%u/%u drawkind=%s prim=%d count=%d instances=%d base_instance=%d indirect=%d keys=%s",
                     (unsigned long long)frame, (unsigned long long)pass, o->present ? "present" : "none",
                     (unsigned long long)(o->present ? o->serial : 0), o->nstage, o->cached, o->nkeys,
                     o->indexed ? "indexed" : "direct", o->prim, o->count, o->instances, o->base_instance, o->indirect, keys);
    }
    if (r < 0 || (size_t)r >= cap) return 0;
    return 1;
}
#endif
