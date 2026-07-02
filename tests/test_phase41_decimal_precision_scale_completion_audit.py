from __future__ import annotations

import subprocess
import tomllib
from dataclasses import fields
from pathlib import Path

import pietto.semantic as semantic_api
from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from pietto._metadata.model import SemanticMetadataType
from pietto.ir import TypeRefIR
from pietto.semantic import ResolvedType, ValueType

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-41-decimal-precision-scale-mvp.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
SEMANTIC_API_PATH = REPO_ROOT / "src/pietto/semantic/__init__.py"
SEMANTIC_ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"

PHASE41_TEST_PATHS = (
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase41_decimal_precision_scale_semantic_validation.py",
    "tests/test_phase41_decimal_precision_scale_type_carrier.py",
    "tests/test_phase41_decimal_precision_scale_ir_compatibility.py",
    "tests/test_phase41_decimal_precision_scale_aggregate_numeric_boundary.py",
    "tests/test_phase41_decimal_precision_scale_metadata_cli_compatibility.py",
    "tests/test_phase41_decimal_precision_scale_docs_readiness.py",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
)

PUBLIC_OUTPUT_SURFACE_PATHS = (
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli_json.py",
    "src/pietto/_metadata",
    "src/pietto/_project/json_v2.py",
)

ALLOWED_SLICE8_CHANGED_PATHS = {
    "docs/plan/phase-41-decimal-precision-scale-mvp.md",
    "tests/test_phase41_decimal_precision_scale_completion_audit.py",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/diagnostics.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "examples",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _phase41_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in (
            *PHASE41_TEST_PATHS,
            "docs/plan/phase-41-decimal-precision-scale-mvp.md",
            "docs/spec/diagnostics.md",
            "src/pietto/semantic/analyzer.py",
            "src/pietto/semantic/model.py",
        )
    )


def _public_output_surface_text() -> str:
    chunks: list[str] = []
    for relative_path in PUBLIC_OUTPUT_SURFACE_PATHS:
        path = REPO_ROOT / relative_path
        if path.is_file():
            chunks.append(_normalized(path))
            continue
        chunks.extend(_normalized(child) for child in sorted(path.glob("**/*.py")))
    return " ".join(chunks)


def _git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return [line for line in result.stdout.splitlines() if line]


def _git_status_for(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase41_artifact_inventory_is_complete_through_slice8() -> None:
    assert PLAN_PATH.is_file()
    for relative_path in PHASE41_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _plan()
    for required in (
        "| 1 | Candidate Decision And Scope Lock |",
        "| 2 | Decimal Precision-Scale Semantic Validation |",
        "| 3 | Internal Type Carrier MVP |",
        "| 4 | IR Compatibility Carrier Boundary |",
        "| 5 | Aggregate / Numeric Boundary Hardening |",
        "| 6 | Metadata / CLI JSON / Explain Compatibility |",
        "| 7 | Docs, Deferred Register, And Package Smoke Readiness |",
        "| 8 | Completion Audit And Status Lock |",
        "No remaining Phase 41 slice is pending",
    ):
        assert required in plan, required


def test_phase41_final_completion_status_is_locked_in_plan() -> None:
    plan = _plan()

    for required in (
        "Phase 41 Slice 8 is Completion Audit And Status Lock",
        "docs/plan/status-lock and tests/static-audit completion work only",
        "adds no new compiler behavior",
        "marks Phase 41 complete only after Slice 8",
        "Slices 1 through 8 are complete",
        "Phase 41 is complete as the Decimal precision-scale MVP",
        "Slice 8 updates only this approved Phase 41 plan/status artifact",
        "It does not update `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
        "Package version remains `0.1.0`",
        "No tag/release/publish/upload/signing/",
        "attestation occurred",
        "No manual workflow trigger and no `gh workflow run`",
        "Slice 8 completion audit/status lock is complete once Gate 3 records",
        "natural CI `headSha` verification",
    ):
        assert required in plan, required

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_slice1_through_slice8_outcomes_remain_represented() -> None:
    plan = _plan()

    for required in (
        "Slice 1 Candidate Decision And Scope Lock is complete",
        "Slice 2 Decimal Precision-Scale Semantic Validation is complete with `PIE-S2004`",
        "Slice 3 Internal Type Carrier MVP is complete",
        "private `DecimalPrecisionScale` carrier",
        "`SemanticModel.decimal_precision_scales`",
        "`decimal_precision_scale_for`",
        "safe alias-chain facts",
        "Slice 4 IR Compatibility Carrier Boundary is complete",
        "keeps `TypeRefIR` precision-scale-field-free",
        "Slice 5 Aggregate / Numeric Boundary Hardening is complete",
        "existing Decimal aggregate/numeric boundaries",
        "Slice 6 Metadata / CLI JSON / Explain Compatibility is complete",
        "CLI JSON v1, Project JSON v2, explain text/JSON, and Semantic Metadata Artifact v1 precision-scale-field-free",
        "Slice 7 Docs, Deferred Register, And Package Smoke Readiness is complete",
    ):
        assert required in plan, required


def test_completed_decimal_precision_scale_mvp_is_locked() -> None:
    evidence = _phase41_evidence()
    analyzer = _read(SEMANTIC_ANALYZER_PATH)
    model = _read(SEMANTIC_MODEL_PATH)
    semantic_api_source = _read(SEMANTIC_API_PATH)
    diagnostics = _read(DIAGNOSTICS_PATH)

    for required in (
        "`Decimal(p,s)` semantic validation",
        "`PIE-S2004`",
        "the private internal carrier",
        "alias precision-scale fact propagation",
        "IR compatibility",
        "aggregate/numeric boundary hardening",
        "metadata/CLI/explain compatibility",
        "docs/deferred-register readiness",
        "test_valid_decimal_precision_scale_type_arguments_remain_plain_decimal",
        "test_decimal_precision_scale_facts_are_stored_for_supported_type_sites",
        "test_decimal_precision_scale_facts_propagate_through_safe_alias_chains",
        "test_decimal_precision_scale_ir_type_refs_remain_logical_decimal",
        "test_decimal_precision_scale_direct_aggregates_remain_logical_decimal",
        "test_explain_json_keeps_artifact_v1_logical_decimal_schema",
    ):
        assert required in evidence, required

    for required in (
        "_DECIMAL_PRECISION_MAX = 38",
        "def _decimal_precision_scale_fact(",
        "_propagate_decimal_precision_scale_aliases",
        "PIE-S2004",
    ):
        assert required in analyzer, required

    for required in (
        "class DecimalPrecisionScale:",
        "precision: int",
        "scale: int",
        "decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale]",
        "def decimal_precision_scale_for(",
    ):
        assert required in model, required

    assert "| `PIE-S2004` | Invalid Decimal precision-scale type arguments |" in (
        diagnostics
    )
    assert "DecimalPrecisionScale" not in semantic_api_source
    assert not hasattr(semantic_api, "DecimalPrecisionScale")


def test_public_type_output_and_sql_surfaces_remain_precision_scale_free() -> None:
    for model_type in (
        ResolvedType,
        ValueType,
        TypeRefIR,
        SemanticMetadataType,
    ):
        field_names = {field.name for field in fields(model_type)}
        assert "precision" not in field_names
        assert "scale" not in field_names
        assert "precision_scale" not in field_names

    public_output_surface = _public_output_surface_text()
    for forbidden in (
        "DecimalPrecisionScale",
        "decimal_precision_scales",
        "decimal_precision_scale_for",
        "precision_scale",
        "precision",
        "scale",
    ):
        assert forbidden not in public_output_surface, forbidden

    evidence = _phase41_evidence()
    for required in (
        '"DECIMAL(" not in',
        '"NUMERIC(" not in',
        '"precision" not in',
        '"scale" not in',
        "test_decimal_precision_scale_sql_output_remains_logical_and_unparameterized",
        "test_semantic_metadata_artifact_json_does_not_serialize_internal_carrier",
        "test_project_json_v2_remains_discovery_only_for_decimal_sources",
    ):
        assert required in evidence, required


def test_deferred_inventory_and_future_owners_are_locked() -> None:
    plan = _plan()

    for required in (
        "Remaining deferred work keeps named prerequisites",
        "Decimal literals: Phase 42 numeric/literal work",
        "Int/Float/Decimal promotion: Phase 42",
        "Float/Decimal mixing: Phase 42 decision",
        "Decimal multiplication/division: Phase 42 or later numeric operator matrix",
        "Cast syntax: future cast syntax/design prerequisite",
        "Aggregate precision propagation: future aggregate/type propagation phase",
        "SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output: native SQL type/DDL/dialect",
        "DDL/native DB metadata: native DB metadata prerequisite",
        "Public JSON precision-scale fields: schema-versioned public output contract",
        "Metadata/explain precision-scale display: Artifact v2/display contract",
        "Non-Decimal type argument policy: future type-argument policy phase",
        "| Plain `Decimal` | Unaffected",
        "| Non-Decimal type arguments | Unaffected compatibility surface",
        "| Broad aggregate features | Unaffected",
    ):
        assert required in plan, required

    for forbidden in (
        "Decimal literals are implemented",
        "Int/Float/Decimal promotion is implemented",
        "SQL `DECIMAL(p,s)` output is implemented",
        "public JSON precision-scale fields are implemented",
        "metadata/explain precision-scale display is implemented",
    ):
        assert forbidden not in plan


def test_package_release_workflow_and_status_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "It does not update `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
        "does not add public JSON precision-scale fields",
        "Semantic Metadata Artifact v1 precision-scale fields",
        "SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output",
        "fixtures, goldens, examples, workflows, package metadata, release files",
        "or production behavior in Slice 8",
        "Package version remains `0.1.0`",
        "No tag/release/publish/upload/signing/",
        "No manual workflow trigger and no `gh workflow run`",
    ):
        assert required in plan, required


def test_forbidden_surfaces_are_unchanged_or_slice8_allowlisted() -> None:
    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert diff_paths <= ALLOWED_SLICE8_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE8_CHANGED_PATHS


def test_changed_set_is_slice8_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert status_paths <= ALLOWED_SLICE8_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE8_CHANGED_PATHS
            for path in status_paths
        )
