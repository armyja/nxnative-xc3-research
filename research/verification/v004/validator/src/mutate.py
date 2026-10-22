#!/usr/bin/env python3
"""V004 mutants: each must COMPILE (compile_rc==0) and make the suite FAIL."""
import json, pathlib, shutil, subprocess, sys
R = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v004/validator")
MUT = [
 ("m1_observer_gate_forbidden", "mtl_emit.inc",
  "    if (tf_diag_on()) {", "    if (1) {",
  "tests/t_obs.c", ["-Wno-unused-function", "-Wno-unused-parameter"], "D04"),
 ("m2_mode_not_fixed", "hle_init.inc",
  "    g_tf_diag_mode_fixed = 1;\n", "",
  "tests/t_init.c", [], "D01"),
]
res = []
for name, inc, old, new, test, extra, cid in MUT:
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
    cc = subprocess.run(["cc","-std=c11","-O1","-g","-Wall","-Wextra","-Werror"] + extra +
                        ["-I"+str(d/"include"), str(R/test), "-o", str(binp)], capture_output=True, text=True)
    run = subprocess.run([str(binp), "1", "full"], capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [l for l in (run.stdout.splitlines() if run else []) if l.startswith("FAIL")]
    r = {"mutant": name, "contract": cid, "compile_rc": cc.returncode,
         "run_rc": run.returncode if run else None, "failed": len(fails), "first_fail": fails[:2],
         "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
    (d/"compile.log").write_text(cc.stdout + cc.stderr)
    if run: (d/"run.log").write_text(run.stdout + run.stderr)
    print(json.dumps(r, ensure_ascii=False)); res.append(r)
(R/"logs/mutants.json").write_text(json.dumps(res, indent=2))
caught = sum(r.get("verdict") == "BEHAVIOUR-CAUGHT" for r in res)
print("MUTANTS caught=%d/%d" % (caught, len(res)))
sys.exit(0 if caught == len(res) else 1)
