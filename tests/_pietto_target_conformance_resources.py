"""Explicit, bounded ownership of one local Docker test instance."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from ipaddress import IPv4Address
import json
import os
from pathlib import Path
import re
import secrets
import signal
import shutil
import socket
import threading
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
# "index" tolerates the key that only a descriptor-aware image store exposes.
IMAGE_FIELDS = (
    '{"id":{{json .Id}},"os":{{json .Os}},"architecture":{{json .Architecture}}'
    ',"descriptor":{{json (index . "Descriptor")}}}'
)
DIGEST = re.compile(r"sha256:[0-9a-f]{64}")
MYSQL_TLS_VERSIONS = ("TLSv1.2", "TLSv1.3")
EXEC_STDIO_SCRIPT = """exec 3<>/dev/tcp/127.0.0.1/5432
cat <&0 >&3 &
to_server=$!
cat <&3 >&1 &
from_server=$!
trap 'kill "$to_server" "$from_server" 2>/dev/null || true; wait "$to_server" "$from_server" 2>/dev/null || true' EXIT
wait -n "$to_server" "$from_server" || true
"""
EXEC_STDIO_COMMAND_IDENTITY = hashlib.sha256(
    b"docker\0--config\0<owned-private-config>\0--host\0unix:///var/run/docker.sock"
    b"\0container\0exec\0-i\0<owned-container>\0/bin/bash\0-c\0"
    + EXEC_STDIO_SCRIPT.encode()
).hexdigest()


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
            "OPENSSL_CONF",
            "OPENSSL_MODULES",
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


def verify_no_default_route(ipv4: object, ipv6: object) -> None:
    """Parse bounded kernel route tables; reject an active default route."""
    if type(ipv4) is not str or type(ipv6) is not str:
        raise ValueError("offline route observation type")
    lines = ipv4.splitlines()
    if (
        not lines
        or lines[0].split()
        != [
            "Iface",
            "Destination",
            "Gateway",
            "Flags",
            "RefCnt",
            "Use",
            "Metric",
            "Mask",
            "MTU",
            "Window",
            "IRTT",
        ]
        or len(lines) > 256
        or len(ipv6.splitlines()) > 256
    ):
        raise ValueError("offline route observation shape")
    for line in lines[1:]:
        fields = line.split()
        if len(fields) != 11 or any(
            re.fullmatch(r"[0-9A-Fa-f]{1,8}", fields[i]) is None for i in (1, 2, 3, 7)
        ):
            raise ValueError("offline IPv4 route shape")
        flags = int(fields[3], 16)
        if (
            int(fields[1], 16) == int(fields[7], 16) == 0
            and flags & 1
            and not flags & 0x200
        ):
            raise ValueError("offline IPv4 default route")
    for line in ipv6.splitlines():
        fields = line.split()
        if (
            len(fields) != 10
            or any(
                re.fullmatch(r"[0-9a-fA-F]{32}", fields[i]) is None for i in (0, 2, 4)
            )
            or any(re.fullmatch(r"[0-9a-fA-F]{2}", fields[i]) is None for i in (1, 3))
            or any(
                re.fullmatch(r"[0-9a-fA-F]{8}", fields[i]) is None for i in (5, 6, 7, 8)
            )
        ):
            raise ValueError("offline IPv6 route shape")
        if int(fields[1], 16) > 128 or int(fields[3], 16) > 128:
            raise ValueError("offline IPv6 prefix length")
        flags = int(fields[8], 16)
        if (
            int(fields[0], 16) == int(fields[1], 16) == 0
            and flags & 1
            and not flags & 0x200
        ):
            raise ValueError("offline IPv6 default route")


def image_identity(observed: dict[str, Any], pin: dict[str, Any]) -> dict[str, Any]:
    """Select the identity contract the active Docker image store actually exposes.

    A descriptor-aware store exposes the pinned platform manifest directly and
    reports a storage-specific runtime object ID; the historical store exposes the
    pinned config identity as that ID. Each route verifies its own exposed digest,
    so a matching ID never rescues a wrong descriptor and neither route is a
    fallback for the other.
    """
    identifier, descriptor = observed.get("id"), observed.get("descriptor")
    if (
        set(observed) != {"id", "os", "architecture", "descriptor"}
        or type(identifier) is not str
        or DIGEST.fullmatch(identifier) is None
        or (observed["os"], observed["architecture"]) != ("linux", "amd64")
    ):
        raise ValueError("incomplete or non-amd64 image observation")
    if descriptor is None:
        if identifier != pin["config_digest"]:
            raise ValueError("historical image config identity mismatch")
        contract, digest = "classic", None
    elif type(descriptor) is dict and DIGEST.fullmatch(str(descriptor.get("digest"))):
        contract, digest = "descriptor", descriptor["digest"]
        platform = descriptor.get("platform")
        if digest != pin["platform_digest"]:
            raise ValueError("descriptor platform manifest identity mismatch")
        if platform is not None and (
            type(platform) is not dict
            or (platform.get("os"), platform.get("architecture")) != ("linux", "amd64")
        ):
            raise ValueError("descriptor platform disagreement")
    else:
        raise ValueError("unrecognized Docker image observation shape")
    return {
        "contract": contract,
        "runtime_image_id": identifier,
        "descriptor_digest": digest,
        "os": "linux",
        "architecture": "amd64",
    }


def verify_offline_evidence(events: Any, target: str, pin: dict[str, Any]) -> bool:
    """Independently bind an optional local-offline journal to owned resources."""
    if type(events) is not list or any(type(event) is not dict for event in events):
        raise ValueError("offline event collection")
    requested = [event for event in events if event.get("event") == "offline_requested"]
    if not requested:
        if any(event.get("event", "").startswith("offline_") for event in events):
            raise ValueError("offline request missing")
        return False

    def one(name: str) -> dict[str, Any]:
        found = [event for event in events if event.get("event") == name]
        if len(found) != 1:
            raise ValueError("offline event inventory: " + name)
        return found[0]

    request = one("offline_requested")
    transport = request.get("transport", "bridge")
    if transport not in ("bridge", "exec-stdio"):
        raise ValueError("offline transport")
    known_offline_events = {
        "offline_requested",
        "offline_network_verified",
        "offline_bridge_started",
        "offline_bridge_closed",
        "offline_exec_stdio_started",
        "offline_exec_stdio_closed",
    }
    if any(
        event.get("event", "").startswith("offline_")
        and event.get("event") not in known_offline_events
        for event in events
    ):
        raise ValueError("unknown offline transport evidence")
    network = one("network_observed")["observation"]
    start = one("container_start_observed")
    proof = one("offline_network_verified")
    cleanup = one("cleanup_complete")["result"]
    cached, image = one("image_cached"), one("image_verified")
    reference = pin["repository"] + "@" + pin["platform_digest"]
    if (
        request.get("cache_only") is not True
        or any(
            event.get("event") in ("image_pull_start", "image_pulled")
            for event in events
        )
        or cached.get("reference") != reference
        or image.get("reference") != reference
    ):
        raise ValueError("offline cache/image evidence")
    if transport == "bridge":
        if (
            not Path(request.get("bridge_tool", "")).is_absolute()
            or type(request.get("bridge_version")) is not list
            or not request["bridge_version"]
            or any(
                type(value) is not str or not value
                for value in request["bridge_version"]
            )
            or any(
                event.get("event")
                in ("offline_exec_stdio_started", "offline_exec_stdio_closed")
                for event in events
            )
        ):
            raise ValueError("offline bridge evidence")
    elif (
        set(request) != {"event", "cache_only", "transport"}
        or target != "postgres"
        or any(
            event.get("event") in ("offline_bridge_started", "offline_bridge_closed")
            for event in events
        )
    ):
        raise ValueError("offline exec-stdio evidence")
    if transport == "exec-stdio":
        endpoint_observation = one("endpoint_verified")
        if (
            set(endpoint_observation)
            != {"event", "endpoint", "version", "os", "architecture"}
            or endpoint_observation.get("endpoint") != ENDPOINT
            or endpoint_observation.get("os") != "linux"
            or endpoint_observation.get("architecture") != "amd64"
            or type(endpoint_observation.get("version")) is not str
            or not endpoint_observation["version"]
        ):
            raise ValueError("offline exec-stdio endpoint identity")
    observed = {
        "id": image.get("runtime_image_id"),
        "os": image.get("os"),
        "architecture": image.get("architecture"),
        "descriptor": None
        if image.get("contract") == "classic"
        else {"digest": image.get("descriptor_digest")},
    }
    identity = image_identity(observed, pin)
    if (
        image.get("contract") != identity["contract"]
        or image.get("descriptor_digest") != identity["descriptor_digest"]
    ):
        raise ValueError("offline image identity")
    nid, cid = cleanup.get("network_id"), cleanup.get("container_id")
    if any(
        type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in (nid, cid)
    ):
        raise ValueError("offline resource identifiers")
    for kind, identifier in (("network", nid), ("container", cid)):
        acquired, removed = one(kind + "_acquired"), one(kind + "_removed")
        if (
            acquired.get("id") != identifier
            or removed.get("id") != identifier
            or events.index(acquired) >= events.index(removed)
            or events.index(removed) >= events.index(one("cleanup_complete"))
        ):
            raise ValueError("offline owned resource lifecycle")
    topology = proof.get("topology", {})
    networks = topology.get("networks", {})
    if (
        network.get("id") != nid
        or network.get("internal") is not True
        or network.get("driver") != "bridge"
        or network.get("options", {}).get("com.docker.network.bridge.gateway_mode_ipv4")
        is not None
        or proof.get("network_id") != nid
        or proof.get("container_id") != cid
        or topology.get("mode") != nid
        or topology.get("cpus") != "0-7"
        or set(networks) != {network.get("name")}
        or networks[network["name"]].get("NetworkID") != nid
        or start.get("id") != cid
        or start.get("image") != identity["runtime_image_id"]
        or start.get("running") is not True
        or any(start.get("ports", {}).values())
        or cleanup.get("status") != "success"
        or cleanup.get("failures") != []
        or cleanup.get("absent") != {"container": True, "network": True}
    ):
        raise ValueError("offline network identity")
    endpoint = proof.get("endpoint", {})
    ip = IPv4Address(networks[network["name"]].get("IPAddress"))
    if (
        not ip.is_private
        or ip.is_loopback
        or ip.is_unspecified
        or ip.is_multicast
        or endpoint != {"host": str(ip), "port": 5432 if target == "postgres" else 3306}
    ):
        raise ValueError("offline endpoint identity")
    started = one("container_started")
    if transport == "bridge":
        bridge, closed = one("offline_bridge_started"), one("offline_bridge_closed")
        local = bridge.get("endpoint", {})
        if (
            bridge.get("target") != endpoint
            or bridge.get("container_id") != cid
            or bridge.get("network_id") != nid
            or local.get("host") != "127.0.0.1"
            or type(local.get("port")) is not int
            or not 0 < local["port"] < 65536
            or closed.get("endpoint") != local
            or started.get("id") != cid
            or started.get("port") != local["port"]
            or events.index(closed) >= events.index(one("container_removed"))
        ):
            raise ValueError("offline bridge loopback identity")
        lifecycle = (
            "offline_requested",
            "image_cached",
            "image_verified",
            "network_acquired",
            "network_observed",
            "container_acquired",
            "container_start_observed",
            "offline_bridge_started",
            "offline_network_verified",
            "container_started",
            "offline_bridge_closed",
            "container_removed",
            "network_removed",
            "cleanup_complete",
        )
    else:
        bridge, closed = (
            one("offline_exec_stdio_started"),
            one("offline_exec_stdio_closed"),
        )
        local = bridge.get("endpoint", {})
        target_fact = {"container_id": cid, "host": "127.0.0.1", "port": 5432}
        if (
            bridge.get("docker_endpoint") != ENDPOINT
            or bridge.get("client") != "docker"
            or bridge.get("target") != target_fact
            or bridge.get("command_sha256") != EXEC_STDIO_COMMAND_IDENTITY
            or bridge.get("tty") is not False
            or local.get("host") != "127.0.0.1"
            or type(local.get("port")) is not int
            or not 0 < local["port"] < 65536
            or closed.get("endpoint") != local
            or closed.get("target") != target_fact
            or closed.get("children_reaped") is not True
            or started.get("id") != cid
            or started.get("port") != local["port"]
            or events.index(closed) >= events.index(one("container_removed"))
        ):
            raise ValueError("offline exec-stdio identity")
        lifecycle = (
            "endpoint_verified",
            "offline_requested",
            "image_cached",
            "image_verified",
            "network_acquired",
            "network_observed",
            "container_acquired",
            "container_start_observed",
            "offline_exec_stdio_started",
            "offline_network_verified",
            "container_started",
            "offline_exec_stdio_closed",
            "container_removed",
            "network_removed",
            "cleanup_complete",
        )
    verify_no_default_route(proof.get("ipv4_routes"), proof.get("ipv6_routes"))
    order = [events.index(one(name)) for name in lifecycle]
    if order != sorted(set(order)):
        raise ValueError("offline lifecycle order")
    return True


class _LoopbackBridge:
    """Owned host-local transport into an isolated container, without TLS termination."""

    def __init__(self, command: tuple[str, ...]):
        self.listener = socket.create_server(("127.0.0.1", 0))
        self.listener.settimeout(0.2)
        self.port = self.listener.getsockname()[1]
        self.command = command
        self.stop = threading.Event()
        self.children: list[subprocess.Popen] = []
        self.failure: BaseException | None = None
        self.thread = threading.Thread(
            target=self.serve, daemon=True, name="pietto-offline-bridge"
        )
        self.thread.start()

    def serve(self):
        try:
            while not self.stop.is_set():
                try:
                    client, _address = self.listener.accept()
                except TimeoutError:
                    continue
                with client:
                    if self.stop.is_set():
                        break
                    self.children = [
                        child for child in self.children if child.poll() is None
                    ]
                    if len(self.children) >= 16:
                        continue
                    self.children.append(
                        subprocess.Popen(
                            self.command,
                            stdin=client.fileno(),
                            stdout=client.fileno(),
                            stderr=subprocess.DEVNULL,
                            env=clean_environment(),
                        )
                    )
        except BaseException as error:
            if not self.stop.is_set():
                self.failure = error

    def close(self):
        self.stop.set()
        self.listener.close()
        self.thread.join(2)
        if self.thread.is_alive():
            raise TimeoutError("offline bridge thread did not stop")
        for child in self.children:
            if child.poll() is None:
                child.terminate()
        end = time.monotonic() + 5
        for child in self.children:
            try:
                child.wait(timeout=max(0.001, end - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=1)
        if self.failure is not None:
            raise RuntimeError("offline bridge failed") from None


class Resources:
    def __init__(self, target: str, pin: dict[str, Any], directory: Path):
        mode = os.environ.get("PIETTO_NATIVE_OFFLINE", "0")
        if mode not in ("0", "1"):
            raise ValueError("invalid native offline mode")
        self.offline = mode == "1"
        transport = os.environ.get("PIETTO_NATIVE_OFFLINE_TRANSPORT")
        if transport not in (None, "exec-stdio"):
            raise ValueError("invalid native offline transport")
        if transport is not None and not self.offline:
            raise ValueError("native offline transport requires offline mode")
        if transport == "exec-stdio" and target != "postgres":
            raise ValueError("exec-stdio transport requires postgres")
        self.offline_transport = transport or "bridge"
        self.target, self.pin, self.directory = target, pin, directory
        self.nonce = uuid.uuid4().hex
        self.name = "pietto-p66-" + self.nonce
        self.network_name = self.name + "-network"
        self.network_id: str | None = None
        self.container_id: str | None = None
        self.manager: Any = None
        self.query: Any = None
        self.host = "127.0.0.1"
        self.port = 0
        self._bridge: _LoopbackBridge | None = None
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
        self.runtime_image_id: str | None = None

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
            if args[:2] == ("image", "inspect") and any(
                marker in str(getattr(result, "stderr", "")).lower()
                for marker in ("no such image", "not found")
            ):
                raise RuntimeError("Docker image inspect unknown or missing")
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

    def measurement_container_observation(
        self, *, timeout: float = 10
    ) -> dict[str, Any]:
        """Read the current owned container identity for an explicit measurement.

        The caller still has to prove ownership before it uses this observation.
        This method deliberately has no lifecycle effect and is not called by
        ordinary target setup or execution.
        """
        if self.container_id is None:
            raise ValueError("measurement requires an acquired container")
        fields = (
            '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},'
            '"labels":{{json .Config.Labels}},"running":{{json .State.Running}},'
            '"pid":{{json .State.Pid}},"started_at":{{json .State.StartedAt}}}'
        )
        return json.loads(
            self.docker(
                "container",
                "inspect",
                self.container_id,
                "--format",
                fields,
                timeout=timeout,
            )
        )

    def owned(self, kind: str, value: dict[str, Any]) -> bool:
        expected = self.name if kind == "container" else self.network_name
        return (
            value.get("name", "").lstrip("/") == expected
            and value.get("labels", {}).get("pietto.phase66.invocation") == self.nonce
            and (
                kind != "container"
                or (
                    self.runtime_image_id is not None
                    and value.get("image") == self.runtime_image_id
                )
            )
        )

    def acquire_image(self, image: str) -> None:
        """Use a locally cached immutable image only after its full identity
        contract verifies.  A known missing cache entry alone permits a pull."""
        try:
            observed = json.loads(
                self.docker("image", "inspect", image, "--format", IMAGE_FIELDS)
            )
        except RuntimeError as error:
            if str(error) != "Docker image inspect unknown or missing":
                raise
            if self.offline:
                raise RuntimeError("offline image cache miss") from None
            self.event("image_pull_start", image=image)
            self.docker(
                "image",
                "pull",
                "--quiet",
                "--platform",
                "linux/amd64",
                image,
                timeout=600,
            )
            observed = json.loads(
                self.docker("image", "inspect", image, "--format", IMAGE_FIELDS)
            )
            source = "pulled"
        else:
            source = "cached"
        identity = image_identity(observed, self.pin)
        self.runtime_image_id = identity["runtime_image_id"]
        self.event("image_" + source, reference=image)
        self.event("image_verified", reference=image, **identity)

    def exec_stdio_command(self) -> tuple[str, ...]:
        if self.container_id is None:
            raise ValueError("exec-stdio requires an acquired container")
        observed = self.inspect_resource("container", self.container_id)
        if not self.owned("container", observed) or observed.get("running") is not True:
            raise ValueError("exec-stdio container identity mismatch")
        return (
            "docker",
            "--config",
            str(self.docker_config),
            "--host",
            ENDPOINT,
            "container",
            "exec",
            "-i",
            self.container_id,
            "/bin/bash",
            "-c",
            EXEC_STDIO_SCRIPT,
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
        program = None
        if self.offline:
            if self.offline_transport == "bridge":
                program = shutil.which("socat")
                if program is None:
                    raise RuntimeError(
                        "offline mode requires the installed socat host tool"
                    )
                version = subprocess.run(
                    [program, "-V"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=5,
                ).stdout.splitlines()[:2]
                self.event(
                    "offline_requested",
                    cache_only=True,
                    transport="bridge",
                    bridge_tool=program,
                    bridge_version=version,
                )
            else:
                self.event("offline_requested", cache_only=True, transport="exec-stdio")
        self.acquire_image(image)
        label = "pietto.phase66.invocation=" + self.nonce
        self.event("network_create_intent", name=self.network_name, nonce=self.nonce)
        self.uncertain.append("network")
        options = (
            ("--internal",)
            if self.offline
            else ("--opt", "com.docker.network.bridge.gateway_mode_ipv4=nat")
        )
        self.network_id = self.docker(
            "network",
            "create",
            "--driver",
            "bridge",
            *options,
            "--label",
            label,
            self.network_name,
        )
        self.event("network_acquired", id=self.network_id)
        network = self.inspect_resource("network", self.network_id)
        self.event("network_observed", observation=network)
        if (
            not self.owned("network", network)
            or network.get("internal") is not self.offline
            or network.get("driver") != "bridge"
            or network.get("options", {}).get(
                "com.docker.network.bridge.gateway_mode_ipv4"
            )
            != (None if self.offline else "nat")
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
            *(("--publish", "127.0.0.1::" + port) if not self.offline else ()),
            "--memory",
            "1g",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--no-healthcheck",
        ]
        if self.offline:
            args[2:2] = ["--pull=never", "--cpuset-cpus", "0-7"]
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
            reference=image,
            runtime_image_id=self.runtime_image_id,
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
            image=observed["image"],
            running=observed["running"],
            ports=observed["ports"],
        )
        if self.offline:
            topology = json.loads(
                self.docker(
                    "container",
                    "inspect",
                    self.container_id,
                    "--format",
                    '{"mode":{{json .HostConfig.NetworkMode}},"networks":{{json .NetworkSettings.Networks}},"cpus":{{json .HostConfig.CpusetCpus}}}',
                )
            )
            if (
                topology.get("mode") != self.network_id
                or topology.get("cpus") != "0-7"
                or set(topology.get("networks", {})) != {self.network_name}
                or topology["networks"][self.network_name].get("NetworkID")
                != self.network_id
            ):
                raise ValueError("offline network membership mismatch")
            ipv4 = self.docker(
                "container", "exec", self.container_id, "cat", "/proc/net/route"
            )
            ipv6 = self.docker(
                "container", "exec", self.container_id, "cat", "/proc/net/ipv6_route"
            )
            verify_no_default_route(ipv4, ipv6)
            address = topology["networks"][self.network_name].get("IPAddress")
            ip = IPv4Address(address)
            if (
                not ip.is_private
                or ip.is_loopback
                or ip.is_unspecified
                or ip.is_multicast
            ):
                raise ValueError("offline owned endpoint mismatch")
            target_host, target_port = str(ip), int(port)
            if self.offline_transport == "bridge":
                if program is None:
                    raise RuntimeError("offline bridge tool missing")
                self._bridge = _LoopbackBridge(
                    (
                        program,
                        "STDIO",
                        f"TCP4:{target_host}:{target_port},connect-timeout=5",
                    )
                )
                self.host, self.port = "127.0.0.1", self._bridge.port
                self.event(
                    "offline_bridge_started",
                    endpoint={"host": self.host, "port": self.port},
                    target={"host": target_host, "port": target_port},
                    container_id=self.container_id,
                    network_id=self.network_id,
                )
            else:
                self._bridge = _LoopbackBridge(self.exec_stdio_command())
                self.host, self.port = "127.0.0.1", self._bridge.port
                self.event(
                    "offline_exec_stdio_started",
                    endpoint={"host": self.host, "port": self.port},
                    docker_endpoint=ENDPOINT,
                    client="docker",
                    command_sha256=EXEC_STDIO_COMMAND_IDENTITY,
                    target={
                        "container_id": self.container_id,
                        "host": "127.0.0.1",
                        "port": 5432,
                    },
                    tty=False,
                )
            self.event(
                "offline_network_verified",
                container_id=self.container_id,
                network_id=self.network_id,
                topology=topology,
                ipv4_routes=ipv4,
                ipv6_routes=ipv6,
                endpoint={"host": target_host, "port": target_port},
            )
        else:
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
                host=self.host,
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
            host=self.host,
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
        if self._bridge is not None:
            try:
                self._bridge.close()
                if self.offline_transport == "exec-stdio":
                    self.event(
                        "offline_exec_stdio_closed",
                        endpoint={"host": self.host, "port": self.port},
                        target={
                            "container_id": self.container_id,
                            "host": "127.0.0.1",
                            "port": 5432,
                        },
                        children_reaped=True,
                    )
                else:
                    self.event(
                        "offline_bridge_closed",
                        endpoint={"host": self.host, "port": self.port},
                    )
            except Exception as error:
                failures.append(error_fact(error, "offline_transport.close"))
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
