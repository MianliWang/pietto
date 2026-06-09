"""Semantic analysis entry point."""

from __future__ import annotations

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import CheckMode, SemanticModel, SemanticResult


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Collect top-level symbols and report same-namespace duplicates."""

    mode = mode_override or _mode_from_script(script)
    type_symbols: dict[str, Definition] = {}
    callable_symbols: dict[str, Definition] = {}
    relation_symbols: dict[str, Definition] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        namespace_name, namespace = _namespace_for(
            definition,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
        )
        if definition.name in namespace:
            diagnostics.append(_duplicate_diagnostic(definition, namespace_name))
            continue
        namespace[definition.name] = definition

    return SemanticResult(
        model=SemanticModel(
            mode=mode,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
        ),
        diagnostics=tuple(diagnostics),
    )


def _mode_from_script(script: Script) -> CheckMode:
    """Select the declared mode or the checked default."""

    if script.header is None or script.header.mode is None:
        return CheckMode.CHECKED
    return CheckMode(script.header.mode)


def _namespace_for(
    definition: Definition,
    *,
    type_symbols: dict[str, Definition],
    callable_symbols: dict[str, Definition],
    relation_symbols: dict[str, Definition],
) -> tuple[str, dict[str, Definition]]:
    """Return the namespace assigned to a top-level definition."""

    if isinstance(definition, (TypeDef, EnumDef, ShapeDef)):
        return "type", type_symbols
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return "callable", callable_symbols
    if isinstance(definition, (SourceDef, TableDef, QueryDef)):
        return "relation", relation_symbols
    raise AssertionError(f"Unsupported definition: {type(definition).__name__}")


def _duplicate_diagnostic(
    definition: Definition,
    namespace_name: str,
) -> Diagnostic:
    """Report a duplicate at the later definition's complete source span."""

    span = definition.span
    return Diagnostic(
        code="P2001",
        severity=Severity.ERROR,
        message=(
            f"Duplicate symbol name in {namespace_name} namespace: {definition.name}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
