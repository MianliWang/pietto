"""Pure guards for recovered raw-prep observations; no DB or runtime access."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def require_exact_keys(record: Mapping[str, Any], keys: Sequence[str]) -> None:
    """Reject a partial or widened captured record before a later campaign."""
    expected = tuple(keys)
    actual = tuple(record)
    if actual != expected:
        raise ValueError(f"record keys must be {expected!r}, got {actual!r}")


def require_finite_float(value: object) -> float:
    """Accept finite binary64 inputs while preserving Python's signed zero."""
    if type(value) is not float or value != value or value in (float("inf"), float("-inf")):
        raise ValueError("expected finite float")
    return value


def require_collection_state(record: Mapping[str, Any]) -> None:
    """Keep absent, empty, and present collection states non-interchangeable."""
    require_exact_keys(record, ("present", "count", "children"))
    present, count, children = record["present"], record["count"], record["children"]
    if type(present) is not bool or (count is not None and type(count) is not int):
        raise ValueError("invalid collection header")
    if not isinstance(children, tuple):
        raise ValueError("children must retain occurrence order as a tuple")
    if not present and (count is not None or children):
        raise ValueError("absent container must not become empty or present")
    if present and (count is None or count != len(children) or count < 0):
        raise ValueError("present collection count mismatch")


def require_ordered_occurrences(values: Sequence[object], ordinals: Sequence[int]) -> None:
    """Guard the frozen positional witness; do not sort or deduplicate it."""
    if len(values) != len(ordinals) or any(type(item) is not int for item in ordinals):
        raise ValueError("invalid ordered occurrence witness")
    if tuple(ordinals) != tuple(range(len(ordinals))):
        raise ValueError("ordinals must retain source occurrence order")
