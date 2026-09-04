# Phase 63 Slice 13 Completed Project Semantic Result And Public Check Boundaries v1

## Decision And Live Authority

Slice 13 从已发布 commit
`0d1d66badc2cf901d35876b360a25a9c36a829b3`、tree
`01817712dd0cdbf7fd6ce7a1a3442dabf9bf637f` 开始。其 subject 是
`Complete Phase 63 final relation outputs`。自然 exact-head push run
`33845906404` 是 attempt 1；Python 3.12 与 Python 3.13 均为 success。

Phase 63 保持 `ACTIVE`。Slices 1–13 是 `COMPLETED / PUBLISHED`；Slice 14
是唯一 `NEXT / NOT IMPLEMENTED` owner；Slices 15–16 未实现。本 Slice 不开始
Slice 14。

## Closed Completed Result Domain

私有 `ProjectCompletedSemanticResult` 是以下封闭 union：

```text
ProjectConcreteCompletedSemanticResult
ProjectNonConcreteCompletedSemanticResult
```

positive construction 只属于 `EXPLICIT_MODULES`。`LEGACY_FLAT` 与
`PACKAGE_ROOT` 的 direct builder 调用形成 typed non-concrete mode terminal，
不被静默升级或重解释。CLI 对这两个 mode 继续沿用历史
`ProjectSemanticResult` 路径。

concrete result 以 object identity 保留原始 `ProjectSemanticResult`、精确
`ProjectPhase62VerificationResult`、`ProjectCompletion`、
`ProjectEffectiveOutputCompletion` 与最终 diagnostics。它不修改或替换
`ProjectSemanticResult.ok`；explicit-module 原始 result 的历史 posture 保持不变。

completed `.ok` 仅在以下条件同时成立时为 true：

1. 最终 diagnostics 没有 `Severity.ERROR`；
2. effective-output overlay 的每个 entry 都严格是
   `ProjectExistingEffectiveOutput` 或 `ProjectCompletedEffectiveOutput`。

任一 Slice-7 或 Slice-12 terminal 都使 completed result 失败。

## Exact Existing Construction Chain

builder 从一个精确原始 `ProjectSemanticResult` 开始，只编排已发布 builder：

```text
ProjectSemanticResult
-> project row keys
-> project Value FDs
-> Phase-61 Project plan and evaluation context
-> fresh base Project IR verification
-> grain origins and relational properties
-> relationships, conditions, match guarantees, paths, and uses
-> Phase-62 JOIN regions and multi-fact analysis
-> verify_project_phase62
-> build_project_completion
-> joined row filters
-> joined aggregations
-> joined window stages
-> joined QUALIFY results
-> build_project_effective_output_completion
-> ProjectConcreteCompletedSemanticResult
```

Project plan 从新的 snapshot-local
`ProjectIRAllocationState(scope=ProjectIRSnapshotScope())` 开始；JOIN region 只沿
该 plan 的 ending allocation 延续。Slice 13 不复制 row-key、FD、relationship、
JOIN、aggregate、window、QUALIFY、projection、ORDER 或 LIMIT 语义。

## Phase-61/62 Prerequisite Boundary

Phase-61/62 Project IR 与 Phase-62 verification 仅作为私有 semantic-completion
proof prerequisite。三者严格不同：

```text
private Phase-61/62 verification prerequisite
!= public Project IR result
!= Slice-14 Phase-63 unary-tail Project IR
```

completed result 不序列化或渲染 Project IR plan、node、use、slot、coordinate、
canonical bytes 或 property carrier。CLI 不返回 Project IR 对象。Slice 13 不调用
或实现 Slice-14 unary-tail composition，不创建 SQL、Arrow、executor 或 optimizer
行为。

## Root Continuity And Graft Rejection

一个私有 roots carrier 绑定精确连续链：

```text
original semantic result
-> exact VERIFIED Phase-62 root
-> exact completion
-> exact Slice-12 overlay
```

该 carrier 只接受原始 semantic result；verification、completion 与 overlay 都是
同一次构造中的 `init=False` derived roots，caller 不能逐项提供或替换。

verification 的 Project plan 必须保留原始 result 的同一个 semantic-fact set 与
attribution set。completion 必须保留同一个 verification 与 plan。overlay 必须
保留同一个 completion；其 joined-QUALIFY root 必须沿 Slice-10/9/8 chain 回闭到
该 completion。Slice-12 已建立的 final-field、relation-ORDER、terminal、replay
root 与 upstream membership checks 保持不弱化。

来自另一个 equal-looking project build 的 semantic root、verification、
completion、effective-output tuple、joined-QUALIFY set 或 diagnostic projection
都不能按 name、shape、type、hash 或 canonical bytes graft。构造只接受 object
identity 与完整 collection membership。

## Final Diagnostic Projection

最终 projection 先按原顺序保留
`ProjectSemanticResult.diagnostics`。随后按 effective-output overlay 的 canonical
owner order 访问每个 non-concrete entry。

每个 entry 已携带的 `Severity.ERROR` diagnostics 按其原顺序保留；不按 code、
message 或位置排序，也不做 content dedup。若同一个 `Diagnostic` object 已保留，
只跳过该 exact object identity。

projection 通过一个 closed typed visitor 显式访问 historical helper/window facts、
joined LET/filter/aggregate/window/QUALIFY carriers、no-JOIN scalar/WHERE/QUALIFY、
relation ORDER、LIMIT、local replay blocker 与 propagated upstream terminal。它不做
generic reflection、dataclass field walking、serialization discovery，也不重跑任何
semantic analysis。Slice-12 completion terminal 的 historical `base_entry` 只提供
root identity；若当前 joined/replay stage 已 supersede 其历史 deferral diagnostics，
该 identity edge 不被误当作 causal diagnostic edge。

若一个 non-concrete entry 自身没有 ERROR，exactly one fallback diagnostic 是：

```text
PIE-S2333 — Project relation semantic completion is unavailable: <relation>
```

它使用 authored `SourceDef`、`TableDef` 或 `QueryDef` 的精确 source span。message
只公开 authored relation name，不公开 terminal enum、Python carrier、object ID、
内部路径或 Project IR coordinate。entry 已保留精确 user-facing ERROR 时不生成
fallback。

因此每个 non-concrete completion 都有 public semantic ERROR boundary。dependency-
propagated terminal 若可达 upstream precise ERROR，保留同一个 Diagnostic object；
只有完整 causal graph 无 ERROR 时才按 owner order 获得自己的 `PIE-S2333`。

## CLI Project Check Boundary

`pietto check --project` 仍先直接调用
`build_empty_project_semantic_result(parse_result)`。parse error 继续在两个 semantic
builder 之前终止。

对于 `EXPLICIT_MODULES`：

- text mode 渲染 completed diagnostics；`not completed.ok` 时 exit 1；
- success bytes 保持 `Project check OK: .\nFiles checked: N\n`；
- JSON mode 把 completed diagnostics 传给现有 Project JSON v2 serializer；
- semantic failure 的 text/JSON 均 exit 1。

对于 `LEGACY_FLAT` 与 `PACKAGE_ROOT`，CLI 仍使用原始 semantic diagnostics 与
`ProjectSemanticResult.ok`，不会调用 completed builder。single-file `_run_check`
完全不变，Project Explain 也不进入 completed builder。

## Project JSON v2 Zero-Delta

`src/pietto/_project/json_v2.py` 保持 byte-for-byte unchanged。schema version 仍是
`2`，top-level key order 仍是：

```text
schema_version
command
mode
ok
project
inputs
diagnostics
cli_errors
result
```

serializer 继续从 parse result 与 supplied semantic diagnostics 得出 `ok`。由于
每个 non-concrete completed result 都投影 ERROR，JSON `ok` 与 completed `.ok`
一致。JSON 不增加 completion、effective outputs、owners、field identity、JOIN、
QUALIFY、Project IR、terminal reason 或 private diagnostic metadata。

## Historical And Public Compatibility

以下 authority 保持原对象与原语义：

- `ProjectSemanticResult` 及其 `.ok` property；
- explicit-module sidecar construction 与 `AUTHORED_JOIN_DEFERRED`；
- historical semantic row states、Slice-7 `ProjectCompletion` 与 Slice-12 overlay；
- `ProjectModuleRelationOutputFieldAttribution`；
- LEGACY_FLAT、PACKAGE_ROOT、single-file JSON v1、Project Explain；
- public Python API、SQL backends 与 Project JSON v2 schema。

new module 的 `__all__` 为空；没有新的 public export。

## Exact Changed-Path Closure

冻结 closure 恰为十个路径：

| State | Path |
| --- | --- |
| A | `src/pietto/_project/project_completed_semantics.py` |
| A | `docs/spec/phase63-slice13-completed-project-semantic-result-public-check-boundaries-v1.md` |
| A | `tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py` |
| M | `src/pietto/cli.py` |
| M | `docs/spec/project-cli-json-v2.md` |
| M | `docs/spec/diagnostics.md` |
| M | `docs/roadmap.md` |
| M | `docs/status.md` |
| M | `tests/test_active_phase_lifecycle.py` |
| M | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |

closure 是 `A3/M7/D0`。production inventory 是 `174 -> 175`；test inventory 是
`417 -> 418`。principal 不读取 mutable lifecycle documents，也不成为新的全仓库
inventory reader。没有 grammar、generated、golden、package、dependency 或 workflow
路径变化。

Focused historical compatibility 发现 Phase-54/55 的 schema-v2 CLI oracles 仍把
raw `ProjectSemanticResult.ok` 当作 final success authority。该断言已被 Slice 13
completed boundary 明确替代，因此按 bounded governance 加入七个 mechanical
historical-test closure paths：

```text
M tests/test_phase54_semantic_fact_preservation.py
M tests/test_phase54_module_qualified_nominal_declaration_catalogs.py
M tests/test_phase54_local_export_visibility_module_facades.py
M tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py
M tests/test_phase54_named_import_alias_binding_environments_collision_rules.py
M tests/test_phase54_schema_v2_explicit_module_carrier.py
M tests/test_phase55_slice2_explicit_package_activation_compatibility_and_immutable_package_carrier.py
```

core closure 仍是十路径 `A3/M7/D0`；mechanical expansion 是 `7/10`，累计 closure
是十七路径 `A3/M14/D0`。这些路径只更新 completed-success、final diagnostics 与
CLI exit/text expected oracles，不修改 Phase-54/55 production semantics、历史 sidecar
authority 或 JSON shape/privacy assertions。

## Assurance And Publication

principal 覆盖 join-free、joined、joined-to-no-JOIN downstream、GROUPED、GLOBAL、
window/QUALIFY completion；所有 final effective outputs 的 exact identity；foreign
semantic/verification/completion/overlay/entry/diagnostic graft rejection；precise ERROR
保留、identity-only dedup、`PIE-S2333` fallback 与 dependency propagation；explicit
text/JSON success/failure、parse gate；LEGACY_FLAT、PACKAGE_ROOT、single-file、Project
Explain、JSON v2 与 public/private boundaries。

最终 candidate 通过 focused compatibility、targeted Pyright、Ruff、format、
`git diff --check`、fresh root/privacy rereview 与 authoritative Python 3.13 validator
后，只允许一个普通 commit `Add Phase 63 completed project semantics`、一个 normal
fast-forward push，以及自然 exact-head CI attempt 1。禁止 amend、rebase、force
push、manual rerun、dispatch、tag、Release、signing 或 attestation。

## Slice 14 Handoff

成功 natural exact-head CI 后，Phase 63 Slices 1–13 是
`COMPLETED / PUBLISHED`。Phase 63 保持 `ACTIVE`；Slice 14 是
`NEXT / NOT IMPLEMENTED`，Slices 15–16 仍未实现。Slice 14 单独拥有 Phase-63
unary-tail Project IR、SQL/Arrow/executor/optimizer 后续边界；本 Slice 不开始它。
