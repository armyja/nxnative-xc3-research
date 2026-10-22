#!/usr/bin/env python3
"""V007 chain regression (F2/F3/F4/F6) with the real MLOG prefix. Plan dir overridable for mutations."""
import json, os, pathlib, sys
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v007")
PLAN = pathlib.Path(os.environ.get("TFINTENT_PLAN", str(V/"candidate/plan")))
sys.path.insert(0, str(PLAN)); sys.path.insert(0, str(V/"validator/lib"))
from tfintent_parser import TfIntentChain, parse_tf_intent, ParseError
import gen
PFX = "[dm] [nvn-mtl] "
rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)[:260]))
def chain(lines):
    c = TfIntentChain()
    for l in lines: c.feed(l)
    return c

c = chain([gen.kd(), gen.gs(), PFX + gen.tf()])
ck("F6a", "real [dm] [nvn-mtl] [tf-intent] prefix completes the chain", c.result == "hit", {"r": c.result, "why": c.why})
ck("F6b", "real prefixed tf line is retained in chain.raw", any(PFX + "[tf-intent]" in r for r in c.raw), c.raw)
ck("F6c", "bare control still completes", chain([gen.kd(), gen.gs(), gen.tf()]).result == "hit")
for act in ("unknown", "active", "inactive"):
    c = chain([gen.kd(), gen.gs(), PFX + gen.tf(active=act, reason="none")])
    ck("F6d", f"active={act} completes (record only)", c.result == "hit", c.why)

# F2: production sub-lines in real order
c = chain([gen.kd(), "[kd]   attr 0 format 0x1 offset 0 stream 0", "[kd]   stream 0 stride 12",
           "[kd]   uniform 0 offset 16 size 4", gen.gs(), PFX + gen.tf()])
ck("F2", "attr/stream/uniform sub-lines do not break the chain", c.result == "hit", c.why)

# F3: bare normal-target PS
c = chain([gen.kd(fs="2e16c536b845ea0e"), gen.gs(ps="2e16c536b845ea0e", ps_style="bare"),
           PFX + gen.tf(ps="2e16c536b845ea0e")])
ck("F3", "bare normal-target PS chain completes", c.result == "hit", {"r": c.result, "why": c.why})

# F4: depth i32
c = chain([gen.kd(), gen.gs(), PFX + gen.tf(depth=2147483648)])
ck("F4a", "depth i32 max+1 rejected", c.result != "hit", {"r": c.result})
c = chain([gen.kd(), gen.gs(), PFX + gen.tf(depth=-2147483648)])
ck("F4b", "depth i32 min accepted", c.result == "hit", c.why)

# malformed KD / bad suffix / hex
c = chain(["[kd] F1 pass 2 vs=xyz fs=2e16c536b845ea0e_b prim 0 vertices 1 instances 1 first 0 base_vertex 0 base_instance 0 target yes", gen.gs(), PFX + gen.tf()])
ck("M1", "malformed KD is rejected", c.result == "invalid", c.why)
c = chain([gen.kd(), gen.gs(), PFX + gen.tf(gs_key="zzzzzzzzzzzzzzzz")])
ck("M2", "bad hex GS in the intent line is rejected", c.result == "invalid", c.why)
c = chain([gen.kd(), gen.gs(), PFX + gen.tf(ps="2e16c536b845ea0e_q")])
ck("M3", "bad PS suffix rejected", c.result == "invalid", c.why)

# prefix spoofing: a substring/wrapped form must not be accepted
c = chain([gen.kd(), gen.gs(), "xxx " + PFX + gen.tf()])
ck("M4", "wrapped prefix is not accepted", c.result == "invalid", c.why)

# u64 max
c = chain([gen.kd(frame=(1 << 64) - 1, passc=(1 << 64) - 1),
           gen.gs(frame=(1 << 64) - 1, pass_counter=(1 << 64) - 1),
           PFX + gen.tf(frame=(1 << 64) - 1, passc=(1 << 64) - 1, seq=(1 << 64) - 1, events=(1 << 64) - 1, copies=0)])
ck("N1", "u64 MAX accepted through the chain", c.result == "hit", c.why)
c = chain([gen.kd(frame=(1 << 64)), gen.gs(), PFX + gen.tf()])
ck("N2", "u64 MAX+1 in KD rejected", c.result == "invalid", c.why)

json.dump({"rows": rows, "fail": sum(not r["ok"] for r in rows)}, open(V/"validator/evidence/chain.json", "w"), indent=2)
fails = sum(not r["ok"] for r in rows)
print("RESULT cases=%d fail=%d" % (len(rows), fails)); sys.exit(1 if fails else 0)
