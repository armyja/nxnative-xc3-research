# report136 · texture extent 字段/边界修正（CPU-only）

日期：2026-10-22 11:55–12:20（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU；无 device/PSO/资源/queue/commandbuffer/dispatch/GPU、无生产/库/guard 改动、无 gate/guest/资源采样、无 commit。

---

## 0 report135 统计勘误

- report135 日志的 `payload=528/516` 实际是 **backing MTLBuffer 总字节（含两侧 256B guard）**，不是 payload：
  - vb_data0 backing 528 B = 256 guard + **16 B payload** + 256 guard；
  - ib_data/trb backing 516 B = 256 + **4 B payload** + 256。
- 旧 checker 把 `b.length`（528/516）当 payload，且用 `offset+need<=payload_len` 混用总长度；本次 width4/read0..3 恰好落在
  真实 16B payload 内，所以 GPU 数值仍有效，但 checker **没有证明**会拒绝落在 guard 的 view。
- 旧 `need=(max-min+1)*4` 对 min>0 低估结束地址；`width*4` 在 row 比较前也未做溢出检查。report135 的有限 GPU 结果保留；
  checker 缺口与本次安全访问范围分开，勿称 checker 已全覆盖。

## 1 新 helper 字段（固定 R32Float）

`harness/texture_extent.h`（sha `4774b08b…`）：

[Fenced excerpt omitted from the shareable research record.]

检查顺序/语义：
- `element_bytes==4`；`width>0`；先做 `width*4` 溢出检查，再要求 `row_bytes==width*4`；
- `payload_offset<=backing_len`、`payload_len<=backing_len-payload_offset`（减法，无加法溢出）；
- `view_offset<=payload_len`、`width*4<=payload_len-view_offset`（view 整体落 payload，不落 guard）；
- `min<=max`、`max<width`、`max*4+4<=view_bytes`；所有乘法/加法均有域检查。

## 2 CPU tests（同一 helper，无并行实现）

`test_extent.c`（sha `881e0909…`，binary `0acc43d0…`）全过：
- legal VB backing528/payload_offset256/payload_len16/view0/width4/row16/read0..3；
- legal IB/TRB payload_len4/width1/row4/read0；
- VB width8/row32/read0..7 但 payload16 → **拒绝**（旧 checker 在 backing528 下会接受）；
- payload15、view_offset1、min3/max3+payload4 → 拒绝（view 越 payload/guard）；
- payload_offset513/backing259 → 拒绝；
- width=UINT64_MAX/4+1 → `width*4 overflow` 拒绝；
- row8、max4、payload0 等字段混用 → 各自明确拒绝。

- 算术覆盖点：`width*4`、`view_bytes`、`max*4+4`、`payload` 减法；测试命中相应错误串，不只是被无关前置条件挡住。
- negative 域不适用（全 uint）；未用 float/NaN 比较。

## 3 新 harness（仅编译，未运行）

- 新副本 `harness/execute_vsgs_extent.m`（sha `510c060a…`，binary `81e3da25…`）调用新 helper；日志字段明确
  `backing/payload_offset/payload_len/view_offset/width/row`，不再把 528/516 叫 payload。
- 由于 Metal texture 对象没有公开的 backing buffer/offset 查询（本 SDK 未用），backing/offset/row 记录为
  **创建参数输入**，width/pixelFormat/type 仍实际查询；未声称查询到了 texture backing。
- 新 harness 输出路径已指向 `gs-vsgs-extent-corrected`，不覆盖 report135 readback。
- **未运行 device/prepare/PSO 路径**；原真实 binary/source/readback 未改。

## 4 边界/状态

- 新 helper 尚未替换真实成功 harness；report135 的 GPU 成功仍是旧 checker 下、恰好安全访问的 limited evidence。
- 未运行 GPU；不证新 checker 与真实 view/guard 的运行时交叉验证（CPU only）。
- 文档：report135 §7 追加统计勘误；INDEX/EXPERIMENTS 加 exp140（extent correction/CPU-only）；request 140 归档。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 30 分钟内完成；停止 review，无自动下一步。
