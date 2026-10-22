// D01/D02/D03: startup-fixed mode, conditional all-or-none install, adapters.
// hle_init.inc / hle_impl_type.inc / hle_adapters.inc are verbatim v004 bodies.
// The verifier supplies the slot table, name table, section stub, LOG and the command buffer.
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#include "nvn_tf_diag.h"
#include "ops.inc"

#define NVN_NFUNC 32
typedef struct { _Atomic uint64_t cnt; void *fn; } nvn_slot_t;
static nvn_slot_t nvn_slot[NVN_NFUNC];
static const char *nvn_names[NVN_NFUNC];
static void nvn_unimpl_entry(void) {}

static char g_logbuf[8192]; static size_t g_log_n;
static void LOG(const char *fmt, ...) {
    va_list ap; va_start(ap, fmt); int n = vsnprintf(g_logbuf + g_log_n, sizeof g_logbuf - g_log_n, fmt, ap); va_end(ap);
    if (n > 0) g_log_n += (size_t)n; if (g_log_n < sizeof g_logbuf - 1) g_logbuf[g_log_n++] = '\n';
}
static void die(const char *fmt, ...) { va_list ap; va_start(ap, fmt); vfprintf(stderr, fmt, ap); va_end(ap); exit(9); }
static unsigned char _mh_execute_header[1];
static const void *g_fake_impl; static unsigned long g_fake_sz;
static const void *getsectiondata(const void *h, const char *s1, const char *s2, unsigned long *sz) {
    (void)h; (void)s1; (void)s2; *sz = g_fake_sz; return g_fake_impl;
}

// adapter prototypes (also declared by the extracted hle_init block)
typedef struct mock_cb NVNcommandBuffer;
typedef uint64_t NVNbufferAddress;
typedef int NVNdrawPrimitive;
typedef struct { uint64_t addr, size; } NVNbufferRange;

#include "hle_impl_type.inc"
#include "hle_init.inc"

typedef struct mock_cb { uint8_t buf[8192]; size_t n, allocs; } mock_cb;
static void *rec(NVNcommandBuffer *c, uint32_t op, size_t payload) {
    uint32_t sz = (uint32_t)((8 + payload + 7) & ~(size_t)7);
    uint8_t *p = c->buf + c->n; c->n += sz; c->allocs++;
    ((op_hdr *)p)->op = op; ((op_hdr *)p)->size = sz;
    memset(p + 8, 0, sz - 8);
    return p + 8;
}
#include "hle_adapters.inc"

static int g_pass, g_fail;
static void ck(int c, const char *id, const char *name, const char *fmt, ...) {
    char d[400] = ""; if (fmt) { va_list ap; va_start(ap, fmt); vsnprintf(d, sizeof d, fmt, ap); va_end(ap); }
    if (c) { g_pass++; printf("PASS %s %s\n", id, name); } else { g_fail++; printf("FAIL %s %s | %s\n", id, name, d); }
}

static const char *TF7[7] = {
    "nvnCommandBufferBindTransformFeedbackBuffer", "nvnCommandBufferBindTransformFeedbackBuffers",
    "nvnCommandBufferBeginTransformFeedback", "nvnCommandBufferEndTransformFeedback",
    "nvnCommandBufferPauseTransformFeedback", "nvnCommandBufferResumeTransformFeedback",
    "nvnCommandBufferDrawTransformFeedback" };
static int slot_of(const char *name) { for (int i = 0; i < NVN_NFUNC; i++) if (nvn_names[i] && !strcmp(nvn_names[i], name)) return i; return -1; }

// build the tables: 7 TF names + 3 "implemented" APIs
static void build_tables(const char *variant) {
    memset(nvn_slot, 0, sizeof nvn_slot);
    for (int i = 0; i < NVN_NFUNC; i++) nvn_names[i] = "";
    for (int i = 0; i < NVN_NFUNC; i++) nvn_slot[i].fn = (void *)nvn_unimpl_entry;
    for (int k = 0; k < 7; k++) if (!strcmp(variant, "full") || k != 2) nvn_names[k] = TF7[k];
    nvn_names[10] = "nvnCommandBufferDrawArrays"; nvn_names[11] = "nvnCommandBufferDrawElements";
    nvn_names[12] = "nvnCommandBufferSetRenderTargets";
    static nvn_impl impls[3];
    impls[0].name = nvn_names[10]; impls[0].fn = (void *)nvn_unimpl_entry;
    impls[1].name = nvn_names[11]; impls[1].fn = (void *)nvn_unimpl_entry;
    impls[2].name = nvn_names[12]; impls[2].fn = (void *)nvn_unimpl_entry;
    g_fake_impl = impls; g_fake_sz = sizeof impls;   // 3 semantic impls -> g_nsem must stay 3
    if (!strcmp(variant, "occupied")) nvn_slot[slot_of(TF7[5])].fn = (void *)nvn_unimpl_entry + 1;   // one name already taken
}

int main(int argc, char **argv) {
    setvbuf(stdout, NULL, _IONBF, 0);
    const char *env = argc > 1 ? argv[1] : "unset";
    const char *variant = argc > 2 ? argv[2] : "full";
    build_tables(variant);
    if (!strcmp(env, "unset")) unsetenv("DM_NVN_TF_DIAG"); else setenv("DM_NVN_TF_DIAG", env, 1);

    int pre = dm_tf_diag_get_mode();
    ck(pre == TF_DIAG_MODE_OFF, "D01", "before the first nvn_init_slots the getter reports OFF", "pre=%d", pre);

    nvn_init_slots();
    int mode = dm_tf_diag_get_mode();
    int installed = 0;
    for (int k = 0; k < 7; k++) { int i = slot_of(TF7[k]); if (i >= 0 && nvn_slot[i].fn != (void *)nvn_unimpl_entry) installed++; }

    if (!strcmp(env, "1")) {
        int want_inst = !strcmp(variant, "full") ? 7 : 0;   // missing/occupied name: all-or-none, nothing installed
        ck(mode == TF_DIAG_MODE_ON && installed == want_inst, "D01",
           want_inst ? "mode \"1\" + full table: ON and all 7 slots installed"
                     : "mode \"1\" + missing/occupied name: ON but 0 installed (all-or-none, no partial)",
           "mode=%d installed=%d want=%d", mode, installed, want_inst);
    } else {
        int want = (!strcmp(env, "unset") || !*env || !strcmp(env, "0")) ? TF_DIAG_MODE_OFF : TF_DIAG_MODE_INVALID;
        ck(mode == want && installed == 0, "D01", "absent/empty/0 -> OFF, other -> INVALID; never installs", "mode=%d want=%d installed=%d", mode, want, installed);
    }

    // immutable: changing the environment afterwards and re-entering init changes nothing
    setenv("DM_NVN_TF_DIAG", "1", 1);
    nvn_init_slots();
    ck(dm_tf_diag_get_mode() == mode, "D01", "later env change + re-init does not change the fixed mode", "now=%d before=%d", dm_tf_diag_get_mode(), mode);
    int installed2 = 0;
    for (int k = 0; k < 7; k++) { int i = slot_of(TF7[k]); if (i >= 0 && nvn_slot[i].fn != (void *)nvn_unimpl_entry) installed2++; }
    ck(installed2 == installed, "D01", "re-init is a no-op (static done) for the install set", "%d -> %d", installed, installed2);

    // D02: other slots / counters untouched by the install
    int others_ok = 1;
    for (int i = 0; i < NVN_NFUNC; i++) {
        int is_tf = 0; for (int k = 0; k < 7; k++) if (nvn_names[i] && !strcmp(nvn_names[i], TF7[k])) is_tf = 1;
        if (!is_tf && nvn_slot[i].fn != (void *)nvn_unimpl_entry) others_ok = 0;
    }
    ck(others_ok, "D02", "no non-TF slot is replaced", NULL);

    // D03: adapters record 40B, plural never dereferences ranges, OFF writes nothing
    mock_cb cb; memset(&cb, 0, sizeof cb);
    dm_tf_diag_bind(&cb, 0, 0x1000, 0x80);
    if (mode == TF_DIAG_MODE_ON) {
        ck(cb.n == 40 && ((op_hdr *)cb.buf)->op == OP_TF_DIAG && ((op_hdr *)cb.buf)->size == 40,
           "D03", "ON: Bind adapter records one 40-byte OP_TF_DIAG", "n=%zu", cb.n);
    } else {
        ck(cb.n == 0 && cb.allocs == 0, "D03", "OFF/INVALID: adapter is inert (no bytes, no alloc)", "n=%zu", cb.n);
    }
    ck(g_nsem == 3, "D02", "g_nsem stays the number of semantic implementations (3), untouched by the install", "g_nsem=%u", g_nsem);
    // plural adapter must not dereference the caller ranges (PROT_NONE page) in any mode
    { void *np = mmap(NULL, (size_t)sysconf(_SC_PAGESIZE), PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      mock_cb pb; memset(&pb, 0, sizeof pb);
      dm_tf_diag_bind_plural(&pb, 2, 3, (const NVNbufferRange *)np);
      int ok = (mode == TF_DIAG_MODE_ON) ? (pb.n == 40 && ((p_tf_diag *)(pb.buf + 8))->addr == 0 &&
                                            ((p_tf_diag *)(pb.buf + 8))->size == 0 &&
                                            ((p_tf_diag *)(pb.buf + 8))->index == 2 &&
                                            ((p_tf_diag *)(pb.buf + 8))->count == 3)
                                          : (pb.n == 0);
      ck(ok, "D03", "plural adapter never dereferences the caller ranges (PROT_NONE) and writes first/count only", "n=%zu", pb.n);
      munmap(np, (size_t)sysconf(_SC_PAGESIZE)); }

    printf("RESULT pass=%d fail=%d\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
