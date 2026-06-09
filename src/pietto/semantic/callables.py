"""Signature-only semantic checks for constraints and derives."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import ConstraintDef, DeriveDef, Node, Script, TypeExpr
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ResolvedType, TypeKind

CallableDefinition = ConstraintDef | DeriveDef


def check_callable_signatures(
    script: Script,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
) -> list[Diagnostic]:
    """Validate callable parameters and declared constraint return types."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (ConstraintDef, DeriveDef)):
            continue
        diagnostics.extend(_duplicate_parameter_diagnostics(definition))
        if isinstance(definition, ConstraintDef):
            diagnostic = _constraint_return_diagnostic(
                definition,
                type_resolutions[definition.return_type],
            )
            if diagnostic is not None:
                diagnostics.append(diagnostic)
    return diagnostics


def _duplicate_parameter_diagnostics(
    definition: CallableDefinition,
) -> list[Diagnostic]:
    """Report each later repeated parameter in source order."""

    diagnostics: list[Diagnostic] = []
    seen_names: set[str] = set()
    callable_kind = "constraint" if isinstance(definition, ConstraintDef) else "derive"

    for parameter in definition.parameters:
        if parameter.name in seen_names:
            diagnostics.append(
                _diagnostic(
                    parameter,
                    code="PIE-S2001",
                    message=(
                        f"Duplicate parameter name in {callable_kind} "
                        f"{definition.name}: {parameter.name}"
                    ),
                )
            )
        else:
            seen_names.add(parameter.name)

    return diagnostics


def _constraint_return_diagnostic(
    definition: ConstraintDef,
    resolved_type: ResolvedType,
) -> Diagnostic | None:
    """Require a directly resolved built-in Bool constraint return type."""

    if resolved_type.kind is TypeKind.UNKNOWN:
        return None
    if resolved_type.kind is TypeKind.BUILTIN and resolved_type.name == "Bool":
        return None
    return _diagnostic(
        definition.return_type,
        code="PIE-S2401",
        message=f"Constraint {definition.name} must return Bool",
    )


def _diagnostic(node: Node, *, code: str, message: str) -> Diagnostic:
    """Create an error diagnostic from one complete AST node span."""

    span = node.span
    return Diagnostic(
        code=code,
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
