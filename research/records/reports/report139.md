# report139 · 2 point × 2 instance synthetic VS→GS→raster

日期：2026-10-22 13:45–14:20（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；唯一 CB commit=1（VS/GS 各一次 compute dispatch + 一次 drawIndexed），无第二 commit/重试；无 guest/gate/生产/库/guard 改动、无 commit。
环境固定：`MTL_DEBUG_LAYER=1 / MTL_SHADER_VALIDATION=1`，全程未关闭。

---

## 0 结果

- 新 fixture（sha `52efef88…`/manifest `046066ed…`）：m0=(2,2,0,0)、m1=(2,0,0,0)、m2=(4,1,1,1)、m3=0；
  ib_data/trb 用 **uint32 位型 [0,1]**（R32Float texture-buffer 承载，非 float1.0）；vb_data 两点
  `(1,2,3,4)`、`(-1,-2,1,4)`；width 8/2/2、payload 32/8/8B。
- CPU 契约：VS 4 active gid (x0/1,y0/1)，输出 20 words；GS 4 primitive、80 words VB、20 index
  `[0,1,2,3,ffffffff, 4,5,6,7,ffffffff, 8,9,10,11,ffffffff, 12,13,14,15,ffffffff]`；两 instance 数值相同、槽位不同。
- 唯一执行：一 CB，两 compute encoder（VS/GS 16×16×1）→render encoder；`drawIndexed` TriangleStrip、**indexCount20**、
  UInt32、instances1、base0（4 个 terminator）；commit=1、wait=0、status=4、error=none。
- **480B numeric PASS**：VS20/GS80/IB20 与 expected `2661b230…` 完全一致；8 buffers guard/只读输入/poison 全覆盖。
- **pixels PASS**：64×64 raw sha `bd53b332…` 与 expected 完全一致；green=128、black=3968、alpha_bad=0；PNG sha `60f6a348…`。
  两矩形 x32..47/y14..17 与 x16..31/y46..49；两个 instance 重叠同色不增加覆盖。

## 1 CPU 推导

- VS：`gid.y*m0.x+gid.x` 写 vertex_output slot0..3；xy 来自输入点；m2 flags=1，PointSize 由 VS 默认1。
- GS：`primitive = gid.y*m1.x+gid.x`（0..3），trb[x] 0/1，vertex_output 索引 `gid.y*m0.x+trb` =
  0/1/2/3；每 primitive 4 corners、base `p*4`；IB `p*4+0..3` + `ffffffff`；无 cross-instance 漏写/别名。
- 四 corner 公式：sample=0.5、cbuf=(2,0.5)：
  - point0 `(1,2,3,4)` → `(0,2.25,3,4)`, `(2,2.25,3,4)`, `(0,1.75,3,4)`, `(2,1.75,3,4)`；
  - point1 `(-1,-2,1,4)` → `(-2,-1.75,1,4)`, `(0,-1.75,1,4)`, `(-2,-2.25,1,4)`, `(0,-2.25,1,4)`。
- 像素 oracle：NDC x -0.5..0.5、y 0.4375..0.5625 等；top-left viewport 64×64 得两个矩形，各64，共128 green；
  其余3968 black，alpha全255。CPU validator 对第二点/第二 instance 偏移、index base/sentinel、NaN/Inf/guard/只读变异拒绝。

## 2 执行/资源

- 固定库：VS `a286322f…`、GS `c3d170fd…`、passthrough `f7da28d7…`、test PS `805f5787…`；未改 shader。
- Compute AB 6 个独立；raster AB `buffer(1)` id0→geometry_vb offset256；index geometry_ib offset256；target 64×64
  RGBA8Unorm/Shared/RenderTarget；clear black/store/no-depth/blend off/cull none；test PS green。
- 预算 allocated=157336 <16MiB；PSO max640、16×16 contract 通过；sampler AB=1；tracked/hazard/useResources 保留。
- GPUStart/End `101882.581241/…582235`；文件写入 rc 均检查。

## 3 日志勘误（不重跑）

- 本轮 `execute.log` 的 `raster: ... indexCount=5` 是旧硬编码打印串；实际源码/调用为 **indexCount20**（4 strip ×5），
  480B/像素结果确认 4 primitive 均被消费。
- `view:` 行仍沿用旧字段名把 backing 长度 544/520 标成 `payload`；实际 payload 为 32/8/8B，extent helper 用修正字段校验。
  这是日志文本问题，不改本轮 success/raw 证据；不为修日志再提交 GPU。

## 4 边界

- 仅证此 2point×2instance、固定 fixture/PointSize=1 变体、passthrough/testPS、64×64 合成配置的 compute→raster 数值/像素。
- 不证原 95bf GS PointSize 默认、游戏 PS/guest、任意 topology/输入/多 z、生产 host；无 spirv-val；PointSize=1 仍测试值。
- 无额外 VS-only/额外 CB/第二提交。

## 5 文档/状态

- INDEX/EXPERIMENTS 加 exp143（2×2 raster/success/evidence-limited）；request 143 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动下一轮执行。
