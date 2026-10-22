# report124 · geometry-as-compute ABI/接线契约审计（只读）

日期：2026-10-22 04:48–05:12（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；只读 repo/pinned 源码；无编译/翻译/SPIRV 生成/MSL/Metal/host/库/profile/facts/lock 改动、无 gate/guest/资源采样、无 commit。

---

## A. 调用顺序与资源所有权

pinned `TranslatorContext.cs`（sha `57e842a2…`）：

- `Translate(asCompute=true)`（:194）→ `CreateResourceManager(true)` → `GetResourceReservations()`（:474-480），后者读
  `_vertexOutput` 与当前 `_program.GetIoUsage()`；因此 **`SetVertexOutputMapForGeometryAsCompute(vsCtx)` 必须在 GS
  `Translate(true)` 之前调用**，否则 `_vertexOutput` 仍是构造时的空 `IoUsage`。
- `SetVertexOutputMap...`（:483）只执行 `_vertexOutput = vertexContext._program.GetIoUsage()`；它不复制 buffer、不分配、
  不校验 VS/GS 的 location 是否匹配。
- `vsCtx` 需要的是已 decode 的 `_program`（`GetIoUsage()` 来源），源码没有要求先调用 `vsCtx.Translate(true)`；但若还要
  VS 的 asCompute SPV，必须另做一次 VS 请求。**repo 内没有该调用者**（backend 不在 vendored 子集），实际 backend 顺序
  unknown，不能宣称已验证。
- `Translate(other, asCompute)`（:214）在同一 ResourceManager 内先 Emit `this` 再 Emit `other`，可组合两个 context；但
  无调用者，且 `other` 的 local memory 状态也会被覆盖；不是现成“VS+GS 一次请求”的证明。
- `Translate(true)` 在 :240 加 `FeatureFlags.VtgAsCompute`；`GetDefinitions(true)` 返回 `ShaderDefinitions(Compute,32,32,1)`
  （:300-305），即 compute local size 32×32×1。
- 资源预留是**每个 Translate 的 ResourceManager 各自创建**；VS/GS 两 stage 仅通过相同 reservation 数字与 host 绑定共享，
  没有共享对象/自动冲突检查。不能把 native GS 的 `res.json` 当 asCompute 资源表。

## B. ABI/set-binding/布局

`ResourceReservations.cs`（sha `ae08a2f8…`）与 `TranslatorContext.cs`：

| 资源 | set / binding | 定义/布局 | 暴露 |
|---|---|---|---|
| support buffer | set0 / 0（ReservedConstantBuffers 首先保留） | 外部 support | 非本文件定义；host 现有 |
| `vb_info` | set0 / 1 | Std140 `VertexInfoBuffer`：vertex_counts vec4u, geometry_counts vec4u, vertex_strides[32] vec4u, vertex_offsets[32] vec4u | translator 内部结构；host 填 |
| `vertex_output` | set1 / 0 | Std430 `{ float data[] }`，stride=`OutputSizePerInvocation`（**32-bit words**） | 仅 translator 定义；host 分配/绑定 |
| `geometry_vb_output` | set1 / 1 | Std430 同 data[]；stride 同上 | 仅 translator；host 分配/绑定 |
| `geometry_ib_output` | set1 / 2 | Std430 `{ uint data[] }` | 仅 translator；host 分配/绑定 |
| `trb_data` | set2 / 1 | TextureBuffer，topology remap | 仅 translator；host 生成 |
| `ib_data` / `vb_dataN` | set2 / 0 / 2+N（N<32） | TextureBuffer | 仅 VS asCompute 使用；host 生成 |

- `VertexInfoBuffer`（sha `aae42b60…`）：`VertexCounts` 由 geometry 用于 `vertexCount`（component0）；VertexToCompute 用
  component2/3 作 base vertex/base instance；`GeometryCounts` 字段存在但本次源码未找到写/读公式，**语义 unknown**；
  strides/offsets 的 32 项由 host 填。
- `OutputSizePerInvocation`、`InputSizePerInvocation` 是 `FillIoOffsetMap` 累计的 **32-bit word 数**（每 Position 4 +
  PointSize 1 + clip distance 每项 1 + user location 4…）；`OutputSizeInBytesPerInvocation` 只是乘 4 的辅助属性。
- `GeometryToCompute.cs`（sha `407ac0f6…`）：
  - EmitVertex：`baseVertex = primitiveId*(MaxOutputVertices*ThreadsPerInputPrimitive) + invocationId*MaxOutputVertices`；
    每个 Emit 把 `stride` words 从 local memory 复制到 `geometry_vb_output`；`outputPrimVertex` 自增。
  - 同时写 `geometry_ib_output[outputBaseIndex] = outputBaseVertex`；EndPrimitive 写 `-1`。
  - 索引 stride 字面：`MaxOutputVertices + (OutputTopology switch { LineStrip=>max/2, TriangleStrip=>max/3, _=>max })`，
    再乘 `ThreadsPerInputPrimitive`。95bf（max4/TriangleStrip/threads1）字面值 **5**；仅公式值，host 实际 index 布局未验证。
- `GenerateGeometryPassthrough`（:578）只生成一个固定展开的 GS：Points→PointList/max1，Lines→LineStrip/max2，其它→
  TriangleStrip/max3；它按 `InputTopology`，不读取实际 command primitive，也不等同于 95bf 的真实 SASS（95bf 是
  非 passthrough、4 Emit）。`GenerateVertexPassthroughForCompute` 生成 VS，读 `vertex_output`，stride 用 geometry
  reservations；GpPassthrough 为 false 时 `GetResourceReservations` 不合并 `_vertexOutput`，两 stage 的 IO layout 关系
  需要 host 明确，源码未给出完整契约。

### 95bf（Points / Invocations=1 / MaxOutputVertices=4）已知/缺口

| 项 | 已知 | 缺口 |
|---|---|---|
| InputTopology | 若 query=Points：`InputVertexCount=1` | 本次 command Points 尚未接到 query；native SPV 仍是默认 Triangles |
| trb_data | 长度 1（Points） | 内容/索引映射 host 生成，未定义 |
| OutputSizePerInvocation | 由 95bf asCompute IO usage 决定；native SPV 有 Position/PointSize/Clip[8]/Cull[1] | asCompute 实际写入集合未生成，精确 word 数 unknown |
| geometry_vb | 每 primitive `4*1*OutputSize` words；每 invocation `4*OutputSize` | host 分配/绑定/清零未实现 |
| geometry_ib | 每 primitive `5*1` words（字面公式） | 实际 index count/布局未验证 |
| vb_info | binding/结构已知 | vertex_counts/geometry_counts/strides/offsets 的 host 值 unknown |
| dispatch/count | 源码无 caller | grid/primitive count/indirect 参数 unknown |

## C. 最小数据流与 host 缺口

[Fenced excerpt omitted from the shareable research record.]

- 需要：compute dispatch（VS/GS 各一次或组合）、写后读 barrier、geometry counts 的 readback/indirect draw、生成
  VB/IB 的绑定、counter 清零、dispatch 数量来自 primitive/vertex 计数。
- 现有 Metal host（`nvn_mtl.m`）**没有** compute-as-vertex 路径、没有这些 buffer 绑定/dispatch/indirect/同步；API 层面
  Metal 有 compute/storage buffer/texture buffer，但“存在 API”不等于本项目已实现。
- 若 asCompute SPV 使用 TextureBuffer（`ib_data`/`vb_dataN`/`trb_data`），需要对应 Metal texture-buffer 能力；本审计只列
  需求，不改 format/sampler/权限。

## D. 下一次 asCompute raw 探针能否 1/2 stage 请求

**当前不能。** `Program.cs`（sha `027e9d79…`）只对 `stage=="cs"` 设 `TranslationFlags.Compute`（:126），其它一律
`ctx.Translate()`（:128），没有 asCompute 参数字段/CLI，也没有调用 `SetVertexOutputMapForGeometryAsCompute`。因此：
- 无法用现有 wrapper 请求 1 或 2 个明确 asCompute stage；
- 即使扩展 wrapper，translator 的 reserved buffer layout/count/dispatch 契约没有 metadata 输出（当前 `.res.json` 只列实际
  采样资源），host 仍需生成。

最小前置（仅设计，不执行）：
1. probe-only wrapper 增加 `asCompute` 模式与 VS/GS 两个明确 job（或一个组合请求），显式传 topology/input/output usage；
2. 输出 reserved set/binding、sizes、trb/vertex_info 结构、index stride 的 metadata；
3. 定义 host 的 dispatch/count/indirect/sync 契约并做离线结构校验。
在这些完成前，不能把 asCompute 探针定为“1 或 2 个 stage 请求”；现有 native GS 结果不能代替。

## 文档/状态

- README/INDEX/EXPERIMENTS 加 exp128（geometry-as-compute ABI audit/read-only）；request 128 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 30 分钟内完成；停止 review，不实现/不 gate/guest。


---

## 6 勘误（主管 review；原文保留）

- `SetVertexAsComputeLocalMemories` 的 `local_topology_remap` 长度 = `InputVertexCount`（95bf Points 若映射则 1），这是
  **本地数组**；不能据此断言整张 `trb_data` texture buffer 长度为 1。`trb_data` 的纹理长度/内容仍由 host 生成，unknown。
- D 的表述过强：host dispatch/count/indirect/sync 契约是**未来执行**前置，不妨碍隔离 wrapper 仅创建 context 并
  `Translate(true)`；本探针已在不实现 host 的情况下取得公开 reservations 与 SPV 声明。两者应分层：编译期探针可做，
  执行/host 仍不可用。
- `GenerateVertexPassthroughForCompute` 读 set1/b0，GS 写 set1/b1；这是两套 buffer，未来 host 需重绑/消费设计，报告不
  暗示自动接通。
