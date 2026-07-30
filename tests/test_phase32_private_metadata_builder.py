from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

from collections.abc import Iterable
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Callable

import pytest

import pietto
import pietto.ir
import pietto.semantic
from pietto import cli_json
from pietto._metadata import __all__ as metadata_exports
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SemanticMetadataArtifact,
    SemanticMetadataPayload,
)
from pietto.ast_nodes import Node, Script
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import FieldId, ScriptIR, SymbolId, build_ir
from pietto.ir.model import DefinitionIR, ExpressionIR
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticModel, SemanticResult, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs/spec/pietto-v0.9.md",
)

SOURCE = (
    "type EventId = UUID not null\n"
    "enum Status:\n"
    "    open\n"
    "    closed\n"
    "shape Event:\n"
    "    id: EventId not null\n"
    "    uuid_direct: UUID not null\n"
    "    status: Status nullable\n"
    "    status_text: Text nullable\n"
    "    amount: Decimal not null\n"
    "    tax: Decimal not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    created_on: Date nullable\n"
    "    created_at: Timestamp nullable\n"
    "    payload: Json nullable\n"
    "    blob: Bytes nullable\n"
    "    anything: Any nullable\n"
    'source events: Event is postgres.table("private_events")\n'
    "relationship event_link:\n"
    "    endpoint left: events\n"
    "    endpoint right: events\n"
    "table stats:\n"
    "    from events\n"
    "    where created_at is not null\n"
    "    group by:\n"
    "        status_text\n"
    "    select:\n"
    "        status_text\n"
    "        rows = count()\n"
    "        known_ids = count(id)\n"
    "        statuses = count_distinct(lower(trim(status_text)))\n"
    "        total = sum(amount + tax)\n"
    "        weighted = avg(score * weight)\n"
    "        first_created = min(created_at)\n"
    "        last_created = max(created_at)\n"
    "    satisfying:\n"
    "        rows > 0\n"
    "    order by:\n"
    "        rows desc\n"
    "        status_text asc\n"
    "    limit 5\n"
    "query report:\n"
    "    from stats\n"
    "    select:\n"
    "        status_text\n"
    "        rows\n"
)


def test_private_model_is_frozen_tuple_based_and_not_reexported() -> None:
    artifact, _, _, _ = _artifact(SOURCE)

    assert metadata_exports == ()
    for public_module in (pietto, pietto.semantic, pietto.ir):
        assert not hasattr(public_module, "SemanticMetadataArtifact")
        assert "SemanticMetadataArtifact" not in getattr(public_module, "__all__", ())

    assert is_dataclass(artifact)
    with pytest.raises(FrozenInstanceError):
        setattr(artifact, "ok", False)

    assert isinstance(artifact.metadata, SemanticMetadataPayload)
    assert isinstance(artifact.diagnostics, tuple)
    assert isinstance(artifact.metadata.definitions, tuple)
    assert isinstance(artifact.metadata.sources, tuple)
    assert isinstance(artifact.metadata.relations, tuple)
    assert isinstance(artifact.metadata.types, tuple)
    assert isinstance(artifact.metadata.sources[0].schema.fields, tuple)
    assert isinstance(artifact.metadata.relations[0].projections, tuple)
    assert isinstance(artifact.metadata.relations[0].query.order_by, tuple)
    assert isinstance(artifact.metadata.relations[0].aggregates[0].arguments, tuple)
    assert isinstance(artifact.metadata.relations[0].lineage, tuple)


def test_source_metadata_preserves_order_locations_and_path_posture() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path=Path("metadata/slice3.pietto"))

    assert artifact.artifact == SEMANTIC_METADATA_ARTIFACT_NAME
    assert artifact.schema_version == 1
    assert artifact.command == "explain"
    assert artifact.ok is True
    assert artifact.path == "metadata/slice3.pietto"
    assert artifact.metadata.source.path == "metadata/slice3.pietto"
    assert artifact.diagnostics == ()

    assert [(item.name, item.kind) for item in artifact.metadata.definitions] == [
        ("EventId", "type"),
        ("Status", "enum"),
        ("Event", "shape"),
        ("events", "source"),
        ("stats", "table"),
        ("report", "query"),
    ]
    assert artifact.metadata.definitions[0].location is not None
    assert artifact.metadata.definitions[0].location.path == "metadata/slice3.pietto"
    assert artifact.metadata.definitions[0].location.line == 1

    assert [source.name for source in artifact.metadata.sources] == ["events"]
    source = artifact.metadata.sources[0]
    assert [field.name for field in source.schema.fields] == [
        "id",
        "uuid_direct",
        "status",
        "status_text",
        "amount",
        "tax",
        "score",
        "weight",
        "created_on",
        "created_at",
        "payload",
        "blob",
        "anything",
    ]
    assert source.schema.fields[0].location is not None
    assert source.schema.fields[0].location.path == "metadata/slice3.pietto"


def test_connector_and_relationship_metadata_are_excluded() -> None:
    artifact, _, semantic_result, _ = _artifact(SOURCE)

    assert semantic_result.model.relationships != ()
    assert "event_link" not in _strings(artifact)
    assert "private_events" not in _strings(artifact)

    forbidden_field_names = {
        "connector",
        "config",
        "secret",
        "secrets",
        "relationship",
        "relationships",
        "dialect",
        "deferred",
        "symbol",
        "field_id",
        "node",
        "ir",
    }
    assert forbidden_field_names.isdisjoint(_field_names(artifact))


def test_table_query_and_query_posture_metadata_are_normalized() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    stats, report = artifact.metadata.relations

    assert (stats.name, stats.kind, stats.input.name, stats.input.kind) == (
        "stats",
        "table",
        "events",
        "source",
    )
    assert [field.name for field in stats.input_schema.fields[:3]] == [
        "id",
        "uuid_direct",
        "status",
    ]
    assert [field.name for field in stats.output_schema.fields] == [
        "status_text",
        "rows",
        "known_ids",
        "statuses",
        "total",
        "weighted",
        "first_created",
        "last_created",
    ]
    assert [projection.expression_kind for projection in stats.projections] == [
        "field_ref",
        "aggregate_call",
        "aggregate_call",
        "aggregate_call",
        "aggregate_call",
        "aggregate_call",
        "aggregate_call",
        "aggregate_call",
    ]
    assert stats.query.where.present is True
    assert [(leaf.relation, leaf.field) for leaf in stats.query.group_keys] == [
        ("events", "status_text")
    ]
    assert stats.query.satisfying.present is True
    assert [
        (item.scope, item.direction, item.expression_kind)
        for item in stats.query.order_by
    ] == [
        ("grouped_result", "DESC", "aggregate_call"),
        ("grouped_result", "ASC", "field_ref"),
    ]
    assert stats.query.limit is not None
    assert stats.query.limit.value == 5

    assert (report.name, report.kind, report.input.name, report.input.kind) == (
        "report",
        "query",
        "stats",
        "table",
    )
    assert report.query.where.present is False
    assert report.query.satisfying.present is False
    assert report.query.limit is None


def test_type_normalization_covers_current_postures_and_unknowns() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    source_types = {
        field.name: field.type for field in artifact.metadata.sources[0].schema.fields
    }

    assert source_types["id"].status == "known"
    assert source_types["id"].name == "EventId"
    assert source_types["id"].kind == "type_alias"
    assert source_types["id"].canonical_name == "UUID"
    assert source_types["id"].support_posture == "limited_frozen"
    assert source_types["uuid_direct"].support_posture == "limited_frozen"
    assert source_types["status"].kind == "enum"
    assert source_types["status"].support_posture == "metadata_only"
    assert source_types["payload"].support_posture == "deferred_builtin"
    assert source_types["blob"].support_posture == "deferred_builtin"
    assert source_types["anything"].support_posture == "current"
    assert source_types["amount"].canonical_name == "Decimal"
    assert source_types["created_on"].canonical_name == "Date"
    assert source_types["created_at"].canonical_name == "Timestamp"
    assert source_types["status"].nullability == "nullable"

    unknown_artifact, _, _, _ = _artifact(
        'source raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        missing\n",
        mode=CheckMode.LOOSE,
    )
    projected = unknown_artifact.metadata.relations[0]
    assert projected.output_schema.fields == ()
    assert projected.projections[0].type is not None
    assert projected.projections[0].type.status == "unknown"
    assert projected.projections[0].type.name is None
    assert projected.projections[0].type.nullability == "unknown"
    assert projected.projections[0].type.support_posture == "unknown"


def test_current_aggregate_metadata_and_basic_lineage_are_normalized() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    stats = artifact.metadata.relations[0]

    assert [
        (aggregate.function, aggregate.projection_name)
        for aggregate in stats.aggregates
    ] == [
        ("count", "rows"),
        ("count", "known_ids"),
        ("count_distinct", "statuses"),
        ("sum", "total"),
        ("avg", "weighted"),
        ("min", "first_created"),
        ("max", "last_created"),
    ]
    assert stats.aggregates[0].arguments == ()
    assert [argument.expression_kind for argument in stats.aggregates[1].arguments] == [
        "field_ref"
    ]
    assert [argument.expression_kind for argument in stats.aggregates[2].arguments] == [
        "call"
    ]
    assert [argument.expression_kind for argument in stats.aggregates[3].arguments] == [
        "bounded_expression"
    ]

    lineage = {item.output: item.field_leaves for item in stats.lineage}
    assert [(leaf.relation, leaf.field) for leaf in lineage["status_text"]] == [
        ("events", "status_text")
    ]
    assert [(leaf.relation, leaf.field) for leaf in lineage["total"]] == [
        ("events", "amount"),
        ("events", "tax"),
    ]
    assert [(leaf.relation, leaf.field) for leaf in lineage["statuses"]] == [
        ("events", "status_text")
    ]
    assert all(leaf.qualifier == () for leaves in lineage.values() for leaf in leaves)


def test_normalized_metadata_exposes_no_raw_ast_semantic_model_or_ir_nodes() -> None:
    artifact, _, _, _ = _artifact(SOURCE)

    _assert_no_raw_objects(artifact)


def test_error_diagnostics_fail_closed_before_constructing_metadata() -> None:
    _, script, semantic_result, ir = _artifact(SOURCE)
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="syntax error",
        location=SourceLocation(path="bad.pietto", line=1, column=1),
    )

    with pytest.raises(
        ValueError,
        match="requires successful diagnostics",
    ):
        build_semantic_metadata_artifact(
            path="bad.pietto",
            script=script,
            semantic_result=semantic_result,
            ir=ir,
            diagnostics=(diagnostic,),
        )

    failed_semantic_result = SemanticResult(
        model=semantic_result.model,
        diagnostics=(diagnostic,),
    )
    with pytest.raises(
        ValueError,
        match="requires successful diagnostics",
    ):
        build_semantic_metadata_artifact(
            path="bad.pietto",
            script=script,
            semantic_result=failed_semantic_result,
            ir=ir,
        )


def test_existing_cli_json_v1_helper_output_remains_unchanged() -> None:
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


def test_slice3_status_docs_record_private_builder_completion_only() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 32 Slice 3 Private Metadata Model And Builder MVP is complete",
            "Slice 3 adds only private metadata model/builder source, tests, status, and hash-lock updates",
            "Phase 32 as a whole is not complete",
            "No `pietto explain` CLI behavior",
            "JSON serializer",
            "text renderer",
            "public API",
            "JSON v1",
            "SQL",
            "semantic behavior",
            "IR behavior",
            "grammar",
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
    path: str | Path | None = "slice3.pietto",
    mode: CheckMode | None = None,
) -> tuple[SemanticMetadataArtifact, Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast, mode_override=mode)
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
            ),
        ),
        parse_result.ast,
        semantic_result,
        ir_result.ir,
    )


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def _field_names(value: object) -> set[str]:
    names: set[str] = set()

    def collect(item: object) -> None:
        if is_dataclass(item):
            names.update(field.name for field in fields(item))

    _walk(value, collect)
    return names


def _strings(value: object) -> set[str]:
    values: set[str] = set()
    _walk(value, lambda item: values.add(item) if isinstance(item, str) else None)
    return values


def _assert_no_raw_objects(value: object) -> None:
    _walk(value, _assert_not_raw_object)


def _assert_not_raw_object(value: object) -> None:
    assert not isinstance(value, Node)
    assert not isinstance(value, SemanticModel)
    assert not isinstance(value, (DefinitionIR, ExpressionIR, SymbolId, FieldId))


def _walk(value: object, visitor: Callable[[object], None]) -> None:
    visitor(value)
    if is_dataclass(value):
        for field in fields(value):
            _walk(getattr(value, field.name), visitor)
    elif isinstance(value, dict):
        for key, item in value.items():
            _walk(key, visitor)
            _walk(item, visitor)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            _walk(item, visitor)
