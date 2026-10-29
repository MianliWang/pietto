"""The public execution witnesses' own laws: the probe's database-free consumer
cases run against the checkout and satisfy the independent checker, the
checker accepts the facts a passing family records and refuses each damaged
fact, and the PostgreSQL fixture and the bundle oracles are the documented
setup and output. The Phase70 joint acceptance runs its database-free facts
against the checkout and its native steps against a stand-in owner, and its
checker refuses each damaged fact. No database, Docker, network or
installation."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
import inspect
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

import _pietto_execution_api as api
import _pietto_execution_api_check as check
import _pietto_execution_api_probe as probe
import _pietto_execution_joint_acceptance as joint
import _pietto_execution_joint_acceptance_check as joint_check

ROOT = Path(__file__).resolve().parents[1]


def test_mysql_consumer_checker_accepts_its_literal_facts_and_refuses_damage():
    command = {"returncode": 0}
    install = {
        recipe: {
            "venv": command,
            "install": command,
            "check": command,
            "python": check.INTERPRETER,
        }
        for recipe in ("core", "execute-mysql")
    }
    report = {
        "format": check.FORMAT,
        "family": "mysql",
        "install": install,
        "core": {
            "returncode": 0,
            "result": {
                "before": [],
                "open": ["PIE-R2001", "EXECUTION_DEPENDENCY_MISSING", False],
                "after": [],
            },
        },
        "ambient": {
            name: {
                "returncode": 0,
                "result": {
                    "before": [],
                    "request": [
                        "PIE-R2003",
                        "EXECUTION_AMBIENT_CONNECTION_PROFILE",
                        False,
                    ],
                    "after": [],
                },
            }
            for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES")
        },
        "shadow": {
            "returncode": 0,
            "result": {
                "before": [],
                "open": ["PIE-R2002", "EXECUTION_DRIVER_VERSION", False],
                "after": ["mysql"],
            },
        },
    }
    assert check.check(report) == {"family": "mysql", "verdict": "ACCEPTED"}
    damaged = copy.deepcopy(report)
    damaged["shadow"]["result"]["open"][0] = "PIE-R2001"
    with pytest.raises(check.Rejected, match="MYSQL_SHADOW"):
        check.check(damaged)


def test_adbc_consumer_checker_accepts_its_literal_facts_and_refuses_damage():
    command = {"returncode": 0}
    install = {
        recipe: {
            "venv": command,
            "install": command,
            "check": command,
            "python": check.INTERPRETER,
        }
        for recipe in ("core", "execute-postgres-adbc")
    }
    report = {
        "format": check.FORMAT,
        "family": "postgres_adbc",
        "install": install,
        "core": {
            "returncode": 0,
            "result": {
                "before": [],
                "open": ["PIE-R2001", "EXECUTION_DEPENDENCY_MISSING", False],
                "after": [],
            },
        },
        "ambient": {
            name: {
                "returncode": 0,
                "result": {
                    "before": [],
                    "request": [
                        "PIE-R2003",
                        "EXECUTION_AMBIENT_CONNECTION_PROFILE",
                        False,
                    ],
                    "after": [],
                },
            }
            for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES")
        },
        "shadow": {
            "returncode": 0,
            "result": {
                "before": [],
                "open": ["PIE-R2002", "POSTGRES_ADBC_DRIVER_PROFILE", False],
                "after": ["adbc_driver_postgresql"],
            },
        },
    }
    assert check.check(report) == {"family": "postgres_adbc", "verdict": "ACCEPTED"}
    damaged = copy.deepcopy(report)
    damaged["ambient"]["OPENSSL_CONF"]["result"]["after"] = ["pyarrow"]
    with pytest.raises(check.Rejected, match="ADBC_AMBIENT_IMPORT"):
        check.check(damaged)


def test_importing_the_witness_modules_acquires_nothing(tmp_path):
    code = (
        "import sys; sys.path[:0] = [sys.argv[1], sys.argv[2]];"
        "import _pietto_execution_api_probe, _pietto_execution_api_check;"
        "import _pietto_execution_joint_acceptance;"
        "import _pietto_execution_joint_acceptance_check;"
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
        for record in (
            *checkout_facts["ambient"].values(),
            checkout_facts["shadow"],
            checkout_facts["psycopg_c"],
            checkout_facts["bundles"],
            checkout_facts["code_change"],
        )
    )
    # The code change touched a copy only: the checkout's code is unchanged.
    run = checkout_facts["code_change"]["run"]["result"]
    assert run["imported"] != str(ROOT / "src/pietto/__init__.py")
    assert checkout_facts["code_change"]["export"]["result"]["imported"] == str(
        ROOT / "src/pietto/__init__.py"
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
        (
            lambda f: f["imports"]["result"]["refusals"].update(route_unknown=None),
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
        (lambda f: f.pop("psycopg_c"), "PSYCOPG_C"),
        (
            lambda f: f["psycopg_c"]["result"].update(
                detail="EXECUTION_DRIVER_VERSION"
            ),
            "PSYCOPG_C",
        ),
        (
            lambda f: f["psycopg_c"]["result"].update(after_open=["psycopg"]),
            "PSYCOPG_C_LOADED",
        ),
        (lambda f: f["psycopg_c"].update(copy_imported=True), "PSYCOPG_C_IMPORTED"),
        (lambda f: f["psycopg_c"].update(copy_received=True), "PSYCOPG_C_IMPORTED"),
        (
            lambda f: f["identity"]["stray"]["result"].update(records=["0" * 64] * 3),
            "IDENTITY_BUNDLE",
        ),
        (
            lambda f: [
                f["identity"][where]["result"]["records"].__setitem__(2, "0" * 64)
                for where in ("clean", "stray")
            ],
            "IDENTITY_BUNDLE",
        ),
        (
            lambda f: f["identity"]["clean"]["result"].update(origin="live"),
            "IDENTITY_BUNDLE",
        ),
        (lambda f: f["identity"]["stray"]["result"].pop("records"), "IDENTITY_BUNDLE"),
        (
            lambda f: [
                f["identity"][where]["result"].pop("records")
                for where in ("clean", "stray")
            ],
            "IDENTITY_BUNDLE",
        ),
        (
            lambda f: [
                f["identity"][where]["result"].update(
                    records=[
                        "X" * 64,
                        "Y" * 64,
                        f["identity"][where]["result"]["identity"],
                    ]
                )
                for where in ("clean", "stray")
            ],
            "IDENTITY_BUNDLE",
        ),
        (lambda f: f["bundles"].update(returncode=1), "BUNDLES"),
        (
            lambda f: f["bundles"]["result"].update(after_import=["psycopg"]),
            "IMPORT_LOADED_DRIVER",
        ),
        (
            lambda f: f["bundles"]["result"]["records"].__setitem__(0, "X" * 64),
            "BUNDLE_RECORDS",
        ),
        (
            lambda f: f["bundles"]["result"].update(payload_sha256=None),
            "BUNDLE_RECORDS",
        ),
        (lambda f: f["bundles"]["result"]["records"].pop(), "BUNDLE_RECORDS"),
        (
            lambda f: f["bundles"]["result"].update(equal=[True, False, True]),
            "BUNDLE_RECORDS",
        ),
        (
            lambda f: f["bundles"]["result"]["loaded"].update(emission="{}"),
            "BUNDLE_LOADED",
        ),
        (
            lambda f: f["bundles"]["result"]["loaded"].update(origin="live"),
            "BUNDLE_LOADED",
        ),
        (
            lambda f: f["bundles"]["result"]["refusals"].update(
                tampered=["PIE-R1008", "COMPILED_JSON", False, False]
            ),
            "BUNDLE_REFUSALS",
        ),
        (
            lambda f: f["bundles"]["result"]["refusals"]["value_bool"].__setitem__(
                2, True
            ),
            "BUNDLE_REFUSALS",
        ),
        (
            lambda f: f["bundles"]["result"]["refusals"]["mixed_records"].__setitem__(
                3, True
            ),
            "BUNDLE_REFUSALS",
        ),
        (
            lambda f: f["bundles"]["result"]["refusals"].update(
                foreign_compatibility=None
            ),
            "BUNDLE_REFUSALS",
        ),
        (
            lambda f: f["bundles"]["result"]["refusals"].pop("pin_none"),
            "BUNDLE_REFUSALS",
        ),
        (
            lambda f: f["bundles"]["result"].update(attempts=["a", "a"]),
            "BUNDLE_EFFECTS",
        ),
        (
            lambda f: f["bundles"]["result"].update(ends=["NOT_STARTED", "OPEN"]),
            "BUNDLE_EFFECTS",
        ),
        (
            lambda f: f["bundles"]["result"].update(password_in_payload=True),
            "BUNDLE_EFFECTS",
        ),
        (
            lambda f: f["bundles"]["result"].update(after=["pyarrow"]),
            "BUNDLE_EFFECTS",
        ),
        (lambda f: f["bundles"].update(connected=True), "BUNDLE_EFFECTS"),
        (lambda f: f["code_change"]["export"].update(returncode=1), "CODE_CHANGE"),
        (lambda f: f["code_change"]["run"].update(result=None), "CODE_CHANGE"),
        (
            lambda f: f["code_change"]["export"]["result"]["records"].update(
                expected_pin="x"
            ),
            "CODE_CHANGE",
        ),
        (
            lambda f: f["code_change"]["run"]["result"].update(
                imported=f["code_change"]["export"]["result"]["imported"]
            ),
            "CODE_CHANGE_COPY",
        ),
        (
            lambda f: f["code_change"]["export"]["result"].update(
                imported=f["code_change"]["copy"]
            ),
            "CODE_CHANGE_COPY",
        ),
        (
            lambda f: f["code_change"]["run"]["result"].update(
                compatibility_changed=False
            ),
            "CODE_CHANGE",
        ),
        (
            lambda f: f["code_change"]["run"]["result"].update(own_load="live"),
            "CODE_CHANGE",
        ),
        (
            lambda f: f["code_change"]["run"]["result"]["refusals"].update(
                relabeled=["PIE-R1005", "PUBLIC_BUNDLE_CODE_IDENTITY", False, False]
            ),
            "CODE_CHANGE",
        ),
        (
            lambda f: f["code_change"]["run"]["result"]["refusals"].update(
                execute_loaded=None
            ),
            "CODE_CHANGE",
        ),
        (lambda f: f["code_change"].update(connected=True), "CODE_CHANGE"),
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


def _core(origin):
    return {
        "returncode": 0,
        "connected": False,
        "result": {
            "after_import": [],
            "origin": origin,
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
    }


def _core_schema():
    value = _core("live")
    value["result"]["schema"] = {
        "code": "PIE-R4004",
        "detail": "EXECUTION_DEPENDENCY_MISSING",
        "shown": False,
        "chained": False,
    }
    return value


def _core_cancel():
    value = _core("live")
    value["result"].update(
        cancel_return=True,
        code="PIE-R3009",
        detail=None,
        outcome={
            "end": "CANCELLED",
            "transaction": "NOT_STARTED",
            "cancel": [True, False, False],
        },
    )
    return value


def consumer_report(cases):
    """A report with the facts a passing consumer family records around the
    checkout's consumer cases."""
    return {
        "format": check.FORMAT,
        "family": "consumer",
        "install": _install("core", "execute-postgres"),
        "core": _core("live"),
        "core_schema": _core_schema(),
        "core_cancel": _core_cancel(),
        "core_bundle": _core("bundle"),
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
            lambda r: r["core_schema"]["result"]["schema"].update(code="PIE-R4003"),
            "CORE_SCHEMA",
        ),
        (lambda r: r["core_schema"].update(connected=True), "CORE_SCHEMA"),
        (
            lambda r: r["core_cancel"]["result"]["outcome"].update(
                cancel=[True, True, False]
            ),
            "CORE_CANCEL",
        ),
        (
            lambda r: r["core"]["result"]["outcome"].update(end="OPEN"),
            "CORE_FALLBACK",
        ),
        (
            lambda r: r["core_bundle"]["result"].update(origin="live"),
            "CORE_BUNDLE_FALLBACK",
        ),
        (
            lambda r: r["core_bundle"]["result"].update(code="PIE-R2002"),
            "CORE_BUNDLE_FALLBACK",
        ),
        (lambda r: r["core_bundle"].update(connected=True), "CORE_BUNDLE_FALLBACK"),
        (lambda r: r.pop("core_bundle"), "CORE_BUNDLE_FALLBACK"),
        (
            lambda r: r["core_bundle"]["result"].update(after_open=["psycopg"]),
            "CORE_LOADED_DRIVER",
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


def _outcome(
    end,
    transaction,
    cleanup="CLOSED",
    rows=0,
    primary=None,
    cancel=(False, False, False),
    cleanup_failures=(),
):
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
        "cleanup_failures": [list(value) for value in cleanup_failures],
        "cancel": list(cancel),
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


def _step(name, attempt, *, rows=None, code=None, sqlstate=None, end="COMPLETE"):
    """One completed or failed step of the loaded bundle."""
    transaction = {
        "COMPLETE": "COMMIT_ACK",
        "PIE-R2004": "NOT_STARTED",
        "PIE-R3003": "UNKNOWN",
    }[code or end]
    primary = None if code is None else [code, None, "check", sqlstate]
    record: dict = {
        "step": name,
        "attempt": attempt,
        "outcome": {"end": end, "transaction": transaction, "primary": primary},
    }
    if rows is not None:
        record["rows"] = rows
    if code is not None:
        record.update(
            code=code, detail=None, sqlstate=sqlstate, shown=False, chained=False
        )
    return record


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
                "schema": list(check.DEMO_SCHEMA),
                "schema_preopen": {
                    "closed": False,
                    "end": "NOT_STARTED",
                    "loaded": ["pyarrow"],
                },
                "rows": sorted(check.ROWS),
                "outcome": _outcome("COMPLETE", "COMMIT_ACK", rows=4),
                **_effects(),
            }
        ),
        "schema_empty": _ok(
            {
                "schema": list(check.DEMO_SCHEMA),
                "schema_preopen": {
                    "closed": False,
                    "end": "NOT_STARTED",
                    "loaded": ["pyarrow"],
                },
                "rows": [],
                "outcome": _outcome("COMPLETE", "COMMIT_ACK", rows=0),
            }
        ),
        "early_stop": _ok(
            {
                "first_rows": 1,
                "outcome": _outcome("STOPPED_EARLY", "ROLLBACK_ACK", rows=1),
                **_effects(),
            }
        ),
        "interrupt": _ok(
            {
                "reraised": True,
                "outcome": _outcome(
                    "FAILED",
                    "ROLLBACK_ACK",
                    primary=["PIE-R3008", None, "consumer", None],
                ),
            }
        ),
        "native_unlimited": _ok(
            {
                "delivered_rows": 1,
                "first_row": [{"id": 2, "label": "two"}],
                "native_buffered_rows": 4,
                "second": "REFUSED",
                "failure": {"code": "PIE-R3004"},
                "outcome": _outcome("FAILED", "ROLLBACK_ACK", rows=1),
            }
        ),
        "native_limited": _ok(
            {
                "delivered_rows": 1,
                "first_row": [{"id": 2, "label": "two"}],
                "native_buffered_rows": 1,
                "second": "EOF",
                "outcome": _outcome("COMPLETE", "COMMIT_ACK", rows=1),
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
        "manual_cancel": _ok(
            {
                "cancel_return": True,
                "code": "PIE-R3009",
                "detail": None,
                "shown": False,
                "chained": False,
                "outcome": _outcome(
                    "CANCELLED",
                    "UNKNOWN",
                    cleanup="FAILED",
                    rows=0,
                    primary=["PIE-R3009", None, None, None, None],
                    cancel=(True, True, True),
                    cleanup_failures=(("PIE-R5001", "transaction", "ExecutionError"),),
                ),
            }
        )
        | {"blocked": [["active", "Lock"]]},
        "dropped": {
            "returncode": 0,
            "result": {"warnings": [["PIE-R5002", "DROPPED", True]], "dropped_at": 1.0},
            "during": 1,
            "tls": [[True, "TLSv1.3"]],
            "exit_delay": 3.4,
            "after": 0,
        },
        "bundle_export": _ok(
            {
                "records": {
                    "expected_pin": "a" * 64,
                    "accepted_producer": "b" * 64,
                    "accepted_compatibility": "c" * 64,
                }
            }
        ),
        "bundle_steps": {
            "returncode": 0,
            "records": [
                {"loaded": dict(check.BUNDLE_LOADED), "source_present": False},
                _step("first", "a1", rows=sorted(check.ROWS)),
                _step("other_role", "a2", code="PIE-R2004", end="FAILED"),
                _step(
                    "revoked", "a3", code="PIE-R3003", sqlstate="42501", end="FAILED"
                ),
                _step("granted", "a4", rows=[[5, "five"]]),
                {
                    "step": "refused_value",
                    "attempt": None,
                    "code": "PIE-R1006",
                    "detail": "BINDING_VALUE:0:Int",
                    "sqlstate": None,
                    "shown": False,
                    "chained": False,
                },
                _step("again", "a5", rows=sorted(check.ROWS)),
                {
                    "threads": ["MainThread"],
                    "jobs": [],
                    "files": {"cwd": [], "home": [], "tmp": []},
                },
            ],
            "stderr": "",
        },
        "bundle_example": {
            "returncode": 0,
            "stdout": "\n".join(check.BUNDLE_EXAMPLE) + "\n",
            "shown": False,
        },
        "consume_example": {
            "returncode": 0,
            "stdout": "\n".join(check.CONSUME_EXAMPLE) + "\n",
            "shown": False,
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
        (
            lambda r: r["bind_safe"]["result"]["schema"].__setitem__(
                0, ["id", "int32", False]
            ),
            "RESULT_SCHEMA",
        ),
        (
            lambda r: r["bind_safe"]["result"]["schema_preopen"].update(end="OPEN"),
            "RESULT_SCHEMA_PREOPEN",
        ),
        (
            lambda r: r["schema_empty"]["result"].update(rows=[[2, "two"]]),
            "EMPTY_RESULT",
        ),
        (
            lambda r: r["native_unlimited"]["result"].update(native_buffered_rows=1),
            "NATIVE_BUFFERING",
        ),
        (
            lambda r: r["native_unlimited"]["result"]["outcome"].update(rows=0),
            "QUERY_LIMIT",
        ),
        (
            lambda r: r["native_limited"]["result"]["outcome"].update(
                transaction="ROLLBACK_ACK"
            ),
            "QUERY_LIMIT",
        ),
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
        (
            lambda r: r["interrupt"]["result"]["outcome"].update(
                primary=["PIE-R3007", None, "consumer", None]
            ),
            "INTERRUPT",
        ),
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
        (
            lambda r: r["statement_timeout"]["result"]["outcome"].update(
                cancel=[False, True, False]
            ),
            "STATEMENT_TIMEOUT",
        ),
        (
            lambda r: r["manual_cancel"]["result"]["outcome"].update(
                transaction="ROLLBACK_ACK", remote="TRANSACTION_ACK", cleanup="CLOSED"
            ),
            "MANUAL_CANCEL",
        ),
        (lambda r: r["dropped"].update(returncode=1), "DROPPED"),
        (lambda r: r["dropped"]["result"].update(warnings=[]), "DROPPED_WARNING"),
        (lambda r: r["dropped"].update(during=0), "DROPPED_SESSION"),
        (lambda r: r["dropped"].update(tls=[[False, None]]), "ACTUAL_TLS"),
        (lambda r: r["dropped"].update(tls=[]), "ACTUAL_TLS"),
        (lambda r: r["dropped"].update(exit_delay=0.1), "DROPPED_EXIT_DELAY"),
        (lambda r: r["dropped"].update(after=1), "DROPPED_SESSION_LEFT"),
        (lambda r: r["cleanup"].update(status="failed"), "RESOURCE_CLEANUP"),
        (
            lambda r: r["example"].update(
                stdout=r["example"]["stdout"].replace(", origin='live'", "")
            ),
            "EXAMPLE_COMPILE",
        ),
        (lambda r: r["bundle_export"].update(returncode=1), "BUNDLE_EXPORT"),
        (
            lambda r: r["bundle_export"]["result"]["records"].update(
                expected_pin="A" * 64
            ),
            "BUNDLE_EXPORT",
        ),
        (
            lambda r: r["bundle_export"]["result"]["records"].pop("accepted_producer"),
            "BUNDLE_EXPORT",
        ),
        (lambda r: r["bundle_steps"].update(returncode=1), "BUNDLE_STEPS"),
        (lambda r: r["bundle_steps"]["records"].pop(3), "BUNDLE_STEPS"),
        (
            lambda r: r["bundle_steps"]["records"][1].update(step="again"),
            "BUNDLE_STEPS",
        ),
        (
            lambda r: r["bundle_steps"]["records"][0].update(source_present=True),
            "BUNDLE_STEPS_LOADED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][0]["loaded"].update(origin="live"),
            "BUNDLE_STEPS_LOADED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][1].update(
                rows=sorted(check.ROWS)[:3]
            ),
            "BUNDLE_STEPS_FIRST",
        ),
        (
            lambda r: r["bundle_steps"]["records"][1]["outcome"].update(
                transaction="ROLLBACK_ACK"
            ),
            "BUNDLE_STEPS_FIRST",
        ),
        (
            lambda r: r["bundle_steps"]["records"][2].update(code="PIE-R2007"),
            "BUNDLE_STEPS_OTHER_ROLE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][2]["outcome"].update(
                transaction="ROLLBACK_ACK"
            ),
            "BUNDLE_STEPS_OTHER_ROLE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][3].update(sqlstate="42P01"),
            "BUNDLE_STEPS_REVOKED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][3].update(code="PIE-R2007"),
            "BUNDLE_STEPS_REVOKED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][3]["outcome"].update(end="COMPLETE"),
            "BUNDLE_STEPS_REVOKED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][4]["outcome"].update(end="FAILED"),
            "BUNDLE_STEPS_GRANTED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][4].update(rows=sorted(check.ROWS)),
            "BUNDLE_STEPS_GRANTED",
        ),
        (
            lambda r: r["bundle_steps"]["records"][5].update(attempt="a6"),
            "BUNDLE_STEPS_REFUSED_VALUE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][5].update(detail="BINDING_SLOTS"),
            "BUNDLE_STEPS_REFUSED_VALUE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][5].update(
                outcome=r["bundle_steps"]["records"][1]["outcome"]
            ),
            "BUNDLE_STEPS_REFUSED_VALUE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][6].update(code="PIE-R3003"),
            "BUNDLE_STEPS_AGAIN",
        ),
        (
            lambda r: r["bundle_steps"]["records"][3].update(shown=True),
            "CREDENTIAL",
        ),
        (
            lambda r: r["bundle_steps"]["records"][5].update(chained=True),
            "CREDENTIAL",
        ),
        (
            lambda r: r["bundle_steps"]["records"][6].update(attempt="a1"),
            "BUNDLE_STEPS_ATTEMPTS",
        ),
        (
            lambda r: r["bundle_steps"]["records"][7].update(
                threads=["MainThread", "pietto-deadline-x"]
            ),
            "BUNDLE_STEPS_THREADS",
        ),
        (
            lambda r: r["bundle_steps"]["records"][7].update(
                jobs=["pietto._project.project_job_store"]
            ),
            "BUNDLE_STEPS_WORKSPACE",
        ),
        (
            lambda r: r["bundle_steps"]["records"][7]["files"]["cwd"].append(
                "active_items.bundle"
            ),
            "BUNDLE_STEPS_FILES",
        ),
        (
            lambda r: r["bundle_steps"]["records"][7]["files"]["home"].append(
                ".pietto"
            ),
            "BUNDLE_STEPS_FILES",
        ),
        (lambda r: r["bundle_example"].update(returncode=1), "BUNDLE_EXAMPLE"),
        (
            lambda r: r["bundle_example"].update(
                stdout=r["bundle_example"]["stdout"].replace("3 [5]", "3 [5, 5]")
            ),
            "BUNDLE_EXAMPLE",
        ),
        (
            lambda r: r["bundle_example"].update(
                stdout=r["bundle_example"]["stdout"].replace("bundle", "live")
            ),
            "BUNDLE_EXAMPLE",
        ),
        (lambda r: r["bundle_example"].update(shown=True), "CREDENTIAL"),
        (lambda r: r["consume_example"].update(returncode=1), "CONSUME_EXAMPLE"),
    ),
)
def test_the_checker_refuses_each_damaged_postgres_fact(damage, reason):
    report = postgres_report()
    damage(report)
    with pytest.raises(check.Rejected, match="^" + reason + "$"):
        check.check(report)


def postgres_adbc_native_report():
    """Literal raw facts for the installed, TCP SCRAM ADBC witness."""
    rows = [[2, "two"], [2, "two"], [3, "three"], [5, "five"]]

    def adbc_outcome(*args, **kwargs):
        value = _outcome(*args, **kwargs)
        value["cleanup"] = "LOCAL_CLOSED_REMOTE_UNOBSERVED"
        return value

    def completed(origin, values, count):
        outcome = adbc_outcome("COMPLETE", "COMMIT_ACK", rows=count)
        outcome["batches"] = 0 if count == 0 else 1
        return {
            "origin": origin,
            "route": "postgres_adbc",
            "sslmode": "require",
            "schema": list(check.DEMO_SCHEMA),
            "rows": copy.deepcopy(values),
            "outcome": outcome,
        }

    early = adbc_outcome("STOPPED_EARLY", "ROLLBACK_ACK", rows=1)
    early.update(source="EARLY_CLOSE", delivery="INCOMPLETE")
    cancelled = adbc_outcome(
        "CANCELLED",
        "NOT_STARTED",
        primary=["PIE-R3009", None, None, None, None],
        cancel=(True, False, False),
    )
    cancelled.update(source="FAILED", delivery="FAILED", batches=0)

    def refused_adbc_outcome():
        value = adbc_outcome(
            "FAILED",
            "NOT_STARTED",
            primary=["PIE-R2004", None, "admission", None, "OperationalError"],
        )
        value.update(source="FAILED", delivery="FAILED", batches=0)
        return value

    def active_adbc(terminal, code, *, manual=True):
        value = adbc_outcome(
            terminal,
            "UNKNOWN",
            primary=[
                code,
                None,
                "query",
                None if manual else "57014",
                "OperationalError",
            ],
            cancel=(True, True, True) if manual else (False, False, False),
        )
        value.update(
            source="FAILED",
            delivery="FAILED",
            batches=0,
            cleanup="FAILED_REMOTE_UNOBSERVED",
        )
        return {
            "returncode": 0,
            "blocked": [["active", "Lock"]],
            "attempt": "active-attempt-" + terminal,
            "purpose": "query",
            "result": {
                "active": {
                    "type": "NativeStatement",
                    "purpose": "query",
                    "native": True,
                },
                "closed": True,
                "raised": "AttemptFailed",
                **({"cancel_return": True} if manual else {}),
                "outcome": value,
                "late_cancel_return": True,
                "outcome_after_late": copy.deepcopy(value),
            },
        }

    authentication = {}
    for method in ("trust", "password", "md5", "gss", "sspi"):
        authentication[method] = _ok(
            {
                "after_import": [],
                "unopened": [[], "NOT_STARTED", False],
                "code": "PIE-R2004",
                "detail": None,
                "shown": False,
                "chained": False,
                "after_open": [
                    "adbc_driver_manager",
                    "adbc_driver_postgresql",
                    "pyarrow",
                ],
                "outcome": refused_adbc_outcome(),
            }
        )
        authentication[method]["stub"] = {
            "events": [["startup", "pietto_reader", "phase66"], ["closed", "EOFError"]],
            "replied": False,
            "startup": ["pietto_reader", "phase66"],
        }
    ambient = {
        name: _ok(
            {
                "after_import": [],
                "code": "PIE-R2003",
                "detail": "EXECUTION_AMBIENT_CONNECTION_PROFILE",
                "shown": False,
                "chained": False,
                "after_open": [],
            }
        )
        for name in ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES")
    }
    for record in ambient.values():
        record.update(connected=False, keylog_created=False)
    return {
        "format": check.FORMAT,
        "family": "postgres_adbc_native",
        "install": _install("execute-postgres-adbc"),
        "server": copy.deepcopy(postgres_report()["server"]),
        "native": _ok(
            {
                "after_import": [],
                "live": completed("live", rows, 4),
                "bundle": completed("bundle", rows, 4),
                "empty": completed("live", [], 0),
                "bounded": completed("live", [[2, "two"]], 1),
                "early_rows": [{"id": 2, "label": "two"}],
                "early": early,
                "cancelled": {
                    "cancel_return": True,
                    "closed": True,
                    "code": "PIE-R3009",
                    "detail": None,
                    "shown": False,
                    "chained": False,
                    "outcome": cancelled,
                },
                "qualification": ["postgres_adbc"] * 5,
                "driver": {
                    "prefix": "/prefix",
                    "postgresql_version": "1.13.0",
                    "manager_version": "1.13.0",
                    "module": "/prefix/lib/python3.13/site-packages/adbc_driver_postgresql/__init__.py",
                    "manager_module": "/prefix/lib/python3.13/site-packages/adbc_driver_manager/__init__.py",
                    "library": "/prefix/lib/python3.13/site-packages/adbc_driver_postgresql/libadbc_driver_postgresql.so",
                    "library_record": True,
                    "module_record": True,
                    "module_in_prefix": True,
                    "library_in_prefix": True,
                    "library_exists": True,
                },
            }
        ),
        "authentication": authentication,
        "ambient": ambient,
        "active_cancel": active_adbc("CANCELLED", "PIE-R3009"),
        "active_server_timeout": active_adbc("FAILED", "PIE-R3002", manual=False),
        "cleanup": {"status": "success"},
    }


def test_the_checker_accepts_the_postgres_adbc_native_raw_facts():
    assert check.check(postgres_adbc_native_report()) == {
        "family": "postgres_adbc_native",
        "verdict": "ACCEPTED",
    }


def test_finish_checks_the_exclusive_json_report_with_ordered_stub_events(tmp_path):
    report = postgres_adbc_native_report()
    events = (
        ("startup", "pietto_reader", "phase66"),
        ("closed", "EOFError"),
        ("closed", "EOFError"),
    )
    for record in report["authentication"].values():
        record["stub"]["events"] = events

    verdict = probe.finish(tmp_path, report)
    written = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert written["authentication"]["trust"]["stub"]["events"] == [
        list(event) for event in events
    ]
    assert (
        verdict
        == check.check(written)
        == {
            "family": "postgres_adbc_native",
            "verdict": "ACCEPTED",
        }
    )


@pytest.mark.parametrize(
    "damage,reason",
    (
        (lambda r: r["install"].pop("execute-postgres-adbc"), "INSTALL"),
        (lambda r: r["server"]["hba"][4].__setitem__(2, "md5"), "HBA_METHODS"),
        (
            lambda r: r["native"]["result"]["live"].update(origin="bundle"),
            "ADBC_NATIVE_LIVE",
        ),
        (
            lambda r: r["native"]["result"]["live"]["outcome"].update(cleanup="CLOSED"),
            "ADBC_NATIVE_LIVE",
        ),
        (
            lambda r: r["native"]["result"]["bundle"]["rows"].reverse(),
            "ADBC_NATIVE_BUNDLE",
        ),
        (
            lambda r: r["native"]["result"]["early"].update(
                remote="REMOTE_QUIESCENCE_UNCONFIRMED"
            ),
            "ADBC_EARLY_CLOSE",
        ),
        (
            lambda r: r["native"]["result"].update(qualification=[]),
            "ADBC_QUALIFICATION",
        ),
        (
            lambda r: r["native"]["result"]["cancelled"]["outcome"].update(
                transaction="COMMIT_ACK"
            ),
            "ADBC_CANCEL",
        ),
        (
            lambda r: r["active_cancel"]["result"].update(active={"purpose": "query"}),
            "ADBC_ACTIVE_CANCEL_STATEMENT",
        ),
        (
            lambda r: r["active_server_timeout"].update(blocked=[]),
            "ADBC_ACTIVE_SERVER_TIMEOUT_BARRIER",
        ),
        (
            lambda r: r["active_server_timeout"]["result"].update(cancel_return=False),
            "ADBC_ACTIVE_SERVER_TIMEOUT",
        ),
        (
            lambda r: r["active_cancel"]["result"]["outcome"].update(end="DEADLINE"),
            "ADBC_ACTIVE_CANCEL",
        ),
        (
            lambda r: r["active_server_timeout"]["result"]["outcome"].update(
                transaction="COMMIT_ACK"
            ),
            "ADBC_ACTIVE_SERVER_TIMEOUT",
        ),
        (
            lambda r: r["active_cancel"]["result"]["outcome"].update(
                cancel=[True, False, True]
            ),
            "ADBC_ACTIVE_CANCEL",
        ),
        (
            lambda r: r["active_server_timeout"]["result"].update(
                outcome_after_late={}
            ),
            "ADBC_ACTIVE_SERVER_TIMEOUT",
        ),
        (
            lambda r: r["native"]["result"]["driver"].update(library_record=False),
            "ADBC_DRIVER_RECORD",
        ),
        (
            lambda r: r["authentication"]["password"]["stub"].update(replied=True),
            "ADBC_AUTH_password",
        ),
        (
            lambda r: r["authentication"]["gss"]["result"]["outcome"].update(
                cleanup="CLOSED"
            ),
            "ADBC_AUTH_gss",
        ),
        (
            lambda r: r["authentication"]["md5"]["result"].update(shown=True),
            "ADBC_AUTH_md5",
        ),
        (
            lambda r: r["ambient"]["SSLKEYLOGFILE"].update(keylog_created=True),
            "ADBC_NATIVE_AMBIENT_SSLKEYLOGFILE",
        ),
        (
            lambda r: r["ambient"]["OPENSSL_CONF"]["result"].update(
                after_open=["pyarrow"]
            ),
            "ADBC_NATIVE_AMBIENT_OPENSSL_CONF",
        ),
        (lambda r: r["cleanup"].update(status="failed"), "RESOURCE_CLEANUP"),
    ),
)
def test_the_checker_refuses_each_damaged_postgres_adbc_native_fact(damage, reason):
    report = postgres_adbc_native_report()
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
    # The bundle steps revoke and grant again exactly the documented grant,
    # with roles of the fixture.
    assert probe.PRIVILEGE["granted"] in api.statements(api.setup_blocks()["sql"])
    assert probe.PRIVILEGE["revoked"] == probe.PRIVILEGE["granted"].replace(
        "GRANT", "REVOKE"
    ).replace(" TO ", " FROM ")
    assert [s["name"] for s in probe.BUNDLE_STEPS] == list(check.STEPS)
    assert {s["user"] for s in probe.BUNDLE_STEPS} <= set(probe.ROLES)


def test_the_bundle_oracles_are_the_documented_output():
    """The documented bundle script's printed lines are the checker's oracle,
    computed from the fixture's rows for the values 1 and 3."""
    docs = (ROOT / "docs/execution.md").read_text(encoding="utf-8")
    section = docs.split("\n## Query bundles\n", 1)[1].split("\n## ", 1)[0]
    printed = " ".join(section.split("It prints", 1)[1].split("\n\n", 1)[0].split())
    assert printed == (
        "`"
        + check.BUNDLE_EXAMPLE[0]
        + "`, then `"
        + check.BUNDLE_EXAMPLE[1]
        + "` and `"
        + check.BUNDLE_EXAMPLE[2]
        + "`."
    )
    for line, value in zip(check.BUNDLE_EXAMPLE[1:], (1, 3), strict=True):
        ids = sorted(i for i, _label in probe.ROWS if i > value)
        assert line == f"{value} {ids} COMPLETE"
    assert [[i, label] for i, label in probe.ROWS if i > 3] == [[5, "five"]]


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


# The Phase70 joint acceptance (S17): the database-free facts of every shape on
# every route from the checkout, the runner's native steps through a stand-in
# owner, and the independent checker's laws.


class _JointBatch:
    """A stand-in result batch; the stand-in `pyarrow.record_batch` returns it."""

    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def to_pylist(self):
        return [dict(enumerate(row)) for row in self.rows]


class _JointResults(_JointBatch):
    """A stand-in result handle or verified export of one batch."""

    outcome = SimpleNamespace(end="COMPLETE", transaction="COMMIT_ACK", primary=None)

    def __iter__(self):
        return iter((_JointBatch(self.rows),))


class _JointFailed(_JointResults):
    """A stand-in result handle whose first read is the server's error."""

    def __init__(self, error):
        self.error = error

    def __iter__(self):
        raise self.error


class _JointReader:
    def __init__(self, rows, end):
        self.items = [SimpleNamespace(batch=_JointBatch(rows)), end]

    def next(self, rows, *, operation):
        return self.items.pop(0)

    def ack(self, item, *, operation):
        return None

    def close(self):
        return None


def _joint_stand_in():
    """The public module, with each call the runner's native steps make bound
    to its real signature (kept visible for `parameters=`) and answered from
    the checker's oracle of the shape in `module.shape` by a stand-in owner of
    one generation per workspace."""
    import pietto.execution as real
    from pietto.execution._errors import failure

    module = SimpleNamespace(**{name: getattr(real, name) for name in real.__all__})

    def answers(name):
        signature = inspect.signature(getattr(real, name))

        def decorate(body):
            def call(*args, **keywords):
                return body(**signature.bind(*args, **keywords).arguments)

            call.__signature__ = signature  # type: ignore[attr-defined]
            setattr(module, name, call)
            return body

        return decorate

    def oracle():
        return joint_check.ORACLES[module.shape.name]

    def rows(parameters):
        return oracle()["rows"][module.shape.bindings.index(parameters)]

    def failed(route):
        """The server's error and the attempt it ends on `route`, as
        documented."""
        code, state = oracle()["failure"]
        end, transaction, cleanup, failures = {
            "postgres_rows": ("FAILED", "UNKNOWN", "FAILED", ("PIE-R5001",)),
            "postgres_adbc": (
                "FAILED",
                "UNKNOWN",
                "LOCAL_CLOSED_REMOTE_UNOBSERVED",
                (),
            ),
            "mysql_rows": ("FAILED", "ROLLBACK_ACK", "CLOSED", ()),
        }[route]
        outcome = SimpleNamespace(
            end=end,
            transaction=transaction,
            cleanup=cleanup,
            cleanup_failures=tuple(
                failure(item, phase="transaction") for item in failures
            ),
        )
        return real.AttemptFailed(failure(code, sqlstate=state), outcome=outcome)  # type: ignore[arg-type]

    def saved(workspace, values, parameters):
        """The saved binding, typed, as a restatement must repeat it."""
        workspace.binding = typed(values, parameters)

    def typed(values, parameters):
        named = sorted((parameters or {}).items())
        return [(type(v), v) for v in values], [(k, type(v), v) for k, v in named]

    def restating(workspace, values, parameters):
        if typed(values, parameters) != workspace.binding:
            raise real.RequestRejected(failure("PIE-R1009", "BINDING_VECTOR"))

    def generation(workspace, rows, closings, frontier=None):
        workspace.rows = rows
        workspace.current = SimpleNamespace(
            identity="gen-1",
            checkpoint="ckp-1",
            frontier=len(rows) if frontier is None else frontier,
            holes=(),
            observed_end=len(rows) if frontier is None else None,
            closings=tuple("close-" + str(i) for i in range(closings)),
        )

    def reply(terminal):
        return SimpleNamespace(
            job="job-1",
            generation="gen-1",
            terminal=terminal,
            settlement="RELEASED",
            cleanup=None,
        )

    @answers("execute")
    def _execute(query, route, parameters=None, **rest):
        if "failure" in oracle():
            return _JointFailed(failed(route))
        return _JointResults(rows(parameters))

    @answers("create_workspace")
    def _create(root, budget_bytes):
        return SimpleNamespace(root=str(root), released=set())

    @answers("inspect_job")
    def _inspect(workspace, job):
        return SimpleNamespace(generations=(workspace.current,))

    @answers("save")
    def _save(workspace, query, values, parameters=None, **rest):
        if "failure" in oracle():
            return reply("FAILED")
        saved(workspace, values, parameters)
        generation(workspace, rows(parameters), 1)
        return reply("COMPLETED")

    @answers("open_saved_read")
    def _open(workspace, consumer, values, parameters=None, **rest):
        restating(workspace, values, parameters)
        if consumer in workspace.released:
            raise real.RequestRejected(failure("PIE-R1009", "CONSUMER_RELEASED"))
        n = len(workspace.rows)
        end = real.SavedReadEnd("SAVED_SCOPE_EXHAUSTED", "gen-1", "ckp-1", n, n)
        return _JointReader(workspace.rows, end)

    @answers("verified_export")
    def _export(workspace, **rest):
        return _JointResults(workspace.rows)

    @answers("publish_saved_generation")
    def _publish(workspace, **rest):
        return SimpleNamespace(terminal="PUBLISHED", extent=len(workspace.rows))

    @answers("release_saved_read")
    def _release(workspace, consumer, **rest):
        workspace.released.add(consumer)
        return SimpleNamespace(kind="release_retention")

    @answers("save_recoverable")
    def _prefix(workspace, query, values, parameters=None, **rest):
        saved(workspace, values, parameters)
        generation(workspace, rows(parameters), 1, frontier=8)
        return reply("FAILED")

    @answers("recover")
    def _recover(workspace, values, parameters=None, **rest):
        restating(workspace, values, parameters)
        generation(workspace, workspace.rows, 2)
        return reply("COMPLETED")

    @answers("create_reference_sink")
    def _sink(root, namespace, epoch, retention_seconds, **rest):
        return SimpleNamespace(
            root=str(root),
            identity="sink-1",
            namespace=namespace,
            epoch=epoch,
            retention="r",
            budget_bytes=1,
            busy_seconds=5.0,
        )

    @answers("relay_live")
    def _relay(workspace, query, parameters=None, **rest):
        if "failure" in oracle():
            return reply("FAILED")
        generation(workspace, rows(parameters), 1)
        return reply("COMPLETED")

    return module


@pytest.fixture(scope="module")
def joint_shape(tmp_path_factory):
    """`joint_shape(name)`: a copy of one shape's database-free facts on every
    route from the checkout, with the runner's native steps through the
    stand-in owner. Each shape compiles once per target and module, when a
    test first needs it."""
    stand_in = _joint_stand_in()
    work = tmp_path_factory.mktemp("joint")
    arrow = ModuleType("pyarrow")
    setattr(arrow, "record_batch", lambda batch: batch)
    found: dict[str, Any] = {}

    def native(case, probes):
        stand_in.shape = case.shape
        access, schemas = joint.probe_inputs(case.target, work / "ca.pem")
        inputs = {"access": access, "schemas": schemas, "providers": ()}
        with pytest.MonkeyPatch.context() as patch:
            patch.setitem(sys.modules, "pyarrow", arrow)
            return joint._native(replace(case, execution=stand_in), probes, inputs)

    def facts(name):
        if name not in found:
            table = tuple(shape for shape in joint.SHAPES if shape.name == name)
            report = joint.offline_report(work / name, native, table)
            found[name] = report["shapes"][name]
        return copy.deepcopy(found[name])

    return facts


def _offline(record):
    """One shape's facts without the native steps, as `offline_report`."""
    for facts in record["routes"].values():
        del facts["native"]
    return record


@pytest.mark.parametrize("name", list(joint_check.ORACLES))
def test_offline_joint_facts_match_the_literal_oracles(joint_shape, name):
    """Compile, bundle, the pre-connect probe of every operation and the
    parameter negatives match the checker's literal oracle on every route; no
    probe connected or reached a workspace it was refused before."""
    joint_check.check_shape(
        name, _offline(joint_shape(name)), "offline", list(joint_check.ROUTES)
    )


def _sql(dialect, change):
    def damage(record):
        fact = record["dialects"][dialect]["compile"]
        fact["sql"] = change(fact["sql"])

    return damage


def _probe_fact(route, operation, **changes):
    return lambda record: record["routes"][route]["probe"][operation].update(changes)


OFFLINE_DAMAGES = {
    "COMPILE_let_chain_postgres": (
        "let_chain",
        lambda r: r["dialects"]["postgres"]["compile"].update(slots=[]),
    ),
    "SQL_let_chain_postgres": ("let_chain", _sql("postgres", lambda s: s + " $2")),
    "SQL_param_where_mysql": ("param_where", _sql("mysql", lambda s: s + " ?")),
    "BUNDLE_let_chain_mysql": (
        "let_chain",
        lambda r: r["dialects"]["mysql"]["bundle"]["reexported"].__setitem__(1, False),
    ),
    # A loaded parameterized query keeps its declared parameters.
    "BUNDLE_param_where_postgres": (
        "param_where",
        lambda r: r["dialects"]["postgres"]["bundle"]["query"].__setitem__(7, []),
    ),
    "PROBE_let_chain_postgres_rows_execute": (
        "let_chain",
        _probe_fact("postgres_rows", "execute", connected=True),
    ),
    "PROBE_let_chain_mysql_rows_save": (
        "let_chain",
        _probe_fact("mysql_rows", "save", workspace=True),
    ),
    "PROBE_let_chain_postgres_adbc_recover": (
        "let_chain",
        _probe_fact("postgres_adbc", "recover", detail="WORKSPACE_IDENTITY"),
    ),
    "PROBE_let_chain_postgres_rows_relay_live": (
        "let_chain",
        _probe_fact("postgres_rows", "relay_live", code="PIE-R1009"),
    ),
    # Every route runs a query that declares parameters.
    "PROBE_param_where_postgres_adbc_execute": (
        "param_where",
        _probe_fact(
            "postgres_adbc",
            "execute",
            outcome="refused",
            code="PIE-R1003",
            detail="PUBLIC_PARAMETERS_ROUTE",
        ),
    ),
    "PROBE_param_where_mysql_rows_save_recoverable": (
        "param_where",
        _probe_fact("mysql_rows", "save_recoverable", connected=True),
    ),
    "NEGATIVE_param_where_postgres_rows_obligation": (
        "param_where",
        lambda r: r["routes"]["postgres_rows"]["negatives"]["obligation"].update(
            code="PIE-R1006"
        ),
    ),
    "NEGATIVE_param_where_mysql_rows": (
        "param_where",
        lambda r: r["routes"]["mysql_rows"]["negatives"].pop("missing"),
    ),
    "NATIVE_let_chain_postgres_rows": (
        "let_chain",
        lambda r: r["routes"]["postgres_rows"].update(native={}),
    ),
    "DIALECTS_let_chain": ("let_chain", lambda r: r["dialects"].pop("mysql")),
    "ROUTES_let_chain": ("let_chain", lambda r: r["routes"].pop("postgres_adbc")),
    # An R2 refusal must be its shape's own word, before any workspace.
    "PROBE_computed_key_join_postgres_adbc_save_recoverable": (
        "computed_key_join",
        _probe_fact(
            "postgres_adbc",
            "save_recoverable",
            code="PIE-R1009",
            detail="WORKSPACE_OBJECT",
        ),
    ),
    "PROBE_values_join_mysql_rows_recover": (
        "values_join",
        _probe_fact("mysql_rows", "recover", detail="REFINEMENT_EXPRESSION_BLOCK_READ"),
    ),
    "PROBE_in_closed_postgres_rows_save_recoverable": (
        "in_closed",
        _probe_fact(
            "postgres_rows",
            "save_recoverable",
            detail="PUBLIC_R2_VALUES_COORDINATE_BASIS",
        ),
    ),
    # MySQL BLOCKS VALUES alone with its word and compiles no query.
    "COMPILE_values_only_mysql": (
        "values_only",
        lambda r: r["dialects"]["mysql"]["compile"].update(
            details=["expression_evidence_unavailable"]
        ),
    ),
    "BUNDLE_values_only_mysql": (
        "values_only",
        lambda r: r["dialects"]["mysql"].update(
            bundle=r["dialects"]["postgres"]["bundle"]
        ),
    ),
    "ROUTES_values_only": (
        "values_only",
        lambda r: r["routes"].update(mysql_rows=r["routes"]["postgres_rows"]),
    ),
    # MySQL BLOCKS each ordered correlated read, in source order.
    "COMPILE_in_limit_mysql": (
        "in_limit",
        lambda r: r["dialects"]["mysql"]["compile"]["details"].pop(),
    ),
    "PROBE_lateral_left_mysql_rows_recover": (
        "lateral_left",
        _probe_fact("mysql_rows", "recover", detail="REFINEMENT_EXPRESSION_BLOCK_READ"),
    ),
    "PROBE_series_join_postgres_rows_save_recoverable": (
        "series_join",
        _probe_fact(
            "postgres_rows",
            "save_recoverable",
            detail="PUBLIC_R2_VALUES_COORDINATE_BASIS",
        ),
    ),
    "SQL_param_capture_mysql": ("param_capture", _sql("mysql", lambda s: s + " ?")),
}


@pytest.mark.parametrize("reason", sorted(OFFLINE_DAMAGES))
def test_the_joint_checker_refuses_each_damaged_offline_fact(joint_shape, reason):
    name, damage = OFFLINE_DAMAGES[reason]
    record = _offline(joint_shape(name))
    damage(record)
    with pytest.raises(joint_check.Rejected, match="^" + reason + "$"):
        joint_check.check_shape(name, record, "offline", list(joint_check.ROUTES))


@pytest.mark.parametrize(
    ("damage", "reason"),
    (
        (lambda r: r.update(format="pietto.execution-joint-acceptance.v0"), "FORMAT"),
        (lambda r: r.update(mode="installed"), "MODE"),
        (lambda r: r["shapes"].pop("let_chain"), "SHAPES"),
    ),
)
def test_the_joint_checker_refuses_a_damaged_envelope(
    joint_shape, monkeypatch, damage, reason
):
    oracles = {"let_chain": joint_check.ORACLES["let_chain"]}
    monkeypatch.setattr(joint_check, "ORACLES", oracles)
    report = {
        "format": joint_check.FORMAT,
        "mode": "offline",
        "shapes": {"let_chain": _offline(joint_shape("let_chain"))},
    }
    damage(report)
    with pytest.raises(joint_check.Rejected, match="^" + reason + "$"):
        joint_check.check(report)


@pytest.mark.parametrize("name", list(joint_check.ORACLES))
def test_the_runner_native_steps_bind_the_public_signatures(joint_shape, name):
    """Every native step binds the real public signature and records what the
    checker reads: exactly the operations whose probes passed, on every
    route, with the oracle's rows or the server's failure."""
    joint_check.check_shape(name, joint_shape(name), "native", list(joint_check.ROUTES))


def _native_of(route, *path):
    def damage(record, change):
        value = record["routes"][route]["native"]
        for key in path:
            value = value[key]
        change(value)

    return damage


NATIVE_DAMAGES = {
    "EXECUTE_let_chain_postgres_rows": (
        _native_of("postgres_rows", "execute", 0, "live", "rows"),
        lambda rows: rows.pop(),
    ),
    "LOADED_let_chain_mysql_rows": (
        _native_of("mysql_rows", "execute", 0, "loaded"),
        lambda fact: fact.update(end="FAILED"),
    ),
    "SAVE_let_chain_postgres_adbc": (
        _native_of("postgres_adbc", "save"),
        lambda fact: fact.update(closings=2),
    ),
    "R1_let_chain_postgres_rows": (
        _native_of("postgres_rows", "save", "r1"),
        lambda fact: fact["end"].__setitem__(3, 0),
    ),
    "R1_EXPORT_let_chain_postgres_rows": (
        _native_of("postgres_rows", "save", "r1", "export"),
        lambda rows: rows.append([1, None]),
    ),
    "R1_PUBLICATION_let_chain_mysql_rows": (
        _native_of("mysql_rows", "save", "r1"),
        lambda fact: fact.update(publication=["FAILED", 16]),
    ),
    "R1_VECTOR_let_chain_postgres_rows": (
        _native_of("postgres_rows", "save", "r1", "vectors"),
        lambda fact: fact.update(bool_for_int={"outcome": "opened"}),
    ),
    "R1_RELEASE_let_chain_postgres_adbc": (
        _native_of("postgres_adbc", "save", "r1"),
        lambda fact: fact.update(released_reopen={"outcome": "opened"}),
    ),
    "R2_let_chain_postgres_rows": (
        _native_of("postgres_rows", "r2"),
        lambda fact: fact.update(prefix=["COMPLETED", False]),
    ),
    "RELAY_let_chain_mysql_rows": (
        _native_of("mysql_rows", "relay_live"),
        lambda fact: fact.update(extent=15),
    ),
    # R2 of a shape of fewer than nine rows runs its probes only.
    "NATIVE_param_where_postgres_adbc": (
        _native_of("postgres_adbc"),
        lambda fact: fact.update(r2={}),
    ),
    "R1_RESTATED_param_where_mysql_rows": (
        _native_of("mysql_rows", "save", "r1", "restated"),
        lambda fact: fact.update(empty_for_null={"outcome": "opened"}),
    ),
    "R1_RESTATED_param_r2_postgres_rows": (
        _native_of("postgres_rows", "save", "r1", "restated"),
        lambda fact: fact.pop("missing"),
    ),
    "R2_RESTATED_param_r2_postgres_adbc": (
        _native_of("postgres_adbc", "r2", "restated"),
        lambda fact: fact.update(bool_for_int={"outcome": "recovered"}),
    ),
    "R2_param_r2_mysql_rows": (
        _native_of("mysql_rows", "r2", "rows"),
        lambda rows: rows.remove([1, 1]),
    ),
    "RELAY_param_capture_postgres_rows": (
        _native_of("postgres_rows", "relay_live"),
        lambda fact: fact.update(extent=6),
    ),
    # LEFT keeps a left row whose every pair the ON rejects, once, as NULL.
    "EXECUTE_lateral_left_postgres_adbc": (
        _native_of("postgres_adbc", "execute", 0, "live", "rows"),
        lambda rows: rows.remove([1, None]),
    ),
    # A LIMIT taken before the correlation would make `b` FALSE for BIG.
    "LOADED_in_limit_postgres_rows": (
        _native_of("postgres_rows", "execute", 0, "loaded", "rows"),
        lambda rows: next(row for row in rows if row[0] != 0).__setitem__(2, False),
    ),
    "EXECUTE_param_where_postgres_rows": (
        _native_of("postgres_rows", "execute"),
        lambda runs: runs.pop(),
    ),
    "LOADED_param_where_postgres_rows": (
        _native_of("postgres_rows", "execute", 1),
        lambda run: run.update(loaded={}),
    ),
    "R2_let_reuse_mysql_rows": (
        _native_of("mysql_rows", "r2", "rows"),
        lambda rows: rows.remove([0, 1]),
    ),
    "EXECUTE_values_only_postgres_adbc": (
        _native_of("postgres_adbc", "execute", 0, "live", "rows"),
        lambda rows: rows.remove([2, None, None, None]),
    ),
    # NULL NOT IN an empty relation is TRUE, not NULL.
    "EXECUTE_in_closed_mysql_rows": (
        _native_of("mysql_rows", "execute", 0, "live", "rows"),
        lambda rows: next(row for row in rows if row[1] is None).__setitem__(4, None),
    ),
    "EXECUTE_scalar_many_postgres_rows": (
        _native_of("postgres_rows", "execute", 0, "live"),
        lambda fact: fact.update(sqlstate="42501"),
    ),
    "LOADED_scalar_many_postgres_adbc": (
        _native_of("postgres_adbc", "execute", 0, "loaded"),
        lambda fact: fact.update(attempt=["FAILED", "ROLLBACK_ACK", "CLOSED", []]),
    ),
    # postgres_adbc closes locally: no PIE-R5001 cleanup failure.
    "EXECUTE_scalar_many_postgres_adbc": (
        _native_of("postgres_adbc", "execute", 0, "live"),
        lambda fact: fact.update(
            attempt=["FAILED", "UNKNOWN", "FAILED", [["PIE-R5001", "transaction"]]]
        ),
    ),
    "LOADED_scalar_many_mysql_rows": (
        _native_of("mysql_rows", "execute", 0, "loaded"),
        lambda fact: fact["attempt"].__setitem__(1, "UNKNOWN"),
    ),
    "EXECUTE_scalar_many_mysql_rows": (
        _native_of("mysql_rows", "execute", 0, "live"),
        lambda fact: fact.update(attempt=["COMPLETE", "COMMIT_ACK", "CLOSED", []]),
    ),
    "SAVE_scalar_many_postgres_rows": (
        _native_of("postgres_rows", "save"),
        lambda fact: fact.update(extent=0),
    ),
    "RELAY_scalar_many_mysql_rows": (
        _native_of("mysql_rows", "relay_live"),
        lambda fact: fact.update(terminal="COMPLETED"),
    ),
}


@pytest.mark.parametrize("reason", sorted(NATIVE_DAMAGES))
def test_the_joint_checker_refuses_each_damaged_native_fact(joint_shape, reason):
    name = max((n for n in joint_check.ORACLES if "_" + n + "_" in reason), key=len)
    locate, change = NATIVE_DAMAGES[reason]
    record = joint_shape(name)
    locate(record, change)
    with pytest.raises(joint_check.Rejected, match="^" + reason + "$"):
        joint_check.check_shape(name, record, "native", list(joint_check.ROUTES))


def _joint_native_report(joint_shape, names: tuple[str, ...]) -> dict[str, Any]:
    targets = ["postgres", "mysql"]
    return {
        "format": joint_check.FORMAT,
        "mode": "native",
        "context": {
            "probe": "1" * 64,
            "check": "2" * 64,
            "docs": "3" * 64,
            "wheel": "pietto-0.1.2-py3-none-any.whl",
            "wheel_sha256": "4" * 64,
        },
        "install": _install("routes"),
        "targets": targets,
        "workers": {t: {"returncode": 0, "origin": "installed"} for t in targets},
        "cleanup": {t: "success" for t in targets},
        "shapes": {name: joint_shape(name) for name in names},
    }


def test_only_a_native_report_of_both_targets_is_accepted(joint_shape, monkeypatch):
    oracles = {"let_chain": joint_check.ORACLES["let_chain"]}
    monkeypatch.setattr(joint_check, "ORACLES", oracles)
    report = _joint_native_report(joint_shape, ("let_chain",))
    accepted = {
        "family": "joint-acceptance",
        "mode": "native",
        "verdict": "ACCEPTED",
        "pending": [],
    }
    assert joint_check.check(report) == accepted
    # One target leaves the other target's routes pending; the campaigns of
    # both targets, judged together, are accepted.
    postgres, mysql = copy.deepcopy(report), copy.deepcopy(report)
    for part, target, other in (
        (postgres, "postgres", "mysql"),
        (mysql, "mysql", "postgres"),
    ):
        part.update(targets=[target])
        for key in ("workers", "cleanup"):
            part[key].pop(other)
        part["shapes"]["let_chain"]["dialects"].pop(other)
        for route, owner in joint_check.ROUTES.items():
            if owner == other:
                part["shapes"]["let_chain"]["routes"].pop(route)
    verdict = joint_check.check(postgres)
    assert (verdict["verdict"], verdict["pending"]) == ("MATCHED", ["route:mysql_rows"])
    assert joint_check.check(joint_check.combined([postgres, mysql])) == accepted
    with pytest.raises(joint_check.Rejected, match="^TARGETS$"):
        joint_check.combined([postgres, postgres])
    mysql["context"]["wheel_sha256"] = "5" * 64
    with pytest.raises(joint_check.Rejected, match="^CONTEXT$"):
        joint_check.combined([postgres, mysql])
    # Database-free facts alone are never an acceptance.
    offline = {
        "format": joint_check.FORMAT,
        "mode": "offline",
        "shapes": {"let_chain": _offline(joint_shape("let_chain"))},
    }
    assert joint_check.check(offline)["pending"] == ["offline"]


@pytest.mark.parametrize(
    ("damage", "reason"),
    (
        (lambda r: r["context"].update(wheel_sha256="0"), "CONTEXT"),
        (
            lambda r: r["install"]["routes"].update(
                python=["CPython", "3.12.14", "Linux", "x86_64"]
            ),
            "INSTALL",
        ),
        (lambda r: r.update(targets=["postgres", "postgres"]), "TARGETS"),
        (lambda r: r["workers"]["mysql"].update(origin="checkout"), "WORKER"),
        (lambda r: r["cleanup"].update(postgres="failed"), "CLEANUP"),
    ),
)
def test_the_joint_checker_refuses_a_damaged_native_envelope(
    joint_shape, damage, reason
):
    report = _joint_native_report(joint_shape, ("let_chain",))
    damage(report)
    with pytest.raises(joint_check.Rejected, match="^" + reason + "$"):
        joint_check.check(report)
