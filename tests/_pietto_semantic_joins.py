"""Run the single-file JOIN stages of `pietto.semantic.joins` on a program.

`analyze_project_namespace` supplies the symbol tables, source rows and
relationship facts after def inlining, without running the single-file JOIN
stages a second time.
`resolve_by_declaration` stands in for relationship resolution,
which `pietto.semantic.join_relationships` owns: tests that need a resolved
relationship patch it in as ``joins.resolve_join_relationship``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    JoinClause,
    QueryDef,
    RelationshipMetadata,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import joins
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.inline_functions import inline_functions
from pietto.semantic.join_relationships import (
    JoinBindingView,
    JoinRelationshipContext,
    ResolvedJoinRelationship,
)
from pietto.semantic.model import RowSchema, SemanticModel, ValueType

# Ends with a newline; the first relation of a program starts on line 18.
JOIN_PREFIX = """shape Order:
    id: Int not null
    customer_id: Int nullable
    amount: Int not null
shape Customer:
    id: Int not null
    name: Text not null
    region_id: Int nullable
    active: Bool nullable
shape Region:
    id: Int not null
    label: Text not null
source orders: Order is postgres.table("shop.orders")
source customers: Customer is postgres.table("shop.customers")
source regions: Region is postgres.table("shop.regions")
relationship order_customer: orders.customer_id == customers.id
relationship customer_region: customers.region_id == regions.id
"""


@dataclass(frozen=True)
class JoinRun:
    """One program after `joins.build_join_structures`."""

    script: Script
    model: SemanticModel
    structures: dict[TableDef | QueryDef, joins.JoinStructure]
    join_resolutions: dict[JoinClause, SourceDef | TableDef | QueryDef]
    diagnostics: list[Diagnostic]

    def relation(self, name: str) -> TableDef | QueryDef:
        return cast(TableDef | QueryDef, self.model.relation_symbols[name])

    def schema_of(self, relation: SourceDef | TableDef | QueryDef) -> RowSchema:
        if isinstance(relation, SourceDef):
            return self.model.source_row_schemas[relation]
        return self.model.relation_row_schemas[relation]

    def rows(self, name: str) -> joins.JoinRows | None:
        return joins.join_rows(self.structures[self.relation(name)], self.schema_of)

    def checks(
        self,
        relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema] | None = None,
    ) -> tuple[joins.JoinChecks, dict[Expression, ValueType]]:
        """Phase B over the model's rows, or over ``relation_row_schemas``."""

        value_types: dict[Expression, ValueType] = {}
        checks = joins.check_join_semantics(
            self.script,
            self.structures,
            relation_symbols=self.model.relation_symbols,
            source_row_schemas=self.model.source_row_schemas,
            relation_row_schemas=(
                self.model.relation_row_schemas
                if relation_row_schemas is None
                else relation_row_schemas
            ),
            expression_value_types=value_types,
            type_expansions=self.model.type_expansions,
        )
        return checks, value_types


def run_joins(source: str, *, path: str = "joins.pietto") -> JoinRun:
    parsed = parse_source(source, path=path)
    assert parsed.ast is not None and parsed.diagnostics == (), parsed.diagnostics
    script, inline_diagnostics = inline_functions(parsed.ast)
    assert inline_diagnostics == (), inline_diagnostics
    result = analyze_project_namespace(script)
    assert result.script is not None
    structures, join_resolutions, diagnostics = joins.build_join_structures(
        result.script,
        relation_symbols=result.model.relation_symbols,
        relationships=result.model.relationships,
        source_row_schemas=result.model.source_row_schemas,
        type_expansions=result.model.type_expansions,
    )
    return JoinRun(
        script=result.script,
        model=result.model,
        structures=structures,
        join_resolutions=join_resolutions,
        diagnostics=diagnostics,
    )


def located(diagnostics: object) -> list[tuple[str, str, int, int]]:
    return [
        (item.code, item.message, item.location.line, item.location.column)
        for item in cast(list[Diagnostic], diagnostics)
    ]


def resolve_by_declaration(
    clause: JoinClause,
    *,
    target: SourceDef | TableDef | QueryDef,
    visible: tuple[JoinBindingView, ...],
    written_source: JoinBindingView | None,
    context: JoinRelationshipContext,
) -> ResolvedJoinRelationship | tuple[Diagnostic, ...]:
    """Resolve as a test program means it: the `via` relationship, or the
    first one between the source's relation and the target, from the
    written `from` or the one visible binding such a relationship relates;
    roles from the step, else from the endpoint of the source's relation.
    Anything else stops silently."""

    steps = clause.traversal_steps

    def relates(relationship: RelationshipMetadata, source: JoinBindingView) -> bool:
        ends = sorted(item.relation_name for item in relationship.endpoints)
        return ends == sorted((source.relation.name, target.name))

    candidates = [
        item
        for item in context.relationships
        if not steps or item.name == steps[0].relationship_name
    ]
    sources = (
        [written_source]
        if written_source is not None
        else [item for item in visible if any(relates(r, item) for r in candidates)]
    )
    if len(sources) != 1:
        return ()
    source = sources[0]
    relationship = next((item for item in candidates if relates(item, source)), None)
    if relationship is None or relationship.base_match is None:
        return ()
    step = steps[0] if steps else None
    if step is not None and step.source_endpoint_role is not None:
        roles = (step.source_endpoint_role, cast(str, step.target_endpoint_role))
    else:
        first, second = relationship.endpoints
        roles = (
            (first.local_name, second.local_name)
            if first.relation_name == source.relation.name
            else (second.local_name, first.local_name)
        )
    pairs = []
    pending: list[Expression] = [relationship.base_match.expression]
    while pending:
        item = pending.pop()
        if type(item) is BinaryExpr and item.operator == "and":
            pending.extend((item.right, item.left))
            continue
        comparison = cast(ComparisonExpr, item)
        left = cast(DottedNameExpr, comparison.left)
        right = cast(DottedNameExpr, comparison.right)
        if left.parts[0] != roles[0]:
            left, right = right, left
        pairs.append((left.parts[1], right.parts[1], comparison, left, right))
    return ResolvedJoinRelationship(
        source=source,
        source_inferred=written_source is None,
        relationship=relationship.name,
        step=step,
        source_role=roles[0],
        target_role=roles[1],
        pairs=tuple(pairs),
    )
