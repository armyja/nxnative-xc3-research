# report156 · TF 状态关联观测设计（只读/CPU，不实现）

日期：2026-10-22 11:1x（本机）· HEAD `1408257`（未变）· 授权：主管 45 分钟只读“TF 状态关联观测设计”；
无实现/build/translate/host/Metal/PSO/GPU/guest/gate/采样；冻结 production 脏源码、profile/facts/库/lock/chain。

## 0 结论

1. **录制期 active 布尔不可用于归属**：命令流可被 `CALL` 多次、复制、原地重录，录制顺序 ≠ 回放顺序。
2. **唯一可靠位置是内联在录制流里的 TF 事件**（新诊断 opcode），回放时按位置应用到影子状态，观测点在 `draw()` 内。
3. 这需要改 production 录制/replay 格式（新增 opcode + 7 个 TF 函数的录制 + replay case + 三个前瞻 walker 的忽略规则）→ **本轮 NO-GO**，先交设计。
4. 观测只表达**意图/replay 状态**，不执行 TF 写入，不构成 TF 实现。

## 1 真实路径 anchors

| 环节 | 位置 |
|---|---|
| 录制入口 | `REC(c,OP,T)` hle_nvn.c:762 → `rec()`（hle_nvn.c:750 附近）写 `op_hdr`+payload 到 guest command memory / host segment（`cmd_new_segment`、`hostseg_*`） |
| Begin/End | hle_nvn.c:714 写 `OP_BEGIN`，返回 handle = **该记录地址**；:720 写 `OP_END` |
| Copy/Call | hle_nvn.c:727 写 `OP_CALL(handle)`；:1676 `CallCommands` 与 Copy 同实现 |
| opcode 枚举 | nvn_obj.h:96-107（无诊断/marker op，`OP_COUNT_` 收尾） |
| 回放 switch | nvn_mtl.m:7700+：`OP_END` :7711、`OP_BEGIN` :7717、`OP_CALL` :7719（跳入 handle 的 OP_BEGIN）、`OP_JUMP`、`OP_DRAW` :7801 |
| 前瞻/扫描（**不得**更新状态或 emit） | `fz_next` :4042、`ds_scan` :4113、`sdx_walk` :4491（各自处理 OP_CALL，深度上限 8） |
| 条件渲染 | `g_rc_skip` :468（置位 :7731-:7734）；OP_DRAW 在 skip 时直接 `break` :7801 → 被 skip 的 draw 不执行、不产生观测 |
| TF API | nvn_protos.h:359/360/371-375（7 个）；nvn_slots.tsv:386-402 全部 flag 0 → 当前是未实现 stub（hle_nvn.c:54 打印 x0..x2），**既不录制也不回放** |

## 2 录制 vs 执行（为什么录制期布尔不成立）

- `handle` 是录制时 `OP_BEGIN` 的地址：同一 handle 可被 `CALL` 多次（每次回放重放同一段流），游戏也可在后续帧**原地重录**（地址复用）。
- 一个 CB 可 `CALL` 另一个 CB 的记录；同一记录可在不同 CB、不同顺序被调用；多个 CB 顺序提交。
- 录制期的 CPU 调用顺序**不携带**“第 N 次 `OP_DRAW` 时 TF 是否 active”的信息；旁路 shadow stream 同样没有位置。
- 因此必须让 TF 事件成为**被回放字节流的一部分**；届时顺序天然正确，无需 handle 身份匹配。

## 3 最小状态（不是单个 tf_addr）

- `tf_bound[i] = {addr:u64, size:u64, known:bool}`：来自 `Bind(index,addr,size)` / plural `Bind(first,n,ranges[])`；命名 **bound range**。
- `tf_begin_addr` / `tf_end_addr`：`Begin/End` 的 `NVNbufferAddress` 实参；`tf_draw_addr`：`DrawTransformFeedback` 实参。
  **与 bound range 分开命名**，不假设同物（原型 nvn_protos.h:359-375；消费者语义未证）。
- `tf_active ∈ {unknown, inactive, active}`；`tf_pause ∈ {unknown, running, paused}`；`tf_events:u32`；`tf_epoch:u32`。
- 语义：Bind → 只改 bound；Begin → active；End → inactive；Pause → paused；Resume → running；
  `DrawTransformFeedback` → 本次 draw 视为 TF 消费（是否等价 active 未证，记 unknown）。
- **unknown 规则**：初始 unknown；任何未覆盖 API 被调用（DrawTransformFeedback / Pause / Resume / plural Bind）→ unknown；
  首个 TF 事件不是 Bind → active 但 bound unknown；`OP_CALL` 深度超限/无效 handle → unknown；状态缺失或 epoch 过期 → unknown。
  绝不把“没见到 Begin”当作 inactive。

## 4 目标 95bf draw 的关联

- 观测点就在 `draw()` 内（`kd_res_line` 已在那里，boot.log 的 `[gs-res]` 行即由它输出）→ 回放到该 draw 时直接读当前 TF 影子状态；
  不需要用 frame/pass 反查，也不依赖录制期时间戳。
- 记录新增字段（默认关闭）：`tf=unknown|inactive|active`、`tf_bound0=addr/size`、`tf_begin_addr`；仅当影子状态存在时写出。
- 语义边界：`inactive` 只表示“截至该 draw 未发生 Begin”，不表示“TF 未写过任何东西”；`tf=unknown` 时 gate 必须拒绝。

## 5 off / inert 与扫描

- 默认关闭：TF 函数保持现有 stub（不录制、不 replay），字节流与今天完全一致；原 replay 行为不变。
- 开启时：只录制 TF 事件 + replay 中更新影子状态；**不改变 GPU 工作**，不改变任何既有 opcode 语义。
- 三个前瞻 walker（`fz_next`/`ds_scan`/`sdx_walk`）必须显式忽略新 opcode：不更新 TF 状态、不 emit、不计入 draw/pass。
- `g_rc_skip` 只作用于 draw/clear；TF 状态 opcode 不 skip（状态表达意图），但被 skip 的 draw 不产生观测，**不能**当作“active/inactive 已执行”的证明。

## 6 影响与 NO-GO

- 需要：5–6 个新诊断 opcode（Bind / BindPlural / Begin / End / Pause+Resume / DrawTF）、`OP_COUNT_` 扩展、
  hle_nvn.c 7 个 TF 函数的录制路径、nvn_mtl.m replay case、三个 walker 的忽略、observer 字段（默认关）。
- 影响面：所有调用 TF 的标题（默认关闭时零影响）；开启时每事件 ~16–24 B 命令内存（XC3 本帧 3 事件 ≈ 72 B/帧），
  命令内存 sizing 与 host segment 机制已存在（注释已说明“our records are larger than real device commands”）。
- 因为要改 production 录制/replay 格式、可能影响其它标题，**判定 NO-GO**：本轮不绕过、不实现；需单独授权。

## 7 CPU 未来验收表（仅设计，不执行）

| 用例 | 期望 |
|---|---|
| 同一 CB 内 Begin/End 多次 | 每次回放独立应用，无残留 |
| 记录 A 被两个 CB 各 CALL 一次 | 两次回放各自得到相同 active/inactive |
| CopyCommands 复制 handle 到另一 CB | 复制后回放同样生效 |
| Bind 多 slot（index 0/1 + plural） | `bound[i]` 各自记录，addr/size 不混 |
| Begin 的地址 ≠ bound 地址 | 分开命名，不互相推断 |
| 无任何 TF 事件即到 95bf draw | unknown → gate 拒绝 |
| Begin 后无 End 直到 present | active（可能泄漏，标注） |
| 游戏调用 DrawTransformFeedback | unknown（未覆盖） |
| `g_rc_skip` 下 TF 事件 + draw | 事件仍应用；draw 不观测 |
| 前瞻 walker 遇到新 opcode | 不更新状态、不 emit |
| env 关闭 | 录制流与今天逐字节一致（用 SHA 比对验证） |

## 8 边界

- 只读/CPU；未实现、未 build、未跑 guest；未扩 route、未重跑 synthetic。
- 下一步（需 owner 新授权）：要么批准最小 opcode 方案（先做 off/inert + 字节流不变验证），要么改选“合法资源生命周期”作为最小阻塞任务。

---

## 9 修订版（替代 §3/§4 末段/§5 的相关规则；旧文保留作历史）

主管 review 判定：状态表自相矛盾、扫描覆盖未穷尽、off 零影响只是验收目标 → 本轮继续 **NO-GO**，未授权 production/host/build/guest。

### 9.1 撤回两条规则

- **撤回“首个非 Bind 事件 → active”**：End / Pause / Resume 语义不同（见 9.2），不能由任一非 Bind 事件推出 active。
- **撤回“inactive = 未发生 Begin”**：它与初始 `unknown` 直接矛盾。`inactive` **只能**来自“被完整观测的有效终止事件”（Begin→End 配对），或将来被证明的 reset 语义；
  **绝不由事件缺失推导**。

### 9.2 状态与转移（A ∈ {U,I,A}，P ∈ {U,R,P}；初始 (U,U)）

| 事件 | 入口 | 出口 | 说明 |
|---|---|---|---|
| `Bind(index,addr,size)` / `BindPlural(first,n,ranges)` | 任意 | (A,P) **不变** | 只更新 `tf_bound[i]={addr,size,known}`；不构造 active |
| `Begin(addr)` | (U,*) / (I,*) / (A,R) | (A,R) | `tf_begin_addr=addr`；“Begin 蕴含 running”是**命名假设**，未证 |
| `Begin(addr)` | (A,P) | (U,U) | paused 中 Begin 视为异常序列 → invalid |
| `End(addr)` | (A,R) / (A,P) | (I,U) | 唯一的 inactive 来源；`tf_end_addr=addr`（与 bound 分开） |
| `End(addr)` | (U,*) | (U,U) | 无配对 Begin，**不可**推出 inactive |
| `End(addr)` | (I,*) | (U,U) | End without active → invalid |
| `Pause(addr)` | (A,R) | (A,P) | — |
| `Pause(addr)` | (U,*) / (I,*) | (U,U) | 不构造 active（不 invent） |
| `Resume(addr)` | (A,P) | (A,R) | — |
| `Resume(addr)` | 其它 | (U,U) | invalid |
| `DrawTF(prim,addr)` | 任意 | (U,U) | 语义未证 → **opaque**，记录但不推断 |
| 未覆盖 API（7 个中未实现的种类） | 任意 | (U,U) | 记录 opaque 事件并 invalidate |
| invalid（坏 handle / addr 溢出 / index 负 / depth 异常 / epoch 失配 / 流在关闭时录制） | 任意 | (U,U) | 同时 `bound.known=0` |

“7 API 全拦截 ≠ 全部语义已知”：未支持种类一律 opaque + invalidate。

### 9.3 状态所有权（回放上下文）

- 状态属于**实际回放执行上下文**，不是“录制期每 CB 一份”。
- **不得**在 `OP_BEGIN`、`OP_END`、每帧入口、每 CB 入口无条件清零：`OP_BEGIN` 在 replay 里就是 `break`（:7717）；`OP_END` 只结束当前 exec 层（:7711）。
- 嵌套 `OP_CALL`（:7719）**继承调用者当前状态**；返回后继续使用被调用列表修改后的状态（inline 语义）。
  “子列表合法改变是否影响 caller”列为**需证**（NVN CallCommands 语义 + 目标 API 消费者），未证前不据此放行 gate。
- 提交边界（新 submission）**置 unknown，不置 inactive**；“submission 开始即 reset”本身也是需证假设。
- 因此“同一被调用列表调用两次结果相同”**不成立**：输出依赖入口状态；验收要比 `(entry, exit)` 对，不比绝对输出。
- 无效 handle / 递归深度：实际 `mtl_exec` 是 C 递归且**没有校验/深度门**（`g_ret` 16 只是前瞻返回栈，walker 的 8 层是前瞻上限）。本设计**不声称已实现拒绝**；异常只记 opaque/invalidate。

### 9.4 CopyCommands 与方案定位

- `nvnCommandBufferCopyCommands` 当前实现是 `OP_CALL(handle)`（hle_nvn.c:727，:1676 注释明确 CALL/COPY 同处理），**不是复制字节**；名称与语义须分开表述。
- 内联事件是本项目**最直接、最稳定**的方案；带位置/版本/生命周期的 sidecar 理论上可行，但本项目无实现、复杂度更高。§2 的“唯一可靠”收窄为“本项目内最直接”。

### 9.5 扫描/优化影响清单（完整化，不写改动）

| # | 位置 | 用途 | 新状态 opcode 的处置 |
|---|---|---|---|
| 1 | nvn_mtl.m:7698 主 switch | 真执行 | **apply**；注意 `default: break`（:7819）会静默跳过，必须显式 case |
| 2 | :7719 `OP_CALL` | 递归 exec | **inherit**，不清零；无深度/无效 handle 校验（见 9.3） |
| 3 | :7711 `OP_END` | 结束当前 exec 层 | 不清零；仅 submission 边界置 unknown |
| 4 | :4042 `fz_next` | 前瞻游标 / pass 合并证据 | 透明跳过 + **合并 barrier** |
| 5 | :4113 `ds_scan` | 深度/模板预测 | 透明跳过 |
| 6 | :4491 `sdx_walk` | seq/事件索引、延迟释放 | 透明跳过（不产生 seq 事件） |
| 7 | :5002 defer 收集 | 延迟绘制判定 | **defer barrier** |
| 8 | :5053-:5066 defer 复查 | 同上 | barrier |
| 9 | :5273 / :5906 / :5983 其它扫描 | 绑定/资源跟踪 | 透明跳过；结论若跨 TF 边界 → barrier |
| 10 | `hoist_take`/`hoist_skipped` :4280/:4117/:5003/:7708 | pure-clear 提升 | **hoist barrier** |
| 11 | `frz_op` :7703 | 帧冻结/合并 | **barrier**（区间终止） |
| 12 | hle_nvn.c cmdstat `op_n[64]`/`op_b[64]`、`cs_op` 守卫 | 统计 | 需扩容或独立桶，否则静默丢失 |
| 13 | :7707 allocprof `g_ap_bytes[prev]`（prev<64） | 分配归因 | 同上 |
| 14 | 并行预编译 :3506/:4314 | 按 draw 预编译 | TF op 不计入 draw |
| 15 | `OP_COUNT_` | 枚举哨兵 | 已确认无 `[OP_COUNT_]` 数组依赖；仅编译期边界 |

**最小 fail-closed 策略**：默认 off（不录事件、不改 exec）；开启时只 apply 状态，且上表所有优化/预测/合并/延迟点在遇到状态 opcode 时**终止当前区间**（barrier），不试图证明安全；
状态为 unknown 时 gate 拒绝。不在 production 加校验，只在观测层记录异常。

### 9.6 录制开关与流生命周期

- 开关**进程启动时固定**；off 时**不录事件**（目标，非已证事实）。
- 若一段流在 off 期间录制、或在另一种 env/回放生命周期下录制 → 事件可能缺失 → 该流的状态一律 **unknown**；**不得**用 `OP_BEGIN` 补 inactive。
- 输出记录标注：**observed replay intent**（观测到的回放意图），不是 GPU TF 实现、不是 TF 内容。

### 9.7 CPU 模型验收 case（纯 CPU，可选，不跑 GPU/repo）

| case | 序列 | 期望 |
|---|---|---|
| C1 | 初始 → 95bf draw | (U,U) → gate 拒绝 |
| C2 | Begin → draw → End | (A,R) → (I,U) |
| C3 | End（无 Begin） | (U,U)，**不是** I |
| C4 | Pause（无 Begin） | (U,U) |
| C5 | Begin→Pause→Resume→End | (A,R)→(A,P)→(A,R)→(I,U) |
| C6 | 同一列表 CALL 两次，entry U / 第二次 entry I | exit U / exit U（End 在 I 入口无效）；体现“输出依赖入口” |
| C7 | DrawTF 或未覆盖 API | opaque → (U,U) |
| C8 | off 期间录制 | 无事件 → (U,U)，不补 inactive |
| C9 | 坏 handle / addr 溢出 | (U,U) 且 bound.known=0 |
| C10 | `g_rc_skip` 的 draw | 不观测；状态事件仍 apply |
