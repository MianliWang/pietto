from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import CallExpr, QueryDef, Script, TableDef
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
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    "projection",
    [
        "value = count_distinct(lower(status))",
        "value = count_distinct(trim(status))",
        "value = count_distinct(lower(trim(status)))",
        "value = count_distinct(trim(lower(status)))",
        "value = count_distinct(lower(lower(status)))",
        "value = count_distinct(trim(trim(status)))",
        "value = count_distinct(lower(trim(lower(status))))",
        "value = count_distinct(lower(orders.status))",
    ],
)
def test_count_distinct_lower_trim_transform_arguments_are_accepted(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    assert isinstance(expression, CallExpr)
    argument = expression.arguments[0]
    schema = result.model.relation_row_schemas[relation]
    field = schema.fields["value"]
    expression_type = result.model.expression_value_types[expression]
    argument_type = result.model.expression_value_types[argument]

    assert _errors(result) == []
    _assert_field(field, "Int", EffectiveNullability.NON_NULL)
    _assert_value_type(expression_type, "Int", EffectiveNullability.NON_NULL)
    _assert_value_type(argument_type, "Text", EffectiveNullability.UNKNOWN)


def test_direct_count_distinct_field_behavior_remains_unchanged() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        value = count_distinct(active)\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == []
    _assert_field(field, "Int", EffectiveNullability.NON_NULL)


def test_grouped_count_distinct_transform_argument_is_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_by_region:\n"
            "    from orders\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        normalized = count_distinct(lower(trim(status)))\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["region", "normalized"]
    _assert_field(schema.fields["region"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["normalized"], "Int", EffectiveNullability.NON_NULL)


def test_satisfying_resolves_count_distinct_transform_projection_alias() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_by_region:\n"
            "    from orders\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        normalized = count_distinct(lower(status))\n"
            "    satisfying:\n"
            "        normalized > 10\n"
        )
    )

    assert _errors(result) == []


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = count_distinct(len(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            'value = count_distinct(matches(status, "x"))',
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(lower(status) + trim(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(lower(status) + lower(region))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(lower(1))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(lower(amount))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = count(amount + tax)",
            (
                "PIE-S2315",
                "Aggregate function count requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "value = min(amount + tax)",
            (
                "PIE-S2315",
                "Aggregate function min requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "value = max(score * score)",
            (
                "PIE-S2315",
                "Aggregate function max requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
    ],
)
def test_unsupported_count_distinct_transform_shapes_use_s2315(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = count_distinct()",
            (
                "PIE-S2309",
                "Aggregate function count_distinct expects 1 arguments, got 0",
            ),
        ),
        (
            "value = count_distinct(lower(status), trim(status))",
            (
                "PIE-S2309",
                "Aggregate function count_distinct expects 1 arguments, got 2",
            ),
        ),
        (
            "value = count_distinct(lower(avg(status)))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = count_distinct(lower(status)) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around count_distinct() is deferred",
            ),
        ),
    ],
)
def test_count_distinct_transform_diagnostic_precedence(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


@pytest.mark.parametrize(
    ("projection", "expected_message"),
    [
        ("value = count_distinct(lower(missing))", "Unknown field: missing"),
        ("value = count_distinct(lower(subtotal))", "Unknown field: subtotal"),
    ],
)
def test_unknown_transform_leaf_suppresses_count_distinct_cascade(
    projection: str,
    expected_message: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        subtotal = status\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", expected_message)]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_direct_count_distinct_inside_satisfying_still_uses_s2308() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table status_by_region:\n"
            "    from orders\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        normalized = count_distinct(lower(status))\n"
            "    satisfying:\n"
            "        count_distinct(lower(status)) > 10\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate count_distinct() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        )
    ]


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_emit_sql_for_count_distinct_transform_fails_closed_without_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
) -> None:
    source = (
        SOURCE_PREFIX + "table status_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        normalized = count_distinct(lower(status))\n"
    )
    semantic_result = analyze(_parse(source))
    path = _write(tmp_path, f"count-distinct-transform-{dialect}.pietto", source)
    output = tmp_path / f"{dialect}.sql"

    assert _errors(semantic_result) == []
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    diagnostic_codes = {str(diagnostic["code"]) for diagnostic in diagnostics}

    assert captured.err == ""
    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output), "written": False}
    assert diagnostic_codes
    assert diagnostic_codes <= {"PIE-I1000", "PIE-B1000"}
    assert "PIE-S2315" not in diagnostic_codes
    assert "SELECT" not in captured.out
    assert not output.exists()


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _select_expression(relation: TableDef | QueryDef, index: int) -> object:
    return relation.select_items[index].expression


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _assert_value_type(
    value_type: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "kind") is not ValueTypeKind.UNKNOWN
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_type
    assert getattr(value_type, "nullability") is expected_nullability


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
