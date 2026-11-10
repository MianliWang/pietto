"""No-Docker positive and fail-closed checks for the external campaign package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent


def invoke(candidate: Path, wheel: Path, receipt: Path, relay: Path, report: Path, resources: Path, *, include_report: bool = True) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, "-I", str(HERE / "judge.py"), "--receipt", str(receipt), "--relay-log", str(relay), "--relay", str(HERE / "relay.py"), "--candidate", str(candidate), "--wheel", str(wheel), "--resources", str(resources)]
    if include_report:
        command += ["--report", str(report)]
    return subprocess.run(command, text=True, capture_output=True, check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    wheel = args.wheel.resolve()
    sys.path.insert(0, str(HERE))
    for path in (HERE / "relay.py", HERE / "judge.py", HERE / "campaign.py", HERE / "preflight.py"):
        ast.parse(path.read_text(encoding="utf-8"))
    relay_source = (HERE / "relay.py").read_text(encoding="utf-8")
    campaign = (HERE / "campaign.py").read_text(encoding="utf-8")
    assert "/dev/tcp/127.0.0.1/3306" in relay_source
    assert "MAX_CHILDREN = 16" in relay_source and "relay children did not close" in relay_source
    assert '"--network", "none"' in campaign and "native.campaign" in campaign and "native.check" in campaign and "resources.MYSQL_MODE" in campaign and "literal_none_deadline_window" in campaign and '"terminal_seconds": 5.0' in campaign
    sys.path.insert(0, str(candidate / "tests"))
    import test_harness_execution_api_mysql_native as fixture
    from campaign import ipc_worker
    ipc_source = next(value for value in ipc_worker.__code__.co_consts if isinstance(value, str) and "native_context" in value)
    ast.parse(ipc_source)
    report_value = fixture.report.__wrapped__()
    report_value["wheel_sha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
    report_value["identity"]["wheel_sha256"] = report_value["wheel_sha256"]
    rows = [[1, None], [1, None]]
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        receipt = directory / "receipt.json"
        relay = directory / "relay.jsonl"
        report = directory / "report.json"
        resources = directory / "resources.jsonl"
        report.write_text(json.dumps(report_value), encoding="utf-8")
        relay.write_text("\n".join(json.dumps(item) for item in ({"event": "listening"}, {"event": "accept", "number": 1}, {"event": "close", "number": 1, "up": 1, "down": 1, "returncode": 0}, {"event": "closed", "children": 1})) + "\n", encoding="utf-8")
        resource_values = (
            {"event": "preflight_bound"},
            {"event": "image_cached", "reference": "container-registry.oracle.com/mysql/community-server@sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be"},
            {"event": "image_verified", "reference": "container-registry.oracle.com/mysql/community-server@sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be", "os": "linux", "architecture": "amd64", "runtime_image_id": "sha256:" + "e" * 64, "descriptor_digest": "sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be"},
            {"event": "image_pin_bound", "config_digest": "sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867", "platform_digest": "sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be"},
            {"event": "container_create_intent", "name": "pietto-p77-maint-my-x", "nonce": "x", "label": "pietto.phase66.invocation=x", "image": "container-registry.oracle.com/mysql/community-server@sha256:7dcc4add9183664de3a214daf85a50c3ba6cccfd7534f700b6561bf5b41885be"},
            {"event": "container_acquired", "id": "cid", "name": "pietto-p77-maint-my-x", "nonce": "x", "label": "pietto.phase66.invocation=x"},
            {"event": "container_start_observed", "id": "cid", "image": "sha256:" + "e" * 64, "network_mode": "none", "networks": {}},
            {"event": "none_network_verified", "network_mode": "none", "raw_networks": {}, "routes": {"ipv4": "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\n", "ipv6": ""}},
            {"event": "tcp_ready", "host": "127.0.0.1", "port": 3306, "authenticated": True, "user_host": ["root@localhost", "root@%"]},
            {"event": "relay_closed", "children": 1},
            {"event": "container_removed", "id": "cid"},
            {"event": "cleanup_complete", "result": {"status": "success", "absent": {"container": True, "network": True}, "failures": []}},
        )
        resources.write_text("\n".join(json.dumps(value) for value in resource_values) + "\n", encoding="utf-8")
        value = {
            "binding": __import__("campaign").binding(candidate, wheel),
            "sources": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in ("campaign.py", "judge.py", "relay.py", "mysql.sh", "preflight.py")},
            "transport": {"profile": "mysql-none-exec-stdio-v1", "network": {"mode": "none", "attached": []}, "container_port": 3306, "relay_sha256": hashlib.sha256((HERE / "relay.py").read_bytes()).hexdigest(), "relay_command": "docker container exec -i /bin/bash -c fixed-3306-forward", "route_tables": {"default_ipv4": False, "default_ipv6": False}},
            "native_report": report_value,
            "ipc": {"rows": rows, "ipc_rows": rows, "schema": [["left_id", "int64", False], ["right_key", "int64", True]], "end": "COMPLETE", "batches": 2, "delivered_rows": 2},
        }
        receipt.write_text(json.dumps(value), encoding="utf-8")
        positive = invoke(candidate, wheel, receipt, relay, report, resources)
        assert positive.returncode == 0, positive.stderr
        classic = list(resource_values)
        classic[2] = dict(resource_values[2]) | {"descriptor_digest": None, "runtime_image_id": "sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867"}
        classic[6] = dict(resource_values[6]) | {"image": "sha256:c9570e7b94230d3717b88a334acaea49a4fe6b162f68a8f2927eaaf866b7f867"}
        resources.write_text("\n".join(json.dumps(item) for item in classic) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode == 0
        resources.write_text("\n".join(json.dumps(item) for item in resource_values) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources, include_report=False).returncode != 0
        report.write_text("{}", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        report.write_text(json.dumps(report_value), encoding="utf-8")
        value["binding"]["wheel_sha256"] = "0" * 64
        receipt.write_text(json.dumps(value), encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        value["binding"] = __import__("campaign").binding(candidate, wheel)
        value["ipc"]["end"] = "FAILED"
        receipt.write_text(json.dumps(value), encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        value["ipc"]["end"] = "COMPLETE"
        receipt.write_text(json.dumps(value), encoding="utf-8")
        resources.write_text("\n".join(json.dumps(item) for item in resource_values if item["event"] != "relay_closed") + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        resources.write_text("\n".join(json.dumps(item) for item in resource_values) + "\n", encoding="utf-8")
        bad_cleanup = list(resource_values)
        bad_cleanup[-1] = {"event": "cleanup_complete", "result": {"status": "failed", "absent": {"container": False, "network": True}, "failures": ["container"]}}
        resources.write_text("\n".join(json.dumps(item) for item in bad_cleanup) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        resources.write_text("\n".join(json.dumps(item) for item in resource_values) + "\n", encoding="utf-8")
        bad_pull = list(resource_values) + [{"event": "image_pull_start"}]
        resources.write_text("\n".join(json.dumps(item) for item in bad_pull) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        wrong_cached = list(resource_values)
        wrong_cached[1] = {"event": "image_cached", "reference": "wrong"}
        resources.write_text("\n".join(json.dumps(item) for item in wrong_cached) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        wrong_verified = list(resource_values)
        wrong_verified[2] = dict(resource_values[2]) | {"reference": "wrong"}
        resources.write_text("\n".join(json.dumps(item) for item in wrong_verified) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        wrong_intent = list(resource_values)
        wrong_intent[4] = dict(resource_values[4]) | {"image": "wrong"}
        resources.write_text("\n".join(json.dumps(item) for item in wrong_intent) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        bad_bridge = list(resource_values)
        bad_bridge[7] = {"event": "none_network_verified", "network_mode": "none", "raw_networks": {"bridge": {"IPAddress": "172.17.0.2"}}, "routes": resource_values[7]["routes"]}
        resources.write_text("\n".join(json.dumps(item) for item in bad_bridge) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        bad_v4 = list(resource_values)
        bad_v4[7] = {"event": "none_network_verified", "network_mode": "none", "raw_networks": {}, "routes": {"ipv4": "Iface Destination Gateway Flags RefCnt Use Metric Mask MTU Window IRTT\neth0 00000000 00000000 0001 0 0 0 00000000 0 0 0\n", "ipv6": ""}}
        resources.write_text("\n".join(json.dumps(item) for item in bad_v4) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        bad_v6 = list(resource_values)
        bad_v6[7] = {"event": "none_network_verified", "network_mode": "none", "raw_networks": {}, "routes": {"ipv4": resource_values[7]["routes"]["ipv4"], "ipv6": "00000000000000000000000000000000 00 00000000000000000000000000000000 00 00000000000000000000000000000000 00000000 00000000 00000000 00000001 lo\n"}}
        resources.write_text("\n".join(json.dumps(item) for item in bad_v6) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        bad_name = list(resource_values)
        bad_name[4] = {"event": "container_create_intent", "name": "foreign", "nonce": "x", "label": "pietto.phase66.invocation=x"}
        resources.write_text("\n".join(json.dumps(item) for item in bad_name) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        bad_tcp = list(resource_values)
        bad_tcp[8] = {"event": "tcp_ready", "host": "127.0.0.1", "port": 3306, "authenticated": False, "user_host": []}
        resources.write_text("\n".join(json.dumps(item) for item in bad_tcp) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        resources.write_text("\n".join(json.dumps(item) for item in resource_values) + "\n", encoding="utf-8")
        relay.write_text("\n".join(json.dumps(item) for item in ({"event": "listening"}, {"event": "accept", "number": 1}, {"event": "close", "number": 1, "up": 1, "down": 1, "returncode": 0})) + "\n", encoding="utf-8")
        assert invoke(candidate, wheel, receipt, relay, report, resources).returncode != 0
        assert invoke(candidate, wheel, receipt, relay, report, directory / "missing.jsonl").returncode != 0
        ipc_project = directory / "ipc-source"
        ipc_project.mkdir()
        for name in ("main.pietto", "pietto.toml", "contract.json"):
            (ipc_project / name).write_text(name, encoding="utf-8")
        try:
            ipc_worker(Path("/missing-python"), {"project": str(ipc_project), "password": "pw", "port": 1, "ca": "none", "recording": False}, {"PATH": "/usr/bin"}, directory, label="ipc-worker", failure="IPC_WORKER")
        except ValueError as error:
            assert str(error) == "IPC_WORKER"
        else:
            raise AssertionError("launch failure accepted")
        ipc_raw = json.loads((directory / "ipc-worker.json").read_text(encoding="utf-8"))
        assert ipc_raw["launch"] == "ERROR" and ipc_raw["returncode"] is None
        finite = ipc_worker(
            Path(sys.executable),
            {"project": str(ipc_project), "password": "pw", "port": 1, "ca": "none", "finite_selftest": True},
            {"PATH": os.environ.get("PATH", "/usr/bin"), "PYTHONNOUSERSITE": "1"},
            directory,
            label="finite-context",
            failure="FINITE_CONTEXT",
        )
        context = finite["native_context"]
        assert finite["terminal"] == "finite_selftest"
        assert context["native"]["count"] == 12 and len(context["native"]["calls"]) == 8
        assert context["context"]["count"] == 13 and context["context"]["first_shape"] == {"row_count": 1, "arities": [16]}
        assert context["context"]["shape_mismatches"] == [{"call": {"session_id": 1, "data_connection": 2, "control_connection": 3}, "shape": {"row_count": 2, "arities": [1, 1]}}]
        try:
            ipc_worker(
                Path(sys.executable),
                {"project": str(ipc_project), "password": "pw", "port": 1, "ca": "none", "finite_selftest": True, "finite_oversized": True},
                {"PATH": os.environ.get("PATH", "/usr/bin"), "PYTHONNOUSERSITE": "1"},
                directory,
                label="finite-oversized",
                failure="FINITE_OVERSIZED",
            )
        except ValueError as error:
            assert str(error) == "FINITE_OVERSIZED"
        else:
            raise AssertionError("oversized returned context accepted")
        oversized = json.loads((directory / "finite-oversized.json").read_text(encoding="utf-8"))
        assert oversized["record"]["terminal"] == "finite_error"
        assert oversized["record"]["native_context"]["context"]["truncated"] is True
        assert ipc_raw["inputs_unchanged"] is True and ipc_raw["stdout_bytes"] == 0
    print("mysql none campaign self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
