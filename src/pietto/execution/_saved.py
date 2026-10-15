"""The public ordinary saved-result entry.  Advanced reads stay elsewhere."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from pietto._project import project_execution as private_execution
from pietto._project import project_public_jobs as jobs
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace
from pietto._project.project_compiled_loading import supported_compatibility
from pietto._project.project_execution_template import (
    BindingError,
    bind_values,
    named_values,
)
from pietto.execution._access import (
    ExecutionLimits,
    MySQLAccess,
    MySQLDeploymentPremise,
    PostgresAccess,
    PostgresDeploymentPremise,
)
from pietto.execution._errors import (
    RequestRejected,
    failure,
    request_failure,
    workspace_failure,
)
from pietto.execution._query import CompiledQuery
from pietto.execution._workspace import OperationReply, WorkspaceRef, _reply

__all__ = ["SaveCloseHandle", "SaveReply", "save"]


class SaveCloseHandle:
    """The only public control for an ADBC cleanup that remains unobserved."""

    __slots__ = ("_pending", "_closed")

    def __init__(self, pending):
        self._pending, self._closed = pending, False

    @property
    def closed(self):
        return self._closed

    def close(self):
        if self._closed:
            return
        refusal = None
        try:
            self._pending.close()
        except Exception as caught:
            refusal = workspace_failure(caught)
        else:
            self._closed = True
            return
        assert refusal is not None
        raise RequestRejected(refusal)

    def __reduce_ex__(self, protocol):
        raise TypeError("SaveCloseHandle cannot be pickled or copied")


@dataclass(frozen=True, slots=True)
class SaveReply:
    """The factual terminal observation of one ordinary capture flow."""

    workspace: str
    operation: OperationReply | None
    job: str | None
    generation: str | None
    admission: str | None
    terminal: str
    settlement: str | None
    cleanup: SaveCloseHandle | None = None


def _refuse(code, detail):
    raise RequestRejected(failure(code, detail))


def _values(query: Any, values: Any) -> Any:
    if values is None:
        return tuple(
            slot.original.site.position.literal.value for slot in query._template.slots
        )
    return values


def _parameters(parameters: Any) -> dict | None:
    """A private copy of a caller's ``parameters``: None or a dict with string
    keys (PIE-R1002 otherwise); names and values are checked by binding."""
    if parameters is None:
        return None
    if type(parameters) is not dict or any(type(k) is not str for k in parameters):
        _refuse("PIE-R1002", "PUBLIC_PARAMETERS_TYPE")
    return dict(parameters)


def _checked_request(
    workspace: Any,
    query: Any,
    operation: Any,
    route: Any,
    access: Any,
    premise: Any,
    limits: Any,
    isolation: Any,
    values: Any,
    job: Any,
    allow_guard_sql: bool = False,
    parameters: Any = None,
    restating: bool = False,
) -> tuple[Any, Any, Any, Any, tuple[str, ...], dict | None]:
    """Check one request before the workspace opens and bind its values.

    ``restating`` (recover): once parameters take part, values that do not
    bind are not refused here; only the saved binding can tell how they
    differ (BINDING_VECTOR in the workspace). The result then has no binding,
    and every check of the other inputs still runs, in the same order."""
    if type(workspace) is not WorkspaceRef:
        _refuse("PIE-R1002", "PUBLIC_WORKSPACE_REFERENCE")
    if query is None:
        _refuse("PIE-R1001", "PUBLIC_QUERY_REQUIRED")
    if type(query) is not CompiledQuery:
        _refuse("PIE-R1002", "PUBLIC_QUERY_TYPE")
    if operation is None:
        _refuse("PIE-R1001", "PUBLIC_OPERATION_REQUIRED")
    if type(operation) is not str:
        _refuse("PIE-R1002", "PUBLIC_OPERATION_TYPE")
    if not private_workspace.valid_identity(operation, "op"):
        _refuse("PIE-R1010", "PUBLIC_OPERATION_IDENTITY")
    if route is None:
        _refuse("PIE-R1001", "PUBLIC_ROUTE_REQUIRED")
    if type(route) is not str:
        _refuse("PIE-R1002", "PUBLIC_ROUTE_TYPE")
    route = cast(str, route)
    query = cast(Any, query)
    dialect = {
        "postgres_rows": "postgres",
        "postgres_adbc": "postgres",
        "mysql_rows": "mysql",
    }.get(route)
    if dialect is None or query.dialect != dialect:
        _refuse("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")
    if access is None:
        _refuse("PIE-R1001", "PUBLIC_ACCESS_REQUIRED")
    access_type = PostgresAccess if route.startswith("postgres_") else MySQLAccess
    premise_type = (
        PostgresDeploymentPremise
        if route.startswith("postgres_")
        else MySQLDeploymentPremise
    )
    if type(access) is not access_type:
        _refuse("PIE-R1002", "PUBLIC_ACCESS_TYPE")
    if premise is None:
        _refuse("PIE-R1001", "PUBLIC_PREMISE_REQUIRED")
    if type(premise) is not premise_type:
        _refuse("PIE-R1002", "PUBLIC_PREMISE_TYPE")
    if limits is None:
        _refuse("PIE-R1001", "PUBLIC_LIMITS_REQUIRED")
    if type(limits) is not ExecutionLimits:
        _refuse("PIE-R1002", "PUBLIC_LIMITS_TYPE")
    if isolation is None:
        _refuse("PIE-R1001", "PUBLIC_ISOLATION_REQUIRED")
    access = cast(Any, access)
    premise = cast(Any, premise)
    limits = cast(Any, limits)
    isolation = cast(Any, isolation)
    if values is not None and type(values) is not tuple:
        _refuse("PIE-R1002", "PUBLIC_VALUES_TYPE")
    named = _parameters(parameters)
    if job is not None and type(job) is not str:
        _refuse("PIE-R1002", "PUBLIC_JOB_TYPE")
    if (
        route == "mysql_rows"
        and type(access.host) is str
        and (access.host.startswith(("/", "@")) or "," in access.host)
    ):
        _refuse("PIE-R1002", "EXECUTION_ACCESS_PROFILE")
    supplied = _values(query, values)
    refusal = None
    try:
        root = query._template.artifact.request.verification.completed.root
        if root.accepted_compatibility != supported_compatibility():
            raise private_execution.ExecutionError("COMPILED_COMPATIBILITY")
        try:
            binding = bind_values(
                query._template,
                tuple(zip(query._template.slots, supplied))
                if len(supplied) == len(query._template.slots)
                else supplied,
                named_values(query._template, named),
            )
        except BindingError:
            if not (restating and (named or query._template.parameters)):
                raise
            binding = None
        sources = (
            query._template if binding is None else binding
        ).artifact.request.sources
        private_limits = private_execution.ExecutionLimits(
            limits.batch_rows,
            limits.batch_bytes,
            limits.max_rows,
            limits.max_bytes,
            limits.seconds,
        )
        if route == "mysql_rows":
            private_access = private_execution.MySQLAccess(
                access.host,
                access.port,
                access.database,
                access.user,
                access.password,
                access.ca_file,
                access.account,
                access.roles,
                verify_identity=True,
                loopback_tls_exception=False,
            )
            deployment = {
                "mysql_deployment": private_execution.MySQLDeploymentPremise(
                    private_access, sources, tuple(premise.schemas)
                )
            }
        else:
            private_access = private_execution.PostgresAccess(
                access.host,
                access.port,
                access.database,
                access.user,
                access.password,
                access.sslmode,
            )
            deployment = (
                {
                    "postgres_adbc_deployment": private_execution.PostgresADBCDeploymentPremise(
                        private_access, sources, tuple(premise.schemas)
                    )
                }
                if route == "postgres_adbc"
                else {
                    "postgres_deployment": private_execution.PostgresDeploymentPremise(
                        private_access, sources, tuple(premise.schemas), route
                    )
                }
            )
        if binding is None:
            private_execution.verify_unbound_request(
                query._template,
                private_access,
                route=route,
                limits=private_limits,
                isolation=isolation,
                **deployment,
            )
        else:
            private_execution.prepare_compiled_execution(
                binding,
                private_access,
                route=route,
                limits=private_limits,
                isolation=isolation,
                allow_guard_sql=allow_guard_sql,
                **deployment,
            )
    except Exception as caught:
        refusal = request_failure(caught)
    else:
        return (
            binding,
            supplied,
            private_access,
            private_limits,
            tuple(premise.schemas),
            named,
        )
    raise RequestRejected(refusal)


def save(
    workspace: WorkspaceRef,
    query: CompiledQuery,
    *,
    operation: str,
    route: str,
    access: PostgresAccess | MySQLAccess,
    premise: PostgresDeploymentPremise | MySQLDeploymentPremise,
    limits: ExecutionLimits = ExecutionLimits(),
    isolation: str = "stable",
    values: tuple | None = None,
    job: str | None = None,
    parameters: dict[str, object] | None = None,
) -> SaveReply:
    """Save one ordinary query result; the supplied operation is never retried.

    It runs a fresh source attempt through private runtime admission and records
    its own attempt/capture/checkpoint lifecycle.  A replayed caller operation
    only reports its recorded first step, because later steps may be unknown.
    ``parameters`` binds a query's declared parameters by name, as for
    execute(); the job records their values with the slot values.
    """
    (
        binding,
        supplied,
        private_access,
        private_limits,
        schemas,
        named,
    ) = _checked_request(
        workspace,
        query,
        operation,
        route,
        access,
        premise,
        limits,
        isolation,
        values,
        job,
        parameters=parameters,
    )
    refusal = None
    try:
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            expected_kind = "register_job" if job is None else "register_binding"
            expected_request = (
                store.register_job_request(query._template)
                if job is None
                else store.register_binding_request(job, binding)
            )
            previous = store.query_operation(
                opened,
                operation,
                expected_kind=expected_kind,
                expected_request=expected_request,
            )
            if previous is not None:
                return SaveReply(
                    workspace.identity,
                    _reply(previous),
                    previous.job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
            template = query._template
            if job is not None:
                root = template.artifact.request.verification.completed.root
                template = store.load_job(
                    opened,
                    job,
                    expected_pin=root.expected_pin,
                    accepted_producer=root.accepted_producer,
                    accepted_compatibility=root.accepted_compatibility,
                )
                binding = bind_values(
                    template,
                    tuple(zip(template.slots, supplied))
                    if len(supplied) == len(template.slots)
                    else supplied,
                    named_values(template, named),
                )
            registered, actual_job, generation = jobs.register_generation(
                opened, template, binding, route, isolation, operation, job
            )
            if (
                registered is not None
                and registered.observation != "COMMITTED_THIS_CALL"
            ):
                return SaveReply(
                    workspace.identity,
                    _reply(registered),
                    actual_job,
                    None,
                    None,
                    "REPLY_LOST_OR_PARTIAL",
                    None,
                )
        finally:
            opened.close()
        state, pending = jobs.capture(
            workspace,
            job=actual_job,
            generation=generation,
            template=template,
            route=route,
            access=private_access,
            schemas=schemas,
            limits=private_limits,
            isolation=isolation,
            values=supplied,
            parameters=named,
        )
        return SaveReply(
            workspace.identity,
            operation_result(workspace, operation),
            actual_job,
            generation,
            state.handle,
            state.terminal or "FAILED_REMOTE_UNOBSERVED",
            state.settlement,
            None if pending is None else SaveCloseHandle(pending),
        )
    except RequestRejected:
        raise
    except Exception as caught:
        refusal = workspace_failure(caught)
    assert refusal is not None
    raise RequestRejected(refusal)


def operation_result(workspace: WorkspaceRef, operation: str) -> OperationReply | None:
    from pietto.execution._workspace import operation_result as lookup

    return lookup(workspace, operation)
