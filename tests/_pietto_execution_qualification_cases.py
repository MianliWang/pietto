"""Named S03 qualification/acceptance contracts. Workers never read these oracles."""

ROUTES = ("postgres_rows", "postgres_adbc", "mysql_rows")
MANIFEST = {
    "P1-postgres": "sealed component-view domain, composite K, fresh reopen, domain/role/version controls",
    "P1-mysql": "same provider contract via genuine native prepared statements",
    "P2-postgres_rows": "joint choice/peer/frame, PG GROUPS/exclusions, bounded nonempty/empty pages",
    "P2-postgres_adbc": "same difficult SQL through typed ADBC parameters, real Arrow metadata/EOF",
    "P2-mysql_rows": "ROWS/RANGE native frames and representations; PG-only features remain excluded",
}
RECIPES = ("scalar_frame_subquery", "frame_pairs_native_window")
SOURCE_ROWS = [
    [10, 1, 1, 10, "same", 9007199254740993, 0.0],
    [10, 2, 1, None, "same", 9007199254740993, 0.5],
    [10, 3, 2, 20, "same", -9007199254740993, 9007199254740992.0],
    [10, 4, 3, 30, "same", 104, -1.25],
    [20, 1, 1, 10, "same", 201, 0.0],
    [20, 2, 1, 40, "same", 202, 0.5],
    [20, 3, 2, None, "same", 9007199254740993, 9007199254740992.0],
    [20, 4, 3, 60, "same", 204, -1.25],
]
# part,lid,v,rn,lag_big,ntile,rank,dense,pct,cume,rows_first,range_last,nth5,next_last
# Fractions below are independently fixed IEEE754 oracle bits, not a SQL decoder.
JOINT_ROWS = [
    [
        10,
        1,
        10,
        1,
        999999999,
        1,
        1,
        1,
        "0000000000000000",
        "3fe0000000000000",
        10,
        40,
        None,
        None,
    ],
    [
        10,
        2,
        None,
        2,
        10,
        1,
        1,
        1,
        "0000000000000000",
        "3fe0000000000000",
        10,
        40,
        None,
        10,
    ],
    [
        20,
        2,
        40,
        4,
        10,
        2,
        1,
        1,
        "0000000000000000",
        "3fe0000000000000",
        10,
        40,
        None,
        20,
    ],
    [
        10,
        3,
        20,
        5,
        40,
        2,
        5,
        2,
        "3fe2492492492492",
        "3fe8000000000000",
        40,
        None,
        20,
        None,
    ],
    [
        20,
        3,
        None,
        6,
        20,
        2,
        5,
        2,
        "3fe2492492492492",
        "3fe8000000000000",
        20,
        None,
        20,
        30,
    ],
]
FRAME_ROWS = [
    [10, 1, 10, 40, None, None, 40],
    [10, 2, 10, 40, None, 10, 40],
    [20, 1, None, 40, None, 40, 40],
    [20, 2, 10, 40, None, 20, 40],
    [10, 3, 40, None, 20, None, None],
    [20, 3, 20, None, 20, 30, None],
    [10, 4, None, 60, 20, 60, 60],
    [20, 4, 30, 60, 20, None, 60],
]
GROUP_ROWS = [
    [10, 1, None, 10, None],
    [10, 2, 10, None, None],
    [20, 1, 10, 10, None],
    [20, 2, 10, 40, None],
    [10, 3, 10, 10, 10],
    [20, 3, 10, 10, 10],
    [10, 4, 20, 20, 20],
    [20, 4, 20, 20, 20],
]
JOINT_LABELS = (
    "part",
    "lid",
    "v",
    "rn",
    "lag_big",
    "bucket",
    "rnk",
    "dense",
    "pct",
    "cume",
    "rows_first",
    "range_last",
    "nth5",
    "next_last",
)
FRAME_LABELS = (
    "part",
    "lid",
    "rows_first",
    "range_last",
    "nth5",
    "next_last",
    "desc_last",
)
GROUP_LABELS = ("part", "lid", "exclude_current", "exclude_ties", "exclude_group")

NATIVE_FRAME_ROWS = [
    [10, 1, 1, 1, 2],
    [10, 2, 1, 1, 2],
    [20, 1, 1, 1, 2],
    [20, 2, 1, 1, 2],
    [10, 3, 1, 1, 3],
    [20, 3, 1, 1, 3],
    [10, 4, 2, 1, 3],
    [20, 4, 2, 1, 3],
]
NATIVE_GROUP_ROWS = [
    [10, 1, 1, 1, None],
    [10, 2, 1, 1, None],
    [20, 1, 1, 1, None],
    [20, 2, 1, 1, None],
    [10, 3, 1, 1, 1],
    [20, 3, 1, 1, 1],
    [10, 4, 2, 2, 2],
    [20, 4, 2, 2, 2],
]


def tagged(rows, *, floats=()):
    import struct

    return [
        [
            {"kind": "null"}
            if v is None
            else {
                "kind": "float",
                "bits": v if i in floats else struct.pack(">d", v).hex(),
            }
            if i in floats or type(v) is float
            else {"kind": "int", "value": str(v)}
            if type(v) is int
            else {"kind": "text", "value": v}
            for i, v in enumerate(row)
        ]
        for row in rows
    ]


def require(value, message):
    if not value:
        raise ValueError(message)


def check_query(q, route, *, sql=None, args=(), expected=None, labels=None):
    from copy import deepcopy

    values = tagged([list(args)])[0]
    require(q["parameters"] == values, "declared parameter correspondence")
    method = "cmd_stmt_execute" if route == "mysql_rows" else "execute"
    calls = [c for c in q["api_calls"] if c["method"] == method]
    require(len(calls) == 1 and calls[0]["values"] == values, "actual native arguments")
    submitted = (
        [c for c in q["api_calls"] if c["method"] == "cmd_stmt_prepare"]
        if route == "mysql_rows"
        else calls
    )
    require(
        len(submitted) == 1 and submitted[0]["sql"] == q["sql"], "actual native SQL"
    )
    if sql is not None:
        require(q["sql"] == sql, "frozen producing SQL")
    require(
        q["stage"] == "returned"
        and "error" not in q
        and q["statement_cleanup"] == "close_returned",
        "normal query and statement terminal",
    )
    require(
        q["source_terminal"]
        == {
            "postgres_rows": "empty_fetchmany",
            "postgres_adbc": "arrow_StopIteration",
            "mysql_rows": "native_rowset_eof",
        }[route],
        "native EOF",
    )
    if expected is not None:
        require(q["actual"] == deepcopy(expected), "original values/multiplicity")
    if labels is not None:
        require(
            tuple(x[0] for x in q["metadata"]) == tuple(labels),
            "original positional metadata",
        )


def checked_process(record):
    require(
        record["exit"] == 0 and record["reaped"] and record["stderr_bytes"] == 0,
        "child cleanup",
    )
    return record["data"]


def check_p1(target, record):
    route = target + "_rows"
    a = checked_process(record["initial"])
    b = checked_process(record["reopen"])
    require(
        record["initial"]["pid"] != record["reopen"]["pid"]
        and a["session_id"] != b["session_id"],
        "fresh process and session",
    )
    require(
        a["registry"]["actual"] == b["registry"]["actual"]
        and a["definition"]["actual"] == b["definition"]["actual"],
        "same retained provider and actual view definition",
    )
    require(
        "UNION ALL" in a["definition"]["actual"][0][0]["value"].upper(),
        "complete component view",
    )
    expected = tagged(SOURCE_ROWS)
    require(
        a["rows"]["metadata"][0][1] == (23 if target == "postgres" else 8),
        "independent original token metadata",
    )
    for item in (a, b):
        check_query(item["uniqueness"], route, expected=[])
        check_query(item["rows"], route)
        require(
            sorted(
                item["rows"]["actual"],
                key=lambda row: (int(row[0]["value"]), int(row[1]["value"])),
            )
            == expected,
            "K to exact source payload",
        )
        check_query(
            item["local_key"], route, expected=tagged([[1, 2], [2, 2], [3, 2], [4, 2]])
        )
        pairs = [
            [p, local, q, local]
            for p in (10, 20)
            for local in (1, 2, 3, 4)
            for q in (10, 20)
        ]
        check_query(item["repeated"], route, expected=tagged(pairs))
        check_query(
            item["signed_zero"],
            route,
            expected=[
                [
                    {"kind": "float", "bits": "0000000000000000"},
                    {"kind": "float", "bits": "8000000000000000"},
                ]
            ],
        )
    require(
        a["rows"]["sql"].endswith("ORDER BY part,lid")
        and b["rows"]["sql"].endswith("ORDER BY lid DESC,part DESC"),
        "actual alternate requested access order",
    )
    require(
        a["rows"]["actual"] != b["rows"]["actual"], "observed changed delivery order"
    )
    for name, reason in (
        ("expiry", "provider version or retention"),
        ("replacement", "provider version or retention"),
        ("visibility", "view domain"),
        ("token_mismatch", "token domain"),
        ("role", "role context"),
    ):
        denied = checked_process(record[name])
        if name == "expiry":
            require(
                denied["registry"]["actual"][0][2] == {"kind": "int", "value": "0"},
                "actual source expiry",
            )
        elif name == "replacement":
            require(
                denied["registry"]["actual"][0][1] == {"kind": "text", "value": "v2"},
                "actual source replacement",
            )
        elif name == "visibility":
            definition = denied["definition"]["actual"][0][0]["value"].lower()
            require(
                "p68s3_left" in definition and "p68s3_right" not in definition,
                "actual visibility domain change",
            )
        elif name == "token_mismatch":
            require(
                denied["uniqueness"]["actual"]
                == tagged([[10, 1, 2], [10, 2, 2], [10, 3, 2], [10, 4, 2]]),
                "complete-domain token collision",
            )
        else:
            require(
                "p68s3_role" in str(denied["session"]["actual"][0][:2]),
                "actual role context change",
            )
        require(
            denied.get("rejected") == reason and "rows" not in denied,
            "source admission refuses " + name,
        )
    return {
        "K": "(component tag, existing component primary key)",
        "source_rows": 8,
        "repeated_use_rows": 16,
        "all_domain_checked": True,
        "reopen_correspondence": True,
    }


def check_p2(route, record):
    body = checked_process(record)
    names = (
        ("joint", "frames", "native_frames", "groups", "native_groups")
        if route != "mysql_rows"
        else ("joint", "frames", "native_frames")
    )
    require(
        set(body["cases"])
        == {c + "/" + v for c in names for v in ("full", "prefix", "empty")},
        "complete case denominator",
    )
    codes_pg = {
        "joint": [23, 23, 21, 20, 23, 23, 20, 20, 701, 701, 21, 21, 21, 21],
        "frames": [23, 23, 21, 21, 21, 21, 21],
        "groups": [23, 23, 21, 21, 21],
        "native_frames": [23, 23, 21, 21, 21],
        "native_groups": [23, 23, 21, 21, 21],
    }
    codes_my = {
        "joint": [8, 3, 2, 8, 8, 8, 8, 8, 5, 5, 3, 3, 3, 3],
        "frames": [8, 3, 3, 3, 3, 3, 3],
        "groups": [],
        "native_frames": [8, 3, 3, 3, 3],
    }
    pg_arrow = {23: "int32", 21: "int16", 20: "int64", 701: "double"}
    for case in names:
        expected = tagged(
            {
                "joint": JOINT_ROWS,
                "frames": FRAME_ROWS,
                "groups": GROUP_ROWS,
                "native_frames": NATIVE_FRAME_ROWS,
                "native_groups": NATIVE_GROUP_ROWS,
            }[case],
            floats=(8, 9) if case == "joint" else (),
        )
        labels = {
            "joint": JOINT_LABELS,
            "frames": FRAME_LABELS,
            "groups": GROUP_LABELS,
            "native_frames": ("part", "lid", "narrow", "wide", "descending"),
            "native_groups": (
                "part",
                "lid",
                "original_current",
                "original_ties",
                "original_group",
            ),
        }[case]
        for variant, after, size in (
            ("full", 0, 16),
            ("prefix", 0, 2),
            ("empty", 99, 2),
        ):
            q = body["cases"][case + "/" + variant]
            sql = q["sql"]
            require(
                "DENSE_RANK() OVER(ORDER BY k) AS g" in sql
                and "ROW_NUMBER() OVER(ORDER BY k,part,lid) AS u" in sql,
                "separate original peers and chosen order",
            )
            require(
                "FROM e WHERE page_position>" in sql
                and "ORDER BY page_position LIMIT" in sql,
                "page after complete operators",
            )
            if case in ("joint", "frames"):
                for fragment in (
                    "RANK() OVER(ORDER BY x.k) AS rnk",
                    "CUME_DIST() OVER(ORDER BY x.k) AS cume",
                    "z.g<=x.g",
                    "z.k BETWEEN x.k AND x.k+1",
                    "NTH_VALUE(z.v,5)",
                ):
                    require(
                        fragment in sql, "original frame and joint choice operation"
                    )
                require(
                    "ROWS BETWEEN 1 FOLLOWING AND 1 FOLLOWING" in sql,
                    "empty frame operation",
                )
            if case == "joint":
                require(
                    "WHERE rn<=7 AND (hidden_next IS NULL OR hidden_next<>40) ORDER BY u LIMIT 5"
                    in sql,
                    "hidden QUALIFY and original LIMIT before page",
                )
            if case == "groups":
                require(
                    "z.g BETWEEN x.g-1 AND x.g" in sql
                    and "NOT(z.part=x.part AND z.lid=x.lid)" in sql
                    and "z.g<>x.g" in sql,
                    "peer-preserving exclusions",
                )
            if case == "native_frames":
                require(
                    "RANGE BETWEEN 40000 PRECEDING AND CURRENT ROW" in sql
                    and "ORDER BY k DESC RANGE BETWEEN 1 PRECEDING AND CURRENT ROW"
                    in sql,
                    "native exact offset RANGE anchor",
                )
            if case == "native_groups":
                require(
                    all(
                        "EXCLUDE " + x in sql for x in ("CURRENT ROW", "TIES", "GROUP")
                    ),
                    "native PG exclusions",
                )
            check_query(
                q,
                route,
                args=(1, after, size),
                expected=expected
                if variant == "full"
                else expected[:2]
                if variant == "prefix"
                else [],
                labels=labels,
            )
            wanted = (
                codes_my[case]
                if route == "mysql_rows"
                else [pg_arrow[x] for x in codes_pg[case]]
                if route == "postgres_adbc"
                else codes_pg[case]
            )
            require(
                [col[1] for col in q["metadata"]] == wanted,
                "actual physical widths " + route + "/" + case + "/" + variant,
            )
            require(
                "hidden_next" not in labels
                and q["sql"].endswith(
                    "LIMIT ?" if route == "mysql_rows" else "LIMIT $3"
                ),
                "hidden output/page boundary",
            )
        require(
            body["cases"][case + "/full"]["metadata"]
            == body["cases"][case + "/empty"]["metadata"],
            "empty schema does not depend on first row",
        )
    return {"native_rows_and_metadata": "MATCH", "cases": list(body["cases"])}


def verify_qualification(report):
    require(
        report["complete"] is True
        and report["location"] == "local"
        and len(report["execution_tree"]) == 40,
        "complete producing context",
    )
    require(
        report["metadata_preflight"]["type"] == "int16"
        and report["metadata_preflight"]["nullable"] is True,
        "actual metadata serializer",
    )
    require(
        set(report["targets"]) == {"postgres", "mysql"}, "complete target denominator"
    )
    results = {}
    for target, record in report["targets"].items():
        require(
            set(record["p2"])
            == (
                {"postgres_rows", "postgres_adbc"}
                if target == "postgres"
                else {"mysql_rows"}
            ),
            "complete route denominator",
        )
        require(
            record["cleanup"]["status"] == "success"
            and len(record["fixture"]["immutability_controls"]) == 2,
            "provider enforcement and cleanup",
        )
        require(
            ("18.6" if target == "postgres" else "8.4.12")
            in record["server_version"][0][0],
            "pinned actual target",
        )
        results["P1-" + target] = check_p1(target, record["p1"])
        for route, observed in record["p2"].items():
            results["P2-" + route] = check_p2(route, observed)
    return results


PRODUCT_ROWS = [
    [9007199254740993, 10],
    [9007199254740993, None],
    [-9007199254740993, 20],
    [104, 30],
    [201, 10],
    [202, 40],
    [9007199254740993, None],
    [204, 60],
]
PRODUCT_TERMINALS = {
    "normal": ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED", 8, None),
    "installed_normal": ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED", 8, None),
    "serializable": ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED", 8, None),
    "empty": ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED", 0, None),
    "early_close": ("EARLY_CLOSE", "ROLLBACK_ACK", "INCOMPLETE", "CLOSED", 2, None),
    "row_limit": ("INCOMPLETE", "ROLLBACK_ACK", "FAILED", "CLOSED", 2, "check"),
    "late_check": ("INCOMPLETE", "ROLLBACK_ACK", "FAILED", "CLOSED", 2, "check"),
    "consumer_error": (
        "EARLY_CLOSE",
        "ROLLBACK_ACK",
        "FAILED",
        "CLOSED",
        2,
        "consumer",
    ),
    "pre_cancel": ("FAILED", "NOT_STARTED", "FAILED", "CLOSED", 0, "admission"),
    "blocked_cancel": ("FAILED", "ROLLBACK_ACK", "FAILED", "CLOSED", 0, "execute"),
    "deadline": ("FAILED", "ROLLBACK_ACK", "FAILED", "CLOSED", 0, "execute"),
    "late_cancel": ("EOF", "COMMIT_ACK", "COMPLETE", "CLOSED", 8, None),
    "cleanup": ("EOF", "COMMIT_ACK", "FAILED", "FAILED", 8, "finalization"),
    "source_error": ("FAILED", "ROLLBACK_ACK", "FAILED", "CLOSED", 0, "execute"),
    "source_error_cleanup": (
        "FAILED",
        "ROLLBACK_ACK",
        "FAILED",
        "FAILED",
        0,
        "execute",
    ),
    "cap_expired": ("FAILED", "ROLLBACK_ACK", "FAILED", "CLOSED", 0, "admission"),
    "cap_token": ("FAILED", "ROLLBACK_ACK", "FAILED", "CLOSED", 0, "admission"),
}


def check_product_case(name, record):
    import json
    from collections import Counter

    body = checked_process(record)
    out = body["outcome"]
    expected = PRODUCT_TERMINALS[name]
    require(
        tuple(out[k] for k in ("source", "transaction", "delivery", "cleanup", "rows"))
        == expected[:5],
        "separate product terminals " + name,
    )
    require(
        (None if out["primary"] is None else out["primary"]["phase"]) == expected[5],
        "primary failure phase",
    )
    require(
        body["control_joined"] and record["remaining_session"] == [],
        "owned control/session cleanup",
    )
    require(
        body["compiled_verified"] and body["native_uses"] == 0, "real verified producer"
    )
    relation = (
        "p68s3_empty"
        if name == "empty"
        else "p68s3_fault"
        if name in ("source_error", "source_error_cleanup")
        else "p68s3_input"
    )
    sql = f'SELECT "s0"."hidden" AS "renamed", "s0"."v" AS "other" FROM "public"."{relation}" AS "s0"'
    require(body["sql"] == sql, "original compiler SQL")
    refused = name in ("pre_cancel", "cap_expired", "cap_token")
    require(
        body["submissions"]
        == ([] if refused else [{"sql": sql, "arguments": [], "prepare": True}]),
        "native compiler submission",
    )
    count = expected[4]
    actual = Counter(json.dumps(row, sort_keys=True) for row in body["actual"])
    oracle = Counter(json.dumps(row, sort_keys=True) for row in tagged(PRODUCT_ROWS))
    require(
        sum(actual.values()) == count and actual <= oracle,
        "checked BAG values and multiplicity",
    )
    if count == 8:
        require(actual == oracle, "complete checked BAG")
    require(out["batches"] == count // 2, "exact-boundary batches")
    require(
        bool(out["cleanup_failures"]) == (expected[3] == "FAILED"),
        "cleanup does not erase primary",
    )
    if name != "pre_cancel":
        require(
            body["context"]
            == [
                "pietto_query",
                "serializable" if name == "serializable" else "repeatable read",
                "on",
                "UTF8",
                "pg_catalog",
            ],
            "actual readonly context",
        )
    if count or name == "empty":
        require(
            body["metadata"] == [["renamed", 20, None], ["other", 21, None]],
            "actual native representation",
        )
        schema = [["renamed", "int64", False], ["other", "int16", True]]
        require(
            body["bound_schema"] == schema
            and body["consumer_schemas"] == [schema] * (count // 2),
            "checked Arrow schema including empty",
        )
        require(
            body["native_buffered_rows"] == (0 if name == "empty" else 8),
            "buffered native boundary",
        )
    if name in ("normal", "installed_normal", "serializable"):
        admission = body["source_admission"]
        require(
            admission is not None
            and admission["version"] == "v1"
            and admission["token_type_oids"] == [23, 23]
            and admission["session"] == body["session_id"],
            "source admission/session correspondence",
        )
    for value in body["origins"].values():
        require(
            ("/site-packages/pietto/" if name == "installed_normal" else "/src/pietto/")
            in value,
            "actual source/installed origin",
        )
    if name in ("blocked_cancel", "deadline"):
        control = record["manager_control"]
        require(
            len(control) == 1
            and control[0]["observation"]
            == [[body["session_id"], "active", "Lock", sql]],
            "actual blocked owned execute",
        )
        require(out["primary"]["sqlstate"] == "57014", "native control failure")
    if name == "blocked_cancel":
        require(
            out["cancel_requested"] and out["cancel_sent"] and out["cancel_observed"],
            "observed explicit cancellation",
        )
    if name == "deadline":
        # Native statement timeout and the owned timer can race; neither is EOF.
        require(body["caught"]["sqlstate"] == "57014", "native deadline result")
    if name == "pre_cancel":
        require(
            body["session_id"] is None
            and not body["control_events"]
            and out["cancel_requested"]
            and not out["cancel_sent"],
            "pre-cancel no connection",
        )
    if name == "late_cancel":
        require(
            body["late_cancel"]
            == {"requested": True, "sent": False, "observed": False, "late": True},
            "late cancellation",
        )
    if name.startswith("source_error"):
        require(
            out["primary"]["sqlstate"] == "42P01"
            and record["manager_control"]
            == [{"event": "owned_fault_view_removed", "session": body["session_id"]}],
            "real source failure",
        )
    if name.startswith("cap_"):
        require(
            body["caught"]["category"]
            == (
                "SOURCE_VERSION_OR_RETENTION"
                if name == "cap_expired"
                else "SOURCE_TOKEN_NOT_INJECTIVE"
            ),
            "source capability refusal",
        )
    require(
        body["injection"]
        == (
            name
            if name
            in ("late_check", "cleanup", "source_error_cleanup", "consumer_error")
            else None
        ),
        "real versus injected",
    )


def verify_product(report):
    require(
        report["complete"] and report["location"] == "local",
        "product observation context",
    )
    target = report["targets"]["postgres"]
    require(target["cleanup"]["status"] == "success", "owned native cleanup")
    cases = target["product"]
    require(set(cases) == set(PRODUCT_TERMINALS), "complete product family")
    for name, record in cases.items():
        check_product_case(name, record)
    sessions = [
        r["data"]["session_id"]
        for r in cases.values()
        if r["data"]["session_id"] is not None
    ]
    require(len(sessions) == len(set(sessions)), "fresh exclusive sessions")
    return {"product": "MATCH", "cases": list(cases)}
