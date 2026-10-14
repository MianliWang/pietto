from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli


SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")

SUPPORTED_RELATION = (
    "query enriched_orders:\n"
    "    from orders\n"
    "    let:\n"
    "        gross = amount + tax\n"
    "    where gross > 0\n"
    "    select:\n"
    "        gross_value = gross\n"
    "    order by:\n"
    "        gross\n"
)

CHECK_JSON_KEYS = (
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
)
EMIT_JSON_KEYS = (
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
EXPLAIN_JSON_KEYS = (
    "artifact",
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "metadata",
)
METADATA_KEYS = ("source", "definitions", "sources", "relations", "types")


def test_supported_let_check_text_and_json_preserve_cli_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "supported.pietto", SUPPORTED_RELATION)

    assert cli.main(["check", str(path)]) == 0
    text_output = capsys.readouterr()
    assert text_output.err == ""
    assert text_output.out == f"OK: {path}\n"

    assert cli.main(["check", str(path), "--format", "json"]) == 0
    document = _read_json(capsys)
    assert tuple(document) == CHECK_JSON_KEYS
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["ok"] is True
    assert document["path"] == str(path)
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert "let_scopes" not in json.dumps(document)


@pytest.mark.parametrize(
    ("dialect", "prefix", "forbidden_ref", "expected_where", "expected_alias"),
    [
        (
            "postgres",
            SOURCE_PREFIX,
            '"gross"',
            '("amount" + "tax") > 0',
            '"amount" + "tax" AS "gross_value"',
        ),
        (
            "mysql",
            MYSQL_SOURCE_PREFIX,
            "`gross`",
            "(`amount` + `tax`) > 0",
            "`amount` + `tax` AS `gross_value`",
        ),
    ],
)
def test_supported_let_emit_sql_text_inlines_without_hidden_layers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    prefix: str,
    forbidden_ref: str,
    expected_where: str,
    expected_alias: str,
) -> None:
    path = _write_source(tmp_path, f"{dialect}.pietto", SUPPORTED_RELATION, prefix)

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0
    captured = capsys.readouterr()

    assert captured.err == ""
    assert forbidden_ref not in captured.out
    assert expected_where in captured.out
    assert expected_alias in captured.out
    assert "WITH " not in captured.out.upper()
    assert "FROM (SELECT" not in captured.out.upper()


@pytest.mark.parametrize(
    ("dialect", "prefix", "forbidden_ref"),
    [
        ("postgres", SOURCE_PREFIX, '"gross"'),
        ("mysql", MYSQL_SOURCE_PREFIX, "`gross`"),
    ],
)
def test_supported_let_emit_sql_json_preserves_schema_and_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    prefix: str,
    forbidden_ref: str,
) -> None:
    path = _write_source(tmp_path, f"{dialect}.pietto", SUPPORTED_RELATION, prefix)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )
    document = _read_json(capsys)

    assert tuple(document) == EMIT_JSON_KEYS
    assert document["schema_version"] == 1
    assert document["command"] == "emit-sql"
    assert document["ok"] is True
    assert document["dialect"] == dialect
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["output"] is None
    artifacts = cast(list[dict[str, object]], document["artifacts"])
    assert len(artifacts) == 1
    assert artifacts[0]["kind"] == "relation"
    assert artifacts[0]["name"] == "enriched_orders"
    sql = cast(str, artifacts[0]["sql"])
    assert forbidden_ref not in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()
    assert "let_scopes" not in json.dumps(document)


def test_supported_let_emit_sql_output_writes_only_inline_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "supported.pietto", SUPPORTED_RELATION)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    sql = output.read_text(encoding="utf-8")

    assert captured.out == ""
    assert captured.err == ""
    assert '"gross"' not in sql
    assert '("amount" + "tax") > 0' in sql
    assert '"amount" + "tax" AS "gross_value"' in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        smallest = min(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        net = orders.gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        gross = amount - tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = gross + tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
    ],
)
def test_unsupported_let_emit_sql_json_and_output_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected_code: str,
) -> None:
    path = _write_source(tmp_path, "unsupported.pietto", "query bad:\n" + body)
    missing_output = tmp_path / "missing.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(missing_output),
            ]
        )
        == 1
    )
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["ok"] is False
    assert document["artifacts"] == []
    assert document["output"] == {"path": str(missing_output), "written": False}
    assert expected_code in [diagnostic["code"] for diagnostic in diagnostics]
    assert not missing_output.exists()

    existing_output = _write_text(tmp_path, "existing.sql", "original SQL\n")
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(existing_output),
            ]
        )
        == 1
    )
    text_failure = capsys.readouterr()
    assert expected_code in text_failure.err
    assert existing_output.read_text(encoding="utf-8") == "original SQL\n"


def test_supported_let_explain_text_and_json_preserve_artifact_v1(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "supported.pietto", SUPPORTED_RELATION)

    assert cli.main(["explain", str(path)]) == 0
    text_output = capsys.readouterr()
    assert text_output.err == ""
    assert "Semantic Metadata Artifact v1\n" in text_output.out
    assert "schema_version: 1\n" in text_output.out
    assert "let_scopes" not in text_output.out

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    document = _read_json(capsys)
    assert tuple(document) == EXPLAIN_JSON_KEYS
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is True
    assert document["diagnostics"] == []
    metadata = cast(dict[str, object], document["metadata"])
    assert tuple(metadata) == METADATA_KEYS
    assert "let_scopes" not in json.dumps(document)


def test_unsupported_let_explain_json_fails_without_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "unsupported.pietto",
        "query bad:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        smallest = min(gross)\n",
    )

    assert cli.main(["explain", str(path), "--format", "json"]) == 1
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["ok"] is False
    assert "metadata" not in document
    assert cast(dict[str, object], document["error"])["stage"] == "semantic"
    assert "PIE-S2102" in [diagnostic["code"] for diagnostic in diagnostics]
    assert "let_scopes" not in json.dumps(document)


def test_non_let_cli_json_metadata_shape_remains_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "plain.pietto",
        "query plain_orders:\n    from orders\n    select:\n        amount\n",
    )

    assert cli.main(["check", str(path), "--format=json"]) == 0
    check_document = _read_json(capsys)
    assert tuple(check_document) == CHECK_JSON_KEYS

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
    emit_document = _read_json(capsys)
    assert tuple(emit_document) == EMIT_JSON_KEYS

    assert cli.main(["explain", str(path), "--format=json"]) == 0
    explain_document = _read_json(capsys)
    assert tuple(explain_document) == EXPLAIN_JSON_KEYS
    assert tuple(cast(dict[str, object], explain_document["metadata"])) == (
        METADATA_KEYS
    )


def _write_source(
    tmp_path: Path,
    filename: str,
    relation_source: str,
    prefix: str = SOURCE_PREFIX,
) -> Path:
    return _write_text(tmp_path, filename, prefix + relation_source)


def _write_text(tmp_path: Path, filename: str, content: str) -> Path:
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))
