#!/usr/bin/env python3
"""Generate the verification harness inputs from the read-only candidate snapshot.

Every extracted region is recorded with its exact source line range and SHA256 so a
reader can re-derive it. No file under the candidate snapshot is modified.
"""
import hashlib
import json
import pathlib

CAND = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/validator/build/include")
OUT.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lines(path):
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


prov = {"snapshot": str(CAND), "regions": []}


def region(tag, path, first, last, text, out_name):
    block = "".join(lines(path)[first - 1:last])
    (OUT / out_name).write_text(text + block, encoding="utf-8")
    prov["regions"].append({
        "tag": tag, "source": str(path), "line_range": [first, last],
        "source_sha256": sha(path), "generated": out_name,
        "generated_sha256": hashlib.sha256((text + block).encode()).hexdigest(),
    })


model_src = CAND / "nvn_tf_diag.h"
(OUT / "nvn_tf_diag.h").write_text(model_src.read_text(encoding="utf-8"), encoding="utf-8")
prov["regions"].append({"tag": "model header", "source": str(model_src), "line_range": "1-end",
                        "source_sha256": sha(model_src), "generated": "nvn_tf_diag.h",
                        "generated_sha256": sha(OUT / "nvn_tf_diag.h")})

region("opcode enum + op_hdr", CAND / "nvn_obj.h", 95, 104,
       "// extracted verbatim from candidate dm/gfx/nvn/nvn_obj.h\n#pragma once\n#include <stdint.h>\n",
       "ops.h")

region("recording adapters", CAND / "hle_nvn.c", 779, 796,
       "// extracted verbatim from candidate dm/gfx/nvn/hle_nvn.c\n#pragma once\n",
       "adapters.inc")

region("A2a consumer", CAND / "nvn_mtl.m", 7695, 7728,
       "// extracted verbatim from candidate dm/gfx/nvn/nvn_mtl.m (inside TF-DIAG-A2A markers)\n#pragma once\n",
       "consumer.inc")

prov["candidate_manifest_sha256"] = sha(pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate.json"))
prov["manifest"] = json.loads(pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate.json").read_text())
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "regions": prov["regions"]}, indent=2))
