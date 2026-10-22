#!/usr/bin/env python3
"""V3.4: per-body SHA comparison v002 vs v003 -> what may be inherited, what must be retested."""
import hashlib, json, pathlib, re
V2 = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
V3 = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v003/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()

def body(text, sig_regex):
    m = re.search(sig_regex, text)
    if not m: return None
    i = text.index("{", m.start()); depth = 0
    for j in range(i, len(text)):
        if text[j] == "{": depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0: return text[m.start():j + 1]
    return None

FN = {
 "tf_diag_barrier": r"static int tf_diag_barrier\(",
 "ds_scan": r"static int ds_scan\(",
 "hoist_try": r"static void hoist_try\(",
 "fz_next": r"static int fz_next\(",
 "hoist_skipped": r"static int hoist_skipped\(",
 "hoist_take": r"static int hoist_take\(",
 "defer_try": r"static (?:void|int) defer_try\(",
 "sdx_decide": r"static int sdx_decide\(",
 "frz_op": r"static int frz_op\(",
 "fz_prefilter": r"static int fz_prefilter\(",
 "tf_diag_enter": r"static int tf_diag_enter\(",
 "tf_diag_case": r"static void tf_diag_case\(",
}
rows = []
for name, rx in FN.items():
    b2, b3 = body(V2, rx), body(V3, rx)
    h2 = hashlib.sha256(b2.encode()).hexdigest() if b2 else None
    h3 = hashlib.sha256(b3.encode()).hexdigest() if b3 else None
    rows.append({"function": name, "v002_sha": h2, "v003_sha": h3,
                 "same": h2 == h3 and h2 is not None,
                 "inheritable": ("V002-S/V002 evidence for this body" if h2 == h3 and h2 else "must be retested in v003")})
# latch removal checks
checks = [
 ("g_tf_diag_seen removed from v003", "g_tf_diag_seen" not in V3),
 ("fz_prefilter has no seen guard", "g_tf_diag_seen" not in body(V3, r"static int fz_prefilter\(")),
 ("ds TF case is mode-gated", "case OP_TF_DIAG: if (tf_diag_barrier(h.op))" in V3),
 ("hoist TF case is mode-gated", "case OP_TF_DIAG: if (tf_diag_barrier(h.op)) return; break;" in V3),
 ("barrier is a single pure expression", "static int tf_diag_barrier(uint32_t op) { return tf_diag_is_boundary(" in V3),
 ("local barrier call sites remain", len(re.findall(r"tf_diag_barrier\(", V3)) - 1 == 10, str(len(re.findall(r"tf_diag_barrier\(", V3)) - 1) + " sites (8 inherited + 2 new mode gates)"),
]
out = {"rows": rows,
       "checks": [{"name": n, "ok": bool(o), "detail": d} for n, o, d in
                  [(c[0], c[1], (c[2] if len(c) > 2 else "ok")) for c in checks]],
       "pass": None, "fail": None}
out["pass"] = sum(r["same"] for r in rows[:])  # not a pass/fail metric; kept for structure
json.dump(out, open("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v003/validator/logs/inheritance.json", "w"), indent=2)
for r in rows:
    print(("SAME " if r["same"] else "DIFF "), r["function"], r["v003_sha"][:12] if r["v003_sha"] else "-", "|", r["inheritable"])
for c in out["checks"]:
    print(("OK   " if c["ok"] else "FAIL "), c["name"], c["detail"])
