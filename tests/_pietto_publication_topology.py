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

import subprocess
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

TOPIC_BRANCH = "phase54/post-slice12-workflow-hardening"
MAIN_BRANCH = "main"
BASE_SUBJECT = "Base commit"
TOPIC_SUBJECT = "Add Pietto workflow convergence tooling"
REPAIR_SUBJECT = "Fix Pietto workflow convergence tooling"

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


def _seed_from_source(root: Path, source: Path) -> None:
    """Copy one source repository's tracked and untracked working tree into root."""

    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=source,
        text=True,
        capture_output=True,
    )
    if listing.returncode != 0:
        raise TopologyError(f"cannot list {source}: {listing.stderr.strip()}")
    entries = [line for line in listing.stdout.splitlines() if line]
    if not entries:
        raise TopologyError(f"source repository has no content: {source}")
    for relative in entries:
        origin = source / relative
        if not origin.is_file():
            continue
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(origin.read_bytes())


def _init_base(root: Path, source: Path | None = None) -> str:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--quiet", "--initial-branch", MAIN_BRANCH)
    if source is None:
        _write(root, "AUTHORITY.md", "# authority\n\nbase\n")
        _write(root, "reader.txt", "count=1\n")
    else:
        # Projections built from the real tree let the actual reader set run
        # inside each checkout; a synthetic repository proves nothing about them.
        _seed_from_source(root, source)
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", BASE_SUBJECT)
    return _git(root, "rev-parse", "HEAD")


def run_in_projection(
    fixture: TopologyFixture,
    command: Sequence[str],
) -> subprocess.CompletedProcess[str]:
    """Run one read-only command inside a built projection and return its result.

    This is the entry point that lets the real topology-sensitive reader set
    execute under every projection rather than only self-verifying the fixture.
    """

    if not command:
        raise TopologyError("a projection command must not be empty")
    return subprocess.run(
        list(command),
        cwd=fixture.root,
        text=True,
        capture_output=True,
    )


def _commit(root: Path, subject: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", subject)
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

    Supplying ``source`` seeds the projection from that repository's working
    tree, so the real reader set can run inside the checkout.
    """

    if kind not in TOPOLOGY_KINDS:
        raise TopologyError(f"unknown topology kind: {kind}")
    if root.exists() and any(root.iterdir()):
        raise TopologyError(f"topology root must be empty: {root}")

    base = _init_base(root, source)
    _set_upstream(root, MAIN_BRANCH, base)
    refs: dict[str, str] = {"base": base}

    if kind == TOPOLOGY_DIRTY_GATE2:
        _write(root, "AUTHORITY.md", "# authority\n\nbase\ncandidate\n")
        _write(root, "added.md", "# added\n")
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
            head_parents=(),
            merge_base=base,
            shallow=False,
            event_name=EVENT_LOCAL,
            event_head_ref="",
            event_base_ref="",
            added_paths=("added.md",),
            modified_paths=("AUTHORITY.md",),
        )
        return TopologyFixture(
            kind=kind,
            root=root,
            expectation=expectation,
            observation=observation,
            refs=refs,
        )

    _git(root, "checkout", "--quiet", "-b", TOPIC_BRANCH)
    _write(root, "AUTHORITY.md", "# authority\n\nbase\ncandidate\n")
    _write(root, "added.md", "# added\n")
    topic = _commit(root, TOPIC_SUBJECT)
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
        _write(root, "reader.txt", "count=2\n")
        repair = _commit(root, REPAIR_SUBJECT)
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
        _git(root, "update-ref", "refs/pull/1/merge", merge)
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
        _git(root, "update-ref", "refs/pull/1/merge", merge)
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
            "+refs/pull/1/merge:refs/remotes/pull/1/merge",
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
