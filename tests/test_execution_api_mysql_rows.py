"""Public MySQL rows route checks that need no MySQL service."""

from __future__ import annotations

import copy
import pickle
from types import SimpleNamespace

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_execution as ex
from pietto._project import project_public_execution as composition


PASSWORD = "pw-mysql-never-shown"
ACCESS = execution.MySQLAccess(
    "mysql.example.test", 3306, "app", "reader", PASSWORD, "/ca.pem", "reader"
)
PREMISE = execution.MySQLDeploymentPremise(schemas=("fixture",))


@pytest.fixture(scope="module")
def query(tmp_path_factory):
    postgres = execution.compile_query(
        api.write_example(tmp_path_factory.mktemp("execution-mysql-public")),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    mysql = object.__new__(execution.CompiledQuery)
    for slot in execution.CompiledQuery.__slots__:
        object.__setattr__(mysql, slot, getattr(postgres, slot))
    object.__setattr__(mysql, "_dialect", "mysql")
    return mysql


def test_mysql_access_and_premise_redact_and_refuse_copy():
    assert "password=<redacted>" in repr(ACCESS)
    assert PASSWORD not in repr(ACCESS)
    for value in (ACCESS, PREMISE):
        for duplicate in (pickle.dumps, copy.copy, copy.deepcopy):
            with pytest.raises(TypeError):
                duplicate(value)


def test_mysql_route_dispatches_one_private_owner_with_fixed_profile(
    query, monkeypatch
):
    captured = {}
    owner = SimpleNamespace(attempt="mysql-attempt")

    def prepare(template, access, **options):
        captured.update(template=template, access=access, options=options)
        return owner

    monkeypatch.setattr(composition, "prepare_mysql_attempt", prepare)
    handle = execution.execute(
        query,
        route="mysql_rows",
        access=ACCESS,
        premise=PREMISE,
        values=(7,),
    )
    assert handle.route == "mysql_rows" and handle.attempt == "mysql-attempt"
    private = captured["access"]
    assert type(private) is ex.MySQLAccess
    assert (
        private.host,
        private.port,
        private.database,
        private.user,
        private.password,
        private.ca_file,
        private.account,
        private.roles,
        private.verify_identity,
        private.loopback_tls_exception,
        private.transaction_observation,
    ) == (
        "mysql.example.test",
        3306,
        "app",
        "reader",
        PASSWORD,
        "/ca.pem",
        "reader",
        "NONE",
        True,
        False,
        "performance_schema_own_transaction",
    )
    assert captured["options"] == {
        "schemas": ("fixture",),
        "limits": ex.ExecutionLimits(),
        "isolation": "stable",
        "values": (7,),
        "parameters": None,
    }


@pytest.mark.parametrize("host", ("/run/mysql", "@mysql", "one,two"))
def test_mysql_host_forms_are_refused_before_the_bridge(query, monkeypatch, host):
    monkeypatch.setattr(
        composition,
        "prepare_mysql_attempt",
        lambda *args, **kwargs: pytest.fail("refused host reached MySQL bridge"),
    )
    access = execution.MySQLAccess(
        host, 3306, "app", "reader", PASSWORD, "/ca.pem", "reader"
    )
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(query, route="mysql_rows", access=access, premise=PREMISE)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    )


@pytest.mark.parametrize("host", (None, 3306, b"mysql", ["mysql"]))
def test_mysql_non_string_host_reaches_private_access_validation(
    query, monkeypatch, host
):
    def refuse(*args, **kwargs):
        raise ex.ExecutionError("EXECUTION_ACCESS")

    monkeypatch.setattr(composition, "prepare_mysql_attempt", refuse)
    access = execution.MySQLAccess(
        host, 3306, "app", "reader", PASSWORD, "/ca.pem", "reader"
    )
    with pytest.raises(execution.RequestRejected) as rejected:
        execution.execute(query, route="mysql_rows", access=access, premise=PREMISE)
    assert (rejected.value.code, rejected.value.detail) == (
        "PIE-R1002",
        "EXECUTION_ACCESS",
    )


def test_mysql_ambient_refusal_precedes_private_owner_import(monkeypatch):
    calls = []

    def refuse():
        calls.append("ambient")
        raise ex.ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")

    monkeypatch.setattr(ex, "refuse_ambient", refuse)
    with pytest.raises(ex.ExecutionError, match="EXECUTION_AMBIENT_CONNECTION_PROFILE"):
        composition.prepare_mysql_attempt(
            object(),
            object(),
            schemas=("fixture",),
            limits=object(),
            isolation="stable",
        )
    assert calls == ["ambient"]


def test_mysql_ambient_refusal_uses_the_existing_public_code(query, monkeypatch):
    def refuse(*args, **kwargs):
        raise ex.ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")

    monkeypatch.setattr(composition, "prepare_mysql_attempt", refuse)
    with pytest.raises(execution.RequestRejected) as rejected:
        execution.execute(query, route="mysql_rows", access=ACCESS, premise=PREMISE)
    assert (rejected.value.code, rejected.value.detail) == (
        "PIE-R2003",
        "EXECUTION_AMBIENT_CONNECTION_PROFILE",
    )


@pytest.fixture(scope="module")
def parameterized(tmp_path_factory):
    """A MySQL query that declares parameters, compiled from its own contract."""
    import _pietto_sql_emission as probe

    item = probe.fixture("mysql", "Q_query_parameters", "preserve")
    project = tmp_path_factory.mktemp("execution-mysql-parameters")
    (project / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (project / "main.pietto").write_text(item["source"], encoding="utf-8")
    (project / "contract.json").write_text(item["contract"], encoding="utf-8")
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="mysql",
        emission_contract="contract.json",
    )


class Submitted(Exception):
    """Stops a statement at the driver's execute call."""


def test_mysql_route_binds_parameters_with_one_marker_per_read(parameterized):
    """MySQL sends one `?` per read: `low` twice, `label` once, in rendering
    order, with the template's exact SQL for every binding, and the reader
    prepares that SQL and executes it with those values (a NULL included)
    up to the driver."""
    assert parameterized.dialect == "mysql"
    assert parameterized.parameters == (("low", "Int", False), ("label", "Text", True))
    template = parameterized._template.artifact.rendered.sql
    submitted = []

    class Connection:
        unread_result = False

        def cmd_stmt_prepare(self, sql, **options):
            submitted.append(sql)
            return {
                "statement_id": 1,
                "warning_count": 0,
                "num_params": 3,
                "parameters": [(None,) * 9] * 3,
                "num_columns": 0,
                "columns": [],
            }

        def cmd_stmt_execute(self, statement_id, *, data, **options):
            submitted.append(data)
            raise Submitted

    for parameters, arguments in (
        ({"low": 10, "label": "x"}, (10, "x", 10)),
        ({"label": None, "low": -5}, (-5, None, -5)),
    ):
        owner = composition.prepare_mysql_attempt(
            parameterized._template,
            ex.MySQLAccess(
                "mysql.example.test",
                3306,
                "app",
                "reader",
                PASSWORD,
                "/ca.pem",
                "reader",
                verify_identity=True,
                loopback_tls_exception=False,
            ),
            schemas=("phase66",),
            limits=ex.ExecutionLimits(),
            isolation="stable",
            parameters=parameters,
        )
        assert owner.request.binding.arguments == arguments
        assert owner.request.artifact.rendered.sql == template
        # One native occurrence per read (the fixture's identifiers hold `?`).
        assert len(owner.request.artifact.parameter_uses) == len(arguments)
        # Only the open session is stood in for; submission is the reader's.
        owner._connection = owner._owned_connection = Connection()
        owner._verify_lifetime = lambda: None
        with pytest.raises(Submitted):
            owner._submit(template, ex.execution_arguments(owner.request), "query")
        assert submitted == [template, arguments]
        submitted.clear()


@pytest.mark.parametrize(
    "parameters,code,detail",
    (
        (None, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": 1}, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": True, "label": None}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": None, "label": None}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": 1, "label": 1}, "PIE-R1006", "BINDING_PARAMETER:1:Text"),
        ({"low": 2**63 - 1, "label": None}, "PIE-R1004", "BINDING_INVALID"),
        ({1: 1, "label": None}, "PIE-R1002", "PUBLIC_PARAMETERS_TYPE"),
    ),
    ids=("missing", "absent", "bool", "null", "int_text", "overflow", "key"),
)
def test_mysql_route_refuses_each_parameter_input_before_the_owner(
    parameterized, monkeypatch, parameters, code, detail
):
    from pietto._project import project_execution_mysql as mysql

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the MySQL owner")

    monkeypatch.setattr(mysql.MySQLExecution, "__init__", forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(
            parameterized,
            route="mysql_rows",
            access=ACCESS,
            premise=PREMISE,
            parameters=parameters,
        )
    assert (refused.value.code, refused.value.detail) == (code, detail)


def test_mysql_refuses_a_zero_source_values_query_before_connect(tmp_path):
    """No non-vacuous MySQL qualification exists for a statement without a
    physical relation, so the compiled route is refused before any socket."""
    import json

    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + "\nquery seeded:\n    values(id: Int):\n        1\n",
        encoding="utf-8",
    )
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    contract["sources"] = []
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    postgres = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="seeded",
        dialect="postgres",
        emission_contract="contract.json",
    )
    mysql = object.__new__(execution.CompiledQuery)
    for slot in execution.CompiledQuery.__slots__:
        object.__setattr__(mysql, slot, getattr(postgres, slot))
    object.__setattr__(mysql, "_dialect", "mysql")
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(mysql, route="mysql_rows", access=ACCESS, premise=PREMISE)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1003",
        "MYSQL_ZERO_SOURCE_ROUTE",
    )
    assert refused.value.attempt is None


def test_mysql_compile_blocks_a_statement_without_a_physical_source(tmp_path):
    """compile_query reports a MySQL statement whose only input is a VALUES
    body as the command's BLOCKED document, before any execution exists."""
    import json

    project = api.write_join_witness(
        tmp_path / "mysql",
        "mysql",
        "query result:\n    values(id: Int):\n        1\n",
    )
    with pytest.raises(execution.CompileRejected) as refused:
        execution.compile_query(
            project,
            module="main.pietto",
            kind="query",
            name="result",
            dialect="mysql",
            emission_contract="contract.json",
        )
    assert refused.value.status == "BLOCKED"
    document = json.loads(refused.value.emission)
    assert [(b["code"], b["subject"]["detail"]) for b in document["blockers"]] == [
        ("PIE-B1003", "zero_physical_source_not_admitted_on_target")
    ]
