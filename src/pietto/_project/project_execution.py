"""Private execution authority over already verified live compiler artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import threading
from typing import Any

from pietto._project.project_result_contract import (
    build_result_contract,
    verify_result_contract,
)
from pietto._project.project_result_binding import _columns
from pietto._project.project_sql_emission import EmissionArtifact
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission
from pietto._project.project_sql_emission_rows import field_realization
from pietto._project.project_execution_source import (
    RetainedSourceRequirement,
    requirement_state,
    verify_requirement,
)

__all__: tuple[str, ...] = ()


class ExecutionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class PostgresAccess:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    sslmode: str = "require"


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    batch_rows: int = 256
    batch_bytes: int = 1024 * 1024
    max_rows: int = 1048576
    max_bytes: int = 64 * 1024 * 1024
    seconds: float = 20.0


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionRequest:
    artifact: EmissionArtifact = field(repr=False)
    contract: Any = field(repr=False)
    access: PostgresAccess = field(repr=False)
    limits: ExecutionLimits
    isolation: str
    source_requirement: RetainedSourceRequirement | None = field(
        default=None, repr=False
    )
    binding: Any = field(default=None, repr=False)
    projection: Any = field(default=None, repr=False)
    output: Any = field(default=None, repr=False)


def verify_execution_request(request) -> None:
    _verify_execution_structure(request)


def _verify_execution_structure(request, *, guarded=None) -> None:
    from pietto._project.project_guard_preparation import GuardedArtifact

    artifact = request.artifact if type(request) is ExecutionRequest else None
    allowed_artifact = type(artifact) is EmissionArtifact or (
        guarded is not None
        and type(artifact) is GuardedArtifact
        and artifact.guard_scope is guarded.scope
    )
    if (
        type(request) is not ExecutionRequest
        or not allowed_artifact
        or type(request.access) is not PostgresAccess
        or type(request.limits) is not ExecutionLimits
    ):
        raise ExecutionError("EXECUTION_REQUEST")
    if guarded is None:
        view = inspect_project_sql_emission(request.artifact, request.artifact.request)
    else:
        from pietto._project.project_guard_preparation import inspect_pending

        view = inspect_pending(guarded, request.artifact)
        if request.output is None or request.output.guarded is not guarded:
            raise ExecutionError("GUARD_EXECUTION_OUTPUT")
    if view.request.family != "postgres":
        raise ExecutionError("EXECUTION_TARGET")
    verify_result_contract(request.contract, view.request.verification)
    # Inspect the entire verified inventory before restricting the S03 producer
    # shape. No winning obligation or hidden/filter-based exemption is allowed.
    if guarded is None and any(
        item.downstream_enforcement_required
        for item in view.request.plan.single_matches
    ):
        raise ExecutionError("UNFULFILLED_RUNTIME_OBLIGATION")
    if request.binding is not None:
        from pietto._project.project_execution_binding_verification import (
            verify_binding,
        )

        verify_binding(request.binding)
        if request.binding.artifact is not request.artifact:
            raise ExecutionError("EXECUTION_BINDING_ROOT")
    elif request.projection is not None:
        raise ExecutionError("EXECUTION_BINDING_ROOT")
    columns = _columns(
        request.contract, request.artifact, request.projection, request.output
    )
    if request.output is not None:
        # _columns already verified the complete output and its exact roots.
        if request.output.binding is not request.binding:
            raise ExecutionError("EXECUTION_BINDING_ROOT")
    else:
        realizations = tuple(field_realization(c.source_field) for c in columns)
        if any(value is None or value.tag != "Int" for value in realizations):
            raise ExecutionError("EXECUTION_REALIZATION_NOT_DELIVERED")
    if (
        request.output is None
        and request.binding is None
        and (request.artifact.parameter_uses or request.artifact.fixed_values)
    ):
        # The existing lawful producer path is field-only. Nonempty native
        # literal uses currently require an unsupported producer shape, not SQL
        # interpolation or a speculative S04 rebinding implementation.
        raise ExecutionError("EXECUTION_PRODUCER_NOT_DELIVERED")
    a = request.access
    if (
        any(
            type(v) is not str or not v or "\0" in v
            for v in (a.host, a.database, a.user, a.password)
        )
        or type(a.port) is not int
        or not 1 <= a.port <= 65535
    ):
        raise ExecutionError("EXECUTION_ACCESS")
    if a.sslmode not in ("require", "disable") or (
        a.sslmode == "disable" and a.host not in ("127.0.0.1", "::1")
    ):
        raise ExecutionError("EXECUTION_ACCESS_PROFILE")
    if request.isolation not in ("stable", "serializable"):
        raise ExecutionError("EXECUTION_ISOLATION")
    verify_execution_limits(request.limits)
    verify_requirement(request.source_requirement, view.request.sources)


def verify_execution_limits(limits):
    if type(limits) is not ExecutionLimits:
        raise ExecutionError("EXECUTION_LIMITS")
    if (
        any(
            type(v) is not int or v <= 0
            for v in (
                limits.batch_rows,
                limits.batch_bytes,
                limits.max_rows,
                limits.max_bytes,
            )
        )
        or limits.batch_rows > 4096
        or limits.batch_bytes > 8 * 1024 * 1024
        or type(limits.seconds) not in (int, float)
        or not math.isfinite(limits.seconds)
        or limits.seconds <= 0
        or limits.seconds > threading.TIMEOUT_MAX
    ):
        raise ExecutionError("EXECUTION_LIMITS")


def prepare_execution(
    artifact,
    access,
    *,
    limits=ExecutionLimits(),
    isolation="stable",
    source_requirement=None,
    binding=None,
    output=None,
):
    if type(artifact) is not EmissionArtifact:
        raise ExecutionError("EXECUTION_ARTIFACT")
    contract = (
        output.contract
        if output is not None
        else build_result_contract(
            artifact.request.verification,
            scalar_meaning=artifact.request.scalar_meaning,
        )
    )
    projection = None
    if binding is not None and output is None:
        from pietto._project.project_sql_emission_ast import SQLRowQuery
        from pietto._project.project_execution_projection import prepare_projection

        if type(artifact.ast) is SQLRowQuery:
            projection = prepare_projection(artifact)
    request = ExecutionRequest(
        artifact,
        contract,
        access,
        limits,
        isolation,
        source_requirement,
        binding,
        projection,
        output,
    )
    verify_execution_request(request)
    return request


def prepare_bound_execution(binding, access, **options):
    from pietto._project.project_execution_binding_verification import verify_binding

    verify_binding(binding)
    return prepare_execution(binding.artifact, access, binding=binding, **options)


def execution_arguments(request):
    verify_execution_request(request)
    if request.binding is not None:
        return request.binding.arguments
    if request.output is not None:
        from pietto._project.project_execution_binding_verification import (
            native_arguments,
        )

        return native_arguments(
            request.artifact,
            tuple(
                s.site.position.literal.value
                for s in request.artifact.request.plan.literal_slots
            ),
        )
    return ()


def request_state(request):
    from pietto._project.project_execution_binding_verification import binding_state

    a = request.access
    limits = request.limits
    return (
        request.binding,
        None if request.binding is None else binding_state(request.binding),
        request.projection,
        request.output,
        request.artifact,
        request.artifact.request,
        request.artifact.rendered.sql,
        request.contract,
        request.contract.shape,
        a,
        (a.host, a.port, a.database, a.user, a.password, a.sslmode),
        limits,
        (
            limits.batch_rows,
            limits.batch_bytes,
            limits.max_rows,
            limits.max_bytes,
            limits.seconds,
        ),
        request.isolation,
        request.source_requirement,
        requirement_state(request.source_requirement),
    )


@dataclass(frozen=True, slots=True)
class ExecutionFailure:
    phase: str
    kind: str
    sqlstate: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    attempt: str
    source: str
    transaction: str
    delivery: str
    cleanup: str
    rows: int
    batches: int
    bytes: int
    primary: ExecutionFailure | None
    cleanup_failures: tuple[ExecutionFailure, ...]
    cancel_requested: bool
    cancel_sent: bool
    cancel_observed: bool
