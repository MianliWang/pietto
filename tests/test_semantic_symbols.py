from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    ConstraintDef,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, analyze


def test_unique_definitions_populate_expected_namespaces() -> None:
    result = analyze(
        _parse(
            "type Age = Int not null\n"
            "enum Status:\n"
            "    active\n"
            "shape User:\n"
            "    id: UUID not null\n"
            "derive normalize(value: Text not null) -> Text not null:\n"
            "    value\n"
            "constraint valid(value: Text not null) -> Bool not null:\n"
            "    true\n"
            'source users: User is postgres.table("public.users")\n'
            "table active_users:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query output:\n"
            "    from active_users\n"
            "    select:\n"
            "        id\n"
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.type_symbols) == ["Age", "Status", "User"]
    assert isinstance(result.model.type_symbols["Age"], TypeDef)
    assert isinstance(result.model.type_symbols["Status"], EnumDef)
    assert isinstance(result.model.type_symbols["User"], ShapeDef)
    assert list(result.model.callable_symbols) == ["normalize", "valid"]
    assert isinstance(result.model.callable_symbols["normalize"], DeriveDef)
    assert isinstance(result.model.callable_symbols["valid"], ConstraintDef)
    assert list(result.model.relation_symbols) == [
        "users",
        "active_users",
        "output",
    ]
    assert isinstance(result.model.relation_symbols["users"], SourceDef)
    assert isinstance(result.model.relation_symbols["active_users"], TableDef)
    assert isinstance(result.model.relation_symbols["output"], QueryDef)


def test_duplicate_shape_reports_p2001() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            "shape User:\n"
            "    email: Text not null\n"
        )
    )

    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-S2001"
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.message == "Duplicate symbol name in type namespace: User"


def test_source_and_table_names_duplicate_in_relation_namespace() -> None:
    result = analyze(
        _parse(
            'source users is postgres.table("public.users")\n'
            "table users:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
        ),
        mode_override=CheckMode.LOOSE,
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2001"]
    assert (
        result.diagnostics[0].message
        == "Duplicate symbol name in relation namespace: users"
    )


def test_derive_and_constraint_names_duplicate_in_callable_namespace() -> None:
    result = analyze(
        _parse(
            "derive normalize_email(email: Text not null) -> Text not null:\n"
            "    lower(email)\n"
            "constraint normalize_email(email: Text not null) -> Bool not null:\n"
            "    email is not null\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2001"]
    assert (
        result.diagnostics[0].message
        == "Duplicate symbol name in callable namespace: normalize_email"
    )


def test_same_name_across_namespaces_is_allowed() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    id: UUID not null\n"
            "derive User(value: Text not null) -> Text not null:\n"
            "    value\n"
            'source User: User is postgres.table("public.users")\n'
        )
    )

    assert result.diagnostics == ()
    assert isinstance(result.model.type_symbols["User"], ShapeDef)
    assert isinstance(result.model.callable_symbols["User"], DeriveDef)
    assert isinstance(result.model.relation_symbols["User"], SourceDef)


def test_multiple_duplicates_follow_source_order() -> None:
    result = analyze(
        _parse(
            "type Shared = Int not null\n"
            "type Shared = Text not null\n"
            "derive normalize(value: Text not null) -> Text not null:\n"
            "    value\n"
            "constraint normalize(value: Text not null) -> Bool not null:\n"
            "    true\n"
            'source rows is postgres.table("rows")\n'
            "query rows:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
        ),
        mode_override=CheckMode.LOOSE,
    )

    assert [diagnostic.location.line for diagnostic in result.diagnostics] == [
        2,
        5,
        8,
    ]
    assert [diagnostic.message for diagnostic in result.diagnostics] == [
        "Duplicate symbol name in type namespace: Shared",
        "Duplicate symbol name in callable namespace: normalize",
        "Duplicate symbol name in relation namespace: rows",
    ]


def test_duplicate_diagnostic_uses_later_definition_span() -> None:
    path = Path("examples/semantic/duplicate.pie")
    script = _parse(
        "shape User:\n    id: UUID not null\nshape User:\n    email: Text not null\n",
        path=path,
    )
    duplicate = script.definitions[1]

    diagnostic = analyze(script).diagnostics[0]

    assert diagnostic.location.path == duplicate.span.path
    assert diagnostic.location.line == duplicate.span.line
    assert diagnostic.location.column == duplicate.span.column
    assert diagnostic.location.end_line == duplicate.span.end_line
    assert diagnostic.location.end_column == duplicate.span.end_column


def test_first_symbol_remains_bound_after_duplicate() -> None:
    script = _parse("type Value = Int not null\ntype Value = Text not null\n")
    first = script.definitions[0]

    result = analyze(script)

    assert result.model.type_symbols["Value"] is first


def test_forward_reference_order_does_not_affect_collection() -> None:
    result = analyze(
        _parse(
            "table active_users:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            'source users is postgres.table("public.users")\n'
        ),
        mode_override=CheckMode.LOOSE,
    )

    assert result.diagnostics == ()
    assert list(result.model.relation_symbols) == ["active_users", "users"]


def test_symbol_collection_coexists_with_valid_builtin_calls() -> None:
    result = analyze(
        _parse(
            "shape Row:\n"
            "    id: UUID not null\n"
            'source input: Row is postgres.table("input")\n'
            "table projected:\n"
            "    from input\n"
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
    assert list(result.model.relation_symbols) == ["input", "projected", "output"]


def test_semantic_symbols_and_diagnostics_do_not_expose_antlr_nodes() -> None:
    result = analyze(_parse("type Age = Int not null\ntype Age = Float not null\n"))

    _assert_no_antlr_nodes(result)


def test_symbol_collection_does_not_mutate_input_ast() -> None:
    script = _parse("type Age = Int not null\ntype Age = Float not null\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


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
