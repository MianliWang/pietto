# Phase 64 Slice 7 Single-Match Direction Unit Scoped Proof Obligation And Warning Diagnostics v1

## Gate 0 与 D05 范围

clean synchronized main 基线 commit `241be04da179969ddb1bd50381ee9ac58cea1641`，
tree `c20ce463fd8f9fb31ac183b6e3f659f5f5c77217`，parent
`04b234a38cb92f647e3a4a869117b15fa1163928`。local/cached/live main 一致，fetch 后
0/0，无 staged/worktree/untracked delta 或 active Git operation。自然 CI
`34238303080` 为 push/main/attempt 1/success；Python 3.12 `102101642715`、
3.13 `102101642205` 的 validator/generated/golden/package 均成功。
D01–D08、N=11、E01–E12 保持。Slice 7 只交付 E06 private semantic/check 三态。

当前没有已批准的 public single-match marker。复用真实 completed roots 上的
显式 private request seam；默认空请求。无 grammar/AST/generated/CLI flag/public
JSON field 变更，无隐式全 JOIN requirement。用户无需作新的 spelling 决策。

计数单位只能为 ACTUAL_MATCHED_BAG_OCCURRENCE：每个 exact left BAG occurrence
在指定 matching boundary 上使完整 predicate TRUE 的 actual right match occurrences。
相同 payload 的两个右 occurrence 仍为两次匹配。FALSE/UNKNOWN、未匹配 outer
合成行、post-JOIN WHERE/LIMIT、SEMI/ANTI 的 0-or-1 left retention、distinct target、
source-side key、grain/estimate 都不构成 right-match count proof。

## Producer/root/consumer 与选择

| Producer | Exact retaining authority | Consumer / rebuild |
| --- | --- | --- |
| Authored use 与 operative condition | real parsed owner、ledger use、condition/base/refinement | private request 绑定现有身份；foreign owner/use/condition/role 为 INVALID |
| Current/historical binary boundaries | current region 优先；无 current acquisition 才可用 exact verified historical region | direct binary / exact path hop / exact complete path 保持分离；whole-path 保留每个 hop input pair |
| Relationship maximum | 同一方向/同一 hop 的 AT_MOST_ONE；M4 exact refined upper bound | PROVED；whole path 需完整 path/use root 和全部 hop 的 applicable proof，不能借单 hop |
| Completed right LIMIT | exact consumed entry/output + its ProjectRelationLimit，或 historical completed fragment 的真实 LIMIT producer/literal | pre-JOIN LIMIT 0/1 提供 exact upper bound；不提升底层 source key/relationship |
| Completed GLOBAL | actual completed aggregation/replay producer mode 与 canonical entry | 只沿真实 producer 证明上界；不读取 intrinsic grain 作为 cardinality |
| Private assessments/obligations | exact effective-output root 与显式 request occurrences | completed result 保留结果并把新诊断追加到原有诊断之后；只按 Diagnostic object identity 防重 |
| IR / observer readers | 尚不能保留 private obligations 的旧组合接口 | 若被传入非空 request，必须 fail closed；不增加 positive IR/inspection 或新 format |

选择一个新 private module `project_single_match.py`，由现有 completed-result
constructor 实际调用；它消费 upstream condition/current/final facts，无回指到未完成
root、无新 JOIN identity 或第二 property/cardinality engine。相比把高层 completed
input/diagnostic 依赖塞回 directional relationship owner，该位置避免反向耦合。
private completed result 可复用原 roots 接收显式请求，默认普通编译的空请求不改变
历史语义、diagnostic bytes 或公共入口。INVALID assessment 不产生可执行 obligation；
invalid D02/D03 operation 的原错误保留，也不获得 obligation。

PROVED 保留全部适用 exact evidence，无新增 warning。LEGAL_UNPROVED 保留
下游 enforcement requirement，并产生一个 `PIE-S2337` WARNING，在三种 mode
均不升级为 ERROR。INVALID 请求产生独立 `PIE-S2338` ERROR。代码审计确认这两个
码空闲，不复用 2334–2336。warning 表示未静态证明，不表示已执行或已兑现。
同一 request object 重复引用不得重复插入同一个 Diagnostic；不同请求的同码同文
诊断保持各自 identity。原有 warning/error 的次序与多重性不归一化。

## Gate 1 exact path freeze

以下完整清单在首个 repo edit 前保存至仓库外。contingency 必须先在本文记录
直接原因才可激活。core 7、additional direct readers 10/10、new module 1/1、
existing focused 8/8、historical/static 12/12。未使用容量不授权新增或替换路径。

| State / category | Exact path |
| --- | --- |
| CONTINGENCY core | src/pietto/_project/project_relationship_match_guarantees.py |
| CONTINGENCY core | src/pietto/_project/project_join_conditions.py |
| CONTINGENCY core | src/pietto/_project/project_current_joins.py |
| CONTINGENCY core | src/pietto/_project/project_current_join_inputs.py |
| ACTIVE core | src/pietto/_project/project_completed_semantics.py |
| CONTINGENCY core | src/pietto/_project/project_final_outputs.py |
| CONTINGENCY core | src/pietto/_project/project_completion.py |
| CONTINGENCY direct reader | src/pietto/_project/project_relationship_uses.py |
| CONTINGENCY direct reader | src/pietto/_project/project_relationship_paths.py |
| CONTINGENCY direct reader | src/pietto/_project/project_ir_relational_properties.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_aggregation.py |
| CONTINGENCY direct reader | src/pietto/_project/project_joined_qualify.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_verification.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_pure_boundary.py |
| CONTINGENCY direct reader | src/pietto/_project/project_query_block_ir_inspection.py |
| ACTIVE new private module | src/pietto/_project/project_single_match.py |
| ACTIVE required | docs/spec/phase64-slice7-single-match-direction-unit-scoped-proof-obligation-warning-diagnostics-v1.md |
| ACTIVE principal | tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py |
| CONTINGENCY focused | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py |
| CONTINGENCY focused | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py |
| CONTINGENCY focused | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py |
| CONTINGENCY focused | tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py |
| CONTINGENCY focused | tests/test_phase62_slice8_referential_coverage_match_simple_full_directional_match_guarantees.py |
| CONTINGENCY focused | tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py |
| CONTINGENCY focused | tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py |
| CONTINGENCY focused | tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py |
| CONTINGENCY historical/static | tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py |
| CONTINGENCY historical/static | tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py |
| CONTINGENCY historical/static | tests/test_phase63_slice16_completion_audit_phase64_handoff.py |
| CONTINGENCY historical/static | tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py |
| CONTINGENCY historical/static | tests/test_phase62_slice14_private_inspection_winner_free_query_pure_canonical_boundary.py |
| CONTINGENCY historical/static | tests/test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance.py |
| CONTINGENCY historical/static | tests/test_phase62_slice16_completion_audit_phase63_handoff.py |
| CONTINGENCY historical/static | tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py |
| CONTINGENCY historical/static | tests/test_phase62_slice1_relationship_join_keys_fd_grain_fanout_multifact_architecture_source_audit_route_lock.py |
| CONTINGENCY historical/static | tests/test_phase61_slice12_completion_audit_phase62_handoff.py |
| CONTINGENCY historical/static | tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py |
| CONTINGENCY historical/static | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py |
| ACTIVE lifecycle/guide | docs/status.md |
| ACTIVE lifecycle/guide | docs/roadmap.md |
| ACTIVE lifecycle/guide | docs/language.md |
| ACTIVE lifecycle/guide | docs/spec/diagnostics.md |
| ACTIVE lifecycle/guide | tests/test_active_phase_lifecycle.py |
| ACTIVE lifecycle/guide | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |

## Review / validation / accounting

先最小 no-request/unproved/proved/invalid red cases 与早期 production/test Pyright，
再完成 C06 pre-vs-post LIMIT、所有 matching kinds、hop/path、producer/tail、foreign/
stale/self-use、JSON/text severity 和 unrelated errors。有限 multiplicity witness
仅用 test-side occurrence tuples，不用 database 或 production evaluator。
主代理 foreground 执行 semantic + engineering 与 Ponytail review；无 subagent。

最终 focused Slice-7/3–6/F01/F02 双 Python、resource-aware loadfile affected 回归、
sole lifecycle/inventory、Ruff/format、两 Pyright、diff、native generated、golden、
package smoke 与 `UV_PYTHON=3.13 uv run python scripts/validate.py --timings`。
每个 validator start/result 绑定 exact candidate，失败不可 unchanged luck rerun；
未知 observation 先恢复进程终态，不能重叠启动。

Fresh counters：repairs 0/20、authoritative validators 0/4、initial commit 0/1、
CI repair children 0/2。初始计划实现不计 corrective batch。证据与 prompt 保留仓库外。
全部 review/validation 完成才 seal；rebind remote、stage sealed paths、一次 ordinary
commit 与 fast-forward push，观察 natural exact-head push/main/attempt 1 CI。
不 amend/rebase/force/rerun/dispatch/squash/tag/Release/sign/attest/status-only commit。

成功 publication 后 Phase 64 ACTIVE；Slices 1–7 COMPLETED/PUBLISHED；Slice 8
NEXT/NOT IMPLEMENTED，Slices 8–11 未实现。E06 仅 semantic/check complete；
Slice 8 row-equivalence/DISTINCT、Slice 9 sets/non-SELECT、Slice 10 combined IR/
verification/inspection、Slice 11 completion/handoff、Phase 65/66 SQL 与 Phase 68
unproved obligation runtime fulfillment 都保持后续 ownership。

## Checkpoint 与 corrective ledger

真实 authored empty-request baseline 1 failed（缺少 private seam），初始实现后
1 passed。早期 production Pyright 发现 malformed-use INVALID diagnostic fallback
漏传必需 location。Corrective batch 1：new private module 使用明确 unknown-source
`SourceLocation(path=None, line=1, column=1)`，普通有效 use 仍保留 exact authored
span。仅修正 malformed private request 的 ERROR 构造；repairs 1/20，validators 0/4。

Principal 首次扩展 collection 失败：parse-check API 位于 `_project.check` 而非
`_project.model`。Corrective batch 2 只修正 principal import。没有形成行为 verdict；
repairs 2/20，validators 0/4。

初步状态/方向/C06/三模式 matrix 40 passed，early test Pyright 0 errors。
激活两个冻结的 direct-reader contingencies：
- `src/pietto/_project/project_query_block_ir.py`：非空 private requests 不能被旧
  combined builder/snapshot 静默丢弃；入口与 closed snapshot 构造拒绝该未支持 root。
- `src/pietto/_project/project_query_block_ir_verification.py`：防止把带请求的同一
  completed root graft 到旧 snapshot 后仍获 VERIFIED，按既有 ROOT_CONTINUITY 拒绝。
该适配只保持 Slice-10 前 negative boundary，不新增 IR node/schema/enum/format、
不赋予 inspection 正结果；默认空请求的行为与 observer bytes 不变。
追加 contingencies 2/10；repairs 2/20，validators 0/4。

Authority/path matrix 47 passed / 1 failed。Corrective batch 3：malformed private
`input_pairs=(object(),)` 在 `_same_pairs` 先触发 len() traceback；在比较 exact use
roles 前验证 tuple/pair 的完整类型和 arity。仍只输出一个 INVALID ERROR，且不会
产生 obligation/proof。只修改 new private module；repairs 3/20，validators 0/4。

Diagnostic-identity regression 为 48 passed / 1 failed：附加 request 时 completed
result 重新调用 `_fallback_diagnostic`，生成了等值但不同的既有 ERROR object。
Corrective batch 4 在同一 `_ProjectCompletedSemanticRoots` 保留一次生成的 base
诊断，result 只在其后投影新 request 诊断。该 tuple 是当前 root 的规范诊断事实，
不是跨 snapshot/cache 或 observer 结果。空请求与原错误顺序不变；private request
字段沿既有 roots 字段使用 repr=False。repairs 4/20，validators 0/4。

Focused Python 3.13 474 passed，production/test Pyright 均 0 errors。
新增 principal+lifecycle/inventory 为 187 passed / 1 failed：未使用 shape 的
single-file PIE-S2005 fixture 不会由当前 explicit-module producer 产生。
Corrective batch 5 只修正测试入口：从真实 parser/analyzer 取得旧 warning，再与
真实 rooted request warning 经既有 JSON v2 diagnostic consumer 验证顺序与成功规则。
不扩展旧 warning producer。既有 completed ERROR/fallback identity 与两条独立
request warning 的 source order 已另有真实 completed-root regressions。
repairs 5/20，validators 0/4。

## Foreground complete review

主代理重新阅读完整实现、principal 和 completed/IR direct consumers，按
code-verification 与 Ponytail FULL/review 做两轴审查；无独立 reviewer/subagent。
已发现的 malformed-pair 与旧 fallback Diagnostic identity 均修复并复查。

| Review question | Exact answer / evidence |
| --- | --- |
| What is counted? | 每个 exact left BAG occurrence 对完整 TRUE predicate 的 actual right BAG match；C06 两个相同 payload 仍 count 2，distinct payload 1 |
| Which left/right uses? | assessment.input_pairs 来自 retained binary operators；whole path 保留所有 hop pairs；同 producer self-use 仍按 use object 区分左右 |
| Which condition/scope? | exact operative ProjectJoinCondition；base/refinement 不替换，direct/hop/whole-path selector 分离；外来或错误 path/hop/condition 为 INVALID |
| Why do proofs apply? | same-direction/hop AT_MOST_ONE 或 exact refinement；whole path 所有 hop 都需证据；right LIMIT root/compiled LIMIT producer 或 actual completed GLOBAL root；同时保留所有适用 proofs |
| Grain versus cardinality? | proof code 不读取 grain；真正 FULL(two GLOBAL) UNKNOWN 不被判为 GLOBAL cardinality；left GLOBAL/LIMIT 不约束 right matches |
| SEMI/ANTI retention? | 这两种 kind 的 generic unbounded right 仍 LEGAL_UNPROVED；未从输出 0/1 生成证明 |
| Pre- versus post-LIMIT? | 只追踪 exact right producer 的 limit，JOIN owner 自身 limit/where 不参与；不推导 raw source key |
| Stale/equal-looking roots? | request roots/roles/hops 要求 object membership；derived state/proofs init=False，旧 LIMIT/condition 不可 graft；fresh valid request 丢失 proof 时降为 LEGAL_UNPROVED |
| Successful warning? | 真实 completed ok=True 与 actual CLI text/JSON consumer 传递 exact PIE-S2337 WARNING；三模式一致，unrelated ERROR 保留且 ok=False |
| Data repair? | 无数据执行、选择、截断、payload dedup 或 database evaluator；只生成 immutable semantic facts/diagnostics |
| Extra engine/dead abstraction? | 一个高层 private request module，由 completed result 当前调用；复用旧 boundary、limit、mode、guarantee，未建 property/cardinality engine、registry 或缓存 |

IR builder/snapshot 与 verifier 对非空 request 只作 negative closure；默认空请求
与旧观察格式保持。Base diagnostics 归现有 completed root，保留稳定 object identity；
request diagnostics 只按 exact object 防重，原有顺序与多重性不被全局归一化。

Affected broad regressions 为 730 passed / 1 failed。激活冻结 focused contingency
`tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py`
（1/8）：它把 private completed-result fields 固定为旧 exact set，拒绝本 Slice
已授权的 request/set 字段。Corrective batch 6 保留原字段作为 required subset、
原禁止公开 IR fields 与 JSON v2 exact keys，并增加默认 request/obligation/diagnostic
为空的行为检查；不把 private carrier shape 当成永久 public schema。
repairs 6/20，validators 0/4；historical/static contingencies 仍 0/12。

## Final review closure 与 pre-validator evidence

Fresh rereview 无剩余 material finding。新增 UNKNOWN-grain + actual right LIMIT-1
正例仍 PROVED，说明 cardinality proof 与 grain availability 独立；completed-left
LIMIT/GLOBAL matrix 全部不产生 right-match proof。Ponytail review 未发现需要保留的
第二 engine、registry、cache、无 caller 的 abstraction 或 data-repair code。

最终 principal 93 cases；Python 3.13 与 3.12 相同 focused set 各 501 passed，含
Slice-3–7、Phase-63 completed-diagnostic consumer 与 F01/F02。修复后的 resource-aware
`-n 4 --dist=loadfile` affected broad set 为 731 passed（含 historical observer/
differential controls）。Sole lifecycle/inventory 101 passed。625-file whole-tree
format、Ruff、production/test Pyright、diff check 均通过。Native OpenJDK/ANTLR
验证 8 tracked generated files byte-for-byte；golden audit 39 fixtures；installed
sdist/wheel/CLI smoke 全部成功。CLI/JSON production files 零变更。

实际 closure A3/M10/D0，共 13 paths。新增 required contract/principal 与一个 private
module；existing core 只改 completed semantics；两个 activated production contingencies
是 query-block IR builder/snapshot 与 verifier 的 negative-only guards；一个 activated
focused contingency 是 Phase-63 Slice-13 private carrier compatibility。其余四个 guide
与两个 sole lifecycle/inventory readers 按冻结清单更新。没有 historical/static
contingency、grammar/AST/generated/golden contents、dependency/lock/workflow/validator/
version/public schema/SQL 变更。

Pre-validator accounting：corrective batches 6/20（3 production、3 test），
authoritative local starts 0/4，initial publication commit 0/1，natural-CI repair
children 0/2。全部 failed evidence 保留仓库外；无 validator observation interruption。
后续 authoritative validator start/result 绑定 exact candidate tree，seal/commit/push/
natural CI 结果保留在外部 operation ledger 与 Git/CI，不预写未知 identity。
