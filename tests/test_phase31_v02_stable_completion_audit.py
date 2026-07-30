from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CI_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
MAKEFILE_PATH = REPO_ROOT / "Makefile"

PHASE29_REGISTER_SPEC_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE29_AGGREGATE_FREEZE_PATH = (
    REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
)
PHASE29_EXIT_CRITERIA_PATH = (
    REPO_ROOT / "docs/spec/v02-exit-criteria-validation-strategy-v1.md"
)
PHASE30_CONTRACT_PATHS = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md",
    REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md",
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md",
    REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md",
    REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md",
    REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md",
    REPO_ROOT / "docs/spec/operator-comparison-matrix-contract-v1.md",
)
PHASE31_HARDENING_TESTS = (
    "tests/test_phase31_aggregate_result_matrix_hardening.py",
    "tests/test_phase31_numeric_promotion_decimal_boundary.py",
    "tests/test_phase31_date_timestamp_sql_compatibility.py",
    "tests/test_phase31_uuid_enum_readiness_decision.py",
    "tests/test_phase31_diagnostic_cli_json_stability.py",
    "tests/test_phase31_docs_examples_package_ci_readiness.py",
    "tests/test_phase31_v02_stable_completion_audit.py",
)
STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)
PHASE31_DOCS = (PLAN_PATH, SPEC_PATH)
COMPLETION_WORDING = (
    "Pietto v0.2 single-file stable complete",
    "Phase 31 complete",
    "Phase 31 Slice 8 complete",
    "Phase 32 remains post-v0.2 and has not started",
)


def test_phase31_slice8_plan_and_spec_lock_completion_scope() -> None:
    combined = _phase31_text()

    for required in (
        "Phase 31 Slice 8 is complete as v0.2 Stable Completion Audit And "
        "Status Lock, tests/spec/static-audit/status-lock/hash-lock work only",
        *COMPLETION_WORDING,
        "Slice 8 locks v0.2 stable completion through tests/spec/static audit",
        "completion audit",
        "exact hash-lock updates",
        "Gate 3 trust conditions remain external proof",
        "CI `headSha` exactly matching the final Slice 8 commit",
    ):
        assert required in combined

    for forbidden in (
        "source implementation",
        "grammar",
        "generated",
        "example, fixture, golden",
        "script, package, dependency, lockfile",
        "CI workflow",
        "public API",
        "CLI, JSON, IR, SQL, semantic",
        "aggregate, diagnostic, predicate",
        "runtime, project, relationship/JOIN",
        "schema introspection",
        "type-system behavior",
        "package version bump",
        "release tag",
        "publishing",
        "JSON v2",
        "public MySQL API expansion",
        "tooling adoption",
        "`ty` adoption",
        "coverage threshold",
        "Phase 32 implementation",
    ):
        assert forbidden in combined


def test_phase31_all_eight_slices_are_complete() -> None:
    combined = _phase31_text()

    for slice_title in (
        "Candidate Decision And Phase 30 Carry-forward Audit",
        "Aggregate Result Matrix Hardening",
        "Numeric Promotion And Decimal Boundary Tests",
        "Date / Timestamp SQL Compatibility Audit",
        "UUID / Enum Readiness Decision",
        "Diagnostic / CLI / JSON Stability Hardening",
        "Docs / Examples / Package / CI v0.2 Readiness Audit",
        "v0.2 Stable Completion Audit And Status Lock",
    ):
        assert slice_title in combined

    assert "Slice 8 is complete" in combined
    assert "Slice 8 remains planned only" not in combined
    assert "Slice 8 is planned only" not in combined
    assert "Phase 31 as a whole is not complete" not in combined
    assert "Phase 31 Slice 9" not in combined
    assert not (REPO_ROOT / "tests/test_phase32_semantic_explain.py").exists()


def test_v02_single_file_stable_completion_matrix_is_locked() -> None:
    combined = _phase31_text()

    for criterion in (
        "single-file compiler boundary: passed",
        "parser/generated stability: passed",
        "AST/parser contract: passed",
        "semantic/type/nullability stability: passed",
        "core scalar registry: passed",
        "Bool/predicate semantics: passed",
        "Date/Timestamp boundary: passed",
        "Decimal boundary: passed",
        "operator/comparison boundary: passed",
        "aggregate surface freeze: passed",
        "aggregate result matrix: passed",
        "numeric promotion and Decimal boundaries: passed",
        "UUID readiness: passed",
        "Enum readiness/risk posture: passed",
        "PostgreSQL SQL stability: passed",
        "private MySQL CLI boundary: passed",
        "public Python SQL API posture: passed",
        "diagnostic inventory and presentation: passed",
        "CLI behavior stability: passed",
        "JSON v1 stability: passed",
        "JSON v2 deferral: passed",
        "examples readiness: passed",
        "package readiness: passed",
        "validation entrypoint readiness: passed",
        "CI workflow readiness: passed",
        "deferred feature register: passed",
        "project/multi-file deferral: passed",
        "runtime/database and schema introspection deferral: passed",
        "relationship/JOIN deferral: passed",
        "release-ops separation: passed",
    ):
        assert criterion in combined

    assert "clean worktree" in combined
    assert "successful GitHub Actions run" in combined
    assert "CI `headSha` exactly matching the final Slice 8 commit" in combined


def test_phase29_deferred_register_and_aggregate_freeze_remain_active() -> None:
    combined = _phase31_text()
    register = _normalized(PHASE29_REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(PHASE29_AGGREGATE_FREEZE_PATH)

    assert "Phase 29 deferred register remains active" in combined
    assert "Phase 29 aggregate freeze remains active" in combined
    assert "It does not authorize implementation" in register
    assert "Runtime/database execution" in register
    assert "Project/multi-file" in register
    assert "Relationship/JOIN" in register
    assert "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen" in (
        aggregate_freeze
    )
    assert "Rejected v0.2 Aggregate Expansions" in aggregate_freeze


def test_phase30_type_system_contracts_remain_active() -> None:
    combined = _phase31_text()
    contracts = " ".join(_normalized(path) for path in PHASE30_CONTRACT_PATHS)

    assert "Phase 30 type-system contracts are carried forward" in combined
    for required in (
        "canonical scalar type registry",
        "nullability propagation",
        "Bool and predicate semantics",
        "Date and Timestamp formalization",
        "Decimal precision and scale",
        "operator and comparison matrix",
        "Phase 30 is complete as docs/spec/static-audit/status work only",
    ):
        assert required in contracts


def test_phase31_slice2_through_slice7_hardening_evidence_is_present() -> None:
    tracked_tests = set(_git_ls_files("tests/test_phase31_*.py"))
    combined = _phase31_text()

    for relative_path in PHASE31_HARDENING_TESTS:
        assert relative_path in tracked_tests or (REPO_ROOT / relative_path).is_file()

    for required in (
        "aggregate result matrix",
        "numeric promotion and Decimal boundaries",
        "Date/Timestamp boundary",
        "UUID readiness",
        "diagnostic inventory and presentation",
        "examples readiness",
        "package readiness",
        "CI workflow readiness",
    ):
        assert required in combined


def test_version_labels_remain_distinct_after_v02_completion() -> None:
    project = cast(dict[str, Any], _pyproject()["project"])
    status = " ".join(_normalized(path) for path in STATUS_DOCS)

    assert PIETTO_SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "docs/spec/pietto-v0.9.md` remains the current specification" in status
    assert "not the package version and is not a release tag" in status
    assert "Pietto v0.2 single-file stable complete" in status
    assert "`0.1.0` is the current package and installed CLI version" in status
    assert "Package version remains `0.1.0`" in status
    assert "Internal v0.2 completion does not imply a package release" in status


def test_package_version_release_tag_and_publish_are_not_implied() -> None:
    project = cast(dict[str, Any], _pyproject()["project"])
    pyproject = _read(PYPROJECT_PATH)
    workflow = _read(CI_PATH).lower()
    makefile = _read(MAKEFILE_PATH).lower()
    package_smoke = _read(PACKAGE_SMOKE_PATH).lower()
    status = " ".join(_normalized(path) for path in STATUS_DOCS)

    assert project["version"] == "0.1.0"
    assert 'version = "0.2.0"' not in pyproject
    status_lower = status.lower()
    assert (
        "phase 32 slice 1 performed no package version bump, tag, release, "
        "publish, upload, signing, or attestation"
    ) in status_lower
    assert "internal v0.2 completion does not imply a package release" in status_lower
    for forbidden in (
        "twine",
        "pypi",
        "publish",
        "upload",
        "signing",
        "attestation",
        "contents: write",
        "id-token:",
    ):
        assert forbidden not in workflow
        assert forbidden not in makefile
    assert "publish" not in package_smoke


def test_phase32_post_v02_roadmap_is_locked_without_implementation() -> None:
    combined = _phase31_text()
    assert "Phase 32 is post-v0.2 Semantic Explain And Metadata Output MVP" in (
        combined
    )
    assert "Phase 32 remains post-v0.2 and has not started" in combined
    assert "Phase 32 complete" not in combined

    for path in STATUS_DOCS:
        status = _normalized(path)
        assert "Phase 32 has started" in status, path
        assert (
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work"
        ) in status, path
        assert "Phase 32 as a whole is not complete" in status, path
        assert "Phase 32: Semantic Explain And Metadata Output MVP" in status, path
        assert "Phase 33: JSON v2 And Project / Multi-file MVP" in status, path
        assert "Phase 34: Relationship Grain And Narrow JOIN MVP" in status, path
        assert ("Phase 35: Developer Experience And Delivery Pipeline MVP") in status, (
            path
        )
        assert "Phase 36: Post-v0.2 Core Type System Expansion MVP" in status, path
        assert "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP" in status, path
        assert (
            "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
            "deferred candidate without an assigned phase number"
        ) in status, path
        assert "Phase 32 remains post-v0.2 and has not started" not in status, path


def test_historical_phase29_route_is_classified_without_contract_weakening() -> None:
    phase29_exit = _normalized(PHASE29_EXIT_CRITERIA_PATH)
    current = _phase31_text()
    status = " ".join(_normalized(path) for path in STATUS_DOCS)

    assert "Phase 32 remains the actual v0.2 single-file stable completion audit" in (
        phase29_exit
    )
    assert "remain required before the v0.2 stable completion status can be locked" in (
        phase29_exit
    )
    assert "Phase 29 historical Phase 32 completion-audit wording is superseded" in (
        current
    )
    assert "current Phase 31 merged roadmap" in current
    assert "Phase 32 has started" in status
    assert "Phase 32 remains post-v0.2 and has not started" not in status


def test_validation_package_examples_and_ci_readiness_are_locked() -> None:
    combined = _phase31_text()
    validate = _read(VALIDATE_PATH)
    package_smoke = _read(PACKAGE_SMOKE_PATH)
    workflow = _read(CI_PATH)
    examples = tuple(
        path for path in _git_ls_files("examples") if path.endswith(".pietto")
    )

    assert examples
    for command_name in (
        "lockfile",
        "format",
        "lint",
        "production typing",
        "test typing",
        "tests",
    ):
        assert command_name in validate
    for phrase in (
        "installed CLI version",
        "installed CLI help",
        "installed CLI check",
        "installed PostgreSQL text",
        "installed MySQL JSON v1",
        "PiettoParser.py",
    ):
        assert phrase in package_smoke
    for command in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert command in workflow
    assert (
        "All current tracked Pietto examples are included in the readiness audit"
        in (combined)
    )
    assert "Pyright remains the source-of-truth type checker" in combined
    assert "coverage threshold" in combined
    assert "exact pytest count" not in combined
    assert "exact coverage percentage" not in combined


def test_static_audit_no_forbidden_behavior_or_release_surface_was_added() -> None:
    combined = _phase31_text()
    pyproject = _read(PYPROJECT_PATH)
    workflow = _read(CI_PATH).lower()
    makefile = _read(MAKEFILE_PATH).lower()

    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert "emit_mysql_sql" not in _read(REPO_ROOT / "src/pietto/sql/__init__.py")
    for path in (
        "setup.py",
        "setup.cfg",
        "MANIFEST.in",
        ".pypirc",
        "docs/spec/v02-stable-completion-v1.md",
        "docs/spec/json-v2.md",
    ):
        assert not (REPO_ROOT / path).exists()
    for forbidden in (
        'version = "0.2.0"',
        "ty>=",
        "import-linter",
        "deptry",
        "mutmut",
        "cosmic-ray",
    ):
        assert forbidden not in pyproject
    for forbidden in (
        "twine",
        "pypi",
        "publish",
        "upload",
        "signing",
        "attestation",
        "coverage xml",
        "ty check",
    ):
        assert forbidden not in workflow
        assert forbidden not in makefile
    for required in (
        "no JSON v2",
        "public MySQL API expansion",
        "project or multi-file implementation",
        "runtime/database",
        "schema introspection",
        "relationship/JOIN",
        "Phase 32 implementation",
    ):
        assert required in combined


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase31_text() -> str:
    paths = (*PHASE31_DOCS, *STATUS_DOCS)
    return " ".join(_normalized(path) for path in paths)


def _pyproject() -> dict[str, object]:
    return tomllib.loads(_read(PYPROJECT_PATH))


def _git_ls_files(pathspec: str) -> tuple[str, ...]:
    result = subprocess.run(
        ("git", "ls-files", "-z", "--", pathspec),
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return tuple(item for item in result.stdout.decode("utf-8").split("\0") if item)
