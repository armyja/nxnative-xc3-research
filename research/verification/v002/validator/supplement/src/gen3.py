#!/usr/bin/env python3
"""Extract the bodies used by V002-S (S01/S02/S03) verbatim from the frozen v002 snapshot."""
import hashlib, json, pathlib
CAND = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/supplement/build/include")
OUT.mkdir(parents=True, exist_ok=True)
prov = {"source_dir": str(CAND), "regions": []}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def lines(p): return p.read_text().splitlines(keepends=True)
def region(tag, path, a, b, hdr):
    block = "".join(lines(path)[a - 1:b])
    name = tag.replace(" ", "_") + ".inc"
    (OUT / name).write_text(hdr + block, encoding="utf-8")
    prov["regions"].append({"tag": tag, "file": path.name, "lines": [a, b],
                            "source_sha256": sha(path), "generated": name,
                            "generated_sha256": hashlib.sha256((hdr + block).encode()).hexdigest()})
H = "// extracted verbatim from the frozen v002 snapshot\n#pragma once\n"
region("a2b_init", CAND / "nvn_mtl.m", 35, 44, H)
region("hoist", CAND / "nvn_mtl.m", 4055, 4058, H)
region("sd_need", CAND / "nvn_mtl.m", 4161, 4161, H)
region("sd_att", CAND / "nvn_mtl.m", 2187, 2188, H + "#include <stdint.h>\n")
region("sdx_core", CAND / "nvn_mtl.m", 4490, 4496, H)
region("sdx_op_state", CAND / "nvn_mtl.m", 4505, 4506, H)
region("g_exec_cur", CAND / "nvn_mtl.m", 4160, 4160, H)
region("fz_next", CAND / "nvn_mtl.m", 4059, 4081, H)
region("sdx_decide", CAND / "nvn_mtl.m", 4590, 4607, H)
region("defer_empty_loop", CAND / "nvn_mtl.m", 5061, 5067, H)   # loop body only; wrapper retargets `break`
(OUT / "nvn_tf_diag.h").write_text((CAND / "nvn_tf_diag.h").read_text(), encoding="utf-8")
region("ops", CAND / "nvn_obj.h", 95, 104, H + "#include <stdint.h>\n#include <stddef.h>\n")
prov["frozen"] = {
 "candidate_manifest_sha256": sha(CAND.parents[3] / "candidate.json"),
 "mtl_sha256": sha(CAND / "nvn_mtl.m"), "tf_diag_h_sha256": sha(CAND / "nvn_tf_diag.h")}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps({"regions": prov["regions"], "frozen": prov["frozen"]}, indent=1))
