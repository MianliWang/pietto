from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticResult, ValueTypeKind, analyze

SOURCE = (
    "shape Row:\n"
    "    text: Text\n"
    "    count: Int\n"
    "    optional_text: Text | None\n"
    'source rows: Row = postgres.table("rows")\n'
)


@pytest.mark.parametrize("operator", ["is None", "is not None"])
def test_is_null_where_expression_is_bool(operator: str) -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            f"    where optional_text {operator}\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table_where_expression(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_simple_comparison_where_expression_is_bool() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where count >= 1\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table_where_expression(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


@pytest.mark.parametrize(
    ("field_name", "type_name"), [("text", "Text"), ("count", "Int")]
)
def test_known_non_bool_table_where_reports_pie_s2202(
    field_name: str,
    type_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            f"    where {field_name}\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table_where_expression(result)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2202",
            Severity.ERROR,
            "Expected Bool expression in where clause",
        )
    ]
    assert (
        result.model.expression_value_types[expression].resolved_type.name == type_name
    )


def test_non_bool_where_diagnostic_uses_expression_span() -> None:
    script = _parse(
        SOURCE + "table filtered:\n"
        "    from rows\n"
        "    where text\n"
        "    select:\n"
        "        text\n",
        path="where.pietto",
    )
    result = analyze(script)
    expression = _table_where_expression(result)
    diagnostic = result.diagnostics[0]

    assert diagnostic.code == "PIE-S2202"
    assert diagnostic.location.path == expression.span.path == "where.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        expression.span.line,
        expression.span.column,
        expression.span.end_line,
        expression.span.end_column,
    )


def test_unknown_field_suppresses_bool_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where missing\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table_where_expression(result)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_input_schema_suppresses_field_and_bool_diagnostics() -> None:
    result = analyze(
        _parse(
            'source raw = postgres.table("raw")\n'
            "table filtered:\n"
            "    from raw\n"
            "    where missing\n"
            "    select:\n"
            "        missing\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    expression = _table_where_expression(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_known_non_bool_query_where_reports_pie_s2202() -> None:
    result = analyze(
        _parse(
            SOURCE + "query filtered:\n"
            "    from rows\n"
            "    where text\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _query_where_expression(result)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2202"]
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"


def test_unknown_function_suppresses_bool_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE + "table filtered:\n"
            "    from rows\n"
            "    where unknown_call(text)\n"
            "    select:\n"
            "        text\n"
        )
    )
    expression = _table_where_expression(result)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2103"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def _errors(source: str) -> list[tuple[str, int, int, str]]:
    return [
        (d.code, d.location.line, d.location.column, d.message)
        for d in analyze(_parse(source, path="m.pietto")).diagnostics
    ]


EXPECTED_BOOL = "Expected Bool expression in where clause"


def test_a_built_in_call_over_an_unknown_row_is_a_condition_of_its_result_type() -> (
    None
):
    """Over a source without a shape a built-in call whose signature fixes its
    result type has that type to a condition whatever its arguments are, also
    as a `let:` value: `where len(t)` and `where lower(t)` are PIE-S2202, as
    over a source with a shape, and a known operand of `and`, `or` or `not`
    that is not a Bool is PIE-S2105 beside an operand of unknown type, such
    as a line of a `where:` block (before: each accepted, and emission wrote
    a WHERE that is not Bool). A value of unknown type stays accepted."""
    source = (
        'source raw = postgres.table("raw")\n'
        "table a:\n    from raw\n    where len(t)\n    select:\n        id\n"
        "table b:\n    from raw\n    where lower(t)\n    select:\n        id\n"
        "table c:\n    from raw\n    let w = year(t)\n    let v = w\n"
        "    where v\n    select:\n        id\n"
        "table d:\n    from raw\n    where:\n        t\n        5\n    select:\n"
        "        id\n"
        "table e:\n    from raw\n    where t == 1 or upper(t)\n    select:\n"
        "        id\n"
        "table f:\n    from raw\n    where not lower(t)\n    select:\n        id\n"
        "table g:\n    from raw\n    where:\n        t\n        coalesce(t, u)\n"
        "        contains(t, 'x')\n        matches(t, 'y')\n    select:\n        id\n"
    )

    assert _errors(source) == [
        ("PIE-S2303", 1, 1, "Source raw has no bound shape; row schema is unknown"),
        ("PIE-S2202", 4, 11, EXPECTED_BOOL),
        ("PIE-S2202", 9, 11, EXPECTED_BOOL),
        ("PIE-S2202", 16, 11, EXPECTED_BOOL),
        (
            "PIE-S2105",
            22,
            9,
            "Invalid operands for operator and: expected Bool operands",
        ),
        (
            "PIE-S2105",
            28,
            11,
            "Invalid operands for operator or: expected Bool operands",
        ),
        (
            "PIE-S2105",
            33,
            11,
            "Invalid operands for operator not: expected Bool operand",
        ),
    ]


def test_a_built_in_call_of_null_values_is_a_condition_of_its_result_type() -> None:
    """A built-in call is a condition of its result type also where an
    always-null argument leaves its type unknown, written by hand or through
    a `let:` name (before: accepted). An error of its own explains an unknown
    type, also one of a binding it reads, so it adds nothing there."""
    source = SOURCE + (
        "table a:\n    from rows\n    where lower(coalesce(None, None))\n"
        "    select:\n        text\n"
        "table b:\n    from rows\n    let k = None\n"
        "    let j = len(coalesce(k, k))\n    where j\n    select:\n        text\n"
        "table c:\n    from rows\n    where len(missing)\n    select:\n        text\n"
        "table d:\n    from rows\n    where missing and 1\n    select:\n        text\n"
        "table e:\n    from rows\n    let e = lower(1)\n    where len(e)\n"
        "    select:\n        text\n"
    )

    assert _errors(source) == [
        ("PIE-S2202", 8, 11, EXPECTED_BOOL),
        ("PIE-S2202", 15, 11, EXPECTED_BOOL),
        ("PIE-S2102", 20, 15, "Unknown field: missing"),
        ("PIE-S2102", 25, 11, "Unknown field: missing"),
        (
            "PIE-S2104",
            30,
            13,
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        ),
    ]


def test_a_built_in_call_over_an_unknown_row_has_its_result_type_everywhere() -> None:
    """Over a source without a shape a built-in call whose signature fixes its
    result type has that type wherever it is read, and each of its arguments
    of known type is checked. Before, the call was of unknown type outside a
    condition and an argument of unknown type hid the others: `lower(t) + 1`
    and `matches(t, 1)` passed and PostgreSQL rejected the SQL, `where len(t)
    + 1` passed, `substr(t, "a", 1)` reported only its bounds, and a `count`
    output with an argument was of unknown type to `satisfying`;
    `coalesce(t, 1, "x")` passed too, whose arguments of known type do not
    compare. Arguments of unknown type alone stay accepted (`contains(t, u)`,
    `year(t) + 1`, `coalesce(t, null, 1)`), and so do arguments of known type
    that compare (`coalesce(t, 1, 2.5)`), and a read of a binding whose error
    is reported where it is bound adds nothing."""
    source = (
        'source raw = postgres.table("raw")\n'
        "table a:\n    from raw\n    where len(t) + 1\n    select:\n        id\n"
        "table b:\n    from raw\n    select:\n"
        "        x = lower(t) + 1\n"
        "        y = matches(t, 1)\n"
        '        z = substr(t, "a", 1)\n'
        "        w = contains(t, u)\n"
        "        v = year(t) + 1\n"
        '        s = sign(t) + "x"\n'
        "        r = len(t) / 2\n"
        '        q = coalesce(t, 1, "x")\n'
        "        o = coalesce(t, None, 1)\n"
        "        n = coalesce(t, 1, 2.5)\n"
        "table c:\n    from raw\n    group by g\n    select:\n        g\n"
        "        n = count(t)\n        m = count_distinct(t)\n"
        "    having n and m > 1\n"
        "table d:\n    from raw\n    let j = lower(k)\n    let k = t\n"
        "    select:\n        p = j + 1\n"
    )

    plus = (
        "Invalid operands for operator +: expected numeric operands; "
        "string concatenation is not supported yet"
    )
    assert _errors(source) == [
        ("PIE-S2303", 1, 1, "Source raw has no bound shape; row schema is unknown"),
        ("PIE-S2202", 4, 11, EXPECTED_BOOL),
        ("PIE-S2105", 10, 13, plus),
        (
            "PIE-S2104",
            11,
            13,
            "Invalid argument type for function matches at position 2: "
            "expected Text, got Int",
        ),
        (
            "PIE-S2104",
            12,
            13,
            "Invalid argument type for function substr at position 2: "
            "expected Int, got Text",
        ),
        ("PIE-S2105", 15, 13, plus),
        (
            "PIE-S2104",
            17,
            13,
            "Invalid argument types for function coalesce: expected same "
            "canonical type",
        ),
        (
            "PIE-S2105",
            27,
            12,
            "Invalid operands for operator and: expected Bool operands",
        ),
        ("PIE-S2330", 30, 19, "Let binding cannot reference a later binding: k"),
    ]


def test_where_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table filtered:\n"
        "    from rows\n"
        "    where text\n"
        "    select:\n"
        "        text\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_where_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "query filtered:\n"
            "    from rows\n"
            "    where text\n"
            "    select:\n"
            "        text\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _table(result: SemanticResult) -> TableDef:
    definition = result.model.relation_symbols["filtered"]
    assert isinstance(definition, TableDef)
    assert definition.where_clause is not None
    return definition


def _query(result: SemanticResult) -> QueryDef:
    definition = result.model.relation_symbols["filtered"]
    assert isinstance(definition, QueryDef)
    assert definition.where_clause is not None
    return definition


def _table_where_expression(result: SemanticResult) -> Expression:
    table = _table(result)
    assert table.where_clause is not None
    return table.where_clause.expression


def _query_where_expression(result: SemanticResult) -> Expression:
    query = _query(result)
    assert query.where_clause is not None
    return query.where_clause.expression


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
