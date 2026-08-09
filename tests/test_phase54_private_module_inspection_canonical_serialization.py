"""Phase 54 Slice 14 private module inspection and canonical serialization."""

from __future__ import annotations

import ast
from dataclasses import fields, replace
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto
import pietto._project.check as project_check
import pietto._project.module_inspection as inspection_module
import pietto._project.module_package_neutral_identity as layering
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectModuleIdentity

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice14-private-module-inspection-and-canonical-"
    "serialization-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_inspection.py"
TEST_REL = "tests/test_phase54_private_module_inspection_canonical_serialization.py"

EXPECTED_TEST_NAMES = (
    "test_slice14_contract_status_active_manifest_and_allowlist_are_exact",
    "test_inspection_vocabulary_carriers_fields_and_privacy_are_exact",
    "test_schema_v1_has_no_inspection_sidecar_and_public_bytes_remain_exact",
    "test_schema_v2_builds_the_inspection_sidecar_from_ten_exact_shared_roots",
    "test_shared_root_predicate_rejects_value_equal_foreign_root_sets",
    "test_shared_root_predicate_rejects_coordinated_mixed_slice_roots",
    "test_shared_root_predicate_rejects_partial_misaligned_or_reordered_roots",
    "test_inspection_authority_derives_products_and_rejects_grafted_projections",
    "test_inspection_covers_every_selected_module_in_exact_selected_order",
    "test_inspection_covers_every_declaration_in_catalog_and_source_order",
    "test_module_digest_is_reached_through_slice13_without_reread_or_rehash",
    "test_byte_equal_modules_share_one_digest_identity_and_remain_distinct",
    "test_loader_readiness_is_recorded_as_a_fact_without_loader_behavior",
    "test_module_cycle_records_blocked_readiness_and_complete_cycle_members",
    "test_graph_section_records_components_dependency_targets_and_evidence",
    "test_import_section_keeps_local_aliases_separate_from_nominal_ownership",
    "test_unresolvable_upstream_text_is_inspected_verbatim_without_revalidation",
    "test_export_section_records_requests_entries_origins_and_issue_buckets",
    "test_repeated_nominal_identity_is_ambiguous_with_a_complete_bucket",
    "test_identity_distinct_occurrences_preserve_multiplicity_and_position",
    "test_relation_declaration_states_concrete_unknown_deferred_and_blocked",
    "test_non_relation_declaration_is_absent_rather_than_unknown",
    "test_origin_section_records_local_and_imported_paths_with_exact_hops",
    "test_dependency_and_row_lineage_sections_preserve_exact_identities",
    "test_type_source_and_relation_resolution_sections_are_complete",
    "test_semantic_fact_section_preserves_ordinals_names_and_states",
    "test_issue_section_preserves_every_family_status_without_a_winner",
    "test_inspection_indexes_are_derived_and_return_complete_buckets",
    "test_canonical_bytes_declare_the_private_format_and_end_with_one_newline",
    "test_canonical_bytes_encode_every_inspection_record_deterministically",
    "test_canonical_bytes_are_identical_across_processes_and_hash_seeds",
    "test_canonical_bytes_are_stable_under_non_authoritative_mapping_order",
    "test_canonical_bytes_change_with_identity_order_multiplicity_or_state",
    "test_canonical_bytes_change_with_a_replaced_digest_or_readiness_fact",
    "test_canonical_bytes_escape_control_characters_and_stay_utf8_exact",
    "test_inspection_exposes_no_host_path_inode_address_or_runtime_state",
    "test_forged_canonical_payload_and_grafted_inspection_are_rejected",
    "test_eleventh_sidecar_all_or_none_boundary_is_exact_and_fail_closed",
    "test_inspection_builder_is_pure_over_preloaded_roots_and_performs_no_io",
    "test_slice13_and_earlier_products_remain_independent_and_unchanged",
    "test_schema_v2_public_api_cli_json_ir_sql_dependencies_and_goldens_unchanged",
)

_RECORD_KINDS = (
    "declaration",
    "declaration_row_field",
    "dependency",
    "digest",
    "export",
    "export_issue",
    "graph",
    "graph_component_member",
    "graph_dependency_target",
    "graph_import_evidence",
    "import",
    "import_issue",
    "inspection",
    "issue",
    "module",
    "origin",
    "origin_hop",
    "owner",
    "readiness",
    "readiness_cycle",
    "readiness_cycle_member",
    "relation_resolution",
    "row_lineage",
    "row_lineage_field",
    "row_lineage_hop",
    "row_lineage_path",
    "semantic_clause_dependency",
    "semantic_facts",
    "semantic_let_binding",
    "semantic_select",
    "semantic_window_output",
    "source_shape_resolution",
    "type_resolution",
    "type_resolution_alias",
)

_TOKEN_TAGS = ("b:", "e:", "i:", "n:", "s:")

_SHAPE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    category: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
)


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["**/*.pietto"]\n',
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
) -> ProjectSemanticResult:
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, sources, schema_version=schema_version)
    )
    assert parse_result.ok
    return build_empty_project_semantic_result(parse_result)


def _inspection(
    semantic: ProjectSemanticResult,
) -> inspection_module.ProjectModuleInspectionFactSet:
    facts = semantic.module_inspection_facts
    assert facts is not None
    return facts


def _layered(
    semantic: ProjectSemanticResult,
) -> layering.ProjectModulePackageNeutralIdentityFactSet:
    facts = semantic.module_package_identity_facts
    assert facts is not None
    return facts


def _decoded(semantic: ProjectSemanticResult) -> str:
    return _inspection(semantic).canonical_bytes.decode("utf-8")


def _record(
    semantic: ProjectSemanticResult,
    module_path: str,
) -> inspection_module.ProjectModuleInspectionRecord:
    matches = _inspection(semantic).find_module(ProjectModuleIdentity(path=module_path))
    assert len(matches) == 1
    return matches[0]


def _declaration(
    semantic: ProjectSemanticResult,
    module_path: str,
    declared_name: str,
) -> inspection_module.ProjectInspectionDeclaration:
    matches = tuple(
        declaration
        for declaration in _record(semantic, module_path).declarations
        if declaration.identity.declared_name == declared_name
    )
    assert len(matches) == 1
    return matches[0]


def _build_inspection(
    result: ProjectSemanticResult,
    **overrides: object,
) -> inspection_module.ProjectModuleInspectionFactSet:
    roots: dict[str, object] = {
        "modules": result.modules,
        "catalogs": result.module_catalogs,
        "exports": result.module_exports,
        "bindings": result.module_bindings,
        "graph": result.module_graph,
        "type_source_resolutions": result.module_type_source_resolutions,
        "relation_resolutions": result.module_relation_resolutions,
        "attribution": result.module_attribution_facts,
        "semantic": result.module_semantic_facts,
        "package_identity": result.module_package_identity_facts,
    }
    roots.update(overrides)
    return inspection_module._build_project_module_inspection_fact_set(
        roots["modules"],  # pyright: ignore[reportArgumentType]
        roots["catalogs"],  # pyright: ignore[reportArgumentType]
        roots["exports"],  # pyright: ignore[reportArgumentType]
        roots["bindings"],  # pyright: ignore[reportArgumentType]
        roots["graph"],  # pyright: ignore[reportArgumentType]
        roots["type_source_resolutions"],  # pyright: ignore[reportArgumentType]
        roots["relation_resolutions"],  # pyright: ignore[reportArgumentType]
        roots["attribution"],  # pyright: ignore[reportArgumentType]
        roots["semantic"],  # pyright: ignore[reportArgumentType]
        roots["package_identity"],  # pyright: ignore[reportArgumentType]
    )


def _query_module(body: str) -> str:
    return _SHAPE_PREFIX + "query result:\n    from rows\n" + body


def _cycle_sources() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    shape S\nexport:\n    shape T\nshape T:\n'
            "    id: Int\n"
        ),
        "b.pietto": (
            'import "a.pietto":\n    shape T\nexport:\n    shape S\nshape S:\n'
            "    id: Int\n"
        ),
    }


def _facade_sources() -> dict[str, str]:
    return {
        "base.pietto": (_SHAPE_PREFIX + "export:\n    shape Row\n    source rows\n"),
        "main.pietto": (
            'import "base.pietto":\n    shape Row\n    source rows as r\n'
            "query result:\n    from r\n    select:\n        id\n        amount\n"
        ),
    }


def _expected_record_count(
    inspection: inspection_module.ProjectModuleInspection,
) -> int:
    total = 2
    for record in inspection.modules:
        total += 3
        total += len(record.readiness.cycles)
        total += sum(len(cycle.members) for cycle in record.readiness.cycles)
        total += 1
        total += len(record.graph.component_members)
        total += len(record.graph.dependency_targets)
        total += len(record.graph.import_evidence)
        total += len(record.imports)
        total += sum(len(item.issue_statuses) for item in record.imports)
        total += len(record.exports)
        total += sum(len(item.issue_statuses) for item in record.exports)
        total += len(record.declarations)
        total += sum(len(item.row_fields) for item in record.declarations)
        total += len(record.origins)
        total += sum(len(item.hops) for item in record.origins)
        total += len(record.dependencies)
        total += len(record.row_lineage)
        for lineage in record.row_lineage:
            total += len(lineage.fields)
            for field_lineage in lineage.fields:
                total += len(field_lineage.paths)
                total += sum(len(path.hops) for path in field_lineage.paths)
        total += len(record.type_resolutions)
        total += sum(len(item.alias_chain) for item in record.type_resolutions)
        total += len(record.source_shape_resolutions)
        total += len(record.relation_resolutions)
        total += len(record.semantic_facts)
        for facts in record.semantic_facts:
            total += len(facts.let_bindings)
            total += len(facts.selects)
            total += len(facts.clause_dependencies)
            total += len(facts.window_outputs)
        total += len(record.issues)
    return total


def _family_rank(family: inspection_module.ProjectInspectionIssueFamily) -> int:
    order = (
        inspection_module.ProjectInspectionIssueFamily.GRAPH,
        inspection_module.ProjectInspectionIssueFamily.TYPE_SOURCE,
        inspection_module.ProjectInspectionIssueFamily.RELATION,
    )
    return order.index(family)


def test_slice14_contract_status_active_manifest_and_allowlist_are_exact() -> None:
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert spec.startswith(
        "# Phase 54 Slice 14 Private Module Inspection And Canonical Serialization v1"
    )
    assert "PHASE54_SLICE14_GATE2_COMPLETED_AWAITING_PUBLICATION" in plan
    assert "Slices 15-16" in plan
    assert "Slice 14" in readme

    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE14_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "040ab19c56519c39c56541979c850484f9cc47f0"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BRANCH == (
        "phase54/slice14-private-module-inspection"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_SUBJECT == (
        "Add Phase 54 private module inspection"
    )
    assert active_gate2_manifest.ADDED_PATHS == {SPEC_REL, SOURCE_REL, TEST_REL}
    assert active_gate2_manifest.NON_READER_MODIFIED_PATHS == {
        "README.md",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "docs/spec/pietto-v0.9.md",
        "src/pietto/_project/model.py",
        "tests/_phase54_active_gate2_manifest.py",
    }
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 58
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 63
    assert len(active_gate2_manifest.ALLOWLIST_PATHS) == 66
    assert (
        sum(path.endswith(".py") for path in active_gate2_manifest.ALLOWLIST_PATHS)
        == 62
    )
    assert not (
        active_gate2_manifest.NON_READER_MODIFIED_PATHS
        & active_gate2_manifest.MECHANICAL_READER_PATHS
    )
    assert not (
        active_gate2_manifest.ADDED_PATHS & active_gate2_manifest.MODIFIED_PATHS
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert "58-reader" in spec
    assert "exact 62 Python paths" in spec
    assert "exact `A3_M63_D0`" in spec


def test_inspection_vocabulary_carriers_fields_and_privacy_are_exact() -> None:
    assert inspection_module.__all__ == ()
    assert tuple(
        member.value for member in inspection_module.ProjectInspectionFormat
    ) == ("pietto.module-inspection.v1",)
    assert tuple(
        member.value for member in inspection_module.ProjectInspectionBinding
    ) == ("local_declaration", "imported_binding")
    assert tuple(
        member.value for member in inspection_module.ProjectInspectionIssueFamily
    ) == ("graph", "type_source", "relation")

    projection_fields = tuple(
        item.name for item in fields(inspection_module.ProjectModuleInspection)
    )
    assert projection_fields == ("format", "owner", "modules")
    record_fields = tuple(
        item.name for item in fields(inspection_module.ProjectModuleInspectionRecord)
    )
    assert record_fields == (
        "module",
        "position",
        "digest",
        "readiness",
        "graph",
        "imports",
        "exports",
        "declarations",
        "origins",
        "dependencies",
        "row_lineage",
        "type_resolutions",
        "source_shape_resolutions",
        "relation_resolutions",
        "semantic_facts",
        "issues",
        "asset",
    )
    fact_set_fields = tuple(
        item.name for item in fields(inspection_module.ProjectModuleInspectionFactSet)
    )
    assert fact_set_fields == (
        "inspection",
        "canonical_bytes",
        "authority",
        "_modules_by_path",
        "_declarations_by_identity",
    )

    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    for forbidden in (
        "package_name",
        "manifest",
        "registry",
        "lockfile",
        "urllib",
        "socket",
        "subprocess",
        "importlib",
        "hashlib",
        "open(",
        "read_text",
        "read_bytes",
        "exec(",
        "eval(",
    ):
        assert forbidden not in source


def test_schema_v1_has_no_inspection_sidecar_and_public_bytes_remain_exact(
    tmp_path: Path,
) -> None:
    root = _configured_project(
        tmp_path,
        {"main.pietto": _SHAPE_PREFIX},
        schema_version=1,
    )
    parse_result = project_check.check_project_parse_only(root)
    before = json.dumps(
        project_check_result_to_json_dict(parse_result), sort_keys=True
    ).encode()
    legacy = build_empty_project_semantic_result(parse_result)
    after = json.dumps(
        project_check_result_to_json_dict(parse_result), sort_keys=True
    ).encode()

    assert legacy.module_inspection_facts is None
    assert legacy.model is not None
    assert after == before
    for forbidden in ("inspection", "canonical_bytes", "module-inspection"):
        assert forbidden not in after.decode()
    with pytest.raises(ValueError, match="forbid module sidecars"):
        replace(
            legacy,
            module_inspection_facts=object(),  # pyright: ignore[reportArgumentType]
        )


def test_schema_v2_builds_the_inspection_sidecar_from_ten_exact_shared_roots(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    facts = _inspection(semantic)
    authority = facts.authority

    assert authority.modules is semantic.modules
    assert authority.catalogs is semantic.module_catalogs
    assert authority.exports is semantic.module_exports
    assert authority.bindings is semantic.module_bindings
    assert authority.graph is semantic.module_graph
    assert authority.type_source_resolutions is semantic.module_type_source_resolutions
    assert authority.relation_resolutions is semantic.module_relation_resolutions
    assert authority.attribution is semantic.module_attribution_facts
    assert authority.semantic is semantic.module_semantic_facts
    assert authority.package_identity is semantic.module_package_identity_facts

    assert facts.inspection is authority.inspection
    assert facts.canonical_bytes is authority.canonical_bytes
    assert semantic.model is None
    assert (
        facts.inspection.format
        is inspection_module.ProjectInspectionFormat.MODULE_INSPECTION_V1
    )
    assert facts.inspection.owner is _layered(semantic).owner


def test_shared_root_predicate_rejects_value_equal_foreign_root_sets(
    tmp_path: Path,
) -> None:
    sources = _facade_sources()
    semantic = _semantic_project(tmp_path / "one", sources)
    foreign = _semantic_project(tmp_path / "two", sources)

    assert semantic.module_attribution_facts == foreign.module_attribution_facts
    assert semantic.module_attribution_facts is not foreign.module_attribution_facts

    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, modules=foreign.modules)
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, catalogs=foreign.module_catalogs)
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, attribution=foreign.module_attribution_facts)
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, semantic=foreign.module_semantic_facts)
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(
            semantic,
            package_identity=foreign.module_package_identity_facts,
        )
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(semantic, exports=foreign.module_exports)
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(semantic, bindings=foreign.module_bindings)
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(semantic, graph=foreign.module_graph)
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(
            semantic,
            type_source_resolutions=foreign.module_type_source_resolutions,
        )
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(
            semantic,
            relation_resolutions=foreign.module_relation_resolutions,
        )


def test_shared_root_predicate_rejects_coordinated_mixed_slice_roots(
    tmp_path: Path,
) -> None:
    sources = _facade_sources()
    semantic = _semantic_project(tmp_path / "one", sources)
    foreign = _semantic_project(tmp_path / "two", sources)

    # A coordinated set that mixes the Slice 11, Slice 12, and Slice 13 roots of
    # two value-equal projects is rejected as a whole, not child by child.
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(
            semantic,
            attribution=foreign.module_attribution_facts,
            semantic=foreign.module_semantic_facts,
        )
    # The Slice 13 sub-set is internally consistent here, so the whole-set
    # predicate still rejects it on the Slice 11 roots it left behind.
    with pytest.raises(ValueError, match="exact Slice 11 roots"):
        _build_inspection(
            semantic,
            modules=foreign.modules,
            catalogs=foreign.module_catalogs,
            attribution=foreign.module_attribution_facts,
            semantic=foreign.module_semantic_facts,
            package_identity=foreign.module_package_identity_facts,
        )
    # Keeping only the Slice 12 root local is rejected by the Slice 13 anchor,
    # which retains that sidecar as one of its own exact roots.
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(
            semantic,
            modules=foreign.modules,
            catalogs=foreign.module_catalogs,
            exports=foreign.module_exports,
            bindings=foreign.module_bindings,
            graph=foreign.module_graph,
            type_source_resolutions=foreign.module_type_source_resolutions,
            relation_resolutions=foreign.module_relation_resolutions,
            attribution=foreign.module_attribution_facts,
            package_identity=foreign.module_package_identity_facts,
        )
    every_foreign = _build_inspection(
        semantic,
        modules=foreign.modules,
        catalogs=foreign.module_catalogs,
        exports=foreign.module_exports,
        bindings=foreign.module_bindings,
        graph=foreign.module_graph,
        type_source_resolutions=foreign.module_type_source_resolutions,
        relation_resolutions=foreign.module_relation_resolutions,
        attribution=foreign.module_attribution_facts,
        semantic=foreign.module_semantic_facts,
        package_identity=foreign.module_package_identity_facts,
    )
    assert every_foreign.authority.modules is foreign.modules
    assert every_foreign.canonical_bytes == _inspection(semantic).canonical_bytes
    with pytest.raises(ValueError, match="exact ten sidecar roots"):
        replace(semantic, module_inspection_facts=every_foreign)
    assert (
        replace(foreign, module_inspection_facts=every_foreign).module_inspection_facts
        is every_foreign
    )


def test_shared_root_predicate_rejects_partial_misaligned_or_reordered_roots(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    modules = semantic.modules
    assert len(modules) == 2

    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, modules=modules[:1])
    with pytest.raises(ValueError, match="exact Slice 13 module, catalog"):
        _build_inspection(semantic, modules=(modules[1], modules[0]))
    with pytest.raises(TypeError, match="authority modules"):
        _build_inspection(semantic, modules=list(modules))
    with pytest.raises(TypeError, match="exact module catalogs"):
        _build_inspection(semantic, catalogs=None)
    with pytest.raises(TypeError, match="exact export surface set"):
        _build_inspection(semantic, exports=None)
    with pytest.raises(TypeError, match="exact binding set"):
        _build_inspection(semantic, bindings=None)
    with pytest.raises(TypeError, match="exact module graph"):
        _build_inspection(semantic, graph=None)
    with pytest.raises(TypeError, match="exact Slice 9 set"):
        _build_inspection(semantic, type_source_resolutions=None)
    with pytest.raises(TypeError, match="exact Slice 10 set"):
        _build_inspection(semantic, relation_resolutions=None)
    with pytest.raises(TypeError, match="exact Slice 11 fact set"):
        _build_inspection(semantic, attribution=None)
    with pytest.raises(TypeError, match="exact Slice 12 fact set"):
        _build_inspection(semantic, semantic=None)
    with pytest.raises(TypeError, match="exact Slice 13 fact set"):
        _build_inspection(semantic, package_identity=None)


def test_inspection_authority_derives_products_and_rejects_grafted_projections(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path / "one", _facade_sources())
    foreign = _semantic_project(tmp_path / "two", _facade_sources())
    facts = _inspection(semantic)
    foreign_facts = _inspection(foreign)

    assert facts.inspection == foreign_facts.inspection
    assert facts.inspection is not foreign_facts.inspection
    assert facts.canonical_bytes == foreign_facts.canonical_bytes

    with pytest.raises(ValueError, match="exact derived projection"):
        replace(facts, inspection=foreign_facts.inspection)
    with pytest.raises(ValueError, match="exact derived canonical bytes"):
        replace(facts, canonical_bytes=bytes(bytearray(facts.canonical_bytes)))
    with pytest.raises(TypeError, match="exact private authority"):
        replace(
            facts,
            authority=None,  # pyright: ignore[reportArgumentType]
        )
    # Both products are init=False on the authority, so a replacement operation
    # substitutes roots only and can never graft a derived product.
    with pytest.raises((TypeError, ValueError)):
        replace(facts.authority, inspection=foreign_facts.inspection)
    with pytest.raises((TypeError, ValueError)):
        replace(facts.authority, canonical_bytes=b"forged\n")


def test_inspection_covers_every_selected_module_in_exact_selected_order(
    tmp_path: Path,
) -> None:
    for count in (1, 2, 3):
        sources = {f"m{index}.pietto": _SHAPE_PREFIX for index in range(count)}
        semantic = _semantic_project(tmp_path / f"project{count}", sources)
        facts = _inspection(semantic)
        assert len(facts.inspection.modules) == count
        assert tuple(record.module.path for record in facts.inspection.modules) == (
            tuple(module.path for module in semantic.modules)
        )
        assert tuple(record.position for record in facts.inspection.modules) == (
            tuple(range(count))
        )
        assert all(
            record.asset is asset
            for record, asset in zip(
                facts.inspection.modules,
                _layered(semantic).module_assets,
                strict=True,
            )
        )

    empty = _semantic_project(tmp_path / "empty", {"zero.pietto": "\n"})
    empty_facts = _inspection(empty)
    assert len(empty_facts.inspection.modules) == 1
    assert empty_facts.inspection.modules[0].declarations == ()


def test_inspection_covers_every_declaration_in_catalog_and_source_order(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _SHAPE_PREFIX,
            "b.pietto": _query_module("    select:\n        id\n"),
        },
    )
    facts = _inspection(semantic)
    assets = _layered(semantic).declaration_assets
    projected = tuple(
        declaration
        for record in facts.inspection.modules
        for declaration in record.declarations
    )
    assert len(projected) == len(assets)
    assert all(
        declaration.asset is asset
        for declaration, asset in zip(projected, assets, strict=True)
    )
    assert tuple(
        (declaration.identity.module_path, declaration.declaration_position)
        for declaration in projected
    ) == (
        ("a.pietto", 0),
        ("a.pietto", 1),
        ("b.pietto", 0),
        ("b.pietto", 1),
        ("b.pietto", 2),
    )


def test_module_digest_is_reached_through_slice13_without_reread_or_rehash(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, {"main.pietto": _SHAPE_PREFIX})
    record = _record(semantic, "main.pietto")
    asset = _layered(semantic).module_assets[0]
    snapshot = semantic.trusted_source_snapshots[0]

    assert record.digest is asset.digest
    assert record.digest.digest == snapshot.sha256
    assert record.digest.byte_count == snapshot.byte_count
    assert (
        record.digest.algorithm
        is layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES
    )
    decoded = _decoded(semantic)
    assert f"digest=s:{snapshot.sha256}" in decoded
    assert snapshot.source_text not in decoded


def test_byte_equal_modules_share_one_digest_identity_and_remain_distinct(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    first = _record(semantic, "a.pietto")
    second = _record(semantic, "b.pietto")

    assert first.digest == second.digest
    assert first.digest is not second.digest
    assert first.module != second.module
    assert first.position == 0
    assert second.position == 1
    decoded = _decoded(semantic)
    assert decoded.count(f"digest=s:{first.digest.digest}") == 2
    assert len(_layered(semantic).find_digest(first.digest)) == 2
    assert "module=i:0\tpath=s:a.pietto" in decoded
    assert "module=i:1\tpath=s:b.pietto" in decoded


def test_loader_readiness_is_recorded_as_a_fact_without_loader_behavior(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, {"main.pietto": _SHAPE_PREFIX})
    record = _record(semantic, "main.pietto")
    asset = _layered(semantic).module_assets[0]

    assert record.readiness.fact is asset.readiness
    assert record.readiness.status is layering.ProjectLayeredLoaderReadiness.READY
    assert (
        record.readiness.reason
        is layering.ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
    )
    assert record.readiness.cycles == ()
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    for forbidden in ("def load", "importlib", "exec(", "eval("):
        assert forbidden not in source


def test_module_cycle_records_blocked_readiness_and_complete_cycle_members(
    tmp_path: Path,
) -> None:
    sources = _cycle_sources()
    sources["c.pietto"] = _SHAPE_PREFIX
    semantic = _semantic_project(tmp_path, sources)

    for path in ("a.pietto", "b.pietto"):
        record = _record(semantic, path)
        assert record.readiness.status is layering.ProjectLayeredLoaderReadiness.BLOCKED
        assert (
            record.readiness.reason
            is layering.ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED
        )
        assert record.readiness.cycles
        for cycle in record.readiness.cycles:
            assert tuple(member.path for member in cycle.members) == (
                "a.pietto",
                "b.pietto",
            )
        assert record.graph.component_is_cyclic
        assert all(
            declaration.availability is layering.ProjectLayeredAvailability.BLOCKED
            for declaration in record.declarations
        )

    healthy = _record(semantic, "c.pietto")
    assert healthy.readiness.status is layering.ProjectLayeredLoaderReadiness.READY
    assert healthy.readiness.cycles == ()
    assert not healthy.graph.component_is_cyclic


def test_graph_section_records_components_dependency_targets_and_evidence(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    base = _record(semantic, "base.pietto")
    main = _record(semantic, "main.pietto")

    assert tuple(member.path for member in base.graph.component_members) == (
        "base.pietto",
    )
    assert base.graph.dependency_targets == ()
    assert base.graph.import_evidence == ()
    assert tuple(target.path for target in main.graph.dependency_targets) == (
        "base.pietto",
    )
    assert tuple(
        (
            evidence.target.path,
            evidence.module_statement_position,
            evidence.item_position,
        )
        for evidence in main.graph.import_evidence
    ) == (("base.pietto", 0, 0), ("base.pietto", 0, 1))


def test_import_section_keeps_local_aliases_separate_from_nominal_ownership(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    main = _record(semantic, "main.pietto")
    assert len(main.imports) == 2

    aliased = main.imports[1]
    assert aliased.local_name == "r"
    assert aliased.exported_name == "rows"
    assert aliased.target_module_path == "base.pietto"
    assert aliased.resolved_target is not None
    assert aliased.resolved_target.declared_name == "rows"
    assert aliased.resolved_target.module_path == "base.pietto"
    assert aliased.issue_statuses == ()
    bindings = semantic.module_bindings
    assert bindings is not None
    assert aliased.request is bindings.environments[1].requests[1]

    unresolved = _semantic_project(
        tmp_path / "unresolved",
        {"main.pietto": 'import "missing.pietto":\n    shape Row\n'},
    )
    request = _record(unresolved, "main.pietto").imports[0]
    assert request.resolved_target is None
    assert request.issue_statuses
    assert _record(unresolved, "main.pietto").exports == ()


def test_unresolvable_upstream_text_is_inspected_verbatim_without_revalidation(
    tmp_path: Path,
) -> None:
    # Upstream deliberately retains an unresolvable or empty decoded target and
    # reports it through its own issue facts, so the inspection must project the
    # text verbatim rather than re-validate its content.
    semantic = _semantic_project(
        tmp_path,
        {"main.pietto": 'import "":\n    shape Row\n'},
    )
    record = _record(semantic, "main.pietto")
    assert len(record.imports) == 1
    projected = record.imports[0]
    assert projected.target_module_path == ""
    assert projected.exported_name == "Row"
    assert projected.resolved_target is None
    assert tuple(status.value for status in projected.issue_statuses) == (
        "unresolved_target_module",
    )
    assert record.declarations == ()
    assert record.origins == ()

    decoded = _decoded(semantic)
    assert "\ttarget_module_path=s:\texported_name=s:Row\t" in decoded
    assert "status=e:unresolved_target_module" in decoded
    assert "family=e:graph\tstatus=s:unresolved_target_module" in decoded


def test_export_section_records_requests_entries_origins_and_issue_buckets(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    base = _record(semantic, "base.pietto")
    assert len(base.exports) == 2
    first = base.exports[0]
    assert first.local_name == "Row"
    assert first.exposed_name == "Row"
    assert first.entry_origin is not None
    assert first.target_identity is not None
    assert first.target_identity.module_path == "base.pietto"
    assert first.issue_statuses == ()

    unresolved = _semantic_project(
        tmp_path / "unresolved",
        {"main.pietto": "export:\n    shape Missing\n"},
    )
    request = _record(unresolved, "main.pietto").exports[0]
    assert request.exposed_name is None
    assert request.entry_origin is None
    assert request.target_identity is None
    assert request.issue_statuses


def test_repeated_nominal_identity_is_ambiguous_with_a_complete_bucket(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": _SHAPE_PREFIX
            + "table t:\n    from rows\n    select:\n        id\n"
            + "table t:\n    from rows\n    select:\n        id\n"
        },
    )
    bucket = tuple(
        declaration
        for declaration in _record(semantic, "main.pietto").declarations
        if declaration.identity.declared_name == "t"
    )
    assert len(bucket) == 2
    assert all(
        declaration.availability is layering.ProjectLayeredAvailability.AMBIGUOUS
        for declaration in bucket
    )
    assert all(declaration.relation_status is None for declaration in bucket)
    assert all(declaration.occurrence_count == 2 for declaration in bucket)
    assert tuple(declaration.occurrence_index for declaration in bucket) == (0, 1)
    assert bucket[0].identity == bucket[1].identity
    assert bucket[0].identity.declared_name == "t"
    assert len(_inspection(semantic).find_declaration(bucket[0].identity)) == 2


def test_identity_distinct_occurrences_preserve_multiplicity_and_position(
    tmp_path: Path,
) -> None:
    for count in (1, 2, 3):
        body = "".join(
            "table t:\n    from rows\n    select:\n        id\n" for _ in range(count)
        )
        semantic = _semantic_project(
            tmp_path / f"project{count}",
            {"main.pietto": _SHAPE_PREFIX + body},
        )
        bucket = tuple(
            declaration
            for declaration in _record(semantic, "main.pietto").declarations
            if declaration.identity.declared_name == "t"
        )
        assert len(bucket) == count
        assert all(declaration.occurrence_count == count for declaration in bucket)
        assert tuple(declaration.occurrence_index for declaration in bucket) == (
            tuple(range(count))
        )
        assert tuple(
            declaration.declaration_position for declaration in bucket
        ) == tuple(range(2, 2 + count))


def test_relation_declaration_states_concrete_unknown_deferred_and_blocked(
    tmp_path: Path,
) -> None:
    cases = (
        (
            "concrete",
            _query_module("    select:\n        id\n"),
            ProjectRelationRowSchemaStatus.CONCRETE,
        ),
        (
            "unknown",
            _query_module("    select:\n        nope\n"),
            ProjectRelationRowSchemaStatus.UNKNOWN,
        ),
        (
            "deferred",
            _SHAPE_PREFIX + "query pending:\n    from rows\n    select:\n"
            "        divided = amount / 2\n"
            "query result:\n    from pending\n    select:\n        divided\n",
            ProjectRelationRowSchemaStatus.DEFERRED,
        ),
        (
            "blocked",
            _SHAPE_PREFIX
            + "query result:\n    from missing\n    select:\n        id\n",
            ProjectRelationRowSchemaStatus.BLOCKED,
        ),
    )
    for name, source, expected in cases:
        semantic = _semantic_project(tmp_path / name, {"main.pietto": source})
        declaration = _declaration(semantic, "main.pietto", "result")
        asset = declaration.asset
        assert asset.relation_state is not None
        assert declaration.relation_status is expected
        assert declaration.relation_reason is asset.relation_state.reason
        assert declaration.availability.value == expected.value
        if expected is ProjectRelationRowSchemaStatus.CONCRETE:
            assert tuple(item.name for item in declaration.row_fields) == ("id",)
        else:
            assert declaration.row_fields == ()


def test_non_relation_declaration_is_absent_rather_than_unknown(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, {"main.pietto": _SHAPE_PREFIX})
    declaration = _declaration(semantic, "main.pietto", "Row")
    assert declaration.availability is layering.ProjectLayeredAvailability.ABSENT
    assert declaration.relation_status is None
    assert declaration.relation_reason is None
    assert declaration.row_fields == ()
    assert "availability=e:absent" in _decoded(semantic)


def test_origin_section_records_local_and_imported_paths_with_exact_hops(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    main = _record(semantic, "main.pietto")
    local = tuple(
        origin
        for origin in main.origins
        if origin.binding
        is inspection_module.ProjectInspectionBinding.LOCAL_DECLARATION
    )
    imported = tuple(
        origin
        for origin in main.origins
        if origin.binding is inspection_module.ProjectInspectionBinding.IMPORTED_BINDING
    )
    assert tuple(origin.local_name for origin in local) == ("result",)
    assert tuple(origin.local_name for origin in imported) == ("Row", "r")

    alias = imported[1]
    assert alias.local_name == "r"
    assert alias.target_module_path == "base.pietto"
    assert alias.target_declared_name == "rows"
    assert len(alias.hops) == 1
    hop = alias.hops[0]
    assert hop.import_exported_name == "rows"
    assert hop.facade_module_path == "base.pietto"
    assert hop.facade_exposed_name == "rows"
    assert hop.target_identity.declared_name == "rows"
    assert all(origin.path is not None for origin in main.origins)


def test_dependency_and_row_lineage_sections_preserve_exact_identities(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    main = _record(semantic, "main.pietto")
    attribution = semantic.module_attribution_facts
    assert attribution is not None

    expected = tuple(
        fact
        for fact in attribution.dependencies
        if fact.reference.owner.identity.module_path == "main.pietto"
    )
    assert tuple(item.fact for item in main.dependencies) == expected
    assert all(
        (item.target_declaration is None) != (item.target_row_field is None)
        for item in main.dependencies
    )

    lineages = tuple(
        lineage
        for lineage in attribution.row_lineages
        if lineage.owner.identity.module_path == "main.pietto"
    )
    assert tuple(item.lineage for item in main.row_lineage) == lineages
    projected = main.row_lineage[0]
    assert projected.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert tuple(item.name for item in projected.fields) == ("id", "amount")
    for field_lineage in projected.fields:
        assert field_lineage.paths
        for path in field_lineage.paths:
            assert path.root_module_path == "base.pietto"
            assert path.hops


def test_type_source_and_relation_resolution_sections_are_complete(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    base = _record(semantic, "base.pietto")
    main = _record(semantic, "main.pietto")
    type_source = semantic.module_type_source_resolutions
    relations = semantic.module_relation_resolutions
    assert type_source is not None
    assert relations is not None

    base_environment = type_source.find_module_path("base.pietto")[0]
    assert tuple(item.resolution for item in base.type_resolutions) == (
        base_environment.type_resolutions
    )
    assert tuple(item.resolution for item in base.source_shape_resolutions) == (
        base_environment.source_shape_resolutions
    )
    assert base.source_shape_resolutions[0].target_identity.declared_name == "Row"

    main_environment = relations.find_module_path("main.pietto")[0]
    assert tuple(item.resolution for item in main.relation_resolutions) == (
        main_environment.resolutions
    )
    assert main.relation_resolutions[0].local_name == "r"
    assert main.relation_resolutions[0].target_identity.declared_name == "rows"


def test_semantic_fact_section_preserves_ordinals_names_and_states(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": _SHAPE_PREFIX + "query result:\n    from rows\n    select:\n"
            "        id\n        doubled = amount * 2\n"
        },
    )
    record = _record(semantic, "main.pietto")
    preservation = semantic.module_semantic_facts
    assert preservation is not None
    environment = preservation.find_module_path("main.pietto")[0]
    assert tuple(item.facts for item in record.semantic_facts) == (
        environment.relation_facts
    )
    result_facts = record.semantic_facts[-1]
    assert tuple(
        (item.selected_output_ordinal, item.output_name)
        for item in result_facts.selects
    ) == ((0, "id"), (1, "doubled"))
    assert result_facts.status is result_facts.facts.state.status
    assert result_facts.reason is result_facts.facts.state.reason
    assert result_facts.window_outputs == ()
    assert result_facts.let_bindings == ()


def test_issue_section_preserves_every_family_status_without_a_winner(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _cycle_sources())
    record = _record(semantic, "a.pietto")
    families = tuple(issue.family for issue in record.issues)
    assert inspection_module.ProjectInspectionIssueFamily.GRAPH in families
    assert inspection_module.ProjectInspectionIssueFamily.TYPE_SOURCE in families
    assert inspection_module.ProjectInspectionIssueFamily.RELATION in families
    assert families == tuple(sorted(families, key=_family_rank))
    assert all(issue.status for issue in record.issues)

    ambiguous = _semantic_project(
        tmp_path / "ambiguous",
        {
            "main.pietto": _SHAPE_PREFIX
            + "table t:\n    from rows\n    select:\n        id\n"
            + "table t:\n    from rows\n    select:\n        id\n"
        },
    )
    statuses = tuple(issue.status for issue in _record(ambiguous, "main.pietto").issues)
    assert "ambiguous_local_relation_name" in statuses


def test_inspection_indexes_are_derived_and_return_complete_buckets(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    facts = _inspection(semantic)
    assert len(facts.find_module(ProjectModuleIdentity(path="a.pietto"))) == 1
    assert facts.find_module(ProjectModuleIdentity(path="missing.pietto")) == ()
    with pytest.raises(TypeError, match="module lookup"):
        facts.find_module("a.pietto")  # pyright: ignore[reportArgumentType]

    declaration = _declaration(semantic, "a.pietto", "Row")
    assert facts.find_declaration(declaration.identity) == (declaration,)
    other = _declaration(semantic, "b.pietto", "Row")
    assert facts.find_declaration(other.identity) == (other,)
    assert declaration.identity != other.identity
    with pytest.raises(TypeError, match="declaration lookup"):
        facts.find_declaration("Row")  # pyright: ignore[reportArgumentType]


def test_canonical_bytes_declare_the_private_format_and_end_with_one_newline(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    payload = _inspection(semantic).canonical_bytes

    assert type(payload) is bytes
    assert payload.decode("utf-8").encode("utf-8") == payload
    assert not payload.startswith(b"\xef\xbb\xbf")
    assert payload.endswith(b"\n")
    assert not payload.endswith(b"\n\n")
    assert payload.count(b"\r") == 0
    text = payload.decode("utf-8")
    assert text.splitlines()[0] == (
        "inspection\tformat=e:pietto.module-inspection.v1\tmodules=i:2"
    )
    assert text.splitlines()[1] == (
        "owner\tkind=e:local_project_root\tnamespace=s:\tname=s:"
    )


def test_canonical_bytes_encode_every_inspection_record_deterministically(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(
        tmp_path,
        {
            "base.pietto": _facade_sources()["base.pietto"],
            "main.pietto": _facade_sources()["main.pietto"],
            "cycle_a.pietto": _cycle_sources()["a.pietto"].replace(
                "b.pietto", "cycle_b.pietto"
            ),
            "cycle_b.pietto": _cycle_sources()["b.pietto"].replace(
                "a.pietto", "cycle_a.pietto"
            ),
        },
    )
    facts = _inspection(semantic)
    lines = facts.canonical_bytes.decode("utf-8").splitlines()
    assert len(lines) == _expected_record_count(facts.inspection)
    for line in lines:
        parts = line.split("\t")
        assert parts[0] in _RECORD_KINDS
        for part in parts[1:]:
            key, separator, token = part.partition("=")
            assert separator == "="
            assert key and key.replace("_", "").isalnum()
            assert token.startswith(_TOKEN_TAGS)
            if token.startswith("i:"):
                assert token[2:].isdigit()
                assert token[2:] == str(int(token[2:]))
            if token.startswith("b:"):
                assert token[2:] in ("true", "false")
            if token == "n:":
                continue
    rebuilt = _build_inspection(semantic)
    assert rebuilt.canonical_bytes == facts.canonical_bytes
    assert rebuilt.canonical_bytes is not facts.canonical_bytes


def test_canonical_bytes_are_identical_across_processes_and_hash_seeds(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path, _facade_sources())
    semantic = _semantic_project(tmp_path, _facade_sources())
    expected = hashlib.sha256(_inspection(semantic).canonical_bytes).hexdigest()

    script = (
        "import hashlib\n"
        "import sys\n"
        "from pathlib import Path\n"
        "import pietto._project.check as project_check\n"
        "from pietto._project.model import build_empty_project_semantic_result\n"
        "result = build_empty_project_semantic_result(\n"
        "    project_check.check_project_parse_only(Path(sys.argv[1]))\n"
        ")\n"
        "facts = result.module_inspection_facts\n"
        "assert facts is not None\n"
        "sys.stdout.write(hashlib.sha256(facts.canonical_bytes).hexdigest())\n"
    )
    package_root = str(Path(pietto.__file__).resolve().parents[1])
    observed = set()
    for seed in ("0", "1", "4294967295"):
        environment = dict(os.environ)
        environment["PYTHONHASHSEED"] = seed
        environment["PYTHONPATH"] = package_root
        completed = subprocess.run(
            [sys.executable, "-c", script, str(root)],
            check=True,
            text=True,
            capture_output=True,
            env=environment,
        )
        observed.add(completed.stdout)
    assert observed == {expected}


def test_canonical_bytes_are_stable_under_non_authoritative_mapping_order(
    tmp_path: Path,
) -> None:
    sources = _facade_sources()
    forward = _semantic_project(tmp_path / "forward", sources)
    reversed_root = tmp_path / "reversed"
    reversed_root.mkdir(parents=True, exist_ok=True)
    reversed_sources = {name: sources[name] for name in reversed(tuple(sources.keys()))}
    backward = _semantic_project(reversed_root, reversed_sources)

    assert tuple(sources.keys()) != tuple(reversed_sources.keys())
    assert _inspection(forward).canonical_bytes == _inspection(backward).canonical_bytes
    assert _inspection(forward).inspection == _inspection(backward).inspection


def test_canonical_bytes_change_with_identity_order_multiplicity_or_state(
    tmp_path: Path,
) -> None:
    baseline = _inspection(
        _semantic_project(
            tmp_path / "baseline",
            {
                "a.pietto": _SHAPE_PREFIX,
                "b.pietto": _query_module("    select:\n        id\n"),
            },
        )
    ).canonical_bytes
    renamed = _inspection(
        _semantic_project(
            tmp_path / "renamed",
            {
                "a.pietto": _SHAPE_PREFIX,
                "c.pietto": _query_module("    select:\n        id\n"),
            },
        )
    ).canonical_bytes
    reordered = _inspection(
        _semantic_project(
            tmp_path / "reordered",
            {
                "a.pietto": _query_module("    select:\n        id\n"),
                "b.pietto": (_SHAPE_PREFIX),
            },
        )
    ).canonical_bytes
    duplicated = _inspection(
        _semantic_project(
            tmp_path / "duplicated",
            {
                "a.pietto": _SHAPE_PREFIX,
                "b.pietto": _query_module("    select:\n        id\n")
                + "query result2:\n    from rows\n    select:\n        id\n",
            },
        )
    ).canonical_bytes
    unknown = _inspection(
        _semantic_project(
            tmp_path / "unknown",
            {
                "a.pietto": _SHAPE_PREFIX,
                "b.pietto": _query_module("    select:\n        nope\n"),
            },
        )
    ).canonical_bytes

    assert len({baseline, renamed, reordered, duplicated, unknown}) == 5


def test_canonical_bytes_change_with_a_replaced_digest_or_readiness_fact(
    tmp_path: Path,
) -> None:
    baseline = _inspection(
        _semantic_project(tmp_path / "baseline", {"a.pietto": _SHAPE_PREFIX})
    ).canonical_bytes
    rewritten = _inspection(
        _semantic_project(tmp_path / "rewritten", {"a.pietto": _SHAPE_PREFIX + "\n"})
    ).canonical_bytes
    assert baseline != rewritten
    assert b"byte_count=i:" in baseline

    acyclic = _inspection(
        _semantic_project(
            tmp_path / "acyclic",
            {
                "a.pietto": "export:\n    shape T\nshape T:\n    id: Int\n",
                "b.pietto": 'import "a.pietto":\n    shape T\n',
            },
        )
    ).canonical_bytes
    cyclic = _inspection(
        _semantic_project(tmp_path / "cyclic", _cycle_sources())
    ).canonical_bytes
    assert b"status=e:ready" in acyclic
    assert b"status=e:blocked" in cyclic
    assert b"readiness_cycle_member" not in acyclic
    assert b"readiness_cycle_member" in cyclic


def test_canonical_bytes_escape_control_characters_and_stay_utf8_exact(
    tmp_path: Path,
) -> None:
    escape = inspection_module._escape
    assert escape("plain") == "plain"
    assert escape("a\\b") == "a\\\\b"
    assert escape("a\tb") == "a\\tb"
    assert escape("a\nb") == "a\\nb"
    assert escape("a\rb") == "a\\rb"
    assert escape("a\x00b") == "a\\x00b"
    assert escape("a\x1fb") == "a\\x1fb"
    assert escape("a\x7fb") == "a\\x7fb"
    assert escape("é模") == "é模"
    assert inspection_module._text("n:") == "s:n:"
    assert inspection_module._integer(0) == "i:0"
    assert inspection_module._integer(12) == "i:12"
    assert inspection_module._boolean(True) == "b:true"
    assert inspection_module._optional_text(None) == "n:"
    assert inspection_module._optional_integer(None) == "n:"
    assert inspection_module._optional_enumeration(None) == "n:"
    with pytest.raises(ValueError, match="non-negative integer"):
        inspection_module._integer(-1)
    with pytest.raises(ValueError, match="non-negative integer"):
        inspection_module._integer(True)
    with pytest.raises(TypeError, match="must be text"):
        inspection_module._text(1)  # pyright: ignore[reportArgumentType]

    semantic = _semantic_project(tmp_path, {"模块.pietto": _SHAPE_PREFIX})
    payload = _inspection(semantic).canonical_bytes
    assert "path=s:模块.pietto" in payload.decode("utf-8")
    assert payload.decode("utf-8").encode("utf-8") == payload


def test_inspection_exposes_no_host_path_inode_address_or_runtime_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    semantic = _semantic_project(root, _facade_sources())
    decoded = _decoded(semantic)

    assert str(root) not in decoded
    assert str(root.resolve()) not in decoded
    assert str(REPO_ROOT) not in decoded
    assert "0x" not in decoded
    for forbidden in (
        "canonical_path",
        "invocation_path",
        "symlink_target",
        "inode",
        "device",
        "mtime",
        "ctime",
        "source_text",
        "object at",
    ):
        assert forbidden not in decoded
    pinned_root = semantic.pinned_root
    assert pinned_root is not None
    assert str(pinned_root.canonical_path) not in decoded

    def _walk(value: object, depth: int) -> None:
        assert depth < 16
        if isinstance(value, (str, int, bool, bytes)) or value is None:
            return
        if isinstance(value, tuple):
            for item in value:
                _walk(item, depth + 1)
            return
        assert not isinstance(value, Path)
        if hasattr(type(value), "__dataclass_fields__"):
            for item in fields(value):  # pyright: ignore[reportArgumentType]
                if item.compare:
                    _walk(getattr(value, item.name), depth + 1)

    _walk(_inspection(semantic).inspection, 0)


def test_forged_canonical_payload_and_grafted_inspection_are_rejected(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path / "one", _facade_sources())
    foreign = _semantic_project(tmp_path / "two", _facade_sources())
    facts = _inspection(semantic)

    forged = bytes(bytearray(facts.canonical_bytes))
    assert forged == facts.canonical_bytes
    assert forged is not facts.canonical_bytes
    with pytest.raises(ValueError, match="exact derived canonical bytes"):
        replace(facts, canonical_bytes=forged)
    with pytest.raises(ValueError, match="exact derived canonical bytes"):
        replace(facts, canonical_bytes=_inspection(foreign).canonical_bytes)
    with pytest.raises(ValueError, match="exact derived projection"):
        replace(facts, inspection=_inspection(foreign).inspection)

    projection = facts.inspection
    with pytest.raises(ValueError, match="exact derived projection"):
        replace(facts, inspection=replace(projection))
    with pytest.raises(ValueError, match="selected-input order"):
        replace(projection, modules=tuple(reversed(projection.modules)))
    with pytest.raises(ValueError, match="exact private format marker"):
        replace(
            projection,
            format=None,  # pyright: ignore[reportArgumentType]
        )


def test_eleventh_sidecar_all_or_none_boundary_is_exact_and_fail_closed(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, {"main.pietto": _SHAPE_PREFIX})
    sidecar_names = (
        "module_catalogs",
        "module_exports",
        "module_bindings",
        "module_graph",
        "module_diagnostic_facts",
        "module_type_source_resolutions",
        "module_relation_resolutions",
        "module_semantic_facts",
        "module_attribution_facts",
        "module_package_identity_facts",
        "module_inspection_facts",
    )
    assert len(sidecar_names) == 11
    assert all(getattr(semantic, name) is not None for name in sidecar_names)
    for name in sidecar_names:
        with pytest.raises(ValueError, match="require all module sidecars"):
            replace(semantic, **{name: None})
    empty = replace(semantic, **{name: None for name in sidecar_names}, diagnostics=())
    assert empty.module_inspection_facts is None
    with pytest.raises(TypeError, match="exact inspection fact set"):
        replace(
            semantic,
            module_inspection_facts=object(),  # pyright: ignore[reportArgumentType]
        )


def test_inspection_builder_is_pure_over_preloaded_roots_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    expected = _inspection(semantic)
    builder_source = inspect.getsource(
        inspection_module._build_project_module_inspection_fact_set
    )
    serializer_source = inspect.getsource(inspection_module._serialize_inspection)
    assert "open" not in builder_source
    assert "Path" not in builder_source
    assert "open" not in serializer_source

    def _refuse(*arguments: object, **keywords: object) -> object:
        raise AssertionError("the inspection builder must perform no input or output")

    monkeypatch.setattr("builtins.open", _refuse)
    monkeypatch.setattr(Path, "open", _refuse)
    monkeypatch.setattr(Path, "read_text", _refuse)
    monkeypatch.setattr(Path, "read_bytes", _refuse)
    monkeypatch.setattr(os, "open", _refuse)
    monkeypatch.setattr(os, "listdir", _refuse)

    rebuilt = _build_inspection(semantic)
    assert rebuilt.canonical_bytes == expected.canonical_bytes
    assert rebuilt.inspection == expected.inspection


def test_slice13_and_earlier_products_remain_independent_and_unchanged(
    tmp_path: Path,
) -> None:
    semantic = _semantic_project(tmp_path, _facade_sources())
    layered = semantic.module_package_identity_facts
    attribution = semantic.module_attribution_facts
    preservation = semantic.module_semantic_facts
    assert layered is not None
    assert attribution is not None
    assert preservation is not None

    assert not hasattr(layered, "module_inspection_facts")
    assert not hasattr(attribution, "module_inspection_facts")
    assert not hasattr(preservation, "module_inspection_facts")
    for relative in (
        "src/pietto/_project/module_package_neutral_identity.py",
        "src/pietto/_project/module_attribution.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/module_relation_resolution.py",
        "src/pietto/_project/module_resolution.py",
        "src/pietto/_project/module_graph.py",
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "module_inspection" not in source
    assert layered.declaration_assets == layered.authority.declaration_assets
    assert layered.module_assets is layered.authority.module_assets


def test_schema_v2_public_api_cli_json_ir_sql_dependencies_and_goldens_unchanged(
    tmp_path: Path,
) -> None:
    parse_result = project_check.check_project_parse_only(
        _configured_project(tmp_path, _facade_sources())
    )
    encoded = json.dumps(
        project_check_result_to_json_dict(parse_result), sort_keys=True
    )
    for forbidden in (
        "module_inspection_facts",
        "inspection",
        "canonical_bytes",
        "module-inspection",
    ):
        assert forbidden not in encoded

    package_init = (REPO_ROOT / "src/pietto/_project/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "module_inspection" not in package_init
    for relative in (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/__init__.py",
    ):
        assert "module_inspection" not in (REPO_ROOT / relative).read_text(
            encoding="utf-8"
        )

    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == "0.1.0"
    assert pyproject["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").iterdir()
        if path.is_file()
    )
    assert len(generated) == 8
    goldens = tuple(
        path
        for path in (REPO_ROOT / "tests/fixtures/golden").iterdir()
        if path.is_file()
    )
    assert len(goldens) == 37

    module = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    test_nodes = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert tuple(node.name for node in test_nodes) == EXPECTED_TEST_NAMES
    assert len(EXPECTED_TEST_NAMES) == 41
    assert all(not node.decorator_list for node in test_nodes)
