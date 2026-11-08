from __future__ import annotations

import json
from pathlib import Path

import pytest

from pietto import cli
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    Expression,
    Script,
    SelectItem,
    TableDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    price: Decimal\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    status: Text\n"
    'source orders: Order = postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    "expression_source",
    [
        "price + price",
        "price - price",
    ],
)
def test_decimal_add_subtract_computed_projection_schema_is_locked(
    expression_source: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {expression_source}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert isinstance(expression, BinaryExpr)
    assert result.diagnostics == ()
    assert field.resolved_type.name == "Decimal"
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.resolved_type.name == "Decimal"
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_decimal_arithmetic_inside_decimal_comparison_shape_is_locked() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table filtered:\n"
            "    from orders\n"
            "    where price - price == price - price\n"
            "    select:\n"
            "        price\n"
        )
    )
    relation = _relation(result)
    assert relation.where_clause is not None
    where_expression = relation.where_clause.expression
    assert isinstance(where_expression, ComparisonExpr)
    assert isinstance(where_expression.left, BinaryExpr)
    assert isinstance(where_expression.right, BinaryExpr)

    left_type = result.model.expression_value_types[where_expression.left]
    right_type = result.model.expression_value_types[where_expression.right]
    where_type = result.model.expression_value_types[where_expression]

    assert result.diagnostics == ()
    assert left_type.resolved_type.name == "Decimal"
    assert left_type.nullability is EffectiveNullability.UNKNOWN
    assert right_type.resolved_type.name == "Decimal"
    assert right_type.nullability is EffectiveNullability.UNKNOWN
    assert where_type.resolved_type.name == "Bool"
    assert where_type.nullability is EffectiveNullability.UNKNOWN


_DECIMAL_FLOAT = "a Decimal does not mix with a Float in `+`, `-` or `*`"


@pytest.mark.parametrize(
    ("expression_source", "operator", "rule"),
    [
        ("score + price", "+", _DECIMAL_FLOAT),
        ("price + score", "+", _DECIMAL_FLOAT),
        ("price - 1.5", "-", _DECIMAL_FLOAT),
        ("price * 2.00", "*", _DECIMAL_FLOAT),
    ],
)
def test_invalid_decimal_arithmetic_forms_reuse_s2105(
    expression_source: str,
    operator: str,
    rule: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {expression_source}\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    # A Decimal is a number: the message names its rule, which is the suggestion.
    assert [(d.code, d.message, d.suggestion) for d in result.diagnostics] == [
        ("PIE-S2105", f"Invalid operands for operator {operator}: {rule}", rule)
    ]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_decimal_sign_rewrite_named_by_s2105_is_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        negated = 0 - price\n"
            "        plain = price\n"
        )
    )
    fields = result.model.relation_row_schemas[_relation(result)].fields

    assert result.diagnostics == ()
    assert fields["negated"].resolved_type.name == "Decimal"
    assert fields["plain"].resolved_type.name == "Decimal"


def test_decimal_rule_reaches_json_suggestion_in_file_and_project(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        "type Money = Decimal(12, 2)\n"
        "shape Order:\n    money: Money\n    score: Float\n"
        'source orders: Order = postgres.table("orders")\n'
        "table projected:\n    from orders\n    select:\n"
        "        doubled = money * 2\n        mixed = score - money\n"
        "        negated = -money\n        kept = +money\n",
        encoding="utf-8",
    )
    rules = [("-", 10, _DECIMAL_FLOAT)]

    for argv in (
        ["check", str(tmp_path / "main.pietto")],
        ["check", "--project", str(tmp_path)],
    ):
        assert cli.main([*argv, "--format", "json"]) == 1
        diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
        # The alias expands to Decimal, and the JSON suggestion carries the rule.
        assert [
            (d["code"], d["location"]["line"], d["message"], d["suggestion"])
            for d in diagnostics
        ] == [
            ("PIE-S2105", line, f"Invalid operands for operator {op}: {rule}", rule)
            for op, line, rule in rules
        ]


def test_unknown_decimal_operand_suppresses_s2105_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = missing + price\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in result.diagnostics]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_decimal_division_remains_deferred_without_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price / price\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.kind is ValueTypeKind.UNKNOWN
    assert value_type.resolved_type.kind is TypeKind.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = count_distinct(len(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are not supported yet",
            ),
        ),
        (
            "value = sum(avg(price))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = sum(price) if True else 1",
            (
                "PIE-S2310",
                "Aggregate composition requires scalar calls or arithmetic over direct aggregates, group keys and literals; invalid composition around sum(); select the sum() under a name in one query, then compute with that name in another that reads it with `from`",
            ),
        ),
    ],
)
def test_aggregate_expression_boundaries_remain_deferred(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_direct_aggregate_inside_satisfying_still_uses_s2308() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(price)\n"
            "    having:\n"
            "        sum(price + price) > 1000\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in having clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef:
    relation = next(
        definition
        for definition in result.model.relation_symbols.values()
        if isinstance(definition, TableDef)
    )
    return relation


def _select_expression(relation: TableDef, index: int) -> Expression:
    item = relation.select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
