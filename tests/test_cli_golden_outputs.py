from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"


@pytest.mark.parametrize(
    ("example", "fixture"),
    [
        ("examples/basic/types.pie", "check_types.json"),
        (
            "examples/sources/users.pie",
            "check_sources_users_warning.json",
        ),
    ],
)
def test_check_json_matches_structural_golden(
    example: str,
    fixture: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", example, "--format", "json"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == _load_json(fixture)


@pytest.mark.parametrize(
    ("example", "fixture"),
    [
        (
            "examples/tables/active_users.pie",
            "emit_sql_active_users.sql",
        ),
        (
            "examples/queries/active_user_emails.pie",
            "emit_sql_active_user_emails.sql",
        ),
        (
            "tests/fixtures/postgres/compatibility_literals_identifiers.pie",
            "emit_sql_compatibility_literals_identifiers.sql",
        ),
        (
            "tests/fixtures/postgres/compatibility_expressions.pie",
            "emit_sql_compatibility_expressions.sql",
        ),
        (
            "tests/fixtures/postgres/compatibility_ordering_metadata.pie",
            "emit_sql_compatibility_ordering_metadata.sql",
        ),
    ],
)
def test_emit_sql_matches_byte_exact_golden(
    example: str,
    fixture: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", example, "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == (GOLDEN_ROOT / fixture).read_bytes()


def test_emit_sql_json_matches_structural_golden(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                "examples/tables/active_users.pie",
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == _load_json("emit_sql_active_users.json")


def _load_json(name: str) -> object:
    """Load one manually reviewed JSON golden fixture."""

    return json.loads((GOLDEN_ROOT / name).read_text(encoding="utf-8"))
