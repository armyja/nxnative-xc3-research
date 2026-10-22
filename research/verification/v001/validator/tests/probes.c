// Targeted counterexample probes (findings), NOT part of the pass/fail contract suite.
// Exit 0 = finding reproduced as described; exit 2 = expected behaviour (finding not reproduced).
// Probe names: depth-leak | bad-kind | oob
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>

#include "nvn_tf_diag.h"
#include "ops.h"

typedef struct { uint8_t buf[8192]; size_t n, allocs; } mock_cb;
typedef mock_cb NVNcommandBuffer;
typedef uint64_t NVNbufferAddress;
typedef int NVNdrawPrimitive;
typedef struct { uint64_t addr, size; } NVNbufferRange;
static void *rec(NVNcommandBuffer *c, uint32_t op, size_t payload) {
    uint32_t sz = (uint32_t)((8 + payload + 7) & ~(size_t)7);
    uint8_t *p = c->buf + c->n; c->n += sz; c->allocs++;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
#include "adapters.inc"
#include "consumer.inc"

static int g_rc_skip, g_draw;
static void mini_exec(const uint8_t *p) {
    tf_diag_enter();
    for (;;) {
        op_hdr h; memcpy(&h, p, sizeof h);
        const void *a = p + 8;
        switch (h.op) {
        case OP_END: tf_diag_leave(); return;
        case OP_BEGIN: break;
        case OP_CALL: { uint64_t t; memcpy(&t, a, 8); mini_exec((const uint8_t *)t); break; }
        case OP_DRAW: if (g_rc_skip) break; g_draw++; break;
        case OP_TF_DIAG: tf_diag_case(h.size, a); break;
        default: break;
        }
        p += h.size;
    }
}

static int depth_leak(void) {
    // Scenario: a submission starts with mode ON, mode is switched OFF mid-submission
    // (only dm_tf_diag_set_mode can do that; A1 never calls it after startup), then back ON
    // for the next submission. tf_diag_leave() is guarded by tf_diag_on(), so depth leaks.
    static uint8_t sub[64] __attribute__((aligned(8)));
    memset(sub, 0, sizeof sub);
    ((op_hdr *)sub)->op = OP_END; ((op_hdr *)sub)->size = 8;

    dm_tf_diag_set_mode(TF_DIAG_MODE_ON);
    tf_diag_enter();                       // submission 1 top level: depth 0 -> 1, state init
    dm_tf_diag_set_mode(TF_DIAG_MODE_OFF);
    tf_diag_leave();                       // leave is a no-op while off: depth stays 1
    int leaked = g_tf_diag_depth;

    dm_tf_diag_set_mode(TF_DIAG_MODE_ON);
    // Give the shadow a known state, then show submission 2 does not re-initialise it.
    p_tf_diag e; memset(&e, 0, sizeof e);
    e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&g_tf_diag, &e);
    e.kind = TF_DIAG_KIND_END;   tf_diag_apply(&g_tf_diag, &e);
    int before2 = g_tf_diag.active;
    mini_exec(sub);                        // "submission 2": enter sees depth 2, no re-init
    int after2 = g_tf_diag.active, depth_after2 = g_tf_diag_depth;
    tf_diag_leave();

    printf("EXPECTED depth=0 after off-mode leave, second submission re-initialised to unknown\n");
    printf("ACTUAL   leaked depth=%d, state before 2nd submission=%s, state after 2nd submission=%s, depth after=%d\n",
           leaked, tf_diag_active_name(before2), tf_diag_active_name(after2), depth_after2);
    printf("VERDICT  %s\n", (leaked != 0 && after2 == before2) ? "FINDING-REPRODUCED" : "NOT-REPRODUCED");
    return (leaked != 0 && after2 == before2) ? 0 : 2;
}

static int bad_kind(void) {
    // TF_DIAG_REASON_BAD_KIND exists, but tf_diag_payload_ok rejects kind > 7 as BAD_PAYLOAD,
    // so the switch default arm is unreachable with the current validation order.
    tf_diag_state s; tf_diag_init(&s);
    p_tf_diag e; memset(&e, 0, sizeof e); e.kind = TF_DIAG_KIND_INVALID_OPAQUE + 1;
    tf_diag_apply(&s, &e);
    printf("EXPECTED reason=BAD_KIND(14) for kind=8 if the enum reason were reachable\n");
    printf("ACTUAL   reason=%u (%s), active=%s\n", s.reason,
           s.reason == TF_DIAG_REASON_BAD_KIND ? "BAD_KIND" : "BAD_PAYLOAD",
           tf_diag_active_name(s.active));
    printf("VERDICT  %s\n", s.reason == TF_DIAG_REASON_BAD_PAYLOAD ? "FINDING-REPRODUCED (dead enum value, still fail-closed)" : "NOT-REPRODUCED");
    return s.reason == TF_DIAG_REASON_BAD_PAYLOAD ? 0 : 2;
}

static int oob(void) {
    // The consumer trusts the record's own size field. A record whose header claims 40 bytes
    // but whose payload is shorter makes the 32-byte copy run past the written bytes; this is
    // why the size check must not be described as stream/memory-boundary protection.
    uint8_t *rec = malloc(8 + 16 + 8);      // header + 16 payload bytes + one trailing header
    memset(rec, 0, 8 + 16 + 8);
    ((op_hdr *)rec)->op = OP_TF_DIAG; ((op_hdr *)rec)->size = 40;   // claims 32B payload
    dm_tf_diag_set_mode(TF_DIAG_MODE_ON);
    tf_diag_enter();
    tf_diag_case(40, rec + 8);              // memcpy 32 from rec+8, only 24 bytes are valid
    printf("EXPECTED (under ASan) heap-buffer-overflow reported for the 32B payload copy\n");
    printf("ACTUAL   no ASan report; copies=%llu\n", (unsigned long long)g_tf_diag_copies);
    free(rec);
    return 2;
}

int main(int argc, char **argv) {
    const char *w = argc > 1 ? argv[1] : "";
    if (!strcmp(w, "depth-leak")) return depth_leak();
    if (!strcmp(w, "bad-kind")) return bad_kind();
    if (!strcmp(w, "oob")) return oob();
    fprintf(stderr, "usage: %s depth-leak|bad-kind|oob\n", argv[0]);
    return 64;
}
