from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-35-developer-experience-and-delivery-pipeline.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/phase-35-safe-simplification-contract-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

OFFICIAL_TITLE = "Phase 35 Developer Experience And Delivery Pipeline MVP"
PHASE34_COMPLETION_STATEMENT = (
    "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
    "complete as docs/spec/static-audit/status-only work. The original behavior "
    "MVP remains future implementation deferred."
)
SAFE_SIMPLIFICATION_CATEGORIES = (
    "safe docs/status housekeeping",
    "safe test-helper simplification",
    "safe internal helper simplification with proof",
    "behavior-risky refactor",
    "defer / do not touch",
)
NO_BEHAVIOR_STANDARD = (
    "accepted/rejected programs",
    "diagnostics code/message/order/span where applicable",
    "SQL bytes",
    "JSON v1",
    "Project JSON v2",
    "Semantic Metadata Artifact v1",
    "generated inventory",
    "goldens",
    "package version",
    "dependencies",
    "workflows",
    "public CLI behavior",
)
FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md",
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
    "src/pietto/_project",
    "src/pietto/_metadata",
    "src/pietto/metadata",
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


def test_phase35_plan_exists_and_locks_official_title() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    assert OFFICIAL_TITLE in plan
    assert (
        "Developer Experience, Delivery Pipeline, And Safe Simplification MVP"
        not in (plan)
    )
    assert "Safe Simplification is a Slice 1 scope and future-slice discipline" in plan
    assert "not a Phase 35 title change" in plan
    assert "not a roadmap title change" in plan


def test_phase34_handoff_and_slice1_candidate_decision_are_locked() -> None:
    combined = _phase35_docs()

    for required in (
        "baseline HEAD: `10f882ad66f94523e05368b34aea9c5f845a9e62`",
        "baseline commit: `Complete Phase 34 relationship readiness audit`",
        PHASE34_COMPLETION_STATEMENT,
        "Proceed with Phase 35 as Developer Experience And Delivery Pipeline MVP",
        "Slice 1 is docs/spec/static-audit-only and implements no behavior change",
        "not as authorization for source refactors",
    ):
        assert required in combined, required


def test_safe_simplification_categories_and_inventory_are_documented() -> None:
    combined = _phase35_docs()

    for category in SAFE_SIMPLIFICATION_CATEGORIES:
        assert category in combined, category
    for required in (
        "CLI parse/analyze/IR flow",
        "project/metadata serializers",
        "PostgreSQL/MySQL expression and relation renderer",
        "grammar, generated parser, fixtures, goldens, package metadata, workflows",
    ):
        assert required in combined, required


def test_no_behavior_change_standard_is_documented() -> None:
    combined = _phase35_docs()

    for required in NO_BEHAVIOR_STANDARD:
        assert required in combined, required
    assert (
        "Any candidate that cannot prove this standard is not safe simplification"
        in (combined)
    )


def test_ponytail_inspired_style_rules_are_documented() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "prefer boring, local, explicit code",
        "prefer small pure helpers",
        "keep the main path straight and readable",
        "avoid speculative abstraction",
        "avoid hidden side effects",
        "remove duplication only with exact public-surface proof",
        "preserve fail-closed branches over compact ambiguous control flow",
        "preserve stable diagnostics and output over shorter code",
    ):
        assert required in spec, required


def test_status_housekeeping_is_deferred_to_later_dedicated_slice() -> None:
    combined = _phase35_docs()

    for required in (
        "`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
        "global status-housekeeping files are stale after Phase 34",
        "later dedicated slice candidate",
        "Status-housekeeping for `README.md`, `AGENTS.md`, and "
        "`docs/spec/pietto-v0.9.md`, if explicitly approved",
    ):
        assert required in combined, required


def test_slice1_does_not_authorize_refactors_or_behavior_changes() -> None:
    combined = _phase35_docs()

    for required in (
        "no source refactor",
        "no test-helper refactor",
        "no behavior change",
        "no grammar or generated change",
        "no fixture or golden change",
        "no package/dependency/workflow change",
        "no release operation",
        "no parser or AST behavior change",
        "no semantic model change",
        "no Semantic IR change",
        "no PostgreSQL/MySQL SQL lowering change",
        "no CLI/JSON/project behavior change",
    ):
        assert required in combined, required


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = _phase35_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "package version remains `0.1.0`" in combined
    assert "no tag/release/publish/upload/signing/attestation occurred" in combined
    assert "No tag/release/publish/upload/signing/" in combined
    assert "attestation is performed by Slice 1" in combined

    lowered = combined.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase35_docs() -> str:
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
