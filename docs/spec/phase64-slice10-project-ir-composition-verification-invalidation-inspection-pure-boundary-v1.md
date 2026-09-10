# Phase 64 Slice 10 Project IR Composition, Verification, Invalidation, Inspection And Pure Boundary v1

## Gate 0 与集成边界

main baseline `9333faeae1e544f1be70f17bfcb67d06fd57f9c4`，tree
`8646dd478445ec91ead181116a79d5e484294589`，parent
`73fcb2bcdbe27775fc3bf9500df8d68006a62578`，subject
`Add Phase 64 set operation semantics`。fetch 后 local/cached/live main 一致，
0/0、index/worktree/untracked 干净，无 active Git operation。自然 CI
`34305449725 / push / main / attempt 1 / success`；Python 3.12
`102321072675`、3.13 `102321072425` 的 validator/generated/golden/package 全成功。
Slice9 local 12416 passed / 0 skipped 与 CI 12412 passed / 4 skipped 分开保留。

D01–D08、D07-FLOAT-DEFERRED、S9-NAME-1、N=11、E01–E12 不变。本 Slice
只把既有 semantic products 带入 combined IR、verification/invalidation/private
observation；不重跑语义编译、不实现 SQLPlan/SQL/execution/optimizer/public API。

复用 Phase63 snapshot、dependency-first schedule、canonical owner ledger 与
显式 active_output/active_properties。历史 Phase61/62 roots 原样保留；只有实际
active-input 前提保持时才复用旧 IR。当前 JOIN prefix 与 tails 不能拼接独立
coordinates；在同一 project allocation owner 下建立 exact source-to-combined
node/output/use/field/grain 对应，再消费 canonical active upstream outputs。

一个新 private module project_query_block_ir_algebra 只分离该 correspondence
及 JOIN/set integration carriers，让 builder/verifier/observer 共同读取既有证据，
避免回到 semantic constructors。property/type/FD/grain 仍由现有 kernels 拥有。
SELECT tail 继续使用既有 stage builder；set 保持独立 non-SELECT semantic variant。
没有第二个 identity system、resolver、scheduler 或执行器。

| Producer | Retained authority | Combined consumer / independent check |
| --- | --- | --- |
| Completion topology and ledger | exact owner/dependency/schedule/terminal objects | canonical entry order; explicit active endpoints; blocked owner zero allocation |
| Current/historical JOIN regions | original joins, condition/use/scope, ordered refs/conjuncts and binary input pairs | dense remapped nodes/slots/uses; authored orientation, whole-side nulling, SEMI/ANTI right dependencies |
| Final SELECT/tails | exact LET/filter/group/window/QUALIFY/projection/order/limit evidence | existing unary stages and field images; no fabricated AST or hidden scalar |
| DISTINCT | exact clause/visible comparison/type/Decimal/full-row/order proofs and origin | operator after visible projection, before relation ORDER/LIMIT; no representative |
| Set operations | exact operation/quantifier/ordered repeated uses/positional fields and S9-NAME-1 | every operand targets active producer; separate value/membership maps; no flattening |
| Single-match assessments | original request occurrences, direct/hop/path joins, input pairs, proofs and diagnostics | complete composed-boundary mapping; PROVED/LEGAL_UNPROVED retained, INVALID has no executable positive owner |
| Properties/grain | STRICT/LAX, canonical classes/keys/FDs, UNKNOWN and exact factor sources | locality and correspondence, not a second derivation engine; no false GLOBAL or repaired risk |
| Verified graph | exact verified bundle and actual uses | existing reverse use/topology/reachability; changed semantic/proof/type root requires rebuild and fresh verification |

## Private observation contract

新增 marker `pietto.phase64-flat-relational-ir-inspection.v1`。原
`pietto.project-ir-inspection.v1`、`pietto.phase62-inspection.v1` 与
`pietto.phase63-query-block-ir-inspection.v1` 的未变输入保留旧格式/记录/bytes。
使用了当前新增 algebra/obligations 或新完成边界的 snapshot 使用新 marker；
旧 mixed corpus 中 stale JOIN / downstream terminal 正向迁移，不声称其 bytes 未变。

复用现有 portable typed refs、closed records、单一 encoder 和 total evaluator。
新 document 保留旧完整 owner/structure/operator/property/window/analysis sections，
并追加具名 closed evidence records：algebra operator（kind/quantifier/span）、
input correspondence（role/use/active producer）、field map（ordered input fields、
value/membership sources、nulling）、condition（scope/expression/base/refinement）、
reference（source order/state/complete candidates）、type/equivalence（canonical
identity/Decimal/source）、requirement（request ordinal/scope/unit/status/joins/
diagnostic）、proof（kind/exact producer/boundary roots）。这些是 document-local
records；portable equality 不等于 runtime identity。

所有事实保留实际 authored logical source/span，禁止 Python id/hash/repr、opaque
scope、cwd/clock/absolute temporary paths。pure validator 检查 arity、endpoints、
roles、order/multiplicity、active refs、complete evidence/property links 与 analyses；
malformed/unknown format 或 record deterministic fail closed/no bytes。pure OK 只
证明 document consistency，不重新证明数据库语义或执行 fulfillment。

## Gate 1 exact path freeze

首个 repository edit 前将本记录及 JSON path ledger 保存到仓库外。core 6；
additional existing production 12/12；new private modules 1/2；required files 2；
additional new focused tests 2/2；new differential probe 1/1；behavioral readers
12/12；historical/helper 12/12；lifecycle/guides 6。每个 CONTINGENCY 激活前记录
因果用途；未用容量不允许后加或替换路径。Slice9 swap 不带入本次授权。

| State | Category | Exact path | Purpose |
| --- | --- | --- | --- |
| ACTIVE | core | src/pietto/_project/project_query_block_ir.py | Combined construction/verification/observation and exact property images. |
| ACTIVE | core | src/pietto/_project/project_query_block_ir_verification.py | Combined construction/verification/observation and exact property images. |
| ACTIVE | core | src/pietto/_project/project_query_block_ir_inspection.py | Combined construction/verification/observation and exact property images. |
| ACTIVE | core | src/pietto/_project/project_query_block_ir_pure_boundary.py | Combined construction/verification/observation and exact property images. |
| ACTIVE | core | src/pietto/_project/project_ir_relational_properties.py | Combined construction/verification/observation and exact property images. |
| CONTINGENCY | core | src/pietto/_project/project_grain.py | Combined construction/verification/observation and exact property images. |
| ACTIVE | additional production | src/pietto/_project/project_ir.py | Typed set input use over the existing scope/ref/slot domains; preserve old use laws. |
| CONTINGENCY | additional production | src/pietto/_project/project_ir_construction.py | Existing dense allocation and historical fragment rebind adapter only. |
| CONTINGENCY | additional production | src/pietto/_project/project_ir_properties.py | Exact composed row/nulling property image admission only. |
| CONTINGENCY | additional production | src/pietto/_project/project_ir_evaluation_context.py | Existing grouped/context interface for remapped semantic witnesses. |
| CONTINGENCY | additional production | src/pietto/_project/project_ir_joins.py | Reuse existing JOIN field/key/FD/grain kernels under exact remapping. |
| CONTINGENCY | additional production | src/pietto/_project/project_current_join_inputs.py | Retained current input fields/properties to active producer correspondence. |
| CONTINGENCY | additional production | src/pietto/_project/project_current_joins.py | Retain original binary/prefix fields and conditions as IR witnesses. |
| CONTINGENCY | additional production | src/pietto/_project/project_final_outputs.py | SELECT/set final identity and property image integration only. |
| CONTINGENCY | additional production | src/pietto/_project/project_join_conditions.py | Exact operative condition/reference/input-role retaining adapter only. |
| CONTINGENCY | additional production | src/pietto/_project/project_single_match.py | Read validated direct/hop/path assessments and proof-root membership. |
| CONTINGENCY | additional production | src/pietto/_project/project_set_operations.py | Exact ordered operand/field/type/membership map integration only. |
| CONTINGENCY | additional production | src/pietto/_project/project_row_equivalence.py | Exact inherited capability/Decimal evidence image adapter only. |
| ACTIVE | behavioral reader | tests/test_phase64_slice2_generic_on_join_kinds_set_operation_grammar_ast_spans.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| CONTINGENCY | behavioral reader | tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| CONTINGENCY | behavioral reader | tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase64_slice9_set_output_composition_and_authority.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| CONTINGENCY | behavioral reader | tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | behavioral reader | tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py | Planned temporary-boundary migration; keep foreign-root and public negative controls. |
| ACTIVE | historical/helper | tests/_pietto_phase63_query_block_ir_differential_probe.py | Migrate the now-supported effective JOIN scenarios; preserve unchanged historical byte controls. |
| ACTIVE | historical/helper | tests/_pietto_differential_process_acquisition.py | Register Phase64 in the existing logical request/relocation manifest only. |
| ACTIVE | historical/helper | tests/_pietto_differential_probe_batch.py | Register the one new probe and ambient marker; no process policy change. |
| ACTIVE | historical/helper | tests/test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization.py | Account for the additive corpus family while preserving exact existing cells/requests. |
| ACTIVE | historical/helper | tests/test_validation_performance_interlude_ii_slice3_heavy_file_xdist_scheduling_isolation_decision.py | Separate the historical six-family 62 requests from the current additive registration. |
| CONTINGENCY | historical/helper | tests/test_validation_performance_interlude_slice2_differential_probe_runtime_decomposition_optimization.py | Old probe/differential dimensions remain behaviorally complete. |
| CONTINGENCY | historical/helper | tests/test_validation_performance_interlude_ii_slice1_post_phase63_baseline_profiling_cost_attribution_route_lock.py | Historical probe manifest observation reader only. |
| CONTINGENCY | historical/helper | tests/test_validation_performance_interlude_ii_slice4_completion_benchmark_phase64_readiness_assurance.py | Historical readiness/unsupported boundary reader only. |
| CONTINGENCY | historical/helper | tests/test_phase63_slice16_completion_audit_phase64_handoff.py | Historical source/closed format guard, without rewriting published contracts. |
| CONTINGENCY | historical/helper | tests/test_phase64_slice1_flat_relational_algebra_product_phase_initiation_gate_v3_source_audit_architecture_route_lock.py | Retain original route and prior boundary evidence as history. |
| CONTINGENCY | historical/helper | tests/test_compilation_boundary_qualify_admission.py | Preserve F01 negative public admission; only private IR reader if required. |
| CONTINGENCY | historical/helper | tests/test_completion_dependency_cycles.py | Preserve SCC/blocked ownership and zero-allocation terminals. |
| ACTIVE | new | src/pietto/_project/project_query_block_ir_algebra.py | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | new | docs/spec/phase64-slice10-project-ir-composition-verification-invalidation-inspection-pure-boundary-v1.md | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | new | tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | new | tests/test_phase64_slice10_ir_corruption_and_invalidation.py | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | new | tests/test_phase64_slice10_ir_observation_and_differential.py | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | new | tests/_pietto_phase64_flat_ir_differential_probe.py | One shared correspondence dependency boundary, contract, bounded retention/mutation/pure tests and differential corpus. |
| ACTIVE | lifecycle/guide | docs/status.md | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |
| ACTIVE | lifecycle/guide | docs/roadmap.md | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |
| ACTIVE | lifecycle/guide | docs/language.md | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |
| ACTIVE | lifecycle/guide | docs/spec/diagnostics.md | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |
| ACTIVE | lifecycle/guide | tests/test_active_phase_lifecycle.py | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |
| ACTIVE | lifecycle/guide | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py | Prospective Slice10 publication, Slice11 NEXT and sole inventory/lifecycle accounting. |

## Checkpoints、验证与预算

Baseline 新功能红例 4 failed：generic 输出为 current-JOIN terminal；DISTINCT、
sets、nonempty requests 在 builder guard 拒绝。所有 semantic checks 本身成功。
旧 combined IR/verifier/inspection/pure controls 21 passed / 6 deselected。
这些是 pre-implementation evidence，未使用 corrective batch 或 full validator。

1. Thin vertical：真实 effective-input generic INNER/LEFT -> combined graph ->
   independent VERIFIED analyses -> 最小真实新格式 observation；早期两 Pyright。
2. Complete retained algebra：全部 JOIN kinds、DISTINCT、six sets、private requests；
   同一机制处理 repeated/self inputs、both roles、imports/replays/mixed tails；此时
   就运行全部迁移 readers，避免把已知旧临时负例留到最终 broad。
3. Adversaries：missing/extra/reordered/swapped/foreign/stale field、type、condition、
   origin、uses、proof/obligation；invalidation 与 pure normalized failures；既有
   acquisition 添加一个 family，真实双 Python/四 hash seeds/relocated/wheel cells。

前台主代理 semantic/engineering + Ponytail review，无 subagents/background agents。
失败日志分类并保留；已知失败候选不 lucky rerun。final focused/direct readers/F01/F02
双 Python、affected broad、sole lifecycle/inventory、whole-tree Ruff/format、production
与 test Pyright、diff、native generated/golden/package，加一次 authoritative
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`，均绑定最终候选树。

Fresh counters：corrective batches 0/20、authoritative starts 0/4、initial commits
0/1、CI children 0/2；不继承 Slice9 额度。初始实现/计划迁移不计 repair；新 root
causes 单独累计。任何未列必需路径、预算耗尽、drift、无关既有缺陷或新 material
architecture/product/trust decision 都保留候选并 STOP。

全部 review/validation 通过才 seal、rebind live remote、stage exact tree、普通
commit `Complete Phase 64 flat relational Project IR`、ff push main，等待自然
final-exact-head push/main/attempt 1 双 Python 四项必需步骤全成功。无 amend、
rebase、force、manual CI、tag/release/sign/attest/status-only follow-up。

成功自然 CI 后 E05 支持域的剩余 IR boundary 与 E10 闭合，E12 提供 exact
condition/scope/field/type/obligation/active-output 消费证据。Phase64 ACTIVE，
Slices1–10 PUBLISHED，Slice11 NEXT/NOT IMPLEMENTED。Phase65 消费这些真实
roots/maps；不冻结 ProjectSQLPlan，不实现 Slice11 或 Phase65。


## Corrective ledger

Batch 1：03-first-vertical 的 current JOIN 在分类前进入 historical-only
_stale_join_inputs；先读取 exact current-region membership，再仅对历史路径检查
staleness。只改冻结的 project_query_block_ir.py，不放宽 historical region guard。
Repairs 1/20；authoritative starts 0/4；commits/CI children 0。

04-production-pyright 为 2 errors。Batch 2 补充 independent verifier 所用的确切
historical region type import；batch 3 修正 verifier active helper 的返回座位：
它已返回 ProjectIROutputValueOccurrence，直接比较该 object，不再读 .occurrence。
Repairs 3/20；authoritative starts 0/4；publication 未开始。

Batch 4：05-vertical 的 constructor/independent passes 已成功，但 verification
result 仍 blanket 拒绝 current_regions。改为要求每个 current positive owner 的
exact composed prefix；不允许用缺失 correspondence 的结果声称 VERIFIED。
Repairs 4/20；authoritative starts 0/4。

06-effective-vertical 的 4 cases 均已通过 constructor 与 independent verification，
停在 analysis builder 的旧 current-regions blanket guard。Batch 5 删除该临时
guard，仍只接受 exact VERIFIED result 并用既有 actual-use topology 检查/派生。
07-production-pyright 的 5 errors 分为两项：batch 6 在已确认 JOIN output 分支
直接取得其 typed row field；batch 7 用 relationship identity 的真实 module.path
保留 base-match logical source。Ruff 当前通过。Repairs 7/20；validator 0/4。

Batch 8：08-effective-vertical 在 pure property validator 拒绝实际
ProjectIRJoinedRowField source-kind；只在 Phase64 新 marker 允许该 exact variant，
Phase63 v1 接受域不变。旧 property locality/nulling/identity 验证继续执行。
Repairs 8/20；authoritative starts 0/4。


## Checkpoint 1 result

10-effective-vertical：4 passed（INNER/LEFT × both effective-input roles），真实
constructor -> independent VERIFIED -> combined analyses -> 新 marker document /
pure OK。Production Pyright（11）与 test Pyright（09）均 0 errors；Ruff 通过。
Gate1 已计划的 Slice4 reader migration 已实施：现在正向检查 exact prefix 与
VERIFIED，同时拒绝删除 prefix 后的 dense-allocation graft。12-reader-controls
为 40 passed，含该整文件与既有 field/window/property/foreign-root controls。
累计 repairs 8/20，authoritative starts 0/4，commits/CI children 0。

Checkpoint2 激活原 frozen CONTINGENCY
`src/pietto/_project/project_final_outputs.py`：把现有 DISTINCT quotient-grain
构造因式分解到 shared relational-property owner，semantic materialization 与
combined IR 读取同一规则。原 semantic witness、factor/origin 与输出含义不变；
该行为等价 factoring 属于计划内集成，不新增 repair。

13-production-pyright 为 2 errors。Batch 9 在 exact closed identity type guard
后显式窄化 dataclass locator；batch 10 从 ProjectRowEquivalence.evidence 读取
capability tuple，fields 仍是独立的 visible projection tuple。只改 frozen observer。
Repairs 10/20；authoritative starts 0/4；publication 0。

Batch 11：共享 DISTINCT/set capability record inventory 的编辑误删了
_distinct_records 的 signature 尾部与 operators 绑定，Ruff parse check 精确
报错 line 2699。保留 failed source 于仓库外，恢复同一 function 边界；不改语义。
Repairs 11/20；authoritative starts 0/4；commits/CI children 0。

Batch 12：Ruff F402 指出 set field-map loop 的 field 名称遮蔽 dataclasses.field
import；只重命名该局部循环变量。Repairs 12/20；authoritative starts 0/4。

Batch 13：17-production-pyright 指出 combined structural-use reader 的 closed
union 漏接 SET use；同一新 SET variant 的 caller 复查同时补足
_semantic_entry_identities 的 runtime dispatch（此前只扩了 annotation）。两个
helper 均在既有 QBI owner，完整接入同一新闭合 variant，不放宽历史 base-use union。
Repairs 13/20；authoritative starts 0/4。

18-set-vertical：12 passed / 8 failed，新增 sets 均已经通过 independent verifier，
失败在 reverse-use entry 的 runtime closed use family。Batch 14 补足 SET use
及相应 issue-coordinate reader；不改拓扑算法或去重 uses。19-test-pyright 为
0 errors。Repairs 14/20；authoritative starts 0/4。

20-set-vertical：20 passed。21-production-pyright 的两个 errors 属于同一
proof-boundary image 返回类型：exact historical membership 分支显式窄化为
ProjectIRBinaryJoinOccurrence，不把 semantic current JOIN 当 combined node。
记作 batch 15；累计 repairs 15/20、authoritative starts 0/4。

22-requirements：24 passed / 3 failed；失败仅历史 relationship/path 的新格式
operator owner linkage。实测 pure 拒绝 _validate_algebra 的 OUTPUT.owner：
历史 JOIN output 原 v1 没有 owner 映射。Batch 16 只在新 marker 下由已保留的
exact historical-match correspondence 填写 output/use consumer owner；旧 marker
仍保留原 bytes。23-production-pyright 为 0 errors。Repairs 16/20，validator 0/4。

## Adversarial finding set

25-composition 为 32 passed。26-adversaries 为 22 passed / 3 failed，冻结三个
独立 findings：batch 17 要求每个 external JOIN producer 来自 original source
的确切 owner，不能同时替换 use.output 与 producer；batch 18 独立逐项验证
完整 grain factor/active/dependency/source-factor 与 ref images，不能靠后续
一致复制掩盖原 grain 丢失；batch 19 将 portable DISTINCT ORDER-proof 数量
绑定实际 ORDER operator/property items，遗漏 proof 不得 pure OK。
全部只改 frozen verifier/pure owner；repairs 19/20，authoritative starts 0/4。

Batch 20：27-adversarial-recheck 为 34 passed / 23 failed，全部新增失败为
batch17 producer-owner 校验漏导入既有 _declaration_identity 导致的 NameError。
只补充 canonical identity helper import；累计 repairs 20/20，authoritative
starts 0/4、initial commits 0/1、CI children 0/2。该预算已耗尽；复核后按用户
STOP 条件保留未封存候选，不继续 reader/probe migration 或 publication。

## STOP — REPAIR_BUDGET_EXHAUSTED

第20批后 28-final-allowed-recheck 为 57 passed / 0 skipped；whole-tree Ruff、
format、diff check 通过。29-stop-production-pyright 仍有 1 error：verifier 的
producer-owner 分支在排除 ProjectIRStageFieldAnchor 前访问 anchor.identity。
只在仓库外保存 proposed-anchor-narrowing.patch，未应用。修复预算 20/20 已耗尽。

候选 A5/M8/D0，空 index；HEAD/main/origin/main 保留 Slice9 baseline。未 seal、
未启动 authoritative validator、未 commit/push、无 Slice10 CI。仅 Slice4 的
旧 reader 已迁移；其余已计划 reader/probe/differential/lifecycle 闭合与完整
复审、最终验证/出版仍未完成。此处不是 Slice10 PASS，不转移实现到 Slice11。
仓库外 stop.json 保存路径、计数、未修 finding 与最新日志。


## Preserved-candidate continuation

用户 continuation 仅接纳原 dirty candidate，并将 cumulative repair ceiling
从 20 提高到 32。原 batches 1–20、失败证据、exact-path freeze 与其他预算
保持不变。Rebind 确认 HEAD/main/cached origin/main/live main 均为
9333faeae1e544f1be70f17bfcb67d06fd57f9c4，tree/parent 与原记录一致，
local/remote 0/0、index 空、无 active Git operation。当前 A5/M8/D0 与 STOP
路径清单一致；STOP 未记录候选内容 hash，因此不声称逐字节连续性。

Retention matrix 与剩余工作复核：anchor correction 使用已修改的 verifier
及新 corruption test；剩余 behavioral readers、Phase63 probe、Phase64 probe、
acquisition/batch 注册、两个性能 reader、六个 lifecycle/guide 路径均已在原
Gate1 逐名冻结。只使用这些预留路径，未新增或交换 reservation。原 ACTIVE
路径按冻结用途进入后续计划内迁移；CONTINGENCY 仍须在实际需要时逐项激活。

Batch 21：只在 ProjectIRRelationAnchor 分支访问 identity；合法 intermediate
stage anchor 继续走其既有 producer/source 验证。补充 canonical producer
位置的 wrong-stage-anchor 拒绝，复用既有 final/window stage 正向测试。
累计 repairs 20 + 1 = 21/32；authoritative starts 0/4，initial commits 0/1，
CI children 0/2，尚未 seal/push。结果待本批实际检查完成后追加。

Batch 22：第21批的 unapplied patch 增加了实际文件中已经存在的
ProjectIRRelationAnchor import，Ruff F811 首先失败，Pyright/tests 尚未启动。
删除重复 import，不改变 guard；累计 22/32。

Batch21/22 检查结果：30 Ruff passed；31 production Pyright 与32 test
Pyright 均 0 errors；33 anchor tests 为16 passed，含合法 final/window stage
与 wrong-stage-anchor 拒绝。累计22/32，authoritative starts0/4。

开始原 ACTIVE behavioral reader 迁移：Slice2、5、6、7、8、9 composition、
Phase63 Slice14/15 及旧probe。只提升精确 private availability 断言，保留
legacy/public 与 foreign-root negatives。

34-readers：691 passed /3 failed。分别记录 batch23 更新 request occurrence
拒绝的具体消息断言（拒绝仍发生）；batch24 补全私有 extension enum 的
DISTINCT/SET_OPERATION 断言（旧 logical enum 不变）；batch25 修正新迁移
下游变体：actual completed SELECT tail 不是 historical rebound，仍要求
relation_input 绑定 exact active upstream output。旧 probe 同一变体迁移同步。
累计25/32，authoritative starts0/4；没有重计或删除既有 repairs。

原 ACTIVE probe/registration 路径已进入计划内实施：新增唯一 Phase64 probe，
在 acquisition family/relocation manifest、batch family/ambient、两个性能 reader
注册。现有6-family62 requests 保留，新增12 requests，cells仍16；不改缓存、
调度、隔离策略。旧 Phase63 的2个 effective-JOIN case 从terminal迁移为
completed；35-recheck105 passed，36-probe 实测2118 records/350845 bytes。
已核对 exact upstream/condition、semantic failure negatives；Phase61/62 bytes
摘要与旧值一致。新格式的旧 corpus 输出有变化，不宣称该 corpus byte兼容。

38-phase64-probe 发现完整删除 LEGAL_UNPROVED requirement 后，其 retained
PIE-S2337 warning 成为孤立记录却仍 pure OK。Batch26 在既有 requirement
validator 对 single-match diagnostic ref 与全部 request diagnostic refs 做
完整双向对应；不删除 warning、不改变 semantic assessment 或 format schema。
该 probe 的 full records/rejections case 为 regression；累计26/32。

39-probe recheck 已生成 proved/unproved/v1_control 的完整 records/bytes 与
normalized rejections。40 test Pyright4 errors 同属 reader 的 terminal union
未排除：batch27 用 existing terminal variant guard 收窄，再读取 active_output；
不使用 cast 或伪造属性。累计27/32。

41-review-adversaries：9 failed /27 deselected，冻结6个独立原因；不合并为
一个泛化“schema”修复。Batch28 为4个 historical match-view 反例：补足 exact
operative condition、source property、每个 input property 与 active producer
对应，保留原 nodes/uses/output 零分配。Batch29 绑定 condition mode 与既有
scope 枚举。Batch30 把全部 authored field-reference leaves（排除 call callee）
按原顺序/重复次数对应 retained reference expressions。Batch31 关闭 proof root
JSON family/字段，并检查其 owner/node/use/child 的 document-local associations。
Batch32 为 selected type identity：DISTINCT/SET/parents 共用 canonical field
locator 的结构检查，不能接受空 identity。每个原因独立计数，累计32/32。

ORDER proof 反例仍未修：visible_count 可被改为0而pure OK；审查同时确认
strict-FD semantic proof 实际为(item, determination)二元组，而 observer目前
只接受三元 visible proof，尚缺正向/反例闭合。Decimal alias 的最终
decimal_type_expr 也未在 portable evidence 显式保留。不得以当前定向结果
宣称 E05/E10、review 或 differential 全部完成。后续只记录末批检查及STOP，
不再修改实现/reader 或启动 authoritative validator/publication。

## Continuation STOP — REPAIR_BUDGET_EXHAUSTED

累计20 +12 =32/32。43-final-allowed-focused：50 passed /17 failed /0 skipped /
1 deselected（未启动 process-cell differential）。第32批新增 field identity guard
遗漏既有 SOURCE_FIELD="source_field"（module_attribution.py 的三种 closed
variants之一），造成合法 set/type 文档 invalid_document，17失败大多在
positive document construction，不能当作对应 corruption 已通过。

44-stop-production-pyright：1 error，verifier historical-view check 的条件
分支推导为 tuple[()]，conditions[0] 在line2610触发 reportGeneralTypeIssues。
45-stop-test-pyright：0 errors。42 Ruff通过；46 whole format635 files已格式化；
47 diff check通过。全部前台process已恢复终态，无第二validator或background agent。

第21批 original anchor blocker 已修；早期16 tests/两套typing通过。reader
迁移首次691 passed/3 failed，修正后相关105 passed；Phase63实际probe取得
完整 records/bytes，Phase64 probe在第26批后 proved/unproved/v1 control通过。
这些是各自当时的候选证据，不覆盖最后的失败候选。未完成真实全部cells、
最终两Python/readers/F01/F02/broad/lifecycle/inventory/generated/golden/package
或 authoritative validator。剩余已冻结guides/lifecycle尚未修改。

保留当前A6/M21/D0、27个exact-frozen路径，空index。HEAD/main/cached origin/main/
live main均为9333faeae1e544f1be70f17bfcb67d06fd57f9c4，0/0。没有candidate seal、
commit、push或Slice10 CI：authoritative0/4、initial commit0/1、CI child0/2。
原stop.json及batches1–20不改；仓库外continuation-stop.json记录本次全部路径、
最终每文件SHA256和失败证据。未完成E05/E10，不进入Slice11，不作PASS声明。


## Audit-bound portable-evidence convergence

本次仅处理审计C1–C7，写集为用户逐名指定的七个既有candidate路径。原
32批记录及STOP不改；累计上限39，无其他repair容量。authoritative/封存/
stage/commit/push/CI/lifecycle与Slice11均暂停。本单元结束即checkpoint STOP。
原candidate manifest adf905ab81477b7e51c4867eca7d9fad31dd9b4a225cc84acfd641c53745a812
逐文件匹配；HEAD/main/cached/live main与9333faea baseline一致，index空、
无活动Git操作。仍为原前台实现代理，审计不是独立第三方意见。

| Producer | Runtime authority | Phase64 portable record/ref | Structural decoder invariant |
| --- | --- | --- | --- |
| source/set/SELECT field identity | exact selected identity + explicit active field | TYPE_EQUIVALENCE.field -> ROW_FIELD，selected locator | owner/kind/position/name与该字段角色一致；source输入和canonical final结果分开 |
| final projection/set output | exact completed field and producing operator | ROW_FIELD -> property/output/operator | FINAL_PROJECTION/SET_OPERATION canonical field必须RELATION_OUTPUT；旧marker规则不改 |
| historical operative condition/property | original complete candidate tuples | existing runtime verifier only | _same_objects(tuple,(retained,))同时证明singleton和identity，0/多/缺失拒绝 |
| visible ORDER proof triple | exact item + ordered visible/target source objects | ORDER_SOURCE声明source；ORDER_BINDING固定item/source inventories；ORDER_PROOF visible引用binding与source refs；DISTINCT引用proof refs | 严格逐序关联binding/owner、source refs和multiplicity；counts仅派生，不按AST/name重解引用 |
| strict-FD ORDER proof pair | exact item + existing determination witness/index | ORDER_BINDING + ORDER_PROOF strict_fd，引用RELATIONAL_PROPERTY/VALUE_CLASS/VALUE_FD及原witness steps | 检查域/owner/property、seed/requested/closure/step既有引用与供应witness一致；不求新FD closure |
| Decimal direct/alias terminal | exact type resolution/alias chain/decimal_type_expr/(p,s) | TYPE_EQUIVALENCE parents refs；该family的TYPE_PARAMETER_SOURCE声明最小owner/role/logical span/parameters，capability引用source | source backlink、terminal alias/declared owner、参数和父链匹配；继承node允许无local terminal |

新增声明均使用现有closed record/ref encoder/evaluator机制，仅用于未发布
Phase64 marker；不建外部registry/新模块，不改semantic ORDER tuple producer。
ORDER两变体只在一个inspection adapter分派。TYPE_EQUIVALENCE父节点保留
自身source field identity，不强制等于当前output。旧Phase61/62/63 marker与
未变输入bytes保持。正向与malformed记录逐项对照上述矩阵后才作为证据。

### Convergence checkpoint evidence

Corrective entries分别为33=C1、34=C6、35=C7、36=C2、37=C3、38=C4、39=C5；
32 +7 =39/39。共享编辑仍分别记因。C5开发时修正了参数helper import、实际
继承fixture前提及test text窄化；C4修正optional ordering的窄化。旧批次不重计。

一次前台semantic/engineering + Ponytail复审确认C3 source模块、C4实际上游
property、C5 closed role/span仍需收紧，四个反例先失败；一次集中响应补足。
该响应脚本曾在写pure文件前中止，仅inspector部分落盘；中间97 passed/3 failed
保留，补完同一次既定响应后100 passed。额外paired controls证明重复ORDER
target保留两次、SET canonical final不能换SOURCE_FIELD。没有另开repair循环。

最终Python3.13和3.12均102 passed /0 skipped /1 deselected，三个Slice10文件
的唯一排除项为test_real_flat_ir_records_bytes_and_rejections_match_every_process_cell。
原17失败IDs均通过，旧masked mutations已到达其拒绝断言。Production/test
Pyright均0 errors，whole-tree Ruff/format/diff通过。validator/commit/CI child
仍0/4、0/1、0/2，push0。

正常3.13 Phase64 source-only probe仅执行一次，覆盖proved/unproved/imported
alias/strict-FD/v1-control；actual records/bytes/normalized failures保留。
集中响应后对保存的完整records用最终pure重新验证，五case canonical bytes
和normalized rejections相同，未重跑probe API。plain/window controls与
起始候选的Phase61/62/63完整bytes及Phase63 records相同。全部seed、relocation、
wheel/broad/full-validator/lifecycle/publication未执行，仍需后续明确continuation。

本记录仅为PORTABLE_EVIDENCE_CHECKPOINT_COMPLETE — NOT_PUBLISHED。
Slice10仍incomplete/unpublished，E05/E10不宣告闭合，Slice11未开始。


## FV01–FV04 compatibility closure continuation

用户仅授权三份behavior/probe文件的四项原因修正及随后原计划metadata、
验证、条件发布。40=FV01明确五case顺序；41=FV02逐installed cell核实际
package subtree归属并排除checkout；42=FV03按既有协议补main，仍复用唯一
render；43=FV04只迁移已越过旧边界的Phase63 fixture marker/观察预期。
累计39 +4 =43/43，无batch44或production修改权；CI child额度仍inactive。

起始manifest44400a6c38290865883451db6b201051c900431f4cb95f63b2c273698c2c5742
及27 paths/index/HEAD/tree/parent/cached/live main均匹配原STOP。仍为同一
前台实现代理，无第三方独立reviewer或background agent；旧receipts不改。

FV04在修改预期前用normal builders复核十个ROW_FIELD：56归ordered_limited；
81–83归mixed；108–109归replay_full；184–185归relation_order_added；187/189
归limit_one/limit_two。每个active field的semantic_source是原selected object，
其身份是同owner FINAL_PROJECTION的exact identity；在ORDER/LIMIT active
output上显式观察该身份，不继承另一source owner。差异仅这些final_*字段，
实际351210 bytes/2118 records；Phase61/62完整bytes未变。另用原未改的
Phase63 Slice13 POSITIVE_SOURCE，外部只读提取published HEAD src运行对照，
确认其Phase63-v1完整52134 bytes与current相同，再保留独立strict v1 control。
没有修改旧fixture输入、Phase63 probe、历史contracts或生产encoder。

### FV closure validation STOP

FV01–FV04的6个直接checks通过，test Pyright0 errors，三份行为文件Ruff/
format通过。随后复用原resource policy（本机选择serial fallback）执行68个
受影响文件、1685项：1684 passed/1 failed/0 skipped。完整Phase64 matrix
及此前三个失败nodes均通过，全部历史family通过既有lazy acquisition取得
16/16 global cells、74/74 logical requests：phase58=8、59–61各10、62–64各12。
Phase64五case完整records/bytes/rejections及逐cell installed origin均通过。

新失败为test_validation_performance_interlude_ii_slice2_differential_probe_process_acquisition_optimization.py
的test_specification_records_the_measured_optimization_and_closure：它将当前
七项acquisition.FAMILY_ORDER用于当时只含phase58–63的不可变Process Cell
Audit，因缺phase64文本失败。此为新的历史reader epoch绑定问题，不属于
FV03 standalone main修复，也不在本轮三个behavior写路径内。无batch44
授权，故不修改该reader/旧contract/acquisition；保留失败candidate并STOP。

累计43/43；authoritative0/4、ordinary commit0/1、CI children0/2 inactive、
push0。未启动后续3.12 broad、最终metadata/lifecycle、static/generated/golden/
package smoke、authoritative、seal或publication。生产及非授权candidate路径
仍与本轮起点字节一致；只有三份behavior/probe及本contract追加有变化。
Slice10未完成/未发布，E05/E10不作最终闭合声明，Slice11/65未开始。


## HR01 historical audit reader continuation

用户仅追加授权HR01 / batch44：历史Process Cell Audit断言使用明确的
phase58–phase63六family tuple。当前acquisition七family/74requests/16cells、
standalone/batch、原62requests历史数值和所有其他断言不变。不修改旧spec、
production、probe或acquisition policy。

起始EXIT manifest6afccff5ca6ea1706eae1e1036309bf0d7ada7d6a3b84777ca0466e4ac87f795
与实际27paths、index、HEAD/tree/parent/cached/live main一致；上轮broad测试
的是575e4e17f938dfd287eb78d3553e311d82ecbdf857a0e26fef6d4f459012615f，
其后仅contract追加STOP，两个manifest不混用且都不是Git seal。旧43批历史
及receipts保留。累计44/44；无batch45或CI child修复权。一个前台实现代理，
不是第三方独立review。直接checks后继续原验证/metadata/条件发布，不另开
permission checkpoint；新独立失败仍STOP。

### HR01 direct-check STOP

明确six-family断言通过后，同一node继续在Changed-Path And Lifecycle Lock
处失败：assert all(name in modified for name in DIFFERENTIAL_TESTS)。当前
DIFFERENTIAL_TESTS含7个文件，但不可变M18历史清单不含后来新增的
tests/test_phase64_slice10_ir_observation_and_differential.py。此后续file-inventory
断言未修改；它不是本次指定family断言的import/format/type清理。没有
batch45授权，保留candidate并停止后续broad/metadata/authoritative/publication。

3.13与3.12直接检查均3 passed/1 failed；当前registry/cell与standalone/batch
协议三个controls通过。新失败node仍为test_specification_records_the_measured_optimization_and_closure，
失败位置已移到line539。旧spec、live registry、production/probes及FV/C1–C7
行为文件未改。累计44/44，authoritative0/4、commit0/1、inactive CI children0/2、
push0。未创建candidate seal或Git tree，Slice10仍未完成/未发布。


## HR02 complete historical/current input separation continuation

用户追加授权HR02 / batch45，取代HR01仅限family断言的范围。先读完整历史
test、section helpers及全部输入/consumers；历史family与历史文件membership
为两处时期边界。保留HR01的六family tuple；历史M18 membership改用明确的
六份phase58–phase63 differential文件，逐项与不可变原closure核对。函数其余
历史计数、timings、process算术、路径检查和最终lifecycle断言不变。当前七
family/74requests/16cells、完整DIFFERENTIAL_TESTS及所有live controls不变。

起始EXIT manifest3fd8eb03ae5fd63c304fa63b40b4720d9758c1afa6e0a44b9d2231cb595b51f9
与27paths逐文件匹配，index空且bytes不变，HEAD/tree/parent/cached/live main
仍为原9333faea baseline。旧broad-tested575e4e17及旧EXIT6afccff5分别保留，
均不是Git seal。累计44 +HR02 =45/45，无独立batch46；authoritative0/4、
ordinary commit0/1、CI children0/2 inactive、push0。production/probes与其他
candidate文件保持起始bytes。一个前台代理执行及复审，不称独立第三方review。

本次先跑整个reader文件的3.13/3.12，再恢复原broad与完整行为复审；通过后
才更新七个既定metadata路径及执行原final checks，全部成功则按原条件封存、
普通commit/fast-forward push与natural exact-head CI，无额外permission pause。


## Interruption recovery — EXTERNAL_JOIN_PRODUCER_OMISSION_ACCEPTED

恢复会话核对实际候选与原执行记录：HR02 / batch45已经完成，完整reader在
Python3.13和3.12均10 passed /0 skipped /0 deselected、exit0；其输入manifest为
5925e174fa61ff4c5c001195cfe31aae161a3ac40cf3543506af2b3bba0e65b0，恢复时27个
候选文件的manifest与之完全一致。未重做HR02或重跑已通过的reader。原HR02
随后启动68文件3.13 broad，但中断后没有可恢复的终态；宿主机已重启，无
残留Pietto writer/validator。原/tmp回执目录缺失，相关命令、退出状态和测试
摘要从原会话执行记录恢复；缺失的完整日志不冒称仍在，也不把中断记作PASS。

恢复后只补该未观察到终态的3.13 broad，使用既有resource policy选择
-n7 --dist=loadfile：1685 passed /0 failed /0 skipped /0 deselected，68文件、
131.70s、exit0。完整Phase64 matrix已执行；实际七family共74requests/16cells，
phase58=8、59–61各10、62–64各12，包含真实双Python/hash seeds/relocated/
isolated-wheel origins。此证据仍绑定上述manifest，不覆盖本段结果追加。

前台code-verification及Ponytail候选审查发现一个新的生产pure-decoder原因：
project_query_block_ir_pure_boundary._validate_algebra仅在producer.ref非None时
核对其active_output，缺少对外部输入producer缺失的拒绝。真实lhs.id == r.id
JOIN经normal builders、独立VERIFIED及inspection产生合法文档；分别仅把左、
右INPUT_CORRESPONDENCE.producer改为ABSENT，两个结果均仍OK并返回canonical
bytes。仓库外最小反例exit1，明确违反显式active producer/input mapping的
完整性要求。已有测试只删除整组correspondence records，未覆盖单字段遗漏。
内部累计JOIN输入允许producer缺省，不能以全局改成required替代正确的边界
区分。此结论是文档一致性缺口，不声称数据库执行或公共CLI已受影响。

本项不属于HR02历史函数时期隔离，也不属于metadata；未修改生产、probe或
行为测试，无batch46授权，按恢复约定STOP。修复方向需在既有decoder区分
内部累计输入与外部active producer，并补同一观察测试文件的遗漏/合法内部
输入反例；这里仅记录方向，未应用修复、未删除断言或缩减matrix。

累计repairs45/45，authoritative starts0/4，initial commit0/1，CI children0/2
INACTIVE，push0。HEAD/main/cached/live main仍为9333faea基线，A6/M21/D0，
index为空且bytes不变；没有Git seal/candidate tree/commit/CI。本轮仓库写入仅
本contract追加结果，全部生产与行为字节保持恢复输入。剩余3.12-parent broad、
最终完整review、六路径metadata闭合、最终static/generated/golden/package及
authoritative validation均未完成；不作E05/E10或Slice10最终PASS声明。
恢复回执、实际矩阵、反例与最终manifest保存于仓库外
/tmp/pietto-phase64-slice10-recovery-w0eihsvs。Phase64保持ACTIVE，Slice10未发布，
Slice11与Phase65未开始。


## JPC01 JOIN producer-correspondence closure continuation

用户仅追加JPC01 / batch46：在现有pure decoder一次闭合external/internal JOIN
input correspondence，保留原format/encoder/valid bytes。累计45+1=46/46；
authoritative0/4、commit0/1、CI children0/2 INACTIVE、push0，旧批次不重做。
起始EXIT f3e8cd3c280c76a7efd09b03c6c3ce50448400c105bb6e2fb7cc987c0230856a
逐文件匹配，原TEST 5925e174单独保留。HEAD/main/cached/live均9333faea基线，
index为空且bytes不变，无残留validator或competing writer。旧丢失临时日志按
既有恢复记录处理，不编造其结果。

已读完整INPUT_CORRESPONDENCE schema、_validate_algebra及ref/shape/owner/
property/topology helpers，对照只读runtime verifier、carrier和encoder：USE
保留owner/output/slot，slot保留consumer/ordinal，OUTPUT保留producer-node/owner，
ALGEBRA保留owner/node/output/ordered inputs，OWNER_ENTRY保留active output及
active property。首个左输入与各外部右输入必须显式指向被消费的active owner；
self-use可共享producer但不能合并use。累计prefix通过先前同owner JOIN record
及其output->producer-node->当前use/slot链证明，不能用ABSENT或坐标猜测。
局部修正只使用这些已保留链接，不新增schema/marker/encoder或semantic计算。

本批写集仅pure decoder、现有Slice10 observation test和本contract追加。计划
小矩阵覆盖direct/self/named-completed/set输入、累计prefix、外部遗漏/错误/
dangling/terminal producer及伪装internal的错owner/非前驱/self/forward链接。
合法原文档先通过再变异；原whole-record与C1–C7 controls保留。修复后双Python
局部checks/两typing，再原68文件双parent broad/full differential，完成原复审
才进入既定metadata及最终验证/条件发布；新独立原因仍STOP，无batch47授权。


### JPC01 results and planned publication closure

JPC01在同一_validate_algebra路径核对use.owner/slot.consumer及输入端点。
已验证的前一个同owner ALGEBRA与当前左input通过明确output/producer-node链接
证明累计输入；它保留原ABSENT producer。其他输入必须有非terminal producer，
并与OUTPUT.owner、OWNER_ENTRY.active_output及active_property对应；self-use
仍保留两个不同use。无schema/encoder/marker变化，无推导或补填producer。

19个JPC01节点覆盖六种输入形态与external/internal/owner/endpoint反例。
首轮7 failed/12 passed中，6项是真实遗漏或use-owner反例，1项是新test的
historical v1前提错误（它没有新增correspondence）。改为保留历史JOIN、带
合法DISTINCT的Phase64文档后，三个Slice10文件123 passed/1 matrix deselected。
首个fixed run的122 passed/1 setup failure保留，不冒称production回归。
修前/修后六份完整合法bytes相同，包含原historical v1控制；仅本批decoder和
指定test改变，所有其他生产、encoder、probe、acquisition、HR02 reader不变。

早期production/test Pyright均0 errors；changed-file Ruff/format通过。
原68文件受影响选择在3.13-parent和3.12-parent各1704 passed /0 failed /
0 skipped /0 deselected，分别101.87s和134.01s；每次使用独立调用内acquisition
实际取得七family/74requests/16cells。Phase64全matrix、真实interpreter/
startup seeds/relocated/isolated-wheel origin/full records/bytes/rejections均
实际执行。3.12-parent的JPC01、direct readers和F01/F02由该broad直接覆盖，
不以3.13-parent中的3.12 children替代。此前1685-pass仍只属于修前输入。
本批behavior-tested manifest为
53ea98304a894cc9c34f72533440e371cfe689316901684dd4d05519f2604ae8，后续本段和
metadata修改与该输入分开；content manifest不是Git seal。

原中断的semantic/engineering复审及Ponytail review已完成，当前无剩余确认
finding；同一前台执行链，不称第三方独立review。完整候选按原语义边界覆盖
以下验收与消费事实，最终发布仍须下述完整validation及natural CI成功。

| Exit / boundary | Concrete retained evidence and actual acceptance |
| --- | --- |
| E05 supported active-input IR closure | effective generic INNER/LEFT两角色、accumulated RIGHT/FULL、grouped->LEFT->window/QUALIFY、UNION ALL->JOIN->DISTINCT->replay；独立verifier与JPC01检查exact active owner/output及内部prefix，支持域不再被旧临时JOIN terminal阻断 |
| E10 operation and property retention | CROSS absence、M1–M4 condition/base/refinement/reference order、whole-side nulling、SEMI/ANTI左输出及右use、STRICT/LAX key/FD、GLOBAL/UNKNOWN/quotient/alternative/subset grain；missing/extra/swapped/foreign证据反例及完整field/ORDER/Decimal controls |
| E10 set and obligation closure | six set forms、ordered repeated/self uses、EXCEPT右membership、canonical set-owned fields、direct/hop/whole-path PROVED/LEGAL_UNPROVED/INVALID及原diagnostic identity；blocked owner零新分配、独立valid branch保留 |
| E10 verification/invalidation/observation | 独立passes不调用builder重建预期；combined reverse uses/topology/reachability覆盖实际依赖；semantic/property/proof root改变需overlay rebuild及fresh verification；observer只消费exact VERIFIED bundle；total closed pure rejection/no bytes及全cell差分 |
| Historical compatibility | 未变Phase61/62/63输入保持旧完整records/bytes；已提升旧boundary的Phase63 fixture按FV04明确迁移，未改其输入或假称旧bytes相同；F01/F02与public negative controls保持 |
| E12 / later planning consumption | Phase65可消费exact active endpoints、authored orientation/conditions/scopes、ordered operand uses和positional field/type/value/membership maps、nulling/key/FD/grain origins、ORDER/Decimal证明及未履行的single-match obligations；没有冻结ProjectSQLPlan或实现SQL/execution |

既定七metadata路径进入最终closure：本contract、status、roadmap、language、
diagnostics及两个sole lifecycle/inventory owners。当前production Python由
186到187、test Python由440到444；唯一新增production为原冻结algebra helper，
三个新test加一个probe。完整候选A6/M27/D0，共33paths；不修改任何其他文件。
最终lifecycle/inventory、whole-tree format/Ruff、两Pyright、native generated、
39golden、final-build-input package/CLI smoke和authoritative validator须通过
才seal/stage/普通commit/ff push，实际结果与Git seal保存于仓库外回执。
自然final-exact-head push/main/attempt1双Python全部必需步骤成功才完成发布；
不追加status-only commit，不使用基线CI代替候选CI。

成功链条仅使Phase64保持ACTIVE、Slices1–10 PUBLISHED、Slice11 NEXT /
NOT IMPLEMENTED。VERIFIED及pure OK不证明single-match运行时履行、数据库语义
或SQL/execution。Slice11 completion audit与Phase65仍未实施。


### JPC01 final-validation STOP — HISTORICAL_CAPABILITY_TOKEN_GUARD

最终metadata候选manifest
1f1d98d174277a2238c62af628c4e8d54f390d82ebe1f1c286e285c71fb3f87b上，sole
lifecycle/inventory/reader guard104 passed；native生成8文件逐字节一致，39golden
审计通过，final-input sdist/wheel及隔离安装CLI smoke通过。首次authoritative
`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`运行至完整终态：
lockfile、635文件format、Ruff、production/test Pyright均通过；全测试
12542 collected，12541 passed /1 failed /0 skipped /0 deselected，tests144.74s，
validator总205.649s，exit1。当前资源策略选择-n2 --dist=loadfile；未覆盖或
取消运行，未重复启动authoritative。累计starts1/4，不退回0。

唯一失败node为
`tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py::test_only_private_window_strategy_is_new_compiler_capability_consumer`，
line900按原始文本禁止capability_。bounded只读诊断枚举原排除清单后的全部
命中，只有project_query_block_ir_inspection.py与project_query_block_ir_pure_boundary.py，
来自_capability_data/_capability_field/_capability_records及_type_capability_key/
_capability_field_matches/_capability_key等本地row-equivalence evidence helpers。
两个文件均无compiler capability模块import；原测试保护的lookup入口与module
stem断言通过。对该函数全部341次断言predicate做不改变文件的只读观测，仅
line900为False；这是诊断枚举，不是额外pytest通过或替代失败gate。

这些helper名称在JPC01起点候选中已经存在，9333faea baseline的两个文件中
尚无该token。该失败属于历史静态reader将通用本地命名与compiler capability
subsystem消费混同；不是external/internal JOIN correspondence修复。原68文件
broad不含这个Phase52文件，所以不把其1704-pass误作完整validator成功。

该reader不在JPC01写集或七metadata路径中，无batch47授权。未修改reader、
重命名生产helper规避检查、重跑失败候选或追加通用repair。最小后续方向是
基于已有repository AST事实检查实际compiler capability import/lookup consumer
边界，保留真实负例保护；这里只记录，未应用。

保留已完成metadata及全部JPC01生产/测试bytes，本次之后仅本contract追加
失败事实。最终content manifest与上述测试输入区分，保存于仓库外stop.json。
累计repairs46/46、authoritative1/4、ordinary commit0/1、CI children0/2 INACTIVE、
push0；index为空且原bytes不变。没有candidate Git seal/tree/commit或natural CI。
HEAD/main/cached/live仍为9333faea基线。status/roadmap使用的conditional
publication表述没有使Slice10实际发布；Phase64 ACTIVE、Slice10未完成/未发布，
Slice11与Phase65未实施。恢复材料和本轮完整回执位于
/tmp/pietto-phase64-slice10-jpc01-2b24leo3，历史失败记录不改写。


## CCG01 compiler-capability guard correction continuation

用户显式将一个既有路径加入当前effective修改闭合：
`tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py`。
这是CCG01 / batch47新增授权，不回写原Gate1列表，不复活旧reservation；
JPC01及1–46批不重做。累计46+1=47/47，authoritative保留已失败start1/4，
ordinary commit0/1、CI children0/2 INACTIVE、push0。起点EXIT
 daa652a302569a58eaabe0a64eb8996c5a353fbd7008ff152b58f15dc8b368a3
逐文件匹配；index为空且原bytes不变，local/cached/live均9333faea，无残留
validator或竞争writer。原12541passed/1failed/exit1永久保留为失败证据。

完整target函数、module constants、相邻privacy/dynamic-import guards及Phase52
scope/foundation ownership已读。assertions分类：第一loop的五lookup入口与
qualified semantic module检查保护真实消费边界；第二loop的通用capability_
文本禁令是过宽代理；后续指定consumer的正负import/lookup组合以及相邻模块
privacy/__all__/dynamic-import限制是具体边界，原意与例外清单均保留。
旧loop完整命中只有inspection与pure boundary中的row-equivalence/Decimal
helpers；它们无compiler capability imports/lookup，不构成新consumer。

保护身份在test文件内明确冻结：既有MODULE_RELS的十个semantic capability
模块，以及原_project边界中的capability_availability/checking/matrix/
inspection/pure_boundary、package_capability_requirements、project_capability_environment。
lookup身份为原五lookup-input APIs、lookup_capability与canonical_capability_provider_inputs。
复用RepositoryFactIndex/PythonSourceFacts的imports/identifiers/string literals，
仅为import facts未保留的from-import/relative拼写补充狭窄的本地syntax读取。
qualified/aliased/parent from-import/relative与明确protected module literals均
受检查；不以generic capability_字样、局部helper或注释作为新consumer证据。
两个原目录loop和授权consumer例外不变，收集完整path/reference violations后
统一assert；不将两个命中文件加入例外，不迁移policy到shared facts helper。

新增同文件guard controls使用pytest临时目录中先写好的NamedTemporaryFile，
再由真实RepositoryFactIndex取得facts；不写入或修改被扫描的repository文件。
production、decoder、verifier、encoder、probe、acquisition和其他behavior tests
均冻结于起点bytes。现有七metadata closure保持，仅本contract记录path/acceptance
accounting；预期A6/M28/D0共34paths，Python文件数量仍187/444。

复用JPC01两parent1704-pass/16cells/74requests及既有semantic review，只声明其
真实输入。CCG01完整Phase52 reader与guard controls及直接acquisition guard将
双Python新验证；完成早期lint/format/test typing及最终metadata后，后续结果
只记仓库外回执，避免append/revalidate循环。最终完整validator下一次必须记
start2；通过全部原gates及新guard后才按原授权seal/普通commit/ff push/natural
exact-head CI，无额外permission pause。新独立原因或路径需求仍STOP，无batch48。


### CCG01 reviewed correction and final candidate boundary

CCG01保留原两次rglob范围、全部authorized consumer例外、相邻privacy/
__all__/dynamic-import guards，以及consumer-specific正负断言。第一loop的原
五lookup token与qualified semantic module检查等价纳入完整violations清单；
补充source-fact依赖检查。第二loop用同一predicate保护semantic十模块及
project七模块，替代通用capability_文本禁令。全部path/reference命中收集后
统一assert；没有新增例外或first-match遗漏。

普通qualified/aliased imports由shared import事实保留；parent from-import
模块名由identifier事实与必要的ImportFrom语法补充；relative forms使用既有
package位置和stdlib resolve_name。明确的protected module literal仍拒绝，
通用注释、无关literal及六种local row-equivalence helper names允许。predicate
只做该test-local边界检查，不承诺一般Python动态名解析或taint分析。

完整Phase52 reader、24个snippet控制、两个真实helper控制及直接repository
reader-acquisition guard，在Python3.13与3.12分别88 passed /0 failed /
0 skipped /0 deselected（6.82s、6.87s）；测试通过真实RepositoryFactIndex读取
先写入的独立临时snippet，未修改shared helper或生产。changed-file lint/format
及early test Pyright通过。旧失败guard的两个命中是本地row-equivalence helpers，
不是compiler capability imports；原authoritative start1仍为FAIL，不更名重计。

AST复核证明其他既有function不变，target原consumer exception sets与后续
consumer-specific assertion suffix原样保留。prior semantic/engineering review
与JPC01双parent1704-pass/16cells/74requests保留为其精确输入证据，未另跑两份
broad或独立matrix。完整累积候选的既有E05/E10/E12验收映射及本guard delta已
复审，当前无剩余确认finding；仍为同一前台代理，不称第三方独立review。

本轮只修改明确新增的Phase52 reader与本contract追加；其余生产、probe、
validator/acquisition/shared facts、JPC01及已完成六metadata路径全部保持起点
bytes。实际最终closure为A6/M28/D0，共34paths；production/test Python文件
仍187/444，无额外路径、无新Python文件、无language/diagnostic变更。
早期CCG01测试manifest为
 e48751b426eeb3c2707f5ad1c7f7f791aed8c02e298dde5367cdaba37e456a0b；本段追加后
最终manifest另存仓库外。后续final lifecycle/static/generated/golden/package及
累计authoritative start2的结果只保存到仓库外
/tmp/pietto-phase64-slice10-ccg01-tiojs2kf，不再以contract追加造成重验证循环。
全部最终gates通过才封存Git tree、精确stage、一个ordinary commit与ff push，
然后以natural exact-head push/main/attempt1双Python必需步骤判定发布。
未获成功链前不宣告最终PASS；成功后Phase64 ACTIVE、Slices1–10 PUBLISHED、
Slice11 NEXT/NOT IMPLEMENTED，SQL/执行及运行时single-match履行仍不在本Slice。
