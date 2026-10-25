"""Private project relation-local ``let:`` scope facts."""

from __future__ import annotations

from pietto.ast_nodes import SetRelationDef, TableFunctionRelationDef, ValuesRelationDef

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeVar

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
from pietto.semantic.expressions import LetValues, _let_names_with_diagnostics
from pietto.semantic.let_bindings import analyze_relation_let_bindings
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind
from pietto.errors import Diagnostic

if TYPE_CHECKING:
    from pietto._project.existence_values import ProjectAnyValue
    from pietto.semantic.relationship_predicates import RelationshipCallFailure

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_DerivedRelation = TableDef | QueryDef
_RelationDefinition = (
    SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | ValuesRelationDef
    | TableFunctionRelationDef
)


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
    # The type of each binding without an error of its own, as a single file
    # reads it: `value_types` itself in a CONCRETE scope; in an UNKNOWN one
    # whose let analysis ran, also beside a binding with an error, and of
    # unknown type for one such as `k = null`, whose read takes its type from
    # where it stands, as `null` does.
    binding_value_types: Mapping[str, ValueType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    definition: _DerivedRelation | None = None
    input_schema: ProjectRowSchema | None = None
    upstream_definition: _RelationDefinition | None = None
    input_state: ProjectRelationRowSchemaState | None = None
    expression_value_types: Mapping[Expression, ValueType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    existence_values: tuple[ProjectAnyValue, ...] = ()

    def __post_init__(self) -> None:
        """Copy fact maps into immutable containers and validate invariants."""

        if type(self.existence_values) is not tuple:
            raise TypeError("LET ANY facts require an exact tuple.")
        if self.existence_values:
            from pietto._project.existence_values import ProjectAnyValue

            if type(self.existence_values) is not tuple or any(
                type(value) is not ProjectAnyValue
                or value.input.binding.owner.definition is not self.definition
                or not any(value.context is binding for binding in self.bindings)
                for value in self.existence_values
            ):
                raise ValueError("LET ANY facts require their exact binding scope.")
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
        binding_value_types = (
            value_types
            if self.status is ProjectLetScopeFactsStatus.CONCRETE
            else _readonly_mapping(self.binding_value_types)
        )
        object.__setattr__(self, "binding_value_types", binding_value_types)
        if (
            binding_value_types
            and self.status is not ProjectLetScopeFactsStatus.CONCRETE
            and (
                self.status is not ProjectLetScopeFactsStatus.UNKNOWN
                or any(
                    type(value) is not ValueType
                    for value in binding_value_types.values()
                )
                or not set(binding_value_types) <= set(_binding_names(bindings))
            )
        ):
            raise ValueError("LET binding value types require analyzed bindings")
        object.__setattr__(
            self,
            "expression_value_types",
            _readonly_mapping(self.expression_value_types),
        )
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if self.expression_value_types or self.diagnostics:
            if (
                self.definition is None
                or self.definition.let_clause is not self.clause
                or self.input_schema is None
                or self.upstream_definition is None
                or any(
                    type(value) is not ValueType
                    for value in self.expression_value_types.values()
                )
            ):
                raise ValueError(
                    "LET analysis requires its exact definition/input context"
                )

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
    normalized_bindings: Mapping[LetBinding, Expression] | None = None,
    failed_relationship_calls: Sequence[RelationshipCallFailure] = (),
) -> ProjectRelationLetScopeFacts:
    """Build private let scope facts from existing semantic let analysis."""

    bindings = (
        () if definition.let_clause is None else tuple(definition.let_clause.bindings)
    )
    if normalized_bindings is not None and (
        len(normalized_bindings) != len(bindings)
        or any(
            actual is not binding
            for actual, binding in zip(normalized_bindings, bindings, strict=True)
        )
    ):
        raise ValueError("Normalized LET bindings require complete exact source order.")
    if definition.let_clause is None:
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.ABSENT,
            reason=ProjectLetScopeFactsReason.NO_LET_CLAUSE,
            definition=definition,
            input_schema=_effective_input_schema(
                input_schema, upstream_state=upstream_state
            ),
            upstream_definition=upstream_definition,
            input_state=upstream_state,
        )

    binding_expressions = _binding_expressions(bindings, normalized_bindings)
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
    scopes, expression_value_types, diagnostics = analyze_relation_let_bindings(
        (definition,),
        from_resolutions={definition.from_clause: upstream_definition},
        source_row_schemas=_source_row_schemas(upstream_definition, row_schema),
        relation_row_schemas=_relation_row_schemas(upstream_definition, row_schema),
        allow_unaliased_selected_let_outputs=True,
        normalized_bindings=normalized_bindings,
        failed_relationship_calls=failed_relationship_calls,
    )
    scope = scopes.get(definition)
    erroneous = _let_names_with_diagnostics(definition, diagnostics)
    binding_values = {
        name: value_type
        for name, value_type in ({} if scope is None else scope.value_types).items()
        if name not in erroneous
    }
    if (
        diagnostics
        or tuple(binding_values) != _binding_names(bindings)
        or any(
            value_type.kind is not ValueTypeKind.KNOWN
            for value_type in binding_values.values()
        )
    ):
        return ProjectRelationLetScopeFacts(
            status=ProjectLetScopeFactsStatus.UNKNOWN,
            reason=(
                ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
                if diagnostics
                else ProjectLetScopeFactsReason.MISSING_OR_UNKNOWN_VALUE_TYPE
            ),
            clause=definition.let_clause,
            bindings=bindings,
            binding_expressions=binding_expressions,
            binding_value_types=binding_values,
            definition=definition,
            input_schema=effective_input_schema,
            upstream_definition=upstream_definition,
            input_state=upstream_state,
            expression_value_types=expression_value_types,
            diagnostics=tuple(diagnostics),
        )

    return ProjectRelationLetScopeFacts(
        status=ProjectLetScopeFactsStatus.CONCRETE,
        reason=ProjectLetScopeFactsReason.UPSTREAM_CONCRETE,
        clause=definition.let_clause,
        bindings=bindings,
        binding_expressions=binding_expressions,
        value_types=binding_values,
        definition=definition,
        input_schema=effective_input_schema,
        upstream_definition=upstream_definition,
        input_state=upstream_state,
        expression_value_types=expression_value_types,
    )


def checked_let_values(
    let_scope: ProjectRelationLetScopeFacts,
    values: Mapping[str, Expression],
) -> Mapping[str, Expression]:
    """``values``, `let:` values of ``let_scope``, as `LetValues` once its let
    analysis ran, so that a ``def`` argument is checked with them written in
    as emission writes them; before, no binding is known to be free of an
    error of its own, so none is written in."""

    if let_scope.reason not in {
        ProjectLetScopeFactsReason.UPSTREAM_CONCRETE,
        ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED,
        ProjectLetScopeFactsReason.MISSING_OR_UNKNOWN_VALUE_TYPE,
    }:
        return values
    assert let_scope.definition is not None
    return LetValues(
        values, _let_names_with_diagnostics(let_scope.definition, let_scope.diagnostics)
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
) -> Mapping[
    _DerivedRelation | SetRelationDef | ValuesRelationDef | TableFunctionRelationDef,
    RowSchema,
]:
    if isinstance(
        upstream_definition,
        (
            TableDef,
            QueryDef,
            SetRelationDef,
            ValuesRelationDef,
            TableFunctionRelationDef,
        ),
    ):
        return {upstream_definition: row_schema}
    return {}


def _binding_expressions(
    bindings: tuple[LetBinding, ...],
    normalized_bindings: Mapping[LetBinding, Expression] | None = None,
) -> Mapping[str, Expression]:
    expressions: dict[str, Expression] = {}
    for binding in bindings:
        if binding.name not in expressions:
            expressions[binding.name] = (normalized_bindings or {}).get(
                binding, binding.expression
            )
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
