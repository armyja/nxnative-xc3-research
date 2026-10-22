# report134 · VS→GS 16×16 单次合成提交：payload FAIL（停止，无第二 commit）

日期：2026-10-22 10:45–11:20（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD；唯一一次 GPU commit；无第二 commit/重试、无 guest/gate/生产/库/guard 改动、无 commit。
环境：`MTL_DEBUG_LAYER=1 MTL_SHADER_VALIDATION=1`（固定，未移除）。

---

## 0 结果

- CPU 条件全过：两份 kernel body 仅依赖 `thread_position_in_grid`（无 local/threadgroup/workgroup/simd/共享内存/barrier/归约）；
  256 gid 与旧 1024 gid 均只有 `(0,0,0)` 过 x/y guard；contract 16×16×1 通过（PSO max640，256 产品合法）；
  payload/guard/预算/identity 测试通过。
- 唯一一次执行：一 queue/一 command buffer；VS encoder（1 dispatch 16×16×1）→end→GS encoder（1 dispatch 16×16×1）
  →end→commit=1；wait=0、status=4、error=none；GPUStart/End `100511.648406/…485`。
- **payload FAIL**：VS 输出 `(1,0,0,0,1)`，期望 `(1,2,3,4,1)`；GS positions 因 VS y/z/w=0 而成为
  `(0,0.25,0,0),(2,0.25,0,0),(0,-0.25,0,0),(2,-0.25,0,0)`；IB 正确 `0,1,2,3,0xffffffff`；只读/guard PASS。
- 依授权停止，无第二 commit、无参数/validation 调整。

## 1 CPU/契约

- 新 helper `submit_contract_16.h`：groups(1,1,1)、threads(16,16,1)、max>=256、device 各维、零/溢出/乘积；
  `test_contract16`：allow640、reject255、reject-dim、reject-groups、reject-threads、reject-zero，fails0。
- 新 harness `execute_vsgs` 在 queue 前检查两 PSO contract（均 max640→ok）与 shared `vertex_output`
  `hazardTrackingMode==Tracked`；`useResource` 对 VS/GS 的 buffer/texture/AB 显式声明。
- 双 encoder 严格串行（VS end 后 GS），各一次 dispatch；CB commit 恰一次；bounded completion 10s。
- CPU payload validator 120B（VS5+GS20+IB5）逐 byte/word exact；120 字节变异、NaN/Inf 全拒；guard/budget/身份负例
  pre-device。输出文件写入 rc 检查；`result.txt`/`readback.bin`/`expected.bin` 保存。

## 2 失败分析（无第二 commit）

- 直接观察：VS 只写出 x=1、PointSize=1，y/z/w 全 0；IB 读到的 index 0 正确。最可能原因是 **vb_data0 的
  texture_buffer 描述符宽度为 1**（同一 `tbd` 用于 ib/vb/trb），只能读取 element0，故 vb 的 y/z/w 读到 0；MSL/VS 的
  component enable（m2=(4,1,1,1)）本身已正确。此为事后代码/现象推断，**未被第二次运行证明**；未修 shader/未重跑。
- GS positions 与 VS 输出的零 y/z/w 一致；index 正确说明 VS 的 IB 路径/共享 vertex_output 写/GS 的 IB 写与同步至少
  覆盖了该部分；不能称 VS→GS 全链路通过。
- 未改参数/validation 后重试；失败结果完整保留。

## 3 边界/状态

- 本轮不证 VS→GS 数值/GPU 正确，也不证原 GS PointSize/guest/像素；GS PointSize=1 仍是 fixture-defined 测试值。
- 16×16 是测试组形状，原 SPV LocalSize32×32 仍标注，不冒充原调度。
- 新 output 路径独立，旧 report131/133 证据未覆盖。
- 文档：INDEX/EXPERIMENTS 加 exp138（VS→GS 16×16 attempt/payload-fail/evidence-only）；request 138 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 60 分钟内完成；停止 review，无自动下一轮/第二 commit。
