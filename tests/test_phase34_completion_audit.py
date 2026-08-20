from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md"
BOUNDARY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md"
)
GRAIN_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-relationship-grain-contract-v1.md"
JOIN_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md"
)
READINESS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-parser-ast-readiness-contract-v1.md"
)
SEMANTIC_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-semantic-readiness-contract-v1.md"
CANDIDATE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-first-implementation-candidate-decision-v1.md"
)
RESCOPE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-rescope-completion-candidate-decision-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE34_SPECS = (
    BOUNDARY_SPEC_PATH,
    GRAIN_SPEC_PATH,
    JOIN_SPEC_PATH,
    READINESS_SPEC_PATH,
    SEMANTIC_SPEC_PATH,
    CANDIDATE_SPEC_PATH,
    RESCOPE_SPEC_PATH,
)

PHASE34_TESTS = (
    "tests/test_phase34_candidate_decision.py",
    "tests/test_phase34_relationship_grain_contract.py",
    "tests/test_phase34_narrow_join_contract.py",
    "tests/test_phase34_parser_ast_readiness_contract.py",
    "tests/test_phase34_semantic_readiness_contract.py",
    "tests/test_phase34_first_implementation_candidate_decision.py",
    "tests/test_phase34_rescope_completion_candidate_decision.py",
    "tests/test_phase34_completion_audit.py",
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

COMPLETION_STATEMENT = (
    "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
    "complete as docs/spec/static-audit/status-only work. The original behavior "
    "MVP remains future implementation deferred."
)


def test_phase34_slice8_completion_status_is_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 8 Completion Audit And Status Lock is complete as "
        "docs/spec/static-audit/status-lock work",
        "Proceed with Phase 34 Slice 8 as docs/spec/static-audit/status-lock "
        "work: complete Phase 34 as a conservative relationship grain and "
        "narrow JOIN readiness/contracts foundation only",
        "Slice 8 approved file scope is limited to",
        "`tests/test_phase34_completion_audit.py`",
        "Slice 8 is the completion audit/status lock slice",
        COMPLETION_STATEMENT,
    ):
        assert required in plan, required


def test_historical_slice_statuses_remain_available_for_audit_chain() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Slice 1 is the current docs/spec/static-audit/status-only slice",
        "Phase 34 remains in progress after Slice 1",
        "Slice 2 is the current docs/spec/static-audit/status-only contract slice",
        "Phase 34 remains in progress after Slice 2",
        "Slice 3 is the current docs/spec/static-audit/status-only contract slice",
        "Phase 34 remains in progress after Slice 3",
        "Slice 4 is the current docs/spec/static-audit/status-only readiness slice",
        "Phase 34 remains in progress after Slice 4",
        "Slice 5 is the current docs/spec/static-audit/status-only readiness slice",
        "Phase 34 remains in progress after Slice 5",
        "Slice 6 is the current docs/spec/static-audit/status-only candidate "
        "decision slice",
        "Phase 34 remains in progress after Slice 6",
        "Slice 7 is the current docs/spec/static-audit/status-only candidate "
        "decision slice",
        "Phase 34 remains in progress and is not complete after Slice 7",
    ):
        assert required in plan, required


def test_phase34_artifacts_for_slices_1_through_8_exist() -> None:
    assert PLAN_PATH.is_file()

    for path in PHASE34_SPECS:
        assert path.is_file(), str(path.relative_to(REPO_ROOT))
    for relative_path in PHASE34_TESTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_completion_wording_does_not_claim_behavior_mvp() -> None:
    combined = _phase34_docs()

    assert COMPLETION_STATEMENT in combined
    for required in (
        "Phase 34 is complete only as a conservative relationship grain and "
        "narrow JOIN readiness/contracts foundation",
        "Phase 34 does not complete JOIN behavior",
        "relationship grain syntax",
        "JOIN syntax",
        "parser/AST behavior",
        "semantic validation",
        "diagnostic codes",
        "IR/SQL lowering",
        "CLI/JSON/project behavior",
        "runtime/database behavior",
        "release operations",
        "relationship graph traversal",
        "relationship chaining",
        "automatic join inference",
        "Phase 34 does not implement JOIN, JOIN syntax, grain syntax, parser "
        "behavior, AST nodes, semantic model changes, semantic validation, "
        "diagnostic codes, IR/SQL lowering, CLI/JSON/project behavior, "
        "runtime/database behavior, fixtures, goldens, scripts, package "
        "metadata, dependencies, workflows, tag/release/publish/upload/signing/"
        "attestation, or runtime behavior",
        "Unsupported join-like syntax remains unsupported unless later approved",
        "Relationship metadata remains metadata-only and is not lowered to "
        "Semantic IR or SQL",
        "Current single-input relation behavior remains unchanged",
        "`RelationIR` remains single-source",
        "PostgreSQL/MySQL render one `FROM` input",
    ):
        assert required in combined, required


def test_slice1_through_slice7_contracts_are_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "Proceed with Phase 34, but Slice 1 is docs/spec/static-audit/status-only "
        "and implements no JOIN",
        "Relationship grain is a compile-time metadata contract around endpoint "
        "row identity and cardinality expectations",
        "Slice 3 may discuss future source shape and future syntax "
        "requirements, but it does not define accepted Pietto syntax",
        "Slice 4 implements no JOIN, no JOIN syntax, no relationship grain syntax",
        "Slice 5 implements no JOIN, no JOIN syntax, no relationship grain syntax",
        "Actual narrow JOIN parser/AST implementation is not approved yet in Slice 6",
        "Slice 7 does not complete Phase 34 yet",
        "The original behavior MVP remains future implementation deferred",
    ):
        assert required in combined, required


def test_phase33_project_json_boundaries_remain_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "TOML schema parsing remains deferred",
        "glob expansion remains deferred",
        "project source parsing remains deferred",
        "multi-file semantic analysis remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "project metadata aggregation remains deferred",
        "single-file `check` and `emit-sql` JSON remain JSON v1",
        "single-file `explain --format json` remains Semantic Metadata Artifact v1",
    ):
        assert required in combined, required


def test_status_housekeeping_files_remain_deferred() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "README, AGENTS, and `docs/spec/pietto-v0.9.md` status updates are "
        "deferred to a later completion audit slice unless separately approved",
        "README, AGENTS, and `docs/spec/pietto-v0.9.md` global status cleanup "
        "remains deferred to Phase 35 Developer Experience / Safe "
        "Simplification or a separately approved housekeeping slice",
        "Slice 8 intentionally does not update those status-housekeeping files",
    ):
        assert required in plan, required


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = _phase34_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in combined
    assert "no tag/release/publish/upload/signing/attestation occurred" in combined
    assert "No tag/release/publish/upload/signing/" in combined
    assert "attestation is performed by Slice 8" in combined

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in combined.lower(), forbidden


def _phase34_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, *PHASE34_SPECS))
