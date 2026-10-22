# V003 追加：helper 变化下的依赖处理（barrier body）

主管要求：继承不能只看行号；`tf_diag_barrier` 在 v003 确有纯化变化，依赖它的代表组合必须用新 body 重编执行，
未改的 decide/finish 等可按 body SHA 继承。本文件是对 `report.md` 的**追加**，不改其结论。

## 变化本身

| | SHA256 |
|---|---|
| barrier body（v002，带 latch 写入） | `5bc67eed54967e8f23d52a9cab4f412147a7f6f2070ca8b8c8554abd49499666` |
| barrier body（v003，纯谓词） | `a6c8dad70619757fb195131a99c645f7e7500809dfd3508bbbead2b0d33a2086` |
| `nvn_tf_diag.h`（两版相同） | `578957c7…12ee` |

## 执行：两版 barrier 同编译单元对比

18 组输入（opcode ∈ {OP_TF_DIAG, OP_DRAW, OP_END, 63, 0, 7} × mode ∈ {OFF, ON, INVALID}）：
**mismatches = 0**。v002 版仅在 ON+OP_TF_DIAG 时写 `g_tf_diag_seen`（1 次），v003 版从不写。
证据：`evidence/barrier-equivalence.json`、`build/barrier_equiv`（`checks=18 mismatches=0 v002_seen_writes=1`）。

## 副作用读者

`g_tf_diag_seen` 在 v002 的引用：33/36/39（定义与写入）、5112（`fz_prefilter` 读）、7735（`tf_diag_enter` 清零）；
v003 中引用数为 **0**。两个读者都已删除 → 未改 body 的调用者观察不到副作用差异。

## 依赖此 helper 的代表组合（已用 v003 新 body 重编）

| 调用者 | 处置 |
|---|---|
| `ds_scan` | V3.1 执行（三模式） |
| `hoist_try`（片段） | V3.2 执行 |
| `fz_next` | V3.3 执行 |
| `hoist_skipped` / `hoist_take` | V3.2 执行 |
| `sdx_walk` / `defer_try`（3 处）/ `frz_op` | **未执行**：这些 body 与 v002 逐字相同，且已证明 barrier 返回值全等、被删副作用无读者 → 调用点行为不变；其自身路径仍记 **SKIP**（V002-S 的 defer 主/Q、sdx 索引构造、frz 分支） |

## 不升级结论

上述等价性只说明"换 helper 不改这些调用点的判定"，不证明 `sdx_walk`/`defer_try`/`frz_op` 的路径被执行过；
V002-S 的 SKIP 边界继续保留。A2c 未开启。
