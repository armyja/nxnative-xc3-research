#!/usr/bin/env python3
"""D06/body-SHA inheritance: compare actual function bodies v003 -> v004, not whole files."""
import hashlib, json, pathlib, re
W = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification")
V3 = (W/"v003/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
V4 = (W/"v004/candidate/dm/gfx/nvn/nvn_mtl.m").read_text()
H3 = (W/"v003/candidate/dm/gfx/nvn/hle_nvn.c").read_text()
H4 = (W/"v004/candidate/dm/gfx/nvn/hle_nvn.c").read_text()
def body(text, rx):
    m = re.search(rx, text); 
    if not m: return None
    i = text.index("{", m.start()); d = 0
    for j in range(i, len(text)):
        d += {"{": 1, "}": -1}.get(text[j], 0)
        if d == 0: return text[m.start():j+1]
FN = [("tf_diag_barrier", r"static int tf_diag_barrier\("), ("ds_scan", r"static int ds_scan\("),
      ("hoist_try", r"static void hoist_try\("), ("fz_next", r"static int fz_next\("),
      ("hoist_skipped", r"static int hoist_skipped\("), ("hoist_take", r"static int hoist_take\("),
      ("defer_try", r"static (?:void|int) defer_try\("), ("sdx_decide", r"static int sdx_decide\("),
      ("frz_op", r"static int frz_op\("), ("fz_prefilter", r"static int fz_prefilter\("),
      ("tf_diag_enter", r"static int tf_diag_enter\("), ("tf_diag_case", r"static void tf_diag_case\(")]
rows = []
for name, rx in FN:
    b3, b4 = body(V3, rx), body(V4, rx)
    h3 = hashlib.sha256(b3.encode()).hexdigest() if b3 else None
    h4 = hashlib.sha256(b4.encode()).hexdigest() if b4 else None
    rows.append({"function": name, "v003_sha": h3, "v004_sha": h4, "same": h3 == h4 and h3 is not None,
                 "disposition": "inherit V002/V003 evidence" if h3 == h4 and h3 else "re-verify if touched by D-scope"})
# hle adapters + init
def hle_init(t):
    return body(t, r"static void nvn_init_slots\(")
def hle_inst(t):
    return body(t, r"static void tf_diag_install_adapters\(")
adapters = {}
for name in ("tf_diag_emit",):
    b3, b4 = body(H3, r"static void " + name + r"\("), body(H4, r"static void " + name + r"\(")
    adapters[name] = {"same": b3 == b4, "v004_sha": hashlib.sha256((b4 or "").encode()).hexdigest()}
out = {"rows": rows, "hle": {"nvn_init_slots": {"v003": hashlib.sha256((hle_init(H3) or "").encode()).hexdigest(),
                                                "v004": hashlib.sha256((hle_init(H4) or "").encode()).hexdigest()},
                            "tf_diag_install_adapters": {"v003": None,
                                                         "v004": hashlib.sha256((hle_inst(H4) or "").encode()).hexdigest()},
                            "tf_diag_emit": adapters["tf_diag_emit"]}}
# static facts for D04/D02
checks = [
 ("observer early-return precedes the emit path", "if (!g_gsres.on || g_gsres.closed) return;" in V4),
 ("observer has no installed/partial state to consult", "tf_diag_installed" not in V4 and "g_tf_diag_installed" not in V4),
 ("exactly one tf-intent call site", V4.count("kd_tf_intent_line(") == 2),
 ("tf-intent is gated only by tf_diag_on()", "if (tf_diag_on()) {" in V4 and "r.result" not in V4.split("if (tf_diag_on())")[1][:200]),
 ("no runtime setter remains in hle", "dm_tf_diag_set_mode" not in H4),
 ("mode fixed exactly once in nvn_init_slots", H4.count("g_tf_diag_mode_fixed = 1;") == 1),
]
out["checks"] = [{"name": n, "ok": bool(o)} for n, o in checks]
json.dump(out, open(W/"v004/validator/logs/inheritance.json", "w"), indent=2)
for r in rows: print(("SAME " if r["same"] else "DIFF "), r["function"], "|", r["disposition"])
for c in out["checks"]: print(("OK   " if c["ok"] else "FAIL "), c["name"])
print("hle init changed:", out["hle"]["nvn_init_slots"]["v003"] != out["hle"]["nvn_init_slots"]["v004"])
