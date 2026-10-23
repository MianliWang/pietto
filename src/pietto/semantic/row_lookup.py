"""Field lookups over a relation's input row, the one rule for every clause.

A joined row (``RowSchema.joined``) is the input row of a single-file JOIN
relation: one field per field of each visible binding, keyed
``"<binding>.<field>"``. Every other row is keyed by field name, and over it
each helper is exactly the lookup it replaces.

Private: nothing here is exported.
"""

from __future__ import annotations

from pietto.semantic.model import RowField, RowSchema

__all__ = ()


def bare_candidates(schema: RowSchema, name: str) -> tuple[RowField, ...]:
    """The fields a bare ``name`` can read, in row order."""

    if not schema.joined:
        field = schema.fields.get(name)
        return () if field is None else (field,)
    return tuple(
        field for key, field in schema.fields.items() if key.partition(".")[2] == name
    )


def bare_field(schema: RowSchema, name: str) -> RowField | None:
    """The one field a bare ``name`` reads; None when none or several match."""

    if not schema.joined:
        return schema.fields.get(name)
    candidates = bare_candidates(schema, name)
    return candidates[0] if len(candidates) == 1 else None


def has_bare_field(schema: RowSchema, name: str) -> bool:
    """Whether a bare ``name`` names a field, an ambiguous one included."""

    if not schema.joined:
        return name in schema.fields
    return bool(bare_candidates(schema, name))


def qualified_field(
    schema: RowSchema, parts: tuple[str, ...], qualifier: str
) -> RowField | None:
    """The field a two-part read ``parts`` names.

    Over a joined row the first part is a binding, and an empty ``qualifier``
    admits no qualified read; over any other row the first part must be
    ``qualifier``, the name of the sole input.
    """

    if len(parts) != 2:
        return None
    if not schema.joined:
        return schema.fields.get(parts[1]) if parts[0] == qualifier else None
    if qualifier == "":
        return None
    return schema.fields.get(f"{parts[0]}.{parts[1]}")
