"""Shared diagnostics for Semantic IR lowering."""

from __future__ import annotations

from pietto.ast_nodes import Node
from pietto.errors import Diagnostic, Severity, SourceLocation


def missing_semantic_fact_diagnostic(node: Node, fact: str) -> Diagnostic:
    """Report an absent semantic prerequisite at the affected source node."""

    span = node.span
    return Diagnostic(
        code="PIE-I1000",
        severity=Severity.ERROR,
        message=f"Missing semantic fact required for IR lowering: {fact}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
