"""Single-file JOIN facts for semantic tests of the fan-out rule.

They are read from one analyzed file the way the analyzer's JOIN phases read
it: a relation's JOIN facts, admitted `let` values and relationship calls.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, analyze
from pietto.semantic.join_fanout import join_fanout_diagnostics


@dataclass(frozen=True, slots=True)
class JoinScript:
    """One analyzed single file."""

    script: Script
    model: SemanticModel

    def relation(self, name: str) -> TableDef | QueryDef:
        definition = self.model.relation_symbols[name]
        assert isinstance(definition, (TableDef, QueryDef))
        return definition

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
    """Parse and analyze `source`."""

    parsed = parse_source(source, path=path)
    assert parsed.ast is not None, parsed.diagnostics
    semantic = analyze(parsed.ast)
    script = semantic.script
    assert script is not None
    return JoinScript(script=script, model=semantic.model)


def located(
    diagnostics: tuple[Diagnostic, ...],
) -> list[tuple[str, str, int, int]]:
    return [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ]
