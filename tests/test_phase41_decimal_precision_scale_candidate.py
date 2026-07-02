from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-41-decimal-precision-scale-mvp.md"
TEST_PATH = REPO_ROOT / "tests/test_phase41_decimal_precision_scale_candidate.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE1_CHANGED_PATHS = {
    "docs/plan/phase-41-decimal-precision-scale-mvp.md",
    "tests/test_phase41_decimal_precision_scale_candidate.py",
}
ALLOWED_REPAIR_GATE2_CHANGED_PATHS = ALLOWED_SLICE1_CHANGED_PATHS | {
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/diagnostics.md",
    "grammar",
    "src",
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


def _git_status_all() -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
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


def test_phase41_slice1_plan_exists_and_records_trusted_handoff() -> None:
    assert PLAN_PATH.is_file()
    assert TEST_PATH.is_file()

    plan = _plan()

    for required in (
        "Phase 41 Slice 1 is Candidate Decision And Scope Lock",
        "docs/plan/static-audit/tests-only and implements no behavior change",
        "Phase 41 theme: Decimal precision-scale MVP",
        "baseline HEAD: `0244eb9cdb00a5fa97d9533377a059a2c25757b0`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 40 let binding implementation audit`",
        "latest completed phase: Phase 40 Let Binding Model",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
        "Phase 40 implemented row-level `let:` only",
        "Phase 41 starts from the trusted Phase 40 handoff",
    ):
        assert required in plan, required


def test_phase41_candidate_decision_and_slice_sequence_are_locked() -> None:
    plan = _plan()

    for required in (
        "Minimal fail-closed compiler-internal Decimal precision-scale MVP",
        "Phase 41 is not a docs-only phase",
        "production implementation begins in Slice 2",
        "accept `Decimal(precision, scale)` as a semantic Decimal type form",
        "preserve plain `Decimal` and all current plain Decimal behavior",
        "store validated precision-scale facts in internal compiler type facts",
        "reject invalid precision-scale forms fail-closed",
        "keep SQL expression output unchanged",
        "keep CLI JSON v1 and Semantic Metadata Artifact v1 schemas unchanged",
        "| 1 | Candidate Decision And Scope Lock |",
        "| 2 | Decimal Precision-Scale Semantic Validation |",
        "| 3 | Internal Type Carrier MVP |",
        "| 4 | IR Compatibility Carrier Boundary |",
        "| 5 | Aggregate / Numeric Boundary Hardening |",
        "| 6 | Metadata / CLI JSON / Explain Compatibility |",
        "| 7 | Docs, Deferred Register, And Package Smoke Readiness |",
        "| 8 | Completion Audit And Status Lock |",
    ):
        assert required in plan, required

    for forbidden in (
        "Phase 41 is docs-only",
        "production implementation begins in Slice 3",
        "Slice 1 implements Decimal precision-scale semantics",
    ):
        assert forbidden not in plan


def test_repo_derived_decimal_readiness_and_no_grammar_requirement_are_locked() -> None:
    plan = _plan()

    for required in (
        "`grammar/Pietto.g4` already allows generic type arguments",
        "`TypeExpr` already stores `arguments: tuple[TypeArgument, ...]`",
        "`Decimal(12, 2)` can parse as generic `TypeExpr.arguments`",
        "current semantic resolution ignores those arguments",
        "`ResolvedType` carries only `name`, `kind`, and optional `definition`",
        "`ValueType` carries `resolved_type`, `nullability`, and `kind`",
        "No precision-scale carrier exists in semantic, IR, SQL, CLI JSON, "
        "Project JSON v2, or Semantic Metadata Artifact v1 models",
        "Slice 2 should start in semantic validation and carrier ownership, not "
        "grammar regeneration",
    ):
        assert required in plan, required


def test_forbidden_surfaces_and_out_of_scope_items_are_locked() -> None:
    plan = _plan()

    for required in (
        "source implementation",
        "grammar change",
        "generated ANTLR change",
        "semantic behavior change",
        "IR behavior change",
        "SQL behavior change",
        "CLI JSON v1 change",
        "Project JSON v2 change",
        "Semantic Metadata Artifact v1 schema or output change",
        "SQL golden byte change",
        "fixture or golden change",
        "example change",
        "workflow change",
        "package metadata change",
        "lockfile change",
        "package version change",
        "tag, release, publish/upload, signing, or attestation",
        "Decimal literal typing",
        "full numeric promotion matrix",
        "Float/Decimal mixing behavior beyond preserving current fail-closed posture",
        "Decimal multiplication or division expansion except boundary tests",
        "cast syntax",
        "SQL DDL/native type output",
        "public JSON schema expansion",
        "Semantic Metadata Artifact v1 schema expansion",
        "relationship/JOIN behavior",
        "project/multi-file behavior",
        "runtime/database execution",
    ):
        assert required in plan, required


def test_slice1_allowlist_is_exact_and_phase41_inventory_is_bounded() -> None:
    plan = _plan()

    for relative_path in ALLOWED_SLICE1_CHANGED_PATHS:
        assert f"`{relative_path}`" in plan
        assert (REPO_ROOT / relative_path).is_file()

    discovered = {
        path.relative_to(REPO_ROOT).as_posix()
        for root in (REPO_ROOT / "docs", REPO_ROOT / "tests")
        for path in root.rglob("*phase*41*")
        if path.is_file() and "__pycache__" not in path.parts
    }

    assert discovered == ALLOWED_SLICE1_CHANGED_PATHS
    assert "No other file is approved" in plan
    assert "stop and request a Repair Gate 1 and allowlist expansion" in plan


def test_deferred_inventory_impact_is_explicit() -> None:
    plan = _plan()

    for required in (
        "| Decimal precision-scale carrier | Implement in Phase 41",
        "| Invalid Decimal precision-scale diagnostics | Implement in Phase 41 fail-closed",
        "| Plain `Decimal` | Unaffected",
        "| Decimal aggregate precision propagation | Still deferred",
        "| Decimal literals | Explicitly rejected in Phase 41",
        "| Full Int/Float/Decimal promotion matrix | Explicitly rejected in Phase 41",
        "| Decimal `*` and `/` | Still deferred",
        "| SQL `DECIMAL(p, s)` / native DB metadata / DDL | Still deferred",
        "| Public JSON precision-scale fields | Explicitly rejected in Phase 41",
        "| Broad aggregate features | Unaffected",
    ):
        assert required in plan, required


def test_package_version_release_and_public_status_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "Slice 1 does not update `README.md`, `AGENTS.md`",
        "`docs/spec/pietto-v0.9.md`, the deferred register, or status-lock files",
        "Status housekeeping remains future dedicated work unless separately approved",
    ):
        assert required in plan, required

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_unchanged_or_untracked() -> None:
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

    assert diff_paths <= ALLOWED_REPAIR_GATE2_CHANGED_PATHS
    assert status_paths <= ALLOWED_REPAIR_GATE2_CHANGED_PATHS


def test_changed_set_is_slice1_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status_all().splitlines()}

    assert status_paths <= ALLOWED_REPAIR_GATE2_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden)
            and path not in ALLOWED_REPAIR_GATE2_CHANGED_PATHS
            for path in status_paths
        )
