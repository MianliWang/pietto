from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import CallExpr, Script, ShapeDef, SourceDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticResult, ValueTypeKind, analyze

SHAPE = "shape UserRow:\n    id: UUID not null\n    email: Text not null\n"


def test_postgres_table_with_text_argument_passes() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    )

    assert result.diagnostics == ()


@pytest.mark.parametrize(
    "connector",
    [
        "postgres.table()",
        'postgres.table("public.users", "extra")',
        "postgres.table(123)",
    ],
)
def test_invalid_postgres_table_arguments_report_pie_s2306(
    connector: str,
) -> None:
    result = analyze(_parse(SHAPE + f"source users: UserRow is {connector}\n"))

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2306",
            Severity.ERROR,
            "Invalid source connector arguments for postgres.table",
        )
    ]


def test_unknown_source_connector_reports_pie_s2306() -> None:
    result = analyze(_parse(SHAPE + 'source users: UserRow is mysql.table("users")\n'))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2306", "Unknown source connector: mysql.table")]


def test_non_call_source_connector_reports_pie_s2306() -> None:
    result = analyze(_parse(SHAPE + "source users: UserRow is 42\n"))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2306", "Invalid source connector expression")]


def test_unknown_argument_suppresses_connector_cascade() -> None:
    result = analyze(
        _parse(SHAPE + "source users: UserRow is postgres.table(missing)\n")
    )
    source = _source(result)
    connector = source.connector
    assert isinstance(connector, CallExpr)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert (
        result.model.expression_value_types[connector.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CheckMode.LOOSE, ()),
        (CheckMode.CHECKED, (("PIE-S2303", Severity.WARNING),)),
        (CheckMode.STRICT, (("PIE-S2303", Severity.ERROR),)),
    ],
)
def test_untyped_source_mode_policy_is_unchanged(
    mode: CheckMode,
    expected: tuple[tuple[str, Severity], ...],
) -> None:
    result = analyze(
        _parse('source users is postgres.table("public.users")\n'),
        mode_override=mode,
    )

    assert (
        tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
        )
        == expected
    )


def test_typed_source_schema_still_comes_from_declared_shape() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    )
    source = _source(result)
    shape = result.model.type_symbols["UserRow"]
    assert isinstance(shape, ShapeDef)
    schema = result.model.source_row_schemas[source]

    assert list(schema.fields) == ["id", "email"]
    assert schema.fields["id"].definition is shape.fields[0]
    assert schema.fields["email"].definition is shape.fields[1]


def test_connector_diagnostic_uses_connector_expression_span() -> None:
    script = _parse(
        SHAPE + 'source users: UserRow is mysql.table("users")\n',
        path="source-connectors.pie",
    )
    source = script.definitions[-1]
    assert isinstance(source, SourceDef)

    diagnostic = analyze(script).diagnostics[0]
    span = source.connector.span

    assert diagnostic.code == "PIE-S2306"
    assert diagnostic.location.path == span.path == "source-connectors.pie"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (span.line, span.column, span.end_line, span.end_column)


def test_connector_validation_does_not_mutate_input_ast() -> None:
    script = _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_connector_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _source(result: SemanticResult) -> SourceDef:
    definition = result.model.relation_symbols["users"]
    assert isinstance(definition, SourceDef)
    return definition


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
