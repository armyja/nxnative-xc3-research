# report148 · gs-res 固定身份 preflight + 默认 preflight-only launcher

日期：2026-10-22 21:05–22:05（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU；无 host/guest/device/GPU/gate/真实资源采样、无生产/库/lock/chain 改动、无 commit。

---

## 0 交付

- `preflight.py`：只读固定身份，正例通过；固定/校验 host、dirty `nvn_mtl.m`/`nvn_kd_res.h`、parser/supervisor 全 SHA；
  profile `fout-six-lgt-correct645`/`c7c374c3eb34`、9 facts、645 map/90 pairs（生产 `validate_map`→`validate_pairs`）、
  645 package tree、717 metallib（645 normal + 72 `_bf`）manifest、json/metal tree、c1/游戏/profile/chain 文件、
  patched main/sdk/subsdk0+`build_src.sha256`、两真实 GS exempt dump 的 key/length/full SHA。未 import `dmsh_build`。
- `identity.json` 是审计基线（host `9f3df170…`、nvn_mtl `faf06a9b…`、nvn_kd_res `9956f931…`、parser `cc7745e7…`、
  supervisor `19c727ca…`；package 645；metallib 717（72 `_bf`）；两真实 exemptions 已离线核对）。不把本轮计算值当 expected。
- `launcher.py`：默认 preflight-only，无 run dir/child；`--launch` 需已有 run、构造固定 host/patched/preflight/exempt
  与 `--gate-mib 2800 --gate-secs 10 --secs 180`；env 白名单 + 禁止 `IMGSUP_TEST_*/IMGBIND/PSOFAIL_RT*/SSBO_OBS/skip/
  override/BINDAUDIT`；测试只用 mock supervisor，真实路径未运行。
- `supervise_gsres.py` 修正：coverage 移除 fabricated source，记录 result/record_obtained/validated/original gs_present；
  gsres.json 加 validated/record_obtained/matcher_result；finally 写 `stop.json`（kind/reason/terminal/success）。
  checked gsres writes：失败→supervisor-error/evidence-write-failed，内存 hit 不报 success。
- 真实豁免：`imgdiag-run3/run-20261021-171600/shdump` 的 95bf/a841 ctl/code 长度与 full SHA 与冻结 exempt 一致，只读核对；
  synthetic two-exemption 测试仍只是算法测试，不冒充真实内容。

## 1 tests

- `test_preflight_launcher.py` 42 checks，FAILS0：
  - 真实 preflight 正例；
  - host/source/parser SHA 错、89 pairs、8 facts、metal count 错、chain 错副本均拒绝；
  - launcher 默认无 run/marker；mock route 验证 host、gate 2800/10/180、KEYDUMP/GSRES 覆盖、white-list 无 test env；
  - 禁止继承 `IMGBIND` 在 mock 前拒绝。
- supervisor 入口 22 cases，FAILS0：
  - hit/unbound/partial hit、nonhit、truncated-line、split（最终 hit）、no-record host-exit、no-record wall-clock deadline；
  - bad frame/bad-then-good/wrong VS、control invalid-config/diagnostic、近似 diagnostic；
  - same-poll nonexempt dump 保留 hit record 但 stop success=false；两个 synthetic exempt 后继续 hit；
  - evidence-write-failed、sample-nonzero/empty/timeout、child finally `gone_at` 全部通过。
- preflight/launcher 正例只读运行；未启动真实 host/child/gate/guest/GPU；synthetic child 24?/22 cases 中的 child 均为 test-only。

## 2 状态/缺口

- `STATUS.md` 标记 **ready-for-review, not launch-authorized**；真实 gate/guest 需单独明确授权。
- 未实现真实 `--launch` 运行证据；launcher 真实路径只准备，未执行。
- split 中途文件探针仍 gap；两真实 GS 内容豁免未测（仅身份/长度/hash 与 synthetic 算法）；`prePopen guard` 已在基线，未改。
- 无 host/source 重编；无 guest/GPU；旧证据保留。
- INDEX/EXPERIMENTS 加 exp152；request 152 归档。


---

## 3 P1 修复（launcher/preflight）

- **launcher 以 kdgeom run-kdgeom.sh 为契约**：删除自造 `DM_NVN_PSO/MEMSTAT/INPUT*/ENGB/AUDIO*`；固定
  `DM_ROMFS=/path/to/external-drive/xc3/build/RomFS`、`DM_SAVE=<run>/save`、`DM_TEMP=<run>/temp`、
  `DM_MSL_DIR=/path/to/external-drive/fout-six-lgt-correct645/out`、`DM_NVN_SHMAP=<profile>/shader_map.tsv`、
  `DM_NVN_SHDUMP=<run>/shdump`、`DM_PSO_RECORD=<run>/pso_user.tsv`、`DM_MEMSTAT=<run>/memstat.tsv`、精确 `DM_KEYS`、
  `DM_LANG=en-GB`、`DM_AUDIO=0`、KEYDUMP/GSRES；其余 DM 全丢；冲突 env 用真实全名拒绝。
- **patched 固定目录** `/path/to/external-drive/build/patched_v3`；supervisor 用 identity 固定路径并校验 SHA；生产 launcher 不提供
  `--supervisor/--identity` override，测试用 `--test-supervisor` 隔离；默认打印完整 DM 配置+精确 argv，且不创建 run。
- **preflight 用 identity 全量**：json_tree_sha 实际校验；对 map 每 key 检查 `_b.json/.metal/.metallib` 与 JSON chain；
  72bf 用冻结 tree；runtime exempt 校验文件 full SHA+全文值（不只 key set）；patched 必须是目录；
  map 仍用生产 `validate_map`→`validate_pairs`（645/90）。
- **测试改为真实 artifact 副本**：复制 out 后删一个 metallib、改一个 JSON chain、复制类 runtime exempt 改同 key 的
  ctl_sha、supervisor 路径不存在、patched 指向文件；均拒绝。mock 完整 env/argv 逐项断言 ROMFS/SAVE/TEMP/MSLDIR/MAP/
  SHDUMP/PSORECORD/MEMSTAT/KEYS/LANG/AUDIO/KEYDUMP/GSRES/2800/10/180。
- 修正 identity `metal_count` 为实际 717（645 normal +72 `_bf`），此前 2008 是目录所有文件数。
- 旧 launcher/preflight/错误 env 与只比较 exempt key set 的说法作废；旧证据保留。
- 仍未做真实 launch/gate/guest/GPU、真实两 GS 内容豁免、split 中途探针。
