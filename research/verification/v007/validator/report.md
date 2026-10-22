# V007 定点复验报告

只读冻结候选；产物仅 `v007/validator/`；host 未执行（`--help` 也未跑）；无 commit/push。route NO-GO。

## 0. 身份

- manifest `0504466f…3dbf3b` 匹配，**23/23** 文件 SHA 一致
- host `931a241f…3d12b3` 一致；四源与 V005 相同（按 SHA 继承，未 rebuild）
- `identity.json` 的 parser/supervisor/launcher/tfintent_parser 引用与实际冻结文件逐一匹配（`evidence/identity_refs.json`）
- V006→V007 变化 7 文件（identity/launcher/preflight.log/supervisor/test_fixes/infra.sha/tfintent_parser）

## 1. 链回归（F2/F3/F4/F6）：16/16 PASS

- 真实 `[dm] [nvn-mtl] [tf-intent]` 前缀：完成 `hit`，且该行保留在 `chain.raw`；裸行为对照
- unknown/active/inactive 都完成（仅记录取得）
- 生产 `[kd] attr/stream/uniform` 子行不再破坏 header（F2）
- bare 正常 PS 完成（F3）；depth `-2147483648` 接受、`2147483648` 拒绝（F4）
- 畸形 KD、坏后缀、坏 hex、包裹前缀均拒绝；u64 MAX 通过、MAX+1 拒绝

## 2. supervisor 与 F1 写入失败：6/6 PASS

| 用例 | 结果 |
|---|---|
| 正确链（真实前缀） | validated/success，coverage+stop+timing 齐全，**child 已回收**（真实 PID 检查） |
| 仅 gs HIT | record=1、intent=0、validated=0，回收正常 |
| OSError（coverage/stop 为目录） | `evidence write failed`、timing 有 exit/term/gone、无 success 声明、**child 已回收** |
| 非 OSError（validator 副本注入 ValueError，已披露） | 同上保证 |
| sampling-error 注入 | kind=sampling-error，child 回收 |
| 两条合成 exempt dump 后正确链 | exempt 被跳过，链仍完成 |

## 3. F5 路径身份：10 项（1 SKIP）

PASS：fresh experiments 路径接受（不 mkdir）、相对/已存在/`/tmp` 之外拒绝、symlink 逃逸按 realpath 拒绝；
preflight 实际只读正例通过；把 host 指向真实副本后 preflight 报错（非只改 expected）。
SKIP：跨设备分支需 run root 内已存在子目录，会写到 validator 之外，仅保留源码分支（`launcher.py check_run_path` 的 `st_dev` 比较）。

## 4. mutation（import 0 / run≠0）

- M1 恢复旧 header 键（`pass_`/`fs`）→ S1 失败（evidence/hit 路径回归）
- M2 去掉 MLOG 前缀处理（`PREFIX='[never] '`）→ F6a 失败

## 5. 未覆盖

完整 180 s gate、真实 dump 内容、真实 host capture、PROF/F3；设备分支 SKIP；短超时 + synthetic-sampler 已披露。
CPU 通过不是 launch 授权；route NO-GO。
