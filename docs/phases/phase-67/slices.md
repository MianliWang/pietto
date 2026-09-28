# Phase67 路线：N67=16

当前只展开已授权 [Slice16](slice-16.md)，[Slice01](slice-01.md) 为已发布历史。后三层acceptance见 [brief](brief.md#三层完成验收与回归)；各后续Slice在获得执行授权后才展开自己的精确验收。

| Slice | 目标／acceptance链接 | 依赖／类型 |
| --- | --- | --- |
| 01 | 启动、耐久规划/教训、工作CI治理、真实Arrow兼容/生命周期/device实验（P67-A16/A18；[验收](slice-01.md#三层验收)） | Phase66 + R1；joint foundation/experiment |
| 02 | ResultContract/ResultShape与一个Int的producer→Arrow→batch[薄纵向](slice-02.md)（P67-A01–A04/A08/A11–A12/A15–A16；[验收](brief.md#三层完成验收与回归)） | 01；thin vertical |
| 03 | [canonical private bytes、pure decoder、runtime correspondence/invalidation](slice-03.md)（P67-A01/A05/A15；[验收](brief.md#三层完成验收与回归)） | 02 |
| 04 | Int/Bool/Float、NULL、signed zero、显式lossless adaptation（P67-A02–A04/A06；[验收](brief.md#三层完成验收与回归)） | 02–03 |
| 05 | [Text/Unicode、string/large_string/collation](slice-05.md)（P67-A02–A04/A06–A07；[验收](brief.md#三层完成验收与回归)） | 04 |
| 06 | [Decimal128/256 precision/scale与overflow](slice-06.md)（P67-A02–A04/A06；[验收](brief.md#三层完成验收与回归)） | 04 |
| 07 | [Timestamp/UUID与显式upstream meaning](slice-07.md)（P67-A02–A04/A06–A07；[验收](brief.md#三层完成验收与回归)） | 04 + 01 decisions |
| 08 | [empty/all-null/duplicate-label carrier及完整finite-type integration；midpoint](slice-08.md)（P67-A02/A06/A08；[验收](brief.md#三层完成验收与回归)） | 04–07 |
| 09 | [bounded finite reader/finalization、rechunk、BAG/order](slice-09.md)（P67-A09–A10/A15；[验收](brief.md#三层完成验收与回归)） | 08 |
| 10 | [ownership/copy/borrow、CPU、C Data/C stream/PyCapsule](slice-10.md)（P67-A07/A11/A13/A15；[验收](brief.md#三层完成验收与回归)） | 09 |
| 11 | [row与Arrow-native ingress correspondence](slice-11.md)（P67-A09/A12/A15；[验收](brief.md#三层完成验收与回归)） | 09–10 |
| 12 | [bounded private IPC、truncation/completion、metadata](slice-12.md)（P67-A07/A10/A14/A15；[验收](brief.md#三层完成验收与回归)） | 09–11 |
| 13 | [公开可安装optional extra与wheel isolation](slice-13.md)（P67-A16；[验收](brief.md#三层完成验收与回归)） | 02–12；消费Slice01实验，不重复实验campaign |
| 14 | [真实producer/result consumer integration，无产品executor](slice-14.md)（P67-A03/A13/A16–A17；[验收](brief.md#三层完成验收与回归)） | 13 |
| 15 | [whole-result differential/metamorphic assurance与Phase68交接](slice-15.md)（P67-A01/A03/A05/A09/A13–A14/A17；[验收](brief.md#三层完成验收与回归)） | 14 |
| 16 | [三层完成审计、回归、retrospective与lessons](completion-audit.md)（P67-A01/A18；[验收](brief.md#三层完成验收与回归)） | 15 |

Slice08执行 S/H/L/K/Q midpoint：复核价值、现状/health、lessons、路线/预算与Q；保留固定16行，不自动新增Slice17。
解冻条件：新的product/trust选择、批准要求损失、不可解dependency/support前提、实证成本超预算或支持域改变；
将冲突集中呈现，不把implementation detail升级审批。

Phase68接已验证result/binding/batch/finite-finalization合同，不重决编译语义；execution success、连接、事务、
取消、runtime failure和backpressure由68负责。Phase69 public alpha、83 stable1.0、90 Rust；91–97保持tentative。

## Slice01 执行记录

联合授权共用一份ledger；已完成一次author/Ponytail review和一次targeted follow-up，一次完整本地equivalent
为826.439s、16230 passed/0 skips。CI-governance与Arrow-readiness各自command wall
为5.697s／9.479s，共用validation另列于[Slice01](slice-01.md#gate2-实测与分项成本)。
未复用S3/R1预算；两runtime的真实Arrow探索＋最终probe共4次，非重复完整套件。
一次ordinary commit/FF push与自然exact-head全15jobs的最终事实、artifact IDs/digests及总成本保存在外部终态证据。
成功后Phase67 ACTIVE／N67=16／Slice01 COMPLETED-PUBLISHED；Slice02 NEXT/NOT STARTED，03–16 NOT STARTED。

## Slice02 当前交付

[Slice02](slice-02.md) 连接首个private Int产品消费者并完整归属P67-A01–A18。最终发布事实以Git、自然CI和外部ledger为准；
成功后Slices01–02 COMPLETED/PUBLISHED，Slice03 NEXT/NOT STARTED，Slices04–16 NOT STARTED。禁止自动进入Slice03。

## Slice03 交付与停点

[Slice03](slice-03.md) 保留完整中立字段、类型与 import provenance 描述，分别执行 bounded pure consistency 和 supplied-live-authority correspondence。原14个产品案例与9个SDK案例保留；两runtime新增codec消费者、完整bytes比较和raw evidence核验均为必需。
发布链通过后 Slices01–03 COMPLETED/PUBLISHED，Slice04 NEXT/NOT STARTED，Slices05–16 NOT STARTED。不开始Slice04。

## Slice04 已发布历史边界

[Slice04](slice-04.md) 仅扩Int16/32/64、Bool、finite Float64的checked producer/Arrow owned batch；完整domain-total显式整数适配、physical/logical Bool分离、IEEE754 signed-zero值oracle保持。codec与上游语义不变。发布链全部通过后Slices01–04完成，Slice05 NEXT/NOT STARTED；不推进后续payload/reader/protocol/IPC。

## Slice05 已发布历史边界

[Slice05](slice-05.md) 仅扩 verified builtin Text source/projection与mixed scalar结果：exact Unicode、显式32/64 offsets、source-bound collation/padding、保守引用buffer与实际UTF-8准入计费。没有Arrow比较语义、native新SQL输入、reader/IPC/API扩展。自然CI及raw证据全部通过后Slices01–05完成，Slice06 NEXT/NOT STARTED，07–16 NOT STARTED；package/CLI0.1.0。

## Slice06 已发布历史边界

[Slice06](slice-06.md) 在正确HOLD后经明确批准，将shared参数precision上限38扩至65、语言scale≤p；当前producer保留scale≤min(p,30)。Decimal128/256结果采用context-free精确fixed-scale转换，正负Decimal零统一系数0，Float signed zero不变。原10份canonical documents保持，新增4份Decimal/mixed；计划47cases/45controls以实际required consumer证据为准。发布链完整通过后Slices01–06完成，Slice07 NEXT/NOT STARTED，08–16 NOT STARTED；不新增算术、nominal、reader或IPC成功域。

## Slice07 当前private边界

[Slice07](slice-07.md) 显式取得并独立核对真实builtin source occurrence的meaning；private emission/result共同保留该authority，仅field-only scan/projection进入新成功域。Timestamp为无timezone civil microseconds，inclusive1000-01-01至9999-12-31 23:59:59.499999；UUID保留标准big-endian128bits，默认canonical extension，binary16需field-bound请求。旧public/default missing-meaning行为及S06 Decimal接受扩展保持。计划56cases/54controls及原14+新4份完整文档以最终证据为准；完整publication/raw闭合后Slices01–07完成，Slice08 NEXT/NOT STARTED，09–16 NOT STARTED。

## Slice08 midpoint 路线结论

[已完成的S/H/L/K/Q评估](slice-08.md#midpoint-三层状态与最终评估)保留全部16行和原依赖；S09 finite attester/denominator与total budgets、S10 lifetime/release、S12 IPC completion、S13 packaging在各自首次接口前决定。S08发布完成后仅将Slice09置NEXT/NOT STARTED，10–16未开始；不添加S17或规划interlude。

## Slice09 交付边界

S08延后的extent/attester/limits三项已由用户明确批准：caller先声明，session绑定exact source/binding，完成只相对声明；同步pull与source布局保留；最多1024批/1048576行/64MiB累计费用。正常EOF、close成功与独立session receipt共同验收。S10ownership/non-mutation/protocol、S11ingress、S12IPC/独立completion envelope及后续owner未提前实现。发布闭环后Slice10 NEXT/NOT STARTED，11–16未开始。

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
