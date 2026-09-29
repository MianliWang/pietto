"""Explicit S02 recovery laboratory. No database discovery during import/collection."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


s01 = load("p68_s01", ROOT / "scripts/phase68_executor_premise.py")
store = load("p68_store", ROOT / "tests/_pietto_phase68_recovery_store.py")


def binding(job="lab", token="local"):
    return dict(
        job=job, version=1, token=token, namespace="reference", epoch=1, expires=100
    )


def barrier(data):
    print(json.dumps({"event": "result", "data": data}), flush=True)
    if not sys.stdin.readline():
        raise RuntimeError("barrier peer disappeared")


def child(config, directory, *, kill=False, at_barrier=None, seconds=60):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = time.monotonic()
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    record = {"pid": process.pid, "operation": config["op"], "killed_at_barrier": False}
    with (directory / "children.jsonl").open("a") as f:
        f.write(json.dumps({"event": "registered", **record}) + "\n")
    messages = []

    def dispatch(message):
        if message["event"] != "result" or messages:
            raise ValueError("unexpected recovery control frame")
        messages.append(message["data"])
        if at_barrier:
            at_barrier(message["data"])
        if kill:
            process.kill()
            record["killed_at_barrier"] = True
        elif config.get("wait"):
            s01._send_control(process, {"continue": True})

    try:
        try:
            stderr = s01._pump_child(process, dispatch, initial=config, seconds=seconds)
            record["stderr_bytes"] = len(stderr)
        except RuntimeError as error:
            if not (
                kill
                and record["killed_at_barrier"]
                and process.returncode == -signal.SIGKILL
                and str(error) == "registered child failed"
            ):
                raise
            record["expected_pump_failure"] = str(error)
        if len(messages) != 1:
            raise ValueError("missing recovery observation")
        record.update(
            exit=process.returncode,
            reaped=process.poll() is not None,
            data=messages[0],
            elapsed_seconds=time.monotonic() - started,
        )
        with (directory / "observations.jsonl").open("a") as f:
            f.write(json.dumps(record) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return record
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()
        with (directory / "children.jsonl").open("a") as f:
            f.write(
                json.dumps(
                    {"event": "reaped", "pid": process.pid, "exit": process.returncode}
                )
                + "\n"
            )


def source_worker(config):
    driver = s01.Driver(config)
    try:
        session_sql = (
            "SELECT current_user, pg_backend_pid()"
            if config["target"] == "postgres"
            else "SELECT CURRENT_USER(), CONNECTION_ID()"
        )
        session, session_rows = driver.query(session_sql)
        result = {
            "pid": os.getpid(),
            "session": session,
            "session_id": session_rows[0][1],
        }
        if config["op"] == "mutable":
            driver.control(
                "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
                if config["target"] == "postgres"
                else "START TRANSACTION READ ONLY"
            )
            result["query"], _ = driver.query("SELECT value FROM p68r_mutable")
            driver.control("COMMIT")
        elif config["op"] == "snapshot_export":
            driver.control("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            result["query"], rows = driver.query("SELECT pg_export_snapshot()")
            result["snapshot"] = rows[0][0]
            driver.control("ROLLBACK")
        elif config["op"] == "snapshot_import":
            value = config["snapshot"]
            if not value or any(c not in "0123456789ABCDEFabcdef-" for c in value):
                raise ValueError("invalid laboratory snapshot identifier")
            driver.control("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            result["query"], _ = driver.query(
                "SET TRANSACTION SNAPSHOT '" + value + "'"
            )
            driver.control("ROLLBACK")
        else:
            directory = Path(config["job_directory"])
            b = config["binding"]
            recovered = store.reopen(directory, b)
            result["reopened"] = recovered
            parameter = "?" if config["target"] == "mysql" else "$1"
            result["version_query"], version = driver.query(
                "SELECT token, retained FROM p68r_versions WHERE version_id = "
                + parameter,
                (b["version"],),
            )
            if version != [(b["token"], 1)]:
                result["rejected"] = "source version absent, replaced or expired"
            else:
                result["pages"] = []
                last = recovered["frontier"]
                page_size = config["page_size"]
                while True:
                    placeholders = (
                        ("?", "?", "?")
                        if config["target"] == "mysql"
                        else ("$1", "$2", "$3")
                    )
                    sql = (
                        "SELECT occurrence_id, visible_key, payload, exact_value FROM p68r_rows WHERE version_id = "
                        + placeholders[0]
                        + " AND occurrence_id > "
                        + placeholders[1]
                        + " ORDER BY occurrence_id LIMIT "
                        + placeholders[2]
                    )
                    observed, rows = driver.query(sql, (b["version"], last, page_size))
                    if "error" in observed:
                        raise RuntimeError(
                            "source page failed: " + str(observed["error"])
                        )
                    page = {"query": observed, "after": last, "limit": page_size}
                    result["pages"].append(page)
                    if not rows:
                        result["source_terminal"] = (
                            "empty_bounded_query_after_all_pages"
                        )
                        break
                    page["checkpoint"] = store.persist(directory, b, rows)
                    last = rows[-1][0]
                    if config.get("prefix"):
                        result["source_terminal"] = "interrupted_after_prefix_ack"
                        barrier(result)
                        raise RuntimeError("crashed extractor unexpectedly resumed")
        result["controls"] = driver.controls
        return result
    finally:
        driver.close()


def worker(config):
    op = config["op"]
    if op in ("source", "mutable", "snapshot_export", "snapshot_import"):
        return source_worker(config)
    directory = Path(config.get("job_directory", "."))
    b = config.get("binding", binding())
    if op == "echo":
        return {"value": config["value"]}
    if op == "stall":
        sys.stdin.readline()
        return {}
    if op == "store":
        try:
            return store.persist(
                directory, b, config["rows"], config.get("cut", "none"), barrier
            )
        except OSError as error:
            if config.get("cut") != "fsync_failure":
                raise
            return {"injected": str(error), "checkpoint_ack": False}
    if op == "reopen":
        try:
            return store.reopen(directory, b, config.get("now", 0))
        except (ValueError, FileNotFoundError) as error:
            return {"rejected": type(error).__name__ + ": " + str(error)}
    if op == "sink":
        try:
            result = store.effect(
                Path(config["sink"]), b, config["row"], config.get("now", 0)
            )
            if config.get("wait"):
                barrier(result)
            return result
        except ValueError as error:
            return {"rejected": str(error)}
    if op == "sink_read":
        return store.sink_read(Path(config["sink"]))
    if op == "consume":
        saved = store.reopen(directory, b, config.get("now", 0))
        receipts = []
        for row in saved["rows"]:
            receipt = store.effect(Path(config["sink"]), b, row)
            receipt["ack_profile"] = store.acknowledge(directory, b, row[0])
            receipts.append(receipt)
        return {"receipts": receipts, "job": store.reopen(directory, b)}
    if op == "wait":
        with store.connection(directory / "job.sqlite") as db:
            barrier(
                {
                    "profile": store.profile(db),
                    "state": db.execute("SELECT state FROM job").fetchone()[0],
                }
            )
        return None
    raise ValueError("unknown laboratory operation")


def run_store(directory):
    directory.mkdir(mode=0o700)
    records = {}
    b = binding()
    rows = [[1, 7, "same", 9007199254740993]]
    for cut in ("partial", "fsync_failure", "orphan", "uncommitted", "committed"):
        job = directory / cut
        store.initialize(job, b)
        prior = store.persist(job, b, rows)
        c = child(
            dict(
                op="store",
                job_directory=str(job),
                binding=b,
                rows=[[2, 7, "same", 9007199254740993]],
                cut=cut,
            ),
            directory,
            kill=cut != "fsync_failure",
        )
        records["store_" + cut] = {
            "prior_checkpoint": prior,
            "producer": c,
            "reopen": child(
                dict(op="reopen", job_directory=str(job), binding=b), directory
            ),
            "files": sorted(p.name for p in job.iterdir()),
        }
    rejected = {}
    for defect in (
        "missing",
        "corrupt",
        "binding",
        "version",
        "namespace",
        "epoch",
        "expiry",
        "canceled",
    ):
        job = directory / defect
        store.initialize(job, b)
        store.persist(job, b, rows)
        store.acknowledge(job, b, 1)
        candidate, now = dict(b), 0
        if defect == "missing":
            (job / "chunk-1-1.json").unlink()
        elif defect == "corrupt":
            (job / "chunk-1-1.json").write_bytes(b"wrong")
        elif defect in ("binding", "version", "namespace", "epoch"):
            candidate["job" if defect == "binding" else defect] = (
                2 if defect in ("version", "epoch") else "changed"
            )
        elif defect == "expiry":
            now = 100
        else:
            with store.connection(job / "job.sqlite") as db:
                db.execute("UPDATE job SET state='canceled'")
        rejected[defect] = child(
            dict(op="reopen", job_directory=str(job), binding=candidate, now=now),
            directory,
        )
    records["store_guards"] = rejected
    job = directory / "holes"
    sink = directory / "holes-sink.sqlite"
    store.initialize(job, b)
    store.sink_initialize(sink, b)
    for position in (1, 3):
        row = [position, 7, "same", 9007199254740993]
        store.persist(job, b, [row])
        child(dict(op="sink", sink=str(sink), binding=b, row=row), directory)
        store.acknowledge(job, b, position)
    records["holes"] = {
        "reopen": child(
            dict(op="reopen", job_directory=str(job), binding=b), directory
        ),
        "sink": child(dict(op="sink_read", sink=str(sink)), directory),
    }
    guards = {}
    for defect in ("payload", "namespace", "epoch", "expiry"):
        candidate, row, now = dict(b), list(rows[0]), 0
        if defect == "payload":
            row[2] = "different"
        elif defect == "expiry":
            now = 100
        else:
            candidate[defect] = "changed"
        guards[defect] = child(
            dict(op="sink", sink=str(sink), binding=candidate, row=row, now=now),
            directory,
        )
    records["sink_guards"] = guards
    other = directory / "other"
    store.initialize(other, binding("other"))
    history = {}

    def during_wait(observed):
        history["waiting"] = observed
        with store.connection(other / "job.sqlite") as reader:
            reader.execute("BEGIN")
            history["reader_before"] = reader.execute(
                "SELECT state FROM job"
            ).fetchone()[0]
            with store.connection(other / "job.sqlite") as writer:
                writer.execute("UPDATE job SET state='complete'")
                history["writer_profile"] = store.profile(writer)
            history["reader_same_view"] = reader.execute(
                "SELECT state FROM job"
            ).fetchone()[0]
            reader.execute("COMMIT")
            history["reader_new_view"] = reader.execute(
                "SELECT state FROM job"
            ).fetchone()[0]

    records["isolation"] = {
        "waiter": child(
            dict(op="wait", wait=True, job_directory=str(job)),
            directory,
            at_barrier=during_wait,
        ),
        "history": history,
        "original_job": child(
            dict(op="reopen", job_directory=str(job), binding=b), directory
        ),
    }
    repeated = [(1, 7), (2, 7), (3, 9)]
    records["algorithms"] = {
        "input": repeated,
        "prefix": repeated[:1],
        "strict_key_suffix": [r for r in repeated if r[1] > 7],
        "occurrence_suffix": [r for r in repeated if r[0] > 1],
        "global_input": [2, 3, 5],
        "whole_sum": [sum([2, 3, 5])],
        "concatenated_partial_sum": [sum([2, 3]), sum([5])],
        "unknown": {
            "saved_eof": True,
            "remote_commit_observed": False,
            "transaction_terminal": "UNKNOWN",
        },
    }
    if (
        sum(p.stat().st_size for p in directory.rglob("*") if p.is_file())
        > 64 * 1024 * 1024
    ):
        raise ValueError("store family bound")
    return records


def manager(resources, sql):
    with resources.manager.cursor() as cursor:
        cursor.execute(sql)
        return [list(row) for row in cursor.fetchall()] if cursor.description else []


def setup_source(resources, token):
    statements = [
        "CREATE TABLE p68r_versions(version_id INTEGER PRIMARY KEY, token VARCHAR(64), retained INTEGER)",
        "CREATE TABLE p68r_rows(version_id INTEGER, occurrence_id INTEGER, visible_key INTEGER, payload VARCHAR(64), exact_value BIGINT, PRIMARY KEY(version_id,occurrence_id))",
        "CREATE TABLE p68r_mutable(value INTEGER)",
        "INSERT INTO p68r_mutable VALUES (10)",
        f"INSERT INTO p68r_versions VALUES (1,'{token}',1)",
        "INSERT INTO p68r_rows VALUES (1,1,7,'same',9007199254740993),(1,2,7,'same',9007199254740993),(1,3,7,'same',9007199254740993),(1,4,9,NULL,-11),(1,5,9,'雪'' ? $1',0),(1,6,12,'last',42)",
    ]
    if resources.target == "postgres":
        statements += [
            "CREATE FUNCTION p68r_sealed() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'sealed fixture'; END $$",
            "CREATE TRIGGER p68r_sealed BEFORE INSERT OR UPDATE OR DELETE ON p68r_rows FOR EACH ROW EXECUTE FUNCTION p68r_sealed()",
        ]
    else:
        statements += [
            f"CREATE TRIGGER p68r_sealed_{op.lower()} BEFORE {op} ON p68r_rows FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='sealed fixture'"
            for op in ("INSERT", "UPDATE", "DELETE")
        ]
    for sql in statements:
        manager(resources, sql)
    for sql, secret in resources.role_statements():
        manager(resources, sql)
        if not secret:
            statements.append(sql)
    try:
        manager(
            resources, "UPDATE p68r_rows SET payload='changed' WHERE occurrence_id=1"
        )
    except Exception as error:
        enforcement = {
            "error_type": type(error).__name__,
            "message": resources.without_secrets(str(error)),
        }
    else:
        raise RuntimeError("immutable fixture enforcement failed")
    return {
        "statements": statements,
        "manager_update_rejected": enforcement,
        "ownership": "isolated fixture manager; row-level triggers reject DML even by manager; extractor SELECT-only; DDL/retention guarantee belongs to manager",
    }


def gone(resources, session):
    sql = (
        f"SELECT pid FROM pg_stat_activity WHERE pid={int(session)}"
        if resources.target == "postgres"
        else f"SELECT ID FROM information_schema.PROCESSLIST WHERE ID={int(session)}"
    )
    start = time.monotonic()
    while True:
        rows = manager(resources, sql)
        if not rows:
            return {
                "sql": sql,
                "actual": rows,
                "session": session,
                "seconds": time.monotonic() - start,
            }
        if time.monotonic() - start > 5:
            raise TimeoutError("owned extractor session did not end")
        time.sleep(0.02)


def charge(ledger, category, reason):
    data = json.loads(ledger.read_text())
    counter = data["budgets"][category]
    if counter["used"] >= counter["limit"]:
        raise RuntimeError("execution budget exhausted: " + category)
    counter["used"] += 1
    data["events"].append(
        {
            "event": "charge",
            "category": category,
            "number": counter["used"],
            "reason": reason,
        }
    )
    ledger.write_text(json.dumps(data, indent=2) + "\n")


def run_source(target, directory, ledger):
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resources = s01.helper("_pietto_target_conformance_resources").Resources(
        target, pins["targets"][target], directory
    )
    records, receipt = {}, {}
    charge(ledger, "source_db_lifecycle_starts", target)
    try:
        resources.acquire()
        token = uuid.uuid4().hex
        receipt["server_version"] = manager(resources, "SELECT version()")
        receipt["fixture"] = setup_source(resources, token)
        routes = (
            ("postgres_rows", "postgres_adbc")
            if target == "postgres"
            else ("mysql_rows",)
        )
        config = dict(
            target=target,
            port=resources.port,
            password=resources._passwords[1],
            ca=str(resources.ca_path),
        )
        for route in routes:
            b = binding(route, token)
            job = directory / route
            sink = directory / (route + "-sink.sqlite")
            store.initialize(job, b)
            store.sink_initialize(sink, b)
            initial = dict(
                config,
                op="source",
                route=route,
                binding=b,
                job_directory=str(job),
                page_size=2,
                prefix=True,
            )
            prefix = child(initial, directory, kill=True)
            record = {
                "binding": b,
                "prefix": prefix,
                "old_session_absent": gone(resources, prefix["data"]["session_id"]),
            }
            records[route] = record
            # A distinct source version cannot replace the selected immutable version.
            if route == routes[0]:
                sql = "INSERT INTO p68r_versions VALUES (2,'different-version',1)"
                manager(resources, sql)
                receipt["new_version_sql"] = sql
            record["recovery"] = child(
                dict(initial, prefix=False, page_size=3), directory
            )
            record["recovery_session_absent"] = gone(
                resources, record["recovery"]["data"]["session_id"]
            )
            saved = child(
                dict(op="reopen", binding=b, job_directory=str(job)), directory
            )
            record["saved"] = saved
            record["lost_ack"] = child(
                dict(
                    op="sink",
                    sink=str(sink),
                    binding=b,
                    row=saved["data"]["rows"][0],
                    wait=True,
                ),
                directory,
                kill=True,
            )
            record["before_reconcile"] = child(
                dict(op="reopen", binding=b, job_directory=str(job)), directory
            )
            record["sink_after_loss"] = child(
                dict(op="sink_read", sink=str(sink)), directory
            )
            record["consumer"] = child(
                dict(op="consume", sink=str(sink), binding=b, job_directory=str(job)),
                directory,
            )
            record["sink_final"] = child(
                dict(op="sink_read", sink=str(sink)), directory
            )
            manager(resources, "UPDATE p68r_versions SET retained=0 WHERE version_id=1")
            record["expired"] = child(
                dict(initial, prefix=False, page_size=3), directory
            )
            manager(
                resources,
                "UPDATE p68r_versions SET retained=1, token='replacement' WHERE version_id=1",
            )
            record["replacement"] = child(
                dict(initial, prefix=False, page_size=3), directory
            )
            manager(
                resources,
                f"UPDATE p68r_versions SET token='{token}' WHERE version_id=1",
            )
            record["owned_payload_bytes"] = (
                sum(p.stat().st_size for p in job.iterdir()) + sink.stat().st_size
            )
            if record["owned_payload_bytes"] > 64 * 1024 * 1024:
                raise ValueError("case storage bound")
            (directory / (route + ".json")).write_text(
                json.dumps(record, indent=2) + "\n"
            )
        control = dict(config, route=routes[0])
        before = child(dict(control, op="mutable"), directory)
        manager(resources, "UPDATE p68r_mutable SET value=20")
        after = child(dict(control, op="mutable"), directory)
        records[target + "_mutable"] = {
            "before": before,
            "manager_sql": "UPDATE p68r_mutable SET value=20",
            "after": after,
        }
        if target == "postgres":
            exporter = child(dict(control, op="snapshot_export"), directory)
            absent = gone(resources, exporter["data"]["session_id"])
            importer = child(
                dict(
                    control, op="snapshot_import", snapshot=exporter["data"]["snapshot"]
                ),
                directory,
            )
            records["snapshot"] = {
                "exporter": exporter,
                "exporter_absent": absent,
                "importer": importer,
            }
    finally:
        receipt["cleanup"] = resources.cleanup()
        receipt["events"] = resources.events
        (directory / "resource-receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n"
        )
    return records, receipt


def metadata(directory):
    import _sqlite3
    import platform
    import sysconfig
    import pyarrow as pa

    directory.mkdir(mode=0o700)
    field = pa.field(
        "exact_value", pa.int64(), nullable=True, metadata={b"probe": b"actual"}
    )
    batch = pa.record_batch(
        [pa.array([9007199254740993, None], type=field.type)], schema=pa.schema([field])
    )
    batch.validate(full=True)
    with store.connection(directory / "metadata.sqlite") as db:
        sqlite = dict(
            version=sqlite3.sqlite_version,
            source_id=db.execute("SELECT sqlite_source_id()").fetchone()[0],
            compile_options=[r[0] for r in db.execute("PRAGMA compile_options")],
            profile=store.profile(db),
            module_file=getattr(_sqlite3, "__file__", None),
            module_origin=_sqlite3.__spec__.origin,
        )
    mount = json.loads(
        subprocess.check_output(["findmnt", "-J", "-T", str(directory)], text=True)
    )
    return {
        "sqlite": sqlite,
        "python": sys.version,
        "executable": sys.executable,
        "base_prefix": sys.base_prefix,
        "build": (Path(sys.base_prefix) / "BUILD").read_text().strip(),
        "config_args": sysconfig.get_config_var("CONFIG_ARGS"),
        "platform": platform.platform(),
        "mount": mount,
        "arrow": {
            "schema": str(batch.schema),
            "type": str(field.type),
            "metadata": {k.hex(): v.hex() for k, v in field.metadata.items()},
            "values": batch.column(0).to_pylist(),
        },
        "runtime": s01.runtime_identity(),
    }


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "worker":
        config = json.loads(sys.stdin.readline())
        result = worker(config)
        if result is not None:
            print(json.dumps({"event": "result", "data": result}), flush=True)
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run", "metadata"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--tree", default="unsealed")
    parser.add_argument(
        "--family", choices=("store", "postgres", "mysql", "all"), default="all"
    )
    args = parser.parse_args()
    if args.action == "run":
        assert args.ledger
        charge(
            args.ledger,
            "complete_experiment_campaign_starts"
            if args.family == "all"
            else "targeted_live_experiment_starts",
            args.family,
        )
    args.directory.mkdir(mode=0o700)
    report = {
        "execution_tree": args.tree,
        "location": "local",
        "family": args.family,
        "records": {},
        "resources": {},
        "complete": False,
    }
    try:
        report["metadata"] = metadata(args.directory / "metadata")
        if (
            report["metadata"]["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("experiment dependency identity mismatch")
        if args.action == "run":
            assert args.ledger
            if args.family in ("all", "store"):
                report["records"].update(run_store(args.directory / "store"))
            for target in ("postgres", "mysql"):
                if args.family in ("all", target):
                    with s01.helper("_pietto_target_conformance_resources").deadline(
                        780
                    ):
                        rows, resources = run_source(
                            target, args.directory / target, args.ledger
                        )
                    report["records"].update(rows)
                    report["resources"][target] = resources
        report["connections"] = [
            dict(location=str(path.relative_to(args.directory)), **json.loads(line))
            for path in sorted(args.directory.rglob("sqlite-connections.jsonl"))
            for line in path.read_text().splitlines()
        ]
        report["complete"] = True
    finally:
        (args.directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps({"complete": report["complete"], "cases": sorted(report["records"])})
    )


if __name__ == "__main__":
    main()
