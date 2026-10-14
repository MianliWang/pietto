from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pietto
import pietto._project_explain as project_explain_package
import pietto._project_explain.compatibility_matrix_projection as matrix_projection
import pietto._project_explain.composition as composition
import pietto._project_explain.extension_catalog_evidence_projection as catalog_projection
import pietto._project_explain.json_v1 as json_v1
import pietto._project_explain.model as explain_model
import pietto._project_explain.package_requirement_projection as package_projection
import pietto._project_explain.portability_projection as portability_projection
import pietto._project_explain.runtime_builder as runtime_builder
import pietto._project_explain.text as text_projection
from pietto._project.model import ProjectConfig
from pietto._project.package_manifest import PackageManifest
from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCheckedStatus,
    ProjectExplainEvaluationState,
)
from pietto._project_explain.composition import (
    ProjectExplainArtifactReference,
    ProjectExplainPayload,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainCatalogSelectionOutcome,
)
from pietto._project_explain.json_v1 import (
    project_explain_envelope_to_json_value,
    serialize_project_explain_json_document,
)
from pietto._project_explain.model import (
    ProjectExplainDiagnostic,
    ProjectExplainEnvelope,
    ProjectExplainFormat,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainCapabilityKey,
)
from pietto._project_explain.portability_projection import (
    ProjectExplainPortabilityClassification,
    ProjectExplainPortabilityReason,
)
from pietto.errors import Severity
from pietto.semantic.capability_facts import CapabilityKey
from pietto.semantic.capability_profiles import CapabilityProfileTarget
from pietto.semantic.extension_catalog import (
    ExtensionCatalogLookupScope,
    ExtensionCatalogTarget,
)
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelector,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase58-completion-audit-phase59-handoff-v1.md"

_EXIT_CRITERIA = tuple("ABCDEFGHIJKLMNOPQRSTUVWX")

_LATER_OWNERS = {
    "Transitive local package graph": "Phase 59",
    "Cross-artifact attribution, complete provenance and lineage": "Phase 59",
    "Persistent/global graph IDs and transitive why chains": "Phase 59",
    "Advanced windows and window frames": "Phase 60",
    "Project IR and semantic composition": "Phase 61",
    "Relationship, JOIN, grain and fanout semantics": "Phase 62",
    "Multi-relation SQL, project emit-SQL and QUALIFY": "Phase 63",
    "Arrays, typmods, composites, coercion, temporal, Decimal and native mapping": (
        "Phase 64"
    ),
    "Advanced aggregation and grouping": "Phase 65",
    "Additional module and semantic-package asset kinds": "Phase 66",
    "Remote package transport and trust": "Phase 67",
    "Dependency solver, canonical lockfile and first Rust-kernel decision": (
        "Phase 68"
    ),
    "Backend/catalog expansion and extension lowering": "Phase 69",
    "Public schema/lineage expansion and v0.2 release-readiness decision": ("Phase 70"),
}

_PROJECT_EXPLAIN_MODULES = (
    explain_model,
    package_projection,
    matrix_projection,
    catalog_projection,
    portability_projection,
    composition,
    json_v1,
    runtime_builder,
    text_projection,
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )[1:]


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def test_final_identity_public_envelope_and_private_boundaries_are_exact() -> None:
    capability_fields = (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert tuple(field.name for field in fields(CapabilityKey)) == capability_fields
    assert (
        tuple(field.name for field in fields(ProjectExplainCapabilityKey))
        == capability_fields
    )
    assert tuple(
        field.name for field in fields(ExtensionSignatureRequirementSelector)
    ) == ("scope",)
    assert tuple(field.name for field in fields(ExtensionCatalogLookupScope)) == (
        "family",
        "identity",
    )
    assert tuple(field.name for field in fields(ExtensionCatalogTarget)) == (
        "database_family",
        "database_release",
        "extension_identity",
        "extension_release",
    )
    assert tuple(field.name for field in fields(CapabilityProfileTarget)) == (
        "kind",
        "family",
        "release",
        "extension_identity",
        "extension_release",
    )
    assert tuple(field.name for field in fields(ProjectExplainArtifactReference)) == (
        "kind",
        "positions",
    )

    assert ProjectExplainFormat.PROJECT_EXPLAIN_V1.value == (
        "pietto.project-explain.v1"
    )
    diagnostic = ProjectExplainDiagnostic(
        code="phase58-completion-audit",
        severity=Severity.ERROR,
        message="Completion audit checkpoint.",
        location=None,
        suggestion=None,
    )
    envelope: ProjectExplainEnvelope[ProjectExplainPayload] = ProjectExplainEnvelope(
        format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=False,
        diagnostics=(diagnostic,),
        payload=None,
    )
    value = project_explain_envelope_to_json_value(envelope)
    assert tuple(value) == ("format", "ok", "diagnostics", "payload")
    assert value["ok"] is False and value["payload"] is None
    assert serialize_project_explain_json_document(envelope).endswith(b"\n")
    assert not {"outcome", "runtime_outcome", "exit_code", "graph_id"} & value.keys()

    assert project_explain_package.__all__ == ()
    assert all(module.__all__ == () for module in _PROJECT_EXPLAIN_MODULES)
    for name in (
        "ProjectExplainEnvelope",
        "ProjectExplainPayload",
        "ProjectExplainRuntimeBuildResult",
    ):
        assert not hasattr(pietto, name)


def test_package_project_runtime_cli_and_zero_target_owners_remain_single() -> None:
    assert tuple(field.name for field in fields(PackageManifest)) == (
        "schema_version",
        "namespace",
        "name",
        "version",
        "assets",
        "dependencies",
        "capability_requirements",
    )
    assert tuple(field.name for field in fields(ProjectConfig)) == (
        "schema_version",
        "sources",
        "compilation_mode",
        "root_package",
        "capability_environment",
    )

    definitions: list[str] = []
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        definitions.extend(
            path.relative_to(REPO_ROOT).as_posix()
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_build_project_explain_runtime"
        )
    assert definitions == ["src/pietto/_project_explain/runtime_builder.py"]

    cli_path = REPO_ROOT / "src/pietto/cli.py"
    cli_tree = ast.parse(cli_path.read_text(encoding="utf-8"), filename=str(cli_path))
    runtime_calls = tuple(
        node
        for node in ast.walk(cli_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_build_project_explain_runtime"
    )
    assert len(runtime_calls) == 1

    owner_functions = {
        "test_project_package_capability_requirements.py": {
            "test_schema_one_and_two_are_valid_and_schema_one_rejects_the_new_key",
            "test_undeclared_declared_empty_and_ordered_binding_states",
        },
        "test_project_package_extension_selectors.py": {
            "test_manifest_model_and_schema_compatibility_are_exact",
            "test_all_five_selector_families_and_physical_types_are_exact",
        },
        "test_project_explain_runtime.py": {
            "test_zero_targets_preserve_all_three_declaration_states_without_cells",
            "test_real_schema3_runtime_chain_builds_successful_exact_envelope",
        },
        "test_cli_project_explain.py": {
            "test_explain_parser_enforces_file_xor_project_and_exact_formats",
            "test_project_json_success_is_exact_existing_serializer_bytes",
        },
    }
    for filename, required in owner_functions.items():
        assert required <= _function_names(REPO_ROOT / "tests" / filename)


def test_reachability_differential_and_central_audit_owners_are_closed() -> None:
    reachability = _function_names(
        REPO_ROOT / "tests/test_project_explain_reachability.py"
    )
    assert {
        "test_real_multi_package_multi_target_runtime_preserves_authority_and_states",
        "test_current_runtime_structurally_prevents_blocked_and_catalog_multi_candidate",
        "test_empty_targets_preserve_declaration_identity_without_synthetic_results",
    } <= reachability

    differential = _function_names(
        REPO_ROOT / "tests/test_harness_project_explain_differential.py"
    )
    assert {
        "test_four_fixed_hash_seeds_preserve_exact_values_and_authoritative_order",
        "test_available_supported_interpreters_consume_the_same_reference",
        "test_project_and_source_relocation_ignore_cwd_and_unrelated_ambient_state",
        "test_installed_wheel_matches_source_from_fresh_cache_and_wheel_target",
        "test_failure_and_single_file_surfaces_share_the_same_cross_environment_contract",
    } <= differential

    assert tuple(ProjectExplainEvaluationState) == (
        ProjectExplainEvaluationState.UNDECLARED,
        ProjectExplainEvaluationState.BLOCKED,
        ProjectExplainEvaluationState.CHECKED,
    )
    assert tuple(ProjectExplainCheckedStatus) == (
        ProjectExplainCheckedStatus.SATISFIED,
        ProjectExplainCheckedStatus.UNSUPPORTED,
        ProjectExplainCheckedStatus.ABSENT,
        ProjectExplainCheckedStatus.UNKNOWN,
        ProjectExplainCheckedStatus.CONFLICT,
    )
    assert tuple(ProjectExplainCatalogSelectionOutcome) == (
        ProjectExplainCatalogSelectionOutcome.UNDECLARED,
        ProjectExplainCatalogSelectionOutcome.SELECTED,
        ProjectExplainCatalogSelectionOutcome.AMBIGUOUS,
        ProjectExplainCatalogSelectionOutcome.CONFLICT,
    )
    assert tuple(ProjectExplainPortabilityClassification) == (
        ProjectExplainPortabilityClassification.PORTABLE,
        ProjectExplainPortabilityClassification.NOT_PORTABLE,
        ProjectExplainPortabilityClassification.INDETERMINATE,
    )
    assert tuple(ProjectExplainPortabilityReason) == (
        ProjectExplainPortabilityReason.NO_EVALUATED_TARGETS,
    )

    for path in (
        "scripts/validate.py",
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        ".github/workflows/ci.yml",
    ):
        assert (REPO_ROOT / path).is_file()


def test_exit_criteria_deferred_subjects_and_later_owners_are_closed() -> None:
    document = SPEC.read_text(encoding="utf-8")
    exit_rows = _table(_section(document, "Final Exit-criteria Ledger"))
    assert tuple(row[0] for row in exit_rows) == _EXIT_CRITERIA
    assert all(row[1] == "`PASS`" and row[2] for row in exit_rows)
    assert "passed criteria: 24" in document
    assert "total exit criteria: 24" in document
    assert "PHASE58_SELF_OWNED_OPEN = 0" in document

    deferred_rows = _table(_section(document, "Deferred-subject Ledger"))
    assert len({row[0] for row in deferred_rows}) == len(deferred_rows)
    transferred = {
        row[0]: row[2]
        for row in deferred_rows
        if row[1] == "`TRANSFERRED_TO_EXACT_LATER_OWNER`"
    }
    assert transferred == _LATER_OWNERS
    assert deferred_rows[-1][1] == "`INTENTIONALLY_OUT_OF_SCOPE`"
    assert not {
        "OPEN",
        "UNASSIGNED",
        "TBD",
        "UNKNOWN_OWNER",
    } & {row[1].strip("`") for row in deferred_rows}

    handoff = _section(document, "Phase 59 Handoff")
    assert "Phase 59: Local package graph, attribution, provenance, and lineage" in (
        handoff
    )
    assert "`docs/roadmap.md` / `Retained later ownership`" in handoff
    assert "`UNSTARTED / NOT AUTHORIZED`" in handoff
    assert "Phase 58 prerequisites still missing for Phase 59 planning: 0" in handoff
    assert "Phase 59 planning after successful Slice 17 natural CI: UNBLOCKED" in (
        handoff
    )
    assert handoff.count("`READY`") == 8
    readiness_rows = _table(_section(document, "Phase 60 Through 70 Readiness"))
    assert tuple(row[0] for row in readiness_rows) == tuple(
        str(phase) for phase in range(60, 71)
    )


def test_publication_boundaries_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    release = " ".join(
        _section(document, "Release Rust And Publication Boundary").split()
    )
    assert "version remain `0.1.0`" in release
    assert "does not authorize a version bump, tag, GitHub Release" in release
    assert "Phase 70 owns" in release
    assert "Phase 68 owns the first Rust-kernel decision" in release
    for publication_fact in (
        "local tags: 0",
        "remote tags: 0",
        "GitHub Releases: []",
        "package publication: none",
        "commit signing: none",
        "attestation: none",
    ):
        assert publication_fact in release
    assert "0c539caa9e724ce00f265a5b010d084b37d3f1c6" in document
    assert "Fix fresh-cache installed-wheel differential assurance" in document
    lifecycle_section = _section(document, "Lifecycle And Frozen Publication Subject")
    assert "Complete Phase 58 project explain portability" in lifecycle_section
    assert "no status-only follow-up commit" in lifecycle_section
