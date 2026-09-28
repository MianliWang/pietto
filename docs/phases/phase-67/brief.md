# Phase67：有限结果契约与 Arrow 互操作基础

规划层级 FULL；N67=16。描述性 Stage 目标是建立有限结果交换边界；现有资料没有数字 Stage，故不另造编号。
这是已接受全 Phase 计划的耐久入口。Slice01 的 CI/SDK 实验范围与预算见其历史记录；当前只授权
[Slice16](slice-16.md)，后续 Phase 仍须独立授权。包/CLI 保持0.1.0。

## 使命、当前能力与边界

现有 source → completed semantics → immutable IR → verified neutral ProjectSQLPlan → 显式 PostgreSQL/MySQL
emission 已具备有限 native correspondence。Phase67 从这些 retained authority 派生 target-neutral
PiettoResultContract 与 scalar-first ResultShape，再分别核对 ProducerResultBinding 和 ArrowResultBinding，
交付 RecordBatch／有限 reader 消费链。转换不能修补 producer 谎报，下游不重解上游语义。

Slice01 已发布 CI governance 与两解释器真实 PyArrow25.0.1 SDK/lifetime/device 实验；它未实现产品结果。
Slice02 交付 private Int batch 薄纵向；Slice03 增加独立 canonical private bytes、bounded pure decoder、runtime correspondence/invalidation。Slice09增加相对显式caller extent的有限完成；Slice10连接CPU C协议及ownership，Slice12连接有界private IPC；Slice13交付公开optional extra及安装隔离。
Slice07已关闭显式private Timestamp/UUID meaning前提；默认无meaning仍拒绝。Slice08连接有限scalar、typed empty/all-NULL和显式carrier labels。CPU是当前成功域。

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

## Slice04 已发布历史边界

[Slice04](slice-04.md) 仅扩Int16/32/64、Bool、finite Float64的checked producer/Arrow owned batch；完整domain-total显式整数适配、physical/logical Bool分离、IEEE754 signed-zero值oracle保持。codec与上游语义不变。发布链全部通过后Slices01–04完成，Slice05 NEXT/NOT STARTED；不推进后续payload/reader/protocol/IPC。

## Slice05 已发布历史边界

[Slice05](slice-05.md) 仅扩 verified builtin Text source/projection与mixed scalar结果：exact Unicode、显式32/64 offsets、source-bound collation/padding、保守引用buffer与实际UTF-8准入计费。没有Arrow比较语义、native新SQL输入、reader/IPC/API扩展。自然CI及raw证据全部通过后Slices01–05完成，Slice06 NEXT/NOT STARTED，07–16 NOT STARTED；package/CLI0.1.0。

## Slice06 已发布历史边界

[Slice06](slice-06.md) 在正确HOLD后经明确批准，将shared参数precision上限38扩至65、语言scale≤p；当前producer保留scale≤min(p,30)。Decimal128/256结果采用context-free精确fixed-scale转换，正负Decimal零统一系数0，Float signed zero不变。原10份canonical documents保持，新增4份Decimal/mixed；计划47cases/45controls以实际required consumer证据为准。发布链完整通过后Slices01–06完成，Slice07 NEXT/NOT STARTED，08–16 NOT STARTED；不新增算术、nominal、reader或IPC成功域。

## Slice07 当前private边界

[Slice07](slice-07.md) 显式取得并独立核对真实builtin source occurrence的meaning；private emission/result共同保留该authority，仅field-only scan/projection进入新成功域。Timestamp为无timezone civil microseconds，inclusive1000-01-01至9999-12-31 23:59:59.499999；UUID保留标准big-endian128bits，默认canonical extension，binary16需field-bound请求。旧public/default missing-meaning行为及S06 Decimal接受扩展保持。计划56cases/54controls及原14+新4份完整文档以最终证据为准；完整publication/raw闭合后Slices01–07完成，Slice08 NEXT/NOT STARTED，09–16 NOT STARTED。

## Slice08 与 midpoint

[Slice08](slice-08.md) 保留七类logical scalar和12种既有physical choices，以真实双target source、独立身份/值/NULL/资源oracle连接owned batch；explicit carrier label不改neutral字段或producer observation。P67-A02/A06/A08的当前owned范围完整，其余验收的剩余部分见[三层midpoint](slice-08.md#midpoint-三层状态与最终评估)。S09 reader至S16 closeout仍为必需，固定N67=16不变。

## Slice09 当前reader边界

[Slice09](slice-09.md) 连接P67-A09/A10及A15的有界stream部分：保持真实batch boundaries、NULL与positional values，逐批sum(max(A,R))记账，normal EOF+exact caller extent+successful close才发session-bound completion。P67-A09的broader ingress/whole-result仍归S11/S15；A10的IPC及execution归S12/Phase68；A15的protocol/IPC界面仍归S10/S12。S08 midpoint路线保留，不把这些跨Slice义务整项提前完成。

[Slice10 ownership/CPU interop](slice-10.md) 关闭P67-A11/A13及A07/A15的当前protocol部分；cooperative CPU范围、borrowed non-mutation义务、原S09条件完成与PyArrow消费者证据限制见唯一合同，不宣称独立C实现或executor成功。

[Slice11](slice-11.md) 连接A09/A12及A15的explicit rows/RecordBatch/raw reader入口；复用原checker/ownership/conditional completion。A09 whole-result assurance仍归S15，A15 IPC仍归S12；协作输入前提与原值correspondence边界见唯一合同。

[Slice12](slice-12.md) 连接A14及A07/A10/A15的IPC部分：framing完整性、caller extent与原S09完成条件分开；metadata不授权。S12已在 `8f5333fd` / CI `36343560204` 完成publication与raw/native闭合；N67=16不变。

[Slice13](slice-13.md) 交付唯一 `pietto[arrow]` / `pyarrow==25.0.1`，compiler core仍Arrow-free，
结果API仍私有。same-wheel core/extra在Linux x86-64的CPython3.12/3.13分别验收；原9SDK、
102product/100damage与22neutral全文保持。仅在tested tree普通发布、自然15jobs与raw/native
全部闭合后Slices01–13完成，Slice14 NEXT/NOT STARTED，15–16未开始；不是release。

[Slice14](slice-14.md) 在两target原G/H/I/J八cells连接真实source/binding、rows与独立SDK输入、
C-array/C-stream及IPC三route；TABLE populated/empty另经一个移动project后的installed child。
fixture执行与已strict验证native receipt的实际rows重放分开；无新查询/driver/executor。
原102/100扩为110/108，SDK9及22neutral全文保留；aggregate在原strict后新增required ≤2MiB
sidecar，原27份加1为28。成功发布/自然15jobs/raw/native及当前receipts双local replay闭合后
Slices01–14完成，Slice15 NEXT/NOT STARTED、Slice16未开始；N67=16不变。

[Slice15](slice-15.md) 在原110/108上增加十组whole-result laws与十项实质damage controls，
最终120/118；三route按类型/位置保值保NULL保重，重分批与资源成本分别核对；pure/bound authority、
source/delivery/IPC完成与owned/borrowed义务保持原层。22neutral全文由本次双runtime生成并与S14
verified全文比较；原八cell五类native replay/28raw/15jobs保持。Phase68 readiness见唯一Slice15矩阵，
完整local/publication/raw/native/current-replay闭合后Slices01–15完成，Slice16 NEXT/NOT STARTED；
Phase67 ACTIVE/N67=16，S16审计与Phase68均未开始。

## Slice16 completion candidate

上方逐Slice段落保留当时的发布边界与NEXT记录，不覆盖本段当前状态。

S01–15已由实际publication闭环；当前[Slice16](slice-16.md)为ACTIVE/CANDIDATE，
Phase67仍ACTIVE/N67=16、Phase68 NOT STARTED。[唯一三层完成审计](completion-audit.md)
集中A01–A18、实际工作/费用、六条lessons及handoff。最终状态只依[唯一闭环规则](slice-16.md#唯一闭环规则)
由实际外部record激活；不预写future commit/CI，不开始Phase68 FULL规划或实现。
