# Phase65 Completion Audit And Phase66 Handoff v1

本审计只关闭Phase65已批准支持域，并向下一真实consumer交接，不实施Phase66。
依据已发布D65.01–D65.12、C01–C43、P01–P10及N16，结合当前源码、已读行为断言、
本次重新核实的Git/自然CI，以及明确标为继承的执行收据。新Phase仍须满足durable
phase-initiation的30项与external-reference11字段；此次不是新的initiation或design rewrite。

## Authority and publication rule

接受基线commit `128388bc258d6ee861c0128c42324fca712c0dcc`，tree
`75ba55ccbd70cf482cde8b3a9be10055955babd7`，parent
`b6278c94b74f60fb32b4314e992c22974d4519a0`；自然CI
[34842205857](https://github.com/MianliWang/pietto/actions/runs/34842205857/attempts/1)
为push/main/attempt1/success。审计重新fetch/readback确认clean main/index/worktree、
无活动Git操作和相关竞争进程。Slice15已关闭，其失败、授权与预算不转入本Slice。

只有本合同、新static principal及四个current-document/lifecycle/inventory owners可写，
A2/M4/D0；production204不变，test Python files461→462。其余production、历史合同、
probe、registry、provider和workflow只读。没有新的product/architecture决定；文档组织与
静态traceability是implementation freedom，不认证未知的历史预算、作者或操作终态。

**条件式完成规则：** Phase65 completion只有在本Slice实质审查、全部本地门禁、一次普通
commit/fast-forward push及自然exact-head push/main/attempt1 CI成功后成立；两个Python
jobs都须通过authoritative/generated/golden/package。实际本Slice commit/tree/CI只写仓库外
final receipt，本文不嵌入未来自己的Git身份，不靠status-only后续commit建立完成。

## Published Slice1–15 lineage

以下有限历史由first-parent Git tree/parent和authenticated GitHub attempt1 records独立核对：
16个commits、15个Slice成功终态，14含失败首发和普通repair child。success行的两个Python
jobs及四项必要steps均成功；failure行保留实际job结果。

| Slice / role | Commit | Tree | Parent | Natural CI / event / branch / attempt | Result |
| --- | --- | --- | --- | --- | --- |
| S01/publication | `3d89ebb45a59cee243e03a293f479f3011807f9f` | `29dfc9b7be09a16336861ed497727de2fa21f75e` | `d7af544dd4ce48891d5fe2596ab23e494f48d4ab` | [34512999929](https://github.com/MianliWang/pietto/actions/runs/34512999929/attempts/1); push/main/1 | success (both Python jobs) |
| S02/publication | `adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b` | `b349f9c50d6d3fc28f9cdb621d7ba7d7b1fe2bba` | `3d89ebb45a59cee243e03a293f479f3011807f9f` | [34556059755](https://github.com/MianliWang/pietto/actions/runs/34556059755/attempts/1); push/main/1 | success (both Python jobs) |
| S03/publication | `56fe50b685692ff5ed9e58202d7116ae5a221775` | `f99b74e38d81bdc61aaffeea5abf0072734238c3` | `adb55b84e60f1fc1439e5b7f6e2d9fae81dba12b` | [34562319623](https://github.com/MianliWang/pietto/actions/runs/34562319623/attempts/1); push/main/1 | success (both Python jobs) |
| S04/publication | `d87070d9ab0a261dd0f55f7ef1aceeee966b03dc` | `d001229f4ab6815d76ab27eb7963e472cb86d983` | `56fe50b685692ff5ed9e58202d7116ae5a221775` | [34574113991](https://github.com/MianliWang/pietto/actions/runs/34574113991/attempts/1); push/main/1 | success (both Python jobs) |
| S05/publication | `ec0a9f3a535dc4e4284e1d064c676a217750dc43` | `4ef49bbce9019699c2c3875249b51e1c52b08182` | `d87070d9ab0a261dd0f55f7ef1aceeee966b03dc` | [34651949568](https://github.com/MianliWang/pietto/actions/runs/34651949568/attempts/1); push/main/1 | success (both Python jobs) |
| S06/publication | `720a296a5ac7aa3181afb82ccd42453186ebba1c` | `b0977930d42ddb3214021cb0a1174a1b3ef0900c` | `ec0a9f3a535dc4e4284e1d064c676a217750dc43` | [34669857637](https://github.com/MianliWang/pietto/actions/runs/34669857637/attempts/1); push/main/1 | success (both Python jobs) |
| S07/publication | `0966ecb309f6243baf4490a423ebcb47af1f909c` | `3d4d7f967680309f9ac5a9a339e510fe174903bb` | `720a296a5ac7aa3181afb82ccd42453186ebba1c` | [34682271444](https://github.com/MianliWang/pietto/actions/runs/34682271444/attempts/1); push/main/1 | success (both Python jobs) |
| S08/publication | `86bf4e6e5a525e0c099339f0ea29c4b51ab57f04` | `a813b16992cb2d355aa61a8eac259c3ee715bc69` | `0966ecb309f6243baf4490a423ebcb47af1f909c` | [34686688681](https://github.com/MianliWang/pietto/actions/runs/34686688681/attempts/1); push/main/1 | success (both Python jobs) |
| S09/publication | `9de7991498e2258bf41557bae95f91152c9670f3` | `27dfeff90478e366eb3589544f1b9e07108d0c99` | `86bf4e6e5a525e0c099339f0ea29c4b51ab57f04` | [34715387544](https://github.com/MianliWang/pietto/actions/runs/34715387544/attempts/1); push/main/1 | success (both Python jobs) |
| S10/publication | `0c025b1060a93b9ab0999f71575830b7c25757ed` | `3416da1d1f04614e30e6b525c4f91b603edb6051` | `9de7991498e2258bf41557bae95f91152c9670f3` | [34723478209](https://github.com/MianliWang/pietto/actions/runs/34723478209/attempts/1); push/main/1 | success (both Python jobs) |
| S11/publication | `a7a48a1e3c7b288e051213fdb163dd7226d0cd60` | `c9472766324a40c543c97c2f17bce897a7dfdd27` | `0c025b1060a93b9ab0999f71575830b7c25757ed` | [34739921800](https://github.com/MianliWang/pietto/actions/runs/34739921800/attempts/1); push/main/1 | success (both Python jobs) |
| S12/publication | `a0e235f9c858187a7b5f25e47c1413e61a8899fe` | `eb0bcb33e2291a7114ab9c464959fdc8488ee551` | `a7a48a1e3c7b288e051213fdb163dd7226d0cd60` | [34744544990](https://github.com/MianliWang/pietto/actions/runs/34744544990/attempts/1); push/main/1 | success (both Python jobs) |
| S13/publication | `079ed2ecfbcf71e9adc11dec898a1a61120ae7f5` | `d227daf60175a6100be6dca2d07023b75b53b240` | `a0e235f9c858187a7b5f25e47c1413e61a8899fe` | [34750296114](https://github.com/MianliWang/pietto/actions/runs/34750296114/attempts/1); push/main/1 | success (both Python jobs) |
| S14/initial-failed | `a4db6382dd9d01867529605b14c902aef135bfd2` | `3c17ad7ec1703d4e743494ba4c0525ae4fa23d2a` | `079ed2ecfbcf71e9adc11dec898a1a61120ae7f5` | [34792068365](https://github.com/MianliWang/pietto/actions/runs/34792068365/attempts/1); push/main/1 | failure (3.12 failed;3.13 success) |
| S14/repair-child | `b6278c94b74f60fb32b4314e992c22974d4519a0` | `20460df34ed65dc07dfb5a536f7fcf7b511ea17c` | `a4db6382dd9d01867529605b14c902aef135bfd2` | [34793858855](https://github.com/MianliWang/pietto/actions/runs/34793858855/attempts/1); push/main/1 | success (both Python jobs) |
| S15/publication | `128388bc258d6ee861c0128c42324fca712c0dcc` | `75ba55ccbd70cf482cde8b3a9be10055955babd7` | `b6278c94b74f60fb32b4314e992c22974d4519a0` | [34842205857](https://github.com/MianliWang/pietto/actions/runs/34842205857/attempts/1); push/main/1 | success (both Python jobs) |

Slice14的b6278c94 child只改其process reader：supported版本保留，按actually available
解释器过滤独立request期待，并增加single/dual manifest-only控制，不是production修复。
Slice15再修正双版本insertion order的期待并检查两种顺序；原requests/registry未改变。
Slice序号不等于commit数，失败首发不能从历史删除。

Slice15的两个实质修正分别为：

- **F65S15-01**：真实bound literal文档删除contexts/report links后，原pure边界误给OK，
  runtime correspondence已拒绝。修复owner是
  `src/pietto/_project/project_sql_plan_pure_boundary.py`：完整root-to-leaf ancestry、contexts及
  每份report自己的ordered entry/link identities。两份清单互删不能认证空成功。
- **F65S15-02**：正常named ordered producer经completed/IR/plan/report/map成功后，encoder
  首先拒绝实际`ProjectIRProvidedRelationOrdering`，尚未到pure。修复owners是
  `src/pietto/_project/project_sql_plan_portable.py`、
  `src/pietto/_project/project_sql_plan_portable_schema.py`、
  `src/pietto/_project/project_sql_plan_pure_boundary.py`。专用record保留exact output/evidence/
  ordered items和ordinary/rebound property/ORDER links；独立correspondence machinery复用。
  `ProjectRelationOrdering`仍为不同carrier，不推导outer presentation order。

这些是Slice15显式授权的bounded production exceptions，不是production-free conformance，
也不回写Slice14合同追认没有缺口。RIGHT_GLOBAL fixture改用原已准入joined GLOBAL producer
与outer request，不是新的proof admission。Slice15的tested tree75ba55cc...对应commit128388bc...；
直接publication approval未改变source/test/document。其6/6 corrections、1/4 local validator是
关闭历史；本Slice独立分配，不能借余额，也不重造缺失旧/tmp记录或认证所有早期预算。

## P01–P10 material acceptance

下列英文exit保留原定义。producer/consumer与行为断言源码已读，包含真正执行断言的helpers；
仅有test名称或AST存在不能证明runtime correctness。执行依据基线完整自然CI、重读的Slice15
最终收据及本Slice final authoritative继续运行现有behavior suite。completed success、IR/plan
VERIFIED、runtime source correspondence、pure document consistency、target evidence和execution有别。

审计结论：**Phase65 material exits = 10/10 within the explicitly approved support domain**；
**Phase65 self-owned-open = 0**。这是有限domain的实质关闭，不是universal feature/backend覆盖。
P10合同交接和本Slice发布仍受前述完成规则约束。任何确认的Phase65 material gap都阻止关闭，
不能改名为later work、弱化exit或在此修改production获得PASS。

| Exit | Approved exit (unchanged) | Current producer / verifier / consumer | Read assertion evidence | Qualification / established remaining owner | Phase65-owned open |
| --- | --- | --- | --- | --- | --- |
| P01 | One explicit eligible result/root produces a valid plan; incompatible/unverified/error/terminal inputs cannot masquerade as concrete. | `src/pietto/_project/project_sql_plan.py::build_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_root_and_selection_are_explicit_and_never_name_resolved`<br>`tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_selected_closure_distinguishes_unrelated_limitation_and_error`<br>`tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_every_future_family_is_a_typed_terminal` | 原root/owner graft拒绝、完整diagnostics/blockers、非具体不可inspection。EXPLICIT_MODULES、completed.ok与exact VERIFIED IR/bundle仍是前提；无关有效planning limitation不同于project ERROR。69/70更广入口或partial-error policy尚未批准实现。 | 0 |
| P02 | Source descriptors, reachable producer definitions and all uses/ports/symbol scopes are complete, exact and deterministic. | `src/pietto/_project/project_sql_plan.py::build_project_sql_bindings`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_bindings`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_bindings` | `tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_named_chain_uses_immediate_exports`<br>`tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_imported_reexported_producer_keeps_defining_module_and_exact_trail`<br>`tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_depth12_repeated_set_has_complete_body_and_binding_graph` | immediate exports、defining/use trail、13/24 named DAG及distinct uses/ports完整。SourceDef只是dependency；SET可为QUERY结果。name/locator不是identity，shared definition不承诺single evaluation。Phase66保留scope/ports，70开放composition，94仅tentative federation。 | 0 |
| P03 | Existing row/JOIN/group/window/QUALIFY/DISTINCT/set/order/limit meaning survives query-block planning without invented rewrites. | `src/pietto/_project/project_sql_plan.py::build_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | `tests/test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention.py::test_accumulated_left_has_all_previous_and_current_nulling`<br>`tests/test_phase65_slice6_grouped_global_satisfying_block_boundaries.py::test_false_input_filter_does_not_erase_global_stage`<br>`tests/test_phase65_slice7_windows_named_window_qualify_staging.py::test_real_predecessors_hidden_and_mixed_projection_pipeline`<br>`tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_limit_barrier_and_named_order_scope`<br>`tests/test_phase65_slice9_set_query_expression_bodies_positional_ports.py::test_three_operand_except_and_nested_except_keep_different_graphs` | 累计nulling、GLOBAL empty row、window/QUALIFY scopes、LIMIT barrier与SET nesting有实际字段断言。只覆盖现有admitted组合，不新增FD/coercion/physical策略。直接SET→GROUP/GLOBAL仍PIE-S2333；已有explicit bridge区别保留。66忠实lower或拒绝；70/72/73/88/89保留原范围。 | 0 |
| P04 | Typed fixed data-literal slots/payload/uses are complete, exact and immutable; structural and unknown-context literals remain classified; target representation/overload demands and rendered placeholders stay separate. | `src/pietto/_project/project_sql_plan_literals.py::ProjectSQLFixedEnvelope`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_fixed_literal_envelope`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_equal_values_remain_separate_and_let_references_do_not_reextract`<br>`tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_fixed_envelope_independently_rejects_malformed_or_rebound_values`<br>`tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_exact_numeric_tags_and_finite_float` | direct或helper中的真实断言拒绝wrong/extra/foreign/rebound payload，保留distinct equal leaves和共享stage value。PRESERVE默认，BIND仅eligible Bool/Int/Text/finite Float；结构/call/unknown sites保留理由。66负责placeholders/type anchors，70 caller rebind，69/82公共接口，72 Float equality。 | 0 |
| P05 | Exact source-to-plan and reverse origin queries cover authored and generated sites without fabricated coordinates. | `src/pietto/_project/project_sql_plan_source_maps.py::build_project_sql_source_map`<br>`src/pietto/_project/project_sql_plan_source_maps.py::verify_project_sql_source_map`<br>`src/pietto/_project/project_sql_plan_source_maps.py::inspect_project_sql_source_map` | `tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_flat_original_inventory_and_exact_forward_reverse_relations`<br>`tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_import_reexport_and_external_type_source_ownership`<br>`tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_literal_transport_reverse_identity_and_exact_coordinates` | 完整entry/site/link、defining/use/type roots、escape/non-BMP半开坐标均有断言。authored/generated与value/membership/type/proof有别；legacy缺坐标仍缺。66负责SQL ranges/单位，75负责LSP转换；无source reread补位。 | 0 |
| P06 | Mandatory requirement sites cannot be omitted; original pending obligations and proposition-scoped target evidence have closed distinct states and all blocker evidence; no check/lowering/execution equivalence. | `src/pietto/_project/project_sql_plan_requirements.py::build_project_sql_requirement_report`<br>`src/pietto/_project/project_sql_plan_requirements.py::verify_project_sql_requirement_report`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::build_project_sql_target_assessment`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::verify_project_sql_target_assessment` | `tests/test_phase65_slice11_complete_demand_obligation_report.py::test_layer1_rejects_missing_demands_and_literal_constituents`<br>`tests/test_phase65_slice11_complete_demand_obligation_report.py::test_repeated_original_requests_and_unrelated_project_warnings`<br>`tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_real_compiler_positive_subpropositions_do_not_certify_composites`<br>`tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_complete_product_deletion_and_false_summary_mutations` | 完整denominator、重复requests和全project warnings保持；exact positive subproposition不认证composites。NOT_ASSESSED/negative/Absent/Unknown/Conflict/unmapped/inapplicable有别。hidden ORDER、aggregate evidence、enforcement仍pending；66 lowerer/安全emit，68 fulfillment，76–79深度catalog。 | 0 |
| P07 | Independent verification/invalidation and runtime inspection accompany all supplied plan features. | `src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_verification.py::ProjectSQLPlanVerification`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_verifier_and_inspection_never_call_construction`<br>`tests/test_phase65_slice9_set_query_expression_bodies_positional_ports.py::test_no_downstream_semantic_set_type_or_plan_construction`<br>`tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_policy_and_envelope_identity_invalidate_old_verification`<br>`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_target_only_reassessment_keeps_the_original_neutral_request` | 不重建/调用solver，root/policy/envelope变更失效；target-only新assessment不改neutral root。Bindings VERIFIED不是whole plan VERIFIED；pure OK不是runtime身份。66消费匹配request，91 persistent cache仍tentative；无跨snapshot承诺。 | 0 |
| P08 | Closed portable plan evidence includes context identity, typed values, role-tagged origins and required links; actual positive/field-level-corruption/process/old-format compatibility coverage exists. | `src/pietto/_project/project_sql_plan_portable.py::build_project_sql_plan_portable`<br>`src/pietto/_project/project_sql_plan_portable.py::verify_project_sql_plan_portable`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::parse_project_sql_plan_document`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::Inspection` | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_coherent_document_is_not_runtime_authentication`<br>`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_removing_contexts_and_all_their_links_still_contradicts_ancestry`<br>`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_provided_ordering_fields_preserve_exact_output_evidence_and_items`<br>`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_registered_mutations_and_source_negatives_have_exact_distinct_outcomes` | private source-bearing observation，不是executable deserialization/redaction/source authenticity。F01完整ancestry/report-local links与F02exact provided-ordering已由15限定生产修正闭合，不追认14从无缺口。新record不声称旧checker forward compatibility。 | 0 |
| P09 | The reviewed corpus is stable across actual supported Python/seeds/relocation/installed wheels using the existing invocation-local acquisition; totals are derived from the new exact registry, not copied as16/74 forever. | `tests/_pietto_phase65_sql_plan_differential_probe.py::observation`<br>`tests/_pietto_differential_process_acquisition.py::DifferentialAcquisition` | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_registered_process_matrix_and_same_child_origins`<br>`tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_standalone_forward_reverse_batch_and_atomic_failure`<br>`tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_available_matrix_compares_actual_records_bytes_and_rejections` | 实际requests/bytes、same-child origins、standalone/正反batch、三个mode及failure atomicity。supported3.12/3.13与actually available分开；86/16仅双版本manifest实例，historical62/74原域保持。81扩展assurance，90 Rust仍later，不冻结未来topology。 | 0 |
| P10 | Private/public/package boundaries and complete Phase66 consumer handoff are documented; no Phase65-owned open item is concealed. | `src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::inspect_project_sql_target_assessment`<br>`src/pietto/cli.py::main`<br>`src/pietto/sql/relations.py::render_relation_sql` | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_new_consumers_remain_private_without_dynamic_or_renderer_access`<br>`tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_runtime_accessors_and_original_products_survive_disabled_encoding` | empty private exports、无dynamic/renderer依赖、runtime不依赖portable encoder；package smoke覆盖installed legacy CLI。下文真实consumer契约与待决问题完成交接。legacy SQL已存在，新ProjectSQLPlan不发射SQL；Phase66 fresh initiation/route approval pending，不批准首个Slice。 | 0 |

## D65 decision disposition

保留Slice1原decision kind；已交付状态不是重新批准，不把当时PLANNED名字当现有API。

| Decision | Original kind | Delivered disposition | Exits | Counterexamples |
| --- | --- | --- | --- | --- |
| D65.01 | USER_DECISION_REQUIRED | exact roots、selected closure、全project diagnostics | P01 P02 P06 | C01 C02 C33 |
| D65.02 | ARCHITECTURE_DECISION | referenced SELECT/SET/use/ports及non-fusing边界 | P02 P03 | C08 C09 C10 C38 C41 |
| D65.03 | ARCHITECTURE_DECISION | context-qualified sites、scope symbols、stage-value复用 | P02 P03 P04 | C14 C17 C29 C30 |
| D65.04 | USER_DECISION_REQUIRED | 原BAG/NULL/FD/order/effect要求；无物理执行推断 | P03 P06 | C03 C04 C11 C15 C16 C19 C34 C39 |
| D65.05 | USER_DECISION_REQUIRED | eligible typed fixed transport，非caller rebind | P04 | C05 C06 C07 C27 C28 C40 |
| D65.06 | USER_DECISION_REQUIRED | exact static connector/locator；不选connection | P01 P02 P06 | C20 |
| D65.07 | ARCHITECTURE_DECISION | 完整demands与proposition-scoped assessment | P06 | C18 C31 C32 |
| D65.08 | USER_DECISION_REQUIRED | direct/hop/whole proofs及unfulfilled原义务 | P03 P06 | C12 C21 |
| D65.09 | ARCHITECTURE_DECISION | 完整role origins、原坐标与source-bearing披露 | P05 P08 | C22 C35 C36 C37 |
| D65.10 | ARCHITECTURE_DECISION | independent checks/invalidation；runtime与pure分开 | P07 P08 | C23 C24 C25 C26 C43 |
| D65.11 | ARCHITECTURE_DECISION | 共享有限DAG与输出量计成本；无隐式solver/框架 | P02 P09 | C09 C36 |
| D65.12 | USER_DECISION_REQUIRED | N16不变；15限定例外如实记录，16无production | P08 P09 P10 | C42 |

Slice1 §3D的七项decision index逐项归档，不是第四份asset ledger：

| Index | Original subject | Current disposition |
| --- | --- | --- |
| K01 | 16 delivery units | N16已发布且不变，本audit是16；无Phase66 route选择。 |
| K02 | whole-semantic-success prerequisite | 保守admission已实现，不批准partial-project ERROR bypass。 |
| K03 | fixed-value literal transport only | 固定原值已实现，不是writable query template。 |
| K04 | typed transport demands / closed eligible roles | v2要求由10/11/13/14/15覆盖；fewer binds是原支持边界。 |
| K05 | field/demand/source inventories from first consumer | 2–13捕获，11/12汇总，14/15消费链闭合；F01/F02历史例外已披露。 |
| K06 | later-owner mapping for open parameters/partial-error policy | Slice1登记归属，不追溯成Phase64决定；70 open parameters与69/70 partial-error policy仍UNAPPROVED_PRODUCT_POLICY，需新阶段批准。69/82负责公共边界。 |
| K07 | private names/file factoring/static thresholds | 由实际source/consumer确定；下文用当前spellings，不批准其他行为。 |

## C01–C43 disposition

原参考例说明BAG/NULL/order/effect等应保留的关系。以下对应真实结构/field-level断言或明确
禁止推断的边界；未执行SQLite/PostgreSQL/MySQL参考数据库制造Pietto结果证据。

| Counterexample | Contract-preserving disposition | Existing assertion / bounded claim |
| --- | --- | --- |
| C01 | whole-project ERROR仍阻止；原diagnostics不可裁剪。 | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_selected_closure_distinguishes_unrelated_limitation_and_error` |
| C02 | 当前call-authority terminal不能因IR VERIFIED变concrete；不把历史test名解释为所有后续family都不可用。 | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_every_future_family_is_a_typed_terminal` |
| C03 | 保留LIMIT/filter顺序；[1,2]例子说明语义边界，非reference DB执行证据。 | `tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_limit_barrier_and_named_order_scope` |
| C04 | hidden computation不进入visible DISTINCT key，只比较保持的facet。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_hidden_and_selected_windows_change_only_the_intended_visible_tuple` |
| C05 | data叶与结构LIMIT/order分开，bound stage value不重新提取。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_order_limit_zero_and_qualify_do_not_erase_defining_literals` |
| C06 | 改值/foreign envelope拒绝；static LIMIT不可由query rebind改变，实际placeholder/rebind留66/70。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_fixed_envelope_independently_rejects_malformed_or_rebound_values` |
| C07 | equal literal不合并，Bool/Int/Float标签和原值独立校验。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_equal_values_remain_separate_and_let_references_do_not_reextract` |
| C08 | 共享definition保留每个binding/use，不以alias代替identity。 | `tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_two_import_paths_share_definition_but_not_binding` |
| C09 | 13/24 named DAG加source/result wrappers；不复制4096 leaves。 | `tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_depth12_repeated_set_has_complete_body_and_binding_graph` |
| C10 | 原left fold与nested图保持不同，不声称数据库执行。 | `tests/test_phase65_slice9_set_query_expression_bodies_positional_ports.py::test_three_operand_except_and_nested_except_keep_different_graphs` |
| C11 | base/refinement/ON与post-WHERE分别保留。 | `tests/test_phase65_slice5_seven_join_kinds_match_scopes_obligation_retention.py::test_relationship_base_and_refinement_are_separate_from_where` |
| C12 | SEMI/ANTI的right matching依赖及LEGAL_UNPROVED保留；left0/1不是right≤1证明。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_registered_corpus_retains_proofs_risks_targets_and_hidden_visibility` |
| C13 | scope/use有结构证据；materialize-once/安全重复effects未由结构证明，D65.04禁止推断，70/88/89待实现。 | `tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_real_join_repeated_or_mixed_inputs_have_distinct_scoped_symbols` |
| C14 | GROUPED结果跨scope用port；窗口见P03，不回到旧qualifier。 | `tests/test_phase65_slice6_grouped_global_satisfying_block_boundaries.py::test_plan_let_where_satisfying_references_reuse_results` |
| C15 | 原FD witness与pending realization保留，无min/max/representative。 | `tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_strict_fd_remains_a_pending_scoped_requirement` |
| C16 | inner ORDER/LIMIT保留，不承诺outer presentation order。 | `tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_limit_barrier_and_named_order_scope` |
| C17 | neutral scope符号独立；target case/length/quoting injectivity属66待决。 | `tests/test_phase65_slice3_named_producer_graph_repeated_imported_uses_scope_local_symbols.py::test_labels_do_not_create_cross_scope_or_namespace_identity` |
| C18 | positive/negative/conflict原channels都保留，omitted无support证书。 | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_partial_negative_conflicting_profiles_keep_both_raw_channels` |
| C19 | exact alias/Decimal source与proposition保留，不替target选择collation/coercion。 | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_original_alias_decimal_provenance_is_not_a_builtin_rewrite` |
| C20 | known family mismatch和connection residual有别，无隐式federation。 | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_source_family_bridge_known_mismatch_mixed_and_connection_residual` |
| C21 | LIMIT/EXCEPT后仍有原warning与pending requirement。 | `tests/test_phase65_slice11_complete_demand_obligation_report.py::test_except_membership_and_limit_zero_retain_original_warning` |
| C22 | defining/import/use/type source不混为consumer path。 | `tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_import_reexport_and_external_type_source_ownership` |
| C23 | external producer deletion是graph/document corruption，不伪装成negative source；internal predecessor要positive关系。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_registered_mutations_and_source_negatives_have_exact_distinct_outcomes` |
| C24 | equal-looking foreign roots/ports/fields拒绝，bytes不复原runtime身份。 | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_coherent_looking_field_level_grafts` |
| C25 | coherent alternative可pure OK，但原runtime对应失败；无executable import。 | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_coherent_document_is_not_runtime_authentication` |
| C26 | target-only不改neutral request；policy重建与old-envelope失效另见P07。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_target_only_reassessment_keeps_the_original_neutral_request` |
| C27 | typed operand/representation demands不能缺失；实际SQL参数类型/overload策略留66。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_no_literal_fallback_or_missing_representation_requirements` |
| C28 | data-looking call/aggregate/window/structural sites不以黑名单方式放行bind。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_admitted_aggregate_call_and_satisfying_contexts_are_preserved` |
| C29 | source occurrence加context；共有AST/同名不替代实际evaluation site。 | `tests/test_phase65_slice4_row_scalar_let_where_stage_value_planning.py::test_context_and_field_level_corruptions` |
| C30 | stage/group value复用原port和defining binds，不重建表达式。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_bound_earlier_let_flows_through_aggregate_port` |
| C31 | 删除清单不能产生空all()成功；F01同时删contexts/links仍受ancestry约束。 | `tests/test_phase65_slice11_complete_demand_obligation_report.py::test_layer1_rejects_missing_demands_and_literal_constituents` |
| C32 | legacy/compiler局部fact不是whole-plan support，composite/unmapped仍unresolved。 | `tests/test_phase65_slice13_explicit_target_profile_requirement_assessment.py::test_real_compiler_positive_subpropositions_do_not_certify_composites` |
| C33 | 全project diagnostics与selected需求分开，重复request occurrences不丢失。 | `tests/test_phase65_slice11_complete_demand_obligation_report.py::test_repeated_original_requests_and_unrelated_project_warnings` |
| C34 | hidden key不是quotient普通字段；专门需求连原visible tuple/FD。 | `tests/test_phase65_slice8_distinct_scoped_order_static_limit_result_boundaries.py::test_strict_fd_remains_a_pending_scoped_requirement` |
| C35 | escape/non-BMP按原parser字符range/occurrence，非decoded-value或UTF字节坐标。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_unicode_coordinates_and_imported_defining_vs_consuming_identity` |
| C36 | right-only membership/predicate来源不能被value-only pruning删除。 | `tests/test_phase65_slice12_forward_reverse_source_map_queries.py::test_matching_only_right_inputs_remain_sources_without_becoming_exports` |
| C37 | private观察可含constants/locators，不保证redaction或公开安全。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_exact_refs_and_immutable_source_bearing_inspection` |
| C38 | 未支持reached shape不得omission/pass-through或靠concrete标签变绿。 | `tests/test_phase65_slice2_minimal_selected_scan_projection_project_sql_plan.py::test_concrete_looking_terminal_cannot_bypass_supported_shape` |
| C39 | GLOBAL one_global_row与GROUPED no_groups不同，COUNT()/COUNT(nullable)/SUM保持原类型。 | `tests/test_phase65_slice6_grouped_global_satisfying_block_boundaries.py::test_false_input_filter_does_not_erase_global_stage` |
| C40 | exact tags、signed zero和unary syntax不归一化。 | `tests/test_phase65_slice10_typed_fixed_literal_envelope_bind_use_layout.py::test_signed_zero_payload_corruption_does_not_fold_unary_minus` |
| C41 | 真实field/link/role独立oracle，不靠labels或双encoder输出相同。 | `tests/test_phase65_slice15_whole_selected_plan_real_source_differential_conformance.py::test_registered_portable_join_group_window_set_and_profile_relationships` |
| C42 | 14完成minimum process注册/入口，15扩corpus；注册声明不同于执行证据。 | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_standalone_forward_reverse_batch_and_atomic_failure` |
| C43 | raw重复keys须在mapping前拒绝；重复uses不是重复declarations。 | `tests/test_phase65_slice14_portable_boundary_minimal_process_integration.py::test_raw_duplicate_object_keys_reject_at_every_depth` |

## Inherited and delivered ledgers

逐项更新Slice1 §3A/§3B disposition并沿用原authority。INHERITED_CLOSED是复用既有semantic/IR/
diagnostic authority；TRANSFERRED_TO_PHASE65都有实际consumer，不能把current gap换贴later标签。

| Inherited | Original asset | Current reuse / evidence |
| --- | --- | --- |
| I01 | Typed completed outputs and diagnostics | INHERITED_CLOSED；completion/admission复用原输出和diagnostics；P01/P06 |
| I02 | Canonical source/field/owner/use identities | INHERITED_CLOSED；plan scopes/ports/maps保留原nominal domains；P02/P05 |
| I03 | Exact completed dependency order | INHERITED_CLOSED；selected DAG和各use沿既有拓扑；P02 |
| I04 | JOIN conditions, scopes, orientations | INHERITED_CLOSED；七kind pre-match/output/nulling原证据；P03 |
| I05 | DISTINCT/set semantics and exact types | INHERITED_CLOSED；visible quotient、six SET、Decimal/equivalence要求；P03 |
| I06 | Row/property/grain/ORDER/Decimal facts | INHERITED_CLOSED；引用properties/FD而不重解算；P03/P06 |
| I07 | Single-match private assessments | INHERITED_CLOSED；原request/proof/warning/enforcement；P06 |
| I08 | Existing source connectors | INHERITED_CLOSED；原semantic检查与静态文本，不读取DB；P01/P02 |
| I09 | Capability fact/provider/profile model | INHERITED_CLOSED；原lookup/completeness/release applicability；P06 |
| I10 | Diagnostic objects and source spans | INHERITED_CLOSED；全project tuple及authored/generated来源；P05/P06 |
| I11 | Runtime/pure historical inspection | INHERITED_CLOSED；七个historical family streams/旧formats兼容；P08/P09 |
| I12 | Optimized test acquisition | INHERITED_CLOSED；repository facts/shared store和sole readers复用；P09/P10 |

| Transferred | Original deliverable | Completing slices | Disposition |
| --- | --- | --- | --- |
| T01 | Selected-result plan and source descriptors | 2–3 | DELIVERED within approved domain；P01 P02；handoff publication遵循completion rule。 |
| T02 | Query blocks, symbols, typed stage references | 3–9 | DELIVERED within approved domain；P02 P03 P07；handoff publication遵循completion rule。 |
| T03 | Literal parameter transport and logical bind layout | 10 | DELIVERED within approved domain；P04；handoff publication遵循completion rule。 |
| T04 | Demand and obligation report | 11 | DELIVERED within approved domain；P06；handoff publication遵循completion rule。 |
| T05 | Full source maps | 12 | DELIVERED within approved domain；P05；handoff publication遵循completion rule。 |
| T06 | Explicit target assessment | 13 | DELIVERED within approved domain；P06；handoff publication遵循completion rule。 |
| T07 | Portable plan observation | 14 + 15 F01/F02 | DELIVERED within approved domain；P08；handoff publication遵循completion rule。 |
| T08 | E2E/differential and handoff | 15–16 | DELIVERED within approved domain；P09 P10；handoff publication遵循completion rule。 |

## Retained later owners

Authority为Slice1 §6逐atom分类、§3D新增归属说明，以及当前Future Roadmap v6/tentative ledger。
66–97无遗漏，无新owner/route。CORE_NOW/MINIMUM_NOW等描述当时Phase65的contribution，
**不表示未来owner已经实现**。91–97始终TENTATIVE / OWNER ONLY，不升级为approved功能。

| Later owner | Existing classification | Delivered contribution / exact remaining work and reason |
| --- | --- | --- |
| L66 (SQL/emit) | CORE_NOW | plan/ports/binds/maps/requirements已交付；dialect SQL AST/text、type anchors、target identifiers/source realization、actual placeholder/use mapping、generated SQL ranges与忠实stage实现仍待下一层。 |
| L67 (result/Arrow) | MINIMUM_NOW / DEFER_BY_NECESSITY | 已给exact ordered result/type/nullability/presentation posture；PiettoResultContract API、Arrow types/batches/buffer ownership尚无result层。 |
| L68 (executor) | CONTRACT_ONLY_NOW / DEFER_BY_NECESSITY | payload与pending义务可消费；connection/statement/session/transaction/stream/cancel/backpressure及真实assertion/fulfillment尚无执行层。 |
| L69 (alpha/entrypoints) | CONTRACT_ONLY_NOW | private/check/target边界已明示；统一safe public入口、plan/bind options、集成命令和发布仍待批准。 |
| L70 (open plans) | MINIMUM_NOW / DEFER_BY_NECESSITY | generated scope/use seams已保留；authored CTE/subquery/VALUES/table functions/outer capture/EXISTS/IN/LATERAL/decorrelation、caller rebind与general effect authority未实现。 |
| L71 (nested) | CONTRACT_ONLY_NOW / DEFER_BY_NECESSITY | 只有flat ports/grain provenance；Collect/Unnest/flatten/outer-inner grain/nested Arrow需要其semantic/result层。 |
| L72 (types/equality) | CORE_NOW / DEFER_BY_NECESSITY | exact type/Decimal parent/null/collation要求已投影；NaN/Float row equivalence、widening、temporal/range/ASOF尚未实现。 |
| L73 (aggregate algebra) | MINIMUM_NOW / DEFER_BY_NECESSITY | 保留GROUPED/GLOBAL/proof/risk；state/merge/reaggregation/grouping extensions不能由planner补做。 |
| L74 (assets/SPI) | CONTRACT_ONLY_NOW / NO_CURRENT_USE | 原asset/function/provider identity保留；derived relationships/plugin registration/execution尚无当前consumer实现。 |
| L75 (language tools) | CORE_NOW / DEFER_BY_NECESSITY | source maps已给原parser字符坐标；formatter/LSP/editor/editions/migration与位置转换尚需工具层。 |
| L76 (PostgreSQL depth) | MINIMUM_NOW / DEFER_BY_NECESSITY | 已有requirement/profile seam；深度lowering/extensions/optimization/catalog完整度仍是PostgreSQL owner。 |
| L77 (MySQL depth) | MINIMUM_NOW | 同样的seam与negative source/target结果；深度lowerings/releases/session语义待MySQL owner。 |
| L78 (SQLite depth) | CONTRACT_ONLY_NOW | common plan不证明SQLite支持；实际backend/facts/tests留本owner。 |
| L79 (DuckDB depth) | CONTRACT_ONLY_NOW | 无隐式BY NAME/ASOF；实际backend及深度features留本owner。 |
| L80 (data science) | CONTRACT_ONLY_NOW | exact ports/BAG/order/null可交接；pandas/Polars/NumPy/SciPy/Matplotlib adapters及materialization尚无result runtime。 |
| L81 (assurance) | MINIMUM_NOW / DEFER_BY_NECESSITY | 已有独立有限corpus；real-DB/fuzz/benchmark farms和持续性能承诺尚未实施。 |
| L82 (freeze) | CONTRACT_ONLY_NOW | private version/visibility已披露；公共syntax/API/schema/support matrix仍待冻结。 |
| L83 (release) | CONTRACT_ONLY_NOW | 已有exit/limitation evidence，不等于stable1.0发布审核。 |
| L84 (remote/trust) | CONTRACT_ONLY_NOW / NO_CURRENT_USE | 无ambient registry/credentials；remote loading/signing/authentication/trust policy尚无实现。 |
| L85 (solver/lock) | CONTRACT_ONLY_NOW / NO_CURRENT_USE | 复用dependency identity；solver/canonical lock/resolution不由plan添加。 |
| L86 (devices/domain) | CONTRACT_ONLY_NOW | 不塞入device/RDKit对象；scientific/geospatial/sparse/DLPack/device adapters依赖后续result/transport。 |
| L87 (catalog/statistics) | MINIMUM_NOW / DEFER_BY_NECESSITY | 静态proof与observed data不同；introspection/statistics/chase/data-quality仍无runtime evidence acquisition。 |
| L88 (logical optimizer) | CONTRACT_ONLY_NOW | 保留rewrite premises/ports；memo/cost/join-order/hypergraph search及equivalence transforms未选择。 |
| L89 (physical strategies) | CONTRACT_ONLY_NOW | logical boundary不承诺materialization/evaluation；Yannakakis/WCOJ/Free Join/predicate-transfer/dataflow选择待physical owner。 |
| L90 (Rust) | CONTRACT_ONLY_NOW / NO_CURRENT_USE | pure checker/corpus可作输入；没有profiling-driven PyO3/maturin port/kernel/wheel实现。 |
| L91 (tentative cache) | CONTRACT_ONLY_NOW | 明确root invalidation；persistent/incremental identity/cache仍TENTATIVE / OWNER ONLY。 |
| L92 (tentative recursion) | CONTRACT_ONLY_NOW | 当前图acyclic；recursion/fixpoint/iterative planning/provenance仍TENTATIVE / OWNER ONLY。 |
| L93 (tentative proof) | CONTRACT_ONLY_NOW | 局部assumptions/witnesses不是formal certification；仍TENTATIVE / OWNER ONLY。 |
| L94 (tentative federation) | CONTRACT_ONLY_NOW | mixed connectors不证明跨连接执行；distribution/data movement/network仍TENTATIVE / OWNER ONLY。 |
| L95 (tentative DML/DDL) | NO_CURRENT_USE | 当前为read/query compiler；write/DDL/migration仍TENTATIVE / OWNER ONLY。 |
| L96 (tentative governance) | NO_CURRENT_USE | 普通identity不是访问策略；governance/security semantics仍TENTATIVE / OWNER ONLY。 |
| L97 (tentative continuous) | NO_CURRENT_USE | finite BAG不同于continuous/streaming-time/state；仍TENTATIVE / OWNER ONLY。 |

当前边界不能被later编号替代：

1. EXPLICIT_MODULES及完整semantic/IR/root前提仍强制。无关有效planning limitation不阻止selected
   closure；无关ERROR仍阻止。更广public/open入口或partial-error编译政策尚未批准实现。
2. 直接SET→GROUP/GLOBAL的PIE-S2333保持；已准入explicit SELECT bridge区别有真实测试，
   不自动插桥或普遍承诺bridge可用。unsupported组合、缺mandatory call/type evidence保持typed failure。
3. Float binding不解除Float/alias row-equivalence延后；UNION ALL与其余五个SET forms要求不同。
   Decimal参数、原TypeExpr及parent evidence不被builtin rewrite替代。fixed原值、caller rebind、
   实际SQL placeholder/type anchors分别属于已交付65、待做70、待做66，hidden ORDER/risk/enforcement仍pending。


## Phase66 consumer map

以下是实际private API。可读取不等于target strategy已实现；禁止用name/最后output/bytes重建
语义。Phase66消费typed authority及完整membership，不能成为第二个resolver。

| Handoff | Concern | Actual producer / reader | Inputs, outputs and closed failure contract | May trust / must preserve / must not infer |
| --- | --- | --- | --- | --- |
| H01 | Selection / roots | `src/pietto/_project/project_completed_semantics.py::build_project_completed_semantic_result`<br>`src/pietto/_project/project_query_block_ir.py::build_project_query_block_ir`<br>`src/pietto/_project/project_query_block_ir_verification.py::verify_project_query_block_ir`<br>`src/pietto/_project/project_query_block_ir_verification.py::build_project_query_block_ir_analysis_bundle`<br>`src/pietto/_project/project_sql_plan.py::build_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_plan`<br>`src/pietto/_project/project_sql_plan_inspection.py::inspect_project_sql_plan` | exact completed/bundle/owner；literal_policy默认PRESERVE。builder对malformed roots/policy给TypeError/ValueError，reached semantic/planning阻断返回ProjectSQLPlanUnavailable及完整blockers。verifier给issues/verified；inspection拒绝非VERIFIED。 | 只消费同一request；根、selected owner、IR/evidence、policy/envelope改变须重建/重验。调用BIND builder后验证也要给匹配policy及envelope，不能把bindings-only或IR flag升格为complete plan。 |
| H02 | Sources / SELECT / SET / uses | `src/pietto/_project/project_sql_plan.py::build_project_sql_bindings`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_project_sql_bindings`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.input_terminals`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.terminal_exports` | 读取sources/definitions/uses/ports/symbols及immediate producer images；SELECT blocks和SET bodies分别读取，query refs须属于当前view，foreign refs拒绝。 | canonical terminal exports的identity/order/type不能被helpers替代；locator是原connector文本，不split-on-dot/parse-as-SQL；同family不代表同connection。 |
| H03 | Scalar / JOIN / group / window / results | `src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.stage_context`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.match_context`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.satisfying_uses`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.hidden_order_requirement` | 读取typed expression/stage ports、pre-match/output/nulling、aggregate/window/result/SET结构及原conditions/policies。hidden与visible roles不同，owned refs由query入口检查。 | 可做dialect结构消费，不得自行fuse/reorder/推断physical evaluation；不增加DISTINCT键、representative或outer ordering。无法忠实实现的shape应明确拒绝。 |
| H04 | Fixed values / bind uses | `src/pietto/_project/project_sql_plan_literals.py::ProjectSQLLiteralPolicy`<br>`src/pietto/_project/project_sql_plan_verification.py::verify_fixed_literal_envelope`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.fixed_value`<br>`src/pietto/_project/project_sql_plan_inspection.py::ProjectSQLPlanInspection.uses_for_slot` | plan.fixed_envelope、literal_sites/slots/bind_uses完整；standalone envelope verifier返回bool，whole plan验证还核对scope/policy/原值。fixed_value参数是slot ref，literal_value参数是expression ref。 | 保留tag/value/ordinal/context/ancestry，不按value合并。66形成每statement actual use-to-slot map、placeholder tokens、type anchors；此API不是caller rebind。 |
| H05 | Demand / report / pending obligations | `src/pietto/_project/project_sql_plan_requirements.py::build_project_sql_requirement_report`<br>`src/pietto/_project/project_sql_plan_requirements.py::verify_project_sql_requirement_report`<br>`src/pietto/_project/project_sql_plan_requirements.py::inspect_project_sql_requirement_report` | builder消费exact VERIFIED plan；verifier相对同source request。inspection提供for_subject/definition/stage/input_use/family/requirement及related/referring；wrong refs或非positive verification拒绝。 | 完整denominator及每次use必须保留。diagnostics是全project而selected demands有scope。PROVED不是DB观察；LEGAL_UNPROVED、aggregate evidence、hidden ORDER不能改为fulfilled。 |
| H06 | Forward / reverse origins | `src/pietto/_project/project_sql_plan_source_maps.py::build_project_sql_source_map`<br>`src/pietto/_project/project_sql_plan_source_maps.py::verify_project_sql_source_map`<br>`src/pietto/_project/project_sql_plan_source_maps.py::inspect_project_sql_source_map`<br>`src/pietto/_project/project_sql_plan_source_maps.py::ProjectSQLSourceMapInspection.reverse`<br>`src/pietto/_project/project_sql_plan_source_maps.py::ProjectSQLSourceMapInspection.explain` | 同一source verification；subject/origin/associations/antecedents/dependents/reverse/at/overlapping返回exact有序关系。reverse用原mapped source与occurrence，位置query保留原半开单位。 | 1-based Python text characters/newlines，非UTF-8 bytes/UTF-16/decoded literal indices。generated reason保留antecedents，缺位置不伪造/不source reread。66决定SQL ranges单位，75转换editor坐标。 |
| H07 | Explicit target / profile | `src/pietto/_project/project_sql_plan_target_assessment.py::prepare_project_sql_target_request`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::build_project_sql_target_assessment`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::verify_project_sql_target_assessment`<br>`src/pietto/_project/project_sql_plan_target_assessment.py::inspect_project_sql_target_assessment` | prepare接DATABASE target或omitted，显式base/ordered overlays/catalog；非法组合ValueError。build(source_verification, request, report_verification=...)；不一致输入归一化ValueError。verify对同request/root；inspection按demand/aspect/lookup/uses/outcome查询。 | 保留SATISFIED exact subproposition、NEGATIVE、ABSENT、UNKNOWN、CONFLICT、UNMAPPED、INAPPLICABLE、INPUT_UNRESOLVED、NOT_ASSESSED。posture分not_assessed/incomplete/complete_requirements_satisfied；corpus的真实positive subset仍incomplete。target-only须新assessment，不改neutral plan。 |
| H08 | Portable / corpus | `src/pietto/_project/project_sql_plan_portable.py::build_project_sql_plan_portable`<br>`src/pietto/_project/project_sql_plan_portable.py::verify_project_sql_plan_portable`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::parse_project_sql_plan_document`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::decode_project_sql_plan_mapping`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::evaluate_project_sql_plan_document`<br>`src/pietto/_project/project_sql_plan_pure_boundary.py::Inspection` | build接plan verification与可选verified report/source_map/assessment，返回ProjectSQLPlanPortable；TransportError带RuntimeIssue。runtime verify检查original-object bindings。bytes/text、mapping、typed Document入口有别；非OK无canonical bytes，Inspection只接受重核对的OK outcome。 | private source-bearing，不是executable deserialization；pure OK不认证source/runtime roots/DB。probe observation/render/main、batch/acquisition/readers已注册；66扩展时保持实际消费者闭包，不假定可从portable恢复原编译器对象。 |

`ProjectSQLPlanInspection.requirements/source_map/target_assessment/portable`及各report/map/assessment
inspection的portable方法是已有便利consumer，不增加public入口或改变root要求。
`verify_fixed_literal_envelope`实际位于plan verification模块。decoded portable文档使用pure
`Inspection`；不能从设计提案猜造一个`inspect_project_sql_plan_portable`入口。

Pietto已有legacy SQL generation：`src/pietto/sql/relations.py::render_relation_sql`和
`src/pietto/cli.py::main`等路径及package smoke保持有效，不能声称Pietto从无SQL。
**新ProjectSQLPlan pipeline在Phase65不交付dialect SQL AST/text emission**，也不把legacy renderer
反向引入neutral builder。Phase66的baseline multi-relation SQL/Project emit-SQL必须先进行fresh
phase-initiation discussion和route approval；此处不预设Slice数、编号路线或第一个实现Slice。

## Pending Phase66 decisions

以下均为UNAPPROVED_IMPLEMENTATION_DECISION，绑定现有证据和反例。列出native/emulated
JOIN/WINDOW/QUALIFY或hidden ORDER问题不等于选择任何策略。

| Question | Existing owner concern | Evidence-bound question |
| --- | --- | --- |
| Q01 | Target/release support domain | 哪些DATABASE/release与实际lowerer组合构成初始support matrix？D65.07/C18/C19/C32限定fact范围，catalog不是完整backend。 |
| Q02 | Physical sources / identifiers | 如何保留connector文本解释、quoting/case/length与source-family restrictions？D65.06/C17/C20；connection属68，federation仍94 tentative。 |
| Q03 | Scopes / placeholders / type anchors | 如何形成scope-injective symbols、每statement用序到logical slot映射及type anchors？D65.03/.05，C05–C07/C14/C27–C30/C40。 |
| Q04 | Hidden STRICT-FD ORDER | 何种exact realization保留visible quotient、原FD/NULL语义及unspecified ties，何时拒绝？C15/C16/C34；未批准representative/min/max。 |
| Q05 | Evidence versus implemented lowerer | 如何区分exact applicable facts与已经实现/验证的dialect strategy？C18/C19/C31/C32；native/emulated标签不是支持。 |
| Q06 | Obligations / safe emit outcomes | 未履行single-match、aggregate/risk与realization要求时，哪些emit结果允许，哪些须拒绝？C12/C21/C31/C33；不得默许executable-obligation waiver，actual fulfillment属68。 |
| Q07 | Public entrypoints / legacy compatibility | 怎样交付已归66的Project emit-SQL并保持legacy CLI/SQL，与69统一入口和82公共freeze相接？本handoff不扩大公开plan/bind API。 |
| Q08 | SQL ranges / conformance | 如何合成generated SQL ranges与原authored/generated roles，定义单位与目标BAG/NULL/order/错误conformance？C03/C04/C10/C11/C22/C35/C36/C39/C41/C43；75转换editor单位，81扩展real-DB assurance。 |

Phase67保留result/Arrow，68保留actual resources/fulfillment，70/72/73等保留既有开放、类型/等价、
聚合扩展。handoff不批准connection选择、coercion、optimizer、representative row、native/emulated
strategy、executable-obligation waiver或database execution。

## Evidence and resource domains

| Evidence | Observation class | Exact measured domain / what it establishes |
| --- | --- | --- |
| Publication table | 本次重新读取Git/authenticated CI | 固定历史commit/tree/parent、push/main/attempt1及job/step结果；不是当前工作区测试。 |
| Source and behavior assertions | 本次primary及两个内部只读reviewers重读 | P/C对应的field/root/role/order/failure，包括delegated assertion helpers；不是只找名称，也不是third-party review。 |
| Slice15 local final receipts | 历史executed，本次reread | Python3.12完整affected readers161 passed；Python3.13 authoritative14358 passed/0 skipped；generated8/golden39/package PASS。不是Slice16本次执行。 |
| Slice15 baseline CI | 已验证publication CI重读 | 两jobs各14352 passed/6 skipped，不猜skip causes、不与local14358/no-skip互换。 |
| Published phase65 corpus | 重读成功child payload和当前probe/reader断言 | 37 positives、11 source negatives、41 compact mutations、11 raw rejections是此published实例，不是永久quota。 |
| Single portable document | schema Document / private observation v1 | MAX_BYTES=8 MiB、MAX_RECORDS=32768；最大aggregate_risks为2469801 UTF-8 bytes/7403 records，未碰上限。 |
| Aggregate differential envelope | phase65 differential family v1 | 28037572 bytes/74991是37份documents汇总，不是一个Document，不能与单文档8 MiB/32768混算。 |
| Actual process denominator | Slice15两次final invocations的产物 | 每轮两个已验证available版本、86 requests/16 cells；checkout0/1/7/4294967295及relocated/installed7；same-child三个portable module origins、原62/74子域。不是manifest冒充执行。 |
| Compatibility and artifacts | 实际records/bytes/rejections/fresh installed child | 五个原canonical documents与七个historical family streams各自逐字节相同；expanded envelope不与旧five-case整体相等。全部208 packaged Python files匹配冻结生产输入。 |
| Inventory | 各自existing owner定义 | 204是non-generated production Python，208 packaged Python含4 generated Python，461→462为tests目录全部Python含support，不能和collected pytest items混算。 |

supported Python3.12/3.13不保证每个runner同时安装两者；各job运行其配置版本及其他实际发现并验证
可用的supported executable。Slice14 child的single-interpreter期待和Slice15双版本顺序修正保留，
不减少request keys、seeds、relocation/install或failure atomicity。86/16只绑定明确双版本manifest，
不冻结未来registry topology；审计没有另起full matrix只为重算表中数字。

既有Slice15仓库外receipts包括final-input-freeze-group6、两份acceptance/matrix-observation-analysis、
natural-ci-attempt1日志及final-publication；本次重读标为继承。F01/F02旧STOP、红例、失败standalone
不被PASS覆盖。旧临时日志缺失仅为observation unavailable，不反推成功/失败、不认证所有早期预算，
也不要求重构每个过去操作。

## Static principal and final acceptance

新principal复用RepositoryFactIndex source acquisition并作有限AST索引；只核对本合同/immutable
reference contracts、P/D/K/C/I/T/L/H/Q完整唯一处置、真实entrypoint/test nodes和独立核实的有限
publication inputs。无Git/network/provider调用、history-dependent skip、carrier-field snapshots、
额外source-count owner、all-source hashes或generic prose-verifier framework。静态traceability
**不是runtime correctness的替代证明**；现有behavior由既有tests和final authoritative执行。
mutable lifecycle只由现有sole lifecycle reader负责，新principal不读取它。

初始draft和预期lifecycle migration是计划工作。Slice16独立上限6 complete causal correction groups、
4 local authoritative starts、1 initial ordinary commit，余额内至多1普通CI repair child；无production
repair。四组后评估convergence，计数/失败写仓库外evidence，不能重置或借Slice15余额。

全部内容在final-input freeze前完成：focused static/lifecycle/inventory及Ruff/type checks先行，
Python3.12/3.13 focused compatibility之后执行最终门禁：

```text
UV_PYTHON=3.13 uv run python scripts/validate.py --timings
UV_PYTHON=3.13 uv run python scripts/check_generated.py
UV_PYTHON=3.13 uv run python scripts/check_goldens.py
UV_PYTHON=3.13 uv run python scripts/package_smoke.py
```

authoritative供应其既有full process/conformance覆盖，不额外复跑相同完整矩阵获取summary count。
报告分别标本次executed、重新readback、inherited、unavailable。封存实际tested tree，stage六路径后
一次普通commit/fast-forward push；自然exact-head CI决定完成。输入更改须重做适用验证/artifact证据，
无manual rerun/dispatch、force/amend/rebase或status-only follow-up。

成功后：Phase64 COMPLETED；Phase65 COMPLETED；Phase65 Slices1–16 COMPLETED/PUBLISHED；
N16 unchanged；Phase66 NEXT / NOT STARTED，fresh initiation and route approval pending。
没有批准Phase66 Slice实现，没有universal feature coverage、complete backend capability catalog、
新pipeline SQL emission、executable portable import、database conformance、redaction或fulfilled runtime obligations。

## Controlling references

- [Phase65 initiation/route lock](phase65-project-sql-plan-product-phase-initiation-gate-source-audit-architecture-route-lock-v1.md)：D65、三类ledger、C01–C43、P01–P10、N16及later atoms。
- [Product architecture](../architecture/product-architecture-v1.md)、[identity laws](../architecture/identity-and-authority-laws-v1.md)、[layering laws](../architecture/layering-and-coupling-laws-v1.md)、[phase initiation requirements](../architecture/phase-initiation-gate-v1.md)：future phase须重新讨论批准。

- [Slice2](phase65-slice2-minimal-selected-scan-projection-project-sql-plan-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice3](phase65-slice3-named-producer-graph-repeated-imported-uses-scope-local-symbols-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice4](phase65-slice4-row-scalar-let-where-stage-value-planning-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice5](phase65-slice5-seven-join-kinds-match-scopes-obligation-retention-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice6](phase65-slice6-grouped-global-satisfying-block-boundaries-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice7](phase65-slice7-windows-named-window-qualify-staging-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice8](phase65-slice8-distinct-scoped-order-static-limit-result-boundaries-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice9](phase65-slice9-set-query-expression-bodies-positional-ports-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice10](phase65-slice10-typed-fixed-literal-envelope-bind-use-layout-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice11](phase65-slice11-complete-demand-obligation-report-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice12](phase65-slice12-forward-reverse-source-map-queries-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice13](phase65-slice13-explicit-target-profile-requirement-assessment-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice14](phase65-slice14-portable-boundary-minimal-process-integration-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
- [Slice15](phase65-slice15-whole-selected-plan-real-source-differential-conformance-v1.md)：按其原支持域/current source/test owners读取，不改历史合同。
