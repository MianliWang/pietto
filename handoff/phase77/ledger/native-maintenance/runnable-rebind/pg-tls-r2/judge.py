"""C76-06 run-2 judge. It accepts only one complete same-run receipt."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTES = ("postgres_rows", "postgres_adbc")
APPLICATION = {
    "postgres_rows": "pietto_private_execution",
    "postgres_adbc": "pietto_postgres_adbc",
}
ROWS = sorted([[2, "two"], [2, "two"], [3, "three"], [5, "five"]])
BASE = "f8ccd2c44a2d9adf431a496bd9bbae037783176f"
PATCH = "548e72276b20c2bff3bb0613a527ef230fb9095942b562dca32a6150da12e1cc"
WHEEL = "f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73"
LOCK = "b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064"
IMAGE = "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e"
DEPENDENCIES = {
    "pietto": "0.1.10",
    "pyarrow": "26.0.1",
    "psycopg": "3.3.8",
    "psycopg-binary": "3.3.8",
    "adbc-driver-postgresql": "1.13.0",
    "adbc-driver-manager": "1.13.0",
}

# phase, sslmode, CA basename, expected result kind, expected TCP connection.
CELLS = {
    "A1_full_ok": ("A", "require", "ca.pem", "rows", True),
    "A2_wrong_ca": ("A", "require", "other-ca.pem", "failed", True),
    "A3_missing_ca": ("A", "require", "absent.pem", "failed", True),
    "A4_require": ("A", "require", None, "rows", True),
    "A5_disable_ca": ("A", "disable", "ca.pem", "rejected", False),
    "A6_system_ca": ("A", "require", "system", "rejected", False),
    "B1_wrong_host": ("B", "require", "ca.pem", "failed", True),
    "B2_require_any_name": ("B", "require", None, "rows", True),
    "C1_ambient_pgsslrootcert": ("A", "require", "ca.pem", "rejected", False),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding() -> dict:
    try:
        value = json.loads((HERE / "fresh-binding.json").read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"fresh binding missing or invalid: {error}") from error
    if value.get("format") != "pietto.phase77.pg-fresh-binding.v1" or value.get("dependencies") != DEPENDENCIES:
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


def segment(lines: list[str], cell: str, route: str) -> list[str] | None:
    begin = f"pietto-p77-maint-mark begin {cell} {route}"
    end = f"pietto-p77-maint-mark end {cell} {route}"
    starts = [index for index, line in enumerate(lines) if line.endswith(begin)]
    stops = [index for index, line in enumerate(lines) if line.endswith(end)]
    if len(starts) != 1 or len(stops) != 1 or starts[0] >= stops[0]:
        return None
    return lines[starts[0] + 1 : stops[0]]


def wanted_result(cell: str, route: str, kind: str) -> tuple[str, str, str]:
    if kind == "failed":
        return ("failed", "PIE-R2004", "CONNECTION_FAILED")
    if cell == "C1_ambient_pgsslrootcert":
        return (
            ("failed", "PIE-R2003", "AMBIENT_ENVIRONMENT")
            if route == "postgres_rows"
            else ("rejected", "PIE-R2003", "EXECUTION_AMBIENT_CONNECTION_PROFILE")
        )
    return ("rejected", "PIE-R1002", "EXECUTION_ACCESS_PROFILE")


def record_reasons(cell: str, route: str, record: dict, sql_sha256: str) -> list[str]:
    _, sslmode, ca_file, kind, _ = CELLS[cell]
    reasons = []
    if record.get("sslmode") != sslmode:
        reasons.append(f"sslmode {record.get('sslmode')!r} != {sslmode!r}")
    if record.get("ca_file") != ca_file:
        reasons.append(f"ca_file {record.get('ca_file')!r} != {ca_file!r}")
    if record.get("application") != APPLICATION[route]:
        reasons.append("record route application differs")
    if record.get("ambient_pgsslrootcert") is not (cell == "C1_ambient_pgsslrootcert"):
        reasons.append("ambient PGSSLROOTCERT marker differs")
    if record.get("sql_sha256") != sql_sha256:
        reasons.append("compiled SQL differs from sql/statement.sql")
    if record.get("dependencies") != DEPENDENCIES:
        reasons.append("client dependency identity differs")
    fresh = binding()
    origins = record.get("dependency_origins")
    if origins != fresh["origins"]:
        reasons.append("client dependency origins are incomplete")
    if record.get("pietto_direct_url") != fresh["pietto"]["direct_url"]:
        reasons.append("client Pietto distribution is not the frozen wheel")
    files = record.get("pietto_package_files")
    if files != {name: fresh["pietto"][name] for name in ("module", "record")}:
        reasons.append("client Pietto module or RECORD is outside the wheel prefix")
    result = record.get("result") if isinstance(record.get("result"), dict) else {}
    if kind == "rows":
        if result.get("kind") != "rows":
            reasons.append(f"expected rows, got {result!r}")
        elif sorted(result.get("rows") or []) != ROWS:
            reasons.append("row bag differs from oracle")
        if result.get("end") != "COMPLETE":
            reasons.append(f"end {result.get('end')!r} != COMPLETE")
    else:
        expected = wanted_result(cell, route, kind)
        got = (
            result.get("kind"),
            result.get("code"),
            result.get("detail") if expected[0] == "rejected" else result.get("category"),
        )
        if got != expected:
            reasons.append(f"result {got!r} != {expected!r}")
    return reasons


def authorized(lines: list[str], route: str) -> list[str]:
    return [
        line for line in lines
        if "connection authorized:" in line
        and "user=pietto_reader" in line
        and f"application_name={APPLICATION[route]}" in line
        and "SSL enabled" in line
    ]


def observation_reasons(cell: str, route: str, relay: list[str] | None, server: list[str] | None) -> list[str]:
    _, _, _, kind, connects = CELLS[cell]
    if relay is None or server is None:
        return ["cell markers missing or not unique"]
    reasons = []
    accepts = sum(" accept " in line for line in relay)
    matching = authorized(server, route)
    any_auth = [line for line in server if "connection authorized:" in line and "pietto_reader" in line]
    any_authn = [line for line in server if "connection authenticated:" in line and "pietto_reader" in line]
    if connects and accepts < 1:
        reasons.append("no TCP connection reached relay")
    if not connects and accepts:
        reasons.append("TCP connection despite pre-connect refusal")
    if kind == "rows" and not matching:
        reasons.append("no TLS authorized session for this route application")
    if kind != "rows" and (any_auth or any_authn):
        reasons.append("refused or failed cell reached authentication")
    if cell == "A2_wrong_ca" and not any(
        "could not accept SSL connection" in line and "unknown ca" in line.lower()
        for line in server
    ):
        reasons.append("wrong-CA cell lacks observed TLS unknown-ca failure")
    return reasons


def receipt_reasons(receipt: dict, records: list[dict], raw: Path | None = None) -> list[str]:
    reasons = []
    if receipt.get("schema") != 1 or receipt.get("complete") is not True or receipt.get("ready") is not True:
        reasons.append("campaign receipt is absent or incomplete")
    if (receipt.get("candidate_base"), receipt.get("candidate_patch_sha256"), receipt.get("candidate_wheel_sha256"), receipt.get("candidate_lock_sha256")) != (BASE, PATCH, WHEEL, LOCK):
        reasons.append("candidate identity differs from the pre-registered base, patch or wheel")
    if receipt.get("image") != IMAGE or receipt.get("network") != "none":
        reasons.append("container image or network differs")
    reasons.extend(lifecycle_reasons(receipt))
    expected_exits = sorted((cell, route, 0) for cell in CELLS for route in ROUTES)
    got_exits = sorted((item.get("cell"), item.get("route"), item.get("status")) for item in receipt.get("cells", []))
    if got_exits != expected_exits:
        reasons.append("cell exit receipt is incomplete or nonzero")
    expected_keys = sorted((cell, route) for cell in CELLS for route in ROUTES)
    keys = sorted((record.get("cell"), record.get("route")) for record in records)
    if keys != expected_keys:
        reasons.append("client record receipt is incomplete or duplicate")
    if raw is not None:
        for name in ("relay.log", "pg-server.log", "campaign.log", "cell-exits.tsv", "cleanup.json"):
            path = raw / name
            if not path.is_file() or receipt.get("raw", {}).get(name) != digest(path):
                reasons.append(f"raw receipt mismatch for {name}")
        for path in sorted(raw.glob("cell-*-*.json")):
            if receipt.get("raw", {}).get(path.name) != digest(path):
                reasons.append(f"raw receipt mismatch for {path.name}")
        for name in ("ORACLE.md", "judge.py", "client.py", "receipt.py", "relay.py", "pg.sh", "gen-tls.sh", "fresh_binding.py", "fresh-start.sh", "target-run.sh", "fresh-binding.json", "in/fixture.sql", "in/pg_hba.conf", "sql/statement.sql", "candidate.patch", "tls/ca.pem", "tls/other-ca.pem", "tls/server.pem", "tls/elsewhere.pem"):
            if receipt.get("inputs", {}).get(name) != digest(HERE / name):
                reasons.append(f"input identity mismatch for {name}")
        home = raw / "home/.postgresql/root.crt"
        if not home.is_file() or receipt.get("ambient_home_root_sha256") != digest(home):
            reasons.append("controlled HOME fixture receipt mismatch")
    return reasons


def judge_all(records: list[dict], relay: list[str], server: list[str], sql_sha256: str, receipt: dict, raw: Path | None = None):
    verdicts = []
    integrity = receipt_reasons(receipt, records, raw)
    if integrity:
        verdicts.append(("CAMPAIGN", "FAIL", integrity))
    keyed = {(record.get("cell"), record.get("route")): record for record in records}
    for cell in CELLS:
        for route in ROUTES:
            record = keyed.get((cell, route))
            reasons = ["no client record"] if record is None else record_reasons(cell, route, record, sql_sha256)
            reasons.extend(observation_reasons(cell, route, segment(relay, cell, route), segment(server, cell, route)))
            verdicts.append((f"{cell} {route}", "FAIL" if reasons else "PASS", reasons))
    for route in ROUTES:
        for failed, control in (("A2_wrong_ca", "A1_full_ok"), ("B1_wrong_host", "B2_require_any_name")):
            record = keyed.get((control, route), {})
            if record.get("result", {}).get("kind") != "rows":
                verdicts.append((f"CONTROL {failed} {route}", "FAIL", [f"{control} did not prove same-run transport"]))
    return verdicts


def compare() -> int:
    raw = HERE / "raw"
    if not raw.is_dir():
        print("FAIL CAMPAIGN raw directory missing")
        return 1
    try:
        receipt = json.loads((raw / "campaign.json").read_text())
    except (OSError, ValueError):
        receipt = {}
    records = []
    for path in sorted(raw.glob("cell-*.json")):
        try:
            records.append(json.loads(path.read_text()))
        except ValueError:
            records.append({"cell": path.name, "route": "unparsed"})
    relay = (raw / "relay.log").read_text().splitlines() if (raw / "relay.log").is_file() else []
    server = (raw / "pg-server.log").read_text(errors="replace").splitlines() if (raw / "pg-server.log").is_file() else []
    verdicts = judge_all(records, relay, server, digest(HERE / "sql/statement.sql"), receipt, raw)
    failed = [item for item in verdicts if item[1] != "PASS"]
    for name, verdict, reasons in verdicts:
        print(verdict, name, "; ".join(reasons))
    (raw / "compare.json").write_text(json.dumps({"pass": len(verdicts) - len(failed), "fail": len(failed), "verdicts": verdicts}, indent=2) + "\n")
    return 1 if failed else 0


def world(sql_sha256: str):
    records, relay, server = [], [], []
    for cell, (_, sslmode, ca_file, kind, connects) in CELLS.items():
        for route in ROUTES:
            if kind == "rows":
                result = {"kind": "rows", "rows": list(reversed(ROWS)), "end": "COMPLETE"}
            elif cell == "C1_ambient_pgsslrootcert":
                result = (
                    {"kind": "failed", "code": "PIE-R2003", "category": "AMBIENT_ENVIRONMENT"}
                    if route == "postgres_rows"
                    else {"kind": "rejected", "code": "PIE-R2003", "detail": "EXECUTION_AMBIENT_CONNECTION_PROFILE"}
                )
            elif kind == "rejected":
                result = {"kind": "rejected", "code": "PIE-R1002", "detail": "EXECUTION_ACCESS_PROFILE"}
            else:
                result = {"kind": "failed", "code": "PIE-R2004", "category": "CONNECTION_FAILED"}
            fresh = binding()
            records.append({"cell": cell, "route": route, "sslmode": sslmode, "ca_file": ca_file, "application": APPLICATION[route], "ambient_pgsslrootcert": cell == "C1_ambient_pgsslrootcert", "sql_sha256": sql_sha256, "dependencies": DEPENDENCIES, "dependency_origins": fresh["origins"], "pietto_direct_url": fresh["pietto"]["direct_url"], "pietto_package_files": {name: fresh["pietto"][name] for name in ("module", "record")}, "result": result})
            marker = f"{cell} {route}"
            relay.append(f"1 mark pietto-p77-maint-mark begin {marker}")
            if connects:
                relay.append("2 accept 1")
            relay.append(f"3 mark pietto-p77-maint-mark end {marker}")
            server.append(f"LOG: pietto-p77-maint-mark begin {marker}")
            if kind == "rows":
                server.append(f"LOG: connection authorized: user=pietto_reader database=app application_name={APPLICATION[route]} SSL enabled (protocol=TLSv1.3)")
            if cell == "A2_wrong_ca":
                server.append("LOG: could not accept SSL connection: tlsv1 alert unknown ca")
            server.append(f"LOG: pietto-p77-maint-mark end {marker}")
    nonce = "0" * 24
    label = f"pietto.phase77.pg-run={nonce}"
    receipt = {"schema": 1, "complete": True, "ready": True, "candidate_base": BASE, "candidate_patch_sha256": PATCH, "candidate_wheel_sha256": WHEEL, "candidate_lock_sha256": LOCK, "image": IMAGE, "network": "none", "invocation": {"nonce": nonce, "lock": "/tmp/claude-1000/pietto-docker-campaign-postgres.lock", "timeout_seconds": 7200, "container_name": f"pietto-p77-maint-pg-{nonce}", "container_label": label}, "cleanup": {"container": {"id": "0" * 64, "name": f"pietto-p77-maint-pg-{nonce}", "label": label, "label_value": nonce}, "relay": {"reaped": True, "wait_status": 143}, "server_log_captured": True, "container_absent": True}, "cells": [{"cell": cell, "route": route, "status": 0} for cell in CELLS for route in ROUTES]}
    return records, relay, server, receipt


def selftest() -> int:
    sha = "0" * 64
    records, relay, server, receipt = world(sha)
    assert not [item for item in judge_all(records, relay, server, sha, receipt) if item[1] != "PASS"]
    mutations = (
        lambda r, l, s, q: r[0].__setitem__("sslmode", "disable"),
        lambda r, l, s, q: s.__setitem__(s.index(next(line for line in s if "pietto_postgres_adbc" in line)), "LOG: connection authorized: user=pietto_reader database=app application_name=pietto_private_execution SSL enabled"),
        lambda r, l, s, q: q.clear(),
        lambda r, l, s, q: q.__setitem__("candidate_base", "0" * 40),
        lambda r, l, s, q: q.__setitem__("ready", False),
        lambda r, l, s, q: q.__setitem__("cells", q["cells"][1:]),
        lambda r, l, s, q: l.insert(l.index("3 mark pietto-p77-maint-mark end C1_ambient_pgsslrootcert postgres_rows"), "2 accept 9"),
        lambda r, l, s, q: s.__setitem__(s.index("LOG: could not accept SSL connection: tlsv1 alert unknown ca"), "LOG: ordinary transport failure"),
        lambda r, l, s, q: r[0]["dependency_origins"].__setitem__("pietto", "/tmp/old-prefix"),
        lambda r, l, s, q: r[0]["pietto_package_files"].__setitem__("module", "/grafted/pietto/__init__.py"),
        lambda r, l, s, q: r[0].__setitem__("pietto_direct_url", '{"url":"file:///wrong-wheel.whl","archive_info":{}}'),
        lambda r, l, s, q: q["cleanup"].__setitem__("container_absent", False),
    )
    for mutate in mutations:
        r, l, s, q = json.loads(json.dumps((records, relay, server, receipt)))
        mutate(r, l, s, q)
        assert any(item[1] == "FAIL" for item in judge_all(r, l, s, sha, q))
    with tempfile.TemporaryDirectory() as temporary:
        raw = Path(temporary)
        (raw / "home/.postgresql").mkdir(parents=True)
        (raw / "home/.postgresql/root.crt").write_text("controlled\n")
        for name in ("relay.log", "pg-server.log", "campaign.log", "cell-exits.tsv", "cleanup.json"):
            (raw / name).write_text("\n")
        for record in records:
            (raw / f"cell-{record['cell']}-{record['route']}.json").write_text(json.dumps(record))
        complete = json.loads(json.dumps(receipt))
        complete["inputs"] = {
            name: digest(HERE / name)
            for name in ("ORACLE.md", "judge.py", "client.py", "receipt.py", "relay.py", "pg.sh", "gen-tls.sh", "fresh_binding.py", "fresh-start.sh", "target-run.sh", "fresh-binding.json", "in/fixture.sql", "in/pg_hba.conf", "sql/statement.sql", "candidate.patch", "tls/ca.pem", "tls/other-ca.pem", "tls/server.pem", "tls/elsewhere.pem")
        }
        complete["ambient_home_root_sha256"] = digest(raw / "home/.postgresql/root.crt")
        complete["raw"] = {
            path.name: digest(path)
            for path in (*sorted(raw.glob("cell-*-*.json")), *(raw / name for name in ("relay.log", "pg-server.log", "campaign.log", "cell-exits.tsv", "cleanup.json")))
        }
        assert not receipt_reasons(complete, records, raw)
        for input_name in ("in/pg_hba.conf", "pg.sh"):
            changed = json.loads(json.dumps(complete))
            changed["inputs"][input_name] = "0" * 64
            assert receipt_reasons(changed, records, raw), input_name
    print(f"selftest PASS: clean world 18/18 PASS; {len(mutations) + 2} evidence mutations fail")
    return 0


if __name__ == "__main__":
    sys.exit({"selftest": selftest, "compare": compare}[sys.argv[1]]())
