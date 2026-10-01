"""Offline owned guard lifecycle controls; synthetic transports are labelled."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from _pietto_phase68_slice7_cases import planned
from pietto._project.project_guard_preparation import prepare_guarded
from pietto._project.project_guard_runtime import (
    GuardRun,
    prepare_guarded_execution,
    verify_guarded_execution,
)
from pietto._project.project_guard_context import GuardContext
from pietto._project.project_execution import PostgresAccess, verify_execution_request
from pietto._project.project_execution_postgres import PostgresExecution


def synthetic_owner(tmp_path, *, allow=True):
    prepared = prepare_guarded(*planned(tmp_path))
    request = prepare_guarded_execution(
        prepared,
        PostgresAccess("127.0.0.1", 5432, "lab", "reader", "not-live", "disable"),
        allow_guard_sql=allow,
    )
    owner = PostgresExecution(request)
    connection = SimpleNamespace(
        closed=False, info=SimpleNamespace(backend_pid=123, transaction_status=2)
    )
    owner._connection = owner._owned_connection = connection
    owner.session_id = 123
    owner.context = ("reader", "repeatable read", "on", "UTF8", "pg_catalog")
    owner._transaction = "OPEN"
    owner._guard_transaction = object()
    context = GuardContext(
        request.program,
        "postgres_rows",
        123,
        "reader",
        "repeatable read",
        (),
        (),
        owner,
        connection,
        owner._guard_transaction,
    )
    owner._guard_context = context
    run = GuardRun(request, context)
    owner.guards = owner._owned_guards = run
    return owner, run


def test_old_execution_cannot_borrow_pending_guarded_request(tmp_path):
    owner, run = synthetic_owner(tmp_path)
    verify_guarded_execution(run.request)
    with pytest.raises(ValueError):
        verify_execution_request(owner.request)
    with pytest.raises(ValueError, match="GUARD_CONTEXT_OWNER"):
        GuardRun(run.request, SimpleNamespace(verify_owned=lambda _: None))


def test_status_precedes_public_delivery_and_receipt_is_transaction_local(tmp_path):
    owner, run = synthetic_owner(tmp_path)
    run.prepare_submission(owner)
    names = (
        run.request.program.prefix + "channel",
        run.request.program.prefix + "g0",
        "left_id",
        "right_key",
    )
    metadata = tuple(
        SimpleNamespace(name=n, type_code=20, precision=None, scale=None, null_ok=None)
        for n in names
    )
    with pytest.raises(ValueError, match="GUARD_FULFILLMENT_REQUIRED"):
        run.public_rows(owner, ((1, 0, 1, None),))
    assert [m.name for m in run.accept_header(owner, metadata, (0, 0, None, None))] == [
        "left_id",
        "right_key",
    ]
    assert run.public_rows(owner, ((1, 0, 1, None), (1, 0, 1, None))) == (
        (1, None),
        (1, None),
    )
    for row in ((True, 0, 1, None), (1, False, 1, None), (1, 0, 1, None, 2)):
        with pytest.raises(ValueError, match="GUARD_DATA_CHANNEL"):
            run.public_rows(owner, (row,))
    owner._guard_transaction = object()
    with pytest.raises(ValueError, match="GUARD_CONTEXT_LIFETIME"):
        run.public_rows(owner, ((1, 0, 1, None),))


def test_violation_and_no_additional_guard_sql_cannot_release_data(tmp_path):
    owner, run = synthetic_owner(tmp_path / "violation")
    native = run.prepare_submission(owner)
    names = (
        run.request.program.prefix + "channel",
        run.request.program.prefix + "g0",
        "left_id",
        "right_key",
    )
    metadata = tuple(
        SimpleNamespace(name=n, type_code=20, precision=None, scale=None, null_ok=None)
        for n in names
    )
    with pytest.raises(ValueError, match="SINGLE_MATCH_VIOLATED"):
        run.accept_header(owner, metadata, (0, 1, None, None))
    assert run.states == ("VIOLATED",)
    with pytest.raises(ValueError):
        run.public_rows(owner, ((1, 0, 1, None),))
    run.native = replace(native, sql=native.sql + b" ")
    with pytest.raises(ValueError, match="GUARD_STATEMENT_CHANGED"):
        run.verify(owner)
    owner, run = synthetic_owner(tmp_path / "forbidden", allow=False)
    with pytest.raises(ValueError, match="GUARD_SQL_FORBIDDEN_UNFULFILLED"):
        run.prepare_submission(owner)
    assert run.native is None


@pytest.mark.parametrize("limit", (0, 1))
def test_original_right_bound_is_static_without_guard_sql(tmp_path, limit):
    from _pietto_phase68_slice7_cases import DIRECT
    from pietto._project.project_guard_program import (
        prepare_program,
        pure_static_proofs,
        statement_for,
    )
    from pietto._project.project_guard_rendering import render_guard

    body = (
        "table right_named:\n    from rhs\n    select:\n        id\n        key\n    limit "
        + str(limit)
        + "\n"
        + DIRECT.replace("join rhs as r", "join right_named as r")
    )
    preparation = prepare_guarded(*planned(tmp_path, body=body))
    program = prepare_program(preparation)
    assert len(program.subjects) == 1
    assert pure_static_proofs(program, program.subjects[0])
    native = render_guard(statement_for(program, "data"))
    assert native.sql is preparation.artifact.rendered.sql
    assert not native.statement.subjects
    assert all(u.domain == "original" for u in native.uses)


def test_cancel_after_independent_status_verification_cannot_fulfill(
    tmp_path, monkeypatch
):
    from pietto._project import project_guard_runtime as runtime

    owner, run = synthetic_owner(tmp_path)
    run.prepare_submission(owner)
    names = (
        run.request.program.prefix + "channel",
        run.request.program.prefix + "g0",
        "left_id",
        "right_key",
    )
    metadata = tuple(
        SimpleNamespace(name=n, type_code=20, precision=None, scale=None, null_ok=None)
        for n in names
    )
    verify = runtime.verify_native_guard

    def canceled(native):
        verify(native)
        owner._cancel.set()

    monkeypatch.setattr(runtime, "verify_native_guard", canceled)
    with pytest.raises(ValueError, match="EXECUTION_CANCELED"):
        run.accept_header(owner, metadata, (0, 0, None, None))
    assert run.states == ("RUNNING",) and run.receipt is None
    run.close()
    assert run.states == ("UNKNOWN",)


def test_refined_guard_request_unwraps_one_base_execution(tmp_path):
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from test_phase68_slice6_refinement import capabilities

    preparation = prepare_guarded(*planned(tmp_path))
    query = prepare_refinement(
        preparation.artifact,
        capabilities(preparation.artifact),
        policy=TieRefinement(),
        output=prepare_guarded_output(preparation),
    )
    request = prepare_guarded_execution(
        preparation,
        PostgresAccess("127.0.0.1", 5432, "lab", "reader", "not-live", "disable"),
        refinement=query,
    )
    owner = PostgresExecution(request)
    assert owner.request is request.execution
    assert owner.refined_request is not None
    assert owner.refined_request.refinement is query
    assert owner.guarded_request is request
    assert owner._connection is None and owner.enumeration is None


@pytest.mark.parametrize(
    "route,target", (("mysql_rows", "mysql"), ("postgres_adbc", "postgres"))
)
def test_observed_transport_consumer_cannot_create_pg_execution_authority(
    tmp_path, route, target
):
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_guard_context import ObservedGuardOwner
    from pietto._project.project_guard_runtime import ObservedGuardRequest

    program = prepare_program(prepare_guarded(*planned(tmp_path, target)))
    request = ObservedGuardRequest(program)
    environment = (
        program.preparation.artifact.request.release,
        "repeatable read",
        True,
        "utf8mb4" if target == "mysql" else "UTF8",
    )
    owner = ObservedGuardOwner(
        request,
        route=route,
        session_id=123,
        role="synthetic-observer",
        environment=environment,
        sources=tuple(
            (s, ("synthetic view definition",))
            for s in program.preparation.artifact.request.sources
        ),
    )
    with pytest.raises(ValueError):
        PostgresExecution(request)
    native = owner.guards.prepare_submission(owner)
    names = (program.prefix + "channel", program.prefix + "g0", "left_id", "right_key")
    metadata = (
        tuple((n, 8, None, None, None, None, 1, 0, 63) for n in names)
        if target == "mysql"
        else tuple(
            dict(ordinal=i, name=n, type="int64", nullable=True, metadata={})
            for i, n in enumerate(names)
        )
    )
    public = owner.guards.accept_header(owner, metadata, (0, 0, None, None))
    assert owner.guards.public_rows(owner, ((1, 0, 1, None),)) == ((1, None),)
    if target == "postgres":
        assert [m["ordinal"] for m in public] == [0, 1]
        assert [m["ordinal"] for m in metadata if type(m) is dict] == [0, 1, 2, 3]
    object.__setattr__(native.uses[0], "value", -0.0)
    with pytest.raises(ValueError, match="GUARD_STATEMENT_CHANGED"):
        owner.guards.public_rows(owner, ((1, 0, 1, None),))
    owner.close()


def test_materialized_mysql_text_has_a_guarded_only_physical_abi(tmp_path):
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_execution_reader import (
        bind_native_output,
        decode_native_rows,
        check_native_column,
    )
    from pietto._project.project_result_contract import ResultError
    from pietto._project.project_result_output import prepare_output

    case = next(c for c in manifest() if c["name"] == "bound_four")
    prepared = case_preparation(tmp_path / "guarded", "mysql", case)
    output = prepare_guarded_output(prepared)
    # Synthetic regression of the actual campaign01 type252/flags144/charset309.
    # Native observations remain separate, and no metadata byte is rewritten.
    metadata = tuple(
        (name, code, None, None, None, None, 1, flags, charset)
        for name, code, flags, charset in (
            ("left_id", 8, 0, 63),
            ("right_key", 8, 0, 63),
            ("flag", 8, 0, 63),
            ("ratio", 5, 0, 63),
            ("note", 252, 144, 309),
        )
    )
    producer, rows = decode_native_rows(
        output, "mysql_rows", metadata, ((1, None, 1, 0.0, "v"),)
    )
    assert producer.output is output and rows == ((1, None, True, 0.0, "v"),)
    assert metadata[-1][1:] == (252, None, None, None, None, 1, 144, 309)
    column = output.columns[-1]
    with pytest.raises(ResultError, match="EXECUTION_METADATA"):
        check_native_column(
            column.realization,
            "mysql_rows",
            metadata[-1],
            label=column.label,
            ordinal=column.ordinal,
            source_field=None,
        )
    for index, changed in ((7, 128), (8, 63), (0, "foreign")):
        bad = [list(m) for m in metadata]
        bad[-1][index] = changed
        with pytest.raises(ResultError, match="EXECUTION_METADATA"):
            bind_native_output(output, "mysql_rows", bad)
    ordinary = prepare_guarded(
        *planned(
            tmp_path / "ordinary",
            "mysql",
            body=case["body"],
            requested=False,
            policy="bind_safe_literals",
        )
    )
    old_output = prepare_output(ordinary.artifact)
    with pytest.raises(ResultError, match="EXECUTION_METADATA"):
        bind_native_output(old_output, "mysql_rows", metadata)
    with pytest.raises(ResultError):
        decode_native_rows(
            output, "mysql_rows", metadata, ((1, None, 1, 0.0, b"\xff"),)
        )


def test_guarded_source_text_projection_keeps_physical_source_admission_exact(tmp_path):
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from pietto._project.project_guard_preparation import prepare_guarded_output
    from pietto._project.project_execution_reader import (
        decode_native_rows,
        check_native_column,
    )
    from pietto._project.project_result_contract import ResultError

    case = next(c for c in manifest() if c["name"] == "source_text_wide")
    output = prepare_guarded_output(case_preparation(tmp_path, "mysql", case))
    metadata = (
        ("left_id", 8, None, None, None, None, 1, 0, 63),
        ("right_key", 252, None, None, None, None, 1, 144, 309),
    )
    _producer, rows = decode_native_rows(output, "mysql_rows", metadata, ((1, "v"),))
    assert rows == ((1, "v"),)
    column = output.columns[1]
    assert column.source_field is not None
    with pytest.raises(ResultError, match="EXECUTION_METADATA"):
        check_native_column(
            column.realization,
            "mysql_rows",
            metadata[1],
            label=column.label,
            ordinal=column.ordinal,
            source_field=column.source_field,
        )
    with pytest.raises(ResultError, match="VALUE_DOMAIN"):
        decode_native_rows(output, "mysql_rows", metadata, ((1, "v" * 1025),))
