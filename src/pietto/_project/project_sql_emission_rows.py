"""Admitted row expressions, stage bodies and finite target range realization."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project.model import ProjectResolvedTypeKind
from pietto.semantic.model import TypeKind, ValueTypeKind, EffectiveNullability
from pietto.ir.model import SymbolNamespace

__all__: tuple[str, ...] = ()

ARITHMETIC = ("+", "-", "*")
LOGICAL = ("and", "or")
COMPARISONS = {
    "==": " = ",
    "!=": " <> ",
    "<": " < ",
    "<=": " <= ",
    ">": " > ",
    ">=": " >= ",
    "like": " LIKE ",
    "not like": " NOT LIKE ",
}
COMPARABLE = ("Int", "Text", "Decimal")
# SQL IN is only emitted for carriers with an established equality operation.
# Other same-canonical semantic values (for example Json or Bytes) stay at the
# project boundary until their physical equality proof is reviewed.
MEMBERSHIP_TYPES = ("Bool", "Int", "Float", "Decimal", "Text", "Timestamp", "UUID")
INT_WIDTHS = {
    "pg_int2": 16,
    "pg_int4": 32,
    "pg_int8": 64,
    "my_smallint": 16,
    "my_int": 32,
    "my_bigint": 64,
    "my_signed_int": 64,
}
BOOL_RESULT = {"postgres": "pg_bool", "mysql": "my_signed_bool"}
NULLABILITY = {
    EffectiveNullability.NON_NULL: False,
    EffectiveNullability.NULLABLE: True,
    EffectiveNullability.UNKNOWN: "unknown",
}


@dataclass(frozen=True, slots=True, eq=False)
class Realization:
    """One value's checked logical tag, physical storage and exact value domain.

    ``binding`` marks a value whose exact domain is fixed only when its query
    parameters are bound; the template keeps the declared carrier (the full
    signed range for Int, an unknown width for Text). ``obligation`` names the
    check this node defers to every binding.
    """

    tag: str
    storage: dict[str, Any]
    nullable: bool | str
    domain: dict[str, Any]
    proven_int_range: tuple[int, int] | None = None
    binding: bool = False
    obligation: str | None = None


INT_RANGE_OBLIGATION = "int_range_representable"
TEXT_WIDTH_OBLIGATION = "text_result_width"
TEXT_PROFILE = {
    "postgres": ("UTF8", "C", "NO PAD"),
    "mysql": ("utf8mb4", "utf8mb4_0900_bin", "NO PAD"),
}


@dataclass(frozen=True, slots=True, eq=False)
class SQLParameterRead:
    """One header-parameter read rendered as a typed native placeholder."""

    original: Any
    use: Any
    physical_type: str
    realization: Realization


def parameter_realization(
    family: str, tag: str, nullable: bool, *, bound: bool = False, value=None
) -> Realization:
    """One read's image: the declared carrier for the unbound template, or the
    exact domain of a bound value. NULL has no value, so any domain holds; the
    narrowest one (Int 0..0, Text width 0) keeps every downstream law exact."""
    storage = {"kind": parameters.PHYSICAL[family][tag]}
    if bound and tag in ("Int", "Text"):
        if value is not None and not parameters.value_valid(tag, value, family):
            raise ValueError("query parameter value")
        if tag == "Int":
            exact = 0 if value is None else value
            return Realization(
                tag,
                storage,
                nullable,
                {"kind": "int_range", "min": str(exact), "max": str(exact)},
                (exact, exact),
            )
        encoding, collation, padding = TEXT_PROFILE[family]
        return Realization(
            tag,
            storage,
            nullable,
            {
                "kind": "text",
                "max_characters": 0 if value is None else len(value),
                "encoding": encoding,
                "collation": collation,
                "padding": padding,
            },
        )
    if tag == "Bool":
        return Realization(tag, storage, nullable, {"kind": "bool01"})
    if tag == "Float":
        return Realization(
            tag, storage, nullable, {"kind": "finite_float", "format": "binary64"}
        )
    if tag == "Int":
        low, high = -(1 << 63), (1 << 63) - 1
        return Realization(
            tag,
            storage,
            nullable,
            {"kind": "int_range", "min": str(low), "max": str(high)},
            (low, high),
            binding=True,
        )
    if tag != "Text":
        raise ValueError("query parameter type")
    encoding, collation, padding = TEXT_PROFILE[family]
    return Realization(
        tag,
        storage,
        nullable,
        {
            "kind": "text",
            "max_characters": None,
            "encoding": encoding,
            "collation": collation,
            "padding": padding,
        },
        binding=True,
    )


def deferred_int(storage: dict[str, Any] | None, nullable) -> Realization | None:
    """An Int result whose range is proved only at binding, within its carrier."""
    if storage is None:
        return None
    limits = signed_range(storage)
    if limits is None:
        return None
    low, high = limits
    return Realization(
        "Int",
        storage,
        nullable,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
        binding=True,
        obligation=INT_RANGE_OBLIGATION,
    )


@dataclass(frozen=True, slots=True, eq=False)
class StageColumn:
    """A scan column an expression may read, with its terminal and retained origin."""

    position: int
    name: str
    terminal: Any
    realization: Realization
    field: Any = None
    source_port: Any = None
    literal: Any = None
    scope: Any = None
    aggregate: Any = None
    """One grouped determinant or aggregate result this value ultimately is."""
    window: Any = None
    """One window occurrence result this value ultimately is."""


@dataclass(frozen=True, slots=True, eq=False)
class SQLStageReference:
    original: Any
    port: Any
    column: StageColumn
    realization: Realization
    scope: Any = None
    """The relation alias this reference reads, when its body has more than one."""


@dataclass(frozen=True, slots=True, eq=False)
class SQLOperation:
    original: Any
    kind: str
    operands: tuple[Any, ...]
    realization: Realization


def signed_range(storage) -> tuple[int, int] | None:
    bits = INT_WIDTHS.get(storage["kind"])
    if bits is None:
        return None
    return -(1 << (bits - 1)), (1 << (bits - 1)) - 1


def int_bounds(realization: Realization) -> tuple[int, int] | None:
    domain = realization.domain
    if realization.tag != "Int" or domain.get("kind") != "int_range":
        return None
    return int(domain["min"]), int(domain["max"])


def proven_int_bounds(realization: Realization) -> tuple[int, int] | None:
    if realization.tag != "Int" or realization.proven_int_range is None:
        return None
    low, high = realization.proven_int_range
    if type(low) is not int or type(high) is not int or low > high:
        return None
    return low, high


def source_realization(realization: Realization) -> Realization | None:
    """Keep result-domain requirements; source Int proof is its signed carrier."""
    if realization.tag != "Int":
        return realization
    bounds = signed_range(realization.storage)
    if bounds is None:
        return None
    return Realization(
        realization.tag,
        realization.storage,
        realization.nullable,
        realization.domain,
        bounds,
    )


def value_tag(expression) -> str | None:
    """Read the retained logical builtin name; never infer one."""
    value_type = expression.value_type
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    return value_type.resolved_type.name


def value_nullable(expression) -> bool | str | None:
    return NULLABILITY.get(expression.value_type.nullability)


def field_realization(field) -> Realization | None:
    """The physical realization the accepted contract already fixed for one field."""
    value = json.loads(field.representation)
    logical = field.field.evidence.resolved_type
    if logical.kind is not ProjectResolvedTypeKind.BUILTIN:
        return None
    return source_realization(
        Realization(logical.name, value["storage"], value["nullable"], value["domain"])
    )


def constant_realization(value, family: str) -> Realization:
    if type(value) is parameters.SQLNull:
        value_type = value.original.value_type
        if (
            value_type.kind is not ValueTypeKind.KNOWN
            or value_type.resolved_type.kind is not TypeKind.BUILTIN
            or value_type.nullability is not EffectiveNullability.NULLABLE
        ):
            raise ValueError("compiled typed NULL requires a known nullable builtin")
        return Realization(
            value_type.resolved_type.name,
            {"kind": "typed_null"},
            True,
            {"kind": "typed_null"},
        )
    described = parameters.representation(value, family)
    tag = parameters.tag_of(value.original)
    assert tag is not None
    result = parameters.result_value(value)
    return Realization(
        tag,
        described["storage"],
        described["nullable"],
        described["domain"],
        (result, result) if tag == "Int" and type(result) is int else None,
    )


def _arithmetic_storage(family: str, left: Realization, right: Realization):
    """The target's own documented signed integer result type; never a blanket CAST."""
    if family == "mysql":
        return {"kind": "my_signed_int"}
    left_bits = INT_WIDTHS.get(left.storage["kind"])
    right_bits = INT_WIDTHS.get(right.storage["kind"])
    if left_bits is None or right_bits is None:
        return None
    return {16: {"kind": "pg_int2"}, 32: {"kind": "pg_int4"}, 64: {"kind": "pg_int8"}}[
        max(left_bits, right_bits)
    ]


def _interval(operator: str, left: tuple[int, int], right: tuple[int, int]):
    if operator == "+":
        return left[0] + right[0], left[1] + right[1]
    if operator == "-":
        return left[0] - right[1], left[1] - right[0]
    products = [a * b for a in left for b in right]
    return min(products), max(products)


def _text_domain(realization: Realization):
    return tuple(
        realization.domain.get(key) for key in ("encoding", "collation", "padding")
    )


def _decimal_domain(realization: Realization):
    return tuple(realization.domain.get(key) for key in ("precision", "scale"))


def _typed_null(realization: Realization) -> bool:
    return (
        realization.nullable is True
        and realization.storage == {"kind": "typed_null"}
        and realization.domain == {"kind": "typed_null"}
    )


def _concrete_values(values):
    """Return one established carrier, while retaining typed NULL's tag check."""
    concrete = tuple(value for value in values if not _typed_null(value))
    if not concrete:
        return None
    first = concrete[0]
    if any(value.tag != first.tag for value in values):
        return None
    return first


def _membership_carrier_matches(first: Realization, value: Realization) -> bool:
    if _typed_null(value):
        return value.tag == first.tag
    if value.tag != first.tag:
        return False
    if first.tag == "Int":
        return (
            first.storage.get("kind") in INT_WIDTHS
            and value.storage.get("kind") in INT_WIDTHS
            and int_bounds(first) is not None
            and int_bounds(value) is not None
        )
    if first.tag == "Text":
        return (
            _text_result(
                "postgres", first, first.nullable, first.domain.get("max_characters")
            )
            is not None
            and _text_result(
                "postgres", value, value.nullable, value.domain.get("max_characters")
            )
            is not None
            and _text_domain(first) == _text_domain(value)
        ) or (
            _text_result(
                "mysql", first, first.nullable, first.domain.get("max_characters")
            )
            is not None
            and _text_result(
                "mysql", value, value.nullable, value.domain.get("max_characters")
            )
            is not None
            and _text_domain(first) == _text_domain(value)
        )
    if first.tag == "Decimal":
        return first.storage == value.storage and _decimal_domain(
            first
        ) == _decimal_domain(value)
    if first.tag == "Bool":
        return first.domain == value.domain == {"kind": "bool01"} and (
            first.storage == value.storage == {"kind": "pg_bool"}
            or first.storage
            in (
                {"kind": "my_bool01"},
                {"kind": "my_signed_bool"},
            )
            and value.storage
            in (
                {"kind": "my_bool01"},
                {"kind": "my_signed_bool"},
            )
        )
    if first.tag == "Float":
        return first.storage == value.storage and first.domain == value.domain == {
            "kind": "finite_float",
            "format": "binary64",
        }
    return first.storage == value.storage and first.domain == value.domain


def _text_result(family, value, nullable, maximum):
    """Preserve the one admitted text profile with an explicit result bound."""
    expected = (
        ("UTF8", "C", "NO PAD")
        if family == "postgres"
        else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
    )
    domain = value.domain
    if value.binding and maximum is None:
        return _binding_text_result(family, value, nullable, expected)
    if (
        value.tag != "Text"
        or type(maximum) is not int
        or maximum < 0
        or set(domain) != {"kind", "max_characters", "encoding", "collation", "padding"}
        or domain["kind"] != "text"
        or type(domain["max_characters"]) is not int
        or domain["max_characters"] < 0
        or _text_domain(value) != expected
    ):
        return None
    if family == "postgres":
        if value.storage != {"kind": "pg_text"}:
            return None
        storage = {"kind": "pg_text"}
    elif family == "mysql":
        if maximum > 16383 or not (
            value.storage == {"kind": "my_utf8mb4_text"}
            or (
                value.storage.get("kind") == "my_varchar"
                and set(value.storage) == {"kind", "length"}
                and type(value.storage["length"]) is int
                and domain["max_characters"] <= value.storage["length"] <= 16383
            )
        ):
            return None
        storage = {"kind": "my_varchar", "length": maximum}
    else:
        return None
    return Realization(
        "Text",
        storage,
        nullable,
        {
            "kind": "text",
            "max_characters": maximum,
            "encoding": expected[0],
            "collation": expected[1],
            "padding": expected[2],
        },
    )


def _binding_text_result(family, value, nullable, expected):
    """A Text result whose width each binding fixes and checks (MySQL caps it)."""
    domain = value.domain
    if (
        value.tag != "Text"
        or set(domain) != {"kind", "max_characters", "encoding", "collation", "padding"}
        or domain["kind"] != "text"
        or domain["max_characters"] is not None
        or _text_domain(value) != expected
        or value.storage
        not in (
            ({"kind": "pg_text"},)
            if family == "postgres"
            else (
                {"kind": "my_utf8mb4_text"},
                {"kind": "my_varchar", "length": None},
            )
        )
    ):
        return None
    return Realization(
        "Text",
        {"kind": "pg_text"}
        if family == "postgres"
        else {"kind": "my_varchar", "length": None},
        nullable,
        dict(domain),
        binding=True,
        obligation=TEXT_WIDTH_OBLIGATION,
    )


def _text_carrier_result(family, values, nullable, maximum=None):
    """Keep one Text profile while deriving an explicitly bounded result carrier."""
    carrier = _concrete_values(values)
    if carrier is None or carrier.tag != "Text":
        return None
    if maximum is None and any(value.binding for value in values):
        # A binding fixes the width; every branch keeps the one Text profile.
        if any(
            not _typed_null(value)
            and (
                _text_domain(value) != _text_domain(carrier)
                or _text_result(
                    family,
                    value,
                    value.nullable,
                    None if value.binding else value.domain.get("max_characters"),
                )
                is None
            )
            for value in values
        ):
            return None
        return _binding_text_result(
            family,
            next(value for value in values if value.binding),
            nullable,
            TEXT_PROFILE.get(family),
        )
    widths = []
    for value in values:
        if _typed_null(value):
            if value.tag != "Text":
                return None
            continue
        width = value.domain.get("max_characters")
        if (
            value.tag != "Text"
            or _text_domain(value) != _text_domain(carrier)
            or _text_result(family, value, value.nullable, width) is None
        ):
            return None
        widths.append(width)
    if not widths:
        return None
    result_width = max(widths) if maximum is None else maximum
    return _text_result(family, carrier, nullable, result_width)


def _int_carrier_result(family, values, nullable, preserve_input=False):
    """Join proved signed ranges without selecting a cross-target storage family."""
    carrier = _concrete_values(values)
    kinds = {
        "postgres": {"pg_int2", "pg_int4", "pg_int8"},
        "mysql": {"my_smallint", "my_int", "my_bigint", "my_signed_int"},
    }.get(family)
    if carrier is None or carrier.tag != "Int" or kinds is None:
        return None
    bounds = []
    for value in values:
        if _typed_null(value):
            if value.tag != "Int":
                return None
            continue
        current = proven_int_bounds(value)
        if (
            value.tag != "Int"
            or set(value.storage) != {"kind"}
            or value.storage["kind"] not in kinds
            or current is None
        ):
            return None
        bounds.append((value, current))
    if not bounds:
        return None
    binding = any(value.binding for value in values)
    if preserve_input and not _typed_null(values[0]):
        value, _ = bounds[0]
        return Realization(
            "Int",
            value.storage,
            nullable,
            value.domain,
            value.proven_int_range,
            binding=binding,
        )
    low = min(current[0] for _, current in bounds)
    high = max(current[1] for _, current in bounds)
    storage = (
        {"kind": "my_signed_int"}
        if family == "mysql"
        else {
            16: {"kind": "pg_int2"},
            32: {"kind": "pg_int4"},
            64: {"kind": "pg_int8"},
        }[max(INT_WIDTHS[value.storage["kind"]] for value, _ in bounds)]
    )
    checked = _checked_int(storage, low, high, nullable)
    return None if checked is None else replace(checked, binding=binding)


def _bool_carrier_result(family, values, nullable, preserve_input=False):
    """Admit only the selected target's Bool source and literal carriers."""
    carrier = _concrete_values(values)
    allowed = (
        ({"kind": "pg_bool"},)
        if family == "postgres"
        else ({"kind": "my_bool01"}, {"kind": "my_signed_bool"})
        if family == "mysql"
        else ()
    )
    if carrier is None or carrier.tag != "Bool" or not allowed:
        return None
    for value in values:
        if _typed_null(value):
            if value.tag != "Bool":
                return None
            continue
        if (
            value.tag != "Bool"
            or value.storage not in allowed
            or value.domain != {"kind": "bool01"}
        ):
            return None
    if preserve_input and not _typed_null(values[0]):
        return Realization("Bool", values[0].storage, nullable, values[0].domain)
    return _bool(family, nullable)


CHILD_FIELDS = {
    row.ProjectSQLUnary: ("operand",),
    row.ProjectSQLBinary: ("left", "right"),
    row.ProjectSQLComparison: ("left", "right"),
    row.ProjectSQLIsNull: ("value",),
    row.ProjectSQLBetween: ("value", "lower", "upper"),
    row.ProjectSQLConditional: ("when_true", "condition", "when_false"),
    row.ProjectSQLMembership: ("value", "options"),
    row.ProjectSQLCast: ("value",),
}


def rendered_operand_order(kind, count):
    if kind == "conditional" and count == 3:
        return (1, 0, 2)
    return tuple(range(count))


def tree_nodes(plan, reference):
    """Preorder original nodes of one authored tree, following its operand links."""
    return _tree_nodes(plan, reference, render_order=False)


def rendered_tree_nodes(plan, reference):
    """Preorder original nodes in the order the SQL renderer visits them."""
    return _tree_nodes(plan, reference, render_order=True)


def _tree_nodes(plan, reference, *, render_order):
    result = []
    pending = [reference]
    seen = set()
    while pending:
        current = pending.pop()
        position = getattr(current, "position", None)
        if type(position) is not int or not 0 <= position < len(plan.expressions):
            raise ValueError("expression reference outside the current plan")
        expression = plan.expressions[position]
        if expression.ref is not current or id(current) in seen:
            raise ValueError("expression reference identity or cycle")
        seen.add(id(current))
        result.append(expression)
        if type(expression) is row.ProjectSQLScalarCall:
            pending.extend(reversed(expression.arguments))
        elif type(expression) is row.ProjectSQLMembership:
            pending.extend(reversed(expression.options))
            pending.append(expression.value)
        else:
            fields = CHILD_FIELDS.get(type(expression), ())
            children = tuple(getattr(expression, name) for name in fields)
            if render_order:
                children = tuple(
                    children[i]
                    for i in rendered_operand_order(
                        "conditional"
                        if type(expression) is row.ProjectSQLConditional
                        else "",
                        len(children),
                    )
                )
            pending.extend(reversed(children))
    return tuple(result)


def rendered_constant_chains(plan, reference):
    """Every maximal literal/sign chain in SQL rendering order."""
    return _constant_chains(rendered_tree_nodes(plan, reference), plan)


def _constant_chains(expressions, plan):
    result = []
    covered = set()
    for expression in expressions:
        if expression.ref in covered:
            continue
        chain = parameters.original_chain(plan, expression.ref)
        if chain is None:
            continue
        signs, leaf = chain
        covered.update(sign.ref for sign in signs)
        covered.add(leaf.ref)
        result.append((expression.ref, leaf))
    return tuple(result)


type ReferenceNode = (
    type[row.ProjectSQLReference]
    | type[row.ProjectSQLJoinedReference]
    | type[row.ProjectSQLMatchReference]
    | type[aggregation.ProjectSQLResultReference]
    | type[plan_windows.ProjectSQLWindowReference]
)


def build_row_value(
    request,
    columns,
    reference,
    uses,
    *,
    reference_type: ReferenceNode = row.ProjectSQLReference,
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    """Realize one admitted tree; return (value, None) or (None, (code, detail))."""
    plan = request.plan
    family = request.family
    position = getattr(reference, "position", None)
    if type(position) is not int or not 0 <= position < len(plan.expressions):
        return None, ("PIE-B1008", "expression_reference_outside_plan")
    expression = plan.expressions[position]
    if expression.ref is not reference:
        return None, ("PIE-B1008", "expression_reference_identity")
    chain = parameters.original_chain(plan, reference)
    if chain is not None:
        problem = parameters.chain_problem(plan, reference, family)
        if problem is not None:
            return None, problem
        return parameters.build_value(plan, reference, family, uses), None
    if type(expression) is row.ProjectSQLParameterRead:
        use = uses.get(expression.ref)
        if use is None or use.parameter is not expression.parameter:
            return None, ("PIE-B1008", "native_occurrence_allocation")
        nullable = value_nullable(expression)
        if type(nullable) is not bool:
            return None, ("PIE-B1004", "expression_logical_type_evidence_missing")
        return (
            SQLParameterRead(
                expression,
                use,
                use.physical_type,
                parameter_realization(family, expression.parameter.tag, nullable),
            ),
            None,
        )
    tag, nullable = value_tag(expression), value_nullable(expression)
    if tag is None or nullable is None:
        return None, ("PIE-B1004", "expression_logical_type_evidence_missing")
    if (
        type(expression) is reference_type
        or type(expression) is plan_windows.ProjectSQLWindowReference
    ):
        # A QUALIFY reference is always a read of an established window result
        # port, whatever reference kind the surrounding stage uses.
        column = columns.get(expression.port)
        if column is None:
            return None, ("PIE-B1001", "reference_outside_stage_scope")
        if column.realization.tag != tag or column.realization.nullable != nullable:
            return None, ("PIE-B1002", "reference_logical_type_or_null_drift")
        return (
            SQLStageReference(
                expression,
                expression.port,
                column,
                column.realization,
                getattr(column, "scope", None),
            ),
            None,
        )
    if type(expression) in {
        row.ProjectSQLReference,
        row.ProjectSQLJoinedReference,
        row.ProjectSQLMatchReference,
        aggregation.ProjectSQLResultReference,
        plan_windows.ProjectSQLWindowReference,
    }:
        return None, ("PIE-B1001", "reference_outside_its_admitted_scope")
    if type(expression) is row.ProjectSQLUnary:
        if expression.expression.operator == "not":
            operand, problem = build_row_value(
                request,
                columns,
                expression.operand,
                uses,
                reference_type=reference_type,
            )
            if problem is not None:
                return None, problem
            inner = realization_of(operand, family)
            if (
                tag != "Bool"
                or inner.tag != "Bool"
                or inner.domain.get("kind") != "bool01"
            ):
                return None, ("PIE-B1003", "unary_not_requires_bool_operand")
            return SQLOperation(
                expression, "not", (operand,), _bool(family, nullable)
            ), None
        if expression.expression.operator not in {"+", "-"}:
            return None, ("PIE-B1003", "unary_operator_not_admitted")
        operand, problem = build_row_value(
            request, columns, expression.operand, uses, reference_type=reference_type
        )
        if problem is not None:
            return None, problem
        inner = realization_of(operand, family)
        if tag != "Int" or inner.tag != "Int":
            return None, ("PIE-B1003", "unary_sign_requires_int_operand")
        bounds = proven_int_bounds(inner)
        if bounds is None:
            return None, ("PIE-B1004", "int_range_proof_missing")
        low, high = (
            (-bounds[1], -bounds[0])
            if (expression.expression.operator == "-")
            else bounds
        )
        storage = _arithmetic_storage(family, inner, inner)
        checked = _checked_int(storage, low, high, nullable)
        if checked is None and inner.binding:
            checked = deferred_int(storage, nullable)
        elif checked is not None:
            checked = replace(checked, binding=inner.binding)
        if checked is None:
            return None, ("PIE-B1002", "unary_result_outside_physical_range")
        return SQLOperation(expression, "sign", (operand,), checked), None
    if type(expression) is row.ProjectSQLIsNull:
        operand, problem = build_row_value(
            request, columns, expression.value, uses, reference_type=reference_type
        )
        if problem is not None:
            return None, problem
        if tag != "Bool" or nullable is not False:
            return None, ("PIE-B1002", "null_test_result_not_non_null_bool")
        return (
            SQLOperation(expression, "null_test", (operand,), _bool(family, nullable)),
            None,
        )
    if type(expression) is row.ProjectSQLBinary:
        return _binary(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLComparison:
        return _comparison(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLBetween:
        return _between(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLScalarCall:
        return _scalar_call(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLConditional:
        return _conditional(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLMembership:
        return _membership(
            request, columns, expression, tag, nullable, uses, reference_type
        )
    if type(expression) is row.ProjectSQLCast:
        return _cast(request, columns, expression, tag, nullable, uses, reference_type)
    return None, ("PIE-B1003", "row_expression_not_admitted_in_slice6")


def _bool(family: str, nullable: bool | str) -> Realization:
    return Realization(
        "Bool", {"kind": BOOL_RESULT[family]}, nullable, {"kind": "bool01"}
    )


def _checked_int(storage, low, high, nullable) -> Realization | None:
    if storage is None:
        return None
    limits = signed_range(storage)
    if limits is None or low < limits[0] or high > limits[1]:
        return None
    return Realization(
        "Int",
        storage,
        nullable,
        {"kind": "int_range", "min": str(low), "max": str(high)},
        (low, high),
    )


def _decimal_parameters(family: str, value: Realization) -> tuple[int, int] | None:
    """Read one qualified Decimal carrier; no target default selects a result."""

    expected = "pg_numeric" if family == "postgres" else "my_decimal"
    storage, domain = value.storage, value.domain
    if value.tag != "Decimal" or storage.get("kind") != expected:
        return None
    precision, scale = storage.get("precision"), storage.get("scale")
    if (
        type(precision) is not int
        or type(scale) is not int
        or not 0 <= scale <= precision <= 65
        or domain != {"kind": "decimal", "precision": precision, "scale": scale}
    ):
        return None
    return precision, scale


def _float_literal_value(value) -> float | None:
    """Return one exact finite Float literal/sign value, never a field value."""

    try:
        nodes = parameters.value_nodes(value)
        leaf = nodes[-1]
        if (
            type(leaf) not in {parameters.SQLLiteral, parameters.SQLParameter}
            or parameters.tag_of(leaf.original) != "Float"
        ):
            return None
        result = parameters.result_value(value)
    except (AttributeError, IndexError, TypeError, ValueError):
        return None
    return result if type(result) is float and math.isfinite(result) else None


def _operands(
    request, columns, refs, uses, reference_type
) -> tuple[tuple[Any, ...], None] | tuple[None, tuple[str, str]]:
    values = []
    for reference in refs:
        value, problem = build_row_value(
            request, columns, reference, uses, reference_type=reference_type
        )
        if value is None:
            assert problem is not None
            return None, problem
        values.append(value)
    return tuple(values), None


def _binary(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    operator = expression.expression.operator
    if operator not in (*ARITHMETIC, *LOGICAL):
        return None, ("PIE-B1003", "binary_operator_not_admitted")
    values, problem = _operands(
        request, columns, (expression.left, expression.right), uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    left, right = (realization_of(value, request.family) for value in values)
    float_left, float_right = (_float_literal_value(value) for value in values)
    checked, problem = resolved_binary_realization(
        request.family,
        operator,
        tag,
        nullable,
        left,
        right,
        direct_decimal_sources=all(
            type(value) is SQLStageReference
            and value.column.field is not None
            and value.column.source_port is not None
            for value in values
        ),
        float_values=(
            None
            if float_left is None or float_right is None
            else (float_left, float_right)
        ),
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(
        expression, "logical" if operator in LOGICAL else "arithmetic", values, checked
    ), None


def resolved_binary_realization(
    family,
    operator,
    tag,
    nullable,
    left,
    right,
    *,
    direct_decimal_sources: bool = False,
    float_values: tuple[float, float] | None = None,
):
    """Original range/domain law over resolved operands; no name resolution."""
    if operator in LOGICAL:
        if tag != "Bool" or left.tag != "Bool" or right.tag != "Bool":
            return None, ("PIE-B1003", "logical_operands_require_bool")
        if left.domain.get("kind") != "bool01" or right.domain.get("kind") != "bool01":
            return None, ("PIE-B1002", "logical_operand_outside_bool_domain")
        return _bool(family, nullable), None
    if operator not in ARITHMETIC:
        return None, ("PIE-B1003", "binary_operator_not_admitted")
    if tag == left.tag == right.tag == "Decimal":
        if not direct_decimal_sources:
            return None, ("PIE-B1003", "decimal_direct_source_operands_required")
        left_parameters = _decimal_parameters(family, left)
        right_parameters = _decimal_parameters(family, right)
        if left_parameters is None or right_parameters is None:
            return None, ("PIE-B1004", "decimal_source_carrier_missing")
        left_precision, left_scale = left_parameters
        right_precision, right_scale = right_parameters
        if operator in {"+", "-"}:
            if left_scale != right_scale:
                return None, ("PIE-B1003", "decimal_scale_mismatch")
            scale = left_scale
            precision = (
                max(left_precision - left_scale, right_precision - right_scale)
                + 1
                + scale
            )
        else:
            scale = left_scale + right_scale
            precision = left_precision + right_precision
        if precision > 65 or scale > 30:
            return None, ("PIE-B1002", "decimal_result_outside_physical_range")
        storage = {
            "kind": "pg_numeric" if family == "postgres" else "my_decimal",
            "precision": precision,
            "scale": scale,
        }
        return (
            Realization(
                "Decimal",
                storage,
                nullable,
                {"kind": "decimal", "precision": precision, "scale": scale},
            ),
            None,
        )
    if tag == left.tag == right.tag == "Float":
        if float_values is None:
            return None, ("PIE-B1003", "float_literal_operands_required")
        left_value, right_value = float_values
        result = {
            "+": left_value + right_value,
            "-": left_value - right_value,
            "*": left_value * right_value,
        }[operator]
        if not math.isfinite(result):
            return None, ("PIE-B1002", "float_result_not_finite")
        return (
            Realization(
                "Float",
                {"kind": "pg_float8" if family == "postgres" else "my_double"},
                nullable,
                {"kind": "finite_float", "format": "binary64"},
            ),
            None,
        )
    if tag != "Int" or left.tag != "Int" or right.tag != "Int":
        return None, ("PIE-B1003", "arithmetic_requires_signed_int_operands")
    left_bounds, right_bounds = proven_int_bounds(left), proven_int_bounds(right)
    if left_bounds is None or right_bounds is None:
        return None, ("PIE-B1004", "int_range_proof_missing")
    low, high = _interval(operator, left_bounds, right_bounds)
    storage = _arithmetic_storage(family, left, right)
    binding = left.binding or right.binding
    checked = _checked_int(storage, low, high, nullable)
    if checked is None and binding:
        checked = deferred_int(storage, nullable)
    elif checked is not None:
        checked = replace(checked, binding=binding)
    if checked is None:
        return None, ("PIE-B1002", "arithmetic_outside_physical_range")
    return checked, None


def _comparison(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    operator = expression.expression.operator
    if operator not in COMPARISONS:
        return None, ("PIE-B1003", "comparison_operator_not_admitted")
    values, problem = _operands(
        request, columns, (expression.left, expression.right), uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    left, right = (realization_of(value, request.family) for value in values)
    if operator in {"like", "not like"}:
        checked, problem = resolved_like_realization(
            request.family, tag, nullable, left, right
        )
    else:
        checked, problem = resolved_comparison_realization(
            request.family, tag, nullable, left, right, operator
        )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "comparison", values, checked), None


def _between(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    values, problem = _operands(
        request,
        columns,
        (expression.value, expression.lower, expression.upper),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_between_realization(
        request.family, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "between", values, checked), None


def resolved_comparison_realization(
    family, tag, nullable, left, right, operator: str | None = None
):
    """Original comparison-domain law over already resolved physical inputs."""
    if tag != "Bool":
        return None, ("PIE-B1002", "comparison_result_not_bool")
    if left.tag != right.tag:
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag in {"Timestamp", "UUID"}:
        if (
            operator not in {"==", "!="}
            or left.storage != right.storage
            or left.domain != right.domain
        ):
            return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
        return _bool(family, nullable), None
    if left.tag not in COMPARABLE:
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag == "Text" and _text_domain(left) != _text_domain(right):
        return None, ("PIE-B1005", "text_comparison_domain_conflict")
    if left.tag == "Decimal" and (
        _decimal_domain(left) != _decimal_domain(right)
        or None in _decimal_domain(left)
        or left.storage != right.storage
    ):
        return None, ("PIE-B1005", "decimal_comparison_parameter_conflict")
    return _bool(family, nullable), None


def resolved_like_realization(family, tag, nullable, left, right):
    if (
        tag != "Bool"
        or left.tag != "Text"
        or right.tag != "Text"
        or _text_domain(left) != _text_domain(right)
    ):
        return None, ("PIE-B1003", "like_text_domain_not_admitted")
    return _bool(family, nullable), None


def resolved_between_realization(family, tag, nullable, values):
    """The comparison-domain law applied to each ordered BETWEEN operand."""
    if len(values) != 3:
        return None, ("PIE-B1008", "between_operand_arity")
    first, lower, upper = values
    if first.tag not in COMPARABLE or any(
        value.tag != first.tag for value in (lower, upper)
    ):
        return None, ("PIE-B1003", "between_type_pair_not_admitted")
    for bound in (lower, upper):
        checked, problem = resolved_comparison_realization(
            family, tag, nullable, first, bound
        )
        if checked is None:
            return None, problem
    return _bool(family, nullable), None


def _scalar_call(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    values, problem = _operands(
        request, columns, expression.arguments, uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_scalar_call_realization(
        request.family, expression.callee_symbol, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "scalar_call", values, checked), None


def _conditional(request, columns, expression, tag, nullable, uses, reference_type):
    values, problem = _operands(
        request,
        columns,
        (expression.when_true, expression.condition, expression.when_false),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_conditional_realization(
        request.family, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "conditional", values, checked), None


def resolved_conditional_realization(family, tag, nullable, values):
    if len(values) != 3:
        return None, ("PIE-B1008", "conditional_operand_arity")
    when_true, condition, when_false = values
    carrier = _concrete_values((when_true, when_false))
    if (
        condition.tag != "Bool"
        or condition.domain.get("kind") != "bool01"
        or carrier is None
        or carrier.tag != tag
    ):
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Text":
        result = _text_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Int":
        result = _int_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag == "Bool":
        result = _bool_carrier_result(family, (when_true, when_false), nullable)
        if result is not None:
            return result, None
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if tag not in {"Decimal", "Float", "Timestamp", "UUID"}:
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    if any(
        branch.tag != carrier.tag
        or (
            not _typed_null(branch)
            and (branch.storage != carrier.storage or branch.domain != carrier.domain)
        )
        for branch in (when_true, when_false)
    ):
        return None, ("PIE-B1003", "conditional_realization_not_admitted")
    return Realization(tag, carrier.storage, nullable, carrier.domain), None


def _membership(request, columns, expression, tag, nullable, uses, reference_type):
    values, problem = _operands(
        request,
        columns,
        (expression.value, *expression.options),
        uses,
        reference_type,
    )
    if values is None:
        assert problem is not None
        return None, problem
    realized = tuple(realization_of(value, request.family) for value in values)
    checked, problem = resolved_membership_realization(
        request.family, tag, nullable, realized
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "membership", values, checked), None


def resolved_membership_realization(family, tag, nullable, values):
    if not values or tag != "Bool":
        return None, ("PIE-B1003", "membership_realization_not_admitted")
    first = _concrete_values(values)
    if first is None:
        return None, ("PIE-B1004", "membership_typed_null_context_missing")
    if first.tag not in MEMBERSHIP_TYPES:
        return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    if len(values) == 1:
        # The semantic layer has already checked the left operand.  The empty
        # list is a target-independent Boolean constant, even for NULL lhs.
        if nullable is not False:
            return None, ("PIE-B1002", "empty_membership_not_non_null_bool")
        return _bool(family, False), None
    for option in values[1:]:
        # Membership is the adopted same-canonical-type operation.  Requiring
        # the exact checked carrier preserves that contract without silently
        # narrowing it to the older comparison subset.
        if not _membership_carrier_matches(first, option):
            return None, ("PIE-B1003", "membership_type_pair_not_admitted")
    return _bool(family, nullable), None


def _cast(request, columns, expression, tag, nullable, uses, reference_type):
    value, problem = build_row_value(
        request, columns, expression.value, uses, reference_type=reference_type
    )
    if problem is not None:
        return None, problem
    checked, problem = resolved_cast_realization(
        request.family, tag, nullable, realization_of(value, request.family)
    )
    if checked is None:
        assert problem is not None
        return None, problem
    return SQLOperation(expression, "cast", (value,), checked), None


def resolved_cast_realization(family, tag, nullable, value):
    if tag != "Float" or value.tag != "Int" or proven_int_bounds(value) is None:
        return None, ("PIE-B1003", "cast_realization_not_admitted")
    return Realization(
        "Float",
        {"kind": "pg_float8" if family == "postgres" else "my_double"},
        nullable,
        {"kind": "finite_float", "format": "binary64"},
    ), None


def resolved_scalar_call_realization(family, symbol, tag, nullable, values):
    """Admit only a canonical builtin identity with its proved physical result."""
    if symbol.namespace is not SymbolNamespace.CALLABLE or not values:
        return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
    name = symbol.name
    value = values[0]
    if name == "trim" and len(values) == 1 and tag == "Text":
        result = _text_result(
            family, value, nullable, value.domain.get("max_characters")
        )
        if result is not None:
            return result, None
    if name in {"lower", "upper"} and len(values) == 1 and tag == "Text":
        result = _text_result(
            family, value, nullable, value.domain.get("max_characters")
        )
        if result is not None:
            return result, None
        return None, ("PIE-B1004", "text_case_result_bound_missing")
    if name == "len" and len(values) == 1 and value.tag == "Text" and tag == "Int":
        maximum = value.domain.get("max_characters")
        if type(maximum) is not int or maximum < 0:
            return None, ("PIE-B1004", "text_length_bound_missing")
        storage = {"kind": "pg_int8" if family == "postgres" else "my_bigint"}
        checked = _checked_int(storage, 0, maximum, nullable)
        if checked is None:
            return None, ("PIE-B1002", "text_length_outside_physical_range")
        proof = signed_range(storage)
        assert proof is not None
        return (
            Realization(
                checked.tag,
                checked.storage,
                checked.nullable,
                checked.domain,
                proof,
            ),
            None,
        )
    if name == "substr" and tag == "Text":
        if not (
            len(values) == 3
            and value.tag == "Text"
            and values[1].tag == values[2].tag == "Int"
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        start, count = proven_int_bounds(values[1]), proven_int_bounds(values[2])
        maximum = value.domain.get("max_characters")
        if (
            start is None
            or count is None
            or count[0] < 0
            or count[1] < 0
            or type(maximum) is not int
        ):
            return None, ("PIE-B1004", "substring_result_bound_missing")
        if family == "postgres" and not all(
            -(1 << 31) <= bound <= (1 << 31) - 1 for bound in (*start, *count)
        ):
            return None, ("PIE-B1002", "substring_index_outside_physical_range")
        result = _text_result(family, value, nullable, min(maximum, count[1]))
        if result is not None:
            return result, None
    if name == "replace":
        if len(values) != 3 or tag != "Text":
            return None, ("PIE-B1004", "text_replace_result_bound_missing")
        text, needle, replacement = values
        if any(
            item.tag != "Text" or _text_domain(item) != _text_domain(text)
            for item in values[1:]
        ):
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        input_maximum = text.domain.get("max_characters")
        replacement_maximum = replacement.domain.get("max_characters")
        if type(input_maximum) is not int or type(replacement_maximum) is not int:
            return None, ("PIE-B1004", "text_replace_result_bound_missing")
        result = _text_result(
            family,
            text,
            nullable,
            input_maximum * max(1, replacement_maximum),
        )
        if result is not None:
            return result, None
    if (
        name in {"contains", "starts_with", "ends_with"}
        and len(values) == 2
        and tag == "Bool"
    ):
        left, right = values
        if left.tag == right.tag == "Text" and _text_domain(left) == _text_domain(
            right
        ):
            return _bool(family, nullable), None
    if (name == "coalesce" and len(values) >= 2) or (
        name == "nullif" and len(values) == 2
    ):
        carrier = _concrete_values(values)
        if carrier is not None and carrier.tag == tag == "Text":
            result = _text_carrier_result(
                family,
                values,
                nullable,
                None if name == "coalesce" else values[0].domain.get("max_characters"),
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if carrier is not None and carrier.tag == tag == "Int":
            result = _int_carrier_result(
                family, values, nullable, preserve_input=name == "nullif"
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if carrier is not None and carrier.tag == tag == "Bool":
            result = _bool_carrier_result(
                family, values, nullable, preserve_input=name == "nullif"
            )
            if result is not None:
                return result, None
            return None, ("PIE-B1003", "scalar_call_signature_not_admitted")
        if (
            carrier is not None
            and tag in {"Decimal", "Float", "Timestamp", "UUID"}
            and all(
                item.tag == carrier.tag
                and (
                    _typed_null(item)
                    or (
                        item.storage == carrier.storage
                        and item.domain == carrier.domain
                    )
                )
                for item in values[1:]
            )
            and values[0].tag == carrier.tag
            and tag == carrier.tag
        ):
            return Realization(tag, carrier.storage, nullable, carrier.domain), None
    if name == "abs" and len(values) == 1 and value.tag == tag == "Decimal":
        return Realization(tag, value.storage, nullable, value.domain), None
    if (
        name == "date_of"
        and len(values) == 1
        and value.tag == "Timestamp"
        and (
            _typed_null(value)
            or (
                value.storage
                == {
                    "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                }
                and value.domain == {"kind": "timestamp"}
            )
        )
        and tag == "Date"
    ):
        return (
            Realization(
                "Date",
                {"kind": "pg_date" if family == "postgres" else "my_date"},
                nullable,
                {"kind": "date"},
            ),
            None,
        )
    if (
        name == "sign"
        and len(values) == 1
        and value.tag in {"Int", "Decimal"}
        and tag == "Int"
    ):
        checked = _checked_int(
            {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
            -1,
            1,
            nullable,
        )
        if checked is not None:
            return checked, None
    if (
        name in {"year", "month", "day", "hour", "minute"}
        and len(values) == 1
        and (
            (
                value.tag == "Timestamp"
                and value.storage
                == {
                    "kind": "pg_timestamp" if family == "postgres" else "my_datetime",
                    "fractional_seconds": 6,
                }
                and value.domain == {"kind": "timestamp"}
            )
            or (
                name in {"year", "month", "day"}
                and value.tag == "Date"
                and value.storage
                == {"kind": "pg_date" if family == "postgres" else "my_date"}
                and value.domain == {"kind": "date"}
            )
        )
        and tag == "Int"
    ):
        bounds = {
            "year": (1000, 9999),
            "month": (1, 12),
            "day": (1, 31),
            "hour": (0, 23),
            "minute": (0, 59),
        }[name]
        checked = _checked_int(
            {"kind": "pg_int8" if family == "postgres" else "my_signed_int"},
            *bounds,
            nullable,
        )
        if checked is not None:
            return checked, None
    return None, ("PIE-B1003", "scalar_call_signature_not_admitted")


def realization_of(value, family: str) -> Realization:
    if type(value) in {SQLStageReference, SQLOperation, SQLParameterRead}:
        return value.realization
    return constant_realization(value, family)


def value_nodes(value) -> tuple[Any, ...]:
    """Preorder image of one admitted tree; constant chains stay a single leaf."""
    return _value_nodes(value, render_order=False)


def rendered_value_nodes(value) -> tuple[Any, ...]:
    """Preorder image of one admitted tree in SQL rendering order."""
    return _value_nodes(value, render_order=True)


def _value_nodes(value, *, render_order) -> tuple[Any, ...]:
    if type(value) is SQLStageReference:
        return (value,)
    if type(value) is SQLOperation:
        result: list[Any] = [value]
        operands = (
            tuple(
                value.operands[i]
                for i in rendered_operand_order(value.kind, len(value.operands))
            )
            if render_order
            else value.operands
        )
        for operand in operands:
            result.extend(_value_nodes(operand, render_order=render_order))
        return tuple(result)
    return (value,)


def operand_refs(value) -> tuple[Any, ...]:
    if type(value) is SQLOperation:
        return tuple(root_expression(operand).ref for operand in value.operands)
    return ()


def root_expression(value):
    if type(value) in {SQLStageReference, SQLOperation, SQLParameterRead}:
        return value.original
    return parameters.value_nodes(value)[0].original


def requirement_kind(node) -> str:
    if type(node) is SQLStageReference:
        return "reference"
    if type(node) is SQLParameterRead:
        return "query_parameter"
    assert type(node) is SQLOperation
    return {
        "sign": "arithmetic",
        "arithmetic": "arithmetic",
        "logical": "logical",
        "comparison": "comparison",
        "between": "between",
        "scalar_call": "scalar_call",
        "conditional": "conditional",
        "membership": "membership",
        "cast": "cast",
        "not": "not",
        "null_test": "null_test",
    }[node.kind]


REQUIREMENT_RULES = {
    "query_parameter": "R04",
    "reference": "R05",
    "arithmetic": "R05",
    "comparison": "R05",
    "between": "R05",
    "scalar_call": "R05",
    "conditional": "R05",
    "membership": "R05",
    "cast": "R05",
    "not": "R06",
    "null_test": "R05",
    "logical": "R06",
}


# Retained expression demands of these kinds belong to R05; the compiled replay
# attributes its operation records by the same roles.
R05_OPERATIONS = {
    row.ProjectSQLComparison: "comparison",
    row.ProjectSQLBetween: "between",
    row.ProjectSQLIsNull: "null_test",
    row.ProjectSQLConditional: "conditional",
    row.ProjectSQLMembership: "membership",
    row.ProjectSQLCast: "cast",
}


def demand_rule(plan, entry) -> str | None:
    """Slice6 rule attribution for the retained expression/filter demand families."""
    if entry.family.value == "filter":
        return "R06"
    if entry.family.value != "expression":
        return None
    expression = plan.expressions[entry.subject.position]
    if type(expression) is row.ProjectSQLBinary:
        return "R06" if expression.expression.operator in LOGICAL else "R05"
    if type(expression) in R05_OPERATIONS:
        return "R05"
    return None


def match_applicability(request):
    """Check retained ON trees against the same scalar domain; never build JOIN SQL."""
    plan = request.plan
    problems = []
    sites = {
        site.ref
        for site in plan.expression_sites
        if type(site) is row.ProjectSQLMatchSite
    }
    for expression in plan.expressions:
        if expression.site.ref not in sites:
            continue
        problem = _match_node(plan, expression)
        if problem is not None:
            problems.append((*problem, expression.ref, expression.site.occurrence.span))
    return tuple(problems)


def _match_node(plan, expression):
    if type(expression) is row.ProjectSQLMatchReference:
        ports = {port.ref: port for port in plan.join_ports}
        port = ports.get(expression.port)
        if port is None or port.block is not expression.site.block:
            return ("PIE-B1001", "match_reference_outside_pre_match_scope")
        if value_tag(expression) is None:
            return ("PIE-B1004", "match_reference_logical_type_missing")
        return None
    if type(expression) is row.ProjectSQLComparison:
        if expression.expression.operator not in COMPARISONS:
            return ("PIE-B1003", "match_comparison_operator_not_admitted")
        return None
    if type(expression) is row.ProjectSQLBinary:
        if expression.expression.operator not in LOGICAL:
            return ("PIE-B1003", "match_binary_operator_not_admitted")
        return None
    if type(expression) in {row.ProjectSQLIsNull, row.ProjectSQLLiteral}:
        return None
    return ("PIE-B1003", "match_condition_not_in_row_domain")
