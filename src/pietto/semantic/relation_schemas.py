"""Minimal row schema propagation for table and query definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    DottedNameExpr,
    FromClause,
    NameExpr,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    CheckMode,
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
)

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

_UNKNOWN_RESOLVED_TYPE = ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN)


def propagate_relation_schemas(
    script: Script,
    *,
    mode: CheckMode,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    cyclic_relations: set[DerivedRelation],
) -> tuple[dict[DerivedRelation, RowSchema], list[Diagnostic]]:
    """Propagate stable projection names through table and query relations."""

    schemas: dict[DerivedRelation, RowSchema] = {}
    diagnostics: list[Diagnostic] = []
    visiting: set[DerivedRelation] = set()

    def infer(definition: DerivedRelation) -> RowSchema:
        if definition in schemas:
            return schemas[definition]
        if definition in cyclic_relations:
            schema, relation_diagnostics = _project_schema(
                definition,
                _unknown_schema(),
                mode=mode,
            )
            schemas[definition] = schema
            diagnostics.extend(relation_diagnostics)
            return schema
        if definition in visiting:
            return _unknown_schema()

        visiting.add(definition)
        target = from_resolutions.get(definition.from_clause)
        if isinstance(target, SourceDef):
            input_schema = source_row_schemas[target]
        elif isinstance(target, (TableDef, QueryDef)):
            input_schema = infer(target)
        else:
            input_schema = _unknown_schema()

        schema, relation_diagnostics = _project_schema(
            definition,
            input_schema,
            mode=mode,
        )
        visiting.remove(definition)
        schemas[definition] = schema
        diagnostics.extend(relation_diagnostics)
        return schema

    for definition in script.definitions:
        if isinstance(definition, (TableDef, QueryDef)):
            infer(definition)

    return schemas, diagnostics


def _project_schema(
    definition: DerivedRelation,
    input_schema: RowSchema,
    *,
    mode: CheckMode,
) -> tuple[RowSchema, list[Diagnostic]]:
    """Build ordered output fields from stable projection names."""

    fields: dict[str, RowField] = {}
    seen_names: set[str] = set()
    diagnostics: list[Diagnostic] = []
    named_items: list[tuple[SelectItem, str]] = []

    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            diagnostic = _unnamed_projection_diagnostic(item, mode)
            if diagnostic is not None:
                diagnostics.append(diagnostic)
            continue

        if output_name in seen_names:
            diagnostics.append(_duplicate_projection_diagnostic(item, output_name))
            continue
        seen_names.add(output_name)
        named_items.append((item, output_name))

    has_unknown_field = False
    for item, output_name in named_items:
        expression = item.expression
        if input_schema.is_unknown:
            fields[output_name] = _unknown_row_field(output_name)
            continue

        input_field = _projection_input_field(
            definition,
            item,
            input_schema,
        )
        if input_field is None:
            if item.alias is None and isinstance(expression, NameExpr):
                diagnostics.append(_unknown_field_diagnostic(expression))
                has_unknown_field = True
            elif isinstance(expression, DottedNameExpr):
                has_unknown_field = True
            fields[output_name] = _unknown_row_field(output_name)
            continue
        fields[output_name] = _projected_row_field(output_name, input_field)

    return RowSchema(
        fields=fields,
        is_unknown=input_schema.is_unknown or has_unknown_field,
    ), diagnostics


def _projection_input_field(
    definition: DerivedRelation,
    item: SelectItem,
    input_schema: RowSchema,
) -> RowField | None:
    """Return the input field referenced by a simple projection, if any."""

    expression = item.expression
    if item.alias is None and isinstance(expression, NameExpr):
        return input_schema.fields.get(expression.name)
    if isinstance(expression, DottedNameExpr):
        return _qualified_projection_input_field(
            definition,
            expression,
            input_schema,
        )
    return None


def _qualified_projection_input_field(
    definition: DerivedRelation,
    expression: DottedNameExpr,
    input_schema: RowSchema,
) -> RowField | None:
    """Resolve a two-part projection against the sole relation input."""

    if (
        len(expression.parts) != 2
        or expression.parts[0] != definition.from_clause.source_name
    ):
        return None
    return input_schema.fields.get(expression.parts[1])


def _projected_row_field(output_name: str, input_field: RowField) -> RowField:
    """Preserve input field facts while honoring the projection output name."""

    if output_name == input_field.name:
        return input_field
    return RowField(
        name=output_name,
        resolved_type=input_field.resolved_type,
        nullability=input_field.nullability,
        definition=input_field.definition,
    )


def _projection_output_name(item: SelectItem) -> str | None:
    """Return a projection's stable public output name, when one exists."""

    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _unknown_row_field(name: str) -> RowField:
    """Create a named output field whose expression type is not inferred yet."""

    return RowField(
        name=name,
        resolved_type=_UNKNOWN_RESOLVED_TYPE,
        nullability=EffectiveNullability.UNKNOWN,
    )


def _unknown_schema() -> RowSchema:
    """Create an immutable Unknown row schema."""

    return RowSchema(is_unknown=True)


def _unknown_field_diagnostic(expression: NameExpr) -> Diagnostic:
    """Report an unknown bare projection field at its expression span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {expression.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unnamed_projection_diagnostic(
    item: SelectItem,
    mode: CheckMode,
) -> Diagnostic | None:
    """Apply the mode-sensitive policy for unnamed computed projections."""

    if mode is CheckMode.LOOSE:
        return None
    severity = Severity.WARNING if mode is CheckMode.CHECKED else Severity.ERROR
    span = item.span
    return Diagnostic(
        code="PIE-S2304",
        severity=severity,
        message="Computed projection requires an explicit alias",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _duplicate_projection_diagnostic(
    item: SelectItem,
    output_name: str,
) -> Diagnostic:
    """Report a repeated projection output name at the later select item."""

    span = item.span
    return Diagnostic(
        code="PIE-S2305",
        severity=Severity.ERROR,
        message=f"Duplicate projection field: {output_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
