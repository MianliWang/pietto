"""Explicit S04 lab: owned PG fixture, source/wheel witnesses, data-only checker."""

import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice04-"


def load(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


s01 = load("s04_s01", ROOT / "scripts/phase68_executor_premise.py")
s03 = load("s04_s03", ROOT / "tests/_pietto_phase68_slice3_probe.py")


def template(directory, source=None, *, target="postgres", lower=None, upper=None):
    probe = load("s04_emission", ROOT / "tests/_pietto_phase66_sql_emission_probe.py")
    product = load("s04_result", ROOT / "tests/_pietto_phase67_result_product_probe.py")
    from pietto._project.project_execution_template import prepare_template

    limits = {} if lower is None else dict(lower=lower, upper=upper)
    contract = json.loads(product.emission_input(target, **limits))
    contract["environment"] += [
        dict(
            key="identifier_case",
            scope="statement",
            value="quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        ),
        dict(
            key="parameter_protocol",
            scope="statement",
            value="postgres_extended" if target == "postgres" else "mysql_prepared",
        ),
    ]
    checked, outcome = probe.build_case(
        directory,
        source
        or product.source(target).replace(
            "    select:", "    where id > 1\n    select:"
        ),
        json.dumps(contract),
        "bind_safe_literals",
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome
    return prepare_template(outcome.artifact)


# Independent fixture oracle: exact integers, NULL and bag multiplicity.
ROWS = (
    (-1, 1),
    (0, 0),
    (2, None),
    (5, 50),
    (9007199254740993, None),
    (9007199254740993, None),
    (9007199254740993, -9007199254740993),
)
VALUES = {
    "A": 1,
    "B": 5,
    "A_again": 1,
    "empty": 9223372036854775807,
    "mutated": 1,
    "cancel": 1,
    "consumer_error": 1,
}
SQL = 'WITH "p0" ("c0", "c1") AS (SELECT "s0"."id" AS "c0", "s0"."other" AS "c1" FROM "public"."rows" AS "s0" WHERE ("s0"."id" > CAST($1 AS pg_catalog.int8))) SELECT "t1"."c0" AS "renamed", "t1"."c1" AS "other" FROM "p0" AS "t1"'


def worker(config):
    if config["origin"] == "source":
        sys.path.insert(0, str(ROOT / "src"))
    pa = importlib.import_module("pyarrow")
    from pietto._project import project_execution as ex
    from pietto._project import project_execution_postgres as pg
    from pietto._project.project_execution_template import bind_values, BindingError
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    directory = Path(config["directory"])
    directory.mkdir()
    t = template(directory / "compiled")
    a = bind_values(t, ((t.slots[0], 1),))
    b = bind_values(t, ((t.slots[0], 5),))
    empty = bind_values(t, ((t.slots[0], VALUES["empty"]),))
    supplied = [[t.slots[0], 1]]
    captured = bind_values(t, supplied)
    supplied[0][1] = 9007199254740993
    supplied.clear()
    invalid = None
    try:
        bind_values(t, ((t.slots[0], True),))
    except BindingError as error:
        invalid = str(error)
    bindings = {
        "A": a,
        "B": b,
        "A_again": a,
        "empty": empty,
        "mutated": captured,
        "cancel": a,
        "consumer_error": a,
    }
    results = []
    access = ex.PostgresAccess(
        "127.0.0.1",
        config["port"],
        "phase66",
        "pietto_query",
        config["password"],
        "disable",
    )
    for case in config["cases"]:
        accepted = bindings[case]
        request = ex.prepare_bound_execution(
            accepted, access, limits=ex.ExecutionLimits(batch_rows=2)
        )
        stream = pg.PostgresExecution(request)
        submitted, rows, schemas = [], [], []
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
                    dict(
                        sql=frame.f_locals.get("query"),
                        arguments=[
                            s01.scalar(v) for v in (frame.f_locals.get("params") or ())
                        ],
                        prepare=frame.f_locals.get("prepare"),
                    )
                )

        caught, cancel = None, None
        try:
            sys.setprofile(observe)
            with stream:
                for batch in stream:
                    with batch:
                        actual = pa.record_batch(batch)
                        schemas.append(
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
                    if case == "cancel":
                        cancel = stream.cancel()
                    if case == "consumer_error":
                        raise ValueError("owned consumer error")
        except (ValueError, ex.ExecutionError) as error:
            caught = type(error).__name__
        finally:
            sys.setprofile(old_profile)
            stream.close()
        results.append(
            dict(
                case=case,
                values=[s01.scalar(v) for v in accepted.values],
                public=json.loads(
                    serialize_project_sql_emission(
                        EmissionOutcome("VERIFIED", (), accepted.artifact)
                    )
                ),
                sql=accepted.artifact.rendered.sql.decode(),
                submissions=submitted,
                rows=rows,
                schemas=schemas,
                bound_schema=None
                if stream._payloads is None
                else [
                    [f.name, str(f.type), f.nullable]
                    for f in stream._payloads.binding.schema
                ],
                metadata=stream.actual_metadata,
                outcome=asdict(stream.outcome),
                session=stream.session_id,
                context=stream.context,
                control_joined=stream.control_joined,
                cancel=cancel,
                caught=caught,
            )
        )
    origins = {}
    for name, module in tuple(sys.modules.items()):
        if name == "pietto" or name.startswith("pietto."):
            filename = getattr(module, "__file__", None)
            if filename:
                path = Path(filename).resolve()
                origins[name] = dict(
                    path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                )
    return dict(
        origin=config["origin"],
        prefix=sys.prefix,
        results=results,
        origins=origins,
        invalid=invalid,
    )


def check_observation(data, origin, cases, prefix):
    """Consume values, actual submits, public checks, full rows and terminals."""
    from collections import Counter

    probe = load("s04_emission", ROOT / "tests/_pietto_phase66_sql_emission_probe.py")
    if (
        data["origin"] != origin
        or data["prefix"] != str(prefix)
        or data["invalid"] != "BINDING_VALUE:0:Int"
    ):
        raise ValueError("origin or rejected input")
    if [r["case"] for r in data["results"]] != list(cases):
        raise ValueError("case inventory")
    attempts, sessions = set(), set()
    for result in data["results"]:
        case = result["case"]
        expected = [{"kind": "int", "value": str(VALUES[case])}]
        if result["values"] != expected or result["sql"] != SQL:
            raise ValueError("binding value or original SQL")
        document = probe.decode_public(json.dumps(result["public"]).encode())
        if document["sql"] != SQL or probe.decoded_arguments(document) != (
            VALUES[case],
        ):
            raise ValueError("native use correspondence")
        if result["submissions"] != [dict(sql=SQL, arguments=expected, prepare=True)]:
            raise ValueError("actual native submit")
        if result["context"] != [
            "pietto_query",
            "repeatable read",
            "on",
            "UTF8",
            "pg_catalog",
        ]:
            raise ValueError("fresh execution context")
        if result["bound_schema"] != [
            ["renamed", "int64", False],
            ["other", "int64", True],
        ]:
            raise ValueError("checked empty/result schema")
        if result["metadata"] != [["renamed", 20, None], ["other", 20, None]]:
            raise ValueError("native metadata")
        if any(
            s != [["renamed", "int64", False], ["other", "int64", True]]
            for s in result["schemas"]
        ):
            raise ValueError("checked consumer schema")
        out = result["outcome"]
        if (
            out["rows"] != len(result["rows"])
            or out["batches"] != (out["rows"] + 1) // 2
            or len(result["schemas"]) != out["batches"]
        ):
            raise ValueError("checked batch denominator")
        if (
            out["attempt"] in attempts
            or result["session"] in sessions
            or not result["session"]
        ):
            raise ValueError("fresh attempt/session")
        attempts.add(out["attempt"])
        sessions.add(result["session"])
        if (
            not result["control_joined"]
            or out["cleanup"] != "CLOSED"
            or out["cleanup_failures"]
        ):
            raise ValueError("cleanup")
        actual = Counter(json.dumps(row, sort_keys=True) for row in result["rows"])
        full = Counter(
            json.dumps([s01.scalar(v) for v in row], sort_keys=True)
            for row in ROWS
            if row[0] > VALUES[case]
        )
        if case in ("cancel", "consumer_error"):
            if (
                sum(actual.values()) != 2
                or actual - full
                or out["transaction"] != "ROLLBACK_ACK"
                or out["delivery"] == "COMPLETE"
            ):
                raise ValueError("control terminal")
            cancel = case == "cancel"
            if (
                out["source"] != ("FAILED" if cancel else "EARLY_CLOSE")
                or out["delivery"] != "FAILED"
                or out["primary"]
                != dict(
                    phase="read" if cancel else "consumer",
                    kind="ExecutionError" if cancel else "ValueError",
                    sqlstate=None,
                )
                or (out["cancel_requested"], out["cancel_sent"], out["cancel_observed"])
                != (cancel, cancel, False)
                or result["cancel"]
                != (
                    dict(requested=True, sent=True, observed=False, late=False)
                    if cancel
                    else None
                )
                or result["caught"] != ("ExecutionError" if cancel else "ValueError")
            ):
                raise ValueError("control terminal identity")
        elif (
            actual != full
            or result["caught"] is not None
            or out["source"] != "EOF"
            or out["transaction"] != "COMMIT_ACK"
            or out["delivery"] != "COMPLETE"
            or out["rows"] != sum(full.values())
            or out["primary"] is not None
            or any(
                out[k] for k in ("cancel_requested", "cancel_sent", "cancel_observed")
            )
            or result["cancel"] is not None
        ):
            raise ValueError("result or terminal")
    for required in (
        "project_execution_template",
        "project_execution_binding_verification",
        "project_execution_projection",
        "project_execution_postgres",
        "project_execution_reader",
    ):
        if "pietto._project." + required not in data["origins"]:
            raise ValueError("missing production origin")
    for name, item in data["origins"].items():
        path = Path(item["path"])
        if origin == "source":
            if not path.is_relative_to(ROOT / "src/pietto"):
                raise ValueError("foreign source origin")
        elif not path.is_relative_to(prefix) or "site-packages" not in path.parts:
            raise ValueError("checkout installed origin")
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]
        ):
            raise ValueError("origin bytes")


def child(config, directory):
    process = subprocess.Popen(
        [sys.executable, "-B", str(ROOT / "scripts/phase68_slice4_probe.py"), "worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
    )
    journal = directory / (PREFIX + "children.jsonl")
    with journal.open("a") as f:
        f.write(
            json.dumps(
                dict(event="registered", pid=process.pid, origin=config["origin"])
            )
            + "\n"
        )
    messages = []
    try:
        s01._pump_child(
            process, lambda value: messages.append(value), initial=config, seconds=180
        )
        if len(messages) != 1 or messages[0]["event"] != "result":
            raise ValueError("child observation")
        data = messages[0]["data"]
        s03.save(directory / (PREFIX + config["origin"] + "-raw.json"), data)
        check_observation(data, config["origin"], config["cases"], Path(sys.prefix))
        return dict(
            pid=process.pid,
            exit=process.returncode,
            reaped=process.poll() is not None,
            cases=config["cases"],
        )
    finally:
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream:
                stream.close()
        with journal.open("a") as f:
            f.write(
                json.dumps(dict(event="reaped", pid=process.pid, exit=process.poll()))
                + "\n"
            )


def main():
    if sys.argv[1:] == ["worker"]:
        print(
            json.dumps(
                dict(event="result", data=worker(json.loads(sys.stdin.readline())))
            ),
            flush=True,
        )
        return
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("positive", "campaign"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--tree", required=True)
    args = parser.parse_args()
    args.directory.mkdir(mode=0o700)
    started = time.monotonic()
    report = dict(tree=args.tree, action=args.action, complete=False, observations={})
    resources = None
    try:
        report["runtime"] = s01.runtime_identity()
        if (
            report["runtime"]["versions"]
            != s01.helper("_pietto_phase68_executor_cases").PINS
        ):
            raise ValueError("changed pins")
        pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
        resources = s01.helper("_pietto_target_conformance_resources").Resources(
            "postgres", pins["targets"]["postgres"], args.directory
        )
        s03.charge(args.ledger, "source_db_lifecycle_starts", "S04 " + args.action)
        resources.acquire()
        s03.manager(resources, 'CREATE TABLE "rows"(id BIGINT NOT NULL,other BIGINT)')
        with resources.manager.cursor() as cursor:
            cursor.executemany('INSERT INTO "rows" VALUES ($1,$2)', ROWS)
        for sql, secret in resources.role_statements():
            s03.manager(resources, sql)
        report["server"] = s03.manager(resources, "SELECT version()")
        cases = ("A",) if args.action == "positive" else tuple(VALUES)
        for origin in (
            ("source",) if args.action == "positive" else ("source", "installed")
        ):
            config = dict(
                origin=origin,
                cases=cases,
                port=resources.port,
                password=resources._passwords[1],
                directory=str(args.directory / (PREFIX + origin + "-work")),
            )
            report["observations"][origin] = child(config, args.directory)
        report["complete"] = True
    finally:
        if resources is not None:
            report["cleanup"] = resources.cleanup()
            report["resource_events"] = resources.events
        report["seconds"] = time.monotonic() - started
        s03.save(args.directory / (PREFIX + "report.json"), report)
    if not report["complete"] or report.get("cleanup", {}).get("status") != "success":
        raise ValueError("incomplete S04 campaign")
    print(json.dumps(dict(complete=report["complete"], seconds=report["seconds"])))
