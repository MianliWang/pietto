"""Single-file JOIN facts for semantic tests of relationship resolution and
the fan-out rule.

They are read from one analyzed file the way the analyzer's JOIN phases read
it: the relationship context and each JOIN's visible earlier bindings for
relationship resolution, and a relation's JOIN facts, admitted `let` values
and relationship calls for the fan-out rule.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pietto.ast_nodes import (
    AuthoredJoinKind,
    Expression,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, analyze
from pietto.semantic.join_fanout import join_fanout_diagnostics
from pietto.semantic.join_relationships import (
    JoinBindingView,
    JoinRelationshipContext,
)

_HIDDEN = (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI)


@dataclass(frozen=True, slots=True)
class JoinScript:
    """One analyzed single file and its relationship context."""

    script: Script
    model: SemanticModel
    context: JoinRelationshipContext

    def relation(self, name: str) -> TableDef | QueryDef:
        definition = self.model.relation_symbols[name]
        assert isinstance(definition, (TableDef, QueryDef))
        return definition

    def visible(self, query: str, ordinal: int) -> tuple[JoinBindingView, ...]:
        """The bindings JOIN `ordinal` (1-based) can read its source from:
        FROM and the earlier targets other than SEMI and ANTI."""

        definition = self.relation(query)
        symbols = self.model.relation_symbols
        source = definition.from_clause.source_name
        views = [
            JoinBindingView(ordinal=0, name=source, relation=_row(symbols[source]))
        ]
        for position, clause in enumerate(definition.join_clauses[: ordinal - 1], 1):
            if clause.kind not in _HIDDEN:
                views.append(
                    JoinBindingView(
                        ordinal=position,
                        name=clause.target_binding_name,
                        relation=_row(symbols[clause.target_relation_name]),
                    )
                )
        return tuple(views)

    def fanout(self, query: str) -> tuple[Diagnostic, ...]:
        """Run the fan-out rule over a relation's JOIN facts, admitted `let`
        values and relationship calls, as the analyzer reads them."""

        definition = self.relation(query)
        scope = self.model.let_scopes.get(definition)
        lets: Mapping[str, Expression] = (
            {}
            if scope is None
            else {
                binding.name: binding.expression
                for binding in scope.bindings
                if binding.name in scope.value_types
            }
        )
        return join_fanout_diagnostics(
            definition,
            self.model.relation_joins[definition],
            type_symbols=self.model.type_symbols,
            source_row_schemas=self.model.source_row_schemas,
            let_expressions=lets,
            relationship_calls=self.model.relationship_calls,
        )


def join_script(source: str, *, path: str = "joins.pietto") -> JoinScript:
    """Parse and analyze `source` and build its relationship context."""

    parsed = parse_source(source, path=path)
    assert parsed.ast is not None, parsed.diagnostics
    semantic = analyze(parsed.ast)
    script = semantic.script
    assert script is not None
    model = semantic.model
    return JoinScript(
        script=script,
        model=model,
        context=JoinRelationshipContext(
            relationships=script.relationships,
            admitted=model.relationships,
            relation_symbols=model.relation_symbols,
            source_row_schemas=model.source_row_schemas,
            type_expansions=model.type_expansions,
        ),
    )


def located(
    diagnostics: tuple[Diagnostic, ...],
) -> list[tuple[str, str, int, int]]:
    return [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ]


def _row(definition: object) -> SourceDef | TableDef | QueryDef:
    assert isinstance(definition, (SourceDef, TableDef, QueryDef))
    return definition
