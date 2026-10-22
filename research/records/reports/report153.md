# report153 · 首次真实 95bf GS 资源快照（gate 通过，hit / validated）

日期：2026-10-22 09:32–09:33（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变，branch `xc3`；仍为未提交的诊断改动 `nvn_mtl.m` / `nvn_kd_res.h`）
授权：owner 在机器重启后明确要求再试（“电脑重启了，你再试试”）→ 本轮**一次 gate + 至多一个 guest**。无 commit/push/PR。

---

## 0 结果

- **gate 首次通过**：11 个样本、整窗 10.095 s、min available **2835 MiB**（首样本 2837，末样本 2840），阈值 2800 不变。
- 启动 **1 个 guest**；`launch_at=10.113`，在 `first_at=63.312` 拿到**第一条真实 95bf GS 记录**：`result=hit`、`validated=true`、`terminal=hit (header-associated)`；随即优雅终止（`term_at=63.325`、`gone_at=63.450`、`exit=0`、`stop.json success=true`）。
- run：`/path/to/external-drive/xc3/work/experiments/gsres-real-run-20261022-093229`（fresh，未复用旧 run）。
- 只读观察；无生产代码/库/lock/chain/profile/facts 改动；轮内无重试、未改阈值、未切诊断 env。

## 1 证据

- `gate.csv`：`0.000,16384,4240,177229,110,2837` … `10.095,16384,3941,177585,262,2840`（11 行，min 2835）
- `timing.txt`：`kind=hit / reason=hit (header-associated) / exit=0 / launch_at=10.113 / first_at=63.312 / term_at=63.325 / gone_at=63.450`
- `gsres.txt`（记录原文 + 同 draw 的 `[kd]` 行）、`gsres.json`（`validated:true`、`matcher_result:hit`）、`coverage.txt`、`stop.json`
- `boot.log`（38,232 B；`[kd]`/`[kd-geom]`/`[gs-res]`/`[pass]`/`[RED]` 上下文）
- `exemptions.txt`：两 GS 的 ctl/code 长度+全 SHA（`95bf…` 2176/4bb2164e…、768/a6f403ed…；`a841a5…` 2176/601359d6…、1280/608f3da3…）
- `shdump/95bfab6122539993.{ctl,code}`、`a841a5d995c26b26.{ctl,code}`
- `memstat.tsv`、`pso_user.tsv`（647 行）
- 冻结 parser 独立复核（见 §3）；`gsres-observe-plan/last-launch.log`、`last-run-path.txt`

## 2 记录本身（事实）

- 命中条件：PS key `2e16c536b845ea0e` 与 `DM_NVN_GSRES` 目标一致；GS stage 程序的三个 shader key =
  `[d1657e5077b26d1d, 95bfab6122539993, 2e16c536b845ea0e]`，目标 `95bfab6122539993` 在其中；`gs_present=1 nstage=3 gs_query_calls=3`（`kdr_gs_identity` 命中，非“猜测”）。
- `frame=1508 pass_counter=3168 drawkind=direct prim=0 count=2304 instances=1 base_instance=0 indirect=0`；同 draw 的 `[pass] D` 行：`tgt=960x544 vp=0,0,960,544 sc=0,0,960,544 dt=0`。
- **GS UBO0**：`addr=0x7d82762300 size=32 ubo_mask=0001`；`contents=unavailable`（观察器按设计不读 guest 内存）。
- **GS tex**：唯一非零 slot 0，句柄 `0x10100316` → tid **790**、合并 sampler sid **257**；registry 已注册，描述符快照 `target=1 format=1 64x36x1 samples=0 reg_serial=1845`；句柄推出 `hint_ser=0x735`(=1845) 与 registry serial **一致**。
  - NVN 枚举：`target=1` = `NVN_TEXTURE_TARGET_2D`，`format=1` = `NVN_FORMAT_R8`。
- **GS samp**：`S.samp[2][*]` 全 0（`samp_mask=0 samp_n=1 samp0=0`）→ 该 stage 没有独立 sampler 绑定；记录里的 sampler 描述符来自**合并句柄**的 sid 257：`min=0(nearest) mag=0(nearest) wrap=7,7,7(=CLAMP_TO_EDGE) lod 0..15.999 aniso=1 cmp=0/1 border=0`。
- `tf=unknown final_pass_association=none bind_source=current_S_state`。

## 3 交叉校验（并排除一个假 bug）

- **不矛盾**：同 draw 的 `[pass]` 行（`st1` = fragment）写的是 **Metal** 值——`tid=782 ser=1841 fmt=115(pixelFormat) 640x360x1 target=2(MTLTextureType2D) swz=2345 mtl=0x7609a10000`；`[gs-res]` 写的是 **geometry stage 的 NVN** 描述符——tid 790、`format=1`、64×36、`target=1(NVN 2D)`。stage 不同、枚举不同（`t.textureType` 是 Metal 枚举，不是 NVN target），若按 NVN 读 `target=2` 会误判为 bug。
- UBO 地址/大小与 `[pass] cb reg0 addr=0x7d82762300 size=32` 完全一致；`[kd] fragment uniform r0` 独立打印了同地址内容：
  `0.015625 0.0277778 0 0 0.00104167 0.00183824 0 0` = **1/64, 1/36, 1/960, 1/544**。
- sampler 与 `[pass] B ... samp reg1 sid=257` 逐字段一致（nearest/nearest、7,7,7、LOD 0..15.999、aniso 1、cmp 0/1）→ 两条独立路径对 sid 257 给出同一配置。
- 冻结 parser 独立复核：`parse_gs_res` 成功、`validate_record` 接受、字段与 `gsres.json` 一致。
- registry 语义：`treg` 保存**注册时**的 NVN 对象快照（descriptor 已写入 pool），不是实时重读；`reg_serial` 与句柄 serial 一致说明快照未过期。

## 4 两个 GS 二进制（离线复算，非本轮新发现）

- `95bf` / `a841a5`：ctl 2176 B、code 768 / 1280 B；`ctl[:4]=0x98761234`、`code[:4]=0x12345678`、`ctl+0x704==len(code)` 全部通过；code `+0x30` SPH stage = **gs**。
- 用 `sha256(ctl[:0x880]+code)[:16]` 复算 key，与文件名**逐字符一致**（`95bfab6122539993`、`a841a5d995c26b26`）→ dump 与冻结 exempt 同一身份。
- 该二进制身份在 report148 已离线核对过 hash；本轮新的是**真实资源快照**，不是二进制本身。

## 5 同帧上下文（TF / 缺失 shader）

- frame 1500 脚本按键后：`SetRasterizerDiscard on`（host 忽略）→ `nvnCommandBufferClearColori` 未实现 → `BindTransformFeedbackBuffer` / `BeginTransformFeedback(size=0x120a8)` / `EndTransformFeedback` **三条全部未实现**。
- 同一次提交里：`[RED] shader a841a5d995c26b26 / 95bfab6122539993 is not in the shader map` → **两个 GS 都不在 shader map**，host 侧 GS 阶段被丢弃。
- 因此本记录描述的是**游戏意图的绑定**，不是 host 已执行的几何语义；GS 执行与 TF 都仍是 host 缺口。
- TF 三条调用在 frame 1500，命中 draw 是 frame 1508/pass 3168：同场景，但日志**不能证明**二者同 pass。

## 6 算术观察（假设，未证）

- `2304 = 64×36` 恰好等于 GS tex 的 64×36；UBO 同时含 1/64,1/36 与 1/960,1/544（960×544 正是本 draw 的 target/viewport）；960/64=15、544/36≈15.1 px/cell。
  → 假设：64×36 网格、每格 1 点，GS 把每点扩成 tile、并读 64×36 的 R8 每格数据。**仅是算术一致，未证**。
- TF 缓冲 `0x120a8` = 73896 B ≈ 4×2304×8 = 73728 B（差 168 B）→ 与“每点 4 顶点 × 8 B”一致，但 168 B 无法解释，**不据此推断**。

## 7 限制 / 勘误风险

- `contents=unavailable` 是设计；本轮内容可得属于**巧合**（GS 与 PS 共用同一 32 B UBO）。若下一 draw 不共用，内容仍缺。
- sampler 描述符由**合并句柄**推出：`samp_mask=0` 时仍会 `registered=1`，读取时不要把 `samp_registered=1` 当成“S.samp 里有绑定”。
- 只有 1 条记录（命中即终止，supervisor 设计如此），不代表 95bf 在所有 draw 的资源形态。
- 运行环境一处无关失败：`[RED] save transaction: cloning the work directory failed (errno=45) → 以只读挂载 committed save`（本次不写存档；不影响记录）。

## 8 状态与下一步（需 owner 新授权）

- 95bf GS 真实资源快照已取得（UBO0 / tex0 / 合并 sampler / target / 两个 GS 缺失于 shader map / TF 调用）。
- 仍缺：真实 GS 执行语义、TF 内容、其它 draw 的 95bf 形态、`S.ubo[2][0]` 之外的 slot。
- 若要继续真实观测：需 owner **新的单次授权**（fresh run）；不得重用本轮、不得因“1 条记录不够”而重跑。
- 不需要 guest 的只读工作（95bf GS 代码离线分析、shader_map 缺口核对）不消耗授权。

---

## 9 勘误（追加，旧原文保留；主管限定 review 后）

1. **撤回 TF size**：`dm/gfx/nvn/nvn_protos.h:371-372` 的 `nvnCommandBufferBeginTransformFeedback` / `EndTransformFeedback`
   原型只有 `(NVNcommandBuffer*, NVNbufferAddress)` 两个参数（`BindTransformFeedbackBuffer` 才是 `(command*, int, address, size_t)`）；
   `dm/gfx/nvn/hle_nvn.c:54` 的未实现 stub 无条件打印 `x0/x1/x2`。故日志 `BeginTransformFeedback … x2=0x120a8` **不是已证参数、更不是 size**；
   撤回 §6 的 73896 B 及其与 `4×2304×8` 的一切容量关联。x2 在两参函数上只是无关寄存器值，不赋语义。TF 实际 buffer size / 关联仍 unknown。
2. **撤回 h_ser 语义**：`h_ser(h)` = `g_tser[h & 0xfffff]`（低 20 位 tid → atomic serial hint），不是句柄内编码的 generation；
   它与 registry serial 1845 相同只说明两次采样的标签一致，**不能**证明 descriptor 未过期，也不能证明实际 view / 最终 Metal 资源。
   删除 §2 末、§3 末“快照未过期”的结论。
3. **收窄 samp_mask=0**：它只表示当前 `S.samp[2][*]` 的 raw 值全零，**不能**推出历史从未独立绑定；合并 sid257 候选 descriptor 的观测本身仍成立。
4. **UBO 关联的性质**：同地址 / 同 32 B 与紧邻 PS 的 CPU 打印，只能称“同命令邻近 PS 路径对同 guest 地址的内容观察”；
   地址相等不能证明 GS 读到的精确瞬时/GPU 内容，也不能证明 pin/生命周期或安全读取方案已解决。日志浮点只是打印精度；
   §2 的 1/36 等应读作“约等/相容”，不是 bit-exact 数据。
