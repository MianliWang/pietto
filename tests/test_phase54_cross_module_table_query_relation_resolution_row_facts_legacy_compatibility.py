from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_relation_resolution as relation_resolution
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto.ast_nodes import QueryDef, SourceDef, TableDef


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice10-cross-module-table-query-relation-resolution-"
    "row-facts-and-legacy-compatibility-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_relation_resolution.py"
TEST_REL = (
    "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_"
    "legacy_compatibility.py"
)

EXPECTED_TEST_NAMES = (
    "test_slice10_contract_and_status_docs_freeze_exact_boundary",
    "test_relation_issue_status_and_private_carriers_are_frozen_slotted_keyword_only",
    "test_local_resolved_relation_symbol_preserves_exact_nominal_identity",
    "test_imported_relation_alias_preserves_binding_and_nominal_target_identity",
    "test_resolved_relation_symbol_rejects_mixed_sources_and_wrong_kinds",
    "test_relation_reference_and_resolution_require_exact_retained_ast_sites",
    "test_relation_row_fact_reuses_existing_availability_state_invariants",
    "test_module_relation_environment_keeps_order_and_complete_immutable_lookups",
    "test_relation_resolution_set_requires_dependency_order_and_exact_diagnostic_projection",
    "test_builder_is_pure_over_preloaded_inputs_and_performs_no_io",
    "test_local_sources_tables_and_queries_use_one_collect_before_resolve_namespace",
    "test_imported_source_alias_resolves_in_relation_namespace",
    "test_imported_table_alias_resolves_with_distinct_table_kind",
    "test_imported_query_alias_resolves_with_distinct_query_kind",
    "test_explicit_reexport_preserves_direct_facade_and_original_table_identity",
    "test_explicit_reexport_preserves_original_query_identity",
    "test_dependency_first_order_and_selected_position_tie_break_are_exact",
    "test_cyclic_direct_facade_blocks_before_acyclic_nominal_target",
    "test_module_cycle_emits_only_pie_s2703_root_for_relation_resolution",
    "test_local_import_collision_blocks_complete_relation_bucket_without_winner",
    "test_import_import_collision_blocks_complete_relation_bucket_without_winner",
    "test_duplicate_local_relation_cross_kind_emits_one_pie_s2001_without_winner",
    "test_duplicate_local_sources_reuse_slice9_root_without_duplicate_diagnostic",
    "test_unknown_local_relation_emits_exact_pie_s2301",
    "test_wrong_kind_import_root_suppresses_derived_unknown_relation",
    "test_repeated_consumers_of_one_failed_import_do_not_duplicate_root",
    "test_independent_local_relation_error_remains_visible_with_module_root",
    "test_local_self_cycle_emits_exact_pie_s2302_and_blocks_row_fact",
    "test_local_multi_node_cycle_is_deterministic_and_blocks_every_member",
    "test_source_row_fact_preserves_field_order_types_definitions_and_minimal_nullability",
    "test_invalid_or_untyped_source_row_fact_is_unknown_without_cascade",
    "test_direct_bare_qualified_and_renamed_fields_produce_concrete_row_facts",
    "test_import_alias_is_only_valid_immediate_qualifier_and_original_name_fails",
    "test_query_to_query_multi_hop_propagates_concrete_rows_in_local_dependency_order",
    "test_unknown_deferred_and_blocked_upstream_states_propagate_exact_reasons",
    "test_duplicate_output_is_unknown_advanced_rows_defer_and_legacy_public_bytes_stay_exact",
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
    project_root = _configured_project(root, sources, schema_version=schema_version)
    parse_result = project_check.check_project_parse_only(project_root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _required_set(
    semantic: ProjectSemanticResult,
) -> relation_resolution.ProjectModuleRelationResolutionSet:
    result = semantic.module_relation_resolutions
    assert result is not None
    return result


def _environment(
    semantic: ProjectSemanticResult,
    module_path: str,
) -> relation_resolution.ProjectModuleRelationResolutionEnvironment:
    matches = _required_set(semantic).find_module_path(module_path)
    assert len(matches) == 1
    return matches[0]


def _definition(
    parse_result: ProjectParseCheckResult,
    module_path: str,
    name: str,
) -> SourceDef | TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        if parsed_input.path != module_path:
            continue
        for definition in parsed_input.script.definitions:
            if (
                type(definition) in {SourceDef, TableDef, QueryDef}
                and definition.name == name
            ):
                return cast(SourceDef | TableDef | QueryDef, definition)
    raise AssertionError(f"Relation definition not found: {module_path}:{name}")


def _fact(
    semantic: ProjectSemanticResult,
    module_path: str,
    definition: SourceDef | TableDef | QueryDef,
) -> relation_resolution.ProjectModuleRelationRowFact:
    matches = _environment(semantic, module_path).find_definition(definition)
    assert len(matches) == 1
    return matches[0]


def _diagnostic_pairs(
    semantic: ProjectSemanticResult,
) -> tuple[tuple[str, str], ...]:
    return tuple((item.code, item.message) for item in semantic.diagnostics)


def _library_source(*, export_relation: str = "table projected") -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    name: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        name\n"
        "query reported:\n"
        "    from projected\n"
        "    select:\n"
        "        id\n"
        "        name\n"
        f"export:\n    {export_relation}\n"
    )


def test_slice10_contract_and_status_docs_freeze_exact_boundary() -> None:
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    current = (REPO_ROOT / "docs/spec/pietto-v0.9.md").read_text(encoding="utf-8")
    assert "Schema v1 continues to use the byte-exact legacy-flat resolver" in spec
    assert "There is no cross-namespace fallback" in spec
    assert "Slice 10 is the\nGate 2 cross-module relation-resolution" in readme
    assert "## Status And Slice 10 Lifecycle" in plan
    assert (
        "## Current Phase 54 Slice 10 Cross-module Relation And Row-fact Status"
        in current
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == "PHASE54_SLICE10_GATE2"
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "fadb1924af057cfc901a1658e117810d699e2358"
    )
    assert len(active_gate2_manifest.ADDED_PATHS) == 3
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 69
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 72
    assert active_gate2_manifest.phase54_active_gate2_manifest_is_active()


def test_relation_issue_status_and_private_carriers_are_frozen_slotted_keyword_only() -> (
    None
):
    assert relation_resolution.__all__ == ()
    assert tuple(relation_resolution.ProjectModuleRelationResolutionIssueStatus) == (
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
        relation_resolution.ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
    )
    expected_fields = {
        relation_resolution.ProjectResolvedModuleRelationSymbol: (
            "owning_module_path",
            "local_name",
            "target_identity",
            "target_occurrence",
            "local_occurrence",
            "imported_binding",
        ),
        relation_resolution.ProjectModuleRelationReference: (
            "owner",
            "from_clause",
        ),
        relation_resolution.ProjectResolvedModuleRelationReference: (
            "reference",
            "target_symbol",
        ),
        relation_resolution.ProjectModuleRelationRowFact: ("owner", "state"),
        relation_resolution.ProjectModuleRelationResolutionEnvironment: (
            "module",
            "symbols",
            "references",
            "resolutions",
            "row_facts",
            "issues",
            "_symbols_by_name",
            "_resolutions_by_from_clause",
            "_row_facts_by_definition",
        ),
        relation_resolution.ProjectModuleRelationResolutionSet: (
            "dependency_order",
            "environments",
            "issues",
            "diagnostics",
            "_environments_by_path",
            "_symbols_by_target_identity",
        ),
    }
    for carrier, names in expected_fields.items():
        assert tuple(item.name for item in fields(carrier)) == names
        assert "__dict__" not in carrier.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )


def test_local_resolved_relation_symbol_preserves_exact_nominal_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"a.pietto": _library_source()})
    environment = _environment(semantic, "a.pietto")
    symbol = environment.find_relation_name("projected")[0]
    assert symbol.local_name == "projected"
    assert symbol.target_identity.module_path == "a.pietto"
    assert symbol.target_identity.declared_name == "projected"
    assert symbol.declaration_kind is ProjectSymbolKind.TABLE
    assert symbol.local_occurrence is symbol.target_occurrence
    assert symbol.imported_binding is None
    with pytest.raises(FrozenInstanceError):
        symbol.local_name = "rewritten"  # type: ignore[misc]


def test_imported_relation_alias_preserves_binding_and_nominal_target_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table projected as Local\n'
                "query result:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Local")[0]
    assert symbol.local_name == "Local"
    assert symbol.target_identity.module_path == "b.pietto"
    assert symbol.target_identity.declared_name == "projected"
    assert symbol.imported_binding is not None
    assert symbol.imported_binding.target_module_path == "b.pietto"
    assert symbol.local_occurrence is None


def test_resolved_relation_symbol_rejects_mixed_sources_and_wrong_kinds(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "b.pietto":\n    table projected as Local\n',
            "b.pietto": _library_source(),
        },
    )
    imported = _environment(semantic, "a.pietto").find_relation_name("Local")[0]
    with pytest.raises(ValueError, match="exactly one binding source"):
        replace(imported, imported_binding=None)
    local = _environment(semantic, "b.pietto").find_relation_name("projected")[0]
    with pytest.raises(ValueError, match="exactly one binding source"):
        replace(local, imported_binding=imported.imported_binding)
    type_identity = next(
        occurrence.identity
        for occurrence in semantic.module_catalogs.catalogs[1].occurrences  # type: ignore[union-attr]
        if occurrence.identity.declaration_kind is ProjectSymbolKind.SHAPE
    )
    with pytest.raises(ValueError, match="not relation-producing"):
        replace(local, target_identity=type_identity)


def test_relation_reference_and_resolution_require_exact_retained_ast_sites(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "table first:\n    from rows\n    select:\n        id\n"
                "query second:\n    from first\n    select:\n        id\n"
            )
        },
    )
    environment = _environment(semantic, "a.pietto")
    first = _definition(parse_result, "a.pietto", "first")
    second = _definition(parse_result, "a.pietto", "second")
    assert type(first) is TableDef and type(second) is QueryDef
    first_resolution = environment.find_from_clause(first.from_clause)[0]
    with pytest.raises(ValueError, match="retained AST"):
        replace(first_resolution.reference, from_clause=second.from_clause)
    other_target = environment.find_relation_name("first")[0]
    with pytest.raises(ValueError, match="local lookup"):
        replace(first_resolution, target_symbol=other_target)


def test_relation_row_fact_reuses_existing_availability_state_invariants(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _library_source()},
    )
    projected = _definition(parse_result, "a.pietto", "projected")
    fact = _fact(semantic, "a.pietto", projected)
    assert fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert fact.state.schema is not None
    with pytest.raises(FrozenInstanceError):
        fact.state = fact.state  # type: ignore[misc]
    with pytest.raises(ValueError, match="requires schema"):
        replace(fact.state, schema=None)


def test_module_relation_environment_keeps_order_and_complete_immutable_lookups(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _library_source()},
    )
    environment = _environment(semantic, "a.pietto")
    assert tuple(symbol.local_name for symbol in environment.symbols) == (
        "rows",
        "projected",
        "reported",
    )
    assert tuple(
        fact.owner.identity.declared_name for fact in environment.row_facts
    ) == (
        "rows",
        "projected",
        "reported",
    )
    projected = _definition(parse_result, "a.pietto", "projected")
    assert type(projected) is TableDef
    assert len(environment.find_relation_name("projected")) == 1
    assert len(environment.find_from_clause(projected.from_clause)) == 1
    assert len(environment.find_definition(projected)) == 1
    assert isinstance(environment._symbols_by_name, MappingProxyType)
    with pytest.raises(TypeError):
        environment._symbols_by_name["x"] = ()  # type: ignore[index]


def test_relation_resolution_set_requires_dependency_order_and_exact_diagnostic_projection(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": ("query broken:\n    from missing\n    select:\n        id\n")},
    )
    result = _required_set(semantic)
    assert tuple(item.path for item in result.dependency_order) == ("a.pietto",)
    assert result.diagnostics == tuple(
        issue.diagnostic for issue in result.issues if issue.diagnostic is not None
    )
    assert isinstance(result._environments_by_path, MappingProxyType)
    with pytest.raises(ValueError, match="follow dependency order"):
        replace(result, dependency_order=())
    with pytest.raises(ValueError, match="project exact issues"):
        replace(result, diagnostics=())


def test_builder_is_pure_over_preloaded_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(tmp_path, {"a.pietto": _library_source()})
    parse_result = project_check.check_project_parse_only(root)
    assert parse_result.ok

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("semantic sidecars must not perform filesystem IO")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    semantic = build_empty_project_semantic_result(parse_result)
    assert _required_set(semantic).environments


def test_local_sources_tables_and_queries_use_one_collect_before_resolve_namespace(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "query final:\n    from projected\n    select:\n        id\n"
                "table projected:\n    from rows\n    select:\n        id\n"
                'source rows: Row is postgres.table("rows")\n'
                "shape Row:\n    id: Int not null\n"
            )
        },
    )
    assert semantic.diagnostics == ()
    environment = _environment(semantic, "a.pietto")
    assert {symbol.declaration_kind for symbol in environment.symbols} == {
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }
    final = _definition(parse_result, "a.pietto", "final")
    assert (
        _fact(semantic, "a.pietto", final).state.status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )


def test_imported_source_alias_resolves_in_relation_namespace(tmp_path: Path) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    source rows as Input\n'
                "query result:\n    from Input\n    select:\n        id\n"
            ),
            "b.pietto": (
                "shape Row:\n    id: Int not null\n"
                'source rows: Row is postgres.table("rows")\n'
                "export:\n    source rows\n"
            ),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Input")[0]
    assert symbol.declaration_kind is ProjectSymbolKind.SOURCE
    result = _definition(parse_result, "a.pietto", "result")
    assert tuple(_fact(semantic, "a.pietto", result).state.schema.fields) == ("id",)  # type: ignore[union-attr]


def test_imported_table_alias_resolves_with_distinct_table_kind(tmp_path: Path) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table projected as Input\n'
                "query result:\n    from Input\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Input")[0]
    assert symbol.declaration_kind is ProjectSymbolKind.TABLE
    result = _definition(parse_result, "a.pietto", "result")
    assert (
        _fact(semantic, "a.pietto", result).state.status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )


def test_imported_query_alias_resolves_with_distinct_query_kind(tmp_path: Path) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    query reported as Input\n'
                "query result:\n    from Input\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(export_relation="query reported"),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Input")[0]
    assert symbol.declaration_kind is ProjectSymbolKind.QUERY
    result = _definition(parse_result, "a.pietto", "result")
    assert (
        _fact(semantic, "a.pietto", result).state.status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )


def test_explicit_reexport_preserves_direct_facade_and_original_table_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "b.pietto":\n    table Public as Local\n',
            "b.pietto": (
                'import "c.pietto":\n    table projected as Public\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": _library_source(),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Local")[0]
    assert symbol.imported_binding is not None
    assert symbol.imported_binding.target_module_path == "b.pietto"
    assert symbol.target_identity.module_path == "c.pietto"
    assert symbol.target_identity.declared_name == "projected"
    assert symbol.declaration_kind is ProjectSymbolKind.TABLE


def test_explicit_reexport_preserves_original_query_identity(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "b.pietto":\n    query Public as Local\n',
            "b.pietto": (
                'import "c.pietto":\n    query reported as Public\n'
                "export:\n    query Public\n"
            ),
            "c.pietto": _library_source(export_relation="query reported"),
        },
    )
    symbol = _environment(semantic, "a.pietto").find_relation_name("Local")[0]
    assert symbol.target_identity.module_path == "c.pietto"
    assert symbol.target_identity.declared_name == "reported"
    assert symbol.declaration_kind is ProjectSymbolKind.QUERY


def test_dependency_first_order_and_selected_position_tie_break_are_exact(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": "shape A:\n    id: Int\n",
            "b.pietto": _library_source(),
            "c.pietto": 'import "b.pietto":\n    table projected\n',
        },
    )
    assert tuple(item.path for item in _required_set(semantic).dependency_order) == (
        "a.pietto",
        "b.pietto",
        "c.pietto",
    )


def test_cyclic_direct_facade_blocks_before_acyclic_nominal_target(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table Public as Local\n'
                "query result:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    table projected as Public\n'
                'import "d.pietto":\n    query D\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": _library_source(),
            "d.pietto": (
                "query D:\n    from missing\n    select:\n        id\n"
                "export:\n    query D\n"
                'import "b.pietto":\n    table Public\n'
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        (
            "PIE-S2703",
            "Module import cycle detected: b.pietto -> d.pietto -> b.pietto",
        ),
    )
    environment = _environment(semantic, "a.pietto")
    assert environment.find_relation_name("Local") == ()
    blocker = next(
        issue
        for issue in environment.issues
        if issue.local_name == "Local"
        and issue.status
        is relation_resolution.ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
    )
    assert blocker.module_cycle is not None
    assert tuple(
        member.identity.path for member in blocker.module_cycle.component.members
    ) == ("b.pietto", "d.pietto")


def test_module_cycle_emits_only_pie_s2703_root_for_relation_resolution(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    query B\n'
                "query A:\n    from B\n    select:\n        id\n"
                "export:\n    query A\n"
            ),
            "b.pietto": (
                'import "a.pietto":\n    query A\n'
                "query B:\n    from A\n    select:\n        id\n"
                "export:\n    query B\n"
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2703", "Module import cycle detected: a.pietto -> b.pietto -> a.pietto"),
    )
    result = _required_set(semantic)
    assert result.environments == ()
    assert len(result.issues) == 2


def test_local_import_collision_blocks_complete_relation_bucket_without_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Local = Int\n"
                'import "b.pietto":\n    table projected as Local\n'
                "query result:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2706", "Import binding collides with a local declaration: Local"),
    )
    assert _environment(semantic, "a.pietto").find_relation_name("Local") == ()


def test_import_import_collision_blocks_complete_relation_bucket_without_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table projected as Shared\n'
                'import "c.pietto":\n    query reported as Shared\n'
                "query result:\n    from Shared\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(),
            "c.pietto": _library_source(export_relation="query reported"),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2706", "Import binding name is ambiguous: Shared"),
    )
    assert _environment(semantic, "a.pietto").find_relation_name("Shared") == ()


def test_duplicate_local_relation_cross_kind_emits_one_pie_s2001_without_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Row:\n    id: Int\n"
                'source Shared: Row is postgres.table("rows")\n'
                "table Shared:\n    from Shared\n    select:\n        id\n"
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2001", "Duplicate symbol name in relation namespace: Shared"),
    )
    assert _environment(semantic, "a.pietto").find_relation_name("Shared") == ()


def test_duplicate_local_sources_reuse_slice9_root_without_duplicate_diagnostic(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("one")\n'
                'source rows: Row is postgres.table("two")\n'
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2001", "Duplicate symbol name in relation namespace: rows"),
    )
    blockers = tuple(
        issue
        for issue in _environment(semantic, "a.pietto").issues
        if issue.status
        is relation_resolution.ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED
    )
    assert len(blockers) == 1


def test_unknown_local_relation_emits_exact_pie_s2301(tmp_path: Path) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "query broken:\n    from missing\n    select:\n        id\n"},
    )
    assert _diagnostic_pairs(semantic) == (("PIE-S2301", "Unknown relation: missing"),)
    broken = _definition(parse_result, "a.pietto", "broken")
    fact = _fact(semantic, "a.pietto", broken)
    assert fact.state.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert (
        fact.state.reason is ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
    )


def test_wrong_kind_import_root_suppresses_derived_unknown_relation(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table reported as Local\n'
                "query result:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(export_relation="query reported"),
        },
    )
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2707",)
    assert all(item.code != "PIE-S2301" for item in semantic.diagnostics)
    assert _environment(semantic, "a.pietto").find_relation_name("Local") == ()


def test_repeated_consumers_of_one_failed_import_do_not_duplicate_root(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table reported as Local\n'
                "query first:\n    from Local\n    select:\n        id\n"
                "query second:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": _library_source(export_relation="query reported"),
        },
    )
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2707",)
    environment = _environment(semantic, "a.pietto")
    assert (
        len(tuple(issue for issue in environment.issues if issue.local_name == "Local"))
        == 1
    )


def test_independent_local_relation_error_remains_visible_with_module_root(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "missing.pietto":\n    table absent as Blocked\n'
                "query derived:\n    from Blocked\n    select:\n        id\n"
                "query independent:\n    from local_missing\n    select:\n        id\n"
            )
        },
    )
    assert tuple(item.code for item in semantic.diagnostics) == (
        "PIE-S2701",
        "PIE-S2301",
    )


def test_local_self_cycle_emits_exact_pie_s2302_and_blocks_row_fact(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "query loop:\n    from loop\n    select:\n        id\n"},
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2302", "Relation cycle detected: loop -> loop"),
    )
    loop = _definition(parse_result, "a.pietto", "loop")
    fact = _fact(semantic, "a.pietto", loop)
    assert fact.state.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert fact.state.reason is ProjectRelationRowSchemaReason.CYCLE_BLOCKED


def test_local_multi_node_cycle_is_deterministic_and_blocks_every_member(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "query first:\n    from second\n    select:\n        id\n"
                "query second:\n    from third\n    select:\n        id\n"
                "query third:\n    from first\n    select:\n        id\n"
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2302", "Relation cycle detected: first -> second -> third -> first"),
    )
    assert all(
        _fact(
            semantic, "a.pietto", _definition(parse_result, "a.pietto", name)
        ).state.reason
        is ProjectRelationRowSchemaReason.CYCLE_BLOCKED
        for name in ("first", "second", "third")
    )


def test_source_row_fact_preserves_field_order_types_definitions_and_minimal_nullability(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Identifier = Int\n"
                "enum Status:\n    active\n"
                "shape Row:\n"
                "    id: Identifier not null\n"
                "    status: Status nullable\n"
                "    label: Text\n"
                'source rows: Row is postgres.table("rows")\n'
            )
        },
    )
    source = _definition(parse_result, "a.pietto", "rows")
    state = _fact(semantic, "a.pietto", source).state
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.schema is not None
    assert tuple(state.schema.fields) == ("id", "status", "label")
    assert tuple(
        field.resolved_type.kind for field in state.schema.fields.values()
    ) == (
        ProjectResolvedTypeKind.BUILTIN,
        ProjectResolvedTypeKind.ENUM,
        ProjectResolvedTypeKind.BUILTIN,
    )
    assert tuple(field.nullability for field in state.schema.fields.values()) == (
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.UNKNOWN,
    )
    assert all(field.field_def is not None for field in state.schema.fields.values())
    assert all(field.provenance is None for field in state.schema.fields.values())


def test_invalid_or_untyped_source_row_fact_is_unknown_without_cascade(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'source raw is postgres.table("raw")\n'
                'source broken: Missing is postgres.table("broken")\n'
                "query raw_query:\n    from raw\n    select:\n        id\n"
                "query broken_query:\n    from broken\n    select:\n        id\n"
            )
        },
    )
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2303",)
    for name in ("raw", "broken", "raw_query", "broken_query"):
        fact = _fact(semantic, "a.pietto", _definition(parse_result, "a.pietto", name))
        assert fact.state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert all(item.code != "PIE-S2102" for item in semantic.diagnostics)


def test_direct_bare_qualified_and_renamed_fields_produce_concrete_row_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Row:\n    id: Int not null\n    name: Text nullable\n"
                'source rows: Row is postgres.table("rows")\n'
                "table projected:\n"
                "    from rows\n"
                "    select:\n"
                "        id\n"
                "        label = rows.name\n"
            )
        },
    )
    projected = _definition(parse_result, "a.pietto", "projected")
    state = _fact(semantic, "a.pietto", projected).state
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.schema is not None
    assert tuple(state.schema.fields) == ("id", "label")
    assert state.schema.fields["id"].nullability is ProjectRowFieldNullability.NON_NULL
    assert (
        state.schema.fields["label"].nullability is ProjectRowFieldNullability.NULLABLE
    )


def test_import_alias_is_only_valid_immediate_qualifier_and_original_name_fails(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    source rows as Input\n'
                "query valid:\n    from Input\n    select:\n        Input.id\n"
                "query invalid:\n    from Input\n    select:\n        rows.id\n"
            ),
            "b.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "export:\n    source rows\n"
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (("PIE-S2102", "Unknown field: rows.id"),)
    valid = _definition(parse_result, "a.pietto", "valid")
    invalid = _definition(parse_result, "a.pietto", "invalid")
    assert (
        _fact(semantic, "a.pietto", valid).state.status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert (
        _fact(semantic, "a.pietto", invalid).state.status
        is ProjectRelationRowSchemaStatus.UNKNOWN
    )


def test_query_to_query_multi_hop_propagates_concrete_rows_in_local_dependency_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    query reported as Imported\n'
                "query local_one:\n    from Imported\n    select:\n        id\n        name\n"
                "query local_two:\n    from local_one\n    select:\n        name\n        id\n"
            ),
            "b.pietto": _library_source(export_relation="query reported"),
        },
    )
    local_two = _definition(parse_result, "a.pietto", "local_two")
    state = _fact(semantic, "a.pietto", local_two).state
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.schema is not None
    assert tuple(state.schema.fields) == ("name", "id")


def test_unknown_deferred_and_blocked_upstream_states_propagate_exact_reasons(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'source unknown is postgres.table("unknown")\n'
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "query unknown_child:\n    from unknown\n    select:\n        id\n"
                "query deferred:\n    from rows\n    select:\n        total = id + 1\n"
                "query deferred_child:\n    from deferred\n    select:\n        total\n"
                "query blocked:\n    from missing\n    select:\n        id\n"
                "query blocked_child:\n    from blocked\n    select:\n        id\n"
            )
        },
    )
    expected = {
        "unknown_child": (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        ),
        "deferred": (
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
        ),
        "deferred_child": (
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        ),
        "blocked": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
        ),
        "blocked_child": (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        ),
    }
    for name, (status, reason) in expected.items():
        state = _fact(
            semantic,
            "a.pietto",
            _definition(parse_result, "a.pietto", name),
        ).state
        assert (state.status, state.reason) == (status, reason)


def test_duplicate_output_is_unknown_advanced_rows_defer_and_legacy_public_bytes_stay_exact(
    tmp_path: Path,
) -> None:
    sources = {
        "a.pietto": (
            "shape Row:\n    id: Int not null\n    name: Text nullable\n"
            'source rows: Row is postgres.table("rows")\n'
            "query duplicate:\n"
            "    from rows\n"
            "    select:\n"
            "        value = id\n"
            "        value = name\n"
            "query advanced:\n"
            "    from rows\n"
            "    select:\n"
            "        total = id + 1\n"
        )
    }
    parse_result, explicit = _semantic_project(tmp_path / "explicit", sources)
    duplicate = _definition(parse_result, "a.pietto", "duplicate")
    advanced = _definition(parse_result, "a.pietto", "advanced")
    duplicate_state = _fact(explicit, "a.pietto", duplicate).state
    advanced_state = _fact(explicit, "a.pietto", advanced).state
    assert duplicate_state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert (
        duplicate_state.reason is ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
    )
    assert advanced_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert (
        advanced_state.reason
        is ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
    )
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)
    assert "module_relation_resolutions" not in serialized
    assert "ProjectModuleRelationRowFact" not in serialized

    legacy_parse, legacy = _semantic_project(
        tmp_path / "legacy",
        sources,
        schema_version=1,
    )
    assert legacy.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert legacy.model is not None
    assert legacy.module_relation_resolutions is None
    assert legacy.diagnostics == ()
    legacy_document = project_check_result_to_json_dict(legacy_parse)
    assert tuple(legacy_document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    public_source = (REPO_ROOT / "src/pietto/__init__.py").read_text(encoding="utf-8")
    assert "ProjectModuleRelationResolutionSet" not in public_source

    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    observed = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert observed == EXPECTED_TEST_NAMES
    assert len(observed) == 36
