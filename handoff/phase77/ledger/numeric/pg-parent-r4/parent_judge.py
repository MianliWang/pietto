"""Independently reject incomplete numeric PostgreSQL parent evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import tempfile
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
_receipt_spec = importlib.util.spec_from_file_location("parent_receipt", HERE / "parent_receipt.py")
if _receipt_spec is None or _receipt_spec.loader is None:
    raise RuntimeError("parent receipt module is unavailable")
parent_receipt = importlib.util.module_from_spec(_receipt_spec)
_receipt_spec.loader.exec_module(parent_receipt)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_hashes(root: Path, actual: object, names: tuple[str, ...]) -> None:
    if not isinstance(actual, dict) or set(actual) != set(names):
        raise ValueError("receipt key set is incomplete")
    for name in names:
        if not (root / name).is_file() or actual[name] != digest(root / name):
            raise ValueError("receipt hash mismatch")


def judge(raw: Path, run: Path) -> None:
    receipt = load(raw / "parent-receipt.json")
    if not isinstance(receipt, dict) or set(receipt) != {
        "format", "candidate", "runtime", "cleanup", "inputs", "candidate_inputs", "raw", "hook"
    } or receipt["format"] != "pietto.phase77.numeric_pg_parent_receipt.v1":
        raise ValueError("parent receipt shape")
    expected_candidate = {
        "base": "f8ccd2c44a2d9adf431a496bd9bbae037783176f",
        "lock_sha256": "b2cc96b25b0b9f2225c4529f0123ae869cd804af0578b4f83c931a15aa893064",
        "patch_sha256": "7345ddec240b89308f20867bfbcc9abf6f9cd7c49498b641f95df142cf62da2c",
        "target_pins_sha256": "572a36a890cda4dc286cd9f9fcccf7998a292fc3b437b7836937960c74e87e92",
        "wheel_sha256": "f4c96921c4d4ceb057830f2dd21f2e634325dac2bef933532747ae4aab963a73",
    }
    if receipt["candidate"] != expected_candidate:
        raise ValueError("candidate identity")
    require_hashes(HERE, receipt["inputs"], parent_receipt.INPUT_NAMES)
    expected_external = {name: digest(path) for name, path in parent_receipt.CANDIDATE_NAMES.items()}
    if receipt["candidate_inputs"] != expected_external:
        raise ValueError("candidate input identity")
    require_hashes(raw, receipt["raw"], parent_receipt.RAW_NAMES)
    hook = receipt["hook"]
    if not isinstance(hook, dict) or set(hook) != {"run", "files"} or hook["run"] != str(run):
        raise ValueError("hook run identity")
    require_hashes(run, hook["files"], parent_receipt.HOOK_NAMES)
    runtime = receipt["runtime"]
    cleanup = receipt["cleanup"]
    if not isinstance(runtime, dict) or set(runtime) != {"container_id", "image", "network"}:
        raise ValueError("runtime shape")
    if runtime["network"] != "none" or runtime["image"] != "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e":
        raise ValueError("runtime containment")
    if not isinstance(cleanup, dict) or cleanup.get("container_absent") is not True or cleanup.get("container_id") != runtime["container_id"] or cleanup.get("relay_kill_exit") != 0 or cleanup.get("relay_reaped") is not True or cleanup.get("relay_exit") not in {0, 143}:
        raise ValueError("cleanup terminal")
    expected_run = Path("/tmp/pietto-p77-numeric-pg-run-" + str(runtime["container_id"]))
    if run != expected_run:
        raise ValueError("derived hook run identity")
    manifest = load(HERE / "manifest.json")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("postgres_relay_contract"), dict):
        raise ValueError("manifest identity")
    contract = manifest["postgres_relay_contract"]
    bootstrap, endpoint, binding, numeric = (load(run / name) for name in parent_receipt.HOOK_NAMES)
    endpoint_keys = {"engine", "host", "port", "user", "database", "password_env", "ca_file", "verify_identity", "loopback_tls_exception", "relay_contract"}
    if not isinstance(endpoint, dict) or set(endpoint) != endpoint_keys or endpoint.get("engine") != "postgres" or endpoint.get("host") != "127.0.0.1" or type(endpoint.get("port")) is not int or not 1 <= endpoint["port"] <= 65535 or endpoint.get("user") != "pietto_numeric_probe" or endpoint.get("database") != "pietto_numeric_probe" or endpoint.get("password_env") != "PIETTO_NUMERIC_PROBE_PASSWORD" or endpoint.get("ca_file") != str((HERE / "tls/ca.pem").resolve()) or endpoint.get("verify_identity") is not True or endpoint.get("loopback_tls_exception") is not False or endpoint.get("relay_contract") != contract:
        raise ValueError("endpoint contract")
    public_endpoint = {key: value for key, value in endpoint.items() if key != "password_env"}
    binding_keys = {"format", "engine", "manifest_sha256", "probe_sha256", "relay", "relay_sha256", "ca_sha256", "endpoint"}
    if not isinstance(binding, dict) or set(binding) != binding_keys or binding.get("format") != "pietto.phase77.numeric_endpoint_binding.v1" or binding.get("engine") != "postgres" or binding.get("manifest_sha256") != digest(HERE / "manifest.json") or binding.get("probe_sha256") != digest(HERE / "p77_mysql_numeric_probe.py") or binding.get("relay") != str(HERE / "relay.py") or binding.get("relay_sha256") != digest(HERE / "relay.py") or binding.get("ca_sha256") != digest(HERE / "tls/ca.pem") or binding.get("endpoint") != public_endpoint:
        raise ValueError("endpoint binding")
    expected_bootstrap = {"container": runtime["container_id"], "role": "pietto_numeric_probe", "database": "pietto_numeric_probe", "relay_sha256": digest(HERE / "relay.py"), "endpoint": public_endpoint}
    if not isinstance(bootstrap, dict) or bootstrap != expected_bootstrap:
        raise ValueError("bootstrap identity")
    plan_sha = hashlib.sha256((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")).hexdigest()
    numeric_keys = {"plan", "plan_sha256", "engine", "records", "terminal"}
    if not isinstance(numeric, dict) or set(numeric) != numeric_keys or numeric.get("plan") != str(HERE / "manifest.json") or numeric.get("plan_sha256") != plan_sha or numeric.get("engine") != "postgres" or numeric.get("terminal") != {"kind": "success"} or not isinstance(numeric.get("records"), list):
        raise ValueError("numeric terminal")
    origin = load(raw / "installed-origin.json")
    if not isinstance(origin, dict) or origin.get("wheel_url") != "file:///tmp/pietto-maintenance-2601-338-package-dist-r2/pietto-0.1.10-py3-none-any.whl" or origin.get("editable") is not False or not origin.get("record") or not origin.get("prefix"):
        raise ValueError("installed wheel origin")
    if "pg: removed" not in (raw / "campaign.log").read_text(encoding="utf-8"):
        raise ValueError("cleanup log")


def self_check() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        container = "a" * 64
        raw = root / "raw"
        run = Path("/tmp/pietto-p77-numeric-pg-run-" + container)
        if run.exists():
            raise AssertionError("self-check hook run already exists")
        raw.mkdir()
        run.mkdir()
        try:
            for name in parent_receipt.RAW_NAMES:
                (raw / name).write_text("ok\n", encoding="utf-8")
            (raw / "cleanup.json").write_text(json.dumps({"container_absent": True, "container_id": container, "relay_kill_exit": 0, "relay_exit": 143, "relay_reaped": True}), encoding="utf-8")
            (raw / "installed-origin.json").write_text(json.dumps({"wheel_url": "file:///tmp/pietto-maintenance-2601-338-package-dist-r2/pietto-0.1.10-py3-none-any.whl", "editable": False, "record": "x", "prefix": "x"}), encoding="utf-8")
            (raw / "campaign.log").write_text("pg: removed\n", encoding="utf-8")
            manifest = load(HERE / "manifest.json")
            contract = manifest["postgres_relay_contract"]
            endpoint = {"engine": "postgres", "host": "127.0.0.1", "port": 54321, "user": "pietto_numeric_probe", "database": "pietto_numeric_probe", "password_env": "PIETTO_NUMERIC_PROBE_PASSWORD", "ca_file": str((HERE / "tls/ca.pem").resolve()), "verify_identity": True, "loopback_tls_exception": False, "relay_contract": contract}
            public_endpoint = {key: value for key, value in endpoint.items() if key != "password_env"}
            (run / "endpoint.json").write_text(json.dumps(endpoint), encoding="utf-8")
            (run / "endpoint.json.binding.json").write_text(json.dumps({"format": "pietto.phase77.numeric_endpoint_binding.v1", "engine": "postgres", "manifest_sha256": digest(HERE / "manifest.json"), "probe_sha256": digest(HERE / "p77_mysql_numeric_probe.py"), "relay": str(HERE / "relay.py"), "relay_sha256": digest(HERE / "relay.py"), "ca_sha256": digest(HERE / "tls/ca.pem"), "endpoint": public_endpoint}), encoding="utf-8")
            (run / "bootstrap.json").write_text(json.dumps({"container": container, "role": "pietto_numeric_probe", "database": "pietto_numeric_probe", "relay_sha256": digest(HERE / "relay.py"), "endpoint": public_endpoint}), encoding="utf-8")
            plan_sha = hashlib.sha256((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")).hexdigest()
            (run / "numeric-receipt.json").write_text(json.dumps({"plan": str(HERE / "manifest.json"), "plan_sha256": plan_sha, "engine": "postgres", "terminal": {"kind": "success"}, "records": []}), encoding="utf-8")
            parent_receipt.main(raw, run, "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e", "none", container)
            judge(raw, run)
            endpoint["host"] = "127.0.0.2"
            (run / "endpoint.json").write_text(json.dumps(endpoint), encoding="utf-8")
            parent_receipt.main(raw, run, "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e", "none", container)
            try: judge(raw, run)
            except ValueError: pass
            else: raise AssertionError("endpoint/binding mismatch was accepted")
            endpoint["host"] = "127.0.0.1"
            (run / "endpoint.json").write_text(json.dumps(endpoint), encoding="utf-8")
            (run / "numeric-receipt.json").write_text(json.dumps({"plan": "wrong", "plan_sha256": plan_sha, "engine": "postgres", "terminal": {"kind": "success"}, "records": []}), encoding="utf-8")
            parent_receipt.main(raw, run, "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e", "none", container)
            try: judge(raw, run)
            except ValueError: pass
            else: raise AssertionError("numeric plan mismatch was accepted")
            (run / "numeric-receipt.json").write_text(json.dumps({"plan": str(HERE / "manifest.json"), "plan_sha256": "0" * 64, "engine": "postgres", "terminal": {"kind": "success"}, "records": []}), encoding="utf-8")
            parent_receipt.main(raw, run, "sha256:f372eda99ac2ea249c3dce566dcdf468397035371284d2cf2103b4bc52b3b39e", "none", container)
            try: judge(raw, run)
            except ValueError: pass
            else: raise AssertionError("numeric plan hash mismatch was accepted")
        finally:
            shutil.rmtree(run)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path, nargs="?")
    parser.add_argument("run", type=Path, nargs="?")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        print("numeric PostgreSQL parent judge self-check passed")
    elif args.raw and args.run:
        judge(args.raw, args.run)
    else:
        parser.error("provide RAW RUN or --self-check")


if __name__ == "__main__":
    main()
