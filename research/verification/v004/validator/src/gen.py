#!/usr/bin/env python3
"""v004 extraction: only the bodies needed for D01-D05, verbatim from the frozen snapshot."""
import hashlib, json, pathlib
C = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v004/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v004/validator/build/include")
OUT.mkdir(parents=True, exist_ok=True)
H = "// extracted verbatim from the frozen v004 snapshot\n#pragma once\n"
prov = {"regions": []}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def region(tag, fname, a, b, hdr=H):
    f = C / fname
    block = "".join(f.read_text().splitlines(keepends=True)[a - 1:b])
    name = tag.replace(" ", "_") + ".inc"
    (OUT / name).write_text(hdr + block, encoding="utf-8")
    prov["regions"].append({"tag": tag, "file": fname, "lines": [a, b],
                            "source_sha256": sha(f), "generated": name,
                            "generated_sha256": hashlib.sha256((hdr + block).encode()).hexdigest()})
for name in ("nvn_tf_diag.h", "nvn_kd_res.h"):
    (OUT / name).write_text((C / name).read_text(), encoding="utf-8")
    prov["regions"].append({"tag": name, "file": name, "lines": "1-end", "source_sha256": sha(C / name),
                            "generated": name, "generated_sha256": sha(OUT / name)})
region("ops", "nvn_obj.h", 95, 104, H + "#include <stdint.h>\n#include <stddef.h>\n")
region("hle_impl_type", "hle_nvn.c", 58, 59)
region("hle_init", "hle_nvn.c", 71, 134)
region("hle_adapters", "hle_nvn.c", 824, 838)
region("mtl_consumer", "nvn_mtl.m", 7753, 7781)
region("mtl_fmt", "nvn_mtl.m", 5554, 5569)
region("mtl_emit", "nvn_mtl.m", 5671, 5679)
prov["frozen"] = {"manifest_sha256": sha(C.parents[3] / "candidate.json"),
                  "hle_sha256": sha(C / "hle_nvn.c"), "mtl_sha256": sha(C / "nvn_mtl.m"),
                  "hdr_sha256": sha(C / "nvn_tf_diag.h"), "kd_sha256": sha(C / "nvn_kd_res.h")}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov["frozen"], indent=1))
