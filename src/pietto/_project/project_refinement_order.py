"""Structural occurrence coordinates and explicit target NULL/direction laws."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pietto._project.project_refinement_rendering import (
    Expr,
    conjunction,
    disjunction,
    null_equal,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Coordinate:
    address: tuple
    tag: str
    nullable: bool
    domain: tuple = field(repr=False)
    storage: tuple = (("kind", "signed64"),)
    # Each (index, value) is an enclosing branch/presence condition. Inactive
    # storage must be NULL, even when its original scalar was non-null.
    active: tuple[tuple[int, int], ...] = ()


def scalar_coordinate(address, realization, *, nullable=None):
    if realization.tag not in ("Int", "Bool", "Text", "Decimal"):
        raise ValueError("REFINEMENT_COMPARISON_DOMAIN")
    return Coordinate(
        address,
        realization.tag,
        realization.nullable is not False if nullable is None else nullable,
        tuple(sorted(realization.domain.items())),
        tuple(sorted(realization.storage.items())),
    )


def integer_coordinate(address, lower=-(1 << 63), upper=(1 << 63) - 1):
    return Coordinate(
        address,
        "Int",
        False,
        (("kind", "int_range"), ("max", str(upper)), ("min", str(lower))),
    )


def null_first(family, direction):
    if family not in ("postgres", "mysql") or direction not in ("asc", "desc"):
        raise ValueError("REFINEMENT_ORDER_POLICY")
    return (family == "mysql") == (direction == "asc")


def before(left, right, directions, family):
    """Strict lexicographic order with explicit NULL equality and placement."""
    if len(left) != len(right) or len(left) != len(directions) or not left:
        raise ValueError("REFINEMENT_ORDER_ARITY")
    alternatives = []
    prefix = []
    for a, b, direction in zip(left, right, directions, strict=True):
        lower_null = (a, b) if null_first(family, direction) else (b, a)
        strict = disjunction(
            conjunction(
                Expr("is_null", (lower_null[0],)), Expr("is_not_null", (lower_null[1],))
            ),
            conjunction(
                Expr("is_not_null", (a,)),
                Expr("is_not_null", (b,)),
                Expr("<" if direction == "asc" else ">", (a, b)),
            ),
        )
        alternatives.append(conjunction(*prefix, strict))
        prefix.append(null_equal(a, b))
    return disjunction(*alternatives)


def equality(left, right):
    if len(left) != len(right):
        raise ValueError("REFINEMENT_EQUALITY_ARITY")
    return conjunction(*(null_equal(a, b) for a, b in zip(left, right, strict=True)))


def check_value(value, coordinate):
    if value is None:
        if not coordinate.nullable:
            raise ValueError("REFINEMENT_NULL_COORDINATE")
        return None
    tag, domain = coordinate.tag, dict(coordinate.domain)
    if tag == "Int":
        valid = type(value) is int and int(domain["min"]) <= value <= int(domain["max"])
    elif tag == "Bool":
        valid = type(value) is bool or type(value) is int and value in (0, 1)
        if valid:
            value = bool(value)
    elif tag == "Text":
        valid = type(value) is str
        if valid:
            value.encode("utf-8")
            maximum = domain.get("max_characters")
            valid = maximum is None or len(value) <= int(maximum)
    elif tag == "Decimal":
        valid = type(value) is Decimal and value.is_finite()
        if valid:
            _sign, digits, exponent = value.as_tuple()
            scale = int(domain["scale"])
            precision = int(domain["precision"])
            # Test exponent/digit lengths before powers or large integer
            # conversion. A tiny hostile Decimal exponent must not allocate an
            # unbounded coefficient during page-control validation.
            shift = int(exponent) + scale
            if not any(digits):
                valid = True
            elif shift < 0:
                removed = -shift
                valid = removed < len(digits) and not any(digits[-removed:])
                valid = valid and len(digits) - removed <= precision
            else:
                valid = len(digits) + shift <= precision
    else:
        valid = False
    if not valid:
        raise ValueError("REFINEMENT_COORDINATE_DOMAIN")
    return value


def check_coordinates(values, coordinates):
    if type(values) is not tuple or len(values) != len(coordinates):
        raise ValueError("REFINEMENT_COORDINATE_ARITY")
    accepted: list[Any] = []
    for value, coordinate in zip(values, coordinates, strict=True):
        if type(coordinate) is not Coordinate:
            raise ValueError("REFINEMENT_COORDINATE_TYPE")
        if any(
            type(i) is not int
            or not 0 <= i < len(accepted)
            or type(expected) is not int
            for i, expected in coordinate.active
        ):
            raise ValueError("REFINEMENT_COORDINATE_DEPENDENCY")
        active = all(accepted[i] == expected for i, expected in coordinate.active)
        if not active:
            if value is not None:
                raise ValueError("REFINEMENT_INACTIVE_COORDINATE")
            accepted.append(None)
        else:
            accepted.append(check_value(value, coordinate))
    return tuple(accepted)


def compare(left, right, coordinates, directions, family):
    """Compare already typed components; never compare a Python tuple or hash."""
    left = check_coordinates(left, coordinates)
    right = check_coordinates(right, coordinates)
    if len(directions) != len(coordinates):
        raise ValueError("REFINEMENT_ORDER_ARITY")
    for a, b, coordinate, direction in zip(
        left, right, coordinates, directions, strict=True
    ):
        first = null_first(family, direction)
        if a is None or b is None:
            if a is b:
                continue
            return -1 if (a is None) == first else 1
        if coordinate.tag == "Text":
            # Original admitted C / utf8mb4_0900_bin NO PAD comparisons are
            # exact UTF-8/codepoint order; no normalization or trimming.
            a, b = a.encode("utf-8"), b.encode("utf-8")
        if a == b:
            continue
        result = -1 if a < b else 1
        return result if direction == "asc" else -result
    return 0
