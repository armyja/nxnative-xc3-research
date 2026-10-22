#!/usr/bin/env python3
"""LogTail partial-line, launcher/preflight static+negatives, and 2 behavioral mutations."""
import json, os, pathlib, shutil, subprocess, sys, tempfile, importlib
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v006")
PLAN = V/"candidate/plan"
sys.path.insert(0, str(PLAN)); sys.path.insert(0, str(V/"validator/lib"))
import gen
rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)[:300]))

# L1 LogTail: partial line held, completed line delivered
import supervise_tfintent as supmod
with tempfile.TemporaryDirectory() as td:
    p = pathlib.Path(td)/"log"
    p.write_text(gen.kd()[:20])                 # half a line, no newline
    t = supmod.LogTail(str(p))
    first = t.lines(); held = t.partial()
    with open(p, "a") as f: f.write(gen.kd()[20:] + "\n")
    second = t.lines()
    ck("L1", "LogTail holds a partial line and delivers it once the newline arrives",
       first == [] and held and second and second[0] == gen.kd(), {"first": first, "held": len(held), "second": len(second)})

# L2 launcher static contract
src = (PLAN/"launcher.py").read_text()
ck("L2", "launcher uses the Python interpreter for the supervisor route", "[sys.executable,sup," in src)
ck("L3", "launcher fixes DM_NVN_TF_DIAG=1 and the 2800/10/180 gates",
   "DM_NVN_TF_DIAG':'1'" in src and "'--secs','180'" in src.replace(" ", "") and
   "'--gate-secs','10'" in src.replace(" ", "") and "'--gate-mib','2800'" in src.replace(" ", ""))
ck("L4", "launcher refuses relative/nonexistent run paths and existing run dirs before creating anything",
   "os.path.isabs(a.run)" in src and "os.path.exists(a.run)" in src and src.index("os.makedirs(") > src.index("os.path.exists(a.run)"))
ck("L5", "launcher forbids inherited test/override env", "FORBIDDEN" in src and "IMGSUP_TEST_" in src)
ck("L6", "SSD constraint is not actually enforced (no device/df check; only absolute + not-exists)",
   not any(k in src for k in ("st_dev", "diskutil", "df -")), {"note": "run dir remains unvalidated for SSD"})
ck("L7", "preflight-only default: no run dir / child path before the launch check",
   "launch=not-requested run_dir=NOT_CREATED child=NOT_STARTED" in src)

# M1/M2 behavioral mutations on validator copies
mut = V/"validator/mutants"; mut.mkdir(exist_ok=True)
def make(name):
    d = mut/name/"plan"
    if d.exists(): shutil.rmtree(mut/name)
    shutil.copytree(PLAN, d)
    return d
# M1: parser no longer checks tf-intent association fields
d = make("m1_no_association")
p = d/"tfintent_parser.py"; s = p.read_text()
s = s.replace("if (it['frame'], it['pass_counter']) != (h.get('frame'), h.get('pass_counter')):",
              "if False and (it['frame'], it['pass_counter']) != (h.get('frame'), h.get('pass_counter')):")
s = s.replace("if it['vs'] != h.get('vs') or it['ps'] != h.get('ps'):", "if False:")
p.write_text(s)
r = subprocess.run([sys.executable, str(V/"validator/tests/chain.py")], capture_output=True, text=True,
                   env={**os.environ, "TFINTENT_PLAN": str(d)})
import re
out = r.stdout + r.stderr
ck("M1", "mutation: dropping association checks makes wrong-frame/VS/PS cases pass (behavior change caught)",
   r.returncode != 0 and "FAIL C5a" in out, {"rc": r.returncode})
# M2: supervisor treats a gs-res HIT as terminal
d = make("m2_hit_terminal")
p = d/"tfintent_parser.py"; s = p.read_text()
s = s.replace("if t is not None and self.base.result != 'hit':", "if t is not None:")
p.write_text(s)
r = subprocess.run([sys.executable, str(V/"validator/tests/chain.py")], capture_output=True, text=True,
                   env={**os.environ, "TFINTENT_PLAN": str(d)})
ck("M2", "mutation: treating gs-res HIT as terminal breaks the C3 (HIT alone) and C1 chain cases",
   r.returncode != 0 and ("FAIL C1" in (r.stdout+r.stderr) or "FAIL C3" in (r.stdout+r.stderr)), {"rc": r.returncode})

json.dump({"rows": rows, "fail": sum(not x["ok"] for x in rows)}, open(V/"validator/evidence/rest.json", "w"), indent=2)
print("RESULT cases=%d fail=%d" % (len(rows), sum(not x["ok"] for x in rows)))
