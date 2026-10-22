# TF-DIAG A2b 独立验证报告（V002）

仅验证，未改实现；无 commit/push/PR；未触碰 candidate / repo / 实现方测试。
75 分钟 CPU 预算内完成可覆盖项；不可覆盖项明确 SKIP（见 §5）。

## 0. 结论摘要

| 项 | 结果 |
|---|---|
| 身份（manifest + 7 文件 + vs-v001.diff SHA） | **全部匹配**；仅 `nvn_tf_diag.h`、`nvn_mtl.m` 相对 v001 变化，其余 5 文件 hash 相同 |
| CPU 断言 | **31 PASS / 1 FAIL**（plain 与 ASan/UBSan 结果一致） |
| 静态放置检查 | **20/20 PASS** |
| 独立变异 | **3/3 行为被抓**（全部 `compile_rc=0`） |
| B01 | PASS（predicate 无 payload/无 shadow 副作用；扫描不改状态） |
| B02 | PASS（游标 false 不被当流末；hoist skip 不吃 TF；caller 全部停止） |
| B03 | PASS（TF ⇒ DS_USED 保守 keep；索引失效 ⇒ 全量 store） |
| B04 | **FAIL**（`ds_scan` 的 TF case 未做 mode gate：OFF/INVALID 下同一流结论与 pre-A2b 不同） |
| B05 | PASS（含 F2 生命周期/顺序性发现） |
| B06 | PASS（64 桶无需扩；precompile 不把 TF 当 draw/state） |
| 继承 | V001 的 F1–F4 仍在（模型/消费端与 leave 守卫未变），标 **parent-inherited** |

## 1. 身份

- manifest `…/v002/candidate.json` SHA256 `4cf79789…b5f2`（匹配）
- diff `…/v002/vs-v001.diff` SHA256 `22f7cbbb…399d`（匹配）
- 7/7 snapshot 文件匹配 manifest；相对 v001 仅 2 文件变化：
  `nvn_tf_diag.h` `578957c7…aadf77`、`nvn_mtl.m` `64ba5054…a69701`
- 其余 5 文件 hash 与 v001 相同 ⇒ V001 对 obj/hle/protos 的结论继承有效
- 未读可变 repo 作为候选身份；未写 candidate

## 2. 方法（提取真实 body，非重写算法）

从冻结 snapshot 逐字提取（行号 + SHA 见 `evidence/provenance.json`）：

| 提取物 | 行 |
|---|---|
| 模型 + `tf_diag_is_boundary` | `nvn_tf_diag.h` 全文 |
| A2b 头部（barrier / `g_tf_diag_seen` / 64 断言） | `nvn_mtl.m` 35–44 |
| `hoist_skipped` + skip 列表 | 4055–4058 |
| `fz_cursor` + `fz_next` | 4059–4081 |
| `hoist_take` + `ds_scan` | 4129–4155 |
| A2a consumer（未变，用于证明扫描不改 shadow） | 7725–7755 |

验证方自写：流构造器、最小 `ds_st` stub（仅 `dt/dw/st`，位宽取自 nvn_obj.h）、
`dm_tf_diag_get_mode` stub、两条 caller 模式（分别照 `fuse_try` 与 `pso_predict_rest` 的
`if (!fz_next(...)) return;` / `break` 结构转写）。**没有**重写 fuse/defer/sdx 算法。

命令：`./build.sh` → `./build/v002_tests`；`python3 src/static_checks.py`；`python3 src/mutate.py`。

## 3. 逐契约

**B01 PASS** — `tf_diag_is_boundary(op, tf_op, mode)` 只比较 opcode 与固定 mode，签名不接收 payload；
ON+TF → 1 并置 seen；非 TF → 0；OFF/INVALID → 0 且 seen 不变。调用 barrier 前后 `tf_diag_state` 逐字节相同、
events/copies 不变；对照：只有真正 `tf_diag_case()` 调用才推进 shadow。重复扫描判定一致。
（F2 说明 seen 的 latch 语义。）

**B02 PASS** — TF 记录即使被放进 hoist skip 列表也不会被判 skipped，`hoist_take` 拒绝并保持列表不变；
`fz_next` 遇 TF 置 `bad=1` 并返回 0，不把 TF 当普通 op 返回；同一流去掉 TF 时正常返回两条 draw。
两条 caller 模式均在 false 处中止：`fuse_try` 式 `return` 不越过边界、`pso_predict_rest` 式 `break`
不会把 TF 当 draw 或对其 `state_op`。`frz_op` 的 guard 是函数第一条语句、之前无任何副作用（源码锚点）。

**B03 PASS** — `ds_scan` 遇 TF 立即 `g_ds_why=OP_TF_DIAG` 且返回 `DS_USED`（keep）；同一流无 TF 时走到
SET_RT 返回 `DS_FREE`（对照证明差异只来自 TF）；8 字节名义 TF 记录同样保守（opcode 驱动，非 size 驱动）；
CALL 子列表内的 TF 把 USED 传播给调用者；hoist skip 列表无法把 TF 从 lookahead 中隐藏。
`sdx_walk` 遇 TF 先 `g_sdx_ok=0` 再返回；`sdx_decide` 索引不可用返回 0，`sd_finish` 走 `sd_need(...,6)` →
全量 store（源码锚点，见 §5 SKIP）。

**B04 FAIL（1 项）** — 可执行反例：OFF 模式下，流 `[TF, SET_RT, END]` 的 `ds_scan` 实际返回
`DS_USED(1)`；pre-A2b 的同位置 body 无 `OP_TF_DIAG` case，会 `default: break` 继续到 SET_RT 返回 `DS_FREE(0)`。
即新增 `case OP_TF_DIAG` **没有 mode gate**，OFF/INVALID 下同一流会改变既有优化决策（方向保守：多 store）。
合同明确要求不能用“off 不会有事件”代替测试，故记 FAIL；当前无 producer，生产不可达。
其余新路径均经 `tf_diag_barrier` 的 mode 门控，OFF 下与 pre-A2b 等价（hoist 成员语义、游标不停止均已测）。

**B05 PASS（附 F2）** — 顶层 `tf_diag_enter` 会把 seen 清零；提交内扫描置位后为 latch，后续非 TF 扫描无法清除。
发现：`mtl_sub_index`（`hle_nvn.c:1062`）**先于** `mtl_exec`（1066）执行，其 sdx 行走产生的 seen 标记在
`tf_diag_enter` 处被清掉；随后执行期 lookahead（`pso_predict_rest` 等）产生的标记则保留到提交结束。
同一流、同一提交的 `fz_prefilter` 结论因此可能取决于“是否发生过执行期 lookahead”，属顺序相关（见 F2）。
未发现“依赖历史全局值的错误放行”：索引失效后 `g_sdx_ok=0` 不被重置，规划扫描仍会在真实 TF 处中止。

**B06 PASS** — 快照保留 `_Static_assert(OP_TF_DIAG < 64)`，未扩桶；OP_TF_DIAG=42 在 64 宽桶内。
parallel precompile 走 `fz_next`，遇 TF 直接 break：可执行用例证明 TF 之前不会计 draw、不会 `state_op`。

## 4. 反例 / 发现（只报不修）

**F1（B04，low，新引入）`ds_scan` 的 TF case 未 mode-gated**
- 最小输入：`[OP_TF_DIAG, OP_SET_RT, OP_END]`，mode=OFF。
- expected：`DS_FREE(0)`（与 pre-A2b 一致）；actual：`DS_USED(1)`，`g_ds_why=42`。
- anchor：`nvn_mtl.m:4145`。影响：OFF/INVALID 下多 store（保守方向），当前无 producer 不可达；
  若将来在 OFF 下注入/回放含 TF 的流，优化决策会与基线不同。

**F2（B05，low/info，生命周期+顺序性）`g_tf_diag_seen` 的 mark 在顶层 enter 处被无条件清掉**
- `mtl_sub_index` 先跑、`tf_diag_enter` 后跑 ⇒ 索引扫描的标记必然丢失；执行期扫描的标记才生效。
- 后果：同一提交内 `fz_prefilter` 的“无候选”结论依赖执行期是否发生 lookahead（例如 PSO 是否命中缓存），
  是**顺序/时序相关**的保守拒绝，不是错误放行。anchor：`nvn_mtl.m:36-41, 5112, 7735`；`hle_nvn.c:1062,1066`。
- 若 A2c 要把该 flag 当作提交级属性，需要显式定义 mark 的产生/清除点。

**F3（B02/B03，info，覆盖边界）** `frz_op` 主体、`defer_try`/`defer_q_*`、`sdx_decide`/`sd_finish` 的
Metal/账本部分**未执行**，只做源码锚点核对（guard 位置、返回方向、fail 路径）。不据此声称这些路径行为已验证。

**F4（parent-inherited，来自 V001）** V001 的 F1（mode 中途切换致 depth 泄漏）、F2（`BAD_KIND` 死值）、
F3（size 检查非内存边界）、F4（sticky 守卫重复）在 v002 中代码未变，结论继续有效：
`dm_tf_diag_set_mode` 仍只有 1 处定义、无调用；`tf_diag_leave` 仍被 `tf_diag_on()` 守卫（`nvn_mtl.m:7738`）。

## 5. 未覆盖 / SKIP（不许下结论的地方）

- 未执行 `mtl_exec`、融合规划 `fuse_try`、defer、sdx 账本、`frz_op`、`state_op`、任何 Metal/PSO/GPU 路径；
  这些只有源码锚点证据（§3 已逐条标注）。
- 15 处 scanner/hoist/defer 站点未逐处审计；本报告只覆盖 A2b diff 中的 9 个 `tf_diag_barrier` 调用点
  及 2 个直接 `case OP_TF_DIAG`（ds_scan / hoist 候选扫描）。
- 未验证真实 producer / 真实 replay 流；所有流均为验证方构造。
- 64 桶只验证“无需扩 + op<64 断言 + allocprof 桶 `prev<64` 守卫”；未执行统计输出。
- 通过 CPU 验证不升级 TF/NVN/GPU 语义；A2c/真实 producer 未授权；**route 继续 NO-GO**。

## 6. 交回与冻结

- 结构化结果 `result.json`；证据 `evidence/`（含 `sha256sums.txt`）。
- 仅写 `v002/validator/`；未改 candidate/repo/实现方产物；无 commit/push。
- 状态：冻结等待 review / 派修裁决。
