"""Phase71 S12-A collection admission before any connection, workspace or sink.

No collect record reaches a compiled root before S08/S09 land, so the requests
here replace exactly one name, ``project_execution_nested.collection_operations``
(``_collect``), and every seamed case has an unseamed control that records
today's flat result. Observers that fail when called are not a
second seam. These are mechanism tests; S12-B redoes them on real nested
queries. Expected values are hand-written from S02's literals.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_execution_api as api
import _pietto_execution_jobs_probe as workspace_probe
import _pietto_results_nested as nested_cases
import _pietto_results_product as product
import pietto.execution as execution
from pietto._project import project_execution as ex
from pietto._project import project_execution_nested as nested
from pietto._project import project_job_workspace as private_workspace
from pietto._project.project_compiled_build import build_compiled
from pietto._project.project_compiled_schema import Address, Record
from pietto._project.project_result_binding import CHILD_KINDS
from pietto._project.project_execution_template import (
    bind_values,
    prepare_compiled_template,
)
from pietto.execution import _relay as relay

pytestmark = pytest.mark.ci_workload("general-runtime")

SERIES = """
query tagged:
    let steps:
        from generate_series(1, 3, 1) as n
        select:
            n
    from items
    let s = steps
    inner join s on items.id == s.n
    select:
        id
        step = s.n
"""
DRIVERS = ("adbc_driver", "psycopg", "pyarrow")


def _compiled(directory, extra=""):
    project = api.write_example(directory)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + extra, encoding="utf-8")
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="query" if extra else "table",
        name="tagged" if extra else "active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


@pytest.fixture(scope="module")
def query(tmp_path_factory):
    return _compiled(tmp_path_factory.mktemp("collection-flat"))


@pytest.fixture(scope="module")
def series(tmp_path_factory):
    return _compiled(tmp_path_factory.mktemp("collection-series"), SERIES)


@pytest.fixture(scope="module")
def templates(tmp_path_factory):
    """Real flat compiled templates: plain on both targets, guarded, refined."""
    from _pietto_execution_guard_cases import case_preparation, manifest
    import _pietto_execution_recovery_probe as recovery

    base = tmp_path_factory.mktemp("collection-templates")
    postgres, _ = workspace_probe.compiled_template(base / "postgres")
    mysql, _ = workspace_probe.compiled_template(base / "mysql", target="mysql")
    case = next(c for c in manifest() if c["name"] == "bag_one")
    guarded = case_preparation(base / "guarded", "postgres", case)
    guarded_template = prepare_compiled_template(
        build_compiled(guarded.artifact, guarded=guarded).root
    )
    refined, _, values = recovery.refined_template(base / "refined")
    return {
        "postgres": bind_values(postgres, tuple(zip(postgres.slots, (1,)))),
        "mysql": bind_values(mysql, tuple(zip(mysql.slots, (1,)))),
        "guarded": guarded_template,
        "guarded_binding": bind_values(guarded_template, ()),
        "refined": refined,
        "refined_binding": bind_values(refined, tuple(zip(refined.slots, values))),
    }


@pytest.fixture(scope="module")
def leaves(tmp_path_factory):
    return nested_cases.fixtures(product, tmp_path_factory.mktemp("collection-leaves"))


def _collect(patch):
    """The one S12-A seam: a root whose records hold a collect operation."""
    patch.setattr(
        nested, "collection_operations", lambda records: frozenset({"collect"})
    )


def _records(value):
    if hasattr(value, "_template"):
        value = value._template
    return value.artifact.request.verification.completed.root.records


def _word(action):
    try:
        action()
    except Exception as error:
        return type(error).__name__ + ":" + str(error)
    return "ACCEPTED"


def _rejected(action):
    with pytest.raises(execution.RequestRejected) as refused:
        action()
    # No private exception is reachable from the public refusal.
    assert refused.value.__cause__ is None and refused.value.__context__ is None
    return refused.value.code, refused.value.detail


def _workspace(tmp_path):
    reference = object.__new__(execution.WorkspaceRef)
    object.__setattr__(reference, "root", str(tmp_path / "never-opened"))
    object.__setattr__(reference, "identity", "ws-" + "4" * 32)
    return reference


def _postgres(route="postgres_rows") -> dict[str, Any]:
    return dict(
        route=route,
        access=execution.PostgresAccess("127.0.0.1", 9, "phase66", "u", "pw"),
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
    )


def _private_access():
    return ex.PostgresAccess("127.0.0.1", 9, "phase66", "pietto_query", "pw", "disable")


def _new_drivers(before):
    return sorted(
        name for name in set(sys.modules) - before if name.startswith(DRIVERS)
    )


def test_flat_compiled_roots_have_no_collection_operation(query, series, templates):
    for value in (
        query,
        series,
        templates["postgres"],
        templates["mysql"],
        templates["guarded"],
        templates["refined"],
    ):
        assert nested.collection_operations(_records(value)) == frozenset()


def test_the_predicate_reads_collect_operations_and_unnest_records():
    collect = Record(Address("operation", 3), (("collect", "collect"), (), None, 0))
    other = Record(Address("operation", 4), (("binary", "and"), (), None, 0))
    unnest = Record(Address("unnest", 0), ())
    # The collect pair outside an operation record is not a collect operation.
    elsewhere = Record(Address("aggregate_value", 0), (("collect", "collect"),))

    def ops(*records):
        return nested.collection_operations({r.address: r for r in records})

    assert ops(collect, other) == frozenset({"collect"})
    assert ops(unnest, other) == frozenset({"unnest"})
    assert ops(collect, unnest) == frozenset({"collect", "unnest"})
    assert ops(other) == ops(elsewhere) == ops() == frozenset()
    assert nested.__all__ == ()


@pytest.fixture(scope="module")
def preflight_request(tmp_path_factory):
    output = nested_cases.collected(
        product, tmp_path_factory.mktemp("collection-preflight") / "project"
    )
    return SimpleNamespace(
        artifact=output.artifact,
        output=output,
        limits=ex.ExecutionLimits(),
    )


def test_collection_preflight_uses_only_qualified_descriptor_roots(preflight_request):
    calls = []
    answers = iter(("UTF8", 4, 3, 12))
    connection, qualification = object(), object()

    def read(sql, arguments):
        calls.append((sql, arguments))
        value = next(answers)
        oid = 25 if not arguments else 23 if "octet_length" in sql else 20
        return nested.CollectionReply(
            connection,
            sql,
            arguments,
            ((0, "bound", oid),),
            ((value,),),
            2,
        )

    receipt = nested.run_collection_preflight(
        preflight_request,
        read,
        connection=connection,
        qualification=qualification,
        profile=("snapshot",),
    )
    assert receipt is not None
    assert nested.request_collection_operations(preflight_request) == {"collect"}
    nested.verify_collection_preflight(
        preflight_request,
        receipt,
        connection=connection,
        qualification=qualification,
        profile=("snapshot",),
    )
    assert receipt.connection is connection
    assert receipt.qualification is qualification
    assert receipt.profile == ("snapshot",)
    assert tuple(reply.connection for reply in receipt.replies) == (connection,) * len(
        receipt.replies
    )
    for damaged in (
        replace(receipt, connection=object()),
        replace(receipt, row_bytes=receipt.row_bytes + 1),
        replace(receipt, replies=receipt.replies[:-1]),
    ):
        with pytest.raises(ex.ExecutionError, match="POSTGRES_SOURCE_RESOURCE_LIMIT"):
            nested.verify_collection_preflight(
                preflight_request,
                damaged,
                connection=connection,
                qualification=qualification,
                profile=("snapshot",),
            )
    assert calls == [
        ("SELECT current_setting('server_encoding')", ()),
        (
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."rows" LIMIT $1) AS "__pietto_nested_bound"',
            (65,),
        ),
        (
            'SELECT COUNT(*) FROM (SELECT 1 FROM "public"."kids" LIMIT $1) AS "__pietto_nested_bound"',
            (17,),
        ),
        (
            'SELECT COALESCE(MAX(LEAST(COALESCE(octet_length("t"),0),$1)),0) FROM "public"."kids"',
            (257,),
        ),
    ]


@pytest.mark.parametrize(
    "answers, expected, expected_calls",
    (
        (("LATIN1",), "POSTGRES_SOURCE_ENCODING", 1),
        (("UTF8", 65), "POSTGRES_SOURCE_RESOURCE_LIMIT", 2),
        (("UTF8", 4, 3, 257), "POSTGRES_SOURCE_RESOURCE_LIMIT", 4),
    ),
)
def test_collection_preflight_refuses_encoding_or_bounded_sentinel(
    preflight_request, answers, expected, expected_calls
):
    values = iter(answers)
    connection, qualification = object(), object()
    calls = []

    def read(sql, arguments):
        calls.append((sql, arguments))
        value = next(values)
        oid = 25 if not arguments else 23 if "octet_length" in sql else 20
        return nested.CollectionReply(
            connection,
            sql,
            arguments,
            ((0, "bound", oid),),
            ((value,),),
            2,
        )

    with pytest.raises(ex.ExecutionError, match=expected):
        nested.run_collection_preflight(
            preflight_request,
            read,
            connection=connection,
            qualification=qualification,
            profile=("snapshot",),
        )
    assert len(calls) == expected_calls


def test_actual_public_collect_prepares_without_connecting(tmp_path):
    project = api.write_nested_collect(tmp_path / "nested")
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="preserve",
    )
    arguments = _postgres()
    arguments["premise"] = execution.PostgresDeploymentPremise(("public", "pg_catalog"))
    before = set(sys.modules)
    handle = execution.execute(query, **arguments)
    try:
        assert handle.outcome.end == "NOT_STARTED"
        assert _new_drivers(before) == []
    finally:
        handle.close()


def test_public_execute_admits_a_collection_only_on_postgres_rows(query, monkeypatch):
    handle = execution.execute(query, **_postgres("postgres_adbc"))
    assert type(handle) is execution.ResultHandle
    handle.close()
    _collect(monkeypatch)
    before = set(sys.modules)
    assert _rejected(
        lambda: execution.execute(query, **_postgres("postgres_adbc"))
    ) == (
        "PIE-R1003",
        "COLLECTION_ROUTE",
    )
    assert _new_drivers(before) == []
    handle = execution.execute(query, **_postgres())
    assert type(handle) is execution.ResultHandle
    handle.close()


def test_private_routes_refuse_a_collection_before_their_premise(templates):
    """No deployment premise is given: unseamed, each route reports its own
    premise; seamed, only postgres_rows gets that far."""
    mysql = ex.MySQLAccess(
        "127.0.0.1",
        9,
        "phase66",
        "pietto_query",
        "pw",
        "/dev/null",
        "pietto_query@%",
        verify_identity=False,
        loopback_tls_exception=True,
    )
    calls = (
        lambda: ex.prepare_compiled_execution(
            templates["mysql"], mysql, route="mysql_rows"
        ),
        lambda: ex.prepare_compiled_execution(
            templates["postgres"], _private_access(), route="postgres_adbc"
        ),
        lambda: ex.prepare_compiled_execution(
            templates["postgres"], _private_access(), route="postgres_rows"
        ),
        lambda: ex.prepare_compiled_execution(
            templates["guarded_binding"], _private_access(), route="postgres_rows"
        ),
        lambda: ex.prepare_compiled_execution(
            templates["refined_binding"], _private_access(), route="postgres_rows"
        ),
        lambda: ex.verify_unbound_request(
            templates["guarded"],
            _private_access(),
            route="postgres_rows",
            limits=ex.ExecutionLimits(),
            isolation="stable",
        ),
        lambda: ex.verify_unbound_request(
            templates["refined"],
            _private_access(),
            route="postgres_rows",
            limits=ex.ExecutionLimits(),
            isolation="stable",
        ),
    )
    premise = "ExecutionError:POSTGRES_DEPLOYMENT_PREMISE_REQUIRED"
    route = "ExecutionError:COLLECTION_ROUTE"
    assert [_word(call) for call in calls] == [
        "ExecutionError:MYSQL_DEPLOYMENT_PREMISE_REQUIRED",
        "ExecutionError:POSTGRES_ADBC_DEPLOYMENT_PREMISE_REQUIRED",
        premise,
        premise,
        premise,
        premise,
        premise,
    ]
    with pytest.MonkeyPatch.context() as patch:
        _collect(patch)
        assert [_word(call) for call in calls] == [
            route,
            route,
            premise,
            route,
            route,
            route,
            route,
        ]


def test_all_supported_child_leaves_are_admitted_before_connection(
    leaves,
):
    contract = leaves["parent"][0]
    assert _word(lambda: nested.admit_nested_shape(contract)) == "ACCEPTED"
    ibt = nested_cases.nested(leaves, leaves["ibt"]).contract
    assert _word(lambda: nested.admit_nested_shape(ibt)) == "ACCEPTED"
    for kind in ("Float", "Decimal"):
        from pietto._project.project_result_contract import NestedShape, ScalarShape

        parent, collection = ibt.shape.fields
        assert type(collection.shape) is NestedShape
        child, *remaining = collection.shape.fields
        assert type(child.shape) is ScalarShape
        changed = replace(
            child,
            shape=replace(
                child.shape, canonical=replace(child.shape.canonical, name=kind)
            ),
        )
        shape = replace(
            ibt,
            shape=replace(
                ibt.shape,
                fields=(
                    parent,
                    replace(
                        collection,
                        shape=replace(collection.shape, fields=(changed, *remaining)),
                    ),
                ),
            ),
        )
        assert _word(lambda: nested.admit_nested_shape(shape)) == "ACCEPTED", kind
    assert set(CHILD_KINDS) == {
        "Int",
        "Bool",
        "Text",
        "Float",
        "Decimal",
    }


def test_save_and_relay_refuse_a_collection_before_workspace_or_sink(
    query, tmp_path, monkeypatch
):
    opened, sinks = [], []
    real_sink = relay._sink_target

    def open_workspace(*arguments, **keywords):
        opened.append(arguments)
        raise AssertionError("WORKSPACE_OPENED")

    def sink_target(*arguments):
        sinks.append(arguments)
        return real_sink(*arguments)

    monkeypatch.setattr(private_workspace, "open_workspace", open_workspace)
    monkeypatch.setattr(relay, "_sink_target", sink_target)
    workspace = _workspace(tmp_path)

    def save(route="postgres_rows"):
        return execution.save(
            workspace, query, operation=execution.new_operation(), **_postgres(route)
        )

    def relay_live():
        return execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            **_postgres(),
            sink_root=None,
            expected_sink_identity="snk-" + "0" * 32,
            sink_namespace="relay",
            sink_epoch=1,
            sink_retention="retention",
            sink_budget_bytes=private_workspace.DEFAULT_BUDGET,
        )

    # Unseamed controls reach the workspace and the sink check.
    assert _rejected(save)[0] == "PIE-R1009" and len(opened) == 1
    assert _rejected(relay_live) == ("PIE-R1001", "REFERENCE_SINK_ROOT")
    assert len(sinks) == 1
    _collect(monkeypatch)
    assert _rejected(save) == ("PIE-R1004", "COLLECTION_ENTRY")
    assert _rejected(lambda: save("postgres_adbc")) == (
        "PIE-R1003",
        "COLLECTION_ROUTE",
    )
    assert _rejected(relay_live) == ("PIE-R1004", "COLLECTION_ENTRY")
    assert (len(opened), len(sinks)) == (1, 1)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ("query", "series"))
def test_r2_refuses_a_collection_before_its_other_shape_checks(
    request, tmp_path, monkeypatch, name
):
    """The series join also reads a generated series, which R2 refuses as a
    coordinate basis: a collection is reported first."""
    query = request.getfixturevalue(name)
    bundle = execution.export_bundle(query)
    workspace = _workspace(tmp_path)

    class Opened(Exception):
        pass

    def opened(*arguments, **keywords):
        raise Opened

    monkeypatch.setattr(private_workspace, "open_workspace", opened)
    inputs = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in query._template.artifact.request.sources
    )
    r2: dict[str, Any] = dict(
        query=query,
        source_requirements=inputs,
        operation=execution.new_operation(),
        limits=execution.ExecutionLimits(),
        **_postgres(),
    )
    calls = (
        lambda: execution.save_recoverable(workspace, **r2),
        lambda: execution.recover(
            workspace,
            job="job-" + "5" * 32,
            generation="gen-" + "6" * 32,
            checkpoint=None,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
            purpose="collection recovery",
            seconds=1,
            **r2,
        ),
    )
    control = (
        ("PIE-R1009", None)
        if name == "query"
        else ("PIE-R1004", "PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS")
    )
    for call in calls:
        assert _rejected(call) == control
    _collect(monkeypatch)
    for call in calls:
        assert _rejected(call) == ("PIE-R1004", "PUBLIC_R2_COLLECTION")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", ("U1_cross", "U4_left_true"))
def test_actual_flat_unnest_retains_pre_effect_collection_refusals(
    tmp_path, monkeypatch, name
):
    from pietto._project import project_execution_postgres as pg

    project = api.write_nested_unnest(tmp_path / "project", name)
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="postgres",
        emission_contract="contract.json",
    )
    assert nested.collection_operations(_records(query)) == {"collect", "unnest"}
    touched = []

    def forbidden(*args, **kwargs):
        touched.append(True)
        raise AssertionError("effect before collection refusal")

    monkeypatch.setattr(pg, "_connect", forbidden)
    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    monkeypatch.setattr(relay, "_sink_target", forbidden)
    arguments = _postgres()
    arguments["premise"] = execution.PostgresDeploymentPremise(("public", "pg_catalog"))
    handle = execution.execute(query, **arguments)
    connection, qualification = object(), object()
    values = iter(("UTF8", 6, 11, 25))
    calls = []

    def read(sql, arguments):
        calls.append((sql, arguments))
        oid = 25 if not arguments else 23 if "octet_length" in sql else 20
        return nested.CollectionReply(
            connection, sql, arguments, ((0, "bound", oid),), ((next(values),),), 2
        )

    try:
        receipt = nested.run_collection_preflight(
            handle._owner.request,
            read,
            connection=connection,
            qualification=qualification,
            profile=("snapshot",),
        )
        assert receipt is not None
        assert (
            receipt.parents,
            receipt.children,
            receipt.row_bytes,
            receipt.total_bytes,
        ) == (6, 11, 217, 14322)
        nested.verify_collection_preflight(
            handle._owner.request,
            receipt,
            connection=connection,
            qualification=qualification,
            profile=("snapshot",),
        )
        assert len(calls) == 4
    finally:
        handle.close()
    before = set(sys.modules)
    assert _rejected(
        lambda: execution.execute(query, **{**arguments, "route": "postgres_adbc"})
    ) == ("PIE-R1003", "COLLECTION_ROUTE")
    assert _rejected(
        lambda: execution.execute(query, **{**arguments, "route": "mysql_rows"})
    ) == ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")
    workspace = _workspace(tmp_path)
    assert _rejected(
        lambda: execution.save(
            workspace, query, operation=execution.new_operation(), **arguments
        )
    ) == ("PIE-R1004", "COLLECTION_ENTRY")
    assert _rejected(
        lambda: execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            **arguments,
            sink_root=None,
            expected_sink_identity="snk-" + "0" * 32,
            sink_namespace="relay",
            sink_epoch=1,
            sink_retention="retention",
            sink_budget_bytes=private_workspace.DEFAULT_BUDGET,
        )
    ) == ("PIE-R1004", "COLLECTION_ENTRY")
    inputs = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in query._template.artifact.request.sources
    )
    assert _rejected(
        lambda: execution.save_recoverable(
            workspace,
            query=query,
            source_requirements=inputs,
            operation=execution.new_operation(),
            limits=execution.ExecutionLimits(),
            **arguments,
        )
    ) == ("PIE-R1004", "PUBLIC_R2_COLLECTION")
    assert touched == [] and _new_drivers(before) == []
