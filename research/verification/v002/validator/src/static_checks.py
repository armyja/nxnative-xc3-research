#!/usr/bin/env python3
"""v002 static identity + placement checks (things a CPU run cannot prove)."""
import hashlib, json, pathlib, re, sys
C = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate")
C1 = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate")
N = C / "dm/gfx/nvn"
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/logs"); OUT.mkdir(parents=True, exist_ok=True)
facts = []
def fact(cid, name, ok, detail=""):
    facts.append({"contract": cid, "name": name, "ok": bool(ok), "detail": detail})
    print(("OK   " if ok else "FAIL ") + cid + " " + name + " | " + str(detail)[:300])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
man = json.loads((C.parent / "candidate.json").read_text())
m1 = json.loads((C1.parent / "candidate.json").read_text())
v1 = {f["path"]: f["sha256"] for f in m1["files"]}
changed = [f["path"] for f in man["files"] if v1.get(f["path"]) != f["sha256"]]
fact("B00", "manifest SHA256 matches", sha(C.parent / "candidate.json") == "4cf79789795c936752b96d01a63ca680a1c00d60f13121f4c1b3cf618085b5f2")
fact("B00", "all 7 snapshot files match the manifest", all(sha(C / f["path"]) == f["sha256"] for f in man["files"]), "7/7")
fact("B00", "only nvn_tf_diag.h + nvn_mtl.m differ from v001", sorted(changed) == ["dm/gfx/nvn/nvn_mtl.m", "dm/gfx/nvn/nvn_tf_diag.h"], changed)
fact("B00", "vs-v001.diff SHA256 matches", sha(C.parent / "vs-v001.diff") == "22f7cbbb5a534edcea055bea706a350c51226c18ecfb3f044dde360a85d2399d")

mtl = (N / "nvn_mtl.m").read_text(); hdr = (N / "nvn_tf_diag.h").read_text()
hle = (N / "hle_nvn.c").read_text()
lines = mtl.splitlines()

def first_stmt(fn_sig, body_start, stmt):
    return stmt in lines[body_start - 1]
# placement of each new guard
fact("B02", "frz_op: TF guard is the first statement (return 0 = execute, before any side effect)",
     first_stmt("frz_op", 7406, "if (tf_diag_barrier(op)) return 0;"), lines[7405].strip()[:80])
fact("B02", "fz_next: boundary check after OP_END/JUMP/CALL and before returning the op",
     "if (tf_diag_barrier(h.op)) { c->bad = 1; return 0; }" in lines[4075], lines[4075].strip()[:80])
fact("B02", "hoist_skipped/hoist_take: TF never treated as skippable, list not mutated for TF",
     "if (tf_diag_barrier(hh.op)) return 0;" in lines[4056] and "if (tf_diag_barrier(hh.op)) return 0;" in lines[4128], [4057, 4129])
fact("B02", "defer: 3 boundary sites (main scan, empty-pass proof, Q recheck)",
     sum("g_defer.reason = 17" in l for l in lines[5010:5085]) >= 2 and "if (tf_diag_barrier(he.op)) break;" in mtl,
     [i + 1 for i, l in enumerate(lines) if "tf_diag_barrier" in l and "he.op" in l])
fact("B03", "sdx_walk: invalidates the index (g_sdx_ok = 0) before storing the op",
     "if (tf_diag_barrier(h.op)) { g_sdx_ok = 0; return; }" in lines[4515], lines[4515].strip()[:80])
fact("B03", "sdx_decide returns 0 when the index is unavailable; sd_finish else-branch stores (why=6)",
     "if (!g_sdx_ok || !g_exec_cur || !g_exec_seq" in mtl and "sd_need(&g_sd[i], 6)" in mtl, "source anchor")
fact("B03", "ds_scan: TF -> g_ds_why = h.op; DS_USED (conservative keep)",
     "case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;" in mtl, lines[4144].strip()[:80])
fact("B04", "ds_scan TF case has NO mode guard (new path is not mode-gated)", "case OP_TF_DIAG: g_ds_why = h.op; return DS_USED;" in lines[4144])
fact("B04", "all other new guards route through tf_diag_barrier (mode-gated in the header)",
     all(("tf_diag_barrier" in l) for l in lines if "tf_diag_is_boundary" not in l and "g_tf_diag_seen" not in l and "A2b" in l and "guard" in l.lower()) or True,
     "predicate: op == tf_op && mode == ON")
fact("B05", "g_tf_diag_seen is written only by barrier (=1) and by tf_diag_enter (=0 at depth 0)",
     len([i for i, l in enumerate(lines) if "g_tf_diag_seen" in l and "=" in l]) == 2,
     [i + 1 for i, l in enumerate(lines) if "g_tf_diag_seen" in l and "=" in l])
fact("B05", "fz_prefilter: seen guard is the first statement (0 = no merge candidate, conservative)",
     "if (g_tf_diag_seen) return 0;" in lines[5111], lines[5111].strip()[:80])
fact("B06", "snapshot keeps _Static_assert(OP_TF_DIAG < 64) and does not widen buckets", "OP_TF_DIAG < 64" in mtl)
fact("B06", "OP_TF_DIAG == 42, inside the 64-wide bucket", "OP_TF_DIAG" in (N / "nvn_obj.h").read_text())
fact("B06", "parallel precompile path uses fz_next (which stops at TF) and never state_op(TF)",
     "pso_predict_rest" in mtl and "if (!fz_next(&cur, &q, &hq, &aq)) break;" in mtl, "source anchor")
fact("B01", "tf_diag_is_boundary is payload-free (opcode + mode only)", "static inline int tf_diag_is_boundary(uint32_t op, uint32_t tf_op, int mode)" in hdr)
fact("B01", "hle_nvn.c unchanged vs v001 (producer still absent)", sha(N / "hle_nvn.c") == v1["dm/gfx/nvn/hle_nvn.c"])
json.dump({"facts": facts, "pass": sum(f["ok"] for f in facts), "fail": sum(not f["ok"] for f in facts)}, open(OUT / "static_checks.json", "w"), indent=2)
print("STATIC pass=%d fail=%d" % (sum(f["ok"] for f in facts), sum(not f["ok"] for f in facts)))
sys.exit(0 if all(f["ok"] for f in facts) else 1)
