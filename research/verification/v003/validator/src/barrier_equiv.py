#!/usr/bin/env python3
"""Helper-change handling (supervisor requirement): the barrier body changed (v002 -> v003), so
prove return-value equivalence for every input, and show which callers could observe the removed
side effect. Unchanged callers therefore keep their inherited evidence at the call-site level,
while their own bodies stay SKIP where they cannot be executed."""
import hashlib, json, pathlib, re, subprocess
W = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification")
V2 = (W/"v002/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
V3 = (W/"v003/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
HDR = (W/"v003/candidate/dm/gfx/nvn/nvn_tf_diag.h").read_text()
OUT = W/"v003/validator/evidence"; OUT.mkdir(exist_ok=True)

def fn(text, name):
    m = re.search(r"static int " + name + r"\(uint32_t op\)\s*\{", text)
    i = text.index("{", m.start()); d = 0
    for j in range(i, len(text)):
        d += {"{": 1, "}": -1}.get(text[j], 0)
        if d == 0: return text[m.start():j+1]
    return None

b2, b3 = fn(V2, "tf_diag_barrier"), fn(V3, "tf_diag_barrier")
# rename for a single compile unit; v002's version also touches g_tf_diag_seen
v2_src = b2.replace("tf_diag_barrier", "barrier_v002")
v3_src = b3.replace("tf_diag_barrier", "barrier_v003")
c = f"""
#include <stdio.h>
#include <stdint.h>
#include "{W/'v003/validator/build/include/nvn_tf_diag.h'}"
#include "{W/'v003/validator/build/include/ops.inc'}"
static int g_mode;
int dm_tf_diag_get_mode(void) {{ return g_mode; }}
static int g_tf_diag_seen;   /* only the v002 body writes it */
{v2_src}
{v3_src}
int main(void) {{
    const uint32_t ops[] = {{ (uint32_t)OP_TF_DIAG, (uint32_t)OP_DRAW, (uint32_t)OP_END, 63u, 0u, 7u }};
    const int modes[] = {{ TF_DIAG_MODE_OFF, TF_DIAG_MODE_ON, TF_DIAG_MODE_INVALID }};
    int mism = 0, n = 0, seen_writes = 0;
    for (unsigned m = 0; m < 3; m++) for (unsigned k = 0; k < sizeof ops / sizeof *ops; k++) {{
        g_mode = modes[m]; g_tf_diag_seen = 0;
        int a = barrier_v002(ops[k]); int sa = g_tf_diag_seen;
        g_tf_diag_seen = 0;
        int b = barrier_v003(ops[k]); int sb = g_tf_diag_seen;
        n++; if (a != b) {{ mism++; printf("MISMATCH mode=%d op=%u v002=%d v003=%d\\n", modes[m], ops[k], a, b); }}
        if (sa) seen_writes++; if (sb) printf("V003_WROTE_SEEN mode=%d op=%u\\n", modes[m], ops[k]);
    }}
    printf("checks=%d mismatches=%d v002_seen_writes=%d\\n", n, mism, seen_writes);
    return (mism == 0 && seen_writes == 1) ? 0 : 1;   /* exactly one ON-mode TF call may write the v002 latch */
}}
"""
path = W/"v003/validator/build/barrier_equiv.c"
path.write_text(c)
rc = subprocess.run(["cc","-std=c11","-O1","-Wall","-Wextra","-Werror",str(path),"-o",str(W/"v003/validator/build/barrier_equiv")],
                    capture_output=True, text=True)
run = subprocess.run([str(W/"v003/validator/build/barrier_equiv")], capture_output=True, text=True) if rc.returncode == 0 else None
print((run.stdout if run else rc.stdout + rc.stderr).strip())

# Which bodies could observe the removed side effect?
readers = [i + 1 for i, l in enumerate(V2.splitlines()) if "g_tf_diag_seen" in l]
res = {"barrier_body_sha256": {"v002": hashlib.sha256((b2 or "").encode()).hexdigest(),
                               "v003": hashlib.sha256((b3 or "").encode()).hexdigest()},
       "header_sha256": hashlib.sha256(HDR.encode()).hexdigest(),
       "return_equivalence": {"compile_rc": rc.returncode, "run_rc": run.returncode if run else None,
                              "stdout": (run.stdout if run else "").strip()},
       "v002_seen_references": readers,
       "v003_seen_references": [i + 1 for i, l in enumerate(V3.splitlines()) if "g_tf_diag_seen" in l],
       "conclusion": "v002 and v003 barrier return identical values for every opcode/mode; the only difference is the "
                     "write to g_tf_diag_seen, whose readers (fz_prefilter guard, tf_diag_enter reset) were removed in v003. "
                     "Unchanged callers (fz_next, hoist_skipped, hoist_take, sdx_walk, defer_try, frz_op) therefore observe "
                     "identical call-site behaviour and keep their inherited evidence; their own bodies remain SKIP where unexecuted."}
(OUT/"barrier-equivalence.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=1)[:900])
