"""R3 data-only judge. It refuses incomplete records and invented success."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
IMAGE = "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e"
WHEEL = "f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73"
BASE = "f8ccd2c44a2d9adf431a496bd9bbae037783176f"
PATCH = "548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc"
LOCK = "b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064"
VERSIONS = {
    "pietto": "0.1.10",
    "pyarrow": "26.0.1",
    "psycopg": "3.3.8",
    "psycopg-binary": "3.3.8",
    "adbc-driver-postgresql": "1.13.0",
    "adbc-driver-manager": "1.13.0",
}
INPUTS = {
    "PREREG.md", "ERRATUM.md", "client.py", "raw_driver_child.py", "judge.py", "pg.sh",
    "receipt.py", "relay.py", "gen-tls.sh", "fresh_binding.py", "fresh-start.sh", "target-run.sh", "fresh-binding.json", "candidate.patch",
    "in/fixture.sql", "in/pg_hba.conf", "in/ordered-exec/main.pietto",
    "in/ordered-exec/pietto.toml", "in/ordered-exec/contract.json",
    "in/timestamp-exec/main.pietto", "in/timestamp-exec/pietto.toml", "in/timestamp-exec/contract.json",
    "tls/ca.pem", "tls/ca-key.pem", "tls/other-ca.pem", "tls/other-ca-key.pem",
    "tls/server.pem", "tls/server-key.pem", "tls/elsewhere.pem", "tls/elsewhere-key.pem",
}
RAW = {"campaign.log", "relay.log", "pg-server.log", "client.json", "client.err", "cleanup.json"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding() -> dict:
    try:
        value = json.loads((HERE / "fresh-binding.json").read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"fresh binding missing or invalid: {error}") from error
    if value.get("format") != "pietto.phase77.pg-fresh-binding.v1" or value.get("dependencies") != VERSIONS:
        raise SystemExit("fresh binding has the wrong runtime identity")
    return value


def lifecycle_reasons(receipt: dict) -> list[str]:
    invocation, cleanup = receipt.get("invocation"), receipt.get("cleanup")
    if not isinstance(invocation, dict) or not isinstance(cleanup, dict):
        return ["target invocation or cleanup record missing"]
    nonce = invocation.get("nonce")
    name = f"pietto-p77-maint-pg-{nonce}"
    label = f"pietto.phase77.pg-run={nonce}"
    lock = "/tmp/claude-1000/pietto-docker-campaign-postgres.lock"
    if not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{24}", nonce) or invocation != {"nonce": nonce, "lock": lock, "timeout_seconds": 7200, "container_name": name, "container_label": label}:
        return ["target invocation differs from canonical lock, timeout or ownership"]
    container, relay = cleanup.get("container"), cleanup.get("relay")
    if not isinstance(container, dict) or not isinstance(relay, dict) or not isinstance(container.get("id"), str) or len(container["id"]) != 64 or container.get("name") != name or container.get("label") != label or container.get("label_value") != nonce or relay.get("reaped") is not True or not isinstance(relay.get("wait_status"), int) or cleanup.get("server_log_captured") is not True or cleanup.get("container_absent") is not True:
        return ["cleanup does not prove log capture, relay reap and owned container absence"]
    return []


def reasons(record: dict, receipt: dict, raw: Path | None = None) -> list[str]:
    found = []
    identity = record.get("identity")
    if not isinstance(identity, dict) or {name: item.get("version") for name, item in identity.items()} != VERSIONS:
        found.append("dependency versions")
    pietto = identity.get("pietto", {}) if isinstance(identity, dict) else {}
    fresh = binding()
    if pietto.get("origin") != fresh["origins"]["pietto"] or pietto.get("direct_url") != fresh["pietto"]["direct_url"] or any(pietto.get(key) != fresh["pietto"][key] for key in ("module", "record")):
        found.append("wheel Pietto origin")
    if record.get("fatal") is not None:
        found.append("client fatal")
    rows = record.get("rows", {})
    bounded = rows.get("bounded", {}) if isinstance(rows, dict) else {}
    ordered = [{"id": 2, "label": "two"}, {"id": 2, "label": "two"}, {"id": 3, "label": "three"}, {"id": 5, "label": "five"}]
    if bounded.get("rows") != ordered or bounded.get("batches") != [["int64", "string"]] * 4 or bounded.get("batch_rows") != [1, 1, 1, 1] or bounded.get("outcome", {}).get("end") != "COMPLETE" or bounded.get("outcome", {}).get("rows") != 4:
        found.append("bounded public rows")
    limited = rows.get("limit", {}) if isinstance(rows, dict) else {}
    if limited.get("delivered") != 3 or rows.get("limit_error", {}).get("code") != "PIE-R3004" or limited.get("outcome", {}).get("end") != "FAILED":
        found.append("max_rows public refusal")
    early = rows.get("early", {}) if isinstance(rows, dict) else {}
    if rows.get("early_first_rows") != 1 or rows.get("early_first") != ordered[:1] or early.get("end") != "STOPPED_EARLY" or early.get("transaction") != "ROLLBACK_ACK" or early.get("cleanup") != "CLOSED" or early.get("rows") != 1:
        found.append("early close terminal")
    cancelled = rows.get("cancel", {}) if isinstance(rows, dict) else {}
    cancel_outcome = cancelled.get("outcome", {})
    if rows.get("cancel_first_rows") != 1 or rows.get("cancel_first") != ordered[:1] or rows.get("cancel_control_joined") is not True or rows.get("cancel_error", {}).get("code") != "PIE-R3009" or cancel_outcome.get("cancel_requested") is not True or type(cancel_outcome.get("cancel_sent")) is not bool or type(cancel_outcome.get("cancel_observed")) is not bool or cancel_outcome.get("end") != "CANCELLED" or cancel_outcome.get("transaction") != "ROLLBACK_ACK" or cancel_outcome.get("cleanup") != "CLOSED" or cancel_outcome.get("rows") != 1:
        found.append("public cancel terminal")
    timestamp = record.get("timestamp", {})
    if timestamp.get("schema") != ["timestamp[us]"] or timestamp.get("values") != [{"kind": "datetime", "value": "2026-11-08T12:34:56.123456"}] or timestamp.get("outcome", {}).get("end") != "COMPLETE":
        found.append("typed timestamp")
    adbc = record.get("adbc", {})
    adbc_outcome = adbc.get("outcome", {})
    if adbc.get("before_close") != {"schema": ["int64", "string"], "rows": ordered[:1]} or adbc.get("after_close") != {"schema": ["int64", "string"], "rows": ordered[:1]} or adbc.get("public_batch_closed") is not True or adbc.get("handle_closed") is not True or adbc.get("remainder") != ordered[1:] or adbc_outcome.get("end") != "COMPLETE" or adbc_outcome.get("transaction") != "COMMIT_ACK" or adbc_outcome.get("cleanup") != "LOCAL_CLOSED_REMOTE_UNOBSERVED" or adbc_outcome.get("remote_source_use_end") != "TRANSACTION_ACK" or adbc_outcome.get("cleanup_failures") != [] or adbc_outcome.get("rows") != 4:
        found.append("flat ADBC ownership or EOF")
    raw_driver = record.get("raw_driver", {})
    raw_record = raw_driver.get("record") if isinstance(raw_driver, dict) else None
    before = raw_record.get("before_close", []) if isinstance(raw_record, dict) else []
    after_close = raw_record.get("after_close", {}) if isinstance(raw_record, dict) else {}
    valid_post_close = after_close == {"value": {"kind": "tuple", "value": "([3], datetime.datetime(2026, 11, 9, 0, 0), datetime.timedelta(0))"}} or (set(after_close) == {"error"} and isinstance(after_close["error"], dict))
    if raw_driver.get("returncode") != 0 or raw_driver.get("stderr") != "" or raw_driver.get("capture_overflow") is not False or raw_driver.get("timed_out") is not False or raw_driver.get("stdout_bytes", 4097) > 4096 or raw_driver.get("stderr_bytes", 4097) > 4096 or [item.get("kind") for item in before] != ["list", "datetime", "timedelta"] or not valid_post_close or raw_record.get("connection_closed") is not True:
        found.append("raw driver observation")
    if (receipt.get("candidate_base"), receipt.get("candidate_patch_sha256"), receipt.get("candidate_wheel_sha256"), receipt.get("candidate_lock_sha256")) != (BASE, PATCH, WHEEL, LOCK):
        found.append("candidate identity")
    if receipt.get("image") != IMAGE or receipt.get("network") != "none":
        found.append("image or network")
    found.extend(lifecycle_reasons(receipt))
    if raw is not None:
        if set(receipt.get("raw", {})) != RAW:
            found.append("raw receipt key set")
        if set(receipt.get("inputs", {})) != INPUTS:
            found.append("input receipt key set")
        for name, expected in receipt.get("raw", {}).items():
            if not (raw / name).is_file() or digest(raw / name) != expected:
                found.append("raw receipt " + name)
        for name, expected in receipt.get("inputs", {}).items():
            if not (HERE / name).is_file() or digest(HERE / name) != expected:
                found.append("input receipt " + name)
    return found


def selftest() -> int:
    record = {
        "identity": {name: {"version": version, "origin": binding()["origins"][name]} for name, version in VERSIONS.items()},
        "rows": {"bounded": {"rows": [{"id": 2, "label": "two"}, {"id": 2, "label": "two"}, {"id": 3, "label": "three"}, {"id": 5, "label": "five"}], "batches": [["int64", "string"]] * 4, "batch_rows": [1, 1, 1, 1], "outcome": {"end": "COMPLETE", "rows": 4}}, "limit": {"delivered": 3, "outcome": {"end": "FAILED"}}, "limit_error": {"type": "AttemptFailed", "code": "PIE-R3004"}, "early_first_rows": 1, "early_first": [{"id": 2, "label": "two"}], "early": {"end": "STOPPED_EARLY", "transaction": "ROLLBACK_ACK", "cleanup": "CLOSED", "rows": 1}, "cancel_first_rows": 1, "cancel_first": [{"id": 2, "label": "two"}], "cancel_control_joined": True, "cancel_error": {"code": "PIE-R3009"}, "cancel": {"outcome": {"cancel_requested": True, "cancel_sent": False, "cancel_observed": False, "end": "CANCELLED", "transaction": "ROLLBACK_ACK", "cleanup": "CLOSED", "rows": 1}}},
        "timestamp": {"schema": ["timestamp[us]"], "values": [{"kind": "datetime", "value": "2026-11-08T12:34:56.123456"}], "outcome": {"end": "COMPLETE"}},
        "adbc": {"before_close": {"schema": ["int64", "string"], "rows": [{"id": 2, "label": "two"}]}, "after_close": {"schema": ["int64", "string"], "rows": [{"id": 2, "label": "two"}]}, "public_batch_closed": True, "handle_closed": True, "remainder": [{"id": 2, "label": "two"}, {"id": 3, "label": "three"}, {"id": 5, "label": "five"}], "outcome": {"end": "COMPLETE", "transaction": "COMMIT_ACK", "cleanup": "LOCAL_CLOSED_REMOTE_UNOBSERVED", "remote_source_use_end": "TRANSACTION_ACK", "cleanup_failures": [], "rows": 4}},
        "raw_driver": {"returncode": 0, "stderr": "", "stdout_bytes": 1, "stderr_bytes": 0, "capture_overflow": False, "timed_out": False, "record": {"before_close": [{"kind": "list"}, {"kind": "datetime"}, {"kind": "timedelta"}], "after_close": {"value": {"kind": "tuple", "value": "([3], datetime.datetime(2026, 11, 9, 0, 0), datetime.timedelta(0))"}}, "connection_closed": True}},
    }
    nonce = "0" * 24
    label = f"pietto.phase77.pg-run={nonce}"
    receipt = {"candidate_base": BASE, "candidate_patch_sha256": PATCH, "candidate_wheel_sha256": WHEEL, "candidate_lock_sha256": LOCK, "image": IMAGE, "network": "none", "invocation": {"nonce": nonce, "lock": "/tmp/claude-1000/pietto-docker-campaign-postgres.lock", "timeout_seconds": 7200, "container_name": f"pietto-p77-maint-pg-{nonce}", "container_label": label}, "cleanup": {"container": {"id": "0" * 64, "name": f"pietto-p77-maint-pg-{nonce}", "label": label, "label_value": nonce}, "relay": {"reaped": True, "wait_status": 143}, "server_log_captured": True, "container_absent": True}}
    record["identity"]["pietto"].update({key: binding()["pietto"][key] for key in ("direct_url", "module", "record")})
    assert not reasons(record, receipt)
    for mutate in (
        lambda value: value["rows"]["limit"].__setitem__("delivered", 4),
        lambda value: value["rows"]["early"].__setitem__("end", "COMPLETE"),
        lambda value: value["adbc"].__setitem__("after_close", {"rows": [2]}),
        lambda value: value["raw_driver"]["record"]["after_close"].clear(),
        lambda value: value["identity"]["pietto"].__setitem__("origin", "/editable/source"),
        lambda value: value["identity"]["pietto"].__setitem__("origin", "/tmp/old-prefix"),
        lambda value: value["identity"]["pietto"].__setitem__("module", "/grafted/pietto/__init__.py"),
        lambda value: value["identity"]["pietto"].__setitem__("direct_url", '{"url":"file:///wrong-wheel.whl","archive_info":{}}'),
        lambda value: value["raw_driver"].__setitem__("returncode", -9),
        lambda value: value["rows"]["limit_error"].__setitem__("code", "PIE-R3999"),
    ):
        changed = json.loads(json.dumps(record))
        mutate(changed)
        assert reasons(changed, receipt)
    changed_receipt = json.loads(json.dumps(receipt))
    changed_receipt["cleanup"]["relay"]["reaped"] = False
    assert reasons(record, changed_receipt)
    changed_receipt = json.loads(json.dumps(receipt))
    changed_receipt["candidate_patch_sha256"] = "0" * 64
    assert reasons(record, changed_receipt)
    with tempfile.TemporaryDirectory() as temporary:
        raw = Path(temporary)
        for name in RAW:
            (raw / name).write_text("raw\n")
        complete = json.loads(json.dumps(receipt))
        complete["raw"] = {name: digest(raw / name) for name in RAW}
        complete["inputs"] = {name: digest(HERE / name) for name in INPUTS}
        assert not reasons(record, complete, raw)
        missing = json.loads(json.dumps(complete))
        missing["raw"].pop("client.json")
        assert reasons(record, missing, raw)
        missing = json.loads(json.dumps(complete))
        missing["inputs"].pop("raw_driver_child.py")
        assert reasons(record, missing, raw)
        missing = json.loads(json.dumps(complete))
        missing["inputs"].pop("in/timestamp-exec/pietto.toml")
        assert reasons(record, missing, raw)
    print("selftest PASS: clean R4 observation plus 15 negative mutations")
    return 0


def compare() -> int:
    raw = HERE / "raw"
    try:
        receipt = json.loads((raw / "campaign.json").read_text())
        record = json.loads((raw / "client.json").read_text())
    except (OSError, ValueError):
        print("FAIL missing or invalid raw record")
        return 1
    found = reasons(record, receipt, raw)
    print("PASS" if not found else "FAIL", "; ".join(found))
    (raw / "compare.json").write_text(json.dumps({"pass": not found, "reasons": found}, indent=2) + "\n")
    return 0 if not found else 1


if __name__ == "__main__":
    raise SystemExit({"selftest": selftest, "compare": compare}[sys.argv[1]]())
