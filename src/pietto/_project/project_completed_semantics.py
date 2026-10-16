"""Private Phase-63 completed Project semantic result boundary."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto._project.model import CompiledProjectInput
    from pietto._project.module_attribution import CompiledDeclarationOccurrence
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_sql_emission_rows import Realization
    from pietto.semantic.model import ValueType


from pietto._project.query_parameters import query_parameter_semantic_diagnostics
from pietto._project.project_set_operations import ProjectSetFailure
from pietto._project.module_relation_resolution import ProjectResolvedSetOperand

from dataclasses import dataclass, field, replace
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
    ProjectCompletedValuesOutput,
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
from pietto.ast_nodes import (
    QueryDef,
    SourceDef,
    TableDef,
    TableFunctionRelationDef,
    ValuesRelationDef,
)
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
    """Closed direct-builder terminals."""

    LEGACY_FLAT_MODE = "legacy_flat_mode"
    PACKAGE_ROOT_MODE = "package_root_mode"
    MODULE_IMPORT_CYCLE = "module_import_cycle"


def _non_concrete_reason(
    semantic_result: ProjectSemanticResult,
) -> ProjectCompletedSemanticNonConcreteReason | None:
    """Return the terminal for roots outside the positive chain, or None."""
    if semantic_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT:
        return ProjectCompletedSemanticNonConcreteReason.LEGACY_FLAT_MODE
    if semantic_result.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT:
        return ProjectCompletedSemanticNonConcreteReason.PACKAGE_ROOT_MODE
    graph = semantic_result.module_graph
    # Modules in an import cycle have no relation authority to complete.
    if graph is not None and graph.cycles:
        return ProjectCompletedSemanticNonConcreteReason.MODULE_IMPORT_CYCLE
    return None


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
    """One typed non-positive result with no partial chain."""

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
        expected = _non_concrete_reason(self.semantic_result)
        if expected is None or self.reason is not expected:
            raise ValueError("Completed Project terminal must retain its exact reason.")
        diagnostics = self.semantic_result.diagnostics
        if self.reason is ProjectCompletedSemanticNonConcreteReason.MODULE_IMPORT_CYCLE:
            # Each module's source connectors are checked from its own script,
            # after the semantic diagnostics as on the positive chain.
            diagnostics = (
                *diagnostics,
                *_source_connector_diagnostics(self.semantic_result),
            )
        object.__setattr__(self, "diagnostics", diagnostics)


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
                    shapes=(
                        verification.root.base_relational.origins.value_fds.row_keys.shape_diagnostics
                    ),
                    relationships=(
                        verification.root.join_regions.uses.index.guarantees.conditions.diagnostics
                    ),
                ),
                *operative.diagnostics,
                *source_diagnostics,
                *query_parameter_semantic_diagnostics(
                    self.semantic_result.module_relation_resolutions,
                    self.semantic_result.module_catalogs,
                    # Every concrete input, VALUES bodies included, names its
                    # fields; an entry kind with no schema reader fails closed.
                    {
                        entry.owner: frozenset(
                            project_final_outputs._entry_schema(entry).fields
                        )
                        for entry in effective_outputs.entries
                        if not isinstance(
                            entry,
                            (
                                ProjectEffectiveOutputTerminal,
                                ProjectEffectiveOutputCompletionTerminal,
                            ),
                        )
                    },
                ),
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
                ProjectCompletedValuesOutput,
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
    if type(definition) not in {
        SourceDef,
        TableDef,
        QueryDef,
        ValuesRelationDef,
        TableFunctionRelationDef,
    }:
        raise TypeError("Project completion diagnostic requires a relation definition.")
    span = definition.span
    return Diagnostic(
        code="PIE-S2333",
        severity=Severity.ERROR,
        message=(
            "Project relation semantic completion is unavailable: "
            f"{entry.owner.identity.declared_name}{_fanout_cause(entry)}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _fanout_cause(entry: ProjectEffectiveOutputCompletionEntry) -> str:
    """Name the JOINs that may repeat this relation's own aggregate rows.

    Only the relation whose own joined aggregation is refused for fan-out
    gets the clause; a relation that merely reads it keeps the bare message.
    """

    qualify = (
        entry.joined_qualify
        if type(entry) is ProjectEffectiveOutputCompletionTerminal
        else None
    )
    if type(qualify) is not project_joined_qualify.ProjectNonConcreteJoinedQualify:
        return ""
    stage = qualify.window_stage
    if type(stage) is not project_joined_windows.ProjectNonConcreteJoinedWindowStage:
        return ""
    aggregation = stage.input_aggregation
    if (
        type(aggregation)
        is not project_joined_aggregation.ProjectNonConcreteJoinedAggregation
        or aggregation.reason
        is not (
            project_joined_aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
        )
    ):
        return ""
    risky = tuple(
        linkage
        for linkage in aggregation.grain_linkages
        if linkage.multiplicity_exposures
    )
    return _fanout_clause(risky) if risky else ""


type _Factors = frozenset[project_grain.ProjectGrainFactorIdentity]
type _Dependency = tuple[_Factors, _Factors]


def _fanout_clause(
    risky: tuple[project_joined_aggregation.ProjectJoinedAggregateGrainLinkage, ...],
) -> str:
    """Name the repeating JOINs and only remedies the grain engine accepts.

    Every remedy is checked with the engine's own dependency closure: applied
    alone, it must bring each refused aggregate's closure to the full JOIN
    grain. A declared key is offered only where the engine turns it into a
    dependency (a one-hop relationship JOIN without ON: the target key for
    INNER and LEFT, the source key for INNER) and only on a source, whose shape
    can declare it; a group key only for an input that has a strict key or is
    a source. A remedy that cannot be derived this way is left out.
    """

    region = risky[0].multifact_region
    index = region.grain_index
    joins = region.region.joins
    final_grain = risky[0].final_grain
    final = frozenset(final_grain.active)
    seeds = tuple(frozenset(linkage.combined_seed.factors) for linkage in risky)

    def closure(factors: _Factors, extra: tuple[_Dependency, ...] = ()) -> _Factors:
        current = factors
        while True:
            closed = frozenset(
                project_grain.grain_dependency_closure(
                    index, project_multifact._factor_set(index, tuple(current))
                ).factors
            )
            grown = closed.union(*(rhs for lhs, rhs in extra if lhs <= closed))
            if grown == closed:
                return closed
            current = grown

    def localized(properties, use) -> _Factors:
        # The factors a strict key of this input protects (the engine's law);
        # an input the final grain does not carry (a SEMI or ANTI target)
        # protects nothing and fails closed to no factors.
        try:
            return frozenset(
                project_multifact._localized_input_factors(
                    grain=properties.grain,
                    introduction_use=use,
                    final_grain=final_grain,
                )
            )
        except ValueError:
            return frozenset()

    def source_shape(
        binding: project_relationship_uses.ProjectRelationBindingOccurrence | None,
    ) -> str | None:
        # A key can be declared only on a source, through its shape.
        target = None if binding is None else binding.target
        if target is None or type(target.target_occurrence.definition) is not (
            SourceDef
        ):
            return None
        return target.target_occurrence.identity.declared_name

    def source_binding(join):
        # An ON or CROSS JOIN reads its source binding through its condition.
        if join.use.source_binding is not None:
            return join.use.source_binding
        if type(join) is project_multifact.ProjectCurrentBinaryJoin:
            candidates = join.condition.environment.source_candidates
            return candidates[0] if len(candidates) == 1 else None
        return None

    # Each named row input (the FROM binding and every JOIN binding), its
    # binding and its factors; an intermediate multi-hop input has no name.
    from_binding = source_binding(joins[0])
    inputs: dict[
        str, tuple[project_relationship_uses.ProjectRelationBindingOccurrence, _Factors]
    ] = {}
    if from_binding is not None:
        inputs[from_binding.name] = (
            from_binding,
            localized(joins[0].left_input, joins[0].input_uses[0]),
        )
    last_hop = {join.use.identity: join for join in joins}
    hops: dict[object, int] = {}
    for join in joins:
        hops[join.use.identity] = hops.get(join.use.identity, 0) + 1
    previous: dict[object, _Factors] = {}
    edges = []
    for join in joins:
        target = localized(join.right_input, join.input_uses[1])
        source_input = source_binding(join)
        source = previous.get(
            join.use.identity,
            inputs[source_input.name][1]
            if source_input is not None and source_input.name in inputs
            else frozenset(),
        )
        previous[join.use.identity] = target
        if last_hop[join.use.identity] is join:
            inputs[join.use.target_binding.name] = (join.use.target_binding, target)
        edges.append((join, source, target))

    # Declarable keys, each with every dependency it would add, in JOIN order.
    keys: dict[object, tuple[str, list[_Dependency], dict[str, None]]] = {}
    for join, source, target in edges:
        clause = join.use.clause
        if (
            type(join) is not project_ir_joins.ProjectIRBinaryJoinOccurrence
            or hops[join.use.identity] != 1
            or clause.on_clause is not None
            or not source
            or not target
        ):
            continue
        # Each side's distinct matched fields: an ON may repeat an operand.
        sides = []
        if clause.kind in {"inner", "left"}:
            sides.append(
                (
                    join.use.target_binding,
                    list(dict.fromkeys(p.right.evidence.name for p in join.matches)),
                    (source, target),
                )
            )
        if clause.kind == "inner":
            sides.append(
                (
                    source_binding(join),
                    list(dict.fromkeys(p.left.evidence.name for p in join.matches)),
                    (target, source),
                )
            )
        for binding, fields, dependency in sides:
            shape = source_shape(binding)
            if shape is None:
                continue
            # A key is a field set: the first JOIN to need it fixes its spelling.
            identity = (binding.target.target_identity, frozenset(fields))
            text, dependencies, matched = keys.setdefault(
                identity, (_key(shape, fields), [], {})
            )
            dependencies.append(dependency)
            matched[join.use.target_binding.name] = None

    def with_keys(chosen: tuple[object, ...]) -> tuple[_Dependency, ...]:
        return tuple(item for key in chosen for item in keys[key][1])

    chosen: tuple[object, ...] | None = ()
    for seed in seeds:
        while chosen is not None and not final <= closure(seed, with_keys(chosen)):
            reached = closure(seed, with_keys(chosen))
            step = next(
                (
                    key
                    for key, (_, dependencies, _) in keys.items()
                    if key not in chosen
                    and any(
                        lhs <= reached and not rhs <= reached
                        for lhs, rhs in dependencies
                    )
                ),
                None,
            )
            chosen = None if step is None else (*chosen, step)
    for key in chosen or ():
        rest = tuple(other for other in chosen or () if other != key)
        if all(final <= closure(seed, with_keys(rest)) for seed in seeds):
            chosen = rest
    declared = tuple(key for key in keys if key in (chosen or ()))

    def grouped(picked: tuple[str, ...]) -> bool:
        protected = frozenset().union(*(inputs[name][1] for name in picked))
        return all(final <= closure(seed | protected) for seed in seeds)

    picked = tuple(
        name
        for name, (binding, factors) in inputs.items()
        if factors
        and (
            source_shape(binding) is not None
            or (
                binding.output is not None
                and any(
                    key.strength is project_row_keys.ProjectRowUniquenessStrength.STRICT
                    for key in binding.output.keys
                )
            )
        )
    )
    if grouped(picked):
        for name in picked:
            if grouped(rest_names := tuple(item for item in picked if item != name)):
                picked = rest_names
    else:
        picked = ()

    repeated = tuple(
        f"JOIN {join.use.target_binding.name}"
        for join, source, target in edges
        if source
        and target
        and any(
            (source <= (reached := closure(seed))) != (target <= reached)
            for seed in seeds
        )
    )
    remedies = []
    if declared:
        remedies.append(
            "declare "
            + _and_list(
                tuple(
                    f"a unique key on {keys[key][0]} (matched by "
                    f"JOIN{'s' if len(keys[key][2]) > 1 else ''} "
                    f"{_and_list(tuple(keys[key][2]))})"
                    for key in declared
                )
            )
        )
    if picked:
        noun = "a unique key" if len(picked) == 1 else "unique keys"
        remedies.append(
            f"group by {noun} of {_and_list(picked)} whose fields are all not null"
        )
    if not repeated and not remedies:
        return ""
    cause = (
        f"an aggregate may read rows repeated by {_and_list(tuple(dict.fromkeys(repeated)))}"
        if repeated
        else "an aggregate may read rows that a JOIN repeats"
    )
    return f" ({cause}{'; ' + ', or '.join(remedies) if remedies else ''})"


def _key(relation: str, fields: list[str]) -> str:
    if len(fields) == 1:
        return f"{relation}.{fields[0]}"
    return f"{relation} ({', '.join(fields)})"


def _and_list(names: tuple[str, ...]) -> str:
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _ordinary_row_diagnostics(
    facts: module_semantic_fact_preservation.ProjectModuleRelationSemanticFacts,
) -> tuple[Diagnostic, ...]:
    return (
        *(() if facts.let_scope_facts is None else facts.let_scope_facts.diagnostics),
        *(item.diagnostic for item in facts.scalar_reads if item.diagnostic),
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
    shapes: tuple[Diagnostic, ...] = (),
    relationships: tuple[Diagnostic, ...] = (),
) -> tuple[Diagnostic, ...]:
    retired_ids = {id(diagnostic) for diagnostic in retired}
    retained = [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if id(diagnostic) not in retired_ids
    ]
    # Shape and relationship declarations are checked before the relations
    # using them.
    retained.extend(shapes)
    retained.extend(relationships)
    retained_ids = {id(diagnostic) for diagnostic in retained}
    semantic_facts = semantic_result.module_semantic_facts
    for entry in effective_outputs.entries:
        if type(entry) is ProjectExistingEffectiveOutput:
            for diagnostic in _ordinary_row_diagnostics(entry.fragment.semantic_facts):
                if id(diagnostic) not in retained_ids:
                    retained.append(diagnostic)
                    retained_ids.add(id(diagnostic))
            continue
        if type(entry) in {ProjectCompletedSetOutput, ProjectCompletedValuesOutput}:
            continue
        completed = type(entry) is ProjectCompletedEffectiveOutput
        if not completed and type(entry) not in {
            ProjectEffectiveOutputTerminal,
            ProjectEffectiveOutputCompletionTerminal,
        }:
            raise TypeError("Final diagnostics require exact effective entries.")
        # A JOIN reader or a reader of a set completes its row without its
        # facts, so the diagnostics of its scalar reads are retained here.
        reads = (
            item.diagnostic
            for facts in (
                () if semantic_facts is None else semantic_facts.find_owner(entry.owner)
            )
            for item in facts.scalar_reads
            if item.diagnostic is not None
        )
        errors = tuple(
            diagnostic
            for diagnostic in (
                *(() if completed else _entry_error_diagnostics(entry)),
                *reads,
            )
            if id(diagnostic) not in retired_ids
        )
        if not errors and not completed:
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
    reason = _non_concrete_reason(semantic_result)
    if reason is not None:
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
    # Header parameter values in header order; None is the unbound template.
    parameters: tuple | None = field(default=None, repr=False)


def _captured(records, read, typed, realized):
    """A captured field read widened to nullable by the capture rule."""
    from dataclasses import replace
    from pietto._project.project_compiled_schema import captured_logical
    from pietto.semantic.model import EffectiveNullability, ValueType

    if captured_logical(records, read)[1] != "nullable":
        return typed, realized
    return ValueType(typed.resolved_type, EffectiveNullability.NULLABLE), (
        None if realized is None else replace(realized, nullable=True)
    )


def _compiled_parameter_values(records, parameters, family):
    """Header records in order; a binding gives every one a valid value."""
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_sql_emission_parameters import value_valid

    declared = tuple(r for r in records.values() if r.address.kind == "parameter")
    if parameters is None:
        return declared, None
    if type(parameters) is not tuple or len(parameters) != len(declared):
        raise CompiledError("COMPILED_BINDING_PARAMETERS")
    for record, value in zip(declared, parameters, strict=True):
        if not (
            record.get("nullable")
            if value is None
            else value_valid(record.get("tag"), value, family)
        ):
            raise CompiledError("COMPILED_BINDING_PARAMETERS")
    return declared, {r.address: v for r, v in zip(declared, parameters, strict=True)}


def derive_compiled_semantics(root, values, parameters=None):
    """Derive resolved scalar inputs without calling any source elaborator.

    ``parameters`` is None for the unbound template; a binding re-derives every
    fact from its exact values."""
    import json
    from pietto._project.model import CompiledProjectInput
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_sql_emission_parameters import literal_representation
    from pietto._project.module_attribution import compiled_declarations
    from pietto._project.project_compiled_schema import (
        Address,
        CompiledError,
        Scalar,
        scalar_read_port,
    )
    from pietto._project.project_sql_emission_parameters import value_valid
    from pietto.semantic.expressions import (
        resolved_literal_value_type,
        resolved_unary_value_type,
        resolved_binary_value_type,
        resolved_comparison_value_type,
        resolved_like_value_type,
    )
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
        ValueTypeKind,
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
    _declared, bound = _compiled_parameter_values(records, parameters, family)
    from pietto._project import project_sql_emission_windows as window_counts

    # A header parameter read as a window offset, bucket count or position.
    counts = {
        address: role
        for r in records.values()
        if r.address.kind == "window_value"
        for role, address in r.get("arguments")
        if role in window_counts.COUNT_ROLES and address.kind == "parameter_read"
    }
    facts, active = {}, set()
    null_parents = {}
    for record in records.values():
        if record.address.kind != "operation":
            continue
        for position, operand in enumerate(record.get("operands")):
            if operand.kind == "null_literal":
                null_parents.setdefault(operand, []).append((record, position))

    def declared(value):
        if (
            type(value) is not tuple
            or len(value) != 2
            or value[0]
            not in (
                "Int",
                "Bool",
                "Float",
                "Text",
                "Decimal",
                "Date",
                "Timestamp",
                "UUID",
            )
            or value[1] not in ("non_null", "nullable", "unknown")
        ):
            raise CompiledError("COMPILED_LOGICAL_TYPE")
        return ValueType(
            ResolvedType(value[0], TypeKind.BUILTIN),
            EffectiveNullability(value[1]),
        )

    def dependencies(record) -> tuple[Address, ...]:
        kind, get = record.address.kind, record.get
        if kind == "operation" and get("operator") == ("scalar", "scalar"):
            # A scalar read reads the one producer output its block use names.
            port = scalar_read_port(records, record.address)
            if port is None or get("operands"):
                raise CompiledError("COMPILED_BLOCK_READ")
            return (port,)
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
        "null_literal",
        "parameter_read",
        "operation",
        "aggregate_value",
        "window_value",
        "set_value",
        "join_value",
    }
    for address in records:
        if address.kind not in scalar_kinds:
            continue
        if address.kind == "null_literal":
            # A contextual NULL has no leaf type. Its retained parent edge supplies
            # the only admitted local constraint after the non-NULL siblings exist.
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
                pending.extend(
                    (child, False)
                    for child in reversed(
                        tuple(
                            sorted(
                                children,
                                key=lambda child: child.kind == "null_literal",
                            )
                        )
                    )
                )
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
                    realized = physical.source_realization(
                        physical.Realization(
                            typed.resolved_type.name,
                            described["storage"],
                            described["nullable"],
                            described["domain"],
                        )
                    )
                    if realized is None:
                        raise CompiledError("COMPILED_FIELD_DOMAIN")
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
                        (value, value)
                        if original.tag == "Int" and type(value) is int
                        else None,
                    )
                else:
                    realized = None
            elif kind == "parameter_read":
                origin = "parameter"
                declaration = records[get("parameter")]
                nullable = declaration.get("nullable")
                typed = ValueType(
                    ResolvedType(declaration.get("tag"), TypeKind.BUILTIN),
                    EffectiveNullability.NULLABLE
                    if nullable
                    else EffectiveNullability.NON_NULL,
                )
                if not physical_required:
                    realized = None
                elif ref in counts:
                    if declaration.get("tag") != "Int" or nullable:
                        raise CompiledError("COMPILED_WINDOW_PARAMETER")
                    realized = window_counts.count_realization(
                        family,
                        counts[ref],
                        bound=bound is not None,
                        value=None if bound is None else bound[declaration.address],
                    )
                    if realized is None:
                        raise CompiledError("COMPILED_PHYSICAL_DOMAIN")
                else:
                    realized = physical.parameter_realization(
                        family,
                        declaration.get("tag"),
                        nullable,
                        bound=bound is not None,
                        value=None if bound is None else bound[declaration.address],
                    )
            elif kind == "null_literal":
                site = records[get("site")]
                if site.get("reason") != "contextual_typed_null":
                    raise CompiledError("COMPILED_NULL_CONTEXT")
                candidates = []
                for parent, position in null_parents.get(ref, ()):
                    role, token = parent.get("operator")
                    parent_operands = parent.get("operands")
                    if role == "conditional" and position == 1:
                        candidates.append("Bool")
                    elif role == "conditional" and position in (0, 2):
                        sibling = parent_operands[2 if position == 0 else 0]
                        if sibling in facts:
                            candidates.append(facts[sibling].value_type)
                    elif role in {"membership", "scalar_call"} and (
                        role == "membership" or token in {"coalesce", "nullif"}
                    ):
                        candidates.extend(
                            facts[operand].value_type
                            for operand in parent_operands
                            if operand != ref and operand in facts
                        )
                    elif role == "relation_membership" and position == 0:
                        # A bare NULL left value takes the read column's type.
                        candidates.extend(
                            declared(port.get("logical"))
                            for use in records.values()
                            if use.address.kind == "expression_block_use"
                            and use.get("operation") == parent.address
                            for port in records.values()
                            if port.address.kind == "port"
                            and port.get("owner") == use.get("producer")
                        )
                    elif role == "scalar_call":
                        from pietto.semantic.catalog import BUILTIN_FUNCTIONS

                        signature = BUILTIN_FUNCTIONS.get(token)
                        if signature is not None and position < len(
                            signature.parameter_types
                        ):
                            candidates.append(signature.parameter_types[position])
                resolved = []
                for candidate in candidates:
                    if isinstance(candidate, str):
                        if candidate in {"Int|Decimal", "T"}:
                            continue
                        candidate = ValueType(
                            ResolvedType(candidate, TypeKind.BUILTIN),
                            EffectiveNullability.NULLABLE,
                        )
                    if candidate.kind is ValueTypeKind.KNOWN:
                        resolved.append(candidate.resolved_type)
                if not resolved or any(item != resolved[0] for item in resolved[1:]):
                    raise CompiledError("COMPILED_NULL_CONTEXT")
                typed = ValueType(resolved[0], EffectiveNullability.NULLABLE)
                origin = "literal"
                if physical_required:
                    realized = physical.Realization(
                        typed.resolved_type.name,
                        {"kind": "typed_null"},
                        True,
                        {"kind": "typed_null"},
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
                from pietto._project import (
                    project_sql_emission_parameters as parameter_physical,
                )
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
                            else windowing.BINDING_DEFAULT
                            if type(defaults[0]) is windowing.ParameterStatic
                            else str(defaults[0])
                        )
                        realized, problem = windowing.resolved_value_result(
                            family,
                            argument.realization,
                            # A parameter value is its carrier anchor: MySQL
                            # reads a SIGNED anchor like a literal's.
                            (
                                "literal"
                                if parameter_physical.PHYSICAL[family][
                                    argument.value_type.resolved_type.name
                                ]
                                == "my_signed_int"
                                else "unsupported"
                            )
                            if value_reads[0].kind == "parameter_read"
                            else argument.origin,
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
                if kind == "read" and get("role") == "capture":
                    typed, realized = _captured(records, ref, typed, realized)
            else:
                operator = get("operator")
                if type(operator) is not tuple or len(operator) != 2:
                    raise CompiledError("COMPILED_OPERATOR")
                role, token = operator
                arguments = tuple(facts[child].value_type for child in operands)
                error = None
                if (
                    role in {"unary", "not"}
                    and token in ("+", "-", "not")
                    and len(arguments) == 1
                ):
                    typed, error = resolved_unary_value_type(token, arguments[0])
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
                    and token in ("==", "!=", "<", "<=", ">", ">=", "like", "not like")
                    and len(arguments) == 2
                ):
                    typed, error = (
                        resolved_like_value_type(*arguments)
                        if token in ("like", "not like")
                        else resolved_comparison_value_type(*arguments)
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
                elif role == "between" and len(arguments) == 3:
                    checked = tuple(
                        resolved_comparison_value_type(arguments[0], bound)
                        for bound in arguments[1:]
                    )
                    error = next((problem for _, problem in checked if problem), None)
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.UNKNOWN,
                    )
                elif role == "conditional" and len(arguments) == 3:
                    branches = (arguments[0], arguments[2])
                    error = (
                        None
                        if arguments[1].resolved_type.name == "Bool"
                        and branches[0].resolved_type == branches[1].resolved_type
                        else "conditional operands"
                    )
                    typed = ValueType(
                        branches[0].resolved_type,
                        max(
                            branches[0].nullability,
                            branches[1].nullability,
                            key=lambda item: ("non_null", "unknown", "nullable").index(
                                item.value
                            ),
                        ),
                    )
                elif role == "membership" and arguments:
                    error = (
                        None
                        if all(
                            item.resolved_type == arguments[0].resolved_type
                            for item in arguments
                        )
                        else "membership operands"
                    )
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL
                        if len(arguments) == 1
                        else max(
                            (item.nullability for item in arguments),
                            key=lambda item: ("non_null", "unknown", "nullable").index(
                                item.value
                            ),
                        ),
                    )
                elif role == "exists" and token == "exists" and not arguments:
                    # An existence read of one whole producer block is never NULL.
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL,
                    )
                elif role == "scalar" and token == "scalar" and len(arguments) == 1:
                    # A scalar read is its column's type; no row reads NULL.
                    typed = ValueType(
                        arguments[0].resolved_type, EffectiveNullability.NULLABLE
                    )
                elif (
                    role == "relation_membership"
                    and token in {"in", "not_in"}
                    and len(arguments) == 1
                ):
                    # Three-valued membership in a whole producer block's one
                    # column is conservatively nullable.
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NULLABLE,
                    )
                elif role == "cast" and token == "int_to_float" and len(arguments) == 1:
                    error = (
                        None
                        if arguments[0].resolved_type.name == "Int"
                        else "cast operand"
                    )
                    typed = ValueType(
                        ResolvedType("Float", TypeKind.BUILTIN),
                        arguments[0].nullability,
                    )
                elif role == "scalar_call":
                    from pietto.semantic.catalog import BUILTIN_FUNCTIONS

                    if token in {"coalesce", "nullif"}:
                        error = (
                            None
                            if (
                                len(arguments) >= 2
                                if token == "coalesce"
                                else len(arguments) == 2
                            )
                            and all(
                                item.resolved_type == arguments[0].resolved_type
                                for item in arguments
                            )
                            else "common call operands"
                        )
                        nullability = (
                            EffectiveNullability.NON_NULL
                            if token == "coalesce"
                            and any(
                                item.nullability is EffectiveNullability.NON_NULL
                                for item in arguments
                            )
                            else EffectiveNullability.UNKNOWN
                            if token == "coalesce"
                            and any(
                                item.nullability is EffectiveNullability.UNKNOWN
                                for item in arguments
                            )
                            else EffectiveNullability.NULLABLE
                            if token == "coalesce"
                            else EffectiveNullability.NULLABLE
                            if arguments[0].nullability is EffectiveNullability.NON_NULL
                            else arguments[0].nullability
                        )
                        typed = ValueType(arguments[0].resolved_type, nullability)
                    else:
                        signature = BUILTIN_FUNCTIONS.get(token)
                        special = token in {"sign", "year", "month", "day"}
                        error = (
                            None
                            if token == "sign"
                            and len(arguments) == 1
                            and arguments[0].resolved_type.name in {"Int", "Decimal"}
                            else None
                            if token in {"year", "month", "day"}
                            and len(arguments) == 1
                            and arguments[0].resolved_type.name in {"Date", "Timestamp"}
                            else "scalar call signature"
                            if signature is None
                            or len(arguments) != len(signature.parameter_types)
                            or any(
                                argument.resolved_type.name != expected
                                for argument, expected in zip(
                                    arguments, signature.parameter_types, strict=True
                                )
                            )
                            else None
                        )
                        typed = ValueType(
                            ResolvedType(
                                "Int"
                                if special
                                else "<unknown>"
                                if signature is None
                                else signature.return_type,
                                TypeKind.BUILTIN
                                if special or signature is not None
                                else TypeKind.UNKNOWN,
                            ),
                            EffectiveNullability.UNKNOWN
                            if signature is None and not special
                            else max(
                                (item.nullability for item in arguments),
                                key=lambda item: (
                                    "non_null",
                                    "unknown",
                                    "nullable",
                                ).index(item.value),
                            ),
                        )
                else:
                    raise CompiledError("COMPILED_OPERATOR")
                if error is not None or typed != declared(get("logical")):
                    raise CompiledError("COMPILED_OPERATOR_TYPE")
                if role == "unary":
                    literal_value = facts[operands[0]].value
                    if type(literal_value) in (int, float):
                        value = -literal_value if token == "-" else +literal_value
                input_facts = tuple(facts[child] for child in operands)
                if physical_required:
                    inputs = tuple(item.require_realization() for item in input_facts)
                    nullable = physical.NULLABILITY[typed.nullability]
                    tag = typed.resolved_type.name
                    problem = None
                    if role == "scalar_call":
                        from pietto.ir.model import SymbolId, SymbolNamespace

                        realized, problem = physical.resolved_scalar_call_realization(
                            family,
                            SymbolId(SymbolNamespace.CALLABLE, token),
                            tag,
                            nullable,
                            inputs,
                        )
                    elif role == "conditional":
                        realized, problem = physical.resolved_conditional_realization(
                            family, tag, nullable, inputs
                        )
                    elif role == "membership":
                        realized, problem = physical.resolved_membership_realization(
                            family, tag, nullable, inputs
                        )
                    elif role == "cast":
                        realized, problem = physical.resolved_cast_realization(
                            family, tag, nullable, inputs[0]
                        )
                    elif role == "between":
                        realized, problem = physical.resolved_between_realization(
                            family, tag, nullable, inputs
                        )
                    elif role in {"unary", "not"} and token == "not":
                        realized = physical._bool(family, nullable)
                    elif role == "binary":
                        realized, problem = physical.resolved_binary_realization(
                            family,
                            token,
                            tag,
                            nullable,
                            *inputs,
                            direct_decimal_sources=all(
                                item.origin == "field" for item in input_facts
                            ),
                            float_values=(
                                tuple(item.value for item in input_facts)
                                if all(
                                    item.origin == "literal"
                                    and type(item.value) is float
                                    and math.isfinite(item.value)
                                    for item in input_facts
                                )
                                else None
                            ),
                        )
                    elif role == "comparison":
                        realized, problem = (
                            physical.resolved_like_realization(
                                family, tag, nullable, *inputs
                            )
                            if token in ("like", "not like")
                            else physical.resolved_comparison_realization(
                                family, tag, nullable, *inputs, operator=token
                            )
                        )
                    elif role in {"null_test", "exists"}:
                        realized = physical._bool(family, False)
                    elif role == "scalar":
                        realized = physical.scalar_read_realization(inputs[0])
                    elif role == "relation_membership":
                        realized = physical._bool(family, nullable)
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
                            (value, value)
                            if tag == "Int" and type(value) is int
                            else None,
                        )
                    else:
                        inner = inputs[0]
                        interval = physical.proven_int_bounds(inner)
                        if tag != "Int" or interval is None:
                            raise CompiledError("COMPILED_UNARY_DOMAIN")
                        low, high = (
                            (-interval[1], -interval[0]) if token == "-" else interval
                        )
                        storage = physical._arithmetic_storage(family, inner, inner)
                        realized = physical._checked_int(storage, low, high, nullable)
                        if realized is None and inner.binding:
                            realized = physical.deferred_int(storage, nullable)
                        elif realized is not None:
                            realized = replace(realized, binding=inner.binding)
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
    if set(facts) != {
        r.address for r in records.values() if r.address.kind in scalar_kinds
    }:
        raise CompiledError("COMPILED_NULL_CONTEXT")
    for record in records.values():
        if (
            record.address.kind != "expression_block_use"
            or records[record.get("operation")].get("operator")[0]
            != "relation_membership"
        ):
            continue
        # A membership read pairs its left value with its producer's one
        # column under the literal-list type and carrier rules of emission.
        columns = tuple(
            r.get("source")
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == record.get("producer")
        )
        operation = records[record.get("operation")]
        left = facts[operation.get("operands")[0]]
        if (
            len(columns) != 1
            or left.value_type.resolved_type
            != facts[columns[0]].value_type.resolved_type
        ):
            raise CompiledError("COMPILED_OPERATOR_TYPE")
        if operation.address in executable:
            realized, problem = physical.resolved_membership_realization(
                family,
                "Bool",
                True,
                (left.require_realization(), facts[columns[0]].require_realization()),
            )
            if realized is None or problem is not None:
                raise CompiledError("COMPILED_PHYSICAL_DOMAIN")
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
        parameters,
    )


def verify_compiled_semantics(value):
    """Independently inspect derived facts; never invoke their constructor."""
    import json
    from pietto._project import project_sql_emission_rows as physical
    from pietto._project.project_compiled_schema import Address, scalar_read_port
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
        resolved_comparison_value_type,
        resolved_like_value_type,
    )
    from pietto.semantic.model import (
        EffectiveNullability,
        ResolvedType,
        TypeKind,
        ValueType,
        ValueTypeKind,
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
                declaration.let_position,
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
    declared_parameters = tuple(
        r for r in records.values() if r.address.kind == "parameter"
    )
    need(
        value.parameters is None
        or (
            type(value.parameters) is tuple
            and len(value.parameters) == len(declared_parameters)
            and all(
                r.get("nullable") if v is None else value_valid(r.get("tag"), v, family)
                for r, v in zip(declared_parameters, value.parameters, strict=True)
            )
        ),
        "SEMANTIC_BINDING",
    )
    bound_parameters = (
        None
        if value.parameters is None
        else dict(
            zip(
                (r.address for r in declared_parameters),
                value.parameters,
                strict=True,
            )
        )
    )
    # A window count parameter, against the emission verifier's own interval.
    from pietto._project.project_sql_emission_verification import (
        _COUNT_LOWER,
        _COUNT_STORAGE,
        _COUNT_UPPER,
    )

    count_roles = {
        address: role
        for r in records.values()
        if r.address.kind == "window_value"
        for role, address in r.get("arguments")
        if role in _COUNT_LOWER and address.kind == "parameter_read"
    }
    null_parents = {}
    for record in records.values():
        if record.address.kind != "operation":
            continue
        for position, operand in enumerate(record.get("operands")):
            if operand.kind == "null_literal":
                null_parents.setdefault(operand, []).append((record, position))
    expected_records = tuple(
        r
        for r in records.values()
        if r.address.kind
        in {
            "field",
            "port",
            "read",
            "literal",
            "null_literal",
            "parameter_read",
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
        if address.kind == "null_literal":
            continue
        stack = [(address, False)]
        while stack:
            current, returning = stack.pop()
            if current in checked:
                continue
            record, actual = records[current], by_address[current]
            kind, get = record.address.kind, record.get
            children = (
                tuple(
                    port
                    for port in (scalar_read_port(records, current),)
                    if port is not None
                )
                if kind == "operation" and get("operator") == ("scalar", "scalar")
                else get("operands")
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
                stack.extend(
                    (c, False)
                    for c in reversed(
                        tuple(
                            sorted(
                                children,
                                key=lambda child: child.kind == "null_literal",
                            )
                        )
                    )
                )
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
                    realization = physical.source_realization(
                        Realization(
                            name,
                            expected["storage"],
                            expected["nullable"],
                            expected["domain"],
                        )
                    )
                    if realization is None:
                        raise ValueError("COMPILED_SEMANTIC_FIELD_DOMAIN")
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
                        (expected_value, expected_value)
                        if get("tag") == "Int" and type(expected_value) is int
                        else None,
                    )
                else:
                    realization = None
            elif kind == "parameter_read":
                origin = "parameter"
                declaration = records[get("parameter")]
                need(declaration.address.kind == "parameter", "SEMANTIC_PARAMETER")
                typed = ValueType(
                    ResolvedType(declaration.get("tag"), TypeKind.BUILTIN),
                    EffectiveNullability.NULLABLE
                    if declaration.get("nullable")
                    else EffectiveNullability.NON_NULL,
                )
                if not physical_required:
                    realization = None
                elif current in count_roles:
                    need(
                        declaration.get("tag") == "Int"
                        and declaration.get("nullable") is False,
                        "SEMANTIC_WINDOW_COUNT",
                    )
                    low = _COUNT_LOWER[count_roles[current]]
                    high = _COUNT_UPPER[family]
                    if bound_parameters is not None:
                        bound_value = bound_parameters[declaration.address]
                        need(
                            type(bound_value) is int and low <= bound_value <= high,
                            "SEMANTIC_WINDOW_COUNT",
                        )
                        low = high = bound_value
                    realization = physical.Realization(
                        "Int",
                        {"kind": _COUNT_STORAGE[family]},
                        False,
                        {"kind": "int_range", "min": str(low), "max": str(high)},
                        (low, high),
                        binding=bound_parameters is None,
                        obligation=None
                        if bound_parameters is not None
                        else "structural_count_interval",
                    )
                else:
                    realization = physical.parameter_realization(
                        family,
                        declaration.get("tag"),
                        declaration.get("nullable"),
                        bound=bound_parameters is not None,
                        value=None
                        if bound_parameters is None
                        else bound_parameters[declaration.address],
                    )
            elif kind == "null_literal":
                site = records[get("site")]
                need(site.get("reason") == "contextual_typed_null", "SEMANTIC_NULL")
                candidates = []
                for parent, position in null_parents.get(current, ()):
                    role, token = parent.get("operator")
                    parent_operands = parent.get("operands")
                    if role == "conditional" and position == 1:
                        candidates.append("Bool")
                    elif role == "conditional" and position in (0, 2):
                        sibling = parent_operands[2 if position == 0 else 0]
                        if sibling in by_address:
                            candidates.append(by_address[sibling].value_type)
                    elif role in {"membership", "scalar_call"} and (
                        role == "membership" or token in {"coalesce", "nullif"}
                    ):
                        candidates.extend(
                            by_address[operand].value_type
                            for operand in parent_operands
                            if operand != current and operand in by_address
                        )
                    elif role == "relation_membership" and position == 0:
                        # A bare NULL left value takes the read column's type.
                        candidates.extend(
                            by_address[port.address].value_type
                            for use in records.values()
                            if use.address.kind == "expression_block_use"
                            and use.get("operation") == parent.address
                            for port in records.values()
                            if port.address.kind == "port"
                            and port.get("owner") == use.get("producer")
                        )
                    elif role == "scalar_call":
                        from pietto.semantic.catalog import BUILTIN_FUNCTIONS

                        signature = BUILTIN_FUNCTIONS.get(token)
                        if signature is not None and position < len(
                            signature.parameter_types
                        ):
                            candidates.append(signature.parameter_types[position])
                resolved = []
                for candidate in candidates:
                    if isinstance(candidate, str):
                        if candidate in {"Int|Decimal", "T"}:
                            continue
                        candidate = ValueType(
                            ResolvedType(candidate, TypeKind.BUILTIN),
                            EffectiveNullability.NULLABLE,
                        )
                    if candidate.kind is ValueTypeKind.KNOWN:
                        resolved.append(candidate.resolved_type)
                need(
                    bool(resolved)
                    and all(item == resolved[0] for item in resolved[1:]),
                    "SEMANTIC_NULL",
                )
                typed = ValueType(resolved[0], EffectiveNullability.NULLABLE)
                origin = "literal"
                realization = (
                    Realization(
                        typed.resolved_type.name,
                        {"kind": "typed_null"},
                        True,
                        {"kind": "typed_null"},
                    )
                    if physical_required
                    else None
                )
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
                            else windowing.BINDING_DEFAULT
                            if type(defaults[0]) is windowing.ParameterStatic
                            else str(defaults[0])
                        )
                        # A parameter value is its own anchor (a MySQL SIGNED
                        # anchor reads like a literal), never a column origin.
                        parameter_value = reads[0].kind == "parameter_read"
                        realization = resolved_window_value_result(
                            family,
                            argument.realization,
                            (
                                "literal"
                                if family == "mysql"
                                and argument.value_type.resolved_type.name == "Int"
                                else "unsupported"
                            )
                            if parameter_value
                            else argument.origin,
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
                if kind == "read" and get("role") == "capture":
                    typed, realization = _captured(records, current, typed, realization)
                type_parameters = inputs[0].parameters
                introduction, nulling = inputs[0].introduction, inputs[0].nulling
            else:
                operator = get("operator")
                role, token = operator
                if role in {"unary", "not"}:
                    origin = (
                        "literal" if inputs[0].origin == "literal" else "unsupported"
                    )
                    typed, problem = resolved_unary_value_type(
                        token, inputs[0].value_type
                    )
                elif role == "binary":
                    typed, problem = resolved_binary_value_type(
                        token, *(i.value_type for i in inputs)
                    )
                elif role == "comparison":
                    typed, problem = (
                        resolved_like_value_type(*(i.value_type for i in inputs))
                        if token in ("like", "not like")
                        else resolved_comparison_value_type(
                            *(i.value_type for i in inputs)
                        )
                    )
                elif (
                    role == "null_test"
                    and token in ("is_null", "is_not_null")
                    and len(inputs) == 1
                ):
                    problem = None
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL,
                    )
                elif role == "between" and len(inputs) == 3:
                    checks = tuple(
                        resolved_comparison_value_type(
                            inputs[0].value_type, item.value_type
                        )
                        for item in inputs[1:]
                    )
                    problem = next((item for _, item in checks if item), None)
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.UNKNOWN,
                    )
                elif role == "conditional" and len(inputs) == 3:
                    branches = (inputs[0].value_type, inputs[2].value_type)
                    problem = (
                        None
                        if inputs[1].value_type.resolved_type.name == "Bool"
                        and branches[0].resolved_type == branches[1].resolved_type
                        else "conditional operands"
                    )
                    typed = ValueType(
                        branches[0].resolved_type,
                        max(
                            (item.nullability for item in branches),
                            key=lambda item: ("non_null", "unknown", "nullable").index(
                                item.value
                            ),
                        ),
                    )
                elif role == "membership" and inputs:
                    problem = (
                        None
                        if all(
                            item.value_type.resolved_type
                            == inputs[0].value_type.resolved_type
                            for item in inputs
                        )
                        else "membership operands"
                    )
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL
                        if len(inputs) == 1
                        else max(
                            (item.value_type.nullability for item in inputs),
                            key=lambda item: ("non_null", "unknown", "nullable").index(
                                item.value
                            ),
                        ),
                    )
                elif role == "exists" and token == "exists" and not inputs:
                    problem = None
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NON_NULL,
                    )
                elif (
                    role == "scalar"
                    and token == "scalar"
                    and len(inputs) == 1
                    and not get("operands")
                ):
                    problem = None
                    typed = ValueType(
                        inputs[0].value_type.resolved_type,
                        EffectiveNullability.NULLABLE,
                    )
                elif (
                    role == "relation_membership"
                    and token in {"in", "not_in"}
                    and len(inputs) == 1
                ):
                    problem = None
                    typed = ValueType(
                        ResolvedType("Bool", TypeKind.BUILTIN),
                        EffectiveNullability.NULLABLE,
                    )
                elif role == "cast" and token == "int_to_float" and len(inputs) == 1:
                    problem = (
                        None
                        if inputs[0].value_type.resolved_type.name == "Int"
                        else "cast operand"
                    )
                    typed = ValueType(
                        ResolvedType("Float", TypeKind.BUILTIN),
                        inputs[0].value_type.nullability,
                    )
                elif role == "scalar_call":
                    from pietto.semantic.catalog import BUILTIN_FUNCTIONS

                    arguments = tuple(item.value_type for item in inputs)
                    if token in {"coalesce", "nullif"}:
                        problem = (
                            None
                            if (
                                len(arguments) >= 2
                                if token == "coalesce"
                                else len(arguments) == 2
                            )
                            and all(
                                item.resolved_type == arguments[0].resolved_type
                                for item in arguments
                            )
                            else "common call operands"
                        )
                        nullability = (
                            EffectiveNullability.NON_NULL
                            if token == "coalesce"
                            and any(
                                item.nullability is EffectiveNullability.NON_NULL
                                for item in arguments
                            )
                            else EffectiveNullability.UNKNOWN
                            if token == "coalesce"
                            and any(
                                item.nullability is EffectiveNullability.UNKNOWN
                                for item in arguments
                            )
                            else EffectiveNullability.NULLABLE
                            if token == "coalesce"
                            else EffectiveNullability.NULLABLE
                            if arguments[0].nullability is EffectiveNullability.NON_NULL
                            else arguments[0].nullability
                        )
                        typed = ValueType(arguments[0].resolved_type, nullability)
                    else:
                        signature = BUILTIN_FUNCTIONS.get(token)
                        special = token in {"sign", "year", "month", "day"}
                        problem = (
                            None
                            if token == "sign"
                            and len(arguments) == 1
                            and arguments[0].resolved_type.name in {"Int", "Decimal"}
                            else None
                            if token in {"year", "month", "day"}
                            and len(arguments) == 1
                            and arguments[0].resolved_type.name in {"Date", "Timestamp"}
                            else "scalar call signature"
                            if signature is None
                            or len(arguments) != len(signature.parameter_types)
                            or any(
                                argument.resolved_type.name != expected
                                for argument, expected in zip(
                                    arguments, signature.parameter_types, strict=True
                                )
                            )
                            else None
                        )
                        typed = ValueType(
                            ResolvedType(
                                "Int"
                                if special
                                else "<unknown>"
                                if signature is None
                                else signature.return_type,
                                TypeKind.BUILTIN
                                if special or signature is not None
                                else TypeKind.UNKNOWN,
                            ),
                            EffectiveNullability.UNKNOWN
                            if signature is None and not special
                            else max(
                                (item.nullability for item in arguments),
                                key=lambda item: (
                                    "non_null",
                                    "unknown",
                                    "nullable",
                                ).index(item.value),
                            ),
                        )
                else:
                    problem = "operator"
                    typed = ValueType(
                        ResolvedType("<unknown>", TypeKind.UNKNOWN),
                        EffectiveNullability.UNKNOWN,
                    )
                need(problem is None, "SEMANTIC_TYPE")
                if role == "unary" and inputs and type(inputs[0].value) in (int, float):
                    expected_value = (
                        -inputs[0].value if token == "-" else +inputs[0].value
                    )
                if physical_required:
                    if role == "scalar_call":
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )
                        from pietto.ir.model import SymbolId, SymbolNamespace

                        realization, problem = (
                            physical.resolved_scalar_call_realization(
                                family,
                                SymbolId(SymbolNamespace.CALLABLE, token),
                                typed.resolved_type.name,
                                NULLABILITY[typed.nullability],
                                tuple(item.realization for item in inputs),
                            )
                        )
                        need(
                            realization is not None and problem is None,
                            "SEMANTIC_DOMAIN",
                        )
                    elif role == "conditional":
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )

                        realization, problem = (
                            physical.resolved_conditional_realization(
                                family,
                                typed.resolved_type.name,
                                NULLABILITY[typed.nullability],
                                tuple(item.realization for item in inputs),
                            )
                        )
                        need(
                            realization is not None and problem is None,
                            "SEMANTIC_DOMAIN",
                        )
                    elif role == "membership":
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )

                        realization, problem = physical.resolved_membership_realization(
                            family,
                            typed.resolved_type.name,
                            NULLABILITY[typed.nullability],
                            tuple(item.realization for item in inputs),
                        )
                        need(
                            realization is not None and problem is None,
                            "SEMANTIC_DOMAIN",
                        )
                    elif role == "cast":
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )

                        realization, problem = physical.resolved_cast_realization(
                            family,
                            typed.resolved_type.name,
                            NULLABILITY[typed.nullability],
                            inputs[0].realization,
                        )
                        need(
                            realization is not None and problem is None,
                            "SEMANTIC_DOMAIN",
                        )
                    elif role == "between":
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )

                        realization, problem = physical.resolved_between_realization(
                            family,
                            typed.resolved_type.name,
                            NULLABILITY[typed.nullability],
                            tuple(item.realization for item in inputs),
                        )
                        need(
                            realization is not None and problem is None,
                            "SEMANTIC_DOMAIN",
                        )
                    elif role in {"not", "exists", "relation_membership"}:
                        from pietto._project import (
                            project_sql_emission_rows as physical,
                        )

                        realization = physical._bool(
                            family, NULLABILITY[typed.nullability]
                        )
                    elif role == "scalar":
                        read = inputs[0].require_realization()
                        realization = Realization(
                            read.tag,
                            read.storage,
                            True,
                            read.domain,
                            read.proven_int_range,
                        )
                    elif role == "unary" and type(inputs[0].value) in (int, float):
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
                            (expected_value, expected_value)
                            if typed.resolved_type.name == "Int"
                            and type(expected_value) is int
                            else None,
                        )
                    else:
                        realization = resolved_row_realization(
                            family,
                            role,
                            token,
                            typed.resolved_type.name,
                            NULLABILITY[typed.nullability],
                            tuple(i.realization for i in inputs),
                            direct_decimal_sources=all(
                                item.origin == "field" for item in inputs
                            ),
                            float_values=(
                                tuple(item.value for item in inputs)
                                if all(
                                    item.origin == "literal"
                                    and type(item.value) is float
                                    and math.isfinite(item.value)
                                    for item in inputs
                                )
                                else None
                            ),
                        )
                else:
                    realization = None
            if kind == "operation":
                need(
                    get("logical")
                    == (typed.resolved_type.name, typed.nullability.value),
                    "SEMANTIC_LOGICAL",
                )
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
                    and type(observed.nullable) is type(realization.nullable)
                    and type(observed.proven_int_range)
                    is type(realization.proven_int_range),
                    "SEMANTIC_REALIZATION",
                )
                # The proven Int range feeds every later arithmetic proof.
                need(
                    observed.tag == realization.tag
                    and observed.binding is realization.binding
                    and observed.obligation == realization.obligation
                    and observed.proven_int_range == realization.proven_int_range
                    and all(type(v) is int for v in observed.proven_int_range or ())
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
    need(checked == set(by_address), "SEMANTIC_NULL")
    for record in records.values():
        if (
            record.address.kind != "expression_block_use"
            or records[record.get("operation")].get("operator")[0]
            != "relation_membership"
        ):
            continue
        # Membership pairs the left value with the producer's one column.
        columns = tuple(
            by_address[r.get("source")]
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == record.get("producer")
        )
        operation = records[record.get("operation")]
        left = by_address[operation.get("operands")[0]]
        need(
            len(columns) == 1
            and left.value_type.resolved_type == columns[0].value_type.resolved_type,
            "SEMANTIC_TYPE",
        )
        if operation.address in executable:
            pair = (left.realization, columns[0].realization)
            need(all(type(r) is Realization for r in pair), "SEMANTIC_DOMAIN")
            realization, problem = physical.resolved_membership_realization(
                family, "Bool", True, pair
            )
            need(realization is not None and problem is None, "SEMANTIC_DOMAIN")
    expected_retention = tuple(
        (r.address, project_joined_row_filter._SQL_ROW_RETENTION_EFFECTS)
        for r in records.values()
        if r.address.kind == "row" and r.get("predicate") is not None
    )
    need(value.retention == expected_retention, "SEMANTIC_RETENTION")
    return value
