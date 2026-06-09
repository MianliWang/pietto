"""Structural and field-derive semantic checks for shape definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    Expression,
    IndexDef,
    Node,
    Script,
    ShapeDef,
    TypeExpr,
    UniqueDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ResolvedType, TypeKind, ValueType, ValueTypeKind


def check_shape_structures(script: Script) -> list[Diagnostic]:
    """Check local item names and unique/index field targets."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if isinstance(definition, ShapeDef):
            diagnostics.extend(_check_shape(definition))
    return diagnostics


def check_field_derives(
    script: Script,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    expression_value_types: Mapping[Expression, ValueType],
) -> list[Diagnostic]:
    """Validate known field derive types against canonical field types."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, ShapeDef):
            continue
        for field in definition.fields:
            expression = field.derive_expression
            if expression is None:
                continue
            value_type = expression_value_types.get(expression)
            expected_type = type_expansions[field.type_expr]
            if (
                value_type is None
                or value_type.kind is ValueTypeKind.UNKNOWN
                or expected_type.kind is TypeKind.UNKNOWN
            ):
                continue
            if value_type.resolved_type != expected_type:
                diagnostics.append(
                    _diagnostic(
                        expression,
                        code="PIE-S2402",
                        message=(
                            "Field derive body type does not match field type: "
                            f"{field.name}"
                        ),
                    )
                )
    return diagnostics


def _check_shape(shape: ShapeDef) -> list[Diagnostic]:
    """Check one shape while preserving its source item order."""

    diagnostics: list[Diagnostic] = []
    field_names = {field.name for field in shape.fields}
    seen_item_names: set[str] = set()

    for item in shape.items:
        if item.name in seen_item_names:
            diagnostics.append(
                _diagnostic(
                    item,
                    code="PIE-S2501",
                    message=(
                        f"Duplicate shape item name in shape {shape.name}: {item.name}"
                    ),
                )
            )
        else:
            seen_item_names.add(item.name)

        if isinstance(item, (UniqueDef, IndexDef)):
            diagnostics.extend(_check_targets(shape, item, field_names))

    return diagnostics


def _check_targets(
    shape: ShapeDef,
    item: UniqueDef | IndexDef,
    field_names: set[str],
) -> list[Diagnostic]:
    """Check target existence and repetition for one unique or index item."""

    diagnostics: list[Diagnostic] = []
    seen_targets: set[str] = set()
    item_kind = "unique" if isinstance(item, UniqueDef) else "index"

    # Target names currently have no individual AST spans, so diagnostics use
    # the containing item's span without changing the parser AST.
    for field_name in item.field_names:
        if field_name not in field_names:
            diagnostics.append(
                _diagnostic(
                    item,
                    code="PIE-S2502",
                    message=(
                        f"Unknown target field in shape {shape.name}: {field_name}"
                    ),
                )
            )
        if field_name in seen_targets:
            diagnostics.append(
                _diagnostic(
                    item,
                    code="PIE-S2503",
                    message=(
                        f"Duplicate target field in {item_kind} "
                        f"{item.name}: {field_name}"
                    ),
                )
            )
        else:
            seen_targets.add(field_name)

    return diagnostics


def _diagnostic(node: Node, *, code: str, message: str) -> Diagnostic:
    """Create an error diagnostic at a complete AST node span."""

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
