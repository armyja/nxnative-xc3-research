#!/usr/bin/env python3
"""End-to-end supervisor test with a synthetic mock host child (never the real host)."""
import json, os, pathlib, shutil, subprocess, sys, tempfile
V = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v006")
sys.path.insert(0, str(V/"validator/lib"))
import gen

SUP = V/"candidate/plan/supervise_tfintent.py"
EXEMPT = V/"candidate/plan/exempt.json"

def mock_host(path, lines, sleep=6):
    body = "#!/usr/bin/env python3\nimport sys, time\n"
    body += "for l in %r: print(l, flush=True)\n" % (list(lines),)
    body += "time.sleep(%r)\n" % sleep
    path.write_text(body); path.chmod(0o755)

def run_case(name, lines, inject, run_dir, extra=()):
    run_dir.mkdir(parents=True, exist_ok=True)
    host = run_dir.parent / ("host_%s.py" % name)
    mock_host(host, lines)
    cmd = [sys.executable, str(SUP), "--host", str(host), "--patched", "x", "--run", str(run_dir),
           "--secs", "3", "--gate-secs", "0", "--gate-mib", "1", "--exempt-json", str(EXEMPT)]
    for i in inject: cmd += ["--test-inject", i]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    stop = ((run_dir/"stop.json").read_text() if (run_dir/"stop.json").exists() else "") + ((run_dir/"coverage.txt").read_text() if (run_dir/"coverage.txt").exists() else "")
    txt = (run_dir/"tfintent.txt").read_text() if (run_dir/"tfintent.txt").exists() else ""
    return {"rc": p.returncode, "out": p.stdout[-400:], "err": p.stderr[-300:], "stop": stop, "txt": txt}

rows = []
def ck(cid, name, cond, detail):
    rows.append({"id": cid, "name": name, "ok": bool(cond), "detail": detail})
    print(("PASS " if cond else "FAIL ") + cid + " " + name + ("" if cond else " | " + json.dumps(detail)[:300]))

with tempfile.TemporaryDirectory() as td:
    root = pathlib.Path(td)
    # S1: correct chain via the real supervisor entry
    r = run_case("ok", [gen.kd(), gen.gs(), gen.tf()], ["synthetic-sampler"], root/"s1")
    ck("S1", "supervisor consumes a correct chain and writes evidence",
       "intent_obtained=1" in r["stop"] and "validated=1" in r["stop"] and r["rc"] == 0, r)

    # S2: production [kd] attr line after the header
    r = run_case("attr", [gen.kd(), "[kd]   attr 0 format 0x1 offset 0 stream 0", gen.gs(), gen.tf()],
                 ["synthetic-sampler"], root/"s2")
    ck("S2", "real capture with [kd] attr output still completes",
       "validated=1" in r["stop"] and "intent_obtained=1" in r["stop"], r)

    # S3: no record, short timeout (disclosed)
    r = run_case("none", ["unrelated log"], ["synthetic-sampler"], root/"s3")
    ck("S3", "no record -> not validated, no intent", "validated=0" in r["stop"] and "intent_obtained=0" in r["stop"], r)

    # S4: evidence write failure (tfintent.txt is a directory)
    rd = root/"s4"; rd.mkdir(); (rd/"tfintent.txt").mkdir()
    host = root/"host_s4.py"; mock_host(host, [gen.kd(), gen.gs(), gen.tf()])
    cmd = [sys.executable, str(SUP), "--host", str(host), "--patched", "x", "--run", str(rd),
           "--secs", "3", "--gate-secs", "0", "--gate-mib", "1", "--exempt-json", str(EXEMPT),
           "--test-inject", "synthetic-sampler"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    stop = ((rd/"stop.json").read_text() if (rd/"stop.json").exists() else "") + ((rd/"coverage.txt").read_text() if (rd/"coverage.txt").exists() else "")
    ck("S4", "evidence write failure is reported, not masked as a hit",
       "evidence-write-failed" in stop and "validated=1" not in stop, {"rc": p.returncode, "stop": stop[-300:]})

    # S5: same-poll nonexempt complete dump after the hit (injected) must take priority and keep the record
    r = run_case("dump", [gen.kd(), gen.gs(), gen.tf()], ["synthetic-sampler", "dump-after-hit"], root/"s5")
    ck("S5", "same-poll complete dump takes priority and the record is retained",
       "complete dump" in r["stop"] and "record_obtained=1" in r["stop"], r)

json.dump({"rows": rows, "fail": sum(not x["ok"] for x in rows)}, open(V/"validator/evidence/sup.json", "w"), indent=2)
print("RESULT cases=%d fail=%d" % (len(rows), sum(not x["ok"] for x in rows)))
