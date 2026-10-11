"""Private composition behind the public execution alpha (`pietto.execution`).

Each public call composes the existing owners once and reinterprets nothing:
the shared project emission and live compiled template for a compile, and for
an attempt a fresh binding of the source's own literal values, the caller's
explicit access and deployment premise for exactly that binding's sources, and
the PostgreSQL rows owner. Nothing but the template outlives a call; no
binding, request, qualification or failure is cached.
"""

from __future__ import annotations

from pietto._project import project_execution as ex
from pietto._project.project_verification_scope import entry

__all__: tuple[str, ...] = ()


def compile_live(project, module, kind, name, dialect, contract, policy):
    """The shared emission outcome and, for a VERIFIED one, its live template."""
    from pietto._project.project_execution_template import prepare_live_template
    from pietto._project.project_sql_emission_cli import POLICIES, emit_project

    outcome, _protected = emit_project(
        project, module, kind, name, dialect, contract, POLICIES[policy]
    )
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        return outcome, None
    return outcome, prepare_live_template(outcome.artifact)


@entry
def prepare_attempt(template, access, *, route, schemas, limits, isolation):
    """One fresh, unopened PostgreSQL rows owner; no I/O. One scope verifies
    the template's compiled root once for the binding and the request."""
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_template import bind_values

    binding = bind_values(
        template,
        tuple(
            (slot, slot.original.site.position.literal.value) for slot in template.slots
        ),
    )
    premise = ex.PostgresDeploymentPremise(
        access, binding.artifact.request.sources, schemas, route
    )
    request = ex.prepare_compiled_execution(
        binding,
        access,
        route=route,
        limits=limits,
        isolation=isolation,
        postgres_deployment=premise,
        allow_guard_sql=False,
    )
    return PostgresExecution(request)


def attempt_facts(owner):
    """The owner's closed flag, deadline, established session and layered
    outcome, read without I/O or locks (a dropped handle's finalizer uses it)."""
    return (
        owner._closed is True,
        owner.deadline_expired is True,
        owner.session_id is not None,
        owner.outcome,
    )


def driver_error(error):
    """Whether the route's driver raised `error` (its message is never read)."""
    from pietto._project.project_execution_postgres import driver_error

    return driver_error(error)


def batch_rows(batch):
    """Rows of a checked batch the owner just returned."""
    return batch._batch.num_rows
