"""The one rule for each name Pietto generates into a statement."""

from __future__ import annotations

from collections.abc import Iterable

__all__: tuple[str, ...] = ()


def generated_name(candidates: Iterable[str], used: set[str]) -> str:
    """The first candidate whose spelling no name in ``used`` has, ignoring case.

    ``used`` holds the case-folded names in use, and gains the result. MySQL
    compares column names, and table aliases under lower_case_table_names 1
    or 2, without case, so a generated name that differs from a user name only
    in case would capture it. Semantics and IR serve both dialects, so a
    PostgreSQL statement, which compares quoted names exactly, takes the same
    names.
    """

    for name in candidates:
        if name.casefold() not in used:
            used.add(name.casefold())
            return name
    raise ValueError("no candidate name is free")
