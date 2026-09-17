"""Six finite, independently specified target controls; no resource acquisition."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
import hashlib
from typing import Any
import _pietto_phase66_sql_emission_probe as emission
from _pietto_mysql_native_prepared import API, verify_native

TARGETS = ("postgres", "mysql")
SLICE2_CASE_IDS = (
    "A_legacy",
    "B_result",
    "C_parameters",
    "D_diagnostics",
    "E_recovery",
    "F_privilege_cleanup",
)
CASE_IDS = (*SLICE2_CASE_IDS, *sorted((*emission.VARIANTS, "Q_native_lifecycle")))
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
        (
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
        + emission_setup(target)
        + native_setup(target)
    )


def native_setup(target):
    quote = '"' if target == "postgres" else chr(96)

    def identifier(value):
        return quote + value.replace(quote, quote * 2) + quote

    columns = ", ".join(
        identifier(name) + " BIGINT" + (" NOT NULL" if i < 3 else "")
        for i, name in enumerate(('%s"', '?"', "%s", "neighbor"))
    )
    return (
        (f"CREATE TABLE {identifier('phase66 native')} ({columns})", ()),
        (f"CREATE TABLE {identifier('phase66 native empty')} ({columns})", ()),
        (
            f"INSERT INTO {identifier('phase66 native')} VALUES (11,99,7,NULL),(11,99,7,NULL)",
            (),
        ),
    )


def emission_setup(target):
    if target == "postgres":
        columns = '"order.id" BIGINT NOT NULL, "flag value" BOOLEAN, "text `""é" TEXT COLLATE "C" NOT NULL, "amount value" NUMERIC(9,2) NOT NULL, "ratio value" DOUBLE PRECISION NOT NULL'
        names = ('"phase66 source é"', '"phase66 empty é"')
        parameters = "$1, $2, $3, $4, $5"
    else:
        columns = '`order.id` BIGINT NOT NULL, `flag value` TINYINT, `text ``"é` VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL, `amount value` DECIMAL(9,2) NOT NULL, `ratio value` DOUBLE NOT NULL'
        names = ("`phase66 source é`", "`phase66 empty é`")
        parameters = "?, ?, ?, ?, ?"
    rows = (
        (
            BIG,
            True if target == "postgres" else 1,
            "trail 😀  ",
            Decimal("12.30"),
            -0.0,
        ),
        (
            BIG,
            True if target == "postgres" else 1,
            "trail 😀  ",
            Decimal("12.30"),
            -0.0,
        ),
        (0, False if target == "postgres" else 0, "A", Decimal("0.00"), 1.5),
        (1, None, "a ", Decimal("-0.01"), 0.0),
    )
    collision = '"p0"' if target == "postgres" else "`p0`"
    return (
        tuple((f"CREATE TABLE {name} ({columns})", ()) for name in names)
        + tuple((f"INSERT INTO {names[0]} VALUES ({parameters})", row) for row in rows)
        + ((f"CREATE TABLE {collision} ({columns})", ()),)
        + tuple((f"INSERT INTO {collision} VALUES ({parameters})", row) for row in rows)
    )


def emission_rows(target, *, empty=False):
    if empty:
        return []
    true = (
        {"kind": "bool", "value": True}
        if target == "postgres"
        else {"kind": "int", "value": "1"}
    )
    false = (
        {"kind": "bool", "value": False}
        if target == "postgres"
        else {"kind": "int", "value": "0"}
    )
    duplicate = [
        {"kind": "text", "value": "trail 😀  "},
        {"kind": "int", "value": "9007199254740993"},
        true,
        {"kind": "decimal", "value": "12.30"},
        {"kind": "float", "value": "-0x0.0p+0"},
    ]
    return [
        duplicate,
        duplicate,
        [
            {"kind": "text", "value": "A"},
            {"kind": "int", "value": "0"},
            false,
            {"kind": "decimal", "value": "0.00"},
            {"kind": "float", "value": "0x1.8000000000000p+0"},
        ],
        [
            {"kind": "text", "value": "a "},
            {"kind": "int", "value": "1"},
            {"kind": "null"},
            {"kind": "decimal", "value": "-0.01"},
            {"kind": "float", "value": "0x0.0p+0"},
        ],
    ]


def emission_setup_parameters(target):
    # Independent expected insertion order; never use the observer as an oracle.
    rows = [[row[1], row[2], row[0], row[3], row[4]] for row in emission_rows(target)]
    return [[], [], *rows, [], *rows]


def chain_rows(target, *, empty=False):
    return [[*row, dict(row[1])] for row in emission_rows(target, empty=empty)]


def fixed_rows(target, *, named=False, empty=False):
    """Independent typed oracles, never produced from compiler/public values."""
    if empty:
        return []
    if named:
        row = [
            {"kind": "int", "value": "11"},
            {"kind": "null"},
            {"kind": "int", "value": "17"},
            {"kind": "int", "value": "17"},
            {"kind": "float", "value": "0x1.8000000000000p+0"},
            {"kind": "float", "value": "-0x0.0p+0"},
            {"kind": "text", "value": "雪?%s $1"},
        ]
    else:
        row = [
            {"kind": "int", "value": "11"},
            {"kind": "null"},
            {"kind": "bool", "value": True}
            if target == "postgres"
            else {"kind": "int", "value": "1"},
            {"kind": "bool", "value": False}
            if target == "postgres"
            else {"kind": "int", "value": "0"},
            {"kind": "int", "value": "1"},
            {"kind": "float", "value": "0x1.0000000000000p+0"},
            {"kind": "int", "value": "0"},
            {"kind": "int", "value": "2"},
            {"kind": "int", "value": "-2"},
            {"kind": "float", "value": "0x0.0p+0"},
            {"kind": "float", "value": "-0x0.0p+0"},
            {"kind": "float", "value": "-0x1.8000000000000p+0"},
            {"kind": "int", "value": "9007199254740993"},
            {"kind": "int", "value": "17"},
            {"kind": "int", "value": "17"},
            {"kind": "text", "value": ""},
            {"kind": "text", "value": "a  "},
            {"kind": "text", "value": "雪e\u0301😀"},
            {"kind": "text", "value": "? %s $1"},
            {"kind": "text", "value": "\"'\\\n"},
        ]
    return [row, row]


def parameter_records(document):
    records = []
    for use in document["parameter_uses"]:
        if use["server_index"] <= len(records):
            continue
        value = document["fixed_values"][use["slot"]]
        tag, payload = value["tag"], value["value"]
        if tag == "Bool" and document["target"]["family"] == "mysql":
            record = {"kind": "int", "value": "1" if payload else "0"}
        else:
            record = {
                "kind": {
                    "Bool": "bool",
                    "Int": "int",
                    "Float": "float",
                    "Text": "text",
                }[tag],
                "value": payload,
            }
        records.append(record)
    return records


def fixed_metadata(target, *, named):
    tags = emission.FIXED_NAMED_TAGS if named else emission.FIXED_TAGS
    # Every Text anchor result, empty or not and whichever literal policy
    # produced it, is VAR_STRING on the pinned MySQL 8.4.12; the CAST target
    # spelling is not the protocol result type.
    mapping = (
        {"Bool": 16, "Int": 20, "Float": 701, "Text": 25}
        if target == "postgres"
        else {"Bool": 8, "Int": 8, "Float": 5, "Text": 253}
    )
    return [mapping[tag] for tag in tags]


def check_emission_case(case, target):
    if set(case) != {"id", "observations", "variants"} or [
        v["variant"] for v in case["variants"]
    ] != list(emission.VARIANTS[case["id"]]):
        raise ValueError("emission case denominator mismatch")
    observed = iter(case["observations"])
    for variant in case["variants"]:
        if set(variant) != {
            "variant",
            "public",
            "public_sha256",
            "submission_before",
            "submission_after",
        }:
            raise ValueError("emission transfer fields")
        data = variant["public"].encode("utf-8")
        if hashlib.sha256(data).hexdigest() != variant["public_sha256"]:
            raise ValueError("public artifact transfer substitution")
        document = emission.decode_public(data)
        before, after = variant["submission_before"], variant["submission_after"]
        if type(before) is not int or type(after) is not int or before < 0:
            raise ValueError("submission observation missing")
        expected_status = emission.expected_status(case["id"])
        if document["status"] != expected_status or after - before != (
            1 if expected_status == "VERIFIED" else 0
        ):
            raise ValueError("compiler failure submitted or wrong outcome")
        if expected_status != "VERIFIED":
            continue
        observation = next(observed, None)
        if (
            observation is None
            or observation["sql"].encode() != document["sql"].encode()
            or observation["parameters"] != parameter_records(document)
        ):
            raise ValueError("emitted artifact/submission mismatch")
        check_complete(observation)
        check_identity(observation, target, "query", prepared=True)
        if case["id"] in {"R_fixed_direct", "S_fixed_named"}:
            named = case["id"] == "S_fixed_named"
            expected_rows = fixed_rows(
                target, named=named, empty=variant["variant"].startswith("empty")
            )
            if Counter(
                json.dumps(row, sort_keys=True) for row in observation["rows"]
            ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
                raise ValueError("fixed-value typed BAG mismatch")
            labels = emission.FIXED_NAMED_LABELS if named else emission.FIXED_LABELS
            tags = emission.FIXED_NAMED_TAGS if named else emission.FIXED_TAGS
            types = fixed_metadata(target, named=named)
            if (
                [m[0] for m in observation["metadata"]] != list(labels)
                or [m[1] for m in observation["metadata"]] != types
                or [c["logical_type"]["name"] for c in document["columns"]]
                != list(tags)
            ):
                raise ValueError("fixed-value positional physical/logical metadata")
            if target == "mysql" and any(
                len(m) != 9 or m[8] != 309
                for m, tag in zip(observation["metadata"], tags, strict=True)
                if tag == "Text"
            ):
                raise ValueError("fixed text result encoding metadata")
            continue
        if case["id"] == "P_native_identifiers":
            number = "7" if variant["variant"].startswith("plain") else "11"
            expected_rows = (
                []
                if variant["variant"].startswith("empty")
                else [[_integer(number)], [_integer(number)]]
            )
            if observation["rows"] != expected_rows:
                raise ValueError("native wrong-column regression")
            if [m[:2] for m in observation["metadata"]] != [
                ["id", 20 if target == "postgres" else 8]
            ]:
                raise ValueError("native identifier metadata")
            continue
        named = case["id"] in {"M_named_chain", "N_imported_chain"}
        expected_rows = (chain_rows if named else emission_rows)(
            target, empty=variant["variant"] == "empty"
        )
        if Counter(
            json.dumps(row, sort_keys=True) for row in observation["rows"]
        ) != Counter(json.dumps(row, sort_keys=True) for row in expected_rows):
            raise ValueError("emission typed row multiset mismatch")
        metadata = observation["metadata"]
        types = [25, 20, 16, 1700, 701] if target == "postgres" else [253, 8, 1, 246, 5]
        labels = emission.CHAIN_LABELS if named else emission.LABELS
        logical = emission.CHAIN_LOGICAL if named else emission.LOGICAL
        if named:
            types.append(20 if target == "postgres" else 8)
        if [m[0] for m in metadata] != list(labels) or [
            m[1] for m in metadata
        ] != types:
            raise ValueError("emission positional physical metadata mismatch")
        if [c["logical_type"]["name"] for c in document["columns"]] != list(
            logical
        ) or [c["label"] for c in document["columns"]] != list(labels):
            raise ValueError("emission positional logical metadata mismatch")
        if target == "postgres" and any(m[6] is not None for m in metadata):
            raise ValueError("unavailable nullability was invented")
    if next(observed, None) is not None:
        raise ValueError("extra submitted query observations")


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
        "api",
        "native",
    }
    if (
        set(observation) != keys
        or type(observation["sql"]) is not str
        or type(observation["parameters"]) is not list
        or type(observation["rows"]) is not list
    ):
        raise ValueError("malformed observation")
    if observation["native"] is not None:
        verify_native(observation)
    elif observation["api"] != observation["cursor_type"]:
        raise ValueError("cursor API identity")
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
    observation: dict[str, Any],
    target: str,
    identity: str,
    *,
    prepared: bool = False,
    transaction_control: bool = False,
) -> None:
    if transaction_control and (
        identity != "query"
        or observation["sql"] != "BEGIN"
        or observation["parameters"] != []
        or prepared
    ):
        raise ValueError("transaction purpose substitution")
    native = (
        target == "mysql"
        and not transaction_control
        and (identity == "query" or observation.get("api") == API)
    )
    if (
        observation.get("identity") != identity
        or observation.get("prepared")
        is not (prepared or target == "postgres" or native)
        or observation.get("buffering")
        != ("client_complete" if target == "postgres" else "unbuffered")
        or observation.get("diagnostics", {}).get("protocol")
        != ("postgres_notices" if target == "postgres" else "mysql_warnings")
    ):
        raise ValueError("observation identity or protocol substitution")
    if native:
        verify_native(observation)
    elif observation.get("native") is not None:
        raise ValueError("unexpected native route")
    elif observation.get("api") != (
        "psycopg.RawCursor"
        if target == "postgres"
        else "mysql.connector.cursor.MySQLCursorPrepared"
        if prepared
        else "mysql.connector.cursor.MySQLCursor"
    ):
        raise ValueError("cursor route identity")


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
    native = target == "mysql" and observation.get("api") == API
    # The native layer is not uniform: MySQL resolves a missing column while it
    # prepares the statement, but checks the CREATE DATABASE privilege only when
    # the prepared statement executes.
    at_prepare = native and not privilege
    stage = "prepare" if at_prepare else "execute"
    if (
        observation.get("status") != "failed"
        or observation.get("execute") != ("not_started" if at_prepare else "failed")
        or observation.get("close") != "success"
        or len(failures) != 1
        or failures[0].get("stage") != stage
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
    if case_id in emission.VARIANTS:
        check_emission_case(case, target)
    elif case_id in SLICE2_CASE_IDS[:3]:
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
        if case_id == "C_parameters" and observation.get("api") != (
            "psycopg.RawCursor" if target == "postgres" else API
        ):
            raise ValueError("wrong native parameter cursor")
        check_rows(observation, case_id, target)
    elif case_id == "Q_native_lifecycle":
        if (
            set(case)
            != {"id", "observations", "recovery", "session_before", "session_after"}
            or len(observations) != (5 if target == "postgres" else 8)
            or case.get("recovery") != "success"
            or type(case.get("session_before")) is not int
            or case["session_before"] <= 0
            or case["session_before"] != case.get("session_after")
        ):
            raise ValueError("native lifecycle denominator/session")
        sql = [
            "SELECT 1 AS v",
            "SELECT CAST($1 AS integer)"
            if target == "postgres"
            else "DO JSON_EXTRACT(?, '$')",
            "SELECT 2 AS v",
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')",
            "SELECT id FROM phase66_rows WHERE 1=0",
        ] + (
            ["SELECT ? AS v", "SELECT JSON_EXTRACT(?, '$')", "SELECT 3 AS v"]
            if target == "mysql"
            else []
        )
        if [o["sql"] for o in observations] != sql or [
            o["parameters"] for o in observations
        ] != [[], [_text("{")], [], [], []] + (
            [[], [_text("{")], []] if target == "mysql" else []
        ):
            raise ValueError("native lifecycle SQL/value substitution")
        for i in (0, 2, 4):
            check_complete(observations[i])
            check_identity(observations[i], target, "query")
        if (
            observations[0]["rows"] != [[_integer("1")]]
            or observations[2]["rows"] != [[_integer("2")]]
            or observations[4]["rows"] != []
            or observations[4]["metadata"][0][:2]
            != ["id", 20 if target == "postgres" else 8]
        ):
            raise ValueError("native recovery/empty result")
        failed = observations[1]
        check_identity(failed, target, "query", prepared=True)
        errors = failed["failures"]
        if (
            failed["status"] != "failed"
            or failed["execute"] != "failed"
            or failed["close"] != "success"
            or failed["diagnostics"]["complete"] is not True
            or len(errors) != 1
            or errors[0]["stage"] != "execute"
            or errors[0]["sqlstate"] != ("22P02" if target == "postgres" else "22032")
            or target == "mysql"
            and errors[0]["vendor_code"] != 3141
        ):
            raise ValueError("native allocated execution error")
        if target == "mysql" and (
            failed["diagnostics"]["total"] != 1
            or failed["diagnostics"]["details"][0]["vendor_code"] != 3141
        ):
            raise ValueError("native execution error diagnostics")
        warning = observations[3]
        check_complete(warning)
        check_identity(warning, target, "fixture_manager", prepared=target == "mysql")
        if (
            warning["fetch"] != "not_applicable"
            or len(warning["diagnostics"]["details"]) != 1
            or (
                warning["diagnostics"]["details"][0]["sqlstate"] != "42P07"
                if target == "postgres"
                else warning["diagnostics"]["details"][0]["vendor_code"] != 1265
            )
        ):
            raise ValueError("native warning/no-result loss")
        if target == "mysql":
            mismatch = observations[5]
            check_identity(mismatch, target, "query")
            if (
                mismatch["status"] != "failed"
                or mismatch["execute"] != "not_started"
                or len(mismatch["failures"]) != 1
                or mismatch["failures"][0]["stage"] != "parameter_count"
                or mismatch["failures"][0]["kind"] != "NATIVE_PARAMETER_COUNT"
            ):
                raise ValueError("empty-vector native arity guard")
            late = observations[6]
            check_identity(late, target, "query", prepared=True)
            if (
                late["status"] != "failed"
                or late["execute"] != "success"
                or late["fetch"] != "failed"
                or late["close"] != "success"
                or len(late["failures"]) != 1
                or late["failures"][0]["stage"] != "fetch"
                or late["failures"][0]["sqlstate"] != "22032"
                or late["failures"][0]["vendor_code"] != 3141
                or late["diagnostics"]["complete"] is not True
                or late["diagnostics"]["total"] != 1
                or late["diagnostics"]["details"][0]["vendor_code"] != 3141
            ):
                raise ValueError("native fetch error/diagnostic loss")
            check_complete(observations[7])
            check_identity(observations[7], target, "query")
            if observations[7]["rows"] != [[_integer("3")]]:
                raise ValueError("native recovery after fetch failure")
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
            check_identity(begin, target, "query", transaction_control=True)
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
