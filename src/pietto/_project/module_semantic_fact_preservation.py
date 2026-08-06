"""Private schema-v2 preservation of existing semantic and project facts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_persistence import (
    _is_project_aggregate_grouped_definition,
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
from pietto._project.window_persistence import (
    _final_schema as _final_window_schema,
    _window_fact_matches_source,
)
from pietto._project.window_semantics import (
    WindowResultProjectFact,
    _build_window_result_project_fact,
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
    TableDef,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    effective_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
)
from pietto.semantic.capability_aggregates import (
    _AGGREGATE_CAPABILITY_FACTS,
    aggregate_lookup_inputs,
)
from pietto.semantic.capability_contexts import (
    _CAPABILITY_CONTEXT_FACTS,
    stage_clause_lookup_inputs,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
)
from pietto.semantic.capability_inventory import (
    _CAPABILITY_FACTS,
    inventory_lookup_inputs,
)
from pietto.semantic.capability_lookup import (
    CapabilityLookupResult,
    lookup_capability,
)
from pietto.semantic.capability_signatures import (
    _CAPABILITY_SIGNATURE_FACTS,
    signature_lookup_inputs,
)
from pietto.semantic.capability_windows import (
    _WINDOW_CAPABILITY_FACTS,
    window_lookup_inputs,
)
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
    _NAVIGATION_IDENTITIES,
    _NAVIGATION_SIGNATURE,
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
        ):
            raise ValueError(
                "Window signature inventory must retain all eight identities."
            )
        if self.result_roles != tuple(ProjectRowResultRole):
            raise ValueError("Result-role inventory must retain exact enum order.")

    def lookup(self, key: CapabilityKey) -> CapabilityLookupResult:
        """Dispatch one exact key through its established provider contract."""

        if type(key) is not CapabilityKey:
            raise TypeError("Capability inventory lookup requires an exact key.")
        if key.domain in {
            CapabilityDomain.LOGICAL_TYPE,
            CapabilityDomain.LITERAL,
            CapabilityDomain.PARAMETER,
        }:
            _provider_facts, complete = inventory_lookup_inputs(key)
            return lookup_capability(
                key,
                self.inventory_facts,
                domain_complete=complete,
            )
        if key.domain in {
            CapabilityDomain.SCALAR_FUNCTION,
            CapabilityDomain.UNARY_OPERATOR,
            CapabilityDomain.BINARY_OPERATOR,
            CapabilityDomain.COMPARISON,
            CapabilityDomain.NULL_TEST,
        }:
            _provider_facts, complete, reason = signature_lookup_inputs(key)
            facts = self.signature_facts
        elif key.domain is CapabilityDomain.AGGREGATE:
            _provider_facts, complete, reason = aggregate_lookup_inputs(key)
            facts = self.aggregate_facts
        elif key.domain is CapabilityDomain.WINDOW_FUNCTION:
            _provider_facts, complete, reason = window_lookup_inputs(key)
            facts = self.window_facts
        elif key.domain in {
            CapabilityDomain.EXPRESSION_STAGE,
            CapabilityDomain.CLAUSE,
        }:
            _provider_facts, complete, reason = stage_clause_lookup_inputs(key)
            facts = self.context_facts
        else:
            facts, complete, reason = (), False, None
        return lookup_capability(
            key,
            facts,
            domain_complete=complete,
            unknown_reason=reason,
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
        if (
            self.signature_fact is not None
            and type(self.signature_fact) is not ProjectModuleWindowSignatureFact
        ):
            raise TypeError("Window output signature fact must be exact.")
        if self.analysis is not None and not isinstance(
            self.analysis,
            (WindowExpressionAnalysis, WindowExpressionUnsupported),
        ):
            raise TypeError("Window output analysis has an invalid carrier.")
        if (
            self.project_fact is not None
            and type(self.project_fact) is not WindowResultProjectFact
        ):
            raise TypeError("Window output project fact must be exact.")
        _require_tuple(self.diagnostics, Diagnostic, "Window output diagnostics")
        if type(self.status) is not ProjectModuleCandidateBucketStatus:
            raise TypeError("Window output requires an exact status.")
        if self.reason is not None and (
            type(self.reason) is not str or not self.reason
        ):
            raise ValueError("Window output reason must be non-empty.")


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
        if self.state.status is not ProjectRelationRowSchemaStatus.CONCRETE and (
            self.aggregate_result_facts
            or any(fact.aggregate_result_fact is not None for fact in self.select_facts)
        ):
            raise ValueError(
                "Non-concrete semantic facts cannot publish aggregate results."
            )
        definition = self.owner.definition
        if type(definition) is SourceDef:
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
        elif type(definition) not in {TableDef, QueryDef}:
            raise ValueError("Relation semantic facts require a relation definition.")


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


def _window_signature_inventory() -> tuple[ProjectModuleWindowSignatureFact, ...]:
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
    return (*ranking, *distribution, *navigation)


def _capability_inventory() -> ProjectModuleCapabilityFactInventory:
    return ProjectModuleCapabilityFactInventory(
        inventory_facts=_CAPABILITY_FACTS,
        signature_facts=_CAPABILITY_SIGNATURE_FACTS,
        aggregate_facts=_AGGREGATE_CAPABILITY_FACTS,
        window_facts=_WINDOW_CAPABILITY_FACTS,
        context_facts=_CAPABILITY_CONTEXT_FACTS,
        window_signatures=_window_signature_inventory(),
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
                    semantic_fact = _build_derived_relation_facts(
                        owner=owner,
                        base_row_fact=base_row_fact,
                        resolution=resolution,
                        upstream=upstream,
                        capabilities=capabilities,
                    )
                built_for_module.append(semantic_fact)
                completed.append(semantic_fact)
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
                semantic_fact = _build_derived_relation_facts(
                    owner=base_row_fact.owner,
                    base_row_fact=base_row_fact,
                    resolution=resolution,
                    upstream=None,
                    capabilities=capabilities,
                )
                built_for_module.append(semantic_fact)
                completed.append(semantic_fact)
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
    return ProjectModuleSemanticFactSet(
        dependency_order=relation_resolutions.dependency_order,
        environments=tuple(environments),
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
) -> ProjectModuleRelationSemanticFacts:
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
        return _nonconcrete_relation_facts(
            owner=owner,
            base_row_fact=base_row_fact,
            resolution=resolution,
            state=state,
            let_scope=let_scope,
            group_key_occurrences=group_key_occurrences,
            capabilities=capabilities,
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
        return _nonconcrete_relation_facts(
            owner=owner,
            base_row_fact=base_row_fact,
            resolution=resolution,
            state=state,
            let_scope=let_scope,
            group_key_occurrences=group_key_occurrences,
            capabilities=capabilities,
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
        base_state = readiness.finalization.state
        aggregate_result_facts = tuple(
            fact
            for item in definition.select_items
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
    clause_dependencies = _clause_dependency_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        state=base_state,
        let_scope=let_scope,
        aggregate_result_facts=aggregate_result_facts,
    )
    clause_is_ambiguous = any(
        fact.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
        for fact in clause_dependencies
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
    state = (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=(
                ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
            ),
        )
        if clause_is_ambiguous
        else window_state
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
    return ProjectModuleRelationSemanticFacts(
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
        )
    let_values = (
        let_scope.value_types
        if let_scope.status is ProjectLetScopeFactsStatus.CONCRETE
        else None
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
        matching_lets = tuple(
            binding for binding in let_candidates if binding.name == local_name
        )
        matching_outputs = tuple(
            item
            for item in selected_items
            if _projection_output_name(item) == local_name
        )
        candidate_count = (
            (1 if input_field is not None else 0)
            + len(matching_lets)
            + len(matching_outputs)
        )
        if not qualifier_valid:
            status = ProjectModuleCandidateBucketStatus.UNKNOWN
        elif input_field is not None:
            # Existing row/let semantics give a concrete input field priority over
            # an invalid shadowing let while the raw let occurrences remain visible.
            status = ProjectModuleCandidateBucketStatus.CONCRETE
        elif input_status is not ProjectModuleCandidateBucketStatus.CONCRETE:
            status = input_status
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
) -> tuple[tuple[ProjectRowField, ...], tuple[ProjectAggregateResultFact, ...]]:
    target_fields: list[ProjectRowField] = []
    aggregate_facts: list[ProjectAggregateResultFact] = []
    for candidate in candidates:
        name = _projection_output_name(candidate)
        if name is None:
            continue
        if schema is not None and (field := schema.fields.get(name)) is not None:
            target_fields.append(field)
        if (fact := aggregate_by_name.get(name)) is not None:
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
    if len(candidates) > 1:
        return ProjectModuleCandidateBucketStatus.AMBIGUOUS
    if not candidates:
        return ProjectModuleCandidateBucketStatus.ABSENT
    if len(target_fields) == 1:
        return ProjectModuleCandidateBucketStatus.CONCRETE
    return ProjectModuleCandidateBucketStatus.UNKNOWN


def _clause_dependency_facts(
    *,
    owner: ProjectDeclarationOccurrence,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema | None,
    state: ProjectRelationRowSchemaState,
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
    inherited_status = _candidate_status_from_row_state(state)
    group_items = (
        ()
        if definition.group_by_clause is None
        else tuple(definition.group_by_clause.items)
    )
    for ordinal, item in enumerate(group_items):
        local_name, valid = _local_reference_name(
            item.key,
            relation_qualifier=definition.from_clause.source_name,
        )
        input_field = (
            None
            if input_schema is None or not valid
            else input_schema.fields.get(local_name)
        )
        facts.append(
            ProjectModuleClauseDependencyFact(
                owner=owner,
                role=ProjectModuleFactOccurrenceRole.GROUP_KEY,
                source_ordinal=ordinal,
                source_occurrence=item,
                target_occurrences=((item,) if input_field is not None else ()),
                target_fields=((input_field,) if input_field is not None else ()),
                status=(
                    ProjectModuleCandidateBucketStatus.CONCRETE
                    if input_field is not None
                    else (
                        inherited_status
                        if input_schema is None or input_schema.is_unknown
                        else ProjectModuleCandidateBucketStatus.ABSENT
                    )
                ),
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
                        effective = let_scope.binding_expressions[item.expression.name]
                        local_name = _direct_field_identity(
                            effective,
                            relation_qualifier=definition.from_clause.source_name,
                        )
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
                schema=schema,
                aggregate_by_name=aggregate_by_name,
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
                        state=state,
                        unavailable_let_status=unavailable_let_status,
                    ),
                )
            )
    return tuple(facts)


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
    concrete_facts: dict[str, WindowResultProjectFact] = {}
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
            project_fact = _build_window_result_project_fact(
                semantic_fact=analysis.semantic_fact,
                definition=definition,
                item=item,
                upstream_symbol=upstream_symbol,
                input_scope=input_scope,
            )
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
        if (
            status is ProjectModuleCandidateBucketStatus.CONCRETE
            and output_name is not None
            and project_fact is not None
        ):
            concrete_facts[output_name] = project_fact
        outputs.append(
            ProjectModuleWindowOutputFact(
                owner=owner,
                selected_output_ordinal=ordinal,
                item=item,
                output_name=output_name,
                signature_fact=signature,
                analysis=analysis,
                project_fact=project_fact,
                diagnostics=tuple(diagnostics),
                status=status,
                reason=reason,
            )
        )

    output_names = tuple(
        name
        for item in definition.select_items
        if (name := _projection_output_name(item)) is not None
    )
    if len(output_names) != len(set(output_names)):
        return _unknown_window_state(
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
        ), tuple(outputs)
    statuses = tuple(output.status for output in outputs)
    if all(
        status is ProjectModuleCandidateBucketStatus.CONCRETE for status in statuses
    ):
        final_schema = _final_window_schema(
            definition=definition,
            base_schema=base_schema,
            window_result_facts=concrete_facts,
        )
        return (
            ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.CONCRETE,
                schema=final_schema,
                reason=base_state.reason,
            ),
            tuple(outputs),
        )
    if len(set(statuses)) > 1:
        return _blocked_window_state(), tuple(outputs)
    status = statuses[0]
    if status is ProjectModuleCandidateBucketStatus.UNKNOWN:
        unknown_kinds = tuple(
            "unsupported"
            if isinstance(output.analysis, WindowExpressionUnsupported)
            else "unavailable"
            for output in outputs
        )
        if len(set(unknown_kinds)) > 1:
            return _blocked_window_state(), tuple(outputs)
        reason = (
            ProjectRelationRowSchemaReason.INVALID_WINDOW_OUTPUT
            if unknown_kinds[0] == "unsupported"
            else ProjectRelationRowSchemaReason.UNAVAILABLE_WINDOW_RESULT_FACT
        )
        return _unknown_window_state(reason), tuple(outputs)
    if status is ProjectModuleCandidateBucketStatus.DEFERRED:
        return (
            ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.DEFERRED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.WINDOW_RESULT_DEFERRED,
            ),
            tuple(outputs),
        )
    return _blocked_window_state(), tuple(outputs)


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
    matches = tuple(
        fact for fact in capabilities.window_signatures if fact.identity == identity
    )
    if len(matches) > 1:
        raise ValueError("Window identity cannot select multiple signature facts.")
    return matches[0] if matches else None


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
