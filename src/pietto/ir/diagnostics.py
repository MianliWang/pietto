"""Shared diagnostics for Semantic IR lowering."""

from __future__ import annotations

from pietto.ast_nodes import Node, Span
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir.model import RelationIR, ScriptIR, SourceSpan

_JOIN_EXPLAIN_MESSAGE = (
    "Single-file explain does not describe JOIN relations yet: Semantic Metadata "
    "Artifact v1 has one input per relation; use emit-sql to see their SQL"
)


def missing_semantic_fact_diagnostic(node: Node, fact: str) -> Diagnostic:
    """Report an absent semantic prerequisite at the affected source node."""

    return _diagnostic(
        f"Missing semantic fact required for IR lowering: {fact}", node.span
    )


def join_explain_diagnostics(script: ScriptIR) -> tuple[Diagnostic, ...]:
    """Refuse explain at each relation with JOINs, in definition order:
    Semantic Metadata Artifact v1 describes one input per relation."""

    return tuple(
        _diagnostic(_JOIN_EXPLAIN_MESSAGE, definition.span)
        for definition in script.definitions
        if isinstance(definition, RelationIR) and definition.joins
    )


def _diagnostic(message: str, span: Span | SourceSpan) -> Diagnostic:
    return Diagnostic(
        code="PIE-I1000",
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
