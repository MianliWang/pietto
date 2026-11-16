"""Internal SQLite SQL text rendering primitives."""

from __future__ import annotations

import math

_INT64_MAX = 9_223_372_036_854_775_807


class SqliteRenderError(Exception):
    """Expected fail-closed rejection from the private SQLite renderer."""


def quote_identifier(name: str, *, context: str = "identifier") -> str:
    """Validate and backtick-quote one SQLite identifier.

    SQLite reads a double-quoted identifier that names no column as a string
    literal; a backtick-quoted one stays an identifier, so a missing column
    fails the statement instead.
    """

    _validate_text(name, context=context)
    if not name:
        raise SqliteRenderError(f"SQLite {context} must not be empty")
    return f"`{name.replace('`', '``')}`"


def render_literal(value: object) -> str:
    """Render one unsigned Int, Float, Bool or Text literal for SQLite."""

    if isinstance(value, bool):
        # SQLite reads TRUE and FALSE as a column or output alias so named.
        return "1" if value else "0"
    if isinstance(value, int):
        # unreachable from source (PIE-S2364; a sign is arithmetic); guards other IR
        if not 0 <= value <= _INT64_MAX:
            raise SqliteRenderError("SQLite Int literal is outside 0 to 2**63 - 1")
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value) or math.copysign(1.0, value) < 0:
            raise SqliteRenderError("SQLite Float literal must be finite and unsigned")
        return repr(value)
    if isinstance(value, str):
        _validate_text(value, context="string literal")
        return "'" + value.replace("'", "''") + "'"
    if value is None:
        raise SqliteRenderError("SQLite single-file SQL has no None literal yet")
    raise SqliteRenderError(f"Unsupported SQLite literal type: {type(value).__name__}")


def _validate_text(value: str, *, context: str) -> None:
    if "\x00" in value:
        raise SqliteRenderError(f"SQLite {context} must not contain NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise SqliteRenderError(f"SQLite {context} must be valid UTF-8 text") from error
