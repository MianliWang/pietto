"""Standardized, temporary publication-topology fixtures and fail-closed checks.

Topology-sensitive readers assert repository state — refs, parents, merge base,
shallow boundary, continuous-integration event metadata, head and base identity,
and the expected tree. Those assertions must hold under every projection the
publication lifecycle actually produces, not only the local one. Historically
the missing projections, not the product change, caused the publication repairs.

Every fixture is built inside a caller-supplied temporary directory. Nothing
here touches the primary repository, reads the network, or writes a tracked
file. Verification is fail closed: an observation is accepted only when every
declared field matches exactly.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

TOPOLOGY_DIRTY_GATE2 = "dirty_gate2_candidate"
TOPOLOGY_CLEAN_TOPIC = "clean_topic_candidate"
TOPOLOGY_REPAIR_CHILD = "non_amend_repair_child"
TOPOLOGY_PULL_REQUEST_MERGE = "pull_request_merge"
TOPOLOGY_SHALLOW_PULL_REQUEST = "shallow_pull_request_checkout"
TOPOLOGY_SQUASH_MAIN = "squash_main"
TOPOLOGY_MAIN_PUSH = "natural_main_push"

TOPOLOGY_KINDS: tuple[str, ...] = (
    TOPOLOGY_CLEAN_TOPIC,
    TOPOLOGY_DIRTY_GATE2,
    TOPOLOGY_MAIN_PUSH,
    TOPOLOGY_REPAIR_CHILD,
    TOPOLOGY_PULL_REQUEST_MERGE,
    TOPOLOGY_SHALLOW_PULL_REQUEST,
    TOPOLOGY_SQUASH_MAIN,
)

EVENT_PULL_REQUEST = "pull_request"
EVENT_PUSH = "push"
EVENT_LOCAL = "local"

PULL_REQUEST_MERGE_REF = "refs/pull/1/merge"
CI_EVENT_VARIABLES: tuple[str, ...] = (
    "GITHUB_BASE_REF",
    "GITHUB_EVENT_NAME",
    "GITHUB_EVENT_PATH",
    "GITHUB_HEAD_REF",
    "GITHUB_REF",
    "GITHUB_SHA",
)

TOPIC_BRANCH = "phase54/post-slice12-workflow-hardening"
MAIN_BRANCH = "main"
BASE_SUBJECT = "Base commit"
TOPIC_SUBJECT = "Add Pietto workflow convergence tooling"
REPAIR_SUBJECT = "Fix Pietto workflow convergence tooling"

_SYNTHETIC_CANDIDATE: Mapping[str, str] = {
    "AUTHORITY.md": "# authority\n\nbase\ncandidate\n",
    "added.md": "# added\n",
}

_FIXED_IDENTITY: Mapping[str, str] = {
    "GIT_AUTHOR_NAME": "Pietto Topology Fixture",
    "GIT_AUTHOR_EMAIL": "topology@pietto.invalid",
    "GIT_COMMITTER_NAME": "Pietto Topology Fixture",
    "GIT_COMMITTER_EMAIL": "topology@pietto.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}


class TopologyError(Exception):
    """Raised when a fixture cannot be built or an argument is unusable."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TopologyExpectation:
    """The exact repository state a topology-sensitive reader may accept."""

    kind: str
    branch: str
    head: str
    head_tree: str
    head_parents: tuple[str, ...]
    merge_base: str
    shallow: bool
    event_name: str
    event_head_ref: str
    event_base_ref: str
    added_paths: tuple[str, ...] = ()
    modified_paths: tuple[str, ...] = ()
    deleted_paths: tuple[str, ...] = ()
    staged_paths: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in TOPOLOGY_KINDS:
            raise TopologyError(f"unknown topology kind: {self.kind}")


@dataclass(frozen=True, slots=True, kw_only=True)
class TopologyObservation:
    """The exact repository state observed from a built fixture."""

    branch: str
    head: str
    head_tree: str
    head_parents: tuple[str, ...]
    merge_base: str
    shallow: bool
    event_name: str
    event_head_ref: str
    event_base_ref: str
    added_paths: tuple[str, ...]
    modified_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]
    staged_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TopologyFixture:
    """One built projection plus the expectation it was constructed to satisfy."""

    kind: str
    root: Path
    expectation: TopologyExpectation
    observation: TopologyObservation
    refs: Mapping[str, str] = field(default_factory=dict)
    event_path: Path | None = None


def _git(root: Path, *args: str) -> str:
    environment = dict(_FIXED_IDENTITY)
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        env={**_inherited_environment(), **environment},
    )
    if result.returncode != 0:
        raise TopologyError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _inherited_environment() -> dict[str, str]:
    import os

    return dict(os.environ)


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _source_output(source: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=source,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        raise TopologyError(f"cannot read {source}: {result.stderr.strip()}")
    return result.stdout


def _write_pull_request_event(root: Path, *, base: str, head: str) -> Path:
    """Write one pull-request event payload beside, never inside, a projection."""

    destination = root.parent / f"{root.name}-event.json"
    destination.write_text(
        json.dumps(
            {
                "pull_request": {
                    "base": {"sha": base, "ref": MAIN_BRANCH},
                    "head": {"sha": head, "ref": TOPIC_BRANCH},
                }
            },
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return destination


def source_base_revision(source: Path) -> str:
    """Return the revision a source-backed projection must treat as its base.

    The publication baseline is the source's own main authority, not whatever
    its head happens to be. Anchoring a merge, squash, or push projection to a
    topic child would model a release topology that never exists.
    """

    for candidate in ("refs/heads/main", "refs/remotes/origin/main", "HEAD~1"):
        result = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "--verify", "--quiet", candidate],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return candidate
    return "HEAD"


def source_commit_parents(source: Path, revision: str) -> tuple[str, ...]:
    """Return one source commit's declared parents, oldest first."""

    listing = _source_lines(source, "rev-list", "--parents", "-n", "1", revision)
    if not listing:
        raise TopologyError(f"cannot read parents of {revision} in {source}")
    return tuple(listing[0].split()[1:])


def source_is_dirty(source: Path) -> bool:
    """Return whether one source working tree differs from its own head."""

    added, modified, deleted = source_dirty_paths(source)
    return bool(added or modified or deleted)


def _reject_gitlink_source(source: Path) -> None:
    """Refuse a source that carries a gitlink entry.

    A submodule is recorded as mode ``160000`` and appears as a directory in the
    working tree, so copying entries would silently drop it and still declare
    the projection identical to the candidate. Refusing is the honest outcome.
    """

    for line in _source_lines(source, "ls-files", "--stage"):
        if line.startswith("160000"):
            raise TopologyError(f"source repository contains a gitlink: {source}")


def _reject_staged_source(source: Path) -> None:
    """Refuse a source whose index is not empty.

    The gate contract keeps the index empty, and a staged change is invisible to
    both the unstaged diff and the untracked listing. Refusing is honest;
    reporting such a source as clean would project the wrong candidate.
    """

    if _source_lines(source, "diff", "--cached", "--name-only"):
        raise TopologyError(f"source repository has a non-empty index: {source}")


def _source_working_paths(source: Path) -> tuple[str, ...]:
    """Return the paths that actually exist in one source working tree.

    A tracked path the source deleted is still listed by the index, so the
    listing is filtered by real existence. Otherwise the deletion would never
    reach the projection and the projected tree would not be the candidate.
    """

    _reject_staged_source(source)
    _reject_gitlink_source(source)
    listed = _source_lines(
        source, "ls-files", "--cached", "--others", "--exclude-standard"
    )
    entries = tuple(
        relative
        for relative in listed
        if (source / relative).is_symlink() or (source / relative).is_file()
    )
    # A tracked path may be deleted, or replaced by a directory that now holds
    # new entries. Both are trees Git can represent. Only an entry that exists
    # as something else entirely - a device or socket - is refused.
    unusable = tuple(
        relative
        for relative in listed
        if relative not in set(entries)
        and (source / relative).exists()
        and not (source / relative).is_dir()
    )
    if unusable:
        raise TopologyError(f"source entries are not regular files: {unusable[:5]}")
    if not entries:
        raise TopologyError(f"source repository has no content: {source}")
    return entries


def source_dirty_paths(
    source: Path,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Return one source repository's (added, modified, deleted) uncommitted paths."""

    _reject_staged_source(source)
    deleted = tuple(sorted(_source_lines(source, "ls-files", "--deleted")))
    modified = tuple(
        sorted(set(_source_lines(source, "diff", "--name-only")) - set(deleted))
    )
    added = tuple(
        sorted(_source_lines(source, "ls-files", "--others", "--exclude-standard"))
    )
    return added, modified, deleted


def _source_lines(source: Path, *args: str) -> tuple[str, ...]:
    return tuple(line for line in _source_output(source, *args).splitlines() if line)


def _blob_oid(data: bytes) -> str:
    """Return the Git blob object name of one payload."""

    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _entry_of(path: Path) -> tuple[str, str]:
    """Return one path's exact Git entry: its mode and its blob object name."""

    if path.is_symlink():
        return "120000", _blob_oid(os.readlink(path).encode("utf-8"))
    data = path.read_bytes()
    executable = bool(path.stat().st_mode & 0o111)
    return ("100755" if executable else "100644"), _blob_oid(data)


def candidate_entries(source: Path) -> dict[str, tuple[str, str]]:
    """Return the exact Git entry of every path in one source working tree.

    Tree identity includes entry type and mode, so a projection that copied only
    dereferenced bytes would carry a different tree than the candidate it claims
    to be. These entries are what the projection is verified against.
    """

    return {
        relative: _entry_of(source / relative)
        for relative in _source_working_paths(source)
    }


def _directory_entries(root: Path) -> dict[str, tuple[str, str]]:
    observed: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if not path.is_symlink() and not path.is_file():
            continue
        observed[str(relative)] = _entry_of(path)
    return observed


def _tree_entries(root: Path) -> dict[str, tuple[str, str]]:
    observed: dict[str, tuple[str, str]] = {}
    for line in _git(root, "ls-tree", "-r", "HEAD").splitlines():
        metadata, separator, relative = line.partition("\t")
        if not separator:
            raise TopologyError(f"unparseable tree entry: {line}")
        fields = metadata.split()
        if len(fields) != 3:
            raise TopologyError(f"unparseable tree entry: {line}")
        observed[relative] = (fields[0], fields[2])
    return observed


def _verify_committed_candidate(
    root: Path, expected: dict[str, tuple[str, str]]
) -> None:
    """Fail closed unless the committed head carries exactly these entries."""

    observed = _tree_entries(root)
    if observed != expected:
        difference = sorted(
            relative
            for relative in set(expected) | set(observed)
            if expected.get(relative) != observed.get(relative)
        )
        raise TopologyError(f"projected commit differs: {difference[:5]}")


def _verify_candidate(root: Path, source: Path, *, committed: bool) -> None:
    """Fail closed unless the projection carries exactly the candidate entries."""

    expected = candidate_entries(source)
    observed = _tree_entries(root) if committed else _directory_entries(root)
    if observed == expected:
        return
    difference = sorted(
        relative
        for relative in set(expected) | set(observed)
        if expected.get(relative) != observed.get(relative)
    )
    raise TopologyError(f"projected candidate differs from {source}: {difference[:5]}")


def committed_entries(
    source: Path, revision: str = "HEAD"
) -> dict[str, tuple[str, str]]:
    """Return the exact Git entry of every path in one committed source tree."""

    entries: dict[str, tuple[str, str]] = {}
    for line in _source_lines(source, "ls-tree", "-r", revision):
        metadata, separator, relative = line.partition("\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise TopologyError(f"unparseable source tree entry: {line}")
        entries[relative] = (fields[0], fields[2])
    if not entries:
        raise TopologyError(f"source revision has no content: {source}@{revision}")
    return entries


def _seed_committed_tree(root: Path, source: Path, revision: str = "HEAD") -> None:
    """Materialize one source repository's committed tree, byte for byte."""

    archive = subprocess.run(
        ["git", "archive", "--format=tar", revision],
        cwd=source,
        capture_output=True,
    )
    if archive.returncode != 0:
        raise TopologyError(
            f"cannot archive {source}: {archive.stderr.decode('utf-8', 'replace').strip()}"
        )
    if not archive.stdout:
        raise TopologyError(f"source repository has no content: {source}")
    root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as bundle:
        bundle.extractall(root, filter="data")
    # ``git archive`` stamps every entry with its commit time. Two source
    # commits made in the same second would then produce identical size and
    # timestamp, and Git's stat cache would report the extraction as unchanged.
    for extracted in root.rglob("*"):
        if ".git" in extracted.relative_to(root).parts:
            continue
        if extracted.is_symlink() or not extracted.is_file():
            continue
        os.utime(extracted)


def _seed_working_tree(root: Path, source: Path) -> None:
    """Make root's content exactly one source repository's working tree."""

    entries = _source_working_paths(source)
    wanted = set(entries)
    for relative in entries:
        origin = source / relative
        destination = root / relative
        # A path may change between file, symlink, and directory. Clear whatever
        # occupies the destination or blocks its parents before writing.
        for ancestor in reversed(destination.parents):
            if ancestor.is_symlink() or (ancestor.exists() and not ancestor.is_dir()):
                ancestor.unlink()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_symlink() or (
            destination.exists() and not destination.is_dir()
        ):
            destination.unlink()
        elif destination.is_dir():
            shutil.rmtree(destination)
        if origin.is_symlink():
            os.symlink(os.readlink(origin), destination)
            continue
        destination.write_bytes(origin.read_bytes())
        destination.chmod(0o755 if origin.stat().st_mode & 0o111 else 0o644)
    for existing in sorted(root.rglob("*")):
        relative = existing.relative_to(root)
        if ".git" in relative.parts:
            continue
        # A dangling symlink is still a Git entry the candidate may remove, and
        # ``is_file`` follows the link, so entry type is what decides here.
        if not existing.is_symlink() and not existing.is_file():
            continue
        if str(relative) not in wanted:
            existing.unlink()


def _clear_worktree(root: Path) -> None:
    for path in sorted(root.rglob("*"), reverse=True):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink() or path.is_file():
            path.unlink()


def _apply_committed_candidate(root: Path, source: Path, revision: str) -> None:
    """Replace the working tree with one committed source revision."""

    _clear_worktree(root)
    _seed_committed_tree(root, source, revision)


def _apply_candidate(
    root: Path, source: Path | None, synthetic: Mapping[str, str]
) -> None:
    """Write one candidate state: synthetic edits, or the real working tree.

    A source-backed projection must carry the exact publication candidate tree.
    Adding synthetic files on top of real content would move every repository
    inventory a real reader asserts, so the two modes never mix.
    """

    if source is None:
        for relative, text in synthetic.items():
            _write(root, relative, text)
        return
    _seed_working_tree(root, source)


def _init_base(root: Path, source: Path | None = None, revision: str = "HEAD") -> str:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--quiet", "--initial-branch", MAIN_BRANCH)
    if source is not None:
        # Import the real baseline commit instead of re-committing its files:
        # readers assert the exact base object name, and a synthetic identity
        # would make every merge and push projection unrecognizable.
        _reject_staged_source(source)
        _reject_gitlink_source(source)
        _git(root, "remote", "add", "origin", str(source))
        _git(
            root,
            "fetch",
            "--quiet",
            "--no-tags",
            "origin",
            "+refs/heads/*:refs/remotes/origin/*",
            "+HEAD:refs/remotes/origin/source-head",
        )
        base = _source_output(source, "rev-parse", revision).strip()
        if not base:
            raise TopologyError(f"cannot resolve {revision} in {source}")
        _git(root, "checkout", "--quiet", "-B", MAIN_BRANCH, base)
        _verify_committed_candidate(root, committed_entries(source, revision))
        return base
    _write(root, "AUTHORITY.md", "# authority\n\nbase\n")
    _write(root, "reader.txt", "count=1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", BASE_SUBJECT)
    return _git(root, "rev-parse", "HEAD")


def projection_environment(
    expectation: TopologyExpectation,
    inherited: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Return the exact continuous-integration event environment of a projection.

    Readers branch on the event variables, so a projection is only reproduced
    when they are set from its own expectation. Every variable is cleared first:
    a sweep that runs inside one integration job must not leak that job's event
    into the other six projections.
    """

    environment = dict(
        _inherited_environment() if inherited is None else dict(inherited)
    )
    for name in CI_EVENT_VARIABLES:
        environment.pop(name, None)
    if expectation.event_name == EVENT_LOCAL:
        return environment
    environment["GITHUB_EVENT_NAME"] = expectation.event_name
    environment["GITHUB_SHA"] = expectation.head
    if expectation.event_name == EVENT_PUSH:
        # A push event carries no pull-request head or base reference. Exporting
        # either one would let a reader observe a state main integration never
        # produces, which is the opposite of what a projection is for.
        environment["GITHUB_REF"] = f"refs/heads/{expectation.event_head_ref}"
        return environment
    environment["GITHUB_REF"] = PULL_REQUEST_MERGE_REF
    if expectation.event_head_ref:
        environment["GITHUB_HEAD_REF"] = expectation.event_head_ref
    if expectation.event_base_ref:
        environment["GITHUB_BASE_REF"] = expectation.event_base_ref
    return environment


def run_in_projection(
    fixture: TopologyFixture,
    command: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    """Run one read-only command inside a built projection and return its result.

    This is the entry point that lets the real topology-sensitive reader set
    execute under every projection rather than only self-verifying the fixture.
    The command runs under the projection's own event environment.
    """

    if not command:
        raise TopologyError("a projection command must not be empty")
    environment = projection_environment(fixture.expectation)
    if fixture.event_path is not None:
        environment["GITHUB_EVENT_PATH"] = str(fixture.event_path)
    elif fixture.expectation.event_name == EVENT_PULL_REQUEST:
        raise TopologyError("a pull-request projection requires an event payload")
    return subprocess.run(
        list(command),
        cwd=fixture.root,
        text=True,
        capture_output=True,
        env=environment,
    )


def _commit(root: Path, subject: str, *, allow_empty: bool = False) -> str:
    _git(root, "add", "-A")
    arguments = ["commit", "--quiet", "-m", subject]
    if allow_empty:
        # A source-backed candidate may carry the same tree as its base. The
        # projection still needs the commit, because its shape is the subject.
        arguments.insert(1, "--allow-empty")
    _git(root, *arguments)
    return _git(root, "rev-parse", "HEAD")


def _set_upstream(root: Path, branch: str, oid: str) -> None:
    _git(root, "update-ref", f"refs/remotes/origin/{branch}", oid)
    _git(root, "config", f"branch.{branch}.remote", "origin")
    _git(root, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")


def observe(
    root: Path,
    *,
    event_name: str,
    event_head_ref: str,
    event_base_ref: str,
    base_ref: str,
) -> TopologyObservation:
    """Observe one repository's publication topology without changing it."""

    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    head = _git(root, "rev-parse", "HEAD")
    head_tree = _git(root, "rev-parse", "HEAD^{tree}")
    parents = tuple(_git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:])
    shallow = _git(root, "rev-parse", "--is-shallow-repository") == "true"
    merge_base = ""
    if base_ref and not shallow:
        try:
            merge_base = _git(root, "merge-base", "HEAD", base_ref)
        except TopologyError:
            merge_base = ""
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    staged: list[str] = []
    status = _git(root, "status", "--porcelain=v2", "--untracked-files=all")
    for line in status.splitlines():
        if line.startswith(("# ", "! ")):
            continue
        if line.startswith("? "):
            added.append(line.removeprefix("? "))
            continue
        if not line.startswith("1 "):
            # Renames, copies, and unmerged records are never a recognized
            # publication projection; fail closed rather than silently drop them.
            raise TopologyError(f"unrecognized repository status record: {line}")
        parts = line.split(" ", 8)
        if len(parts) != 9:
            raise TopologyError(f"unparseable repository status record: {line}")
        index_status, worktree_status = parts[1]
        path = parts[8]
        if index_status != ".":
            staged.append(path)
        if worktree_status == "M":
            modified.append(path)
        elif worktree_status == "D":
            deleted.append(path)
        elif worktree_status != ".":
            raise TopologyError(
                f"unrecognized worktree status {worktree_status}: {path}"
            )
    return TopologyObservation(
        branch=branch,
        head=head,
        head_tree=head_tree,
        head_parents=parents,
        merge_base=merge_base,
        shallow=shallow,
        event_name=event_name,
        event_head_ref=event_head_ref,
        event_base_ref=event_base_ref,
        added_paths=tuple(sorted(added)),
        modified_paths=tuple(sorted(modified)),
        deleted_paths=tuple(sorted(deleted)),
        staged_paths=tuple(sorted(staged)),
    )


def verify(
    observation: TopologyObservation, expectation: TopologyExpectation
) -> tuple[str, ...]:
    """Return the exact mismatch reasons. An empty result accepts the topology."""

    reasons: list[str] = []
    checks: tuple[tuple[str, object, object], ...] = (
        ("branch", observation.branch, expectation.branch),
        ("head", observation.head, expectation.head),
        ("head_tree", observation.head_tree, expectation.head_tree),
        ("head_parents", observation.head_parents, expectation.head_parents),
        ("merge_base", observation.merge_base, expectation.merge_base),
        ("shallow", observation.shallow, expectation.shallow),
        ("event_name", observation.event_name, expectation.event_name),
        ("event_head_ref", observation.event_head_ref, expectation.event_head_ref),
        ("event_base_ref", observation.event_base_ref, expectation.event_base_ref),
        ("added_paths", observation.added_paths, expectation.added_paths),
        ("modified_paths", observation.modified_paths, expectation.modified_paths),
        ("deleted_paths", observation.deleted_paths, expectation.deleted_paths),
        ("staged_paths", observation.staged_paths, expectation.staged_paths),
    )
    for name, observed, expected in checks:
        if observed != expected:
            reasons.append(f"{name}: observed {observed!r} expected {expected!r}")
    return tuple(reasons)


def build_topology(
    kind: str,
    root: Path,
    *,
    source: Path | None = None,
) -> TopologyFixture:
    """Build one temporary projection under ``root`` and observe it.

    Supplying ``source`` builds the base from that repository's committed HEAD
    tree and every candidate from its working tree, so the projected tree is
    exactly the publication candidate tree and the real reader set can run
    inside the checkout without any synthetic file moving an inventory.
    """

    if kind not in TOPOLOGY_KINDS:
        raise TopologyError(f"unknown topology kind: {kind}")
    if root.exists() and any(root.iterdir()):
        raise TopologyError(f"topology root must be empty: {root}")

    # A dirty candidate is defined relative to the source head. Every other
    # source-backed projection is anchored to the source's main authority, so a
    # merge, squash, or push projection carries the real publication baseline.
    base_revision = (
        source_base_revision(source)
        if source is not None and kind != TOPOLOGY_DIRTY_GATE2
        else "HEAD"
    )
    base = _init_base(root, source, base_revision)
    _set_upstream(root, MAIN_BRANCH, base)
    refs: dict[str, str] = {"base": base}

    if kind == TOPOLOGY_DIRTY_GATE2:
        _apply_candidate(root, source, _SYNTHETIC_CANDIDATE)
        if source is not None:
            _verify_candidate(root, source, committed=False)
        dirty_added, dirty_modified, dirty_deleted = (
            (("added.md",), ("AUTHORITY.md",), ())
            if source is None
            else source_dirty_paths(source)
        )
        observation = observe(
            root,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            base_ref=f"refs/remotes/origin/{MAIN_BRANCH}",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch=MAIN_BRANCH,
            head=base,
            head_tree=_git(root, "rev-parse", "HEAD^{tree}"),
            head_parents=(
                () if source is None else source_commit_parents(source, base)
            ),
            merge_base=base,
            shallow=False,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            added_paths=dirty_added,
            modified_paths=dirty_modified,
            deleted_paths=dirty_deleted,
        )
        return TopologyFixture(
            kind=kind,
            root=root,
            expectation=expectation,
            observation=observation,
            refs=refs,
        )

    _git(root, "checkout", "--quiet", "-b", TOPIC_BRANCH)
    if kind == TOPOLOGY_REPAIR_CHILD and source is not None:
        # The repair child keeps the whole chain: main authority, the topic
        # child, then the repair candidate. Both a committed repair (the state a
        # pre-push sweep runs in) and an uncommitted one must be projectable, so
        # the topic revision is the head's parent when the source is clean.
        topic_revision = "HEAD" if source_is_dirty(source) else "HEAD^"
        if committed_entries(source, topic_revision) == committed_entries(
            source, base_revision
        ):
            raise TopologyError(f"source has no committed topic child: {source}")
        _apply_committed_candidate(root, source, topic_revision)
        topic = _commit(root, TOPIC_SUBJECT)
        _verify_committed_candidate(root, committed_entries(source, topic_revision))
    else:
        _apply_candidate(root, source, _SYNTHETIC_CANDIDATE)
        topic = _commit(root, TOPIC_SUBJECT, allow_empty=source is not None)
        if source is not None:
            _verify_candidate(root, source, committed=True)
    _set_upstream(root, TOPIC_BRANCH, topic)
    refs["topic"] = topic
    topic_tree = _git(root, "rev-parse", "HEAD^{tree}")

    if kind == TOPOLOGY_CLEAN_TOPIC:
        observation = observe(
            root,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            base_ref=f"refs/heads/{MAIN_BRANCH}",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch=TOPIC_BRANCH,
            head=topic,
            head_tree=topic_tree,
            head_parents=(base,),
            merge_base=base,
            shallow=False,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
        )
        return TopologyFixture(
            kind=kind,
            root=root,
            expectation=expectation,
            observation=observation,
            refs=refs,
        )

    if kind == TOPOLOGY_REPAIR_CHILD:
        if source is not None and not source_is_dirty(source):
            _apply_committed_candidate(root, source, "HEAD")
            repair = _commit(root, REPAIR_SUBJECT)
            _verify_committed_candidate(root, committed_entries(source, "HEAD"))
        else:
            _apply_candidate(root, source, {"reader.txt": "count=2\n"})
            repair = _commit(root, REPAIR_SUBJECT, allow_empty=source is not None)
            if source is not None:
                _verify_candidate(root, source, committed=True)
        if source is not None:
            if _git(root, "rev-parse", "HEAD^{tree}") == _git(
                root, "rev-parse", "HEAD^^{tree}"
            ):
                raise TopologyError("repair child must change the topic tree")
        _set_upstream(root, TOPIC_BRANCH, repair)
        refs["repair"] = repair
        observation = observe(
            root,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            base_ref=f"refs/heads/{MAIN_BRANCH}",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch=TOPIC_BRANCH,
            head=repair,
            head_tree=_git(root, "rev-parse", "HEAD^{tree}"),
            head_parents=(topic,),
            merge_base=base,
            shallow=False,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
        )
        return TopologyFixture(
            kind=kind,
            root=root,
            expectation=expectation,
            observation=observation,
            refs=refs,
        )

    if kind == TOPOLOGY_PULL_REQUEST_MERGE:
        _git(root, "checkout", "--quiet", MAIN_BRANCH)
        merge = _git(
            root,
            "commit-tree",
            topic_tree,
            "-p",
            base,
            "-p",
            topic,
            "-m",
            f"Merge {TOPIC_BRANCH} into {MAIN_BRANCH}",
        )
        _git(root, "update-ref", PULL_REQUEST_MERGE_REF, merge)
        _git(root, "checkout", "--quiet", "--detach", merge)
        refs["merge"] = merge
        observation = observe(
            root,
            event_name=EVENT_PULL_REQUEST,
            event_head_ref=TOPIC_BRANCH,
            event_base_ref=MAIN_BRANCH,
            base_ref=f"refs/heads/{MAIN_BRANCH}",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch="HEAD",
            head=merge,
            head_tree=topic_tree,
            head_parents=(base, topic),
            merge_base=base,
            shallow=False,
            event_name=EVENT_PULL_REQUEST,
            event_head_ref=TOPIC_BRANCH,
            event_base_ref=MAIN_BRANCH,
        )
        return TopologyFixture(
            kind=kind,
            root=root,
            expectation=expectation,
            observation=observation,
            refs=refs,
            event_path=_write_pull_request_event(root, base=base, head=topic),
        )

    if kind == TOPOLOGY_SHALLOW_PULL_REQUEST:
        # Integration checks out the synthetic merge commit at depth one and
        # detached, not the named topic branch. Modelling the branch instead
        # would describe the pull-request head rather than the checkout.
        merge = _git(
            root,
            "commit-tree",
            topic_tree,
            "-p",
            base,
            "-p",
            topic,
            "-m",
            f"Merge {topic} into {base}",
        )
        _git(root, "update-ref", PULL_REQUEST_MERGE_REF, merge)
        refs["merge"] = merge
        checkout = root.parent / f"{root.name}-shallow"
        _git(root, "init", "--quiet", str(checkout))
        _git(checkout, "remote", "add", "origin", str(root))
        _git(
            checkout,
            "fetch",
            "--quiet",
            "--depth",
            "1",
            "origin",
            f"+{PULL_REQUEST_MERGE_REF}:refs/remotes/pull/1/merge",
        )
        _git(checkout, "checkout", "--quiet", "--detach", "refs/remotes/pull/1/merge")
        refs["shallow_head"] = _git(checkout, "rev-parse", "HEAD")
        observation = observe(
            checkout,
            event_name=EVENT_PULL_REQUEST,
            event_head_ref=TOPIC_BRANCH,
            event_base_ref=MAIN_BRANCH,
            base_ref="",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch="HEAD",
            head=merge,
            head_tree=topic_tree,
            head_parents=(),
            merge_base="",
            shallow=True,
            event_name=EVENT_PULL_REQUEST,
            event_head_ref=TOPIC_BRANCH,
            event_base_ref=MAIN_BRANCH,
        )
        return TopologyFixture(
            kind=kind,
            root=checkout,
            expectation=expectation,
            observation=observation,
            refs=refs,
            event_path=_write_pull_request_event(checkout, base=base, head=topic),
        )

    _git(root, "checkout", "--quiet", MAIN_BRANCH)
    _git(root, "merge", "--quiet", "--squash", TOPIC_BRANCH)
    squash = _commit(root, TOPIC_SUBJECT)
    _set_upstream(root, MAIN_BRANCH, squash)
    refs["squash"] = squash

    if kind == TOPOLOGY_MAIN_PUSH:
        # Integration checks the merged head out at depth one, exactly as it
        # does for a pull request. Reusing the full local repository here would
        # hide every guard that depends on history or on the shallow boundary.
        checkout = root.parent / f"{root.name}-mainpush"
        _git(root, "init", "--quiet", str(checkout))
        _git(checkout, "remote", "add", "origin", str(root))
        _git(
            checkout,
            "fetch",
            "--quiet",
            "--depth",
            "1",
            "origin",
            f"+refs/heads/{MAIN_BRANCH}:refs/remotes/origin/{MAIN_BRANCH}",
        )
        _git(checkout, "checkout", "--quiet", "-B", MAIN_BRANCH, squash)
        observation = observe(
            checkout,
            event_name=EVENT_PUSH,
            event_head_ref=MAIN_BRANCH,
            event_base_ref="",
            base_ref="",
        )
        expectation = TopologyExpectation(
            kind=kind,
            branch=MAIN_BRANCH,
            head=squash,
            head_tree=topic_tree,
            head_parents=(),
            merge_base="",
            shallow=True,
            event_name=EVENT_PUSH,
            event_head_ref=MAIN_BRANCH,
            event_base_ref="",
        )
        return TopologyFixture(
            kind=kind,
            root=checkout,
            expectation=expectation,
            observation=observation,
            refs=refs,
        )

    observation = observe(
        root,
        event_name=EVENT_LOCAL,
        event_head_ref="",
        event_base_ref="",
        base_ref=f"refs/remotes/origin/{MAIN_BRANCH}",
    )
    expectation = TopologyExpectation(
        kind=kind,
        branch=MAIN_BRANCH,
        head=squash,
        head_tree=topic_tree,
        head_parents=(base,),
        merge_base=squash,
        shallow=False,
        event_name=EVENT_LOCAL,
        event_head_ref="",
        event_base_ref="",
    )
    return TopologyFixture(
        kind=kind,
        root=root,
        expectation=expectation,
        observation=observation,
        refs=refs,
    )


def build_all(
    root: Path,
    *,
    source: Path | None = None,
) -> tuple[TopologyFixture, ...]:
    """Build every standardized projection under one temporary root."""

    fixtures: list[TopologyFixture] = []
    for kind in TOPOLOGY_KINDS:
        fixtures.append(build_topology(kind, root / kind, source=source))
    return tuple(fixtures)


def rejected_variants(
    expectation: TopologyExpectation,
) -> tuple[tuple[str, TopologyExpectation], ...]:
    """Return named corruptions of one expectation that must all be rejected."""

    wrong_parent = "0" * 40
    variants: list[tuple[str, TopologyExpectation]] = [
        (
            "wrong_parent",
            _replace(expectation, head_parents=(wrong_parent,)),
        ),
        ("wrong_ref", _replace(expectation, branch="wrong/branch")),
        ("wrong_tree", _replace(expectation, head_tree="1" * 40)),
        ("wrong_shallow", _replace(expectation, shallow=not expectation.shallow)),
        (
            "wrong_event",
            _replace(
                expectation,
                event_name=(
                    EVENT_PUSH
                    if expectation.event_name != EVENT_PUSH
                    else EVENT_PULL_REQUEST
                ),
            ),
        ),
        ("wrong_head", _replace(expectation, head="2" * 40)),
        (
            "wrong_dirty_set",
            _replace(expectation, modified_paths=("unexpected.md",)),
        ),
        (
            "wrong_staged_set",
            _replace(expectation, staged_paths=("unexpected.md",)),
        ),
    ]
    return tuple(variants)


def _replace(
    expectation: TopologyExpectation, **changes: object
) -> TopologyExpectation:
    fields: dict[str, object] = {
        "kind": expectation.kind,
        "branch": expectation.branch,
        "head": expectation.head,
        "head_tree": expectation.head_tree,
        "head_parents": expectation.head_parents,
        "merge_base": expectation.merge_base,
        "shallow": expectation.shallow,
        "event_name": expectation.event_name,
        "event_head_ref": expectation.event_head_ref,
        "event_base_ref": expectation.event_base_ref,
        "added_paths": expectation.added_paths,
        "modified_paths": expectation.modified_paths,
        "deleted_paths": expectation.deleted_paths,
        "staged_paths": expectation.staged_paths,
    }
    fields.update(changes)
    return TopologyExpectation(**fields)  # pyright: ignore[reportArgumentType]


def assert_topology(fixture: TopologyFixture) -> None:
    """Fail closed unless the built projection matches its own expectation."""

    reasons = verify(fixture.observation, fixture.expectation)
    if reasons:
        raise TopologyError(f"{fixture.kind} rejected: {'; '.join(reasons)}")


def sequence_is_complete(kinds: Sequence[str]) -> bool:
    """Return whether the supplied kinds cover every standardized projection."""

    return tuple(sorted(set(kinds))) == TOPOLOGY_KINDS
