"""Private aggregate/grouped clause-readiness facts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateGroupedSchemaFinalization,
    ProjectGroupKeyFact,
    ProjectGroupKeySchemaFacts,
    _build_project_group_key_schema_attempt,
    build_project_aggregate_grouped_schema_finalization,
    build_project_group_key_schema_facts,
)
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
)
from pietto._project.row_expression_type_facts import (
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    contains_semantic_aggregate,
    effective_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.let_bindings import admitted_relation_let_expressions
from pietto.semantic.model import RowSchema, ValueType
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT
from pietto.semantic.satisfying import check_satisfying_clauses

__all__: tuple[str, ...] = ()

_DerivedRelation = TableDef | QueryDef


class ProjectRelationClauseDependencyKind(StrEnum):
    """Private kinds of immediate clause dependency."""

    GROUP_KEY_INPUT = "group_key_input"
    SATISFYING_OUTPUT = "satisfying_output"
    GROUPED_ORDER_OUTPUT = "grouped_order_output"


class ProjectAggregateGroupedClauseReadinessStatus(StrEnum):
    """Private aggregate/grouped clause-readiness states."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectAggregateGroupedClauseReadinessReason(StrEnum):
    """Private deterministic clause-readiness reasons."""

    CLAUSES_READY = "clauses_ready"
    SCHEMA_FINALIZATION_NON_CONCRETE = "schema_finalization_non_concrete"
    UNAVAILABLE_CLAUSE_DEPENDENCY = "unavailable_clause_dependency"
    INVALID_CLAUSE_OUTPUT_REFERENCE = "invalid_clause_output_reference"
    INVALID_CLAUSE_EXPRESSION = "invalid_clause_expression"
    UNSUPPORTED_CLAUSE_FAMILY = "unsupported_clause_family"
    MISSING_REQUIRED_CLAUSE_FACT = "missing_required_clause_fact"
    CONFLICTING_CLAUSE_FACTS = "conflicting_clause_facts"


@dataclass(frozen=True, slots=True)
class ProjectRelationClauseDependencyFact:
    """One exact immediate dependency retained by the private helper layer."""

    kind: ProjectRelationClauseDependencyKind
    source_occurrence: GroupByItem | Expression | OrderItem
    target_occurrence: ProjectGroupKeyFact | SelectItem
    target_field: ProjectRowField
    aggregate_result_fact: ProjectAggregateResultFact | None

    def __post_init__(self) -> None:
        """Validate local shape and identity invariants."""

        if not isinstance(self.kind, ProjectRelationClauseDependencyKind):
            raise ValueError("Clause dependency fact requires a kind")
        if not isinstance(self.target_field, ProjectRowField):
            raise ValueError("Clause dependency fact requires a target field")

        if self.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT:
            if not isinstance(self.source_occurrence, GroupByItem):
                raise ValueError("Group dependency requires a group-by source")
            if not isinstance(self.target_occurrence, ProjectGroupKeyFact):
                raise ValueError("Group dependency requires a group-key fact target")
            if self.target_occurrence.item is not self.source_occurrence:
                raise ValueError("Group dependency source/fact identity mismatch")
            if self.target_occurrence.input_field is not self.target_field:
                raise ValueError("Group dependency input-field identity mismatch")
            if self.aggregate_result_fact is not None:
                raise ValueError("Group dependency cannot carry an aggregate fact")
            return

        if not isinstance(self.target_occurrence, SelectItem):
            raise ValueError("Output dependency requires a select-item target")
        if self.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT:
            if not isinstance(self.source_occurrence, (NameExpr, CallExpr)):
                raise ValueError("Satisfying dependency requires an expression source")
        elif self.kind is ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT:
            if not isinstance(self.source_occurrence, OrderItem):
                raise ValueError(
                    "Grouped-order dependency requires an order-item source"
                )
            if not isinstance(self.source_occurrence.expression, NameExpr):
                raise ValueError("Grouped-order dependency requires a bare-name source")
        else:
            raise ValueError("Clause dependency fact has unsupported kind")

        output_name = _projection_output_name(self.target_occurrence)
        if output_name is None or output_name != self.target_field.name:
            raise ValueError("Output dependency selected/field identity mismatch")
        if self.target_field.result_role is ProjectRowResultRole.GROUP_KEY:
            if self.aggregate_result_fact is not None:
                raise ValueError("Group-key output cannot carry an aggregate fact")
            return
        if self.target_field.result_role is not ProjectRowResultRole.AGGREGATE_RESULT:
            raise ValueError("Output dependency requires a grouped output role")
        fact = self.aggregate_result_fact
        if not isinstance(fact, ProjectAggregateResultFact):
            raise ValueError("Aggregate output dependency requires aggregate fact")
        if fact.output_name != self.target_field.name:
            raise ValueError("Aggregate output dependency fact identity mismatch")
        selected_expression = self.target_occurrence.expression
        if (
            not isinstance(selected_expression, CallExpr)
            or semantic_aggregate_call_name(selected_expression) != fact.function
            or len(selected_expression.arguments) != fact.argument_count
            or fact.grouped is not True
        ):
            raise ValueError("Aggregate output dependency selected-call mismatch")


@dataclass(frozen=True, slots=True)
class ProjectAggregateGroupedClauseReadiness:
    """Atomic helper-only clause readiness over one Slice 7 finalization."""

    definition: TableDef | QueryDef
    finalization: ProjectAggregateGroupedSchemaFinalization
    status: ProjectAggregateGroupedClauseReadinessStatus
    reason: ProjectAggregateGroupedClauseReadinessReason
    dependency_facts: tuple[ProjectRelationClauseDependencyFact, ...]
    limit_present: bool

    def __post_init__(self) -> None:
        """Defensively freeze facts and enforce cross-carrier coherence."""

        if not isinstance(self.definition, (TableDef, QueryDef)):
            raise ValueError("Clause readiness requires a derived relation")
        if not isinstance(
            self.finalization,
            ProjectAggregateGroupedSchemaFinalization,
        ):
            raise ValueError("Clause readiness requires a schema finalization")
        if not isinstance(self.status, ProjectAggregateGroupedClauseReadinessStatus):
            raise ValueError("Clause readiness requires a status")
        if not isinstance(self.reason, ProjectAggregateGroupedClauseReadinessReason):
            raise ValueError("Clause readiness requires a reason")
        if type(self.limit_present) is not bool:
            raise ValueError("Clause readiness requires exact limit-presence bool")

        dependency_facts = tuple(self.dependency_facts)
        object.__setattr__(self, "dependency_facts", dependency_facts)
        if not all(
            isinstance(fact, ProjectRelationClauseDependencyFact)
            for fact in dependency_facts
        ):
            raise ValueError("Clause readiness requires dependency facts")

        nested_status = self.finalization.state.status
        if nested_status is not ProjectRelationRowSchemaStatus.CONCRETE:
            expected = _readiness_status(nested_status)
            if (
                self.status is not expected
                or self.reason
                is not ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
                or dependency_facts
                or self.limit_present
            ):
                raise ValueError(
                    "Non-concrete finalization must be mirrored atomically"
                )
            return

        if self.limit_present is not (self.definition.limit_clause is not None):
            raise ValueError("Concrete finalization requires exact limit presence")

        if self.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE:
            if (
                self.reason
                is not ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY
            ):
                raise ValueError("Concrete clause readiness requires ready reason")
            _validate_complete_dependency_facts(
                self.definition,
                self.finalization,
                dependency_facts,
            )
            return

        if dependency_facts:
            raise ValueError("Non-ready clause readiness cannot carry partial facts")
        if self.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN:
            if self.reason not in {
                ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
                ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
                ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
            }:
                raise ValueError("Unknown clause readiness reason mismatch")
            return
        if self.status is ProjectAggregateGroupedClauseReadinessStatus.DEFERRED:
            if (
                self.reason
                is not ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
                or self.definition.group_by_clause is not None
                or self.definition.order_by_clause is None
                or self.definition.satisfying_clause is not None
            ):
                raise ValueError("Deferred clause readiness reason mismatch")
            return
        if self.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED:
            if self.reason not in {
                ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
                ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
            }:
                raise ValueError("Blocked clause readiness reason mismatch")
            return
        raise ValueError("Concrete finalization has unsupported readiness status")


@dataclass(frozen=True, slots=True)
class _OutputTarget:
    item: SelectItem
    field: ProjectRowField
    aggregate_fact: ProjectAggregateResultFact | None


@dataclass(frozen=True, slots=True)
class _Evidence:
    group_keys: tuple[ProjectGroupKeyFact, ...]
    outputs: Mapping[str, _OutputTarget]
    missing: bool
    conflicting: bool


def build_project_aggregate_grouped_clause_readiness(
    *,
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedClauseReadiness:
    """Build atomic private clause facts over exactly one Slice 7 finalization."""

    finalization = build_project_aggregate_grouped_schema_finalization(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
        let_scope_facts=let_scope_facts,
    )
    if finalization.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return ProjectAggregateGroupedClauseReadiness(
            definition=definition,
            finalization=finalization,
            status=_readiness_status(finalization.state.status),
            reason=(
                ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
            ),
            dependency_facts=(),
            limit_present=False,
        )

    evidence = _retained_evidence(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path=fallback_path,
        finalization=finalization,
        let_scope_facts=let_scope_facts,
    )
    if evidence.missing:
        return _failed_readiness(
            definition,
            finalization,
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        )
    if evidence.conflicting:
        return _failed_readiness(
            definition,
            finalization,
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        )

    satisfying_facts: tuple[ProjectRelationClauseDependencyFact, ...] = ()
    satisfying_status: ProjectAggregateGroupedClauseReadinessStatus | None = None
    satisfying_reason: ProjectAggregateGroupedClauseReadinessReason | None = None
    if definition.satisfying_clause is not None:
        satisfying_facts, satisfying_status, satisfying_reason = _satisfying_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            finalization=finalization,
            outputs=evidence.outputs,
            let_scope_facts=let_scope_facts,
        )

    order_facts: tuple[ProjectRelationClauseDependencyFact, ...] = ()
    order_status: ProjectAggregateGroupedClauseReadinessStatus | None = None
    order_reason: ProjectAggregateGroupedClauseReadinessReason | None = None
    if definition.group_by_clause is not None:
        order_facts, order_status, order_reason = _grouped_order_facts(
            definition=definition,
            input_schema=input_schema,
            group_keys=evidence.group_keys,
            outputs=evidence.outputs,
            let_scope_facts=let_scope_facts,
        )

    internal_reasons = (satisfying_reason, order_reason)
    if (
        ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT
        in internal_reasons
    ):
        return _failed_readiness(
            definition,
            finalization,
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        )
    if ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS in (
        internal_reasons
    ):
        return _failed_readiness(
            definition,
            finalization,
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        )

    facts = [
        ProjectRelationClauseDependencyFact(
            kind=ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT,
            source_occurrence=fact.item,
            target_occurrence=fact,
            target_field=fact.input_field,
            aggregate_result_fact=None,
        )
        for fact in evidence.group_keys
    ]

    if definition.satisfying_clause is not None:
        if satisfying_reason is not None:
            assert satisfying_status is not None
            return _failed_readiness(
                definition,
                finalization,
                satisfying_status,
                satisfying_reason,
            )
        facts.extend(satisfying_facts)

    if definition.group_by_clause is None:
        order_reason = _no_group_order_reason(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            let_scope_facts=let_scope_facts,
        )
        if order_reason is not None:
            status = (
                ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
                if order_reason
                is ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
                else ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
            )
            return _failed_readiness(
                definition,
                finalization,
                status,
                order_reason,
            )
    else:
        if order_reason is not None:
            assert order_status is not None
            return _failed_readiness(
                definition,
                finalization,
                order_status,
                order_reason,
            )
        facts.extend(order_facts)

    if not _valid_limit(definition):
        return _failed_readiness(
            definition,
            finalization,
            ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        )

    return ProjectAggregateGroupedClauseReadiness(
        definition=definition,
        finalization=finalization,
        status=ProjectAggregateGroupedClauseReadinessStatus.CONCRETE,
        reason=ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY,
        dependency_facts=_dedupe_facts(facts),
        limit_present=definition.limit_clause is not None,
    )


def _retained_evidence(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    fallback_path: str,
    finalization: ProjectAggregateGroupedSchemaFinalization,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> _Evidence:
    missing = False
    conflicting = False
    group_keys: tuple[ProjectGroupKeyFact, ...] = ()
    if definition.group_by_clause is not None:
        if let_scope_facts is None:
            group_facts = build_project_group_key_schema_facts(
                definition=definition,
                input_schema=input_schema,
                upstream_symbol=upstream_symbol,
                fallback_path=fallback_path,
            )
        else:
            group_attempt = _build_project_group_key_schema_attempt(
                definition=definition,
                input_schema=input_schema,
                upstream_symbol=upstream_symbol,
                fallback_path=fallback_path,
                let_scope_facts=let_scope_facts,
            )
            group_facts = (
                group_attempt.facts
                if isinstance(group_attempt.facts, ProjectGroupKeySchemaFacts)
                else None
            )
        if group_facts is None:
            missing = True
        elif not isinstance(group_facts, ProjectGroupKeySchemaFacts):
            conflicting = True
        else:
            group_keys = tuple(group_facts.group_keys)
            expected_items = tuple(definition.group_by_clause.items)
            if len(group_keys) < len(expected_items):
                missing = True
            elif len(group_keys) > len(expected_items):
                conflicting = True
            for index, fact in enumerate(group_keys[: len(expected_items)]):
                item = expected_items[index]
                if fact.item is not item:
                    conflicting = True
                retained = input_schema.fields.get(fact.field_identity)
                if retained is None:
                    missing = True
                elif fact.input_field is not retained:
                    conflicting = True

    outputs, output_missing, output_conflicting = _output_targets(
        definition,
        finalization,
    )
    return _Evidence(
        group_keys=group_keys,
        outputs=outputs,
        missing=missing or output_missing,
        conflicting=conflicting or output_conflicting,
    )


def _output_targets(
    definition: _DerivedRelation,
    finalization: ProjectAggregateGroupedSchemaFinalization,
) -> tuple[dict[str, _OutputTarget], bool, bool]:
    schema = finalization.state.schema
    if schema is None:
        return {}, True, False

    outputs: dict[str, _OutputTarget] = {}
    missing = False
    conflicting = False
    expected_names: list[str] = []
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            missing = True
            continue
        expected_names.append(output_name)
        if output_name in outputs:
            conflicting = True
            continue
        field = schema.fields.get(output_name)
        if field is None:
            missing = True
            continue
        aggregate_fact = finalization.aggregate_result_facts.get(output_name)
        if field.result_role is ProjectRowResultRole.GROUP_KEY:
            if aggregate_fact is not None:
                conflicting = True
        elif field.result_role is ProjectRowResultRole.AGGREGATE_RESULT:
            if aggregate_fact is None:
                missing = True
            elif aggregate_fact.output_name != output_name:
                conflicting = True
        else:
            conflicting = True
        outputs[output_name] = _OutputTarget(
            item=item,
            field=field,
            aggregate_fact=aggregate_fact,
        )

    if tuple(schema.fields) != tuple(expected_names):
        schema_names = tuple(schema.fields)
        if any(name not in schema.fields for name in expected_names):
            missing = True
        if any(name not in expected_names for name in schema_names) or (
            len(schema_names) != len(expected_names)
        ):
            conflicting = True
        if set(schema_names) == set(expected_names):
            conflicting = True
    aggregate_names = tuple(
        name
        for name in expected_names
        if (target := outputs.get(name)) is not None
        and target.field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
    )
    if tuple(finalization.aggregate_result_facts) != aggregate_names:
        if any(
            name not in finalization.aggregate_result_facts for name in aggregate_names
        ):
            missing = True
        if set(finalization.aggregate_result_facts) != set(aggregate_names):
            conflicting = True
        elif tuple(finalization.aggregate_result_facts) != aggregate_names:
            conflicting = True
    return outputs, missing, conflicting


def _satisfying_facts(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    finalization: ProjectAggregateGroupedSchemaFinalization,
    outputs: Mapping[str, _OutputTarget],
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> tuple[
    tuple[ProjectRelationClauseDependencyFact, ...],
    ProjectAggregateGroupedClauseReadinessStatus | None,
    ProjectAggregateGroupedClauseReadinessReason | None,
]:
    if definition.group_by_clause is None:
        return (
            (),
            ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        )
    output_schema = finalization.state.schema
    assert output_schema is not None
    semantic_input = project_row_schema_to_semantic_row_schema(input_schema)
    semantic_output = project_row_schema_to_semantic_row_schema(output_schema)
    upstream_definition = upstream_symbol.definition
    if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
        return (
            (),
            ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
        )

    source_row_schemas: dict[SourceDef, RowSchema] = {}
    if isinstance(upstream_definition, SourceDef):
        source_row_schemas[upstream_definition] = semantic_input
    relation_row_schemas: dict[_DerivedRelation, RowSchema] = {
        definition: semantic_output
    }
    if isinstance(upstream_definition, (TableDef, QueryDef)):
        relation_row_schemas[upstream_definition] = semantic_input
    let_expressions = (
        let_scope_facts.binding_expressions
        if let_scope_facts is not None
        else admitted_relation_let_expressions(definition, semantic_input)
    )
    result_predicates, diagnostics = check_satisfying_clauses(
        Script(
            span=definition.span,
            header=None,
            definitions=(definition,),
        ),
        from_resolutions={definition.from_clause: upstream_definition},
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_expressions={definition: let_expressions},
    )
    if diagnostics:
        codes = {diagnostic.code for diagnostic in diagnostics}
        if "PIE-S2324" in codes:
            reason = ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        elif codes & {"PIE-S2325", "PIE-S2326"}:
            reason = ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE
        else:
            reason = (
                ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION
            )
        return (), ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN, reason
    if definition not in result_predicates:
        return (
            (),
            ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        )

    assert definition.satisfying_clause is not None
    facts: list[ProjectRelationClauseDependencyFact] = []
    missing = False
    conflicting = False
    for occurrence in _satisfying_dependency_occurrences(
        definition.satisfying_clause.expression
    ):
        target = (
            outputs.get(occurrence.name)
            if isinstance(occurrence, NameExpr)
            else _matching_aggregate_output(
                occurrence,
                outputs=outputs,
                let_expressions=let_expressions,
            )
        )
        if target is None:
            missing = True
            continue
        if target.item is not _exact_select_item(definition, target.item):
            conflicting = True
            continue
        facts.append(
            ProjectRelationClauseDependencyFact(
                kind=ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT,
                source_occurrence=occurrence,
                target_occurrence=target.item,
                target_field=target.field,
                aggregate_result_fact=target.aggregate_fact,
            )
        )
    if missing:
        return (
            (),
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        )
    if conflicting:
        return (
            (),
            ProjectAggregateGroupedClauseReadinessStatus.BLOCKED,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        )
    return tuple(facts), None, None


def _satisfying_dependency_occurrences(
    expression: Expression,
) -> tuple[NameExpr | CallExpr, ...]:
    if isinstance(expression, NameExpr):
        return (expression,)
    if isinstance(expression, LiteralExpr):
        return ()
    if isinstance(expression, CallExpr):
        return (expression,)
    if isinstance(expression, ComparisonExpr):
        return (
            *_satisfying_dependency_occurrences(expression.left),
            *_satisfying_dependency_occurrences(expression.right),
        )
    if isinstance(expression, BinaryExpr) and expression.operator in {"and", "or"}:
        return (
            *_satisfying_dependency_occurrences(expression.left),
            *_satisfying_dependency_occurrences(expression.right),
        )
    return ()


def _matching_aggregate_output(
    expression: CallExpr,
    *,
    outputs: Mapping[str, _OutputTarget],
    let_expressions: Mapping[str, Expression],
) -> _OutputTarget | None:
    function_name = semantic_aggregate_call_name(expression)
    if function_name is None or len(expression.arguments) != 1:
        return None
    argument = expression.arguments[0]
    if not aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        let_expressions,
    ):
        return None
    effective_argument = effective_semantic_aggregate_argument_expression(
        function_name,
        argument,
        let_expansions=let_expressions,
    )
    for target in outputs.values():
        selected_expression = target.item.expression
        if not isinstance(selected_expression, CallExpr):
            continue
        if semantic_aggregate_call_name(selected_expression) != function_name:
            continue
        if len(selected_expression.arguments) != 1:
            continue
        selected_argument = effective_semantic_aggregate_argument_expression(
            function_name,
            selected_expression.arguments[0],
            let_expansions=let_expressions,
        )
        if selected_argument == effective_argument:
            return target
    return None


def _grouped_order_facts(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    group_keys: tuple[ProjectGroupKeyFact, ...],
    outputs: Mapping[str, _OutputTarget],
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> tuple[
    tuple[ProjectRelationClauseDependencyFact, ...],
    ProjectAggregateGroupedClauseReadinessStatus | None,
    ProjectAggregateGroupedClauseReadinessReason | None,
]:
    if definition.order_by_clause is None:
        return (), None, None
    semantic_input = project_row_schema_to_semantic_row_schema(input_schema)
    let_expressions = (
        let_scope_facts.binding_expressions
        if let_scope_facts is not None
        else admitted_relation_let_expressions(definition, semantic_input)
    )
    group_identities = {fact.field_identity for fact in group_keys}
    selected_group_targets: dict[str, _OutputTarget] = {}
    for target in outputs.values():
        if target.field.result_role is not ProjectRowResultRole.GROUP_KEY:
            continue
        identity = _direct_field_identity(
            definition,
            target.item.expression,
            input_schema,
        )
        if identity is not None and identity in group_identities:
            selected_group_targets.setdefault(identity, target)

    tentative: list[ProjectRelationClauseDependencyFact] = []
    unavailable = False
    invalid_output = False
    invalid_expression = False
    for item in definition.order_by_clause.items:
        expression = item.expression
        if not isinstance(expression, NameExpr):
            invalid_expression = True
            continue
        target = outputs.get(expression.name)
        if target is None and expression.name in let_expressions:
            effective = _effective_field_let_expression(
                expression,
                let_expressions=let_expressions,
                seen=frozenset(),
            )
            if effective is None:
                invalid_expression = True
                continue
            identity = _direct_field_identity(
                definition,
                effective,
                input_schema,
            )
            if identity is None:
                invalid_expression = True
                continue
            selected_target = selected_group_targets.get(identity)
            if selected_target is not None:
                target = selected_target
            else:
                invalid_output = True
                continue
        if target is None:
            if expression.name in input_schema.fields:
                invalid_output = True
            else:
                unavailable = True
            continue
        tentative.append(
            ProjectRelationClauseDependencyFact(
                kind=ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT,
                source_occurrence=item,
                target_occurrence=target.item,
                target_field=target.field,
                aggregate_result_fact=target.aggregate_fact,
            )
        )

    if unavailable:
        reason = (
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        )
    elif invalid_output:
        reason = (
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE
        )
    elif invalid_expression:
        reason = ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION
    else:
        return tuple(tentative), None, None
    return (), ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN, reason


def _no_group_order_reason(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
) -> ProjectAggregateGroupedClauseReadinessReason | None:
    if definition.order_by_clause is None:
        return None
    upstream_definition = upstream_symbol.definition
    if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
        return (
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        )
    let_facts = let_scope_facts
    if let_facts is None:
        let_facts = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_definition=upstream_definition,
        )
    if let_facts.status not in {
        ProjectLetScopeFactsStatus.ABSENT,
        ProjectLetScopeFactsStatus.CONCRETE,
    }:
        return (
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        )

    semantic_input = project_row_schema_to_semantic_row_schema(input_schema)
    unavailable = False
    invalid = False
    value_types: dict[Expression, ValueType] = {}
    for item in definition.order_by_clause.items:
        if contains_semantic_aggregate(item.expression):
            invalid = True
            continue
        diagnostics: list[Diagnostic] = []
        infer_row_expression(
            item.expression,
            semantic_input,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=definition.from_clause.source_name,
            bare_value_types=let_facts.value_types,
            bare_value_expressions=let_facts.binding_expressions,
        )
        if any(diagnostic.code == "PIE-S2102" for diagnostic in diagnostics):
            unavailable = True
        elif diagnostics:
            invalid = True
    if unavailable:
        return (
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        )
    if invalid:
        return ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION
    return ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY


def _valid_limit(definition: _DerivedRelation) -> bool:
    clause = definition.limit_clause
    if clause is None:
        return True
    expression = clause.expression
    if not isinstance(expression, LiteralExpr):
        return False
    value = expression.value
    return type(value) is int and 0 <= value <= MAX_RELATION_LIMIT


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _direct_field_identity(
    definition: _DerivedRelation,
    expression: Expression,
    input_schema: ProjectRowSchema,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name if expression.name in input_schema.fields else None
    if isinstance(expression, DottedNameExpr):
        if (
            len(expression.parts) == 2
            and expression.parts[0] == definition.from_clause.source_name
            and expression.parts[1] in input_schema.fields
        ):
            return expression.parts[1]
    return None


def _effective_field_let_expression(
    expression: NameExpr,
    *,
    let_expressions: Mapping[str, Expression],
    seen: frozenset[str],
) -> NameExpr | DottedNameExpr | None:
    if expression.name not in let_expressions:
        return expression
    if expression.name in seen:
        return None
    expanded = let_expressions[expression.name]
    if isinstance(expanded, DottedNameExpr):
        return expanded
    if isinstance(expanded, NameExpr):
        return _effective_field_let_expression(
            expanded,
            let_expressions=let_expressions,
            seen=seen | frozenset((expression.name,)),
        )
    return None


def _dedupe_facts(
    facts: Iterable[ProjectRelationClauseDependencyFact],
) -> tuple[ProjectRelationClauseDependencyFact, ...]:
    retained: list[ProjectRelationClauseDependencyFact] = []
    seen: set[tuple[ProjectRelationClauseDependencyKind, int]] = set()
    for fact in facts:
        identity = (fact.kind, id(fact.target_occurrence))
        if identity in seen:
            continue
        seen.add(identity)
        retained.append(fact)
    return tuple(retained)


def _failed_readiness(
    definition: _DerivedRelation,
    finalization: ProjectAggregateGroupedSchemaFinalization,
    status: ProjectAggregateGroupedClauseReadinessStatus,
    reason: ProjectAggregateGroupedClauseReadinessReason,
) -> ProjectAggregateGroupedClauseReadiness:
    return ProjectAggregateGroupedClauseReadiness(
        definition=definition,
        finalization=finalization,
        status=status,
        reason=reason,
        dependency_facts=(),
        limit_present=definition.limit_clause is not None,
    )


def _readiness_status(
    status: ProjectRelationRowSchemaStatus,
) -> ProjectAggregateGroupedClauseReadinessStatus:
    if status is ProjectRelationRowSchemaStatus.CONCRETE:
        return ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    if status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    if status is ProjectRelationRowSchemaStatus.DEFERRED:
        return ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
    if status is ProjectRelationRowSchemaStatus.BLOCKED:
        return ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
    raise ValueError("Unsupported project row-schema status")


def _exact_select_item(
    definition: _DerivedRelation,
    target: SelectItem,
) -> SelectItem | None:
    return next((item for item in definition.select_items if item is target), None)


def _validate_complete_dependency_facts(
    definition: _DerivedRelation,
    finalization: ProjectAggregateGroupedSchemaFinalization,
    facts: tuple[ProjectRelationClauseDependencyFact, ...],
) -> None:
    if not _valid_limit(definition):
        raise ValueError("Concrete clause readiness requires a valid static limit")
    if definition.group_by_clause is None and (
        definition.satisfying_clause is not None
        or definition.order_by_clause is not None
    ):
        raise ValueError("Concrete no-group readiness has unsupported clauses")

    seen: set[tuple[ProjectRelationClauseDependencyKind, int]] = set()
    stages = {
        ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT: 0,
        ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT: 1,
        ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT: 2,
    }
    prior_stage = 0
    group_source_ids: list[int] = []
    satisfying_ids = (
        set()
        if definition.satisfying_clause is None
        else {
            id(expression)
            for expression in _walk_expression(definition.satisfying_clause.expression)
        }
    )
    order_ids = (
        set()
        if definition.order_by_clause is None
        else {id(item) for item in definition.order_by_clause.items}
    )
    schema = finalization.state.schema
    assert schema is not None

    for fact in facts:
        stage = stages[fact.kind]
        if stage < prior_stage:
            raise ValueError("Clause dependency fact order mismatch")
        prior_stage = stage
        identity = (fact.kind, id(fact.target_occurrence))
        if identity in seen:
            raise ValueError("Clause dependency facts require first-target dedupe")
        seen.add(identity)

        if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT:
            assert isinstance(fact.source_occurrence, GroupByItem)
            group_source_ids.append(id(fact.source_occurrence))
            continue

        assert isinstance(fact.target_occurrence, SelectItem)
        if _exact_select_item(definition, fact.target_occurrence) is None:
            raise ValueError("Clause output target is outside the definition")
        output_name = _projection_output_name(fact.target_occurrence)
        if (
            output_name is None
            or schema.fields.get(output_name) is not fact.target_field
        ):
            raise ValueError("Clause output target field is not finalized field")
        expected_aggregate = finalization.aggregate_result_facts.get(output_name)
        if expected_aggregate is not fact.aggregate_result_fact:
            raise ValueError("Clause output aggregate fact is not finalized fact")
        if fact.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT:
            if id(fact.source_occurrence) not in satisfying_ids:
                raise ValueError("Satisfying source is outside the definition")
        elif id(fact.source_occurrence) not in order_ids:
            raise ValueError("Grouped-order source is outside the definition")

    expected_group_ids = (
        []
        if definition.group_by_clause is None
        else [id(item) for item in definition.group_by_clause.items]
    )
    if group_source_ids != expected_group_ids:
        raise ValueError("Concrete grouped readiness requires every group occurrence")

    outputs, missing, conflicting = _output_targets(definition, finalization)
    if missing or conflicting:
        raise ValueError("Concrete clause readiness requires exact output evidence")
    expected_facts = [
        fact
        for fact in facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
    ]
    let_expressions = _definition_let_expressions(definition)
    if definition.satisfying_clause is not None:
        expression = definition.satisfying_clause.expression
        if not _satisfying_traversal_is_supported(expression):
            raise ValueError("Concrete readiness has invalid satisfying expression")
        for occurrence in _satisfying_dependency_occurrences(expression):
            target = (
                outputs.get(occurrence.name)
                if isinstance(occurrence, NameExpr)
                else _matching_aggregate_output(
                    occurrence,
                    outputs=outputs,
                    let_expressions=let_expressions,
                )
            )
            if target is None:
                raise ValueError("Concrete readiness has missing satisfying target")
            expected_facts.append(
                ProjectRelationClauseDependencyFact(
                    kind=ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT,
                    source_occurrence=occurrence,
                    target_occurrence=target.item,
                    target_field=target.field,
                    aggregate_result_fact=target.aggregate_fact,
                )
            )

    if definition.order_by_clause is not None:
        selected_group_targets: dict[str, _OutputTarget] = {}
        for target in outputs.values():
            if target.field.result_role is not ProjectRowResultRole.GROUP_KEY:
                continue
            identity = _source_field_identity(
                definition,
                target.item.expression,
            )
            if identity is not None:
                selected_group_targets.setdefault(identity, target)
        for item in definition.order_by_clause.items:
            expression = item.expression
            if not isinstance(expression, NameExpr):
                raise ValueError("Concrete readiness has invalid grouped order")
            target = outputs.get(expression.name)
            if target is None:
                if expression.name not in let_expressions:
                    raise ValueError(
                        "Concrete readiness has missing grouped order target"
                    )
                effective = _effective_field_let_expression(
                    expression,
                    let_expressions=let_expressions,
                    seen=frozenset(),
                )
                if effective is None:
                    raise ValueError("Concrete readiness has invalid grouped order let")
                identity = _source_field_identity(definition, effective)
                target = (
                    None if identity is None else selected_group_targets.get(identity)
                )
            if target is None:
                raise ValueError("Concrete readiness has missing grouped order target")
            expected_facts.append(
                ProjectRelationClauseDependencyFact(
                    kind=ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT,
                    source_occurrence=item,
                    target_occurrence=target.item,
                    target_field=target.field,
                    aggregate_result_fact=target.aggregate_fact,
                )
            )

    expected = _dedupe_facts(expected_facts)
    if len(facts) != len(expected):
        raise ValueError("Concrete clause readiness requires a complete atomic tuple")
    for supplied, required in zip(facts, expected, strict=True):
        if (
            supplied.kind is not required.kind
            or supplied.source_occurrence is not required.source_occurrence
            or supplied.target_occurrence is not required.target_occurrence
            or supplied.target_field is not required.target_field
            or supplied.aggregate_result_fact is not required.aggregate_result_fact
        ):
            raise ValueError("Concrete clause readiness dependency identity mismatch")


def _definition_let_expressions(
    definition: _DerivedRelation,
) -> dict[str, Expression]:
    clause = definition.let_clause
    if clause is None:
        return {}
    expressions: dict[str, Expression] = {}
    for binding in clause.bindings:
        expressions.setdefault(binding.name, binding.expression)
    return expressions


def _satisfying_traversal_is_supported(expression: Expression) -> bool:
    if isinstance(expression, (NameExpr, LiteralExpr, CallExpr)):
        return True
    if isinstance(expression, ComparisonExpr):
        return isinstance(
            expression.left,
            (NameExpr, LiteralExpr, CallExpr),
        ) and isinstance(
            expression.right,
            (NameExpr, LiteralExpr, CallExpr),
        )
    if isinstance(expression, BinaryExpr) and expression.operator in {"and", "or"}:
        return _satisfying_traversal_is_supported(
            expression.left,
        ) and _satisfying_traversal_is_supported(
            expression.right,
        )
    return False


def _source_field_identity(
    definition: _DerivedRelation,
    expression: Expression,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name
    if (
        isinstance(expression, DottedNameExpr)
        and len(expression.parts) == 2
        and expression.parts[0] == definition.from_clause.source_name
    ):
        return expression.parts[1]
    return None


def _walk_expression(expression: Expression) -> tuple[Expression, ...]:
    children: tuple[Expression, ...]
    if isinstance(expression, CallExpr):
        children = expression.arguments
    elif isinstance(expression, UnaryExpr):
        children = (expression.operand,)
    elif isinstance(expression, BinaryExpr):
        children = (expression.left, expression.right)
    elif isinstance(expression, ComparisonExpr):
        children = (expression.left, expression.right)
    elif isinstance(expression, BetweenExpr):
        children = (expression.value, expression.lower, expression.upper)
    elif isinstance(expression, IsNullExpr):
        children = (expression.value,)
    else:
        children = ()
    return (
        expression,
        *(item for child in children for item in _walk_expression(child)),
    )
