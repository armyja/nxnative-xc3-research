# report147 · gs-res supervisor 接线 + synthetic child/injection tests

日期：2026-10-22 20:00–21:00（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU 合成测试；无 host/guest/device/GPU/gate/真实资源采样、无生产/库/lock/chain 改动、无 commit。

---

## 0 交付

- `gsres-observe-plan/supervise_gsres.py`：从已审 kdgeom v2 骨架复制，只替换 matcher 适配块/输出文件名/证据写入，并加入 test-only synthetic sampler/dump-after-hit 注入。
- 导入冻结 parser `gsres_parser_frozen.py`（sha `cc7745e7…`），未重写 parser/state；supervisor 使用 `GsResStateMachine`。
- `supervisor.diff` 记录相对骨架的适配边界；gate/sampling/threshold/deadline/180s/Tail/信号/finally 函数体保留；无 prePopen guard（baseline 本身没有，不新增）。
- 合成 child `tests/synthetic_child.py` + 真实 supervisor 入口测试 `run_supervisor_tests.py`：16 cases，rc0/FAILS0，全部 child 被 finally 回收（`gone_at`）。
- 输出 `gsres.txt`（kd 原文+完整 gs-res 原文）与 `gsres.json`（header/record/terminal）；nonhit/invalid 写 terminal 证据，不写 hit。

## 1 验收

- hit/unbound/partial hit：kind=hit，`terminal=hit`，gsres.txt/json 存在。
- nonhit：identity-unavailable，terminal 证据存在，非成功。
- control：invalid-config、diagnostic-error；近似 diagnostic 串 invalid。
- no-record：无 gsres.txt，kind=normal，不称 absent。
- half、bad frame、bad-then-good、wrong VS：invalid，后续好链不救。
- same-poll nonexempt dump：`kind=normal reason=complete dump`，但保留 `terminal=hit`/gsres 证据（`dump-after-hit` test injection）。
- 两 synthetic exempt dumps：继续，最终 hit；exemptions.txt 两条。
- other PS/_bf header：target-not-obtained，无 GS 查询。
- 每 case 记录 kind/reason/success（终局写文件）/gone_at；测试只走真实入口，不直接 state 替代。
- 采样通过 `--test-inject synthetic-sampler` 固定，调用真实 `sysctl/vm_stat/ps` 为 0；dump 内容为合成，非 GS 实数据。

## 2 边界/缺口

- 未实现 preflight.py、launcher.py；无真实 launch/gate/guest/device/GPU；默认 preflight-only 仍未接。
- 无真实两 GS 内容豁免（测试是 dummy 文件/hash），无真实资源采样；supervisor 仅 synthetic-tested，不是 ready supervisor。
- base 骨架没有 prePopen guard；未新增，记录 gap。
- 未改 parser/state 语义；`dump-after-hit` 是 test-only，不在生产路径；正常 match/output 不变。
- 旧证据/host/source 冻结；无 guest/GPU。

## 3 状态

- INDEX/EXPERIMENTS 加 exp151（supervisor synthetic-tested/preflight-launcher absent）；request 151 归档。
- 新 SHA 见 `gsres-observe-plan/identity.supervisor2.sha`、`tests/supervisor_tests.log`。
- 停止 review，无自动 preflight/launcher/guest/GPU。


---

## 4 定点修正确认（主管 review）

- **prePopen guard 勘误**：`supervise_gsres.py:200` 的 `STOP requested→LaunchRefused` 与 `:207` 的 `el()>secs→LaunchRefused` 确实在 Popen 前，
  diff 未改；报告原“base 无 guard”错误，撤回。
- **coverage 不再 fabricate source**：移除旧 `geom source=present/none`；改为 `result/record_obtained/validated/gs_present`，
  short control/otherPS 无 record 时 `gs_present` 为空、`record_obtained=0`，不再称 GS present/none；未通过 validation 不标 validated。
- **truncated-line**：原 `half` 改名；新增 `split`：header + 完整合法 record 分两段，第一段无 newline，0.9s 后第二段；
  最终 hit。测试只证最终 hit，未用额外探针断言中途文件不存在（gap）。
- **no-record**：保留 host-exit case；新增 `no-record-alive` child 存活超过 secs→`wall clock 1s`，无 success artifact，child 回收。
- **sampling failures**：新增 `sample-nonzero`/`sample-empty`/`sample-timeout` 入口 cases（fake child 存活、无目标 record），
  结果 `sampling-error`、finally `gone_at`；synthetic-sampler 分支不调用 sysctl/vm_stat/ps，sh/parse 注入仍走原 test mechanism。
- **checked writes**：gsres.txt/json 写失败→`kind=supervisor-error, reason=evidence-write-failed`，内存 hit 保留但不报 hit；
  用把 `run/gsres.txt` 预建为目录注入写失败，child 回收。
- **dummy exemptions**：两 synthetic exempt dump 继续→最终 hit；只是算法测试，不是真实 GS 内容核实；active exempt 未改。
- **test-only**：`dump-after-hit` 确实进入 complete_dumps 扫描并验证 nonexempt dump 优先；`synthetic-sampler` 固定值。
- 最终入口 22 cases rc0/FAILS0，child 全部 gone_at；旧 16-case log 保留。
- 未完成：preflight/launcher、真实 launch/guest/GPU、真实两 GS 内容豁免；split 中途文件探针为 gap。
