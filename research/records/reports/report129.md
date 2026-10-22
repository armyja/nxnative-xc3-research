# report129 · GS-only PointSize 定义性变体 + prepare-only harness

日期：2026-10-22 07:00–07:40（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；无 dispatch/queue/command buffer/encoder、无 GPU 执行/翻译/build、无生产/库/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 结论

- 建立 **fixture-defined-pointsize** GS 变体：只加一行 `_43[4]=1.0`，不改 position/index/Emit/采样/guard/stride/绑定；metal/metallib 单次构建 rc0。
- 建立 GS-only 的 packed fixture + manifest、prepare-only ObjC harness；harness 成功准备 3 个 argument buffers、小 buffers、1×1 纹理与 texture-buffer、sampler、PSO，并打印资源清单；**没有** queue/command buffer/encoder/dispatch。
- 负例：`--dispatch` 拒绝 rc2；坏 library rc6；缺 kernel rc7；缺 fixture rc3；截断 fixture rc10；静态 API 检查 0 命中。PSO 失败路径代码返回 8，本轮未构造受控 PSO-failing metallib，未以 rc0 代替。
- PointSize=1.0 仅 **synthetic 测试假设**，不是 NVN/GS 真实默认；position oracle 与 PointSize 解释分开。

## 1 变体

- 原：`gs-ascompute-metal/msl/gs.metal`（sha `da1d8ecd…`）。
- 变体：`msl/gs-fixture-pointsize.metal`（sha `3faf31d8…`）；diff sha `a44cc9c1…`，唯一新增：
  ```
  +    _43[4] = 1.0;   // fixture-defined PointSize test value; not a proven NVN/GS default
  ```
- 构建：`xcrun -sdk macosx metal -c -fpreserve-invariance` → AIR `4b92ef09…`；`metallib` → `c3d170fd…`；各一次，无重试。
- 原库/生产文件未改；变体只用于测试。

## 2 Fixture（GS-only，不含 VS 执行）

`fixture/fixture.bin` 66716 B（sha `9da34cd8…`），`manifest.json` sha `0eed087c…`：

| section | offset | bytes | 内容 |
|---|---:|---:|---|
| vb_info | 0 | 1056 | m0=(1,1,0,0), m1=(1,0,0,0), m2[0]=(4,0,0,0), m3[0]=0 |
| cbuf | 1056 | 65536 | cbuf3[0].x=2.0, y=0.5；其余0 |
| vertex_output | 66592 | 20 | (1.0,2.0,3.0,4.0,1.0) |
| geometry_vb | 66612 | 80 | 初始0，20 words |
| geometry_ib | 66692 | 20 | 初始0，5 uints |
| trb | 66712 | 4 | float 0.0（bitcast uint 0）|

- **明确 GS-only**：直接提供 `vertex_output`，不调用 VS；`m2[0]=(4,0,0,0)` 关闭 y/z/w 分量，若执行现 VS 不会得到该行。
- CPU oracle（独立代数，exact float）：positions
  `[0,2.25,3,4], [2,2.25,3,4], [0,1.75,3,4], [2,1.75,3,4]`，index `[0,1,2,3,0xffffffff]`。
- geometry_vb 的 word4 = PointSize 测试值 1.0（fixture defined）；不是真实默认证明。

## 3 prepare-only harness

`harness/prepare_gs`（sha `1b9f7bb9…`；source `7a3432bf…`）：

- 加载变体 library、`main0` kernel，创建 PSO：**pso=ok，TEW32，maxTotalThreadsPerThreadgroup1024**。
- 资源（含 256 B 前后 canary，canary 均为 `a5`，未改）：
  - `vb_info` 1568 B @256；`cbuf3` 66048 B @256；`vertex_output` 532 B；`geometry_vb` 592 B；
    `geometry_ib` 532 B；`trb_data` 516 B（1 float + guard）。
  - 1×1 R32Float texture = 0.5；`texture_buffer` trb 1 element；nearest/clamp sampler。
- 三个 argument encoder（实际 kernel buffer index）：encoded_length 32/24/8；按 MSL id：
  set0 id0 vb_info、id1 cbuf3、id2 texture、id3 sampler；set1 id0 vertex_output、id1 geometry_vb、id2 geometry_ib；
  set2 id0 trb texture。**按真实 id，不抄 SPV binding**；自动重排见 report127。
- 输出明确 `prepare-only`、资源长度/offset/canary、`command_queue=NOT_CREATED command_buffer=NOT_CREATED encoder=NOT_CREATED dispatch=NOT_CREATED`。
- **没有** `MTLCommandQueue`/`MTLCommandBuffer`/compute encoder/dispatch；没有 guest/资源轮询/读回。

## 4 负例/静态

| 测试 | rc |
|---|---:|
| `--dispatch` | 2（在任何 device/资源前拒绝） |
| 坏 library | 6 |
| 缺 kernel | 7 |
| 缺 fixture | 3 |
| 截断 fixture | 10 |
| 静态 grep queue/commandBuffer/encoder/dispatch | 0 命中 |

- PSO 失败显式 `return 8`；未构造受控 PSO-failing metallib，故不声称该路径已执行验证。

## 5 边界/下一步

- 这是 **GS-only prepare harness**，不证明 VS→GS、GPU 执行、像素/数值、dispatch/indirect/sync。
- PointSize=1.0 是测试定义；position oracle 的数值来自 fixture 代数（texture0.5/cbuf2,0.5/vertex1,2,3,4），不是 GPU 结果。
- 可审查的下一步是一次单独授权的 **prepare-only 复核**或未来 dispatch 设计；本轮不实现执行路径、不自动下一步。host argument buffer/资源布局仍按本 harness 的 id 表，未成为生产接线。

## 6 文档/状态

- INDEX/EXPERIMENTS 加 exp133（GS-only prepare/evidence-only）；report128 §E 范围限界已加；request 133 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动 dispatch/后续。


---

## 7 追加限制/勘误（主管 review；原文保留）

- 旧 harness 的 sampler 未设置 `supportArgumentBuffers=YES`；argument buffer 中 setSamplerState 的兼容性未证。保留旧 `prepare.log` 作为旧证据，
  不能把旧 prepare 当已满足；新 v2 harness 已设置并记录。
- 旧 harness 的 `section()` 把缺失/类型错误静默转 0，且在分配后才做范围检查；无总预算。v2 已改为 device 前固定六 section
  契约/SHA/预算/减法范围校验，详见 report130。
- 旧 `dumpBuf` 只采样首尾字节，不是完整 256B guard；v2 改为逐字节两侧 guard 校验。
- 报告129 的“无 build”应限定为**无生产/host/shader 翻译 build**；该轮实际有 metal/metallib 与 ObjC harness 编译。
