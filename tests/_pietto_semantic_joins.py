"""Run the single-file JOIN stages of `pietto.semantic.joins` on a program.

`analyze_project_namespace` supplies the symbol tables, source rows and
relationship facts after def inlining, without running the single-file JOIN
stages a second time.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from pietto.ast_nodes import (
    Expression,
    JoinClause,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import joins
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic.inline_functions import inline_functions
from pietto.semantic.model import RowSchema, SemanticModel, ValueType

# Ends with a newline; the first relation of a program starts on line 18.
JOIN_PREFIX = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
shape Customer:
    id: Int
    name: Text
    region_id: Int | None
    active: Bool | None
shape Region:
    id: Int
    label: Text
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
source regions: Region = postgres.table("shop.regions")
relationship order_customer(order: Order, customer: Customer): order.customer_id == customer.id
relationship customer_region(customer: Customer, region: Region): customer.region_id == region.id
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
