from __future__ import annotations

from pathlib import Path

from _maintenance_surface_helpers import (
    assert_dependency_maintenance_surface,
    assert_pyproject_maintenance_surface,
    assert_uv_lock_maintenance_surface,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_dependency_surface_is_semantically_locked() -> None:
    assert_pyproject_maintenance_surface(REPO_ROOT)


def test_uv_lock_surface_is_semantically_locked_without_byte_locking() -> None:
    assert_uv_lock_maintenance_surface(REPO_ROOT)


def test_dependency_maintenance_surface_accepts_version_churn_only() -> None:
    assert_dependency_maintenance_surface(REPO_ROOT)
