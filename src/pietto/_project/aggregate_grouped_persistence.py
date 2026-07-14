"""Private aggregate/grouped production-persistence adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pietto._project.aggregate_grouped_dependency_lineage import (
    ProjectAggregateGroupedDependencyLineageReadiness,
    build_project_aggregate_grouped_dependency_lineage_readiness,
)
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyGraphStatus
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.semantic.aggregates import contains_semantic_aggregate

__all__: tuple[str, ...] = ()


def _is_project_aggregate_grouped_definition(
    definition: TableDef | QueryDef,
) -> bool:
    """Return whether a definition requires aggregate/grouped persistence."""

    return definition.group_by_clause is not None or any(
        contains_semantic_aggregate(item.expression) for item in definition.select_items
    )


@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedPersistenceBundle:
    """One validated all-or-none aggregate/grouped production bundle."""

    definition: TableDef | QueryDef
    let_scope_facts: ProjectRelationLetScopeFacts
    dependency_lineage_readiness: ProjectAggregateGroupedDependencyLineageReadiness
    state: ProjectRelationRowSchemaState
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact]

    def __post_init__(self) -> None:
        """Freeze facts and enforce exact nested authority and atomicity."""

        if not isinstance(self.definition, (TableDef, QueryDef)):
            raise ValueError("Persistence bundle requires a derived relation")
        if not isinstance(self.let_scope_facts, ProjectRelationLetScopeFacts):
            raise ValueError("Persistence bundle requires canonical let facts")
        if self.definition.let_clause is None:
            if (
                self.let_scope_facts.status is not ProjectLetScopeFactsStatus.ABSENT
                or self.let_scope_facts.clause is not None
            ):
                raise ValueError("Persistence bundle absent let facts mismatch")
        elif self.let_scope_facts.clause is not self.definition.let_clause:
            raise ValueError("Persistence bundle let-fact identity mismatch")

        readiness = self.dependency_lineage_readiness
        if not isinstance(
            readiness,
            ProjectAggregateGroupedDependencyLineageReadiness,
        ):
            raise ValueError("Persistence bundle requires Slice 9 readiness")
        if readiness.definition is not self.definition:
            raise ValueError("Persistence bundle definition identity mismatch")
        if not isinstance(self.state, ProjectRelationRowSchemaState):
            raise ValueError("Persistence bundle requires a row state")

        aggregate_result_facts = MappingProxyType(dict(self.aggregate_result_facts))
        object.__setattr__(
            self,
            "aggregate_result_facts",
            aggregate_result_facts,
        )

        graph = readiness.dependency_graph
        if (
            self.state.status.value != graph.status.value
            or self.state.reason.value != graph.reason.value
        ):
            raise ValueError("Persistence bundle outer state mismatch")

        finalization = readiness.clause_readiness.finalization
        if graph.status is ProjectRowDependencyGraphStatus.CONCRETE:
            if self.state is not finalization.state:
                raise ValueError(
                    "Concrete persistence bundle must retain finalized state"
                )
            nested_facts = finalization.aggregate_result_facts
            if tuple(aggregate_result_facts) != tuple(nested_facts) or any(
                aggregate_result_facts[name] is not fact
                for name, fact in nested_facts.items()
            ):
                raise ValueError(
                    "Concrete persistence bundle must retain aggregate facts"
                )
            return

        if (
            finalization.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            and self.state is not finalization.state
        ):
            raise ValueError(
                "Nested non-concrete persistence must retain finalized state"
            )
        if aggregate_result_facts:
            raise ValueError("Non-concrete persistence bundle forbids facts")
        if self.state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
            schema = self.state.schema
            if schema is None or schema.fields or not schema.is_unknown:
                raise ValueError(
                    "Unknown persistence bundle requires empty unknown schema"
                )
        elif self.state.schema is not None:
            raise ValueError("Deferred or blocked persistence bundle forbids schema")


def build_project_aggregate_grouped_persistence(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
    fallback_path: str,
) -> ProjectAggregateGroupedPersistenceBundle:
    """Build one canonical Slice 9 result and normalize it for persistence."""

    if input_schema.is_unknown:
        raise ValueError("Aggregate/grouped persistence requires concrete input")
    upstream_definition = upstream_symbol.definition
    if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
        raise ValueError("Aggregate/grouped persistence requires relation upstream")
    if isinstance(upstream_definition, SourceDef):
        if (
            upstream_symbol.kind is not ProjectSymbolKind.SOURCE
            or upstream_lineage is not None
        ):
            raise ValueError("Source persistence requires no upstream lineage")
    elif (
        isinstance(upstream_definition, TableDef)
        and upstream_symbol.kind is not ProjectSymbolKind.TABLE
    ) or (
        isinstance(upstream_definition, QueryDef)
        and upstream_symbol.kind is not ProjectSymbolKind.QUERY
    ):
        raise ValueError("Relation persistence symbol kind mismatch")
    elif (
        upstream_lineage is None
        or upstream_lineage.status is not ProjectRowLineageStatus.CONCRETE
    ):
        raise ValueError("Relation persistence requires concrete upstream lineage")

    let_scope_facts = build_project_relation_let_scope_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_definition=upstream_definition,
    )
    readiness = build_project_aggregate_grouped_dependency_lineage_readiness(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        upstream_lineage=upstream_lineage,
        fallback_path=fallback_path,
        let_scope_facts=let_scope_facts,
    )
    graph = readiness.dependency_graph
    finalization = readiness.clause_readiness.finalization
    if finalization.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        state = finalization.state
        aggregate_result_facts = {}
    elif graph.status is ProjectRowDependencyGraphStatus.CONCRETE:
        state = readiness.clause_readiness.finalization.state
        aggregate_result_facts = (
            readiness.clause_readiness.finalization.aggregate_result_facts
        )
    else:
        status = ProjectRelationRowSchemaStatus(graph.status.value)
        state = ProjectRelationRowSchemaState(
            status=status,
            schema=(
                ProjectRowSchema(is_unknown=True)
                if status is ProjectRelationRowSchemaStatus.UNKNOWN
                else None
            ),
            reason=ProjectRelationRowSchemaReason(graph.reason.value),
        )
        aggregate_result_facts = {}

    return ProjectAggregateGroupedPersistenceBundle(
        definition=definition,
        let_scope_facts=let_scope_facts,
        dependency_lineage_readiness=readiness,
        state=state,
        aggregate_result_facts=aggregate_result_facts,
    )
