# report159 · A2b-impl：TF 诊断 opcode 的扫描/优化边界（实现候选，未验收）

日期：2026-10-22 12:5x（本机）· HEAD `1408257`（未变）· 授权：主管 A2b-impl（90 分钟），实现方角色；与 V001 独立验证并行。
无 commit/amend/push/PR；未改 V001 candidate/validator 目录与测试；未向验证方预置答案。
未构建/链接/运行完整 host，未跑 shader/Metal/PSO/device/GPU/guest/gate/真实资源采样；route 仍 NO-GO。

## 0 结果

- 新增纯 predicate（header）与 11 处边界接线（nvn_mtl.m）；`OP_TF_DIAG` 在扫描/预测/合并/hoist/defer/frz 路径上一律作为**候选边界**。
- 语法检查（**不是** host build）：`clang -fsyntax-only -x objective-c -fobjc-arc`（profile/gen include）对 `nvn_mtl.m` **rc=0、0 error**、49 个既有 warning（无一条涉及 tf_diag）。
- 纯 predicate smoke：7 条断言全过（fails 0，ASan/UBSan）。
- 未做：独立反例/mutation 验收、运行时验证、A2c、真实 producer、observer。候选完成后已冻结 source。

## 1 变更与 SHA

| 文件 | 变更 | SHA256 |
|---|---|---|
| `nvn_mtl.m` | +194 行：边界 helper + 11 处接线 | `64ba5054280df310ec98f66485f7a4760dda47ab57ee558bb00f115bfca69701` |
| `nvn_tf_diag.h` | +`tf_diag_is_boundary()`（纯 predicate） | `578957c717cdd1a583ea1159295afeadf1bf96d4aa83550b145b3b5708aadf77` |
| `hle_nvn.c` | 未改 | `36863fc4cc56cba3fe969766c094a204e5640abe7d81b7b77ffba09a5b29258b` |
| `nvn_obj.h` | 未改 | `8e9f93e2742d0e634c2451c1f6c8583bc262c253c56679c3b87cb1c8efb3221f` |

pre-A2b 基线：`/path/to/external-drive/xc3/work/experiments/tf-diag-a2b/pre-a2b/`（`nvn_mtl.m` `bc0a2095…`、`nvn_tf_diag.h` `016cced4…` + `pre-a2b.sha`）。

## 2 predicate 与 helper（验证方可直接读取）

[Fenced excerpt omitted from the shareable research record.]
`tf_diag_barrier` 只读 opcode 与固定 mode；不读 payload / guest 内存 / shader / Metal 资源；不调用 `tf_diag_apply/enter/leave`；
`g_tf_diag_seen` 仅 ON 路径置位，并在 `tf_diag_enter()` 的顶层 submission 分支清零。

## 3 每项不变式 → 实际修改位置

| 不变式 | 修改位置（函数） | 行为 |
|---|---|---|
| B01 扫描不 apply | 全部改动点 | 只 `tf_diag_barrier()`（谓词）；扫描路径无 `tf_diag_apply/enter/leave`、无 emit |
| B02 前瞻不跨界 | `fz_next`（`c->bad=1; return 0`）、`hoist_skipped`、`hoist_take` | 遇 TF 即边界；所有 `fz_next` caller 都是 `if (!fz_next(...)) return/break`，即“无成功证据”；`bad` 供区分不完整 |
| B03 预测保守 | `ds_scan`（`case OP_TF_DIAG: return DS_USED`）、`sdx_walk`（`g_sdx_ok=0; return`） | 深度/模板保持；store 索引失效 → `sdx_decide` 返回 0 → 既有 full-store fallback；`sdx_seq` 后续对不上即失效，不错位静默 |
| B04 不吞事件 | `hoist_try`（`case OP_TF_DIAG: return`）、`hoist_skipped/take`、`defer_try` 主扫描/Q 复查/空 pass 内扫描（`reason=17; goto fail`）、`fz_prefilter`（`g_tf_diag_seen → return 0`）、`frz_op`（`return 0` 使事件进主 case） | 候选区间不跨 TF；真实 loop 不把 TF 当 skip 项 |
| B05 helper 纯 | 见 §2 | 仅 opcode+mode；无 payload/guest/shader/Metal；OFF 时谓词恒 0，优化决策不变 |

另：`OP_TF_DIAG < 64` 静态断言（cmdstat/allocprof 的 64 宽数组无需扩容；本轮未改统计代码）。

## 4 未完成 / blocked（不猜）

- **并行预编译**：未改。TF 不是 draw，现有路径不把它计入 draw；没有可证明需要的边界（列为“无需改动，待验证方判断”）。
- **`fz_probe_cov2` 及其 merge caller**：未单独加 guard；它们经 `fz_next` 消费流，已被 B02 覆盖（`fz_next` 返回 0 → caller 停止）。若验证方认为需要独立 guard，请指派。
- **`mtl_sub_index`**：未改；其索引由 `sdx_walk` 构建，已由 `g_sdx_ok=0` 失效。
- **observer / 7 接口安装 / 真实 producer**：A2c 未授权，未做。
- **运行时/反例/mutation 验收**：按分工不做；本文所有结论仅来自源码修改、语法检查与 predicate smoke。

## 5 验证方入口

- 纯谓词：`dm/gfx/nvn/nvn_tf_diag.h` → `tf_diag_is_boundary`
- 边界 helper：`dm/gfx/nvn/nvn_mtl.m` → `tf_diag_barrier`（`grep -n tf_diag_barrier` 得 11 处调用点）
- 语法检查命令（可复现，非 host build）：
  `clang -fsyntax-only -x objective-c -fobjc-arc -I dm/gfx/nvn -I dm/gfx/nvn/include -I dm/host -I dm -I <profile> -I <gen> dm/gfx/nvn/nvn_mtl.m`

## 6 边界与状态

- 候选 source 已冻结；未改 V001 的 oracle/结果，未新造 accepted/confirmed facts。
- OFF/INVALID：谓词恒 0，既有 stream 与优化决策不变（语法层面）；实际行为未运行验证。
- `tf_diag_seen` 是 ON-only 诊断标志，不参与 OFF 决策。
- 真实 GS/TF route 继续 NO-GO；无自动下一项。
