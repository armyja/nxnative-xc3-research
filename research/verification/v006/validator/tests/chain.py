#!/usr/bin/env python3
"""Chain tests against the candidate TfIntentChain (read-only import)."""
import sys, json, pathlib
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v006")
import os
PLAN = pathlib.Path(os.environ.get("TFINTENT_PLAN", str(V/"candidate/plan")))
sys.path.insert(0, str(PLAN)); sys.path.insert(0, str(V/"validator/lib"))
from tfintent_parser import TfIntentChain, parse_tf_intent, ParseError
import gen

def run(lines, **kw):
    c = TfIntentChain(**kw); terms = []
    for l in lines: terms.append(c.feed(l))
    return c, terms

rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)))

# C1 full chain, _b tokens
c, _ = run([gen.kd(), gen.gs(), gen.tf()])
ck("C1", "full KD->gs HIT->_b tf-intent chain terminates as hit", c.result == "hit" and c.terminal and c.intent is not None, {"result": c.result, "why": c.why})

# C2 unknown/active/inactive all complete
for act in ("unknown", "active", "inactive"):
    c, _ = run([gen.kd(), gen.gs(), gen.tf(active=act, reason="none")])
    ck("C2", f"active={act} completes the chain (record only)", c.result == "hit", {"result": c.result, "why": c.why})

# C3 gs HIT alone is not terminal
c, terms = run([gen.kd(), gen.gs()])
ck("C3", "gs-res HIT alone does not terminate (not record obtained)", c.terminal is None and c.record is not None and c.intent is None, {"terminal": c.terminal})

# C4 tf-intent before gs-res
c, _ = run([gen.kd(), gen.tf(), gen.gs()])
ck("C4", "tf-intent before a validated gs-res is rejected", c.result == "invalid", {"result": c.result, "why": c.why})

# C5 wrong association fields
for cid, kw, exp in [("C5a", {"frame": 9}, "invalid"), ("C5b", {"passc": 9}, "invalid"),
                     ("C5c", {"vs": "aaaaaaaaaaaaaaaa_b"}, "invalid"), ("C5d", {"ps": "aaaaaaaaaaaaaaaa_b"}, "invalid"),
                     ("C5e", {"gs_key": "aaaaaaaaaaaaaaaa"}, "invalid")]:
    c, _ = run([gen.kd(), gen.gs(), gen.tf(**kw)])
    ck(cid, f"tf-intent mismatch {list(kw)[0]} rejected", c.result == exp, {"result": c.result, "why": c.why})

# C6 bare PS (normal target per reviewed gsres contract) must be accepted
c, _ = run([gen.kd(fs="2e16c536b845ea0e"), gen.gs(ps="2e16c536b845ea0e", ps_style="bare"), gen.tf(ps="2e16c536b845ea0e")])
ck("C6", "bare normal-target PS chain completes (reviewed contract: bare/_b both normal)", c.result == "hit",
   {"result": c.result, "why": c.why})

# C7 KD attr / stream sub-lines must not break the header
c, _ = run([gen.kd(), "[kd]   attr 0 format 0x1 offset 0 stream 0", "[kd]   stream 0 stride 12", gen.gs(), gen.tf()])
ck("C7", "ordinary [kd] attr/stream output does not terminate the chain", c.result == "hit", {"result": c.result, "why": c.why})

# C8 duplicate KD
c, _ = run([gen.kd(), gen.kd(), gen.gs(), gen.tf()])
ck("C8", "duplicate [kd] header rejected", c.result == "invalid", {"result": c.result, "why": c.why})

# C9 numeric boundaries
c, _ = run([gen.kd(frame=(1 << 64) - 1, passc=(1 << 64) - 1),
            gen.gs(frame=(1 << 64) - 1, pass_counter=(1 << 64) - 1),
            gen.tf(frame=(1 << 64) - 1, passc=(1 << 64) - 1, seq=(1 << 64) - 1, events=(1 << 64) - 1, copies=0)])
ck("C9", "u64 MAX accepted throughout the chain", c.result == "hit", {"result": c.result, "why": c.why})
c, _ = run([gen.kd(frame=(1 << 64)), gen.gs(), gen.tf()])
ck("C10", "u64 MAX+1 in the KD header rejected", c.result == "invalid", {"result": c.result, "why": c.why})
c, _ = run([gen.kd(), gen.gs(), gen.tf(seq=(1 << 64))])
ck("C11", "u64 MAX+1 in tf seq rejected", c.result == "invalid", {"result": c.result, "why": c.why})

# C12 depth i32 boundaries and overflow
c, _ = run([gen.kd(), gen.gs(), gen.tf(depth=-2147483648)])
ok_min = c.result == "hit"
c, _ = run([gen.kd(), gen.gs(), gen.tf(depth=2147483648)])
overflow_rejected = c.result != "hit"
ck("C12", "tf depth stays within i32 (min ok, max+1 rejected)", ok_min and overflow_rejected,
   {"i32_min": ok_min, "overflow_result": c.result, "why": c.why})

# C13 duplicate / extra tokens in the tf line
dup = gen.tf() .replace("depth=0", "depth=0 depth=1")
c, _ = run([gen.kd(), gen.gs(), dup])
ck("C13", "duplicate tf field rejected (strict full-line grammar)", c.result == "invalid", {"result": c.result})
trail = gen.tf() + " extra=1"
c, _ = run([gen.kd(), gen.gs(), trail])
ck("C14", "trailing tf token rejected", c.result == "invalid", {"result": c.result})

# C15 non-HIT with a following intent line must not complete as hit
c, _ = run([gen.kd(), gen.gs(result="gs-key-mismatch"), gen.tf()])
ck("C15", "non-HIT gs-res never completes on a later intent line", c.result != "hit", {"result": c.result, "why": c.why})

json.dump({"rows": rows, "fail": sum(not r["ok"] for r in rows)}, open(V/"validator/evidence/chain.json", "w"), indent=2)
fails = sum(not r["ok"] for r in rows)
print("RESULT cases=%d fail=%d" % (len(rows), fails))
sys.exit(1 if fails else 0)
