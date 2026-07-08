"""Private project relation-local ``let:`` scope facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto._project.model import (
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowSchema,
)
from pietto._project.row_expression_type_facts import (
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    Expression,
    LetBinding,
    LetClause,
    QueryDef,
    SourceDef,
    TableDef,
)
from pietto.semantic.let_bindings import analyze_relation_let_bindings
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_DerivedRelation = TableDef | QueryDef
_RelationDefinition = SourceDef | TableDef | QueryDef


def _readonly_mapping(
    values: Mapping[_Key, _Value] | None = None,
) -> Mapping[_Key, _Value]:
    return MappingProxyType(dict(values or {}))


class ProjectLetScopeFactsStatus(StrEnum):
    """Private availability status for one relation-local let scope."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ABSENT = "absent"


class ProjectLetScopeFactsReason(StrEnum):
    """Private deterministic reason for one relation-local let fact result."""

    NO_LET_CLAUSE = "no_let_clause"
    UPSTREAM_CONCRETE = "upstream_concrete"
    UPSTREAM_UNKNOWN = "upstream_unknown"
    UPSTREAM_DEFERRED = "upstream_deferred"
    UPSTREAM_BLOCKED = "upstream_blocked"
    LET_DIAGNOSTICS_SUPPRESSED = "let_diagnostics_suppressed"
    MISSING_OR_UNKNOWN_VALUE_TYPE = "missing_or_unknown_value_type"


@dataclass(frozen=True, slots=True)
class ProjectRelationLetScopeFacts:
    """Private relation-local let scope/value facts for future project slices."""

    status: ProjectLetScopeFactsStatus
    reason: ProjectLetScopeFactsReason
    clause: LetClause | None = None
    bindings: tuple[LetBinding, ...] = ()
    binding_expressions: Mapping[str, Expression] = field(
        default_factory=lambda: _readonly_mapping()
    )
    value_types: Mapping[str, ValueType] = field(
        default_factory=lambda: _readonly_mapping()
    )

    def __post_init__(self) -> None:
        """Copy fact maps into immutable containers and validate invariants."""

        if not isinstance(self.status, ProjectLetScopeFactsStatus):
            raise ValueError("Project let scope facts require a status")
        if not isinstance(self.reason, ProjectLetScopeFactsReason):
            raise ValueError("Project let scope facts require a reason")

        bindings = tuple(self.bindings)
        binding_expressions = _readonly_mapping(self.binding_expressions)
        value_types = _readonly_mapping(self.value_types)
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "binding_expressions", binding_expressions)
        object.__setattr__(self, "value_types", value_types)

        if self.status is ProjectLetScopeFactsStatus.ABSENT:
            if (
                self.clause is not None
                or bindings
                or binding_expressions
                or value_types
            ):
                raise ValueError("Absent project let scope facts cannot carry values")
            return

        if self.clause is None:
            raise ValueError("Present project let scope facts require a clause")

        if self.status is ProjectLetScopeFactsStatus.CONCRETE:
            binding_names = _binding_names(bindings)
            if tuple(value_types) != binding_names:
                raise ValueError("Concrete project let scope facts require all values")
            return

        if value_types:
            raise ValueError("Non-concrete project let scope facts cannot carry values")


def build_project_relation_let_scope_facts(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    upstream_definition: _RelationDefinition | None,
    upstream_state: ProjectRelationRowSchemaState | None = None,
) -> ProjectRelationLetScopeFacts:
    """Build private let scope facts from existing semantic let analysis."""

    if definition.let_clause is None:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.ABSENT,
            reason=ProjectLetScopeFactsReason.NO_LET_CLAUSE,
        )

    bindings = tuple(definition.let_clause.bindings)
    binding_expressions = _binding_expressions(bindings)
    non_concrete = _upstream_non_concrete_facts(
        definition,
        upstream_state=upstream_state,
        bindings=bindings,
        binding_expressions=binding_expressions,
    )
    if non_concrete is not None:
        return non_concrete

    effective_input_schema = _effective_input_schema(
        input_schema,
        upstream_state=upstream_state,
    )
    if effective_input_schema is None or effective_input_schema.is_unknown:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.UNKNOWN,
            reason=ProjectLetScopeFactsReason.UPSTREAM_UNKNOWN,
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
        )
    if upstream_definition is None:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.BLOCKED,
            reason=ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
        )

    row_schema = project_row_schema_to_semantic_row_schema(effective_input_schema)
    scopes, _expression_value_types, diagnostics = analyze_relation_let_bindings(
        (definition,),
        from_resolutions={definition.from_clause: upstream_definition},
        source_row_schemas=_source_row_schemas(upstream_definition, row_schema),
        relation_row_schemas=_relation_row_schemas(upstream_definition, row_schema),
    )
    if diagnostics:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.UNKNOWN,
            reason=ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED,
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
        )

    scope = scopes.get(definition)
    if scope is None:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.UNKNOWN,
            reason=ProjectLetScopeFactsReason.MISSING_OR_UNKNOWN_VALUE_TYPE,
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
        )

    known_values = {
        name: value_type
        for name, value_type in scope.value_types.items()
        if value_type.kind is ValueTypeKind.KNOWN
    }
    if tuple(known_values) != _binding_names(bindings):
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.UNKNOWN,
            reason=ProjectLetScopeFactsReason.MISSING_OR_UNKNOWN_VALUE_TYPE,
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
        )

    return ProjectRelationLetScopeFacts(
        status=ProjectLetScopeFactsStatus.CONCRETE,
        reason=ProjectLetScopeFactsReason.UPSTREAM_CONCRETE,
        clause=definition.let_clause,
        bindings=bindings,
        binding_expressions=binding_expressions,
        value_types=known_values,
    )


def _upstream_non_concrete_facts(
    definition: _DerivedRelation,
    *,
    upstream_state: ProjectRelationRowSchemaState | None,
    bindings: tuple[LetBinding, ...],
    binding_expressions: Mapping[str, Expression],
) -> ProjectRelationLetScopeFacts | None:
    if upstream_state is None:
        return None
    if upstream_state.status is ProjectRelationRowSchemaStatus.CONCRETE:
        return None
    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        status = ProjectLetScopeFactsStatus.UNKNOWN
        reason = ProjectLetScopeFactsReason.UPSTREAM_UNKNOWN
    elif upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        status = ProjectLetScopeFactsStatus.DEFERRED
        reason = ProjectLetScopeFactsReason.UPSTREAM_DEFERRED
    else:
        status = ProjectLetScopeFactsStatus.BLOCKED
        reason = ProjectLetScopeFactsReason.UPSTREAM_BLOCKED
    return ProjectRelationLetScopeFacts(
        status=status,
        reason=reason,
        clause=definition.let_clause,
        bindings=bindings,
        binding_expressions=binding_expressions,
    )


def _effective_input_schema(
    input_schema: ProjectRowSchema | None,
    *,
    upstream_state: ProjectRelationRowSchemaState | None,
) -> ProjectRowSchema | None:
    if input_schema is not None:
        return input_schema
    if (
        upstream_state is not None
        and upstream_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    ):
        return upstream_state.schema
    return None


def _source_row_schemas(
    upstream_definition: _RelationDefinition,
    row_schema: RowSchema,
) -> Mapping[SourceDef, RowSchema]:
    if isinstance(upstream_definition, SourceDef):
        return {upstream_definition: row_schema}
    return {}


def _relation_row_schemas(
    upstream_definition: _RelationDefinition,
    row_schema: RowSchema,
) -> Mapping[_DerivedRelation, RowSchema]:
    if isinstance(upstream_definition, (TableDef, QueryDef)):
        return {upstream_definition: row_schema}
    return {}


def _binding_expressions(bindings: tuple[LetBinding, ...]) -> Mapping[str, Expression]:
    expressions: dict[str, Expression] = {}
    for binding in bindings:
        if binding.name not in expressions:
            expressions[binding.name] = binding.expression
    return expressions


def _binding_names(bindings: tuple[LetBinding, ...]) -> tuple[str, ...]:
    names: list[str] = []
    seen_names: set[str] = set()
    for binding in bindings:
        if binding.name in seen_names:
            continue
        names.append(binding.name)
        seen_names.add(binding.name)
    return tuple(names)
