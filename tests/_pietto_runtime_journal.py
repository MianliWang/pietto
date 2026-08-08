"""Schema validation and atomic replacement for the non-authoritative journal.

The runtime journal is a small local orientation aid for long workflows. It is
deliberately *not* repository state and *not* evidence: Git, the live
repository, GitHub and continuous-integration state, repository authority
documents, and immutable create-once evidence all outrank it. A journal that
could be mistaken for authority would become an uncontrolled validation input,
so every payload must carry explicit non-authority markers and every write must
refuse to touch the repository.
"""

from __future__ import annotations

import functools
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

AUTHORITY_MARKER = "NON_AUTHORITATIVE"
REPLACEMENT_MARKER = "SAFE_TO_REPLACE_ATOMICALLY"
REVALIDATION_MARKER = "LIVE_STATE_MUST_BE_REVALIDATED"

REQUIRED_MARKERS: Mapping[str, str] = {
    "authority": AUTHORITY_MARKER,
    "replacement": REPLACEMENT_MARKER,
    "revalidation": REVALIDATION_MARKER,
}

REQUIRED_KEYS: tuple[str, ...] = (
    "authority",
    "gate_state",
    "interlude",
    "journal_kind",
    "journal_version",
    "lifecycle",
    "outranked_by",
    "replacement",
    "revalidation",
    "trusted_base_sha",
    "trusted_base_tree",
)

REQUIRED_OUTRANKING: tuple[str, ...] = (
    "git",
    "github_and_ci_state",
    "immutable_create_once_evidence",
    "live_repository_state",
    "repository_authority_documents",
)


class JournalError(Exception):
    """Raised when a journal payload or destination is unusable."""


def validate_payload(payload: Mapping[str, Any]) -> tuple[str, ...]:
    """Return the exact schema violations. An empty result accepts the payload."""

    problems: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in payload:
            problems.append(f"missing key: {key}")
    for key, marker in REQUIRED_MARKERS.items():
        if key in payload and payload[key] != marker:
            problems.append(f"{key} must be {marker}, got {payload[key]!r}")
    version = payload.get("journal_version")
    # `isinstance(True, int)` is true, so a boolean must be excluded explicitly.
    if version is not None and (type(version) is not int or version < 1):
        problems.append(f"journal_version must be a positive integer, got {version!r}")
    outranked = payload.get("outranked_by")
    if outranked is None:
        pass
    elif not isinstance(outranked, Sequence) or isinstance(outranked, (str, bytes)):
        problems.append("outranked_by must be a sequence of authority names")
    else:
        missing = [name for name in REQUIRED_OUTRANKING if name not in tuple(outranked)]
        if missing:
            problems.append(f"outranked_by omits: {', '.join(missing)}")
    return tuple(problems)


def is_authoritative(payload: Mapping[str, Any]) -> bool:
    """Always False. The journal never becomes authority for any decision."""

    return False


def _enclosing_worktree(directory: Path) -> Path | None:
    """Return the Git worktree containing ``directory``, or None."""

    try:
        result = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            text=True,
            capture_output=True,
            check=False,
            env=_isolated_environment(),
        )
    except OSError as error:
        # An unusable probe is not evidence that the path is outside a
        # repository, so the destination guard must not treat it as one.
        raise JournalError(f"cannot probe {directory} for a repository: {error}")
    if result.returncode != 0:
        # Only a definite "this is not a repository" answer may be treated as
        # one. A refused probe - dubious ownership, for instance - is an error.
        if "not a git repository" not in result.stderr.lower():
            raise JournalError(
                f"cannot probe {directory} for a repository: {result.stderr.strip()}"
            )
        return None
    top = result.stdout.strip()
    return Path(top) if top else None


LOCATION_VARIABLES: tuple[str, ...] = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_GRAFT_FILE",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_WORK_TREE",
)


@functools.lru_cache(maxsize=1)
def local_git_variables() -> tuple[str, ...]:
    """Return every environment variable that relocates or reconfigures Git.

    Git reports its own complete set; a hand-maintained list cannot track it.
    Discovery runs under the fallback-sanitized environment so it never
    inherits the overrides it is asked to report, and the fallback is unioned
    in so the removed set can only grow.
    """

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--local-env-vars"],
            capture_output=True,
            check=False,
            env={
                name: value
                for name, value in os.environ.items()
                if name not in LOCATION_VARIABLES
            },
        )
    except OSError:
        return LOCATION_VARIABLES
    if result.returncode != 0:
        return LOCATION_VARIABLES
    reported = tuple(
        name
        for name in result.stdout.decode("utf-8", "surrogateescape").split()
        if name
    )
    if not reported:
        return LOCATION_VARIABLES
    return tuple(sorted(set(reported) | set(LOCATION_VARIABLES)))


def _isolated_environment() -> dict[str, str]:
    """Return the environment without any Git repository relocation.

    ``GIT_DIR`` and its relatives override ``-C``, so an inherited value would
    make the guard inspect a different repository than the destination's.
    """

    return {
        name: value
        for name, value in os.environ.items()
        if name not in local_git_variables()
    }


def _enclosing_repository_roots(directory: Path) -> tuple[Path, ...]:
    """Return every repository root containing this directory.

    A bare repository and a ``--separate-git-dir`` metadata directory have no
    worktree and no ``.git`` path component, so the Git directory itself must be
    probed as well. Otherwise the easiest destination to corrupt stays open.
    """

    roots: list[Path] = []
    worktree = _enclosing_worktree(directory)
    if worktree is not None:
        roots.append(worktree)
    for flag in ("--absolute-git-dir", "--git-common-dir"):
        try:
            result = subprocess.run(
                ["git", "-C", str(directory), "rev-parse", flag],
                text=True,
                capture_output=True,
                check=False,
                env=_isolated_environment(),
            )
        except OSError as error:
            raise JournalError(
                f"cannot probe {directory} for a repository: {error}"
            ) from error
        if result.returncode != 0:
            if "not a git repository" not in result.stderr.lower():
                raise JournalError(
                    f"cannot probe {directory} for a repository: "
                    f"{result.stderr.strip()}"
                )
            continue
        reported = result.stdout.strip()
        if reported:
            roots.append((directory / reported).resolve())
    return tuple(roots)


def _reject_repository_destination(path: Path, repo_root: Path | None) -> None:
    """Refuse any destination inside a repository, with or without a hint.

    Omitting ``repo_root`` must not disable the guard: that would make the
    easiest call form the only unprotected one.
    """

    candidate = path if path.is_absolute() else (Path.cwd() / path)
    directory = candidate.parent
    resolved = directory.resolve() / candidate.name
    # A Git metadata directory is not a worktree, so ``rev-parse
    # --show-toplevel`` fails there. Treating that failure as "outside a
    # repository" would let the journal overwrite HEAD or config.
    if any(part == ".git" for part in resolved.parts):
        raise JournalError(f"journal destination is inside Git metadata: {path}")
    roots: list[Path] = []
    if repo_root is not None:
        roots.append(repo_root.resolve())
    probe = directory
    while not probe.is_dir() and probe != probe.parent:
        probe = probe.parent
    if probe.is_dir():
        roots.extend(root.resolve() for root in _enclosing_repository_roots(probe))
    for root in roots:
        if resolved == root or root in resolved.parents:
            raise JournalError(f"journal destination is inside the repository: {path}")


def atomic_replace(
    path: Path,
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> Path:
    """Validate then atomically replace one journal file. Returns the path.

    A failed validation writes nothing, so the previous journal survives. The
    replacement itself is a single ``os.replace`` of a fully written temporary
    file in the destination directory, so a reader never observes a partial
    payload.
    """

    problems = validate_payload(payload)
    if problems:
        raise JournalError(f"invalid journal payload: {'; '.join(problems)}")
    _reject_repository_destination(path, repo_root)
    directory = path.parent
    if not directory.is_dir():
        raise JournalError(f"journal directory does not exist: {directory}")
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    handle, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(directory)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path


def load(path: Path) -> dict[str, Any]:
    """Load one journal file, failing closed unless it validates.

    Validating on read as well as on write keeps the non-authority markers
    machine-checkable for a hand-edited, truncated, or older payload.
    """

    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise JournalError(f"cannot read journal {path}: {error}") from error
    try:
        parsed: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise JournalError(f"journal is not valid JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise JournalError("journal must be a JSON object")
    payload = dict(parsed)
    problems = validate_payload(payload)
    if problems:
        raise JournalError(f"invalid journal payload: {'; '.join(problems)}")
    return payload
