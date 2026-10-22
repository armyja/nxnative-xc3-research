// V005: D02 fix (install-then-publish), D04 fix (explicit HIT guard), integrated same-process checks.
// Extracted verbatim: hle 71-144 (mode/installer/activate/init), adapters 834-848,
// consumer 7757-7785, wanted+formatter 5557-5573, emit tail 5675-5683.
// Verifier supplies: slot/name tables, section stub, LOG/MLOG sinks, gs-res struct, mock command buffer.
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#include "nvn_tf_diag.h"
#include "nvn_kd_res.h"
#include "ops.inc"

#define NVN_NFUNC 32
typedef struct { _Atomic uint64_t cnt; void *fn; } nvn_slot_t;
static nvn_slot_t nvn_slot[NVN_NFUNC];
static const char *nvn_names[NVN_NFUNC];
static void nvn_unimpl_entry(void) {}
typedef struct mock_cb NVNcommandBuffer;
typedef uint64_t NVNbufferAddress;
typedef int NVNdrawPrimitive;
typedef struct { uint64_t addr, size; } NVNbufferRange;

int dm_tf_diag_get_mode(void);
static char g_logbuf[16384]; static size_t g_log_n; static int g_log_lines;
static int g_getter_at_failure = -1, g_getter_at_success_log = -1;
static void LOG(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    char tmp[1024]; int n = vsnprintf(tmp, sizeof tmp, fmt, ap); va_end(ap);
    if (n > 0) {
        if (strstr(tmp, "not installed")) g_getter_at_failure = dm_tf_diag_get_mode();
        if (strstr(tmp, "adapters installed")) g_getter_at_success_log = dm_tf_diag_get_mode();
        int w = snprintf(g_logbuf + g_log_n, sizeof g_logbuf - g_log_n, "%s\n", tmp);
        if (w > 0) { g_log_n += (size_t)w; g_log_lines++; }
    }
}
static void die(const char *fmt, ...) { va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); exit(9); }
static unsigned char _mh_execute_header[1];
static const void *g_fake_impl; static unsigned long g_fake_sz;
static const void *getsectiondata(const void *h, const char *a, const char *b, unsigned long *sz) {
    (void)h; (void)a; (void)b; *sz = g_fake_sz; return g_fake_impl;
}
#include "hle_impl_type.inc"
#include "hle_init.inc"

typedef struct mock_cb { uint8_t buf[4096]; size_t n, allocs; } mock_cb;
static uint8_t *rec(NVNcommandBuffer *c, uint32_t op, size_t payload) {
    uint32_t sz = (uint32_t)((8 + payload + 7) & ~(size_t)7);
    uint8_t *p = c->buf + c->n; c->n += sz; c->allocs++;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
#include "hle_adapters.inc"
#include "mtl_barrier.inc"

static char g_mlog[32768]; static size_t g_mlog_n; static int g_mlog_lines;
static void MLOG(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt);
    int n = vsnprintf(g_mlog + g_mlog_n, sizeof g_mlog - g_mlog_n, fmt, ap); va_end(ap);
    if (n > 0) { g_mlog_n += (size_t)n; g_mlog_lines++; if (g_mlog_n < sizeof g_mlog - 1) g_mlog[g_mlog_n++] = '\n'; }
}
static int count_lines(const char *s, const char *needle) {
    int c = 0; const char *p = s;
    while ((p = strstr(p, needle))) { const char *bol = p; while (bol > s && bol[-1] != '\n') bol--; if (!strncmp(bol, needle, strlen(needle))) c++; p++; }
    return c;
}
static struct { int on, valid, closed; char gs_hex[32]; } g_gsres;
#include "mtl_consumer.inc"
#include "mtl_fmt.inc"
static void emit_tail(kdr_record r) {
#include "mtl_emit.inc"
}

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[500] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
}
static const char *TF7[7] = {
    "nvnCommandBufferBindTransformFeedbackBuffer", "nvnCommandBufferBindTransformFeedbackBuffers",
    "nvnCommandBufferBeginTransformFeedback", "nvnCommandBufferEndTransformFeedback",
    "nvnCommandBufferPauseTransformFeedback", "nvnCommandBufferResumeTransformFeedback",
    "nvnCommandBufferDrawTransformFeedback" };
static int slot_of(const char *name) { for (int i = 0; i < NVN_NFUNC; i++) if (nvn_names[i] && !strcmp(nvn_names[i], name)) return i; return -1; }
static int installed_count(void) {
    int n = 0; for (int k = 0; k < 7; k++) { int i = slot_of(TF7[k]); if (i >= 0 && nvn_slot[i].fn != (void *)nvn_unimpl_entry) n++; } return n;
}
static void build_tables(const char *variant) {
    memset(nvn_slot, 0, sizeof nvn_slot);
    for (int i = 0; i < NVN_NFUNC; i++) { nvn_names[i] = ""; nvn_slot[i].fn = (void *)nvn_unimpl_entry; }
    for (int k = 0; k < 7; k++) if (!strcmp(variant, "full") || k != 2) nvn_names[k] = TF7[k];
    nvn_names[10] = "nvnCommandBufferDrawArrays"; nvn_names[11] = "nvnCommandBufferDrawElements";
    nvn_names[12] = "nvnCommandBufferSetRenderTargets";
    static nvn_impl impls[3];
    for (int i = 0; i < 3; i++) { impls[i].name = nvn_names[10 + i]; impls[i].fn = (void *)nvn_unimpl_entry; }
    g_fake_impl = impls; g_fake_sz = sizeof impls;
    if (!strcmp(variant, "occupied")) nvn_slot[slot_of(TF7[5])].fn = (void *)((char *)nvn_unimpl_entry + 1);
}
static kdr_record rec_of(kdr_result r) {
    kdr_record x; memset(&x, 0, sizeof x); x.result = r; x.frame = 5; x.pass = 2;
    x.drawkind = 0; x.prim = 4; x.count = 3; x.instances = 1;
    snprintf(x.vs, sizeof x.vs, "vskey"); snprintf(x.ps, sizeof x.ps, "pskey"); snprintf(x.ps_style, sizeof x.ps_style, "plain");
    return x;
}
static int emit_count(kdr_result res) {
    memset(g_mlog, 0, sizeof g_mlog); g_mlog_n = 0; g_mlog_lines = 0;
    g_gsres.on = 1; g_gsres.valid = 1; g_gsres.closed = 0; snprintf(g_gsres.gs_hex, sizeof g_gsres.gs_hex, "gshex");
    memset(&g_tf_diag, 0, sizeof g_tf_diag); tf_diag_init(&g_tf_diag);
    emit_tail(rec_of(res));
    return count_lines(g_mlog, "[tf-intent] frame=");
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *env = argc > 1 ? argv[1] : "unset";
    const char *variant = argc > 2 ? argv[2] : "full";
    build_tables(variant);
    if (!strcmp(env, "unset")) unsetenv("DM_NVN_TF_DIAG"); else setenv("DM_NVN_TF_DIAG", env, 1);

    int pre = dm_tf_diag_get_mode();
    nvn_init_slots();
    int mode = dm_tf_diag_get_mode();
    int inst = installed_count();
    int want_on = !strcmp(env, "1") && !strcmp(variant, "full");

    ck(pre == TF_DIAG_MODE_OFF, "V5.1", "getter is OFF before the first nvn_init_slots", "pre=%d", pre);
    if (want_on) {
        ck(mode == TF_DIAG_MODE_ON && inst == 7, "V5.1", "requested ON + full table: 7/7 installed then getter ON", "mode=%d inst=%d", mode, inst);
        ck(g_getter_at_success_log == TF_DIAG_MODE_OFF, "V5.1", "getter still OFF while the installer's success log runs (publish happens after)", "seen=%d", g_getter_at_success_log);
    } else if (!strcmp(env, "1")) {
        ck(mode == TF_DIAG_MODE_OFF && inst == 0, "V5.1", "requested ON + missing/occupied name: 0 installed and effective OFF", "mode=%d inst=%d", mode, inst);
        ck(g_getter_at_failure == TF_DIAG_MODE_OFF, "V5.1", "getter is OFF while the failure is logged (no early publish)", "seen=%d", g_getter_at_failure);
        ck(count_lines(g_logbuf, "[tf-intent] diagnostic not enabled") == 1, "V5.1", "failure is logged as 'not enabled, effective mode OFF'", NULL);
        ck(tf_diag_barrier(OP_TF_DIAG) == 0, "V5.1", "barrier does not treat TF as a boundary when effective mode is OFF", NULL);
        ck(emit_count(KDR_HIT) == 0, "V5.3", "same process: failed install -> KDR_HIT emit produces zero tf-intent", NULL);
    } else {
        int want_invalid = !strcmp(env, "01") || !strcmp(env, "2");
        ck(mode == TF_DIAG_MODE_OFF && inst == 0, "V5.1", "absent/empty/0/invalid: OFF, nothing installed", "mode=%d inst=%d", mode, inst);
        ck(count_lines(g_logbuf, "[tf-intent]") == 0, "V5.1", "no install log is added in OFF/INVALID", NULL);
        (void)want_invalid;
    }

    // env change after publish cannot revive the mode
    setenv("DM_NVN_TF_DIAG", "1", 1);
    nvn_init_slots();
    ck(dm_tf_diag_get_mode() == mode && installed_count() == inst, "V5.1", "env change + re-init does not change the published mode/install set", "mode=%d inst=%d", dm_tf_diag_get_mode(), installed_count());

    // V5.3 contrast in the same process: real installer + activate, bypassing only the init `done` guard.
    if (!want_on) {
        build_tables("full");
        int act = tf_diag_activate(TF_DIAG_MODE_ON);   // activate performs the install itself
        ck(act == 1 && dm_tf_diag_get_mode() == TF_DIAG_MODE_ON && installed_count() == 7,
           "V5.3", "same process contrast: a successful install publishes ON and installs 7/7", "act=%d mode=%d inst=%d",
           act, dm_tf_diag_get_mode(), installed_count());
        ck(emit_count(KDR_HIT) == 1, "V5.3", "same process contrast: with ON, KDR_HIT emits exactly one tf-intent", NULL);
    } else {
        ck(emit_count(KDR_HIT) == 1, "V5.3", "successful install path: KDR_HIT emits exactly one tf-intent", NULL);
    }

    // V5.2 truth table: result x mode (ON first, then OFF, then INVALID)
    const kdr_result all[] = { KDR_HIT, KDR_TARGET_NOT_OBTAINED, KDR_NO_GEOMETRY_SOURCE, KDR_IDENTITY_UNAVAILABLE,
                               KDR_GS_KEY_MISMATCH, KDR_INVALID_CONFIG, KDR_DIAG_ERROR };
    const char *nm[] = { "hit", "target-not-obtained", "no-geometry-source", "identity-unavailable", "gs-key-mismatch", "invalid-config", "diagnostic-error" };
    int on_ok = 1;
    for (unsigned i = 0; i < 7; i++) { int c = emit_count(all[i]); int want = (i == 0) ? 1 : 0; if (c != want) { on_ok = 0; printf("  [ON] %s -> %d (want %d)\n", nm[i], c, want); } }
    ck(on_ok, "V5.2", "ON: exactly KDR_HIT emits one tf-intent; the other six emit none", NULL);
    tf_diag_activate(TF_DIAG_MODE_OFF);
    int off_ok = 1;
    for (unsigned i = 0; i < 7; i++) if (emit_count(all[i]) != 0) { off_ok = 0; printf("  [OFF] %s emitted\n", nm[i]); }
    ck(off_ok, "V5.2", "OFF: no result emits a tf-intent (gs-res line still emitted)", NULL);
    tf_diag_activate(TF_DIAG_MODE_INVALID);
    int inv_ok = 1;
    for (unsigned i = 0; i < 7; i++) if (emit_count(all[i]) != 0) { inv_ok = 0; }
    ck(inv_ok, "V5.2", "INVALID: no result emits a tf-intent", NULL);

    // gs-res line / close logic unchanged by the guard
    memset(g_mlog, 0, sizeof g_mlog); g_mlog_n = 0; g_gsres.on = 1; g_gsres.closed = 0; g_gsres.valid = 1;
    emit_tail(rec_of(KDR_HIT));
    ck(count_lines(g_mlog, "[gs-res] result=hit") == 1 && g_gsres.closed == 1, "V5.2", "gs-res line still printed and observer closed once", "closed=%d", g_gsres.closed);

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
