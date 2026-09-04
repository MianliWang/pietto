# Phase 63 Completion Audit And Phase 64 Handoff v1

## Decision

Phase 63 **Joined Query Block Semantic Completion And QUALIFY** 的 15 项物质
出口均已由现有产品、principal tests、不可变 Git 对象和 natural exact-head
CI 支撑。Slice 16 只做文档与静态 assurance，不新增产品语义。

本地 publication candidate 阶段：

```text
Phase 63 = ACTIVE / COMPLETION CANDIDATE
Slices 1–15 = COMPLETED / PUBLISHED
Slice 16 = CURRENT / COMPLETION CANDIDATE
Phase 64 = NOT STARTED
```

本 Slice 的 natural exact-head CI 成功后，无需 status-only follow-up commit：

```text
Phase 63 = COMPLETED
Slices 1–16 = COMPLETED / PUBLISHED
Phase63 material exits = 15/15
Phase63 self-owned-open = 0
Phase 64 = NEXT / NOT IMPLEMENTED
```

Phase 64 仍未激活，没有 numbered Slice route，也没有实现。

## Starting Authority

Gate 0 重新绑定的唯一 live baseline 为：

```text
commit = e1590be595f9218341c74a830f611170bfc6092a
tree = 7708b722af9e601bee62bd852593086a6c89e802
parent = 23c9d9c4e657501b07664c7f65ee4e455ff7bb0f
subject = Add Phase 63 query-block IR inspection
natural CI = 33903599417
event / branch / attempt / conclusion = push / main / 1 / success
Python 3.12 job = 101123180491 / success
Python 3.13 job = 101123180303 / success
```

`HEAD == origin/main == FETCH_HEAD == live remote main`，divergence 为 `0/0`，
worktree、index、untracked inventory 均为空，没有 active Git operation，且
`NUL` absent。

续行授权前没有 candidate：

```text
documentation/test repairs = 0/12
mechanical closure paths = 0/12
authoritative validator starts = 0/4
production mutations = 0
changed paths = 0
commit = 0
push = 0
new CI = 0
```

用户纠正的前置 publication-lineage 假设属于 evidence correction，不计 repair
batch。

## Numbered Route Closure

| Slice | Exact owner | Candidate state |
| ---: | --- | --- |
| 1 | Product Gate v3, Pietto/external source audit, Future Roadmap, route lock | COMPLETED / PUBLISHED |
| 2 | Query-block owner bridge, row-source sum, states, mode boundary | COMPLETED / PUBLISHED |
| 3 | Scalar-reference environment, resolution facts, type-kernel adapter | COMPLETED / PUBLISHED |
| 4 | Bindings, visible joined fields, qualified/unqualified lookup | COMPLETED / PUBLISHED |
| 5 | LET, stage namespace lattice, shadowing and alias laws | COMPLETED / PUBLISHED |
| 6 | Post-JOIN row semantics, nullability, lineage and property bridge | COMPLETED / PUBLISHED |
| 7 | Completion scheduling, effective-output ledger foundation, module propagation | COMPLETED / PUBLISHED |
| 8 | Joined row filtering | COMPLETED / PUBLISHED |
| 9 | Joined grouping, aggregate, GLOBAL, satisfying and risk linkage | COMPLETED / PUBLISHED |
| 10 | Generic window-computation sites and named-window reuse | COMPLETED / PUBLISHED |
| 11 | QUALIFY grammar, AST, semantics and property transfer | COMPLETED / PUBLISHED |
| 12 | Projection, ordering, limit, final output and ledger completion | COMPLETED / PUBLISHED |
| 13 | Completed project semantic result and public check boundaries | COMPLETED / PUBLISHED |
| 14 | Query-block Project IR composition, verification and invalidation | COMPLETED / PUBLISHED |
| 15 | Inspection/pure boundary and real E2E/differential/metamorphic assurance | COMPLETED / PUBLISHED |
| 16 | Completion audit and Phase-64 handoff | CURRENT / COMPLETION CANDIDATE |

## Corrected First-Parent Publication Ledger

Phase-62 terminal `d9a423fe6822ed549e3063299a4781cd7ed4b480` 是 exact
merge base。到 Slice-15 terminal 共 `19` 个 first-parent commits，当前 terminal
相对 base 为 ahead/behind `19/0`。每个 commit 恰有一个 parent，无 merge、无
rewritten predecessor。

| # | Role | Commit | Tree | Parent | Subject | Natural run | Python 3.12 | Python 3.13 | Publication state |
| ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Slice-1 failed implementation head | e5b790b0b1c516bbeb2aac0833d209afe1b83811 | 5134d48db2e86d1e09740d6c97937c280c6e3ae6 | d9a423fe6822ed549e3063299a4781cd7ed4b480 | Add Phase 63 joined query-block route lock | 33690102213 | 100446638955 / failure | 100446639356 / failure | push/main/attempt 1/failure |
| 2 | Slice-1 repair child and terminal | e90e8eb5c3fcee12fb932773959e9b862968776e | d8b54927e1a36840c39f6c693b2aa0cf4d1ce3fc | e5b790b0b1c516bbeb2aac0833d209afe1b83811 | Fix Phase 63 route-lock shallow CI portability | 33693963322 | 100458702267 / success | 100458702526 / success | push/main/attempt 1/success |
| 3 | Unnumbered architecture extraction | 9edcd34ec5526e94ad11c7be03a3329b7510a39f | b7ea670b5d2fbd25b1087515be914ce330ded471 | e90e8eb5c3fcee12fb932773959e9b862968776e | Extract repository architecture authority | 33700551496 | 100478703692 / success | 100478703743 / success | push/main/attempt 1/success |
| 4 | Unnumbered dependency-direction correction | 6d9756e4c8279cd0c435f4a4cb73537604facd78 | 8c22b8a8c5dbf6072cb6e6edd8e43f80e4bec94b | 9edcd34ec5526e94ad11c7be03a3329b7510a39f | Correct architecture planning dependency direction | 33702605149 | 100484917268 / success | 100484917477 / success | push/main/attempt 1/success |
| 5 | Slice 2 terminal | 6de9f741e848443a3acee996e4a27e23d2377f2f | 86a9eb5269123da465cb1d646655b4ab5763d747 | 6d9756e4c8279cd0c435f4a4cb73537604facd78 | Add Phase 63 query-block foundation | 33708448662 | 100502606667 / success | 100502606913 / success | push/main/attempt 1/success |
| 6 | Slice 3 terminal | 1a2e2482870cd26eb3bae103b008d310b9bbd51f | 8611019db93eb520e4c6e2566da58524debac9cd | 6de9f741e848443a3acee996e4a27e23d2377f2f | Add Phase 63 scalar reference foundation | 33716105707 | 100525506665 / success | 100525506857 / success | push/main/attempt 1/success |
| 7 | Slice 4 terminal | 095c8e27cfc23c7fe0e520628c51c1ade884d318 | acd03a63aa28d303baa70b7438f052718823630d | 1a2e2482870cd26eb3bae103b008d310b9bbd51f | Add Phase 63 joined scalar bindings | 33718336042 | 100532126969 / success | 100532126826 / success | push/main/attempt 1/success |
| 8 | Slice 5 terminal | b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0 | 51fbc7b00ba1f86823d5ac94614051eb5ca6c104 | 095c8e27cfc23c7fe0e520628c51c1ade884d318 | Add Phase 63 joined LET namespaces | 33721542236 | 100541531022 / success | 100541531143 / success | push/main/attempt 1/success |
| 9 | Slice 6 terminal | b3e31fa697919155396e7437e9bfe8d52866dc70 | 7ccaa64f281f91cb4537d45db2b77dd0ca01ceec | b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0 | Add Phase 63 joined row semantics | 33725329642 | 100552928039 / success | 100552927866 / success | push/main/attempt 1/success |
| 10 | Slice 7 terminal | 9de90b395452a60f8efcdb570e2578cd40e489fb | 80d5b9e06fccaae8c436250e9a8fe31be828db71 | b3e31fa697919155396e7437e9bfe8d52866dc70 | Add Phase 63 completion foundation | 33729260966 | 100565237673 / success | 100565237795 / success | push/main/attempt 1/success |
| 11 | Slice 8 terminal | 9984669e5be79d775906b18052c3e0cc16d112ea | 7894b6d57375e193af8d3291325b34eb5ed589b4 | 9de90b395452a60f8efcdb570e2578cd40e489fb | Add Phase 63 joined row filtering | 33734174516 | 100580739912 / success | 100580740172 / success | push/main/attempt 1/success |
| 12 | Slice-9 successful semantic implementation | adb1c7efde895f0d213ba233369ced0702e618d1 | 4438cf13ad727c5aac9a9a91c5c209d9240a893d | 9984669e5be79d775906b18052c3e0cc16d112ea | Add Phase 63 joined aggregation | 33742777004 | 100608277745 / success | 100608277561 / success | push/main/attempt 1/success |
| 13 | Slice-9 reconciliation child and terminal | fb0e4584730d44e72598d6fb26a9afeca7e2b699 | c2c14dfb1e57669cf3257f904798824a0990f436 | adb1c7efde895f0d213ba233369ced0702e618d1 | Reconcile Phase 63 Slice 9 closure evidence | 33764259970 | 100677973573 / success | 100677973531 / success | push/main/attempt 1/success |
| 14 | Slice 10 terminal | 4b984f8c8578bcd7abd42db80fa8ead294d49f8f | 582a4e974cc6068847edf31a68e2ffdda01c1235 | fb0e4584730d44e72598d6fb26a9afeca7e2b699 | Add Phase 63 joined window computations | 33778747491 | 100726921396 / success | 100726921559 / success | push/main/attempt 1/success |
| 15 | Slice 11 terminal | 3f0a5435aa14d7b6ca23348b28c5b966f745c04f | be7f7c7dc1f36ed0a7aed1a4561d33eb17fd21ec | 4b984f8c8578bcd7abd42db80fa8ead294d49f8f | Add Phase 63 QUALIFY semantics | 33831892060 | 100896447555 / success | 100896447459 / success | push/main/attempt 1/success |
| 16 | Slice 12 terminal | 0d1d66badc2cf901d35876b360a25a9c36a829b3 | 01817712dd0cdbf7fd6ce7a1a3442dabf9bf637f | 3f0a5435aa14d7b6ca23348b28c5b966f745c04f | Complete Phase 63 final relation outputs | 33845906404 | 100937629132 / success | 100937629007 / success | push/main/attempt 1/success |
| 17 | Slice 13 terminal | 8b56db95ab45933d05db2123b3e89fb81b8ac2fa | c07493ab11dcf308a0cde01f9ef33a567096eb3c | 0d1d66badc2cf901d35876b360a25a9c36a829b3 | Add Phase 63 completed project semantics | 33855263140 | 100966972688 / success | 100966972586 / success | push/main/attempt 1/success |
| 18 | Slice 14 terminal | 23c9d9c4e657501b07664c7f65ee4e455ff7bb0f | 34e654d856463cc6aa63fbf4cc3591e788c1e493 | 8b56db95ab45933d05db2123b3e89fb81b8ac2fa | Add Phase 63 query-block Project IR | 33877240716 | 101037032127 / success | 101037032178 / success | push/main/attempt 1/success |
| 19 | Slice 15 terminal | e1590be595f9218341c74a830f611170bfc6092a | 7708b722af9e601bee62bd852593086a6c89e802 | 23c9d9c4e657501b07664c7f65ee4e455ff7bb0f | Add Phase 63 query-block IR inspection | 33903599417 | 101123180491 / success | 101123180303 / success | push/main/attempt 1/success |

精确角色方程为：

```text
15 final numbered Slice terminals
+ 2 unnumbered architecture publications
+ 1 preserved failed Slice-1 implementation head
+ 1 successful non-terminal Slice-9 semantic implementation
= 19 first-parent commits
```

成功 terminal 与两项 unnumbered publication 均为 natural
`push/main/attempt 1/success` 且 Python 3.12/3.13 成功。唯一失败 pushed head
是单独分类的 `e5b790b0...`；failed heads = 1，successful repair children = 1，
manual reruns = 0，merge commits = 0。

## Numbered Slice Terminal Ledger

| Slice | Final terminal | Tree | Natural CI | Status |
| ---: | --- | --- | --- | --- |
| 1 | e90e8eb5c3fcee12fb932773959e9b862968776e | d8b54927e1a36840c39f6c693b2aa0cf4d1ce3fc | 33693963322 | COMPLETED / PUBLISHED |
| 2 | 6de9f741e848443a3acee996e4a27e23d2377f2f | 86a9eb5269123da465cb1d646655b4ab5763d747 | 33708448662 | COMPLETED / PUBLISHED |
| 3 | 1a2e2482870cd26eb3bae103b008d310b9bbd51f | 8611019db93eb520e4c6e2566da58524debac9cd | 33716105707 | COMPLETED / PUBLISHED |
| 4 | 095c8e27cfc23c7fe0e520628c51c1ade884d318 | acd03a63aa28d303baa70b7438f052718823630d | 33718336042 | COMPLETED / PUBLISHED |
| 5 | b6af2573f0e10b377fea1d4b3eed2eb92dbc1ab0 | 51fbc7b00ba1f86823d5ac94614051eb5ca6c104 | 33721542236 | COMPLETED / PUBLISHED |
| 6 | b3e31fa697919155396e7437e9bfe8d52866dc70 | 7ccaa64f281f91cb4537d45db2b77dd0ca01ceec | 33725329642 | COMPLETED / PUBLISHED |
| 7 | 9de90b395452a60f8efcdb570e2578cd40e489fb | 80d5b9e06fccaae8c436250e9a8fe31be828db71 | 33729260966 | COMPLETED / PUBLISHED |
| 8 | 9984669e5be79d775906b18052c3e0cc16d112ea | 7894b6d57375e193af8d3291325b34eb5ed589b4 | 33734174516 | COMPLETED / PUBLISHED |
| 9 | fb0e4584730d44e72598d6fb26a9afeca7e2b699 | c2c14dfb1e57669cf3257f904798824a0990f436 | 33764259970 | COMPLETED / PUBLISHED |
| 10 | 4b984f8c8578bcd7abd42db80fa8ead294d49f8f | 582a4e974cc6068847edf31a68e2ffdda01c1235 | 33778747491 | COMPLETED / PUBLISHED |
| 11 | 3f0a5435aa14d7b6ca23348b28c5b966f745c04f | be7f7c7dc1f36ed0a7aed1a4561d33eb17fd21ec | 33831892060 | COMPLETED / PUBLISHED |
| 12 | 0d1d66badc2cf901d35876b360a25a9c36a829b3 | 01817712dd0cdbf7fd6ce7a1a3442dabf9bf637f | 33845906404 | COMPLETED / PUBLISHED |
| 13 | 8b56db95ab45933d05db2123b3e89fb81b8ac2fa | c07493ab11dcf308a0cde01f9ef33a567096eb3c | 33855263140 | COMPLETED / PUBLISHED |
| 14 | 23c9d9c4e657501b07664c7f65ee4e455ff7bb0f | 34e654d856463cc6aa63fbf4cc3591e788c1e493 | 33877240716 | COMPLETED / PUBLISHED |
| 15 | e1590be595f9218341c74a830f611170bfc6092a | 7708b722af9e601bee62bd852593086a6c89e802 | 33903599417 | COMPLETED / PUBLISHED |

## Unnumbered Publication Ledger

| Publication | Commit | Tree | Parent | Natural CI | State |
| --- | --- | --- | --- | --- | --- |
| Repository architecture authority extraction | 9edcd34ec5526e94ad11c7be03a3329b7510a39f | b7ea670b5d2fbd25b1087515be914ce330ded471 | e90e8eb5c3fcee12fb932773959e9b862968776e | 33700551496 | push/main/attempt 1/success |
| Architecture dependency-direction correction | 6d9756e4c8279cd0c435f4a4cb73537604facd78 | 8c22b8a8c5dbf6072cb6e6edd8e43f80e4bec94b | 9edcd34ec5526e94ad11c7be03a3329b7510a39f | 33702605149 | push/main/attempt 1/success |

两行是 completed/published prerequisites，不是 numbered Slices。

## Slice-1 Failed-Head And Repair-Child Lineage

`e5b790b0b1c516bbeb2aac0833d209afe1b83811` 是保留的 failed Slice-1
implementation head；其 natural run `33690102213` 是
`push/main/attempt 1/failure`，两个 Python jobs 都失败且没有 manual rerun。

`e90e8eb5c3fcee12fb932773959e9b862968776e` 是普通 successful repair
child，不是 amend 或 rerun。它的 parent 是 failed head，exact child delta 为：

```text
M tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py
```

它只修复 principal 的 shallow-CI Git-object portability；没有 production、
grammar、generated、public、package、dependency、workflow、SQL、Arrow、executor
或 Slice-2 behavior delta。Natural run `33693963322` 为 attempt 1 success。

原 Slice-1 contract 中 intended single-commit publication 是历史意图；最终
authority 是 failed head + repair child 的 live Git/CI lineage。Slice-1 numbered
terminal 只有 `e90e8eb5...`。

## Slice-9 Successful Intermediate And Reconciliation Lineage

Slice 9 与 Slice 1 不同：`adb1c7efde895f0d213ba233369ced0702e618d1`
及 CI `33742777004` 已成功发布 semantic implementation；
`fb0e4584730d44e72598d6fb26a9afeca7e2b699` 及 CI `33764259970`
是 successful evidence-reconciliation child 和最终 numbered Slice-9 terminal。

Child delta 是 exact M2：

```text
M docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md
M tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py
```

Slice-8 terminal 到 Slice-9 terminal 的 cumulative delta 是 exact `A3/M5/D0`；
reconciliation child 没有 production semantic bytes。它不是 failed-head repair。

## Immutable Historical Delta Law

每一项历史 Slice delta 只允许：

```text
historical_slice_delta = immutable_slice_start..immutable_slice_terminal
```

禁止使用 `historical_slice_start..current_HEAD`。Slice 1 分别保留 failed head、
M1 child 与 cumulative terminal；Slice 9 分别保留 semantic implementation、M2
child 与 cumulative terminal。Shallow CI 只能 narrow skip unavailable Git-object
assertion，static product/exit/handoff assurance 仍必须执行。Tests 不访问网络。

## Complete Product Inventory

| Slice | Exact owner | Immutable contract | Principal test | Production/source authorities | Final publication | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Product Gate v3, Pietto/external source audit, Future Roadmap, route lock | `docs/spec/phase63-joined-query-block-product-architecture-source-audit-future-roadmap-route-lock-v1.md` | `tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py` | architecture/route authority; no production owner | `e90e8eb5` / `d8b54927` / CI `33693963322` | COMPLETED / PUBLISHED |
| 2 | Query-block owner bridge, row-source sum, states, mode boundary | `docs/spec/phase63-slice2-query-block-owner-bridge-row-source-sum-states-mode-boundary-v1.md` | `tests/test_phase63_slice2_query_block_owner_bridge_row_source_sum_states_mode_boundary.py` | `src/pietto/_project/project_query_block.py` | `6de9f741` / `86a9eb52` / CI `33708448662` | COMPLETED / PUBLISHED |
| 3 | Scalar-reference environment, resolution facts, type-kernel adapter | `docs/spec/phase63-slice3-scalar-reference-environment-resolution-facts-type-kernel-adapter-v1.md` | `tests/test_phase63_slice3_scalar_reference_environment_resolution_facts_type_kernel_adapter.py` | `src/pietto/_project/project_scalar_references.py`<br>`src/pietto/_project/row_expression_type_facts.py` | `1a2e2482` / `8611019d` / CI `33716105707` | COMPLETED / PUBLISHED |
| 4 | Bindings, visible joined fields, qualified/unqualified lookup | `docs/spec/phase63-slice4-bindings-visible-joined-fields-qualified-unqualified-lookup-v1.md` | `tests/test_phase63_slice4_bindings_visible_joined_fields_qualified_unqualified_lookup.py` | `src/pietto/_project/project_scalar_bindings.py` | `095c8e27` / `acd03a63` / CI `33718336042` | COMPLETED / PUBLISHED |
| 5 | LET, stage namespace lattice, shadowing and alias laws | `docs/spec/phase63-slice5-let-stage-namespace-lattice-shadowing-alias-laws-v1.md` | `tests/test_phase63_slice5_let_stage_namespace_lattice_shadowing_alias_laws.py` | `src/pietto/_project/project_scalar_namespaces.py` | `b6af2573` / `51fbc7b0` / CI `33721542236` | COMPLETED / PUBLISHED |
| 6 | Post-JOIN row semantics, nullability, lineage and property bridge | `docs/spec/phase63-slice6-post-join-row-semantics-nullability-lineage-property-bridge-v1.md` | `tests/test_phase63_slice6_post_join_row_semantics_nullability_lineage_property_bridge.py` | `src/pietto/_project/project_joined_row_semantics.py` | `b3e31fa6` / `7ccaa64f` / CI `33725329642` | COMPLETED / PUBLISHED |
| 7 | Completion scheduling, effective-output ledger foundation, module propagation | `docs/spec/phase63-slice7-completion-scheduling-effective-output-ledger-module-propagation-v1.md` | `tests/test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation.py` | `src/pietto/_project/project_completion.py` | `9de90b39` / `80d5b9e0` / CI `33729260966` | COMPLETED / PUBLISHED |
| 8 | Joined row filtering | `docs/spec/phase63-slice8-joined-row-filtering-v1.md` | `tests/test_phase63_slice8_joined_row_filtering.py` | `src/pietto/_project/project_joined_row_filter.py`<br>`src/pietto/_project/project_scalar_namespaces.py` | `9984669e` / `7894b6d5` / CI `33734174516` | COMPLETED / PUBLISHED |
| 9 | Joined grouping, aggregate, GLOBAL, satisfying and risk linkage | `docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md` | `tests/test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage.py` | `src/pietto/_project/project_joined_aggregation.py` | `fb0e4584` / `c2c14dfb` / CI `33764259970` | COMPLETED / PUBLISHED |
| 10 | Generic window-computation sites and named-window reuse | `docs/spec/phase63-slice10-generic-window-computation-sites-named-window-reuse-v1.md` | `tests/test_phase63_slice10_generic_window_computation_sites_named_window_reuse.py` | `src/pietto/_project/project_joined_windows.py`<br>`src/pietto/semantic/window_analysis.py`<br>`src/pietto/semantic/window_navigation_analysis.py`<br>`src/pietto/semantic/window_semantics.py` | `4b984f8c` / `582a4e97` / CI `33778747491` | COMPLETED / PUBLISHED |
| 11 | QUALIFY grammar, AST, semantics and property transfer | `docs/spec/phase63-slice11-qualify-grammar-ast-semantics-property-transfer-v1.md` | `tests/test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer.py` | `grammar/Pietto.g4`<br>`src/pietto/ast_nodes.py`<br>`src/pietto/ast_builder.py`<br>`src/pietto/_project/project_joined_qualify.py` | `3f0a5435` / `be7f7c7d` / CI `33831892060` | COMPLETED / PUBLISHED |
| 12 | Projection, ordering, limit, final output and ledger completion | `docs/spec/phase63-slice12-projection-order-limit-final-output-ledger-completion-v1.md` | `tests/test_phase63_slice12_projection_order_limit_final_output_ledger_completion.py` | `src/pietto/_project/project_final_outputs.py`<br>`src/pietto/_project/project_joined_qualify.py` | `0d1d66ba` / `01817712` / CI `33845906404` | COMPLETED / PUBLISHED |
| 13 | Completed project semantic result and public check boundaries | `docs/spec/phase63-slice13-completed-project-semantic-result-public-check-boundaries-v1.md` | `tests/test_phase63_slice13_completed_project_semantic_result_public_check_boundaries.py` | `src/pietto/_project/project_completed_semantics.py`<br>`src/pietto/cli.py` | `8b56db95` / `c07493ab` / CI `33855263140` | COMPLETED / PUBLISHED |
| 14 | Query-block Project IR composition, verification and invalidation | `docs/spec/phase63-slice14-query-block-project-ir-composition-verification-invalidation-v1.md` | `tests/test_phase63_slice14_query_block_project_ir_composition_verification_invalidation.py` | `src/pietto/_project/project_query_block_ir.py`<br>`src/pietto/_project/project_query_block_ir_verification.py`<br>`src/pietto/_project/project_ir_relational_properties.py`<br>`src/pietto/_project/project_ir_evaluation_context.py`<br>`src/pietto/_project/project_grain.py` | `23c9d9c4` / `34e654d8` / CI `33877240716` | COMPLETED / PUBLISHED |
| 15 | Inspection/pure boundary and real E2E/differential/metamorphic assurance | `docs/spec/phase63-slice15-inspection-pure-boundary-real-e2e-differential-metamorphic-assurance-v1.md` | `tests/test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance.py` | `src/pietto/_project/project_query_block_ir_inspection.py`<br>`src/pietto/_project/project_query_block_ir_pure_boundary.py` | `e1590be5` / `7708b722` / CI `33903599417` | COMPLETED / PUBLISHED |

每个 contract、principal、source authority 与 final publication 都已绑定；所有
private owners 继续 private，只有 Slice 11 的 QUALIFY authored clause 和 Slice 13
既有 project-check consumer 位于已冻结的 public behavior boundary。

## Phase-63 Material Exit Ledger

| Exit | Exact criterion | Evidence owner | Status |
| --- | --- | --- | --- |
| E01 | Product Gate v3、architecture/source audit、Future Roadmap v6、route lock 与 repository architecture authority 完成 | Slice 1 + two unnumbered publications | SATISFIED |
| E02 | Exact declaration/query-block bridge、row-source sum、compilation-mode boundary 与 closed concrete/non-concrete states 完成 | Slice 2 | SATISFIED |
| E03 | Occurrence-complete scalar-reference environments、0/1/N resolution facts 与 existing scalar type kernel reuse 完成 | Slice 3 | SATISFIED |
| E04 | Exact joined bindings、visible/hidden partition、qualified lookup 与 winner-free unqualified lookup 完成 | Slice 4 | SATISFIED |
| E05 | POST_JOIN_INPUT -> LET_BINDING(i) -> POST_LET namespace chain、shadowing、collision、self/forward-reference 与 alias laws 完成 | Slice 5 | SATISFIED |
| E06 | Post-JOIN row semantics、effective nullability、nulling provenance、existing lineage identity 与 exact Phase-62 property bridge 完成 | Slice 6 | SATISFIED |
| E07 | Dependency-first completion schedule、one-entry-per-owner effective-output ledger、module propagation 与 no-new-JOIN recovery boundary 完成 | Slice 7 | SATISFIED |
| E08 | Joined WHERE analysis、SQL TRUE-only retention 与 conservative property preservation 完成 | Slice 8 | SATISFIED |
| E09 | GROUPED/GLOBAL aggregation、satisfying、exact group protection、fanout/chasm risk linkage 与 fail-closed aggregate-algebra boundary 完成 | Slice 9 | SATISFIED |
| E10 | Generic selected/hidden window sites、occurrence-neutral kernel、exact named-window reuse 与 post-window readiness 完成 | Slice 10 | SATISFIED |
| E11 | QUALIFY grammar/AST、post-window lookup、hidden inline windows、Bool semantics、TRUE-only retention 与 conservative property transfer 完成 | Slice 11 | SATISFIED |
| E12 | Final projection、relation ORDER、LIMIT、canonical field identity、semantic effective outputs 与 downstream no-JOIN replay 完成 | Slice 12 | SATISFIED |
| E13 | Completed project semantic result、exact final diagnostics、EXPLICIT_MODULES project-check success boundary 与 JSON-v2 compatibility 完成 | Slice 13 | SATISFIED |
| E14 | Explicit active-output/active-properties query-block IR overlay、property/grain transfer、independent verification、analyses 与 invalidation 完成 | Slice 14 | SATISFIED |
| E15 | VERIFIED-only inspection、winner-free queries、additive pure format、total evaluator、real authored E2E、Python differential、isolated wheel 与 metamorphic assurance 完成 | Slice 15 | SATISFIED |

```text
Phase63 material exits = 15/15
```

Slice 16 是 lifecycle/audit closure，不新增 E16。

## Open-Marker Classification

| Marker family | Classification | Result |
| --- | --- | --- |
| TODO / FIXME / TBD | Phase-63 product sources/contracts/principals 中无 unresolved marker | SATISFIED |
| Historical CURRENT / NEXT / NOT IMPLEMENTED | Immutable Slice-local lifecycle provenance，不是 current authority | SATISFIED |
| Historical repair / STOP / budgets | Immutable workflow evidence，不是 product work | SATISFIED |
| UNKNOWN / BLOCKED / AMBIGUOUS / DEFERRED / non-concrete / terminal | Intentional typed runtime evidence | SATISFIED |
| AUTHORED_JOIN_DEFERRED | Historical fact 保留；Phase-63 completed semantics/effective output/IR 已叠加完成 | SATISFIED / NOT WHOLESALE TRANSFERRED |
| Phase-64 flat-relational subjects | Exact Phase-64 owner | TRANSFERRED |
| Other future/later subjects | Future Roadmap v6 exact owner | TRANSFERRED |

```text
Phase63 self-owned-open = 0
```

## Exact Phase-64 Transfers

| Transferred subject | Owner | State |
| --- | --- | --- |
| Generic JOIN over arbitrary completed/effective row sources | Phase 64 | NOT IMPLEMENTED |
| Generic authored ON/refinement | Phase 64 | NOT IMPLEMENTED |
| Relationship base condition vs JOIN-local refinement vs WHERE/satisfying/QUALIFY separation | Phase 64 | NOT IMPLEMENTED |
| CROSS JOIN | Phase 64 | NOT IMPLEMENTED |
| RIGHT JOIN | Phase 64 | NOT IMPLEMENTED |
| FULL JOIN | Phase 64 | NOT IMPLEMENTED |
| SEMI JOIN | Phase 64 | NOT IMPLEMENTED |
| ANTI JOIN | Phase 64 | NOT IMPLEMENTED |
| DISTINCT | Phase 64 | NOT IMPLEMENTED |
| UNION | Phase 64 | NOT IMPLEMENTED |
| INTERSECT | Phase 64 | NOT IMPLEMENTED |
| EXCEPT | Phase 64 | NOT IMPLEMENTED |
| Single-match enforcement | Phase 64 | NOT IMPLEMENTED |
| EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED | Phase 64 | NOT IMPLEMENTED |
| EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED | Phase 64 | NOT IMPLEMENTED |

`AUTHORED_JOIN_DEFERRED` 不被整体转移；它继续是历史事实。Aggregate algebra
也不转移到 Phase 64。

## Exact Other Later-Owner Ledger

| Owner | Exact retained subject |
| --- | --- |
| Phase 65 | Target-neutral ProjectSQLPlan、parameters、source maps、legality 与 capability requirements |
| Phase 66 | PostgreSQL/MySQL baseline multi-relation SQL 与 Project emit-SQL |
| Phase 67 | Arrow interchange foundation 与 Pietto result contract |
| Phase 68 | Executor SPI、ADBC/DBAPI、streaming、cancellation 与 backpressure |
| Phase 69 | Public alpha/release engineering 与 unified safe entrypoints |
| Phase 70 | Open/composite plans、nonrecursive CTE/subqueries、VALUES/table functions、outer captures、EXISTS/IN、LATERAL、bounded decorrelation 与 effect authority |
| Phase 71 | NestedRelation、Collect、Unnest、flatten、outer/inner grain 与 nested Arrow |
| Phase 72 | Advanced equality/types/nullability 与 temporal/range/ASOF relationships |
| Phase 73 | Aggregate algebra/state、grouping extensions、fanout-safe reaggregation 与 AGGREGATE_ALGEBRA_REQUIRED |
| Phase 74 | Reusable local semantic assets、derived relationships 与 function/plugin SPI |
| Phase 75 | Formatter、LSP、editor、diagnostics、syntax editions 与 migrations |
| Phase 88 | Logical optimizer memo 与 join-order/hypergraph search |
| Phase 89 | Physical strategies including Yannakakis/WCOJ/Free Join/predicate transfer |
| Tentative Phase 91 | Persistent incremental-cache identity 与 incremental/differential Project IR |
| Tentative Phase 92 | Recursive relations、fixpoints、iterative planning 与 bounded recursive provenance |

Slice 16 不改变 Future Roadmap v6 ownership。

## Public And Compatibility Exit

| Boundary | Exact finding | Result |
| --- | --- | --- |
| Package/CLI version | `0.1.0` | UNCHANGED |
| Authored language | QUALIFY 是 Phase 63 唯一新增 authored clause | COMPLETE |
| Project check | EXPLICIT_MODULES 消费 completed project semantics | COMPLETE |
| Historical result | `ProjectSemanticResult` 保持不变 | COMPATIBLE |
| Text success bytes | 保持不变 | COMPATIBLE |
| Project JSON | v2 top-level schema/keys 保持不变 | COMPATIBLE |
| Single-file check | 保持不变 | COMPATIBLE |
| LEGACY_FLAT / PACKAGE_ROOT | 保持兼容、typed fail-closed | COMPATIBLE |
| Project Explain | 无变化 | UNCHANGED |
| `_project` exports | `__all__ == ()`，private | PRIVATE |
| Query-block carriers | IR、verification、inspection、pure carriers 均未 public expose | PRIVATE |
| Phase-61 format | `pietto.project-ir-inspection.v1` | UNCHANGED |
| Phase-62 format | `pietto.phase62-inspection.v1` | UNCHANGED |
| Phase-63 format | `pietto.phase63-query-block-ir-inspection.v1` | ADDITIVE / PRIVATE |
| SQL | 未启用 multi-relation SQL emission | NOT IMPLEMENTED |
| Arrow/runtime | 未启用 Arrow/result runtime contract | NOT IMPLEMENTED |
| Execution/optimization | 无 executor、optimizer、physical plan 或 backend selection | NOT IMPLEMENTED |
| Release surface | 无 package/dependency/lockfile/workflow/tag/Release/signing/attestation change | ZERO DELTA |
| Lifecycle publication | 不需要 status-only follow-up commit | CLOSED BY NATURAL CI |

Private canonical bytes 只用于 observation；不是 semantic、runtime、Project-field、
rewrite、cache 或 content identity。

## Phase-64 Inherited Assets

| Inherited asset | Readiness | Exact authority |
| --- | --- | --- |
| Product/Phase Initiation Gate v3 procedure | READY | Phase-63 Slice-1 contract |
| Repository architecture and layering laws | READY | Four architecture documents + AGENTS.md |
| Module/declaration identities and resolution | READY | Existing Project catalogs/resolution |
| Relationship identities, paths, conditions and match guarantees | READY | Phase 62 |
| Occurrence-complete joined row shapes | READY | Phase 62 + Phase-63 Slice 6 |
| Effective nullability and null-extension provenance | READY | Phase 62 + Slice 6 |
| Candidate keys, strict/lax FDs, value classes and FD indexes | READY | Phase 62 + Slice 14 transfer |
| Factorized intrinsic grain and dependency kernels | READY | Phase 62 + Slice 14 transfer |
| Fanout/chasm/multifact evidence | READY | Phase 62 + Slice 9 linkage |
| Completed WHERE/GROUP/WINDOW/QUALIFY/final-output semantics | READY | Slices 8–12 |
| Project-wide effective-output ledger | READY | Slices 7 and 12 |
| Completed project semantic result and final diagnostics | READY | Slice 13 |
| Exact active IR output/property mapping | READY | Slice 14 |
| Phase-61/62/63 combined structural topology | READY | Slice 14 |
| Independent verifier and invalidation | READY | Slice 14 |
| Combined reverse-use/topological/reachability analyses | READY | Slice 14 |
| VERIFIED-only inspection and winner-free queries | READY | Slice 15 |
| Additive Phase-63 pure observation format | READY | Slice 15 |
| Real-authored Python 3.12/3.13 differential harness | READY | Slice 15 |
| Isolated-wheel/relocation/hash-seed assurance | READY | Slice 15 |
| Fail-closed typed terminal patterns | READY | Slices 7, 12–15 |

READY 只表示可继承 authority 存在，不表示 Phase-64 features 已实现。Generic ON、
additional JOIN kinds、DISTINCT、set operations 与 single-match enforcement 均
`NOT IMPLEMENTED`。

## Phase-64 Mandatory Initiation Questions

Phase-64 Slice 1 必须 fresh review live source/external evidence，并先回答：

1. 哪个 exact row-source sum 接纳 source、historical relation output、completed effective output、JOIN result、DISTINCT result 与 set-operation result，同时不把所有 output 晋升为 relationship endpoint？
2. 哪个 identity 表示独立于 relationship traversal/path identity 的 generic JOIN occurrence？
3. 如何严格分离 relationship base condition、traversal/VIA、generic ON/refinement、WHERE、satisfying 与 QUALIFY？
4. CROSS、RIGHT、FULL、SEMI、ANTI 的 exact output-shape/null-extension laws 是什么？
5. SEMI/ANTI 如何保留 left occurrence identity 与 BAG multiplicity，而不发布 right fields？
6. DISTINCT 的 row-equivalence 与 NULL semantics 是什么，如何区别于 predicate equality？
7. UNION/INTERSECT/EXCEPT 是 positional、name-aligned 还是 explicitly mapped；ALL/distinct、type/nullability、multiplicity、provenance、ordering、key/FD 与 grain laws 是什么？
8. Single-match enforcement 是 semantic contract、runtime error possibility 还是 cardinality assertion；为什么不能由 LIMIT 1 推导？
9. 新 flat operators 如何接入 active-output ledger、explicit roots、verification、invalidation、inspection 与 pure boundary？
10. 哪些 key/FD/grain kernels 可复用而不创建 second property engine？
11. 哪些 operations 在 Phase 64 保持 target-neutral，而 ProjectSQLPlan/backend legality 继续属于 Phase 65+？
12. Phase-64 publication 前必须有哪些 adversarial、differential 与 metamorphic cases？

Slice 16 不回答这些 architecture questions，不冻结 Phase-64 numbered route。

## Reader And Inventory Ownership

唯一 mutable lifecycle-document reader 仍是
`tests/test_active_phase_lifecycle.py`。Slice-16 principal 只消费本 immutable
contract、explicit source 与 Git objects；它不读取、不命名、不重建 mutable
lifecycle-document paths。Dedicated inventory reader 继续独占 current whole-repo
Python inventory；principal 只保留 immutable transition `179 -> 179` 与
`421 -> 422`，不做动态 inventory scan。Tests 不访问网络。

## Zero-Delta Boundary

```text
production delta = 0
grammar / generated delta = 0
public API delta = 0
CLI behavior delta = 0
Project JSON schema delta = 0
SQL delta = 0
Arrow / executor / optimizer delta = 0
package / dependency / lockfile / workflow delta = 0
version delta = 0
Phase-64 implementation delta = 0
```

任何真实 production correctness defect 都会停止完成审计，不会在 Slice 16
修复或用 prose 掩盖。

## Exact Changed-Path Closure

| Status | Path |
| --- | --- |
| A | docs/spec/phase63-completion-audit-phase64-handoff-v1.md |
| A | tests/test_phase63_slice16_completion_audit_phase64_handoff.py |
| M | docs/roadmap.md |
| M | docs/status.md |
| M | tests/test_active_phase_lifecycle.py |
| M | tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py |

```text
A2/M4/D0
6 paths
production Python: 179 -> 179
tests: 421 -> 422
```

没有 production、grammar/generated、package/dependency/lockfile/workflow/version、
public schema、SQL、Arrow、executor、optimizer 或 Phase-64 implementation path。

## Validation And Publication

完成 focused suites、reader/inventory guards、public/private compatibility、
targeted Pyright、Ruff、format、`git diff --check` 与 fresh rereview 后，唯一
authoritative validator 是：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
```

预算为 4 starts；unchanged failed candidate 不得重跑。最终 PASS 后封存 exact
tree，只创建一个 ordinary non-amend commit：

```text
Complete Phase 63 joined query blocks
```

只允许一次 normal fast-forward push，随后只观察 natural exact-head CI。必须
为 `push/main/attempt 1/success` 且 Python 3.12/3.13 成功。禁止 amend、rebase、
force push、manual rerun、dispatch、tag、Release、signing、attestation 或
status-only follow-up commit。

成功标题：

```text
PASS — PHASE63_SLICE16_COMPLETION_AUDIT_PHASE64_HANDOFF_END_TO_END
```
