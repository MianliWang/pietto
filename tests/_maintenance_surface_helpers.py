from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import cast

EXPECTED_RUNTIME_DEPENDENCY_NAMES = ("antlr4-python3-runtime",)
EXPECTED_DEV_DEPENDENCY_NAMES = (
    "mypy",
    "pyright",
    "pytest",
    "pytest-cov",
    "pytest-xdist",
    "ruff",
)
EXPECTED_BUILD_REQUIREMENT_NAMES = ("uv_build",)
EXPECTED_WORKFLOW_ACTIONS = (
    "actions/checkout",
    "actions/setup-python",
    "actions/setup-java",
    "astral-sh/setup-uv",
)
EXPECTED_PYTHON_MATRIX = ("3.12", "3.13")
EXPECTED_DIRECT_CI_COMMANDS = (
    "uv sync --locked",
    "uv run python scripts/validate.py",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
)


def assert_dependency_maintenance_surface(repo_root: Path) -> None:
    assert_pyproject_maintenance_surface(repo_root)
    assert_uv_lock_maintenance_surface(repo_root)


def assert_pyproject_maintenance_surface(repo_root: Path) -> None:
    pyproject = _load_toml(repo_root / "pyproject.toml")
    project = _table(pyproject, "project")
    build_system = _table(pyproject, "build-system")
    dependency_groups = _table(pyproject, "dependency-groups")

    assert project["name"] == "pietto"
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.12"
    assert _table(project, "scripts") == {"pietto": "pietto.cli:main"}
    assert build_system["build-backend"] == "uv_build"
    assert (
        _dependency_names(_string_list(build_system["requires"]))
        == EXPECTED_BUILD_REQUIREMENT_NAMES
    )
    assert (
        _dependency_names(_string_list(project["dependencies"]))
        == EXPECTED_RUNTIME_DEPENDENCY_NAMES
    )
    assert tuple(sorted(dependency_groups)) == ("dev",)
    assert (
        _dependency_names(_string_list(dependency_groups["dev"]))
        == EXPECTED_DEV_DEPENDENCY_NAMES
    )


def assert_uv_lock_maintenance_surface(repo_root: Path) -> None:
    uv_lock_path = repo_root / "uv.lock"
    assert uv_lock_path.is_file()
    uv_lock = _load_toml(uv_lock_path)

    assert uv_lock["requires-python"] == ">=3.12"
    packages = _package_tables(uv_lock)
    root_package = _find_package(packages, "pietto")
    assert root_package["version"] == "0.1.0"
    assert _table(root_package, "source") == {"editable": "."}
    assert (
        _dependency_names(_package_dependency_entries(root_package["dependencies"]))
        == EXPECTED_RUNTIME_DEPENDENCY_NAMES
    )
    assert (
        _dependency_names(
            _package_dependency_entries(_table(root_package, "dev-dependencies")["dev"])
        )
        == EXPECTED_DEV_DEPENDENCY_NAMES
    )
    assert (
        _dependency_names(
            _package_dependency_entries(
                _table(root_package, "metadata")["requires-dist"]
            )
        )
        == EXPECTED_RUNTIME_DEPENDENCY_NAMES
    )
    assert (
        _dependency_names(
            _package_dependency_entries(
                _table(_table(root_package, "metadata"), "requires-dev")["dev"]
            )
        )
        == EXPECTED_DEV_DEPENDENCY_NAMES
    )
    assert "sqlglot" not in {str(package.get("name", "")) for package in packages}


def assert_workflow_maintenance_surface(repo_root: Path) -> None:
    workflow_path = repo_root / ".github" / "workflows" / "ci.yml"
    dependabot_path = repo_root / ".github" / "dependabot.yml"
    alternate_dependabot_path = repo_root / ".github" / "dependabot.yaml"

    assert workflow_path.is_file()
    assert dependabot_path.is_file()
    assert not alternate_dependabot_path.exists()
    assert _tracked_github_files(repo_root) == (
        ".github/dependabot.yml",
        ".github/workflows/ci.yml",
    )
    assert _tracked_workflow_files(repo_root) == (".github/workflows/ci.yml",)

    workflow = workflow_path.read_text(encoding="utf-8")
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == list(
        EXPECTED_PYTHON_MATRIX
    )
    assert _workflow_action_identities(workflow) == EXPECTED_WORKFLOW_ACTIONS
    assert not re.search(
        r"(?m)^\s*uses:\s+\S+@(main|master|HEAD|latest|v[0-9][^\s#]*)\s*(#.*)?$",
        workflow,
    )
    assert _direct_run_commands(workflow) == EXPECTED_DIRECT_CI_COMMANDS
    for required in (
        'echo "UV_PROJECT_ENVIRONMENT=$RUNNER_TEMP/pietto-venv" >> "$GITHUB_ENV"',
        'echo "UV_CACHE_DIR=$RUNNER_TEMP/uv-cache" >> "$GITHUB_ENV"',
        "persist-credentials: false",
        'version: "0.11.19"',
        "enable-cache: false",
    ):
        assert required in workflow
    lowered = workflow.lower()
    for forbidden in (
        "contents: write",
        "write-all",
        "pull-requests:",
        "id-token:",
        "secrets.",
        "pypi",
        "twine",
        "publish",
        "deploy",
        "upload-artifact",
        "attest",
        "sigstore",
    ):
        assert forbidden not in lowered


def _load_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _table(mapping: dict[str, object], key: str) -> dict[str, object]:
    value = mapping[key]
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def _string_list(value: object) -> tuple[str, ...]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return tuple(cast(list[str], value))


def _package_tables(uv_lock: dict[str, object]) -> tuple[dict[str, object], ...]:
    packages = uv_lock["package"]
    assert isinstance(packages, list)
    assert all(isinstance(package, dict) for package in packages)
    return tuple(cast(list[dict[str, object]], packages))


def _find_package(
    packages: tuple[dict[str, object], ...], package_name: str
) -> dict[str, object]:
    matches = tuple(
        package for package in packages if package.get("name") == package_name
    )
    assert len(matches) == 1
    return matches[0]


def _dependency_names(requirements: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted(_dependency_name(requirement) for requirement in requirements))


def _dependency_name(requirement: str) -> str:
    match = re.match(r"^[A-Za-z0-9_.-]+", requirement)
    assert match is not None
    return match.group(0)


def _package_dependency_entries(value: object) -> tuple[str, ...]:
    assert isinstance(value, list)
    names: list[str] = []
    for item in value:
        assert isinstance(item, dict)
        name = item.get("name")
        assert isinstance(name, str)
        names.append(name)
    return tuple(names)


def _workflow_action_identities(workflow: str) -> tuple[str, ...]:
    uses = re.findall(
        r"(?m)^        uses: ([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)@"
        r"([0-9a-f]{40}) # v[0-9][0-9.]*$",
        workflow,
    )
    assert len(uses) == len(EXPECTED_WORKFLOW_ACTIONS)
    return tuple(repository for repository, _sha in uses)


def _direct_run_commands(workflow: str) -> tuple[str, ...]:
    return tuple(
        command
        for command in re.findall(r"(?m)^        run: (.+)$", workflow)
        if command != "|"
    )


def _tracked_github_files(repo_root: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.relative_to(repo_root).as_posix()
            for path in (repo_root / ".github").rglob("*")
            if path.is_file()
        )
    )


def _tracked_workflow_files(repo_root: Path) -> tuple[str, ...]:
    workflow_root = repo_root / ".github" / "workflows"
    return tuple(
        sorted(
            path.relative_to(repo_root).as_posix()
            for path in workflow_root.iterdir()
            if path.is_file()
        )
    )
