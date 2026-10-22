# report146 · 纯 gs-res record parser + C fixture/tests

日期：2026-10-22 19:15–19:55（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变）；仅 SSD/CPU；无 host/guest/device/GPU/gate/资源采样、无生产/库/lock/chain 改动、无 commit。

---

## 0 交付

- 新模块 `gsres-parser/parse_gs_res.py`（202 行，sha `dd374c1c…`）：
  - `parse_gs_res(line)` 对完整合法生产记录返回 dict（含原 `raw`）；不是 gs-res 返回 `None`；gs-res 字段非法/截断/重复/多余 tail 抛 `ParseError`。
  - 可选 host 前缀 `[dm] [nvn-mtl] `，主体必须 `[gs-res] `；不做 hit/target 选择、不跨行。
- C fixture generator `tests/gen_fixtures.c` **直接 include 生产** `dm/gfx/nvn/nvn_kd_res.h`，调用 `kdr_format` 生成 4 例：
  - `hit_res.record`（hit，UBO/tex/samp 非零，tex/samp candidate+registry/desc）；
  - `hit_unbound.record`（hit，全 unbound、slot0 raw0、mask0）；
  - `partial_keys.record`（partial keys: unknown,target,unknown）；
  - `nonhit.record`（identity-unavailable，nstage0/keys空/资源未采集）。
- `tests/test_parse.py` 19 项 rc0；C generator 编译/运行 rc0；日志/SHA 保存。

## 1 语法/数域/内部不变量

- 固定前缀/顺序/完整尾部：`final_pass_association=none`、`contents=unavailable`、`reg_serial=unavailable`、`tf=unknown`、`bind_source=current_S_state`。
- u64/i32/u32/精确 16hex key、32hex mask、4hex ubo_mask；接受十进制与合法 `0x`；拒绝 u64 溢出/i32 越界。
- keys 长度=nstage，`gs_query_calls=nstage`；indirect 与 count/instances/base 组合；kind 枚举。
- tex/samp 各按上下文解析重复 `raw/registry_checked/registered/desc`，不使用覆盖字典；slot0 必列，列表升序/去重/≤9、0..127、mask/listed/omitted 关系、`tex_n/samp_n` 为 listed 条数。
- tex candidate0/1、tex raw==tex0、hint/desc availability；samp sid=raw>>20、sampler raw==combined tex raw；candidate0 的 raw/hint/registry/desc 合约。
- 0 与 0x 均保留数值语义；未知/未绑定不臆造 registry 容量或 descriptor 语义；不做 target/hit 跨行选择。

## 2 测试

- 4 合法 fixture 全部 parse；host 前缀/non-gs-res None；duplicate raw 组上下文；0x frame；u64 溢出；i32 越界；mask 矛盾；tex_n 数量；重复/顺序 slot；缺尾；truncated；extra garbage；sid 关系；candidate0 违约。
- 每项测试范围：语法/数域/记录内部一致性；未做 renderer/supervisor 运行。
- 未覆盖/未断言：registry 实际容量/描述符语义、ubo_avail/mask 的完整交叉、部分 availability 组合、target 选择、跨行状态；标 TODO，不称 strict-ready。

## 3 范围/状态

- 仅 parser + fixtures/tests；未实现 kd 状态机、supervisor matcher/output、preflight、launcher、child/injection tests。
- 旧 `gsres-observe-plan/STATUS.md` 仍记录 supervisor 未完成；本 parser 是独立可调用模块。
- 工作树 repo 诊断改动未提交；host 冻结未重编；无 guest/GPU。
- 文档 INDEX/EXPERIMENTS 加 exp150（parser/fixtures/tests）；request 150 归档。
- 45 分钟内完成；停止 review，无自动后续实现。


---

## 4 P1 修复（主管 review；旧结论保留为历史）

- shader token：接受 VS/PS bare、`_b`、`_bf`，保留 actual token；`ps_style` 必须与 PS 后缀一致；VS `-` 显式 `vs_form.form=absent`；
  其它 suffix 归 `other`（配 `ps_style=other`），不静默 canonical。纯 parser 仍不做 target 选择。
- omitted：允许 mask 中存在未列出的位；校验 listed 非零与 mask 一致、`pop>=listed_nonzero`、
  `omitted=pop-listed_nonzero`；slot0 仍必列（资源可用时）。新增 `omitted_mask`（>9 listed + 高 64 位 mask）fixture。
- nonhit/nstage：修正 `nonhit` 为真实空列表（avail=0、n=0、mask=0、无 slot0）；新增 nstage7（keys 最多6 unknown、query0）、
  target-not-obtained（avail0）；nstage≤6 query=nstage、>6 query0。
- 数字/异常：显式十进制/0x 解析；lod/aniso 先验证 8hex 再转换；坏 lod/aniso 抛 `ParseError`，不再裸 ValueError。
- 旧四 fixtures 保留在 `fixtures.pre-fix/`；新 fixtures 由 C generator 重生成；测试 31 项 rc0，逐项断言具体 ParseError。
- **未完成**：partial-nohit/full-mismatch 独立 fixture、registry 容量/descriptor 语义、完整 availability 交叉未做；不称 strict-ready。


---

## 5 A/B/C 完成（本轮）

### A validate_record
- 新增 `validate_record(r)`，未来状态机已调用，不能绕过；只验证 wrapper 确定关系，不猜 registry 容量/format 枚举/descriptor 物理语义。
- hit：ubo/tex/samp avail=1；ubo0 present，mask bit0 iff addr||size；tex candidate iff tex0 raw 非零、raw==tex0；hint iff 低20 tid 非零；registered 与 desc 同时且 registry_checked 先用；desc 不可用时字段为零 placeholder；sampler candidate/raw 由同一 tex raw 派生，不相干 `S.samp0`。
- nonhit：全部资源未读 placeholder（avail0、mask/n0、candidate0、descriptor unavailable/零），不允许把未读 0 当 absence。
- 反例：hit registry_checked0/registered1 被拒；nonhit 改 result=hit 被拒。

### B 状态机
- 新增 `GsResStateMachine(target_gs,target_ps)`，不硬编码 XC3 key；`[kd]` 锚 frame/pass/actualVS/PS，首个其它完整 PS 或 `_bf` 立即 target-not-obtained；bare/_b 目标继续。
- `[gs-res]` 必须与 header 的 VS/PS/frame/pass/prim 一致，direct counts 一致，indirect 用 unavailable 不伪对照；hit 要求 known keys 含 target GS；partial nohit identity-unavailable，full-known nohit mismatch，nil no-source；nonhit/invalid/diagnostic 终局非成功；bad record/重复 header/record-before-header/错帧终局 invalid，后续好链不能救；无 record 保持 waiting 不宣称 absent；旧诊断行忽略。
- 仅结构化 terminal/result/raw，无文件 IO/supervisor。

### C tests
- 生产 header C generator 现 11 fixtures：hit_res/hit_unbound/hit_b/omitted_mask（>9 listed+高64 mask）/partial_keys/partial_nohit/full_mismatch/nil/nonhit/nstage7/target_not_obtained。
- `test_parse.py` 33 项、`test_state.py` 25 项 rc0；覆盖 _b、omitted、非hit空列表、nstage7、直接/indirect、wrong VS/frame/pass/count、other PS/_bf、duplicate/bad-then-good/short diagnostic/old line、validate 反例。
- 未纳入 float/enum 物理语义；nstage7 按 keys 最多6/query0；合法负 i32 保留。
- 未完成：supervisor/output、preflight、launcher、child/injection；registry容量/descriptor语义仍未猜。
- 新 SHA 见 `identity.final.sha`；旧错误 fixtures 在 `fixtures.pre-fix/`。


---

## 6 最终 P1 修复（命中/容量/负例/控制行）

- **present0**：状态机在资源校验前把 `gs_present=0` 归 `no-geometry-source`；`hit_res` 改 present0 不再 hit。
- **nstage>6**：状态机先归 `identity-unavailable`（keys 最多 6），不把 known key 当 hit；`hit_res` 改 nstage7/query0/known key 不再 hit。
- `validate_record` 对 hit 另要求 present1、nstage 1..6；普通 nonhit placeholder 仍独立。
- **negative tests**：同一有效 F12/P23 基线先证 hit；再分别只改 VS/frame/pass/prim/count/instances/base_instance，并断言 terminal 具体原因；`hdr` 的 count 现在真正填 vertices。
- **控制行**：精确 `[gs-res] invalid DM_NVN_GSRES; observer closed` → `invalid-config`；`[gs-res] diagnostic-error: ...` → `diagnostic-error`，可在 header 前；裸 `[gs-res]`/截断 → `invalid`，不 None/裸异常；普通 record-before-header 仍 invalid。
- 新计数：parse 33、state 34，全部 rc0。旧 58 项记录保留，不撤。
- 未完成仍是 supervisor/preflight/launcher/child；registry 容量/descriptor 未猜。


---

## 7 P1 去早返回修复（最终）

- 控制行只认三条精确生产字符串：invalid DM_NVN_GSRES、identity copy overflow、record formatting overflow；近似 diagnostic 文本归 invalid，不再 `startswith` 吞尾。
- 普通完整 record 一律 **parse → validate_record → header VS/PS/frame/pass/prim/count 关联 → identity expected → claimed==expected**；删除 result/present0/nstage>6 早 return。
- identity expected：present0 要求 nstage0/query0/keys空→no-geometry-source；present1 nstage0/>6 要求 query0、keys为formatter的0/6个unknown→identity-unavailable；1..6 按 target known/partial/fully-known 得 hit/identity-unavailable/gs-key-mismatch；claimed 不符→invalid。
- present0 声称 hit→invalid（hit gs_present），nstage7 含 known key→invalid（hit nstage）；后续好链不能救。
- target-not-obtained 的普通目标 header + 完整 record 现在 invalid；合法路径只保留真实 other PS/_bf header 的前置终局；旧 target fixture 保留为 parser 测试，不作为 state 成功。
- negative 每个字段从同一 F12/P23 基线单独变异，断言 VS/PS、frame/pass、prim、count、instances、base 原因；各 nonhit 单独 wrong-frame 仍 invalid。
- 最终 **parse 33 + state 42** rc0。旧 34 项日志保留；其 target-not-obtained 期望标记为错误并已改为 invalid。未撤真实通过项。
- 未完成仍 supervisor/preflight/launcher/child；registry 容量/descriptor 未猜。
