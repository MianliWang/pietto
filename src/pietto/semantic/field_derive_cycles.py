"""Cycle diagnostics for dependencies between derived shape fields."""

from __future__ import annotations

from collections.abc import Iterator

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    FieldDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Script,
    ShapeDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation


def check_field_derive_cycles(script: Script) -> list[Diagnostic]:
    """Report one diagnostic per cyclic derived-field component."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if isinstance(definition, ShapeDef):
            diagnostics.extend(_check_shape(definition))
    return diagnostics


def _check_shape(shape: ShapeDef) -> list[Diagnostic]:
    """Build one shape-local dependency graph and find cyclic components."""

    fields_by_name: dict[str, FieldDef] = {}
    for field in shape.fields:
        fields_by_name.setdefault(field.name, field)

    derived_fields = tuple(
        field
        for field in fields_by_name.values()
        if field.derive_expression is not None
    )
    source_order = {field: index for index, field in enumerate(shape.fields)}
    dependencies: dict[FieldDef, tuple[FieldDef, ...]] = {}

    for field in derived_fields:
        assert field.derive_expression is not None
        targets: list[FieldDef] = []
        seen_targets: set[FieldDef] = set()
        for name in _bare_name_references(field.derive_expression):
            target = fields_by_name.get(name)
            if (
                target is not None
                and target.derive_expression is not None
                and target not in seen_targets
            ):
                targets.append(target)
                seen_targets.add(target)
        dependencies[field] = tuple(targets)

    components = _strongly_connected_components(derived_fields, dependencies)
    cyclic_components: list[tuple[FieldDef, ...]] = []
    for component in components:
        if not component:
            continue
        first = component[0]
        if len(component) > 1 or first in dependencies[first]:
            cyclic_components.append(component)
    anchors = sorted(
        (
            min(component, key=source_order.__getitem__)
            for component in cyclic_components
        ),
        key=source_order.__getitem__,
    )
    return [_cycle_diagnostic(field) for field in anchors]


def _strongly_connected_components(
    fields: tuple[FieldDef, ...],
    dependencies: dict[FieldDef, tuple[FieldDef, ...]],
) -> list[tuple[FieldDef, ...]]:
    """Return deterministic strongly connected components."""

    next_index = 0
    indexes: dict[FieldDef, int] = {}
    low_links: dict[FieldDef, int] = {}
    stack: list[FieldDef] = []
    on_stack: set[FieldDef] = set()
    components: list[tuple[FieldDef, ...]] = []

    def visit(field: FieldDef) -> None:
        nonlocal next_index
        indexes[field] = next_index
        low_links[field] = next_index
        next_index += 1
        stack.append(field)
        on_stack.add(field)

        for target in dependencies[field]:
            if target not in indexes:
                visit(target)
                low_links[field] = min(low_links[field], low_links[target])
            elif target in on_stack:
                low_links[field] = min(low_links[field], indexes[target])

        if low_links[field] != indexes[field]:
            return

        component: list[FieldDef] = []
        while True:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member is field:
                break
        components.append(tuple(component))

    for field in fields:
        if field not in indexes:
            visit(field)
    return components


def _bare_name_references(expression: Expression) -> Iterator[str]:
    """Yield bare value names without treating call targets as dependencies."""

    if isinstance(expression, NameExpr):
        yield expression.name
    elif isinstance(expression, CallExpr):
        for argument in expression.arguments:
            yield from _bare_name_references(argument)
    elif isinstance(expression, UnaryExpr):
        yield from _bare_name_references(expression.operand)
    elif isinstance(expression, (BinaryExpr, ComparisonExpr)):
        yield from _bare_name_references(expression.left)
        yield from _bare_name_references(expression.right)
    elif isinstance(expression, BetweenExpr):
        yield from _bare_name_references(expression.value)
        yield from _bare_name_references(expression.lower)
        yield from _bare_name_references(expression.upper)
    elif isinstance(expression, IsNullExpr):
        yield from _bare_name_references(expression.value)
    elif isinstance(expression, (LiteralExpr, DottedNameExpr)):
        return
    else:
        raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


def _cycle_diagnostic(field: FieldDef) -> Diagnostic:
    """Report a cyclic component at its earliest field in source order."""

    span = field.span
    return Diagnostic(
        code="PIE-S2504",
        severity=Severity.ERROR,
        message=f"Derived field cycle involving {field.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
