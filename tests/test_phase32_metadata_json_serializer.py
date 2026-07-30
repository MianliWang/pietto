from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import json
from collections.abc import Iterable, Mapping
from dataclasses import is_dataclass
from pathlib import Path
from typing import Callable, cast

import pytest

from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SemanticMetadataArtifact,
)
from pietto._metadata.serializer import (
    SemanticMetadataFailureStage,
    build_semantic_metadata_error_envelope,
    semantic_metadata_artifact_to_json_dict,
)
from pietto.ast_nodes import Node, Script
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import FieldId, ScriptIR, SymbolId, build_ir
from pietto.ir.model import DefinitionIR, ExpressionIR
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, SemanticResult, analyze

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
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    created_at: Timestamp nullable\n"
    'source orders: Order is postgres.table("slice6_secret_orders")\n'
    "relationship order_link:\n"
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
    "        known_amounts = count(amount)\n"
    "        statuses = count_distinct(lower(trim(status)))\n"
    "        total = sum(amount + tax)\n"
    "        weighted = avg(score * weight)\n"
    "        first_seen = min(created_at)\n"
    "        last_seen = max(created_at)\n"
    "    satisfying:\n"
    "        total > 0\n"
    "    order by:\n"
    "        total desc\n"
    "        status asc\n"
    "    limit 5\n"
    "query report:\n"
    "    from stats\n"
    "    select:\n"
    "        status\n"
    "        total\n"
)

FAILURE_MESSAGES = {
    "parse": "Semantic Metadata Artifact v1 metadata is unavailable because parsing failed.",
    "semantic": "Semantic Metadata Artifact v1 metadata is unavailable because semantic analysis failed.",
    "ir": "Semantic Metadata Artifact v1 metadata is unavailable because IR construction failed.",
}


def test_success_envelope_serializes_with_artifact_v1_key_order() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path=Path("metadata/slice6.pietto"))

    document = semantic_metadata_artifact_to_json_dict(artifact)

    assert tuple(document) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    assert document["artifact"] == SEMANTIC_METADATA_ARTIFACT_NAME
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is True
    assert document["path"] == "metadata/slice6.pietto"
    assert document["diagnostics"] == []
    assert "error" not in document
    assert "metadata" in document


def test_metadata_payload_and_nested_objects_are_json_compatible_and_ordered() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path="json-compatible.pietto")

    document = semantic_metadata_artifact_to_json_dict(artifact)
    metadata = cast(dict[str, object], document["metadata"])
    sources = cast(list[dict[str, object]], metadata["sources"])
    source_schema = cast(dict[str, object], sources[0]["schema"])
    source_fields = cast(list[dict[str, object]], source_schema["fields"])
    first_location = cast(dict[str, object], source_fields[0]["location"])

    assert tuple(metadata) == ("source", "definitions", "sources", "relations", "types")
    assert isinstance(metadata["definitions"], list)
    assert isinstance(metadata["sources"], list)
    assert isinstance(metadata["relations"], list)
    assert isinstance(metadata["types"], list)
    assert tuple(first_location) == (
        "path",
        "line",
        "column",
        "end_line",
        "end_column",
    )
    assert json.loads(json.dumps(document, ensure_ascii=True)) == document


def test_type_schema_relation_query_aggregate_and_lineage_shapes_match_contract() -> (
    None
):
    artifact, _, _, _ = _artifact(SOURCE)

    document = semantic_metadata_artifact_to_json_dict(artifact)
    metadata = cast(dict[str, object], document["metadata"])
    sources = cast(list[dict[str, object]], metadata["sources"])
    source_schema = cast(dict[str, object], sources[0]["schema"])
    source_fields = cast(list[dict[str, object]], source_schema["fields"])
    field_type = cast(dict[str, object], source_fields[0]["type"])
    relations = cast(list[dict[str, object]], metadata["relations"])
    stats = next(relation for relation in relations if relation["name"] == "stats")
    query = cast(dict[str, object], stats["query"])
    order_by = cast(list[dict[str, object]], query["order_by"])
    limit = cast(dict[str, object], query["limit"])
    projections = cast(list[dict[str, object]], stats["projections"])
    aggregates = cast(list[dict[str, object]], stats["aggregates"])
    total = next(
        aggregate for aggregate in aggregates if aggregate["projection_name"] == "total"
    )
    total_arguments = cast(list[dict[str, object]], total["arguments"])
    lineage = cast(list[dict[str, object]], stats["lineage"])

    assert tuple(field_type) == (
        "status",
        "name",
        "kind",
        "canonical_name",
        "canonical_kind",
        "nullability",
        "support_posture",
    )
    assert tuple(stats) == (
        "name",
        "kind",
        "input",
        "input_schema",
        "output_schema",
        "projections",
        "query",
        "aggregates",
        "lineage",
        "location",
    )
    assert tuple(query) == ("where", "group_keys", "satisfying", "order_by", "limit")
    assert cast(dict[str, object], query["where"]) == {"present": True}
    assert cast(dict[str, object], query["satisfying"]) == {"present": True}
    assert tuple(order_by[0]) == (
        "scope",
        "direction",
        "expression_kind",
        "field_leaves",
    )
    assert "location" not in order_by[0]
    assert tuple(limit) == ("value",)
    assert "location" not in limit
    assert tuple(projections[0]) == (
        "name",
        "expression_kind",
        "type",
        "field_leaves",
        "location",
    )
    assert tuple(total) == (
        "function",
        "arguments",
        "result_type",
        "projection_name",
        "location",
    )
    assert tuple(total_arguments[0]) == ("expression_kind", "type", "field_leaves")
    assert "location" not in total_arguments[0]
    assert tuple(lineage[0]) == ("output", "field_leaves")

    group_keys = cast(list[dict[str, object]], query["group_keys"])
    assert _leaf_signature(group_keys) == [("orders", "status", [])]
    total_leaves = cast(list[dict[str, object]], total_arguments[0]["field_leaves"])
    assert _leaf_signature(total_leaves) == [
        ("orders", "amount", []),
        ("orders", "tax", []),
    ]


def test_success_diagnostics_use_existing_cli_json_v1_shape() -> None:
    first = _diagnostic("PIE-W1000", "first warning", path=None)
    second = _diagnostic("PIE-W1001", "second warning", path="warning.pietto")
    artifact, _, _, _ = _artifact(
        SOURCE,
        path=Path("diagnostics/slice6.pietto"),
        diagnostics=(first, second),
    )

    document = semantic_metadata_artifact_to_json_dict(artifact)

    assert document["diagnostics"] == [
        cli_json.diagnostic_to_json_dict(first, fallback_path=artifact.path),
        cli_json.diagnostic_to_json_dict(second, fallback_path=artifact.path),
    ]


@pytest.mark.parametrize("stage", ["parse", "semantic", "ir"])
def test_failure_envelope_is_fail_closed_for_parse_semantic_and_ir_stages(
    stage: str,
) -> None:
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="syntax error",
        location=SourceLocation(path=None, line=1, column=1),
    )

    document = build_semantic_metadata_error_envelope(
        path=Path("bad.pietto"),
        stage=cast(SemanticMetadataFailureStage, stage),
        diagnostics=(diagnostic,),
        message=FAILURE_MESSAGES[stage],
    )

    assert tuple(document) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "error",
    )
    assert document["ok"] is False
    assert document["path"] == "bad.pietto"
    assert "metadata" not in document
    assert document["diagnostics"] == [
        cli_json.diagnostic_to_json_dict(diagnostic, fallback_path="bad.pietto")
    ]
    error = cast(dict[str, object], document["error"])
    assert tuple(error) == ("stage", "message")
    assert error == {"stage": stage, "message": FAILURE_MESSAGES[stage]}

    forbidden = {
        "metadata",
        "definitions",
        "sources",
        "relations",
        "schemas",
        "fields",
        "projections",
        "aggregates",
        "lineage",
        "types",
    }
    assert forbidden.isdisjoint(_keys(document))


def test_failure_envelope_rejects_unsupported_internal_stage() -> None:
    with pytest.raises(ValueError, match="Unsupported Semantic Metadata Artifact v1"):
        build_semantic_metadata_error_envelope(
            path="bad.pietto",
            stage=cast(SemanticMetadataFailureStage, "lexical"),
            message="metadata unavailable",
        )


def test_serializer_output_exposes_no_raw_private_or_runtime_objects() -> None:
    artifact, _, semantic_result, _ = _artifact(SOURCE)
    document = semantic_metadata_artifact_to_json_dict(artifact)

    assert semantic_result.model.relationships != ()
    _assert_no_raw_objects(document)

    strings = _strings(document)
    assert "slice6_secret_orders" not in strings
    assert "postgres.table" not in strings
    assert "order_link" not in strings

    forbidden_keys = {
        "connector",
        "connectors",
        "secret",
        "secrets",
        "relationship",
        "relationships",
        "join",
        "joins",
        "runtime",
        "database",
        "project",
        "workspace",
        "multi_file",
        "symbol",
        "field_id",
        "ast",
        "ir",
    }
    assert forbidden_keys.isdisjoint(_keys(document))


def test_existing_cli_json_v1_outputs_remain_unchanged() -> None:
    check_result = cli_json.check_result_to_json_dict(path="input.pietto")
    emit_result = cli_json.emit_sql_result_to_json_dict(
        path="input.pietto",
        dialect="postgres",
    )

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
    assert "error" not in check_result

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
    assert "error" not in emit_result


def test_slice6_status_docs_record_private_serializer_completion_only() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 32 Slice 6 JSON Serializer And Fail-closed Error Envelope is complete",
            "Slice 6 adds private Artifact v1 JSON-compatible serializer and fail-closed diagnostics/error-only envelope coverage",
            "Phase 32 as a whole is not complete",
            "no `pietto explain` CLI behavior was implemented",
            "no text renderer",
            "no public API",
            "no JSON v1 mutation",
            "no SQL behavior",
            "no semantic behavior change",
            "no IR behavior change",
            "no grammar",
            "generated",
            "fixture",
            "golden",
            "example",
            "package",
            "dependency",
            "workflow",
            "version",
            "release",
            "tag",
            "publish",
            "upload",
            "signing",
            "attestation behavior changed",
        ):
            assert required in status, f"{path}: missing {required!r}"


def _artifact(
    source: str,
    *,
    path: str | Path | None = "slice6.pietto",
    diagnostics: tuple[Diagnostic, ...] = (),
) -> tuple[SemanticMetadataArtifact, Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None

    return (
        build_semantic_metadata_artifact(
            path=path,
            script=parse_result.ast,
            semantic_result=semantic_result,
            ir=ir_result.ir,
            diagnostics=(
                parse_result.diagnostics
                + semantic_result.diagnostics
                + ir_result.diagnostics
                + diagnostics
            ),
        ),
        parse_result.ast,
        semantic_result,
        ir_result.ir,
    )


def _diagnostic(code: str, message: str, *, path: str | None) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.WARNING,
        message=message,
        location=SourceLocation(path=path, line=2, column=3),
    )


def _leaf_signature(
    leaves: Iterable[dict[str, object]],
) -> list[tuple[object, object, object]]:
    return [(leaf["relation"], leaf["field"], leaf["qualifier"]) for leaf in leaves]


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _keys(value: object) -> set[str]:
    keys: set[str] = set()

    def collect(item: object) -> None:
        if isinstance(item, Mapping):
            keys.update(str(key) for key in item)

    _walk(value, collect)
    return keys


def _strings(value: object) -> set[str]:
    values: set[str] = set()
    _walk(value, lambda item: values.add(item) if isinstance(item, str) else None)
    return values


def _assert_no_raw_objects(value: object) -> None:
    _walk(value, _assert_not_raw_object)


def _assert_not_raw_object(value: object) -> None:
    assert not is_dataclass(value)
    assert not isinstance(value, Node)
    assert not isinstance(value, SemanticModel)
    assert not isinstance(value, (DefinitionIR, ExpressionIR, SymbolId, FieldId))


def _walk(value: object, visitor: Callable[[object], None]) -> None:
    visitor(value)
    if isinstance(value, Mapping):
        for key, item in value.items():
            _walk(key, visitor)
            _walk(item, visitor)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            _walk(item, visitor)
