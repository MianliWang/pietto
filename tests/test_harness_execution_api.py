"""The public execution witnesses' own laws: the probe's database-free consumer
cases run against the checkout and satisfy the independent checker, the
checker accepts the facts a passing family records and refuses each damaged
fact, and the PostgreSQL fixture is the documented setup the oracles
describe. No database, Docker, network or installation."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

import _pietto_execution_api as api
import _pietto_execution_api_check as check
import _pietto_execution_api_probe as probe

ROOT = Path(__file__).resolve().parents[1]


def test_importing_the_witness_modules_acquires_nothing(tmp_path):
    code = (
        "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]];"
        "import _pietto_execution_api_probe, _pietto_execution_api_check;"
        "print(sorted({m.split('.')[0] for m in sys.modules}"
        " & {'psycopg', 'pyarrow', 'pietto', 'docker'}))"
    )
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            code,
            str(ROOT / "tests"),
            str(ROOT / "src"),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]" and list(tmp_path.iterdir()) == []


@pytest.fixture(scope="module")
def checkout_facts(tmp_path_factory):
    """The consumer cases, each a fresh `-I` worker, with the checkout first on
    sys.path instead of an installed wheel."""
    return probe.consumer_cases(
        sys.executable,
        tmp_path_factory.mktemp("execution-witness") / "cases",
        path=[str(ROOT / "src")],
    )


def test_checkout_consumer_cases_satisfy_the_checker(checkout_facts):
    check.check_consumer_cases(checkout_facts)
    assert all(
        record.get("connected") is False
        for record in (*checkout_facts["ambient"].values(), checkout_facts["shadow"])
    )


@pytest.mark.parametrize(
    "damage,reason",
    (
        (
            lambda f: f["imports"]["result"].update(after_import=["psycopg"]),
            "IMPORT_LOADED_DRIVER",
        ),
        (lambda f: f["imports"].update(connected=True), "IMPORT_CONNECTED"),
        (
            lambda f: f["imports"]["result"]["refusals"].update(sql_text=None),
            "REQUEST_REFUSALS",
        ),
        (lambda f: f["ambient"].pop("OPENSSL_CONF"), "AMBIENT_DENOMINATOR"),
        (
            lambda f: f["ambient"]["PGHOST"]["result"].update(code="PIE-R2004"),
            "AMBIENT_PGHOST",
        ),
        (
            lambda f: f["ambient"]["SSLKEYLOGFILE"].update(keylog_created=True),
            "KEYLOG_OPENED",
        ),
        (
            lambda f: f["ambient"]["PGSERVICE"]["result"].update(shown=True),
            "CREDENTIAL",
        ),
        (lambda f: f["shadow"].update(shadow_connected=True), "SHADOW_CONNECTED"),
        (
            lambda f: f["shadow"]["result"].update(psycopg_file=None),
            "SHADOW_NOT_IMPORTED",
        ),
        (
            lambda f: f["identity"]["stray"]["result"].update(identity="0" * 64),
            "IDENTITY_FOLLOWS_CWD",
        ),
        (
            lambda f: f["identity"]["stray"]["result"].update(metadata="4.13.2"),
            "IDENTITY_CONTROL",
        ),
        (
            lambda f: f["identity"]["clean"]["result"].update(metadata="9.9.9"),
            "IDENTITY_CONTROL",
        ),
        (
            lambda f: [
                f["identity"][where]["result"].update(identity="0" * 63)
                for where in ("clean", "stray")
            ],
            "IDENTITY",
        ),
        (lambda f: f["shadow"].update(shadow_imported=False), "SHADOW_NOT_IMPORTED"),
    ),
)
def test_the_checker_refuses_each_damaged_consumer_fact(checkout_facts, damage, reason):
    facts = copy.deepcopy(checkout_facts)
    damage(facts)
    with pytest.raises(check.Rejected, match="^" + reason + "$"):
        check.check_consumer_cases(facts)


def _install(*recipes):
    steps = {step: {"returncode": 0} for step in ("venv", "install", "check")}
    return {recipe: {**steps, "python": list(check.INTERPRETER)} for recipe in recipes}


def consumer_report(cases):
    """A report with the facts a passing consumer family records around the
    checkout's consumer cases."""
    return {
        "format": check.FORMAT,
        "family": "consumer",
        "install": _install("core", "execute-postgres"),
        "core": {
            "returncode": 0,
            "connected": False,
            "result": {
                "after_import": [],
                "unopened": [[], "NOT_STARTED", False],
                "code": "PIE-R2001",
                "detail": "EXECUTION_DEPENDENCY_MISSING",
                "shown": False,
                "chained": False,
                "outcome": {
                    "end": "FAILED",
                    "transaction": "NOT_STARTED",
                    "cleanup": "CLOSED",
                },
                "after_open": [],
            },
        },
        "cases": copy.deepcopy(cases),
    }


def test_the_checker_accepts_the_consumer_facts(checkout_facts):
    assert check.check(consumer_report(checkout_facts)) == {
        "family": "consumer",
        "verdict": "ACCEPTED",
    }


@pytest.mark.parametrize(
    "damage,reason",
    (
        (lambda r: r["install"]["core"]["install"].update(returncode=1), "INSTALL"),
        (
            lambda r: r["install"]["execute-postgres"].update(
                python=["CPython", "3.12.14", "Linux", "x86_64"]
            ),
            "INTERPRETER",
        ),
        (lambda r: r["core"]["result"].update(code="PIE-R2002"), "CORE_FALLBACK"),
        (lambda r: r["core"].update(connected=True), "CORE_FALLBACK"),
        (
            lambda r: r["core"]["result"].update(after_open=["psycopg"]),
            "CORE_LOADED_DRIVER",
        ),
        (
            lambda r: r["core"]["result"].update(unopened=[[], "OPEN", False]),
            "UNOPENED_EFFECT",
        ),
        (
            lambda r: r["cases"]["ambient"]["OPENSSL_CONF"]["result"].update(
                after_open=["pyarrow"]
            ),
            "AMBIENT_LOADED_DRIVER",
        ),
        (lambda r: r["install"].pop("core"), "INSTALL"),
        (lambda r: r["core"].update(returncode=1), "CORE_FALLBACK"),
        (lambda r: r["core"].update(result=None), "CORE_FALLBACK"),
        (
            lambda r: r["core"]["result"]["outcome"].update(end="OPEN"),
            "CORE_FALLBACK",
        ),
    ),
)
def test_the_checker_refuses_each_damaged_consumer_report(
    checkout_facts, damage, reason
):
    report = consumer_report(checkout_facts)
    damage(report)
    with pytest.raises(check.Rejected, match="^" + reason + "$"):
        check.check(report)


def _outcome(end, transaction, cleanup="CLOSED", rows=0, primary=None):
    ack = transaction in ("COMMIT_ACK", "ROLLBACK_ACK")
    return {
        "end": end,
        "source": "EOF",
        "transaction": transaction,
        "delivery": "COMPLETE",
        "cleanup": cleanup,
        "remote": "TRANSACTION_ACK" if ack else "REMOTE_QUIESCENCE_UNCONFIRMED",
        "rows": rows,
        "batches": 1,
        "primary": primary,
        "cleanup_failures": [],
    }


def _ok(value):
    return {"returncode": 0, "result": value}


def _failure(
    code, detail, cause, transaction, cleanup="CLOSED", sqlstate=None, **extra
):
    return _ok(
        {
            "code": code,
            "detail": detail,
            "cause": cause,
            "sqlstate": sqlstate,
            "shown": False,
            "chained": False,
            "outcome": _outcome(
                "FAILED",
                transaction,
                cleanup,
                primary=[code, detail, extra.pop("phase", "check"), sqlstate, cause],
            ),
            **extra,
        }
    )


def _effects():
    files = {"cwd": ["demo-exec", "demo-exec/main.pietto"], "home": [], "tmp": []}
    return {
        "before": {"threads": ["MainThread"], "jobs": [], "files": files},
        "after": {"threads": ["MainThread"], "jobs": [], "files": copy.deepcopy(files)},
    }


def postgres_report():
    """A report with the facts a passing postgres family records."""
    example = "\n".join(
        (
            check.EXAMPLE_REPR,
            "[{'id': 3, 'label': 'three'}, {'id': 2, 'label': 'two'}]",
            "[{'id': 5, 'label': 'five'}, {'id': 2, 'label': 'two'}]",
            "COMPLETE COMMIT_ACK CLOSED",
            "PIE-R1001 INPUT_MISSING",
        )
    )
    timeout = _failure(
        "PIE-R3002",
        None,
        "QueryCanceled",
        "UNKNOWN",
        "FAILED",
        "57014",
        phase="execute",
        opened=1.4,
        seconds=11.6,
    )
    timeout["result"]["outcome"]["cleanup_failures"] = [
        ["PIE-R5001", "transaction", "ExecutionError"]
    ]
    return {
        "format": check.FORMAT,
        "family": "postgres",
        "install": _install("execute-postgres"),
        "server": {
            "version": "180006",
            "ssl": "on",
            "password_encryption": "scram-sha-256",
            "reader_settings": ["statement_timeout=0"],
            "hba": [
                ["local", ["all"], "trust", None],
                ["host", ["pietto_trust"], "trust", None],
                ["host", ["pietto_cleartext"], "password", None],
                ["host", ["pietto_md5"], "md5", None],
                ["hostssl", ["pietto_reader"], "scram-sha-256", None],
                ["host", ["pietto_reader"], "scram-sha-256", None],
                ["host", ["pietto_manager"], "scram-sha-256", None],
            ],
            "hashes": [
                ["pietto_cleartext", True, False],
                ["pietto_md5", False, True],
                ["pietto_reader", True, False],
                ["pietto_trust", None, None],
            ],
        },
        "example": {"returncode": 0, "stdout": example + "\n", "shown": False},
        "example_loopback": {"returncode": 0, "stdout": example + "\n", "shown": False},
        "bind_safe": _ok(
            {
                "rows": sorted(check.ROWS),
                "outcome": _outcome("COMPLETE", "COMMIT_ACK", rows=4),
                **_effects(),
            }
        ),
        "early_stop": _ok(
            {
                "first_rows": 1,
                "outcome": _outcome("STOPPED_EARLY", "ROLLBACK_ACK", rows=1),
                **_effects(),
            }
        ),
        "result_check": _failure(
            "PIE-R3005", "VALUE_DOMAIN", "ResultError", "ROLLBACK_ACK"
        ),
        "authentication": {
            role: _failure(
                "PIE-R2004", None, "OperationalError", "NOT_STARTED", phase="admission"
            )
            for role in check.ROLES
        },
        "statement_timeout": timeout,
        "dropped": {
            "returncode": 0,
            "result": {"warnings": [["PIE-R5002", "DROPPED", True]], "dropped_at": 1.0},
            "during": 1,
            "tls": [[True, "TLSv1.3"]],
            "exit_delay": 3.4,
            "after": 0,
        },
        "cleanup": {"status": "success"},
    }


def test_the_checker_accepts_the_postgres_oracle_facts():
    assert check.check(postgres_report()) == {
        "family": "postgres",
        "verdict": "ACCEPTED",
    }


@pytest.mark.parametrize(
    "damage,reason",
    (
        (lambda r: r.update(format="other"), "ENVELOPE"),
        (lambda r: r.update(family="other"), "ENVELOPE"),
        (lambda r: r["install"].pop("execute-postgres"), "INSTALL"),
        (lambda r: r["server"]["hashes"][0].__setitem__(1, False), "SCRAM_ROLE"),
        (lambda r: r["bind_safe"].update(returncode=1), "BIND_SAFE"),
        (lambda r: r["bind_safe"]["result"].update(outcome=None), "BIND_SAFE"),
        (
            lambda r: r["bind_safe"]["result"]["before"]["files"].pop("tmp"),
            "BIND_SAFE_FILES",
        ),
        (
            lambda r: [
                r["bind_safe"]["result"][when]["files"]["home"].append(".pietto")
                for when in ("before", "after")
            ],
            "BIND_SAFE_FILES",
        ),
        (lambda r: r["early_stop"].update(result=None), "EARLY_STOP"),
        (lambda r: r["early_stop"]["result"].update(first_rows=2), "EARLY_STOP"),
        (
            lambda r: r["authentication"]["pietto_trust"]["result"].update(shown=True),
            "CREDENTIAL",
        ),
        (
            lambda r: r["authentication"]["pietto_cleartext"]["result"].update(
                chained=True
            ),
            "CREDENTIAL",
        ),
        (
            lambda r: r["authentication"]["pietto_md5"]["result"]["outcome"].update(
                transaction="OPEN"
            ),
            "AUTH_pietto_md5",
        ),
        (
            # Another server error ending the statement inside the window
            # (here a lock timeout) is not the statement limit.
            lambda r: r["statement_timeout"]["result"].update(
                code="PIE-R3003", sqlstate="55P03"
            ),
            "STATEMENT_TIMEOUT",
        ),
        (
            lambda r: r["statement_timeout"]["result"].update(code="PIE-R3001"),
            "STATEMENT_TIMEOUT",
        ),
        (
            lambda r: r["statement_timeout"]["result"]["outcome"].update(
                end="DEADLINE"
            ),
            "STATEMENT_TIMEOUT_END",
        ),
        (
            lambda r: r["install"]["execute-postgres"]["check"].update(returncode=1),
            "INSTALL",
        ),
        (
            lambda r: r["install"]["execute-postgres"].update(python=None),
            "INTERPRETER",
        ),
        (lambda r: r["server"].update(version="180005"), "SERVER_VERSION"),
        (lambda r: r["server"].update(ssl="off"), "SERVER_TLS"),
        (lambda r: r["server"].update(password_encryption="md5"), "SCRAM_DEFAULT"),
        (lambda r: r["server"].update(reader_settings=None), "READER_STATEMENT_LIMIT"),
        (lambda r: r["server"]["hba"][4].__setitem__(3, "bad line"), "HBA_ERROR"),
        (lambda r: r["server"]["hba"][4].__setitem__(0, "host"), "HBA_METHODS"),
        (lambda r: r["server"]["hba"][4].__setitem__(2, "md5"), "HBA_METHODS"),
        (
            lambda r: r["server"]["hba"].insert(0, ["host", ["all"], "trust", None]),
            "HBA_METHODS",
        ),
        (lambda r: r["server"]["hashes"][2].__setitem__(1, False), "SCRAM_ROLE"),
        (lambda r: r["server"]["hashes"][1].__setitem__(2, False), "MD5_ROLE"),
        (lambda r: r["example_loopback"].update(returncode=1), "EXAMPLE"),
        (
            lambda r: r["example"].update(
                stdout=r["example"]["stdout"].replace(
                    "release='18.6'", "release='18.5'"
                )
            ),
            "EXAMPLE_COMPILE",
        ),
        (
            lambda r: r["example"].update(
                stdout=r["example"]["stdout"].replace(
                    "COMPLETE COMMIT_ACK CLOSED", "[]\nCOMPLETE COMMIT_ACK CLOSED"
                )
            ),
            "EXAMPLE_BATCH",
        ),
        (
            lambda r: r["example"].update(
                stdout=r["example"]["stdout"].replace("five", "six")
            ),
            "EXAMPLE_ROWS",
        ),
        (
            lambda r: r["example"].update(
                stdout=r["example"]["stdout"].replace(
                    "COMPLETE COMMIT_ACK", "FAILED UNKNOWN"
                )
            ),
            "EXAMPLE_END",
        ),
        (lambda r: r["example"].update(shown=True), "CREDENTIAL"),
        (
            lambda r: r["bind_safe"]["result"].update(rows=check.ROWS[:3]),
            "BIND_SAFE_ROWS",
        ),
        (
            lambda r: r["bind_safe"]["result"]["outcome"].update(cleanup="FAILED"),
            "BIND_SAFE_END",
        ),
        (
            lambda r: r["bind_safe"]["result"]["after"].update(
                threads=["MainThread", "pietto-deadline-x"]
            ),
            "BIND_SAFE_THREADS",
        ),
        (
            lambda r: r["bind_safe"]["result"]["after"].update(
                jobs=["pietto._project.project_job_store"]
            ),
            "BIND_SAFE_WORKSPACE",
        ),
        (
            lambda r: r["early_stop"]["result"]["outcome"].update(
                transaction="COMMIT_ACK", remote="TRANSACTION_ACK"
            ),
            "EARLY_STOP_END",
        ),
        (
            lambda r: r["early_stop"]["result"]["after"]["files"]["home"].append(
                ".pietto"
            ),
            "EARLY_STOP_FILES",
        ),
        (
            lambda r: r["early_stop"]["result"]["after"]["files"]["cwd"].append(
                "workspace.sqlite"
            ),
            "EARLY_STOP_FILES",
        ),
        (
            lambda r: r["result_check"]["result"].update(code="PIE-R3999"),
            "RESULT_CHECK",
        ),
        (
            lambda r: r["result_check"]["result"]["outcome"].update(cleanup="FAILED"),
            "RESULT_CHECK_END",
        ),
        (
            lambda r: r["authentication"]["pietto_md5"]["result"].update(
                code="PIE-R3003"
            ),
            "AUTH_pietto_md5",
        ),
        (lambda r: r["authentication"].pop("pietto_trust"), "AUTH_DENOMINATOR"),
        (
            lambda r: r["statement_timeout"]["result"].update(seconds=3.0),
            "STATEMENT_TIMEOUT_SECONDS",
        ),
        (
            lambda r: r["statement_timeout"]["result"].update(seconds=10.4),
            "STATEMENT_TIMEOUT_SECONDS",
        ),
        (
            lambda r: r["statement_timeout"]["result"].update(seconds=16.4),
            "STATEMENT_TIMEOUT_SECONDS",
        ),
        (
            lambda r: r["statement_timeout"]["result"].pop("opened"),
            "STATEMENT_TIMEOUT_SECONDS",
        ),
        (
            lambda r: r["statement_timeout"]["result"]["outcome"].update(
                remote="TRANSACTION_ACK"
            ),
            "STATEMENT_TIMEOUT",
        ),
        (
            lambda r: r["statement_timeout"]["result"]["outcome"][
                "primary"
            ].__setitem__(2, "read"),
            "STATEMENT_TIMEOUT_PHASE",
        ),
        (
            lambda r: r["statement_timeout"]["result"]["outcome"].update(
                transaction="ROLLBACK_ACK", remote="TRANSACTION_ACK"
            ),
            "STATEMENT_TIMEOUT_END",
        ),
        (
            lambda r: r["statement_timeout"]["result"]["outcome"].update(
                cleanup_failures=[]
            ),
            "STATEMENT_TIMEOUT_END",
        ),
        (lambda r: r["dropped"].update(returncode=1), "DROPPED"),
        (lambda r: r["dropped"]["result"].update(warnings=[]), "DROPPED_WARNING"),
        (lambda r: r["dropped"].update(during=0), "DROPPED_SESSION"),
        (lambda r: r["dropped"].update(tls=[[False, None]]), "ACTUAL_TLS"),
        (lambda r: r["dropped"].update(tls=[]), "ACTUAL_TLS"),
        (lambda r: r["dropped"].update(exit_delay=0.1), "DROPPED_EXIT_DELAY"),
        (lambda r: r["dropped"].update(after=1), "DROPPED_SESSION_LEFT"),
        (lambda r: r["cleanup"].update(status="failed"), "RESOURCE_CLEANUP"),
    ),
)
def test_the_checker_refuses_each_damaged_postgres_fact(damage, reason):
    report = postgres_report()
    damage(report)
    with pytest.raises(check.Rejected, match="^" + reason + "$"):
        check.check(report)


def test_the_fixture_is_the_documented_setup_and_hides_every_password():
    """The fixture runs the documented relation and role statements (database
    `app` replaced), its rows are the oracle's, the reader's password reaches
    the server only as a verifier, and pg_hba.conf has the documented reader
    lines in place, first match first."""
    passwords = {role: f"secret-{n}" for n, role in enumerate(probe.ROLES)}
    statements = probe.statements(passwords)
    relation = api.statements(api.example_blocks()["sql"])
    assert list(statements[: len(relation)]) == relation
    insert = relation[-1].removeprefix("INSERT INTO fixture.items VALUES ")
    assert ast.literal_eval("[" + insert + "]") == list(probe.ROWS)
    kept = [list(row) for row in probe.ROWS if row[0] > 1]
    assert sorted(kept) == sorted(check.ROWS)
    assert all(0 <= row[0] <= 100 for row in probe.ROWS)
    assert any(row[0] > 100 for row in probe.WIDE_ROWS)
    role = [
        s.replace(" DATABASE app ", " DATABASE phase66 ")
        for s in api.statements(api.setup_blocks()["sql"])
    ]
    assert all(s in statements for s in role)
    assert "ALTER ROLE pietto_reader SET statement_timeout = 0" in statements
    with_secret = [s for s in statements if any(p in s for p in passwords.values())]
    assert [s.split()[2] for s in with_secret] == ["pietto_cleartext", "pietto_md5"]
    md5 = statements.index("SET password_encryption = 'md5'")
    assert statements[md5 + 1].startswith("CREATE ROLE pietto_md5")
    assert statements[md5 + 2] == "RESET password_encryption"
    lines = [line.split() for line in probe.hba()]
    assert [(m[0], m[2], m[-1]) for m in lines] == [
        (row[0], row[1][0], row[2]) for row in check.HBA
    ]
    assert {m[2]: m[-1] for m in lines if m[2] in probe.ROLES} == probe.ROLES
    assert json.loads(json.dumps(postgres_report())) == postgres_report()


class _Cursor:
    def __init__(self, executed):
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement):
        text = statement if type(statement) is str else statement.as_string(None)
        self.executed.append(text)


def test_the_reader_password_is_set_as_the_documented_password_command():
    """Like psql's `\\password`, only a verifier libpq computed reaches the
    server, after the documented SET commands that keep the session from
    logging it and choose SCRAM-SHA-256."""
    executed: list[str] = []
    requested = []

    def encrypt(password, user, algorithm=None):
        requested.append((password, user, algorithm))
        return b"SCRAM-SHA-256$4096:c2FsdA==$c3RvcmVk:c2VydmVy"

    manager = type(
        "Manager",
        (),
        {
            "cursor": lambda self: _Cursor(executed),
            "pgconn": type("PGconn", (), {"encrypt_password": staticmethod(encrypt)})(),
        },
    )()
    probe.set_password(manager, "pietto_reader", "never-sent")
    assert requested == [(b"never-sent", b"pietto_reader", None)]
    assert executed == [
        "SET log_statement = 'none'",
        "SET log_min_error_statement = 'panic'",
        "SET password_encryption = 'scram-sha-256'",
        'ALTER USER "pietto_reader" PASSWORD'
        " 'SCRAM-SHA-256$4096:c2FsdA==$c3RvcmVk:c2VydmVy'",
    ]
