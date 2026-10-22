#!/usr/bin/env python3
"""Independent mutation check: each mutant must still COMPILE (compile_rc == 0) and make the
test suite FAIL (run_rc != 0). A mutant that fails to compile proves nothing about behaviour."""
import json, pathlib, shutil, subprocess, sys

ROOT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/validator")
INC = ROOT / "build/include"
TESTS = ROOT / "tests/tfv_tests.c"
OUT = ROOT / "mutants"
LOG = ROOT / "logs"

MUTANTS = [
    ("m1_saturation_sticky_dropped", "nvn_tf_diag.h",
     "    s->saturated = 1;\n    tf_diag_sticky_saturated(s);",
     "    s->saturated = 1;", "C05"),
    ("m2_bind_creates_active", "nvn_tf_diag.h",
     "        s->bound0_valid = 1;\n        break;                                     // active/pause are untouched by a bind",
     "        s->bound0_valid = 1; s->active = TF_DIAG_ACTIVE_ACTIVE;\n        break;", "C04"),
    ("m3_size_check_weakened", "consumer.inc",
     "if (hsize != (uint32_t)(sizeof(op_hdr) + TF_DIAG_PAYLOAD) ||",
     "if (hsize < (uint32_t)(sizeof(op_hdr) + TF_DIAG_PAYLOAD) ||", "C03"),
    ("m4_alignment_check_removed", "consumer.inc",
     " || (((uintptr_t)a) & 7u) != 0", "", "C03"),
    ("m6_end_from_unknown_allowed", "nvn_tf_diag.h",
     "        } else {\n            tf_diag_mark_unknown(s, TF_DIAG_REASON_END_WITHOUT_BEGIN);\n        }",
     "        } else { s->active = TF_DIAG_ACTIVE_INACTIVE; s->reason = TF_DIAG_REASON_NONE; }", "C04"),
]
DISPATCH_MUTANT = ("m5_consumer_arm_removed", "C07",
                   "case OP_TF_DIAG: tf_diag_case(h.size, a); break;",
                   "case OP_TF_DIAG: break;")

results = []
for name, fname, old, new, cid in MUTANTS:
    d = OUT / name
    if d.exists():
        shutil.rmtree(d)
    shutil.copytree(INC, d / "include")
    src = d / "include" / fname
    text = src.read_text()
    if old not in text:
        results.append({"mutant": name, "error": "patch site not found"}); continue
    src.write_text(text.replace(old, new, 1))
    binp = d / "tfv_tests"
    cc = subprocess.run(["cc", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                         "-I" + str(d / "include"), str(TESTS), "-o", str(binp)],
                        capture_output=True, text=True)
    run = subprocess.run([str(binp)], capture_output=True, text=True) if cc.returncode == 0 else None
    fails = [ln for ln in (run.stdout.splitlines() if run else []) if ln.startswith("FAIL")]
    res = {"mutant": name, "target": fname, "contract": cid,
           "compile_rc": cc.returncode, "run_rc": run.returncode if run else None,
           "failed": len(fails), "first_fail": fails[:3],
           "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
    (d / "compile.log").write_text(cc.stdout + cc.stderr)
    if run:
        (d / "run.log").write_text(run.stdout + run.stderr)
    print(json.dumps(res, ensure_ascii=False))
    results.append(res)

# m5 mutates the transcribed mtl_exec dispatch arm (the snapshot arm is a one-line body that
# calls the same tf_diag_case); it is disclosed as a harness-level mutation.
name, cid, old, new = DISPATCH_MUTANT
d = OUT / name
if d.exists():
    shutil.rmtree(d)
(d / "include").mkdir(parents=True)
shutil.copytree(INC, d / "include", dirs_exist_ok=True)
src = (d / "tfv_tests.c")
src.write_text(TESTS.read_text().replace(old, new, 1))
binp = d / "tfv_tests"
cc = subprocess.run(["cc", "-std=c11", "-O1", "-g", "-Wall", "-Wextra", "-Werror",
                     "-I" + str(d / "include"), str(src), "-o", str(binp)],
                    capture_output=True, text=True)
run = subprocess.run([str(binp)], capture_output=True, text=True) if cc.returncode == 0 else None
fails = [ln for ln in (run.stdout.splitlines() if run else []) if ln.startswith("FAIL")]
res = {"mutant": name, "target": "tests/tfv_tests.c (transcribed mtl_exec arm)", "contract": cid,
       "compile_rc": cc.returncode, "run_rc": run.returncode if run else None,
       "failed": len(fails), "first_fail": fails[:3],
       "verdict": "BEHAVIOUR-CAUGHT" if cc.returncode == 0 and run and run.returncode != 0 else "NOT-CAUGHT"}
(d / "compile.log").write_text(cc.stdout + cc.stderr)
if run:
    (d / "run.log").write_text(run.stdout + run.stderr)
print(json.dumps(res, ensure_ascii=False))
results.append(res)

(LG := LOG / "mutants.json").write_text(json.dumps(results, indent=2))
caught = sum(r.get("verdict") == "BEHAVIOUR-CAUGHT" for r in results)
print("MUTANTS caught=%d/%d" % (caught, len(results)))
sys.exit(0 if caught == len(results) else 1)
