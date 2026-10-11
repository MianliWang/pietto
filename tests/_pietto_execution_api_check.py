"""Independent checker of the public execution witnesses; data only.

It judges the raw facts `_pietto_execution_api_probe` wrote against literal
oracles: the interpreter, the server's TLS and pg_hba.conf rules, the
fixture's rows, the documented example's output over TLS and on loopback, the
PIE-R codes and terminal states each case must reach, the 10 second statement
limit, the effects an attempt leaves, and the absence of every password.
"""

from __future__ import annotations

import ast
from collections import Counter
from typing import Any

FORMAT = "pietto.execution-api-witness.v1"
# fixture.items rows with id > 1, as a bag: the documented query's oracle.
ROWS = [[2, "two"], [2, "two"], [3, "three"], [5, "five"]]
AMBIENT = (
    "PGHOST",
    "PGPASSWORD",
    "PGSERVICE",
    "SSLKEYLOGFILE",
    "OPENSSL_CONF",
    "OPENSSL_MODULES",
)
REFUSALS = {
    "premise_none": ["PIE-R1001", "PUBLIC_PREMISE_REQUIRED", False],
    "route_adbc": ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE", False],
    "socket_host": ["PIE-R1002", "EXECUTION_ACCESS_PROFILE", False],
    "sql_text": ["PIE-R1002", "PUBLIC_QUERY_TYPE", False],
}
ROLES = ("pietto_cleartext", "pietto_md5", "pietto_trust")
# The interpreter the docs name for the witness.
INTERPRETER = ["CPython", "3.13.13", "Linux", "x86_64"]
# pg_hba.conf as the server reports it, first match first: the refused
# methods, the documented hostssl line and loopback host line of the reader,
# and the fixture's manager.
HBA = [
    ["local", ["all"], "trust"],
    ["host", ["pietto_trust"], "trust"],
    ["host", ["pietto_cleartext"], "password"],
    ["host", ["pietto_md5"], "md5"],
    ["hostssl", ["pietto_reader"], "scram-sha-256"],
    ["host", ["pietto_reader"], "scram-sha-256"],
    ["host", ["pietto_manager"], "scram-sha-256"],
]
TLS = ("TLSv1.2", "TLSv1.3")
EXAMPLE_REPR = (
    "CompiledQuery(module='main.pietto', kind='table', name='active_items',"
    " dialect='postgres', release='18.6', literal_policy='preserve')"
)


class Rejected(ValueError):
    pass


def need(condition: object, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def result(record: Any, reason: Any) -> Any:
    need(type(record) is dict and record.get("returncode") == 0, reason)
    value = record.get("result")
    need(type(value) is dict, reason)
    return value


def check_install(install: Any, recipes: Any) -> None:
    for recipe in recipes:
        commands = install.get(recipe)
        need(type(commands) is dict, "INSTALL")
        for step in ("venv", "install", "check"):
            need(commands.get(step, {}).get("returncode") == 0, "INSTALL")
        need(commands.get("python") == INTERPRETER, "INTERPRETER")


def unopened(value: Any) -> None:
    need(value.get("after_import") == [], "IMPORT_LOADED_DRIVER")
    need(value.get("unopened") == [[], "NOT_STARTED", False], "UNOPENED_EFFECT")


def refused(record: Any, code: Any, detail: Any, reason: Any) -> Any:
    value = result(record, reason)
    unopened(value)
    need((value.get("code"), value.get("detail")) == (code, detail), reason)
    need(value.get("shown") is False and value.get("chained") is False, "CREDENTIAL")
    outcome = value.get("outcome") or {}
    need(
        (outcome.get("end"), outcome.get("transaction"), outcome.get("cleanup"))
        == ("FAILED", "NOT_STARTED", "CLOSED"),
        reason,
    )
    need(record.get("connected") is False, reason)
    return value


def check_consumer_cases(cases: Any) -> None:
    """The database-free laws, from an installed prefix or the checkout."""
    imports = result(cases.get("imports"), "IMPORTS")
    unopened(imports)
    need(imports.get("refusals") == REFUSALS, "REQUEST_REFUSALS")
    need(cases["imports"].get("connected") is False, "IMPORT_CONNECTED")
    ambient = cases.get("ambient") or {}
    need(sorted(ambient) == sorted(AMBIENT), "AMBIENT_DENOMINATOR")
    for name in AMBIENT:
        value = refused(
            ambient[name],
            "PIE-R2003",
            "EXECUTION_AMBIENT_CONNECTION_PROFILE",
            "AMBIENT_" + name,
        )
        need(value.get("after_open") == [], "AMBIENT_LOADED_DRIVER")
        need(ambient[name].get("keylog_created") is False, "KEYLOG_OPENED")
    shadow = cases.get("shadow") or {}
    value = refused(shadow, "PIE-R2002", "EXECUTION_DRIVER_VERSION", "SHADOW")
    need(value.get("psycopg_file") == shadow.get("shadow"), "SHADOW_NOT_IMPORTED")
    need(shadow.get("shadow_imported") is True, "SHADOW_NOT_IMPORTED")
    need(shadow.get("shadow_connected") is False, "SHADOW_CONNECTED")
    identity = cases.get("identity") or {}
    clean = result(identity.get("clean"), "IDENTITY")
    stray = result(identity.get("stray"), "IDENTITY")
    need(len(str(clean.get("identity"))) == 64, "IDENTITY")
    need(clean.get("identity") == stray.get("identity"), "IDENTITY_FOLLOWS_CWD")
    need(stray.get("metadata") == "9.9.9", "IDENTITY_CONTROL")
    need(clean.get("metadata") != "9.9.9", "IDENTITY_CONTROL")


def check_consumer(report: Any) -> Any:
    check_install(report.get("install", {}), ("core", "execute-postgres"))
    core = refused(
        report.get("core"),
        "PIE-R2001",
        "EXECUTION_DEPENDENCY_MISSING",
        "CORE_FALLBACK",
    )
    need(core.get("after_open") == [], "CORE_LOADED_DRIVER")
    check_consumer_cases(report.get("cases") or {})
    return {"family": "consumer", "verdict": "ACCEPTED"}


def outcome_of(value: Any, reason: Any) -> Any:
    outcome = value.get("outcome")
    need(type(outcome) is dict, reason)
    ack = outcome.get("transaction") in ("COMMIT_ACK", "ROLLBACK_ACK")
    need(
        outcome.get("remote")
        == ("TRANSACTION_ACK" if ack else "REMOTE_QUIESCENCE_UNCONFIRMED"),
        reason,
    )
    return outcome


def check_server(server: Any) -> None:
    need(server.get("version") == "180006", "SERVER_VERSION")
    need(server.get("ssl") == "on", "SERVER_TLS")
    need(server.get("password_encryption") == "scram-sha-256", "SCRAM_DEFAULT")
    need(
        server.get("reader_settings") == ["statement_timeout=0"],
        "READER_STATEMENT_LIMIT",
    )
    hba = server.get("hba") or []
    need(all(row[3] is None for row in hba), "HBA_ERROR")
    need([row[:3] for row in hba] == HBA, "HBA_METHODS")
    hashes = {row[0]: (row[1], row[2]) for row in server.get("hashes") or []}
    need(hashes.get("pietto_reader") == (True, False), "SCRAM_ROLE")
    need(hashes.get("pietto_cleartext") == (True, False), "SCRAM_ROLE")
    need(hashes.get("pietto_md5") == (False, True), "MD5_ROLE")


def check_effects(value: Any, reason: str) -> None:
    """An attempt that ended leaves no thread, no workspace module and no
    file in the working directory, HOME or TMPDIR."""
    before, after = value.get("before") or {}, value.get("after") or {}
    need(after.get("threads") == ["MainThread"], reason + "_THREADS")
    need(before.get("jobs") == [] and after.get("jobs") == [], reason + "_WORKSPACE")
    files = before.get("files") or {}
    need(sorted(files) == ["cwd", "home", "tmp"], reason + "_FILES")
    need(files["home"] == files["tmp"] == [], reason + "_FILES")
    need(after.get("files") == files, reason + "_FILES")


def check_example(record: Any) -> None:
    need(type(record) is dict and record.get("returncode") == 0, "EXAMPLE")
    need(record.get("shown") is False, "CREDENTIAL")
    lines = record.get("stdout", "").strip().splitlines()
    need(len(lines) >= 3 and lines[0] == EXAMPLE_REPR, "EXAMPLE_COMPILE")
    need(
        lines[-2:] == ["COMPLETE COMMIT_ACK CLOSED", "PIE-R1001 INPUT_MISSING"],
        "EXAMPLE_END",
    )
    found: list[list[Any]] = []
    for line in lines[1:-2]:
        batch: list[dict[str, Any]] = ast.literal_eval(line)
        need(type(batch) is list and batch, "EXAMPLE_BATCH")
        found.extend([row["id"], row["label"]] for row in batch)
    need(Counter(map(tuple, found)) == Counter(map(tuple, ROWS)), "EXAMPLE_ROWS")


def check_postgres(report: Any) -> Any:
    check_install(report.get("install", {}), ("execute-postgres",))
    check_server(report.get("server") or {})
    check_example(report.get("example"))
    check_example(report.get("example_loopback"))
    bind = result(report.get("bind_safe"), "BIND_SAFE")
    need(bind.get("rows") == sorted(ROWS), "BIND_SAFE_ROWS")
    outcome = outcome_of(bind, "BIND_SAFE")
    need(
        (outcome["end"], outcome["transaction"], outcome["cleanup"], outcome["rows"])
        == ("COMPLETE", "COMMIT_ACK", "CLOSED", 4),
        "BIND_SAFE_END",
    )
    check_effects(bind, "BIND_SAFE")
    early = result(report.get("early_stop"), "EARLY_STOP")
    outcome = outcome_of(early, "EARLY_STOP")
    need(early.get("first_rows") == 1, "EARLY_STOP")
    need(
        (outcome["end"], outcome["transaction"], outcome["rows"], outcome["primary"])
        == ("STOPPED_EARLY", "ROLLBACK_ACK", 1, None),
        "EARLY_STOP_END",
    )
    check_effects(early, "EARLY_STOP")
    check = result(report.get("result_check"), "RESULT_CHECK")
    need(
        (check.get("code"), check.get("detail")) == ("PIE-R3005", "VALUE_DOMAIN"),
        "RESULT_CHECK",
    )
    outcome = outcome_of(check, "RESULT_CHECK")
    need(
        (outcome["end"], outcome["transaction"], outcome["cleanup"])
        == ("FAILED", "ROLLBACK_ACK", "CLOSED"),
        "RESULT_CHECK_END",
    )
    authentication = report.get("authentication") or {}
    need(sorted(authentication) == list(ROLES), "AUTH_DENOMINATOR")
    for role in ROLES:
        value = result(authentication[role], "AUTH_" + role)
        need(
            (value.get("code"), value.get("cause"))
            == ("PIE-R2004", "OperationalError"),
            "AUTH_" + role,
        )
        need(
            value.get("shown") is False and value.get("chained") is False, "CREDENTIAL"
        )
        need(value["outcome"]["transaction"] == "NOT_STARTED", "AUTH_" + role)
    timeout = result(report.get("statement_timeout"), "STATEMENT_TIMEOUT")
    need(
        (timeout.get("code"), timeout.get("sqlstate")) == ("PIE-R3002", "57014"),
        "STATEMENT_TIMEOUT",
    )
    # Only Pietto's limit applies (60 s deadline, no server-side limit for the
    # role). The window, counted from the opened attempt, confirms that this
    # limit of about 10 s ended the statement: without it the deadline would,
    # and a cap of 12 s or more falls outside. The exact 10 000 ms is pinned
    # offline (test_each_statement_is_limited_to_exactly_10_seconds).
    opened = timeout.get("opened")
    need(
        type(opened) is float and 9.5 <= timeout.get("seconds", 0) - opened < 12.0,
        "STATEMENT_TIMEOUT_SECONDS",
    )
    outcome = outcome_of(timeout, "STATEMENT_TIMEOUT")
    need(outcome["end"] == "FAILED", "STATEMENT_TIMEOUT_END")
    need(outcome["primary"][2] == "execute", "STATEMENT_TIMEOUT_PHASE")
    # The aborted transaction is closed with the connection, not rolled back.
    need(
        (outcome["transaction"], outcome["cleanup"], outcome["cleanup_failures"])
        == ("UNKNOWN", "FAILED", [["PIE-R5001", "transaction", "ExecutionError"]]),
        "STATEMENT_TIMEOUT_END",
    )
    drop: Any = report.get("dropped") or {}
    value: Any = drop.get("result")
    need(drop.get("returncode") == 0 and type(value) is dict, "DROPPED")
    need(value.get("warnings") == [["PIE-R5002", "DROPPED", True]], "DROPPED_WARNING")
    need(drop.get("during") == 1, "DROPPED_SESSION")
    tls = drop.get("tls") or []
    need(len(tls) == 1 and tls[0][0] is True and tls[0][1] in TLS, "ACTUAL_TLS")
    need(2.0 <= (drop.get("exit_delay") or 0) < 30.0, "DROPPED_EXIT_DELAY")
    need(drop.get("after") == 0, "DROPPED_SESSION_LEFT")
    need((report.get("cleanup") or {}).get("status") == "success", "RESOURCE_CLEANUP")
    return {"family": "postgres", "verdict": "ACCEPTED"}


def check(report: Any) -> Any:
    need(type(report) is dict and report.get("format") == FORMAT, "ENVELOPE")
    family = report.get("family")
    need(family in ("consumer", "postgres"), "ENVELOPE")
    return (check_consumer if family == "consumer" else check_postgres)(report)
