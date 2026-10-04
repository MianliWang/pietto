"""Pure common-entry/profile boundaries; actual native observations live in S10's lab."""

from dataclasses import replace

import pytest

from _pietto_phase68_slice4_probe import template
from pietto._project import project_execution as execution
from pietto._project.project_execution_template import (
    prepare_live_template,
    prepare_compiled_template,
    bind_values,
)
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_loading import load_compiled
from pietto._project.project_execution_postgres import (
    PostgresExecution,
    PostgresCatalogReply,
)
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution


def access():
    return execution.PostgresAccess(
        "127.0.0.1", 5432, "phase66", "pietto_query", "unused-fixture", "disable"
    )


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    original = template(tmp_path_factory.mktemp("s10-profile-source"))
    live = prepare_live_template(original.artifact)
    built = build_compiled(original.artifact)
    root = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    loaded = prepare_compiled_template(root)
    return original, tuple(
        bind_values(t, tuple((slot, 2) for slot in t.slots)) for t in (live, loaded)
    )


@pytest.mark.parametrize("route", ("postgres_rows", "postgres_adbc"))
def test_live_and_loaded_require_the_same_fresh_profile(prepared, route):
    original, bindings = prepared
    assert bindings[0].artifact.rendered.sql == bindings[1].artifact.rendered.sql
    assert (
        bindings[0].artifact.request.verification.completed.root
        is not bindings[1].artifact.request.verification.completed.root
    )
    a = access()
    for binding in bindings:
        with pytest.raises(execution.ExecutionError, match="PREMISE_REQUIRED"):
            execution.prepare_compiled_execution(binding, a, route=route)
        premise = execution.PostgresDeploymentPremise(
            a, binding.artifact.request.sources, ("public", "pg_catalog"), route
        )
        request = execution.prepare_compiled_execution(
            binding, a, route=route, postgres_deployment=premise
        )
        assert type(request) is execution.ExecutionRequest
        assert request.postgres_deployment is premise
        owner = (
            PostgresExecution if route == "postgres_rows" else PostgresADBCExecution
        )(request)
        assert owner._connection is None
        assert (
            execution.compiled_attempt_outcome(owner).source_qualification
            == "NOT_QUALIFIED"
        )
        owner.cancel()
        with pytest.raises(execution.ExecutionError, match="CANCEL"):
            owner.open()
        assert owner._connection is None and owner.control_joined
        assert (
            execution.compiled_attempt_outcome(owner).local_durable_result
            == "NOT_IMPLEMENTED"
        )
    # The original PG rows entry retains its original admission and profile.
    legacy = execution.prepare_bound_execution(
        original and bind_values(original, tuple((slot, 2) for slot in original.slots)),
        a,
    )
    assert legacy.route == "" and legacy.postgres_deployment is None


@pytest.mark.parametrize(
    "change",
    ("access", "sources", "route", "schemas", "basis", "profile", "mysql", "old_adbc"),
)
def test_premise_cannot_be_transferred_or_downgraded(prepared, change):
    _original, (binding, foreign) = prepared
    a = access()
    premise = execution.PostgresDeploymentPremise(
        a, binding.artifact.request.sources, ("public", "pg_catalog"), "postgres_rows"
    )
    changed = {
        "access": lambda: replace(premise, access=access()),
        "sources": lambda: replace(premise, sources=foreign.artifact.request.sources),
        "route": lambda: replace(premise, route="postgres_adbc"),
        "schemas": lambda: replace(premise, schemas=("unrelated",)),
        "basis": lambda: replace(premise, basis="NATIVE_LIFETIME_EXCLUSION"),
        "profile": lambda: replace(premise, profile="legacy_pg_rows"),
        "mysql": lambda: execution.MySQLDeploymentPremise(
            execution.MySQLAccess(
                "127.0.0.1",
                3306,
                "phase66",
                "pietto_query",
                "unused-fixture",
                "/tmp/not-opened",
                "pietto_query@localhost",
            ),
            premise.sources,
            premise.schemas,
        ),
        "old_adbc": lambda: execution.PostgresADBCDeploymentPremise(
            a, premise.sources, premise.schemas
        ),
    }[change]()
    with pytest.raises(execution.ExecutionError):
        execution.prepare_compiled_execution(
            binding, a, route="postgres_rows", postgres_deployment=changed
        )
    with pytest.raises(execution.ExecutionError, match="FRESH_PROFILE"):
        execution.prepare_compiled_execution(
            binding, a, route="", postgres_deployment=premise
        )


def test_new_rows_validation_occurs_inside_the_attempt(prepared, monkeypatch):
    from pietto._project import project_execution_postgres as product

    binding = prepared[1][0]
    a = access()
    p = execution.PostgresDeploymentPremise(
        a, binding.artifact.request.sources, ("public",), "postgres_rows"
    )
    request = execution.prepare_compiled_execution(
        binding, a, route="postgres_rows", postgres_deployment=p
    )
    owner = PostgresExecution(request)
    original = product.verify_execution_request
    visits = []

    def verify(value):
        assert owner._started is not None
        visits.append(value)
        original(value)
        owner.cancel()

    def no_connection(_request):
        raise AssertionError("canceled validation reached native acquisition")

    monkeypatch.setattr(product, "verify_execution_request", verify)
    monkeypatch.setattr(product, "_connect", no_connection)
    with pytest.raises(execution.ExecutionError, match="CANCEL"):
        owner.open()
    assert visits == [request] and owner._connection is None and owner.control_joined


def test_native_reply_types_and_values_are_checked_independently():
    """Synthetic protocol data checks do not claim an owned native acquisition."""
    from pietto._project.project_postgres_source_assurance import SQL
    from pietto._project.project_postgres_source_assurance_verification import (
        verify_native_reply,
    )

    reply = PostgresCatalogReply(
        object(),
        object(),
        SQL["resolve"].encode(),
        ("public", "rows"),
        ((0, "oid", 20),),
        ((123,),),
        b"SELECT 1",
        "NORMAL",
    )
    verify_native_reply(reply, SQL["resolve"], ("public", "rows"), ((123,),))
    for candidate in (
        replace(reply, metadata=((0, "oid", 16),)),
        replace(reply, rows=((True,),)),
        replace(reply, metadata=((),)),
        replace(reply, terminal="UNKNOWN"),
        replace(reply, status=b"SELECT_UNKNOWN"),
        replace(reply, arguments=("other", "rows")),
    ):
        with pytest.raises(execution.ExecutionError):
            verify_native_reply(
                candidate, SQL["resolve"], ("public", "rows"), ((123,),)
            )


def test_required_refinement_cannot_be_unwrapped(prepared, monkeypatch):
    from test_phase68_slice6_refinement import capabilities
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from pietto._project.project_refinement_enumeration import RefinedExecutionRequest
    from pietto._project import project_execution_postgres as product

    artifact = prepared[0].artifact
    refined = prepare_refinement(
        artifact, capabilities(artifact), policy=TieRefinement()
    )
    template = prepare_live_template(artifact, refinement=refined)
    binding = bind_values(template, tuple((slot, 2) for slot in template.slots))
    a = access()
    p = execution.PostgresDeploymentPremise(
        a, binding.artifact.request.sources, ("public",), "postgres_rows"
    )
    request = execution.prepare_compiled_execution(
        binding, a, route="postgres_rows", postgres_deployment=p
    )
    assert type(request) is RefinedExecutionRequest
    proper = PostgresExecution(request)
    execution.verify_compiled_owner(proper)
    unwrapped = PostgresExecution(request.execution)

    def forbidden(_request):
        raise AssertionError("a downgraded mode reached native acquisition")

    monkeypatch.setattr(product, "_connect", forbidden)
    with pytest.raises(execution.ExecutionError, match="REFINEMENT_MODE_REQUIRED"):
        unwrapped.open()
    assert unwrapped._connection is None and unwrapped.control_joined


def test_guard_disabled_or_serializable_still_requires_the_profile(tmp_path):
    from _pietto_phase68_slice7_cases import planned
    from pietto._project.project_guard_preparation import prepare_guarded
    from pietto._project.project_guard_runtime import GuardedExecutionRequest

    verified, contract = planned(tmp_path / "guarded-source")
    guarded = prepare_guarded(verified, contract)
    template = prepare_live_template(guarded.artifact, guarded=guarded)
    binding = bind_values(template, tuple((slot, 2) for slot in template.slots))
    a = access()
    for isolation in ("stable", "serializable"):
        with pytest.raises(execution.ExecutionError, match="PREMISE_REQUIRED"):
            execution.prepare_compiled_execution(
                binding,
                a,
                route="postgres_rows",
                isolation=isolation,
                allow_guard_sql=False,
            )
        p = execution.PostgresDeploymentPremise(
            a, binding.artifact.request.sources, ("public",), "postgres_rows"
        )
        request = execution.prepare_compiled_execution(
            binding,
            a,
            route="postgres_rows",
            isolation=isolation,
            allow_guard_sql=False,
            postgres_deployment=p,
        )
        assert type(request) is GuardedExecutionRequest
        owner = PostgresExecution(request)
        execution.verify_compiled_owner(owner)
        owner.cancel()
        with pytest.raises(execution.ExecutionError, match="CANCEL"):
            owner.open()
        assert owner._connection is None and owner.control_joined


@pytest.fixture(scope="module")
def mysql_binding(tmp_path_factory):
    original = template(tmp_path_factory.mktemp("s10-mysql-source"), target="mysql")
    live = prepare_live_template(original.artifact)
    return bind_values(live, tuple((slot, 2) for slot in live.slots))


def mysql_request(binding):
    from test_phase68_slice8_execution import access as mysql_access

    a = mysql_access()
    return execution.prepare_compiled_execution(
        binding,
        a,
        route="mysql_rows",
        mysql_deployment=execution.MySQLDeploymentPremise(
            a, binding.artifact.request.sources, ("phase66",)
        ),
    )


def test_mysql_validation_occurs_in_timed_cancellable_attempt(
    mysql_binding, monkeypatch
):
    from pietto._project import project_execution_mysql as product

    request = mysql_request(mysql_binding)
    original = product.verify_execution_request
    visits = []

    def verify(value):
        assert owner._started is not None
        visits.append(value)
        original(value)
        owner.cancel()

    monkeypatch.setattr(product, "verify_execution_request", verify)
    owner = product.MySQLExecution(request)
    assert visits == []
    with pytest.raises(execution.ExecutionError, match="CANCEL"):
        owner.open()
    assert visits == [request] and owner._connection is None and owner.control_joined


@pytest.mark.parametrize("replacement", (False, True))
@pytest.mark.parametrize("primary", (False, True))
@pytest.mark.parametrize("commit", (False, True))
def test_mysql_finalizer_rechecks_original_epoch_after_primary(
    mysql_binding, monkeypatch, replacement, primary, commit
):
    """Data-only fault cut; native transaction witnesses are acquired by the lab."""
    from types import SimpleNamespace
    import time
    from pietto._project import project_execution_mysql as product
    from pietto._project.project_execution_mysql_context import EPOCH_SQL

    owner = product.MySQLExecution(mysql_request(mysql_binding))
    owner._started = time.monotonic()
    owner._transaction = "OPEN"
    calls = []
    connection = SimpleNamespace(
        unread_result=False, in_transaction=True, shutdown=lambda: calls.append("close")
    )
    control = SimpleNamespace()
    owner._connection = owner._owned_connection = connection
    owner._control_connection = owner._owned_control_connection = control
    owner._connections.append(connection)
    owner._transport = owner._control_transport = ("fixture-transport",)
    owner._initial_epoch = owner._epoch = (12, 34, "ACTIVE", "READ ONLY")
    initial_failure = (
        execution.ExecutionFailure("fixture", "ValueError", None) if primary else None
    )
    owner._primary = initial_failure
    monkeypatch.setattr(product, "transport_state", lambda c: ("fixture-transport",))

    def read(o, sql, arguments=(), **options):
        assert o is owner and options["cleanup"] is True
        calls.append(sql)
        if sql == EPOCH_SQL:
            assert options["connection"] is control
            return (), ((12, 35 if replacement else 34, "ACTIVE", "READ ONLY"),)
        return (), ()

    monkeypatch.setattr(product, "read_control", read)
    owner._finish(commit)
    command = "COMMIT" if commit else "ROLLBACK"
    assert calls == (
        [EPOCH_SQL, "close"] if replacement else [EPOCH_SQL, command, "close"]
    )
    assert owner.outcome.transaction == ("UNKNOWN" if replacement else command + "_ACK")
    if primary:
        assert owner.outcome.primary is initial_failure
        assert len(owner.outcome.cleanup_failures) == int(replacement)
    elif replacement:
        assert owner.outcome.primary is not None
    assert owner.control_joined


@pytest.mark.parametrize("mode", ("public", "refined", "pending_page"))
def test_new_pg_metadata_shares_the_existing_result_budget(prepared, mode, monkeypatch):
    from types import SimpleNamespace

    binding = prepared[1][0]
    a = access()
    premise = execution.PostgresDeploymentPremise(
        a, binding.artifact.request.sources, ("public",), "postgres_rows"
    )
    request = execution.prepare_compiled_execution(
        binding,
        a,
        route="postgres_rows",
        postgres_deployment=premise,
        limits=execution.ExecutionLimits(max_bytes=100),
    )
    owner = PostgresExecution(request)
    # Each category is below the cap, yet their combined accepted work can exceed it.
    owner._catalog_bytes = 30
    owner._guard_bytes = 10
    monkeypatch.setattr(
        owner, "_payloads", SimpleNamespace(bytes=60 if mode == "public" else 0)
    )
    monkeypatch.setattr(
        owner, "enumeration", SimpleNamespace(_bytes=60 if mode == "refined" else 0)
    )
    pending = 60 if mode == "pending_page" else 0
    owner._check_profile_bytes(pending)
    owner._catalog_bytes += 1
    with pytest.raises(execution.ExecutionError, match="RESOURCE_LIMIT"):
        owner._check_profile_bytes(pending)
    # The legacy route keeps its original public/refined accounting behavior.
    owner.request = replace(owner.request, route="")
    owner._check_profile_bytes(pending)
