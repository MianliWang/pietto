"""The local-offline target profile keeps its cache, network and endpoint proof."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import socket
import threading
import time

import pytest

import _pietto_target_conformance_resources as resources

PINS = json.loads(Path(__file__).with_name("phase66_target_pins.json").read_text())
HEADER = "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT"
V4 = HEADER + "\neth0 000011AC 00000000 0001 0 0 0 0000FFFF 0 0 0"
V6 = (
    "0" * 32
    + " 00 "
    + "0" * 32
    + " 00 "
    + "0" * 32
    + " ffffffff 00000001 00000000 00200200 lo"
)


def journal(transport="bridge"):
    pin = PINS["targets"]["postgres"]
    cid, nid, name = "a" * 64, "b" * 64, "owned-network"
    reference = pin["repository"] + "@" + pin["platform_digest"]
    local = {"host": "127.0.0.1", "port": 23456}
    target = {"host": "172.17.0.2", "port": 5432}
    events = [
        {
            "event": "offline_requested",
            "cache_only": True,
            "bridge_tool": "/usr/bin/socat",
            "bridge_version": ["socat", "version"],
        },
        {"event": "image_cached", "reference": reference},
        {
            "event": "image_verified",
            "reference": reference,
            "contract": "classic",
            "runtime_image_id": pin["config_digest"],
            "descriptor_digest": None,
            "os": "linux",
            "architecture": "amd64",
        },
        {
            "event": "network_observed",
            "observation": {
                "id": nid,
                "name": name,
                "internal": True,
                "driver": "bridge",
                "options": {},
            },
        },
        {
            "event": "container_start_observed",
            "id": cid,
            "image": pin["config_digest"],
            "running": True,
            "ports": {"5432/tcp": None},
        },
        {
            "event": "offline_bridge_started",
            "container_id": cid,
            "network_id": nid,
            "endpoint": local,
            "target": target,
        },
        {
            "event": "offline_network_verified",
            "container_id": cid,
            "network_id": nid,
            "endpoint": target,
            "topology": {
                "mode": nid,
                "networks": {name: {"NetworkID": nid, "IPAddress": target["host"]}},
            },
            "ipv4_routes": V4,
            "ipv6_routes": V6,
        },
        {"event": "container_started", "id": cid, "port": local["port"]},
        {"event": "offline_bridge_closed", "endpoint": local},
        {
            "event": "cleanup_complete",
            "result": {
                "container_id": cid,
                "network_id": nid,
                "status": "success",
                "failures": [],
                "absent": {"container": True, "network": True},
            },
        },
    ]

    network_at = next(
        i for i, event in enumerate(events) if event["event"] == "network_observed"
    )
    events.insert(network_at, {"event": "network_acquired", "id": nid})
    container_at = next(
        i
        for i, event in enumerate(events)
        if event["event"] == "container_start_observed"
    )
    events.insert(container_at, {"event": "container_acquired", "id": cid})
    proof = next(
        event for event in events if event["event"] == "offline_network_verified"
    )
    proof["topology"]["cpus"] = "0-7"
    events[-1:-1] = [
        {"event": "container_removed", "id": cid},
        {"event": "network_removed", "id": nid},
    ]
    if transport == "exec-stdio":
        events[0] = {
            "event": "offline_requested",
            "cache_only": True,
            "transport": transport,
        }
        events.insert(
            0,
            {
                "event": "endpoint_verified",
                "endpoint": resources.ENDPOINT,
                "version": "29.8",
                "os": "linux",
                "architecture": "amd64",
            },
        )
        event = next(
            item for item in events if item["event"] == "offline_bridge_started"
        )
        event.clear()
        event.update(
            event="offline_exec_stdio_started",
            endpoint=local,
            docker_endpoint=resources.ENDPOINT,
            client="docker",
            command_sha256=resources.EXEC_STDIO_COMMAND_IDENTITY,
            target={"container_id": cid, "host": "127.0.0.1", "port": 5432},
            tty=False,
        )
        event = next(
            item for item in events if item["event"] == "offline_bridge_closed"
        )
        event.clear()
        event.update(
            event="offline_exec_stdio_closed",
            endpoint=local,
            target={"container_id": cid, "host": "127.0.0.1", "port": 5432},
            children_reaped=True,
        )
    return events


@pytest.mark.parametrize("transport", ["bridge", "exec-stdio"])
@pytest.mark.ci_workload("general-runtime")
def test_offline_evidence_accepts_only_its_complete_local_path(transport):
    events = journal(transport)
    assert resources.verify_offline_evidence(
        events, "postgres", PINS["targets"]["postgres"]
    )
    assert not resources.verify_offline_evidence(
        [], "postgres", PINS["targets"]["postgres"]
    )


@pytest.mark.parametrize(
    "damage",
    [
        "missing_request",
        "duplicate_proof",
        "pull",
        "nat",
        "network_id",
        "second_network",
        "public_endpoint",
        "different_target",
        "public_listener",
        "bridge_not_closed",
        "default_v4",
        "default_v6",
        "wrong_image",
        "cleanup_failed",
        "published_port",
        "order",
    ],
)
@pytest.mark.ci_workload("general-runtime")
def test_offline_evidence_rejects_each_broken_boundary(damage):
    events = journal()

    def event(name):
        return next(item for item in events if item["event"] == name)

    proof = event("offline_network_verified")
    if damage == "missing_request":
        events.pop(0)
    elif damage == "duplicate_proof":
        events.append(copy.deepcopy(proof))
    elif damage == "pull":
        events.append({"event": "image_pull_start"})
    elif damage == "nat":
        event("network_observed")["observation"].update(internal=False)
    elif damage == "network_id":
        proof["network_id"] = "c" * 64
    elif damage == "second_network":
        proof["topology"]["networks"]["foreign"] = {}
    elif damage == "public_endpoint":
        proof["topology"]["networks"]["owned-network"]["IPAddress"] = "8.8.8.8"
    elif damage == "different_target":
        event("offline_bridge_started")["target"] = {"host": "172.17.0.3", "port": 5432}
    elif damage == "public_listener":
        event("offline_bridge_started")["endpoint"] = {"host": "0.0.0.0", "port": 23456}
    elif damage == "bridge_not_closed":
        events.remove(event("offline_bridge_closed"))
    elif damage == "default_v4":
        proof["ipv4_routes"] += "\neth0 00000000 010011AC 0003 0 0 0 00000000 0 0 0"
    elif damage == "default_v6":
        proof["ipv6_routes"] = V6.replace("00200200", "00000003")
    elif damage == "wrong_image":
        event("container_start_observed")["image"] = "sha256:" + "0" * 64
    elif damage == "cleanup_failed":
        event("cleanup_complete")["result"]["failures"] = [{"stage": "bridge.close"}]
    elif damage == "published_port":
        event("container_start_observed")["ports"] = {
            "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "23456"}]
        }
    else:
        events[0], events[-1] = events[-1], events[0]
    with pytest.raises(ValueError):
        resources.verify_offline_evidence(
            events, "postgres", PINS["targets"]["postgres"]
        )


@pytest.mark.parametrize(
    "damage",
    [
        "mixed_bridge",
        "foreign_container",
        "command_drift",
        "published_port",
        "default_route",
        "close_error",
        "close_before_start",
        "missing_endpoint",
        "wrong_docker_endpoint",
        "foreign_endpoint",
        "malformed_endpoint",
        "obsolete_published_event",
    ],
)
@pytest.mark.ci_workload("general-runtime")
def test_exec_stdio_evidence_rejects_each_broken_boundary(damage):
    events = journal("exec-stdio")

    def event(name):
        return next(item for item in events if item["event"] == name)

    if damage == "mixed_bridge":
        events.append({"event": "offline_bridge_closed"})
    elif damage == "foreign_container":
        event("offline_exec_stdio_started")["target"]["container_id"] = "c" * 64
    elif damage == "command_drift":
        event("offline_exec_stdio_started")["command_sha256"] = "0" * 64
    elif damage == "published_port":
        event("container_start_observed")["ports"] = {
            "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "23456"}]
        }
    elif damage == "default_route":
        event("offline_network_verified")["ipv4_routes"] += (
            "\neth0 00000000 010011AC 0003 0 0 0 00000000 0 0 0"
        )
    elif damage == "close_error":
        event("cleanup_complete")["result"]["failures"] = [{"stage": "close"}]
    elif damage == "missing_endpoint":
        events.remove(event("endpoint_verified"))
    elif damage == "wrong_docker_endpoint":
        event("offline_exec_stdio_started")["docker_endpoint"] = "tcp://foreign"
    elif damage == "foreign_endpoint":
        event("endpoint_verified")["endpoint"] = "unix:///foreign.sock"
    elif damage == "malformed_endpoint":
        event("endpoint_verified")["version"] = ""
    elif damage == "obsolete_published_event":
        events.append({"event": "offline_published_loopback_observed"})
    else:
        closed = event("offline_exec_stdio_closed")
        events.remove(closed)
        events.insert(events.index(event("offline_exec_stdio_started")) + 1, closed)
    with pytest.raises(ValueError):
        resources.verify_offline_evidence(
            events, "postgres", PINS["targets"]["postgres"]
        )


@pytest.mark.ci_workload("general-runtime")
def test_offline_cache_miss_never_pulls(tmp_path, monkeypatch):
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE", "1")
    owned = resources.Resources("postgres", PINS["targets"]["postgres"], tmp_path)
    commands = []

    def docker(*args, **kwargs):
        commands.append(args)
        raise RuntimeError("Docker image inspect unknown or missing")

    monkeypatch.setattr(owned, "docker", docker)
    pin = owned.pin
    with pytest.raises(RuntimeError, match="offline image cache miss"):
        owned.acquire_image(pin["repository"] + "@" + pin["platform_digest"])
    assert [cmd[:2] for cmd in commands] == [("image", "inspect")]
    assert owned.events == []


@pytest.mark.ci_workload("general-runtime")
def test_unknown_offline_mode_is_refused_before_local_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE", "unknown")
    with pytest.raises(ValueError, match="invalid native offline mode"):
        resources.Resources("postgres", PINS["targets"]["postgres"], tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("offline", "transport", "target", "message"),
    [
        ("1", "unknown", "postgres", "invalid native offline transport"),
        ("1", "published-loopback", "postgres", "invalid native offline transport"),
        ("0", "exec-stdio", "postgres", "requires offline mode"),
        ("1", "exec-stdio", "mysql", "requires postgres"),
    ],
)
@pytest.mark.ci_workload("general-runtime")
def test_invalid_offline_transport_is_refused_before_local_creation(
    tmp_path, monkeypatch, offline, transport, target, message
):
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE", offline)
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE_TRANSPORT", transport)
    with pytest.raises(ValueError, match=message):
        resources.Resources(target, PINS["targets"][target], tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.ci_workload("general-runtime")
def test_exec_stdio_command_is_fixed_and_owned(tmp_path, monkeypatch):
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE", "1")
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE_TRANSPORT", "exec-stdio")
    owned = resources.Resources("postgres", PINS["targets"]["postgres"], tmp_path)
    owned.container_id = "a" * 64
    owned.runtime_image_id = PINS["targets"]["postgres"]["config_digest"]
    monkeypatch.setattr(
        owned,
        "inspect_resource",
        lambda kind, identifier: {
            "name": "/" + owned.name,
            "labels": {"pietto.phase66.invocation": owned.nonce},
            "image": owned.runtime_image_id,
            "running": True,
        },
    )
    command = owned.exec_stdio_command()
    assert command[:7] == (
        "docker",
        "--config",
        str(owned.docker_config),
        "--host",
        resources.ENDPOINT,
        "container",
        "exec",
    )
    assert command[7:] == (
        "-i",
        owned.container_id,
        "/bin/bash",
        "-c",
        resources.EXEC_STDIO_SCRIPT,
    )
    assert "-t" not in command
    assert all(password not in command for password in owned._passwords)
    assert resources.EXEC_STDIO_SCRIPT.index(
        "trap "
    ) < resources.EXEC_STDIO_SCRIPT.index("wait -n")


def test_exec_stdio_bridge_preserves_binary_bytes_and_reaps_children(monkeypatch):
    children = []

    class Child:
        def __init__(self, stdin, stdout):
            self.done = False
            self.read_fd, self.write_fd = os.dup(stdin), os.dup(stdout)
            self.thread = threading.Thread(target=self.forward, daemon=True)
            self.thread.start()

        def forward(self):
            try:
                value = os.read(self.read_fd, 3)
                os.write(self.write_fd, value)
            finally:
                os.close(self.read_fd)
                os.close(self.write_fd)
                self.done = True

        def poll(self):
            return 0 if self.done else None

        def terminate(self):
            self.done = True

        def kill(self):
            self.done = True

        def wait(self, timeout):
            self.thread.join(timeout)
            return 0

    def popen(command, *, stdin, stdout, stderr, env):
        assert command == ("docker", "fixed")
        assert stderr is resources.subprocess.DEVNULL
        assert env["PYTHONNOUSERSITE"] == "1"
        child = Child(stdin, stdout)
        children.append(child)
        return child

    monkeypatch.setattr(resources.subprocess, "Popen", popen)
    bridge = resources._LoopbackBridge(("docker", "fixed"))
    with socket.create_connection(("127.0.0.1", bridge.port), timeout=1) as client:
        client.sendall(b"\x00\xffx")
        assert client.recv(3) == b"\x00\xffx"
    end = time.monotonic() + 1
    while not children and time.monotonic() < end:
        time.sleep(0.01)
    bridge.close()
    assert children and all(child.poll() is not None for child in children)
