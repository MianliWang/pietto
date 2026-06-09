"""Canonical type alias expansion and cycle diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import Definition, Script, TypeDef, TypeExpr
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ResolvedType, TypeKind

_UNKNOWN_EXPANSION = ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN)


def expand_type_aliases(
    script: Script,
    *,
    type_symbols: Mapping[str, Definition],
    type_resolutions: Mapping[TypeExpr, ResolvedType],
) -> tuple[dict[TypeExpr, ResolvedType], list[Diagnostic]]:
    """Expand all resolved type expressions to canonical terminal types."""

    aliases = tuple(
        definition
        for definition in script.definitions
        if isinstance(definition, TypeDef)
        and type_symbols.get(definition.name) is definition
    )
    source_order = {definition: index for index, definition in enumerate(aliases)}
    canonical_aliases: dict[TypeDef, ResolvedType] = {}
    stack: list[TypeDef] = []
    stack_positions: dict[TypeDef, int] = {}
    reported_cycles: set[frozenset[TypeDef]] = set()
    diagnostics: list[Diagnostic] = []

    def expand_alias(definition: TypeDef) -> ResolvedType:
        existing = canonical_aliases.get(definition)
        if existing is not None:
            return existing

        cycle_start = stack_positions.get(definition)
        if cycle_start is not None:
            cycle = tuple(stack[cycle_start:])
            cycle_key = frozenset(cycle)
            if cycle_key not in reported_cycles:
                anchor = min(cycle, key=source_order.__getitem__)
                diagnostics.append(_cycle_diagnostic(anchor))
                reported_cycles.add(cycle_key)
            for member in cycle:
                canonical_aliases[member] = _UNKNOWN_EXPANSION
            return _UNKNOWN_EXPANSION

        stack_positions[definition] = len(stack)
        stack.append(definition)
        direct = type_resolutions[definition.base]
        if direct.kind is TypeKind.TYPE_ALIAS:
            target = direct.definition
            assert isinstance(target, TypeDef)
            canonical = expand_alias(target)
        else:
            canonical = direct
        stack.pop()
        del stack_positions[definition]

        if definition not in canonical_aliases:
            canonical_aliases[definition] = canonical
        return canonical_aliases[definition]

    for alias in aliases:
        expand_alias(alias)

    expansions: dict[TypeExpr, ResolvedType] = {}
    for type_expr, direct in type_resolutions.items():
        if direct.kind is TypeKind.TYPE_ALIAS:
            definition = direct.definition
            assert isinstance(definition, TypeDef)
            expansions[type_expr] = expand_alias(definition)
        else:
            expansions[type_expr] = direct

    return expansions, diagnostics


def _cycle_diagnostic(definition: TypeDef) -> Diagnostic:
    """Report one alias cycle at its earliest participating target."""

    span = definition.base.span
    return Diagnostic(
        code="PIE-S2003",
        severity=Severity.ERROR,
        message=f"Type alias cycle involving {definition.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
