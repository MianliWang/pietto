from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any, cast

from pietto.errors import Severity
from pietto.parser_api import parse_file
from pietto.semantic import analyze

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
CI_PATH = REPO_ROOT / ".github/workflows/ci.yml"

PHASE31_STATUS_DOCS = (README_PATH, AGENTS_PATH, PIETTO_SPEC_PATH)
TOOLING_DEPENDENCIES = (
    "ty",
    "import-linter",
    "deptry",
    "hypothesis",
    "mutmut",
    "cosmic-ray",
)


def test_phase31_slice7_plan_and_spec_lock_readiness_audit_scope() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    combined = f"{plan} {spec}"
    combined_lower = combined.lower()

    for required in (
        "Phase 31 Slice 7 is complete as Docs / Examples / Package / CI "
        "v0.2 readiness audit, tests, static audit, status, and docs work only",
        "Slice 8 is complete",
        "Version Labels",
        "`docs/spec/pietto-v0.9.md` remains the current specification document "
        "path and label",
        "It is not the package version and is not a release tag",
        "`v0.2` is the internal single-file stable compiler boundary",
        "It is complete as of Phase 31 Slice 8 after repository-local "
        "validation and status lock",
        "`0.1.0` remains the current package and installed CLI version",
        "Pietto v0.2 single-file stable complete",
        "Phase 31 Slice 8 complete",
        "Phase 29 historical Phase 32 completion-audit wording is superseded by "
        "the current Phase 31 merged roadmap",
        "Phase 32 remains post-v0.2 and has not started",
        "Phase 32 is post-v0.2 Semantic Explain And Metadata Output MVP",
    ):
        assert required in combined

    for required in (
        "all current tracked pietto examples are included in the readiness audit",
        "the tracked examples inventory is non-empty",
        "every current tracked pietto example parses and passes the applicable "
        "semantic checks",
    ):
        assert required in combined_lower

    for forbidden in (
        "package version bump",
        "release tag",
        "publishing",
        "dependency change",
        "lockfile change",
        "workflow change",
        "fixture or golden change",
        "tooling adoption",
        "`ty` adoption",
        "coverage threshold",
        "v0.2 completion declaration in Slice 7",
        "Phase 32 implementation",
    ):
        assert forbidden in combined


def test_version_labels_are_unambiguous_without_version_bump() -> None:
    project = cast(dict[str, Any], _pyproject()["project"])
    combined_docs = " ".join(_normalized(path) for path in PHASE31_STATUS_DOCS)
    package_smoke = _read(PACKAGE_SMOKE_PATH)

    assert PIETTO_SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "pietto-0.1.0.tar.gz" not in _read(PYPROJECT_PATH)
    assert 'expected_version = f"pietto {contract.version}\\n".encode()' in (
        package_smoke
    )
    assert 'version="0.2.0"' not in combined_docs
    assert "not the package version and is not a release tag" in combined_docs
    for required in ("package version bump", "release tag", "publishing"):
        assert required in combined_docs
    assert "internal single-file stable compiler boundary" in combined_docs
    assert "`0.1.0` is the current package and installed CLI version" in combined_docs


def test_docs_status_and_post_v02_roadmap_are_consistent() -> None:
    for path in PHASE31_STATUS_DOCS:
        text = _normalized(path)
        text_lower = text.lower()
        for required in (
            "Phase 31 Slice 7 Docs / Examples / Package / CI v0.2 Readiness "
            "Audit is complete as tests/static-audit/status/docs work only",
            "Pietto v0.2 single-file stable complete",
            "Phase 31 Slice 8 complete",
            "Phase 32 remains post-v0.2 and has not started",
            "Phase 32 is post-v0.2 Semantic Explain And Metadata Output MVP",
            "Phase 33 is Project And Multi-file MVP",
            "Phase 34 is Semantic Graph / ERD / AI Metadata Export MVP",
            "Phase 35 is Relationship Grain And Narrow JOIN MVP",
            "Version Labels",
            "Phase 29 historical Phase 32 completion-audit wording is "
            "superseded by the current Phase 31 merged roadmap",
            "no Phase 31 behavior implementation in Slice 7",
            "no Phase 32 implementation in Slices 1 through 8",
        ):
            assert required in text, path

        for required in (
            "all current tracked pietto examples are included in the readiness audit",
            "the tracked examples inventory is non-empty",
            "every current tracked pietto example parses and passes the "
            "applicable semantic checks",
        ):
            assert required in text_lower, path

        assert "v0.2 is not complete yet at Phase 31 Slice 5" not in text
        assert "v0.2 is not complete yet at Phase 31 Slice 6" not in text
        assert "Phase 32 remains required before v0.2 stable completion" not in text


def test_examples_inventory_parse_and_semantic_readiness_is_locked() -> None:
    example_paths = _tracked_pietto_examples()
    assert example_paths

    for relative_path in example_paths:
        path = REPO_ROOT / relative_path
        parse_result = parse_file(path)
        assert parse_result.diagnostics == ()
        assert parse_result.ast is not None

        semantic_result = analyze(parse_result.ast)
        errors = tuple(
            diagnostic
            for diagnostic in semantic_result.diagnostics
            if diagnostic.severity is Severity.ERROR
        )
        assert errors == (), relative_path

        source = path.read_text(encoding="utf-8").lower()
        for forbidden in (
            "json v2",
            "project ",
            "join",
            "schema introspection",
            "datetime",
            "interval",
            "timezone",
            "decimal(",
        ):
            assert forbidden not in source


def test_package_metadata_entrypoint_and_artifact_readiness_is_locked() -> None:
    project = cast(dict[str, Any], _pyproject()["project"])
    package_smoke = _read(PACKAGE_SMOKE_PATH)

    assert project["name"] == "pietto"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.12"
    assert project["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["scripts"]["pietto"] == "pietto.cli:main"
    build_system = cast(dict[str, Any], _pyproject()["build-system"])
    assert build_system["build-backend"] == "uv_build"

    for required in (
        '"build"',
        '"--sdist"',
        '"--wheel"',
        '"--out-dir"',
        "contract.version",
        "examples/basic/types.pietto",
        "installed CLI version",
        "installed CLI help",
        "installed CLI check",
        "installed PostgreSQL text",
        "installed MySQL JSON v1",
        "PiettoParser.py",
    ):
        assert required in package_smoke

    assert '"examples/"' not in package_smoke
    for forbidden in ("twine", "PyPI", "publish", "upload", "signing"):
        assert forbidden.lower() not in package_smoke.lower()


def test_validation_entrypoint_and_documented_commands_are_consistent() -> None:
    validate = _read(VALIDATE_PATH)
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    commands = re.findall(r'\(\s*"([^"]+)",\s*\(', validate)

    assert commands == [
        "lockfile",
        "format",
        "lint",
        "production typing",
        "test typing",
        "tests",
    ]
    for command in (
        "uv lock --check",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run pyright",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest",
    ):
        assert command in plan
        assert command in spec

    assert "check_generated" not in validate
    assert "check_goldens" not in validate
    assert "package_smoke" not in validate
    assert "CI separately runs generated, golden, and package smoke checks" in (
        f"{plan} {spec}"
    )


def test_ci_workflow_readiness_is_locked_without_workflow_change() -> None:
    workflow = _read(CI_PATH)
    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "pull_request:",
        "push:",
        "branches:",
        "main",
        "permissions:",
        "contents: read",
    ):
        assert required in workflow
    for version in ('"3.12"', '"3.13"'):
        assert version in workflow
    for command in (
        "uv sync --locked",
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert command in workflow

    for forbidden in (
        "upload-artifact",
        "twine",
        "PyPI",
        "publish",
        "release",
        "id-token:",
        "contents: write",
    ):
        assert forbidden.lower() not in workflow.lower()

    assert "CI headSha verification remains an external Gate 3 process" in combined
    assert "workflow change" in combined


def test_tooling_evaluation_is_advisory_and_not_adopted() -> None:
    pyproject_text = _read(PYPROJECT_PATH)
    workflow = _read(CI_PATH)
    plan_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"
    plan_spec_lower = plan_spec.lower()

    assert "pytest-cov>=7.1.0" in pyproject_text
    assert "`ty` was not adopted in slice 7" in plan_spec_lower
    assert "ty is not a blocking local-validation or ci requirement" in (
        plan_spec_lower
    )
    assert "future separately approved tooling evaluation may consider `ty`" in (
        plan_spec_lower
    )
    assert "coverage remains advisory" in plan_spec_lower
    assert "no coverage threshold was adopted" in plan_spec_lower
    assert "generated parser/visitor coverage should not drive a global threshold" in (
        plan_spec_lower
    )
    assert "coverage threshold was adopted" not in plan_spec_lower.replace(
        "no coverage threshold was adopted",
        "",
    )
    assert "Pyright remains the source-of-truth type checker" in plan_spec

    for dependency in (item for item in TOOLING_DEPENDENCIES if item != "ty"):
        assert dependency not in pyproject_text
        assert dependency not in workflow
    assert "ty>=" not in pyproject_text
    assert "ty check" not in workflow
    assert "astral-sh/ty" not in workflow


def test_slice8_completion_status_keeps_release_ops_separate() -> None:
    plan_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "single-file compiler boundary",
        "parser/generated stability",
        "semantic/type/nullability stability",
        "aggregate freeze",
        "PostgreSQL SQL stability",
        "private MySQL CLI boundary",
        "diagnostic stability",
        "CLI stability",
        "JSON v1 stability",
        "examples readiness",
        "package readiness",
        "CI readiness",
        "deferred register",
        "clean worktree",
        "CI `headSha` exactly matching the final Slice 8 commit",
        "no package version/release/tag/publish implication",
        "Pietto v0.2 single-file stable complete",
        "Phase 31 complete",
        "Phase 31 Slice 8 complete",
        "Phase 32 remains post-v0.2 and has not started",
    ):
        assert required in plan_spec

    for forbidden in (
        "Pietto 0.2.0 released",
        "v0.2 package published",
        "v0.2 Git tag created",
        "Phase 32 is complete",
    ):
        assert forbidden not in plan_spec


def test_static_audit_no_release_tooling_or_post_v02_surface_was_added() -> None:
    pyproject_text = _read(PYPROJECT_PATH)
    workflow = _read(CI_PATH)
    makefile = _read(REPO_ROOT / "Makefile")
    plan_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for path in (
        "setup.py",
        "setup.cfg",
        "MANIFEST.in",
        "package.json",
        ".pypirc",
        "docs/spec/json-v2.md",
    ):
        assert not (REPO_ROOT / path).exists()

    for forbidden in (
        'version = "0.2.0"',
        "ty>=",
        "hypothesis",
        "import-linter",
        "deptry",
        "mutmut",
        "cosmic-ray",
    ):
        assert forbidden not in pyproject_text

    for forbidden in (
        "twine",
        "pypi",
        "publish",
        "upload",
        "signing",
        "attestation",
        "coverage xml",
        "ty check",
        "hypothesis",
    ):
        assert forbidden not in workflow.lower()
        assert forbidden not in makefile.lower()

    for required in (
        "no JSON v2",
        "project or multi-file implementation",
        "runtime or database execution",
        "schema introspection",
        "relationship or JOIN implementation",
        "Phase 32 implementation",
    ):
        assert required in plan_spec


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _pyproject() -> dict[str, object]:
    return tomllib.loads(_read(PYPROJECT_PATH))


def _tracked_pietto_examples() -> tuple[str, ...]:
    result = subprocess.run(
        ("git", "ls-files", "-z", "--", "examples"),
        cwd=REPO_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return tuple(
        sorted(
            path
            for path in result.stdout.decode("utf-8").split("\0")
            if path.endswith(".pietto")
        )
    )
