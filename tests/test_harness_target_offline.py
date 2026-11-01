"""The local-offline target profile keeps its cache, network and endpoint proof."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import _pietto_target_conformance_resources as resources

pytestmark = pytest.mark.ci_workload("general-runtime")
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


def journal():
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
    return events


def test_offline_evidence_accepts_only_its_complete_local_path():
    events = journal()
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


def test_unknown_offline_mode_is_refused_before_local_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("PIETTO_NATIVE_OFFLINE", "unknown")
    with pytest.raises(ValueError, match="invalid native offline mode"):
        resources.Resources("postgres", PINS["targets"]["postgres"], tmp_path)
    assert list(tmp_path.iterdir()) == []
