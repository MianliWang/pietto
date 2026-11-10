"""External literal-none adapter around the existing full MySQL native witness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
PROFILE = "mysql-none-exec-stdio-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def binding(candidate: Path, wheel: Path) -> dict[str, str]:
    patch = subprocess.run(("git", "-C", str(candidate), "diff", "--binary", "HEAD"), capture_output=True, check=True).stdout
    return {
        "head": subprocess.check_output(("git", "-C", str(candidate), "rev-parse", "HEAD"), text=True).strip(),
        "patch_sha256": hashlib.sha256(patch).hexdigest(),
        "pins_sha256": sha256(candidate / "tests/phase66_target_pins.json"),
        "lock_sha256": sha256(candidate / "uv.lock"),
        "wheel_sha256": sha256(wheel),
    }


def ipc_worker(python: Path, config: dict[str, Any], env: dict[str, str], directory: Path, *, label: str, failure: str) -> dict[str, Any]:
    source = '''
import json
from pathlib import Path
import pyarrow as pa
import pietto.execution as pe
import pietto._project.project_execution_mysql as mysql_execution
import pietto._project.project_execution_mysql_context as mysql_context
cfg = json.load(__import__("sys").stdin)
context_summary = {"count": 0, "first": None, "first_shape": None, "calls": [], "mismatches": [], "shape_mismatches": [], "truncated": False}
native_summary = {"count": 0, "first_expected": None, "first_returned": None, "calls": [], "mismatches": [], "error": None}
def compact(value):
    if type(value) is str and len(value.encode("utf-8")) > 256:
        context_summary["truncated"] = True
        return {"truncated_bytes": len(value.encode("utf-8"))}
    return value
original_read = mysql_context.read_control
original_native = mysql_context.native_context
def read_observed(owner, sql, *args, **kwargs):
    result = original_read(owner, sql, *args, **kwargs)
    if sql == mysql_context.CONTEXT_SQL:
        context_summary["count"] += 1
        shape = {"row_count": len(result[1]), "arities": [len(row) if isinstance(row, tuple) else None for row in result[1][:8]]}
        row = [compact(value) for value in result[1][0]] if shape == {"row_count": 1, "arities": [16]} else None
        call = {"session_id": owner.session_id, "data_connection": getattr(owner._connection, "connection_id", None), "control_connection": getattr(owner._control_connection, "connection_id", None)}
        if len(context_summary["calls"]) < 8:
            context_summary["calls"].append(call)
        if context_summary["first_shape"] is None:
            context_summary["first_shape"] = shape
        elif shape != context_summary["first_shape"] and len(context_summary["shape_mismatches"]) < 2:
            context_summary["shape_mismatches"].append({"call": call, "shape": shape})
        if context_summary["first"] is None and row is not None:
            context_summary["first"] = row
        elif row is not None and row != context_summary["first"] and len(context_summary["mismatches"]) < 2:
            context_summary["mismatches"].append({"call": call, "fields": [index for index, pair in enumerate(zip(context_summary["first"] or (), row or (), strict=False)) if pair[0] != pair[1]], "row": row})
    return result
def native_observed(owner):
    expected = {
        "prefix": [owner.request.artifact.request.release, owner.request.access.account, owner.request.access.roles, owner.session_id, owner.request.access.database, "REPEATABLE-READ" if owner.request.isolation == "stable" else "SERIALIZABLE", "utf8mb4", "utf8mb4", "utf8mb4", "utf8mb4_0900_bin"],
        "sql_mode_set": sorted(mysql_context.SQL_MODE.split(",")),
        "time_zone": "+00:00",
        "lower_case_table_names": 0,
        "cte_max_recursion_depth": "nonnegative_int",
        "server_uuid": "nonempty_str",
        "max_allowed_packet": "positive_int",
    }
    native_summary["count"] += 1
    call = {"session_id": owner.session_id, "data_connection": getattr(owner._connection, "connection_id", None), "control_connection": getattr(owner._control_connection, "connection_id", None)}
    if len(native_summary["calls"]) < 8:
        native_summary["calls"].append(call)
    if native_summary["first_expected"] is None:
        native_summary["first_expected"] = expected
    elif expected != native_summary["first_expected"] and len(native_summary["mismatches"]) < 2:
        native_summary["mismatches"].append({"call": call, "expected": expected})
    try:
        value = original_native(owner)
    except BaseException as error:
        native_summary["error"] = {"kind": type(error).__name__, "detail": str(error)[:512]}
        raise
    if context_summary["truncated"] is True:
        raise RuntimeError("NATIVE_CONTEXT_CAPTURE_BOUNDS")
    returned = [compact(item) for item in value]
    if native_summary["first_returned"] is None:
        native_summary["first_returned"] = returned
    elif returned != native_summary["first_returned"] and len(native_summary["mismatches"]) < 2:
        native_summary["mismatches"].append({"call": call, "returned": returned})
    if context_summary["truncated"] is True:
        raise RuntimeError("NATIVE_CONTEXT_CAPTURE_BOUNDS")
    return value
mysql_context.read_control = read_observed
mysql_execution.native_context = native_observed
if cfg.get("finite_selftest") is True:
    class Box:
        pass
    owner = Box()
    owner.session_id = 1
    owner._connection = Box(); owner._connection.connection_id = 2
    owner._control_connection = Box(); owner._control_connection.connection_id = 3
    owner.request = Box(); owner.request.isolation = "stable"
    owner.request.artifact = Box(); owner.request.artifact.request = Box(); owner.request.artifact.request.release = "8.4.12"
    owner.request.access = Box(); owner.request.access.account = "acct"; owner.request.access.roles = "NONE"; owner.request.access.database = "phase66"
    row = ("8.4.12", "acct", "NONE", 1, "phase66", "REPEATABLE-READ", "utf8mb4", "utf8mb4", "utf8mb4", "utf8mb4_0900_bin", mysql_context.SQL_MODE, "+00:00", 0, 1000, "uuid", 1024)
    original_read = lambda *_args, **_kwargs: ((), (row,))
    returned = list(row[:15])
    if cfg.get("finite_oversized") is True:
        returned[-1] = "x" * 257
    original_native = lambda _owner: tuple(returned)
    try:
        for _ in range(12):
            read_observed(owner, mysql_context.CONTEXT_SQL)
            native_observed(owner)
        original_read = lambda *_args, **_kwargs: ((), ((1,), (2,)))
        read_observed(owner, mysql_context.CONTEXT_SQL)
    except BaseException as error:
        print(json.dumps({"terminal": "finite_error", "native_context": {"native": native_summary, "context": context_summary}, "error": {"kind": type(error).__name__, "detail": str(error)[:512]}}))
        raise
    print(json.dumps({"terminal": "finite_selftest", "native_context": {"native": native_summary, "context": context_summary}}))
    raise SystemExit(0)
query = pe.compile_query(Path(cfg["project"]), module="main.pietto", kind="table", name="result", dialect="mysql", emission_contract="contract.json")
access = pe.MySQLAccess("localhost", cfg["port"], "phase66", "pietto_query", cfg["password"], cfg["ca"], "pietto_query@%")
premise = pe.MySQLDeploymentPremise(schemas=("phase66",))
def execute_once():
    records = []
    with pe.execute(query, route="mysql_rows", access=access, premise=premise, limits=pe.ExecutionLimits(batch_rows=1, seconds=10)) as handle:
        for batch in handle:
            with batch:
                records.append(pa.record_batch(batch))
    outcome = handle.outcome
    rows = [row for record in records for row in record.to_pylist()]
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, records[0].schema) as writer:
        for record in records:
            writer.write_batch(record)
    round_trip = [row for batch in pa.ipc.open_stream(sink.getvalue()) for row in batch.to_pylist()]
    return {"rows": [[row["left_id"], row["right_key"]] for row in rows], "ipc_rows": [[row["left_id"], row["right_key"]] for row in round_trip], "schema": [[field.name, str(field.type), field.nullable] for field in records[0].schema], "end": outcome.end, "batches": outcome.batches, "delivered_rows": outcome.rows}
try:
    if cfg.get("recording") is True:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        trace.set_tracer_provider(TracerProvider())
        with trace.get_tracer("pietto.s06.witness").start_as_current_span("mysql-context-control") as span:
            if not span.is_recording():
                raise RuntimeError("OTEL_NOT_RECORDING")
            result = execute_once()
    else:
        result = execute_once()
    print(json.dumps({"terminal": "success", "native_context": {"native": native_summary, "context": context_summary}, **result}))
except BaseException as error:
    print(json.dumps({"terminal": "error", "native_context": {"native": native_summary, "context": context_summary}, "error": {"kind": type(error).__name__, "detail": str(error)[:512]}}))
    raise
'''
    project = Path(config["project"])
    password = str(config["password"])
    frozen = directory / (label + "-input")
    frozen.mkdir(mode=0o700)
    input_hashes: dict[str, str] = {}
    for name in ("main.pietto", "pietto.toml", "contract.json"):
        data = (project / name).read_bytes()
        (frozen / name).write_bytes(data)
        input_hashes[name] = hashlib.sha256(data).hexdigest()
    child_config = dict(config) | {"project": str(frozen)}
    raw_path = directory / (label + ".json")
    raw = {
        "format": "pietto.mysql-none-ipc-worker.v2",
        "argv": [str(python), "-I", "-B", "-c", "IPC_WORKER"],
        "config_sha256": hashlib.sha256(json.dumps(child_config, sort_keys=True).encode()).hexdigest(),
        "inputs": input_hashes,
        "launch": "NOT_STARTED",
        "returncode": None,
        "timed_out": False,
        "capture_overflow": False,
        "stdout": "",
        "stderr": "",
        "stdout_bytes": 0,
        "stderr_bytes": 0,
    }
    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    output: dict[object, bytearray] = {}
    try:
        process = subprocess.Popen((str(python), "-I", "-B", "-c", source), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        raw["launch"] = "STARTED"
        assert process.stdin is not None and process.stdout is not None and process.stderr is not None
        process.stdin.write(json.dumps(child_config).encode())
        process.stdin.close()
        for stream in (process.stdout, process.stderr):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ)
            output[stream] = bytearray()
        deadline = time.monotonic() + 120
        while selector.get_map():
            if time.monotonic() >= deadline:
                raw["timed_out"] = True
                process.kill()
            for key, _ in selector.select(max(0, min(0.2, deadline - time.monotonic()))):
                data = os.read(key.fd, 4097)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if len(output[key.fileobj]) + len(data) > 4096:
                    raw["capture_overflow"] = True
                    process.kill()
                    selector.unregister(key.fileobj)
                else:
                    output[key.fileobj].extend(data)
        process.wait(timeout=5)
        raw["returncode"] = process.returncode
    except OSError as error:
        raw["launch"] = "ERROR"
        raw["stderr"] = (type(error).__name__ + ": " + str(error)).replace(password, "[REDACTED]")[:4096]
    except subprocess.TimeoutExpired:
        raw["timed_out"] = True
    finally:
        selector.close()
        if process is not None and process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                raw["returncode"] = "UNREAPED"
        if process is not None and raw["returncode"] is None:
            raw["returncode"] = process.returncode
        if process is not None:
            assert process.stdout is not None and process.stderr is not None
            raw["stdout"] = bytes(output.get(process.stdout, b"")).decode("utf-8", "replace").replace(password, "[REDACTED]")
            raw["stderr"] = bytes(output.get(process.stderr, b"")).decode("utf-8", "replace").replace(password, "[REDACTED]")
            raw["stdout_bytes"] = len(raw["stdout"].encode())
            raw["stderr_bytes"] = len(raw["stderr"].encode())
        try:
            raw["record"] = json.loads(raw["stdout"])
        except (TypeError, json.JSONDecodeError):
            raw["record"] = None
        raw["inputs_after"] = {name: sha256(frozen / name) for name in input_hashes}
        raw["inputs_unchanged"] = raw["inputs_after"] == input_hashes
        raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if raw["launch"] != "STARTED" or raw["returncode"] != 0 or raw["timed_out"] or raw["capture_overflow"] or raw["inputs_unchanged"] is not True:
        raise ValueError(failure)
    return raw["record"]


def run(args: argparse.Namespace) -> int:
    candidate, wheel, directory = args.candidate.resolve(), args.wheel.resolve(), args.run_dir.resolve()
    require(not directory.exists() and not directory.is_relative_to(candidate), "RUN_DIRECTORY")
    require(sha256(wheel) == args.wheel_sha256, "WHEEL")
    require(args.house.is_dir() and args.otel_house.is_dir(), "WHEELHOUSE")
    expected = json.loads(args.expected_binding.read_text(encoding="utf-8"))
    require(expected == binding(candidate, wheel), "BINDING_DRIFT")
    tests = candidate / "tests"
    sys.path.insert(0, str(tests))
    import _pietto_execution_api_mysql_native as native
    import _pietto_execution_installation_probe as installation
    import _pietto_target_conformance_resources as resources

    class NoneResource(resources.Resources):
        def __init__(self, target: str, pin: dict[str, Any], service: Path):
            require(target == "mysql", "TARGET")
            os.environ["PIETTO_NATIVE_OFFLINE"] = "1"
            os.environ.pop("PIETTO_NATIVE_OFFLINE_TRANSPORT", None)
            super().__init__(target, pin, service)
            self.name = "pietto-p77-maint-my-" + self.nonce
            self.relay: subprocess.Popen[str] | None = None
            self.relay_port = directory / "relay.port"
            self.relay_log = directory / "relay.jsonl"
            frozen = service.parent / "expected-binding.json"
            frozen.write_bytes(args.expected_binding.read_bytes())
            require(
                sha256(frozen) == sha256(args.expected_binding)
                and json.loads(frozen.read_text(encoding="utf-8")) == binding(candidate, wheel),
                "PREFLIGHT_COPY",
            )
            self.event("preflight_bound", path=frozen.name, sha256=sha256(frozen))

        def acquire(self) -> None:
            require(Path("/var/run/docker.sock").is_socket(), "DOCKER_SOCKET")
            image = self.pin["repository"] + "@" + self.pin["platform_digest"]
            self.acquire_image(image)
            self.event("image_pin_bound", config_digest=self.pin["config_digest"], platform_digest=self.pin["platform_digest"])
            password = self._passwords[0]
            label = "pietto.phase66.invocation=" + self.nonce
            self.event("container_create_intent", name=self.name, nonce=self.nonce, label=label, image=image, profile=PROFILE)
            self.container_id = self.docker(
                "container", "create", "--platform", "linux/amd64", "--name", self.name,
                "--label", label, "--network", "none",
                "--pull=never", "--cpuset-cpus", "0-7", "--memory", "1g", "--cpus", "1",
                "--pids-limit", "128", "--no-healthcheck", "--tmpfs", "/var/lib/mysql:rw,size=536870912",
                "--env", "MYSQL_ROOT_PASSWORD", "--env", "MYSQL_ROOT_HOST", "--env", "MYSQL_DATABASE", image, "mysqld",
                "--character-set-server=utf8mb4", "--collation-server=utf8mb4_0900_bin",
                "--bind-address=127.0.0.1", "--sql-mode=" + resources.MYSQL_MODE, "--max-execution-time=10000",
                extra_env={"MYSQL_ROOT_PASSWORD": password, "MYSQL_ROOT_HOST": "%", "MYSQL_DATABASE": "phase66"},
            )
            require(self.owned("container", self.inspect_resource("container", self.container_id)), "CONTAINER_OWNERSHIP")
            self.event("container_acquired", id=self.container_id, name=self.name, nonce=self.nonce, label=label)
            self.docker("container", "start", self.container_id, timeout=30)
            docker = ("docker", "--config", str(self.docker_config), "--host", "unix:///var/run/docker.sock")
            inspect = subprocess.run((*docker, "container", "inspect", self.container_id, "--format", '{{json .HostConfig.NetworkMode}} {{json .NetworkSettings.Networks}}'), env=resources.clean_environment(), capture_output=True, text=True, timeout=20, check=False)
            require(inspect.returncode == 0, "NETWORK_INSPECT")
            mode, raw_networks = inspect.stdout.strip().split(" ", 1)
            networks = json.loads(raw_networks)
            require(json.loads(mode) == "none" and isinstance(networks, dict), "NETWORK_NONE")
            require(not any(isinstance(item, dict) and any(item.get(key) for key in ("IPAddress", "Gateway", "GlobalIPv6Address", "IPv6Gateway")) for item in networks.values()), "NETWORK_ATTACHMENT")
            route_text: dict[str, str] = {}
            for family, path in (("ipv4", "/proc/net/route"), ("ipv6", "/proc/net/ipv6_route")):
                output = subprocess.run((*docker, "container", "exec", self.container_id, "cat", path), env=resources.clean_environment(), capture_output=True, text=True, timeout=20, check=False)
                require(output.returncode == 0, "ROUTES")
                route_text[family] = output.stdout
            resources.verify_no_default_route(route_text["ipv4"], route_text["ipv6"])
            self.event("container_start_observed", id=self.container_id, image=self.runtime_image_id, network_mode="none", networks=networks)
            self.event("none_network_verified", network_mode="none", raw_networks=networks, routes=route_text)
            for _ in range(60):
                ready = subprocess.run(
                    (*docker, "container", "exec", "--env", "MYSQL_PWD", self.container_id, "mysql", "--protocol=TCP", "--host=127.0.0.1", "--port=3306", "-uroot", "--batch", "--skip-column-names", "-e", "SELECT USER(), CURRENT_USER()"),
                    env=resources.clean_environment() | {"MYSQL_PWD": password}, capture_output=True, text=True, timeout=5, check=False,
                )
                if ready.returncode == 0:
                    identities = [line.split("\t") for line in ready.stdout.splitlines()]
                    require(len(identities) == 1 and len(identities[0]) == 2 and all(identities[0]), "TCP_AUTH")
                    self.event("tcp_ready", host="127.0.0.1", port=3306, authenticated=True, user_host=identities[0])
                    break
                time.sleep(1)
            else:
                raise TimeoutError("MYSQL_READY")
            self.relay = subprocess.Popen((sys.executable, "-I", str(HERE / "relay.py"), "--container", self.container_id, "--docker-config", str(self.docker_config), "--port-file", str(self.relay_port), "--log-file", str(self.relay_log)), env=resources.clean_environment(), text=True)
            for _ in range(100):
                if self.relay_port.is_file():
                    self.port = int(self.relay_port.read_text(encoding="ascii"))
                    break
                require(self.relay.poll() is None, "RELAY_START")
                time.sleep(0.1)
            else:
                raise TimeoutError("RELAY_PORT")
            certificate = self.docker("container", "exec", self.container_id, "cat", "/var/lib/mysql/ca.pem")
            self.ca_path.write_text(certificate + "\n", encoding="utf-8")
            self.ca_identity = {"container_id": self.container_id, "image_config": self.pin["config_digest"], "sha256": sha256(self.ca_path)}
            self.startup_started = time.monotonic()
            try:
                self.manager = self.connect(query=False)
            except Exception as error:
                message = self.without_secrets(str(error))[:512]
                self.event(
                    "manager_connection_failure",
                    kind=type(error).__name__,
                    errno=getattr(error, "errno", None),
                    sqlstate=getattr(error, "sqlstate", None),
                    message=message,
                )
                raise

        def cleanup(self) -> dict[str, Any]:
            failures: list[str] = []
            for name in ("query", "manager"):
                connection = getattr(self, name)
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:
                        failures.append(name)
            if self.relay is not None:
                try:
                    self.relay.terminate()
                    try:
                        self.relay.wait(15)
                    except subprocess.TimeoutExpired:
                        self.relay.kill()
                        self.relay.wait(5)
                    relay_records = [json.loads(line) for line in self.relay_log.read_text(encoding="utf-8").splitlines()]
                    if relay_records and relay_records[-1].get("event") == "closed":
                        self.event("relay_closed", children=relay_records[-1].get("children"))
                    else:
                        failures.append("relay")
                except Exception:
                    failures.append("relay")
            if self.container_id is not None:
                try:
                    require(self.owned("container", self.inspect_resource("container", self.container_id)), "CLEANUP_OWNERSHIP")
                    self.docker("container", "rm", "--force", "--volumes", self.container_id, timeout=30)
                    require(self.docker("container", "ls", "--all", "--no-trunc", "--filter", "id=" + self.container_id, "--format", "{{.ID}}", timeout=20) == "", "CLEANUP_ABSENT")
                    self.event("container_removed", id=self.container_id)
                except Exception:
                    failures.append("container")
            result = {"status": "success" if not failures else "failed", "absent": {"container": not failures, "network": True}, "failures": failures}
            self.event("cleanup_complete", result=result)
            return result

    original_resource, original_worker = resources.Resources, native._worker
    original_terminal_worker = native._terminal_worker
    original_environment, original_download = installation._environment, installation._download
    ipc: dict[str, Any] | None = None

    def worker(python: Path, work: Path, config: dict[str, Any]) -> dict[str, Any]:
        nonlocal ipc
        if config.get("case") != "main":
            return original_worker(python, work, config)
        main_raw: dict[str, Any] = {"format": "pietto.mysql-none-main-worker.v2", "terminal": None, "result": None}
        main_config: dict[str, Any] | None = None
        frozen_main = work / "main-worker-input"
        try:
            source_project = Path(config["project"])
            frozen_main.mkdir(mode=0o700)
            inputs: dict[str, str] = {}
            for name in ("main.pietto", "pietto.toml", "contract.json"):
                data = (source_project / name).read_bytes()
                (frozen_main / name).write_bytes(data)
                inputs[name] = hashlib.sha256(data).hexdigest()
            main_config = dict(config) | {"project": str(frozen_main)}
            main_raw.update(
                config_sha256=hashlib.sha256(json.dumps(main_config, sort_keys=True).encode()).hexdigest(),
                inputs=inputs,
                inputs_after={name: sha256(frozen_main / name) for name in inputs},
            )
            main_raw["inputs_unchanged"] = main_raw["inputs_after"] == inputs
        except BaseException as error:
            main_raw["terminal"] = {"kind": type(error).__name__, "message": str(error)[:512], "state": "INPUT_BLOCKED"}
            (work / "main-worker.json").write_text(json.dumps(main_raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (work / "context-observers.json").write_text(json.dumps({"recording": "BLOCKED_INPUT", "plain": "BLOCKED_INPUT"}) + "\n", encoding="utf-8")
            raise ValueError("MAIN_INPUT_BLOCKED")
        value: dict[str, Any] | None = None
        main_error: BaseException | None = None
        try:
            value = original_worker(python, work, main_config)
            main_raw["terminal"] = {"state": "RETURNED"}
            main_raw["result"] = value
        except BaseException as error:
            main_error = error
            main_raw["terminal"] = {"kind": type(error).__name__, "message": str(error)[:512], "state": "RAISED"}
        main_raw["inputs_after"] = {name: sha256(frozen_main / name) for name in main_raw["inputs"]}
        main_raw["inputs_unchanged"] = main_raw["inputs_after"] == main_raw["inputs"]
        (work / "main-worker.json").write_text(json.dumps(main_raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        observed: dict[str, str] = {}
        control: dict[str, Any] | None = None
        try:
            control = ipc_worker(python, dict(main_config) | {"recording": True}, resources.clean_environment(), work, label="context-main", failure="CONTEXT_CONTROL")
            observed["recording"] = "RETURNED"
        except ValueError as error:
            observed["recording"] = str(error)
        try:
            ipc = ipc_worker(python, dict(main_config) | {"recording": False}, resources.clean_environment(), work, label="ipc-worker", failure="IPC_WORKER")
            observed["plain"] = "RETURNED"
        except ValueError as error:
            observed["plain"] = str(error)
        (work / "context-observers.json").write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        expected_rows = [[1, None], [1, None]]
        if main_error is not None or main_raw["inputs_unchanged"] is not True or value is None or value.get("rows", {}).get("end") != "COMPLETE" or value.get("rows", {}).get("rows") != expected_rows or value.get("bundle", {}).get("end") != "COMPLETE" or value.get("bundle", {}).get("rows") != expected_rows:
            raise ValueError("MAIN_WORKER_TERMINAL")
        if control is None or control.get("terminal") != "success":
            raise ValueError("CONTEXT_CONTROL")
        if ipc is None:
            raise ValueError("IPC_WORKER")
        return value

    def terminal_worker(python: Path, work: Path, config: dict[str, Any], resource: Any, terminal: str) -> dict[str, Any]:
        if terminal == "deadline" and config.get("terminal_seconds") == 1.0:
            resource.event("literal_none_deadline_window", original_seconds=1.0, adjusted_seconds=5.0, reason="deadline_before_open_ready_r7")
            config = dict(config) | {"terminal_seconds": 5.0}
        return original_terminal_worker(python, work, config, resource, terminal)

    def offline_environment(cache: Path) -> dict[str, str]:
        value = original_environment(cache)
        value.update(UV_PYTHON="3.13.13", UV_OFFLINE="1", UV_PYTHON_DOWNLOADS="never", UV_LINK_MODE="copy")
        return value

    resources.Resources, native._worker, native._terminal_worker = NoneResource, worker, terminal_worker
    installation._environment = offline_environment
    installation._download = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("WHEELHOUSE_MISSING"))
    try:
        report_path = native.campaign(directory, wheel, "3.13.13", args.house, args.otel_house)
    finally:
        resources.Resources, native._worker, native._terminal_worker = original_resource, original_worker, original_terminal_worker
        installation._environment, installation._download = original_environment, original_download
    report = json.loads(report_path.read_text(encoding="utf-8"))
    native.check(report)
    require(ipc is not None and ipc.get("rows") == [[1, None], [1, None]] and ipc.get("ipc_rows") == [[1, None], [1, None]] and ipc.get("schema") == [["left_id", "int64", False], ["right_key", "int64", True]] and ipc.get("end") == "COMPLETE" and ipc.get("batches") == 2 and ipc.get("delivered_rows") == 2, "IPC")
    require(report.get("cleanup") == "PASS", "CLEANUP")
    relay_log = directory / "relay.jsonl"
    sources = {name: sha256(HERE / name) for name in ("campaign.py", "judge.py", "relay.py", "mysql.sh", "preflight.py")}
    receipt = {
        "binding": binding(candidate, wheel), "native_report": report, "ipc": ipc,
        "sources": sources,
        "transport": {"profile": PROFILE, "network": {"mode": "none", "attached": []}, "container_port": 3306, "relay_sha256": sha256(HERE / "relay.py"), "relay_command": "docker container exec -i /bin/bash -c fixed-3306-forward", "route_tables": {"default_ipv4": False, "default_ipv6": False}},
    }
    receipt_path = directory / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    resources_path = directory / "service/resources.jsonl"
    subprocess.run((sys.executable, "-I", str(HERE / "judge.py"), "--receipt", str(receipt_path), "--relay-log", str(relay_log), "--relay", str(HERE / "relay.py"), "--report", str(report_path), "--candidate", str(candidate), "--wheel", str(wheel), "--resources", str(resources_path)), check=True, timeout=30)
    verdict = {
        "format": "pietto.mysql-none-maintenance-verdict.v1",
        "binding": binding(candidate, wheel),
        "sources": sources,
        "files": {
            "expected_binding": sha256(directory / "expected-binding.json"),
            "receipt": sha256(receipt_path),
            "native_report": sha256(report_path),
            "resources": sha256(resources_path),
            "relay": sha256(relay_log),
        },
        "verdict": "ACCEPTED",
    }
    verdict_path = directory / "verdict.json"
    verdict_path.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(verdict_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--wheel-sha256", required=True)
    parser.add_argument("--house", type=Path, required=True)
    parser.add_argument("--otel-house", type=Path, required=True)
    parser.add_argument("--expected-binding", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    return run(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
