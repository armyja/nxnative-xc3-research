// Pure logic of the image-binding diagnostic: key parsing, target match, classification, record formatting and the
// bounded per-slot source table. No Metal, no renderer state, so it can be driven by a plain C test.
#include "nvn_imgdiag.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static struct {
    int armed, checked, invalid;
    uint8_t target[8];
    imgdiag_slot src[IMGDIAG_SLOTS];
    uint64_t skipped;
} D;

int imgdiag_parse_key(const char *s, uint8_t out[8]) {
    if (!s) return 0;
    size_t n = strlen(s);
    if (n != 16) return 0;                       // exactly 16: no shorter key, no prefix match
    for (size_t i = 0; i < 16; i++) {
        int c = s[i], v;
        if (c >= '0' && c <= '9') v = c - '0';
        else if (c >= 'a' && c <= 'f') v = c - 'a' + 10;
        else if (c >= 'A' && c <= 'F') v = c - 'A' + 10;
        else return 0;
        if (i & 1) out[i >> 1] = (uint8_t)((out[i >> 1] & 0xf0) | v);
        else       out[i >> 1] = (uint8_t)(v << 4);
    }
    return 1;
}

int imgdiag_find_key(const uint8_t keys[][8], int n, const uint8_t target[8]) {
    for (int i = 0; i < n; i++) if (!memcmp(keys[i], target, 8)) return i;
    return -1;
}

const char *imgdiag_classify(const imgdiag_snapshot *s) {
    int nz = 0;
    for (int i = 0; i < IMGDIAG_SLOTS; i++) if (s->slot[i].handle) nz++;
    return nz == 0 ? "no-image-state" : nz == 1 ? "unique-candidate" : "ambiguous";
}

size_t imgdiag_format(char *buf, size_t n, const imgdiag_snapshot *s, const uint8_t target[8], const char *target_src) {
    size_t o = 0;
    int w = snprintf(buf, n, "[imgdiag] target=%02x%02x%02x%02x%02x%02x%02x%02x src=%s frame=%llu pass=%llu "
                              "match=%llu bindseq=%llu noid=%llu hit=%d class=%s skipped=%llu\n",
                     target[0], target[1], target[2], target[3], target[4], target[5], target[6], target[7],
                     target_src ? target_src : "-", (unsigned long long)s->frame, (unsigned long long)s->pass,
                     (unsigned long long)s->match, (unsigned long long)s->bindseq, (unsigned long long)s->noid,
                     s->hit_index,
                     imgdiag_classify(s), (unsigned long long)imgdiag_skipped());
    if (w < 0 || (size_t)w >= n) return 0;
    o = (size_t)w;
    w = snprintf(buf + o, n - o, "[imgdiag] keys:");
    if (w < 0 || (size_t)w >= n - o) return 0;
    o += (size_t)w;
    for (int i = 0; i < s->nkeys; i++) {
        w = snprintf(buf + o, n - o, " %02x%02x%02x%02x%02x%02x%02x%02x%s", s->keys[i][0], s->keys[i][1], s->keys[i][2],
                     s->keys[i][3], s->keys[i][4], s->keys[i][5], s->keys[i][6], s->keys[i][7], i == s->hit_index ? "*" : "");
        if (w < 0 || (size_t)w >= n - o) return 0;
        o += (size_t)w;
    }
    w = snprintf(buf + o, n - o, "\n");
    if (w < 0 || (size_t)w >= n - o) return 0;
    o += (size_t)w;
    for (int i = 0; i < IMGDIAG_SLOTS; i++) {
        const imgdiag_slot *k = &s->slot[i];
        if (!k->handle) continue;
        w = snprintf(buf + o, n - o, "[imgdiag] slot %d handle=%#llx ser=%llu reg=%u fmt=%#x %ux%ux%u type=%u "
                                      "lastbind=frame%llu/cmd%llu/st%d/first%d/n%d\n",
                     i, (unsigned long long)k->handle, (unsigned long long)k->serial, k->registered, k->fmt, k->w, k->h,
                     k->depth, k->type, (unsigned long long)k->write_frame, (unsigned long long)k->write_cmd,
                     k->write_stage, k->write_first, k->write_count);
        if (w < 0 || (size_t)w >= n - o) return 0;
        o += (size_t)w;
    }
    return o;
}

int imgdiag_arm(void) {
    if (D.checked) return D.armed && !D.invalid;
    D.checked = 1;
    const char *e = getenv("DM_NVN_IMGBIND");
    if (!e || !*e) return 0;                       // default off
    if (!imgdiag_parse_key(e, D.target)) {
        D.invalid = 1;
        fprintf(stderr, "[imgdiag] DM_NVN_IMGBIND=%s is not exactly 16 hex digits: diagnostic disabled\n", e);
        return 0;
    }
    D.armed = 1;
    return 1;
}
int imgdiag_armed(void) { return D.armed; }
void imgdiag_disarm(void) { D.armed = 0; }
void imgdiag_target(uint8_t out[8]) { memcpy(out, D.target, 8); }
void imgdiag_reset(void) { D.armed = D.checked = D.invalid = 0; D.skipped = 0; memset(D.src, 0, sizeof D.src); }

void imgdiag_note_bind(int stage, int first, int count, uint64_t frame, uint64_t cmd) {
    if (!D.armed || stage != 1) return;            // only the fragment stage carries the image table we watch
    if (first < 0 || count <= 0 || first + count > IMGDIAG_SLOTS) return;
    for (int i = 0; i < count; i++) {
        imgdiag_slot *s = &D.src[first + i];
        s->write_frame = frame; s->write_cmd = cmd; s->write_first = first; s->write_count = count; s->write_stage = stage;
    }
}
void imgdiag_copy_sources(imgdiag_slot *slots) { memcpy(slots, D.src, sizeof D.src); }
void imgdiag_note_skipped(void) { D.skipped++; }
uint64_t imgdiag_skipped(void) { return D.skipped; }
