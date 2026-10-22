# report99 · 高槽 TEX matcher/launcher 计划与 no-guest 测试（无 gate/guest/host 运行）

日期：2026-10-22 00:57–01:20（本机）
HEAD **`36bba17`**（未变；本轮无生产代码/库/profile/lock 改动、无提交/push）。
目录：`/path/to/external-drive/xc3/work/experiments/tex27-highslot-final-plan/`

---

## 0 本轮内容

- 修正 report98 的两处文档/测试问题（见 §1）；
- 沿独立 supervisor `supervise9.py` 实现唯一验收链（kd → K st1 → tex-final st1 reg16 aid33 → d），字段/矛盾/顺序规则按
  review 逐条落地；
- launcher 默认 preflight-only，`--launch` 路由到 `supervise9.py` 但**未执行**（只用替身 supervisor 验证路由/env）；
- preflight 身份实测通过；8 组 no-guest 测试全过；未运行 host、无 gate/guest。

## 1 文档/测试修正（不重造历史）

- report98 追加 §8 勘误：新 host 实际 `compileline` sha256
  `43499dc9ec77a4c48de265c9fe0c764e5aeace5b9e3eda8d20ee07067208db63`、`build.log` sha256
  `237bbc2bd55dd856971507b6aecddd0d0a39601cd7b57ce459a82560fb7ceda5`，`build.rc` 仍 `93ff7811…`；正文不改，以此为准。
- `t_source_order.py` 原用 `text[tf-200:tf+200]` 把行号当字符下标；已改为对 if/MLOG 相邻行切片做**静态**断言（条件不含
  TEXU、字段齐全），报告中注明静态断言不等于运行分支测试。

## 2 Matcher（`supervise9.TexFinal`）

唯一成功链：

1. `[kd]` 锚点：`fs` 必须是目标 PS（bare 或 `_b`）；`_bf` 或其它 PS 首次 forced draw → terminal
   `target-not-obtained`；实际 VS 从 `[kd]` 记录，不预设。
2. 同 pass `K st1 key=4f30af45c2f40e25`。
3. 同 pass `[tex-final] … st1 key=该 PS reg16 aid33`。字段逐一解析：
   - `sres/fb/fit/afr/fallback ∈ {0,1}`；`actual=real` 当且仅当 `fallback=0`，`dummy` 当且仅当 `fallback=1`；
   - `sres=0` 且 `fallback=0` → invalid；`sres=0` 且任一 `fb/fit/afr=1` → invalid；`sres=1` 且 `fallback=1` 合法
     （feedback 替换可给 nil 后走 dummy）；
   - `tid` 必须 uint20；`sser` decimal uint64；`slot` plain uint64；`fmt/dims/type` 必须 unsigned 数字（负值/坏串/溢出拒绝）；
   - `reg16 aid33 st1`；reg/aid 不符 → terminal `unexpected-candidate-record`；
   - real 且 slot0 或任一维为 0 → terminal `consistent-but-abnormal`；dummy 且 slot0 → `consistent-but-abnormal dummy-slot0`；
     dummy 非零 slot 正常；`sser` 是注册对象 serial，不是 final view 身份，也不从 serial0 推未解析。
4. 同 pass `d … vs=<完整 key> fs=该 PS`；`vs` 必须与 `[kd]` 一致，有 `K st0` 时也须一致；无 `K st0` 只说明缺第三处来源
   （kd 与 d 两个来源已一致），不是缺口。

重复/错 pass/stage/key/非法字段/矛盾 → `diagnostic-record-invalid`，不后补；`d` 先于 tex-final 毒化该 pass；其它 stage、
低槽记录正常；`sbuf-final`/`img-final` 旧记录**不会**触发成功（测试覆盖）。

## 3 Launcher 与 preflight

- `run-highslot.sh`：默认 preflight-only，打印 child DM 配置（`DM_NVN_KEYDUMP=4f30af45c2f40e25:1`、PSO/SHDUMP/MEMSTAT、
  六输入、en-GB/audio0）；`--launch` 会 exec `supervise9.py`（180 s 含 10 s/2800 MiB 采样锚定 gate、reviewed 阈值、两条固定 GS、
  `env -i` 白名单）——**本轮未执行**，仅用替身 supervisor 验证路由。
- preflight 实测（`preflight.txt`）：

[Fenced excerpt omitted from the shareable research record.]

- 负例（副本/替身）仍全部拒绝：假 patched 树、89 pairs、缺 metal、sampler reg15。

## 4 测试（no-guest，`tests/run.log`）

| 测试 | 覆盖 |
|---|---|
| `t_preflight` / `t_preflight_negative` | 身份与四类负例（host/patched/pairs/metal/sampler） |
| `t_source_order` | PD 3855 < fallback 3861 < slots 3875 < tex-final 3881；局部 if/MLOG 静态断言不含 TEXU |
| `t_texfields` | real/dummy、source1+feedback+fallback 合法、source0 无 fallback / 带替换非法、actual 矛盾、reg/aid、tid/sser/slot/fmt 数字域、real slot0/零尺寸、dummy slot0、跨 pass、乱序、重复、`_bf`、其它 PS、旧 sbuf/img 记录 |
| `t_gate` | reviewed gate 的慢首样本/CSV 越界/终端低阈/采样错误/0 秒/T0 |
| `t_launch_guard` | gate 期 signal 与 deadline 均不启动 child；matcher real/dummy smoke |
| `t_launch_path` | 真实 launcher 默认 preflight-only、不建 run 目录；替身 `--launch` 路由 host/gate 2800/10 s/180 s、KEYDUMP、无冲突开关、PSO/SHDUMP/MEMSTAT、en-GB/audio0、六 inputs |
| `t_e2e` | synthetic child：real、dummy、feedback-dummy、invalid-reg、wrong-PS、半行；成功写 `triple.txt`，terminal 不写 |

全部通过；无 host 运行。

## 5 产物

| 文件 | sha256 |
|---|---|
| `supervise9.py` | `b8e4faf074a819f814e26489e9cc64a6478217ebfa7813e5c0d37a7f7ba327d5` |
| `run-highslot.sh` | `a8f5a992ef988dd2327366b3e9a63db5a376d82ef196f04abb2bb85debe2831b` |
| `preflight.py` | `3700b2aa388ff11ea6567a9ed6433e11eb6ccd2543b1c0e08d9f3ce5600f0f1e` |
| `plan.md` | `4a961dc14875853f2171482fbaecdd62567f020c566cd14691c2490d6e1ff479` |
| `README.md` | `385a7e70bd88da4c6c355dca86b8c33bed6bf3298871d9fa5b4608420bc319d1` |
| tests + logs | 见目录；`run.log` sha `ab9c104edbe88433c475289fbce7877e99c8c8e99a65490a63ee232f0a2b9dda` |

## 6 边界

- 未 gate、未 guest、未运行 host；`--launch` 未授权，替身测试不等于启动。
- tex-final 只证明编码期最终纹理参数选择；不证明 GPU 执行/采样/内容、真实 NVN 槽映射或 sampler。
- TEX27/base20、SSBO110/510、IMG120 仍是候选；fout/GS/输入/阈值/库值未动；旧 host/计划/证据未覆盖。
- 旧 SSBO/image 记录不是成功路径；不复制旧 matcher 成功路径。

## 7 文档与状态

- INDEX/EXPERIMENTS 加入 exp99；request 098 补真实 relay
  `codex-xc3-texfinal-offline-32c250610c54431fa9f2d9735e1d4ade` 与 `accepted:true`；request 099 原样归档
  （local id `xc3-texmatcher-plan-099`；relay id 未提供，unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；无 commit/push；AGENTS.md/XC3-SETUP.md/共享 dmhost/旧证据未动。
- 停止等 review；不自动授权 launch。


---

## 8 追加勘误（主管 feed 反例；原文保留）

主管用生产 `TexFinal` 直接 feed 复现两个反例（共同前缀：kd F1/p1 vs=c013… fs=4f30…_b；K F1/p1 st1 目标；合法 TF
F1/p1 reg16aid33 tid1 sser1 sres1 fb0 fit0 afr0 fallback0 actualreal slot0x1 fmt70 1x1x1 type2；d F1/p1 同 pair）：

- **A**：`kd,K,TF(p2),TF(p1),d` → 返回 complete。`p!=self.pass_` 分支 `return None` 静默忽略了错误 pass；而
  `t_texfields` 的 wrong-pass 用例还明确期望 None，report99 中“错 pass invalid”的表述不实。
- **B**：`kd,K,TF(F2),d(F1)` → 同样 complete；解析了 frame 却未与锚点比较，允许跨 frame 拼接。

**修复**（仅 matcher/tests，无生产代码/host/库变化）：
- `kd` 锚定 frame+pass；
- 目标 PS 的 `tex-final`（完整目标 key）若 stage≠1 或 frame/pass 与锚点不符，立即
  `diagnostic-record-invalid` 终局，不等后续好记录；目标 key 出现在错误 stage 不再被悄悄过滤；
- 锚定 pass 内的 `K st0`/`K st1`/`d` 也检查 frame 一致；
- 正常其它 shader/stage 与低槽日志仍允许；完整 key/后缀规则未放宽。

**测试更新**：`wrong-pass` 改为拒绝；新增 `bad-pass-then-good`（首次坏记录已 terminal，后续完整链不能变 success）、
`mixed-frame`、`k-frame`、`d-frame`、`tf-stage`、`other-stage-ok`；`t_e2e` 新增 `bad-pass-then-good` 与 `mixed-frame`
（真实 supervisor 入口，terminal、无 `triple.txt`、child 回收）。原测试/报告的成功记录不改写，本节即勘误。

新 sha：`supervise9.py 48204a250a4093316f94131a33ca2a2ecb844dba2aa89d4c2639f02d967f9fc6`、
`t_texfields.py 8c56bc936d27a12b8bf251513cffab39e3378e1035de9328403a523a91e5df4a`、
`t_e2e.py 4198dc8d42b54374b302cdb4050c2340b05c175bf1a7b9b003e6cfe7697c049c`、
`run.log 7c40d7fee81191f6c1ba7766d19242a2b972104ea929c75c01152e54bd6e9c1b`。
