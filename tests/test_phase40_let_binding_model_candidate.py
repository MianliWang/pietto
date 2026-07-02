from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized

from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS as PHASE40_SLICE3_REPAIR_CHANGED_PATHS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-40-let-binding-model-candidate.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_RELATION_SCHEMAS_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
SEMANTIC_SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/relations.py"
MYSQL_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_relations.py"
PHASE38_BINDING_ROADMAP_PATH = (
    REPO_ROOT / "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md"
)
PHASE39_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-39-count-family-implementation-candidate.md"
)

ALLOWED_SLICE1_CHANGED_PATHS = {
    "docs/plan/phase-40-let-binding-model-candidate.md",
    "tests/test_phase40_let_binding_model_candidate.py",
    "docs/spec/diagnostics.md",
    "grammar/Pietto.g4",
    "src/pietto/ast_builder.py",
    "src/pietto/ast_nodes.py",
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/generated/__init__.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/let_bindings.py",
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/relation_schemas.py",
    "tests/test_phase40_let_binding_parser_ast.py",
    "tests/test_phase40_let_binding_row_level_semantics.py",
    "tests/test_phase40_let_binding_semantic_model_ir_readiness.py",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
}
ALLOWED_SLICE1_CHANGED_PATHS = (
    ALLOWED_SLICE1_CHANGED_PATHS | PHASE40_SLICE3_REPAIR_CHANGED_PATHS
)

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            GRAMMAR_PATH,
            AST_NODES_PATH,
            SEMANTIC_EXPRESSIONS_PATH,
            SEMANTIC_RELATION_SCHEMAS_PATH,
            SEMANTIC_SATISFYING_PATH,
            IR_MODEL_PATH,
            POSTGRES_RELATIONS_PATH,
            MYSQL_RELATIONS_PATH,
            PHASE38_BINDING_ROADMAP_PATH,
            PHASE39_PLAN_PATH,
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


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase40_candidate_doc_exists_and_names_let_binding_direction() -> None:
    assert PLAN_PATH.is_file()
    plan = _plan()

    for required in (
        "# Phase 40 Let Binding Model Candidate Decision",
        "Phase 40 theme: `let:` binding model",
        "Let binding model candidate and row-level expression reuse readiness",
        "choose explicit `let:`-style binding as the preferred direction",
        "define a ten-slice Phase 40 roadmap",
        "docs/plan/static-audit/tests-only",
        "implements no behavior change",
    ):
        assert required in plan, required


def test_phase39_trusted_baseline_is_recorded() -> None:
    plan = _plan()

    for required in (
        "baseline HEAD: `2144b4912c7d75d138e6c3d838551b4ccf762bff`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 39 count expression implementation audit`",
        "latest completed phase: Phase 39 Count Family Implementation Candidate",
        "package version remains `0.1.0`",
        "Phase 39 completed the count-family implementation audit",
    ):
        assert required in plan, required


def test_repo_derived_readiness_facts_are_evidence_backed() -> None:
    evidence = _evidence()

    for required in (
        "uses one shared `tableBody` for both `table` and `query` definitions",
        "from`, optional `where`, optional `group by`, required `select`",
        "selectItem",
        "identifier ASSIGN expression NEWLINE",
        "source users: User is postgres.table",
        "class TableDef",
        "class QueryDef",
        "There is no `LetClause` or `LetBinding` AST node",
        "Current relation `where`, no-GROUP `select`, and input-scope `order by`",
        "def type_relation_expressions",
        "def _name_value_type",
        "Projection aliases become output field names after projection",
        "def _projection_output_name",
        "def _computed_row_field",
        "`satisfying:` has a separate selected-output-name scope",
        "def _satisfying_output_scope",
        "class RelationIR",
        "result_predicate: ResultPredicateIR | None = None",
        "There is no `RelationLayerIR`",
        "def render_relation_sql",
        "def render_mysql_relation",
        "Relationship metadata remains metadata/readiness only",
    ):
        assert required in evidence, required

    assert "There is no `LetClause` or `LetBinding` AST node" in _plan()
    assert "RelationLayerIR" not in _read(IR_MODEL_PATH)


def test_projection_aliases_are_not_promoted_to_expression_leaves() -> None:
    plan = _plan()

    for required in (
        "Explicit `let:` binding is preferred over projection-alias reuse",
        "Projection aliases are public output field names",
        "Reusing them as hidden input variables would retroactively change",
        "Projection aliases do not enter same-relation `where`",
        "projection aliases must not become expression leaves",
        "Projection alias syntax remains `alias = expression`",
        "SQL-style expression `AS alias` source syntax remains unaccepted",
        "top-level `relation ...:` source syntax remains unaccepted",
    ):
        assert required in plan, required


def test_mvp_boundary_keeps_let_row_level_only() -> None:
    plan = _plan()

    for required in (
        "`let:` is row-level only",
        "`let:` bindings are reusable scalar expressions",
        "`let:` bindings are immutable within one relation body",
        "`let:` bindings are source-ordered and deterministic",
        "`let:` bindings may reference input fields",
        "`let:` bindings must not reference later bindings",
        "duplicate `let:` names fail closed",
        "unresolved `let:` references fail closed",
        "`satisfying:` remains the result predicate surface",
    ):
        assert required in plan, required


def test_deferred_and_forbidden_behavior_is_locked() -> None:
    plan = _plan()

    for required in (
        "projection alias expression reuse",
        "aggregate-level `let` binding",
        "aggregate binding in `satisfying:`",
        "post-aggregate expression composition",
        "`RelationLayerIR`",
        "hidden CTE insertion",
        "hidden subquery insertion",
        "nested aggregate composition",
        "aggregate filters or SQL `FILTER (WHERE ...)`",
        "`count_if(predicate)`",
        "public MySQL API expansion",
        "relationship-driven lookup or JOIN behavior",
        "endpoint-qualified field lookup",
        "relation composition",
        "runtime/database execution",
        "project/multi-file behavior",
        "schema introspection or db pull behavior",
        "policy/security DSL behavior",
        "package version changes or release operations",
    ):
        assert required in plan, required


def test_future_slice2_contract_questions_are_recorded() -> None:
    plan = _plan()

    for required in (
        "Does `let:` appear only after `from` and before `where`",
        "Are `let:` bindings allowed in both `table` and `query` definitions",
        "Which clauses may see `let:` names",
        "May one `let:` binding reference earlier `let:` bindings",
        "May `let:` names shadow input fields, projection aliases, relation names",
        "Are `let:` names bare-only",
        "Are source-qualified field leaves such as `orders.amount` accepted",
        "Are aggregate calls prohibited in all `let:` bindings for the MVP",
        "Does SQL lowering inline `let:` expressions",
        "Recommended defaults for Slice 2 are conservative",
    ):
        assert required in plan, required


def test_phase40_slice_sequence_is_locked() -> None:
    plan = _plan()

    for required in (
        "| 1 | Let Binding Model Candidate Decision | docs/plan/static-audit/tests-only; no behavior change |",
        "| 2 | Let Binding Syntax And Scope Contract | docs/spec/static-audit first; no behavior change unless separately approved |",
        "| 3 | Let Binding Parser And AST Surface | grammar/generated/parser/AST only for the approved syntax |",
        "| 4 | Row-level Let Semantic Validation | semantic validation for names, ordering, duplicates, cycles, and row-level typing |",
        "| 5 | Let Binding Semantic Model Storage | immutable semantic facts for approved bindings without public output widening |",
        "| 6 | Let Binding IR Lowering MVP | IR lowering for approved row-level binding references and expression facts |",
        "| 7 | Let Binding SQL Lowering MVP | PostgreSQL/private MySQL lowering for the approved IR subset with stable SQL output |",
        "| 8 | CLI / JSON / Metadata Compatibility Hardening | preserve CLI JSON v1, Project JSON v2, and Semantic Metadata Artifact v1 compatibility |",
        "| 9 | Let Binding Boundary Regression Matrix | regression matrix for projection aliases, aggregates, post-aggregate exclusions, and relationship/JOIN non-interaction |",
        "| 10 | Completion Audit And Status Lock | audit/status; no new behavior unless a prior slice separately approved implementation |",
    ):
        assert required in plan, required


def test_slice1_public_surface_constraints_and_allowlist_are_locked() -> None:
    plan = _plan()

    for required in (
        "source/compiler behavior unchanged",
        "grammar and generated parser inventory unchanged",
        "parser and AST behavior unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "examples unchanged",
        "scripts/workflows unchanged",
        "package metadata unchanged",
        "package version remains `0.1.0`",
        "Approved Slice 1 Gate 2 file allowlist:",
        "docs/plan/phase-40-let-binding-model-candidate.md",
        "tests/test_phase40_let_binding_model_candidate.py",
    ):
        assert required in plan, required


def test_forbidden_implementation_surfaces_are_documented() -> None:
    plan = _plan()

    for required in (
        "`src/pietto/**`",
        "`grammar/**`",
        "generated parser files",
        "`examples/**`",
        "`fixtures/**`",
        "golden files",
        "`scripts/**`",
        "`.github/workflows/**`",
        "package metadata such as `pyproject.toml`, `uv.lock`, and version files",
        "`README.md`",
        "`AGENTS.md`",
        "`docs/spec/pietto-v0.9.md`",
        "release/tag/publish/upload/signing/attestation surfaces",
    ):
        assert required in plan, required


def test_validation_plan_and_manual_markdown_formatting_policy_are_recorded() -> None:
    plan = _plan()

    for required in (
        "uv run pytest tests/test_phase40_let_binding_model_candidate.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "git diff --check",
        "uv run ruff format tests/test_phase40_let_binding_model_candidate.py",
        "Do not pass this Markdown plan file to `ruff format`",
        "Markdown formatting remains manual",
        "`/tmp/phase40-slice1-gate2-evidence.txt`",
    ):
        assert required in plan, required


def test_package_version_and_release_non_authorization_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "no tag/release/publish/upload/signing/attestation",
        "no tag/release/publish/upload/signing/attestation is authorized",
        "Gate 2 must not stage, commit, push, start or poll CI",
    ):
        assert required in plan, required

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_unchanged_or_untracked() -> None:
    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(FORBIDDEN_DIFF_PATHS).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert diff_paths <= ALLOWED_SLICE1_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE1_CHANGED_PATHS


def test_changed_set_is_slice1_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert status_paths <= ALLOWED_SLICE1_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE1_CHANGED_PATHS
            for path in status_paths
        )
