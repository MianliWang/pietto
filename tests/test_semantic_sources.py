from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Script, ShapeDef, SourceDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    RowSchema,
    SemanticResult,
    TypeKind,
    analyze,
)


def test_typed_source_builds_known_ordered_row_schema() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            "    email: Text nullable\n"
            'source users: User is postgres.table("public.users")\n'
        )
    )
    source = _source(result, "users")
    shape = result.model.type_symbols["User"]
    assert isinstance(shape, ShapeDef)

    schema = result.model.source_row_schemas[source]

    assert isinstance(schema, RowSchema)
    assert schema.is_unknown is False
    assert list(schema.fields) == ["id", "email"]
    assert schema.fields["id"].resolved_type.kind is TypeKind.BUILTIN
    assert schema.fields["id"].resolved_type.name == "UUID"
    assert schema.fields["id"].nullability is EffectiveNullability.NON_NULL
    assert schema.fields["id"].definition is shape.fields[0]
    assert schema.fields["email"].resolved_type.kind is TypeKind.BUILTIN
    assert schema.fields["email"].nullability is EffectiveNullability.NULLABLE
    assert schema.fields["email"].definition is shape.fields[1]
    assert result.diagnostics == ()


def test_source_row_field_preserves_user_resolved_type() -> None:
    result = analyze(
        _parse(
            "type Email = Text not null\n"
            "shape User:\n"
            "    email: Email nullable\n"
            'source users: User is postgres.table("public.users")\n'
        )
    )
    schema = result.model.source_row_schemas[_source(result, "users")]

    row_field = schema.fields["email"]
    assert row_field.resolved_type.kind is TypeKind.TYPE_ALIAS
    assert row_field.resolved_type.definition is result.model.type_symbols["Email"]
    assert row_field.nullability is EffectiveNullability.NULLABLE


def test_missing_source_shape_reports_p2303_and_unknown_schema() -> None:
    result = analyze(
        _parse('source users: Missing is postgres.table("public.users")\n')
    )
    source = _source(result, "users")

    assert _diagnostics(result, "PIE-S2303") == [
        (Severity.ERROR, "Unknown source shape: Missing")
    ]
    assert result.model.source_row_schemas[source].is_unknown is True
    assert result.model.source_row_schemas[source].fields == {}


@pytest.mark.parametrize(
    ("definition", "name"),
    [
        ("type User = Text not null\n", "User"),
        ("enum User:\n    active\n", "User"),
        ("", "Text"),
    ],
)
def test_source_shape_must_refer_to_shape(
    definition: str,
    name: str,
) -> None:
    result = analyze(
        _parse(f'{definition}source users: {name} is postgres.table("public.users")\n')
    )
    source = _source(result, "users")

    assert _diagnostics(result, "PIE-S2303") == [
        (Severity.ERROR, f"Source shape must refer to a shape: {name}")
    ]
    assert result.model.source_row_schemas[source].is_unknown is True


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CheckMode.LOOSE, ()),
        (CheckMode.CHECKED, (("PIE-S2303", Severity.WARNING),)),
        (CheckMode.STRICT, (("PIE-S2303", Severity.ERROR),)),
    ],
)
def test_untyped_source_mode_policy(
    mode: CheckMode,
    expected: tuple[tuple[str, Severity], ...],
) -> None:
    result = analyze(
        _parse('source events is postgres.table("public.events")\n'),
        mode_override=mode,
    )
    source = _source(result, "events")

    assert (
        tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
        )
        == expected
    )
    assert result.model.source_row_schemas[source].is_unknown is True


def test_untyped_source_diagnostic_uses_source_span() -> None:
    path = Path("examples/semantic/untyped-source.pietto")
    script = _parse(
        'source events is postgres.table("public.events")\n',
        path=path,
    )
    source = script.definitions[0]
    assert isinstance(source, SourceDef)

    diagnostic = analyze(script).diagnostics[0]

    _assert_location_matches(diagnostic, source)


def test_source_checking_continues_after_invalid_source() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            'source missing: Missing is postgres.table("missing")\n'
            'source users: User is postgres.table("users")\n'
            'source raw is postgres.table("raw")\n'
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.severity)
        for diagnostic in result.diagnostics
    ] == [
        (3, "PIE-S2303", Severity.ERROR),
        (5, "PIE-S2303", Severity.WARNING),
    ]
    assert result.model.source_row_schemas[_source(result, "missing")].is_unknown
    assert not result.model.source_row_schemas[_source(result, "users")].is_unknown
    assert result.model.source_row_schemas[_source(result, "raw")].is_unknown


def test_table_and_query_expressions_keep_existing_semantic_behavior() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            'source users: User is postgres.table("users")\n'
            "table projected:\n"
            "    from users\n"
            '    where matches("value", "value")\n'
            "    select:\n"
            '        computed = lower("value")\n'
            "query output:\n"
            "    from projected\n"
            "    select:\n"
            '        recomputed = trim("value")\n'
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.source_row_schemas) == [_source(result, "users")]


def test_source_schema_mappings_are_readonly() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            'source users: User is postgres.table("users")\n'
        )
    )
    source = _source(result, "users")
    schema = result.model.source_row_schemas[source]

    with pytest.raises(TypeError):
        result.model.source_row_schemas[source] = RowSchema()  # type: ignore[index]
    with pytest.raises(TypeError):
        schema.fields["other"] = schema.fields["id"]  # type: ignore[index]


def test_source_checks_do_not_mutate_input_ast() -> None:
    script = _parse(
        "shape User:\n"
        "    id: UUID not null\n"
        'source users: User is postgres.table("users")\n'
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_source_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            'source users: User is postgres.table("users")\n'
            'source raw is postgres.table("raw")\n'
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _source(result: SemanticResult, name: str) -> SourceDef:
    definition = result.model.relation_symbols[name]
    assert isinstance(definition, SourceDef)
    return definition


def _diagnostics(
    result: SemanticResult,
    code: str,
) -> list[tuple[Severity, str]]:
    return [
        (diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.code == code
    ]


def _assert_location_matches(diagnostic: Diagnostic, source: SourceDef) -> None:
    assert diagnostic.location.path == source.span.path
    assert diagnostic.location.line == source.span.line
    assert diagnostic.location.column == source.span.column
    assert diagnostic.location.end_line == source.span.end_line
    assert diagnostic.location.end_column == source.span.end_column


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
