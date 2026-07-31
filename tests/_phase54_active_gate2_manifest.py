"""Compatibility exports for the stable active Gate 2 manifest authority."""

from __future__ import annotations

import subprocess

from _active_gate2_manifest import (
    ActiveGate2RepositoryState as Phase54Gate2RepositoryState,
    _matches_active_gate2_manifest as _matches_phase54_active_gate2_manifest,
    _read_active_gate2_repository_state,
)
from _active_gate2_manifest_data import (
    ACTIVE_GATE2_ADDED_PATHS as PHASE54_ACTIVE_GATE2_ADDED_PATHS,
    ACTIVE_GATE2_BASE as PHASE54_ACTIVE_GATE2_BASE,
    ACTIVE_GATE2_DELETED_PATHS as PHASE54_ACTIVE_GATE2_DELETED_PATHS,
    ACTIVE_GATE2_MARKER as PHASE54_ACTIVE_GATE2_MARKER,
    ACTIVE_GATE2_MODIFIED_PATHS as PHASE54_ACTIVE_GATE2_MODIFIED_PATHS,
    ADDED_PATHS,
    ALLOWLIST_PATHS,
    MECHANICAL_READER_PATHS,
    MODIFIED_PATHS,
    NON_READER_MODIFIED_PATHS,
)

__all__ = [
    "ADDED_PATHS",
    "ALLOWLIST_PATHS",
    "MECHANICAL_READER_PATHS",
    "MODIFIED_PATHS",
    "NON_READER_MODIFIED_PATHS",
    "PHASE54_ACTIVE_GATE2_ADDED_PATHS",
    "PHASE54_ACTIVE_GATE2_BASE",
    "PHASE54_ACTIVE_GATE2_DELETED_PATHS",
    "PHASE54_ACTIVE_GATE2_MARKER",
    "PHASE54_ACTIVE_GATE2_MODIFIED_PATHS",
    "Phase54Gate2RepositoryState",
    "_matches_phase54_active_gate2_manifest",
    "_read_phase54_gate2_repository_state",
    "phase54_active_gate2_manifest_is_active",
]


def _read_phase54_gate2_repository_state() -> Phase54Gate2RepositoryState:
    """Compatibility seam retained for existing fail-closed tests."""

    return _read_active_gate2_repository_state()


def phase54_active_gate2_manifest_is_active() -> bool:
    """Delegate through the stable exact matcher without ambient activation."""

    try:
        state = _read_phase54_gate2_repository_state()
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    return _matches_phase54_active_gate2_manifest(state)
