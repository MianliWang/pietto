from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
POSTGRES_INPUT = Path("tests/fixtures/phase19/postgres_count_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase19/mysql_count_aggregate.pietto")
POSTGRES_GOLDEN = "emit_sql_count_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_count_aggregate.sql"

SPAN = SourceSpan(
    path="aggregate.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="<unknown>",
    canonical_name="<unknown>",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
    nullability=NullabilityIR.UNKNOWN,
)
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
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter"),
    [
        (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql),
        (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql),
    ],
)
def test_direct_backend_count_sql_matches_reviewed_golden(
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
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_text_count_sql_matches_reviewed_golden(
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
def test_cli_json_count_sql_success_preserves_v1_shape(
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
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_count_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-count.sql"
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
    assert artifacts[0]["sql"] == _golden_text(golden_name).removesuffix("\n")
    assert output_path.read_bytes() == _golden_bytes(golden_name)


def test_invalid_count_shape_stops_before_sql_without_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "invalid-count.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text not null\n"
        'source orders: Order is postgres.table("orders")\n'
        "table paid_order_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = count() + 1\n",
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

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2310"]
    assert result["artifacts"] == []


def test_supported_aggregate_ir_shapes_render_without_changing_count_sql() -> None:
    assert render_expression_sql(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"
    assert render_mysql_expression(_aggregate("count", INT_NON_NULL)) == "COUNT(*)"
    assert (
        render_expression_sql(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'SUM("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "SUM(`amount`)"
    )
    assert (
        render_expression_sql(
            _aggregate("avg", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'AVG("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("avg", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "AVG(`amount`)"
    )


def test_malformed_aggregate_ir_shapes_still_fail_closed() -> None:
    count_with_too_many_arguments = _aggregate(
        "count",
        INT_NON_NULL,
        _field("amount", INT_NON_NULL),
        _field("score", FLOAT_NULLABLE),
    )
    count_with_non_field_argument = _aggregate("count", INT_NON_NULL, _literal(1))
    count_with_unknown_type = _aggregate("count", UNKNOWN_TYPE)
    unsupported_name = _aggregate(
        "median",
        FLOAT_NULLABLE,
        _field("amount", INT_NON_NULL),
    )
    sum_wrong_arity = _aggregate("sum", INT_NULLABLE)
    sum_non_field = _aggregate("sum", INT_NULLABLE, _literal(1))
    sum_decimal_argument = _aggregate(
        "sum",
        INT_NULLABLE,
        _field("price", DECIMAL_NON_NULL),
    )
    sum_bad_result_type = _aggregate(
        "sum",
        FLOAT_NULLABLE,
        _field("amount", INT_NON_NULL),
    )

    with pytest.raises(ValueError, match="PostgreSQL aggregate count expects 0 or 1"):
        render_expression_sql(count_with_too_many_arguments)
    with pytest.raises(ValueError, match="direct field argument"):
        render_expression_sql(count_with_non_field_argument)
    with pytest.raises(ValueError, match="PostgreSQL aggregate count expects Int"):
        render_expression_sql(count_with_unknown_type)
    with pytest.raises(
        ValueError,
        match="Unsupported PostgreSQL aggregate call: median",
    ):
        render_expression_sql(unsupported_name)
    with pytest.raises(ValueError, match="PostgreSQL aggregate sum expects 1"):
        render_expression_sql(sum_wrong_arity)
    with pytest.raises(ValueError, match="direct field argument"):
        render_expression_sql(sum_non_field)
    with pytest.raises(ValueError, match="approved logical shape"):
        render_expression_sql(sum_decimal_argument)
    with pytest.raises(ValueError, match="approved logical shape"):
        render_expression_sql(sum_bad_result_type)

    with pytest.raises(MySqlRenderError, match="MySQL aggregate count expects 0 or 1"):
        render_mysql_expression(count_with_too_many_arguments)
    with pytest.raises(MySqlRenderError, match="direct field argument"):
        render_mysql_expression(count_with_non_field_argument)
    with pytest.raises(MySqlRenderError, match="MySQL aggregate count expects Int"):
        render_mysql_expression(count_with_unknown_type)
    with pytest.raises(MySqlRenderError, match="Unsupported MySQL aggregate call"):
        render_mysql_expression(unsupported_name)
    with pytest.raises(MySqlRenderError, match="MySQL aggregate sum expects 1"):
        render_mysql_expression(sum_wrong_arity)
    with pytest.raises(MySqlRenderError, match="direct field argument"):
        render_mysql_expression(sum_non_field)
    with pytest.raises(MySqlRenderError, match="approved logical shape"):
        render_mysql_expression(sum_decimal_argument)
    with pytest.raises(MySqlRenderError, match="approved logical shape"):
        render_mysql_expression(sum_bad_result_type)


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


def _literal(value: StaticValue) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
