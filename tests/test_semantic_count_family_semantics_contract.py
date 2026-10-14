from __future__ import annotations

from pietto.ast_nodes import TableDef
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, analyze
from pietto.sql import emit_postgres_sql


def test_count_star_and_count_field_semantics_are_documented() -> None:
    script = _parse(_source("value: Int nullable"))
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    relation = next(
        definition
        for definition in semantic.model.relation_row_schemas
        if isinstance(definition, TableDef)
    )
    schema = semantic.model.relation_row_schemas[relation]
    assert schema.fields["rows"].resolved_type.name == "Int"
    assert schema.fields["values"].resolved_type.name == "Int"
    assert schema.fields["rows"].nullability is EffectiveNullability.NON_NULL
    assert schema.fields["values"].nullability is EffectiveNullability.NON_NULL

    ir = build_ir(script, semantic.model)
    assert ir.diagnostics == ()
    assert ir.ir is not None
    sql = emit_postgres_sql(ir.ir)
    assert sql.diagnostics == ()
    assert 'COUNT(*) AS "rows"' in sql.artifacts[0].sql
    assert 'COUNT("value") AS "values"' in sql.artifacts[0].sql


def test_sql_null_and_json_null_distinction_is_documented() -> None:
    semantic = analyze(_parse(_source("value: Json nullable")))
    assert semantic.diagnostics == ()


def _source(field: str) -> str:
    return (
        "shape Row:\n"
        f"    {field}\n"
        'source rows: Row is postgres.table("rows")\n'
        "table totals:\n"
        "    from rows\n"
        "    select:\n"
        "        rows = count()\n"
        "        values = count(value)\n"
    )


def _parse(source: str):
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
