# Phase 64 Slice 9 Set Operations, Explicit ALL/DISTINCT And Output Identity v1

## Gate 0 与当前裁决

基线 main / commit `73fcb2bcdbe27775fc3bf9500df8d68006a62578`，
tree `8c955e8754f53311160b25c22dd571267777177c`，parent
`66c0e08628834c88e0a68013d036e32baad24e56`，subject
`Add Phase 64 DISTINCT semantics`。重新 fetch 后 local/cached/live main 一致，
divergence 0/0，index/worktree/untracked 干净，无 active Git operation。
自然 CI `34265355099 / push / main / attempt 1 / success`；Python 3.12
`102193214444`、3.13 `102193214112` 的 validator/generated/golden/package 全成功。
Slice-8 local `12340 passed` 与 CI `12336 passed / 4 skipped` 是不同观察；
不更改既有合理 environment/history skips 来凑相同计数。

用户执行授权明确采用 **S9-NAME-1**：每个 output position 使用第一 authored
operand 的 completed output label；其余 operands 只按位置对齐。第一 operand
只给 label；result identity 归 set owner，类型/NULL/property/lineage 来自完整
operation-specific evidence。第一输入无效/不可用时禁止 first-available fallback；
runtime empty BAG 不改变 label authority。这是本 Slice 新补充，不回写为
[原 D04/D06/D07](phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md)
既有裁决。D01–D08、D07-FLOAT-DEFERRED、N=11、E01–E12 保持。

复用当前 SetRelationDef/SetOperationBody/SetOperand 与 TABLE/QUERY identities；
无 grammar/AST/generated edits。quantifier 必须显式 ALL/DISTINCT，至少两个
authored operands，保留 AST/span/order/repetition；一个 operand 可多次使用，
scheduling build 一次不等于 operand-use dedup。

## 三个 checkpoints 与当前 producer/consumer

1. Vertical skeleton：两输入 UNION ALL -> canonical non-SELECT output -> replay/check；
   quantifier/arity/width/type negatives、旧 SELECT control，early 两 Pyright/Ruff。
2. Semantic matrix：六条多重性律、NULL、重复、Decimal、Float、type/equality 分离、
   property/grain 与 EXCEPT grouping；再运行两 Pyright。
3. Consumption/adversaries：sets/JOIN/DISTINCT/tails、cycles、imports/self-use、
   diagnostics/negative readers，完整 review 后 final validation。

| Producer | Retaining root | Consumer / exact closure |
| --- | --- | --- |
| Existing module relation binding environment | explicit operand reference/resolution variants over original SetOperand + ordinal; complete candidate/blocker authority | completion dependency producer, no fake FromClause or second name registry |
| Existing completion topology | every available FROM/JOIN/set occurrence edge before dependency-first scheduling | existing SCC versus blocked descendants; no blocked output allocation |
| Current effective-input adapter | exact historical/completed SELECT/completed set entry and complete visible fields | shared row-equivalence/type evidence; no fabricated SelectItem |
| Shared row-equivalence owner | canonical type and original alias/nominal provenance; exact validated Decimal (p,s) and source images | separate positional compatibility from operation-specific equality capability |
| New set semantic stage | exact owner/body/operator/quantifier, source-ordered operand uses and positional mappings | all-or-none canonical non-SELECT output in existing final-output owner |
| Existing final-output schedule | SELECT and non-SELECT typed variants share RELATION_OUTPUT identity construction | ordinary replay, both current JOIN roles, another set and SELECT DISTINCT |
| Existing key/FD/grain kernels | operation-specific exact field images and NULL/equality premises | UNION loses branch-local FD/key; INTERSECT all applicable inputs, EXCEPT safe left facts |
| Completed diagnostics / requests | exact owner-held temporary admission causes, original matching roots | retire only genuinely completed causes; no generic set/grain single-match proof |
| Existing IR/verifier/observer | retained set roots/dependencies and downstream replay | explicit negative boundary until Slice 10; unaffected historical bytes unchanged |

SELECT constructor invariants stay intact. Non-SELECT fields have set-owned canonical
identity、position、label、type/nullability 与全部 operand-use/field mappings，不需要
select_fact/SelectItem/window identity。新字段 local result role 为普通结果值；
原 GROUPED/aggregate/window role 只保留在 source provenance。

当前 type-alias contract 保留 declared 与 canonical facts，不产生新 scalar primitive。
兼容性使用现有 canonical kind/name 和确切 terminal nominal declaration；
别名/导入的原始声明与路径仍保留，不按同名猜测、不合并独立 nominal types。
Decimal 各位置双方必须独立带已验证的同 precision **且** scale，缺失不借邻列、
不从 aggregate 反推，不 widening。

| Operation | Binary class multiplicity (m,n) | Row equivalence |
| --- | --- | --- |
| UNION ALL | m+n | No; exact shape/type only |
| UNION DISTINCT | 1 iff m+n>0 | Yes |
| INTERSECT ALL | min(m,n) | Yes |
| INTERSECT DISTINCT | 1 iff m>0 and n>0 | Yes |
| EXCEPT ALL | max(m-n,0) | Yes |
| EXCEPT DISTINCT | 1 iff m>0 and n=0 | Yes |

Flat operands 按 authored order left fold；命名 nested set 保留显式边界，EXCEPT
不改为 right association。只记录 operation/evidence；有界 oracle 仅在 tests，
无生产 row evaluator、database、winner selection 或 ALL 的额外 dedup。

UNION nullability 保守合并；INTERSECT 可用任一对应 NON_NULL，UNKNOWN 不能变
NON_NULL；EXCEPT 保留 first input 的安全 nullability。UNION ALL 为 alternative
domain，非 JOIN factor product；DISTINCT variants 为独立 set quotient origin，
不伪造 SELECT DISTINCT/GROUPED_RESULT。ALL subset 操作保留精确 subset evidence；
只有当前确切前提可保留输入 grain，否则显式 UNKNOWN，不任择 surviving occurrence。
多个 GLOBAL operands 不使 UNION GLOBAL；unknown grain 本身不使已知类型 set 非法。
无 automatic fanout-safe reaggregation。Right EXCEPT inputs 始终保留 membership/
multiplicity dependency，哪怕不提供输出 value lineage。

D07-FLOAT-DEFERRED：Float/aliases 在五种 equality-dependent forms 中 ERROR，
无 finite-value exception。UNION ALL 不因 equality unavailable 而拒绝具体 Float；
Any/Bytes/Json 同样先按真实 exact type evidence 判兼容。UNKNOWN type 不自相兼容。
PIE-S2337/2338 与 SELECT-DISTINCT PIE-S2339/2340 含义不变。
Gate-1 code audit 确认 PIE-S2341–2344 空闲，计划分别用于 set quantifier/arity、
input/width、positional type/Decimal、required row-equivalence failure；
existing precise unknown/ambiguity diagnostics 保持 identity/order，不全局按 code 去重。

## Gate 1 exact path freeze

下表在首个 repo edit 前保存到仓库外。Core 11；additional production 16/16；
new private modules 最多 2（第二个仅限实际需要的依赖边界）；existing focused 8/8；
historical/static 12/12；可选新增 focused 1。contingency 必须先记录逐路径原因；
unused quota 不允许补充或替换路径。生产字段身份构造只在既有 final-output owner。

| State / category | Exact path |
| --- | --- |
| ACTIVE core | src/pietto/_project/module_relation_resolution.py |
| CONTINGENCY core | src/pietto/_project/module_semantic_fact_preservation.py |
| CONTINGENCY core | src/pietto/_project/module_attribution.py |
| ACTIVE core | src/pietto/_project/project_completion.py |
| ACTIVE core | src/pietto/_project/project_final_outputs.py |
| ACTIVE core | src/pietto/_project/project_completed_semantics.py |
| ACTIVE core | src/pietto/_project/project_row_equivalence.py |
| ACTIVE core | src/pietto/_project/project_grain.py |
| ACTIVE core | src/pietto/_project/project_ir_relational_properties.py |
| ACTIVE core | src/pietto/_project/project_current_join_inputs.py |
| CONTINGENCY core | src/pietto/_project/project_current_joins.py |
| ACTIVE direct reader | src/pietto/_project/model.py |
| ACTIVE direct reader | src/pietto/_project/let_scope_facts.py |
| ACTIVE direct reader | src/pietto/semantic/let_bindings.py |
| ACTIVE direct reader | src/pietto/_project/project_query_block_ir.py |
| ACTIVE direct reader | src/pietto/_project/project_query_block_ir_verification.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_inspection.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_pure_boundary.py |
| CONTINGENCY direct reader | src/pietto/_project/project_ir_construction.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block.py |
| CONTINGENCY direct reader | src/pietto/_project/project_multifact.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_aggregation.py |
| ACTIVE direct reader | src/pietto/_project/project_single_match.py |
| CONTINGENCY direct reader | src/pietto/_project/module_inspection.py |
| CONTINGENCY direct reader | src/pietto/_project/module_pure_boundary.py |
| CONTINGENCY direct reader | src/pietto/_project/row_expression_type_facts.py |
| CONTINGENCY direct reader | src/pietto/_project/project_relationship_uses.py |
| ACTIVE new private | src/pietto/_project/project_set_operations.py |
| CONTINGENCY new private | src/pietto/_project/project_set_inputs.py |
| ACTIVE required | docs/spec/phase64-slice9-set-operations-explicit-all-distinct-output-identity-v1.md |
| ACTIVE principal | tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py |
| CONTINGENCY new focused | tests/test_phase64_slice9_set_output_composition_and_authority.py |
| ACTIVE guide/lifecycle | docs/status.md |
| ACTIVE guide/lifecycle | docs/roadmap.md |
| ACTIVE guide/lifecycle | docs/language.md |
| ACTIVE guide/lifecycle | docs/spec/diagnostics.md |
| ACTIVE guide/lifecycle | tests/test_active_phase_lifecycle.py |
| ACTIVE guide/lifecycle | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |
| CONTINGENCY guide | docs/project-package.md |
| CONTINGENCY focused | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py |
| CONTINGENCY focused | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py |
| CONTINGENCY focused | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py |
| CONTINGENCY focused | tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py |
| CONTINGENCY focused | tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py |
| CONTINGENCY focused | tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py |
| CONTINGENCY focused | tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py |
| CONTINGENCY focused | tests/test_compilation_boundary_qualify_admission.py |
| CONTINGENCY historical/static | tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py |
| CONTINGENCY historical/static | tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py |
| CONTINGENCY historical/static | tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py |
| CONTINGENCY historical/static | tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py |
| CONTINGENCY historical/static | tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py |
| CONTINGENCY historical/static | tests/test_phase63_slice8_joined_row_filtering.py |
| CONTINGENCY historical/static | tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py |
| CONTINGENCY historical/static | tests/test_phase63_slice10_generic_window_computation_sites_named_window_reuse.py |
| CONTINGENCY historical/static | tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py |
| CONTINGENCY historical/static | tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py |
| CONTINGENCY historical/static | tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py |
| CONTINGENCY historical/static | tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py |

Additional direct-reader purposes：
- src/pietto/_project/model.py: Narrow completed set input type to existing projection helper; legacy model remains negative.
- src/pietto/_project/let_scope_facts.py: Concrete named set row schema to existing LET kernel.
- src/pietto/semantic/let_bindings.py: Existing LET input-schema dispatch for exact provided set inputs.
- src/pietto/_project/project_query_block_ir.py: Negative set-root construction/snapshot boundary.
- src/pietto/_project/project_query_block_ir_verification.py: Foreign set-root/operand dependency negative continuity.
- src/pietto/_project/project_query_block_ir_inspection.py: Negative-only set/grain direct reader.
- src/pietto/_project/project_query_block_ir_pure_boundary.py: Existing negative format compatibility only.
- src/pietto/_project/project_ir_construction.py: Preserve raw set fragment non-concreteness.
- src/pietto/_project/project_query_block.py: Current-input/typed set terminal adapter only.
- src/pietto/_project/project_multifact.py: Unknown/subset/set input grain to existing risk analysis.
- src/pietto/_project/project_joined_aggregation.py: Existing aggregate-safety consumer with new inputs.
- src/pietto/_project/project_single_match.py: Set roots give no new generic cardinality proof; retain downstream own LIMIT.
- src/pietto/_project/module_inspection.py: Preserve low-level resolution observation boundary.
- src/pietto/_project/module_pure_boundary.py: Existing typed negative reader compatibility.
- src/pietto/_project/row_expression_type_facts.py: Exact provided type bridge only if directly required.
- src/pietto/_project/project_relationship_uses.py: Set named input is not a derived relationship endpoint.

## 验证、计数与出版

主代理前台 semantic + engineering 与 Ponytail review，无 subagents/background
agents。允许现有受控 test subprocesses 和 resource-aware xdist/loadfile。
使用 normal populated locked uv cache，保留失败日志，未知进程终态先恢复；
不通过重跑 unchanged failed candidate 求幸运通过。

Final：focused/affected Python 3.12/3.13、F01/F02、affected broad、sole lifecycle/
inventory、whole-tree format/Ruff、两 Pyright、diff、native generated/golden/package，
以及 `UV_PYTHON=3.13 uv run python scripts/validate.py --timings`。
每项结果绑定 actual tested tree，最终 full validation 覆盖 final candidate；
passes/skips 分开报告，不加 machine-specific timing assertion。

Fresh Slice-9 counters：corrective batches 0/20，authoritative starts 0/4，
ordinary initial commits 0/1，ordinary natural-CI repair children 0/2。
初始实现与 S9-NAME-1 决策不计 repair；每项 corrective cause/path/count 显式记录。
该 repair envelope 是用户对 AGENTS.md 单 batch 默认规则的明确覆盖。

成功 review/validation 后 seal，rebind baseline/stage exact tree，一次 ordinary
commit `Add Phase 64 set operation semantics`，ff push main，要求自然 final-exact-head
push/main/attempt 1 的 Python 3.12/3.13 validator/generated/golden/package 成功。
失败 head 保留，仅用预算内普通 child；无 amend/rebase/force/manual CI/squash/
admin bypass/tag/Release/sign/attest/status-only follow-up。

自然 CI 成功才有 Phase 64 ACTIVE；Slices 1–9 PUBLISHED；Slice 10 NEXT/
NOT IMPLEMENTED；Slice 11 NOT IMPLEMENTED。E08 在确切支持域内交付，E09 set
部分覆盖。Slice 10 接收真实 set roots、operand uses、field/type/equality/provenance
maps 和 obligation retention 边界；E05/E10 全闭合仍归 Slice 10。不设计 ProjectSQLPlan。

## Checkpoint 1 记录

Baseline 4 expected failures / 1 SELECT control pass。Operand reference/resolution
variants 由既有 module binding authority 产生，当前 completion topology 一次
保留，再创建完整 dependency edges；raw historical module environment 不新增
其自身不消费的 set metadata。生成器、AST、公开 observer 格式均不变。
初始实现未计 corrective batch，当前 counters 0/20、0/4、0/1、0/2。

Early production Pyright 18 errors、test Pyright 19 errors；完整归因后修复：
1. Row-equivalence input 的 field 属性遮蔽 dataclasses.field；把它放在最后。
2. 新 closed variants 的类型窄化：SELECT diagnostic 保持 SELECT-only，schema/domain
   reader 接受两种 completed outputs，旧 LIMIT reader 显式排除 set；grain body 精确窄化。
3. LET input Mapping key invariance：callee 接受既有与 set-input mappings，安全读取
   provided schema；不要求未授权的旧 analyzer caller 改变其模型。
4. dependency source-site 合约：新的 resolved set operand 提供真实 SetOperand.site；
   completion cycle diagnostic 与旧直接 reader 共享此现有含义，不伪造 FromClause。
5. principal 对实际成功 output variants 做显式断言；错误 entry 不当作 schema。
这些是 corrective batches 1–5；仅冻结的 active production/principal paths。
当前 repairs 5/20，validators 0/4，commits 0/1，CI children 0/2。

Vertical checkpoint 4 passed / 1 failed：set output 与 replay 已真实生成且
diagnostics 为空，但 completed ok 的 closed-variant classifier 漏接新输出。
Corrective batch 6 扩充这一成功分类；不把 error 或 unavailable entry 当成功。
同一 batch-4 source-site 适配补足 isinstance 窄化，test Pyright 已 0 errors。
Counters repairs 6/20，validators 0/4。

第二 checkpoint 的 production Pyright 5 errors，test Pyright 的结果另存。
Corrective batch 7：SELECT type_sources 声明放在名为 field 的属性之前，消除同类
class-scope 名称遮蔽。Batch 8：set operand use 的 producer 明确为实际
ProjectEffectiveJoinInputAuthority，并运行 exact nominal type guard，避免抽象
adapter 替换真实 current producer。Batch 9：field-image helper 使用已窄化的
non-None image，保持默认旧路径与 coalesced set-image 路径的类型闭合。
Repairs 9/20；authoritative starts 0/4；无出版操作。

Checkpoint 2：45 semantic tests、production/test Pyright 均通过。激活预冻结
tests/test_phase64_slice9_set_output_composition_and_authority.py：把真实消费、
imports/cycles/identity adversaries 与 principal 的 type/multiplicity/property
矩阵分开，复用现有 acquisition helper，不复制旧 Slices 的完整矩阵。
此为 planned checkpoint 3，repairs 仍 9/20，validators 0/4。

## Foreground complete review finding set

Checkpoint 3 为 70 passed，test Pyright 0 errors。主代理 fresh semantic + engineering
与 Ponytail review 后冻结以下完整 root-cause 集（无独立 reviewer/subagent）：
- Batch 10：scope.available 未限制为本 owner 前的实际 topology prefix，可混入自己
  或 foreign unused entry。两条 real-root graft red 已复现；同时在 overlay 验证
  available entries 的实际 object membership，防 equal-looking producer 替换。
- Batch 11：自身 relation binding 歧义的 set owner 仍能构造 concrete output；保留
  原 collision diagnostics，并让该 owner 保持 typed non-concrete，不选其中一个。
- Batch 12：computed input 没有 TypeExpr 时，foreign type-source root 仍可 certifiy；
  adapter capability 必须绑定它自身 completion 的 exact type root。
- Batch 13：EXCEPT mapping 没有显式区分 value sources 与 membership sources；新
  derived views 保留左侧 value provenance，以及包含全部右侧的 membership/type map。
19-review-red 为 4 failed，20-lineage-red 为 1 failed；均是新语义边界的在域 findings。
全部修复局限于已冻结 active set/equivalence/final owner 与新 focused tests。
Repairs 13/20，authoritative starts 0/4，commits/CI children 0。

Review repair reread 为 74 passed / 1 failed，失败仅为新增测试的 diagnostic
预期：既有 local duplicate relation symbol 使用 PIE-S2001，不是 import/binding
collision 的 PIE-S2706。Corrective batch 14 仅修正该断言，保留生产诊断对象。
Repairs 14/20，validators 0/4。

直接相关回归 760 passed / 15 failed。分为一个真实诊断原因与既有 readiness 迁移：
Corrective batch 15：失败 set 的新 terminal 没有遍历 base-entry 的 owner-held
PIE-S2334 cause；23-diagnostic-root-red 独立复现 exact Diagnostic identity 丢失。
失败路径保留该原始 cause，只有成功 set admission 才退休它。
激活两个 Gate-1 focused contingencies 并作 batch 16：
- tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py：
  更新 UNION ALL 可用性、set operand dependencies 与新 typed terminals；原 AST/span、
  missing quantifier、独立 cycle/SCC、legacy/IR negative guarantees 保留。
- tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py：
  DISTINCT outputs 现在可作 sets 输入；combined IR 仍须拒绝。保留全部 Slice-8 laws。
不改历史契约或未冻结文件；repairs 16/20，validators 0/4，publication 仍未开始。

迁移后 focused 379 passed。其最终 typing 复查补足 batch 11 的 branch-local
owner_diagnostics 名称，避免与后续 list 同名；补足 batch 16 的字典 entry 窄化。
这两项仍是尚在核验中的同一 cause。Ruff 发现 7 个无 caller 的测试 imports；
corrective batch 17 只删除这两个已激活测试文件内的 stale imports。
Repairs 17/20；validators 0/4。无新 production 语义变更。


## Explicit reader reservation amendment after STOP

此前 affected broad `27-broad313.log` 为 1380 passed / 1 failed；唯一失败是
Slice-3 `test_set_input_and_independent_valid_branches_survive` 对合法 UNION ALL
仍要求 unavailable JOIN reference、terminal output 与零 dependencies。该直接
reader 不在原冻结修改清单，故保留 A4/M16/D0、空 index 的候选并停止于
`STOP — UNLISTED_REQUIRED_PATH`；未执行 validator、stage、commit 或 push。

用户随后明确接受这一 dirty candidate，并授权一次一换：
- ADD / ACTIVE focused：
  `tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py`。
- REMOVE unused modification reservation：
  `tests/test_compilation_boundary_qualify_admission.py`；仍是必须执行的 F01/F02
  validation coverage，禁止修改。

上方原 Gate-1 list 保留为历史；本修订改变当前 effective modification closure，
总路径额度不增加，其他 active/contingency 状态和用途不变，无其他替换授权。
续作核对 local/cached/live main、HEAD tree、parent 均与 STOP 基线一致，0/0、
无 active Git operation，两个交换路径均未修改， proposed patch 未应用。

已审阅 proposed patch；迁移限于该测试与一项 import，正向断言 concrete set、
authored ordered dependency/use 的确切对应、resolved/ready JOIN 的 exact set
entry，以及独立 valid branch。Slice-9 composition 中 missing-first/later、mixed
cycle/blocked descendant 与 invalid upstream aggregation 继续提供真实负例隔离。
该迁移记作 corrective batch 18；行政授权不另计批次。累计 repairs 18/20，
authoritative starts 0/4，initial commits 0/1，CI children 0/2；前 17 批和失败日志保留。


## Continuation review and final validation candidate

Batch 18 的单项测试 1 passed；whole Slice-3 + Slice-9 principal/composition +
F01/F02 在 Python 3.13 与 3.12 均 218 passed / 0 skipped。必要同文件 import
清理属于同一 reader migration。Production/test Pyright 均 0 errors；Ruff、
whole-tree format 与 diff check 通过。此前失败 broad 原日志和 STOP receipt 保留。

主代理前台复查全部既有 findings、迁移 diff、dependency/type/provenance/final
output/property consumers 与旧 IR negative guards；没有独立 reviewer 或 subagent。
Ponytail review 保留当前实际 invariants 所需的 typed variants，未新增备用 module、
registry、executor 或 Slice-10 正向 IR。没有剩余已确认 finding。

原已冻结 guide/lifecycle 与 sole inventory reader 现在记录成功自然 CI 后的
Slices 1–9 PUBLISHED、Slice 10 NEXT、Slice 11 NOT IMPLEMENTED；实际 inventory
为 186 production / 440 test Python files。此为原 planned closure，不是另起 repair。
最终改动 A4/M23/D0（27 paths）；修改路径仍在一次一换后的 effective freeze 内。
Repairs 18/20；以下 final gates 开始前 authoritative starts 0/4、commits 0/1、
CI children 0/2。最终 validation、candidate/sealed Git tree 与 publication counters
由仓库外同一 Slice-9 accounting records 记录，natural Git/CI 是出版依据。
