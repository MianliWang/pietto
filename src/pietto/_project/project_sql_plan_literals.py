"""Contextual fixed literals; no rebind API or backend parameter spelling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    Expression,
    LiteralExpr,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    IsNullExpr,
    BetweenExpr,
    CallExpr,
    Span,
)
from pietto.semantic.model import ValueType, ValueTypeKind, TypeKind
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_aggregation as aggregation

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import (
        ProjectSQLPlan,
        ProjectSQLPlanRef,
        ProjectSQLPlanScope,
    )
    from pietto._project.module_catalog import ProjectDeclarationOccurrence

__all__: tuple[str, ...] = ()


class ProjectSQLLiteralPolicy(StrEnum):
    PRESERVE_LITERALS = "preserve_literals"
    BIND_SAFE_LITERALS = "bind_safe_literals"


class ProjectSQLLiteralRole(StrEnum):
    SELECT = "select"
    LET = "let"
    WHERE = "where"
    ON = "on"
    AGGREGATE_ARGUMENT = "aggregate_argument"
    SATISFYING = "satisfying"
    QUALIFY = "qualify"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_PARTITION = "window_partition"
    WINDOW_ORDER = "window_order"
    FRAME = "frame"
    ORDER = "relation_order"
    LIMIT = "limit"
    CONNECTOR = "connector"
    TYPE = "type_argument"
    UNKNOWN = "unknown"


class ProjectSQLLiteralDisposition(StrEnum):
    BOUND = "bound"
    PRESERVED_WITH_REASON = "preserved_with_reason"


class ProjectSQLLiteralReason(StrEnum):
    POLICY = "preserve_policy"
    SPECIALIZED = "specialized_or_structural_context"
    CALL_ARGUMENT = "call_argument_subtree"
    UNKNOWN_CONTEXT = "unknown_extraction_context"
    NULL = "untyped_null"
    TYPE_UNAVAILABLE = "literal_type_unavailable"
    NON_BUILTIN = "not_an_admitted_builtin"
    VALUE_REPRESENTATION = "original_scalar_representation_unavailable"
    NONFINITE = "nonfinite_float"


class ProjectSQLLiteralTag(StrEnum):
    BOOL = "Bool"
    INT = "Int"
    TEXT = "Text"
    FLOAT = "Float"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLiteralPosition:
    """Pure traversal result, before policy, allocation or transport selection."""

    definition: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    context: object
    context_ref: ProjectSQLPlanRef
    role: ProjectSQLLiteralRole
    literal: LiteralExpr
    # Each edge is the exact parent and the ordered operand index, root first.
    ancestry: tuple[tuple[Expression, int], ...]
    value_type: ValueType | None
    evidence: object
    expression: ProjectSQLPlanRef | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLiteralSite:
    ref: ProjectSQLPlanRef
    position: ProjectSQLLiteralPosition
    span: Span
    disposition: ProjectSQLLiteralDisposition
    reason: ProjectSQLLiteralReason | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLiteralSlot:
    ref: ProjectSQLPlanRef
    site: ProjectSQLLiteralSite
    value_type: ValueType
    tag: ProjectSQLLiteralTag


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLFixedLiteralValue:
    ref: ProjectSQLPlanRef
    slot: ProjectSQLLiteralSlot
    tag: ProjectSQLLiteralTag
    value: bool | int | str | float


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBindUse:
    ref: ProjectSQLPlanRef
    slot: ProjectSQLLiteralSlot
    expression: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLFixedEnvelope:
    scope: ProjectSQLPlanScope
    policy: ProjectSQLLiteralPolicy
    slots: tuple[ProjectSQLLiteralSlot, ...]
    values: tuple[ProjectSQLFixedLiteralValue, ...]


class ProjectSQLLiteralRequirement(StrEnum):
    DATA_TYPE = "exact_data_representation"
    NULLABILITY = "original_nullability"
    RANGE_PRECISION = "exact_range_and_precision"
    OPERATOR_OPERAND = "typed_operator_and_operand_context"
    COLLATION_OVERLOAD = "applicable_collation_and_overload"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLiteralDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    use: ProjectSQLBindUse
    value: ProjectSQLFixedLiteralValue
    # Original requirements, including every ancestor's actual operand types.
    contexts: tuple[row.ProjectSQLExpressionDemand, ...]
    requirements: tuple[ProjectSQLLiteralRequirement, ...]
    origin: ProjectSQLPlanRef


type Witness = (
    ProjectSQLLiteralSite
    | ProjectSQLLiteralSlot
    | ProjectSQLFixedLiteralValue
    | ProjectSQLBindUse
)


def literal_nodes(expression: Expression):
    """Closed, iterative source traversal; windows own their separate consumers."""
    pending: list[tuple[Expression, int | None]] = [(expression, None)]
    links: list[tuple[Expression, int, int | None]] = []
    while pending:
        node, predecessor = pending.pop()
        if type(node) is LiteralExpr:
            ancestry = []
            current = predecessor
            while current is not None:
                parent, position, current = links[current]
                ancestry.append((parent, position))
            yield node, tuple(reversed(ancestry))
        if isinstance(node, (BinaryExpr, ComparisonExpr)):
            children = (node.left, node.right)
        elif isinstance(node, UnaryExpr):
            children = (node.operand,)
        elif isinstance(node, IsNullExpr):
            children = (node.value,)
        elif isinstance(node, BetweenExpr):
            children = (node.value, node.lower, node.upper)
        elif isinstance(node, CallExpr):
            children = node.arguments
        else:
            children = ()
        for i, child in reversed(tuple(enumerate(children))):
            links.append((node, i, predecessor))
            pending.append((child, len(links) - 1))


def type_arguments(plan: ProjectSQLPlan):
    """Only types consumed by reached source fields; follow retained alias links.

    TypeArgument ASTs are structural, unlike ensure/index/proof predicates.
    Repeated result-port metadata does not create fresh type uses.
    """
    from pietto.ast_nodes import TypeDef

    types = plan.scope.analysis_bundle.root.base_plan.attribution._authority.type_source_resolutions
    for port in plan.source_ports:
        field = port.field.evidence.field_def
        if field is None:
            continue
        expression = field.type_expr
        seen = set()
        while expression is not None:
            if id(expression) in seen:
                raise ValueError("Type source contains a repeated alias context.")
            seen.add(id(expression))
            environment = types._environments_by_path.get(expression.span.path or "")
            matches = (
                ()
                if environment is None
                else tuple(
                    item
                    for item in environment.find_type_expr(expression)
                    if item.reference.type_expr is expression
                )
            )
            resolution = matches[0] if len(matches) == 1 else None
            for argument in expression.arguments:
                yield port, argument.value, resolution
            # Read an already selected edge; no resolve/infer/compose call.
            if resolution is None or resolution.direct_symbol is None:
                break
            definition = resolution.direct_symbol.target_occurrence.definition
            expression = definition.base if type(definition) is TypeDef else None


def positions(plan: ProjectSQLPlan):
    """Read only evaluated/source-component consumers, never proof/type payloads.

    Definition order is dependency-first. Within one definition: scalar sites in
    stage order, window arguments/components, ORDER, LIMIT. Shared producers and
    stage-port references are not traversed again. Inherited window components
    retain their authored AST separately in each actual computation context.
    """
    from pietto._project import project_sql_plan_results as results

    R = ProjectSQLLiteralRole
    role_map = {
        row.ProjectSQLExpressionRole.SELECT: R.SELECT,
        row.ProjectSQLExpressionRole.LET: R.LET,
        row.ProjectSQLExpressionRole.WHERE: R.WHERE,
        row.ProjectSQLExpressionRole.MATCH: R.ON,
        row.ProjectSQLExpressionRole.AGGREGATE_ARGUMENT: R.AGGREGATE_ARGUMENT,
        row.ProjectSQLExpressionRole.SATISFYING: R.SATISFYING,
        row.ProjectSQLExpressionRole.QUALIFY: R.QUALIFY,
    }
    definitions = {d.ref: d for d in plan.bindings.definitions}
    owners = {id(d.entry.owner): d.ref for d in plan.bindings.definitions}
    roots = {d.ref: [] for d in plan.bindings.definitions}
    expressions = {(e.site.ref, id(e.expression)): e for e in plan.expressions}

    def add(
        definition,
        context,
        expression,
        role,
        evidence,
        types,
        consumer=None,
        owner=None,
    ):
        roots[definition].append(
            (context, expression, role, evidence, types, consumer, owner)
        )

    for source in plan.sources:
        add(source.ref, source, source.connector, R.CONNECTOR, source.source, {}, None)
    for port, expression, resolution in type_arguments(plan):
        add(
            port.owner,
            port,
            expression,
            R.TYPE,
            port.field if resolution is None else resolution,
            {},
            owner=None if resolution is None else resolution.reference.owner,
        )
    for site in plan.expression_sites:
        root = (
            site.expression
            if isinstance(site, aggregation.ProjectSQLAggregateSite)
            else site.occurrence.expression
        )
        add(
            owners[id(site.owner)],
            site,
            root,
            role_map.get(site.role, R.UNKNOWN),
            site.evidence,
            {id(e): (e, t) for e, t in row.evidence_types(site.evidence).items()},
            site.ref,
        )
    windows = {w.ref: w for w in plan.windows}
    for argument in plan.window_arguments:
        window = windows[argument.window]
        add(
            window.definition,
            argument,
            argument.expression,
            R.WINDOW_ARGUMENT,
            argument,
            {id(argument.expression): (argument.expression, argument.value_type)},
        )
    for policy in plan.window_policies:
        window = windows[policy.window]
        spec = window.effective.spec
        for expression in spec.partition_by:
            add(window.definition, policy, expression, R.WINDOW_PARTITION, policy, {})
        for item in spec.order_by:
            add(window.definition, policy, item.expression, R.WINDOW_ORDER, policy, {})
        for bound in (spec.frame.start, spec.frame.end):
            if bound is not None and bound.offset is not None:
                add(window.definition, policy, bound.offset, R.FRAME, policy, {})
    orders = {o.ref: o for o in plan.orders}
    boundaries = {b.ref: b for b in plan.result_boundaries}
    for item in plan.order_items:
        definition = boundaries[orders[item.ordering].boundary].definition
        add(
            definition,
            item,
            item.source.item.expression,
            R.ORDER,
            item.source,
            {id(e): (e, t) for e, t in results.order_types(item.source).items()},
        )
    for limit in plan.result_limits:
        add(
            boundaries[limit.boundary].definition,
            limit,
            limit.literal,
            R.LIMIT,
            limit.source,
            {},
        )
    for definition, entries in roots.items():
        for context, expression, role, evidence, types, consumer, owner in entries:
            for literal, ancestry in literal_nodes(expression):
                typed = types.get(id(literal))
                expression_value = expressions.get((consumer, id(literal)))
                yield ProjectSQLLiteralPosition(
                    definition=definition,
                    owner=definitions[definition].entry.owner
                    if owner is None
                    else owner,
                    context=context,
                    context_ref=context.ref,
                    role=role,
                    literal=literal,
                    ancestry=ancestry,
                    evidence=evidence,
                    value_type=None
                    if typed is None or typed[0] is not literal
                    else typed[1],
                    expression=None
                    if expression_value is None
                    else expression_value.ref,
                )


def classify(position: ProjectSQLLiteralPosition, policy: ProjectSQLLiteralPolicy):
    """Builder-only positive eligibility; verification implements its own rule."""
    R, Why = ProjectSQLLiteralRole, ProjectSQLLiteralReason
    if policy is ProjectSQLLiteralPolicy.PRESERVE_LITERALS:
        return Why.POLICY
    if position.role not in (R.SELECT, R.LET, R.WHERE, R.ON, R.UNKNOWN):
        return Why.SPECIALIZED
    if position.role is R.UNKNOWN or position.expression is None:
        return Why.UNKNOWN_CONTEXT
    if any(isinstance(parent, CallExpr) for parent, _ in position.ancestry):
        return Why.CALL_ARGUMENT
    if any(
        type(parent)
        not in (UnaryExpr, BinaryExpr, ComparisonExpr, IsNullExpr, BetweenExpr)
        for parent, _ in position.ancestry
    ):
        return Why.UNKNOWN_CONTEXT
    if position.literal.value is None:
        return Why.NULL
    value_type = position.value_type
    if type(value_type) is not ValueType or value_type.kind is not ValueTypeKind.KNOWN:
        return Why.TYPE_UNAVAILABLE
    resolved = value_type.resolved_type
    if (
        resolved.kind is not TypeKind.BUILTIN
        or resolved.definition is not None
        or resolved.name not in ProjectSQLLiteralTag
    ):
        return Why.NON_BUILTIN
    tag = ProjectSQLLiteralTag(resolved.name)
    value = position.literal.value
    if (
        tag is ProjectSQLLiteralTag.FLOAT
        and type(value) is float
        and not isfinite(value)
    ):
        return Why.NONFINITE
    if not same_value(tag, value, value):
        return Why.VALUE_REPRESENTATION
    return None


def same_value(tag, actual, original) -> bool:
    """Exact immutable primitive tags; float.hex preserves the sign of zero."""
    if type(tag) is not ProjectSQLLiteralTag:
        return False
    scalar = {
        ProjectSQLLiteralTag.BOOL: bool,
        ProjectSQLLiteralTag.INT: int,
        ProjectSQLLiteralTag.TEXT: str,
        ProjectSQLLiteralTag.FLOAT: float,
    }[tag]
    if type(actual) is not scalar or type(original) is not scalar:
        return False
    return (
        isfinite(actual) and isfinite(original) and actual.hex() == original.hex()
        if scalar is float
        else actual == original
    )


def context_index(plan: ProjectSQLPlan):
    return {
        (d.site.ref, id(d.expression)): d
        for d in plan.demands
        if isinstance(d, row.ProjectSQLExpressionDemand)
    }


def demand_contexts(site: ProjectSQLLiteralSite, demands):
    """Read original typed operation demands in source ancestry order."""
    position = site.position
    return tuple(
        demands[(position.context_ref, id(expression))]
        for expression in (*tuple(p for p, _ in position.ancestry), position.literal)
    )


def origin_parts(witness: Witness):
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    if isinstance(witness, ProjectSQLLiteralSite):
        position = witness.position
        return (
            witness,
            (position.context_ref,),
            (
                P.TYPE_PROOF
                if position.role is ProjectSQLLiteralRole.TYPE
                else P.MEMBERSHIP
                if position.role
                in (
                    ProjectSQLLiteralRole.ON,
                    ProjectSQLLiteralRole.WHERE,
                    ProjectSQLLiteralRole.SATISFYING,
                    ProjectSQLLiteralRole.QUALIFY,
                )
                else P.VALUE
            ),
        )
    if isinstance(witness, ProjectSQLLiteralSlot):
        return witness.site, (witness.site.ref,), P.TYPE_PROOF
    if isinstance(witness, ProjectSQLFixedLiteralValue):
        return witness.slot.site, (witness.slot.ref, witness.slot.site.ref), P.VALUE
    return (
        witness.slot.site,
        (witness.slot.ref, witness.expression),
        P.GENERATED_STRUCTURE,
    )


def build(plan: ProjectSQLPlan, policy: ProjectSQLLiteralPolicy, ref):
    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind as K

    sites, slots, values, uses = [], [], [], []
    replacements = {}
    expressions = {e.ref: e for e in plan.expressions}
    for position in positions(plan):
        reason = classify(position, policy)
        site = ProjectSQLLiteralSite(
            ref=ref(K.LITERAL_SITE),
            position=position,
            span=position.literal.span,
            reason=reason,
            disposition=ProjectSQLLiteralDisposition.BOUND
            if reason is None
            else ProjectSQLLiteralDisposition.PRESERVED_WITH_REASON,
        )
        sites.append(site)
        if reason is not None:
            continue
        assert position.value_type is not None and position.expression is not None
        tag = ProjectSQLLiteralTag(position.value_type.resolved_type.name)
        slot = ProjectSQLLiteralSlot(
            ref=ref(K.LITERAL_SLOT), site=site, value_type=position.value_type, tag=tag
        )
        literal_value = position.literal.value
        assert literal_value is not None
        value = ProjectSQLFixedLiteralValue(
            ref=ref(K.FIXED_LITERAL_VALUE), slot=slot, tag=tag, value=literal_value
        )
        use = ProjectSQLBindUse(
            ref=ref(K.BIND_USE), slot=slot, expression=position.expression
        )
        original = expressions[position.expression]
        replacements[original.ref] = row.ProjectSQLBoundLiteral(
            ref=original.ref,
            site=original.site,
            value_type=original.value_type,
            expression=position.literal,
            use=use,
        )
        slots.append(slot)
        values.append(value)
        uses.append(use)
    return dict(
        literal_policy=policy,
        literal_sites=tuple(sites),
        literal_slots=tuple(slots),
        bind_uses=tuple(uses),
        fixed_envelope=ProjectSQLFixedEnvelope(
            scope=plan.scope, policy=policy, slots=tuple(slots), values=tuple(values)
        ),
        expressions=tuple(replacements.get(e.ref, e) for e in plan.expressions),
    )
