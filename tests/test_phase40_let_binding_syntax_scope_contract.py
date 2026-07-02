from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS as PHASE40_SLICE3_REPAIR_CHANGED_PATHS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

SPEC_PATH = REPO_ROOT / "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md"
PHASE40_PLAN_PATH = REPO_ROOT / "docs/plan/phase-40-let-binding-model-candidate.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER_PATH = REPO_ROOT / "src/pietto/ast_builder.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_RELATION_SCHEMAS_PATH = REPO_ROOT / "src/pietto/semantic/relation_schemas.py"
SEMANTIC_SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/relations.py"
MYSQL_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_relations.py"

ALLOWED_SLICE2_CHANGED_PATHS = {
    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
    "tests/test_phase40_let_binding_syntax_scope_contract.py",
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
    "src/pietto/ir/builder.py",
    "src/pietto/ir/lowering.py",
    "src/pietto/semantic/analyzer.py",
    "src/pietto/semantic/expressions.py",
    "src/pietto/semantic/let_bindings.py",
    "src/pietto/semantic/model.py",
    "src/pietto/semantic/relation_schemas.py",
    "tests/test_phase40_let_binding_ir_sql_lowering.py",
    "tests/test_phase40_let_binding_model_candidate.py",
    "tests/test_phase40_let_binding_parser_ast.py",
    "tests/test_phase40_let_binding_row_level_semantics.py",
    "tests/test_phase40_let_binding_semantic_model_ir_readiness.py",
}
ALLOWED_SLICE2_CHANGED_PATHS = (
    ALLOWED_SLICE2_CHANGED_PATHS | PHASE40_SLICE3_REPAIR_CHANGED_PATHS
)

FORBIDDEN_DIFF_PATHS = (
    "docs/plan/phase-40-let-binding-model-candidate.md",
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


def _spec() -> str:
    return _normalized(SPEC_PATH)


def _repo_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            SPEC_PATH,
            PHASE40_PLAN_PATH,
            GRAMMAR_PATH,
            AST_NODES_PATH,
            AST_BUILDER_PATH,
            SEMANTIC_EXPRESSIONS_PATH,
            SEMANTIC_RELATION_SCHEMAS_PATH,
            SEMANTIC_SATISFYING_PATH,
            SEMANTIC_GROUP_BY_PATH,
            SEMANTIC_AGGREGATES_PATH,
            IR_MODEL_PATH,
            POSTGRES_RELATIONS_PATH,
            MYSQL_RELATIONS_PATH,
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


def _status_path(line: str) -> str:
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_slice2_contract_doc_exists_and_records_guardrails() -> None:
    assert SPEC_PATH.is_file()
    spec = _spec()

    for required in (
        "# Phase 40 Let Binding Syntax And Scope Contract v1",
        "Phase 40 Slice 2 is Let Binding Syntax And Scope Contract",
        "docs/spec/static-audit/tests-only",
        "authorizes no behavior change",
        "does not implement `let:`",
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
        "SQL golden bytes",
        "fixtures/goldens",
        "examples",
        "scripts",
        "workflows",
        "package metadata",
        "lockfiles",
    ):
        assert required in spec, required


def test_trusted_slice1_baseline_is_recorded() -> None:
    spec = _spec()

    for required in (
        "baseline HEAD: `475e3a17978b51d8670db042e66ef7b80672c27e`",
        "baseline branch: `main`",
        "baseline commit: `Add Phase 40 let binding model candidate`",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized",
        "Slice 1 completed the Phase 40 Let Binding Model Candidate Decision",
        "selected explicit `let:` binding over projection-alias expression reuse",
    ):
        assert required in spec, required


def test_repo_derived_grammar_ast_scope_ir_and_sql_facts_are_recorded() -> None:
    evidence = _repo_evidence()

    for required in (
        "uses one shared `tableBody` for both `table` and `query` definitions",
        "from`, optional `where`, optional `group by`, required `select`",
        "optional `satisfying`, optional `order by`, optional `limit`",
        "There is no current `LetClause` or `LetBinding`",
        "Projection aliases are output names",
        "not reusable expression leaves",
        "where`, no-GROUP `select`, and no-GROUP input-scope `order by`",
        "input row-level scope",
        "`satisfying:` and grouped `order by:` use selected-output/result scope",
        "Current `RelationIR` is a single-layer relation model",
        "There is no `RelationLayerIR`",
        "one SELECT and do not insert hidden CTE or hidden subquery layers",
        "tableBody",
        "class TableDef",
        "class QueryDef",
        "def _relation_body",
        "def type_relation_expressions",
        "def _satisfying_output_scope",
        "def _grouped_order_by_diagnostics",
        "class RelationIR",
        "def render_relation_sql",
        "def render_mysql_relation",
    ):
        assert required in evidence, required


def test_future_let_syntax_and_parser_compatibility_contract_is_locked() -> None:
    spec = _spec()

    for required in (
        "future `let:` is one optional relation-body section shared by `table` and `query` definitions",
        "The MVP placement is after `from` and before `where`",
        "The future MVP rejects `let:` after any of these sections",
        "`where`",
        "`group by`",
        "`select`",
        "`satisfying`",
        "`order by`",
        "`limit`",
        "A later parser slice may add `LET: 'let'`",
        "Slice 2 does not implement grammar",
        "Keyword compatibility must be considered",
        "existing identifier behavior is not casually broken",
    ):
        assert required in spec, required


def test_binding_item_syntax_is_name_equals_expression_only() -> None:
    spec = _spec()

    for required in (
        "Each future binding item uses `name = expression`",
        "Binding names follow existing Pietto identifier rules",
        "SQL-style `expression AS name` remains rejected",
        "destructuring is deferred",
        "tuple binding is deferred",
        "multiple assignment is deferred",
        "binding type annotations are deferred",
        "Assignment remains a relation binding item form only",
        "not a general expression form",
    ):
        assert required in spec, required


def test_first_mvp_row_level_visibility_and_deferred_surfaces_are_locked() -> None:
    spec = _spec()

    for required in (
        "The first behavior MVP is row-level only",
        "| `where` | May see let names. |",
        "| no-GROUP `select` | May see let names. |",
        "| no-GROUP input-scope `order by` | May see let names. |",
        "| `group by` | Does not see let names in the first behavior MVP. |",
        "| aggregate arguments | Do not see let names in the first behavior MVP. |",
        "| `satisfying:` | Does not see let names directly and remains selected-output/result scope. |",
        "| grouped `order by` | Does not see let names directly and remains selected-output/result scope. |",
        "| `limit` | Does not see let names. |",
        "Aggregate arguments referencing let names, such as `sum(gross)`, are deferred to a later Phase 40 slice",
        "not permanently rejected by the whole phase",
        "Group-by interaction is deferred to a later contract or behavior slice",
    ):
        assert required in spec, required


def test_dependency_ordering_and_fail_closed_rules_are_locked() -> None:
    spec = _spec()

    for required in (
        "Bindings are source-ordered and deterministic",
        "earlier let references are allowed",
        "later references fail closed",
        "self-reference fails closed",
        "cycles fail closed",
        "unresolved input field references inside binding expressions fail closed",
        "unresolved let references fail closed",
        "deterministic diagnostic ordering",
        "Slice 2 introduces no diagnostics",
    ):
        assert required in spec, required


def test_no_shadowing_and_no_projection_alias_expression_reuse_are_locked() -> None:
    spec = _spec()

    for required in (
        "The future MVP uses a no-shadowing policy",
        "duplicate let names fail closed",
        "let names cannot shadow input fields",
        "let names cannot shadow the input qualifier or relation name",
        "let names cannot shadow projection aliases",
        "projection aliases cannot shadow let names",
        "projection aliases must not become expression leaves",
        "Projection aliases remain output names after the projection boundary",
        "do not become row-level reusable scalar expressions",
        "aggregate argument leaves",
        "hidden input variables",
    ):
        assert required in spec, required


def test_qualification_contract_is_bare_only_for_let_references() -> None:
    spec = _spec()

    for required in (
        "Let references are bare-only",
        "referenced as `gross`, not as `orders.gross`",
        "Source-qualified field leaves such as `orders.amount` remain valid inside let expressions",
        "existing single-input qualifier rules",
        "Qualified let references such as `orders.gross` are rejected",
        "a field reference governed by the existing single-input qualifier contract",
        "not a let-binding qualifier mechanism",
    ):
        assert required in spec, required


def test_aggregate_result_scope_and_relation_layer_boundaries_are_deferred() -> None:
    spec = _spec()

    for required in (
        "Aggregate calls inside `let:` are forbidden for the first behavior MVP",
        "aggregate-level let binding",
        "aggregate arguments referencing let names",
        "aggregate binding in `satisfying:`",
        "post-aggregate expression composition",
        "`RelationLayerIR`",
        "hidden CTE insertion",
        "hidden subquery insertion",
        "relationship-driven lookup or JOIN behavior",
        "`satisfying:` continues to expose Pietto result predicates",
        "not SQL `HAVING` source syntax",
        "Direct SQL `HAVING` syntax remains unavailable",
    ):
        assert required in spec, required


def test_sql_lowering_posture_prefers_inline_and_protects_stable_output() -> None:
    spec = _spec()

    for required in (
        "Later behavior slices should prefer explicit inline expression expansion first",
        "rendering the approved expression at the reference site",
        "after semantic validation and IR lowering have proved it safe",
        "Hidden CTE insertion remains forbidden unless separately approved",
        "Hidden subquery insertion remains forbidden unless separately approved",
        "Stable SQL output must be protected",
        "PostgreSQL and private MySQL parity evidence",
        "current projection aliases, `satisfying:`, grouped ordering, and aggregate boundaries remain stable",
    ):
        assert required in spec, required


def test_diagnostic_posture_is_documented_without_new_codes() -> None:
    spec = _spec()

    for required in (
        "Slice 2 introduces no new diagnostics",
        "changes no diagnostic wording",
        "Later slices may reuse existing diagnostics where appropriate",
        "existing unknown field diagnostics",
        "existing duplicate-name or duplicate-output families",
        "existing aggregate invalid-context, aggregate composition, nested aggregate, and deferred aggregate argument diagnostics",
        "existing `satisfying:` selected-output diagnostics",
        "Let-specific duplicate, shadowing, forward-reference, self-reference, and cycle cases may require new semantic codes later",
        "does not reserve or introduce those codes",
    ):
        assert required in spec, required


def test_package_version_release_and_public_surface_boundaries_are_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    spec = _spec()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    for required in (
        "grammar/generated inventory unchanged",
        "parser and AST behavior unchanged",
        "source/compiler behavior unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "examples/fixtures/goldens unchanged",
        "scripts/workflows unchanged",
        "package metadata unchanged",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in spec, required

    lowered = spec.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_unchanged_or_untracked() -> None:
    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, tuple(FORBIDDEN_DIFF_PATHS)).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert diff_paths <= ALLOWED_SLICE2_CHANGED_PATHS
    assert status_paths <= ALLOWED_SLICE2_CHANGED_PATHS


def test_changed_set_is_slice2_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert status_paths <= ALLOWED_SLICE2_CHANGED_PATHS

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(
            _path_matches(path, forbidden) and path not in ALLOWED_SLICE2_CHANGED_PATHS
            for path in status_paths
        )
