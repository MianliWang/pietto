"""Private Phase-63 completed Project semantic result boundary."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto._project.model import CompiledProjectInput
    from pietto._project.module_attribution import CompiledDeclarationOccurrence
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_sql_emission_rows import Realization
    from pietto.semantic.model import ValueType


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


@dataclass(frozen=True, slots=True, eq=False)
class CompiledScalarFact:
    """A fresh original-law result at one resolved compiled expression address."""

    root: CompiledProjectInput = field(repr=False)
    address: Address
    value_type: ValueType
    value: object = field(default=None, repr=False)
    operator: tuple[str, str] | None = None
    operands: tuple[Address, ...] = field(default=(), repr=False)
    realization: Realization | None = field(kw_only=True, repr=False)
    origin: str = field(kw_only=True, default="unsupported")
    parameters: tuple[int, int] | None = field(kw_only=True, default=None)
    introduction: Address | None = field(kw_only=True, default=None)
    nulling: tuple[Address, ...] = field(kw_only=True, default=())

    def require_realization(self) -> Realization:
        from pietto._project.project_sql_emission_rows import Realization
        from pietto._project.project_compiled_schema import CompiledError

        if type(self.realization) is not Realization:
            raise CompiledError("COMPILED_LOGICAL_ONLY_FACT")
        return self.realization


@dataclass(frozen=True, slots=True, eq=False)
class CompiledCompletedSemanticResult:
    """A compiled-input branch, never a fabricated source semantic result."""

    root: CompiledProjectInput = field(repr=False)
    values: tuple = field(repr=False)
    declarations: tuple[CompiledDeclarationOccurrence, ...] = field(repr=False)
    facts: tuple[CompiledScalarFact, ...] = field(repr=False)
    retention: tuple = field(repr=False)
    single_match_requests: tuple = field(default=(), repr=False)


def derive_compiled_semantics(root, values):
    """Derive resolved scalar inputs without calling any source elaborator."""
    import json
    from pietto._project.model import CompiledProjectInput
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_sql_emission_parameters import literal_representation
    from pietto._project.module_attribution import compiled_declarations
    from pietto._project.project_compiled_schema import Address, CompiledError, Scalar
    from pietto._project.project_sql_emission_parameters import value_valid
    from pietto.semantic.expressions import (
        resolved_literal_value_type,
        resolved_unary_value_type,
        resolved_binary_value_type,
    )
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
    )

    if type(root) is not CompiledProjectInput or type(values) is not tuple:
        raise CompiledError("COMPILED_BINDING_INPUT")
    root.verify()
    records = root.records
    from pietto._project.project_compiled_schema import selected_records

    executable = selected_records(records, records[root.description.query])
    slots = tuple(r for r in records.values() if r.address.kind == "slot")
    family = records[Address("target", 0)].get("family")
    if len(values) != len(slots):
        raise CompiledError("COMPILED_BINDING_SLOTS")
    replacements = {}
    for slot, value in zip(slots, values, strict=True):
        if not value_valid(slot.get("tag"), value, family):
            raise CompiledError("COMPILED_BINDING_VALUE")
        replacements[slot.get("literal")] = value
    facts, active = {}, set()

    def declared(value):
        if (
            type(value) is not tuple
            or len(value) != 2
            or value[0]
            not in ("Int", "Bool", "Float", "Text", "Decimal", "Timestamp", "UUID")
            or value[1] not in ("non_null", "nullable", "unknown")
        ):
            raise CompiledError("COMPILED_LOGICAL_TYPE")
        return ValueType(
            ResolvedType(value[0], TypeKind.BUILTIN),
            EffectiveNullability(value[1]),
        )

    def dependencies(record) -> tuple[Address, ...]:
        kind, get = record.address.kind, record.get
        if kind == "operation":
            return get("operands")
        if kind == "aggregate_value":
            return get("arguments")
        if kind == "set_value":
            return get("inputs")
        if kind == "join_value":
            join = records[get("owner")]
            return (
                get("input"),
                *(
                    a
                    for e in join.get("equalities")
                    for a in (records[e].get("left"), records[e].get("right"))
                ),
                *(
                    (join.get("predicate"),)
                    if join.get("predicate") is not None
                    else ()
                ),
            )
        if kind == "window_value":
            spec = records[get("specification")]
            return (
                *get("inputs"),
                *(a for _, a in get("arguments") if a.kind != "null_literal"),
                *spec.get("partition"),
                *(a for a, _, _ in spec.get("ordering")),
            )
        if kind == "port":
            return (get("source"),)
        if kind == "read":
            return (get("port"),)
        return ()

    scalar_kinds = {
        "field",
        "port",
        "read",
        "literal",
        "operation",
        "aggregate_value",
        "window_value",
        "set_value",
        "join_value",
    }
    for address in records:
        if address.kind not in scalar_kinds:
            continue
        pending = [(address, False)]
        while pending:
            ref, returning = pending.pop()
            if ref in facts:
                continue
            record = records[ref]
            if not returning:
                if ref in active:
                    raise CompiledError("COMPILED_VALUE_CYCLE")
                active.add(ref)
                pending.append((ref, True))
                children = dependencies(record)
                if type(children) is not tuple or any(
                    type(child) is not Address
                    or child not in records
                    or child.kind not in scalar_kinds
                    for child in children
                ):
                    raise CompiledError("COMPILED_VALUE_DEPENDENCY")
                pending.extend((child, False) for child in reversed(children))
                continue
            active.remove(ref)
            kind, get = record.address.kind, record.get
            value, operator, operands = None, None, dependencies(record)
            physical_required = ref in executable
            origin = "unsupported"
            type_parameters = None
            introduction, nulling = None, ()
            if kind == "field":
                origin = "field"
                type_parameters = get("decimal")
                typed = declared(get("logical"))
                if physical_required:
                    described = json.loads(get("physical"))
                    realized = physical.Realization(
                        typed.resolved_type.name,
                        described["storage"],
                        described["nullable"],
                        described["domain"],
                    )
                else:
                    realized = None
            elif kind == "literal":
                origin = "literal"
                original = get("value")
                if type(original) is not Scalar:
                    raise CompiledError("COMPILED_LITERAL")
                value = replacements.get(ref, original.value)
                if not value_valid(original.tag, value, family):
                    raise CompiledError("COMPILED_BINDING_VALUE")
                typed = resolved_literal_value_type(value)
                if physical_required:
                    described = literal_representation(original.tag, value, family)
                    realized = physical.Realization(
                        original.tag,
                        described["storage"],
                        described["nullable"],
                        described["domain"],
                    )
                else:
                    realized = None
            elif kind == "aggregate_value":
                origin = "aggregate"
                from pietto.semantic.aggregates import (
                    semantic_aggregate_result_value_type,
                )
                from pietto._project import project_sql_emission_aggregation as grouping

                function = get("function")
                if function not in grouping.SPELLING or len(operands) > 1:
                    raise CompiledError("COMPILED_AGGREGATE_SIGNATURE")
                argument = None if not operands else facts[operands[0]]
                if (
                    physical_required
                    and argument is not None
                    and grouping.resolved_argument_problem(
                        function, argument.address.kind == "read", argument.realization
                    )
                    is not None
                ):
                    raise CompiledError("COMPILED_AGGREGATE_ARGUMENT")
                typed = semantic_aggregate_result_value_type(
                    function, None if argument is None else argument.value_type
                )
                if typed is None or typed != declared(get("logical")):
                    raise CompiledError("COMPILED_AGGREGATE_TYPE")
                if physical_required:
                    realized, problem = grouping.result_realization(
                        family,
                        function,
                        argument,
                        (
                            typed.resolved_type.name,
                            physical.NULLABILITY[typed.nullability],
                        ),
                    )
                    if realized is None or problem is not None:
                        raise CompiledError("COMPILED_AGGREGATE_DOMAIN")
                else:
                    realized = None
            elif kind == "join_value":
                from pietto._project.project_sql_plan_joins import (
                    compiled_join_rejections,
                )
                from pietto._project.project_sql_emission_joins import (
                    resolved_port_realization,
                )

                join = records[get("owner")]
                read = records[get("input")]
                incoming = facts[read.address]
                use = records[read.get("use")]
                rejected = (use.address, read.get("port")) in compiled_join_rejections(
                    records, join
                )
                from pietto._project.project_current_joins import (
                    resolved_join_field_nullability,
                )
                from pietto.ast_nodes import AuthoredJoinKind
                from pietto._project.model import ProjectRowFieldNullability

                preserve = (
                    use.get("ordinal") == 0 and use.get("producer").kind == "join"
                )
                introduction = incoming.introduction if preserve else use.address
                nulling = incoming.nulling if preserve else ()
                if join.get("kind") == "full" or (
                    join.get("kind"),
                    use.get("ordinal"),
                ) in (("left", 1), ("right", 0)):
                    nulling = (*nulling, join.address)
                nullable = EffectiveNullability(
                    resolved_join_field_nullability(
                        AuthoredJoinKind(join.get("kind")),
                        ProjectRowFieldNullability(
                            incoming.value_type.nullability.value
                        ),
                        bool(nulling),
                        rejected,
                    ).value
                )
                typed = ValueType(incoming.value_type.resolved_type, nullable)
                if typed != declared(get("logical")):
                    raise CompiledError("COMPILED_JOIN_NULLABILITY")
                origin, type_parameters = incoming.origin, incoming.parameters
                if physical_required:
                    realized, problem = resolved_port_realization(
                        typed.resolved_type.name,
                        physical.NULLABILITY[nullable],
                        incoming.realization,
                        outer=True,
                        proved=rejected,
                    )
                    if realized is None or problem is not None:
                        raise CompiledError("COMPILED_JOIN_DOMAIN")
                else:
                    realized = None
            elif kind == "set_value":
                from pietto._project.project_set_operations import (
                    resolved_set_nullability,
                )
                from pietto._project.project_row_equivalence import (
                    resolved_builtin_equivalence_reason,
                )
                from pietto._project import project_sql_emission_sets as setting
                from pietto._project.model import ProjectRowFieldNullability
                from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

                operation = records[get("owner")]
                inputs = tuple(facts[a] for a in operands)
                first = inputs[0]
                if any(
                    i.value_type.resolved_type != first.value_type.resolved_type
                    or i.parameters != first.parameters
                    for i in inputs
                ):
                    raise CompiledError("COMPILED_SET_TYPE")
                type_parameters = first.parameters
                set_kind, quantifier = (
                    SetOperationKind(operation.get("kind")),
                    SetOperationQuantifier(operation.get("quantifier")),
                )
                nullable = resolved_set_nullability(
                    set_kind,
                    tuple(
                        ProjectRowFieldNullability(i.value_type.nullability.value)
                        for i in inputs
                    ),
                )
                typed = ValueType(
                    first.value_type.resolved_type, EffectiveNullability(nullable.value)
                )
                if typed != declared(get("logical")):
                    raise CompiledError("COMPILED_SET_NULLABILITY")
                reasons = tuple(
                    resolved_builtin_equivalence_reason(i.value_type.resolved_type.name)
                    for i in inputs
                )
                if physical_required:
                    realized, problem = setting.resolved_column_realization(
                        set_kind,
                        quantifier,
                        physical.NULLABILITY[typed.nullability],
                        inputs,
                        reasons,
                    )
                    if realized is None or problem is not None:
                        raise CompiledError("COMPILED_SET_DOMAIN")
                else:
                    realized = None
            elif kind == "window_value":
                from pietto._project import project_sql_emission_windows as windowing
                from pietto._project.project_sql_plan_windows import (
                    resolved_result_type,
                )

                origin = "window"
                function = get("function")
                static = windowing.resolved_arguments(
                    function, get("arguments"), records, family
                )
                value_reads = tuple(
                    a for role, a in get("arguments") if role == "value"
                )
                argument = facts[value_reads[0]] if value_reads else None
                typed = resolved_result_type(
                    function, None if argument is None else argument.value_type, static
                )
                type_parameters = None if argument is None else argument.parameters
                if typed != declared(get("logical")):
                    raise CompiledError("COMPILED_WINDOW_TYPE")
                retained = (
                    typed.resolved_type.name,
                    physical.NULLABILITY[typed.nullability],
                )
                if physical_required:
                    if argument is None:
                        realized, problem = windowing.result_realization(
                            family, function, (), retained
                        )
                    else:
                        defaults = tuple(v for role, v in static if role == "default")
                        default = (
                            None
                            if not defaults
                            else "NULL"
                            if defaults[0] is None
                            else str(defaults[0])
                        )
                        realized, problem = windowing.resolved_value_result(
                            family,
                            argument.realization,
                            argument.origin,
                            default,
                            retained,
                        )
                    if realized is None or problem is not None:
                        raise CompiledError("COMPILED_WINDOW_DOMAIN")
                else:
                    realized = None
            elif kind in ("port", "read"):
                origin = facts[operands[0]].origin
                type_parameters = facts[operands[0]].parameters
                introduction, nulling = (
                    facts[operands[0]].introduction,
                    facts[operands[0]].nulling,
                )
                if kind == "port" and get("owner").kind == "aggregate":
                    origin = "aggregate"
                typed = facts[operands[0]].value_type
                realized = facts[operands[0]].realization
                if kind == "port" and declared(get("logical")) != typed:
                    raise CompiledError("COMPILED_PORT_TYPE")
            else:
                operator = get("operator")
                if type(operator) is not tuple or len(operator) != 2:
                    raise CompiledError("COMPILED_OPERATOR")
                role, token = operator
                arguments = tuple(facts[child].value_type for child in operands)
                error = None
                if role == "unary" and token in ("+", "-") and len(arguments) == 1:
                    typed, error = resolved_unary_value_type(arguments[0])
                    origin = input_origin = facts[operands[0]].origin
                    if input_origin != "literal":
                        origin = "unsupported"
                elif (
                    role == "binary"
                    and token in ("+", "-", "*", "and", "or")
                    and len(arguments) == 2
                ):
                    typed, error = resolved_binary_value_type(token, *arguments)
                elif (
                    role == "comparison"
                    and token in ("==", "!=", "<", "<=", ">", ">=")
                    and len(arguments) == 2
                ):
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.UNKNOWN,
                    )
                elif (
                    role == "null_test"
                    and token in ("is_null", "is_not_null")
                    and len(arguments) == 1
                ):
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL,
                    )
                else:
                    raise CompiledError("COMPILED_OPERATOR")
                if error is not None or typed != declared(get("logical")):
                    raise CompiledError("COMPILED_OPERATOR_TYPE")
                literal_value = facts[operands[0]].value
                if role == "unary" and type(literal_value) in (int, float):
                    value = -literal_value if token == "-" else +literal_value
                input_facts = tuple(facts[child] for child in operands)
                if physical_required:
                    inputs = tuple(item.require_realization() for item in input_facts)
                    nullable = physical.NULLABILITY[typed.nullability]
                    tag = typed.resolved_type.name
                    problem = None
                    if role == "binary":
                        realized, problem = physical.resolved_binary_realization(
                            family, token, tag, nullable, *inputs
                        )
                    elif role == "comparison":
                        realized, problem = physical.resolved_comparison_realization(
                            family, tag, nullable, *inputs
                        )
                    elif role == "null_test":
                        realized = physical._bool(family, False)
                    elif type(input_facts[0].value) in (int, float):
                        value = (
                            -input_facts[0].value
                            if token == "-"
                            else +input_facts[0].value
                        )
                        described = literal_representation(tag, value, family)
                        realized = physical.Realization(
                            tag,
                            described["storage"],
                            described["nullable"],
                            described["domain"],
                        )
                    else:
                        inner = inputs[0]
                        interval = physical.int_bounds(inner)
                        if tag != "Int" or interval is None:
                            raise CompiledError("COMPILED_UNARY_DOMAIN")
                        low, high = (
                            (-interval[1], -interval[0]) if token == "-" else interval
                        )
                        realized = physical._checked_int(
                            physical._arithmetic_storage(family, inner, inner),
                            low,
                            high,
                            nullable,
                        )
                    if realized is None or problem is not None:
                        raise CompiledError("COMPILED_PHYSICAL_DOMAIN")
                else:
                    realized = None
            if not physical_required:
                realized = None
            facts[ref] = CompiledScalarFact(
                root,
                ref,
                typed,
                value,
                operator,
                operands,
                realization=realized,
                origin=origin,
                parameters=type_parameters,
                introduction=introduction,
                nulling=nulling,
            )
    retention = tuple(
        (r.address, project_joined_row_filter._SQL_ROW_RETENTION_EFFECTS)
        for r in records.values()
        if r.address.kind == "row" and r.get("predicate") is not None
    )
    from pietto._project.project_single_match import compiled_requests

    declarations = compiled_declarations(root)
    return CompiledCompletedSemanticResult(
        root,
        values,
        declarations,
        tuple(facts[address] for address in records if address in facts),
        retention,
        compiled_requests(root, declarations),
    )


def verify_compiled_semantics(value):
    """Independently inspect derived facts; never invoke their constructor."""
    import json
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_sql_emission_parameters import (
        literal_representation,
        same_value,
        value_valid,
    )
    from pietto._project.project_sql_emission_rows import Realization, NULLABILITY
    from pietto._project.project_sql_emission_verification import (
        resolved_row_realization,
    )
    from pietto.semantic.expressions import (
        resolved_literal_value_type,
        resolved_unary_value_type,
        resolved_binary_value_type,
    )
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
    )

    need(type(value) is CompiledCompletedSemanticResult, "SEMANTIC_ROOT")
    value.root.verify()
    records = value.root.records
    from pietto._project.project_compiled_schema import selected_records

    executable = selected_records(records, records[value.root.description.query])
    from pietto._project.project_single_match import (
        CompiledSingleMatchRequest,
        ProjectSingleMatchScope,
        ProjectSingleMatchUnit,
    )
    from pietto._project.module_attribution import CompiledDeclarationOccurrence

    declarations = tuple(r for r in records.values() if r.address.kind == "declaration")
    need(
        type(value.declarations) is tuple
        and len(value.declarations) == len(declarations),
        "SEMANTIC_DECLARATIONS",
    )
    owners = {}
    for declaration, record in zip(value.declarations, declarations, strict=True):
        need(
            type(declaration) is CompiledDeclarationOccurrence
            and declaration.root is value.root
            and declaration.address == record.address
            and (
                declaration.module_path,
                declaration.module_position,
                declaration.declaration_position,
                declaration.namespace,
                declaration.kind,
                declaration.name,
            )
            == record.values,
            "SEMANTIC_DECLARATION",
        )
        owners[record.address] = declaration
    expected_requests = records[value.root.description.query].get("requests")
    need(
        type(value.single_match_requests) is tuple
        and len(value.single_match_requests) == len(expected_requests),
        "SEMANTIC_REQUEST_INVENTORY",
    )
    request_objects = {}
    for request, address in zip(
        value.single_match_requests, expected_requests, strict=True
    ):
        record = records[address]
        need(
            type(request) is CompiledSingleMatchRequest
            and request.root is value.root
            and request.address == address
            and request.owner is owners[record.get("owner")]
            and request.use is records[record.get("use")]
            and request.scope is ProjectSingleMatchScope(record.get("scope"))
            and request.unit is ProjectSingleMatchUnit(record.get("unit"))
            and request.path
            is (None if record.get("path") is None else records[record.get("path")])
            and request.hop == record.get("hop")
            and request.input_pairs == record.get("pairs"),
            "SEMANTIC_REQUEST",
        )
        need(
            address not in request_objects or request_objects[address] is request,
            "SEMANTIC_REQUEST_ALIAS",
        )
        request_objects[address] = request
    family = records[Address("target", 0)].get("family")
    slots = tuple(r for r in records.values() if r.address.kind == "slot")
    need(
        type(value.values) is tuple and len(slots) == len(value.values),
        "SEMANTIC_BINDING",
    )
    replacements = {}
    for slot, scalar in zip(slots, value.values, strict=True):
        need(value_valid(slot.get("tag"), scalar, family), "SEMANTIC_BINDING")
        replacements[slot.get("literal")] = scalar
    expected_records = tuple(
        r
        for r in records.values()
        if r.address.kind
        in {
            "field",
            "port",
            "read",
            "literal",
            "operation",
            "aggregate_value",
            "window_value",
            "set_value",
            "join_value",
        }
    )
    need(
        type(value.facts) is tuple and len(value.facts) == len(expected_records),
        "SEMANTIC_INVENTORY",
    )
    by_address = {}
    for fact, record in zip(value.facts, expected_records, strict=True):
        need(
            type(fact) is CompiledScalarFact
            and fact.root is value.root
            and fact.address == record.address
            and fact.address not in by_address,
            "SEMANTIC_FACT",
        )
        need(
            type(fact.value_type) is ValueType
            and (
                type(fact.realization) is Realization
                if fact.address in executable
                else fact.realization is None
            ),
            "SEMANTIC_FACT_TYPE",
        )
        by_address[record.address] = fact
    checked, active = set(), set()
    for address in by_address:
        stack = [(address, False)]
        while stack:
            current, returning = stack.pop()
            if current in checked:
                continue
            record, actual = records[current], by_address[current]
            kind, get = record.address.kind, record.get
            children = (
                get("operands")
                if kind == "operation"
                else get("arguments")
                if kind == "aggregate_value"
                else get("inputs")
                if kind == "set_value"
                else (get("source"),)
                if kind == "port"
                else (get("port"),)
                if kind == "read"
                else ()
            )
            if kind == "join_value":
                join = records[get("owner")]
                children = (
                    get("input"),
                    *(
                        a
                        for e in join.get("equalities")
                        for a in (records[e].get("left"), records[e].get("right"))
                    ),
                    *(
                        (join.get("predicate"),)
                        if join.get("predicate") is not None
                        else ()
                    ),
                )
            if kind == "window_value":
                spec = records[get("specification")]
                children = (
                    *get("inputs"),
                    *(a for _, a in get("arguments") if a.kind != "null_literal"),
                    *spec.get("partition"),
                    *(a for a, _, _ in spec.get("ordering")),
                )
            need(
                type(children) is tuple and all(c in by_address for c in children),
                "SEMANTIC_DEPENDENCY",
            )
            if not returning:
                need(current not in active, "SEMANTIC_CYCLE")
                active.add(current)
                stack.append((current, True))
                stack.extend((c, False) for c in reversed(children))
                continue
            active.remove(current)
            inputs = tuple(by_address[c] for c in children)
            expected_value, operator = None, None
            physical_required = current in executable
            origin = "unsupported"
            type_parameters = None
            introduction, nulling = None, ()
            if kind == "field":
                origin = "field"
                type_parameters = get("decimal")
                name, nullable = get("logical")
                typed = ValueType(
                    ResolvedType(name, TypeKind.BUILTIN), EffectiveNullability(nullable)
                )
                if physical_required:
                    expected = json.loads(get("physical"))
                    realization = Realization(
                        name,
                        expected["storage"],
                        expected["nullable"],
                        expected["domain"],
                    )
                else:
                    realization = None
            elif kind == "literal":
                origin = "literal"
                expected_value = replacements.get(current, get("value").value)
                typed = resolved_literal_value_type(expected_value)
                if physical_required:
                    expected = literal_representation(
                        get("tag"), expected_value, family
                    )
                    realization = Realization(
                        get("tag"),
                        expected["storage"],
                        expected["nullable"],
                        expected["domain"],
                    )
                else:
                    realization = None
            elif kind == "aggregate_value":
                origin = "aggregate"
                from pietto.semantic.aggregates import (
                    semantic_aggregate_result_value_type,
                )
                from pietto._project.project_sql_emission_verification import (
                    _aggregate_result_realization,
                )
                from pietto._project import project_sql_emission_aggregation as grouping

                function = get("function")
                need(
                    function in grouping.SPELLING and len(inputs) <= 1,
                    "SEMANTIC_AGGREGATE_SIGNATURE",
                )
                argument = inputs[0] if inputs else None
                if physical_required and argument is not None:
                    need(
                        grouping.resolved_argument_problem(
                            function,
                            argument.address.kind == "read",
                            argument.realization,
                        )
                        is None,
                        "SEMANTIC_AGGREGATE_ARGUMENT",
                    )
                typed = semantic_aggregate_result_value_type(
                    function, None if argument is None else argument.value_type
                )
                if typed is None:
                    raise ValueError("COMPILED_SEMANTIC_AGGREGATE_TYPE")
                if physical_required:
                    realization = _aggregate_result_realization(
                        family,
                        function,
                        argument,
                        (typed.resolved_type.name, NULLABILITY[typed.nullability]),
                    )
                else:
                    realization = None
            elif kind == "join_value":
                from pietto._project.project_sql_plan_joins import (
                    compiled_join_rejections,
                )
                from pietto._project.project_sql_emission_joins import (
                    resolved_port_realization,
                )

                join = records[get("owner")]
                read = records[get("input")]
                incoming = by_address[read.address]
                use = records[read.get("use")]
                rejected = (use.address, read.get("port")) in compiled_join_rejections(
                    records, join
                )
                from pietto._project.project_current_joins import (
                    resolved_join_field_nullability,
                )
                from pietto.ast_nodes import AuthoredJoinKind
                from pietto._project.model import ProjectRowFieldNullability

                preserve = (
                    use.get("ordinal") == 0 and use.get("producer").kind == "join"
                )
                introduction = incoming.introduction if preserve else use.address
                nulling = incoming.nulling if preserve else ()
                if join.get("kind") == "full" or (
                    join.get("kind"),
                    use.get("ordinal"),
                ) in (("left", 1), ("right", 0)):
                    nulling = (*nulling, join.address)
                nullable = EffectiveNullability(
                    resolved_join_field_nullability(
                        AuthoredJoinKind(join.get("kind")),
                        ProjectRowFieldNullability(
                            incoming.value_type.nullability.value
                        ),
                        bool(nulling),
                        rejected,
                    ).value
                )
                typed = ValueType(incoming.value_type.resolved_type, nullable)
                origin, type_parameters = incoming.origin, incoming.parameters
                if physical_required:
                    realization, problem = resolved_port_realization(
                        typed.resolved_type.name,
                        NULLABILITY[nullable],
                        incoming.realization,
                        outer=True,
                        proved=rejected,
                    )
                    if realization is None or problem is not None:
                        raise ValueError("COMPILED_SEMANTIC_JOIN_DOMAIN")
                else:
                    realization = None
            elif kind == "set_value":
                from pietto._project.project_set_operations import (
                    resolved_set_nullability,
                )
                from pietto._project.project_row_equivalence import (
                    resolved_builtin_equivalence_reason,
                )
                from pietto._project.project_sql_emission_verification import (
                    resolved_set_column_realization,
                )
                from pietto._project.model import ProjectRowFieldNullability
                from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier

                operation = records[get("owner")]
                first = inputs[0]
                need(
                    all(
                        i.value_type.resolved_type == first.value_type.resolved_type
                        and i.parameters == first.parameters
                        for i in inputs
                    ),
                    "SEMANTIC_SET_TYPE",
                )
                type_parameters = first.parameters
                set_kind, quantifier = (
                    SetOperationKind(operation.get("kind")),
                    SetOperationQuantifier(operation.get("quantifier")),
                )
                nullable = resolved_set_nullability(
                    set_kind,
                    tuple(
                        ProjectRowFieldNullability(i.value_type.nullability.value)
                        for i in inputs
                    ),
                )
                typed = ValueType(
                    first.value_type.resolved_type, EffectiveNullability(nullable.value)
                )
                if physical_required:
                    realization = resolved_set_column_realization(
                        set_kind,
                        quantifier,
                        NULLABILITY[typed.nullability],
                        inputs,
                        tuple(
                            resolved_builtin_equivalence_reason(
                                i.value_type.resolved_type.name
                            )
                            for i in inputs
                        ),
                    )
                else:
                    realization = None
            elif kind == "window_value":
                from pietto._project import project_sql_emission_windows as windowing
                from pietto._project.project_sql_plan_windows import (
                    resolved_result_type,
                )
                from pietto._project.project_sql_emission_verification import (
                    _window_result_realization,
                    resolved_window_value_result,
                )

                origin = "window"
                function = get("function")
                static = windowing.resolved_arguments(
                    function, get("arguments"), records, family
                )
                reads = tuple(a for role, a in get("arguments") if role == "value")
                argument = by_address[reads[0]] if reads else None
                typed = resolved_result_type(
                    function, None if argument is None else argument.value_type, static
                )
                type_parameters = None if argument is None else argument.parameters
                retained = (typed.resolved_type.name, NULLABILITY[typed.nullability])
                if physical_required:
                    if argument is None:
                        realization = _window_result_realization(
                            family, function, (), retained
                        )
                    else:
                        defaults = tuple(v for role, v in static if role == "default")
                        default = (
                            None
                            if not defaults
                            else "NULL"
                            if defaults[0] is None
                            else str(defaults[0])
                        )
                        realization = resolved_window_value_result(
                            family,
                            argument.realization,
                            argument.origin,
                            default,
                            retained,
                        )
                else:
                    realization = None
            elif kind in ("read", "port"):
                origin = (
                    "aggregate"
                    if kind == "port" and get("owner").kind == "aggregate"
                    else inputs[0].origin
                )
                typed, realization = inputs[0].value_type, inputs[0].realization
                type_parameters = inputs[0].parameters
                introduction, nulling = inputs[0].introduction, inputs[0].nulling
            else:
                operator = get("operator")
                role, token = operator
                if role == "unary":
                    origin = (
                        "literal" if inputs[0].origin == "literal" else "unsupported"
                    )
                    typed, problem = resolved_unary_value_type(inputs[0].value_type)
                elif role == "binary":
                    typed, problem = resolved_binary_value_type(
                        token, *(i.value_type for i in inputs)
                    )
                else:
                    problem = None
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL
                        if role == "null_test"
                        else EffectiveNullability.UNKNOWN,
                    )
                need(problem is None, "SEMANTIC_TYPE")
                if role == "unary" and type(inputs[0].value) in (int, float):
                    expected_value = (
                        -inputs[0].value if token == "-" else +inputs[0].value
                    )
                if physical_required:
                    if role == "unary" and type(inputs[0].value) in (int, float):
                        expected_value = (
                            -inputs[0].value if token == "-" else +inputs[0].value
                        )
                        expected = literal_representation(
                            typed.resolved_type.name, expected_value, family
                        )
                        realization = Realization(
                            typed.resolved_type.name,
                            expected["storage"],
                            expected["nullable"],
                            expected["domain"],
                        )
                    else:
                        realization = resolved_row_realization(
                            family,
                            role,
                            token,
                            typed.resolved_type.name,
                            NULLABILITY[typed.nullability],
                            tuple(i.realization for i in inputs),
                        )
                else:
                    realization = None
            need(
                actual.value_type == typed
                and actual.origin == origin
                and actual.parameters == type_parameters
                and actual.introduction == introduction
                and actual.nulling == nulling
                and same_value(actual.value, expected_value)
                and actual.operator == operator
                and actual.operands == children,
                "SEMANTIC_DERIVATION",
            )
            if physical_required:
                observed = actual.require_realization()
                if type(realization) is not Realization:
                    raise ValueError("COMPILED_SEMANTIC_REALIZATION")
                need(
                    type(observed.storage) is dict
                    and type(observed.domain) is dict
                    and type(observed.nullable) is type(realization.nullable),
                    "SEMANTIC_REALIZATION",
                )
                need(
                    observed.tag == realization.tag
                    and json.dumps(
                        (observed.storage, observed.nullable, observed.domain),
                        sort_keys=True,
                        allow_nan=False,
                    )
                    == json.dumps(
                        (realization.storage, realization.nullable, realization.domain),
                        sort_keys=True,
                        allow_nan=False,
                    ),
                    "SEMANTIC_REALIZATION",
                )
            else:
                need(actual.realization is None, "SEMANTIC_LOGICAL_ONLY")
            checked.add(current)
    expected_retention = tuple(
        (r.address, project_joined_row_filter._SQL_ROW_RETENTION_EFFECTS)
        for r in records.values()
        if r.address.kind == "row" and r.get("predicate") is not None
    )
    need(value.retention == expected_retention, "SEMANTIC_RETENTION")
    return value
