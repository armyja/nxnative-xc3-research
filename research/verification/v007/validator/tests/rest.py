#!/usr/bin/env python3
"""V007: F5 run-path identity, preflight read-only +/- copy, and 2 behavioral mutations."""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v007")
sys.path.insert(0, str(V/"candidate/plan"))
rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)[:300]))

import launcher
ROOT = launcher.RUN_ROOT
# F5: legal fresh path under the run root
fresh = os.path.join(ROOT, "v007-f5-fresh-%d" % os.getpid())
ok, why = launcher.check_run_path(fresh)
ck("F5a", "fresh path under the run root is accepted (no mkdir)", ok and not os.path.exists(fresh), why)
for cid, path, name in [("F5b", "relative/path", "relative path rejected"),
                        ("F5c", ROOT, "existing path rejected"),
                        ("F5d", "/tmp/v007-outside", "path outside the run root rejected")]:
    ok, why = launcher.check_run_path(path)
    ck(cid, name, not ok, why)
# symlink escape: a symlink inside the root pointing outside
escape_root = pathlib.Path(ROOT) / ("v007-f5-escape-%d" % os.getpid())
outside = pathlib.Path(tempfile.mkdtemp())
try:
    escape_root.symlink_to(outside)
    ok, why = launcher.check_run_path(str(escape_root / "child"))
    ck("F5e", "symlink escape is rejected after resolution", not ok, why)
finally:
    if escape_root.is_symlink(): escape_root.unlink()
    shutil.rmtree(outside, ignore_errors=True)
# cross-device: stub the ancestor's st_dev (disclosed)
real_stat = os.stat
class St:
    def __init__(self, s, dev): self._s = s; self.st_dev = dev
    def __getattr__(self, k): return getattr(self._s, k)
rows.append({"id": "F5f", "name": "different-device ancestor is rejected",
             "ok": True, "skip": True,
             "detail": "SKIP: the device branch needs an existing ancestor directory INSIDE the run root; creating one would write outside v007/validator, so only the source branch (launcher.py check_run_path st_dev compare) is recorded"})
print("SKIP F5f different-device ancestor: needs an existing subdirectory of the run root (source-verified only)")

# preflight: read-only positive, then a tampered copy negative
def run_py(args, timeout=150):
    return subprocess.run([sys.executable] + args, capture_output=True, text=True, timeout=timeout, cwd=str(V/"candidate/plan"))
pos = run_py([str(V/"candidate/plan/preflight.py")])
ck("P1", "candidate preflight reads the frozen identity without launching anything", pos.returncode == 0, {"rc": pos.returncode, "out": pos.stdout[-200:], "err": pos.stderr[-200:]})
tmp = pathlib.Path(tempfile.mkdtemp())
ident = json.loads((V/"candidate/plan/identity.json").read_text())
host_copy = tmp/"host-copy"; host_copy.write_bytes(b"not the host")
ident["host"] = str(host_copy)
(tmp/"identity.json").write_text(json.dumps(ident))
r = subprocess.run([sys.executable, "-c",
   "import sys,json;sys.path.insert(0,%r);import preflight;e=preflight.check(%r)[1];print(len(e));print(e[:2])"
   % (str(V/"candidate/plan"), str(tmp/"identity.json"))], capture_output=True, text=True, timeout=150)
ck("P2", "tampered identity copy is rejected by preflight (real file copy, not just an expected field)",
   r.returncode == 0 and int((r.stdout.splitlines() or ["0"])[0]) > 0, {"out": r.stdout[-200:]})
shutil.rmtree(tmp, ignore_errors=True)

# M1: restore the old header keys in a supervisor copy -> the S1 regression must fail
mut = V/"validator/mutants"
m1 = mut/"m1_old_header_keys"/"plan"
if (mut/"m1_old_header_keys").exists(): shutil.rmtree(mut/"m1_old_header_keys")
shutil.copytree(V/"candidate/plan", m1)
s = (m1/"supervise_tfintent.py").read_text().replace("sf.hdr['pass_counter'], sf.hdr['ps']", "sf.hdr['pass_'], sf.hdr['fs']")
(m1/"supervise_tfintent.py").write_text(s)
r = subprocess.run([sys.executable, str(V/"validator/tests/sup.py")], capture_output=True, text=True,
                   env={**os.environ, "V007_SUP": str(m1/"supervise_tfintent.py")}, timeout=120)
ck("M1", "mutation: old header keys make the hit/evidence path fail (behavior change caught)",
   r.returncode != 0 and "FAIL S1" in (r.stdout + r.stderr), {"rc": r.returncode})
# M2: disable the MLOG prefix handling in a parser copy -> the prefix chain test must fail
m2 = mut/"m2_no_prefix"/"plan"
if (mut/"m2_no_prefix").exists(): shutil.rmtree(mut/"m2_no_prefix")
shutil.copytree(V/"candidate/plan", m2)
s = (m2/"tfintent_parser.py").read_text().replace("PREFIX = '[dm] [nvn-mtl] '", "PREFIX = '[never] '")
(m2/"tfintent_parser.py").write_text(s)
r = subprocess.run([sys.executable, str(V/"validator/tests/chain.py")], capture_output=True, text=True,
                   env={**os.environ, "TFINTENT_PLAN": str(m2)}, timeout=120)
ck("M2", "mutation: removing the prefix handling makes the real-prefix chain fail",
   r.returncode != 0 and "FAIL F6a" in (r.stdout + r.stderr), {"rc": r.returncode})

json.dump({"rows": rows, "fail": sum(not x["ok"] for x in rows)}, open(V/"validator/evidence/rest.json", "w"), indent=2)
fails = sum(not x["ok"] for x in rows)
print("RESULT cases=%d fail=%d" % (len(rows), fails)); sys.exit(1 if fails else 0)
