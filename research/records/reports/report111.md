# report111 · 六 key 有界 batch psort 授权运行：6 个完整记录，dump 优先停止

日期：2026-10-22 02:05–02:09（本机）
Run：`/path/to/external-drive/xc3/work/experiments/posttex-batch-psort-run/run-20261022-020510/`
HEAD `af094f470c43133016a899527b06a4c598677fce`（未变）；无 tracked 改动、无 commit/push。

---

## 0 授权/次数/身份

- 合并授权：计划与 no-guest 测试全部通过后，一次 gate、通过后一次 batch guest。实际 **1 gate / 1 guest / 0 retry**。
- 身份（`prelaunch-20261022-020503/identity.sha`，preflight ok）：host
  `03c93b09f450b138078263e6496de85a9ccb43aec3335083e8a3b7f28ba25477`；`supervise_batch.py`、`run-batch.sh`、
  `preflight.py`、`exempt.json`；facts `d9cc9ce7…`（3 行）；chain `35de4665bff4`；patched 三模块、gen headers、c1 固定。
- 环境仅 `DM_NVN_PSOFAIL_RT_MULTI=06f1...,c9d7...,885b...,1581...,4b9a...,aadd1...`（顺序固定）、PSO/SHDUMP/MEMSTAT
  新绝对路径、六输入/enGB/audio0/headless；无单目标/KEYDUMP/IMGBIND/SSBO_OBS/BINDAUDIT/skip/override/test。

## 1 Gate

11 样本，`elapsed` 0.000 → 10.115（span 10.115 ≥10），min available **2889 MiB**（≥2800），`launch_at=10.132`。

## 2 六个完整记录（每 key 1 条；`batch-records.txt` 66 行，sha `9d80c86c…`）

所有六条 header：`frame=4592 pass=553097 snapframe=4592 snappass=553096 assoc=same-pass snap=valid/553097
cfmt=103,53,0,0,0,0,0,0 dfmt=260 sfmt=260 ctx 全 0`；`map enabled=0 identity`。

| key (PS) | actual VS | slots（NVN 原 fmt / cview / final MTL） | 备注 |
|---|---|---|---|
| 06f1dcc9c37acf00 | f9cb32fab57fd5f8 | slot0 NVN 0x17 (RG32UI) cview 0x17 → MTL 103 (RG32Uint); slot1 0xB (R32UI) cview 0xB → 53 (R32Uint); 640x360; slots2-7 unattached | 1 valid；rec1；cached note |
| c9d762917edfee9f | 493d3e99bbacd343 | 同上 | 1 valid；rec2 |
| 885bb4caecc378cf | 43a09053e4556e1c | 同上 | 1 valid；rec3 |
| 15816d836842bfb5 | c1896d1c1390d65a | 同上 | 1 valid；rec4；cached note |
| 4b9a4e60d5ee5f16 | 2862405df8c18f0d | 同上 | 1 valid；rec5；cached note |
| aadd1c2efa076cc3 | d2fdecde11966fab | 同上 | 1 valid；rec6 |

- 六个 key 的 **签名相同**（cfmt 103/53 + identity map），但每条按 key+rec 独立保存，未跨 key 合并；本轮每 key 只有
  1 个签名，没有第二签名。
- `snap` serial = 553097，而 `snappass` = 553096；`assoc=same-pass` 按生产 serial+cfmt，不说明两个 pass 计数器相等，
  也不把 snapshot pass 冒充 actual pass（actual frame/pass 单独记录）。
- 3 个 key（06f1/1581/4b9a）在记录前后各有一条 `cached-failure no descriptor` note；note 未关闭 key、未计 valid。
- `pso_user.tsv` 中这 6 个 key **无同 pair R 记录**（pipeline 仍失败），不补跑。
- 原文行号：header 475/488/500/512/525/538；done 485/498/510/522/535/548；notes 486/523/536 等。

## 3 停止优先级：非豁免完整 dump 胜出

- 同一批 poll 内六个有效记录已完整解析，但 supervisor 先执行 complete-dump 扫描：**非豁免 GS `4c0a9c8e53f088cb`**
  完整 dump 出现，停止原因 **`complete dump: 4c0a9c8e53f088cb`**，不是 coverage-complete。
- `coverage.txt` 如实记录每 key `valid=1 attempts=1 sigs=1`，但 kind/reason 是 dump stop；报告不宣称
  coverage-complete，只说明“若只看 records 覆盖已齐，同时发生 dump 停止”。
- 两条原内容 GS 豁免（95bf/a841，63.004 s，hash 一致）；未扩豁免；非豁免 dump 出现即停。

## 4 时序/资源/回收

[Fenced excerpt omitted from the shareable research record.]

- guest 时长 ≈ **156.14 s**；TERM 后 0.09 s 消失；legacy launch=0 忽略。
- 640 samples：运行期 min available **1446 MiB**（≥1 GiB），max RSS **1156400 kB ≈ 1129.3 MiB**（≤2 GiB）。
- log 89,737 B（<64 MiB）；shdump 46.25 KiB（<32 MiB）；child exit=0；无残留进程。
- 停止原因不是 deadline/timeout，而是完整 dump 优先；无 retry/refill/改值。

## 5 证明与不证明

**证明（编码期）**：6 个固定 key 各自在真实 pso 失败路径上取得完整 pass 附件快照；actual VS 按本次记录；附件
logical0/1 为 RG32Uint/R32Uint（NVN 0x17/0xB、cview 同格式、final MTL 103/53）。

**不证明**：GPU/内容/像素、数值/bitcast 语义、其它 float-target 用途、NVN→MTL 语义；同签名不证明六个 shader
语义相同；不是 PC 反射；无 facts 生成/回写。

## 6 文档与状态

- INDEX/EXPERIMENTS 加入 exp113（batch run/validated-limited）；实验 README 写就；request 113 补 relay
  `codex-xc3-multi-psort-review-fix-e8bd86b0aca544e6b943fbb1cb83ce5f` 与 `accepted:true`；request 114 原样归档
  （local id `xc3-6key-batch-run-114`；relay id 未提供 unknown）。
- report110 §8 追加旧 host 身份说明：同名 `dmhost-batch-psort-multi` 已由 `11c32dd2…` 被本次重建为 `03c93b09…`；
  旧 binary 未另存，旧 hash/报告留存，不声称旧 host 全保留。
- HEAD `af094f4`；`git status` 仅既有未跟踪 `XC3-SETUP.md`；AGENTS.md/XC3-SETUP.md/共享 host/旧库证据未动。
- 停止等 review；无自动 guest/facts 搜索/下一步授权。


---

## 7 追加说明（主管 review；原文保留）

- 最终 `boot.log` 的 558/559/560 行另有 c9d7/885b/aadd 的 `cached-failure` note，整日志 **6 个 key 都有 note**；
  在线 `coverage.txt` 是停机判定时已处理范围（只记录了 3 个 key 的 note）。二者区别是“停机时已处理 vs finally 后完整
  日志”，不是数据丢失；报告不改写原时序，另在离线最终归并中列出 6 条 note。
- 6 条 valid 记录本身不受影响；`snappass=553096` 与 `actualpass=553097` 不等，assoc 仍按生产 serial+cfmt，不强调相等。
