# Phase67：有限结果契约与 Arrow 互操作基础

规划层级 FULL；N67=16。描述性 Stage 目标是建立有限结果交换边界；现有资料没有数字 Stage，故不另造编号。
这是已接受全 Phase 计划的耐久入口。Slice01 的 CI/SDK 实验范围与预算见其历史记录；当前只授权
[Slice03](slice-03.md)，后续 Slice 仍逐次 dispatch。包/CLI 保持0.1.0。

## 使命、当前能力与边界

现有 source → completed semantics → immutable IR → verified neutral ProjectSQLPlan → 显式 PostgreSQL/MySQL
emission 已具备有限 native correspondence。Phase67 从这些 retained authority 派生 target-neutral
PiettoResultContract 与 scalar-first ResultShape，再分别核对 ProducerResultBinding 和 ArrowResultBinding，
交付 RecordBatch／有限 reader 消费链。转换不能修补 producer 谎报，下游不重解上游语义。

Slice01 已发布 CI governance 与两解释器真实 PyArrow25.0.1 SDK/lifetime/device 实验；它未实现产品结果。
Slice02 交付 private Int batch 薄纵向；Slice03 增加独立 canonical private bytes、bounded pure decoder、runtime correspondence/invalidation。有限完成、C 协议、IPC、公开 optional extra 仍待各自 Slice。
Timestamp/UUID meaning 仍有 Phase66 V05 前提，Slice07 在首次映射前关闭。CPU 是当前成功域。

## 三层完成验收与回归

可观察：以下有限类型、NULL、BAG/order/multiplicity、绑定、生命周期与完成语义有真实正反消费者。
已存在：private canonical contract、pure decoder、runtime correspondence、可选依赖/资源边界及隔离安装。
已连接：upstream authority → contract → producer → Arrow binding/batches → finite consumption/close；
不能以 SDK roundtrip、字节相等、immutable wrapper 或 EOF 替代这条链。

| 稳定 ID | 全 Phase 完成准则 | Slice owner |
| --- | --- | --- |
| P67-A01 | target-neutral contract 保留 selected owner/root、全部按序 field occurrences、名称/位置和语义引用；不得由 target/driver/Arrow 推断身份 | 02基础；03、15–16闭合 |
| P67-A02 | 保留 declared/canonical scalar、value domain、nullability、nominal/refinement 身份；ResultShape 单一 scalar authority，结构可扩展但不引入 Struct/List/NestedRelation 成功域 | 02；04–08 |
| P67-A03 | producer binding 分开核对 exact representation/domain/nullability/provenance；同一语义根可有多个合法 binding，失配在转换前拒绝 | 02；04–07、14–15 |
| P67-A04 | Arrow binding/schema 显式、可独立核验；仅有声明且 lossless 的 adaptation，不能让 widening 修复 producer lie | 02；04–07 |
| P67-A05 | 独立 canonical private bytes 与 bounded pure decoder；pure consistency 不等于 live runtime correspondence；拒绝 resurrection、stale/graft 与 missing tail | 03、15 |
| P67-A06 | 有限类型 ledger：Int16/32/64、Bool、finite Float/signed zero、Unicode、Decimal128/256、timestamp(us，无时区转换)、UUID；只宣称实际支持域 | 04–08 |
| P67-A07 | 默认 string、显式 large_string；collation/padding 不成为 Arrow equality authority；canonical UUID extension 与显式 binary16 备选；时间/UUID meaning 先在上游闭合 | 05、07、10、12 |
| P67-A08 | empty/all-null 仍有 explicit types；实际 NULL 遵守合同；carrier duplicate labels 按 ordinal 保留，不取消语言 PIE-S2305 | 02基础；08完整 |
| P67-A09 | RecordBatch/finite reader 保值、NULL、multiplicity、已有 order；覆盖 rechunk/empty batches，不强制 Table/read_all/combine_chunks 或整结果复制 | 09、11、15 |
| P67-A10 | batch、finite completion、executor success 分开；empty 不是 EOF、prefix 未闭合、IPC EOF 不证明查询完成；attester/denominator 明确 | 09、12；Phase68执行 |
| P67-A11 | owned/borrowed/transferred 的 lifetime、non-mutation、release 和 memory domain 明确；CPU 成功、unsupported devices 拒绝 | 02 owned；10完整；Phase86设备 |
| P67-A12 | positional rows 与 Arrow-native ingress 共享 checker；不从首行猜类型、不重建 candidate 掩盖 validation failure | 02 seam；11完整 |
| P67-A13 | CPU C Data/PyCapsule/C Stream 有真实 consumer/lifetime checks；PyArrow-backed 通过不等于独立 C 实现认证 | 10、14–15 |
| P67-A14 | bounded private IPC 验证有效/畸形/truncation/completeness/metadata forgery；IPC bytes 不是语义身份 | 12、15 |
| P67-A15 | field count、batch rows/bytes、batch count/total bytes、contract bytes、IPC bytes 有明确 ceiling，超限以小 fixtures 拒绝 | 02最低界面；03、09–12 |
| P67-A16 | compiler core Arrow-free；optional install path 与 private API 隔离实测，无额外 release/range promise 或公共泄漏 | 01证据；02 seam；13–14 |
| P67-A17 | real producer/result consumers、independent negatives、whole-result metamorphics；data correspondence 不等于 SQL 正确性或 runtime obligations 完成 | 14–15；Phase68/81 |
| P67-A18 | 保留原 semantic/compiler/package assurance、真实 skips 与解释器域；closeout 对账 numbered/unnumbered 工作、成本/readiness/incidents，提炼3–7条教训供下一 Phase 消费 | 每 Slice；16 |

以上准则是已批准要求的归属，不代表各项当前已实现。[固定16行路线](slices.md) 中的 acceptance IDs 可直接追踪。
保留 parser/AST/source locations、semantic identity、SQL/diagnostics/CLI/JSON、native assurance 与全量测试。

## 范围、成本与风险

必需：上述验收、Slice08 midpoint、Slice16 三层审计和 retrospective；可选：可获得的 CPU/内存观测，缺失标 unavailable。
Phase 外：executor/连接/事务/取消/backpressure、nested relation、public stable format、签名信任、device/DLPack、Rust runtime。
每 Slice 单独冻结文件、可用预算与真实 evidence；Slice01 的 src 禁令和实验预算不限制后续已授权产品 Slice。
Slice02 的路径/资源/累计 starts 在其说明与外部 ledger，不能继承或重置 Slice01 计数。

三项主要风险：producer/逻辑/Arrow authority 混淆；buffer lifetime 或 EOF 被错认成完成；验证成本和环境漂移。
对应手段是独立 checker/negative、明确 ownership/completion，以及 guard/固定解释器/一次 full equivalent。
health/history 只作 advisory；没有新 alert 不启动 CI 维护。

后续 owner：Phase68 execution，69 public alpha，71 nested，80 Python adapters，82 public format freeze，
83 stable1.0，84 stronger trust/signing，86 device/DLPack，90 Rust/PyO3；91–97 保持 tentative/owner-only。
