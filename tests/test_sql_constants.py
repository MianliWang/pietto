"""The SQL each target emits for a read of a single-file top-level constant,
and for a `--set` value."""

from __future__ import annotations

import pytest

from _pietto_semantic_constants import CONSTANTS, QUERY, SHAPE, parsed
from pietto.ast_nodes import Script, UnaryExpr
from pietto.ir import build_ir
from pietto.semantic import analyze
from pietto.semantic.constants import override_constants
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SELECT = {
    "postgres": (
        'SELECT\n    "id" AS "id",\n'
        "    DATE '2024-01-31' AS \"as_of\",\n"
        "    TIMESTAMP '2024-01-31 08:30:00.250000' AS \"stamped\",\n"
        "    E'it''s \\\\ ok' AS \"tag\",\n"
        '    TRUE AS "on",\n'
        '    "amount" + (-1.5) AS "shifted",\n'
        '    CAST("at" AS date) = DATE \'2024-01-31\' AS "same_day",\n'
    ),
    "mysql": (
        "SELECT\n    `id` AS `id`,\n"
        "    DATE '2024-01-31' AS `as_of`,\n"
        "    TIMESTAMP '2024-01-31 08:30:00.250000' AS `stamped`,\n"
        "    _utf8mb4 X'69742773205c206f6b' AS `tag`,\n"
        "    TRUE AS `on`,\n"
        "    `amount` + (-1.5) AS `shifted`,\n"
        "    DATE(`at`) = DATE '2024-01-31' AS `same_day`,\n"
    ),
}


def _sql(script: Script, dialect: str) -> str:
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    lowered = build_ir(semantic.script or script, semantic.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    emit = emit_postgres_sql if dialect == "postgres" else emit_mysql_sql
    result = emit(lowered.ir)
    assert result.diagnostics == ()
    (artifact,) = result.artifacts
    return artifact.sql


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_each_read_emits_its_literal_of_the_declared_type(dialect: str) -> None:
    sql = _sql(parsed(SHAPE.format(dialect=dialect) + CONSTANTS + QUERY), dialect)

    assert sql.startswith(SELECT[dialect])
    quote = '"' if dialect == "postgres" else "`"
    assert (
        f"WHERE ((({quote}day{quote} <= DATE '2024-01-31') AND "
        f"({quote}at{quote} < TIMESTAMP '2024-01-31 08:30:00.250000')) AND "
        f"({quote}paid{quote} = TRUE)) AND ({quote}amount{quote} > (-1.5))"
    ) in sql
    assert ".`day` > DATE '2024-01-31'" in sql or ".\"day\" > DATE '2024-01-31'" in sql
    assert sql.endswith("LIMIT 3")


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_set_values_emit_the_bytes_of_the_same_source_values(dialect: str) -> None:
    source = SHAPE.format(dialect=dialect) + CONSTANTS + QUERY
    written = (
        source.replace('"2024-01-31"', '"2024-02-29"')
        .replace('"2024-01-31 08:30:00.25"', '"2024-02-29 23:59:59"')
        .replace("it's \\\\ ok", "EU")
        .replace("= True", "= False")
        .replace("= 3\n", "= 1_000\n")
        .replace("= -1.5", "= 2.0")
    )
    settings = (
        ("cutoff", "2024-02-29"),
        ("stamp", "2024-02-29 23:59:59"),
        ("label", "EU"),
        ("flag", "false"),
        ("limit_n", "1_000"),
        ("lo", "2.0"),
    )

    overridden = _sql(override_constants(parsed(source), settings), dialect)

    assert overridden == _sql(parsed(written), dialect)
    assert "DATE '2024-02-29'" in overridden and "LIMIT 1000" in overridden
    negative = override_constants(parsed(source), (("limit_n", "-7"),))
    (limit_n,) = (item for item in negative.constants if item.name == "limit_n")
    assert type(limit_n.value) is UnaryExpr
    assert limit_n.value.span == parsed(source).constants[4].value.span


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_a_negative_zero_reads_as_written(dialect: str) -> None:
    query = (
        "query q:\n    from events\n    select:\n        id\n"
        "        flipped = -{v}\n        scaled = amount * {v}\n"
    )
    shape = SHAPE.format(dialect=dialect)
    written = _sql(parsed(shape + query.format(v="(-0.0)")), dialect)

    for constant, settings in (("-0.0", ()), ("1.0", (("flip", "-0.0"),))):
        source = shape + f"flip: Float = {constant}\n\n" + query.format(v="flip")
        sql = _sql(override_constants(parsed(source), settings), dialect)
        # PostgreSQL would read `--0.0` as a comment and drop the column.
        assert sql == written and "--" not in sql
