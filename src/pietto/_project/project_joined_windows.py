"""Private Phase-63 joined window-computation and readiness authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._window_identity import WindowFunctionIdentity
from pietto._project import project_joined_aggregation as aggregation
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_joined_aggregation import (
    ProjectConcreteJoinedAggregation,
    ProjectJoinedAggregationMode,
    ProjectJoinedAggregationResult,
    ProjectJoinedAggregationSet,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedStageOutputRole,
    ProjectNonConcreteJoinedAggregation,
)
from pietto._project.project_joined_row_filter import (
    ProjectJoinedRowFilterPreservationWitness,
    ProjectJoinedRowMultiplicity,
)
from pietto._project.project_joined_row_semantics import (
    ProjectJoinedRowFieldSemantics,
)
from pietto._project.project_scalar_namespaces import ProjectJoinedLetValue
from pietto._project.window_semantics import WindowDependencyRole
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
    WindowUseKind,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ValueType
from pietto.semantic.window_analysis import (
    _WindowComputationAdmissionFailure,
    _relation_has_forbidden_window_placement,
    analyze_window_computation,
    named_window_resolution_diagnostics,
)
from pietto.semantic.window_semantics import (
    ComposedNamedWindowUse,
    NamedWindowOccurrence,
    NamedWindowResolutionFailure,
    NamedWindowUseResolutionFailure,
    QueryBlockOccurrence,
    ResolvedNamedWindowNamespace,
    WindowComponentOrigin,
    WindowComputationAnalysis,
    WindowComputationUnsupported,
    WindowFrameApplicability,
    WindowFrameBound,
    WindowFrameExclusion,
    WindowFrameUnit,
    WindowNthDirection,
    WindowNullTreatment,
    WindowOccurrenceIdentity,
    compose_named_window_use,
    resolve_named_window_namespace_for_query_block,
)
from pietto._project.project_scalar_references import scalar_field_reference_leaves

__all__: tuple[str, ...] = ()


def _definition(
    result: ProjectConcreteJoinedAggregation,
) -> TableDef | QueryDef:
    definition = result.input_filter.entry.owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Joined windows require a table or query owner.")
    return cast(TableDef | QueryDef, definition)


def _query_block(result: ProjectConcreteJoinedAggregation) -> QueryBlockOccurrence:
    block = (
        result.input_filter.namespace.binding_environment.scalar_environment.query_block
    )
    if block.owner_bridge.owner is not result.input_filter.entry.owner:
        raise ValueError("Joined windows lost the exact query-block owner bridge.")
    return block.owner_bridge.query_block


class ProjectJoinedWindowInputBindingKind(StrEnum):
    """Closed exact authorities admitted before window evaluation."""

    JOINED_FIELD = "joined_field"
    FIELD_BACKED_LET = "field_backed_let"
    GROUP_KEY = "group_key"
    AGGREGATE_RESULT = "aggregate_result"
    GROUP_KEY_BACKED_LET = "group_key_backed_let"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedWindowInputBinding:
    """One nameable pre-window value retaining its exact stage authority."""

    aggregation: ProjectConcreteJoinedAggregation = field(
        repr=False,
        compare=False,
        hash=False,
    )
    name: str
    qualifier: str | None
    kind: ProjectJoinedWindowInputBindingKind
    value_type: ValueType
    joined_field: ProjectJoinedRowFieldSemantics | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    let_value: ProjectJoinedLetValue | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    stage_output: ProjectJoinedStageOutputOccurrence | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.aggregation) is not ProjectConcreteJoinedAggregation:
            raise TypeError("Window input binding requires exact Slice-9 authority.")
        if type(self.name) is not str or not self.name:
            raise ValueError("Window input binding name must be nonempty.")
        if self.qualifier is not None and (
            type(self.qualifier) is not str or not self.qualifier
        ):
            raise ValueError("Window input qualifier must be nonempty or absent.")
        if type(self.kind) is not ProjectJoinedWindowInputBindingKind:
            raise TypeError("Window input binding kind must be exact.")
        if type(self.value_type) is not ValueType:
            raise TypeError("Window input value type must be exact.")

        input_filter = self.aggregation.input_filter
        if self.kind is ProjectJoinedWindowInputBindingKind.JOINED_FIELD:
            valid = (
                self.aggregation.mode is ProjectJoinedAggregationMode.ABSENT
                and type(self.joined_field) is ProjectJoinedRowFieldSemantics
                and self.let_value is None
                and self.stage_output is None
                and self.qualifier is not None
                and self.name == self.joined_field.scalar_field.evidence.name
                and self.value_type is self.joined_field.scalar_field.value_type
                and any(self.joined_field is item for item in input_filter.fields)
            )
        elif self.kind is ProjectJoinedWindowInputBindingKind.FIELD_BACKED_LET:
            valid = (
                self.aggregation.mode is ProjectJoinedAggregationMode.ABSENT
                and type(self.joined_field) is ProjectJoinedRowFieldSemantics
                and type(self.let_value) is ProjectJoinedLetValue
                and self.stage_output is None
                and self.qualifier is None
                and self.name == self.let_value.occurrence.binding.name
                and self.value_type is self.let_value.value_type
                and any(
                    self.let_value is item for item in input_filter.namespace.let_values
                )
                and any(self.joined_field is item for item in input_filter.fields)
            )
        elif self.kind in {
            ProjectJoinedWindowInputBindingKind.GROUP_KEY,
            ProjectJoinedWindowInputBindingKind.AGGREGATE_RESULT,
        }:
            expected_role = (
                ProjectJoinedStageOutputRole.GROUP_KEY
                if self.kind is ProjectJoinedWindowInputBindingKind.GROUP_KEY
                else ProjectJoinedStageOutputRole.AGGREGATE_RESULT
            )
            valid = (
                self.joined_field is None
                and self.let_value is None
                and type(self.stage_output) is ProjectJoinedStageOutputOccurrence
                and self.stage_output.role is expected_role
                and self.qualifier is None
                and self.name == self.stage_output.output_name
                and self.value_type is self.stage_output.value_type
                and any(
                    self.stage_output is item for item in self.aggregation.stage_outputs
                )
            )
        else:
            valid = (
                self.aggregation.mode is ProjectJoinedAggregationMode.GROUPED
                and type(self.joined_field) is ProjectJoinedRowFieldSemantics
                and type(self.let_value) is ProjectJoinedLetValue
                and type(self.stage_output) is ProjectJoinedStageOutputOccurrence
                and self.stage_output.role is ProjectJoinedStageOutputRole.GROUP_KEY
                and self.stage_output.group_key is not None
                and self.stage_output.group_key.field_semantics is self.joined_field
                and self.qualifier is None
                and self.name == self.let_value.occurrence.binding.name
                and self.value_type is self.stage_output.value_type
                and any(
                    self.let_value is item for item in input_filter.namespace.let_values
                )
                and any(self.joined_field is item for item in input_filter.fields)
                and any(
                    self.stage_output is item for item in self.aggregation.stage_outputs
                )
            )
        if not valid:
            raise ValueError("Window input binding lost its exact target authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedWindowInputNamespace:
    """Occurrence-safe immutable input namespace for one Slice-9 result."""

    aggregation: ProjectConcreteJoinedAggregation = field(
        repr=False,
        compare=False,
        hash=False,
    )
    bindings: tuple[ProjectJoinedWindowInputBinding, ...]
    post_aggregate: aggregation.ProjectJoinedPostAggregateNamespace = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.aggregation) is not ProjectConcreteJoinedAggregation or (
            type(self.bindings) is not tuple
            or any(
                type(binding) is not ProjectJoinedWindowInputBinding
                or binding.aggregation is not self.aggregation
                for binding in self.bindings
            )
        ):
            raise ValueError("Window input namespace requires exact Slice-9 bindings.")
        if len({id(binding) for binding in self.bindings}) != len(self.bindings):
            raise ValueError("Window input namespace cannot repeat one occurrence.")
        expected = _window_input_bindings(self.aggregation)
        if len(self.bindings) != len(expected) or any(
            actual.kind is not retained.kind
            or actual.name != retained.name
            or actual.qualifier != retained.qualifier
            or actual.value_type is not retained.value_type
            or actual.joined_field is not retained.joined_field
            or actual.let_value is not retained.let_value
            or actual.stage_output is not retained.stage_output
            for actual, retained in zip(self.bindings, expected, strict=True)
        ):
            raise ValueError("Window input namespace must be complete and ordered.")
        object.__setattr__(self, "post_aggregate", self.aggregation.post_aggregate)

    def candidates(
        self,
        expression: NameExpr | DottedNameExpr,
    ) -> tuple[ProjectJoinedWindowInputBinding, ...]:
        """Return the complete exact lookup bucket without a winner fallback."""

        if type(expression) is NameExpr:
            return tuple(
                binding for binding in self.bindings if binding.name == expression.name
            )
        if type(expression) is not DottedNameExpr:
            raise TypeError("Window input lookup requires a direct field expression.")
        if len(expression.parts) != 2:
            return ()
        qualifier, name = expression.parts
        return tuple(
            binding
            for binding in self.bindings
            if binding.qualifier == qualifier and binding.name == name
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedWindowInputResolution:
    """One exact direct reference with its complete occurrence bucket."""

    namespace: ProjectJoinedWindowInputNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: NameExpr | DottedNameExpr = field(
        repr=False,
        compare=False,
        hash=False,
    )
    candidates: tuple[ProjectJoinedWindowInputBinding, ...]
    status: ProjectModuleCandidateBucketStatus = field(init=False)
    target: ProjectJoinedWindowInputBinding | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.namespace) is not ProjectJoinedWindowInputNamespace or type(
            self.expression
        ) not in {NameExpr, DottedNameExpr}:
            raise TypeError("Window input resolution requires exact lookup evidence.")
        if self.candidates != self.namespace.candidates(self.expression):
            raise ValueError("Window input candidates must be complete and ordered.")
        status = (
            ProjectModuleCandidateBucketStatus.ABSENT
            if not self.candidates
            else (
                ProjectModuleCandidateBucketStatus.CONCRETE
                if len(self.candidates) == 1
                else ProjectModuleCandidateBucketStatus.AMBIGUOUS
            )
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "target",
            self.candidates[0] if len(self.candidates) == 1 else None,
        )


def _visible_field_qualifier(
    result: ProjectConcreteJoinedAggregation,
    field_semantics: ProjectJoinedRowFieldSemantics,
) -> str:
    scalar_field = field_semantics.scalar_field
    matches = tuple(
        retained.binding.name
        for retained in result.input_filter.namespace.bindings
        if any(candidate is scalar_field for candidate in retained.fields)
    )
    if len(matches) != 1:
        raise ValueError("Visible joined field requires one authored binding.")
    return matches[0]


def _field_backed_let(
    result: ProjectConcreteJoinedAggregation,
    value: ProjectJoinedLetValue,
) -> ProjectJoinedRowFieldSemantics | None:
    _, field_semantics, computed = (
        aggregation._direct_field_resolution(
            result.input_filter,
            cast(NameExpr | DottedNameExpr, value.occurrence.expression),
            expand_let=True,
        )
        if type(value.occurrence.expression) in {NameExpr, DottedNameExpr}
        else ((), None, True)
    )
    return None if computed else field_semantics


def _window_input_bindings(
    result: ProjectConcreteJoinedAggregation,
) -> tuple[ProjectJoinedWindowInputBinding, ...]:
    bindings: list[ProjectJoinedWindowInputBinding] = []
    if result.mode is ProjectJoinedAggregationMode.ABSENT:
        for scalar_field in result.input_filter.namespace.visible_fields:
            field_semantics = aggregation._field_semantics(
                result.input_filter,
                scalar_field,
            )
            bindings.append(
                ProjectJoinedWindowInputBinding(
                    aggregation=result,
                    name=scalar_field.evidence.name,
                    qualifier=_visible_field_qualifier(result, field_semantics),
                    kind=ProjectJoinedWindowInputBindingKind.JOINED_FIELD,
                    value_type=scalar_field.value_type,
                    joined_field=field_semantics,
                )
            )
        for value in result.input_filter.namespace.let_values:
            field_semantics = _field_backed_let(result, value)
            if field_semantics is not None:
                bindings.append(
                    ProjectJoinedWindowInputBinding(
                        aggregation=result,
                        name=value.occurrence.binding.name,
                        qualifier=None,
                        kind=ProjectJoinedWindowInputBindingKind.FIELD_BACKED_LET,
                        value_type=value.value_type,
                        joined_field=field_semantics,
                        let_value=value,
                    )
                )
    else:
        for output in result.stage_outputs:
            bindings.append(
                ProjectJoinedWindowInputBinding(
                    aggregation=result,
                    name=output.output_name,
                    qualifier=None,
                    kind=(
                        ProjectJoinedWindowInputBindingKind.GROUP_KEY
                        if output.role is ProjectJoinedStageOutputRole.GROUP_KEY
                        else ProjectJoinedWindowInputBindingKind.AGGREGATE_RESULT
                    ),
                    value_type=output.value_type,
                    stage_output=output,
                )
            )
        group_outputs = tuple(
            output
            for output in result.stage_outputs
            if output.role is ProjectJoinedStageOutputRole.GROUP_KEY
        )
        for value in result.input_filter.namespace.let_values:
            field_semantics = _field_backed_let(result, value)
            matches = tuple(
                output
                for output in group_outputs
                if output.group_key is not None
                and output.group_key.field_semantics is field_semantics
            )
            if len(matches) == 1:
                bindings.append(
                    ProjectJoinedWindowInputBinding(
                        aggregation=result,
                        name=value.occurrence.binding.name,
                        qualifier=None,
                        kind=(ProjectJoinedWindowInputBindingKind.GROUP_KEY_BACKED_LET),
                        value_type=matches[0].value_type,
                        joined_field=field_semantics,
                        let_value=value,
                        stage_output=matches[0],
                    )
                )
    return tuple(bindings)


def build_project_joined_window_input_namespace(
    result: ProjectConcreteJoinedAggregation,
) -> ProjectJoinedWindowInputNamespace:
    """Build the exact pre-window namespace without a joined RowSchema."""

    if type(result) is not ProjectConcreteJoinedAggregation:
        raise TypeError("Window input namespace requires concrete Slice-9 authority.")
    return ProjectJoinedWindowInputNamespace(
        aggregation=result,
        bindings=_window_input_bindings(result),
    )


class ProjectWindowComputationSiteKind(StrEnum):
    """Selected result occurrences and hidden inline computations are distinct."""

    SELECTED_OUTPUT = "selected_output"
    HIDDEN_INLINE = "hidden_inline"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectWindowComputationSite:
    """One computation site, never a final field identity."""

    kind: ProjectWindowComputationSiteKind
    root: ProjectConcreteJoinedAggregation | ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: WindowExpr = field(repr=False, compare=False, hash=False)
    item: SelectItem | None = field(default=None, repr=False, compare=False, hash=False)
    selected_output_ordinal: int | None = None
    occurrence: WindowOccurrenceIdentity | None = None

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not ProjectWindowComputationSiteKind
            or type(self.expression) is not WindowExpr
        ):
            raise TypeError("Window computation site requires exact typed evidence.")
        if self.kind is ProjectWindowComputationSiteKind.SELECTED_OUTPUT:
            if type(self.root) is not ProjectConcreteJoinedAggregation:
                raise TypeError("Selected window site requires exact Slice-9 input.")
            definition = _definition(self.root)
            valid = (
                type(self.item) is SelectItem
                and type(self.selected_output_ordinal) is int
                and 0 <= self.selected_output_ordinal < len(definition.select_items)
                and definition.select_items[self.selected_output_ordinal] is self.item
                and self.item.expression is self.expression
                and type(self.occurrence) is WindowOccurrenceIdentity
                and self.occurrence.source_id == _query_block(self.root).source_id
                and self.occurrence.relation_name == definition.name
                and self.occurrence.selected_output_ordinal
                == self.selected_output_ordinal
                and self.occurrence.span == self.expression.span
            )
        else:
            valid = (
                type(self.root) is ProjectConcreteJoinedWindowStage
                and self.expression.use_kind is WindowUseKind.INLINE
                and self.item is None
                and self.selected_output_ordinal is None
                and self.occurrence is None
            )
        if not valid:
            raise ValueError("Window computation site lost its exact identity law.")

    @property
    def input_aggregation(self) -> ProjectConcreteJoinedAggregation:
        if type(self.root) is ProjectConcreteJoinedAggregation:
            return self.root
        assert type(self.root) is ProjectConcreteJoinedWindowStage
        return self.root.input_aggregation


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectWindowDependencyOccurrence:
    """One duplicate-preserving exact Phase-63 window data dependency."""

    site: ProjectWindowComputationSite = field(
        repr=False,
        compare=False,
        hash=False,
    )
    global_ordinal: int
    role_ordinal: int
    role: WindowDependencyRole
    expression: Expression = field(repr=False, compare=False, hash=False)
    target: ProjectJoinedWindowInputNamespace | ProjectJoinedWindowInputBinding
    location: SourceLocation

    def __post_init__(self) -> None:
        if type(self.site) is not ProjectWindowComputationSite or any(
            type(value) is not int or value < 0
            for value in (self.global_ordinal, self.role_ordinal)
        ):
            raise ValueError("Window dependency ordinals and site must be exact.")
        if type(self.role) is not WindowDependencyRole or not isinstance(
            self.expression,
            Expression,
        ):
            raise TypeError("Window dependency role and expression must be exact.")
        if type(self.location) is not SourceLocation:
            raise TypeError("Window dependency location must be exact.")
        if self.location != _source_location(self.expression):
            raise ValueError("Window dependency location must match its expression.")
        if self.role is WindowDependencyRole.RELATION_INPUT:
            valid = (
                type(self.target) is ProjectJoinedWindowInputNamespace
                and self.target.aggregation is self.site.input_aggregation
            )
        else:
            valid = (
                type(self.target) is ProjectJoinedWindowInputBinding
                and self.target.aggregation is self.site.input_aggregation
            )
        if not valid:
            raise ValueError(
                "Window dependency target must retain pre-window authority."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectWindowSemanticProvenance:
    """Target-neutral projection of the shared computation semantics."""

    analysis: WindowComputationAnalysis
    function_identity: WindowFunctionIdentity
    use_kind: WindowUseKind
    named_target: NamedWindowOccurrence | None
    partition_origin: WindowComponentOrigin
    order_origin: WindowComponentOrigin
    frame_origin: WindowComponentOrigin
    frame_applicability: WindowFrameApplicability
    frame_unit: WindowFrameUnit | None
    frame_start: WindowFrameBound | None
    frame_end: WindowFrameBound | None
    frame_exclusion: WindowFrameExclusion | None
    null_treatment: WindowNullTreatment | None
    null_treatment_is_explicit: bool
    nth_direction: WindowNthDirection | None
    nth_direction_is_explicit: bool

    def __post_init__(self) -> None:
        if (
            type(self.analysis) is not WindowComputationAnalysis
            or type(self.function_identity) is not WindowFunctionIdentity
            or (
                self.function_identity != self.analysis.expression.identity
                or self.use_kind is not self.analysis.authored_expression.use_kind
            )
        ):
            raise ValueError("Window provenance must retain its common computation.")
        named = self.analysis.resolved_named_use
        expected_target = (
            None if named is None else named.composed.target_template.occurrence
        )
        resolved = self.analysis.validated_specification.resolved
        frame = resolved.frame
        modifiers = self.analysis.modifiers
        if (
            self.named_target != expected_target
            or self.partition_origin is not resolved.partition_origin
            or self.order_origin is not resolved.ordering_origin
            or self.frame_origin is not frame.origin
            or self.frame_applicability is not frame.applicability
            or self.frame_unit is not frame.unit
            or self.frame_start is not frame.start
            or self.frame_end is not frame.end
            or self.frame_exclusion is not frame.exclusion
            or self.null_treatment is not modifiers.null_treatment
            or self.null_treatment_is_explicit
            is not modifiers.null_treatment_is_explicit
            or self.nth_direction is not modifiers.nth_direction
            or self.nth_direction_is_explicit is not modifiers.nth_direction_is_explicit
        ):
            raise ValueError("Window provenance must be an exact semantic projection.")


def _semantic_provenance(
    analysis: WindowComputationAnalysis,
) -> ProjectWindowSemanticProvenance:
    resolved = analysis.validated_specification.resolved
    frame = resolved.frame
    modifiers = analysis.modifiers
    named = analysis.resolved_named_use
    return ProjectWindowSemanticProvenance(
        analysis=analysis,
        function_identity=analysis.expression.identity,
        use_kind=analysis.authored_expression.use_kind,
        named_target=(
            None if named is None else named.composed.target_template.occurrence
        ),
        partition_origin=resolved.partition_origin,
        order_origin=resolved.ordering_origin,
        frame_origin=frame.origin,
        frame_applicability=frame.applicability,
        frame_unit=frame.unit,
        frame_start=frame.start,
        frame_end=frame.end,
        frame_exclusion=frame.exclusion,
        null_treatment=modifiers.null_treatment,
        null_treatment_is_explicit=modifiers.null_treatment_is_explicit,
        nth_direction=modifiers.nth_direction,
        nth_direction_is_explicit=modifiers.nth_direction_is_explicit,
    )


class ProjectWindowComputationNonConcreteReason(StrEnum):
    """Closed blockers after a valid computation site exists."""

    NAMED_USE_NON_CONCRETE = "named_use_non_concrete"
    SEMANTIC_NON_CONCRETE = "semantic_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteWindowComputation:
    """One exact successful selected or hidden computation without field identity."""

    site: ProjectWindowComputationSite = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_namespace: ProjectJoinedWindowInputNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...]
    analysis: WindowComputationAnalysis
    dependencies: tuple[ProjectWindowDependencyOccurrence, ...]
    semantic_provenance: ProjectWindowSemanticProvenance
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.site) is not ProjectWindowComputationSite
            or type(self.input_namespace) is not ProjectJoinedWindowInputNamespace
            or self.input_namespace.aggregation is not self.site.input_aggregation
            or type(self.analysis) is not WindowComputationAnalysis
            or self.analysis.authored_expression is not self.site.expression
            or type(self.semantic_provenance) is not ProjectWindowSemanticProvenance
            or self.semantic_provenance.analysis is not self.analysis
            or type(self.resolutions) is not tuple
            or any(
                type(resolution) is not ProjectJoinedWindowInputResolution
                or resolution.namespace is not self.input_namespace
                for resolution in self.resolutions
            )
            or type(self.dependencies) is not tuple
            or any(
                type(dependency) is not ProjectWindowDependencyOccurrence
                or dependency.site is not self.site
                for dependency in self.dependencies
            )
            or type(self.diagnostics) is not tuple
            or any(
                type(diagnostic) is not Diagnostic
                or diagnostic.severity is Severity.ERROR
                for diagnostic in self.diagnostics
            )
        ):
            raise ValueError("Concrete window computation requires exact authority.")
        references = _input_reference_expressions(self.analysis.expression)
        if len(self.resolutions) != len(references) or any(
            resolution.expression is not reference
            for resolution, reference in zip(
                self.resolutions,
                references,
                strict=True,
            )
        ):
            raise ValueError("Window resolutions must cover exact input occurrences.")
        expected_dependencies = tuple(
            (role, role_ordinal, expression, target)
            for role, inputs in _dependency_inputs(
                namespace=self.input_namespace,
                resolutions=self.resolutions,
                analysis=self.analysis,
            )
            for role_ordinal, (expression, target) in enumerate(inputs)
        )
        if len(self.dependencies) != len(expected_dependencies) or any(
            dependency.global_ordinal != global_ordinal
            or dependency.role is not role
            or dependency.role_ordinal != role_ordinal
            or dependency.expression is not expression
            or dependency.target is not target
            for global_ordinal, (
                dependency,
                (role, role_ordinal, expression, target),
            ) in enumerate(zip(self.dependencies, expected_dependencies, strict=True))
        ):
            raise ValueError("Window dependencies must retain exact role and targets.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteWindowComputation:
    """One exact selected or hidden semantic blocker with no result binding."""

    site: ProjectWindowComputationSite = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_namespace: ProjectJoinedWindowInputNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectWindowComputationNonConcreteReason
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...] = ()
    named_failure: NamedWindowUseResolutionFailure | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_failure: WindowComputationUnsupported | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    result_binding: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.site) is not ProjectWindowComputationSite
            or self.input_namespace.aggregation is not self.site.input_aggregation
            or type(self.reason) is not ProjectWindowComputationNonConcreteReason
            or any(
                type(item) is not ProjectJoinedWindowInputResolution
                or item.namespace is not self.input_namespace
                for item in self.resolutions
            )
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("Window computation blocker requires exact evidence.")
        if (
            self.reason
            is ProjectWindowComputationNonConcreteReason.NAMED_USE_NON_CONCRETE
        ):
            valid = (
                type(self.named_failure) is NamedWindowUseResolutionFailure
                and self.semantic_failure is None
                and not self.resolutions
            )
        else:
            valid = (
                self.named_failure is None
                and type(self.semantic_failure) is WindowComputationUnsupported
            )
        if not valid:
            raise ValueError("Window computation blocker reason must match evidence.")


type ProjectWindowComputationResult = (
    ProjectConcreteWindowComputation | ProjectNonConcreteWindowComputation
)


def _source_location(expression: Expression) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _input_reference_expressions(
    expression: WindowExpr,
) -> tuple[NameExpr | DottedNameExpr, ...]:
    roots = (
        *expression.call.arguments,
        *expression.spec.partition_by,
        *(item.expression for item in expression.spec.order_by),
    )
    return tuple(leaf for root in roots for leaf in scalar_field_reference_leaves(root))


def _resolution_for(
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...],
    expression: NameExpr | DottedNameExpr,
) -> ProjectJoinedWindowInputBinding:
    matches = tuple(item for item in resolutions if item.expression is expression)
    if len(matches) != 1 or matches[0].target is None:
        raise ValueError("Concrete window dependency requires one exact input target.")
    return matches[0].target


def _dependency_inputs(
    *,
    namespace: ProjectJoinedWindowInputNamespace,
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...],
    analysis: WindowComputationAnalysis,
) -> tuple[
    tuple[
        WindowDependencyRole,
        tuple[
            tuple[
                Expression,
                ProjectJoinedWindowInputNamespace | ProjectJoinedWindowInputBinding,
            ],
            ...,
        ],
    ],
    ...,
]:
    argument_expressions: tuple[NameExpr | DottedNameExpr, ...] = ()
    default_expressions: tuple[NameExpr | DottedNameExpr, ...] = ()
    if analysis.navigation is not None:
        value = analysis.navigation.value_expression
        if type(value) in {NameExpr, DottedNameExpr}:
            argument_expressions = (cast(NameExpr | DottedNameExpr, value),)
        default = analysis.navigation.default_fact.expression
        if type(default) in {NameExpr, DottedNameExpr}:
            default_expressions = (cast(NameExpr | DottedNameExpr, default),)
    elif analysis.frame_value is not None:
        value = analysis.frame_value.value_expression
        if type(value) in {NameExpr, DottedNameExpr}:
            argument_expressions = (cast(NameExpr | DottedNameExpr, value),)

    return (
        (
            WindowDependencyRole.RELATION_INPUT,
            ()
            if argument_expressions or default_expressions
            else ((analysis.expression.call, namespace),),
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            tuple(
                (expression, _resolution_for(resolutions, expression))
                for expression in argument_expressions
            ),
        ),
        (
            WindowDependencyRole.WINDOW_DEFAULT,
            tuple(
                (expression, _resolution_for(resolutions, expression))
                for expression in default_expressions
            ),
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            tuple(
                (
                    binding.expression,
                    _resolution_for(resolutions, binding.expression),
                )
                for binding in analysis.partition_bindings
            ),
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            tuple(
                (
                    binding.expression,
                    _resolution_for(resolutions, binding.expression),
                )
                for binding in analysis.order_bindings
            ),
        ),
    )


def _dependencies(
    *,
    site: ProjectWindowComputationSite,
    namespace: ProjectJoinedWindowInputNamespace,
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...],
    analysis: WindowComputationAnalysis,
) -> tuple[ProjectWindowDependencyOccurrence, ...]:
    inputs = _dependency_inputs(
        namespace=namespace,
        resolutions=resolutions,
        analysis=analysis,
    )
    dependencies: list[ProjectWindowDependencyOccurrence] = []
    for role, role_inputs in inputs:
        for role_ordinal, (expression, target) in enumerate(role_inputs):
            dependencies.append(
                ProjectWindowDependencyOccurrence(
                    site=site,
                    global_ordinal=len(dependencies),
                    role_ordinal=role_ordinal,
                    role=role,
                    expression=expression,
                    target=target,
                    location=_source_location(expression),
                )
            )
    return tuple(dependencies)


def _analyze_site(
    site: ProjectWindowComputationSite,
    namespace: ProjectJoinedWindowInputNamespace,
    named_namespace: ResolvedNamedWindowNamespace,
) -> ProjectWindowComputationResult:
    expression = site.expression
    diagnostics: list[Diagnostic] = []
    named_composition: ComposedNamedWindowUse | None = None
    if expression.use_kind is not WindowUseKind.INLINE:
        ordinal = site.selected_output_ordinal
        if ordinal is None:
            raise ValueError("Only selected sites may compose named windows.")
        composition = compose_named_window_use(
            named_namespace,
            expression,
            selected_output_ordinal=ordinal,
        )
        if type(composition) is NamedWindowUseResolutionFailure:
            diagnostics.extend(named_window_resolution_diagnostics(composition))
            return ProjectNonConcreteWindowComputation(
                site=site,
                input_namespace=namespace,
                reason=(
                    ProjectWindowComputationNonConcreteReason.NAMED_USE_NON_CONCRETE
                ),
                named_failure=composition,
                diagnostics=tuple(diagnostics),
            )
        assert type(composition) is ComposedNamedWindowUse
        named_composition = composition

    admission: _WindowComputationAdmissionFailure | None = None
    if site.kind is ProjectWindowComputationSiteKind.SELECTED_OUTPUT:
        assert site.item is not None
        definition = _definition(site.input_aggregation)
        if site.item.alias is None:
            admission = _WindowComputationAdmissionFailure(
                reason=(
                    f"{expression.identity.name} requires a direct selected output alias"
                )
            )
        elif _relation_has_forbidden_window_placement(definition, site.item):
            admission = _WindowComputationAdmissionFailure(
                reason="window expression appears outside one direct selected output"
            )
    if (
        admission is None
        and site.input_aggregation.mode is ProjectJoinedAggregationMode.GLOBAL
    ):
        admission = _WindowComputationAdmissionFailure(
            reason=(
                f"no-group aggregate context does not admit {expression.identity.name}"
            ),
            code=None,
        )

    value_types: dict[Expression, ValueType] = {}
    resolutions: tuple[ProjectJoinedWindowInputResolution, ...] = ()

    def prepare_inputs(effective: WindowExpr) -> None:
        nonlocal resolutions
        resolutions = tuple(
            ProjectJoinedWindowInputResolution(
                namespace=namespace,
                expression=reference,
                candidates=namespace.candidates(reference),
            )
            for reference in _input_reference_expressions(effective)
        )
        for resolution in resolutions:
            if resolution.target is not None:
                value_types[resolution.expression] = resolution.target.value_type

    semantic = analyze_window_computation(
        expression=expression,
        input_schema=None,
        field_qualifier="",
        value_types=value_types,
        diagnostics=diagnostics,
        allow_qualified_fields=False,
        named_composition=named_composition,
        admission_failure=admission,
        prepare_inputs=prepare_inputs,
    )
    if type(semantic) is WindowComputationUnsupported:
        return ProjectNonConcreteWindowComputation(
            site=site,
            input_namespace=namespace,
            reason=ProjectWindowComputationNonConcreteReason.SEMANTIC_NON_CONCRETE,
            resolutions=resolutions,
            semantic_failure=semantic,
            diagnostics=tuple(diagnostics),
        )
    assert type(semantic) is WindowComputationAnalysis
    dependencies = _dependencies(
        site=site,
        namespace=namespace,
        resolutions=resolutions,
        analysis=semantic,
    )
    return ProjectConcreteWindowComputation(
        site=site,
        input_namespace=namespace,
        resolutions=resolutions,
        analysis=semantic,
        dependencies=dependencies,
        semantic_provenance=_semantic_provenance(semantic),
        diagnostics=tuple(diagnostics),
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSelectedWindowResultBinding:
    """One selected result binding before final field identity exists."""

    computation: ProjectConcreteWindowComputation = field(
        repr=False,
        compare=False,
        hash=False,
    )
    item: SelectItem = field(init=False, repr=False, compare=False, hash=False)
    selected_output_ordinal: int = field(init=False)
    output_name: str = field(init=False)
    occurrence: WindowOccurrenceIdentity = field(init=False)
    value_type: ValueType = field(init=False)

    def __post_init__(self) -> None:
        if type(self.computation) is not ProjectConcreteWindowComputation or (
            self.computation.site.kind
            is not ProjectWindowComputationSiteKind.SELECTED_OUTPUT
        ):
            raise TypeError("Selected result binding requires a selected computation.")
        site = self.computation.site
        assert site.item is not None
        assert site.selected_output_ordinal is not None
        assert site.occurrence is not None
        if (
            site.item.alias is None
            or self.computation.analysis.result.value_type is None
        ):
            raise ValueError("Selected window result requires an exact alias and type.")
        object.__setattr__(self, "item", site.item)
        object.__setattr__(
            self, "selected_output_ordinal", site.selected_output_ordinal
        )
        object.__setattr__(self, "output_name", site.item.alias)
        object.__setattr__(self, "occurrence", site.occurrence)
        object.__setattr__(
            self,
            "value_type",
            self.computation.analysis.result.value_type,
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedPostWindowNamespace:
    """Separate pre-window inputs and selected results for Slice 11."""

    pre_window: ProjectJoinedWindowInputNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_results: tuple[ProjectSelectedWindowResultBinding, ...]

    def __post_init__(self) -> None:
        if (
            type(self.pre_window) is not ProjectJoinedWindowInputNamespace
            or type(self.selected_results) is not tuple
            or any(
                type(result) is not ProjectSelectedWindowResultBinding
                or result.computation.input_namespace is not self.pre_window
                for result in self.selected_results
            )
        ):
            raise ValueError("Post-window namespace requires exact separate domains.")
        ordinals = tuple(
            result.selected_output_ordinal for result in self.selected_results
        )
        if any(left >= right for left, right in zip(ordinals, ordinals[1:])):
            raise ValueError("Selected window results must retain source order.")

    def input_candidates(
        self, name: str
    ) -> tuple[ProjectJoinedWindowInputBinding, ...]:
        if type(name) is not str:
            raise TypeError("Post-window input lookup name must be exact.")
        return tuple(
            binding for binding in self.pre_window.bindings if binding.name == name
        )

    def selected_candidates(
        self,
        name: str,
    ) -> tuple[ProjectSelectedWindowResultBinding, ...]:
        if type(name) is not str:
            raise TypeError("Post-window result lookup name must be exact.")
        return tuple(
            result for result in self.selected_results if result.output_name == name
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedWindowPreservationWitness:
    """Reference-only row/property preservation across window evaluation."""

    aggregation: ProjectConcreteJoinedAggregation = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_filter_preservation: ProjectJoinedRowFilterPreservationWitness = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    multiplicity: ProjectJoinedRowMultiplicity = field(init=False)
    filters_rows: bool = field(init=False, default=False)
    establishes_relation_order: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if type(self.aggregation) is not ProjectConcreteJoinedAggregation:
            raise TypeError("Window preservation requires concrete Slice-9 input.")
        preservation = self.aggregation.input_filter.preservation
        object.__setattr__(self, "input_filter_preservation", preservation)
        object.__setattr__(self, "multiplicity", preservation.multiplicity)

    @property
    def intrinsic_grain(self):
        return self.input_filter_preservation.input_property_bridge.grain

    @property
    def relation_ordering(self):
        return self.input_filter_preservation.input_property_bridge.ordering


class ProjectJoinedWindowStageKind(StrEnum):
    """Concrete operator absence versus selected window evaluation."""

    ABSENT = "absent"
    WINDOW_EVALUATION = "window_evaluation"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedWindowStage:
    """One closed Slice-10 absent or selected-window stage."""

    aggregation_set: ProjectJoinedAggregationSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_aggregation: ProjectConcreteJoinedAggregation = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectJoinedWindowStageKind
    named_namespace: ResolvedNamedWindowNamespace
    pre_window: ProjectJoinedWindowInputNamespace
    computations: tuple[ProjectConcreteWindowComputation, ...]
    selected_results: tuple[ProjectSelectedWindowResultBinding, ...]
    post_window: ProjectJoinedPostWindowNamespace
    preservation: ProjectJoinedWindowPreservationWitness
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        definition = _definition(self.input_aggregation)
        query_block = _query_block(self.input_aggregation)
        selected_items = tuple(
            item
            for item in definition.select_items
            if type(item.expression) is WindowExpr
        )
        if (
            type(self.aggregation_set) is not ProjectJoinedAggregationSet
            or not any(
                self.input_aggregation is item for item in self.aggregation_set.results
            )
            or type(self.kind) is not ProjectJoinedWindowStageKind
            or type(self.named_namespace) is not ResolvedNamedWindowNamespace
            or self.named_namespace.definition is not definition
            or self.named_namespace.query_block is not query_block
            or self.pre_window.aggregation is not self.input_aggregation
            or len(self.computations) != len(selected_items)
            or any(
                computation.site.item is not item
                for computation, item in zip(
                    self.computations,
                    selected_items,
                    strict=True,
                )
            )
            or tuple(result.computation for result in self.selected_results)
            != self.computations
            or self.post_window.pre_window is not self.pre_window
            or self.post_window.selected_results is not self.selected_results
            or self.preservation.aggregation is not self.input_aggregation
            or any(
                diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
            )
        ):
            raise ValueError("Concrete window stage requires complete exact authority.")
        if self.kind is ProjectJoinedWindowStageKind.ABSENT:
            if self.computations or self.selected_results:
                raise ValueError("Absent window stage cannot manufacture an operator.")
        elif not self.computations or (
            self.input_aggregation.mode is ProjectJoinedAggregationMode.GLOBAL
        ):
            raise ValueError("Window evaluation requires supported selected sites.")


class ProjectJoinedWindowStageNonConcreteReason(StrEnum):
    """Closed Slice-10 stage blocker families."""

    UPSTREAM_AGGREGATION_NON_CONCRETE = "upstream_aggregation_non_concrete"
    NAMED_NAMESPACE_NON_CONCRETE = "named_namespace_non_concrete"
    SELECTED_COMPUTATION_NON_CONCRETE = "selected_computation_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedWindowStage:
    """One exact Slice-10 terminal with no post-window authority."""

    aggregation_set: ProjectJoinedAggregationSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_aggregation: ProjectJoinedAggregationResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectJoinedWindowStageNonConcreteReason
    pre_window: ProjectJoinedWindowInputNamespace | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    named_failure: NamedWindowResolutionFailure | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    attempts: tuple[ProjectWindowComputationResult, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    post_window: None = field(init=False, default=None)
    selected_results: tuple[ProjectSelectedWindowResultBinding, ...] = field(
        init=False,
        default=(),
    )

    def __post_init__(self) -> None:
        if (
            type(self.aggregation_set) is not ProjectJoinedAggregationSet
            or not any(
                self.input_aggregation is item for item in self.aggregation_set.results
            )
            or type(self.reason) is not ProjectJoinedWindowStageNonConcreteReason
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("Window stage terminal requires exact Slice-9 authority.")
        if self.reason is (
            ProjectJoinedWindowStageNonConcreteReason.UPSTREAM_AGGREGATION_NON_CONCRETE
        ):
            valid = (
                type(self.input_aggregation) is ProjectNonConcreteJoinedAggregation
                and self.pre_window is None
                and self.named_failure is None
                and not self.attempts
                and not self.diagnostics
            )
        elif self.reason is (
            ProjectJoinedWindowStageNonConcreteReason.NAMED_NAMESPACE_NON_CONCRETE
        ):
            valid = (
                type(self.input_aggregation) is ProjectConcreteJoinedAggregation
                and self.pre_window is not None
                and type(self.named_failure) is NamedWindowResolutionFailure
                and not self.attempts
            )
        else:
            valid = (
                type(self.input_aggregation) is ProjectConcreteJoinedAggregation
                and self.pre_window is not None
                and self.named_failure is None
                and bool(self.attempts)
                and any(
                    type(item) is ProjectNonConcreteWindowComputation
                    for item in self.attempts
                )
            )
        if not valid:
            raise ValueError("Window stage terminal reason must match its evidence.")


type ProjectJoinedWindowStageResult = (
    ProjectConcreteJoinedWindowStage | ProjectNonConcreteJoinedWindowStage
)


def build_project_joined_window_stage(
    aggregation_set: ProjectJoinedAggregationSet,
    input_aggregation: ProjectJoinedAggregationResult,
) -> ProjectJoinedWindowStageResult:
    """Build one exact Slice-10 result without partial downstream authority."""

    if type(aggregation_set) is not ProjectJoinedAggregationSet or not any(
        input_aggregation is item for item in aggregation_set.results
    ):
        raise ValueError("Joined windows require exact Slice-9 membership.")
    if type(input_aggregation) is ProjectNonConcreteJoinedAggregation:
        return ProjectNonConcreteJoinedWindowStage(
            aggregation_set=aggregation_set,
            input_aggregation=input_aggregation,
            reason=(
                ProjectJoinedWindowStageNonConcreteReason.UPSTREAM_AGGREGATION_NON_CONCRETE
            ),
        )
    if type(input_aggregation) is not ProjectConcreteJoinedAggregation:
        raise TypeError("Joined windows require one closed Slice-9 variant.")

    definition = _definition(input_aggregation)
    pre_window = build_project_joined_window_input_namespace(input_aggregation)
    named = resolve_named_window_namespace_for_query_block(
        definition,
        query_block=_query_block(input_aggregation),
    )
    if type(named) is NamedWindowResolutionFailure:
        return ProjectNonConcreteJoinedWindowStage(
            aggregation_set=aggregation_set,
            input_aggregation=input_aggregation,
            reason=(
                ProjectJoinedWindowStageNonConcreteReason.NAMED_NAMESPACE_NON_CONCRETE
            ),
            pre_window=pre_window,
            named_failure=named,
            diagnostics=named_window_resolution_diagnostics(named),
        )
    assert type(named) is ResolvedNamedWindowNamespace

    sites = tuple(
        ProjectWindowComputationSite(
            kind=ProjectWindowComputationSiteKind.SELECTED_OUTPUT,
            root=input_aggregation,
            expression=cast(WindowExpr, item.expression),
            item=item,
            selected_output_ordinal=ordinal,
            occurrence=WindowOccurrenceIdentity(
                source_id=named.query_block.source_id,
                relation_name=definition.name,
                selected_output_ordinal=ordinal,
                span=item.expression.span,
            ),
        )
        for ordinal, item in enumerate(definition.select_items)
        if type(item.expression) is WindowExpr
    )
    attempts = tuple(_analyze_site(site, pre_window, named) for site in sites)
    diagnostics = tuple(
        diagnostic for attempt in attempts for diagnostic in attempt.diagnostics
    )
    if any(
        type(attempt) is ProjectNonConcreteWindowComputation for attempt in attempts
    ):
        return ProjectNonConcreteJoinedWindowStage(
            aggregation_set=aggregation_set,
            input_aggregation=input_aggregation,
            reason=(
                ProjectJoinedWindowStageNonConcreteReason.SELECTED_COMPUTATION_NON_CONCRETE
            ),
            pre_window=pre_window,
            attempts=attempts,
            diagnostics=diagnostics,
        )
    computations = cast(tuple[ProjectConcreteWindowComputation, ...], attempts)
    selected_results = tuple(
        ProjectSelectedWindowResultBinding(computation=computation)
        for computation in computations
    )
    post_window = ProjectJoinedPostWindowNamespace(
        pre_window=pre_window,
        selected_results=selected_results,
    )
    return ProjectConcreteJoinedWindowStage(
        aggregation_set=aggregation_set,
        input_aggregation=input_aggregation,
        kind=(
            ProjectJoinedWindowStageKind.WINDOW_EVALUATION
            if computations
            else ProjectJoinedWindowStageKind.ABSENT
        ),
        named_namespace=named,
        pre_window=pre_window,
        computations=computations,
        selected_results=selected_results,
        post_window=post_window,
        preservation=ProjectJoinedWindowPreservationWitness(
            aggregation=input_aggregation,
        ),
        diagnostics=diagnostics,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedWindowStageSet:
    """Canonical Slice-9-order Slice-10 results."""

    aggregation_set: ProjectJoinedAggregationSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    results: tuple[ProjectJoinedWindowStageResult, ...]

    def __post_init__(self) -> None:
        if type(self.aggregation_set) is not ProjectJoinedAggregationSet or (
            len(self.results) != len(self.aggregation_set.results)
            or any(
                type(result)
                not in {
                    ProjectConcreteJoinedWindowStage,
                    ProjectNonConcreteJoinedWindowStage,
                }
                or result.aggregation_set is not self.aggregation_set
                or result.input_aggregation is not input_aggregation
                for result, input_aggregation in zip(
                    self.results,
                    self.aggregation_set.results,
                    strict=True,
                )
            )
        ):
            raise ValueError("Window stage set must retain canonical Slice-9 order.")


def build_project_joined_window_stages(
    aggregation_set: ProjectJoinedAggregationSet,
) -> ProjectJoinedWindowStageSet:
    """Build one closed Slice-10 result per exact Slice-9 result."""

    if type(aggregation_set) is not ProjectJoinedAggregationSet:
        raise TypeError("Window stage set requires exact Slice-9 authority.")
    return ProjectJoinedWindowStageSet(
        aggregation_set=aggregation_set,
        results=tuple(
            build_project_joined_window_stage(aggregation_set, result)
            for result in aggregation_set.results
        ),
    )


class ProjectHiddenWindowComputationNonConcreteReason(StrEnum):
    """Requests that cannot form a hidden-inline computation site."""

    NAMED_USE_FORBIDDEN = "named_use_forbidden"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteHiddenWindowComputation:
    """One rejected hidden request with no fake selected occurrence."""

    stage: ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: WindowExpr = field(repr=False, compare=False, hash=False)
    reason: ProjectHiddenWindowComputationNonConcreteReason
    site: None = field(init=False, default=None)
    occurrence: None = field(init=False, default=None)
    result_binding: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.stage) is not ProjectConcreteJoinedWindowStage
            or type(self.expression) is not WindowExpr
            or self.expression.use_kind is WindowUseKind.INLINE
            or self.reason
            is not ProjectHiddenWindowComputationNonConcreteReason.NAMED_USE_FORBIDDEN
        ):
            raise ValueError("Hidden named-window rejection must retain exact input.")


type ProjectHiddenWindowComputationResult = (
    ProjectConcreteWindowComputation
    | ProjectNonConcreteWindowComputation
    | ProjectNonConcreteHiddenWindowComputation
)


def analyze_hidden_project_window_computation(
    stage: ProjectConcreteJoinedWindowStage,
    expression: WindowExpr,
) -> ProjectHiddenWindowComputationResult:
    """Analyze one caller-supplied hidden inline use without mutating the stage."""

    if type(stage) is not ProjectConcreteJoinedWindowStage:
        raise TypeError("Hidden window computation requires a concrete Slice-10 stage.")
    if type(expression) is not WindowExpr:
        raise TypeError("Hidden window computation requires an exact WindowExpr.")
    if expression.use_kind is not WindowUseKind.INLINE:
        return ProjectNonConcreteHiddenWindowComputation(
            stage=stage,
            expression=expression,
            reason=(
                ProjectHiddenWindowComputationNonConcreteReason.NAMED_USE_FORBIDDEN
            ),
        )
    site = ProjectWindowComputationSite(
        kind=ProjectWindowComputationSiteKind.HIDDEN_INLINE,
        root=stage,
        expression=expression,
    )
    return _analyze_site(site, stage.pre_window, stage.named_namespace)
