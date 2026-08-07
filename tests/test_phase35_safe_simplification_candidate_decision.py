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


def test_status_housekeeping_is_locked_to_approved_slice2_scope() -> None:
    combined = _phase35_docs()

    for required in (
        "`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
        "Slice 2 updates those global status-housekeeping files",
        "Phase 34 complete, Phase 35 active, and Phase 35 Slice 1 complete",
        "Status Housekeeping for `README.md`, `AGENTS.md`, and "
        "`docs/spec/pietto-v0.9.md`",
        "docs/status/static-audit/hash-lock work only",
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
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert (
        _non_slice3_repair_diff_paths(diff_output) == set()
    ) or _phase54_active_gate2_is_active()


def _phase35_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))
