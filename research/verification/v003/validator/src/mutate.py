#!/usr/bin/env python3
"""V003 mutant: remove the ds_scan TF mode gate (back to unconditional keep). compile_rc must be 0, run must fail."""
import json, pathlib, shutil, subprocess, sys
R = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v003/validator")
d = R / "mutants/m1_ds_tf_gate_removed"
if d.exists(): shutil.rmtree(d)
d.mkdir(parents=True)
shutil.copytree(R/"build/include", d/"include")
src = d/"include/ds.inc"
old = "            case OP_TF_DIAG: if (tf_diag_barrier(h.op)) { g_ds_why = h.op; return DS_USED; } break;   // A2b: only an active boundary keeps depth/stencil; OFF/INVALID falls through to the original default path\n"
new = "            case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;\n"
t = src.read_text()
res = {"mutant": "m1_ds_tf_gate_removed"}
if old not in t:
    res.update({"error": "site not found"})
else:
    src.write_text(t.replace(old, new, 1))
    binp = d/"v003_tests"
    cc = subprocess.run(["cc","-std=c11","-O1","-g","-Wall","-Wextra","-Werror","-I"+str(d/"include"),
                         str(R/"tests/v003_tests.c"),"-o",str(binp)], capture_output=True, text=True)
    run = subprocess.run([str(binp)], capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [l for l in (run.stdout.splitlines() if run else []) if l.startswith("FAIL")]
    res.update({"compile_rc": cc.returncode, "run_rc": run.returncode if run else None,
                "failed": len(fails), "first_fail": fails[:2],
                "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"})
    (d/"compile.log").write_text(cc.stdout + cc.stderr)
    if run: (d/"run.log").write_text(run.stdout + run.stderr)
(R/"logs/mutants.json").write_text(json.dumps([res], indent=2))
print(json.dumps(res, ensure_ascii=False))
sys.exit(0 if res.get("verdict") == "BEHAVIOUR-CAUGHT" else 1)
