from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-27-grouped-result-ordering-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/grouped-result-ordering-v1.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_phase27_slice1_artifacts_exist_and_record_status() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    for required in (
        "Phase 27 is complete. Slices 1 through 6 cover candidate decision "
        "and exact contract, grouped result-order semantic validation, IR "
        "lowering, PostgreSQL and private MySQL SQL lowering, CLI / JSON / "
        "output hardening, and completion audit/status lock",
        "Status: complete as candidate decision, exact contract, and static "
        "audit work only",
        "Grouped Result Ordering MVP",
        "HEAD: `80245a301b6281c8e92efd7f88b2e868ab643649`",
        "Phase 26 Aggregate Expression Arguments + Numeric Expression "
        "Foundation is complete",
    ):
        assert required in plan
    for required in (
        "Status: Phase 27 is complete for the grouped result-ordering MVP",
        "The implemented behavior is limited to grouped result-scope `ORDER "
        "BY` over bare selected output names",
        "SQL renders underlying selected expressions, not SELECT aliases",
        "Phase 27 changes no grammar, generated ANTLR, AST, AST builder, "
        "JSON schema, JSON serializer, fixture, golden, script, dependency, "
        "lockfile, package metadata, CI, Makefile/config, public API",
    ):
        assert required in spec


def test_slice1_boundary_is_docs_plan_spec_static_audit_and_status_only() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "docs/spec/grouped-result-ordering-v1.md",
        "docs/plan/phase-27-grouped-result-ordering-mvp.md",
        "tests/test_phase27_grouped_order_candidate_decision.py",
        "minimal status updates in `README.md`, `AGENTS.md`, and "
        "`docs/spec/pietto-v0.9.md`",
        "no `src/` changes",
        "no grammar, generated ANTLR, AST, AST builder, semantic, IR, SQL, "
        "CLI, JSON, fixture, golden, script, dependency, CI, package metadata, "
        "public API, relationship/JOIN, project, runtime, or database behavior "
        "changes",
    ):
        assert required in plan
    for required in (
        "runtime/database behavior",
        "schema introspection",
        "public MySQL API",
        "relationship/JOIN behavior",
        "JSON schema",
        "JSON serializer",
    ):
        assert required in spec


def test_phase12_phase21_phase25_phase26_baselines_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    phase12_order = _normalized(REPO_ROOT / "docs/spec/order-limit-contract-v1.md")
    phase21_plan = _normalized(
        REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"
    )
    phase26_plan = _normalized(
        REPO_ROOT
        / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
    )

    for required in (
        "Phase 12 baseline",
        "no-GROUP input-scope `order by:` and static `limit`",
        "no-GROUP projection aliases are still not in `ORDER BY` scope",
        "Phase 21 baseline",
        "Phase 21 originally kept grouped `order by:` deferred through `PIE-S2321`",
        "`RelationIR.group_keys` is the existing grouped relation seam",
        "Phase 25/26 alias-normalization precedent",
        "`satisfying:` resolves select output names in source",
        "IR/SQL lowering uses underlying select expressions rather than SELECT aliases",
    ):
        assert required in plan
    assert (
        "Projection aliases are not members of the `ORDER BY` name-resolution scope"
        in (phase12_order)
    )
    assert "grouped `order by` emits `PIE-S2321` and remains deferred" in (phase21_plan)
    assert "proving HAVING uses the normalized underlying aggregate expression" in (
        phase26_plan
    )
    assert "Phase 25 and Phase 26 establish the portability precedent" in spec


def test_existing_parser_ast_and_ir_surface_already_support_clause_shape() -> None:
    grammar = _read(REPO_ROOT / "grammar/Pietto.g4")
    ast_nodes = _read(REPO_ROOT / "src/pietto/ast_nodes.py")
    ir_model = _read(REPO_ROOT / "src/pietto/ir/model.py")

    assert (
        "tableBody\n"
        "    : NEWLINE* fromClause NEWLINE* whereClause? NEWLINE* "
        "groupByClause? NEWLINE* selectClause NEWLINE* satisfyingClause? "
        "NEWLINE* orderByClause? NEWLINE* limitClause? NEWLINE*"
    ) in grammar
    assert "orderItem\n    : expression (ASC | DESC)? NEWLINE" in grammar
    assert "class OrderByClause(Node):" in ast_nodes
    assert "order_by_clause: OrderByClause | None = None" in ast_nodes
    assert "class OrderItemIR:" in ir_model
    assert "order_by: tuple[OrderItemIR, ...] = ()" in ir_model


def test_exact_accepted_grouped_order_subset_is_locked() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 27 supports only grouped result-scope `ORDER BY` over bare "
        "selected output names",
        "the relation contains `group by:`",
        "the item expression is a bare name",
        "the name resolves to exactly one selected output name",
        "group-key projection output",
        "direct aggregate projection output",
        "Phase 26 aggregate-expression projection output",
        "`sum(amount + tax)`",
        "`avg(score * weight)`",
        "`count_distinct(lower(trim(status)))`",
        "omitted direction lowering to `ASC`",
        "duplicate order items are preserved",
    ):
        assert required in spec
    for required in (
        "only relations with `group by:`",
        "only bare `order by:` names that resolve to selected output names",
        "selected Phase 26 aggregate-expression projection outputs",
        "source-ordered and duplicate-preserving order items",
    ):
        assert required in plan


def test_sql_lowering_uses_underlying_expression_not_select_alias() -> None:
    spec = _read(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    for required in (
        "Grouped result ordering must render the selected output's underlying "
        "expression. It must not rely on SELECT aliases for portability.",
        'SUM(("amount" + "tax")) DESC',
        '"region" ASC',
        '"total" DESC',
        "SELECT\nFROM\nWHERE\nGROUP BY\nHAVING\nORDER BY\nLIMIT",
    ):
        assert required in spec
    for required in (
        "SQL lowering must render underlying selected expressions rather than "
        "SELECT aliases",
        "`order by: total desc` where `total = sum(amount + tax)` renders the "
        "backend aggregate expression",
        'not `"total" DESC` or `` `total` DESC ``',
    ):
        assert required in plan


def test_diagnostic_strategy_keeps_s2321_without_new_code() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)
    diagnostics = _read(REPO_ROOT / "docs/spec/diagnostics.md")

    assert "| `PIE-S2321` | Grouped ORDER BY is deferred |" in diagnostics
    for required in (
        "Phase 27 keeps `PIE-S2321` as the grouped `order by:` unsupported "
        "diagnostic family",
        "It does not add `PIE-S2328` or reserve any new diagnostic code",
        "unknown grouped select output names",
        "Parser-owned malformed shapes",
        "`order by: 1` remain parser errors through `PIE-P1000`",
        "No-GROUP `order by:` remains Phase 12 input-scope behavior",
    ):
        assert required in spec
    assert "It does not add a new `PIE-S2328` diagnostic in the MVP" in plan


def test_backend_placement_and_current_grouped_order_guard_are_acknowledged() -> None:
    postgres = _read(REPO_ROOT / "src/pietto/sql/relations.py")
    mysql = _read(REPO_ROOT / "src/pietto/sql/mysql_relations.py")
    phase25_sql_tests = _read(REPO_ROOT / "tests/test_phase25_satisfying_sql.py")

    for renderer in (postgres, mysql):
        assert 'lines.extend(\n            (\n                "HAVING",' in renderer
        assert 'lines.extend(\n            (\n                "ORDER BY",' in renderer
        assert "if relation.order_by:" in renderer
        assert "def _validate_grouped_order_by(" in renderer
        assert "grouped ORDER BY expression must match a selected" in renderer
        assert "grouped ORDER BY is not supported" not in renderer
    assert 'sql.index("GROUP BY") < sql.index("HAVING") < sql.index("LIMIT")' in (
        phase25_sql_tests
    )


def test_slice_plan_and_validation_commands_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Slice 1: Candidate Decision And Exact Contract",
        "Slice 2: Grouped Result Ordering Semantics",
        "Slice 3: IR Lowering",
        "Slice 4: PostgreSQL And Private MySQL SQL Lowering",
        "Slice 5: CLI / JSON / Output Hardening",
        "Slice 6: Completion Audit And Status Lock",
        "uv run pytest tests/test_phase27_grouped_order_candidate_decision.py",
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert required in plan


def test_required_non_goals_remain_explicitly_deferred() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    for required in (
        "grammar/generated/AST changes",
        "a new keyword",
        "broad `ORDER BY` / `LIMIT` redesign",
        "no-GROUP projection-alias ordering",
        "no-GROUP `satisfying:`",
        "direct aggregate calls inside `order by:`",
        "arbitrary grouped order expressions",
        "ordinal ordering",
        "`NULLS FIRST` / `NULLS LAST`",
        "collation",
        "offset, fetch, or ties",
        "aggregate argument widening",
        "JOIN, relationship traversal, or relationship composition",
        "project/multi-file implementation",
        "runtime/database execution",
        "schema introspection",
        "JSON schema change",
        "public MySQL API or CLI expansion",
        "fixtures, goldens, scripts, dependencies, CI, package metadata, "
        "Makefile, or lockfile changes unless separately authorized",
    ):
        assert required in plan
    for required in (
        "direct aggregate calls inside `order by:`",
        "arbitrary grouped order expressions",
        "JSON schema or serializer changes",
        "public MySQL API expansion",
        "fixtures, goldens, scripts, dependencies, CI, package metadata, "
        "Makefile, or lockfile changes unless separately authorized",
    ):
        assert required in spec


def test_status_docs_record_phase27_completion_without_broadening_scope() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        text = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 27 Grouped Result Ordering MVP",
            "complete",
            "grouped result-scope `ORDER BY` over bare selected output names",
            "SQL renders the underlying selected expression rather than the "
            "SELECT alias",
            "Unsupported grouped order source shapes continue to use existing "
            "diagnostics such as `PIE-S2321`",
            "no arbitrary grouped `ORDER BY` expressions",
            "direct aggregate calls inside source `order by:`",
            "ordinal ordering",
            "no-GROUP projection-alias ordering",
            "JSON schema change",
            "CLI option change",
            "public MySQL API expansion",
            "runtime/database execution",
            "project/multi-file behavior",
            "relationship/JOIN behavior",
        ):
            assert required in text
