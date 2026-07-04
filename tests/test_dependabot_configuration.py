from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / ".github/dependabot.yml"
ALTERNATE_CONFIG_PATH = REPO_ROOT / ".github/dependabot.yaml"

EXPECTED_CONFIG = """version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
      timezone: "America/Toronto"
    open-pull-requests-limit: 1

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:30"
      timezone: "America/Toronto"
    open-pull-requests-limit: 1
"""

FORBIDDEN_LOW_NOISE_KEYS = (
    "registries",
    "groups",
    "assignees",
    "reviewers",
    "milestone",
    "target-branch",
    "labels",
)


def _read_config() -> str:
    return CONFIG_PATH.read_text(encoding="utf-8")


def test_dependabot_config_uses_single_canonical_file() -> None:
    assert CONFIG_PATH.is_file()
    assert not ALTERNATE_CONFIG_PATH.exists()


def test_dependabot_config_is_exact_low_noise_maintenance_shape() -> None:
    assert _read_config() == EXPECTED_CONFIG


def test_dependabot_config_tracks_only_uv_and_github_actions() -> None:
    config = _read_config()

    assert config.count('package-ecosystem: "uv"') == 1
    assert config.count('package-ecosystem: "github-actions"') == 1
    assert config.count("package-ecosystem:") == 2
    assert config.count('directory: "/"') == 2
    assert config.count('interval: "weekly"') == 2
    assert config.count('day: "monday"') == 2
    assert config.count('timezone: "America/Toronto"') == 2
    assert config.count("open-pull-requests-limit: 1") == 2


def test_dependabot_config_omits_unapproved_noise_controls() -> None:
    config = _read_config()

    for key in FORBIDDEN_LOW_NOISE_KEYS:
        assert f"{key}:" not in config
