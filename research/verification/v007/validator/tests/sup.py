#!/usr/bin/env python3
"""V007 supervisor regression: correct chain, HIT-only, forced write failures (OSError and not),
sampling-error injection, two synthetic exempt dumps, child reclamation."""
import hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v007")
sys.path.insert(0, str(V/"validator/lib")); import gen
PFX = "[dm] [nvn-mtl] "
SUP = pathlib.Path(os.environ.get("V007_SUP", str(V/"candidate/plan/supervise_tfintent.py")))
EXEMPT = V/"candidate/plan/exempt.json"
rows = []
def ck(cid, name, cond, detail=""):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + str(detail)[:280]))

def mock_host(path, lines, sleep=8):
    path.write_text("#!/usr/bin/env python3\nimport os,sys,time\n"
                    "open(os.environ['V007_CHILD_PID'],'w').write(str(os.getpid()))\n" +
                    "for l in %r: print(l, flush=True)\n" % (list(lines),) + "time.sleep(%r)\n" % sleep)
    path.chmod(0o755)

def run(name, lines, inject, extra_env=None, sup=SUP, prepare=None):
    d = pathlib.Path(tempfile.mkdtemp(prefix="v007_%s_" % name))
    run_dir = d/"run"; run_dir.mkdir()
    host = d/"host.py"; mock_host(host, lines)
    pidfile = d/"child.pid"
    if prepare: prepare(run_dir)
    cmd = [sys.executable, str(sup), "--host", str(host), "--patched", "x", "--run", str(run_dir),
           "--secs", "3", "--gate-secs", "0", "--gate-mib", "1", "--exempt-json", str(EXEMPT)]
    for i in inject: cmd += ["--test-inject", i]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                       env={**os.environ, "V007_CHILD_PID": str(pidfile)})
    pid = int(pidfile.read_text()) if pidfile.exists() else None
    alive = False
    if pid:
        try: os.kill(pid, 0); alive = True
        except ProcessLookupError: alive = False
    out = {"rc": p.returncode, "err": p.stderr[-300:], "dir": str(d), "alive": alive, "pid": pid,
           "timing": (run_dir/"timing.txt").read_text() if (run_dir/"timing.txt").is_file() else None,
           "coverage": (run_dir/"coverage.txt").read_text() if (run_dir/"coverage.txt").is_file() else None,
           "stop": (run_dir/"stop.json").read_text() if (run_dir/"stop.json").is_file() else None,
           "exit_ok": None}
    return out

# S1: correct chain with the real prefix, complete evidence, child reclaimed
r = run("ok", [gen.kd(), gen.gs(), PFX + gen.tf()], ["synthetic-sampler"])
stop = json.loads(r["stop"]) if r["stop"] else {}
ck("S1", "correct chain completes: validated, coverage/stop/timing present, child gone",
   stop.get("validated") is True and stop.get("success") is True and r["coverage"] and r["timing"] and not r["alive"], r)

# S2: gs HIT alone must not complete; child reclaimed
r = run("hitonly", [gen.kd(), gen.gs()], ["synthetic-sampler"])
cov = r["coverage"] or ""
ck("S2", "gs-res HIT alone: record obtained, not validated", "record_obtained=1" in cov and "intent_obtained=0" in cov and "validated=0" in cov and not r["alive"], r)

# S3: coverage/stop write fails with OSError -> cleanup still runs, no success
def prep_dirs(run_dir):
    (run_dir/"coverage.txt").mkdir(); (run_dir/"stop.json").mkdir()
r = run("oserr", [gen.kd(), gen.gs(), PFX + gen.tf()], ["synthetic-sampler"], prepare=prep_dirs)
def no_success(stop):
    try: return json.loads(stop).get("success") is not True
    except Exception: return True
ck("S3", "OSError while serialising evidence: child reclaimed, timing present, no success claim",
   bool(r["timing"]) and "evidence write failed" in r["err"] and not r["alive"] and no_success(r["stop"]), r)

# S4: non-OSError during serialisation (validator copy, disclosed) -> same guarantees
mut = V/"validator/mutants/m_write_raise/plan"
if mut.exists(): shutil.rmtree(V/"validator/mutants/m_write_raise")
shutil.copytree(V/"candidate/plan", mut)
src = (mut/"supervise_tfintent.py").read_text()
src = src.replace('def _write_final(run, sf, kind, reason):\n', 'def _write_final(run, sf, kind, reason):\n    raise ValueError("injected non-OSError during serialisation")\n')
(mut/"supervise_tfintent.py").write_text(src)
r = run("nonoserr", [gen.kd(), gen.gs(), PFX + gen.tf()], ["synthetic-sampler"], sup=mut/"supervise_tfintent.py")
ck("S4", "non-OSError (injected copy): child reclaimed, timing present, no success claim",
   bool(r["timing"]) and "evidence write failed" in r["err"] and not r["alive"] and no_success(r["stop"]), r)

# S5: sampling-error injection -> sampling-error class, child reclaimed
r = run("sampling", [gen.kd(), gen.gs(), PFX + gen.tf()], ["synthetic-sampler", "sample-nonzero"])
ck("S5", "sampling-error injection ends as sampling-error with the child reclaimed",
   r["timing"] and "sampling-error" in (r["timing"] or "") and not r["alive"], r)

# S6: two synthetic exempt dumps are consumed, then the correct chain completes
def prep_dumps(run_dir):
    dump = run_dir/"shdump"; dump.mkdir()
    for key in ("95bfab6122539993", "a841a5d995c26b26"):
        ctl = bytearray(2176); ctl[:4] = bytes.fromhex("34127698")
        code = b"C" * (768 if key == "95bfab6122539993" else 1280)
        ctl = ctl[: 2176]
        (dump/("%s.ctl" % key)).write_bytes(bytes(ctl))
        (dump/("%s.code" % key)).write_bytes(code)
r = run("exempt", [gen.kd(), gen.gs(), PFX + gen.tf()], ["synthetic-sampler"], prepare=prep_dumps)
ck("S6", "two synthetic exempt dumps are skipped and the correct chain still completes",
   bool(r["stop"]) and json.loads(r["stop"]).get("validated") is True, r)

json.dump({"rows": rows, "fail": sum(not x["ok"] for x in rows)}, open(V/"validator/evidence/sup.json", "w"), indent=2)
fails = sum(not x["ok"] for x in rows)
print("RESULT cases=%d fail=%d" % (len(rows), fails)); sys.exit(1 if fails else 0)
