"""Phase 54 Slice 15 Rust-ready pure boundaries and differential vectors."""

from __future__ import annotations

import ast
from dataclasses import replace
from enum import StrEnum
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import _pietto_differential_harness as harness
import _pietto_differential_vectors as vectors
import pietto
import pietto._project.check as project_check
import pietto._project.module_attribution as attribution_module
import pietto._project.module_bindings as bindings_module
import pietto._project.module_exports as exports_module
import pietto._project.module_graph as graph_module
import pietto._project.module_inspection as inspection_module
import pietto._project.module_package_neutral_identity as layering
import pietto._project.module_pure_boundary as pure_boundary
import pietto._project.module_relation_resolution as relation_module
import pietto._project.module_resolution as resolution_module
import pietto._project.module_semantic_fact_preservation as preservation_module
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectSemanticResult,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice15-rust-ready-pure-boundaries-differential-vectors-"
    "and-end-to-end-hardening-v1.md"
)
PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
SOURCE_REL = "src/pietto/_project/module_pure_boundary.py"
INSPECTION_REL = "src/pietto/_project/module_inspection.py"
HARNESS_REL = "tests/_pietto_differential_harness.py"
VECTORS_REL = "tests/_pietto_differential_vectors.py"
TEST_REL = "tests/test_phase54_rust_ready_pure_boundaries_differential_vectors.py"

EXPECTED_TEST_NAMES = (
    "test_slice15_contract_status_active_manifest_and_allowlist_are_exact",
    "test_slice15_plan_readme_and_specification_status_lines_are_exact",
    "test_pure_boundary_module_is_private_with_an_empty_export_surface",
    "test_pure_boundary_source_performs_no_input_output_or_ambient_lookup",
    "test_declared_record_kinds_are_the_exact_thirty_four_slice14_kinds",
    "test_declared_key_orders_match_the_real_canonical_payload_exactly",
    "test_declared_enumeration_vocabularies_equal_the_live_enumerations",
    "test_declared_scope_chains_and_child_counts_are_internally_consistent",
    "test_declared_ordinal_rules_match_the_projection_emission_rules",
    "test_declared_section_order_matches_the_canonical_projection_order",
    "test_token_encoding_covers_every_declared_tag_exactly",
    "test_escaping_covers_control_characters_delete_and_backslash",
    "test_escaping_covers_the_complete_surrogate_range_and_stays_utf8",
    "test_canonical_payload_always_ends_with_exactly_one_newline",
    "test_integer_payloads_are_canonical_non_negative_decimal",
    "test_production_serializer_evaluates_the_portable_pure_boundary",
    "test_canonical_bytes_of_real_projects_reproduce_through_the_pure_boundary",
    "test_projected_document_carries_no_python_enumeration_or_object_identity",
    "test_canonical_bytes_remain_exact_for_every_bootstrap_fixture",
    "test_forged_payload_and_grafted_projection_remain_rejected",
    "test_pure_evaluation_has_no_ambient_dependency",
    "test_pure_evaluation_is_total_and_deterministic_for_admitted_inputs",
    "test_repeated_processes_and_hash_seeds_produce_identical_corpus_digests",
    "test_available_supported_interpreters_agree_on_the_corpus_digest",
    "test_pure_evaluation_ignores_working_directory_and_environment",
    "test_every_rejection_status_is_reachable_and_normalized",
    "test_rejections_carry_no_payload_and_no_supplied_content",
    "test_portable_value_carriers_reject_non_primitive_payloads",
    "test_portable_outcome_atomicity_is_enforced",
    "test_invalid_documents_never_raise_from_the_portable_boundary",
    "test_vector_corpus_covers_the_frozen_property_matrix",
    "test_vector_corpus_exercises_every_declared_record_kind",
    "test_vector_purposes_match_the_documents_they_label",
    "test_vector_identities_are_unique_deterministic_and_lowercase",
    "test_vector_corpus_is_deterministically_ordered_across_rebuilds",
    "test_vector_expected_outputs_are_stored_literals",
    "test_vector_expected_outputs_are_not_silently_regenerated",
    "test_vectors_contain_no_host_path_address_or_timestamp",
    "test_harness_fails_closed_on_malformed_vectors",
    "test_harness_fails_closed_on_duplicate_vector_identities",
    "test_harness_reports_a_concise_machine_readable_summary",
    "test_harness_authoring_mode_proposes_without_writing",
    "test_harness_and_production_are_not_the_same_implementation_path",
    "test_record_level_corruption_fails_closed_and_content_only_moves_bytes",
    "test_document_validation_visits_each_record_exactly_once",
    "test_repeated_identity_buckets_remain_bounded_and_linear",
    "test_end_to_end_root_integrity_fails_closed_before_the_portable_boundary",
    "test_all_or_none_sidecar_boundary_and_schema_v1_remain_exact",
    "test_no_public_api_cli_json_package_ir_sql_rust_or_build_expansion_occurs",
    "test_retained_rust_and_slice16_boundaries_remain_unimplemented",
)

_SHAPE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    category: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
)

_SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


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


def _facade_sources() -> dict[str, str]:
    return {
        "base.pietto": (_SHAPE_PREFIX + "export:\n    shape Row\n    source rows\n"),
        "main.pietto": (
            'import "base.pietto":\n    shape Row\n    source rows as r\n'
            "query result:\n    from r\n    select:\n        id\n        amount\n"
        ),
    }


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


_RICH_QUERY = (
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


def _alias_chain_sources() -> dict[str, str]:
    return {
        "base.pietto": "type Years = Int\nexport:\n    type Years\n",
        "mid.pietto": (
            'import "base.pietto":\n    type Years\ntype Age = Years\n'
            "export:\n    type Age\n"
        ),
        "leaf.pietto": (
            'import "mid.pietto":\n    type Age\nshape Person:\n    age: Age\n'
        ),
    }


def _bootstrap_fixtures() -> dict[str, dict[str, str]]:
    """Return fixtures whose union exercises every declared record kind."""

    return {
        "single": {"main.pietto": _SHAPE_PREFIX},
        "facade": _facade_sources(),
        "cycle": _cycle_sources(),
        "collision": {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
        "non_ascii": {"模块é.pietto": _SHAPE_PREFIX},
        "rich": {"rich.pietto": _SHAPE_PREFIX + "query rich:\n" + _RICH_QUERY},
        "alias_chain": _alias_chain_sources(),
        "unresolved_import": {"a.pietto": 'import "missing.pietto":\n    shape Nope\n'},
        "ambiguous_export": {
            "a.pietto": (
                "shape Row:\n    id: Int\nshape Row:\n    id: Int\n"
                "export:\n    shape Row\n"
            )
        },
    }


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _corpus_digest() -> str:
    report = harness.run_corpus(vectors.differential_vectors())
    payload = "\n".join(
        f"{result.vector_id}:{result.observed_status.value}:{result.matched}"
        for result in report.results
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_SUBPROCESS_DIGEST_SCRIPT = (
    "import hashlib\n"
    "import sys\n"
    "import _pietto_differential_harness as harness\n"
    "import _pietto_differential_vectors as vectors\n"
    "report = harness.run_corpus(vectors.differential_vectors())\n"
    "payload = '\\n'.join(\n"
    "    f'{r.vector_id}:{r.observed_status.value}:{r.matched}'\n"
    "    for r in report.results\n"
    ")\n"
    "sys.stdout.write(hashlib.sha256(payload.encode('utf-8')).hexdigest())\n"
)


def _subprocess_digest(executable: str, seed: str = "0") -> str:
    package_root = str(Path(pietto.__file__).resolve().parents[1])
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONPATH"] = os.pathsep.join(
        (package_root, str(REPO_ROOT / "tests"))
    )
    completed = subprocess.run(
        [executable, "-c", _SUBPROCESS_DIGEST_SCRIPT],
        check=True,
        text=True,
        capture_output=True,
        env=environment,
        cwd=str(REPO_ROOT.parent),
    )
    return completed.stdout


def test_slice15_contract_status_active_manifest_and_allowlist_are_exact() -> None:
    """Lock the Slice 15 contract, the active Gate manifest, and the allowlist."""

    spec = _read(SPEC_REL)
    for phrase in (
        "Phase 54 Slice 15",
        "Rust-ready Pure Boundaries",
        "Narrowest Sufficient Pure Boundary",
        "pietto.module-inspection.v1",
        "pietto.differential-vectors.v1",
        "no production Rust",
    ):
        assert phrase in spec

    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == "PHASE54_SLICE15_GATE2"
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "93f0f591e28a01f32d1698fcd4b8c57d41c6d714"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BRANCH == (
        "phase54/slice15-rust-ready-pure-boundaries"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_SUBJECT == (
        "Add Phase 54 Rust-ready pure boundaries"
    )
    added = active_gate2_manifest.ADDED_PATHS
    assert added == {SPEC_REL, SOURCE_REL, HARNESS_REL, VECTORS_REL, TEST_REL}
    assert INSPECTION_REL in active_gate2_manifest.NON_READER_MODIFIED_PATHS
    assert not (
        active_gate2_manifest.ADDED_PATHS
        & active_gate2_manifest.MECHANICAL_READER_PATHS
    )


def test_slice15_plan_readme_and_specification_status_lines_are_exact() -> None:
    """Lock the Slice 15 status text in the plan, README, and specification."""

    plan = _read(PLAN_REL)
    readme = _read("README.md")
    language_spec = _read("docs/spec/pietto-v0.9.md")
    for document in (plan, readme, language_spec):
        assert "Slice 15" in document
    assert "Rust-ready pure boundaries" in plan
    assert "differential vectors" in plan
    assert "Slice 16" in plan
    assert "0.1.0" in readme


def test_pure_boundary_module_is_private_with_an_empty_export_surface() -> None:
    """The portable boundary stays private and exports nothing."""

    assert pure_boundary.__all__ == ()
    assert "module_pure_boundary" not in _read("src/pietto/_project/__init__.py")
    for relative in (
        "src/pietto/__init__.py",
        "src/pietto/cli.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/ir/__init__.py",
        "src/pietto/sql/__init__.py",
    ):
        assert "module_pure_boundary" not in _read(relative)


def test_pure_boundary_source_performs_no_input_output_or_ambient_lookup() -> None:
    """No ambient dependency may appear in the portable boundary source."""

    source = _read(SOURCE_REL)
    for forbidden in (
        "os.environ",
        "os.getcwd",
        "os.getpid",
        "time.time",
        "random.",
        "socket.",
        "subprocess.",
        "importlib.",
        "hashlib.",
        "pathlib.",
        "read_text",
        "read_bytes",
        "exec(",
        "id(",
        "repr(",
    ):
        assert forbidden not in source
    tree = ast.parse(source)
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported == {
        "__future__",
        "collections.abc",
        "dataclasses",
        "enum",
        "types",
    }
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Import)]
    assert not [node for node in ast.walk(tree) if isinstance(node, ast.Global)]


def test_declared_record_kinds_are_the_exact_thirty_four_slice14_kinds() -> None:
    """The declared schema covers exactly the thirty-four Slice 14 kinds."""

    kinds = pure_boundary.PURE_RECORD_KINDS
    assert len(kinds) == 34
    assert len(set(kinds)) == 34
    assert set(kinds) == set(pure_boundary.PURE_RECORD_SCHEMA)
    assert kinds[0] == "inspection"
    assert kinds[1] == "owner"
    assert kinds[2] == "module"
    slice14_contract = _read(
        "docs/spec/phase54-slice14-private-module-inspection-and-canonical-"
        "serialization-v1.md"
    )
    for kind in kinds:
        assert f"`{kind}`" in slice14_contract


def test_declared_key_orders_match_the_real_canonical_payload_exactly(
    tmp_path: Path,
) -> None:
    """Every real record's kind and key order equals its declared schema entry."""

    observed: set[str] = set()
    for name, sources in _bootstrap_fixtures().items():
        semantic = _semantic_project(tmp_path / name, sources)
        payload = _inspection(semantic).canonical_bytes.decode("utf-8")
        for line in payload.split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            specification = pure_boundary.PURE_RECORD_SCHEMA[parts[0]]
            observed.add(parts[0])
            keys = tuple(pair.split("=", 1)[0] for pair in parts[1:])
            assert keys == tuple(item.key for item in specification.keys)
    assert observed == set(pure_boundary.PURE_RECORD_KINDS)
    assert len(observed) == 34


def test_declared_enumeration_vocabularies_equal_the_live_enumerations() -> None:
    """Every frozen portable vocabulary equals its live Python enumeration."""

    live: dict[str, type[StrEnum]] = {
        "owner_kind": layering.ProjectLayeredOwnerKind,
        "digest_algorithm": layering.ProjectLayeredDigestAlgorithm,
        "loader_readiness": layering.ProjectLayeredLoaderReadiness,
        "loader_readiness_reason": layering.ProjectLayeredLoaderReadinessReason,
        "symbol_namespace": ProjectSymbolNamespace,
        "symbol_kind": ProjectSymbolKind,
        "binding_issue_status": bindings_module.ProjectModuleBindingIssueStatus,
        "export_entry_origin": exports_module.ProjectModuleExportEntryOrigin,
        "export_issue_status": exports_module.ProjectModuleExportIssueStatus,
        "layered_availability": layering.ProjectLayeredAvailability,
        "row_field_nullability": inspection_module.ProjectRowFieldNullability,
        "row_result_role": inspection_module.ProjectRowResultRole,
        "relation_row_status": inspection_module.ProjectRelationRowSchemaStatus,
        "relation_row_reason": inspection_module.ProjectRelationRowSchemaReason,
        "inspection_binding": inspection_module.ProjectInspectionBinding,
        "dependency_kind": attribution_module.ProjectModuleDependencyKind,
        "reference_role": attribution_module.ProjectModuleReferenceRole,
        "row_field_kind": attribution_module.ProjectModuleRowFieldKind,
        "projection_kind": attribution_module.ProjectModuleProjectionKind,
        "type_reference_role": resolution_module.ProjectModuleTypeReferenceRole,
        "resolved_type_kind": inspection_module.ProjectResolvedTypeKind,
        "candidate_bucket_status": (
            preservation_module.ProjectModuleCandidateBucketStatus
        ),
        "inspection_issue_family": inspection_module.ProjectInspectionIssueFamily,
    }
    # A record kind whose own carrier admits only part of an enumeration
    # declares that exact subset, in the enumeration's own member order.
    narrowed: dict[str, tuple[type[StrEnum], tuple[str, ...]]] = {
        "clause_dependency_role": (
            preservation_module.ProjectModuleFactOccurrenceRole,
            ("group_key", "satisfying", "grouped_order"),
        ),
        "window_output_status": (
            preservation_module.ProjectModuleCandidateBucketStatus,
            ("concrete", "unknown", "deferred", "blocked"),
        ),
        "lineage_field_kind": (
            attribution_module.ProjectModuleRowFieldKind,
            ("source_field", "relation_output"),
        ),
    }
    assert not set(live) & set(narrowed)
    assert set(live) | set(narrowed) == set(pure_boundary.PURE_ENUMERATION_VOCABULARIES)
    for name, enumeration in live.items():
        declared = pure_boundary.PURE_ENUMERATION_VOCABULARIES[name]
        assert declared == tuple(member.value for member in enumeration)
    preservation_source = _read(
        "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for name, (enumeration, subset) in narrowed.items():
        declared = pure_boundary.PURE_ENUMERATION_VOCABULARIES[name]
        members = tuple(member.value for member in enumeration)
        assert declared == subset
        assert set(declared) < set(members)
        assert declared == tuple(value for value in members if value in set(declared))
    attribution_source = _read("src/pietto/_project/module_attribution.py")
    assert "Relation lineage fields must belong to its owner." in attribution_source
    assert "Clause dependency has an invalid role." in preservation_source
    assert (
        "A syntactic window output cannot be absent or ambiguous."
        in preservation_source
    )
    assert pure_boundary.PURE_DOCUMENT_FORMAT_MARKER == (
        inspection_module.ProjectInspectionFormat.MODULE_INSPECTION_V1.value
    )
    families = {
        "graph": graph_module.ProjectModuleGraphIssueStatus,
        "type_source": resolution_module.ProjectTypeSourceResolutionIssueStatus,
        "relation": relation_module.ProjectModuleRelationResolutionIssueStatus,
    }
    assert set(families) == set(
        pure_boundary.PURE_ENUMERATION_VOCABULARIES["inspection_issue_family"]
    )


def test_declared_scope_chains_and_child_counts_are_internally_consistent() -> None:
    """Parent chains, ordinal keys, and declared child counts stay coherent."""

    schema = pure_boundary.PURE_RECORD_SCHEMA
    for kind, specification in schema.items():
        assert specification.kind == kind
        if specification.parent is not None:
            assert specification.parent in schema
            assert schema[specification.parent].is_scope
        chain: list[str] = []
        walker = specification.parent
        while walker is not None:
            ancestor = schema[walker]
            if ancestor.ordinal_key is not None:
                chain.append(ancestor.ordinal_key)
            walker = ancestor.parent
        assert tuple(reversed(chain)) == specification.parent_ordinal_keys
        declared = tuple(item.key for item in specification.keys)
        for parent_key in specification.parent_ordinal_keys:
            assert parent_key in declared
        if specification.ordinal_key is not None:
            assert specification.ordinal_key in declared
        for count_key, child_kind in specification.counts:
            assert count_key in declared
            assert schema[child_kind].parent == kind
            assert specification.is_scope
        if specification.singleton:
            assert specification.ordinal_key is None


def test_declared_ordinal_rules_match_the_projection_emission_rules() -> None:
    """Every ordinal is dense, and the catalog invariant proves it."""

    schema = pure_boundary.PURE_RECORD_SCHEMA
    ordinal_kinds = {
        kind
        for kind, specification in schema.items()
        if specification.ordinal_key is not None
    }
    assert len(ordinal_kinds) == 29
    assert "module" in ordinal_kinds
    assert "declaration" in ordinal_kinds
    assert not hasattr(schema["declaration"], "dense")
    singletons = {
        kind for kind, specification in schema.items() if specification.singleton
    }
    assert singletons == {"inspection", "owner", "digest", "readiness", "graph"}
    assert not (ordinal_kinds & singletons)
    ruled = {
        kind for kind, specification in schema.items() if specification.state_rules
    }
    assert ruled == {
        "declaration",
        "declaration_row_field",
        "dependency",
        "digest",
        "export",
        "graph",
        "graph_component_member",
        "graph_dependency_target",
        "graph_import_evidence",
        "import",
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
        "semantic_facts",
        "semantic_let_binding",
        "semantic_select",
        "semantic_window_output",
        "source_shape_resolution",
        "type_resolution",
        "type_resolution_alias",
    }
    shapes = {
        rule.rule
        for specification in schema.values()
        for rule in specification.state_rules
    }
    assert shapes == set(pure_boundary._PureStateKind)
    scoped = {
        kind for kind, specification in schema.items() if specification.scope_rules
    }
    assert scoped == {
        "declaration",
        "declaration_row_field",
        "dependency",
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
        "readiness_cycle_member",
        "relation_resolution",
        "row_lineage",
        "row_lineage_field",
        "row_lineage_hop",
        "row_lineage_path",
        "semantic_clause_dependency",
        "semantic_facts",
        "semantic_window_output",
        "source_shape_resolution",
        "type_resolution",
        "type_resolution_alias",
    }
    scope_shapes = {
        rule.rule
        for specification in schema.values()
        for rule in specification.scope_rules
    }
    assert scope_shapes == set(pure_boundary._PureScopeKind)
    for specification in schema.values():
        for rule in specification.scope_rules:
            assert rule.at in ("any", "first", "last")
            if rule.rule in (
                pure_boundary._PureScopeKind.ANCESTOR_EQUAL,
                pure_boundary._PureScopeKind.ANCESTOR_COMBINATION,
            ):
                assert rule.scope in schema and schema[rule.scope].is_scope
            if rule.rule is pure_boundary._PureScopeKind.SCOPE_CONTAINS_ANCESTOR:
                assert schema[rule.child].parent == specification.kind
    graph_order = next(rule.order for rule in schema["issue"].scope_rules if rule.order)
    assert graph_order == tuple(
        member.value for member in graph_module.ProjectModuleGraphIssueStatus
    )
    assert "tuple(ProjectModuleGraphIssueStatus).index(issue.status)" in _read(
        "src/pietto/_project/module_graph.py"
    )
    exports_source = _read("src/pietto/_project/module_exports.py")
    ordered = next(
        rule.order for rule in schema["export_issue"].scope_rules if rule.order
    )
    for rank, status in enumerate(ordered):
        member = status.upper()
        assert f"ProjectModuleExportIssueStatus.{member}: {rank}," in exports_source
    assert len(ordered) == len(exports_module.ProjectModuleExportIssueStatus)
    catalog_source = _read("src/pietto/_project/module_catalog.py")
    assert "occurrence.declaration_position != position" in catalog_source
    inspection_source = _read(INSPECTION_REL)
    assert "complete ordered Slice 13 declaration " in inspection_source


def test_declared_section_order_matches_the_canonical_projection_order(
    tmp_path: Path,
) -> None:
    """Section and sibling order in a real payload never decreases."""

    schema = pure_boundary.PURE_RECORD_SCHEMA
    semantic = _semantic_project(tmp_path, _facade_sources())
    payload = _inspection(semantic).canonical_bytes.decode("utf-8")
    last_module_order = -1
    for line in payload.split("\n"):
        if not line:
            continue
        kind = line.split("\t", 1)[0]
        specification = schema[kind]
        if specification.parent != "module":
            if kind == "module":
                last_module_order = -1
            continue
        assert specification.child_order >= last_module_order
        last_module_order = specification.child_order


def test_token_encoding_covers_every_declared_tag_exactly() -> None:
    """Each portable tag renders exactly one canonical token form."""

    encode = pure_boundary.encode_pure_value
    assert encode(pure_boundary.pure_text("value")) == "s:value"
    assert encode(pure_boundary.pure_enumeration("concrete")) == "e:concrete"
    assert encode(pure_boundary.pure_integer(0)) == "i:0"
    assert encode(pure_boundary.pure_integer(1024)) == "i:1024"
    assert encode(pure_boundary.pure_boolean(True)) == "b:true"
    assert encode(pure_boundary.pure_boolean(False)) == "b:false"
    assert encode(pure_boundary.PURE_ABSENT) == "n:"
    assert len(pure_boundary.ProjectPureTag) == 5
    assert tuple(member.value for member in pure_boundary.ProjectPureTag) == (
        "s",
        "i",
        "b",
        "e",
        "n",
    )


def test_escaping_covers_control_characters_delete_and_backslash() -> None:
    """Escaping is total over control characters, tab, newline, and DEL."""

    escape = pure_boundary.escape_pure_text
    assert escape("plain") == "plain"
    assert escape("a\\b") == "a\\\\b"
    assert escape("a\tb") == "a\\tb"
    assert escape("a\nb") == "a\\nb"
    assert escape("a\rb") == "a\\rb"
    assert escape("a\x00b") == "a\\x00b"
    assert escape("a\x1fb") == "a\\x1fb"
    assert escape("a\x7fb") == "a\\x7fb"
    assert escape("é模") == "é模"
    for codepoint in range(0x20):
        rendered = escape(chr(codepoint))
        assert rendered != chr(codepoint)
        assert "\t" not in rendered and "\n" not in rendered


def test_escaping_covers_the_complete_surrogate_range_and_stays_utf8() -> None:
    """Every surrogate code point escapes and the payload always encodes."""

    escape = pure_boundary.escape_pure_text
    for codepoint in (0xD800, 0xDC00, 0xDCFF, 0xDFFF):
        rendered = escape(chr(codepoint))
        assert rendered == f"\\u{codepoint:04x}"
        assert rendered.encode("utf-8")
    document = vectors.differential_vectors()
    surrogate = next(
        vector
        for vector in document
        if vector.purpose is harness.DifferentialPurpose.SURROGATE_TEXT
    )
    outcome = pure_boundary.evaluate_pure_document(surrogate.document)
    assert outcome.status is pure_boundary.ProjectPureStatus.OK
    assert outcome.canonical_bytes is not None
    assert b"\\udcff" in outcome.canonical_bytes
    assert outcome.canonical_bytes.decode("utf-8").encode("utf-8") == (
        outcome.canonical_bytes
    )


def test_canonical_payload_always_ends_with_exactly_one_newline() -> None:
    """Every accepted payload is non-empty and ends with exactly one newline."""

    for vector in vectors.differential_vectors():
        if vector.expected_status is not pure_boundary.ProjectPureStatus.OK:
            continue
        payload = vector.expected_bytes
        assert payload is not None
        assert payload
        assert payload.endswith(b"\n")
        assert not payload.endswith(b"\n\n")
        assert payload.count(b"\n") == len(vector.document.records)


def test_integer_payloads_are_canonical_non_negative_decimal() -> None:
    """Integers render without a sign and without a leading zero."""

    encode = pure_boundary.encode_pure_value
    for value in (0, 1, 9, 10, 4294967295):
        rendered = encode(pure_boundary.pure_integer(value))
        assert rendered == f"i:{value}"
        assert not rendered.startswith("i:-")
        digits = rendered[2:]
        assert digits == str(int(digits))
    with pytest.raises(ValueError, match="non-negative"):
        encode(pure_boundary.pure_integer(-1))


def test_production_serializer_evaluates_the_portable_pure_boundary() -> None:
    """The production serializer routes through the same portable boundary."""

    source = inspect.getsource(inspection_module._serialize_inspection)
    assert "evaluate_pure_document" in source
    assert "_project_pure_document" in source
    assert "open" not in source
    projection = inspect.getsource(inspection_module._project_pure_document)
    assert "ProjectPureDocument" in projection
    assert "open" not in projection
    inspection_source = _read(INSPECTION_REL)
    assert "module_pure_boundary" in inspection_source
    assert "def _escape" not in inspection_source


def test_canonical_bytes_of_real_projects_reproduce_through_the_pure_boundary(
    tmp_path: Path,
) -> None:
    """A settled inspection re-evaluates to its exact published canonical bytes."""

    for name, sources in _bootstrap_fixtures().items():
        semantic = _semantic_project(tmp_path / name, sources)
        facts = _inspection(semantic)
        document = inspection_module._project_pure_document(facts.inspection)
        outcome = pure_boundary.evaluate_pure_document(document)
        assert outcome.status is pure_boundary.ProjectPureStatus.OK
        assert outcome.canonical_bytes == facts.canonical_bytes


def test_projected_document_carries_no_python_enumeration_or_object_identity(
    tmp_path: Path,
) -> None:
    """Portable values carry declared text, never a Python enumeration member."""

    semantic = _semantic_project(tmp_path, _facade_sources())
    document = inspection_module._project_pure_document(
        _inspection(semantic).inspection
    )
    for record in document.records:
        assert type(record.kind) is str
        for field in record.fields:
            assert type(field.key) is str
            value = field.value
            assert type(value) is pure_boundary.ProjectPureValue
            assert value.text is None or type(value.text) is str
            assert value.integer is None or type(value.integer) is int
            assert value.boolean is None or type(value.boolean) is bool
            assert not isinstance(value.text, StrEnum)


def test_canonical_bytes_remain_exact_for_every_bootstrap_fixture(
    tmp_path: Path,
) -> None:
    """Repeated construction of one project yields byte-identical payloads."""

    for name, sources in _bootstrap_fixtures().items():
        first = _inspection(_semantic_project(tmp_path / f"{name}_1", sources))
        second = _inspection(_semantic_project(tmp_path / f"{name}_2", sources))
        assert first.canonical_bytes == second.canonical_bytes
        assert first.inspection == second.inspection


def test_forged_payload_and_grafted_projection_remain_rejected(
    tmp_path: Path,
) -> None:
    """A forged payload or projection is refused by exact object identity."""

    semantic = _semantic_project(tmp_path, _facade_sources())
    facts = _inspection(semantic)
    forged = bytes(bytearray(facts.canonical_bytes))
    assert forged == facts.canonical_bytes
    assert forged is not facts.canonical_bytes
    with pytest.raises(ValueError, match="exact derived canonical bytes"):
        inspection_module.ProjectModuleInspectionFactSet(
            inspection=facts.inspection,
            canonical_bytes=forged,
            authority=facts.authority,
        )
    other = _inspection(_semantic_project(tmp_path / "other", _facade_sources()))
    with pytest.raises(ValueError, match="exact derived projection"):
        inspection_module.ProjectModuleInspectionFactSet(
            inspection=other.inspection,
            canonical_bytes=facts.canonical_bytes,
            authority=facts.authority,
        )


def test_pure_evaluation_has_no_ambient_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Evaluation performs no input, output, or ambient state lookup."""

    def _refuse(*arguments: object, **keywords: object) -> object:
        raise AssertionError("the portable boundary must perform no ambient lookup")

    monkeypatch.setattr("builtins.open", _refuse)
    monkeypatch.setattr(Path, "open", _refuse)
    monkeypatch.setattr(Path, "read_text", _refuse)
    monkeypatch.setattr(Path, "read_bytes", _refuse)
    monkeypatch.setattr(os, "getcwd", _refuse)
    monkeypatch.setattr(os, "listdir", _refuse)
    monkeypatch.setattr(os, "urandom", _refuse)
    report = harness.run_corpus(vectors.differential_vectors())
    assert report.failed == ()
    assert report.matched == report.total


def test_pure_evaluation_is_total_and_deterministic_for_admitted_inputs() -> None:
    """Every admitted document evaluates identically on repeated calls."""

    corpus = vectors.differential_vectors()
    for vector in corpus:
        first = pure_boundary.evaluate_pure_document(vector.document)
        second = pure_boundary.evaluate_pure_document(vector.document)
        assert first == second
        assert first.status is second.status
        assert first.canonical_bytes == second.canonical_bytes
    assert harness.run_corpus(corpus).failed == ()
    assert harness.run_corpus(corpus).summary() == (
        harness.run_corpus(corpus).summary()
    )


def test_repeated_processes_and_hash_seeds_produce_identical_corpus_digests() -> None:
    """The corpus digest is invariant across processes and hash seeds."""

    expected = _corpus_digest()
    observed = {
        _subprocess_digest(sys.executable, seed) for seed in ("0", "1", "4294967295")
    }
    assert observed == {expected}


def test_available_supported_interpreters_agree_on_the_corpus_digest() -> None:
    """Every discoverable supported interpreter reports the same digest."""

    assert sys.version_info[:2] in _SUPPORTED_INTERPRETERS
    digests = {_corpus_digest(), _subprocess_digest(sys.executable)}
    for major, minor in _SUPPORTED_INTERPRETERS:
        candidate = shutil.which(f"python{major}.{minor}")
        if candidate is None:
            continue
        probe = subprocess.run(
            [candidate, "-c", "import sys; print(sys.version_info[:2])"],
            check=False,
            text=True,
            capture_output=True,
        )
        if probe.returncode != 0:
            continue
        digests.add(_subprocess_digest(candidate))
    assert len(digests) == 1


def test_pure_evaluation_ignores_working_directory_and_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Neither the working directory nor the environment changes any result."""

    baseline = _corpus_digest()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("LANG", "C")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("PIETTO_UNUSED_PROBE", "1")
    assert _corpus_digest() == baseline


def test_every_rejection_status_is_reachable_and_normalized() -> None:
    """Every declared rejection status is exercised by the frozen corpus."""

    statuses = {
        vector.expected_status
        for vector in vectors.differential_vectors()
        if vector.expected_status is not pure_boundary.ProjectPureStatus.OK
    }
    declared = set(pure_boundary.ProjectPureStatus) - {
        pure_boundary.ProjectPureStatus.OK
    }
    assert statuses == declared
    assert len(declared) == 25


def test_rejections_carry_no_payload_and_no_supplied_content() -> None:
    """A rejection reports coordinates only and never echoes supplied data."""

    for vector in vectors.differential_vectors():
        outcome = pure_boundary.evaluate_pure_document(vector.document)
        if outcome.status is pure_boundary.ProjectPureStatus.OK:
            continue
        assert outcome.canonical_bytes is None
        assert set(vars(pure_boundary.ProjectPureOutcome).keys()) >= {"__slots__"}
        fields = (outcome.record_position, outcome.field_position)
        for coordinate in fields:
            assert coordinate is None or type(coordinate) is int
        rendered = (
            f"{outcome.status.value}|{outcome.record_position}|{outcome.field_position}"
        )
        assert "pietto" not in rendered
        assert "/" not in rendered


def test_portable_value_carriers_reject_non_primitive_payloads() -> None:
    """Carrier construction admits exact primitive payloads only."""

    with pytest.raises(TypeError, match="exact tag"):
        pure_boundary.ProjectPureValue(tag="s")  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="must be text"):
        pure_boundary.pure_text(1)  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="must be an integer"):
        pure_boundary.pure_integer(True)
    with pytest.raises(TypeError, match="must be a boolean"):
        pure_boundary.pure_boolean(1)  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="must be text"):
        pure_boundary.pure_enumeration(
            inspection_module.ProjectInspectionBinding.LOCAL_DECLARATION  # pyright: ignore[reportArgumentType]
        )
    with pytest.raises(TypeError, match="exact portable value"):
        pure_boundary.ProjectPureField(key="k", value="v")  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="exact portable fields"):
        pure_boundary.ProjectPureRecord(kind="module", fields=("x",))  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="exact portable records"):
        pure_boundary.ProjectPureDocument(records=("x",))  # pyright: ignore[reportArgumentType]


def test_portable_outcome_atomicity_is_enforced() -> None:
    """An outcome's status, payload, and coordinates stay one atomic tuple."""

    with pytest.raises(ValueError, match="carries its payload"):
        pure_boundary.ProjectPureOutcome(status=pure_boundary.ProjectPureStatus.OK)
    with pytest.raises(ValueError, match="carries no coordinate"):
        pure_boundary.ProjectPureOutcome(
            status=pure_boundary.ProjectPureStatus.OK,
            canonical_bytes=b"x\n",
            record_position=0,
        )
    with pytest.raises(ValueError, match="carries no payload"):
        pure_boundary.ProjectPureOutcome(
            status=pure_boundary.ProjectPureStatus.EMPTY_DOCUMENT,
            canonical_bytes=b"x\n",
        )
    with pytest.raises(ValueError, match="requires its record coordinate"):
        pure_boundary.ProjectPureOutcome(
            status=pure_boundary.ProjectPureStatus.FIELD_KEY_MISMATCH,
            field_position=1,
        )


def test_invalid_documents_never_raise_from_the_portable_boundary() -> None:
    """A well-typed but invalid document always returns a normalized rejection."""

    documents = [vector.document for vector in vectors.differential_vectors()]
    documents.append(pure_boundary.ProjectPureDocument())
    documents.append(
        pure_boundary.ProjectPureDocument(
            records=(pure_boundary.ProjectPureRecord(kind="unknown"),)
        )
    )
    for document in documents:
        outcome = pure_boundary.evaluate_pure_document(document)
        assert type(outcome) is pure_boundary.ProjectPureOutcome
        assert type(outcome.status) is pure_boundary.ProjectPureStatus
    # A value a rule looks up in a collected ledger is the shape most likely to
    # escape as an exception rather than a rejection, so every text field of
    # every accepted document is replaced by one that appears nowhere.
    foreign = "foreign.pietto"
    swept = 0
    for _purpose, document in vectors._accepted_document_map().values():
        for position, record in enumerate(document.records):
            for index, field in enumerate(record.fields):
                if field.value.tag is not pure_boundary.ProjectPureTag.TEXT:
                    continue
                fields = list(record.fields)
                fields[index] = replace(field, value=pure_boundary.pure_text(foreign))
                records = list(document.records)
                records[position] = replace(record, fields=tuple(fields))
                mutated = replace(document, records=tuple(records))
                outcome = pure_boundary.evaluate_pure_document(mutated)
                assert type(outcome.status) is pure_boundary.ProjectPureStatus
                swept += 1
    assert swept == 848


def test_vector_corpus_covers_the_frozen_property_matrix() -> None:
    """Every frozen property dimension has at least one vector."""

    corpus = vectors.differential_vectors()
    purposes = {vector.purpose for vector in corpus}
    assert purposes == set(harness.DifferentialPurpose)
    accepted = tuple(
        vector
        for vector in corpus
        if vector.classification
        is harness.DifferentialClassification.PORTABLE_EVALUATION
    )
    rejected = tuple(
        vector
        for vector in corpus
        if vector.classification
        is harness.DifferentialClassification.PORTABLE_REJECTION
    )
    assert len(corpus) >= 40
    assert len(accepted) >= 16
    assert len(rejected) >= 24
    assert len(pure_boundary.PURE_MAX_INTEGER.__class__.__mro__) >= 1
    assert pure_boundary.PURE_MAX_INTEGER == 2**63 - 1
    assert len(accepted) + len(rejected) == len(corpus)
    assert set(harness.DifferentialClassification) == {
        harness.DifferentialClassification.PORTABLE_EVALUATION,
        harness.DifferentialClassification.PORTABLE_REJECTION,
    }


def test_vector_corpus_exercises_every_declared_record_kind() -> None:
    """No declared record kind may go unexercised by the accepted vectors."""

    exercised = {
        record.kind
        for vector in vectors.differential_vectors()
        if vector.classification
        is harness.DifferentialClassification.PORTABLE_EVALUATION
        for record in vector.document.records
    }
    assert exercised == set(pure_boundary.PURE_RECORD_SCHEMA)
    assert len(exercised) == 34
    optional_keys = {
        (kind, item.key)
        for kind, specification in pure_boundary.PURE_RECORD_SCHEMA.items()
        for item in specification.keys
        if item.optional
    }
    absent = {
        (record.kind, field.key)
        for vector in vectors.differential_vectors()
        for record in vector.document.records
        for field in record.fields
        if field.value.tag is pure_boundary.ProjectPureTag.ABSENT
    }
    assert optional_keys <= absent


def test_vector_purposes_match_the_documents_they_label() -> None:
    """A vector's declared purpose must describe what its document contains."""

    corpus = {vector.vector_id: vector for vector in vectors.differential_vectors()}

    def _texts(vector_id: str) -> tuple[str, ...]:
        return tuple(
            field.value.text or ""
            for record in corpus[vector_id].document.records
            for field in record.fields
            if field.value.tag is pure_boundary.ProjectPureTag.TEXT
        )

    def _kinds(vector_id: str) -> set[str]:
        return {record.kind for record in corpus[vector_id].document.records}

    assert any("\udcff" in text for text in _texts("surrogate_text"))
    assert any("\t" in text for text in _texts("control_character_text"))
    assert any("模" in text for text in _texts("non_ascii_text"))
    assert {"readiness_cycle", "readiness_cycle_member"} <= _kinds(
        "module_cycle_and_blocked_readiness"
    )
    assert {"source_shape_resolution", "relation_resolution"} <= _kinds(
        "resolution_sections"
    )
    assert {"origin", "origin_hop"} <= _kinds("explicit_reexport")
    assert {"row_lineage_hop"} <= _kinds("direct_and_renamed_lineage")
    assert {"type_resolution_alias"} <= _kinds("type_alias_chain")
    assert "callable" in {
        field.value.text
        for record in corpus["same_spelling_distinct_namespaces"].document.records
        for field in record.fields
        if field.value.tag is pure_boundary.ProjectPureTag.ENUMERATION
    }


def test_vector_identities_are_unique_deterministic_and_lowercase() -> None:
    """Vector identifiers are unique, stable, and private lowercase text."""

    corpus = vectors.differential_vectors()
    identifiers = tuple(vector.vector_id for vector in corpus)
    assert len(set(identifiers)) == len(identifiers)
    for identifier in identifiers:
        assert identifier
        assert identifier == identifier.lower()
        assert set(identifier) <= set("abcdefghijklmnopqrstuvwxyz0123456789_")
    assert identifiers == tuple(
        vector.vector_id for vector in vectors.differential_vectors()
    )


def test_vector_corpus_is_deterministically_ordered_across_rebuilds() -> None:
    """Rebuilding the corpus yields exactly the same order and expectations."""

    first = vectors.differential_vectors()
    second = vectors.differential_vectors()
    assert len(first) == len(second)
    for left, right in zip(first, second, strict=True):
        assert left.vector_id == right.vector_id
        assert left.expected_status is right.expected_status
        assert left.expected_bytes == right.expected_bytes
        assert left.document == right.document


def test_vector_expected_outputs_are_stored_literals() -> None:
    """Expected payloads are reviewed byte literals, not derived at run time."""

    tree = ast.parse(_read(VECTORS_REL))
    stored: ast.Dict | None = None
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "_EXPECTED_CANONICAL_BYTES_LITERAL":
                assert isinstance(node.value, ast.Dict)
                stored = node.value
    assert stored is not None
    assert stored.keys
    for key, value in zip(stored.keys, stored.values, strict=True):
        assert isinstance(key, ast.Constant)
        assert isinstance(key.value, str)
        assert isinstance(value, ast.Constant)
        assert isinstance(value.value, bytes)
    accepted = tuple(
        vector
        for vector in vectors.differential_vectors()
        if vector.expected_status is pure_boundary.ProjectPureStatus.OK
    )
    assert len(stored.keys) == len(accepted)
    with pytest.raises(TypeError):
        vectors.EXPECTED_CANONICAL_BYTES["forged"] = b"x\n"  # pyright: ignore[reportIndexIssue]


def test_vector_expected_outputs_are_not_silently_regenerated() -> None:
    """A disagreeing stored expectation is reported, never repaired."""

    corpus = list(vectors.differential_vectors())
    target = next(
        index
        for index, vector in enumerate(corpus)
        if vector.expected_status is pure_boundary.ProjectPureStatus.OK
    )
    original = corpus[target]
    assert original.expected_bytes is not None
    corpus[target] = replace(original, expected_bytes=original.expected_bytes + b"x\n")
    report = harness.run_corpus(tuple(corpus))
    assert len(report.failed) == 1
    assert report.failed[0].vector_id == original.vector_id
    assert report.failed[0].detail == "canonical_bytes"
    proposals = harness.propose_expected_updates(tuple(corpus))
    assert len(proposals) == 1
    assert original.vector_id in proposals[0]

    # A rejection whose coordinates disagree is a real authoring disagreement,
    # so the authoring path must propose for it too.
    shifted = list(vectors.differential_vectors())
    index = next(
        position
        for position, vector in enumerate(shifted)
        if vector.expected_record_position is not None
    )
    moved = shifted[index]
    moved_position = moved.expected_record_position
    assert moved_position is not None
    shifted[index] = replace(moved, expected_record_position=moved_position + 5)
    report = harness.run_corpus(tuple(shifted))
    assert [result.detail for result in report.failed] == ["record_position"]
    coordinate_proposals = harness.propose_expected_updates(tuple(shifted))
    assert len(coordinate_proposals) == 1
    assert moved.vector_id in coordinate_proposals[0]
    assert harness.run_corpus(vectors.differential_vectors()).failed == ()


def test_vectors_contain_no_host_path_address_or_timestamp() -> None:
    """No vector or expected payload leaks host, address, or clock state."""

    source = _read(VECTORS_REL)
    for forbidden in (
        "/home/",
        "/tmp/",
        "C:\\",
        "0x7f",
        "id(",
        "datetime",
        "time.time",
        "getenv",
        "environ",
        "subprocess",
    ):
        assert forbidden not in source
    for vector in vectors.differential_vectors():
        payload = vector.expected_bytes or b""
        decoded = payload.decode("utf-8")
        assert "/home/" not in decoded
        assert not decoded.startswith("/")
        for record in vector.document.records:
            for field in record.fields:
                text = field.value.text
                if text is None:
                    continue
                assert not text.startswith("/")
                assert "\\x00" not in repr(text) or "\x00" in text


def test_harness_fails_closed_on_malformed_vectors() -> None:
    """A malformed vector is refused rather than silently skipped."""

    valid = vectors.differential_vectors()[0]
    bad_format = replace(valid, vector_format="pietto.differential-vectors.v0")
    assert harness.validate_vector(bad_format)
    with pytest.raises(harness.DifferentialVectorError, match="malformed"):
        harness.validate_corpus((bad_format,))
    accepted = next(
        vector
        for vector in vectors.differential_vectors()
        if vector.expected_status is pure_boundary.ProjectPureStatus.OK
    )
    with pytest.raises(harness.DifferentialVectorError, match="malformed"):
        harness.validate_corpus((replace(accepted, expected_bytes=None),))
    with pytest.raises(harness.DifferentialVectorError, match="malformed"):
        harness.validate_corpus((replace(accepted, expected_record_position=1),))
    rejected = next(
        vector
        for vector in vectors.differential_vectors()
        if vector.expected_status is not pure_boundary.ProjectPureStatus.OK
    )
    with pytest.raises(harness.DifferentialVectorError, match="malformed"):
        harness.validate_corpus((replace(rejected, expected_bytes=b"x\n"),))
    with pytest.raises(harness.DifferentialVectorError, match="must not be empty"):
        harness.validate_corpus(())
    with pytest.raises(harness.DifferentialVectorError, match="must be a tuple"):
        harness.validate_corpus([valid])  # pyright: ignore[reportArgumentType]
    with pytest.raises(harness.DifferentialVectorError, match="not text"):
        harness.validate_corpus(
            (replace(valid, vector_id=7),)  # pyright: ignore[reportArgumentType]
        )
    coordinate_free = {
        pure_boundary.ProjectPureStatus.EMPTY_DOCUMENT,
        pure_boundary.ProjectPureStatus.MISSING_HEADER_RECORD,
    }
    coordinated = next(
        vector
        for vector in vectors.differential_vectors()
        if vector.expected_status not in coordinate_free
        and vector.expected_status is not pure_boundary.ProjectPureStatus.OK
    )
    with pytest.raises(
        harness.DifferentialVectorError, match="requires a record coordinate"
    ):
        harness.validate_corpus(
            (
                replace(
                    coordinated,
                    expected_record_position=None,
                    expected_field_position=None,
                ),
            )
        )


def test_harness_fails_closed_on_duplicate_vector_identities() -> None:
    """Two vectors may never share one private identifier."""

    corpus = vectors.differential_vectors()
    with pytest.raises(harness.DifferentialVectorError, match="duplicate"):
        harness.validate_corpus((corpus[0], corpus[1], corpus[0]))
    with pytest.raises(harness.DifferentialVectorError, match="duplicate"):
        harness.run_corpus((corpus[0], corpus[0]))
    # The accepted half is declared as ordered triples rather than a mapping, so
    # a repeated identifier reaches the fail-closed check instead of being
    # folded away before the harness can ever see it.
    accepted = vectors._accepted_documents()
    assert type(accepted) is tuple
    identifiers = tuple(vector_id for vector_id, _purpose, _document in accepted)
    assert len(set(identifiers)) == len(identifiers)


def test_harness_reports_a_concise_machine_readable_summary() -> None:
    """The harness emits one deterministic machine-readable summary line."""

    report = harness.run_corpus(vectors.differential_vectors())
    summary = report.summary()
    assert summary.startswith(
        f"vector_format={harness.DIFFERENTIAL_VECTOR_FORMAT} vectors="
    )
    assert f"vectors={report.total}" in summary
    assert f"matched={report.matched}" in summary
    assert "failed=0" in summary
    assert "\n" not in summary
    assert report.total == report.matched


def test_harness_authoring_mode_proposes_without_writing() -> None:
    """The authoring mode returns a proposal and mutates no tracked file."""

    before = (REPO_ROOT / VECTORS_REL).read_bytes()
    assert harness.propose_expected_updates(vectors.differential_vectors()) == ()
    after = (REPO_ROOT / VECTORS_REL).read_bytes()
    assert before == after
    harness_source = _read(HARNESS_REL)
    for forbidden in ("write_text", "write_bytes", "open(", "os.replace", "shutil"):
        assert forbidden not in harness_source
    vectors_source = _read(VECTORS_REL)
    for forbidden in ("write_text", "write_bytes", "open("):
        assert forbidden not in vectors_source


def test_harness_and_production_are_not_the_same_implementation_path() -> None:
    """Expected values never come from the production serializer at run time."""

    harness_source = _read(HARNESS_REL)
    vectors_source = _read(VECTORS_REL)
    for source in (harness_source, vectors_source):
        assert "module_inspection" not in source
        assert "_serialize_inspection" not in source
        assert "_project_pure_document" not in source
    assert "evaluate_pure_document" in harness_source
    assert "evaluate_pure_document" not in vectors_source
    assert "EXPECTED_CANONICAL_BYTES" in vectors_source


def test_record_level_corruption_fails_closed_and_content_only_moves_bytes(
    tmp_path: Path,
) -> None:
    """A malformed stream is rejected; a different valid stream only moves bytes."""

    schema = pure_boundary.PURE_RECORD_SCHEMA
    counted = {child for item in schema.values() for _, child in item.counts}
    uncounted_sections = {
        kind
        for kind, item in schema.items()
        if item.parent == "module"
        and item.ordinal_key is not None
        and kind not in counted
    }
    semantic = _semantic_project(tmp_path, _facade_sources())
    published = _inspection(semantic).canonical_bytes
    records = inspection_module._project_pure_document(
        _inspection(semantic).inspection
    ).records
    accepted_drops = 0
    for position in range(len(records)):
        duplicated = pure_boundary.ProjectPureDocument(
            records=records[:position] + (records[position],) + records[position:]
        )
        assert (
            pure_boundary.evaluate_pure_document(duplicated).status
            is not pure_boundary.ProjectPureStatus.OK
        )
        if position + 1 < len(records):
            swapped = list(records)
            swapped[position], swapped[position + 1] = (
                swapped[position + 1],
                swapped[position],
            )
            assert (
                pure_boundary.evaluate_pure_document(
                    pure_boundary.ProjectPureDocument(records=tuple(swapped))
                ).status
                is not pure_boundary.ProjectPureStatus.OK
            )
        dropped = pure_boundary.ProjectPureDocument(
            records=records[:position] + records[position + 1 :]
        )
        outcome = pure_boundary.evaluate_pure_document(dropped)
        if outcome.status is pure_boundary.ProjectPureStatus.OK:
            # Truncating the tail of a section the Slice 14 format gives no
            # declared count is a different valid document rather than a
            # corruption, so the byte comparison against the authority detects
            # it instead. Adding a count would change the canonical bytes.
            accepted_drops += 1
            assert records[position].kind in uncounted_sections
            assert outcome.canonical_bytes != published
    assert accepted_drops


def test_document_validation_visits_each_record_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The validator performs exactly one pass over the record stream."""

    original = pure_boundary._validate_fields
    calls: list[int] = []

    def _counted(
        record: pure_boundary.ProjectPureRecord,
        specification: pure_boundary._PureKindSpec,
        record_position: int,
    ) -> pure_boundary.ProjectPureOutcome | None:
        calls.append(1)
        return original(record, specification, record_position)

    monkeypatch.setattr(pure_boundary, "_validate_fields", _counted)
    for vector in vectors.differential_vectors():
        if vector.expected_status is not pure_boundary.ProjectPureStatus.OK:
            continue
        calls.clear()
        outcome = pure_boundary.evaluate_pure_document(vector.document)
        assert outcome.status is pure_boundary.ProjectPureStatus.OK
        assert len(calls) == len(vector.document.records)


def test_repeated_identity_buckets_remain_bounded_and_linear() -> None:
    """Construction and evaluation grow linearly in the number of records."""

    def _bucket_document(size: int) -> pure_boundary.ProjectPureDocument:
        records = [
            vectors._header(1),
            vectors._OWNER,
            *vectors._module_block(0, "a.pietto"),
        ]
        records.extend(
            vectors._declaration(
                0,
                position,
                owner_name="a.pietto",
                declared_name="Row",
                availability="ambiguous",
                occurrence_count=size,
                occurrence_index=position,
            )
            for position in range(size)
        )
        # Every declaration answers to its own local origin, so the bucket grows
        # on both sides of that correspondence rather than on one.
        records.extend(
            vectors._origin(
                0,
                position,
                local_name="Row",
                target_module_path="a.pietto",
                target_declared_name="Row",
                target_declaration_position=position,
            )
            for position in range(size)
        )
        return pure_boundary.ProjectPureDocument(records=tuple(records))

    measurements: list[tuple[int, int]] = []
    for size in (4, 8, 16, 32, 64):
        document = _bucket_document(size)
        outcome = pure_boundary.evaluate_pure_document(document)
        assert outcome.status is pure_boundary.ProjectPureStatus.OK
        assert outcome.canonical_bytes is not None
        measurements.append((len(document.records), len(outcome.canonical_bytes)))
    for (records, payload), (next_records, next_payload) in zip(
        measurements, measurements[1:], strict=False
    ):
        assert next_records < 2 * records + 2
        assert next_payload < 2 * payload + 512


def test_end_to_end_root_integrity_fails_closed_before_the_portable_boundary(
    tmp_path: Path,
) -> None:
    """Foreign, value-equal, and mixed roots fail before any portable step."""

    semantic = _semantic_project(tmp_path / "one", _facade_sources())
    foreign = _semantic_project(tmp_path / "two", _facade_sources())
    facts = _inspection(semantic)
    authority = facts.authority
    for field_name in (
        "modules",
        "catalogs",
        "exports",
        "bindings",
        "graph",
        "type_source_resolutions",
        "relation_resolutions",
        "attribution",
        "semantic",
        "package_identity",
    ):
        foreign_root = getattr(_inspection(foreign).authority, field_name)
        with pytest.raises((TypeError, ValueError)):
            inspection_module._build_project_module_inspection_fact_set(
                **{
                    **{
                        name: getattr(authority, name)
                        for name in (
                            "modules",
                            "catalogs",
                            "exports",
                            "bindings",
                            "graph",
                            "type_source_resolutions",
                            "relation_resolutions",
                            "attribution",
                            "semantic",
                            "package_identity",
                        )
                    },
                    field_name: foreign_root,
                }
            )
    with pytest.raises((TypeError, ValueError)):
        inspection_module._build_project_module_inspection_fact_set(
            modules=tuple(reversed(authority.modules)),
            catalogs=authority.catalogs,
            exports=authority.exports,
            bindings=authority.bindings,
            graph=authority.graph,
            type_source_resolutions=authority.type_source_resolutions,
            relation_resolutions=authority.relation_resolutions,
            attribution=authority.attribution,
            semantic=authority.semantic,
            package_identity=authority.package_identity,
        )


def test_all_or_none_sidecar_boundary_and_schema_v1_remain_exact(
    tmp_path: Path,
) -> None:
    """Eleven sidecars stay all-or-none and schema v1 keeps no sidecar."""

    semantic = _semantic_project(tmp_path / "v2", _facade_sources())
    sidecars = (
        semantic.module_catalogs,
        semantic.module_exports,
        semantic.module_bindings,
        semantic.module_graph,
        semantic.module_diagnostic_facts,
        semantic.module_type_source_resolutions,
        semantic.module_relation_resolutions,
        semantic.module_semantic_facts,
        semantic.module_attribution_facts,
        semantic.module_package_identity_facts,
        semantic.module_inspection_facts,
    )
    assert len(sidecars) == 11
    assert all(sidecar is not None for sidecar in sidecars)
    assert semantic.model is None
    with pytest.raises(ValueError):
        replace(semantic, module_inspection_facts=None)

    legacy = _semantic_project(
        tmp_path / "v1", {"main.pietto": _SHAPE_PREFIX}, schema_version=1
    )
    assert legacy.module_inspection_facts is None
    assert legacy.module_package_identity_facts is None
    legacy_json = json.dumps(
        project_check_result_to_json_dict(
            project_check.check_project_parse_only(
                _configured_project(
                    tmp_path / "v1_json",
                    {"main.pietto": _SHAPE_PREFIX},
                    schema_version=1,
                )
            )
        ),
        sort_keys=True,
    )
    for forbidden in ("inspection", "canonical_bytes", "pure", "vector"):
        assert forbidden not in legacy_json


def test_no_public_api_cli_json_package_ir_sql_rust_or_build_expansion_occurs(
    tmp_path: Path,
) -> None:
    """No public surface, dependency, or build surface grows in this Slice."""

    parse_result = project_check.check_project_parse_only(
        _configured_project(tmp_path, _facade_sources())
    )
    encoded = json.dumps(
        project_check_result_to_json_dict(parse_result), sort_keys=True
    )
    for forbidden in (
        "pure_boundary",
        "canonical_bytes",
        "differential",
        "vector",
        "module-inspection",
    ):
        assert forbidden not in encoded
    pyproject = tomllib.loads(_read("pyproject.toml"))
    assert pyproject["project"]["version"] == "0.1.0"
    assert pyproject["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "build-dependencies" not in pyproject
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

    module = ast.parse(_read(TEST_REL))
    test_nodes = [
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    assert tuple(node.name for node in test_nodes) == EXPECTED_TEST_NAMES
    assert len(EXPECTED_TEST_NAMES) == 50
    assert all(not node.decorator_list for node in test_nodes)


def test_retained_rust_and_slice16_boundaries_remain_unimplemented() -> None:
    """No Rust, native build, or Slice 16 completion work appears here."""

    tracked = subprocess.run(
        ["git", "ls-files"],
        check=True,
        text=True,
        capture_output=True,
        cwd=str(REPO_ROOT),
    ).stdout.split("\n")
    for relative in tracked:
        assert not relative.endswith(".rs")
        assert not relative.endswith("Cargo.toml")
        assert not relative.endswith("Cargo.lock")
        assert "pyo3" not in relative.lower()
    for relative in (SOURCE_REL, HARNESS_REL, VECTORS_REL):
        source = _read(relative)
        for forbidden in ("pyo3", "cargo", "ctypes", "cffi", "wasm", "extern crate"):
            assert forbidden not in source.lower()
    spec = _read(SPEC_REL)
    for retained in (
        "Phase 68",
        "Phase 58",
        "Slice 16",
        "retained",
    ):
        assert retained in spec
