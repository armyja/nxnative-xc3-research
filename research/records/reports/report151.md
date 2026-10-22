# report151 · 第二次单次真实授权：gate 第二样本拒绝

日期：2026-10-22 09:09（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；一次真实 gate 尝试；0 host/0 guest/0 GPU；无生产/库/lock/chain 改动、无 commit。

- fresh run：`/path/to/external-drive/xc3/work/experiments/gsres-real-run-20261022-090903`
- preflight PASS；argv/env 按契约。
- gate：第一样本 `available 2802 MiB`（≥2800），第二样本 `2795 MiB < 2800`，exit=3；`launch=` 空。
- 0 host/0 guest；无 supervisor/host 残留；按单次授权失败即结束，未重试/未改阈值/未清进程。
- 证据：`last-launch.log`、run/gate.csv（两行）、run/timing.txt。
- 本授权轮结束；下一次真实观测需 owner 再次明确单次授权。旧 run 不复用。
