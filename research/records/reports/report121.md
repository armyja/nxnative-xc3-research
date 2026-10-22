# report121 · kdgeom gate/guest 成功：目标 PS draw 的 geometry 来源含 95bf

日期：2026-10-22 04:14–04:16（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；无生产/库/facts/阈值改动、无提交。
Run：`/path/to/external-drive/xc3/work/experiments/kdgeom-plan/run-20261022-041419/`

---

## 0 结果

- 第 4 次 gate（前三次分别 2756/2757/2738/2772 MiB 拒绝）在关闭 Chrome 后通过：**11 samples，min available 2850 MiB**。
- 唯一 guest 在约 65 s 命中目标 PS；`kind=geom-hit`，child exit=0，无残留。
- **geometry 来源 present/serial=359，nstage=3，cached=3/3，keys=[d1657e5077b26d1d, 95bfab6122539993,
  2e16c536b845ea0e]**；目标 GS 在 input index 1（不是 stage 表）。
- 同一命中 draw 的 command primitive 为 **0 = NVN_DRAW_PRIMITIVE_POINTS**（`nvn.h`）；direct，count=2304，instances=1，
  base_instance=0；与 `[kd]` header 完全一致。

## 1 原文（boot.log 240/241）

[Fenced excerpt omitted from the shareable research record.]

- `source=present/359` 是 geometry program 的 serial，不是地址，不能跨 run 比较。
- `keys` 是 `prog_key_cached` 的 input index 列表；95bf 命中只说明该 geometry 来源含目标 key，**不证明 GS 已执行/已发射**。
- `prim=0` 是 command primitive（Points），不是 MTL 映射后的 topology，也不是 GS 声明的 input/output topology。

## 2 时序/资源/回收

- gate：11 samples，elapsed 0.000→10.092，min 2850 MiB；launch_at=10.111。
- guest：first_at=65.057，term_at=65.075，gone_at=65.200；exit=0。
- 236 samples：min available **1852 MiB**，max RSS **723664 kB ≈ 706.7 MiB**；log 35648 B；dump 6.25 KiB。
- 两条原 GS 内容豁免（95bf/a841，64.544 s，hash 一致）；无非豁免 dump 停止；无 child 残留。
- 停止原因 `geom-hit`，不是 deadline/dump/resource。

## 3 证明边界

- 证明：该次 guest 命令绑定到目标 PS 的 draw，其 geometry 来源（`S.bst[2]`）确实包含 `95bfab6122539993`；该命令的
  原始 primitive 为 Points，direct count/instances/base_instance 与 header 一致。
- 不证明：GS 执行、每输入 primitive invocation 数、真实 GS input topology、输出/像素/GPU 内容；SPV interface 仍未解。
- 仍无 facts 生成/回写、无 asCompute/GS 实现、未扩 GS 白名单。

## 4 文档

- INDEX/EXPERIMENTS 加 exp125（kdgeom successful observation/evidence-only）；report120 的 ready plan 现已执行一次。
- request 124 无 relay id；request 125 原样归档（local id `xc3-kdgeom-hit-125`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无自动后续。


---

## 5 勘误

- §0 的“第 4 次 gate（前三次分别四个数）”措辞有误：实际是**此前 4 次拒绝，本次为第 5 次 gate 并通过**。各次授权
  边界分别保留，本次成功不写成早前拒绝轮内的重试。
