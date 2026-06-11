from __future__ import annotations

import inspect
import math

import pytest

import pietto.sql as sql_api
import pietto.sql.mysql_render as render_module
from pietto.sql.mysql_render import (
    MYSQL_ALIAS_MAX_CHARACTERS,
    MYSQL_IDENTIFIER_MAX_CHARACTERS,
    MySqlRenderError,
    quote_identifier,
    quote_qualified_identifier,
    render_literal,
)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("users", "`users`"),
        ("UserProfile", "`UserProfile`"),
        ("order", "`order`"),
        ("weird`name", "`weird``name`"),
        ("daily users", "`daily users`"),
        ("app.users", "`app.users`"),
    ],
)
def test_quote_identifier_uses_backticks_and_preserves_spelling(
    name: str,
    expected: str,
) -> None:
    assert quote_identifier(name) == expected


@pytest.mark.parametrize("name", ["", "bad\x00name", "x" * 65, "\ud800"])
def test_quote_identifier_rejects_invalid_values(name: str) -> None:
    with pytest.raises(MySqlRenderError):
        quote_identifier(name)


def test_alias_limit_is_separate_from_identifier_limit() -> None:
    alias = "a" * MYSQL_ALIAS_MAX_CHARACTERS

    assert MYSQL_IDENTIFIER_MAX_CHARACTERS == 64
    assert (
        quote_identifier(
            alias,
            max_characters=MYSQL_ALIAS_MAX_CHARACTERS,
            context="select-list alias",
        )
        == f"`{alias}`"
    )
    with pytest.raises(MySqlRenderError, match="256"):
        quote_identifier(
            alias + "a",
            max_characters=MYSQL_ALIAS_MAX_CHARACTERS,
            context="select-list alias",
        )


def test_quote_qualified_identifier_quotes_each_logical_component() -> None:
    assert quote_qualified_identifier(("app", "users", "email")) == (
        "`app`.`users`.`email`"
    )


@pytest.mark.parametrize("parts", [(), [], ("app", ""), ["", "users"]])
def test_quote_qualified_identifier_rejects_empty_parts(
    parts: tuple[str, ...] | list[str],
) -> None:
    with pytest.raises(MySqlRenderError):
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
        ("你好", "'你好'"),
    ],
)
def test_render_literal_supports_approved_scalar_values(
    value: object,
    expected: str,
) -> None:
    assert render_literal(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("path\\to\\file", "'path\\\\to\\\\file'"),
        ("\\n", "'\\\\n'"),
        ("\b\n\r\t\x1a", "'\\b\\n\\r\\t\\Z'"),
        ("\\'; --", "'\\\\''; --'"),
    ],
)
def test_render_literal_uses_canonical_mysql_escapes(
    value: str,
    expected: str,
) -> None:
    assert render_literal(value) == expected


@pytest.mark.parametrize("value", ["bad\x00value", "\ud800"])
def test_render_literal_rejects_invalid_text(value: str) -> None:
    with pytest.raises(MySqlRenderError):
        render_literal(value)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_render_literal_rejects_non_finite_float(value: float) -> None:
    with pytest.raises(MySqlRenderError):
        render_literal(value)


@pytest.mark.parametrize("value", [b"bytes", object(), [1]])
def test_render_literal_rejects_unknown_types(value: object) -> None:
    with pytest.raises(MySqlRenderError):
        render_literal(value)


def test_mysql_render_helpers_remain_private_and_dependency_free() -> None:
    source = inspect.getsource(render_module)

    for name in (
        "quote_identifier",
        "quote_qualified_identifier",
        "render_literal",
    ):
        assert name not in sql_api.__all__
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
