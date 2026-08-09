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
import sys
import tarfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import _phase54_active_gate2_manifest

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

# The topic branch that carries a publication moves with every Gate. Reading it
# from the active Gate 2 manifest keeps one authority for the name instead of
# freezing a stale branch into the fixtures every later Slice must work around.
TOPIC_BRANCH = _phase54_active_gate2_manifest.phase54_publication_topic_branch()
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


def _git_raw(root: Path, *args: str) -> str:
    """Run one Git command and return its output without stripping."""

    environment = dict(_FIXED_IDENTITY)
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        env={**_inherited_environment(), **environment},
    )
    if result.returncode != 0:
        raise TopologyError(
            f"git {' '.join(args)} failed: {_decoded(result.stderr).strip()}"
        )
    return _decoded(result.stdout)


_FALLBACK_LOCAL_GIT_VARIABLES: tuple[str, ...] = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CONFIG",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_IMPLICIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_NO_REPLACE_OBJECTS",
    "GIT_OBJECT_DIRECTORY",
    "GIT_PREFIX",
    "GIT_REPLACE_REF_BASE",
    "GIT_SHALLOW_FILE",
    "GIT_WORK_TREE",
)


_LOCAL_GIT_VARIABLES: tuple[str, ...] | None = None


def reset_local_git_variables() -> None:
    """Forget a cached derivation so the next call probes Git again."""

    global _LOCAL_GIT_VARIABLES

    _LOCAL_GIT_VARIABLES = None


def local_git_variables() -> tuple[str, ...]:
    """Return every environment variable that relocates or reconfigures Git.

    Git reports its own complete set, which a hand-maintained list cannot
    track: an inherited ``GIT_SHALLOW_FILE`` alone makes a shallow repository
    report itself as complete. Discovery runs under the fallback-sanitized
    environment so it never inherits the overrides it is asked to report, and
    the fallback is unioned in so the removed set can only grow.
    """

    global _LOCAL_GIT_VARIABLES

    if _LOCAL_GIT_VARIABLES is not None:
        return _LOCAL_GIT_VARIABLES
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--local-env-vars"],
            capture_output=True,
            env={
                name: value
                for name, value in os.environ.items()
                if name not in _FALLBACK_LOCAL_GIT_VARIABLES
            },
        )
    except OSError:
        return _FALLBACK_LOCAL_GIT_VARIABLES
    if result.returncode != 0:
        return _FALLBACK_LOCAL_GIT_VARIABLES
    reported = tuple(name for name in _decoded(result.stdout).split() if name)
    if not reported:
        return _FALLBACK_LOCAL_GIT_VARIABLES
    # Only a complete derivation is cached. A probe that fails once must
    # not freeze the degraded answer for the life of the process.
    _LOCAL_GIT_VARIABLES = tuple(
        sorted(set(reported) | set(_FALLBACK_LOCAL_GIT_VARIABLES))
    )
    return _LOCAL_GIT_VARIABLES


def _inherited_environment() -> dict[str, str]:
    """Return the caller environment without any repository relocation.

    ``GIT_DIR`` and its relatives override the working directory, so inheriting
    them would make a fixture command operate on the caller's repository
    instead of the projection.
    """

    environment = dict(os.environ)
    for name in local_git_variables():
        environment.pop(name, None)
    return environment


def _write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _decoded(payload: bytes) -> str:
    """Decode Git output the way the filesystem does, preserving stray bytes."""

    return payload.decode(sys.getfilesystemencoding(), "surrogateescape")


def _source_output(source: Path, *args: str) -> str:
    # Git paths are bytes. Decoding strictly would raise before a valid but
    # undecodable path could even be reported.
    result = subprocess.run(
        ["git", *args],
        cwd=source,
        capture_output=True,
        env=_inherited_environment(),
    )
    if result.returncode != 0:
        raise TopologyError(f"cannot read {source}: {_decoded(result.stderr).strip()}")
    return _decoded(result.stdout)


def _merge_tree(root: Path, base: str, topic: str) -> str:
    """Return the tree a real merge of base and topic produces.

    ``commit-tree`` records whatever tree it is handed, so a diverged main would
    otherwise lose its own changes in the projected merge.
    """

    result = subprocess.run(
        ["git", "merge-tree", "--write-tree", base, topic],
        cwd=root,
        capture_output=True,
        env=_inherited_environment(),
    )
    if result.returncode != 0:
        raise TopologyError(
            f"cannot merge {base} and {topic}: {_decoded(result.stderr).strip()}"
        )
    reported = _decoded(result.stdout).splitlines()
    if not reported or len(reported[0].strip()) != 40:
        raise TopologyError(f"unparseable merge tree for {base} and {topic}")
    return reported[0].strip()


def _reserve_sibling(root: Path, suffix: str) -> Path:
    """Return an unused sibling directory path, or fail closed."""

    destination = root.parent / f"{root.name}-{suffix}"
    if destination.exists() or destination.is_symlink():
        raise TopologyError(f"projection sibling path is occupied: {destination}")
    return destination


def _write_pull_request_event(root: Path, *, base: str, head: str) -> Path:
    """Write one pull-request event payload beside, never inside, a projection."""

    destination = root.parent / f"{root.name}-event.json"
    if destination.exists() or destination.is_symlink():
        raise TopologyError(f"event payload path is occupied: {destination}")
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
            env=_inherited_environment(),
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


def _mirror_conversion_config(root: Path, source: Path) -> None:
    """Copy the source's content-conversion configuration into the projection.

    Git may clean content on the way into a commit. The projection commits the
    same working-tree bytes, so it must convert them by the same rules or its
    tree would not be the candidate's tree.
    """

    for record in _source_output(source, "config", "--list").splitlines():
        key, separator, value = record.partition("=")
        if not separator:
            continue
        lowered = key.lower()
        if lowered in (
            "core.autocrlf",
            "core.eol",
            "core.filemode",
            "core.safecrlf",
        ) or lowered.startswith("filter."):
            _git(root, "config", key, value)


def _reject_foreign_object_format(source: Path) -> None:
    """Refuse a source whose object names are not the ones this module asserts.

    Every identity here is a forty character SHA-1 object name. A SHA-256
    repository is a valid Git repository with different names, so it is refused
    instead of projected under an identity model that does not describe it.
    """

    reported = _source_output(source, "rev-parse", "--show-object-format").strip()
    if reported and reported != "sha1":
        raise TopologyError(f"source uses the {reported} object format: {source}")


def _reject_unreproducible_source(source: Path) -> None:
    """Refuse a source whose content authority the projection cannot reproduce.

    ``core.symlinks=false`` stores a symbolic entry as a plain file, and a local
    attributes authority decides which paths a clean filter touches. Neither
    travels with the tree, so a projection built from such a source would carry
    a different candidate than the one it claims to be.
    """

    symlinks = _source_output(
        source, "config", "--bool", "--default", "true", "--get", "core.symlinks"
    ).strip()
    if symlinks == "false":
        raise TopologyError(f"source disables symbolic links: {source}")
    attributes = _source_output(
        source, "config", "--default", "", "--get", "core.attributesFile"
    ).strip()
    if attributes:
        raise TopologyError(f"source declares a local attributes file: {source}")
    git_dir = _source_output(source, "rev-parse", "--absolute-git-dir").strip()
    if git_dir and (Path(git_dir) / "info" / "attributes").exists():
        raise TopologyError(f"source declares repository-local attributes: {source}")


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

    for record in _source_lines(
        source, "status", "--porcelain=v2", "--untracked-files=all"
    ):
        if not record.startswith(("1 ", "2 ", "u ")):
            continue
        fields = record.split(" ")
        if len(fields) < 9:
            raise TopologyError(f"unparseable source status record: {record}")
        # An intent-to-add entry reports a clean index status and a zero index
        # mode. It is invisible to a cached diff but is still a non-empty index,
        # which the gate contract forbids.
        if fields[1][0] != "." or fields[4] == "000000":
            raise TopologyError(f"source repository has a non-empty index: {source}")


def _source_working_paths(source: Path) -> tuple[str, ...]:
    """Return the paths that actually exist in one source working tree.

    A tracked path the source deleted is still listed by the index, so the
    listing is filtered by real existence. Otherwise the deletion would never
    reach the projection and the projected tree would not be the candidate.
    """

    _reject_foreign_object_format(source)
    _reject_unreproducible_source(source)
    _reject_staged_source(source)
    _reject_gitlink_source(source)
    listed = _source_lines(
        source, "ls-files", "--cached", "--others", "--exclude-standard"
    )
    # A sparse checkout leaves skip-worktree entries unmaterialized. They are
    # still part of the candidate tree, so only a real deletion removes a path.
    _, _, deleted_paths = source_dirty_paths(source)
    deleted = set(deleted_paths)
    tracked = set(_source_lines(source, "ls-files", "--cached"))

    def _blocked(relative: str) -> bool:
        # A symbolic or non-directory ancestor removes the entry from the tree,
        # so it must never make a deleted path look present. Only components
        # inside the repository are Git entries; the path to the repository is
        # the caller's and may legitimately cross a link.
        for ancestor in reversed((source / relative).parents):
            if ancestor == source or source not in ancestor.parents:
                continue
            if ancestor.is_symlink() or (ancestor.exists() and not ancestor.is_dir()):
                return True
        return False

    def _present(relative: str) -> bool:
        if _blocked(relative):
            return False
        path = source / relative
        return path.is_symlink() or path.is_file()

    entries = tuple(
        relative
        for relative in listed
        if _present(relative)
        or (
            # Absent, tracked, and not deleted: a skip-worktree entry.
            relative in tracked
            and relative not in deleted
            and not _blocked(relative)
            and not (source / relative).exists()
        )
    )
    # A tracked path may be deleted, or replaced by a directory that now holds
    # new entries. Both are trees Git can represent. Only an entry that exists
    # as something else entirely - a device or socket - is refused.
    nested = tuple(relative for relative in listed if relative.endswith("/"))
    if nested:
        # ``ls-files --others`` reports an untracked nested repository as a
        # directory entry. Adding it would record a gitlink this module does
        # not model, so the source is refused instead.
        raise TopologyError(f"source contains a nested repository: {nested[:5]}")
    kept = set(entries)
    unusable = tuple(
        relative
        for relative in listed
        if relative not in kept
        and not _blocked(relative)
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
    """Return one source repository's (added, modified, deleted) uncommitted paths.

    Git's own status is the authority. ``ls-files --deleted`` uses a bare stat
    and therefore misses a path whose directory was replaced by a symbolic link,
    which Git itself reports as deleted.
    """

    _reject_staged_source(source)
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for record in _source_lines(
        source, "status", "--porcelain=v2", "--untracked-files=all"
    ):
        if record.startswith("? "):
            added.append(record.removeprefix("? "))
            continue
        if not record.startswith("1 "):
            continue
        fields = record.split(" ", 8)
        if len(fields) != 9:
            raise TopologyError(f"unparseable source status record: {record}")
        worktree_status = fields[1][1]
        path = fields[8]
        if worktree_status == "D":
            deleted.append(path)
        elif worktree_status in ("M", "T"):
            modified.append(path)
    return tuple(sorted(added)), tuple(sorted(modified)), tuple(sorted(deleted))


def _source_lines(source: Path, *args: str) -> tuple[str, ...]:
    """Return one read-only Git listing, split on NUL.

    Git path output is NUL separated for a reason: a path may contain a
    newline, and splitting on lines would silently break that entry in two.
    """

    return tuple(
        record for record in _source_output(source, *args, "-z").split("\0") if record
    )


def _blob_oid(data: bytes) -> str:
    """Return the Git blob object name of one payload."""

    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _entry_of(path: Path) -> tuple[str, str]:
    """Return one path's exact Git entry: its mode and its blob object name."""

    if path.is_symlink():
        # A link target is bytes on disk; encode it the way the filesystem does.
        return "120000", _blob_oid(os.fsencode(os.readlink(path)))
    data = path.read_bytes()
    executable = bool(path.stat().st_mode & 0o111)
    return ("100755" if executable else "100644"), _blob_oid(data)


def candidate_entries(source: Path) -> dict[str, tuple[str, str]]:
    """Return the exact Git entry of every path in one source working tree.

    Tree identity includes entry type and mode, and Git may apply a clean filter
    that the raw working-tree bytes do not show. Unchanged paths therefore take
    their recorded index entry, and only changed paths are hashed - through Git,
    so the source's own conversion rules decide the object name.
    """

    wanted = set(_source_working_paths(source))
    # ``core.filemode=false`` tells Git to keep the recorded mode, so the
    # filesystem permission bit is not the authority on a tracked path.
    # Git's default is true, and an unset key exits non-zero without --default.
    filemode = (
        _source_output(
            source, "config", "--bool", "--default", "true", "--get", "core.filemode"
        ).strip()
        != "false"
    )
    index_modes: dict[str, str] = {}
    entries: dict[str, tuple[str, str]] = {}
    for record in _source_lines(source, "ls-files", "--stage"):
        metadata, separator, relative = record.partition("\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            raise TopologyError(f"unparseable source index record: {record}")
        # ``ls-files --stage`` prints mode, object name, then stage number.
        index_modes[relative] = fields[0]
        if relative in wanted:
            entries[relative] = (fields[0], fields[1])
    added, modified, _ = source_dirty_paths(source)
    for relative in (*added, *modified):
        if relative not in wanted:
            continue
        path = source / relative
        if path.is_symlink():
            entries[relative] = _entry_of(path)
            continue
        oid = _source_output(
            source, "hash-object", "--path", relative, "--", str(path)
        ).strip()
        if len(oid) != 40:
            raise TopologyError(f"cannot hash {relative} in {source}")
        recorded = index_modes.get(relative)
        # Disabling filemode makes Git ignore the working-tree executable bit
        # entirely: a recorded regular-file mode is kept, and anything else -
        # including a new file - is recorded as a plain regular file. It never
        # carries an entry type across a type change.
        if not filemode:
            mode = (
                recorded
                if recorded is not None and recorded.startswith("100")
                else "100644"
            )
        else:
            mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        entries[relative] = (mode, oid)
    missing = wanted - set(entries)
    if missing:
        raise TopologyError(
            f"source entries have no object name: {sorted(missing)[:5]}"
        )
    return entries


def _directory_entries(root: Path) -> dict[str, tuple[str, str]]:
    """Return the Git entry of every working-tree path under root.

    Regular files are hashed through Git so the projection's own conversion
    rules - mirrored from the source - decide the object name, exactly as they
    would when the candidate is committed.
    """

    filemode = (
        _git(root, "config", "--bool", "--default", "true", "--get", "core.filemode")
        != "false"
    )
    index_modes: dict[str, str] = {}
    listing = _git_raw(root, "ls-files", "--stage", "-z")
    for record in (entry for entry in listing.split("\0") if entry):
        metadata, separator, relative = record.partition("\t")
        fields = metadata.split()
        if separator and len(fields) == 3:
            index_modes[relative] = fields[0]
    observed: dict[str, tuple[str, str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            observed[str(relative)] = _entry_of(path)
            continue
        if not path.is_file():
            continue
        oid = _git(root, "hash-object", "--path", str(relative), "--", str(path))
        if len(oid) != 40:
            raise TopologyError(f"cannot hash {relative} in {root}")
        recorded = index_modes.get(str(relative))
        if not filemode:
            mode = (
                recorded
                if recorded is not None and recorded.startswith("100")
                else "100644"
            )
        else:
            mode = "100755" if path.stat().st_mode & 0o111 else "100644"
        observed[str(relative)] = (mode, oid)
    return observed


def _tree_entries(root: Path) -> dict[str, tuple[str, str]]:
    observed: dict[str, tuple[str, str]] = {}
    listing = _git_raw(root, "ls-tree", "-r", "-z", "HEAD")
    for line in (record for record in listing.split("\0") if record):
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
        env=_inherited_environment(),
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
        if not origin.is_symlink() and not origin.is_file():
            # An unmaterialized sparse entry keeps whatever the base placed
            # there; it is unchanged by definition.
            continue
        destination = root / relative
        # A path may change between file, symlink, and directory. Clear whatever
        # occupies the destination or blocks its parents, never stepping above
        # the projection root: the caller owns everything outside it.
        blocking = [
            ancestor
            for ancestor in destination.parents
            if root in ancestor.parents or ancestor == root
        ]
        for ancestor in reversed(blocking):
            if ancestor == root:
                continue
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
    """Empty the working tree, directories included.

    Leaving an empty directory behind would block materializing a file at the
    same path, which is exactly what a directory to file transition needs.
    """

    for entry in sorted(root.iterdir()):
        if entry.name == ".git":
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


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
        _reject_foreign_object_format(source)
        _reject_unreproducible_source(source)
        _reject_staged_source(source)
        _reject_gitlink_source(source)
        _mirror_conversion_config(root, source)
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


def _optional_reference(root: Path, reference: str) -> str:
    """Return one reference's object name, or the empty string when unresolvable.

    A reference that could not be resolved when the window opened must be
    revalidated as still unresolvable: comparing against a truthy value only
    would make that half of the check unreachable.
    """

    try:
        return _git(root, "rev-parse", reference)
    except TopologyError:
        return ""


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
    # Read every derived fact from the resolved object name, not from the moving
    # reference, and confirm the reference again at the end of the window.
    head_tree = _git(root, "rev-parse", f"{head}^{{tree}}")
    shallow_reading = _git(root, "rev-parse", "--is-shallow-repository")
    shallow = shallow_reading == "true"
    # The parent line is graph truncation dependent, not content addressed: a
    # concurrent deepen reveals a boundary commit's parents while the shallow
    # flag itself stays true, so the raw line is kept for revalidation.
    parent_reading = _git(root, "rev-list", "--parents", "-n", "1", head)
    parents = tuple(parent_reading.split()[1:])
    merge_base = ""
    base_identity = ""
    base_probed = bool(base_ref) and not shallow
    if base_probed:
        try:
            base_identity = _git(root, "rev-parse", base_ref)
            merge_base = _git(root, "merge-base", head, base_ref)
        except TopologyError:
            base_identity = ""
            merge_base = ""
    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    staged: list[str] = []
    # NUL separated records keep the exact path: the line oriented form quotes
    # any path containing a newline, a tab, or a non-ASCII byte.
    status_arguments = ("status", "--porcelain=v2", "-z", "--untracked-files=all")
    status = _git_raw(root, *status_arguments)
    for line in (record for record in status.split("\0") if record):
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
        if worktree_status in ("M", "T"):
            # A regular file that became a symbolic link, or the reverse, is a
            # modification of that path, not an unknown state.
            modified.append(path)
        elif worktree_status == "D":
            deleted.append(path)
        elif worktree_status != ".":
            raise TopologyError(
                f"unrecognized worktree status {worktree_status}: {path}"
            )
    if (
        _git(root, "rev-parse", "HEAD") != head
        or _git(root, "rev-parse", "--abbrev-ref", "HEAD") != branch
        or _git_raw(root, *status_arguments) != status
        or (base_probed and _optional_reference(root, base_ref) != base_identity)
        or _git(root, "rev-parse", "--is-shallow-repository") != shallow_reading
        or _git(root, "rev-list", "--parents", "-n", "1", head) != parent_reading
    ):
        # Every fact this observation reports must still hold: the object name,
        # the symbolic identity, the working state, the base authority in both
        # directions, the shallow boundary, and the parent line. A concurrent
        # unshallow or deepen leaves all the others equal while the shallow and
        # parent facts go stale, so they are re-read here too.
        raise TopologyError(f"repository moved while observing {root}")
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
    if root.is_symlink():
        # A symbolic root would place the whole projection in its target.
        raise TopologyError(f"topology root must not be a symbolic link: {root}")
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
        if source is not None and not source_is_dirty(source):
            # A gate candidate is defined by its non-empty dirty set. A clean
            # source would project an empty one and silently skip the branch
            # every dirty-state reader exists to check.
            raise TopologyError(f"source has no uncommitted candidate: {source}")
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
    if source is not None and not source_is_dirty(source):
        # The candidate is already committed, so the projection reuses its real
        # object identity instead of re-committing its tree under a new one.
        committed_revision = "HEAD^" if kind == TOPOLOGY_REPAIR_CHILD else "HEAD"
        topic = _source_output(source, "rev-parse", committed_revision).strip()
        if not topic:
            raise TopologyError(f"cannot resolve {committed_revision} in {source}")
        if topic == base:
            # Without a candidate generation there is no topic to project.
            raise TopologyError(f"source has no committed topic child: {source}")
        _git(root, "checkout", "--quiet", "-B", TOPIC_BRANCH, topic)
        _verify_committed_candidate(root, committed_entries(source, committed_revision))
        topic_parents = source_commit_parents(source, committed_revision)
    elif kind == TOPOLOGY_REPAIR_CHILD and source is not None:
        # The repair child keeps the whole chain: main authority, the committed
        # topic child, then the uncommitted repair candidate. The topic child
        # already exists, so its real commit is checked out rather than rebuilt.
        if committed_entries(source, "HEAD") == committed_entries(
            source, base_revision
        ):
            raise TopologyError(f"source has no committed topic child: {source}")
        topic = _source_output(source, "rev-parse", "HEAD").strip()
        if not topic:
            raise TopologyError(f"cannot resolve HEAD in {source}")
        _git(root, "checkout", "--quiet", "-B", TOPIC_BRANCH, topic)
        _verify_committed_candidate(root, committed_entries(source, "HEAD"))
        topic_parents = source_commit_parents(source, "HEAD")
    else:
        candidate_parent = base
        if source is not None:
            # An uncommitted candidate is published as a child of the source
            # head, not of main. Chaining onto the real commit keeps the merge,
            # squash, and push projections on the topology that will exist.
            head_sha = _source_output(source, "rev-parse", "HEAD").strip()
            if head_sha and head_sha != base:
                _git(root, "checkout", "--quiet", "-B", TOPIC_BRANCH, head_sha)
                candidate_parent = head_sha
        _apply_candidate(root, source, _SYNTHETIC_CANDIDATE)
        topic = _commit(root, TOPIC_SUBJECT, allow_empty=source is not None)
        if source is not None:
            _verify_candidate(root, source, committed=True)
        topic_parents = (candidate_parent,)
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
            # A real topic branch may already carry several non-amend children,
            # so the declared parent is the checked-out generation's own parent.
            head_parents=topic_parents,
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
            repair = _source_output(source, "rev-parse", "HEAD").strip()
            _git(root, "checkout", "--quiet", "-B", TOPIC_BRANCH, repair)
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
        merged_tree = _merge_tree(root, base, topic)
        merge = _git(
            root,
            "commit-tree",
            merged_tree,
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
            head_tree=merged_tree,
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
        merged_tree = _merge_tree(root, base, topic)
        merge = _git(
            root,
            "commit-tree",
            merged_tree,
            "-p",
            base,
            "-p",
            topic,
            "-m",
            f"Merge {topic} into {base}",
        )
        _git(root, "update-ref", PULL_REQUEST_MERGE_REF, merge)
        refs["merge"] = merge
        checkout = _reserve_sibling(root, "shallow")
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
            head_tree=merged_tree,
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
    # A squash of a diverged main carries both sides, so the expected tree is
    # the real merge result, not the topic tree.
    squash_tree = _merge_tree(root, base, topic)
    if _git(root, "rev-parse", f"{squash}^{{tree}}") != squash_tree:
        raise TopologyError(f"squash tree does not match the merge of {base}, {topic}")

    if kind == TOPOLOGY_MAIN_PUSH:
        # Integration checks the merged head out at depth one, exactly as it
        # does for a pull request. Reusing the full local repository here would
        # hide every guard that depends on history or on the shallow boundary.
        checkout = _reserve_sibling(root, "mainpush")
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
            head_tree=squash_tree,
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
        head_tree=squash_tree,
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
