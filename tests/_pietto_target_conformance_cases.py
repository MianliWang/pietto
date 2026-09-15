"""Six finite, independently specified target controls; no resource acquisition."""

from __future__ import annotations

from collections import Counter
import json
import hashlib
from typing import Any

TARGETS = ("postgres", "mysql")
CASE_IDS = (
    "A_legacy",
    "B_result",
    "C_parameters",
    "D_diagnostics",
    "E_recovery",
    "F_privilege_cleanup",
)
BIG = 9007199254740993
TEXT = "雪?%s e\u0301 😀"


def legacy_source(target: str) -> str:
    if target not in TARGETS:
        raise ValueError("unknown target")
    return (
        "shape LegacyRow:\n    id: Int not null\n"
        f'source source_rows: LegacyRow is {target}.table("phase66_rows")\n'
        "table legacy_rows:\n    from source_rows\n    select:\n        id\n"
    )


def legacy_sql(target: str) -> str:
    quote = '"' if target == "postgres" else "`"
    return f"SELECT\n    {quote}id{quote} AS {quote}id{quote}\nFROM {quote}phase66_rows{quote}"


def control(target: str, case: str) -> tuple[str, tuple[object, ...]]:
    if case == "B_result":
        return "SELECT id, note FROM phase66_control_rows ORDER BY seq", ()
    if case == "C_parameters":
        if target == "postgres":
            return "SELECT $1::bigint AS a, $2::text AS txt, $1::bigint AS again", (
                BIG,
                TEXT,
            )
        return (
            "SELECT CAST(? AS SIGNED) AS a, CAST(? AS CHAR CHARACTER SET utf8mb4) AS txt, CAST(? AS SIGNED) AS again",
            (BIG, TEXT, BIG),
        )
    raise ValueError("unknown control")


def setup(target: str) -> tuple[tuple[str, tuple[object, ...]], ...]:
    markers = ("$1", "$2", "$3") if target == "postgres" else ("?", "?", "?")
    return (
        ("CREATE TABLE phase66_rows (id BIGINT NOT NULL)", ()),
        ("INSERT INTO phase66_rows VALUES (1), (1)", ()),
        (
            "CREATE TABLE phase66_control_rows (seq INTEGER NOT NULL, id BIGINT NOT NULL, note VARCHAR(64))",
            (),
        ),
        (
            f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
            (1, 7, None),
        ),
        (
            f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
            (2, 7, None),
        ),
        (
            f"INSERT INTO phase66_control_rows VALUES ({', '.join(markers)})",
            (3, BIG, TEXT),
        ),
        ("CREATE TABLE phase66_diagnostic_rows (value VARCHAR(5))", ()),
    )


def _integer(value: str) -> dict[str, str]:
    return {"kind": "int", "value": value}


def _text(value: str) -> dict[str, str]:
    return {"kind": "text", "value": value}


def expected_rows(case: str) -> list[list[dict[str, str]]]:
    # These literals are the oracle, not the observer's encoding of its results.
    if case == "A_legacy":
        return [[_integer("1")], [_integer("1")]]
    if case == "B_result":
        return [
            [_integer("7"), {"kind": "null"}],
            [_integer("7"), {"kind": "null"}],
            [_integer("9007199254740993"), _text(TEXT)],
        ]
    if case == "C_parameters":
        return [
            [_integer("9007199254740993"), _text(TEXT), _integer("9007199254740993")]
        ]
    raise ValueError("no row oracle for case")


def check_complete(observation: dict[str, Any]) -> None:
    keys = {
        "sql",
        "sql_sha256",
        "parameters",
        "identity",
        "prepared",
        "buffering",
        "status",
        "execute",
        "fetch",
        "close",
        "metadata",
        "rows",
        "diagnostics",
        "failures",
        "cursor_type",
    }
    if (
        set(observation) != keys
        or type(observation["sql"]) is not str
        or type(observation["parameters"]) is not list
        or type(observation["rows"]) is not list
    ):
        raise ValueError("malformed observation")
    if (
        observation["sql"] != "CREDENTIAL_MANAGEMENT"
        and observation["sql_sha256"]
        != hashlib.sha256(observation["sql"].encode()).hexdigest()
    ):
        raise ValueError("SQL byte identity mismatch")
    if observation["fetch"] == "success":
        metadata = observation["metadata"]
        if (
            not isinstance(metadata, list)
            or not metadata
            or any(
                not isinstance(column, list) or len(column) < 7 for column in metadata
            )
            or any(len(row) != len(metadata) for row in observation["rows"])
        ):
            raise ValueError("incomplete positional metadata")
    elif observation["fetch"] == "not_applicable" and (
        observation["metadata"] is not None or observation["rows"] != []
    ):
        raise ValueError("unexpected unobserved result")
    if (
        observation.get("status") != "success"
        or observation.get("execute") != "success"
        or observation.get("fetch") not in {"success", "not_applicable"}
        or observation.get("close") != "success"
        or observation.get("failures") != []
        or observation.get("diagnostics", {}).get("complete") is not True
    ):
        raise ValueError("incomplete observation")
    diagnostic = observation["diagnostics"]
    if (
        set(diagnostic) != {"protocol", "total", "details", "complete"}
        or (
            diagnostic["protocol"] == "postgres_notices"
            and diagnostic["total"] is not None
        )
        or (
            diagnostic["protocol"] == "mysql_warnings"
            and (
                type(diagnostic["total"]) is not int
                or diagnostic["total"] != len(diagnostic["details"])
            )
        )
    ):
        raise ValueError("diagnostic completeness mismatch")


def check_identity(
    observation: dict[str, Any], target: str, identity: str, *, prepared: bool = False
) -> None:
    if (
        observation.get("identity") != identity
        or observation.get("prepared") is not (prepared or target == "postgres")
        or observation.get("buffering")
        != ("client_complete" if target == "postgres" else "unbuffered")
        or observation.get("diagnostics", {}).get("protocol")
        != ("postgres_notices" if target == "postgres" else "mysql_warnings")
    ):
        raise ValueError("observation identity or protocol substitution")


def check_rows(observation: dict[str, Any], case: str, target: str) -> None:
    check_complete(observation)
    expected = expected_rows(case)
    actual = observation["rows"]
    if case == "A_legacy":
        actual_bag = Counter(json.dumps(row, sort_keys=True) for row in actual)
        expected_bag = Counter(json.dumps(row, sort_keys=True) for row in expected)
        if actual_bag != expected_bag:
            raise ValueError("BAG result mismatch")
    elif actual != expected:
        raise ValueError("ordered result or value type mismatch")
    names = {
        "A_legacy": ["id"],
        "B_result": ["id", "note"],
        "C_parameters": ["a", "txt", "again"],
    }[case]
    types = {
        "postgres": {
            "A_legacy": [20],
            "B_result": [20, 1043],
            "C_parameters": [20, 25, 20],
        },
        "mysql": {"A_legacy": [8], "B_result": [8, 253], "C_parameters": [8, 253, 8]},
    }[target][case]
    metadata = observation.get("metadata")
    if (
        not isinstance(metadata, list)
        or [m[0] for m in metadata] != names
        or [m[1] for m in metadata] != types
    ):
        raise ValueError("positional metadata mismatch")
    if any(len(m) < 7 for m in metadata):
        raise ValueError("incomplete protocol metadata")
    if target == "postgres" and any(m[6] is not None for m in metadata):
        raise ValueError("unavailable nullability metadata was invented")


def check_server_error(
    observation: dict[str, Any], target: str, *, privilege: bool = False
) -> None:
    expected = (
        ("42501" if privilege else "22012")
        if target == "postgres"
        else ("42000" if privilege else "42S22")
    )
    failures = observation.get("failures", [])
    if (
        observation.get("status") != "failed"
        or observation.get("execute") != "failed"
        or observation.get("close") != "success"
        or len(failures) != 1
        or failures[0].get("stage") != "execute"
        or failures[0].get("sqlstate") != expected
        or (
            target == "mysql"
            and failures[0].get("vendor_code") != (1044 if privilege else 1054)
        )
        or observation.get("diagnostics", {}).get("complete") is not True
    ):
        raise ValueError("wrong failure layer or exact server error")
    if target == "mysql":
        diagnostic = observation["diagnostics"]
        if (
            diagnostic["total"] != 1
            or len(diagnostic["details"]) != 1
            or diagnostic["details"][0]["vendor_code"] != (1044 if privilege else 1054)
            or diagnostic["details"][0]["severity"] != "Error"
        ):
            raise ValueError("server error diagnostic loss")


def check_case(case: dict[str, Any], target: str) -> None:
    case_id = case.get("id")
    observations = case.get("observations", [])
    if case_id in CASE_IDS[:3]:
        if len(observations) != 1:
            raise ValueError("wrong observation denominator")
        statement, params = (
            (legacy_sql(target), ())
            if case_id == "A_legacy"
            else control(target, case_id)
        )
        observation = observations[0]
        check_identity(observation, target, "query", prepared=case_id == "C_parameters")
        if observation.get("sql") != statement:
            raise ValueError("submitted SQL substitution")
        expected_params = (
            []
            if not params
            else [_integer("9007199254740993"), _text(TEXT)]
            + ([_integer("9007199254740993")] if target == "mysql" else [])
        )
        if observation.get("parameters") != expected_params:
            raise ValueError("submitted parameter substitution")
        if case_id == "C_parameters" and observation.get("cursor_type") != (
            "psycopg.RawCursor"
            if target == "postgres"
            else "mysql.connector.cursor.MySQLCursorPrepared"
        ):
            raise ValueError("wrong native parameter cursor")
        check_rows(observation, case_id, target)
    elif case_id == "D_diagnostics":
        if len(observations) != (2 if target == "postgres" else 3):
            raise ValueError("wrong diagnostic control denominator")
        first, empty = observations[:2]
        check_identity(first, target, "fixture_manager")
        check_identity(empty, target, "query")
        statement = (
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')"
        )
        if (
            first.get("sql") != statement
            or empty.get("sql") != "SELECT 1 AS v"
            or any(observation.get("parameters") != [] for observation in observations)
        ):
            raise ValueError("diagnostic statement or parameter substitution")
        check_complete(first)
        check_complete(empty)
        if empty["rows"] != [[_integer("1")]]:
            raise ValueError("diagnostic success control lost its row")
        details = first["diagnostics"]["details"]
        if len(details) != 1 or empty["diagnostics"]["details"] != []:
            raise ValueError("lost or unexpected diagnostic")
        if target == "postgres":
            if (
                first["diagnostics"]["total"] is not None
                or details[0]["sqlstate"] != "42P07"
                or details[0]["severity"] != "NOTICE"
            ):
                raise ValueError("wrong PostgreSQL notice")
        else:
            settings = case.get("settings", [])
            if [item.get("sql") for item in settings] != [
                "SET SESSION max_error_count=0",
                "SET SESSION max_error_count=64",
            ]:
                raise ValueError("diagnostic control setting evidence missing")
            for item in settings:
                check_complete(item)
                check_identity(item, target, "fixture_manager")
                if item["parameters"] != []:
                    raise ValueError("diagnostic setting parameter substitution")
            if first["diagnostics"]["total"] != 1 or details[0]["vendor_code"] != 1265:
                raise ValueError("wrong MySQL fixture warning")
            truncated = observations[2]
            check_identity(truncated, target, "fixture_manager")
            if truncated.get("sql") != statement:
                raise ValueError("truncation statement substitution")
            if (
                truncated.get("status") != "failed"
                or truncated["diagnostics"]
                != {
                    "protocol": "mysql_warnings",
                    "total": 1,
                    "details": [],
                    "complete": False,
                }
                or truncated.get("close") != "success"
                or [f.get("kind") for f in truncated.get("failures", [])]
                != ["DIAGNOSTICS_INCOMPLETE"]
            ):
                raise ValueError("truncation cannot be complete success")
    elif case_id in {"E_recovery", "F_privilege_cleanup"}:
        if len(observations) != 3:
            raise ValueError("wrong success-failure-success denominator")
        for observation in observations:
            check_identity(observation, target, "query")
        error_sql = (
            (
                "CREATE TABLE public.phase66_denied (id BIGINT)"
                if target == "postgres"
                else "CREATE DATABASE phase66_denied"
            )
            if case_id == "F_privilege_cleanup"
            else (
                "SELECT 1/0"
                if target == "postgres"
                else "SELECT missing_column FROM phase66_rows"
            )
        )
        if [observation.get("sql") for observation in observations] != [
            "SELECT 1 AS v",
            error_sql,
            "SELECT 2 AS v",
        ] or any(observation.get("parameters") != [] for observation in observations):
            raise ValueError("recovery statement or parameter substitution")
        check_complete(observations[0])
        check_server_error(
            observations[1], target, privilege=case_id == "F_privilege_cleanup"
        )
        check_complete(observations[2])
        if observations[0]["rows"] != [[_integer("1")]] or observations[2]["rows"] != [
            [_integer("2")]
        ]:
            raise ValueError("recovery control result mismatch")
        if (
            case.get("recovery") != "success"
            or case.get("session_before") != case.get("session_after")
            or type(case.get("session_before")) is not int
            or case.get("session_before", 0) <= 0
        ):
            raise ValueError("reconnection or failed recovery")
        if case_id == "E_recovery":
            begin = case.get("begin", {})
            check_complete(begin)
            check_identity(begin, target, "query")
            if begin["sql"] != "BEGIN" or begin["parameters"] != []:
                raise ValueError("transaction start evidence missing")
            expected_states = (3, 0) if target == "postgres" else (True, False)
            actual_states = (
                case.get("state_after_failure"),
                case.get("state_after_recovery"),
            )
            if actual_states != expected_states or any(
                type(actual) is not type(expected)
                for actual, expected in zip(actual_states, expected_states, strict=True)
            ):
                raise ValueError("transaction recovery was not observed")
        if (
            case_id == "F_privilege_cleanup"
            and case.get("privileges_verified") is not True
        ):
            raise ValueError("query privilege evidence missing")
    else:
        raise ValueError("unknown case")
