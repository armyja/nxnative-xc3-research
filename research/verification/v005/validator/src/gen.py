#!/usr/bin/env python3
"""v005 extraction for V5.1-V5.4 (verbatim from the frozen snapshot)."""
import hashlib, json, pathlib
C = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v005/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v005/validator/build/include")
OUT.mkdir(parents=True, exist_ok=True)
H = "// extracted verbatim from the frozen v005 snapshot\n#pragma once\n"
prov = {"regions": []}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def region(tag, fname, a, b, hdr=H):
    f = C / fname
    block = "".join(f.read_text().splitlines(keepends=True)[a - 1:b])
    name = tag.replace(" ", "_") + ".inc"
    (OUT / name).write_text(hdr + block, encoding="utf-8")
    prov["regions"].append({"tag": tag, "file": fname, "lines": [a, b], "source_sha256": sha(f),
                            "generated": name, "generated_sha256": hashlib.sha256((hdr + block).encode()).hexdigest()})
for name in ("nvn_tf_diag.h", "nvn_kd_res.h"):
    (OUT / name).write_text((C / name).read_text(), encoding="utf-8")
    prov["regions"].append({"tag": name, "file": name, "lines": "1-end", "source_sha256": sha(C / name),
                            "generated": name, "generated_sha256": sha(OUT / name)})
region("ops", "nvn_obj.h", 95, 104, H + "#include <stdint.h>\n#include <stddef.h>\n")
region("hle_impl_type", "hle_nvn.c", 58, 59)
region("hle_init", "hle_nvn.c", 71, 144)     # mode var .. nvn_init_slots end (incl. installer + activate)
region("hle_adapters", "hle_nvn.c", 834, 848)
region("mtl_barrier", "nvn_mtl.m", 43, 43)
region("mtl_consumer", "nvn_mtl.m", 7757, 7785)
region("mtl_fmt", "nvn_mtl.m", 5557, 5573)   # wanted + line
region("mtl_emit", "nvn_mtl.m", 5675, 5683)
prov["frozen"] = {"manifest_sha256": sha(C.parents[3] / "candidate.json"),
                  "hle_sha256": sha(C / "hle_nvn.c"), "mtl_sha256": sha(C / "nvn_mtl.m")}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov["frozen"], indent=1))
