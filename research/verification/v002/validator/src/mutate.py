#!/usr/bin/env python3
"""Independent mutation: each mutant must COMPILE (compile_rc==0) and make the suite FAIL."""
import json, pathlib, shutil, subprocess, sys
ROOT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator")
INC, TESTS, OUT, LOG = ROOT/"build/include", ROOT/"tests/v002_tests.c", ROOT/"mutants", ROOT/"logs"
MUT = [
 ("m1_fz_next_boundary_removed", "a2b_fz.inc",
  "        if (tf_diag_barrier(h.op)) { c->bad = 1; return 0; }   // A2b: TF event = candidate boundary; every caller stops on FALSE (no end-of-stream success evidence)\n",
  "", "B02"),
 ("m2_ds_scan_tf_case_removed", "a2b_ds.inc",
  "            case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;   // A2b: unknown TF side effects -> keep depth/stencil, never predict discard\n",
  "", "B03"),
 ("m3_hoist_skipped_guard_removed", "a2b_hoist.inc",
  "if (tf_diag_barrier(hh.op)) return 0;   // A2b: never treat a TF record as skipped", "", "B02"),
]
res = []
for name, fname, old, new, cid in MUT:
    d = OUT/name
    if d.exists(): shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copytree(INC, d/"include")
    src = d/"include"/fname
    t = src.read_text()
    if old not in t:
        res.append({"mutant": name, "error": "patch site not found"}); continue
    src.write_text(t.replace(old, new, 1))
    binp = d/"v002_tests"
    cc = subprocess.run(["cc","-std=c11","-O1","-g","-Wall","-Wextra","-Werror","-I"+str(d/"include"),str(TESTS),"-o",str(binp)], capture_output=True, text=True)
    run = subprocess.run([str(binp)], capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [l for l in (run.stdout.splitlines() if run else []) if l.startswith("FAIL")]
    r = {"mutant": name, "target": fname, "contract": cid, "compile_rc": cc.returncode,
         "run_rc": run.returncode if run else None, "failed": len(fails), "first_fail": fails[:2],
         "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
    (d/"compile.log").write_text(cc.stdout + cc.stderr)
    if run: (d/"run.log").write_text(run.stdout + run.stderr)
    print(json.dumps(r, ensure_ascii=False)); res.append(r)
(LG := LOG/"mutants.json").write_text(json.dumps(res, indent=2))
caught = sum(r.get("verdict") == "BEHAVIOUR-CAUGHT" for r in res)
print("MUTANTS caught=%d/%d" % (caught, len(res)))
sys.exit(0 if caught == len(res) else 1)
