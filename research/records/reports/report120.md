# report120 · kdgeom supervisor 契约修复（复制已审骨架）

日期：2026-10-22 05:30–05:50（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；无 gate/guest/host 运行、无生产/库/facts/阈值改动、无 commit。

---

## 0 结论

- 旧 `supervise_kdgeom.py` 冻结为 `supervise_kdgeom.superseded.py`，不再被 launcher 引用；新入口
  `supervise_kdgeom_v2.py` **直接复制已审、实际运行过的 `posttex-batch-psort-run/supervise_batch.py`**，只替换目标
  matcher/结果输出；gate、采样、资源、时限、信号、pre-Popen、complete-dump、cleanup、env 拒绝、Tail 有界读等函数保持
  原样（`supervisor.diff` 4 个 hunk）。
- 本轮**无新 gate 授权**，未运行 host/guest；仅 SSD 修复与 no-guest 测试。

## 1 P1 修复

- **采样/资源恢复**：v2 保留 `pages_and_avail`/`rss_kb`/`parse_*`/`sh`（rc/timeout/OSError/空/负/缺字段均
  SamplingUnavailable）、`gate()` sample-completion anchor、每 sample 立即写 gate.csv、runtime samples.csv、available
  1 GiB/RSS 2 GiB/dump 32 MiB/log 64 MiB、180 s、pre-Popen signal/deadline、complete-dump 优先、两 GS 内容豁免、finally
  TERM 2 s→KILL→wait。
- **matcher**：真实 `[kd]` header 支持 bare/`_b`/`_bf` canonical；`_bf` 首 forced draw 直接
  `geom-target-not-obtained`，不等第二 header；其他 PS 忽略；目标 header/geom 均校 frame/pass/prim、数字域、VS/PS 16hex、
  source/serial/nstage、cached/den、keys 长度/known count、each key 16 小写 hex 或 `unknown`；none/unavailable 的
  keys/counts 关系；direct/indexed（indirect=0）count/instances/base_instance 与 header 一致；indirect=1 必须
  unavailable。非法/重复/乱序/矛盾终局 invalid，不补链。
- **输出**：`kdgeom.txt` 保存完整 header+geom 原文；`coverage.txt` 写 header/geom 摘要；旧 timing/gate/samples/
  exemptions 结构不变。

## 2 测试（全部 synthetic/substitute，无真实 host）

- `tests/run2.log`：preflight、negative、supervisor、gate、sampling、e2e、launch-path、guard 共 **7 组 fails:none、无 FAIL**。
- matcher 用**生产 helper 实际输出** fixture（C 生成，非 Python 镜像）：裸 `_b` 成功、bare 成功、`_bf`→target-not-obtained、
  other PS 忽略、index5/partial hit、partial nohit→unknown、full nohit→target-not-obtained、none、unavailable、indirect、
  indexed count mismatch、坏 16hex、none 矛盾、bf 不等第二 header、坏 keys 长度、重复 header、geom-before-header、坏
  source/数字域/prim/frame/pass/cached。
- sampling：真实入口正常跑有 samples.csv 行且 rss/pagesize/avail 非零；sample-nonzero/empty/timeout 均为 sampling-error
  并回收 child；残留 `IMGSUP_TEST_*` 无 `--test-inject` 拒绝且无 samples/child。
- gate：audited `t_gate.py`（慢首样本、CSV 跨线、终端低、终端错误、零秒、单 gate、180 s 固定）全过。
- e2e：hit/index5/unknown/nohit/none/unavailable/indirect/half/非豁免 dump 优先/原 GS 豁免后继续，child 回收。
- launcher 替身：默认 preflight-only 无 child；--launch 只带 KEYDUMP=`2e16c536b845ea0e:1`、PSO/SHDUMP/MEMSTAT 新路径、
  六输入/enGB/audio0、gate 2800/10/180，无禁用 env；替换 v2 真实入口。
- 未测/未跑：真实 host、真实 guest、真实 available/RSS 触发（需实际内存压力，本轮无 guest）；log/dump 阈值代码逐字
  保留自 audited 骨架，未单独注入触发；不称已运行验证。

## 3 身份/差异

- v2 sha `ce703cdca59d24fa4529822c82e07e6352ffeb60d4cd454240006a4849165feb`；launcher sha
  `f254e45fb36ab2ad38b7b30cbe35c57b0b2dd54b70cd778e91599e04cafe6aa2`；prelaunch
  `prelaunch-v2-20261022-031529/identity.sha`。
- `supervisor.diff`（audited batch → v2）4 hunks：matcher 块、`sf=` 初始化、dump/hit 输出文件、coverage 摘要；其余
  gate/采样/资源/cleanup 等逐字保留。
- Preflight 仍 ok：host sha `7b500780…`、chain `c7c374c3eb34`、9 facts `492151bd…`、map645/pairs90、目标
  VS/GS/PS 全 key；GS 不在 map，未假装加载。旧 host/旧 gate 记录保留。

## 4 状态

- 旧 supervisor 已 superseded，launcher 指向 v2；本轮未 gate/guest，资源状态不测不轮询。
- request 122 补 relay `codex-xc3-kdgeom-plan-conditional-run-26a9f8ca7b4e44ab98d7e8a7e311cce5` 与 `accepted:true`；
  request 123 原样归档（local id `xc3-kdgeom-contract-fix-123`；relay id 未提供 unknown）。
- HEAD `1408257`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧证据未动。
- 结束停 review，无自动 gate/guest。


---

## 5 追加勘误/契约修复（主管 review；原文保留）

- **首个完整合法 [kd] 非目标 PS**：原实现 `return None` 等后续，现改为立即 `geom-target-not-obtained`，保留实际
  VS/PS；后续目标好链不能救回（测试 `otherps`、`bad-then-good-no-rescue`）。
- **none/unavailable 早退绕过 count/indirect**：已把 count/instances/base_instance 与 header 一致性、direct/indexed
  数字契约、indirect counts unavailable 的验证移到 source none/nstage unavailable 早返回**之前**；none 还必须
  serial=0。反例 source none/999、none count 7、unavailable count mismatch 均 invalid；合法 none/unavailable 不回归。
- **数值范围**：frame/pass/serial 按 uint64，nstage/cached/den 按 unsigned，prim/count/instances/first/base_* 按
  生产 int 字段（i32，合法负值不排除）；F18446744073709551616 现 invalid。新增 negative-count-legal、frame-overflow、
  bad-16hex。
- v2 顶部文档改为 kdgeom，明确 matcher 契约；基础设施 diff 仍 gate/采样/资源/cleanup 原样。
- 新 v2 sha **`5fcf9c0d230c24cddbd1f609c1dfda344c7d69185987f0a8f7aa927bb402fa91`**；supervisor.diff
  `0c603878…`；tests/run3.log `db52344f…`（matcher/e2e/launch_path/gate 4 组 fails:none、无 FAIL）；preflight ok；
  prelaunch `prelaunch-v2-032526/identity.sha`。
- 本轮无 gate/guest/真实 host/资源采样；ready plan 冻结，下一次 gate/guest 等单独授权。
