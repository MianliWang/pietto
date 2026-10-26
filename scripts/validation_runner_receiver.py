"""Bounded candidate transport and validation-runner acceptance checks.

VR1 entrypoints retain their deliberately non-qualified terminals.  The
separate VR2 acceptance entrypoint only accepts successor candidates after the
integration host has recorded a successful natural-CI bootstrap publication.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
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
BOOTSTRAP_FORMAT = "pietto.validation-runner-bootstrap.v1"
ACCEPTANCE_PLAN_FORMAT = "pietto.validation-runner-plan.v1"
ACCEPTANCE_RECEIPT_FORMAT = "pietto.validation-runner-receipt.v1"
REQUIREMENTS_FORMAT = "pietto.validation-runner-requirements.v1"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_INVENTORY_ENTRIES = 100_000
MAX_ACCEPTANCE_BYTES = 64 * 1024 * 1024
REMOTE_PARTITIONS = (
    "shared-acquisition",
    "plan-portability",
    "emission-portability",
)
STATIC_GATES = tuple(name for name, _command in validate.GATES[:5])
TEACH_RUNNER_CATEGORY = "owner-controlled-teach"
LOCAL_ACCEPTANCE_FILES = frozenset({"tests/test_harness_validation_runner_receiver.py"})
ACCEPTANCE_RULE_PATHS = (
    ".github/workflows/ci.yml",
    "ci/workloads.toml",
    "scripts/ci_workloads.py",
    "scripts/validate.py",
    "scripts/ci_validation.py",
    "scripts/validation_runner_receiver.py",
    "docs/development.md",
    "docs/spec/validation-runner-acceptance-v1.md",
)


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
    environment: dict[str, str] | None = None,
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
        exit_code = (
            ci_validation.run_gate(name, command, guard)
            if environment is None
            else subprocess.run(
                command, cwd=repo, env=environment, check=False
            ).returncode
        )
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


def verify_bootstrap(
    value: object, manifest: dict[str, Any], repo: Path
) -> dict[str, Any]:
    """Bind a successor candidate to the host-recorded first publication.

    The record is an integration-host observation of GitHub's natural CI, not
    an assertion made by Teach.  It deliberately contains the complete job
    result list so a partial workflow cannot activate the split.
    """

    record = exact(
        value,
        {"format", "published", "adopted", "natural_ci"},
        "bootstrap record",
    )
    published = exact(record["published"], {"head", "tree"}, "published head")
    adopted = exact(record["adopted"], {"blobs"}, "adopted acceptance rules")
    natural = exact(
        record["natural_ci"],
        {
            "run_id",
            "event",
            "branch",
            "head",
            "attempt",
            "status",
            "conclusion",
            "jobs",
            "workflow",
        },
        "natural CI",
    )
    workflow = exact(natural["workflow"], {"id", "path", "blob"}, "CI workflow")
    if (
        type(workflow["id"]) is not int
        or workflow["id"] <= 0
        or workflow["path"] != ".github/workflows/ci.yml"
    ):
        raise ValueError("invalid bootstrap workflow identity")
    oid(workflow["blob"], "published workflow blob")
    if (
        record["format"] != BOOTSTRAP_FORMAT
        or oid(published["head"], "published head") != published["head"]
        or oid(published["tree"], "published tree") != published["tree"]
        or natural["head"] != published["head"]
        or type(natural["run_id"]) is not int
        or natural["run_id"] <= 0
        or natural["event"] != "push"
        or natural["branch"] != "main"
        or natural["attempt"] != 1
        or natural["status"] != "completed"
        or natural["conclusion"] != "success"
        or type(natural["jobs"]) is not list
        or not natural["jobs"]
    ):
        raise ValueError("invalid bootstrap natural CI observation")
    names: set[str] = set()
    for job in natural["jobs"]:
        item = exact(job, {"name", "conclusion"}, "natural CI job")
        if (
            type(item["name"]) is not str
            or not item["name"]
            or item["name"] in names
            or item["conclusion"] != "success"
        ):
            raise ValueError("incomplete bootstrap natural CI jobs")
        names.add(item["name"])
    if git(repo, "rev-parse", published["head"] + "^{tree}") != published["tree"]:
        raise ValueError("published bootstrap tree differs from repository")
    blobs = adopted["blobs"]
    if type(blobs) is not list or len(blobs) != len(ACCEPTANCE_RULE_PATHS):
        raise ValueError("incomplete adopted acceptance rules")
    published_inventory = {
        row["path"]: row["blob"] for row in tree_inventory(repo, published["tree"])
    }
    candidate_inventory = {
        row["path"]: row["blob"]
        for row in tree_inventory(repo, manifest["candidate"]["tree"])
    }
    if published_inventory.get(workflow["path"]) != workflow["blob"]:
        raise ValueError("bootstrap workflow differs from published policy")
    for path, row in zip(ACCEPTANCE_RULE_PATHS, blobs, strict=True):
        item = exact(row, {"path", "blob"}, "adopted acceptance rule")
        if item["path"] != path or published_inventory.get(path) != oid(
            item["blob"], "adopted rule blob"
        ):
            raise ValueError("bootstrap did not publish accepted rule bytes")
        if candidate_inventory.get(path) != item["blob"]:
            raise ValueError("candidate changes adopted acceptance rule bytes")
    if manifest["candidate"]["tree"] == published["tree"]:
        raise ValueError("bootstrap publication cannot qualify itself")
    if subprocess.run(
        (
            "git",
            "merge-base",
            "--is-ancestor",
            published["head"],
            manifest["candidate"]["base"],
        ),
        cwd=repo,
        check=False,
    ).returncode:
        raise ValueError("candidate does not succeed bootstrap publication")
    return record


def _github_repository(repo: Path) -> str:
    remote = git(repo, "remote", "get-url", "origin")
    match = re.fullmatch(
        r"(?:git@github\.com:|https://github\.com/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?",
        remote,
    )
    if match is None:
        raise ValueError("origin is not a GitHub repository")
    return match.group(1)


def observe_bootstrap(repo: Path, run_id: int, token: str) -> dict[str, Any]:
    """Read the published exact-head natural-CI result on the host.

    This is intentionally a bounded GitHub read, reusing the repository's
    existing read-only Actions transport.  A hand-written success object never
    reaches this producer.
    """

    if type(run_id) is not int or run_id <= 0 or not token:
        raise ValueError("missing bootstrap run identity or read-only token")
    repository = _github_repository(repo)
    published = oid(
        git(repo, "rev-parse", "refs/remotes/origin/main"), "published main"
    )
    tree = oid(git(repo, "rev-parse", published + "^{tree}"), "published tree")
    inventory = {row["path"]: row["blob"] for row in tree_inventory(repo, tree)}
    deadline = time.monotonic() + 40

    def api(path: str) -> dict[str, Any]:
        return workloads.json_bytes(
            workloads.github_bytes(
                path, token, 2 * workloads.MAX_HEALTH_BYTES, deadline
            ),
            2 * workloads.MAX_HEALTH_BYTES,
        )

    prefix = f"repos/{repository}/actions/runs/{run_id}"
    reference = api(f"repos/{repository}/git/ref/heads/main")
    workflow = api(f"repos/{repository}/actions/workflows/ci.yml")
    run = api(prefix)
    jobs = api(prefix + "/attempts/1/jobs?per_page=100")
    records = jobs.get("jobs")
    reference_object = reference.get("object")
    if (
        type(reference_object) is not dict
        or reference.get("ref") != "refs/heads/main"
        or reference_object.get("type") != "commit"
        or reference_object.get("sha") != published
        or type(workflow.get("id")) is not int
        or workflow["id"] <= 0
        or workflow.get("path") != ".github/workflows/ci.yml"
        or run.get("workflow_id") != workflow["id"]
        or run.get("path") != workflow["path"]
    ):
        raise ValueError("natural CI workflow or published branch identity differs")
    if (
        run.get("id") != run_id
        or run.get("event") != "push"
        or run.get("head_branch") != "main"
        or run.get("head_sha") != published
        or run.get("run_attempt") != 1
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or type(run.get("repository")) is not dict
        or run["repository"].get("full_name") != repository
        or type(records) is not list
        or not records
        or jobs.get("total_count") != len(records)
        or any(
            type(job) is not dict
            or job.get("status") != "completed"
            or job.get("conclusion") != "success"
            or job.get("run_id") != run_id
            or job.get("head_sha") != published
            or job.get("run_attempt") != 1
            for job in records
        )
    ):
        raise ValueError("published natural CI did not close every consumer")
    names = [job.get("name") for job in records]
    if any(type(name) is not str or not name for name in names) or len(
        set(names)
    ) != len(names):
        raise ValueError("natural CI job identity is malformed")
    expected_jobs = {
        "Compiler / Package 3.12",
        "Compiler / Package 3.13",
        "Python 3.12",
        "Python 3.13",
        "Target postgres",
        "Target mysql",
        "Target conformance aggregate",
        *{
            f"Runtime {python} / {partition}"
            for python in ("3.12", "3.13")
            for partition in ci_validation.PARTITIONS
        },
    }
    if set(names) != expected_jobs:
        raise ValueError(
            "natural CI job inventory differs from required workflow consumers"
        )
    if any(path not in inventory for path in ACCEPTANCE_RULE_PATHS):
        raise ValueError("published bootstrap lacks acceptance rule bytes")
    return {
        "format": BOOTSTRAP_FORMAT,
        "published": {"head": published, "tree": tree},
        "adopted": {
            "blobs": [
                {"path": path, "blob": inventory[path]}
                for path in ACCEPTANCE_RULE_PATHS
            ]
        },
        "natural_ci": {
            "workflow": {
                "id": workflow["id"],
                "path": workflow["path"],
                "blob": inventory[workflow["path"]],
            },
            "run_id": run_id,
            "event": "push",
            "branch": "main",
            "head": published,
            "attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "jobs": [{"name": name, "conclusion": "success"} for name in sorted(names)],
        },
    }


def acceptance_requirements(
    manifest: dict[str, Any],
    collection_report: dict[str, Any],
    marks: dict[str, list[tuple[tuple, dict[str, Any]]]],
) -> dict[str, Any]:
    """Capture marker provenance without changing CI placement or reports."""

    collection, _old_remote = derive_remote_partitions(
        collection_report, manifest["context"]
    )
    nodes = ci_validation.verify_report(
        collection_report, manifest["context"], "collection"
    )
    policy = workloads.load_policy(ROOT / "ci/workloads.toml")
    indices = workloads.resolve(policy, nodes, marks)
    if indices != collection_report["requirements"]["indices"]:
        raise ValueError("acceptance marker requirements differ from collection")
    return {
        "format": REQUIREMENTS_FORMAT,
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": manifest["inputs"],
        "policy": manifest["policy"],
        "collection": collection,
        "nodes": [
            {"node": node, "index": index, "explicit": bool(marks.get(node))}
            for node, index in zip(nodes, indices, strict=True)
        ],
    }


def capture_acceptance_requirements(
    repo: Path,
    manifest: dict[str, Any],
    collection_path: Path,
    output: Path,
) -> dict[str, Any]:
    """Collect the current ``ci_workload`` marker provenance on the host."""

    if output.exists() or output.is_symlink():
        raise ValueError("acceptance requirements output must be fresh")
    if ROOT.resolve() != repo.resolve():
        raise ValueError("requirements collector must run from candidate repository")
    if (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        != manifest["context"]["python_version"]
    ):
        raise ValueError("requirements collector interpreter differs from manifest")
    verify_runner_script(manifest)
    collection_report, _remote = verify_collection_report(manifest, collection_path)
    with tempfile.TemporaryDirectory(prefix="pietto-runner-requirements-") as name:
        raw_path = Path(name) / "requirements.json"
        environment = dict(os.environ)
        environment.pop("PYTEST_ADDOPTS", None)
        environment.pop("PYTEST_PLUGINS", None)
        subprocess.run(
            (
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-qq",
                "-p",
                "scripts.validation_runner_receiver",
                "--validation-runner-requirements",
                str(raw_path),
            ),
            cwd=repo,
            env=environment,
            check=True,
        )
        raw = read_json(raw_path, MAX_ACCEPTANCE_BYTES)
    marks = exact(raw, {"nodes"}, "captured marker requirements")["nodes"]
    if type(marks) is not dict:
        raise ValueError("captured marker requirements are malformed")
    normalized: dict[str, list[tuple[tuple, dict[str, Any]]]] = {}
    for node, values in marks.items():
        if type(node) is not str or type(values) is not list:
            raise ValueError("captured marker requirements are malformed")
        normalized[node] = []
        for value in values:
            item = exact(value, {"args", "kwargs"}, "captured ci_workload marker")
            if type(item["args"]) is not list or type(item["kwargs"]) is not dict:
                raise ValueError("captured ci_workload marker is malformed")
            normalized[node].append((tuple(item["args"]), item["kwargs"]))
    result = acceptance_requirements(manifest, collection_report, normalized)
    write_json(output, result, MAX_ACCEPTANCE_BYTES)
    return result


def acceptance_plan(
    manifest: dict[str, Any],
    collection_report: dict[str, Any],
    requirements: object,
) -> dict[str, Any]:
    """Derive the local complement from explicit existing workload markers.

    Default workload placement is deliberately not remote authority.  Only an
    explicit ``ci_workload('general-runtime')`` declaration whose resolved
    descriptor is the ordinary core descriptor can be sent to Teach.  Every
    unmarked or special descriptor stays on the integration host.  This leaves
    CI placement untouched while making the selection current-collection data.
    """

    collection, _old_remote = derive_remote_partitions(
        collection_report, manifest["context"]
    )
    nodes = ci_validation.verify_report(
        collection_report, manifest["context"], "collection"
    )
    indices = collection_report["requirements"]["indices"]
    evidence = exact(
        requirements,
        {"format", "candidate", "context", "inputs", "policy", "collection", "nodes"},
        "acceptance requirements",
    )
    if (
        evidence["format"] != REQUIREMENTS_FORMAT
        or any(
            evidence[name] != manifest[name]
            for name in ("candidate", "context", "inputs", "policy", "collection")
        )
        or type(evidence["nodes"]) is not list
        or len(evidence["nodes"]) != len(nodes)
    ):
        raise ValueError("foreign acceptance requirements")
    policy = workloads.load_policy(ROOT / "ci/workloads.toml")
    core_index = workloads.table(policy).index(
        workloads.declared(policy, "general-runtime", {})
    )
    remote_nodes: set[str] = set()
    for expected_node, expected_index, row in zip(
        nodes, indices, evidence["nodes"], strict=True
    ):
        item = exact(row, {"node", "index", "explicit"}, "acceptance requirement")
        if (
            item["node"] != expected_node
            or item["index"] != expected_index
            or type(item["explicit"]) is not bool
        ):
            raise ValueError("acceptance requirements differ from collection")
        if (
            item["explicit"]
            and item["index"] == core_index
            and expected_node.split("::", 1)[0] not in LOCAL_ACCEPTANCE_FILES
        ):
            remote_nodes.add(expected_node)
    by_node = dict(zip(nodes, indices, strict=True))
    placed = ci_validation.partition_nodes(nodes, indices)

    def owner_rows(remote: bool) -> list[dict[str, Any]]:
        return [
            {
                "partition": partition,
                "nodes": [
                    node
                    for node in placed[partition]
                    if (node in remote_nodes) == remote
                ],
                "indices": [
                    by_node[node]
                    for node in placed[partition]
                    if (node in remote_nodes) == remote
                ],
            }
            for partition in ci_validation.PARTITIONS
        ]

    return {
        "format": ACCEPTANCE_PLAN_FORMAT,
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": manifest["inputs"],
        "policy": manifest["policy"],
        "collection": collection,
        "domain": collection_report["domain"],
        "remote": owner_rows(True),
        "local": owner_rows(False),
    }


def verify_acceptance_plan(
    value: object,
    manifest: dict[str, Any],
    collection_report: dict[str, Any],
    requirements: object,
) -> dict[str, Any]:
    plan = exact(
        value,
        {
            "format",
            "candidate",
            "context",
            "inputs",
            "policy",
            "collection",
            "domain",
            "remote",
            "local",
        },
        "acceptance plan",
    )
    if plan["format"] != ACCEPTANCE_PLAN_FORMAT or any(
        plan[name] != manifest[name]
        for name in ("candidate", "context", "inputs", "policy", "collection")
    ):
        raise ValueError("foreign acceptance plan")
    expected = acceptance_plan(manifest, collection_report, requirements)
    if plan != expected:
        raise ValueError("acceptance plan does not close current collection")
    return plan


def verify_execution_tree(
    repo: Path, manifest: dict[str, Any], inventory: list[dict[str, str]]
) -> None:
    """Check the complete candidate before and after every accepted producer step."""

    verify_runner_script(manifest)
    if (
        rebuilt_tree(repo, manifest["candidate"]["base"], verify_inventory(inventory))
        != manifest["candidate"]["tree"]
        or candidate_input_identity(repo) != manifest["inputs"]
    ):
        raise ValueError("producer candidate differs from manifest")


def qualified_storage_environment(repo: Path, temp_root: Path) -> dict[str, str]:
    """Run the existing qualified-storage probe with the selected interpreter."""

    environment = dict(os.environ)
    declared = environment.get("PIETTO_STORAGE_CLASS")
    if declared is not None and declared != "qualified":
        raise ValueError("host local complement storage class conflicts with qualified")
    environment["PIETTO_STORAGE_CLASS"] = "qualified"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(repo / "src")
    if temp_root.is_symlink() or not temp_root.is_dir():
        raise ValueError("host local complement pytest root is not a real directory")
    environment["PYTEST_DEBUG_TEMPROOT"] = str(temp_root.resolve())
    completed = subprocess.run(
        (sys.executable, "-c", validate.STORAGE_PRECHECK),
        cwd=repo,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode:
        raise ValueError("host local complement storage precheck refused")
    return environment


def teach_environment(repo: Path) -> dict[str, str]:
    """Reject credentials and pass only the fixed validation-job environment."""

    forbidden = [
        name
        for name in os.environ
        if (
            name in {"SSH_AUTH_SOCK", "GITHUB_TOKEN", "GH_TOKEN"}
            or "TOKEN" in name
            or "SECRET" in name
            or name.endswith("_KEY")
        )
    ]
    if forbidden:
        raise ValueError("Teach job environment exposes credential names")
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "TZ", "TMPDIR", "UV_CACHE_DIR")
    result = {name: os.environ[name] for name in allowed if name in os.environ}
    for name in ("HOME", "TMPDIR", "UV_CACHE_DIR"):
        value = result.get(name)
        if not value or not Path(value).is_absolute() or not Path(value).is_dir():
            raise ValueError("Teach isolated environment directory is unavailable")
    fixed = {"UV_OFFLINE": "1", "UV_LOCKED": "1", "UV_PYTHON_DOWNLOADS": "never"}
    if any(os.environ.get(name) != value for name, value in fixed.items()):
        raise ValueError("Teach offline environment guard is not set")
    result.update(fixed)
    result.update(
        {
            "PIETTO_STORAGE_CLASS": "report",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(repo / "src"),
        }
    )
    return result


def produce_teach_receipt(
    repo: Path,
    manifest: dict[str, Any],
    inventory: list[dict[str, str]],
    materialization: object,
    collection_path: Path,
    requirements_path: Path,
    plan: object,
    output: Path,
    job_id: str,
    lease_id: str,
    offline_cache_manifest: Path,
    workers: int,
) -> dict[str, Any]:
    """Run the fixed Teach payload over one materialized candidate tree.

    This producer is usable for development before bootstrap publication, but
    emits no qualified terminal.  The host later re-derives the plan before it
    accepts this receipt for a successor.
    """

    if output.exists() or output.is_symlink():
        raise ValueError("Teach receipt output must be fresh")
    if ROOT.resolve() != repo.resolve() or not 1 <= workers <= 4:
        raise ValueError("invalid Teach producer repository or worker allocation")
    if platform.python_version() != manifest["context"]["python_version"]:
        raise ValueError("Teach producer interpreter differs from manifest")
    allocation = os.environ.get("SLURM_CPUS_ON_NODE", "")
    if not allocation.isdigit() or int(allocation) < workers:
        raise ValueError("Teach scheduler allocation is below requested workers")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", job_id) or not re.fullmatch(
        r"[A-Za-z0-9_-]{1,160}", lease_id
    ):
        raise ValueError("invalid Teach job or lease identity")
    cache_root = Path(os.environ.get("UV_CACHE_DIR", "")).resolve()
    if (
        not os.environ.get("UV_CACHE_DIR")
        or offline_cache_manifest.resolve().parent != cache_root
        or offline_cache_manifest.name != "pietto-offline-cache-manifest.json"
    ):
        raise ValueError("Teach cache manifest is not the active cache observation")
    offline_cache_sha256 = file_digest(offline_cache_manifest, MAX_SOURCE_BYTES)
    verify_materialization(materialization, manifest)
    verify_execution_tree(repo, manifest, inventory)
    accepted_plan = exact(
        plan,
        {
            "format",
            "candidate",
            "context",
            "inputs",
            "policy",
            "collection",
            "domain",
            "remote",
            "local",
        },
        "Teach acceptance plan",
    )
    if accepted_plan["format"] != ACCEPTANCE_PLAN_FORMAT or any(
        accepted_plan[name] != manifest[name]
        for name in ("candidate", "context", "inputs", "policy", "collection")
    ):
        raise ValueError("foreign Teach acceptance plan")
    collection_report, _remote = verify_collection_report(manifest, collection_path)
    if (
        verify_acceptance_plan(
            accepted_plan,
            manifest,
            collection_report,
            read_json(requirements_path, MAX_ACCEPTANCE_BYTES),
        )
        != accepted_plan
    ):
        raise ValueError("Teach plan is not the host-approved eligible-node plan")
    remote_rows = accepted_plan["remote"]
    if type(remote_rows) is not list or [
        row.get("partition") for row in remote_rows if type(row) is dict
    ] != list(ci_validation.PARTITIONS):
        raise ValueError("invalid Teach acceptance plan partitions")
    output.mkdir(mode=0o700)
    environment = teach_environment(repo)
    static = run_static(manifest, repo, "on", inventory, materialization, environment)
    verify_execution_tree(repo, manifest, inventory)
    reports: dict[str, object] = {}
    basetemp_roots: dict[str, str] = {}
    acquisition_roots: dict[str, str] = {}
    report_root = output / "reports"
    for row in remote_rows:
        item = exact(row, {"partition", "nodes", "indices"}, "Teach plan partition")
        if not item["nodes"]:
            reports[item["partition"]] = None
            continue
        nodes_path = output / ("nodes-" + item["partition"] + ".json")
        write_json(nodes_path, item["nodes"], MAX_ACCEPTANCE_BYTES)
        report_path = report_root / ci_validation.report_name(
            manifest["context"], item["partition"]
        )
        health_path = report_root / ("health-" + item["partition"] + ".json")
        command = (
            sys.executable,
            "scripts/ci_validation.py",
            "run",
            "--python",
            "3.13",
            "--report",
            str(report_path),
            "--health",
            str(health_path),
            "--partition",
            item["partition"],
            "--nodes-file",
            str(nodes_path),
            "--checkout",
            manifest["context"]["checkout"],
            "--run-id",
            manifest["context"]["run_id"],
            "--run-attempt",
            str(manifest["context"]["run_attempt"]),
            "--max-workers",
            str(workers),
            "--oom-guard",
            "on",
        )
        subprocess.run(command, cwd=repo, env=environment, check=True)
        verify_execution_tree(repo, manifest, inventory)
        basetemp = output / (report_path.stem + "-pytest")
        matches = list(basetemp.rglob("pietto-differential-acquisition"))
        if (
            not basetemp.is_dir()
            or len(matches) > 1
            or any(not match.is_dir() for match in matches)
        ):
            raise ValueError("Teach pytest temporary roots were not observed")
        basetemp_roots[item["partition"]] = str(basetemp.resolve())
        if matches:
            acquisition_roots[item["partition"]] = str(matches[0].resolve())
        reports[item["partition"]] = ci_validation.read_report(report_path)
    path312 = subprocess.check_output(("python3.12", "--version"), text=True).strip()
    node = subprocess.check_output(("node", "--version"), text=True).strip()
    java = subprocess.check_output(
        ("java", "-version"), stderr=subprocess.STDOUT, text=True
    )
    if re.search(r'(?:openjdk|java) version "21(?:\.|\")', java) is None:
        raise ValueError("Teach Java is not 21")
    receipt = {
        "format": ACCEPTANCE_RECEIPT_FORMAT,
        "runner": {
            "category": TEACH_RUNNER_CATEGORY,
            "job_id": job_id,
            "lease_id": lease_id,
            "credential_env_names": [],
            "canonical_worktree_written": False,
            "push_attempted": False,
        },
        "environment": {
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "path_python312": path312.removeprefix("Python "),
            "node_version": node,
            "java_version": "21",
            "uv_lock_sha256": file_digest(repo / "uv.lock", MAX_SOURCE_BYTES),
            "offline_cache_sha256": offline_cache_sha256,
            "runner_script_sha256": file_digest(
                Path(__file__).resolve(), MAX_SOURCE_BYTES
            ),
            "history_complete": git(repo, "rev-parse", "--is-shallow-repository")
            == "false",
            "basetemp_roots": basetemp_roots,
            "acquisition_roots": acquisition_roots,
            "workers": workers,
            "allocation_cpus": int(allocation),
        },
        "materialization": materialization,
        "static": static,
        "remote": {"reports": reports},
    }
    write_json(output / "receipt.json", receipt, MAX_ACCEPTANCE_BYTES)
    return receipt


def produce_local_reports(
    repo: Path,
    manifest: dict[str, Any],
    inventory: list[dict[str, str]],
    plan: object,
    output: Path,
    workers: int,
) -> dict[str, Any]:
    """Run the host-owned complement selected by the same frozen plan."""

    if output.exists() or output.is_symlink() or not 1 <= workers <= 4:
        raise ValueError("local acceptance output or worker allocation is invalid")
    if platform.python_version() != manifest["context"]["python_version"]:
        raise ValueError("host complement interpreter differs from manifest")
    accepted_plan = exact(
        plan,
        {
            "format",
            "candidate",
            "context",
            "inputs",
            "policy",
            "collection",
            "domain",
            "remote",
            "local",
        },
        "local acceptance plan",
    )
    if accepted_plan["format"] != ACCEPTANCE_PLAN_FORMAT or any(
        accepted_plan[name] != manifest[name]
        for name in ("candidate", "context", "inputs", "policy", "collection")
    ):
        raise ValueError("foreign local acceptance plan")
    verify_execution_tree(repo, manifest, inventory)
    output.mkdir(mode=0o700)
    environment = qualified_storage_environment(repo, output.parent)
    rows = accepted_plan["local"]
    if type(rows) is not list or [
        row.get("partition") for row in rows if type(row) is dict
    ] != list(ci_validation.PARTITIONS):
        raise ValueError("invalid local acceptance plan partitions")
    reports: dict[str, object] = {}
    for row in rows:
        item = exact(row, {"partition", "nodes", "indices"}, "local plan partition")
        if not item["nodes"]:
            reports[item["partition"]] = None
            continue
        nodes_path = output / ("nodes-" + item["partition"] + ".json")
        write_json(nodes_path, item["nodes"], MAX_ACCEPTANCE_BYTES)
        report_path = output / ci_validation.report_name(
            manifest["context"], item["partition"]
        )
        health_path = output / ("health-" + item["partition"] + ".json")
        subprocess.run(
            (
                sys.executable,
                "scripts/ci_validation.py",
                "run",
                "--python",
                "3.13",
                "--report",
                str(report_path),
                "--health",
                str(health_path),
                "--partition",
                item["partition"],
                "--nodes-file",
                str(nodes_path),
                "--checkout",
                manifest["context"]["checkout"],
                "--run-id",
                manifest["context"]["run_id"],
                "--run-attempt",
                str(manifest["context"]["run_attempt"]),
                "--max-workers",
                str(workers),
                "--oom-guard",
                "on",
            ),
            cwd=repo,
            env=environment,
            check=True,
        )
        verify_execution_tree(repo, manifest, inventory)
        reports[item["partition"]] = ci_validation.read_report(report_path)
    value = {"reports": reports}
    write_json(output / "local.json", value, MAX_ACCEPTANCE_BYTES)
    return value


def _verify_acceptance_report(
    report: object,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    owner: str,
) -> list[dict[str, Any]]:
    item = exact(
        report,
        {"reports"},
        owner + " acceptance report",
    )
    reports = item["reports"]
    if type(reports) is not dict or set(reports) != set(ci_validation.PARTITIONS):
        raise ValueError("missing or foreign " + owner + " acceptance reports")
    accepted = []
    for expected in plan[owner]:
        partition = expected["partition"]
        coverage = reports[partition]
        if not expected["nodes"]:
            if coverage is not None:
                raise ValueError("unexpected " + owner + " empty-partition report")
            continue
        if type(coverage) is not dict:
            raise ValueError("missing " + owner + " acceptance coverage")
        ci_validation.verify_report(coverage, manifest["context"], "partition")
        if (
            coverage["partition"] != partition
            or coverage["collection"] != manifest["collection"]
            or coverage["inputs"] != manifest["inputs"]
            or coverage["policy"] != manifest["policy"]
            or coverage["domain"] != plan["domain"]
            or coverage["nodes"] != expected["nodes"]
            or coverage["requirements"]["indices"] != expected["indices"]
        ):
            raise ValueError("foreign " + owner + " acceptance coverage")
        accepted.append(coverage)
    return accepted


def verify_acceptance_receipt(
    value: object,
    manifest: dict[str, Any],
    plan: dict[str, Any],
    bootstrap: object,
    repo: Path,
    inventory: list[dict[str, str]],
) -> dict[str, Any]:
    """Accept a bounded Teach receipt only with its local complement.

    This validates transport consistency and the explicitly approved trust
    premises.  It does not claim that a returned digest independently proves
    execution; the integration host owns that trust decision.
    """

    verify_bootstrap(bootstrap, manifest, repo)
    if (
        rebuilt_tree(repo, manifest["candidate"]["base"], verify_inventory(inventory))
        != manifest["candidate"]["tree"]
        or candidate_input_identity(repo) != manifest["inputs"]
    ):
        raise ValueError("integration-host candidate differs from acceptance manifest")
    receipt = exact(
        value,
        {
            "format",
            "runner",
            "environment",
            "materialization",
            "static",
            "remote",
            "local",
        },
        "acceptance receipt",
    )
    runner = exact(
        receipt["runner"],
        {
            "category",
            "job_id",
            "lease_id",
            "credential_env_names",
            "canonical_worktree_written",
            "push_attempted",
        },
        "Teach runner receipt",
    )
    if (
        receipt["format"] != ACCEPTANCE_RECEIPT_FORMAT
        or runner["category"] != TEACH_RUNNER_CATEGORY
        or type(runner["job_id"]) is not str
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", runner["job_id"])
        or type(runner["lease_id"]) is not str
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", runner["lease_id"])
        or runner["credential_env_names"] != []
        or runner["canonical_worktree_written"] is not False
        or runner["push_attempted"] is not False
    ):
        raise ValueError("Teach runner trust boundary is not satisfied")
    environment = exact(
        receipt["environment"],
        {
            "implementation",
            "python_version",
            "path_python312",
            "node_version",
            "java_version",
            "uv_lock_sha256",
            "offline_cache_sha256",
            "runner_script_sha256",
            "history_complete",
            "basetemp_roots",
            "acquisition_roots",
            "workers",
            "allocation_cpus",
        },
        "Teach environment record",
    )
    if (
        environment["implementation"] != "CPython"
        or environment["python_version"] != manifest["context"]["python_version"]
        or environment["path_python312"] != "3.12.13"
        or type(environment["node_version"]) is not str
        or not environment["node_version"]
        or environment["java_version"] != "21"
        or environment["uv_lock_sha256"] != manifest["lock_sha256"]
        or environment["runner_script_sha256"] != manifest["runner_script_sha256"]
        or environment["history_complete"] is not True
        or type(environment["basetemp_roots"]) is not dict
        or type(environment["acquisition_roots"]) is not dict
        or type(environment["workers"]) is not int
        or not 1 <= environment["workers"] <= 4
        or type(environment["allocation_cpus"]) is not int
        or environment["allocation_cpus"] < environment["workers"]
    ):
        raise ValueError("Teach environment premises are not satisfied")
    active = {row["partition"] for row in plan["remote"] if row["nodes"]}
    basetemps = environment["basetemp_roots"]
    acquisitions = environment["acquisition_roots"]
    if (
        set(basetemps) != active
        or not set(acquisitions).issubset(active)
        or any(
            type(value) is not str or not value.startswith("/") or "\x00" in value
            for value in (*basetemps.values(), *acquisitions.values())
        )
    ):
        raise ValueError(
            "Teach temporary root observations differ from executed partitions"
        )
    sha(environment["uv_lock_sha256"], "Teach uv.lock SHA-256")
    sha(environment["offline_cache_sha256"], "Teach offline cache SHA-256")
    sha(environment["runner_script_sha256"], "Teach runner script SHA-256")
    verify_materialization(receipt["materialization"], manifest)
    verify_static(receipt["static"], manifest)
    remote = _verify_acceptance_report(receipt["remote"], manifest, plan, "remote")
    local = _verify_acceptance_report(receipt["local"], manifest, plan, "local")
    if any(report["workers"] != environment["workers"] for report in remote):
        raise ValueError("Teach worker observation differs from environment record")
    if any(
        "PIETTO_NOT_RUN" in reason
        for report in remote
        for _index, reason in report["skips"]
    ):
        raise ValueError("remote acceptance report carries PIETTO_NOT_RUN")
    if any(
        "PIETTO_NOT_RUN" in reason
        for report in local
        for _index, reason in report["skips"]
    ):
        raise ValueError("local acceptance report carries PIETTO_NOT_RUN")
    return {
        "status": "VERIFIED_PENDING_HOST_ADOPTION",
        "candidate": manifest["candidate"],
        "remote_nodes": sum(len(report["nodes"]) for report in remote),
        "local_nodes": sum(len(report["nodes"]) for report in local),
    }


def accept_successor(
    repo: Path,
    manifest: dict[str, Any],
    inventory: list[dict[str, str]],
    collection_path: Path,
    bootstrap_path: Path,
    receipt_path: Path,
    local_reports_path: Path,
) -> dict[str, Any]:
    """Host-controlled acceptance entrypoint for one successor candidate.

    It deliberately recaptures marker provenance and derives the plan in the
    accepting process.  A received plan or a caller-supplied ``explicit`` bit
    therefore cannot move an unmarked node to Teach.
    """

    collection_report, _remote = verify_collection_report(manifest, collection_path)
    with tempfile.TemporaryDirectory(prefix="pietto-runner-accept-") as name:
        requirements_path = Path(name) / "requirements.json"
        requirements = capture_acceptance_requirements(
            repo, manifest, collection_path, requirements_path
        )
    plan = acceptance_plan(manifest, collection_report, requirements)
    receipt = read_json(receipt_path, MAX_ACCEPTANCE_BYTES)
    receipt["local"] = read_json(local_reports_path, MAX_ACCEPTANCE_BYTES)
    return verify_acceptance_receipt(
        receipt,
        manifest,
        plan,
        read_json(bootstrap_path),
        repo,
        inventory,
    )


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


def pytest_addoption(parser) -> None:
    """Expose marker provenance only for the acceptance collector plugin."""

    parser.addoption("--validation-runner-requirements")


def pytest_configure(config) -> None:
    config.addinivalue_line(
        "markers",
        "ci_workload(kind, **fields): explicit CI execution requirement",
    )


def pytest_collection_modifyitems(session, config, items) -> None:
    output = config.getoption("validation_runner_requirements")
    if output is None:
        return
    path = Path(output)
    if path.exists() or path.is_symlink():
        raise ValueError("acceptance marker output must be fresh")
    rows: dict[str, list[dict[str, object]]] = {}
    for item in sorted(items, key=lambda value: value.nodeid):
        rows[item.nodeid] = [
            {"args": list(mark.args), "kwargs": mark.kwargs}
            for mark in item.iter_markers("ci_workload")
        ]
    write_json(path, {"nodes": rows}, MAX_ACCEPTANCE_BYTES)


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
    observe = sub.add_parser("bootstrap-observe")
    observe.add_argument("--repo", type=Path, required=True)
    observe.add_argument("--run-id", type=int, required=True)
    observe.add_argument("--token-env", required=True)
    observe.add_argument("--output", type=Path, required=True)
    produce = sub.add_parser("teach-produce")
    produce.add_argument("--repo", type=Path, required=True)
    produce.add_argument("--manifest", type=Path, required=True)
    produce.add_argument("--inventory", type=Path, required=True)
    produce.add_argument("--materialization", type=Path, required=True)
    produce.add_argument("--collection", type=Path, required=True)
    produce.add_argument("--requirements", type=Path, required=True)
    produce.add_argument("--plan", type=Path, required=True)
    produce.add_argument("--output", type=Path, required=True)
    produce.add_argument("--job-id", required=True)
    produce.add_argument("--lease-id", required=True)
    produce.add_argument("--offline-cache-manifest", type=Path, required=True)
    produce.add_argument("--workers", type=int, required=True)
    local = sub.add_parser("host-produce")
    local.add_argument("--repo", type=Path, required=True)
    local.add_argument("--manifest", type=Path, required=True)
    local.add_argument("--inventory", type=Path, required=True)
    local.add_argument("--plan", type=Path, required=True)
    local.add_argument("--output", type=Path, required=True)
    local.add_argument("--workers", type=int, required=True)
    requirements = sub.add_parser("requirements")
    requirements.add_argument("--repo", type=Path, required=True)
    requirements.add_argument("--manifest", type=Path, required=True)
    requirements.add_argument("--collection", type=Path, required=True)
    requirements.add_argument("--output", type=Path, required=True)
    plan = sub.add_parser("acceptance-plan")
    plan.add_argument("--manifest", type=Path, required=True)
    plan.add_argument("--collection", type=Path, required=True)
    plan.add_argument("--requirements", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    accept = sub.add_parser("accept")
    accept.add_argument("--repo", type=Path, required=True)
    accept.add_argument("--manifest", type=Path, required=True)
    accept.add_argument("--inventory", type=Path, required=True)
    accept.add_argument("--collection", type=Path, required=True)
    accept.add_argument("--bootstrap", type=Path, required=True)
    accept.add_argument("--receipt", type=Path, required=True)
    accept.add_argument("--local-reports", type=Path, required=True)
    accept.add_argument("--output", type=Path, required=True)
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
        elif args.action == "bootstrap-observe":
            result = observe_bootstrap(
                args.repo, args.run_id, os.environ.get(args.token_env, "")
            )
            write_json(args.output, result)
            print(json.dumps({"published": result["published"]}, sort_keys=True))
        elif args.action == "teach-produce":
            manifest = read_manifest(args.manifest)
            result = produce_teach_receipt(
                args.repo,
                manifest,
                verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES)),
                read_json(args.materialization),
                args.collection,
                args.requirements,
                read_json(args.plan, MAX_ACCEPTANCE_BYTES),
                args.output,
                args.job_id,
                args.lease_id,
                args.offline_cache_manifest,
                args.workers,
            )
            print(
                json.dumps(
                    {
                        "status": "PRODUCED_NOT_QUALIFIED",
                        "remote_reports": sum(
                            report is not None
                            for report in result["remote"]["reports"].values()
                        ),
                    },
                    sort_keys=True,
                )
            )
        elif args.action == "host-produce":
            result = produce_local_reports(
                args.repo,
                read_manifest(args.manifest),
                verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES)),
                read_json(args.plan, MAX_ACCEPTANCE_BYTES),
                args.output,
                args.workers,
            )
            print(
                json.dumps(
                    {
                        "status": "LOCAL_COMPLEMENT_PRODUCED",
                        "reports": sum(
                            report is not None for report in result["reports"].values()
                        ),
                    },
                    sort_keys=True,
                )
            )
        elif args.action == "requirements":
            result = capture_acceptance_requirements(
                args.repo,
                read_manifest(args.manifest),
                args.collection,
                args.output,
            )
            print(json.dumps({"nodes": len(result["nodes"])}, sort_keys=True))
        elif args.action == "acceptance-plan":
            manifest = read_manifest(args.manifest)
            collection, _remote = verify_collection_report(manifest, args.collection)
            result = acceptance_plan(
                manifest, collection, read_json(args.requirements, MAX_ACCEPTANCE_BYTES)
            )
            write_json(args.output, result, MAX_ACCEPTANCE_BYTES)
            print(
                json.dumps(
                    {
                        "remote_nodes": sum(
                            len(row["nodes"]) for row in result["remote"]
                        ),
                        "local_nodes": sum(
                            len(row["nodes"]) for row in result["local"]
                        ),
                    },
                    sort_keys=True,
                )
            )
        elif args.action == "accept":
            manifest = read_manifest(args.manifest)
            result = accept_successor(
                args.repo,
                manifest,
                verify_inventory(read_value(args.inventory, MAX_SOURCE_BYTES)),
                args.collection,
                args.bootstrap,
                args.receipt,
                args.local_reports,
            )
            write_json(args.output, result)
            print(json.dumps(result, sort_keys=True))
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
