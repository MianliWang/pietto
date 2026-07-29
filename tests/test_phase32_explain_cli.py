from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import IrResult

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs/spec/pietto-v0.9.md",
)

SOURCE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    created_at: Timestamp nullable\n"
    'source orders: Order is postgres.table("slice7_secret_orders")\n'
    "relationship hidden_order_link:\n"
    "    endpoint left: orders\n"
    "    endpoint right: orders\n"
    "table stats:\n"
    "    from orders\n"
    "    where created_at is not null\n"
    "    group by:\n"
    "        status\n"
    "    select:\n"
    "        status\n"
    "        rows = count()\n"
    "        total = sum(amount + tax)\n"
    "    satisfying:\n"
    "        total > 0\n"
    "    order by:\n"
    "        total desc\n"
    "    limit 5\n"
    "query report:\n"
    "    from stats\n"
    "    select:\n"
    "        status\n"
    "        total\n"
)


def test_explain_defaults_to_text_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "orders.pietto", SOURCE)

    assert cli.main(["explain", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Semantic Metadata Artifact v1\n" in captured.out
    assert "schema_version: 1\n" in captured.out
    assert f"path: {path}\n" in captured.out
    assert "summary: definitions=4 sources=1 relations=2" in captured.out
    assert "sources:\n  - orders\n    fields:" in captured.out
    assert "relations:\n  - stats (table)" in captured.out
    assert "input: orders (source)" in captured.out
    assert "query: where=yes group_keys=orders.status satisfying=yes" in captured.out
    assert "aggregates:" in captured.out
    assert "total = sum(bounded_expression:orders.amount, orders.tax)" in captured.out
    assert "lineage:" in captured.out
    assert "total <- orders.amount, orders.tax" in captured.out
    assert "slice7_secret_orders" not in captured.out
    assert "hidden_order_link" not in captured.out


def test_explain_json_success_emits_artifact_v1_envelope(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "orders.pietto", SOURCE)

    assert cli.main(["explain", str(path), "--format", "json"]) == 0

    captured = capsys.readouterr()
    document = _json(captured.out, captured.err)
    assert tuple(document) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is True
    assert document["path"] == str(path)
    assert document["diagnostics"] == []
    assert "metadata" in document
    assert "error" not in document

    metadata = cast(dict[str, object], document["metadata"])
    assert tuple(metadata) == ("source", "definitions", "sources", "relations", "types")
    assert "slice7_secret_orders" not in captured.out
    assert "hidden_order_link" not in captured.out


def test_explain_json_parse_failure_is_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "syntax.pietto", "shape User {\n")

    assert cli.main(["explain", str(path), "--format", "json"]) == 1

    document = _json(capsys.readouterr().out, "")
    assert document["ok"] is False
    assert "metadata" not in document
    error = cast(dict[str, object], document["error"])
    assert error["stage"] == "parse"
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics
    assert diagnostics[0]["code"] == "PIE-P1000"


def test_explain_json_semantic_failure_is_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic.pietto",
        "shape User:\n    email: MissingType not null\n",
    )

    assert cli.main(["explain", str(path), "--format", "json"]) == 1

    document = _json(capsys.readouterr().out, "")
    assert document["ok"] is False
    assert "metadata" not in document
    error = cast(dict[str, object], document["error"])
    assert error["stage"] == "semantic"
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2002"]


def test_explain_json_ir_failure_is_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "orders.pietto", SOURCE)
    diagnostic = Diagnostic(
        code="PIE-I1000",
        severity=Severity.ERROR,
        message="forced IR failure",
        location=SourceLocation(path=None, line=1, column=1),
    )

    def fail_ir(*args: object, **kwargs: object) -> IrResult:
        del args, kwargs
        return IrResult(ir=None, diagnostics=(diagnostic,))

    monkeypatch.setattr(cli.ir_api, "build_ir", fail_ir)

    assert cli.main(["explain", str(path), "--format", "json"]) == 1

    document = _json(capsys.readouterr().out, "")
    assert document["ok"] is False
    assert "metadata" not in document
    error = cast(dict[str, object], document["error"])
    assert error["stage"] == "ir"
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [item["code"] for item in diagnostics] == ["PIE-I1000"]


def test_explain_json_file_read_error_returns_two_without_fake_diagnostic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pietto"

    assert cli.main(["explain", str(path), "--format", "json"]) == 2

    document = _json(capsys.readouterr().out, "")
    assert document["ok"] is False
    assert "metadata" not in document
    assert document["diagnostics"] == []
    error = cast(dict[str, object], document["error"])
    assert error["stage"] == "parse"
    assert "could not be read or decoded" in str(error["message"])


@pytest.mark.parametrize(
    "arguments",
    [
        ["explain", "input.pietto", "--dialect", "postgres"],
        ["explain", "input.pietto", "--output", "out.txt"],
    ],
)
def test_explain_rejects_sql_flags(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(arguments) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unrecognized arguments:" in captured.err


def test_existing_cli_json_v1_outputs_remain_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_path = _write(tmp_path, "check.pietto", "shape User:\n    email: Text\n")
    emit_path = _write(
        tmp_path,
        "emit.pietto",
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is postgres.table("users")\n'
        "table emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )

    assert cli.main(["check", str(check_path), "--format", "json"]) == 0
    check_result = _json(capsys.readouterr().out, "")
    assert tuple(check_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert check_result["schema_version"] == 1
    assert check_result["command"] == "check"
    assert "artifact" not in check_result
    assert "metadata" not in check_result

    assert (
        cli.main(
            [
                "emit-sql",
                str(emit_path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_result = _json(capsys.readouterr().out, "")
    assert tuple(emit_result) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    )
    assert emit_result["schema_version"] == 1
    assert emit_result["command"] == "emit-sql"
    assert "artifact" not in emit_result
    assert "metadata" not in emit_result


def test_explain_does_not_call_sql_emitters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "orders.pietto", SOURCE)

    def unexpected_sql_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("explain must not call SQL emitters")

    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_sql_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_sql_call)

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    captured = capsys.readouterr()
    assert "SELECT" not in captured.out
    assert captured.err == ""


def test_cli_help_includes_explain_and_existing_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--help"]) == 0

    captured = capsys.readouterr()
    assert "check" in captured.out
    assert "emit-sql" in captured.out
    assert "explain" in captured.out
    assert captured.err == ""


def test_slice7_status_docs_record_explain_integration_only() -> None:
    for path in STATUS_DOCS:
        status = " ".join(path.read_text(encoding="utf-8").split())
        for required in (
            "Phase 32 Slice 7 Explain CLI Text/JSON Integration, Docs, Examples, And Package Smoke Readiness is complete",
            "Slice 7 adds `pietto explain` CLI text/JSON integration using private Artifact v1 metadata",
            "Phase 32 as a whole is not complete",
            "Slice 8 remains completion audit/status lock",
            "no package version bump",
            "tag",
            "release",
            "publish",
            "upload",
            "signing",
            "attestation",
            "no SQL execution",
            "database",
            "runtime behavior",
            "changes no parser, semantic, IR, or SQL behavior except CLI orchestration over existing facts",
        ):
            assert required in status, f"{path}: missing {required!r}"


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _json(stdout: str, stderr: str) -> dict[str, object]:
    assert stdout.endswith("\n")
    assert not stdout.endswith("\n\n")
    assert stderr == ""
    return cast(dict[str, object], json.loads(stdout))
