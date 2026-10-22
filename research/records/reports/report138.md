# report138 · synthetic VS→GS→passthrough→testPS 64×64 raster 单点

日期：2026-10-22 13:00–13:35（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；唯一 CB commit=1（VS/GS 各一次 dispatch + 1 次 indexed draw）、无第二 commit/重试；无 guest/gate/生产/库/guard 改动、无 commit。
环境固定：`MTL_DEBUG_LAYER=1 / MTL_SHADER_VALIDATION=1`，全程未关闭。

---

## 0 结果

- 固定资产：VS `a286322f…`、GS PointSize=1 变体 `c3d170fd…`、passthrough `f7da28d7…`、test PS `805b…`（完整 SHA 见 identity），fixture `7a1ab70c…`/manifest `9c601614…`/expected120 `b794fad5…`；未改 shader/库/fixture。
- 一次 command buffer：VS compute encoder dispatch(1,16,16) → GS compute encoder 同参数 → render encoder；**commit=1**；wait=0、status=4、error=none；GPUStart/End `101509.844849/…553`。
- 64×64 RGBA8Unorm Shared render target；clear black；TriangleStrip indexCount5/UInt32/instances1/base0；`ffffffff` terminator。
- **payload PASS**：VS5/GS20/IB5 与 expected120 `b794fad5…` 完全一致；只读输入/8 guard PASS。
- **pixels PASS**：64×64 raw 与 expected raw 完全一致（sha `141a2a0f…`）；green=64、black=4032、alpha_bad=0；PNG 64×64 RGBA（sha `66a03ffa…`）。
- 失败会立即停；本轮一次成功，无第二 commit。

## 1 CPU 前置

- fixture/manifest/expected120 先 SHA；u64 无 double；VS/GS compute 16×16 contract（两 PSO max640）通过；pre-submit 在 queue 前。
- report136 extent contract：VB width4/16B payload、IB/TRB width1/4B；actual width/type/format 查询；backing 528/516 与 payload16/4 分开。
- 像素 oracle（CPU 先推导）：由 positions/w → NDC x0..0.5、y0.4375..0.5625，viewport 64×64 top-left 得到
  **x32..47、y14..17 共64像素 green，其余4032 black，alpha全部255**。
- `pixel_self_test`：正确 mask 接受；矩形上移1行、一个颜色错、alpha254、全黑均拒绝。`payload_self_test` 120B 变异/NaN/Inf 拒绝。
- 预算 allocated=156952 <16MiB；sampler supportArgumentBuffers=1；shared vertex_output tracked；hazard/useResource 保留。

## 2 资源/AB

- Compute：VS 3 AB + GS 3 AB 独立；shared `vertex_output`；GS 写 `geometry_vb`/`geometry_ib`。
- Raster AB：passthrough `main0` 的 `buffer(1)` argument encoder，id0 -> `geometry_vb_output` MTLBuffer + offset256；
  **不绑 VS vertex_output**。
- Index：`geometry_ib_output` 原 buffer + offset256，`MTLIndexTypeUInt32`、TriangleStrip、indexCount5；0xffffffff 由 API
  terminator 消费，不作为 vertex index。
- 目标：64×64 RGBA8Unorm/Shared/RenderTarget，检查实际 size/format/storage；clear(0,0,0,1)、store、无 depth/stencil、
  blend off/colorwriteall/cull none、viewport(0,0,64,64,0,1)、scissor全幅。
- test fragment 固定 green（非游戏 PS 2e16）；passthrough 输出 Position/PointSize。

## 3 执行/读回

- 单 queue/单 CB；VS/GS 两个串行 compute encoder，随后单 render encoder；`useResource` 读 geometryVB/IB（vertex/index）、
  写 target，AB read；无 concurrent encoder、无 indirect draw、无额外 dispatch/draw。
- completion 10s 内；CPU `getBytes` 64×64 RGBA 16384B；raw/expected/PNG/result/stderr 保存，写入 rc 检查通过。
- 120B numeric readback 与 expected 同 sha；pixels raw 与 expected 同 sha；PNG 文件有效 64×64 RGBA。

## 4 证明边界

- 成功仅证：**此 synthetic 配置**（report135 fixture-defined PointSize=1 GS 变体 + report137 生成 passthrough VS +
  fixed green test PS + 64×64 RGBA8/Shared/no-depth + 16×16 compute 组）的 compute→raster 单点数值/像素。
- 不证原 95bf GS PointSize 默认、游戏 PS/guest 画面、其它输入/topology/GS、多 z/多 invocation、生产 host。
- 无 spirv-val；PSO/validation 成功不等于一般 GS 支持。PointSize=1 仍是测试值，非游戏语义。

## 5 文档/状态

- INDEX/EXPERIMENTS 加 exp142（synthetic compute→raster 64×64/success/evidence-limited）；request 142 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动下一轮/第二 commit。
