"""Internal MySQL SQL text rendering primitives."""

from __future__ import annotations

import math

MYSQL_IDENTIFIER_MAX_CHARACTERS = 64
MYSQL_ALIAS_MAX_CHARACTERS = 256


class MySqlRenderError(Exception):
    """Expected fail-closed rejection from the private MySQL renderer."""


def quote_identifier(
    name: str,
    *,
    max_characters: int = MYSQL_IDENTIFIER_MAX_CHARACTERS,
    context: str = "identifier",
) -> str:
    """Validate and backtick-quote one MySQL identifier."""

    _validate_text(name, context=context)
    if not name:
        raise MySqlRenderError(f"MySQL {context} must not be empty")
    if len(name) > max_characters:
        raise MySqlRenderError(
            f"MySQL {context} must not exceed {max_characters} characters"
        )
    return f"`{name.replace('`', '``')}`"


def quote_qualified_identifier(parts: tuple[str, ...] | list[str]) -> str:
    """Quote each logical component of one qualified field reference."""

    if not parts:
        raise MySqlRenderError("Qualified MySQL identifiers must not be empty")
    return ".".join(
        quote_identifier(part, context="identifier component") for part in parts
    )


def render_literal(value: object) -> str:
    """Render one scalar under the accepted MySQL 8.0 literal contract."""

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise MySqlRenderError("MySQL float literals must be finite")
        return repr(value)
    if isinstance(value, str):
        return _render_text_literal(value)
    raise MySqlRenderError(f"Unsupported MySQL literal type: {type(value).__name__}")


def _render_text_literal(value: str) -> str:
    _validate_text(value, context="string literal")
    escaped: list[str] = []
    for character in value:
        if character == "'":
            escaped.append("''")
        elif character == "\\":
            escaped.append("\\\\")
        elif character == "\b":
            escaped.append("\\b")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif character == "\t":
            escaped.append("\\t")
        elif character == "\x1a":
            escaped.append("\\Z")
        else:
            escaped.append(character)
    return "'" + "".join(escaped) + "'"


def _validate_text(value: str, *, context: str) -> None:
    if "\x00" in value:
        raise MySqlRenderError(f"MySQL {context} must not contain NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise MySqlRenderError(f"MySQL {context} must be valid UTF-8 text") from error
