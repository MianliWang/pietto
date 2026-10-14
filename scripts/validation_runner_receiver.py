"""Bounded VR1 candidate transport and non-authoritative evidence checks.

The successful terminals in this module deliberately do not qualify a runner
or accept a Gate 2 validation.  VR2 owns qualification and E* freezing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from typing import Any


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import ci_validation
from scripts import ci_workloads as workloads
from scripts import validate


ROOT = Path(__file__).resolve().parents[1]
FORMAT = "pietto.validation-runner.v1"
STATIC_FORMAT = "pietto.validation-runner-static.v1"
MATERIALIZATION_FORMAT = "pietto.validation-runner-materialization.v1"
ENVIRONMENT_FORMAT = "pietto.validation-runner-environment.v1"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_INVENTORY_ENTRIES = 100_000
REMOTE_PARTITIONS = (
    "shared-acquisition",
    "plan-portability",
    "emission-portability",
)
STATIC_GATES = tuple(name for name, _command in validate.GATES[:5])


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path, limit: int) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("file is not a bounded regular file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("nonfinite JSON constant: " + value)


def json_value(data: bytes, limit: int = MAX_MANIFEST_BYTES) -> object:
    if len(data) > limit:
        raise ValueError("JSON exceeds byte limit")
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=_nonfinite)


def json_bytes(data: bytes, limit: int = MAX_MANIFEST_BYTES) -> dict[str, Any]:
    value = json_value(data, limit)
    if type(value) is not dict:
        raise ValueError("JSON root must be an object")
    return value


def read_json(path: Path, limit: int = MAX_MANIFEST_BYTES) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("JSON must be a regular file")
    return json_bytes(path.read_bytes(), limit)


def read_value(path: Path, limit: int = MAX_MANIFEST_BYTES) -> object:
    if path.is_symlink() or not path.is_file():
        raise ValueError("JSON must be a regular file")
    return json_value(path.read_bytes(), limit)


def write_json(path: Path, value: object, limit: int = MAX_MANIFEST_BYTES) -> None:
    data = canonical(value)
    if len(data) > limit:
        raise ValueError("JSON exceeds byte limit")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


def exact(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("unknown, missing, or malformed " + label + " fields")
    return value


def oid(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError("invalid " + label)
    return value


def sha(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("invalid " + label)
    return value


def safe_path(value: object) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError("unsafe path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or str(path) != value
        or any(part in ("", ".", "..") for part in path.parts)
    ):
        raise ValueError("unsafe path")
    return value


def git(repo: Path, *args: str, data: bytes | None = None) -> str:
    return subprocess.check_output(
        ("git", *args), cwd=repo, input=data, text=data is None
    ).strip()


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(("git", *args), cwd=repo)


def git_status_paths(repo: Path) -> tuple[str, ...]:
    values: set[str] = set()
    for args in (
        ("diff", "--no-renames", "--name-only", "-z"),
        ("diff", "--cached", "--no-renames", "--name-only", "-z"),
        ("ls-files", "--others", "--exclude-standard", "-z"),
    ):
        values.update(
            safe_path(item.decode())
            for item in git_bytes(repo, *args).split(b"\0")
            if item
        )
    return tuple(sorted(values))


def candidate_tree(repo: Path, base: str, paths: tuple[str, ...]) -> str:
    if not paths:
        raise ValueError("candidate path set is empty")
    with tempfile.TemporaryDirectory(prefix="pietto-runner-index-") as name:
        index = Path(name) / "index"
        pathspec = Path(name) / "paths"
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        subprocess.run(("git", "read-tree", base), cwd=repo, env=env, check=True)
        pathspec.write_bytes(b"\0".join(path.encode() for path in paths) + b"\0")
        subprocess.run(
            (
                "git",
                "add",
                "-A",
                f"--pathspec-from-file={pathspec}",
                "--pathspec-file-nul",
            ),
            cwd=repo,
            env=env,
            check=True,
        )
        return subprocess.check_output(
            ("git", "write-tree"), cwd=repo, env=env, text=True
        ).strip()


def tree_inventory(repo: Path, tree: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in git_bytes(repo, "ls-tree", "-r", "-z", tree).split(b"\0"):
        if not item:
            continue
        left, raw_path = item.split(b"\t", 1)
        mode, kind, blob = left.decode().split(" ", 2)
        path = safe_path(raw_path.decode())
        if mode not in ("100644", "100755") or kind != "blob":
            raise ValueError("candidate tree has unsupported entry")
        rows.append({"path": path, "mode": mode, "blob": oid(blob, "inventory blob")})
    if (
        not rows
        or len(rows) > MAX_INVENTORY_ENTRIES
        or rows != sorted(rows, key=lambda row: row["path"])
    ):
        raise ValueError("invalid tree inventory")
    if len({row["path"] for row in rows}) != len(rows):
        raise ValueError("duplicate tree inventory path")
    return rows


def verify_inventory(value: object) -> list[dict[str, str]]:
    if type(value) is not list or not value or len(value) > MAX_INVENTORY_ENTRIES:
        raise ValueError("invalid source inventory")
    rows: list[dict[str, str]] = []
    for row in value:
        item = exact(row, {"path", "mode", "blob"}, "source inventory")
        if item["mode"] not in ("100644", "100755"):
            raise ValueError("unsupported source inventory mode")
        rows.append(
            {
                "path": safe_path(item["path"]),
                "mode": item["mode"],
                "blob": oid(item["blob"], "inventory blob"),
            }
        )
    if rows != sorted(rows, key=lambda row: row["path"]) or len(
        {row["path"] for row in rows}
    ) != len(rows):
        raise ValueError("noncanonical source inventory")
    return rows


def candidate_input_identity(repo: Path) -> str:
    saved = sys.modules.pop("_pietto_differential_process_acquisition", None)
    sys.path.insert(0, str(repo / "tests"))
    try:
        return workloads.input_identity(repo)
    finally:
        sys.path.pop(0)
        sys.modules.pop("_pietto_differential_process_acquisition", None)
        if saved is not None:
            sys.modules["_pietto_differential_process_acquisition"] = saved


def verify_collection_identity(value: object) -> dict[str, Any]:
    collection = exact(value, {"count", "sha256", "requirements_sha256"}, "collection")
    if type(collection["count"]) is not int or collection["count"] < 1:
        raise ValueError("invalid collection count")
    sha(collection["sha256"], "collection SHA-256")
    sha(collection["requirements_sha256"], "collection requirements SHA-256")
    return collection


def verify_remote_partitions(value: object) -> list[dict[str, Any]]:
    partitions = value
    if type(partitions) is not list or len(partitions) != len(REMOTE_PARTITIONS):
        raise ValueError("incomplete remote partition plan")
    seen_nodes: set[str] = set()
    for expected, row in zip(REMOTE_PARTITIONS, partitions, strict=True):
        item = exact(row, {"partition", "nodes", "indices"}, "remote partition")
        nodes = item["nodes"]
        indices = item["indices"]
        if (
            item["partition"] != expected
            or type(nodes) is not list
            or not nodes
            or nodes != sorted(set(nodes))
            or any(type(node) is not str or not node for node in nodes)
            or type(indices) is not list
            or len(indices) != len(nodes)
            or any(type(index) is not int or index < 0 for index in indices)
            or seen_nodes.intersection(nodes)
        ):
            raise ValueError("invalid remote partition plan")
        seen_nodes.update(nodes)
    return partitions


def derive_remote_partitions(
    collection: dict[str, Any], context: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    nodes = ci_validation.verify_report(collection, context, "collection")
    indices = collection["requirements"]["indices"]
    expected = ci_validation.partition_nodes(nodes, indices)
    by_node = dict(zip(nodes, indices, strict=True))
    remote = [
        {
            "partition": partition,
            "nodes": expected[partition],
            "indices": [by_node[node] for node in expected[partition]],
        }
        for partition in REMOTE_PARTITIONS
    ]
    return collection["collection"], verify_remote_partitions(remote)


def verify_manifest(value: object) -> dict[str, Any]:
    manifest = exact(
        value,
        {
            "format",
            "run",
            "candidate",
            "context",
            "policy",
            "inputs",
            "collection",
            "collection_report_sha256",
            "remote_partitions",
            "source",
            "runner_script_sha256",
            "lock_sha256",
        },
        "manifest",
    )
    if manifest["format"] != FORMAT:
        raise ValueError("wrong manifest format")
    run = exact(manifest["run"], {"id", "attempt"}, "run")
    if (
        type(run["id"]) is not str
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run["id"])
        or type(run["attempt"]) is not int
        or not 1 <= run["attempt"] <= 100
    ):
        raise ValueError("invalid run identity")
    candidate = exact(manifest["candidate"], {"base", "tree"}, "candidate")
    oid(candidate["base"], "baseline")
    oid(candidate["tree"], "candidate tree")
    context = exact(
        manifest["context"],
        {"checkout", "run_id", "run_attempt", "python", "python_version"},
        "context",
    )
    if (
        context["checkout"] != candidate["base"]
        or context["run_id"] != run["id"]
        or context["run_attempt"] != run["attempt"]
        or context["python"] != "3.13"
        or type(context["python_version"]) is not str
        or re.fullmatch(r"3\.13\.\d+", context["python_version"]) is None
    ):
        raise ValueError("invalid baseline provenance context")
    policy = exact(
        manifest["policy"], {"version", "topology_version", "sha256"}, "policy"
    )
    if (
        type(policy["version"]) is not int
        or type(policy["topology_version"]) is not int
    ):
        raise ValueError("invalid policy identity")
    sha(policy["sha256"], "policy SHA-256")
    sha(manifest["inputs"], "candidate input identity")
    verify_collection_identity(manifest["collection"])
    sha(manifest["collection_report_sha256"], "collection report SHA-256")
    verify_remote_partitions(manifest["remote_partitions"])
    source = exact(
        manifest["source"],
        {"archive_sha256", "inventory_sha256", "entry_count"},
        "source",
    )
    sha(source["archive_sha256"], "source archive SHA-256")
    sha(source["inventory_sha256"], "source inventory SHA-256")
    if (
        type(source["entry_count"]) is not int
        or not 1 <= source["entry_count"] <= MAX_INVENTORY_ENTRIES
    ):
        raise ValueError("invalid source inventory count")
    sha(manifest["runner_script_sha256"], "runner script SHA-256")
    sha(manifest["lock_sha256"], "uv.lock SHA-256")
    return manifest


def create_manifest(
    repo: Path,
    output: Path,
    paths: tuple[str, ...],
    collection_path: Path,
    run_id: str,
    attempt: int,
    python_version: str,
    runner_script: Path,
) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise ValueError("output directory must be fresh")
    actual_paths = git_status_paths(repo)
    if paths != actual_paths:
        raise ValueError(
            "candidate paths differ from the complete working tree change set"
        )
    base = oid(git(repo, "rev-parse", "HEAD"), "baseline")
    tree = oid(candidate_tree(repo, base, paths), "candidate tree")
    inventory = tree_inventory(repo, tree)
    expected_script = repo / "scripts" / "validation_runner_receiver.py"
    if runner_script.resolve() != expected_script.resolve():
        raise ValueError("runner script must be the candidate repository script")
    script_row = next(
        (
            row
            for row in inventory
            if row["path"] == "scripts/validation_runner_receiver.py"
        ),
        None,
    )
    if script_row is None or script_row["blob"] != git_hash_blob(
        expected_script.read_bytes()
    ):
        raise ValueError("runner script is not the candidate tree script")
    context = {
        "checkout": base,
        "run_id": run_id,
        "run_attempt": attempt,
        "python": "3.13",
        "python_version": python_version,
    }
    collection_bytes = collection_path.read_bytes()
    if len(collection_bytes) > ci_validation.MAX_REPORT_BYTES:
        raise ValueError("collection report exceeds byte limit")
    collection_report = ci_validation.read_report(collection_path)
    collection, remote_partitions = derive_remote_partitions(collection_report, context)
    output.mkdir(mode=0o700)
    archive = git_bytes(repo, "archive", "--format=tar", tree)
    if len(archive) > MAX_SOURCE_BYTES:
        raise ValueError("source archive exceeds byte limit")
    (output / "source.tar").write_bytes(archive)
    write_json(output / "source-tree.json", inventory, MAX_SOURCE_BYTES)
    with (output / "collection.json").open("xb") as stream:
        stream.write(collection_bytes)
    policy = workloads.policy_identity(
        workloads.load_policy(repo / "ci/workloads.toml")
    )
    manifest = {
        "format": FORMAT,
        "run": {"id": run_id, "attempt": attempt},
        "candidate": {"base": base, "tree": tree},
        "context": context,
        "policy": policy,
        "inputs": candidate_input_identity(repo),
        "collection": collection,
        "collection_report_sha256": digest_bytes(collection_bytes),
        "remote_partitions": remote_partitions,
        "source": {
            "archive_sha256": digest_bytes(archive),
            "inventory_sha256": digest_bytes(canonical(inventory)),
            "entry_count": len(inventory),
        },
        "runner_script_sha256": digest_bytes(runner_script.read_bytes()),
        "lock_sha256": file_digest(repo / "uv.lock", MAX_SOURCE_BYTES),
    }
    verify_manifest(manifest)
    write_json(output / "manifest.json", manifest)
    if candidate_tree(repo, base, paths) != tree:
        raise ValueError("candidate tree drifted while creating manifest")
    return manifest


def read_manifest(path: Path) -> dict[str, Any]:
    return verify_manifest(read_json(path))


def verify_collection_report(
    manifest: dict[str, Any], collection_path: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if (
        file_digest(collection_path, ci_validation.MAX_REPORT_BYTES)
        != manifest["collection_report_sha256"]
    ):
        raise ValueError("collection report differs from manifest")
    collection_report = ci_validation.read_report(collection_path)
    collection, remote = derive_remote_partitions(
        collection_report, manifest["context"]
    )
    if collection != manifest["collection"] or remote != manifest["remote_partitions"]:
        raise ValueError("collection report does not derive manifest partitions")
    return collection_report, remote


def verify_runner_script(manifest: dict[str, Any]) -> None:
    if (
        file_digest(Path(__file__).resolve(), MAX_SOURCE_BYTES)
        != manifest["runner_script_sha256"]
    ):
        raise ValueError("runner script differs from manifest")


def safe_archive_members(
    path: Path, inventory: list[dict[str, str]]
) -> dict[str, tuple[tarfile.TarInfo, bytes]]:
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size > MAX_SOURCE_BYTES
    ):
        raise ValueError("source archive is not a bounded regular file")
    expected = {row["path"]: row for row in inventory}
    expected_directories = {
        "/".join(PurePosixPath(name).parts[:index])
        for name in expected
        for index in range(1, len(PurePosixPath(name).parts))
    }
    result: dict[str, tuple[tarfile.TarInfo, bytes]] = {}
    directories: set[str] = set()
    with tarfile.open(path, "r:") as archive:
        members = archive.getmembers()
        if len(members) != len(expected) + len(expected_directories):
            raise ValueError("source archive member count differs from inventory")
        for member in members:
            name = safe_path(member.name)
            if member.isdir():
                if name not in expected_directories or name in directories:
                    raise ValueError("unsafe or foreign source archive directory")
                directories.add(name)
                continue
            row = expected.get(name)
            if row is None or name in result or not member.isfile() or member.size < 0:
                raise ValueError("unsafe or foreign source archive member")
            if bool(member.mode & 0o111) != (row["mode"] == "100755"):
                raise ValueError(
                    "source archive executable mode differs from inventory"
                )
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("source archive member is unreadable")
            data = stream.read(member.size + 1)
            if len(data) != member.size or digest_bytes(data) == "":
                raise ValueError("source archive member is truncated")
            blob = git_hash_blob(data)
            if blob != row["blob"]:
                raise ValueError("source archive blob differs from inventory")
            result[name] = (member, data)
    if set(result) != set(expected) or directories != expected_directories:
        raise ValueError("source archive does not close inventory")
    return result


def git_hash_blob(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def ensure_parent_regular(root: Path, path: str) -> Path:
    target = root / path
    parent = target.parent
    relative = parent.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if current.exists() and current.is_symlink():
            raise ValueError("source path crosses a symlink")
        current.mkdir(mode=0o755, exist_ok=True)
    return target


def rebuilt_tree(repo: Path, base: str, inventory: list[dict[str, str]]) -> str:
    baseline = tree_inventory(repo, base)
    paths = tuple(
        sorted({row["path"] for row in baseline} | {row["path"] for row in inventory})
    )
    return candidate_tree(repo, base, paths)


def materialize_candidate(
    repo: Path, manifest: dict[str, Any], archive: Path, inventory: list[dict[str, str]]
) -> dict[str, Any]:
    base = manifest["candidate"]["base"]
    if git(repo, "rev-parse", "HEAD") != base or git(
        repo, "status", "--porcelain", "--untracked-files=all"
    ):
        raise ValueError("remote baseline checkout is not clean")
    inventory = verify_inventory(inventory)
    if (
        len(inventory) != manifest["source"]["entry_count"]
        or digest_bytes(canonical(inventory)) != manifest["source"]["inventory_sha256"]
    ):
        raise ValueError("source inventory differs from manifest")
    if file_digest(archive, MAX_SOURCE_BYTES) != manifest["source"]["archive_sha256"]:
        raise ValueError("source archive differs from manifest")
    members = safe_archive_members(archive, inventory)
    baseline = tree_inventory(repo, base)
    candidate_paths = {row["path"] for row in inventory}
    for row in baseline:
        if row["path"] not in candidate_paths:
            target = ensure_parent_regular(repo, row["path"])
            if target.is_symlink() or not target.is_file():
                raise ValueError("baseline deletion target is not a regular file")
            target.unlink()
    for row in inventory:
        target = ensure_parent_regular(repo, row["path"])
        if target.exists() or target.is_symlink():
            if target.is_dir() or target.is_symlink():
                raise ValueError("source target is not a replaceable regular file")
            target.unlink()
        member, data = members[row["path"]]
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(int(row["mode"], 8) & 0o777)
    rebuilt = rebuilt_tree(repo, base, inventory)
    if rebuilt != manifest["candidate"]["tree"]:
        raise ValueError("remote source tree differs from candidate tree")
    inputs = candidate_input_identity(repo)
    if inputs != manifest["inputs"]:
        raise ValueError("remote candidate input identity differs from manifest")
    return {
        "format": MATERIALIZATION_FORMAT,
        "status": "MATERIALIZED_NOT_QUALIFIED",
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": inputs,
        "rebuilt_tree": rebuilt,
        "archive_sha256": manifest["source"]["archive_sha256"],
        "inventory_sha256": manifest["source"]["inventory_sha256"],
    }


def verify_materialization(value: object, manifest: dict[str, Any]) -> dict[str, Any]:
    proof = exact(
        value,
        {
            "format",
            "status",
            "candidate",
            "context",
            "inputs",
            "rebuilt_tree",
            "archive_sha256",
            "inventory_sha256",
        },
        "materialization",
    )
    if (
        proof["format"] != MATERIALIZATION_FORMAT
        or proof["status"] != "MATERIALIZED_NOT_QUALIFIED"
    ):
        raise ValueError("wrong materialization terminal")
    if (
        proof["candidate"] != manifest["candidate"]
        or proof["context"] != manifest["context"]
        or proof["inputs"] != manifest["inputs"]
        or proof["rebuilt_tree"] != manifest["candidate"]["tree"]
        or proof["archive_sha256"] != manifest["source"]["archive_sha256"]
        or proof["inventory_sha256"] != manifest["source"]["inventory_sha256"]
    ):
        raise ValueError("foreign materialization proof")
    oid(proof["rebuilt_tree"], "rebuilt tree")
    sha(proof["inputs"], "materialized input identity")
    sha(proof["archive_sha256"], "materialized archive SHA-256")
    sha(proof["inventory_sha256"], "materialized inventory SHA-256")
    return proof


def static_report(
    manifest: dict[str, Any], results: list[tuple[str, tuple[str, ...], int, float]]
) -> dict[str, Any]:
    if len(results) != len(validate.GATES[:5]):
        raise ValueError("incomplete static gate results")
    gates = []
    for (expected_name, expected_command), (name, command, exit_code, elapsed) in zip(
        validate.GATES[:5], results, strict=True
    ):
        if (
            name != expected_name
            or command != expected_command
            or type(exit_code) is not int
            or type(elapsed) not in (int, float)
            or not math.isfinite(elapsed)
            or elapsed < 0
        ):
            raise ValueError("foreign static gate result")
        gates.append(
            {
                "name": name,
                "command": list(command),
                "exit_code": exit_code,
                "elapsed_seconds": float(elapsed),
            }
        )
    return {
        "format": STATIC_FORMAT,
        "status": "success"
        if all(row["exit_code"] == 0 for row in gates)
        else "failed",
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": manifest["inputs"],
        "policy": manifest["policy"],
        "gates": gates,
    }


def verify_static(value: object, manifest: dict[str, Any]) -> dict[str, Any]:
    report = exact(
        value,
        {"format", "status", "candidate", "context", "inputs", "policy", "gates"},
        "static report",
    )
    if report["format"] != STATIC_FORMAT or report["status"] != "success":
        raise ValueError("static gates did not succeed")
    if any(
        report[field] != manifest[field]
        for field in ("candidate", "context", "inputs", "policy")
    ):
        raise ValueError("foreign static report")
    gates = report["gates"]
    if type(gates) is not list or len(gates) != len(validate.GATES[:5]):
        raise ValueError("incomplete static gate report")
    for row, (name, command) in zip(gates, validate.GATES[:5], strict=True):
        item = exact(
            row, {"name", "command", "exit_code", "elapsed_seconds"}, "static gate"
        )
        if (
            item["name"] != name
            or item["command"] != list(command)
            or item["exit_code"] != 0
            or type(item["elapsed_seconds"]) not in (int, float)
            or not math.isfinite(item["elapsed_seconds"])
            or item["elapsed_seconds"] < 0
        ):
            raise ValueError("invalid static gate report")
    return report


def run_static(
    manifest: dict[str, Any],
    repo: Path,
    guard: str,
    inventory: list[dict[str, str]],
    materialization: object,
) -> dict[str, Any]:
    if ROOT.resolve() != repo.resolve():
        raise ValueError("static producer must run from the materialized repository")
    verify_runner_script(manifest)
    verify_materialization(materialization, manifest)
    if git(repo, "rev-parse", "HEAD") != manifest["candidate"]["base"]:
        raise ValueError("static producer baseline differs from manifest")
    if (
        rebuilt_tree(repo, manifest["candidate"]["base"], verify_inventory(inventory))
        != manifest["candidate"]["tree"]
    ):
        raise ValueError("static producer tree differs from manifest")
    if candidate_input_identity(repo) != manifest["inputs"]:
        raise ValueError("static producer inputs differ from manifest")
    results = []
    for name, command in validate.GATES[:5]:
        started = time.monotonic()
        exit_code = ci_validation.run_gate(name, command, guard)
        results.append((name, command, exit_code, time.monotonic() - started))
    if (
        rebuilt_tree(repo, manifest["candidate"]["base"], verify_inventory(inventory))
        != manifest["candidate"]["tree"]
        or candidate_input_identity(repo) != manifest["inputs"]
    ):
        raise ValueError("static gates changed the candidate inputs")
    return static_report(manifest, results)


def verify_environment(value: object, manifest: dict[str, Any]) -> dict[str, Any]:
    record = exact(
        value,
        {
            "format",
            "candidate",
            "context",
            "inputs",
            "interpreter",
            "tooling",
            "history_complete",
            "storage_class",
            "credential_env_names",
        },
        "environment observation",
    )
    if record["format"] != ENVIRONMENT_FORMAT:
        raise ValueError("wrong environment observation format")
    if any(
        record[field] != manifest[field] for field in ("candidate", "context", "inputs")
    ):
        raise ValueError("foreign environment observation")
    interpreter = exact(
        record["interpreter"],
        {"implementation", "python_version", "path_python312"},
        "interpreter",
    )
    tooling = exact(
        record["tooling"],
        {
            "node_version",
            "java_version",
            "uv_lock_sha256",
            "offline_cache_sha256",
            "runner_script_sha256",
        },
        "tooling",
    )
    if (
        interpreter["implementation"] != "CPython"
        or interpreter["python_version"] != manifest["context"]["python_version"]
        or interpreter["path_python312"] != "3.12.13"
        or type(tooling["node_version"]) is not str
        or not tooling["node_version"]
        or tooling["java_version"] != "21"
        or tooling["runner_script_sha256"] != manifest["runner_script_sha256"]
        or tooling["uv_lock_sha256"] != manifest["lock_sha256"]
        or record["history_complete"] is not True
        or record["storage_class"] != "report"
        or record["credential_env_names"] != []
    ):
        raise ValueError("environment assertion is invalid")
    sha(tooling["uv_lock_sha256"], "uv.lock SHA-256")
    sha(tooling["offline_cache_sha256"], "offline cache SHA-256")
    return {"status": "ASSERTED_NOT_QUALIFIED", "record": record}


def verify_received(
    manifest: dict[str, Any],
    materialization: object,
    static: object,
    reports: dict[str, dict[str, Any]],
    repo: Path,
    inventory: list[dict[str, str]],
    collection_report: dict[str, Any],
) -> dict[str, Any]:
    verify_materialization(materialization, manifest)
    verify_static(static, manifest)
    if (
        rebuilt_tree(repo, manifest["candidate"]["base"], verify_inventory(inventory))
        != manifest["candidate"]["tree"]
    ):
        raise ValueError("integration-host candidate tree drifted")
    if candidate_input_identity(repo) != manifest["inputs"]:
        raise ValueError("integration-host candidate inputs drifted")
    collection, remote = derive_remote_partitions(
        collection_report, manifest["context"]
    )
    if collection != manifest["collection"] or remote != manifest["remote_partitions"]:
        raise ValueError("full collection does not derive manifest partitions")
    expected = {row["partition"]: row for row in remote}
    if set(reports) != set(REMOTE_PARTITIONS):
        raise ValueError("missing or foreign remote coverage reports")
    for partition in REMOTE_PARTITIONS:
        report = reports[partition]
        ci_validation.verify_report(report, manifest["context"], "partition")
        row = expected[partition]
        if (
            report["partition"] != partition
            or report["collection"] != collection
            or report["nodes"] != row["nodes"]
            or report["requirements"]["indices"] != row["indices"]
            or report["inputs"] != manifest["inputs"]
            or any("PIETTO_NOT_RUN" in reason for _index, reason in report["skips"])
        ):
            raise ValueError("foreign or incomplete remote coverage report")
    return {
        "status": "RECEIVED_NOT_QUALIFIED",
        "candidate": manifest["candidate"],
        "partitions": list(REMOTE_PARTITIONS),
    }


def receive_from_directory(
    repo: Path,
    manifest: dict[str, Any],
    inventory: list[dict[str, str]],
    materialization_path: Path,
    static_path: Path,
    collection_path: Path,
    reports_dir: Path,
) -> dict[str, Any]:
    if ROOT.resolve() != repo.resolve():
        raise ValueError("receiver must run from the integration-host repository")
    verify_runner_script(manifest)
    if reports_dir.is_symlink() or not reports_dir.is_dir():
        raise ValueError("report directory is not a real directory")
    expected_names = {
        ci_validation.report_name(manifest["context"], partition)
        for partition in REMOTE_PARTITIONS
    }
    if {path.name for path in reports_dir.iterdir()} != expected_names:
        raise ValueError("missing or foreign remote report files")
    reports = {
        partition: ci_validation.read_report(
            reports_dir / ci_validation.report_name(manifest["context"], partition)
        )
        for partition in REMOTE_PARTITIONS
    }
    collection_report, _remote = verify_collection_report(manifest, collection_path)
    return verify_received(
        manifest,
        read_json(materialization_path),
        read_json(static_path),
        reports,
        repo,
        inventory,
        collection_report,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    create = sub.add_parser("create")
    create.add_argument("--repo", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--paths", type=Path, required=True)
    create.add_argument("--collection", type=Path, required=True)
    create.add_argument("--run-id", required=True)
    create.add_argument("--attempt", type=int, required=True)
    create.add_argument("--python-version", required=True)
    create.add_argument("--runner-script", type=Path, default=Path(__file__))
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--repo", type=Path, required=True)
    materialize.add_argument("--manifest", type=Path, required=True)
    materialize.add_argument("--archive", type=Path, required=True)
    materialize.add_argument("--inventory", type=Path, required=True)
    materialize.add_argument("--output", type=Path, required=True)
    static = sub.add_parser("static")
    static.add_argument("--repo", type=Path, required=True)
    static.add_argument("--manifest", type=Path, required=True)
    static.add_argument("--inventory", type=Path, required=True)
    static.add_argument("--materialization", type=Path, required=True)
    static.add_argument("--output", type=Path, required=True)
    static.add_argument("--oom-guard", choices=("on", "off"), required=True)
    predicate = sub.add_parser("predicate")
    predicate.add_argument("--manifest", type=Path, required=True)
    predicate.add_argument("--environment", type=Path, required=True)
    receive = sub.add_parser("receive")
    receive.add_argument("--repo", type=Path, required=True)
    receive.add_argument("--manifest", type=Path, required=True)
    receive.add_argument("--inventory", type=Path, required=True)
    receive.add_argument("--materialization", type=Path, required=True)
    receive.add_argument("--static", type=Path, required=True)
    receive.add_argument("--collection", type=Path, required=True)
    receive.add_argument("--reports-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "create":
            paths = tuple(
                safe_path(line) for line in args.paths.read_text().splitlines() if line
            )
            if paths != tuple(sorted(set(paths))):
                raise ValueError("candidate paths must be sorted and unique")
            value = create_manifest(
                args.repo,
                args.output,
                paths,
                args.collection,
                args.run_id,
                args.attempt,
                args.python_version,
                args.runner_script,
            )
            print(
                json.dumps(
                    {
                        "status": "CREATED_NOT_QUALIFIED",
                        "candidate": value["candidate"],
                    },
                    sort_keys=True,
                )
            )
        elif args.action == "materialize":
            manifest = read_manifest(args.manifest)
            inventory = verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES))
            if (
                digest_bytes(canonical(inventory))
                != manifest["source"]["inventory_sha256"]
            ):
                raise ValueError("inventory digest differs from manifest")
            proof = materialize_candidate(args.repo, manifest, args.archive, inventory)
            write_json(args.output, proof)
            print(
                json.dumps(
                    {"status": proof["status"], "rebuilt_tree": proof["rebuilt_tree"]},
                    sort_keys=True,
                )
            )
        elif args.action == "static":
            manifest = read_manifest(args.manifest)
            inventory = verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES))
            proof = read_json(args.materialization)
            report = run_static(manifest, args.repo, args.oom_guard, inventory, proof)
            write_json(args.output, report)
            print(json.dumps({"status": report["status"]}, sort_keys=True))
        elif args.action == "predicate":
            result = verify_environment(
                read_json(args.environment), read_manifest(args.manifest)
            )
            print(json.dumps({"status": result["status"]}, sort_keys=True))
        else:
            manifest = read_manifest(args.manifest)
            inventory = verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES))
            result = receive_from_directory(
                args.repo,
                manifest,
                inventory,
                args.materialization,
                args.static,
                args.collection,
                args.reports_dir,
            )
            print(json.dumps(result, sort_keys=True))
        return 0
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        tarfile.TarError,
        json.JSONDecodeError,
    ) as error:
        print(
            "[validation-runner] rejected: " + json.dumps(str(error)), file=sys.stderr
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
