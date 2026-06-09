"""Minimal row schema propagation for table and query definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    FromClause,
    NameExpr,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import RowField, RowSchema

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


def propagate_relation_schemas(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
) -> tuple[dict[DerivedRelation, RowSchema], list[Diagnostic]]:
    """Propagate bare field projections through table and query relations."""

    schemas: dict[DerivedRelation, RowSchema] = {}
    diagnostics: list[Diagnostic] = []
    visiting: set[DerivedRelation] = set()

    def infer(definition: DerivedRelation) -> RowSchema:
        if definition in schemas:
            return schemas[definition]
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

        schema, relation_diagnostics = _project_schema(definition, input_schema)
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
) -> tuple[RowSchema, list[Diagnostic]]:
    """Project simple bare fields or return Unknown for unsupported inputs."""

    if input_schema.is_unknown or any(
        item.alias is not None or not isinstance(item.expression, NameExpr)
        for item in definition.select_items
    ):
        return _unknown_schema(), []

    fields: dict[str, RowField] = {}
    seen_names: set[str] = set()
    diagnostics: list[Diagnostic] = []
    has_unknown_field = False

    for item in definition.select_items:
        expression = item.expression
        assert isinstance(expression, NameExpr)
        field_name = expression.name

        if field_name in seen_names:
            diagnostics.append(_duplicate_projection_diagnostic(item, field_name))
            continue
        seen_names.add(field_name)

        input_field = input_schema.fields.get(field_name)
        if input_field is None:
            diagnostics.append(_unknown_field_diagnostic(expression))
            has_unknown_field = True
            continue
        fields[field_name] = input_field

    if has_unknown_field:
        return _unknown_schema(), diagnostics
    return RowSchema(fields=fields), diagnostics


def _unknown_schema() -> RowSchema:
    """Create an immutable Unknown row schema."""

    return RowSchema(is_unknown=True)


def _unknown_field_diagnostic(expression: NameExpr) -> Diagnostic:
    """Report an unknown bare projection field at its expression span."""

    span = expression.span
    return Diagnostic(
        code="P2102",
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


def _duplicate_projection_diagnostic(
    item: SelectItem,
    field_name: str,
) -> Diagnostic:
    """Report a repeated bare projection at the later select item."""

    span = item.span
    return Diagnostic(
        code="P2305",
        severity=Severity.ERROR,
        message=f"Duplicate projection field: {field_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
