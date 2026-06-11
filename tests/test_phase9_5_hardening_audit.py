from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE_SUFFIX = ".pietto"
FORMER_SOURCE_SUFFIX = "." + "p" + "i" + "e"
TEXT_SUFFIXES = {
    ".g4",
    ".json",
    ".md",
    ".pietto",
    ".py",
    ".toml",
    ".txt",
}


def test_pyright_gate_targets_handwritten_production_source() -> None:
    config_text = _read("pyrightconfig.json")
    config = json.loads(re.sub(r",(\s*[}\]])", r"\1", config_text))

    assert config == {
        "include": ["src/pietto"],
        "exclude": ["src/pietto/generated"],
        "ignore": ["src/pietto/generated"],
        "extraPaths": ["src"],
        "venvPath": ".",
        "venv": ".venv",
        "pythonVersion": "3.12",
        "typeCheckingMode": "standard",
    }
    assert "tests" not in config["include"]


def test_pylance_ignores_only_generated_antlr_diagnostics() -> None:
    settings = json.loads(_read(".vscode/settings.json"))

    assert settings == {
        "python.analysis.exclude": ["src/pietto/generated/**"],
        "python.analysis.ignore": ["src/pietto/generated/**"],
    }
    assert "python.analysis.typeCheckingMode" not in settings
    assert "python.analysis.diagnosticSeverityOverrides" not in settings


def test_official_examples_and_source_fixtures_use_pietto_suffix() -> None:
    examples = tuple(
        path for path in (REPO_ROOT / "examples").rglob("*") if path.is_file()
    )
    postgres_fixtures = tuple(
        path
        for path in (REPO_ROOT / "tests" / "fixtures" / "postgres").rglob("*")
        if path.is_file()
    )

    assert len(examples) == 10
    assert len(postgres_fixtures) == 3
    assert all(path.suffix == OFFICIAL_SOURCE_SUFFIX for path in examples)
    assert all(path.suffix == OFFICIAL_SOURCE_SUFFIX for path in postgres_fixtures)


def test_repository_contains_no_former_source_suffix() -> None:
    legacy_paths = tuple(
        path.relative_to(REPO_ROOT)
        for path in REPO_ROOT.rglob(f"*{FORMER_SOURCE_SUFFIX}")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )
    assert legacy_paths == ()

    legacy_reference = re.compile(re.escape(FORMER_SOURCE_SUFFIX) + r"(?=\b|\")")
    matches: list[Path] = []
    roots = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / ".vscode",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "pyrightconfig.json",
        REPO_ROOT / "docs",
        REPO_ROOT / "examples",
        REPO_ROOT / "grammar",
        REPO_ROOT / "src",
        REPO_ROOT / "tests",
    )
    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if (
                not path.is_file()
                or "__pycache__" in path.parts
                or path.suffix not in TEXT_SUFFIXES
            ):
                continue
            if legacy_reference.search(path.read_text(encoding="utf-8")):
                matches.append(path.relative_to(REPO_ROOT))
    assert matches == []


def test_current_user_facing_commands_use_pietto_suffix() -> None:
    readme = _read("README.md")
    agents = _read("AGENTS.md")
    language_spec = _read("docs/spec/pietto-v0.9.md")

    assert "pietto check file.pietto" in readme
    assert "pietto emit-sql file.pietto --dialect postgres" in readme
    assert "pietto check file.pietto" in agents
    assert "pietto emit-sql file.pietto --dialect postgres" in agents
    assert "pietto check app.pietto" in language_spec


def test_cli_remains_path_based_for_nonstandard_suffix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "source.txt"
    path.write_text(
        """
shape User:
    id: Int not null

source users: User is postgres.table("users")

table all_users:
    from users
    select:
        id
""".lstrip(),
        encoding="utf-8",
    )

    assert cli.main(["check", str(path)]) == 0
    checked = capsys.readouterr()
    assert checked.out == f"OK: {path}\n"
    assert checked.err == ""

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    emitted = capsys.readouterr()
    assert emitted.err == ""
    assert emitted.out == 'SELECT\n    "id" AS "id"\nFROM "users"\n'


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (None, 0),
        (0, 0),
        (2, 2),
        ("message", 1),
    ],
)
def test_system_exit_codes_are_normalized(code: object, expected: int) -> None:
    assert cli._system_exit_code(SystemExit(code)) == expected


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
