from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Callable

from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import (
    SemanticMetadataArtifact,
    SemanticMetadataType,
)
from pietto.ast_nodes import Node, Script
from pietto.ir import FieldId, ScriptIR, SymbolId, build_ir
from pietto.ir.model import (
    DefinitionIR,
    ExpressionIR,
    NullabilityIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    RowFieldIR,
    RowSchemaIR,
    SourceSpan,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticModel, SemanticResult, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs/spec/pietto-v0.9.md",
)

SOURCE = (
    "type EventId = UUID not null\n"
    "type PayloadDoc = Json nullable\n"
    "type Price = Decimal(12, 2) not null\n"
    "enum Status:\n"
    "    open\n"
    "    closed\n"
    "shape Address:\n"
    "    city: Text nullable\n"
    "shape Event:\n"
    "    id: EventId not null\n"
    "    payload_doc: PayloadDoc nullable\n"
    "    status: Status nullable\n"
    "    address: Address nullable\n"
    "    anything: Any nullable\n"
    "    active: Bool not null\n"
    "    count: Int not null\n"
    "    ratio: Float nullable\n"
    "    label: Text not null\n"
    "    price: Price not null\n"
    "    direct_decimal: Decimal not null\n"
    "    created_on: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    blob: Bytes nullable\n"
    "    direct_json: Json nullable\n"
    "    direct_uuid: UUID not null\n"
    "constraint valid_event(id: EventId not null) -> Bool not null:\n"
    "    id is not null\n"
    "derive normalized_label(label: Text not null) -> Text not null:\n"
    "    lower(label)\n"
    'source events: Event is postgres.table("secret_events_table")\n'
    "table projected:\n"
    "    from events\n"
    "    select:\n"
    "        id\n"
    "        payload_doc\n"
    "        status\n"
    "        address\n"
    "        anything\n"
    "        active\n"
    "        count\n"
    "        ratio\n"
    "        label\n"
    "        price\n"
    "        direct_decimal\n"
    "        created_on\n"
    "        created_at\n"
    "        blob\n"
    "        direct_json\n"
    "        direct_uuid\n"
    "query summarized:\n"
    "    from projected\n"
    "    select:\n"
    "        id\n"
    "        status\n"
    "        address\n"
    "query final_report:\n"
    "    from summarized\n"
    "    select:\n"
    "        id\n"
    "        status\n"
)

SOURCE_FIELDS = (
    "id",
    "payload_doc",
    "status",
    "address",
    "anything",
    "active",
    "count",
    "ratio",
    "label",
    "price",
    "direct_decimal",
    "created_on",
    "created_at",
    "blob",
    "direct_json",
    "direct_uuid",
)


def test_all_definition_kinds_are_ordered_and_located() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path="slice4-definitions.pietto")

    assert [(item.name, item.kind) for item in artifact.metadata.definitions] == [
        ("EventId", "type"),
        ("PayloadDoc", "type"),
        ("Price", "type"),
        ("Status", "enum"),
        ("Address", "shape"),
        ("Event", "shape"),
        ("valid_event", "constraint"),
        ("normalized_label", "derive"),
        ("events", "source"),
        ("projected", "table"),
        ("summarized", "query"),
        ("final_report", "query"),
    ]
    assert {item.kind for item in artifact.metadata.definitions} == {
        "type",
        "enum",
        "shape",
        "source",
        "table",
        "query",
        "constraint",
        "derive",
    }
    for definition in artifact.metadata.definitions:
        assert definition.location is not None
        assert definition.location.path == "slice4-definitions.pietto"


def test_source_schema_fields_preserve_order_types_nullability_and_locations() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path="slice4-schema.pietto")
    source = artifact.metadata.sources[0]

    assert [field.name for field in source.schema.fields] == list(SOURCE_FIELDS)
    for field in source.schema.fields:
        assert field.location is not None
        assert field.location.path == "slice4-schema.pietto"
        assert field.nullability == field.type.nullability

    types = _source_types(artifact)
    _assert_type(
        types["id"],
        name="EventId",
        kind="type_alias",
        canonical_name="UUID",
        canonical_kind="builtin",
        nullability="non_null",
        support_posture="limited_frozen",
    )
    _assert_type(
        types["payload_doc"],
        name="PayloadDoc",
        kind="type_alias",
        canonical_name="Json",
        canonical_kind="builtin",
        nullability="nullable",
        support_posture="deferred_builtin",
    )
    _assert_type(
        types["status"],
        name="Status",
        kind="enum",
        canonical_name="Status",
        canonical_kind="enum",
        nullability="nullable",
        support_posture="metadata_only",
    )
    _assert_type(
        types["address"],
        name="Address",
        kind="shape",
        canonical_name="Address",
        canonical_kind="shape",
        nullability="nullable",
        support_posture="current",
    )

    expected_builtin_postures = {
        "anything": ("Any", "nullable", "current"),
        "active": ("Bool", "non_null", "current"),
        "count": ("Int", "non_null", "current"),
        "ratio": ("Float", "nullable", "current"),
        "label": ("Text", "non_null", "current"),
        "direct_decimal": ("Decimal", "non_null", "current"),
        "created_on": ("Date", "nullable", "current"),
        "created_at": ("Timestamp", "non_null", "current"),
        "blob": ("Bytes", "nullable", "deferred_builtin"),
        "direct_json": ("Json", "nullable", "deferred_builtin"),
        "direct_uuid": ("UUID", "non_null", "limited_frozen"),
    }
    for field_name, (
        type_name,
        nullability,
        support_posture,
    ) in expected_builtin_postures.items():
        _assert_type(
            types[field_name],
            name=type_name,
            kind="builtin",
            canonical_name=type_name,
            canonical_kind="builtin",
            nullability=nullability,
            support_posture=support_posture,
        )

    _assert_type(
        types["price"],
        name="Price",
        kind="type_alias",
        canonical_name="Decimal",
        canonical_kind="builtin",
        nullability="non_null",
        support_posture="current",
    )


def test_source_connector_values_and_raw_structures_are_excluded() -> None:
    artifact, _, _, _ = _artifact(SOURCE)

    strings = _strings(artifact)
    assert "secret_events_table" not in strings
    assert "postgres.table" not in strings
    assert "postgres" not in strings

    forbidden_field_names = {
        "connector",
        "arguments",
        "config",
        "secret",
        "secrets",
        "credential",
        "credentials",
        "dialect",
        "relationships",
        "symbol",
        "field_id",
        "ast",
        "ir",
    }
    assert forbidden_field_names.isdisjoint(_field_names(artifact))


def test_relation_input_kinds_and_input_output_schemas_are_normalized() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    projected, summarized, final_report = artifact.metadata.relations

    assert (
        projected.name,
        projected.kind,
        projected.input.name,
        projected.input.kind,
    ) == (
        "projected",
        "table",
        "events",
        "source",
    )
    assert [field.name for field in projected.input_schema.fields] == list(
        SOURCE_FIELDS
    )
    assert [field.name for field in projected.output_schema.fields] == list(
        SOURCE_FIELDS
    )

    assert (
        summarized.name,
        summarized.kind,
        summarized.input.name,
        summarized.input.kind,
    ) == (
        "summarized",
        "query",
        "projected",
        "table",
    )
    assert [field.name for field in summarized.input_schema.fields] == list(
        SOURCE_FIELDS
    )
    assert [field.name for field in summarized.output_schema.fields] == [
        "id",
        "status",
        "address",
    ]

    assert (
        final_report.name,
        final_report.kind,
        final_report.input.name,
        final_report.input.kind,
    ) == (
        "final_report",
        "query",
        "summarized",
        "query",
    )
    assert [field.name for field in final_report.input_schema.fields] == [
        "id",
        "status",
        "address",
    ]
    assert [field.name for field in final_report.output_schema.fields] == [
        "id",
        "status",
    ]


def test_type_posture_and_metadata_types_first_reference_order_are_locked() -> None:
    artifact, _, _, _ = _artifact(SOURCE)

    assert _type_signature(artifact.metadata.types) == [
        ("type_alias", "EventId", "builtin", "UUID", "non_null", "limited_frozen"),
        (
            "type_alias",
            "PayloadDoc",
            "builtin",
            "Json",
            "nullable",
            "deferred_builtin",
        ),
        ("enum", "Status", "enum", "Status", "nullable", "metadata_only"),
        ("shape", "Address", "shape", "Address", "nullable", "current"),
        ("builtin", "Any", "builtin", "Any", "nullable", "current"),
        ("builtin", "Bool", "builtin", "Bool", "non_null", "current"),
        ("builtin", "Int", "builtin", "Int", "non_null", "current"),
        ("builtin", "Float", "builtin", "Float", "nullable", "current"),
        ("builtin", "Text", "builtin", "Text", "non_null", "current"),
        ("type_alias", "Price", "builtin", "Decimal", "non_null", "current"),
        ("builtin", "Decimal", "builtin", "Decimal", "non_null", "current"),
        ("builtin", "Date", "builtin", "Date", "nullable", "current"),
        ("builtin", "Timestamp", "builtin", "Timestamp", "non_null", "current"),
        ("builtin", "Bytes", "builtin", "Bytes", "nullable", "deferred_builtin"),
        ("builtin", "Json", "builtin", "Json", "nullable", "deferred_builtin"),
        ("builtin", "UUID", "builtin", "UUID", "non_null", "limited_frozen"),
    ]
    assert len(artifact.metadata.types) == len(set(artifact.metadata.types))

    type_field_names = {field.name for field in fields(SemanticMetadataType)}
    assert {
        "precision",
        "scale",
        "timezone",
        "literal",
        "native",
        "database",
    }.isdisjoint(type_field_names)


def test_unknown_schema_unknown_input_and_synthetic_locations_are_private_fallbacks() -> (
    None
):
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
    assert projected.projections[0].type.nullability == "unknown"

    _, script, semantic_result, _ = _artifact(SOURCE)
    manual_artifact = build_semantic_metadata_artifact(
        path=None,
        script=script,
        semantic_result=semantic_result,
        ir=ScriptIR(
            definitions=(
                _manual_relation(
                    name="unknown_output",
                    source_name="missing_input",
                    row_schema=RowSchemaIR(fields=(), is_unknown=True),
                ),
                _manual_relation(
                    name="synthetic_output",
                    source_name="missing_input",
                    row_schema=RowSchemaIR(
                        fields=(
                            RowFieldIR(
                                name="mystery",
                                type_ref=_unknown_type_ref(),
                                nullability=NullabilityIR.UNKNOWN,
                                span=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    unknown_output, synthetic_output = manual_artifact.metadata.relations

    assert unknown_output.input.name == "missing_input"
    assert unknown_output.input.kind == "unknown"
    assert unknown_output.input_schema.fields == ()
    assert unknown_output.output_schema.fields == ()

    assert synthetic_output.input.kind == "unknown"
    field = synthetic_output.output_schema.fields[0]
    assert field.location is None
    assert field.nullability == "unknown"
    assert field.type.status == "unknown"
    assert field.type.name is None
    assert field.type.canonical_name is None
    assert field.type.nullability == "unknown"
    assert field.type.support_posture == "unknown"


def test_no_raw_ast_semantic_ir_symbol_or_field_identity_is_exposed() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    _, script, semantic_result, _ = _artifact(SOURCE)
    manual_artifact = build_semantic_metadata_artifact(
        path="manual.pietto",
        script=script,
        semantic_result=semantic_result,
        ir=ScriptIR(
            definitions=(
                _manual_relation(
                    name="synthetic_output",
                    source_name="missing_input",
                    row_schema=RowSchemaIR(
                        fields=(
                            RowFieldIR(
                                name="mystery",
                                type_ref=_unknown_type_ref(),
                                nullability=NullabilityIR.UNKNOWN,
                                span=None,
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    _assert_no_raw_objects(artifact)
    _assert_no_raw_objects(manual_artifact)


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


def test_slice4_status_docs_record_private_schema_type_completion_only() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 32 Slice 4 Definition, Schema, Type, And Nullability Metadata is complete",
            "Slice 4 hardens private metadata definition/schema/type/nullability coverage",
            "Phase 32 as a whole is not complete",
            "No `pietto explain` CLI behavior",
            "JSON serializer",
            "text renderer",
            "public API",
            "JSON v1 mutation",
            "SQL behavior",
            "semantic behavior change",
            "IR behavior change",
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
    path: str | Path | None = "slice4.pietto",
    mode: CheckMode | None = None,
) -> tuple[SemanticMetadataArtifact, Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast, mode_override=mode)
    assert all(
        diagnostic.severity.value != "error"
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


def _source_types(
    artifact: SemanticMetadataArtifact,
) -> dict[str, SemanticMetadataType]:
    return {
        field.name: field.type for field in artifact.metadata.sources[0].schema.fields
    }


def _assert_type(
    value: SemanticMetadataType,
    *,
    name: str,
    kind: str,
    canonical_name: str,
    canonical_kind: str,
    nullability: str,
    support_posture: str,
) -> None:
    assert value.status == "known"
    assert value.name == name
    assert value.kind == kind
    assert value.canonical_name == canonical_name
    assert value.canonical_kind == canonical_kind
    assert value.nullability == nullability
    assert value.support_posture == support_posture


def _type_signature(
    values: Iterable[SemanticMetadataType],
) -> list[tuple[str, str | None, str, str | None, str, str]]:
    return [
        (
            value.kind,
            value.name,
            value.canonical_kind,
            value.canonical_name,
            value.nullability,
            value.support_posture,
        )
        for value in values
    ]


def _unknown_type_ref() -> TypeRefIR:
    return TypeRefIR(
        symbol=None,
        canonical_symbol=None,
        declared_name="<unknown>",
        canonical_name="<unknown>",
        kind=TypeKindIR.UNKNOWN,
        canonical_kind=TypeKindIR.UNKNOWN,
        nullability=NullabilityIR.UNKNOWN,
    )


def _manual_relation(
    *,
    name: str,
    source_name: str,
    row_schema: RowSchemaIR,
) -> RelationIR:
    span = SourceSpan(
        path=None,
        line=1,
        column=1,
        end_line=1,
        end_column=1,
    )
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, name),
        name=name,
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(
            target=SymbolId(SymbolNamespace.RELATION, source_name),
            name=source_name,
            span=span,
        ),
        filter=None,
        projections=(),
        row_schema=row_schema,
        span=span,
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
