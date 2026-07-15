# Phase 51 Slice 12 Completion Audit And Status Lock v1

## Purpose And Slice Identity

This contract defines Phase 51 Slice 12, `Completion Audit And Status Lock`,
as tests/docs/status-only completion-audit and status-lock work over the
completed Phase 51 Slices 1 through 11.

Slices 1 through 11 are complete through their separately authorized publish
gates. During Slice 12 Gate 2, Phase 51 remains ACTIVE and incomplete, Slice
12 is current but incomplete, and Phase 52–60 remain UNSTARTED.

Phase 51 remains ACTIVE and incomplete during Gate 2. Phase 52–60 remain
UNSTARTED.

Slice 12 adds no production source, compiler behavior, `_project` behavior,
diagnostic, public behavior, runtime or database behavior, dependency,
package-version change, tag, or release operation. Its exact route is
`tests/docs/status-only`.

## Authority And Evidence Hierarchy

Authority is applied in this order:

1. the current committed repository source and tests;
2. `/tmp/pietto-phase51-slice12-gate1-plan.txt`, whose SHA-256 is
   `fa6324a686e1d679baf6d288d178be9ab67fdfe4bae445f619bcc6f1d11e7ada`
   and whose final non-empty line is exactly
   `STOP: Phase 51 Slice 12 Gate 0 and Gate 1 planning complete; waiting for Phase 51 Slice 12 Gate 2.`;
3. `/tmp/pietto-phase51-slice11-gate3-evidence.txt`, whose SHA-256 is
   `5c130df05cf75f6c9e293f5bc63e4a21003ce3d94fcd34f0e533da4d16d14635`;
4. the Phase 51 plan, active roadmap, Slice 1 scope lock, and completed Slice
   2 through Slice 11 contracts and focused tests;
5. the completed Phase 49 and Phase 50 conditional completion precedents; and
6. this separately authorized Slice 12 completion contract.

The earlier stopped Slice 12 Gate 2 evidence has SHA-256
`ef6f4571c2989b43a0ab5ce683e5c072f8430a674afbb592131e15335c3a0328`
and is diagnostic history only. Its recorded ignored-cache event changes no
design, allowlist, lifecycle, completion, validation, or ownership authority.

Historical documents remain checkpoint evidence. Current committed behavior
and the active roadmap remain authoritative when historical checkpoint
wording describes an earlier unpersisted or production-inactive state.

## Trusted Slice 11 Baseline

The trusted Slice 11 baseline is:

- branch: `main`;
- HEAD and local `origin/main`:
  `5138d28ee2d0a258076a68a6f98c74ce15a93bf8`;
- parent: `ed3e79137722443677fc39b1bfe83e209bcb9868`;
- HEAD subject: `Add Phase 51 cross-phase closure`;
- parent subject: `Refresh Phase 51 Slice 9 project lock`;
- tracked worktree diff, index, and nonignored untracked set: empty;
- package version: `0.1.0`;
- tags pointing at HEAD: none;
- exact-match tag: none.

The successful Slice 11 natural CI authority is run `29371109641`, workflow
`CI`, event `push`, with `headSha` exactly
`5138d28ee2d0a258076a68a6f98c74ce15a93bf8` and conclusion `success`. It
recorded CPython 3.12.13 and CPython 3.13.14 with `5739 passed` in each job,
8 generated files, 37 golden fixtures, installed `pietto==0.1.0`, and
installed CLI `pietto 0.1.0`.

These are completed Slice 11 facts. They do not prove Slice 12 Gate 2, a
future Slice 12 commit, a future natural CI run, or Phase 51 completion.

## Phase 51 Slice Ledger

The exact Slice 1 through Slice 11 lifecycle ledger is:

| Slice | Normative title | Contract / focused test | Commit / repair authority | Natural CI / clean authority | Focused functions / items |
| ---: | --- | --- | --- | --- | ---: |
| 1 | Scope Architecture And Active-roadmap Lock | `docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md` / `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py` | `0946c7d9f81323a1fe4a711014174fd0d48035fc`, `Add Phase 51 active roadmap and scope lock`; no repair | `29210218630`, success, 5430 passed per job | 13 / 13 |
| 2 | Private Result-role And Output-identity Foundation | `docs/spec/phase51-private-result-role-output-identity-v1.md` / `tests/test_phase51_private_result_role_output_identity.py` | implementation `ac6f07e2e804a7c6bc661bf444ad16a0170930c6`, `Add Phase 51 private result role foundation`; additive repair `e81fde473d4c4d2c1eee9db032daa0b50be60e82`, `Fix Phase 51 Slice 2 plan heading lock` | initial `29214203134`, failure with 1 failed and 5449 passed; final `29215802595`, success, 5450 passed per job | 11 / 20 |
| 3 | Group-key Project Row-schema Foundation | `docs/spec/phase51-group-key-project-row-schema-foundation-v1.md` / `tests/test_phase51_group_key_project_row_schema.py` | `882600c797fb885edbfd27ba37d47607c4a5a0db`, `Add Phase 51 group-key schema foundation`; no published repair | `29224454642`, success, 5474 passed | 14 / 24 |
| 4 | Aggregate-only Project Row-schema Foundation | `docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md` / `tests/test_phase51_aggregate_only_project_row_schema.py` | `41932133ee6223ff8de90018568bebb6731d90d6`, `Add Phase 51 aggregate result candidates`; no published repair | `29232106422`, success, 5541 passed | 10 / 60 |
| 5 | Grouped Aggregate Project Row-schema Foundation | `docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md` / `tests/test_phase51_grouped_aggregate_project_row_schema.py` | `300651b2944ca45e31744bfcd269a3b575d0b090`, `Add Phase 51 grouped candidate assembly`; no repair | `29236828662`, success, 5564 passed | 13 / 21 |
| 6 | Selected-let And Accepted-expression Aggregate Integration | `docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md` / `tests/test_phase51_selected_let_accepted_expression_aggregate.py` | `98f96d32cc4af67bb8703398f2116a4e55b56460`, `Add Phase 51 aggregate expression candidates`; no repair | `29280446165`, success, 5616 passed | 12 / 61 |
| 7 | Type Nullability Availability-state And Duplicate Handling | `docs/spec/phase51-type-nullability-availability-state-duplicate-handling-v1.md` / `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py` | `122b7efa50f2383badf328803b82ef5ba7fb96f4`, `Add Phase 51 aggregate state finalization`; no repository repair | `29288413076`, success, 5639 passed | 17 / 23 |
| 8 | Clause-dependency And Fail-closed Hardening | `docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md` / `tests/test_phase51_clause_dependency_fail_closed.py` | `fa0622331dfe3e11fe6b762c7e0a215794ca3f6c`, `Add Phase 51 clause dependency readiness`; no published repair | `29301595259`, success, 5702 passed | 29 / 63 |
| 9 | Origin Provenance Dependency And Lineage Integration | `docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md` / `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py` | `8370045ba686e99273b6b0138378fd09bac0806f`, `Add Phase 51 origin dependency lineage`; no slice-content repair; separate interpreter-integrity repair `9908d7f15594cc27d45885613a4a4bf350bea32d`, `Fix CI matrix interpreter binding` | implementation `29310398020`, success, 5716 passed; integrity `29314629944`, success, 5716 passed under real CPython 3.12 and 3.13 | 12 / 14 |
| 10 | Downstream Propagation And Qualification | `docs/spec/phase51-downstream-propagation-qualification-v1.md` / `tests/test_phase51_aggregate_grouped_downstream_propagation.py` | implementation `39a58d50b8e5ef420cb637c42124422c1d82911d`, `Add Phase 51 downstream propagation`; static-lock repair `ed3e79137722443677fc39b1bfe83e209bcb9868`, `Refresh Phase 51 Slice 9 project lock` | initial `29325365925`, failure with 1 failed and 5731 passed; final `29326813216`, success, 5732 passed under CPython 3.12.13 and 3.13.14 | 16 / 16 |
| 11 | Cross-phase Readiness Privacy And Compatibility Closure | `docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md` / `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py` | `5138d28ee2d0a258076a68a6f98c74ce15a93bf8`, `Add Phase 51 cross-phase closure`; no repair | `29371109641`, success, 5739 passed | 7 / 7 |

The exact Slice 1 through Slice 11 focused inventory is 154 top-level test
functions and 322 pytest items. Slice 12 adds exactly 11 top-level tests and
11 pytest items, so the Slice 1 through Slice 12 inventory is 165 top-level
tests and 333 items. The Slice 12 focused file has no parametrization.

The only independent published repair heads that define final slice authority
are Slice 2 `e81fde4` and Slice 10 `ed3e791`. Commit `9908d7f` is a separate
CI interpreter-integrity repair between Slices 9 and 10, not a slice-content
migration. Pre-publish corrections in Slices 3, 4, 7, and 8 are not additional
published repair commits. Dependency-only maintenance commits after Slices 5
and 8 are not Phase 51 content repairs.

## Phase 51 Artifact Inventory

The dedicated governance artifacts are:

- `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`;
- `docs/spec/pietto-active-roadmap-phase51-60-v1.md`.

The exact Slice 1 through Slice 11 contracts and focused tests are:

| Slice | Contract | Focused test |
| ---: | --- | --- |
| 1 | `docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md` | `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py` |
| 2 | `docs/spec/phase51-private-result-role-output-identity-v1.md` | `tests/test_phase51_private_result_role_output_identity.py` |
| 3 | `docs/spec/phase51-group-key-project-row-schema-foundation-v1.md` | `tests/test_phase51_group_key_project_row_schema.py` |
| 4 | `docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md` | `tests/test_phase51_aggregate_only_project_row_schema.py` |
| 5 | `docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md` | `tests/test_phase51_grouped_aggregate_project_row_schema.py` |
| 6 | `docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md` | `tests/test_phase51_selected_let_accepted_expression_aggregate.py` |
| 7 | `docs/spec/phase51-type-nullability-availability-state-duplicate-handling-v1.md` | `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py` |
| 8 | `docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md` | `tests/test_phase51_clause_dependency_fail_closed.py` |
| 9 | `docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md` | `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py` |
| 10 | `docs/spec/phase51-downstream-propagation-qualification-v1.md` | `tests/test_phase51_aggregate_grouped_downstream_propagation.py` |
| 11 | `docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md` | `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py` |

The Phase 51 private production foundation is bounded to the existing files:

- `src/pietto/_project/model.py`;
- `src/pietto/_project/aggregate_grouped_schema.py`;
- `src/pietto/_project/aggregate_grouped_clause_facts.py`;
- `src/pietto/_project/aggregate_grouped_dependency_lineage.py`;
- `src/pietto/_project/aggregate_grouped_persistence.py`;
- `src/pietto/_project/row_dependency_graph.py`;
- `src/pietto/_project/row_lineage.py`.

Slice 12 adds exactly this contract and
`tests/test_phase51_completion_audit_and_status_lock.py`; it updates only the
Phase 51 plan and the active roadmap. It adds no production artifact.

## Historical Allowlist And Repair Preservation

Every historical Gate 2 allowlist remains exact and is not widened by Slice
12. The complete membership ledger is:

- Slice 1, 4 paths: `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`,
  `docs/spec/pietto-active-roadmap-phase51-60-v1.md`,
  `docs/spec/phase51-aggregate-grouped-output-schema-foundation-scope-lock-v1.md`,
  `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py`.
- Slice 2, 13 paths: `src/pietto/_project/model.py`,
  `tests/test_phase51_private_result_role_output_identity.py`, the Phase 51
  plan, `docs/spec/phase51-private-result-role-output-identity-v1.md`, the
  eight boundary-lock tests `tests/test_phase11_ci_workflow.py`,
  `tests/test_phase11_completion_audit.py`,
  `tests/test_phase11_generated_guard.py`,
  `tests/test_phase11_golden_policy.py`,
  `tests/test_phase11_packaging_smoke.py`,
  `tests/test_phase11_validation_entrypoint.py`,
  `tests/test_phase12_completion_audit.py`,
  `tests/test_phase12_composition_cli_json_goldens.py`, and
  `tests/test_phase33_completion_audit.py`.
- Slice 2 additive repair, 1 path: the Phase 51 plan only.
- Slice 3, 13 paths: `src/pietto/_project/aggregate_grouped_schema.py`,
  `tests/test_phase51_group_key_project_row_schema.py`, the Phase 51 plan,
  `docs/spec/phase51-group-key-project-row-schema-foundation-v1.md`, the same
  eight boundary-lock tests, and `tests/test_phase33_completion_audit.py`.
- Slice 4, 14 paths: `src/pietto/_project/aggregate_grouped_schema.py`,
  `tests/test_phase51_aggregate_only_project_row_schema.py`,
  `tests/test_phase51_group_key_project_row_schema.py`, the Phase 51 plan,
  `docs/spec/phase51-aggregate-only-result-candidate-foundation-v1.md`, the
  same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 5, 13 paths: `src/pietto/_project/aggregate_grouped_schema.py`,
  `tests/test_phase51_grouped_aggregate_project_row_schema.py`, the Phase 51
  plan, `docs/spec/phase51-grouped-key-aggregate-candidate-assembly-v1.md`,
  the same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 6, 15 paths: `src/pietto/_project/aggregate_grouped_schema.py`,
  `tests/test_phase51_selected_let_accepted_expression_aggregate.py`,
  `tests/test_phase51_aggregate_only_project_row_schema.py`,
  `tests/test_phase51_grouped_aggregate_project_row_schema.py`, the Phase 51
  plan, `docs/spec/phase51-aggregate-expression-row-let-candidate-integration-v1.md`,
  the same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 7, 16 paths: `src/pietto/_project/model.py`,
  `src/pietto/_project/aggregate_grouped_schema.py`,
  `src/pietto/_project/row_dependency_graph.py`,
  `src/pietto/_project/row_lineage.py`,
  `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`, the
  Phase 51 plan,
  `docs/spec/phase51-type-nullability-availability-state-duplicate-handling-v1.md`,
  the same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 8, 13 paths: `src/pietto/_project/aggregate_grouped_clause_facts.py`,
  `tests/test_phase51_clause_dependency_fail_closed.py`, the Phase 51 plan,
  `docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md`, the
  same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 9, 15 paths:
  `src/pietto/_project/aggregate_grouped_dependency_lineage.py`,
  `src/pietto/_project/row_dependency_graph.py`,
  `src/pietto/_project/row_lineage.py`,
  `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`, the
  Phase 51 plan,
  `docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md`,
  the same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- The separate interpreter-integrity repair after Slice 9 changed exactly
  `.github/workflows/ci.yml` and `tests/test_phase11_ci_workflow.py`; it is
  not a Slice 9 content allowlist extension.
- Slice 10, 38 paths: `src/pietto/_project/model.py`,
  `src/pietto/_project/aggregate_grouped_persistence.py`,
  `src/pietto/_project/aggregate_grouped_schema.py`,
  `src/pietto/_project/aggregate_grouped_clause_facts.py`,
  `src/pietto/_project/aggregate_grouped_dependency_lineage.py`,
  `src/pietto/_project/row_dependency_graph.py`,
  `src/pietto/_project/row_lineage.py`,
  `tests/test_phase51_aggregate_grouped_downstream_propagation.py`, all eight
  earlier Slice 2–9 focused tests, the eleven transition tests
  `tests/test_phase47_downstream_readiness_hardening.py`,
  `tests/test_phase48_upstream_non_concrete_schema_propagation.py`,
  `tests/test_phase48_query_to_query_multi_hop_propagation.py`,
  `tests/test_phase49_computed_alias_project_row_schema_mvp.py`,
  `tests/test_phase49_computed_alias_origin_provenance_privacy.py`,
  `tests/test_phase49_private_row_level_dependency_graph_scaffold.py`,
  `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py`,
  `tests/test_phase49_computed_let_multi_hop_row_lineage.py`,
  `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`,
  `tests/test_phase49_let_visibility_order_shadowing_hardening.py`,
  `tests/test_phase49_selected_let_derived_output_schema.py`, the Phase 51
  plan, `docs/spec/phase51-downstream-propagation-qualification-v1.md`, the
  same eight boundary-lock tests, and
  `tests/test_phase33_completion_audit.py`.
- Slice 10 static-lock repair, 1 path:
  `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py` only.
- Slice 11, 20 paths: the Phase 51 plan,
  `docs/spec/phase51-cross-phase-readiness-privacy-compatibility-closure-v1.md`,
  `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py`,
  the nine transition tests
  `tests/test_phase47_downstream_readiness_hardening.py`,
  `tests/test_phase48_upstream_non_concrete_schema_propagation.py`,
  `tests/test_phase48_query_to_query_multi_hop_propagation.py`,
  `tests/test_phase49_computed_alias_project_row_schema_mvp.py`,
  `tests/test_phase49_computed_alias_origin_provenance_privacy.py`,
  `tests/test_phase49_computed_let_multi_hop_row_lineage.py`,
  `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`,
  `tests/test_phase49_let_visibility_order_shadowing_hardening.py`, and
  `tests/test_phase49_selected_let_derived_output_schema.py`, plus all eight
  Slice 2–9 focused tests.

The exact seventeen live identifier migrations, each present once as a
top-level definition in its exact module, are:

1. `tests/test_phase47_downstream_readiness_hardening.py`:
   `test_aggregate_projection_schema_is_concrete_with_persisted_fact`.
2. `tests/test_phase48_upstream_non_concrete_schema_propagation.py`:
   `test_computed_alias_and_aggregate_are_concrete_while_pure_grouping_stays_deferred`.
3. `tests/test_phase48_query_to_query_multi_hop_propagation.py`:
   `test_computed_alias_let_and_aggregate_are_concrete_while_pure_grouping_stays_deferred`.
4. `tests/test_phase49_computed_alias_project_row_schema_mvp.py`:
   `test_unknown_null_division_stay_non_concrete_while_aggregate_is_concrete`.
5. `tests/test_phase49_computed_alias_origin_provenance_privacy.py`:
   `test_let_and_aggregate_outputs_are_concrete_while_pure_grouping_stays_deferred`.
6. `tests/test_phase49_computed_let_multi_hop_row_lineage.py`:
   `test_non_concrete_lineage_is_empty_while_grouped_aggregate_lineage_is_concrete`.
7. `tests/test_phase49_let_visibility_order_shadowing_hardening.py`:
   `test_invalid_grouped_selected_let_output_schema_is_unknown`.
8. `tests/test_phase49_selected_let_derived_output_schema.py`:
   `test_unresolved_upstream_is_blocked_and_invalid_grouped_let_output_is_unknown`.
9. `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py`:
   `test_grouped_aggregate_schema_graph_and_lineage_are_concrete_without_public_diagnostics`.
10. `tests/test_phase51_private_result_role_output_identity.py`:
    `test_aggregate_and_grouped_relations_are_concrete_with_persisted_facts`.
11. `tests/test_phase51_group_key_project_row_schema.py`:
    `test_pure_grouping_stays_deferred_while_grouped_aggregate_is_concrete`.
12. `tests/test_phase51_aggregate_only_project_row_schema.py`:
    `test_aggregate_and_grouped_outputs_are_persisted_private_and_unserialized`.
13. `tests/test_phase51_grouped_aggregate_project_row_schema.py`:
    `test_aggregate_grouped_outputs_are_concrete_private_persisted_and_unserialized`.
14. `tests/test_phase51_selected_let_accepted_expression_aggregate.py`:
    `test_expression_and_row_let_aggregate_relations_are_concrete_private_and_persisted`.
15. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py`:
    `test_aggregate_grouped_production_is_persisted_private_and_downstream_active`.
16. `tests/test_phase51_clause_dependency_fail_closed.py`:
    `test_aggregate_grouped_production_persists_graph_lineage_and_activates_downstream`.
17. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py`:
    `test_origin_dependency_lineage_production_is_persisted_and_downstream_active`.

The exact seventeen superseded identifiers remain absent from live tracked
tests and documentation. This contract does not reintroduce a superseded
identifier as a contiguous token. The two historical modules that shared one
old name remain distinct and each has its own exact replacement above.

The exact 29 clean-only Gate 2 guards are:

1. `tests/test_phase51_private_result_role_output_identity.py::test_forbidden_compiler_dependency_and_lineage_surfaces_have_no_diff`
2. `tests/test_phase51_group_key_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff`
3. `tests/test_phase51_aggregate_only_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff`
4. `tests/test_phase51_grouped_aggregate_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff`
5. `tests/test_phase51_selected_let_accepted_expression_aggregate.py::test_plan_contract_versions_protected_boundaries_and_exact_dirty_set`
6. `tests/test_phase51_aggregate_grouped_state_duplicate_hardening.py::test_slice7_documentation_exact_allowlist_and_protected_boundaries`
7. `tests/test_phase51_clause_dependency_fail_closed.py::test_slice8_documentation_exact_allowlist_dirty_and_protected_boundaries`
8. `tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py::test_slice9_documentation_allowlist_hash_and_protected_boundaries`
9. `tests/test_phase51_aggregate_grouped_downstream_propagation.py::test_slice10_documentation_allowlist_hashes_and_protected_boundaries`
10. `tests/test_phase47_downstream_readiness_hardening.py::test_phase47_slice9_package_version_and_dirty_paths_are_locked`
11. `tests/test_phase48_upstream_non_concrete_schema_propagation.py::test_phase48_slice7_package_version_and_dirty_paths_are_locked`
12. `tests/test_phase48_query_to_query_multi_hop_propagation.py::test_phase48_slice5_package_version_and_dirty_paths_are_locked`
13. `tests/test_phase49_computed_alias_project_row_schema_mvp.py::test_slice4_keeps_forbidden_project_files_untouched`
14. `tests/test_phase49_computed_alias_project_row_schema_mvp.py::test_phase49_slice4_package_version_and_dirty_paths_are_locked`
15. `tests/test_phase49_computed_alias_origin_provenance_privacy.py::test_slice5_forbidden_project_files_are_untouched`
16. `tests/test_phase49_computed_alias_origin_provenance_privacy.py::test_slice5_package_version_and_dirty_paths_are_locked`
17. `tests/test_phase49_private_row_level_dependency_graph_scaffold.py::test_slice9_forbidden_files_have_no_diff`
18. `tests/test_phase49_private_row_level_dependency_graph_scaffold.py::test_slice9_package_version_and_dirty_paths_are_locked`
19. `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py::test_slice10_forbidden_files_have_no_diff`
20. `tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py::test_slice10_package_version_and_dirty_paths_are_locked`
21. `tests/test_phase49_computed_let_multi_hop_row_lineage.py::test_slice11_forbidden_files_source_boundaries_version_and_dirty_paths`
22. `tests/test_phase49_unknown_deferred_diagnostic_ordering_hardening.py::test_slice12_forbidden_files_package_version_and_dirty_paths_are_locked`
23. `tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_slice8_forbidden_files_have_no_diff`
24. `tests/test_phase49_let_visibility_order_shadowing_hardening.py::test_slice8_package_version_and_dirty_paths_are_locked`
25. `tests/test_phase49_selected_let_derived_output_schema.py::test_slice7_forbidden_files_remain_unchanged`
26. `tests/test_phase49_selected_let_derived_output_schema.py::test_slice7_package_version_and_dirty_paths_are_locked`
27. `tests/test_phase51_aggregate_grouped_output_schema_foundation_scope_lock.py::test_historical_roadmap_package_tag_goldens_protected_diffs_and_dirty_set`
28. `tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_slice13_package_version_and_dirty_paths_are_locked`
29. `tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_slice11_contract_plan_allowlist_and_protected_boundaries_are_locked`

All 29 guards remain mandatory in clean natural CI. Their Gate 2 deselection
does not count as a pass. Slice 12 adds an independent dirty-safe live-lock
test and does not migrate or weaken an existing clean-only guard.

## Final Capability Classification

The final capability classes are: 1 = complete and directly tested, 2 =
complete but only indirectly tested, 3 = deferred to one explicit later
owner, 4 = contradiction requiring Slice 12 migration, and 5 = outside the
Pietto product charter. No capability is class 4, and Slice 12 implements no
class 3 or class 5 capability.

| Capability family | Class | Final disposition |
| --- | ---: | --- |
| private result roles, output identities, aggregate facts | 1 | exact private carriers and identities are complete |
| aggregate-only and grouped key-plus-aggregate schema | 1 | current legal selected outputs are concrete |
| selected-let and admitted-expression aggregate schema | 1 | only already-admitted current semantics are covered |
| type and nullability propagation | 1 | current canonical semantic facts only |
| four availability states and exact reasons | 1 | `CONCRETE`, `UNKNOWN`, `DEFERRED`, `BLOCKED`; no fifth state |
| duplicate output and duplicate group-key handling | 1 | private no-winner outcomes are locked |
| transient clause readiness | 1 | remains unpersisted and separate from lineage |
| dependency graph and lineage | 1 | argument, relation-input, let ancestry, immediate and transitive facts are complete |
| private persistence and downstream propagation | 1 | atomic six-map, completed-last, one-hop and multi-hop behavior is complete |
| diagnostics and non-concrete suppression | 1 | existing codes, messages, order, and fail-closed boundaries are unchanged |
| private serialization absence and public artifacts | 1 | direct privacy and compatibility assertions are complete |
| parser, semantic, IR, PostgreSQL, private MySQL compatibility | 1 | compiler digest and exact selectors remain unchanged |
| pure grouping and broader aggregate/grouping work | 3 | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| project IR | 3 | `POST60_PROJECT_IR` |
| project SQL | 3 | `POST60_MULTI_RELATION_SQL` |
| runtime and database execution as a feature | 5 | `OUT_OF_SCOPE_CHARTER` |

No category 2 row is needed to close Phase 51. No cleanup, speculative
refactor, extensibility hook, or future-owner listing creates production-code
authority for Slice 12.

## Result And Schema Foundation Audit

The completed private result/schema surface locks:

- `ProjectRowResultRole.ORDINARY_ROW_VALUE`, `GROUP_KEY`, and
  `AGGREGATE_RESULT`;
- group-key source identity and selected-output identity;
- aggregate function, output name, grouped posture, argument count, and
  location facts;
- concrete current legal aggregate-only, grouped key-plus-aggregate,
  selected-let, and admitted-expression outputs;
- canonical current type propagation;
- count-family non-nullability and current nullable rules for
  `sum`/`avg`/`min`/`max`;
- exact states `CONCRETE`, `UNKNOWN`, `DEFERRED`, and `BLOCKED`;
- exact state/reason precedence and non-concrete payload shape; and
- duplicate output and duplicate group-key no-winner behavior.

The exact dataclass field-order ledger is:

- `ProjectRowField`: `name`, `resolved_type`, `nullability`, `field_def`,
  `provenance`, `result_role`;
- `ProjectAggregateResultFact`: `function`, `output_name`, `grouped`,
  `argument_count`, `location`;
- `ProjectGroupKeyFact`: `item`, `effective_expression`, `field_identity`,
  `input_field`;
- `ProjectGroupKeySchemaFacts`: `group_keys`, `selected_fields`;
- `ProjectAggregateSelectedResult`: `field`, `fact`;
- `ProjectAggregateSchemaFacts`: `selected_results`;
- `ProjectGroupedSelectedResult`: `field`, `aggregate_fact`;
- `ProjectGroupedSchemaFacts`: `group_keys`, `selected_results`;
- `ProjectAggregateGroupedCandidateAttempt`: `facts`, `failure_reason`;
- `ProjectAggregateGroupedSchemaFinalization`: `state`,
  `aggregate_result_facts`;
- `ProjectRelationClauseDependencyFact`: `kind`, `source_occurrence`,
  `target_occurrence`, `target_field`, `aggregate_result_fact`;
- `ProjectAggregateGroupedClauseReadiness`: `definition`, `finalization`,
  `status`, `reason`, `dependency_facts`, `limit_present`;
- `ProjectAggregateGroupedDependencyLineageReadiness`: `definition`,
  `clause_readiness`, `dependency_graph`, `lineage`;
- `ProjectAggregateGroupedPersistenceBundle`: `definition`,
  `let_scope_facts`, `dependency_lineage_readiness`, `state`,
  `aggregate_result_facts`.

The exact keyword-only builder-signature ledger is:

- `build_project_group_key_schema_facts`: `definition`, `input_schema`,
  `upstream_symbol`, `fallback_path`;
- `build_project_aggregate_schema_facts`: `definition`, `input_schema`,
  `upstream_symbol`, `fallback_path`;
- `build_project_grouped_schema_facts`: `definition`, `input_schema`,
  `upstream_symbol`, `fallback_path`;
- `build_project_aggregate_grouped_schema_finalization`: `definition`,
  `input_schema`, `upstream_symbol`, `fallback_path`, `let_scope_facts`;
- `build_project_aggregate_grouped_clause_readiness`: `definition`,
  `input_schema`, `upstream_symbol`, `fallback_path`, `let_scope_facts`;
- `build_project_aggregate_grouped_dependency_lineage_readiness`:
  `definition`, `input_schema`, `upstream_symbol`, `upstream_lineage`,
  `fallback_path`, `let_scope_facts`;
- `build_project_aggregate_grouped_persistence`: `definition`,
  `input_schema`, `upstream_symbol`, `upstream_lineage`, `fallback_path`.

Field order, keyword-only posture, and signature order are compatibility
locks. Slice 12 adds no carrier, field, builder, parameter, default, or public
constructor.

## Dependency And Lineage Audit

Clause readiness remains transient and unpersisted. The exact readiness kinds
remain group-key input, satisfying output, grouped-order output, and static
limit presence. Clause facts do not become output lineage.

The completed dependency and lineage surface preserves:

- one nested `ProjectAggregateGroupedClauseReadiness` identity inside one
  `ProjectAggregateGroupedDependencyLineageReadiness`;
- exact state/reason coherence across finalization, readiness, graph, and
  lineage;
- aggregate argument leaves in expression AST left-to-right order with
  first-target dedupe;
- relation-input dependency for `count()` without a fabricated field leaf;
- ancestry of admitted selected-let aggregate arguments;
- immediate lineage before its transitive expansion;
- deterministic graph node and edge order; and
- identity preservation from one readiness build into persistence.

No lineage ancestry creates a lookup name. No graph or lineage fact becomes
public, serialized, IR, SQL, runtime, or database state.

## Private Persistence And Downstream Propagation Audit

The private production path has one canonical persistence adapter, one
canonical let-fact object retained across nested builders, and exactly one
Slice 9 readiness call for each eligible complete definition. Unresolved,
cyclic, or non-concrete upstream definitions perform zero such calls.

One coherent logical operation publishes or clears exactly six maps:

1. `relation_row_schemas`;
2. `relation_row_schema_states`;
3. `relation_let_scope_facts`;
4. `relation_aggregate_result_facts`;
5. `relation_row_dependency_graphs`; and
6. `relation_row_lineages`.

A definition enters the completed set only after all six maps are coherent.
No provisional schema, partial insertion, stale concrete payload, duplicate
winner, build-then-overwrite graph, or independently reconstructed lineage is
permitted.

Concrete `TableDef` and `QueryDef` outputs propagate through one-hop and
multi-hop dependency-first chains. Downstream fields reset to ordinary result
role. Lookup remains limited to a bare selected output or its immediate
upstream relation qualifier. An original source, earlier relation, multi-part
lineage path, unselected group key, hidden aggregate argument, or hidden let
binding remains unavailable downstream.

## Failure And Diagnostic Audit

The exact private failure outcomes remain:

| Condition | Exact outcome |
| --- | --- |
| pure grouping | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED`, empty schema/facts/graph/lineage, diagnostic-free |
| invalid grouped selected-let | `UNKNOWN / INVALID_AGGREGATE_OR_GROUPED_OUTPUT`, empty unknown payload, no new diagnostic |
| duplicate selected output | `UNKNOWN / DUPLICATE_OUTPUT_NAME`, empty unknown payload, no first/last winner, diagnostic-free |
| duplicate group-key identity | `UNKNOWN / DUPLICATE_GROUP_KEY`, no winner |
| unavailable type, nullability, or fact | `UNKNOWN / UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT`, no partial bundle |
| explicitly deferred family | `DEFERRED / AGGREGATE_OR_GROUPED_DEFERRED` |
| conflicting private facts | `BLOCKED / CONFLICTING_AGGREGATE_OR_GROUPED_FACTS` |
| unresolved relation | `BLOCKED / UNRESOLVED_RELATION_BLOCKED`, existing `PIE-S2301` only |
| relation cycle | `BLOCKED / CYCLE_BLOCKED`, existing `PIE-S2302` only |
| upstream unknown | downstream `UNKNOWN / UPSTREAM_UNKNOWN`, no fabricated field diagnostic |
| upstream deferred | downstream `DEFERRED / UPSTREAM_DEFERRED`, no fabricated field diagnostic |
| upstream blocked | downstream `BLOCKED / UPSTREAM_BLOCKED`, no fabricated field diagnostic |

Slice 12 adds no diagnostic code, message, severity, location, ordering rule,
JSON field, or CLI error behavior. Public order remains `PIE-S2301`, then a
legitimately reachable `PIE-S2102`, then `PIE-S2302`; source-definition and
occurrence order remains authoritative within each family. `PIE-S2102` is
reachable only after a concrete upstream activates. `UNKNOWN`, `DEFERRED`,
and `BLOCKED` upstream states do not fabricate a downstream diagnostic.

## Public Artifact Compatibility Audit

Project JSON v2 retains exactly this top-level key order:

1. `schema_version`;
2. `command`;
3. `mode`;
4. `ok`;
5. `project`;
6. `inputs`;
7. `diagnostics`;
8. `cli_errors`;
9. `result`.

CLI JSON v1 remains a separate single-file envelope. Semantic Metadata
Artifact v1 and `pietto explain FILE` remain separate single-file surfaces.
The bounded public PostgreSQL API remains unchanged; the MySQL renderer
remains private. Project JSON v2, CLI JSON v1, Artifact v1, explain text,
Semantic IR, and SQL receive no field, key-order, schema-version, placeholder,
null, redaction, private-only marker, or compatibility-alias change.

`src/pietto/__init__.py` remains docstring-only. `pietto._project.__all__`,
`aggregate_grouped_clause_facts.__all__`,
`aggregate_grouped_dependency_lineage.__all__`, and
`aggregate_grouped_persistence.__all__` remain empty. No private Phase 51
carrier, enum, helper, builder, adapter, graph, lineage, readiness object, or
model map is publicly exported.

Parse-only project checking remains parse-only. Parser-error and other
pre-semantic failure paths continue to bypass project semantic evaluation,
finalization, readiness, persistence, dependency, lineage, and downstream
work.

The final diagnostic, privacy, public, and compiler compatibility matrix is:

| Surface | Current or future lock | Class | Slice 12 action |
| --- | --- | ---: | --- |
| diagnostics | no new code or message; `PIE-S2102`, `PIE-S2301`, and `PIE-S2302` preserved | 1 | assert only |
| duplicate private state | `UNKNOWN`, empty, diagnostic-free | 1 | assert only |
| non-concrete suppression | unknown, deferred, and blocked do not cascade | 1 | assert only |
| CLI JSON v1 | unchanged | 1 | exact selector |
| Project JSON v2 | unchanged nine-key order | 1 | exact selector |
| Artifact v1 and explain | unchanged and separate | 1 | exact selector |
| public Python API | unchanged | 1 | export and static lock |
| private serialization | Phase 51 carriers absent | 1 | negative token and key assertions |
| parse-only and parser-error | unchanged bypass behavior | 1 | exact selectors |
| grammar, parser, and AST | unchanged | 1 | compiler digest |
| single-file semantics | accepted and rejected language unchanged | 1 | compatibility selectors |
| Semantic IR | unchanged | 1 | compiler digest |
| PostgreSQL and private MySQL SQL | unchanged | 1 | compiler digest and clean CI |
| `_project` production | exact Slice 10 private foundation | 1 | carrier, signature, and behavior locks |
| project IR | deferred | 3 | `POST60_PROJECT_IR` |
| project SQL | deferred | 3 | `POST60_MULTI_RELATION_SQL` |
| runtime and database execution | excluded | 5 | `OUT_OF_SCOPE_CHARTER` |

## Private Carrier Privacy Audit

The following remain private and unserialized:

- `relation_row_schemas`;
- `relation_row_schema_states`;
- `relation_let_scope_facts`;
- `relation_aggregate_result_facts`;
- `relation_row_dependency_graphs`;
- `relation_row_lineages`;
- result-role, group-key, aggregate-result, state, reason, availability,
  clause-readiness, dependency, lineage, and persistence-bundle carriers;
- field origin and provenance facts; and
- every immediate and transitive graph or lineage fact.

Serialization contains none of those private map or carrier tokens. The
existing public `inputs[].status` field is part of Project JSON v2 and is not
a private carrier state. Unknown, absent, null, redacted, private-only,
conflicting, unresolved, unsupported, and unavailable remain distinct; no
missing or conflicting private fact receives a fabricated value or winner.

## Single-file Compiler IR SQL Runtime And Database Compatibility Audit

Slice 12 adds no grammar, generated parser, AST, parser behavior, accepted or
rejected single-file semantic behavior, Semantic IR model/lowering,
PostgreSQL rendering, private MySQL rendering, CLI command or option, JSON
serializer, public Python API, diagnostic, fixture, golden, example, script,
workflow, dependency, lockfile, package metadata, runtime, database,
connection, credential, SQL execution, transaction, introspection, server
validation, network, or executable-plugin behavior.

The compiler input count and digest, exact compatibility selectors, parser
error and parse-only bypass tests, public artifact tests, and future clean CI
are the compatibility authorities. Phase 51 changes no source-language
surface and implements no project IR, project SQL, relationship/JOIN/grain,
or runtime/database behavior.

Runtime/database execution remains `OUT_OF_SCOPE_CHARTER`, not an incomplete
Phase 51 deliverable.

## Compiler And Project-private Lock Audit

The compiler digest algorithm covers `Makefile`, `grammar/Pietto.g4`, and
every regular file below `src/pietto` except `__pycache__` and `.pyc` files,
using sorted relative paths and repeated relative-path/NUL/content/NUL bytes.
The exact compiler input count is 75 and the digest is
`2ed54ba89c64c89d9d9bfc26f83041faf0addb335f086bd2e75dc2a567be775c`.

All eight `BOUNDARY_HASH` assignments equal that exact digest in:

1. `tests/test_phase11_ci_workflow.py`;
2. `tests/test_phase11_completion_audit.py`;
3. `tests/test_phase11_generated_guard.py`;
4. `tests/test_phase11_golden_policy.py`;
5. `tests/test_phase11_packaging_smoke.py`;
6. `tests/test_phase11_validation_entrypoint.py`;
7. `tests/test_phase12_completion_audit.py`;
8. `tests/test_phase12_composition_cli_json_goldens.py`.

The `_project` digest uses the same sorted path/NUL/content/NUL encoding. Its
exact regular-file count is 16 and its digest is
`c032a23c7f0477df58cacc9374e2882bebad346bec9a539899878da062248013`.
The `project_private` count and digest in
`tests/test_phase33_completion_audit.py` are exactly 16 and that same digest.

These locks are dirty-safe current values. Slice 12 refreshes none of them and
changes no compiler or `_project` path.

## Deferred-owner Audit

No deferral becomes anonymous, reopened, transferred, or implemented. Exact
owners remain:

| Deferred family | Exact owner |
| --- | --- |
| aggregate filters | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| aggregate-internal ordering | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| aggregate modifiers and generic `DISTINCT` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| `count_if` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| broad `count_distinct(expression)` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| `min/max(expression)` | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| pure grouping | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| rollup, cube, grouping sets | `POST60_ADVANCED_AGGREGATION_GROUPING` |
| broader type, temporal, coercion, Decimal, domain, native mapping | `POST60_ADVANCED_TYPE_NATIVE_MAPPING` |
| exact-current private capability facts and fail-closed lookup | `PHASE_52` |
| initial ranking windows | `PHASE_53` |
| advanced windows | `POST60_ADVANCED_WINDOWS` |
| local module/import/export minimum | `PHASE_54` |
| advanced module/package assets | `POST60_ADVANCED_MODULE_PACKAGE_ASSETS` |
| local semantic-package manifest/assets/loading | `PHASE_55` |
| remote package manager | `POST60_REMOTE_PACKAGE_MANAGER` |
| dependency solver/lockfile | `POST60_DEPENDENCY_SOLVER_LOCKFILE` |
| private capability profiles/checking | `PHASE_56` |
| PostgreSQL extension catalog/matching/seeds | `PHASE_57` |
| extension-specific lowering | `POST60_EXTENSION_LOWERING` |
| minimal public project/portability/package projection | `PHASE_58` |
| wider public project schema/lineage/package graph | `POST60_PUBLIC_PROJECT_SCHEMA_LINEAGE_EXPANSION` |
| local exact package graph/private attribution | `PHASE_59` |
| ecosystem-coherence and residual-owner audit checkpoint | `PHASE_60` |
| project IR | `POST60_PROJECT_IR` |
| project SQL / project emit-sql | `POST60_MULTI_RELATION_SQL` |
| JOIN/relationship/grain/fanout | `POST60_RELATIONSHIP_JOIN_GRAIN_FANOUT` |
| database connections, SQL execution, introspection, server validation | `OUT_OF_SCOPE_CHARTER` |

Phase 51-owned A01–A08 obligations are satisfied by the completed foundation.
That closure transfers no residual owner and authorizes no later work.

## Phase 52 Handoff

Phase 52 remains the unique owner of a private, immutable, deterministic,
exact-current type-system capability carrier and fail-closed lookup. It may
later consume generic Phase 51 logical type/nullability and result-role facts,
but Phase 51 provides no Phase 52 implementation authority.

After successful Slice 12 Gate 3, Phase 51 is COMPLETED. Phase 52–60 remain
UNSTARTED. Phase 52 is the next planned but unstarted target, and its exact
next separately authorized gate is `Phase 52 Slice 1 Gate 0 and Gate 1`.

Phase 52 is not marked ACTIVE, NEXT, implemented, or complete by this
contract. No Phase 52 type, literal, cast, operator, coercion, promotion,
aggregate, Decimal, temporal, UUID/Enum, native-mapping, capability API,
public metadata, CLI/JSON, IR, SQL, or backend behavior begins in Phase 51
Gate 2 or Gate 3.

## Package Version And Release Audit

Package version and installed CLI version remain `0.1.0`. No tag points at
the trusted Slice 11 baseline and there is no exact-match tag.

Slice 12 performs no package-version change, dependency change, package
metadata change, tag, release, publish, upload, signing, attestation,
package-registry operation, or future release claim. Conditional Phase 51
completion is an internal repository lifecycle fact, not a package release.

No future Slice 12 commit SHA, CI run ID, URL, `headSha`, conclusion, release
identifier, or tag appears in Gate 2 repository wording.

## Protected Surface Audit

The exact protected hashes are:

| Path | SHA-256 / lock |
| --- | --- |
| `.github/workflows/ci.yml` | `8ad82ff09677901971d79d4fec689f2cc265fb35adca71649d8890115efcb88d` |
| `.python-version` | `7b55f8e67b5623c4bef3fa691288da9437d79d3aba156de48d481db32ac7d16d` |
| `pyproject.toml` | `b051191df2210a907cafbfb753df0368ba0b91a8043727da5f9668965e121edf` |
| `uv.lock` | `97b9bebd286bc45c168551a81eeb6df852331622507ea998b1fcb1acc19217b5` |
| `docs/spec/pietto-roadmap-phase45-60-v1.md` | `26cc0ae4a68518223d6bf600ad3c4b0b226618aa7ef31b2ae1c25924d2655169` |
| pre-Slice-12 `docs/spec/pietto-active-roadmap-phase51-60-v1.md` bytes | `2de797d68fd621bf6198cc19f24e07bbb4e101c13683bfa8792614d479af3c75` |

Workflow, interpreter policy, dependencies, lockfile, historical roadmap,
compiler, all eight `BOUNDARY_HASH` values, `_project`, Phase 33, package
version, tags, fixtures, goldens, examples, scripts, Makefile, public
artifacts, and release surfaces remain unchanged.

The active-roadmap change is authorized only as one EOF append. Its complete
pre-Slice-12 bytes, including the original final newline, remain a byte-exact
prefix with SHA-256
`2de797d68fd621bf6198cc19f24e07bbb4e101c13683bfa8792614d479af3c75`.
No existing roadmap H2, initial-ledger sentence, phase route, phase title,
delivery class, or owner assignment changes.

## Completion Encoding Decision

The selected model is exactly:

`conditional single-commit completion plus exact Gate 3 natural-CI evidence`

Gate 2 records a condition and does not claim that it has been satisfied.
Gate 3 stages the exact four paths, creates one commit, performs one normal
push to `main`, and observes only the natural `CI / push` run whose `headSha`
exactly matches that commit.

Phase 51 is complete only if that natural run is `completed / success` for
the exact commit and supplies every required clean-CI proof. When the
condition is satisfied, the conditional repository wording is true and the
Phase 51 lifecycle is COMPLETED.

No post-CI repository status-flip commit is planned or required. Phase 52–60
remain UNSTARTED and Phase 52 does not start automatically.

## Gate 2 Pre-completion State

During Gate 2:

- Slices 1 through 11 are complete;
- Slice 12 is current and incomplete;
- Phase 51 remains ACTIVE and incomplete;
- Phase 52–60 remain UNSTARTED;
- the exact route is `tests/docs/status-only`;
- no Gate 2 PASS, Gate 3 success, Slice 12 completion, Phase 51 completion,
  or Phase 52 activation is preclaimed; and
- no future Slice 12 commit SHA or CI run ID is recorded.

The expected bounded validation total of `499 passed, 29 deselected` and the
future clean total of `5750 passed` are expectations, not current claims.
Gate 2 leaves the exact four paths dirty and unstaged and waits for separately
authorized Gate 3.

## Gate 3 Completion Condition

Phase 51 is complete only after Slice 12 Gate 3 stages exactly the four
allowlisted paths, creates one normal commit, performs one normal push to
`main`, and observes the natural `CI / push` run with `headSha` exactly equal
to that commit and conclusion `completed / success`.

The clean run must prove 5750 passed under both real CPython 3.12 and CPython
3.13 jobs, all 29 clean-only guards, generated 8, goldens 37, package
build/smoke, installed `pietto==0.1.0`, installed CLI `pietto 0.1.0`, no tag,
and final `main == origin/main` with a clean worktree and index and zero
untracked paths.

The exact future commit SHA, push identity, natural CI run ID, URL,
conclusion, interpreter output, and `headSha` match belong only in Gate 3
evidence. Gate 2 records none of them. Natural CI failure stops Gate 3 and
hands off to a separately authorized read-only repair Gate 1; it does not
authorize a same-turn repair or manual CI operation.

## Post-completion Phase 52–60 Status

After the Gate 3 condition is satisfied, Phase 51 is COMPLETED as the
twelve-slice Aggregate / Grouped Project Output-Schema Foundation. Phase
52–60 remain UNSTARTED and separately gated.

Phase 52 is only the next planned target. It is not ACTIVE, automatically
authorized, implemented, or complete. The exact next gate is
`Phase 52 Slice 1 Gate 0 and Gate 1`.

Phase 51 completion authorizes no later phase, post-60 deferral, compiler
expansion, public artifact, package release, runtime, database, relationship,
JOIN, grain, project IR, or project SQL work.

## Active-roadmap Reconciliation

The active roadmap receives exactly one EOF-only H3:

`### Reconciliation 1 — Phase 51 Conditional Completion And Phase 52 Handoff`

It records these eight protocol facts:

1. the previous entry is the initial base route and there was no prior
   reconciliation;
2. trusted evidence through Slice 11 is HEAD `5138d28...` and natural CI
   `29371109641`;
3. old and new phase names, routes, and delivery classes are identical;
4. owner additions, removals, and transfers are none;
5. before activation, Phase 51 is ACTIVE and incomplete and Phase 52–60 are
   UNSTARTED;
6. activation requires the exact Slice 12 commit, one normal push, and a
   `completed / success` natural CI run with exact `headSha`;
7. after activation, Phase 51 is COMPLETED and Phase 52–60 remain UNSTARTED;
8. no deferral becomes anonymous and no Phase 52 implementation, version,
   tag, release, runtime, database, public, or compiler behavior is
   authorized.

The future exact commit SHA and CI run ID belong only in Gate 3 evidence. No
post-CI flip commit is required. Phase 52 is next planned but UNSTARTED; its
exact next gate is `Phase 52 Slice 1 Gate 0 and Gate 1`.

The existing Reconciliation Ledger H2 and the historical initial-base
sentence remain byte-for-byte in the locked prefix. The marker occurs once in
the active roadmap. The base H2 order remains unchanged.

## Exact Gate 2 Allowlist

Slice 12 Gate 2 may create or modify exactly these four unstaged paths, in
this exact order:

1. `docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md`
2. `docs/spec/pietto-active-roadmap-phase51-60-v1.md`
3. `docs/spec/phase51-completion-audit-and-status-lock-v1.md`
4. `tests/test_phase51_completion_audit_and_status_lock.py`

The expected final Git-visible state is exactly two modified tracked paths,
the two new nonignored untracked paths at items 3 and 4, four dirty paths
total, and an empty index. A clean tree is accepted before implementation or
after later authorized publication; while Gate 2 changes exist, the set may
only be an approved subset and must end as the exact state above.

The plan receives one additive H3 only. The active roadmap receives one EOF
append only. This contract and the focused test are the only new files. Every
other Git-visible path is forbidden, including every `src/pietto` path,
grammar/generated path, existing Slice 1–11 contract/test, boundary lock,
Phase 33 lock, workflow, script, dependency, lockfile, package, fixture,
golden, example, historical roadmap, public API, version, tag, and release
surface.

## Validation And Clean-CI Boundary

The new focused file has exactly ten helpers, in this order:

1. `_read`;
2. `_normalized`;
3. `_headings`;
4. `_git_output`;
5. `_dirty_paths`;
6. `_digest`;
7. `_compiler_digest`;
8. `_project_private_paths`;
9. `_top_level_functions`;
10. `_pytest_inventory`.

It has exactly eleven unparametrized tests, eleven pytest items, and 21 total
top-level functions. The exact ordered test inventory is:

1. `test_slice12_artifacts_title_and_exact_heading_order_are_locked`;
2. `test_slice1_11_lifecycle_artifact_and_focused_item_ledgers_are_exact`;
3. `test_result_schema_carrier_field_orders_and_builder_signatures_are_locked`;
4. `test_dependency_lineage_persistence_and_downstream_completion_is_locked`;
5. `test_failure_diagnostic_and_non_concrete_behavior_remains_compatible`;
6. `test_project_json_public_exports_and_private_serialization_boundaries_are_locked`;
7. `test_deferred_owner_phase52_handoff_and_active_roadmap_reconciliation_are_locked`;
8. `test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe`;
9. `test_historical_allowlists_migrations_and_clean_only_guards_are_accounted`;
10. `test_completion_encoding_gate2_gate3_and_no_release_boundaries_are_locked`;
11. `test_static_git_helper_and_exact_slice12_dirty_set_are_locked`.

The static selector authority is 57 files, 318 selected top-level test
functions, 181 parametrized expansions, 499 selected pytest items, 29
deselected pytest items, zero selected/deselected overlap, and zero missing,
duplicate, stale, or wrong-module selectors. Phase 51 Slices 1–12 account for
165 focused top-level tests and 333 focused pytest items.

The exact ordered Gate 2 matrix is:

| Step | Scope | Expected result |
| --- | --- | --- |
| A | Ruff format check, new focused file only | PASS |
| B | Ruff lint, new focused file only | PASS |
| C | test-project Pyright, new focused file only | 0 errors |
| D | new Slice 12 focused file | 11 passed |
| E | Slice 11 focused file, guard 29 deselected | 6 passed, 1 deselected |
| F | Slice 2–9 focused files, guards 1–8 deselected | 278 passed, 8 deselected |
| G | Slice 10 focused file, guard 9 deselected | 15 passed, 1 deselected |
| H | Phase 47–49 transition files, guards 10–26 deselected | 110 passed, 17 deselected |
| I | Phase 44 parse-only file | 5 passed |
| J | Slice 1 scope-lock file, guard 27 deselected | 12 passed, 1 deselected |
| K | Phase 49 compatibility/privacy/hash file, guard 28 deselected | 6 passed, 1 deselected |
| L | exact 38 compatibility/hash/static selectors | 38 passed |
| M | exact 16 public/explain/Phase 50/Phase 52 selectors | 18 passed |

The bounded aggregate expectation is exactly `499 passed, 29 deselected`.
The 29 deselected guards remain mandatory in clean natural CI. Full pytest,
`scripts/validate.py`, generated checks, golden checks, package smoke, build,
installed CLI, GitHub, and CI are outside Gate 2 validation.

The current clean authority is 5739 passed. Slice 12 adds 11 items and removes
none, so the future clean full-suite expectation is exactly 5750 passed under
each real CPython 3.12 and CPython 3.13 natural-CI job. Future clean CI also
proves all 29 guards, generated 8, goldens 37, package smoke, installed
package 0.1.0, and installed CLI 0.1.0. These are future expectations, not
Gate 2 claims.

## Separate Authorization Boundary

Slice 12 Gate 2 authorizes only the exact four-path documentation/static-audit
set. It does not authorize staging, commit, push, fetch, pull, merge, rebase,
reset, restore, clean, stash, GitHub/CI operation, tag, release, publish,
upload, signing, or attestation.

Gate 3 requires separate explicit authorization. Gate 3 is publish and
observation only: it may not edit repository files, rerun local validation,
manually trigger, rerun, or cancel CI, or repair a failed natural run.

Phase 52 Slice 1 Gate 0 and Gate 1 require separate explicit authorization.
No route listing, owner mapping, handoff, completion statement, future
artifact name, or successful Phase 51 run automatically starts or implements
Phase 52–60 or any post-60 work.

## Stop Conditions

Stop without staging, completion claim, repair, or scope expansion if:

- a controlling evidence identity, trusted baseline, package version, tag,
  compiler, `_project`, `BOUNDARY_HASH`, Phase 33, protected hash, or
  historical-roadmap lock differs;
- any Git-visible path outside the exact four-path allowlist changes, an
  unexpected nonignored untracked path appears, or the index is non-empty;
- the plan additive reconstruction fails or its Slice 12 H3 is missing,
  duplicated, misplaced, or unconditional;
- the active-roadmap edit is not EOF-only, its original prefix differs, or
  the reconciliation marker is missing or duplicated;
- this H1, the exact 28-H2 order, focused helper/test order, count,
  parametrization, selector, or deselection inventory differs;
- any historical allowlist, lifecycle, repair, CI, capability, carrier,
  signature, migration, clean-only guard, diagnostic, privacy, public,
  compiler, or deferred-owner fact differs;
- Gate 2 preclaims a future commit, push, natural CI run/result, Slice 12
  completion, Phase 51 completion, Phase 52 activation, tag, or release;
- Phase 52–60 cease to be UNSTARTED;
- a production, compiler, grammar, generated, semantic, IR, SQL, CLI, JSON,
  diagnostic, public, workflow, dependency, version, runtime, database,
  package, or release surface changes;
- static selector analysis differs from 499 selected items and 29 exact
  deselections, or bounded validation differs from `499 passed, 29 deselected`;
- the conditional single-commit model or no-post-CI-flip rule cannot remain
  exact;
- an architecture, behavior, diagnostic, public-contract, lifecycle,
  ownership, release, or item-count ambiguity requires a wider change; or
- a second validation failure occurs after the one permitted same-task repair.

Gate 2 success, if separately proved by complete evidence, leaves exactly the
four allowlisted paths dirty and unstaged and waits for separately authorized
Phase 51 Slice 12 Gate 3. Until that Gate 3 condition succeeds, Phase 51
remains ACTIVE and incomplete and Phase 52–60 remain UNSTARTED.
