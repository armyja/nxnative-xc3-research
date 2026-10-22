#!/usr/bin/env python3
"""V005 mutants: revert the HIT guard, or publish ON on failed install. compile_rc must be 0."""
import json, pathlib, shutil, subprocess, sys
R = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v005/validator")
MUT = [
 ("m1_hit_guard_removed", "mtl_fmt.inc",
  "static int kd_tf_intent_wanted(const kdr_record *r) { return r && r->result == KDR_HIT && tf_diag_on(); }",
  "static int kd_tf_intent_wanted(const kdr_record *r) { return r && tf_diag_on(); }",
  "1 full", "V5.2"),
 ("m2_publish_on_failure", "hle_init.inc",
  "    g_tf_diag_mode = ok ? TF_DIAG_MODE_ON : TF_DIAG_MODE_OFF;",
  "    g_tf_diag_mode = requested == TF_DIAG_MODE_ON ? TF_DIAG_MODE_ON : TF_DIAG_MODE_OFF;",
  "1 missing", "V5.1"),
]
res = []
for name, inc, old, new, args, cid in MUT:
    d = R/"mutants"/name
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copytree(R/"build/include", d/"include")
    src = d/"include"/inc
    t = src.read_text()
    if old not in t:
        res.append({"mutant": name, "error": "site not found"}); continue
    src.write_text(t.replace(old, new, 1))
    binp = d/"test"
    cc = subprocess.run(["cc","-std=c11","-O1","-g","-Wall","-Wextra","-Werror","-Wno-unused-function","-Wno-unused-parameter",
                         "-I"+str(d/"include"), str(R/"tests/t_v5.c"), "-o", str(binp)], capture_output=True, text=True)
    run = subprocess.run([str(binp)] + args.split(), capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [l for l in (run.stdout.splitlines() if run else []) if l.startswith("FAIL")]
    r = {"mutant": name, "contract": cid, "args": args, "compile_rc": cc.returncode,
         "run_rc": run.returncode if run else None, "failed": len(fails), "first_fail": fails[:2],
         "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
    (d/"compile.log").write_text(cc.stdout + cc.stderr)
    if run: (d/"run.log").write_text(run.stdout + run.stderr)
    print(json.dumps(r, ensure_ascii=False)); res.append(r)
(R/"logs/mutants.json").write_text(json.dumps(res, indent=2))
caught = sum(r.get("verdict") == "BEHAVIOUR-CAUGHT" for r in res)
print("MUTANTS caught=%d/%d" % (caught, len(res)))
sys.exit(0 if caught == len(res) else 1)
