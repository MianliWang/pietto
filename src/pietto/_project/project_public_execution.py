"""Private composition behind the public execution alpha (`pietto.execution`).

Each public call composes the existing owners once and reinterprets nothing:
the shared project emission and live compiled template for a compile; the
original compiled loader under the caller's own trust records, then the
compiled template, for a bundle; and for an attempt a fresh binding of the
caller's values (or the compiled literals), the caller's explicit access and
deployment premise for exactly that binding's sources, and the PostgreSQL rows
owner. Nothing but the template outlives a call; no binding, request,
qualification, accepted bundle or failure is cached.
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


def accept_bundle(payload, pin, producer, compatibility):
    """The original loader under the caller's three records. The installed
    code identity is compared with the accepted one and the payload's size is
    checked before the bytes are read; only the shapes compile_query produces
    are accepted."""
    from pietto._project.project_compiled_loading import (
        load_compiled,
        supported_compatibility,
    )
    from pietto._project.project_compiled_schema import (
        MAX_BYTES,
        VERSIONS,
        Address,
        CompiledError,
    )

    accepted = (*VERSIONS, compatibility)
    if accepted != supported_compatibility():
        raise CompiledError("PUBLIC_BUNDLE_CODE_IDENTITY")
    if not 0 < len(payload) <= MAX_BYTES:
        raise CompiledError("PUBLIC_BUNDLE_SIZE")
    root = load_compiled(
        payload,
        expected_pin=pin,
        accepted_producer=producer,
        accepted_compatibility=accepted,
    )
    policy = root.records[Address("policy", 0)]
    if policy.get("guarded") or policy.get("refinement") is not None:
        raise CompiledError("PUBLIC_BUNDLE_UNSUPPORTED")
    return root


def bundle_template(root):
    """The compiled template of an accepted root (its own failure stage)."""
    from pietto._project.project_execution_template import prepare_compiled_template

    return prepare_compiled_template(root)


def query_facts(template):
    """Module, kind, name, family, release, literal policy and slot tags of a
    compiled template, read from its root's own records."""
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_sql_emission_cli import POLICIES

    request = template.artifact.request
    root = request.verification.completed.root
    declaration = root.records[root.records[root.description.query].get("declaration")]
    policy = root.records[Address("policy", 0)].get("literal_policy")
    return (
        declaration.get("module"),
        declaration.get("kind"),
        declaration.get("label"),
        request.family,
        request.release,
        {value: name for name, value in POLICIES.items()}[policy],
        tuple(slot.tag for slot in template.slots),
    )


def export_facts(template):
    """The verified compiled root's exact bytes and its own pin, producer and
    code identity; no I/O."""
    from pietto._project.project_compiled_schema import encode

    root = template.artifact.request.verification.completed.root
    root.verify()
    return (
        encode(root.description),
        root.expected_pin,
        root.accepted_producer,
        root.accepted_compatibility[-1],
    )


@entry
def prepare_attempt(
    template, access, *, route, schemas, limits, isolation, values=None
):
    """One fresh, unopened PostgreSQL rows owner; no I/O. One scope verifies
    the template's compiled root once for the binding and the request.
    `values` None binds the template's own literals; a tuple of another
    length is handed to the binder whole, which refuses it."""
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_template import bind_values

    if values is None:
        values = tuple(
            slot.original.site.position.literal.value for slot in template.slots
        )
    binding = bind_values(
        template,
        tuple(zip(template.slots, values))
        if len(values) == len(template.slots)
        else values,
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


@entry
def prepare_mysql_attempt(
    template, access, *, schemas, limits, isolation, values=None
):
    """One fresh, unopened MySQL rows owner; no I/O or driver import.

    The ambient TLS refusal precedes importing the private MySQL owner, whose
    native module imports ``ssl``. The public access shape is converted only
    here, with the private identity and transaction escape hatches fixed to
    the approved route profile.
    """
    ex.refuse_ambient()
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_execution_template import bind_values

    if values is None:
        values = tuple(
            slot.original.site.position.literal.value for slot in template.slots
        )
    binding = bind_values(
        template,
        tuple(zip(template.slots, values))
        if len(values) == len(template.slots)
        else values,
    )
    premise = ex.MySQLDeploymentPremise(
        access, binding.artifact.request.sources, schemas
    )
    request = ex.prepare_compiled_execution(
        binding,
        access,
        route="mysql_rows",
        limits=limits,
        isolation=isolation,
        mysql_deployment=premise,
        allow_guard_sql=False,
    )
    return MySQLExecution(request)


def attempt_facts(owner):
    """The owner's closed flag, deadline, established session and layered
    outcome, read without I/O or locks (a dropped handle's finalizer uses it)."""
    return (
        owner._closed is True,
        owner.deadline_expired is True,
        owner.session_id is not None,
        owner.outcome,
        owner._terminal,
    )


def driver_error(error):
    """Whether the route's driver raised `error` (its message is never read)."""
    return type(error).__module__.partition(".")[0] in ("mysql", "psycopg")


def batch_rows(batch):
    """Rows of a checked batch the owner just returned."""
    return batch._batch.num_rows


@entry
def result_schema(owner):
    """The schema every batch of one prepared owner has, without I/O."""
    from pietto._project import project_arrow_result as arrow
    from pietto._project.project_execution_reader import bind_stored_output

    arrow.pinned()
    producer = bind_stored_output(owner.request.output, owner.request.route)
    return arrow.bind_arrow(producer).schema
