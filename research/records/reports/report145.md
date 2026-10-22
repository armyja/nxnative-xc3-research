# report145 · wrapper index5 测试修正 + gs-res 严格监督计划

日期：2026-10-22 18:30–19:10（本机）
HEAD `14082571ea0a1ea515be64b963e4f4d7c39a3097`（未变；repo 诊断改动未提交）；仅 SSD/CPU；无 host/guest/device/GPU/gate/资源采样、无生产/库/lock/chain 改动、无 commit。

---

## 0 wrapper 测试修正

- `index5` 改为真实第六 entry：`gs.nstage=6`、`stub_nstage=6`；keys0..4 均为已知非目标，target 仅放 **index5**；
  断言 `stub_prog_calls=6`、`nstage=6`、`gs_query_calls=6`、record hit；不再由 index0 目标误命中。
- 重跑 actual-wrapper stub suite（ASan/UBSan）rc0/fails0；source/host 固定：`nvn_mtl.m` sha `faf06a9b…`、
  `nvn_kd_res.h` sha `9956f931…`、`dmhost-gsres2` sha `9f3df170…`；未重编 host。
- **mutex 限界**：stub body 有 4 处 `pthread_mutex_lock/unlock` 文本被替换为计数 stub；生产锁不变。不是 100% 原样提取，
  报告/测试明确这一层；其余匹配/格式 body 原样。

## 1 gs-res 监督计划（未实现 matcher/injection）

- 新目录 `gsres-observe-plan/`：复制 `kdgeom-plan/supervise_kdgeom_v2.py` 骨架为 `supervise_gsres.plan.py`；
  `diff` 为 **空**（gate/sampling/threshold/deadline/complete-dump/two-GS exemption/finally/signal/bounded tail 逐字未改）。
- `PLAN.md` 固定：
  - `[dm] [nvn-mtl] [gs-res]` 非裸行首匹配；`[kd]` header 锚 frame/pass_counter/actualVS/PS；PS bare/_b normal，
    `_bf`/首 forced 其它完整 PS terminal `target-not-obtained`。
  - 唯一正常 hit：完整 production record，result=hit、GS known 含 95bf、PS 2e16、frame/pass 与 kd 一致、
    `final_pass_association=none`、尾部 `bind_source=current_S_state`；unbound/unavailable 也是有效 hit。
  - nonhit 完整 record 终局非资源成功；无 record 只叫 no-record-obtained；不恢复 knownskipped/notreached。
  - 严格 uint/i32/u32/hex/masks/slot/omitted/query/candidate/registry/desc 语境解析；截断/坏 numeric/重复/矛盾/tail 缺失 invalid；
    旧 kd-geom/img-final/sbuf-final/tex-final/PSORT 不触发；同 poll 完整非豁免 dump 优先；两个 GS 豁免仅原 hash/长度。
  - preflight 只读固定 host/source/map/pairs/package/lib/c1/profile/chain/patched；生产 validate_map/pairs，不 import dmsh_build；
    launcher 默认 preflight-only 不建 run；env 白名单与排除项、2800MiB/10s/1GiB/2GiB/32/64/180s gate 逐字保留。
- **尚未实现**：matcher/output 替换、synthetic child/injection tests、preflight/launcher 代码、同 poll dump 路由测试。
  因此本轮是“计划+骨架复制”，不声称 supervisor 可运行或资源 snapshot 已准备完成。
- 当前 host `dmhost-gsres2` 仍只编译未运行；旧 host not guest-ready。

## 2 边界/状态

- 无 guest/GPU/device/PSO/资源采样；cbuf contents unavailable、TF unknown、descriptor/view/final resource 未观测；
  PS2e16 资源/RT 未扩。
- 工作树：`nvn_mtl.m`/新 `nvn_kd_res.h` 未提交；其它 profile/库/lock/chain/旧 host 未改。
- 文档 INDEX/EXPERIMENTS 加 exp149（wrapper test fix + supervision plan）；request 149 归档。
- 60 分钟内到计划层；停止 review，无自动 guest/GPU/supervisor 实现。


---

## 7 内存澄清后状态

- 主管澄清 2800 MiB 只是未来 guest gate，不阻塞 SSD/CPU plan 实现；但本轮仍按 60 分钟上限工作。
- 实际新增只有：wrapper index6 测试修正（已在 §0）与骨架/PLAN 复制；严格 matcher/output、preflight、launcher、
  synthetic child/injection tests 仍未实现。一个未完成 parser 草稿已删除，不留在目录中冒充实现。
- 未重跑 host/gate/guest/GPU；未再做资源采样。状态文件 `gsres-observe-plan/STATUS.md`。
