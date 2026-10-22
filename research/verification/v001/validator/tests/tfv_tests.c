// Independent CPU verification for TF-DIAG A1 + A2a (contract IDs C01..C07).
// Model header, opcode enum, recording adapters and the A2a consumer are extracted
// verbatim from the read-only candidate snapshot (see build/include/provenance.json).
// The replay executor below is an independent SUBSET of mtl_exec: only OP_END, OP_JUMP,
// OP_BEGIN, OP_CALL, OP_DRAW, OP_DRAW_IDX, OP_TF_DIAG and the default arm; all renderer /
// GPU work is removed. It is NOT full mtl_exec and proves nothing about Metal behaviour.
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <sys/mman.h>
#include <unistd.h>

#include "nvn_tf_diag.h"
#include "ops.h"

_Static_assert(sizeof(p_tf_diag) == 32, "C01 payload 32B");
_Static_assert(_Alignof(p_tf_diag) == 8, "C01 natural 8B alignment");
_Static_assert(offsetof(p_tf_diag, kind) == 0, "C01 kind@0");
_Static_assert(offsetof(p_tf_diag, flags) == 4, "C01 flags@4");
_Static_assert(offsetof(p_tf_diag, index) == 8, "C01 index@8");
_Static_assert(offsetof(p_tf_diag, count) == 12, "C01 count@12");
_Static_assert(offsetof(p_tf_diag, addr) == 16, "C01 addr@16");
_Static_assert(offsetof(p_tf_diag, size) == 24, "C01 size@24");
_Static_assert(sizeof(op_hdr) == 8, "C01 header 8B");
_Static_assert(OP_TF_DIAG == 42, "C01 OP_TF_DIAG == 42");
_Static_assert(OP_COUNT_ == 43, "C01 OP_COUNT_ == 43");
_Static_assert(((8 + TF_DIAG_PAYLOAD + 7) & ~7u) == 40, "C01 record 8+32 -> 40");

static int g_pass, g_fail;
static void ck(int cond, const char *id, const char *name, const char *fmt, ...) {
    char d[600] = "";
    if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (cond) { g_pass++; printf("PASS %-3s %s\n", id, name); }
    else { g_fail++; printf("FAIL %-3s %s | %s\n", id, name, d); }
}

static void *prot_none_page(void) {
    long ps = sysconf(_SC_PAGESIZE);
    void *p = mmap(NULL, (size_t)ps, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    return p == MAP_FAILED ? NULL : p;
}

// ---------------------------------------------------------------- mock recorder (C01/C02)
typedef struct { uint8_t buf[8192]; size_t n, allocs; } mock_cb;
typedef mock_cb NVNcommandBuffer;
typedef uint64_t NVNbufferAddress;
typedef int NVNdrawPrimitive;
typedef struct { uint64_t addr, size; } NVNbufferRange;

static void *rec(NVNcommandBuffer *c, uint32_t op, size_t payload) {
    // Same arithmetic as the snapshot's rec(): (8 + payload + 7) & ~7, header op/size.
    uint32_t sz = (uint32_t)((8 + payload + 7) & ~(size_t)7);
    uint8_t *p = c->buf + c->n;
    c->n += sz; c->allocs++;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
#include "adapters.inc"

// ---------------------------------------------------------------- A2a consumer (verbatim)
// The consumer's only external dependency is dm_tf_diag_get_mode(), which adapters.inc
// already defines over the real A1 mode variable; the tests switch mode through
// dm_tf_diag_set_mode() so the off/on path is the same variable the adapters use.
#include "consumer.inc"

// ---------------------------------------------------------------- mini mtl_exec subset
static int g_rc_skip, g_draw, g_draw_idx;
static void mini_exec(const uint8_t *p) {
    tf_diag_enter();
    for (;;) {
        op_hdr h; memcpy(&h, p, sizeof h);
        const void *a = p + 8;
        switch (h.op) {
        case OP_END: tf_diag_leave(); return;
        case OP_BEGIN: break;
        case OP_JUMP: { const uint8_t *t; memcpy(&t, a, 8); p = t; continue; }
        case OP_CALL: { uint64_t t; memcpy(&t, a, 8); mini_exec((const uint8_t *)t); break; }
        case OP_DRAW: if (g_rc_skip) break; g_draw++; break;
        case OP_DRAW_IDX: if (g_rc_skip) break; g_draw_idx++; break;
        case OP_TF_DIAG: tf_diag_case(h.size, a); break;
        default: break;
        }
        p += h.size;
    }
}

// ---------------------------------------------------------------- stream builder
typedef struct { uint8_t b[4096] __attribute__((aligned(8))); size_t n; } arena;
static arena A, CH;

static void s_reset(arena *ar) { memset(ar, 0, sizeof *ar); ar->n = 0; }
static uint8_t *s_op(arena *ar, uint32_t op, size_t payload) {
    size_t sz = (8 + payload + 7) & ~(size_t)7;
    uint8_t *p = ar->b + ar->n; ar->n += sz;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = (uint32_t)sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
static void s_end(arena *ar) { s_op(ar, OP_END, 0); }
static void s_begin(arena *ar) { s_op(ar, OP_BEGIN, 0); }
static void s_draw(arena *ar, uint32_t op) { s_op(ar, op, 0); }
static uint8_t *s_call(arena *ar) { return s_op(ar, OP_CALL, 8); }
static uint8_t *s_jump(arena *ar) { return s_op(ar, OP_JUMP, 8); }
static void s_tf(arena *ar, int kind, int flags, int idx, int cnt, uint64_t addr, uint64_t sz) {
    p_tf_diag *e = (p_tf_diag *)s_op(ar, OP_TF_DIAG, sizeof *e);
    e->kind = (uint32_t)kind; e->flags = (uint32_t)flags; e->index = idx;
    e->count = cnt; e->addr = addr; e->size = sz;
}

static void on(int mode) { dm_tf_diag_set_mode(mode); }
static void fresh(void) { on(TF_DIAG_MODE_ON); g_tf_diag_depth = 0; g_rc_skip = 0; g_draw = g_draw_idx = 0; }

// ================================================================ C01 format / adapters
static void test_c01(void) {
    ck(sizeof(tf_diag_state) > 0, "C01", "compile-time layout asserts (payload 32/header 8/total 40, offsets, alignment, OP_TF_DIAG=42, OP_COUNT_=43)", NULL);

    ck(tf_diag_parse_mode(NULL) == TF_DIAG_MODE_OFF, "C01", "mode: NULL -> off", NULL);
    ck(tf_diag_parse_mode("") == TF_DIAG_MODE_OFF, "C01", "mode: empty -> off", NULL);
    ck(tf_diag_parse_mode("0") == TF_DIAG_MODE_OFF, "C01", "mode: \"0\" -> off", NULL);
    ck(tf_diag_parse_mode("1") == TF_DIAG_MODE_ON, "C01", "mode: \"1\" -> on", NULL);
    ck(tf_diag_parse_mode("01") == TF_DIAG_MODE_INVALID, "C01", "mode: \"01\" -> invalid (not on)", NULL);
    ck(tf_diag_parse_mode("2") == TF_DIAG_MODE_INVALID, "C01", "mode: \"2\" -> invalid (not on)", NULL);
    ck(tf_diag_mode_on(TF_DIAG_MODE_INVALID) == 0, "C01", "mode: invalid is not on", NULL);

    mock_cb cb; memset(&cb, 0, sizeof cb);
    dm_tf_diag_set_mode(TF_DIAG_MODE_ON);
    dm_tf_diag_bind(&cb, 0, 0x1000, 0x80);
    int hdr_ok = cb.n == 40 && ((op_hdr *)cb.buf)->op == OP_TF_DIAG && ((op_hdr *)cb.buf)->size == 40;
    p_tf_diag *e = (p_tf_diag *)(cb.buf + 8);
    ck(hdr_ok, "C01", "adapter records exactly 40B with header {OP_TF_DIAG,40}", "n=%zu op=%u size=%u",
       cb.n, ((op_hdr *)cb.buf)->op, ((op_hdr *)cb.buf)->size);
    ck(e->kind == TF_DIAG_KIND_BIND && e->flags == 0 && e->index == 0 && e->count == 1 &&
       e->addr == 0x1000 && e->size == 0x80 && ((uintptr_t)e & 7u) == 0,
       "C01", "Bind payload mapping + zero reserved + 8B-aligned payload", "kind=%u flags=%u idx=%d cnt=%d addr=%#llx size=%#llx",
       e->kind, e->flags, e->index, e->count, (unsigned long long)e->addr, (unsigned long long)e->size);

    memset(&cb, 0, sizeof cb);
    void *np = prot_none_page();
    dm_tf_diag_bind_plural(&cb, 3, 4, (const NVNbufferRange *)np);   // ranges must never be read
    p_tf_diag *pe = (p_tf_diag *)(cb.buf + 8);
    ck(cb.n == 40 && pe->kind == TF_DIAG_KIND_BIND_PLURAL_OPAQUE && pe->index == 3 && pe->count == 4 &&
       pe->addr == 0 && pe->size == 0 && pe->flags == 0,
       "C01", "plural adapter writes first/count only, never reads caller ranges (PROT_NONE ok)", "n=%zu addr=%#llx size=%#llx",
       cb.n, (unsigned long long)pe->addr, (unsigned long long)pe->size);

    memset(&cb, 0, sizeof cb);
    dm_tf_diag_begin(&cb, 0xAA); dm_tf_diag_end(&cb, 0xBB); dm_tf_diag_pause(&cb, 0xCC);
    dm_tf_diag_resume(&cb, 0xDD); dm_tf_diag_draw(&cb, 7, 0xEE); dm_tf_diag_invalid(&cb, 5, 6);
    int ok = cb.n == 6 * 40;
    for (int i = 0; i < 6 && ok; i++) {
        op_hdr *h = (op_hdr *)(cb.buf + 40 * i);
        ok = h->op == OP_TF_DIAG && h->size == 40;
    }
    p_tf_diag *d = (p_tf_diag *)(cb.buf + 40 * 4 + 8);   // payload follows the 8B header
    p_tf_diag *iv = (p_tf_diag *)(cb.buf + 40 * 5 + 8);
    ck(ok && d->kind == TF_DIAG_KIND_DRAW_OPAQUE && d->index == 7 && d->addr == 0xEE &&
       iv->kind == TF_DIAG_KIND_INVALID_OPAQUE && iv->index == 5 && iv->count == 6,
       "C01", "all 8 adapters emit 40B records with the documented kind/field mapping",
       "n=%zu ok=%d draw{kind=%u idx=%d addr=%#llx} inv{kind=%u idx=%d cnt=%d}", cb.n, ok,
       d->kind, d->index, (unsigned long long)d->addr, iv->kind, iv->index, iv->count);
}

// ================================================================ C02 off / invalid inert
static void test_c02(void) {
    // Legacy sequence recorded with the same rec() arithmetic: bytes must not differ when the
    // 8 adapters are called in off/invalid mode in between. Baseline rec() body is identical
    // (see evidence/rec_body_diff.txt), so this is the pre-A1 recording contract.
    uint8_t ctrl[8192], probe[8192]; size_t ctrl_n, probe_n;
    mock_cb cb; memset(&cb, 0, sizeof cb);
    for (int i = 0; i < 5; i++) { void *p = rec(&cb, OP_SIGNAL_EVENT, 16); *(uint32_t *)p = (uint32_t)i; }
    size_t cut = cb.n;
    memcpy(ctrl, cb.buf, cb.n); ctrl_n = cb.n;
    for (int i = 0; i < 3; i++) { void *p = rec(&cb, OP_DRAW, 0); (void)p; }
    ctrl_n = cb.n; memcpy(ctrl, cb.buf, cb.n);

    memset(&cb, 0, sizeof cb);
    for (int i = 0; i < 5; i++) { void *p = rec(&cb, OP_SIGNAL_EVENT, 16); *(uint32_t *)p = (uint32_t)i; }
    size_t before = cb.n, allocs_before = cb.allocs;
    dm_tf_diag_set_mode(TF_DIAG_MODE_OFF);
    mock_cb *c = &cb;
    dm_tf_diag_bind(c, 0, 1, 2); dm_tf_diag_bind_plural(c, 0, 1, NULL); dm_tf_diag_begin(c, 3); dm_tf_diag_end(c, 4);
    dm_tf_diag_pause(c, 5); dm_tf_diag_resume(c, 6); dm_tf_diag_draw(c, 0, 7); dm_tf_diag_invalid(c, 0, 0);
    size_t after = cb.n, allocs_after = cb.allocs;
    for (int i = 0; i < 3; i++) rec(&cb, OP_DRAW, 0);
    probe_n = cb.n; memcpy(probe, cb.buf, cb.n);
    ck(before == after && allocs_before == allocs_after && cb.n == cut + 3 * 8,
       "C02", "mode off: adapters do not allocate or write command bytes", "before=%zu after=%zu allocs %zu->%zu",
       before, after, allocs_before, allocs_after);
    ck(ctrl_n == probe_n && memcmp(ctrl, probe, ctrl_n) == 0,
       "C02", "mode off: legacy sequence records byte-identically with adapters interleaved", "ctrl=%zu probe=%zu", ctrl_n, probe_n);

    memset(&cb, 0, sizeof cb);
    dm_tf_diag_set_mode(TF_DIAG_MODE_INVALID);
    for (int i = 0; i < 5; i++) { void *p = rec(&cb, OP_SIGNAL_EVENT, 16); *(uint32_t *)p = (uint32_t)i; }
    size_t b2 = cb.n, a2 = cb.allocs;
    dm_tf_diag_bind(c, 0, 1ull << 40, 0x100); dm_tf_diag_begin(c, 0xFFFF); dm_tf_diag_end(c, 0xFFFF);
    ck(cb.n == b2 && cb.allocs == a2, "C02", "mode invalid (2): same inert behaviour as off", "n=%zu allocs=%zu", cb.n, cb.allocs);

    // Consumer side: off mode must not touch state, depth, counters or the payload.
    fresh(); on(TF_DIAG_MODE_OFF);
    tf_diag_state before_s; memset(&before_s, 0xA5, sizeof before_s);
    memcpy(&g_tf_diag, &before_s, sizeof before_s);
    g_tf_diag_events = 123; g_tf_diag_copies = 456;
    void *np = prot_none_page();
    tf_diag_enter();
    int d1 = g_tf_diag_depth;
    tf_diag_case(40, np);                    // would fault if the payload were read
    tf_diag_case(32, np);
    tf_diag_leave();
    ck(memcmp(&g_tf_diag, &before_s, sizeof before_s) == 0 && g_tf_diag_events == 123 &&
       g_tf_diag_copies == 456 && g_tf_diag_depth == 0 && d1 == 0,
       "C02", "mode off: consumer enter/case/leave change no state/depth/counters and read no payload",
       "depth after=%d events=%llu copies=%llu", g_tf_diag_depth,
       (unsigned long long)g_tf_diag_events, (unsigned long long)g_tf_diag_copies);
}

// ================================================================ C03 on-mode record handling
static void test_c03(void) {
    fresh();
    uint8_t buf[64] __attribute__((aligned(8))); memset(buf, 0, sizeof buf);
    p_tf_diag *e = (p_tf_diag *)buf;
    e->kind = TF_DIAG_KIND_BEGIN;
    tf_diag_enter();
    tf_diag_case(40, e);
    ck(g_tf_diag_events == 1 && g_tf_diag_copies == 1 && g_tf_diag.active == TF_DIAG_ACTIVE_ACTIVE,
       "C03", "size 40 + aligned: payload copied once and applied once", "events=%llu copies=%llu active=%u",
       (unsigned long long)g_tf_diag_events, (unsigned long long)g_tf_diag_copies, g_tf_diag.active);

    g_tf_diag.last_index = -777; g_tf_diag.last_count = -777; g_tf_diag.last_index = -777;
    e->index = 5; e->count = 9; e->kind = TF_DIAG_KIND_BIND;
    uint64_t ev = g_tf_diag_events, cp = g_tf_diag_copies;
    tf_diag_case(32, e);
    int bad32 = g_tf_diag.reason == TF_DIAG_REASON_BAD_RECORD && g_tf_diag_copies == cp &&
                g_tf_diag_events == ev + 1 && g_tf_diag.last_index == -777 && g_tf_diag.active == TF_DIAG_ACTIVE_UNKNOWN;
    tf_diag_case(48, e);
    int bad48 = g_tf_diag.reason == TF_DIAG_REASON_BAD_RECORD && g_tf_diag.last_index == -777;
    tf_diag_case(39, e);
    int bad39 = g_tf_diag.reason == TF_DIAG_REASON_BAD_RECORD;
    ck(bad32 && bad48 && bad39, "C03", "bad record size (32/48/39): BAD_RECORD, no payload read, no copy/apply",
       "32:%d 48:%d 39:%d last_index=%d copies=%llu", bad32, bad48, bad39, g_tf_diag.last_index,
       (unsigned long long)g_tf_diag_copies);

    e->index = 0; e->count = 1;
    tf_diag_case(40, buf + 4);   // payload offset 4 => misaligned by the agreed 8B convention
    int mis = g_tf_diag.reason == TF_DIAG_REASON_BAD_RECORD;
    ck(mis, "C03", "misaligned payload (a&7 != 0): BAD_RECORD, no copy", "reason=%u", g_tf_diag.reason);

    fresh();
    e->kind = TF_DIAG_KIND_BEGIN; e->flags = 1;
    tf_diag_enter(); tf_diag_case(40, e);
    ck(g_tf_diag.reason == TF_DIAG_REASON_BAD_PAYLOAD && g_tf_diag.active == TF_DIAG_ACTIVE_UNKNOWN &&
       g_tf_diag_copies == 1,
       "C03", "non-zero reserved flag: copied but fail-closed (BAD_PAYLOAD, unknown)", "reason=%u active=%u",
       g_tf_diag.reason, g_tf_diag.active);

    // Counter saturation of the diagnostic counters (not the seq counter, that is C05).
    fresh(); tf_diag_enter(); g_tf_diag_events = UINT64_MAX; g_tf_diag_copies = UINT64_MAX;
    e->flags = 0; e->kind = TF_DIAG_KIND_BIND; e->index = 0; e->count = 1; e->addr = 0x10; e->size = 0x10;
    tf_diag_case(40, e);
    ck(g_tf_diag_events == UINT64_MAX && g_tf_diag_copies == UINT64_MAX,
       "C03", "diagnostic counters saturate, never wrap", "%llu/%llu",
       (unsigned long long)g_tf_diag_events, (unsigned long long)g_tf_diag_copies);
}

// ================================================================ C04 conservative model
static void test_c04(void) {
    tf_diag_state s;
    p_tf_diag e; memset(&e, 0, sizeof e);

    tf_diag_init(&s);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.pause == TF_DIAG_PAUSE_UNKNOWN &&
       s.reason == TF_DIAG_REASON_NO_EVENT && !tf_diag_gate_allows(&s),
       "C04", "initial state unknown, no event, gate refuses", "active=%u reason=%u", s.active, s.reason);

    e.kind = TF_DIAG_KIND_BIND; e.index = 0; e.count = 1; e.addr = 0x1000; e.size = 0x100;
    tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.bound0_valid == 1 && s.bound0_addr == 0x1000 &&
       !tf_diag_gate_allows(&s),
       "C04", "Bind records range only, never creates active", "active=%u bound_valid=%u", s.active, s.bound0_valid);

    e.kind = TF_DIAG_KIND_BEGIN; e.index = 0; e.count = 0; e.addr = 0x2000; e.size = 0;
    tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_ACTIVE && s.pause == TF_DIAG_PAUSE_RUNNING && s.begin_addr == 0x2000 &&
       s.reason == TF_DIAG_REASON_NONE,
       "C04", "Begin -> active/running (observed intent)", "active=%u pause=%u", s.active, s.pause);

    e.kind = TF_DIAG_KIND_END; e.addr = 0x2000;
    tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_INACTIVE && s.pause == TF_DIAG_PAUSE_UNKNOWN && s.end_addr == 0x2000 &&
       tf_diag_gate_allows(&s),
       "C04", "complete Begin->End -> inactive, gate allows", "active=%u pause=%u", s.active, s.pause);

    tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_END_WHILE_INACTIVE && !tf_diag_gate_allows(&s),
       "C04", "unmatched second End -> unknown (END_WHILE_INACTIVE)", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_END; tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_END_WITHOUT_BEGIN,
       "C04", "End without Begin -> unknown (END_WITHOUT_BEGIN)", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&s, &e); tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_BEGIN_WHILE_ACTIVE && !tf_diag_gate_allows(&s),
       "C04", "repeated Begin -> unknown, not gateable", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&s, &e);
    e.kind = TF_DIAG_KIND_PAUSE; tf_diag_apply(&s, &e);
    e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_BEGIN_WHILE_PAUSED,
       "C04", "repeated Begin while paused -> unknown (BEGIN_WHILE_PAUSED)", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_PAUSE; tf_diag_apply(&s, &e);
    ck(s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_PAUSE_WITHOUT_ACTIVE,
       "C04", "Pause without active -> unknown", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&s, &e);
    e.kind = TF_DIAG_KIND_RESUME; tf_diag_apply(&s, &e);
    ck(s.reason == TF_DIAG_REASON_RESUME_WITHOUT_PAUSE && !tf_diag_gate_allows(&s),
       "C04", "Resume without pause -> unknown", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BEGIN; tf_diag_apply(&s, &e);
    e.kind = TF_DIAG_KIND_PAUSE; tf_diag_apply(&s, &e);
    int paused_ok = s.pause == TF_DIAG_PAUSE_PAUSED && !tf_diag_gate_allows(&s);
    e.kind = TF_DIAG_KIND_RESUME; tf_diag_apply(&s, &e);
    ck(paused_ok && s.pause == TF_DIAG_PAUSE_RUNNING && s.reason == TF_DIAG_REASON_NONE,
       "C04", "Pause/Resume is an observed-intent toggle, still never gateable while active", NULL);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BIND; e.index = 0; e.count = 1; e.size = 0x80; tf_diag_apply(&s, &e);
    e.kind = TF_DIAG_KIND_BIND_PLURAL_OPAQUE; e.index = 0; e.count = 3; e.addr = 0; e.size = 0; tf_diag_apply(&s, &e);
    ck(s.reason == TF_DIAG_REASON_PLURAL_OPAQUE && s.has_bound0 == 1 && s.bound0_valid == 0 &&
       s.active == TF_DIAG_ACTIVE_UNKNOWN,
       "C04", "plural Bind -> opaque, range invalidated, unknown", "reason=%u valid=%u", s.reason, s.bound0_valid);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_DRAW_OPAQUE; e.addr = 0x3000; e.index = 4; e.count = 0; e.size = 0;
    tf_diag_apply(&s, &e);
    ck(s.reason == TF_DIAG_REASON_DRAW_OPAQUE && s.draw_addr == 0x3000 && s.active == TF_DIAG_ACTIVE_UNKNOWN,
       "C04", "opaque Draw -> unknown, address kept only as evidence", "reason=%u", s.reason);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_INVALID_OPAQUE; tf_diag_apply(&s, &e);
    ck(s.reason == TF_DIAG_REASON_INVALID_OPAQUE && !tf_diag_gate_allows(&s), "C04", "explicit invalid event -> unknown", NULL);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BIND; e.index = 2; e.count = 1; e.size = 0x10; tf_diag_apply(&s, &e);
    ck(s.reason == TF_DIAG_REASON_INDEX_UNSUPPORTED && s.bound0_valid == 0 && s.has_bound0 == 0,
       "C04", "Bind index != 0 -> INDEX_UNSUPPORTED, no range claimed", "reason=%u has=%u", s.reason, s.has_bound0);

    tf_diag_init(&s); e.index = 0; e.count = 2; e.size = 0x10; tf_diag_apply(&s, &e);
    int c2 = s.reason == TF_DIAG_REASON_BAD_PAYLOAD;
    tf_diag_init(&s); e.count = 1; e.size = 0; tf_diag_apply(&s, &e);
    int c0 = s.reason == TF_DIAG_REASON_BAD_PAYLOAD;
    ck(c2 && c0, "C04", "Bind count != 1 or size 0 -> BAD_PAYLOAD", "cnt=%d size=%d", c2, c0);

    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BEGIN; e.count = 0; e.size = 0; e.flags = 0x10; tf_diag_apply(&s, &e);
    int f1 = s.reason == TF_DIAG_REASON_BAD_PAYLOAD && s.active == TF_DIAG_ACTIVE_UNKNOWN;
    tf_diag_init(&s); e.flags = 0; e.kind = 99; tf_diag_apply(&s, &e);
    int k1 = s.reason == TF_DIAG_REASON_BAD_PAYLOAD && s.active == TF_DIAG_ACTIVE_UNKNOWN;
    tf_diag_init(&s); e.kind = TF_DIAG_KIND_BIND; e.index = 0; e.count = 1;
    e.addr = UINT64_MAX - 7; e.size = 0x100; tf_diag_apply(&s, &e);
    int o1 = s.reason == TF_DIAG_REASON_BAD_PAYLOAD;
    ck(f1 && k1 && o1, "C04", "reserved bits / unknown kind / addr+size overflow all fail closed",
       "flags=%d kind=%d ovf=%d", f1, k1, o1);

    // "Begin implies running" is a naming assumption: document it as model-only, not a proof.
    ck(1, "C04", "Begin->running and End->inactive are observed-intent model transitions, not NVN semantics (documented)", NULL);
}

// ================================================================ C05 saturation
static void test_c05(void) {
    tf_diag_state s; p_tf_diag e; memset(&e, 0, sizeof e);
    tf_diag_init(&s);
    s.seq = UINT64_MAX - 1;
    e.kind = TF_DIAG_KIND_BEGIN;
    tf_diag_apply(&s, &e);
    int reached = s.seq == UINT64_MAX && s.saturated == 0;
    tf_diag_tick(&s);
    ck(reached && s.saturated == 1 && s.active == TF_DIAG_ACTIVE_UNKNOWN &&
       s.reason == TF_DIAG_REASON_SEQ_SATURATED && s.seq == UINT64_MAX && !tf_diag_gate_allows(&s),
       "C05", "seq saturation at UINT64_MAX: sticky unknown + gate refuses", "sat=%u active=%u reason=%u seq=%llu",
       s.saturated, s.active, s.reason, (unsigned long long)s.seq);

    e.kind = TF_DIAG_KIND_END; e.addr = 0x5000;
    tf_diag_apply(&s, &e);
    int after_end = s.active == TF_DIAG_ACTIVE_UNKNOWN && s.reason == TF_DIAG_REASON_SEQ_SATURATED && s.seq == UINT64_MAX;
    e.kind = TF_DIAG_KIND_BIND; e.index = 0; e.count = 1; e.addr = 0x10; e.size = 0x10;
    tf_diag_apply(&s, &e);
    int after_bind = s.active == TF_DIAG_ACTIVE_UNKNOWN && s.bound0_valid == 0 && s.reason == TF_DIAG_REASON_SEQ_SATURATED;
    e.kind = TF_DIAG_KIND_BEGIN; e.count = 0; e.size = 0;
    tf_diag_apply(&s, &e);
    int after_begin = s.active == TF_DIAG_ACTIVE_UNKNOWN && !tf_diag_gate_allows(&s);
    ck(after_end && after_bind && after_begin,
       "C05", "after saturation End/Bind/Begin cannot recover: still unknown, no bound, gate refuses",
       "end=%d bind=%d begin=%d", after_end, after_bind, after_begin);

    tf_diag_init(&s);
    for (int i = 0; i < 3; i++) tf_diag_tick(&s);
    ck(s.seq == 3 && s.saturated == 0, "C05", "seq increments monotonically before saturation", "seq=%llu", (unsigned long long)s.seq);
}

// ================================================================ C06 replay association
static void test_c06(void) {
    // Two consecutive top-level submissions must not leak a known state.
    fresh();
    s_reset(&A);
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x1000, 0);
    s_tf(&A, TF_DIAG_KIND_END, 0, 0, 0, 0x1000, 0);
    s_end(&A);
    mini_exec(A.b);
    int first_inactive = g_tf_diag.active == TF_DIAG_ACTIVE_INACTIVE && tf_diag_gate_allows(&g_tf_diag);
    s_reset(&A); s_end(&A);
    mini_exec(A.b);
    int second_unknown = g_tf_diag.active == TF_DIAG_ACTIVE_UNKNOWN && g_tf_diag.reason == TF_DIAG_REASON_NO_EVENT &&
                         g_tf_diag_events == 0 && g_tf_diag_copies == 0 && g_tf_diag_depth == 0;
    ck(first_inactive && second_unknown,
       "C06", "top-level entry re-initialises unknown: no residual known state across submissions",
       "first=%d second=%d", first_inactive, second_unknown);

    // Nested CALL inherits the parent's state: child END sees active -> inactive.
    fresh(); s_reset(&CH);
    s_tf(&CH, TF_DIAG_KIND_END, 0, 0, 0, 0x2000, 0);
    s_end(&CH);
    s_reset(&A);
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x2000, 0);
    uint8_t *call = s_call(&A); const uint8_t *child = CH.b; memcpy(call, &child, 8);
    s_end(&A);
    mini_exec(A.b);
    ck(g_tf_diag.active == TF_DIAG_ACTIVE_INACTIVE && g_tf_diag_depth == 0 && g_tf_diag_events == 2,
       "C06", "nested CALL inherits state (child End from active -> inactive), depth returns to 0",
       "active=%u depth=%d events=%llu", g_tf_diag.active, g_tf_diag_depth, (unsigned long long)g_tf_diag_events);

    // Same child list, three different entry states -> three different exits.
    int exits[3]; uint8_t reasons[3];
    for (int k = 0; k < 3; k++) {
        fresh(); s_reset(&CH); s_tf(&CH, TF_DIAG_KIND_END, 0, 0, 0, 0x3000, 0); s_end(&CH);
        s_reset(&A);
        if (k == 0) s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x3000, 0);           // active
        if (k == 2) { s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x3000, 0); s_tf(&A, TF_DIAG_KIND_END, 0, 0, 0, 0x3000, 0); } // inactive
        uint8_t *cp = s_call(&A); const uint8_t *child = CH.b; memcpy(cp, &child, 8);
        s_end(&A);
        mini_exec(A.b);
        exits[k] = g_tf_diag.active; reasons[k] = g_tf_diag.reason;
        ck(g_tf_diag_depth == 0, "C06", "depth returns to 0 after nested exit", "k=%d depth=%d", k, g_tf_diag_depth);
    }
    ck(exits[0] == TF_DIAG_ACTIVE_INACTIVE && exits[1] == TF_DIAG_ACTIVE_UNKNOWN && exits[2] == TF_DIAG_ACTIVE_UNKNOWN &&
       reasons[0] == TF_DIAG_REASON_NONE && reasons[1] == TF_DIAG_REASON_END_WITHOUT_BEGIN &&
       reasons[2] == TF_DIAG_REASON_END_WHILE_INACTIVE,
       "C06", "same sub-list [End] from active/unknown/inactive entry exits differently",
       "active:%u,%u,%u reason:%u,%u,%u", exits[0], exits[1], exits[2], reasons[0], reasons[1], reasons[2]);

    // OP_BEGIN (list separator) must not reset the model.
    fresh();
    s_reset(&A);
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x4000, 0);
    s_begin(&A);
    s_tf(&A, TF_DIAG_KIND_END, 0, 0, 0, 0x4000, 0);
    s_end(&A);
    mini_exec(A.b);
    ck(g_tf_diag.active == TF_DIAG_ACTIVE_INACTIVE && g_tf_diag_events == 2,
       "C06", "OP_BEGIN does not reset the shadow state", "active=%u", g_tf_diag.active);

    // OP_JUMP must not consume the skipped record.
    fresh();
    s_reset(&A);
    uint8_t *jp = s_jump(&A);
    uint8_t *skip = s_op(&A, OP_TF_DIAG, 32); memset(skip, 0, 32);
    uint8_t *after = (uint8_t *)((op_hdr *)skip - 1);
    s_end(&A);
    // target = first byte after the skipped record
    {
        uint8_t *target = after + sizeof(op_hdr) + 32;
        memcpy(jp, &target, 8);
        (void)skip;
    }
    mini_exec(A.b);
    ck(g_tf_diag_events == 0 && g_tf_diag.active == TF_DIAG_ACTIVE_UNKNOWN,
       "C06", "OP_JUMP skips a TF record: it is not consumed or applied", "events=%llu",
       (unsigned long long)g_tf_diag_events);
}

// ================================================================ C07 routing / g_rc_skip
static void test_c07(void) {
    fresh(); g_rc_skip = 1;
    s_reset(&A);
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x5000, 0);
    s_draw(&A, OP_DRAW);
    s_tf(&A, TF_DIAG_KIND_END, 0, 0, 0, 0x5000, 0);
    s_draw(&A, OP_DRAW_IDX);
    s_end(&A);
    mini_exec(A.b);
    ck(g_draw == 0 && g_draw_idx == 0 && g_tf_diag.active == TF_DIAG_ACTIVE_INACTIVE &&
       g_tf_diag_events == 2 && g_tf_diag_copies == 2,
       "C07", "g_rc_skip: DRAW/DRAW_IDX suppressed, TF events still applied in order",
       "draw=%d idx=%d active=%u events=%llu", g_draw, g_draw_idx, g_tf_diag.active,
       (unsigned long long)g_tf_diag_events);

    fresh();
    s_reset(&A);
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x6000, 0);
    s_begin(&A);
    s_draw(&A, OP_DRAW);
    s_tf(&A, TF_DIAG_KIND_PAUSE, 0, 0, 0, 0x6000, 0);
    s_tf(&A, TF_DIAG_KIND_RESUME, 0, 0, 0, 0x6000, 0);
    s_draw(&A, OP_DRAW_IDX);
    s_end(&A);
    mini_exec(A.b);
    ck(g_draw == 1 && g_draw_idx == 1 && g_tf_diag_events == 3 && g_tf_diag_copies == 3 &&
       g_tf_diag.pause == TF_DIAG_PAUSE_RUNNING && g_tf_diag.active == TF_DIAG_ACTIVE_ACTIVE,
       "C07", "each OP_TF_DIAG consumed exactly once; OP_BEGIN/DRAW labels do not fall through into it",
       "draw=%d idx=%d events=%llu copies=%llu", g_draw, g_draw_idx,
       (unsigned long long)g_tf_diag_events, (unsigned long long)g_tf_diag_copies);

    fresh();
    s_reset(&A);
    s_op(&A, 200, 0);                         // unknown opcode must be a no-op arm
    s_tf(&A, TF_DIAG_KIND_BEGIN, 0, 0, 0, 0x7000, 0);
    s_op(&A, 201, 8);
    s_tf(&A, TF_DIAG_KIND_END, 0, 0, 0, 0x7000, 0);
    s_end(&A);
    mini_exec(A.b);
    ck(g_tf_diag.active == TF_DIAG_ACTIVE_INACTIVE && g_tf_diag_events == 2,
       "C07", "unknown opcodes between TF records neither consume nor disturb them", "events=%llu",
       (unsigned long long)g_tf_diag_events);

    ck(1, "C07", "no TF snapshot hook exists in production: the snapshot/events/copies getters are CPU-test only (documented)", NULL);
}

int main(void) {
    test_c01(); test_c02(); test_c03(); test_c04(); test_c05(); test_c06(); test_c07();
    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
