"""Explicit S09 native acquisition; no database work during ordinary imports."""

from dataclasses import asdict
import importlib
import hashlib
import io
import subprocess
import tarfile
import json
import linecache
from pathlib import Path
import sys
import time
from typing import Any

from _pietto_phase68_slice7_cases import manifest, case_preparation
from _pietto_phase68_slice7_probe import setup, fill, refinement, encoded, origins
from _pietto_phase68_slice7_probe import native_record
from _pietto_phase68_slice6_probe import manager, session_gone, observation_data
from _pietto_phase68_slice8_probe import worker_process, event, write
from _pietto_target_conformance_resources import Resources, clean_environment

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "pietto-phase68-slice09-"


def capture_inputs(tree, directory):
    """Preserve producing bytes before any native or installed worker starts."""
    data = subprocess.check_output(
        [
            "git",
            "archive",
            tree,
            "src",
            "tests",
            "scripts",
            "ci/phase68-executor-premise-requirements.txt",
            "pyproject.toml",
            "uv.lock",
        ],
        cwd=ROOT,
    )
    (directory / (PREFIX + "inputs.tar")).write_bytes(data)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("S09_INPUT_MEMBER")
            raw = stream.read()
            if (ROOT / member.name).read_bytes() != raw:
                raise ValueError("S09_PRODUCING_TREE_CHANGED:" + member.name)
            files[member.name] = hashlib.sha256(raw).hexdigest()
    result = {
        "tree": tree,
        "files": files,
        "archive_sha256": hashlib.sha256(data).hexdigest(),
    }
    write(directory / (PREFIX + "inputs.json"), result)
    return result


def check_readiness(readiness, tree, inputs, wheel):
    if readiness is None:
        raise ValueError("S09_READINESS_REQUIRED")
    ready = json.loads(Path(readiness).read_text())
    if (
        ready["status"] != "GREEN_FOR_CURRENT_INPUTS"
        or ready["tree"] != tree
        or ready["inputs"] != inputs["files"]
        or ready["wheel_sha256"] != hashlib.sha256(Path(wheel).read_bytes()).hexdigest()
    ):
        raise ValueError("S09_READINESS_CHANGED")
    return ready


def enable_fixture_tls(resource):
    """Ephemeral self-signed fixture; this tests require, not peer identity."""
    key, cert = resource.private / "s09-key.pem", resource.private / "s09-cert.pem"
    try:
        subprocess.run(
            [
                "openssl",
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-days",
                "1",
                "-subj",
                "/CN=pietto-s09-fixture",
            ],
            check=True,
            capture_output=True,
            timeout=20,
        )
        for path in (key, cert):
            resource.docker(
                "cp", str(path), resource.container_id + ":/tmp/" + path.name
            )
        resource.docker(
            "exec",
            "--user",
            "root",
            resource.container_id,
            "chown",
            "postgres:postgres",
            "/tmp/s09-key.pem",
            "/tmp/s09-cert.pem",
        )
        resource.docker(
            "exec",
            "--user",
            "root",
            resource.container_id,
            "chmod",
            "600",
            "/tmp/s09-key.pem",
        )
        manager(resource, "ALTER SYSTEM SET ssl_cert_file='/tmp/s09-cert.pem'")
        manager(resource, "ALTER SYSTEM SET ssl_key_file='/tmp/s09-key.pem'")
        manager(resource, "ALTER SYSTEM SET ssl=on")
        manager(resource, "SELECT pg_catalog.pg_reload_conf()")
        # Reload delivery is asynchronous; observe the actual configuration.
        end = time.monotonic() + 5
        while time.monotonic() < end:
            if manager(resource, "SHOW ssl") == [("on",)]:
                return
            time.sleep(0.05)
        raise ValueError("S09_TLS_RELOAD_UNOBSERVED")
    finally:
        key.unlink(missing_ok=True)
        cert.unlink(missing_ok=True)


def native_data(reply):
    return {
        "sql": reply.sql.decode(),
        "arguments": reply.arguments,
        "rows": reply.rows,
        "terminal": reply.terminal,
    }


class Calls:
    """Passive Python/C-call boundary records and actual returned Arrow values."""

    def __init__(self, owner):
        from pietto._project import project_execution_postgres_adbc_native as native

        self.owner = owner
        self.previous = sys.getprofile()
        self.statements = []
        self.pages = []
        self.copy_checkpoints = []
        self.native_path = native.__file__
        self.owner_path = sys.modules[type(owner).__module__].__file__
        self.enumeration_path = sys.modules[
            "pietto._project.project_refinement_enumeration"
        ].__file__
        self.trace_parent = None
        self.index = {}

    def observe(self, frame, event_name, result):
        if self.previous is not None:
            self.previous(frame, event_name, result)
        filename = frame.f_code.co_filename
        method = frame.f_code.co_name
        if (
            filename != self.native_path
            and not (filename == self.owner_path and method == "_refresh")
            and not (filename == self.enumeration_path and method == "commit_page")
        ):
            return
        local = frame.f_locals
        obj = local.get("self")
        if (
            frame.f_code.co_filename == self.native_path
            and getattr(obj, "owner", None) is self.owner
        ):
            name = frame.f_code.co_name
            if name == "_execute" and event_name == "call":
                self.trace_parent = sys.gettrace()
                sys.settrace(self.trace)
                frame.f_trace = self.trace
                record = {
                    "sql": obj.sql.decode(),
                    "arguments": encoded((obj.arguments,))[0],
                    "types": obj.tags,
                    "purpose": obj.purpose,
                    "copy": obj.copy,
                    "finalizing": self.owner._finalizing,
                    "api": [],
                    "rows": [],
                    "raw_rows": [],
                    "raw_pulls": 0,
                    "schema": [],
                    "pulls": [],
                    "terminal": None,
                    "reader_close": "NOT_STARTED",
                    "statement_close": "NOT_STARTED",
                }
                self.index[id(obj)] = record
                self.statements.append(record)
            if name == "_execute" and event_name == "return":
                sys.settrace(self.trace_parent)
            record = self.index.get(id(obj))
            if record is None:
                return
            if event_name == "c_call" and name == "_execute":
                method = getattr(result, "__name__", "")
                if getattr(result, "__self__", None) is obj.native and method in (
                    "set_sql_query",
                    "prepare",
                    "bind",
                    "execute_query",
                ):
                    fact: dict[str, Any] = {"method": method}
                    if method == "set_sql_query":
                        fact["sql"] = obj.sql.decode()
                    if method == "bind":
                        bound = local["bound"]
                        fact["schema"] = [str(f.type) for f in bound.schema]
                        fact["rows"] = encoded(
                            tuple(
                                tuple(
                                    bound.column(i)[j].as_py()
                                    for i in range(bound.num_columns)
                                )
                                for j in range(bound.num_rows)
                            )
                        )
                    if (
                        record["api"]
                        and record["api"][-1].get("method") == method
                        and record["api"][-1].get("capture") == "execution_line"
                    ):
                        record["api"][-1]["c_call_observed"] = True
                    else:
                        record["api"].append(fact)
            if name == "fetch" and event_name == "return" and result is not None:
                record["rows"].extend(encoded(result))
            if event_name == "return" and name in ("execute", "_execute", "close"):
                record.update(
                    schema=obj.schema,
                    pulls=obj.pulls,
                    terminal=obj.terminal,
                    reader_close=obj.reader_close,
                    statement_close=obj.statement_close,
                )
        if (
            frame.f_code.co_name == "_refresh"
            and event_name == "return"
            and obj is self.owner
            and local.get("pending") is not None
        ):
            self.copy_checkpoints.append(
                {
                    "before": local.get("before"),
                    "after": local.get("after"),
                    "context": local.get("current"),
                }
            )
        if (
            frame.f_code.co_name == "commit_page"
            and event_name == "return"
            and obj is self.owner.enumeration
        ):
            from _pietto_phase68_slice6_probe import page_data

            checked = local["checked"]
            self.pages.append(
                {
                    "page": page_data(checked.request, obj.query),
                    "progress": obj.progress,
                }
            )

    def trace(self, frame, event_name, value):
        if (
            frame.f_code.co_filename != self.native_path
            or frame.f_code.co_name != "_execute"
        ):
            return None
        obj = frame.f_locals.get("self")
        if getattr(obj, "owner", None) is not self.owner:
            return None
        record = self.index.get(id(obj))
        if event_name == "line" and record is not None:
            if len(obj.pulls) > record["raw_pulls"]:
                batch = frame.f_locals["batch"]
                if (
                    batch.num_rows > 4096
                    or batch.get_total_buffer_size() > 64 * 1024 * 1024
                ):
                    record["raw_capture_incomplete"] = True
                else:
                    record["raw_rows"].extend(
                        encoded(
                            tuple(
                                tuple(
                                    batch.column(i)[j].as_py()
                                    for i in range(batch.num_columns)
                                )
                                for j in range(batch.num_rows)
                            )
                        )
                    )
                record["raw_pulls"] = len(obj.pulls)
            line = linecache.getline(self.native_path, frame.f_lineno).strip()
            methods = {
                "self.native.set_sql_query(self.sql.decode())": "set_sql_query",
                "self.native.prepare()": "prepare",
                "self.native.bind(bound)": "bind",
                "handle, _rowcount = self.native.execute_query()": "execute_query",
            }
            if line in methods:
                fact: dict[str, Any] = {
                    "method": methods[line],
                    "capture": "execution_line",
                }
                if fact["method"] == "set_sql_query":
                    fact["sql"] = obj.sql.decode()
                if fact["method"] == "bind":
                    bound = frame.f_locals["bound"]
                    fact["schema"] = [str(f.type) for f in bound.schema]
                    fact["rows"] = encoded(
                        tuple(
                            tuple(
                                bound.column(i)[j].as_py()
                                for i in range(bound.num_columns)
                            )
                            for j in range(bound.num_rows)
                        )
                    )
                record["api"].append(fact)
        return self.trace


def attempt(
    resource,
    artifact,
    *,
    preparation=None,
    query=None,
    binding=None,
    allow=True,
    size=2,
    isolation="stable",
    user="pietto_query",
    seconds=120,
    hook=None,
    prefix=False,
    observe_session=True,
    max_rows=1048576,
    batch_bytes=1048576,
    sslmode="disable",
):
    from pietto._project.project_execution import (
        PostgresAccess,
        PostgresADBCDeploymentPremise,
        ExecutionLimits,
        prepare_execution,
    )
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
    from pietto._project.project_guard_runtime import prepare_guarded_execution
    from pietto._project.project_refinement_enumeration import prepare_refined_execution
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    a = PostgresAccess(
        "127.0.0.1", resource.port, "phase66", user, resource._passwords[1], sslmode
    )
    premise = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    options = {
        "route": "postgres_adbc",
        "postgres_adbc_deployment": premise,
        "limits": ExecutionLimits(
            batch_rows=size, seconds=seconds, max_rows=max_rows, batch_bytes=batch_bytes
        ),
        "isolation": isolation,
    }
    request = (
        prepare_guarded_execution(
            preparation,
            a,
            refinement=query,
            binding=binding,
            allow_guard_sql=allow,
            **options,
        )
        if preparation is not None
        else prepare_refined_execution(query, a, **options)
        if query is not None
        else prepare_execution(artifact, a, binding=binding, **options)
    )
    owner = PostgresADBCExecution(request)
    calls = Calls(owner)
    started = time.monotonic()
    result: dict[str, Any] = {
        "attempt": owner.attempt,
        "rows": [],
        "schemas": [],
        "failure": None,
        "interventions": [],
        "public": None,
        "request_seconds": seconds,
    }
    if preparation is None:
        result["public"] = json.loads(
            serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), artifact))
        )
    retained_arrays = []
    previous = sys.getprofile()
    previous_trace = sys.gettrace()
    sys.setprofile(calls.observe)
    try:
        if hook is not None:
            hook("before_open", owner, result)
        with owner:
            if hook is not None:
                hook("opened", owner, result)
            for batch in owner:
                with batch:
                    array = importlib.import_module("pyarrow").record_batch(batch)
                    result["schemas"].append(
                        [[f.name, str(f.type), f.nullable] for f in array.schema]
                    )
                    rows = tuple(
                        tuple(
                            array.column(i)[j].as_py() for i in range(array.num_columns)
                        )
                        for j in range(array.num_rows)
                    )
                    result["rows"].extend(encoded(rows))
                    retained_arrays.append(array)
                if hook is not None:
                    hook("batch", owner, result)
                if prefix:
                    break
            if hook is not None:
                hook("after_iteration", owner, result)
    except Exception as error:
        result["failure"] = {
            "kind": type(error).__name__,
            "message": resource.without_secrets(str(error)),
        }
    finally:
        sys.setprofile(previous)
        sys.settrace(previous_trace)
        owner.close()
        result["post_close_rows"] = encoded(
            tuple(
                tuple(array.column(i)[j].as_py() for i in range(array.num_columns))
                for array in retained_arrays
                for j in range(array.num_rows)
            )
        )
        result.update(
            outcome=asdict(owner.outcome),
            context=owner.context,
            native_context=None
            if owner._context_native is None
            else native_data(owner._context_native),
            statements=calls.statements,
            pages=calls.pages,
            control_events=owner.control_events,
            control_joined=owner.control_joined,
            copy_checkpoints=calls.copy_checkpoints,
            guard_states=None if owner.guards is None else owner.guards.states,
            elapsed_seconds=time.monotonic() - started,
        )
        result["bound_schema"] = (
            None
            if owner._payloads is None
            else [
                [f.name, str(f.type), f.nullable]
                for f in owner._payloads.binding.schema
            ]
        )
        result["premise"] = {
            "route": premise.route,
            "basis": premise.basis,
            "schemas": premise.schemas,
            "roots": [[v.namespace, v.name] for v in premise.sources],
            "access": {
                "host": a.host,
                "port": a.port,
                "database": a.database,
                "user": a.user,
                "sslmode": a.sslmode,
            },
        }
        if owner.guards is not None and owner.guards.native is not None:
            result["guard_native"] = native_record(owner.guards.native)
        if owner.source_admissions is not None:
            result["admission"] = observation_data(owner.source_admissions)
        if owner._qualification is not None:
            q = owner._qualification
            result["qualification"] = {
                "roots": q.roots,
                "paths": q.paths,
                "context": q.context,
                "replies": [
                    {
                        "kind": v.kind,
                        "arguments": v.arguments,
                        "rows": v.rows,
                        "native": native_data(v.native),
                    }
                    for v in q.replies
                ],
                "basis": q.definition_stability,
                "compliance": q.premise_compliance,
                "native_lifetime": q.native_lifetime_protection,
            }
        result["session_gone"] = (
            None
            if owner.session_id is None or not observe_session
            else session_gone(resource, owner.session_id)
        )
    return result


def worker(config_path):
    """Same installed/source observer; manager stays explicitly distinct."""
    from _pietto_phase68_slice6_cases import original, source_requirements
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_guard_preparation import (
        prepare_guarded_output,
        prepare_guarded_template,
    )
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_refinement import prepare_refinement, TieRefinement
    from _pietto_phase68_slice6_probe import s01
    import os

    config = json.loads(config_path.read_text())
    directory = Path(config["directory"])
    holder = directory / (PREFIX + "worker-manager")
    holder.mkdir(mode=0o700)
    resource = Resources(
        "postgres",
        json.loads((ROOT / "tests/phase66_target_pins.json").read_text())["targets"][
            "postgres"
        ],
        holder,
    )
    resource.port, resource._passwords = config["port"], tuple(config["passwords"])
    resource.startup_started = time.monotonic()
    report: dict[str, Any] = {
        "tree": config["tree"],
        "origin": config["origin"],
        "group": config["group"],
        "worker_pid": os.getpid(),
        "attempts": [],
        "runtime": s01.runtime_identity(),
    }
    importlib.import_module("pietto._project.project_execution_postgres_adbc")
    importlib.import_module(
        "pietto._project.project_postgres_source_assurance_verification"
    )
    report["origins_before"] = origins()
    path = directory / (PREFIX + "worker.json")
    write(path, report)
    template = first_binding = None
    try:
        resource.manager = resource.connect(query=False)
        report["manager_session"] = resource.manager.info.backend_pid
        if config["group"] == "controls":
            if not config.get("source_only", False):
                control_records(resource, directory, report, path)
            if not config.get("lifecycle_only", False):
                source_records(resource, directory, report, path)
            report["acquisition"] = "FINISHED_REQUIRES_INDEPENDENT_CHECK"
            return
        for index, selected in enumerate(config["cases"]):
            case, variant = selected["family"], selected.get("variant")
            work = directory / (PREFIX + str(index))
            binding = query = preparation = None
            fixture: Any = None
            options = {}
            if config["group"] == "guarded":
                fixture = next(c for c in manifest() if c["name"] == case)
                options = fixture["options"]
                fill(
                    resource,
                    fixture["lhs"],
                    fixture["rhs"],
                    wide_text=options.get("wide_text", False),
                )
                if "binding_values" in options:
                    if template is None:
                        template = prepare_guarded_template(
                            case_preparation(work, "postgres", fixture)
                        )
                    if case == "binding_A_again":
                        binding = first_binding
                    else:
                        supplied = list(
                            zip(template.slots, options["binding_values"], strict=True)
                        )
                        binding = bind_values(template, supplied)
                        supplied.clear()
                        if case == "binding_A":
                            first_binding = binding
                    if binding is None:
                        raise ValueError("S09_ORIGINAL_BINDING_REQUIRED")
                    preparation = binding.guarded
                else:
                    preparation = case_preparation(work, "postgres", fixture)
                artifact = preparation.artifact
                if options.get("refined"):
                    query = refinement(
                        resource,
                        preparation,
                        prepare_guarded_output(preparation, binding=binding),
                        role=options.get("role", "pietto_query"),
                    )
            else:
                artifact = original(
                    work, "postgres", "R2_seven" if case == "seven" else case, variant
                )
                if artifact is None:
                    raise ValueError("S09_UNEXPECTED_COMPILER_BLOCKER")
                if config["group"] == "refined":
                    query = prepare_refinement(
                        artifact,
                        source_requirements(
                            artifact, config["providers"], "pietto_query"
                        ),
                        policy=TieRefinement(),
                        output=prepare_output(artifact),
                    )
            report["origins_before"].update(origins())
            write(path, report)
            result = attempt(
                resource,
                artifact,
                preparation=preparation,
                query=query,
                binding=binding,
                allow=options.get("allow", True),
                size=options.get("page_size", 2),
                isolation=options.get("isolation", "stable"),
                user=options.get("role", "pietto_query"),
                prefix=config.get("fresh_stage") == "prefix",
            )
            result.update(case=case, variant=variant)
            report["attempts"].append(result)
            write(path, report)
            print(
                config["origin"],
                config["group"],
                index,
                case,
                variant,
                result["failure"],
                flush=True,
            )
            if config.get("fail_fast") and result["failure"] is not None:
                message = result["failure"]["message"]
                expected = preparation is not None and (
                    (
                        "VIOLATED" in fixture["states"]
                        and message == "SINGLE_MATCH_VIOLATED"
                    )
                    or (
                        not options.get("allow", True)
                        and message == "GUARD_SQL_FORBIDDEN_UNFULFILLED"
                    )
                )
                if not expected:
                    raise ValueError("S09_PREFLIGHT_UNEXPECTED_FAILURE")
        report["acquisition"] = "FINISHED_REQUIRES_INDEPENDENT_CHECK"
    finally:
        report["origins"] = origins()
        report["runtime"] = s01.runtime_identity()
        if resource.manager is not None:
            resource.manager.close()
            resource.manager = None
        report["manager_local_closed"] = True
        write(path, report)


def reset_fixture_database(resource):
    manager(resource, "DROP SCHEMA public CASCADE")
    manager(resource, "CREATE SCHEMA public")
    manager(resource, "SET search_path=public")
    roles = manager(
        resource,
        "SELECT rolname::text FROM pg_catalog.pg_roles WHERE rolname IN ('pietto_subset','pietto_query') ORDER BY rolname",
    )
    for (role,) in roles:
        if role not in ("pietto_subset", "pietto_query"):
            raise ValueError("S09_FIXTURE_ROLE")
        manager(
            resource, 'REVOKE ALL PRIVILEGES ON DATABASE phase66 FROM "' + role + '"'
        )
        manager(resource, 'DROP ROLE "' + role + '"')


def campaign(
    directory,
    ledger,
    tree,
    *,
    mode,
    groups,
    origins_selected=("source",),
    readiness=None,
    selected_families=None,
    source_only=False,
    lifecycle_only=False,
    wheel=None,
    fresh_refinement=False,
):
    import _pietto_phase68_slice6_probe as six
    import _pietto_phase68_slice5_probe as five
    import _pietto_target_conformance_cases as fixtures

    directory.mkdir(mode=0o700)
    pins = json.loads((ROOT / "tests/phase66_target_pins.json").read_text())
    resource = Resources("postgres", pins["targets"]["postgres"], directory)
    event(
        ledger,
        {"kind": mode + "_start", "tree": tree, "directory": str(directory)},
        **{
            (
                "complete_s09_live_campaign_starts"
                if mode == "campaign"
                else "targeted_live_family_starts"
            ): 1,
            "source_db_lifecycle_starts": 1,
        },
    )
    required = json.loads(
        (ledger.parent / (PREFIX + "acceptance-manifest.json")).read_text()
    )
    report = {"tree": tree, "mode": mode, "workers": []}
    started = time.monotonic()
    profile = ledger.parent / (PREFIX + "native-env")
    try:
        inputs = capture_inputs(tree, directory)
        if wheel is None:
            raise ValueError("S09_WHEEL_REQUIRED")
        if mode == "campaign":
            check_readiness(readiness, tree, inputs, wheel)
            if (
                selected_families
                or tuple(groups) != ("controls", "ordinary", "refined", "guarded")
                or tuple(origins_selected) != ("source", "installed")
            ):
                raise ValueError("S09_FULL_MANIFEST_REQUIRED")
        resource.acquire()
        enable_fixture_tls(resource)
        for group_index, group in enumerate(groups):
            if group_index:
                reset_fixture_database(resource)
            if group == "guarded":
                setup(resource)
                providers = []
            elif group == "refined":
                providers = six.setup(resource)
            else:
                for sql, args in (
                    fixtures.emission_setup("postgres")
                    + fixtures.native_setup("postgres")
                    + fixtures.row_domain_setup("postgres")
                ):
                    manager(resource, sql, args)
                five.setup_seven(resource)
                for sql, _secret in resource.role_statements():
                    manager(resource, sql)
                if group == "controls":
                    manager(
                        resource,
                        "CREATE ROLE pietto_subset NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",
                    )
                    manager(resource, "GRANT pietto_subset TO pietto_query")
                providers = []
            cases = (
                []
                if group == "controls"
                else (
                    [{"family": n} for n in required[group]]
                    if group == "guarded"
                    else [{"family": a, "variant": b} for a, b in required[group]]
                )
            )
            if mode != "campaign" and group != "controls":
                names = {
                    "ordinary": {
                        "G_emission_table_bag",
                        "I_emission_table_empty",
                        "G_scan_row_domains",
                        "seven",
                    },
                    "refined": {
                        "G_emission_table_bag",
                        "G_scan_row_domains",
                        "R2_mixed",
                    },
                    "guarded": {
                        "bag_one",
                        "bag_two_equal_null",
                        "right_limit_0",
                        "path_whole_positive",
                        "refined_pages",
                        "refined_violation_outside_page",
                        "binding_A",
                        "binding_B",
                        "binding_A_again",
                    },
                }[group]
                cases = [
                    c
                    for c in cases
                    if c["family"] in names
                    and (c["family"] != "seven" or c["variant"] == "39_values")
                ]
            if selected_families and group in selected_families:
                cases = [c for c in cases if c["family"] in selected_families[group]]
            specs: list[tuple[str, str | None]] = [
                (origin, None) for origin in origins_selected
            ]
            if group == "refined" and fresh_refinement:
                specs.extend(
                    (origin, stage)
                    for origin in origins_selected
                    for stage in ("prefix", "fresh")
                )
            for origin, fresh_stage in specs:
                worker_dir = directory / (
                    PREFIX
                    + group
                    + "-"
                    + origin
                    + ("-" + fresh_stage if fresh_stage else "")
                )
                worker_dir.mkdir(mode=0o700)
                config = {
                    "tree": tree,
                    "origin": origin,
                    "group": group,
                    "directory": str(worker_dir),
                    "port": resource.port,
                    "passwords": resource._passwords,
                    "providers": providers,
                    "cases": cases,
                    "fail_fast": mode != "campaign",
                    "source_only": source_only,
                    "lifecycle_only": lifecycle_only,
                    "fresh_stage": fresh_stage,
                    "finalization_context_required": True,
                    "inputs": str(directory / (PREFIX + "inputs.json")),
                    "wheel": str(wheel),
                    "wheel_sha256": hashlib.sha256(
                        Path(wheel).read_bytes()
                    ).hexdigest(),
                    "profile": str(
                        profile
                        if origin == "source"
                        else ledger.parent / (PREFIX + "installed-env")
                    ),
                }
                if fresh_stage:
                    config["cases"] = [
                        {"family": "G_emission_table_bag", "variant": "bag"}
                    ]
                private = worker_dir / (PREFIX + "private-input.json")
                private.write_text(json.dumps(config))
                private.chmod(0o600)
                public = {k: v for k, v in config.items() if k != "passwords"}
                write(worker_dir / (PREFIX + "manifest.json"), public)
                resource.manager.close()
                resource.manager = None
                interpreter = (
                    profile
                    if origin == "source"
                    else ledger.parent / (PREFIX + "installed-env")
                ) / "bin/python"
                try:
                    with (worker_dir / (PREFIX + "worker.log")).open("wb") as log:
                        code = worker_process(
                            [
                                str(interpreter),
                                "-I",
                                "-B",
                                str(ROOT / "scripts/phase68_slice9_probe.py"),
                                "--mode",
                                "worker",
                                "--origin",
                                origin,
                                "--input",
                                str(private),
                            ],
                            clean_environment(),
                            ledger,
                            log,
                            origin=origin,
                            group=group,
                            directory=worker_dir,
                            seconds=7200,
                        )
                    report["workers"].append(
                        {
                            "directory": str(worker_dir),
                            "origin": origin,
                            "group": group,
                            "fresh_stage": fresh_stage,
                            "exit_code": code,
                        }
                    )
                    write(directory / (PREFIX + "campaign.json"), report)
                    if code:
                        raise ValueError("S09_WORKER_FAILED")
                finally:
                    private.unlink()
                    resource.startup_started = time.monotonic()
                    resource.connect_attempts = 0
                    resource.manager = resource.connect(query=False)
            # Compatible fixture reset is exercised between groups in this same DB.
        report["status"] = "ACQUIRED_REQUIRES_INDEPENDENT_CHECK"
    finally:
        report["cleanup"] = resource.cleanup()
        report["wall_seconds"] = time.monotonic() - started
        write(directory / (PREFIX + "campaign.json"), report)
        event(
            ledger,
            {
                "kind": mode + "_terminal",
                "wall_seconds": report["wall_seconds"],
                "cleanup": report["cleanup"],
                "report": str(directory / (PREFIX + "campaign.json")),
            },
        )


def controlled(resource, artifact, kind, *, seconds=60):
    import threading
    from pietto._project import project_execution_postgres_adbc as product
    from pietto._project import project_execution_postgres_adbc_native as native
    from _pietto_phase68_slice6_probe import quoted

    saved_verify = product.verify_execution_request
    saved_control = product.read_control
    saved_close = native.NativeStatement.close
    events, threads, observed, errors = [], [], [], []
    observer = None
    current = [None]
    sql = artifact.rendered.sql.decode()
    lock = kind in ("blocked_cancel", "blocked_deadline")
    if lock:
        source = artifact.request.sources[0]
        manager(resource, "BEGIN")
        manager(
            resource,
            "LOCK TABLE "
            + quoted(source.namespace, "postgres")
            + "."
            + quoted(source.name, "postgres")
            + " IN ACCESS EXCLUSIVE MODE",
        )
        resource.startup_started = time.monotonic()
        resource.connect_attempts = 0
        observer = resource.connect(query=False)

    def watch(owner):
        if observer is None:
            raise ValueError("S09_OBSERVER_REQUIRED")
        try:
            end = time.monotonic() + 20
            while time.monotonic() < end:
                with observer.cursor() as cursor:
                    cursor.execute("SELECT pg_catalog.pg_stat_clear_snapshot()")
                    cursor.execute(
                        "SELECT state,wait_event_type,query FROM pg_catalog.pg_stat_activity WHERE pid=$1",
                        (owner.session_id,),
                    )
                    rows = cursor.fetchall()
                if rows and rows[0][0:2] == ("active", "Lock") and sql in rows[0][2]:
                    event = {
                        "kind": "actual_native_lock_wait",
                        "pid": owner.session_id,
                        "observed": rows,
                        "since_open_seconds": time.monotonic() - owner._started,
                    }
                    events.append(event)
                    observed.append(event)
                    if kind == "blocked_cancel":
                        events.append(
                            {"kind": "cancel_result", "result": owner.cancel()}
                        )
                    return
                time.sleep(0.02)
            raise ValueError("S09_BLOCK_WAIT_NOT_OBSERVED")
        except BaseException as error:
            errors.append({"kind": type(error).__name__, "message": str(error)})
            owner.cancel()

    def verify(request):
        result = saved_verify(request)
        owner = current[0]
        if (
            owner is not None
            and kind in ("cancel_verify", "deadline_verify")
            and not events
        ):
            if kind == "cancel_verify":
                owner.cancel()
            else:
                owner._started = time.monotonic() - owner.request.limits.seconds - 1
            events.append(
                {"kind": "injected_" + kind, "after_expensive_verification": True}
            )
        return result

    def control(owner, command, *args, **kwargs):
        result = saved_control(owner, command, *args, **kwargs)
        if kind == "commit_loss" and command == "COMMIT":
            events.append({"kind": "injected_commit_response_loss_after_native_return"})
            raise OSError("injected commit response loss")
        return result

    def close(self):
        statement = self
        result = saved_close(statement)
        if (
            kind == "statement_close_loss"
            and statement.purpose == "query"
            and not events
        ):
            events.append(
                {"kind": "injected_statement_close_return_loss_after_native_close"}
            )
            raise OSError("injected statement close return loss")
        return result

    def hook(stage, owner, record):
        current[0] = owner
        if stage == "before_open" and kind == "pre_cancel":
            events.append({"kind": "pre_cancel", "result": owner.cancel()})
        elif stage == "opened":
            if lock:
                thread = threading.Thread(
                    target=watch, args=(owner,), name="pietto-s09-observer"
                )
                threads.append(thread)
                thread.start()
            elif kind == "cancel_after_admission":
                events.append(
                    {"kind": "cancel_after_admission", "result": owner.cancel()}
                )
            elif kind in (
                "transaction_replace",
                "transaction_early_close",
                "transaction_role_replace",
                "transaction_cancel",
            ):
                native.read_control(owner, "COMMIT", maximum=0)
                native.read_control(
                    owner, "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY", maximum=0
                )
                events.append({"kind": "injected_actual_commit_begin"})
                if kind == "transaction_role_replace":
                    native.read_control(owner, "SET ROLE pietto_subset", maximum=0)
                    events.append({"kind": "injected_actual_set_role"})
                elif kind == "transaction_early_close":
                    owner.close()
                    events.append({"kind": "early_close_after_transaction_replace"})
                elif kind == "transaction_cancel":
                    events.append(
                        {
                            "kind": "cancel_after_transaction_replace",
                            "result": owner.cancel(),
                        }
                    )
            elif kind == "role_replace":
                native.read_control(owner, "SET ROLE pietto_subset", maximum=0)
                events.append({"kind": "injected_actual_set_role"})
            elif kind == "late_read_close_error":
                pa = owner._arrow

                class Reader:
                    def __init__(self, reader):
                        self.reader = reader
                        self.schema = reader.schema
                        self.pulled = False

                    def read_next_batch(self):
                        if self.pulled:
                            events.append(
                                {"kind": "injected_read_error_after_actual_batch"}
                            )
                            raise OSError("injected late read failure")
                        result = self.reader.read_next_batch()
                        self.pulled = True
                        return result

                    def close(self):
                        self.reader.close()
                        events.append({"kind": "injected_reader_close_return_loss"})
                        raise RuntimeError("injected reader close return loss")

                class ReaderFactory:
                    @staticmethod
                    def _import_from_c(address):
                        reader = pa.RecordBatchReader._import_from_c(address)
                        return (
                            Reader(reader)
                            if owner._active.purpose == "query"
                            else reader
                        )

                class ArrowProxy:
                    RecordBatchReader = ReaderFactory

                    def __getattr__(self, name):
                        return getattr(pa, name)

                owner._arrow = ArrowProxy()
        elif stage == "batch":
            if kind == "cancel_after_batch" and not events:
                events.append({"kind": "cancel_after_batch", "result": owner.cancel()})
            elif kind == "consumer_error":
                events.append({"kind": "injected_consumer_error"})
                raise ValueError("injected consumer failure")
            elif kind == "slow_consumer" and not events:
                delay = (
                    max(
                        0,
                        owner.request.limits.seconds
                        - (time.monotonic() - owner._started),
                    )
                    + 0.05
                )
                t = time.monotonic()
                time.sleep(delay)
                events.append(
                    {"kind": "actual_consumer_delay", "seconds": time.monotonic() - t}
                )
        elif stage == "after_iteration" and kind == "late_cancel":
            events.append({"kind": "late_cancel", "result": owner.cancel()})

    product.verify_execution_request = verify
    product.read_control = control
    native.NativeStatement.close = close
    try:
        result = attempt(
            resource,
            artifact,
            seconds=seconds,
            hook=hook,
            prefix=kind == "early_close",
            observe_session=not lock,
            max_rows=1 if kind == "resource_rows" else 1048576,
            batch_bytes=8 if kind == "resource_batch" else 1048576,
        )
        result["deadline_expired"] = (
            current[0].deadline_expired if current[0] is not None else False
        )
    finally:
        product.verify_execution_request = saved_verify
        product.read_control = saved_control
        native.NativeStatement.close = saved_close
        for thread in threads:
            thread.join(timeout=25)
        if lock:
            manager(resource, "ROLLBACK")
        if observer is not None:
            observer.close()
    if lock and current[0] is not None and current[0].session_id is not None:
        result["session_gone"] = session_gone(resource, current[0].session_id)
    result.update(
        control=kind,
        interventions=events,
        observer_errors=errors,
        observer_joined=all(not t.is_alive() for t in threads),
    )
    if lock and (not observed or errors):
        raise ValueError("S09_UNCONFIRMED_BLOCKING_CONTROL")
    return result


CONTROL_CASES = (
    "stable_update",
    "serializable",
    "pre_cancel",
    "cancel_after_admission",
    "cancel_verify",
    "deadline_verify",
    "early_close",
    "late_cancel",
    "cancel_after_batch",
    "consumer_error",
    "statement_close_loss",
    "commit_loss",
    "transaction_replace",
    "role_replace",
    "blocked_cancel",
    "blocked_deadline",
    "slow_consumer",
    "resource_rows",
    "resource_batch",
    "late_read_close_error",
    "tls_require",
    "transaction_early_close",
    "transaction_role_replace",
    "transaction_cancel",
)


def control_records(resource, directory, report, path):
    from _pietto_phase68_slice6_cases import original

    artifact = original(
        directory / (PREFIX + "control-input"),
        "postgres",
        "G_emission_table_bag",
        "bag",
    )
    report["controls"] = []
    blocked_entry = None
    for kind in CONTROL_CASES:
        if kind == "stable_update":

            def update(stage, owner, record):
                if stage == "opened":
                    manager(
                        resource,
                        'UPDATE public."phase66 source é" SET "order.id"=42 WHERE "order.id"=0',
                    )
                    record["interventions"].append(
                        {"kind": "writer_commit_after_snapshot", "value": 42}
                    )

            first = attempt(resource, artifact, hook=update)
            fresh = attempt(resource, artifact)
            result = {"control": kind, "original": first, "fresh": fresh}
            manager(
                resource,
                'UPDATE public."phase66 source é" SET "order.id"=0 WHERE "order.id"=42',
            )
        elif kind in ("serializable", "tls_require"):

            def observe_tls(stage, owner, record):
                if stage == "opened":
                    record["tls_observation"] = manager(
                        resource,
                        "SELECT ssl,version,cipher FROM pg_catalog.pg_stat_ssl WHERE pid=$1",
                        (owner.session_id,),
                    )

            result = attempt(
                resource,
                artifact,
                isolation="serializable" if kind == "serializable" else "stable",
                sslmode="require" if kind == "tls_require" else "disable",
                hook=observe_tls if kind == "tls_require" else None,
            )
            result["control"] = kind
        else:
            seconds = 60
            if kind in ("blocked_deadline", "slow_consumer"):
                if blocked_entry is None:
                    raise ValueError("S09_BLOCK_ENTRY_REQUIRED")
                seconds = blocked_entry + 4
            result = controlled(resource, artifact, kind, seconds=seconds)
            if kind == "blocked_cancel":
                blocked_entry = next(
                    e["since_open_seconds"]
                    for e in result["interventions"]
                    if e["kind"] == "actual_native_lock_wait"
                )
        report["controls"].append(result)
        write(path, report)
        print(report["origin"], "control", kind, result.get("failure"), flush=True)


def source_records(resource, directory, report, path):
    """Finite admitted mechanisms and pre-evaluation negatives on owned inputs."""
    from _pietto_phase68_slice6_cases import original
    from pietto._project.project_execution_source import RetainedSourceRequirement
    from pietto._project.project_result_output import prepare_output
    from pietto._project.project_refinement import prepare_refinement, TieRefinement

    artifact = original(
        directory / (PREFIX + "source-input"), "postgres", "G_emission_table_bag", "bag"
    )
    if artifact is None:
        raise ValueError("S09_SOURCE_CONTROL_ARTIFACT")
    report["source_controls"] = []

    def keep(name, result):
        result["source_control"] = name
        report["source_controls"].append(result)
        write(path, report)
        print(report["origin"], "source", name, result.get("failure"), flush=True)

    manager(resource, 'ALTER TABLE public."phase66 source é" RENAME TO p68s9_original')
    manager(
        resource,
        "CREATE VIEW public.p68s9_invoker WITH (security_invoker=true) AS SELECT * FROM public.p68s9_original",
    )
    manager(
        resource,
        'CREATE VIEW public."phase66 source é" AS SELECT * FROM public.p68s9_invoker UNION ALL SELECT * FROM public.p68s9_invoker',
    )
    manager(resource, "REVOKE SELECT ON public.p68s9_original FROM pietto_query")
    manager(resource, 'GRANT SELECT ON public."phase66 source é" TO pietto_query')
    keep(
        "nested_definer_invoker_requires_query_base_privilege",
        attempt(resource, artifact),
    )
    manager(resource, "ALTER VIEW public.p68s9_invoker SET (security_invoker=false)")
    manager(
        resource, 'ALTER VIEW public."phase66 source é" SET (security_invoker=true)'
    )
    manager(resource, "GRANT SELECT ON public.p68s9_invoker TO pietto_query")
    keep("nested_invoker_definer_union_all_no_base_select", attempt(resource, artifact))
    manager(resource, 'DROP VIEW public."phase66 source é"')
    manager(
        resource,
        "CREATE FUNCTION public.p68s9_opaque() RETURNS boolean LANGUAGE sql STABLE AS 'SELECT true'",
    )
    manager(
        resource,
        'CREATE VIEW public."phase66 source é" AS SELECT * FROM public.p68s9_original WHERE public.p68s9_opaque()',
    )
    manager(resource, 'GRANT SELECT ON public."phase66 source é" TO pietto_query')
    keep("opaque_function_before_evaluation", attempt(resource, artifact))
    manager(resource, 'DROP VIEW public."phase66 source é"')
    manager(
        resource,
        "CREATE FUNCTION public.p68s9_equal(bigint,bigint) RETURNS boolean LANGUAGE sql IMMUTABLE AS 'SELECT $1=$2'",
    )
    manager(
        resource,
        "CREATE OPERATOR public.=== (LEFTARG=bigint,RIGHTARG=bigint,FUNCTION=public.p68s9_equal)",
    )
    manager(
        resource,
        'CREATE VIEW public."phase66 source é" AS SELECT * FROM public.p68s9_original WHERE "order.id" OPERATOR(public.===) "order.id"',
    )
    manager(resource, 'GRANT SELECT ON public."phase66 source é" TO pietto_query')
    keep("custom_operator_before_evaluation", attempt(resource, artifact))
    manager(resource, 'DROP VIEW public."phase66 source é"')
    manager(resource, "DROP VIEW public.p68s9_invoker")
    manager(resource, 'ALTER TABLE public.p68s9_original RENAME TO "phase66 source é"')
    manager(resource, 'GRANT SELECT ON public."phase66 source é" TO pietto_query')
    manager(resource, 'ALTER TABLE public."phase66 source é" ENABLE ROW LEVEL SECURITY')
    manager(
        resource,
        'CREATE POLICY p68s9_policy ON public."phase66 source é" USING (public.p68s9_opaque())',
    )
    keep("unqualified_rls_before_evaluation", attempt(resource, artifact))
    manager(resource, 'DROP POLICY p68s9_policy ON public."phase66 source é"')
    manager(
        resource, 'ALTER TABLE public."phase66 source é" DISABLE ROW LEVEL SECURITY'
    )
    manager(
        resource,
        'ALTER TABLE public."phase66 source é" ADD COLUMN p68s9_abs BIGINT GENERATED ALWAYS AS (pg_catalog.abs("order.id")) VIRTUAL',
    )
    keep("qualified_builtin_virtual_expression", attempt(resource, artifact))
    manager(resource, 'ALTER TABLE public."phase66 source é" DROP COLUMN p68s9_abs')
    manager(
        resource,
        'ALTER TABLE public."phase66 source é" ADD COLUMN p68s9_hash TEXT GENERATED ALWAYS AS (pg_catalog.md5("text `""é")) VIRTUAL',
    )
    keep("unqualified_virtual_expression", attempt(resource, artifact))
    manager(resource, 'ALTER TABLE public."phase66 source é" DROP COLUMN p68s9_hash')
    manager(
        resource,
        'ALTER TABLE public."phase66 source é" ADD COLUMN p68s9_token BIGINT GENERATED ALWAYS AS IDENTITY',
    )
    manager(resource, 'ALTER TABLE public."phase66 source é" RENAME TO p68s9_original')
    manager(
        resource,
        'CREATE VIEW public."phase66 source é" AS SELECT * FROM public.p68s9_original',
    )
    manager(
        resource,
        "CREATE TABLE public.p68s9_registry_base(provider TEXT,version_tag TEXT,active INTEGER,revision TEXT)",
    )
    manager(
        resource,
        "INSERT INTO public.p68s9_registry_base VALUES('p68-source-control','v1',1,'r1')",
    )
    manager(
        resource,
        "CREATE VIEW public.p68s9_registry AS SELECT * FROM public.p68s9_registry_base",
    )
    manager(
        resource,
        'GRANT SELECT ON public."phase66 source é",public.p68s9_registry TO pietto_query',
    )
    manager(resource, "SET search_path=pg_catalog")
    definition = manager(
        resource,
        "SELECT pg_catalog.pg_get_viewdef($1::regclass,true)",
        ('public."phase66 source é"',),
    )[0][0]
    requirement = RetainedSourceRequirement(
        artifact.request.sources[0],
        "p68-source-control",
        "v1",
        "r1",
        "public",
        "p68s9_registry",
        definition,
        ("p68s9_token",),
        "pietto_query",
        "Owned fixture retains the same token/payload version for this bounded history.",
    )
    query = prepare_refinement(
        artifact,
        (requirement,),
        policy=TieRefinement(),
        output=prepare_output(artifact),
    )
    keep("qualified_registry_view_and_key", attempt(resource, artifact, query=query))
    manager(resource, "DROP VIEW public.p68s9_registry")
    manager(
        resource,
        "CREATE FUNCTION public.p68s9_active() RETURNS integer LANGUAGE sql STABLE AS 'SELECT 1'",
    )
    manager(
        resource,
        "CREATE VIEW public.p68s9_registry AS SELECT provider,version_tag,public.p68s9_active() AS active,revision FROM public.p68s9_registry_base",
    )
    manager(resource, "GRANT SELECT ON public.p68s9_registry TO pietto_query")
    keep("registry_wrapper_before_values", attempt(resource, artifact, query=query))
    manager(resource, "DROP VIEW public.p68s9_registry")
    manager(resource, 'DROP VIEW public."phase66 source é"')
    manager(resource, "DROP TABLE public.p68s9_registry_base")
    manager(resource, "ALTER TABLE public.p68s9_original DROP COLUMN p68s9_token")
    manager(resource, 'ALTER TABLE public.p68s9_original RENAME TO "phase66 source é"')
    manager(resource, "DROP OPERATOR public.=== (bigint,bigint)")
    manager(resource, "DROP FUNCTION public.p68s9_equal(bigint,bigint)")
    manager(resource, "DROP FUNCTION public.p68s9_opaque()")
    manager(resource, "DROP FUNCTION public.p68s9_active()")
    manager(resource, "SET search_path=public")
