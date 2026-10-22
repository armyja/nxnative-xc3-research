# report119 · kdgeom supervisor 准备完成；gate 拒绝（无 guest）

日期：2026-10-22 05:10–05:25（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；无生产/库/facts/阈值改动、无提交/push。

---

## 0 结果

- SSD supervisor/launcher/preflight + no-guest 测试全部通过；prelaunch 身份保存。
- 唯一一次 gate 在首样本即拒绝：**available 2756 MiB < 2800 MiB**。按授权 gate 拒绝即整轮结束，
  **未启动 child、0 guest、未重试/未第二 gate/未轮询等资源**。
- run：`/path/to/external-drive/xc3/work/experiments/kdgeom-plan/run-20261022-030621/`
  - `kind=gate-refused reason=gate available 2756 MiB < 2800`；`launch_at/first/term/gone` 空；无 boot.log/shdump。
  - gate.csv 两行同 0.006 s 样本（首样本失败即停，不继续采样）；child 未创建。

## 1 准备与测试

- Host `dmhost-six-lgt-kdgeom` sha `7b500780…`；library `fout-six-lgt-correct645` chain `c7c374c3eb34`、9 facts
  `492151bd…`；map645/pairs90/packages/patched tree/c1/宏/目标 VS/GS/PS 全 key preflight ok。
- 测试（SSD，无 guest）：
  - 生产 helper 测试补 6 distinct keys / direct / indexed，`fails: 0`；旧 unused 参数警告保留。
  - supervisor 直接吃生产 helper 输出 fixture：hit、index5/partial hit、partial nohit→unknown、full nohit→target-not-obtained、
    none、unavailable、indirect、wrong frame/pass/prim/count/cached/keys、duplicate header、geom-before-header、
    wrong PS ignored、bad source，全部按预期终局。
  - e2e（合成 child）：hit/index5/unknown/nohit/none/unavailable/indirect/half-line/非豁免 dump 优先/原 GS 豁免后继续，
    全过并回收 child。
  - launcher 替身路由：默认 preflight-only 无 run/child；--launch 只带 KEYDUMP=2e16c536b845ea0e:1、新绝对
    PSO/SHDUMP/MEMSTAT、六输入/enGB/audio0，gate 2800/10/180，无 PSOFAIL_RT/MULTI/IMGBIND/SSBO_OBS/BINDAUDIT 等；
    guard 零 gate 拒绝、gate 中 SIGTERM 记录。
  - preflight 正/负例（host sha、facts、GS 目标）通过。
- prelaunch `prelaunch-20261022-030612/identity.sha` 保存 host/supervisor/launcher/preflight/exempt/库 facts/chain/
  patched/tests run.log/HEAD 全 SHA。

## 2 证据边界

- 未取得 `[kd]`/`[kd-geom]` 任何运行记录；不能说明 GS 来源/primitive 或 GS 执行。
- Gate 拒绝是资源条件，不是 supervisor 语义失败；本轮按授权停止，不重试、不清用户进程、不第二 gate。
- 预热/后台进程若占用内存，本轮不做清理（scope 外）；下一轮若重试需新授权。

## 3 文档

- INDEX/EXPERIMENTS 加 exp122（kdgeom plan/gate-refused/evidence-only）；report118 的 host/接线仍有效。
- request 121 补 relay `codex-xc3-gs-kd-topology-diag-8e56d2604cbd4a83b13b4aff148ae617` 与 `accepted:true`；
  request 122 原样归档（local id `xc3-kdgeom-gate-122`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无自动 guest/后续。


---

## 4 追加更正（主管 review；原文保留）

- 本报告“ssd supervisor/launcher/preflight + no-guest 测试全部通过”**仅指已被 supersede 的简化 supervisor**；它没有
  pages/rss 采样、samples.csv、runtime 资源阈值、采样严格解析、真实 `_b` header/`_bf`/完整 keys 校验，gate
  sample-anchor 与 pre-Popen guard 也不完整。该计划未通过监督契约，旧文件冻结不得用于真实 launch。
- 修复版见 report120；本报告 gate 拒绝记录（2756<2800）仍真实，0 guest 不变；不回写旧“成功”。
