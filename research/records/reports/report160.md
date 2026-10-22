# report160 · A2b-fix：F1 mode gate + F2 去 latch（实现候选，未验收）

日期：2026-10-22 13:0x（本机）· HEAD `1408257`（未变）· 授权：主管 A2b-fix（30 分钟），实现方角色。
无 commit/push/PR；无注册/slots/observer/producer/hostbuild/执行/GPU/guest/gate/采样；profile/库/lock/chain 未动。
未改 v002 的 oracle/结果/snapshot 与 validator 目录；未自行宣布通过，未开启 A2c；route 仍 NO-GO。

## 0 结果

- **F1 已修**：`ds_scan` 的 `OP_TF_DIAG` 分支改为 mode-gated：仅 `tf_diag_barrier(h.op)` 为真才 `g_ds_why = h.op; return DS_USED;`，否则 `break` 走原 default 等价路径（OFF/INVALID 的 `[TF,SET_RT,END]` 恢复原判定）。
- **F2 已修**：删除 `g_tf_diag_seen`（声明/写入/reset）与 `fz_prefilter` 的全局 seen 拒绝分支；`tf_diag_barrier` 现在是**纯边界 predicate**，无扫描顺序依赖的历史状态；所有实际扫描点的局部 barrier 保留。
- **同类缺陷一并修正（请在验证时按 F1 原则复核）**：`hoist_try` 的 `case OP_TF_DIAG: return;` 原来也是无条件，OFF 下会改变 clear-hoist 决策；现改为 `if (tf_diag_barrier(h.op)) return; break;`，OFF 与原行为一致。
- 语法检查 rc=0 / 0 error；predicate smoke fails 0（命令见 §4）。**未做**独立验收、运行时、mutation。

## 1 SHA 与修改函数

pre-fix（本轮前）：`/path/to/external-drive/xc3/work/experiments/tf-diag-a2b/pre-a2b-fix/`
`nvn_mtl.m 64ba5054…`、`nvn_tf_diag.h 578957c7…`（`pre-a2b-fix.sha`）。

fix 后：

| 文件 | SHA256 |
|---|---|
| `nvn_mtl.m` | `2ba9af1a0f3821365e22a8d9ed6ad2350c89a0cd98f9464a369f7f6b844878fd` |
| `nvn_tf_diag.h` | `578957c7…`（未变） |
| `hle_nvn.c` / `nvn_obj.h` | `36863fc4…` / `8e9f93e2…`（未变） |

修改函数：`ds_scan`（F1）、`tf_diag_barrier`（F2，纯化）、`tf_diag_enter`（F2，去掉 seen reset）、`fz_prefilter`（F2，删除 seen 分支）、`hoist_try`（同类 F1 修正）。

## 2 F2 后“是否仍有成功路径绕过局部完整 scanner”审计（源码级，非运行验证）

- merge：`fuse_try` 粗筛 `fz_prefilter`；其索引路径在 `!g_sdx_ok` 时返回 1（放行粗筛），但真正的分步扫描用 `fz_next`，而 `fz_next` 遇 TF 即 `c->bad=1; return 0`，所有 caller 都是 `if (!fz_next(...)) return/break` → 跨 TF 的候选无法完成。**未发现绕过**。
- store：`sdx_walk` 遇 TF 置 `g_sdx_ok=0` → `sdx_decide` 返回 0 → full-store fallback；`xv_forward` 在 `!g_sdx_ok` 时 block。**未发现绕过**。
- hoist / defer / frz：各自带局部 gated barrier（`hoist_try`、defer 三处、`frz_op`）。**未发现绕过**。
- 仍无 boundary 的路径（已登记、未改）：并行预编译（TF 非 draw）。**列为 gap，未猜改。**

## 3 未做 / 边界

- F3（defer/store fallback 的独立补充 CPU 覆盖）与 F4（A2c 的 mode/lifetime 约束）按裁决属验证/后续实现阶段，本轮不做。
- 非阻塞 reason 冗余、通用 stream OOB 未修（已登记边界，不扩大 scope）。
- 未改 ON 规则、未移除其它局部 boundary、未新增全局历史状态。
- 语法/smoke 仅是基本检查，不构成验收；候选完成后冻结，V003 由主管制作快照交独立验证。

## 4 实际命令（可复现）

[Fenced excerpt omitted from the shareable research record.]
日志：`/path/to/external-drive/xc3/work/experiments/tf-diag-a2b/syntax-fix.log`、`smoke-fix.log`、`a2b-fix.sha`。
