"""Run the single topology-sensitive pytest registry in isolated local clones."""

# pyright: reportMissingImports=false

from __future__ import annotations

import argparse
import base64
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable, Mapping


SCHEMA = "pietto.gate2.topology-results.v1"
BASE = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
BRANCH = "phase54/post-slice6-workflow-efficiency"
SUBJECT = "Add Pietto lean end-to-end workflow infrastructure"
ORIGIN_MAIN_FETCH = "+refs/heads/main:refs/remotes/origin/main"
CENTRAL_NODE = (
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_"
    "bounded_let_visibility_contract.py::"
    "test_reconciled_main_maintenance_handoff_and_build_backend_are_locked"
)
NEGATIVE_CASES = (
    "wrong_base",
    "wrong_candidate",
    "reversed_parents",
    "missing_parent",
    "extra_parent",
    "non_shallow_pr",
    "arbitrary_subject",
    "malformed_suffix",
    "non_decimal_suffix",
    "wrong_push_ref",
    "wrong_push_sha",
    "divergent_origin_main",
    "dirty_state",
    "staged_state",
    "stale_slice5_manifest",
    "two_commit_main",
    "detached_non_main_full_history",
    "wrong_pr_base_ref",
    "wrong_pr_head_ref",
    "non_shallow_main_push",
    "depth_one_active_gate2",
    "successor_unpublished",
    "no_diff",
    "protected_tree_mismatch",
)
ACTIVE_DEPTH_NODE = (
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py::"
    "test_dirty_untracked_clean_and_depth_one_states_are_all_modeled"
)
OUTCOME_SCHEMA = "pietto.gate2.pytest-outcomes.v1"
OUTCOME_ENV = "PIETTO_GATE2_PYTEST_OUTCOMES"


_PLUGIN_COLLECTED: list[str] = []
_PLUGIN_DESELECTED: list[str] = []
_PLUGIN_COLLECTION_ERRORS: list[str] = []
_PLUGIN_REPORTS: dict[str, dict[str, dict[str, object]]] = {}


def pytest_collection_finish(session: Any) -> None:
    """Capture the complete expanded collection for one isolated invocation."""

    _PLUGIN_COLLECTED[:] = [item.nodeid for item in session.items]


def pytest_deselected(items: list[Any]) -> None:
    _PLUGIN_DESELECTED.extend(item.nodeid for item in items)


def pytest_collectreport(report: Any) -> None:
    if report.failed:
        _PLUGIN_COLLECTION_ERRORS.append(str(report.longrepr))


def pytest_runtest_logreport(report: Any) -> None:
    phases = _PLUGIN_REPORTS.setdefault(report.nodeid, {})
    phases[report.when] = {
        "outcome": report.outcome,
        "was_xfail": bool(getattr(report, "wasxfail", False)),
    }


def _final_outcome(phases: Mapping[str, Mapping[str, object]]) -> str:
    if any(bool(phase.get("was_xfail")) for phase in phases.values()):
        call = phases.get("call", {})
        return "xpass" if call.get("outcome") == "passed" else "xfail"
    if any(phase.get("outcome") == "skipped" for phase in phases.values()):
        return "skipped"
    if (
        phases.get("setup", {}).get("outcome") == "failed"
        or phases.get("teardown", {}).get("outcome") == "failed"
    ):
        return "error"
    if phases.get("call", {}).get("outcome") == "failed":
        return "failed"
    if phases.get("call", {}).get("outcome") == "passed":
        return "passed"
    return "error"


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    del session
    output = os.environ.get(OUTCOME_ENV)
    if not output:
        return
    items = []
    summary: dict[str, int] = {
        name: 0 for name in ("passed", "failed", "error", "skipped", "xfail", "xpass")
    }
    for node_id in sorted(_PLUGIN_COLLECTED):
        phases = _PLUGIN_REPORTS.get(node_id, {})
        final = _final_outcome(phases)
        summary[final] += 1
        items.append({"node_id": node_id, "phases": phases, "final": final})
    document = {
        "schema": OUTCOME_SCHEMA,
        "exitstatus": int(exitstatus),
        "collected_count": len(_PLUGIN_COLLECTED),
        "collected_node_ids": sorted(_PLUGIN_COLLECTED),
        "deselected": sorted(_PLUGIN_DESELECTED),
        "collection_errors": sorted(_PLUGIN_COLLECTION_ERRORS),
        "items": items,
        "summary": summary,
    }
    Path(output).write_bytes(_canonical_json(document))


class TopologyCheckError(RuntimeError):
    """Raised for a malformed projection or unexpected pytest outcome."""


class ProjectionRejected(RuntimeError):
    """One exact projection validator rejection with a stable code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProjectionIdentity:
    name: str
    head: str
    parents: tuple[str, ...]
    tree: str
    shallow: bool
    branch: str
    event: str | None
    github_ref: str | None
    github_sha: str | None
    subject: str = ""
    main_oid: str = ""
    origin_main_oid: str = ""
    status: str = ""
    staged: str = ""
    depth: int = 0
    event_path: str | None = None
    event_payload_sha256: str | None = None
    upstream: str = ""
    refs: tuple[tuple[str, str], ...] = ()


def _canonical_json(document: object) -> bytes:
    return (
        json.dumps(
            document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _run(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        check=check,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _git(
    repo: Path,
    *args: str,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> str:
    return _run(["git", *args], cwd=repo, env=env, check=check).stdout.strip()


def _optional_ref(repo: Path, ref: str) -> str:
    result = _run(["git", "rev-parse", "--verify", ref], cwd=repo, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def _refs(repo: Path) -> tuple[tuple[str, str], ...]:
    rows: list[tuple[str, str]] = []
    for line in _git(
        repo, "for-each-ref", "--format=%(refname)%00%(objectname)"
    ).splitlines():
        ref, separator, oid = line.partition("\0")
        if separator != "\0" or not ref or not oid:
            raise TopologyCheckError(f"malformed ref identity: {line!r}")
        rows.append((ref, oid))
    return tuple(sorted(rows))


def _set_exact_refs(repo: Path, refs: Mapping[str, str]) -> None:
    for ref, _ in _refs(repo):
        if ref not in refs:
            _git(repo, "update-ref", "--no-deref", "-d", ref)
    for ref, oid in sorted(refs.items()):
        _git(repo, "update-ref", ref, oid)


def _set_origin_main_upstream(repo: Path) -> None:
    _git(
        repo,
        "config",
        "--replace-all",
        "remote.origin.fetch",
        ORIGIN_MAIN_FETCH,
    )
    _git(repo, "branch", "--set-upstream-to=origin/main", "main")


def _commit_environment() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "GIT_AUTHOR_NAME": "Pietto Topology Audit",
            "GIT_AUTHOR_EMAIL": "topology@example.invalid",
            "GIT_COMMITTER_NAME": "Pietto Topology Audit",
            "GIT_COMMITTER_EMAIL": "topology@example.invalid",
            "GIT_AUTHOR_DATE": "2026-07-30T22:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-07-30T22:00:00+00:00",
        }
    )
    return env


def _commit_tree(
    repo: Path,
    tree: str,
    *,
    parents: tuple[str, ...],
    subject: str,
    ref: str,
) -> str:
    args = ["commit-tree", tree]
    for parent in parents:
        args.extend(("-p", parent))
    args.extend(("-m", subject))
    commit = _git(repo, *args, env=_commit_environment())
    _git(repo, "update-ref", ref, commit)
    return commit


def _apply_active_overlay(
    *, root: Path, target_root: Path, base: str, statuses: Mapping[str, str]
) -> None:
    changed_paths = tuple(sorted(statuses))
    tracked = tuple(path for path in changed_paths if statuses[path] != "A")
    if tracked:
        patch = _run(
            ["git", "diff", "--binary", "--full-index", base, "--", *tracked],
            cwd=root,
        ).stdout
        if patch:
            _run(["git", "apply", "--binary", "-"], cwd=target_root, input_text=patch)
    for relative in changed_paths:
        origin = root / relative
        target = target_root / relative
        if statuses[relative] == "A":
            _reject_unless(origin.is_file(), "OVERLAY_ADDED_SOURCE")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
        elif statuses[relative] == "D":
            _reject_unless(not origin.exists(), "OVERLAY_DELETED_SOURCE")
            target.unlink()


def _copy_active_tree(
    *, root: Path, source: Path, base: str, statuses: Mapping[str, str]
) -> tuple[str, str]:
    changed_paths = tuple(sorted(statuses))
    _run(
        ["git", "clone", "--local", "--no-hardlinks", str(root), str(source)],
        cwd=root,
    )
    _git(source, "switch", "--detach", base)
    _apply_active_overlay(root=root, target_root=source, base=base, statuses=statuses)
    _git(source, "add", "--", *changed_paths)
    staged = _committed_statuses(source, base, "--cached")
    if staged != dict(statuses):
        raise TopologyCheckError(f"candidate manifest drift: {staged}")
    candidate = _git(
        source,
        "commit",
        "--no-gpg-sign",
        "-m",
        SUBJECT,
        env=_commit_environment(),
    )
    del candidate
    candidate_sha = _git(source, "rev-parse", "HEAD")
    tree = _git(source, "rev-parse", "HEAD^{tree}")
    _git(source, "branch", "-f", BRANCH, candidate_sha)
    _git(source, "branch", "-f", "main", base)
    _git(source, "update-ref", "refs/remotes/origin/main", base)
    return candidate_sha, tree


def _clone(
    source: Path,
    target: Path,
    ref: str,
    *,
    depth: int | None = None,
) -> Path:
    command = ["git", "clone"]
    if depth is not None:
        command.extend(("--depth", str(depth)))
    command.extend(("--branch", ref, f"file://{source}", str(target)))
    _run(command, cwd=source)
    return target


def _event_file(
    repo: Path,
    *,
    base_sha: str,
    candidate_sha: str,
    base_ref: str = "main",
    head_ref: str = BRANCH,
) -> Path:
    path = repo.parent / f"{repo.name}-event.json"
    path.write_bytes(
        _canonical_json(
            {
                "pull_request": {
                    "base": {"ref": base_ref, "sha": base_sha},
                    "head": {"ref": head_ref, "sha": candidate_sha},
                }
            }
        )
    )
    return path


def _push_event_file(repo: Path, *, before: str, after: str) -> Path:
    path = repo.parent / f"{repo.name}-event.json"
    path.write_bytes(
        _canonical_json(
            {
                "after": after,
                "before": before,
                "deleted": False,
                "forced": False,
                "ref": "refs/heads/main",
            }
        )
    )
    return path


def _pytest_environment(
    repo: Path,
    *,
    event: str | None = None,
    event_path: Path | None = None,
    github_ref: str | None = None,
    github_sha: str | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    for key in ("GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REF", "GITHUB_SHA"):
        env.pop(key, None)
    env["UV_OFFLINE"] = "1"
    env["UV_NO_SYNC"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        (str(repo / "src"), str(repo / "tests"), str(repo / "scripts"))
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if event is not None:
        env["GITHUB_EVENT_NAME"] = event
    if event_path is not None:
        env["GITHUB_EVENT_PATH"] = str(event_path)
    if github_ref is not None:
        env["GITHUB_REF"] = github_ref
    if github_sha is not None:
        env["GITHUB_SHA"] = github_sha
    return env


def _identity(repo: Path, name: str, env: dict[str, str]) -> ProjectionIdentity:
    head = _git(repo, "rev-parse", "HEAD")
    raw_commit = _git(repo, "cat-file", "-p", "HEAD")
    commit_header, separator, message = raw_commit.partition("\n\n")
    if separator != "\n\n" or not message:
        raise TopologyCheckError("malformed projected commit identity")
    parents = tuple(
        line.removeprefix("parent ")
        for line in commit_header.splitlines()
        if line.startswith("parent ")
    )
    tree_lines = [
        line.removeprefix("tree ")
        for line in commit_header.splitlines()
        if line.startswith("tree ")
    ]
    if len(tree_lines) != 1:
        raise TopologyCheckError("malformed projected commit tree")
    tree = tree_lines[0]
    event_path = env.get("GITHUB_EVENT_PATH")
    event_payload_sha256 = None
    if event_path:
        event_payload_sha256 = hashlib.sha256(Path(event_path).read_bytes()).hexdigest()
    return ProjectionIdentity(
        name=name,
        head=head,
        parents=parents,
        tree=tree,
        shallow=_git(repo, "rev-parse", "--is-shallow-repository") == "true",
        branch=_git(repo, "branch", "--show-current"),
        event=env.get("GITHUB_EVENT_NAME"),
        github_ref=env.get("GITHUB_REF"),
        github_sha=env.get("GITHUB_SHA"),
        subject=message.partition("\n")[0],
        main_oid=_optional_ref(repo, "refs/heads/main"),
        origin_main_oid=_optional_ref(repo, "refs/remotes/origin/main"),
        status=_git(repo, "status", "--porcelain=v1", "--untracked-files=all"),
        staged=_git(repo, "diff", "--cached", "--name-status"),
        depth=int(_git(repo, "rev-list", "--count", "HEAD")),
        event_path=event_path,
        event_payload_sha256=event_payload_sha256,
        upstream=_git(
            repo,
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
            check=False,
        ),
        refs=_refs(repo),
    )


def _reject_unless(condition: bool, code: str) -> None:
    if not condition:
        raise ProjectionRejected(code)


def _committed_statuses(repo: Path, base: str, head: str = "HEAD") -> dict[str, str]:
    result: dict[str, str] = {}
    revision_args = ("--cached", base) if head == "--cached" else (base, head)
    output = _git(repo, "diff", "--name-status", "--no-renames", *revision_args)
    for line in output.splitlines():
        status, separator, path = line.partition("\t")
        if not separator or status not in {"A", "M", "D"} or path in result:
            raise TopologyCheckError(f"malformed committed name-status row: {line!r}")
        result[path] = status
    return result


def validate_projection(
    *,
    profile: str,
    repo: Path,
    env: dict[str, str],
    candidate: str,
    reviewed_tree: str,
    statuses: Mapping[str, str],
) -> ProjectionIdentity:
    """Validate one complete positive topology or raise one stable code."""

    identity = _identity(repo, profile, env)
    _reject_unless(identity.staged == "", "INDEX_EMPTY")
    _reject_unless(identity.status == "", "WORKTREE_CLEAN")
    if profile == "candidate":
        _reject_unless(identity.parents == (BASE,), "CANDIDATE_PARENT")
        _reject_unless(identity.subject == SUBJECT, "CANDIDATE_SUBJECT")
        _reject_unless(identity.branch == BRANCH, "CANDIDATE_BRANCH")
        _reject_unless(not identity.shallow, "CANDIDATE_NONSHALLOW")
        _reject_unless(identity.upstream == "", "CANDIDATE_UPSTREAM")
        _reject_unless(identity.main_oid == BASE, "CANDIDATE_MAIN")
        _reject_unless(identity.origin_main_oid == BASE, "CANDIDATE_ORIGIN_MAIN")
        _reject_unless(
            _committed_statuses(repo, BASE) == dict(statuses),
            "CANDIDATE_DIFF_MANIFEST",
        )
        _reject_unless(identity.tree == reviewed_tree, "REVIEWED_TREE")
        _reject_unless(identity.event is None, "CANDIDATE_EVENT")
        return identity
    if profile == "pr_merge":
        _reject_unless(len(identity.parents) == 2, "PR_PARENT_COUNT")
        _reject_unless(identity.parents == (BASE, candidate), "PR_PARENT_ORDER")
        _reject_unless(identity.tree == reviewed_tree, "REVIEWED_TREE")
        _reject_unless(identity.shallow and identity.depth == 1, "PR_SHALLOW_REQUIRED")
        _reject_unless(identity.branch == "", "PR_DETACHED_REQUIRED")
        _reject_unless(identity.upstream == "", "PR_UPSTREAM")
        _reject_unless(identity.event == "pull_request", "PR_EVENT")
        _reject_unless(identity.github_ref == "refs/pull/999/merge", "PR_REF")
        _reject_unless(identity.github_sha == identity.head, "PR_SHA")
        event_path = identity.event_path
        _reject_unless(event_path is not None, "PR_EVENT_PATH")
        if event_path is None:
            raise TopologyCheckError("PR_EVENT_PATH")
        payload = json.loads(Path(event_path).read_bytes())
        pull_request = payload.get("pull_request", {})
        base = pull_request.get("base", {})
        head = pull_request.get("head", {})
        _reject_unless(base.get("sha") == BASE, "PR_PAYLOAD_BASE_SHA")
        _reject_unless(base.get("ref") == "main", "PR_PAYLOAD_BASE_REF")
        _reject_unless(head.get("sha") == candidate, "PR_PAYLOAD_HEAD_SHA")
        _reject_unless(head.get("ref") == BRANCH, "PR_PAYLOAD_HEAD_REF")
        _reject_unless(
            identity.refs == (("refs/remotes/pull/999/merge", identity.head),),
            "PR_REFS",
        )
        return identity
    if profile == "main_push":
        _reject_unless(identity.parents == (BASE,), "PUSH_PARENT")
        _reject_unless(
            re.fullmatch(rf"{re.escape(SUBJECT)} \(#[0-9]+\)", identity.subject)
            is not None,
            "PUSH_SUBJECT",
        )
        _reject_unless(identity.tree == reviewed_tree, "REVIEWED_TREE")
        _reject_unless(
            identity.shallow and identity.depth == 1, "PUSH_SHALLOW_REQUIRED"
        )
        _reject_unless(identity.branch == "main", "PUSH_BRANCH")
        _reject_unless(identity.upstream == "origin/main", "PUSH_UPSTREAM")
        _reject_unless(identity.main_oid == identity.head, "PUSH_MAIN")
        _reject_unless(identity.origin_main_oid == identity.head, "PUSH_ORIGIN_MAIN")
        _reject_unless(identity.event == "push", "PUSH_EVENT")
        _reject_unless(identity.github_ref == "refs/heads/main", "PUSH_REF")
        _reject_unless(identity.github_sha == identity.head, "PUSH_SHA")
        event_path = identity.event_path
        _reject_unless(event_path is not None, "PUSH_EVENT_PATH")
        if event_path is None:
            raise TopologyCheckError("PUSH_EVENT_PATH")
        payload = json.loads(Path(event_path).read_bytes())
        _reject_unless(isinstance(payload, dict), "PUSH_EVENT_PAYLOAD")
        _reject_unless(payload.get("before") == BASE, "PUSH_PAYLOAD_BEFORE")
        _reject_unless(payload.get("after") == identity.head, "PUSH_PAYLOAD_AFTER")
        _reject_unless(payload.get("ref") == "refs/heads/main", "PUSH_PAYLOAD_REF")
        _reject_unless(payload.get("deleted") is False, "PUSH_PAYLOAD_DELETED")
        _reject_unless(payload.get("forced") is False, "PUSH_PAYLOAD_FORCED")
        _reject_unless(
            identity.refs
            == (
                ("refs/heads/main", identity.head),
                ("refs/remotes/origin/main", identity.head),
            ),
            "PUSH_REFS",
        )
        return identity
    if profile == "reconciled_main":
        if identity.subject.startswith("Start Phase 54 Slice 7"):
            raise ProjectionRejected("SUCCESSOR_FORBIDDEN")
        _reject_unless(identity.parents == (BASE,), "SQUASH_PARENT")
        _reject_unless(
            re.fullmatch(rf"{re.escape(SUBJECT)} \(#[0-9]+\)", identity.subject)
            is not None,
            "SQUASH_SUBJECT",
        )
        _reject_unless(identity.tree == reviewed_tree, "REVIEWED_TREE")
        _reject_unless(not identity.shallow, "RECONCILED_NONSHALLOW")
        _reject_unless(identity.branch == "main", "RECONCILED_BRANCH")
        _reject_unless(identity.upstream == "origin/main", "RECONCILED_UPSTREAM")
        _reject_unless(identity.main_oid == identity.head, "RECONCILED_MAIN")
        _reject_unless(identity.origin_main_oid == identity.head, "ORIGIN_MAIN")
        _reject_unless(identity.event is None, "RECONCILED_EVENT")
        _reject_unless(
            identity.refs
            == (
                ("refs/heads/main", identity.head),
                ("refs/remotes/origin/main", identity.head),
            ),
            "RECONCILED_REFS",
        )
        return identity
    raise TopologyCheckError(f"unknown projection profile: {profile}")


def _pytest(
    *,
    python: Path,
    repo: Path,
    nodes: Iterable[str],
    env: dict[str, str],
    expect_success: bool,
    label: str,
    expected_items: int | None = None,
) -> dict[str, object]:
    node_tuple = tuple(nodes)
    outcome_path = repo.parent / f"pytest-outcomes-{label}.json"
    run_env = dict(env)
    run_env[OUTCOME_ENV] = str(outcome_path)
    command = [
        str(python),
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-p",
        "run_gate2_topology_checks",
        *node_tuple,
    ]
    started_wall = time.monotonic()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    result = _run(command, cwd=repo, env=run_env, check=False)
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    wall = time.monotonic() - started_wall
    cpu = (usage_after.ru_utime + usage_after.ru_stime) - (
        usage_before.ru_utime + usage_before.ru_stime
    )
    if not outcome_path.is_file():
        raise TopologyCheckError(
            f"pytest outcome plugin did not create {outcome_path}: "
            f"{result.stdout}\n{result.stderr}"
        )
    outcome_payload = outcome_path.read_bytes()
    outcome = json.loads(outcome_payload)
    if not isinstance(outcome, dict) or outcome.get("schema") != OUTCOME_SCHEMA:
        raise TopologyCheckError("malformed pytest outcome document")
    if outcome_payload != _canonical_json(outcome):
        raise TopologyCheckError("pytest outcome document is not canonical JSON")
    summary = outcome.get("summary")
    if not isinstance(summary, dict):
        raise TopologyCheckError("pytest outcome summary is absent")
    if outcome.get("deselected") or outcome.get("collection_errors"):
        raise TopologyCheckError("pytest deselection or collection error")
    if expected_items is not None and outcome.get("collected_count") != expected_items:
        raise TopologyCheckError(
            f"pytest item count drift for {label}: {outcome.get('collected_count')}"
        )
    success = result.returncode == 0
    if result.returncode not in {0, 1} or success != expect_success:
        raise TopologyCheckError(
            f"unexpected pytest result {result.returncode}: {result.stdout}\n{result.stderr}"
        )
    forbidden = sum(
        int(summary.get(name, 0)) for name in ("error", "skipped", "xfail", "xpass")
    )
    if forbidden:
        raise TopologyCheckError(f"forbidden pytest outcomes for {label}: {summary}")
    if expect_success is True and int(summary.get("passed", 0)) != outcome.get(
        "collected_count"
    ):
        raise TopologyCheckError(f"positive projection did not fully pass: {summary}")
    if expect_success is False and int(summary.get("failed", 0)) < 1:
        raise TopologyCheckError(
            "negative case did not fail through a call-phase assertion"
        )
    if int(summary.get("passed", 0)) + int(summary.get("failed", 0)) != outcome.get(
        "collected_count"
    ):
        raise TopologyCheckError(f"pytest outcomes are incomplete: {summary}")
    return {
        "argv": command,
        "returncode": result.returncode,
        "result": "PASS" if expect_success else "REJECTED",
        "wall_seconds": round(wall, 6),
        "cpu_seconds": round(cpu, 6),
        "stdout_bytes": len(result.stdout.encode()),
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stdout_base64": base64.b64encode(result.stdout.encode()).decode("ascii"),
        "stderr_bytes": len(result.stderr.encode()),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "stderr_base64": base64.b64encode(result.stderr.encode()).decode("ascii"),
        "outcomes": outcome,
        "outcomes_sha256": hashlib.sha256(outcome_payload).hexdigest(),
    }


def projection_plan(
    *, candidate: str, pr_merge: str, squash: str, tree: str
) -> tuple[ProjectionIdentity, ...]:
    """Return the exact four positive identities without touching Git state."""

    return (
        ProjectionIdentity(
            "candidate", candidate, (BASE,), tree, False, BRANCH, None, None, None
        ),
        ProjectionIdentity(
            "pr_merge",
            pr_merge,
            (BASE, candidate),
            tree,
            True,
            "",
            "pull_request",
            "refs/pull/999/merge",
            pr_merge,
        ),
        ProjectionIdentity(
            "main_push",
            squash,
            (BASE,),
            tree,
            True,
            "main",
            "push",
            "refs/heads/main",
            squash,
        ),
        ProjectionIdentity(
            "reconciled_main", squash, (BASE,), tree, False, "main", None, None, None
        ),
    )


def _prepare_positive_repositories(
    *, source: Path, root: Path, candidate: str, tree: str
) -> tuple[str, str, dict[str, tuple[Path, dict[str, str]]]]:
    pr_merge = _commit_tree(
        source,
        tree,
        parents=(BASE, candidate),
        subject=f"Merge {candidate} into {BASE}",
        ref="refs/heads/synthetic/pr",
    )
    squash = _commit_tree(
        source,
        tree,
        parents=(BASE,),
        subject=f"{SUBJECT} (#999)",
        ref="refs/heads/synthetic/main",
    )
    candidate_repo = _clone(source, root / "candidate", BRANCH)
    _git(candidate_repo, "branch", "--unset-upstream", check=False)
    _git(candidate_repo, "branch", "-f", "main", BASE)
    _git(candidate_repo, "update-ref", "refs/remotes/origin/main", BASE)
    pr_repo = _clone(source, root / "pr", "synthetic/pr", depth=1)
    _git(pr_repo, "switch", "--detach", pr_merge)
    _set_exact_refs(pr_repo, {"refs/remotes/pull/999/merge": pr_merge})
    pr_event = _event_file(pr_repo, base_sha=BASE, candidate_sha=candidate)
    push_repo = _clone(source, root / "push", "synthetic/main", depth=1)
    _git(push_repo, "branch", "-m", "main")
    _set_exact_refs(
        push_repo,
        {"refs/heads/main": squash, "refs/remotes/origin/main": squash},
    )
    _set_origin_main_upstream(push_repo)
    push_event = _push_event_file(push_repo, before=BASE, after=squash)
    reconciled_repo = _clone(source, root / "reconciled", "synthetic/main")
    _git(reconciled_repo, "branch", "-m", "main")
    _set_exact_refs(
        reconciled_repo,
        {"refs/heads/main": squash, "refs/remotes/origin/main": squash},
    )
    _set_origin_main_upstream(reconciled_repo)
    projections = {
        "candidate": (candidate_repo, _pytest_environment(candidate_repo)),
        "pr_merge": (
            pr_repo,
            _pytest_environment(
                pr_repo,
                event="pull_request",
                event_path=pr_event,
                github_ref="refs/pull/999/merge",
                github_sha=pr_merge,
            ),
        ),
        "main_push": (
            push_repo,
            _pytest_environment(
                push_repo,
                event="push",
                event_path=push_event,
                github_ref="refs/heads/main",
                github_sha=squash,
            ),
        ),
        "reconciled_main": (
            reconciled_repo,
            _pytest_environment(reconciled_repo),
        ),
    }
    return pr_merge, squash, projections


def _set_topic_refs(repo: Path) -> None:
    _git(repo, "branch", "-f", "main", BASE)
    _git(repo, "update-ref", "refs/remotes/origin/main", BASE)


def _set_main(repo: Path, head: str, *, origin: str | None = None) -> None:
    current = _git(repo, "branch", "--show-current")
    if current == "main":
        _git(repo, "switch", "--detach")
    _git(repo, "branch", "-f", "main", head)
    _git(repo, "switch", "main")
    _git(repo, "update-ref", "refs/remotes/origin/main", origin or head)
    _set_origin_main_upstream(repo)


def _negative_commits(
    *, source: Path, tree: str, candidate: str, squash: str
) -> dict[str, str]:
    previous = "c44a4271d9592cb393d2232f127a59d8466cc60a"
    base_tree = _git(source, "rev-parse", f"{BASE}^{{tree}}")
    _git(source, "read-tree", tree)
    altered_payload = (source / "AGENTS.md").read_text(encoding="utf-8") + (
        "\n<!-- topology reviewed-tree mismatch -->\n"
    )
    altered_blob = _run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=source,
        input_text=altered_payload,
    ).stdout.strip()
    _git(source, "update-index", "--cacheinfo", "100644", altered_blob, "AGENTS.md")
    altered_tree = _git(source, "write-tree")
    _git(source, "read-tree", tree)
    specifications = {
        "wrong_base": (tree, (previous,), SUBJECT),
        "reversed_parents": (tree, (candidate, BASE), "Synthetic PR"),
        "missing_parent": (tree, (BASE,), "Synthetic PR"),
        "extra_parent": (tree, (BASE, candidate, previous), "Synthetic PR"),
        "arbitrary_subject": (tree, (BASE,), "Arbitrary subject"),
        "malformed_suffix": (tree, (BASE,), f"{SUBJECT} (#999"),
        "non_decimal_suffix": (tree, (BASE,), f"{SUBJECT} (#abc)"),
        "two_commit_main": (tree, (candidate,), f"{SUBJECT} (#1000)"),
        "successor_unpublished": (
            tree,
            (squash,),
            "Start Phase 54 Slice 7 imports",
        ),
        "no_diff": (base_tree, (BASE,), SUBJECT),
        "protected_tree_mismatch": (altered_tree, (BASE,), SUBJECT),
    }
    return {
        name: _commit_tree(
            source,
            commit_tree,
            parents=parents,
            subject=subject,
            ref=f"refs/heads/negative/{name}",
        )
        for name, (commit_tree, parents, subject) in specifications.items()
    }


def _working_statuses(repo: Path) -> dict[str, str]:
    result = _committed_statuses(repo, "HEAD", "--cached")
    if result:
        raise TopologyCheckError("working-status helper requires an empty index")
    worktree: dict[str, str] = {}
    for line in _git(repo, "diff", "--name-status", "--no-renames").splitlines():
        status, separator, path = line.partition("\t")
        if not separator or status not in {"M", "D"} or path in worktree:
            raise TopologyCheckError(f"malformed worktree row: {line!r}")
        worktree[path] = status
    for path in _git(repo, "ls-files", "--others", "--exclude-standard").splitlines():
        if not path or path in worktree:
            raise TopologyCheckError(f"malformed untracked path: {path!r}")
        worktree[path] = "A"
    return worktree


def _run_negative_matrix(
    *,
    primary_root: Path,
    source: Path,
    temporary_root: Path,
    python: Path,
    candidate: str,
    pr_merge: str,
    squash: str,
    tree: str,
    statuses: Mapping[str, str],
) -> list[dict[str, object]]:
    del pr_merge
    commits = _negative_commits(
        source=source, tree=tree, candidate=candidate, squash=squash
    )
    expected_codes = {
        "wrong_base": "CANDIDATE_PARENT",
        "wrong_candidate": "PR_PAYLOAD_HEAD_SHA",
        "reversed_parents": "PR_PARENT_ORDER",
        "missing_parent": "PR_PARENT_COUNT",
        "extra_parent": "PR_PARENT_COUNT",
        "non_shallow_pr": "PR_SHALLOW_REQUIRED",
        "arbitrary_subject": "SQUASH_SUBJECT",
        "malformed_suffix": "SQUASH_SUBJECT",
        "non_decimal_suffix": "SQUASH_SUBJECT",
        "wrong_push_ref": "PUSH_REF",
        "wrong_push_sha": "PUSH_SHA",
        "divergent_origin_main": "ORIGIN_MAIN",
        "dirty_state": "WORKTREE_CLEAN",
        "staged_state": "INDEX_EMPTY",
        "stale_slice5_manifest": "MANIFEST_MARKER",
        "two_commit_main": "SQUASH_PARENT",
        "detached_non_main_full_history": "CANDIDATE_BRANCH",
        "wrong_pr_base_ref": "PR_PAYLOAD_BASE_REF",
        "wrong_pr_head_ref": "PR_PAYLOAD_HEAD_REF",
        "non_shallow_main_push": "PUSH_SHALLOW_REQUIRED",
        "depth_one_active_gate2": "ACTIVE_MANIFEST_NONSHALLOW",
        "successor_unpublished": "SUCCESSOR_FORBIDDEN",
        "no_diff": "CANDIDATE_DIFF_MANIFEST",
        "protected_tree_mismatch": "REVIEWED_TREE",
    }
    results: list[dict[str, object]] = []

    def reject(
        name: str,
        repo: Path,
        profile: str,
        env: dict[str, str] | None = None,
        *,
        node: str | None = CENTRAL_NODE,
        expected_items: int | None = 1,
    ) -> None:
        effective_env = env or _pytest_environment(repo)
        try:
            validate_projection(
                profile=profile,
                repo=repo,
                env=effective_env,
                candidate=candidate,
                reviewed_tree=tree,
                statuses=statuses,
            )
        except ProjectionRejected as error:
            actual_code = error.code
        else:
            raise TopologyCheckError(f"negative projection was accepted: {name}")
        expected_code = expected_codes[name]
        if actual_code != expected_code:
            raise TopologyCheckError(
                f"negative rejection drift for {name}: {actual_code} != {expected_code}"
            )
        pytest_result = None
        if node is not None:
            pytest_result = _pytest(
                python=python,
                repo=repo,
                nodes=(node,),
                env=effective_env,
                expect_success=False,
                label=f"negative-{name}",
                expected_items=expected_items,
            )
        results.append(
            {
                "name": name,
                "profile": profile,
                "expected_rejection_code": expected_code,
                "actual_rejection_code": actual_code,
                "identity": asdict(_identity(repo, name, effective_env)),
                "pytest": pytest_result,
                "result": "REJECTED",
            }
        )

    def pr_environment(
        repo: Path,
        *,
        event_candidate: str = candidate,
        base_ref: str = "main",
        head_ref: str = BRANCH,
    ) -> dict[str, str]:
        event = _event_file(
            repo,
            base_sha=BASE,
            candidate_sha=event_candidate,
            base_ref=base_ref,
            head_ref=head_ref,
        )
        return _pytest_environment(
            repo,
            event="pull_request",
            event_path=event,
            github_ref="refs/pull/999/merge",
            github_sha=_git(repo, "rev-parse", "HEAD"),
        )

    repo = _clone(source, temporary_root / "negative-wrong-base", "negative/wrong_base")
    _git(repo, "branch", "-m", BRANCH)
    _git(repo, "branch", "--unset-upstream", check=False)
    _set_topic_refs(repo)
    reject("wrong_base", repo, "candidate")

    repo = _clone(
        source, temporary_root / "negative-wrong-candidate", "synthetic/pr", depth=1
    )
    _git(repo, "switch", "--detach")
    reject(
        "wrong_candidate",
        repo,
        "pr_merge",
        pr_environment(repo, event_candidate=squash),
    )

    for name in ("reversed_parents", "missing_parent", "extra_parent"):
        repo = _clone(
            source, temporary_root / f"negative-{name}", f"negative/{name}", depth=1
        )
        _git(repo, "switch", "--detach")
        reject(name, repo, "pr_merge", pr_environment(repo))

    repo = _clone(source, temporary_root / "negative-non-shallow-pr", "synthetic/pr")
    _git(repo, "switch", "--detach")
    reject("non_shallow_pr", repo, "pr_merge", pr_environment(repo))

    for name in ("arbitrary_subject", "malformed_suffix", "non_decimal_suffix"):
        repo = _clone(source, temporary_root / f"negative-{name}", f"negative/{name}")
        _set_main(repo, commits[name])
        reject(name, repo, "reconciled_main")

    for name, wrong_ref, wrong_sha in (
        ("wrong_push_ref", "refs/heads/topic", squash),
        ("wrong_push_sha", "refs/heads/main", candidate),
    ):
        repo = _clone(
            source, temporary_root / f"negative-{name}", "synthetic/main", depth=1
        )
        _git(repo, "branch", "-m", "main")
        _git(repo, "update-ref", "refs/remotes/origin/main", squash)
        _set_origin_main_upstream(repo)
        event = _push_event_file(repo, before=BASE, after=squash)
        env = _pytest_environment(
            repo,
            event="push",
            event_path=event,
            github_ref=wrong_ref,
            github_sha=wrong_sha,
        )
        reject(name, repo, "main_push", env)

    repo = _clone(
        source, temporary_root / "negative-divergent-origin", "synthetic/main"
    )
    _set_main(repo, squash, origin=BASE)
    reject("divergent_origin_main", repo, "reconciled_main")

    repo = _clone(source, temporary_root / "negative-dirty", BRANCH)
    _git(repo, "branch", "--unset-upstream", check=False)
    _set_topic_refs(repo)
    (repo / "unrelated.txt").write_text("dirty\n", encoding="utf-8")
    reject("dirty_state", repo, "candidate")

    repo = _clone(source, temporary_root / "negative-staged", BRANCH)
    _git(repo, "branch", "--unset-upstream", check=False)
    _set_topic_refs(repo)
    (repo / "README.md").write_text(
        (repo / "README.md").read_text(encoding="utf-8") + "\nstaged\n",
        encoding="utf-8",
    )
    _git(repo, "add", "README.md")
    reject("staged_state", repo, "candidate")

    sys.path.insert(0, str(source / "tests"))
    from _active_gate2_manifest import (  # noqa: PLC0415
        ActiveGate2RepositoryState,
        _matches_active_gate2_manifest,
    )

    stale = ActiveGate2RepositoryState(
        marker="PHASE54_SLICE5_GATE2",
        branch_oid=BASE,
        branch_head="main",
        branch_upstream="origin/main",
        ahead=0,
        behind=0,
        head_parents=("c44a4271d9592cb393d2232f127a59d8466cc60a",),
        head_subject="Complete Phase 54 local import module export Slice 6",
        main_oid=BASE,
        origin_main_oid=BASE,
        committed_added_paths=frozenset(),
        committed_modified_paths=frozenset(),
        committed_deleted_paths=frozenset(),
        added_paths=frozenset(statuses),
        modified_paths=frozenset(),
        deleted_paths=frozenset(),
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )
    if _matches_active_gate2_manifest(stale):
        raise TopologyCheckError("stale Slice 5 manifest was accepted")
    results.append(
        {
            "name": "stale_slice5_manifest",
            "profile": "active_dirty",
            "expected_rejection_code": expected_codes["stale_slice5_manifest"],
            "actual_rejection_code": "MANIFEST_MARKER",
            "validator": "_matches_active_gate2_manifest",
            "pytest": None,
            "result": "REJECTED",
        }
    )

    repo = _clone(
        source, temporary_root / "negative-two-commit", "negative/two_commit_main"
    )
    _set_main(repo, commits["two_commit_main"])
    reject("two_commit_main", repo, "reconciled_main")

    repo = _clone(source, temporary_root / "negative-detached", BRANCH)
    _git(repo, "branch", "--unset-upstream", check=False)
    _set_topic_refs(repo)
    _git(repo, "switch", "--detach", candidate)
    reject("detached_non_main_full_history", repo, "candidate")

    for name, base_ref, head_ref in (
        ("wrong_pr_base_ref", "trunk", BRANCH),
        ("wrong_pr_head_ref", "main", "wrong/topic"),
    ):
        repo = _clone(
            source, temporary_root / f"negative-{name}", "synthetic/pr", depth=1
        )
        _git(repo, "switch", "--detach")
        reject(
            name,
            repo,
            "pr_merge",
            pr_environment(repo, base_ref=base_ref, head_ref=head_ref),
        )

    repo = _clone(
        source, temporary_root / "negative-non-shallow-push", "synthetic/main"
    )
    _git(repo, "branch", "-m", "main")
    _git(repo, "update-ref", "refs/remotes/origin/main", squash)
    event = _push_event_file(repo, before=BASE, after=squash)
    reject(
        "non_shallow_main_push",
        repo,
        "main_push",
        _pytest_environment(
            repo,
            event="push",
            event_path=event,
            github_ref="refs/heads/main",
            github_sha=squash,
        ),
    )

    repo = _clone(source, temporary_root / "negative-depth-one-active", "main", depth=1)
    _apply_active_overlay(
        root=primary_root, target_root=repo, base=BASE, statuses=statuses
    )
    if _working_statuses(repo) != dict(statuses):
        raise TopologyCheckError("depth-one active overlay drift")
    if _git(repo, "rev-parse", "--is-shallow-repository") != "true":
        raise TopologyCheckError("depth-one active projection is not shallow")
    active_env = _pytest_environment(repo)
    active_pytest = _pytest(
        python=python,
        repo=repo,
        nodes=(ACTIVE_DEPTH_NODE,),
        env=active_env,
        expect_success=False,
        label="negative-depth-one-active-gate2",
        expected_items=3,
    )
    results.append(
        {
            "name": "depth_one_active_gate2",
            "profile": "active_dirty",
            "expected_rejection_code": expected_codes["depth_one_active_gate2"],
            "actual_rejection_code": "ACTIVE_MANIFEST_NONSHALLOW",
            "identity": asdict(_identity(repo, "depth_one_active_gate2", active_env)),
            "pytest": active_pytest,
            "result": "REJECTED",
        }
    )

    repo = _clone(
        source, temporary_root / "negative-successor", "negative/successor_unpublished"
    )
    _set_main(repo, commits["successor_unpublished"])
    reject("successor_unpublished", repo, "reconciled_main")

    for name in ("no_diff", "protected_tree_mismatch"):
        repo = _clone(source, temporary_root / f"negative-{name}", f"negative/{name}")
        _git(repo, "branch", "-m", BRANCH)
        _git(repo, "branch", "--unset-upstream", check=False)
        _set_topic_refs(repo)
        reject(name, repo, "candidate", node=None, expected_items=None)

    if tuple(item["name"] for item in results) != NEGATIVE_CASES:
        raise TopologyCheckError("negative matrix order or completeness drift")
    if len(results) != 24 or sum(item["pytest"] is not None for item in results) != 21:
        raise TopologyCheckError("negative execution accounting drift")
    return results


def run_topology_checks(
    *,
    root: Path,
    statuses: Mapping[str, str],
    reader_paths: tuple[str, ...],
    reader_items: int,
    output: Path,
    python: Path,
) -> dict[str, object]:
    """Execute positives and the fail-closed negative matrix in temp clones."""

    sys.path.insert(0, str(root / "tests"))
    from _topology_sensitive_registry import (  # noqa: PLC0415
        TOPOLOGY_REGISTRY_FILES,
        TOPOLOGY_REGISTRY_PAYLOAD,
        TOPOLOGY_REGISTRY_SHA256,
        TOPOLOGY_SELECTED_ITEMS,
        TOPOLOGY_SENSITIVE_NODE_IDS,
    )

    def result_metric(result: Mapping[str, object], group: str, metric: str) -> float:
        metrics = result.get(group)
        if not isinstance(metrics, dict):
            raise TopologyCheckError(f"missing {group} metrics")
        value = metrics.get(metric)
        if not isinstance(value, (int, float)):
            raise TopologyCheckError(f"invalid {group}.{metric} metric")
        return float(value)

    def primary_state() -> dict[str, object]:
        index_path = Path(_git(root, "rev-parse", "--git-path", "index"))
        if not index_path.is_absolute():
            index_path = root / index_path
        payload = index_path.read_bytes()
        return {
            "head": _git(root, "rev-parse", "HEAD"),
            "branch": _git(root, "branch", "--show-current"),
            "status_sha256": hashlib.sha256(
                _git(
                    root,
                    "status",
                    "--porcelain=v2",
                    "--branch",
                    "--untracked-files=all",
                ).encode()
            ).hexdigest(),
            "staged": _git(root, "diff", "--cached", "--name-status"),
            "index_path": str(index_path),
            "index_bytes": len(payload),
            "index_sha256": hashlib.sha256(payload).hexdigest(),
        }

    primary_index_before = primary_state()
    with tempfile.TemporaryDirectory(prefix="pietto-gate2-topology-") as temporary:
        temporary_root = Path(temporary)
        source = temporary_root / "source"
        candidate, tree = _copy_active_tree(
            root=root, source=source, base=BASE, statuses=statuses
        )
        pr_merge, squash, projections = _prepare_positive_repositories(
            source=source,
            root=temporary_root,
            candidate=candidate,
            tree=tree,
        )
        expected = {
            item.name: item
            for item in projection_plan(
                candidate=candidate, pr_merge=pr_merge, squash=squash, tree=tree
            )
        }
        positive_results: list[dict[str, object]] = []
        legacy_maps: dict[str, dict[str, object]] = {}
        lean_maps: dict[str, dict[str, object]] = {}
        lean_only_nodes: set[str] | None = None
        for name in ("candidate", "pr_merge", "main_push", "reconciled_main"):
            repo, env = projections[name]
            identity = validate_projection(
                profile=name,
                repo=repo,
                env=env,
                candidate=candidate,
                reviewed_tree=tree,
                statuses=statuses,
            )
            reference = expected[name]
            if (
                identity.head != reference.head
                or identity.parents != reference.parents
                or identity.tree != reference.tree
                or identity.shallow != reference.shallow
            ):
                raise TopologyCheckError(f"identity drift for {name}: {identity}")
            legacy = _pytest(
                python=python,
                repo=repo,
                nodes=reader_paths,
                env=env,
                expect_success=True,
                label=f"positive-{name}-legacy",
                expected_items=reader_items,
            )
            lean = _pytest(
                python=python,
                repo=repo,
                nodes=TOPOLOGY_SENSITIVE_NODE_IDS,
                env=env,
                expect_success=True,
                label=f"positive-{name}-lean",
                expected_items=TOPOLOGY_SELECTED_ITEMS,
            )
            legacy_map = {
                item["node_id"]: item
                for item in legacy["outcomes"]["items"]  # type: ignore[index]
            }
            lean_map = {
                item["node_id"]: item
                for item in lean["outcomes"]["items"]  # type: ignore[index]
            }
            missing = sorted(set(lean_map) - set(legacy_map))
            mismatches = sorted(
                node_id
                for node_id in set(lean_map) & set(legacy_map)
                if lean_map[node_id] != legacy_map[node_id]
            )
            if mismatches:
                raise TopologyCheckError(
                    f"legacy/lean mismatch for {name}: mismatch={mismatches}"
                )
            if lean_only_nodes is None:
                lean_only_nodes = set(missing)
            elif lean_only_nodes != set(missing):
                raise TopologyCheckError("lean-only topology registry drift")
            legacy_maps[name] = legacy_map
            lean_maps[name] = lean_map
            event_payload = None
            if identity.event_path:
                event_payload = json.loads(Path(identity.event_path).read_bytes())
            positive_results.append(
                {
                    "result": "PASS",
                    "identity": asdict(identity),
                    "environment": {
                        key: env[key]
                        for key in sorted(env)
                        if key.startswith("GITHUB_")
                        or key
                        in {"UV_OFFLINE", "UV_NO_SYNC", "PYTHONDONTWRITEBYTECODE"}
                    },
                    "event_payload": event_payload,
                    "legacy_pytest": legacy,
                    "lean_pytest": lean,
                    "compared_node_count": len(set(lean_map) & set(legacy_map)),
                    "lean_only_node_ids": missing,
                    "legacy_lean_outcome_equality": True,
                }
            )

        if lean_only_nodes is None:
            raise TopologyCheckError("positive topology result set is empty")
        registry_ids = set(next(iter(lean_maps.values())))
        excluded = set(next(iter(legacy_maps.values()))) - registry_ids
        excluded_mismatches = sorted(
            node_id
            for node_id in excluded
            if len(
                {
                    json.dumps(legacy_maps[name][node_id], sort_keys=True)
                    for name in legacy_maps
                }
            )
            != 1
        )
        if excluded_mismatches:
            raise TopologyCheckError(
                "content-only outcomes changed across projections: "
                + ", ".join(excluded_mismatches)
            )

        negative_results = _run_negative_matrix(
            primary_root=root,
            source=source,
            temporary_root=temporary_root,
            python=python,
            candidate=candidate,
            pr_merge=pr_merge,
            squash=squash,
            tree=tree,
            statuses=statuses,
        )

        primary_index_after = primary_state()
        if primary_index_before != primary_index_after:
            raise TopologyCheckError("primary index changed")
        document: dict[str, object] = {
            "schema": SCHEMA,
            "tool_version": "1",
            "base": BASE,
            "candidate": candidate,
            "reviewed_tree": tree,
            "pr_merge": pr_merge,
            "squash": squash,
            "manifest": {
                "counts": {
                    status: sum(value == status for value in statuses.values())
                    for status in ("A", "M", "D")
                },
                "paths": [
                    {"path": path, "status": statuses[path]}
                    for path in sorted(statuses)
                ],
            },
            "registry": {
                "schema": "pietto.gate2.topology-registry.v1",
                "sha256": TOPOLOGY_REGISTRY_SHA256,
                "payload_bytes": len(TOPOLOGY_REGISTRY_PAYLOAD),
                "files": TOPOLOGY_REGISTRY_FILES,
                "node_ids": list(TOPOLOGY_SENSITIVE_NODE_IDS),
                "node_id_count": len(TOPOLOGY_SENSITIVE_NODE_IDS),
                "selected_items_per_projection": TOPOLOGY_SELECTED_ITEMS,
            },
            "legacy_reader_closure": {
                "paths": list(reader_paths),
                "path_count": len(reader_paths),
                "selected_items_per_projection": reader_items,
                "sha256": hashlib.sha256(
                    "".join(f"{path}\n" for path in reader_paths).encode()
                ).hexdigest(),
            },
            "positive_results": positive_results,
            "negative_results": negative_results,
            "equivalence": {
                "outcome_equality": True,
                "excluded_content_invariant": True,
                "excluded_content_mismatches": [],
                "lean_nodes_missing_from_legacy": sorted(lean_only_nodes),
                "zero_skipped_xfailed_xpassed_deselected": True,
            },
            "performance": {
                "legacy_pytest_processes": 4,
                "legacy_repeated_items": 4 * reader_items,
                "lean_pytest_processes": 4,
                "lean_repeated_topology_items": 4 * TOPOLOGY_SELECTED_ITEMS,
                "negative_pytest_processes": 21,
                "repeated_item_reduction": 4 * (reader_items - TOPOLOGY_SELECTED_ITEMS),
                "legacy_wall_seconds": round(
                    sum(
                        result_metric(result, "legacy_pytest", "wall_seconds")
                        for result in positive_results
                    ),
                    6,
                ),
                "lean_wall_seconds": round(
                    sum(
                        result_metric(result, "lean_pytest", "wall_seconds")
                        for result in positive_results
                    ),
                    6,
                ),
                "legacy_cpu_seconds": round(
                    sum(
                        result_metric(result, "legacy_pytest", "cpu_seconds")
                        for result in positive_results
                    ),
                    6,
                ),
                "lean_cpu_seconds": round(
                    sum(
                        result_metric(result, "lean_pytest", "cpu_seconds")
                        for result in positive_results
                    ),
                    6,
                ),
            },
            "primary_state_before": primary_index_before,
            "primary_state_after": primary_index_after,
        }
        document["payload_sha256"] = hashlib.sha256(
            _canonical_json(document)
        ).hexdigest()
        output.write_bytes(_canonical_json(document))
        return document


def _manifest_statuses(path: Path) -> dict[str, str]:
    payload = path.read_bytes()
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise TopologyCheckError("manifest must be canonical UTF-8/LF with final LF")
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise TopologyCheckError("manifest is not UTF-8") from error
    result: dict[str, str] = {}
    previous = ""
    for line in lines:
        path_text, separator, status = line.partition("\t")
        if (
            not separator
            or "\t" in status
            or status not in {"A", "M", "D"}
            or not path_text
            or path_text.startswith("/")
            or ".." in Path(path_text).parts
            or path_text in result
            or (previous and path_text <= previous)
        ):
            raise TopologyCheckError(f"malformed manifest row: {line!r}")
        result[path_text] = status
        previous = path_text
    return result


def _reader_closure(path: Path) -> tuple[tuple[str, ...], int]:
    payload = path.read_bytes()
    document = json.loads(payload)
    if not isinstance(document, dict) or document.get("schema") != (
        "pietto.gate2.reader-closure.v1"
    ):
        raise TopologyCheckError("reader closure schema mismatch")
    if payload != _canonical_json(document):
        raise TopologyCheckError("reader closure is not canonical JSON")
    recorded_hash = document.pop("payload_sha256", None)
    actual_hash = hashlib.sha256(_canonical_json(document)).hexdigest()
    if recorded_hash != actual_hash:
        raise TopologyCheckError("reader closure internal payload hash mismatch")
    values = document.get("reader_paths")
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise TopologyCheckError("reader closure paths are malformed")
    paths = tuple(values)
    if paths != tuple(sorted(set(paths))):
        raise TopologyCheckError("reader closure paths are not sorted unique")
    return paths, 6786


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reader-closure", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    sys.path.insert(0, str(root / "tests"))
    from _active_gate2_manifest_data import (  # noqa: PLC0415
        ACTIVE_GATE2_ADDED_PATHS,
        ACTIVE_GATE2_DELETED_PATHS,
        ACTIVE_GATE2_DIRECT_READER_SHA256,
        ACTIVE_GATE2_MODIFIED_PATHS,
        ACTIVE_GATE2_READER_CLOSURE_SHA256,
        ACTIVE_GATE2_READER_ITEMS,
        ACTIVE_GATE2_TRANSITIVE_READER_SHA256,
    )

    statuses = _manifest_statuses(arguments.manifest)
    expected_statuses = {
        **{path: "A" for path in ACTIVE_GATE2_ADDED_PATHS},
        **{path: "M" for path in ACTIVE_GATE2_MODIFIED_PATHS},
        **{path: "D" for path in ACTIVE_GATE2_DELETED_PATHS},
    }
    if statuses != expected_statuses:
        raise TopologyCheckError("manifest differs from exact active A12_M51_D0")
    reader_paths, reader_items = _reader_closure(arguments.reader_closure)
    reader_sha = hashlib.sha256(
        "".join(f"{path}\n" for path in reader_paths).encode()
    ).hexdigest()
    if reader_sha != ACTIVE_GATE2_READER_CLOSURE_SHA256:
        raise TopologyCheckError("reader closure identity drift")
    if reader_items != ACTIVE_GATE2_READER_ITEMS:
        raise TopologyCheckError("reader item count drift")
    if not all(
        re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (
            ACTIVE_GATE2_DIRECT_READER_SHA256,
            ACTIVE_GATE2_TRANSITIVE_READER_SHA256,
        )
    ):
        raise TopologyCheckError("reader partition identity malformed")
    python = Path(os.path.abspath(arguments.python))
    if not python.is_file() or not os.access(python, os.X_OK):
        raise TopologyCheckError("pytest Python entrypoint is not executable")
    run_topology_checks(
        root=root,
        statuses=statuses,
        reader_paths=reader_paths,
        reader_items=reader_items,
        output=arguments.output,
        python=python,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
