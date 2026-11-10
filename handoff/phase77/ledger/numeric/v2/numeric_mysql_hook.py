"""Hook the frozen numeric probe into the parent MySQL literal-none campaign."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Any


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(manager: Any, *, container_id: str, port: int, ca_file: Path, run_directory: Path, candidate_python: Path) -> dict[str, Path]:
    """Create only an owned sandbox role/database, then run the frozen plan.

    The caller owns the already-live literal-none container, relay, lock and
    root manager. The generated password remains only in the child environment.
    """
    if (
        not 1 <= port <= 65535
        or run_directory.exists()
        or not ca_file.is_file()
        or not str(run_directory).startswith("/tmp/pietto-p77-numeric-mysql-run-")
        or len(container_id) != 64
        or any(character not in "0123456789abcdef" for character in container_id)
    ):
        raise ValueError("NUMERIC_MYSQL_HOOK_INPUT")
    password = secrets.token_hex(24)
    cursor = manager.cursor()
    try:
        cursor.execute("CREATE DATABASE `pietto_numeric_probe`")
        cursor.execute("CREATE USER 'pietto_numeric_probe'@'127.0.0.1' IDENTIFIED BY %s REQUIRE SSL", (password,))
        cursor.execute("GRANT ALL PRIVILEGES ON `pietto_numeric_probe`.* TO 'pietto_numeric_probe'@'127.0.0.1'")
        manager.commit()
    finally:
        cursor.close()
    run_directory.mkdir(mode=0o700, parents=True)
    endpoint = run_directory / "endpoint.json"
    subprocess.run((str(candidate_python), "-I", "-B", str(HERE / "materialize_endpoint.py"), "--engine", "mysql", "--port", str(port), "--ca-file", str(ca_file), "--out", str(endpoint)), check=True)
    result = run_directory / "numeric-receipt.json"
    environment = {"PATH": "/usr/bin:/bin", "UV_PYTHON": "3.13.13", "UV_OFFLINE": "1", "UV_LINK_MODE": "copy", "PIETTO_NUMERIC_PROBE_PASSWORD": password}
    subprocess.run((str(candidate_python), "-I", "-B", str(HERE / "p77_mysql_numeric_probe.py"), "--run-plan", str(HERE / "manifest.json"), "--endpoint-json", str(endpoint), "--write-receipt", str(result)), env=environment, check=True)
    binding = endpoint.with_suffix(endpoint.suffix + ".binding.json")
    bootstrap = run_directory / "numeric-bootstrap.json"
    bootstrap.write_text(json.dumps({
        "format": "pietto.phase77.numeric_mysql_bootstrap.v1",
        "container_id": container_id,
        "role": "pietto_numeric_probe",
        "database": "pietto_numeric_probe",
        "manifest_sha256": sha256(HERE / "manifest.json"),
        "endpoint_binding_sha256": sha256(binding),
        "numeric_receipt_sha256": sha256(result),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"endpoint": endpoint, "binding": binding, "receipt": result, "bootstrap": bootstrap}


def main() -> int:
    if sys.argv[1:] != ["--self-check"]:
        raise SystemExit("this hook is called only by the parent MySQL campaign")
    assert (HERE / "manifest.json").is_file()
    assert (HERE / "materialize_endpoint.py").is_file()
    assert (HERE / "p77_mysql_numeric_probe.py").is_file()
    assert "pietto_numeric_probe" in (HERE / "p77_mysql_numeric_probe.py").read_text(encoding="utf-8")
    print("numeric MySQL hook self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
