#!/usr/bin/env python3
"""Guard-dominance + direction checks for the A2b sites that cannot be executed here
(defer_try / frz_op / fz_prefilter / sdx_walk / ds_scan). Machine-checked text facts,
anchored to line numbers in the frozen snapshot; not an execution substitute."""
import json, pathlib, re
N = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate/dm/gfx/nvn/nvn_mtl.m")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/logs")
lines = N.read_text().splitlines()
facts = []
def fact(name, ok, detail=""):
    facts.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("OK   " if ok else "FAIL ") + name + " | " + str(detail)[:260])

def find(sub, start=0):
    for i in range(start, len(lines)):
        if sub in lines[i]: return i + 1
    return None

def enclosing_fn(ln):
    for i in range(ln - 1, -1, -1):
        m = re.match(r"^(?:static\s+)?[\w\s\*]+?\b(\w+)\s*\([^;]*\)\s*\{\s*$", lines[i])
        if m: return m.group(1), i + 1
    return None, None

sites = [i + 1 for i, l in enumerate(lines) if "tf_diag_barrier(" in l and "static int tf_diag_barrier" not in l]
fact("every A2b barrier call site found", len(sites) == 8, {"sites": sites})
# Each site must live inside its expected function: between the signature line and the
# first column-0 closing brace after it.
EXPECT = {4057: "hoist_skipped", 4076: "fz_next", 4129: "hoist_take", 4516: "sdx_walk",
          5026: "defer_try", 5062: "defer_try", 5080: "defer_try", 7406: "frz_op"}
for site, fn in EXPECT.items():
    sig = find(f"{fn}(")
    end = next((i + 1 for i in range(sig, len(lines)) if lines[i] == "}"), None)
    ok = sig is not None and site <= len(lines) and sig <= site <= (end or 0)
    fact(f"site {site} is inside {fn}()", ok, {"signature_line": sig, "function_end": end})

# direction of each non-extractable guard
checks = [
 ("frz_op executes TF", "if (tf_diag_barrier(op)) return 0;", 1),
 ("defer main scan + Q recheck refuse the candidate", "if (tf_diag_barrier(h.op)) { g_defer.reason = 17; g_defer.reason_op = h.op; goto fail; }", 2),
 ("defer empty-pass proof stops", "if (tf_diag_barrier(he.op)) break;", 1),
 ("fz_prefilter reports no candidate", "if (g_tf_diag_seen) return 0;", 1),
 ("sdx_walk invalidates the index", "if (tf_diag_barrier(h.op)) { g_sdx_ok = 0; return; }", 1),
 ("ds_scan keeps depth/stencil", "case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;", 1),
]
for name, needle, want in checks:
    n = sum(needle in l for l in lines)
    fact(name, n == want, {"occurrences": n, "line": find(needle)})

# first-statement dominance for functions whose guard must precede any side effect
for fn, needle in [("frz_op", "if (tf_diag_barrier(op)) return 0;"),
                   ("fz_prefilter", "if (g_tf_diag_seen) return 0;"),
                   ("hoist_skipped", "if (tf_diag_barrier(hh.op)) return 0;"),
                   ("hoist_take", "if (tf_diag_barrier(hh.op)) return 0;")]:
    sig = find(f"static int {fn}(")
    body = sig + 1 if fn not in ("hoist_skipped", "hoist_take") else None
    if fn in ("hoist_skipped", "hoist_take"):
        # one-line signature followed by the guard on the same or next line
        ok = needle in lines[sig - 1] or (sig < len(lines) and needle in lines[sig])
        first_stmt = "same line" if needle in lines[sig - 1] else "next line"
    else:
        first = next(i for i in range(sig, len(lines)) if lines[i].strip())
        ok = needle in lines[first]
        first_stmt = lines[first].strip()[:60]
    fact(f"{fn}: boundary guard is the first statement (no prior side effect)", ok, first_stmt)

# defer loops: the barrier is checked before the hoist-skip and before candidate acceptance
d1 = find("if (tf_diag_barrier(h.op)) { g_defer.reason = 17; g_defer.reason_op = h.op; goto fail; }", 4900)
d1b = next(i + 1 for i in range(d1, d1 + 12) if "hoist_skipped(p)" in lines[i]) if d1 else None
fact("defer main loop: barrier precedes the hoist-skip and the switch", d1 and d1b and d1 < d1b, {"barrier": d1, "hoist": d1b})
# Q recheck: barrier appears before the DRAW sampling check in that loop
q = find("if (tf_diag_barrier(h.op)) { g_defer.reason = 17; g_defer.reason_op = h.op; goto fail; }", d1 + 1)
qd = next(i + 1 for i in range(q, q + 12) if "g_defer.reason = 14" in lines[i]) if q else None
fact("defer Q recheck: barrier precedes the sampling conflict check", q and qd and q < qd, {"barrier": q, "conflict": qd})
fail_line = find("fail:")
fact("defer 'goto fail' exits without taking the deferred candidate (fail label sets reason and returns)",
     fail_line is not None and "return" in "\n".join(lines[fail_line - 1:fail_line + 4]), {"fail_line": fail_line})

# B04: ds_scan's case is unconditional (no mode guard)
ds = find("case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;")
fact("B04 finding: ds_scan TF case carries no mode gate", ds is not None and "tf_diag_barrier" not in lines[ds - 1], {"line": ds})

json.dump({"facts": facts, "pass": sum(f["ok"] for f in facts), "fail": sum(not f["ok"] for f in facts)},
          open(OUT / "static_guards.json", "w"), indent=2)
print("GUARDS pass=%d fail=%d" % (sum(f["ok"] for f in facts), sum(not f["ok"] for f in facts)))
