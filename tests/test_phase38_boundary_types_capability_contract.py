from __future__ import annotations

from pietto.ast_nodes import TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, analyze


def test_boundary_type_count_capabilities_remain_fail_closed() -> None:
    for type_name, field_name, expected_code in (
        ("Any", "anything", "PIE-S2314"),
        ("Json", "payload", None),
        ("Bytes", "raw", None),
        ("UUID", "identifier", None),
    ):
        result = analyze(
            _parse(
                "shape Row:\n"
                f"    {field_name}: {type_name} nullable\n"
                'source rows: Row is postgres.table("rows")\n'
                "table totals:\n"
                "    from rows\n"
                "    select:\n"
                f"        total = count({field_name})\n"
            )
        )
        relation = next(
            definition
            for definition in result.model.relation_row_schemas
            if isinstance(definition, TableDef)
        )
        field = result.model.relation_row_schemas[relation].fields["total"]

        if expected_code is None:
            assert result.diagnostics == ()
            assert field.resolved_type.name == "Int"
            assert field.nullability is EffectiveNullability.NON_NULL
        else:
            assert [
                diagnostic.code
                for diagnostic in result.diagnostics
                if diagnostic.severity is Severity.ERROR
            ] == [expected_code]


def _parse(source: str):
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
