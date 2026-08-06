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
from pietto.ast_nodes import NameExpr, QueryDef, SelectItem, SourceDef
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
)
from pietto.semantic.capability_lookup import Absent, Conflict, Found, Unknown
from pietto.semantic.window_semantics import (
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


def _unavailable_candidate_body(expressions: tuple[str, ...]) -> str:
    lines: list[str] = []
    if expressions:
        lines.append("    let:")
        lines.extend(f"        key = {expression}" for expression in expressions)
    lines.extend(
        ("    group by:", "        id", "    select:", "        projected = key")
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
            {"main.pietto": source_head + _unavailable_candidate_body(expressions)},
        )
        relation = _relation(semantic, "main.pietto", "result")
        definition = cast(QueryDef, relation.owner.definition)
        expected_lets = (
            ()
            if definition.let_clause is None
            else tuple(definition.let_clause.bindings)
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


def test_slice12_contract_status_active_manifest_and_allowlist_are_exact() -> None:
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
    assert len(active_gate2_manifest.NON_READER_MODIFIED_PATHS) == 5
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 65
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 70
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 73
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
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query("    select:\n        total = id + 1\n")},
    )
    facts = _fact_set(semantic)
    assert facts.authority.modules is parse_result.modules
    assert facts.authority.catalogs is semantic.module_catalogs
    assert facts.authority.relation_resolutions is semantic.module_relation_resolutions
    signature = inspect.signature(preservation._build_project_module_semantic_fact_set)
    assert tuple(signature.parameters) == (
        "modules",
        "catalogs",
        "relation_resolutions",
    )
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    assert "module_attribution" not in source


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
                "query a:\n    from b\n    select:\n        id\n"
                "query b:\n    from a\n    select:\n        id\n"
            )
        },
    )
    assert {
        _relation(local_semantic, "main.pietto", name).state.status
        for name in ("a", "b")
    } == {ProjectRelationRowSchemaStatus.BLOCKED}
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
        and output.project_fact is not None
        and output.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        for output in relation.window_outputs
    )


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
        and output.project_fact is not None
        and output.status is preservation.ProjectModuleCandidateBucketStatus.CONCRETE
        for output in relation.window_outputs
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
        for output in relation.window_outputs
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
