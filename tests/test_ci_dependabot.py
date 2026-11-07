from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / ".github/dependabot.yml"
ALTERNATE_CONFIG_PATH = REPO_ROOT / ".github/dependabot.yaml"

EXPECTED_CONFIG = """version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "daily"
      time: "09:00"
      timezone: "America/Toronto"
    open-pull-requests-limit: 5
    groups:
      python-tooling:
        applies-to: version-updates
        patterns:
          - "ruff"
          - "pyright"
          - "pytest"
          - "pytest-cov"
          - "pytest-xdist"
        update-types:
          - "minor"
          - "patch"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "daily"
      time: "09:30"
      timezone: "America/Toronto"
    open-pull-requests-limit: 5
    groups:
      routine-actions:
        applies-to: version-updates
        patterns:
          - "*"
        update-types:
          - "minor"
          - "patch"
"""

FORBIDDEN_LOW_NOISE_KEYS = (
    "registries",
    "automerge",
    "auto-merge",
    "assignees",
    "reviewers",
    "milestone",
    "target-branch",
    "labels",
)

FORBIDDEN_POLICY_SURFACE_REFERENCES = (
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
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
    assert config.count('interval: "daily"') == 2
    assert 'interval: "weekly"' not in config
    assert "day:" not in config
    assert config.count('timezone: "America/Toronto"') == 2
    assert config.count("open-pull-requests-limit: 5") == 2
    assert "open-pull-requests-limit: 1" not in config


def test_dependabot_config_omits_unapproved_noise_controls() -> None:
    config = _read_config()

    for key in FORBIDDEN_LOW_NOISE_KEYS:
        assert f"{key}:" not in config


def test_dependabot_policy_does_not_reference_other_update_surfaces() -> None:
    config = _read_config()

    for reference in FORBIDDEN_POLICY_SURFACE_REFERENCES:
        assert reference not in config


def test_groups_match_only_approved_version_updates() -> None:
    config = _read_config()
    tooling = config.split("      python-tooling:\n", 1)[1].split(
        "  - package-ecosystem:", 1
    )[0]
    actions = config.split("      routine-actions:\n", 1)[1]
    patterns = re.findall(
        r'          - "([^"]+)"', tooling.split("        update-types:", 1)[0]
    )
    assert patterns == ["ruff", "pyright", "pytest", "pytest-cov", "pytest-xdist"]
    for package in patterns:
        assert any(fnmatchcase(package, pattern) for pattern in patterns)
    for package in (
        "psycopg",
        "psycopg-binary",
        "mysql-connector-python",
        "antlr4-python3-runtime",
        "uv-build",
        "coverage",
    ):
        assert not any(fnmatchcase(package, pattern) for pattern in patterns)
    for group in (tooling, actions):
        assert "applies-to: version-updates" in group
        assert re.findall(
            r'          - "([^"]+)"', group.split("        update-types:", 1)[1]
        ) == ["minor", "patch"]
        assert "dependency-type:" not in group
        assert '"major"' not in group
    assert 'patterns:\n          - "*"' in actions
    assert fnmatchcase("actions/checkout", "*")
    assert fnmatchcase("astral-sh/setup-uv", "*")
    for forbidden in (
        "ignore:",
        "allow:",
        "security-updates",
        "insecure-external-code-execution",
    ):
        assert forbidden not in config
