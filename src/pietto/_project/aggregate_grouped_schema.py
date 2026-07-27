"""Private project aggregate/grouped row-schema candidate helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
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
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import SourceLocation
from pietto.semantic.aggregates import (
    MAX_AGGREGATE_NAME,
    MIN_AGGREGATE_NAME,
    aggregate_argument_can_use_let_scope,
    contains_semantic_aggregate,
    effective_semantic_aggregate_argument_expression,
    is_supported_semantic_aggregate_argument,
    is_supported_semantic_aggregate_argument_expression,
    is_supported_semantic_aggregate_arity,
    nested_semantic_aggregate,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
)
from pietto.semantic.let_bindings import admitted_relation_let_expressions
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)


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


_AggregateGroupedSchemaFacts = (
    ProjectGroupKeySchemaFacts | ProjectAggregateSchemaFacts | ProjectGroupedSchemaFacts
)

_AGGREGATE_GROUPED_ATTEMPT_FAILURE_REASONS = frozenset(
    {
        ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
    }
)


@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedCandidateAttempt:
    """One complete candidate or one exact helper-local failure reason."""

    facts: _AggregateGroupedSchemaFacts | None
    failure_reason: ProjectRelationRowSchemaReason | None

    def __post_init__(self) -> None:
        """Require exactly one well-formed attempt outcome."""

        if (self.facts is None) == (self.failure_reason is None):
            raise ValueError(
                "Aggregate/grouped candidate attempt requires exactly one outcome"
            )
        if self.facts is not None and not isinstance(
            self.facts,
            (
                ProjectGroupKeySchemaFacts,
                ProjectAggregateSchemaFacts,
                ProjectGroupedSchemaFacts,
            ),
        ):
            raise ValueError(
                "Aggregate/grouped candidate attempt requires candidate facts"
            )
        if self.failure_reason is not None:
            if not isinstance(
                self.failure_reason,
                ProjectRelationRowSchemaReason,
            ):
                raise ValueError(
                    "Aggregate/grouped candidate attempt requires a failure reason"
                )
            if self.failure_reason not in _AGGREGATE_GROUPED_ATTEMPT_FAILURE_REASONS:
                raise ValueError(
                    "Aggregate/grouped candidate attempt has invalid failure reason"
                )


@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedSchemaFinalization:
    """Atomic unpersisted aggregate/grouped schema and aggregate-fact decision."""

    state: ProjectRelationRowSchemaState
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact]

    def __post_init__(self) -> None:
        """Freeze facts and enforce state/schema/fact atomicity."""

        if not isinstance(self.state, ProjectRelationRowSchemaState):
            raise ValueError("Aggregate/grouped finalization requires a state")
        if not isinstance(self.aggregate_result_facts, Mapping):
            raise ValueError("Aggregate/grouped finalization requires a fact mapping")
        aggregate_result_facts = MappingProxyType(dict(self.aggregate_result_facts))
        object.__setattr__(
            self,
            "aggregate_result_facts",
            aggregate_result_facts,
        )

        status = self.state.status
        reason = self.state.reason
        if status is ProjectRelationRowSchemaStatus.UNKNOWN:
            if reason not in {
                ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
                ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
                ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
                ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
            }:
                raise ValueError(
                    "Unknown aggregate/grouped finalization reason mismatch"
                )
            schema = self.state.schema
            if schema is None or schema.fields or not schema.is_unknown:
                raise ValueError(
                    "Unknown aggregate/grouped finalization requires empty unknown schema"
                )
            if aggregate_result_facts:
                raise ValueError(
                    "Unknown aggregate/grouped finalization cannot carry facts"
                )
            return

        if status is ProjectRelationRowSchemaStatus.DEFERRED:
            if reason not in {
                ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
                ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
            }:
                raise ValueError(
                    "Deferred aggregate/grouped finalization reason mismatch"
                )
            if aggregate_result_facts:
                raise ValueError(
                    "Deferred aggregate/grouped finalization cannot carry facts"
                )
            return

        if status is ProjectRelationRowSchemaStatus.BLOCKED:
            if reason not in {
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
                ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
            }:
                raise ValueError(
                    "Blocked aggregate/grouped finalization reason mismatch"
                )
            if aggregate_result_facts:
                raise ValueError(
                    "Blocked aggregate/grouped finalization cannot carry facts"
                )
            return

        if status is not ProjectRelationRowSchemaStatus.CONCRETE:
            raise ValueError("Aggregate/grouped finalization has unsupported status")
        if reason not in {
            ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
            ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        }:
            raise ValueError("Concrete aggregate/grouped finalization reason mismatch")
        schema = self.state.schema
        if schema is None or schema.is_unknown or not schema.fields:
            raise ValueError(
                "Concrete aggregate/grouped finalization requires non-empty schema"
            )

        expected_fact_names: list[str] = []
        has_group_key = False
        provenance_symbol: ProjectSymbol | None = None
        for output_name, field in schema.fields.items():
            if output_name != field.name:
                raise ValueError(
                    "Aggregate/grouped finalization schema identity mismatch"
                )
            provenance = field.provenance
            if not isinstance(provenance, ProjectRowFieldProvenance) or not isinstance(
                provenance.symbol, ProjectSymbol
            ):
                raise ValueError(
                    "Aggregate/grouped finalization requires provenance symbol"
                )
            if provenance_symbol is None:
                provenance_symbol = provenance.symbol
            elif provenance.symbol is not provenance_symbol:
                raise ValueError(
                    "Aggregate/grouped finalization has conflicting provenance symbols"
                )
            if field.result_role is ProjectRowResultRole.GROUP_KEY:
                has_group_key = True
                if output_name in aggregate_result_facts:
                    raise ValueError(
                        "Aggregate/grouped finalization group key cannot carry fact"
                    )
                if not _group_key_field_is_concrete_ready(field):
                    raise ValueError(
                        "Aggregate/grouped finalization has invalid group key"
                    )
                continue
            if field.result_role is not ProjectRowResultRole.AGGREGATE_RESULT:
                raise ValueError(
                    "Aggregate/grouped finalization has unsupported field role"
                )
            fact = aggregate_result_facts.get(output_name)
            if fact is None or fact.output_name != output_name:
                raise ValueError(
                    "Aggregate/grouped finalization aggregate fact mismatch"
                )
            if not _aggregate_field_fact_is_concrete_ready(field, fact):
                raise ValueError(
                    "Aggregate/grouped finalization has invalid aggregate field"
                )
            expected_fact_names.append(output_name)

        if not expected_fact_names:
            raise ValueError(
                "Concrete aggregate/grouped finalization requires aggregate facts"
            )
        if tuple(aggregate_result_facts) != tuple(expected_fact_names):
            raise ValueError(
                "Aggregate/grouped finalization requires exact aggregate facts"
            )
        grouped_flags = {fact.grouped for fact in aggregate_result_facts.values()}
        if len(grouped_flags) != 1 or (has_group_key and grouped_flags != {True}):
            raise ValueError(
                "Aggregate/grouped finalization has conflicting grouped facts"
            )
        assert provenance_symbol is not None
        if _project_relation_topology_reason(provenance_symbol) is not reason:
            raise ValueError(
                "Aggregate/grouped finalization provenance topology mismatch"
            )


@dataclass(frozen=True, slots=True)
class _ProjectAggregateSelectedResultAttempt:
    result: ProjectAggregateSelectedResult | None
    failure_reason: ProjectRelationRowSchemaReason | None

    def __post_init__(self) -> None:
        if (self.result is None) == (self.failure_reason is None):
            raise ValueError(
                "Aggregate selected-result attempt requires exactly one outcome"
            )


@dataclass(frozen=True, slots=True)
class _ProjectAggregateArgumentTypeAttempt:
    value_type: ValueType | None
    failure_reason: ProjectRelationRowSchemaReason | None

    def __post_init__(self) -> None:
        if (self.value_type is None) == (self.failure_reason is None):
            raise ValueError(
                "Aggregate argument-type attempt requires exactly one outcome"
            )


def build_project_group_key_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupKeySchemaFacts | None:
    """Build complete group-key candidates without publishing a row schema."""

    attempt = _build_project_group_key_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
    )
    if isinstance(attempt.facts, ProjectGroupKeySchemaFacts):
        return attempt.facts
    return None


def _build_project_group_key_schema_attempt(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedCandidateAttempt:
    """Build one structured group-key candidate attempt."""

    group_by_clause = definition.group_by_clause
    if group_by_clause is None:
        raise ValueError("Project group-key schema facts require GROUP BY")
    if input_schema.is_unknown:
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
        )
    if len(set(definition.select_items)) != len(definition.select_items):
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )

    let_expressions = (
        let_scope_facts.binding_expressions
        if let_scope_facts is not None
        else admitted_relation_let_expressions(
            definition,
            project_row_schema_to_semantic_row_schema(input_schema),
        )
    )
    group_keys: list[ProjectGroupKeyFact] = []
    declared_group_identities: set[str] = set()
    group_key_identities: set[str] = set()
    failure_reasons: list[ProjectRelationRowSchemaReason] = []
    for item in group_by_clause.items:
        effective_expression = _effective_group_key_expression(
            item.key,
            let_expressions=let_expressions,
            let_stack=frozenset(),
        )
        declared_identity = _direct_expression_identity(
            effective_expression,
            relation_qualifier=definition.from_clause.source_name,
        )
        if declared_identity is not None:
            if declared_identity in declared_group_identities:
                failure_reasons.append(
                    ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY
                )
            declared_group_identities.add(declared_identity)
        resolved = _resolve_input_field(
            definition,
            effective_expression,
            input_schema,
        )
        if resolved is None:
            failure_reasons.append(
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            )
            continue
        field_identity, input_field = resolved
        if (
            input_field.name != field_identity
            or input_field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            failure_reasons.append(
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            )
            continue
        if field_identity in group_key_identities:
            continue
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
    seen_items: set[SelectItem] = set()
    for item in definition.select_items:
        if item in seen_items:
            failure_reasons.append(
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
            )
            continue
        seen_items.add(item)
        selected_expression = item.expression
        if type(selected_expression) is WindowExpr:
            continue
        if contains_semantic_aggregate(selected_expression):
            continue
        if not isinstance(
            selected_expression,
            (NameExpr, DottedNameExpr),
        ):
            failure_reasons.append(
                ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
            )
            continue

        resolved = _resolve_input_field(
            definition,
            selected_expression,
            input_schema,
        )
        if resolved is None:
            failure_reasons.append(
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            )
            continue
        field_identity, input_field = resolved
        if input_field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN:
            failure_reasons.append(
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            )
            continue
        if field_identity not in declared_group_identities:
            failure_reasons.append(
                ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
            )
            continue
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

    failure_reason = _candidate_failure_reason(failure_reasons)
    if failure_reason is not None:
        return _failed_candidate_attempt(failure_reason)

    return ProjectAggregateGroupedCandidateAttempt(
        facts=ProjectGroupKeySchemaFacts(
            group_keys=tuple(group_keys),
            selected_fields=selected_fields,
        ),
        failure_reason=None,
    )


def build_project_aggregate_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectAggregateSchemaFacts | None:
    """Build complete aggregate-only candidates without publishing a schema."""

    # The structured attempt owns _build_project_aggregate_let_scope_facts.
    attempt = _build_project_aggregate_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
    )
    if isinstance(attempt.facts, ProjectAggregateSchemaFacts):
        return attempt.facts
    return None


def _build_project_aggregate_schema_attempt(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedCandidateAttempt:
    """Build one structured aggregate-only candidate attempt."""

    if definition.group_by_clause is not None or not definition.select_items:
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )
    if any(type(item.expression) is WindowExpr for item in definition.select_items):
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )
    if input_schema.is_unknown:
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
        )
    if len(set(definition.select_items)) != len(definition.select_items):
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )

    structural_failure_reasons = [
        reason
        for item in definition.select_items
        if type(item.expression) is not WindowExpr
        if (reason := _aggregate_selected_structure_failure_reason(item)) is not None
    ]

    let_scope_facts, let_failure_reason = _build_project_aggregate_let_scope_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope_facts=let_scope_facts,
    )
    if let_scope_facts is None:
        assert let_failure_reason is not None
        failure_reason = _candidate_failure_reason(
            [*structural_failure_reasons, let_failure_reason]
        )
        assert failure_reason is not None
        return _failed_candidate_attempt(failure_reason)

    selected_occurrences: list[tuple[SelectItem, ProjectAggregateSelectedResult]] = []
    failure_reasons = list(structural_failure_reasons)
    if let_failure_reason is not None:
        failure_reasons.append(let_failure_reason)
    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            continue
        selected_attempt = _build_project_aggregate_selected_result_attempt(
            definition=definition,
            item=item,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            let_scope_facts=let_scope_facts,
            fallback_path=fallback_path,
        )
        if selected_attempt.result is None:
            assert selected_attempt.failure_reason is not None
            failure_reasons.append(selected_attempt.failure_reason)
            continue
        selected_occurrences.append((item, selected_attempt.result))

    failure_reason = _candidate_failure_reason(failure_reasons)
    if failure_reason is not None:
        return _failed_candidate_attempt(failure_reason)

    return ProjectAggregateGroupedCandidateAttempt(
        facts=ProjectAggregateSchemaFacts(selected_results=dict(selected_occurrences)),
        failure_reason=None,
    )


def build_project_grouped_schema_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
) -> ProjectGroupedSchemaFacts | None:
    """Build complete grouped candidates without publishing a row schema."""

    # The structured attempt owns _build_project_aggregate_let_scope_facts.
    attempt = _build_project_grouped_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
    )
    if isinstance(attempt.facts, ProjectGroupedSchemaFacts):
        return attempt.facts
    return None


def build_project_aggregate_grouped_schema_finalization(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedSchemaFinalization:
    """Finalize one complete candidate without publishing it to the model."""

    if definition.group_by_clause is None:
        attempt = _build_project_aggregate_schema_attempt(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
            let_scope_facts=let_scope_facts,
        )
    else:
        attempt = _build_project_grouped_schema_attempt(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
            let_scope_facts=let_scope_facts,
        )
    return _finalize_project_aggregate_grouped_candidate(
        definition=definition,
        upstream_symbol=upstream_symbol,
        attempt=attempt,
    )


def _build_project_grouped_schema_attempt(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedCandidateAttempt:
    """Build one structured grouped candidate attempt."""

    if definition.group_by_clause is None:
        raise ValueError("Project grouped schema facts require GROUP BY")
    if input_schema.is_unknown:
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
        )
    if not definition.select_items:
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )
    if len(set(definition.select_items)) != len(definition.select_items):
        return _failed_candidate_attempt(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )

    group_key_attempt = _build_project_group_key_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
        let_scope_facts=let_scope_facts,
    )
    group_key_facts = (
        group_key_attempt.facts
        if isinstance(group_key_attempt.facts, ProjectGroupKeySchemaFacts)
        else None
    )
    failure_reasons: list[ProjectRelationRowSchemaReason] = []
    if group_key_facts is None:
        assert group_key_attempt.failure_reason is not None
        failure_reasons.append(group_key_attempt.failure_reason)
    elif not group_key_facts.group_keys:
        failure_reasons.append(
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )

    declared_group_identities = _declared_group_key_identities(
        definition=definition,
        input_schema=input_schema,
        let_scope_facts=let_scope_facts,
    )
    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            continue
        group_key_field = (
            None
            if group_key_facts is None
            else group_key_facts.selected_fields.get(item)
        )
        selected_identity = _direct_expression_identity(
            item.expression,
            relation_qualifier=definition.from_clause.source_name,
        )
        is_group_key = group_key_field is not None or (
            group_key_facts is None and selected_identity in declared_group_identities
        )
        if is_group_key:
            continue
        structural_reason = _aggregate_selected_structure_failure_reason(item)
        if structural_reason is not None:
            failure_reasons.append(structural_reason)

    let_scope_facts, let_failure_reason = _build_project_aggregate_let_scope_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope_facts=let_scope_facts,
    )
    if let_scope_facts is None:
        assert let_failure_reason is not None
        failure_reasons.append(let_failure_reason)
        failure_reason = _candidate_failure_reason(failure_reasons)
        assert failure_reason is not None
        return _failed_candidate_attempt(failure_reason)
    if let_failure_reason is not None:
        failure_reasons.append(let_failure_reason)

    selected_occurrences: list[tuple[SelectItem, ProjectGroupedSelectedResult]] = []
    aggregate_count = 0
    aggregate_selection_count = 0
    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            continue
        group_key_field = (
            None
            if group_key_facts is None
            else group_key_facts.selected_fields.get(item)
        )
        if group_key_field is not None:
            selected_occurrences.append(
                (
                    item,
                    ProjectGroupedSelectedResult(
                        field=group_key_field,
                        aggregate_fact=None,
                    ),
                )
            )
            continue
        selected_identity = _direct_expression_identity(
            item.expression,
            relation_qualifier=definition.from_clause.source_name,
        )
        if group_key_facts is None and selected_identity in declared_group_identities:
            continue
        if contains_semantic_aggregate(item.expression):
            aggregate_selection_count += 1

        aggregate_attempt = _build_project_aggregate_selected_result_attempt(
            definition=definition,
            item=item,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            let_scope_facts=let_scope_facts,
            fallback_path=fallback_path,
        )
        if aggregate_attempt.result is None:
            assert aggregate_attempt.failure_reason is not None
            failure_reasons.append(aggregate_attempt.failure_reason)
            continue
        aggregate_result = aggregate_attempt.result
        aggregate_count += 1
        selected_occurrences.append(
            (
                item,
                ProjectGroupedSelectedResult(
                    field=aggregate_result.field,
                    aggregate_fact=aggregate_result.fact,
                ),
            )
        )

    if (
        aggregate_count == 0
        and aggregate_selection_count == 0
        and not failure_reasons
        and group_key_facts is not None
        and len(selected_occurrences) == len(_base_selected_items(definition))
    ):
        failure_reasons.append(
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
        )
    if (
        group_key_facts is not None
        and not failure_reasons
        and len(selected_occurrences) != len(_base_selected_items(definition))
    ):
        failure_reasons.append(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )

    failure_reason = _candidate_failure_reason(failure_reasons)
    if failure_reason is not None:
        return _failed_candidate_attempt(failure_reason)

    assert group_key_facts is not None
    return ProjectAggregateGroupedCandidateAttempt(
        facts=ProjectGroupedSchemaFacts(
            group_keys=group_key_facts.group_keys,
            selected_results=dict(selected_occurrences),
        ),
        failure_reason=None,
    )


def _project_relation_topology_reason(
    upstream_symbol: ProjectSymbol,
) -> ProjectRelationRowSchemaReason | None:
    definition = upstream_symbol.definition
    if (
        upstream_symbol.namespace is ProjectSymbolNamespace.RELATION
        and upstream_symbol.kind is ProjectSymbolKind.SOURCE
        and isinstance(definition, SourceDef)
    ):
        return ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    if (
        upstream_symbol.namespace is ProjectSymbolNamespace.RELATION
        and upstream_symbol.kind is ProjectSymbolKind.TABLE
        and isinstance(definition, TableDef)
    ) or (
        upstream_symbol.namespace is ProjectSymbolNamespace.RELATION
        and upstream_symbol.kind is ProjectSymbolKind.QUERY
        and isinstance(definition, QueryDef)
    ):
        return ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    return None


def _finalize_project_aggregate_grouped_candidate(
    *,
    definition: TableDef | QueryDef,
    upstream_symbol: ProjectSymbol,
    attempt: ProjectAggregateGroupedCandidateAttempt,
) -> ProjectAggregateGroupedSchemaFinalization:
    """Convert one structured attempt into an atomic helper-local decision."""

    concrete_reason = _project_relation_topology_reason(upstream_symbol)
    if concrete_reason is None:
        return _failed_schema_finalization(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )
    if attempt.failure_reason is not None:
        return _failed_schema_finalization(attempt.failure_reason)

    facts = attempt.facts
    if isinstance(facts, ProjectGroupKeySchemaFacts):
        return _failed_schema_finalization(
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
        )
    if not isinstance(facts, (ProjectAggregateSchemaFacts, ProjectGroupedSchemaFacts)):
        return _failed_schema_finalization(
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
        )

    occurrences, failure_reason = _aggregate_grouped_selected_occurrences(
        definition=definition,
        facts=facts,
        upstream_symbol=upstream_symbol,
    )
    if failure_reason is not None:
        return _failed_schema_finalization(failure_reason)

    output_names: set[str] = set()
    duplicate_output = False
    for field, _fact in occurrences:
        if field.name in output_names:
            duplicate_output = True
        output_names.add(field.name)
    if duplicate_output:
        return _failed_schema_finalization(
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
        )

    schema_fields: dict[str, ProjectRowField] = {}
    aggregate_result_facts: dict[str, ProjectAggregateResultFact] = {}
    for field, fact in occurrences:
        schema_fields[field.name] = field
        if fact is not None:
            aggregate_result_facts[field.name] = fact

    return ProjectAggregateGroupedSchemaFinalization(
        state=ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.CONCRETE,
            schema=ProjectRowSchema(fields=schema_fields, is_unknown=False),
            reason=concrete_reason,
        ),
        aggregate_result_facts=aggregate_result_facts,
    )


def _aggregate_grouped_selected_occurrences(
    *,
    definition: TableDef | QueryDef,
    facts: ProjectAggregateSchemaFacts | ProjectGroupedSchemaFacts,
    upstream_symbol: ProjectSymbol,
) -> tuple[
    tuple[tuple[ProjectRowField, ProjectAggregateResultFact | None], ...],
    ProjectRelationRowSchemaReason | None,
]:
    """Validate complete occurrence-level field/fact coherence before dicts."""

    base_selected_items = _base_selected_items(definition)
    if tuple(facts.selected_results) != base_selected_items:
        return (
            (),
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )

    occurrences: list[tuple[ProjectRowField, ProjectAggregateResultFact | None]] = []
    grouped_flags: set[bool] = set()
    for item in base_selected_items:
        selected_result = facts.selected_results.get(item)
        if isinstance(selected_result, ProjectAggregateSelectedResult):
            field = selected_result.field
            fact = selected_result.fact
        elif isinstance(selected_result, ProjectGroupedSelectedResult):
            field = selected_result.field
            fact = selected_result.aggregate_fact
        else:
            return (
                (),
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
            )

        provenance = field.provenance
        if (
            not isinstance(provenance, ProjectRowFieldProvenance)
            or provenance.symbol is not upstream_symbol
        ):
            return (
                (),
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
            )

        if field.result_role is ProjectRowResultRole.GROUP_KEY:
            if fact is not None or not _group_key_field_is_concrete_ready(field):
                return (
                    (),
                    ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
                )
            occurrences.append((field, None))
            continue

        if (
            not isinstance(field.resolved_type, ProjectResolvedType)
            or field.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
            or not isinstance(field.nullability, ProjectRowFieldNullability)
            or field.nullability is ProjectRowFieldNullability.UNKNOWN
            or fact is None
        ):
            return (
                (),
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
            )
        if not _aggregate_field_fact_is_concrete_ready(field, fact):
            return (
                (),
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
            )
        if fact.grouped != (definition.group_by_clause is not None):
            return (
                (),
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
            )
        grouped_flags.add(fact.grouped)
        occurrences.append((field, fact))

    if not grouped_flags or len(grouped_flags) != 1:
        return (
            (),
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )
    if any(
        field.result_role is ProjectRowResultRole.GROUP_KEY
        for field, _fact in occurrences
    ) and grouped_flags != {True}:
        return (
            (),
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )
    return tuple(occurrences), None


def _base_selected_items(
    definition: TableDef | QueryDef,
) -> tuple[SelectItem, ...]:
    """Return outputs owned by the pre-window project schema stage."""

    return tuple(
        item
        for item in definition.select_items
        if type(item.expression) is not WindowExpr
    )


def _aggregate_selected_structure_failure_reason(
    item: SelectItem,
) -> ProjectRelationRowSchemaReason | None:
    """Apply canonical aggregate identity and arity checks without type facts."""

    call = item.expression
    if not isinstance(call, CallExpr):
        return ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    function_name = semantic_aggregate_call_name(call)
    if function_name is None or not item.alias:
        return ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    if nested_semantic_aggregate(call) is not None:
        return ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    if not is_supported_semantic_aggregate_arity(
        function_name,
        len(call.arguments),
    ):
        return ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    return None


def _build_project_aggregate_selected_result(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts,
    fallback_path: str,
) -> ProjectAggregateSelectedResult | None:
    """Build one current accepted aggregate selected-result candidate."""

    attempt = _build_project_aggregate_selected_result_attempt(
        definition=definition,
        item=item,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope_facts=let_scope_facts,
        fallback_path=fallback_path,
    )
    return attempt.result


def _build_project_aggregate_selected_result_attempt(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts,
    fallback_path: str,
) -> _ProjectAggregateSelectedResultAttempt:
    """Build one aggregate result or retain its exact failure category."""

    structural_reason = _aggregate_selected_structure_failure_reason(item)
    if structural_reason is not None:
        return _failed_selected_result_attempt(structural_reason)

    call = item.expression
    assert isinstance(call, CallExpr)
    function_name = semantic_aggregate_call_name(call)
    assert function_name is not None
    output_name = item.alias
    assert output_name

    arguments = call.arguments
    argument_type: ValueType | None = None
    if arguments:
        assert len(arguments) == 1
        argument = arguments[0]
        argument_attempt = _project_aggregate_argument_type_attempt(
            definition=definition,
            function_name=function_name,
            argument=argument,
            input_schema=input_schema,
            let_scope_facts=let_scope_facts,
        )
        if argument_attempt.value_type is None:
            assert argument_attempt.failure_reason is not None
            return _failed_selected_result_attempt(argument_attempt.failure_reason)
        argument_type = argument_attempt.value_type

    result_type = semantic_projection_aggregate_result_value_type(
        function_name,
        argument_type,
    )
    if (
        result_type is None
        or result_type.kind is not ValueTypeKind.KNOWN
        or result_type.resolved_type.kind is not TypeKind.BUILTIN
    ):
        return _failed_selected_result_attempt(
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
        )
    if result_type.nullability is EffectiveNullability.NON_NULL:
        project_nullability = ProjectRowFieldNullability.NON_NULL
    elif result_type.nullability is EffectiveNullability.NULLABLE:
        project_nullability = ProjectRowFieldNullability.NULLABLE
    else:
        return _failed_selected_result_attempt(
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
        )

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
    return _ProjectAggregateSelectedResultAttempt(
        result=ProjectAggregateSelectedResult(
            field=field,
            fact=fact,
        ),
        failure_reason=None,
    )


def _build_project_aggregate_let_scope_facts(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> ProjectRelationLetScopeFacts | None:
    """Compatibility wrapper over structured let-scope classification."""

    # _build_project_aggregate_let_scope_attempt calls
    # build_project_relation_let_scope_facts at the exact failure source.
    facts, _failure_reason = _build_project_aggregate_let_scope_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
    )
    if _failure_reason is not None:
        return None
    return facts


def _build_project_aggregate_let_scope_attempt(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> tuple[ProjectRelationLetScopeFacts | None, ProjectRelationRowSchemaReason | None]:
    """Retain exact let-scope failure posture for aggregate candidates."""

    upstream_definition = upstream_symbol.definition
    if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
        return (
            None,
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )

    facts = let_scope_facts
    if facts is None:
        facts = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_definition=upstream_definition,
        )
    elif definition.let_clause is None:
        if (
            facts.status is not ProjectLetScopeFactsStatus.ABSENT
            or facts.clause is not None
        ):
            return (
                facts,
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
            )
    elif facts.clause is not definition.let_clause:
        return (
            facts,
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )
    if facts.status not in (
        ProjectLetScopeFactsStatus.ABSENT,
        ProjectLetScopeFactsStatus.CONCRETE,
    ):
        if facts.status is ProjectLetScopeFactsStatus.DEFERRED:
            reason = ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
        elif facts.status is ProjectLetScopeFactsStatus.BLOCKED:
            reason = ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED
        elif facts.reason is ProjectLetScopeFactsReason.UPSTREAM_UNKNOWN:
            reason = ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
        elif facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED:
            reason = ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        else:
            reason = (
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            )
        return facts, reason
    return facts, None


def _project_aggregate_argument_type(
    *,
    definition: TableDef | QueryDef,
    function_name: str,
    argument: Expression,
    input_schema: ProjectRowSchema,
    let_scope_facts: ProjectRelationLetScopeFacts,
) -> ValueType | None:
    """Compatibility wrapper over the structured argument-type attempt."""

    # The structured helper owns
    # effective_semantic_aggregate_argument_expression and
    # is_supported_semantic_aggregate_argument_expression checks.
    attempt = _project_aggregate_argument_type_attempt(
        definition=definition,
        function_name=function_name,
        argument=argument,
        input_schema=input_schema,
        let_scope_facts=let_scope_facts,
    )
    return attempt.value_type


def _project_aggregate_argument_type_attempt(
    *,
    definition: TableDef | QueryDef,
    function_name: str,
    argument: Expression,
    input_schema: ProjectRowSchema,
    let_scope_facts: ProjectRelationLetScopeFacts,
) -> _ProjectAggregateArgumentTypeAttempt:
    """Resolve one aggregate argument or retain its exact failure category."""

    let_expansions = (
        let_scope_facts.binding_expressions
        if let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )
    is_deferred_min_max = function_name in {
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
    }
    if (
        is_deferred_min_max
        and isinstance(argument, NameExpr)
        and let_expansions is not None
        and argument.name in let_expansions
    ):
        return _failed_argument_type_attempt(
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
        )
    effective_argument = effective_semantic_aggregate_argument_expression(
        function_name,
        argument,
        let_expansions=let_expansions,
    )
    is_direct_row_let = aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        let_expansions,
    )
    if is_direct_row_let:
        if (
            not isinstance(argument, NameExpr)
            or let_scope_facts.status is not ProjectLetScopeFactsStatus.CONCRETE
        ):
            return _failed_argument_type_attempt(
                ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
            )
        argument_type = let_scope_facts.value_types.get(argument.name)
    else:
        effective_value_types = build_project_row_expression_value_types(
            expressions=(effective_argument,),
            input_schema=input_schema,
            relation_qualifier=definition.from_clause.source_name,
        )
        argument_type = effective_value_types.get(effective_argument)

    if argument_type is None or argument_type.kind is not ValueTypeKind.KNOWN:
        return _failed_argument_type_attempt(
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
        )
    if not is_supported_semantic_aggregate_argument(
        function_name,
        argument_type,
    ):
        return _failed_argument_type_attempt(
            ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
        )
    if not is_supported_semantic_aggregate_argument_expression(
        function_name,
        argument,
        argument_type,
        let_expansions=let_expansions,
    ):
        reason = (
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
            if is_deferred_min_max
            else ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )
        return _failed_argument_type_attempt(reason)
    return _ProjectAggregateArgumentTypeAttempt(
        value_type=argument_type,
        failure_reason=None,
    )


def _failed_candidate_attempt(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectAggregateGroupedCandidateAttempt:
    return ProjectAggregateGroupedCandidateAttempt(
        facts=None,
        failure_reason=reason,
    )


def _failed_selected_result_attempt(
    reason: ProjectRelationRowSchemaReason,
) -> _ProjectAggregateSelectedResultAttempt:
    return _ProjectAggregateSelectedResultAttempt(
        result=None,
        failure_reason=reason,
    )


def _failed_argument_type_attempt(
    reason: ProjectRelationRowSchemaReason,
) -> _ProjectAggregateArgumentTypeAttempt:
    return _ProjectAggregateArgumentTypeAttempt(
        value_type=None,
        failure_reason=reason,
    )


def _candidate_failure_reason(
    reasons: list[ProjectRelationRowSchemaReason],
) -> ProjectRelationRowSchemaReason | None:
    """Choose one deterministic reason independent of occurrence order."""

    reason_set = set(reasons)
    for reason in (
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
    ):
        if reason in reason_set:
            return reason
    if reason_set:
        raise ValueError("Unsupported aggregate/grouped candidate failure reason")
    return None


def _failed_schema_finalization(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectAggregateGroupedSchemaFinalization:
    if reason in {
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    }:
        status = ProjectRelationRowSchemaStatus.UNKNOWN
        schema = ProjectRowSchema(fields={}, is_unknown=True)
    elif reason in {
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
    }:
        status = ProjectRelationRowSchemaStatus.DEFERRED
        schema = None
    elif reason in {
        ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
    }:
        status = ProjectRelationRowSchemaStatus.BLOCKED
        schema = None
    else:
        raise ValueError("Unsupported aggregate/grouped finalization failure reason")

    return ProjectAggregateGroupedSchemaFinalization(
        state=ProjectRelationRowSchemaState(
            status=status,
            schema=schema,
            reason=reason,
        ),
        aggregate_result_facts={},
    )


def _declared_group_key_identities(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> frozenset[str]:
    group_by_clause = definition.group_by_clause
    if group_by_clause is None:
        return frozenset()
    let_expressions = (
        let_scope_facts.binding_expressions
        if let_scope_facts is not None
        else admitted_relation_let_expressions(
            definition,
            project_row_schema_to_semantic_row_schema(input_schema),
        )
    )
    identities: set[str] = set()
    for item in group_by_clause.items:
        effective_expression = _effective_group_key_expression(
            item.key,
            let_expressions=let_expressions,
            let_stack=frozenset(),
        )
        identity = _direct_expression_identity(
            effective_expression,
            relation_qualifier=definition.from_clause.source_name,
        )
        if identity is not None:
            identities.add(identity)
    return frozenset(identities)


def _group_key_field_is_concrete_ready(field: ProjectRowField) -> bool:
    provenance = field.provenance
    return (
        field.result_role is ProjectRowResultRole.GROUP_KEY
        and isinstance(field.resolved_type, ProjectResolvedType)
        and isinstance(field.resolved_type.kind, ProjectResolvedTypeKind)
        and field.resolved_type.kind is not ProjectResolvedTypeKind.UNKNOWN
        and isinstance(field.nullability, ProjectRowFieldNullability)
        and isinstance(provenance, ProjectRowFieldProvenance)
        and provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def _aggregate_field_fact_is_concrete_ready(
    field: ProjectRowField,
    fact: ProjectAggregateResultFact,
) -> bool:
    provenance = field.provenance
    return (
        field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
        and isinstance(field.resolved_type, ProjectResolvedType)
        and field.resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
        and isinstance(field.nullability, ProjectRowFieldNullability)
        and field.nullability is not ProjectRowFieldNullability.UNKNOWN
        and field.field_def is None
        and isinstance(provenance, ProjectRowFieldProvenance)
        and provenance.kind is ProjectRowFieldProvenanceKind.AGGREGATE
        and isinstance(fact, ProjectAggregateResultFact)
        and field.name == fact.output_name
        and provenance.location == fact.location
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
