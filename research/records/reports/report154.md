# report154 · 95bf-only 消费契约表（离线 SASS/SPH 审读，无 guest）

日期：2026-10-22 10:0x（本机）· HEAD `1408257`（未变）· 授权：主管 45 分钟离线审计（SSD 只读/CPU），**不授予 gate/guest**。
无 build/translate/host/Metal/PSO/GPU、无 production 源码或 profile/facts/库/lock/chain 改动、无采样/轮询、synthetic GPU 未重跑。

依据（全部只读）：
- 冻结 SPH 解码 `gs-sph-decode/six-gs.tsv`、`fields.tsv`（ctl/code 全 SHA 与本次 run 一致）
- 冻结 SASS 数据流 `gs-sass-decode/95bf.dataflow.sass.tsv`、`dataflow.log`、`Program.cs`（解码器）
- 本次真实记录 run `…/gsres-real-run-20261022-093229`：`gsres.txt`、`boot.log`（`[kd]`/`[pass]`）、`exemptions.txt`
- 冻结 MSL I/O `gs-sph-decode/a841-io.md`（库 `fout-six-lgt-correct645/out/b-c7c374c3eb34`）
- 拓扑枚举 `dm/third_party/ryujinx/.../OutputTopology.cs`（PointList=1, LineStrip=6, TriangleStrip=7）

## 1 消费契约表

| 类别 | 项目 | 值 / 来源 | 状态 |
|---|---|---|---|
| 身份 | key / ctl / code | `95bfab6122539993` / 2176 B / 768 B；SHA 与冻结 exempt 一致 | known |
| 身份 | stage / SphType / Version | Stage=4 (gs) / 1 / 3；code+0x30 SPH stage=4 | known |
| 拓扑 | GpPassthrough | 0（非直通） | known |
| 拓扑 | OutputTopology | 7 = **TriangleStrip**（ryujinx 枚举） | known |
| 拓扑 | MaxOutputVertexCount | 4（每输入图元最多 4 顶点） | known |
| 拓扑 | ThreadsPerInputPrimitive | 1 | known |
| 拓扑 | StreamOutMask | 1（有 stream-out 输出） | known |
| 其它 SPH | MrtEnable / KillsPixels / DoesGlobalStore / DoesLoadOrStore / DoesFp64 | 0 / 0 / 0 / 0 / 0 | known |
| 其它 SPH | ShaderLocalMemory(Low/High/Crs) / PerPatchAttributeCount / StoreReq(Start/End) | 0 / 0 / 0/–/0 | known |
| 绘制 | prim / count / instances / base_instance / indirect | 0(点) / 2304 / 1 / 0 / 0（direct） | known（record） |
| 输入 | 属性读 | `Ald` off 112/116/120/124 = (x,y,z,w)（SASS） | known |
| 输入 | 顶点格式 | stride 16；attr0 fmt 0x22 off 0；attr1 fmt 0x16 off 12 | known（boot） |
| 输入 | 前 4 点实测值 | (−63/64,−35/36,1,1)、( −61/64,−35/36,1,1)、(−59/64,…)、(−57/64,…) | known（boot） |
| 输入 | 网格位置规律 | x = −1+(2i+1)/64；y = −1+(2j+1)/36，前 4 个为 i=0..3, j=0 | hypothesis（由 4 点外推） |
| 纹理 | 采样指令 | `Texs` TidB=8, Target=Texture2D；SASS 0xc0 | known |
| 纹理 | 坐标 | `Ffma(±)(x,0.5,0.5)`：F20 立即数 0x3F000/0xBF000 = **±0.5** → (0.5x+0.5, −0.5y+0.5) | known（立即数解码） |
| 纹理 | 实际资源 | 合并句柄 `0x10100316` → tid 790；NVN 2D / **R8** / 64×36 / samples 0 | known（record） |
| 采样器 | 配置 | nearest/nearest、wrap 7,7,7(=CLAMP_TO_EDGE)、LOD 0..15.999、aniso 1、cmp 0/1 | known（record, sid 257 候选） |
| 采样器 | 由合并句柄推出 | `samp_mask=0`（S.samp[2][*] 全零）+ 句柄高位 sid=257 | known（record 语义，见 report153 §9.3） |
| 常数 | 用法 | `Ffma` 读 c[3][0]、c[3][1]（SASS 0xb0/0xb8/0xd0/0xe8） | known |
| 常数 | 数值 | **hypothesis**：= 观测 32 B UBO 的 (1/64, 1/36)；bank3↔UBO reg0 映射未证 | hypothesis |
| 输出 | 每输入点 4 顶点 | v0=(x−T·C0, y+T·C1)、v1=(x+T·C0, y+T·C1)、v2=(x−T·C0, y−T·C1)、v3=(x+T·C0, y−T·C1)，随后 `Out Cut` | known（SASS，含 NegA 位） |
| 输出 | z,w | 直接传输入 z,w（=1,1） | known（SASS + boot） |
| 输出 | T（texel 值） | 符号变量，**本轮未观测** | unknown |
| TF | 存在性 | StreamOutMask=1；同场景 frame1500 有 Bind/Begin/End 三条未实现调用 | known（记录/日志） |
| TF | buffer 地址/大小/stride/与哪次 draw 关联 | — | unknown（见 report153 §9.1） |

## 2 依赖式：前 4 个 VB 输入 → GS 输出 xy

设输入点 `(x,y,z,w)`（前 4 点为 `x_i=−1+(2i+1)/64`，`y=−35/36`，`z=w=1`），

[Fenced excerpt omitted from the shareable research record.]

四角顺序（TRIANGLE_STRIP + Cut）：`(−,+), (+,+), (−,−), (+,−)`。

代入前 4 点（T 保持符号）：
- i=0..3：`u_i = (2i+1)/128`，`v = 71/72` → texel 列 = i，行 = ⌊(71/72)·36⌋ = 35
- 即 `T_i = texel8[i, 35]`；`out = (−1+(2i+1)/64 ± T_i·C0, −35/36 ± T_i·C1, 1, 1)`
- 若 C0=1/64、C1=1/36（hypothesis），半宽/半高 = `(T_i/64, T_i/36)` NDC = `(7.5·T_i, 7.55·T_i)` px
  → 当 `T_i=1` 时四边形正好覆盖一格（960/64=15 × 544/36≈15.11 px）；`T_i=0` 退化为一点。
  **这只说明“尺寸与一格同量级”相容，不证明 T 的真实分布或该 GS 的最终视觉作用。**

## 3 PS `2e16` 的真实输入/资源需求（证据）

- 冻结 MSL：输出只有 color0，**无 user(locn) 输入**（`a841-io.md`）→ 该链无 GS→PS varying 传递。
- 本次 `[pass]`（`st1` = fragment）：tex reg1 tid 782、Metal fmt 115、640×360×1；samp reg1 sid 257；cb reg0 = 同一 32 B UBO。
- 真实目标/视口：`tgt=960x544`、`vp=0,0,960,544`、`sc=0,0,960,544`（`[pass] D` 行）。
- unknown：PS 是否与该 GS 的四边形有数据依赖（无 varying，只能经纹理/RenderTarget 间接）。

## 4 TF：只按原型分 known/unknown

- known：`BindTransformFeedbackBuffer(command*, int, NVNbufferAddress, size_t)`；`Begin/EndTransformFeedback(command*, NVNbufferAddress)`；
  SPH `StreamOutMask=1`；同场景日志出现三条调用（frame 1500）。
- unknown：buffer 的实际地址/size/stride/layout；begin/end 覆盖哪些 draw；stream 记录内容；TF 与 95bf 是否同一 pass。
- 本轮**不实现、不加 hook**。

## 5 接入真实 route 仍缺什么（有界）

1. `c[3]` bank ↔ `S.ubo[2][reg]` 映射的证明（SPH cbuf 表或翻译产物对照）；当前 C0/C1 只是 hypothesis。
2. `T` 的真实 texel 内容（本轮未观测；需要新的内容观测途径与授权，不得用 0.5 或 synthetic 代入）。
3. GS 实际执行：95bf/a841a5 不在 shader map；Metal 侧无 GS/mesh 路径（`a841-io.md` 已记录接口缺口）。
4. TF 语义：buffer/size/关联/布局全 unknown。
5. final-pass / GPU 证据：本轮记录只到 header-associated 的当前 S state 与 registry 标量。
6. 输出属性/TF 流布局（哪些 attr 进 stream、每顶点字节数）unknown。

## 6 边界

- 未新增脚本（只读既有产物 + 一次立即数/拓扑核对）；未翻译/build/host/Metal/PSO/GPU；未改 production 脏源码、profile/facts/库/lock/chain；未采样/轮询。
- 下一步真实观测仍需 owner 新的单次授权；本报告不构成授权。

---

## 7 勘误（追加，旧原文保留；主管限定 review 后）

1. **VB 打印精度**：boot 的 `[kd] stream r0` 只有限精度（`.6g`），§1/§2 中前 4 点的分数形式（−63/64 等）是**与文本相容的拟合**，
   不是 bit-exact 读回；由 4 点外推全网格（x=−1+(2i+1)/64、y=−1+(2j+1)/36）仍是 **hypothesis**。
2. **T_i 的条件**：`T_i = texel8[i,35]` 只在下列条件同时成立时才是“texel 地址”，条件未证：(a) 当前候选 slot 映射确实指向该 64×36 纹理；
   (b) 有效 view 为 64×36、baselevel 0、未改 swizzle；(c) R8 归一化与最近邻/CLAMP_TO_EDGE 采样语义成立。
   registry `d` 不含最终 view、也不证明实际 GS 选择。§2 应读作“在上述假设下的 texel 地址”，不是无条件“实测纹理读取”。不新增观测。
3. **PS 的依赖表述**：PS 没有 user varying ≠ 只经纹理/RT 受 GS 影响。GS 的 Position 决定 raster 覆盖与插值内建值（FragCoord 等），
   PS 可以用这些。§3 的“只能经纹理/RenderTarget 间接”改为“**user-varying 无传递**；raster 覆盖/内建依赖需实际 MSL 核对”。
4. **StreamOutMask 的效力**：它只是 SPH 的声明位，不证明 TF 启用、也不证明真的发生了 stream-out 输出；`tf=unknown` 保留。
