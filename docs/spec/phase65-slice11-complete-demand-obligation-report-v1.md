# Phase65 Slice11 Complete Demand And Obligation Report v1

本交付沿用 D65.01–D65.12、N16 和显式 TABLE/QUERY selection。基线 commit
`0c025b1060a93b9ab0999f71575830b7c25757ed`，tree
`3416da1d1f04614e30e6b525c4f91b603edb6051`，parent
`9de7991498e2258bf41557bae95f91152c9670f3`；自然 CI `34723478209`
为 push/main/attempt1/success。写前和重启恢复时均核对实时 refs、工作区、index、
Git 操作和相关进程。已有候选与累计计数继续使用，没有重开 Slice10。

## 独立只读产品与真实入口

`project_sql_plan_requirements.py` 构造一个可选的 immutable report，输入必须是
exact current ProjectSQLPlanVerification。它保留原 verification、plan、completed、
Query Block IR analysis bundle、selected owner、literal policy、fixed envelope、
完整 project diagnostic tuple 和原 input-use tuple。

构造时使用原 captured literal_policy/envelope 重新验证计划。bindings-only、
unavailable、failed/foreign roots、伪造 verified flag、stale request 都拒绝；同内容
envelope wrapper 也不能沿用旧 verification。新的有效请求需要新的 report。
报告不修改计划、semantic facts 或 demand carriers；普通 plan verification 不依赖报告。

入口为 `build_project_sql_requirement_report` →
`verify_project_sql_requirement_report` → `inspect_project_sql_requirement_report`。
既有 `ProjectSQLPlanInspection.requirements()` 连接这条实际消费路径。产品构造、
verification 和 view 边界各自验证一次；不按 entry 重验计划，不建立 persistent cache。
已有 plan queries、builder、verifier 和全部 demand/origin 构造保持。

## Producer / checker / report 矩阵

Source demand 顺序是原 `plan.demands` 的顺序，不重新按源码路径、值或消息排序。
每个 exact occurrence 对应一个 ProjectSQLDemandEntry，保留完整原 demand 对象、
ref、strict int position、family/subkind、subject、实际 consuming scope 和原 demand origin。
表中 carrier 均位于既有 plan owners；report 不创建替代 proposition。

| 原 carrier / 当前 subkind | 原 producer 与独立 checker | 保留命题与 report scope |
| --- | --- | --- |
| ProjectSQLSourceRealizationDemand / single | plan.build_project_sql_bindings / verification._binding_demands | 原 source binding、connector、IR/source evidence；source definition |
| ProjectSQLExportRepresentationDemand / single | 同上 | 原 field、logical_type、nullability；canonical export 的 definition，无伪造 terminal stage |
| ProjectSQLExpressionDemand / MATCH、LET、WHERE、SELECT、AGGREGATE_ARGUMENT、SATISFYING、QUALIFY | plan row construction / _row_origins_and_demands | 原 site/expression/ValueType、有序 operand_types；实际 expression site 的 block/aggregate context |
| ProjectSQLStageValueDemand / INPUT、EXPORT | 同上 | 原 stage port、type_evidence、block；不展开已有值 |
| ProjectSQLFilterDemand / WHERE、SATISFYING、QUALIFY | 同上 | 原 Bool/NULL evidence 和 SQL TRUE-only retention_effects；实际 predicate scope |
| ProjectSQLScopeDemand / LET、WHERE、PROJECTION、AGGREGATE、SATISFYING、WINDOW、QUALIFY | 同上 | 原 predecessor、ordered inputs/exports；实际 SELECT block |
| ProjectSQLJoinDemand / JOIN_ROWS、MATCH_INPUT、MATCH_FIELD、OUTPUT_FIELD、RELATIONSHIP_EQUALITY、POST_MATCH_SCOPE、SINGLE_MATCH、PROOF_CONTEXT | plan JOIN construction / _join_origins_and_demands | 完整 typed witness、kind/nulling/input pairs/relationship/assessment/proof；原 JOIN、tail 或 obligation scopes |
| ProjectSQLAggregateDemand / GROUPING_AND_EMPTY_INPUT、GROUP_COMPARISON、AGGREGATE_OPERATION、RESULT_PROJECTION、RETAINED_RISK | plan aggregate construction / _aggregate_origins_and_demands | 原 grouping/empty-input、keys、calls、result ports、risk objects；实际 block 与 aggregate operator |
| ProjectSQLWindowDemand / INPUT_BAG_AND_RESULT、INPUT_USE、ARGUMENT、POLICY、PROJECTION | plan window construction / _window_origins_and_demands | 原 input/default/offset、type、frame/modifier/named policy 和 IR effects；实际 window/block scopes |
| ProjectSQLResultDemand / BOUNDARY、PORT、DISTINCT、COMPARISON、ORDER、ORDER_ITEM、EXPRESSION、USE、HIDDEN、LIMIT、EXPORT | results.build 与 plan origin construction / _result_origins_and_demands | 原 quotient/equivalence/NULL、ORDER direction/ties/FD、LIMIT 和 canonical terminal images；实际 result/terminal scope |
| ProjectSQLSetDemand / OPERATION、PROPERTIES、COMPARISON、OPERAND、INPUT、COLUMN | sets.build_body 与 plan origin construction / _set_origins_and_demands | 原 operation/quantifier/multiplicity、row domain、equivalence、positional values 和 membership；SET body，operand/input 的 exact use |
| ProjectSQLLiteralDemand / Bool、Int、Text、Float | literal transport 与 plan construction / _literal_origins_and_demands、verify_fixed_literal_envelope | 原 use/slot/fixed value、全部五项 requirement tags 和 ancestor expression demands；原 defining expression context |

闭合 taxonomy 按 exact class 和 exact enum member 识别。未处理 variant/subkind
拒绝，没有 repr/class-name/message 匹配或 generic complete bucket。测试将当前
ProjectSQLDemand union 与真实 corpus 对照，不以历史 class 总数作为未来准入规则。

Demand origin 与 subject origin 分开：例如 EXCEPT 右输入的 demand origin 是
TYPE_PROOF，其原 origin antecedent 指向 MEMBERSHIP input origin。两者都保持原
ref/proposition，不把 type requirement 重标为 value contribution。原 origin.owner
和 consuming definition 分别保留，不改成 selected owner，也不依据 path/name 猜测
ownership。Imported/reexported source、原 FieldDef/type references、literal type-site
的 declaration owner 与 use trail 仍通过原 typed evidence 保留。

## 无损分组、关联和查询

Flat entries 是完整性 authority。所有 indexes 都是 immutable MappingProxyType，
其 members 保持 flat order。提供 exact demand ref、subject、definition、stage、
input-use context、family 和 original requirement 查询，以及 related/referring edges。
同一 demand 沿多个路径被访问不会增加 flat entries；不同的 equal-looking uses
仍然不同。同一 request 的重复 retained occurrence 也不合并。

Stage facets 包括真实 SELECT/JOIN/tail/result/SET scopes 及 retained aggregate/window
operators；projection 可同时关联其实际 block 和相关 operator。Input facets 表示
enclosing input context，JOIN input、SET operand/input 使用已有明确 use correspondence。
这些 facets 可能重叠，不是 value-lineage 推导，也不能相加作为完整性证明。
共享 definition 的要求只存在一次，不把 producer 要求复制进每个 consumer。

当前 subject domain 是 context index 中的已存在 plan nodes；其中没有 direct demand
的 source port 等节点可返回空 tuple。demand/origin/symbol metadata refs、foreign refs、
wrong-role refs 不被当作合法空查询。definition/stage/use 查询分别要求实际 owned role。
Family 查询要求 exact family enum；original requirement 查询使用 exact object identity。
内部 identity index 不序列化 Python id，不承诺跨快照稳定性。

三种有序 related edge 是 literal ancestor context、single-match root proof、proof child。
边指向同一 flat inventory 中原 entry，保留顺序与直接关联，不复制 ancestor demands
或递归展开 proof/producer DAG。Forward/reverse indexes 必须互相符合这些原始边。
Literal entry 的完整 requirement tuple 直接来自原 demand，包含 data representation、
nullability、range/precision、operator/operand context、collation/overload；没有宽泛
support flag 代替这些子命题。

## 状态分离与可用 summary

Summary 包含各 family 的实际 entry members、原 PROVED records、原 enforcement-required
records、pending hidden realizations、typed aggregate evidence 和 NOT_ASSESSED target。
demand_count 是附属信息，不能代替这些结构。没有 ready/executable/universal success flag。

- Single-match report 保留 exact request/assessment、scope/unit、ordered JOIN/input
  pairs、所有 proof images/premises 和原 Diagnostic。PROVED 仅是原 scoped static
  proof；LEGAL_UNPROVED 保留原 PIE-S2337 WARNING 与 enforcement posture。INVALID
  不能产生正向报告。Diagnostic 消息不用于推导状态。
- Hidden STRICT-FD ORDER 独立标为 pending_lowering_realization，保持 determinant、
  requested classes、source/property roots 和 input images。它不成为 available port，
  没有 MIN/MAX、representative、join-back 或 fulfilled flag。
- Aggregate group-protection、grain linkage、pair linkage 按原 typed carrier 分开。
  原 determinations、final_comparison、common_grain、structural posture、requirements
  全部留在原证据中；不发明统一 verdict，也不把所有 risk objects 归入 runtime enforcement。
- Source/type/NULL/window/SET/literal 等仍是 demands。没有 single-match obligation
  不表示 target 支持或计划可执行。完整报告可以同时具有 pending requirements。

完整 project diagnostics 保持原 tuple。Unrelated warning 不进入 selected obligations；
EXCEPT、SEMI/ANTI membership-only dependencies 和 LIMIT0 不删除 reached requirements。
RIGHT_LIMIT/RIGHT_GLOBAL proof 保持原 producer scope，不从最终 result bound 重算。

## 两层独立验证与实源覆盖

Layer1 调用已有 whole-plan verifier，检查 roots、mandatory feature inventories 和
literal request。Layer2 独立核对每个原 demand 到 entry、scope、origin、related edge、
obligation/risk/realization record、index 和 summary 的精确完整对应。
它不调用 report builder、classifier 或 summary builder，不复制第二套 semantic verifier。
共享部分只包括 closed taxonomy、类型和纯 membership/index utilities。

删除 plan.demands 由 Layer1 拒绝；删除 report entries/family/obligation/proof link/
hidden realization 或调整总数由 Layer2 拒绝。缺失、额外、重复、重排、wrong-role、
Bool ordinal、same-looking substitution、stale root/policy/envelope/report 均有控制。
View 边界 fresh verify，不修复输入。错误使用 closed issues/fixed messages；异常链
不得转储源 payload。Private full view 仍是 source-bearing，不是 redacted export。

真实 corpus 覆盖全部当前 carrier/subkind、两种 literal policies、minimal/row/JOIN、
PROVED/LEGAL_UNPROVED direct/hop/whole-path、RIGHT_LIMIT/RIGHT_GLOBAL、重复 request 与
unrelated warning、聚合风险/隐藏 grouping key、hidden window/QUALIFY、pending hidden ORDER、
SET right-only membership、mixed descriptors、depth12 sharing 和 imported/reexported owners。
Monkeypatch controls 禁止 downstream inference/resolution/proof/provider access、literal
classifier 和 report builder/classifier/summary reconstruction；普通 plan verification
在 report 构造被禁用时仍成立。没有发现需要修改旧 demand/origin 构造的缺口。

## 范围、门禁与发布

实际代码接入为一个新增 report owner 和既有 inspection 的可选方法。既有 plan
construction、demand carriers/checkers 和 Slice2–10 tests 均保持。Sole lifecycle/inventory
readers 更新为 production198/test456；其他 source/public/portable/grammar/SQL/provider
和历史合同只读。实际闭包为 A3/M5/D0，八个获准路径。

作者 self-review/Ponytail review 不称第三方审核。重启造成临时收据丢失时，保留已知
启动与终态，把缺失终态标为 observation loss；确认无存活进程后补齐必要检查，没有
重置预算。后续账本在仓库外持久目录 `~/.local/state/pietto/evidence/phase65-slice11/`。
第 4 个修正组后复查完整剩余 findings 与收敛。上限为 6 correction groups、4 本地
authoritative starts、1 initial commit，以及余额内至多 1 ordinary CI repair child。

最终内容冻结后要求正常 locked Python3.12/3.13 focused/compatibility、Ruff/format、
production/test Pyright、Python3.13 authoritative、generated/golden/package 全部通过。
实际 tested tree 封存后一次普通 commit/fast-forward push，自然 exact-head
push/main/attempt1 的两个 Python jobs 四项步骤成功才建立发布终态。

成功时 Phase64 COMPLETED，Phase65 ACTIVE，Slices1–11 PUBLISHED；Slice12 NEXT /
NOT IMPLEMENTED，Slices13–16 NOT IMPLEMENTED，N16 不变。没有开启 Slice12/13、
full source-map 产品、provider/target assessment、rebind、backend strategy、runtime
enforcement、SQL emission/execution、portable format 或公共 API/CLI。
