"""Private Phase-63 completed Project semantic result boundary."""

from __future__ import annotations

from pietto._project.project_set_operations import ProjectSetFailure
from pietto._project.module_relation_resolution import ProjectResolvedSetOperand

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project import (
    aggregate_grouped_clause_facts,
    let_scope_facts,
    module_semantic_fact_preservation,
    project_final_outputs,
    project_grain,
    project_ir_joins,
    project_joined_aggregation,
    project_joined_qualify,
    project_joined_row_filter,
    project_joined_row_semantics,
    project_joined_windows,
    project_multifact,
    project_relationship_conditions,
    project_relationship_match_guarantees,
    project_relationship_paths,
    project_relationship_uses,
    project_relationships,
    project_row_keys,
    project_scalar_namespaces,
    project_value_fds,
)
from pietto._project.model import ProjectSemanticResult
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_completion import (
    ProjectCompletion,
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
    build_project_completion,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedSetOutput,
    completed_set_admission_diagnostics,
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletion,
    ProjectEffectiveOutputCompletionEntry,
    ProjectEffectiveOutputCompletionTerminal,
    build_project_effective_output_completion,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_relational_properties import (
    build_project_ir_relational_property_stage,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)
from pietto._project.project_join_conditions import (
    ProjectJoinCondition,
    ProjectJoinConditionCompletion,
    ProjectJoinConditionSet,
    build_project_join_conditions,
)
from pietto._project.project_current_join_inputs import ProjectCurrentJoinInputFailure
from pietto._project.project_joined_qualify import build_project_joined_tail
from pietto._project.project_joined_row_filter import (
    build_project_joined_row_filters,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
    verify_project_phase62,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.expressions import type_source_connector_arguments
from pietto.semantic.source_connectors import check_source_connectors
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchSet,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedOrderFacts:
    """ORDER preparation for one exact existing or completed result boundary."""

    entry: ProjectExistingEffectiveOutput | ProjectCompletedEffectiveOutput
    ordering: project_final_outputs.ProjectRelationOrderingResult


def _completed_order_facts(
    effective: ProjectEffectiveOutputCompletion,
) -> tuple[ProjectCompletedOrderFacts, ...]:
    result = []
    for entry in effective.entries:
        definition = entry.owner.definition
        if (
            not isinstance(definition, (TableDef, QueryDef))
            or definition.order_by_clause is None
        ):
            continue
        if isinstance(entry, ProjectCompletedEffectiveOutput):
            ordering = entry.ordering
        elif isinstance(entry, ProjectExistingEffectiveOutput):
            facts = entry.fragment.semantic_facts
            if (
                facts.input_state is None
                or facts.input_state.schema is None
                or facts.let_scope_facts is None
            ):
                continue
            # Existing-entry ORDER has no earlier typed analysis carrier. Construct
            # it here once with the same semantic ORDER resolver and original input;
            # keep its outcome separate from the legacy completion's diagnostics.
            ordering = project_final_outputs._no_join_relation_ordering(
                owner=entry.owner,
                input_schema=facts.input_state.schema,
                let_scope=facts.let_scope_facts,
                mode=project_joined_aggregation._mode(definition),
                clause_dependencies=facts.clause_dependencies,
                window_outputs=facts.window_outputs,
            )
        else:
            continue
        result.append(ProjectCompletedOrderFacts(entry=entry, ordering=ordering))
    return tuple(result)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedRowReferenceFacts:
    """References retained once in the effective replay's actual environment."""

    entry: ProjectCompletedEffectiveOutput
    let_bindings: tuple[
        module_semantic_fact_preservation.ProjectModuleLetBindingFact, ...
    ]
    selections: tuple[
        tuple[
            module_semantic_fact_preservation.ProjectModuleExpressionReferenceFact, ...
        ],
        ...,
    ]
    where: tuple[
        module_semantic_fact_preservation.ProjectModuleExpressionReferenceFact, ...
    ]
    groups: tuple[
        tuple[
            module_semantic_fact_preservation.ProjectModuleExpressionReferenceFact, ...
        ],
        ...,
    ]


def _completed_row_references(
    effective: ProjectEffectiveOutputCompletion,
) -> tuple[ProjectCompletedRowReferenceFacts, ...]:
    facts = module_semantic_fact_preservation
    result: list[ProjectCompletedRowReferenceFacts] = []
    for entry in effective.entries:
        if not isinstance(entry, ProjectCompletedEffectiveOutput) or not isinstance(
            entry.root, project_final_outputs.ProjectConcreteNoJoinReplay
        ):
            continue
        root = entry.root
        definition = root.owner.definition
        assert isinstance(definition, (TableDef, QueryDef))

        qualifier = definition.from_clause.source_name

        def references(expression, role, ordinal):
            return facts._expression_reference_facts(
                owner=root.owner,
                role=role,
                container_ordinal=ordinal,
                expression=expression,
                relation_qualifier=qualifier,
                input_schema=root.input_schema,
                input_status=facts.ProjectModuleCandidateBucketStatus.CONCRETE,
                let_scope=root.let_scope,
                let_candidates=root.let_scope.bindings,
                selected_items=(),
            )

        result.append(
            ProjectCompletedRowReferenceFacts(
                entry=entry,
                let_bindings=facts._let_binding_facts(
                    owner=root.owner,
                    definition=definition,
                    input_schema=root.input_schema,
                    input_status=facts.ProjectModuleCandidateBucketStatus.CONCRETE,
                    let_scope=root.let_scope,
                ),
                selections=tuple(
                    references(
                        item.expression,
                        facts.ProjectModuleFactOccurrenceRole.SELECT_VALUE,
                        i,
                    )
                    for i, item in enumerate(definition.select_items)
                ),
                groups=tuple(
                    references(
                        item.key, facts.ProjectModuleFactOccurrenceRole.GROUP_KEY, i
                    )
                    for i, item in enumerate(
                        ()
                        if definition.group_by_clause is None
                        else definition.group_by_clause.items
                    )
                ),
                where=()
                if definition.where_clause is None
                else references(
                    definition.where_clause.expression,
                    facts.ProjectModuleWhereReferenceRole.WHERE_VALUE,
                    0,
                ),
            )
        )
    return tuple(result)


class ProjectCompletedSemanticNonConcreteReason(StrEnum):
    """Closed direct-builder mode terminals."""

    LEGACY_FLAT_MODE = "legacy_flat_mode"
    PACKAGE_ROOT_MODE = "package_root_mode"


def _source_connector_diagnostics(
    semantic_result: ProjectSemanticResult,
) -> tuple[Diagnostic, ...]:
    """Validate every retained defining script once, before publishing its root."""
    catalogs = semantic_result.module_catalogs
    modules = semantic_result.modules
    if (
        catalogs is None
        or len(catalogs.catalogs) != len(modules)
        or any(
            catalog.module is not module
            for catalog, module in zip(catalogs.catalogs, modules, strict=True)
        )
    ):
        raise ValueError("Completed source validation requires exact module evidence.")
    diagnostics: list[Diagnostic] = []
    for module in modules:
        if module.parsed_input is None:
            raise ValueError(
                "Completed source validation requires every module script."
            )
        script = module.parsed_input.script
        value_types, expression_diagnostics = type_source_connector_arguments(script)
        diagnostics.extend(expression_diagnostics)
        diagnostics.extend(check_source_connectors(script, value_types))
    return tuple(diagnostics)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteCompletedSemanticResult:
    """One typed non-positive compilation-mode result with no partial chain."""

    semantic_result: ProjectSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectCompletedSemanticNonConcreteReason
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    verification: None = field(init=False, default=None)
    completion: None = field(init=False, default=None)
    effective_outputs: None = field(init=False, default=None)
    ok: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        if (
            type(self.semantic_result) is not ProjectSemanticResult
            or type(self.reason) is not ProjectCompletedSemanticNonConcreteReason
        ):
            raise TypeError("Completed Project terminal requires exact typed roots.")
        expected = {
            ProjectCompilationMode.LEGACY_FLAT: (
                ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE
            ),
            ProjectCompilationMode.PACKAGE_ROOT: (
                ProjectCompletedSemanticNonConcreteReason.PACKAGE_ROOT_MODE
            ),
        }.get(self.semantic_result.compilation_mode)
        if expected is None or self.reason is not expected:
            raise ValueError("Completed Project terminal must retain its exact mode.")
        object.__setattr__(self, "diagnostics", self.semantic_result.diagnostics)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _ProjectCompletedSemanticRoots:
    """Build and retain the exact Phase-61/62 through Slice-12 chain."""

    semantic_result: ProjectSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    row_references: tuple[ProjectCompletedRowReferenceFacts, ...] = field(
        init=False, repr=False
    )
    order_facts: tuple[ProjectCompletedOrderFacts, ...] = field(init=False, repr=False)
    verification: ProjectPhase62VerificationResult = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    completion: ProjectCompletion = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    effective_outputs: ProjectEffectiveOutputCompletion = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    join_conditions: ProjectJoinConditionSet | ProjectJoinConditionCompletion = field(
        init=False, repr=False
    )
    diagnostics: tuple[Diagnostic, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.semantic_result) is not ProjectSemanticResult or (
            self.semantic_result.compilation_mode
            is not ProjectCompilationMode.EXPLICIT_MODULES
        ):
            raise TypeError("Completed Project semantics require exact concrete roots.")
        source_diagnostics = _source_connector_diagnostics(self.semantic_result)
        verification = _build_phase62_verification(self.semantic_result)
        join_conditions = build_project_join_conditions(
            verification.root.join_regions.uses
        )
        completion = build_project_completion(verification)
        filters = build_project_joined_row_filters(completion)
        qualifies = build_project_joined_tail(filters)
        effective_outputs = build_project_effective_output_completion(
            completion,
            qualifies,
            join_conditions=join_conditions,
        )
        object.__setattr__(self, "verification", verification)
        object.__setattr__(self, "completion", completion)
        object.__setattr__(self, "effective_outputs", effective_outputs)
        object.__setattr__(
            self, "row_references", _completed_row_references(effective_outputs)
        )
        object.__setattr__(
            self, "order_facts", _completed_order_facts(effective_outputs)
        )
        operative = effective_outputs.operative_conditions
        if operative is None:
            raise ValueError(
                "Completed roots lost their operative condition authority."
            )
        object.__setattr__(self, "join_conditions", operative)
        object.__setattr__(
            self,
            "diagnostics",
            (
                *_final_diagnostics(
                    self.semantic_result,
                    effective_outputs,
                    retired=(
                        *(
                            diagnostic
                            for admission in effective_outputs.join_admissions
                            for diagnostic in admission.diagnostics
                        ),
                        *completed_set_admission_diagnostics(effective_outputs),
                    ),
                ),
                *operative.diagnostics,
                *source_diagnostics,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteCompletedSemanticResult:
    """One exact completed Project semantic chain and final diagnostic boundary."""

    roots: _ProjectCompletedSemanticRoots = field(
        repr=False,
        compare=False,
        hash=False,
    )
    single_match_requests: tuple[ProjectSingleMatchRequest, ...] = field(
        default=(), repr=False
    )
    single_matches: ProjectSingleMatchSet = field(init=False, repr=False)
    semantic_result: ProjectSemanticResult = field(init=False, repr=False)
    verification: ProjectPhase62VerificationResult = field(init=False, repr=False)
    completion: ProjectCompletion = field(init=False, repr=False)
    effective_outputs: ProjectEffectiveOutputCompletion = field(
        init=False,
        repr=False,
    )
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    ok: bool = field(init=False)

    def __post_init__(self) -> None:
        if type(self.roots) is not _ProjectCompletedSemanticRoots:
            raise TypeError("Completed Project result requires one exact root chain.")
        semantic_result = self.roots.semantic_result
        verification = self.roots.verification
        completion = self.roots.completion
        effective_outputs = self.roots.effective_outputs
        diagnostics = self.roots.diagnostics
        single_matches = ProjectSingleMatchSet(
            root=effective_outputs, requests=self.single_match_requests
        )
        retained_ids = {id(diagnostic) for diagnostic in diagnostics}
        diagnostics = (
            *diagnostics,
            *(
                diagnostic
                for diagnostic in single_matches.diagnostics
                if id(diagnostic) not in retained_ids
            ),
        )
        object.__setattr__(self, "single_matches", single_matches)
        entries_are_concrete = all(
            type(entry)
            in {
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
            }
            for entry in effective_outputs.entries
        )
        object.__setattr__(self, "semantic_result", semantic_result)
        object.__setattr__(self, "verification", verification)
        object.__setattr__(self, "completion", completion)
        object.__setattr__(self, "effective_outputs", effective_outputs)
        object.__setattr__(self, "diagnostics", diagnostics)
        object.__setattr__(
            self,
            "ok",
            entries_are_concrete
            and not any(
                diagnostic.severity is Severity.ERROR for diagnostic in diagnostics
            ),
        )


type ProjectCompletedSemanticResult = (
    ProjectConcreteCompletedSemanticResult | ProjectNonConcreteCompletedSemanticResult
)


def _entry_error_diagnostics(
    entry: ProjectEffectiveOutputCompletionEntry,
) -> tuple[Diagnostic, ...]:
    retained: list[Diagnostic] = []
    retained_ids: set[int] = set()
    for diagnostic in _diagnostics_from_carrier(entry):
        if diagnostic.severity is Severity.ERROR and id(diagnostic) not in retained_ids:
            retained.append(diagnostic)
            retained_ids.add(id(diagnostic))
    return tuple(retained)


def _diagnostics_from_carrier(carrier: object | None) -> tuple[Diagnostic, ...]:
    """Project exact diagnostics from the closed terminal authority graph."""

    if carrier is None:
        return ()
    if isinstance(carrier, ProjectSetFailure):
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.scope.base_entry),
            *_diagnostics_from_carrier(carrier.blockers),
        )
    if isinstance(carrier, ProjectResolvedSetOperand):
        return carrier.diagnostics
    if type(carrier) is ProjectCurrentJoinInputFailure:
        return _diagnostics_from_carrier(carrier.blockers)
    if type(carrier) is ProjectJoinCondition:
        return carrier.diagnostics
    if type(carrier) is tuple:
        return tuple(
            diagnostic
            for item in carrier
            for diagnostic in _diagnostics_from_carrier(item)
        )
    if type(carrier) is ProjectEffectiveOutputTerminal:
        cycle_diagnostics = (
            ()
            if carrier.cycle_blocker is None
            else tuple(
                diagnostic
                for cycle in carrier.cycle_blocker.cycles
                for diagnostic in cycle.diagnostics
            )
        )
        return (
            *cycle_diagnostics,
            *_diagnostics_from_carrier(carrier.fragment.semantic_facts),
            *_diagnostics_from_carrier(carrier.joined_completion),
            *_diagnostics_from_carrier(carrier.pending_entries),
        )
    if type(carrier) is ProjectEffectiveOutputCompletionTerminal:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.blocker),
            *_diagnostics_from_carrier(carrier.joined_qualify),
            *_diagnostics_from_carrier(carrier.replay_root),
            *_diagnostics_from_carrier(carrier.upstream_entry),
        )
    if type(carrier) is project_final_outputs.ProjectNoJoinReplayRoot:
        return _diagnostics_from_carrier(carrier.blocker)
    if type(carrier) is (
        module_semantic_fact_preservation.ProjectModuleRelationSemanticFacts
    ):
        return (
            *carrier.helper_diagnostics,
            *_ordinary_row_diagnostics(carrier),
            *_diagnostics_from_carrier(carrier.window_outputs),
            *_diagnostics_from_carrier(carrier.aggregate_grouped_clause_readiness),
        )
    if type(carrier) is (
        module_semantic_fact_preservation.ProjectModuleWindowOutputFact
    ):
        return carrier.diagnostics

    if type(carrier) is project_joined_row_semantics.ProjectConcreteJoinedRowSemantics:
        return _diagnostics_from_carrier(carrier.namespaces)
    if (
        type(carrier)
        is project_joined_row_semantics.ProjectNonConcreteJoinedRowSemantics
    ):
        return _diagnostics_from_carrier(carrier.namespaces)
    if type(carrier) is project_scalar_namespaces.ProjectConcreteJoinedLetNamespaces:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.values),
        )
    if type(carrier) is project_scalar_namespaces.ProjectNonConcreteJoinedLetNamespaces:
        return carrier.diagnostics
    if type(carrier) is project_scalar_namespaces.ProjectJoinedLetValue:
        return carrier.diagnostics
    if type(carrier) is (
        project_scalar_namespaces.ProjectConcreteJoinedNamespaceExpression
    ):
        return carrier.diagnostics
    if type(carrier) is (
        project_scalar_namespaces.ProjectNonConcreteJoinedNamespaceExpression
    ):
        return carrier.diagnostics

    if type(carrier) is project_joined_row_filter.ProjectConcreteJoinedRowFilter:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.expression_analysis),
        )
    if type(carrier) is project_joined_row_filter.ProjectNonConcreteJoinedRowFilter:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.expression_analysis),
        )
    if type(carrier) is project_joined_aggregation.ProjectConcreteJoinedAggregation:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.input_filter),
            *_diagnostics_from_carrier(carrier.satisfying),
        )
    if type(carrier) is project_joined_aggregation.ProjectNonConcreteJoinedAggregation:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.input_filter),
            *_diagnostics_from_carrier(carrier.group_key_results),
            *_diagnostics_from_carrier(carrier.aggregate_results),
            *_diagnostics_from_carrier(carrier.selected_output_issues),
            *_diagnostics_from_carrier(carrier.satisfying),
        )
    if type(carrier) is project_joined_aggregation.ProjectJoinedGroupKeyIssue:
        return carrier.diagnostics
    if type(carrier) is project_joined_aggregation.ProjectJoinedAggregateIssue:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.argument_analysis),
        )
    if type(carrier) is project_joined_aggregation.ProjectJoinedSelectedOutputIssue:
        return carrier.diagnostics
    if type(carrier) is project_joined_aggregation.ProjectJoinedSatisfyingAnalysis:
        return carrier.diagnostics

    if type(carrier) is project_joined_windows.ProjectConcreteJoinedWindowStage:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.input_aggregation),
            *_diagnostics_from_carrier(carrier.computations),
        )
    if type(carrier) is project_joined_windows.ProjectNonConcreteJoinedWindowStage:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.input_aggregation),
            *_diagnostics_from_carrier(carrier.attempts),
        )
    if type(carrier) is project_joined_windows.ProjectConcreteWindowComputation:
        return carrier.diagnostics
    if type(carrier) is project_joined_windows.ProjectNonConcreteWindowComputation:
        return carrier.diagnostics
    if (
        type(carrier)
        is project_joined_windows.ProjectNonConcreteHiddenWindowComputation
    ):
        return ()

    if type(carrier) is project_joined_qualify.ProjectConcreteJoinedQualify:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.window_stage),
            *_diagnostics_from_carrier(carrier.hidden_computations),
        )
    if type(carrier) is project_joined_qualify.ProjectNonConcreteJoinedQualify:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.window_stage),
            *_diagnostics_from_carrier(carrier.hidden_attempts),
        )
    if type(carrier) is project_joined_qualify._ProjectQualifyPredicateAnalysis:
        return carrier.diagnostics

    if type(carrier) is project_final_outputs.ProjectNoJoinScalarExpression:
        return carrier.diagnostics
    if type(carrier) is project_final_outputs.ProjectConcreteNoJoinWhere:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.expression_analysis),
        )
    if type(carrier) is project_final_outputs.ProjectNoJoinHiddenWindowComputation:
        return carrier.diagnostics
    if type(carrier) is project_final_outputs.ProjectNoJoinQualify:
        return (
            *_diagnostics_from_carrier(carrier.predicate),
            *_diagnostics_from_carrier(carrier.hidden_attempts),
        )
    if type(carrier) is project_final_outputs.ProjectNonConcreteRelationOrdering:
        return (
            *carrier.diagnostics,
            *_diagnostics_from_carrier(carrier.blocker),
        )
    if type(carrier) is project_final_outputs.ProjectNonConcreteRelationLimit:
        return carrier.diagnostics
    if type(carrier) is let_scope_facts.ProjectRelationLetScopeFacts:
        return carrier.diagnostics
    if (
        type(carrier)
        is aggregate_grouped_clause_facts.ProjectAggregateGroupedClauseReadiness
    ):
        return ()
    return ()


def _fallback_diagnostic(
    entry: ProjectEffectiveOutputCompletionEntry,
) -> Diagnostic:
    if type(entry) not in {
        ProjectEffectiveOutputTerminal,
        ProjectEffectiveOutputCompletionTerminal,
    }:
        raise TypeError("Project completion fallback requires an exact terminal.")
    definition = entry.owner.definition
    if type(definition) not in {SourceDef, TableDef, QueryDef}:
        raise TypeError("Project completion diagnostic requires a relation definition.")
    span = definition.span
    return Diagnostic(
        code="PIE-S2333",
        severity=Severity.ERROR,
        message=(
            "Project relation semantic completion is unavailable: "
            f"{entry.owner.identity.declared_name}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _ordinary_row_diagnostics(
    facts: module_semantic_fact_preservation.ProjectModuleRelationSemanticFacts,
) -> tuple[Diagnostic, ...]:
    return (
        *(() if facts.let_scope_facts is None else facts.let_scope_facts.diagnostics),
        *(() if facts.where_fact is None else facts.where_fact.diagnostics),
        *(
            diagnostic
            for selected in facts.select_expressions
            for diagnostic in selected.diagnostics
        ),
    )


def _final_diagnostics(
    semantic_result: ProjectSemanticResult,
    effective_outputs: ProjectEffectiveOutputCompletion,
    *,
    retired: tuple[Diagnostic, ...] = (),
) -> tuple[Diagnostic, ...]:
    retired_ids = {id(diagnostic) for diagnostic in retired}
    retained = [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if id(diagnostic) not in retired_ids
    ]
    retained_ids = {id(diagnostic) for diagnostic in retained}
    for entry in effective_outputs.entries:
        if type(entry) is ProjectExistingEffectiveOutput:
            for diagnostic in _ordinary_row_diagnostics(entry.fragment.semantic_facts):
                if id(diagnostic) not in retained_ids:
                    retained.append(diagnostic)
                    retained_ids.add(id(diagnostic))
            continue
        if type(entry) in {
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
        }:
            continue
        if type(entry) not in {
            ProjectEffectiveOutputTerminal,
            ProjectEffectiveOutputCompletionTerminal,
        }:
            raise TypeError("Final diagnostics require exact effective entries.")
        errors = tuple(
            diagnostic
            for diagnostic in _entry_error_diagnostics(entry)
            if id(diagnostic) not in retired_ids
        )
        if not errors:
            errors = (_fallback_diagnostic(entry),)
        for diagnostic in errors:
            if id(diagnostic) in retained_ids:
                continue
            retained.append(diagnostic)
            retained_ids.add(id(diagnostic))
    return tuple(retained)


def _build_phase62_verification(
    semantic_result: ProjectSemanticResult,
) -> ProjectPhase62VerificationResult:
    semantic_facts = semantic_result.module_semantic_facts
    attribution = semantic_result.module_attribution_facts
    if semantic_facts is None or attribution is None:
        raise ValueError(
            "Completed Project semantics require exact explicit-module sidecars."
        )
    row_keys = project_row_keys.build_project_row_keys(semantic_result)
    value_fds = project_value_fds.build_project_value_fds(row_keys)
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    base_verification = verify_project_ir_stage(evaluation)
    base_relational = build_project_ir_relational_property_stage(
        origins,
        build_project_ir_analysis_bundle(base_verification),
    )
    relationships = project_relationships.build_project_relationships(semantic_result)
    conditions = project_relationship_conditions.build_project_relationship_conditions(
        relationships
    )
    guarantees = project_relationship_match_guarantees.build_project_relationship_match_guarantees(
        conditions,
        base_relational,
    )
    uses = project_relationship_uses.build_project_relationship_uses(
        relationships,
        project_relationship_paths.build_project_relationship_join_shape_index(
            guarantees
        ),
    )
    join_regions = project_ir_joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_relational,
        uses=uses,
        allocation=plan.ending_allocation,
    )
    analysis = project_multifact.build_project_multifact_analysis(
        evaluation=evaluation,
        base_relational=base_relational,
        join_regions=join_regions,
    )
    return verify_project_phase62(analysis)


def build_project_completed_semantic_result(
    semantic_result: ProjectSemanticResult,
) -> ProjectCompletedSemanticResult:
    """Complete explicit-module Project semantics through existing private stages."""

    if type(semantic_result) is not ProjectSemanticResult:
        raise TypeError("Completed Project semantics require an exact semantic result.")
    if semantic_result.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
        reason = {
            ProjectCompilationMode.LEGACY_FLAT: (
                ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE
            ),
            ProjectCompilationMode.PACKAGE_ROOT: (
                ProjectCompletedSemanticNonConcreteReason.PACKAGE_ROOT_MODE
            ),
        }[semantic_result.compilation_mode]
        return ProjectNonConcreteCompletedSemanticResult(
            semantic_result=semantic_result,
            reason=reason,
        )

    return ProjectConcreteCompletedSemanticResult(
        roots=_ProjectCompletedSemanticRoots(
            semantic_result=semantic_result,
        )
    )


def with_project_single_match_requests(
    completed: ProjectConcreteCompletedSemanticResult,
    requests: tuple[ProjectSingleMatchRequest, ...],
) -> ProjectConcreteCompletedSemanticResult:
    """Check explicit private requests against the same parsed/completed roots."""
    if type(completed) is not ProjectConcreteCompletedSemanticResult:
        raise TypeError(
            "Single-match requests require an explicit-module completed result."
        )
    return ProjectConcreteCompletedSemanticResult(
        roots=completed.roots,
        single_match_requests=requests,
    )
