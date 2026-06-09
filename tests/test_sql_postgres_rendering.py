from __future__ import annotations

import inspect
import math

import pytest

import pietto.sql as sql_api
import pietto.sql.render as render_module
from pietto.sql.render import (
    quote_identifier,
    quote_qualified_identifier,
    render_literal,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("users", '"users"'),
        ("UserProfile", '"UserProfile"'),
        ("order", '"order"'),
        ('weird"name', '"weird""name"'),
        ("daily users", '"daily users"'),
    ],
)
def test_quote_identifier_always_quotes_and_preserves_spelling(
    name: str,
    expected: str,
) -> None:
    assert quote_identifier(name) == expected


def test_quote_identifier_rejects_empty_name() -> None:
    with pytest.raises(ValueError):
        quote_identifier("")


def test_quote_qualified_identifier_quotes_each_part() -> None:
    assert quote_qualified_identifier(("public", "users")) == '"public"."users"'
    assert quote_qualified_identifier(["analytics", "daily users"]) == (
        '"analytics"."daily users"'
    )


@pytest.mark.parametrize("parts", [(), [], ("public", ""), ["", "users"]])
def test_quote_qualified_identifier_rejects_empty_parts(
    parts: tuple[str, ...] | list[str],
) -> None:
    with pytest.raises(ValueError):
        quote_qualified_identifier(parts)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "NULL"),
        (True, "TRUE"),
        (False, "FALSE"),
        (42, "42"),
        (-7, "-7"),
        (1.5, "1.5"),
        (-0.0, "-0.0"),
        ("Alice", "'Alice'"),
        ("O'Reilly", "'O''Reilly'"),
    ],
)
def test_render_literal_supports_current_scalar_subset(
    value: object,
    expected: str,
) -> None:
    assert render_literal(value) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_render_literal_rejects_non_finite_float(value: float) -> None:
    with pytest.raises(ValueError):
        render_literal(value)


@pytest.mark.parametrize("value", [b"bytes", object(), [1]])
def test_render_literal_rejects_unsupported_types(value: object) -> None:
    with pytest.raises(TypeError):
        render_literal(value)


def test_render_helpers_remain_internal_and_dependency_free() -> None:
    source = inspect.getsource(render_module)

    assert "quote_identifier" not in sql_api.__all__
    assert "quote_qualified_identifier" not in sql_api.__all__
    assert "render_literal" not in sql_api.__all__
    for dependency in (
        "antlr",
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir",
        "sqlglot",
        "database",
        "connector",
        "pietto.cli",
    ):
        assert dependency not in source
