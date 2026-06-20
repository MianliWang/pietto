from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-28-numeric-aggregate-refinement-ii.md"
SPEC_PATH = REPO_ROOT / "docs/spec/numeric-literal-aggregate-arguments-v1.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice1_artifacts_exist_and_record_planning_only_status() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 28 Slice 1 is complete as candidate decision, exact contract, "
        "and static audit work only",
        "Phase 28 implementation has not started",
        "Trusted Phase 27 baseline",
        "HEAD: `dcfab7c2a048fa9c29b267c395d5c779994ea128`",
        "Phase 27 Grouped Result Ordering MVP is complete",
        "Slice 1 adds the Phase 28 plan, the numeric literal aggregate "
        "argument contract, focused static audit coverage, and status-only "
        "documentation",
    ):
        assert required in plan

    for required in (
        "Status: Phase 28 Slice 1 is complete as candidate decision, exact "
        "contract, and static audit work only",
        "Phase 28 implementation has not started",
        "admit Int and Float numeric literal leaves inside selected "
        "`sum(...)` and `avg(...)` numeric expression arguments",
        "Slice 1 changes no grammar, generated ANTLR, AST, AST builder, "
        "parser, semantic implementation, IR model or lowering, SQL backend",
    ):
        assert required in spec


def test_candidate_set_and_recommendation_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 28 selects **Numeric / Aggregate Refinement II**",
        "numeric literal aggregate argument MVP",
        "Numeric / Aggregate Refinement II",
        "Explain / Audit Output MVP",
        "Project / Multi-file Readiness II",
        "ORDER BY / LIMIT Expansion II",
        "Relationship / JOIN Readiness",
        "Arrow / PyArrow / Python ecosystem compatibility planning",
        "Chosen. It is the most continuous, bounded, and testable post-Phase "
        "27 direction",
        "Deferred. It risks CLI/JSON surface churn before a contract phase",
        "Deferred. Safe only as planning/readiness; implementation would be broad",
        "Deferred. It is scope-creep-prone immediately after Phase 27",
        "Deferred. It needs a separate readiness gate before implementation",
        "Deferred. It is low-continuity and dependency/runtime-risky",
    ):
        assert required in plan


def test_existing_literal_and_expression_carriers_are_repo_facts() -> None:
    ast_nodes = _read(REPO_ROOT / "src/pietto/ast_nodes.py")
    ir_model = _read(REPO_ROOT / "src/pietto/ir/model.py")
    ir_lowering = _read(REPO_ROOT / "src/pietto/ir/lowering.py")
    semantic_expressions = _read(REPO_ROOT / "src/pietto/semantic/expressions.py")
    postgres_expressions = _read(REPO_ROOT / "src/pietto/sql/expressions.py")
    mysql_expressions = _read(REPO_ROOT / "src/pietto/sql/mysql_expressions.py")

    assert "class LiteralExpr(Expression):" in ast_nodes
    assert "class LiteralIR(ExpressionIR):" in ir_model
    assert "if isinstance(expression, LiteralExpr):" in ir_lowering
    assert "LiteralIR(value=expression.value" in ir_lowering
    assert "def _literal_value_type(expression: LiteralExpr)" in semantic_expressions
    assert 'name = "Int"' in semantic_expressions
    assert 'name = "Float"' in semantic_expressions
    assert "if isinstance(expression, LiteralIR):" in postgres_expressions
    assert "return render_literal(expression.value)" in postgres_expressions
    assert "if isinstance(expression, LiteralIR):" in mysql_expressions
    assert "return render_literal(expression.value)" in mysql_expressions


def test_current_aggregate_literal_boundary_and_future_target_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    aggregates = _read(REPO_ROOT / "src/pietto/semantic/aggregates.py")
    phase26_semantics = _read(
        REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_semantics.py"
    )

    assert "def _is_field_only_numeric_shape(expression: Expression)" in aggregates
    assert "return False" in aggregates
    assert '("value = sum(amount + 1)", "sum")' in phase26_semantics
    assert '("value = avg(score * 2)", "avg")' in phase26_semantics

    for required in (
        "`sum(amount + 1)`",
        "`sum(1 + amount)`",
        "`sum(amount - 1)`",
        "`sum(amount * 2)`",
        "`avg(score * 2)`",
        "`avg(score + 1.5)`",
        "bare or existing single-input qualified field leaves",
        "unary `+` / `-` and binary `+` / `-` / `*`",
        "at least one direct input field leaf",
        "Literal-only aggregate arguments such as `sum(1)` and `avg(1)` "
        "remain rejected",
    ):
        assert required in plan
    for required in (
        "the aggregate function is `sum` or `avg`",
        "the argument expression contains at least one direct input field leaf",
        "literal leaves are only Int or Float scalar literals",
        "the complete argument expression has an existing scalar numeric type "
        "of `Int` or `Float`",
    ):
        assert required in spec


def test_result_type_and_scalar_typing_contract_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    phase26_plan = _normalized(
        REPO_ROOT
        / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
    )

    for required in (
        "`sum(Int expression)` keeps the existing `sum` Int nullable result behavior",
        "`sum(Float expression)` keeps the existing Float nullable result behavior",
        "`avg(Int expression)` keeps the existing Float nullable result behavior",
        "`avg(Float expression)` keeps the existing Float nullable result behavior",
        "mixed Int/Float expression behavior follows existing scalar numeric "
        "typing, not a new promotion system",
    ):
        assert required in plan
        assert required in spec

    for required in (
        "`Int + Float -> Float`",
        "`Float + Int -> Float`",
        "`Int * Float -> Float`",
        "`Float * Int -> Float`",
        "`sum(Int expression) -> Int nullable`",
        "`avg(Int expression) -> Float nullable`",
    ):
        assert required in phase26_plan


def test_diagnostics_and_deferred_shapes_remain_explicit() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    diagnostics = _read(REPO_ROOT / "docs/spec/diagnostics.md")

    assert "| `PIE-S2315` | Aggregate expression argument is deferred |" in diagnostics
    for required in (
        "`PIE-S2315` remains for unsupported aggregate argument shapes",
        "Existing primary diagnostics remain primary",
        "must not force `PIE-S2315` to replace more specific scalar operand "
        "or aggregate diagnostics",
        "No new diagnostic code is reserved by this contract",
        "literal-only aggregate arguments such as `sum(1)` and `avg(1)`",
        "division inside aggregate arguments",
        "modulo inside aggregate arguments",
        "`count(expression)`",
        "`min(expression)`",
        "`max(expression)`",
        "unsupported `count_distinct(...)` expression expansion",
    ):
        assert required in spec
    for required in (
        "`PIE-S2315` remains for unsupported aggregate argument shapes",
        "Existing primary diagnostics remain primary",
        "Phase 28 must not force `PIE-S2315` to replace more specific scalar "
        "operand or aggregate diagnostics",
    ):
        assert required in plan


def test_six_slice_plan_and_validation_commands_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Slice 1: Candidate Decision And Exact Contract",
        "Slice 2: Semantic Acceptance",
        "Slice 3: IR Lowering",
        "Slice 4: PostgreSQL And Private MySQL SQL Lowering",
        "Slice 5: CLI / JSON / Output Hardening",
        "Slice 6: Completion Audit And Status Lock",
        "uv run pytest tests/test_phase28_numeric_literal_aggregate_candidate_decision.py",
        "uv run pytest tests/test_phase28_numeric_literal_aggregate_semantics.py",
        "uv run pytest tests/test_phase28_numeric_literal_aggregate_ir.py",
        "uv run pytest tests/test_phase28_numeric_literal_aggregate_sql.py",
        "uv run pytest tests/test_phase28_numeric_literal_aggregate_cli_json_output.py",
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert required in plan


def test_phase_wide_non_goals_and_slice1_boundaries_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "no production code",
        "no grammar, generated ANTLR, AST, AST builder, parser, semantic "
        "implementation, IR implementation, IR model, SQL backend, CLI "
        "implementation, JSON schema, JSON serializer, fixture, golden, "
        "script, dependency, lockfile, CI, package metadata, public API, "
        "runtime/project, public MySQL API, or relationship/JOIN behavior "
        "changes",
        "Decimal literal aggregate arguments",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal/Int or Decimal/Float promotion",
        "precision/scale modeling",
        "casts",
        "schema introspection",
        "ORDER BY / LIMIT redesign",
        "explain or audit output",
        "project/multi-file behavior or JSON v2",
        "runtime/database execution or connector execution",
        "public MySQL API expansion",
        "relationship/JOIN behavior",
    ):
        assert required in plan

    for required in (
        "grammar, generated ANTLR, AST, AST builder, or parser changes",
        "Decimal literal syntax or Decimal literal aggregate arguments",
        "mixed Decimal/Int or Decimal/Float promotion",
        "`count(expression)`, `min(expression)`, `max(expression)`, or new "
        "`count_distinct(...)` expression forms",
        "JSON schema or CLI option changes",
        "runtime/database execution, connector execution, project/multi-file "
        "behavior, relationship traversal, relationship composition, or JOIN "
        "behavior",
    ):
        assert required in spec


def test_status_docs_record_slice1_without_claiming_implementation() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        text = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 28 Numeric / Aggregate Refinement II",
            "Slice 1 is complete as candidate decision, exact contract, and "
            "static audit work only",
            "Phase 28 implementation has not started",
            "numeric literal aggregate argument MVP",
            "Int and Float numeric literal leaves inside selected `sum(...)` "
            "and `avg(...)` numeric expression arguments",
            "at least one direct input field leaf",
            "literal-only aggregate arguments such as `sum(1)` and `avg(1)` "
            "remain rejected",
            "no Decimal literal, Decimal multiplication, Decimal division, "
            "mixed Decimal promotion, casts, precision/scale modeling, "
            "division, modulo, `count(expression)`, `min(expression)`, "
            "`max(expression)`, `count_distinct(...)` widening",
            "adds no Decimal literal, Decimal multiplication, Decimal "
            "division, mixed Decimal promotion, casts, precision/scale "
            "modeling, division, modulo, `count(expression)`, "
            "`min(expression)`, `max(expression)`, `count_distinct(...)` "
            "widening, grammar, generated ANTLR, AST, parser, IR model, SQL "
            "fixture/golden, JSON schema, CLI option, dependency, public API, "
            "runtime/project, public MySQL API, or relationship/JOIN changes",
        ):
            assert required in text
