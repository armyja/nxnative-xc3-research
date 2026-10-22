#!/usr/bin/env python3
"""S03: does any fz_next() caller treat FALSE (boundary/absent cursor) as a normal end-of-stream
success? Classify all call sites and the merge-acceptance points by source path."""
import json, pathlib, re
N = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate/dm/gfx/nvn/nvn_mtl.m")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/supplement/evidence")
OUT.mkdir(parents=True, exist_ok=True)
lines = N.read_text().splitlines()
facts, sites = [], []
for i, l in enumerate(lines):
    if "fz_next(&cur" not in l: continue
    ln = i + 1
    nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
    if "for (" in l and "&& fz_next" in l:
        action = "loop-condition (stops collecting)"
    elif "if (!fz_next" in l:
        tail = l.split("fz_next", 1)[1]
        if "return" in tail: action = "return (abort caller)"
        elif "break" in tail: action = "break (stop scan)"
        else: action = "UNKNOWN"
    else:
        action = "UNKNOWN"
    sites.append({"line": ln, "source": l.strip()[:150], "on_false": action, "next_line": nxt[:100]})
    facts.append({"name": f"site {ln} false-handling", "ok": action != "UNKNOWN", "detail": action})
bad = [s for s in sites if s["on_false"] == "UNKNOWN"]
facts.append({"name": "no caller falls through on FALSE", "ok": not bad, "detail": bad})
# merge acceptance points
acc = [i + 1 for i, l in enumerate(lines) if "g_fz.active = 1" in l]
take = [i + 1 for i, l in enumerate(lines) if "fuse_take(" in l and "static" not in l]
planned = [i + 1 for i, l in enumerate(lines) if l.strip() == "planned:"]
last_fz = max(s["line"] for s in sites if 5129 <= s["line"] <= 5260)
facts.append({"name": "merge activation (g_fz.active = 1) happens after the plan's fz_next scans",
              "ok": len(acc) == 1 and acc[0] > last_fz, "detail": {"activate": acc, "last_fz_next": last_fz}})
facts.append({"name": "activation follows the 'planned' label of fuse_try",
              "ok": bool(planned) and acc and acc[0] > planned[0],
              "detail": {"planned": planned, "activate": acc}})
# hoist/prefilter: no other success path from a boundary
facts.append({"name": "fz_prefilter returns 0 (no candidate) when the seen latch is set",
              "ok": "if (g_tf_diag_seen) return 0;" in "\n".join(lines), "detail": "line " + str(next(i + 1 for i, l in enumerate(lines) if "if (g_tf_diag_seen) return 0;" in l))})
OUT.joinpath("callers.json").write_text(json.dumps({"sites": sites, "facts": facts,
    "pass": sum(f["ok"] for f in facts), "fail": sum(not f["ok"] for f in facts)}, indent=2))
print(json.dumps({"sites": [(s["line"], s["on_false"]) for s in sites], "facts": facts}, indent=1))
