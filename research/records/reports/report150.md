# report150 · 单次真实观测授权：gate 拒绝（未启动 host/guest）

日期：2026-10-22 08:44（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；一次真实 gate 尝试；无 host/guest/GPU、无生产/库/lock/chain 改动、无 commit。

---

## 0 结果

- Owner 给出单次真实观测授权后，执行唯一一次真实 launcher 路径，fresh run：
  `/path/to/external-drive/xc3/work/experiments/gsres-real-run-20261022-084403`
- preflight PASS；固定 host/supervisor/identity/patched/DM env 已打印。
- 10s gate（`--gate-secs 10 --gate-mib 2800`）在**第一次样本即拒绝**：
  `available 2758 MiB < 2800 MiB before launch`；`gate.csv` 只有 1 行（elapsed 0）。
- 因此 **0 host、0 guest、0 GPU、0 观测**；`timing.txt exit=3`，`launch=` 空。没有 host/supervisor 残留进程。
- 按授权“一个 gate 尝试、失败即结束、无 retry”停止；未改阈值、未清进程、未重试。

## 1 证据

- `gsres-observe-plan/last-launch.log`、`last-run-path.txt`；**launcher shell rc 文件未保存（not retained/unknown）**，exit=3 由 run/timing.txt 直接记录
- run 目录 `gate.csv`：`0.000,16384,26097,148524,1944,2758`
- `timing.txt`：`kind=gate / reason=not launched... / exit=3 / launch= / gone_at=`
- 旧失败入口 run 保留不复用；本 run 也不复用。

## 2 状态

- 本次失败授权轮结束；没有真实 95bf resource snapshot。
- 下一次真实观测需 owner 再次明确单次授权；不得因“0 guest”重用本轮。
- 无自动 gate/guest/GPU/采样；文章意见已由主管直接给出（645 底座/成本、GS/TF/整数 RT 分类、机器码≠完整环境契约等），本轮不扩 TF/全 GS/视觉 AI。


---

## 3 证据勘误

- 复核发现 `gsres-observe-plan/last-launch.rc` 不存在；此前报告把它列为已保存证据是错误的。未事后创建伪 rc、未重跑 launcher。
- gate 拒绝结论不变：`run/timing.txt` 明确 `exit=3`、`kind=gate`、`reason=available 2758 MiB < 2800`；`last-launch.log` 与 `gate.csv` 保留。
- 该 rc 缺失不影响 1 gate/0 host/0 guest/0 观测的判定。
