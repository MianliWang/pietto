from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
    "src/pietto/generated",
    "tests/fixtures",
    "tests/goldens",
    "scripts",
    "pyproject.toml",
    "uv.lock",
    ".github",
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


def test_phase34_plan_exists_and_locks_candidate_decision() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Relationship Grain And Narrow JOIN MVP",
        "baseline HEAD: `8f62905c4552ec2855ac04646044978bcdc74f56`",
        "baseline commit: `Complete Phase 33 JSON v2 project audit`",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation occurred",
        "Proceed with Phase 34, but Slice 1 is docs/spec/static-audit/status-only "
        "and implements no JOIN",
        "Phase 34 is not complete",
        "Phase 34 remains in progress after Slice 1",
    ):
        assert required in plan, required


def test_phase34_slice1_scope_is_docs_spec_static_audit_only() -> None:
    combined = _phase34_docs()

    for required in (
        "Slice 1 is docs/spec/static-audit/status-only",
        "Slice 1 adds a Phase 34 master plan, candidate decision, "
        "relationship/grain/JOIN scope boundary, Phase 33 handoff audit, and "
        "focused static tests",
        "Slice 1 implements no JOIN and no relationship grain behavior",
        "Slice 1 adds this spec, the Phase 34 plan, and focused static audit "
        "tests only",
        "This spec does not change grammar, generated files, AST, semantic "
        "model, IR, SQL, CLI, JSON, fixtures, goldens, scripts, package "
        "metadata, dependencies, workflows, or runtime behavior",
    ):
        assert required in combined, required


def test_grain_definition_and_non_claims_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    assert SPEC_PATH.is_file()
    for required in (
        "Grain is compile-time metadata describing expected row "
        "identity/cardinality behavior around relationship endpoints",
        "Grain is not runtime enforcement, not database constraint "
        "introspection, not authorization, not optimization proof, and not a "
        "security guarantee",
        "Slice 1 does not add grain syntax",
        "does not store grain in the semantic model",
        "does not validate grain",
        "does not lower grain to IR or SQL",
    ):
        assert required in spec, required


def test_phase33_project_mode_boundaries_are_preserved() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "TOML schema parsing remains deferred",
        "glob expansion remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "project metadata aggregation remains deferred",
        "single-file `pietto check --format json` remains JSON v1",
        "single-file `pietto emit-sql --format json` remains JSON v1",
        "single-file `pietto explain --format json` remains Semantic Metadata "
        "Artifact v1",
        "Slice 1 changes none of these constraints",
    ):
        assert required in spec, required


def test_narrow_join_mvp_is_future_only_and_conservative() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Narrow JOIN is later-slice only",
        "a single relationship metadata edge",
        "explicit query opt-in",
        "one base relation plus one joined endpoint",
        "deterministic endpoint qualification",
        "statically known endpoint schemas",
        "PostgreSQL/MySQL parity",
        "fail-closed behavior when relationship, grain, scope, or backend "
        "lowering is ambiguous or unsupported",
        "arbitrary multi-hop traversal",
        "relationship chaining",
        "automatic join inference",
        "Final JOIN syntax is deferred and requires a later approved slice",
    ):
        assert required in spec, required


def test_phase17_and_relationship_metadata_boundaries_are_preserved() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Relationship metadata does not enter relation, type, callable, or "
        "field lookup",
        "Relationship metadata is not lowered to Semantic IR, PostgreSQL SQL, "
        "MySQL SQL, CLI text, JSON v1, Project JSON v2, or Semantic Metadata "
        "Artifact v1",
        "current relation bodies have one `from` input",
        "current two-part qualified fields bind only to the existing single "
        "input relation qualifier",
        "a relation name that is not the current input remains invalid as a qualifier",
        "relationship metadata does not participate in qualified field lookup",
    ):
        assert required in spec, required


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_remains_010() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)


def test_no_release_claims_are_introduced_outside_non_goals() -> None:
    combined = _phase34_docs()

    for required in (
        "no tag/release/publish/upload/signing/attestation occurred",
        "release/tag/publish/upload/signing/attestation behavior",
    ):
        assert required in combined, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in combined.lower(), forbidden


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase34_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def _git_diff_name_only(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()
