# Phase 64 Slice 8 Row-Equivalence, DISTINCT And Quotient Grain Origin v1

## Gate 0 与补充产品裁决

本 Slice 基线 commit `66c0e08628834c88e0a68013d036e32baad24e56`，
tree `551d34398b90535bed1f91fa3656e26cc68c5cc2`，parent
`241be04da179969ddb1bd50381ee9ac58cea1641`。重新 fetch 后 local/cached/live
main 一致，0/0，index/worktree/untracked inventory 干净，无 active Git operation。
自然 CI `34253791709` 为 push/main/attempt 1/success；Python 3.12
`102154345228`、3.13 `102154345958` 的 validator/generated/golden/package 均成功。

首次前台审计在任何 repository edit 前按 USER_DECISION_REQUIRED 停止：
Float 字段没有 finite-only 证据，原 D07 未给出完整 NaN 等价规则。该 STOP 不是
failed implementation/validator；A0/M0/D0，所有预算消耗为 0。

用户随后明确补充 **D07-FLOAT-DEFERRED**：Phase-64 row-equivalence 暂不支持
Float 及现有解析权威解析到 Float 的别名；完整浮点等价归 Phase 72。
这是一项新的产品范围裁决，不追写为
[原 D07](phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md)
已经作过的决定。既有
[Phase-72 NaN/equality owner](phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md)
保持。D01–D06、D07 其余部分、D08、N=11、E01–E12 不变。

只检查最终 visible selected fields；nullable/non-null、literal/computed/aggregate/
window Float 均 ERROR，无 finite-only/GLOBAL/LIMIT/key 例外。不声称输入实际含 NaN。
隐藏或未选 Float 不触发此限制；原 projection/arithmetic/predicate/relationship/
aggregate/window/ORDER/count_distinct 不变。Any/Bytes/Json 同样不支持。
有限 Decimal 必须保留经现有校验器验证的精确 (p,s) 与原始类型根，缺失不猜测；
type identity 与 nullability 分离，不 widening，不新增 equality resolver/evaluator。

## 语义与当前消费路径

`select:` 保持；新增恰为 `select distinct:`，AST 以默认 None 的 clause 保留
DISTINCT token 的 exact span。set quantifiers 与 aggregate count_distinct 不变。
顺序为既有 ROW/JOIN、LET/WHERE、GROUP/satisfying、WINDOW/QUALIFY、
final visible projection、DISTINCT quotient、relation ORDER、LIMIT、completed output。

| Producer | Exact retaining root | Consumer / invalidation |
| --- | --- | --- |
| Grammar / AST | owner definition + DISTINCT occurrence/span | shared legacy availability and final-output completion |
| Existing type/alias resolution | original field TypeExpr + module resolution; canonical scalar and nominal path remain separate | private row-equivalence capability; changed type/field/root rebuilds evidence |
| Existing Decimal validator | exact retained TypeExpr and validated precision/scale | row-equivalence only; missing/unpropagated fails closed |
| Final projection | source-ordered canonical completed field tuple, unchanged RELATION_OUTPUT identities | equivalence and full-row uniqueness; no hidden field, smaller key or source winner |
| DISTINCT | exact owner/clause/visible tuple/equivalence/input domain | new DISTINCT_QUOTIENT origin in project_grain; GLOBAL retains stronger posture |
| ORDER | exact current selected source or existing strict FD proof | reject hidden representative selection; no ordering invented |
| Completion schedule | exact producer entries / replay / current JOIN inputs | new active quotient factor, upstream grain remains provenance |
| Legacy IR / combined IR | authored DISTINCT / retained completed root | existing typed or non-concrete rejection; combined integration stays Slice 10 |

新模块 project_row_equivalence 只拥有类型能力/证据，由 final-output 当前调用。
DISTINCT result/full-row witness/ORDER transfer 留在现有 project_final_outputs
owner，以共享 production constructor 的完整 root/source/domain 校验。第二新模块
预留 project_distinct.py 最终未使用；实际新 private module 为 1/2。
复用现有严格 FD closure、grain factor kernel 和 completion schedule，不新增 property
engine、cache、registry、生产 evaluator、database 或 optimizer。

计划 additive diagnostics：`PIE-S2339` unsupported DISTINCT visible-field equivalence，
`PIE-S2340` DISTINCT ORDER not determined by visible row。Gate-1 live code audit 确认
两码空闲；均 ERROR，保留 exact offending field/type/reason/location，不使用 PIE-S2337。

## Gate 1 exact path freeze

本表在首个 repo edit 前固定并保存到仓库外。生成器仅 `make generate-parser`；
只暂存 bytes 实际变化的生成文件。core 7，additional production 12/12，
new private modules 2/2，existing focused 8/8，historical/static 12/12。
contingency 激活需先记录直接原因；未用容量不允许新增或替换路径。

| State / category | Exact path |
| --- | --- |
| ACTIVE syntax | grammar/Pietto.g4 |
| ACTIVE syntax | src/pietto/ast_nodes.py |
| ACTIVE syntax | src/pietto/ast_builder.py |
| ACTIVE core | src/pietto/_project/project_final_outputs.py |
| ACTIVE core | src/pietto/_project/project_grain.py |
| ACTIVE direct reader | src/pietto/_flat_relational_admission.py |
| ACTIVE direct reader | src/pietto/ir/builder.py |
| ACTIVE direct reader | src/pietto/_project/module_semantic_fact_preservation.py |
| ACTIVE direct reader | src/pietto/_project/project_query_block_ir.py |
| ACTIVE direct reader | src/pietto/_project/project_query_block_ir_verification.py |
| ACTIVE new private | src/pietto/_project/project_row_equivalence.py |
| ACTIVE new private | src/pietto/_project/project_distinct.py |
| ACTIVE required | docs/spec/phase64-slice8-row-equivalence-distinct-quotient-grain-origin-v1.md |
| ACTIVE principal | tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py |
| ACTIVE lifecycle/guide | docs/status.md |
| ACTIVE lifecycle/guide | docs/roadmap.md |
| ACTIVE lifecycle/guide | docs/language.md |
| ACTIVE lifecycle/guide | docs/spec/diagnostics.md |
| ACTIVE lifecycle/guide | tests/test_active_phase_lifecycle.py |
| ACTIVE lifecycle/guide | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |
| CONTINGENCY generator | src/pietto/generated/Pietto.interp |
| CONTINGENCY generator | src/pietto/generated/Pietto.tokens |
| CONTINGENCY generator | src/pietto/generated/PiettoLexer.interp |
| CONTINGENCY generator | src/pietto/generated/PiettoLexer.py |
| CONTINGENCY generator | src/pietto/generated/PiettoLexer.tokens |
| CONTINGENCY generator | src/pietto/generated/PiettoParser.py |
| CONTINGENCY generator | src/pietto/generated/PiettoVisitor.py |
| CONTINGENCY generator | src/pietto/generated/__init__.py |
| CONTINGENCY core | src/pietto/_project/project_completed_semantics.py |
| CONTINGENCY core | src/pietto/_project/project_current_join_inputs.py |
| CONTINGENCY core | src/pietto/_project/project_current_joins.py |
| CONTINGENCY core | src/pietto/_project/project_ir_relational_properties.py |
| CONTINGENCY core | src/pietto/_project/project_multifact.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block.py |
| CONTINGENCY direct reader | src/pietto/_project/project_scalar_bindings.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_row_semantics.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_aggregation.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_qualify.py |
| CONTINGENCY direct reader | src/pietto/_project/row_expression_type_facts.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_inspection.py |
| CONTINGENCY focused | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py |
| CONTINGENCY focused | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py |
| CONTINGENCY focused | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py |
| CONTINGENCY focused | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py |
| CONTINGENCY focused | tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py |
| CONTINGENCY focused | tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py |
| CONTINGENCY focused | tests/test_compilation_boundary_qualify_admission.py |
| CONTINGENCY focused | tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py |
| CONTINGENCY historical/static | tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py |
| CONTINGENCY historical/static | tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py |
| CONTINGENCY historical/static | tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py |
| CONTINGENCY historical/static | tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py |
| CONTINGENCY historical/static | tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py |
| CONTINGENCY historical/static | tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py |
| CONTINGENCY historical/static | tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py |
| CONTINGENCY historical/static | tests/test_phase63_slice16_completion_audit_phase64_handoff.py |
| CONTINGENCY historical/static | tests/test_phase62_slice6_factorized_intrinsic_grain_basis_dependencies_optional_factors_global_grain.py |
| CONTINGENCY historical/static | tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py |
| CONTINGENCY historical/static | tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py |
| CONTINGENCY historical/static | tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py |

## 验证与交付边界

先真实 authored 正/负 minimal tests 与 early production/test Pyright，随后
覆盖 source/JOIN 各 kind、GROUPED/GLOBAL、window/QUALIFY、imports/reexports、
downstream replay/JOIN both roles/self-use、Decimal、Float、ORDER/LIMIT、
single-match 与 exact-object grafts。测试侧有界 BAG/NULL witness 验证 C08：
(1,NULL),(1,NULL),(2,NULL) -> 两个可见等价类，隐藏值差异不拆类；
predicate NULL equality 不改变，不调用生产 evaluator。

前台 semantic + engineering 与 Ponytail review，完整 findings 后修复并复查。
最终双 Python focused Slice-4–7/F01/F02、resource-aware loadfile broad、lifecycle/
inventory、whole-tree format/Ruff、两 Pyright、diff、native generated、golden、
installed-package/CLI smoke，再 authoritative
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`。
只验证 exact candidate，未知进程结果先恢复，不 unchanged luck rerun。

初始实现与本补充裁决不计 repair。起始 counters：
corrective batches 0/20，authoritative starts 0/4，initial commits 0/1，
natural-CI repair children 0/2。所有过程日志、每次 validator start/result、
exact tested/sealed tree 与 Git/CI receipts 保存在仓库外和 Git/CI。
review/validation 全部通过才 seal、rebind remote、stage exact tree、一次 ordinary
commit、fast-forward push、自然 exact-head push/main/attempt 1 双 Python CI。
无 subagent、amend、rebase、force、manual CI、tag/release/sign/attest/status-only commit。

成功自然 CI 才使 Phase 64 ACTIVE、Slices 1–8 COMPLETED/PUBLISHED、Slice 9
NEXT/NOT IMPLEMENTED、Slices 9–11 NOT IMPLEMENTED，E07 在补充支持域内完成，
E09 仅 Slice-8 部分完成；Float row-equivalence: DEFERRED -> Phase 72。

## Slice-9 handoff（不实现）

| Operation | Requires row equivalence | Float consequence |
| --- | --- | --- |
| SELECT DISTINCT | Yes | participating Float unsupported |
| UNION DISTINCT | Yes | same unsupported-domain result |
| INTERSECT ALL / DISTINCT | Yes | row matching required |
| EXCEPT ALL / DISTINCT | Yes | row matching required |
| UNION ALL | No | use own shape/type compatibility; no equality-based Float denial |

ALL 并不普遍免比较。set/non-SELECT construction 归 Slice 9；combined Project IR/
verification/inspection 归 Slice 10；completion/handoff 归 Slice 11；SQL planning/
lowering 归 Phase 65/66。本 Slice 不实现任何上述后续能力。

## Checkpoint 1

Baseline red 2 failed / 1 passed：两条 authored DISTINCT 在 parser 精确缺口失败，
普通 SELECT control 通过。初始实现启用 generator inventory contingency；实际
变更以 native generator bytes 为准。Counters 仍 0/20、0/4、0/1、0/2。

Early test Pyright 0 errors；production Pyright 发现两个直接原因。Corrective
batch 1：类型根座位应为 attribution._authority.type_source_resolutions，修正
final-output 调用。Batch 2：新的 base-factor variant 使旧 observer return type
不再闭合；激活冻结 project_query_block_ir_inspection.py contingency，先拆
JOIN wrapper 再检查旧两种 base，DISTINCT 保持 TypeError negative boundary。
两项均无新公开/观察格式。Counters repairs 2/20，validators 0/4。

扩展 matrix 104 passed / 3 failed；测试把 region.final_properties.relational
误写为 region.properties。Corrective batch 3 修正 principal 的精确 property
访问。Early test Pyright 同时要求对 terminal/blocker 显式窄化；batch 4 增加
真实闭合 variant 断言，不改变生产。Repairs 4/20，validators 0/4。

组合 matrix 123 passed / 2 failed：DISTINCT 识别 completed upstream LIMIT，
但遗漏 ProjectExistingEffectiveOutput 的真实 LIMIT operator。Corrective batch 5
在 final-output adapter 同样要求 exact upstream owner clause、合法 LIMIT 0/1、
existing logical LIMIT at fragment root；保留该 producer 为 provenance。
不能借 DISTINCT 自己的后置 LIMIT；repairs 5/20，validators 0/4。

## Foreground complete finding set

主代理按 semantic + engineering / Ponytail review 全量审阅 candidate。冻结三个
material finding；10-review-red.log 为 4 failed / 4 passed：
- Corrective batch 6：GROUPED DISTINCT 下游 input context 仍检查最终 GROUPED，
  应消费 exact distinct.input_domain 的真实分组前提，最终 active grain 仍商域。
- Batch 7：field_def 能替换为同 schema 的另一 Decimal 字段，而 source expression
  未变。DISTINCT 要额外验证最终字段的 exact pre-projection schema/source type，
  既用于构造前检查，也用于 completed constructor 的 graft 拒绝。
- Batch 8：ORDER proof tuple 可被删除。验证完整 item 序列与 exact source/FD-index/
  strict-proof roots；重复使用同一 FD kernel，不创造第二引擎。
Ponytail finding：row-equivalence.same_type 无当前 production caller，只有测试，
属于不必要的提前比较 API。删除它，参数 mismatch 改由真实 field/source graft
反例验证，保留 exact parameter/nominal facts。此删除并入 batch 7。
全部 repair 只涉及冻结的 final outputs、新 equivalence module 与 principal；
repairs 8/20，validators 0/4，publication/CI children 均 0。

Fresh rereview principal 133 passed。Test Pyright 发现 UNKNOWN-grain witness
的 union 未显式窄化；corrective batch 9 仅在 principal 断言其实际
ProjectIRProvidedIntrinsicGrain variant。Repairs 9/20，validators 0/4。

Entrypoint/negative matrix 150 passed / 1 failed：测试误用 where: block，
现有 surface 为 where expression。Corrective batch 10 仅修正 principal。
Oracle review 同时发现 nullable UNIQUE 例子的非空重复值违反输入契约；
batch 11 将 mandatory no-key counterexample 与 nullable-key/NULL 反例分开，
保留 score=10/20 无 winner 的证明目的。Repairs 11/20，validators 0/4。

Rereview producer-root counterexamples 为 3 failed：最终输出的拒绝无法阻止单独
构造带 object root、伪造 GLOBAL 或缺失 ORDER proof 的 DISTINCT producer。
Corrective batch 12 将该 producer/witness/unsupported variants 并回既有 final
owner，提取并复用其原有 exact projection-domain 验证；生产者自身同时执行
字段来源、cardinality 与 ORDER closure。删除未发布的 project_distinct.py，
保留唯一新模块 row-equivalence。Gate-1 第二模块预留未使用，不增加路径。
Inventory 185 production / 438 tests；repairs 12/20，validators 0/4。

Affected broad loadfile/4 workers：1217 passed、1 failed、11 acquisition errors。
激活冻结 focused test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py：
旧断言禁止读取 ProjectIRLogicalOperatorKind，误把 Slice-8 对 exact historical
LIMIT 的只读证明当作 IR allocation。Corrective batch 13 以 AST constructor-call
检查保留 no logical-IR construction，不禁止读取既有 typed enum；其余旧行为不改。
11 errors 来自同一 installed-wheel acquisition 的 uv cache lock：只读 sandbox 无法
在 /home/mianliwang/.cache/uv 写临时锁，standalone offline build 重现 os error 30。
继续使用原 populated locked cache，以已授权的 sandbox capability 运行验证；
不换空缓存、不改 dependency/lockfile/fixtures。不是产品失败或 validator start。
Counters repairs 13/20、validators 0/4，全部失败日志保留。

## Final foreground rereview 与 validation handoff

主代理 fresh rereview 已关闭全部 findings；未运行 subagent。受影响 broad
Phase-62/63/64 40 files 以 resource-aware loadfile/3 workers 得到 1229 passed，
包含未更改的历史 differential manifests、canonical bytes 与 installed-wheel
隔离控制。Principal 当前 155 cases；sole lifecycle/inventory 101 passed。
后续 final checks/authoritative run 绑定最终 Git tree，具体结果保留仓库外 ledger；
本文不预写未知最终 commit、CI/run/job identity。

| Review question | Answer / current evidence |
| --- | --- |
| Final visible fields / C08? | exact completed fields tuple；hidden Float、window/QUALIFY、multi-hop JOIN fields 被真实 principal 排除，有界 NULL/BAG oracle 3 -> 2 classes |
| NULL equality confined? | full-row witness 的 nulls_equal；nullable predicate typing、nullability 与全部旧 predicate code 保持 |
| Decimal evidence exact? | exact selected source field/type root + existing module alias resolution + existing Decimal validator；缺失、无传播、无效、替换参数来源均拒绝 |
| Unsupported predicate equality inheritance? | Any/Bytes/Json 与 D07-FLOAT-DEFERRED 有独立 typed capability failure，三模式 ERROR；不借 predicate/key/ordering Python equality |
| Representative winner? | 不评估、不选输入行；商域对象只保留 operator/field/type/input provenance |
| Nominal quotient distinct from grouping? | DISTINCT_QUOTIENT + DISTINCT_DOMAIN；真实 grouping 只作前置 property context，最终 active factor 为 quotient |
| Total <= 1 / GLOBAL? | DISTINCT 不给 right-match proof；自己的后置 LIMIT 有独立 exact LIMIT root；GLOBAL/真实输入 LIMIT 0/1 保持 stronger posture；两 GLOBAL 的 FULL UNKNOWN 正例建立新商域 |
| Hidden ORDER representative? | selected exact source 或现有 strict FD closure；非空重复 customer_id/不同 score 以及 nullable UNIQUE/NULL 对照均失败，原始字段可见性不扩张 |
| Grafts / identity closure? | producer 与 completed output 都验证 exact root/fields/type source/input domain/ORDER proof；derived equivalence/origin/uniqueness init=False；foreign overlays/replay/input roles 无法替换 |
| Composition? | all JOIN kinds、historical/refined INNER/LEFT、GROUPED/GLOBAL/window/QUALIFY、both roles/self-use、replay、import/reexport；下游保留 quotient active factors |
| Later slices / SQL? | set bodies仍 typed unavailable，旧 IR 不能漏掉 DISTINCT，combined IR/inspection 明确拒绝；不增加 SQL lowering 或 Slice-9 semantics |
| Extra engine / dead abstraction? | 一个新 private type-capability module；复用 existing Decimal validation、type resolution、FD closure、grain kernel 和 completion；删除无生产 caller 的 comparison helper 和多余新 result module |

工程审查还确认：无 dependency/lock/workflow/validator/package-version/public JSON
schema/SQL-renderer/golden-content 变更。生成文件仅 native generator 改变的
Pietto.interp 与 PiettoParser.py；其余六个 tracked generated files 未改 bytes。
实际 contingent activations 为 production observer negative adapter 1、focused
historical no-allocation reader 1；historical/static reservations 0。
本文件路径表保留原 Gate-1 reservations；第二 new module 未使用。

最终验证前累计：root-cause corrective batches 13/20，authoritative validators
0/4，ordinary initial commits 0/1，natural-CI repair children 0/2。
后续只执行已授权的 final validation / seal / publication，任何失败保留原 evidence
并沿相同预算处理；不做 unchanged failed-candidate lucky rerun。
