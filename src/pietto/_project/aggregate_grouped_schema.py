"""Private project aggregate/grouped row-schema candidate helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
)
from pietto._project.row_expression_type_facts import (
    build_project_row_expression_value_types,
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
)
from pietto.errors import SourceLocation
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    is_direct_field_argument,
    is_supported_semantic_aggregate_argument_expression,
    is_supported_semantic_aggregate_arity,
    nested_semantic_aggregate,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
)
from pietto.semantic.let_bindings import admitted_relation_let_expressions
from pietto.semantic.model import EffectiveNullability, TypeKind, ValueTypeKind


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


@dataclass(frozen=True, slots=True)
class ProjectAggregateSelectedResult:
    """One project-private aggregate selected-result candidate."""

    field: ProjectRowField
    fact: ProjectAggregateResultFact

    def __post_init__(self) -> None:
        """Reject malformed private aggregate selected-result candidates."""

        if not isinstance(self.field, ProjectRowField):
            raise ValueError("Aggregate selected result requires a row field")
        if not isinstance(self.fact, ProjectAggregateResultFact):
            raise ValueError("Aggregate selected result requires an aggregate fact")
        if self.field.result_role is not ProjectRowResultRole.AGGREGATE_RESULT:
            raise ValueError("Aggregate selected result requires AGGREGATE_RESULT role")
        if self.field.field_def is not None:
            raise ValueError(
                "Aggregate selected result cannot carry a field definition"
            )
        provenance = self.field.provenance
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.kind is not ProjectRowFieldProvenanceKind.AGGREGATE
        ):
            raise ValueError("Aggregate selected result requires AGGREGATE provenance")
        if self.field.name != self.fact.output_name:
            raise ValueError("Aggregate selected result output name mismatch")
        if (
            not isinstance(self.field.resolved_type, ProjectResolvedType)
            or not isinstance(
                self.field.resolved_type.kind,
                ProjectResolvedTypeKind,
            )
            or self.field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            raise ValueError("Aggregate selected result requires a concrete type")
        if (
            not isinstance(
                self.field.nullability,
                ProjectRowFieldNullability,
            )
            or self.field.nullability is ProjectRowFieldNullability.UNKNOWN
        ):
            raise ValueError("Aggregate selected result requires concrete nullability")


@dataclass(frozen=True, slots=True)
class ProjectAggregateSchemaFacts:
    """Complete unpersisted aggregate-only selected-result candidates."""

    selected_results: Mapping[SelectItem, ProjectAggregateSelectedResult]

    def __post_init__(self) -> None:
        """Freeze mappings and reject malformed aggregate candidate facts."""

        if not isinstance(self.selected_results, Mapping):
            raise ValueError("Aggregate schema facts require a selected-result mapping")
        selected_results = MappingProxyType(dict(self.selected_results))
        if not selected_results:
            raise ValueError(
                "Aggregate schema facts require non-empty selected results"
            )

        for item, selected_result in selected_results.items():
            if not isinstance(item, SelectItem):
                raise ValueError("Aggregate schema facts require select-item keys")
            if not isinstance(selected_result, ProjectAggregateSelectedResult):
                raise ValueError(
                    "Aggregate schema facts require selected-result values"
                )
            call = item.expression
            if not isinstance(call, CallExpr):
                raise ValueError(
                    "Aggregate schema facts require direct aggregate calls"
                )
            if (
                item.alias != selected_result.field.name
                or item.alias != selected_result.fact.output_name
            ):
                raise ValueError("Aggregate schema facts output identity mismatch")
            if semantic_aggregate_call_name(call) != selected_result.fact.function:
                raise ValueError("Aggregate schema facts canonical function mismatch")
            if selected_result.fact.grouped is not False:
                raise ValueError("Aggregate schema facts require ungrouped facts")
            if selected_result.fact.argument_count != len(call.arguments):
                raise ValueError("Aggregate schema facts argument count mismatch")
            provenance = selected_result.field.provenance
            if (
                provenance is None
                or selected_result.fact.location != provenance.location
            ):
                raise ValueError("Aggregate schema facts location mismatch")

        object.__setattr__(self, "selected_results", selected_results)


@dataclass(frozen=True, slots=True)
class ProjectGroupedSelectedResult:
    """One project-private grouped selected-result candidate."""

    field: ProjectRowField
    aggregate_fact: ProjectAggregateResultFact | None

    def __post_init__(self) -> None:
        """Reject malformed private grouped selected-result candidates."""

        if not isinstance(self.field, ProjectRowField):
            raise ValueError("Grouped selected result requires a row field")
        if self.field.result_role not in (
            ProjectRowResultRole.GROUP_KEY,
            ProjectRowResultRole.AGGREGATE_RESULT,
        ):
            raise ValueError(
                "Grouped selected result requires GROUP_KEY or AGGREGATE_RESULT role"
            )
        if (
            not isinstance(self.field.resolved_type, ProjectResolvedType)
            or not isinstance(
                self.field.resolved_type.kind,
                ProjectResolvedTypeKind,
            )
            or self.field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            raise ValueError("Grouped selected result requires a concrete type")
        if not isinstance(
            self.field.nullability,
            ProjectRowFieldNullability,
        ):
            raise ValueError("Grouped selected result requires valid nullability")

        provenance = self.field.provenance
        if self.field.result_role is ProjectRowResultRole.GROUP_KEY:
            if self.aggregate_fact is not None:
                raise ValueError("Grouped key result cannot carry an aggregate fact")
            if (
                not isinstance(provenance, ProjectRowFieldProvenance)
                or provenance.kind
                is not ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
            ):
                raise ValueError(
                    "Grouped key result requires DIRECT_PROJECTION provenance"
                )
            return

        if not isinstance(self.aggregate_fact, ProjectAggregateResultFact):
            raise ValueError("Grouped aggregate result requires an aggregate fact")
        if self.field.nullability is ProjectRowFieldNullability.UNKNOWN:
            raise ValueError("Grouped aggregate result requires concrete nullability")
        if self.field.field_def is not None:
            raise ValueError("Grouped aggregate result cannot carry a field definition")
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.kind is not ProjectRowFieldProvenanceKind.AGGREGATE
        ):
            raise ValueError("Grouped aggregate result requires AGGREGATE provenance")
        if self.field.name != self.aggregate_fact.output_name:
            raise ValueError("Grouped aggregate result output name mismatch")
        if self.aggregate_fact.grouped is not True:
            raise ValueError("Grouped aggregate result requires a grouped fact")


@dataclass(frozen=True, slots=True)
class ProjectGroupedSchemaFacts:
    """Complete unpersisted grouped selected-result candidates."""

    group_keys: tuple[ProjectGroupKeyFact, ...]
    selected_results: Mapping[SelectItem, ProjectGroupedSelectedResult]

    def __post_init__(self) -> None:
        """Freeze mappings and reject malformed grouped candidate facts."""

        if type(self.group_keys) is not tuple or not self.group_keys:
            raise ValueError("Grouped schema facts require non-empty tuple keys")
        group_keys_by_identity: dict[str, ProjectGroupKeyFact] = {}
        for fact in self.group_keys:
            if not isinstance(fact, ProjectGroupKeyFact):
                raise ValueError("Grouped schema facts require group-key facts")
            if fact.field_identity in group_keys_by_identity:
                raise ValueError("Grouped schema facts require unique key identities")
            group_keys_by_identity[fact.field_identity] = fact

        if not isinstance(self.selected_results, Mapping):
            raise ValueError("Grouped schema facts require a selected-result mapping")
        selected_results = MappingProxyType(dict(self.selected_results))
        if not selected_results:
            raise ValueError("Grouped schema facts require non-empty selected results")

        aggregate_count = 0
        for item, selected_result in selected_results.items():
            if not isinstance(item, SelectItem):
                raise ValueError("Grouped schema facts require select-item keys")
            if not isinstance(selected_result, ProjectGroupedSelectedResult):
                raise ValueError(
                    "Grouped schema facts require grouped selected-result values"
                )

            if selected_result.aggregate_fact is None:
                identity = _direct_expression_identity(item.expression)
                key_fact = (
                    None if identity is None else group_keys_by_identity.get(identity)
                )
                if key_fact is None:
                    raise ValueError(
                        "Grouped key result requires a resolved group-key identity"
                    )
                if selected_result.field.name != (item.alias or identity):
                    raise ValueError("Grouped key result output identity mismatch")
                if (
                    selected_result.field.resolved_type
                    != key_fact.input_field.resolved_type
                    or selected_result.field.nullability
                    is not key_fact.input_field.nullability
                    or selected_result.field.field_def != key_fact.input_field.field_def
                ):
                    raise ValueError("Grouped key result input field mismatch")
                continue

            aggregate_count += 1
            call = item.expression
            if not isinstance(call, CallExpr):
                raise ValueError(
                    "Grouped aggregate result requires a direct aggregate call"
                )
            fact = selected_result.aggregate_fact
            if (
                item.alias != selected_result.field.name
                or item.alias != fact.output_name
            ):
                raise ValueError("Grouped aggregate result output identity mismatch")
            if semantic_aggregate_call_name(call) != fact.function:
                raise ValueError("Grouped aggregate result canonical function mismatch")
            if fact.grouped is not True:
                raise ValueError("Grouped aggregate result requires grouped facts")
            if fact.argument_count != len(call.arguments):
                raise ValueError("Grouped aggregate result argument count mismatch")
            provenance = selected_result.field.provenance
            if provenance is None or fact.location != provenance.location:
                raise ValueError("Grouped aggregate result location mismatch")

        if aggregate_count == 0:
            raise ValueError("Grouped schema facts require an aggregate result")

        object.__setattr__(self, "selected_results", selected_results)


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


def build_project_aggregate_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateSchemaFacts | None:
    """Build complete aggregate-only candidates without publishing a schema."""

    if (
        definition.group_by_clause is not None
        or input_schema.is_unknown
        or not definition.select_items
    ):
        return None

    selected_results: dict[SelectItem, ProjectAggregateSelectedResult] = {}
    for item in definition.select_items:
        selected_result = _build_project_aggregate_selected_result(
            definition=definition,
            item=item,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
        )
        if selected_result is None:
            return None
        selected_results[item] = selected_result

    return ProjectAggregateSchemaFacts(selected_results=selected_results)


def build_project_grouped_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupedSchemaFacts | None:
    """Build complete grouped candidates without publishing a row schema."""

    if definition.group_by_clause is None:
        raise ValueError("Project grouped schema facts require GROUP BY")
    if input_schema.is_unknown or not definition.select_items:
        return None

    group_key_facts = build_project_group_key_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
    )
    if group_key_facts is None or not group_key_facts.group_keys:
        return None

    selected_results: dict[SelectItem, ProjectGroupedSelectedResult] = {}
    aggregate_count = 0
    for item in definition.select_items:
        if item in selected_results:
            return None
        group_key_field = group_key_facts.selected_fields.get(item)
        aggregate_result = _build_project_aggregate_selected_result(
            definition=definition,
            item=item,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
        )
        if (group_key_field is None) == (aggregate_result is None):
            return None
        if group_key_field is not None:
            selected_result = ProjectGroupedSelectedResult(
                field=group_key_field,
                aggregate_fact=None,
            )
        else:
            assert aggregate_result is not None
            aggregate_count += 1
            selected_result = ProjectGroupedSelectedResult(
                field=aggregate_result.field,
                aggregate_fact=aggregate_result.fact,
            )
        selected_results[item] = selected_result

    if aggregate_count == 0 or len(selected_results) != len(definition.select_items):
        return None

    return ProjectGroupedSchemaFacts(
        group_keys=group_key_facts.group_keys,
        selected_results=selected_results,
    )


def _build_project_aggregate_selected_result(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateSelectedResult | None:
    """Build one current direct aggregate selected-result candidate."""

    call = item.expression
    if not isinstance(call, CallExpr):
        return None

    function_name = semantic_aggregate_call_name(call)
    if function_name is None:
        return None
    output_name = item.alias
    if not output_name:
        return None
    if nested_semantic_aggregate(call) is not None:
        return None

    arguments = call.arguments
    if not is_supported_semantic_aggregate_arity(
        function_name,
        len(arguments),
    ):
        return None

    argument_type = None
    if arguments:
        if len(arguments) != 1:
            return None
        argument = arguments[0]
        if not is_direct_field_argument(argument):
            return None
        argument_value_types = build_project_row_expression_value_types(
            expressions=(argument,),
            input_schema=input_schema,
            relation_qualifier=definition.from_clause.source_name,
        )
        if len(argument_value_types) != 1:
            return None
        argument_type = argument_value_types.get(argument)
        if argument_type is None or argument_type.kind is not ValueTypeKind.KNOWN:
            return None
        if not is_supported_semantic_aggregate_argument_expression(
            function_name,
            argument,
            argument_type,
        ):
            return None

    result_type = semantic_projection_aggregate_result_value_type(
        function_name,
        argument_type,
    )
    if (
        result_type is None
        or result_type.kind is not ValueTypeKind.KNOWN
        or result_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    if result_type.nullability is EffectiveNullability.NON_NULL:
        project_nullability = ProjectRowFieldNullability.NON_NULL
    elif result_type.nullability is EffectiveNullability.NULLABLE:
        project_nullability = ProjectRowFieldNullability.NULLABLE
    else:
        return None

    location = _expression_location(call, fallback_path=fallback_path)
    field = ProjectRowField(
        name=output_name,
        resolved_type=ProjectResolvedType(
            name=result_type.resolved_type.name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=project_nullability,
        field_def=None,
        provenance=ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.AGGREGATE,
            symbol=upstream_symbol,
            location=location,
        ),
        result_role=ProjectRowResultRole.AGGREGATE_RESULT,
    )
    fact = ProjectAggregateResultFact(
        function=function_name,
        output_name=output_name,
        grouped=definition.group_by_clause is not None,
        argument_count=len(arguments),
        location=location,
    )
    return ProjectAggregateSelectedResult(
        field=field,
        fact=fact,
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
    expression: Expression,
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
