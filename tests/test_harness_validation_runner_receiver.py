"""Functional checks for VR1 candidate transport and evidence boundaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import ci_validation
from scripts import validation_runner_receiver as runner


CANDIDATE_FILES = (
    "scripts/ci_validation.py",
    "scripts/validation_runner_receiver.py",
    "tests/test_harness_validation_runner_receiver.py",
    "docs/development.md",
    "docs/spec/validation-runner-acceptance-v1.md",
)
NODES = tuple(f"tests/test_runner_{index}.py::test_x" for index in range(6))


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=repo, text=True).strip()


def _clone(
    tmp_path: Path,
    name: str = "source",
    candidate: bool = True,
    source: Path | None = None,
) -> Path:
    source = runner.ROOT if source is None else source
    repo = tmp_path / name
    subprocess.run(
        ("git", "clone", "--quiet", "--no-hardlinks", str(source), str(repo)),
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
        "domain": [[3, 12], [3, 13]],
        "requirements": {"indices": [0, 1, 2, 3, 0, 0]},
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
            "general-runtime-3": [NODES[5]],
        }

    monkeypatch.setattr(runner.ci_validation, "read_report", read)
    monkeypatch.setattr(runner.ci_validation, "verify_report", verify)
    monkeypatch.setattr(runner.ci_validation, "partition_nodes", partitions)


def _manifest(tmp_path: Path, monkeypatch):
    source = _clone(tmp_path)
    subprocess.run(("git", "add", *CANDIDATE_FILES), cwd=source, check=True)
    subprocess.run(
        (
            "git",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "test: publish runner bootstrap",
        ),
        cwd=source,
        check=True,
    )
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


def _report(
    manifest: dict[str, object],
    partition: str,
    nodes: list[str],
    indices: list[int],
):
    return {
        "format": ci_validation.FORMAT,
        "kind": "partition",
        "context": manifest["context"],
        "exit_code": 0,
        "collection": manifest["collection"],
        "elapsed_seconds": 1.0,
        "nodes": nodes,
        "policy": manifest["policy"],
        "inputs": manifest["inputs"],
        "domain": [[3, 12], [3, 13]],
        "requirements": {
            "table": ci_validation.workloads.table(ci_validation.POLICY),
            "indices": indices,
        },
        "partition": partition,
        "outcomes": [
            [index, "passed", "passed", "passed"] for index in range(len(nodes))
        ],
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
            manifest, row["partition"], row["nodes"], row["indices"]
        )
        for row in manifest["remote_partitions"]
    }


def _materialized(tmp_path: Path, monkeypatch):
    source, output, manifest, collection, collection_path, removed = _manifest(
        tmp_path, monkeypatch
    )
    remote = _clone(tmp_path, "remote", candidate=False, source=source)
    assert _git(remote, "rev-parse", "HEAD") == manifest["candidate"]["base"]
    assert not _git(remote, "status", "--porcelain", "--untracked-files=all")
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


@pytest.mark.parametrize("candidate_is_committed", (False, True))
def test_create_binds_candidate_repository_script_and_rebuilds_tree(
    tmp_path, monkeypatch, candidate_is_committed
):
    committed_head = None
    if candidate_is_committed:
        committed = _clone(tmp_path, "committed-candidate", candidate=False)
        for relative in CANDIDATE_FILES:
            shutil.copy2(runner.ROOT / relative, committed / relative)
        subprocess.run(("git", "add", *CANDIDATE_FILES), cwd=committed, check=True)
        subprocess.run(
            (
                "git",
                "commit",
                "--quiet",
                "--allow-empty",
                "-m",
                "test: commit candidate bytes",
            ),
            cwd=committed,
            check=True,
        )
        committed_head = _git(committed, "rev-parse", "HEAD")
        monkeypatch.setattr(runner, "ROOT", committed)
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
    if committed_head is not None:
        assert _git(source, "rev-parse", "HEAD^") == committed_head


def test_candidate_transport_refuses_tampered_tree_or_remote_baseline(
    tmp_path, monkeypatch
):
    (
        source,
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
    clean_target = _clone(tmp_path, "clean-target", candidate=False, source=source)
    with pytest.raises(ValueError, match="archive differs"):
        runner.materialize_candidate(clean_target, manifest, changed_archive, inventory)

    dirty_target = _clone(tmp_path, "dirty-target", candidate=False, source=source)
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


def _acceptance_requirements(manifest, collection, explicit=()):
    return {
        "format": runner.REQUIREMENTS_FORMAT,
        "candidate": manifest["candidate"],
        "context": manifest["context"],
        "inputs": manifest["inputs"],
        "policy": manifest["policy"],
        "collection": manifest["collection"],
        "nodes": [
            {
                "node": node,
                "index": index,
                "explicit": node in explicit,
            }
            for node, index in zip(
                NODES, collection["requirements"]["indices"], strict=True
            )
        ],
    }


def _acceptance_reports(manifest, plan, owner):
    reports = {}
    for row in plan[owner]:
        reports[row["partition"]] = (
            None
            if not row["nodes"]
            else _report(manifest, row["partition"], row["nodes"], row["indices"])
        )
    return {"reports": reports}


def _acceptance_environment(manifest, plan):
    active = [row["partition"] for row in plan["remote"] if row["nodes"]]
    return {
        "implementation": "CPython",
        "python_version": manifest["context"]["python_version"],
        "path_python312": "3.12.13",
        "node_version": "v1",
        "java_version": "21",
        "uv_lock_sha256": manifest["lock_sha256"],
        "offline_cache_sha256": "d" * 64,
        "runner_script_sha256": manifest["runner_script_sha256"],
        "history_complete": True,
        "basetemp_roots": {
            partition: "/tmp/teach-" + partition for partition in active
        },
        "acquisition_roots": {},
        "workers": 1,
        "allocation_cpus": 1,
    }


def _bootstrap(source: Path):
    head = _git(source, "rev-parse", "HEAD")
    inventory = {
        row["path"]: row["blob"] for row in runner.tree_inventory(source, head)
    }
    return {
        "format": runner.BOOTSTRAP_FORMAT,
        "published": {"head": head, "tree": _git(source, "rev-parse", "HEAD^{tree}")},
        "adopted": {
            "blobs": [
                {"path": path, "blob": inventory[path]}
                for path in runner.ACCEPTANCE_RULE_PATHS
            ]
        },
        "natural_ci": {
            "workflow": {
                "id": 7,
                "path": ".github/workflows/ci.yml",
                "blob": inventory[".github/workflows/ci.yml"],
            },
            "run_id": 1,
            "event": "push",
            "branch": "main",
            "head": head,
            "attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "jobs": [
                {"name": name, "conclusion": "success"}
                for name in _natural_ci_job_names()
            ],
        },
    }


def _natural_ci_job_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            {
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
        )
    )


def test_acceptance_uses_only_explicit_core_and_requires_bootstrap(
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
    # NODES[4] is the only explicitly declared ordinary core requirement.
    requirements = _acceptance_requirements(manifest, collection, (NODES[4],))
    plan = runner.acceptance_plan(manifest, collection, requirements)
    assert [row["nodes"] for row in plan["remote"]] == [[], [], [], [], [NODES[4]], []]
    assert sum(len(row["nodes"]) for row in plan["local"]) == len(NODES) - 1
    assert (
        runner.verify_acceptance_plan(plan, manifest, collection, requirements) == plan
    )

    static = runner.static_report(
        manifest,
        [(name, command, 0, 1.0) for name, command in runner.validate.GATES[:5]],
    )
    bootstrap = _bootstrap(source)
    receipt = {
        "format": runner.ACCEPTANCE_RECEIPT_FORMAT,
        "runner": {
            "category": runner.TEACH_RUNNER_CATEGORY,
            "job_id": "teach-1",
            "lease_id": "lease-1",
            "credential_env_names": [],
            "canonical_worktree_written": False,
            "push_attempted": False,
        },
        "environment": _acceptance_environment(manifest, plan),
        "materialization": proof,
        "static": static,
        "remote": _acceptance_reports(manifest, plan, "remote"),
        "local": _acceptance_reports(manifest, plan, "local"),
    }
    result = runner.verify_acceptance_receipt(
        receipt, manifest, plan, bootstrap, source, inventory
    )
    assert result["status"] == "VERIFIED_PENDING_HOST_ADOPTION"
    assert result["remote_nodes"] == 1

    receipt["runner"]["credential_env_names"] = ["GITHUB_TOKEN"]
    with pytest.raises(ValueError, match="trust boundary"):
        runner.verify_acceptance_receipt(
            receipt, manifest, plan, bootstrap, source, inventory
        )


def test_acceptance_rejects_remote_skip_and_unapproved_marker_selection(
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
    requirements = _acceptance_requirements(manifest, collection, (NODES[4],))
    requirements["nodes"][0]["explicit"] = True
    with pytest.raises(ValueError, match="acceptance plan"):
        runner.verify_acceptance_plan(
            runner.acceptance_plan(
                manifest, collection, _acceptance_requirements(manifest, collection)
            ),
            manifest,
            collection,
            requirements,
        )

    plan = runner.acceptance_plan(
        manifest,
        collection,
        _acceptance_requirements(manifest, collection, (NODES[4],)),
    )
    static = runner.static_report(
        manifest,
        [(name, command, 0, 1.0) for name, command in runner.validate.GATES[:5]],
    )
    bootstrap = _bootstrap(source)
    remote = _acceptance_reports(manifest, plan, "remote")
    remote["reports"]["general-runtime-2"]["outcomes"] = [
        [0, "passed", "skipped", "passed"]
    ]
    remote["reports"]["general-runtime-2"]["skips"] = [
        [0, "PIETTO_NOT_RUN storage-positive"]
    ]
    receipt = {
        "format": runner.ACCEPTANCE_RECEIPT_FORMAT,
        "runner": {
            "category": runner.TEACH_RUNNER_CATEGORY,
            "job_id": "teach-1",
            "lease_id": "lease-1",
            "credential_env_names": [],
            "canonical_worktree_written": False,
            "push_attempted": False,
        },
        "environment": _acceptance_environment(manifest, plan),
        "materialization": proof,
        "static": static,
        "remote": remote,
        "local": _acceptance_reports(manifest, plan, "local"),
    }
    with pytest.raises(ValueError, match="PIETTO_NOT_RUN"):
        runner.verify_acceptance_receipt(
            receipt, manifest, plan, bootstrap, source, inventory
        )


def test_bootstrap_rejects_unpublished_rule_bytes(tmp_path, monkeypatch):
    (
        source,
        _output,
        manifest,
        _collection,
        _path,
        _removed,
        _remote,
        inventory,
        _proof,
    ) = _materialized(tmp_path, monkeypatch)
    bootstrap = _bootstrap(source)
    bootstrap["adopted"]["blobs"][0]["blob"] = "0" * 40
    with pytest.raises(ValueError, match="accepted rule bytes"):
        runner.verify_bootstrap(bootstrap, manifest, source)
    assert inventory


def test_teach_environment_rejects_credentials_before_static(monkeypatch, tmp_path):
    _clear_teach_credentials(monkeypatch)
    cache = tmp_path / "cache"
    home = tmp_path / "home"
    job_tmp = tmp_path / "job-tmp"
    for path in (cache, home, job_tmp):
        path.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(job_tmp))
    monkeypatch.setenv("UV_CACHE_DIR", str(cache))
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.setenv("UV_LOCKED", "1")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    monkeypatch.setenv("GITHUB_TOKEN", "present")
    with pytest.raises(ValueError, match="credential"):
        runner.teach_environment(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN")
    monkeypatch.setenv("UV_OFFLINE", "0")
    with pytest.raises(ValueError, match="offline environment guard"):
        runner.teach_environment(tmp_path)
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.setenv("UNRELATED_PARENT_VALUE", "must-not-reach-job")
    environment = runner.teach_environment(tmp_path)
    assert environment["PIETTO_STORAGE_CLASS"] == "report"
    assert environment["PYTHONPATH"] == str(tmp_path / "src")
    assert "UNRELATED_PARENT_VALUE" not in environment


def test_bootstrap_observer_requires_exact_workflow_consumers_and_adopted_bytes(
    tmp_path, monkeypatch
):
    source = _clone(tmp_path, candidate=False)
    published = _git(source, "rev-parse", "refs/remotes/origin/main")
    tree = _git(source, "rev-parse", published + "^{tree}")
    jobs = [
        {
            "name": name,
            "status": "completed",
            "conclusion": "success",
            "run_id": 42,
            "head_sha": published,
            "run_attempt": 1,
        }
        for name in _natural_ci_job_names()
    ]
    responses: dict[str, dict[str, Any]] = {
        "repos/example/pietto/actions/runs/42": {
            "id": 42,
            "event": "push",
            "head_branch": "main",
            "head_sha": published,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
            "repository": {"full_name": "example/pietto"},
            "workflow_id": 7,
            "path": ".github/workflows/ci.yml",
        },
        "repos/example/pietto/git/ref/heads/main": {
            "ref": "refs/heads/main",
            "object": {"type": "commit", "sha": published},
        },
        "repos/example/pietto/actions/workflows/ci.yml": {
            "id": 7,
            "path": ".github/workflows/ci.yml",
        },
        "repos/example/pietto/actions/runs/42/attempts/1/jobs?per_page=100": {
            "total_count": len(jobs),
            "jobs": jobs,
        },
    }

    monkeypatch.setattr(runner, "_github_repository", lambda repo: "example/pietto")
    monkeypatch.setattr(
        runner.workloads,
        "github_bytes",
        lambda path, token, limit, deadline: runner.canonical(responses[path]),
    )
    record = runner.observe_bootstrap(source, 42, "read-only-token")
    assert record["published"] == {"head": published, "tree": tree}
    assert [row["name"] for row in record["natural_ci"]["jobs"]] == list(
        _natural_ci_job_names()
    )
    assert [row["path"] for row in record["adopted"]["blobs"]] == list(
        runner.ACCEPTANCE_RULE_PATHS
    )
    assert record["natural_ci"]["workflow"] == {
        "id": 7,
        "path": ".github/workflows/ci.yml",
        "blob": next(
            row["blob"]
            for row in runner.tree_inventory(source, tree)
            if row["path"] == ".github/workflows/ci.yml"
        ),
    }

    jobs_path = "repos/example/pietto/actions/runs/42/attempts/1/jobs?per_page=100"
    responses[jobs_path]["jobs"] = jobs[:-1]
    responses[jobs_path]["total_count"] = len(jobs) - 1
    with pytest.raises(ValueError, match="job inventory"):
        runner.observe_bootstrap(source, 42, "read-only-token")

    responses[jobs_path]["jobs"] = jobs
    responses[jobs_path]["total_count"] = len(jobs)
    responses["repos/example/pietto/git/ref/heads/main"]["object"] = {
        "type": "commit",
        "sha": "0" * 40,
    }
    with pytest.raises(ValueError, match="workflow or published branch"):
        runner.observe_bootstrap(source, 42, "read-only-token")

    responses["repos/example/pietto/git/ref/heads/main"]["object"] = {
        "type": "commit",
        "sha": published,
    }
    responses["repos/example/pietto/actions/workflows/ci.yml"]["id"] = 8
    with pytest.raises(ValueError, match="workflow or published branch"):
        runner.observe_bootstrap(source, 42, "read-only-token")


def _teach_inputs(tmp_path, monkeypatch, *, explicit=()):
    (
        source,
        output,
        manifest,
        collection,
        collection_path,
        _removed,
        _remote,
        inventory,
        proof,
    ) = _materialized(tmp_path, monkeypatch)
    requirements = _acceptance_requirements(manifest, collection, explicit)
    requirements_path = tmp_path / "requirements.json"
    requirements_path.write_text(json.dumps(requirements, sort_keys=True))
    cache = tmp_path / "cache"
    cache.mkdir()
    cache_manifest = cache / "pietto-offline-cache-manifest.json"
    cache_manifest.write_text('{"format":"test"}\n')
    monkeypatch.setattr(runner, "ROOT", source)
    monkeypatch.setattr(runner.platform, "python_version", lambda: "3.13.13")
    monkeypatch.setenv("SLURM_CPUS_ON_NODE", "4")
    monkeypatch.setenv("UV_CACHE_DIR", str(cache))
    home = tmp_path / "teach-home"
    job_tmp = tmp_path / "teach-tmp"
    home.mkdir()
    job_tmp.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("TMPDIR", str(job_tmp))
    monkeypatch.setenv("UV_OFFLINE", "1")
    monkeypatch.setenv("UV_LOCKED", "1")
    monkeypatch.setenv("UV_PYTHON_DOWNLOADS", "never")
    return (
        source,
        output,
        manifest,
        collection_path,
        requirements_path,
        runner.acceptance_plan(manifest, collection, requirements),
        inventory,
        proof,
        cache_manifest,
    )


def _clear_teach_credentials(monkeypatch) -> None:
    for name in tuple(os.environ):
        if (
            name in {"SSH_AUTH_SOCK", "GITHUB_TOKEN", "GH_TOKEN"}
            or "TOKEN" in name
            or "SECRET" in name
            or name.endswith("_KEY")
        ):
            monkeypatch.delenv(name)


def test_teach_producer_rejects_credential_before_static_or_pytest(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        collection_path,
        requirements_path,
        plan,
        inventory,
        proof,
        cache_manifest,
    ) = _teach_inputs(tmp_path, monkeypatch, explicit=(NODES[4],))
    monkeypatch.setenv("GITHUB_TOKEN", "forbidden")
    static_calls = []
    monkeypatch.setattr(
        runner,
        "run_static",
        lambda *args: static_calls.append(args) or pytest.fail("static ran"),
    )
    with pytest.raises(ValueError, match="credential"):
        runner.produce_teach_receipt(
            source,
            manifest,
            inventory,
            proof,
            collection_path,
            requirements_path,
            plan,
            tmp_path / "teach-output",
            "teach-42",
            "lease-42",
            cache_manifest,
            1,
        )
    assert static_calls == []


def test_teach_producer_rejects_unmarked_remote_plan_before_pytest(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        collection_path,
        requirements_path,
        plan,
        inventory,
        proof,
        cache_manifest,
    ) = _teach_inputs(tmp_path, monkeypatch)
    plan["remote"][0]["nodes"] = [NODES[0]]
    plan["remote"][0]["indices"] = [0]
    plan["local"][0]["nodes"] = []
    plan["local"][0]["indices"] = []
    commands = []

    original_run = runner.subprocess.run

    def run(command, **kwargs):
        if command[0] == "git":
            return original_run(command, **kwargs)
        commands.append(command)
        pytest.fail("pytest ran before eligible plan validation")

    monkeypatch.setattr(
        runner.subprocess,
        "run",
        run,
    )
    with pytest.raises(ValueError, match="acceptance plan"):
        runner.produce_teach_receipt(
            source,
            manifest,
            inventory,
            proof,
            collection_path,
            requirements_path,
            plan,
            tmp_path / "teach-output",
            "teach-42",
            "lease-42",
            cache_manifest,
            1,
        )
    assert commands == []


def test_teach_producer_refuses_unmeasured_cache_manifest_before_execution(
    tmp_path, monkeypatch
):
    (
        source,
        _output,
        manifest,
        collection_path,
        requirements_path,
        plan,
        inventory,
        proof,
        _cache_manifest,
    ) = _teach_inputs(tmp_path, monkeypatch)
    wrong_cache = tmp_path / "wrong-cache-manifest.json"
    wrong_cache.write_text("not the active cache observation\n")
    with pytest.raises(ValueError, match="cache manifest"):
        runner.produce_teach_receipt(
            source,
            manifest,
            inventory,
            proof,
            collection_path,
            requirements_path,
            plan,
            tmp_path / "teach-output",
            "teach-42",
            "lease-42",
            wrong_cache,
            1,
        )


@pytest.mark.parametrize("acquisition_present", (False, True))
def test_teach_producer_records_actual_pytest_roots(
    tmp_path, monkeypatch, acquisition_present
):
    (
        source,
        _output,
        manifest,
        collection_path,
        requirements_path,
        plan,
        inventory,
        proof,
        cache_manifest,
    ) = _teach_inputs(tmp_path, monkeypatch, explicit=(NODES[4],))
    _clear_teach_credentials(monkeypatch)
    static = runner.static_report(
        manifest,
        [(name, command, 0, 1.0) for name, command in runner.validate.GATES[:5]],
    )
    static_environments = []

    def run_static(manifest, repo, oom_guard, inventory, materialization, environment):
        assert environment == runner.teach_environment(source)
        static_environments.append(environment)
        return static

    monkeypatch.setattr(runner, "run_static", run_static)
    original_check_output = runner.subprocess.check_output
    original_run = runner.subprocess.run

    def check_output(command, **kwargs):
        if command[0] == "git":
            return original_check_output(command, **kwargs)
        values = {
            "python3.12": "Python 3.12.13\n",
            "node": "v20.0.0\n",
            "java": 'openjdk version "21.0.1"\n',
        }
        if command[0] in values:
            return values[command[0]]
        return original_check_output(command, **kwargs)

    def run(command, **kwargs):
        if command[:3] != (
            runner.sys.executable,
            "scripts/ci_validation.py",
            "run",
        ):
            return original_run(command, **kwargs)
        report_path = Path(command[command.index("--report") + 1])
        partition = command[command.index("--partition") + 1]
        row = next(item for item in plan["remote"] if item["partition"] == partition)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(_report(manifest, partition, row["nodes"], row["indices"]))
        )
        basetemp = report_path.parent.parent / (report_path.stem + "-pytest")
        basetemp.mkdir(parents=True)
        if acquisition_present:
            (basetemp / "pietto-differential-acquisition").mkdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner.subprocess, "check_output", check_output)
    monkeypatch.setattr(runner.subprocess, "run", run)
    output = tmp_path / "teach-output"
    receipt = runner.produce_teach_receipt(
        source,
        manifest,
        inventory,
        proof,
        collection_path,
        requirements_path,
        plan,
        output,
        "teach-42",
        "lease-42",
        cache_manifest,
        1,
    )
    assert len(static_environments) == 1
    row = next(row for row in plan["remote"] if row["nodes"])
    report_path = (
        output
        / "reports"
        / ci_validation.report_name(manifest["context"], row["partition"])
    )
    assert receipt["environment"]["basetemp_roots"] == {
        row["partition"]: str((output / (report_path.stem + "-pytest")).resolve())
    }
    expected_acquisition = (
        {
            row["partition"]: str(
                (
                    output
                    / (report_path.stem + "-pytest")
                    / "pietto-differential-acquisition"
                ).resolve()
            )
        }
        if acquisition_present
        else {}
    )
    assert receipt["environment"]["acquisition_roots"] == expected_acquisition


def test_local_producer_rejects_hosted_refusal_and_tree_drift(tmp_path, monkeypatch):
    (
        source,
        _output,
        manifest,
        _collection_path,
        _requirements_path,
        plan,
        inventory,
        _proof,
        _cache_manifest,
    ) = _teach_inputs(tmp_path, monkeypatch)
    monkeypatch.setenv("PIETTO_STORAGE_CLASS", "hosted-refusal")
    with pytest.raises(ValueError, match="storage class conflicts"):
        runner.produce_local_reports(
            source, manifest, inventory, plan, tmp_path / "local-refusal", 1
        )

    monkeypatch.delenv("PIETTO_STORAGE_CLASS")
    calls = []
    original_run = runner.subprocess.run

    def run(command, **kwargs):
        if command[:2] == (runner.sys.executable, "-c"):
            calls.append((command, kwargs))
            assert kwargs["env"]["PIETTO_STORAGE_CLASS"] == "qualified"
            assert kwargs["env"]["PYTHONPATH"] == str(source / "src")
            assert kwargs["env"]["PYTEST_DEBUG_TEMPROOT"] == str(tmp_path.resolve())
            return SimpleNamespace(returncode=0)
        if command[:3] == (
            runner.sys.executable,
            "scripts/ci_validation.py",
            "run",
        ):
            calls.append((command, kwargs))
            (source / "README.md").write_text("changed while local pytest ran\n")
            return SimpleNamespace(returncode=0)
        return original_run(command, **kwargs)

    monkeypatch.setattr(runner.subprocess, "run", run)
    with pytest.raises(ValueError, match="producer candidate differs"):
        runner.produce_local_reports(
            source, manifest, inventory, plan, tmp_path / "local-drift", 1
        )
    assert len(calls) == 2
