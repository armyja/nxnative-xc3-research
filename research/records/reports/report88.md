# report88 · SSBO VS base 0x110 终局计划：唯一一次门控 + 唯一一次启动，三重记录在日志层成立

日期：2026-10-21 21:38–21:42（本机）
运行目录：`/path/to/external-drive/xc3/work/experiments/ssbo-vs110-final-plan/run-20261021-213817/`
预启动固定：`/path/to/external-drive/xc3/work/experiments/ssbo-vs110-final-plan/prelaunch-20261021-213811/`

---

## 0 本轮授权边界与本轮实际动作

授权：**一次 gate attempt，至多一次 guest launch**；`real` 与 `dummy` 都是终态（无论哪个先出现都不得再启动）；验收条件为同一次 pass 的三重记录：

1. `K st0` 的 VS key = `9b770cf888d729bd`；
2. 同一 pass 的 `[sbuf-final]` 同 key、`reg0`、`aid2`；
3. 同一 pass 的 `d` 记录 VS/PS = `9b770cf888d729bd` / `7faa92fddfdd06bd`。

附带禁令（全部遵守）：不修改脚本/代码/数值；不预启动轮询；门控失败即结束该授权；不得扩大豁免（仅两条按内容豁免的 GS）；不动 `AGENTS.md`、`XC3-SETUP.md`、共享 `dmhost`、旧 profile/库/证据；产物全部在 SSD 上。

本轮实际动作：门控通过 → **恰好一次** Popen 启动 → 验收条件在日志层成立 → 启动器自行 `complete` → 本轮停止，等待复核。没有第二次启动、没有重试、没有 refill、没有重建。

---

## 1 预启动固定（启动前写盘，未再改动）

`identity.sha`（逐行原样，12 项）：

[Fenced excerpt omitted from the shareable research record.]

`preflight.txt`（原样）：

[Fenced excerpt omitted from the shareable research record.]

即：宿主二进制（含唯一一次 `26c9ad81719f` 链号、`[sbuf-final]` 唯一一次）、启动器、预检、豁免表、profile 五个表 + 链头，全部在启动前固定并复核；`preflight ok` 通过后才进入门控。

---

## 2 门控（gate）

- 11 个样本，`elapsed` 0.000 → 10.094 s，**跨度 10.094 s ≥ 10 s**（按样本自身时间锚定，CSV 写入时刻不计）；
- 最小可用内存 **2902 MiB ≥ 2800 MiB**；
- 门控通过后 `Popen` 时刻 `launch_at=10.108`（`timing.txt` 中的 `launch=0.000` 是遗留字段，不代表启动时刻，见 §9）。

门控首末样本（`gate.csv`）：

[Fenced excerpt omitted from the shareable research record.]

---

## 3 三重记录（原样，带行号，同一 `boot.log`）

[Fenced excerpt omitted from the shareable research record.]

三条记录 frame/pass 完全一致（F4601 / p553094），stage 一致（st0），VS key 一致，`[sbuf-final]` 为 `reg0 aid2`，`d` 的 VS/PS 与验收条件一致。**验收条件成立。**

同一段落的其余原样记录（用于对照，不参与验收判定）：

[Fenced excerpt omitted from the shareable research record.]

该段 `[pass]` 共 12 条（行 581–593，无第二条 `553094` 的其它绘制）；`[sbuf-final]` 全日志仅 1 条。

`[sbuf-final]` 完整字段逐项：

| 字段 | 值 | 说明 |
|---|---|---|
| frame / pass | 4601 / 553094 | 与 K、d 相同 |
| stage | 0 | VS |
| key | `9b770cf888d729bd_b` | 与 K st0 相同 |
| reg / aid | 0 / 2 | 验收要求 reg0/aid2 |
| u | 1 | 解析可用标志 |
| addr | `0x7d9a95ba70` | 客端低地址（记录值） |
| rawsize / size | 140 / 140 | 一致 |
| resolved | 1 | 最终选择路径判定为可解析 |
| actual | real | 非 dummy |
| slot | `0x1516793a70` | 54 位，编码期写入的 Metal 侧地址 |
| rw | 0 | 只读 |

字段域全部落在计划允许范围（`resolved/u/rw ∈ {0,1}`、`actual ∈ {real,dummy}`、`size == rawsize`、`resolved=1` 时 `u=1` 且 `addr≠0`），`reg0/aid2` 未触发 `unexpected-candidate-record`；`real` + `slot` 非 0，未触发 `consistent-but-abnormal`。

---

## 4 同绘制一致性（可作为线索，不作为证明）

1. **缓冲区大小与实例数自洽**：`rawsize=size=140`，同绘制 `inst=5`，140 = 5 × 28；28 正是 NVSD 调查里 `U_Instance` 的声明大小，其偏移为 0x110。即：shader 声明的实例缓冲偏移（0x110）↔ 本次绑定记录的缓冲区大小（140）↔ 本次绘制的实例数（5）三者数值自洽。
2. **PSO 描述与本次顶点布局自洽**：`pso_user.tsv` 第 1612、1613 行是同一 pair 的两条 `R` 记录（432 字节：`vs[24]` + `fs[24]` + 描述块），解码后 `vs=9b770cf888d729bd_b`、`fs=7faa92fddfdd06bd_b`；描述块中的属性表（按描述块中打包的 u32 低字节为 format、次字节为 offset 解读）为 `(format 0x22, offset 0)`、`(0x16, 0xc)`、`(0x25, 0x14)`、`stride 24`，与 `[kd]` 头（553–557 行）打印的 `attr 0 format 0x22 offset 0`、`attr 1 format 0x16 offset 12`、`attr 2 format 0x25 offset 20`、`stream 0 stride 24` 逐项一致。
3. **目标 pair 没有被判 pipeline 创建失败**：全日志 `failed to create render pipeline` 共 12 条、11 个不同 pair，逐条核对**均不含** `9b770cf888d729bd` 或 `7faa92fddfdd06bd`（针对目标对计数为 0）。日志中存在的失败是别的 pair，例如 R8Uint 的 `f64e061d85e6f3a5_b/531d637463e53486_b`、RG32Uint 的 `a6201ef91b12f9e2_b/d3c541d46f389225_b`、fragment input 不匹配的 `d7bec51f33a503a4_b/ef5549568475fd20_b`。
4. **PS 资源同一性**：`R st1 ser=9125` 与 `tex reg0 ser=9125` 同对象，`fmt=130`、`512x512x1`、`array=1`、`view 0+10`；`samp sid=304` 解析为 real。
5. **cb 与 sbuf 是不同缓冲区**：`[kd]` 打印的 VS/PS 统一常量块为 `r0 addr=0x7d83ea7e00 size=400`、`r1 addr=0x7d9d70a400 size=48`（与 582/583、587/588 的 `B … cb` 地址一致）；`[sbuf-final]` 的 `addr=0x7d9a95ba70` 不在这两块内，`size=140` 也不同，说明本次 SSBO 绑定目标是独立缓冲区，不是被 dump 的常量块。

以上五点只说明“本次绘制的 PSO 描述、顶点布局、资源与绑定记录彼此自洽”，**不说明** GPU 真的读取了该缓冲区，也不说明内容正确。

---

## 5 时序

| 事件 | 时刻（s，自 T0=import） |
|---|---|
| T0 | 0（进程 import 即计时，门控计入 180 s 预算） |
| 门控样本 | 0.000 → 10.094（11 样本，跨度 10.094） |
| Popen（`launch_at`） | 10.108 |
| 首条 `[sbuf-final]`（`first_at`，即 `sbuf-final.txt` 的 `elapsed`） | 166.436 |
| TERM（`term_at`） | 166.439 |
| 子进程消失（`gone_at`） | 166.780 |
| 退出码 | 0 |

客端实际存活 ≈ 156.3 s；全程 166.8 s < 180 s 预算，未触发超时路径。

---

## 6 资源

| 指标 | 门控阶段 | 运行阶段 |
|---|---|---|
| 样本数 | 11 | 639（末条 `elapsed=166.211`） |
| 最小可用内存 | **2902 MiB**（阈值 2800） | **1623 MiB**（阈值 1024） |
| 最大 RSS | — | **1188 MiB**（1216160 kB，阈值 2048） |
| 日志 | — | 618 行 / 86117 B（阈值 64 MiB） |
| shdump | — | 1664 KiB（阈值 32 MiB） |

豁免：仅 2 条 GS 按内容豁免（`95bfab6122539993`、`a841a5d995c26b26`，均 63.157 s，ctl/code sha 见 `exemptions.txt`），豁免表未增长。

---

## 7 子进程回收与停止原因

`timing.txt` 原样：

[Fenced excerpt omitted from the shareable research record.]

- 停止原因是**验收条件达成**（`reason=complete`），不是超时、不是资源越界、不是字段非法；
- TERM 后 0.341 s 子进程消失，`exit=0`；TERM→2 s→KILL 的强杀路径未用上；
- 运行结束后 `pgrep -fl 'dmhost|nxnative'` 为空，无残留子进程。

---

## 8 本轮证明了什么、没有证明什么

**证明（日志层）**：在被强制记录的这一次绘制（F4601 / p553094 / st0 / key `9b770cf888d729bd_b`）上，编码期最终选择路径判定为 `resolved=1`、`actual=real`，并把 `slot=0x1516793a70`（非 0）写入该绑定的参数槽；该记录为 `reg0/aid2/u=1`、`rw=0`、`size==rawsize==140`；同 pass 的 `d` 记录的 VS/PS 与 `K st0/st1` 一致；目标 pair 无 pipeline 创建失败记录；PSO 描述与本次顶点布局一致。

**没有证明**：
- GPU 已提交/执行该绘制，或 GPU 实际读取了该缓冲区；
- 像素/内容正确；
- NVN 槽位映射正确：本记录只说明“在配置 base 0x110 时，该绑定解析成了 reg0 并写入了一个真实 GPU 地址”，不构成对“0x110 是真实 base”的独立验证（base 是配置输入，reg 由 `(off-base)/16` 得出，二者同源）；
- `slot` 与 `addr` 是同一对象：`slot=0x1516793a70` 是 Metal 侧 54 位地址，`addr=0x7d9a95ba70` 是客端低地址，命名空间不同，不得跨轮比较地址；
- `slot` 是纹理 rid/序列号：它是 buffer 地址，不是 `ser`；
- 旧 `B … sbufp … real` 行（585）中的 `real` 仍只表示“addr 非零”，不是解析成功的证据；真正的解析结论只以 `[sbuf-final]` 的 `resolved/actual/slot` 为准；
- tex/samp 未解数量不变（87/87）、9 条 image binding 仍为 reg0、2 个 PS c0 reader 不变；`c1` 的 `not proven bounded: 0 shaders` 语义不变（工具无独占 bank 需求，不是内存安全结论）。

另需注意：本轮未做“换 base 的对照”，因此本记录**不能区分** 0x110 与其他候选 base；若 base 取 0x40，同一偏移会得到 reg13 而非 reg0，所以本记录只与该配置自洽，不排除其它候选。做区分实验需要另行授权。

---

## 9 与既有记录/文档的差异与说明

1. `timing.txt` 的 `launch=0.000` 是遗留字段；真实启动时刻看 `launch_at=10.108`（report87 已就此勘误）。
2. `d` 记录没有 `count` 字段，只有 `vc=96 inst=5`；不要写成 `count=96`。
3. `pso_user.tsv` 本轮为 784 条 `R` + 1223 条 `S`；`R` 是 432 字节的 pair 描述（`vs[24]`+`fs[24]`+描述），`S` 是 `key stage` 两列。目标 pair 有 2 条 R、4 条 S（VS stage0 ×2、PS stage1 ×2）。
4. `[dm] [RED] pipeline prewarm: seed list does not exist: …/pso_manifest.tsv` 与本轮无关（预热清单文件不存在，仅提示）；`[dm] [RED] save transaction: cloning the work directory failed (errno=45)` 是环境提示，save 已回退到已提交目录。
5. 日志中的 `shader … is not in the shader map` 共 6 条（含两条按内容豁免的 GS）、`reflection conversion failed` 29 条、`NVN unimplemented` 47 条，均为既有类别，与本轮目标 pair 无交集。

---

## 10 仓库状态

- HEAD：`cac7c6f`（`[sbuf-final]` 最小记录提交），本轮无 tracked 改动、无 commit、无 push。
- `git status --porcelain` 只有既有的未跟踪文件 `?? XC3-SETUP.md`（mtime 2026-10-21 01:59，早于本轮，未触碰）。
- 新产物：`run-20261021-213817/`、`prelaunch-20261021-213811/`、本报告；均在 SSD 上。

---

## 11 结论与下一轮候选项（不执行，等复核）

结论：本轮授权的门控通过，唯一一次启动的日志满足验收条件（同 pass、同 key、reg0/aid2、`d` 的 VS/PS 一致），启动器以 `complete` 停止，资源与时序均在阈值内，子进程已回收。按授权，本轮到此为止。

候选项（均需新授权，本轮不做）：

- **A（区分 base）**：在同一绘制上用不同 base 做对照记录（例如临时把 vs base 配成 0x40），观察同一绑定的 reg 是否随之变化，以确认记录只反映配置而非“证明 0x110”。需要新的启动授权与脚本/配置改动授权。
- **B（GPU 侧）**：用 Metal capture / 读回确认该槽位确实被 GPU 读取（需要新的采集工具与授权）。
- **C**：转回 tex/samp 87/87 未解问题（有独立的静态/运行时证据链）。
- **D**：9 条 image binding reg0 与 2 个 PS c0 reader 的收敛。

不再启动、不再重试、不再 refill；等待主管复核。
