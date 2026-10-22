# report105 · 645 候选库 + matching host（PS 531d fout{2:uint}，纯离线）

日期：2026-10-22 01:12–01:40（本机）
目录：`/path/to/external-drive/xc3/work/experiments/fout-531d-uint2-correct645/`
HEAD `36bba17c0f45d22c78ce987dcfe177f2860d81cc`（未变）；无生产代码/诊断/matcher/facts 变更（仅既有 531d 行）、无 guest/gate/host 执行、无提交。

---

## 0 范围与输入

- 从 `fout-531d-uint2-candidate`（两 key 实验）复制到新目录；`shader_facts.tsv` 与两 key 候选**逐字节相同**
  （sha `3e34a5e20d467ab01f3373644ca318ca15b89205dd907e5637146c1be6ae1446`），避免注释/文件名改动造成 chain 分叉；
  两个 provenance 文件（`provenance-fout-531d-uint2.md`、`provenance-fout-uint-two-key.md`）与 `README-two-key.md` 保留。
- 645 包与 tex27 逐字节相同；profile 与 tex27 的差异仅 `shader_facts.tsv`（新增 531d 行）与 `dmsh_chain.h`；4bae 事实不变；
  TEX27/base20、SSBO110/510/0、IMG120/slots1 不变。
- 生产验证：`validate_map` 645 keys / 0 problems；`validate_pairs` 0 problems；`package_verify` 645/645 通过
  （按 vertex→vs、pixel→ps、compute→cs 映射）。

## 1 chain / header / 构建

- 真实 `dmsh_chain.py`：**`c26257ff13a8`**（与两 key 实验相同，非手写；不同才需查输入/env）；`--check-tools` rc0；
  `--header` 写新目录 header。
- fresh `cas/`、`out/`、`work/`（WORK 已存在）；`J=1`；显式 645 keys 单次构建；`build.cmd`/`build.env` 保存精确
  argv/env/cwd；rc0。
- 摘要：`shaders 645: ok 645`、`shader cache: hit 0, rebuilt 645`、`variant cache: generated 72, hit 1, rebuilt 71`、
  `Metal cache: mac 105 reused, 540 compiled`（真实 reuse 照实）、未解码 binding 0、driver 读取 2（c0 2）、
  645 queries 无 PC 反射。未从旧链抄产物进新 out。

## 2 完整验收（对照 tex27 `b-8c02a1137b0d`）

| 项 | 结果 |
|---|---|
| 每 key 三件套 | 645 json + 645 metal + 645 metallib；72 `_bf.metallib`；无缺 |
| JSON 深 diff | **仅 `chain` 字段，645/645**；无其它字段差异 |
| MSL hash | 仅 `531d637463e53486` 不同；VS `f64e…` 与其余 643 个逐字节相同 |
| metallib hash | 仅 `531d637463e53486` 不同 |
| 目标两 key | json/metal/metallib 与 report104 两 key 构建**逐字节相同** |
| 字段对照 | sbuf 45（7 rw）、img 9、tex/samp `reg=None` 0、driver readers 与 `drv_unfillable` 与 tex27 逐项相等 |
| c1_guard | 真实生成 `# chain b-c26257ff13a8 2026-10-22T01:15:10+08:00`；`not proven bounded: 0 shaders`（list 语义，非安全证明） |

- `shader_facts` 行存在**不等于** PC 反射已配对：两 key 与 645 的 notes 仍是 `no paired PC reflection, queries use defaults`，
  `pc_missing:true`；本轮只声明该行是离线单 pass 事实。

## 3 matching host（未运行）

- 用新目录 generated headers（`gen/010074F013262000/game_profile.h` + `gen/.../profile/dmsh_chain.h`）在 repo `gen/` 之前编译：
  `linkcheck/dmhost-fout-531d-uint2-645` sha256
  **`a6ded1fc7246e69664b5cf4c2cb56b7b4a1aac7e12eab36d2f7770c8c3b549b2`**；compileline sha `8104315f…`、
  build.log sha `237bbc2b…`、build.rc `93ff7811…`，rc0/0 errors。
- 宏：TEX base 0x20 / slots 27、SSBO 0x110/0x510/0、IMG 0x120 slots 1（新 header 中确认）。
- strings：新 chain `c26257ff13a8` 1 次；旧链 `8c02a1137b0d`、`b52eb825b741` 均 0 次；`tex-final` 1、`sbuf-final` 1
  （现成诊断保留）。源码 HEAD `36bba17`。
- **未运行 host**；旧 host 与共享 `dmhost` 未覆盖；ready launcher 未改；active `tex27-writeflag-correct645` /
  `ssbo-writeflag-correct645` 未被自动替换。

## 4 后续单目标 guest 验收草案（仅文字，不实施/不运行）

- 目的：确认旧 pipeline 拒绝是否被新库越过，而不是把失败 psort 当成功条件。
- 唯一链：`DM_NVN_KEYDUMP=531d637463e53486:1` 下，同一 frame/pass 出现 `[kd]`（fs=目标）→ `K st1` 目标 →
  `d` 同 VS/PS；PSO 记录（`pso_user.tsv`）显示该 pair 的 pipeline 建立。实际 VS 取本次 kd/d，不预设 f64e。
- 终局：PSO 建立/仍失败/目标未取得/更早 dump/资源/时限/信号/CRASH 均如实；其它 PSO 失败独立记录；不因等 real 延长/重试。
- 边界：只证明“越过旧 pipeline 拒绝”这一编码期事实；不证明 GPU 执行/采样/内容/像素，不证明 NVN 语义或其它 7 个整数 pair。
- 本轮不实现该计划、不加诊断、不 launch。

## 5 边界与状态

- 候选库/host 仅为实验产物，不替换 active checkpoint；未跑 GPU 写/采样/截图；未建全量 645 之外的额外 facts。
- 建库/host 均成功；无失败现场需要保留。
- 文档：INDEX/EXPERIMENTS 加入 exp107（full-645-candidate/evidence-only）；实验 README 写就；request 106 补 relay
  `codex-xc3-531d-fout2-candidate-57c188e768dd4be4bb6ae6dfa95e4795` 与 `accepted:true`；request 107 原样归档
  （local id `xc3-fout-645-107`；relay id 未提供 unknown）。
- HEAD `36bba17`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/旧证据/共享 host 未动。停止等 review。
