from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
POSTGRES_INPUT = Path("tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto")
POSTGRES_GOLDEN = "emit_sql_sum_avg_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_sum_avg_aggregate.sql"

SPAN = SourceSpan(
    path="phase20-sum-avg-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
FLOAT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
DECIMAL_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Decimal",
    canonical_name="Decimal",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter"),
    [
        (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql),
        (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql),
    ],
)
def test_direct_backend_sum_avg_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "paid_order_stats"
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("render", "expected"),
    [
        (
            render_expression_sql,
            (
                'AVG(CAST("amount" AS double precision))',
                'AVG(CAST(("amount" + 1) AS double precision))',
                'AVG("score")',
                'AVG("price")',
                'CAST(SUM(CAST("amount" AS pg_catalog.int8)) AS pg_catalog.int8)',
            ),
        ),
        (
            render_mysql_expression,
            (
                "AVG(CAST(`amount` AS DOUBLE))",
                "AVG(CAST((`amount` + 1) AS DOUBLE))",
                "AVG(`score`)",
                "AVG(`price`)",
                "SUM(`amount`)",
            ),
        ),
    ],
)
def test_numeric_aggregate_casts_match_their_logical_types(
    render: Callable[[ExpressionIR], str],
    expected: tuple[str, ...],
) -> None:
    # Both targets average integers as exact decimals; Pietto types avg(Int) as
    # Float, so only that argument is cast, as project SQL does.
    amount = _field("amount", INT_NON_NULL)
    shifted = BinaryIR(
        span=SPAN,
        value_type=INT_NON_NULL,
        left=amount,
        operator="+",
        right=_literal(1, INT_NON_NULL),
    )
    float_type = replace(FLOAT_NULLABLE, nullability=NullabilityIR.NON_NULL)
    decimal_type = replace(DECIMAL_NON_NULL, nullability=NullabilityIR.NULLABLE)

    assert (
        render(_aggregate("avg", FLOAT_NULLABLE, amount)),
        render(_aggregate("avg", FLOAT_NULLABLE, shifted)),
        render(_aggregate("avg", FLOAT_NULLABLE, _field("score", float_type))),
        render(_aggregate("avg", decimal_type, _field("price", DECIMAL_NON_NULL))),
        render(_aggregate("sum", INT_NULLABLE, amount)),
    ) == expected


def test_postgres_int_sum_is_checked_in_global_grouped_and_having_sql() -> None:
    parsed = parse_source("""shape Row:
    bucket: Int
    value: Int
source rows: Row = postgres.table("rows")
table global_stats:
    from rows
    select:
        total = sum(value)
table grouped_stats:
    from rows
    group by bucket
    select:
        bucket
        total = sum(value)
    having:
        total > 0
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None, lowered.diagnostics

    artifacts = emit_postgres_sql(lowered.ir).artifacts
    checked_sum = 'CAST(SUM(CAST("value" AS pg_catalog.int8)) AS pg_catalog.int8)'

    assert len(artifacts) == 2
    assert artifacts[0].sql.count(checked_sum) == 1
    assert artifacts[1].sql.count(checked_sum) == 2
    assert f"HAVING\n    {checked_sum} > 0" in artifacts[1].sql


STDDEV_SOURCE = """shape Row:
    bucket: Int
    value: Int
    ratio: Float
source rows: Row = {target}.table("rows")
table global_spread:
    from rows
    select:
        spread = {call}
table grouped_spread:
    from rows
    group by bucket
    select:
        bucket
        spread = {call}
    having:
        spread > 1.0
"""


def _stddev_result(target: str, call: str) -> SqlResult:
    parsed = parse_source(STDDEV_SOURCE.format(target=target, call=call))
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None, lowered.diagnostics
    emit = emit_postgres_sql if target == "postgres" else emit_mysql_sql
    return emit(lowered.ir)


@pytest.mark.parametrize("field", ("value", "ratio"))
def test_postgres_stddev_casts_the_exact_sample_variance_once(field: str) -> None:
    """Int and Float share SQRT(CAST(VAR_SAMP(x) AS double precision)): the
    integer variance is exact numeric, so it is rounded once by the cast and
    the square root rounds correctly; STDDEV_SAMP(int8) would round twice."""
    result = _stddev_result("postgres", f"stddev({field})")
    spread = f'SQRT(CAST(VAR_SAMP("{field}") AS double precision))'

    assert result.diagnostics == ()
    global_sql, grouped_sql = (artifact.sql for artifact in result.artifacts)
    assert global_sql.count(spread) == 1
    assert f"HAVING\n    {spread} > 1.0" in grouped_sql
    for sql in (global_sql, grouped_sql):
        # Never a population or double-rounding spelling, nor an argument cast.
        assert not any(
            token in sql
            for token in (
                "STD(",
                "STDDEV(",
                "STDDEV_POP(",
                "STDDEV_SAMP(",
                "VAR_SAMP(CAST(",
            )
        )


def test_mysql_stddev_is_the_sample_deviation_of_a_float_only() -> None:
    result = _stddev_result("mysql", "stddev(ratio)")

    assert result.diagnostics == ()
    global_sql, grouped_sql = (artifact.sql for artifact in result.artifacts)
    assert "STDDEV_SAMP(`ratio`) AS `spread`" in global_sql
    assert "HAVING\n    STDDEV_SAMP(`ratio`) > 1.0" in grouped_sql
    for sql in (global_sql, grouped_sql):
        assert not any(token in sql for token in ("STD(", "STDDEV(", "STDDEV_POP("))

    refused = _stddev_result("mysql", "stddev(value)")
    assert refused.artifacts == ()
    assert [(d.code, d.message) for d in refused.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "MySQL aggregate stddev of an Int argument is not supported",
        )
        for name in ("global_spread", "grouped_spread")
    ]


@pytest.mark.parametrize("field", ("value", "ratio"))
@pytest.mark.parametrize(
    ("function", "spread"),
    (
        ("variance", 'CAST(VAR_SAMP("{field}") AS double precision)'),
        ("pvariance", 'CAST(VAR_POP("{field}") AS double precision)'),
        ("pstdev", 'SQRT(CAST(VAR_POP("{field}") AS double precision))'),
    ),
)
def test_postgres_variance_and_population_deviation_cast_the_variance_once(
    field: str, function: str, spread: str
) -> None:
    """`variance` and `pvariance` are VAR_SAMP and VAR_POP cast once to double
    precision and `pstdev` the square root of the cast VAR_POP, as `stddev`:
    never an argument cast, the MySQL population VARIANCE, or STDDEV_POP of an
    integer, which would round the numeric square root first."""
    result = _stddev_result("postgres", f"{function}({field})")
    spread = spread.format(field=field)

    assert result.diagnostics == ()
    global_sql, grouped_sql = (artifact.sql for artifact in result.artifacts)
    assert f'{spread} AS "spread"' in global_sql
    assert f"HAVING\n    {spread} > 1.0" in grouped_sql
    for sql in (global_sql, grouped_sql):
        assert not any(
            token in sql
            for token in (
                "VARIANCE(",
                "STD(",
                "STDDEV(",
                "STDDEV_POP(",
                "VAR_SAMP(CAST(",
                "VAR_POP(CAST(",
            )
        )


@pytest.mark.parametrize(
    ("function", "spread"),
    (
        ("variance", "VAR_SAMP(`ratio`)"),
        ("pvariance", "VAR_POP(`ratio`)"),
        ("pstdev", "STDDEV_POP(`ratio`)"),
    ),
)
def test_mysql_variance_and_population_deviation_are_of_a_float_only(
    function: str, spread: str
) -> None:
    """MySQL emits the sample and population variances and the population
    deviation of a Float as VAR_SAMP, VAR_POP and STDDEV_POP, never its
    population VARIANCE, STD or STDDEV; an Int is refused as for `stddev`, as
    MySQL computes an integer variance in DOUBLE."""
    result = _stddev_result("mysql", f"{function}(ratio)")

    assert result.diagnostics == ()
    global_sql, grouped_sql = (artifact.sql for artifact in result.artifacts)
    assert f"{spread} AS `spread`" in global_sql
    assert f"HAVING\n    {spread} > 1.0" in grouped_sql
    for sql in (global_sql, grouped_sql):
        assert not any(token in sql for token in ("VARIANCE(", "STD(", "STDDEV("))

    refused = _stddev_result("mysql", f"{function}(value)")
    assert refused.artifacts == ()
    assert [(d.code, d.message) for d in refused.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            f"MySQL aggregate {function} of an Int argument is not supported; "
            "emit with --dialect postgres",
        )
        for name in ("global_spread", "grouped_spread")
    ]


@pytest.mark.parametrize("function", ("stddev", "variance", "pvariance", "pstdev"))
@pytest.mark.parametrize(
    "emitter",
    (emit_postgres_sql, emit_mysql_sql),
)
@pytest.mark.parametrize(
    "case", ("decimal_argument", "expression_argument", "non_null_result")
)
def test_malformed_hand_built_stddev_ir_fails_closed_with_pie_b1000(
    emitter: Callable[[ScriptIR], SqlResult], case: str, function: str
) -> None:
    script_ir = _compile(
        POSTGRES_INPUT if emitter is emit_postgres_sql else MYSQL_INPUT
    )
    relation = _relation_ir(script_ir)
    score = _field("score", replace(FLOAT_NULLABLE, nullability=NullabilityIR.NON_NULL))
    bad = {
        "decimal_argument": _aggregate(
            function, FLOAT_NULLABLE, _field("price", DECIMAL_NON_NULL)
        ),
        "expression_argument": _aggregate(
            function,
            FLOAT_NULLABLE,
            BinaryIR(
                span=SPAN,
                value_type=score.value_type,
                left=score,
                operator="+",
                right=score,
            ),
        ),
        "non_null_result": _aggregate(
            function, replace(FLOAT_NULLABLE, nullability=NullabilityIR.NON_NULL), score
        ),
    }[case]
    bad_relation = replace(
        relation,
        projections=(replace(relation.projections[1], expression=bad),),
    )

    result = emitter(
        ScriptIR(
            definitions=tuple(
                bad_relation if definition is relation else definition
                for definition in script_ir.definitions
            )
        )
    )

    assert result.artifacts == ()
    assert [d.code for d in result.diagnostics] == ["PIE-B1000"]


QUANTILE_SOURCE = STDDEV_SOURCE.replace("spread = {call}", "middle = {call}").replace(
    "spread > 1.0", "middle > 1.0"
)


def _quantile_result(target: str, call: str) -> SqlResult:
    parsed = parse_source(QUANTILE_SOURCE.format(target=target, call=call))
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None, lowered.diagnostics
    emit = emit_postgres_sql if target == "postgres" else emit_mysql_sql
    return emit(lowered.ir)


@pytest.mark.parametrize(
    ("call", "expected"),
    (
        (
            "median(value)",
            'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST("value" AS double '
            "precision))",
        ),
        ("median(ratio)", 'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "ratio")'),
        (
            "quantile(value, 0.9)",
            'PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY CAST("value" AS double '
            "precision))",
        ),
        (
            "quantile(ratio, 0.0)",
            'PERCENTILE_CONT(0.0) WITHIN GROUP (ORDER BY "ratio")',
        ),
        (
            "quantile(ratio, 1.0)",
            'PERCENTILE_CONT(1.0) WITHIN GROUP (ORDER BY "ratio")',
        ),
    ),
)
def test_postgres_median_and_quantile_are_the_interpolated_percentile(
    call: str, expected: str
) -> None:
    """PERCENTILE_CONT interpolates between the two nearest non-NULL values in
    double precision; an Int value is cast to double precision first."""
    result = _quantile_result("postgres", call)

    assert result.diagnostics == ()
    global_sql, grouped_sql = (artifact.sql for artifact in result.artifacts)
    assert f'{expected} AS "middle"' in global_sql
    assert f'{expected} AS "middle"' in grouped_sql
    assert f"HAVING\n    {expected} > 1.0" in grouped_sql
    assert "PERCENTILE_DISC" not in global_sql + grouped_sql


@pytest.mark.parametrize("call", ("median(value)", "quantile(ratio, 0.5)"))
def test_mysql_refuses_median_and_quantile(call: str) -> None:
    refused = _quantile_result("mysql", call)
    name = call.split("(")[0]

    assert refused.artifacts == ()
    assert [(d.code, d.message) for d in refused.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {relation}. "
            f"MySQL aggregate {name} is not supported: MySQL has no interpolated "
            "percentile; emit this relation for PostgreSQL",
        )
        for relation in ("global_spread", "grouped_spread")
    ]


@pytest.mark.parametrize(
    "case",
    (
        "decimal_argument",
        "expression_argument",
        "non_null_result",
        "fraction_above_one",
        "int_fraction",
        "field_fraction",
        "median_fraction",
    ),
)
def test_malformed_hand_built_quantile_ir_fails_closed_with_pie_b1000(
    case: str,
) -> None:
    script_ir = _compile(POSTGRES_INPUT)
    relation = _relation_ir(script_ir)
    non_null = replace(FLOAT_NULLABLE, nullability=NullabilityIR.NON_NULL)
    score = _field("score", non_null)
    half = _literal(0.5, non_null)
    bad = {
        "decimal_argument": _aggregate(
            "quantile", FLOAT_NULLABLE, _field("price", DECIMAL_NON_NULL), half
        ),
        "expression_argument": _aggregate(
            "median",
            FLOAT_NULLABLE,
            BinaryIR(
                span=SPAN,
                value_type=score.value_type,
                left=score,
                operator="+",
                right=score,
            ),
        ),
        "non_null_result": _aggregate("median", non_null, score),
        "fraction_above_one": _aggregate(
            "quantile", FLOAT_NULLABLE, score, _literal(1.5, non_null)
        ),
        "int_fraction": _aggregate(
            "quantile", FLOAT_NULLABLE, score, _literal(1, INT_NON_NULL)
        ),
        "field_fraction": _aggregate("quantile", FLOAT_NULLABLE, score, score),
        "median_fraction": _aggregate("median", FLOAT_NULLABLE, score, half),
    }[case]
    bad_relation = replace(
        relation,
        projections=(replace(relation.projections[1], expression=bad),),
    )

    result = emit_postgres_sql(
        ScriptIR(
            definitions=tuple(
                bad_relation if definition is relation else definition
                for definition in script_ir.definitions
            )
        )
    )

    assert result.artifacts == ()
    assert [d.code for d in result.diagnostics] == ["PIE-B1000"]


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_text_sum_avg_sql_matches_reviewed_golden(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_sum_avg_sql_success_preserves_v1_shape(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert set(result) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "paid_order_stats",
            "sql": _golden_sql(golden_name),
        }
    ]


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_sum_avg_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-sum-avg.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["sql"] == _golden_sql(golden_name)
    assert output_path.read_bytes() == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("select_body", "expected_code"),
    [
        ("        revenue = sum(1)\n", "PIE-S2315"),
        ("        average = avg(1)\n", "PIE-S2315"),
        ("        revenue = sum(status)\n", "PIE-S2314"),
        ("        average = avg(status)\n", "PIE-S2314"),
        ("        revenue = sum(avg(amount))\n", "PIE-S2311"),
        ("        revenue = sum(amount) if True else 1\n", "PIE-S2310"),
        ("        status\n        revenue = sum(amount)\n", "PIE-S2312"),
    ],
)
def test_invalid_sum_avg_shapes_stop_before_sql_without_artifacts(
    select_body: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "invalid-sum-avg.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text\n"
        "    amount: Int\n"
        "    price: Decimal\n"
        'source orders: Order = postgres.table("orders")\n'
        "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}",
        encoding="utf-8",
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == [expected_code]
    assert "PIE-B1000" not in codes
    assert result["artifacts"] == []


@pytest.mark.parametrize(
    ("input_path", "emitter"),
    [
        (POSTGRES_INPUT, emit_postgres_sql),
        (MYSQL_INPUT, emit_mysql_sql),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "unsupported_function",
        "wrong_arity",
        "non_field_argument",
        "decimal_argument",
        "malformed_result_type",
    ],
)
def test_malformed_hand_built_sum_avg_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir)
    projection = relation.projections[1]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_aggregate(case)),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"


def _compile(path: Path) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _malformed_aggregate(case: str) -> AggregateCallIR:
    if case == "unsupported_function":
        return _aggregate("kurtosis", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "wrong_arity":
        return _aggregate("sum", INT_NULLABLE)
    if case == "non_field_argument":
        return _aggregate("sum", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "decimal_argument":
        return _aggregate("sum", INT_NULLABLE, _field("price", DECIMAL_NON_NULL))
    if case == "malformed_result_type":
        return _aggregate("sum", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    raise AssertionError(f"Unknown malformed aggregate case: {case}")


def _aggregate(
    function: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> AggregateCallIR:
    return AggregateCallIR(
        span=SPAN,
        value_type=value_type,
        function=function,
        arguments=arguments,
    )


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _literal(value: StaticValue, value_type: TypeRefIR) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_sql(name: str) -> str:
    """The SQL of a one-artifact golden, without its `--` name line and `;`."""

    return _golden_text(name).split("\n", 1)[1].removesuffix(";\n")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    """The artifacts as `emit-sql` text prints them: named, `;`-terminated."""

    return (
        "\n\n".join(f"-- {item.name}\n{item.sql};" for item in result.artifacts) + "\n"
    ).encode("utf-8")


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
