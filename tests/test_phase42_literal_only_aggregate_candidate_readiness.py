from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md"
)
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
AGGREGATES_SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER_PATH = REPO_ROOT / "src/pietto/ast_builder.py"

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    'source orders: Order is postgres.table("orders")\n'
)

FUTURE_SUM_AVG_LITERAL_ONLY_NUMERIC_CANDIDATES = frozenset(
    {
        "sum(Int literal-only expression)",
        "sum(Float literal-only expression)",
        "avg(Int literal-only expression)",
        "avg(Float literal-only expression)",
    }
)
SEPARATE_COMPATIBILITY_CANDIDATES = frozenset(
    {
        "count(1)",
        "count(constant)",
    }
)
DEFERRED_LITERAL_ONLY_FORMS = frozenset(
    {
        "count_distinct(literal)",
        "min(literal)",
        "max(literal)",
        "Text literal aggregate",
        "Bool literal aggregate",
        "Null literal aggregate",
        "Decimal literal aggregate",
    }
)


def test_phase42_slice6_plan_alignment_and_guardrails_are_documented() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    register = _normalized(REGISTER_PATH)
    combined = f"{plan} {spec} {register}"

    for required in (
        "| 6 | Literal-only Aggregate Argument Candidate |",
        "Decimal precision fusion still requires a later design",
        "Later literal-only aggregate support must update semantic, IR, PostgreSQL, and private MySQL guardrails together",
        "must preserve `SUM(constant)` instead of rewriting to `constant * COUNT(*)`",
        "`sum(1 + 2)` and `sum(1.23)` must lower and render as `SUM(constant)` or `SUM(expression)`",
        "SQL `SUM` over empty input returns `NULL` while `COUNT(*)` returns `0`",
        "Decimal literal syntax requires future grammar/AST/parser approval",
        "Phase 42 Slice 5 adds only a private direct-field expression fact carrier scaffold",
        "Aggregate typeclass, literal-only aggregate behavior, expression/literal group keys, grouped let ordering outside the approved Phase 43 Slice 5 direct selected-field subset, raw `satisfying` let-name behavior outside the approved Phase 43 Slice 6 selected aggregate-wrapped let subset, and `limit let_name` behavior unfreeze only when a later implementation slice is explicitly approved",
    ):
        assert required in combined, required

    for forbidden in (
        "literal-only aggregates are implemented",
        "Decimal precision fusion is implemented",
        "Decimal literals are implemented",
    ):
        assert forbidden not in combined, forbidden


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(1)",
        "value = sum(1 + 2)",
        "value = sum(1.23)",
        "value = avg(1)",
        "value = avg(1.23)",
        "value = count(1)",
        "value = count(1 + 2)",
        'value = count("x")',
        "value = count(true)",
        "value = count_distinct(1)",
        'value = count_distinct("x")',
        "value = min(1)",
        "value = max(1)",
    ],
)
def test_literal_only_aggregate_arguments_currently_fail_closed(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _error_codes(result) == ["PIE-S2315"]


def test_literal_only_guard_sources_still_require_field_leaves_today() -> None:
    aggregate_source = _read(AGGREGATES_SOURCE_PATH)
    postgres_source = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql_source = _read(MYSQL_EXPRESSIONS_PATH)

    for required in (
        "return is_valid and has_field",
        "has_field",
        "has_literal",
        "deferred_argument_expression_diagnostic",
        "is_supported_semantic_aggregate_argument_expression",
    ):
        assert required in aggregate_source, required

    for renderer_source in (postgres_source, mysql_source):
        assert "_numeric_aggregate_argument_type" in renderer_source
        assert "has_literal and (not has_field or expression_type not in" in (
            renderer_source
        )
        assert "constant * COUNT" not in renderer_source


def test_future_candidate_matrix_remains_narrow_and_explicit() -> None:
    assert FUTURE_SUM_AVG_LITERAL_ONLY_NUMERIC_CANDIDATES == {
        "sum(Int literal-only expression)",
        "sum(Float literal-only expression)",
        "avg(Int literal-only expression)",
        "avg(Float literal-only expression)",
    }
    assert SEPARATE_COMPATIBILITY_CANDIDATES == {
        "count(1)",
        "count(constant)",
    }
    assert DEFERRED_LITERAL_ONLY_FORMS == {
        "count_distinct(literal)",
        "min(literal)",
        "max(literal)",
        "Text literal aggregate",
        "Bool literal aggregate",
        "Null literal aggregate",
        "Decimal literal aggregate",
    }


def test_float_literals_and_decimal_literal_absence_remain_locked() -> None:
    script = _parse(
        SOURCE_PREFIX + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        value = 1.23\n"
    )
    result = analyze(script)
    relation = _relation(script)
    expression = relation.select_items[0].expression
    value_type = result.model.expression_value_types[expression]

    assert _error_codes(result) == []
    assert value_type.resolved_type.name == "Float"
    assert value_type.nullability is EffectiveNullability.NON_NULL

    grammar = _read(GRAMMAR_PATH)
    ast_nodes = _read(AST_NODES_PATH)
    ast_builder = _read(AST_BUILDER_PATH)

    assert "NUMBER\n    : DIGIT+ ('.' DIGIT+)?" in grammar
    assert "value: str | int | float | bool | None" in ast_nodes
    assert 'value = float(text) if "." in text else int(text)' in ast_builder
    assert "raw" not in _normalized(AST_NODES_PATH)


def test_public_and_forbidden_surface_boundaries_remain_documented() -> None:
    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "grammar/generated changes",
        "SQL output changes",
        "IR model or lowering behavior changes",
        "CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1",
        "new diagnostic codes",
        "warning/lint infrastructure",
        "runtime/database execution",
        "project/multi-file execution",
        "relationship/JOIN-driven query behavior",
        "private MySQL aggregate renderer guard changes",
        "PostgreSQL or private MySQL SQL renderer behavior changes",
        "Decimal literal syntax",
        "cast syntax",
        "Decimal multiplication",
        "mixed `Decimal`/`Float`",
        "aggregate precision propagation",
    ):
        assert required in combined, required


def _parse(source: str) -> Script:
    result = parse_source(source)

    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(script: Script) -> TableDef:
    relations = [
        definition
        for definition in script.definitions
        if isinstance(definition, TableDef)
    ]
    assert len(relations) == 1
    return relations[0]


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())
