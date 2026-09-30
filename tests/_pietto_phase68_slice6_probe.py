"""Explicit bounded native acquisition; no database work during pytest/import."""

from pathlib import Path
from dataclasses import asdict
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice06-"
_spec = importlib.util.spec_from_file_location(
    "_s06_transport", ROOT / "scripts/phase68_executor_premise.py"
)
assert _spec is not None and _spec.loader is not None
s01 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s01)


def ledger_event(path, event, **charges):
    value = json.loads(path.read_text())
    for name, amount in charges.items():
        value["used"][name] += amount
        if value["used"][name] > value["ceilings"][name]:
            raise ValueError("S06 action ceiling: " + name)
    value["events"].append(event)
    path.write_text(json.dumps(value, indent=2) + "\n")


def register(path, resource):
    value = json.loads(path.read_text())
    value["resources"].append(resource)
    path.write_text(json.dumps(value, indent=2) + "\n")


def quoted(name, target):
    q = '"' if target == "postgres" else "`"
    return q + name.replace(q, q * 2) + q


def manager(resources, sql, arguments=()):
    if resources.target == "postgres":
        with resources.manager.cursor() as cursor:
            cursor.execute(sql, arguments or None)
            return cursor.fetchall() if cursor.description else []
    if arguments:
        from _pietto_mysql_native_prepared import NativeStatement

        statement = NativeStatement(resources.manager)
        try:
            statement.prepare(sql)
            statement.execute(arguments)
            if statement.columns:
                rows, _ = resources.manager.get_rows(
                    binary=True, columns=statement.columns
                )
                return rows
            return []
        finally:
            statement.close()
    with resources.manager.cursor() as cursor:
        cursor.execute(sql)
        return cursor.fetchall() if cursor.description else []


def setup(resources):
    """Existing literal fixtures, with owned retained views and composite tokens."""
    import _pietto_target_conformance_cases as fixtures
    import _pietto_phase68_slice5_probe as previous
    import _pietto_phase68_slice6_cases as cases

    target = resources.target
    for sql, args in (
        fixtures.emission_setup(target)
        + fixtures.native_setup(target)
        + fixtures.row_domain_setup(target)
    ):
        manager(resources, sql, args)
    previous.setup_seven(resources)
    relations = set()
    for case, variant in cases.CASES:
        if case == "R2_seven":
            relations.add(
                ("public" if target == "postgres" else "phase66", "p68seven" + variant)
            )
            continue
        item = cases.fixture(target, case, variant)
        for source in json.loads(item["contract"])["sources"]:
            relations.add((source["relation"]["namespace"], source["relation"]["name"]))
    if target == "postgres":
        manager(
            resources,
            "CREATE FUNCTION public.p68_r2_immutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable owned source'; END $$",
        )
    providers = []
    for index, (namespace, name) in enumerate(sorted(relations)):
        relation = quoted(namespace, target) + "." + quoted(name, target)
        backing = "p68_r2_base_" + str(index)
        registry = "p68_r2_registry_" + str(index)
        if target == "postgres":
            manager(
                resources,
                f"ALTER TABLE {relation} ADD COLUMN p68_raw_id BIGINT GENERATED ALWAYS AS IDENTITY",
            )
            manager(
                resources, f"ALTER TABLE {relation} RENAME TO {quoted(backing, target)}"
            )
            body = f"SELECT b.*,((p68_raw_id-1)%2)::bigint AS p68_part,((p68_raw_id-1)/2)::bigint AS p68_lid FROM {quoted(namespace, target)}.{quoted(backing, target)} AS b"
            if name == "phase66 part":
                body = f"SELECT b.*,CAST(id AS BIGINT) AS p68_part,p68_raw_id AS p68_lid FROM {quoted(namespace, target)}.{quoted(backing, target)} AS b"
            manager(resources, f"CREATE VIEW {relation} AS {body}")
            manager(
                resources,
                f"CREATE TRIGGER p68_r2_immutable BEFORE INSERT OR UPDATE OR DELETE ON {quoted(namespace, target)}.{quoted(backing, target)} FOR EACH ROW EXECUTE FUNCTION public.p68_r2_immutable()",
            )
            manager(resources, "SET search_path=pg_catalog")
            definition = manager(
                resources,
                "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
                (relation,),
            )[0][0]
        else:
            manager(
                resources,
                f"ALTER TABLE {relation} ADD COLUMN p68_raw_id BIGINT NOT NULL AUTO_INCREMENT, ADD KEY p68_r2_source_key(p68_raw_id)",
            )
            manager(
                resources,
                f"RENAME TABLE {relation} TO {quoted(namespace, target)}.{quoted(backing, target)}",
            )
            body = f"SELECT b.*,CAST((p68_raw_id-1)%2 AS SIGNED) AS p68_part,CAST((p68_raw_id-1) DIV 2 AS SIGNED) AS p68_lid FROM {quoted(namespace, target)}.{quoted(backing, target)} AS b"
            if name == "phase66 part":
                body = f"SELECT b.*,CAST(id AS SIGNED) AS p68_part,p68_raw_id AS p68_lid FROM {quoted(namespace, target)}.{quoted(backing, target)} AS b"
            manager(resources, f"CREATE VIEW {relation} AS {body}")
            for action in ("INSERT", "UPDATE", "DELETE"):
                trigger = f"p68_r2_{index}_{action.lower()}"
                manager(
                    resources,
                    f"CREATE TRIGGER {quoted(trigger, target)} BEFORE {action} ON {quoted(namespace, target)}.{quoted(backing, target)} FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='immutable owned source'",
                )
            definition = manager(resources, "SHOW CREATE VIEW " + relation)[0][1]
        qualified_registry = quoted(namespace, target) + "." + quoted(registry, target)
        manager(
            resources,
            "CREATE TABLE "
            + qualified_registry
            + "(provider VARCHAR(64),version_tag VARCHAR(32),active INTEGER,revision VARCHAR(32))",
        )
        provider = "p68-provider-" + str(index)
        manager(
            resources,
            "INSERT INTO " + qualified_registry + f" VALUES('{provider}','v1',1,'r1')",
        )
        providers.append(
            dict(
                namespace=namespace,
                name=name,
                backing=backing,
                registry=registry,
                provider=provider,
                version="v1",
                revision="r1",
                definition=definition,
                view_sql=body,
                tokens=["p68_part", "p68_lid"],
            )
        )
    for sql, _ in resources.role_statements():
        manager(resources, sql)
    if target == "mysql":
        manager(resources, "GRANT SHOW VIEW ON phase66.* TO 'pietto_query'@'%'")
    return providers


def metadata_description(raw, route):
    if route == "postgres_rows":
        return tuple(
            SimpleNamespace(
                name=m[0], type_code=m[1], precision=m[4], scale=m[5], null_ok=m[6]
            )
            for m in raw["metadata"]
        )
    if route == "postgres_adbc":
        return tuple(raw["arrow_schema"])
    return tuple(tuple(m) for m in raw["metadata"])


def bridge_admission(driver, query):
    from pietto._project.project_execution_source import (
        ObservedSource,
        admit_observed_sources,
    )
    from pietto._project.project_result_output import source_read_columns

    target, route = driver.target, driver.route
    records = []
    driver.source_queries = records

    def read(sql, args=(), *, copy=False):
        raw, values = driver.query(sql, args, use_copy=copy)
        records.append(raw)
        if raw.get("error") or raw["statement_cleanup"] != "close_returned":
            raise ValueError("source observation query failed")
        return raw, tuple(tuple(v) for v in values)

    if target == "postgres":
        driver.control("SET search_path=pg_catalog")
    driver.control(
        "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
        if target == "postgres"
        else "START TRANSACTION READ ONLY"
    )
    driver.refined_transaction_open = True
    if target == "postgres":
        _, ctx = read(
            "SELECT current_setting('server_version_num'),current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_user,pg_backend_pid()"
        )
        version, isolation, readonly, encoding, role, session = ctx[0]
        version = int(version)
        environment = (
            f"{version // 10000}.{version % 10000}",
            isolation,
            readonly == "on",
            encoding,
        )
    else:
        raw, ctx = read(
            "SELECT VERSION(),@@transaction_isolation,@@character_set_connection,CURRENT_USER(),CONNECTION_ID(),@@cte_max_recursion_depth,CURRENT_ROLE()"
        )
        version, isolation, encoding, role, session, recursion_limit, active_roles = (
            ctx[0]
        )
        status = raw["native"]["terminal"]["packet"]["status_flag"]
        environment = (
            version,
            isolation.lower().replace("-", " "),
            bool(status & 8192),
            encoding,
            recursion_limit,
            active_roles,
        )
    driver.observed_session = session
    driver.observed_environment = environment
    observations = []
    reads = source_read_columns(query.output)
    for requirement, names in zip(query.sources, reads, strict=True):
        relation = (
            quoted(requirement.source.namespace, target)
            + "."
            + quoted(requirement.source.name, target)
        )
        registry = (
            quoted(requirement.registry_namespace, target)
            + "."
            + quoted(requirement.registry_name, target)
        )
        _, registered = read(
            "SELECT provider,version_tag,active,revision FROM " + registry + " LIMIT 2"
        )
        if target == "postgres":
            _, defined = read(
                "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)", (relation,)
            )
            definition = defined[0][0]
        else:
            _, defined = read("SHOW CREATE VIEW " + relation)
            definition = defined[0][1]
        columns = ",".join(quoted(n, target) for n in requirement.token_columns)
        token_meta, _ = read(
            "SELECT " + columns + " FROM " + relation + " LIMIT 0", copy=True
        )
        token_types = (
            tuple(m["type"] for m in token_meta["arrow_schema"])
            if route == "postgres_adbc"
            else tuple((m[1], m[7]) for m in token_meta["metadata"])
        )
        nulls = " OR ".join(
            quoted(n, target) + " IS NULL" for n in requirement.token_columns
        )
        _, collisions = read(
            "SELECT "
            + columns
            + " FROM "
            + relation
            + " GROUP BY "
            + columns
            + " HAVING "
            + nulls
            + " OR COUNT(*)<>1 LIMIT 1"
        )
        schema = ()
        if names:
            selected = ",".join(
                quoted(n, target) + " AS " + quoted("__pietto_source_" + str(i), target)
                for i, n in enumerate(names)
            )
            schema_raw, _ = read(
                "SELECT " + selected + " FROM " + relation + " LIMIT 0", copy=True
            )
            schema = (
                tuple(schema_raw["arrow_schema"])
                if route == "postgres_adbc"
                else tuple(tuple(m) for m in schema_raw["metadata"])
            )
        collations = ()
        if target == "postgres":
            _, collations = read(
                "SELECT a.attname,c.collname FROM pg_catalog.pg_attribute AS a JOIN pg_catalog.pg_collation AS c ON c.oid=a.attcollation WHERE a.attrelid=$1::regclass AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",
                (relation,),
            )
        observations.append(
            ObservedSource(
                requirement,
                route,
                session,
                role,
                registered,
                definition,
                token_types,
                collisions,
                schema,
                collations,
                ("NORMAL",) * 4 + (("NORMAL" if names else "NOT_REQUIRED"), "NORMAL"),
            )
        )
    admission = admit_observed_sources(
        query.sources,
        reads,
        tuple(observations),
        route=route,
        session_id=session,
        role=role,
        environment=environment,
    )
    return admission, records


def adbc_page(driver, page, query):
    """Typed ADBC binding, including NULL/Decimal continuation controls."""
    pa = importlib.import_module("pyarrow")

    native = page.native
    coordinates = query.units[-1].order_coordinates + query.units[-1].coordinates
    kinds = {}
    for use in native.uses:
        if use.domain == "original":
            kind = use.owner.tag.value
        else:
            kind = (
                "Int"
                if page.frontier is None or use.owner == len(coordinates)
                else coordinates[use.owner].tag
            )
        kinds[use.index] = kind
    types = {
        "Int": pa.int64(),
        "Bool": pa.bool_(),
        "Float": pa.float64(),
        "Text": pa.string(),
        "Decimal": pa.string(),
    }
    bound = pa.record_batch(
        [
            pa.array([v], type=types[kinds[i + 1]])
            for i, v in enumerate(native.arguments)
        ],
        names=["p" + str(i) for i in range(len(native.arguments))],
    )
    raw: dict[str, Any] = dict(
        sql=native.sql.decode(),
        parameters=[s01.scalar(v) for v in native.arguments],
        api_calls=[],
        metadata=[],
        arrow_schema=[],
        actual=[],
        raw_actual=[],
        pulls=[],
        source_terminal="NOT_OBSERVED",
        statement_cleanup="NOT_STARTED",
        options={"use_copy": True, "batch_size_hint_bytes": 1},
    )
    cursor = driver.connection.cursor(
        adbc_stmt_kwargs={
            "adbc.postgresql.use_copy": True,
            "adbc.postgresql.batch_size_hint_bytes": 1,
        }
    )
    previous = sys.getprofile()

    def observe(frame, event, result):
        if previous:
            previous(frame, event, result)
        if event != "call" or frame.f_locals.get("self") is not cursor:
            return
        name = frame.f_code.co_name
        if name not in ("execute", "_bind"):
            return
        values = frame.f_locals.get("parameters", frame.f_locals.get("params"))
        data = (
            [s01.scalar(values.column(i)[0].as_py()) for i in range(values.num_columns)]
            if hasattr(values, "num_columns")
            else [s01.scalar(v) for v in (values or ())]
        )
        raw["api_calls"].append(
            dict(
                method=name,
                sql=frame.f_locals.get("operation", frame.f_locals.get("query")),
                values=data,
            )
        )

    rows = []
    try:
        sys.setprofile(observe)
        cursor.execute(native.sql.decode(), bound)
        reader = cursor.fetch_record_batch()
        raw["arrow_schema"] = [
            dict(
                ordinal=i,
                name=f.name,
                type=str(f.type),
                nullable=f.nullable,
                metadata={k.hex(): v.hex() for k, v in (f.metadata or {}).items()},
            )
            for i, f in enumerate(reader.schema)
        ]
        for batch in reader:
            raw["pulls"].append(batch.num_rows)
            rows.extend(
                tuple(batch.column(i)[j].as_py() for i in range(batch.num_columns))
                for j in range(batch.num_rows)
            )
            if len(rows) > page.size:
                raise ValueError("native page bound")
        raw["source_terminal"] = "NORMAL"
        raw["actual"] = [[s01.scalar(v) for v in row] for row in rows]
        raw["raw_actual"] = raw["actual"]
    finally:
        sys.setprofile(previous)
        cursor.close()
        raw["statement_cleanup"] = "close_returned"
    return raw, tuple(rows)


def observation_data(admission):
    return dict(
        route=admission.route,
        session=admission.session_id,
        role=admission.role,
        environment=admission.environment,
        sources=[
            dict(
                position=i,
                registry=o.registry,
                definition=o.definition,
                token_types=o.token_types,
                collision_rows=o.collision_rows,
                schema=o.schema,
                collations=o.collations,
                terminals=o.terminals,
            )
            for i, o in enumerate(admission.observations)
        ],
    )


def use_data(page, query):
    slots = query.original.request.plan.literal_slots
    return [
        dict(
            domain=u.domain,
            index=u.index,
            value=s01.scalar(u.value),
            owner=next(i for i, s in enumerate(slots) if s is u.owner)
            if u.domain == "original"
            else u.owner,
            original=None if u.original is None else u.original.ordinal,
        )
        for u in page.native.uses
    ]


def page_data(page, query) -> dict[str, Any]:
    return dict(
        ordinal=page.ordinal,
        size=page.size,
        frontier=None
        if page.frontier is None
        else [s01.scalar(v) for v in page.frontier],
        uses=use_data(page, query),
        erasure=[position for position, _ in query.erasure],
    )


def collect_pg(query, config, *, size=2, prefix_pages=None, control=None):
    pa = importlib.import_module("pyarrow")
    from pietto._project.project_execution import PostgresAccess, ExecutionLimits
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_refinement_enumeration import prepare_refined_execution

    request = prepare_refined_execution(
        query,
        PostgresAccess(
            "127.0.0.1",
            config["port"],
            "phase66",
            "pietto_query",
            config["password"],
            "disable",
        ),
        limits=ExecutionLimits(batch_rows=size, seconds=75),
    )
    stream = PostgresExecution(request)
    report: dict[str, Any] = dict(
        pages=[], rows=[], schema=None, attempt=stream.attempt, source_queries=[]
    )
    control_cursors: dict[int, dict[str, Any]] = {}
    previous = sys.getprofile()

    def observe(frame, event, value):
        if previous:
            previous(frame, event, value)
        candidate = frame.f_locals.get("self")
        if candidate is not stream._cursor:
            if (
                stream._connection is not None
                and getattr(candidate, "connection", None) is stream._connection
            ):
                if event == "call" and frame.f_code.co_name == "execute":
                    item = dict(
                        sql=frame.f_locals.get("query"),
                        arguments=[
                            s01.scalar(v) for v in (frame.f_locals.get("params") or ())
                        ],
                    )
                    report["source_queries"].append(item)
                    control_cursors[id(candidate)] = item
                elif (
                    event == "return"
                    and frame.f_code.co_name in ("fetchone", "fetchall")
                    and id(candidate) in control_cursors
                ):
                    observed = (
                        ([] if value is None else [value])
                        if frame.f_code.co_name == "fetchone"
                        else value
                    )
                    control_cursors[id(candidate)]["rows"] = [
                        [s01.scalar(v) for v in row] for row in observed
                    ]
            return
        if event == "call" and frame.f_code.co_name == "execute":
            page = stream.last_page
            item = page_data(page, query)
            item.update(
                sql=frame.f_locals["query"],
                arguments=[s01.scalar(v) for v in (frame.f_locals.get("params") or ())],
                api="psycopg.RawCursor.execute",
                prepare=frame.f_locals.get("prepare"),
                terminal="NOT_OBSERVED",
                raw_rows=[],
            )
            report["pages"].append(item)
        elif event == "return" and frame.f_code.co_name == "fetchall":
            item = report["pages"][-1]
            item.update(
                raw_rows=[[s01.scalar(v) for v in row] for row in value],
                metadata=stream.actual_metadata_details,
                terminal="NORMAL",
                buffered_rows=stream.native_buffered_rows,
            )

    try:
        sys.setprofile(observe)
        with stream:
            report["admission"] = observation_data(stream.source_admissions)
            for batch in stream:
                with batch:
                    array = pa.record_batch(batch)
                    report["schema"] = [
                        [f.name, str(f.type), f.nullable] for f in array.schema
                    ]
                    report["rows"].extend(
                        [
                            [
                                s01.scalar(array.column(i)[j].as_py())
                                for i in range(array.num_columns)
                            ]
                            for j in range(array.num_rows)
                        ]
                    )
                assert stream.enumeration is not None
                report["pages"][-1]["accepted_progress"] = stream.enumeration.progress
                if control == "cancel":
                    stream.cancel()
                elif control == "consumer_error":
                    raise ValueError("owned consumer failure")
                if prefix_pages is not None and len(report["pages"]) >= prefix_pages:
                    break
    except BaseException as error:
        report["failure"] = dict(kind=type(error).__name__, category=str(error))
    finally:
        sys.setprofile(previous)
        stream.close()
        report.update(
            outcome=asdict(stream.outcome),
            session=stream.session_id,
            control_joined=stream.control_joined,
            controls=stream.control_events,
            progress=None
            if stream.enumeration is None
            else stream.enumeration.progress,
        )
        if report["schema"] is None and stream._payloads is not None:
            report["schema"] = [
                [f.name, str(f.type), f.nullable]
                for f in stream._payloads.binding.schema
            ]
    return report


def collect_bridge(query, config, *, size=2, prefix_pages=None, control=None):
    pa = importlib.import_module("pyarrow")
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_refinement_enumeration import Enumeration
    from pietto._project.project_arrow_result import bind_arrow
    from pietto._project.project_arrow_interop import build_managed_batch

    report: dict[str, Any] = dict(
        pages=[], rows=[], schema=None, transaction="NOT_STARTED", cleanup="NOT_STARTED"
    )
    driver = s01.Driver(config)
    try:
        admission, controls = bridge_admission(driver, query)
        report.update(
            admission=observation_data(admission),
            source_queries=controls,
            session=admission.session_id,
            transaction="OPEN",
        )
        enumeration = Enumeration(
            query, admission, limits=ExecutionLimits(batch_rows=size, seconds=75)
        )
        while not enumeration.progress[2]:
            page = enumeration.request_page()
            if config["route"] == "postgres_adbc":
                raw, rows = adbc_page(driver, page, query)
            else:
                raw, rows = driver.query(
                    page.native.sql.decode(), page.native.arguments
                )
                rows = tuple(tuple(r) for r in rows)
            item = page_data(page, query)
            item.update(
                sql=raw["sql"],
                arguments=raw["parameters"],
                raw_rows=raw["actual"],
                metadata=raw.get("arrow_schema", raw["metadata"]),
                raw=raw,
                terminal="NORMAL"
                if not raw.get("error")
                and raw["source_terminal"]
                in ("NORMAL", "native_rowset_eof", "empty_fetchmany")
                else "UNKNOWN",
            )
            report["pages"].append(item)
            checked = enumeration.check_page(
                page,
                metadata_description(raw, config["route"]),
                rows,
                terminal=item["terminal"],
            )
            arrow_binding = bind_arrow(checked.producer)
            report["schema"] = [
                [f.name, str(f.type), f.nullable] for f in arrow_binding.schema
            ]
            if checked.rows:
                with build_managed_batch(arrow_binding, checked.rows) as batch:
                    array = pa.record_batch(batch)
                    report["rows"].extend(
                        [
                            [
                                s01.scalar(array.column(i)[j].as_py())
                                for i in range(array.num_columns)
                            ]
                            for j in range(array.num_rows)
                        ]
                    )
            enumeration.commit_page(checked)
            item["accepted_progress"] = enumeration.progress
            if prefix_pages is not None and len(report["pages"]) >= prefix_pages:
                break
        report["progress"] = enumeration.progress
        complete = enumeration.progress[2]
        driver.control("COMMIT" if complete else "ROLLBACK")
        report["transaction"] = "COMMIT_ACK" if complete else "ROLLBACK_ACK"
    except BaseException as error:
        report["failure"] = dict(kind=type(error).__name__, category=str(error))
        if getattr(driver, "refined_transaction_open", False):
            driver.control("ROLLBACK")
            report["transaction"] = "ROLLBACK_ACK"
    finally:
        report["session"] = getattr(driver, "observed_session", report.get("session"))
        report["source_queries"] = getattr(
            driver, "source_queries", report.get("source_queries", [])
        )
        driver.close()
        report["cleanup"] = "CLOSED"
    return report


def binding_worker(config, directory):
    import _pietto_phase68_slice6_cases as cases
    from pietto._project.project_execution_template import prepare_template, bind_values
    from pietto._project.project_execution_binding_verification import verify_binding
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from pietto._project.project_result_output import prepare_output
    from dataclasses import replace

    seed = cases.original(directory / "seed", config["target"], "R2_bound", "values")
    template = prepare_template(seed)
    if len(template.slots) != 2:
        raise ValueError("bound fixture slot denominator")
    first = bind_values(template, tuple(zip(template.slots, (0, 1), strict=True)))
    second = bind_values(template, tuple(zip(template.slots, (1, 2), strict=True)))
    role = "pietto_query@%" if config["target"] == "mysql" else "pietto_query"
    queries = []
    for binding in (first, second):
        output = prepare_output(binding.artifact, binding=binding)
        queries.append(
            prepare_refinement(
                binding.artifact,
                cases.source_requirements(binding.artifact, config["providers"], role),
                policy=TieRefinement(),
                output=output,
                binding=binding,
            )
        )
    records = []
    for index, (name, query) in enumerate(
        (("A", queries[0]), ("B", queries[1]), ("A_again", queries[0]))
    ):
        collect = collect_pg if config["route"] == "postgres_rows" else collect_bridge
        report = collect(query, config, size=2)
        item = dict(
            case="R2_bound",
            variant=name,
            binding_values=[0, 1] if name != "B" else [1, 2],
            status="FAILED" if report.get("failure") else "OBSERVED",
            report=report,
            original_sql=query.original.rendered.sql.decode(),
            fields=[
                dict(
                    label=c.label,
                    tag=c.realization.tag,
                    storage=c.realization.storage,
                    domain=c.realization.domain,
                    nullable=c.realization.nullable,
                )
                for c in query.output.columns
            ],
        )
        path = directory / (PREFIX + name + ".json")
        path.write_text(json.dumps(item, indent=2) + "\n")
        records.append(
            dict(
                path=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                case="R2_bound",
                variant=name,
                status=item["status"],
            )
        )
    rejected = []
    try:
        bind_values(template, ((template.slots[0], True), (template.slots[1], 1)))
    except ValueError:
        rejected.append("wrong_binding_type")
    item = cases.fixture(config["target"], "R2_bound", "values")
    _, different = cases.emission.build_case(
        directory / "different-limit",
        item["source"].replace("limit 4", "limit 2"),
        item["contract"],
        item["policy"],
    )
    try:
        verify_binding(replace(first, artifact=different.artifact))
    except ValueError:
        rejected.append("structural_limit")
    if rejected != ["wrong_binding_type", "structural_limit"]:
        raise ValueError("bound structural controls")
    result = dict(
        records=records,
        origins=origins(config["origin"]),
        python=sys.version,
        executable=sys.executable,
        pid=os.getpid(),
        mode="binding",
        rejected=rejected,
        same_A_root=True,
    )
    (directory / (PREFIX + "worker.json")).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result


def origins(expected):
    names = {}
    for name, module in sys.modules.items():
        filename = getattr(module, "__file__", None)
        if (name == "pietto" or name.startswith("pietto.")) and type(filename) is str:
            names[name] = str(Path(filename).resolve())
    base = ROOT / "src" if expected == "source" else Path(sys.prefix)
    if not names or any(not Path(path).is_relative_to(base) for path in names.values()):
        raise ValueError("source/installed origin mismatch")
    return {
        name: dict(
            path=path, sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest()
        )
        for name, path in names.items()
    }


def worker(config):
    # Decide package provenance before importing any product owner.
    if config["origin"] == "source":
        sys.path.insert(0, str(ROOT / "src"))
    import _pietto_phase68_slice6_cases as cases
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from pietto._project.project_result_output import prepare_output

    directory = Path(config["directory"])
    directory.mkdir(mode=0o700)
    outputs = []
    mode = config.get("mode", "cases")
    if mode == "binding":
        return binding_worker(config, directory)
    for index, (case, variant) in enumerate(config["cases"]):
        artifact = cases.original(
            directory / ("input-" + str(index)), config["target"], case, variant
        )
        if artifact is None:
            item = dict(case=case, variant=variant, status="ORIGINAL_BLOCKED")
        else:
            role = "pietto_query@%" if config["target"] == "mysql" else "pietto_query"
            requirements = cases.source_requirements(
                artifact, config["providers"], config.get("requirement_role", role)
            )
            if config.get("token_columns"):
                from dataclasses import replace

                requirements = tuple(
                    replace(r, token_columns=tuple(config["token_columns"]))
                    for r in requirements
                )
            output = prepare_output(artifact)
            query = prepare_refinement(
                artifact, requirements, policy=TieRefinement(), output=output
            )
            call = collect_pg if config["route"] == "postgres_rows" else collect_bridge
            report = call(
                query,
                config,
                size=config.get("page_size", 2),
                prefix_pages=1 if mode == "prefix" else None,
                control=config.get("control"),
            )
            item = dict(
                case=case,
                variant=variant,
                status="OBSERVED",
                report=report,
                fields=[
                    dict(
                        label=c.label,
                        tag=c.realization.tag,
                        storage=c.realization.storage,
                        domain=c.realization.domain,
                        nullable=c.realization.nullable,
                    )
                    for c in output.columns
                ],
                original_sql=artifact.rendered.sql.decode(),
            )
            if mode == "resume":
                prefix = config["prefix"]
                raw_prefix = config["prefix_raw"]
                all_raw = [row for page in report["pages"] for row in page["raw_rows"]]
                item["prefix_checked"] = (
                    report["rows"][: len(prefix)] == prefix
                    and all_raw[: len(raw_prefix)] == raw_prefix
                )
                if not item["prefix_checked"]:
                    raise ValueError("prefix correspondence")
            if config.get("expect_failure"):
                item["control"] = config["control_name"]
                item["status"] = (
                    "EXPECTED_REJECTION" if report.get("failure") else "FAILED"
                )
            elif report.get("failure"):
                item["status"] = "FAILED"
        path = directory / (PREFIX + str(index) + ".json")
        path.write_text(json.dumps(item, indent=2) + "\n")
        outputs.append(
            dict(
                path=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                case=case,
                variant=variant,
                status=item["status"],
            )
        )
    result = dict(
        records=outputs,
        origins=origins(config["origin"]),
        python=sys.version,
        executable=sys.executable,
        pid=os.getpid(),
        mode=mode,
    )
    (directory / (PREFIX + "worker.json")).write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return result


def session_gone(resources, session):
    observations = []
    for _ in range(20):
        sql = (
            "SELECT COUNT(*) FROM pg_catalog.pg_stat_activity WHERE pid=$1"
            if resources.target == "postgres"
            else "SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=?"
        )
        found = manager(resources, sql, (session,))[0][0]
        observations.append(int(found))
        if found == 0:
            return observations
        time.sleep(0.1)
    raise ValueError("owned native session did not close")


def run_worker(config, ledger, resource, directory):
    from _pietto_target_conformance_resources import clean_environment

    started = time.monotonic()
    register(
        ledger,
        dict(
            kind="native_worker",
            path=config["directory"],
            state="registered",
            operation=config.get("mode", "cases"),
            cases=config["cases"],
        ),
    )
    argv = [
        sys.executable,
        "-B",
        str(ROOT / "scripts/phase68_slice6_probe.py"),
        "worker",
    ]
    ledger_event(
        ledger,
        dict(
            kind="child_intent",
            argv=argv,
            origin=config["origin"],
            route=config["route"],
            directory=config["directory"],
        ),
    )
    input_path = Path(config["directory"]).with_suffix(".input.json")
    register(
        ledger, dict(kind="worker_input", path=str(input_path), state="registered")
    )
    with input_path.open("x") as stream:
        input_path.chmod(0o600)
        json.dump(config, stream)
    child = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        cwd=directory,
        env=clean_environment(),
    )
    ledger_event(
        ledger,
        dict(
            kind="child_registered",
            pid=child.pid,
            directory=config["directory"],
            parent_deadline=180,
        ),
    )
    results = []

    def receive(message):
        if message.get("event") != "result":
            raise ValueError("unknown child message")
        results.append(message["data"])

    try:
        stderr = s01._pump_child(
            child, receive, initial={"input_path": str(input_path)}, seconds=180
        )
        if child.returncode != 0 or len(results) != 1:
            raise ValueError("native worker failed")
        result = results[0]
        result.update(
            exit=child.returncode,
            reaped=child.poll() is not None,
            seconds=time.monotonic() - started,
        )
        result["sessions_gone"] = []
        for item in result["records"]:
            data = Path(item["path"]).read_bytes()
            if hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise ValueError("child record identity")
            report = json.loads(data).get("report")
            if report is not None and report.get("session") is not None:
                result["sessions_gone"].append(
                    dict(
                        session=report["session"],
                        observations=session_gone(resource, report["session"]),
                    )
                )
        (Path(config["directory"]) / (PREFIX + "stderr.txt")).write_bytes(stderr)
        if any(x["status"] == "FAILED" for x in result["records"]):
            result["failed_case"] = True
        return result
    finally:
        input_path.unlink(missing_ok=True)
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        ledger_event(
            ledger,
            dict(
                kind="child_terminal",
                pid=child.pid,
                exit=child.returncode,
                reaped=child.poll() is not None,
                seconds=time.monotonic() - started,
            ),
        )


def campaign(args):
    from _pietto_target_conformance_resources import Resources
    import _pietto_phase68_slice6_cases as cases

    register(
        args.ledger,
        dict(kind="campaign_evidence", path=str(args.directory), state="registered"),
    )
    ledger_event(
        args.ledger,
        dict(kind="complete_live_start", directory=str(args.directory), tree=args.tree),
        complete_s06_live_campaign_starts=1,
    )
    args.directory.mkdir(mode=0o700)
    runtime = s01.runtime_identity()
    if runtime["versions"] != s01.helper("_pietto_phase68_executor_cases").PINS:
        raise ValueError("native profile drift")
    report: dict[str, Any] = dict(
        tree=args.tree,
        runtime=runtime,
        workers=[],
        resources=[],
        bindings=[],
        controls=[],
        fresh=[],
        complete=False,
    )
    if args.reuse_families is not None:
        old_file = args.reuse_families / (PREFIX + "campaign.json")
        old = json.loads(old_file.read_text())
        report["family_reuse"] = dict(
            root=str(args.reuse_families),
            sha256=hashlib.sha256(old_file.read_bytes()).hexdigest(),
            tree=old["tree"],
            reason="Unchanged production/native inputs and source-generated original cases; only the separately unexecuted bound fixture gained its required protocol declaration. Reconsumption required.",
        )
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    started = time.monotonic()
    try:
        for target in ("postgres", "mysql"):
            directory = args.directory / (PREFIX + target)
            register(
                args.ledger,
                dict(
                    kind="mechanism_scratch",
                    path=str(directory),
                    state="registered",
                    purpose="complete native target",
                ),
            )
            directory.mkdir()
            resources = Resources(target, pins["targets"][target], directory)
            register(
                args.ledger,
                dict(
                    kind="database",
                    target=target,
                    nonce=resources.nonce,
                    container=resources.name,
                    network=resources.network_name,
                    path=str(directory),
                    state="registered",
                ),
            )
            ledger_event(
                args.ledger,
                dict(kind="source_db_start", target=target, directory=str(directory)),
                source_db_lifecycle_starts=1,
            )
            state: dict[str, Any] = dict(target=target)
            report["resources"].append(state)
            try:
                resources.acquire()
                providers = setup(resources)
                (directory / (PREFIX + "providers.json")).write_text(
                    json.dumps(providers, indent=2) + "\n"
                )
                routes = (
                    (
                        ("postgres_rows", "source"),
                        ("postgres_rows", "installed"),
                        ("postgres_adbc", "source"),
                    )
                    if target == "postgres"
                    else (("mysql_rows", "source"),)
                )
                for route, origin in routes:
                    for offset in (
                        ()
                        if target == "postgres" and args.reuse_families is not None
                        else range(0, len(cases.CASES), 8)
                    ):
                        root = directory / (
                            PREFIX + route + "-" + origin + "-" + str(offset // 8)
                        )
                        config = dict(
                            target=target,
                            route=route,
                            origin=origin,
                            port=resources.port,
                            password=resources._passwords[1],
                            ca=str(resources.ca_path),
                            directory=str(root),
                            providers=providers,
                            cases=cases.CASES[offset : offset + 8],
                            page_size=3,
                        )
                        worker_report = run_worker(
                            config, args.ledger, resources, directory
                        )
                        report["workers"].append(
                            dict(
                                target=target,
                                route=route,
                                origin=origin,
                                **worker_report,
                            )
                        )
                        (args.directory / (PREFIX + "campaign.json")).write_text(
                            json.dumps(report, indent=2) + "\n"
                        )
                        print(
                            target,
                            route,
                            origin,
                            offset,
                            len(worker_report["records"]),
                            "FAILED"
                            if worker_report.get("failed_case")
                            else "observed",
                            flush=True,
                        )
                for route, origin in routes:
                    config = dict(
                        target=target,
                        route=route,
                        origin=origin,
                        port=resources.port,
                        password=resources._passwords[1],
                        ca=str(resources.ca_path),
                        providers=providers,
                        cases=(("R2_bound", "values"),),
                        mode="binding",
                        directory=str(
                            directory / (PREFIX + route + "-" + origin + "-binding")
                        ),
                    )
                    bound = run_worker(config, args.ledger, resources, directory)
                    report["bindings"].append(
                        dict(target=target, route=route, origin=origin, **bound)
                    )
                    if bound.get("failed_case"):
                        raise ValueError("refined binding cohort failed")
                fresh_routes = (
                    ("postgres_rows", "postgres_adbc")
                    if target == "postgres"
                    else ("mysql_rows",)
                )
                for route in fresh_routes:
                    common = dict(
                        target=target,
                        route=route,
                        origin="source",
                        port=resources.port,
                        password=resources._passwords[1],
                        ca=str(resources.ca_path),
                        providers=providers,
                        cases=(("R2_mixed", "joint"),),
                    )
                    first = run_worker(
                        common
                        | dict(
                            directory=str(directory / (PREFIX + route + "-prefix")),
                            page_size=1,
                            mode="prefix",
                        ),
                        args.ledger,
                        resources,
                        directory,
                    )
                    prefix = json.loads(Path(first["records"][0]["path"]).read_text())[
                        "report"
                    ]
                    if first.get("failed_case") or len(prefix["rows"]) != 1:
                        raise ValueError("prefix capture boundary")
                    suffix = run_worker(
                        common
                        | dict(
                            directory=str(directory / (PREFIX + route + "-resume")),
                            page_size=3,
                            mode="resume",
                            prefix=prefix["rows"],
                            prefix_raw=[
                                r for p in prefix["pages"] for r in p["raw_rows"]
                            ],
                        ),
                        args.ledger,
                        resources,
                        directory,
                    )
                    report["fresh"].append(
                        dict(target=target, route=route, prefix=first, resume=suffix)
                    )
                    if suffix.get("failed_case"):
                        raise ValueError("fresh suffix failed")
                    print(
                        target,
                        route,
                        "fresh process prefix/suffix observed",
                        flush=True,
                    )
                provider = next(p for p in providers if p["name"] == "phase66 source é")
                registry = (
                    quoted(provider["namespace"], target)
                    + "."
                    + quoted(provider["registry"], target)
                )
                relation = (
                    quoted(provider["namespace"], target)
                    + "."
                    + quoted(provider["name"], target)
                )
                control_routes = (
                    ("postgres_rows", "postgres_adbc")
                    if target == "postgres"
                    else ("mysql_rows",)
                )
                for control_name in (
                    "expiry",
                    "revision",
                    "visibility",
                    "role",
                    "component_collision",
                ):
                    if control_name == "expiry":
                        manager(resources, "UPDATE " + registry + " SET active=0")
                    elif control_name == "revision":
                        manager(
                            resources, "UPDATE " + registry + " SET revision='replaced'"
                        )
                    elif control_name == "visibility":
                        manager(
                            resources,
                            "CREATE OR REPLACE VIEW "
                            + relation
                            + " AS "
                            + provider["view_sql"]
                            + " WHERE FALSE",
                        )
                    for route in control_routes:
                        config = dict(
                            target=target,
                            route=route,
                            origin="source",
                            port=resources.port,
                            password=resources._passwords[1],
                            ca=str(resources.ca_path),
                            providers=providers,
                            cases=(("G_emission_table_bag", "bag"),),
                            page_size=2,
                            expect_failure=True,
                            control_name=control_name,
                            directory=str(
                                directory / (PREFIX + route + "-" + control_name)
                            ),
                        )
                        if control_name == "role":
                            config["requirement_role"] = "p68_ungranted_role"
                        if control_name == "component_collision":
                            config["token_columns"] = ["p68_lid"]
                        result = run_worker(config, args.ledger, resources, directory)
                        report["controls"].append(
                            dict(
                                target=target,
                                route=route,
                                control=control_name,
                                **result,
                            )
                        )
                        if result.get("failed_case"):
                            raise ValueError("source damage accepted")
                    if control_name == "expiry":
                        manager(resources, "UPDATE " + registry + " SET active=1")
                    elif control_name == "revision":
                        manager(resources, "UPDATE " + registry + " SET revision='r1'")
                    elif control_name == "visibility":
                        manager(
                            resources,
                            "CREATE OR REPLACE VIEW "
                            + relation
                            + " AS "
                            + provider["view_sql"],
                        )
                with resources.manager.cursor() as probe_cursor:
                    probe_cursor.execute("SELECT * FROM " + relation + " LIMIT 0")
                    raw_columns = [c[0] for c in probe_cursor.description]
                    probe_cursor.fetchall()
                declared = [n for n in raw_columns if n not in ("p68_part", "p68_lid")]
                items = []
                for name in declared:
                    field = "b." + quoted(name, target)
                    if name == "order.id":
                        field = (
                            "CASE WHEN b.p68_raw_id=4 THEN 9223372036854775807 ELSE "
                            + field
                            + " END"
                        )
                    items.append(field + " AS " + quoted(name, target))
                base = (
                    quoted(provider["namespace"], target)
                    + "."
                    + quoted(provider["backing"], target)
                )
                if target == "postgres":
                    items += [
                        "((p68_raw_id-1)%2)::bigint AS p68_part",
                        "((p68_raw_id-1)/2)::bigint AS p68_lid",
                    ]
                else:
                    items += [
                        "CAST((p68_raw_id-1)%2 AS SIGNED) AS p68_part",
                        "CAST((p68_raw_id-1) DIV 2 AS SIGNED) AS p68_lid",
                    ]
                manager(
                    resources,
                    "CREATE OR REPLACE VIEW "
                    + relation
                    + " AS SELECT "
                    + ",".join(items)
                    + " FROM "
                    + base
                    + " AS b",
                )
                changed_definition = (
                    manager(
                        resources,
                        "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
                        (relation,),
                    )[0][0]
                    if target == "postgres"
                    else manager(resources, "SHOW CREATE VIEW " + relation)[0][1]
                )
                changed_providers = [
                    dict(p, definition=changed_definition) if p is provider else p
                    for p in providers
                ]
                for route in control_routes:
                    config = dict(
                        target=target,
                        route=route,
                        origin="source",
                        port=resources.port,
                        password=resources._passwords[1],
                        ca=str(resources.ca_path),
                        providers=changed_providers,
                        cases=(("G_emission_table_bag", "bag"),),
                        page_size=2,
                        expect_failure=True,
                        control_name="late_value",
                        directory=str(directory / (PREFIX + route + "-late_value")),
                    )
                    result = run_worker(config, args.ledger, resources, directory)
                    report["controls"].append(
                        dict(target=target, route=route, control="late_value", **result)
                    )
                    if result.get("failed_case"):
                        raise ValueError("late value violation accepted")
                manager(
                    resources,
                    "CREATE OR REPLACE VIEW "
                    + relation
                    + " AS "
                    + provider["view_sql"],
                )
                if target == "postgres":
                    for control in ("cancel", "consumer_error"):
                        config = dict(
                            target=target,
                            route="postgres_rows",
                            origin="source",
                            port=resources.port,
                            password=resources._passwords[1],
                            ca=str(resources.ca_path),
                            providers=providers,
                            cases=(("R2_mixed", "joint"),),
                            page_size=1,
                            control=control,
                            expect_failure=True,
                            control_name=control,
                            directory=str(
                                directory / (PREFIX + "postgres_rows-" + control)
                            ),
                        )
                        result = run_worker(config, args.ledger, resources, directory)
                        report["controls"].append(
                            dict(
                                target=target,
                                route="postgres_rows",
                                control=control,
                                **result,
                            )
                        )
                        if result.get("failed_case"):
                            raise ValueError("late control accepted")
            finally:
                state["cleanup"] = resources.cleanup()
                ledger_event(
                    args.ledger,
                    dict(
                        kind="source_db_terminal",
                        target=target,
                        cleanup=state["cleanup"],
                    ),
                )
                (args.directory / (PREFIX + "campaign.json")).write_text(
                    json.dumps(report, indent=2) + "\n"
                )
        report["complete"] = not any(w.get("failed_case") for w in report["workers"])
    finally:
        report["seconds"] = time.monotonic() - started
        (args.directory / (PREFIX + "campaign.json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )
    return report


def main():
    if sys.argv[1:] == ["worker"]:
        control = json.loads(sys.stdin.readline())
        input_path = Path(control["input_path"])
        if input_path.stat().st_size > 1024 * 1024:
            raise ValueError("bounded native fixture input")
        config = json.loads(input_path.read_text())
        try:
            result = worker(config)
        except BaseException:
            import traceback

            directory = Path(config["directory"])
            directory.mkdir(mode=0o700, exist_ok=True)
            (directory / (PREFIX + "worker-error.txt")).write_text(
                traceback.format_exc()
            )
            raise
        print(json.dumps(dict(event="result", data=result)), flush=True)
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("campaign",))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--reuse-families", type=Path)
    args = parser.parse_args()
    campaign(args)
    return 0
