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


def test_quote_identifier_rejects_nul() -> None:
    with pytest.raises(ValueError, match="must not contain NUL"):
        quote_identifier("bad\x00name")


def test_quote_identifier_refuses_names_postgresql_would_truncate() -> None:
    # 63 UTF-8 bytes is PostgreSQL's identifier length; longer names collide.
    assert quote_identifier("a" * 63) == f'"{"a" * 63}"'
    assert quote_identifier("é" * 31 + "a") == f'"{"é" * 31}a"'
    for name, shown, size in (
        ("a" * 64, "a" * 24 + "...", 64),
        ("é" * 32, "é" * 24 + "...", 64),
        ("\x1b" + "b" * 63, "\\u001b" + "b" * 23 + "...", 64),
    ):
        # Before: the message named no identifier.
        with pytest.raises(ValueError) as refused:
            quote_identifier(name)
        assert str(refused.value) == (
            f'PostgreSQL identifier "{shown}" is {size} bytes, over the 63 bytes '
            "PostgreSQL keeps of a name"
        )


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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("path\\to\\file", "E'path\\\\to\\\\file'"),
        ("\\'; DROP TABLE users; --", "E'\\\\''; DROP TABLE users; --'"),
        ("value'; -- comment", "'value''; -- comment'"),
    ],
)
def test_render_literal_safely_escapes_string_payloads(
    value: str,
    expected: str,
) -> None:
    assert render_literal(value) == expected


def test_render_literal_rejects_nul() -> None:
    with pytest.raises(ValueError, match="must not contain NUL"):
        render_literal("bad\x00value")


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
