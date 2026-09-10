# Phase 64 Completion Audit And Phase 65 Handoff v1

## Decision And Publication Boundary

本 Slice 11 审计已经发布的 flat relational product exits，只新增文档与 static
assurance。D01–D08、N=11、E01–E12保持；未发现 Phase64-owned implementation gap。
结论为已批准支持域内 `Phase64 material exits = 12/12`、
`Phase64 self-owned-open = 0`，其完成状态仍以本 Slice 的成功出版链为条件。

本地候选阶段，Phase64仍为ACTIVE，Slice11为AUDIT / COMPLETION CANDIDATE。
只有本 Slice 的review、最终验证、精确Git tree和自然exact-head
`push/main/attempt 1/success`全部成功，才建立：

```text
Phase64 = COMPLETED
Slices1–11 = COMPLETED / PUBLISHED
Phase64 material exits = 12/12 within the explicitly approved support domain
Phase64 self-owned-open = 0
Phase65 = NEXT / NOT STARTED / no approved numbered route
```

该结论不等于SQL生成、数据库执行、通用类型等价、public IR API或运行期
single-match履行；后续owner与未决planning问题列于下文。Phase65未开始。

## Starting Authority And Writing Closure

| Fact | Value |
| --- | --- |
| HEAD/main/cached/live main | `ceccba408d042c3bfe08c90a9c67b57cd690541a` |
| Tree | `6462e82c508a2b9cbe06094e6dfc0166a243ec2e` |
| Parent | `9333faeae1e544f1be70f17bfcb67d06fd57f9c4` |
| Subject | `Complete Phase 64 flat relational Project IR` |
| Natural baseline CI | [34451916850](https://github.com/MianliWang/pietto/actions/runs/34451916850), push/main/attempt 1/success |
| Python3.12 / Python3.13 jobs | `102789349888` / `102789350132`, validator/generated/golden/package均success |
| Baseline state | divergence0/0；index/worktree/untracked干净；无active Git operation或残留validator |

在首次repository edit前读完sole lifecycle/inventory functions及direct reader
controls，并冻结以下closure；旧Slice10的47批权限已闭合，不能用于本Slice：

| State | Path |
| --- | --- |
| A ACTIVE | `docs/spec/phase64-completion-audit-phase65-handoff-v1.md` |
| A ACTIVE | `tests/test_phase64_slice11_completion_audit_phase65_handoff.py` |
| M ACTIVE | `docs/status.md` |
| M ACTIVE | `docs/roadmap.md` |
| M ACTIVE | `tests/test_active_phase_lifecycle.py` |
| M ACTIVE | `tests/test_validation_performance_interlude_slice4_validator_static_analysis_stage_optimization.py` |
| M CONTINGENCY / NOT ACTIVATED | `docs/language.md` |
| M CONTINGENCY / NOT ACTIVATED | `docs/spec/diagnostics.md` |
| M CONTINGENCY / NOT ACTIVATED | `docs/project-package.md` |

三个guide现有支持/后续owner陈述与本审计一致，无需激活。预期实际A2/M4/D0、
6paths；production Python187不变，test Python444 -> 445。新principal只读本
immutable audit、显式source/test与固定Git objects；不读取mutable lifecycle文档，
也不新增whole-repository inventory reader。零生产delta在本候选review/seal时
对确切baseline核验，不能成为对future HEAD的永久零变化断言。

## Published Scope And Lineage

依据[Phase64 route/decisions](phase64-flat-relational-algebra-product-phase-initiation-gate-v3-source-audit-architecture-route-lock-v1.md)：
D01扩展现有JOIN body的ON；D02新kind仅direct binary；D03既有命名关系是组合
边界；D04显式ALL/DISTINCT与positional operands；D05私有三态single-match；
D06共用RELATION_OUTPUT身份域的SELECT/non-SELECT入口；D07精确类型/Decimal与
独立row-domain；D08实现本阶段IR/retention，Phase65承载形状留待planning。

补充决定单独注明时点，不回填原D07或D04/D06：

- Slice8的[D07-FLOAT-DEFERRED](phase64-slice8-row-equivalence-distinct-quotient-grain-origin-v1.md)明确将Float和aliases的row equivalence留给Phase72，无finite-literal例外。
- Slice9的[S9-NAME-1](phase64-slice9-set-operations-explicit-all-distinct-output-identity-v1.md)采用第一authored operand标签；result identity/properties/provenance仍由set owner和完整operation evidence决定。

从Interlude-II terminal `bb52135038973b40638ff86367ba478846f898c6` 到本基线，
独立 `git log --first-parent --reverse` / `rev-list`重建得到**13条**出版记录。
不是一Slice一commit：编号1的最终terminal为reconciliation child；其初次
`f483d2d3...` publication原本成功，**不是failed head**。以下13个自然run均现场
核实push/main/attempt1/success，且两Python job的四项必需步骤成功。

| # | Role | Commit | Tree | Parent | Natural CI | Python3.12 job | Python3.13 job |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Slice1 initial publication | `f483d2d3a73edbfd6b203fb3014758095e398e23` | `008c88eb2a6aadb63172bb2ee3b326971dfe058d` | `bb52135038973b40638ff86367ba478846f898c6` | [34049044651](https://github.com/MianliWang/pietto/actions/runs/34049044651) | `101529218653` | `101529218496` |
| 2 | Slice1 reconciliation terminal | `691245e48c387357f700d19b9f7318bbf79f3045` | `b87a62318156e5c9f574446b365debee1fa1bdbf` | `f483d2d3a73edbfd6b203fb3014758095e398e23` | [34077572865](https://github.com/MianliWang/pietto/actions/runs/34077572865) | `101606592867` | `101606593025` |
| 3 | Unnumbered F01/F02 repair | `ac32bd5d8f98c7952f4276f8ba2a8c7bdc332c73` | `fc0a2e100c6115ebf771e8313b8061a2eceb98fa` | `691245e48c387357f700d19b9f7318bbf79f3045` | [34092606235](https://github.com/MianliWang/pietto/actions/runs/34092606235) | `101649111830` | `101649111641` |
| 4 | Slice2 terminal | `317ae65440447997740b58bb4eac774aa7df19b8` | `8d6adc6f3056d6c578291c68d4da534482836446` | `ac32bd5d8f98c7952f4276f8ba2a8c7bdc332c73` | [34102086024](https://github.com/MianliWang/pietto/actions/runs/34102086024) | `101678602445` | `101678602679` |
| 5 | Slice3 terminal | `dae18c78ab38e4d6fbe517218b92d6f2506da489` | `42ac5a3eb9810bfeab0d1696086f51ab6f627152` | `317ae65440447997740b58bb4eac774aa7df19b8` | [34165657512](https://github.com/MianliWang/pietto/actions/runs/34165657512) | `101876063245` | `101876063201` |
| 6 | Slice4 terminal | `dc194d3932656af7d41b1fd7bcabb5c4f7c59c03` | `13e35e12c889c9c269508f9bf29ba9b31c46d998` | `dae18c78ab38e4d6fbe517218b92d6f2506da489` | [34192534911](https://github.com/MianliWang/pietto/actions/runs/34192534911) | `101953350809` | `101953350968` |
| 7 | Dependabot PR73 maintenance | `32632ea8dd5057034d2b5add861c1d2850ae5dee` | `82bd4551d8101747a68b98becbbed4c455630906` | `dc194d3932656af7d41b1fd7bcabb5c4f7c59c03` | [34194052736](https://github.com/MianliWang/pietto/actions/runs/34194052736) | `101957837087` | `101957836902` |
| 8 | Slice5 terminal | `04b234a38cb92f647e3a4a869117b15fa1163928` | `c685accd427399c97ae7c4914156b93c5be5dcc9` | `32632ea8dd5057034d2b5add861c1d2850ae5dee` | [34205094377](https://github.com/MianliWang/pietto/actions/runs/34205094377) | `101992620359` | `101992620682` |
| 9 | Slice6 terminal | `241be04da179969ddb1bd50381ee9ac58cea1641` | `c20ce463fd8f9fb31ac183b6e3f659f5f5c77217` | `04b234a38cb92f647e3a4a869117b15fa1163928` | [34238303080](https://github.com/MianliWang/pietto/actions/runs/34238303080) | `102101642715` | `102101642205` |
| 10 | Slice7 terminal | `66c0e08628834c88e0a68013d036e32baad24e56` | `551d34398b90535bed1f91fa3656e26cc68c5cc2` | `241be04da179969ddb1bd50381ee9ac58cea1641` | [34253791709](https://github.com/MianliWang/pietto/actions/runs/34253791709) | `102154345228` | `102154345958` |
| 11 | Slice8 terminal | `73fcb2bcdbe27775fc3bf9500df8d68006a62578` | `8c955e8754f53311160b25c22dd571267777177c` | `66c0e08628834c88e0a68013d036e32baad24e56` | [34265355099](https://github.com/MianliWang/pietto/actions/runs/34265355099) | `102193214444` | `102193214112` |
| 12 | Slice9 terminal | `9333faeae1e544f1be70f17bfcb67d06fd57f9c4` | `8646dd478445ec91ead181116a79d5e484294589` | `73fcb2bcdbe27775fc3bf9500df8d68006a62578` | [34305449725](https://github.com/MianliWang/pietto/actions/runs/34305449725) | `102321072675` | `102321072425` |
| 13 | Slice10 terminal | `ceccba408d042c3bfe08c90a9c67b57cd690541a` | `6462e82c508a2b9cbe06094e6dfc0166a243ec2e` | `9333faeae1e544f1be70f17bfcb67d06fd57f9c4` | [34451916850](https://github.com/MianliWang/pietto/actions/runs/34451916850) | `102789349888` | `102789350132` |

编号终态为上表2、4、5、6、8、9、10、11、12、13行，分别对应Slices1–10。
行3是[未编号F01/F02修复](pre-phase64-slice2-compilation-boundary-correctness-repair-v1.md)：
shared legacy-IR QUALIFY admission及exact cycle/blocked-owner closure，不是新Slice。

行7是[Dependabot PR #73](https://github.com/MianliWang/pietto/pull/73)维护：
合入`32632ea8...`，Ruff0.16.4 -> 0.16.6；实际修改`uv.lock`及
`tests/test_phase63_slice1_joined_query_block_product_architecture_source_audit_future_roadmap_route_lock.py`
的synthetic shallow-PR检查。它不是Slice4失败修复或编号product Slice。
Phase64区间内的lockfile变化由该维护提交拥有，不能声称整个phase无lockfile变化。
该固定历史区间的Project JSON v2 serializer、pyproject及CI workflow无delta；
本Slice自身的production/dependency/workflow/generated/golden内容也不变。

Slice10已知本地观察是12568 passed，两个CI job各12564 passed /4 skipped；
来源和环境分别保留，不从数值推断skip原因。47项corrective accounting包含
correctness、integration、compatibility和命令/fixture工作，不是47次失败publication，
也不声称47个生产缺陷曾被独立重演。第一次local authoritative的12541passed/
1failed仍是FAIL；最终publication是上表唯一ceccba40 head及其成功自然CI。
旧/tmp细节是可选补充；缺失不重造、不成为新的completion门槛。

## E01–E12 Acceptance Map

每行保留原exit含义，列出实际producer/carrier、consumer和既有pytest node
selector；parametrized selector代表其已覆盖的参数家族。所列测试由Slice10
exact-head自然完整CI覆盖，本Slice最终authoritative/full CI继续运行它们。
新principal只核对audit的可追溯性，不另建semantic oracle或mutation campaign。

| Exit | Original product result | Current producer/carrier | Relevant consumer | Existing verification witnesses | Support limit | Phase64-owned open |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Generic INNER/LEFT ON 经真实 authored EXPLICIT_MODULES check完成 | `src/pietto/_project/project_current_joins.py::ProjectCurrentJoinRegion` | `src/pietto/_project/project_final_outputs.py::build_project_effective_output_completion` | `tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py::test_minimal_generic_and_refined_vertical_completion`<br>`tests/test_phase64_slice4_effective_output_join_first_generic_vertical_closure.py::test_real_project_check_json_success_in_each_mode` | generic Bool/TRUE-only匹配；无新单文件、PACKAGE_ROOT或SQL入口 | 0 |
| E02 | CROSS/RIGHT/FULL完整累计左侧及双侧补空 | `src/pietto/_project/project_current_joins.py::ProjectCurrentBinaryJoin` | `src/pietto/_project/project_joined_row_semantics.py::ProjectConcreteJoinedRowSemantics` | `tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_minimal_new_kinds_complete_exact_rows`<br>`tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_full_nulls_entire_multihop_prefix_and_following_on_sees_it`<br>`tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_full_of_two_global_inputs_keeps_explicit_unknown_grain` | 新kind仅direct binary；GLOBAL×GLOBAL FULL可能UNKNOWN，不伪造GLOBAL | 0 |
| E03 | SEMI/ANTI左BAG出现保留，右匹配/依赖保留而字段不外泄 | `src/pietto/_project/project_current_joins.py::ProjectCurrentJoinRegion` | `src/pietto/_project/project_current_join_inputs.py::ProjectCurrentPreMatchInputs` | `tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_authored_existence_retains_exact_left_fields_and_both_input_uses`<br>`tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_predicate_only_right_is_absent_from_every_later_tail_scope`<br>`tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_finite_bag_null_reference_and_metamorphics` | 0-or-1左输出不证明右match≤1；未知右grain不污染已知左grain | 0 |
| E04 | base/generic/refinement与WHERE/satisfying/QUALIFY authority分离 | `src/pietto/_project/project_join_conditions.py::ProjectJoinCondition` | `src/pietto/_project/project_final_outputs.py::ProjectEffectiveOutputCompletion` | `tests/test_phase64_slice3_generic_on_condition_semantics_authority_separation.py::test_refinement_keeps_base_and_conjunct_occurrences`<br>`tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_join_on_and_later_where_keep_separate_authority`<br>`tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py::test_grouped_output_left_join_window_qualify_retains_all_stages` | M3不发现relationship；M4保base+refinement；post filters不回写matching证据 | 0 |
| E05 | completed/effective输入映射到exact active IR producer | `src/pietto/_project/project_current_join_inputs.py::ProjectCurrentInputAuthority` | `src/pietto/_project/project_query_block_ir_algebra.py::ProjectIRJoinInputCorrespondence` | `tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py::test_effective_input_vertical_to_verified_private_observation`<br>`tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_swapped_same_schema_active_producer_is_not_a_valid_input_image`<br>`tests/test_phase64_slice10_ir_observation_and_differential.py::test_join_producer_correspondence_retains_valid_inputs_and_rejects_omission` | 外部producer必须显式；内部缺省须实际同owner前置JOIN链接；旧UNSUPPORTED enum允许保留 | 0 |
| E06 | private request/proof/obligation和全模式warning/error契约 | `src/pietto/_project/project_single_match.py::ProjectSingleMatchAssessment` | `src/pietto/_project/project_completed_semantics.py::with_project_single_match_requests` | `tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_unproved_actual_matches_warn_on_success_in_every_mode`<br>`tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_malformed_and_foreign_requests_are_errors_without_obligations`<br>`tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_hop_and_whole_path_keep_their_exact_units_and_complete_authority` | PIE-S2337 WARNING，PIE-S2338 ERROR；PROVED是scoped static proof，不是数据观察 | 0 |
| E07 | visible-row DISTINCT、精确equivalence与quotient grain | `src/pietto/_project/project_final_outputs.py::ProjectDistinct` | `src/pietto/_project/project_query_block_ir.py::ProjectIRDistinctComparison` | `tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_join_outputs_compare_only_visible_projection`<br>`tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_decimal_parameters_are_exact_not_nullable_or_widened`<br>`tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_float_computed_and_finite_literal_not_exempt` | Float/aliases推迟Phase72；Decimal参数必须独立validated；hidden fields不参与等价 | 0 |
| E08 | 六set多重性律、显式quantifier、位置/重复use及set-owned输出 | `src/pietto/_project/project_set_operations.py::ProjectSetOperandUse` | `src/pietto/_project/project_query_block_ir.py::ProjectIRCompletedSetOperationOutput` | `tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py::test_six_laws_include_zero_and_null_class`<br>`tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py::test_repeated_operand_build_once_use_twice`<br>`tests/test_phase64_slice9_set_operations_explicit_all_distinct_output_identity.py::test_three_operand_except_is_left_fold_and_nested_is_not_flattened` | S9-NAME-1只赋标签；UNION ALL仅shape/type；其他五式需row equivalence；非DB执行证明 | 0 |
| E09 | 新输出穿过既有tails、replay及命名跨特性组合 | `src/pietto/_project/project_final_outputs.py::ProjectEffectiveOutputCompletion` | `src/pietto/_project/project_query_block_ir.py::build_project_query_block_ir` | `tests/test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer.py::test_new_kinds_use_the_existing_tail_builders`<br>`tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_existing_completed_tails_in_both_roles_and_result_replay_join`<br>`tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py::test_decimal_set_join_distinct_and_named_nested_set_keep_parameter_sources` | 保持既有tail legality和aggregate-risk terminals；不自动重聚合或扩展未知组合 | 0 |
| E10 | combined IR、独立verification/invalidation及VERIFIED-only closed observation | `src/pietto/_project/project_query_block_ir.py::ProjectIRQueryBlockSnapshot` | `src/pietto/_project/project_query_block_ir_verification.py::verify_project_query_block_ir` | `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_semantic_evidence_changes_require_rebuild_and_fresh_verification`<br>`tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_single_match_obligations_and_proofs_cannot_be_replaced`<br>`tests/test_phase64_slice10_ir_observation_and_differential.py::test_real_flat_ir_records_bytes_and_rejections_match_every_process_cell` | private Phase64 marker；old formats保留；runtime identity不由canonical bytes代替 | 0 |
| E11 | Project JSON v2 top-level shape不变，authored/diagnostic变化区分 | `src/pietto/_project/json_v2.py::project_check_result_to_json_dict` | `src/pietto/cli.py::main` | `tests/test_phase64_slice6_semi_anti_left_occurrence_retention_existence_semantics.py::test_real_explicit_project_check_and_unchanged_json_shape`<br>`tests/test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics.py::test_real_cli_diagnostic_consumer_renders_private_warning_without_new_option`<br>`tests/test_phase64_slice8_row_equivalence_distinct_quotient_grain_origin.py::test_public_explicit_check_keeps_json_shape` | 语法/诊断为公开additive；private IR不是public JSON/Explain/SQL扩展 | 0 |
| E12 | Phase65直接消费保留事实，无需名字/末端输出/bytes重建语义 | `src/pietto/_project/project_query_block_ir.py::ProjectIRSingleMatchRetention` | `src/pietto/_project/project_query_block_ir_inspection.py::build_project_query_block_ir_inspection` | `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_all_except_membership_and_repeated_uses_reach_the_consumer`<br>`tests/test_phase64_slice10_ir_observation_and_differential.py::test_order_proof_variants_retain_declared_bindings_and_supplied_steps`<br>`tests/test_phase64_slice10_ir_observation_and_differential.py::test_decimal_sources_and_parent_references_are_retained` | 仅消费需求和未决问题，未定义ProjectSQLPlan API/carrier/算法/编号route | 0 |

E05的current/effective rebind由正常builders产生正向VERIFIED图，不以删除旧
UNSUPPORTED enum成员判定成功。E10补充覆盖source/final-field roles、visible/
strict-FD ORDER、Decimal source/parent、blocked owners及义务完整性：

- `tests/test_phase64_slice10_ir_observation_and_differential.py::test_capability_locator_and_canonical_final_roles_are_bound`
- `tests/test_phase64_slice10_ir_observation_and_differential.py::test_order_binding_and_witness_corruptions_are_rejected`
- `tests/test_phase64_slice10_ir_observation_and_differential.py::test_decimal_source_and_parent_corruptions_are_rejected`
- `tests/test_phase64_slice10_project_ir_composition_verification_invalidation_inspection_pure_boundary.py::test_invalid_request_blocks_owner_and_all_set_membership_dependencies`
- `tests/test_phase64_slice10_ir_corruption_and_invalidation.py::test_coherent_loss_of_grain_images_is_rejected_against_semantic_authority`

F01/F02现有tests/test_compilation_boundary_qualify_admission.py及
 tests/test_completion_dependency_cycles.py保持run-only。历史/out-of-domain
negatives与有意的typed UNKNOWN/terminal仍有效，不是遗漏的Phase64实现。

## Support And Non-Goal Ledger

| Boundary | Completed guarantee / approved limit | Outstanding classification / owner |
| --- | --- | --- |
| Entrypoints | 正向新语义在EXPLICIT_MODULES；single-file、LEGACY_FLAT、PACKAGE_ROOT、public Explain/SQL保持实际admission限制；已有single-file功能不被泛化禁止 | 已批准later-owner：Phase65 planning、Phase66 baseline multi-relation SQL/Project emit-SQL、Phase69统一安全public入口 |
| Single-match | 私有request无public marker/CLI flag；PIE-S2337在LOOSE/CHECKED/STRICT均WARNING；PIE-S2338是invalid ERROR；PROVED仅exact scope静态证据 | 已批准later-owner：Phase65保留/legality处理，Phase68执行期fulfillment；不通过过滤、LIMIT或去重履行 |
| Equality/types | DISTINCT及五种equality-dependent set forms排除Float/aliases，无finite-literal例外；Decimal需要exact validated参数/source；UNION ALL只要求shape/type | 已批准later-owner：Phase72高级equality、NaN/type widening；此处无猜测或隐式coercion |
| Set identity | S9-NAME-1只给first-authored labels；位置对齐、repeated uses、set-owned fields、operation-specific NULL/property/value/membership provenance保持 | 已批准later-owner：Phase70更广composition；没有first-available或name alignment |
| Tails and uncertainty | 既有LET/WHERE/GROUP/satisfying/WINDOW/QUALIFY/projection/ORDER/LIMIT规则继续；UNKNOWN grain或risk缺证时typed fail closed，不自动修复aggregate | 已完成的non-concrete行为；额外aggregate algebra/自动重聚合归Phase73，非Phase64-owned gap |
| Representation | private marker为pietto.phase64-flat-relational-ir-inspection.v1；未变Phase61/62/63输入保留旧format/bytes；明确lifted fixture按新行为迁移 | 已批准later-owner：Phase65 planning表示；不重新命名旧version或假称lifted bytes未变 |
| Five claims | check success、runtime IR VERIFIED、pure-document OK、backend lowerability、runtime fulfillment互不等同；verified graph可含typed terminals | Planning结果/partial-owner边界尚待Phase65决议；不据此产生SQL或执行能力 |
| Other future work | 无新inline path-group/outer capture、nested relation、optimizer、persistent cache或recursion | 已批准Phase70/71、88/89；tentative91/92保持owner-only |

当前未确认Phase64-owned implementation gap；若验收出现该类问题，必须停止本
completion，而非将它重标为Phase65。上述later items是原批准边界，下面的问题
是尚未开始的Phase65设计选择，两者均不同于漏做本阶段mandatory exit。

## Phase-65 Consumer Handoff

以下是当前**私有**入口与精确前提，不是新SQLPlan API：

| Existing entrypoint | Exact prerequisite / supplied result |
| --- | --- |
| `build_project_completed_semantic_result` | exact ProjectSemanticResult；EXPLICIT_MODULES产生ProjectConcreteCompletedSemanticResult，其他mode为typed non-concrete；ok与owner availability需分别检查 |
| `with_project_single_match_requests` | exact completed root + explicit request tuple；保留原roots/effective output身份并附加assessment/diagnostics |
| `build_project_query_block_ir` | exact completed root、其Phase61 plan/Phase62 VERIFIED prerequisite/final overlay连续性；产出canonical owner entries及explicit active endpoints或typed terminals |
| `verify_project_query_block_ir` | exact snapshot；独立检查原evidence、allocation、uses、fields/properties/requirements，不调用builder重建预期 |
| `build_project_query_block_ir_analysis_bundle` | exact VERIFIED result；combined reverse-use/topology/reachability必须同一root |
| `build_project_query_block_ir_inspection` | exact verified analysis bundle；不重建或重新验证semantic facts |
| `evaluate_project_query_block_ir_document` | document-local closed refs/evidence；malformed为normalized rejection/no bytes，OK不是runtime root身份或SQL legality |

| Fact | Existing producer/carrier | Exact root / membership | Phase65 consumption need | Loss/mutation counterexample | Remaining decision / later owner |
| --- | --- | --- | --- | --- | --- |
| H01 active outputs/uses | ProjectIRQueryBlockSnapshot、ProjectIRJoinInputCorrespondence、entry.active_output/active_properties | completed/owners/dependencies/schedule同根；每个use指向实际active producer，内部prefix须同owner前置JOIN | 明确计划输入与partial/terminal处理，不选择last/largest output或按名称重建 | 同schema wrong producer、external producer omission、重复use丢失；E05/E10现有反例 | Q65.1结果边界；语义root改变必须rebuild/fresh verification |
| H02 JOIN orientation/scopes | ProjectCurrentBinaryJoin、ProjectIRComposedJoin.source/condition/inputs、ProjectJoinCondition | exact authored use/kind、M1–M5/base/refinement、pre-match references；WHERE/satisfying/QUALIFY各自stage | 保留direct二元方向、whole-left结构及predicate stage；CROSS无fabricated ON TRUE | 交换input role、补空只作用一个binding、把WHERE当ON；E02/E04 | Q65.5 legality；rewrite搜索仍Phase88 |
| H03 positional type/value/membership | ProjectSetOperation.uses、ProjectSetColumn、ProjectCompletedSetOutputField、ProjectIRSetOperandInput | ordered operand occurrence、positional fields、canonical set owner；EXCEPT右侧仍membership dependency | 表示六条multiplicity laws和named nesting，分开label与identity，不按名称对齐 | repeated operand去重、EXCEPT右依赖丢失、foreign set field；E08/E12 | Q65.1结果结构与Q65.5 requirement；高级composition Phase70 |
| H04 source spans | 原JoinClause/ON/VIA、SetOperationBody spans、condition references、TypeExpr | 实际logical module/source span与原AST occurrence；不取cwd/id/repr | source -> planning -> 后续SQL映射必须保持原owner；明确generated位置与authored位置关系 | `test_convergence_rereview_order_source_uses_its_actual_module`、Decimal span/source反例 | Q65.4 source-map ownership |
| H05 NULL/property/grain | ProjectIRJoinedRowField、ProjectIROutputRelationalProperties、ProjectIRQueryBlockRowDomainOrigin | ordered nulling refs、STRICT/LAX、key/FD及GLOBAL/UNKNOWN/quotient/alternative/subset premises；exact field images | 保留facts和适用前提；缺证不提升为GLOBAL/max-one/backend promise | coherent grain-image loss、FULL两GLOBAL、outer-FD scope；E02/E10 | Q65.5 capability/legality；aggregate algebra Phase73 |
| H06 equality/Decimal | ProjectDistinct、ProjectRowEquivalenceField、set column/operand capability | visible comparison tuple、canonical type/alias/nominal identity、validated(p,s)/TypeExpr及ordered parents | 分开semantic equality requirement与backend实现能力，不扩大Phase64支持域 | source/final-field替换、参数/parent/source嫁接、hidden equality fields；E07/E10 | Q65.5 requirement；advanced equality Phase72 |
| H07 ORDER evidence | ProjectRelationOrdering、ProjectCompletedEffectiveOutput.order_proofs、portable ORDER_BINDING/ORDER_PROOF | exact item、visible source refs或既有strict-FD property/index/witness；window order不同于relation order | alias/scope及ordering expressions依靠真实已供证明，不重求语义closure或选代表 | visible targets丢失/重复归一、foreign FD property或witness；E10现有ORDER反例 | Q65.3 alias scope，Q65.5 legality |
| H08 obligations/state | ProjectSingleMatchAssessment/Proof、ProjectIRSingleMatchRetention/ProjectIRSingleMatchProofImage、原Diagnostic | exact request occurrence、scope/unit/boundaries/input pairs/proof roots；LEGAL_UNPROVED保留enforcement_required | 明确未履行要求如何进入plan结果及下游承诺；不能因IR VERIFIED/pure OK即认为已履行 | omitted/foreign proof、post-JOIN LIMIT掩盖、INVALID owner被提升；E06/E10 | Q65.1/Q65.5；runtime fulfillment Phase68 |

这些输入已经存在于当前carriers及其消费者；Phase65不需要从名字、末端输出
或canonical bytes补造丢失语义。此表没有定义ProjectSQLPlan构造函数、数据结构、
别名算法或execution SPI。

## Phase-65 Open Questions And Planning Preference

下表都是下一次joint product/architecture/phase-start讨论的未决选择；已知owner
不是已批准方案。当前Phase65仍NEXT / NOT STARTED / no approved numbered route。

| Question | Known responsibility | Alternatives / decision still needed |
| --- | --- | --- |
| Q65.1 planning result boundaries | Phase65 target-neutral planning结果与legality | whole-project还是selected-owner结果；typed terminals/partial availability如何表达；计划结果如何绑定exact verified root |
| Q65.2 parameter and placeholder identity | Phase65参数与占位符身份 | authored occurrence与共享value如何区分；稳定顺序/重复引用及backend占位符映射；禁止把相同literal值当同一semantic occurrence |
| Q65.3 alias scope | Phase65 SQL planning名字和scope | relation/field/use/scope如何投影；哪些名称只供展示，怎样处理nested/repeated uses；不回流改变semantic binding |
| Q65.4 source-map ownership | Phase65 planning source maps，Phase66 SQL位置消费 | authored、planning、generated SQL spans各由谁产生/组合；诊断如何回到exact original owner而非绝对临时路径 |
| Q65.5 legality, capability and obligation handling | Phase65 planning/legal requirements；Phase68 fulfillment | unsupported/unknown/unproved分别如何失败或保留；target capability怎样匹配；哪些obligation能表达/何时必须拒绝，不能默认执行可用 |

用户规划偏好：**compare 14–16 real delivery Slices; 16 is the preferred initial
candidate**。下一次应比较14/15/16的实际交付粒度，以一个principal invariant加
一个真实first consumer拆分。该偏好**不是approved N=16**，不是编号route，也
不授权Phase65实现。representation、verification和portable-consumer compatibility
应随其第一消费者尽早闭合，避免再次全部堆到一个过大的最终integration单元。

## Slice-10 Lessons

已发布Slice10的工作需要分开描述：correctness fixes保障root/membership与证据
完整性；representation integration处理combined坐标与portable links；compatibility
migration处理明确lifted fixtures及历史/live epoch；command/fixture工作处理运行
参数、测试前提和中断回执。47项账目不等于47个独立重演的生产缺陷，也不等于
47次failed publication。

HR01/HR02表明历史六family/62-request/A4-M18清单不能借live七family/74-request
registry来认证。JPC01保留合法internal prefix同时拒绝external producer omission；
CCG01保护实际compiler capability module/API边界，而不是泛化helper-name substring。
这提供更小delivery单元和更早consumer closure的经验，不新增governance/performance
framework，也不声称测得了新的时间节省。

## Static Assurance And Validation

新principal核对固定历史谱系、原decisions/supplements、12个exit的实际source/test
引用、support/handoff/未决问题与规划偏好。它不运行新semantic oracle，不冻结
完整live enum集合，不将old baseline..future HEAD固定为零production。
Optional Git历史测试只在确切immutable对象缺失时skip，核心static/decision检查
仍执行；pytest不fetch网络。sole mutable reader及whole-repo inventory职责不变。

本Slice生产修复为0。fresh document/static correction groups最多4，authoritative
starts最多4，ordinary initial commit1，允许同closure且剩余修正预算内最多1个
natural-CI repair child。初始draft不是repair；新production finding或越界路径STOP。

内容完成后执行双Python principal/lifecycle/inventory与early test Pyright/Ruff/format，
再以`UV_PYTHON=3.13 uv run python scripts/validate.py --timings`覆盖whole-tree
format/Ruff/两Pyright和全套existing behavior/differential。最终native generated、
39-golden、final-document-input package/CLI smoke及diff check均必须通过。

review/seal只对本候选验证production delta=0与固定closure；之后结果/receipts
留在仓库外和Git/自然CI，不逐次追加本文造成循环。按已授权流程封存exact tree、
一次ordinary commit `Complete Phase 64 audit and Phase 65 handoff`、ff push main，
观察exact-head push/main/attempt1双Python四项步骤。失败head保留，禁止manual
rerun/amend/rebase/force/admin bypass/tag/release/signing/attestation/status-only commit。
