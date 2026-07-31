"""Stable exact matcher for Pietto active Gate 2 repository manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from _active_gate2_manifest_data import (
    ACTIVE_GATE2_ADDED_PATHS,
    ACTIVE_GATE2_BASE,
    ACTIVE_GATE2_BRANCH,
    ACTIVE_GATE2_CANDIDATE_BRANCH,
    ACTIVE_GATE2_CANDIDATE_SUBJECT,
    ACTIVE_GATE2_DELETED_PATHS,
    ACTIVE_GATE2_MARKER,
    ACTIVE_GATE2_MODIFIED_PATHS,
    ACTIVE_GATE2_UPSTREAM,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True, kw_only=True)
class ActiveGate2RepositoryState:
    """Exact read-only Git facts accepted by the active manifest."""

    marker: str
    branch_oid: str
    branch_head: str
    branch_upstream: str
    ahead: int
    behind: int
    head_parents: tuple[str, ...]
    head_subject: str
    main_oid: str
    origin_main_oid: str
    committed_added_paths: frozenset[str]
    committed_modified_paths: frozenset[str]
    committed_deleted_paths: frozenset[str]
    added_paths: frozenset[str]
    modified_paths: frozenset[str]
    deleted_paths: frozenset[str]
    staged_paths: frozenset[str]
    other_paths: frozenset[str]
    worktree_count: int
    shallow: bool
    active_git_operation: bool


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _git_optional_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return result.stdout.rstrip()
    return ""


def _name_status_between_base_and_head() -> tuple[
    frozenset[str], frozenset[str], frozenset[str]
]:
    added: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    output = _git_output(
        ["diff", "--name-status", "--no-renames", ACTIVE_GATE2_BASE, "HEAD"]
    )
    for line in output.splitlines():
        status, separator, path = line.partition("\t")
        if not separator or status not in {"A", "M", "D"} or not path:
            raise ValueError(f"unsupported committed name-status row: {line!r}")
        {"A": added, "M": modified, "D": deleted}[status].add(path)
    return frozenset(added), frozenset(modified), frozenset(deleted)


def _read_active_gate2_repository_state() -> ActiveGate2RepositoryState:
    status = _git_output(
        ["status", "--porcelain=v2", "--branch", "--untracked-files=all"]
    )
    branch_oid = ""
    branch_head = ""
    branch_upstream = ""
    ahead = -1
    behind = -1
    added_paths: set[str] = set()
    modified_paths: set[str] = set()
    deleted_paths: set[str] = set()
    staged_paths: set[str] = set()
    other_paths: set[str] = set()

    for line in status.splitlines():
        if line.startswith("# branch.oid "):
            branch_oid = line.removeprefix("# branch.oid ")
        elif line.startswith("# branch.head "):
            branch_head = line.removeprefix("# branch.head ")
        elif line.startswith("# branch.upstream "):
            branch_upstream = line.removeprefix("# branch.upstream ")
        elif line.startswith("# branch.ab "):
            ahead_text, behind_text = line.removeprefix("# branch.ab ").split()
            ahead = int(ahead_text.removeprefix("+"))
            behind = int(behind_text.removeprefix("-"))
        elif line.startswith("? "):
            added_paths.add(line.removeprefix("? "))
        elif line.startswith("1 "):
            parts = line.split(" ", 8)
            if len(parts) != 9:
                other_paths.add(line)
                continue
            index_status, worktree_status = parts[1]
            path = parts[8]
            if index_status != ".":
                staged_paths.add(path)
            if worktree_status == "M":
                modified_paths.add(path)
            elif worktree_status == "D":
                deleted_paths.add(path)
            elif worktree_status != ".":
                other_paths.add(path)
        elif not line.startswith("# "):
            other_paths.add(line)

    git_dir = Path(_git_output(["rev-parse", "--git-dir"]))
    if not git_dir.is_absolute():
        git_dir = REPO_ROOT / git_dir
    active_git_operation = any(
        (git_dir / name).exists()
        for name in (
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "REBASE_HEAD",
            "rebase-merge",
            "rebase-apply",
        )
    )
    worktree_count = _git_output(["worktree", "list", "--porcelain"]).count("worktree ")
    shallow = _git_output(["rev-parse", "--is-shallow-repository"]) == "true"
    header = _git_output(["show", "-s", "--format=%P%x00%s", "HEAD"])
    parent_text, separator, head_subject = header.partition("\0")
    if separator != "\0":
        raise ValueError("malformed HEAD identity")
    committed_added, committed_modified, committed_deleted = (
        _name_status_between_base_and_head()
    )
    return ActiveGate2RepositoryState(
        marker=ACTIVE_GATE2_MARKER,
        branch_oid=branch_oid,
        branch_head=branch_head,
        branch_upstream=branch_upstream,
        ahead=ahead,
        behind=behind,
        head_parents=tuple(parent_text.split()),
        head_subject=head_subject,
        main_oid=_git_optional_output(["rev-parse", "--verify", "refs/heads/main"]),
        origin_main_oid=_git_optional_output(
            ["rev-parse", "--verify", "refs/remotes/origin/main"]
        ),
        committed_added_paths=committed_added,
        committed_modified_paths=committed_modified,
        committed_deleted_paths=committed_deleted,
        added_paths=frozenset(added_paths),
        modified_paths=frozenset(modified_paths),
        deleted_paths=frozenset(deleted_paths),
        staged_paths=frozenset(staged_paths),
        other_paths=frozenset(other_paths),
        worktree_count=worktree_count,
        shallow=shallow,
        active_git_operation=active_git_operation,
    )


def _matches_active_gate2_manifest(state: ActiveGate2RepositoryState) -> bool:
    """Return whether supplied facts exactly equal the one active Gate 2."""

    return (
        type(state) is ActiveGate2RepositoryState
        and state.marker == ACTIVE_GATE2_MARKER
        and state.branch_oid == ACTIVE_GATE2_BASE
        and state.branch_head == ACTIVE_GATE2_BRANCH
        and state.branch_upstream == ACTIVE_GATE2_UPSTREAM
        and state.ahead == 0
        and state.behind == 0
        and state.main_oid == ACTIVE_GATE2_BASE
        and state.origin_main_oid == ACTIVE_GATE2_BASE
        and state.committed_added_paths == frozenset()
        and state.committed_modified_paths == frozenset()
        and state.committed_deleted_paths == frozenset()
        and state.added_paths == ACTIVE_GATE2_ADDED_PATHS
        and state.modified_paths == ACTIVE_GATE2_MODIFIED_PATHS
        and state.deleted_paths == ACTIVE_GATE2_DELETED_PATHS
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )


def _matches_active_gate2_candidate(state: ActiveGate2RepositoryState) -> bool:
    """Recognize only the clean, exact one-commit candidate projection."""

    return (
        type(state) is ActiveGate2RepositoryState
        and state.marker == ACTIVE_GATE2_MARKER
        and re.fullmatch(r"[0-9a-f]{40}", state.branch_oid) is not None
        and state.branch_oid != ACTIVE_GATE2_BASE
        and state.branch_head == ACTIVE_GATE2_CANDIDATE_BRANCH
        and state.branch_upstream == ""
        and state.ahead == -1
        and state.behind == -1
        and state.head_parents == (ACTIVE_GATE2_BASE,)
        and state.head_subject == ACTIVE_GATE2_CANDIDATE_SUBJECT
        and state.main_oid == ACTIVE_GATE2_BASE
        and state.origin_main_oid == ACTIVE_GATE2_BASE
        and state.committed_added_paths == ACTIVE_GATE2_ADDED_PATHS
        and state.committed_modified_paths == ACTIVE_GATE2_MODIFIED_PATHS
        and state.committed_deleted_paths == ACTIVE_GATE2_DELETED_PATHS
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )


def _matches_active_gate2_reconciled_main(
    state: ActiveGate2RepositoryState,
) -> bool:
    """Recognize only the exact full-history reconciled-main projection."""

    return (
        type(state) is ActiveGate2RepositoryState
        and state.marker == ACTIVE_GATE2_MARKER
        and re.fullmatch(r"[0-9a-f]{40}", state.branch_oid) is not None
        and state.branch_oid != ACTIVE_GATE2_BASE
        and state.branch_head == ACTIVE_GATE2_BRANCH
        and state.branch_upstream == ACTIVE_GATE2_UPSTREAM
        and state.ahead == 0
        and state.behind == 0
        and state.head_parents == (ACTIVE_GATE2_BASE,)
        and re.fullmatch(
            rf"{re.escape(ACTIVE_GATE2_CANDIDATE_SUBJECT)} \(#[0-9]+\)",
            state.head_subject,
        )
        is not None
        and state.main_oid == state.branch_oid
        and state.origin_main_oid == state.branch_oid
        and state.committed_added_paths == ACTIVE_GATE2_ADDED_PATHS
        and state.committed_modified_paths == ACTIVE_GATE2_MODIFIED_PATHS
        and state.committed_deleted_paths == ACTIVE_GATE2_DELETED_PATHS
        and state.added_paths == frozenset()
        and state.modified_paths == frozenset()
        and state.deleted_paths == frozenset()
        and state.staged_paths == frozenset()
        and state.other_paths == frozenset()
        and state.worktree_count == 1
        and not state.shallow
        and not state.active_git_operation
    )


def active_gate2_manifest_is_active() -> bool:
    """Recognize the exact dirty, candidate, or reconciled Gate 2 state."""

    try:
        state = _read_active_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return (
        _matches_active_gate2_manifest(state)
        or _matches_active_gate2_candidate(state)
        or _matches_active_gate2_reconciled_main(state)
    )


def active_gate2_candidate_is_active() -> bool:
    """Read Git facts and recognize only the clean candidate projection."""

    try:
        state = _read_active_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_active_gate2_candidate(state)


def active_gate2_local_lifecycle_is_active() -> bool:
    """Stable explicit alias for the exact local lifecycle predicate."""

    return active_gate2_manifest_is_active()
