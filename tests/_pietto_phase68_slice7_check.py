"""Fresh-root, data-only guard evidence checks; never native execution authority."""

from collections import Counter
from pathlib import Path
import hashlib
import json

from _pietto_phase68_slice6_check import (
    value,
    rebound_admission,
    expected_uses,
    canonical_checked,
)
from _pietto_phase68_slice6_probe import s01
from pietto._project.project_guard_program import (
    GuardParameterUse,
    NativeGuardStatement,
    statement_for,
)
from pietto._project.project_guard_verification import verify_native_guard


def need(condition, category):
    if not condition:
        raise ValueError("S07_RECORD_" + category)


def scalar(item):
    decoded = value(item)
    need(s01.scalar(decoded) == item, "SCALAR_ENCODING")
    return decoded


def bag(rows):
    return Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows
    )


def native_from_record(program, record):
    """Rebind declared identities, then let the independent byte reader check all uses."""
    statement = statement_for(program, record["kind"])
    need(
        record["subjects"]
        == [[s.request_position, s.boundary_position] for s in statement.subjects],
        "SUBJECTS",
    )
    slots = program.preparation.artifact.request.plan.literal_slots
    original_uses = program.preparation.artifact.parameter_uses
    uses = []
    for item in record["uses"]:
        domain = item["domain"]
        if domain == "original":
            need(type(item["slot"]) is int and 0 <= item["slot"] < len(slots), "SLOT")
            owner = slots[item["slot"]]
            matches = tuple(
                u for u in original_uses if u.ordinal == item["original_use"]
            )
            need(
                bool(matches) and all(u is matches[0] for u in matches), "ORIGINAL_USE"
            )
            original = matches[0]
            need(original.slot is owner, "ORIGINAL_SLOT")
        else:
            need(
                domain == "guard"
                and type(item["control"]) is int
                and 0 <= item["control"] < len(statement.controls),
                "CONTROL",
            )
            owner = statement.controls[item["control"]]
            original = None
        uses.append(
            GuardParameterUse(
                domain, owner, item["index"], scalar(item["value"]), original
            )
        )
    native = NativeGuardStatement(
        statement,
        record["sql"].encode(),
        tuple(uses),
        tuple(scalar(v) for v in record["arguments"]),
    )
    verify_native_guard(native)
    return native


def check_statement_inventory(record):
    statements = record["statements"]
    need(type(statements) is list, "STATEMENT_INVENTORY")
    if record["route"] == "postgres_rows":
        cursors = record["cursors"]
        need(
            [c["ordinal"] for c in cursors] == list(range(len(cursors))),
            "CURSOR_INVENTORY",
        )
        need(
            all(c["closed"] and c["session"] == record["session"] for c in cursors),
            "CURSOR_TERMINAL",
        )
        expected = [i for c in cursors for i in c["statements"]]
        need(
            sorted(expected) == list(range(len(statements)))
            and len(expected) == len(set(expected)),
            "CURSOR_STATEMENTS",
        )
        need(
            [s["ordinal"] for s in statements] == list(range(len(statements))),
            "STATEMENT_ORDER",
        )
        for statement in statements:
            need(
                statement["closed"]
                and type(statement["cursor"]) is int
                and 0 <= statement["cursor"] < len(cursors),
                "STATEMENT_CLOSE",
            )
            need(
                statement["ordinal"] in cursors[statement["cursor"]]["statements"],
                "STATEMENT_CURSOR",
            )
            need(
                statement.get("execute_returned") or statement.get("error"),
                "STATEMENT_TERMINAL",
            )
            if statement.get("execute_returned"):
                need(statement["native_status"] in (1, 2), "PG_NATIVE_STATUS")
                fetched = [row for pull in statement["fetches"] for row in pull["rows"]]
                if statement["native_status"] == 2:
                    need(len(fetched) <= statement["native_rows"], "PG_FETCH_COVERAGE")
        need(record["control_joined"] and record["session_gone"], "SESSION_TERMINAL")
    else:
        need(record["closed"] and record["session_gone"], "SESSION_TERMINAL")
        need(record["statement_count"] == len(statements), "STATEMENT_INVENTORY")
        operations = record["operations"]
        need(
            [op["ordinal"] for op in operations] == list(range(len(operations)))
            and all(op["state"] == "terminal" for op in operations),
            "OPERATION_INVENTORY",
        )
        queries = [op for op in operations if op["kind"] == "query"]
        controls = [op for op in operations if op["kind"] == "control"]
        need(
            [s["operation"] for s in statements] == [op["ordinal"] for op in queries],
            "QUERY_OPERATION_COVERAGE",
        )
        need(
            [c["sql"] for c in record["controls"]]
            == [op["sql"] for op in controls if op.get("returned")],
            "CONTROL_OPERATION_COVERAGE",
        )
        for statement, operation in zip(statements, queries, strict=True):
            need(
                statement["sql"] == operation["sql"]
                and statement["parameters"] == operation["arguments"]
                and operation["closed"],
                "OPERATION_CORRESPONDENCE",
            )
        for statement in statements:
            need(statement["statement_cleanup"] == "close_returned", "STATEMENT_CLOSE")
            need(
                statement.get("error")
                or statement["source_terminal"]
                in (
                    "NORMAL",
                    "native_rowset_eof",
                    "arrow_StopIteration",
                    "empty_fetchmany",
                ),
                "STATEMENT_TERMINAL",
            )
        need(
            record["controls"]
            and record["controls"][-1]["sql"] in ("COMMIT", "ROLLBACK")
            and record["controls"][-1]["returned"],
            "TRANSACTION_TERMINAL",
        )


def check_attempt(record, case, program):
    need(record["case"] == case["name"], "CASE")
    need(record["route"] in ("postgres_rows", "mysql_rows", "postgres_adbc"), "ROUTE")
    check_statement_inventory(record)
    choices = case["options"].get("choices", ((case["states"], case["rows"]),))
    encoded = [
        ([*states], [[s01.scalar(v) for v in row] for row in rows])
        for states, rows in choices
    ]
    need(
        any(
            record["guard_states"] == states and bag(record["rows"]) == bag(rows)
            for states, rows in encoded
        ),
        "LITERAL_FULL_RESULTS",
    )
    failure = case["options"].get("failure")
    if "VIOLATED" in record["guard_states"]:
        failure = "SINGLE_MATCH_VIOLATED"
    if failure:
        need(
            record.get("failure", {}).get("category") == failure and not record["rows"],
            "FAILURE_NOT_EMPTY_SUCCESS",
        )
    else:
        need("failure" not in record, "UNEXPECTED_FAILURE")
    if record["route"] == "postgres_rows":
        outcome = record["outcome"]
        need(
            outcome["cleanup"] == "CLOSED" and not outcome["cleanup_failures"],
            "PG_CLEANUP",
        )
        need(
            outcome["transaction"] == ("ROLLBACK_ACK" if failure else "COMMIT_ACK"),
            "PG_TRANSACTION",
        )
        need(
            outcome["source"] == "EOF" if not failure else outcome["source"] != "EOF",
            "PG_SOURCE",
        )
    else:
        need(
            record["transaction"] == ("ROLLBACK_ACK" if failure else "COMMIT_ACK"),
            "BRIDGE_TRANSACTION",
        )
    if failure == "GUARD_SQL_FORBIDDEN_UNFULFILLED":
        need("guard_native" not in record, "FORBIDDEN_SUBMISSION")
        return
    if not record["guard_states"] or all(s == "STATIC" for s in record["guard_states"]):
        expected_kind = "data"
    else:
        expected_kind = "guard" if program.refinement is not None else "combined"
    need(record["guard_native"]["kind"] == expected_kind, "STATEMENT_PURPOSE")
    native = native_from_record(program, record["guard_native"])
    submitted = [s for s in record["statements"] if s["sql"] == native.sql.decode()]
    need(len(submitted) == 1, "EXACT_SUBMISSION")
    raw = submitted[0]
    arguments = (
        raw["arguments"] if record["route"] == "postgres_rows" else raw["parameters"]
    )
    need(arguments == record["guard_native"]["arguments"], "ACTUAL_ARGUMENTS")
    if record["route"] == "postgres_rows":
        need(
            raw.get("execute_returned") and raw["native_status"] == 2,
            "GUARD_NATIVE_TERMINAL",
        )
        rows = [r for pull in raw["fetches"] for r in pull["rows"]]
    else:
        need(not raw.get("error"), "GUARD_NATIVE_TERMINAL")
        rows = raw["actual"]
        s01.verify_submission(
            raw,
            native.sql.decode(),
            [s01.scalar(v) for v in native.arguments],
            record["route"],
        )
    if expected_kind in ("guard", "combined"):
        need(bool(rows), "MISSING_GUARD_RESULT")
        values = [scalar(v) for v in rows[0]]
        flags = (
            values
            if expected_kind == "guard"
            else values[1 : len(native.statement.subjects) + 1]
        )
        need(
            len(flags) == len(native.statement.subjects)
            and all(type(v) is int and v in (0, 1) for v in flags),
            "GUARD_FLAGS",
        )
        need(
            ["VIOLATED" if v else "FULFILLED" for v in flags]
            == [s for s in record["guard_states"] if s != "STATIC"],
            "STATUS_RECEIPT",
        )
        if expected_kind == "combined":
            need(
                type(values[0]) is int
                and values[0] == 0
                and all(v is None for v in values[len(flags) + 1 :]),
                "STATUS_HEADER",
            )
            if failure:
                need(len(rows) == 1, "VIOLATION_CHANNEL")
            else:
                for row in rows[1:]:
                    decoded = [scalar(v) for v in row]
                    need(
                        decoded[0] == 1
                        and all(
                            type(v) is int and v == 0
                            for v in decoded[1 : len(flags) + 1]
                        ),
                        "DATA_CHANNEL",
                    )
                # Native carriers (for example MySQL int01) are decoded by the
                # complete PUBLIC_RECONSUMPTION check below, before comparison.
    if program.refinement is not None and not failure:
        need(record["progress"][2:] == [True, False], "REFINED_COMPLETE")
    reconsume(record, program, native, raw)


def check_origins(origins, expected, *, installed, root):
    need(origins and set(origins) == set(expected), "ORIGIN_DENOMINATOR")
    for name, observed in origins.items():
        need(observed["sha256"] == expected[name], "ORIGIN_BYTES")
        path = Path(observed["path"])
        need(("site-packages" in path.parts) is installed, "ORIGIN_MODE")
        need(
            path.is_absolute() and path.resolve().is_relative_to(root.resolve()),
            "ORIGIN_PATH",
        )


def current_origins(origins, root):
    expected = {}
    for name, observed in origins.items():
        path = Path(observed["path"])
        if "site-packages" in path.parts:
            member = Path(*path.parts[path.parts.index("site-packages") + 1 :])
        else:
            member = path.relative_to(root)
        need(member.parts[0] == "pietto", "ORIGIN_MEMBER")
        expected[name] = hashlib.sha256((root / member).read_bytes()).hexdigest()
    return expected


def metadata(raw, route):
    from types import SimpleNamespace

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


def raw_rows(raw, route):
    return (
        [r for pull in raw["fetches"] for r in pull["rows"]]
        if route == "postgres_rows"
        else raw["actual"]
    )


def reconsume(record, program, native, raw):
    """Recorded observations produce evidence only, never a live PG capability."""
    from dataclasses import replace
    from pietto._project.project_guard_context import ObservedGuardOwner
    from pietto._project.project_guard_runtime import ObservedGuardRequest
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_execution_reader import decode_native_rows
    from pietto._project.project_refinement_enumeration import Enumeration
    from pietto._project.project_refinement_verification import verify_native

    route = record["route"]
    query = program.refinement
    admission = None if query is None else rebound_admission(query, record)
    environment = (
        tuple(record["environment"]) if admission is None else admission.environment
    )
    role = record["role"] if admission is None else admission.role
    sources = tuple(
        (s, ("record-only context; no execution authority",))
        for s in program.preparation.artifact.request.sources
    )
    size = 2 if not record.get("pages") else record["pages"][0]["size"]
    owner = ObservedGuardOwner(
        ObservedGuardRequest(
            program,
            ExecutionLimits(batch_rows=size, seconds=180),
            isolation=environment[1],
        ),
        route=route,
        session_id=record["session"],
        role=role,
        environment=environment,
        sources=sources,
        admissions=admission,
    )
    owner.guards.consume_observed_submission(owner, native)
    rows = tuple(tuple(scalar(v) for v in row) for row in raw_rows(raw, route))
    meta = metadata(raw, route)
    try:
        if native.statement.kind == "guard":
            owner.guards.accept_guard_result(owner, meta, rows, terminal="NORMAL")
        else:
            public_meta = owner.guards.accept_header(
                owner, meta, None if native.statement.kind == "data" else rows[0]
            )
            public = owner.guards.public_rows(
                owner, rows if native.statement.kind == "data" else rows[1:]
            )
            _producer, decoded = decode_native_rows(
                program.output, route, public_meta, public
            )
            need(
                canonical_checked(decoded, program.output.columns) == record["rows"],
                "PUBLIC_RECONSUMPTION",
            )
            owner.close()
            return
    except ValueError as error:
        if str(error) == "SINGLE_MATCH_VIOLATED":
            need(
                record.get("failure", {}).get("category") == str(error)
                and not record["rows"]
                and not record.get("pages"),
                "VIOLATION_RECONSUMPTION",
            )
            owner.close()
            return
        raise
    if query is None:
        raise ValueError("S07_RECORD_REFINED_QUERY")
    try:
        enumeration = Enumeration(
            query, admission, limits=owner.request.limits, _guards=owner.guards
        )
        delivered = []
        need(record.get("pages"), "PAGE_DENOMINATOR")
        for supplied in record["pages"]:
            page = enumeration.request_page()
            need(
                supplied["ordinal"] == page.ordinal
                and supplied["size"] == page.size
                and supplied["uses"] == expected_uses(page, query),
                "PAGE_IDENTITY",
            )
            need(
                supplied["frontier"]
                == (
                    None
                    if page.frontier is None
                    else [s01.scalar(v) for v in page.frontier]
                ),
                "PAGE_FRONTIER",
            )
            need(supplied["erasure"] == [i for i, _ in query.erasure], "PAGE_ERASURE")
            actual = replace(
                page.native,
                sql=supplied["sql"].encode(),
                arguments=tuple(scalar(v) for v in supplied["arguments"]),
            )
            verify_native(actual, query, frontier=page.frontier, size=page.size)
            matches = [
                s
                for s in record["statements"]
                if s["sql"] == supplied["sql"]
                and (s["arguments"] if route == "postgres_rows" else s["parameters"])
                == supplied["arguments"]
            ]
            need(len(matches) == 1, "PAGE_ACTUAL_SUBMISSION")
            observed = matches[0]
            if route != "postgres_rows":
                s01.verify_submission(
                    observed, supplied["sql"], supplied["arguments"], route
                )
            values = tuple(
                tuple(scalar(v) for v in row) for row in raw_rows(observed, route)
            )
            checked = enumeration.check_page(
                page, metadata(observed, route), values, terminal="NORMAL"
            )
            delivered.extend(canonical_checked(checked.rows, query.output.columns))
            enumeration.commit_page(checked)
            need(
                supplied["accepted_progress"] == list(enumeration.progress),
                "PAGE_PROGRESS",
            )
        need(
            record["progress"] == list(enumeration.progress)
            and enumeration.progress[2]
            and not enumeration.progress[3],
            "PAGE_COMPLETION",
        )
        need(delivered == record["rows"], "COMPLETE_PAGE_RESULTS")
    finally:
        owner.close()


def check_control(record, name):
    """The observed control kind, native work and product outcome stay distinct."""
    check_statement_inventory(record)
    outcomes = record["outcome"]
    states = record["guard_states"]
    events = record["interventions"]
    need(
        (events or name == "native_guard_error")
        and record["session_gone"]
        and record["control_joined"],
        "CONTROL_DENOMINATOR",
    )
    if name in ("writer_version", "ddl_block"):
        need(
            "failure" not in record
            and outcomes["transaction"] == "COMMIT_ACK"
            and outcomes["source"] == "EOF",
            "CONTROL_SUCCESS",
        )
        need(states == ["FULFILLED"], "CONTROL_GUARD")
        if name == "writer_version":
            need(
                [e["kind"] for e in events]
                == ["guard_fulfilled", "writer_begin", "writer_commit"],
                "WRITER_ORDER",
            )
            need(
                events[1]["boundary"] == "after_guard_before_page"
                and events[2]["old_rows_retained"],
                "WRITER_CONTEXT",
            )
            guard_sql = record["guard_native"]["sql"]
            guard_index = next(
                i for i, s in enumerate(record["statements"]) if s["sql"] == guard_sql
            )
            need(
                record["pages"]
                and all(
                    next(
                        i
                        for i, s in enumerate(record["statements"])
                        if s["sql"] == p["sql"]
                    )
                    > guard_index
                    for p in record["pages"]
                ),
                "GUARD_BEFORE_PAGES",
            )
        else:
            need(
                any(
                    e.get("kind") == "actual_ddl_block" and e.get("sqlstate") == "55P03"
                    for e in events
                ),
                "DDL_REAL_BLOCK",
            )
        return
    need(
        record.get("failure")
        and outcomes["transaction"]
        in ("ROLLBACK_ACK", "UNKNOWN", "NOT_STARTED", "COMMIT_ACK"),
        "CONTROL_FAILURE",
    )
    if name == "consumer_error":
        need(
            record["failure"]["category"] == "injected consumer error"
            and outcomes["source"] != "EOF"
            and states == ["FULFILLED"],
            "CONSUMER_LAYERS",
        )
        return
    if name in ("commit_loss", "cleanup_error"):
        need(
            outcomes["source"] == "EOF" and states == ["FULFILLED"],
            "FINALIZATION_LAYERS",
        )
        need(
            any(
                e["kind"]
                == (
                    "injected_commit_response_loss"
                    if name == "commit_loss"
                    else "injected_cursor_close_error"
                )
                for e in events
            ),
            "INJECTION_LABEL",
        )
        if name == "commit_loss":
            need(outcomes["transaction"] == "UNKNOWN", "COMMIT_UNKNOWN")
        else:
            need(outcomes["cleanup_failures"], "CLEANUP_FAILURE_RETAINED")
        return
    need(not record["rows"] and not record.get("pages"), "CONTROL_NO_PROGRESS")
    if name in ("native_guard_error", "cancel_guard", "deadline_guard"):
        actual = [
            s for s in record["statements"] if s["sql"] == record["guard_native"]["sql"]
        ]
        need(
            len(actual) == 1
            and actual[0].get("error", {}).get("sqlstate")
            == ("22012" if name == "native_guard_error" else "57014")
            and not actual[0].get("execute_returned"),
            "ACTUAL_NATIVE_GUARD_ERROR",
        )
        need(
            record["failure"]["sqlstate"]
            == ("22012" if name == "native_guard_error" else "57014"),
            "REAL_GUARD_ERROR",
        )
        need(
            states == ["UNKNOWN"] and outcomes["transaction"] == "ROLLBACK_ACK",
            "GUARD_ERROR_UNFULFILLED",
        )
        if name != "native_guard_error":
            need(
                any(e["kind"] == "actual_blocked_guard" for e in events)
                and any(e["kind"] == "thread_joined" for e in events),
                "REAL_BLOCKED_GUARD",
            )
        if name == "deadline_guard":
            need(record["deadline_expired"], "REAL_DEADLINE")
        return
    categories = {
        "pre_cancel": "EXECUTION_PRE_CANCELED",
        "cancel_verify": "EXECUTION_CANCELED",
        "deadline_verify": "EXECUTION_DEADLINE",
        "cancel_after_guard": "EXECUTION_CANCELED",
        "incomplete_guard_read": "GUARD_STATUS_ARITY",
        "transaction_graft": "GUARD_TRANSACTION_CHANGED",
        "role_graft": "GUARD_LIVE_CONTEXT",
    }
    need(record["failure"]["category"] == categories[name], "CONTROL_CATEGORY")
    if name in ("cancel_after_guard", "transaction_graft", "role_graft"):
        need(states == ["FULFILLED"], "COMPLETED_GUARD_DISTINCT_FROM_DELIVERY")
    else:
        need(
            not states
            or all(
                s in ("PENDING", "RUNNING", "UNKNOWN", "NOT_STARTED") for s in states
            ),
            "UNFULFILLED_CONTROL",
        )


def check_bridge_control(record, control):
    check_statement_inventory(record)
    expected = {
        "cancel_verify": "EXECUTION_CANCELED",
        "deadline_verify": "EXECUTION_DEADLINE",
        "incomplete_guard_read": "GUARD_STATUS_ARITY",
    }
    need(record["failure"]["category"] == expected[control], "BRIDGE_CONTROL_CATEGORY")
    need(
        not record["rows"]
        and record["guard_states"] == ["UNKNOWN"]
        and record["transaction"] == "ROLLBACK_ACK",
        "BRIDGE_CONTROL_NO_FULFILLMENT",
    )
    need(
        record["interventions"]
        and all(
            e.get("native_rowset_observed") is True for e in record["interventions"]
        ),
        "BRIDGE_CONTROL_MEANING",
    )
    matching = [
        s for s in record["statements"] if s["sql"] == record["guard_native"]["sql"]
    ]
    need(
        len(matching) == 1 and not matching[0].get("error"),
        "BRIDGE_CONTROL_ACTUAL_GUARD",
    )


def actual_record_damages(record, case, program):
    """Damage copies of real acquired records, preserving the immutable raw file."""
    from copy import deepcopy

    if "guard_native" not in record:
        return []
    mutations = []
    changed = deepcopy(record)
    sql = changed["guard_native"]["sql"]
    changed["guard_native"]["sql"] += " WHERE TRUE"
    for statement in changed["statements"]:
        if statement["sql"] == sql:
            statement["sql"] = changed["guard_native"]["sql"]
    mutations.append(("coordinated_sql", changed))
    changed = deepcopy(record)
    changed["guard_states"] = ["FULFILLED"] * (len(record["guard_states"]) + 1)
    mutations.append(("receipt_coverage", changed))
    changed = deepcopy(record)
    changed["session_gone"] = False
    mutations.append(("live_session", changed))
    changed = deepcopy(record)
    changed["statements"] = changed["statements"][:-1]
    if "statement_count" in changed:
        changed["statement_count"] = len(changed["statements"])
    mutations.append(("statement_omission", changed))
    if record["guard_native"]["uses"]:
        changed = deepcopy(record)
        changed["guard_native"]["uses"] = changed["guard_native"]["uses"][:-1]
        mutations.append(("parameter_use_omission", changed))
    changed = deepcopy(record)
    changed["rows"] = changed["rows"] + [
        [{"kind": "null"} for _ in program.output.columns]
    ]
    mutations.append(("coordinated_empty_or_value", changed))
    if record.get("pages"):
        changed = deepcopy(record)
        changed["pages"] = changed["pages"][:-1]
        mutations.append(("page_omission", changed))
    rejected = []
    for name, damaged in mutations:
        try:
            check_attempt(damaged, case, program)
        except (ValueError, TypeError, KeyError, IndexError, AttributeError):
            rejected.append(name)
        else:
            raise ValueError("S07_RECORD_DAMAGE_ACCEPTED:" + name)
    return rejected


def check_worker_denominator(record, cases, controls):
    need([a["case"] for a in record["attempts"]] == list(cases), "WORKER_CASES")
    need(
        [a["control"] for a in record.get("control_attempts", [])] == list(controls),
        "WORKER_CONTROLS",
    )
    for item in record.get("control_attempts", []):
        if item["control"] == "writer_version":
            need("new_attempt" in item, "WRITER_NEW_ATTEMPT")
            later = item["new_attempt"]
            check_statement_inventory(later)
            need(
                later["session"] != item["session"] and later.get("damage_rejections"),
                "WRITER_NEW_SESSION",
            )
    for item in record["attempts"]:
        if item["case"] == "ordinary_tied_subject":
            need("same_snapshot_tie_contrast" in item, "TIE_REFERENCE")
            check_tie_contrast(item["same_snapshot_tie_contrast"], record["route"])


def check_tie_contrast(record, route):
    pg = route != "mysql_rows"
    context_sql = (
        "SELECT pg_backend_pid(),current_user,current_setting('transaction_isolation'),current_setting('transaction_read_only'),pg_current_xact_id()::text"
        if pg
        else "SELECT VERSION(),@@transaction_isolation,@@character_set_connection,CURRENT_USER(),CONNECTION_ID()"
    )
    need(
        record["closed"]
        and record["session_close_observations"]
        and record["session_close_observations"][-1] == 0,
        "TIE_SESSION_CLOSE",
    )
    need(
        [c["sql"] for c in record["controls"]]
        == [
            "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY"
            if pg
            else "START TRANSACTION READ ONLY",
            "COMMIT",
        ]
        and all(c["returned"] for c in record["controls"]),
        "TIE_TRANSACTION",
    )
    need(
        len(record["contexts"]) == 2 and len(record["statements"]) == 2,
        "TIE_STATEMENTS",
    )
    for raw in record["contexts"] + record["statements"]:
        need(
            not raw.get("error")
            and raw["source_terminal"]
            in ("native_rowset_eof", "arrow_StopIteration", "empty_fetchmany")
            and raw["statement_cleanup"] == "close_returned",
            "TIE_NATIVE_TERMINAL",
        )
    contexts = []
    for raw in record["contexts"]:
        s01.verify_submission(raw, context_sql, [], route)
        need(
            not raw.get("error")
            and raw["statement_cleanup"] == "close_returned"
            and len(raw["actual"]) == 1,
            "TIE_CONTEXT",
        )
        contexts.append([scalar(v) for v in raw["actual"][0]])
        if not pg:
            need(
                raw["native"]["terminal"]["packet"]["status_flag"] & 8192,
                "TIE_READ_ONLY",
            )
    need(
        contexts[0] == contexts[1]
        and (
            contexts[0][:3] if pg else [contexts[0][4], contexts[0][3], contexts[0][1]]
        )
        == [
            record["session"],
            "pietto_query" if pg else "pietto_query@%",
            "repeatable read" if pg else "REPEATABLE-READ",
        ],
        "TIE_SAME_CONTEXT",
    )
    if pg:
        need(contexts[0][3] == "on" and bool(contexts[0][4]), "TIE_NATIVE_TRANSACTION")
    else:
        need(contexts[0][2] == "utf8mb4", "TIE_NATIVE_ENCODING")
    q = '"' if pg else "`"

    def field(name):
        return q + name + q

    relation = field("public" if pg else "phase66") + "." + field("phase66 rhs é")
    identity, key = field("order.id"), field("key value")
    for i, raw in enumerate(record["statements"]):
        order = key + (",token" if i == 0 else "," + identity + ",token")
        sql = (
            "SELECT "
            + identity
            + ","
            + key
            + " FROM "
            + relation
            + " ORDER BY "
            + order
            + " LIMIT 2"
        )
        s01.verify_submission(raw, sql, [], route)
        rows = [[scalar(v) for v in row] for row in raw["actual"]]
        need(
            not raw.get("error")
            and raw["statement_cleanup"] == "close_returned"
            and rows == ([[1, 0], [2, 0]] if i == 0 else [[1, 0], [1, 0]]),
            "TIE_NATIVE_VALUES",
        )
