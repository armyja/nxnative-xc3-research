#!/usr/bin/env python3
"""V006-PREFIX-S: does the candidate accept the REAL tf-intent log prefix?

Real production wrapping (V005 source):
  MLOG(...)          -> fprintf(stderr, "[dm] [nvn-mtl] " __VA_ARGS__)
  kd_res_line        -> MLOG("%s", line)      with line starting "[gs-res] ..."
  D04 emit           -> MLOG("%s", tfl)       with tfl starting "[tf-intent] ..."
  KD header          -> fprintf(stderr, "[kd] F...")   (no MLOG prefix)
So the real lines are: bare [kd], "[dm] [nvn-mtl] [gs-res] ...", "[dm] [nvn-mtl] [tf-intent] ...".
"""
import json, pathlib, sys
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v006")
sys.path.insert(0, str(V/"candidate/plan")); sys.path.insert(0, str(V/"validator/lib"))
from tfintent_parser import TfIntentChain, parse_tf_intent, ParseError
import gen

PFX = "[dm] [nvn-mtl] "
rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)[:300]))

def chain(lines):
    c = TfIntentChain()
    for l in lines: c.feed(l)
    return c

# P1 control: bare tf-intent (what the candidate expects)
c = chain([gen.kd(), gen.gs(), gen.tf()])
ck("P1", "control: bare [tf-intent] completes the chain", c.result == "hit", {"result": c.result, "why": c.why})

# P2 real prefix
c = chain([gen.kd(), gen.gs(), PFX + gen.tf()])
ck("P2", "real [dm] [nvn-mtl] [tf-intent] prefix completes the chain", c.result == "hit",
   {"result": c.result, "why": c.why, "intent": c.intent})

# P3 the raw line is retained in the chain (record obtained evidence)
c = chain([gen.kd(), gen.gs(), PFX + gen.tf()])
import re
want = re.sub(r"^\[tf-intent\] ", "", gen.tf())
ck("P3", "real prefixed tf line is kept in chain.raw", any(PFX + "[tf-intent]" in r for r in c.raw),
   {"raw": c.raw})

# P4 parse_tf_intent directly on the real line
try:
    parse_tf_intent(PFX + gen.tf()); direct = True; why = ""
except ParseError as e:
    direct = False; why = str(e)
ck("P4", "parse_tf_intent accepts the real prefixed line", direct, {"error": why})

# P5 supervisor matcher: retention and completion with the real prefix
from supervise_tfintent import TfIntentSupervisor
sf = TfIntentSupervisor()
for l in [gen.kd(), gen.gs(), PFX + gen.tf()]: sf.feed(l)
ck("P5", "supervisor retains the real prefixed tf line", any("[tf-intent]" in l for l in sf.lines), {"lines": len(sf.lines)})
ck("P6", "supervisor completes on the real prefixed line", sf.validated and sf.intent_obtained,
   {"validated": sf.validated, "intent": sf.intent_obtained, "terminal": sf.terminal})

json.dump({"rows": rows, "fail": sum(not r["ok"] for r in rows)},
          open(V/"validator/prefix-supplement/evidence/prefix.json", "w"), indent=2)
print("RESULT cases=%d fail=%d" % (len(rows), sum(not r["ok"] for r in rows)))
sys.exit(0)
