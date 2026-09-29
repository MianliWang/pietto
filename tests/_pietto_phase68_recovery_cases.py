"""S02 named manifest and original-value oracle, never imported by workers."""

ROUTES = ("postgres_rows", "postgres_adbc", "mysql_rows")
CUTS = ("partial", "fsync_failure", "orphan", "uncommitted", "committed")
MANIFEST = {
    **{
        r: {
            "purpose": "uncaptured same-version suffix and joined lost-ACK sink",
            "profile": r,
            "inputs": "manager sealed v1, prefix page2, fresh suffix page3",
            "relation": "ordered six occurrences, duplicates and NULL exact",
            "checker": "check_source",
            "terminal": "extractor SIGKILL/reap, old session absent, recovery EOF, sink reconcile, target cleanup",
        }
        for r in ROUTES
    },
    "snapshot": {
        "purpose": "exporter lifetime negative",
        "profile": "postgres",
        "inputs": "ended exporter and importer",
        "relation": "new import rejects",
        "checker": "check_controls",
        "terminal": "rollback/close",
    },
    **{
        t + "_mutable": {
            "purpose": "ordinary transaction is a new view",
            "profile": t,
            "inputs": "manager update10to20",
            "relation": "new transaction sees20",
            "checker": "check_controls",
            "terminal": "read transaction commit/close",
        }
        for t in ("postgres", "mysql")
    },
    **{
        "store_" + cut: {
            "purpose": "crash boundary " + cut,
            "profile": "disk SQLite WAL/FULL",
            "inputs": "one checked chunk and named cut",
            "relation": "committed iff metadata commit returned",
            "checker": "check_store",
            "terminal": "owned child reaped and new process reopen",
        }
        for cut in CUTS
    },
    "store_guards": {
        "purpose": "missing/corrupt/binding/canceled refusal",
        "profile": "disk WAL/FULL",
        "inputs": "closed-store defects",
        "relation": "reopen rejects",
        "checker": "check_store",
        "terminal": "closed",
    },
    "holes": {
        "purpose": "persisted positions1,3 and ACK gap",
        "profile": "disk WAL/FULL",
        "inputs": "separate chunk/effect commits",
        "relation": "frontier1",
        "checker": "check_store",
        "terminal": "fresh process reopen",
    },
    "isolation": {
        "purpose": "two jobs and reader/writer",
        "profile": "separate WAL/FULL connections",
        "inputs": "barrier outside write transaction",
        "relation": "other job commits while wait and reader retains view",
        "checker": "check_store",
        "terminal": "barrier released/reaped",
    },
    "sink_guards": {
        "purpose": "conflict and promise boundaries",
        "profile": "separate disk sink",
        "inputs": "same key/different payload, namespace/epoch/expiry",
        "relation": "reject; equal distinct occurrences retained",
        "checker": "check_sink",
        "terminal": "fresh query",
    },
    "algorithms": {
        "purpose": "duplicate-key and global operator counterexamples",
        "profile": "algorithm only",
        "inputs": "literal repeated keys and cross-chunk SUM",
        "relation": "naive loses duplicate/global sum differs",
        "checker": "check_algorithms",
        "terminal": "finite",
    },
}

# Independently authored literal original values; fixture SQL is separate.
ORIGINAL = [
    [1, 7, "same", 9007199254740993],
    [2, 7, "same", 9007199254740993],
    [3, 7, "same", 9007199254740993],
    [4, 9, None, -11],
    [5, 9, "雪' ? $1", 0],
    [6, 12, "last", 42],
]


def require(condition, purpose):
    if not condition:
        raise ValueError(purpose)


def process(record, killed=False):
    require(
        record["reaped"] is True and record["exit"] == (-9 if killed else 0),
        "process terminal/reap",
    )
    require(record["killed_at_barrier"] is killed, "crash cut barrier")
    require(record["elapsed_seconds"] >= 0, "measured child timing")
    return record["data"]


def profiles(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("profile", "writer_profile", "ack_profile"):
                require(
                    item["journal"] == "wal" and item["synchronous"] == 2,
                    "effective connection profile",
                )
            profiles(item)
    elif isinstance(value, list):
        for item in value:
            profiles(item)


def literals(rows):
    return [
        [
            {"kind": "null"}
            if value is None
            else {"kind": "int", "value": str(value)}
            if type(value) is int
            else {"kind": "text", "value": value}
            for value in row
        ]
        for row in rows
    ]


def submission(query, sql, values, route):
    expected = literals([values])[0]
    require(
        query["options"]
        == (
            {"use_copy": True, "batch_size_hint_bytes": 1}
            if route == "postgres_adbc"
            else {}
        ),
        "selected driver options",
    )
    require(
        query["sql"] == sql and query["parameters"] == expected, "declared operation"
    )
    method = "cmd_stmt_execute" if route == "mysql_rows" else "execute"
    actual = [c for c in query["api_calls"] if c["method"] == method]
    require(
        len(actual) == 1 and actual[0]["values"] == expected,
        "actual submitted parameters",
    )
    if route == "mysql_rows":
        prepare = [c for c in query["api_calls"] if c["method"] == "cmd_stmt_prepare"]
        require(
            len(prepare) == 1 and prepare[0]["sql"] == sql, "actual native prepared SQL"
        )
        require(
            query["native"]["terminal"]["kind"] == "rowset_eof",
            "native result termination",
        )
    else:
        require(actual[0]["sql"] == sql, "actual submitted SQL")
    require(
        query["stage"] == "returned"
        and "error" not in query
        and query["statement_cleanup"] == "close_returned",
        "query/statement terminal",
    )
    require(
        query["source_terminal"]
        == {
            "postgres_rows": "empty_fetchmany",
            "postgres_adbc": "arrow_StopIteration",
            "mysql_rows": "native_rowset_eof",
        }[route],
        "route-specific EOF",
    )


def check_source(route, record):
    require(
        0 < record["owned_payload_bytes"] <= 64 * 1024 * 1024, "bounded owned payload"
    )
    prefix = process(record["prefix"], True)
    recovery = process(record["recovery"])
    require(
        prefix["pid"] != recovery["pid"]
        and prefix["session_id"] != recovery["session_id"],
        "fresh extractor and native session",
    )
    require(
        record["old_session_absent"]["actual"] == []
        and record["old_session_absent"]["session"] == prefix["session_id"],
        "old source session ended",
    )
    require(
        record["recovery_session_absent"]["actual"] == [], "recovery connection closed"
    )
    require(
        prefix["reopened"]["rows"] == []
        and recovery["reopened"]["rows"] == ORIGINAL[:2],
        "only prefix captured before restart",
    )
    require(
        recovery["reopened"]["frontier"] == 2,
        "restart from committed occurrence, not batch",
    )
    for attempt in (prefix, recovery):
        session = attempt["session"]["actual"][0]
        require(
            session[0]["value"].startswith("pietto_query")
            and session[1]["value"] == str(attempt["session_id"]),
            "reauthorized read identity",
        )
        vq = attempt["version_query"]
        sql = "SELECT token, retained FROM p68r_versions WHERE version_id = " + (
            "?" if route == "mysql_rows" else "$1"
        )
        submission(vq, sql, [1], route)
        require(
            vq["actual"] == literals([[record["binding"]["token"], 1]]),
            "same retained explicit version",
        )
    require(
        len(prefix["pages"]) == 1 and len(recovery["pages"]) == 3,
        "bounded prefix and changed page-size suffix",
    )
    combined = []
    for page, after, limit, expected in zip(
        prefix["pages"] + recovery["pages"],
        (0, 2, 5, 6),
        (2, 3, 3, 3),
        (ORIGINAL[:2], ORIGINAL[2:5], ORIGINAL[5:], []),
        strict=True,
    ):
        markers = ("?", "?", "?") if route == "mysql_rows" else ("$1", "$2", "$3")
        sql = (
            "SELECT occurrence_id, visible_key, payload, exact_value FROM p68r_rows WHERE version_id = "
            + markers[0]
            + " AND occurrence_id > "
            + markers[1]
            + " ORDER BY occurrence_id LIMIT "
            + markers[2]
        )
        submission(page["query"], sql, [1, after, limit], route)
        require(page["after"] == after and page["limit"] == limit, "page progress")
        require(
            page["query"]["actual"] == literals(expected),
            "exact original values/order/multiplicity",
        )
        require(
            [c[0] for c in page["query"]["metadata"]]
            == ["occurrence_id", "visible_key", "payload", "exact_value"],
            "actual metadata correspondence",
        )
        if expected:
            events = page["checkpoint"]["events"]
            require(
                events
                == [
                    "file_fsync_returned",
                    "namespace_fsync_returned",
                    "metadata_insert_uncommitted",
                    "metadata_commit_returned",
                    "checkpoint_ack",
                ],
                "durable checkpoint ordering",
            )
        combined.extend(page["query"]["actual"])
    require(
        combined == literals(ORIGINAL)
        and recovery["source_terminal"] == "empty_bounded_query_after_all_pages",
        "complete recovered occurrence coverage",
    )
    require(process(record["saved"])["rows"] == ORIGINAL, "saved result values")
    lost = process(record["lost_ack"], True)
    require(
        lost["position"] == 1 and lost["commit"] and not lost["reconciled"],
        "actual sink commit before lost ACK",
    )
    require(
        process(record["before_reconcile"])["acks"] == [],
        "job has not recorded sink ACK",
    )
    require(
        process(record["sink_after_loss"])["effects"] == ORIGINAL[:1],
        "separate process observes committed effect",
    )
    consumer = process(record["consumer"])
    require(
        consumer["job"]["ack_frontier"] == 6
        and consumer["job"]["acks"] == list(range(1, 7)),
        "ACK coverage",
    )
    require(
        [r["position"] for r in consumer["receipts"]] == list(range(1, 7))
        and [r["reconciled"] for r in consumer["receipts"]]
        == [True, False, False, False, False, False],
        "same identity reconciliation without duplicate effect",
    )
    require(
        all(r["commit"] for r in consumer["receipts"]), "effect commits before ACKs"
    )
    require(
        process(record["sink_final"])["effects"] == ORIGINAL,
        "independent sink multiplicity and exact values",
    )
    for key in ("expired", "replacement"):
        rejected = process(record[key])
        sql = "SELECT token, retained FROM p68r_versions WHERE version_id = " + (
            "?" if route == "mysql_rows" else "$1"
        )
        submission(rejected["version_query"], sql, [1], route)
        require(
            rejected["version_query"]["actual"]
            == literals(
                [
                    [record["binding"]["token"], 0]
                    if key == "expired"
                    else ["replacement", 1]
                ]
            ),
            "actual source refusal prerequisite",
        )
        require(
            rejected.get("rejected") == "source version absent, replaced or expired"
            and "pages" not in rejected,
            "source contract refusal before new reads",
        )


def check_store(records):
    full = [
        "file_fsync_returned",
        "namespace_fsync_returned",
        "metadata_insert_uncommitted",
        "metadata_commit_returned",
    ]
    for cut in CUTS:
        record = records["store_" + cut]
        data = process(record["producer"], cut != "fsync_failure")
        reopened = process(record["reopen"])
        require(
            record["prior_checkpoint"]["events"] == full + ["checkpoint_ack"],
            "prior committed checkpoint remains usable",
        )
        require(
            reopened["frontier"] == (2 if cut == "committed" else 1),
            "committed frontier on fresh reopen",
        )
        require(
            reopened["rows"] == (ORIGINAL[:2] if cut == "committed" else ORIGINAL[:1]),
            "actual persisted chunk correspondence",
        )
        if cut == "fsync_failure":
            require(
                data
                == {"injected": "injected file fsync failure", "checkpoint_ack": False},
                "explicit sync injection",
            )
        else:
            require(
                data["cut"] == cut
                and data["events"]
                == {
                    "partial": ["partial_write"],
                    "orphan": full[:2],
                    "uncommitted": full[:3],
                    "committed": full,
                }[cut],
                "acknowledged exact crash cut",
            )
            require(
                data["profile"]["in_transaction"] is (cut == "uncommitted"),
                "crash transaction state",
            )
        if cut in ("orphan", "uncommitted"):
            require(
                "chunk-2-2.json" in record["files"]
                and len(reopened["references"]) == 1,
                "orphan must not advance job checkpoint",
            )
    require(
        set(records["store_guards"])
        == {
            "missing",
            "corrupt",
            "binding",
            "version",
            "namespace",
            "epoch",
            "expiry",
            "canceled",
        },
        "store defect inventory",
    )
    for defect, record in records["store_guards"].items():
        reason = process(record).get("rejected", "")
        require(
            reason.startswith("FileNotFoundError:")
            if defect == "missing"
            else reason
            == (
                "ValueError: changed chunk"
                if defect == "corrupt"
                else "ValueError: binding, cancellation or retention mismatch"
            ),
            "invalid recovery refused for intended reason",
        )
    holes = process(records["holes"]["reopen"])
    require(
        holes["frontier"] == holes["ack_frontier"] == 1
        and holes["acks"] == [1, 3]
        and holes["rows"] == [ORIGINAL[0], ORIGINAL[2]],
        "persisted gap cannot advance either frontier",
    )
    require(
        process(records["holes"]["sink"])["effects"] == [ORIGINAL[0], ORIGINAL[2]],
        "equal visible occurrences remain separate effects",
    )
    isolation = records["isolation"]
    process(isolation["waiter"])
    history = isolation["history"]
    require(
        not history["waiting"]["profile"]["in_transaction"],
        "source/consumer wait outside metadata write transaction",
    )
    require(
        (
            history["reader_before"],
            history["reader_same_view"],
            history["reader_new_view"],
        )
        == ("active", "active", "complete"),
        "real reader/writer interleaving",
    )
    require(process(isolation["original_job"])["frontier"] == 1, "two-job isolation")
    require(
        set(records["sink_guards"]) == {"payload", "namespace", "epoch", "expiry"},
        "sink defect inventory",
    )
    for key, record in records["sink_guards"].items():
        require(
            process(record).get("rejected")
            == (
                "effect payload conflict"
                if key == "payload"
                else "sink promise mismatch or expiry"
            ),
            "cooperative promise rejection",
        )
    a = records["algorithms"]
    require(
        a["input"] == [[1, 7], [2, 7], [3, 9]]
        and a["strict_key_suffix"] == [[3, 9]]
        and a["occurrence_suffix"] == [[2, 7], [3, 9]],
        "duplicate-key loss counterexample",
    )
    require(
        a["global_input"] == [2, 3, 5]
        and a["whole_sum"] == [10]
        and a["concatenated_partial_sum"] == [5, 5],
        "global operator counterexample",
    )
    require(
        a["unknown"]
        == {
            "saved_eof": True,
            "remote_commit_observed": False,
            "transaction_terminal": "UNKNOWN",
        },
        "EOF cannot settle unobserved remote commit",
    )


def verify(report):
    # Deliberately data-only: no DB, imports of drivers, or extractor decoder.
    records = report["records"]
    family = report["family"]
    keys = set(MANIFEST)
    if family == "store":
        keys -= set(ROUTES) | {"snapshot", "postgres_mutable", "mysql_mutable"}
    elif family in ("postgres", "mysql"):
        keys = (
            {"postgres_rows", "postgres_adbc", "snapshot", "postgres_mutable"}
            if family == "postgres"
            else {"mysql_rows", "mysql_mutable"}
        )
    require(
        report["complete"] is True
        and set(records) == keys
        and report["location"] == "local",
        "complete named manifest",
    )
    require(len(report["execution_tree"]) == 40, "actual execution tree")
    require(
        report["connections"]
        and all(
            row["profile"]
            == {"journal": "wal", "synchronous": 2, "in_transaction": False}
            for row in report["connections"]
        ),
        "every participating SQLite connection profile",
    )
    profiles(report)
    meta = report["metadata"]
    require(
        meta["sqlite"]["source_id"]
        == "2026-05-05 10:34:17 c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9"
        and meta["sqlite"]["version"] == "3.53.1",
        "selected fixed-build profile identity",
    )
    require(
        meta["build"] == "20260602" and meta["sqlite"]["module_origin"] == "built-in",
        "actual runtime build provenance",
    )
    require(
        meta["mount"]["filesystems"][0]["fstype"] == "ext4",
        "selected observed filesystem",
    )
    require(
        meta["arrow"]["values"] == [9007199254740993, None]
        and meta["arrow"]["type"] == "int64",
        "real metadata serialization",
    )
    for name, version in {
        "psycopg": "3.3.5",
        "psycopg-binary": "3.3.5",
        "mysql-connector-python": "26.7.0",
        "pyarrow": "25.0.1",
        "adbc-driver-manager": "1.12.0",
        "adbc-driver-postgresql": "1.12.0",
    }.items():
        require(meta["runtime"]["versions"][name] == version, "pinned runtime")
    for route in ROUTES:
        if route in records:
            check_source(route, records[route])
    if "store_partial" in records:
        check_store(records)
    for target in ("postgres", "mysql"):
        if target + "_mutable" in records:
            value = records[target + "_mutable"]
            route = target + "_rows"
            require(
                value["before"]["data"]["session_id"]
                != value["after"]["data"]["session_id"],
                "fresh ordinary transaction session",
            )
            for key, expected in (("before", 10), ("after", 20)):
                data = process(value[key])
                submission(data["query"], "SELECT value FROM p68r_mutable", [], route)
                require(
                    data["query"]["actual"] == literals([[expected]])
                    and data["controls"][-1] == {"sql": "COMMIT", "returned": True},
                    "new ordinary transaction sees changed mutable source",
                )
            resource = report["resources"][target]
            require(
                ("18.6" if target == "postgres" else "8.4.12")
                in resource["server_version"][0][0],
                "actual pinned source server version",
            )
            require(
                resource["cleanup"]["status"] == "success"
                and resource["fixture"]["manager_update_rejected"],
                "immutable fixture/target cleanup",
            )
            require(
                resource["new_version_sql"]
                == "INSERT INTO p68r_versions VALUES (2,'different-version',1)",
                "different version exists during recovery",
            )
    if "snapshot" in records:
        snap = records["snapshot"]
        process(snap["exporter"])
        require(snap["exporter_absent"]["actual"] == [], "exporter ended before import")
        imported = process(snap["importer"])
        failure = imported["query"]
        snapshot_sql = (
            "SET TRANSACTION SNAPSHOT '" + snap["exporter"]["data"]["snapshot"] + "'"
        )
        require(
            failure["sql"] == snapshot_sql
            and failure["api_calls"]
            == [{"method": "execute", "sql": snapshot_sql, "values": []}],
            "actual snapshot import operation",
        )
        require(
            imported["controls"]
            == [
                {
                    "sql": "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY",
                    "returned": True,
                },
                {"sql": "ROLLBACK", "returned": True},
            ],
            "import transaction prerequisites",
        )
        require(
            snap["exporter_absent"]["session"]
            == snap["exporter"]["data"]["session_id"],
            "exact old exporter session",
        )
        require(
            failure["error"]["sqlstate"] == "42704"
            and failure["error"]["message"]
            == 'snapshot "' + snap["exporter"]["data"]["snapshot"] + '" does not exist',
            "actual expired exported-snapshot rejection",
        )
    return {
        "investigation": "COMPLETE_FOR_FAMILY",
        "family": family,
        "cases": sorted(records),
    }
