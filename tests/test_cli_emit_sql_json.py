from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import IrResult
from pietto.parser_api import parse_source
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
RELATION = (
    SOURCE + "table active_users:\n"
    "    from users\n"
    "    where active == true\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)
_EMIT_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "dialect",
    "diagnostics",
    "cli_errors",
    "artifacts",
    "output",
}


def test_emit_sql_json_valid_file_returns_one_document(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "active_users.pie", RELATION)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)
    assert set(result) == _EMIT_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert "version" not in result
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "active_users",
            "sql": (
                "SELECT\n"
                '    "id" AS "id",\n'
                '    "email" AS "email"\n'
                'FROM "users"\n'
                'WHERE "active" = TRUE'
            ),
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}


def test_emit_sql_json_equals_form_preserves_artifact_order(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "relations.pie",
        SOURCE + "table first:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query second:\n"
        "    from first\n"
        "    select:\n"
        "        email\n",
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 0
    )

    result = _read_json_document(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert [artifact["name"] for artifact in artifacts] == ["first", "second"]


def test_emit_sql_json_warning_is_successful_and_preserved(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pie",
        "shape User:\n"
        "    email: Text\n"
        'source users: User is postgres.table("users")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )

    assert _emit_json(path) == 0
    result = _read_json_document(capsys)

    assert result["ok"] is True
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["severity"] for diagnostic in diagnostics] == ["warning"]
    assert cast(list[object], result["artifacts"])


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        ("parser.pie", "shape User {\n", "PIE-P1005"),
        (
            "semantic.pie",
            "shape User:\n    email: MissingType not null\n",
            "PIE-S2002",
        ),
    ],
)
def test_emit_sql_json_frontend_errors_return_one(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert _emit_json(path) == 1
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert expected_code in [
        diagnostic["code"]
        for diagnostic in cast(list[dict[str, object]], result["diagnostics"])
    ]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []


def test_emit_sql_json_ir_error_stops_before_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "ir-error.pie", SOURCE)
    diagnostic = _diagnostic(path, "PIE-I1000", "missing semantic fact")
    monkeypatch.setattr(
        cli.ir_api,
        "build_ir",
        lambda script, model: IrResult(ir=None, diagnostics=(diagnostic,)),
    )

    def unexpected_emit(script_ir: object) -> object:
        del script_ir
        raise AssertionError("SQL backend must not run after IR errors")

    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_emit)

    assert _emit_json(path) == 1
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert cast(list[dict[str, object]], result["diagnostics"])[0]["code"] == (
        "PIE-I1000"
    )
    assert result["artifacts"] == []


def test_emit_sql_json_preserves_backend_artifacts_with_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "mixed-result.pie", SOURCE)
    diagnostic = _diagnostic(path, "PIE-B1000", "one relation unsupported")
    artifacts = (
        _artifact("first", "SELECT 1"),
        _artifact("second", "SELECT 2"),
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=artifacts,
            diagnostics=(diagnostic,),
        ),
    )

    assert _emit_json(path) == 1
    result = _read_json_document(capsys)

    assert result["ok"] is False
    serialized = cast(list[dict[str, object]], result["artifacts"])
    assert [artifact["name"] for artifact in serialized] == ["first", "second"]
    assert cast(list[dict[str, object]], result["diagnostics"])[0]["code"] == (
        "PIE-B1000"
    )


def test_emit_sql_json_missing_file_returns_file_read_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pie"

    assert _emit_json(path) == 2
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["diagnostics"] == []
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert error["kind"] == "file_read"
    assert error["path"] == str(path)


def test_emit_sql_json_unsupported_dialect_is_structured_and_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pie", SOURCE)

    def unexpected_parse(checked_path: Path) -> object:
        del checked_path
        raise AssertionError("unsupported dialect must stop before parsing")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_parse)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "mysql",
                "--format=json",
            ]
        )
        == 2
    )
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["path"] == str(path)
    assert result["dialect"] == "mysql"
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert error["kind"] == "unsupported_dialect"
    assert error["path"] is None


@pytest.mark.parametrize(
    ("arguments", "expected_path", "expected_dialect"),
    [
        (["emit-sql", "--format=json"], None, None),
        (["emit-sql", "input.pie", "--format", "json"], "input.pie", None),
        (
            [
                "emit-sql",
                "input.pie",
                "--dialect",
                "postgres",
                "--unknown",
                "--format=json",
            ],
            None,
            None,
        ),
    ],
)
def test_emit_sql_json_usage_errors_are_structured(
    arguments: list[str],
    expected_path: str | None,
    expected_dialect: str | None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(arguments) == 2
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["path"] == expected_path
    assert result["dialect"] == expected_dialect
    assert result["diagnostics"] == []
    assert result["artifacts"] == []
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == ("usage")


def test_emit_sql_invalid_format_remains_plain_argparse_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pie", SOURCE)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "yaml",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'yaml'" in captured.err


def test_emit_sql_text_modes_and_output_remain_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "active_users.pie", RELATION)
    expected = (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    default = capsys.readouterr()
    assert default.out == expected
    assert default.err == ""

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "text",
            ]
        )
        == 0
    )
    explicit = capsys.readouterr()
    assert explicit.out == expected
    assert explicit.err == ""

    output = tmp_path / "out.sql"
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "text",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    written = capsys.readouterr()
    assert written.out == ""
    assert written.err == ""
    assert output.read_text(encoding="utf-8") == expected


def test_emit_sql_json_uses_raw_fields_and_json_encoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unsafe = 'line\nquote"slash\\esc\x1bnul\x00del\x7funicode雪'
    path_text = str(tmp_path / unsafe)
    parse_result = parse_source(SOURCE)
    assert parse_result.ast is not None
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message=unsafe,
        location=SourceLocation(path=None, line=1, column=1),
    )
    artifact = _artifact(unsafe, f"SELECT '{unsafe}'")
    monkeypatch.setattr(cli.parser_api, "parse_file", lambda path: parse_result)
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert _emit_json(Path(path_text)) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)

    assert "\x1b" not in captured.out
    assert "\x00" not in captured.out
    assert "\x7f" not in captured.out
    assert "雪" not in captured.out
    assert result["path"] == path_text
    serialized_diagnostic = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert serialized_diagnostic["message"] == unsafe
    assert serialized_diagnostic["message"] != cli._escape_cli_text(unsafe)
    location = cast(dict[str, object], serialized_diagnostic["location"])
    assert location["path"] == path_text
    serialized_artifact = cast(list[dict[str, object]], result["artifacts"])[0]
    assert serialized_artifact["name"] == unsafe
    assert serialized_artifact["sql"] == artifact.sql


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        (
            "huge-integer.pie",
            "type Huge = Int(max = " + "9" * 5000 + ") not null\n",
            "PIE-P1000",
        ),
        (
            "deep-parser.pie",
            "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n",
            "PIE-P1000",
        ),
        (
            "deep-semantic.pie",
            "".join(
                [
                    *(
                        f"type Alias{index} = Alias{index + 1} not null\n"
                        for index in range(1399)
                    ),
                    "type Alias1399 = Int not null\n",
                ]
            ),
            "PIE-S2006",
        ),
    ],
)
def test_emit_sql_json_containment_failures_have_no_traceback(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert _emit_json(path) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)

    assert "Traceback" not in captured.out
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert diagnostics[0]["code"] == expected_code


def test_emit_sql_json_parser_error_stops_all_later_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "parser-error.pie", "shape User {\n")
    _forbid_later_stages(monkeypatch, include_semantic=True)

    assert _emit_json(path) == 1
    assert _read_json_document(capsys)["ok"] is False


def test_emit_sql_json_semantic_error_stops_ir_and_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic-error.pie",
        "shape User:\n    email: MissingType not null\n",
    )
    _forbid_later_stages(monkeypatch, include_semantic=False)

    assert _emit_json(path) == 1
    assert _read_json_document(capsys)["ok"] is False


def _emit_json(path: Path) -> int:
    return cli.main(
        [
            "emit-sql",
            str(path),
            "--dialect",
            "postgres",
            "--format=json",
        ]
    )


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    return _parse_json_document(captured.out, captured.err)


def _parse_json_document(stdout: str, stderr: str) -> dict[str, object]:
    assert stderr == ""
    assert stdout.startswith("{")
    assert stdout.endswith("}\n")
    assert not stdout.endswith("\n\n")
    result = json.loads(stdout)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


def _forbid_later_stages(
    monkeypatch: pytest.MonkeyPatch,
    *,
    include_semantic: bool,
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("failed stage must stop later compiler stages")

    if include_semantic:
        monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)


def _diagnostic(path: Path, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(path=str(path), line=1, column=1),
    )


def _artifact(name: str, sql: str) -> SqlArtifact:
    return SqlArtifact(
        name=name,
        kind=SqlArtifactKind.RELATION,
        sql=sql,
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
