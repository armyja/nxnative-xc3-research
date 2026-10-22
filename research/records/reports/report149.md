# report149 · 真实 launch 入口失败 + interpreter 修复

日期：2026-10-22 22:10–22:30（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU；无 gate/guest/host/device/GPU/资源采样（失败发生在 supervisor 启动前）、无生产/库/lock/chain 改动、无 commit。

---

## 0 真实 launch 失败（一次授权轮已结束）

- Owner 说“可以启动”后，按 ready-for-authorization 路径执行一次真实 launcher，fresh run：
  `/path/to/external-drive/xc3/work/experiments/gsres-real-run-20261022-081143`
- preflight PASS，DM env/argv 按 run-kdgeom 契约打印；launcher 直接 Popen 无 shebang 的
  `supervise_gsres.py`，报 `OSError: [Errno 8] Exec format error`。
- 失败在 **gate 采样、host Popen、guest 之前**：0 gate、0 guest、0 host；只创建 run/save/temp/shdump。
  `pgrep` 无 supervisor/host 进程；按“任何失败结束、无 retry”停止，未修后重跑。
- 证据：`gsres-observe-plan/last-launch.log`、`last-run-path.txt`；run 目录保留不可复用。
- 旧 real launch 记录不删除，也不改写为成功。

## 1 入口修复

- `launcher.py` 默认打印 argv 与实际执行 cmd 均改为 `[sys.executable, fixed_supervisor, ...]`；mock/stand-in 同样由
  interpreter 调用；不改 supervisor/shebang/host/库/profile/chain。
- 新增**无 shebang、chmod 0644** 的 Python 替身回归：真实 launcher 入口执行，断言 `interpreter==sys.executable`、
  `program==standin`，不依赖 shebang/执行位。
- 真实 supervisor `python3 supervise_gsres.py --help` rc0，仅 argparse help；未 gate/采样/host/device。`
  import gsres_parser_frozen` rc0，无副作用。
- identity 增加 `launcher` 路径/SHA，preflight 校验；launcher SHA 进入身份 manifest。
- 默认 preflight-only：打印完整 DM 配置 + `argv=[python3, supervisor, ...]`，不建 run/child；不存在 run 路径验证未创建。
- 测试 `test_preflight_launcher.py` **47 checks FAILS0**；mock route 断言 argv[0]=interpreter、argv[1]=固定 supervisor；
  real `--launch` 未重跑。

## 2 边界/状态

- 真实 gate/guest 仍未授权；本次失败授权轮不可重用；下一次真实观测需 owner 重新明确单次授权。
- 真实 95bf resource snapshot 仍未取得；split 探针、真实 registry/cbuf/TF 等边界照旧。
- 文章意见主管已直接给出：645 是底座/成本非进度，GS/TF/整数 RT 分类正确；需收紧 645 当前审计范围、TEX27/SSBObase
  候选、TF stub 未证生产消费、“机器码≠环境契约”、TotK/XC3 数字与 savestate 需 primary source；方法上 evidence vector/
  批量离线/代表点有用，compiler/PSO 只是兼容性 oracle，VLM 不替代数值/pixel oracle。下一阶段不扩 TF/全 GS/视觉 AI。
- STATUS：ready-for-review，not launch-authorized；无自动重试/guest/GPU。


---

## 3 测试命名勘误（非阻塞）

- `tests/test_preflight_launcher.py` 生成的 `stand.py` 字符串实际以 `#!/usr/bin/env python3` 开头，因此该 case **不是**
  “无 shebang stand-in”；`chmod 644 + interpreter` 只证明“非可执行脚本由解释器调用”。
- 真实 `python3 supervise_gsres.py --help` 的 rc0 是另一项实际证据（supervisor 本体无 shebang），不能与该 stand-in
  混称。
- 测试名称/注释应改为“non-executable script via interpreter”；后续维护可去掉 stand.py 的 shebang，本轮不改日志、
  不重跑套件、不重编 host。
- 旧 47 checks 结果保持有效，仅此命名/证据范围勘误。
