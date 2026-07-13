"""Private project aggregate/grouped row-schema candidate helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pietto._project.model import (
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
)
from pietto._project.row_expression_type_facts import (
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    GroupByItem,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
)
from pietto.errors import SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.let_bindings import admitted_relation_let_expressions


@dataclass(frozen=True, slots=True)
class ProjectGroupKeyFact:
    """One resolved project-private group-key candidate fact."""

    item: GroupByItem
    effective_expression: NameExpr | DottedNameExpr
    field_identity: str
    input_field: ProjectRowField

    def __post_init__(self) -> None:
        """Validate one resolved group-key candidate fact."""

        if not isinstance(self.item, GroupByItem):
            raise ValueError("Project group-key fact requires a group-by item")
        if not isinstance(self.effective_expression, (NameExpr, DottedNameExpr)):
            raise ValueError("Project group-key fact requires a direct expression")
        if type(self.field_identity) is not str or not self.field_identity:
            raise ValueError("Project group-key fact requires field identity")
        if not isinstance(self.input_field, ProjectRowField):
            raise ValueError("Project group-key fact requires input field")
        if self.field_identity != self.input_field.name:
            raise ValueError("Project group-key fact field identity mismatch")


@dataclass(frozen=True, slots=True)
class ProjectGroupKeySchemaFacts:
    """Complete private group-key candidates for one grouped relation."""

    group_keys: tuple[ProjectGroupKeyFact, ...]
    selected_fields: Mapping[SelectItem, ProjectRowField]

    def __post_init__(self) -> None:
        """Freeze mappings and reject malformed private candidate facts."""

        if type(self.group_keys) is not tuple:
            raise ValueError("Project group-key facts require a tuple")
        identities: set[str] = set()
        for fact in self.group_keys:
            if not isinstance(fact, ProjectGroupKeyFact):
                raise ValueError("Project group-key facts require fact values")
            if fact.field_identity in identities:
                raise ValueError("Project group-key facts require unique identities")
            identities.add(fact.field_identity)

        selected_fields = MappingProxyType(dict(self.selected_fields))
        for item, selected_field in selected_fields.items():
            if not isinstance(item, SelectItem):
                raise ValueError("Selected group-key fields require select-item keys")
            if not isinstance(selected_field, ProjectRowField):
                raise ValueError("Selected group-key fields require row-field values")
            if selected_field.result_role is not ProjectRowResultRole.GROUP_KEY:
                raise ValueError("Selected group-key fields require GROUP_KEY role")
            identity = _direct_expression_identity(item.expression)
            if identity is None or identity not in identities:
                raise ValueError(
                    "Selected group-key fields require a resolved group-key identity"
                )

        object.__setattr__(self, "selected_fields", selected_fields)


def build_project_group_key_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupKeySchemaFacts | None:
    """Build complete group-key candidates without publishing a row schema."""

    group_by_clause = definition.group_by_clause
    if group_by_clause is None:
        raise ValueError("Project group-key schema facts require GROUP BY")
    if input_schema.is_unknown:
        return None

    semantic_input_schema = project_row_schema_to_semantic_row_schema(input_schema)
    let_expressions = admitted_relation_let_expressions(
        definition,
        semantic_input_schema,
    )
    group_keys: list[ProjectGroupKeyFact] = []
    group_key_identities: set[str] = set()
    for item in group_by_clause.items:
        effective_expression = _effective_group_key_expression(
            item.key,
            let_expressions=let_expressions,
            let_stack=frozenset(),
        )
        resolved = _resolve_input_field(
            definition,
            effective_expression,
            input_schema,
        )
        if resolved is None:
            return None
        field_identity, input_field = resolved
        if (
            input_field.name != field_identity
            or input_field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            return None
        if field_identity in group_key_identities:
            return None
        group_key_identities.add(field_identity)
        group_keys.append(
            ProjectGroupKeyFact(
                item=item,
                effective_expression=effective_expression,
                field_identity=field_identity,
                input_field=input_field,
            )
        )

    selected_fields: dict[SelectItem, ProjectRowField] = {}
    for item in definition.select_items:
        selected_expression = item.expression
        if contains_semantic_aggregate(selected_expression):
            continue
        if not isinstance(
            selected_expression,
            (NameExpr, DottedNameExpr),
        ):
            return None

        resolved = _resolve_input_field(
            definition,
            selected_expression,
            input_schema,
        )
        if resolved is None:
            return None
        field_identity, input_field = resolved
        if field_identity not in group_key_identities:
            return None
        selected_fields[item] = ProjectRowField(
            name=item.alias or field_identity,
            resolved_type=input_field.resolved_type,
            nullability=input_field.nullability,
            field_def=input_field.field_def,
            provenance=ProjectRowFieldProvenance(
                kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
                symbol=upstream_symbol,
                location=_expression_location(
                    selected_expression,
                    fallback_path=fallback_path,
                ),
            ),
            result_role=ProjectRowResultRole.GROUP_KEY,
        )

    return ProjectGroupKeySchemaFacts(
        group_keys=tuple(group_keys),
        selected_fields=selected_fields,
    )


def _effective_group_key_expression(
    expression: NameExpr | DottedNameExpr,
    *,
    let_expressions: Mapping[str, Expression],
    let_stack: frozenset[str],
) -> NameExpr | DottedNameExpr:
    if not isinstance(expression, NameExpr):
        return expression
    if expression.name not in let_expressions or expression.name in let_stack:
        return expression

    expanded = let_expressions[expression.name]
    if isinstance(expanded, DottedNameExpr):
        return expanded
    if isinstance(expanded, NameExpr):
        return _effective_group_key_expression(
            expanded,
            let_expressions=let_expressions,
            let_stack=let_stack | frozenset((expression.name,)),
        )
    return expression


def _resolve_input_field(
    definition: TableDef | QueryDef,
    expression: object,
    input_schema: ProjectRowSchema,
) -> tuple[str, ProjectRowField] | None:
    identity = _direct_expression_identity(
        expression,
        relation_qualifier=definition.from_clause.source_name,
    )
    if identity is None:
        return None
    input_field = input_schema.fields.get(identity)
    if input_field is None:
        return None
    return identity, input_field


def _direct_expression_identity(
    expression: object,
    *,
    relation_qualifier: str | None = None,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name
    if not isinstance(expression, DottedNameExpr):
        return None
    if len(expression.parts) != 2:
        return None
    if relation_qualifier is not None and expression.parts[0] != relation_qualifier:
        return None
    return expression.parts[1]


def _expression_location(
    expression: NameExpr | DottedNameExpr,
    *,
    fallback_path: str,
) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
