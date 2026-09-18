"""Fixed original leaves, explicit anchors and native occurrence allocation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from pietto._project import project_sql_plan_expressions as row
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


@dataclass(frozen=True, slots=True, eq=False)
class NativeUse:
    ordinal: int
    original: Any
    slot: Any
    physical_type: str
    server_index: int


@dataclass(frozen=True, slots=True, eq=False)
class SQLLiteral:
    original: Any
    site: Any
    value: bool | int | float | str


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
    value: SQLAnchor | SQLUnary
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


def value_valid(tag, value, family):
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
    for ordinal, (original, physical) in enumerate(occurrences):
        if type(original) is not row.ProjectSQLBoundLiteral:
            raise ValueError("original bound occurrence required")
        slot = original.use.slot
        tag = tag_of(original)
        if slot in seen and seen[slot][0] != physical:
            raise ValueError("incompatible_slot_context")
        if (
            tag is None
            or physical != PHYSICAL[family].get(tag)
            or original.use.expression is not original.ref
            or slot.site.position.expression is not original.ref
            or slot.site.position.literal is not original.expression
            or slot.tag.value != tag_of(original)
        ):
            raise ValueError("original slot/context correspondence")
        if family == "mysql":
            index = ordinal + 1
        elif slot in seen:
            index = seen[slot][1]
        else:
            index = len(seen) + 1
        seen[slot] = physical, index
        result.append(NativeUse(ordinal, original, slot, physical, index))
    return tuple(result)


def build_value(plan, reference, family, uses):
    chain = original_chain(plan, reference)
    assert chain is not None
    signs, original = chain
    (site,) = tuple(
        s for s in plan.literal_sites if s.position.expression is original.ref
    )
    if type(original) is row.ProjectSQLBoundLiteral:
        (fixed,) = tuple(
            value
            for value in plan.fixed_envelope.values
            if value.slot is original.use.slot
        )
        leaf = SQLParameter(original, site, fixed, uses[original.ref])
    else:
        leaf = SQLLiteral(original, site, original.expression.value)
    tag = tag_of(original)
    assert tag is not None
    value = SQLAnchor(original, PHYSICAL[family][tag], leaf)
    for sign in reversed(signs):
        value = SQLUnary(sign, value)
    return value


def value_nodes(value):
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
    value = leaf.value
    tag = tag_of(leaf.original)
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


def anchor_suffix(physical):
    suffix = " AS " + SQL_TYPES[physical] + ")"
    if physical == "pg_text":
        suffix += ' COLLATE "C"'
    elif physical == "my_utf8mb4_text":
        suffix += " COLLATE utf8mb4_0900_bin"
    return suffix


def representation(value, family):
    tag = tag_of(value.original)
    assert tag is not None
    result = result_value(value)
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
    if tag == "Int":
        return str(value)
    if tag == "Float":
        return value.hex()
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
