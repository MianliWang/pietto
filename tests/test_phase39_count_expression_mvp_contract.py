from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import ALLOWED_SLICE3_CHANGED_PATHS
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase39-count-expression-mvp-contract-v1.md"
PLAN_PATH = REPO_ROOT / "docs/plan/phase-39-count-family-implementation-candidate.md"
PHASE38_COUNT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-count-family-semantics-contract-v1.md"
)
PHASE38_TYPE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
PHASE38_BINDING_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md"
)
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_RELATION_SCHEMAS_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
IR_LOWERING_PATH = REPO_ROOT / "src/pietto/ir/lowering.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE2_CHANGED_PATHS = {
    "docs/spec/phase39-count-expression-mvp-contract-v1.md",
    "tests/test_phase39_count_expression_mvp_contract.py",
}
FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-39-count-family-implementation-candidate.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _repo_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            PHASE38_COUNT_SPEC_PATH,
            PHASE38_TYPE_SPEC_PATH,
            PHASE38_BINDING_SPEC_PATH,
            SEMANTIC_AGGREGATES_PATH,
            SEMANTIC_RELATION_SCHEMAS_PATH,
            SEMANTIC_GROUP_BY_PATH,
            IR_MODEL_PATH,
            IR_LOWERING_PATH,
            POSTGRES_EXPRESSIONS_PATH,
            MYSQL_EXPRESSIONS_PATH,
        )
    )


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


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase39_slice2_contract_spec_exists_and_is_behavior_preserving() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 39 Count Expression MVP Contract v1",
        "Phase 39 Slice 2 is Count Expression MVP Contract",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not implement `count(expression)`",
        "does not broaden count-family behavior",
        "does not change source/compiler behavior",
        "grammar",
        "generated ANTLR files",
        "parser behavior",
        "AST behavior",
        "semantic behavior",
        "IR behavior",
        "SQL lowering",
        "CLI behavior",
        "JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1",
        "diagnostic envelope shape",
        "SQL golden bytes",
        "fixtures/goldens",
        "scripts",
        "workflows",
        "package metadata",
        "lockfiles",
        "Package version remains `0.1.0`",
    ):
        assert required in spec, required


def test_slice2_allowlist_and_forbidden_surfaces_are_locked() -> None:
    assert ALLOWED_SLICE2_CHANGED_PATHS == {
        "docs/spec/phase39-count-expression-mvp-contract-v1.md",
        "tests/test_phase39_count_expression_mvp_contract.py",
    }

    status_paths = {_status_path(line) for line in _git_status()}
    assert (status_paths <= ALLOWED_SLICE3_CHANGED_PATHS) or _slice5_gate2()

    for path in status_paths:
        for forbidden in FORBIDDEN_DIFF_PATHS:
            if path not in ALLOWED_SLICE3_CHANGED_PATHS:
                assert (not _path_matches(path, forbidden)) or _slice5_gate2(), path

    tracked_diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, tuple(FORBIDDEN_DIFF_PATHS)).splitlines(),
        )
    )
    assert (tracked_diff_paths <= ALLOWED_SLICE3_CHANGED_PATHS) or _slice5_gate2()


def test_repo_evidence_confirms_slice3_semantic_acceptance_and_lowering_deferral() -> (
    None
):
    evidence = _repo_evidence()

    for required in (
        "Count Expression MVP Contract",
        "docs/spec/static-audit first; no behavior change unless separately approved",
        "`count(expression)` | Deferred and fail-closed today",
        "`count(constant)` / `count(1)` | Not current behavior",
        "`count_if(predicate)` | No current aggregate or builtin function surface",
        "expected_semantic_aggregate_arities",
        "return (0, 1)",
        "def is_supported_semantic_aggregate_argument_expression",
        "_is_supported_count_expression_shape",
        "_count_expression_shape",
        '{"lower", "trim", "len"}',
        "Validate the direct aliased no-GROUP aggregate projection shape",
        "project_grouped_schema",
        "class AggregateCallIR",
        "arguments: tuple[ExpressionIR, ...]",
        "class RelationIR",
        "_is_valid_aggregate_projection",
        "_aggregate_type_matches_ir",
        "PostgreSQL aggregate count expects a direct field argument",
        "MySQL aggregate count expects a direct field argument",
    ):
        assert required in evidence, required

    assert "RelationLayerIR" not in _read(IR_MODEL_PATH)


def test_future_count_expression_mvp_boundary_is_locked() -> None:
    spec = _spec()

    for required in (
        "direct aliased aggregate projections only",
        "no-GROUP and grouped contexts may both be in scope",
        "one row-level scalar expression argument only",
        "must include at least one resolved direct input field leaf",
        "supported single-input qualified field leaves count",
        "projection aliases remain output names and are not aggregate argument leaves",
        "known, concrete, non-`Any`, non-Enum, non-Unknown, and dialect-lowerable",
        "numeric, orderable, and distinct-compatible capabilities are not required",
        "result type remains `Int not null`",
        "unsupported shapes must fail closed before SQL rendering",
    ):
        assert required in spec, required


def test_sql_bool_and_diagnostic_contract_are_locked() -> None:
    spec = _spec()

    for required in (
        "SQL non-`NULL` expression-result counting",
        "rows whose expression result is SQL `NULL` are not counted",
        "rows whose expression result is SQL non-`NULL` are counted",
        "SQL lowering expectation is `COUNT(<expression SQL>)`",
        "PostgreSQL and private MySQL lowering may use this form only after semantic validation and IR lowering",
        "current `COUNT(*)` and direct `COUNT(field)` bytes must remain compatible",
        "count non-`NULL` `TRUE` and non-`NULL` `FALSE`",
        "distinct from `count_if(predicate)`",
        "`PIE-S2315`",
        "`PIE-S2314`",
        "`PIE-S2311`",
        "`PIE-S2310`",
        "existing unresolved-field diagnostics",
        "offending nested aggregate call",
    ):
        assert required in spec, required


def test_explicit_exclusions_are_locked() -> None:
    spec = _spec()

    for required in (
        "`count(1)`",
        "`count(constant)`",
        "literal-only count expressions",
        "`count_if(predicate)`",
        "projection aliases as aggregate argument leaves",
        "nested aggregates",
        "aggregate composition",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "broad `sum/avg(expression)`",
        "aggregate filters",
        "SQL-style aggregate modifiers",
        "post-aggregate expressions",
        "`RelationLayerIR`",
        "JOIN/fanout-aware semantics",
        "runtime/database execution",
        "public MySQL API expansion",
        "release/tag/publish/upload/signing/attestation",
        "must not be accepted accidentally",
    ):
        assert required in spec, required


def test_public_surface_release_and_package_boundaries_are_locked() -> None:
    spec = _spec()
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))

    assert pyproject["project"]["version"] == "0.1.0"
    for required in (
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "parser/AST/grammar/generated inventory unchanged",
        "semantic, IR, and SQL behavior unchanged",
        "scripts/workflows/package metadata unchanged",
        "package version remains `0.1.0`",
        "no tag, release, publish/upload, signing, or attestation",
    ):
        assert required in spec, required
