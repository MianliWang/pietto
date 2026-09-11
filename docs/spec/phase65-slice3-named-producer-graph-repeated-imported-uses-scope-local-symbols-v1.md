# Phase65 Slice3 Named Producer Graph, Repeated/Imported Uses And Local Symbols v1

## Authority and support domain

基线 `adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b`，tree
`b349f9c50d6d3fc28f9cdb621d7ba7d7b1fe2bba`，parent
`3d89ebb45a59cee243e03a293f479f3011807f9f`；自然 CI `34556059755`
为 push/main/attempt1/success，两个 Python job 的四项必需步骤成功。
Slice2 与 RECOVERY_R1 已关闭；其历史不确定性不重开、不借用预算。
D65.01–D65.12、N16、EXPLICIT_MODULES、whole-project completed.ok、exact
VERIFIED Query Block IR 和显式同 snapshot TABLE/QUERY selection 保持。

本 Slice 独立上限为六个完整因果修正组、四次本地 authoritative starts、一个
ordinary initial commit，以及剩余预算内至多一个 ordinary CI repair child。
操作记录位于仓库外 `~/.local/state/pietto/evidence/phase65-slice3/`。
review 为 foreground author self-review；独立 verifier 指代码职责，不称第三方审核。

## Source-backed representation

真实 `source -> table p0 -> table p1 -> query result` 的直接投影链正向 entries
均为 ProjectIRReusedEffectiveOutput，非 source 的算子是 RELATION_INPUT、
FINAL_PROJECTION。逐层 rename/reorder/duplicate projection 必须使用 immediate
producer canonical outputs，不回跳 physical source。

真实 repeated UNION ALL depth12 的 p0–p12 有十三个 named definitions、二十四个
operand uses；另计 source、result 两个 wrapper definitions 和两条 wrapper edges。
p1–p12 为 ProjectIRCompletedSetOperationOutput，下游 result 是 replay
ProjectIRCompletedQueryBlockOutput。self-JOIN 则有两个实际 binding occurrences 和
两个 active input uses，不能用重复 SELECT 字段替代。历史 cross_relation_edges、
rebound/replay relation_input、SET operands、JOIN prefix correspondence 分别拥有
实际 active endpoints；本层只读这些证据，不改 Phase64。

一个私有 definition/input-binding seam 由真实 planner 消费：每个 reached owner
只分配一个 definition；每个 dependency 分配独立 input use、active IR edge、
resolved binding、既有 canonical origin path 和输入端口。Definition ref 定义逻辑
block context，SourceBinding/实际 SELECT block 引用同一 definition ref；SET/JOIN
只拥有 binding definition，不伪造 SELECT block。

Definitions 按上游 schedule 分配，uses 按 retained dependency/source order 分配。
输入端口显式连接 immediate producer export。所有 named stage exports 单独暴露；
plan.exports/inspection.exports 仅为 selected visible result。Source descriptor 保留
原 defining module、SourceDef 和 connector/argument AST。Import/reexport 保留 exact
ProjectResolvedModuleRelationSymbol、ProjectModuleOriginPath；按已存在 occurrence
坐标索引，不重新解析名字或构造 origin paths。

每次 input scope crossing 有 SOURCE_INPUT/NAMED_INPUT boundary reason。
Symbol 分为 RELATION_USE、FIELD_PORT namespaces，保留 owning definition/block
scope、局部序号、exact subject ref 和独立 label。Block-context lookup 只接受实际
成员 ref，拒绝跨 scope capture、同名异体及 role substitution。投影构造与 runtime
reader 都消费 context；没有 SQL alias spelling、case-fold/truncation 或跨 snapshot ID。

Binding origins 覆盖 definitions、source、uses、ports、boundaries、symbols；完整
plan 另保留实际 SELECT/projection/export origins。每个 source definition 保留一个
realization demand，每个 named exported stage value 保留 representation demand，
包括 intermediate exports。相同类型/locator 不合并 occurrence，也不证明 target 支持。

Binding verification/inspection 可以观察真实 JOIN/SET 的输入依赖，但不构造 SQL
operator body。Whole-plan 遇到 scalar/LET/WHERE、JOIN、GROUP/satisfying、window/
QUALIFY、DISTINCT/ORDER/LIMIT、SET 仍保留完整 typed blockers，没有部分 concrete
plan 或 VERIFIED whole-plan inspection。共享 definition 不保证 evaluation once。

采用迭代 traversal 和 invocation-local indexes，不展开 shared DAG；upstream
completion/IR analysis 成本单独记录。Verifier 检查所给 witness，不调用 planner 或
binding allocator 重建答案。Inspection 重验当前内容，不修复缺失事实。

## Acceptance and reader migration

| Invariant | Evidence |
| --- | --- |
| Named chains | TABLE/QUERY × postgres/mysql；多层 rename/reorder/duplicate；immediate canonical identities |
| Import identity | imported source、imported/reexported producer、共享定义/独立 binding uses、defining locations |
| Repeated graph | 真正 self-JOIN/SET operands/不同 consumer scopes；depth12 的 13 definitions/24 uses |
| Local context | 两 namespace、完整 labels、actual lookup、拒绝 capture/collision/foreign refs |
| Inventories | missing/extra/duplicated definitions、uses、ports、symbols、intermediate exports、origins/demands |
| Integrity | same-looking root/owner/port、alias graft、wrong producer、cycle、stale verification |
| Admission | whole-project ERROR 阻止；无关合法 unsupported sibling 不阻止；source validation 保持 |
| Typed terminals | 只移除 composition blocker；保留 transitive WHERE/operators；binding PASS 不等于 plan PASS |

Slice2 imported-source terminal test 迁移为正向；named-producer blocker test 移除
composition blocker，保留 transitive WHERE/operator evidence。Slice1 固定历史
principal 和已发布 Slice2 合同不改；其余 direct-scan controls 保持。Sole lifecycle/
inventory readers 负责状态和 production190/test448 的现行库存。

## Write and publication boundary

最多 A2/M8/D0：本合同、Slice3 focused test；三个既有 plan modules；Slice2 focused
测试；status、roadmap、sole lifecycle reader、sole inventory reader。没有新 production
module 或 contingency path。Upstream semantics/IR/source checker、CLI、grammar、
public exports/schema、dependencies/workflows/version、generated/goldens 只读。

完整 review、双 Python focused/direct compatibility、Ruff/format/双 Pyright、最终
完整 authoritative3.13、generated/golden/package 通过后，seal exact tree，ordinary
commit 和 fast-forward push；自然 exact-head push/main/attempt1 双 Python 必需步骤
成功才建立 Slices1–3 COMPLETED/PUBLISHED、Slice4 NEXT/NOT IMPLEMENTED。
Phase65 仍 ACTIVE，Slices5–16 NOT IMPLEMENTED。无 JOIN/SET SQL planning、literal
binding policy、target assessment、portable format、新 differential family 或执行。
