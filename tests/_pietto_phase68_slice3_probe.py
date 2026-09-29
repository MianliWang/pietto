"""Owned S03 native observations. Literal expectations live in a separate module."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice03-"


def load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        m = importlib.util.module_from_spec(spec)
        sys.modules[name] = m
        spec.loader.exec_module(m)
    return sys.modules[name]


s01 = load("s03_s01", ROOT / "scripts/phase68_executor_premise.py")


def save(path, value):
    with path.open("x") as f:
        json.dump(value, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def charge(ledger, category, reason):
    d = json.loads(ledger.read_text())
    c = d["budgets"][category]
    if c["used"] >= c["limit"]:
        raise RuntimeError("budget exhausted: " + category)
    c["used"] += 1
    d["events"].append(
        dict(event="charge", category=category, number=c["used"], reason=reason)
    )
    ledger.write_text(json.dumps(d, indent=2) + "\n")


def child(config, directory, *, dispatch_hook=None, seconds=180) -> dict[str, Any]:
    started = time.monotonic()
    p = subprocess.Popen(
        [sys.executable, "-B", str(ROOT / "scripts/phase68_slice3_probe.py"), "worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    journal = directory / (PREFIX + "children.jsonl")
    with journal.open("a") as f:
        f.write(
            json.dumps(dict(event="registered", pid=p.pid, operation=config["op"]))
            + "\n"
        )
    messages = []

    def receive(value):
        if value["event"] == "result":
            messages.append(value["data"])
        elif dispatch_hook:
            dispatch_hook(value, p)
        else:
            raise ValueError("unregistered control event")

    try:
        stderr = s01._pump_child(p, receive, initial=config, seconds=seconds)
        if len(messages) != 1:
            raise ValueError("missing observation")
        result = dict(
            pid=p.pid,
            exit=p.returncode,
            reaped=p.poll() is not None,
            elapsed_seconds=time.monotonic() - started,
            stderr_bytes=len(stderr),
            data=messages[0],
        )
        with (directory / (PREFIX + "observations.jsonl")).open("a") as f:
            f.write(json.dumps(result) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return result
    finally:
        for stream in (p.stdin, p.stdout, p.stderr):
            if stream:
                stream.close()
        with journal.open("a") as f:
            f.write(
                json.dumps(dict(event="reaped", pid=p.pid, exit=p.returncode)) + "\n"
            )


def control(event, **data):
    print(json.dumps(dict(event=event, **data)), flush=True)
    return json.loads(sys.stdin.readline())


def view_sql(target, mode="full"):
    first = "SELECT 10 AS part,lid,version_id,k,v,visible,hidden,f FROM p68s3_left WHERE version_id=1"
    other = "10" if mode == "token_mismatch" else "20"
    second = f"SELECT {other} AS part,lid,version_id,k,v,visible,hidden,f FROM p68s3_right WHERE version_id=1"
    return first if mode == "visibility" else first + " UNION ALL " + second


def setup(resources, provider):
    statements = [
        "CREATE TABLE p68s3_version(provider VARCHAR(64), version_tag VARCHAR(16), active INTEGER, revision VARCHAR(32))",
        f"INSERT INTO p68s3_version VALUES ('{provider}','v1',1,'view-v1')",
    ]
    for name in ("left", "right"):
        statements.append(
            f"CREATE TABLE p68s3_{name}(lid INTEGER PRIMARY KEY,version_id INTEGER,k SMALLINT,v SMALLINT,visible VARCHAR(32),hidden BIGINT,f DOUBLE PRECISION)"
        )
    statements += [
        "INSERT INTO p68s3_left VALUES (1,1,1,10,'same',9007199254740993,0.0),(2,1,1,NULL,'same',9007199254740993,0.5),(3,1,2,20,'same',-9007199254740993,9007199254740992.0),(4,1,3,30,'same',104,-1.25)",
        "INSERT INTO p68s3_right VALUES (1,1,1,10,'same',201,0.0),(2,1,1,40,'same',202,0.5),(3,1,2,NULL,'same',9007199254740993,9007199254740992.0),(4,1,3,60,'same',204,-1.25)",
        "CREATE VIEW p68s3_input AS " + view_sql(resources.target),
        (
            'CREATE TABLE "rows"(id BIGINT NOT NULL,other BIGINT)'
            if resources.target == "postgres"
            else "CREATE TABLE `rows`(id BIGINT NOT NULL,other BIGINT)"
        ),
        (
            'INSERT INTO "rows" VALUES(9007199254740993,NULL),(9007199254740993,-9007199254740993),(0,0),(-1,1)'
            if resources.target == "postgres"
            else "INSERT INTO `rows` VALUES(9007199254740993,NULL),(9007199254740993,-9007199254740993),(0,0),(-1,1)"
        ),
    ]
    if resources.target == "postgres":
        statements.append(
            "CREATE FUNCTION p68s3_sealed() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable version'; END $$"
        )
        statements += [
            f"CREATE TRIGGER p68s3_seal BEFORE INSERT OR UPDATE OR DELETE ON p68s3_{name} FOR EACH ROW EXECUTE FUNCTION p68s3_sealed()"
            for name in ("left", "right")
        ]
    else:
        statements += [
            f"CREATE TRIGGER p68s3_{name}_{op} BEFORE {op} ON p68s3_{name} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='immutable version'"
            for name in ("left", "right")
            for op in ("INSERT", "UPDATE", "DELETE")
        ]
    for sql in statements:
        manager(resources, sql)
    for sql, secret in resources.role_statements():
        manager(resources, sql)
    if resources.target == "postgres":
        role = [
            "CREATE ROLE p68s3_role NOLOGIN",
            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO p68s3_role",
            "GRANT p68s3_role TO pietto_query",
        ]
    else:
        role = [
            "GRANT SHOW VIEW ON phase66.* TO 'pietto_query'@'%'",
            "CREATE ROLE 'p68s3_role'",
            "GRANT SELECT,SHOW VIEW ON phase66.* TO 'p68s3_role'",
            "GRANT 'p68s3_role' TO 'pietto_query'@'%'",
        ]
    for sql in role:
        manager(resources, sql)
    failures = []
    for name in ("left", "right"):
        try:
            manager(resources, f"UPDATE p68s3_{name} SET visible='mutated' WHERE lid=1")
        except Exception as error:
            failures.append(
                dict(component=name, error=resources.without_secrets(str(error)))
            )
        else:
            raise ValueError("fixture not sealed")
    return dict(
        statements=statements,
        role_read_grants=[
            sql for sql, secret in resources.role_statements() if not secret
        ],
        immutability_controls=failures,
        guarantees="fixture manager retains this immutable version and complete component view until explicit expiry; DDL/retention remain provider responsibility",
        provider=provider,
    )


def manager(resources, sql):
    with resources.manager.cursor() as cursor:
        cursor.execute(sql)
        return [list(row) for row in cursor.fetchall()] if cursor.description else []


def frame_query(target, case, *, recipe="scalar_frame_subquery"):
    if recipe != "scalar_frame_subquery":
        raise ValueError("alternative requires an explicit diagnosed revision")
    markers = ("?", "?", "?") if target == "mysql" else ("$1", "$2", "$3")
    base = (
        "WITH b AS (SELECT * FROM p68s3_input WHERE version_id="
        + markers[0]
        + "), c AS (SELECT b.*,ROW_NUMBER() OVER(ORDER BY k,part,lid) AS u,ROW_NUMBER() OVER(ORDER BY k DESC,part,lid) AS ud,DENSE_RANK() OVER(ORDER BY k) AS g FROM b)"
    )

    def frame(function, predicate, order="u"):
        return f"(SELECT {function} OVER(ORDER BY z.{order} ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) FROM c z WHERE {predicate} ORDER BY z.{order} LIMIT 1)"

    if case in ("native_frames", "native_groups"):
        if case == "native_frames":
            calls = [
                "FIRST_VALUE(k) OVER(ORDER BY k RANGE BETWEEN 1 PRECEDING AND CURRENT ROW) AS narrow",
                "FIRST_VALUE(k) OVER(ORDER BY k RANGE BETWEEN 40000 PRECEDING AND CURRENT ROW) AS wide",
                "FIRST_VALUE(k) OVER(ORDER BY k DESC RANGE BETWEEN 1 PRECEDING AND CURRENT ROW) AS descending",
            ]
            labels = "part,lid,narrow,wide,descending"
        else:
            calls = [
                f"FIRST_VALUE(k) OVER(ORDER BY k GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE {clause}) AS {label}"
                for clause, label in (
                    ("CURRENT ROW", "original_current"),
                    ("TIES", "original_ties"),
                    ("GROUP", "original_group"),
                )
            ]
            labels = "part,lid,original_current,original_ties,original_group"
        body = "SELECT part,lid,u," + ",".join(calls) + " FROM c"
        complete = "SELECT * FROM w"
    elif case == "groups":
        fields = [
            frame("FIRST_VALUE(z.v)", f"z.g BETWEEN x.g-1 AND x.g AND {predicate}")
            + " AS "
            + label
            for predicate, label in (
                ("NOT(z.part=x.part AND z.lid=x.lid)", "exclude_current"),
                ("(z.g<>x.g OR (z.part=x.part AND z.lid=x.lid))", "exclude_ties"),
                ("z.g<>x.g", "exclude_group"),
            )
        ]
        body = "SELECT x.part,x.lid,x.u," + ",".join(fields) + " FROM c x"
        labels = "part,lid,exclude_current,exclude_ties,exclude_group"
        complete = "SELECT * FROM w"
    else:
        fields = [
            "x.part",
            "x.lid",
            "x.v",
            "x.u AS rn",
            "LAG(x.v,1,999999999) OVER(ORDER BY x.u) AS lag_big",
            "NTILE(3) OVER(ORDER BY x.u) AS bucket",
            "RANK() OVER(ORDER BY x.k) AS rnk",
            "DENSE_RANK() OVER(ORDER BY x.k) AS dense",
            "PERCENT_RANK() OVER(ORDER BY x.k) AS pct",
            "CUME_DIST() OVER(ORDER BY x.k) AS cume",
            "FIRST_VALUE(x.v) OVER(ORDER BY x.u ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS rows_first",
            frame("LAST_VALUE(z.v)", "z.g<=x.g") + " AS range_last",
            frame("NTH_VALUE(z.v,5)", "z.g<=x.g") + " AS nth5",
            "LAST_VALUE(x.v) OVER(ORDER BY x.u ROWS BETWEEN 1 FOLLOWING AND 1 FOLLOWING) AS next_last",
            frame("LAST_VALUE(z.v)", "z.k BETWEEN x.k AND x.k+1", "ud")
            + " AS desc_last",
            "LEAD(x.v) OVER(ORDER BY x.u) AS hidden_next",
            "x.u",
        ]
        body = "SELECT " + ",".join(fields) + " FROM c x"
        labels = (
            "part,lid,v,rn,lag_big,bucket,rnk,dense,pct,cume,rows_first,range_last,nth5,next_last"
            if case == "joint"
            else "part,lid,rows_first,range_last,nth5,next_last,desc_last"
        )
        complete = (
            "SELECT * FROM w WHERE rn<=7 AND (hidden_next IS NULL OR hidden_next<>40) ORDER BY u LIMIT 5"
            if case == "joint"
            else "SELECT * FROM w"
        )
    return (
        base
        + ", w AS ("
        + body
        + "), q AS ("
        + complete
        + "), e AS (SELECT q.*,ROW_NUMBER() OVER(ORDER BY u) AS page_position FROM q) SELECT "
        + labels
        + " FROM e WHERE page_position>"
        + markers[1]
        + " ORDER BY page_position LIMIT "
        + markers[2]
    )


def worker(config):
    if config["op"] == "product":
        return product_worker(config)
    if config["op"] == "echo":
        return dict(value=config["value"])
    if config["op"] == "stall":
        sys.stdin.readline()
        return {}
    d = s01.Driver(config)
    queries = []

    def query(sql, args=()):
        rec, rows = d.query(sql, args)
        queries.append(rec)
        return rec, rows

    try:
        if config.get("changed_role"):
            d.control("SET ROLE p68s3_role")
        role_sql = (
            "SELECT current_user,session_user,pg_backend_pid()"
            if config["target"] == "postgres"
            else "SELECT CURRENT_USER(),CURRENT_ROLE(),CONNECTION_ID()"
        )
        session, role = query(role_sql)
        result = dict(session=session, session_id=role[0][2], queries=queries)
        if config["op"] == "p1":
            meta, rows = query(
                "SELECT provider,version_tag,active,revision FROM p68s3_version"
            )
            result["registry"] = meta
            if role[0][0].split("@")[0] != "pietto_query" or (
                config["target"] == "mysql" and role[0][1] != "NONE"
            ):
                result["rejected"] = "role context"
                return result
            if rows != [(config["provider"], "v1", 1, "view-v1")]:
                result["rejected"] = "provider version or retention"
                return result
            namespace = "public" if config["target"] == "postgres" else "phase66"
            definition, defs = query(
                "SELECT pg_get_viewdef('public.p68s3_input'::regclass, true)"
                if config["target"] == "postgres"
                else "SELECT view_definition FROM information_schema.views WHERE table_schema='"
                + namespace
                + "' AND table_name='p68s3_input'"
            )
            result["definition"] = definition
            if config.get("expected_definition") is not None and defs != [
                (config["expected_definition"],)
            ]:
                result["rejected"] = "view domain"
                return result
            unique, bad = query(
                "SELECT part,lid,COUNT(*) FROM p68s3_input GROUP BY part,lid HAVING part IS NULL OR lid IS NULL OR COUNT(*)<>1"
            )
            result["uniqueness"] = unique
            if bad:
                result["rejected"] = "token domain"
                return result
            order = "lid DESC,part DESC" if config.get("alternate") else "part,lid"
            result["rows"], _ = query(
                "SELECT part,lid,k,v,visible,hidden,f FROM p68s3_input ORDER BY "
                + order
            )
            result["local_key"], _ = query(
                "SELECT lid,COUNT(*) FROM p68s3_input GROUP BY lid HAVING COUNT(*)<>1 ORDER BY lid"
            )
            result["repeated"], _ = query(
                "SELECT l.part,l.lid,r.part,r.lid FROM p68s3_input l JOIN p68s3_input r ON l.lid=r.lid ORDER BY l.part,l.lid,r.part,r.lid"
            )
            cast = "DOUBLE PRECISION" if config["target"] == "postgres" else "DOUBLE"
            result["signed_zero"], _ = query(
                "SELECT CAST('0' AS "
                + cast
                + ") AS positive_zero,-CAST('0' AS "
                + cast
                + ") AS negative_zero"
            )
        elif config["op"] == "p2":
            result["cases"] = {}
            names = (
                ("joint", "frames", "native_frames", "groups", "native_groups")
                if config["target"] == "postgres"
                else ("joint", "frames", "native_frames")
            )
            for case in names:
                sql = frame_query(config["target"], case)
                for label, after, size in (
                    ("full", 0, 16),
                    ("prefix", 0, 2),
                    ("empty", 99, 2),
                ):
                    result["cases"][case + "/" + label], _ = query(
                        sql, (1, after, size)
                    )
            result["pg_only_domain"] = (
                "GROUPS/exclusions exercised"
                if config["target"] == "postgres"
                else "approved MySQL feature-specific non-support retained; not emulated"
            )
        return result
    finally:
        d.close()


def run_target(target, directory, ledger, *, stage="qualify"):
    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resources = s01.helper("_pietto_target_conformance_resources").Resources(
        target, pins["targets"][target], directory
    )
    charge(ledger, "source_db_lifecycle_starts", "S03 qualification " + target)
    result = {"target": target, "p1": {}, "p2": {}}
    try:
        resources.acquire()
        provider = uuid.uuid4().hex
        result["fixture"] = setup(resources, provider)
        result["server_version"] = manager(resources, "SELECT version()")
        config = dict(
            target=target,
            route=target + "_rows",
            port=resources.port,
            password=resources._passwords[1],
            ca=str(resources.ca_path),
            provider=provider,
            op="p1",
        )
        if stage == "product":
            result["product"] = product_family(resources, config, directory)
            return result
        first = child(config, directory)
        result["p1"]["initial"] = first
        definition_cell = first["data"]["definition"]["actual"][0][0]
        if definition_cell.get("kind") != "text":
            raise ValueError("source definition unavailable to explicit read role")
        definition = definition_cell["value"]
        config["expected_definition"] = definition
        result["p1"]["reopen"] = child(dict(config, alternate=True), directory)
        for name, sql in (
            ("expiry", "UPDATE p68s3_version SET active=0"),
            ("replacement", "UPDATE p68s3_version SET version_tag='v2'"),
        ):
            manager(resources, sql)
            result["p1"][name] = child(config, directory)
            manager(resources, "UPDATE p68s3_version SET active=1,version_tag='v1'")
        manager(
            resources,
            "CREATE OR REPLACE VIEW p68s3_input AS " + view_sql(target, "visibility"),
        )
        result["p1"]["visibility"] = child(config, directory)
        manager(
            resources,
            "CREATE OR REPLACE VIEW p68s3_input AS "
            + view_sql(target, "token_mismatch"),
        )
        result["p1"]["token_mismatch"] = child(
            dict(config, expected_definition=None), directory
        )
        manager(resources, "CREATE OR REPLACE VIEW p68s3_input AS " + view_sql(target))
        result["p1"]["role"] = child(dict(config, changed_role=True), directory)
        save(directory / (PREFIX + "p1.json"), result["p1"])
        for route in (
            ("postgres_rows", "postgres_adbc")
            if target == "postgres"
            else ("mysql_rows",)
        ):
            result["p2"][route] = child(dict(config, op="p2", route=route), directory)
            save(directory / (PREFIX + route + ".json"), result["p2"][route])
        if stage == "all" and target == "postgres":
            result["product"] = product_family(resources, config, directory)
    finally:
        result["cleanup"] = resources.cleanup()
        result["resource_events"] = resources.events
        save(directory / (PREFIX + "target-receipt.json"), result)
        if result["cleanup"]["status"] != "success":
            raise RuntimeError("owned cleanup failed")
    return result


def main():
    if sys.argv[1:] == ["worker"]:
        value = worker(json.loads(sys.stdin.readline()))
        print(json.dumps(dict(event="result", data=value)), flush=True)
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("qualify", "metadata", "product", "all"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--target", choices=("postgres", "mysql", "all"), default="all")
    a = parser.parse_args()
    a.directory.mkdir(mode=0o700)
    report = {
        "kind": "S03_qualification",
        "execution_tree": a.tree,
        "location": "local",
        "targets": {},
        "complete": False,
    }
    try:
        runtime = s01.runtime_identity()
        pins = s01.helper("_pietto_phase68_executor_cases").PINS
        if runtime["versions"] != pins:
            raise ValueError("changed experiment dependencies")
        report["runtime"] = runtime
        pa = __import__("importlib").import_module("pyarrow")
        metadata = pa.field(
            "value", pa.int16(), nullable=True, metadata={b"s03": b"actual"}
        )
        report["metadata_preflight"] = {
            "type": str(metadata.type),
            "metadata": {k.hex(): v.hex() for k, v in metadata.metadata.items()},
            "nullable": metadata.nullable,
        }
        json.dumps(report)
        if a.action in ("qualify", "product", "all"):
            assert a.ledger
            for target in ("postgres", "mysql"):
                if a.target in ("all", target):
                    with s01.helper("_pietto_target_conformance_resources").deadline(
                        900
                    ):
                        report["targets"][target] = run_target(
                            target,
                            a.directory / (PREFIX + target),
                            a.ledger,
                            stage=a.action,
                        )
        report["complete"] = True
    finally:
        save(a.directory / (PREFIX + "report.json"), report)
    print(
        json.dumps({"complete": report["complete"], "targets": list(report["targets"])})
    )


def product_artifact(directory, relation):
    product = s01.helper("_pietto_phase67_result_product_probe")
    from pietto._project.project_sql_emission import emit_project_sql

    checked = product.build_neutral(
        directory, {"main.pietto": product.source("postgres")}
    )
    contract = json.loads(product.emission_input("postgres"))
    source = contract["sources"][0]
    source["relation"]["name"] = relation
    source["fields"][0]["column"] = "hidden"
    source["fields"][1]["column"] = "v"
    source["fields"][1]["representation"]["storage"] = {"kind": "pg_int2"}
    source["fields"][1]["representation"]["domain"] = {
        "kind": "int_range",
        "min": "-32768",
        "max": "32767",
    }
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        raise ValueError("product compile/emission failed")
    return checked, outcome.artifact


def product_worker(config):
    if config.get("origin", "source") == "source":
        sys.path.insert(0, str(ROOT / "src"))
    import importlib
    from dataclasses import asdict
    import threading
    from pietto._project import project_execution as execution
    from pietto._project import project_execution_postgres as pg
    from pietto._project.project_execution_source import RetainedSourceRequirement
    from pietto._project import project_execution_reader as reading
    from pietto._project.project_result_contract import ResultError

    pa = importlib.import_module("pyarrow")
    case = config["case"]
    directory = Path(config["directory"])
    directory.mkdir(mode=0o700)
    relation = (
        "p68s3_empty"
        if case == "empty"
        else "p68s3_fault"
        if case in ("source_error", "source_error_cleanup")
        else "p68s3_input"
    )
    checked, artifact = product_artifact(directory / "compiled", relation)
    access = execution.PostgresAccess(
        "127.0.0.1",
        config["port"],
        "phase66",
        "pietto_query",
        config["password"],
        "disable",
    )
    limits = execution.ExecutionLimits(
        batch_rows=2,
        max_rows=2 if case == "row_limit" else 1024,
        seconds=2 if case == "deadline" else 20,
    )
    requirement = None
    if case in (
        "normal",
        "installed_normal",
        "serializable",
        "cap_expired",
        "cap_token",
    ):
        requirement = RetainedSourceRequirement(
            artifact.request.sources[0],
            config["provider"],
            "v1",
            "view-v1",
            "public",
            "p68s3_version",
            config["definition"],
            ("part", "lid"),
            "pietto_query",
            "isolated provider retains this immutable complete component domain until explicit expiry",
        )
    request = execution.prepare_execution(
        artifact,
        access,
        limits=limits,
        isolation="serializable" if case == "serializable" else "stable",
        source_requirement=requirement,
    )
    stream = pg.PostgresExecution(request)
    rows = []
    consumer_schemas = []
    submitted = []
    callbacks = []
    late = None
    caught = None
    thread = None
    old_profile = sys.getprofile()

    def observe(frame, event, value):
        if old_profile:
            old_profile(frame, event, value)
        if (
            event == "call"
            and frame.f_code.co_name == "execute"
            and frame.f_locals.get("self") is stream._cursor
        ):
            submitted.append(
                {
                    "sql": frame.f_locals.get("query"),
                    "arguments": [
                        s01.scalar(x) for x in (frame.f_locals.get("params") or ())
                    ],
                    "prepare": frame.f_locals.get("prepare"),
                }
            )

    if case == "late_check":
        original = reading.ExecutionPayloads.accept
        count = [0]

        def injected(self, rows):
            count[0] += 1
            if count[0] == 2:
                raise ResultError("INJECTED_LATE_CHECK")
            return original(self, rows)

        reading.ExecutionPayloads.accept = injected
    if case in ("cleanup", "source_error_cleanup"):
        original_connect = pg._connect

        class ClosingProxy:
            def __init__(self, connection):
                self.connection = connection

            def __getattr__(self, name):
                return getattr(self.connection, name)

            def close(self):
                self.connection.close()
                raise OSError("injected after actual connection close")

        pg._connect = lambda request: ClosingProxy(original_connect(request))
    if case == "pre_cancel":
        callbacks.append(stream.cancel())
    try:
        sys.setprofile(observe)
        with stream:
            if case in ("source_error", "source_error_cleanup"):
                control("remove_fault", session=stream.session_id)
            if case in ("blocked_cancel", "deadline"):
                control(
                    "blocking_ready",
                    session=stream.session_id,
                    sql=artifact.rendered.sql.decode(),
                    cancel=case == "blocked_cancel",
                )
                if case == "blocked_cancel":

                    def cancel():
                        message = json.loads(sys.stdin.readline())
                        if message.get("cancel") is not True:
                            raise ValueError("unregistered cancellation")
                        callbacks.append(stream.cancel())

                    thread = threading.Thread(
                        target=cancel, name="pietto-s03-owned-cancel"
                    )
                    callbacks.append({"thread_registered": thread.name})
                    thread.start()
            for batch in stream:
                with batch:
                    actual = pa.record_batch(batch)
                    consumer_schemas.append(
                        [[f.name, str(f.type), f.nullable] for f in actual.schema]
                    )
                    rows.extend(
                        [
                            [
                                s01.scalar(actual.column(i)[j].as_py())
                                for i in range(actual.num_columns)
                            ]
                            for j in range(actual.num_rows)
                        ]
                    )
                if case == "early_close":
                    break
                if case == "consumer_error":
                    raise ValueError("injected consumer failure after checked delivery")
    except BaseException as error:
        caught = {
            "kind": type(error).__name__,
            "sqlstate": getattr(error, "sqlstate", None),
        }
        if (
            type(error) in (execution.ExecutionError, ResultError)
            or type(error).__name__ == "SourceAdmissionError"
        ):
            caught["category"] = str(error)
    finally:
        sys.setprofile(old_profile)
        if thread is not None:
            thread.join(6)
            if thread.is_alive():
                raise RuntimeError("owned product control thread not reaped")
        stream.close()
    if case == "late_cancel":
        late = stream.cancel()
    admission = stream.source_admission
    result = {
        "case": case,
        "compiled_verified": checked.verified,
        "sql": artifact.rendered.sql.decode(),
        "native_uses": len(artifact.parameter_uses),
        "submissions": submitted,
        "actual": rows,
        "metadata": stream.actual_metadata,
        "outcome": asdict(stream.outcome),
        "session_id": stream.session_id,
        "context": stream.context,
        "native_buffered_rows": stream.native_buffered_rows,
        "consumer_schemas": consumer_schemas,
        "bound_schema": None
        if stream._payloads is None
        else [
            [f.name, str(f.type), f.nullable] for f in stream._payloads.binding.schema
        ],
        "deadline_expired": stream.deadline_expired,
        "control_joined": stream.control_joined
        and (thread is None or not thread.is_alive()),
        "control_events": stream.control_events,
        "cancel_calls": callbacks,
        "late_cancel": late,
        "caught": caught,
        "source_admission": None
        if admission is None
        else {
            "provider": admission.requirement.provider,
            "version": admission.requirement.version,
            "token_type_oids": admission.token_type_oids,
            "session": admission.session_id,
        },
        "origins": {
            "execution": execution.__file__,
            "postgres": pg.__file__,
            "reader": reading.__file__,
        },
        "injection": case
        if case in ("late_check", "cleanup", "source_error_cleanup", "consumer_error")
        else None,
    }
    return result


def product_definition(resources):
    # Same explicit deparse context as production admission, with fixture context restored.
    manager(resources, "SET search_path=pg_catalog")
    try:
        return manager(
            resources, "SELECT pg_get_viewdef('public.p68s3_input'::regclass,true)"
        )[0][0]
    finally:
        manager(resources, "SET search_path=public")


def product_family(resources, config, directory):
    result = {}
    for name in ("p68s3_empty", "p68s3_fault"):
        manager(
            resources,
            "CREATE VIEW "
            + name
            + " AS SELECT * FROM p68s3_input"
            + (" WHERE FALSE" if name.endswith("empty") else ""),
        )
        manager(resources, "GRANT SELECT ON " + name + " TO pietto_query")
    definition = product_definition(resources)
    config = dict(config, op="product", definition=definition)
    cases = (
        "normal",
        "empty",
        "serializable",
        "early_close",
        "row_limit",
        "late_check",
        "consumer_error",
        "pre_cancel",
        "blocked_cancel",
        "deadline",
        "late_cancel",
        "cleanup",
        "source_error",
        "source_error_cleanup",
        "cap_expired",
        "cap_token",
        "installed_normal",
    )
    for case in cases:
        if case == "cap_expired":
            manager(resources, "UPDATE p68s3_version SET active=0")
        if case == "cap_token":
            manager(
                resources,
                "CREATE OR REPLACE VIEW p68s3_input AS "
                + view_sql("postgres", "token_mismatch"),
            )
            config["definition"] = product_definition(resources)
        if case == "source_error_cleanup":
            manager(resources, "CREATE VIEW p68s3_fault AS SELECT * FROM p68s3_input")
            manager(resources, "GRANT SELECT ON p68s3_fault TO pietto_query")
        observed_control = []

        def dispatch(message, p):
            if message["event"] == "remove_fault":
                manager(resources, "DROP VIEW p68s3_fault")
                s01._send_control(p, {"removed": True})
                observed_control.append(
                    {"event": "owned_fault_view_removed", "session": message["session"]}
                )
            elif message["event"] == "blocking_ready":
                manager(resources, "BEGIN")
                manager(resources, "LOCK TABLE p68s3_left IN ACCESS EXCLUSIVE MODE")
                s01._send_control(p, {"lock_held": True})
                until = time.monotonic() + 10
                seen = []
                while time.monotonic() < until:
                    manager(resources, "SELECT pg_catalog.pg_stat_clear_snapshot()")
                    seen = manager(
                        resources,
                        f"SELECT pid,state,wait_event_type,query FROM pg_stat_activity WHERE pid={int(message['session'])}",
                    )
                    if (
                        seen
                        and seen[0][1:3] == ["active", "Lock"]
                        and seen[0][3] == message["sql"]
                    ):
                        break
                    time.sleep(0.01)
                else:
                    save(
                        directory / (PREFIX + "blocked-observation-" + case + ".json"),
                        {
                            "session": message["session"],
                            "sql": message["sql"],
                            "last_observation": seen,
                            "observed": False,
                        },
                    )
                    raise TimeoutError("owned blocked query not observed")
                observed_control.append(
                    {
                        "event": "native_execute_lock_observed",
                        "session": message["session"],
                        "observation": seen,
                    }
                )
                if message["cancel"]:
                    s01._send_control(p, {"cancel": True})
            else:
                raise ValueError("unknown product control")

        try:
            observed = child(
                dict(
                    config,
                    case=case,
                    origin="installed" if case == "installed_normal" else "source",
                    directory=str(directory / (PREFIX + "product-" + case)),
                ),
                directory,
                dispatch_hook=dispatch,
            )
            result[case] = observed
            result[case]["manager_control"] = observed_control
            session = observed["data"]["session_id"]
            manager(resources, "SELECT pg_catalog.pg_stat_clear_snapshot()")
            result[case]["remaining_session"] = (
                []
                if session is None
                else manager(
                    resources,
                    f"SELECT pid FROM pg_stat_activity WHERE pid={int(session)}",
                )
            )
        finally:
            if case in ("blocked_cancel", "deadline"):
                manager(resources, "ROLLBACK")
            if case == "cap_expired":
                manager(resources, "UPDATE p68s3_version SET active=1")
            if case == "cap_token":
                manager(
                    resources,
                    "CREATE OR REPLACE VIEW p68s3_input AS " + view_sql("postgres"),
                )
                config["definition"] = definition
        save(directory / (PREFIX + "product-" + case + ".json"), result[case])
    return result
