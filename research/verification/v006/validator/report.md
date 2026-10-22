# V006 独立验证报告（CPU，只读候选）

候选 22 文件 SHA 全匹配；host 未执行（仅静态读 build.log/build.env/compileline）。无 commit/push。
route NO-GO。

## 1. 身份与静态核对

| 项 | 结果 |
|---|---|
| manifest `112f832d…` | 匹配；22/22 文件 SHA 一致 |
| host `931a241f…` | 与要求一致；**未执行**（`--help` 也未跑） |
| 四源 vs V005 | 逐文件 SHA 相同 |
| 编译日志/compileline/include 优先级/profile chain | 静态读取；未发现与 manifest 冲突（未执行 host） |

## 2. 真实 CPU 链（TfIntentChain + supervisor Matcher）

| 项 | 结果 |
|---|---|
| `_b` 完整链 KD→HIT→intent | **PASS**（chain: hit）；但 supervisor 入口随后崩溃（F1） |
| gs HIT 不终局 | PASS（C3） |
| unknown/active/inactive | 均完成，仅"记录取得"（C2） |
| 错 frame/pass/VS/PS/GS、错序、非 HIT、重复 KD | 均拒绝（C4/C5/C8/C15） |
| u64 MAX / MAX+1（KD 与 tf seq） | MAX 通过、MAX+1 拒绝（C9–C11） |
| 重复/尾随 token | 拒绝（C13/C14） |
| 普通 `[kd] attr/stream` | **FAIL**：被判 duplicate header（F2） |
| bare 正常 PS | **FAIL**：tf parser 要求 `_b/_bf`（F3） |
| depth i32 | i32 min 通过，**max+1 也通过**（F4） |

## 3. supervisor（synthetic child，真实入口）

- S3 无记录：`validated=0`，无 intent —— PASS
- S4 evidence 写失败：报 `evidence-write-failed` —— PASS
- S5 同 poll dump 注入：进入 dump 分支（但随后同样被 F1 崩掉）
- S1/S2 正确链/含 attr：**exit 1**，无 stop.json/coverage.txt —— F1

F1 anchor：`supervise_tfintent.py:285` 用 `sf.hdr['pass_'],['fs'],['count']`，而 `parse_kd` 返回
`pass_counter/ps/vertices` → KeyError；`except OSError` 不捕获 → 命中记录被崩溃掩盖。

## 4. launcher/preflight（静态/mock）

PASS：解释器 argv、`DM_NVN_TF_DIAG=1`、2800/10/180、禁用测试 env、`--run` 需绝对且不存在、
默认不建 run/child、LogTail 半行保持。
**F5**：文档写 "fresh absolute SSD path"，但代码只查 isabs + 不存在，无设备/df 校验。

## 5. mutation（validator 副本，import 成功、行为失败）

- M1 去掉关联校验 → 7 项失败（C5a 等）
- M2 把 gs HIT 当终局 → 12 项失败（C1/C3 等）

## 6. 未覆盖 / SKIP

真实 host 执行、完整 180 s gate、真实 dump 内容、两条合成 exempt dump、sampling-error/timeout 注入、
preflight 实跑（仅静态）；真实 GPU/TF 语义不涉及。route NO-GO。
