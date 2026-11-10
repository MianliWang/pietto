"""Materialize one numeric-probe endpoint from a reviewed literal-none relay."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile


HERE = Path(__file__).resolve().parent
PROBE = HERE / "p77_mysql_numeric_probe.py"
MANIFEST = HERE / "manifest.json"
RELAY = {
    "postgres": Path(__file__).resolve().parent / "relay.py",
    "mysql": Path("/tmp/pietto-p77-maint-mysql-none-campaign/relay.py"),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("artifact") != "pietto.phase77.numeric_primitive_probe.v2":
        raise ValueError("MANIFEST")
    return value


def materialize(engine: str, port: int, ca_file: Path, out: Path) -> dict[str, object]:
    manifest = load_manifest(MANIFEST)
    if engine not in RELAY or not 1 <= port <= 65535 or not ca_file.is_file():
        raise ValueError("ENGINE_PORT_OR_CA")
    contract = manifest[engine + "_relay_contract"]
    if not isinstance(contract, dict):
        raise ValueError("RELAY_CONTRACT")
    relay = RELAY[engine]
    if not relay.is_file() or sha256(relay) != contract.get("relay_sha256"):
        raise ValueError("RELAY_IDENTITY")
    endpoint = {
        "engine": engine,
        "host": "127.0.0.1",
        "port": port,
        "user": "pietto_numeric_probe",
        "database": "pietto_numeric_probe",
        "password_env": "PIETTO_NUMERIC_PROBE_PASSWORD",
        "ca_file": str(ca_file.resolve()),
        "verify_identity": True,
        "loopback_tls_exception": False,
        "relay_contract": contract,
    }
    binding = {
        "format": "pietto.phase77.numeric_endpoint_binding.v1",
        "engine": engine,
        "manifest_sha256": sha256(MANIFEST),
        "probe_sha256": sha256(PROBE),
        "relay": str(relay),
        "relay_sha256": sha256(relay),
        "ca_sha256": sha256(ca_file),
        "endpoint": {key: value for key, value in endpoint.items() if key != "password_env"},
    }
    if out.exists() or out.parent.exists() and not out.parent.is_dir():
        raise ValueError("ENDPOINT_OUTPUT")
    out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    out.write_text(json.dumps(endpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    binding_path = out.with_suffix(out.suffix + ".binding.json")
    binding_path.write_text(json.dumps(binding, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return binding


def self_check() -> None:
    manifest = load_manifest(MANIFEST)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        ca = root / "ca.pem"
        ca.write_text("test-ca\n", encoding="ascii")
        binding = materialize("postgres", 54321, ca, root / "endpoint.json")
        endpoint = json.loads((root / "endpoint.json").read_text(encoding="utf-8"))
        assert endpoint["host"] == "127.0.0.1"
        assert endpoint["user"] == endpoint["database"] == "pietto_numeric_probe"
        assert endpoint["verify_identity"] is True and endpoint["loopback_tls_exception"] is False
        assert endpoint["relay_contract"] == manifest["postgres_relay_contract"]
        assert binding["manifest_sha256"] == sha256(MANIFEST)
        try:
            materialize("postgres", 0, ca, root / "bad.json")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid listener port was accepted")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--engine", choices=("postgres", "mysql"))
    parser.add_argument("--port", type=int)
    parser.add_argument("--ca-file", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("numeric endpoint materializer self-check passed")
    if args.engine or args.port or args.ca_file or args.out:
        if not (args.engine and args.port and args.ca_file and args.out):
            parser.error("--engine, --port, --ca-file and --out are required together")
        if args.out.name != "endpoint.json" or not str(args.out.parent).startswith("/tmp/pietto-p77-numeric-"):
            parser.error("--out must be an owned numeric run endpoint.json")
        materialize(args.engine, args.port, args.ca_file, args.out)
    if not args.self_check and not args.engine:
        parser.error("choose --self-check or endpoint arguments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
