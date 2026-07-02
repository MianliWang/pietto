from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import SemanticMetadataType
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto.ast_nodes import Script, ShapeDef, TypeExpr
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.semantic.model import DecimalPrecisionScale

VALID_SOURCE = (
    "type Money = Decimal(12, 2) not null\n"
    "type Price = Money nullable\n"
    "shape Order:\n"
    "    amount: Decimal(12, 2) not null\n"
    "    money: Money not null\n"
    "    price: Price nullable\n"
    "    plain: Decimal not null\n"
    "    empty: Decimal() nullable\n"
    "    label: Text(max = 255) not null\n"
    'source orders: Order is postgres.table("orders")\n'
    "table report:\n"
    "    from orders\n"
    "    select:\n"
    "        amount\n"
    "        money\n"
    "        price\n"
    "        plain\n"
    "        empty\n"
)
INVALID_SOURCE = "shape Order:\n    amount: Decimal(0, 0) not null\n"

_TYPE_KEYS = {
    "status",
    "name",
    "kind",
    "canonical_name",
    "canonical_kind",
    "nullability",
    "support_posture",
}
_DIAGNOSTIC_KEYS = {
    "code",
    "severity",
    "message",
    "location",
    "suggestion",
}
_SQL_FORBIDDEN_TOKENS = ("DECIMAL(", "NUMERIC(", "precision", "scale")
_CARRIER_TOKENS = (
    "DecimalPrecisionScale",
    "decimal_precision_scales",
    "decimal_precision_scale_for",
)


def test_check_json_valid_decimal_precision_scale_keeps_json_v1_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("slice6_valid.pietto"), VALID_SOURCE)

    assert cli.main(["check", "slice6_valid.pietto", "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["ok"] is True
    assert document["path"] == "slice6_valid.pietto"
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    _assert_no_precision_scale_keys(document)
    _assert_no_carrier_tokens(json.dumps(document))


def test_emit_sql_json_and_output_keep_sql_unparameterized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("slice6_valid.pietto"), VALID_SOURCE)
    output_path = Path("slice6_out.sql")

    assert (
        cli.main(
            [
                "emit-sql",
                "slice6_valid.pietto",
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    document = _read_json_document(capsys)
    assert tuple(document) == (
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
    assert document["schema_version"] == 1
    assert document["command"] == "emit-sql"
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["output"] == {"path": str(output_path), "written": True}

    artifacts = cast(list[dict[str, object]], document["artifacts"])
    assert len(artifacts) == 1
    sql = cast(str, artifacts[0]["sql"])
    written_sql = output_path.read_text(encoding="utf-8")
    assert written_sql == f"{sql}\n"
    _assert_no_sql_precision_scale(sql)
    _assert_no_sql_precision_scale(written_sql)
    _assert_no_precision_scale_keys(document)
    _assert_no_carrier_tokens(json.dumps(document))


def test_explain_text_keeps_logical_decimal_and_alias_type_labels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("slice6_valid.pietto"), VALID_SOURCE)

    assert cli.main(["explain", "slice6_valid.pietto"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert "Semantic Metadata Artifact v1\n" in captured.out
    assert "amount: Decimal kind=builtin canonical=Decimal" in captured.out
    assert "money: Money kind=type_alias canonical=Decimal" in captured.out
    assert "price: Price kind=type_alias canonical=Decimal" in captured.out
    assert "plain: Decimal kind=builtin canonical=Decimal" in captured.out
    assert "empty: Decimal kind=builtin canonical=Decimal" in captured.out
    for forbidden in ("precision", "scale", *_CARRIER_TOKENS):
        assert forbidden not in captured.out


def test_explain_json_keeps_artifact_v1_logical_decimal_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("slice6_valid.pietto"), VALID_SOURCE)

    assert cli.main(["explain", "slice6_valid.pietto", "--format", "json"]) == 0

    document = _read_json_document(capsys)
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
    assert document["diagnostics"] == []

    metadata = cast(dict[str, object], document["metadata"])
    assert tuple(metadata) == ("source", "definitions", "sources", "relations", "types")
    _assert_no_precision_scale_keys(document)
    _assert_no_carrier_tokens(json.dumps(document))
    _assert_metadata_type_shapes_are_logical_decimal(metadata)


def test_semantic_metadata_artifact_json_does_not_serialize_internal_carrier() -> None:
    script, semantic_result, document = _metadata_json_from_source()

    amount_type = _shape_field_type_expr(script, "amount")
    money_type = _shape_field_type_expr(script, "money")
    price_type = _shape_field_type_expr(script, "price")
    assert semantic_result.model.decimal_precision_scale_for(
        amount_type
    ) == DecimalPrecisionScale(12, 2)
    assert semantic_result.model.decimal_precision_scale_for(
        money_type
    ) == DecimalPrecisionScale(12, 2)
    assert semantic_result.model.decimal_precision_scale_for(
        price_type
    ) == DecimalPrecisionScale(12, 2)
    assert semantic_result.model.decimal_precision_scales

    assert {"precision", "scale"}.isdisjoint(
        {field.name for field in fields(SemanticMetadataType)}
    )
    _assert_no_precision_scale_keys(document)
    serialized = json.dumps(document)
    _assert_no_carrier_tokens(serialized)
    _assert_metadata_type_shapes_are_logical_decimal(
        cast(dict[str, object], document["metadata"])
    )


def test_project_json_v2_remains_discovery_only_for_decimal_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("pietto.toml"), "")
    _write(Path("slice6_valid.pietto"), VALID_SOURCE)

    assert cli.main(["check", "--project", ".", "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    _assert_no_precision_scale_keys(document)
    _assert_no_carrier_tokens(json.dumps(document))


def test_invalid_decimal_precision_scale_check_json_keeps_diagnostic_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(Path("slice6_invalid.pietto"), INVALID_SOURCE)

    assert cli.main(["check", "slice6_invalid.pietto", "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["ok"] is False
    assert document["cli_errors"] == []

    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert set(diagnostic) == _DIAGNOSTIC_KEYS
    assert diagnostic["code"] == "PIE-S2004"
    assert diagnostic["severity"] == "error"
    assert "precision" in cast(str, diagnostic["message"])
    assert "scale" not in set(diagnostic)
    assert "precision" not in set(diagnostic)


def _write(path: Path, source: str) -> None:
    path.write_text(source, encoding="utf-8")


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert captured.out.endswith("}\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _metadata_json_from_source() -> tuple[Script, SemanticResult, dict[str, object]]:
    parse_result = parse_source(VALID_SOURCE, path="slice6_valid.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None

    artifact = build_semantic_metadata_artifact(
        path="slice6_valid.pietto",
        script=parse_result.ast,
        semantic_result=semantic_result,
        ir=ir_result.ir,
        diagnostics=(),
    )
    return (
        parse_result.ast,
        semantic_result,
        semantic_metadata_artifact_to_json_dict(artifact),
    )


def _shape_field_type_expr(script: Script, field_name: str) -> TypeExpr:
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef)
    )
    field = next(field for field in shape.fields if field.name == field_name)
    return field.type_expr


def _assert_metadata_type_shapes_are_logical_decimal(
    metadata: dict[str, object],
) -> None:
    types = cast(list[dict[str, object]], metadata["types"])
    for type_ref in types:
        assert set(type_ref) == _TYPE_KEYS

    assert any(
        type_ref["name"] == "Money"
        and type_ref["kind"] == "type_alias"
        and type_ref["canonical_name"] == "Decimal"
        and type_ref["canonical_kind"] == "builtin"
        for type_ref in types
    )
    assert any(
        type_ref["name"] == "Price"
        and type_ref["kind"] == "type_alias"
        and type_ref["canonical_name"] == "Decimal"
        and type_ref["canonical_kind"] == "builtin"
        for type_ref in types
    )
    assert any(
        type_ref["name"] == "Decimal"
        and type_ref["kind"] == "builtin"
        and type_ref["canonical_name"] == "Decimal"
        and type_ref["canonical_kind"] == "builtin"
        for type_ref in types
    )


def _assert_no_precision_scale_keys(value: object) -> None:
    if isinstance(value, dict):
        assert "precision" not in value
        assert "scale" not in value
        for child in value.values():
            _assert_no_precision_scale_keys(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_precision_scale_keys(child)


def _assert_no_sql_precision_scale(sql: str) -> None:
    for forbidden in _SQL_FORBIDDEN_TOKENS:
        assert forbidden not in sql, forbidden


def _assert_no_carrier_tokens(text: str) -> None:
    for forbidden in _CARRIER_TOKENS:
        assert forbidden not in text
