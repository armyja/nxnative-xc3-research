# report155 · 95bf-only 实验 route：最小可实现契约与拒绝条件（设计，未执行）

日期：2026-10-22 10:5x（本机）· HEAD `1408257`（未变）· 授权：主管 60 分钟只读/CPU 设计；**无 build/translate/Metal/PSO/GPU/host/guest/gate/采样**。
未改 production 脏源码、profile/facts/库/lock/chain；未新增脚本（仅 CPU 算术）。

## 0 结论先行

- **GO 的部分**：不猜 contents 的**接线设计**成立——动态绑定真实 texture（不造内容、不解引用 guest raw 地址）在生产路径上已有入口。
- **NO-GO 的部分**：本轮**不能**定义一个“既不猜 contents、又不跳 GS/TF 语义”的可执行 route。GS 无执行路径（可后续 build），**TF 没有可判状态**（本轮不可判定）。
- 因此本轮产物是契约+拒绝条件+GO/NO-GO 表；**最小独立阻塞任务 = TF 状态关联观测设计**（§5）。

## 1 分层：接线所需 vs 数值/像素验收所需

| 层 | 需求 | 现状 / 锚点 | 判定 |
|---|---|---|---|
| A 接线 | 资源身份（tid/sid/serial） | `mtl_reg_tex` nvn_mtl.m:2957（调用点 hle_nvn.c:221/226）、`mtl_reg_samp` :2977（hle_nvn.c:232）、`treg_t` :2941 | 可用 |
| A 接线 | handle 解析（tid 低 20 位 / sid 高 20 位） | `tex_fast_rid` :3058、`h_ser` :4463、`ubo_handle` :3785 | 可用 |
| A 接线 | 有效 view | `tex_fit` :3064（类型不符时建 alt view）、view cache 以 `view_ser == g_ser_gen` 且 `!view_dirty` 判定 :3058 | 可用，但有代际问题（见缺口） |
| A 接线 | AB 绑定 | `encode_args_(encoder, sh, nvn_stage, metal_vertex)` :3799——按 stage 编码 texture/sampler/UBO 槽 | 可用但仅 render encoder 路径 |
| A 接线 | lifetime/pin | `use_rec`（纹理/缓冲登记 residency）、`defer_obj_unref`/延迟释放、`treg_drop_pool_views` :2950 | 部分可用（跨 pass 未证） |
| A 接线 | limits/预算 | §3 | 可算 |
| A 接线 | 同步 | fixture 要求 `MTLHazardTrackingModeTracked`（execute_vsgs.m:99）；生产无显式声明 | 缺口 |
| A 接线 | TF 是否可安全拒绝 | 无状态（stub 只打印 x0..x2；Bind 的 size 形参存在但未记录） | **缺口（阻塞）** |
| B 验收 | 真实 texel T 内容 | 未观测（报告153 §9.2 条件未证） | 阻塞（需新授权） |
| B 验收 | 参考画面/像素 | 无 real-frame oracle | 阻塞 |
| B 验收 | GS 输出数值 | 只有 SASS 静态依赖式；无执行 oracle | 阻塞 |

**关键**：T 未知只阻塞 B 层。A 层可以设计成“动态绑定游戏注册的那张纹理”，前提是 §2 的拒绝条件成立（不触发 dummy、不解引用 raw 地址）。
生产路径现有的 `dummy_tex` :3697 / `dummy_samp` :3730 与 `encode_args_` 内 `if (!t) { t = dummy_tex(...); tdummy = 1; }` :3891、`USE(ss ? ss : dummy_samp(), ...)` :3874
会**静默伪造**资源——实验 route 必须把这两处改成“失败即终止”，否则“动态绑定真实 texture”不成立。

## 2 exact route gate（拒绝条件）

范围：仅 `d1657e5077b26d1d`(VS) + `95bfab6122539993`(GS) + `2e16c536b845ea0e`(PS)，`prim=0`(Points)、direct、1 instance。
其它 GS/draw 保持现有 guard（不匹配即不进入本 route）。

必须成立才允许进入（任一不成立 → **终止实验**，不允许静默回退到 VS/PS-only）：
1. 三 key 精确匹配 + `gs_present=1`；`ps_style=_b`。
2. stage2 资源：UBO0 / tex0 / 合并 sid 全部来自**游戏注册**（`g_treg[tid].ok`、`g_sreg_ok[sid]`）；任一路径落到 `dummy_` 即终止。
3. view：`tex_fit` 或 base view 得到 64×36、baselevel 0、swizzle 未改；否则终止。
4. topology/prim：`prim=0`、`OutputTopology=7`、`MaxOutputVertexCount=4`；否则终止。
5. limits：§3 全部通过；任一 buffer 超限即终止。
6. TF：**可判 inactive** 才允许；当前无法判定 → 见 §4。
7. 真实 stage2 资源与 PS 原资源/RT **不被 test PS 替换**；PointSize 编译 flag 走独立 manifest（不混入生产 map）。

## 3 CPU 资源预算（公式 + 溢出检查）

输入：`P=2304` 点 × `I=1` instance → `N = P·I = 2304` invocation；`M=4` 输出顶点/invocation（SPH）。

| 量 | 公式 | 值 | 检查 |
|---|---|---|---|
| dispatch | groups `{64,36,1}`、threads `{1,1,1}` | 2304 | 每维 ≤1024 ✓；threads/group ≤640 ✓ |
| 输出顶点 | `V = N·M` | 9216 | — |
| VB 字节 | `V·5 words·4` | 184,320 | ≤256 MiB ✓；5 words 是冻结 16×16 fixture 的 stride，**真实 GS 输出 stride unknown** |
| IB 条目 | `N·5`（4 index + `0xFFFFFFFF` restart） | 11,520 | u16 需 `9216<65536` ✓；fixture 用 u32（46,080 B） |
| IB 字节 | `N·5·4` | 46,080 | ✓ |
| TRB | `N·4`（fixture 1 invocation→4 B） | 9,216 | 假设，未证 |
| guard | 每 buffer `2×256`（`G=256`, execute_vsgs.m:8/79） | ~1.5 KB | — |
| 合计 | — | ≈240 KB | 冻结 16 MiB 预算（BUDGET :8）充足 |

溢出/对齐：`newBufferWithLength` 256 MiB 上限；texture-buffer 视图 `newTextureWithDescriptor:offset:bytesPerRow:` 要求 offset 4 字节对齐（fixture R32Float/bytesPerRow 4）；
`submit_contract16`（`harness/submit_contract_16.h`，负例见 `test_contract16.c`：max_threads 255、dim 15、groups 2、threads 8/0 全部拒绝）在生产侧无等价检查 → 需新增（本轮只设计）。

**重绑（VS→GS→passthrough）**：
1. VS kernel：输入 vb_info（AB idx0），输出 vertex_output（AB idx1）。
2. GS kernel：输入 vb_info（idx0）/cbuf（idx1）/vertex_output（作为 texture，idx2）/sampler（idx3）；输出生成的 VB/IB/TRB（texture buffer）。
3. passthrough draw：把生成的 VB 绑到 **idx0** —— 即 b1→b0 的重绑；生产 `encode_args_` 一次性编码 VS/PS 参数，没有中间 compute pass、没有分离 AB、也没有显式 hazard 声明（差异点）。

**还需要实测的字段**（本 route 用到但现有记录没有）：真实 PS 资源全量（现只有 tex reg1 tid782 640×360 fmt115、samp reg1 sid257、cb reg0）、raster 状态（cull 0/blend 0xff/wm 0xffffffff/scissor）、attachment 格式与 depth（`df=8` 含义未证）、`R.rt.color[0]` 的 Metal 格式。

## 4 GO / NO-GO 证据表

| 要求 | 现状 | 判定 |
|---|---|---|
| 不猜 contents | 动态绑定真实 texture 可行（A 层入口存在，需去掉 dummy 回退） | **GO**（设计） |
| 不跳 GS 语义 | shader map 无 95bf；Metal 无 GS 路径；synthetic geometry-as-compute 脚手架存在但未接入生产 | **NO**（需 build/translate，本轮禁止） |
| 不跳 TF 语义 | TF 无可判状态（stub 只打印；`Bind` 的 `size_t` 形参未记录；Begin/End 无 size） | **NO-GO** |
| 安全资源路径 | 生产有 dummy 静默回退 :3874/:3891 | 需改；本轮只设计 |

**结论：NO-GO**（无法定义既不猜 contents、又不跳 TF/GS 语义的可执行 route）。
**最小独立阻塞任务（下一轮唯一目标）**：TF 状态关联观测设计——
- 需要的**最小状态**：per-command-buffer `{tf_addr, tf_size, active}` 锁存；`Bind` 的 `size_t` 在第 4 个实参（当前 stub 未打印）；`Begin/End` 记录 draw 序号/pass id，用以回答“draw N 时 TF 是否 active”。
- 不实现 TF 语义、不改 guest 行为、不产生新 GPU 工作；产出是对 gate 可判性的最小增量。
- 次选（若 TF 被主管判为不需要）：合法资源生命周期（view cache 代际 vs 跨 pass pin）。

## 5 边界

- 只读/CPU；未 build/translate/Metal/PSO/GPU/host/guest/gate/采样；未重复 raw/synthetic GPU 证明；未扩全 GS/其它 shader/map refill。
- 本轮不实现 dummy→拒绝的改动（属 production 脏源码；需单独授权）。
- 下一步真实观测/实现仍需 owner 新授权；本报告不构成授权。

---

## 6 §3 勘误（追加，旧原文保留；主管核对冻结 gs.metal 后）

1. **dispatch 不成立**：`groups {64,36,1}` / `threads {1,1,1}` 不等于“2304 点放进二维纹理网格”。冻结 gs.metal 的 kernel 用 `globalID.y`
   作 instance guard/index，`m0.y=1` 时 `y>=1` 直接 early-return；该布局只处理 x0..63 / y0，不是 2304 个 invocation。
   dispatch 必须**逐 stage 从 kernel 的 gid/guard 公式反推**；纹理尺寸不是 dispatch 坐标。真实组 shape **仍未定**；本轮不执行。
2. **AB 布局写错**：GS 的 Metal buffer0(set0)：id0 `vb_info`、id1 `gp_c3`、id2 `texture2d`、id3 `sampler`；
   buffer1(set1)：id0 `vertex_output`（**DEVICE BUFFER，不是 texture**）、id1 `geometry_vb_output`、id2 `geometry_ib_output`；
   buffer2(set2)：id0 `trb_data`（texture_buffer，**INPUT 不是生成 output**）。passthrough 是 Metal buffer1 的 id0 → GS 输出 VB
   （SPV `set1/b1`→`set1/b0` 重绑，**不是 Metal 顶层 idx0**）。不得混用 SPV set/binding、Metal buffer index、AB id。
3. **5word/stride 来源与 IB 契约**：5 word/stride 是冻结 translator metadata + MSL 确定的**实验 ABI**，不是从 16×16 fixture 测出的；
   生产 route 版本必须由 manifest 固定。IB 当前 ABI 是 **uint32 + -1 sentinel**，不因 `9216<65536` 就可改 u16。
   纹理 buffer 的 offset 对齐不能由一次 offset 256 合法推广为“仅 4 字节需求”；需 device/API 实际约束，当前记**未核对**。
4. **不共享 encode_args_ 的 dummy 策略**：未来实验 route 自己 fail-closed（例如只在 route 内部包一层判定），
   不改 `encode_args_` 的全局 dummy 行为、不影响正常游戏路径/其它标题。仍只是设计。
