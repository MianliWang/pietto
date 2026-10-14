"""Functional checks for VR1 candidate transport and evidence boundaries."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

import pytest

from scripts import ci_validation
from scripts import validation_runner_receiver as runner


CANDIDATE_FILES = (
    "scripts/validation_runner_receiver.py",
    "tests/test_harness_validation_runner_receiver.py",
    "docs/development.md",
    "docs/spec/validation-runner-acceptance-v1.md",
)
NODES = tuple(f"tests/test_runner_{index}.py::test_x" for index in range(5))


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=repo, text=True).strip()


def _clone(tmp_path: Path, name: str = "source", candidate: bool = True) -> Path:
    repo = tmp_path / name
    subprocess.run(
        ("git", "clone", "--quiet", "--no-hardlinks", str(runner.ROOT), str(repo)),
        check=True,
    )
    if candidate:
        for relative in CANDIDATE_FILES:
            destination = repo / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(runner.ROOT / relative, destination)
    return repo


def _collection(repo: Path) -> dict[str, object]:
    base = _git(repo, "rev-parse", "HEAD")
    return {
        "context": {
            "checkout": base,
            "run_id": "vr1-test",
            "run_attempt": 1,
            "python": "3.13",
            "python_version": "3.13.13",
        },
        "collection": {
            "count": len(NODES),
            "sha256": "a" * 64,
            "requirements_sha256": "b" * 64,
        },
        "requirements": {"indices": [0, 1, 2, 3, 0]},
    }


def _bind_collection(monkeypatch, collection: dict[str, Any]) -> None:
    def read(path: Path):
        return json.loads(path.read_text())

    def verify(report, context, kind):
        assert report["context"] == context
        if kind == "collection":
            return list(NODES)
        assert kind == "partition"
        return report["nodes"]

    def partitions(nodes, indices):
        assert nodes == list(NODES)
        assert indices == collection["requirements"]["indices"]
        return {
            "shared-acquisition": [NODES[0]],
            "plan-portability": [NODES[1]],
            "emission-portability": [NODES[2]],
            "general-runtime-1": [NODES[3]],
            "general-runtime-2": [NODES[4]],
            "general-runtime-3": [NODES[4]],
        }

    monkeypatch.setattr(runner.ci_validation, "read_report", read)
    monkeypatch.setattr(runner.ci_validation, "verify_report", verify)
    monkeypatch.setattr(runner.ci_validation, "partition_nodes", partitions)


def _manifest(tmp_path: Path, monkeypatch):
    source = _clone(tmp_path)
    readme = source / "README.md"
    readme.write_text(readme.read_text() + "\nVR1 synthetic candidate.\n")
    removed = source / "examples/basic/types.pietto"
    removed.unlink()
    collection = _collection(source)
    collection_path = tmp_path / "collection.json"
    collection_path.write_text(json.dumps(collection, sort_keys=True))
    _bind_collection(monkeypatch, collection)
    output = tmp_path / "out"
    manifest = runner.create_manifest(
        source,
        output,
        runner.git_status_paths(source),
        collection_path,
        "vr1-test",
        1,
        "3.13.13",
        source / "scripts/validation_runner_receiver.py",
    )
    return (
        source,
        output,
        manifest,
        collection,
        collection_path,
        removed.relative_to(source).as_posix(),
    )


def _report(manifest: dict[str, object], partition: str, node: str, index: int):
    return {
        "format": ci_validation.FORMAT,
        "kind": "partition",
        "context": manifest["context"],
        "exit_code": 0,
        "collection": manifest["collection"],
        "elapsed_seconds": 1.0,
        "nodes": [node],
        "policy": manifest["policy"],
        "inputs": manifest["inputs"],
        "domain": [[3, 12], [3, 13]],
        "requirements": {"table": [], "indices": [index]},
        "partition": partition,
        "outcomes": [[0, "passed", "passed", "passed"]],
        "workers": 1,
        "properties": [],
        "skips": [],
    }


def _environment(manifest: dict[str, object]) -> dict[str, object]:
    return {
        "format": runner.ENVIRONMENT_FORMAT,
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": manifest["inputs"],
        "interpreter": {
            "implementation": "CPython",
            "python_version": "3.13.13",
            "path_python312": "3.12.13",
        },
        "tooling": {
            "node_version": "v1",
            "java_version": "21",
            "uv_lock_sha256": manifest["lock_sha256"],
            "offline_cache_sha256": "d" * 64,
            "runner_script_sha256": manifest["runner_script_sha256"],
        },
        "history_complete": True,
        "storage_class": "report",
        "credential_env_names": [],
    }


def _reports(manifest: dict[str, Any]) -> dict[str, dict[str, object]]:
    return {
        row["partition"]: _report(
            manifest, row["partition"], row["nodes"][0], row["indices"][0]
        )
        for row in manifest["remote_partitions"]
    }


def _materialized(tmp_path: Path, monkeypatch):
    source, output, manifest, collection, collection_path, removed = _manifest(
        tmp_path, monkeypatch
    )
    remote = _clone(tmp_path, "remote", candidate=False)
    inventory = runner.verify_inventory(
        runner.read_value(output / "source-tree.json", runner.MAX_SOURCE_BYTES)
    )
    proof = runner.materialize_candidate(
        remote, manifest, output / "source.tar", inventory
    )
    return (
        source,
        output,
        manifest,
        collection,
        collection_path,
        removed,
        remote,
        inventory,
        proof,
    )


def test_create_binds_candidate_repository_script_and_rebuilds_tree(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        _collection_,
        _path,
        removed,
        remote,
        _inventory,
        proof,
    ) = _materialized(tmp_path, monkeypatch)

    assert _git(remote, "rev-parse", "HEAD") == manifest["candidate"]["base"]
    assert proof["rebuilt_tree"] == manifest["candidate"]["tree"]
    assert proof["status"] == "MATERIALIZED_NOT_QUALIFIED"
    assert _git(remote, "status", "--porcelain")
    assert not (remote / removed).exists()
    assert runner.verify_materialization(proof, manifest) == proof
    assert _git(source, "rev-parse", "HEAD") == manifest["candidate"]["base"]


def test_candidate_transport_refuses_tampered_tree_or_remote_baseline(
    tmp_path, monkeypatch
):
    (
        _source,
        output,
        manifest,
        _collection_,
        _path,
        _removed,
        _remote,
        inventory,
        _proof,
    ) = _materialized(tmp_path, monkeypatch)
    altered = [dict(row) for row in inventory]
    altered[0]["blob"] = "0" * 40
    with pytest.raises(ValueError, match="blob"):
        runner.safe_archive_members(output / "source.tar", altered)

    changed_archive = tmp_path / "changed-source.tar"
    changed_archive.write_bytes((output / "source.tar").read_bytes() + b"x")
    clean_target = _clone(tmp_path, "clean-target", candidate=False)
    with pytest.raises(ValueError, match="archive differs"):
        runner.materialize_candidate(clean_target, manifest, changed_archive, inventory)

    dirty_target = _clone(tmp_path, "dirty-target", candidate=False)
    (dirty_target / "README.md").write_text("unexpected tracked modification\n")
    with pytest.raises(ValueError, match="not clean"):
        runner.materialize_candidate(
            dirty_target, manifest, output / "source.tar", inventory
        )


def test_full_collection_derives_remote_subset_and_rejects_false_closure(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        collection,
        _path,
        _removed,
        _remote,
        inventory,
        proof,
    ) = _materialized(tmp_path, monkeypatch)
    reports = _reports(manifest)
    static = runner.static_report(
        manifest,
        [(name, command, 0, 1.0) for name, command in runner.validate.GATES[:5]],
    )
    assert (
        runner.verify_received(
            manifest, proof, static, reports, source, inventory, collection
        )["status"]
        == "RECEIVED_NOT_QUALIFIED"
    )

    wrong_index = json.loads(json.dumps(reports))
    wrong_index["shared-acquisition"]["requirements"]["indices"] = [99]
    with pytest.raises(ValueError, match="incomplete"):
        runner.verify_received(
            manifest, proof, static, wrong_index, source, inventory, collection
        )

    omitted = json.loads(json.dumps(reports))
    omitted["plan-portability"]["nodes"] = []
    with pytest.raises(ValueError, match="incomplete"):
        runner.verify_received(
            manifest, proof, static, omitted, source, inventory, collection
        )

    duplicate = json.loads(json.dumps(reports))
    duplicate["emission-portability"]["nodes"] = duplicate["shared-acquisition"][
        "nodes"
    ]
    with pytest.raises(ValueError, match="incomplete"):
        runner.verify_received(
            manifest, proof, static, duplicate, source, inventory, collection
        )

    foreign_collection = json.loads(json.dumps(collection))
    foreign_collection["collection"]["count"] = len(NODES) + 1
    with pytest.raises(ValueError, match="full collection"):
        runner.verify_received(
            manifest, proof, static, reports, source, inventory, foreign_collection
        )


def test_static_producer_and_environment_remain_asserted_not_qualified(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        _collection_,
        _path,
        _removed,
        _remote,
        inventory,
        proof,
    ) = _materialized(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr(runner, "ROOT", source)
    monkeypatch.setattr(
        runner.ci_validation,
        "run_gate",
        lambda name, command, guard: calls.append((name, command, guard)) or 0,
    )
    static = runner.run_static(manifest, source, "on", inventory, proof)
    assert [call[:2] for call in calls] == list(runner.validate.GATES[:5])
    assert static["status"] == "success"

    monkeypatch.setattr(runner.ci_validation, "run_gate", lambda *_: 1)
    assert (
        runner.run_static(manifest, source, "on", inventory, proof)["status"]
        == "failed"
    )

    def mutate(name, command, guard):
        (source / "README.md").write_text("changed by fake gate\n")
        return 0

    monkeypatch.setattr(runner.ci_validation, "run_gate", mutate)
    with pytest.raises(ValueError, match="changed the candidate"):
        runner.run_static(manifest, source, "on", inventory, proof)

    assert (
        runner.verify_environment(_environment(manifest), manifest)["status"]
        == "ASSERTED_NOT_QUALIFIED"
    )
    environment = _environment(manifest)
    environment["storage_class"] = "qualified"
    with pytest.raises(ValueError, match="assertion"):
        runner.verify_environment(environment, manifest)
