# report123 · 95bf native Geometry Points 受控 raw 探针

日期：2026-10-22 04:24–04:45（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD 实验；无生产/工具/lock/chain/profile/facts/host/库/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 结果

- 隔离实验 wrapper 构建成功；与 pinned wrapper 的**唯一源码行为差异**是
  `QueryGraphicsState` 的 `InputTopology.Triangles` → `InputTopology.Points`（`points.diff` 1 行）。
- 对 95bf 做**一次** raw 翻译（stage gs，code/c1/job 与 report117 原输入严格一致；debug/reduced/tex/img/attr/fout 不变），
  rc=0，得到 Points SPV。
- **可证伪预测成立**：Points SPV 为 `ExecutionMode InputPoints(19)`，geometry input 数组长度 **1**；原 Triangles 产物为
  `InputTriangles(22)`、数组长度 **3**。其余接口/BuiltIn/OutputVertices 不变。
- EmitVertex/EndPrimitive 仍为 **4 / 1**；资源 response 完全相同（cbuf slot3/binding2；texture binding1/handle8/type3/array1；
  无 sbuf/image）。

## 1 构建隔离/身份

- 复制 `dmsh_xlate/Program.cs` 到 SSD；`points.diff` 仅一行：
  `InputTopology.Triangles` → `InputTopology.Points`。
- 实验项目用现有 pinned DLL 引用（`Ryujinx.Graphics.Shader/Common`、`Spv.Generator`、`Gommon`），不是生产项目引用；
  `RestoreSources` 为空，离线 `dotnet build -c Release`，0 warnings/0 errors。
- 身份：
  - baseline Program.cs sha `027e9d79…`；new Program.cs sha `75eb7977…`；diff sha `3b274d6c…`。
  - pinned DLL：Shader `011c50cb…`、Common `5222da62…`、Spv.Generator `4ef85303…`、Gommon `1648a882…`。
  - new binary sha `927a7d19…`；build.log `5ca78daa…`；build.env 记录 cwd/cmd/DOTNET_ROOT。
  - 输入：code sha `a6f403ed…`（report117 `.sph.bin` sha `4c64701b…`）、c1 空、job sha `c1c916d2…`；run rc=0，stderr 空。
  - 输出 Points SPV `ae52c1f2…`、res `b615da72…`；旧 Triangles SPV 保留 `e50cf60d…`。

## 2 比较（旧 Triangles vs Points）

| 项 | Triangles（旧，默认假设） | Points（新探针） |
|---|---|---|
| ExecutionModel | Geometry(3) | Geometry(3) |
| Input mode | **InputTriangles(22)** | **InputPoints(19)** |
| Invocations | 1 | 1 |
| Output mode | OutputTriangleStrip(29) | OutputTriangleStrip(29) |
| OutputVertices | 4 | 4 |
| geometry input | array[**3**] of struct | array[**1**] of struct |
| input members | Position/PointSize/Clip[8]/Cull[1]，BuiltIn | 同左，BuiltIn 不变 |
| Location | 无 | 无 |
| output | per-vertex struct，同成员 | 同左 |
| EmitVertex/EndPrimitive | 4 / 1 | **4 / 1** |
| resources | cbuf slot3/b2；tex b1/h8/type3/array1 | **完全相同** |
| SPV size/sha | 4360 / e50cf60d… | 4344 / ae52c1f2… |

- 差异集中在 Input mode 与输入数组长度；没有新增 Location/user varying，没有输出拓扑/emit 数变化。SPV 字节重编号
  （size -16）不应当作语义变化。
- 不能说数值/像素/GPU 等价，也不能说 GS 实际执行或每 guest primitive 的动态 invocation 已证明；这只是同一
  raw 输入的编译期 SPV 形状差异。

## 3 解析器修正

- `decode_spv_interface.py` 的 EntryPoint interface 起点改为按 SPIR-V LiteralString 的 null 终止 word 计算，不再用
  `a[3:]` 过滤 0；新增 `fixtures_entrypoint.py`：`main`、跨多 word 名称、空名称三例均得到 interface [33,37]。
- 用修正后的 parser 重解旧 SPV，EntryPoint/interface 33/37、modes、BuiltIn 结论不变。

## 4 边界

- 这是**实验 wrapper**的 Points 输出，不是生产 pinned wrapper 已改；生产仍固定 Triangles。
- 不是 NVN command→InputTopology 的生产映射；Points 探针仅证明“把 query 改成 Points 后，SPV 形状按预期变化”。
- 无 optimizer/spirv-cross/MSL/Metal/host/库/guest；Points SPV 不是 Metal 执行路径。
- 未做 asCompute/GS 实现/白名单/`vs_pad`。

## 5 文档/状态

- INDEX/EXPERIMENTS 加 exp127（Points raw probe/evidence-only）；report122 已加 parser 修正说明。
- request 127 原样归档（local id `xc3-points-raw-127`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 30 分钟内完成；停止 review，无自动后续。
