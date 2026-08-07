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

import json
import os
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
    if version is not None and (not isinstance(version, int) or version < 1):
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


def _reject_repository_destination(path: Path, repo_root: Path | None) -> None:
    if repo_root is None:
        return
    resolved_root = repo_root.resolve()
    candidate = path if path.is_absolute() else (Path.cwd() / path)
    resolved = candidate.parent.resolve() / candidate.name
    if resolved == resolved_root or resolved_root in resolved.parents:
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
    """Load one journal file and fail closed when it is not a valid object."""

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
    return dict(parsed)
