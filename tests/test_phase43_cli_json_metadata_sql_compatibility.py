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
    "    discount: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")

COMBINED_APPROVED_RELATION = (
    "query phase43_report:\n"
    "    from orders\n"
    "    let:\n"
    "        gross = amount + tax\n"
    "        weighted = score * weight\n"
    "        normalized = lower(trim(status))\n"
    "        key = orders.status\n"
    "    group by:\n"
    "        key\n"
    "    select:\n"
    "        status_label = orders.status\n"
    "        total_amounts = sum(gross)\n"
    "        average_score = avg(weighted)\n"
    "        known_rows = count(gross)\n"
    "        unique_labels = count_distinct(normalized)\n"
    "    satisfying:\n"
    "        sum(gross) > 10 and count(gross) > 0\n"
    "    order by:\n"
    "        key desc\n"
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

PUBLIC_FORBIDDEN_STRINGS = (
    "let_scopes",
    "LetBindingIR",
    "RelationLayerIR",
    '"precision"',
    '"scale"',
)


def test_combined_phase43_check_json_and_explain_shapes_remain_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "combined.pietto", COMBINED_APPROVED_RELATION)

    assert cli.main(["check", str(path)]) == 0
    check_text = capsys.readouterr()
    assert check_text.err == ""
    assert check_text.out == f"OK: {path}\n"

    assert cli.main(["check", str(path), "--format", "json"]) == 0
    check_document = _read_json(capsys)
    assert tuple(check_document) == CHECK_JSON_KEYS
    assert check_document["schema_version"] == 1
    assert check_document["command"] == "check"
    assert check_document["ok"] is True
    assert check_document["path"] == str(path)
    assert check_document["diagnostics"] == []
    assert check_document["cli_errors"] == []
    _assert_no_public_let_or_precision_surface(check_document)

    assert cli.main(["explain", str(path)]) == 0
    explain_text = capsys.readouterr()
    assert explain_text.err == ""
    assert "Semantic Metadata Artifact v1\n" in explain_text.out
    assert "schema_version: 1\n" in explain_text.out
    assert "let_scopes" not in explain_text.out
    assert "LetBindingIR" not in explain_text.out
    assert "RelationLayerIR" not in explain_text.out

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    explain_document = _read_json(capsys)
    assert tuple(explain_document) == EXPLAIN_JSON_KEYS
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert explain_document["ok"] is True
    assert explain_document["diagnostics"] == []
    metadata = cast(dict[str, object], explain_document["metadata"])
    assert tuple(metadata) == METADATA_KEYS
    _assert_no_public_let_or_precision_surface(explain_document)


@pytest.mark.parametrize(
    ("dialect", "prefix", "expected_fragments", "forbidden_identifiers"),
    [
        (
            "postgres",
            SOURCE_PREFIX,
            (
                'SUM(("amount" + "tax")) AS "total_amounts"',
                'AVG(("score" * "weight")) AS "average_score"',
                'COUNT(("amount" + "tax")) AS "known_rows"',
                'COUNT(DISTINCT lower(trim("status"))) AS "unique_labels"',
                'GROUP BY\n    "orders"."status"',
                "HAVING",
                'SUM(("amount" + "tax")) > 10',
                'COUNT(("amount" + "tax")) > 0',
                'ORDER BY\n    "orders"."status" DESC',
            ),
            ('"gross"', '"weighted"', '"normalized"', '"key"'),
        ),
        (
            "mysql",
            MYSQL_SOURCE_PREFIX,
            (
                "SUM((`amount` + `tax`)) AS `total_amounts`",
                "AVG((`score` * `weight`)) AS `average_score`",
                "COUNT((`amount` + `tax`)) AS `known_rows`",
                "COUNT(DISTINCT LOWER(TRIM(`status`))) AS `unique_labels`",
                "GROUP BY\n    `orders`.`status`",
                "HAVING",
                "SUM((`amount` + `tax`)) > 10",
                "COUNT((`amount` + `tax`)) > 0",
                "ORDER BY\n    `orders`.`status` DESC",
            ),
            ("`gross`", "`weighted`", "`normalized`", "`key`"),
        ),
    ],
)
def test_combined_phase43_emit_sql_text_and_json_inline_expansion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    prefix: str,
    expected_fragments: tuple[str, ...],
    forbidden_identifiers: tuple[str, ...],
) -> None:
    path = _write_source(
        tmp_path,
        f"{dialect}.pietto",
        COMBINED_APPROVED_RELATION,
        prefix,
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0
    text_output = capsys.readouterr()
    assert text_output.err == ""
    _assert_sql_compatibility(
        text_output.out,
        expected_fragments=expected_fragments,
        forbidden_identifiers=forbidden_identifiers,
    )

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
    emit_document = _read_json(capsys)
    assert tuple(emit_document) == EMIT_JSON_KEYS
    assert emit_document["schema_version"] == 1
    assert emit_document["command"] == "emit-sql"
    assert emit_document["ok"] is True
    assert emit_document["dialect"] == dialect
    assert emit_document["diagnostics"] == []
    assert emit_document["cli_errors"] == []
    assert emit_document["output"] is None
    artifacts = cast(list[dict[str, object]], emit_document["artifacts"])
    assert len(artifacts) == 1
    assert artifacts[0]["kind"] == "relation"
    assert artifacts[0]["name"] == "phase43_report"
    _assert_sql_compatibility(
        cast(str, artifacts[0]["sql"]),
        expected_fragments=expected_fragments,
        forbidden_identifiers=forbidden_identifiers,
    )
    _assert_no_public_let_or_precision_surface(emit_document)


def test_emit_sql_output_writes_only_expanded_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "combined.pietto", COMBINED_APPROVED_RELATION)
    output = tmp_path / "phase43.sql"

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
    _assert_sql_compatibility(
        sql,
        expected_fragments=(
            'SUM(("amount" + "tax")) AS "total_amounts"',
            'AVG(("score" * "weight")) AS "average_score"',
            'COUNT(("amount" + "tax")) AS "known_rows"',
            'COUNT(DISTINCT lower(trim("status"))) AS "unique_labels"',
            'GROUP BY\n    "orders"."status"',
            "HAVING",
            'SUM(("amount" + "tax")) > 10',
            'COUNT(("amount" + "tax")) > 0',
            'ORDER BY\n    "orders"."status" DESC',
        ),
        forbidden_identifiers=('"gross"', '"weighted"', '"normalized"', '"key"'),
    )


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(gross)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
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
            "    select:\n"
            "        total = sum(orders.gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        total = sum(gross)\n",
            "PIE-S2102",
        ),
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
            "    select:\n"
            "        largest = max(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        one = 1\n"
            "    select:\n"
            "        total = sum(one)\n",
            "PIE-S2315",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        one = 1\n"
            "    group by:\n"
            "        one\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
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
            "        total = count()\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    satisfying:\n"
            "        sum(gross) > 10\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(gross)\n"
            "    satisfying:\n"
            "        sum(amount + tax) > 10\n",
            "PIE-S2308",
        ),
    ],
)
def test_forbidden_phase43_let_contexts_fail_closed_in_check_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected_code: str,
) -> None:
    path = _write_source(tmp_path, "forbidden.pietto", "query forbidden:\n" + body)

    assert cli.main(["check", str(path), "--format", "json"]) == 1
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert tuple(document) == CHECK_JSON_KEYS
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["ok"] is False
    assert document["cli_errors"] == []
    assert expected_code in [diagnostic["code"] for diagnostic in diagnostics]
    _assert_no_public_let_or_precision_surface(document)


def test_failed_emit_sql_json_output_does_not_write_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "bad_emit.pietto",
        "query bad_emit:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        smallest = min(gross)\n",
    )
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

    assert tuple(document) == EMIT_JSON_KEYS
    assert document["ok"] is False
    assert document["artifacts"] == []
    assert document["output"] == {"path": str(missing_output), "written": False}
    assert "PIE-S2102" in [diagnostic["code"] for diagnostic in diagnostics]
    assert not missing_output.exists()
    _assert_no_public_let_or_precision_surface(document)


def test_failed_explain_json_keeps_artifact_error_envelope_without_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "bad_explain.pietto",
        "query bad_explain:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    satisfying:\n"
        "        sum(gross) > 10\n",
    )

    assert cli.main(["explain", str(path), "--format", "json"]) == 1
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is False
    assert "metadata" not in document
    assert cast(dict[str, object], document["error"])["stage"] == "semantic"
    assert "PIE-S2308" in [diagnostic["code"] for diagnostic in diagnostics]
    _assert_no_public_let_or_precision_surface(document)


@pytest.mark.parametrize(
    ("predicate", "expected_fragment"),
    [
        ("avg(weighted) > 1.5", 'HAVING\n    AVG(("score" * "weight")) > 1.5'),
        ("count(gross) > 0", 'HAVING\n    COUNT(("amount" + "tax")) > 0'),
        (
            "count_distinct(normalized) > 1",
            'HAVING\n    COUNT(DISTINCT lower(trim("status"))) > 1',
        ),
    ],
)
def test_postgres_having_sql_covers_all_aggregate_let_families(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    predicate: str,
    expected_fragment: str,
) -> None:
    path = _write_source(
        tmp_path,
        "having_family.pietto",
        COMBINED_APPROVED_RELATION.replace(
            "sum(gross) > 10 and count(gross) > 0",
            predicate,
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    captured = capsys.readouterr()

    assert captured.err == ""
    assert expected_fragment in captured.out
    for identifier in ('"gross"', '"weighted"', '"normalized"', '"key"'):
        assert identifier not in captured.out
    assert "WITH " not in captured.out.upper()
    assert "FROM (SELECT" not in captured.out.upper()


def _write_source(
    tmp_path: Path,
    filename: str,
    relation_source: str,
    prefix: str = SOURCE_PREFIX,
) -> Path:
    path = tmp_path / filename
    path.write_text(prefix + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _assert_sql_compatibility(
    sql: str,
    *,
    expected_fragments: tuple[str, ...],
    forbidden_identifiers: tuple[str, ...],
) -> None:
    for fragment in expected_fragments:
        assert fragment in sql
    for identifier in forbidden_identifiers:
        assert identifier not in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()


def _assert_no_public_let_or_precision_surface(document: dict[str, object]) -> None:
    serialized = json.dumps(document, sort_keys=True)
    for forbidden in PUBLIC_FORBIDDEN_STRINGS:
        assert forbidden not in serialized
