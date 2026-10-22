# report137 · geometry compute 输出 → passthrough VS 结构/编译/无 draw PSO

日期：2026-10-22 12:25–12:50（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无 dispatch/draw/queue/commandbuffer/encoder/资源创建、无 guest/gate/生产/库/guard 改动、无 commit。
PSO 启动前固定 `MTL_DEBUG_LAYER=1 / MTL_SHADER_VALIDATION=1`；首次合法 smoke 通过。

---

## 0 结果

- 真实 VS `d1657e5077b26d1d` / GS `95bfab6122539993` context decode；`SetVertexOutputMap` 后**仅一次**
  `gsCtx.GenerateVertexPassthroughForCompute()`；`Translate` 调用=0，未调用 VS/GS `Translate(true)`、`Translate(other,true)`、
  `GenerateGeometryPassthrough`。
- 输出 SPV：**Vertex model**（预测验证），2448 B，sha `1256f13a…`；MSL/ metal / metallib / no-draw render PSO 全部成功。
- 关键 ABI：passthrough VS 读 **set1/b0 `vb_input`**（runtime float），按 `gl_VertexIndex * 5` 访问 word0..4，写成
  Position.xyzw + PointSize；它**不读 geometry_vb_output 的 set1/b1**。未来 host 必须把 GS 展开输出重绑到 b0，不能认为
  “同 set 不同 binding 自动串联”。
- SPV 输出还声明 Clip/Cull BuiltIn，但 MSL 实际只保留 Position/PointSize；不把声明当实际消费。
- 无 queue/commandbuffer/encoder/buffer/texture/draw；PSO 用固定常量色 test fragment（非游戏 PS 2e16）与 RGBA8Unorm/
  sample1/no-depth 合成配置。

## 1 生成身份

- 输入：VS SPH 208 B sha `5f68c1cf…`；GS SPH 720 B sha `4c64701b…`；c1 空；Points accessor；pinned DLL。
- helper `passthrough`（SSD）只创建 context、SetVertexOutputMap、一次 `GenerateVertexPassthroughForCompute`；无 Translator
  Translate、无 FP64 fallback、无重试。
- 输出 `passthrough_vs.spv` 2448 B sha `1256f13a…`；`passthrough.json` 记录 info 为空（生成器未填原资源 metadata）。
- SPV：EntryPoint Vertex id31，interface 21/28；输入 var21 builtin 42（VertexIndex）；输出 struct 25
  member0 Position(vec4)、1 PointSize(f32)、2 ClipDistance、3 CullDistance；无 Location 装饰。
- 资源：`vb_input` set1/b0，runtime_array f32；无 CB/纹理/图像。

## 2 MSL/金属

- spirv-cross（同 flags）→ MSL sha `880bb809…`；metal AIR `846b4ce7…`；metallib `f7da28d7…`；各一次 rc0。
- MSL：
  ```
  struct spvDescriptorSetBuffer1 { const device _15* vb_input [[id(0)]]; };
  vertex main0_out main0(constant spvDescriptorSetBuffer1& set1 [[buffer(1)]],
                         uint gl_VertexIndex [[vertex_id]])
  ```
  读 `_m0[gl_VertexIndex*5 + 0..4]`，写 `gl_Position` + `gl_PointSize`；无 Location/attribute 输入。
- test fragment `test_frag`（fixed float4 0,1,0,1）独立编译；非游戏 PS。
- 无 draw render PSO：vertex `main0` type=vertex、fragment `test_frag` type=fragment；RGBA8Unorm、sample1、no depth；
  **PSO ok**。无 queue/commandbuffer/encoder/buffer/texture/draw。

## 3 ABI 对照（关键）

| 项 | 值 |
|---|---|
| passthrough 输入 buffer | **set1 / b0**（MSL `buffer(1)`, arg id0） |
| GS `geometry_vb_output` | **set1 / b1**（report135 实际） |
| 每 vertex stride | 5 words / 20 B；读 word0..4 = Position.xyzw + PointSize |
| GS VB layout | 5 words/vertex，相同 word 顺序（source/实际 MSL） |
| 索引 | GS `geometry_ib_output` 5 uints，最后 `0xffffffff` |
| 自动串联？ | **否**：binding b1→b0 需 host 重绑；VertexIndex 还需对应生成顶点顺序/计数 |

- 5-word layout 匹配不等于 host 已连通；passthrough 的 VertexIndex 是 raster 输入，不是 GS 的 primitive/invocation 索引。
- `0xffffffff` 作为 triangle-strip/primitive restart sentinel 的消费需要 host 的 index buffer 类型 uint32、primitive type、
  restart 配置/draw 参数；本 PSO 无 draw，不能称 raster 可消费。

## 4 下一次 compute→render 单点测试候选（未执行）

- 数据流：VS compute → GS fixture PointSize 变体 → 将 GS VB/IB 重绑到 passthrough 的 set1/b0 + test fragment；
  需要同步（同 CB/encoder 或 barrier）、uint32 index、restart/sentinel、draw count/vertex count、viewport/scissor、目标
  image 尺寸、passthrough input binding（b1→b0）与 generated buffer 消费。
- 未实现 host；不声称输出已 raster/像素已验；PointSize=1 仍是 fixture-defined，不对原 GS 默认下结论。

## 5 边界/状态

- 仅证该生成器在该输入下的 Vertex SPV/MSL/PSO 编译结构，以及 passthrough 读 set1/b0 的 ABI 事实；不证 GPU 输出/raster/像素/guest。
- 文档：INDEX/EXPERIMENTS 加 exp141（passthrough ABI/PSO probe/evidence-only）；request 141 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动下一轮执行。
