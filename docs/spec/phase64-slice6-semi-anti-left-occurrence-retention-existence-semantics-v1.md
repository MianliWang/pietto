# Phase 64 Slice 6 SEMI/ANTI Left-Occurrence Retention And Existence Semantics v1

## Gate 0 与语义边界

基线 commit `04b234a38cb92f647e3a4a869117b15fa1163928`，tree
`c685accd427399c97ae7c4914156b93c5be5dcc9`，parent
`32632ea8dd5057034d2b5add861c1d2850ae5dee`。clean main、本地与 cached/live
origin/main 同一；fetch 后 divergence 0/0，无 active Git operation。
自然 CI `34205094377` 为 push/main/attempt 1/success；Python 3.12
`101992620359`、3.13 `101992620682` 的 validator/generated/golden/package
步骤均成功。Ruff 0.16.6、lockfile 与 shallow-PR maintenance 原样保留。

遵循 D01–D08、N=11、E01–E12；本 Slice 只交付 D02/D03、L07、C05 下的
直接二元 SEMI/ANTI。M1/M2 直接关系与单 VIA、M3 generic ON、M4 单 VIA
refinement 沿既有规则。C03 的 base AND refinement 与 C04 的保守 NULL
证据保持。整个 accumulated-left 的每个 BAG occurrence 在 SEMI 有 TRUE
匹配时保留一次，在 ANTI 无 TRUE 匹配时保留一次；FALSE/UNKNOWN 不匹配。
重复右匹配不能放大输出，等值 payload 的不同左出现不能合并。

输出为新 operator/output 的精确左字段 images，保留顺序、hidden intermediates、
原 introduction 与 nulling。右 binding/ordinal/dependency/input-use/condition
完整保留，但无 visible 或 hidden 右输出；下一个条件与全部 tail 不得复活它。
按 binding/use role 判定 self-use。左 keys/FD/grain 沿 subset 映射；没有新增
fanout、null-extension、右 output factor、coverage 或 match max-one proof。
已知左 grain 不被 UNKNOWN 右污染；UNKNOWN 左与已有 fanout 不被修复。
GLOBAL 仅是 at-most-one posture，不承诺最低一行或 display order。

复用 completion schedule、current input/condition/region、owner-local tail 与
canonical final output。只扩大 EXPLICIT_MODULES 三种 check mode；保持 JSON v2、
F01/F02、CURRENT_JOIN_COMPOSITION_UNSUPPORTED、
EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED 与旧 observer bytes。多跳新 kind、
多跳 refinement、single-match、DISTINCT/sets/non-SELECT、combined IR/inspection、
SQL/execution/optimization 不在本 Slice。

## Producer/root/consumer 冻结矩阵

| Producer | Retaining root / identity | Direct consumer / invalidation |
| --- | --- | --- |
| Authored uses/matching modes | exact ledger binding/use ordinal、base/refinement roots | condition source candidates/rebuild；不能从已消费的右 binding 解析下一个 FROM/VIA |
| Current inputs | complete dependencies、available producer entries、binding roles | pre-match rows；过滤 prior existence right 的可见性，保留失败/循环因果 |
| Current binary | exact prefix/output/properties/origins/allocation、two slots/uses | 左字段 images；输出与输入不同 occurrence；不从 evidence equality 判定角色 |
| Field/key/FD/grain | exact left images 与 both-input condition witness | 既有 property kernel、multifact/aggregate；右 uncertainty 仅作为输入证据 |
| Row/tail | binding introduction 与 final row membership | LET/WHERE/GROUP/satisfying/window/QUALIFY/select/ORDER；空 binding fields 已被既有类型允许 |
| Final completion | exact schedule、operative conditions、available input scopes/current regions | replay/JOIN、check 与 exact successful diagnostic retirement；失败无 partial output |

## Gate 1 exact path freeze

以下 active/contingency 清单在首次 repository edit 前保存于仓库外并冻结。
contingency 只在本文件先记录直接原因后激活。额外 production 12/12，existing
focused 6/6，historical/static 12/12；new focused 最多 2；不预留新 production
module。unused capacity 不允许追加或替换路径。历史契约不改写。

| State / category | Exact path |
| --- | --- |
| ACTIVE core | src/pietto/_project/project_current_joins.py |
| ACTIVE core | src/pietto/_project/project_current_join_inputs.py |
| ACTIVE core | src/pietto/_project/project_join_conditions.py |
| ACTIVE core | src/pietto/_project/project_relationship_uses.py |
| ACTIVE core | src/pietto/_project/project_ir_joins.py |
| ACTIVE core | src/pietto/_project/project_multifact.py |
| ACTIVE core | src/pietto/_project/project_final_outputs.py |
| CONTINGENCY core | src/pietto/_project/project_scalar_bindings.py |
| CONTINGENCY core | src/pietto/_project/project_ir_relational_properties.py |
| CONTINGENCY core | src/pietto/_project/project_grain.py |
| CONTINGENCY additional production | src/pietto/_project/project_joined_row_semantics.py |
| CONTINGENCY additional production | src/pietto/_project/project_joined_aggregation.py |
| CONTINGENCY additional production | src/pietto/_project/project_joined_row_filter.py |
| CONTINGENCY additional production | src/pietto/_project/project_scalar_namespaces.py |
| CONTINGENCY additional production | src/pietto/_project/project_scalar_references.py |
| CONTINGENCY additional production | src/pietto/_project/project_joined_windows.py |
| CONTINGENCY additional production | src/pietto/_project/project_joined_qualify.py |
| CONTINGENCY additional production | src/pietto/_project/project_completed_semantics.py |
| CONTINGENCY additional production | src/pietto/_project/project_query_block.py |
| CONTINGENCY additional production | src/pietto/_project/project_completion.py |
| CONTINGENCY additional production | src/pietto/_project/project_query_block_ir.py |
| CONTINGENCY additional production | src/pietto/_flat_relational_admission.py |
| ACTIVE required | docs/spec/phase64-slice6-semi-anti-left-occurrence-retention-existence-semantics-v1.md |
| ACTIVE principal | tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py |
| CONTINGENCY new focused | tests/test_phase64_slice6_existence_properties_and_authority.py |
| CONTINGENCY new focused | tests/test_phase64_slice6_existence_tail_and_entrypoints.py |
| ACTIVE existing focused | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py |
| ACTIVE existing focused | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py |
| ACTIVE existing focused | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py |
| ACTIVE existing focused | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py |
| CONTINGENCY existing focused | tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py |
| CONTINGENCY existing focused | tests/test_phase62_slice12_per_aggregate_fact_locality_chasm_detection_multi_fact_alignment.py |
| CONTINGENCY historical/static | tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py |
| CONTINGENCY historical/static | tests/test_phase63_slice8_joined_row_filtering.py |
| CONTINGENCY historical/static | tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py |
| CONTINGENCY historical/static | tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py |
| CONTINGENCY historical/static | tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py |
| CONTINGENCY historical/static | tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py |
| CONTINGENCY historical/static | tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py |
| CONTINGENCY historical/static | tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py |
| CONTINGENCY historical/static | tests/test_phase63_slice16_completion_audit_phase64_handoff.py |
| CONTINGENCY historical/static | tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py |
| CONTINGENCY historical/static | tests/test_phase62_slice13_integrity_verifier_analysis_invalidation_bounded_bag_null_semantic_oracle.py |
| CONTINGENCY historical/static | tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py |
| ACTIVE guide/lifecycle | docs/status.md |
| ACTIVE guide/lifecycle | docs/roadmap.md |
| ACTIVE guide/lifecycle | docs/language.md |
| ACTIVE guide/lifecycle | docs/spec/diagnostics.md |
| ACTIVE guide/lifecycle | tests/test_active_phase_lifecycle.py |
| ACTIVE guide/lifecycle | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |
| CONTINGENCY guide | docs/project-package.md |

## 实施、核验与计数

三个内部 checkpoint：left-only operation/check；后续条件/tail 与 dependency；
property/grain/aggregate/effective inputs 与 adversarial composition。先运行最小
real-authored red/old-kind green 和两份 Pyright，再扩大矩阵。

只使用一个 foreground writer；subagent/independent reviewer 未运行。最终进行
主代理实质语义 review 和 Ponytail review；记录全部 finding、直接原因、修改与复查。
失败证据保存在仓库外，不对 unchanged failed validator candidate 重跑。
Fresh bounds：corrective batches 0/20；authoritative validator starts 0/4；
initial publication commits 0/1；natural-CI repair children 0/2。

最终运行 Python 3.12/3.13 principal/affected Slice-2–5/F01/F02、直接读者回归、
Ruff/format、两份 Pyright、diff、native generated/golden/package gates，并执行
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`。
只有 reviewed/validated exact tree 可 seal；重新绑定 remote，精确 stage sealed
paths，ordinary commit 与 ff push，再核实 exact-head natural CI attempt 1。
未知的 seal/commit/CI identity 不预写入此文档。

成功 publication 后 prospective lifecycle：Phase 64 ACTIVE；Slices 1–6
COMPLETED/PUBLISHED；Slice 7 NEXT/NOT IMPLEMENTED；Slices 7–11 未实现。
E03 为 semantic/check delivery，不声明 combined IR/inspection 或全部 E05/E10/
E01–E12 闭合。Slice 7 消费 exact matching boundary、left/right use role、完整
condition/refinement 与 applicable bound；每左出现的 0-or-1 retention 不是右
match cardinality 的证明。本 Slice 不创建 requirement syntax、obligations/warnings。


## Checkpoint evidence

Baseline minimal authored cases：2 expected failures (SEMI/ANTI PIE-S2334)，5
old-kind green；第一检查点为 7 passed。两份 early Pyright 均 0 errors。
第二检查点 scope red 为 16 expected failures / 7 passed，展示已消费右 binding
仍可出现在下一 ON/FROM/VIA 及后续 RIGHT/FULL condition environment。
初始计划的 visibility implementation 在现有 relationship-use owner 共享按 role
判定，historical/current condition rows 与 relationship rebuild 一致消费它。
结构 binding/dependency/ordinal/introduction 不过滤。repairs 0/20，validators 0/4。

第二检查点 23 passed；扩展 BAG/NULL、M1–M4、全部 tail negative scopes、hidden
multihop-left、self-use/C05 后 70 passed。第三检查点 110 passed / 6 failed，
三个独立测试原因分别计 corrective batches 1–3（仅 principal）：
1. `ProjectActualGrainCandidate` 的 kind 在完整 `authorities` 中，不在 candidate；
   改为遍历全部 authority，验证无 predicate-right output-fact authority。
2. fanout tail 沿既有 public fallback 输出 PIE-S2333，不能猜测 PIE-S2323；
   同时断言保留的 private grain linkage 风险/aggregate-algebra requirement。
3. stale allocation 在 prefix authority guard 先拒绝，消息为 prefix，不是 allocation；
   修正精确错误匹配。正确拒绝本身不变。
累计 repairs 3/20，validators 0/4；production 未因这些 assertion 变更。

复验新增 dependency/rebuild/import/retirement 后 128 passed / 2 failed。
Corrective batch 4（principal only）：Explain 既有入口要求 schema 4，schema 2
应返回 CLI exit 2 与 `config_schema`，而非所猜测的 exit 1/schema_version 字段。
按既有 Explain contract 修正断言；不扩大 Explain 支持。repairs 4/20，validators 0/4。

Python 3.13 / 3.12 的 Slice-2–6 + F01/F02 各 529 passed；lifecycle/inventory
101 passed。主代理 complete review 发现 GLOBAL 有限用例中一处只枚举 0/1 的
assertion 未实际执行存在性参考。Corrective batch 5 删除该无效枚举，改用已有
independent BAG oracle 对单 occurrence GLOBAL domain、空右与重复匹配右作
零/一保留检查；不新增 production evaluator。另补核 completed self-use 与下一
M1/M2 role，不改变产品。repairs 5/20，validators 0/4。

最终 test Pyright 暴露 4 errors，冻结为两个独立测试原因，计 batches 6–7：
6. 两个 test-side `type` alias 位于 function scope，移至 module scope。
7. dependency failure 的 effective-output union 未先区分 completed 与 terminal；
   用 exact terminal/existing variants narrowing 后读取 `.output`。
只改 principal，不增加 cast/ignore，也不改变 public type 或生产状态。
repairs 7/20，validators 0/4。

Full candidate/direct-consumer review 的身份 finding 经两种 kind 的真实 authored
self-use 复现：`_CurrentPrefix` 只比对 field evidence，故当左右复用同一 producer
时，把 origins 的 binding 换成 predicate-only right 仍能构造成功（2 failed,
DID NOT RAISE）。Corrective batch 8 在既有 `project_current_joins.py` 要求
current prefix 原样保留前一 current operator 的 `field_inputs` authority tuple。
这是 Slice-6 output membership/left-right-role 边界，不改 historical IR 路径、不删除
dependency、不重建字段。principal 保留该 adversarial regression。此前 affected
suite 为 1272 passed，production/test Pyright 均通过；修正后复验受影响结果。
累计 repairs 8/20（1 production、7 test/evidence），validators 0/4。

Batch-8 后 Python 3.13/3.12 focused 各 537 passed（principal 140）；完整 root
复查确认 current prefix 已拒绝 wrong-role graft。最终 auxiliary gates 的 format
623 files pass，Ruff 首次报告 test oracle 的六个 lambda 使用模糊参数名 `l`。
Corrective batch 9 统一为 `left_value/right_value`，仅 principal 的局部命名。
该 gate 在 lint 后 fail-fast，generated/golden/package 尚未启动；不计 validator。
repairs 9/20，validators 0/4。

## Final candidate review 与验证交接

主代理实际完成 specification 与 engineering-quality 两轴审查，未运行 subagent、
独立 reviewer 或未调用的 review interface。逐一追踪 predicate-only right 经
condition rows/source candidates/relationship rebuild、结构 introductions、scalar
field partition 与所有 tail 入口；逐一追踪 UNKNOWN right 经 left-subset grain、
multifact candidates、aggregate linkage 与 effective replay。对 equal-evidence
self-use 的 prefix-role finding 已按 batch 8 修复，fresh rereview 无剩余 material
finding。Ponytail FULL/ponytail-review：现有 owner/kernel/shared caller 足够，未增加
module、property engine、scope registry、dependency graph、evaluator 或 later-Slice
scaffold；无可删的 speculative abstraction。

| Acceptance | Fresh witness / boundary |
| --- | --- |
| E03 / BAG / NULL | real-authored M1–M4、TRUE/FALSE/nullable Bool/OR/explicit NULL match；独立 BAG occurrence oracle 与 SQLite EXISTS/NOT EXISTS；右重复不增倍、左重复保留、partition/idempotence |
| Whole left / visibility | expanded/multihop hidden left、重复字段名、prior nulling；九类 tail negative scopes；后续 ON/FROM/VIA、RIGHT/FULL、重复存在性与 M1/M2 |
| Structural authority | both input slots/uses/dependencies、same-producer roles、foreign roots、stale prefix/allocation、wrong-role graft、精确 diagnostic retirement |
| Property / grain / safety | exact left key/FD/factor images；genuine FULL(two GLOBAL) UNKNOWN 经 replay 分别作左右输入；GLOBAL at-most-one/zero survival；UNKNOWN 左 typed terminal 与已有 fanout requirement |
| Vertical / public | 五类 completed tail outputs 作两侧输入、replay/JOIN、import/re-export、三种 check modes/JSON v2；single-file/LEGACY_FLAT/PACKAGE_ROOT/Explain/IR negatives 与 F01/F02 |

Final focused：Python 3.12/3.13 各 537 passed（principal 140）；batch-9 名称修正
后的独立 BAG oracle 1 passed。Affected direct-consumer/CLI/module/private observer/
differential suite 为 resource-aware `-n 4 --dist=loadfile` 的 1272 passed；
lifecycle/inventory 101 passed。Ruff 与 623-file format 均通过；production 与 test
Pyright 已各得到 0 errors，最终 exact candidate 再由 authoritative validator 覆盖。
Native OpenJDK/ANTLR reproducibility 验证 8 个 tracked files byte-for-byte，golden
audit 验证 39 fixtures，installed wheel/sdist/package/CLI smoke 全部成功。

实际 closure 为 A2/M17/D0，共 19 paths：7 个 ACTIVE core production、required
contract/principal、4 个 existing focused、4 个 guides 与 sole lifecycle/inventory
readers。无 contingency activation、无新 production module 或额外 test module，
无 published contract/differential manifest/grammar/AST/generated/golden/lock/workflow/
validator/public schema/SQL 变更。Phase 64 route 与后续 owner 不变。

Pre-validator accounting：corrective batches 9/20（1 production、8 test/evidence）；
authoritative starts 0/4；initial publication commits 0/1；CI repair children 0/2。
以下 authoritative validator 的每次 start/result 与 exact candidate tree、最终 seal/
commit/push/natural CI 事实保存为仓库外 operation ledger 与 Git/CI evidence。
未发生 validator observation interruption；所有已结束检查的 exit 均已恢复。
本文件不预写未知 commit/run，不需要 status-only follow-up commit。
