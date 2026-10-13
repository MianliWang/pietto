from __future__ import annotations

from pietto.ast_nodes import TableDef
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, analyze


def test_min_max_results_are_nullable_same_logical_type() -> None:
    parsed = parse_source(
        "shape Row:\n"
        "    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "table extrema:\n"
        "    from rows\n"
        "    select:\n"
        "        smallest = min(amount)\n"
        "        largest = max(amount)\n"
    )
    assert parsed.ast is not None
    assert parsed.diagnostics == ()

    relation = next(
        definition
        for definition in parsed.ast.definitions
        if isinstance(definition, TableDef)
    )
    result = analyze(parsed.ast)
    schema = result.model.relation_row_schemas[relation]

    assert result.diagnostics == ()
    for name in ("smallest", "largest"):
        assert schema.fields[name].resolved_type.name == "Int"
        assert schema.fields[name].nullability is EffectiveNullability.NULLABLE
