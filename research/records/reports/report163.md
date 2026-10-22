# report163 · TF-NEXT-IMPL：独立 matching host + 专用 TF-intent 观测计划（ready-for-independent-verification）

日期：2026-10-22 14:3x–15:1x · HEAD `1408257`（未变，HEAD 不是候选身份）· 实现方任务（90 分钟离线）。
未 commit/push；**未运行 host（含 --help）**、无 gate/guest/GPU/device/PSO/真实内存采样/轮询；未改 shader/profile/facts/library/lock/chain、
共享 host、AGENTS/XC3-SETUP、V001–V005 快照与验证方目录。route 继续 NO-GO；CPU/编译成功不升级为运行证明。

## 0 结果

- **源与 V005 一致**：`nvn_tf_diag.h b27fb321…`、`nvn_obj.h 8e9f93e2…`、`hle_nvn.c 029efe76…`、`nvn_mtl.m ee708ad5…`（manifest 核对）。未改生产源。
- **独立 host 构建成功**（只编译链接，未运行）：
  `/path/to/external-drive/xc3/work/experiments/tf-intent-host/dmhost-tfintent`
  SHA256 `931a241f60e2bd1d3f7c672c817b163972e6ecccfd7128607053698f6a3d12b3`；构建 rc=0，55 warnings，0 error。
- **专用观测计划**：`/path/to/external-drive/xc3/work/experiments/tf-intent-observe-plan/`，含专用 matcher（[kd]→validated [gs-res] HIT→[tf-intent] 链）、supervisor、preflight、launcher、identity、测试。
- preflight-only 实测 **PASS**（新 host + V005 source + 旧 profile/library/patched/exempt 精确身份）。
- 基础测试 `tests/test_tf_next.py` **fails 0**（链语义 + launcher 默认路径 + 零真实 sysctl/vm_stat/ps）。
- 状态：**ready-for-independent-verification**，不是 launch-authorized。

## 1 host 构建

| 项 | 值 |
|---|---|
| 输出 | `/path/to/external-drive/xc3/work/experiments/tf-intent-host/dmhost-tfintent` |
| SHA256 | `931a241f60e2bd1d3f7c672c817b163972e6ecccfd7128607053698f6a3d12b3` |
| compileline | 复用 `gsres-observer-fix/compileline.txt` 原文，仅改 `-o` |
| cwd | `/path/to/user/projects/nxnative-xc3/dm/host` |
| clang | `/usr/bin/clang` Apple clang 21.0.0 (clang-2100.3.34.2) |
| SDK | `MacOSX.sdk`（Xcode） |
| include 顺序 | `../gfx/nvn/include`、`../third_party/vulkan-headers/include`、`gsres-observer/gen`、`fout-six…/profile/010074F013262000/`、`gen/010074F013262000/profile`、`../third_party/libvpx`、`../third_party/stb_vorbis` |
| env | 空（`build.env` 记录）；无 SDKROOT/ARCH/CFLAGS 覆盖 |
| chain strings | 链接进二进制；`identity`/preflight 另行核对 `c7c374c3eb34` |

日志/记录：`tf-intent-host/build.sh`、`build.env`、`build.log`、`dmhost-tfintent.sha256`。**未执行该二进制**（未测 `--help`、未启动）。
输入源/头 SHA 记录：`tf-intent-host/inputs.sha`（V005 四文件 + nvn_kd_res）。

## 2 观测计划（新目录，原 `gsres-observe-plan` 未改）

| 文件 | 内容 |
|---|---|
| `gsres_parser_base.py` | 冻结 parser 原样副本（sha `cc7745e7…`），`[kd]`/`[gs-res]` 解析与校验 |
| `tfintent_parser.py` | 专用 `parse_tf_intent` + `TfIntentChain`：gs-res HIT **不终局**；仅同 frame/pass/VS/PS/GS 的 `[tf-intent]` 完成链；语法/值域/字段一致性；raw 保留 |
| `supervise_tfintent.py` | 复制已审 supervisor：保留 gate（2800 MiB/10 s）、sampling、180 s deadline、LogTail、finally、信号、CRASH/FATAL、两条精确 GS exemption；只替换 matcher 与 evidence（`tfintent.txt/json`） |
| `preflight.py` | 固定新 host + V005 四源 + 新 parser/supervisor/launcher + 旧 profile/library/patched_v3/exempt 精确身份 |
| `launcher.py` | 默认仅 preflight/打印；不建 run/child；实际 argv 为 `sys.executable + 固定 supervisor`；新增 `DM_NVN_TF_DIAG=1`、`KEYDUMP=2e16c536b845ea0e:1`、`GSRES=95bfab6122539993:2e16c536b845ea0e`；阈值不变 |
| `identity.json` | 新身份（host `931a241f…`、nvn_mtl `ee708ad5…`、nvn_kd_res `9956f931…`、tf_diag `b27fb321…`、obj `8e9f93e2…`、新旧工具 SHA） |

matcher 语义：`[kd]` 头与 `[gs-res]` 必须经冻结 parser 校验且 `result==hit`；之前出现的 `[tf-intent]`、错 frame/pass/VS/PS/GS、非法 active/pause/reason、
`copies>events`、截断行、`diagnostic-error`、重复/矛盾控制行 → 终局非成功。`active` 的 unknown/inactive/active 三者都可完成记录；
输出仍标 `final_pass_association=none interpretation=observed-replay-intent`，不把 intent 当实际 TF 状态证明。缺 `[tf-intent]` 行 → 不完整记录（非成功）。

## 3 测试（基础，不宣称独立验收）

- `python3 tests/test_tf_next.py` → **fails 0**：gs-res HIT 不终局；完整链成功；frame/GS 不匹配、intent 先于 HIT、active/reason 值域、
  `copies>events`、截断、`diagnostic-error`、重复终局幂等；active 三值均可完成。
- preflight-only：`python3 preflight.py` → `PREFLIGHT-OK`（新 host、V005 源、645 map/90 pairs/717 metallib/72 `_bf`、patched_v3、两条 exemption）。
- launcher 默认：不建 run/child；打印的 child 配置含 `DM_NVN_TF_DIAG=1`；argv 用 `sys.executable`；阈值 `2800/10/180`；
  `--launch` 相对路径/已存在目录均拒绝（rc 3）；测试期间 monkeypatch `subprocess.Popen/run`、`os.popen`、`os.system` 为抛错 → **零真实 sysctl/vm_stat/ps 调用**。
- 记录：`tf-intent-observe-plan/tests/test_tf_next.py` 输出、`preflight.py` 输出（`tfintent.infra.sha` 记录五个工具 SHA）。

## 4 未做 / gap

- 未运行 host、未做真实 gate/guest/GPU/采样；湿运行（真实 `--launch`）未调用。
- supervisor 的完整 180 s 路径、信号/finally、exemption 观测、dump-after-hit 等只继承代码，未在本轮合成测试中重跑（V 系列已测部分未重复）。
- matcher 对“重复 `[tf-intent]`”只能在链内观测到第一次即终局（supervisor 停止），重复行本身不会进入判定；已在测试中覆盖“终局幂等”。
- 未覆盖：多线程/并发初始化、PROF/big/fullkd 入口、真实 producer 输出、日志落盘校验、F3 命令流内存边界。
- 验证方反例由其独立准备；本轮未向其提供任何测试答案。

## 5 状态

`ready-for-independent-verification`，**不是** launch-authorized。source/candidate/host 目录保持；等独立验证与主管派修。
