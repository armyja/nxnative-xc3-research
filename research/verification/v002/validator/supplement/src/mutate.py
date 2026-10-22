#!/usr/bin/env python3
"""S-mutants: delete one local boundary guard; must compile (compile_rc=0) and fail at run."""
import json, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/supplement")
INC, OUT = ROOT/"build/include", ROOT/"mutants"
MUT = [
 ("m1_sdx_decide_ok_guard_removed", "sdx_decide.inc",
  "    if (!g_sdx_ok || !g_exec_cur || !g_exec_seq || g_sdx_op[g_exec_seq - 1] != g_exec_cur) return 0;\n",
  "", "tests/s01_sdx.c", "S01"),
 ("m2_fz_next_boundary_removed", "fz_next.inc",
  "        if (tf_diag_barrier(h.op)) { c->bad = 1; return 0; }   // A2b: TF event = candidate boundary; every caller stops on FALSE (no end-of-stream success evidence)\n",
  "", "tests/s03_callers.c", "S03"),
]
res = []
for name, inc, old, new, test, cid in MUT:
    d = OUT/name
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copytree(INC, d/"include")
    src = d/"include"/inc
    t = src.read_text()
    if old not in t:
        res.append({"mutant": name, "error": "site not found"}); continue
    src.write_text(t.replace(old, new, 1))
    binp = d/"test"
    cc = subprocess.run(["cc","-std=c11","-O1","-g","-Wall","-Wextra","-Werror","-I"+str(d/"include"),
                         str(ROOT/test),"-o",str(binp)], capture_output=True, text=True)
    run = subprocess.run([str(binp)], capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [l for l in (run.stdout.splitlines() if run else []) if l.startswith("FAIL")]
    r = {"mutant": name, "contract": cid, "compile_rc": cc.returncode,
         "run_rc": run.returncode if run else None, "failed": len(fails), "first_fail": fails[:2],
         "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
    (d/"compile.log").write_text(cc.stdout + cc.stderr)
    if run: (d/"run.log").write_text(run.stdout + run.stderr)
    print(json.dumps(r, ensure_ascii=False)); res.append(r)
(ROOT/"evidence/mutants.json").write_text(json.dumps(res, indent=2))
caught = sum(r.get("verdict") == "BEHAVIOUR-CAUGHT" for r in res)
print("MUTANTS caught=%d/%d" % (caught, len(res)))
sys.exit(0 if caught == len(res) else 1)
