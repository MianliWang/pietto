# Phase 65 Slice 2 Minimal Selected Scan/Projection ProjectSQLPlan v1

## Authority and recovery

本交付沿用已发布 Phase65 Slice1 的 D65.01–D65.12 和 N16，不改变历史合同。
基线 commit 为 `3d89ebb45a59cee243e03a293f479f3011807f9f`，tree 为
`29dfc9b7be09a16336861ed497727de2fa21f75e`，parent 为
`d7af544dd4ce48891d5fe2596ab23e494f48d4ab`；自然 CI `34512999929`
为 push/main/attempt 1/success。

RECOVERY_R1 明确接纳未验证的输入 tree
`c68d036c885a5ed4fe7c7b38049d34b992894661`。H0 的零次 validator、修正、
commit/push 是上次报告；H1 中间活动和累计计数 UNKNOWN，未作历史合规认证。
R1 是此恢复点上的一次性前瞻授权：最多四个因果修正组、三个本地 authoritative
starts、一个普通初始 commit，及同闭包/剩余预算内至多一个自然 CI repair child。
采用当前草稿不表示认可其正确性。操作开始/结果记录保存在仓库外的
`~/.local/state/pietto/evidence/phase65-slice2-recovery-r1/`。
同一 R1 后续恢复接纳中间 tree `a1b1e6427b15d4600a361e8786311197c4fb32c3`；
其中另一次未归属 lifecycle 写入区间保持独立 UNKNOWN，不并入 H1，也不重置 R1。
已批准在既定语义和十一条路径内自主修复可审查的任务变更；候选 lifecycle 是
预期发布后状态，实际完成仍须下述本地门禁与自然 exact-head CI。

## Completed source authority correction

正常 explicit-module 路径是 parse -> `build_empty_project_semantic_result`
-> `build_project_completed_semantic_result`；CLI 的
`_project_semantic_boundary`、Query Block IR 和 private single-match wrapper
均消费此 completed 边界。既有链遗漏 connector validation：
`postgres.table(123)`、`mysql.table("")`、`unknown.table("rows")` 的单文件
analyzer 产生 `PIE-S2306`，Project completed 却报告 ok=True。

本次授权的行为修正只在 `project_completed_semantics.py` 接入既有
`type_source_connector_arguments(script)` 与 `check_source_connectors(script,
expression_value_types)`。它们继续拥有规则；不调用完整 analyzer，不复制 checker。
按完整 retained module tuple 顺序，每个原始 script 在 completed root 构造时
验证一次，覆盖所有 authored SourceDef；缺失 script 或不连续的 module/catalog
证据直接拒绝，不把部分扫描当成功。

原有 `_final_diagnostics` 和 operative-condition diagnostics 顺序、对象身份保留。
其后追加每个 module 的 argument-expression diagnostics，再追加该 module 的
connector diagnostics；不按 code/message/name 去重。single-match wrapper 复用
同一 roots，保留原诊断对象且不重验 source。ERROR 通过已有 ok 规则阻止 planning；
IR VERIFIED 仍只表示结构验证，允许保留 typed terminal。

UNKNOWN argument 保留表达式 ERROR 与已有 cascade suppression。合法 nonliteral
PostgreSQL 参数仍可语义成功，但没有静态值时 planning 为 typed unavailable。
PostgreSQL 空 Text literal 和合法空白 locator 原样保留；MySQL 的空字符串规则
仅由既有语义 checker 拥有。不评估 locator，不拆点、不 trim，不声明数据库可用性。
legacy-flat/package-root 与 public JSON schema 保持既有行为。

## Concrete private representation

正向域为 EXPLICIT_MODULES、exact completed.ok、exact VERIFIED Query Block IR
analysis bundle、显式同 snapshot TABLE/QUERY occurrence，及同 module 的一个
direct static source。真实 builder 的最小链为 `ProjectIRReusedEffectiveOutput`
上的 `RELATION_INPUT -> FINAL_PROJECTION`；source entry 自身只有 RELATION_INPUT。

`ProjectSQLPlan` 是闭合不可变结果，直接构造被拒绝；builder 在完整对应关系成立后
才发布。`ProjectSQLPlanUnavailable` 保留完整、有序、带 exact evidence/site 的
blockers；foreign owner/root 为 incoherent API input。完整 project ERROR 阻止
plan；语义成功后，只按 selected dependency closure 判断增量 planner 支持域。

一个 plan scope 内有一个 `ProjectSQLSourceBinding`、一个 `ProjectSQLSelectBlock`、
一个独立的 `ProjectSQLInputUse`。ref 按 domain 分开、局部 dense 编号，绑定 exact
scope，不承诺跨 snapshot 稳定。source descriptor 保留 defining logical module、
SourceDef、connector AST 和原始参数。input use 保留 exact upstream cross-relation
edge/dependency，区分 producer definition 和 use occurrence。

`ProjectSQLPort` 分别表示有序 source/input/export ports；`ProjectSQLProjection`
明确连接 source port -> input port -> canonical final export，并保留 exact
ProjectModuleSelectFact 与 reference。重命名不把 source-field identity 当最终
RELATION_OUTPUT identity。端口保存 upstream relational field occurrence，因此
其 exact type/nullability/provenance/property authority 不丢失、不重新求解。

Origins 区分 selected owner、source descriptor、input use、block、source/input ports、
projection、export、demand，并保留 value/type-proof/generated-structure role、
exact causative AST/evidence 和直接 antecedents。保留 parser 一基、半开 character
坐标；生成实体没有伪造 authored span 或 SQL offset。

Mandatory demands 为一个 `ProjectSQLSourceRealizationDemand`，以及每个可见
export 的 `ProjectSQLExportRepresentationDemand`，包括 exact subject、type、
effective nullability、field evidence 和 origin。它们不是 CapabilityFact，也不
表示 target support、lowerer implementation 或 runtime fulfillment。

独立 `project_sql_plan_verification.py` 检查所给 plan 与 exact roots、完整
supported shape、producer/use、所有有序 ports/projections/origins/demands；不调用
planner 重建答案。`project_sql_plan_inspection.py` 只消费 VERIFIED 结果并暴露完整
typed tuples；输入 ref 查询按 exact membership 返回所有对应项。inspection 不做
语义推断、名称解析、target assessment、SQL rendering 或 portable serialization。
进入 view 时重新检查所给 verification 的当前 plan witness，拒绝嫁接旧 positive
result 的内容；这只调用独立 plan verifier，不重建语义或计划。

Selected closure 采用迭代遍历；source schema 的唯一 label 仅作候选位置索引，
真正对应仍须 exact field-object identity，重复 projection use 不合并。port/origin/
demand 检查按实际库存线性遍历；既有 upstream graph analysis 的复杂度单独保留，
不宣称重算整个 Project reachability 为线性，也不添加 persistent cache。

Named/imported producer composition、LET/scalar/WHERE、JOIN、GROUP/GLOBAL/satisfying、
window/QUALIFY、DISTINCT/ORDER/LIMIT 和 set stages 均为 typed blockers。
它们分别归 Slices3–9；binding/report/source-map/target/portable/integrated assurance
仍归 Slices10–15；Slice16 audit-only。Slice2 仅建立 P01/P02/P07 的首个实际消费者。

## Acceptance and write purposes

| Boundary | Required evidence |
| --- | --- |
| Shared semantic rules | 三个原始 ERROR；arity/name/non-call/MySQL literal/UNKNOWN cascade 与既有语义 checker 一致 |
| Full module scan | 非 selected source、独立 module、重复名字/错误 occurrence、defining locations、import/reexport/root reuse |
| Valid static and unavailable static | TABLE/QUERY × postgres/mysql；空/空白/Unicode locator；合法 nonliteral PostgreSQL typed terminal |
| Selected closure | 原 project diagnostics 原样保留；无关 ERROR 阻止；无关有效 future stage 不阻止 |
| Identity and completeness | foreign roots/owner/source；missing/duplicate/swapped ports/use；source/final roles；projection/origin/demand omissions、extras、grafts |
| Verification and inspection | 不调用 builder/semantic resolver；empty demands 不 vacuous PASS；typed terminal 不洗成 concrete |
| Compatibility | 现有 completed/CLI/single-match/Query Block IR reader；Slice1 principal；sole lifecycle/inventory readers |
| Final gates | Python3.12/3.13 focused；Ruff/format/双 Pyright；authoritative3.13；generated/golden/package；exact tree + natural dual-Python CI |

写闭包最多 A5/M6/D0，十一条路径，无 contingency：

- A `src/pietto/_project/project_sql_plan.py`：闭合表示、selected construction、typed blockers。
- A `src/pietto/_project/project_sql_plan_verification.py`：独立验证。
- A `src/pietto/_project/project_sql_plan_inspection.py`：VERIFIED-only runtime view。
- A `docs/spec/phase65-slice2-minimal-selected-scan-projection-project-sql-plan-v1.md`：本合同。
- A `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py`：真实正向/terminal/mutation 证据。
- M `src/pietto/_project/project_completed_semantics.py`：唯一上游 source validation 接入。
- M `tests/test_semantic_source_connectors.py`：完整 shared-rule 与 completed-root 回归。
- M `docs/status.md`、`docs/roadmap.md`：仅本 Slice 的生命周期与下一 owner。
- M `tests/test_active_phase_lifecycle.py`：唯一 mutable lifecycle reader 迁移。
- M `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py`：唯一 inventory owner，production187->190/test446->447。

只有成功的普通 commit、fast-forward push 和自然 exact-head push/main/attempt1 CI
建立 Slice2 COMPLETED/PUBLISHED、Slice3 NEXT/NOT IMPLEMENTED；不开始 Slice3。
无 grammar/AST/public API/schema/SQL/backend/dependency/workflow/version/golden delta。
