#!/usr/bin/env python3
"""v003 extraction: only the bodies needed for V3.1-V3.4, taken verbatim from the frozen snapshot."""
import hashlib, json, pathlib
C = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v003/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v003/validator/build/include")
OUT.mkdir(parents=True, exist_ok=True)
H = "// extracted verbatim from the frozen v003 snapshot\n#pragma once\n"
prov = {"regions": []}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def region(tag, a, b, hdr=H, fname="nvn_mtl.m"):
    f = C / fname
    block = "".join(f.read_text().splitlines(keepends=True)[a - 1:b])
    name = tag.replace(" ", "_") + ".inc"
    (OUT / name).write_text(hdr + block, encoding="utf-8")
    prov["regions"].append({"tag": tag, "lines": [a, b], "generated": name,
                            "source_sha256": sha(f),
                            "generated_sha256": hashlib.sha256((hdr + block).encode()).hexdigest()})
(OUT / "nvn_tf_diag.h").write_text((C / "nvn_tf_diag.h").read_text(), encoding="utf-8")
region("ops", 95, 104, H + "#include <stdint.h>\n#include <stddef.h>\n", "nvn_obj.h")
region("init", 36, 40)
region("hoist", 4051, 4054)
region("fz", 4055, 4077)
region("ds", 4125, 4151)
region("bind_state", 115, 115, "", "nvn_obj.h")
region("consumer", 7722, 7750)
prov["frozen"] = {"manifest_sha256": sha(C.parents[3] / "candidate.json"),
                  "mtl_sha256": sha(C / "nvn_mtl.m"), "hdr_sha256": sha(C / "nvn_tf_diag.h")}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov["frozen"], indent=1))
