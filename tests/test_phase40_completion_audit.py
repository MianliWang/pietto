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

PHASE40_PLAN_PATH = REPO_ROOT / "docs/plan/phase-40-let-binding-model-candidate.md"
PHASE40_SYNTAX_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md"
)
PHASE40_AGGREGATE_BOUNDARY_PATH = (
    REPO_ROOT / "docs/spec/phase40-let-binding-aggregate-interaction-boundary-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE40_DOC_PATHS = (
    "docs/plan/phase-40-let-binding-model-candidate.md",
    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
    "docs/spec/phase40-let-binding-aggregate-interaction-boundary-v1.md",
)

PHASE40_TEST_PATHS = (
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
    "tests/test_phase40_let_binding_parser_ast.py",
    "tests/test_phase40_let_binding_row_level_semantics.py",
    "tests/test_phase40_let_binding_semantic_model_ir_readiness.py",
    "tests/test_phase40_let_binding_ir_sql_lowering.py",
    "tests/test_phase40_let_binding_cli_json_metadata.py",
    "tests/test_phase40_let_binding_aggregate_interaction_boundary.py",
    "tests/test_phase40_let_binding_boundary_regression_matrix.py",
    "tests/test_phase40_completion_audit.py",
)

PHASE40_IMPLEMENTATION_EVIDENCE_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/let_bindings.py",
    "src/pietto/semantic/model.py",
    "src/pietto/ir/model.py",
    "src/pietto/ir/builder.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/sql/relations.py",
    "src/pietto/sql/mysql_relations.py",
)

PUBLIC_JSON_METADATA_PATHS = (
    "src/pietto/_metadata",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
)

ALLOWED_SLICE10_CHANGED_PATHS = {
    "docs/plan/phase-40-let-binding-model-candidate.md",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase40_completion_audit.py",
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/diagnostics.md",
    "src",
    "grammar",
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
    return _normalized(PHASE40_PLAN_PATH)


def _phase40_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in (
            *PHASE40_DOC_PATHS,
            *PHASE40_TEST_PATHS,
            *PHASE40_IMPLEMENTATION_EVIDENCE_PATHS,
        )
    )


def _release_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path) for relative_path in PHASE40_DOC_PATHS
    )


def _public_json_metadata_text() -> str:
    return " ".join(
        _normalized(path)
        for relative_path in PUBLIC_JSON_METADATA_PATHS
        for path in sorted((REPO_ROOT / relative_path).glob("**/*.py"))
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


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase40_artifact_inventory_is_complete_through_slice10() -> None:
    for relative_path in (*PHASE40_DOC_PATHS, *PHASE40_TEST_PATHS):
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _plan()
    for required in (
        "| 1 | Let Binding Model Candidate Decision |",
        "| 2 | Let Binding Syntax And Scope Contract |",
        "| 3 | Let Binding Parser And AST Surface |",
        "| 4 | Row-level Let Semantic Validation |",
        "| 5 | Let Binding Semantic Model Storage |",
        "| 6 | Let Binding IR Lowering MVP |",
        "| 7 | Let Binding SQL Lowering MVP |",
        "| 8 | CLI / JSON / Metadata Compatibility Hardening |",
        "| 9 | Let Binding Boundary Regression Matrix |",
        "| 10 | Completion Audit And Status Lock |",
    ):
        assert required in plan, required


def test_phase40_final_completion_status_is_locked_in_plan() -> None:
    plan = _plan()

    for required in (
        "Phase 40 Slice 10 is Completion Audit And Status Lock",
        "docs/plan status-lock and tests/static-audit completion work only",
        "adds no new language behavior",
        "does not start Phase 41",
        "Phase 40 is complete as a ten-slice let binding phase",
        "Slice 1 Let Binding Model Candidate Decision is complete",
        "Slice 2 Let Binding Syntax And Scope Contract is complete",
        "Slice 3 Let Binding Parser And AST Surface is complete",
        "Slice 4 Row-level Let Semantic Validation is complete",
        "Slice 5 Let Binding Semantic Model Storage is complete",
        "Slice 6 Let Binding Row-level IR/SQL Inline Expansion MVP is complete",
        "Slice 7 CLI / JSON / Metadata Compatibility Hardening is complete",
        "Slice 8 Aggregate Interaction Boundary Hardening is complete",
        "Slice 9 Boundary Regression Matrix is complete",
        "Slice 10 completion audit/status lock is complete once Gate 3 records",
        "natural CI `headSha` verification",
    ):
        assert required in plan, required

    assert "Phase 41 implementation" not in plan
    assert "Phase 41 behavior" not in plan


def test_supported_row_level_let_surface_is_locked() -> None:
    evidence = _phase40_evidence()

    for required in (
        "letClause",
        "letBinding",
        "class LetBinding",
        "class LetClause",
        "row-level `where` may reference let names",
        "grouped pre-aggregate `where` may reference let names",
        "no-GROUP non-aggregate `select` may reference let names",
        "no-GROUP input-scope `order by` may reference let names",
        "LetScopeSemanticInfo",
        "let_scopes",
        "let_expansions",
        "supported let references are IR inline-expanded",
        "PostgreSQL and private MySQL SQL are emitted through existing renderers",
        "emit-sql --format json",
        "emit-sql --output",
        "explain --format json",
    ):
        assert required in evidence, required


def test_deferred_and_fail_closed_boundaries_are_locked() -> None:
    evidence = _phase40_evidence()

    for required in (
        "aggregate-let remains deferred",
        "`sum(gross)`",
        "`avg(gross)`",
        "`count(gross)`",
        "`count_distinct(gross)`",
        "`group by gross` remains deferred/fail-closed",
        "`satisfying: gross > 0` remains deferred/fail-closed",
        "grouped `order by gross` remains deferred/fail-closed",
        "`limit gross` remains deferred/fail-closed",
        "qualified let references such as `orders.gross` remain rejected",
        "duplicate, shadowing, self-reference, later-reference, and cycle-like",
        "projection aliases remain output names only and do not become expression leaves",
        "Projection aliases remain output names only",
        "PIE-S2329",
        "PIE-S2330",
    ):
        assert required in evidence, required


def test_ir_sql_metadata_and_artifact_guardrails_are_locked() -> None:
    evidence = _phase40_evidence()
    ir_text = " ".join(
        _read(REPO_ROOT / relative_path)
        for relative_path in (
            "src/pietto/ir/model.py",
            "src/pietto/ir/builder.py",
            "src/pietto/ir/lowering.py",
        )
    )

    for required in (
        "no `LetBindingIR`",
        "no `RelationLayerIR`",
        "no hidden CTE insertion",
        "no hidden subquery insertion",
        "no public `let_scopes` metadata key",
        "no metadata schema expansion",
        "examples, fixtures, or goldens",
        "no package metadata or package version change",
    ):
        assert required in evidence, required

    assert "LetBindingIR" not in ir_text
    assert "RelationLayerIR" not in ir_text
    assert "let_scopes" not in _public_json_metadata_text()


def test_package_version_release_and_phase41_non_authorization_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()
    release_evidence = _release_evidence().lower()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "package version remains `0.1.0`",
        "no release/tag/publish/upload/signing/attestation",
        "does not start Phase 41",
    ):
        assert required in plan, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in release_evidence, forbidden


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

    assert diff_paths <= ALLOWED_SLICE10_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE10_CHANGED_PATHS


def test_changed_set_is_slice10_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert status_paths <= ALLOWED_SLICE10_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE10_CHANGED_PATHS
            for path in status_paths
        )
