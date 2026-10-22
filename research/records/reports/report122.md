# report122 · Points→InputTopology 对照 + 95bf SPV interface 解码（只读）

日期：2026-10-22 06:30–06:52（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；无翻译/optimizer/spirv-cross/MSL/Metal/host/库/repo/profile/facts/lock 改动、无 gate/guest/资源采样、无依赖安装。
证据：`/path/to/external-drive/xc3/work/experiments/gs-points-inputtopology/`

---

## A. Command Points → pinned InputTopology

- NVN：`NVN_DRAW_PRIMITIVE_POINTS = 0x0`（`dm/gfx/nvn/include/nvn.h:721`，sha `7e691b24…`）；邻接值
  `LINES_ADJACENCY=0xA`、`TRIANGLES_ADJACENCY=0xC`（:731/:733）。
- Pinned `InputTopology`（`InputTopology.cs` sha `452ece08…`）：枚举序 **Points=0, Lines=1, LinesAdjacency=2,
  Triangles=3, TrianglesAdjacency=4**；`InputVertexCount` 1/2/4/3/6，`InputVertexCountNoAdjacency` 1/2/2/3/3（:5-42）。
- 消费者：`TranslatorContext.cs`（sha `57e842a2…`）`Translate` 用 topology 设 vertex-as-compute local memory（:453），
  `GenerateGeometryPassthrough` switch 用 topology 决定 PointList/LineStrip/TriangleStrip 与 max vertices（:591-598）；
  `SpirvGenerator.cs`（sha `44886a62…`）把 topology 映射到 `ExecutionMode.InputPoints/InputLines/InputLinesAdjacency/
  Triangles/InputTrianglesAdjacency`（:241-248）；`Declarations.cs`（sha `63814353…`）geometry 输入数组长度用
  `InputTopology.InputVertexCount`（:393/:540）。
- **没有找到 NVN command primitive → InputTopology 的生产映射函数**。Wrapper `dmsh_xlate/Program.cs`（sha `027e9d79…`）
  `QueryGraphicsState` 固定返回 `InputTopology.Triangles`（:82），不接收 command prim；`nvn_mtl` 也没有调用查询。
- 因此：**枚举层面 Points=0 与 InputTopology.Points 序号相同，但当前 query 路径完全没有使用 command prim**；实际
  运行 95bf 的 command prim 是 Points（report121），生成的 SPV 却是 `InputTriangles` + input array[3]——这是旧默认
  Triangles 诊断假设，不是真实 Points 对照。Points 到邻接/数组长度的映射不能从现有代码推断成已实现；未做 Points raw
  翻译（授权禁止）。

## B. 95bf native Geometry SPV interface 33/37

SPV：`/path/to/external-drive/xc3/work/experiments/gs-raw-probe/out/95bfab6122539993.spv`，4360 B，sha
`e50cf60d…`。OpEntryPoint word 34：`00000003`(Geometry) `00000028`(id40) `6e69616d`("main") `00000000`
`00000021`(33) `00000025`(37)。原始指令见 `spv-trace.txt`。

| 项 | 原始依据 | 解码 |
|---|---|---|
| ExecutionModel | word34 `00000003` | **Geometry(3)** |
| ExecutionModes | modes table | **InputTriangles(22), Invocations=1, OutputTriangleStrip(29), OutputVertices=4** |
| 输入变量 33 | word403 `OpVariable 0000001f 00000021 00000001` | storage **Input**，类型 ptr[Input] -> array[3] of struct 0x1c |
| 输入数组长度 | word395 `OpTypeArray 0000001e 0000001c 0000001d`；const 0x1d=3 | **3**（与默认 Triangles 一致，不是 Points） |
| 输入成员 0 | OpMemberDecorate 0x1c:0 BuiltIn 0 | `vec4<f32>`, **BuiltIn Position**，Invariant |
| 输入成员 1 | 0x1c:1 BuiltIn 1 | `f32`, BuiltIn PointSize |
| 输入成员 2 | 0x1c:2 BuiltIn 3 | `array[8] of f32`, BuiltIn ClipDistance |
| 输入成员 3 | 0x1c:3 BuiltIn 4 | `array[1] of f32`, BuiltIn CullDistance |
| 输出变量 37 | word417 `OpVariable 00000023 00000025 00000003` | storage **Output**，类型 ptr[Output] -> struct 0x22 |
| 输出成员 | 0x22:0..3 BuiltIn 0/1/3/4 | Position/PointSize/ClipDistance[8]/CullDistance[1]，**struct 无外层数组** |
| Location | 无 OpDecorate/OpMemberDecorate Location(30) | **无 user Location**；接口只有 BuiltIn |
| 输入/输出接口 | 33/37 only | 无其它 Location interface |

- `Position` 是 BuiltIn，不是 Location；输入是 `gl_in[3]` 形状的 struct 数组，输出是单份 per-vertex struct。
- 输出没有 user varying；与 SASS 95bf 只写位置、PS 无 user 输入一致，但 **SPV 的 Interfaces 只描述声明，不代表 GS
  实际执行的 emit/邻接语义**。
- 未解/缺失：SPIR-V 中无 Location，故无 user attribute 映射；`InputTriangles` 是 wrapper 默认假设，不是 command Points
  的映射结果；未解码其他 interface 类型（仅 33/37）。

## C. 结论边界

- A 证明：pinned enum/消费者与 wrapper 默认 Triangles 的差异；Points 与 InputTopology.Points 仅在数值上同为 0，
  没有生产映射路径，当前 SPV 的 Triangles/array[3] 不能当 Points 运行配置。
- B 证明：现有 95bf SPV 的接口是 Geometry、InputTriangles 默认、输入数组 3、Position/PointSize/Clip/Cull BuiltIn，
  无 Location/user varying；不证明 GS 执行/真实 topology/像素/GPU。
- 未做 Points raw 翻译、GS 实现、asCompute、优化/反编译安装。

## D. 文档/状态

- INDEX/EXPERIMENTS 加 exp126（Points/SPV interface read-only）；报告121 追加 gate 次数笔误勘误（此前 4 次拒绝，
  本次第 5 次）。
- request 126 原样归档（local id `xc3-points-spv-126`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 30 分钟内完成；停止 review，无自动后续。


---

## E. 追加：EntryPoint LiteralString 解析修正

- 原 `decode_spv_interface.py` 的 interface 起点用 `a[3:]` 并过滤 0，仅对 `main` 这种恰好两 word 名称碰巧正确。
- 现按 SPIR-V LiteralString 的 null 终止 word 计算实际 interface 起点；`fixtures_entrypoint.py` 用 `main`、跨多 word
  名称、空名称三例验证均得到 `[33,37]`。重解旧 SPV 后 33/37、modes、BuiltIn 结论不变。
