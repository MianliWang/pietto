"""CollectV1 and UnnestV1 in the SQL plan: a nested-relation SELECT item, the
JOIN that reads a nested field's rows, and their demands."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCollectReadFact,
    ProjectModuleSelectFact,
    ProjectModuleUnnestOccurrenceFact,
)

if TYPE_CHECKING:
    from pietto._project.module_catalog import ProjectDeclarationOccurrence
    from pietto._project.project_completed_semantics import (
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_sql_plan import (
        ProjectSQLOriginProvenance,
        ProjectSQLPlan,
        ProjectSQLPlanRef,
    )
    from pietto._project.project_sql_plan_results import (
        ProjectSQLOrder,
        ProjectSQLResultLimit,
    )
    from pietto.ast_nodes import CollectRelationExpr

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLCollect:
    """CollectV1 in the plan: one `name = collect r` SELECT item of an ungrouped
    table or query (the parent) is the value of one parent export, the whole
    completed bag of the relation let r (the producer) per parent row. It is the
    projection of `export`; it is never a row expression, input use, boundary,
    scalar port or ProjectSQLProjection.

    ``block`` is the parent's PROJECTION block, ``use`` the expression block
    use of this read, ``children`` the producer's exports in order and
    ``captures`` the captures this read completes, one per capture line of the
    producer in capture order, none for a closed let. The producer's ORDER and
    LIMIT are its own (``collect_order``, ``collect_limit``).
    """

    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    export: ProjectSQLPlanRef
    use: ProjectSQLPlanRef
    producer: ProjectSQLPlanRef
    children: tuple[ProjectSQLPlanRef, ...]
    captures: tuple[ProjectSQLPlanRef, ...]
    semantic: ProjectModuleSelectFact
    fact: ProjectModuleCollectReadFact


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLUnnest:
    """UnnestV1 in the plan: the right input of one CROSS, INNER or LEFT JOIN
    reads the rows of a nested field of the JOIN's left row; its rows are real
    child occurrences, and a LEFT placeholder is known only by its nulling
    cause.

    ``definition`` is the Unnest occurrence (U1), the producer of ``input``;
    ``source`` the left input's port of the nested field, which ``collect``
    reads; ``outputs`` the JOIN's output ports of the element fields, in
    child order; ``semantic`` the occurrence's one input fact (D-S05-7).
    """

    ref: ProjectSQLPlanRef
    join: ProjectSQLPlanRef
    input: ProjectSQLPlanRef
    definition: ProjectSQLPlanRef
    source: ProjectSQLPlanRef
    collect: ProjectSQLPlanRef
    outputs: tuple[ProjectSQLPlanRef, ...]
    semantic: ProjectModuleUnnestOccurrenceFact


class ProjectSQLCollectionDemandKind(StrEnum):
    COLLECT = "collect_completed_bag_per_parent_row"
    COLLECT_ORDER = "collect_element_order_from_producer_order"
    COLLECT_EXPORT = "collect_container_and_child_fields"
    UNNEST_ROWS = "unnest_child_rows_and_left_placeholder"
    UNNEST_SOURCE = "unnest_source_field_and_children"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLCollectionDemand:
    """What a target must realize for one Collect read: COLLECT the whole
    producer bag per parent row (bag duplicates kept, `[]` for no rows, never
    None, parent rows unchanged, parallel reads independent); COLLECT_ORDER
    the element order of the producer's ORDER keys, carried to the collecting
    operation, with no added tie-breaker; COLLECT_EXPORT the container
    nullability of the export and exactly ``children`` as its element fields.

    And for one Unnest: UNNEST_ROWS the real child rows per left row (INNER
    keeps those whose ON is True; `[]` and a None container give none; LEFT
    keeps a left row without such a child once, null-extended; no order);
    UNNEST_SOURCE the nested field at ``source``, its Collect read and the
    correspondence of its children to ``outputs``.
    """

    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    kind: ProjectSQLCollectionDemandKind
    witness: ProjectSQLCollect | ProjectSQLUnnest
    origin: ProjectSQLPlanRef


def collect_read(
    completed: ProjectConcreteCompletedSemanticResult,
    owner: ProjectDeclarationOccurrence,
    expression: CollectRelationExpr,
) -> ProjectModuleCollectReadFact:
    """The one Collect read fact of ``expression`` in ``owner``'s semantic
    facts, the single authority of its value (D-S04-4)."""

    facts = completed.completion.plan.semantic_facts.find_owner(owner)
    matches = tuple(
        item
        for fact in facts
        for item in fact.collect_reads
        if item.expression is expression
    )
    if len(facts) != 1 or len(matches) != 1:
        raise ValueError("A Collect read requires its one read fact.")
    return matches[0]


def unnest_occurrence(
    completed: ProjectConcreteCompletedSemanticResult,
    owner: ProjectDeclarationOccurrence,
) -> ProjectModuleUnnestOccurrenceFact:
    """The one input fact of the Unnest occurrence ``owner`` (D-S05-7)."""

    facts = completed.completion.plan.semantic_facts.find_owner(owner)
    if (
        owner.unnest is None
        or len(facts) != 1
        or facts[0].unnest_occurrence is None
        or facts[0].unnest_occurrence.nested_type is None
    ):
        raise ValueError("An Unnest requires its one typed input fact.")
    return facts[0].unnest_occurrence


def collect_order(plan: ProjectSQLPlan, collect: ProjectSQLCollect) -> ProjectSQLOrder:
    """The producer's own ORDER: its items are the element order (D71.03)."""

    owner = _producer_owner(plan, collect)
    matches = tuple(order for order in plan.orders if order.source.owner is owner)
    if len(matches) != 1:
        raise ValueError("A Collect read requires its producer's one ORDER.")
    return matches[0]


def collect_limit(
    plan: ProjectSQLPlan, collect: ProjectSQLCollect
) -> ProjectSQLResultLimit | None:
    """The producer's own LIMIT, if any; it applies per parent row."""

    boundaries = {
        boundary.ref
        for boundary in plan.result_boundaries
        if boundary.definition is collect.producer
    }
    matches = tuple(
        limit for limit in plan.result_limits if limit.boundary in boundaries
    )
    if len(matches) > 1:
        raise ValueError("A Collect producer has at most one LIMIT.")
    return matches[0] if matches else None


def collect_of(plan: ProjectSQLPlan, port: ProjectSQLPlanRef) -> ProjectSQLCollect:
    """The one Collect read whose nested value ``port`` carries, following
    only EXPORT, INPUT_PORT (its producer port) and JOIN_PORT (its source)."""

    from pietto._project.project_sql_plan import ProjectSQLPlanRefKind as K

    input_ports = {value.ref: value for value in plan.input_ports}
    join_ports = {value.ref: value for value in plan.join_ports}
    current = port
    for _ in range(len(input_ports) + len(join_ports) + 1):
        if current.kind is K.EXPORT:
            matches = tuple(c for c in plan.collects if c.export is current)
            if len(matches) != 1:
                raise ValueError("Port carries no one Collect read.")
            return matches[0]
        if current.kind is K.INPUT_PORT and current in input_ports:
            following = input_ports[current].producer_port
        elif current.kind is K.JOIN_PORT and current in join_ports:
            following = join_ports[current].source
        else:
            following = None
        if following is None:
            raise ValueError("Port carries no one Collect read.")
        current = following
    raise ValueError("Port lineage does not end.")


def origin_parts(
    witness: ProjectSQLCollect | ProjectSQLUnnest,
) -> tuple[
    tuple[ProjectSQLPlanRef, ...],
    tuple[
        tuple[
            ProjectSQLCollectionDemandKind,
            ProjectSQLPlanRef,
            ProjectSQLOriginProvenance,
        ],
        ...,
    ],
]:
    """The COLLECT or UNNEST origin's antecedents and the demands it carries,
    each with its subject and provenance; shared with the independent check."""

    from pietto._project.project_sql_plan import ProjectSQLOriginProvenance as P

    D = ProjectSQLCollectionDemandKind
    if isinstance(witness, ProjectSQLUnnest):
        return (
            (
                witness.join,
                witness.input,
                witness.definition,
                witness.source,
                witness.collect,
            ),
            (
                (D.UNNEST_ROWS, witness.ref, P.MEMBERSHIP),
                (D.UNNEST_SOURCE, witness.ref, P.TYPE_PROOF),
            ),
        )
    return (
        (
            witness.block,
            witness.use,
            witness.producer,
            *witness.captures,
        ),
        (
            (D.COLLECT, witness.ref, P.MEMBERSHIP),
            (D.COLLECT_ORDER, witness.ref, P.MEMBERSHIP),
            (D.COLLECT_EXPORT, witness.export, P.TYPE_PROOF),
        ),
    )


def _producer_owner(plan: ProjectSQLPlan, collect: ProjectSQLCollect):
    matches = tuple(
        definition.entry.owner
        for definition in plan.bindings.definitions
        if definition.ref is collect.producer
    )
    if len(matches) != 1:
        raise ValueError("A Collect read requires its one producer definition.")
    return matches[0]
