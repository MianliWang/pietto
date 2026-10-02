"""Independent S09 raw-record consumer; never creates a live execution owner."""

from collections import Counter
from dataclasses import replace
import json
import hashlib
from pathlib import Path
import subprocess
import tarfile
import zipfile

from _pietto_phase68_slice6_check import (
    value,
    expected_uses,
    rebound_admission,
    canonical_checked,
)
from _pietto_phase68_slice5_probe import oracle_values
from _pietto_phase68_slice5_cases import expected as ordinary_expected, seven_rows
from _pietto_phase68_slice7_probe import encoded
from _pietto_phase68_slice7_check import native_from_record
from pietto._project.project_postgres_source_assurance import CatalogReply, SQL
from pietto._project.project_postgres_source_assurance_verification import (
    verify_catalog,
)
from pietto._project.project_execution_postgres_adbc_native import (
    NativeReply,
    CONTEXT_SQL,
)
from pietto._project.project_execution import ExecutionLimits
from pietto._project.project_execution_reader import decode_native_rows
from pietto._project.project_refinement_enumeration import Enumeration
from pietto._project.project_refinement_verification import verify_native


def need(condition, code):
    if not condition:
        raise ValueError("S09_RECORD_" + code)


def exact(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(
        right, sort_keys=True, separators=(",", ":")
    )


def bag(rows):
    return Counter(
        json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows
    )


def tuples(value):
    return tuple(tuples(v) for v in value) if type(value) is list else value


def native_reply(d):
    return NativeReply(
        d["sql"].encode(), tuples(d["arguments"]), tuples(d["rows"]), d["terminal"]
    )


def check_worker_inputs(report, config):
    from _pietto_phase68_executor_cases import PINS

    root = Path(__file__).resolve().parents[1]
    inputs_path = Path(config["inputs"])
    inputs = json.loads(inputs_path.read_text())
    need(inputs["tree"] == config["tree"] == report["tree"], "PRODUCING_TREE")
    archive_path = inputs_path.with_suffix(".tar")
    need(
        hashlib.sha256(archive_path.read_bytes()).hexdigest()
        == inputs["archive_sha256"],
        "INPUT_ARCHIVE",
    )
    blobs = {}
    for line in subprocess.check_output(
        ["git", "ls-tree", "-r", "--format=%(objectname) %(path)", inputs["tree"]],
        cwd=root,
        text=True,
    ).splitlines():
        oid, name = line.split(" ", 1)
        if name.startswith(("src/", "tests/", "scripts/")) or name in (
            "ci/phase68-executor-premise-requirements.txt",
            "pyproject.toml",
            "uv.lock",
        ):
            blobs[name] = oid
    actual = {}
    with tarfile.open(archive_path) as archive:
        for member in archive:
            if member.isfile():
                stream = archive.extractfile(member)
                need(stream is not None, "INPUT_MEMBER")
                if stream is None:
                    raise ValueError("S09_RECORD_INPUT_MEMBER")
                raw = stream.read()
                need(
                    member.name in blobs
                    and hashlib.sha1(
                        b"blob " + str(len(raw)).encode() + b"\0" + raw
                    ).hexdigest()
                    == blobs[member.name],
                    "INPUT_GIT_BLOB",
                )
                actual[member.name] = hashlib.sha256(raw).hexdigest()
    need(
        actual == inputs["files"] and set(actual) == set(blobs), "COMPLETE_INPUT_FILES"
    )
    wheel = Path(config["wheel"])
    need(
        hashlib.sha256(wheel.read_bytes()).hexdigest() == config["wheel_sha256"],
        "WHEEL_BYTES",
    )
    with zipfile.ZipFile(wheel) as archive:
        members = {
            "src/" + n: hashlib.sha256(archive.read(n)).hexdigest()
            for n in archive.namelist()
            if n.startswith("pietto/") and n.endswith(".py")
        }
    need(
        members
        == {
            n: h
            for n, h in actual.items()
            if n.startswith("src/pietto/") and n.endswith(".py")
        },
        "WHEEL_SOURCE_CORRESPONDENCE",
    )
    profile = Path(config["profile"])
    runtime = report["runtime"]
    need(
        runtime["versions"] == PINS
        and Path(runtime["executable"]) == profile / "bin/python",
        "RUNTIME_PROFILE",
    )
    base = (
        root / "src"
        if config["origin"] == "source"
        else profile / "lib/python3.13/site-packages"
    )
    required = {
        "pietto._project.project_execution_postgres_adbc",
        "pietto._project.project_execution_postgres_adbc_native",
        "pietto._project.project_postgres_source_assurance",
        "pietto._project.project_postgres_source_assurance_verification",
    }
    need(
        required <= set(report["origins_before"]) <= set(report["origins"]),
        "ORIGINS_BEFORE_NATIVE",
    )
    for name, origin in report["origins"].items():
        path = Path(origin["path"])
        need(path.is_relative_to(base), "LOADED_ORIGIN_PATH")
        key = "src/" + path.relative_to(base).as_posix()
        need(origin["sha256"] == actual.get(key), "LOADED_ORIGIN_BYTES")
        if name in report["origins_before"]:
            need(
                origin == report["origins_before"][name], "ORIGIN_CHANGED_DURING_WORKER"
            )
    for filename, digest in runtime["libraries"].items():
        path = Path(filename)
        need(
            path.is_relative_to(profile)
            and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
            "PINNED_LIBRARY_BYTES",
        )
    return {
        "loaded_modules": len(report["origins"]),
        "wheel_sha256": config["wheel_sha256"],
    }


def check_native(record):
    if "post_close_rows" in record:
        need(
            exact(record["rows"], record["post_close_rows"]), "POST_CLOSE_BATCH_VALUES"
        )
    history = record["session_gone"]
    need(
        record["control_joined"]
        and type(history) is list
        and 0 < len(history) <= 20
        and all(type(n) is int and n >= 0 for n in history)
        and history[-1] == 0
        and all(n != 0 for n in history[:-1]),
        "SESSION_TERMINAL",
    )
    statements = record["statements"]
    if statements and "finalizing" in statements[0]:
        for i, statement in enumerate(statements):
            if statement["sql"] in ("COMMIT", "ROLLBACK") and statement["finalizing"]:
                need(
                    i > 0
                    and statements[i - 1]["sql"] == CONTEXT_SQL
                    and statements[i - 1]["finalizing"] is True
                    and exact(
                        statements[i - 1]["raw_rows"],
                        encoded((tuple(record["context"]),)),
                    ),
                    "FINALIZATION_TRANSACTION_IDENTITY",
                )
    for s in statements:
        need(
            s["statement_close"] == "RETURNED" and s["reader_close"] == "RETURNED",
            "HANDLE_CLOSE",
        )
        need(
            s["terminal"] == "NORMAL" and not s.get("raw_capture_incomplete"),
            "NATIVE_EOF",
        )
        need(sum(p[0] for p in s["pulls"]) == len(s["raw_rows"]), "FULL_RAW_VALUES")
        wanted = (
            ["set_sql_query", "prepare"]
            + (["bind"] if s["arguments"] else [])
            + ["execute_query"]
        )
        need([c["method"] for c in s["api"]] == wanted, "ACTUAL_API_SEQUENCE")
        need(s["api"][0]["sql"] == s["sql"], "ACTUAL_SQL")
        if s["arguments"]:
            bind = s["api"][2]
            need(exact(bind["rows"], [s["arguments"]]), "ACTUAL_BIND_VALUES")
            types = {
                "Int": "int64",
                "Bool": "bool",
                "Float": "double",
                "Text": "string",
                "Decimal": "string",
            }
            need(bind["schema"] == [types[t] for t in s["types"]], "ACTUAL_BIND_TYPES")
        need(
            type(s["copy"]) is bool and s["copy"] == (s["purpose"] != "control"),
            "COPY_PURPOSE",
        )
    context = record["context"]
    actual = [s for s in record["statements"] if s["sql"] == CONTEXT_SQL]
    need(
        actual
        and all(exact(s["raw_rows"], encoded((tuple(context),))) for s in actual),
        "NATIVE_CONTEXT",
    )
    raw = record["native_context"]
    need(
        raw["sql"] == CONTEXT_SQL
        and exact(raw["rows"], [context])
        and raw["terminal"] == "NORMAL",
        "NATIVE_CONTEXT_REPLY",
    )
    premise = record["premise"]
    need(
        premise["route"] == "postgres_adbc"
        and premise["basis"] == "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
        "PREMISE",
    )
    need(
        premise["access"]["database"] == context[1]
        and premise["access"]["user"] == context[2] == context[3],
        "ACCESS_CONTEXT",
    )
    q = record["qualification"]
    need(
        q["basis"] == "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        and q["compliance"] == "NOT_INDEPENDENTLY_VERIFIED"
        and q["native_lifetime"] == "NOT_DEMONSTRATED",
        "ASSURANCE_CLAIMS",
    )
    need(exact(q["context"], context), "SOURCE_CONTEXT")
    catalog = [s for s in record["statements"] if s["sql"] in SQL.values()]
    need(len(catalog) == len(q["replies"]), "CATALOG_DENOMINATOR")
    replies = []
    for r, s in zip(q["replies"], catalog, strict=True):
        need(
            s["sql"] == SQL[r["kind"]]
            and exact(s["arguments"], encoded((tuple(r["arguments"]),))[0])
            and exact(s["raw_rows"], encoded(tuples(r["rows"]))),
            "CATALOG_NATIVE_CORRESPONDENCE",
        )
        replies.append(
            CatalogReply(
                r["kind"],
                tuples(r["arguments"]),
                tuples(r["rows"]),
                native_reply(r["native"]),
            )
        )
    roots = tuples(q["roots"])
    root_oids = []
    for root in roots:
        matches = [v for v in replies if v.kind == "resolve" and v.arguments == root]
        need(len(matches) == 1, "ROOT_RESOLUTION")
        root_oids.append(matches[0].rows[0][0])
    paths = verify_catalog(
        roots,
        tuple(root_oids),
        tuple(replies),
        tuple(context),
        tuple(premise["schemas"]),
        native_reply(raw),
    )
    need(exact(paths, q["paths"]), "COMPLETE_SECURITY_PATHS")


def check_rows(record, output, statement):
    producer, decoded = decode_native_rows(
        output,
        "postgres_adbc",
        tuple(statement["schema"]),
        tuple(tuple(value(v) for v in row) for row in statement["raw_rows"]),
    )
    need(
        exact(canonical_checked(decoded, output.columns), record["rows"]),
        "RAW_PUBLIC_CORRESPONDENCE",
    )
    from pietto._project.project_arrow_result import bind_arrow

    expected = [[f.name, str(f.type), f.nullable] for f in bind_arrow(producer).schema]
    need(
        exact(expected, record["bound_schema"])
        and all(exact(s, expected) for s in record["schemas"]),
        "COMPLETE_OUTPUT_SCHEMA",
    )


def check_pages(record, query, *, guards=None, complete=True):
    admission = rebound_admission(query, record)
    statements = [s for s in record["statements"] if s["purpose"] == "page"]
    need(statements and len(statements) == len(record["pages"]), "PAGE_DENOMINATOR")
    size = record["pages"][0]["page"]["size"]
    enumeration = Enumeration(
        query,
        admission,
        limits=ExecutionLimits(batch_rows=size, seconds=180),
        _guards=guards,
    )
    delivered = []
    for supplied, raw in zip(record["pages"], statements, strict=True):
        page = enumeration.request_page()
        info = supplied["page"]
        need(
            info["ordinal"] == page.ordinal
            and info["size"] == page.size
            and info["erasure"] == [p for p, _ in query.erasure]
            and exact(info["uses"], expected_uses(page, query)),
            "PAGE_IDENTITY_USES",
        )
        need(
            exact(
                info["frontier"],
                None if page.frontier is None else encoded((page.frontier,))[0],
            ),
            "PAGE_FRONTIER",
        )
        actual = replace(
            page.native,
            sql=raw["sql"].encode(),
            arguments=tuple(value(v) for v in raw["arguments"]),
        )
        verify_native(actual, query, frontier=page.frontier, size=page.size)
        checked = enumeration.check_page(
            page,
            tuple(raw["schema"]),
            tuple(tuple(value(v) for v in row) for row in raw["raw_rows"]),
            terminal=raw["terminal"],
        )
        delivered.extend(canonical_checked(checked.rows, query.output.columns))
        enumeration.commit_page(checked)
        need(exact(enumeration.progress, supplied["progress"]), "PAGE_PROGRESS")
    need(
        enumeration.progress[2] is complete and exact(delivered, record["rows"]),
        "COMPLETE_ENUMERATION",
    )


def check_attempt(record, config, artifact, output, *, program=None, case=None):
    check_native(record)
    roots = [[s.namespace, s.name] for s in artifact.request.sources]
    need(
        exact(roots, record["premise"]["roots"])
        and exact(record["qualification"]["roots"][: len(roots)], roots),
        "ORIGINAL_ROOTS",
    )
    data = [
        s for s in record["statements"] if s["purpose"] in ("query", "guard", "page")
    ]
    group = config["group"]
    failure = None
    if group == "guarded":
        if program is None or case is None:
            raise ValueError("S09_RECORD_GUARD_INPUT_REQUIRED")
        from pietto._project.project_guard_context import ObservedGuardOwner
        from pietto._project.project_guard_runtime import ObservedGuardRequest

        choices = case["options"].get("choices", ((case["states"], case["rows"]),))
        need(
            any(
                record["guard_states"] == list(states)
                and bag(record["rows"]) == bag(encoded(rows))
                for states, rows in choices
            ),
            "GUARD_JOINT_LITERAL_RESULTS",
        )
        failure = case["options"].get("failure")
        if "VIOLATED" in record["guard_states"]:
            failure = "SINGLE_MATCH_VIOLATED"
        if failure == "GUARD_SQL_FORBIDDEN_UNFULFILLED":
            need(not data and "guard_native" not in record, "FORBIDDEN_SUBMISSION")
        else:
            native = native_from_record(program, record["guard_native"])
            need(
                data
                and data[0]["sql"] == native.sql.decode()
                and exact(data[0]["arguments"], encoded((native.arguments,))[0]),
                "GUARD_ACTUAL_SUBMISSION",
            )
            admission = (
                None
                if program.refinement is None
                else rebound_admission(program.refinement, record)
            )
            observer = ObservedGuardOwner(
                ObservedGuardRequest(
                    program,
                    ExecutionLimits(batch_rows=2, seconds=180),
                    isolation=record["context"][8],
                ),
                route="postgres_adbc",
                session_id=record["context"][6],
                role=record["context"][2],
                environment=(
                    artifact.request.release,
                    record["context"][8],
                    True,
                    "UTF8",
                ),
                sources=tuple((s, ("data-only",)) for s in artifact.request.sources),
                admissions=admission,
            )
            observer.guards.consume_observed_submission(observer, native)
            rows = tuple(tuple(value(v) for v in row) for row in data[0]["raw_rows"])
            try:
                if native.statement.kind == "guard":
                    observer.guards.accept_guard_result(
                        observer, tuple(data[0]["schema"]), rows, terminal="NORMAL"
                    )
                else:
                    metadata = observer.guards.accept_header(
                        observer,
                        tuple(data[0]["schema"]),
                        rows[0] if native.statement.kind == "combined" else None,
                    )
                    public = observer.guards.public_rows(
                        observer,
                        rows[1:] if native.statement.kind == "combined" else rows,
                    )
                    _, decoded = decode_native_rows(
                        output, "postgres_adbc", metadata, public
                    )
                    need(
                        exact(
                            canonical_checked(decoded, output.columns), record["rows"]
                        ),
                        "GUARD_RAW_PUBLIC",
                    )
            except ValueError as error:
                need(
                    failure == "SINGLE_MATCH_VIOLATED"
                    and str(error) == "SINGLE_MATCH_VIOLATED",
                    "GUARD_FAILURE_CORRESPONDENCE",
                )
            if program.refinement is not None and not failure:
                check_pages(record, program.refinement, guards=observer.guards)
    elif group == "refined":
        from _pietto_phase68_slice6_check import expected

        query = output
        check_pages(record, query)
        literal, ordered = expected(
            "postgres", record["case"], record["variant"], query.output.columns
        )
        need(
            bag(literal) == bag(record["rows"])
            and (not ordered or exact(literal, record["rows"])),
            "ORIGINAL_REFINED_VALUES",
        )
    else:
        from _pietto_phase66_sql_emission_probe import decode_public, decoded_arguments

        if record["case"] == "seven":
            from _pietto_phase68_slice5_probe import seven_sql

            precision, state = record["variant"].split("_")
            document = record["public"]
            need(
                document["sql"] == seven_sql(int(precision), state),
                "SEVEN_ORIGINAL_SQL",
            )
            expected_arguments = []
        else:
            document = decode_public(json.dumps(record["public"]).encode())
            expected_arguments = encoded((tuple(decoded_arguments(document)),))[0]
        need(
            len(data) == 1
            and data[0]["sql"] == document["sql"] == artifact.rendered.sql.decode(),
            "ORIGINAL_SQL",
        )
        need(
            exact(data[0]["arguments"], expected_arguments),
            "ORIGINAL_ARGUMENTS",
        )
        check_rows(record, output, data[0])
        if record["case"] == "seven":
            precision, state = record["variant"].split("_")
            literal = encoded(
                seven_rows("postgres", int(precision))
                if state == "values"
                else [(None,) * 9]
                if state == "null"
                else ()
            )
            import _pietto_phase67_result_product_probe as seven

            types = [
                "timestamp[us]",
                "timestamp[us]",
                "extension<arrow.uuid>",
                "extension<arrow.uuid>",
                "int32",
                "bool",
                "double",
                "string",
                f"decimal256({precision}, {4 if precision == '39' else 30})",
            ]
            need(
                record["bound_schema"]
                == [
                    [name, typ, True]
                    for name, typ in zip(seven.TEMPORAL_LABELS, types, strict=True)
                ],
                "SEVEN_LOGICAL_SCHEMA",
            )
            ordered = False
        else:
            raw, ordered = ordinary_expected(
                "postgres", record["case"], record["variant"]
            )
            literal = oracle_values(raw, document["columns"])
        need(
            bag(literal) == bag(record["rows"])
            and (not ordered or exact(literal, record["rows"])),
            "ORIGINAL_LITERAL_VALUES",
        )
    outcome = record["outcome"]
    need(
        outcome["cleanup"] == "LOCAL_CLOSED_REMOTE_UNOBSERVED"
        and not outcome["cleanup_failures"],
        "CLEANUP",
    )
    if failure:
        need(
            record["failure"] is not None
            and record["failure"]["message"] == failure
            and not record["rows"]
            and outcome["transaction"] == "ROLLBACK_ACK"
            and outcome["delivery"] == "FAILED",
            "EXPECTED_FAILURE",
        )
    else:
        need(
            record["failure"] is None
            and (outcome["source"], outcome["transaction"], outcome["delivery"])
            == ("EOF", "COMMIT_ACK", "COMPLETE"),
            "LAYERED_SUCCESS",
        )
        need(outcome["rows"] == len(record["rows"]), "DELIVERY_COUNT")


def check_worker(report, config, directory):
    from _pietto_phase68_slice6_cases import original, source_requirements
    from _pietto_phase68_slice7_cases import manifest, case_preparation
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_guard_program import prepare_program
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_execution_source import RetainedSourceRequirement
    from pietto._project.project_refinement import prepare_refinement, TieRefinement

    if "inputs" in config:
        check_worker_inputs(report, config)
        if config.get("finalization_context_required"):
            need(
                all(
                    all(type(s.get("finalizing")) is bool for s in r["statements"])
                    for r in report["attempts"]
                ),
                "FINALIZATION_CAPTURE_REQUIRED",
            )
        need(
            all("post_close_rows" in r for r in report["attempts"]),
            "BATCH_LIFETIME_EVIDENCE",
        )
    need(
        report["tree"] == config["tree"]
        and report["origin"] == config["origin"]
        and report["group"] == config["group"],
        "ORIGIN_CONTEXT",
    )
    need(
        report["acquisition"] == "FINISHED_REQUIRES_INDEPENDENT_CHECK"
        and report["manager_local_closed"],
        "WORKER_TERMINAL",
    )
    need(len(report["attempts"]) == len(config["cases"]), "ATTEMPT_DENOMINATOR")
    template = first = None
    for i, (record, selected) in enumerate(
        zip(report["attempts"], config["cases"], strict=True)
    ):
        need(
            record["case"] == selected["family"]
            and record["variant"] == selected.get("variant"),
            "CASE_ORDER",
        )
        root = directory / str(i)
        binding = query = program = case = None
        if config["group"] == "guarded":
            case = next(c for c in manifest() if c["name"] == record["case"])
            if "binding_values" in case["options"]:
                if template is None:
                    template = prepare_guarded_template(
                        case_preparation(root, "postgres", case)
                    )
                binding = (
                    first
                    if case["name"] == "binding_A_again"
                    else bind_values(
                        template,
                        tuple(
                            zip(
                                template.slots,
                                case["options"]["binding_values"],
                                strict=True,
                            )
                        ),
                    )
                )
                if case["name"] == "binding_A":
                    first = binding
                if binding is None:
                    raise ValueError("S09_RECORD_ORIGINAL_BINDING_REQUIRED")
                preparation = binding.guarded
            else:
                preparation = case_preparation(root, "postgres", case)
            artifact = preparation.artifact
            output = prepare_guarded_output(preparation, binding=binding)
            if case["options"].get("refined"):
                requirements = []
                for source, obs in zip(
                    artifact.request.sources,
                    record["admission"]["sources"],
                    strict=True,
                ):
                    side = "lhs" if source.name == "phase66 lhs é" else "rhs"
                    requirements.append(
                        RetainedSourceRequirement(
                            source,
                            "p68-guard-" + side,
                            "v1",
                            "r1",
                            source.namespace,
                            "p68_guard_registry_" + side,
                            obs["definition"],
                            ("token",),
                            record["context"][2],
                            "Original controlled retained-source fixture promise; no live authority.",
                        )
                    )
                query = prepare_refinement(
                    artifact, tuple(requirements), policy=TieRefinement(), output=output
                )
            program = prepare_program(preparation, binding=binding, refinement=query)
            output = program.output
        else:
            artifact = original(
                root,
                "postgres",
                "R2_seven" if record["case"] == "seven" else record["case"],
                record["variant"],
            )
            need(artifact is not None, "ORIGINAL_COMPILER_RESULT")
            output = prepare_output(artifact)
            if config["group"] == "refined":
                output = prepare_refinement(
                    artifact,
                    source_requirements(artifact, config["providers"], "pietto_query"),
                    policy=TieRefinement(),
                    output=output,
                )
        if config.get("fresh_stage") == "prefix":
            need(config["group"] == "refined", "PREFIX_ENTRY")
            check_native(record)
            check_pages(record, output, complete=False)
            need(
                record["failure"] is None
                and (
                    record["outcome"]["source"],
                    record["outcome"]["transaction"],
                    record["outcome"]["delivery"],
                )
                == ("EARLY_CLOSE", "ROLLBACK_ACK", "INCOMPLETE"),
                "PREFIX_TERMINAL",
            )
        else:
            check_attempt(record, config, artifact, output, program=program, case=case)
    return {
        "status": "PASS_CURRENT_RECORDS"
        if "inputs" in config
        else "PASS_COMPONENT_RECORDS",
        "attempts": len(report["attempts"]),
    }


def check_fixture_values(record, *, repeat=1, updated=False, partial=False):
    raw, _ = ordinary_expected("postgres", "G_emission_table_bag", "bag")
    literal = oracle_values(raw, record["public"]["columns"])
    if updated:
        for row in literal:
            if row[1] == {"kind": "int", "value": "0"}:
                row[1] = {"kind": "int", "value": "42"}
    expected = bag(literal * repeat)
    actual = bag(record["rows"])
    need(actual <= expected if partial else actual == expected, "FIXTURE_FULL_VALUES")


def check_controls(records, *, legacy=False):
    from _pietto_phase68_slice9_probe import CONTROL_CASES

    need(
        [r["control"] for r in records]
        == list(CONTROL_CASES[:19] if legacy else CONTROL_CASES),
        "CONTROL_DENOMINATOR",
    )
    summaries = []
    for r in records:
        kind = r["control"]
        if kind == "stable_update":
            old, fresh = r["original"], r["fresh"]
            for a in (old, fresh):
                check_native(a)
                need(
                    (
                        a["outcome"]["source"],
                        a["outcome"]["transaction"],
                        a["outcome"]["delivery"],
                    )
                    == ("EOF", "COMMIT_ACK", "COMPLETE"),
                    "SNAPSHOT_TERMINAL",
                )
            need(
                old["attempt"] != fresh["attempt"]
                and old["context"][6:8] != fresh["context"][6:8],
                "FRESH_ATTEMPT",
            )
            check_fixture_values(old)
            check_fixture_values(fresh, updated=True)
            old_ids = Counter(row[1]["value"] for row in old["rows"])
            new_ids = Counter(row[1]["value"] for row in fresh["rows"])
            need(
                old_ids == Counter(("9007199254740993", "9007199254740993", "0", "1"))
                and new_ids
                == Counter(("9007199254740993", "9007199254740993", "42", "1")),
                "STABLE_AND_FRESH_VALUES",
            )
            summaries.append(kind)
            continue
        check_fixture_values(r, partial=True)
        o = r["outcome"]
        events = r.get("interventions", [])
        need(r["control_joined"] and r.get("observer_joined", True), "CONTROL_THREADS")
        if kind in ("pre_cancel", "cancel_verify", "deadline_verify"):
            need(
                not r["statements"]
                and r["context"] is None
                and o["transaction"] == "NOT_STARTED",
                "BEFORE_NATIVE",
            )
        else:
            history = r["session_gone"]
            need(
                type(history) is list
                and history
                and history[-1] == 0
                and all(type(v) is int and v >= 0 for v in history),
                "CONTROL_SESSION",
            )
        if kind in ("serializable", "late_cancel", "tls_require"):
            check_native(r)
            need(
                r["failure"] is None
                and o["source"] == "EOF"
                and o["transaction"] == "COMMIT_ACK"
                and o["delivery"] == "COMPLETE"
                and len(r["rows"]) == 4,
                "LATE_SUCCESS",
            )
            if kind == "serializable":
                need(r["context"][8] == "serializable", "SERIALIZABLE")
            elif kind == "tls_require":
                need(
                    r["premise"]["access"]["sslmode"] == "require"
                    and len(r["tls_observation"]) == 1
                    and r["tls_observation"][0][0] is True
                    and r["tls_observation"][0][1] in ("TLSv1.2", "TLSv1.3"),
                    "ACTUAL_TLS",
                )
            else:
                need(
                    o["cancel_requested"]
                    and not o["cancel_sent"]
                    and events[-1]["result"]["late"],
                    "LATE_CANCEL",
                )
        elif kind == "late_read_close_error":
            data = [s for s in r["statements"] if s["purpose"] == "query"]
            need(
                r["failure"]["message"] == "injected late read failure"
                and len(data) == 1
                and data[0]["raw_rows"]
                and data[0]["terminal"] == "ERROR"
                and data[0]["reader_close"] == "FAILED"
                and not r["rows"]
                and o["transaction"] == "UNKNOWN"
                and any(e["phase"] == "reader_close" for e in o["cleanup_failures"]),
                "LATE_READ_PRIMARY_AND_CLEANUP",
            )
        elif kind in (
            "transaction_early_close",
            "transaction_role_replace",
            "transaction_cancel",
        ):
            need(
                o["transaction"] == "UNKNOWN"
                and not r["rows"]
                and o["primary"] is not None,
                "FOREIGN_TRANSACTION_NOT_ACKNOWLEDGED",
            )
            probes = [
                s
                for s in r["statements"]
                if s["sql"] == CONTEXT_SQL and s["finalizing"]
            ]
            need(
                len(probes) == 1
                and probes[0]["terminal"] == "NORMAL"
                and not exact(probes[0]["raw_rows"], encoded((tuple(r["context"]),))),
                "ACTUAL_FOREIGN_FINALIZATION_CONTEXT",
            )
            need(
                not any(
                    s["finalizing"] and s["sql"] in ("COMMIT", "ROLLBACK")
                    for s in r["statements"]
                ),
                "NO_FOREIGN_TRANSACTION_COMMAND",
            )
            if kind == "transaction_role_replace":
                need(
                    r["failure"]["message"] == "POSTGRES_ADBC_NATIVE_CONTEXT",
                    "ROLE_MASKED_TRANSACTION",
                )
            elif kind == "transaction_cancel":
                need(
                    o["cancel_requested"]
                    and r["failure"]["message"] == "EXECUTION_CANCELED",
                    "CANCEL_MASKED_TRANSACTION",
                )
            else:
                need(
                    r["failure"] is None and o["source"] == "EARLY_CLOSE",
                    "CLOSE_MASKED_TRANSACTION",
                )
        elif kind == "early_close":
            need(
                r["failure"] is None
                and o["source"] == "EARLY_CLOSE"
                and o["delivery"] == "INCOMPLETE"
                and o["transaction"] == "ROLLBACK_ACK"
                and len(r["rows"]) == 2,
                "EARLY_CLOSE",
            )
        elif kind in ("commit_loss", "statement_close_loss"):
            need(
                r["failure"]
                and o["source"] == "EOF"
                and len(r["rows"]) == 4
                and any("injected_" in e["kind"] for e in events),
                "INJECTED_FINALIZATION",
            )
            if kind == "commit_loss":
                need(o["transaction"] == "UNKNOWN", "COMMIT_UNKNOWN")
            else:
                need(
                    o["transaction"] == "COMMIT_ACK" and o["cleanup_failures"],
                    "CLEANUP_DISTINCT",
                )
        elif kind in ("blocked_cancel", "blocked_deadline"):
            wait = [e for e in events if e["kind"] == "actual_native_lock_wait"]
            need(
                len(wait) == 1
                and wait[0]["pid"] == r["context"][6]
                and wait[0]["observed"][0][:2] == ["active", "Lock"],
                "ACTUAL_LOCK_WAIT",
            )
            need(
                r["failure"]
                and "57014" in r["failure"]["message"]
                and o["cancel_requested"]
                and o["cancel_sent"]
                and o["cancel_observed"]
                and o["transaction"] == "UNKNOWN",
                "NATIVE_CANCEL_TERMINAL",
            )
            if kind == "blocked_deadline":
                need(r["deadline_expired"], "NATIVE_DEADLINE")
        else:
            need(
                r["failure"] is not None and o["delivery"] == "FAILED", "CONTROL_FAILED"
            )
            if kind == "transaction_replace":
                need(
                    r["failure"]["message"] == "POSTGRES_ADBC_TRANSACTION_CHANGED"
                    and o["transaction"] == "UNKNOWN"
                    and not r["rows"],
                    "TRANSACTION_REPLACE",
                )
            elif kind == "role_replace":
                need(
                    r["failure"]["message"] == "POSTGRES_ADBC_NATIVE_CONTEXT"
                    and not r["rows"],
                    "ROLE_REPLACE",
                )
            elif kind == "resource_rows":
                need(
                    r["failure"]["message"] == "EXECUTION_RESOURCE_LIMIT"
                    and not r["rows"],
                    "ROW_LIMIT",
                )
            elif kind == "resource_batch":
                need(
                    r["failure"]["message"] == "LIMIT" and not r["rows"], "BATCH_LIMIT"
                )
            elif kind == "slow_consumer":
                need(
                    r["deadline_expired"]
                    and len(r["rows"]) == 2
                    and events[0]["kind"] == "actual_consumer_delay",
                    "CONSUMER_DEADLINE",
                )
        summaries.append(kind)
    return summaries


def check_source_controls(records):
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
    need(
        [r["source_control"] for r in records] == expected, "SOURCE_CONTROL_DENOMINATOR"
    )
    positives = {
        "nested_invoker_definer_union_all_no_base_select": 8,
        "qualified_builtin_virtual_expression": 4,
        "qualified_registry_view_and_key": 4,
    }
    for r in records:
        name = r["source_control"]
        need(r["control_joined"] and r["session_gone"][-1] == 0, "SOURCE_SESSION")
        if name in positives:
            check_native(r)
            check_fixture_values(
                r,
                repeat=2
                if name == "nested_invoker_definer_union_all_no_base_select"
                else 1,
            )
            need(
                r["failure"] is None
                and r["outcome"]["transaction"] == "COMMIT_ACK"
                and len(r["rows"]) == positives[name],
                "SOURCE_POSITIVE",
            )
        elif name == "nested_definer_invoker_requires_query_base_privilege":
            need(
                r["failure"] is not None
                and "42501" in r["failure"]["message"]
                and not r["rows"],
                "NATIVE_INVOKER_ACCESS",
            )
        else:
            need(
                r["failure"] is not None
                and r["failure"]["message"].startswith("POSTGRES_SOURCE_")
                and not r["rows"],
                "SOURCE_NEGATIVE",
            )
            permitted = set(SQL.values()) | {
                CONTEXT_SQL,
                "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY",
                "ROLLBACK",
            }
            need(
                all(s["sql"] in permitted for s in r["statements"]),
                "REFUSED_BEFORE_SOURCE_EVALUATION",
            )
    return {"source_laws": len(records)}


def check_fresh_pair(prefix, fresh):
    need(
        prefix["worker_pid"] != fresh["worker_pid"]
        and prefix["origin"] == fresh["origin"],
        "FRESH_PROCESS",
    )
    need(len(prefix["attempts"]) == len(fresh["attempts"]) == 1, "FRESH_DENOMINATOR")
    a, b = prefix["attempts"][0], fresh["attempts"][0]
    need(
        a["attempt"] != b["attempt"] and a["context"][6:8] != b["context"][6:8],
        "FRESH_ATTEMPT_CONTEXT",
    )
    need(
        exact(a["admission"]["sources"], b["admission"]["sources"]),
        "SAME_VERSION_SOURCE_VECTOR",
    )
    need(
        a["rows"] and exact(a["rows"], b["rows"][: len(a["rows"])]),
        "FRESH_PREFIX_VALUES",
    )
    first_raw = [s["raw_rows"] for s in a["statements"] if s["purpose"] == "page"]
    fresh_raw = [s["raw_rows"] for s in b["statements"] if s["purpose"] == "page"]
    need(exact(first_raw, fresh_raw[: len(first_raw)]), "FRESH_PREFIX_COORDINATES")
    return {
        "prefix_rows": len(a["rows"]),
        "fresh_rows": len(b["rows"]),
        "claim": "SAME_VERSION_REEVALUATION_ONLY",
    }
