from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
)
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE35_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md"
)
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
CI_WORKFLOW_PATH = REPO_ROOT / ".github/workflows/ci.yml"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "docs/spec/phase-35-safe-simplification-contract-v1.md",
    "tests/_static_audit_helpers.py",
    "tests/test_phase35_safe_simplification_candidate_decision.py",
    "tests/test_phase35_static_audit_helper_simplification.py",
    "scripts/validate.py",
    "scripts/package_smoke.py",
    "scripts/check_generated.py",
    "scripts/check_goldens.py",
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "uv.lock",
    "grammar/Pietto.g4",
    "src/pietto",
    "tests/fixtures",
    "tests/goldens",
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


def test_phase35_plan_records_slice4_delivery_guidance() -> None:
    plan = _normalized(PHASE35_PLAN_PATH)

    for required in (
        "Phase 35 Slice 4 Validation And Delivery Workflow Polish is the current "
        "docs/static-audit-only delivery guidance slice",
        "Phase 35 Slice 4 Validation And Delivery Workflow Polish is "
        "docs/static-audit delivery guidance work only",
        "`UV_CACHE_DIR=/tmp/...` is the preferred sandbox-local workaround",
        "default `uv` cache under `/home/mianliwang/.cache/uv` is read-only",
        "Sandbox DNS/PyPI failures in `scripts/package_smoke.py` are "
        "environment/network failures",
        "dependency fetch or name resolution",
        "record the raw failure and rerun only `scripts/package_smoke.py` with "
        "network access if available",
        "Do not change repository files to fix sandbox cache, DNS, or PyPI "
        "environment failures",
        "Gate 2 evidence should be `.txt`, not `.md`",
        "long evidence should be written in small chunks",
        "not one giant shell block",
        "full diff, full cat, and validation output should go into evidence files",
        "`scripts/validate.py` remains the authoritative local gate",
        "Generated, golden, and package smoke checks remain separate commands",
        "no script change, no workflow change, no package metadata change",
        "Package version remains `0.1.0`",
        "attestation is performed by Slice 4",
    ):
        assert required in plan, required


def test_validate_py_remains_authoritative_local_gate_only() -> None:
    validate_py = _read(VALIDATE_PATH)

    for required in (
        '("lockfile", ("uv", "lock", "--check"))',
        '("format", ("uv", "run", "ruff", "format", "--check", "."))',
        '("lint", ("uv", "run", "ruff", "check", "."))',
        '("production typing", ("uv", "run", "pyright"))',
        '"test typing"',
        '"pyrightconfig.tests.json"',
        '("tests", ("uv", "run", "pytest"))',
    ):
        assert required in validate_py, required

    for forbidden in (
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "check_generated",
        "check_goldens",
        "package_smoke",
        "twine",
        "pypi",
        "upload",
        "publish",
        "sigstore",
        "attest",
    ):
        assert forbidden not in validate_py, forbidden


def test_ci_separates_validation_generated_goldens_and_package_smoke() -> None:
    workflow = _read(CI_WORKFLOW_PATH)
    normalized_workflow = _normalized(CI_WORKFLOW_PATH)
    lowered = workflow.lower()

    for required in (
        "permissions:\n  contents: read",
        'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"',
        "run: uv run python scripts/validate.py",
        "run: uv run python scripts/check_generated.py",
        "run: uv run python scripts/check_goldens.py",
        "run: uv run python scripts/package_smoke.py",
    ):
        assert required in workflow, required
    for step_name in (
        "Run authoritative validation",
        "Verify generated files",
        "Audit golden fixtures",
        "Smoke test installed package",
    ):
        assert step_name in normalized_workflow, step_name

    for forbidden in (
        "contents: write",
        "id-token:",
        "upload-artifact",
        "twine",
        "pypi-token",
        "trusted publishing",
        "sigstore",
        "attestation",
    ):
        assert forbidden not in lowered, forbidden


def test_package_smoke_remains_smoke_install_cli_verification_only() -> None:
    package_smoke = _read(PACKAGE_SMOKE_PATH)
    lowered = package_smoke.lower()

    for required in (
        "Build, inspect, install, and smoke test Pietto release artifacts.",
        '"build sdist and wheel"',
        '"install wheel"',
        "installed CLI version",
        "installed CLI help",
        "installed CLI check",
        "installed CLI project check text",
        "installed CLI explain JSON",
        "installed PostgreSQL text",
        "installed MySQL JSON v1",
        "packaging and installed CLI smoke passed",
    ):
        assert required in package_smoke, required

    for forbidden in (
        "twine",
        "pypi",
        "publish",
        "upload",
        "sigstore",
        "attestation",
        "id-token",
        "trusted publishing",
    ):
        assert forbidden not in lowered, forbidden


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = " ".join(
        _normalized(path)
        for path in (PHASE35_PLAN_PATH, VALIDATE_PATH, PACKAGE_SMOKE_PATH)
    )

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = combined.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_slice4_forbidden_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert (
        _non_slice3_repair_diff_paths(diff_output) == set()
    ) or _phase54_active_gate2_is_active()
