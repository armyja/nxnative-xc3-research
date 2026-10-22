# report114 · GS SPH 字段解码 + geometry-as-compute 源路径评估（纯只读）

日期：2026-10-22 02:42–02:58（本机）
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无 build/translate/host/guest/gate、无 repo/工具/lock/profile/facts/库改动、无提交。
证据目录：`/path/to/external-drive/xc3/work/experiments/gs-sph-decode/`

---

## 0 report113 更正（原文保留）

- “没有可用 decoder 定义”错误：pinned Ryujinx `ShaderHeader.cs` 已有完整字段读取；本轮按其定义解码，不再从零反推。
- “a841 1280 最小”错误：全六最小是 `ef6ec0914d348ad3` 256，其次 `95bfab6122539993` 768；a841 1280 不是最小，只
  是“已知接口失败”的代表。语义难度此前未知，本轮用实解字段重新比较。

## 1 解码路径（关键）

- 我们的 `job_for` 对 graphics 从代码区剥掉 `0x30` packaging header，再把 **SPH 起始**交给 translator；`Program.cs`
  Accessor.GetCode 从 code[0] 返回，`ShaderHeader` 读 code[0..0x50]。dump 的 `.code` 仍含 `0x30` packaging header，
  因此 decoder 必须读 **code+0x30**，不能读 CTL、不能读 packaging 0x30 本身。
- 固定六输入、长度/hash 核对；SPH Stage=4，六 key 均由 ctl/code hash 重算固定，不新提取资产。

## 2 实解字段（pinned 定义；raw word/offset/bitrange 见 `fields.tsv`）

| key | ctl/code | SphType | Ver | Stage | GpPassthrough | StreamOutMask | ThreadsPerInputPrimitive | OutputTopology | MaxOutputVertexCount |
|---|---|---|---|---|---|---|---|---|---|
| a841a5d995c26b26 | 2176/1280 | 1 | 3 | 4 | 0 | 1 | 1 | 7 TriangleStrip | 4 |
| 95bfab6122539993 | 2176/768 | 1 | 3 | 4 | 0 | 1 | 1 | 7 TriangleStrip | 4 |
| ef6ec0914d348ad3 | 2176/256 | 1 | 3 | 4 | **1** | 1 | 1 | 7 TriangleStrip | **1** |
| 4c0a9c8e53f088cb | 2176/11520 | 1 | 3 | 4 | 0 | 1 | 1 | 7 TriangleStrip | 4 |
| eafdbb5a5af2a6dd | 2176/14336 | 1 | 3 | 4 | 0 | 1 | 1 | 7 TriangleStrip | 4 |
| 7a7eb30dfb6187b5 | 2176/6144 | 1 | 3 | 4 | 0 | 1 | 1 | 7 TriangleStrip | 4 |

- 全部 `StreamOutMask=1`，但这不证明 Transform Feedback API 实际用途；`ThreadsPerInputPrimitive=1`。
- **Input primitive 不在 SPH**：来自 runtime QueryGraphicsState；wrapper 目前默认 `InputTopology.Triangles`，不能用
  output topology 或默认值反推。实际 SASS emit/ATTR 读写未解码；header 的 Imap/Omap 只是声明。
- `ef6e` 是唯一 `GpPassthrough=1 + MaxOutputVertexCount=1`：这只表示该 feature 位；不能仅据此称“不可修改输出/可省略 GS”，
  实际控制/输出仍需 SASS/运行分析。它与 a841/95bf 的 max4 声明不同，仅作候选分类线索。

## 3 三个完整链的 MSL 声明（只读）

| chain | VS 输出 | PS 输入/输出 |
|---|---|---|
| a841 (post#83:0) | d7be：仅 gl_Position/PointSize，**无 user(locn)** | ef55：color0；user(locn0/1/2) |
| 95bf (post#92:0) | d165：仅 gl_Position/PointSize，无 user | 2e16：color0 only，无 user 输入 |
| ef6e (lgt#3:1) | f5d9：user(locn0/1) + position | abdad：color0/1 + user(locn0) |

- a841 正好解释 d7be/ef55 的 locn0/1/2 接口失败；GS 实际 emit 未解出，不能证明它一定写这些通道。
- 95bf 的 PS 无 user 输入，若 GS 只写位置/颜色，语义面更小；a841 需要多输出，难度更高。

## 4 源码路径/缺层（只读事实）

pinned hash/行号：`ShaderHeader.cs 0c8ba060…`（98/100-130/138/142/144）、`OutputTopology.cs a288af1c…`（5-7）、
`TranslatorContext.cs 57e842a2…`（194 Translate(asCompute)、433-450 geometry 资源、483 SetVertexOutputMapForGeometryAsCompute、
488 GenerateVertexPassthroughForCompute、578 GenerateGeometryPassthrough）、`Program.cs 027e9d79…`（126 仅 cs 设 Compute，
128 Translate()，77-82 QueryGraphicsState 默认 Triangles）；lock `3fd3b3f6…`，Shader DLL `011c50cb1c08e44f`。

- 底层库有 geometry-as-compute/passthrough 代码路径；**wrapper 没有调用 asCompute/SetVertexOutputMap**，host 没有 GS
  执行/同步/间接 draw/ABI；Metal 侧无 mesh 路径。不能把库里有函数当成已可用。
- 需要：真实 input topology/primitive 查询、VS 输出 map、geometry 资源 reservation（TRB、vb/ib output）、展开布局/indices、
  host compute 调度与生成 buffer 的 draw；本轮均未实现。

## 5 选择建议（一页结论）

- 六者中 **95bf（768，完整 vs→gs→ps，GpPassthrough=0，max4，PS 无 user 输入）** 是“真 GS 语义 + 受控复杂度”的
  最小候选；a841（1280，已知接口失败，PS 需要 locn0/1/2）语义更明确但更难；ef6e（256）是 GP passthrough，不能代表
  真 GS 展开，且若用它需证明 passthrough 等价性。
- 下一步**不建议直接写 GS 译器**：先做 95bf/a841 的 GS SASS emit/ATTR 只读签名分析（确认真正输出通道/邻接用法），
  再决定 raw GS 译器试验是否值得。最小可离线测试的语义是“GS 输出通道集合与 PS 输入匹配”，不是像素。
- 原生 Metal geometry stage 不存在；geometry-as-compute 是多层结构性实现（wrapper+translator+host+ABI），工作量大、
  无离线语义 oracle。保持 guard 不绕过，不用 vs_pad 代替 GS 语义，不扩白名单。

## 6 状态

- decoder 与 fixtures：合成 bitfield/offset 边界通过（不依赖真实 dump）；六真实 dump 表见 `six-gs.tsv`/`fields.tsv`；
  原 ctl/code 未改。
- 文档：INDEX/EXPERIMENTS 加入 exp117（GS decode/evidence-only）；本报告；request 116 补 relay
  `codex-xc3-postinteger-gs-feasibility-3707334aa68146579d6d868111db26f0` 与 `accepted:true`；request 117 原样归档
  （local id `xc3-gs-sph-decode-117`；relay id 未提供 unknown）。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无后续自动实现或 guest。


---

## 7 追加撤回（SASS 坐标 bug 影响）

report115 的 SASS 扫描坐标错误（control 用 SPH-relative），因此 report114 §5 里基于 SASS 的最终候选比较/“95bf 无资源/
直线”等说法**撤回**；SPH 字段表（stage/topology/maxv/GP/stream/threads）不受影响。修复后的 SASS 见 report116。
