from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    analyze,
)

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    'source users: User is postgres.table("users")\n'
)


def test_bare_field_projection_keeps_field_name_and_type() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n    from users\n    select:\n        email\n"
        )
    )
    schema = result.model.relation_row_schemas[_relation(result, TableDef)]

    assert list(schema.fields) == ["email"]
    assert schema.fields["email"].resolved_type.name == "Text"
    assert schema.fields["email"].nullability is EffectiveNullability.NULLABLE
    assert result.diagnostics == ()


def test_explicit_alias_becomes_output_name_with_unknown_type() -> None:
    result = analyze(
        _parse(
            SOURCE + "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        email_norm = lower(trim(email))\n"
        )
    )
    schema = result.model.relation_row_schemas[_relation(result, QueryDef)]

    assert list(schema.fields) == ["email_norm"]
    assert schema.fields["email_norm"].resolved_type.kind is TypeKind.UNKNOWN
    assert schema.fields["email_norm"].nullability is EffectiveNullability.UNKNOWN
    assert result.diagnostics == ()


def test_bare_dotted_name_uses_last_segment_as_output_name() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        users.email\n"
        )
    )
    schema = result.model.relation_row_schemas[_relation(result, TableDef)]

    assert list(schema.fields) == ["email"]
    assert schema.fields["email"].resolved_type.kind is TypeKind.UNKNOWN
    assert result.diagnostics == ()


def test_projection_output_order_excludes_unnamed_computed_expression() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        normalized = lower(email)\n"
            "        lower(email)\n"
            "        users.email\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    schema = result.model.relation_row_schemas[_relation(result, TableDef)]

    assert list(schema.fields) == ["id", "normalized", "email"]
    assert result.diagnostics == ()


def test_duplicate_bare_field_outputs_report_pie_s2305() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        email\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2305"]


def test_alias_conflicting_with_bare_output_reports_pie_s2305() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "        email = lower(email)\n"
        )
    )
    schema = result.model.relation_row_schemas[_relation(result, TableDef)]

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2305", "Duplicate projection field: email")]
    assert list(schema.fields) == ["email"]
    assert schema.fields["email"].resolved_type.name == "Text"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CheckMode.LOOSE, ()),
        (CheckMode.CHECKED, (("PIE-S2304", Severity.WARNING),)),
        (CheckMode.STRICT, (("PIE-S2304", Severity.ERROR),)),
    ],
)
@pytest.mark.parametrize("keyword", ["table", "query"])
def test_unnamed_computed_projection_mode_policy(
    mode: CheckMode,
    expected: tuple[tuple[str, Severity], ...],
    keyword: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE + f"{keyword} projected:\n"
            "    from users\n"
            "    select:\n"
            "        lower(trim(email))\n"
        ),
        mode_override=mode,
    )
    schema = result.model.relation_row_schemas[
        _relation(result, TableDef if keyword == "table" else QueryDef)
    ]

    assert (
        tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
        )
        == expected
    )
    assert schema.is_unknown is False
    assert schema.fields == {}


def test_unnamed_computed_projection_diagnostic_uses_item_span() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        lower(email)\n",
        path="projection.pie",
    )
    table = script.definitions[-1]
    assert isinstance(table, TableDef)

    diagnostic = analyze(script).diagnostics[0]
    item = table.select_items[0]

    assert diagnostic.code == "PIE-S2304"
    assert diagnostic.location.path == item.span.path == "projection.pie"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        item.span.line,
        item.span.column,
        item.span.end_line,
        item.span.end_column,
    )


def test_complex_projection_with_alias_has_no_pie_s2304() -> None:
    result = analyze(
        _parse(
            SOURCE + "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        email_norm = lower(trim(email))\n"
        ),
        mode_override=CheckMode.STRICT,
    )

    assert result.diagnostics == ()


def test_unknown_input_schema_preserves_names_without_field_cascade() -> None:
    result = analyze(
        _parse(
            'source raw is postgres.table("raw")\n'
            "table projected:\n"
            "    from raw\n"
            "    select:\n"
            "        missing\n"
            "        normalized = unknown_call(missing)\n"
        ),
        mode_override=CheckMode.LOOSE,
    )
    schema = result.model.relation_row_schemas[_relation(result, TableDef)]

    assert result.diagnostics == ()
    assert schema.is_unknown is True
    assert list(schema.fields) == ["missing", "normalized"]
    assert all(
        field.resolved_type.kind is TypeKind.UNKNOWN for field in schema.fields.values()
    )


def test_projection_name_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "        email = lower(email)\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_projection_name_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            SOURCE + "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        email_norm = lower(trim(email))\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation[RelationT: (TableDef, QueryDef)](
    result: SemanticResult,
    expected_type: type[RelationT],
) -> RelationT:
    definition = result.model.relation_symbols["projected"]
    assert isinstance(definition, expected_type)
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
