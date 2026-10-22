# report152 · 关闭 Edge 后重试：gate 2784 MiB 拒绝

日期：2026-10-22 09:22（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；一次 gate 尝试；0 host/0 guest/0 GPU；无生产/库/lock/chain 改动、无 commit。

- 按 owner 要求关闭 Microsoft Edge（osascript quit，Edge 已退出）；点测 available 2884 MiB。
- fresh run：`/path/to/external-drive/xc3/work/experiments/gsres-real-run-20261022-092215`
- gate 首样本：`free=12910 inactive=158787 speculative=6484` → **available 2784 MiB < 2800**；exit=3，`launch=` 空。
- 0 host/0 guest；无 supervisor/host 残留；按单次 gate 失败即结束，未重试/未改阈值/未清其他进程。
- 证据：`last-launch.log`、run/gate.csv、run/timing.txt。
- Edge 仍保持关闭；下一次真实观测需 owner 再次明确单次授权。
