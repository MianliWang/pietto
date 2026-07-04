from __future__ import annotations

from pathlib import Path

from _maintenance_surface_helpers import assert_workflow_maintenance_surface

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_workflow_and_github_maintenance_surface_is_semantically_locked() -> None:
    assert_workflow_maintenance_surface(REPO_ROOT)
