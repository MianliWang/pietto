"""Independent data-only S10 native observation checks; no database acquisition."""

from collections import Counter
from pathlib import Path
from typing import Any, cast
import copy
import hashlib
import json


def need(condition, category):
    if not condition:
        raise ValueError("S10_" + category)


def row_key(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def int_row(row):
    return [
        {"kind": "null"} if value is None else {"kind": "int", "value": str(value)}
        for value in row
    ]


def check_small_pg(
    data: dict[str, Any],
    expected_rows,
    origin_root,
    expected_sql,
    *,
    origin="source",
    entry="bundle",
    target="postgres",
):
    """Complete bag/SQL/bind/schema and native lifecycle, from original literals."""
    need(type(data) is dict and data["forbidden_calls"] == [], "SOURCE_FREE_BOUNDARY")
    routes = (
        ("mysql_rows",) if target == "mysql" else ("postgres_rows", "postgres_adbc")
    )
    cases = (("A", 1), ("B", 5), ("A_again", 1), ("empty", 2**63 - 1))
    results = data["results"]
    need(
        tuple((r["route"], r["case"]) for r in results)
        == tuple((route, name) for route in routes for name, _ in cases),
        "PILOT_DENOMINATOR",
    )
    bindings = []
    attempts = []
    for result, (route, (name, threshold)) in zip(
        results, ((route, case) for route in routes for case in cases), strict=True
    ):
        need(
            result["entry"] == entry
            and result["origin"] == origin
            and result["route"] == route
            and result["case"] == name,
            "PILOT_CELL",
        )
        need(
            result["values"] == [{"kind": "int", "value": str(threshold)}],
            "BINDING_VALUES",
        )
        expected = Counter(
            row_key(int_row(row)) for row in expected_rows if row[0] > threshold
        )
        need(Counter(map(row_key, result["rows"])) == expected, "COMPLETE_VALUES")
        need(
            result["sql"] == expected_sql and len(result["submissions"]) == 1,
            "ACTUAL_SQL",
        )
        submission = result["submissions"][0]
        need(
            submission["sql"] == expected_sql
            and submission["arguments"] == result["values"],
            "ACTUAL_ARGUMENTS",
        )
        need(
            result["bound_schema"]
            == [["renamed", "int64", False], ["other", "int64", True]],
            "EMPTY_SCHEMA",
        )
        need(
            all(schema == result["bound_schema"] for schema in result["schemas"]),
            "BATCH_SCHEMA",
        )
        need(result["native_metadata"] is not None, "NATIVE_SCHEMA")
        if route == "mysql_rows":
            check_mysql_bound_native(result)
        else:
            q = cast(dict[str, Any], result["qualification"])
            need(
                q is not None
                and q["roots"] == [["public", "rows"]]
                and bool(q["replies"])
                and bool(q["paths"]),
                "SOURCE_QUALIFICATION",
            )
            need(
                q["context"] == result["context"] and len(q["context"]) == 17,
                "CONTEXT_CORRESPONDENCE",
            )
            need(
                q["context"][0] == 180006
                and q["context"][8:14]
                == ["repeatable read", "on", "UTF8", "pg_catalog", "UTC", "on"],
                "CONTEXT_PROFILE",
            )
            for reply in q["replies"]:
                need(
                    reply["arguments"] == reply["native_arguments"]
                    and reply["rows"] == reply["native_rows"]
                    and reply["native_terminal"] == "NORMAL",
                    "NATIVE_CATALOG_CORRESPONDENCE",
                )
                if route == "postgres_rows":
                    need(
                        type(reply["native_metadata"]) is list
                        and bool(reply["native_metadata"])
                        and reply["native_status"].startswith("SELECT "),
                        "PSYCOPG_CATALOG_PROTOCOL",
                    )
        outcome, layers = result["outcome"], result["layers"]
        need(
            result["failure"] is None
            and result["control_joined"] is True
            and outcome["source"] == "EOF"
            and outcome["transaction"] == "COMMIT_ACK"
            and outcome["delivery"] == "COMPLETE"
            and outcome["rows"] == sum(expected.values())
            and outcome["primary"] is None
            and outcome["cleanup_failures"] == [],
            "LIFECYCLE",
        )
        need(
            layers["source_qualification"] == "QUALIFIED"
            and layers["remote_source_use_end"] == "TRANSACTION_ACK"
            and layers["premise_compliance"] == "NOT_INDEPENDENTLY_VERIFIED"
            and layers["native_definition_lifetime_exclusion"] == "NOT_DEMONSTRATED"
            and layers["local_durable_result"] == "NOT_IMPLEMENTED",
            "ASSURANCE",
        )
        need(
            layers["binding_reference"] == result["binding"]
            and layers["transaction"] == outcome["transaction"],
            "OUTCOME_CORRESPONDENCE",
        )
        bindings.append(result["binding"])
        attempts.append(outcome["attempt"])
    need(
        len(set(bindings)) == len(bindings) and len(set(attempts)) == len(attempts),
        "FRESH_ATTEMPTS",
    )
    origins = data["origins"]
    for required in (
        "project_compiled_loading",
        "project_execution_template",
        *(
            (
                "project_execution_mysql",
                "project_execution_mysql_native",
                "project_execution_mysql_context",
            )
            if target == "mysql"
            else (
                "project_execution_postgres",
                "project_execution_postgres_adbc",
                "project_postgres_source_assurance",
            )
        ),
    ):
        need("pietto._project." + required in origins, "ORIGIN_INVENTORY")
    for item in origins.values():
        path = Path(item["path"])
        need(
            path.is_relative_to(origin_root)
            and path.is_file()
            and hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"],
            "LIBRARY_ORIGIN",
        )


def check_small_pg_damage(
    data,
    expected_rows,
    origin_root,
    expected_sql,
    *,
    origin="source",
    entry="bundle",
    target="postgres",
):
    """Coordinated context, same-type wrong value and missing terminal controls."""
    for kind in ("value", "context", "terminal", "cell"):
        changed = copy.deepcopy(data)
        if kind == "value":
            changed["results"][0]["rows"][0][0]["value"] = "123456789"
        elif kind == "context":
            changed["results"][0]["context"][9] = "off"
            changed["results"][0]["qualification"]["context"][9] = "off"
        elif kind == "terminal":
            changed["results"][0]["outcome"]["transaction"] = "UNKNOWN"
            changed["results"][0]["layers"]["transaction"] = "UNKNOWN"
        else:
            changed["results"].pop()
        try:
            check_small_pg(
                changed,
                expected_rows,
                origin_root,
                expected_sql,
                origin=origin,
                entry=entry,
                target=target,
            )
        except ValueError:
            continue
        raise ValueError("S10_RAW_DAMAGE_ACCEPTED:" + kind)


def check_pg_source_controls(records):
    """Original source-law denominator and values, with real Psycopg protocol facts."""
    from _pietto_phase68_slice9_check import check_fixture_values
    from pietto._project.project_postgres_source_assurance import SQL
    from pietto._project.project_execution_postgres_adbc_native import CONTEXT_SQL

    expected = [
        "nested_definer_invoker_requires_query_base_privilege",
        "nested_invoker_definer_union_all_no_base_select",
        "opaque_function_before_evaluation",
        "custom_operator_before_evaluation",
        "unqualified_rls_before_evaluation",
        "qualified_builtin_virtual_expression",
        "unqualified_virtual_expression",
        "qualified_registry_view_and_key",
        "registry_wrapper_before_values",
    ]
    positives = {
        "nested_invoker_definer_union_all_no_base_select": 8,
        "qualified_builtin_virtual_expression": 4,
        "qualified_registry_view_and_key": 4,
    }
    need(
        [r["source_control"] for r in records] == expected, "SOURCE_CONTROL_DENOMINATOR"
    )
    legacy_context = "SELECT current_user,current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_setting('search_path'),pg_backend_pid()"
    permitted = set(SQL.values()) | {
        CONTEXT_SQL,
        legacy_context,
        "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "ROLLBACK",
    }
    for record in records:
        name = record["source_control"]
        need(
            record["route"] == "postgres_rows"
            and record["entry"] == "live"
            and record["control_joined"]
            and record["session_gone"][-1] == 0,
            "SOURCE_ATTEMPT",
        )
        if name in positives:
            check_fixture_values(record, repeat=2 if name == expected[1] else 1)
            need(
                record["failure"] is None
                and len(record["rows"]) == positives[name]
                and record["outcome"]["transaction"] == "COMMIT_ACK"
                and record["outcome"]["source"] == "EOF"
                and record["outcome"]["delivery"] == "COMPLETE",
                "SOURCE_POSITIVE",
            )
            need(
                record["qualification"] is not None
                and record["layers"]["source_qualification"] == "QUALIFIED",
                "SOURCE_QUALIFICATION",
            )
        elif name == expected[0]:
            need(
                record["failure"] is not None
                and record["failure"]["sqlstate"] == "42501"
                and record["rows"] == [],
                "INVOKER_ACCESS",
            )
        else:
            need(
                record["failure"] is not None
                and record["failure"]["message"].startswith("POSTGRES_SOURCE_")
                and record["rows"] == [],
                "SOURCE_NEGATIVE",
            )
            need(
                all(s["sql"] in permitted for s in record["statements"]),
                "SOURCE_EVALUATION_BEFORE_QUALIFICATION",
            )
    registry = records[7]["qualification"]["roots"]
    need(
        ["public", "p68s9_registry"] in [list(v) for v in registry],
        "REGISTRY_QUALIFICATION",
    )


def check_mysql_bound_native(record: dict[str, Any]):
    """Actual prepared driver calls, metadata and binary terminal for the bound pilot."""
    q = cast(dict[str, Any], record["qualification"])
    need(q is not None and q["roots"] == [["phase66", "rows"]], "MYSQL_QUALIFICATION")
    need(q["context"] == record["context"] and len(q["context"]) == 15, "MYSQL_CONTEXT")
    context = q["context"]
    need(
        context[1:3] == ["pietto_query@%", "NONE"]
        and context[4] == "phase66"
        and context[5] == "REPEATABLE-READ"
        and context[6:10] == ["utf8mb4", "utf8mb4", "utf8mb4", "utf8mb4_0900_bin"],
        "MYSQL_CONTEXT_PROFILE",
    )
    need(
        record["epoch"] == record["initial_epoch"]
        and record["epoch"][2:6] == ["ACTIVE", "READ ONLY", "REPEATABLE READ", "NO"],
        "MYSQL_EPOCH",
    )
    need(
        len(q["objects"]) == 1 and q["objects"][0]["engine"] == "InnoDB",
        "MYSQL_SOURCE_ENGINE",
    )
    actual = record["submissions"][0]
    need(
        actual["flags"] == 0
        and actual["prepared"]["num_params"] == len(actual["arguments"])
        and actual["prepared"]["warning_count"] == 0,
        "MYSQL_PREPARED",
    )
    statements = record["statements"]
    need(len(statements) == 1, "MYSQL_STATEMENT_INVENTORY")
    statement = statements[0]
    need(
        statement["sql"] == actual["sql"]
        and statement["arguments"] == actual["arguments"]
        and statement["prepared"] == actual["prepared"],
        "MYSQL_NATIVE_CORRESPONDENCE",
    )
    need(
        statement["closed"] and statement["close_send"] == "COMPLETE_NO_ACK",
        "MYSQL_CLOSE_SEND",
    )
    for terminal in (statement["metadata_eof"], statement["terminal"]):
        need(
            type(terminal) is dict
            and terminal["warning_count"] == 0
            and type(terminal["status_flag"]) is int
            and cast(int, terminal["status_flag"]) & (1 | 8192) == (1 | 8192),
            "MYSQL_BINARY_EOF",
        )


def check_representative(record, case, program):
    """Original literal and native reconsumption owners check the new-entry record."""
    route = record["route"]
    check_public_schema(
        record, program.output, query=program.refinement, program=program
    )
    need(record["post_close_rows"] == record["rows"], "POST_CLOSE_VALUES")
    layers = record["layers"]
    need(
        layers["local_durable_result"] == "NOT_IMPLEMENTED"
        and layers["source_qualification"] == "QUALIFIED",
        "REPRESENTATIVE_LAYERS",
    )
    if route == "postgres_rows":
        from _pietto_phase68_slice7_check import check_attempt

        copied = copy.deepcopy(record)
        if copied["failure"] is None:
            del copied["failure"]
        check_attempt(copied, case, program)
    elif route == "postgres_adbc":
        from _pietto_phase68_slice9_check import check_attempt

        check_attempt(
            record,
            {"group": "guarded"},
            program.preparation.artifact,
            program.output,
            program=program,
            case=case,
        )
    else:
        from _pietto_phase68_slice8_check import check_product
        from _pietto_phase68_slice7_probe import encoded

        choices = case["options"].get("choices", ((case["states"], case["rows"]),))
        need(
            any(
                record["guard_states"] == list(states)
                and Counter(map(row_key, record["rows"]))
                == Counter(map(row_key, encoded(rows)))
                for states, rows in choices
            ),
            "GUARD_LITERAL_VALUES",
        )
        copied = copy.deepcopy(record)
        if copied["failure"] is None:
            del copied["failure"]
        check_product(
            copied,
            program.preparation.artifact,
            program.output,
            program=program,
            query=program.refinement,
        )


def check_matrix_origin(
    data: dict[str, Any], config: dict[str, Any], interpreter, wheel
):
    import zipfile

    root = Path(__file__).resolve().parents[1]
    need(data["forbidden_calls"] == [], "MATRIX_SOURCE_FREE")
    need(
        [
            (r["route"], r["case"], r["variant"], r["origin"], r["entry"])
            for r in data["results"]
        ]
        == [
            (
                route,
                config["cell"]["case"],
                config["cell"]["variant"],
                config["origin"],
                config["entry"],
            )
            for route in config["routes"]
        ],
        "MATRIX_DENOMINATOR",
    )
    need(
        len({r["outcome"]["attempt"] for r in data["results"]}) == len(data["results"]),
        "MATRIX_FRESH_ATTEMPTS",
    )
    need(
        "pietto._project.project_compiled_loading" in data["origins"]
        and "pietto._project.project_execution_template" in data["origins"],
        "MATRIX_ORIGIN_INVENTORY",
    )
    archive = None if config["origin"] == "source" else zipfile.ZipFile(wheel)
    try:
        for name, item in data["origins"].items():
            path = Path(item["path"])
            relative = "/".join(name.split(".")) + (
                "/__init__.py" if path.name == "__init__.py" else ".py"
            )
            if archive is None:
                need(path.is_relative_to(root / "src"), "MATRIX_SOURCE_ORIGIN")
                expected = (root / "src" / relative).read_bytes()
            else:
                need(
                    path.is_relative_to(interpreter.parent.parent)
                    and "site-packages" in path.parts,
                    "MATRIX_INSTALLED_ORIGIN",
                )
                expected = archive.read(relative)
            need(
                hashlib.sha256(expected).hexdigest()
                == item["sha256"]
                == hashlib.sha256(path.read_bytes()).hexdigest(),
                "MATRIX_MEMBER_BYTES",
            )
    finally:
        if archive is not None:
            archive.close()


def check_pg_owned_catalog(record: dict[str, Any]):
    """Reconsume actual Psycopg catalog/context records under original PG laws."""
    from _pietto_phase68_slice6_check import value
    from _pietto_phase68_slice9_check import tuples, exact
    from pietto._project.project_postgres_source_assurance import SQL, CatalogReply
    from pietto._project.project_postgres_source_assurance_verification import (
        verify_catalog,
    )
    from pietto._project.project_execution_postgres import PostgresCatalogReply
    from pietto._project.project_execution_postgres_adbc_native import CONTEXT_SQL

    context = tuples(record["context"])
    need(
        len(context) == 17
        and context[8] in ("repeatable read", "serializable")
        and context[9:14] == ("on", "UTF8", "pg_catalog", "UTC", "on"),
        "PG_CONTEXT_PROFILE",
    )
    q = cast(dict[str, Any], record["qualification"])
    need(q is not None and exact(q["context"], context), "PG_QUALIFIED_CONTEXT")

    def native(statement):
        rows = tuple(
            tuple(value(v) for v in row)
            for pull in statement["fetches"]
            for row in pull["rows"]
        )
        need(
            statement["execute_returned"]
            and statement["native_status"] == 2
            and statement["closed"]
            and len(rows) == statement["native_rows"],
            "PG_CATALOG_PROTOCOL",
        )
        metadata = tuple((i, m[0], m[1]) for i, m in enumerate(statement["metadata"]))
        return PostgresCatalogReply(
            None,
            None,
            statement["sql"].encode(),
            tuple(value(v) for v in statement["arguments"]),
            metadata,
            rows,
            statement["command_status"].encode(),
            "NORMAL",
        )

    catalogs = [s for s in record["statements"] if s["sql"] in SQL.values()]
    need(len(catalogs) == len(q["replies"]), "PG_CATALOG_DENOMINATOR")
    replies = []
    for item, statement in zip(q["replies"], catalogs, strict=True):
        n = native(statement)
        need(
            statement["sql"] == SQL[item["kind"]]
            and exact(n.arguments, item["arguments"])
            and exact(n.rows, item["rows"]),
            "PG_NATIVE_CATALOG_CORRESPONDENCE",
        )
        replies.append(
            CatalogReply(
                item["kind"], tuples(item["arguments"]), tuples(item["rows"]), n
            )
        )
    roots = tuples(q["roots"])
    oids = []
    for root in roots:
        matches = [r for r in replies if r.kind == "resolve" and r.arguments == root]
        need(len(matches) == 1, "PG_ROOT_RESOLUTION")
        oids.append(matches[0].rows[0][0])
    contexts = [s for s in record["statements"] if s["sql"] == CONTEXT_SQL]
    need(
        bool(contexts) and all(native(s).rows == (context,) for s in contexts),
        "PG_CONTEXT_CONTINUITY",
    )
    paths = verify_catalog(
        roots,
        tuple(oids),
        tuple(replies),
        context,
        tuple(record["premise"]["schemas"]),
        native(contexts[-1]),
    )
    need(exact(paths, q["paths"]), "PG_COMPLETE_PATHS")
    commands = [
        i
        for i, s in enumerate(record["statements"])
        if s["sql"] in ("COMMIT", "ROLLBACK")
    ]
    need(
        len(commands) == 1
        and commands[0] > 0
        and record["statements"][commands[0] - 1]["sql"] == CONTEXT_SQL,
        "PG_FINALIZATION_CONTEXT",
    )
    need(
        record["session_gone"]
        and record["session_gone"][-1] == 0
        and record["control_joined"],
        "PG_SESSION_TERMINAL",
    )


def check_pg_refined_record(record: dict[str, Any], query):
    from _pietto_phase68_slice7_check import metadata
    from dataclasses import replace
    from _pietto_phase68_slice6_check import (
        rebound_admission,
        expected_uses,
        value,
        canonical_checked,
    )
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_refinement_enumeration import Enumeration
    from pietto._project.project_refinement_verification import verify_native

    pages = record["pages"]
    raw = [s for s in record["statements"] if s["purpose"] == "page"]
    need(pages and len(pages) == len(raw), "PG_PAGE_DENOMINATOR")
    e = Enumeration(
        query,
        rebound_admission(query, record),
        limits=ExecutionLimits(batch_rows=pages[0]["size"], seconds=180),
    )
    delivered = []
    for supplied, statement in zip(pages, raw, strict=True):
        page = e.request_page()
        need(
            supplied["ordinal"] == page.ordinal
            and supplied["size"] == page.size
            and supplied["uses"] == expected_uses(page, query)
            and supplied["erasure"] == [i for i, _ in query.erasure],
            "PG_PAGE_IDENTITY",
        )
        from _pietto_phase68_slice7_probe import encoded

        need(
            supplied["frontier"]
            == (None if page.frontier is None else encoded((page.frontier,))[0]),
            "PG_RECORDED_FRONTIER",
        )
        observed = replace(
            page.native,
            sql=statement["sql"].encode(),
            arguments=tuple(value(v) for v in statement["arguments"]),
        )
        verify_native(observed, query, frontier=page.frontier, size=page.size)
        rows = tuple(
            tuple(value(v) for v in row)
            for pull in statement["fetches"]
            for row in pull["rows"]
        )
        need(
            statement["execute_returned"]
            and statement["native_status"] == 2
            and statement["closed"]
            and len(rows) == statement["native_rows"],
            "PG_PAGE_TERMINAL",
        )
        checked = e.check_page(
            page,
            metadata(statement, "postgres_rows"),
            rows,
            terminal="NORMAL",
        )
        delivered.extend(canonical_checked(checked.rows, query.output.columns))
        e.commit_page(checked)
        need(supplied["accepted_progress"] == list(e.progress), "PG_PAGE_PROGRESS")
    need(
        e.progress[2:] == (True, False)
        and delivered == record["rows"]
        and list(e.progress) == record["progress"],
        "PG_COMPLETE_ENUMERATION",
    )


def check_matrix_record(record: dict[str, Any], cell, reference, *, case=None):
    from _pietto_phase68_slice6_check import expected, canonical_checked, value
    from _pietto_phase68_slice7_probe import encoded
    from _pietto_phase68_slice7_check import metadata
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_execution_binding_verification import native_arguments
    from pietto._project.project_execution_reader import decode_native_rows
    from pietto._project.project_arrow_result import bind_arrow

    artifact, preparation, query, output, binding = reference
    submitted: list[dict[str, Any]] = []
    route = record["route"]
    if route == "postgres_rows":
        check_pg_owned_catalog(record)
    if cell["group"] == "guarded":
        program = prepare_program(preparation, binding=binding, refinement=query)
        check_representative(record, case, program)
        return
    need(record["failure"] is None, "MATRIX_UNEXPECTED_FAILURE")
    if route == "mysql_rows":
        from _pietto_phase68_slice8_check import check_product

        copied = copy.deepcopy(record)
        copied.pop("failure")
        check_product(copied, artifact, output, query=query)
    elif route == "postgres_adbc":
        from _pietto_phase68_slice9_check import check_native, check_pages, check_rows

        check_native(record)
        if query is not None:
            check_pages(record, query)
        else:
            submitted = [s for s in record["statements"] if s["purpose"] == "query"]
            need(len(submitted) == 1, "MATRIX_QUERY_DENOMINATOR")
            check_rows(record, output, submitted[0])
    elif query is not None:
        check_pg_refined_record(record, query)
    else:
        submitted = [s for s in record["statements"] if s["purpose"] == "query"]
        need(len(submitted) == 1, "MATRIX_QUERY_DENOMINATOR")
        raw = submitted[0]
        rows = tuple(
            tuple(value(v) for v in row)
            for pull in raw["fetches"]
            for row in pull["rows"]
        )
        need(
            raw["execute_returned"]
            and raw["native_status"] == 2
            and len(rows) == raw["native_rows"]
            and raw["closed"],
            "MATRIX_NATIVE_TERMINAL",
        )
        producer, decoded = decode_native_rows(
            output, route, metadata(raw, route), rows
        )
        need(
            canonical_checked(decoded, output.columns) == record["rows"],
            "MATRIX_RAW_RECONSUMPTION",
        )
        schema = [
            [f.name, str(f.type), f.nullable] for f in bind_arrow(producer).schema
        ]
        need(
            record["bound_schema"] == schema
            and all(s == schema for s in record["schemas"]),
            "MATRIX_OUTPUT_SCHEMA",
        )
    check_public_schema(record, output, query=query)
    if query is None and route != "mysql_rows":
        arguments = (
            binding.arguments
            if binding is not None
            else native_arguments(
                artifact,
                tuple(
                    s.site.position.literal.value
                    for s in artifact.request.plan.literal_slots
                ),
            )
        )
        need(
            submitted[0]["sql"] == artifact.rendered.sql.decode()
            and submitted[0]["arguments"] == encoded((arguments,))[0],
            "MATRIX_ORIGINAL_SQL_USES",
        )
    literal, ordered = expected(
        "mysql" if route == "mysql_rows" else "postgres",
        cell["case"],
        cell["variant"],
        output.columns,
    )
    need(
        Counter(map(row_key, literal)) == Counter(map(row_key, record["rows"]))
        and (not ordered or literal == record["rows"]),
        "MATRIX_ORIGINAL_FULL_VALUES",
    )
    outcome = record["outcome"]
    need(
        (outcome["source"], outcome["transaction"], outcome["delivery"])
        == ("EOF", "COMMIT_ACK", "COMPLETE")
        and outcome["rows"] == len(record["rows"])
        and not outcome["cleanup_failures"]
        and record["control_joined"],
        "MATRIX_COMPLETE_TERMINALS",
    )
    need(
        record["post_close_rows"] == record["rows"]
        and record["layers"]["local_durable_result"] == "NOT_IMPLEMENTED",
        "MATRIX_OUTCOME_LAYERS",
    )


def check_control_family(records, reference, cell):
    controls = (
        "pre_cancel",
        "short_deadline",
        "finalize_error",
        "finalize_graft",
        "delivery_after_eof",
        "cancel_after_batch",
        "fresh_success",
    )
    need(tuple(r["control"] for r in records) == controls, "CONTROL_DENOMINATOR")
    need(
        len({r["outcome"]["attempt"] for r in records}) == len(controls),
        "CONTROL_FRESH_ATTEMPTS",
    )
    for r in records:
        o = r["outcome"]
        control = r["control"]
        need(
            r["control_joined"]
            and (r["session"] is None or r["session_gone"][-1] == 0),
            "CONTROL_CLEANUP",
        )
        if control in ("pre_cancel", "short_deadline"):
            need(
                r["failure"] is not None
                and r["session"] is None
                and r["layers"]["source_qualification"] == "NOT_QUALIFIED"
                and not r["rows"],
                "CONTROL_BEFORE_ACQUISITION",
            )
        elif control in ("finalize_error", "finalize_graft"):
            need(
                o["primary"]["phase"] == "injected_before_finalization"
                and o["primary"]["kind"] == "ValueError"
                and o["source"] == "EOF"
                and o["delivery"] == "FAILED",
                "CONTROL_PRIMARY_RETAINED",
            )
            need(
                o["transaction"]
                == ("UNKNOWN" if control == "finalize_graft" else "ROLLBACK_ACK"),
                "CONTROL_ORIGINAL_TRANSACTION",
            )
            need(
                bool(o["cleanup_failures"]) == (control == "finalize_graft"),
                "CONTROL_CLEANUP_FAILURE_SEPARATE",
            )
            commands = (
                [
                    event["value"]
                    for event in r["events"]
                    if event["event"] == "cmd_query.call"
                ]
                if r["route"] == "mysql_rows"
                else [statement["sql"] for statement in r["statements"]]
            )
            if control == "finalize_graft":
                need(
                    commands.count("COMMIT") == 1 and "ROLLBACK" not in commands,
                    "CONTROL_NO_FOREIGN_FINALIZATION",
                )
                need(
                    commands[-1].startswith("SELECT t.THREAD_ID,e.EVENT_ID")
                    if r["route"] == "mysql_rows"
                    else "pg_current_xact_id()" in commands[-1],
                    "CONTROL_FINAL_IDENTITY_OBSERVED",
                )
            else:
                need(
                    commands[-1] == "ROLLBACK"
                    and (
                        commands[-2].startswith("SELECT t.THREAD_ID,e.EVENT_ID")
                        if r["route"] == "mysql_rows"
                        else "pg_current_xact_id()" in commands[-2]
                    ),
                    "CONTROL_IDENTITY_BEFORE_ROLLBACK",
                )
            if control == "finalize_graft":
                need(
                    r["layers"]["remote_source_use_end"]
                    == "REMOTE_QUIESCENCE_UNCONFIRMED",
                    "CONTROL_UNCONFIRMED_REMOTE_END",
                )
        elif control == "delivery_after_eof":
            need(
                (o["source"], o["transaction"], o["delivery"])
                == ("EOF", "COMMIT_ACK", "FAILED")
                and o["primary"] is not None,
                "CONTROL_EOF_ACK_DELIVERY_FAILURE",
            )
        elif control == "cancel_after_batch":
            need(
                o["cancel_requested"]
                and not o["cancel_observed"]
                and o["delivery"] == "FAILED",
                "CONTROL_CANCEL_NOT_TERMINAL",
            )
        else:
            check_matrix_record(r, cell, reference)
    graft = records[3]
    need(
        graft["outcome"]["transaction"] == "UNKNOWN"
        and records[-1]["outcome"]["transaction"] == "COMMIT_ACK",
        "CONTROL_HISTORY_NOT_REWRITTEN",
    )


def check_public_schema(record, output, *, query=None, program=None):
    """Arrow schema from original output laws and the actual public native columns."""
    from _pietto_phase68_slice7_check import metadata, native_from_record
    from _pietto_phase68_slice6_check import value
    from pietto._project.project_execution_reader import bind_native_output
    from pietto._project.project_arrow_result import bind_arrow

    route = record["route"]
    if record.get("failure") or route == "mysql_rows":
        return
    if query is not None:
        statements = [s for s in record["statements"] if s["purpose"] == "page"]
        need(bool(statements), "SCHEMA_PAGE_REQUIRED")
        raw = statements[-1]
        native_metadata = (
            tuple(raw["schema"]) if route == "postgres_adbc" else metadata(raw, route)
        )
        public_metadata = tuple(
            native_metadata[position] for position, _ in query.erasure
        )
    elif program is not None:
        from pietto._project.project_guard_context import ObservedGuardOwner
        from pietto._project.project_guard_runtime import ObservedGuardRequest
        from pietto._project.project_execution import ExecutionLimits

        native = native_from_record(program, record["guard_native"])
        matches = [s for s in record["statements"] if s["sql"] == native.sql.decode()]
        need(len(matches) == 1, "SCHEMA_GUARD_STATEMENT")
        raw = matches[0]
        native_metadata = (
            tuple(raw["schema"]) if route == "postgres_adbc" else metadata(raw, route)
        )
        rows = (
            raw["raw_rows"]
            if route == "postgres_adbc"
            else [row for pull in raw["fetches"] for row in pull["rows"]]
        )
        observer = ObservedGuardOwner(
            ObservedGuardRequest(
                program, ExecutionLimits(), isolation=record["environment"][1]
            ),
            route=route,
            session_id=record["session"],
            role=record["role"],
            environment=tuple(record["environment"]),
            sources=tuple((s, ("data only",)) for s in output.artifact.request.sources),
        )
        try:
            observer.guards.consume_observed_submission(observer, native)
            public_metadata = observer.guards.accept_header(
                observer,
                native_metadata,
                None
                if native.statement.kind == "data"
                else tuple(value(v) for v in rows[0]),
            )
        finally:
            observer.close()
    else:
        return
    producer = bind_native_output(output, route, public_metadata)
    expected = [[f.name, str(f.type), f.nullable] for f in bind_arrow(producer).schema]
    need(
        record["bound_schema"] == expected
        and len(record["schemas"]) == record["outcome"]["batches"]
        and all(schema == expected for schema in record["schemas"]),
        "PUBLIC_SCHEMA_CORRESPONDENCE",
    )


def check_complete_campaign(report, denominator):
    """Independently reconcile frozen cells with intact, checked native records."""
    expected = []
    exclusions = []
    cells = (
        ("source", "live"),
        ("source", "bundle"),
        ("installed", "live"),
        ("installed", "bundle"),
    )
    for target in ("postgres", "mysql"):
        for item in denominator[target]:
            prefix = (target, item["group"], item["case"], item["variant"])
            if item["excluded"]:
                exclusions.append(prefix)
            else:
                for origin, entry in cells:
                    for route in (
                        ("postgres_rows", "postgres_adbc")
                        if target == "postgres"
                        else ("mysql_rows",)
                    ):
                        expected.append((*prefix, origin, entry, route))
    groups = report["groups"]
    need(
        [(g["target"], g["group"]) for g in groups]
        == [(t, g) for t in ("postgres", "mysql") for g in ("general", "guarded")],
        "COMPLETE_GROUPS",
    )
    actual, rejected, attempts = [], [], []
    for group in groups:
        need(
            group["status"] == "PASS"
            and group["cleanup"]["status"] == "success"
            and all(group["cleanup"]["absent"].values())
            and not group["cleanup"]["failures"],
            "COMPLETE_GROUP_CLEANUP",
        )
        for item in group["records"]:
            cell = item["cell"]
            prefix = (group["target"], cell["group"], cell["case"], cell["variant"])
            if item.get("status") == "ORIGINAL_TARGET_EXCLUSION":
                rejected.append(prefix)
                continue
            need(
                item["checked"] is True and item["worker_exit"] == 0,
                "COMPLETE_WORKER_ACCEPTANCE",
            )
            raw, sessions = Path(item["raw"]), Path(item["sessions"])
            need(
                hashlib.sha256(raw.read_bytes()).hexdigest() == item["raw_sha256"]
                and hashlib.sha256(sessions.read_bytes()).hexdigest()
                == item["sessions_sha256"],
                "COMPLETE_OBSERVATION_BYTES",
            )
            data = json.loads(raw.read_text())
            need(data["forbidden_calls"] == [], "COMPLETE_SOURCE_FREE")
            for record in data["results"]:
                need(
                    record["origin"] == item["origin"]
                    and record["entry"] == item["entry"]
                    and (record["case"], record["variant"])
                    == (cell["case"], cell["variant"]),
                    "COMPLETE_CELL_IDENTITY",
                )
                actual.append(
                    (*prefix, record["origin"], record["entry"], record["route"])
                )
                attempts.append(record["outcome"]["attempt"])
    need(
        Counter(actual) == Counter(expected)
        and Counter(rejected) == Counter(exclusions)
        and len(set(attempts)) == len(attempts),
        "COMPLETE_NAMED_DENOMINATOR",
    )
    return {
        "actual_attempts": len(actual),
        "original_exclusions": len(exclusions),
        "by_route": dict(Counter(c[-1] for c in actual)),
        "by_entry": dict(Counter(c[-2] for c in actual)),
        "by_origin": dict(Counter(c[-3] for c in actual)),
    }
