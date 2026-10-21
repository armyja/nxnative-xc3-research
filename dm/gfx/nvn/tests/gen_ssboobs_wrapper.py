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
static int log_count, fmt_calls, fail_at = 0x7fffffff;
#define MLOG(...) do { log_count++; printf("LOG " __VA_ARGS__); printf("\n"); } while (0)
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
static unsigned char g_keys[6][8]; static unsigned char g_known[6];
static int prog_key_cached(const prog_t *p, unsigned i, unsigned char k[8]) {
    (void)p; if (i >= 6 || !g_known[i]) return 0; memcpy(k, g_keys[i], 8); return 1;
}
'''
main = r'''
static int fails;
#define CK(c, m) do { if (!(c)) { printf("FAIL %s\n", m); fails++; } else printf("ok   %s\n", m); } while (0)
static prog_t P; static unsigned char T[8] = {0x4b,0xae,0x5b,0x8a,0xbd,0x3b,0xec,0x7f};
static void reset(int mode, unsigned nstage) {
    memset(&g_so, 0, sizeof g_so); memset(&S, 0, sizeof S); memset(&P, 0, sizeof P);
    memset(g_known, 0, sizeof g_known); memset(g_keys, 0, sizeof g_keys);
    g_so.mode = mode; memcpy(g_so.key, T, 8); P.nstage = nstage; S.bst[0] = &P;
    log_count = fmt_calls = 0; fail_at = 0x7fffffff;
}
int main(void) {
    unsetenv("DM_NVN_SSBO_OBS");
    memset(&g_so, 0, sizeof g_so); ssbo_obs_arm(); ssbo_obs_arm();
    CK(g_so.mode == 2, "absent switch latches closed");
    ssbo_obs_draw(); ssbo_obs_draw_skipped(); ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 2});
    CK(log_count == 0 && g_so.unknown == 0 && g_so.invalid == 0 && g_so.skips == 0 && g_so.obs_seq == 0, "off: no log, no counter, no key query");

    memset(&g_so, 0, sizeof g_so); setenv("DM_NVN_SSBO_OBS", "zzzz", 1); ssbo_obs_arm();
    CK(g_so.mode == 2 && log_count == 1, "invalid value latches closed with exactly one log");
    log_count = 0; ssbo_obs_arm(); CK(log_count == 0, "second arm after close does not re-log");

    reset(1, 1); g_cur_frame = 7; ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 2});
    CK(g_so.lb[0].known && g_so.lb[0].frame == 7 && g_so.lb[0].seq == 1, "real vertex bind recorded with frame and seq");
    ssbo_obs_bind(&(p_bind_buf){1, 0, 1, 1}); ssbo_obs_bind(&(p_bind_buf){0, 16, 1, 1});
    CK(g_so.lb[0].seq == 1, "foreign stage and index 16 do not touch the vertex table");

    reset(1, 1); for (int i = 0; i < 600; i++) ssbo_obs_draw();
    CK(log_count == 1 && g_so.unknown == 600, "unknown: one log per run, counter saturates past 512");
    reset(1, 7); for (int i = 0; i < 600; i++) ssbo_obs_draw();
    CK(log_count == 1 && g_so.invalid == 600, "invalid nstage: one log per run, counter past 512");

    reset(1, 1); g_known[0] = 1; memcpy(g_keys[0], T, 8);
    ssbo_obs_draw_skipped();
    CK(g_so.skips == 1 && g_so.mode == 1 && log_count == 1, "target skip: counted once, logged once, still armed");
    ssbo_obs_draw();
    CK(g_so.mode == 2 && g_so.done == 1, "target skip keeps the observation armed; the later draw still completes");

    reset(1, 2); g_known[0] = 1; memcpy(g_keys[0], T, 8);
    ssbo_obs_draw(); CK(g_so.mode == 2 && g_so.done == 1, "hit with another entry unknown still completes");

    reset(1, 2); g_known[0] = 1; memset(g_keys[0], 0x11, 8); g_known[1] = 0;
    ssbo_obs_draw(); CK(g_so.done == 0 && g_so.unknown == 1, "partial cache without hit is identity-unknown, not absent");

    reset(1, 1); g_known[0] = 1; memcpy(g_keys[0], T, 8);
    ssbo_obs_draw(); int after = log_count;
    ssbo_obs_draw(); ssbo_obs_draw_skipped(); ssbo_obs_bind(&(p_bind_buf){0, 0, 1, 1});
    CK(g_so.done == 1 && g_so.skips == 0 && g_so.lb[0].known == 0 && log_count == after, "after one-shot: silent and inert");

    reset(1, 7); ssbo_obs_draw(); CK(g_so.rep_invalid == 1, "invalid count reported first");
    P.nstage = 1; g_known[0] = 1; memcpy(g_keys[0], T, 8); fail_at = 0;
    ssbo_obs_draw(); CK(g_so.mode == 2 && g_so.done == 0 && g_so.rep_invalid == 1, "format failure after an invalid report still closes without done");

    reset(1, 1); g_known[0] = 1; memcpy(g_keys[0], T, 8);
    S.ssbo[0][15].addr = 0xffffffffffffffffull; S.ssbo[0][15].size = 0xffffffffffffffffull;
    ssbo_obs_draw(); CK(g_so.done == 1, "worst-case 64-bit slot still completes");
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
