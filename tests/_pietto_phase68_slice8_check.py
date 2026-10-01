"""Independent data-only consumption of S08 native premise records."""

from typing import Any, cast


def require(condition, category):
    if not condition:
        raise ValueError("S08_RECORD_" + category)


def check_source_lifetime(record, manifest):
    expected = [(x["isolation"], x["mechanism"]) for x in manifest["cases"]]
    require(record["tree"] == manifest["tree"], "PRODUCING_TREE")
    require(
        [(x["isolation"], x["mechanism"]) for x in record["cases"]] == expected,
        "CASE_DENOMINATOR",
    )
    require(len(expected) == 10 and len(set(expected)) == 10, "MANIFEST")
    require(record["identity"]["rows"][0][0] == "8.4.12", "SERVER")
    data_session = record["identity"]["session"]
    control_session = record["cases"][0]["epoch_before"]["session"]
    require(
        type(data_session) is int
        and type(control_session) is int
        and data_session != control_session,
        "SESSIONS",
    )
    require(
        set(record["sessions_gone"]) == {str(data_session), str(control_session)},
        "SESSION_DENOMINATOR",
    )
    require(
        all(rows and rows[-1] == 0 for rows in record["sessions_gone"].values()),
        "SESSION_TERMINAL",
    )
    require(
        record["canary_after_definitions"]["rows"]
        == record["canary_final"]["rows"]
        == [[0]],
        "METADATA_EFFECT",
    )
    require(
        [x["rows"][0][0] for x in record["definitions"]]
        == [
            "p68s3_input",
            "p68_mdl_wrapper",
            "p68_mdl_nested",
            "p68_mdl_role",
            "p68_mdl_unsafe",
        ],
        "DEFINITION_DENOMINATOR",
    )
    for case in record["cases"]:
        before, after = case["epoch_before"], case["epoch_after"]
        require(
            before["rows"] == after["rows"] and len(before["rows"]) == 1,
            "TRANSACTION_CHANGED",
        )
        epoch = before["rows"][0]
        require(
            epoch[2:6] == ["ACTIVE", "READ ONLY", case["isolation"], "NO"],
            "TRANSACTION_PROFILE",
        )
        require(
            before["session"] == after["session"] == control_session
            and before["arguments"] == after["arguments"] == [data_session],
            "EPOCH_OWNER",
        )
        for name in ("locks_after_acquisition", "locks_after_rollback"):
            observation = case[name]
            require(
                observation["session"] == control_session
                and observation["arguments"] == [data_session]
                and observation["normal_terminal"],
                "LOCK_OBSERVATION",
            )
            require(observation["rows"] == [], "UNEXPECTED_LOCK_INVENTORY")
        require(case["ddl"] == "COMPLETED_WHILE_READER_OPEN", "DDL_TERMINAL")
        if case["target"] == "table":
            require(
                case["engine_after_ddl"]["rows"] == [["MyISAM"]], "ENGINE_REPLACEMENT"
            )
        if case["mechanism"].startswith("information_schema_"):
            require(
                case["acquisition_error"]["errno"] == 3550
                and case["acquisition_error"]["sqlstate"] == "HY000",
                "LOCKING_READ_ERROR",
            )
        else:
            require(
                case["acquisition"]["session"] == data_session
                and case["acquisition"]["normal_terminal"]
                and case["acquisition"]["rows"],
                "DEFINITION_TERMINAL",
            )
    require(
        record["cleanup"]["status"] == "success"
        and record["cleanup"]["absent"] == {"container": True, "network": True},
        "RESOURCE_TERMINAL",
    )
    return "NO_DEMONSTRATED_NATIVE_DEFINITION_LIFETIME"


def native_statements(record):
    """Independent event partition; variable bounded fetches, real binary EOF."""
    groups = []
    binary = False
    for event in record["events"]:
        require(event["connection"] in ("data", "control"), "CONNECTION_KIND")
        if event["connection"] != "data":
            continue
        require(event["session"] == record["session"], "NATIVE_SESSION")
        name = event["event"]
        if name == "get_rows.call":
            binary = event["value"]["binary"]
        if name.startswith("get_rows.") and not binary:
            continue
        if name.startswith("cmd_query."):
            continue
        if name == "cmd_stmt_prepare.call":
            groups.append([])
        require(bool(groups), "UNOWNED_NATIVE_EVENT")
        groups[-1].append(event)
    require(len(groups) == len(record["statements"]), "STATEMENT_DENOMINATOR")
    result = []
    for supplied, events in zip(record["statements"], groups, strict=True):

        def values(name):
            return [e["value"] for e in events if e["event"] == name]

        require(values("cmd_stmt_prepare.call") == [supplied["sql"]], "PREPARE_SQL")
        prepared = cast(dict[str, Any], supplied["prepared"])
        require(
            type(prepared) is dict and values("cmd_stmt_prepare.return") == [prepared],
            "PREPARE_RETURN",
        )
        sid = prepared["statement_id"]
        require(
            type(sid) is int and sid > 0 and prepared["warning_count"] == 0,
            "PREPARED_ID",
        )
        args = supplied["arguments"]
        require(
            prepared["num_params"] == len(args) == len(prepared["parameters"]),
            "PARAMETER_OCCURRENCES",
        )
        execute = dict(
            statement_id=sid, data=args, parameters=prepared["parameters"], flags=0
        )
        require(values("cmd_stmt_execute.call") == [execute], "EXECUTE_IDENTITY")
        encodings = values("make_stmt_execute.call")
        require(
            len(encodings) == 1
            and encodings[0]
            == dict(
                execute,
                charset="utf8mb4",
                long_data_used={},
                query_attrs=[],
                converter_str_fallback=False,
            ),
            "ENCODING_INPUT",
        )
        packet = values("make_stmt_execute.return")
        require(len(packet) == 1 and type(packet[0]) is str, "NATIVE_PACKET")
        prefix = sid.to_bytes(4, "little").hex()
        require(packet[0].startswith(prefix + "0001000000"), "EXECUTE_PACKET_HEADER")
        sends = values("_send_cmd.call")
        require(values("_send_cmd.return") == sends, "SEND_TERMINALS")
        expected_sends = [
            dict(command=22, payload=supplied["sql"], expect_response=True),
            dict(command=23, payload=packet[0], expect_response=True),
        ]
        closed = supplied["close_send"] == "COMPLETE_NO_ACK"
        if closed:
            expected_sends.append(
                dict(command=25, payload=prefix, expect_response=False)
            )
            require(
                values("cmd_stmt_close.call")
                == values("cmd_stmt_close.return")
                == [sid],
                "CLOSE_SEND",
            )
        else:
            require(
                supplied["close_send"] == "NOT_SENT_CONNECTION_DISCARDED"
                and not values("cmd_stmt_close.call"),
                "DISCARD_CLOSE",
            )
        require(sends == expected_sends and supplied["closed"], "COMMAND_DENOMINATOR")
        meta, eof = supplied["metadata"], supplied["metadata_eof"]
        require(
            values("cmd_stmt_execute.return") == [[len(meta), meta, eof]],
            "RESULT_METADATA",
        )
        require(
            eof["warning_count"] == 0
            and eof["status_flag"] & (1 | 8192 | 8) == (1 | 8192),
            "METADATA_EOF",
        )
        calls, pulls = values("get_rows.call"), values("get_rows.return")
        require(
            len(calls) == len(pulls) and all(type(p) is dict for p in pulls),
            "FETCH_DENOMINATOR",
        )
        for call, pull in zip(calls, pulls, strict=True):
            require(
                call["binary"] is True
                and call["columns"] == meta
                and type(call["count"]) is int
                and 0 < call["count"] <= record["batch_rows"]
                and len(pull["rows"]) <= call["count"],
                "BOUNDED_BINARY_FETCH",
            )
        terminals = [p["eof"] for p in pulls if p["eof"] is not None]
        if supplied["terminal"] is not None:
            require(
                terminals == [supplied["terminal"]]
                and pulls[-1]["eof"] == supplied["terminal"],
                "ACTUAL_EOF",
            )
            require(
                supplied["terminal"]["warning_count"] == 0
                and supplied["terminal"]["status_flag"] & (1 | 8192 | 8) == (1 | 8192),
                "EOF_PROFILE",
            )
        else:
            require(not terminals and not closed, "UNREAD_TERMINAL")
        expected_events = [
            "cmd_stmt_prepare.call",
            "_send_cmd.call",
            "_send_cmd.return",
            "cmd_stmt_prepare.return",
            "cmd_stmt_execute.call",
            "make_stmt_execute.call",
            "make_stmt_execute.return",
            "_send_cmd.call",
            "_send_cmd.return",
            "cmd_stmt_execute.return",
        ]
        expected_events += [
            n for _ in pulls for n in ("get_rows.call", "get_rows.return")
        ]
        if closed:
            expected_events += [
                "cmd_stmt_close.call",
                "_send_cmd.call",
                "_send_cmd.return",
                "cmd_stmt_close.return",
            ]
        require([e["event"] for e in events] == expected_events, "NATIVE_EVENT_ORDER")
        result.append(
            dict(
                sql=bytes.fromhex(supplied["sql"]),
                arguments=args,
                metadata=meta,
                rows=[r for p in pulls for r in p["rows"]],
                terminal=supplied["terminal"],
                purpose=supplied["purpose"],
            )
        )
    return result


def native_control_records(record):
    """Partition actual text-protocol calls by owned connection and normal EOF."""
    from _pietto_phase68_slice6_check import value

    statements = []
    current: dict[str, dict[str, Any]] = {}
    pending: dict[str, bool] = {}
    sessions: dict[str, int] = {}

    def complete(item):
        require(item["returned"], "CONTROL_RETURN_MISSING")
        if item["rowset"]:
            require(item["eof"] is not None, "CONTROL_EOF_MISSING")
        else:
            require(not item["rows"] and item["eof"] is None, "CONTROL_RESULT_KIND")

    for event in record["events"]:
        connection, session, name = (
            event["connection"],
            event["session"],
            event["event"],
        )
        require(
            connection in ("data", "control") and type(session) is int and session > 0,
            "CONTROL_SESSION",
        )
        require(
            session == sessions.setdefault(connection, session),
            "CONTROL_SESSION_CHANGED",
        )
        if name == "cmd_query.call":
            require(connection not in pending, "CONTROL_OVERLAP")
            if connection in current:
                complete(current[connection])
            item = dict(
                connection=connection,
                session=session,
                sql=event["value"],
                rows=[],
                returned=False,
                rowset=False,
                eof=None,
            )
            current[connection] = item
            statements.append(item)
        elif name == "cmd_query.return":
            require(
                connection in current and not current[connection]["returned"],
                "CONTROL_RETURN_OWNER",
            )
            result = event["value"]
            require(
                type(result) is dict and result["warnings"] in (None, 0),
                "CONTROL_WARNING",
            )
            current[connection]["returned"] = True
            current[connection]["rowset"] = result["warnings"] is None
        elif name == "get_rows.call":
            require(connection not in pending, "CONTROL_FETCH_OVERLAP")
            pending[connection] = event["value"]["binary"]
            if pending[connection] is False:
                require(
                    connection in current
                    and current[connection]["returned"]
                    and current[connection]["rowset"]
                    and current[connection]["eof"] is None,
                    "CONTROL_FETCH_OWNER",
                )
        elif name == "get_rows.return":
            require(connection in pending, "CONTROL_FETCH_CALL_MISSING")
            if pending.pop(connection) is True:
                continue
            result = event["value"]
            require(type(result) is dict, "CONTROL_FETCH_FAILED")
            current[connection]["rows"].extend(
                tuple(value(v) for v in row) for row in result["rows"]
            )
            eof = result["eof"]
            if eof is not None:
                require(
                    type(eof) is dict
                    and eof["warning_count"] == 0
                    and type(eof["status_flag"]) is int
                    and not eof["status_flag"] & 8,
                    "CONTROL_EOF",
                )
                current[connection]["eof"] = eof
    require(
        not pending
        and set(sessions) == {"data", "control"}
        and sessions["data"] == record["session"]
        and sessions["control"] != record["session"],
        "CONTROL_SESSION_DENOMINATOR",
    )
    for item in current.values():
        complete(item)
    return statements


def native_context_records(record):
    """No copied context/epoch can replace the actual native query replies."""
    from pietto._project.project_execution_mysql_context import CONTEXT_SQL, EPOCH_SQL

    controls = native_control_records(record)
    context, epoch = tuple(record["context"]), tuple(record["epoch"])
    require(len(context) == 15 and len(epoch) == 10, "NATIVE_CONTEXT_SHAPE")
    observed = [c for c in controls if c["sql"] == CONTEXT_SQL]
    require(
        observed
        and all(
            c["connection"] == "data"
            and c["rows"] == [context]
            and c["eof"]["status_flag"] & 8193 == 8193
            for c in observed
        ),
        "ACTUAL_NATIVE_CONTEXT",
    )
    user = record["role"].rsplit("@", 1)[0]
    literal = "'" + user.replace("\\", "\\\\").replace("'", "\\'") + "'"
    sql = EPOCH_SQL.replace("%s", str(record["session"]), 1).replace("%s", literal, 1)
    observed = [
        c for c in controls if c["sql"].startswith("SELECT t.THREAD_ID,e.EVENT_ID,")
    ]
    require(
        observed
        and {c["connection"] for c in observed} == {"data", "control"}
        and all(c["sql"] == sql and c["rows"] == [epoch] for c in observed),
        "ACTUAL_NATIVE_EPOCH",
    )
    require(
        epoch[2:6] == ("ACTIVE", "READ ONLY", context[5].replace("-", " "), "NO")
        and epoch[6:] == (context[14], context[1], context[2], context[4])
        and context[1] == record["role"]
        and context[3] == record["session"],
        "NATIVE_CONTEXT_EPOCH_BINDING",
    )
    return [c for c in controls if c["connection"] == "data"]


def source_records(record, sources, requirements=()):
    """Reconstruct data-only derivations, never call the source constructor."""
    from pietto._project.project_mysql_view_source import Node, ViewDefinition
    from pietto._project.project_mysql_view_source_verification import (
        SourceObject,
        verify_closure,
        security_paths,
    )
    from pietto._project.project_execution_source import identifier

    def node(data):
        return Node(
            data["rule"],
            data["start"],
            data["end"],
            tuple(node(c) for c in data["children"]),
        )

    def literal(s):
        return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

    controls = native_context_records(record)
    objects = []
    for data in record["sources"]:
        key = tuple(data["key"])
        v = data["view"]
        view = (
            None
            if v is None
            else ViewDefinition(
                tuple(v["key"]),
                v["sql"],
                v["charset"],
                v["collation"],
                node(v["tree"]),
                tuple(tuple(e) for e in v["references"]),
                v["sql_mode"],
                v["quote_show_create"],
            )
        )
        definition = data["native_definition"]
        show = (
            "SHOW CREATE "
            + ("VIEW " if view is not None else "TABLE ")
            + ".".join(identifier(k, family="mysql") for k in key)
        )
        actual = [c["rows"] for c in controls if c["sql"] == show]
        require(
            bool(actual)
            and all(
                len(rows) == 1 and rows[0][:2] == (key[1], definition)
                for rows in actual
            ),
            "ACTUAL_DEFINITION",
        )
        if view is None:
            require(
                definition.startswith(
                    "CREATE TABLE " + identifier(key[1], family="mysql") + " ("
                ),
                "ACTUAL_PERSISTENT_IDENTITY",
            )
        if view is not None:
            require(
                view.sql == definition
                and all(
                    rows[0][2:] == (view.charset, view.collation) for rows in actual
                ),
                "DEFINITION_CONTEXT",
            )
        suffix = (
            " WHERE TABLE_SCHEMA="
            + literal(key[0])
            + " AND TABLE_NAME="
            + literal(key[1])
        )
        kind_sql = "SELECT TABLE_TYPE,ENGINE FROM information_schema.TABLES" + suffix
        columns_sql = (
            "SELECT COLUMN_NAME,EXTRA,GENERATION_EXPRESSION FROM information_schema.COLUMNS"
            + suffix
            + " ORDER BY ORDINAL_POSITION"
        )
        columns = tuple(tuple(c) for c in data["columns"])
        require(
            [c["rows"] for c in controls if c["sql"] == kind_sql]
            == [[(data["kind"], data["engine"])]],
            "ACTUAL_KIND_ENGINE",
        )
        require(
            [tuple(c["rows"]) for c in controls if c["sql"] == columns_sql]
            == [columns],
            "ACTUAL_COLUMNS",
        )
        objects.append(
            SourceObject(
                key,
                data["kind"],
                data["engine"],
                columns,
                view,
                tuple(data["context"]),
                definition,
            )
        )
    roots = tuple((s.namespace, s.name) for s in sources) + tuple(
        (r.registry_namespace, r.registry_name) for r in requirements
    )
    edges = verify_closure(roots, tuple(objects), tuple(record["context"]))
    import json

    require(json.loads(json.dumps(edges)) == record["source_edges"], "SOURCE_EDGES")
    paths = security_paths(roots, tuple(objects), record["role"], record["context"][2])
    require(json.loads(json.dumps(paths)) == record["security"], "SECURITY_PATHS")
    assurance = record["assurance"]
    require(
        assurance["structural_sources"] == "CHECKED"
        and assurance["definition_stability"] == "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        and assurance["native_lifetime_protection"] == "NOT_DEMONSTRATED"
        and assurance["premise_compliance"] == "NOT_INDEPENDENTLY_VERIFIED",
        "CONDITIONAL_ASSURANCE",
    )
    require(
        record["context"][0] == "8.4.12"
        and record["context"][1] == record["role"]
        and record["context"][3] == record["session"]
        and record["epoch"][6] == record["context"][14],
        "NATIVE_CONTEXT",
    )


def check_product(record, artifact, output, *, query=None, program=None):
    """Fresh original roots consume exact native output/guards/pages independently."""
    from dataclasses import replace
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_execution_reader import decode_native_rows
    from pietto._project.project_refinement_enumeration import Enumeration
    from pietto._project.project_refinement_verification import verify_native
    from pietto._project.project_guard_context import ObservedGuardOwner
    from pietto._project.project_guard_runtime import ObservedGuardRequest
    from _pietto_phase68_slice6_check import (
        canonical_checked,
        value,
        rebound_admission,
        expected_uses,
    )
    from _pietto_phase68_slice7_check import native_from_record
    from _pietto_phase68_slice6_probe import s01

    source_records(
        record, artifact.request.sources, () if query is None else query.sources
    )
    rows = record["rows"]
    outcome = record["outcome"]
    require(record["assurance"]["attempt"] == outcome["attempt"], "ATTEMPT")
    sessions = {e["session"] for e in record["events"] if type(e["session"]) is int}
    require(
        len(sessions) == 2
        and set(record["sessions_gone"]) == {str(s) for s in sessions},
        "SESSION_DENOMINATOR",
    )
    require(
        all(v and v[-1] == 0 for v in record["sessions_gone"].values())
        and record["control_joined"]
        and outcome["cleanup"] == "LOCAL_CLOSED_REMOTE_UNOBSERVED"
        and not outcome["cleanup_failures"],
        "OWNED_CLEANUP",
    )
    if record.get("failure", {}).get("category") == "GUARD_SQL_FORBIDDEN_UNFULFILLED":
        require(
            not record["statements"]
            and not rows
            and outcome["transaction"] == "ROLLBACK_ACK",
            "FORBIDDEN_GUARD",
        )
        return
    statements = native_statements(record)
    owner = None
    admission = None if query is None else rebound_admission(query, record)
    consumed = 0
    delivered = []
    decoded_producer = None
    if program is not None:
        native = native_from_record(program, record["guard_native"])
        raw = statements[0]
        require(
            raw["sql"] == native.sql
            and raw["arguments"] == [s01.scalar(v) for v in native.arguments],
            "GUARD_SQL_USES",
        )
        owner = ObservedGuardOwner(
            ObservedGuardRequest(
                program,
                ExecutionLimits(batch_rows=record["batch_rows"], seconds=180),
                isolation=record["environment"][1],
            ),
            route="mysql_rows",
            session_id=record["session"],
            role=record["role"],
            environment=tuple(record["environment"]),
            sources=tuple((s, ("record only",)) for s in artifact.request.sources),
            admissions=admission,
        )
        owner.guards.consume_observed_submission(owner, native)
        values = tuple(tuple(value(v) for v in r) for r in raw["rows"])
        metadata = tuple(tuple(m) for m in raw["metadata"])
        consumed = 1
        try:
            if native.statement.kind == "guard":
                require(raw["terminal"] is not None, "GUARD_EOF")
                owner.guards.accept_guard_result(
                    owner, metadata, values, terminal="NORMAL"
                )
            else:
                meta = owner.guards.accept_header(
                    owner,
                    metadata,
                    None if native.statement.kind == "data" else values[0],
                )
                public = owner.guards.public_rows(
                    owner, values if native.statement.kind == "data" else values[1:]
                )
                decoded_producer, decoded = decode_native_rows(
                    output, "mysql_rows", meta, public
                )
                delivered.extend(canonical_checked(decoded, output.columns))
        except ValueError as error:
            require(
                str(error) == "SINGLE_MATCH_VIOLATED"
                and record.get("failure", {}).get("category") == str(error)
                and not rows
                and not record["pages"]
                and len(statements) == 1,
                "GUARD_VIOLATION",
            )
            require(list(owner.guards.states) == record["guard_states"], "GUARD_STATES")
            owner.close()
            return
        require(list(owner.guards.states) == record["guard_states"], "GUARD_STATES")
    if query is not None:
        enumeration = Enumeration(
            query,
            admission,
            limits=ExecutionLimits(batch_rows=record["batch_rows"], seconds=180),
            _guards=None if owner is None else owner.guards,
        )
        for supplied in record["pages"]:
            page = enumeration.request_page()
            require(
                supplied["ordinal"] == page.ordinal
                and supplied["size"] == page.size
                and supplied["uses"] == expected_uses(page, query),
                "PAGE_IDENTITY",
            )
            require(
                supplied["frontier"]
                == (
                    None
                    if page.frontier is None
                    else [s01.scalar(v) for v in page.frontier]
                )
                and supplied["erasure"] == [i for i, _ in query.erasure],
                "PAGE_FRONTIER_ERASURE",
            )
            native = replace(
                page.native,
                sql=supplied["sql"].encode(),
                arguments=tuple(value(v) for v in supplied["arguments"]),
            )
            verify_native(native, query, frontier=page.frontier, size=page.size)
            raw = statements[consumed]
            require(
                raw["purpose"] == "page"
                and raw["sql"] == native.sql
                and raw["arguments"] == supplied["arguments"]
                and raw["terminal"] is not None,
                "PAGE_SUBMISSION",
            )
            checked = enumeration.check_page(
                page,
                tuple(tuple(m) for m in raw["metadata"]),
                tuple(tuple(value(v) for v in r) for r in raw["rows"]),
                terminal="NORMAL",
            )
            decoded_producer = checked.producer
            delivered.extend(canonical_checked(checked.rows, output.columns))
            enumeration.commit_page(checked)
            require(
                supplied["accepted_progress"] == list(enumeration.progress),
                "PAGE_PROGRESS",
            )
            consumed += 1
        require(
            record["progress"] == list(enumeration.progress)
            and enumeration.progress[2:] == (True, False),
            "PAGE_COMPLETION",
        )
    elif program is None:
        from pietto._project.project_execution_binding_verification import (
            native_arguments,
        )

        raw = statements[0]
        arguments = (
            output.binding.arguments
            if output.binding is not None
            else native_arguments(
                artifact,
                tuple(
                    s.site.position.literal.value
                    for s in artifact.request.plan.literal_slots
                ),
            )
        )
        require(
            raw["sql"] == artifact.rendered.sql
            and raw["arguments"] == [s01.scalar(v) for v in arguments],
            "ORDINARY_SUBMISSION",
        )
        decoded_producer, decoded = decode_native_rows(
            output,
            "mysql_rows",
            tuple(tuple(m) for m in raw["metadata"]),
            tuple(tuple(value(v) for v in r) for r in raw["rows"]),
        )
        delivered = canonical_checked(decoded, output.columns)
        consumed = 1
    require(consumed == len(statements) and delivered == rows, "COMPLETE_RECONSUMPTION")
    require(
        all(s["terminal"] is not None for s in statements)
        and not record.get("failure")
        and (outcome["source"], outcome["transaction"], outcome["delivery"])
        == ("EOF", "COMMIT_ACK", "COMPLETE")
        and outcome["rows"] == len(rows),
        "COMPLETE_TERMINALS",
    )
    if "schemas" in record:
        from pietto._project.project_arrow_result import bind_arrow

        if decoded_producer is None:
            raise ValueError("S08_RECORD_PUBLIC_PRODUCER")
        schema = [
            [f.name, str(f.type), f.nullable]
            for f in bind_arrow(decoded_producer).schema
        ]
        require(
            record["bound_schema"] == schema
            and len(record["schemas"]) == outcome["batches"]
            and all(s == schema for s in record["schemas"]),
            "ACTUAL_ARROW_SCHEMA",
        )
    if owner is not None:
        owner.close()


def check_worker(report, config, directory, root):
    from collections import Counter
    from pathlib import Path
    import hashlib
    import json
    from _pietto_phase68_slice6_cases import original, source_requirements
    from _pietto_phase68_slice6_check import expected
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from _pietto_phase68_slice7_probe import encoded
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_refinement import prepare_refinement, TieRefinement

    require(
        report["tree"] == config["tree"]
        and report["origin"] == config["origin"]
        and report["group"] == config["group"]
        and report["parent_database"] == config["database"],
        "WORKER_IDENTITY",
    )
    require(
        report["manager_local_closed"] and report["manager_gone"][-1] == 0,
        "WORKER_MANAGER_TERMINAL",
    )
    require(
        [(r["case"], r["variant"]) for r in report["attempts"]]
        == [(c["family"], c.get("variant")) for c in config["cases"]],
        "CASE_DENOMINATOR",
    )
    require(
        len({r["outcome"]["attempt"] for r in report["attempts"]})
        == len(report["attempts"]),
        "FRESH_ATTEMPTS",
    )
    from _pietto_mysql_native_prepared import driver_sources

    require(report["driver_sources"] == driver_sources(), "PINNED_DRIVER_BYTES")
    origins = report["origins"]
    require("pietto._project.project_execution_mysql" in origins, "PRODUCT_ORIGIN")
    for name, observed in origins.items():
        path = Path(observed["path"])
        if config["origin"] == "source":
            member = path.relative_to(root / "src")
        else:
            require("site-packages" in path.parts, "INSTALLED_ORIGIN")
            member = Path(*path.parts[path.parts.index("site-packages") + 1 :])
        require(
            member.parts[0] == "pietto"
            and hashlib.sha256((root / "src" / member).read_bytes()).hexdigest()
            == observed["sha256"],
            "ORIGIN_BYTES",
        )
    template = first_binding = None
    damage_checks = []

    def bag(rows):
        return Counter(
            json.dumps(r, sort_keys=True, separators=(",", ":")) for r in rows
        )

    for index, record in enumerate(report["attempts"]):
        case, variant = record["case"], record["variant"]
        if config.get("schema_observation"):
            require(
                "schemas" in record and "bound_schema" in record,
                "SCHEMA_OBSERVATION_REQUIRED",
            )
        work = directory / str(index)
        query = program = binding = None
        if config["group"] == "guarded":
            fixture = next(c for c in manifest() if c["name"] == case)
            options = fixture["options"]
            if "binding_values" in options:
                if template is None:
                    template = prepare_guarded_template(
                        case_preparation(work, "mysql", fixture)
                    )
                if case == "binding_A_again":
                    binding = first_binding
                else:
                    binding = bind_values(
                        template,
                        tuple(
                            zip(template.slots, options["binding_values"], strict=True)
                        ),
                    )
                    if case == "binding_A":
                        first_binding = binding
                if binding is None:
                    raise ValueError("S08_MISSING_ORIGINAL_BINDING")
                preparation = binding.guarded
            else:
                preparation = case_preparation(work, "mysql", fixture)
            artifact = preparation.artifact
            output = prepare_guarded_output(preparation, binding=binding)
            if options.get("refined"):
                query = prepare_refinement(
                    artifact,
                    source_requirements(
                        artifact,
                        config["providers"],
                        options.get("role", "pietto_query") + "@%",
                    ),
                    policy=TieRefinement(),
                    output=output,
                )
            program = prepare_program(preparation, binding=binding, refinement=query)
            choices = options.get("choices", ((fixture["states"], fixture["rows"]),))
            require(
                any(
                    record["guard_states"] == list(states)
                    and bag(record["rows"]) == bag(encoded(rows))
                    for states, rows in choices
                ),
                "INDEPENDENT_GUARD_FULL_VALUES",
            )
            failure = options.get("failure")
            if "VIOLATED" in record["guard_states"]:
                failure = "SINGLE_MATCH_VIOLATED"
            require(
                record.get("failure", {}).get("category") == failure,
                "EXPECTED_GUARD_DISPOSITION",
            )
        else:
            artifact = original(
                work, "mysql", "R2_seven" if case == "seven" else case, variant
            )
            output = prepare_output(artifact)
            if config["group"] == "unguarded_refinement":
                query = prepare_refinement(
                    artifact,
                    source_requirements(
                        artifact, config["providers"], "pietto_query@%"
                    ),
                    policy=TieRefinement(),
                    output=output,
                )
            wanted, ordered = expected(
                "mysql",
                "R2_seven" if case == "seven" else case,
                variant,
                output.columns,
            )
            require(
                record["rows"] == wanted
                if ordered
                else bag(record["rows"]) == bag(wanted),
                "INDEPENDENT_FULL_VALUES",
            )
        check_product(record, artifact, output, query=query, program=program)
        if config.get("damages") and case in (
            "G_emission_table_bag",
            "bound_four",
            "bound_four_refined",
            "seven_65_values",
        ):
            damage_checks.append(
                dict(
                    case=case,
                    rejected=product_record_damages(
                        record, artifact, output, query=query, program=program
                    ),
                )
            )
    if config.get("fresh_refinement"):
        prefix, fresh = report["fresh_refinement"]
        artifact = original(
            directory / "fresh-refinement", "mysql", "G_emission_table_bag", "bag"
        )
        if artifact is None:
            raise ValueError("S08_RECORD_FRESH_ARTIFACT")
        output = prepare_output(artifact)
        query = prepare_refinement(
            artifact,
            source_requirements(artifact, config["providers"], "pietto_query@%"),
            policy=TieRefinement(),
            output=output,
        )
        check_product(fresh, artifact, output, query=query)
        wanted, _ = expected("mysql", "G_emission_table_bag", "bag", output.columns)
        require(bag(fresh["rows"]) == bag(wanted), "FRESH_REFINEMENT_VALUES")
        source_records(prefix, artifact.request.sources, query.sources)
        statements = native_statements(prefix)
        require(
            len(prefix["rows"]) == 1
            and prefix["rows"] == fresh["rows"][:1]
            and len(fresh["rows"]) > 1
            and len(statements) == len(prefix["pages"]) == 1,
            "UNOBSERVED_SUFFIX",
        )
        require(
            prefix["outcome"]["delivery"] == "INCOMPLETE"
            and prefix["progress"][2:] == [False, True]
            and prefix["outcome"]["attempt"] != fresh["outcome"]["attempt"]
            and prefix["session"] != fresh["session"]
            and fresh["pages"][0]["ordinal"] == 0
            and fresh["pages"][0]["frontier"] is None,
            "FRESH_ATTEMPT_NOT_CURSOR_REUSE",
        )
        require(
            [x["registry"] for x in prefix["admission"]["sources"]]
            == [x["registry"] for x in fresh["admission"]["sources"]]
            and all(v[-1] == 0 for v in prefix["sessions_gone"].values()),
            "SAME_RETAINED_VERSION",
        )
    check_controls(report.get("controls", []), config.get("controls", []))
    if config.get("source_delta", bool(config.get("controls"))):
        check_source_delta(report["source_delta"], directory / "source-delta")
    else:
        require("source_delta" not in report, "UNDECLARED_SOURCE_DELTA")
    return dict(
        result="PASS_INDEPENDENT_CURRENT_PRODUCT_RECORDS",
        damage_checks=damage_checks,
        cases=len(report["attempts"]),
        origin=config["origin"],
        group=config["group"],
        definition_stability="EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
        native_lifetime_protection="NOT_DEMONSTRATED",
        premise_compliance="NOT_INDEPENDENTLY_VERIFIED",
    )


def check_controls(records, expected):
    require([r["kind"] for r in records] == expected, "CONTROL_DENOMINATOR")
    for r in records:
        kind, outcome = r["kind"], r["outcome"]
        require(
            r["control_joined"]
            and r.get("test_thread_joined", True)
            and len(r["sessions_gone"]) == 2
            and all(v[-1] == 0 for v in r["sessions_gone"].values()),
            "CONTROL_CLEANUP",
        )
        require(
            outcome["cleanup"] in ("LOCAL_CLOSED_REMOTE_UNOBSERVED", "FAILED"),
            "CONTROL_LOCAL_TERMINAL",
        )
        if kind == "late_cancel":
            require(
                outcome["delivery"] == "COMPLETE"
                and outcome["transaction"] == "COMMIT_ACK"
                and r["cancel_return"]["late"]
                and not outcome["cancel_sent"],
                "LATE_CANCEL",
            )
        elif kind == "early_close":
            require(
                outcome["delivery"] == "INCOMPLETE"
                and outcome["source"] != "NOT_STARTED"
                and len(r["rows"]) == 1,
                "EARLY_CLOSE",
            )
        else:
            require(
                r.get("failure")
                and outcome["delivery"] == "FAILED"
                and outcome["primary"] is not None,
                "CONTROL_FAILURE",
            )
        if kind in ("replace_transaction", "commit_loss", "rollback_loss"):
            require(outcome["transaction"] == "UNKNOWN", "UNKNOWN_TRANSACTION")
        if kind.startswith("blocked_"):
            require(
                any(
                    i["kind"] == "actual_native_lock_wait" and i["wait_edges"] > 0
                    for i in r["interventions"]
                ),
                "ACTUAL_BLOCKED_WAIT",
            )
            require(
                outcome["cancel_requested"]
                and outcome["cancel_sent"]
                and any(
                    e[0] == "kill_query_send_returned" for e in r["control_events"]
                ),
                "OWNED_KILL",
            )
        if kind in ("blocked_deadline", "slow_consumer"):
            require(
                r["deadline_expired"] and outcome["cancel_requested"], "ACTUAL_DEADLINE"
            )
        if kind == "prepare_error":
            require(
                r["failure"]["errno"] == 1356
                and r["failure"]["sqlstate"] == "HY000"
                and not r["rows"],
                "NATIVE_PREPARE_ERROR",
            )
        if kind == "close_send_error":
            require(
                any(
                    e["phase"] == "statement_close" for e in outcome["cleanup_failures"]
                ),
                "CLOSE_SEND_FAILURE",
            )


def check_source_delta(records, directory):
    from _pietto_phase68_slice8_probe import component_artifact
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from _pietto_phase68_slice7_probe import encoded
    from pietto._project.project_result_output import prepare_output
    from collections import Counter
    import json

    names = (
        "component_union_all",
        "outside_accepted_scope",
        "nested_definer_invoker",
        "hidden_routine",
        "visible_base_hidden_routine",
    )
    require([r["case"] for r in records] == list(names), "SOURCE_DELTA_DENOMINATOR")
    big = 9007199254740993
    expected = (
        (big, 10),
        (big, None),
        (-big, 20),
        (104, 30),
        (201, 10),
        (202, 40),
        (big, None),
        (204, 60),
    )

    def bag(rows):
        return Counter(json.dumps(r, sort_keys=True) for r in rows)

    require(
        bag(records[0]["rows"]) == bag(encoded(expected)), "COMPONENT_VALUES_DUPLICATES"
    )
    artifact = component_artifact(directory / "component")
    check_product(records[0], artifact, prepare_output(artifact))
    prep = case_preparation(
        directory / "nested",
        "mysql",
        next(c for c in manifest() if c["name"] == "no_request"),
    )
    require(records[2]["rows"] == encoded(((1, None),)), "NESTED_CURRENT_USER_VALUES")
    check_product(records[2], prep.artifact, prepare_output(prep.artifact))
    nested = [p for p in records[2]["security"] if p[1][0] == "p68_scope"]
    require(
        len(nested) == 2 and all(p[3] == "root@%" for p in nested), "INHERITED_DEFINER"
    )
    grants = [
        row[0] for row in records[2]["query_role_grants"] if "p68_scope" in row[0]
    ]
    require(len(grants) == 2, "SCOPED_METADATA_GRANTS")
    base_grants = [g for g in grants if "`private_base`" in g]
    view_grants = [g for g in grants if "`nested`" in g]
    require(
        len(base_grants) == len(view_grants) == 1
        and "SELECT" not in base_grants[0]
        and "REFERENCES" in base_grants[0]
        and "SELECT" in view_grants[0]
        and "SHOW VIEW" in view_grants[0],
        "NO_BASE_SELECT_GRANT",
    )
    for record, category in (
        (records[1], "MYSQL_DEPLOYMENT_PREMISE_SCOPE"),
        (records[3], "MYSQL_VIEW_UNQUALIFIED_CALL"),
        (records[4], "MYSQL_VIEW_UNQUALIFIED_CALL"),
    ):
        require(
            record["failure"]["category"] == category
            and not record["rows"]
            and not record["statements"]
            and record["outcome"]["transaction"] == "ROLLBACK_ACK",
            "SOURCE_REFUSAL_BEFORE_USE",
        )
        if "routine_calls_before" in record:
            for counts in (
                record["routine_calls_before"],
                record["routine_calls_after"],
            ):
                require(
                    len(counts) <= 1
                    and all(
                        r[:3] == ["FUNCTION", "p68_hidden", "read_value"] and r[3] == 0
                        for r in counts
                    ),
                    "NO_ROUTINE_INVOCATION",
                )


def product_record_damages(record, artifact, output, *, query=None, program=None):
    """Small real-record matrix: each mutation exercises a distinct trust boundary."""
    from copy import deepcopy

    damaged = []

    def change(name):
        value = deepcopy(record)
        damaged.append((name, value))
        return value

    change("statement_omission")["statements"].pop()
    change("source_omission")["sources"].pop()
    change("session_omission")["sessions_gone"].pop(str(record["session"]))
    changed = change("coordinated_server_identity")
    changed["context"][14] = changed["epoch"][6] = "foreign-server"
    for obj in changed["sources"]:
        obj["context"][14] = "foreign-server"
    if record["statements"]:
        change("metadata_eof")["statements"][0]["metadata_eof"]["status_flag"] |= 8
        changed = change("actual_rowset_eof_omission")
        binary = False
        eof_events = []
        for event in changed["events"]:
            if event["connection"] != "data":
                continue
            if event["event"] == "get_rows.call":
                binary = event["value"]["binary"]
            if (
                binary
                and event["event"] == "get_rows.return"
                and event["value"]
                and event["value"]["eof"] is not None
            ):
                eof_events.append(event)
        require(bool(eof_events), "DAMAGE_REQUIRES_NATIVE_EOF")
        eof_events[-1]["value"]["eof"] = None
        if record["statements"][0]["arguments"]:
            change("native_parameter_occurrence")["statements"][0]["arguments"].pop()
    if record.get("guard_native", {}).get("uses"):
        change("guard_use_coverage")["guard_native"]["uses"].pop()
    if record.get("guard_states"):
        change("guard_receipt_coverage")["guard_states"].append("FULFILLED")
    if record.get("pages"):
        change("terminal_page_omission")["pages"].pop()
        change("page_progress")["pages"][0]["accepted_progress"][0] += 1
    if record.get("schemas"):
        change("actual_arrow_schema")["schemas"][0][0][1] = "null"
    if record.get("case") == "seven_65_values":
        changed = change("late_bad_native_scalar")
        label = next(c.label for c in output.columns if c.realization.tag == "Int")
        position = next(
            i
            for i, m in enumerate(record["statements"][-1]["metadata"])
            if m[0] == label
        )
        binary = False
        pulls = []
        for event in changed["events"]:
            if event["connection"] != "data":
                continue
            if event["event"] == "get_rows.call":
                binary = event["value"]["binary"]
            if (
                binary
                and event["event"] == "get_rows.return"
                and event["value"]
                and event["value"]["rows"]
            ):
                pulls.append(event["value"]["rows"])
        pulls[-1][-1][position] = {"kind": "int", "value": str(2**80)}
    rejected = []
    for name, bad in damaged:
        try:
            check_product(bad, artifact, output, query=query, program=program)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            rejected.append(name)
        else:
            raise ValueError("S08_DAMAGE_ACCEPTED:" + name)
    return rejected
