"""Admitted row expressions, stage bodies and finite target range realization."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project.model import ProjectResolvedTypeKind
from pietto.semantic.model import TypeKind, ValueTypeKind, EffectiveNullability

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
}
COMPARABLE = ("Int", "Text", "Decimal")
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
    """One value's checked logical tag, physical storage and exact value domain."""

    tag: str
    storage: dict[str, Any]
    nullable: bool | str
    domain: dict[str, Any]


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
    return Realization(
        logical.name, value["storage"], value["nullable"], value["domain"]
    )


def constant_realization(value, family: str) -> Realization:
    described = parameters.representation(value, family)
    tag = parameters.tag_of(value.original)
    assert tag is not None
    return Realization(
        tag, described["storage"], described["nullable"], described["domain"]
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


CHILD_FIELDS = {
    row.ProjectSQLUnary: ("operand",),
    row.ProjectSQLBinary: ("left", "right"),
    row.ProjectSQLComparison: ("left", "right"),
    row.ProjectSQLIsNull: ("value",),
    row.ProjectSQLBetween: ("value", "lower", "upper"),
}


def tree_nodes(plan, reference):
    """Preorder original nodes of one authored tree, following its operand links."""
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
        fields = CHILD_FIELDS.get(type(expression), ())
        pending.extend(getattr(expression, name) for name in reversed(fields))
    return tuple(result)


def constant_chains(plan, reference):
    """Every maximal literal/sign chain in this tree, in exact preorder."""
    result = []
    covered = set()
    for expression in tree_nodes(plan, reference):
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
    tag, nullable = value_tag(expression), value_nullable(expression)
    if tag is None or nullable is None:
        return None, ("PIE-B1004", "expression_logical_type_evidence_missing")
    if type(expression) is reference_type:
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
    }:
        return None, ("PIE-B1001", "reference_outside_its_admitted_scope")
    if type(expression) is row.ProjectSQLUnary:
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
        bounds = int_bounds(inner)
        if bounds is None:
            return None, ("PIE-B1004", "int_range_evidence_missing")
        low, high = (
            (-bounds[1], -bounds[0])
            if (expression.expression.operator == "-")
            else bounds
        )
        storage = _arithmetic_storage(family, inner, inner)
        checked = _checked_int(storage, low, high, nullable)
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
    )


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
    if operator in LOGICAL:
        if tag != "Bool" or left.tag != "Bool" or right.tag != "Bool":
            return None, ("PIE-B1003", "logical_operands_require_bool")
        if left.domain.get("kind") != "bool01" or right.domain.get("kind") != "bool01":
            return None, ("PIE-B1002", "logical_operand_outside_bool_domain")
        return (
            SQLOperation(
                expression, "logical", values, _bool(request.family, nullable)
            ),
            None,
        )
    if tag != "Int" or left.tag != "Int" or right.tag != "Int":
        return None, ("PIE-B1003", "arithmetic_requires_signed_int_operands")
    left_bounds, right_bounds = int_bounds(left), int_bounds(right)
    if left_bounds is None or right_bounds is None:
        return None, ("PIE-B1004", "int_range_evidence_missing")
    low, high = _interval(operator, left_bounds, right_bounds)
    checked = _checked_int(
        _arithmetic_storage(request.family, left, right), low, high, nullable
    )
    if checked is None:
        return None, ("PIE-B1002", "arithmetic_outside_physical_range")
    return SQLOperation(expression, "arithmetic", values, checked), None


def _comparison(
    request, columns, expression, tag, nullable, uses, reference_type
) -> tuple[Any, None] | tuple[None, tuple[str, str]]:
    if expression.expression.operator not in COMPARISONS:
        return None, ("PIE-B1003", "comparison_operator_not_admitted")
    values, problem = _operands(
        request, columns, (expression.left, expression.right), uses, reference_type
    )
    if values is None:
        assert problem is not None
        return None, problem
    left, right = (realization_of(value, request.family) for value in values)
    if tag != "Bool":
        return None, ("PIE-B1002", "comparison_result_not_bool")
    if left.tag not in COMPARABLE or left.tag != right.tag:
        return None, ("PIE-B1003", "comparison_type_pair_not_admitted")
    if left.tag == "Text" and _text_domain(left) != _text_domain(right):
        return None, ("PIE-B1005", "text_comparison_domain_conflict")
    if left.tag == "Decimal" and (
        _decimal_domain(left) != _decimal_domain(right)
        or None in _decimal_domain(left)
        or left.storage != right.storage
    ):
        return None, ("PIE-B1005", "decimal_comparison_parameter_conflict")
    return (
        SQLOperation(expression, "comparison", values, _bool(request.family, nullable)),
        None,
    )


def realization_of(value, family: str) -> Realization:
    if type(value) in {SQLStageReference, SQLOperation}:
        return value.realization
    return constant_realization(value, family)


def value_nodes(value) -> tuple[Any, ...]:
    """Preorder image of one admitted tree; constant chains stay a single leaf."""
    if type(value) is SQLStageReference:
        return (value,)
    if type(value) is SQLOperation:
        result: list[Any] = [value]
        for operand in value.operands:
            result.extend(value_nodes(operand))
        return tuple(result)
    return (value,)


def operand_refs(value) -> tuple[Any, ...]:
    if type(value) is SQLOperation:
        return tuple(root_expression(operand).ref for operand in value.operands)
    return ()


def root_expression(value):
    if type(value) in {SQLStageReference, SQLOperation}:
        return value.original
    return parameters.value_nodes(value)[0].original


def requirement_kind(node) -> str:
    if type(node) is SQLStageReference:
        return "reference"
    assert type(node) is SQLOperation
    return {
        "sign": "arithmetic",
        "arithmetic": "arithmetic",
        "logical": "logical",
        "comparison": "comparison",
        "null_test": "null_test",
    }[node.kind]


REQUIREMENT_RULES = {
    "reference": "R05",
    "arithmetic": "R05",
    "comparison": "R05",
    "null_test": "R05",
    "logical": "R06",
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
    if type(expression) in {row.ProjectSQLComparison, row.ProjectSQLIsNull}:
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
