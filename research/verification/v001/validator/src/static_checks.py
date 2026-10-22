#!/usr/bin/env python3
"""Static identity/contract checks that a CPU run cannot prove: numbering, signatures,
registration/producer absence, preserved NVN stub, and the C08 not-wired inventory."""
import hashlib, json, pathlib, re, sys

CAND = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate")
BASE = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-a1/baseline")
N = CAND / "dm/gfx/nvn"
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/validator/logs")
OUT.mkdir(parents=True, exist_ok=True)
facts = []


def fact(cid, name, ok, detail):
    facts.append({"contract": cid, "name": name, "ok": bool(ok), "detail": detail})
    print(("OK   " if ok else "FAIL ") + cid + " " + name + " | " + str(detail))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


MAN = CAND.parent / "candidate.json"
man = json.loads(MAN.read_text())

# --- identity: every manifest file matches in the snapshot copy and the repo worktree
repo = pathlib.Path("/path/to/user/projects/nxnative-xc3")
mis_snap, mis_repo = [], []
for f in man["files"]:
    p = CAND / f["path"]
    if not p.exists() or sha(p) != f["sha256"]:
        mis_snap.append(f["path"])
    q = repo / f["path"]
    if not q.exists() or sha(q) != f["sha256"]:
        mis_repo.append(f["path"])
fact("C00", "manifest SHA256 matches file", sha(MAN) == "2ba2f76a15ff5e565e33caef2474e342a9f079abcb06a5259ebf13fbfa83c995",
     sha(MAN))
fact("C00", "all 7 snapshot files match manifest SHA256", not mis_snap, mis_snap or "7/7")
# The repo is dirty and was already being edited while this verification ran (see drift below);
# the manifest snapshot is the only identity. Record whether the live repo still matches it.
drift = {}
for f in man["files"]:
    q = repo / f["path"]
    h = sha(q) if q.exists() else None
    if h != f["sha256"]:
        drift[f["path"]] = {"manifest": f["sha256"], "repo_now": h,
                            "repo_mtime": __import__("datetime").datetime.fromtimestamp(q.stat().st_mtime).isoformat() if q.exists() else None}
fact("C00", "repo worktree drift vs manifest recorded (informational; manifest is the identity)",
     True, drift or "no drift at check time")

# --- C01 opcode numbering: baseline list + OP_TF_DIAG, OP_COUNT_ moved 42 -> 43
def enum_names(path, first, last):
    text = "".join(path.read_text().splitlines(keepends=True)[first - 1:last])
    body = text[text.index("{") + 1:text.rindex("}")]
    body = re.sub(r"//[^\n]*", "", body)
    return [t.strip() for t in body.split(",") if t.strip()]

cand_ops = enum_names(N / "nvn_obj.h", 96, 104)
base_ops = enum_names(BASE / "nvn_obj.h", 96, 104)
fact("C01", "candidate enum == baseline enum + OP_TF_DIAG appended before OP_COUNT_",
     cand_ops == base_ops[:-1] + ["OP_TF_DIAG", "OP_COUNT_"], {"baseline_count": base_ops.index("OP_COUNT_"),
                                                              "candidate_count": cand_ops.index("OP_COUNT_"),
                                                              "tf_index": cand_ops.index("OP_TF_DIAG")})

# --- C01 seven typed signatures: compare adapter definitions to nvn_protos.h typedefs
proto = (N / "nvn_protos.h").read_text()
hle = (N / "hle_nvn.c").read_text()
want = {
 "dm_tf_diag_bind": "nvnCommandBufferBindTransformFeedbackBuffer",
 "dm_tf_diag_bind_plural": "nvnCommandBufferBindTransformFeedbackBuffers",
 "dm_tf_diag_begin": "nvnCommandBufferBeginTransformFeedback",
 "dm_tf_diag_end": "nvnCommandBufferEndTransformFeedback",
 "dm_tf_diag_pause": "nvnCommandBufferPauseTransformFeedback",
 "dm_tf_diag_resume": "nvnCommandBufferResumeTransformFeedback",
 "dm_tf_diag_draw": "nvnCommandBufferDrawTransformFeedback",
}

def params(sig):
    inner = sig[sig.index("(") + 1:sig.rindex(")")]
    return [p.strip() for p in inner.split(",") if p.strip()]

TYPE_WORDS = {"NVNcommandBuffer", "NVNbufferAddress", "NVNbufferRange", "NVNdrawPrimitive",
              "int", "size_t", "const", "unsigned", "char", "void", "bool", "float",
              "int32_t", "uint32_t", "uint64_t", "int64_t"}


def norm(t):
    t = re.sub(r"\s+", " ", t.strip())
    # drop the parameter name: any identifier that is not a known type word
    toks = [x for x in re.findall(r"[A-Za-z_]\w*|\*", t) if x == "*" or x in TYPE_WORDS]
    return " ".join(toks)

mismatch = []
for fn, proto_name in want.items():
    m = re.search(r"typedef void \(\*NVNT_" + proto_name + r"\)(\([^;]*\));", proto)
    if not m:
        mismatch.append((fn, "proto missing")); continue
    d = re.search(r"void " + fn + r"\(([^)]*)\)", hle)
    if not d:
        mismatch.append((fn, "adapter missing")); continue
    pt = [norm(x) for x in params("(" + d.group(1) + ")")]
    pp = [norm(x) for x in params(m.group(1))]
    if pt != pp:
        mismatch.append((fn, pp, pt))
fact("C01", "7 adapters keep the exact nvn_protos.h parameter types", not mismatch, mismatch or "7/7")

# --- C01 no slot registration / no producer / NVN stub preserved
slots = "\n".join(hle.splitlines()[75:91])
fact("C01", "nvn_init_slots() registers no TF entry", "tf_diag" not in slots, "checked lines 76-91")
fact("C01", "adapters are not swnvn section entries (no nvn_impl e_)", "e_dm_tf_diag" not in hle, "no such symbol")
calls = [ln for ln in hle.splitlines() if re.search(r"\bdm_tf_diag_(bind|bind_plural|begin|end|pause|resume|draw|invalid)\s*\(\s*[a-z_]", ln)]
fact("C01", "no producer calls the adapters in hle_nvn.c", not calls, calls or "none")
real = re.findall(r"NVN\(nvnCommandBuffer\w*TransformFeedback\w*", hle)
base_real = re.findall(r"NVN\(nvnCommandBuffer\w*TransformFeedback\w*", (BASE / "hle_nvn.c").read_text())
fact("C01", "NVN TF entry points remain unimplemented stubs (unchanged vs baseline)", real == base_real == [],
     {"candidate": real, "baseline": base_real})

# --- C02 rec() body unchanged vs pre-A1 baseline
def rec_body(text):
    m = re.search(r"static void \*rec\(NVNcommandBuffer \*c, uint32_t op, size_t payload\) \{.*?\n\}", text, re.S)
    return m.group(0) if m else None
rb_c, rb_b = rec_body(hle), rec_body((BASE / "hle_nvn.c").read_text())
fact("C02", "rec() recording arithmetic is byte-identical to the pre-A1 baseline",
     rb_c is not None and rb_c == rb_b, {"candidate_sha256": hashlib.sha256((rb_c or "").encode()).hexdigest(),
                                         "baseline_sha256": hashlib.sha256((rb_b or "").encode()).hexdigest()})

# --- C07 exactly one OP_TF_DIAG consumer arm, no fallthrough neighbours
mtl = (N / "nvn_mtl.m").read_text()
arms = [i + 1 for i, ln in enumerate(mtl.splitlines()) if "case OP_TF_DIAG:" in ln]
fact("C07", "exactly one case OP_TF_DIAG arm", len(arms) == 1, arms)
line = mtl.splitlines()[arms[0] - 1]
fact("C07", "the arm calls tf_diag_case(h.size, a) once and breaks", "break;" in line and line.count("tf_diag_case") == 1, line.strip())

# --- C08 not-wired inventory: nothing else references the model
for fn in ("sdx_seq", "hoist_take", "defer_begin_q", "frz_op"):
    m = re.search(r"(?:static )?\w[\w \*]*\b" + fn + r"\(([^)]*)\)\s*\{", mtl)
    body = ""
    if m:
        start = m.end(); depth = 1; i = start
        while i < len(mtl) and depth:
            depth += {"{": 1, "}": -1}.get(mtl[i], 0); i += 1
        body = mtl[start:i]
    fact("C08", f"{fn}() does not reference TF diag", "tf_diag" not in body and "TF_DIAG" not in body,
         "not wired" if not body else "checked")
fact("C08", "dm_tf_diag_snapshot/events/copies referenced only by their definitions (no snapshot hook)",
     len(re.findall(r"\bdm_tf_diag_(snapshot|events|copies)\b", mtl)) == 3, "3 definition sites")
fact("C08", "dm_tf_diag_set_mode is never called after startup (A1 keeps mode fixed OFF)",
     len(re.findall(r"\bdm_tf_diag_set_mode\b", hle)) == 1, "1 definition site")
fact("C08", "OP_TF_DIAG never appears in scanning/hoist/defer/frz helpers",
     len([ln for ln in mtl.splitlines() if "OP_TF_DIAG" in ln]) == 1,
     [ln.strip()[:60] for ln in mtl.splitlines() if "OP_TF_DIAG" in ln])

json.dump({"facts": facts, "pass": sum(f["ok"] for f in facts), "fail": sum(not f["ok"] for f in facts)},
          open(OUT / "static_checks.json", "w"), indent=2)
print("STATIC pass=%d fail=%d" % (sum(f["ok"] for f in facts), sum(not f["ok"] for f in facts)))
sys.exit(0 if all(f["ok"] for f in facts) else 1)
