"""Fixed original leaves, explicit anchors and native occurrence allocation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, localcontext
import math
from typing import Any
from uuid import UUID

from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_sql_plan_windows import ProjectSQLWindowArgument
from pietto.semantic.model import TypeKind, ValueTypeKind, EffectiveNullability

__all__: tuple[str, ...] = ()

PHYSICAL = {
    "postgres": {
        "Bool": "pg_bool",
        "Int": "pg_int8",
        "Float": "pg_float8",
        "Text": "pg_text",
    },
    "mysql": {
        "Bool": "my_signed_bool",
        "Int": "my_signed_int",
        "Float": "my_double",
        "Text": "my_utf8mb4_text",
    },
}
SQL_TYPES = {
    "pg_bool": "pg_catalog.bool",
    "pg_int8": "pg_catalog.int8",
    "pg_float8": "pg_catalog.float8",
    "pg_text": "pg_catalog.text",
    "my_signed_bool": "SIGNED",
    "my_signed_int": "SIGNED",
    "my_double": "DOUBLE",
    "my_utf8mb4_text": "CHAR CHARACTER SET utf8mb4",
}


# Header-parameter carriers no literal or slot has: PostgreSQL only. MySQL has
# none until its differential (a later MySQL catch-up), so a MySQL declaration of one of these
# types is refused before any placeholder is allocated.
HEADER_PHYSICAL = {
    "postgres": {
        "Decimal": "pg_numeric",
        "Date": "pg_date",
        "Timestamp": "pg_timestamp",
        "UUID": "pg_uuid",
    },
    "mysql": {},
}
HEADER_SQL_TYPES = {
    "pg_numeric": "pg_catalog.numeric",
    "pg_date": "pg_catalog.date",
    "pg_timestamp": "pg_catalog.timestamp",
    "pg_uuid": "pg_catalog.uuid",
}


def parameter_physical(family, tag):
    """The native carrier of a header parameter of ``tag`` (None: none)."""
    return PHYSICAL[family].get(tag) or HEADER_PHYSICAL[family].get(tag)


@dataclass(frozen=True, slots=True, eq=False)
class NativeUse:
    """One native placeholder occurrence; its owner is a slot or a parameter."""

    ordinal: int
    original: Any
    slot: Any
    physical_type: str
    server_index: int
    parameter: Any = None


@dataclass(frozen=True, slots=True, eq=False)
class SQLLiteral:
    original: Any
    site: Any
    value: bool | int | float | str


@dataclass(frozen=True, slots=True, eq=False)
class SQLNull:
    """One contextual typed NULL that never becomes a bound native value."""

    original: Any
    site: Any


@dataclass(frozen=True, slots=True, eq=False)
class SQLParameter:
    original: Any
    site: Any
    fixed: Any
    use: NativeUse


@dataclass(frozen=True, slots=True, eq=False)
class SQLAnchor:
    original: Any
    physical_type: str
    operand: SQLLiteral | SQLParameter


@dataclass(frozen=True, slots=True, eq=False)
class SQLUnary:
    original: Any
    operand: SQLAnchor | SQLUnary


@dataclass(frozen=True, slots=True, eq=False)
class LiteralOrigin:
    value: SQLNull | SQLAnchor | SQLUnary
    export: Any
    terminal: Any


def original_chain(plan, reference):
    signs = []
    seen = set()
    while reference not in seen:
        position = getattr(reference, "position", None)
        if type(position) is not int or not 0 <= position < len(plan.expressions):
            return None
        expression = plan.expressions[position]
        if expression.ref is not reference:
            return None
        seen.add(reference)
        if type(expression) is row.ProjectSQLUnary:
            if expression.expression.operator not in {"+", "-"}:
                return None
            signs.append(expression)
            reference = expression.operand
        elif type(expression) in {row.ProjectSQLLiteral, row.ProjectSQLBoundLiteral}:
            return tuple(signs), expression
        else:
            return None
    return None


def tag_of(original):
    value_type = original.value_type
    if (
        type(original) is row.ProjectSQLLiteral
        and original.expression.value is None
        and value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.nullability is EffectiveNullability.NULLABLE
    ):
        return value_type.resolved_type.name
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
        or value_type.nullability is not EffectiveNullability.NON_NULL
        or value_type.resolved_type.name not in {"Bool", "Int", "Float", "Text"}
    ):
        return None
    return value_type.resolved_type.name


def same_value(left, right):
    return type(left) is type(right) and (
        math.isfinite(left) and math.isfinite(right) and left.hex() == right.hex()
        if type(left) is float
        else left == right
    )


# Civil Timestamp bounds (language.md, Timestamp and UUID source meaning); a
# Date has the same civil interval from 1000-01-01 (Python ends at 9999-12-31).
TIMESTAMP_RANGE = (datetime(1000, 1, 1), datetime(9999, 12, 31, 23, 59, 59, 499999))
# Header parameter tags beyond the literal ones: their Python value types.
PARAMETER_VALUE_TYPES = {
    "Decimal": Decimal,
    "Date": date,
    "Timestamp": datetime,
    "UUID": UUID,
}


def value_valid(tag, value, family):
    """A value of ``tag``'s exact Python type in its domain; a Decimal is any
    finite one here, its declared precision and scale are checked by
    ``decimal_fits``."""
    if tag in PARAMETER_VALUE_TYPES:
        if type(value) is not PARAMETER_VALUE_TYPES[tag]:
            return False
        if tag == "Decimal":
            return value.is_finite()
        if tag == "Timestamp":
            low, high = TIMESTAMP_RANGE
            return value.tzinfo is None and low <= value <= high
        if tag == "Date":
            return value.year >= 1000
        return True
    if tag == "Bool":
        return type(value) is bool
    if tag == "Int":
        return type(value) is int and -(1 << 63) <= value < 1 << 63
    if tag == "Float":
        return type(value) is float and math.isfinite(value)
    if tag == "Text" and type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError:
            return False
        return family != "postgres" or "\0" not in value
    return False


def chain_problem(plan, reference, family):
    chain = original_chain(plan, reference)
    if chain is None:
        return "PIE-B1003", "scalar_expression_not_in_literal_sign_domain"
    signs, leaf = chain
    tag = tag_of(leaf)
    if tag is None or (signs and tag not in {"Int", "Float"}):
        return "PIE-B1003", "literal_type_or_sign_context_not_supported"
    if typed_null(leaf):
        if signs:
            return "PIE-B1003", "typed_null_sign_not_admitted"
        return None
    value = leaf.expression.value
    if not value_valid(tag, value, family):
        return "PIE-B1002", "literal_leaf_representation"
    for sign in reversed(signs):
        if tag_of(sign) != tag:
            return "PIE-B1002", "unary_logical_type_mismatch"
        value = -value if sign.expression.operator == "-" else +value
        if not value_valid(tag, value, family):
            return "PIE-B1002", "unary_result_representation"
    return None


def typed_null(original):
    """Recognize only the plan-retained contextual NULL image."""
    return (
        type(original) is row.ProjectSQLLiteral
        and original.expression.value is None
        and tag_of(original) is not None
    )


def allocate_uses(family, occurrences, limit):
    if (
        family not in PHYSICAL
        or type(occurrences) is not tuple
        or type(limit) is not int
        or limit < 0
        or len(occurrences) > limit
    ):
        raise ValueError("native occurrence limit or target")
    seen = {}
    result = []
    for ordinal, (item, physical) in enumerate(occurrences):
        kind = type(item)
        # A header-parameter read, in a row expression or as a window argument.
        named = kind in (row.ProjectSQLParameterRead, row.CompiledParameterRead) or (
            kind is ProjectSQLWindowArgument and item.parameter is not None
        )
        if not named and kind not in (
            row.ProjectSQLBoundLiteral,
            row.CompiledBoundLiteral,
        ):
            raise ValueError("original bound occurrence required")
        original: Any = item
        owner = original.parameter if named else original.use.slot
        if owner in seen and seen[owner][0] != physical:
            raise ValueError("incompatible_slot_context")
        if named:
            if physical != parameter_physical(family, owner.tag):
                raise ValueError("original parameter/context correspondence")
        elif (
            (tag := tag_of(original)) is None
            or physical != PHYSICAL[family].get(tag)
            or original.use.expression is not original.ref
            or owner.site.position.expression is not original.ref
            or owner.site.position.literal is not original.expression
            or owner.tag.value != tag
        ):
            raise ValueError("original slot/context correspondence")
        if family == "mysql":
            index = ordinal + 1
        elif owner in seen:
            index = seen[owner][1]
        else:
            index = len(seen) + 1
        seen[owner] = physical, index
        result.append(
            NativeUse(ordinal, original, None, physical, index, owner)
            if named
            else NativeUse(ordinal, original, owner, physical, index)
        )
    return tuple(result)


def occurrence_uses(allocated):
    """Keep the ordered allocation stream for every retained expression."""
    result: dict[Any, deque[NativeUse]] = {}
    for use in allocated:
        result.setdefault(use.original.ref, deque()).append(use)
    return result


def take_use(uses, reference):
    pending = uses.get(reference)
    return pending.popleft() if pending else None


def build_value(plan, reference, family, uses):
    chain = original_chain(plan, reference)
    assert chain is not None
    signs, original = chain
    (site,) = tuple(
        s for s in plan.literal_sites if s.position.expression is original.ref
    )
    if typed_null(original):
        assert not signs
        return SQLNull(original, site)
    if type(original) is row.ProjectSQLBoundLiteral:
        (fixed,) = tuple(
            value
            for value in plan.fixed_envelope.values
            if value.slot is original.use.slot
        )
        native = take_use(uses, original.ref)
        if native is None:
            raise ValueError("native occurrence allocation")
        leaf = SQLParameter(original, site, fixed, native)
    else:
        leaf = SQLLiteral(original, site, original.expression.value)
    tag = tag_of(original)
    assert tag is not None
    value = SQLAnchor(original, PHYSICAL[family][tag], leaf)
    for sign in reversed(signs):
        value = SQLUnary(sign, value)
    return value


def value_nodes(value):
    if type(value) is SQLNull:
        return (value,)
    result = []
    seen = set()
    while type(value) is SQLUnary:
        if id(value) in seen:
            raise ValueError("cyclic literal SQL structure")
        seen.add(id(value))
        result.append(value)
        value = value.operand
    if type(value) is not SQLAnchor or type(value.operand) not in {
        SQLLiteral,
        SQLParameter,
    }:
        raise ValueError("unknown literal SQL structure")
    return (*result, value, value.operand)


def result_value(value):
    nodes = value_nodes(value)
    leaf = nodes[-1]
    if isinstance(leaf, SQLLiteral):
        result = leaf.value
    else:
        assert isinstance(leaf, SQLParameter)
        result = leaf.fixed.value
    for sign in reversed(nodes[:-2]):
        if not isinstance(result, (int, float)) or isinstance(result, bool):
            raise ValueError("non-numeric sign operand")
        result = -result if sign.original.expression.operator == "-" else +result
    return result


def literal_token(leaf, family):
    if type(leaf) is SQLNull:
        return "NULL"
    return scalar_token(tag_of(leaf.original), leaf.value, family)


def scalar_token(tag, value, family):
    """The one fixed spelling of a non-NULL builtin scalar inside its anchor."""
    if tag == "Bool":
        return "TRUE" if value else "FALSE"
    if tag == "Int":
        return str(value)
    if tag == "Float":
        text = repr(value)
        return (
            "'" + text + "'"
            if family == "postgres"
            else (text if "e" in text else text + "e0")
        )
    if family == "postgres":
        return "E'" + "".join("\\" + format(b, "03o") for b in value.encode()) + "'"
    return "X'" + value.encode().hex() + "'"


def anchor_suffix(physical, storage=None):
    """The closing text of a CAST anchor; a Decimal header-parameter read
    passes its storage, whose precision and scale the cast names."""
    sql_type = (
        SQL_TYPES[physical] if physical in SQL_TYPES else HEADER_SQL_TYPES[physical]
    )
    if physical == "pg_numeric":
        if storage is None:
            raise ValueError("Decimal anchor carrier")
        sql_type += f"({storage['precision']},{storage['scale']})"
    suffix = " AS " + sql_type + ")"
    if physical == "pg_text":
        suffix += ' COLLATE "C"'
    elif physical == "my_utf8mb4_text":
        suffix += " COLLATE utf8mb4_0900_bin"
    return suffix


def representation(value, family):
    if type(value) is SQLNull:
        return {
            "storage": {"kind": "typed_null"},
            "nullable": True,
            "domain": {"kind": "typed_null"},
        }
    tag = tag_of(value.original)
    assert tag is not None
    return literal_representation(tag, result_value(value), family)


def literal_representation(tag, result, family):
    """The original exact literal-domain rule, without an AST or plan operand."""
    if not value_valid(tag, result, family):
        raise ValueError("literal representation requires its exact scalar domain")
    storage = PHYSICAL[family][tag]
    if tag == "Bool":
        domain = {"kind": "bool01"}
    elif tag == "Int":
        domain = {"kind": "int_range", "min": str(result), "max": str(result)}
    elif tag == "Float":
        domain = {"kind": "finite_float", "format": "binary64"}
    else:
        assert isinstance(result, str)
        domain = {
            "kind": "text",
            "max_characters": len(result),
            "encoding": "UTF8" if family == "postgres" else "utf8mb4",
            "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
            "padding": "NO PAD",
        }
    return {"storage": {"kind": storage}, "nullable": False, "domain": domain}


def wire_value(tag, value):
    if value is None:
        return None
    if tag == "Int":
        return str(value)
    if tag == "Float":
        return value.hex()
    return value


def decimal_fits(value, precision, scale):
    """A finite Decimal exactly representable as ``numeric(precision, scale)``:
    never rounded, never widened."""
    if type(value) is not Decimal or not value.is_finite():
        return False
    with localcontext() as context:
        context.prec = 66
        try:
            exact = value.quantize(Decimal(1).scaleb(-scale))
        except ArithmeticError:
            return False
    return exact == value and len(exact.as_tuple().digits) <= precision


def parameter_valid(tag, value, family, decimal=None):
    """A header value of ``tag`` on ``family``; ``decimal`` is the declared
    (precision, scale) of a Decimal parameter."""
    if not value_valid(tag, value, family):
        return False
    return tag != "Decimal" or (
        type(decimal) is tuple and decimal_fits(value, *decimal)
    )


def parameter_text(tag, value):
    """The one canonical text of a valid Decimal, Date, Timestamp or UUID
    value: the native argument the anchor casts and its typed wire payload.
    A Decimal is written without exponent or trailing zeros (``-0`` is
    ``0``), so equal values have one text."""
    if tag == "Decimal":
        with localcontext() as context:
            context.prec = 66
            normalized = value.normalize()
        return "0" if normalized == 0 else format(normalized, "f")
    if tag == "Date":
        return value.isoformat()
    if tag == "Timestamp":
        return value.isoformat(sep=" ", timespec="microseconds")
    if tag == "UUID":
        return str(value)
    raise ValueError("parameter text tag")


def parameter_value(tag, text):
    """The value of one canonical ``parameter_text``; anything else raises."""
    if type(text) is not str or len(text) > 80:
        raise ValueError("parameter text")
    if tag == "Decimal":
        value: Any = Decimal(text)
    elif tag == "Date":
        value = date.fromisoformat(text)
    elif tag == "Timestamp":
        value = datetime.fromisoformat(text)
    elif tag == "UUID":
        value = UUID(text)
    else:
        raise ValueError("parameter text tag")
    if not value_valid(tag, value, "postgres") or parameter_text(tag, value) != text:
        raise ValueError("parameter text")
    return value


def anchor_premises(request, kind, tag):
    keys = {"operator_environment"}
    if tag == "Text":
        keys.add("client_encoding")
    if kind == "parameter":
        keys.add("parameter_protocol")
    return tuple(
        p for p in request.premises if p.scope == "statement" and p.key in keys
    )
