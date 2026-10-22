# report135 · vb_data0 view 修复后的 VS→GS 16×16 单次提交

日期：2026-10-22 11:25–11:50（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；唯一 commit=1（内含 VS/GS 两次 dispatch，共两次 stage dispatch）、无第二 commit/重试；无 guest/gate/生产/库/guard 改动、无 commit。
环境固定：`MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1`。

---

## 0 结果

- 只修 vb_data0 R32Float texture-buffer 的 **view width=1→4 / bytesPerRow 4→16**；ib_data/trb 保持 width1/4B；未改 shader/metallib/fixture/expected/PointSize/数值/同步。
- 新 extent contract 与实际 view 查询通过：`vb width=4 bytesPerRow=16 offset=256 payload=528`，`ib width=1/4/256/516`，`trb width=1/4/256/516`。
- 一次 command buffer，两个严格串行 compute encoder：VS dispatch(1,16,16)、GS dispatch(1,16,16)，每个 encoder 一次 dispatch；CB **commit=1**；wait=0、status=4、error=none。
- **payload PASS**：VS `(1,2,3,4,1)`；GS `(0,2.25,3,4,1),(2,2.25,3,4,1),(0,1.75,3,4,1),(2,1.75,3,4,1)`；IB `0,1,2,3,0xffffffff`。
- `readback.bin` 120B sha **b794fad5…**，与 expected 完全一致；只读 0/1/5/6/7 不变、8 资源 guard 全过；poison 全部覆盖；GPUStart/End `100766.224392/…480`。

## 1 修复/合同

- 唯一资源行为 diff：`vb_data0` 使用独立 width=4 descriptor（bytesPerRow16）；ib/trb 使用 width1（bytesPerRow4）。精确 diff `harness/extent.diff`。
- 新 `texture_extent.h`：format bytes=4、view width、bytesPerRow、offset/payload、min/max index；检查 width>=max+1、offset+need<=payload、乘法/加法溢出；测试 width1/2/3 拒绝、width4 接受、ib/trb width1 接受、zero/offset/payload/index overflow/format/row 拒绝。
- 执行前查询实际 `MTLTexture.width/pixelFormat/textureType` 与 backing buffer offset/payload，并打印；不是只信 descriptor 对象。
- submit contract 16×16（groups1、threads16,16,1、PSO max640、device dims）通过；sampler supportArgumentBuffers=1；预算 allocated=136464<16MiB；shared vertex_output hazardTrackingModeTracked 检查通过；`useResource`/AB 读写显式。

## 2 执行/读回

- 两 stage 各一次 dispatch（总 stage dispatch=2）；一个 command buffer；commit=1；两 encoder 严格顺序，未使用 concurrent dispatch。
- 读回 VS5/GS20/IB5 共120B 与 expected bit-exact；raw/expected/result/execute.log/stderr 保存；写 rc 检查通过。
- validation 环境无 error；PSO max640 与 16×16 合同相容，未改线程/环境。

## 3 证明边界

- 成功仅证：**此新 view 配置 + fixture-defined PointSize=1 GS 变体 + 16×16 测试组形状** 的单点合成 VS→GS 数值/流水。
- 不证原始 95bf（PointSize 未初始化）、真实 guest GS、游戏像素、其它 topology/input/多 z/多 invocation；不把 fixture PointSize=1 当原 GS 语义。
- VS/GS 都是 PointSize 但 producer 不同：VS 的 word4 是 VS 产生，GS 不转发 VS word4；此点继续保留。
- 未启用 spirv-val；原 SPV LocalSize 32×32 仍标注，16×16 是新实验合同。

## 4 文档/状态

- INDEX/EXPERIMENTS 加 exp139（VB view fix/one commit/synthetic success/evidence-limited）；report134 旧失败证据保留；request 139 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 45 分钟内完成；停止 review，无自动下一轮/第二 commit。


---

## 7 统计勘误（checker 边界）

- §1/日志的 `payload=528/516` 实际是 backing buffer 总字节（含两侧 256B guard）；有效 payload 是 **VB 16B / IB、TRB 4B**。
  不能把 528/516 称作 payload。
- 本次 width4/read0..3 实际落在 16B payload 内，GPU 数值证据保留；但旧 checker 以 backing 长度当 payload、对 min>0 低估
  end、row 乘法未先查溢出，**未证明**会拒绝落在 guard 的 view。新 helper/CPU 测试见 report136；未重跑 GPU。
- INDEX 的 VS→GS synthetic milestone 仍保留为 validated-limited，不撤真实数值，也不称 checker 已全覆盖。
