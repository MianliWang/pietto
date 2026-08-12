from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import inspect
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import cast

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_attribution as module_attribution
import pietto._project.module_relation_resolution as relation_resolution
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto.ast_nodes import TypeExpr
from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.sql import emit_postgres_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice11-module-attribution-dependency-origin-provenance-"
    "and-lineage-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_attribution.py"
TEST_REL = (
    "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py"
)

EXPECTED_TEST_NAMES = (
    "test_slice11_contract_status_and_active_manifest_freeze_exact_boundary",
    "test_private_carrier_enums_fields_and_sidecar_are_exact",
    "test_declaration_occurrence_identity_excludes_ast_payload_from_semantic_equality",
    "test_import_and_facade_occurrence_identities_preserve_positions_and_exact_names",
    "test_reference_occurrence_identity_uses_owner_role_and_position_not_ast_value",
    "test_row_field_identity_distinguishes_shape_source_and_projection_occurrences",
    "test_all_eight_declaration_kinds_receive_source_ordered_module_attribution",
    "test_all_six_import_export_kinds_preserve_local_binding_and_nominal_target",
    "test_local_declaration_origins_are_self_paths_without_facade_hops",
    "test_direct_import_origin_retains_local_alias_direct_facade_and_nominal_owner",
    "test_explicit_reexport_origin_retains_every_exact_import_and_facade_hop",
    "test_same_nominal_target_through_distinct_aliases_retains_distinct_origin_paths",
    "test_origin_target_lookup_returns_complete_deterministic_tuple",
    "test_module_import_dependencies_retain_every_graph_evidence_occurrence",
    "test_module_dependency_diamond_retains_all_direct_edges_without_best_path",
    "test_module_cycle_retains_raw_attribution_and_dependencies_without_resolved_provenance",
    "test_builtin_type_reference_has_attribution_and_builtin_terminal_without_nominal_dependency",
    "test_local_type_alias_chain_retains_every_reference_and_nominal_hop",
    "test_cross_module_alias_chain_retains_local_alias_and_canonical_target",
    "test_reexported_alias_chain_retains_each_facade_hop_and_nominal_occurrence",
    "test_shape_field_reference_occurrences_preserve_order_and_duplicate_spelling",
    "test_source_shape_provenance_retains_source_occurrence_shape_occurrence_and_route",
    "test_relation_from_dependency_retains_immediate_local_symbol_and_target_occurrence",
    "test_imported_source_table_query_dependencies_preserve_distinct_kinds_and_aliases",
    "test_reexported_relation_dependency_retains_direct_facade_and_original_target",
    "test_source_field_origins_preserve_shape_field_position_order_and_field_identity",
    "test_direct_bare_qualified_and_renamed_lineage_preserves_select_order",
    "test_imported_relation_alias_lineage_uses_only_consumer_local_qualifier_route",
    "test_local_multi_hop_lineage_preserves_every_immediate_projection_hop",
    "test_cross_module_multi_hop_lineage_preserves_binding_and_facade_evidence",
    "test_explicit_reexport_row_lineage_reaches_original_source_without_identity_rewrite",
    "test_same_spelling_cross_module_relations_and_fields_never_cross_wire",
    "test_multiple_outputs_sharing_one_source_root_remain_distinct_paths",
    "test_same_target_through_distinct_relation_aliases_retains_two_lineage_routes",
    "test_definition_and_selected_module_permutations_change_only_explicit_order_evidence",
    "test_unknown_ambiguous_and_blocked_references_have_raw_attribution_but_no_provenance",
    "test_local_relation_cycle_has_empty_lineage_for_every_blocked_member",
    "test_unknown_upstream_and_duplicate_output_publish_empty_nonconcrete_lineage",
    "test_computed_let_grouped_aggregate_and_window_rows_remain_outside_slice11_lineage",
    "test_fact_set_lookups_are_complete_tuple_backed_immutable_and_no_winner",
    "test_builder_rejects_incomplete_or_misaligned_retained_inputs",
    "test_builder_is_pure_over_preloaded_inputs_and_performs_no_io",
    "test_schema_v1_text_json_ir_sql_and_sidecar_absence_remain_byte_exact",
    "test_schema_v2_cli_json_public_exports_dependencies_version_and_generated_goldens_remain_unchanged",
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


def _facts(
    semantic: ProjectSemanticResult,
) -> module_attribution.ProjectModuleAttributionFactSet:
    result = semantic.module_attribution_facts
    assert result is not None
    return result


def _declaration(
    facts: module_attribution.ProjectModuleAttributionFactSet,
    module_path: str,
    name: str,
    *,
    kind: ProjectSymbolKind | None = None,
) -> module_attribution.ProjectModuleDeclarationAttribution:
    matches = tuple(
        item
        for item in facts.declarations
        if item.identity.identity.module_path == module_path
        and item.identity.identity.declared_name == name
        and (kind is None or item.identity.identity.declaration_kind is kind)
    )
    assert len(matches) == 1
    return matches[0]


def _reference(
    facts: module_attribution.ProjectModuleAttributionFactSet,
    module_path: str,
    owner_name: str,
    role: module_attribution.ProjectModuleReferenceRole,
    *,
    position: int = 0,
) -> module_attribution.ProjectModuleReferenceAttribution:
    matches = tuple(
        item
        for item in facts.references
        if item.identity.owner.identity.module_path == module_path
        and item.identity.owner.identity.declared_name == owner_name
        and item.identity.role is role
        and item.identity.member_position == position
    )
    assert len(matches) == 1
    return matches[0]


def _lineage(
    facts: module_attribution.ProjectModuleAttributionFactSet,
    module_path: str,
    owner_name: str,
) -> module_attribution.ProjectModuleRelationLineage:
    owner = _declaration(facts, module_path, owner_name).identity
    matches = facts.find_row_lineage(owner)
    assert len(matches) == 1
    return matches[0]


def _simple_library() -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    name: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        label = rows.name\n"
        "query reported:\n"
        "    from projected\n"
        "    select:\n"
        "        id\n"
        "        label\n"
    )


def _all_kind_library() -> str:
    return (
        "type Email = Text\n"
        "enum Status:\n"
        "    active\n"
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "query reported:\n"
        "    from projected\n"
        "    select:\n"
        "        id\n"
        "constraint valid(value: Text) -> Bool:\n"
        "    value == value\n"
        "derive normalized(value: Text) -> Text:\n"
        "    value\n"
        "export:\n"
        "    type Email\n"
        "    enum Status\n"
        "    shape Row\n"
        "    source rows\n"
        "    table projected\n"
        "    query reported\n"
    )


def test_slice11_contract_status_and_active_manifest_freeze_exact_boundary() -> None:
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    current = (REPO_ROOT / "docs/spec/pietto-v0.9.md").read_text(encoding="utf-8")
    assert "Every selected declaration of the eight retained nominal kinds" in spec
    assert "Unknown, ambiguous, and blocked references keep raw attribution" in spec
    assert "exact nominal\ntarget identity, its exact declaration occurrence" in spec
    assert "unrelated same-spelling field diagnostic such as an `Other`" in spec
    assert "The parse result is the eleventh private validation root" in spec
    assert "It is not factory-origin attestation" in spec
    assert "No token, seal, digest, source reopening, or" in spec
    assert "reparse is introduced." in spec
    assert "Slice 11 adds private occurrence-safe declaration, import," in readme
    assert "Module attribution, dependency, origin, provenance, and lineage" in readme
    assert "## Status And Slice 16 Lifecycle" in plan
    assert "## Current Phase 54 Completion Status" in current
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE16_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "1f69c0316086a2236cee03a96cca95218fbd50fc"
    )
    assert active_gate2_manifest.PHASE54_SLICE12_HISTORICAL_ADDED_PATHS == {
        "docs/spec/phase54-slice12-semantic-fact-preservation-v1.md",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "tests/test_phase54_semantic_fact_preservation.py",
    }
    assert TEST_REL in active_gate2_manifest.MECHANICAL_READER_PATHS
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 46
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 51
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 53
    assert active_gate2_manifest.PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE == (
        "691db405a7e787adec5d7bd0498330b070bf6b75"
    )
    assert (
        len(active_gate2_manifest.PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
        == 64
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_DELETED_PATHS == set()


def test_private_carrier_enums_fields_and_sidecar_are_exact() -> None:
    assert module_attribution.__all__ == ()
    assert tuple(module_attribution.ProjectModuleReferenceRole) == (
        module_attribution.ProjectModuleReferenceRole.TYPE_ALIAS_BASE,
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
        module_attribution.ProjectModuleReferenceRole.SOURCE_SHAPE,
        module_attribution.ProjectModuleReferenceRole.RELATION_FROM,
        module_attribution.ProjectModuleReferenceRole.ROW_FIELD,
    )
    assert tuple(module_attribution.ProjectModuleDependencyKind) == (
        module_attribution.ProjectModuleDependencyKind.TYPE_REFERENCE,
        module_attribution.ProjectModuleDependencyKind.SOURCE_SHAPE_REFERENCE,
        module_attribution.ProjectModuleDependencyKind.RELATION_REFERENCE,
        module_attribution.ProjectModuleDependencyKind.ROW_FIELD_REFERENCE,
    )
    assert tuple(module_attribution.ProjectModuleRowFieldKind) == (
        module_attribution.ProjectModuleRowFieldKind.SHAPE_FIELD,
        module_attribution.ProjectModuleRowFieldKind.SOURCE_FIELD,
        module_attribution.ProjectModuleRowFieldKind.RELATION_OUTPUT,
    )
    assert tuple(module_attribution.ProjectModuleProjectionKind) == (
        module_attribution.ProjectModuleProjectionKind.DIRECT,
        module_attribution.ProjectModuleProjectionKind.RENAMED,
    )
    expected_fields = {
        module_attribution.ProjectDeclarationOccurrenceIdentity: (
            "identity",
            "module_position",
            "declaration_position",
        ),
        module_attribution.ProjectModuleImportOccurrenceIdentity: (
            "binding_identity",
            "target_module_path",
            "exported_name",
            "module_statement_position",
            "item_position",
        ),
        module_attribution.ProjectModuleFacadeOccurrenceIdentity: (
            "owning_module_path",
            "namespace",
            "declaration_kind",
            "exposed_name",
            "module_statement_position",
            "item_position",
        ),
        module_attribution.ProjectModuleReferenceOccurrenceIdentity: (
            "owner",
            "role",
            "member_position",
        ),
        module_attribution.ProjectModuleRowFieldIdentity: (
            "owner",
            "kind",
            "field_position",
            "name",
        ),
        module_attribution.ProjectModuleOriginPath: (
            "owning_module_path",
            "namespace",
            "declaration_kind",
            "local_name",
            "target_occurrence",
            "local_occurrence",
            "import_occurrence",
            "hops",
        ),
        module_attribution.ProjectModuleAttributionFactSet: (
            "binding_authority",
            "_authority",
            "declarations",
            "imports",
            "facades",
            "references",
            "origins",
            "reference_provenance",
            "module_dependencies",
            "dependencies",
            "source_field_origins",
            "row_lineages",
            "_origins_by_target",
            "_provenance_by_reference",
            "_dependencies_by_reference",
            "_source_origins_by_field",
            "_row_lineages_by_owner",
        ),
        module_attribution._ProjectModuleAttributionAuthority: (
            "parse_result",
            "selected_input_index",
            "trusted_source_snapshots",
            "binding_authority",
            "modules",
            "catalogs",
            "exports",
            "graph",
            "module_diagnostic_facts",
            "type_source_resolutions",
            "relation_resolutions",
            "declarations",
            "imports",
            "facades",
            "references",
            "origins",
            "reference_provenance",
            "module_dependencies",
            "dependencies",
            "source_field_origins",
            "row_lineages",
        ),
    }
    for carrier, names in expected_fields.items():
        assert carrier.__dataclass_params__.frozen
        assert tuple(item.name for item in fields(carrier)) == names
        assert all(item.kw_only for item in fields(carrier))
        assert "__dict__" not in carrier.__slots__
    authority_field = fields(module_attribution.ProjectModuleAttributionFactSet)[0]
    assert not authority_field.repr
    assert not authority_field.compare
    assert authority_field.hash is False
    for authority_field in fields(
        module_attribution._ProjectModuleAttributionAuthority
    ):
        assert not authority_field.repr
        assert not authority_field.compare
        assert authority_field.hash is False
    authority_roots = {
        "parse_result",
        "selected_input_index",
        "trusted_source_snapshots",
        "binding_authority",
        "modules",
        "catalogs",
        "exports",
        "graph",
        "module_diagnostic_facts",
        "type_source_resolutions",
        "relation_resolutions",
    }
    authority_products = {
        "declarations",
        "imports",
        "facades",
        "references",
        "origins",
        "reference_provenance",
        "module_dependencies",
        "dependencies",
        "source_field_origins",
        "row_lineages",
    }
    assert {
        item.name
        for item in fields(module_attribution._ProjectModuleAttributionAuthority)
        if item.init
    } == authority_roots
    assert {
        item.name
        for item in fields(module_attribution._ProjectModuleAttributionAuthority)
        if not item.init
    } == authority_products
    assert "_factory_seal" not in tuple(
        item.name
        for item in fields(module_attribution._ProjectModuleAttributionAuthority)
    )
    assert (
        "_factory_seal"
        not in module_attribution._ProjectModuleAttributionAuthority.__slots__
    )
    assert not any(
        "token" in item.name or "seal" in item.name
        for item in fields(module_attribution._ProjectModuleAttributionAuthority)
    )
    assert "parse_result" not in tuple(
        item.name for item in fields(ProjectSemanticResult)
    )


def test_declaration_occurrence_identity_excludes_ast_payload_from_semantic_equality(
    tmp_path: Path,
) -> None:
    _, first = _semantic_project(tmp_path / "first", {"main.pietto": "type A = Int\n"})
    _, second = _semantic_project(
        tmp_path / "second", {"main.pietto": "type A = Int\n"}
    )
    first_fact = _facts(first).declarations[0]
    second_fact = _facts(second).declarations[0]
    assert first_fact.occurrence.definition is not second_fact.occurrence.definition
    assert first_fact.identity == second_fact.identity
    assert first_fact == second_fact
    occurrence_field = next(
        item
        for item in fields(module_attribution.ProjectModuleDeclarationAttribution)
        if item.name == "occurrence"
    )
    assert not occurrence_field.compare and not occurrence_field.hash


def test_import_and_facade_occurrence_identities_preserve_positions_and_exact_names(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": "type Public = Text\nexport:\n    type Public\n",
        },
    )
    facts = _facts(semantic)
    assert facts._authority.parse_result is parse_result
    imported = facts.imports[0].identity
    facade = next(
        item.identity
        for item in facts.facades
        if item.identity.exposed_name == "Public"
    )
    assert imported.binding_identity.local_binding_name == "Local"
    assert imported.exported_name == "Public"
    assert imported.target_module_path == "b.pietto"
    assert (imported.module_statement_position, imported.item_position) == (0, 0)
    assert facade.owning_module_path == "b.pietto"
    assert facade.exposed_name == "Public"
    assert (facade.module_statement_position, facade.item_position) == (0, 0)


def test_reference_occurrence_identity_uses_owner_role_and_position_not_ast_value(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": "shape Row:\n    first: Int\n    second: Int\n"},
    )
    facts = _facts(semantic)
    first = _reference(
        facts,
        "main.pietto",
        "Row",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    )
    second = _reference(
        facts,
        "main.pietto",
        "Row",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
        position=1,
    )
    assert isinstance(first.site, TypeExpr)
    assert isinstance(second.site, TypeExpr)
    assert first.site.name == second.site.name == "Int"
    assert first.identity != second.identity
    site_field = next(
        item
        for item in fields(module_attribution.ProjectModuleReferenceAttribution)
        if item.name == "site"
    )
    assert not site_field.compare and not site_field.hash


def test_row_field_identity_distinguishes_shape_source_and_projection_occurrences(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"main.pietto": _simple_library()})
    facts = _facts(semantic)
    shape_field = facts.source_field_origins[0].shape_field
    source_field = facts.source_field_origins[0].source_field
    projection_field = _lineage(facts, "main.pietto", "projected").fields[0].field
    assert {shape_field.kind, source_field.kind, projection_field.kind} == {
        module_attribution.ProjectModuleRowFieldKind.SHAPE_FIELD,
        module_attribution.ProjectModuleRowFieldKind.SOURCE_FIELD,
        module_attribution.ProjectModuleRowFieldKind.RELATION_OUTPUT,
    }
    assert len({shape_field, source_field, projection_field}) == 3


def test_all_eight_declaration_kinds_receive_source_ordered_module_attribution(
    tmp_path: Path,
) -> None:
    source = (
        "type Email = Text\n"
        "enum Status:\n    active\n"
        "constraint valid(value: Text) -> Bool:\n    value == value\n"
        "derive normalized(value: Text) -> Text:\n    value\n"
        "shape Row:\n    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n    from rows\n    select:\n        id\n"
        "query reported:\n    from projected\n    select:\n        id\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    declarations = _facts(semantic).declarations
    assert tuple(item.identity.identity.declaration_kind for item in declarations) == (
        ProjectSymbolKind.TYPE_ALIAS,
        ProjectSymbolKind.ENUM,
        ProjectSymbolKind.CONSTRAINT,
        ProjectSymbolKind.DERIVE,
        ProjectSymbolKind.SHAPE,
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    )
    assert tuple(item.identity.declaration_position for item in declarations) == tuple(
        range(8)
    )


def test_all_six_import_export_kinds_preserve_local_binding_and_nominal_target(
    tmp_path: Path,
) -> None:
    consumer = (
        'import "z.pietto":\n'
        "    type Email as LocalEmail\n"
        "    enum Status as LocalStatus\n"
        "    shape Row as LocalRow\n"
        "    source rows as local_rows\n"
        "    table projected as local_projected\n"
        "    query reported as local_reported\n"
        "shape Uses:\n    email: LocalEmail\n    status: LocalStatus\n"
    )
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": consumer, "z.pietto": _all_kind_library()},
    )
    facts = _facts(semantic)
    assert tuple(
        item.identity.binding_identity.local_binding_name for item in facts.imports
    ) == (
        "LocalEmail",
        "LocalStatus",
        "LocalRow",
        "local_rows",
        "local_projected",
        "local_reported",
    )
    assert tuple(
        item.identity.binding_identity.declaration_kind for item in facts.imports
    ) == (
        ProjectSymbolKind.TYPE_ALIAS,
        ProjectSymbolKind.ENUM,
        ProjectSymbolKind.SHAPE,
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    )
    assert tuple(
        item.identity.declared_name
        for item in (
            path.target_occurrence
            for path in facts.origins
            if path.import_occurrence is not None
        )
    ) == (
        "Email",
        "Status",
        "Row",
        "rows",
        "projected",
        "reported",
    )


def test_local_declaration_origins_are_self_paths_without_facade_hops(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"main.pietto": "type A = Int\n"})
    facts = _facts(semantic)
    declaration = facts.declarations[0]
    origins = facts.find_origin_target(declaration.identity.identity)
    assert len(origins) == 1
    assert origins[0].local_occurrence == declaration.identity
    assert origins[0].import_occurrence is None
    assert origins[0].hops == ()


def test_direct_import_origin_retains_local_alias_direct_facade_and_nominal_owner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": "type Public = Text\nexport:\n    type Public\n",
        },
    )
    facts = _facts(semantic)
    origin = next(item for item in facts.origins if item.local_name == "Local")
    assert origin.owning_module_path == "a.pietto"
    assert origin.target_occurrence.identity.module_path == "b.pietto"
    assert origin.target_occurrence.identity.declared_name == "Public"
    assert len(origin.hops) == 1
    assert origin.hops[0].facade_occurrence.exposed_name == "Public"


def test_explicit_reexport_origin_retains_every_exact_import_and_facade_hop(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Base as Public\n'
                "export:\n    type Public\n"
            ),
            "c.pietto": "type Base = Text\nexport:\n    type Base\n",
        },
    )
    origin = next(
        item for item in _facts(semantic).origins if item.local_name == "Local"
    )
    assert tuple(
        hop.import_occurrence.binding_identity.owning_module_path for hop in origin.hops
    ) == (
        "a.pietto",
        "b.pietto",
    )
    assert tuple(hop.facade_occurrence.owning_module_path for hop in origin.hops) == (
        "b.pietto",
        "c.pietto",
    )
    assert origin.target_occurrence.identity.declared_name == "Base"


def test_same_nominal_target_through_distinct_aliases_retains_distinct_origin_paths(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    type Base as First\n    type Base as Second\n'
                "shape Uses:\n    first: First\n    second: Second\n"
            ),
            "z.pietto": "type Base = Text\nexport:\n    type Base\n",
        },
    )
    facts = _facts(semantic)
    target = _declaration(facts, "z.pietto", "Base").identity.identity
    routes = facts.find_origin_target(target)
    imported = tuple(route for route in routes if route.import_occurrence is not None)
    assert tuple(route.local_name for route in imported) == ("First", "Second")
    assert imported[0] != imported[1]


def test_origin_target_lookup_returns_complete_deterministic_tuple(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "z.pietto":\n    type Base as A\n',
            "b.pietto": 'import "z.pietto":\n    type Base as B\n',
            "z.pietto": "type Base = Text\nexport:\n    type Base\n",
        },
    )
    facts = _facts(semantic)
    target = _declaration(facts, "z.pietto", "Base").identity.identity
    routes = facts.find_origin_target(target)
    assert type(routes) is tuple
    assert tuple(route.owning_module_path for route in routes) == (
        "z.pietto",
        "a.pietto",
        "b.pietto",
    )
    assert facts.find_origin_target(target) is routes


def test_module_import_dependencies_retain_every_graph_evidence_occurrence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    type Base as First\n    type Base as Second\n'
                "shape Uses:\n    first: First\n    second: Second\n"
            ),
            "z.pietto": "type Base = Text\nexport:\n    type Base\n",
        },
    )
    facts = _facts(semantic)
    assert semantic.module_graph is not None
    assert len(facts.imports) == 2
    assert len(facts.module_dependencies) == 2
    assert tuple(
        (
            item.import_occurrence,
            item.origin,
            item.target,
        )
        for item in facts.module_dependencies
    ) == tuple(
        (
            module_attribution._import_identity(edge.request),
            edge.origin.identity,
            edge.target.identity,
        )
        for edge in semantic.module_graph.evidence_edges
    )
    assert tuple(
        item.import_occurrence.binding_identity.local_binding_name
        for item in facts.module_dependencies
    ) == ("First", "Second")
    assert tuple(
        (item.origin.path, item.target.path) for item in facts.module_dependencies
    ) == (
        ("a.pietto", "z.pietto"),
        ("a.pietto", "z.pietto"),
    )

    _, unresolved_semantic = _semantic_project(
        tmp_path / "unresolved",
        {"main.pietto": 'import "missing.pietto":\n    shape Missing\n'},
    )
    unresolved_facts = _facts(unresolved_semantic)
    assert len(unresolved_facts.imports) == 1
    assert unresolved_facts.module_dependencies == ()
    with pytest.raises(ValueError, match="ordered binding authority requests"):
        replace(unresolved_facts, imports=())

    _, empty_target_semantic = _semantic_project(
        tmp_path / "empty-target",
        {
            "main.pietto": 'import "empty.pietto":\n    shape Missing\n',
            "empty.pietto": "",
        },
    )
    empty_target_facts = _facts(empty_target_semantic)
    assert len(empty_target_facts.imports) == 1
    assert len(empty_target_facts.module_dependencies) == 1
    assert empty_target_facts.declarations == ()


def test_module_dependency_diamond_retains_all_direct_edges_without_best_path(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    shape B\n'
                'import "c.pietto":\n    shape C\n'
                "shape A:\n    left: B\n    right: C\n"
            ),
            "b.pietto": (
                'import "d.pietto":\n    shape D\n'
                "shape B:\n    value: D\nexport:\n    shape B\n"
            ),
            "c.pietto": (
                'import "d.pietto":\n    shape D\n'
                "shape C:\n    value: D\nexport:\n    shape C\n"
            ),
            "d.pietto": "shape D:\n    id: Int\nexport:\n    shape D\n",
        },
    )
    edges = tuple(
        (item.origin.path, item.target.path)
        for item in _facts(semantic).module_dependencies
    )
    assert edges == (
        ("a.pietto", "b.pietto"),
        ("a.pietto", "c.pietto"),
        ("b.pietto", "d.pietto"),
        ("c.pietto", "d.pietto"),
    )


def test_module_cycle_retains_raw_attribution_and_dependencies_without_resolved_provenance(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    shape B\n'
                "shape A:\n    value: B\nexport:\n    shape A\n"
            ),
            "b.pietto": (
                'import "a.pietto":\n    shape A\n'
                "shape B:\n    value: A\nexport:\n    shape B\n"
            ),
        },
    )
    facts = _facts(semantic)
    assert len(facts.declarations) == 2
    assert len(facts.imports) == 2
    assert len(facts.module_dependencies) == 2
    assert len(facts.references) == 2
    assert facts.reference_provenance == ()
    assert facts.dependencies == ()
    assert facts.row_lineages == ()


def test_builtin_type_reference_has_attribution_and_builtin_terminal_without_nominal_dependency(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": "shape Row:\n    id: Int\n"},
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "main.pietto",
        "Row",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    ).identity
    result = facts.find_reference_provenance(reference)
    assert len(result) == 1
    path = result[0].paths[0]
    assert path.hops == ()
    assert path.terminal_builtin == "Int"
    assert path.terminal_reference == reference
    assert path.terminal_target is None
    assert facts.find_reference_dependencies(reference) == ()


def test_local_type_alias_chain_retains_every_reference_and_nominal_hop(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "type Base = Int\n"
                "type Middle = Base\n"
                "type Outer = Middle\n"
                "shape Uses:\n    value: Outer\n"
            )
        },
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "main.pietto",
        "Uses",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    ).identity
    path = facts.find_reference_provenance(reference)[0].paths[0]
    assert tuple(hop.reference.owner.identity.declared_name for hop in path.hops) == (
        "Uses",
        "Outer",
        "Middle",
    )
    assert tuple(hop.target.identity.declared_name for hop in path.hops) == (
        "Outer",
        "Middle",
        "Base",
    )
    assert path.terminal_builtin == "Int"
    assert path.terminal_reference is not None
    assert path.terminal_reference.owner.identity.declared_name == "Base"
    assert {
        item.reference.owner.identity.declared_name for item in facts.dependencies
    } == {"Uses", "Outer", "Middle"}


def test_cross_module_alias_chain_retains_local_alias_and_canonical_target(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Remote\n'
                "type Local = Remote\n"
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                "type Base = Text\ntype Public = Base\nexport:\n    type Public\n"
            ),
        },
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "a.pietto",
        "Uses",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    ).identity
    path = facts.find_reference_provenance(reference)[0].paths[0]
    assert tuple(hop.target.identity.declared_name for hop in path.hops) == (
        "Local",
        "Public",
        "Base",
    )
    assert path.hops[1].origin.local_name == "Remote"
    assert path.hops[1].origin.target_occurrence.identity.module_path == "b.pietto"
    assert path.terminal_builtin == "Text"


def test_reexported_alias_chain_retains_each_facade_hop_and_nominal_occurrence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Alias as Public\n'
                "export:\n    type Public\n"
            ),
            "c.pietto": (
                "type Base = UUID\ntype Alias = Base\nexport:\n    type Alias\n"
            ),
        },
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "a.pietto",
        "Uses",
        module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE,
    ).identity
    path = facts.find_reference_provenance(reference)[0].paths[0]
    assert tuple(hop.target.identity.declared_name for hop in path.hops) == (
        "Alias",
        "Base",
    )
    assert tuple(
        hop.facade_occurrence.owning_module_path for hop in path.hops[0].origin.hops
    ) == ("b.pietto", "c.pietto")
    assert path.terminal_builtin == "UUID"
    assert path.terminal_reference is not None
    assert path.terminal_reference.owner.identity.declared_name == "Base"


def test_shape_field_reference_occurrences_preserve_order_and_duplicate_spelling(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": "shape Row:\n    first: Int\n    second: Int\n"},
    )
    references = tuple(
        item
        for item in _facts(semantic).references
        if item.identity.role
        is module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE
    )
    assert tuple(item.identity.member_position for item in references) == (0, 1)
    assert all(isinstance(item.site, TypeExpr) for item in references)
    assert tuple(
        item.site.name for item in references if isinstance(item.site, TypeExpr)
    ) == (
        "Int",
        "Int",
    )
    assert references[0].identity != references[1].identity


def test_source_shape_provenance_retains_source_occurrence_shape_occurrence_and_route(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    shape Row as RemoteRow\n'
                'source rows: RemoteRow is postgres.table("rows")\n'
            ),
            "b.pietto": "shape Row:\n    id: Int\nexport:\n    shape Row\n",
        },
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "a.pietto",
        "rows",
        module_attribution.ProjectModuleReferenceRole.SOURCE_SHAPE,
    ).identity
    path = facts.find_reference_provenance(reference)[0].paths[0]
    assert path.reference.owner.identity.declared_name == "rows"
    assert path.terminal_target is not None
    assert path.terminal_target.identity.declared_name == "Row"
    assert path.terminal_target.identity.module_path == "b.pietto"
    assert path.hops[0].origin.local_name == "RemoteRow"


def test_relation_from_dependency_retains_immediate_local_symbol_and_target_occurrence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"main.pietto": _simple_library()})
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "main.pietto",
        "projected",
        module_attribution.ProjectModuleReferenceRole.RELATION_FROM,
    ).identity
    dependencies = facts.find_reference_dependencies(reference)
    assert len(dependencies) == 1
    dependency = dependencies[0]
    assert (
        dependency.kind
        is module_attribution.ProjectModuleDependencyKind.RELATION_REFERENCE
    )
    assert dependency.target_declaration is not None
    assert dependency.target_declaration.identity.declared_name == "rows"
    assert dependency.origin_path is not None
    assert dependency.origin_path.local_name == "rows"


def test_imported_source_table_query_dependencies_preserve_distinct_kinds_and_aliases(
    tmp_path: Path,
) -> None:
    consumer = (
        'import "z.pietto":\n'
        "    source rows as InputSource\n"
        "    table projected as InputTable\n"
        "    query reported as InputQuery\n"
        "query from_source:\n    from InputSource\n    select:\n        id\n"
        "query from_table:\n    from InputTable\n    select:\n        id\n"
        "query from_query:\n    from InputQuery\n    select:\n        id\n"
    )
    library = _simple_library() + (
        "export:\n    shape Row\n    source rows\n    table projected\n    query reported\n"
    )
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": consumer, "z.pietto": library},
    )
    facts = _facts(semantic)
    results = []
    for owner in ("from_source", "from_table", "from_query"):
        reference = _reference(
            facts,
            "a.pietto",
            owner,
            module_attribution.ProjectModuleReferenceRole.RELATION_FROM,
        ).identity
        dependency = facts.find_reference_dependencies(reference)[0]
        assert dependency.target_declaration is not None
        assert dependency.origin_path is not None
        results.append(
            (
                dependency.origin_path.local_name,
                dependency.target_declaration.identity.declaration_kind,
            )
        )
    assert tuple(results) == (
        ("InputSource", ProjectSymbolKind.SOURCE),
        ("InputTable", ProjectSymbolKind.TABLE),
        ("InputQuery", ProjectSymbolKind.QUERY),
    )


def test_reexported_relation_dependency_retains_direct_facade_and_original_target(
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
                'import "c.pietto":\n    table base as Public\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "table base:\n    from rows\n    select:\n        id\n"
                "export:\n    table base\n"
            ),
        },
    )
    facts = _facts(semantic)
    reference = _reference(
        facts,
        "a.pietto",
        "result",
        module_attribution.ProjectModuleReferenceRole.RELATION_FROM,
    ).identity
    dependency = facts.find_reference_dependencies(reference)[0]
    assert dependency.target_declaration is not None
    assert dependency.origin_path is not None
    assert dependency.target_declaration.identity.module_path == "c.pietto"
    assert dependency.target_declaration.identity.declared_name == "base"
    assert dependency.origin_path.local_name == "Local"
    assert tuple(
        hop.facade_occurrence.owning_module_path for hop in dependency.origin_path.hops
    ) == ("b.pietto", "c.pietto")


def test_source_field_origins_preserve_shape_field_position_order_and_field_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    shape Remote as LocalRow\n'
                'source rows: LocalRow is postgres.table("rows")\n'
            ),
            "z.pietto": (
                "shape Remote:\n    id: Int\n    name: Text\n"
                "export:\n    shape Remote\n"
            ),
        },
    )
    origins = _facts(semantic).source_field_origins
    assert tuple(item.source_field.field_position for item in origins) == (0, 1)
    assert tuple(item.source_field.name for item in origins) == ("id", "name")
    assert tuple(item.shape_field.field_position for item in origins) == (0, 1)
    assert tuple(item.shape_field.name for item in origins) == ("id", "name")
    assert all(
        item.source_field.owner.identity.declared_name == "rows" for item in origins
    )
    assert all(
        item.shape_field.owner.identity.declared_name == "Remote" for item in origins
    )


def test_direct_bare_qualified_and_renamed_lineage_preserves_select_order(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"main.pietto": _simple_library()})
    lineage = _lineage(_facts(semantic), "main.pietto", "projected")
    assert lineage.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert tuple(item.field.name for item in lineage.fields) == ("id", "label")
    assert tuple(item.field.field_position for item in lineage.fields) == (0, 1)
    assert tuple(item.paths[0].hops[0].projection_kind for item in lineage.fields) == (
        module_attribution.ProjectModuleProjectionKind.DIRECT,
        module_attribution.ProjectModuleProjectionKind.RENAMED,
    )
    assert tuple(item.paths[0].root_field.name for item in lineage.fields) == (
        "id",
        "name",
    )


def test_imported_relation_alias_lineage_uses_only_consumer_local_qualifier_route(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    table projected as Input\n'
                "query result:\n"
                "    from Input\n"
                "    select:\n"
                "        Input.id\n"
                "        Input.label\n"
            ),
            "z.pietto": _simple_library() + "export:\n    table projected\n",
        },
    )
    lineage = _lineage(_facts(semantic), "a.pietto", "result")
    assert tuple(item.field.name for item in lineage.fields) == ("id", "label")
    first_hops = lineage.fields[0].paths[0].hops
    assert first_hops[0].relation_origin.local_name == "Input"
    assert first_hops[0].relation_origin.owning_module_path == "a.pietto"
    assert first_hops[0].relation_origin.target_occurrence.identity.declared_name == (
        "projected"
    )
    assert all(hop.relation_origin.local_name != "z.pietto" for hop in first_hops)


def test_local_multi_hop_lineage_preserves_every_immediate_projection_hop(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"main.pietto": _simple_library()})
    lineage = _lineage(_facts(semantic), "main.pietto", "reported")
    id_path = lineage.fields[0].paths[0]
    label_path = lineage.fields[1].paths[0]
    assert tuple(
        hop.output_field.owner.identity.declared_name for hop in id_path.hops
    ) == ("reported", "projected")
    assert tuple(
        hop.upstream_field.owner.identity.declared_name for hop in id_path.hops
    ) == ("projected", "rows")
    assert id_path.root_field.name == "id"
    assert tuple(hop.projection_kind for hop in label_path.hops) == (
        module_attribution.ProjectModuleProjectionKind.DIRECT,
        module_attribution.ProjectModuleProjectionKind.RENAMED,
    )
    assert label_path.root_field.name == "name"


def test_cross_module_multi_hop_lineage_preserves_binding_and_facade_evidence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    table projected as Input\n'
                "query local:\n    from Input\n    select:\n        id\n"
                "query final:\n    from local\n    select:\n        id\n"
            ),
            "z.pietto": _simple_library() + "export:\n    table projected\n",
        },
    )
    path = _lineage(_facts(semantic), "a.pietto", "final").fields[0].paths[0]
    assert tuple(
        hop.output_field.owner.identity.declared_name for hop in path.hops
    ) == ("final", "local", "projected")
    imported_hop = path.hops[1]
    assert imported_hop.relation_origin.local_name == "Input"
    assert len(imported_hop.relation_origin.hops) == 1
    assert (
        imported_hop.relation_origin.hops[0].facade_occurrence.owning_module_path
        == "z.pietto"
    )
    assert path.root_field.owner.identity.module_path == "z.pietto"


def test_explicit_reexport_row_lineage_reaches_original_source_without_identity_rewrite(
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
                'import "c.pietto":\n    table base as Public\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "table base:\n    from rows\n    select:\n        id\n"
                "export:\n    table base\n"
            ),
        },
    )
    path = _lineage(_facts(semantic), "a.pietto", "result").fields[0].paths[0]
    assert path.root_field.owner.identity.module_path == "c.pietto"
    assert path.root_field.owner.identity.declared_name == "rows"
    first = path.hops[0]
    assert first.relation_origin.local_name == "Local"
    assert first.relation_origin.target_occurrence.identity.declared_name == "base"
    assert tuple(
        hop.facade_occurrence.owning_module_path for hop in first.relation_origin.hops
    ) == ("b.pietto", "c.pietto")


def test_same_spelling_cross_module_relations_and_fields_never_cross_wire(
    tmp_path: Path,
) -> None:
    library = (
        "shape Row:\n    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table shared:\n    from rows\n    select:\n        id\n"
        "export:\n    table shared\n"
    )
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    table shared as Left\n'
                'import "c.pietto":\n    table shared as Right\n'
                "query left_result:\n    from Left\n    select:\n        id\n"
                "query right_result:\n    from Right\n    select:\n        id\n"
            ),
            "b.pietto": library,
            "c.pietto": library,
        },
    )
    facts = _facts(semantic)
    left = _lineage(facts, "a.pietto", "left_result").fields[0].paths[0]
    right = _lineage(facts, "a.pietto", "right_result").fields[0].paths[0]
    assert left.root_field.owner.identity.module_path == "b.pietto"
    assert right.root_field.owner.identity.module_path == "c.pietto"
    assert left.root_field.name == right.root_field.name == "id"
    assert left.root_field != right.root_field


def test_multiple_outputs_sharing_one_source_root_remain_distinct_paths(
    tmp_path: Path,
) -> None:
    source = (
        "shape Row:\n    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "query duplicated:\n"
        "    from rows\n"
        "    select:\n"
        "        first = id\n"
        "        second = id\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    lineage = _lineage(_facts(semantic), "main.pietto", "duplicated")
    assert tuple(item.field.name for item in lineage.fields) == ("first", "second")
    assert (
        lineage.fields[0].paths[0].root_field == lineage.fields[1].paths[0].root_field
    )
    assert lineage.fields[0].paths[0] != lineage.fields[1].paths[0]
    assert (
        lineage.fields[0].paths[0].hops[0].reference
        != lineage.fields[1].paths[0].hops[0].reference
    )


def test_same_target_through_distinct_relation_aliases_retains_two_lineage_routes(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    table base as First\n    table base as Second\n'
                "query first_result:\n    from First\n    select:\n        id\n"
                "query second_result:\n    from Second\n    select:\n        id\n"
            ),
            "z.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row is postgres.table("rows")\n'
                "table base:\n    from rows\n    select:\n        id\n"
                "export:\n    table base\n"
            ),
        },
    )
    facts = _facts(semantic)
    first = _lineage(facts, "a.pietto", "first_result").fields[0].paths[0]
    second = _lineage(facts, "a.pietto", "second_result").fields[0].paths[0]
    assert first.root_field == second.root_field
    assert first.hops[0].relation_origin.local_name == "First"
    assert second.hops[0].relation_origin.local_name == "Second"
    assert first != second


def test_definition_and_selected_module_permutations_change_only_explicit_order_evidence(
    tmp_path: Path,
) -> None:
    sources_ab = {
        "a.pietto": "type A = Int\ntype B = Text\n",
        "z.pietto": "type Z = UUID\n",
    }
    sources_ba = {
        "z.pietto": "type Z = UUID\n",
        "a.pietto": "type B = Text\ntype A = Int\n",
    }
    _, first_semantic = _semantic_project(tmp_path / "first", sources_ab)
    _, second_semantic = _semantic_project(tmp_path / "second", sources_ba)
    first = _facts(first_semantic)
    second = _facts(second_semantic)
    assert tuple(item.identity.identity.module_path for item in first.declarations) == (
        "a.pietto",
        "a.pietto",
        "z.pietto",
    )
    assert tuple(
        item.identity.identity.module_path for item in second.declarations
    ) == (
        "a.pietto",
        "a.pietto",
        "z.pietto",
    )
    first_positions = {
        item.identity.identity.declared_name: item.identity.declaration_position
        for item in first.declarations
    }
    second_positions = {
        item.identity.identity.declared_name: item.identity.declaration_position
        for item in second.declarations
    }
    assert first_positions == {"A": 0, "B": 1, "Z": 0}
    assert second_positions == {"B": 0, "A": 1, "Z": 0}
    assert {
        (
            item.identity.identity.module_path,
            item.identity.identity.declared_name,
            item.identity.identity.declaration_kind,
        )
        for item in first.declarations
    } == {
        (
            item.identity.identity.module_path,
            item.identity.identity.declared_name,
            item.identity.identity.declaration_kind,
        )
        for item in second.declarations
    }


def test_unknown_ambiguous_and_blocked_references_have_raw_attribution_but_no_provenance(
    tmp_path: Path,
) -> None:
    cases = {
        "unknown": {"main.pietto": "shape Uses:\n    value: Missing\n"},
        "ambiguous": {
            "main.pietto": (
                "type Shared = Int\n"
                "enum Shared:\n    active\n"
                "shape Uses:\n    value: Shared\n"
            )
        },
        "blocked": {
            "a.pietto": (
                'import "b.pietto":\n    shape B\n'
                "shape A:\n    value: B\nexport:\n    shape A\n"
            ),
            "b.pietto": (
                'import "a.pietto":\n    shape A\n'
                "shape B:\n    value: A\nexport:\n    shape B\n"
            ),
        },
    }
    for name, sources in cases.items():
        _, semantic = _semantic_project(tmp_path / name, sources)
        facts = _facts(semantic)
        assert facts.references
        blocked_references = tuple(
            item.identity
            for item in facts.references
            if name == "blocked" or item.identity.owner.identity.declared_name == "Uses"
        )
        assert blocked_references
        assert all(
            facts.find_reference_provenance(reference) == ()
            for reference in blocked_references
        )
        assert all(
            facts.find_reference_dependencies(reference) == ()
            for reference in blocked_references
        )

    causal_parse_result, causal_semantic = _semantic_project(
        tmp_path / "exact-imported-relation-causal-root",
        {
            "a.pietto": (
                'import "b.pietto":\n    source Shared as Remote\n'
                "query Uses:\n    from Remote\n    select:\n        id\n"
            ),
            "b.pietto": (
                "shape Row:\n    id: Int\n"
                'source Shared: Row is postgres.table("shared")\n'
                'source Rows: Row is postgres.table("rows")\n'
                "table Shared:\n    from Rows\n    select:\n        id\n"
                "table Other:\n    from Rows\n    select:\n        Shared\n"
                "export:\n    source Shared\n"
            ),
        },
    )
    causal_facts = _facts(causal_semantic)
    remote_import = next(
        item
        for item in causal_facts.imports
        if item.identity.binding_identity.owning_module_path == "a.pietto"
        and item.identity.binding_identity.local_binding_name == "Remote"
    )
    assert remote_import.request.identity is remote_import.identity.binding_identity
    relation_reference = _reference(
        causal_facts,
        "a.pietto",
        "Uses",
        module_attribution.ProjectModuleReferenceRole.RELATION_FROM,
    ).identity
    assert causal_facts.find_reference_provenance(relation_reference) == ()
    assert causal_facts.find_reference_dependencies(relation_reference) == ()
    remote_origins = tuple(
        origin
        for origin in causal_facts.origins
        if origin.owning_module_path == "a.pietto" and origin.local_name == "Remote"
    )
    assert len(remote_origins) == 1
    assert remote_origins[0].import_occurrence == remote_import.identity
    assert remote_origins[0].target_occurrence.identity.module_path == "b.pietto"
    assert remote_origins[0].target_occurrence.identity.declared_name == "Shared"
    root_identity = remote_origins[0].target_occurrence.identity
    assert root_identity.declaration_kind is ProjectSymbolKind.SOURCE
    blocked_lineage = _lineage(causal_facts, "a.pietto", "Uses")
    assert blocked_lineage.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert (
        blocked_lineage.reason
        is ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
    )
    assert blocked_lineage.fields == ()

    relation_set = causal_semantic.module_relation_resolutions
    assert relation_set is not None
    target_environment = next(
        environment
        for environment in relation_set.environments
        if environment.module.path == "b.pietto"
    )
    importer_environment = next(
        environment
        for environment in relation_set.environments
        if environment.module.path == "a.pietto"
    )
    ambiguity = next(
        issue
        for issue in target_environment.issues
        if issue.diagnostic is not None and issue.diagnostic.code == "PIE-S2001"
    )
    unrelated = next(
        issue
        for issue in target_environment.issues
        if issue.diagnostic is not None and issue.diagnostic.code == "PIE-S2102"
    )
    importer_blocker = next(
        issue
        for issue in importer_environment.issues
        if issue.status
        is relation_resolution.ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED
        and issue.local_name == "Remote"
    )
    root = ambiguity.diagnostic
    assert root is not None
    assert any(root is diagnostic for diagnostic in relation_set.diagnostics)
    assert len(importer_blocker.occurrences) == 1
    assert importer_blocker.occurrences[0].identity is root_identity
    assert importer_blocker.suppressing_diagnostics == (root,)
    assert importer_blocker.suppressing_diagnostics[0] is root
    assert unrelated.diagnostic is not root
    assert all(
        diagnostic is not unrelated.diagnostic
        for diagnostic in importer_blocker.suppressing_diagnostics
    )

    _, equal_root_semantic = _semantic_project(
        tmp_path / "equal-distinct-imported-type-roots",
        {
            "a.pietto": (
                'import "b.pietto":\n'
                "    shape Shared as Alpha\n"
                "    shape Shared as Beta\n"
                "shape Input:\n"
                "    first: Alpha\n"
                "    second: Beta\n"
                'source rows: Input is postgres.table("rows")\n'
            ),
            "b.pietto": (
                "shape Physical:\n"
                "    id: Int\n"
                'source Shared: Physical is postgres.table("shared")\n'
                "export:\n"
                "    source Shared\n"
            ),
        },
    )
    equal_root_facts = _facts(equal_root_semantic)
    assert tuple(
        item.identity.binding_identity.local_binding_name
        for item in equal_root_facts.imports
        if item.identity.binding_identity.owning_module_path == "a.pietto"
    ) == ("Alpha", "Beta")
    blocked_type_references = tuple(
        item.identity
        for item in equal_root_facts.references
        if item.identity.owner.identity.module_path == "a.pietto"
        and item.identity.owner.identity.declared_name == "Input"
        and item.identity.role
        is module_attribution.ProjectModuleReferenceRole.SHAPE_FIELD_TYPE
    )
    assert len(blocked_type_references) == 2
    assert all(
        equal_root_facts.find_reference_provenance(reference) == ()
        for reference in blocked_type_references
    )
    assert all(
        equal_root_facts.find_reference_dependencies(reference) == ()
        for reference in blocked_type_references
    )
    assert equal_root_semantic.module_diagnostic_facts is not None
    equal_root_diagnostic_facts = tuple(
        fact
        for fact in equal_root_semantic.module_diagnostic_facts.facts
        if fact.diagnostic.code == "PIE-S2707"
    )
    assert len(equal_root_diagnostic_facts) == 2
    equal_roots = tuple(fact.diagnostic for fact in equal_root_diagnostic_facts)
    assert equal_roots[0] == equal_roots[1]
    assert equal_roots[0] is not equal_roots[1]
    equal_roots_by_local_name = {
        fact.binding_issues[0].request.identity.local_binding_name: fact.diagnostic
        for fact in equal_root_diagnostic_facts
    }
    assert equal_root_semantic.module_relation_resolutions is not None
    equal_root_environment = next(
        environment
        for environment in (
            equal_root_semantic.module_relation_resolutions.environments
        )
        if environment.module.path == "a.pietto"
    )
    equal_root_blockers = tuple(
        issue
        for issue in equal_root_environment.issues
        if issue.status
        is relation_resolution.ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED
        and issue.local_name == "rows"
    )
    assert tuple(
        tuple(issue.local_name for issue in blocker.type_source_issues)
        for blocker in equal_root_blockers
    ) == (("Alpha",), ("Beta",))
    for blocker, local_name in zip(
        equal_root_blockers,
        ("Alpha", "Beta"),
        strict=True,
    ):
        assert len(blocker.suppressing_diagnostics) == 1
        assert (
            blocker.suppressing_diagnostics[0] is equal_roots_by_local_name[local_name]
        )

    foreign_root = replace(root)
    assert foreign_root == root
    assert foreign_root is not root
    foreign_blocker = replace(
        importer_blocker,
        suppressing_diagnostics=(foreign_root,),
    )
    foreign_importer_environment = replace(
        importer_environment,
        issues=tuple(
            foreign_blocker if issue is importer_blocker else issue
            for issue in importer_environment.issues
        ),
    )
    foreign_relation_set = replace(
        relation_set,
        environments=tuple(
            foreign_importer_environment
            if environment is importer_environment
            else environment
            for environment in relation_set.environments
        ),
        issues=tuple(
            foreign_blocker if issue is importer_blocker else issue
            for issue in relation_set.issues
        ),
    )
    assert foreign_relation_set == relation_set
    assert foreign_relation_set.diagnostics is relation_set.diagnostics
    assert causal_semantic.selected_input_index is not None
    assert causal_semantic.module_catalogs is not None
    assert causal_semantic.module_exports is not None
    assert causal_semantic.module_bindings is not None
    assert causal_semantic.module_graph is not None
    assert causal_semantic.module_diagnostic_facts is not None
    assert causal_semantic.module_type_source_resolutions is not None
    with pytest.raises(ValueError, match="exact current roots"):
        module_attribution._build_project_module_attribution_fact_set(
            causal_parse_result,
            causal_parse_result.modules,
            causal_semantic.selected_input_index,
            causal_semantic.trusted_source_snapshots,
            causal_semantic.module_catalogs,
            causal_semantic.module_exports,
            causal_semantic.module_bindings,
            causal_semantic.module_graph,
            causal_semantic.module_diagnostic_facts,
            causal_semantic.module_type_source_resolutions,
            foreign_relation_set,
        )


def test_local_relation_cycle_has_empty_lineage_for_every_blocked_member(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "query first:\n    from second\n    select:\n        id\n"
                "query second:\n    from first\n    select:\n        id\n"
            )
        },
    )
    facts = _facts(semantic)
    for owner in ("first", "second"):
        lineage = _lineage(facts, "main.pietto", owner)
        assert lineage.status is ProjectRelationRowSchemaStatus.BLOCKED
        assert lineage.reason is ProjectRelationRowSchemaReason.CYCLE_BLOCKED
        assert lineage.fields == ()


def test_unknown_upstream_and_duplicate_output_publish_empty_nonconcrete_lineage(
    tmp_path: Path,
) -> None:
    source = (
        'source unknown is postgres.table("unknown")\n'
        "shape Row:\n    id: Int\n    name: Text\n"
        'source rows: Row is postgres.table("rows")\n'
        "query unknown_child:\n    from unknown\n    select:\n        id\n"
        "query duplicate:\n"
        "    from rows\n"
        "    select:\n"
        "        value = id\n"
        "        value = name\n"
    )
    _, semantic = _semantic_project(tmp_path, {"main.pietto": source})
    facts = _facts(semantic)
    unknown = _lineage(facts, "main.pietto", "unknown_child")
    duplicate = _lineage(facts, "main.pietto", "duplicate")
    assert (unknown.status, unknown.reason, unknown.fields) == (
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        (),
    )
    assert (duplicate.status, duplicate.reason, duplicate.fields) == (
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        (),
    )


def test_computed_let_grouped_aggregate_and_window_rows_remain_outside_slice11_lineage(
    tmp_path: Path,
) -> None:
    prefix = (
        "shape Row:\n    id: Int not null\n    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    cases = {
        "computed": (
            "query result:\n    from rows\n    select:\n        total = id + 1\n"
        ),
        "let": (
            "query result:\n"
            "    from rows\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        total\n"
        ),
        "grouped": (
            "query result:\n"
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        total = sum(amount)\n"
        ),
        "window": (
            "query result:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        position = row_number() window:\n"
            "            order by:\n"
            "                id\n"
        ),
    }
    for name, query in cases.items():
        _, semantic = _semantic_project(
            tmp_path / name,
            {"main.pietto": prefix + query},
        )
        lineage = _lineage(_facts(semantic), "main.pietto", "result")
        assert lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE
        assert lineage.fields == ()


def test_fact_set_lookups_are_complete_tuple_backed_immutable_and_no_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "origins",
        {
            "a.pietto": (
                'import "z.pietto":\n    type Base as First\n    type Base as Second\n'
                "shape Uses:\n    first: First\n    second: Second\n"
            ),
            "z.pietto": (
                "type Base = Text\n"
                "type Other = Int\n"
                "export:\n"
                "    type Base\n"
                "    type Other\n"
            ),
        },
    )
    facts = _facts(semantic)
    target = _declaration(facts, "z.pietto", "Base").identity.identity
    origins = facts.find_origin_target(target)
    assert type(origins) is tuple
    assert tuple(item.local_name for item in origins) == ("Base", "First", "Second")
    assert isinstance(facts._origins_by_target, MappingProxyType)
    assert isinstance(facts._provenance_by_reference, MappingProxyType)
    assert isinstance(facts._dependencies_by_reference, MappingProxyType)
    assert isinstance(facts._source_origins_by_field, MappingProxyType)
    assert isinstance(facts._row_lineages_by_owner, MappingProxyType)
    with pytest.raises(TypeError):
        facts._origins_by_target[target] = ()  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        facts.origins = ()  # type: ignore[misc]
    with pytest.raises(ValueError, match="must not repeat exact facts"):
        replace(facts, origins=(origins[0], origins[0]))

    imported_origin = next(item for item in origins if item.local_name == "First")
    other = _declaration(facts, "z.pietto", "Other").identity
    forged_hop = replace(
        imported_origin.hops[0],
        target_identity=other.identity,
    )
    forged_origin = replace(
        imported_origin,
        target_occurrence=other,
        hops=(forged_hop,),
    )
    with pytest.raises(ValueError, match="retained facade attribution"):
        replace(facts, origins=(forged_origin,))
    with pytest.raises(ValueError, match="exactly match retained paths"):
        replace(facts, dependencies=())
    with pytest.raises(ValueError, match="Module dependencies must exactly match"):
        replace(facts, module_dependencies=())
    with pytest.raises(ValueError, match="ordered binding authority requests"):
        replace(
            facts,
            imports=tuple(reversed(facts.imports)),
            module_dependencies=tuple(reversed(facts.module_dependencies)),
        )
    canonical_fields = (
        "declarations",
        "imports",
        "facades",
        "references",
        "origins",
        "reference_provenance",
        "module_dependencies",
        "dependencies",
        "source_field_origins",
        "row_lineages",
    )
    for field_name in canonical_fields:
        values = getattr(facts, field_name)
        if len(values) > 1:
            with pytest.raises(ValueError):
                replace(facts, **{field_name: tuple(reversed(values))})
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            facts,
            declarations=(),
            facades=(),
            references=(),
            origins=(),
            reference_provenance=(),
            dependencies=(),
            source_field_origins=(),
            row_lineages=(),
        )
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            facts,
            declarations=(replace(facts.declarations[0]), *facts.declarations[1:]),
        )
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            facts,
            imports=(replace(facts.imports[0]), *facts.imports[1:]),
        )
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            facts,
            module_dependencies=(
                replace(facts.module_dependencies[0]),
                *facts.module_dependencies[1:],
            ),
        )

    _, foreign_semantic = _semantic_project(
        tmp_path / "foreign-authority",
        {
            "a.pietto": (
                'import "z.pietto":\n    type Base as First\n    type Base as Second\n'
                "shape Uses:\n    first: First\n    second: Second\n"
            ),
            "z.pietto": (
                "type Base = Text\n"
                "type Other = Int\n"
                "export:\n"
                "    type Base\n"
                "    type Other\n"
            ),
        },
    )
    assert foreign_semantic.module_bindings is not None
    with pytest.raises(ValueError, match="exact binding authority"):
        replace(facts, binding_authority=foreign_semantic.module_bindings)
    foreign_facts = _facts(foreign_semantic)
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            facts,
            binding_authority=foreign_facts.binding_authority,
            _authority=foreign_facts._authority,
            imports=foreign_facts.imports,
            module_dependencies=foreign_facts.module_dependencies,
        )

    rebuilt_authority = replace(facts._authority)
    assert rebuilt_authority is not facts._authority
    for field_name in canonical_fields:
        assert getattr(rebuilt_authority, field_name) == getattr(
            facts._authority, field_name
        )
    rebuilt_facts = replace(
        facts,
        _authority=rebuilt_authority,
        **{
            field_name: getattr(rebuilt_authority, field_name)
            for field_name in canonical_fields
        },
    )
    assert rebuilt_facts._authority is rebuilt_authority
    for field_name in canonical_fields:
        assert getattr(rebuilt_facts, field_name) is getattr(
            rebuilt_authority, field_name
        )
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(facts, _authority=rebuilt_authority)
    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(facts, origins=rebuilt_authority.origins)
    for field_name in canonical_fields:
        with pytest.raises((TypeError, ValueError), match="init=False"):
            replace(facts._authority, **{field_name: ()})

    _, row_semantic = _semantic_project(
        tmp_path / "rows",
        {
            "main.pietto": (
                "shape Row:\n"
                "    id: Int not null\n"
                'source rows: Row is postgres.table("rows")\n'
                "table projected:\n"
                "    from rows\n"
                "    select:\n"
                "        id\n"
                "query reported:\n"
                "    from projected\n"
                "    select:\n"
                "        id\n"
            )
        },
    )
    row_facts = _facts(row_semantic)
    with pytest.raises(ValueError, match="provenance must be retained"):
        replace(row_facts, reference_provenance=())
    with pytest.raises(ValueError, match="root requires a source-field origin"):
        replace(row_facts, source_field_origins=())

    with pytest.raises(ValueError, match="canonical authority facts"):
        replace(
            row_facts,
            source_field_origins=(),
            row_lineages=(),
            dependencies=tuple(
                item for item in row_facts.dependencies if item.target_row_field is None
            ),
        )

    source_owner = row_facts.source_field_origins[0].source_field.owner
    without_source_lineage = tuple(
        item for item in row_facts.row_lineages if item.owner != source_owner
    )
    with pytest.raises(ValueError, match="requires its retained row field"):
        replace(
            row_facts,
            dependencies=(),
            row_lineages=without_source_lineage,
        )

    row_dependency = next(
        item for item in row_facts.dependencies if item.target_row_field is not None
    )
    assert row_dependency.target_row_field is not None
    forged_target = replace(
        row_dependency.target_row_field,
        name="forged_missing",
    )
    forged_dependency = replace(
        row_dependency,
        target_row_field=forged_target,
    )
    forged_dependencies = tuple(
        forged_dependency if item == row_dependency else item
        for item in row_facts.dependencies
    )
    with pytest.raises(ValueError, match="target must be a retained row field"):
        replace(row_facts, dependencies=forged_dependencies)
    without_row_dependencies = tuple(
        item for item in row_facts.dependencies if item.target_row_field is None
    )
    with pytest.raises(ValueError, match="exactly match retained paths"):
        replace(row_facts, dependencies=without_row_dependencies)

    reported = _lineage(row_facts, "main.pietto", "reported")
    reported_field = reported.fields[0]
    reported_path = reported_field.paths[0]
    assert len(reported_path.hops) == 2
    forged_middle = replace(
        reported_path.hops[0].upstream_field,
        name="forged_middle",
    )
    forged_path = replace(
        reported_path,
        hops=(
            replace(reported_path.hops[0], upstream_field=forged_middle),
            replace(reported_path.hops[1], output_field=forged_middle),
        ),
    )
    forged_reported = replace(
        reported,
        fields=(replace(reported_field, paths=(forged_path,)),),
    )
    forged_lineages = tuple(
        forged_reported if item.owner == reported.owner else item
        for item in row_facts.row_lineages
    )
    with pytest.raises(ValueError, match="fields must be retained"):
        replace(row_facts, row_lineages=forged_lineages)

    _, alias_semantic = _semantic_project(
        tmp_path / "alias-route",
        {
            "a.pietto": (
                'import "z.pietto":\n'
                "    source rows as First\n"
                "    source rows as Second\n"
                "table result:\n"
                "    from First\n"
                "    select:\n"
                "        id\n"
            ),
            "z.pietto": (
                "shape Row:\n"
                "    id: Int not null\n"
                'source rows: Row is postgres.table("rows")\n'
                "export:\n"
                "    source rows\n"
            ),
        },
    )
    alias_facts = _facts(alias_semantic)
    alias_lineage = _lineage(alias_facts, "a.pietto", "result")
    alias_field = alias_lineage.fields[0]
    alias_path = alias_field.paths[0]
    assert len(alias_path.hops) == 1
    original_hop = alias_path.hops[0]
    second_origin = next(
        item
        for item in alias_facts.origins
        if item.owning_module_path == "a.pietto" and item.local_name == "Second"
    )
    swapped_hop = replace(original_hop, relation_origin=second_origin)
    swapped_path = replace(alias_path, hops=(swapped_hop,))
    swapped_lineage = replace(
        alias_lineage,
        fields=(replace(alias_field, paths=(swapped_path,)),),
    )
    swapped_lineages = tuple(
        swapped_lineage if item.owner == alias_lineage.owner else item
        for item in alias_facts.row_lineages
    )
    original_dependency = next(
        item
        for item in alias_facts.dependencies
        if item.reference == original_hop.reference
        and item.target_row_field == original_hop.upstream_field
    )
    swapped_dependency = replace(
        original_dependency,
        origin_path=second_origin,
    )
    swapped_dependencies = tuple(
        swapped_dependency if item == original_dependency else item
        for item in alias_facts.dependencies
    )
    with pytest.raises(ValueError, match="retained relation provenance"):
        replace(
            alias_facts,
            row_lineages=swapped_lineages,
            dependencies=swapped_dependencies,
        )


def test_builder_rejects_incomplete_or_misaligned_retained_inputs(
    tmp_path: Path,
) -> None:
    sources = {
        "a.pietto": "type A = Int\n",
        "z.pietto": (
            "enum E:\n"
            "    A\n"
            "shape Z:\n"
            "    id: E\n"
            'source rows: Z is postgres.table("rows")\n'
        ),
    }
    parse_result, semantic = _semantic_project(
        tmp_path,
        sources,
    )
    assert semantic.module_catalogs is not None
    assert semantic.module_exports is not None
    assert semantic.module_bindings is not None
    assert semantic.module_graph is not None
    assert semantic.module_diagnostic_facts is not None
    assert semantic.module_type_source_resolutions is not None
    assert semantic.module_relation_resolutions is not None
    assert semantic.selected_input_index is not None
    _, foreign_semantic = _semantic_project(
        tmp_path / "foreign-sidecar",
        sources,
    )
    assert foreign_semantic.module_catalogs is not None
    assert foreign_semantic.module_exports is not None
    assert foreign_semantic.module_bindings is not None
    assert foreign_semantic.module_graph is not None
    assert foreign_semantic.module_diagnostic_facts is not None
    assert foreign_semantic.module_type_source_resolutions is not None
    assert foreign_semantic.module_relation_resolutions is not None
    with pytest.raises(ValueError, match="exact canonical authority roots"):
        module_attribution._validate_resolution_identity_closure(
            parse_result.modules,
            semantic.module_catalogs,
            semantic.module_exports,
            semantic.module_bindings,
            semantic.module_graph,
            foreign_semantic.module_diagnostic_facts,
            semantic.module_type_source_resolutions,
            semantic.module_relation_resolutions,
        )

    relation_set = semantic.module_relation_resolutions
    local_environment = next(
        environment
        for environment in relation_set.environments
        if any(
            fact.state.schema is not None
            and any(
                field.resolved_type.symbol is not None
                for field in fact.state.schema.fields.values()
            )
            for fact in environment.row_facts
        )
    )
    foreign_environment = next(
        environment
        for environment in foreign_semantic.module_relation_resolutions.environments
        if environment.module.path == local_environment.module.path
    )
    local_fact = next(
        fact
        for fact in local_environment.row_facts
        if fact.state.schema is not None
        and any(
            field.resolved_type.symbol is not None
            for field in fact.state.schema.fields.values()
        )
    )
    foreign_fact = next(
        fact
        for fact in foreign_environment.row_facts
        if fact.owner.identity == local_fact.owner.identity
    )
    assert local_fact.state.schema is not None
    assert foreign_fact.state.schema is not None
    field_name = next(
        name
        for name, field in local_fact.state.schema.fields.items()
        if field.resolved_type.symbol is not None
    )
    local_field = local_fact.state.schema.fields[field_name]
    foreign_field = foreign_fact.state.schema.fields[field_name]
    assert local_field.resolved_type.symbol is not None
    assert foreign_field.resolved_type.symbol is not None
    assert (
        local_field.resolved_type.symbol.definition
        is not foreign_field.resolved_type.symbol.definition
    )
    hybrid_field = replace(
        local_field,
        resolved_type=foreign_field.resolved_type,
    )
    hybrid_schema = replace(
        local_fact.state.schema,
        fields={
            **local_fact.state.schema.fields,
            field_name: hybrid_field,
        },
    )
    hybrid_fact = replace(
        local_fact,
        state=replace(local_fact.state, schema=hybrid_schema),
    )
    hybrid_environment = replace(
        local_environment,
        row_facts=tuple(
            hybrid_fact if fact is local_fact else fact
            for fact in local_environment.row_facts
        ),
    )
    hybrid_relation_set = replace(
        relation_set,
        environments=tuple(
            hybrid_environment if environment is local_environment else environment
            for environment in relation_set.environments
        ),
    )
    assert hybrid_relation_set == relation_set
    with pytest.raises(ValueError, match="exact current roots"):
        module_attribution._validate_resolution_identity_closure(
            parse_result.modules,
            semantic.module_catalogs,
            semantic.module_exports,
            semantic.module_bindings,
            semantic.module_graph,
            semantic.module_diagnostic_facts,
            semantic.module_type_source_resolutions,
            hybrid_relation_set,
        )

    build = module_attribution._build_project_module_attribution_fact_set
    arguments = (
        parse_result,
        parse_result.modules,
        semantic.selected_input_index,
        semantic.trusted_source_snapshots,
        semantic.module_catalogs,
        semantic.module_exports,
        semantic.module_bindings,
        semantic.module_graph,
        semantic.module_diagnostic_facts,
        semantic.module_type_source_resolutions,
        semantic.module_relation_resolutions,
    )
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(parse_result, (parse_result.modules[0],), *arguments[2:])
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(
            parse_result,
            parse_result.modules,
            semantic.selected_input_index,
            tuple(reversed(semantic.trusted_source_snapshots)),
            *arguments[4:],
        )
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(replace(parse_result, root=None), *arguments[1:])
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(
            replace(
                parse_result,
                compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
            ),
            *arguments[1:],
        )
    misbound_input_parse = replace(
        parse_result,
        inputs=(replace(parse_result.inputs[0]), *parse_result.inputs[1:]),
    )
    with pytest.raises(ValueError, match="ordered selected input authority"):
        build(misbound_input_parse, *arguments[1:])
    misbound_parsed_input_parse = replace(
        parse_result,
        parsed_inputs=(
            replace(parse_result.parsed_inputs[0]),
            *parse_result.parsed_inputs[1:],
        ),
    )
    with pytest.raises(ValueError, match="ordered selected input authority"):
        build(misbound_parsed_input_parse, *arguments[1:])

    foreign_input_parse, foreign_input_semantic = _semantic_project(
        tmp_path / "foreign-input-authority",
        {
            "a.pietto": "type A = Text\n",
            "z.pietto": (
                "enum E:\n"
                "    B\n"
                "shape Z:\n"
                "    id: E\n"
                'source rows: Z is postgres.table("other_rows")\n'
            ),
        },
    )
    assert foreign_input_semantic.selected_input_index is not None
    assert foreign_input_parse.selected_input_index is not None
    assert tuple(module.path for module in foreign_input_parse.modules) == tuple(
        module.path for module in parse_result.modules
    )
    assert tuple(
        snapshot.sha256 for snapshot in foreign_input_parse.trusted_source_snapshots
    ) != tuple(snapshot.sha256 for snapshot in parse_result.trusted_source_snapshots)
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(
            parse_result,
            parse_result.modules,
            foreign_input_parse.selected_input_index,
            foreign_input_parse.trusted_source_snapshots,
            *arguments[4:],
        )
    with pytest.raises(ValueError, match="exact parse result roots"):
        build(
            foreign_input_parse,
            parse_result.modules,
            foreign_input_parse.selected_input_index,
            foreign_input_parse.trusted_source_snapshots,
            *arguments[4:],
        )

    type_set = semantic.module_type_source_resolutions
    reversed_type = replace(
        type_set,
        dependency_order=tuple(reversed(type_set.dependency_order)),
        environments=tuple(reversed(type_set.environments)),
    )
    reversed_relation = replace(
        relation_set,
        dependency_order=tuple(reversed(relation_set.dependency_order)),
        environments=tuple(reversed(relation_set.environments)),
    )
    with pytest.raises(ValueError, match="exact graph dependency order"):
        build(*arguments[:-2], reversed_type, reversed_relation)

    first_environment = type_set.environments[0]
    incomplete_environment = replace(first_environment, type_resolutions=())
    incomplete_type_set = replace(
        type_set,
        environments=(incomplete_environment, *type_set.environments[1:]),
    )
    with pytest.raises(ValueError, match="cover exact catalog references"):
        build(*arguments[:-2], incomplete_type_set, relation_set)

    _, diagnostic_semantic = _semantic_project(
        tmp_path / "diagnostic-root",
        {"main.pietto": 'import "missing.pietto":\n    shape Missing\n'},
    )
    assert diagnostic_semantic.selected_input_index is not None
    assert diagnostic_semantic.module_catalogs is not None
    assert diagnostic_semantic.module_exports is not None
    assert diagnostic_semantic.module_bindings is not None
    assert diagnostic_semantic.module_graph is not None
    assert diagnostic_semantic.module_diagnostic_facts is not None
    assert diagnostic_semantic.module_diagnostic_facts.facts
    assert diagnostic_semantic.module_type_source_resolutions is not None
    assert diagnostic_semantic.module_relation_resolutions is not None
    with pytest.raises(ValueError, match="canonical authority objects"):
        replace(
            diagnostic_semantic.module_diagnostic_facts,
            facts=(),
            diagnostics=(),
        )
    with pytest.raises(ValueError, match="exact ordered root projection"):
        replace(diagnostic_semantic, diagnostics=())

    facts = _facts(semantic)
    assert replace(semantic, module_attribution_facts=facts) == semantic
    for field_name in (
        "module_catalogs",
        "module_exports",
        "module_bindings",
        "module_graph",
        "module_diagnostic_facts",
        "module_type_source_resolutions",
        "module_relation_resolutions",
        "module_attribution_facts",
    ):
        with pytest.raises(ValueError, match="require all module sidecars"):
            replace(semantic, **{field_name: None})
    with pytest.raises(TypeError, match="exact attribution fact set"):
        replace(
            semantic,
            module_attribution_facts=cast(
                module_attribution.ProjectModuleAttributionFactSet,
                SimpleNamespace(),
            ),
        )
    preliminary = ProjectSemanticResult(
        root=parse_result.root,
        config_path=parse_result.config_path,
        model=None,
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        modules=parse_result.modules,
        pinned_root=parse_result.pinned_root,
        selected_input_index=parse_result.selected_input_index,
        trusted_source_snapshots=parse_result.trusted_source_snapshots,
    )
    assert preliminary.module_attribution_facts is None
    with pytest.raises(TypeError, match="exact compilation mode"):
        replace(
            preliminary,
            compilation_mode=cast(ProjectCompilationMode, "invalid"),
        )
    with pytest.raises(ValueError, match="require all module sidecars"):
        replace(preliminary, module_catalogs=semantic.module_catalogs)
    with pytest.raises(ValueError, match="forbid module sidecars"):
        replace(
            preliminary,
            compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
            module_catalogs=semantic.module_catalogs,
        )
    assert (
        ProjectSemanticResult(
            root=None,
            config_path=None,
            model=None,
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        ).module_attribution_facts
        is None
    )
    foreign_facts = _facts(foreign_semantic)
    assert foreign_semantic.module_diagnostic_facts is not None
    assert foreign_semantic.module_type_source_resolutions is not None
    assert foreign_semantic.module_relation_resolutions is not None
    assert foreign_facts == facts
    assert foreign_facts is not facts
    assert foreign_facts.binding_authority is not facts.binding_authority
    with pytest.raises(ValueError, match="exact parse result roots"):
        replace(
            semantic,
            module_attribution_facts=foreign_facts,
        )
    with pytest.raises(ValueError, match="exact parse result roots"):
        replace(
            semantic,
            selected_input_index=foreign_semantic.selected_input_index,
        )
    with pytest.raises(ValueError, match="exact parse result roots"):
        replace(
            semantic,
            trusted_source_snapshots=foreign_semantic.trusted_source_snapshots,
        )
    with pytest.raises(ValueError, match="exact parse result roots"):
        replace(
            semantic,
            pinned_root=foreign_semantic.pinned_root,
        )
    with pytest.raises(ValueError, match="exact diagnostic authority"):
        replace(
            semantic,
            module_diagnostic_facts=foreign_semantic.module_diagnostic_facts,
        )
    foreign_module_roots = {
        field_name: getattr(foreign_semantic, field_name)
        for field_name in (
            "module_catalogs",
            "module_exports",
            "module_bindings",
            "module_graph",
            "module_diagnostic_facts",
            "module_type_source_resolutions",
            "module_relation_resolutions",
            "module_attribution_facts",
        )
    }
    with pytest.raises(ValueError, match="exact parse result roots"):
        replace(semantic, **foreign_module_roots)
    with pytest.raises(ValueError, match="exact current roots"):
        build(
            *arguments[:-2],
            foreign_semantic.module_type_source_resolutions,
            foreign_semantic.module_relation_resolutions,
        )
    module_by_path = {module.path: module for module in parse_result.modules}
    current_occurrences = tuple(
        occurrence
        for catalog in semantic.module_catalogs.catalogs
        for occurrence in catalog.occurrences
    )
    foreign_type_environment = (
        foreign_semantic.module_type_source_resolutions.environments[0]
    )
    rebound_type_environment = replace(
        foreign_type_environment,
        module=module_by_path[foreign_type_environment.module.path],
    )
    assert rebound_type_environment.type_resolutions
    assert all(
        rebound_type_environment.type_resolutions[0].reference.owner is not occurrence
        for occurrence in current_occurrences
    )
    partial_type = replace(
        type_set,
        environments=tuple(
            rebound_type_environment
            if environment.module.path == rebound_type_environment.module.path
            else environment
            for environment in type_set.environments
        ),
    )
    foreign_relation_environment = next(
        environment
        for environment in foreign_semantic.module_relation_resolutions.environments
        if environment.row_facts
    )
    rebound_relation_environment = replace(
        foreign_relation_environment,
        module=module_by_path[foreign_relation_environment.module.path],
    )
    assert all(
        rebound_relation_environment.row_facts[0].owner is not occurrence
        for occurrence in current_occurrences
    )
    partial_relation = replace(
        relation_set,
        environments=tuple(
            rebound_relation_environment
            if environment.module.path == rebound_relation_environment.module.path
            else environment
            for environment in relation_set.environments
        ),
    )
    with pytest.raises(ValueError, match="exact current roots"):
        build(*arguments[:-2], partial_type, relation_set)
    with pytest.raises(ValueError, match="exact current roots"):
        build(*arguments[:-2], type_set, partial_relation)
    for field_name in (
        "modules",
        "module_catalogs",
        "module_exports",
        "module_graph",
        "module_type_source_resolutions",
        "module_relation_resolutions",
    ):
        with pytest.raises(
            ValueError,
            match=r"exact (?:parse result|project semantic|canonical authority) roots",
        ):
            replace(
                semantic,
                **{field_name: getattr(foreign_semantic, field_name)},
            )
    with pytest.raises(ValueError, match="exact project binding authority"):
        replace(
            semantic,
            module_bindings=foreign_semantic.module_bindings,
        )
    _, legacy_semantic = _semantic_project(
        tmp_path / "legacy-model",
        sources,
        schema_version=1,
    )
    assert legacy_semantic.model is not None
    with pytest.raises(ValueError, match="forbid a legacy model"):
        replace(semantic, model=legacy_semantic.model)
    with pytest.raises(ValueError, match="forbid module sidecars"):
        replace(
            semantic,
            compilation_mode=ProjectCompilationMode.LEGACY_FLAT,
        )


def test_builder_is_pure_over_preloaded_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _simple_library()},
    )
    assert semantic.module_catalogs is not None
    assert semantic.module_exports is not None
    assert semantic.module_bindings is not None
    assert semantic.module_graph is not None
    assert semantic.module_diagnostic_facts is not None
    assert semantic.module_type_source_resolutions is not None
    assert semantic.module_relation_resolutions is not None
    assert semantic.selected_input_index is not None

    def unexpected_io(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("Slice 11 builder must consume preloaded facts only")

    monkeypatch.setattr("builtins.open", unexpected_io)
    monkeypatch.setattr(Path, "read_text", unexpected_io)
    monkeypatch.setattr(Path, "read_bytes", unexpected_io)
    rebuilt = module_attribution._build_project_module_attribution_fact_set(
        parse_result,
        parse_result.modules,
        semantic.selected_input_index,
        semantic.trusted_source_snapshots,
        semantic.module_catalogs,
        semantic.module_exports,
        semantic.module_bindings,
        semantic.module_graph,
        semantic.module_diagnostic_facts,
        semantic.module_type_source_resolutions,
        semantic.module_relation_resolutions,
    )
    assert rebuilt == _facts(semantic)


def test_schema_v1_text_json_ir_sql_and_sidecar_absence_remain_byte_exact(
    tmp_path: Path,
) -> None:
    source = _simple_library()
    project_root = _configured_project(
        tmp_path,
        {"main.pietto": source},
        schema_version=1,
    )
    parse_result = project_check.check_project_parse_only(project_root)
    assert parse_result.ok
    json_before = json.dumps(
        project_check_result_to_json_dict(parse_result),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    semantic = build_empty_project_semantic_result(parse_result)
    json_after = json.dumps(
        project_check_result_to_json_dict(parse_result),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()
    assert semantic.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert semantic.model is not None
    assert semantic.module_attribution_facts is None
    assert json_after == json_before
    assert b"module_attribution" not in json_after

    parsed = parser_api.parse_source(source, path="main.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    analyzed = semantic_api.analyze(parsed.ast)
    assert not any(item.severity is Severity.ERROR for item in analyzed.diagnostics)
    lowered = build_ir(parsed.ast, analyzed.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    sql = emit_postgres_sql(lowered.ir)
    assert sql.diagnostics == ()
    ir_bytes = repr(lowered.ir).encode()
    sql_bytes = repr(sql).encode()
    assert b"ProjectModule" not in ir_bytes
    assert b"module_attribution" not in ir_bytes + sql_bytes
    assert (
        hashlib.sha256(ir_bytes).hexdigest()
        == hashlib.sha256(repr(lowered.ir).encode()).hexdigest()
    )
    assert (
        hashlib.sha256(sql_bytes).hexdigest()
        == hashlib.sha256(repr(emit_postgres_sql(lowered.ir)).encode()).hexdigest()
    )


def test_schema_v2_cli_json_public_exports_dependencies_version_and_generated_goldens_remain_unchanged(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _simple_library()},
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic.diagnostics,
    )
    serialized = json.dumps(document, ensure_ascii=True)
    assert tuple(document) == (
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
    assert "module_attribution" not in serialized
    assert "ProjectModuleAttributionFactSet" not in serialized
    assert semantic.model is None
    assert semantic.module_attribution_facts is not None

    public_sources = tuple(
        (REPO_ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "src/pietto/__init__.py",
            "src/pietto/cli.py",
            "src/pietto/_project/json_v2.py",
            "src/pietto/ir/__init__.py",
            "src/pietto/sql/__init__.py",
        )
    )
    assert all("module_attribution" not in source for source in public_sources)
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    assert "module-attribution" not in pyproject
    assert "module_attribution" not in (REPO_ROOT / "uv.lock").read_text(
        encoding="utf-8"
    )
    generated = tuple(
        item
        for item in (REPO_ROOT / "src/pietto/generated").iterdir()
        if item.is_file()
    )
    goldens = tuple(
        item
        for item in (REPO_ROOT / "tests/fixtures/golden").iterdir()
        if item.is_file()
    )
    assert len(generated) == 8
    assert len(goldens) == 37

    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    observed = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert observed == EXPECTED_TEST_NAMES
    assert len(observed) == 44
    assert inspect.signature(
        module_attribution._build_project_module_attribution_fact_set
    ).return_annotation in {
        "ProjectModuleAttributionFactSet",
        module_attribution.ProjectModuleAttributionFactSet,
    }
