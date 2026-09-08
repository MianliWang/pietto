# Phase 64 Slice 5 CROSS RIGHT FULL Output Shapes Null Extension And Property Transfer v1

## Gate 0 与范围

Slice 5 从唯一 live baseline
`32632ea8dd5057034d2b5add861c1d2850ae5dee` 开始，tree 为
`82bd4551d8101747a68b98becbbed4c455630906`，parent 为 Slice-4 terminal
`dc194d3932656af7d41b1fd7bcabb5c4f7c59c03`，subject 为
`Bump ruff from 0.16.4 to 0.16.6`。本地 clean `main` 精确停在 parent，且
`origin/main` 与 live remote 已是 baseline；执行一次 `ff-only` 同步后，
`HEAD == main == origin/main == live remote main`。index、worktree 与 untracked
inventory 均为空，无 active Git operation，`NUL` absent，Ruff 0.16.6 与
`uv.lock` 保留。

自然 CI `34194052736` 为该 baseline 的 `push/main/attempt 1/success`。
Python 3.12 job `101957837087` 与 Python 3.13 job `101957836902` 均成功，
且各自的 validator、generated、golden 与 installed-package 步骤全部成功。

本 Slice 只交付 D02/D03、M5、C03/C04/C10 下的 direct-binary `CROSS`、
`RIGHT`、`FULL`：消费 Slice-4 已有 named/effective inputs，产生完整 left-then-right
row shape、BAG/TRUE-only matching 所需的 kind authority、正确的双侧 null-extension、
sound property/grain transfer、现有 SELECT tail、canonical completed output 与
EXPLICIT_MODULES project check。D01–D08、N=11 与 E01–E12 不变。

`SEMI`/`ANTI`、single-match、`DISTINCT`、set operations、non-SELECT output、
combined current IR/verification/inspection、SQL、execution 与 optimizer 均不在本
Slice。Phase 64 保持 ACTIVE；只有本 Slice 的 natural exact-head CI 成功才建立
Slice 5 COMPLETED/PUBLISHED 与 Slice 6 NEXT/NOT IMPLEMENTED。

## 构造审计与 producer/root/consumer 矩阵

Slice-4 的 `ProjectCurrentBinaryJoin`、`ProjectCurrentJoinRegion`、现有 completion
schedule 与 owner-local tail 是唯一 current-operation pipeline。Slice-3 的
`ProjectJoinCondition` 已保留每个 authored use；M5 的 `expression`、`scope`、
`base_conditions` 均为空且可 READY，所以 CROSS 复用这项“无匹配条件”的权威，
不创建字面量 TRUE、base match 或 relationship discovery。

RIGHT/FULL 的左输入是 operator 前的整个 accumulated row。输出字段仍按完整 left
后接 right 排列；当前 operator 的 nulling ref 追加到被补空一侧的既有有序 nulling
provenance，绝不覆盖旧记录。后续 ON 从 `ProjectCurrentPreMatchInputs` 读取该完整
有效 nullability。

属性转换复用现有 output image、key/FD frontier、grain dependency 与 current tail
kernel。forward at-most-one 只来自 exact applicable relationship/refinement bound 或
右输入 GLOBAL；reverse whole-left at-most-one 还要求 qualifying source slice 是当前
accumulated-left 的 exact key，或整个左输入本来就是 GLOBAL。CROSS 不产生 predicate
equality/null-rejection/relationship evidence。被 null-extend 一侧的 key/FD 只保留
sound LAX 形态；outer match evidence不成为 unconditional cross-side FD。

两个 GLOBAL one-row 输入的 `FULL ... ON false` 可能有两行。其 combined active
factor tuple 为空时使用既有 `ProjectGrainBasisState.UNKNOWN` 作为明确的 proof
unavailability，而不是 `GLOBAL`。普通 SELECT 仍合法；若后续 aggregate safety 需要
该不可用 grain，现有 tail 必须返回 typed non-concrete 结果，不得 traceback 或伪造
aggregate permission。

| Producer | 精确 root / membership | Consumer 与 rebuild trigger | 非 concrete / foreign counterexample |
| --- | --- | --- | --- |
| Authored kind 与 M1–M5 facts | exact `ProjectJoinUseIdentity`、ledger use、可选 ON、VIA 与 base/refinement roots | `ProjectCurrentJoinRegion`；输入 root 改变时仍经 Slice-3 rebuild | CROSS 携带 ON/VIA、多跳新 kind、foreign condition/use 均拒绝 |
| Available named/effective inputs | exact dependency、producer entry/output、binding role、ordered fields 与 materialized properties | current binary inputs；上游 completed output 改变时重建 | stale/equal-looking field/property/dependency 或 unavailable upstream 不能借用 |
| Accumulated row | exact prior prefix output/properties/origins/allocation | RIGHT/FULL whole-left nulling 与下一 condition environment | 只 null 某个 FROM binding、覆盖旧 nulling、交换左右角色均拒绝 |
| Binary row/property result | exact node、two slots/uses、kind、condition absence/presence、left-then-right fields | scalar/binding/row semantics、multifact 与 existing tail | wrong side/use/field/allocation、predicate-derived CROSS fact、outer unconditional FD 均拒绝 |
| Grain authority | exact input grains、introduction uses、ordered side nulling、directional bounds | multifact/aggregate safety 与 downstream current JOIN | empty FULL factor tuple 不证明 GLOBAL；source-entity reverse bound不证明 whole-left bound |
| Final completion/admission | existing schedule、operative conditions、input scopes、current regions/tails 与 owner-held helper diagnostics | canonical output、downstream replay/JOIN 与 real project check | blocked owner零 allocation；unrelated same-code diagnostic保留；combined IR仍 typed unsupported |

## Gate 1 精确 changed-path freeze

以下清单在首个 production/test 编辑前冻结。ACTIVE 是初始实现 owner；CONTINGENCY
只可在本文件先记录直接原因后变更。未使用容量不授权任何未列路径。

### Core production paths

| State | Path | Direct purpose |
| --- | --- | --- |
| ACTIVE | src/pietto/_project/project_current_joins.py | 唯一 current binary/region owner；kind、whole-left/right nulling 与 property transfer |
| ACTIVE | src/pietto/_project/project_current_join_inputs.py | 后续 condition 的完整双侧累计 nullability/nulling replay |
| CONTINGENCY | src/pietto/_project/project_join_conditions.py | 只在现有 M5/direct relationship fact 需要窄 membership 补强时使用 |
| ACTIVE | src/pietto/_project/project_ir_joins.py | 复用并窄扩展 grain image kernel 的 left/right nulling 与 empty-state 参数 |
| ACTIVE | src/pietto/_project/project_ir_relational_properties.py | 允许 exact provided grain 保留既有 UNKNOWN proof-unavailability state |
| CONTINGENCY | src/pietto/_project/project_grain.py | 只在既有 witness/origin identity 无法准确表达新 transfer 时使用 |
| CONTINGENCY | src/pietto/_project/project_relationship_uses.py | 只做 direct-kind exact role/relationship evidence compatibility；无新 resolver |
| ACTIVE | src/pietto/_project/project_final_outputs.py | scheduled operation selection、current region completion 与精确 diagnostic retirement |
| CONTINGENCY | src/pietto/_project/project_completed_semantics.py | 只处理新增 closed terminal/diagnostic direct reader |

### Additional existing production reservations (10/12)

| State | Path | Direct purpose |
| --- | --- | --- |
| CONTINGENCY | src/pietto/_flat_relational_admission.py | 现有 kind-specific temporary diagnostic producer；成功时按 object identity retirement |
| CONTINGENCY | src/pietto/_project/project_query_block.py | current row-source sum 与 final output membership direct reader |
| CONTINGENCY | src/pietto/_project/project_scalar_bindings.py | accumulated hidden/visible binding introduction reader |
| CONTINGENCY | src/pietto/_project/project_joined_row_semantics.py | 双侧有效 nullability、nulling provenance 与 property bridge reader |
| CONTINGENCY | src/pietto/_project/project_joined_row_filter.py | owner-local WHERE preservation reader |
| ACTIVE | src/pietto/_project/project_joined_aggregation.py | UNKNOWN grain 的 typed aggregate-safety terminal；普通 tail 保持 concrete |
| CONTINGENCY | src/pietto/_project/project_joined_qualify.py | shared owner-local aggregate/window/QUALIFY tail dispatch |
| CONTINGENCY | src/pietto/_project/project_multifact.py | current grain candidate/exposure reader；不得把未知空 tuple 当 GLOBAL |
| CONTINGENCY | src/pietto/_project/project_query_block_ir.py | Slice-10 前继续只发布 CURRENT_JOIN_COMPOSITION_UNSUPPORTED |
| CONTINGENCY | src/pietto/_project/project_query_block_ir_verification.py | combined current IR negative-only verification compatibility |

不预留新 production module：现有 current owner 与 kernel 已能表达所需边界。

### Tests, guides and lifecycle

| State / category | Path | Direct purpose |
| --- | --- | --- |
| ACTIVE required | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py | real source vertical path、BAG/NULL/property/grain/identity/failure matrix |
| CONTINGENCY new focused 1 | tests/test_phase64_slice5_outer_join_authority_and_failures.py | principal 超出可维护规模时才分出 root/failure cases |
| CONTINGENCY new focused 2 | tests/test_phase64_slice5_outer_join_tail_and_entrypoints.py | principal 超出可维护规模时才分出 tail/entrypoint cases |
| ACTIVE existing focused 1 | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py | 保留 INNER/LEFT；转移 RIGHT 临时拒绝与扩展 downstream controls |
| ACTIVE existing focused 2 | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py | 保留 condition laws；转移三种新 kind 的 operation admission |
| ACTIVE existing focused 3 | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py | 保留 syntax/entrypoint negatives；更新 explicit-module operation owner |
| CONTINGENCY existing focused 4 | tests/test_phase62_slice11_project_ir_binary_join_region_multi_input_topology_null_extension_property_transfer.py | 历史 INNER/LEFT transfer contract兼容 |
| CONTINGENCY existing focused 5 | tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py | UNKNOWN grain aggregate terminal reader compatibility |
| ACTIVE guide | docs/status.md | prospective Slice-5 publication / Slice-6 NEXT |
| ACTIVE guide | docs/roadmap.md | E02 closure与 Slice-10 combined-IR deferral |
| ACTIVE guide | docs/language.md | CROSS/RIGHT/FULL check semantics与 retained entrypoint boundaries |
| CONTINGENCY guide | docs/project-package.md | project check / Explain boundary only if direct text requires update |
| ACTIVE guide | docs/spec/diagnostics.md | 精确临时 admission retirement与 grain-unavailable terminal |
| ACTIVE lifecycle | tests/test_active_phase_lifecycle.py | sole mutable lifecycle reader |
| ACTIVE inventory | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py | sole whole-repository Python inventory owner，test Python 434 -> 435 |

### Historical/static-reader contingency reservations (12/12)

| Path | Exact compatibility purpose |
| --- | --- |
| tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py | live additive enum/owner claims must remain historical-or-subset |
| tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py | historical INNER/LEFT readiness remains immutable |
| tests/test_phase62_slice6_factorized_intrinsic_grain_basis_dependencies_optional_factors_global_grain.py | historical provided concrete grain domain versus additive current UNKNOWN |
| tests/test_phase62_slice7_existing_operator_key_fd_grain_transfer_grain_comparison.py | historical existing-operator property behavior |
| tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py | current unknown-grain consumer compatibility |
| tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py | historical INNER/LEFT oracle support boundary |
| tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py | preserve historical differential bytes and observations |
| tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py | additive dual-side nulling provenance reader |
| tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py | canonical final-output/tail reader compatibility |
| tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py | current combined IR stays negative |
| tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py | observer bytes remain unchanged for historical roots |
| tests/test_phase63_slice16_completion_audit_phase64_handoff.py | retained-later claims bind immutable handoff authority |

No grammar/AST/generated/golden、dependency/lockfile、workflow、validator、version、
public schema/API、SQL 或 inspection-format path 可变更。

## Checkpoints、review 与 accounting

先用 real authored sources 建立 baseline red：conditionless CROSS、最小 RIGHT/FULL
以及旧 INNER/LEFT/refinement green controls。随后依次闭合 accumulated-prefix 双侧
nulling/property/grain，再覆盖 completed inputs、existing tail、downstream replay/JOIN、
module/CLI/negative entrypoints 与 identity/failure cases。测试 side 使用独立有限 BAG
reference，不增加 production evaluator 或数据库依赖。

最终 review 同时覆盖 specification 与 engineering-quality 两条轴，重点检查 whole-left
角色、hidden prefix、双侧历史 nulling、directional proof scope、FULL/GLOBAL degeneracy、
stale roots、exact diagnostic retirement 与 old-root byte compatibility。前台串行运行
focused Python 3.12/3.13、affected regressions、format/Ruff、production/test Pyright、
diff、native generated/golden/package gates，再启动 authoritative validator：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

Fresh counters：corrective batches 0/20；authoritative validator starts 0/4；
ordinary initial publication commits 0/1；natural-CI repair children 0/2。
初始计划实现不计 repair。所有 failed evidence 保留于仓库外；unchanged failed
authoritative candidate 不重跑。

最终 reviewed/validated tree 才可 seal。随后重新绑定 remote、精确暂存 sealed paths、
创建一个 ordinary non-amend commit、normal fast-forward push，并只观察 natural
`push/main/attempt 1` CI。不得 amend、rebase、force-push、squash、rerun、dispatch、
tag/Release、sign/attest 或追加 status-only commit。

## Checkpoint evidence 与 corrective accounting

Baseline principal 得到预期的 3 个新 kind failure 与 3 个旧 control pass；CROSS、
RIGHT、FULL 均停在其精确 `PIE-S2334` 临时 availability diagnostic。第一轮 current
binary、调度与 grain transfer 实现后，production/test Pyright 均通过，operation
已完成，但 focused test 得到 2 failed / 4 passed。原因是 principal 把 fixture 中原本
声明为 nullable 的 `key`、`allow_any` 误写为 NON_NULL；只有每侧 `id` 可隔离验证本
operator 的新增 null-extension。Corrective batch 1 只修正该独立测试 oracle，生产
实现不变。Counters：repairs 1/20，validators 0/4，commits 0/1，CI children 0/2。

扩展 C10/nulling/property/grain 矩阵得到 16 passed、5 failed。冻结两个独立
root cause：batch 2 修复 outer nulling 重新映射后的 carried left grain factor；
`_localized_input_factors` 必须沿 exact `source_factor` 与原 introduction use 找到
final universe member，而不能误要求当前 left input-slot use。为此在变更前激活已
预列的 `src/pietto/_project/project_multifact.py` contingency。Batch 3 允许 UNKNOWN
provided grain 保留来自两个 GLOBAL input 的完整 inactive factor universe 与既有
dependencies；UNKNOWN 只禁止伪造 active basis。测试同步检查 retained provenance，
不把空 active tuple 当作空 provenance。Counters：repairs 3/20，validators 0/4。

首次 batch-2 修补后同一 5 个用例仍失败：input candidate 已能定位，但同一
`ProjectCurrentMultiFactRegion` 中 intermediate `JOIN_OUTPUT` candidate 仍把旧 active
factor tuple 直接放入 final universe。完成同一 root-cause batch：沿 exact nested
`source_factor` chain 定位，并让每个非 final intermediate output 先投影到 final grain
universe。另一个独立 fixture cause 计 batch 4：最初 FULL/GLOBAL 用例使用历史
aggregate output，而该 output 的 module lineage 按既有契约仍为 deferred；改为两个
经 Slice-4 current JOIN 完成的 GLOBAL named results，仍精确覆盖“双 GLOBAL + false
FULL”反例。Counters：repairs 4/20，validators 0/4。

新增 UNKNOWN-grain aggregate consumer red witness 首次 collection 被 principal
重构遗留的单独三引号阻断。Corrective batch 5 删除该 stray delimiter；这是测试
语法缺陷，尚未形成 production verdict，也不是 validator start。Counters：
repairs 5/20，validators 0/4。

修正后的 red witness 精确到 production boundary：UNKNOWN grain 进入 aggregate
consumer 时在 `ProjectFactContextualGrain` traceback，而非发布 closed terminal。
Corrective batch 6 在现有 joined-aggregation owner 增加 private
`INTRINSIC_GRAIN_NON_CONCRETE` 原因，绑定 exact final UNKNOWN grain；它保留已完成的
operation/current region，阻止 aggregate namespace 与伪造 GLOBAL/permission，最终
仍由既有 completed-result fallback diagnostic 公开。Counters：repairs 6/20，
validators 0/4。

Prospective lifecycle/inventory run 得到 100 passed、1 failed。Corrective batch 7
修正 sole lifecycle reader 中遗漏的一处 current-status evidence：它仍要求
“Phase 64 Slice 5 NEXT”；现改为 Slice 6 NEXT。Immutable historical contracts 与
历史 Slice-5 文本不变。Counters：repairs 7/20，validators 0/4。

Fresh complete review 的 material finding 由真实
`FULL(two GLOBAL, false) -> replay -> CROSS` 左/右角色 witness 复现：两条 downstream
grain 都错误变成 FACTORIZED。Corrective batch 8 让 UNKNOWN 在任一 input UNKNOWN 时
沿共享 `_grain` 传播，同时保留另一侧已知 active factors 作为不完整 provenance；
`ProjectCurrentMultiFactRegion` 不把 UNKNOWN input/output 的这些 partial factors 登记为
完整 actual-grain candidate。普通 row/tail 仍可用，aggregate consumer 继续命中 batch-6
typed terminal。Counters：repairs 8/20，validators 0/4。

全树 Ruff format check 在两处已计划迁移的 Slice-2/3 test assertion 上报告机械
reformat；620 个文件已格式化。该步骤不改变 oracle 或 production，属于 approved
change 的 derived formatting，不计 root-cause repair。失败输出保留后对两条路径运行
Ruff formatter。

Final test Pyright 报告 4 errors，冻结为三个独立 test-narrowing cause。Batch 9
在两处 ON witness 先断言 exact non-None `JoinOnClause`；batch 10 在 completed
window/QUALIFY input witness 断言 exact `ProjectConcreteJoinedQualify` root；batch 11
在 changed-input rebuild witness 断言 exact `ProjectJoinConditionCompletion`。只改
principal，不增加 cast/ignore 或放宽类型配置。Counters：repairs 11/20，validators
0/4。

## Final candidate review 与 pre-validator evidence

Foreground substantive review 覆盖 specification 与 engineering-quality 两轴：
direct-binary authored role、whole accumulated-left hidden fields、双侧有序 nulling、
condition/base/refinement membership、CROSS 无条件事实、directional bound scope、
key/FD strength、nested factor identity、UNKNOWN propagation、aggregate terminal、
schedule/cycle/diagnostic retirement、completed-input/tail reverse consumers，以及
Slice-10 negative boundary。Batch-8 finding已由 red witness 修复并重新审查；无 material
finding remain。Ponytail FULL/ponytail-review 直接用于当前 diff；未运行独立 review
agent/interface。结论为 `Lean already. Ship.`：没有可删除的第二 resolver、property
engine、module、dependency、retry/fixed-point 或 later-Slice scaffold。

Principal 为 70 passed。Slice-2–5 principals 加 F01/F02 在 Python 3.13 与 3.12
各 397 passed。最终 resource-aware `-n 5 --dist=loadfile` affected regression 为
907 passed，覆盖 Phase-62/63 JOIN、key/FD/grain/multifact、tail/completion、private
observer 与 CLI；历史 differential manifests 未变。Lifecycle/inventory 为 101
passed。Whole-tree format 为 622 files，Ruff、production/test Pyright 与 diff check
均通过。Native generated gate 验证 8 个 tracked files byte-for-byte；golden audit
验证 39 fixtures；installed-package/CLI smoke 通过。

实际 changed-path closure 为 A2/M16/D0，共 18 paths。Production mutations 为七个
ACTIVE owner：`project_current_join_inputs.py`、`project_current_joins.py`、
`project_final_outputs.py`、`project_ir_joins.py`、
`project_ir_relational_properties.py`、`project_joined_aggregation.py`，以及已在 batch 2
前激活的唯一 production contingency `project_multifact.py`。三个 existing focused
tests 与四个 guides、sole lifecycle/inventory readers 被使用；无新 production module、
optional focused test 或 historical/static-reader contingency 被激活。

Current accounting：corrective batches 11/20；authoritative validator starts 0/4；
ordinary initial publication commits 0/1；natural-CI repair children 0/2。所有 red、
failure 与 first-static logs 保存在 Slice-5 外部 evidence directory。Authoritative
validator、sealed tree、commit 与 natural CI 结果只记录为后续 Git/run evidence，本文
不预写未知 identity。

Slice 6 可复用 exact effective-input scopes、operative conditions（含 M5 无表达式
authority）、current binary/region、双侧 field/nulling/grain images 与 existing
owner-local tail。Slice 6 必须另行实现 SEMI/ANTI 的 left-only output shape；本 Slice
没有发布右字段丢弃或 existence semantics。Slice 10 仍拥有 combined current IR、
verification/invalidation、inspection/pure boundary 与最终
`EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED` closure；E05/E10 与全部 E01–E12 未声明闭合。
