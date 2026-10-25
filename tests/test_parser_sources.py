from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    EnumDef,
    LiteralExpr,
    ShapeDef,
    SourceDef,
    Span,
    TypeDef,
)
from pietto.parser_api import ParseResult, parse_file, parse_source


def test_typed_and_untyped_sources_parse_connector_expressions() -> None:
    result = parse_source(
        'source users: User = postgres.table("public.users")\n'
        'source raw_events = postgres.table("public.events")\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    typed, untyped = result.ast.definitions
    assert isinstance(typed, SourceDef)
    assert typed.name == "users"
    assert typed.shape_name == "User"
    assert isinstance(typed.connector, CallExpr)
    assert isinstance(typed.connector.callee, DottedNameExpr)
    assert typed.connector.callee.parts == ("postgres", "table")
    assert len(typed.connector.arguments) == 1
    assert isinstance(typed.connector.arguments[0], LiteralExpr)
    assert typed.connector.arguments[0].value == "public.users"

    assert isinstance(untyped, SourceDef)
    assert untyped.name == "raw_events"
    assert untyped.shape_name is None
    assert isinstance(untyped.connector, CallExpr)
    assert isinstance(untyped.connector.arguments[0], LiteralExpr)
    assert untyped.connector.arguments[0].value == "public.events"


def test_source_is_parse_only_without_shape_or_connector_validation() -> None:
    result = parse_source(
        "source duplicate: MissingShape = unknown.connector(1, True)\n"
        "source duplicate = 42\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    first, second = result.ast.definitions
    assert isinstance(first, SourceDef)
    assert first.shape_name == "MissingShape"
    assert isinstance(first.connector, CallExpr)
    assert isinstance(second, SourceDef)
    assert isinstance(second.connector, LiteralExpr)
    assert second.connector.value == 42


def test_source_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "# External relation binding.\n"
        "\n"
        'source users: User = postgres.table("public.users")'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert definition.span.end_line == 3
    assert definition.span.end_column == 52


def test_source_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type UserId = UUID\n"
        "shape User:\n"
        "    id: UserId\n"
        'source users: User = postgres.table("public.users")\n'
        "enum Status:\n"
        "    ready\n"
        'source raw_events = postgres.table("public.events")\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ShapeDef,
        SourceDef,
        EnumDef,
        SourceDef,
    ]


def test_source_and_is_remain_available_in_dotted_expressions() -> None:
    result = parse_source("source registry = connector.source(row.is)\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert isinstance(definition.connector, CallExpr)
    assert isinstance(definition.connector.callee, DottedNameExpr)
    assert definition.connector.callee.parts == ("connector", "source")
    argument = definition.connector.arguments[0]
    assert isinstance(argument, DottedNameExpr)
    assert argument.parts == ("row", "is")


def test_source_spans_are_one_based_half_open() -> None:
    path = Path("examples/sources/span.pietto")
    result = parse_source(
        'source users: User = postgres.table("public.users")\n',
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=1,
        end_column=52,
    )
    assert definition.connector.span == Span(
        path=str(path),
        line=1,
        column=22,
        end_line=1,
        end_column=52,
    )
    assert isinstance(definition.connector, CallExpr)
    assert definition.connector.arguments[0].span == Span(
        path=str(path),
        line=1,
        column=37,
        end_line=1,
        end_column=51,
    )


def test_source_example_fixture_parses() -> None:
    result = parse_file("examples/sources/users.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    sources = tuple(
        definition
        for definition in result.ast.definitions
        if isinstance(definition, SourceDef)
    )
    assert [source.name for source in sources] == [
        "users",
        "raw_events",
    ]


def test_source_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source('source users: User = postgres.table("public.users")\n')

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        'source : User is postgres.table("public.users")\n',
        'source users: is postgres.table("public.users")\n',
        'source users User is postgres.table("public.users")\n',
        'source users: User postgres.table("public.users")\n',
        "source users: User =\n",
        'source users: User = postgres.table("public.users") extra\n',
        "source users:\n",
    ],
)
def test_malformed_sources_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_unclosed_connector_call_reports_the_open_parenthesis() -> None:
    result = parse_source('source users: User = postgres.table("public.users"\n')

    assert result.ast is None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-P1008", "'(' is never closed.", 1, 36)]


def test_source_rejects_old_postfix_nullability() -> None:
    result = parse_source('source users: User? is postgres.table("public.users")\n')

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_source_brace_block_reports_unsupported_brace() -> None:
    result = parse_source('source users: User = postgres.table("public.users") {\n}\n')

    assert result.ast is None
    assert _has_code(result, "PIE-P1005")


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)


def test_modern_source_binding_preserves_connector_and_spans() -> None:
    result = parse_source('source users: User = postgres.table("public.users")\n')
    assert result.diagnostics == ()
    assert result.ast is not None
    source = result.ast.definitions[0]
    assert isinstance(source, SourceDef)
    assert source.shape_name == "User"
    assert source.connector.span.column == 22


def test_modern_source_refuses_old_binding_before_ast_normalization() -> None:
    result = parse_source('source users: User is postgres.table("public.users")\n')
    assert result.ast is None
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert (diagnostic.location.line, diagnostic.location.column) == (1, 20)
    assert diagnostic.suggestion == "Bind the source with '=' instead of 'is'."


def test_modern_spelling_checks_do_not_rewrite_string_contents() -> None:
    result = parse_source(
        'source records = connector("null true nullable is") # false\n'
    )
    assert result.diagnostics == ()
    assert result.ast is not None


def test_modern_legacy_reader_retains_tree_offsets_and_old_identifier_names() -> None:
    from antlr4.tree.Tree import TerminalNodeImpl

    from pietto.generated.PiettoParser import PiettoParser
    from pietto.parser_api import _parse_migration_source

    source = 'source True is connector("null")\n'
    result, tree = _parse_migration_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == "True"
    assert tree is not None
    assert isinstance(tree, PiettoParser.ScriptContext)
    definition = tree.definition(0)
    assert definition is not None
    source_definition = definition.sourceDefinition()
    assert source_definition is not None
    keyword = source_definition.IS()
    assert isinstance(keyword, TerminalNodeImpl)
    token = keyword.getSymbol()
    assert source[token.start : token.stop + 1] == "is"


def test_modern_bare_types_are_not_null_while_the_legacy_reader_keeps_them_implicit() -> (
    None
):
    from pietto.ast_nodes import Nullability
    from pietto.parser_api import _parse_legacy_source

    source = "shape Row:\n    id: Int\n    note: Text not null\n"
    modern = parse_source(source.replace(" not null", " | None"))
    legacy = _parse_legacy_source(source.replace(" not null", " nullable"))
    for parsed, states in (
        (modern, [Nullability.NOT_NULL, Nullability.NULLABLE]),
        (legacy, [Nullability.IMPLICIT, Nullability.NULLABLE]),
    ):
        assert parsed.diagnostics == () and parsed.ast is not None
        shape = parsed.ast.definitions[0]
        assert isinstance(shape, ShapeDef)
        assert [item.type_expr.nullability for item in shape.fields] == states
    old_def = _parse_legacy_source("def f(x: Int) -> Int not null: return x\n")
    assert old_def.ast is None
    assert [
        (item.code, item.location.line, item.location.column)
        for item in old_def.diagnostics
    ] == [("PIE-P1000", 1, 10)]


def test_modern_clause_blocks_keep_colons_while_inline_clauses_omit_them() -> None:
    result = parse_source(
        "query q:\n"
        "    from rows\n"
        "    where:\n"
        "        id > 0\n"
        "        active == True\n"
        "    select id\n"
        "    having:\n"
        "        id < 100\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None


def test_modern_rewrite_diagnostics_keep_all_original_occurrences() -> None:
    result = parse_source(
        "type A = Int nullable ensure value is null\n"
        "type B = Bool ensure true or false\n"
    )
    assert result.ast is None
    assert [item.location.line for item in result.diagnostics] == [1, 1, 2, 2]
    assert [item.suggestion for item in result.diagnostics] == [
        "Declare 'type Name = T' and write 'Name | None' where a value may be None.",
        "Write 'is None' or 'is not None'.",
        "Use True.",
        "Use False.",
    ]
    # Text output prints only the message, so it states the same fix.
    assert [item.message for item in result.diagnostics] == [
        "This spelling is not accepted by the modern syntax. Declare 'type Name = T' "
        "and write 'Name | None' where a value may be None.",
        "This spelling is not accepted by the modern syntax. Write 'is None' or "
        "'is not None'.",
        "This spelling is not accepted by the modern syntax. Use True.",
        "This spelling is not accepted by the modern syntax. Use False.",
    ]


def test_modern_any_and_for_remain_contextual_identifiers_and_scalar_calls() -> None:
    from pietto.ast_nodes import CallExpr, FunctionDef, NameExpr
    from pietto.parser_api import _parse_legacy_source

    common = (
        "def any(for: Int) -> Bool:\n"
        "    return for > 0\n"
        "type Positive = Int ensure any(value)\n"
    )
    legacy = common.replace("Int)", "Int not null)").replace("Bool:", "Bool not null:")
    for parsed in (parse_source(common), _parse_legacy_source(legacy)):
        assert parsed.diagnostics == () and parsed.ast is not None
        function, definition = parsed.ast.definitions
        assert isinstance(function, FunctionDef) and function.name == "any"
        assert function.parameters[0].name == "for"
        assert isinstance(definition, TypeDef)
        call = definition.ensures[0].expression
        assert isinstance(call, CallExpr)
        assert isinstance(call.callee, NameExpr) and call.callee.name == "any"
    sources = parse_source("source for = connector(any)\nsource any = connector(for)\n")
    assert sources.diagnostics == () and sources.ast is not None
    assert [item.name for item in sources.ast.definitions] == ["for", "any"]
