# Phase67 Slice02：ResultContract / ResultShape 与 Int Arrow 纵向

基线 cffb59b29961b4a75552979093d0a18f369cf7df，tree dbf77f6ed1097a728134059544e0aad6e497bc09，
sole parent e0d02247f1f6410c1715ef22eb3c6e254726a962；自然 push/main36099028120 attempt1 的15jobs 已 rebind。
本次只执行 Slice02；成功 seal、普通发布、自然 exact-head CI 与 raw evidence 核验后才为 COMPLETED/PUBLISHED。

## 可观察行为、存在的边界与真实连接

真实 source → completed semantics/verified ProjectSQLPlan → PiettoResultContract/ResultShape → checked
ProducerResultBinding → explicit ArrowResultBinding → owned RecordBatch。new private owners 为
project_result_contract、project_result_binding、project_arrow_result；均无 public root export。

contract 保留 exact selected owner/output、全部按序 port/field references、declared TypeExpr（可用时）、canonical
resolved scalar、effective nullability、provenance、multiplicity 与 ordering。独立 verifier 对 retained upstream
逐项核对，不能用 labels/dicts/bytes/Arrow metadata 重建身份。scalar leaves 可多列，未知/Shape 拒绝；本 Slice
producer 成功域限定 direct-source/projection builtin Int，不新增 nominal/refinement/type solver。

producer checker 复用完整 emission verifier 和已固定 field realization，保留 column/export correspondence；
只支持 pg_int8/my_bigint、已批准 signed64 int_range 与确定 logical nullability。supplied metadata/rows 是观察，
不是 DB execution 认证。protocol nullable 可以未知，也不覆盖 logical nullable；没有 cursor/connection adapter。
同一个 neutral root 可绑定不同合法 physical domains；两个相似编译 root 仍不同。label/ordinal/width/family/domain
失配先拒绝，widening 不得修复。支持边界以实际 checker 为准，后续形态在各自 Slice 明确扩展。

Arrow 只在显式路径动态导入，缺依赖抛 private `ARROW_DEPENDENCY_MISSING`；core无依赖/网络行为。
explicit int64 schema 保留 nullable 与位置；验证有限 positional list/tuple rows 的arity、精确Python int、signed64、
producer domain和实际NULL，然后拥有新buffers。Bool/float/Decimal/string不隐式转Int。空批次/全NULL可空列仍显式定型；
重复值和输入sequence保留，但不提升无ORDER查询的保证。caller container mutation不影响owned batch；不声称抵御unsafe memory写入。

hard ceilings：64 fields、4096 rows、8MiB data+validity；预算为 fields×(8×rows+ceil(rows/8))，小配置只能收紧。
不实现 Table/read_all、borrowed success、multibatch/finite finalization、IPC、PiettoFiniteResult 或公开 extra。

## 冻结见证与原有 assurance

| 组 | required positive / discriminating negative |
| --- | --- |
| 两target真实source | id:Int not null + other:Int nullable；输出 renamed=id, other；pg_int8/my_bigint 到真实int64 batch |
| 身份/字段 | same neutral root两realization；equal-looking foreign root、drop/swap/duplicate/ordinal/label拒绝 |
| 精确值 | 9007199254740993重复、0、负数、在全signed64域中的两端点；窄域端点外拒绝 |
| typed empty/NULL | zero rows、nullable all-null；非空列NULL、Bool、float/string/Decimal、错误arity拒绝 |
| producer与独立checker | wrong width/ordinal/domain；producer+Arrow协调篡改仍从真实上游失败；schema/null corruption拒绝 |
| ownership/resources/imports | caller mutation后保持测值；小field/row/byte ceiling拒绝；core缺Arrow确定失败；有效读取不reparse/re-emit |
| installed消费者 | fresh3.12/3.13 candidate wheel、真实PyArrow25.0.1、完整input closure与实际imports、14组独立测值/负例 |

原九组 SDK readiness probe保持独立必需；ordinary tests不安装Arrow、不用skip替代positive。
当前native receipts来自新head；不把new source modules当作输入未变。本地DB/Docker因不改target语义/driver而明确豁免。
参考限定既有Arrow实验及其RecordBatch/array接口，不开展新生态调研。此处只证明batch数据/表示对应，不证明SQL执行成功。

## Gate、预算与证据

外部 evidence 根 `~/.local/state/pietto/evidence/phase67-slice02/`，前缀 `pietto-phase67-slice02-`。
十九冻结路径 A6/M13/D0；不改workloads、acquisition、native fixtures/pins/receipt schema、core lock、.venv或.agents。
诊断6、focused12、causal correction6、full-equivalent2默认1、review/followup1/1、Q2、fresh env2；
每local解释器product probe≤3，CI执行另计；新Arrow下载≤256MiB（复用两已hash核验wheels）；commit/push1/1，
必要failed-CI child/push/delta-review各≤1；native strict verifiers≤4默认3。agents/detached/manualCI/localDB=0。

Gate2：主作者整合/Ponytail review、必要一批root-cause repair和targeted followup；一次3.13 equivalent
包含五static gates、独立fullU、四分区串行新root及完整对账/health、generated/golden/package一次、两runtimeSDK与
installed Int product。所有heavy经guard on、最多4workers；固定既有project3.13.13，不重建环境。
Gate3：rebind baseline与sealed tree、普通sole-parent commit/FFpush；观察natural attempt1全部15jobs，raw artifacts逐份
核对ID/length/digest/context，逐runtime coverage/product及PG/MySQL/aggregate strict native checks。health仍仅advisory。

Phase67 ACTIVE/N67=16；成功后Slices01–02 COMPLETED/PUBLISHED，Slice03 NEXT/NOT STARTED，Slices04–16 NOT STARTED。
Phase66/Interlude V/R1保持完成；0.1.0不变。执行代理在本次终态停止。

## Gate2 实测终态

一次完整3.13.13 equivalent 用时 818.341s：16274 collected/selected/terminal，全部passed、0 skips；
shared=315、plan=3、emission=3、general=15953。原assurance保留，新增44个ordinary节点；
一个current lifecycle节点只迁移名称与当前Slice断言。static五项、generated/golden/package及两runtime九组SDK/14组installed product均通过。
product reports另拒绝13种真实保存数据篡改，159个实际Pietto origins与core/Arrow dependency路径/版本核验通过。
292项focused followup与244项depth-one通过；主作者/Ponytail review的一批修正闭合，无独立第三方review宣称。
首次focused输入缺scan及类型检查失败均保留；累计diagnostic2、focused7、correction2、review/followup1/1，
full1/2，local product probes3.12=1/3、3.13=2/3。两fresh env，Arrow复用原100,206,889-byte官方wheels，新增Arrow下载0。
项目3.13.13/18 distributions/Arrow-free与.agents字节保持；没有DB、agents、detached jobs、手动CI或resource abort。
最终HEAD/tree、自然CI实际artifact inventory、strict native结果与耗时在外部seal/ledger；本段不预言CI成功。

执行顺序偏差：上述64/4096/8MiB限额与case manifest在实现前写入外部Gate1 freeze，slice-02.md在产品初版之后同步；限额从未改变。未将后补文档冒称实现前的仓库记录。
