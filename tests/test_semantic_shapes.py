from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Node, Script, ShapeDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze


def test_distinct_shape_item_names_have_no_duplicate_diagnostic() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    check valid_email:\n"
            "        email is not null\n"
            "    unique user_email on email\n"
            "    index email_idx on email when email is not null\n"
        )
    )

    assert result.diagnostics == ()


def test_duplicate_field_name_reports_p2501() -> None:
    result = analyze(
        _parse("shape User:\n    email: Text not null\n    email: Text nullable\n")
    )

    assert _diagnostics(result, "PIE-S2501") == [
        (
            Severity.ERROR,
            "Duplicate shape item name in shape User: email",
        )
    ]


@pytest.mark.parametrize(
    "conflicting_item",
    [
        "    check email:\n        true\n",
        "    unique email on email\n",
        "    index email on email\n",
    ],
)
def test_field_name_conflicts_with_other_shape_item_kinds(
    conflicting_item: str,
) -> None:
    result = analyze(
        _parse(f"shape User:\n    email: Text not null\n{conflicting_item}")
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2501"]
    assert result.diagnostics[0].message == (
        "Duplicate shape item name in shape User: email"
    )


@pytest.mark.parametrize(
    "items",
    [
        ("    check valid:\n        true\n    check valid:\n        false\n"),
        ("    unique identity on email\n    unique identity on email\n"),
        ("    index lookup on email\n    index lookup on email\n"),
    ],
)
def test_duplicate_check_unique_and_index_names_report_p2501(items: str) -> None:
    result = analyze(_parse(f"shape User:\n    email: Text not null\n{items}"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2501"]


def test_unique_target_existing_field_succeeds() -> None:
    result = analyze(
        _parse(
            "shape User:\n    email: Text not null\n    unique user_email on email\n"
        )
    )

    assert result.diagnostics == ()


def test_unique_unknown_target_reports_p2502() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    unique user_email on missing_email\n"
        )
    )

    assert _diagnostics(result, "PIE-S2502") == [
        (
            Severity.ERROR,
            "Unknown target field in shape User: missing_email",
        )
    ]


def test_index_target_existing_field_succeeds() -> None:
    result = analyze(
        _parse(
            "shape User:\n    email: Text not null\n    index user_email_idx on email\n"
        )
    )

    assert result.diagnostics == ()


def test_index_unknown_target_reports_p2502() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    index user_email_idx on missing_email\n"
        )
    )

    assert _diagnostics(result, "PIE-S2502") == [
        (
            Severity.ERROR,
            "Unknown target field in shape User: missing_email",
        )
    ]


@pytest.mark.parametrize(
    ("item", "message"),
    [
        (
            "unique user_email on email, email",
            "Duplicate target field in unique user_email: email",
        ),
        (
            "index user_email_idx on email, email",
            "Duplicate target field in index user_email_idx: email",
        ),
    ],
)
def test_repeated_target_field_reports_p2503(item: str, message: str) -> None:
    result = analyze(_parse(f"shape User:\n    email: Text not null\n    {item}\n"))

    assert _diagnostics(result, "PIE-S2503") == [(Severity.ERROR, message)]


def test_shape_diagnostics_use_later_or_containing_item_spans() -> None:
    path = Path("examples/semantic/shape-errors.pie")
    script = _parse(
        "shape User:\n"
        "    email: Text not null\n"
        "    email: Text nullable\n"
        "    unique missing_unique on missing\n"
        "    index repeated_index on email, email\n",
        path=path,
    )
    shape = script.definitions[0]
    assert isinstance(shape, ShapeDef)
    duplicate_field, missing_unique, repeated_index = shape.items[1:]

    diagnostics = analyze(script).diagnostics

    assert [diagnostic.code for diagnostic in diagnostics] == [
        "PIE-S2501",
        "PIE-S2502",
        "PIE-S2503",
    ]
    _assert_location_matches(diagnostics[0], duplicate_field)
    _assert_location_matches(diagnostics[1], missing_unique)
    _assert_location_matches(diagnostics[2], repeated_index)


def test_shape_checks_continue_after_diagnostics() -> None:
    result = analyze(
        _parse(
            "shape First:\n"
            "    id: UUID not null\n"
            "    unique missing_target on missing\n"
            "shape Second:\n"
            "    id: UUID not null\n"
            "    index repeated_target on id, id\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code) for diagnostic in result.diagnostics
    ] == [(3, "PIE-S2502"), (6, "PIE-S2503")]


def test_field_derive_unknown_function_reports_pie_s2103() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    normalized: Text not null derive unknown_call(email)\n"
            "    check unchecked:\n"
            "        email is not null\n"
            "    index partial_idx on email when email is not null\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2103", "Unknown function: unknown_call")]


def test_shape_structural_checks_do_not_mutate_input_ast() -> None:
    script = _parse(
        "shape User:\n    email: Text not null\n    unique user_email on missing\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_shape_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    unique user_email on missing\n"
            "    index repeated on email, email\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _diagnostics(
    result: SemanticResult,
    code: str,
) -> list[tuple[Severity, str]]:
    return [
        (diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.code == code
    ]


def _assert_location_matches(diagnostic: Diagnostic, node: Node) -> None:
    location = diagnostic.location
    span = node.span
    assert location.path == span.path
    assert location.line == span.line
    assert location.column == span.column
    assert location.end_line == span.end_line
    assert location.end_column == span.end_column


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
