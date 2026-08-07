from __future__ import annotations

import ast
import builtins
from dataclasses import fields, replace
import inspect
from itertools import permutations
import json
from pathlib import Path
from typing import cast

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_semantic_fact_preservation as preservation
from pietto import cli
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import ProjectLetScopeFactsStatus
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.window_semantics import (
    WindowDependencyRole,
    deduplicate_window_dependency_edges,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    GroupByItem,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    WindowExpr,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
)
from pietto.semantic.capability_lookup import Absent, Conflict, Found, Unknown
from pietto.semantic.window_semantics import (
    RankingAdvancePolicy,
    WindowExpressionAnalysis,
    WindowExpressionUnsupported,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = "docs/spec/phase54-slice12-semantic-fact-preservation-v1.md"
SOURCE_REL = "src/pietto/_project/module_semantic_fact_preservation.py"
TEST_REL = "tests/test_phase54_semantic_fact_preservation.py"

EXPECTED_TEST_NAMES = (
    "test_slice12_contract_status_active_manifest_and_allowlist_are_exact",
    "test_private_preservation_carriers_fields_enums_and_privacy_are_exact",
    "test_capability_family_inventory_counts_order_and_exact_raw_facts_are_preserved",
    "test_capability_lookup_preserves_found_absent_unknown_conflict_and_duplicate_folding",
    "test_window_signature_formula_inventory_preserves_all_eight_identities_exactly",
    "test_result_role_inventory_is_exact_separate_and_source_ordered",
    "test_schema_v1_has_no_sidecar_and_text_json_ir_sql_bytes_remain_exact",
    "test_schema_v2_builds_sidecar_from_exact_slice10_authority_without_slice11_input",
    "test_builder_rejects_value_equal_or_misaligned_foreign_authority_roots",
    "test_zero_relation_fact_environment_and_lookup_are_exact",
    "test_source_relation_fact_retains_exact_slice10_owner_state_and_order",
    "test_local_computed_output_preserves_expression_type_nullability_origin_and_role",
    "test_imported_computed_output_preserves_local_lookup_and_nominal_target",
    "test_aliased_import_keeps_qualifier_separate_from_nominal_target_identity",
    "test_explicit_reexport_keeps_direct_facade_lookup_and_original_nominal_target",
    "test_same_spelling_cross_module_relations_and_fields_never_merge",
    "test_same_target_through_two_local_aliases_retains_two_identity_distinct_facts",
    "test_relation_and_output_cardinalities_zero_one_two_three_have_no_truncation",
    "test_module_definition_and_fact_permutations_change_only_explicit_tuple_order",
    "test_complete_tuple_lookups_retain_middle_tail_and_duplicate_occurrences",
    "test_unknown_upstream_state_and_reason_propagate_without_child_inference",
    "test_deferred_upstream_state_and_reason_propagate_without_concretization",
    "test_blocked_unresolved_reference_retains_issue_root_and_empty_candidates",
    "test_ambiguous_relation_bucket_retains_every_occurrence_without_winner",
    "test_local_and_module_cycles_retain_complete_roots_without_guessed_facts",
    "test_let_binding_ledger_preserves_source_order_duplicates_visibility_and_status",
    "test_let_derived_output_preserves_type_nullability_origin_dependency_and_role",
    "test_select_output_collision_preserves_every_candidate_and_never_overwrites",
    "test_group_keys_preserve_source_order_visibility_fields_and_result_roles",
    "test_aggregate_results_preserve_function_arguments_type_nullability_origin_and_role",
    "test_aggregate_dependency_occurrences_preserve_repetition_before_derived_dedup",
    "test_satisfying_aggregate_candidate_bucket_preserves_all_matches_without_first_winner",
    "test_grouped_order_let_candidate_bucket_preserves_all_matching_outputs",
    "test_aggregate_grouped_concrete_unknown_deferred_and_blocked_states_are_atomic",
    "test_all_eight_window_families_preserve_complete_composite_analysis",
    "test_navigation_offset_default_generic_and_nullability_formula_evidence_is_exact",
    "test_window_partition_order_and_direction_bindings_preserve_order_and_duplicates",
    "test_multiple_window_outputs_preserve_global_ordinals_and_every_output",
    "test_mixed_window_outcomes_scan_all_candidates_and_publish_no_partial_schema",
    "test_window_dependency_occurrences_preserve_duplicates_and_edges_first_dedupe_only",
    "test_ordinary_group_aggregate_and_window_result_roles_remain_distinct_in_one_relation",
    "test_nominal_generic_same_spelling_types_fail_closed_without_cross_module_merge",
    "test_sidecar_builder_is_pure_over_preloaded_inputs_and_performs_no_io",
    "test_schema_v2_public_api_cli_json_metadata_ir_sql_dependencies_version_and_goldens_are_unchanged",
)


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in sources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _semantic_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, sources, schema_version=schema_version)
    )
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _fact_set(
    semantic: ProjectSemanticResult,
) -> preservation.ProjectModuleSemanticFactSet:
    facts = semantic.module_semantic_facts
    assert facts is not None
    return facts


def _relation(
    semantic: ProjectSemanticResult,
    module_path: str,
    name: str,
) -> preservation.ProjectModuleRelationSemanticFacts:
    matches = tuple(
        fact
        for environment in _fact_set(semantic).environments
        for fact in environment.relation_facts
        if fact.owner.identity.module_path == module_path
        and fact.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _replace_relation_in_final_semantic(
    semantic: ProjectSemanticResult,
    original: preservation.ProjectModuleRelationSemanticFacts,
    replacement: preservation.ProjectModuleRelationSemanticFacts,
) -> ProjectSemanticResult:
    facts = _fact_set(semantic)
    environments = tuple(
        replace(
            environment,
            relation_facts=tuple(
                replacement if fact is original else fact
                for fact in environment.relation_facts
            ),
        )
        if any(fact is original for fact in environment.relation_facts)
        else environment
        for environment in facts.environments
    )
    replaced_facts = replace(facts, environments=environments)
    return replace(semantic, module_semantic_facts=replaced_facts)


def _replace_window_in_final_semantic(
    semantic: ProjectSemanticResult,
    relation: preservation.ProjectModuleRelationSemanticFacts,
    original: preservation.ProjectModuleWindowOutputFact,
    replacement: preservation.ProjectModuleWindowOutputFact,
) -> ProjectSemanticResult:
    replaced_relation = replace(
        relation,
        window_outputs=tuple(
            replacement if output is original else output
            for output in relation.window_outputs
        ),
    )
    return _replace_relation_in_final_semantic(
        semantic,
        relation,
        replaced_relation,
    )


def _library_source(*, export_relation: str = "table projected") -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        "    name: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount\n"
        "        name\n"
        f"export:\n    {export_relation}\n"
    )


def _prefix() -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        "    category: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
    )


def _query(body: str) -> str:
    return _prefix() + "query result:\n    from rows\n" + body


def _unavailable_candidate_body(
    expressions: tuple[str, ...],
    *,
    relation_qualifier: str,
) -> str:
    lines = ["    let:"]
    lines.extend(f"        key = {expression}" for expression in expressions)
    lines.extend(
        (
            f"        qualified_key = {relation_qualifier}.id",
            "        wrong_qualified_key = other.id",
        )
    )
    lines.extend(
        (
            "    group by:",
            "        id",
            "    select:",
            "        projected = key",
            f"        qualified_projected = {relation_qualifier}.id",
            "        wrong_qualified_projected = other.id",
        )
    )
    lines.extend(f"        total = sum({expression})" for expression in expressions)
    lines.extend(
        (
            "    satisfying:",
            "        total > 0",
            "    order by:",
            "        total",
        )
    )
    return "\n".join(lines) + "\n"


def _assert_unavailable_candidate_matrix(
    tmp_path: Path,
    *,
    source_head: str,
    relation_status: ProjectRelationRowSchemaStatus,
    relation_reason: ProjectRelationRowSchemaReason,
    bucket_status: preservation.ProjectModuleCandidateBucketStatus,
    relation_qualifier: str,
    expect_issues: bool = False,
) -> None:
    expression_orders = (
        (),
        ("id",),
        ("id", "amount"),
        *tuple(permutations(("id", "amount", "id + amount"))),
    )
    for case_ordinal, expressions in enumerate(expression_orders):
        _, semantic = _semantic_project(
            tmp_path / f"case-{case_ordinal}",
            {
                "main.pietto": source_head
                + _unavailable_candidate_body(
                    expressions,
                    relation_qualifier=relation_qualifier,
                )
            },
        )
        relation = _relation(semantic, "main.pietto", "result")
        definition = cast(QueryDef, relation.owner.definition)
        expected_lets = (
            ()
            if definition.let_clause is None
            else tuple(
                binding
                for binding in definition.let_clause.bindings
                if binding.name == "key"
            )
        )
        expected_outputs = tuple(
            item for item in definition.select_items if item.alias == "total"
        )
        projected = next(
            item for item in relation.select_facts if item.output_name == "projected"
        )
        assert relation.state.status is relation_status
        assert relation.state.reason is relation_reason
        assert relation.aggregate_result_facts == ()
        assert all(item.aggregate_result_fact is None for item in relation.select_facts)
        assert len(projected.references) == 1
        assert projected.references[0].let_candidates == expected_lets
        assert projected.references[0].status is bucket_status
        qualified_references = (
            next(
                fact
                for fact in relation.let_bindings
                if fact.binding.name == "qualified_key"
            ).references[0],
            next(
                fact
                for fact in relation.let_bindings
                if fact.binding.name == "wrong_qualified_key"
            ).references[0],
            next(
                fact
                for fact in relation.select_facts
                if fact.output_name == "qualified_projected"
            ).references[0],
            next(
                fact
                for fact in relation.select_facts
                if fact.output_name == "wrong_qualified_projected"
            ).references[0],
        )
        assert tuple(reference.role for reference in qualified_references) == (
            preservation.ProjectModuleFactOccurrenceRole.LET_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.LET_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
            preservation.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
        )
        for reference in qualified_references:
            assert type(reference.expression) is DottedNameExpr
            assert reference.input_field is None
            assert reference.let_candidates == ()
            assert reference.selected_output_candidates == ()
            assert reference.status is bucket_status
        dependencies = {fact.role: fact for fact in relation.clause_dependencies}
        group_key = dependencies[preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY]
        satisfying = dependencies[
            preservation.ProjectModuleFactOccurrenceRole.SATISFYING
        ]
        grouped_order = dependencies[
            preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
        ]
        assert group_key.status is bucket_status
        assert group_key.target_occurrences == ()
        for dependency in (satisfying, grouped_order):
            assert dependency.status is bucket_status
            assert dependency.target_occurrences == expected_outputs
            assert dependency.target_fields == ()
            assert dependency.aggregate_result_facts == ()
        if relation_status is ProjectRelationRowSchemaStatus.UNKNOWN:
            assert relation.state.schema is not None
            assert relation.state.schema.fields == {}
        else:
            assert relation.state.schema is None
        if expect_issues:
            assert _fact_set(semantic).issues


def _window_call(identity: str) -> str:
    if identity in {
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
    }:
        return f"{identity}()"
    if identity == "ntile":
        return "ntile(4)"
    if identity == "lag":
        return "lag(amount, 2, amount)"
    return "lead(amount, 0, amount)"


def _window_lines(identities: tuple[str, ...]) -> str:
    lines = ["    select:", "        id"]
    for position, identity in enumerate(identities):
        lines.extend(
            (
                f"        w{position} = {_window_call(identity)} window:",
                "            partition by:",
                "                category",
                "            order by:",
                "                id desc",
            )
        )
    return "\n".join(lines) + "\n"


def test_slice12_contract_status_active_manifest_and_allowlist_are_exact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    assert "Slice 10 is the sole semantic authority root" in spec
    assert "Every identity-distinct occurrence remains distinct" in spec
    assert "Slice 13 is the first authorized join" in spec
    assert "Slice 12 Gate 2 candidate" in plan
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE12_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "bc46faff1c9aa71f583ed7d2964b651cc659bc90"
    )
    assert active_gate2_manifest.ADDED_PATHS == {SPEC_REL, SOURCE_REL, TEST_REL}
    assert len(active_gate2_manifest.NON_READER_MODIFIED_PATHS) == 6
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 173
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 179
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 182
    assert (
        sum(path.endswith(".py") for path in active_gate2_manifest.ALLOWLIST_PATHS)
        == 178
    )
    assert "173-reader" in spec
    assert "exact 178 Python paths" in spec
    assert "exact `A3_M179_D0`" in spec
    assert "65-reader" not in spec
    assert "exact 69 Python paths" not in spec
    assert "`A3_M70_D0`" not in spec
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
        == 158
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_SEED_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_SEED_PATHS | {SPEC_REL}
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_READER_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_READER_PATHS
    )
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
        == 159
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_SEED_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_SEED_PATHS
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_READER_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_READER_PATHS
    )
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS)
        == 159
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_SEED_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_SEED_PATHS
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_READER_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_READER_PATHS
    )
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS)
        == 159
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_SEED_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_SEED_PATHS
    )
    assert active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_READER_PATHS == (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_READER_PATHS
    )
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS)
        == 159
    )
    assert active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_SEED_PATHS == {
        "tests/_phase54_active_gate2_manifest.py",
        TEST_REL,
    }
    assert active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_READER_PATHS == {
        "tests/test_phase50_import_module_export_readiness.py",
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_completion_audit_and_status_lock.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase52_aggregate_signature_algebra_facts.py",
        "tests/test_phase52_completion_audit_and_status_lock.py",
        "tests/test_phase52_expression_stage_clause_capability_facts.py",
        "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
        "tests/test_phase52_scalar_function_operator_signature_facts.py",
        "tests/test_phase53_completion_audit_and_status_lock.py",
        "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
        "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
        "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
        "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
        "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
        "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
    }
    assert (
        len(active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS)
        == 21
    )
    assert not active_gate2_manifest.phase54_slice12_product_repair11_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair12_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair13_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair14_is_active()
    publication_states = (
        active_gate2_manifest.phase54_slice12_product_repair14_clean_topic_is_active(),
        active_gate2_manifest.phase54_slice12_mechanical_repair3_is_active(),
        active_gate2_manifest.phase54_slice12_mechanical_repair3_clean_topic_is_active(),
    )
    assert sum(publication_states) == 1
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()
    child = "1" * 40
    other_child = "2" * 40
    tree = "3" * 40
    other_tree = "4" * 40
    trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_REVIEWED_TREE_TRAILER
    )
    subject = active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_SUBJECT
    message = f"{subject}\n\n{trailer_key}: {tree}"
    clean_topic_state = active_gate2_manifest.Phase54Gate2RepositoryState(
        marker=active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER,
        branch_oid=child,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH}"
        ),
        ahead=0,
        behind=0,
        added_paths=frozenset(),
        modified_paths=frozenset(),
        deleted_paths=frozenset(),
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )

    def exact_git_output(arguments: list[str]) -> str:
        values = {
            ("rev-parse", "--verify", "HEAD^{commit}"): child,
            ("rev-list", "--parents", "-n", "1", child): (
                f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR10_BASE}"
            ),
            ("show", "-s", "--format=%s", child): subject,
            ("show", "-s", "--format=%T", child): tree,
            ("rev-parse", "--verify", "refs/heads/main"): (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
            ),
            ("rev-parse", "--verify", "refs/remotes/origin/main"): (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
            ),
        }
        return values[tuple(arguments)]

    monkeypatch.setattr(active_gate2_manifest, "_git_output", exact_git_output)
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: clean_topic_state,
    )
    assert active_gate2_manifest._matches_phase54_slice12_product_repair10_clean_topic(
        clean_topic_state
    )
    invalid_messages = (
        subject,
        f"{subject}\n\n{trailer_key}: {other_tree}",
        f"{message}\n{trailer_key}: {tree}",
        f"{subject}\n\n{trailer_key}: {other_tree}\n{trailer_key}: {tree}",
        f"{subject}\n\n{trailer_key.lower()}: {tree}\n{trailer_key}: {tree}",
        f"{subject}\n\n {trailer_key}: {tree}\n{trailer_key}: {tree}",
        f"{subject}\n\n{trailer_key} : {tree}",
        f"{message}\n\nOther-Trailer: value",
        f"{message} ",
        f"{subject}\n\n{trailer_key}: {tree[:-1]}",
        f"{subject}\n\n{trailer_key}: {tree}z",
    )
    for invalid_message in invalid_messages:
        assert not active_gate2_manifest._phase54_slice12_product_repair10_message_matches_tree(
            invalid_message,
            tree,
        )
    assert not active_gate2_manifest._phase54_slice12_product_repair10_message_matches_tree(
        message,
        other_tree,
    )

    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            clean_topic_state,
            other_paths=frozenset({"persistent-state-drift"}),
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair10_clean_topic(
            clean_topic_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: clean_topic_state,
    )
    head_reads = iter((child, other_child))

    def moving_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(head_reads)
        return exact_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_head_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair10_clean_topic(
            clean_topic_state
        )
    )
    main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in main_ref_reads
        ):
            read = main_ref_reads[reference]
            main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_main_refs_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair10_clean_topic(
            clean_topic_state
        )
    )
    assert main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }

    repair11_subject = active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_SUBJECT
    repair11_trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_REVIEWED_TREE_TRAILER
    )
    repair11_message = f"{repair11_subject}\n\n{repair11_trailer_key}: {tree}"
    repair11_clean_state = replace(
        clean_topic_state,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH}"
        ),
    )
    repair11_git_values = {
        ("rev-parse", "--verify", "HEAD^{commit}"): child,
        ("rev-list", "--parents", "-n", "1", "HEAD"): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BASE}"
        ),
        ("rev-list", "--parents", "-n", "1", child): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BASE}"
        ),
        ("show", "-s", "--format=%s", "HEAD"): repair11_subject,
        ("show", "-s", "--format=%s", child): repair11_subject,
        ("show", "-s", "--format=%T", child): tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
    }

    def exact_repair11_git_output(arguments: list[str]) -> str:
        return repair11_git_values[tuple(arguments)]

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        exact_repair11_git_output,
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair11_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair11_clean_state,
    )
    assert active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
        repair11_clean_state
    )
    assert (
        active_gate2_manifest.phase54_slice12_product_repair11_clean_topic_is_active()
    )
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    repair11_dirty_state = replace(
        repair11_clean_state,
        branch_oid=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
        modified_paths=(
            active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS
        ),
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        repair11_dirty_state
    )
    repair10_compatible_state = replace(
        repair11_dirty_state,
        modified_paths=repair11_dirty_state.modified_paths - {SPEC_REL},
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        repair10_compatible_state
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair10_compatible_state,
    )
    assert active_gate2_manifest.phase54_slice12_product_repair10_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair11_is_active()
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            repair11_dirty_state,
            modified_paths=repair11_dirty_state.modified_paths | {"unauthorized-path"},
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair11_dirty_state,
    )
    assert active_gate2_manifest.phase54_slice12_product_repair11_is_active()

    repair11_parent_key = ("rev-list", "--parents", "-n", "1", child)
    repair11_git_values[repair11_parent_key] = f"{child} {'5' * 40}"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    repair11_git_values[repair11_parent_key] = (
        f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR11_BASE}"
    )
    repair11_subject_key = ("show", "-s", "--format=%s", child)
    repair11_git_values[repair11_subject_key] = "Wrong Repair11 subject"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    repair11_git_values[repair11_subject_key] = repair11_subject
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: (
            f"{repair11_subject}\n\n{repair11_trailer_key}: {other_tree}"
            if revision == child
            else ""
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair11_message if revision == child else "",
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            replace(
                repair11_clean_state,
                other_paths=frozenset({"dirty-state-drift"}),
            )
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            repair11_clean_state,
            staged_paths=frozenset({"post-read-state-drift"}),
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair11_clean_state,
    )
    repair11_head_reads = iter((child, other_child))

    def moving_repair11_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(repair11_head_reads)
        return exact_repair11_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair11_head_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    repair11_main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_repair11_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in repair11_main_ref_reads
        ):
            read = repair11_main_ref_reads[reference]
            repair11_main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_repair11_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair11_main_refs_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair11_clean_topic(
            repair11_clean_state
        )
    )
    assert repair11_main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }

    repair12_subject = active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_SUBJECT
    repair12_trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_REVIEWED_TREE_TRAILER
    )
    repair12_message = f"{repair12_subject}\n\n{repair12_trailer_key}: {tree}"
    repair12_clean_state = replace(
        clean_topic_state,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH}"
        ),
    )
    repair12_git_values = {
        ("rev-parse", "--verify", "HEAD^{commit}"): child,
        ("rev-list", "--parents", "-n", "1", "HEAD"): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BASE}"
        ),
        ("rev-list", "--parents", "-n", "1", child): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BASE}"
        ),
        ("show", "-s", "--format=%s", "HEAD"): repair12_subject,
        ("show", "-s", "--format=%s", child): repair12_subject,
        ("show", "-s", "--format=%T", child): tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
    }

    def exact_repair12_git_output(arguments: list[str]) -> str:
        return repair12_git_values[tuple(arguments)]

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        exact_repair12_git_output,
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair12_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair12_clean_state,
    )
    assert active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
        repair12_clean_state
    )
    assert (
        active_gate2_manifest.phase54_slice12_product_repair12_clean_topic_is_active()
    )
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    repair12_dirty_state = replace(
        repair12_clean_state,
        branch_oid=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
        modified_paths=(
            active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS
        ),
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        repair12_dirty_state
    )
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            repair12_dirty_state,
            modified_paths=repair12_dirty_state.modified_paths | {"unauthorized-path"},
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair12_dirty_state,
    )
    assert active_gate2_manifest.phase54_slice12_product_repair12_is_active()

    repair12_parent_key = ("rev-list", "--parents", "-n", "1", child)
    repair12_git_values[repair12_parent_key] = f"{child} {'5' * 40}"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    repair12_git_values[repair12_parent_key] = (
        f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR12_BASE}"
    )
    repair12_subject_key = ("show", "-s", "--format=%s", child)
    repair12_git_values[repair12_subject_key] = "Wrong Repair12 subject"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    repair12_git_values[repair12_subject_key] = repair12_subject
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: (
            f"{repair12_subject}\n\n{repair12_trailer_key}: {other_tree}"
            if revision == child
            else ""
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair12_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            repair12_clean_state,
            staged_paths=frozenset({"post-read-state-drift"}),
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair12_clean_state,
    )
    repair12_head_reads = iter((child, other_child))

    def moving_repair12_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(repair12_head_reads)
        return exact_repair12_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair12_head_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    repair12_main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_repair12_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in repair12_main_ref_reads
        ):
            read = repair12_main_ref_reads[reference]
            repair12_main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_repair12_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair12_main_refs_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair12_clean_topic(
            repair12_clean_state
        )
    )
    assert repair12_main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }

    repair13_subject = active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_SUBJECT
    repair13_trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_REVIEWED_TREE_TRAILER
    )
    repair13_message = f"{repair13_subject}\n\n{repair13_trailer_key}: {tree}"
    repair13_clean_state = replace(
        clean_topic_state,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH}"
        ),
    )
    repair13_git_values = {
        ("rev-parse", "--verify", "HEAD^{commit}"): child,
        ("rev-list", "--parents", "-n", "1", child): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_BASE}"
        ),
        ("show", "-s", "--format=%s", child): repair13_subject,
        ("show", "-s", "--format=%T", child): tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
    }

    def exact_repair13_git_output(arguments: list[str]) -> str:
        return repair13_git_values[tuple(arguments)]

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        exact_repair13_git_output,
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair13_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair13_clean_state,
    )
    assert active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
        repair13_clean_state
    )
    assert (
        active_gate2_manifest.phase54_slice12_product_repair13_clean_topic_is_active()
    )
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    repair13_dirty_state = replace(
        repair13_clean_state,
        branch_oid=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
        modified_paths=(
            active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS
        ),
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        repair13_dirty_state
    )
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            repair13_dirty_state,
            modified_paths=repair13_dirty_state.modified_paths | {"unauthorized-path"},
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair13_dirty_state,
    )
    assert active_gate2_manifest.phase54_slice12_product_repair13_is_active()

    repair13_parent_key = ("rev-list", "--parents", "-n", "1", child)
    repair13_git_values[repair13_parent_key] = f"{child} {'5' * 40}"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    repair13_git_values[repair13_parent_key] = (
        f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR13_BASE}"
    )
    repair13_subject_key = ("show", "-s", "--format=%s", child)
    repair13_git_values[repair13_subject_key] = "Wrong Repair13 subject"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    repair13_git_values[repair13_subject_key] = repair13_subject
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: (
            f"{repair13_subject}\n\n{repair13_trailer_key}: {other_tree}"
            if revision == child
            else ""
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair13_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            repair13_clean_state,
            staged_paths=frozenset({"post-read-state-drift"}),
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair13_clean_state,
    )
    repair13_head_reads = iter((child, other_child))

    def moving_repair13_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(repair13_head_reads)
        return exact_repair13_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair13_head_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    repair13_main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_repair13_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in repair13_main_ref_reads
        ):
            read = repair13_main_ref_reads[reference]
            repair13_main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_repair13_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair13_main_refs_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair13_clean_topic(
            repair13_clean_state
        )
    )
    assert repair13_main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }

    repair14_subject = active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_SUBJECT
    repair14_trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_REVIEWED_TREE_TRAILER
    )
    repair14_message = f"{repair14_subject}\n\n{repair14_trailer_key}: {tree}"
    repair14_clean_state = replace(
        clean_topic_state,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH}"
        ),
    )
    repair14_git_values = {
        ("rev-parse", "--verify", "HEAD^{commit}"): child,
        ("rev-list", "--parents", "-n", "1", child): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_BASE}"
        ),
        ("show", "-s", "--format=%s", child): repair14_subject,
        ("show", "-s", "--format=%T", child): tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
    }

    def exact_repair14_git_output(arguments: list[str]) -> str:
        return repair14_git_values[tuple(arguments)]

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        exact_repair14_git_output,
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair14_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair14_clean_state,
    )
    assert active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
        repair14_clean_state
    )
    assert (
        active_gate2_manifest.phase54_slice12_product_repair14_clean_topic_is_active()
    )
    assert not active_gate2_manifest.phase54_slice12_mechanical_repair3_is_active()
    assert not active_gate2_manifest.phase54_slice12_mechanical_repair3_clean_topic_is_active()
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    repair14_dirty_state = replace(
        repair14_clean_state,
        branch_oid=active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,
        modified_paths=(
            active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS
        ),
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        repair14_dirty_state
    )
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            repair14_dirty_state,
            modified_paths=repair14_dirty_state.modified_paths | {"unauthorized-path"},
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair14_dirty_state,
    )
    assert active_gate2_manifest.phase54_slice12_product_repair14_is_active()

    repair14_parent_key = ("rev-list", "--parents", "-n", "1", child)
    repair14_git_values[repair14_parent_key] = f"{child} {'5' * 40}"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    repair14_git_values[repair14_parent_key] = (
        f"{child} {active_gate2_manifest.PHASE54_SLICE12_PRODUCT_REPAIR14_BASE}"
    )
    repair14_subject_key = ("show", "-s", "--format=%s", child)
    repair14_git_values[repair14_subject_key] = "Wrong Repair14 subject"
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    repair14_git_values[repair14_subject_key] = repair14_subject
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: (
            f"{repair14_subject}\n\n{repair14_trailer_key}: {other_tree}"
            if revision == child
            else ""
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: repair14_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            repair14_clean_state,
            staged_paths=frozenset({"post-read-state-drift"}),
        ),
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: repair14_clean_state,
    )
    repair14_head_reads = iter((child, other_child))

    def moving_repair14_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(repair14_head_reads)
        return exact_repair14_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair14_head_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    repair14_main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_repair14_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in repair14_main_ref_reads
        ):
            read = repair14_main_ref_reads[reference]
            repair14_main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_repair14_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_repair14_main_refs_git_output,
    )
    assert (
        not active_gate2_manifest._matches_phase54_slice12_product_repair14_clean_topic(
            repair14_clean_state
        )
    )
    assert repair14_main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }

    mechanical_subject = (
        active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_SUBJECT
    )
    mechanical_trailer_key = (
        active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_REVIEWED_TREE_TRAILER
    )
    mechanical_message = f"{mechanical_subject}\n\n{mechanical_trailer_key}: {tree}"
    mechanical_clean_state = replace(
        clean_topic_state,
        branch_head=active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH,
        branch_upstream=(
            f"origin/{active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH}"
        ),
    )
    mechanical_git_values = {
        ("rev-parse", "--verify", "HEAD^{commit}"): child,
        ("rev-list", "--parents", "-n", "1", child): (
            f"{child} {active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE}"
        ),
        ("show", "-s", "--format=%s", child): mechanical_subject,
        ("show", "-s", "--format=%T", child): tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
        ),
    }

    def exact_mechanical_git_output(arguments: list[str]) -> str:
        return mechanical_git_values[tuple(arguments)]

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        exact_mechanical_git_output,
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: mechanical_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: mechanical_clean_state,
    )
    assert (
        active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
            mechanical_clean_state
        )
    )
    assert (
        active_gate2_manifest.phase54_slice12_mechanical_repair3_clean_topic_is_active()
    )
    assert not active_gate2_manifest.phase54_slice12_mechanical_repair3_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair14_clean_topic_is_active()
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    mechanical_dirty_state = replace(
        mechanical_clean_state,
        branch_oid=active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,
        modified_paths=(
            active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS
        ),
    )
    assert active_gate2_manifest._matches_phase54_active_gate2_manifest(
        mechanical_dirty_state
    )
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            mechanical_dirty_state,
            modified_paths=mechanical_dirty_state.modified_paths
            | {"unauthorized-path"},
        )
    )
    assert not active_gate2_manifest._matches_phase54_active_gate2_manifest(
        replace(
            mechanical_dirty_state,
            other_paths=frozenset({"untracked-state-drift"}),
        )
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: mechanical_dirty_state,
    )
    assert active_gate2_manifest.phase54_slice12_mechanical_repair3_is_active()
    assert not active_gate2_manifest.phase54_slice12_mechanical_repair3_clean_topic_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair14_is_active()
    assert not active_gate2_manifest.phase54_slice12_product_repair14_clean_topic_is_active()
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()

    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: mechanical_clean_state,
    )
    mechanical_parent_key = ("rev-list", "--parents", "-n", "1", child)
    mechanical_git_values[mechanical_parent_key] = f"{child} {'5' * 40}"
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    mechanical_git_values[mechanical_parent_key] = (
        f"{child} {active_gate2_manifest.PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE}"
    )
    mechanical_subject_key = ("show", "-s", "--format=%s", child)
    mechanical_git_values[mechanical_subject_key] = "Wrong mechanical Repair3 subject"
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    mechanical_git_values[mechanical_subject_key] = mechanical_subject
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: (
            f"{mechanical_subject}\n\n{mechanical_trailer_key}: {other_tree}"
            if revision == child
            else ""
        ),
    )
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_commit_message",
        lambda revision: mechanical_message if revision == child else "",
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: replace(
            mechanical_clean_state,
            staged_paths=frozenset({"post-read-state-drift"}),
        ),
    )
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: mechanical_clean_state,
    )
    mechanical_head_reads = iter((child, other_child))

    def moving_mechanical_head_git_output(arguments: list[str]) -> str:
        if tuple(arguments) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return next(mechanical_head_reads)
        return exact_mechanical_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_mechanical_head_git_output,
    )
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    mechanical_main_ref_reads = {
        "refs/heads/main": 0,
        "refs/remotes/origin/main": 0,
    }

    def moving_mechanical_main_refs_git_output(arguments: list[str]) -> str:
        reference = arguments[-1]
        if tuple(arguments[:2]) == ("rev-parse", "--verify") and (
            reference in mechanical_main_ref_reads
        ):
            read = mechanical_main_ref_reads[reference]
            mechanical_main_ref_reads[reference] += 1
            return (
                active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE
                if read == 0
                else other_child
            )
        return exact_mechanical_git_output(arguments)

    monkeypatch.setattr(
        active_gate2_manifest,
        "_git_output",
        moving_mechanical_main_refs_git_output,
    )
    assert not active_gate2_manifest._matches_phase54_slice12_mechanical_repair3_clean_topic(
        mechanical_clean_state
    )
    assert mechanical_main_ref_reads == {
        "refs/heads/main": 2,
        "refs/remotes/origin/main": 2,
    }
    manifest_tree = ast.parse(
        (REPO_ROOT / "tests/_phase54_active_gate2_manifest.py").read_text(
            encoding="utf-8"
        )
    )
    historical_reader_assignment = next(
        node
        for node in manifest_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name)
            and target.id == "PHASE54_SLICE10_PRIOR_MECHANICAL_READER_PATHS"
            for target in node.targets
        )
    )
    assert isinstance(historical_reader_assignment.value, ast.Call)
    assert isinstance(historical_reader_assignment.value.func, ast.Name)
    assert historical_reader_assignment.value.func.id == "frozenset"
    assert len(historical_reader_assignment.value.args) == 1
    assert isinstance(historical_reader_assignment.value.args[0], ast.Set)
    assert not any(
        isinstance(node, ast.Name) and node.id == "MECHANICAL_READER_PATHS"
        for node in ast.walk(historical_reader_assignment.value)
    )


def test_private_preservation_carriers_fields_enums_and_privacy_are_exact() -> None:
    assert preservation.__all__ == ()
    assert tuple(preservation.ProjectModuleFactOccurrenceRole) == (
        preservation.ProjectModuleFactOccurrenceRole.RELATION_INPUT,
        preservation.ProjectModuleFactOccurrenceRole.LET_VALUE,
        preservation.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
        preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY,
        preservation.ProjectModuleFactOccurrenceRole.SATISFYING,
        preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER,
        preservation.ProjectModuleFactOccurrenceRole.WINDOW_PARTITION,
        preservation.ProjectModuleFactOccurrenceRole.WINDOW_ORDER,
        preservation.ProjectModuleFactOccurrenceRole.WINDOW_ARGUMENT,
        preservation.ProjectModuleFactOccurrenceRole.WINDOW_DEFAULT,
    )
    assert tuple(preservation.ProjectModuleCandidateBucketStatus) == (
        preservation.ProjectModuleCandidateBucketStatus.CONCRETE,
        preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
        preservation.ProjectModuleCandidateBucketStatus.DEFERRED,
        preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
        preservation.ProjectModuleCandidateBucketStatus.ABSENT,
        preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS,
    )
    expected = {
        preservation.ProjectModuleWindowSignatureFact: (
            "identity",
            "signature",
            "result_formulas",
        ),
        preservation.ProjectModuleExpressionReferenceFact: (
            "owner",
            "role",
            "container_ordinal",
            "dependency_ordinal",
            "expression",
            "local_name",
            "input_field",
            "let_candidates",
            "selected_output_candidates",
            "status",
        ),
        preservation.ProjectModuleLetBindingFact: (
            "owner",
            "binding_ordinal",
            "binding",
            "scope_facts",
            "value_type",
            "references",
        ),
        preservation.ProjectModuleSelectFact: (
            "owner",
            "selected_output_ordinal",
            "item",
            "output_name",
            "expression_schema",
            "field",
            "aggregate_result_fact",
            "references",
        ),
        preservation.ProjectModuleWindowOutputFact: (
            "owner",
            "selected_output_ordinal",
            "item",
            "output_name",
            "signature_fact",
            "analysis",
            "project_fact",
            "retained_project_fact",
            "diagnostics",
            "status",
            "reason",
        ),
    }
    for carrier, names in expected.items():
        assert tuple(item.name for item in fields(carrier)) == names
        assert "__dict__" not in carrier.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )


def test_capability_family_inventory_counts_order_and_exact_raw_facts_are_preserved() -> (
    None
):
    capabilities = preservation._capability_inventory()
    second_inventory = preservation._capability_inventory()
    assert capabilities.window_signatures is second_inventory.window_signatures
    assert (
        capabilities.window_signatures is preservation._CANONICAL_WINDOW_SIGNATURE_FACTS
    )
    assert tuple(
        len(facts)
        for facts in (
            capabilities.inventory_facts,
            capabilities.signature_facts,
            capabilities.aggregate_facts,
            capabilities.window_facts,
            capabilities.context_facts,
        )
    ) == (41, 39, 69, 24, 18)
    assert len({fact.key for fact in capabilities.aggregate_facts}) == 68
    assert (
        sum(
            len(facts)
            for facts in (
                capabilities.inventory_facts,
                capabilities.signature_facts,
                capabilities.aggregate_facts,
                capabilities.window_facts,
                capabilities.context_facts,
            )
        )
        == 191
    )
    for field_name in (
        "inventory_facts",
        "signature_facts",
        "aggregate_facts",
        "window_facts",
        "context_facts",
    ):
        with pytest.raises(ValueError, match="exact canonical tuple"):
            replace(capabilities, **{field_name: ()})
    signatures = capabilities.window_signatures
    invalid_signature_snapshots = (
        (),
        signatures[:-1],
        (*signatures, signatures[0]),
        tuple(reversed(signatures)),
        tuple(replace(signature) for signature in signatures),
    )
    for invalid in invalid_signature_snapshots:
        with pytest.raises(ValueError, match="exact canonical tuple"):
            replace(capabilities, window_signatures=invalid)


def test_capability_lookup_preserves_found_absent_unknown_conflict_and_duplicate_folding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capabilities = preservation._capability_inventory()
    found_key = capabilities.inventory_facts[0].key
    found = capabilities.lookup(found_key)
    assert isinstance(found, Found)
    assert found.fact is capabilities.inventory_facts[0]
    provider = preservation.inventory_lookup_inputs

    def empty_provider_facts(
        key: CapabilityKey,
    ) -> tuple[tuple[CapabilityFact, ...], bool]:
        _facts, complete = provider(key)
        return (), complete

    monkeypatch.setattr(
        preservation,
        "inventory_lookup_inputs",
        empty_provider_facts,
    )
    retained = capabilities.lookup(found_key)
    assert isinstance(retained, Found)
    assert retained.fact is capabilities.inventory_facts[0]
    absent = capabilities.lookup(
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureScalar",
            operation="catalog_membership",
            context="builtin_registry",
        )
    )
    assert isinstance(absent, Absent)
    unknown = capabilities.lookup(
        CapabilityKey(CapabilityDomain.CONVERSION, subject="Int", operation="to")
    )
    assert isinstance(unknown, Unknown)
    conflicting_key = next(
        fact.key
        for fact in capabilities.aggregate_facts
        if fact.key.subject == "count"
        and "Shape" in fact.key.operands
        and sum(candidate.key == fact.key for candidate in capabilities.aggregate_facts)
        == 2
    )
    conflict = capabilities.lookup(conflicting_key)
    assert isinstance(conflict, Conflict)
    assert len(conflict.evidence) == 2


def test_window_signature_formula_inventory_preserves_all_eight_identities_exactly() -> (
    None
):
    signatures = preservation._capability_inventory().window_signatures
    assert tuple(fact.identity.name for fact in signatures) == (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    )
    assert tuple(len(fact.result_formulas) for fact in signatures) == (
        1,
        1,
        1,
        1,
        1,
        1,
        3,
        3,
    )
    assert all(
        formula.signature is fact.signature
        for fact in signatures
        for formula in fact.result_formulas
    )


def test_result_role_inventory_is_exact_separate_and_source_ordered() -> None:
    assert preservation._capability_inventory().result_roles == (
        ProjectRowResultRole.ORDINARY_ROW_VALUE,
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.WINDOW_RESULT,
    )


def test_schema_v1_has_no_sidecar_and_text_json_ir_sql_bytes_remain_exact(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query("    select:\n        id\n")},
        schema_version=1,
    )
    assert parse_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert semantic.module_semantic_facts is None
    payload = project_check_result_to_json_dict(parse_result)
    assert "module_semantic_facts" not in json.dumps(payload, sort_keys=True)


def test_schema_v2_builds_sidecar_from_exact_slice10_authority_without_slice11_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query("    select:\n        total = id + 1\n")},
    )
    facts = _fact_set(semantic)
    assert facts.authority.modules is parse_result.modules
    assert facts.authority.catalogs is semantic.module_catalogs
    assert facts.authority.relation_resolutions is semantic.module_relation_resolutions
    relations = tuple(
        relation
        for environment in facts.environments
        for relation in environment.relation_facts
    )
    assert len(facts.authority._relation_fact_projections) == len(relations)
    assert all(
        projected is relation
        for projected, relation in zip(
            facts.authority._relation_fact_projections,
            relations,
            strict=True,
        )
    )
    signature = inspect.signature(preservation._build_project_module_semantic_fact_set)
    assert tuple(signature.parameters) == (
        "modules",
        "catalogs",
        "relation_resolutions",
    )
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    assert "module_attribution" not in source

    unknown_root = tmp_path / "unknown-window-identity"
    _, unknown_semantic = _semantic_project(
        unknown_root,
        {
            "main.pietto": _query(
                "    select:\n"
                "        mystery = mystery_window() window:\n"
                "            order by:\n"
                "                id\n"
            )
        },
    )
    unknown = _relation(
        unknown_semantic,
        "main.pietto",
        "result",
    ).window_outputs[0]
    assert type(unknown.analysis) is WindowExpressionUnsupported
    assert unknown.analysis.reason == "unsupported window function identity"
    assert unknown.signature_fact is None
    assert unknown.project_fact is None
    assert unknown.retained_project_fact is None
    assert unknown.status is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    assert unknown.reason == unknown.analysis.reason
    assert tuple(diagnostic.code for diagnostic in unknown.diagnostics) == (
        "PIE-S2103",
    )
    assert cli.main(["check", "--project", str(unknown_root), "--format", "json"]) == 1
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload["ok"] is True
    assert cli_payload["diagnostics"] == []


def test_builder_rejects_value_equal_or_misaligned_foreign_authority_roots(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _prefix()},
    )
    catalogs = semantic.module_catalogs
    resolutions = semantic.module_relation_resolutions
    assert catalogs is not None and resolutions is not None
    foreign_modules = tuple(replace(module) for module in parse_result.modules)
    with pytest.raises(ValueError, match="exact catalog module roots"):
        preservation._build_project_module_semantic_fact_set(
            foreign_modules,
            catalogs,
            resolutions,
        )
    incomplete_resolutions = replace(
        resolutions,
        dependency_order=(),
        environments=(),
        issues=(),
        diagnostics=(),
    )
    with pytest.raises(ValueError, match="complete Slice 10 module coverage"):
        preservation._build_project_module_semantic_fact_set(
            parse_result.modules,
            catalogs,
            incomplete_resolutions,
        )
    facts = _fact_set(semantic)
    authoritative_environment = resolutions.environments[0]
    foreign_resolution_environment = replace(authoritative_environment)
    foreign_semantic_environment = replace(
        facts.environments[0],
        resolution_environment=foreign_resolution_environment,
    )
    with pytest.raises(ValueError, match="exact Slice 10 environments"):
        replace(facts, environments=(foreign_semantic_environment,))

    rich_query = (
        "    from rows\n"
        "    let:\n"
        "        key = id\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        id\n"
        "        total = sum(amount)\n"
        "        position = rank() window:\n"
        "            order by:\n"
        "                total desc\n"
        "    satisfying:\n"
        "        total > 0\n"
        "    order by:\n"
        "        position\n"
    )
    _, rich_semantic = _semantic_project(
        tmp_path / "owner-closure",
        {
            "main.pietto": (
                _prefix()
                + "query first:\n"
                + rich_query
                + "query second:\n"
                + rich_query
            )
        },
    )
    first = _relation(rich_semantic, "main.pietto", "first")
    second = _relation(rich_semantic, "main.pietto", "second")
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            rich_semantic,
            first,
            replace(first),
        )
    for attribute in (
        "let_bindings",
        "select_facts",
        "clause_dependencies",
        "window_outputs",
    ):
        with pytest.raises(ValueError, match="exact owner"):
            replace(first, **{attribute: getattr(second, attribute)})
    assert first.resolution is not None and second.resolution is not None
    with pytest.raises(ValueError, match="exact owner"):
        replace(first, resolution=second.resolution)
    for foreign_resolution in (None, replace(first.resolution)):
        foreign_relation = replace(first, resolution=foreign_resolution)
        with pytest.raises(ValueError, match="exact Slice 10 resolution"):
            _replace_relation_in_final_semantic(
                rich_semantic,
                first,
                foreign_relation,
            )
    assert (
        first.aggregate_grouped_clause_readiness is not None
        and second.aggregate_grouped_clause_readiness is not None
    )
    with pytest.raises(ValueError, match="exact definition"):
        replace(
            first,
            aggregate_grouped_clause_readiness=(
                second.aggregate_grouped_clause_readiness
            ),
        )

    first_let = first.let_bindings[0]
    assert first_let.value_type is not None
    missing_let_value_type = replace(first_let, value_type=None)
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            rich_semantic,
            first,
            replace(first, let_bindings=(missing_let_value_type,)),
        )
    foreign_let_reference = replace(
        first_let.references[0],
        owner=second.owner,
    )
    with pytest.raises(ValueError, match="exact source ledger"):
        replace(first_let, references=(foreign_let_reference,))
    first_select = first.select_facts[0]
    foreign_select_reference = replace(
        first_select.references[0],
        owner=second.owner,
    )
    with pytest.raises(ValueError, match="exact source ledger"):
        replace(first_select, references=(foreign_select_reference,))

    group_dependency = first.clause_dependencies[0]
    with pytest.raises(TypeError, match="exact role"):
        replace(
            group_dependency,
            role=cast(
                preservation.ProjectModuleFactOccurrenceRole,
                "group_key",
            ),
        )
    cloned_group_item = replace(cast(GroupByItem, group_dependency.source_occurrence))
    with pytest.raises(ValueError, match="exact source occurrence"):
        replace(
            group_dependency,
            target_occurrences=(cloned_group_item,),
        )
    with pytest.raises(ValueError, match="exact source ledger"):
        replace(first, clause_dependencies=first.clause_dependencies[:-1])
    with pytest.raises(ValueError, match="exact source ledger"):
        replace(first, group_key_occurrences=second.group_key_occurrences)

    assert first.aggregate_grouped_clause_readiness is not None
    cloned_readiness = replace(first.aggregate_grouped_clause_readiness)
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            rich_semantic,
            first,
            replace(
                first,
                aggregate_grouped_clause_readiness=cloned_readiness,
            ),
        )

    _, carrier_semantic = _semantic_project(
        tmp_path / "whole-relation-carrier-closure",
        {
            "main.pietto": _query(
                "    let:\n"
                "        id = amount\n"
                "        id = category\n"
                "    select:\n"
                "        bare = id\n"
            )
        },
    )
    carrier_relation = _relation(carrier_semantic, "main.pietto", "result")
    carrier_scope = carrier_relation.let_scope_facts
    assert carrier_scope is not None
    assert carrier_scope.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert len(carrier_scope.bindings) == 2
    assert (
        carrier_scope.binding_expressions["id"] is carrier_scope.bindings[0].expression
    )
    carrier_select = carrier_relation.select_facts[0]
    carrier_reference = carrier_select.references[0]
    assert carrier_reference.input_field is not None
    assert (
        carrier_reference.status
        is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
    )
    assert carrier_reference.let_candidates == carrier_scope.bindings

    for forged_reference in (
        replace(carrier_reference),
        replace(
            carrier_reference,
            input_field=None,
            let_candidates=(),
            selected_output_candidates=(),
            status=preservation.ProjectModuleCandidateBucketStatus.ABSENT,
        ),
    ):
        forged_select = replace(carrier_select, references=(forged_reference,))
        with pytest.raises(ValueError, match="exact existing relation projection"):
            _replace_relation_in_final_semantic(
                carrier_semantic,
                carrier_relation,
                replace(carrier_relation, select_facts=(forged_select,)),
            )

    assert carrier_select.expression_schema is not None
    assert carrier_select.field is not None
    missing_select_payload = replace(
        carrier_select,
        expression_schema=None,
        field=None,
    )
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            carrier_semantic,
            carrier_relation,
            replace(carrier_relation, select_facts=(missing_select_payload,)),
        )

    forged_scope = replace(
        carrier_scope,
        binding_expressions={"id": carrier_scope.bindings[1].expression},
    )
    forged_scope_bindings = tuple(
        replace(binding, scope_facts=forged_scope)
        for binding in carrier_relation.let_bindings
    )
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            carrier_semantic,
            carrier_relation,
            replace(
                carrier_relation,
                let_scope_facts=forged_scope,
                let_bindings=forged_scope_bindings,
            ),
        )

    assert first.let_scope_facts is not None
    concrete_value_type = next(iter(first.let_scope_facts.value_types.values()))
    forged_concrete_scope = replace(
        carrier_scope,
        status=ProjectLetScopeFactsStatus.CONCRETE,
        binding_expressions={"id": carrier_scope.bindings[1].expression},
        value_types={"id": concrete_value_type},
    )
    forged_concrete_bindings = tuple(
        replace(binding, scope_facts=forged_concrete_scope)
        for binding in carrier_relation.let_bindings
    )
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            carrier_semantic,
            carrier_relation,
            replace(
                carrier_relation,
                let_scope_facts=forged_concrete_scope,
                let_bindings=forged_concrete_bindings,
            ),
        )

    _, aggregate_semantic = _semantic_project(
        tmp_path / "whole-relation-aggregate-closure",
        {"main.pietto": _query("    select:\n        total = count()\n")},
    )
    aggregate_relation = _relation(aggregate_semantic, "main.pietto", "result")
    aggregate_select = aggregate_relation.select_facts[0]
    assert len(aggregate_relation.aggregate_result_facts) == 1
    assert (
        aggregate_select.aggregate_result_fact
        is (aggregate_relation.aggregate_result_facts[0])
    )
    dropped_aggregate_select = replace(
        aggregate_select,
        aggregate_result_fact=None,
    )
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            aggregate_semantic,
            aggregate_relation,
            replace(
                aggregate_relation,
                select_facts=(dropped_aggregate_select,),
                aggregate_result_facts=(),
            ),
        )

    first_window = first.window_outputs[0]
    second_window = second.window_outputs[0]
    first_analysis = cast(WindowExpressionAnalysis, first_window.analysis)
    second_analysis = cast(WindowExpressionAnalysis, second_window.analysis)
    assert first_window.project_fact is not None
    assert second_window.project_fact is not None
    assert first_window.retained_project_fact is first_window.project_fact
    assert second_window.retained_project_fact is second_window.project_fact
    with pytest.raises(ValueError, match="exact owner source occurrence"):
        replace(first_window, analysis=second_analysis)
    with pytest.raises(ValueError, match="exact owner source occurrence"):
        replace(first_window, analysis=replace(second_analysis))
    with pytest.raises(ValueError, match="exact analysis identity"):
        replace(
            first_window,
            project_fact=second_window.project_fact,
            retained_project_fact=second_window.project_fact,
        )
    with pytest.raises(ValueError, match="share its exact retained fact"):
        replace(
            first_window,
            retained_project_fact=replace(first_window.project_fact),
        )
    assert first_analysis.ranking_fact is not None
    with pytest.raises(ValueError, match="exact existing family payload"):
        replace(
            first_window,
            analysis=replace(
                first_analysis,
                ranking_fact=replace(
                    first_analysis.ranking_fact,
                    advance_policy=RankingAdvancePolicy.PER_ROW,
                ),
            ),
        )

    first_project_fact = first_window.project_fact
    foreign_definition = replace(cast(QueryDef, first.owner.definition))
    foreign_definition_identity = replace(
        first_project_fact.result_identity,
        definition=foreign_definition,
    )
    foreign_definition_fact = replace(
        first_project_fact,
        result_identity=foreign_definition_identity,
    )
    with pytest.raises(ValueError, match="exact analysis identity"):
        replace(
            first_window,
            project_fact=foreign_definition_fact,
            retained_project_fact=foreign_definition_fact,
        )
    cloned_occurrence = replace(first_analysis.semantic_fact.occurrence)
    cloned_occurrence_identity = replace(
        first_project_fact.result_identity,
        occurrence=cloned_occurrence,
    )
    cloned_occurrence_fact = replace(
        first_project_fact,
        result_identity=cloned_occurrence_identity,
    )
    with pytest.raises(ValueError, match="exact analysis identity"):
        replace(
            first_window,
            project_fact=cloned_occurrence_fact,
            retained_project_fact=cloned_occurrence_fact,
        )
    wrong_output_identity = replace(
        first_project_fact.result_identity,
        output_name="foreign",
    )
    wrong_output_fact = replace(
        first_project_fact,
        result_identity=wrong_output_identity,
    )
    with pytest.raises(ValueError, match="exact analysis identity"):
        replace(
            first_window,
            project_fact=wrong_output_fact,
            retained_project_fact=wrong_output_fact,
        )

    unsupported_query = (
        "    from rows\n"
        "    select:\n"
        "        bad = row_number(1) window:\n"
        "            order by:\n"
        "                id\n"
    )
    _, unsupported_semantic = _semantic_project(
        tmp_path / "unsupported-owner-closure",
        {
            "main.pietto": (
                _prefix()
                + "query first:\n"
                + unsupported_query
                + "query second:\n"
                + unsupported_query
            )
        },
    )
    unsupported_first = _relation(
        unsupported_semantic,
        "main.pietto",
        "first",
    ).window_outputs[0]
    unsupported_second = _relation(
        unsupported_semantic,
        "main.pietto",
        "second",
    ).window_outputs[0]
    assert isinstance(unsupported_first.analysis, WindowExpressionUnsupported)
    assert isinstance(unsupported_second.analysis, WindowExpressionUnsupported)
    with pytest.raises(ValueError, match="exact owner source occurrence"):
        replace(unsupported_first, analysis=unsupported_second.analysis)

    with pytest.raises(ValueError, match="exact static signature"):
        replace(first_window, signature_fact=None)
    assert first_window.signature_fact is not None
    rich_facts = _fact_set(rich_semantic)
    foreign_signature = next(
        signature
        for signature in rich_facts.capabilities.window_signatures
        if signature.identity != first_window.signature_fact.identity
    )
    with pytest.raises(ValueError, match="exact window identity"):
        replace(first_window, signature_fact=foreign_signature)
    with pytest.raises(TypeError, match="exact analysis carrier"):
        replace(first_window, analysis=None, project_fact=None)
    with pytest.raises(ValueError, match="exact project fact"):
        replace(first_window, project_fact=None)
    with pytest.raises(ValueError, match="exact analysis availability"):
        replace(
            first_window,
            status=preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
        )
    with pytest.raises(ValueError, match="exact analysis availability"):
        replace(first_window, reason="foreign")
    with pytest.raises(
        ValueError,
        match="cannot publish concrete project evidence",
    ):
        replace(
            unsupported_first,
            status=preservation.ProjectModuleCandidateBucketStatus.CONCRETE,
        )
    for status, reason in (
        (
            preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
            "foreign",
        ),
        (
            preservation.ProjectModuleCandidateBucketStatus.DEFERRED,
            unsupported_first.analysis.reason,
        ),
        (
            preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
            unsupported_first.analysis.reason,
        ),
    ):
        mutated_unsupported = replace(
            unsupported_first,
            status=status,
            reason=reason,
        )
        unsupported_relation = _relation(
            unsupported_semantic,
            "main.pietto",
            "first",
        )
        with pytest.raises(ValueError, match="exact analyzer availability"):
            _replace_window_in_final_semantic(
                unsupported_semantic,
                unsupported_relation,
                unsupported_first,
                mutated_unsupported,
            )
    for status in (
        preservation.ProjectModuleCandidateBucketStatus.ABSENT,
        preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS,
    ):
        with pytest.raises(ValueError, match="cannot be absent or ambiguous"):
            replace(unsupported_first, status=status)
    with pytest.raises(ValueError, match="retain analyzer diagnostics"):
        replace(unsupported_first, diagnostics=())
    with pytest.raises(ValueError, match="exact analyzer source evidence"):
        replace(
            unsupported_first,
            diagnostics=unsupported_second.diagnostics,
        )
    unsupported_relation = _relation(
        unsupported_semantic,
        "main.pietto",
        "first",
    )
    diagnostic = unsupported_first.diagnostics[0]
    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            rich_semantic,
            first,
            replace(first, helper_diagnostics=(diagnostic,)),
        )
    diagnostic_mutations = (
        (replace(diagnostic),),
        (replace(diagnostic, message="foreign"),),
        (diagnostic, diagnostic),
    )
    for diagnostics in diagnostic_mutations:
        mutated_diagnostics = replace(
            unsupported_first,
            diagnostics=diagnostics,
        )
        with pytest.raises(ValueError, match="exact analyzer payload and diagnostics"):
            _replace_window_in_final_semantic(
                unsupported_semantic,
                unsupported_relation,
                unsupported_first,
                mutated_diagnostics,
            )
    forged_analysis = replace(
        unsupported_first.analysis,
        reason="forged analyzer availability",
    )
    forged_output = replace(
        unsupported_first,
        analysis=forged_analysis,
        reason=forged_analysis.reason,
    )
    with pytest.raises(ValueError, match="exact analyzer payload and diagnostics"):
        _replace_window_in_final_semantic(
            unsupported_semantic,
            unsupported_relation,
            unsupported_first,
            forged_output,
        )
    external_analysis = replace(
        unsupported_first.analysis,
        reason="grouped context does not admit forged",
    )
    external_output = replace(
        unsupported_first,
        analysis=external_analysis,
        diagnostics=(),
        reason=external_analysis.reason,
    )
    with pytest.raises(ValueError, match="exact analyzer payload and diagnostics"):
        _replace_window_in_final_semantic(
            unsupported_semantic,
            unsupported_relation,
            unsupported_first,
            external_output,
        )

    unavailable_supported = replace(
        first_window,
        project_fact=None,
        status=preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
        reason="foreign",
    )
    with pytest.raises(ValueError, match="Concrete relation window outputs"):
        replace(first, window_outputs=(unavailable_supported,))

    with pytest.raises(ValueError, match="exact static signature"):
        replace(
            first_window,
            signature_fact=replace(first_window.signature_fact),
        )
    assert not hasattr(preservation, "_bind_existing_fact_projections")
    unbound_authority = replace(rich_facts.authority)
    with pytest.raises(ValueError, match="authority projections"):
        replace(rich_facts, authority=unbound_authority)

    foreign_window_body = (
        "    select:\n"
        "        position = rank() window:\n"
        "            order by:\n"
        "                id\n"
    )
    _, foreign_semantic = _semantic_project(
        tmp_path / "foreign-window-roots",
        {
            "main.pietto": (
                _prefix()
                + 'source other: Row is postgres.table("other")\n'
                + "query first:\n"
                + "    from rows\n"
                + foreign_window_body
                + "query second:\n"
                + "    from other\n"
                + foreign_window_body
            )
        },
    )
    foreign_first = _relation(foreign_semantic, "main.pietto", "first")
    foreign_second = _relation(foreign_semantic, "main.pietto", "second")
    foreign_first_window = foreign_first.window_outputs[0]
    foreign_second_window = foreign_second.window_outputs[0]
    assert foreign_first_window.project_fact is not None
    assert foreign_second_window.project_fact is not None
    foreign_provenance = replace(
        foreign_first_window.project_fact.provenance,
        symbol=foreign_second_window.project_fact.provenance.symbol,
    )
    provenance_project = replace(
        foreign_first_window.project_fact,
        provenance=foreign_provenance,
    )
    provenance_window = replace(
        foreign_first_window,
        project_fact=provenance_project,
        retained_project_fact=provenance_project,
    )
    with pytest.raises(ValueError, match="exact resolution authority"):
        _replace_window_in_final_semantic(
            foreign_semantic,
            foreign_first,
            foreign_first_window,
            provenance_window,
        )

    first_occurrences = foreign_first_window.project_fact.dependency_occurrences
    second_occurrences = foreign_second_window.project_fact.dependency_occurrences
    first_relation_input = next(
        occurrence
        for occurrence in first_occurrences
        if occurrence.role is WindowDependencyRole.RELATION_INPUT
    )
    second_relation_input = next(
        occurrence
        for occurrence in second_occurrences
        if occurrence.role is WindowDependencyRole.RELATION_INPUT
    )
    dependency_occurrences = tuple(
        replace(occurrence, target=second_relation_input.target)
        if occurrence is first_relation_input
        else occurrence
        for occurrence in first_occurrences
    )
    dependency_project = replace(
        foreign_first_window.project_fact,
        dependency_occurrences=dependency_occurrences,
        dependency_edges=deduplicate_window_dependency_edges(dependency_occurrences),
    )
    dependency_window = replace(
        foreign_first_window,
        project_fact=dependency_project,
        retained_project_fact=dependency_project,
    )
    with pytest.raises(ValueError, match="exact source and target authority"):
        _replace_window_in_final_semantic(
            foreign_semantic,
            foreign_first,
            foreign_first_window,
            dependency_window,
        )


def test_zero_relation_fact_environment_and_lookup_are_exact(tmp_path: Path) -> None:
    _, semantic = _semantic_project(tmp_path, {"types.pietto": "type Age = Int\n"})
    facts = _fact_set(semantic)
    environment = facts.find_module_path("types.pietto")
    assert len(environment) == 1
    assert environment[0].relation_facts == ()
    assert facts.find_module_path("missing.pietto") == ()


def test_source_relation_fact_retains_exact_slice10_owner_state_and_order(
    tmp_path: Path,
) -> None:
    source = (
        _prefix()
        + "query first:\n    from rows\n    select:\n        id\n"
        + "query second:\n    from first\n    select:\n        id\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    facts = _fact_set(semantic)
    source = _relation(semantic, "main.pietto", "rows")
    base = semantic.module_relation_resolutions
    assert base is not None
    base_source = base.environments[0].find_definition(
        cast(SourceDef, source.owner.definition)
    )[0]
    assert source.base_row_fact is base_source
    assert source.owner is base_source.owner
    assert source.state is base_source.state
    with pytest.raises(ValueError, match="exact Slice 10 row state"):
        replace(source, state=replace(source.state))
    semantic_environment = facts.environments[0]
    row_facts = base.environments[0].row_facts
    assert len(semantic_environment.relation_facts) == len(row_facts) == 3
    for fact, row_fact in zip(
        semantic_environment.relation_facts,
        row_facts,
        strict=True,
    ):
        assert fact.base_row_fact is row_fact
        assert fact.owner is row_fact.owner
    invalid_sequences = (
        (),
        semantic_environment.relation_facts[:-1],
        (
            semantic_environment.relation_facts[0],
            *semantic_environment.relation_facts,
        ),
        tuple(reversed(semantic_environment.relation_facts)),
    )
    for invalid in invalid_sequences:
        with pytest.raises(ValueError, match="exact ordered Slice 10 row facts"):
            replace(semantic_environment, relation_facts=invalid)
    foreign_base = replace(row_facts[0])
    foreign_fact = replace(
        semantic_environment.relation_facts[0],
        base_row_fact=foreign_base,
    )
    with pytest.raises(ValueError, match="exact ordered Slice 10 row facts"):
        replace(
            semantic_environment,
            relation_facts=(
                foreign_fact,
                *semantic_environment.relation_facts[1:],
            ),
        )


def test_local_computed_output_preserves_expression_type_nullability_origin_and_role(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query("    select:\n        total = id + 1\n")},
    )
    relation = _relation(semantic, "main.pietto", "result")
    selected = relation.select_facts[0]
    assert (
        relation.base_row_fact.state.status is ProjectRelationRowSchemaStatus.DEFERRED
    )
    assert relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert selected.expression_schema is not None
    assert selected.field is not None
    assert selected.expression_schema.resolved_type == selected.field.resolved_type
    assert selected.field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert selected.field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    assert selected.field.provenance is not None
    assert selected.field.provenance.kind.value == "derived_expression"

    nested_source = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        adjusted = gross + 1\n"
    )
    _, nested_semantic = _semantic_project(
        tmp_path / "nested-let",
        {"main.pietto": nested_source},
    )
    nested_relation = _relation(nested_semantic, "main.pietto", "result")
    nested_selected = nested_relation.select_facts[0]
    nested_schema = nested_relation.state.schema
    nested_let_scope = nested_relation.let_scope_facts

    assert nested_let_scope is not None
    assert nested_let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
    assert nested_let_scope.value_types["gross"].resolved_type.name == "Int"
    assert nested_relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert nested_schema is not None
    assert nested_selected.expression_schema is not None
    assert nested_selected.expression_schema.status.value == "concrete"
    assert nested_selected.expression_schema.reason.value == "known_expression_value"
    assert nested_selected.expression_schema.origin.value == "derived_expression"
    assert nested_selected.expression_schema.resolved_type is not None
    assert nested_selected.expression_schema.resolved_type.name == "Int"
    assert (
        nested_selected.expression_schema.nullability
        is ProjectRowFieldNullability.UNKNOWN
    )
    nested_field = nested_selected.field
    assert nested_field is not None
    assert nested_field is nested_schema.fields["adjusted"]
    assert nested_field.resolved_type.name == "Int"
    assert nested_field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert nested_field.provenance is not None
    assert nested_field.provenance.kind.value == "derived_expression"
    assert len(nested_selected.references) == 1
    nested_reference = nested_selected.references[0]
    assert nested_reference.local_name == "gross"
    assert nested_reference.input_field is None
    assert nested_reference.let_candidates == (nested_relation.let_bindings[0].binding,)
    assert (
        nested_reference.status
        is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
    )

    with pytest.raises(ValueError, match="exact existing relation projection"):
        _replace_relation_in_final_semantic(
            nested_semantic,
            nested_relation,
            replace(
                nested_relation,
                select_facts=(
                    replace(
                        nested_selected,
                        expression_schema=replace(nested_selected.expression_schema),
                    ),
                ),
            ),
        )

    invalid_let_prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    let:\n"
        "        gross = missing + 1\n"
        "    select:\n"
    )
    unavailable_expressions = (
        "gross",
        "gross < 0",
        "gross <= 0",
        "gross > 0",
        "gross >= 0",
        "gross == 0",
        "gross != 0",
        "gross is null",
        "gross is not null",
        "gross between 0 and 1",
        "-gross",
        "gross + 1",
        "lower(gross)",
        "(gross > 0) is null",
    )
    for position, expression in enumerate(unavailable_expressions):
        _, unavailable_semantic = _semantic_project(
            tmp_path / f"unknown-let-{position}",
            {
                "main.pietto": (
                    invalid_let_prefix + f"        adjusted = {expression}\n"
                )
            },
        )
        unavailable_relation = _relation(
            unavailable_semantic,
            "main.pietto",
            "result",
        )
        unavailable_selected = unavailable_relation.select_facts[0]
        unavailable_let_scope = unavailable_relation.let_scope_facts
        assert unavailable_let_scope is not None
        assert unavailable_let_scope.status is ProjectLetScopeFactsStatus.UNKNOWN
        assert unavailable_let_scope.reason.value == "let_diagnostics_suppressed"
        assert dict(unavailable_let_scope.value_types) == {}
        assert unavailable_let_scope.binding_expressions["gross"] is (
            unavailable_relation.let_bindings[0].binding.expression
        )
        assert unavailable_relation.state.status is not (
            ProjectRelationRowSchemaStatus.CONCRETE
        )
        unavailable_schema = unavailable_relation.state.schema
        assert unavailable_schema is None or (
            unavailable_schema.is_unknown and not unavailable_schema.fields
        )
        assert [
            diagnostic.code for diagnostic in unavailable_relation.helper_diagnostics
        ] == (["PIE-S2102"] if expression == "gross" else [])
        assert unavailable_selected.expression_schema is not None
        assert unavailable_selected.expression_schema.status.value == "unknown"
        assert unavailable_selected.expression_schema.reason.value in {
            "missing_input_field",
            "missing_value_type",
        }
        assert unavailable_selected.expression_schema.resolved_type is None
        assert unavailable_selected.expression_schema.nullability is None
        assert unavailable_selected.field is None
        assert unavailable_selected.aggregate_result_fact is None
        gross_references = tuple(
            reference
            for reference in unavailable_selected.references
            if reference.local_name == "gross"
        )
        assert gross_references
        assert all(
            reference.input_field is None
            and reference.let_candidates
            == (unavailable_relation.let_bindings[0].binding,)
            and reference.status
            is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
            for reference in gross_references
        )

    downstream_source = (
        invalid_let_prefix
        + "        adjusted = gross > 0\n"
        + "query downstream:\n"
        + "    from result\n"
        + "    select:\n"
        + "        adjusted\n"
    )
    _, downstream_semantic = _semantic_project(
        tmp_path / "unknown-let-downstream",
        {"main.pietto": downstream_source},
    )
    downstream_relation = _relation(
        downstream_semantic,
        "main.pietto",
        "downstream",
    )
    assert downstream_relation.state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert downstream_relation.state.reason is (
        ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
    )
    assert downstream_relation.state.schema is None
    assert downstream_relation.select_facts[0].field is None

    for position, expressions in enumerate(
        (
            ("missing > 0", "missing"),
            ("missing", "missing > 0"),
            ("missing is null", "missing is null"),
        )
    ):
        selection = "".join(
            f"        output{ordinal} = {expression}\n"
            for ordinal, expression in enumerate(expressions)
        )
        _, permutation_semantic = _semantic_project(
            tmp_path / f"root-isolation-{position}",
            {"main.pietto": _query("    select:\n" + selection)},
        )
        permutation_relation = _relation(
            permutation_semantic,
            "main.pietto",
            "result",
        )
        assert tuple(
            selected.output_name for selected in permutation_relation.select_facts
        ) == ("output0", "output1")
        assert all(
            selected.expression_schema is not None
            and selected.expression_schema.status.value == "unknown"
            and selected.expression_schema.resolved_type is None
            and selected.field is None
            for selected in permutation_relation.select_facts
        )

    shadowing_source = _query(
        "    let:\n"
        "        id = missing + 1\n"
        "    select:\n"
        "        direct = id\n"
        "        compared = id > 0\n"
        "        qualified = rows.id\n"
    )
    _, shadowing_semantic = _semantic_project(
        tmp_path / "invalid-shadowing-let",
        {"main.pietto": shadowing_source},
    )
    shadowing_relation = _relation(
        shadowing_semantic,
        "main.pietto",
        "result",
    )
    assert shadowing_relation.let_scope_facts is not None
    assert (
        shadowing_relation.let_scope_facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    )
    assert shadowing_relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert shadowing_relation.state.schema is not None
    assert tuple(shadowing_relation.state.schema.fields) == (
        "direct",
        "compared",
        "qualified",
    )
    assert all(
        selected.expression_schema is not None
        and selected.expression_schema.status.value == "concrete"
        and selected.field is not None
        for selected in shadowing_relation.select_facts
    )
    direct_reference = shadowing_relation.select_facts[0].references[0]
    assert direct_reference.input_field is not None
    assert direct_reference.status is (
        preservation.ProjectModuleCandidateBucketStatus.CONCRETE
    )
    assert direct_reference.let_candidates == (
        shadowing_relation.let_bindings[0].binding,
    )

    aggregate_source = invalid_let_prefix + "        total = sum(gross)\n"
    _, aggregate_semantic = _semantic_project(
        tmp_path / "unknown-let-aggregate",
        {"main.pietto": aggregate_source},
    )
    aggregate_relation = _relation(aggregate_semantic, "main.pietto", "result")
    assert (
        aggregate_relation.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert aggregate_relation.aggregate_result_facts == ()
    assert aggregate_relation.select_facts[0].aggregate_result_fact is None
    assert aggregate_relation.select_facts[0].field is None


def test_imported_computed_output_preserves_local_lookup_and_nominal_target(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table projected as Input\n'
                "query result:\n    from Input\n    select:\n        total = id + 1\n"
            ),
            "b.pietto": _library_source(),
        },
    )
    relation = _relation(semantic, "a.pietto", "result")
    assert relation.resolution is not None
    assert relation.resolution.target_symbol.local_name == "Input"
    assert relation.resolution.target_symbol.target_identity.module_path == "b.pietto"
    assert relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE


def test_aliased_import_keeps_qualifier_separate_from_nominal_target_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table projected as Local\n'
                "query result:\n    from Local\n    select:\n        total = Local.id + 1\n"
            ),
            "b.pietto": _library_source(),
        },
    )
    relation = _relation(semantic, "a.pietto", "result")
    reference = relation.select_facts[0].references[0]
    assert relation.resolution is not None
    assert relation.resolution.target_symbol.local_name == "Local"
    assert (
        relation.resolution.target_symbol.target_identity.declared_name == "projected"
    )
    assert reference.local_name == "id"
    assert reference.input_field is not None


def test_explicit_reexport_keeps_direct_facade_lookup_and_original_nominal_target(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table Public as Local\n'
                "query result:\n    from Local\n    select:\n        total = Local.id + 1\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    table projected as Public\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": _library_source(),
        },
    )
    relation = _relation(semantic, "a.pietto", "result")
    assert relation.resolution is not None
    symbol = relation.resolution.target_symbol
    assert symbol.local_name == "Local"
    assert symbol.imported_binding is not None
    assert symbol.imported_binding.target_module_path == "b.pietto"
    assert symbol.target_identity.module_path == "c.pietto"


def test_same_spelling_cross_module_relations_and_fields_never_merge(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _library_source(),
            "b.pietto": _library_source(),
        },
    )
    first = _relation(semantic, "a.pietto", "projected")
    second = _relation(semantic, "b.pietto", "projected")
    assert first.owner.identity != second.owner.identity
    assert first.state.schema is not None and second.state.schema is not None
    assert first.state.schema.fields["id"] is not second.state.schema.fields["id"]


def test_same_target_through_two_local_aliases_retains_two_identity_distinct_facts(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    table projected as First\n    table projected as Second\n'
                "query one:\n    from First\n    select:\n        id\n"
                "query two:\n    from Second\n    select:\n        id\n"
            ),
            "z.pietto": _library_source(),
        },
    )
    first = _relation(semantic, "a.pietto", "one")
    second = _relation(semantic, "a.pietto", "two")
    assert first.resolution is not None and second.resolution is not None
    assert first.resolution.target_symbol.local_name == "First"
    assert second.resolution.target_symbol.local_name == "Second"
    assert (
        first.resolution.target_symbol.target_occurrence
        is second.resolution.target_symbol.target_occurrence
    )
    assert first != second


def test_relation_and_output_cardinalities_zero_one_two_three_have_no_truncation(
    tmp_path: Path,
) -> None:
    sources = {
        "zero.pietto": "type Age = Int\n",
        "one.pietto": _prefix(),
        "two.pietto": _query("    select:\n        id\n        amount\n"),
        "three.pietto": _query(
            "    select:\n        id\n        amount\n        category\n"
        ),
    }
    _, semantic = _semantic_project(tmp_path, sources)
    assert (
        len(_fact_set(semantic).find_module_path("zero.pietto")[0].relation_facts) == 0
    )
    assert (
        len(_fact_set(semantic).find_module_path("one.pietto")[0].relation_facts) == 1
    )
    assert len(_relation(semantic, "two.pietto", "result").select_facts) == 2
    assert len(_relation(semantic, "three.pietto", "result").select_facts) == 3


def test_module_definition_and_fact_permutations_change_only_explicit_tuple_order(
    tmp_path: Path,
) -> None:
    shape = "shape Row:\n    id: Int not null\n"
    records = (
        (
            "rows",
            'source rows: Row is postgres.table("rows")\n',
        ),
        (
            "first",
            "query first:\n    from rows\n    select:\n        id\n",
        ),
        (
            "second",
            "query second:\n    from rows\n    select:\n        id\n",
        ),
    )
    observed_orders: set[tuple[str, ...]] = set()
    for position, ordered_records in enumerate(permutations(records)):
        _, semantic = _semantic_project(
            tmp_path / str(position),
            {
                "main.pietto": shape
                + "".join(source for _name, source in ordered_records)
            },
        )
        catalogs = semantic.module_catalogs
        resolutions = semantic.module_relation_resolutions
        assert catalogs is not None and resolutions is not None
        catalog_owners = tuple(
            occurrence
            for occurrence in catalogs.catalogs[0].occurrences
            if occurrence.identity.declaration_kind.value
            in {"source", "table", "query"}
        )
        row_facts = resolutions.environments[0].row_facts
        semantic_facts = _fact_set(semantic).environments[0].relation_facts
        expected_order = tuple(name for name, _source in ordered_records)
        observed_orders.add(
            tuple(owner.identity.declared_name for owner in catalog_owners)
        )
        assert tuple(owner.identity.declared_name for owner in catalog_owners) == (
            expected_order
        )
        assert len(catalog_owners) == len(row_facts) == len(semantic_facts) == 3
        for owner, row_fact, semantic_fact in zip(
            catalog_owners,
            row_facts,
            semantic_facts,
            strict=True,
        ):
            assert row_fact.owner is owner
            assert semantic_fact.owner is owner
            assert semantic_fact.base_row_fact is row_fact
    assert len(observed_orders) == 6


def test_complete_tuple_lookups_retain_middle_tail_and_duplicate_occurrences(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": _query(
                "    select:\n        a = id\n        b = id\n        c = id\n"
            )
        },
    )
    facts = _fact_set(semantic)
    relation = _relation(semantic, "main.pietto", "result")
    assert facts.find_owner(relation.owner) == (relation,)
    assert facts.find_owner(replace(relation.owner)) == ()
    assert (
        facts.environments[0].find_definition(
            cast(QueryDef, replace(relation.owner.definition))
        )
        == ()
    )
    assert tuple(item.output_name for item in relation.select_facts) == ("a", "b", "c")
    assert [item.references[0].local_name for item in relation.select_facts] == [
        "id",
        "id",
        "id",
    ]


def test_unknown_upstream_state_and_reason_propagate_without_child_inference(
    tmp_path: Path,
) -> None:
    _assert_unavailable_candidate_matrix(
        tmp_path,
        source_head=(
            'source unknown is postgres.table("unknown")\n'
            "query result:\n"
            "    from unknown\n"
        ),
        relation_status=ProjectRelationRowSchemaStatus.UNKNOWN,
        relation_reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        bucket_status=preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
        relation_qualifier="unknown",
    )


def test_deferred_upstream_state_and_reason_propagate_without_concretization(
    tmp_path: Path,
) -> None:
    _assert_unavailable_candidate_matrix(
        tmp_path,
        source_head=(
            _prefix() + "query pending:\n"
            "    from rows\n"
            "    select:\n"
            "        divided = amount / 2\n"
            "query result:\n"
            "    from pending\n"
        ),
        relation_status=ProjectRelationRowSchemaStatus.DEFERRED,
        relation_reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        bucket_status=preservation.ProjectModuleCandidateBucketStatus.DEFERRED,
        relation_qualifier="pending",
    )


def test_blocked_unresolved_reference_retains_issue_root_and_empty_candidates(
    tmp_path: Path,
) -> None:
    _assert_unavailable_candidate_matrix(
        tmp_path,
        source_head="query result:\n    from missing\n",
        relation_status=ProjectRelationRowSchemaStatus.BLOCKED,
        relation_reason=ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
        bucket_status=preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
        relation_qualifier="missing",
        expect_issues=True,
    )


def test_ambiguous_relation_bucket_retains_every_occurrence_without_winner(
    tmp_path: Path,
) -> None:
    source = (
        _prefix()
        + "query duplicated:\n    from rows\n    select:\n        id\n"
        + "query duplicated:\n    from rows\n    select:\n        amount\n"
        + "query result:\n    from duplicated\n    select:\n        id\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    duplicates = tuple(
        fact
        for fact in _fact_set(semantic).environments[0].relation_facts
        if fact.owner.identity.declared_name == "duplicated"
    )
    result = _relation(semantic, "main.pietto", "result")
    assert len(duplicates) == 2
    assert result.resolution is None
    assert result.state.status is not ProjectRelationRowSchemaStatus.CONCRETE


def test_local_and_module_cycles_retain_complete_roots_without_guessed_facts(
    tmp_path: Path,
) -> None:
    _, local_semantic = _semantic_project(
        tmp_path / "local",
        {
            "main.pietto": (
                "query a:\n"
                "    from b\n"
                "    let:\n"
                "        qualified = b.id\n"
                "        wrong = other.id\n"
                "    select:\n"
                "        id\n"
                "        qualified = b.id\n"
                "        wrong = other.id\n"
                "        position = rank() window:\n"
                "            order by:\n"
                "                id\n"
                "query b:\n"
                "    from a\n"
                "    let:\n"
                "        qualified = a.id\n"
                "        wrong = other.id\n"
                "    select:\n"
                "        id\n"
                "        qualified = a.id\n"
                "        wrong = other.id\n"
                "        position = rank() window:\n"
                "            order by:\n"
                "                id\n"
            )
        },
    )
    assert {
        _relation(local_semantic, "main.pietto", name).state.status
        for name in ("a", "b")
    } == {ProjectRelationRowSchemaStatus.BLOCKED}
    for name in ("a", "b"):
        relation = _relation(local_semantic, "main.pietto", name)
        references = tuple(
            reference
            for binding in relation.let_bindings
            for reference in binding.references
        ) + tuple(
            reference
            for selected in relation.select_facts
            for reference in selected.references
        )
        assert len(references) == 5
        assert {reference.status for reference in references} == {
            preservation.ProjectModuleCandidateBucketStatus.BLOCKED
        }
        assert all(
            reference.input_field is None
            and reference.let_candidates == ()
            and reference.selected_output_candidates == ()
            for reference in references
        )
        assert len(relation.window_outputs) == 1
        window = relation.window_outputs[0]
        assert isinstance(
            window.analysis,
            (WindowExpressionAnalysis, WindowExpressionUnsupported),
        )
        assert window.project_fact is None
        assert window.status is preservation.ProjectModuleCandidateBucketStatus.BLOCKED
        assert window.reason == ProjectRelationRowSchemaReason.CYCLE_BLOCKED.value
    _, module_semantic = _semantic_project(
        tmp_path / "module",
        {
            "a.pietto": 'import "b.pietto":\n    query b as B\n',
            "b.pietto": 'import "a.pietto":\n    query a as A\n',
        },
    )
    facts = _fact_set(module_semantic)
    assert facts.environments == ()
    assert facts.issues


def test_let_binding_ledger_preserves_source_order_duplicates_visibility_and_status(
    tmp_path: Path,
) -> None:
    source = _query(
        "    let:\n"
        "        first = id + 1\n"
        "        repeated = first + 1\n"
        "        repeated = amount + 1\n"
        "    group by:\n"
        "        id\n"
        "    select:\n"
        "        id\n"
        "        projected = repeated\n"
        "        total = sum(id)\n"
        "    satisfying:\n"
        "        sum(repeated) > 0\n"
        "    order by:\n"
        "        repeated\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    assert tuple(item.binding.name for item in relation.let_bindings) == (
        "first",
        "repeated",
        "repeated",
    )
    assert relation.let_bindings[1].references[0].let_candidates == (
        relation.let_bindings[0].binding,
    )
    assert relation.let_scope_facts is not None
    assert relation.let_scope_facts.status is not ProjectLetScopeFactsStatus.CONCRETE
    projected = next(
        fact for fact in relation.select_facts if fact.output_name == "projected"
    )
    assert len(projected.references) == 1
    assert projected.references[0].let_candidates == tuple(
        fact.binding for fact in relation.let_bindings[1:]
    )
    assert (
        projected.references[0].status
        is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    for role in (
        preservation.ProjectModuleFactOccurrenceRole.SATISFYING,
        preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER,
    ):
        dependency = next(
            fact for fact in relation.clause_dependencies if fact.role is role
        )
        assert (
            dependency.status is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
        )
        assert dependency.target_occurrences == ()
        assert dependency.target_fields == ()
        assert dependency.aggregate_result_facts == ()

    _, qualified_semantic = _semantic_project(
        tmp_path / "qualified",
        {
            "main.pietto": _query(
                "    let:\n"
                "        id = amount\n"
                "        missing = amount\n"
                "        qualified = rows.id\n"
                "    select:\n"
                "        existing = rows.id\n"
                "        absent = rows.missing\n"
                "        bare = id\n"
            )
        },
    )
    qualified_relation = _relation(qualified_semantic, "main.pietto", "result")
    qualified_let = qualified_relation.let_bindings[2].references[0]
    existing = qualified_relation.select_facts[0].references[0]
    absent = qualified_relation.select_facts[1].references[0]
    bare = qualified_relation.select_facts[2].references[0]
    for reference in (qualified_let, existing):
        assert type(reference.expression) is DottedNameExpr
        assert reference.input_field is not None
        assert reference.input_field.name == "id"
        assert reference.let_candidates == ()
        assert reference.selected_output_candidates == ()
        assert (
            reference.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        )
    assert type(absent.expression) is DottedNameExpr
    assert absent.input_field is None
    assert absent.let_candidates == ()
    assert absent.selected_output_candidates == ()
    assert absent.status is preservation.ProjectModuleCandidateBucketStatus.ABSENT
    assert bare.input_field is not None
    assert bare.let_candidates == (qualified_relation.let_bindings[0].binding,)
    with pytest.raises(ValueError, match="cannot carry local candidates"):
        replace(
            existing,
            let_candidates=(qualified_relation.let_bindings[0].binding,),
        )
    with pytest.raises(ValueError, match="cannot carry local candidates"):
        replace(
            existing,
            selected_output_candidates=(qualified_relation.select_facts[0].item,),
        )
    with pytest.raises(ValueError, match="require an input field"):
        replace(
            absent,
            status=preservation.ProjectModuleCandidateBucketStatus.CONCRETE,
        )


def test_let_derived_output_preserves_type_nullability_origin_dependency_and_role(
    tmp_path: Path,
) -> None:
    source = _query("    let:\n        total = id + 1\n    select:\n        total\n")
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    selected = relation.select_facts[0]
    assert selected.field is not None
    assert selected.field.provenance is not None
    assert selected.field.provenance.kind.value == "let_derived"
    assert selected.field.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
    assert selected.references[0].let_candidates == (relation.let_bindings[0].binding,)


def test_select_output_collision_preserves_every_candidate_and_never_overwrites(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "ordinary",
        {
            "main.pietto": _query(
                "    select:\n        value = id\n        value = amount\n"
            )
        },
    )
    relation = _relation(semantic, "main.pietto", "result")
    assert relation.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert relation.state.reason is ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
    assert tuple(item.output_name for item in relation.select_facts) == (
        "value",
        "value",
    )
    _, aggregate_semantic = _semantic_project(
        tmp_path / "aggregate",
        {
            "main.pietto": _query(
                "    group by:\n"
                "        category\n"
                "    select:\n"
                "        category\n"
                "        total = sum(id)\n"
                "        total = sum(amount)\n"
                "    satisfying:\n"
                "        total > 0\n"
                "    order by:\n"
                "        total\n"
            )
        },
    )
    aggregate_relation = _relation(aggregate_semantic, "main.pietto", "result")
    assert aggregate_relation.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        aggregate_relation.state.reason
        is ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
    )
    duplicate_outputs = tuple(
        fact for fact in aggregate_relation.select_facts if fact.output_name == "total"
    )
    assert len(duplicate_outputs) == 2
    assert aggregate_relation.aggregate_result_facts == ()
    assert all(fact.aggregate_result_fact is None for fact in duplicate_outputs)
    group_dependency = next(
        dependency
        for dependency in aggregate_relation.clause_dependencies
        if dependency.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
    )
    assert aggregate_relation.group_key_occurrences == (
        group_dependency.source_occurrence,
    )
    assert group_dependency.target_occurrences == (group_dependency.source_occurrence,)
    assert tuple(field.name for field in group_dependency.target_fields) == (
        "category",
    )
    assert (
        group_dependency.status
        is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
    )
    for dependency in aggregate_relation.clause_dependencies:
        if dependency.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY:
            continue
        assert (
            dependency.status is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
        )
        assert dependency.target_occurrences == tuple(
            fact.item for fact in duplicate_outputs
        )
        assert dependency.target_fields == ()
        assert dependency.aggregate_result_facts == ()


def test_group_keys_preserve_source_order_visibility_fields_and_result_roles(
    tmp_path: Path,
) -> None:
    source = _query(
        "    group by:\n        category\n        id\n"
        "    select:\n        category\n        id\n        total = sum(amount)\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    assert tuple(
        cast(NameExpr, item.key).name for item in relation.group_key_occurrences
    ) == (
        "category",
        "id",
    )
    assert relation.state.schema is not None
    assert tuple(
        field.result_role for field in relation.state.schema.fields.values()
    ) == (
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
    )

    _, let_semantic = _semantic_project(
        tmp_path / "let-backed",
        {
            "main.pietto": _query(
                "    let:\n"
                "        category_key = rows.category\n"
                "        bucket = category_key\n"
                "        id_key = id\n"
                "    group by:\n"
                "        bucket\n"
                "        id_key\n"
                "    select:\n"
                "        category\n"
                "        id\n"
                "        total = count()\n"
            )
        },
    )
    let_relation = _relation(let_semantic, "main.pietto", "result")
    let_group_dependencies = tuple(
        fact
        for fact in let_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
    )
    assert tuple(fact.source_ordinal for fact in let_group_dependencies) == (0, 1)
    assert (
        tuple(fact.source_occurrence for fact in let_group_dependencies)
        == let_relation.group_key_occurrences
    )
    assert tuple(
        tuple(field.name for field in fact.target_fields)
        for fact in let_group_dependencies
    ) == (("category",), ("id",))
    assert all(
        fact.target_occurrences == (fact.source_occurrence,)
        and fact.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        for fact in let_group_dependencies
    )

    for case, body in {
        "nonconcrete-let": (
            "    let:\n"
            "        key = category\n"
            "        key = id\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        category\n"
            "        total = count()\n"
        ),
        "nonconcrete-shadowing-input": (
            "    let:\n"
            "        category = id\n"
            "        category = amount\n"
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = count()\n"
        ),
        "wrong-qualifier": (
            "    group by:\n"
            "        other.category\n"
            "    select:\n"
            "        category\n"
            "        total = count()\n"
        ),
        "non-direct-let": (
            "    let:\n"
            "        key = id + 1\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        id\n"
            "        total = count()\n"
        ),
    }.items():
        _, unavailable_semantic = _semantic_project(
            tmp_path / case,
            {"main.pietto": _query(body)},
        )
        unavailable_relation = _relation(unavailable_semantic, "main.pietto", "result")
        unavailable = next(
            fact
            for fact in unavailable_relation.clause_dependencies
            if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
        )
        assert unavailable.target_occurrences == ()
        assert unavailable.target_fields == ()
        assert (
            unavailable.status
            is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
        )

    for case, body in {
        "unsupported-aggregate": (
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(category)\n"
        ),
        "duplicate-aggregate-alias-reversed": (
            "    group by:\n"
            "        category\n"
            "    select:\n"
            "        category\n"
            "        total = sum(amount)\n"
            "        total = sum(id)\n"
        ),
    }.items():
        _, independent_failure_semantic = _semantic_project(
            tmp_path / case,
            {"main.pietto": _query(body)},
        )
        independent_failure = _relation(
            independent_failure_semantic,
            "main.pietto",
            "result",
        )
        group_dependency = next(
            fact
            for fact in independent_failure.clause_dependencies
            if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
        )
        assert group_dependency.target_occurrences == (
            group_dependency.source_occurrence,
        )
        assert tuple(field.name for field in group_dependency.target_fields) == (
            "category",
        )
        assert (
            group_dependency.status
            is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        )

    _, duplicate_group_semantic = _semantic_project(
        tmp_path / "duplicate-group",
        {
            "main.pietto": _query(
                "    group by:\n"
                "        category\n"
                "        category\n"
                "    select:\n"
                "        category\n"
                "        total = count()\n"
            )
        },
    )
    duplicate_group = _relation(duplicate_group_semantic, "main.pietto", "result")
    duplicate_dependencies = tuple(
        fact
        for fact in duplicate_group.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
    )
    assert len(duplicate_dependencies) == 2
    assert tuple(fact.source_ordinal for fact in duplicate_dependencies) == (0, 1)
    assert (
        tuple(fact.source_occurrence for fact in duplicate_dependencies)
        == duplicate_group.group_key_occurrences
    )
    assert all(
        fact.target_occurrences == (fact.source_occurrence,)
        and tuple(field.name for field in fact.target_fields) == ("category",)
        and fact.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        for fact in duplicate_dependencies
    )
    assert duplicate_group.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        duplicate_group.state.reason
        is ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY
    )

    for case, keys in {
        "valid-before-wrong": ("category", "other.id"),
        "wrong-before-valid": ("other.id", "category"),
    }.items():
        _, mixed_semantic = _semantic_project(
            tmp_path / case,
            {
                "main.pietto": _query(
                    "    group by:\n"
                    + "".join(f"        {key}\n" for key in keys)
                    + "    select:\n"
                    "        category\n"
                    "        total = count()\n"
                )
            },
        )
        mixed = _relation(mixed_semantic, "main.pietto", "result")
        mixed_dependencies = tuple(
            fact
            for fact in mixed.clause_dependencies
            if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUP_KEY
        )
        assert tuple(fact.source_ordinal for fact in mixed_dependencies) == (0, 1)
        for key, dependency in zip(keys, mixed_dependencies, strict=True):
            if key == "category":
                assert dependency.target_occurrences == (dependency.source_occurrence,)
                assert tuple(field.name for field in dependency.target_fields) == (
                    "category",
                )
                assert (
                    dependency.status
                    is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
                )
            else:
                assert dependency.target_occurrences == ()
                assert dependency.target_fields == ()
                assert (
                    dependency.status
                    is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
                )


def test_aggregate_results_preserve_function_arguments_type_nullability_origin_and_role(
    tmp_path: Path,
) -> None:
    source = _query(
        "    group by:\n        id\n"
        "    select:\n        id\n        total = sum(amount)\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    assert len(relation.aggregate_result_facts) == 1
    fact = relation.aggregate_result_facts[0]
    selected = relation.select_facts[1]
    assert (fact.function, fact.argument_count, fact.grouped) == ("sum", 1, True)
    assert selected.aggregate_result_fact is fact
    assert selected.field is not None
    assert selected.field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
    assert selected.field.provenance is not None
    assert selected.field.provenance.kind.value == "aggregate"


def test_aggregate_dependency_occurrences_preserve_repetition_before_derived_dedup(
    tmp_path: Path,
) -> None:
    source = _query("    select:\n        total = sum(amount + amount)\n")
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    selected = _relation(semantic, "main.pietto", "result").select_facts[0]
    assert tuple(reference.local_name for reference in selected.references) == (
        "amount",
        "amount",
    )
    assert tuple(reference.dependency_ordinal for reference in selected.references) == (
        0,
        1,
    )


def test_satisfying_aggregate_candidate_bucket_preserves_all_matches_without_first_winner(
    tmp_path: Path,
) -> None:
    source = _query(
        "    let:\n        gross = amount\n"
        "    group by:\n        id\n"
        "    select:\n"
        "        id\n"
        "        first = sum(gross)\n"
        "        second = sum(gross)\n"
        "        position = rank() window:\n"
        "            order by:\n"
        "                id\n"
        "        sequence = row_number() window:\n"
        "            order by:\n"
        "                first\n"
        "        dense = dense_rank() window:\n"
        "            order by:\n"
        "                second\n"
        "    satisfying:\n        sum(gross) > 0\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    satisfying = tuple(
        fact
        for fact in relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.SATISFYING
    )
    assert len(satisfying) == 1
    assert tuple(
        cast(SelectItem, item).alias for item in satisfying[0].target_occurrences
    ) == (
        "first",
        "second",
    )
    assert (
        satisfying[0].status
        is preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS
    )
    assert relation.state.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert tuple(
        output.selected_output_ordinal for output in relation.window_outputs
    ) == (3, 4, 5)
    assert all(
        isinstance(output.analysis, WindowExpressionAnalysis)
        and output.project_fact is None
        and output.retained_project_fact is not None
        and output.retained_project_fact.semantic_fact
        is cast(WindowExpressionAnalysis, output.analysis).semantic_fact
        and output.status is preservation.ProjectModuleCandidateBucketStatus.BLOCKED
        and output.reason == relation.state.reason.value
        for output in relation.window_outputs
    )
    assert tuple(output.output_name for output in relation.window_outputs) == (
        "position",
        "sequence",
        "dense",
    )

    for count, window_source in (
        (0, ""),
        (
            1,
            "        position = rank() window:\n"
            "            order by:\n"
            "                id\n",
        ),
    ):
        matrix_source = _query(
            "    let:\n        gross = amount\n"
            "    group by:\n        id\n"
            "    select:\n"
            "        id\n"
            "        first = sum(gross)\n"
            "        second = sum(gross)\n"
            + window_source
            + "    satisfying:\n        sum(gross) > 0\n"
        )
        _, matrix_semantic = _semantic_project(
            tmp_path / f"window-count-{count}",
            {"main.pietto": matrix_source},
        )
        matrix_relation = _relation(matrix_semantic, "main.pietto", "result")
        matrix_satisfying = next(
            fact
            for fact in matrix_relation.clause_dependencies
            if fact.role is preservation.ProjectModuleFactOccurrenceRole.SATISFYING
        )
        assert tuple(
            cast(SelectItem, item).alias
            for item in matrix_satisfying.target_occurrences
        ) == ("first", "second")
        assert (
            matrix_satisfying.status
            is preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS
        )
        assert matrix_relation.state.status is ProjectRelationRowSchemaStatus.BLOCKED
        assert len(matrix_relation.window_outputs) == count
        assert all(
            output.project_fact is None
            and output.retained_project_fact is not None
            and output.status is preservation.ProjectModuleCandidateBucketStatus.BLOCKED
            and output.reason == matrix_relation.state.reason.value
            for output in matrix_relation.window_outputs
        )

    upstream = _relation(semantic, "main.pietto", "rows")
    assert relation.resolution is not None
    assert relation.let_scope_facts is not None
    assert relation.aggregate_grouped_clause_readiness is not None
    assert upstream.state.schema is not None
    _, raw_window_outputs = preservation._window_output_facts(
        owner=relation.owner,
        definition=cast(QueryDef, relation.owner.definition),
        input_schema=upstream.state.schema,
        upstream_symbol=preservation._project_symbol_for_resolution(
            relation.resolution
        ),
        let_scope=relation.let_scope_facts,
        base_state=relation.aggregate_grouped_clause_readiness.finalization.state,
        capabilities=_fact_set(semantic).capabilities,
    )
    assert all(output.project_fact is not None for output in raw_window_outputs)
    assert all(
        output.retained_project_fact is output.project_fact
        for output in raw_window_outputs
    )
    suppressed_window_outputs = (
        preservation._suppress_window_project_facts_after_clause_ambiguity(
            state=relation.state,
            clause_dependencies=relation.clause_dependencies,
            window_outputs=raw_window_outputs,
        )
    )
    for raw_output, suppressed_output in zip(
        raw_window_outputs,
        suppressed_window_outputs,
        strict=True,
    ):
        assert suppressed_output.item is raw_output.item
        assert suppressed_output.signature_fact is raw_output.signature_fact
        assert suppressed_output.analysis is raw_output.analysis
        assert suppressed_output.diagnostics is raw_output.diagnostics
        assert suppressed_output.project_fact is None
        assert suppressed_output.retained_project_fact is raw_output.project_fact
    retained_roles = tuple(
        tuple(
            (
                occurrence.role,
                occurrence.target.name,
                occurrence.target_result_role,
            )
            for occurrence in cast(
                preservation.WindowResultProjectFact,
                output.retained_project_fact,
            ).dependency_occurrences
        )
        for output in relation.window_outputs
    )
    assert retained_roles == (
        (
            (WindowDependencyRole.RELATION_INPUT, "rows", None),
            (WindowDependencyRole.WINDOW_ORDER, "id", ProjectRowResultRole.GROUP_KEY),
        ),
        (
            (WindowDependencyRole.RELATION_INPUT, "rows", None),
            (
                WindowDependencyRole.WINDOW_ORDER,
                "first",
                ProjectRowResultRole.AGGREGATE_RESULT,
            ),
        ),
        (
            (WindowDependencyRole.RELATION_INPUT, "rows", None),
            (
                WindowDependencyRole.WINDOW_ORDER,
                "second",
                ProjectRowResultRole.AGGREGATE_RESULT,
            ),
        ),
    )

    _, navigation_semantic = _semantic_project(
        tmp_path / "navigation-window",
        {
            "main.pietto": _query(
                "    let:\n        gross = amount\n"
                "    group by:\n        id\n"
                "    select:\n"
                "        id\n"
                "        first = sum(gross)\n"
                "        second = sum(gross)\n"
                "        previous = lag(first, 2, second) window:\n"
                "            partition by:\n"
                "                id\n"
                "                id\n"
                "            order by:\n"
                "                first\n"
                "                first\n"
                "    satisfying:\n        sum(gross) > 0\n"
            )
        },
    )
    navigation_relation = _relation(
        navigation_semantic,
        "main.pietto",
        "result",
    )
    navigation_output = navigation_relation.window_outputs[0]
    navigation_project = navigation_output.retained_project_fact
    assert navigation_output.project_fact is None
    assert navigation_project is not None
    assert tuple(
        (
            occurrence.global_ordinal,
            occurrence.role_ordinal,
            occurrence.role,
            occurrence.target.name,
            occurrence.target_result_role,
        )
        for occurrence in navigation_project.dependency_occurrences
    ) == (
        (
            0,
            0,
            WindowDependencyRole.WINDOW_ARGUMENT,
            "first",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
        (
            1,
            0,
            WindowDependencyRole.WINDOW_DEFAULT,
            "second",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
        (
            2,
            0,
            WindowDependencyRole.WINDOW_PARTITION,
            "id",
            ProjectRowResultRole.GROUP_KEY,
        ),
        (
            3,
            1,
            WindowDependencyRole.WINDOW_PARTITION,
            "id",
            ProjectRowResultRole.GROUP_KEY,
        ),
        (
            4,
            0,
            WindowDependencyRole.WINDOW_ORDER,
            "first",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
        (
            5,
            1,
            WindowDependencyRole.WINDOW_ORDER,
            "first",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
    )
    assert tuple(
        (edge.role, edge.target.name, edge.target_result_role)
        for edge in navigation_project.dependency_edges
    ) == (
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            "first",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
        (
            WindowDependencyRole.WINDOW_DEFAULT,
            "second",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            "id",
            ProjectRowResultRole.GROUP_KEY,
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            "first",
            ProjectRowResultRole.AGGREGATE_RESULT,
        ),
    )
    with pytest.raises(
        ValueError,
        match="Clause-ambiguous supported window output must retain",
    ):
        _replace_window_in_final_semantic(
            semantic,
            relation,
            relation.window_outputs[0],
            replace(
                relation.window_outputs[0],
                retained_project_fact=None,
            ),
        )
    with pytest.raises(
        ValueError,
        match="Clause-ambiguous semantic facts cannot publish window project evidence",
    ):
        replace(relation, window_outputs=raw_window_outputs)


def test_grouped_order_let_candidate_bucket_preserves_all_matching_outputs(
    tmp_path: Path,
) -> None:
    source = _query(
        "    let:\n        key = id\n"
        "    group by:\n        id\n"
        "    select:\n"
        "        first = id\n"
        "        second = id\n"
        "        total = sum(amount)\n"
        "        position = rank() window:\n"
        "            order by:\n"
        "                first\n"
        "        sequence = row_number() window:\n"
        "            order by:\n"
        "                second\n"
        "        dense = dense_rank() window:\n"
        "            order by:\n"
        "                first\n"
        "    order by:\n        key\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    order = tuple(
        fact
        for fact in relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )[0]
    assert tuple(cast(SelectItem, item).alias for item in order.target_occurrences) == (
        "first",
        "second",
    )
    assert order.status is preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert relation.state.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert tuple(
        output.selected_output_ordinal for output in relation.window_outputs
    ) == (3, 4, 5)
    assert all(
        isinstance(output.analysis, WindowExpressionAnalysis)
        and output.project_fact is None
        and output.retained_project_fact is not None
        and output.retained_project_fact.semantic_fact
        is cast(WindowExpressionAnalysis, output.analysis).semantic_fact
        and output.status is preservation.ProjectModuleCandidateBucketStatus.BLOCKED
        and output.reason == relation.state.reason.value
        for output in relation.window_outputs
    )
    for count, window_source in (
        (0, ""),
        (
            1,
            "        position = rank() window:\n"
            "            order by:\n"
            "                first\n",
        ),
    ):
        matrix_source = _query(
            "    let:\n        key = id\n"
            "    group by:\n        id\n"
            "    select:\n"
            "        first = id\n"
            "        second = id\n"
            "        total = sum(amount)\n"
            + window_source
            + "    order by:\n        key\n"
        )
        _, matrix_semantic = _semantic_project(
            tmp_path / f"window-count-{count}",
            {"main.pietto": matrix_source},
        )
        matrix_relation = _relation(matrix_semantic, "main.pietto", "result")
        matrix_order = next(
            fact
            for fact in matrix_relation.clause_dependencies
            if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
        )
        assert tuple(
            cast(SelectItem, item).alias for item in matrix_order.target_occurrences
        ) == ("first", "second")
        assert (
            matrix_order.status
            is preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS
        )
        assert matrix_relation.state.status is ProjectRelationRowSchemaStatus.BLOCKED
        assert len(matrix_relation.window_outputs) == count
        assert all(
            output.project_fact is None
            and output.retained_project_fact is not None
            and output.status is preservation.ProjectModuleCandidateBucketStatus.BLOCKED
            and output.reason == matrix_relation.state.reason.value
            for output in matrix_relation.window_outputs
        )
    forged_order = replace(
        order,
        status=preservation.ProjectModuleCandidateBucketStatus.CONCRETE,
    )
    forged_clause_dependencies = tuple(
        forged_order if fact is order else fact for fact in relation.clause_dependencies
    )
    assert relation.aggregate_grouped_clause_readiness is not None
    forged_state = preservation._reduce_window_outputs_to_state(
        definition=cast(QueryDef, relation.owner.definition),
        base_state=relation.aggregate_grouped_clause_readiness.finalization.state,
        outputs=relation.window_outputs,
    )
    forged_relation = replace(
        relation,
        clause_dependencies=forged_clause_dependencies,
        state=forged_state,
    )
    with pytest.raises(ValueError, match="exact existing-fact projection"):
        _replace_relation_in_final_semantic(
            semantic,
            relation,
            forged_relation,
        )

    _, chained_semantic = _semantic_project(
        tmp_path / "chained",
        {
            "main.pietto": _query(
                "    let:\n"
                "        key = category\n"
                "        bucket = key\n"
                "    group by:\n"
                "        category\n"
                "    select:\n"
                "        category\n"
                "        total = count()\n"
                "    order by:\n"
                "        bucket\n"
            )
        },
    )
    chained_relation = _relation(chained_semantic, "main.pietto", "result")
    chained_order = next(
        fact
        for fact in chained_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )
    assert chained_order.target_occurrences == (chained_relation.select_facts[0].item,)
    assert tuple(field.name for field in chained_order.target_fields) == ("category",)
    assert (
        chained_order.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
    )


def test_aggregate_grouped_concrete_unknown_deferred_and_blocked_states_are_atomic(
    tmp_path: Path,
) -> None:
    cases = {
        "concrete": _query("    select:\n        total = sum(amount)\n"),
        "unknown": _query("    select:\n        total = sum(missing)\n"),
        "deferred": _query("    select:\n        divided = amount / 2\n"),
        "blocked": _query(
            "    let:\n        gross = amount\n"
            "    group by:\n        id\n"
            "    select:\n        id\n        a = sum(gross)\n        b = sum(gross)\n"
            "    satisfying:\n        sum(gross) > 0\n"
        ),
    }
    statuses = {}
    for name, source in cases.items():
        _, semantic = _semantic_project(tmp_path / name, {"main.pietto": source})
        relation = _relation(semantic, "main.pietto", "result")
        statuses[name] = relation.state.status
        if relation.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            assert relation.aggregate_result_facts == ()
            assert all(
                fact.aggregate_result_fact is None for fact in relation.select_facts
            )
            assert relation.state.schema is None or relation.state.schema.fields == {}
    assert statuses == {
        "concrete": ProjectRelationRowSchemaStatus.CONCRETE,
        "unknown": ProjectRelationRowSchemaStatus.UNKNOWN,
        "deferred": ProjectRelationRowSchemaStatus.DEFERRED,
        "blocked": ProjectRelationRowSchemaStatus.BLOCKED,
    }


def test_all_eight_window_families_preserve_complete_composite_analysis(
    tmp_path: Path,
) -> None:
    identities = (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    )
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query(_window_lines(identities))},
    )
    relation = _relation(semantic, "main.pietto", "result")
    assert relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        tuple(
            cast(WindowExpressionAnalysis, output.analysis).semantic_fact.identity.name
            for output in relation.window_outputs
        )
        == identities
    )
    assert all(
        isinstance(output.analysis, WindowExpressionAnalysis)
        and output.project_fact is not None
        and output.retained_project_fact is output.project_fact
        for output in relation.window_outputs
    )
    canonical_by_identity = {
        fact.identity.name: fact
        for fact in preservation._CANONICAL_WINDOW_SIGNATURE_FACTS
    }
    assert all(
        output.signature_fact
        is canonical_by_identity[
            cast(WindowExpressionAnalysis, output.analysis).semantic_fact.identity.name
        ]
        for output in relation.window_outputs
    )
    ntile_output = relation.window_outputs[5]
    ntile_analysis = cast(WindowExpressionAnalysis, ntile_output.analysis)
    assert ntile_analysis.distribution_fact is not None
    with pytest.raises(ValueError, match="exact existing family payload"):
        replace(
            ntile_output,
            analysis=replace(
                ntile_analysis,
                distribution_fact=replace(
                    ntile_analysis.distribution_fact,
                    bucket_count=7,
                ),
            ),
        )
    foreign_state = replace(
        relation.state,
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
    )
    foreign_relation = replace(relation, state=foreign_state)
    with pytest.raises(ValueError, match="deterministic existing window reduction"):
        _replace_relation_in_final_semantic(
            semantic,
            relation,
            foreign_relation,
        )


def test_navigation_offset_default_generic_and_nullability_formula_evidence_is_exact(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query(_window_lines(("lag", "lead")))},
    )
    outputs = _relation(semantic, "main.pietto", "result").window_outputs
    assert all(output.signature_fact is not None for output in outputs)
    assert all(
        output.project_fact is not None
        and output.retained_project_fact is output.project_fact
        for output in outputs
    )
    assert tuple(
        len(
            cast(
                preservation.ProjectModuleWindowSignatureFact,
                output.signature_fact,
            ).result_formulas
        )
        for output in outputs
    ) == (
        3,
        3,
    )
    assert all(
        cast(WindowExpressionAnalysis, output.analysis).navigation_fact is not None
        for output in outputs
    )


def test_window_partition_order_and_direction_bindings_preserve_order_and_duplicates(
    tmp_path: Path,
) -> None:
    source = _query(
        "    select:\n"
        "        w = rank() window:\n"
        "            partition by:\n"
        "                category\n"
        "                category\n"
        "            order by:\n"
        "                id desc\n"
        "                id desc\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    analysis = cast(
        WindowExpressionAnalysis,
        _relation(semantic, "main.pietto", "result").window_outputs[0].analysis,
    )
    assert len(analysis.partition_binding_fact.bindings) == 2
    assert len(analysis.order_binding_fact.bindings) == 2
    assert tuple(
        item.source_direction for item in analysis.order_binding_fact.bindings
    ) == (
        "desc",
        "desc",
    )


def test_multiple_window_outputs_preserve_global_ordinals_and_every_output(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query(_window_lines(("row_number", "ntile", "lead")))},
    )
    outputs = _relation(semantic, "main.pietto", "result").window_outputs
    assert tuple(output.selected_output_ordinal for output in outputs) == (1, 2, 3)
    assert tuple(output.output_name for output in outputs) == ("w0", "w1", "w2")


def test_mixed_window_outcomes_scan_all_candidates_and_publish_no_partial_schema(
    tmp_path: Path,
) -> None:
    bodies = (
        (
            "    select:\n"
            "        good = row_number() window:\n            order by:\n                id\n"
            "        bad = ntile(0) window:\n            order by:\n                id\n"
        ),
        (
            "    select:\n"
            "        bad = ntile(0) window:\n            order by:\n                id\n"
            "        good = row_number() window:\n            order by:\n                id\n"
        ),
    )
    for position, body in enumerate(bodies):
        _, semantic = _semantic_project(
            tmp_path / str(position),
            {"main.pietto": _query(body)},
        )
        relation = _relation(semantic, "main.pietto", "result")
        assert len(relation.window_outputs) == 2
        assert {output.status for output in relation.window_outputs} == {
            preservation.ProjectModuleCandidateBucketStatus.CONCRETE,
            preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
        }
        assert relation.state.status is ProjectRelationRowSchemaStatus.BLOCKED
        assert relation.state.schema is None
        outputs_by_name = {
            output.output_name: output for output in relation.window_outputs
        }
        assert (
            outputs_by_name["good"].status
            is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        )
        assert outputs_by_name["good"].project_fact is not None
        assert (
            outputs_by_name["good"].retained_project_fact
            is outputs_by_name["good"].project_fact
        )
        assert (
            outputs_by_name["bad"].status
            is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
        )
        assert outputs_by_name["bad"].project_fact is None
        assert outputs_by_name["bad"].retained_project_fact is None
        assert all(
            fact.status is not preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS
            for fact in relation.clause_dependencies
        )

    _, local_nonconcrete_semantic = _semantic_project(
        tmp_path / "local-nonconcrete",
        {
            "main.pietto": _query(
                "    select:\n"
                "        missing\n"
                "        position = rank() window:\n"
                "            order by:\n"
                "                id\n"
            )
        },
    )
    local_nonconcrete = _relation(
        local_nonconcrete_semantic,
        "main.pietto",
        "result",
    )
    assert local_nonconcrete.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert len(local_nonconcrete.window_outputs) == 1
    local_window = local_nonconcrete.window_outputs[0]
    assert isinstance(local_window.analysis, WindowExpressionAnalysis)
    assert local_window.project_fact is None
    assert local_window.retained_project_fact is None
    assert (
        local_window.status is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    assert local_window.reason == local_nonconcrete.state.reason.value

    _, missing_order_semantic = _semantic_project(
        tmp_path / "missing-order",
        {
            "main.pietto": _query(
                "    select:\n"
                "        position = rank() window:\n"
                "            order by:\n"
                "                missing\n"
            )
        },
    )
    missing_order = _relation(missing_order_semantic, "main.pietto", "result")
    missing_window = missing_order.window_outputs[0]
    assert isinstance(missing_window.analysis, WindowExpressionUnsupported)
    assert missing_window.analysis.reason == "window order field type must be concrete"
    assert len(missing_window.diagnostics) == 1
    missing_diagnostic = missing_window.diagnostics[0]
    missing_expression = (
        cast(
            WindowExpr,
            missing_window.item.expression,
        )
        .spec.order_by[0]
        .expression
    )
    assert missing_diagnostic.code == "PIE-S2102"
    assert missing_diagnostic.message == "Unknown field: missing"
    assert (
        missing_diagnostic.location.path,
        missing_diagnostic.location.line,
        missing_diagnostic.location.column,
        missing_diagnostic.location.end_line,
        missing_diagnostic.location.end_column,
    ) == (
        missing_expression.span.path,
        missing_expression.span.line,
        missing_expression.span.column,
        missing_expression.span.end_line,
        missing_expression.span.end_column,
    )

    def unavailable_body(field_name: str) -> str:
        return (
            "    select:\n"
            "        first = rank() window:\n"
            "            order by:\n"
            f"                {field_name}\n"
            "        bad = row_number(1) window:\n"
            "            order by:\n"
            f"                {field_name}\n"
            "        last = dense_rank() window:\n"
            "            order by:\n"
            f"                {field_name}\n"
        )

    unavailable_cases = (
        (
            "unknown",
            'source unknown is postgres.table("unknown")\n'
            "query result:\n    from unknown\n" + unavailable_body("id"),
            ProjectRelationRowSchemaStatus.UNKNOWN,
            preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
        ),
        (
            "deferred",
            _prefix() + "query pending:\n"
            "    from rows\n"
            "    select:\n"
            "        divided = amount / 2\n"
            "query result:\n"
            "    from pending\n" + unavailable_body("divided"),
            ProjectRelationRowSchemaStatus.DEFERRED,
            preservation.ProjectModuleCandidateBucketStatus.DEFERRED,
        ),
        (
            "blocked",
            "query result:\n    from missing\n" + unavailable_body("id"),
            ProjectRelationRowSchemaStatus.BLOCKED,
            preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
        ),
    )
    for name, source, relation_status, output_status in unavailable_cases:
        _, semantic = _semantic_project(
            tmp_path / name,
            {"main.pietto": source},
        )
        relation = _relation(semantic, "main.pietto", "result")
        assert relation.state.status is relation_status
        assert len(relation.window_outputs) == 3
        assert all(
            output.status is output_status
            and output.analysis is not None
            and output.project_fact is None
            and output.retained_project_fact is None
            and output.reason == relation.state.reason.value
            for output in relation.window_outputs
        )
        invalid = relation.window_outputs[1]
        assert isinstance(invalid.analysis, WindowExpressionUnsupported)
        assert invalid.analysis.reason == "row_number requires 0 arguments"
        assert tuple(diagnostic.code for diagnostic in invalid.diagnostics) == (
            "PIE-S2104",
        )
        if relation_status is ProjectRelationRowSchemaStatus.UNKNOWN:
            assert relation.state.schema is not None
            assert relation.state.schema.is_unknown
        else:
            assert relation.state.schema is None
        baseline = relation.window_outputs[0]
        for status in (
            preservation.ProjectModuleCandidateBucketStatus.UNKNOWN,
            preservation.ProjectModuleCandidateBucketStatus.DEFERRED,
            preservation.ProjectModuleCandidateBucketStatus.BLOCKED,
        ):
            for reason in (baseline.reason, "foreign"):
                if status is baseline.status and reason == baseline.reason:
                    continue
                mutated = replace(baseline, status=status, reason=reason)
                with pytest.raises(ValueError, match="exact upstream availability"):
                    _replace_window_in_final_semantic(
                        semantic,
                        relation,
                        baseline,
                        mutated,
                    )
        for status in (
            preservation.ProjectModuleCandidateBucketStatus.ABSENT,
            preservation.ProjectModuleCandidateBucketStatus.AMBIGUOUS,
        ):
            with pytest.raises(ValueError, match="cannot be absent or ambiguous"):
                replace(baseline, status=status)


def test_window_dependency_occurrences_preserve_duplicates_and_edges_first_dedupe_only(
    tmp_path: Path,
) -> None:
    source = _query(
        "    select:\n"
        "        w = rank() window:\n"
        "            partition by:\n                category\n                category\n"
        "            order by:\n                id\n                id\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    project_fact = (
        _relation(semantic, "main.pietto", "result").window_outputs[0].project_fact
    )
    assert project_fact is not None
    assert len(project_fact.dependency_occurrences) == 5
    assert len(project_fact.dependency_edges) == 3

    grouped_relations: list[
        tuple[ProjectSemanticResult, preservation.ProjectModuleRelationSemanticFacts]
    ] = []
    for index, (first_name, second_name) in enumerate(
        (("first", "second"), ("second", "first"))
    ):
        _, grouped_semantic = _semantic_project(
            tmp_path / f"grouped-let-{index}",
            {
                "main.pietto": _query(
                    "    let:\n"
                    "        key = id\n"
                    "    group by:\n"
                    "        id\n"
                    "    select:\n"
                    f"        {first_name} = id\n"
                    f"        {second_name} = id\n"
                    "        total = count()\n"
                    "        position = rank() window:\n"
                    "            order by:\n"
                    "                key\n"
                )
            },
        )
        grouped_relation = _relation(grouped_semantic, "main.pietto", "result")
        grouped_relations.append((grouped_semantic, grouped_relation))
        grouped_window = grouped_relation.window_outputs[0]
        assert grouped_window.project_fact is not None
        grouped_order = next(
            occurrence
            for occurrence in grouped_window.project_fact.dependency_occurrences
            if occurrence.role is WindowDependencyRole.WINDOW_ORDER
        )
        assert grouped_order.target.output_name == first_name
        assert grouped_order.target_result_role is ProjectRowResultRole.GROUP_KEY

    _, collision_semantic = _semantic_project(
        tmp_path / "grouped-let-output-collision",
        {
            "main.pietto": _query(
                "    let:\n"
                "        key = id\n"
                "    group by:\n"
                "        id\n"
                "    select:\n"
                "        key = id\n"
                "        first = id\n"
                "        total = count()\n"
                "        key = rank() window:\n"
                "            order by:\n"
                "                key\n"
            )
        },
    )
    collision_relation = _relation(collision_semantic, "main.pietto", "result")
    collision_window = collision_relation.window_outputs[0]
    assert collision_window.project_fact is None
    assert (
        collision_window.status
        is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    assert collision_window.reason == "invalid_aggregate_or_grouped_output"

    provider_sources = {
        "qualified": _query(
            "    let:\n"
            "        key = rows.id\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        first = rows.id\n"
            "        total = count()\n"
            "        position = rank() window:\n"
            "            order by:\n"
            "                key\n"
        ),
    }
    for name, provider_source in provider_sources.items():
        _, provider_semantic = _semantic_project(
            tmp_path / f"grouped-provider-{name}",
            {"main.pietto": provider_source},
        )
        provider_window = _relation(
            provider_semantic,
            "main.pietto",
            "result",
        ).window_outputs[0]
        assert provider_window.project_fact is not None
        provider_order = next(
            occurrence
            for occurrence in provider_window.project_fact.dependency_occurrences
            if occurrence.role is WindowDependencyRole.WINDOW_ORDER
        )
        assert provider_order.target.output_name == "first"
        assert provider_order.target_result_role is ProjectRowResultRole.GROUP_KEY

    grouped_semantic, grouped_relation = grouped_relations[0]
    grouped_window = grouped_relation.window_outputs[0]
    assert grouped_window.project_fact is not None
    grouped_order = next(
        occurrence
        for occurrence in grouped_window.project_fact.dependency_occurrences
        if occurrence.role is WindowDependencyRole.WINDOW_ORDER
    )
    forged_occurrences = tuple(
        replace(
            occurrence,
            target=replace(
                occurrence.target,
                name="second",
                output_name="second",
            ),
        )
        if occurrence is grouped_order
        else occurrence
        for occurrence in grouped_window.project_fact.dependency_occurrences
    )
    forged_project_fact = replace(
        grouped_window.project_fact,
        dependency_occurrences=forged_occurrences,
        dependency_edges=deduplicate_window_dependency_edges(forged_occurrences),
    )
    forged_window = replace(
        grouped_window,
        project_fact=forged_project_fact,
        retained_project_fact=forged_project_fact,
    )
    with pytest.raises(ValueError, match="exact source and target authority"):
        _replace_window_in_final_semantic(
            grouped_semantic,
            grouped_relation,
            grouped_window,
            forged_window,
        )


def test_ordinary_group_aggregate_and_window_result_roles_remain_distinct_in_one_relation(
    tmp_path: Path,
) -> None:
    source = _query(
        "    group by:\n        id\n"
        "    select:\n"
        "        id\n"
        "        total = sum(amount)\n"
        "        position = rank() window:\n"
        "            order by:\n                total desc\n"
        "    order by:\n"
        "        position\n"
        "        position desc\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    relation = _relation(semantic, "main.pietto", "result")
    assert relation.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert relation.state.schema is not None
    assert tuple(
        field.result_role for field in relation.state.schema.fields.values()
    ) == (
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
        ProjectRowResultRole.WINDOW_RESULT,
    )
    assert preservation._capability_inventory().result_roles[0] is (
        ProjectRowResultRole.ORDINARY_ROW_VALUE
    )
    grouped_order = tuple(
        fact
        for fact in relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )
    assert tuple(fact.source_ordinal for fact in grouped_order) == (0, 1)
    assert all(
        fact.target_occurrences == (relation.select_facts[2].item,)
        and fact.target_fields == (relation.state.schema.fields["position"],)
        and fact.target_fields[0].result_role is ProjectRowResultRole.WINDOW_RESULT
        and fact.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        for fact in grouped_order
    )

    _, satisfying_semantic = _semantic_project(
        tmp_path / "satisfying-stage",
        {
            "main.pietto": (
                _query(
                    "    group by:\n"
                    "        id\n"
                    "    select:\n"
                    "        id\n"
                    "        total = sum(amount)\n"
                    "        position = rank() window:\n"
                    "            order by:\n"
                    "                total desc\n"
                    "    satisfying:\n"
                    "        position > 0\n"
                )
                + "query downstream:\n"
                + "    from result\n"
                + "    select:\n"
                + "        total\n"
            )
        },
    )
    satisfying_relation = _relation(satisfying_semantic, "main.pietto", "result")
    satisfying = next(
        fact
        for fact in satisfying_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.SATISFYING
    )
    assert satisfying.target_occurrences == (satisfying_relation.select_facts[2].item,)
    assert satisfying.target_fields == ()
    assert satisfying.status is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    assert satisfying_relation.aggregate_grouped_clause_readiness is not None
    assert satisfying_relation.aggregate_grouped_clause_readiness.status is (
        preservation.ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    )
    assert satisfying_relation.aggregate_grouped_clause_readiness.reason is (
        preservation.ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE
    )
    assert satisfying_relation.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert satisfying_relation.state.reason is (
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    assert satisfying_relation.state.schema is not None
    assert satisfying_relation.state.schema.is_unknown
    assert not satisfying_relation.state.schema.fields
    assert satisfying_relation.aggregate_result_facts == ()
    assert all(
        fact.aggregate_result_fact is None for fact in satisfying_relation.select_facts
    )
    assert len(satisfying_relation.window_outputs) == 1
    assert satisfying_relation.window_outputs[0].analysis is not None
    assert satisfying_relation.window_outputs[0].project_fact is None
    assert satisfying_relation.window_outputs[0].status is (
        preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    satisfying_downstream = _relation(
        satisfying_semantic,
        "main.pietto",
        "downstream",
    )
    assert satisfying_downstream.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        satisfying_downstream.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    )
    assert satisfying_downstream.state.schema is not None
    assert satisfying_downstream.state.schema.is_unknown
    assert not satisfying_downstream.state.schema.fields
    assert satisfying_downstream.aggregate_result_facts == ()
    assert satisfying_downstream.select_facts[0].field is None
    with pytest.raises(
        ValueError,
        match="Non-concrete clause readiness must control the relation state",
    ):
        replace(
            satisfying_relation,
            state=satisfying_relation.aggregate_grouped_clause_readiness.finalization.state,
        )

    missing_grouped_order_source = (
        _query(
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        total = sum(amount)\n"
            "    order by:\n"
            "        missing\n"
        )
        + "query downstream:\n"
        + "    from result\n"
        + "    select:\n"
        + "        total\n"
    )
    _, missing_semantic = _semantic_project(
        tmp_path / "missing-grouped-order",
        {"main.pietto": missing_grouped_order_source},
    )
    missing_relation = _relation(missing_semantic, "main.pietto", "result")
    assert missing_relation.aggregate_grouped_clause_readiness is not None
    assert missing_relation.aggregate_grouped_clause_readiness.status is (
        preservation.ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    )
    assert missing_relation.aggregate_grouped_clause_readiness.reason is (
        preservation.ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
    )
    assert missing_relation.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert missing_relation.state.reason is (
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
    )
    assert missing_relation.aggregate_result_facts == ()
    assert all(
        fact.aggregate_result_fact is None for fact in missing_relation.select_facts
    )
    missing_grouped_order = next(
        fact
        for fact in missing_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )
    assert missing_grouped_order.status is (
        preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    assert missing_grouped_order.target_occurrences == ()
    assert missing_grouped_order.target_fields == ()
    missing_downstream = _relation(missing_semantic, "main.pietto", "downstream")
    assert missing_downstream.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        missing_downstream.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    )
    assert missing_downstream.state.schema is not None
    assert missing_downstream.state.schema.is_unknown
    assert not missing_downstream.state.schema.fields
    assert missing_downstream.select_facts[0].field is None

    concrete_readiness = relation.aggregate_grouped_clause_readiness
    assert concrete_readiness is not None
    assert (
        preservation._relation_state_from_aggregate_grouped_clause_readiness(
            concrete_readiness
        )
        is concrete_readiness.finalization.state
    )
    unknown_finalization_state = preservation.ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=preservation.ProjectRowSchema(is_unknown=True),
        reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    )
    mirrored_readiness = replace(
        concrete_readiness,
        finalization=replace(
            concrete_readiness.finalization,
            state=unknown_finalization_state,
            aggregate_result_facts={},
        ),
        status=preservation.ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
        reason=(
            preservation.ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
        ),
        dependency_facts=(),
        limit_present=False,
    )
    assert (
        preservation._relation_state_from_aggregate_grouped_clause_readiness(
            mirrored_readiness
        )
        is unknown_finalization_state
    )
    for readiness_reason, expected_reason in (
        (
            preservation.ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        ),
        (
            preservation.ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ),
        (
            preservation.ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ),
    ):
        unknown_readiness = replace(
            concrete_readiness,
            status=preservation.ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            reason=readiness_reason,
            dependency_facts=(),
        )
        unknown_state = (
            preservation._relation_state_from_aggregate_grouped_clause_readiness(
                unknown_readiness
            )
        )
        assert unknown_state.status is ProjectRelationRowSchemaStatus.UNKNOWN
        assert unknown_state.reason is expected_reason
        assert unknown_state.schema is not None
        assert unknown_state.schema.is_unknown
        assert not unknown_state.schema.fields

    for readiness_reason in (
        preservation.ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        preservation.ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
    ):
        blocked_readiness = replace(
            concrete_readiness,
            status=preservation.ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            reason=readiness_reason,
            dependency_facts=(),
        )
        blocked_state = (
            preservation._relation_state_from_aggregate_grouped_clause_readiness(
                blocked_readiness
            )
        )
        assert blocked_state.status is ProjectRelationRowSchemaStatus.BLOCKED
        assert blocked_state.reason is (
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )
        assert blocked_state.schema is None

    _, deferred_semantic = _semantic_project(
        tmp_path / "unsupported-no-group-order",
        {
            "main.pietto": _query(
                "    select:\n"
                "        total = sum(amount)\n"
                "    order by:\n"
                "        amount desc\n"
            )
        },
    )
    deferred_relation = _relation(deferred_semantic, "main.pietto", "result")
    deferred_readiness = deferred_relation.aggregate_grouped_clause_readiness
    assert deferred_readiness is not None
    assert deferred_readiness.status is (
        preservation.ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
    )
    assert deferred_readiness.reason is (
        preservation.ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
    )
    deferred_state = (
        preservation._relation_state_from_aggregate_grouped_clause_readiness(
            deferred_readiness
        )
    )
    assert deferred_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert deferred_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert deferred_state.schema is None
    assert deferred_relation.state == deferred_state
    assert deferred_relation.aggregate_result_facts == ()
    assert all(
        fact.aggregate_result_fact is None for fact in deferred_relation.select_facts
    )

    invalid_readiness = replace(
        concrete_readiness,
        status=preservation.ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
        reason=(
            preservation.ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        ),
        dependency_facts=(),
    )
    object.__setattr__(
        invalid_readiness,
        "reason",
        preservation.ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY,
    )
    with pytest.raises(
        ValueError,
        match="Unsupported aggregate/grouped clause-readiness outcome",
    ):
        preservation._relation_state_from_aggregate_grouped_clause_readiness(
            invalid_readiness
        )

    _, collision_semantic = _semantic_project(
        tmp_path / "collision",
        {
            "main.pietto": _query(
                "    group by:\n"
                "        id\n"
                "    select:\n"
                "        id\n"
                "        duplicate = sum(amount)\n"
                "        duplicate = rank() window:\n"
                "            order by:\n"
                "                id\n"
                "    satisfying:\n"
                "        duplicate > 0\n"
                "    order by:\n"
                "        duplicate\n"
            )
        },
    )
    collision_relation = _relation(collision_semantic, "main.pietto", "result")
    assert collision_relation.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        collision_relation.state.reason
        is ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
    )
    collision_order = next(
        fact
        for fact in collision_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.GROUPED_ORDER
    )
    assert collision_order.target_occurrences == tuple(
        fact.item
        for fact in collision_relation.select_facts
        if fact.output_name == "duplicate"
    )
    assert collision_order.target_fields == ()
    collision_satisfying = next(
        fact
        for fact in collision_relation.clause_dependencies
        if fact.role is preservation.ProjectModuleFactOccurrenceRole.SATISFYING
    )
    collision_occurrences = tuple(
        fact.item
        for fact in collision_relation.select_facts
        if fact.output_name == "duplicate"
    )
    assert collision_satisfying.target_occurrences == collision_occurrences
    assert collision_order.target_occurrences == collision_occurrences
    assert len(collision_satisfying.target_fields) == 1
    assert (
        collision_satisfying.target_fields[0].result_role
        is ProjectRowResultRole.AGGREGATE_RESULT
    )
    assert len(collision_satisfying.aggregate_result_facts) == 1
    assert collision_order.aggregate_result_facts == (
        collision_satisfying.aggregate_result_facts[0],
    )
    assert collision_relation.aggregate_result_facts == ()
    assert all(
        fact.aggregate_result_fact is None for fact in collision_relation.select_facts
    )
    assert (
        collision_satisfying.status
        is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    assert (
        collision_order.status
        is preservation.ProjectModuleCandidateBucketStatus.UNKNOWN
    )


def test_nominal_generic_same_spelling_types_fail_closed_without_cross_module_merge(
    tmp_path: Path,
) -> None:
    template = (
        "enum Status:\n    active\n"
        "shape Row:\n    status: Status\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": template, "b.pietto": template},
    )
    first = _relation(semantic, "a.pietto", "rows").state.schema
    second = _relation(semantic, "b.pietto", "rows").state.schema
    assert first is not None and second is not None
    first_symbol = first.fields["status"].resolved_type.symbol
    second_symbol = second.fields["status"].resolved_type.symbol
    assert first_symbol is not None and second_symbol is not None
    assert first_symbol.path == "a.pietto"
    assert second_symbol.path == "b.pietto"
    assert first_symbol != second_symbol


def test_sidecar_builder_is_pure_over_preloaded_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse_result, semantic = _semantic_project(tmp_path, {"main.pietto": _prefix()})
    catalogs = semantic.module_catalogs
    resolutions = semantic.module_relation_resolutions
    assert catalogs is not None and resolutions is not None

    def forbidden_open(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("Slice 12 builder attempted filesystem IO")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    rebuilt = preservation._build_project_module_semantic_fact_set(
        parse_result.modules,
        catalogs,
        resolutions,
    )
    assert rebuilt == semantic.module_semantic_facts


def test_schema_v2_public_api_cli_json_metadata_ir_sql_dependencies_version_and_goldens_are_unchanged(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query("    select:\n        total = id + 1\n")},
    )
    assert semantic.model is None
    payload = project_check_result_to_json_dict(parse_result)
    encoded = json.dumps(payload, sort_keys=True)
    assert "module_semantic_facts" not in encoded
    assert "semantic_fact_preservation" not in encoded
    project_init = (REPO_ROOT / "src/pietto/_project/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "module_semantic_fact_preservation" not in project_init
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    actual = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert actual == EXPECTED_TEST_NAMES
    assert all(
        not node.decorator_list
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
