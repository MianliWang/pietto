from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
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
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
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


def test_phase34_slice3_plan_status_and_scope_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 3 Narrow JOIN Syntax And Semantic Contract is the "
        "current docs/spec/static-audit/status-only contract slice",
        "Proceed with Phase 34 Slice 3 as docs/spec/static-audit/status-only: "
        "define a future narrow JOIN syntax/semantic contract for one explicit "
        "relationship edge, one base relation plus one joined endpoint, "
        "deterministic endpoint qualification, required grain facts, and "
        "fail-closed behavior; implement no grammar, AST, semantic, IR, SQL, "
        "CLI, JSON, project, or runtime behavior",
        "Slice 3 approved file scope is limited to",
        "`docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md`",
        "`tests/test_phase34_narrow_join_contract.py`",
        "Phase 34 remains in progress after Slice 3",
        "Phase 34 is not complete",
    ):
        assert required in plan, required


def test_narrow_join_contract_exists_and_is_non_implementation() -> None:
    spec = _normalized(JOIN_SPEC_PATH)

    assert JOIN_SPEC_PATH.is_file()
    for required in (
        "This specification records the Phase 34 Slice 3 narrow JOIN syntax "
        "and semantic contract",
        "Slice 3 is docs/spec/static-audit/status-only work",
        "It does not implement JOIN, does not implement JOIN syntax, and does "
        "not define accepted Pietto syntax",
        "Final token spelling and grammar remain deferred to a later "
        "explicitly approved implementation slice",
        "This spec does not change grammar, generated files, AST, semantic "
        "model, IR, SQL, CLI, JSON, fixtures, goldens, scripts, package "
        "metadata, dependencies, workflows, public API, project behavior, "
        "runtime behavior, or database behavior",
    ):
        assert required in spec, required


def test_contract_preserves_slice1_boundary_and_slice2_grain_prerequisites() -> None:
    combined = _phase34_docs()

    for required in (
        "Narrow JOIN is later-slice only",
        "Final JOIN syntax is deferred and requires a later approved slice",
        "Relationship grain is a compile-time metadata contract around "
        "endpoint row identity and cardinality expectations",
        "endpoint and pairwise relationship-edge grain facts are statically known",
        "required grain facts before acceptance",
        "Slice 3 depends on those boundaries",
        "It does not widen them and does not authorize implementation",
    ):
        assert required in combined, required


def test_future_source_shape_locks_narrow_explicit_join_only() -> None:
    spec = _normalized(JOIN_SPEC_PATH)

    for required in (
        "explicit query opt-in",
        "exactly one declared relationship metadata edge",
        "one existing base relation",
        "exactly one joined endpoint",
        "deterministic endpoint names",
        "deterministic endpoint ownership",
        "deterministic field ownership",
        "no automatic relationship inference",
        "no graph traversal",
        "no relationship chaining",
        "no arbitrary SQL-like freeform JOIN",
        "no project-mode multi-file relationship resolution",
        "not accepted Pietto syntax",
        "do not introduce accepted keywords",
        "do not imply grammar approval",
    ):
        assert required in spec, required


def test_future_semantic_preconditions_and_fail_closed_cases_are_locked() -> None:
    spec = _normalized(JOIN_SPEC_PATH)

    for required in (
        "selected relationship metadata exists and is semantically valid",
        "selected relationship has exactly two validated endpoints",
        "base relation is statically known and matches exactly one selected endpoint",
        "joined endpoint is explicitly selected and statically known",
        "endpoint schemas are statically known",
        "supported cardinality/fanout posture is known",
        "endpoint qualification makes every field owner deterministic",
        "scope visibility for future `where`, `select`, and `order by` is "
        "defined before implementation",
        "PostgreSQL/MySQL can faithfully lower the same accepted semantic subset",
        "unknown relationship",
        "duplicate relationship",
        "ambiguous relationship selection",
        "base relation not matching selected relationship endpoint",
        "ambiguous endpoint owner",
        "self-relationship without explicit disambiguation",
        "ambiguous field qualification",
        "duplicate visible field owner",
        "missing grain",
        "unknown grain",
        "contradictory grain",
        "unsupported cardinality",
        "unsupported `many-to-many`",
        "unsupported fanout-producing posture",
        "unknown endpoint schema",
        "backend cannot preserve semantic ownership, qualification, "
        "grain/cardinality, or join shape",
    ):
        assert required in spec, required


def test_contract_forbids_runtime_project_inference_and_introspection_surfaces() -> (
    None
):
    spec = _normalized(JOIN_SPEC_PATH)

    for required in (
        "any request for graph traversal, chaining, inference, project "
        "aggregation, DB introspection, runtime execution, or security behavior",
        "hidden runtime row combination",
        "in-memory JOIN fallback",
        "connector execution",
        "DB schema introspection",
        "backend-specific approximation",
        "relationship graph traversal",
        "automatic join inference",
        "SQL execution",
        "runtime security",
        "database/schema introspection or db pull",
        "graph/ERD/AI metadata export",
    ):
        assert required in spec, required


def test_postgres_mysql_parity_and_deferred_sql_shape_are_locked() -> None:
    spec = _normalized(JOIN_SPEC_PATH)

    for required in (
        "PostgreSQL and MySQL must either both accept and faithfully lower the "
        "same subset or both fail closed with deterministic diagnostics",
        "preserve endpoint ownership and field qualification in deterministic "
        "SQL aliases",
        "keep deterministic SQL artifact bytes",
        "The exact SQL join kind and alias generation are deferred",
        "Slice 3 does not add semantic validation, diagnostics, Semantic IR "
        "fields, or SQL lowering",
    ):
        assert required in spec, required


def test_phase33_project_json_boundaries_remain_preserved() -> None:
    spec = _normalized(JOIN_SPEC_PATH)

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "single-file `pietto check --format json` remains JSON v1",
        "single-file `pietto emit-sql --format json` remains JSON v1",
        "single-file `pietto explain --format json` remains Semantic Metadata "
        "Artifact v1",
        "Slice 3 adds no project source selection",
        "Project JSON v2 schema change",
        "Semantic Metadata Artifact v1 schema change",
    ):
        assert required in spec, required


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = _phase34_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in combined
    assert "no tag/release/publish/upload/signing/attestation occurred" in combined
    assert "No tag/release/publish/upload/signing/attestation is performed" in combined

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in combined.lower(), forbidden


def _phase34_docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (PLAN_PATH, BOUNDARY_SPEC_PATH, GRAIN_SPEC_PATH, JOIN_SPEC_PATH)
    )
