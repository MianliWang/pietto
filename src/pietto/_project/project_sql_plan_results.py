"""Visible result ports, quotient comparison and scoped ORDER/LIMIT requirements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto.ast_nodes import (
    Expression,
    NameExpr,
    DottedNameExpr,
    LiteralExpr,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    BetweenExpr,
    IsNullExpr,
    LimitClause,
)
from pietto.semantic.model import ValueType
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT
from pietto._project.model import ProjectRowField
from pietto._project.project_final_outputs import (
    ProjectDistinct,
    ProjectDistinctFullRowUniqueness,
    ProjectCompletedRowDomain,
    ProjectCompletedEffectiveOutput,
    ProjectCompletedOutputField,
    ProjectNoJoinScalarExpression,
    ProjectNoJoinGroupedOutput,
    ProjectRelationOrdering,
    ProjectRelationOrderItem,
    ProjectRelationOrderInput,
    ProjectRelationLimit,
    ProjectConcreteNoJoinReplay,
)
from pietto._project.project_grain import ProjectDistinctGrainOrigin
from pietto._project.project_row_equivalence import ProjectRowEquivalenceField
from pietto._project.project_ir_properties import (
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRPropertyStage,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
    ProjectIROutputDeterminationResult,
    ProjectIROutputValueClass,
)
from pietto._project.project_query_block_ir import (
    ProjectIRDistinctComparison,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockResultProperties,
    ProjectIRQueryBlockOperatorOccurrence,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorOccurrence
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
)
from pietto._project import project_sql_plan_expressions as row
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_aggregation as aggregation

if TYPE_CHECKING:
    from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLPort

__all__: tuple[str, ...] = ()


class ProjectSQLResultKind(StrEnum):
    DISTINCT = "distinct"
    ORDER = "relation_ordering"
    LIMIT = "limit"


class ProjectSQLResultPortRole(StrEnum):
    PROJECTION = "projection"
    INPUT = "input"
    OUTPUT = "output"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultBoundary:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    position: int
    kind: ProjectSQLResultKind
    predecessor: ProjectSQLPlanRef
    operator: ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
    inputs: tuple[ProjectSQLPlanRef, ...]
    outputs: tuple[ProjectSQLPlanRef, ...]
    properties: ProjectIRQueryBlockResultProperties | ProjectIRPropertyStage


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultPort:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    boundary: ProjectSQLPlanRef
    role: ProjectSQLResultPortRole
    position: int
    source: ProjectSQLPlanRef
    canonical: ProjectSQLPort | None
    key: object
    type_evidence: ProjectRowField | ValueType


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLDistinct:
    ref: ProjectSQLPlanRef
    boundary: ProjectSQLPlanRef
    source: ProjectDistinct
    comparison: ProjectIRDistinctComparison
    fields: tuple[ProjectSQLPlanRef, ...]
    uniqueness: ProjectDistinctFullRowUniqueness
    input_domain: ProjectCompletedRowDomain
    origin: ProjectDistinctGrainOrigin
    global_input: bool


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLQuotientField:
    ref: ProjectSQLPlanRef
    distinct: ProjectSQLPlanRef
    position: int
    canonical: ProjectSQLPort
    input: ProjectSQLPlanRef
    output: ProjectSQLPlanRef
    equivalence: ProjectRowEquivalenceField


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrder:
    ref: ProjectSQLPlanRef
    boundary: ProjectSQLPlanRef
    source: ProjectRelationOrdering
    items: tuple[ProjectSQLPlanRef, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrderItem:
    ref: ProjectSQLPlanRef
    ordering: ProjectSQLPlanRef
    position: int
    source: ProjectRelationOrderItem
    uses: tuple[ProjectSQLPlanRef, ...]
    expression: ProjectSQLPlanRef
    # An expression reference or a pending requirement, checked as closed cases.
    value: ProjectSQLPlanRef
    determination: tuple | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrderExpression:
    ref: ProjectSQLPlanRef
    item: ProjectSQLPlanRef
    position: int
    expression: Expression
    value_type: ValueType
    operands: tuple[ProjectSQLPlanRef, ...]
    use: ProjectSQLPlanRef | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLOrderUse:
    ref: ProjectSQLPlanRef
    item: ProjectSQLPlanRef
    position: int
    source: ProjectRelationOrderInput
    scope: ProjectSQLPlanRef
    ports: tuple[ProjectSQLPlanRef, ...]
    requirement: ProjectSQLPlanRef | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLHiddenOrderRequirement:
    """A requested value, with proof images; never an available scalar port."""

    ref: ProjectSQLPlanRef
    item: ProjectSQLPlanRef
    scope: ProjectSQLPlanRef
    source: ProjectRelationOrderItem
    proof: ProjectIROutputDeterminationResult
    properties: ProjectIROutputRelationalProperties
    determinants: tuple[
        tuple[ProjectIROutputValueClass, tuple[ProjectSQLPlanRef, ...]], ...
    ]
    requested: tuple[ProjectIROutputValueClass, ...]
    # Original ORDER occurrences and their active pre-quotient evidence images.
    input_images: tuple[tuple[ProjectRelationOrderInput, ProjectSQLPlanRef], ...]
    value_type: ValueType


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultLimit:
    ref: ProjectSQLPlanRef
    boundary: ProjectSQLPlanRef
    source: ProjectRelationLimit | ProjectIRProvidedCardinalityUpperBound
    clause: LimitClause
    literal: LiteralExpr
    value: int
    row_count_upper_bound: int
    maximum: int


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultExport:
    ref: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    canonical: ProjectSQLPort
    port: ProjectSQLPlanRef


type Witness = (
    ProjectSQLResultBoundary
    | ProjectSQLResultPort
    | ProjectSQLDistinct
    | ProjectSQLQuotientField
    | ProjectSQLOrder
    | ProjectSQLOrderItem
    | ProjectSQLOrderExpression
    | ProjectSQLOrderUse
    | ProjectSQLHiddenOrderRequirement
    | ProjectSQLResultLimit
    | ProjectSQLResultExport
)


class ProjectSQLResultDemandKind(StrEnum):
    BOUNDARY = "result_scope_and_membership"
    PORT = "result_value_representation"
    DISTINCT = "visible_row_quotient"
    COMPARISON = "field_equivalence_nulls_and_type_sources"
    ORDER = "relation_order_scope"
    ORDER_ITEM = "order_direction_nulls_and_ties"
    EXPRESSION = "order_expression_type_and_operands"
    USE = "order_value_use"
    HIDDEN = "pending_strict_fd_order_realization"
    LIMIT = "static_row_count_upper_bound"
    EXPORT = "canonical_result_image"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLResultDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLResultDemandKind
    witness: Witness
    origin: ProjectSQLPlanRef


def order_index(completed):
    indexed = {}
    for fact in completed.roots.order_facts:
        if id(fact.entry) in indexed:
            raise ValueError("ORDER preparation must have one exact result owner")
        indexed[id(fact.entry)] = fact
    return indexed


def ordering(entry, indexed):
    fact = indexed.get(id(entry.semantic_entry))
    return (
        fact.ordering
        if fact is not None and fact.entry is entry.semantic_entry
        else None
    )


def distinct(entry):
    semantic = entry.semantic_entry
    return (
        semantic.row_domain.distinct
        if isinstance(semantic, ProjectCompletedEffectiveOutput)
        else None
    )


def order_types(item):
    source = item.source
    if isinstance(
        source,
        (ProjectNoJoinScalarExpression, ProjectConcreteJoinedNamespaceExpression),
    ):
        return source.value_types
    return {item.expression: item.value_type}


def order_key(use, aggregate):
    target = use.target
    if isinstance(target, windows.ProjectJoinedWindowInputBinding):
        return windows.joined_target(target)
    if isinstance(
        target,
        (
            windows.ProjectModuleWindowOutputFact,
            windows.ProjectSelectedWindowResultBinding,
        ),
    ):
        return windows.selected_source(target)
    return windows.group_target(target, aggregate)


def selected_targets(completed, entry) -> tuple[tuple[object, ...], ...]:
    """Read retained SELECT references; a computed result exposes no free inputs."""
    semantic = entry.semantic_entry
    if not isinstance(semantic, ProjectCompletedEffectiveOutput):
        return ()
    rows = row.row_authority(completed, entry)
    result: list[tuple[object, ...]] = []
    for position, field in enumerate(semantic.fields):
        source = field.source
        if isinstance(source, ProjectConcreteJoinedNamespaceExpression):
            targets = (
                tuple(r.target for r in source.resolutions)
                if isinstance(source.expression, (NameExpr, DottedNameExpr))
                else ()
            )
        elif isinstance(source, ProjectNoJoinScalarExpression):
            if not isinstance(
                source.expression, (NameExpr, DottedNameExpr)
            ) or not isinstance(rows, row.ProjectSQLRowAuthority):
                targets = ()
            else:
                targets = tuple(
                    r.input_field
                    if r.input_field is not None
                    else r.let_candidates[0].expression
                    for r in rows.selected_references[position]
                )
        elif isinstance(source, ProjectNoJoinGroupedOutput):
            targets = (source.select_fact.item,)
        else:
            targets = (source,)
        result.append(targets)
    return tuple(result)


def proof_properties(value: ProjectDistinct):
    root = value.root
    if isinstance(root, windows.ProjectConcreteJoinedQualify):
        return root.window_stage.input_aggregation.input_filter.joined_semantics.property_bridge.relational
    if isinstance(root, ProjectConcreteNoJoinReplay) and isinstance(
        root.upstream_entry, ProjectExistingEffectiveOutput
    ):
        return root.upstream_entry.properties
    return None


def class_target_index(properties):
    """Index exact original value-class images, without compiling or solving FDs."""
    by_field, by_position = {}, {}
    for group in properties.value_classes:
        for member in group.members:
            by_field.setdefault(id(member.evidence), {})[id(group)] = group
            by_position.setdefault(member.field_position, {})[id(group)] = group
    return by_field, by_position


def class_targets(indexes, targets):
    from pietto._project.project_scalar_references import ProjectScalarEnvironmentField

    by_field, by_position = indexes

    matched = tuple(
        tuple(
            (
                by_position.get(target.position, {})
                if isinstance(target, ProjectScalarEnvironmentField)
                else by_field.get(id(target), {})
            ).values()
        )
        for target in targets
    )
    return tuple(groups[0] if len(groups) == 1 else None for groups in matched)


def result_properties(entry, operator):
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        values = entry.row_properties
    elif hasattr(entry, "row_properties"):
        values = entry.row_properties
    else:
        return entry.semantic_entry.fragment.property_stage
    matches = tuple(p for p in values if p.output.occurrence.producer is operator.node)
    if len(matches) != 1:
        raise ValueError("Result boundary lost its original operator properties")
    return matches[0]


def ready(entry, indexed):
    definition = entry.owner.definition
    order = ordering(entry, indexed)
    if definition.order_by_clause is not None:
        if (
            not isinstance(order, ProjectRelationOrdering)
            or order.inputs is None
            or len(order.inputs) != len(order.items)
        ):
            return False
        supported = {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
            UnaryExpr,
            BinaryExpr,
            ComparisonExpr,
            BetweenExpr,
            IsNullExpr,
        }
        for item, uses in zip(order.items, order.inputs, strict=True):
            expected = (
                tuple(
                    node
                    for node in row.scalar_nodes(item.expression)
                    if isinstance(node, (NameExpr, DottedNameExpr))
                )
                if isinstance(
                    item.source,
                    (
                        ProjectNoJoinScalarExpression,
                        ProjectConcreteJoinedNamespaceExpression,
                    ),
                )
                else (item.expression,)
            )
            if len(uses) != len(expected) or any(
                use.expression is not expression
                for use, expression in zip(uses, expected, strict=True)
            ):
                return False
            nodes = row.scalar_nodes(
                item.expression, tuple(use.expression for use in uses)
            )
            types = {id(node): value for node, value in order_types(item).items()}
            if any(
                type(node) not in supported or id(node) not in types for node in nodes
            ):
                return False
            if any(use.target is None for use in uses):
                return False
        quotient = distinct(entry)
        if quotient is not None and (
            len(quotient.order_proofs) != len(order.items)
            or any(
                type(proof) is not tuple
                or len(proof) not in {2, 3}
                or proof[0] is not item
                for proof, item in zip(quotient.order_proofs, order.items, strict=True)
            )
        ):
            return False
    return True


def origin_context(plan):
    return {
        "definitions": {d.ref: d.entry.owner for d in plan.bindings.definitions},
        "boundaries": {b.ref: b for b in plan.result_boundaries},
        "distincts": {d.ref: d for d in plan.distincts},
        "orders": {o.ref: o for o in plan.orders},
        "items": {i.ref: i for i in plan.order_items},
    }


def origin_parts(witness, context):
    """Pure role/link interpretation, shared with the independent inventory check."""
    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    D = ProjectSQLResultDemandKind
    if isinstance(witness, ProjectSQLResultBoundary):
        definition = witness.definition
        cause = context["definitions"][definition].definition
        return (
            definition,
            cause,
            (witness.predecessor, *witness.inputs, *witness.outputs),
            D.BOUNDARY,
            P.GENERATED_STRUCTURE,
        )
    if isinstance(witness, ProjectSQLResultPort):
        cause = context["definitions"][witness.definition].definition
        return (
            witness.definition,
            cause,
            (witness.boundary, witness.source),
            D.PORT,
            P.VALUE,
        )
    if isinstance(witness, ProjectSQLResultExport):
        cause = context["definitions"][witness.definition].definition
        return (
            witness.definition,
            cause,
            (witness.canonical.ref, witness.port),
            D.EXPORT,
            P.VALUE,
        )
    if isinstance(witness, ProjectSQLQuotientField):
        parent = context["distincts"][witness.distinct]
        boundary = context["boundaries"][parent.boundary]
        selected = witness.equivalence.selected
        if not isinstance(selected, ProjectCompletedOutputField):
            raise ValueError("Quotient origin requires an original visible selection")
        return (
            boundary.definition,
            selected.item,
            (witness.distinct, witness.input, witness.output),
            D.COMPARISON,
            P.TYPE_PROOF,
        )
    if isinstance(witness, ProjectSQLDistinct):
        boundary = context["boundaries"][witness.boundary]
        return (
            boundary.definition,
            witness.source.clause,
            (witness.boundary, *witness.fields),
            D.DISTINCT,
            P.MEMBERSHIP,
        )
    if isinstance(witness, ProjectSQLResultLimit):
        boundary = context["boundaries"][witness.boundary]
        return (
            boundary.definition,
            witness.clause,
            (witness.boundary,),
            D.LIMIT,
            P.MEMBERSHIP,
        )
    if isinstance(witness, ProjectSQLOrder):
        boundary = context["boundaries"][witness.boundary]
        return (
            boundary.definition,
            witness.source.clause,
            (witness.boundary, *witness.items),
            D.ORDER,
            P.GENERATED_STRUCTURE,
        )
    item = (
        witness
        if isinstance(witness, ProjectSQLOrderItem)
        else context["items"][witness.item]
    )
    order = context["orders"][item.ordering]
    definition = context["boundaries"][order.boundary].definition
    if isinstance(witness, ProjectSQLOrderItem):
        return (
            definition,
            witness.source.expression,
            (witness.ordering, witness.expression, witness.value, *witness.uses),
            D.ORDER_ITEM,
            P.TYPE_PROOF,
        )
    if isinstance(witness, ProjectSQLOrderExpression):
        return (
            definition,
            witness.expression,
            (
                witness.item,
                *witness.operands,
                *((witness.use,) if witness.use is not None else ()),
            ),
            D.EXPRESSION,
            P.VALUE,
        )
    if isinstance(witness, ProjectSQLOrderUse):
        return (
            definition,
            witness.source.expression,
            (
                witness.item,
                *witness.ports,
                *((witness.requirement,) if witness.requirement is not None else ()),
            ),
            D.USE,
            P.VALUE,
        )
    return (
        definition,
        witness.source.expression,
        (
            witness.item,
            witness.scope,
            *(port for _, ports in witness.determinants for port in ports),
            *(port for _, port in witness.input_images),
        ),
        D.HIDDEN,
        P.TYPE_PROOF,
    )


def build(plan, ref):
    """Allocate the result graph once, after the existing row-stage construction."""
    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind as K, _operators

    collections = {
        name: []
        for name in (
            "result_boundaries",
            "result_ports",
            "distincts",
            "quotient_fields",
            "orders",
            "order_items",
            "order_expressions",
            "order_uses",
            "hidden_order_requirements",
            "result_limits",
            "result_exports",
        )
    }
    ports = collections["result_ports"]
    orderings = order_index(plan.scope.completed)
    class_indexes = {}
    local_stage = {p.ref: p for p in plan.stage_ports}
    projections = {
        p.export: p
        for p in (
            *plan.projections,
            *plan.aggregate_projections,
            *plan.window_projections,
        )
    }
    blocks = {
        b.definition: b
        for b in plan.blocks
        if b.kind is row.ProjectSQLStageKind.PROJECTION
    }

    def port(definition, scope, role, position, source, canonical, key, evidence):
        value = ProjectSQLResultPort(
            ref=ref(K.RESULT_PORT),
            definition=definition,
            boundary=scope,
            role=role,
            position=position,
            source=source,
            canonical=canonical,
            key=key,
            type_evidence=evidence,
        )
        ports.append(value)
        return value

    for definition in plan.bindings.definitions:
        entry = definition.entry
        authored = entry.owner.definition
        projection = blocks.get(definition.ref)
        if projection is None:
            continue
        operators = tuple(
            op for op in _operators(entry) if op.kind.value in set(ProjectSQLResultKind)
        )
        if not operators:
            continue
        order = ordering(entry, orderings)
        quotient = distinct(entry)
        aggregate = aggregation.authority(plan.scope.completed, entry)
        pre_projection = {
            id(local_stage[p].key): local_stage[p] for p in projection.inputs
        }
        carried = [
            port(
                definition.ref,
                projection.ref,
                ProjectSQLResultPortRole.PROJECTION,
                i,
                projections[p.ref].ref,
                p,
                p,
                p.field.evidence,
            )
            for i, p in enumerate(definition.exports)
        ]
        if order is not None and quotient is None:
            assert order.inputs is not None
            seen = set()
            for uses in order.inputs:
                for use in uses:
                    key = order_key(use, aggregate)
                    if id(key) not in seen:
                        seen.add(id(key))
                        previous = pre_projection[id(key)]
                        carried.append(
                            port(
                                definition.ref,
                                projection.ref,
                                ProjectSQLResultPortRole.PROJECTION,
                                len(carried),
                                previous.ref,
                                None,
                                key,
                                previous.type_evidence,
                            )
                        )
        predecessor = projection.ref
        targets = selected_targets(plan.scope.completed, entry)
        for position, operator in enumerate(operators):
            boundary_ref = ref(K.RESULT_BOUNDARY)
            kind = ProjectSQLResultKind(operator.kind.value)
            inputs = tuple(
                port(
                    definition.ref,
                    boundary_ref,
                    ProjectSQLResultPortRole.INPUT,
                    i,
                    previous.ref,
                    previous.canonical,
                    previous.key,
                    previous.type_evidence,
                )
                for i, previous in enumerate(carried)
            )
            outputs = tuple(
                port(
                    definition.ref,
                    boundary_ref,
                    ProjectSQLResultPortRole.OUTPUT,
                    i,
                    previous.ref,
                    previous.canonical,
                    previous.key,
                    previous.type_evidence,
                )
                for i, previous in enumerate(inputs)
                if previous.canonical is not None
            )
            boundary = ProjectSQLResultBoundary(
                ref=boundary_ref,
                definition=definition.ref,
                position=position,
                kind=kind,
                predecessor=predecessor,
                operator=operator,
                inputs=tuple(p.ref for p in inputs),
                outputs=tuple(p.ref for p in outputs),
                properties=result_properties(entry, operator),
            )
            collections["result_boundaries"].append(boundary)
            if kind is ProjectSQLResultKind.DISTINCT:
                assert quotient is not None and isinstance(
                    operator.evidence, ProjectIRDistinctComparison
                )
                distinct_ref = ref(K.DISTINCT)
                fields = []
                for i, (incoming, outgoing, evidence) in enumerate(
                    zip(inputs, outputs, quotient.equivalence.evidence, strict=True)
                ):
                    assert incoming.canonical is not None
                    field = ProjectSQLQuotientField(
                        ref=ref(K.QUOTIENT_FIELD),
                        distinct=distinct_ref,
                        position=i,
                        canonical=incoming.canonical,
                        input=incoming.ref,
                        output=outgoing.ref,
                        equivalence=evidence,
                    )
                    fields.append(field.ref)
                    collections["quotient_fields"].append(field)
                collections["distincts"].append(
                    ProjectSQLDistinct(
                        ref=distinct_ref,
                        boundary=boundary_ref,
                        source=quotient,
                        comparison=operator.evidence,
                        fields=tuple(fields),
                        uniqueness=quotient.uniqueness,
                        input_domain=quotient.input_domain,
                        origin=quotient.origin,
                        global_input=quotient.global_input,
                    )
                )
            elif kind is ProjectSQLResultKind.ORDER:
                assert order is not None and order.inputs is not None
                order_ref = ref(K.ORDER)
                item_refs = []
                visible = {}
                for original_targets, incoming in zip(targets, inputs):
                    for target in original_targets:
                        visible.setdefault(id(target), []).append(incoming.ref)
                helpers = {id(p.key): p.ref for p in inputs if p.canonical is None}
                for i, (item, original_uses) in enumerate(
                    zip(order.items, order.inputs, strict=True)
                ):
                    item_ref = ref(K.ORDER_ITEM)
                    proof = None if quotient is None else quotient.order_proofs[i]
                    if proof is not None and type(proof) is not tuple:
                        raise ValueError(
                            "DISTINCT ORDER requires a retained proof record"
                        )
                    pending_ref = None
                    if proof is not None and len(proof) == 2:
                        assert quotient is not None
                        pending_ref = ref(K.HIDDEN_ORDER_REQUIREMENT)
                        properties = proof_properties(quotient)
                        assert properties is not None
                        if id(properties) not in class_indexes:
                            class_indexes[id(properties)] = class_target_index(
                                properties
                            )
                        target_index = class_indexes[id(properties)]
                        class_ports = {}
                        for original_targets, incoming in zip(targets, inputs):
                            for group in class_targets(target_index, original_targets):
                                if group is not None:
                                    class_ports.setdefault(id(group), []).append(
                                        incoming.ref
                                    )
                        collections["hidden_order_requirements"].append(
                            ProjectSQLHiddenOrderRequirement(
                                ref=pending_ref,
                                item=item_ref,
                                scope=boundary_ref,
                                source=item,
                                proof=proof[1],
                                properties=properties,
                                determinants=tuple(
                                    (group, tuple(class_ports.get(id(group), ())))
                                    for group in proof[1].seed.classes
                                ),
                                requested=proof[1].requested.classes,
                                input_images=tuple(
                                    (
                                        use,
                                        pre_projection[
                                            id(order_key(use, aggregate))
                                        ].ref,
                                    )
                                    for use in original_uses
                                ),
                                value_type=item.value_type,
                            )
                        )
                    uses = []
                    for j, original in enumerate(original_uses):
                        source_ports = (
                            ()
                            if pending_ref is not None
                            else tuple(
                                visible.get(id(original.determination_target), ())
                            )
                            if quotient is not None
                            else (helpers[id(order_key(original, aggregate))],)
                        )
                        value = ProjectSQLOrderUse(
                            ref=ref(K.ORDER_USE),
                            item=item_ref,
                            position=j,
                            source=original,
                            scope=boundary_ref,
                            ports=source_ports,
                            requirement=pending_ref,
                        )
                        uses.append(value)
                        collections["order_uses"].append(value)
                    use_by_expression = {id(use.source.expression): use for use in uses}
                    nodes = row.scalar_nodes(
                        item.expression,
                        tuple(original.expression for original in original_uses),
                    )
                    node_refs = {id(node): ref(K.ORDER_EXPRESSION) for node in nodes}
                    types = {
                        id(node): value for node, value in order_types(item).items()
                    }
                    for j, node in enumerate(nodes):
                        use = use_by_expression.get(id(node))
                        collections["order_expressions"].append(
                            ProjectSQLOrderExpression(
                                ref=node_refs[id(node)],
                                item=item_ref,
                                position=j,
                                expression=node,
                                value_type=types[id(node)],
                                operands=()
                                if use is not None
                                else tuple(
                                    node_refs[id(child)]
                                    for child in row.scalar_children(node)
                                ),
                                use=None if use is None else use.ref,
                            )
                        )
                    expression = node_refs[id(item.expression)]
                    value = ProjectSQLOrderItem(
                        ref=item_ref,
                        ordering=order_ref,
                        position=i,
                        source=item,
                        uses=tuple(use.ref for use in uses),
                        expression=expression,
                        value=expression if pending_ref is None else pending_ref,
                        determination=proof,
                    )
                    collections["order_items"].append(value)
                    item_refs.append(item_ref)
                collections["orders"].append(
                    ProjectSQLOrder(
                        ref=order_ref,
                        boundary=boundary_ref,
                        source=order,
                        items=tuple(item_refs),
                    )
                )
            else:
                source = entry.active_properties.cardinality
                clause = authored.limit_clause
                assert isinstance(
                    source,
                    (ProjectRelationLimit, ProjectIRProvidedCardinalityUpperBound),
                )
                assert (
                    isinstance(clause.expression, LiteralExpr)
                    and type(clause.expression.value) is int
                )
                collections["result_limits"].append(
                    ProjectSQLResultLimit(
                        ref=ref(K.RESULT_LIMIT),
                        boundary=boundary_ref,
                        source=source,
                        clause=clause,
                        literal=clause.expression,
                        value=clause.expression.value,
                        row_count_upper_bound=source.row_count_upper_bound
                        if isinstance(source, ProjectRelationLimit)
                        else source.upper_bound,
                        maximum=MAX_RELATION_LIMIT,
                    )
                )
            carried = list(outputs)
            predecessor = boundary_ref
        for canonical, value in zip(definition.exports, carried, strict=True):
            collections["result_exports"].append(
                ProjectSQLResultExport(
                    ref=ref(K.RESULT_EXPORT),
                    definition=definition.ref,
                    canonical=canonical,
                    port=value.ref,
                )
            )
    return {name: tuple(values) for name, values in collections.items()}
