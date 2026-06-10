"""Internal PostgreSQL SQL text rendering primitives."""

from __future__ import annotations

import math


def quote_identifier(name: str) -> str:
    """Always quote one non-empty PostgreSQL identifier."""

    if not name:
        raise ValueError("PostgreSQL identifiers must not be empty")
    if "\x00" in name:
        raise ValueError("PostgreSQL identifiers must not contain NUL")
    return f'"{name.replace('"', '""')}"'


def quote_qualified_identifier(parts: tuple[str, ...] | list[str]) -> str:
    """Quote and join a non-empty sequence of PostgreSQL identifier parts."""

    if not parts:
        raise ValueError("Qualified PostgreSQL identifiers must not be empty")
    return ".".join(quote_identifier(part) for part in parts)


def render_literal(value: object) -> str:
    """Render one supported scalar as a PostgreSQL SQL literal."""

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("PostgreSQL float literals must be finite")
        return repr(value)
    if isinstance(value, str):
        if "\x00" in value:
            raise ValueError("PostgreSQL string literals must not contain NUL")
        escaped = value.replace("'", "''")
        if "\\" in value:
            escaped = escaped.replace("\\", "\\\\")
            return f"E'{escaped}'"
        return f"'{escaped}'"
    raise TypeError(f"Unsupported PostgreSQL literal type: {type(value).__name__}")
