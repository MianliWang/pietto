"""Data-only judge for the MySQL literal-none relay profile."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(reason: str) -> None:
    raise ValueError(reason)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--relay-log", type=Path, required=True)
    parser.add_argument("--relay", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--resources", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    relay = [json.loads(line) for line in args.relay_log.read_text(encoding="utf-8").splitlines()]
    binding = receipt.get("binding")
    transport = receipt.get("transport")
    if not isinstance(binding, dict) or set(binding) != {"head", "patch_sha256", "pins_sha256", "lock_sha256", "wheel_sha256"}:
        fail("BINDING")
    if not all(isinstance(value, str) and len(value) == 64 for key, value in binding.items() if key != "head") or not isinstance(binding.get("head"), str):
        fail("BINDING_DIGEST")
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from campaign import binding as current_binding
    if binding != current_binding(args.candidate.resolve(), args.wheel.resolve()):
        fail("BINDING_DRIFT")
    sources = receipt.get("sources")
    expected_sources = {name: sha256(Path(__file__).resolve().parent / name) for name in ("campaign.py", "judge.py", "relay.py", "mysql.sh", "preflight.py")}
    if sources != expected_sources:
        fail("ADAPTER_SOURCES")
    if not isinstance(transport, dict):
        fail("TRANSPORT")
    if transport.get("profile") != "mysql-none-exec-stdio-v1":
        fail("PROFILE")
    if transport.get("network") != {"mode": "none", "attached": []}:
        fail("NETWORK")
    if transport.get("container_port") != 3306:
        fail("PORT")
    if transport.get("relay_sha256") != sha256(args.relay):
        fail("RELAY_IDENTITY")
    if transport.get("relay_command") != "docker container exec -i /bin/bash -c fixed-3306-forward":
        fail("COMMAND")
    if transport.get("route_tables", {}).get("default_ipv4") is not False or transport.get("route_tables", {}).get("default_ipv6") is not False:
        fail("ROUTES")
    events = [entry.get("event") for entry in relay]
    if not events or events[0] != "listening" or events[-1] != "closed":
        fail("RELAY_LIFECYCLE")
    accepts = [entry for entry in relay if entry.get("event") == "accept"]
    closes = [entry for entry in relay if entry.get("event") == "close"]
    if len(accepts) != len(closes):
        fail("RELAY_CHILDREN")
    if any(entry.get("up", 0) <= 0 or entry.get("down", 0) <= 0 or entry.get("returncode") != 0 for entry in closes):
        fail("RELAY_BYTES")
    report = json.loads(args.report.read_text(encoding="utf-8"))
    if receipt.get("native_report") != report or report.get("format") != "pietto.execution-api-mysql-native.v1" or report.get("status") != "PASS" or report.get("cleanup") != "PASS":
        fail("PUBLIC_REPORT")
    if report.get("identity", {}).get("drivers") != {"mysql-connector-python": "26.10.0", "pyarrow": "26.0.1"} or report.get("wheel_sha256") != binding["wheel_sha256"]:
        fail("PUBLIC_IDENTITY")
    sys.path.insert(0, str(args.candidate / "tests"))
    import _pietto_execution_api_mysql_native as native
    if native.check(report) != {"family": "mysql-native", "verdict": "ACCEPTED"}:
        fail("NATIVE_ORACLE")
    expected_rows = [[1, None], [1, None]]
    cases = report.get("cases", {})
    if cases.get("rows", {}).get("rows") != expected_rows or cases.get("bundle", {}).get("rows") != expected_rows or cases.get("empty", {}).get("rows") != [] or cases.get("schema", {}).get("schema") != [["left_id", "int64", False], ["right_key", "int64", True]]:
        fail("PUBLIC_CASES")
    ipc = receipt.get("ipc")
    if not isinstance(ipc, dict) or ipc.get("rows") != expected_rows or ipc.get("ipc_rows") != expected_rows or ipc.get("schema") != [["left_id", "int64", False], ["right_key", "int64", True]] or ipc.get("end") != "COMPLETE" or ipc.get("batches") != 2 or ipc.get("delivered_rows") != 2:
        fail("PUBLIC_IPC")
    resource_events = [json.loads(line) for line in args.resources.read_text(encoding="utf-8").splitlines()]
    names = [item.get("event") for item in resource_events]
    required = ("preflight_bound", "image_cached", "image_verified", "image_pin_bound", "container_create_intent", "container_acquired", "container_start_observed", "none_network_verified", "tcp_ready", "relay_closed", "container_removed", "cleanup_complete")
    if any(names.count(name) != 1 for name in required):
        fail("RESOURCE_LIFECYCLE")
    if [names.index(name) for name in required] != sorted(names.index(name) for name in required):
        fail("RESOURCE_ORDER")
    by_name = {item["event"]: item for item in resource_events}
    if any(name.startswith("image_pull") for name in names) or any(name in {"network_create_intent", "network_acquired", "network_observed", "network_removed"} for name in names):
        fail("PULL_OR_NETWORK")
    cached = by_name["image_cached"]
    image = by_name["image_verified"]
    pin = by_name["image_pin_bound"]
    created = by_name["container_create_intent"]
    acquired = by_name["container_acquired"]
    started = by_name["container_start_observed"]
    network = by_name["none_network_verified"]
    cleanup = by_name["cleanup_complete"].get("result")
    config_digest = "sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867"
    platform_digest = "sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be"
    image_ref = "container-registry.oracle.com/mysql/community-server@" + platform_digest
    if cached.get("reference") != image_ref or image.get("reference") != image_ref or created.get("image") != image_ref:
        fail("IMAGE_REFERENCE")
    descriptor = image.get("descriptor_digest")
    classic = descriptor is None and image.get("runtime_image_id") == config_digest
    descriptor_bound = descriptor == platform_digest and isinstance(image.get("runtime_image_id"), str) and image["runtime_image_id"].startswith("sha256:")
    if image.get("os") != "linux" or image.get("architecture") != "amd64" or not (classic or descriptor_bound) or pin.get("config_digest") != config_digest or pin.get("platform_digest") != platform_digest:
        fail("IMAGE_IDENTITY")
    name = created.get("name")
    nonce = created.get("nonce")
    label = created.get("label")
    if not isinstance(name, str) or not isinstance(nonce, str) or name != "pietto-p77-maint-my-" + nonce or label != "pietto.phase66.invocation=" + nonce or acquired.get("name") != name or acquired.get("nonce") != nonce or acquired.get("label") != label:
        fail("OWNERSHIP")
    if started.get("network_mode") != "none" or started.get("image") != image.get("runtime_image_id") or not isinstance(started.get("id"), str) or acquired.get("id") != started.get("id") or network.get("network_mode") != "none" or not isinstance(network.get("routes"), dict) or network.get("raw_networks") is None:
        fail("RESOURCE_IDENTITY")
    raw_networks = network["raw_networks"]
    if not isinstance(raw_networks, dict) or set(raw_networks) - {"none"}:
        fail("NETWORK_ATTACHMENT")
    if "none" in raw_networks:
        none = raw_networks["none"]
        if not isinstance(none, dict) or any(none.get(field) for field in ("IPAddress", "Gateway", "GlobalIPv6Address", "IPv6Gateway")):
            fail("NETWORK_ATTACHMENT")
    tcp_ready = by_name["tcp_ready"]
    if tcp_ready.get("host") != "127.0.0.1" or tcp_ready.get("port") != 3306 or tcp_ready.get("authenticated") is not True or not isinstance(tcp_ready.get("user_host"), list) or len(tcp_ready["user_host"]) != 2 or not all(isinstance(value, str) and value for value in tcp_ready["user_host"]):
        fail("TCP_READY")
    try:
        sys.path.insert(0, str(args.candidate / "tests"))
        import _pietto_target_conformance_resources as resource_reader
        resource_reader.verify_no_default_route(network["routes"].get("ipv4"), network["routes"].get("ipv6"))
    except Exception as error:
        raise ValueError("ROUTE_READER") from error
    if not isinstance(cleanup, dict) or cleanup.get("status") != "success" or cleanup.get("absent") != {"container": True, "network": True} or cleanup.get("failures") != []:
        fail("RESOURCE_CLEANUP")
    print(json.dumps({"profile": "mysql-none-exec-stdio-v1", "verdict": "ACCEPTED", "connections": len(accepts)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
