"""Admitted JOIN structures, membership wrappers and joined port realization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project import project_sql_emission_windows as windowing
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.project_sql_plan_joins import (
    ProjectSQLJoinPortKind,
    ProjectSQLJoinRows,
)
from pietto.ast_nodes import AuthoredJoinKind, SourceDef

__all__: tuple[str, ...] = ()

NATIVE_KINDS = {
    AuthoredJoinKind.CROSS: "CROSS JOIN",
    AuthoredJoinKind.INNER: "INNER JOIN",
    AuthoredJoinKind.LEFT: "LEFT JOIN",
    AuthoredJoinKind.RIGHT: "RIGHT JOIN",
    AuthoredJoinKind.FULL: "FULL JOIN",
}
MEMBERSHIP = {
    AuthoredJoinKind.SEMI: "exists",
    AuthoredJoinKind.ANTI: "not_exists",
}
EXPECTED_ROWS = {
    AuthoredJoinKind.INNER: ProjectSQLJoinRows.MATCHED_PAIRS,
    AuthoredJoinKind.LEFT: ProjectSQLJoinRows.LEFT_PRESERVED,
    AuthoredJoinKind.CROSS: ProjectSQLJoinRows.CARTESIAN_PAIRS,
    AuthoredJoinKind.RIGHT: ProjectSQLJoinRows.RIGHT_PRESERVED,
    AuthoredJoinKind.FULL: ProjectSQLJoinRows.BOTH_PRESERVED,
    AuthoredJoinKind.SEMI: ProjectSQLJoinRows.LEFT_EXISTS,
    AuthoredJoinKind.ANTI: ProjectSQLJoinRows.LEFT_NOT_EXISTS,
}
# The published R09 restricted FULL domain: PostgreSQL only, and only over the
# reviewed physical signed-integer types of direct cross-input V01 fields.
FULL_STORAGE = {"pg_int2", "pg_int4", "pg_int8"}
NULLABILITY = {
    ProjectRowFieldNullability.NON_NULL: False,
    ProjectRowFieldNullability.NULLABLE: True,
    ProjectRowFieldNullability.UNKNOWN: "unknown",
}
SENTINEL = "1"


@dataclass(frozen=True, slots=True, eq=False)
class JoinInput:
    """One JOIN input relation, its alias and its exact pre-match columns."""

    original: Any
    ordinal: int
    use: Any
    producer: Any
    symbol: Any
    columns: tuple[rows.StageColumn, ...]
    ports: tuple[Any, ...]
    source: Any = None
    """The plan source definition this input scans, when it reaches one."""


@dataclass(frozen=True, slots=True, eq=False)
class JoinEquality:
    """One retained relationship base equality between two pre-match ports."""

    original: Any
    left: rows.StageColumn
    right: rows.StageColumn
    left_port: Any
    right_port: Any
    left_scope: Any
    right_scope: Any


@dataclass(frozen=True, slots=True, eq=False)
class JoinColumn:
    """One published joined output port, with its pre-match carrier."""

    position: int
    port: Any
    match: Any
    label: str
    symbol: Any
    column: rows.StageColumn
    scope: Any
    read: rows.StageColumn


@dataclass(frozen=True, slots=True, eq=False)
class JoinBody:
    """One generated SELECT publishing exactly one JOIN occurrence's ports."""

    join: Any
    index: int
    inputs: tuple[JoinInput, JoinInput]
    equalities: tuple[JoinEquality, ...]
    predicate: Any
    columns: tuple[JoinColumn, ...]
    symbol: Any
    cte_columns: tuple[Any, ...]
    membership: str | None
    sentinel: Any


def joined_definitions(plan) -> dict[Any, tuple[Any, ...]]:
    """Ordered JOIN occurrences per definition, exactly as the plan retained them."""
    grouped: dict[Any, list[Any]] = {}
    for join in plan.joins:
        grouped.setdefault(join.definition, []).append(join)
    result = {}
    for definition, items in grouped.items():
        ordered = sorted(items, key=lambda join: join.position)
        if tuple(join.position for join in ordered) != tuple(range(len(ordered))):
            return {}
        result[definition] = tuple(ordered)
    return result


def admitted_join_shape(plan) -> bool:
    """Ordered JOIN chains over admitted inputs with the existing row tail."""
    if not plan.joins or any(
        (
            plan.distincts,
            plan.orders,
            plan.result_limits,
            plan.set_bodies,
        )
    ):
        return False
    if any(
        type(expression)
        not in {
            row.ProjectSQLLiteral,
            row.ProjectSQLBoundLiteral,
            row.ProjectSQLReference,
            row.ProjectSQLJoinedReference,
            row.ProjectSQLMatchReference,
            row.ProjectSQLUnary,
            row.ProjectSQLBinary,
            row.ProjectSQLComparison,
            row.ProjectSQLIsNull,
            grouping.ProjectSQLResultReference,
            plan_windows.ProjectSQLWindowReference,
        }
        for expression in plan.expressions
    ):
        return False
    if not grouping.blocks_admitted(plan) or not windowing.blocks_admitted(plan):
        return False
    grouped = joined_definitions(plan)
    if not grouped:
        return False
    tails = {tail.definition: tail for tail in plan.join_tails}
    if set(tails) != set(grouped):
        return False
    named = tuple(
        item
        for item in plan.bindings.definitions
        if type(item.entry.owner.definition) is not SourceDef
    )
    if not named or not plan.sources:
        return False
    inputs = {item.ref: item for item in plan.join_inputs}
    ports = {port.ref: port for port in plan.join_ports}
    for definition, joins in grouped.items():
        tail = tails[definition]
        final = joins[-1]
        if tail.join is not final.ref or len(tail.ports) != len(tail.fields):
            return False
        if any(reference not in set(final.outputs) for reference in tail.ports):
            return False
        for join in joins:
            if (
                join.kind not in EXPECTED_ROWS
                or join.rows is not (EXPECTED_ROWS[join.kind])
            ):
                return False
            if (join.kind is AuthoredJoinKind.CROSS) != (
                join.on is None and not join.equalities
            ):
                return False
            if len(join.inputs) != 2 or any(
                reference not in inputs for reference in join.inputs
            ):
                return False
            if any(reference not in ports for reference in join.outputs):
                return False
            left, right = (inputs[reference] for reference in join.inputs)
            if (left.ordinal, right.ordinal) != (0, 1):
                return False
            for item in (left, right):
                if (item.producer is None) == (item.predecessor is None):
                    return False
                if (item.binding_use is None) != (item.producer is None):
                    return False
                if len(item.ports) != len(item.source.source_properties.fields):
                    return False
            width = len(left.ports) + len(right.ports)
            expected = len(left.ports) if join.kind in MEMBERSHIP else width
            if len(join.outputs) != expected:
                return False
            match = tuple(
                port
                for port in plan.join_ports
                if port.block is join.ref and port.kind is ProjectSQLJoinPortKind.MATCH
            )
            if len(match) != width or tuple(port.ref for port in match) != (
                *left.ports,
                *right.ports,
            ):
                return False
            for position, reference in enumerate(join.outputs):
                port = ports[reference]
                if (
                    port.block is not join.ref
                    or port.kind is not ProjectSQLJoinPortKind.OUTPUT
                    or port.position != position
                    or port.source is not match[position].ref
                ):
                    return False
    return True


def null_rejected_ports(join, equalities, predicate) -> frozenset:
    """Pre-match ports the join's own effective ON proves cannot be NULL.

    Only a matched-pairs INNER join publishes every row through its condition, so
    only there does a NULL operand remove the row. A conjunct proves its own direct
    comparison operands; an OR branch, a NULL test and a computed operand prove
    nothing. Retained relationship equalities are comparisons over two pre-match
    ports and prove both.
    """
    if join.kind is not AuthoredJoinKind.INNER:
        return frozenset()
    proved = set()
    for item in equalities:
        proved.update((item.left_port, item.right_port))
    pending = [predicate] if predicate is not None else []
    while pending:
        value = pending.pop()
        if type(value) is not rows.SQLOperation:
            continue
        if value.kind == "logical":
            if value.original.expression.operator == "and":
                pending.extend(value.operands)
            continue
        if value.kind != "comparison":
            continue
        for operand in value.operands:
            if type(operand) is rows.SQLStageReference:
                proved.add(operand.port)
    return frozenset(proved)


def port_realization(port, read: rows.StageColumn, *, outer: bool, proved=False):
    """The exact realization of one joined port over its pre-match carrier.

    An outer port keeps the carrier's physical storage and value domain and only
    gains the possibility of NULL; the original declaration is never rewritten.
    A nullable carrier narrows to NON NULL only where `proved` reports that this
    join's own condition rejects a NULL in that exact pre-match port.
    """
    logical = port.field.evidence.resolved_type
    nullable = NULLABILITY.get(port.field.effective_nullability)
    if logical.kind is not ProjectResolvedTypeKind.BUILTIN or nullable is None:
        return None, ("PIE-B1004", "join_port_logical_type_evidence_missing")
    carrier = read.realization
    if carrier.tag != logical.name:
        return None, ("PIE-B1002", "join_port_logical_type_drift")
    if not outer and nullable != carrier.nullable:
        return None, ("PIE-B1002", "pre_match_port_nullability_drift")
    if outer and nullable is not True and nullable != carrier.nullable:
        if not (nullable is False and carrier.nullable is True and proved):
            return None, ("PIE-B1002", "join_output_nullability_drift")
    return (
        rows.Realization(carrier.tag, carrier.storage, nullable, carrier.domain),
        None,
    )


def full_admissible(join, equalities, predicate, family: str):
    """Check the published restricted FULL domain; other inputs are non-support."""
    if family != "postgres":
        return ("PIE-B1003", "mysql_full_join_approved_non_support")
    leaves = []
    for item in equalities:
        leaves.append((item.left.realization, item.right.realization))
    problem = _condition_equalities(predicate, leaves)
    if problem is not None:
        return problem
    if not leaves:
        return ("PIE-B1003", "full_join_requires_cross_input_equality")
    for left, right in leaves:
        if (
            left.tag != "Int"
            or right.tag != "Int"
            or left.storage.get("kind") not in FULL_STORAGE
            or left.storage != right.storage
        ):
            return ("PIE-B1003", "full_join_equality_outside_reviewed_int_domain")
    return None


def _condition_equalities(predicate, leaves):
    """Collect the ordered AND tree of direct cross-input builtin equalities."""
    if predicate is None:
        return None
    if type(predicate) is not rows.SQLOperation:
        return ("PIE-B1003", "full_join_condition_not_an_equality_tree")
    if predicate.kind == "logical":
        if predicate.original.expression.operator != "and":
            return ("PIE-B1003", "full_join_condition_uses_or")
        for operand in predicate.operands:
            problem = _condition_equalities(operand, leaves)
            if problem is not None:
                return problem
        return None
    if predicate.kind != "comparison" or (
        predicate.original.expression.operator != "=="
    ):
        return ("PIE-B1003", "full_join_condition_not_an_equality")
    left, right = predicate.operands
    if type(left) is not rows.SQLStageReference or (
        type(right) is not rows.SQLStageReference
    ):
        return ("PIE-B1003", "full_join_equality_operand_not_a_direct_field")
    if left.scope is right.scope:
        return ("PIE-B1003", "full_join_equality_within_one_input")
    leaves.append((left.realization, right.realization))
    return None


def join_rule(kind: AuthoredJoinKind) -> str:
    if kind in MEMBERSHIP:
        return "R11"
    if kind is AuthoredJoinKind.FULL:
        return "R09"
    if kind in {AuthoredJoinKind.LEFT, AuthoredJoinKind.RIGHT}:
        return "R08"
    return "R07"


def demand_rule(plan, entry) -> str | None:
    """Rule attribution for the retained JOIN demand families."""
    family = entry.family.value
    if family in {"join_rows", "match_input", "match_field", "output_field"}:
        return "R07"
    if family == "relationship_equality":
        return "R07"
    if family == "post_match_scope":
        return "R08"
    if family in {"single_match", "proof_context"}:
        return "R07"
    return None
