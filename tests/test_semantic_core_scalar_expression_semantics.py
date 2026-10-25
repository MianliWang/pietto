from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    Expression,
    SelectItem,
    Script,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir import BinaryIR, RelationIR, ScriptIR, TypeKindIR, UnaryIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PREFIX = (
    "shape Row:\n"
    "    text: Text\n"
    "    count: Int\n"
    "    active: Bool\n"
    'source rows: Row = postgres.table("rows")\n'
    'source mysql_rows: Row = mysql.table("rows")\n'
)


def test_boolean_binary_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where count > 1 and active == True\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BinaryExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_between_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where 1 <= count <= 5\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BetweenExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_invalid_bool_binary_reports_s2105_at_full_span() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where text and True\n"
        "    select:\n"
        "        text\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    expression = _where_expression(parse_result.ast)

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator and: expected Bool operands",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


def test_int_arithmetic_projection_has_semantic_and_ir_type() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.UNKNOWN
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.canonical_kind is TypeKindIR.BUILTIN


def test_mixed_numeric_projection_promotes_to_float() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1.5\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Float"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Float"


def test_unary_numeric_projection_preserves_type_and_nullability() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = -count\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, UnaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.NON_NULL
    assert isinstance(ir_expression, UnaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.nullability.value == "non_null"


def test_modulo_projection_requires_int_and_returns_int() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count % 2\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"


def test_invalid_arithmetic_reports_s2105() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = text + 1\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)
    expression = _select_expression(parse_result.ast, 0)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        value = missing + 1\n",
        "    where missing and True\n    select:\n        text\n",
        "    where 1 <= missing <= 5\n    select:\n        text\n",
    ],
)
def test_unknown_children_suppress_s2105_cascades(body: str) -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table validated:\n    from rows\n" + body,
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [("PIE-S2102", "Unknown field: missing")]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in semantic.diagnostics]


@pytest.mark.parametrize(
    ("value", "type_name", "postgres_sql", "mysql_sql"),
    [
        ("n / m", "Int", '"n" / "m"', "`n` DIV `m`"),
        ("n / f", "Float", '"n" / "f"', "`n` / `f`"),
        ("f / n", "Float", '"f" / "n"', "`f` / `n`"),
        ("f / g", "Float", '"f" / "g"', "`f` / `g`"),
        ("age / 2", "Int", '"age" / 2', "`age` DIV 2"),
        ("ratio / 2", "Float", '"ratio" / 2', "`ratio` / 2"),
        ("n * 1.0 / m", "Float", '("n" * 1.0) / "m"', "(`n` * 1.0) / `m`"),
        (
            "Float(n) / m",
            "Float",
            '(CAST("n" AS double precision)) / "m"',
            "(CAST(`n` AS DOUBLE)) / `m`",
        ),
    ],
    ids=(
        "int-int",
        "int-float",
        "float-int",
        "float-float",
        "int-alias",
        "float-alias",
        "times-one",
        "cast-float",
    ),
)
def test_division_follows_sql_and_never_inserts_a_cast(
    value: str,
    type_name: str,
    postgres_sql: str,
    mysql_sql: str,
) -> None:
    def source(connector: str) -> str:
        return (
            "type Age = Int\n"
            "type Ratio = Float\n"
            "shape Row:\n"
            "    n: Int\n"
            "    m: Int\n"
            "    f: Float\n"
            "    g: Float\n"
            "    age: Age\n"
            "    ratio: Ratio\n"
            f'source rows: Row = {connector}.table("rows")\n'
            "table divided:\n"
            "    from rows\n"
            "    select:\n"
            f"        value = {value}\n"
        )

    script, semantic, postgres_ir = _compile(source("postgres"))
    _, _, mysql_ir = _compile(source("mysql"))
    value_type = semantic.model.expression_value_types[_select_expression(script, 0)]

    # Int / Int truncates toward zero as SQL does: PostgreSQL keeps its bare
    # `/` (unchanged bytes) and MySQL, whose `/` gives DECIMAL, emits DIV.
    assert semantic.diagnostics == ()
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.resolved_type.name == type_name
    assert emit_postgres_sql(postgres_ir).artifacts[0].sql == (
        f'SELECT\n    {postgres_sql} AS "value"\nFROM "rows"'
    )
    assert emit_mysql_sql(mysql_ir).artifacts[0].sql == (
        f"SELECT\n    {mysql_sql} AS `value`\nFROM `rows`"
    )


def test_division_of_a_call_over_an_unknown_row_is_typed_by_its_signature() -> None:
    # Before: over a source without a shape `len(t)` was of unknown type, so
    # MySQL emitted a bare `/`, which keeps the fraction PostgreSQL drops.
    def source(connector: str) -> str:
        return (
            f'source raw = {connector}.table("raw")\n'
            "table divided:\n"
            "    from raw\n"
            "    select:\n"
            "        value = len(t) / 2\n"
        )

    script, semantic, postgres_ir = _compile(source("postgres"))
    _, _, mysql_ir = _compile(source("mysql"))
    value_type = semantic.model.expression_value_types[_select_expression(script, 0)]

    assert [(d.code, d.severity) for d in semantic.diagnostics] == [
        ("PIE-S2303", Severity.WARNING)
    ]
    assert (value_type.kind, value_type.resolved_type.name) == (
        ValueTypeKind.KNOWN,
        "Int",
    )
    assert emit_postgres_sql(postgres_ir).artifacts[0].sql == (
        'SELECT\n    length("t") / 2 AS "value"\nFROM "raw"'
    )
    assert emit_mysql_sql(mysql_ir).artifacts[0].sql == (
        "SELECT\n    CHAR_LENGTH(`t`) DIV 2 AS `value`\nFROM `raw`"
    )


def test_null_arithmetic_has_the_type_of_its_known_operand() -> None:
    # Before: an arithmetic `null` operand took the other operand's type only
    # to be checked, and the result stayed of unknown type, so check passed
    # `trim(null % f1)`, `lower(null + n)`, `(null + n) == "x"` and
    # `where null + n`, whose SQL PostgreSQL rejects (`trim(bigint)` does not
    # exist), and MySQL divided `(null + n) / 2` with `/`. The result, always
    # null, is now of the type the operator gives two operands of that type,
    # as for its typed twin `f1 % f1`, and with a `Decimal` operand a quotient
    # is a number of unknown type (`got numeric`). A scalar error caused by
    # that typed NULL stays specific inside count; bare NULL arithmetic still
    # has the unsupported aggregate shape, PIE-S2315.
    head = (
        "shape Row:\n"
        "    id: Int\n"
        "    n: Int | None\n"
        "    f1: Int\n"
        "    d: Decimal(10, 2) | None\n"
        'source rows: Row = mysql.table("rows")\n'
    )
    refused = analyze(
        _parse(
            head + "table refused:\n"
            "    from rows\n"
            "    where None + n\n"
            "    select:\n"
            "        id\n"
            "        a = trim(None % f1)\n"
            "        b = lower(None / d)\n"
            '        c = (None + n) == "x"\n'
            "table counted:\n"
            "    from rows\n"
            "    select:\n"
            "        e = count(trim(None % f1))\n"
            "        f = count(None + n)\n"
        )
    )
    script, semantic, script_ir = _compile(
        head + "table typed:\n"
        "    from rows\n"
        "    select:\n"
        "        v = (None + n) / 2\n"
        "        w = None % f1\n"
    )
    w_type = semantic.model.expression_value_types[_select_expression(script, 1)]

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in refused.diagnostics
    ] == [
        ("PIE-S2202", 9, 11, "Expected Bool expression in where clause"),
        (
            "PIE-S2104",
            12,
            13,
            "Invalid argument type for function trim at position 1: "
            "expected Text, got Int",
        ),
        (
            "PIE-S2104",
            13,
            13,
            "Invalid argument type for function lower at position 1: "
            "expected Text, got numeric",
        ),
        (
            "PIE-S2105",
            14,
            13,
            "Invalid operands for operator ==: expected comparable operands",
        ),
        (
            "PIE-S2104",
            18,
            19,
            "Invalid argument type for function trim at position 1: expected Text, got Int",
        ),
        (
            "PIE-S2315",
            19,
            13,
            "Aggregate function count requires a direct field argument; "
            "expression arguments are not supported yet",
        ),
    ]
    assert semantic.diagnostics == ()
    assert (w_type.resolved_type.name, w_type.nullability) == (
        "Int",
        EffectiveNullability.NULLABLE,
    )
    assert emit_mysql_sql(script_ir).artifacts[0].sql == (
        "SELECT\n    (NULL + `n`) DIV 2 AS `v`,\n    NULL % `f1` AS `w`\nFROM `rows`"
    )


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
@pytest.mark.parametrize(
    ("argument", "function", "position", "actual"),
    [
        ("trim(None + n)", "trim", 1, "Int"),
        ("trim(-(None + n))", "trim", 1, "Int"),
        ("trim(abs(None + n))", "trim", 1, "Int"),
        ("lower(None % age)", "lower", 1, "Int"),
        ('replace("x", None + n, "y")', "replace", 2, "Int"),
        ("trim(None + d)", "trim", 1, "Decimal"),
        ("trim(None / d)", "trim", 1, "numeric"),
        ("trim(abs(None / d))", "trim", 1, "numeric"),
        ('replace(None / d, "x", "y")', "replace", 1, "numeric"),
        ('replace(d / 2, None + n, "y")', "replace", 2, "Int"),
    ],
)
def test_aggregate_keeps_the_scalar_error_from_typed_null_arithmetic(
    grouped: bool, argument: str, function: str, position: int, actual: str
) -> None:
    source = (
        "type Age = Int\n"
        "shape Row:\n"
        "    id: Int\n"
        "    n: Int | None\n"
        "    age: Age\n"
        "    d: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        + ("    group by id\n" if grouped else "")
        + f"    select:\n        v = count({argument})\n"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == [
        (
            "PIE-S2104",
            f"Invalid argument type for function {function} at position {position}: expected Text, got {actual}",
            12 if grouped else 11,
            19,
        )
    ]


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
@pytest.mark.parametrize(
    ("argument", "scalar_error", "shape_error"),
    [
        ("trim(None / 2.5) + x", True, False),
        ("trim(x / 2.5)", False, True),
        ("trim(1 / 2.5) + x", True, True),
    ],
    ids=["typed-null", "unknown-field", "non-null"],
)
def test_unknown_row_aggregate_keeps_the_actual_typed_null_error(
    grouped: bool, argument: str, scalar_error: bool, shape_error: bool
) -> None:
    source = (
        'source rows = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        + ("    group by x\n" if grouped else "")
        + f"    select:\n        v = count({argument})\n        field = x\n"
    )
    script = _parse(source)
    result = analyze(script)
    line = 6 if grouped else 5
    expected = []
    if shape_error:
        expected.append(
            (
                "PIE-S2315",
                "Aggregate function count requires a direct field argument; expression arguments are not supported yet",
                line,
                13,
            )
        )
    if scalar_error:
        expected.append(
            (
                "PIE-S2104",
                "Invalid argument type for function trim at position 1: expected Text, got Float",
                line,
                19,
            )
        )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
        if d.severity is Severity.ERROR
    ] == expected
    # The invalid aggregate stays unknown and adds no mixed-projection error.
    assert (
        result.model.expression_value_types[_select_expression(script, 0)].kind
        is ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
def test_unknown_row_aggregate_null_error_follows_its_whole_let_argument(
    grouped: bool,
) -> None:
    source = (
        'source rows = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "\n"
        "    let bad = trim(None / 2.5) + x\n"
        "    let value = bad\n"
        + ("    group by x\n" if grouped else "")
        + "    select:\n        v = count(value)\n        field = x\n"
    )
    script = _parse(source)
    result = analyze(script)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
        if d.severity is Severity.ERROR
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function trim at position 1: expected Text, got Float",
            5,
            15,
        )
    ]
    assert (
        result.model.expression_value_types[_select_expression(script, 0)].kind
        is ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
def test_unknown_row_null_arithmetic_checks_only_the_aggregate_form(
    grouped: bool,
) -> None:
    source = (
        'source rows = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        + ("    group by x\n" if grouped else "")
        + "    select:\n        v = count(x + None)\n"
    )
    script = _parse(source)
    result = analyze(script)
    assert [d for d in result.diagnostics if d.severity is Severity.ERROR] == []
    # The check-only field assignments do not give the output row a type.
    schema = result.model.relation_row_schemas[_relation(script)]
    if grouped:
        assert schema.is_unknown and not schema.fields
    else:
        assert schema.fields["v"].resolved_type.kind is TypeKind.UNKNOWN
        assert schema.fields["v"].nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
@pytest.mark.parametrize(
    "argument",
    [
        "lower(n)",
        "None + n",
        'substr("x", None + n, "x")',
        'substr("x", None + n, 1)',
        'replace(n, None + n, "x")',
        "trim(None + n, n)",
        'abs("x" if (None + n is None) else "y")',
        "trim(d / 2)",
        "trim(abs(d / 2))",
        'replace(None / d, n, "x")',
        "substr(None / d, None + n, 1)",
        "trim((None / d) if lower(1) is None else (d / 2))",
        'replace(None / d, (None + n) if lower(1) is None else n, "x")',
    ],
)
def test_unrelated_null_arithmetic_keeps_aggregate_shape_diagnostics(
    grouped: bool, argument: str
) -> None:
    source = (
        "shape Row:\n"
        "    id: Int\n"
        "    n: Int | None\n"
        "    d: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        + ("    group by id\n" if grouped else "")
        + f"    select:\n        v = count({argument})\n"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == [
        (
            "PIE-S2315",
            "Aggregate function count requires a direct field argument; expression arguments are not supported yet",
            10 if grouped else 9,
            13,
        )
    ]


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
def test_aggregate_null_division_error_follows_its_admitted_let_chain(
    grouped: bool,
) -> None:
    source = (
        "shape Row:\n"
        "    id: Int\n"
        "    d: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "\n"
        "    let q = None / d\n"
        "    let a = abs(q)\n"
        "    let b = a\n"
        "    let bad = trim(b)\n"
        + ("    group by id\n" if grouped else "")
        + "    select:\n        v = count(bad)\n"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function trim at position 1: expected Text, got numeric",
            11,
            15,
        )
    ]


@pytest.mark.parametrize("grouped", [False, True], ids=["global", "grouped"])
@pytest.mark.parametrize("mode", ["alias", "arity", "def"])
def test_null_arithmetic_preserves_aggregate_alias_arity_and_def_diagnostics(
    grouped: bool, mode: str
) -> None:
    projection = {
        "alias": "count(trim(None + n))",
        "arity": "v = count(trim(None + n), n)",
        "def": "v = count(nn(n + None))",
    }[mode]
    source = (
        "shape Row:\n"
        "    id: Int\n"
        "    n: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "def nn(x: Int) -> Int: return x\n"
        "table selected:\n"
        "    from rows\n"
        + ("    group by id\n" if grouped else "")
        + f"    select:\n        {projection}\n"
    )
    line = 10 if grouped else 9
    scalar = (
        "Invalid argument type for function trim at position 1: expected Text, got Int"
    )
    expected = {
        "alias": [
            (
                "PIE-S2313",
                "Aggregate count() projection requires an explicit alias",
                line,
                9,
            ),
            ("PIE-S2104", scalar, line, 15),
        ],
        "arity": [("PIE-S2104", scalar, line, 19)],
        "def": [
            (
                "PIE-S2395",
                "Invalid argument for def nn at position 1 (x): expected Int, got null",
                line,
                19,
            )
        ],
    }[mode]
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == expected


@pytest.mark.parametrize("depth", [0, 4, 8, 16])
def test_nested_null_arithmetic_errors_need_no_semantic_replay(
    monkeypatch: pytest.MonkeyPatch, depth: int
) -> None:
    from typing import Any

    from pietto.semantic import expressions
    from pietto.semantic.model import ValueType

    value = "trim(None / d)"
    for _ in range(depth):
        value = f"trim((None / d) if ({value} is None) else d / 2)"
    source = (
        "shape Row:\n"
        "    d: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "    select:\n"
        f"        v = count({value})\n"
    )
    inferred = 0
    original = expressions._infer

    def counted(*args: Any, **kwargs: Any) -> ValueType:
        nonlocal inferred
        inferred += 1
        return original(*args, **kwargs)

    def replayed(*args: object, **kwargs: object) -> bool:
        raise AssertionError("Aggregate diagnostics must use the actual typing errors")

    monkeypatch.setattr(expressions, "_infer", counted)
    monkeypatch.setattr(expressions, "_has_own_error", replayed)
    semantic = analyze(_parse(source))
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in semantic.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function trim at position 1: expected Text, got numeric",
            7,
            source.splitlines()[-1].index("trim(None / d)") + 1,
        )
    ]
    # Two walks of the 5 + 9*depth value nodes, plus one connector literal.
    assert inferred <= 11 + 18 * depth


def test_null_arithmetic_fact_requires_the_reported_diagnostic() -> None:
    from dataclasses import replace

    from pietto.ast_nodes import CallExpr
    from pietto.semantic import expressions
    from pietto.semantic.model import RowSchema

    script = _parse(
        "shape Row:\n"
        "    d: Decimal(10, 2)\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "    select:\n"
        "        v = count(trim(None / d))\n"
    )
    semantic = analyze(script)
    count = _select_expression(script, 0)
    assert isinstance(count, CallExpr)
    actual = tuple(semantic.diagnostics)
    assert len(actual) == 1 and actual[0].code == "PIE-S2104"
    unrelated = replace(actual[0], message="Unrelated scalar error")
    for reported, expected in (
        (frozenset(), ()),
        (frozenset((unrelated,)), ()),
        (frozenset(actual), actual),
        (frozenset(), ()),
    ):
        assert (
            expressions.null_arithmetic_argument_diagnostics(
                count.arguments[0],
                RowSchema(),
                semantic.model.expression_value_types,
                None,
                None,
                reported_errors=reported,
            )
            == expected
        )


def test_decimal_division_keeps_its_deferred_type_and_bare_sql() -> None:
    # Byte-identical to main; Decimal division awaits a decision.
    body = (
        "    select:\n"
        "        dd = d / e\n"
        "        di = d / n\n"
        "        id = n / d\n"
        "        df = d / f\n"
        "        fd = f / d\n"
    )
    shape = (
        "shape Money:\n"
        "    n: Int\n"
        "    f: Float\n"
        "    d: Decimal(10, 2)\n"
        "    e: Decimal(12, 4) | None\n"
    )
    columns = ("dd", "di", "id", "df", "fd")
    expected = ("d / e", "d / n", "n / d", "d / f", "f / d")
    for connector, emitter, quote in (
        ("postgres", emit_postgres_sql, '"'),
        ("mysql", emit_mysql_sql, "`"),
    ):
        script, semantic, script_ir = _compile(
            shape
            + (f'source money: Money = {connector}.table("money")\n')
            + "table divided:\n    from money\n"
            + body
        )
        assert semantic.diagnostics == ()
        assert all(
            semantic.model.expression_value_types[_select_expression(script, i)].kind
            is ValueTypeKind.UNKNOWN
            for i in range(len(columns))
        )
        sql = emitter(script_ir).artifacts[0].sql
        for column, division in zip(columns, expected, strict=True):
            left, right = division.split(" / ")
            assert (
                f"    {quote}{left}{quote} / {quote}{right}{quote} "
                f"AS {quote}{column}{quote}"
            ) in sql


@pytest.mark.parametrize(
    "value", ["text / 2", "count / active", "(count / 2) and active"]
)
def test_division_of_non_numeric_operands_reports_s2105(value: str) -> None:
    semantic = analyze(
        _parse(
            SOURCE_PREFIX
            + "table projected:\n    from rows\n    select:\n"
            + f"        value = {value}\n"
        )
    )

    assert [code for code, _ in _diagnostics(semantic)] == ["PIE-S2105"]


_DIVISION_OPERANDS = (
    "enum Color:\n"
    "    red\n"
    "    blue\n"
    "type Money = Decimal(12, 2)\n"
    "shape Row:\n"
    "    n: Int\n"
    "    d: Money\n"
    "    blob: Bytes\n"
    "    doc: Json\n"
    "    any: Any | None\n"
    "    color: Color\n"
    'source rows: Row = postgres.table("rows")\n'
    "table projected:\n"
    "    from rows\n"
    "    select:\n"
)


@pytest.mark.parametrize("operand", ["blob", "doc", "any", "color"])
def test_division_of_any_known_non_numeric_type_reports_s2105(operand: str) -> None:
    semantic = analyze(_parse(_DIVISION_OPERANDS + f"        value = {operand} / n\n"))

    assert [(code, message) for code, message in _diagnostics(semantic)] == [
        (
            "PIE-S2105",
            "Invalid operands for operator /: expected numeric operands",
        )
    ]


def test_division_with_a_decimal_alias_operand_stays_deferred() -> None:
    semantic = analyze(_parse(_DIVISION_OPERANDS + "        value = d / n\n"))

    assert _diagnostics(semantic) == []


def test_a_decimal_quotient_is_refused_where_no_number_fits() -> None:
    # Before: a quotient with a Decimal operand, of unknown type, passed every
    # check below, and PostgreSQL rejects the SQL. It is a number whatever its
    # type, so a use that takes no number is refused, also through a `let:`
    # name, after arithmetic or in a `coalesce` or conditional, where a null
    # takes its type; a use beside numbers passes.
    semantic = analyze(
        _parse(
            "shape Row:\n"
            "    id: Int\n"
            "    a: Decimal(10, 2)\n"
            "    f: Float\n"
            "    t: Text\n"
            'source rows: Row = postgres.table("rows")\n'
            "table refused:\n"
            "    from rows\n"
            "\n"
            "    let q = a / 2\n"
            "    where a / 2\n"
            "    select:\n"
            "        id\n"
            '        p = a / 2 - "x"\n'
            "        l = lower(a / 2)\n"
            '        c = id / a == "x"\n'
            '        g = f / a like "x%"\n'
            "        w = not (a / 2)\n"
            "        y = year(q / 3)\n"
            '        m = q % "x"\n'
            '        n = -q * 2 like "x%"\n'
            '        i = q in ("x", "y")\n'
            '        e = "a" <= q <= "z"\n'
            "        h = t if id > 1 else q\n"
            "        o = coalesce(t, q)\n"
            '        u = nullif(q, "x")\n'
            "        v = lower(coalesce(q, 0))\n"
            "        z = coalesce(t, q, None)\n"
            '        r = (q if id > 1 else None) == "x"\n'
            "table accepted:\n"
            "    from rows\n"
            "\n"
            "    let q = a / 2\n"
            "    where a / 2 > f and coalesce(q, 0) > 1\n"
            "    select:\n"
            "        id\n"
            "        k = a / 2 + 1\n"
            "        b = abs(a / 2)\n"
            "        r = (a / 2) % 2\n"
            "        s = q % 2.5\n"
            "        j = q in (1, 2.5)\n"
            "        z = 1 if id > 1 else q\n"
            "        x = Float(a / 2)\n"
            "        n = (q if id > 1 else None) + coalesce(q, None)\n"
        )
    )

    operands = "Invalid operands for operator {}: expected {} operands"
    argument = (
        "Invalid argument type for function {} at position 1: expected {}, got numeric"
    )
    arguments = "Invalid argument types for function {}: expected same canonical {}"
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        ("PIE-S2202", "Expected Bool expression in where clause", 11, 11),
        ("PIE-S2105", operands.format("-", "numeric"), 14, 13),
        ("PIE-S2104", argument.format("lower", "Text"), 15, 13),
        ("PIE-S2105", operands.format("==", "comparable"), 16, 13),
        ("PIE-S2105", operands.format("like", "Text"), 17, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator not: expected Bool operand",
            18,
            13,
        ),
        ("PIE-S2104", argument.format("year", "Date or Timestamp"), 19, 13),
        ("PIE-S2105", operands.format("%", "Int"), 20, 13),
        ("PIE-S2105", operands.format("like", "Text"), 21, 13),
        ("PIE-S2105", operands.format("in", "same canonical membership"), 22, 13),
        ("PIE-S2105", operands.format("between", "comparable"), 23, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator conditional: expected same canonical "
            "branch types",
            24,
            13,
        ),
        ("PIE-S2104", arguments.format("coalesce", "type"), 25, 13),
        ("PIE-S2104", arguments.format("nullif", "comparable type"), 26, 13),
        ("PIE-S2104", argument.format("lower", "Text"), 27, 13),
        ("PIE-S2104", arguments.format("coalesce", "type"), 28, 13),
        ("PIE-S2105", operands.format("==", "comparable"), 29, 13),
    ]


def test_abs_of_a_number_of_unknown_type_is_one() -> None:
    # Before: `abs` of a Decimal quotient, or of a field of a source without a
    # shape, was of unknown type, so `lower(abs(a / 2))` and
    # `abs(a / 2) + "x"` passed check, and PostgreSQL rejects their SQL as it
    # rejects `lower(a / 2)`. `abs` keeps its argument's type, which is a
    # number, so it is a number of unknown type there; a use beside numbers
    # passes, and `abs` of a call typed by its signature has that type.
    semantic = analyze(
        _parse(
            "shape Row:\n"
            "    id: Int\n"
            "    a: Decimal(10, 2)\n"
            'source rows: Row = postgres.table("rows")\n'
            'source raw = postgres.table("raw")\n'
            "table refused:\n"
            "    from rows\n"
            "\n"
            "    let q = abs(a / 2)\n"
            "    select:\n"
            "        id\n"
            "        l = lower(abs(a / 2))\n"
            '        p = abs(a / 2) + "x"\n'
            '        c = q == "x"\n'
            "        y = year(abs(abs(a / 2)))\n"
            "table accepted:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        k = abs(a / 2) + 1\n"
            "        r = abs(a / 2) % 2\n"
            "        n = abs(-(a / 2)) > 1\n"
            "table shapeless:\n"
            "    from raw\n"
            "    select:\n"
            "        l = lower(abs(t))\n"
            "        m = abs(t) * 2\n"
            "        r = abs(t) % 2\n"
            "        e = abs(len(t)) + 1\n"
            '        c = abs(t) if b else "x"\n'
            '        z = "x" if b else abs(t)\n'
            "        compatible = abs(t) if b else 1\n"
            '        unchecked = t if b else "x"\n'
        )
    )

    argument = (
        "Invalid argument type for function {} at position 1: expected {}, got numeric"
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in semantic.diagnostics
    ] == [
        (
            "PIE-S2303",
            "Source raw has no bound shape; row schema is unknown",
            5,
            1,
        ),
        ("PIE-S2104", argument.format("lower", "Text"), 12, 13),
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands; "
            "string concatenation is not supported yet",
            13,
            13,
        ),
        (
            "PIE-S2105",
            "Invalid operands for operator ==: expected comparable operands",
            14,
            13,
        ),
        ("PIE-S2104", argument.format("year", "Date or Timestamp"), 15, 13),
        ("PIE-S2104", argument.format("lower", "Text"), 26, 13),
        *[
            (
                "PIE-S2105",
                "Invalid operands for operator conditional: expected same canonical branch types",
                line,
                13,
            )
            for line in (30, 31)
        ],
    ]
    shapeless = semantic.model.relation_symbols["shapeless"]
    assert isinstance(shapeless, TableDef)
    assert (
        semantic.model.expression_value_types[shapeless.select_items[6].expression].kind
        is ValueTypeKind.UNKNOWN
    )


def test_numeric_conditional_branches_preserve_condition_error_suppression() -> None:
    semantic = analyze(
        _parse(
            "shape Row:\n"
            "    d: Decimal(10, 2)\n"
            'source rows: Row = postgres.table("rows")\n'
            "table selected:\n"
            "    from rows\n"
            "    select:\n"
            '        suppressed = abs(d / 2) if missing else "x"\n'
            '        known = abs(d / 2) if (other is None) else "x"\n'
        )
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in semantic.diagnostics
    ] == [
        ("PIE-S2102", "Unknown field: missing", 7, 36),
        (
            "PIE-S2105",
            "Invalid operands for operator conditional: expected same canonical branch types",
            8,
            17,
        ),
        ("PIE-S2102", "Unknown field: other", 8, 32),
    ]


@pytest.mark.parametrize("operator", ["in", "not in"])
@pytest.mark.parametrize("null", ["None", "k"], ids=["literal", "binding"])
def test_numeric_membership_with_null_keeps_its_boolean_result(
    operator: str, null: str
) -> None:
    source = (
        "shape Row:\n"
        "    n: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "\n"
        "    let k = None\n"
        "    select:\n"
    )
    membership = f"1.5 {operator} ({null}, n)"
    script, semantic, script_ir = _compile(source + f"        v = {membership}\n")
    value_type = semantic.model.expression_value_types[_select_expression(script, 0)]
    assert (value_type.resolved_type.name, value_type.nullability) == (
        "Bool",
        EffectiveNullability.NULLABLE,
    )
    assert emit_postgres_sql(script_ir).artifacts[0].sql == (
        f'SELECT\n    1.5 {operator.upper()} (NULL, "n") AS "v"\nFROM "rows"'
    )
    rejected = analyze(
        _parse(
            source + f"        v = abs({membership})\n"
            'query reader:\n    from selected\n    select:\n        w = v + "x"\n'
        )
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in rejected.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function abs at position 1: expected Int, Float or Decimal, got Bool",
            9,
            13,
        ),
        (
            "PIE-S2382",
            "`selected` is a table of this file; single-file SQL reads it by name, "
            "so the SQL runs only where the database already has a relation named "
            "selected (an EXPLICIT_MODULES project emits it as a CTE)",
            11,
            5,
        ),
    ]


@pytest.mark.parametrize("connector", ["postgres", "mysql"])
@pytest.mark.parametrize("operator", ["in", "not in"])
@pytest.mark.parametrize(
    ("field", "literal"),
    [("d", '"2020-01-01"'), ("s", '"active"')],
    ids=["date-text", "enum-label"],
)
def test_comparable_nonnumeric_null_membership_has_a_boolean_result(
    connector: str, operator: str, field: str, literal: str
) -> None:
    from pietto.ast_nodes import CallExpr, MembershipExpr

    predicate = f"{field} {operator} ({literal}, None)"
    script = _parse(
        (
            "enum Status:\n"
            "    active\n"
            "    gone\n"
            "shape Row:\n"
            "    d: Date | None\n"
            "    s: Status | None\n"
            f'source rows: Row = {connector}.table("rows")\n'
            "table selected:\n"
            "    from rows\n"
            "    select:\n"
            f"        direct = {predicate}\n"
            f"        lowered = lower({predicate})\n"
            f"        absolute = abs({predicate})\n"
        )
    )
    semantic = analyze(script)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in semantic.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: expected Text, got Bool",
            12,
            19,
        ),
        (
            "PIE-S2104",
            "Invalid argument type for function abs at position 1: expected Int, Float or Decimal, got Bool",
            13,
            20,
        ),
    ]
    for selected in _relation(script).select_items:
        expression = selected.expression
        membership = (
            expression.arguments[0] if isinstance(expression, CallExpr) else expression
        )
        assert isinstance(membership, MembershipExpr)
        value_type = semantic.model.expression_value_types[membership]
        assert (
            value_type.kind,
            value_type.resolved_type.name,
            value_type.nullability,
        ) == (ValueTypeKind.KNOWN, "Bool", EffectiveNullability.NULLABLE)


@pytest.mark.parametrize("predicate", ["d in (label, None)", 's in ("other", None)'])
def test_null_membership_keeps_unsupported_pairings_closed(predicate: str) -> None:
    source = (
        "enum Status:\n"
        "    active\n"
        "    gone\n"
        "shape Row:\n"
        "    d: Date | None\n"
        "    s: Status | None\n"
        "    label: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "table selected:\n"
        "    from rows\n"
        "    select:\n"
        f"        v = {predicate}\n"
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(_parse(source)).diagnostics
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator in: expected same canonical membership operands",
            12,
            13,
        )
    ]


def test_decimal_quotient_let_chains_check_as_their_int_twins() -> None:
    # Before: the quotient check followed every `let:` name to its value again
    # at each read, so a let doubling a quotient 30 times took exponential
    # time, and 1000 unused lets each adding 1 to the last one exceeded the
    # recursion limit (PIE-S2006), where the Int twin passed.
    def checked(value: str, step: str, count: int, use: str) -> list[tuple[str, int]]:
        lets = "".join(
            f"    let q{index} = {step.format(index - 1)}\n"
            for index in range(1, count + 1)
        )
        source = (
            "shape Row:\n"
            "    id: Int\n"
            "    a: Decimal(10, 2)\n"
            'source rows: Row = postgres.table("rows")\n'
            "table chained:\n"
            "    from rows\n"
            "\n"
            f"    let q0 = {value}\n"
            f"{lets}{use}    select:\n"
            "        id\n"
        )
        return [
            (item.code, item.location.line)
            for item in analyze(_parse(source)).diagnostics
        ]

    assert checked("a / 2", "q{0} + 1", 1000, "") == []
    assert checked("id / 2", "q{0} + 1", 1000, "") == []
    doubled = "q{0} + q{0}"
    where = "    where q30 > 1\n"
    assert checked("a / 2", doubled, 30, where) == [("PIE-S2328", 39)]
    assert checked("id / 2", doubled, 30, where) == [("PIE-S2328", 39)]


def test_existing_unqualified_sql_bytes_remain_stable() -> None:
    _, _, script_ir = _compile(
        SOURCE_PREFIX + "table selected:\n    from rows\n    select:\n        text\n"
    )

    postgres = emit_postgres_sql(script_ir)
    mysql = emit_mysql_sql(
        _compile(
            SOURCE_PREFIX + "table selected:\n"
            "    from mysql_rows\n"
            "    select:\n"
            "        text\n"
        )[2]
    )

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == 'SELECT\n    "text" AS "text"\nFROM "rows"'
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == "SELECT\n    `text` AS `text`\nFROM `rows`"


def test_qualified_sql_bytes_from_slice1_remain_stable() -> None:
    _, _, postgres_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    where rows.active == True\n"
        "    select:\n"
        "        rows.text\n"
    )
    _, _, mysql_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from mysql_rows\n"
        "    where mysql_rows.active == True\n"
        "    select:\n"
        "        mysql_rows.text\n"
    )

    postgres = emit_postgres_sql(postgres_ir)
    mysql = emit_mysql_sql(mysql_ir)

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        'SELECT\n    "rows"."text" AS "text"\nFROM "rows" AS "rows"\n'
        'WHERE "rows"."active" = TRUE'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n    `mysql_rows`.`text` AS `text`\n"
        "FROM `rows` AS `mysql_rows`\n"
        "WHERE `mysql_rows`.`active` = TRUE"
    )


def test_unused_relationship_template_does_not_participate_in_scalar_expression_binding() -> (
    None
):
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "relationship membership(member: Row, group: Row):\n"
        "    member.count == group.count\n"
        "table selected:\n"
        "    from rows\n"
        "    where count > 1 and active == True\n"
        "    select:\n"
        "        value = count % 2\n"
    )

    (template,) = semantic.model.relationship_templates
    assert template.declaration is script.relationship_templates[0]
    assert template.declaration.name == "membership"
    assert semantic.model.expression_value_types[
        _where_expression(script)
    ].resolved_type.name == ("Bool")
    assert semantic.model.expression_value_types[
        _select_expression(script, 0)
    ].resolved_type.name == ("Int")


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic = analyze(script)
    assert all(
        diagnostic.severity is not Severity.ERROR for diagnostic in semantic.diagnostics
    )
    assert semantic.script is not None
    script = semantic.script
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _parse(source: str) -> Script:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _relation(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )


def _where_expression(script: Script) -> Expression:
    relation = _relation(script)
    assert relation.where_clause is not None
    return relation.where_clause.expression


def _select_expression(script: Script, index: int) -> Expression:
    item = _relation(script).select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _diagnostics(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_diagnostic_span(diagnostic: Diagnostic, expression: Expression) -> None:
    assert diagnostic.location.path == expression.span.path
    assert diagnostic.location.line == expression.span.line
    assert diagnostic.location.column == expression.span.column
    assert diagnostic.location.end_line == expression.span.end_line
    assert diagnostic.location.end_column == expression.span.end_column
