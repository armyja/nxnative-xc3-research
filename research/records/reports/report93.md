# report93 · 纯文档轮：分层恢复入口（INDEX / TOOLS / EXPERIMENTS / request 归档 / 实验 README）

日期：2026-10-21 23:14–23:22（本机）
范围：**只整理已有证据**。无 guest、无 build/test/validator/chain/编译/翻译复跑；无生产代码、profile、chain header、库、host 变更；无提交/push/PR；无 repo 指针（`AGENTS.md` / `XC3-SETUP.md` 未动）。HEAD `f5a3cbb`，`git status` 仅既有未跟踪 `XC3-SETUP.md`。

---

## 1 交付文件

| 文件 | 行/行数 | 作用 |
|---|---|---|
| [`INDEX.md`](INDEX.md) | 70 行（更正后） | L0 唯一恢复入口：仓库状态、当前任务/阻塞、active candidate 与 identity 链接、已证/候选/未证、冻结与废弃警示、近期报告与勘误、下一步与授权状态、固定恢复顺序 |
| [`TOOLS.md`](TOOLS.md) | 140 行（更正后） | L2 本阶段 7 条已验证 recipe（profile/header、chain、dmsh_build、c1_guard、package/map/pairs、host compile、supervisor/preflight），每条含适用 HEAD/工具 sha、最后 verified 报告、前置条件、argv/env/cwd、输出、成功判据、副作用/陷阱；末尾列缺失来源与 unknown |
| [`EXPERIMENTS.tsv`](EXPERIMENTS.tsv) | 13 行数据 | L3 实验索引：report84–92 全部行 + 基线 68/80/82/83；字段 `id/path/purpose/parent/profile/chain/host/host_sha/source_head/role/status/report`，无裸 tab/newline，缺值 NA/unknown |
| [`HANDOVER-TEMPLATE.md`](HANDOVER-TEMPLATE.md) | 9 条 | 未来 report 的强制交接字段短模板 |
| [`rounds/README.md`](rounds/README.md) | — | request 档案政策：仅原样镜像；001–091 未保存、不得从 report 重建“原始授权”；档案不授予执行权 |
| [`rounds/092-request.md`](rounds/092-request.md) | 28 行 | 本次请求原样镜像；local_archive_id `xc3-ssbo-round-092`、relay_request_id `codex-xc3-layered-handover-bf9b80b9d60b442ebf8a31abeafe85da`、received 2026-10-21 23:14 +08:00；receipt accepted:true（回执文本未存档） |
| 7 个实验 README | 各 15–20 行 | `ssbo-vs110-correct645`、`ssbo-vs110-plan`、`ssbo-vs110-final-plan`、`ssbo-ps-nvsd`、`ssbo-vs110-ps510-correct645`、`ssbo-flagsabi`、`ssbo-writeflag-correct645`；只给本实验参数/期望与实际/schema 单位/边界 + TOOLS recipe 链接与本地 manifest，不复制 TOOLS |

实验 README 均在 `/path/to/external-drive/xc3/work/experiments/<dir>/README.md`；此前均不存在（无旧版需保留）。

---

## 2 恢复顺序（写入 INDEX）

`INDEX` → active 实验 README（`ssbo-writeflag-correct645/README.md`）→ 相关 `TOOLS` recipe → `rounds/092-request.md` → 必要的 report/证据。

---

## 3 Active candidate（与 INDEX 一致，仍为实验身份）

- profile `ssbo-writeflag-correct645/profile/010074F013262000`（`game.tsv` sha `8a188b57…`）
- library `out/b-b52eb825b741`（645 keys；717 metallibs 含 72 `_bf`）
- chain `b52eb825b741`
- host `linkcheck/dmhost-ssbo-writeflag` sha `b3ba3d18e5a05b8dd6ca9f3a23d50861bf16061b554e26cb5bfff27d5e1264bc`
- source HEAD `f5a3cbb`；`vs=0x110 ps=0x510 cs=0`、IMG `0x120` slots 1、TEX 16、单一 fout 行
- identity manifest 链接：`verify/lib_manifest.sha256`、`pkg_manifest.sha256`、`base_artifacts.tsv`、`variants.tsv`、`diff.json`、`real_rw.tsv`、`verify.txt`（均在本轮 INDEX 表中）
- **不是** production validated；PS writer `8c8d676f2d2bab80` 尚未在 guest 中以 `rw=1` 出现。

---

## 4 明确未做的事（按授权边界）

- 未重新执行任何命令来“补齐”文档；未 import `dmsh_build`；未跑 `--header`/build/test/validator/guest。
- 未重写 report84–92 原文；勘误只以链接指向既有 `report89 §11`、`report90 §11`，不伪造一致历史。
- 未为历史 84–92 request 重建“原始授权”（无原始消息可镜像），`rounds/README.md` 已注明未保存。
- 未改 repo 文档、未加 repo 指针；未改既有 `build.cmd`/日志/哈希记录。
- 未扩 tex/fout/GS/image；未启动 PS 实验。

---

## 5 缺失来源 / unknown（如实记录，不拼装命令）

- report84 的精确 build argv：当时未保存 `build.cmd`（只有 `build.log`）；TOOLS 中只描述其 env 语义，argv 记 unknown。
- report85 的精确 preflight 调用：仅存 `run-ssboobs.sh`，历史 argv 未单独记录。
- report80 的 HEAD/chain：report80 未写明 → `unknown`（EXPERIMENTS.tsv）。
- 废弃 host sha 前缀 `112c345e8ad5a85a`：`imgdiag-run-20261021-164656/report.md` 明确称其 superseded、未使用；当前
  `linkcheck/` 无对应文件 → 位置 `unknown`，INDEX/TOOLS 已标“discarded / do not reuse”。
- `exp86` 的 host 与 headers 分属 `linkcheck/` 与 `ssbo-vs110-correct645`，EXPERIMENTS.tsv 的 `path` 指向后者，host 单独列。
- `exp84` 无 host/host_sha（NA）。
- 历史构建的 `WORK` 值：`build.cmd` 未设 `WORK`（`dmsh_build.py:532` 的 `mkdtemp` 落系统 temp）→ 历史 scratch 位置 `unknown`；不得由 `<out>/../work` 反推契约。
- 历史请求 001–091 的原文：未保存 → `unknown`；不从 report 重建授权。
- report92 的 `WORK` 也没写；`build.cmd` 只是已执行 argv 的记录，参数化 template 另行标注。

---

## 6 校验与影响

- 链接自检：INDEX/TOOLS/rounds/7 个 README 的相对链接全部解析（修正了实验 README 中 `proto/out` 的相对层级）。
- 文档权限统一为 `0444`/`0644` 可读；未改任何实验产物。
- **无 runtime/chain 影响**：未改变 chain、库、host、profile、header、lock；无 guest、无提交。
- INDEX 59 行（≤80）；EXPERIMENTS.tsv 13 行数据，字段无裸 tab/newline。

---

## 7 状态

HEAD `f5a3cbb`；无 tracked 改动、无 commit/push；无 guest。文档入口：[INDEX.md](INDEX.md)。停止等待复核；不接着自启动 PS 实验。

---

## 8 本轮更正（主管 review；上文保留，作为更正记录）

1. **TOOLS R3 的 WORK 契约写错**：源码是 `dmsh_build.py:532` 的
   `w = tempfile.mkdtemp(prefix='dmsh_', dir=os.environ.get('WORK'))`。未设 `WORK` 时落系统 temp；设了 `WORK` 则该目录必须已存在；
   不存在 `<out>/../work` 的通用契约。R3 已改为“已执行 argv（`build.cmd`，未设 WORK，历史 scratch unknown）”与
   “参数化 template（`WORK=<existing SSD scratch>`，明确非历史精确命令）”两部分。
2. **TOOLS R2 的省略写法**：`… dmsh_chain.py --check-tools` 这类行已标为“选项说明，接在同一条 `python3 …` 调用上”，
   不再伪装成可独立复制的命令；并补上 `version()` 还 hash `XLATE_DEBUG`/`XLATE_REDUCED`，默认 debug=1/reduced=1，必须保持一致。
3. **TOOLS R5 误称“没有生产 validator”**：生产 API 是 `dmsh_refill.validate_map(map_path, pkgdir)` 返回
   `(keys, problems)`，再 `validate_pairs(pairs_path, keys)`；`package_verify(blob, key, stage)` 只是 record 层。
   R5 已改引 `ssbo-vs110-final-plan/preflight.py:57-58` 的真实调用顺序；手工五列计数不再当作完整验证。
4. **INDEX 证据范围**：把“no GPU evidence / no content or pixel correctness”限定到 active `b52…` 候选的目标 PS writer
   与映射验收；补一行历史里程碑（report52/53 Loading UI；[handover-rounds-56-64](handover-rounds-56-64.md) 的 title/menu/first-3D；
   report55 title 离开 Loading），旧库证据不冒充新库正确性；VS110 与 PS510 都明确标 candidate；img 改为“9 个静态 reg0，
   仅 4bae 有 runtime 观测（report68），其余 8 未观测”；repo clean 标为 2026-10-21 23:40 的时点结论。
5. **rounds 元数据**：`xc3-ssbo-round-092` 改为 `local_archive_id`（本地档案号，不是 report 号）；补
   `relay_request_id codex-xc3-layered-handover-bf9b80b9d60b442ebf8a31abeafe85da`；receipt 写“accepted:true，回执文本未存档”，
   不写“无回执”。正文保持原样。
6. **HANDOVER 模板**：补回“授权范围与 actual gate/guest/重试次数”“child cleanup/残留状态”“停止原因”，合并在 1/9 项，仍保持 9 项；
   纯离线填 NA，不硬造 child 检查。

**仍缺的资料**：report84 的精确 build argv（无 `build.cmd`）、report85 的 preflight argv、report80 的 HEAD/chain、
历史 `WORK` 值、001–091 请求原文、`112c345e8ad5a85a` host 文件（linkcheck 无）；均如实标 unknown，未用重跑补齐。

**影响**：仅 SSD 文档；无 repo/profile/库/host/header/lock 变更，无 runtime/chain 影响，无 guest，无提交。
