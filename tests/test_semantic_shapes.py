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
            "    email: Text\n"
            "    valid_email = check(email is not None)\n"
            "    user_email = unique(email)\n"
            "    email_idx = index(email) when email is not None\n"
        )
    )

    assert result.diagnostics == ()


def test_duplicate_field_name_reports_p2501() -> None:
    result = analyze(_parse("shape User:\n    email: Text\n    email: Text | None\n"))

    assert _diagnostics(result, "PIE-S2501") == [
        (
            Severity.ERROR,
            "Duplicate shape item name in shape User: email",
        )
    ]


@pytest.mark.parametrize(
    "conflicting_item",
    [
        "    email = check(True)\n",
        "    email = unique(email)\n",
        "    email = index(email)\n",
    ],
)
def test_field_name_conflicts_with_other_shape_item_kinds(
    conflicting_item: str,
) -> None:
    result = analyze(_parse(f"shape User:\n    email: Text\n{conflicting_item}"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2501"]
    assert result.diagnostics[0].message == (
        "Duplicate shape item name in shape User: email"
    )


@pytest.mark.parametrize(
    "items",
    [
        ("    valid = check(True)\n    valid = check(False)\n"),
        ("    identity = unique(email)\n    identity = unique(email)\n"),
        ("    lookup = index(email)\n    lookup = index(email)\n"),
    ],
)
def test_duplicate_check_unique_and_index_names_report_p2501(items: str) -> None:
    result = analyze(_parse(f"shape User:\n    email: Text\n{items}"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2501"]


def test_unique_target_existing_field_succeeds() -> None:
    result = analyze(
        _parse("shape User:\n    email: Text\n    user_email = unique(email)\n")
    )

    assert result.diagnostics == ()


def test_unique_unknown_target_reports_p2502() -> None:
    result = analyze(
        _parse("shape User:\n    email: Text\n    user_email = unique(missing_email)\n")
    )

    assert _diagnostics(result, "PIE-S2502") == [
        (
            Severity.ERROR,
            "Unknown target field in shape User: missing_email",
        )
    ]


def test_index_target_existing_field_succeeds() -> None:
    result = analyze(
        _parse("shape User:\n    email: Text\n    user_email_idx = index(email)\n")
    )

    assert result.diagnostics == ()


def test_index_unknown_target_reports_p2502() -> None:
    result = analyze(
        _parse(
            "shape User:\n    email: Text\n    user_email_idx = index(missing_email)\n"
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
            "user_email = unique(email, email)",
            "Duplicate target field in unique user_email: email",
        ),
        (
            "user_email_idx = index(email, email)",
            "Duplicate target field in index user_email_idx: email",
        ),
    ],
)
def test_repeated_target_field_reports_p2503(item: str, message: str) -> None:
    result = analyze(_parse(f"shape User:\n    email: Text\n    {item}\n"))

    assert _diagnostics(result, "PIE-S2503") == [(Severity.ERROR, message)]


def test_shape_diagnostics_use_later_or_containing_item_spans() -> None:
    path = Path("examples/semantic/shape-errors.pietto")
    script = _parse(
        "shape User:\n"
        "    email: Text\n"
        "    email: Text | None\n"
        "    missing_unique = unique(missing)\n"
        "    repeated_index = index(email, email)\n",
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
            "    id: UUID\n"
            "    missing_target = unique(missing)\n"
            "shape Second:\n"
            "    id: UUID\n"
            "    repeated_target = index(id, id)\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code) for diagnostic in result.diagnostics
    ] == [(3, "PIE-S2502"), (6, "PIE-S2503")]


def test_field_derive_unknown_function_reports_pie_s2103() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text\n"
            "    normalized: Text derive unknown_call(email)\n"
            "    unchecked = check(email is not None)\n"
            "    partial_idx = index(email) when email is not None\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2103", "Unknown function: unknown_call")]


def test_shape_structural_checks_do_not_mutate_input_ast() -> None:
    script = _parse("shape User:\n    email: Text\n    user_email = unique(missing)\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_shape_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text\n"
            "    user_email = unique(missing)\n"
            "    repeated = index(email, email)\n"
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


@pytest.mark.parametrize(
    ("item", "expected"),
    (
        (
            "k = unique(id, id)",
            ("PIE-S2503", "Duplicate target field in unique k: id", 3),
        ),
        (
            "i = index(id, id)",
            ("PIE-S2503", "Duplicate target field in index i: id", 3),
        ),
        (
            "k = unique(nosuch)",
            ("PIE-S2502", "Unknown target field in shape C: nosuch", 3),
        ),
        (
            "k = unique(id)\n    k = unique(id)",
            ("PIE-S2501", "Duplicate shape item name in shape C: k", 4),
        ),
    ),
)
def test_project_check_reports_the_single_file_shape_item_diagnostics(
    tmp_path: Path, item: str, expected: tuple[str, str, int]
) -> None:
    from _pietto_project_join import _completed

    result = _completed(
        tmp_path,
        f"shape C:\n    id: Int\n    {item}\n"
        'source cs: C = postgres.table("cs")\n'
        "query q:\n    from cs\n    select:\n        id\n",
    )

    assert not result.ok
    assert [(d.code, d.message, d.location.line) for d in result.diagnostics] == [
        expected
    ]


def test_project_check_orders_shape_item_diagnostics_by_module(tmp_path: Path) -> None:
    from pietto._project.check import check_project_parse_only
    from pietto._project.model import build_empty_project_semantic_result
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
    )

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (tmp_path / "a.pietto").write_text(
        "shape A:\n    id: Int\n    k = unique(nosuch)\n"
        'source as_: A = postgres.table("as_")\n'
        "relationship r(x: A, y: Nowhere): x.id == y.id\n"
        "query qa:\n    from as_\n    select:\n        id\n"
    )
    (tmp_path / "b.pietto").write_text(
        "shape B:\n    id: Int\n    i = index(id, id)\n"
        'source bs: B = postgres.table("bs")\n'
        "query qb:\n    from bs\n    select:\n        missing\n"
    )
    parsed = check_project_parse_only(tmp_path)
    assert parsed.ok, parsed.diagnostics
    result = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )

    # After the semantic analysis diagnostics, per module in selected-module
    # order, and before the relationship declaration diagnostics.
    assert [(d.location.path, d.location.line, d.code) for d in result.diagnostics][
        :4
    ] == [
        ("b.pietto", 8, "PIE-S2102"),
        ("a.pietto", 3, "PIE-S2502"),
        ("b.pietto", 3, "PIE-S2503"),
        ("a.pietto", 5, "PIE-S2604"),
    ]
