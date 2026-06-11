from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Node, QueryDef, Script, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, RowSchema, SemanticResult, analyze

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    'source users: User is postgres.table("users")\n'
)


def test_table_from_typed_source_builds_known_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    schema = result.model.relation_row_schemas[table]

    assert schema.is_unknown is False
    assert list(schema.fields) == ["id", "email"]
    assert result.diagnostics == ()


def test_query_from_typed_source_builds_known_schema() -> None:
    result = analyze(
        _parse(SOURCE + "query output:\n    from users\n    select:\n        email\n")
    )
    query = _relation(result, "output", QueryDef)

    assert list(result.model.relation_row_schemas[query].fields) == ["email"]


def test_query_from_table_uses_table_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)
    query = _relation(result, "output", QueryDef)

    assert (
        result.model.relation_row_schemas[query].fields["email"]
        is result.model.relation_row_schemas[table].fields["email"]
    )


def test_output_field_order_and_type_information_are_preserved() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        id\n"
        )
    )
    table = _relation(result, "projected", TableDef)
    source = _relation(result, "users", SourceDef)

    schema = result.model.relation_row_schemas[table]
    source_schema = result.model.source_row_schemas[source]

    assert list(schema.fields) == ["email", "id"]
    assert (
        schema.fields["email"].resolved_type
        is source_schema.fields["email"].resolved_type
    )
    assert schema.fields["email"].nullability is EffectiveNullability.NULLABLE
    assert schema.fields["id"].nullability is EffectiveNullability.NON_NULL


def test_unknown_selected_field_reports_p2102_and_unknown_schema() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing")
    ]
    assert result.model.relation_row_schemas[table].is_unknown is True


def test_semantic_diagnostic_uses_canonical_code_format() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        missing\n"
        )
    )

    assert result.diagnostics[0].code == "PIE-S2102"


def test_unknown_field_diagnostic_uses_expression_span() -> None:
    path = Path("examples/semantic/unknown-field.pietto")
    script = _parse(
        SOURCE + "query output:\n    from users\n    select:\n        missing\n",
        path=path,
    )
    query = script.definitions[-1]
    assert isinstance(query, QueryDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, query.select_items[0].expression)


def test_duplicate_projection_reports_p2305_and_keeps_first_field() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        email\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2305", Severity.ERROR, "Duplicate projection field: email")
    ]
    assert list(result.model.relation_row_schemas[table].fields) == ["email"]


def test_duplicate_projection_diagnostic_uses_later_item_span() -> None:
    path = Path("examples/semantic/duplicate-projection.pietto")
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "        id\n",
        path=path,
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, table.select_items[1])


def test_unknown_input_schema_suppresses_field_diagnostics() -> None:
    result = analyze(
        _parse(
            'source raw is postgres.table("raw")\n'
            "table projected:\n"
            "    from raw\n"
            "    select:\n"
            "        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2303"]
    assert result.model.relation_row_schemas[table].is_unknown is True


def test_unknown_from_target_produces_unknown_schema_without_field_cascade() -> None:
    result = analyze(
        _parse(
            "query output:\n"
            "    from missing_relation\n"
            "    select:\n"
            "        missing_field\n"
        )
    )
    query = _relation(result, "output", QueryDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2301"]
    assert result.model.relation_row_schemas[query].is_unknown is True


def test_mixed_projections_validate_names_without_checking_calls() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    where unknown_predicate(missing_field)\n"
            "    select:\n"
            "        lower(email)\n"
            "        normalized = unknown_call(missing_field)\n"
            "        missing\n"
        )
    )
    table = _relation(result, "projected", TableDef)

    assert _diagnostics(result) == [
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing_field"),
        (
            "PIE-S2304",
            Severity.WARNING,
            "Computed projection requires an explicit alias",
        ),
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing_field"),
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing"),
    ]
    assert result.model.relation_row_schemas[table].is_unknown is True
    assert list(result.model.relation_row_schemas[table].fields) == [
        "normalized",
        "missing",
    ]


def test_unknown_upstream_schema_suppresses_downstream_field_diagnostics() -> None:
    result = analyze(
        _parse(
            SOURCE + "table first:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        another_missing\n"
        )
    )
    second = _relation(result, "second", QueryDef)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.relation_row_schemas[second].is_unknown is True


def test_relation_cycles_produce_unknown_schemas_with_cycle_diagnostic() -> None:
    result = analyze(
        _parse(
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "table second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n"
        )
    )
    first = _relation(result, "first", TableDef)
    second = _relation(result, "second", TableDef)

    assert result.model.relation_row_schemas[first].is_unknown is True
    assert result.model.relation_row_schemas[second].is_unknown is True
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2302"]


def test_relation_row_schema_mapping_is_readonly() -> None:
    result = analyze(
        _parse(SOURCE + "table projected:\n    from users\n    select:\n        id\n")
    )
    table = _relation(result, "projected", TableDef)

    with pytest.raises(TypeError):
        result.model.relation_row_schemas[table] = RowSchema()  # type: ignore[index]


def test_relation_schema_propagation_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n    from users\n    select:\n        id\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_relation_schema_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            "        id\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation[RelationT: (SourceDef, TableDef, QueryDef)](
    result: SemanticResult,
    name: str,
    expected_type: type[RelationT],
) -> RelationT:
    definition = result.model.relation_symbols[name]
    assert isinstance(definition, expected_type)
    return definition


def _diagnostics(
    result: SemanticResult,
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ]


def _assert_location_matches(diagnostic: Diagnostic, node: Node) -> None:
    span = node.span
    assert diagnostic.location.path == span.path
    assert diagnostic.location.line == span.line
    assert diagnostic.location.column == span.column
    assert diagnostic.location.end_line == span.end_line
    assert diagnostic.location.end_column == span.end_column


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
