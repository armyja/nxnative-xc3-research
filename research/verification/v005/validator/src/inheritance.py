#!/usr/bin/env python3
"""V5.4: body-SHA comparison v004 -> v005 (not whole files)."""
import hashlib, json, pathlib, re
W = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification")
def txt(v): return (W/f"{v}/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
def hle(v): return (W/f"{v}/candidate/dm/gfx/nvn/hle_nvn.c").read_text()
V4, V5 = txt("v004"), txt("v005"); H4, H5 = hle("v004"), hle("v005")
def body(t, rx):
    m = re.search(rx, t)
    if not m: return None
    i = t.index("{", m.start()); d = 0
    for j in range(i, len(t)):
        d += {"{": 1, "}": -1}.get(t[j], 0)
        if d == 0: return t[m.start():j+1]
FN = [("tf_diag_barrier", r"static int tf_diag_barrier\("), ("ds_scan", r"static int ds_scan\("),
      ("hoist_try", r"static void hoist_try\("), ("fz_next", r"static int fz_next\("),
      ("defer_try", r"static (?:void|int) defer_try\("), ("sdx_decide", r"static int sdx_decide\("),
      ("frz_op", r"static int frz_op\("), ("fz_prefilter", r"static int fz_prefilter\("),
      ("tf_diag_enter", r"static int tf_diag_enter\("), ("tf_diag_case", r"static void tf_diag_case\("),
      ("kd_tf_intent_line", r"static int kd_tf_intent_line\(")]
rows = []
for name, rx in FN:
    b4, b5 = body(V4, rx), body(V5, rx)
    h4 = hashlib.sha256(b4.encode()).hexdigest() if b4 else None
    h5 = hashlib.sha256(b5.encode()).hexdigest() if b5 else None
    rows.append({"function": name, "v004_sha": h4, "v005_sha": h5, "same": h4 == h5 and h4 is not None,
                 "disposition": "inherit V004 evidence" if h4 == h5 and h4 else "re-verify / new"})
HLE = [("nvn_init_slots", r"static void nvn_init_slots\("), ("tf_diag_install_adapters", r"static int tf_diag_install_adapters\("),
       ("tf_diag_activate", r"static int tf_diag_activate\("), ("tf_diag_emit", r"static void tf_diag_emit\(")]
hrows = []
for name, rx in HLE:
    b4, b5 = body(H4, rx), body(H5, rx)
    h4 = hashlib.sha256(b4.encode()).hexdigest() if b4 else None
    h5 = hashlib.sha256(b5.encode()).hexdigest() if b5 else None
    hrows.append({"function": name, "v004_sha": h4, "v005_sha": h5, "same": h4 == h5 and h4 is not None})
checks = [
 ("installer returns int", "static int tf_diag_install_adapters(void)" in H5),
 ("activate publishes only after install", "if (requested == TF_DIAG_MODE_ON) ok = tf_diag_install_adapters();" in H5 and
  "g_tf_diag_mode = ok ? TF_DIAG_MODE_ON : TF_DIAG_MODE_OFF;" in H5),
 ("failure keeps fixed mode OFF", "if (requested == TF_DIAG_MODE_ON && !ok)" in H5),
 ("init calls activate once", H5.count("tf_diag_activate(tf_requested)") == 1),
 ("explicit HIT guard exists", "r->result == KDR_HIT && tf_diag_on()" in V5),
 ("shared emit uses the guard", "if (kd_tf_intent_wanted(&r))" in V5),
]
out = {"mtl": rows, "hle": hrows, "checks": [{"name": n, "ok": bool(o)} for n, o in checks]}
json.dump(out, open(W/"v005/validator/logs/inheritance.json", "w"), indent=2)
for r in rows: print(("SAME " if r["same"] else "DIFF "), r["function"], "|", r["disposition"])
for r in hrows: print(("SAME " if r["same"] else "DIFF "), "hle:" + r["function"])
for c in out["checks"]: print(("OK   " if c["ok"] else "FAIL "), c["name"])
