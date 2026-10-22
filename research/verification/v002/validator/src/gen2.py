#!/usr/bin/env python3
"""Generate v002 harness inputs by extracting the A2b code verbatim from the frozen snapshot."""
import hashlib, json, pathlib

CAND = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate/dm/gfx/nvn")
V1 = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v001/candidate/dm/gfx/nvn")
OUT = pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/validator/build/include")
OUT.mkdir(parents=True, exist_ok=True)


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def lines(p): return p.read_text(encoding="utf-8").splitlines(keepends=True)


prov = {"candidate": str(CAND.resolve().parents[3] / "candidate.json"), "regions": []}


def region(tag, path, first, last, text, out_name):
    block = "".join(lines(path)[first - 1:last])
    (OUT / out_name).write_text(text + block, encoding="utf-8")
    prov["regions"].append({"tag": tag, "source": str(path), "line_range": [first, last],
                            "source_sha256": sha(path), "generated": out_name,
                            "generated_sha256": hashlib.sha256((text + block).encode()).hexdigest()})


(OUT / "nvn_tf_diag.h").write_text((CAND / "nvn_tf_diag.h").read_text(), encoding="utf-8")
prov["regions"].append({"tag": "model+boundary header", "source": str(CAND / "nvn_tf_diag.h"),
                        "line_range": "1-end", "source_sha256": sha(CAND / "nvn_tf_diag.h"),
                        "generated": "nvn_tf_diag.h", "generated_sha256": sha(OUT / "nvn_tf_diag.h")})

region("opcode enum + op_hdr", CAND / "nvn_obj.h", 95, 104,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_obj.h\n#pragma once\n#include <stdint.h>\n#include <stddef.h>\n",
       "ops.h")
region("p_bind_state", CAND / "nvn_obj.h", 115, 115, "", "bind_state.h")
region("A2b init: barrier + seen + 64 assert", CAND / "nvn_mtl.m", 35, 44,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_mtl.m\n#pragma once\n", "a2b_init.inc")
region("hoist skip list + hoist_skipped", CAND / "nvn_mtl.m", 4055, 4058,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_mtl.m\n#pragma once\n", "a2b_hoist.inc")
region("fz_cursor + fz_next", CAND / "nvn_mtl.m", 4059, 4081,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_mtl.m\n#pragma once\n", "a2b_fz.inc")
region("hoist_take + ds_scan", CAND / "nvn_mtl.m", 4129, 4155,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_mtl.m\n#pragma once\n", "a2b_ds.inc")
# A1/A2a consumer, unchanged vs v001: extracted from the v002 snapshot for the "scans must not touch the shadow" check.
region("A2a consumer (v002 copy, unchanged)", CAND / "nvn_mtl.m", 7725, 7755,
       "// extracted verbatim from v002 dm/gfx/nvn/nvn_mtl.m (A2A block, unchanged vs v001)\n#pragma once\n", "consumer.inc")

prov["hashes"] = {"candidate_json_sha256": sha(pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/candidate.json")),
                  "vs_v001_diff_sha256": sha(pathlib.Path("/path/to/external-drive/xc3/work/experiments/tf-diag-verification/v002/vs-v001.diff")),
                  "v001_ds_scan_present": "OP_TF_DIAG" in (V1 / "nvn_mtl.m").read_text().split("static int ds_scan")[1][:2000]}
(OUT / "provenance.json").write_text(json.dumps(prov, indent=2))
print(json.dumps(prov, indent=2))
