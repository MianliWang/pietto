"""Private schema-v2 preservation of existing semantic and project facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessReason,
    ProjectAggregateGroupedClauseReadinessStatus,
    _effective_field_let_expression,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_persistence import (
    _is_project_aggregate_grouped_definition,
)
from pietto._project.aggregate_grouped_schema import (
    _effective_group_key_expression,
)
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolNamespace,
    _project_direct_relation_row_schema,
    _project_relation_row_schema_state_from_result,
)
from pietto._project.module_carrier import (
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalogSet,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionEnvironment,
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionSet,
    ProjectModuleRelationRowFact,
    ProjectResolvedModuleRelationReference,
)
from pietto._project.row_expression_schema import (
    ProjectExpressionSchemaResult,
    adapt_project_row_expression_schema,
)
from pietto._project.row_expression_type_facts import (
    build_project_row_expression_value_types,
    project_row_schema_to_semantic_row_schema,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.window_persistence import (
    _final_schema as _final_window_schema,
    _window_fact_matches_source,
)
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    _PROJECT_NAMED_WINDOW_INTEGRATION_DEFERRED,
    _build_window_result_project_fact,
    _project_window_analysis_boundary,
)
from pietto._window_identity import WindowFunctionIdentity
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    IsNullExpr,
    LetBinding,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    SelectItem,
    SourceDef,
    Span,
    TableDef,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    effective_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
)
from pietto.semantic.capability_aggregates import _AGGREGATE_CAPABILITY_FACTS
from pietto.semantic.capability_contexts import _CAPABILITY_CONTEXT_FACTS
from pietto.semantic.capability_facts import (
    CapabilityFact,
    CapabilityKey,
)
from pietto.semantic.capability_inventory import _CAPABILITY_FACTS
from pietto.semantic.capability_lookup import (
    CapabilityLookupResult,
    lookup_capability,
)
from pietto.semantic.capability_providers import (
    canonical_capability_provider_inputs,
)
from pietto.semantic.capability_signatures import _CAPABILITY_SIGNATURE_FACTS
from pietto.semantic.capability_windows import _WINDOW_CAPABILITY_FACTS
from pietto.semantic.generic_compatibility import GenericSignature
from pietto.semantic.model import RowSchema as SemanticRowSchema
from pietto.semantic.model import ValueType
from pietto.semantic.nullability_formulas import SignatureResultFormula
from pietto.semantic.window_analysis import (
    _CUME_DIST_RESULT_FORMULA,
    _CUME_DIST_SIGNATURE,
    _DISTRIBUTION_FUNCTIONS,
    _NTILE_RESULT_FORMULA,
    _NTILE_SIGNATURE,
    _PERCENT_RANK_RESULT_FORMULA,
    _PERCENT_RANK_SIGNATURE,
    _RANKING_POLICIES,
    _RANKING_RESULT_FORMULA,
    _RANKING_SIGNATURE,
    analyze_window_expression,
)
from pietto.semantic.window_input_analysis import build_window_input_scope
from pietto.semantic.window_navigation_analysis import (
    _BOUNDARY_RESULT_FORMULA,
    _FRAME_VALUE_IDENTITIES,
    _FRAME_VALUE_RESULT_FORMULA,
    _FRAME_VALUE_SIGNATURE,
    _NAVIGATION_IDENTITIES,
    _NAVIGATION_SIGNATURE,
    _NTH_VALUE_RESULT_FORMULA,
    _NTH_VALUE_SIGNATURE,
    _ZERO_ALWAYS_NULL_RESULT_FORMULA,
    _ZERO_RESULT_FORMULA,
)
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowExpressionUnsupported,
    WindowResultAvailabilityKind,
)

__all__: tuple[str, ...] = ()

_DerivedRelation = TableDef | QueryDef
_RelationDefinition = SourceDef | TableDef | QueryDef
_WindowAnalysis = WindowExpressionAnalysis | WindowExpressionUnsupported
_NAMED_WINDOW_DIAGNOSTIC_CODES = frozenset(
    {"PIE-S2110", "PIE-S2111", "PIE-S2112", "PIE-S2113"}
)


class ProjectModuleFactOccurrenceRole(StrEnum):
    """Closed source-occurrence roles retained by the Slice 12 sidecar."""

    RELATION_INPUT = "relation_input"
    LET_VALUE = "let_value"
    SELECT_VALUE = "select_value"
    GROUP_KEY = "group_key"
    SATISFYING = "satisfying"
    GROUPED_ORDER = "grouped_order"
    WINDOW_PARTITION = "window_partition"
    WINDOW_ORDER = "window_order"
    WINDOW_ARGUMENT = "window_argument"
    WINDOW_DEFAULT = "window_default"


class ProjectModuleCandidateBucketStatus(StrEnum):
    """Availability of one complete, source-preserved candidate bucket."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"


def _require_tuple(
    values: object,
    item_type: type[object] | tuple[type[object], ...],
    label: str,
) -> None:
    if type(values) is not tuple:
        raise TypeError(f"{label} requires an exact tuple.")
    if any(not isinstance(item, item_type) for item in values):
        raise TypeError(f"{label} contains an invalid item.")


def _relation_state_from_aggregate_grouped_clause_readiness(
    readiness: ProjectAggregateGroupedClauseReadiness,
) -> ProjectRelationRowSchemaState:
    """Reduce one complete clause-readiness carrier without partial publication."""

    if type(readiness) is not ProjectAggregateGroupedClauseReadiness:
        raise TypeError("Clause-readiness reduction requires an exact carrier.")
    finalization_state = readiness.finalization.state
    if (
        readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
    ):
        if (
            finalization_state.status is ProjectRelationRowSchemaStatus.CONCRETE
            or readiness.status.value != finalization_state.status.value
        ):
            raise ValueError("Non-concrete finalization readiness is inconsistent.")
        return finalization_state
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        and readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY
    ):
        if finalization_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            raise ValueError("Ready clauses require a concrete finalization.")
        return finalization_state
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        and readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=ProjectRowSchema(is_unknown=True),
            reason=(
                ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
            ),
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        and readiness.reason
        in {
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        }
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=ProjectRowSchema(is_unknown=True),
            reason=ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
        and readiness.reason
        is ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        )
    if (
        readiness.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
        and readiness.reason
        in {
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        }
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=(
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
            ),
        )
    raise ValueError("Unsupported aggregate/grouped clause-readiness outcome.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleWindowSignatureFact:
    """One exact existing window identity, signature, and result formula tuple."""

    identity: WindowFunctionIdentity
    signature: GenericSignature
    result_formulas: tuple[SignatureResultFormula, ...]

    def __post_init__(self) -> None:
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("Window signature fact requires an exact identity.")
        if type(self.signature) is not GenericSignature:
            raise TypeError("Window signature fact requires an exact signature.")
        _require_tuple(
            self.result_formulas,
            SignatureResultFormula,
            "Window result formulas",
        )
        if not self.result_formulas or any(
            formula.signature is not self.signature for formula in self.result_formulas
        ):
            raise ValueError("Window formulas must retain their exact signature.")


def _build_canonical_window_signature_facts() -> tuple[
    ProjectModuleWindowSignatureFact,
    ...,
]:
    ranking = tuple(
        ProjectModuleWindowSignatureFact(
            identity=identity,
            signature=_RANKING_SIGNATURE,
            result_formulas=(_RANKING_RESULT_FORMULA,),
        )
        for identity, _policy in _RANKING_POLICIES
    )
    distribution_signatures = {
        "percent_rank": (_PERCENT_RANK_SIGNATURE, _PERCENT_RANK_RESULT_FORMULA),
        "cume_dist": (_CUME_DIST_SIGNATURE, _CUME_DIST_RESULT_FORMULA),
        "ntile": (_NTILE_SIGNATURE, _NTILE_RESULT_FORMULA),
    }
    distribution = tuple(
        ProjectModuleWindowSignatureFact(
            identity=identity,
            signature=distribution_signatures[identity.name][0],
            result_formulas=(distribution_signatures[identity.name][1],),
        )
        for identity, _policy, _signature, _formula in _DISTRIBUTION_FUNCTIONS
    )
    navigation = tuple(
        ProjectModuleWindowSignatureFact(
            identity=identity,
            signature=_NAVIGATION_SIGNATURE,
            result_formulas=(
                _BOUNDARY_RESULT_FORMULA,
                _ZERO_RESULT_FORMULA,
                _ZERO_ALWAYS_NULL_RESULT_FORMULA,
            ),
        )
        for identity, _direction in _NAVIGATION_IDENTITIES
    )
    frame_value = tuple(
        ProjectModuleWindowSignatureFact(
            identity=identity,
            signature=(
                _NTH_VALUE_SIGNATURE
                if identity.name == "nth_value"
                else _FRAME_VALUE_SIGNATURE
            ),
            result_formulas=(
                _NTH_VALUE_RESULT_FORMULA
                if identity.name == "nth_value"
                else _FRAME_VALUE_RESULT_FORMULA,
            ),
        )
        for identity, _function in _FRAME_VALUE_IDENTITIES
    )
    return (*ranking, *distribution, *navigation, *frame_value)


_CANONICAL_WINDOW_SIGNATURE_FACTS = _build_canonical_window_signature_facts()


def _canonical_window_signature(
    identity: WindowFunctionIdentity,
) -> ProjectModuleWindowSignatureFact | None:
    matches = tuple(
        fact for fact in _CANONICAL_WINDOW_SIGNATURE_FACTS if fact.identity == identity
    )
    if len(matches) > 1:
        raise AssertionError("Canonical window signature identities must be unique.")
    return matches[0] if matches else None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCapabilityFactInventory:
    """The five named existing capability tuples and non-lossy lookup inputs."""

    inventory_facts: tuple[CapabilityFact, ...]
    signature_facts: tuple[CapabilityFact, ...]
    aggregate_facts: tuple[CapabilityFact, ...]
    window_facts: tuple[CapabilityFact, ...]
    context_facts: tuple[CapabilityFact, ...]
    window_signatures: tuple[ProjectModuleWindowSignatureFact, ...]
    result_roles: tuple[ProjectRowResultRole, ...]

    def __post_init__(self) -> None:
        for label, facts, expected in (
            (
                "Inventory capability facts",
                self.inventory_facts,
                _CAPABILITY_FACTS,
            ),
            (
                "Signature capability facts",
                self.signature_facts,
                _CAPABILITY_SIGNATURE_FACTS,
            ),
            (
                "Aggregate capability facts",
                self.aggregate_facts,
                _AGGREGATE_CAPABILITY_FACTS,
            ),
            (
                "Window capability facts",
                self.window_facts,
                _WINDOW_CAPABILITY_FACTS,
            ),
            (
                "Context capability facts",
                self.context_facts,
                _CAPABILITY_CONTEXT_FACTS,
            ),
        ):
            _require_tuple(facts, CapabilityFact, label)
            if facts is not expected:
                raise ValueError(f"{label} must retain its exact canonical tuple.")
        _require_tuple(
            self.window_signatures,
            ProjectModuleWindowSignatureFact,
            "Window signature inventory",
        )
        if self.window_signatures is not _CANONICAL_WINDOW_SIGNATURE_FACTS:
            raise ValueError(
                "Window signature inventory must retain its exact canonical tuple."
            )
        _require_tuple(self.result_roles, ProjectRowResultRole, "Result-role inventory")
        if tuple(fact.identity.name for fact in self.window_signatures) != (
            "row_number",
            "rank",
            "dense_rank",
            "percent_rank",
            "cume_dist",
            "ntile",
            "lag",
            "lead",
            "first_value",
            "last_value",
            "nth_value",
        ):
            raise ValueError(
                "Window signature inventory must retain all eleven identities."
            )
        if self.result_roles != tuple(ProjectRowResultRole):
            raise ValueError("Result-role inventory must retain exact enum order.")

    def lookup(self, key: CapabilityKey) -> CapabilityLookupResult:
        """Dispatch one exact key through its established provider contract."""

        if type(key) is not CapabilityKey:
            raise TypeError("Capability inventory lookup requires an exact key.")
        inputs = canonical_capability_provider_inputs(key)
        return lookup_capability(
            inputs.key,
            inputs.facts,
            domain_complete=inputs.domain_complete,
            unknown_reason=inputs.unknown_reason,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleExpressionReferenceFact:
    """One exact expression leaf and every retained local candidate."""

    owner: ProjectDeclarationOccurrence
    role: ProjectModuleFactOccurrenceRole
    container_ordinal: int
    dependency_ordinal: int
    expression: NameExpr | DottedNameExpr
    local_name: str
    input_field: ProjectRowField | None
    let_candidates: tuple[LetBinding, ...] = ()
    selected_output_candidates: tuple[SelectItem, ...] = ()
    status: ProjectModuleCandidateBucketStatus = (
        ProjectModuleCandidateBucketStatus.UNKNOWN
    )

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Expression reference requires an exact owner.")
        if type(self.role) is not ProjectModuleFactOccurrenceRole:
            raise TypeError("Expression reference requires an exact role.")
        if type(self.container_ordinal) is not int or self.container_ordinal < 0:
            raise ValueError("Expression reference container ordinal is invalid.")
        if type(self.dependency_ordinal) is not int or self.dependency_ordinal < 0:
            raise ValueError("Expression reference dependency ordinal is invalid.")
        if type(self.expression) not in {NameExpr, DottedNameExpr}:
            raise TypeError("Expression reference requires a direct name leaf.")
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Expression reference requires a local lookup name.")
        if (
            self.input_field is not None
            and type(self.input_field) is not ProjectRowField
        ):
            raise TypeError("Expression reference input field must be exact.")
        _require_tuple(self.let_candidates, LetBinding, "Let candidate bucket")
        _require_tuple(
            self.selected_output_candidates,
            SelectItem,
            "Selected-output candidate bucket",
        )
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Expression reference requires an exact status.")
        if type(self.expression) is DottedNameExpr:
            if self.let_candidates or self.selected_output_candidates:
                raise ValueError(
                    "Qualified expression references cannot carry local candidates."
                )
            if (
                self.status is ProjectModuleCandidateBucketStatus.CONCRETE
                and self.input_field is None
            ):
                raise ValueError(
                    "Concrete qualified expression references require an input field."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleLetBindingFact:
    """One source-ordered let binding without name-map compression."""

    owner: ProjectDeclarationOccurrence
    binding_ordinal: int
    binding: LetBinding
    scope_facts: ProjectRelationLetScopeFacts
    value_type: ValueType | None
    references: tuple[ProjectModuleExpressionReferenceFact, ...] = ()

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Let binding fact requires an exact owner.")
        if type(self.binding_ordinal) is not int or self.binding_ordinal < 0:
            raise ValueError("Let binding ordinal is invalid.")
        if type(self.binding) is not LetBinding:
            raise TypeError("Let binding fact requires an exact binding.")
        if type(self.scope_facts) is not ProjectRelationLetScopeFacts:
            raise TypeError("Let binding fact requires exact scope facts.")
        if self.value_type is not None and type(self.value_type) is not ValueType:
            raise TypeError("Let binding value type must be exact.")
        _require_tuple(
            self.references,
            ProjectModuleExpressionReferenceFact,
            "Let reference facts",
        )
        expected_leaves = _direct_name_leaves(self.binding.expression)
        if len(self.references) != len(expected_leaves) or any(
            reference.owner is not self.owner
            or reference.role is not ProjectModuleFactOccurrenceRole.LET_VALUE
            or reference.container_ordinal != self.binding_ordinal
            or reference.dependency_ordinal != dependency_ordinal
            or reference.expression is not expected_leaf
            for dependency_ordinal, (reference, expected_leaf) in enumerate(
                zip(self.references, expected_leaves, strict=True)
            )
        ):
            raise ValueError("Let references must retain the exact source ledger.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleSelectFact:
    """One selected output occurrence and its existing retained facts."""

    owner: ProjectDeclarationOccurrence
    selected_output_ordinal: int
    item: SelectItem
    output_name: str | None
    expression_schema: ProjectExpressionSchemaResult | None
    field: ProjectRowField | None
    aggregate_result_fact: ProjectAggregateResultFact | None
    references: tuple[ProjectModuleExpressionReferenceFact, ...] = ()

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Select fact requires an exact owner.")
        if (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
        ):
            raise ValueError("Selected-output ordinal is invalid.")
        if type(self.item) is not SelectItem:
            raise TypeError("Select fact requires an exact select item.")
        if self.output_name is not None and (
            type(self.output_name) is not str or not self.output_name
        ):
            raise ValueError("Select output name must be non-empty.")
        if (
            self.expression_schema is not None
            and type(self.expression_schema) is not ProjectExpressionSchemaResult
        ):
            raise TypeError("Select expression schema must be exact.")
        if self.field is not None and type(self.field) is not ProjectRowField:
            raise TypeError("Select field must be exact.")
        if (
            self.aggregate_result_fact is not None
            and type(self.aggregate_result_fact) is not ProjectAggregateResultFact
        ):
            raise TypeError("Select aggregate result fact must be exact.")
        _require_tuple(
            self.references,
            ProjectModuleExpressionReferenceFact,
            "Select reference facts",
        )
        expected_leaves = (
            ()
            if type(self.item.expression) is WindowExpr
            else _direct_name_leaves(self.item.expression)
        )
        if len(self.references) != len(expected_leaves) or any(
            reference.owner is not self.owner
            or reference.role is not ProjectModuleFactOccurrenceRole.SELECT_VALUE
            or reference.container_ordinal != self.selected_output_ordinal
            or reference.dependency_ordinal != dependency_ordinal
            or reference.expression is not expected_leaf
            for dependency_ordinal, (reference, expected_leaf) in enumerate(
                zip(self.references, expected_leaves, strict=True)
            )
        ):
            raise ValueError("Select references must retain the exact source ledger.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleClauseDependencyFact:
    """One source clause occurrence and its complete candidate bucket."""

    owner: ProjectDeclarationOccurrence
    role: ProjectModuleFactOccurrenceRole
    source_ordinal: int
    source_occurrence: GroupByItem | OrderItem | NameExpr | CallExpr
    target_occurrences: tuple[SelectItem | GroupByItem, ...] = ()
    target_fields: tuple[ProjectRowField, ...] = ()
    aggregate_result_facts: tuple[ProjectAggregateResultFact, ...] = ()
    status: ProjectModuleCandidateBucketStatus = (
        ProjectModuleCandidateBucketStatus.ABSENT
    )

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Clause dependency requires an exact owner.")
        if type(self.role) is not ProjectModuleFactOccurrenceRole:
            raise TypeError("Clause dependency requires an exact role.")
        if self.role not in {
            ProjectModuleFactOccurrenceRole.GROUP_KEY,
            ProjectModuleFactOccurrenceRole.SATISFYING,
            ProjectModuleFactOccurrenceRole.GROUPED_ORDER,
        }:
            raise ValueError("Clause dependency has an invalid role.")
        if type(self.source_ordinal) is not int or self.source_ordinal < 0:
            raise ValueError("Clause dependency source ordinal is invalid.")
        if not isinstance(
            self.source_occurrence,
            (GroupByItem, OrderItem, NameExpr, CallExpr),
        ):
            raise TypeError("Clause dependency requires an exact source occurrence.")
        _require_tuple(
            self.target_occurrences,
            (SelectItem, GroupByItem),
            "Clause target occurrences",
        )
        _require_tuple(self.target_fields, ProjectRowField, "Clause target fields")
        _require_tuple(
            self.aggregate_result_facts,
            ProjectAggregateResultFact,
            "Clause aggregate result facts",
        )
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Clause dependency requires an exact status.")
        if self.role is ProjectModuleFactOccurrenceRole.GROUP_KEY:
            if type(self.source_occurrence) is not GroupByItem:
                raise TypeError("Group-key dependency requires an exact group item.")
            if self.aggregate_result_facts:
                raise ValueError("Group-key dependency cannot carry aggregate facts.")
            if self.target_occurrences and (
                len(self.target_occurrences) != 1
                or self.target_occurrences[0] is not self.source_occurrence
            ):
                raise ValueError(
                    "Group-key target must retain its exact source occurrence."
                )
            if len(self.target_fields) != len(self.target_occurrences):
                raise ValueError(
                    "Group-key target fields must match occurrence cardinality."
                )
        elif self.role is ProjectModuleFactOccurrenceRole.SATISFYING:
            if type(self.source_occurrence) not in {NameExpr, CallExpr}:
                raise TypeError(
                    "Satisfying dependency requires an exact expression occurrence."
                )
        elif type(self.source_occurrence) is not OrderItem:
            raise TypeError("Grouped-order dependency requires an exact order item.")


def _diagnostic_location_is_within_span(
    location: SourceLocation,
    span: Span,
) -> bool:
    if location.path != span.path:
        return False
    start = (location.line, location.column)
    end = (
        location.end_line if location.end_line is not None else location.line,
        location.end_column if location.end_column is not None else location.column,
    )
    return (
        (span.line, span.column)
        <= start
        <= end
        <= (
            span.end_line,
            span.end_column,
        )
    )


def _window_diagnostic_location_is_owned(
    diagnostic: Diagnostic,
    item: SelectItem,
    definition: TableDef | QueryDef,
) -> bool:
    if _diagnostic_location_is_within_span(diagnostic.location, item.expression.span):
        return True
    return diagnostic.code in _NAMED_WINDOW_DIAGNOSTIC_CODES and any(
        _diagnostic_location_is_within_span(diagnostic.location, declaration.span)
        for declaration in definition.named_windows
    )


def _unsupported_window_has_external_diagnostic_owner(reason: str) -> bool:
    return reason == _PROJECT_NAMED_WINDOW_INTEGRATION_DEFERRED or reason.startswith(
        (
            "no-group aggregate context does not admit ",
            "grouped context does not admit ",
        )
    )


def _validate_supported_window_analysis_family(
    expression: WindowExpr,
    analysis: WindowExpressionAnalysis,
) -> None:
    ranking_matches = tuple(
        policy
        for identity, policy in _RANKING_POLICIES
        if identity == expression.identity
    )
    distribution_matches = tuple(
        definition
        for definition in _DISTRIBUTION_FUNCTIONS
        if definition[0] == expression.identity
    )
    navigation_matches = tuple(
        direction
        for identity, direction in _NAVIGATION_IDENTITIES
        if identity == expression.identity
    )
    frame_value_matches = tuple(
        function
        for identity, function in _FRAME_VALUE_IDENTITIES
        if identity == expression.identity
    )
    if (
        sum(
            bool(matches)
            for matches in (
                ranking_matches,
                distribution_matches,
                navigation_matches,
                frame_value_matches,
            )
        )
        != 1
    ):
        raise ValueError(
            "Supported window analysis requires one exact existing family."
        )
    if ranking_matches:
        if (
            len(ranking_matches) != 1
            or analysis.ranking_fact is None
            or analysis.ranking_fact.advance_policy is not ranking_matches[0]
            or analysis.distribution_fact is not None
            or analysis.navigation_fact is not None
            or analysis.frame_value_fact is not None
        ):
            raise ValueError(
                "Ranking analysis must retain its exact existing family payload."
            )
        return
    if distribution_matches:
        if len(distribution_matches) != 1 or analysis.distribution_fact is None:
            raise ValueError(
                "Distribution analysis must retain its exact existing family payload."
            )
        _identity, expected_policy, _signature, _formula = distribution_matches[0]
        expected_bucket_count = (
            cast(LiteralExpr, expression.call.arguments[0]).value
            if expected_policy.value == "balanced_buckets"
            else None
        )
        if (
            analysis.distribution_fact.distribution_policy is not expected_policy
            or analysis.distribution_fact.bucket_count != expected_bucket_count
            or analysis.navigation_fact is not None
            or analysis.frame_value_fact is not None
        ):
            raise ValueError(
                "Distribution analysis must retain its exact existing family payload."
            )
        return
    if navigation_matches:
        if (
            len(navigation_matches) != 1
            or analysis.navigation_fact is None
            or analysis.navigation_fact.direction is not navigation_matches[0]
            or analysis.ranking_fact is not None
            or analysis.distribution_fact is not None
            or analysis.frame_value_fact is not None
        ):
            raise ValueError(
                "Navigation analysis must retain its exact existing family payload."
            )
        return
    if (
        len(frame_value_matches) != 1
        or analysis.frame_value_fact is None
        or analysis.frame_value_fact.function is not frame_value_matches[0]
        or analysis.ranking_fact is not None
        or analysis.distribution_fact is not None
        or analysis.navigation_fact is not None
    ):
        raise ValueError("Frame-value analysis must retain its exact family payload.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleWindowOutputFact:
    """One selected window occurrence, including unsuccessful analysis evidence."""

    owner: ProjectDeclarationOccurrence
    selected_output_ordinal: int
    item: SelectItem
    output_name: str | None
    signature_fact: ProjectModuleWindowSignatureFact | None
    analysis: _WindowAnalysis | None
    project_fact: WindowResultProjectFact | None
    retained_project_fact: WindowResultProjectFact | None
    diagnostics: tuple[Diagnostic, ...] = ()
    status: ProjectModuleCandidateBucketStatus = (
        ProjectModuleCandidateBucketStatus.UNKNOWN
    )
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Window output fact requires an exact owner.")
        if (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
        ):
            raise ValueError("Window output ordinal is invalid.")
        if (
            type(self.item) is not SelectItem
            or type(self.item.expression) is not WindowExpr
        ):
            raise TypeError("Window output fact requires one exact window item.")
        definition = self.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Window output owner requires an exact derived relation.")
        derived = cast(_DerivedRelation, definition)
        if (
            self.selected_output_ordinal >= len(derived.select_items)
            or derived.select_items[self.selected_output_ordinal] is not self.item
            or self.output_name != self.item.alias
        ):
            raise ValueError(
                "Window output must retain the exact owner source occurrence."
            )
        if self.signature_fact is not None and (
            type(self.signature_fact) is not ProjectModuleWindowSignatureFact
        ):
            raise TypeError("Window output signature fact must be exact.")
        if type(self.analysis) not in {
            WindowExpressionAnalysis,
            WindowExpressionUnsupported,
        }:
            raise TypeError("Window output requires an exact analysis carrier.")
        if (
            self.project_fact is not None
            and type(self.project_fact) is not WindowResultProjectFact
        ):
            raise TypeError("Window output project fact must be exact.")
        if (
            self.retained_project_fact is not None
            and type(self.retained_project_fact) is not WindowResultProjectFact
        ):
            raise TypeError("Window output retained project fact must be exact.")
        if (
            self.project_fact is not None
            and self.retained_project_fact is not self.project_fact
        ):
            raise ValueError(
                "Window project evidence must share its exact retained fact."
            )
        _require_tuple(self.diagnostics, Diagnostic, "Window output diagnostics")
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Window output requires an exact status.")
        if self.status in {
            ProjectModuleCandidateBucketStatus.ABSENT,
            ProjectModuleCandidateBucketStatus.AMBIGUOUS,
        }:
            raise ValueError("A syntactic window output cannot be absent or ambiguous.")
        if self.reason is not None and (
            type(self.reason) is not str or not self.reason
        ):
            raise ValueError("Window output reason must be non-empty.")

        analysis = self.analysis
        if type(analysis) is WindowExpressionAnalysis:
            semantic_fact = analysis.semantic_fact
            occurrence = semantic_fact.occurrence
            analysis_expression = semantic_fact.expression
        elif type(analysis) is WindowExpressionUnsupported:
            semantic_fact = None
            occurrence = analysis.occurrence
            analysis_expression = analysis.expression
        else:
            raise AssertionError("validated window analysis type was not retained")
        expected_source_id = (
            self.item.expression.span.path or self.owner.identity.module_path
        )
        if (
            analysis_expression is not self.item.expression
            or occurrence.source_id != expected_source_id
            or occurrence.relation_name != derived.name
            or occurrence.selected_output_ordinal != self.selected_output_ordinal
            or occurrence.span is not self.item.expression.span
        ):
            raise ValueError(
                "Window analysis must retain the exact owner source occurrence."
            )
        expected_signature = _canonical_window_signature(self.item.expression.identity)
        if self.signature_fact is not None and (
            self.signature_fact.identity != self.item.expression.identity
        ):
            raise ValueError("Window signature must match the exact window identity.")
        if expected_signature is None:
            if self.signature_fact is not None or type(analysis) is not (
                WindowExpressionUnsupported
            ):
                raise ValueError(
                    "Unknown window identity requires exact unsupported evidence."
                )
        elif self.signature_fact is not expected_signature:
            raise ValueError(
                "Window output must retain its exact static signature from the "
                "canonical inventory."
            )
        if type(analysis) is WindowExpressionAnalysis:
            _validate_supported_window_analysis_family(
                self.item.expression,
                analysis,
            )
            partition_bindings = analysis.partition_binding_fact.bindings
            order_bindings = analysis.order_binding_fact.bindings
            if len(partition_bindings) != len(
                self.item.expression.spec.partition_by
            ) or any(
                binding.expression is not expression
                for binding, expression in zip(
                    partition_bindings,
                    self.item.expression.spec.partition_by,
                    strict=True,
                )
            ):
                raise ValueError(
                    "Window partition analysis must retain exact source children."
                )
            if len(order_bindings) != len(self.item.expression.spec.order_by) or any(
                binding.order_item is not item
                for binding, item in zip(
                    order_bindings,
                    self.item.expression.spec.order_by,
                    strict=True,
                )
            ):
                raise ValueError(
                    "Window order analysis must retain exact source children."
                )
            navigation = analysis.navigation_fact
            if navigation is not None:
                arguments = self.item.expression.call.arguments
                if navigation.value_expression is not arguments[0]:
                    raise ValueError(
                        "Window navigation analysis must retain argument zero."
                    )
                if len(arguments) > 1 and (
                    navigation.offset_fact.expression is not arguments[1]
                ):
                    raise ValueError(
                        "Window navigation analysis must retain argument one."
                    )
                if len(arguments) > 2 and (
                    navigation.default_fact.expression is not arguments[2]
                ):
                    raise ValueError(
                        "Window navigation analysis must retain argument two."
                    )
        if type(analysis) is WindowExpressionUnsupported:
            external_diagnostic = _unsupported_window_has_external_diagnostic_owner(
                analysis.reason
            )
            if external_diagnostic and self.diagnostics:
                raise ValueError(
                    "Externally diagnosed window evidence cannot invent diagnostics."
                )
            if not external_diagnostic and not self.diagnostics:
                raise ValueError(
                    "Unsupported window evidence must retain analyzer diagnostics."
                )
            if any(
                diagnostic.severity is not Severity.ERROR
                or diagnostic.code
                not in _NAMED_WINDOW_DIAGNOSTIC_CODES
                | {
                    "PIE-S2102",
                    "PIE-S2103",
                    "PIE-S2104",
                }
                or not _window_diagnostic_location_is_owned(
                    diagnostic,
                    self.item,
                    derived,
                )
                for diagnostic in self.diagnostics
            ):
                raise ValueError(
                    "Window diagnostics must retain exact analyzer source evidence."
                )
        elif self.diagnostics:
            raise ValueError("Supported window evidence cannot invent diagnostics.")
        if self.retained_project_fact is not None:
            if semantic_fact is None:
                raise ValueError(
                    "Retained window project fact requires the exact supported "
                    "analysis."
                )
            result_identity = self.retained_project_fact.result_identity
            if (
                self.retained_project_fact.semantic_fact is not semantic_fact
                or result_identity.definition is not derived
                or result_identity.output_name != self.output_name
                or result_identity.occurrence is not semantic_fact.occurrence
            ):
                raise ValueError(
                    "Retained window project fact must preserve the exact analysis "
                    "identity."
                )
        if type(analysis) is WindowExpressionUnsupported:
            if (
                self.project_fact is not None
                or self.retained_project_fact is not None
                or self.status is ProjectModuleCandidateBucketStatus.CONCRETE
            ):
                raise ValueError(
                    "Unsupported window analysis cannot publish concrete project evidence."
                )
        elif self.project_fact is None:
            if self.status is ProjectModuleCandidateBucketStatus.CONCRETE:
                raise ValueError(
                    "Concrete window output requires its exact project fact."
                )
        else:
            if semantic_fact is None:
                raise AssertionError(
                    "supported project evidence lost its semantic fact"
                )
            expected_status = {
                WindowResultAvailabilityKind.CONCRETE: (
                    ProjectModuleCandidateBucketStatus.CONCRETE
                ),
                WindowResultAvailabilityKind.UNKNOWN: (
                    ProjectModuleCandidateBucketStatus.UNKNOWN
                ),
                WindowResultAvailabilityKind.DEFERRED: (
                    ProjectModuleCandidateBucketStatus.DEFERRED
                ),
                WindowResultAvailabilityKind.BLOCKED: (
                    ProjectModuleCandidateBucketStatus.BLOCKED
                ),
            }[semantic_fact.result.kind]
            if (
                self.status is not expected_status
                or self.reason != semantic_fact.result.reason
            ):
                raise ValueError(
                    "Window project evidence must match exact analysis availability."
                )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationSemanticFacts:
    """All existing facts retained for one exact relation declaration occurrence."""

    owner: ProjectDeclarationOccurrence
    base_row_fact: ProjectModuleRelationRowFact
    resolution: ProjectResolvedModuleRelationReference | None
    state: ProjectRelationRowSchemaState
    let_scope_facts: ProjectRelationLetScopeFacts | None
    let_bindings: tuple[ProjectModuleLetBindingFact, ...] = ()
    select_facts: tuple[ProjectModuleSelectFact, ...] = ()
    group_key_occurrences: tuple[GroupByItem, ...] = ()
    aggregate_grouped_clause_readiness: (
        ProjectAggregateGroupedClauseReadiness | None
    ) = None
    clause_dependencies: tuple[ProjectModuleClauseDependencyFact, ...] = ()
    aggregate_result_facts: tuple[ProjectAggregateResultFact, ...] = ()
    window_outputs: tuple[ProjectModuleWindowOutputFact, ...] = ()
    helper_diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Relation semantic facts require an exact owner.")
        if type(self.base_row_fact) is not ProjectModuleRelationRowFact:
            raise TypeError("Relation semantic facts require a Slice 10 row fact.")
        if self.base_row_fact.owner is not self.owner:
            raise ValueError("Relation semantic facts must retain the exact owner.")
        if (
            self.resolution is not None
            and type(self.resolution) is not ProjectResolvedModuleRelationReference
        ):
            raise TypeError("Relation semantic resolution must be exact.")
        if type(self.state) is not ProjectRelationRowSchemaState:
            raise TypeError("Relation semantic facts require an exact state.")
        if (
            self.let_scope_facts is not None
            and type(self.let_scope_facts) is not ProjectRelationLetScopeFacts
        ):
            raise TypeError("Relation semantic let scope must be exact.")
        _require_tuple(self.let_bindings, ProjectModuleLetBindingFact, "Let facts")
        _require_tuple(self.select_facts, ProjectModuleSelectFact, "Select facts")
        _require_tuple(self.group_key_occurrences, GroupByItem, "Group-key occurrences")
        if (
            self.aggregate_grouped_clause_readiness is not None
            and type(self.aggregate_grouped_clause_readiness)
            is not ProjectAggregateGroupedClauseReadiness
        ):
            raise TypeError("Aggregate/grouped clause readiness must be exact.")
        if (
            self.aggregate_grouped_clause_readiness is not None
            and self.aggregate_grouped_clause_readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
            and self.state
            != _relation_state_from_aggregate_grouped_clause_readiness(
                self.aggregate_grouped_clause_readiness
            )
        ):
            raise ValueError(
                "Non-concrete clause readiness must control the relation state."
            )
        _require_tuple(
            self.clause_dependencies,
            ProjectModuleClauseDependencyFact,
            "Clause dependencies",
        )
        _require_tuple(
            self.aggregate_result_facts,
            ProjectAggregateResultFact,
            "Aggregate result facts",
        )
        _require_tuple(
            self.window_outputs,
            ProjectModuleWindowOutputFact,
            "Window output facts",
        )
        _require_tuple(self.helper_diagnostics, Diagnostic, "Helper diagnostics")
        if any(
            fact.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
            for fact in self.clause_dependencies
        ) and any(output.project_fact is not None for output in self.window_outputs):
            raise ValueError(
                "Clause-ambiguous semantic facts cannot publish window project "
                "evidence."
            )
        if self.state.status is not ProjectRelationRowSchemaStatus.CONCRETE and (
            self.aggregate_result_facts
            or any(fact.aggregate_result_fact is not None for fact in self.select_facts)
        ):
            raise ValueError(
                "Non-concrete semantic facts cannot publish aggregate results."
            )
        definition = self.owner.definition
        if type(definition) is SourceDef:
            if self.state is not self.base_row_fact.state:
                raise ValueError(
                    "Source semantic state must retain its exact Slice 10 row state."
                )
            if any(
                (
                    self.resolution is not None,
                    self.let_scope_facts is not None,
                    bool(self.let_bindings),
                    bool(self.select_facts),
                    bool(self.group_key_occurrences),
                    self.aggregate_grouped_clause_readiness is not None,
                    bool(self.clause_dependencies),
                    bool(self.aggregate_result_facts),
                    bool(self.window_outputs),
                    bool(self.helper_diagnostics),
                )
            ):
                raise ValueError("Source semantic facts cannot invent derived facts.")
            return
        if type(definition) not in {TableDef, QueryDef}:
            raise ValueError("Relation semantic facts require a relation definition.")

        derived = cast(_DerivedRelation, definition)
        if self.let_scope_facts is None:
            raise ValueError("Derived semantic facts require exact let-scope facts.")
        if (
            self.resolution is not None
            and self.resolution.reference.owner is not self.owner
        ):
            raise ValueError("Relation resolution must retain the exact owner.")
        if (
            self.aggregate_grouped_clause_readiness is not None
            and self.aggregate_grouped_clause_readiness.definition is not derived
        ):
            raise ValueError("Clause readiness must retain the exact definition.")

        owner_children = (
            *self.let_bindings,
            *self.select_facts,
            *self.clause_dependencies,
            *self.window_outputs,
        )
        if any(child.owner is not self.owner for child in owner_children):
            raise ValueError("Relation children must retain the exact owner.")

        expected_bindings = (
            () if derived.let_clause is None else tuple(derived.let_clause.bindings)
        )
        if (
            self.let_scope_facts.clause is not derived.let_clause
            or len(self.let_scope_facts.bindings) != len(expected_bindings)
            or any(
                actual is not expected
                for actual, expected in zip(
                    self.let_scope_facts.bindings,
                    expected_bindings,
                    strict=True,
                )
            )
            or len(self.let_bindings) != len(expected_bindings)
            or any(
                fact.binding_ordinal != ordinal
                or fact.binding is not expected
                or fact.scope_facts is not self.let_scope_facts
                for ordinal, (fact, expected) in enumerate(
                    zip(self.let_bindings, expected_bindings, strict=True)
                )
            )
        ):
            raise ValueError("Let facts must retain the exact source ledger.")

        expected_select_items = tuple(derived.select_items)
        if len(self.select_facts) != len(expected_select_items) or any(
            fact.selected_output_ordinal != ordinal
            or fact.item is not expected
            or fact.output_name != _projection_output_name(expected)
            for ordinal, (fact, expected) in enumerate(
                zip(self.select_facts, expected_select_items, strict=True)
            )
        ):
            raise ValueError("Select facts must retain the exact source ledger.")

        expected_group_items = (
            ()
            if derived.group_by_clause is None
            else tuple(derived.group_by_clause.items)
        )
        if len(self.group_key_occurrences) != len(expected_group_items) or any(
            actual is not expected
            for actual, expected in zip(
                self.group_key_occurrences,
                expected_group_items,
                strict=True,
            )
        ):
            raise ValueError("Group keys must retain the exact source ledger.")

        satisfying_occurrences = (
            ()
            if derived.satisfying_clause is None
            else _satisfying_occurrences(derived.satisfying_clause.expression)
        )
        grouped_order_items = (
            ()
            if derived.group_by_clause is None or derived.order_by_clause is None
            else tuple(derived.order_by_clause.items)
        )
        expected_clause_sources = (
            *(
                (ProjectModuleFactOccurrenceRole.GROUP_KEY, ordinal, item)
                for ordinal, item in enumerate(expected_group_items)
            ),
            *(
                (ProjectModuleFactOccurrenceRole.SATISFYING, ordinal, occurrence)
                for ordinal, occurrence in enumerate(satisfying_occurrences)
            ),
            *(
                (ProjectModuleFactOccurrenceRole.GROUPED_ORDER, ordinal, item)
                for ordinal, item in enumerate(grouped_order_items)
            ),
        )
        if len(self.clause_dependencies) != len(expected_clause_sources) or any(
            fact.role is not expected_role
            or fact.source_ordinal != expected_ordinal
            or fact.source_occurrence is not expected_occurrence
            for fact, (
                expected_role,
                expected_ordinal,
                expected_occurrence,
            ) in zip(
                self.clause_dependencies,
                expected_clause_sources,
                strict=True,
            )
        ):
            raise ValueError("Clause dependencies must retain the exact source ledger.")
        for fact in self.clause_dependencies:
            if fact.role is ProjectModuleFactOccurrenceRole.GROUP_KEY:
                continue
            last_ordinal = -1
            for target in fact.target_occurrences:
                matches = tuple(
                    ordinal
                    for ordinal, item in enumerate(expected_select_items)
                    if item is target
                )
                if len(matches) != 1 or matches[0] <= last_ordinal:
                    raise ValueError(
                        "Clause targets must retain source-ordered select identities."
                    )
                last_ordinal = matches[0]

        expected_window_items = tuple(
            (ordinal, item)
            for ordinal, item in enumerate(expected_select_items)
            if type(item.expression) is WindowExpr
        )
        if len(self.window_outputs) != len(expected_window_items) or any(
            fact.selected_output_ordinal != ordinal
            or fact.item is not expected
            or fact.output_name != expected.alias
            for fact, (ordinal, expected) in zip(
                self.window_outputs,
                expected_window_items,
                strict=True,
            )
        ):
            raise ValueError("Window outputs must retain the exact source ledger.")
        if self.state.status is ProjectRelationRowSchemaStatus.CONCRETE and any(
            output.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or output.project_fact is None
            for output in self.window_outputs
        ):
            raise ValueError(
                "Concrete relation window outputs require concrete project evidence."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleSemanticFactEnvironment:
    """One dependency-ordered module and its source-ordered relation facts."""

    module: ProjectLogicalModule
    resolution_environment: ProjectModuleRelationResolutionEnvironment
    relation_facts: tuple[ProjectModuleRelationSemanticFacts, ...] = ()
    _facts_by_definition: Mapping[
        int,
        tuple[ProjectModuleRelationSemanticFacts, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Semantic environment requires an exact module.")
        if (
            type(self.resolution_environment)
            is not ProjectModuleRelationResolutionEnvironment
        ):
            raise TypeError(
                "Semantic environment requires an exact Slice 10 environment."
            )
        if self.resolution_environment.module is not self.module:
            raise ValueError("Semantic environment must retain the exact module.")
        _require_tuple(
            self.relation_facts,
            ProjectModuleRelationSemanticFacts,
            "Module relation semantic facts",
        )
        expected_row_facts = self.resolution_environment.row_facts
        if len(self.relation_facts) != len(expected_row_facts) or any(
            fact.base_row_fact is not expected or fact.owner is not expected.owner
            for fact, expected in zip(
                self.relation_facts,
                expected_row_facts,
                strict=True,
            )
        ):
            raise ValueError(
                "Semantic environment must retain exact ordered Slice 10 row facts."
            )
        for fact in self.relation_facts:
            definition = fact.owner.definition
            expected_resolution: ProjectResolvedModuleRelationReference | None
            if type(definition) is SourceDef:
                expected_resolution = None
            elif type(definition) in {TableDef, QueryDef}:
                derived = cast(_DerivedRelation, definition)
                resolution_bucket = self.resolution_environment.find_from_clause(
                    derived.from_clause
                )
                if len(resolution_bucket) > 1:
                    raise ValueError(
                        "Slice 10 resolution authority cannot have multiple winners."
                    )
                expected_resolution = (
                    resolution_bucket[0] if resolution_bucket else None
                )
            else:
                raise ValueError(
                    "Semantic environment requires exact relation definitions."
                )
            if fact.resolution is not expected_resolution:
                raise ValueError(
                    "Semantic relation must retain its exact Slice 10 resolution."
                )
        buckets: dict[int, list[ProjectModuleRelationSemanticFacts]] = {}
        for fact in self.relation_facts:
            if fact.owner.identity.module_path != self.module.path:
                raise ValueError("Semantic relation fact must be module-local.")
            definition = cast(_RelationDefinition, fact.owner.definition)
            buckets.setdefault(id(definition), []).append(fact)
        object.__setattr__(
            self,
            "_facts_by_definition",
            MappingProxyType(
                {definition: tuple(items) for definition, items in buckets.items()}
            ),
        )

    def find_definition(
        self,
        definition: _RelationDefinition,
    ) -> tuple[ProjectModuleRelationSemanticFacts, ...]:
        """Return the complete exact AST-definition bucket."""

        if type(definition) not in {SourceDef, TableDef, QueryDef}:
            raise TypeError("Semantic fact lookup requires a relation definition.")
        return tuple(
            fact
            for fact in self._facts_by_definition.get(id(definition), ())
            if fact.owner.definition is definition
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ProjectModuleSemanticFactAuthority:
    """Exact Slice 10-rooted authority retained by the Slice 12 product."""

    modules: tuple[ProjectLogicalModule, ...]
    catalogs: ProjectModuleCatalogSet
    relation_resolutions: ProjectModuleRelationResolutionSet
    _existing_fact_projections_bound: bool = field(
        init=False,
        default=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _relation_pre_window_state_projections: tuple[
        ProjectRelationRowSchemaState,
        ...,
    ] = field(
        init=False,
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _relation_fact_projections: tuple[
        ProjectModuleRelationSemanticFacts,
        ...,
    ] = field(
        init=False,
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _relation_clause_dependency_projections: tuple[
        tuple[ProjectModuleClauseDependencyFact, ...],
        ...,
    ] = field(
        init=False,
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _window_analysis_projections: tuple[_WindowAnalysis, ...] = field(
        init=False,
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    _window_diagnostic_projections: tuple[tuple[Diagnostic, ...], ...] = field(
        init=False,
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        _require_tuple(self.modules, ProjectLogicalModule, "Semantic authority modules")
        if type(self.catalogs) is not ProjectModuleCatalogSet:
            raise TypeError("Semantic authority requires exact catalogs.")
        if type(self.relation_resolutions) is not ProjectModuleRelationResolutionSet:
            raise TypeError("Semantic authority requires exact Slice 10 resolutions.")
        _validate_builder_inputs(
            self.modules,
            self.catalogs,
            self.relation_resolutions,
        )


def _exact_relation_fact(
    facts_by_owner: Mapping[int, list[ProjectModuleRelationSemanticFacts]],
    owner: ProjectDeclarationOccurrence,
) -> ProjectModuleRelationSemanticFacts | None:
    matches = tuple(
        fact for fact in facts_by_owner.get(id(owner), ()) if fact.owner is owner
    )
    if len(matches) > 1:
        raise ValueError("Exact upstream owner cannot have multiple semantic facts.")
    return matches[0] if matches else None


def _projectless_window_authority_state(
    *,
    pre_window_state: ProjectRelationRowSchemaState,
    output: ProjectModuleWindowOutputFact,
) -> ProjectRelationRowSchemaState | None:
    if (
        output.project_fact is None
        and pre_window_state.status is not ProjectRelationRowSchemaStatus.CONCRETE
    ):
        return pre_window_state
    return None


def _reduce_window_outputs_to_state(
    *,
    definition: _DerivedRelation,
    base_state: ProjectRelationRowSchemaState,
    outputs: tuple[ProjectModuleWindowOutputFact, ...],
) -> ProjectRelationRowSchemaState:
    if not outputs or base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return base_state
    base_schema = base_state.schema
    if base_schema is None or base_schema.is_unknown:
        raise ValueError("Concrete window base state requires a concrete schema.")
    output_names = tuple(
        name
        for item in definition.select_items
        if (name := _projection_output_name(item)) is not None
    )
    if len(output_names) != len(set(output_names)):
        return _unknown_window_state(
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
        )
    statuses = tuple(output.status for output in outputs)
    if all(
        status is ProjectModuleCandidateBucketStatus.CONCRETE for status in statuses
    ):
        concrete_facts: dict[str, WindowResultProjectFact] = {}
        for output in outputs:
            if output.output_name is None or output.project_fact is None:
                raise ValueError(
                    "Concrete window reduction requires exact named project facts."
                )
            concrete_facts[output.output_name] = output.project_fact
        final_schema = _final_window_schema(
            definition=definition,
            base_schema=base_schema,
            window_result_facts=concrete_facts,
        )
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.CONCRETE,
            schema=final_schema,
            reason=base_state.reason,
        )
    if len(set(statuses)) > 1:
        return _blocked_window_state()
    status = statuses[0]
    if status is ProjectModuleCandidateBucketStatus.UNKNOWN:
        unknown_kinds = tuple(
            "unsupported"
            if type(output.analysis) is WindowExpressionUnsupported
            else "unavailable"
            for output in outputs
        )
        if len(set(unknown_kinds)) > 1:
            return _blocked_window_state()
        return _unknown_window_state(
            ProjectRelationRowSchemaReason.INVALID_WINDOW_OUTPUT
            if unknown_kinds[0] == "unsupported"
            else ProjectRelationRowSchemaReason.UNAVAILABLE_WINDOW_RESULT_FACT
        )
    if status is ProjectModuleCandidateBucketStatus.DEFERRED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.WINDOW_RESULT_DEFERRED,
        )
    return _blocked_window_state()


def _apply_clause_ambiguity_to_window_state(
    state: ProjectRelationRowSchemaState,
    clause_dependencies: tuple[ProjectModuleClauseDependencyFact, ...],
) -> ProjectRelationRowSchemaState:
    if any(
        fact.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
        for fact in clause_dependencies
    ):
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        )
    return state


def _suppress_window_project_facts_after_clause_ambiguity(
    *,
    state: ProjectRelationRowSchemaState,
    clause_dependencies: tuple[ProjectModuleClauseDependencyFact, ...],
    window_outputs: tuple[ProjectModuleWindowOutputFact, ...],
) -> tuple[ProjectModuleWindowOutputFact, ...]:
    if not any(
        fact.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
        for fact in clause_dependencies
    ):
        return window_outputs
    if (
        state.status is not ProjectRelationRowSchemaStatus.BLOCKED
        or state.schema is not None
        or state.reason
        is not ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
    ):
        raise ValueError("Clause ambiguity requires the exact blocked relation state.")
    return tuple(
        replace(
            output,
            project_fact=None,
            status=ProjectModuleCandidateBucketStatus.BLOCKED,
            reason=state.reason.value,
        )
        for output in window_outputs
    )


def _project_symbol_matches_resolution(
    symbol: ProjectSymbol | None,
    resolution: ProjectResolvedModuleRelationReference,
) -> bool:
    if symbol is None:
        return False
    expected = _project_symbol_for_resolution(resolution)
    return (
        symbol.namespace is expected.namespace
        and symbol.kind is expected.kind
        and symbol.name == expected.name
        and symbol.path == expected.path
        and symbol.location == expected.location
        and symbol.definition is expected.definition
    )


def _window_dependency_source_ledger(
    expression: WindowExpr,
) -> tuple[tuple[WindowDependencyRole, Expression], ...]:
    arguments = expression.call.arguments
    value_dependent = expression.identity.name in {
        "lag",
        "lead",
        "first_value",
        "last_value",
        "nth_value",
    }
    offset_navigation = expression.identity.name in {"lag", "lead"}
    argument_sources = (
        (arguments[0],)
        if value_dependent and type(arguments[0]) in {NameExpr, DottedNameExpr}
        else ()
    )
    default_sources = (
        (arguments[2],)
        if offset_navigation
        and len(arguments) == 3
        and type(arguments[2]) in {NameExpr, DottedNameExpr}
        else ()
    )
    relation_sources = () if argument_sources or default_sources else (expression.call,)
    return (
        *((WindowDependencyRole.RELATION_INPUT, source) for source in relation_sources),
        *(
            (WindowDependencyRole.WINDOW_ARGUMENT, source)
            for source in argument_sources
        ),
        *((WindowDependencyRole.WINDOW_DEFAULT, source) for source in default_sources),
        *(
            (WindowDependencyRole.WINDOW_PARTITION, source)
            for source in expression.spec.partition_by
        ),
        *(
            (WindowDependencyRole.WINDOW_ORDER, item.expression)
            for item in expression.spec.order_by
        ),
    )


def _grouped_window_dependency_target(
    *,
    relation: ProjectModuleRelationSemanticFacts,
    source: NameExpr | DottedNameExpr,
) -> tuple[ProjectRowDependencyNode, ProjectRowResultRole] | None:
    definition = cast(_DerivedRelation, relation.owner.definition)
    readiness = relation.aggregate_grouped_clause_readiness
    if readiness is None:
        return None
    base_schema = readiness.finalization.state.schema
    if base_schema is None or base_schema.is_unknown:
        return None
    if type(source) is not NameExpr:
        return None
    output_names = tuple(
        _projection_output_name(item) for item in definition.select_items
    )
    direct_candidates = tuple(
        item
        for item in definition.select_items
        if type(item.expression) is not WindowExpr
        and _projection_output_name(item) == source.name
        and output_names.count(source.name) == 1
        and (field := base_schema.fields.get(source.name)) is not None
        and field.resolved_type.kind is not ProjectResolvedTypeKind.UNKNOWN
        and field.result_role
        in {
            ProjectRowResultRole.GROUP_KEY,
            ProjectRowResultRole.AGGREGATE_RESULT,
        }
    )
    if len(direct_candidates) > 1:
        return None
    target_name: str | None = None
    if len(direct_candidates) == 1:
        target_name = _projection_output_name(direct_candidates[0])
    elif (
        relation.let_scope_facts is not None
        and relation.let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
    ):
        effective = _effective_field_let_expression(
            source,
            let_expressions=relation.let_scope_facts.binding_expressions,
            seen=frozenset(),
        )
        local_name = (
            None
            if effective is None
            else _direct_field_identity(
                effective,
                relation_qualifier=definition.from_clause.source_name,
            )
        )
        group_candidates = tuple(
            item
            for item in definition.select_items
            if type(item.expression) is not WindowExpr
            and type(item.expression) in {NameExpr, DottedNameExpr}
            and (
                effective_item := (
                    cast(DottedNameExpr, item.expression)
                    if type(item.expression) is DottedNameExpr
                    else _effective_field_let_expression(
                        cast(NameExpr, item.expression),
                        let_expressions=(relation.let_scope_facts.binding_expressions),
                        seen=frozenset(),
                    )
                )
            )
            is not None
            and _direct_field_identity(
                effective_item,
                relation_qualifier=definition.from_clause.source_name,
            )
            == local_name
            and (output_name := _projection_output_name(item)) is not None
            and output_names.count(output_name) == 1
            and (field := base_schema.fields.get(output_name)) is not None
            and field.resolved_type.kind is not ProjectResolvedTypeKind.UNKNOWN
            and field.result_role is ProjectRowResultRole.GROUP_KEY
        )
        if group_candidates:
            target_name = _projection_output_name(group_candidates[0])
    if target_name is None:
        return None
    field = base_schema.fields.get(target_name)
    if field is None or field.result_role not in {
        ProjectRowResultRole.GROUP_KEY,
        ProjectRowResultRole.AGGREGATE_RESULT,
    }:
        return None
    return (
        ProjectRowDependencyNode(
            kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
            name=target_name,
            relation_name=definition.name,
            output_name=target_name,
        ),
        field.result_role,
    )


def _expected_window_dependency_target(
    *,
    relation: ProjectModuleRelationSemanticFacts,
    upstream: ProjectModuleRelationSemanticFacts,
    upstream_symbol: ProjectSymbol,
    role: WindowDependencyRole,
    source: Expression,
) -> tuple[ProjectRowDependencyNode, ProjectRowResultRole | None] | None:
    definition = cast(_DerivedRelation, relation.owner.definition)
    if role is WindowDependencyRole.RELATION_INPUT:
        return (
            ProjectRowDependencyNode(
                kind=ProjectRowDependencyNodeKind.RELATION_INPUT,
                name=upstream_symbol.name,
                relation_name=upstream_symbol.name,
                source_name=upstream_symbol.name,
            ),
            None,
        )
    if type(source) not in {NameExpr, DottedNameExpr}:
        return None
    direct_source = cast(NameExpr | DottedNameExpr, source)
    if definition.group_by_clause is not None:
        return _grouped_window_dependency_target(
            relation=relation,
            source=direct_source,
        )
    input_schema = upstream.state.schema
    if input_schema is None or input_schema.is_unknown:
        return None
    name = _direct_field_identity(
        direct_source,
        relation_qualifier=definition.from_clause.source_name,
    )
    if name is None:
        return None
    if name in input_schema.fields:
        return (
            ProjectRowDependencyNode(
                kind=ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
                name=f"{upstream_symbol.name}.{name}",
                relation_name=upstream_symbol.name,
                source_name=upstream_symbol.name,
                field_name=name,
            ),
            None,
        )
    let_scope = relation.let_scope_facts
    if (
        type(direct_source) is NameExpr
        and let_scope is not None
        and let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
        and direct_source.name in let_scope.binding_expressions
        and direct_source.name in let_scope.value_types
    ):
        return (
            ProjectRowDependencyNode(
                kind=ProjectRowDependencyNodeKind.LET_BINDING,
                name=direct_source.name,
                relation_name=definition.name,
                binding_name=direct_source.name,
            ),
            None,
        )
    return None


def _validate_window_dependency_source_ledger(
    *,
    relation: ProjectModuleRelationSemanticFacts,
    upstream: ProjectModuleRelationSemanticFacts,
    output: ProjectModuleWindowOutputFact,
) -> None:
    project_fact = output.retained_project_fact
    resolution = relation.resolution
    if project_fact is None or resolution is None:
        raise ValueError(
            "Retained window project evidence requires exact upstream authority."
        )
    provenance_symbol = project_fact.provenance.symbol
    if not _project_symbol_matches_resolution(provenance_symbol, resolution):
        raise ValueError(
            "Window project provenance must retain exact resolution authority."
        )
    assert provenance_symbol is not None
    expression = cast(WindowExpr, output.item.expression)
    ledger = _window_dependency_source_ledger(expression)
    occurrences = project_fact.dependency_occurrences
    if len(occurrences) != len(ledger):
        raise ValueError("Window dependencies must retain the exact source ledger.")
    role_ordinals: dict[WindowDependencyRole, int] = {}
    for global_ordinal, (occurrence, (role, source)) in enumerate(
        zip(occurrences, ledger, strict=True)
    ):
        role_ordinal = role_ordinals.get(role, 0)
        role_ordinals[role] = role_ordinal + 1
        expected_target = _expected_window_dependency_target(
            relation=relation,
            upstream=upstream,
            upstream_symbol=provenance_symbol,
            role=role,
            source=source,
        )
        expected_location = SourceLocation(
            path=source.span.path,
            line=source.span.line,
            column=source.span.column,
            end_line=source.span.end_line,
            end_column=source.span.end_column,
        )
        if (
            expected_target is None
            or occurrence.global_ordinal != global_ordinal
            or occurrence.role_ordinal != role_ordinal
            or occurrence.role is not role
            or occurrence.location != expected_location
            or occurrence.target != expected_target[0]
            or occurrence.target_result_role is not expected_target[1]
        ):
            raise ValueError(
                "Window dependencies must retain exact source and target authority."
            )


def _validate_relation_window_fact_set_closure(
    *,
    relation: ProjectModuleRelationSemanticFacts,
    upstream: ProjectModuleRelationSemanticFacts | None,
    pre_window_state: ProjectRelationRowSchemaState,
) -> None:
    definition = relation.owner.definition
    if type(definition) is SourceDef:
        if relation.window_outputs:
            raise ValueError("Source relation cannot retain window outputs.")
        if relation.state is not pre_window_state:
            raise ValueError("Source relation must retain its exact base state.")
        return
    if type(definition) not in {TableDef, QueryDef}:
        raise ValueError("Window closure requires an exact relation definition.")
    derived = cast(_DerivedRelation, definition)
    window_state = (
        pre_window_state
        if pre_window_state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        else _reduce_window_outputs_to_state(
            definition=derived,
            base_state=pre_window_state,
            outputs=relation.window_outputs,
        )
    )
    expected_state = _apply_clause_ambiguity_to_window_state(
        window_state,
        relation.clause_dependencies,
    )
    clause_ambiguous = any(
        fact.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
        for fact in relation.clause_dependencies
    )
    if clause_ambiguous and (
        expected_state.status is not ProjectRelationRowSchemaStatus.BLOCKED
        or expected_state.schema is not None
        or expected_state.reason
        is not ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
    ):
        raise ValueError("Clause ambiguity requires the exact blocked relation state.")
    for output in relation.window_outputs:
        expression = cast(WindowExpr, output.item.expression)
        expected_signature = _canonical_window_signature(expression.identity)
        if output.signature_fact is not expected_signature:
            raise ValueError("Window output must retain its exact canonical signature.")
        if output.retained_project_fact is not None:
            if (
                relation.resolution is None
                or upstream is None
                or upstream.owner
                is not relation.resolution.target_symbol.target_occurrence
                or upstream.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            ):
                raise ValueError(
                    "Window project evidence requires exact concrete upstream authority."
                )
            _validate_window_dependency_source_ledger(
                relation=relation,
                upstream=upstream,
                output=output,
            )
        if output.project_fact is not None:
            if clause_ambiguous:
                raise ValueError(
                    "Clause-ambiguous semantic facts cannot publish window project "
                    "evidence."
                )
            continue
        if clause_ambiguous:
            if (
                type(output.analysis) is WindowExpressionAnalysis
                and pre_window_state.status is ProjectRelationRowSchemaStatus.CONCRETE
                and output.retained_project_fact is None
            ):
                raise ValueError(
                    "Clause-ambiguous supported window output must retain its exact "
                    "project evidence."
                )
            expected_status = _candidate_status_from_row_state(expected_state)
            if (
                output.status is not expected_status
                or output.reason != expected_state.reason.value
            ):
                raise ValueError(
                    "Clause-ambiguous window output must retain exact blocked "
                    "availability."
                )
            continue
        if output.retained_project_fact is not None:
            raise ValueError(
                "Retained-only window project evidence requires clause ambiguity."
            )
        authority_state = _projectless_window_authority_state(
            pre_window_state=pre_window_state,
            output=output,
        )
        if authority_state is not None:
            expected_status = _candidate_status_from_row_state(authority_state)
            if (
                output.status is not expected_status
                or output.reason != authority_state.reason.value
            ):
                raise ValueError(
                    "Projectless window output must retain exact upstream availability."
                )
            continue
        analysis = output.analysis
        if type(analysis) is not WindowExpressionUnsupported or (
            output.status is not ProjectModuleCandidateBucketStatus.UNKNOWN
            or output.reason != analysis.reason
        ):
            raise ValueError(
                "Projectless window output must retain exact analyzer availability."
            )
    if relation.state != expected_state:
        raise ValueError(
            "Relation state must retain the deterministic existing window reduction."
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleSemanticFactSet:
    """Complete private Slice 12 preservation product."""

    dependency_order: tuple[ProjectModuleIdentity, ...]
    environments: tuple[ProjectModuleSemanticFactEnvironment, ...]
    issues: tuple[ProjectModuleRelationResolutionIssue, ...]
    capabilities: ProjectModuleCapabilityFactInventory
    authority: _ProjectModuleSemanticFactAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )
    _environments_by_path: Mapping[str, ProjectModuleSemanticFactEnvironment] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _facts_by_owner: Mapping[
        int,
        tuple[ProjectModuleRelationSemanticFacts, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        _require_tuple(self.dependency_order, ProjectModuleIdentity, "Dependency order")
        _require_tuple(
            self.environments,
            ProjectModuleSemanticFactEnvironment,
            "Semantic environments",
        )
        _require_tuple(self.issues, ProjectModuleRelationResolutionIssue, "Issues")
        if type(self.capabilities) is not ProjectModuleCapabilityFactInventory:
            raise TypeError("Semantic fact set requires exact capabilities.")
        if type(self.authority) is not _ProjectModuleSemanticFactAuthority:
            raise TypeError("Semantic fact set requires exact authority.")
        if (
            self.dependency_order
            is not self.authority.relation_resolutions.dependency_order
        ):
            raise ValueError(
                "Semantic facts must reuse exact Slice 10 dependency order."
            )
        if self.issues is not self.authority.relation_resolutions.issues:
            raise ValueError("Semantic facts must retain exact Slice 10 issue roots.")
        if tuple(environment.module.identity for environment in self.environments) != (
            self.dependency_order
        ):
            raise ValueError("Semantic environments must follow dependency order.")
        expected_environments = self.authority.relation_resolutions.environments
        if len(self.environments) != len(expected_environments) or any(
            environment.resolution_environment is not expected
            for environment, expected in zip(
                self.environments,
                expected_environments,
                strict=True,
            )
        ):
            raise ValueError(
                "Semantic environments must retain exact Slice 10 environments."
            )
        environments_by_path: dict[str, ProjectModuleSemanticFactEnvironment] = {}
        facts_by_owner: dict[int, list[ProjectModuleRelationSemanticFacts]] = {}
        for environment in self.environments:
            if environment.module.path in environments_by_path:
                raise ValueError("Semantic environment paths must be unique.")
            environments_by_path[environment.module.path] = environment
            for fact in environment.relation_facts:
                facts_by_owner.setdefault(id(fact.owner), []).append(fact)
        relations = tuple(
            fact
            for environment in self.environments
            for fact in environment.relation_facts
        )
        authority = self.authority
        _require_tuple(
            authority._relation_fact_projections,
            ProjectModuleRelationSemanticFacts,
            "Semantic authority relation projections",
        )
        if (
            not authority._existing_fact_projections_bound
            or len(authority._relation_fact_projections) != len(relations)
            or len(authority._relation_pre_window_state_projections) != len(relations)
            or len(authority._relation_clause_dependency_projections) != len(relations)
        ):
            raise ValueError(
                "Semantic facts require complete exact private authority projections."
            )
        window_outputs = tuple(
            output for relation in relations for output in relation.window_outputs
        )
        if len(authority._window_analysis_projections) != len(window_outputs) or len(
            authority._window_diagnostic_projections
        ) != len(window_outputs):
            raise ValueError(
                "Window facts require complete exact analyzer authority projections."
            )
        for output, expected_analysis, expected_diagnostics in zip(
            window_outputs,
            authority._window_analysis_projections,
            authority._window_diagnostic_projections,
            strict=True,
        ):
            if output.analysis is not expected_analysis or (
                output.diagnostics is not expected_diagnostics
            ):
                raise ValueError(
                    "Window evidence must retain exact analyzer payload and diagnostics."
                )
        for fact, expected_fact, pre_window_state, expected_clause_dependencies in zip(
            relations,
            authority._relation_fact_projections,
            authority._relation_pre_window_state_projections,
            authority._relation_clause_dependency_projections,
            strict=True,
        ):
            if fact.clause_dependencies is not expected_clause_dependencies:
                raise ValueError(
                    "Clause dependencies must retain their exact existing-fact "
                    "projection."
                )
            upstream = (
                None
                if fact.resolution is None
                else _exact_relation_fact(
                    facts_by_owner,
                    fact.resolution.target_symbol.target_occurrence,
                )
            )
            _validate_relation_window_fact_set_closure(
                relation=fact,
                upstream=upstream,
                pre_window_state=pre_window_state,
            )
            if fact is not expected_fact:
                raise ValueError(
                    "Semantic relations must retain their exact existing relation "
                    "projection."
                )
        object.__setattr__(
            self,
            "_environments_by_path",
            MappingProxyType(environments_by_path),
        )
        object.__setattr__(
            self,
            "_facts_by_owner",
            MappingProxyType(
                {owner: tuple(items) for owner, items in facts_by_owner.items()}
            ),
        )

    def find_module_path(
        self,
        module_path: str,
    ) -> tuple[ProjectModuleSemanticFactEnvironment, ...]:
        """Return one exact environment or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        environment = self._environments_by_path.get(module_path)
        return () if environment is None else (environment,)

    def find_owner(
        self,
        owner: ProjectDeclarationOccurrence,
    ) -> tuple[ProjectModuleRelationSemanticFacts, ...]:
        """Return the complete exact relation-owner bucket."""

        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Semantic owner lookup requires an exact occurrence.")
        return tuple(
            fact
            for fact in self._facts_by_owner.get(id(owner), ())
            if fact.owner is owner
        )


def _capability_inventory() -> ProjectModuleCapabilityFactInventory:
    return ProjectModuleCapabilityFactInventory(
        inventory_facts=_CAPABILITY_FACTS,
        signature_facts=_CAPABILITY_SIGNATURE_FACTS,
        aggregate_facts=_AGGREGATE_CAPABILITY_FACTS,
        window_facts=_WINDOW_CAPABILITY_FACTS,
        context_facts=_CAPABILITY_CONTEXT_FACTS,
        window_signatures=_CANONICAL_WINDOW_SIGNATURE_FACTS,
        result_roles=tuple(ProjectRowResultRole),
    )


def _build_project_module_semantic_fact_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
) -> ProjectModuleSemanticFactSet:
    """Build the pure Slice 10-rooted preservation sidecar."""

    _validate_builder_inputs(modules, catalogs, relation_resolutions)
    capabilities = _capability_inventory()
    catalog_by_path = {catalog.module_path: catalog for catalog in catalogs.catalogs}
    resolution_by_path = {
        environment.module.path: environment
        for environment in relation_resolutions.environments
    }
    completed: list[ProjectModuleRelationSemanticFacts] = []
    environments: list[ProjectModuleSemanticFactEnvironment] = []
    relation_pre_window_projections: list[
        tuple[
            ProjectModuleRelationSemanticFacts,
            ProjectRelationRowSchemaState,
        ]
    ] = []

    for identity in relation_resolutions.dependency_order:
        catalog = catalog_by_path[identity.path]
        resolution_environment = resolution_by_path[identity.path]
        row_facts = tuple(resolution_environment.row_facts)
        pending = list(row_facts)
        built_for_module: list[ProjectModuleRelationSemanticFacts] = []
        while pending:
            progressed = False
            for base_row_fact in tuple(pending):
                owner = base_row_fact.owner
                definition = owner.definition
                if type(definition) is SourceDef:
                    semantic_fact = ProjectModuleRelationSemanticFacts(
                        owner=owner,
                        base_row_fact=base_row_fact,
                        resolution=None,
                        state=base_row_fact.state,
                        let_scope_facts=None,
                    )
                    pre_window_state = base_row_fact.state
                else:
                    if type(definition) not in {TableDef, QueryDef}:
                        raise ValueError("Slice 10 row fact has a non-relation owner.")
                    derived = cast(_DerivedRelation, definition)
                    resolutions = resolution_environment.find_from_clause(
                        derived.from_clause
                    )
                    resolution = resolutions[0] if len(resolutions) == 1 else None
                    upstream = (
                        None
                        if resolution is None
                        else _find_exact_owner(
                            completed,
                            resolution.target_symbol.target_occurrence,
                        )
                    )
                    if (
                        resolution is not None
                        and upstream is None
                        and base_row_fact.state.status
                        is ProjectRelationRowSchemaStatus.CONCRETE
                    ):
                        continue
                    if (
                        resolution is not None
                        and upstream is None
                        and _owner_is_pending(
                            pending,
                            resolution.target_symbol.target_occurrence,
                        )
                    ):
                        continue
                    semantic_fact, pre_window_state = _build_derived_relation_facts(
                        owner=owner,
                        base_row_fact=base_row_fact,
                        resolution=resolution,
                        upstream=upstream,
                        capabilities=capabilities,
                    )
                built_for_module.append(semantic_fact)
                completed.append(semantic_fact)
                relation_pre_window_projections.append(
                    (semantic_fact, pre_window_state)
                )
                pending.remove(base_row_fact)
                progressed = True
            if progressed:
                continue
            for base_row_fact in tuple(pending):
                definition = cast(_DerivedRelation, base_row_fact.owner.definition)
                resolutions = resolution_environment.find_from_clause(
                    definition.from_clause
                )
                resolution = resolutions[0] if len(resolutions) == 1 else None
                semantic_fact, pre_window_state = _build_derived_relation_facts(
                    owner=base_row_fact.owner,
                    base_row_fact=base_row_fact,
                    resolution=resolution,
                    upstream=None,
                    capabilities=capabilities,
                )
                built_for_module.append(semantic_fact)
                completed.append(semantic_fact)
                relation_pre_window_projections.append(
                    (semantic_fact, pre_window_state)
                )
                pending.remove(base_row_fact)

        catalog_relation_owners = tuple(
            occurrence
            for occurrence in catalog.occurrences
            if type(occurrence.definition) in {SourceDef, TableDef, QueryDef}
        )
        ordered = tuple(
            next(fact for fact in built_for_module if fact.owner is owner)
            for owner in catalog_relation_owners
            if any(fact.owner is owner for fact in built_for_module)
        )
        if tuple(fact.owner for fact in ordered) != tuple(
            fact.owner for fact in row_facts
        ):
            raise ValueError("Semantic facts must retain Slice 10 row-fact order.")
        environments.append(
            ProjectModuleSemanticFactEnvironment(
                module=resolution_environment.module,
                resolution_environment=resolution_environment,
                relation_facts=ordered,
            )
        )

    authority = _ProjectModuleSemanticFactAuthority(
        modules=modules,
        catalogs=catalogs,
        relation_resolutions=relation_resolutions,
    )
    semantic_environments = tuple(environments)
    semantic_relations = tuple(
        fact
        for environment in semantic_environments
        for fact in environment.relation_facts
    )
    if len(relation_pre_window_projections) != len(semantic_relations):
        raise ValueError(
            "Semantic authority requires every pre-window state projection."
        )
    pre_window_states: list[ProjectRelationRowSchemaState] = []
    for relation in semantic_relations:
        matches = tuple(
            state
            for candidate, state in relation_pre_window_projections
            if candidate is relation
        )
        if len(matches) != 1:
            raise ValueError(
                "Semantic authority requires one exact pre-window state projection."
            )
        pre_window_states.append(matches[0])
    window_outputs = tuple(
        output for relation in semantic_relations for output in relation.window_outputs
    )
    object.__setattr__(
        authority,
        "_relation_pre_window_state_projections",
        tuple(pre_window_states),
    )
    object.__setattr__(
        authority,
        "_relation_fact_projections",
        semantic_relations,
    )
    object.__setattr__(
        authority,
        "_relation_clause_dependency_projections",
        tuple(relation.clause_dependencies for relation in semantic_relations),
    )
    object.__setattr__(
        authority,
        "_window_analysis_projections",
        tuple(cast(_WindowAnalysis, output.analysis) for output in window_outputs),
    )
    object.__setattr__(
        authority,
        "_window_diagnostic_projections",
        tuple(output.diagnostics for output in window_outputs),
    )
    object.__setattr__(authority, "_existing_fact_projections_bound", True)
    return ProjectModuleSemanticFactSet(
        dependency_order=relation_resolutions.dependency_order,
        environments=semantic_environments,
        issues=relation_resolutions.issues,
        capabilities=capabilities,
        authority=authority,
    )


def _validate_builder_inputs(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    relation_resolutions: ProjectModuleRelationResolutionSet,
) -> None:
    _require_tuple(modules, ProjectLogicalModule, "Semantic builder modules")
    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Semantic builder requires exact catalogs.")
    if type(relation_resolutions) is not ProjectModuleRelationResolutionSet:
        raise TypeError("Semantic builder requires exact Slice 10 resolutions.")
    modules_by_path = {module.path: module for module in modules}
    if len(modules_by_path) != len(modules):
        raise ValueError("Semantic builder module paths must be unique.")
    if len(catalogs.catalogs) != len(modules) or any(
        catalog.module is not module
        for catalog, module in zip(catalogs.catalogs, modules, strict=True)
    ):
        raise ValueError("Semantic builder requires exact catalog module roots.")
    try:
        expected_modules = tuple(
            modules_by_path[identity.path]
            for identity in relation_resolutions.dependency_order
        )
    except KeyError as exc:
        raise ValueError(
            "Semantic builder dependency order requires exact module roots."
        ) from exc
    if len(relation_resolutions.environments) != len(expected_modules) or any(
        environment.module is not module
        for environment, module in zip(
            relation_resolutions.environments,
            expected_modules,
            strict=True,
        )
    ):
        raise ValueError("Semantic builder requires exact Slice 10 module roots.")
    environment_paths = {
        environment.module.path for environment in relation_resolutions.environments
    }
    cycle_blocked_paths = {
        issue.owning_module_path
        for issue in relation_resolutions.issues
        if issue.module_cycle is not None
    }
    if set(modules_by_path) != environment_paths | cycle_blocked_paths:
        raise ValueError("Semantic builder requires complete Slice 10 module coverage.")


def _find_exact_owner(
    facts: list[ProjectModuleRelationSemanticFacts],
    owner: ProjectDeclarationOccurrence,
) -> ProjectModuleRelationSemanticFacts | None:
    matches = tuple(fact for fact in facts if fact.owner is owner)
    if len(matches) > 1:
        raise ValueError("Exact relation owner cannot have multiple semantic facts.")
    return matches[0] if matches else None


def _owner_is_pending(
    pending: list[ProjectModuleRelationRowFact],
    owner: ProjectDeclarationOccurrence,
) -> bool:
    return any(fact.owner is owner for fact in pending)


def _build_derived_relation_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    base_row_fact: ProjectModuleRelationRowFact,
    resolution: ProjectResolvedModuleRelationReference | None,
    upstream: ProjectModuleRelationSemanticFacts | None,
    capabilities: ProjectModuleCapabilityFactInventory,
) -> tuple[
    ProjectModuleRelationSemanticFacts,
    ProjectRelationRowSchemaState,
]:
    definition = cast(_DerivedRelation, owner.definition)
    group_key_occurrences = (
        ()
        if definition.group_by_clause is None
        else tuple(definition.group_by_clause.items)
    )
    if resolution is None or upstream is None:
        state = base_row_fact.state
        let_scope = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=None,
            upstream_definition=(
                None
                if resolution is None
                else cast(
                    _RelationDefinition,
                    resolution.target_symbol.target_occurrence.definition,
                )
            ),
            upstream_state=state,
        )
        return (
            _nonconcrete_relation_facts(
                owner=owner,
                base_row_fact=base_row_fact,
                resolution=resolution,
                state=state,
                let_scope=let_scope,
                group_key_occurrences=group_key_occurrences,
                capabilities=capabilities,
            ),
            state,
        )

    if upstream.state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        state = _propagate_upstream_state(upstream.state)
        let_scope = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=upstream.state.schema,
            upstream_definition=cast(
                _RelationDefinition,
                resolution.target_symbol.target_occurrence.definition,
            ),
            upstream_state=upstream.state,
        )
        return (
            _nonconcrete_relation_facts(
                owner=owner,
                base_row_fact=base_row_fact,
                resolution=resolution,
                state=state,
                let_scope=let_scope,
                group_key_occurrences=group_key_occurrences,
                capabilities=capabilities,
            ),
            state,
        )

    input_schema = upstream.state.schema
    if input_schema is None or input_schema.is_unknown:
        raise ValueError("Concrete upstream semantic facts require a concrete schema.")
    upstream_definition = cast(
        _RelationDefinition,
        resolution.target_symbol.target_occurrence.definition,
    )
    upstream_symbol = _project_symbol_for_resolution(resolution)
    let_scope = build_project_relation_let_scope_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_definition=upstream_definition,
        upstream_state=upstream.state,
    )
    readiness: ProjectAggregateGroupedClauseReadiness | None = None
    aggregate_result_facts: tuple[ProjectAggregateResultFact, ...] = ()
    helper_diagnostics: tuple[Diagnostic, ...] = ()
    if _is_project_aggregate_grouped_definition(definition):
        readiness = build_project_aggregate_grouped_clause_readiness(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=owner.identity.module_path,
            let_scope_facts=let_scope,
        )
        base_state = _relation_state_from_aggregate_grouped_clause_readiness(readiness)
        aggregate_result_facts = tuple(
            fact
            for item in definition.select_items
            if type(item.expression) is not WindowExpr
            if (output_name := _projection_output_name(item)) is not None
            and (fact := readiness.finalization.aggregate_result_facts.get(output_name))
            is not None
        )
    else:
        schema_result = _project_direct_relation_row_schema(
            definition,
            source_schema=input_schema,
            source_symbol=upstream_symbol,
            upstream_definition=upstream_definition,
            upstream_state=upstream.state,
            fallback_path=owner.identity.module_path,
            let_scope_facts=let_scope,
        )
        helper_diagnostics = schema_result.diagnostics
        base_state = _project_relation_row_schema_state_from_result(
            schema_result,
            concrete_reason=(
                ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
                if type(upstream_definition) is SourceDef
                else ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
            ),
        )

    let_bindings = _let_binding_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        input_status=ProjectModuleCandidateBucketStatus.CONCRETE,
        let_scope=let_scope,
    )
    window_state, window_outputs = _window_output_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope=let_scope,
        base_state=base_state,
        capabilities=capabilities,
    )
    clause_dependencies = _clause_dependency_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        group_input_status=ProjectModuleCandidateBucketStatus.CONCRETE,
        state=base_state,
        grouped_order_state=window_state,
        let_scope=let_scope,
        aggregate_result_facts=aggregate_result_facts,
    )
    state = _apply_clause_ambiguity_to_window_state(
        window_state,
        clause_dependencies,
    )
    window_outputs = _suppress_window_project_facts_after_clause_ambiguity(
        state=state,
        clause_dependencies=clause_dependencies,
        window_outputs=window_outputs,
    )
    published_aggregate_result_facts = (
        aggregate_result_facts
        if state.status is ProjectRelationRowSchemaStatus.CONCRETE
        else ()
    )
    select_facts = _select_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        input_status=ProjectModuleCandidateBucketStatus.CONCRETE,
        state=state,
        let_scope=let_scope,
        aggregate_result_facts=published_aggregate_result_facts,
    )
    return (
        ProjectModuleRelationSemanticFacts(
            owner=owner,
            base_row_fact=base_row_fact,
            resolution=resolution,
            state=state,
            let_scope_facts=let_scope,
            let_bindings=let_bindings,
            select_facts=select_facts,
            group_key_occurrences=group_key_occurrences,
            aggregate_grouped_clause_readiness=readiness,
            clause_dependencies=clause_dependencies,
            aggregate_result_facts=published_aggregate_result_facts,
            window_outputs=window_outputs,
            helper_diagnostics=helper_diagnostics,
        ),
        base_state,
    )


def _nonconcrete_relation_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    base_row_fact: ProjectModuleRelationRowFact,
    resolution: ProjectResolvedModuleRelationReference | None,
    state: ProjectRelationRowSchemaState,
    let_scope: ProjectRelationLetScopeFacts,
    group_key_occurrences: tuple[GroupByItem, ...],
    capabilities: ProjectModuleCapabilityFactInventory,
) -> ProjectModuleRelationSemanticFacts:
    definition = cast(_DerivedRelation, owner.definition)
    input_status = _candidate_status_from_row_state(state)
    let_bindings = _let_binding_facts(
        owner=owner,
        definition=definition,
        input_schema=None,
        input_status=input_status,
        let_scope=let_scope,
    )
    select_facts = _select_facts(
        owner=owner,
        definition=definition,
        input_schema=None,
        input_status=input_status,
        state=state,
        let_scope=let_scope,
        aggregate_result_facts=(),
    )
    window_outputs = _unavailable_window_outputs(
        owner=owner,
        definition=definition,
        input_schema=None,
        state=state,
        let_scope=let_scope,
        capabilities=capabilities,
    )
    return ProjectModuleRelationSemanticFacts(
        owner=owner,
        base_row_fact=base_row_fact,
        resolution=resolution,
        state=state,
        let_scope_facts=let_scope,
        let_bindings=let_bindings,
        select_facts=select_facts,
        group_key_occurrences=group_key_occurrences,
        clause_dependencies=_clause_dependency_facts(
            owner=owner,
            definition=definition,
            input_schema=None,
            group_input_status=input_status,
            state=state,
            let_scope=let_scope,
            aggregate_result_facts=(),
        ),
        window_outputs=window_outputs,
    )


def _propagate_upstream_state(
    upstream_state: ProjectRelationRowSchemaState,
) -> ProjectRelationRowSchemaState:
    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=ProjectRowSchema(is_unknown=True),
            reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.BLOCKED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        )
    raise ValueError("Concrete upstream cannot use non-concrete propagation.")


def _project_symbol_for_resolution(
    resolution: ProjectResolvedModuleRelationReference,
) -> ProjectSymbol:
    target = resolution.target_symbol.target_occurrence
    identity = target.identity
    span = target.definition.span
    return ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=identity.declaration_kind,
        name=identity.declared_name,
        path=identity.module_path,
        location=SourceLocation(
            path=span.path or identity.module_path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
        definition=target.definition,
    )


def _let_binding_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    input_status: ProjectModuleCandidateBucketStatus,
    let_scope: ProjectRelationLetScopeFacts,
) -> tuple[ProjectModuleLetBindingFact, ...]:
    if definition.let_clause is None:
        return ()
    bindings = tuple(definition.let_clause.bindings)
    return tuple(
        ProjectModuleLetBindingFact(
            owner=owner,
            binding_ordinal=ordinal,
            binding=binding,
            scope_facts=let_scope,
            value_type=(
                let_scope.value_types.get(binding.name)
                if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
                else None
            ),
            references=_expression_reference_facts(
                owner=owner,
                role=ProjectModuleFactOccurrenceRole.LET_VALUE,
                container_ordinal=ordinal,
                expression=binding.expression,
                relation_qualifier=definition.from_clause.source_name,
                input_schema=input_schema,
                input_status=input_status,
                let_scope=let_scope,
                let_candidates=bindings[:ordinal],
                selected_items=(),
            ),
        )
        for ordinal, binding in enumerate(bindings)
    )


def _select_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    input_status: ProjectModuleCandidateBucketStatus,
    state: ProjectRelationRowSchemaState,
    let_scope: ProjectRelationLetScopeFacts,
    aggregate_result_facts: tuple[ProjectAggregateResultFact, ...],
) -> tuple[ProjectModuleSelectFact, ...]:
    let_values = (
        let_scope.value_types
        if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
    )
    expression_types: Mapping[Expression, ValueType] = MappingProxyType({})
    if input_schema is not None and not input_schema.is_unknown:
        expression_types = build_project_row_expression_value_types(
            expressions=(
                item.expression
                for item in definition.select_items
                if type(item.expression) is not WindowExpr
            ),
            input_schema=input_schema,
            relation_qualifier=definition.from_clause.source_name,
            bare_value_types=let_values,
        )
    aggregate_by_name = {fact.output_name: fact for fact in aggregate_result_facts}
    schema = (
        state.schema
        if state.status is ProjectRelationRowSchemaStatus.CONCRETE
        else None
    )
    bindings = (
        () if definition.let_clause is None else tuple(definition.let_clause.bindings)
    )
    facts: list[ProjectModuleSelectFact] = []
    for ordinal, item in enumerate(definition.select_items):
        output_name = _projection_output_name(item)
        expression_schema = None
        if output_name is not None and type(item.expression) is not WindowExpr:
            expression_schema = adapt_project_row_expression_schema(
                expression=item.expression,
                output_name=output_name,
                input_schema=input_schema,
                upstream_state=(state if input_schema is None else None),
                relation_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_types,
                let_value_types=let_values,
                fallback_path=owner.identity.module_path,
            )
        facts.append(
            ProjectModuleSelectFact(
                owner=owner,
                selected_output_ordinal=ordinal,
                item=item,
                output_name=output_name,
                expression_schema=expression_schema,
                field=(
                    None
                    if schema is None or output_name is None
                    else schema.fields.get(output_name)
                ),
                aggregate_result_fact=(
                    None if output_name is None else aggregate_by_name.get(output_name)
                ),
                references=(
                    ()
                    if type(item.expression) is WindowExpr
                    else _expression_reference_facts(
                        owner=owner,
                        role=ProjectModuleFactOccurrenceRole.SELECT_VALUE,
                        container_ordinal=ordinal,
                        expression=item.expression,
                        relation_qualifier=definition.from_clause.source_name,
                        input_schema=input_schema,
                        input_status=input_status,
                        let_scope=let_scope,
                        let_candidates=bindings,
                        selected_items=(),
                    )
                ),
            )
        )
    return tuple(facts)


def _expression_reference_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    role: ProjectModuleFactOccurrenceRole,
    container_ordinal: int,
    expression: Expression,
    relation_qualifier: str,
    input_schema: ProjectRowSchema | None,
    input_status: ProjectModuleCandidateBucketStatus,
    let_scope: ProjectRelationLetScopeFacts,
    let_candidates: tuple[LetBinding, ...],
    selected_items: tuple[SelectItem, ...],
) -> tuple[ProjectModuleExpressionReferenceFact, ...]:
    facts: list[ProjectModuleExpressionReferenceFact] = []
    for dependency_ordinal, leaf in enumerate(_direct_name_leaves(expression)):
        local_name, qualifier_valid = _local_reference_name(
            leaf,
            relation_qualifier=relation_qualifier,
        )
        input_field = (
            None
            if input_schema is None or not qualifier_valid
            else input_schema.fields.get(local_name)
        )
        matching_lets = (
            tuple(binding for binding in let_candidates if binding.name == local_name)
            if type(leaf) is NameExpr
            else ()
        )
        matching_outputs = (
            tuple(
                item
                for item in selected_items
                if _projection_output_name(item) == local_name
            )
            if type(leaf) is NameExpr
            else ()
        )
        candidate_count = (
            (1 if input_field is not None else 0)
            + len(matching_lets)
            + len(matching_outputs)
        )
        if input_status is not ProjectModuleCandidateBucketStatus.CONCRETE:
            # An unavailable input bounds every dependent reference before local
            # qualifier or candidate analysis.  In particular, a wrong qualifier
            # must not erase an established UNKNOWN, DEFERRED, or BLOCKED family.
            status = input_status
        elif not qualifier_valid:
            status = ProjectModuleCandidateBucketStatus.UNKNOWN
        elif input_field is not None:
            # Existing row/let semantics give a concrete input field priority over
            # an invalid shadowing let while the raw let occurrences remain visible.
            status = ProjectModuleCandidateBucketStatus.CONCRETE
        elif (
            matching_lets
            and (let_status := _candidate_status_from_let_scope(let_scope))
            is not ProjectModuleCandidateBucketStatus.CONCRETE
        ):
            status = let_status
        elif candidate_count == 0:
            status = ProjectModuleCandidateBucketStatus.ABSENT
        elif candidate_count > 1:
            status = ProjectModuleCandidateBucketStatus.AMBIGUOUS
        elif matching_lets:
            status = _candidate_status_from_let_scope(let_scope)
        elif matching_outputs:
            status = input_status
        else:
            raise AssertionError("One reference candidate must retain its family.")
        facts.append(
            ProjectModuleExpressionReferenceFact(
                owner=owner,
                role=role,
                container_ordinal=container_ordinal,
                dependency_ordinal=dependency_ordinal,
                expression=leaf,
                local_name=local_name,
                input_field=input_field,
                let_candidates=matching_lets,
                selected_output_candidates=matching_outputs,
                status=status,
            )
        )
    return tuple(facts)


def _direct_name_leaves(
    expression: Expression,
) -> tuple[NameExpr | DottedNameExpr, ...]:
    if type(expression) in {NameExpr, DottedNameExpr}:
        return (cast(NameExpr | DottedNameExpr, expression),)
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
    elif isinstance(expression, WindowExpr):
        children = (
            *expression.call.arguments,
            *expression.spec.partition_by,
            *(item.expression for item in expression.spec.order_by),
        )
    else:
        children = ()
    return tuple(leaf for child in children for leaf in _direct_name_leaves(child))


def _local_reference_name(
    expression: NameExpr | DottedNameExpr,
    *,
    relation_qualifier: str,
) -> tuple[str, bool]:
    if type(expression) is NameExpr:
        return cast(NameExpr, expression).name, True
    dotted = cast(DottedNameExpr, expression)
    if len(dotted.parts) == 2 and dotted.parts[0] == relation_qualifier:
        return dotted.parts[1], True
    return ".".join(dotted.parts), False


def _candidate_target_facts(
    candidates: tuple[SelectItem, ...],
    *,
    schema: ProjectRowSchema | None,
    aggregate_by_name: Mapping[str, ProjectAggregateResultFact],
    include_window_candidates: bool,
) -> tuple[tuple[ProjectRowField, ...], tuple[ProjectAggregateResultFact, ...]]:
    target_fields: list[ProjectRowField] = []
    aggregate_facts: list[ProjectAggregateResultFact] = []
    for candidate in candidates:
        is_window = type(candidate.expression) is WindowExpr
        if is_window and not include_window_candidates:
            continue
        name = _projection_output_name(candidate)
        if name is None:
            continue
        if schema is not None and (field := schema.fields.get(name)) is not None:
            target_fields.append(field)
        if not is_window and (fact := aggregate_by_name.get(name)) is not None:
            aggregate_facts.append(fact)
    return tuple(target_fields), tuple(aggregate_facts)


def _candidate_status_from_row_state(
    state: ProjectRelationRowSchemaState,
) -> ProjectModuleCandidateBucketStatus:
    return {
        ProjectRelationRowSchemaStatus.CONCRETE: (
            ProjectModuleCandidateBucketStatus.CONCRETE
        ),
        ProjectRelationRowSchemaStatus.UNKNOWN: ProjectModuleCandidateBucketStatus.UNKNOWN,
        ProjectRelationRowSchemaStatus.DEFERRED: (
            ProjectModuleCandidateBucketStatus.DEFERRED
        ),
        ProjectRelationRowSchemaStatus.BLOCKED: ProjectModuleCandidateBucketStatus.BLOCKED,
    }[state.status]


def _candidate_status_from_let_scope(
    let_scope: ProjectRelationLetScopeFacts,
) -> ProjectModuleCandidateBucketStatus:
    return {
        ProjectLetScopeFactsStatus.CONCRETE: (
            ProjectModuleCandidateBucketStatus.CONCRETE
        ),
        ProjectLetScopeFactsStatus.UNKNOWN: ProjectModuleCandidateBucketStatus.UNKNOWN,
        ProjectLetScopeFactsStatus.DEFERRED: (
            ProjectModuleCandidateBucketStatus.DEFERRED
        ),
        ProjectLetScopeFactsStatus.BLOCKED: ProjectModuleCandidateBucketStatus.BLOCKED,
        ProjectLetScopeFactsStatus.ABSENT: ProjectModuleCandidateBucketStatus.ABSENT,
    }[let_scope.status]


def _clause_bucket_status(
    *,
    candidates: tuple[SelectItem, ...],
    target_fields: tuple[ProjectRowField, ...],
    state: ProjectRelationRowSchemaState,
    unavailable_let_status: ProjectModuleCandidateBucketStatus | None = None,
) -> ProjectModuleCandidateBucketStatus:
    inherited = _candidate_status_from_row_state(state)
    if inherited is not ProjectModuleCandidateBucketStatus.CONCRETE:
        return inherited
    if unavailable_let_status is not None:
        return unavailable_let_status
    if not candidates:
        return ProjectModuleCandidateBucketStatus.ABSENT
    if len(candidates) != len(target_fields):
        return ProjectModuleCandidateBucketStatus.UNKNOWN
    if len(candidates) > 1:
        return ProjectModuleCandidateBucketStatus.AMBIGUOUS
    if len(target_fields) == 1:
        return ProjectModuleCandidateBucketStatus.CONCRETE
    return ProjectModuleCandidateBucketStatus.UNKNOWN


def _clause_dependency_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    group_input_status: ProjectModuleCandidateBucketStatus,
    state: ProjectRelationRowSchemaState,
    grouped_order_state: ProjectRelationRowSchemaState | None = None,
    let_scope: ProjectRelationLetScopeFacts,
    aggregate_result_facts: tuple[ProjectAggregateResultFact, ...],
) -> tuple[ProjectModuleClauseDependencyFact, ...]:
    facts: list[ProjectModuleClauseDependencyFact] = []
    schema = (
        state.schema
        if state.status is ProjectRelationRowSchemaStatus.CONCRETE
        else None
    )
    aggregate_by_name = {fact.output_name: fact for fact in aggregate_result_facts}
    final_order_state = state if grouped_order_state is None else grouped_order_state
    final_order_schema = (
        final_order_state.schema
        if final_order_state.status is ProjectRelationRowSchemaStatus.CONCRETE
        else None
    )
    group_items = (
        ()
        if definition.group_by_clause is None
        else tuple(definition.group_by_clause.items)
    )
    for ordinal, item in enumerate(group_items):
        if type(group_input_status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Group input requires an exact candidate status.")
        local_name, valid = _local_reference_name(
            item.key,
            relation_qualifier=definition.from_clause.source_name,
        )
        input_field: ProjectRowField | None = None
        unavailable_let_status: ProjectModuleCandidateBucketStatus | None = None
        non_direct_let = False
        if (
            group_input_status is ProjectModuleCandidateBucketStatus.CONCRETE
            and type(item.key) is NameExpr
        ):
            matching_lets = tuple(
                binding
                for binding in let_scope.bindings
                if binding.name == item.key.name
            )
            if matching_lets:
                if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE:
                    if _group_key_let_expands_to_direct_name(
                        item.key,
                        let_expressions=let_scope.binding_expressions,
                        seen=frozenset(),
                    ):
                        effective = _effective_group_key_expression(
                            item.key,
                            let_expressions=let_scope.binding_expressions,
                            let_stack=frozenset(),
                        )
                        local_name, valid = _local_reference_name(
                            effective,
                            relation_qualifier=definition.from_clause.source_name,
                        )
                    else:
                        non_direct_let = True
                else:
                    unavailable_let_status = _candidate_status_from_let_scope(let_scope)
        group_status = group_input_status
        if group_input_status is not ProjectModuleCandidateBucketStatus.CONCRETE:
            pass
        elif unavailable_let_status is not None:
            group_status = unavailable_let_status
        elif non_direct_let or not valid:
            group_status = ProjectModuleCandidateBucketStatus.UNKNOWN
        else:
            candidate = (
                None if input_schema is None else input_schema.fields.get(local_name)
            )
            if candidate is None:
                group_status = ProjectModuleCandidateBucketStatus.ABSENT
            elif (
                candidate.name != local_name
                or candidate.resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
            ):
                group_status = ProjectModuleCandidateBucketStatus.UNKNOWN
            else:
                input_field = candidate
                group_status = ProjectModuleCandidateBucketStatus.CONCRETE
        facts.append(
            ProjectModuleClauseDependencyFact(
                owner=owner,
                role=ProjectModuleFactOccurrenceRole.GROUP_KEY,
                source_ordinal=ordinal,
                source_occurrence=item,
                target_occurrences=((item,) if input_field is not None else ()),
                target_fields=((input_field,) if input_field is not None else ()),
                status=group_status,
            )
        )

    if definition.satisfying_clause is not None:
        occurrences = _satisfying_occurrences(definition.satisfying_clause.expression)
        for ordinal, occurrence in enumerate(occurrences):
            candidates, unavailable_let_status = _satisfying_candidates(
                occurrence,
                definition=definition,
                let_scope=let_scope,
            )
            target_fields, aggregate_facts = _candidate_target_facts(
                candidates,
                schema=schema,
                aggregate_by_name=aggregate_by_name,
                include_window_candidates=False,
            )
            facts.append(
                ProjectModuleClauseDependencyFact(
                    owner=owner,
                    role=ProjectModuleFactOccurrenceRole.SATISFYING,
                    source_ordinal=ordinal,
                    source_occurrence=occurrence,
                    target_occurrences=candidates,
                    target_fields=target_fields,
                    aggregate_result_facts=aggregate_facts,
                    status=_clause_bucket_status(
                        candidates=candidates,
                        target_fields=target_fields,
                        state=state,
                        unavailable_let_status=unavailable_let_status,
                    ),
                )
            )

    if (
        definition.group_by_clause is not None
        and definition.order_by_clause is not None
    ):
        for ordinal, item in enumerate(definition.order_by_clause.items):
            candidates: tuple[SelectItem, ...] = ()
            unavailable_let_status: ProjectModuleCandidateBucketStatus | None = None
            if type(item.expression) is NameExpr:
                candidates = tuple(
                    selected
                    for selected in definition.select_items
                    if _projection_output_name(selected) == item.expression.name
                )
                matching_lets = tuple(
                    binding
                    for binding in let_scope.bindings
                    if binding.name == item.expression.name
                )
                if not candidates and matching_lets:
                    if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE:
                        effective = _effective_field_let_expression(
                            item.expression,
                            let_expressions=let_scope.binding_expressions,
                            seen=frozenset(),
                        )
                        if effective is not None:
                            local_name = _direct_field_identity(
                                effective,
                                relation_qualifier=definition.from_clause.source_name,
                            )
                        else:
                            local_name = None
                        if local_name is not None:
                            candidates = tuple(
                                selected
                                for selected in definition.select_items
                                if _direct_field_identity(
                                    selected.expression,
                                    relation_qualifier=(
                                        definition.from_clause.source_name
                                    ),
                                )
                                == local_name
                            )
                    else:
                        unavailable_let_status = _candidate_status_from_let_scope(
                            let_scope
                        )
            target_fields, aggregate_facts = _candidate_target_facts(
                candidates,
                schema=final_order_schema,
                aggregate_by_name=aggregate_by_name,
                include_window_candidates=True,
            )
            facts.append(
                ProjectModuleClauseDependencyFact(
                    owner=owner,
                    role=ProjectModuleFactOccurrenceRole.GROUPED_ORDER,
                    source_ordinal=ordinal,
                    source_occurrence=item,
                    target_occurrences=candidates,
                    target_fields=target_fields,
                    aggregate_result_facts=aggregate_facts,
                    status=_clause_bucket_status(
                        candidates=candidates,
                        target_fields=target_fields,
                        state=final_order_state,
                        unavailable_let_status=unavailable_let_status,
                    ),
                )
            )
    return tuple(facts)


def _group_key_let_expands_to_direct_name(
    expression: NameExpr | DottedNameExpr,
    *,
    let_expressions: Mapping[str, Expression],
    seen: frozenset[str],
) -> bool:
    """Return whether one concrete let chain ends at a direct input name."""

    if type(expression) is DottedNameExpr:
        return True
    name = cast(NameExpr, expression).name
    if name in seen:
        return False
    expanded = let_expressions.get(name)
    if expanded is None:
        return True
    if type(expanded) not in {NameExpr, DottedNameExpr}:
        return False
    return _group_key_let_expands_to_direct_name(
        cast(NameExpr | DottedNameExpr, expanded),
        let_expressions=let_expressions,
        seen=seen | frozenset((name,)),
    )


def _satisfying_occurrences(
    expression: Expression,
) -> tuple[NameExpr | CallExpr, ...]:
    if type(expression) is NameExpr:
        return (cast(NameExpr, expression),)
    if isinstance(expression, LiteralExpr):
        return ()
    if isinstance(expression, CallExpr):
        return (expression,)
    if isinstance(expression, ComparisonExpr):
        return (
            *_satisfying_occurrences(expression.left),
            *_satisfying_occurrences(expression.right),
        )
    if isinstance(expression, BinaryExpr) and expression.operator in {"and", "or"}:
        return (
            *_satisfying_occurrences(expression.left),
            *_satisfying_occurrences(expression.right),
        )
    return ()


def _satisfying_candidates(
    occurrence: NameExpr | CallExpr,
    *,
    definition: _DerivedRelation,
    let_scope: ProjectRelationLetScopeFacts,
) -> tuple[
    tuple[SelectItem, ...],
    ProjectModuleCandidateBucketStatus | None,
]:
    if type(occurrence) is NameExpr:
        name = cast(NameExpr, occurrence).name
        return (
            tuple(
                item
                for item in definition.select_items
                if _projection_output_name(item) == name
            ),
            None,
        )
    call = cast(CallExpr, occurrence)
    function_name = semantic_aggregate_call_name(call)
    if function_name is None or len(call.arguments) != 1:
        return (), None
    argument = call.arguments[0]
    if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE:
        let_expressions = let_scope.binding_expressions
    elif let_scope.status is ProjectLetScopeFactsStatus.ABSENT:
        let_expressions = MappingProxyType({})
    else:
        binding_names = tuple(binding.name for binding in let_scope.bindings)
        if any(
            type(leaf) is NameExpr and cast(NameExpr, leaf).name in binding_names
            for leaf in _direct_name_leaves(argument)
        ):
            return (), _candidate_status_from_let_scope(let_scope)
        let_expressions = MappingProxyType({})
    if not aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        let_expressions,
    ):
        return (), None
    effective = effective_semantic_aggregate_argument_expression(
        function_name,
        argument,
        let_expansions=let_expressions,
    )
    candidates: list[SelectItem] = []
    for item in definition.select_items:
        selected = item.expression
        if not isinstance(selected, CallExpr):
            continue
        if semantic_aggregate_call_name(selected) != function_name:
            continue
        if len(selected.arguments) != 1:
            continue
        selected_effective = effective_semantic_aggregate_argument_expression(
            function_name,
            selected.arguments[0],
            let_expansions=let_expressions,
        )
        if selected_effective == effective:
            candidates.append(item)
    return tuple(candidates), None


def _window_output_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    let_scope: ProjectRelationLetScopeFacts,
    base_state: ProjectRelationRowSchemaState,
    capabilities: ProjectModuleCapabilityFactInventory,
) -> tuple[
    ProjectRelationRowSchemaState,
    tuple[ProjectModuleWindowOutputFact, ...],
]:
    window_items = tuple(
        (ordinal, item)
        for ordinal, item in enumerate(definition.select_items)
        if type(item.expression) is WindowExpr
    )
    if not window_items:
        return base_state, ()
    if base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
        return (
            base_state,
            _unavailable_window_outputs(
                owner=owner,
                definition=definition,
                input_schema=input_schema,
                state=base_state,
                let_scope=let_scope,
                capabilities=capabilities,
            ),
        )
    base_schema = base_state.schema
    if base_schema is None or base_schema.is_unknown:
        raise ValueError("Concrete window base state requires a concrete schema.")

    if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE:
        let_values: Mapping[str, ValueType] | None = let_scope.value_types
        let_expressions: Mapping[str, Expression] | None = let_scope.binding_expressions
    elif let_scope.status is ProjectLetScopeFactsStatus.ABSENT:
        let_values = MappingProxyType({})
        let_expressions = MappingProxyType({})
    else:
        let_values = None
        let_expressions = None
    semantic_input = project_row_schema_to_semantic_row_schema(input_schema)
    outputs: list[ProjectModuleWindowOutputFact] = []
    for ordinal, item in window_items:
        expression = cast(WindowExpr, item.expression)
        source_id = expression.span.path or owner.identity.module_path
        diagnostics: list[Diagnostic] = []
        value_types: dict[Expression, ValueType] = {}
        analysis = analyze_window_expression(
            definition=definition,
            item=item,
            selected_output_ordinal=ordinal,
            source_id=source_id,
            input_schema=semantic_input,
            field_qualifier=definition.from_clause.source_name,
            value_types=value_types,
            diagnostics=diagnostics,
            let_value_types=let_values,
            let_expressions=let_expressions,
        )
        analysis = _project_window_analysis_boundary(item, analysis)
        signature = _find_window_signature(capabilities, expression.identity)
        project_fact: WindowResultProjectFact | None = None
        if isinstance(analysis, WindowExpressionUnsupported):
            status = ProjectModuleCandidateBucketStatus.UNKNOWN
            reason = analysis.reason
        else:
            input_scope = build_window_input_scope(
                definition=definition,
                input_schema=semantic_input,
                field_qualifier=definition.from_clause.source_name,
                value_types=value_types,
                let_value_types=let_values or {},
                let_expressions=let_expressions or {},
            )
            project_result = _build_window_result_project_fact(
                semantic_fact=analysis.semantic_fact,
                definition=definition,
                item=item,
                upstream_symbol=upstream_symbol,
                input_scope=input_scope,
            )
            if type(project_result) is not WindowResultProjectFact:
                raise AssertionError("eligible inline window project fact was deferred")
            project_fact = project_result
            availability = analysis.semantic_fact.result
            status = {
                WindowResultAvailabilityKind.CONCRETE: (
                    ProjectModuleCandidateBucketStatus.CONCRETE
                ),
                WindowResultAvailabilityKind.UNKNOWN: (
                    ProjectModuleCandidateBucketStatus.UNKNOWN
                ),
                WindowResultAvailabilityKind.DEFERRED: (
                    ProjectModuleCandidateBucketStatus.DEFERRED
                ),
                WindowResultAvailabilityKind.BLOCKED: (
                    ProjectModuleCandidateBucketStatus.BLOCKED
                ),
            }[availability.kind]
            reason = availability.reason
            if status is ProjectModuleCandidateBucketStatus.CONCRETE and not (
                _window_fact_matches_source(
                    fact=project_fact,
                    definition=definition,
                    item=item,
                    selected_output_ordinal=ordinal,
                    source_id=source_id,
                    input_schema=input_schema,
                    base_schema=base_schema,
                    upstream_symbol=upstream_symbol,
                    let_scope_facts=let_scope,
                )
            ):
                status = ProjectModuleCandidateBucketStatus.BLOCKED
                reason = (
                    ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS.value
                )
        output_name = item.alias
        outputs.append(
            ProjectModuleWindowOutputFact(
                owner=owner,
                selected_output_ordinal=ordinal,
                item=item,
                output_name=output_name,
                signature_fact=signature,
                analysis=analysis,
                project_fact=project_fact,
                retained_project_fact=project_fact,
                diagnostics=tuple(diagnostics),
                status=status,
                reason=reason,
            )
        )

    result = tuple(outputs)
    return (
        _reduce_window_outputs_to_state(
            definition=definition,
            base_state=base_state,
            outputs=result,
        ),
        result,
    )


def _unavailable_window_outputs(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    state: ProjectRelationRowSchemaState,
    let_scope: ProjectRelationLetScopeFacts,
    capabilities: ProjectModuleCapabilityFactInventory,
) -> tuple[ProjectModuleWindowOutputFact, ...]:
    status = {
        ProjectRelationRowSchemaStatus.CONCRETE: (
            ProjectModuleCandidateBucketStatus.CONCRETE
        ),
        ProjectRelationRowSchemaStatus.UNKNOWN: (
            ProjectModuleCandidateBucketStatus.UNKNOWN
        ),
        ProjectRelationRowSchemaStatus.DEFERRED: (
            ProjectModuleCandidateBucketStatus.DEFERRED
        ),
        ProjectRelationRowSchemaStatus.BLOCKED: (
            ProjectModuleCandidateBucketStatus.BLOCKED
        ),
    }[state.status]
    semantic_input = (
        SemanticRowSchema(is_unknown=True)
        if input_schema is None
        else project_row_schema_to_semantic_row_schema(input_schema)
    )
    if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE:
        let_values: Mapping[str, ValueType] | None = let_scope.value_types
        let_expressions: Mapping[str, Expression] | None = let_scope.binding_expressions
    elif let_scope.status is ProjectLetScopeFactsStatus.ABSENT:
        let_values = MappingProxyType({})
        let_expressions = MappingProxyType({})
    else:
        let_values = None
        let_expressions = None
    outputs: list[ProjectModuleWindowOutputFact] = []
    for ordinal, item in enumerate(definition.select_items):
        if type(item.expression) is not WindowExpr:
            continue
        diagnostics: list[Diagnostic] = []
        analysis = analyze_window_expression(
            definition=definition,
            item=item,
            selected_output_ordinal=ordinal,
            source_id=item.expression.span.path or owner.identity.module_path,
            input_schema=semantic_input,
            field_qualifier=definition.from_clause.source_name,
            value_types={},
            diagnostics=diagnostics,
            let_value_types=let_values,
            let_expressions=let_expressions,
        )
        analysis = _project_window_analysis_boundary(item, analysis)
        outputs.append(
            ProjectModuleWindowOutputFact(
                owner=owner,
                selected_output_ordinal=ordinal,
                item=item,
                output_name=item.alias,
                signature_fact=_find_window_signature(
                    capabilities,
                    item.expression.identity,
                ),
                analysis=analysis,
                project_fact=None,
                retained_project_fact=None,
                diagnostics=tuple(diagnostics),
                status=status,
                reason=state.reason.value,
            )
        )
    return tuple(outputs)


def _find_window_signature(
    capabilities: ProjectModuleCapabilityFactInventory,
    identity: WindowFunctionIdentity,
) -> ProjectModuleWindowSignatureFact | None:
    if capabilities.window_signatures is not _CANONICAL_WINDOW_SIGNATURE_FACTS:
        raise ValueError("Window signature lookup requires the canonical inventory.")
    return _canonical_window_signature(identity)


def _unknown_window_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=ProjectRowSchema(is_unknown=True),
        reason=reason,
    )


def _blocked_window_state() -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.CONFLICTING_WINDOW_RESULT_FACTS,
    )


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if type(item.expression) is NameExpr:
        return item.expression.name
    if type(item.expression) is DottedNameExpr:
        return item.expression.parts[-1]
    return None


def _direct_field_identity(
    expression: Expression,
    *,
    relation_qualifier: str,
) -> str | None:
    if type(expression) is NameExpr:
        return expression.name
    if (
        type(expression) is DottedNameExpr
        and len(expression.parts) == 2
        and expression.parts[0] == relation_qualifier
    ):
        return expression.parts[1]
    return None
