"""S03 production authority and control paths, offline injected collaborators."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest

import _pietto_phase67_result_product_probe as product
from pietto._project import project_execution as execution
from pietto._project import project_execution_postgres as pg
from pietto._project import project_execution_reader as payloads
from pietto._project import project_arrow_result as scalar
from pietto._project.project_result_contract import ResultError
from pietto._project.project_execution_source import (
    RetainedSourceRequirement,
    verify_requirement,
)


@pytest.fixture
def request_(tmp_path):
    _, artifact = product.build_source(tmp_path / "compiled", "postgres")
    return execution.prepare_execution(
        artifact,
        execution.PostgresAccess(
            "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
        ),
        limits=execution.ExecutionLimits(batch_rows=2),
    )


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.position = 0
        self.kind = "control"
        self.description = (
            SimpleNamespace(name="renamed", type_code=20, null_ok=None),
            SimpleNamespace(name="other", type_code=20, null_ok=None),
        )
        self.pgresult = SimpleNamespace(ntuples=4)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def execute(self, sql, params=None, prepare=None):
        self.connection.operations.append((sql, params, prepare))
        if sql.startswith("BEGIN"):
            self.connection.strength = (
                "serializable" if "SERIALIZABLE" in sql else "repeatable read"
            )
        elif sql == "COMMIT" and self.connection.fail == "commit":
            raise OSError("injected lost commit response")
        elif sql.startswith("SELECT current_user"):
            self.kind = "context"
        elif sql.startswith("SELECT pg_catalog.set_config"):
            pass
        elif sql.startswith("SELECT"):
            self.kind = "data"
            if self.connection.fail == "execute":
                raise OSError("injected execute failure")

    def fetchone(self):
        return (
            "pietto_query",
            self.connection.strength,
            "on",
            "UTF8",
            "pg_catalog",
            123,
        )

    def fetchmany(self, size):
        if self.connection.fail == "read" and self.position:
            raise OSError("injected later read")
        rows = self.connection.rows[self.position : self.position + size]
        self.position += len(rows)
        return rows

    def close(self):
        pass


class Connection:
    def __init__(self, fail=""):
        self.info = SimpleNamespace(server_version=180006, backend_pid=123)
        self.rows = [
            (9007199254740993, None),
            (9007199254740993, None),
            (0, 0),
            (-1, 1),
        ]
        self.operations = []
        self.fail = fail
        self.closed = False
        self.strength = "repeatable read"
        self.pgconn = SimpleNamespace(finish=lambda: setattr(self, "closed", True))

    def cursor(self):
        return Cursor(self)

    def close(self):
        self.closed = True
        if self.fail == "cleanup":
            raise OSError("injected close response")

    def cancel_safe(self, timeout):
        self.operations.append(("cancel", timeout, None))


class CheckedRows:
    """Only carrier construction is replaced; real producer/scalar checks remain."""

    def __init__(self, request, description):
        self.producer = payloads.bind_native_projection(request, description)
        self.rows = self.batches = self.bytes = 0

    def accept(self, rows):
        values = tuple(
            tuple(
                scalar._value(value, bound)
                for value, bound in zip(row, self.producer.fields, strict=True)
            )
            for row in rows
        )
        self.rows += len(rows)
        self.batches += 1
        self.bytes += len(rows) * 16
        return values


def install(monkeypatch, connection):
    monkeypatch.setattr(pg, "_connect", lambda request: connection)
    monkeypatch.setattr(pg, "ExecutionPayloads", CheckedRows)


def test_unknown_cardinality_exact_boundary_and_empty(request_, monkeypatch):
    for rows in ([*Connection().rows], []):
        conn = Connection()
        conn.rows = rows
        install(monkeypatch, conn)
        with pg.PostgresExecution(request_) as stream:
            actual = [row for batch in stream for row in cast(Any, batch)]
        assert actual == rows
        out = stream.outcome
        assert (out.source, out.transaction, out.delivery, out.cleanup) == (
            "EOF",
            "COMMIT_ACK",
            "COMPLETE",
            "CLOSED",
        )
        assert out.rows == len(rows) and conn.closed and stream.control_joined
        submitted = [op for op in conn.operations if op[2] is True]
        assert submitted == [(request_.artifact.rendered.sql.decode(), (), True)]


@pytest.mark.parametrize(
    "fail,phase,transaction",
    [
        ("execute", "execute", "ROLLBACK_ACK"),
        ("read", "read", "ROLLBACK_ACK"),
        ("commit", "transaction", "UNKNOWN"),
        ("cleanup", "finalization", "COMMIT_ACK"),
    ],
)
def test_failures_are_not_eof_success(request_, monkeypatch, fail, phase, transaction):
    conn = Connection(fail)
    install(monkeypatch, conn)
    stream = pg.PostgresExecution(request_)
    with pytest.raises((OSError, execution.ExecutionError)):
        with stream:
            list(stream)
    out = stream.outcome
    assert out.primary is not None
    assert (
        out.primary.phase == phase
        and out.transaction == transaction
        and out.delivery == "FAILED"
    )
    assert conn.closed and stream.control_joined
    if fail == "cleanup":
        assert out.cleanup_failures and out.cleanup == "FAILED"


def test_early_close_consumer_failure_and_late_cancel(request_, monkeypatch):
    conn = Connection()
    install(monkeypatch, conn)
    with pg.PostgresExecution(request_) as stream:
        next(stream)
    assert (
        stream.outcome.source,
        stream.outcome.delivery,
        stream.outcome.transaction,
    ) == ("EARLY_CLOSE", "INCOMPLETE", "ROLLBACK_ACK")
    assert stream.cancel() == {
        "requested": True,
        "sent": False,
        "observed": False,
        "late": True,
    }
    conn = Connection()
    install(monkeypatch, conn)
    failed = pg.PostgresExecution(request_)
    with pytest.raises(RuntimeError):
        with failed:
            next(failed)
            raise RuntimeError("injected consumer failure")
    outcome = failed.outcome
    assert outcome.primary is not None
    assert outcome.primary.phase == "consumer" and outcome.delivery == "FAILED"


def test_precancel_foreign_root_bad_strength_and_changed_request_refuse(
    request_, tmp_path, monkeypatch
):
    calls = []
    monkeypatch.setattr(pg, "_connect", lambda request: calls.append(request))
    stream = pg.PostgresExecution(request_)
    stream.cancel()
    with pytest.raises(execution.ExecutionError):
        stream.open()
    assert not calls and stream.control_joined
    with pytest.raises(execution.ExecutionError, match="ISOLATION"):
        pg.PostgresExecution(replace(request_, isolation="read committed"))
    _, other = product.build_source(tmp_path / "foreign", "postgres")
    with pytest.raises((execution.ExecutionError, ResultError, ValueError)):
        pg.PostgresExecution(replace(request_, artifact=other))
    with pytest.raises(execution.ExecutionError, match="LIMITS"):
        pg.PostgresExecution(
            replace(request_, limits=replace(request_.limits, seconds=1e308))
        )
    conn = Connection()
    install(monkeypatch, conn)
    stream = pg.PostgresExecution(request_)
    stream.open()
    object.__setattr__(request_.limits, "max_rows", 100)
    with pytest.raises(execution.ExecutionError, match="CHANGED"):
        next(stream)
    assert not any(op[2] is True for op in conn.operations) and conn.closed


def test_metadata_and_nullable_values_are_checked_without_arrow(request_):
    meta = Cursor(Connection()).description
    checked = CheckedRows(request_, meta)
    with pytest.raises(ResultError, match="NULL"):
        checked.accept([(None, 0)])
    with pytest.raises(ResultError, match="VALUE_DOMAIN"):
        checked.accept([(1.0, 0)])
    changed = (SimpleNamespace(name="renamed", type_code=23, null_ok=None), meta[1])
    with pytest.raises(ResultError, match="EXECUTION_METADATA"):
        payloads.bind_native_projection(request_, changed)


def test_source_capability_is_scoped_and_not_required_for_non_r2(request_, tmp_path):
    verify_requirement(None, request_.artifact.request.sources)
    source = request_.artifact.request.sources[0]
    requirement = RetainedSourceRequirement(
        source,
        "provider",
        "v1",
        "view-v1",
        "public",
        "versions",
        "definition",
        ("part", "lid"),
        "pietto_query",
        "provider guarantee of retained immutable complete domain",
    )
    verify_requirement(requirement, (source,))
    _, other = product.build_source(tmp_path / "foreign_source", "postgres")
    with pytest.raises(ValueError, match="SOURCE_ROOT"):
        verify_requirement(requirement, other.request.sources)
    with pytest.raises(ValueError, match="SOURCE_TOKENS"):
        verify_requirement(
            replace(requirement, token_columns=("part", "part")), (source,)
        )


def test_real_unfulfilled_obligation_is_refused_before_connect(tmp_path, monkeypatch):
    import _pietto_phase66_sql_emission_probe as probe
    from pietto._project.project_completed_semantics import (
        with_project_single_match_requests,
    )
    from pietto._project.project_single_match import ProjectSingleMatchRequest
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
        build_project_query_block_ir_analysis_bundle,
    )
    from pietto._project.project_sql_plan import ProjectSQLPlan, build_project_sql_plan
    from pietto._project.project_sql_plan_verification import verify_project_sql_plan
    from pietto._project.project_sql_emission import emit_project_sql

    item = probe.join_witness(
        "postgres",
        """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on true
    select:
        value = lhs.id
""",
    )
    initial, _ = probe.build_case(
        tmp_path / "obligation", item["source"], item["contract"]
    )
    condition = initial.completed.roots.join_conditions.entries[0]
    completed = with_project_single_match_requests(
        initial.completed,
        (ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use),),
    )
    ir = build_project_query_block_ir(completed)
    bundle = build_project_query_block_ir_analysis_bundle(
        verify_project_query_block_ir(ir)
    )
    selected = next(o for o in ir.owners if o.definition.name == "result")
    plan = build_project_sql_plan(completed, bundle, selected)
    assert isinstance(plan, ProjectSQLPlan)
    checked = verify_project_sql_plan(plan, completed, bundle, selected)
    outcome = emit_project_sql(checked, item["contract"].encode())
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1006", "original_enforcement_not_fulfilled")
    ]
    assert plan.single_matches and all(
        m.downstream_enforcement_required for m in plan.single_matches
    )
    calls = []
    monkeypatch.setattr(pg, "_connect", lambda request: calls.append(request))
    with pytest.raises((execution.ExecutionError, ResultError, ValueError)):
        execution.prepare_execution(
            cast(Any, outcome.artifact),
            execution.PostgresAccess(
                "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
            ),
        )
    assert not calls


def test_grafted_resource_rejection_closes_only_owned_handles(request_, monkeypatch):
    owned, foreign = Connection(), Connection()
    install(monkeypatch, owned)
    stream = pg.PostgresExecution(request_).open()
    stream._connection = foreign
    with pytest.raises(execution.ExecutionError, match="RESOURCE_IDENTITY"):
        next(stream)
    assert owned.closed and not foreign.closed and not foreign.operations


def test_explicit_access_refuses_ambient_libpq_redirect(request_, monkeypatch):
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.1")
    calls = []
    monkeypatch.setattr(pg.importlib, "import_module", lambda _: calls.append(True))
    with pytest.raises(execution.ExecutionError, match="AMBIENT_CONNECTION"):
        pg.PostgresExecution(request_).open()
    assert not calls


def test_registry_boolean_and_extra_rows_cannot_admit_source(request_):
    from pietto._project.project_execution_source import (
        admit_postgres_source,
        SourceAdmissionError,
    )

    source = request_.artifact.request.sources[0]
    req = RetainedSourceRequirement(
        source,
        "p",
        "v",
        "r",
        "public",
        "versions",
        "view",
        ("id",),
        "pietto_query",
        "retained complete domain",
    )
    for rows in ([("p", "v", True, "r")], [("p", "v", 1, "r")] * 2):

        class Registry(Cursor):
            def execute(self, sql, params=None, prepare=None):
                assert sql.endswith("LIMIT 2")

            def fetchall(self):
                return rows

        conn = SimpleNamespace(cursor=lambda: Registry(Connection()))
        with pytest.raises(SourceAdmissionError, match="VERSION_OR_RETENTION"):
            admit_postgres_source(conn, req, role="pietto_query", session_id=1)


def test_real_predicate_keeps_existing_pb_boundary(tmp_path, monkeypatch):
    import _pietto_phase66_sql_emission_probe as probe

    text = product.source("postgres").replace(
        "    select:", "    where id > 1\n    select:"
    )
    import json

    contract = json.loads(product.emission_input("postgres"))
    contract["environment"].append(
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
    )
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended",
        }
    )
    _, outcome = probe.build_case(
        tmp_path / "predicate", text, json.dumps(contract), "bind_safe_literals"
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert outcome.artifact.parameter_uses
    calls = []
    monkeypatch.setattr(pg, "_connect", lambda request: calls.append(True))
    with pytest.raises(ResultError, match="PRODUCER_UNSUPPORTED"):
        execution.prepare_execution(
            outcome.artifact,
            execution.PostgresAccess(
                "127.0.0.1", 5432, "test", "pietto_query", "private", "disable"
            ),
        )
    assert not calls


def test_injected_post_buffer_read_cancel_preserves_incomplete(request_, monkeypatch):
    conn = Connection()
    install(monkeypatch, conn)
    stream = pg.PostgresExecution(request_)
    with stream:
        next(stream)
        original = Cursor.fetchmany

        class Canceled(RuntimeError):
            sqlstate = "57014"
            diag = SimpleNamespace(
                message_primary="canceling statement due to user request"
            )

        def fail(cursor, size):
            if cursor.position:
                stream.cancel()
                raise Canceled("injected read cancellation after native buffer")
            return original(cursor, size)

        monkeypatch.setattr(Cursor, "fetchmany", fail)
        with pytest.raises(Canceled):
            next(stream)
    out = stream.outcome
    assert out.source == "FAILED" and out.delivery == "FAILED" and out.rows == 2
    assert out.cancel_requested and out.cancel_sent and out.cancel_observed
    assert conn.closed and stream.control_joined
