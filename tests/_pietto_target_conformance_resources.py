"""Explicit, bounded ownership of one local Docker test instance."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import stat
import subprocess
import time
from typing import Any, Iterator
import uuid

ENDPOINT = "unix:///var/run/docker.sock"
STARTUP_SECONDS = 120
CONNECT_CHECKPOINTS = (10, 60)
MAX_CONNECT_ATTEMPTS = 3
QUERY_SECONDS = 10
READ_SECONDS = 20
CLEANUP_SECONDS = 30
MYSQL_MODE = "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION"
MYSQL_TLS_VERSIONS = ("TLSv1.2", "TLSv1.3")


@contextmanager
def deadline(seconds: float) -> Iterator[None]:
    if seconds <= 0 or not hasattr(signal, "SIGALRM"):
        raise TimeoutError("deadline unavailable or exhausted")
    started = time.monotonic()
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)

    def expired(signum: int, frame: object) -> None:
        raise TimeoutError("operation deadline exceeded")

    signal.signal(signal.SIGALRM, expired)
    effective = min(seconds, previous_timer[0]) if previous_timer[0] else seconds
    signal.setitimer(signal.ITIMER_REAL, effective)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0]:
            signal.setitimer(
                signal.ITIMER_REAL,
                max(0.000001, previous_timer[0] - (time.monotonic() - started)),
                previous_timer[1],
            )


def clean_environment() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PG")
        and key
        not in {
            "DATABASE_URL",
            "MYSQL_HOST",
            "MYSQL_TCP_PORT",
            "MYSQL_UNIX_PORT",
            "MYSQL_PWD",
            "MYSQL_HOME",
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
            "DOCKER_API_VERSION",
            "PYTHONPATH",
            "PYTHONHOME",
            "PSYCOPG_IMPL",
            "SSLKEYLOGFILE",
        }
    } | {"PSYCOPG_IMPL": "binary", "PYTHONNOUSERSITE": "1"}


def error_fact(error: BaseException, stage: str) -> dict[str, Any]:
    return {
        "stage": stage,
        "kind": type(error).__name__,
        "sqlstate": getattr(error, "sqlstate", None),
        "vendor_code": getattr(error, "errno", None),
    }


def loopback_port(ports: dict[str, Any], port: str) -> int:
    bindings = ports.get(port + "/tcp")
    if (
        not isinstance(bindings, list)
        or len(bindings) != 1
        or bindings[0].get("HostIp") != "127.0.0.1"
        or not str(bindings[0].get("HostPort", "")).isdigit()
        or not 1 <= int(bindings[0]["HostPort"]) <= 65535
        or any(value for key, value in ports.items() if key != port + "/tcp")
    ):
        raise ValueError("missing, non-loopback or ambiguous port binding")
    return int(bindings[0]["HostPort"])


class Resources:
    def __init__(self, target: str, pin: dict[str, Any], directory: Path):
        self.target, self.pin, self.directory = target, pin, directory
        self.nonce = uuid.uuid4().hex
        self.name = "pietto-p66-" + self.nonce
        self.network_name = self.name + "-network"
        self.network_id: str | None = None
        self.container_id: str | None = None
        self.manager: Any = None
        self.query: Any = None
        self.port = 0
        self.connect_attempts = 0
        self.startup_started = 0.0
        self._passwords = (secrets.token_hex(24), secrets.token_hex(24))
        self.events: list[dict[str, Any]] = []
        self.uncertain: list[str] = []
        self.private = directory / "private"
        self.private.mkdir(mode=0o700)
        self.docker_config = self.private / "docker-config"
        self.docker_config.mkdir(mode=0o700)
        self.ca_path = self.private / "mysql-ca.pem"
        self.ca_identity: dict[str, Any] | None = None
        self.cleanup_result: dict[str, Any] | None = None
        self.endpoint_observation: dict[str, str] | None = None

    def event(self, event_name: str, **data: object) -> None:
        value = {"event": event_name, **data}
        encoded = json.dumps(value, ensure_ascii=False)
        if any(password in encoded for password in self._passwords):
            raise ValueError("credential in resource journal")
        self.events.append(value)
        with (self.directory / "resources.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def docker(
        self, *args: str, timeout: float = 30, extra_env: dict[str, str] | None = None
    ) -> str:
        env = clean_environment() | (extra_env or {})
        result = subprocess.run(
            ["docker", "--config", str(self.docker_config), "--host", ENDPOINT, *args],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode:
            # Docker error output can include credentials or raw configuration.
            raise RuntimeError("Docker operation failed: " + args[0])
        if len(result.stdout.encode()) > 1024 * 1024:
            raise ValueError("Docker response limit exceeded")
        return result.stdout.strip()

    def inspect_resource(
        self, kind: str, reference: str, *, timeout: float = 30
    ) -> dict[str, Any]:
        if kind == "container":
            fields = '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"labels":{{json .Config.Labels}},"ports":{{json .NetworkSettings.Ports}},"mounts":{{json .Mounts}},"running":{{json .State.Running}},"status":{{json .State.Status}},"exit_code":{{json .State.ExitCode}},"oom_killed":{{json .State.OOMKilled}}}'
        else:
            fields = '{"id":{{json .Id}},"name":{{json .Name}},"labels":{{json .Labels}},"internal":{{json .Internal}},"driver":{{json .Driver}},"options":{{json .Options}}}'
        return json.loads(
            self.docker(kind, "inspect", reference, "--format", fields, timeout=timeout)
        )

    def owned(self, kind: str, value: dict[str, Any]) -> bool:
        expected = self.name if kind == "container" else self.network_name
        return (
            value.get("name", "").lstrip("/") == expected
            and value.get("labels", {}).get("pietto.phase66.invocation") == self.nonce
            and (kind != "container" or value.get("image") == self.pin["config_digest"])
        )

    def acquire(self) -> None:
        socket = Path("/var/run/docker.sock")
        if not socket.exists() or not stat.S_ISSOCK(socket.stat().st_mode):
            raise RuntimeError("explicit local Docker endpoint unavailable")
        server = json.loads(self.docker("version", "--format", "{{json .Server}}"))
        if (server.get("Os"), server.get("Arch")) != ("linux", "amd64"):
            raise ValueError("Docker platform mismatch; emulation is not allowed")
        self.endpoint_observation = {
            "endpoint": ENDPOINT,
            "version": server["Version"],
            "os": server["Os"],
            "architecture": server["Arch"],
        }
        self.event("endpoint_verified", **self.endpoint_observation)
        image = self.pin["repository"] + "@" + self.pin["platform_digest"]
        self.event("image_pull_start", image=image)
        self.docker(
            "image", "pull", "--quiet", "--platform", "linux/amd64", image, timeout=600
        )
        observed = json.loads(
            self.docker(
                "image",
                "inspect",
                image,
                "--format",
                '{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}}}',
            )
        )
        if observed != {
            "id": self.pin["config_digest"],
            "os": "linux",
            "architecture": "amd64",
        }:
            raise ValueError("immutable image config identity mismatch")
        self.event("image_verified", **observed)
        label = "pietto.phase66.invocation=" + self.nonce
        self.event("network_create_intent", name=self.network_name, nonce=self.nonce)
        self.uncertain.append("network")
        # Internal networks omit the gateway endpoint needed for published ports.
        self.network_id = self.docker(
            "network",
            "create",
            "--driver",
            "bridge",
            "--opt",
            "com.docker.network.bridge.gateway_mode_ipv4=nat",
            "--label",
            label,
            self.network_name,
        )
        self.event("network_acquired", id=self.network_id)
        network = self.inspect_resource("network", self.network_id)
        self.event("network_observed", observation=network)
        if (
            not self.owned("network", network)
            or network.get("internal") is not False
            or network.get("driver") != "bridge"
            or network.get("options", {}).get(
                "com.docker.network.bridge.gateway_mode_ipv4"
            )
            != "nat"
        ):
            raise ValueError("network identity mismatch")
        self.uncertain.remove("network")
        port = "5432" if self.target == "postgres" else "3306"
        credentials = (
            {
                "POSTGRES_USER": "pietto_manager",
                "POSTGRES_PASSWORD": self._passwords[0],
                "POSTGRES_DB": "phase66",
            }
            if self.target == "postgres"
            else {
                "MYSQL_ROOT_PASSWORD": self._passwords[0],
                "MYSQL_ROOT_HOST": "%",
                "MYSQL_DATABASE": "phase66",
            }
        )
        args = [
            "container",
            "create",
            "--platform",
            "linux/amd64",
            "--name",
            self.name,
            "--label",
            label,
            "--network",
            self.network_id,
            "--publish",
            "127.0.0.1::" + port,
            "--memory",
            "1g",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--no-healthcheck",
        ]
        data_path = (
            "/var/lib/postgresql" if self.target == "postgres" else "/var/lib/mysql"
        )
        args.extend(("--tmpfs", data_path + ":rw,size=536870912"))
        for key in credentials:
            args.extend(("--env", key))
        args.append(image)
        if self.target == "postgres":
            args.extend(
                ("postgres", "-c", "statement_timeout=10000", "-c", "timezone=UTC")
            )
        else:
            args.extend(
                (
                    "mysqld",
                    "--character-set-server=utf8mb4",
                    "--collation-server=utf8mb4_0900_bin",
                    "--sql-mode=" + MYSQL_MODE,
                    "--max-execution-time=10000",
                )
            )
        self.event(
            "container_create_intent",
            name=self.name,
            nonce=self.nonce,
            image_config=self.pin["config_digest"],
        )
        self.uncertain.append("container")
        self.container_id = self.docker(*args, extra_env=credentials)
        self.event("container_acquired", id=self.container_id)
        observed = self.inspect_resource("container", self.container_id)
        if not self.owned("container", observed) or any(
            m.get("Type") != "tmpfs" for m in observed["mounts"]
        ):
            raise ValueError("container identity or mount boundary mismatch")
        self.uncertain.remove("container")
        started = time.monotonic()
        self.startup_started = started
        self.docker("container", "start", self.container_id, timeout=20)
        observed = self.inspect_resource("container", self.container_id)
        self.event(
            "container_start_observed",
            id=self.container_id,
            running=observed["running"],
            ports=observed["ports"],
        )
        self.port = loopback_port(observed["ports"], port)
        self.event("container_started", id=self.container_id, port=self.port)
        for attempt, checkpoint in enumerate(CONNECT_CHECKPOINTS, 1):
            time.sleep(max(0, checkpoint - (time.monotonic() - started)))
            remaining = STARTUP_SECONDS - (time.monotonic() - started)
            if remaining <= 0:
                break
            self.event("connect_attempt", attempt=attempt)
            try:
                with deadline(min(10, remaining)):
                    if self.target == "mysql":
                        certificate = self.docker(
                            "container",
                            "exec",
                            self.container_id,
                            "cat",
                            "/var/lib/mysql/ca.pem",
                            timeout=min(10, remaining),
                        )
                        self.ca_path.write_text(certificate + "\n")
                        self.ca_identity = {
                            "container_id": self.container_id,
                            "image_config": self.pin["config_digest"],
                            "sha256": hashlib.sha256(
                                self.ca_path.read_bytes()
                            ).hexdigest(),
                        }
                        self.event("ca_extracted", identity=self.ca_identity)
                    self.manager = self.connect(query=False)
                self.event(
                    "ready", attempt=attempt, elapsed_seconds=time.monotonic() - started
                )
                return
            except Exception as error:
                self.event(
                    "connect_failed",
                    attempt=attempt,
                    failure=error_fact(error, "connect")
                    | {"message": self.without_secrets(str(error))},
                )
                try:
                    state = self.inspect_resource(
                        "container",
                        self.container_id,
                        timeout=min(
                            10,
                            max(0.001, STARTUP_SECONDS - (time.monotonic() - started)),
                        ),
                    )
                    self.event(
                        "connection_failure_server_state",
                        id=self.container_id,
                        state={
                            key: state[key]
                            for key in ("status", "running", "exit_code", "oom_killed")
                        },
                    )
                except Exception as secondary:
                    self.event(
                        "connection_failure_state_unavailable",
                        failure=error_fact(secondary, "inspect"),
                    )
        raise TimeoutError("startup/readiness exhausted after at most three attempts")

    def connect(self, *, query: bool) -> Any:
        if (
            self.connect_attempts >= MAX_CONNECT_ATTEMPTS
            or time.monotonic() - self.startup_started >= STARTUP_SECONDS
        ):
            raise TimeoutError("total connection/startup budget exhausted")
        self.connect_attempts += 1
        self.event(
            "connection_open_attempt",
            query_identity=query,
            ordinal=self.connect_attempts,
        )
        # This is a fresh explicit runner process, not shared application state.
        for key in tuple(os.environ):
            if key.startswith("PG") or key in {
                "DATABASE_URL",
                "MYSQL_PWD",
                "MYSQL_HOME",
                "SSLKEYLOGFILE",
            }:
                del os.environ[key]
        os.environ["PSYCOPG_IMPL"] = "binary"
        user = (
            "pietto_query"
            if query
            else ("pietto_manager" if self.target == "postgres" else "root")
        )
        password = self._passwords[int(query)]
        if self.target == "postgres":
            import psycopg
            import psycopg.pq

            if psycopg.pq.__impl__ != "binary":
                raise ValueError("wrong Psycopg implementation")
            return psycopg.connect(
                host="127.0.0.1",
                port=self.port,
                dbname="phase66",
                user=user,
                password=password,
                connect_timeout=10,
                cursor_factory=psycopg.RawCursor,
                autocommit=True,
                passfile="/dev/null",
                sslmode="disable",
                gssencmode="disable",
                options="-c client_encoding=UTF8 -c search_path=public -c statement_timeout=10000 -c timezone=UTC",
            )
        import mysql.connector

        connection = mysql.connector.connect(
            host="127.0.0.1",
            port=self.port,
            database="phase66",
            user=user,
            password=password,
            connection_timeout=10,
            read_timeout=20,
            write_timeout=10,
            use_pure=True,
            autocommit=True,
            charset="utf8mb4",
            collation="utf8mb4_0900_bin",
            ssl_ca=str(self.ca_path),
            ssl_verify_cert=True,
            ssl_verify_identity=False,
            tls_versions=list(MYSQL_TLS_VERSIONS),
            get_warnings=False,
            raise_on_warnings=False,
            consume_results=False,
        )
        if type(connection).__name__ != "MySQLConnection":
            raise ValueError("wrong MySQL implementation")
        return connection

    def role_statements(self) -> tuple[tuple[str, bool], ...]:
        password = self._passwords[1]
        if self.target == "postgres":
            return (
                (
                    f"CREATE ROLE pietto_query LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS",
                    True,
                ),
                ("REVOKE ALL ON DATABASE phase66 FROM PUBLIC", False),
                ("GRANT CONNECT ON DATABASE phase66 TO pietto_query", False),
                ("REVOKE CREATE ON SCHEMA public FROM PUBLIC", False),
                ("GRANT USAGE ON SCHEMA public TO pietto_query", False),
                ("GRANT SELECT ON ALL TABLES IN SCHEMA public TO pietto_query", False),
            )
        return (
            (f"CREATE USER 'pietto_query'@'%' IDENTIFIED BY '{password}'", True),
            ("GRANT SELECT ON phase66.* TO 'pietto_query'@'%'", False),
        )

    def cleanup(self) -> dict[str, Any]:
        started = time.monotonic()
        failures: list[dict[str, Any]] = []
        absent: dict[str, bool] = {}
        for name in ("query", "manager"):
            connection = getattr(self, name)
            if connection is not None:
                try:
                    session_id = (
                        getattr(getattr(connection, "info", None), "backend_pid", None)
                        if self.target == "postgres"
                        else getattr(connection, "connection_id", None)
                    )
                    with deadline(
                        min(5, CLEANUP_SECONDS - (time.monotonic() - started))
                    ):
                        connection.close()
                    self.event(
                        "connection_closed", identity=name, session_id=session_id
                    )
                except Exception as error:
                    failures.append(error_fact(error, name + ".close"))
        for kind in ("container", "network"):
            resource_id = getattr(self, kind + "_id")
            try:
                remaining = CLEANUP_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("cleanup deadline exhausted")
                if resource_id is None and kind in self.uncertain:
                    reference = self.name if kind == "container" else self.network_name
                    value = self.inspect_resource(
                        kind, reference, timeout=max(0.001, remaining)
                    )
                    if not self.owned(kind, value):
                        raise ValueError("ambiguous resource is not proven owned")
                    resource_id = value["id"]
                    setattr(self, kind + "_id", resource_id)
                    self.event(
                        "ambiguous_creation_recovered", kind=kind, id=resource_id
                    )
                if resource_id is None:
                    absent[kind] = kind not in self.uncertain
                    continue
                if not self.owned(
                    kind,
                    self.inspect_resource(
                        kind,
                        resource_id,
                        timeout=max(
                            0.001, CLEANUP_SECONDS - (time.monotonic() - started)
                        ),
                    ),
                ):
                    raise ValueError("refusing cleanup of foreign resource")
                if kind == "container":
                    try:
                        self.docker(
                            "container",
                            "stop",
                            "--time",
                            "5",
                            resource_id,
                            timeout=min(10, remaining),
                        )
                        self.event("container_stopped", id=resource_id)
                    except Exception as error:
                        failures.append(error_fact(error, "container.stop"))
                    self.docker(
                        "container",
                        "rm",
                        "--force",
                        "--volumes",
                        resource_id,
                        timeout=max(
                            0.001, CLEANUP_SECONDS - (time.monotonic() - started)
                        ),
                    )
                else:
                    self.docker(
                        "network",
                        "rm",
                        resource_id,
                        timeout=max(
                            0.001, CLEANUP_SECONDS - (time.monotonic() - started)
                        ),
                    )
                self.event(kind + "_removed", id=resource_id)
                args = (
                    ("container", "ls", "--all")
                    if kind == "container"
                    else ("network", "ls")
                )
                found = self.docker(
                    *args,
                    "--no-trunc",
                    "--filter",
                    "id=" + resource_id,
                    "--format",
                    "{{.ID}}",
                    timeout=max(0.001, CLEANUP_SECONDS - (time.monotonic() - started)),
                )
                absent[kind] = found == ""
                if not absent[kind]:
                    raise ValueError("owned resource still exists")
            except Exception as error:
                failures.append(error_fact(error, kind + ".cleanup"))
                absent[kind] = False
        if time.monotonic() - started > CLEANUP_SECONDS:
            failures.append(
                error_fact(TimeoutError("cleanup deadline exceeded"), "cleanup")
            )
        self.cleanup_result = {
            "status": "success" if not failures and all(absent.values()) else "failed",
            "absent": absent,
            "failures": failures,
            "elapsed_seconds": time.monotonic() - started,
            "container_id": self.container_id,
            "network_id": self.network_id,
            "image_cache_retained": self.pin["repository"]
            + "@"
            + self.pin["platform_digest"],
        }
        self.event("cleanup_complete", result=self.cleanup_result)
        return self.cleanup_result

    def without_secrets(self, text: str) -> str:
        for password in self._passwords:
            text = text.replace(password, "[REDACTED]")
        return text
