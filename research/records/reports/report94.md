# report94 · PS-writer 验收计划 + no-guest tests/preflight（无 guest、无 launch）

日期：2026-10-21 23:28–23:46（本机）
计划目录：`/path/to/external-drive/xc3/work/experiments/ssbo-ps-writer-final-plan/`
HEAD `f5a3cbb`（未变）；无 repo 改动、无 commit/push；无 guest、无 host 运行、无 shader build、无 profile/facts/库/lock 修改。

---

## 1 计划文件与 SHA

| 文件 | sha256 |
|---|---|
| `supervise8.py`（新 matcher；reuse reviewed gate/guard/cleanup/env） | `7f6dc7430fbc72f4ec04ea2450125195eb731ff4a584e1b68aeeb4d78769c949` |
| `run-ps-writer.sh`（default preflight-only） | `7550cdde3041cc48adbfbe98fd70a655962e2d1e77d3cb46716615f181dbe65e` |
| `preflight.py` | `b9767a65b57dc86080e6aeb0dbefe9ecde7a2eee6b2bb1ae61642dd685f43889` |
| `exempt.json`（两份固定内容 GS） | `844029072907f30d833f3ba05764f701ef9c10e0484e806e6d7731d62a7500c3` |
| `plan.md` | `d9f7af8593aa296c1ec9376e2239afacd0b2605e4c680b8704b5d46177e954af` |
| `README.md` | `e217da64bb22b608935c8950b941968eb486212dae8847c735d6b9debc855ce6` |
| `tests/t_fields.py` | `7e25a9231c9bba0b68dc22610dc846ad47058dfd1fe421ed8fa1838803e8d6d0` |
| `tests/t_matcher.py` | `dc91b60c611aff08cad0230ac7325072e4edb585326ef91f46de7cca85d160d0` |
| `tests/t_gate.py` | `a4dc1f1f447c2efd6ae59a75b19ca1026f1d8e8cdd830631b29a1c22d25ec378` |
| `tests/t_launch_guard.py` | `d9f61c40d7a24af81a3589d979910bca3bebfea1363f3e1dbe2370fa1134ed16` |
| `tests/t_launch_path.py` | `6d8fcdcf6432524e495b601315e60db67dc11e68dc11e9a32493d69a88a5f11f` |
| `tests/t_e2e.py` | `32634114af16712e13446b5085e03d8c69156850f505e2f49ec0efb35b0bfd23` |
| `tests/fakehost.py` | `d92dfabd8a02192087b2d6189e4ddaf13004fa79930dbca18f421bbf8554e9f8` |
| `tests/run.log` | `37c94331d5f65e713af433f9493f87ffecb86c4a14c2d5ddb0290f1c82c4057c` |
| `preflight.txt` | `670d2607bf4688fa8da43287c645e0d290ead99d7177a4d9207b9481c9b09775` |
| `launcher-preflight.txt` | `890366531b6628761b296ff813f0564274a6a7036f98ece9a49b4825ebdfb798` |

`supervise8.py` 只在 reviewed `supervise7.py` 基础上替换成功 matcher（`PsWriterFinal`）、`TARGET/PS_KEY` 与输出文件名
（`triple.txt`），gate/cleanup/complete-dump/`env -i` 逻辑逐字保留；未改 `ssbo-vs110-final-plan` 的 supervisor。

---

## 2 只读 preflight（实际执行，`preflight.txt` 原样）

[Fenced excerpt omitted from the shareable research record.]

- 645 map keys 经生产 `validate_map`/`validate_pairs`，0 problems；每 key 的 `_b.json`/`_b.metallib` 齐全；`c1_full.tsv`
  命名 `b-b52eb825b741`；patched tree sha 与既有 baseline 一致。
- profile 值：`vs=0x110 ps=0x510 cs=0`、IMG `0x120` slots 1、TEX 16。
- schema：45 sbuf，7 writer / 38 reader；目标 PS `8c8d676f2d2bab80` 的唯一 sbuf 为 `index0/reg0/arg_id0/rw=true`。

---

## 3 成功 matcher（单一，只管本次 PS writer）

`[kd] F<frame> pass <pass> vs=<key> fs=<key> …` 为 forced-draw 锚点，`fs` 必须是 `8c8d676f2d2bab80`；否则
terminal `target-not-obtained`（只认首 forced draw，不扩 count/inputs）。之后同一 pass 的有序记录：

1. `K <pass> st1 key=8c8d…[_b]`；
2. `[sbuf-final] … st1 key=8c8d…[_b] reg0 aid0 u=1 addr=<nonzero> rawsize=<uint64> size=<rawsize 或 1>
   resolved=1 actual=real slot=<uint64> rw=1`，或 dummy 形式 `u=0 addr=0 resolved=0 actual=dummy`；两类都 terminal；
3. `d <pass> … vs=<完整 16hex+可选_b> fs=8c8d…[_b]`；实际 VS 写入 `triple.txt` 证据，并与 `[kd]` 的 vs、若存在的
   `K st0` 的 vs 核对；缺少 `K st0` 时只记“没有第二来源”，不编造。

字段：`resolved/u/rw ∈ {0,1}`、`actual ∈ {real,dummy}`、`real ⇔ resolved=1`、addr/slot 为 plain uint64、
`size == rawsize`（rawsize=0 时 size=1）、`resolved=1` 必须 u=1 且 addr 非零；`reg/aid/rw ≠ 0/0/1` 为 terminal
`unexpected-candidate-record`；real+slot0 为 `consistent-but-abnormal`；坏数字/矛盾/乱序/重复/d-before-sbuf 为 terminal
invalid，不后补；`rawsize` 按事实记录，不要求 16。正常 `K st0`、VS 的 `[sbuf-final] st0`、其它 stage 不破坏 PS 链。

---

## 4 测试（no-guest，`tests/run.log`）

| 测试 | 结果 |
|---|---|
| `t_fields.py` | real/dummy、字段域（resolved/u/rw、actual、addr/slot、size）、reg/aid/rw 异常、real-slot0、rawsize0、malformed：全过 |
| `t_matcher.py` | real/dummy、任意合法 VS、`K st0` 冲突 invalid、`d` vs 冲突 invalid、d-before-sbuf invalid、duplicate K/sbuf、second kd invalid、其它 PS/K/阶段忽略、无 kd 无结果：全过 |
| `t_gate.py` | reviewed gate 的慢首样本/CSV 越界/终端样本低阈/采样错误/0 秒/t0 固定：全过 |
| `t_launch_guard.py` | deadline 与 gate 期间 signal 都不启动 child；matcher real/dummy/no-d：全过 |
| `t_launch_path.py` | 真实 launcher 的 entry 存在且含 `PsWriterFinal`、指向 `dmhost-ssbo-writeflag`；默认模式 rc0、打印 preflight-only 与 KEYDUMP、不产生 run 目录；替身 supervisor marker 验证 `--launch` 路由：host/gate 2800/10 s/180 s、KEYDUMP、无冲突开关、PSO/SHDUMP/MEMSTAT、en-GB/audio 0、六 inputs：全过 |
| `t_e2e.py` | synthetic child：real、dummy、半行、invalid reg、wrong-PS 五种；前三种成功并写 `triple.txt`，后两种 terminal 且无 triple：全过 |

真实 launcher 的默认模式已执行（只读 preflight），输出 `launcher-preflight.txt`：`preflight only: supervisor and guest
NOT started`，无 run 目录。`--launch` 未调用；替身测试只证明路由，不接触 host。

---

## 5 边界与非声称

- 本轮无 launch、无 guest、无 host 执行；`--launch` 仍未授权。
- 即便将来取得 triple，也只证明候选 host 最终写入参数槽的选择与该记录 `rw=1` 被传入；`nvn_mtl.m` 的 `USE` 当前丢弃
  usage，`rw=1` **不能**证明启用 Metal 写权限，也不证明 GPU 写入/结果、真实 PS base 或 NVN reg；report80 的三槽
  ambiguity 不被消除。
- 目标 PSO/其它 shader 早失败时无 triple，按原失败/complete dump/时限停；不新增 fout facts、不绕 GS、不重试、不改
  inputs。
- 图像/运行内容不在验收内。

---

## 6 request 归档与文档更新

- `rounds/094-request.md`：本请求原样镜像；`local_archive_id xc3-ps-writer-plan-094`；`relay_request_id` **unknown**
  （收到的消息未附 relay id，未自造）；receipt 文本未存档。
- `INDEX.md`：当前任务/下一步加入 exp94（“plan ready, no launch”）；按主管小修把 report55 表述改为
  “Loading → Auto-Saving 提示页，不是 title”；标题/菜单进展引用 handover-rounds-56-64。
- `EXPERIMENTS.tsv`：新增 `exp94-ps-writer-plan`（role `plan`，status `evidence-only`，report94）。
- 实验目录 `ssbo-ps-writer-final-plan/README.md` 已写：身份/参数/期望与实际/schema 单位/边界，链接 TOOLS R7 与本地证据。
- TOOLS/AGENTS.md/XC3-SETUP.md/共享 dmhost/旧库/旧证据未改；无 commit/push。

---

## 7 状态

HEAD `f5a3cbb`（full `f5a3cbbfad1eeb683a6b431d944b4512e2807ef2`）；`git status` 仅既有未跟踪 `XC3-SETUP.md`。
计划、preflight、6 个测试均已完成并落盘；**无 launch**。等待复核后再决定是否单独授权运行。
