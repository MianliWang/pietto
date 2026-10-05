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
from pietto._project.project_sql_emission import (
    EmissionArtifact,
    CompiledEmissionArtifact,
)
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
class MySQLAccess:
    host: str
    port: int
    database: str
    user: str
    password: str = field(repr=False)
    ca_file: str
    account: str
    roles: str = "NONE"
    verify_identity: bool = True
    loopback_tls_exception: bool = False
    transaction_observation: str = "performance_schema_own_transaction"


@dataclass(frozen=True, slots=True, eq=False)
class MySQLDeploymentPremise:
    """Operator commitment from BEFORE acquisition through last remote source use.

    All administrative paths must keep definitions/security stable in these
    schemas. Row data may change. This is an assumption, not proof of compliance.
    Sources/access are exact in-process roots; each attempt still qualifies anew.
    """

    access: MySQLAccess = field(repr=False)
    sources: tuple = field(repr=False)
    schemas: tuple[str, ...]
    basis: str = "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"


@dataclass(frozen=True, slots=True, eq=False)
class PostgresDeploymentPremise:
    """Explicit per-request commitment for the common finite PG profile.

    Its required lifetime includes discovery through the last possible remote
    use. Neither the bundle nor local close establishes operator compliance.
    """

    access: PostgresAccess = field(repr=False)
    sources: tuple = field(repr=False)
    schemas: tuple[str, ...]
    route: str
    profile: str = "finite_pg_v1"
    basis: str = "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"


def postgres_deployment_state(premise):
    if premise is None:
        return None
    if type(premise) is not PostgresDeploymentPremise:
        raise ExecutionError("POSTGRES_DEPLOYMENT_PREMISE_INVALID")
    return (
        premise,
        premise.access,
        premise.sources,
        premise.schemas,
        premise.route,
        premise.profile,
        premise.basis,
    )


def verify_postgres_deployment(request):
    premise = request.postgres_deployment
    postgres_deployment_state(premise)
    if premise is None:
        raise ExecutionError("POSTGRES_DEPLOYMENT_PREMISE_REQUIRED")
    sources = request.artifact.request.sources
    if (
        type(request.access) is not PostgresAccess
        or premise.access is not request.access
        or premise.route != request.route
        or premise.route not in ("postgres_rows", "postgres_adbc")
        or premise.profile != "finite_pg_v1"
        or premise.basis != "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        or type(premise.sources) is not tuple
        or len(premise.sources) != len(sources)
        or any(a is not b for a, b in zip(premise.sources, sources, strict=True))
        or type(premise.schemas) is not tuple
        or not 0 < len(premise.schemas) <= 128
        or any(type(s) is not str or not s or "\0" in s for s in premise.schemas)
        or len(set(premise.schemas)) != len(premise.schemas)
        or any(s.namespace not in premise.schemas for s in sources)
        or any(
            (s.startswith("pg_") and s != "pg_catalog") or s == "information_schema"
            for s in premise.schemas
        )
        or request.postgres_adbc_deployment is not None
        or request.mysql_deployment is not None
    ):
        raise ExecutionError("POSTGRES_DEPLOYMENT_PREMISE_SCOPE")


def postgres_source_premise(request):
    """Return only the request's actually checked route-specific acceptance."""
    if type(request) is ExecutionRequest and request.postgres_deployment is not None:
        verify_postgres_deployment(request)
        return request.postgres_deployment
    verify_postgres_adbc_deployment(request)
    return request.postgres_adbc_deployment


@dataclass(frozen=True, slots=True, eq=False)
class PostgresADBCDeploymentPremise:
    """Operator protection from before discovery through last remote source use.

    Local close/cancel does not end unresolved remote use. Compliance is not
    independently verified; native all-definition exclusion is not claimed.
    """

    access: PostgresAccess = field(repr=False)
    sources: tuple = field(repr=False)
    schemas: tuple[str, ...]
    route: str = "postgres_adbc"
    basis: str = "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"


def postgres_adbc_deployment_state(premise):
    if premise is None:
        return None
    if type(premise) is not PostgresADBCDeploymentPremise:
        raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_INVALID")
    return (
        premise,
        premise.access,
        premise.sources,
        premise.schemas,
        premise.route,
        premise.basis,
    )


def verify_postgres_adbc_deployment(request):
    if type(request) is ExecutionRequest and request.postgres_deployment is not None:
        verify_postgres_deployment(request)
        return
    premise = request.postgres_adbc_deployment
    postgres_adbc_deployment_state(premise)
    if request.route != "postgres_adbc":
        if premise is not None:
            raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")
        return
    if premise is None:
        raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_REQUIRED")
    sources = request.artifact.request.sources
    if (
        type(request.access) is not PostgresAccess
        or premise.access is not request.access
        or type(premise.sources) is not tuple
        or len(premise.sources) != len(sources)
        or any(a is not b for a, b in zip(premise.sources, sources, strict=True))
        or premise.route != "postgres_adbc"
        or premise.basis != "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        or type(premise.schemas) is not tuple
        or not 0 < len(premise.schemas) <= 128
        or any(type(s) is not str or not s or "\0" in s for s in premise.schemas)
        or len(set(premise.schemas)) != len(premise.schemas)
        or any(s.namespace not in premise.schemas for s in sources)
        or any(
            (s.startswith("pg_") and s != "pg_catalog") or s == "information_schema"
            for s in premise.schemas
        )
    ):
        raise ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE")


def deployment_state(premise):
    if premise is None:
        return None
    if type(premise) is not MySQLDeploymentPremise:
        raise ExecutionError("MYSQL_DEPLOYMENT_PREMISE_INVALID")
    return (premise, premise.access, premise.sources, premise.schemas, premise.basis)


def verify_deployment(request, *, required=False):
    premise = request.mysql_deployment
    deployment_state(premise)
    if premise is None:
        if required:
            raise ExecutionError("MYSQL_DEPLOYMENT_PREMISE_REQUIRED")
        return
    sources = request.artifact.request.sources
    if (
        type(request.access) is not MySQLAccess
        or premise.access is not request.access
        or type(premise.sources) is not tuple
        or len(premise.sources) != len(sources)
        or any(a is not b for a, b in zip(premise.sources, sources, strict=True))
        or type(premise.basis) is not str
        or premise.basis != "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        or type(premise.schemas) is not tuple
        or not 0 < len(premise.schemas) <= 128
        or any(type(s) is not str or not s or "\0" in s for s in premise.schemas)
        or len(set(premise.schemas)) != len(premise.schemas)
        or any(s.namespace not in premise.schemas for s in sources)
        or any(
            s in ("mysql", "sys", "information_schema", "performance_schema")
            for s in premise.schemas
        )
    ):
        raise ExecutionError("MYSQL_DEPLOYMENT_PREMISE_SCOPE")


@dataclass(frozen=True, slots=True)
class ExecutionLimits:
    batch_rows: int = 256
    batch_bytes: int = 1024 * 1024
    max_rows: int = 1048576
    max_bytes: int = 64 * 1024 * 1024
    seconds: float = 20.0


@dataclass(frozen=True, slots=True, eq=False)
class ExecutionRequest:
    artifact: EmissionArtifact | CompiledEmissionArtifact = field(repr=False)
    contract: Any = field(repr=False)
    access: PostgresAccess | MySQLAccess = field(repr=False)
    limits: ExecutionLimits
    isolation: str
    source_requirement: RetainedSourceRequirement | None = field(
        default=None, repr=False
    )
    binding: Any = field(default=None, repr=False)
    projection: Any = field(default=None, repr=False)
    output: Any = field(default=None, repr=False)
    mysql_deployment: MySQLDeploymentPremise | None = field(default=None, repr=False)
    route: str = field(default="", kw_only=True)
    postgres_adbc_deployment: PostgresADBCDeploymentPremise | None = field(
        default=None, repr=False, kw_only=True
    )
    postgres_deployment: PostgresDeploymentPremise | None = field(
        default=None, repr=False, kw_only=True
    )


def verify_execution_request(request) -> None:
    _verify_execution_structure(request)


def _verify_execution_structure(request, *, guarded=None) -> None:
    from pietto._project.project_guard_preparation import (
        GuardedArtifact,
        CompiledGuardedArtifact,
    )

    artifact = request.artifact if type(request) is ExecutionRequest else None
    allowed_artifact = type(artifact) in (
        EmissionArtifact,
        CompiledEmissionArtifact,
    ) or (
        guarded is not None
        and type(artifact) in (GuardedArtifact, CompiledGuardedArtifact)
        and isinstance(artifact, (GuardedArtifact, CompiledGuardedArtifact))
        and artifact.guard_scope is guarded.scope
    )
    if (
        type(request) is not ExecutionRequest
        or not allowed_artifact
        or type(request.access) not in (PostgresAccess, MySQLAccess)
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
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    compiled = type(view.request) is CompiledPreparedEmission
    family = "mysql" if type(request.access) is MySQLAccess else "postgres"
    if compiled:
        routes = (
            ("postgres_rows", "postgres_adbc")
            if family == "postgres"
            else ("mysql_rows",)
        )
        if request.route not in routes:
            raise ExecutionError("COMPILED_FRESH_PROFILE_REQUIRED")
        if request.binding is None or request.output is None:
            raise ExecutionError("COMPILED_BINDING_REQUIRED")
        if family == "postgres":
            verify_postgres_deployment(request)
        else:
            if (
                request.postgres_deployment is not None
                or request.postgres_adbc_deployment is not None
            ):
                raise ExecutionError("MYSQL_DEPLOYMENT_PREMISE_SCOPE")
            verify_deployment(request, required=True)
    else:
        if (
            request.postgres_deployment is not None
            or request.route not in ("", "postgres_adbc")
            or (request.route == "postgres_adbc" and family != "postgres")
        ):
            raise ExecutionError("EXECUTION_TARGET")
        verify_postgres_adbc_deployment(request)
    if view.request.family != family:
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
    if type(a) is PostgresAccess:
        if a.sslmode not in ("require", "disable") or (
            a.sslmode == "disable" and a.host not in ("127.0.0.1", "::1")
        ):
            raise ExecutionError("EXECUTION_ACCESS_PROFILE")
    elif type(a) is MySQLAccess:
        if (
            any(
                type(v) is not str or not v or "\0" in v
                for v in (a.ca_file, a.account, a.roles)
            )
            or type(a.verify_identity) is not bool
            or type(a.loopback_tls_exception) is not bool
            or not a.verify_identity
            and not (a.loopback_tls_exception and a.host in ("127.0.0.1", "::1"))
            or a.transaction_observation != "performance_schema_own_transaction"
        ):
            raise ExecutionError("EXECUTION_ACCESS_PROFILE")
    if request.isolation not in ("stable", "serializable"):
        raise ExecutionError("EXECUTION_ISOLATION")
    verify_deployment(request)
    verify_execution_limits(request.limits)
    verify_requirement(request.source_requirement, view.request.sources, family=family)


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
    mysql_deployment=None,
    route="",
    postgres_adbc_deployment=None,
    postgres_deployment=None,
):
    if type(artifact) not in (EmissionArtifact, CompiledEmissionArtifact):
        raise ExecutionError("EXECUTION_ARTIFACT")
    if (type(access) is MySQLAccess or route == "postgres_adbc") and output is None:
        from pietto._project.project_result_output import prepare_output

        output = prepare_output(artifact, binding=binding)
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
        mysql_deployment,
        route=route,
        postgres_adbc_deployment=postgres_adbc_deployment,
        postgres_deployment=postgres_deployment,
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
        (a.host, a.port, a.database, a.user, a.password)
        + (
            (a.sslmode,)
            if type(a) is PostgresAccess
            else (
                a.ca_file,
                a.account,
                a.roles,
                a.verify_identity,
                a.loopback_tls_exception,
                a.transaction_observation,
            )
        ),
        limits,
        (
            limits.batch_rows,
            limits.batch_bytes,
            limits.max_rows,
            limits.max_bytes,
            limits.seconds,
        ),
        request.isolation,
        deployment_state(request.mysql_deployment),
        request.route,
        postgres_adbc_deployment_state(request.postgres_adbc_deployment),
        postgres_deployment_state(request.postgres_deployment),
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


def prepare_compiled_execution(
    binding,
    access,
    *,
    route,
    limits=ExecutionLimits(),
    isolation="stable",
    postgres_deployment=None,
    mysql_deployment=None,
    allow_guard_sql=True,
):
    """One common three-route entry over a freshly bound resolved template."""
    from pietto._project.project_refinement_enumeration import (
        RefinedExecutionRequest,
        verify_refined_execution,
    )
    from pietto._project.project_guard_runtime import (
        GuardedExecutionRequest,
        verify_guarded_execution,
    )

    output, refinement, program = compiled_output(binding)
    artifact = binding.artifact
    request = ExecutionRequest(
        artifact,
        output.contract,
        access,
        limits,
        isolation,
        binding=binding,
        output=output,
        mysql_deployment=mysql_deployment,
        route=route,
        postgres_deployment=postgres_deployment,
    )
    if program is not None:
        guarded = GuardedExecutionRequest(request, program, allow_guard_sql)
        verify_guarded_execution(guarded)
        return guarded
    if type(allow_guard_sql) is not bool:
        raise ExecutionError("GUARD_EXECUTION_REQUEST")
    if refinement is not None:
        refined = RefinedExecutionRequest(request, refinement)
        verify_refined_execution(refined)
        return refined
    verify_execution_request(request)
    return request


def compiled_output(binding):
    """Output, refinement and guard program of a fresh binding; no access or IO."""
    from pietto._project.project_execution_binding_verification import verify_binding
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_compiled_loading import supported_compatibility
    from pietto._project.project_refinement import prepare_compiled_refinement
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_guard_program import prepare_program

    verify_binding(binding)
    artifact = binding.artifact
    if type(artifact.request) is not CompiledPreparedEmission:
        raise ExecutionError("COMPILED_EXECUTION_ROOT")
    root = artifact.request.verification.completed.root
    if root.accepted_compatibility != supported_compatibility():
        raise ExecutionError("COMPILED_COMPATIBILITY")
    policy = root.records[Address("policy", 0)]
    refinement = (
        prepare_compiled_refinement(artifact, binding=binding, guarded=binding.guarded)
        if policy.get("refinement") is not None
        else None
    )
    program = (
        prepare_program(binding.guarded, binding=binding, refinement=refinement)
        if binding.guarded is not None
        else None
    )
    output = (
        program.output
        if program is not None
        else refinement.output
        if refinement is not None
        else prepare_output(artifact, binding=binding)
    )
    return output, refinement, program


@dataclass(frozen=True, slots=True)
class CompiledAttemptOutcome:
    """Portable descriptions of one attempt; never live replay authority."""

    binding_reference: str
    route: str
    structure: str
    deployment_acceptance: str
    source_qualification: str
    transaction_opened: bool
    guard_states: tuple[str, ...]
    source: str
    transaction: str
    delivery: str
    cancel: tuple[bool, bool, bool]
    cleanup: str
    remote_source_use_end: str
    premise_compliance: str = "NOT_INDEPENDENTLY_VERIFIED"
    native_definition_lifetime_exclusion: str = "NOT_DEMONSTRATED"
    local_durable_result: str = "NOT_IMPLEMENTED"


def compiled_attempt_outcome(owner):
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(owner) not in (PostgresExecution, PostgresADBCExecution, MySQLExecution):
        raise ExecutionError("COMPILED_ATTEMPT_OWNER")
    request = owner.request
    if (
        type(request.artifact.request) is not CompiledPreparedEmission
        or request.binding is None
    ):
        raise ExecutionError("COMPILED_EXECUTION_ROOT")
    if request_state(request) != owner._captured:
        raise ExecutionError("EXECUTION_REQUEST_CHANGED")
    outcome = owner.outcome
    qualified = owner._qualification is not None
    return CompiledAttemptOutcome(
        request.binding.instance_reference,
        request.route,
        "ACCEPTED",
        "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
        "QUALIFIED" if qualified else "NOT_QUALIFIED",
        owner.context is not None,
        () if owner.guards is None else tuple(owner.guards.states),
        outcome.source,
        outcome.transaction,
        outcome.delivery,
        (outcome.cancel_requested, outcome.cancel_sent, outcome.cancel_observed),
        outcome.cleanup,
        "TRANSACTION_ACK"
        if outcome.transaction in ("COMMIT_ACK", "ROLLBACK_ACK")
        else "REMOTE_QUIESCENCE_UNCONFIRMED",
    )


def verify_compiled_owner(owner):
    """The real route must carry every mode required by this compiled template."""
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
    from pietto._project.project_execution_mysql import MySQLExecution

    if type(owner) not in (PostgresExecution, PostgresADBCExecution, MySQLExecution):
        raise ExecutionError("COMPILED_ATTEMPT_OWNER")
    request = owner.request
    if type(request.artifact.request) is not CompiledPreparedEmission:
        return
    expected = {
        PostgresExecution: "postgres_rows",
        PostgresADBCExecution: "postgres_adbc",
        MySQLExecution: "mysql_rows",
    }[type(owner)]
    if request.route != expected:
        raise ExecutionError("COMPILED_EXECUTION_ROUTE")
    root = request.artifact.request.verification.completed.root
    policy = root.records[Address("policy", 0)]
    if (owner.guarded_request is not None) is not policy.get("guarded"):
        raise ExecutionError("COMPILED_GUARD_MODE_REQUIRED")
    if (owner.refined_request is not None) is not (
        policy.get("refinement") is not None
    ):
        raise ExecutionError("COMPILED_REFINEMENT_MODE_REQUIRED")
    if owner.refined_request is not None:
        from pietto._project.project_refinement_enumeration import (
            verify_refined_execution,
        )

        verify_refined_execution(owner.refined_request, _guarded=owner.guarded_request)


# Fresh fields of each route's native context row: PG/ADBC backend pid,
# transaction id, server address, port and postmaster start; MySQL connection id.
_FRESH_CONTEXT = {
    "postgres_rows": (6, 7, 14, 15, 16),
    "postgres_adbc": (6, 7, 14, 15, 16),
    "mysql_rows": (3,),
}


def compiled_source_description(owner):
    """Stable source/environment observations of an open, qualified refined attempt.

    It copies only this owner's own checked qualification and admissions; no
    query, session/transaction identity or live object. It is a description to
    compare with a later fresh attempt, never source authority.
    """
    from pietto._project.project_result_output import source_read_columns

    verify_compiled_owner(owner)
    refined, admissions = owner.refined_request, owner.source_admissions
    qualification = owner._qualification
    if (
        refined is None
        or admissions is None
        or qualification is None
        or owner._closed
        or owner._transaction != "OPEN"
    ):
        raise ExecutionError("COMPILED_SOURCE_DESCRIPTION")
    qualification.verify(owner)
    admissions.verify(
        owner._connection,
        refined.refinement.sources,
        source_read_columns(refined.refinement.output),
    )
    route = owner.request.route
    if route == "mysql_rows":
        context = owner.context
        closure = (
            tuple(
                (o.key, o.kind, o.engine, o.columns, o.native_definition)
                for o in qualification.objects
            ),
            qualification.edges,
            qualification.security,
        )
    else:
        context = (
            owner._initial_profile_context
            if route == "postgres_rows"
            else owner._initial_context
        )
        closure = (
            qualification.roots,
            tuple((r.kind, r.arguments, r.rows) for r in qualification.replies),
        )
    return (
        route,
        owner.request.isolation,
        admissions.role,
        admissions.environment,
        tuple(v for i, v in enumerate(context) if i not in _FRESH_CONTEXT[route]),
        closure,
        tuple(
            (
                o.registry,
                o.definition,
                o.token_types,
                o.collision_rows,
                o.schema,
                o.collations,
                o.terminals,
            )
            for o in admissions.observations
        ),
    )
