#!/usr/bin/env python3
"""Extract the production DM_NVN_SSBO_OBS block from nvn_mtl.m and drive it with stubs (no guest, no Metal).

The extracted text is the real arm/identity/skip/draw code; only the environment it assumes (prog_t, S, the key cache,
MLOG, the frame/pass counters) is stubbed. This tests the wrapper, not the renderer.
"""
import os, subprocess, sys, tempfile, textwrap
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'nvn_mtl.m')
HDR = os.path.join(HERE, '..', 'nvn_ssboobs.h')
src = open(SRC).read()
a = src.index('static ssbo_obs_state g_so;')
b = src.index('void mtl_exec(const uint8_t *p) {')
body = src[a:b]

prelude = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include "nvn_ssboobs.h"
static int log_count, err_logs, done_logs, skip_logs, fmt_calls, fail_at = 0x7fffffff;
static void mlog(const char *f, ...) { char b[1024]; va_list ap; va_start(ap, f); vsnprintf(b, sizeof b, f, ap); va_end(ap);
    log_count++; if (strstr(b, "diagnostic-error")) err_logs++; if (strstr(b, "done key=")) done_logs++;
    if (strstr(b, "known-skipped")) skip_logs++; printf("LOG %s\n", b); }
#define MLOG(...) mlog(__VA_ARGS__)
static int test_snprintf(char *b, size_t n, const char *f, ...) {
    if (++fmt_calls > fail_at) return -1;
    va_list ap; va_start(ap, f);
    int r = vsnprintf(b, n, f, ap);
    va_end(ap);
    return r;
}
#define snprintf(b, n, ...) test_snprintf((b), (n), __VA_ARGS__)
typedef struct { int nstage; unsigned char sd[6][24]; } prog_t;
typedef struct { unsigned stage, index; uint64_t addr, size; } p_bind_buf;
static struct { prog_t *bst[5]; p_bind_buf ssbo[6][16]; } S;
static uint64_t g_cur_frame, g_stat_pass;
static uint64_t atomic_load(const uint64_t *p) { return *p; }
static unsigned char g_keys[6][8]; static unsigned char g_known[6]; static int cache_q;
static int prog_key_cached(const prog_t *p, unsigned i, unsigned char k[8]) {
    cache_q++; (void)p; if (i >= 6 || !g_known[i]) return 0; memcpy(k, g_keys[i], 8); return 1;
}
'''
main = r'''
static int fails;
#define CK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok   %s\n", m); } while (0)
static prog_t P; static unsigned char T[8] = {0x4b,0xae,0x5b,0x8a,0xbd,0x3b,0xec,0x7f};
static ssbo_obs_state gs0;
static void reset(int mode, unsigned nstage) {
    memset(&g_so, 0, sizeof g_so); memset(&S, 0, sizeof S); memset(&P, 0, sizeof P);
    memset(g_known, 0, sizeof g_known); memset(g_keys, 0, sizeof g_keys);
    g_so.mode = mode; memcpy(g_so.key, T, 8); P.nstage = nstage; S.bst[0] = &P;
    log_count = err_logs = done_logs = skip_logs = fmt_calls = cache_q = 0; fail_at = 0x7fffffff;
}
static void target_at(int i) { g_known[i] = 1; memcpy(g_keys[i], T, 8); }
static void snap(void) { memcpy(&gs0, &g_so, sizeof gs0); }
static int unchanged(void) { return memcmp(&gs0, &g_so, sizeof gs0) == 0; }
int main(void) {
    unsetenv("DM_NVN_SSBO_OBS");
    memset(&g_so, 0, sizeof g_so); ssbo_obs_arm(); ssbo_obs_arm();
    CK(g_so.mode == 2, "absent switch latches closed");
    reset(0, 1); target_at(0); snap();
    ssbo_obs_draw(); ssbo_obs_draw_skipped(); ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 2});
    CK(log_count == 0 && cache_q == 0 && unchanged(), "off with a matchable program: no log, no key query, state untouched");

    memset(&g_so, 0, sizeof g_so); setenv("DM_NVN_PSOFAIL_RT", "", 1); setenv("DM_NVN_SSBO_OBS", "zzzz", 1);
    ssbo_obs_arm(); CK(g_so.mode == 2 && log_count == 1 && err_logs == 0, "invalid value latches closed with exactly one log");
    log_count = 0; ssbo_obs_arm(); CK(log_count == 0, "second arm after close does not re-log");
    reset(2, 1); target_at(0); snap();
    ssbo_obs_draw(); ssbo_obs_draw_skipped(); ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 2});
    CK(log_count == 0 && cache_q == 0 && unchanged(), "closed state: all three entry points inert");

    reset(1, 1); target_at(0); g_cur_frame = 7; ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 2});
    CK(g_so.lb[0].known && g_so.lb[0].frame == 7 && g_so.lb[0].seq == 1, "real vertex bind recorded with frame and seq");
    ssbo_obs_bind(&(p_bind_buf){1, 0, 1, 1}); ssbo_obs_bind(&(p_bind_buf){0, 16, 1, 1});
    CK(g_so.lb[0].seq == 1, "foreign stage and index 16 do not touch the vertex table");

    reset(1, 1); g_known[0] = 0; cache_q = 0;
    ssbo_obs_draw(); CK(log_count == 1 && cache_q == 1 && g_so.unknown == 1, "unknown: one query, one log");
    for (int i = 0; i < 600; i++) ssbo_obs_draw();
    CK(log_count == 1 && g_so.unknown == 601, "unknown repeated: still one log, counter grows");
    reset(1, 7); ssbo_obs_draw(); for (int i = 0; i < 600; i++) ssbo_obs_draw();
    CK(log_count == 1 && g_so.invalid == 601, "invalid repeated: one log, counter grows");

    reset(1, 1); target_at(0); for (int i = 0; i < 513; i++) ssbo_obs_draw_skipped();
    CK(skip_logs == 1 && g_so.skips == 513 && g_so.mode == 1, "target skip 513x: one log, exact count, still armed");
    ssbo_obs_draw(); CK(g_so.mode == 2 && done_logs == 1, "target skip keeps armed and the later draw completes");
    reset(1, 1); g_known[0] = 0; ssbo_obs_draw_skipped();
    CK(g_so.skips == 0 && g_so.unknown == 1 && skip_logs == 0, "unknown identity is not counted as a skipped target");

    reset(1, 1); target_at(0); g_so.skips = UINT64_MAX - 1;
    ssbo_obs_draw_skipped(); ssbo_obs_draw_skipped(); CK(g_so.skips == UINT64_MAX, "skip counter saturates at UINT64_MAX");
    reset(1, 1); g_known[0] = 0; g_so.unknown = UINT64_MAX - 1;
    ssbo_obs_draw(); ssbo_obs_draw(); CK(g_so.unknown == UINT64_MAX, "unknown counter saturates at UINT64_MAX");
    reset(1, 7); g_so.invalid = UINT64_MAX - 1;
    ssbo_obs_draw(); ssbo_obs_draw(); CK(g_so.invalid == UINT64_MAX, "invalid counter saturates at UINT64_MAX");

    for (int k = 0; k < 3; k++) {
        reset(1, 1); target_at(0); fail_at = k;   // 0: key list, 1: header, 2: first slot (n == 1)
        ssbo_obs_draw();
        CK(g_so.mode == 2 && done_logs == 0 && err_logs == 1 && g_so.done == 0, k == 0 ? "format failure (key list): one error, no done, closed" : k == 1 ? "format failure (header): one error, no done, closed" : "format failure (slot): one error, no done, closed");
    }

    reset(1, 1); target_at(0); g_cur_frame = UINT64_MAX;
    S.ssbo[0][15].addr = UINT64_MAX; S.ssbo[0][15].size = UINT64_MAX;
    ssbo_obs_draw(); CK(g_so.done == 1 && err_logs == 0, "worst-case addr/size/frame still completes");

    reset(1, 1); target_at(0);
    ssbo_obs_draw(); int after = log_count;
    ssbo_obs_draw(); ssbo_obs_draw_skipped(); ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 1});
    CK(g_so.done == 1 && log_count == after && g_so.skips == 0, "after one-shot: silent and inert");
    printf("fails: %s\n", fails ? "yes" : "none");
    return fails ? 1 : 0;
}
'''
out = os.environ.get('SSBOOBS_OUT') or tempfile.mkdtemp(prefix='ssboobs_')
os.makedirs(out, exist_ok=True)
c = os.path.join(out, 't_wrapper.c')
open(c, 'w').write(prelude + body + main)
r = subprocess.run(['clang', '-O1', '-Wall', '-Wextra', '-I', os.path.dirname(HDR), '-fsanitize=address,undefined', '-o', os.path.join(out, 't_wrapper'), c], capture_output=True, text=True)
print('out dir:', out)
print(r.stderr[-1500:] if r.returncode else 'compiled')
if r.returncode: sys.exit(1)
run = subprocess.run([os.path.join(out, 't_wrapper')], capture_output=True, text=True)
print(run.stdout)
ok = run.returncode == 0 and 'diagnostic-error' in run.stdout and 'done key=4bae5b8abd3bec7f' in run.stdout
sys.exit(0 if ok else 1)
