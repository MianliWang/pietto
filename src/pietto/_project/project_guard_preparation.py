"""Private pending SQL structure; it is never unconditional execution authority."""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_sql_emission_contract import (
    PreparedEmission,
    PreparationFailure,
    prepare_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import (
    SQLJoinQuery,
    build_row_requirements,
    emission_blockers,
    realize_rows,
    row_parameter_leaves,
)
from pietto._project.project_sql_emission import EmissionArtifact, realize_project_sql
from pietto._project.project_sql_emission_rendering import (
    render_join_sql,
    render_row_sql,
)
from pietto._project.project_sql_plan_joins import ProjectSQLSingleMatch
from pietto._project.project_sql_plan_requirements import ProjectSQLSingleMatchReport
from pietto._project.project_single_match import (
    ProjectSingleMatchState,
    ProjectSingleMatchUnit,
)

__all__: tuple[str, ...] = ()


class GuardPreparationError(ValueError):
    def __init__(self, category, *, blockers=(), diagnostics=()):
        super().__init__(category)
        self.blockers = blockers
        self.diagnostics = diagnostics


@dataclass(frozen=True, slots=True, eq=False)
class PendingGuardScope:
    request: PreparedEmission = field(repr=False)
    obligations: tuple = field(repr=False)
    enforcement: tuple = field(repr=False)
    _accepted: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False, repr=False)
class GuardedArtifact(EmissionArtifact):
    """Distinct private carrier; old exact-type artifact consumers reject it."""

    guard_scope: PendingGuardScope = field(kw_only=True, repr=False)

    def __repr__(self):
        return "GuardedArtifact(pending_runtime_applicability=True)"


@dataclass(frozen=True, slots=True, eq=False)
class GuardedPreparation:
    scope: PendingGuardScope = field(repr=False)
    artifact: EmissionArtifact = field(repr=False)


def verify_scope(scope, request):
    from pietto._project.project_sql_emission_verification import prepared_current

    if (
        type(scope) is not PendingGuardScope
        or scope.request is not request
        or not prepared_current(request)
        or scope._accepted != request._accepted
        or scope.obligations is not request.plan.single_matches
        or scope.enforcement is not request.report.report.summary.enforcement_required
    ):
        raise GuardPreparationError("GUARD_PREPARATION_ROOT")
    for obligation in scope.obligations:
        if (
            type(obligation) is not ProjectSQLSingleMatch
            or obligation.assessment.state is ProjectSingleMatchState.INVALID
            or obligation.request.unit
            is not ProjectSingleMatchUnit.ACTUAL_MATCHED_BAG_OCCURRENCE
            or not obligation.joins
            or len(obligation.joins) != len(obligation.input_pairs)
        ):
            raise GuardPreparationError("GUARD_OBLIGATION_KIND")
    expected = tuple(
        item for item in scope.obligations if item.downstream_enforcement_required
    )
    if len(expected) != len(scope.enforcement) or any(
        type(record) is not ProjectSQLSingleMatchReport
        or record.original is not original
        or record.enforcement_required is not True
        or record.state is not ProjectSingleMatchState.LEGAL_UNPROVED
        for record, original in zip(scope.enforcement, expected, strict=True)
    ):
        raise GuardPreparationError("GUARD_ENFORCEMENT_DENOMINATOR")


def structural_blockers(scope, request):
    """Only this exact pending inventory is deferred, in its original order."""
    verify_scope(scope, request)
    blockers = emission_blockers(request, _guarded=scope)
    pending = tuple(
        b
        for b in blockers
        if b.code == "PIE-B1006" and b.detail == "original_enforcement_not_fulfilled"
    )
    if len(pending) != len(scope.enforcement) or any(
        b.subject is not obligation.entry.subject
        for b, obligation in zip(pending, scope.enforcement, strict=True)
    ):
        raise GuardPreparationError("GUARD_BLOCKER_DENOMINATOR")
    return tuple(b for b in blockers if not any(b is p for p in pending))


def prepare_guarded(
    verification, contract_bytes, *, target_request=None, scalar_meaning=None
):
    request = prepare_project_sql_emission(
        verification,
        contract_bytes,
        target_request=target_request,
        scalar_meaning=scalar_meaning,
    )
    if type(request) is PreparationFailure:
        raise GuardPreparationError(
            "GUARD_PREPARATION_INPUT",
            blockers=request.blockers,
            diagnostics=request.diagnostics,
        )
    return prepare_guarded_request(request)


def prepare_guarded_request(request):
    from pietto._project.project_sql_emission_verification import prepared_current

    if not prepared_current(request):
        raise GuardPreparationError("GUARD_PREPARATION_ROOT")
    scope = PendingGuardScope(
        request,
        request.plan.single_matches,
        request.report.report.summary.enforcement_required,
        request._accepted,
    )
    blockers = structural_blockers(scope, request)
    if blockers:
        raise GuardPreparationError(
            "GUARD_PREPARATION_BLOCKED",
            blockers=blockers,
            diagnostics=request.verification.completed.diagnostics,
        )
    from pietto._project.project_sql_emission_joins import guarded_path_input

    private_path = any(
        guarded_path_input(scope, request.plan, item)
        for item in request.plan.join_inputs
    )
    if not scope.enforcement and not private_path:
        result = realize_project_sql(request)
        if result.status != "VERIFIED" or result.artifact is None:
            raise GuardPreparationError(
                "GUARD_PREPARATION_BLOCKED", blockers=result.blockers
            )
        artifact = result.artifact
    else:
        # Reuse the original typed realization and renderers. No request is
        # removed, semantic root cloned, or VERIFIED outcome manufactured.
        realized = realize_rows(request, _guarded=scope)
        query: Any = realized.query
        if query is None:
            raise GuardPreparationError(
                "GUARD_PREPARATION_BLOCKED", blockers=realized.problems
            )
        rendered = (
            render_join_sql(query)
            if type(query) is SQLJoinQuery
            else render_row_sql(query)
        )
        original, generated = build_row_requirements(request, query)
        artifact = GuardedArtifact(
            request,
            query,
            rendered,
            original,
            generated,
            request.plan.fixed_envelope.values,
            tuple(leaf.use for leaf in row_parameter_leaves(query)),
            guard_scope=scope,
        )
    preparation = GuardedPreparation(scope, artifact)
    verify_preparation(preparation)
    return preparation


def verify_preparation(preparation):
    from pietto._project.project_sql_emission_verification import (
        _verify_emission_structure,
    )

    if type(preparation) is not GuardedPreparation:
        raise GuardPreparationError("GUARD_PREPARATION_ROOT")
    scope, artifact = preparation.scope, preparation.artifact
    if (
        type(artifact) not in (EmissionArtifact, GuardedArtifact)
        or artifact.request is not scope.request
        or (type(artifact) is GuardedArtifact and artifact.guard_scope is not scope)
    ):
        raise GuardPreparationError("GUARD_PREPARATION_ROOT")
    if structural_blockers(scope, artifact.request):
        raise GuardPreparationError("GUARD_PREPARATION_BLOCKED")
    if _verify_emission_structure(artifact, artifact.request, guarded=scope):
        raise GuardPreparationError("GUARD_PREPARATION_STRUCTURE")
    return scope.obligations


@dataclass(frozen=True, slots=True, eq=False)
class PendingInspection:
    preparation: GuardedPreparation = field(repr=False)
    request: PreparedEmission = field(repr=False)
    columns: tuple = field(repr=False)


def inspect_pending(preparation, artifact):
    verify_preparation(preparation)
    if preparation.artifact is not artifact:
        raise GuardPreparationError("GUARD_PREPARATION_ARTIFACT")
    ast = artifact.ast
    units = getattr(ast, "units", None) or getattr(ast, "bodies", None) or (ast,)
    return PendingInspection(preparation, artifact.request, tuple(units[-1].columns))


def prepare_guarded_output(preparation, *, binding=None):
    from pietto._project.project_result_output import _prepare_output

    verify_preparation(preparation)
    return _prepare_output(preparation.artifact, binding=binding, guarded=preparation)


def prepare_guarded_template(preparation):
    from pietto._project.project_execution_template import (
        ExecutionTemplate,
        ExecutionSlot,
    )
    from pietto._project import project_execution_binding_verification as check

    verify_preparation(preparation)
    artifact = preparation.artifact
    slots = tuple(
        ExecutionSlot(i, s.tag.value, s)
        for i, s in enumerate(artifact.request.plan.literal_slots)
    )
    template = ExecutionTemplate(
        artifact, slots, check.template_state(artifact, slots, preparation), preparation
    )
    check.verify_template(template)
    return template
