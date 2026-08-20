from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    analyze,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/any-bytes-json-support-posture-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"


BOUNDARY_TYPES = ("Any", "Bytes", "Json")
AGGREGATE_FIELDS = {
    "Any": "anything",
    "Bytes": "raw",
    "Json": "payload",
}


def _phase36_slice7_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice7_selects_tests_only_option_b() -> None:
    combined = _phase36_slice7_docs()

    for required in (
        "Phase 36 Slice 7 selects Option B: tests-only hardening",
        "Any / Bytes / Json Support Posture",
        "without changing compiler behavior",
        "`Any`, `Bytes`, and `Json` remain builtin names",
        "`Any` remains a top/deferred boundary type",
        "`Bytes` and `Json` remain deferred builtin behavior surfaces",
        "Direct `count(Bytes field)` and `count(Json field)` remain current accepted concrete non-Any `count(field)` behavior",
        "remain fail-closed with existing diagnostic `PIE-S2314`",
        "not a stable Any/Bytes/Json-specific compatibility guarantee",
        "Slice 7 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_any_bytes_json_are_builtin_names_with_documented_posture() -> None:
    catalog = _read(CATALOG_PATH)
    metadata_builder = _read(METADATA_BUILDER_PATH)
    combined = _phase36_slice7_docs()

    for type_name in BOUNDARY_TYPES:
        assert f'"{type_name}"' in catalog
        assert f"`{type_name}` is in `BUILTIN_TYPE_NAMES`" in combined

    assert '_DEFERRED_BUILTINS = frozenset({"Bytes", "Json"})' in metadata_builder
    assert 'Any with `support_posture="current"`' in combined
    assert 'Bytes with `support_posture="deferred_builtin"`' in combined
    assert 'Json with `support_posture="deferred_builtin"`' in combined


def test_field_source_projection_alias_and_metadata_postures_remain_generic() -> None:
    script = _parse(_projection_source())
    semantic_result = analyze(script)
    relation = _relation(semantic_result)
    source_schema = next(iter(semantic_result.model.source_row_schemas.values()))
    output_schema = semantic_result.model.relation_row_schemas[relation]

    assert _error_codes(semantic_result) == []
    for field_name, type_name, expected_nullability in (
        ("anything", "Any", EffectiveNullability.NULLABLE),
        ("raw", "Bytes", EffectiveNullability.NON_NULL),
        ("payload", "Json", EffectiveNullability.NULLABLE),
    ):
        source_field = source_schema.fields[field_name]
        projected_field = output_schema.fields[field_name]
        alias_field = output_schema.fields[f"alias_{field_name}"]

        for field in (source_field, projected_field, alias_field):
            assert field.resolved_type.kind is TypeKind.BUILTIN
            assert field.resolved_type.name == type_name
            assert field.nullability is expected_nullability

    ir = _compile(_projection_source())
    artifact = build_semantic_metadata_artifact(
        path="phase36-slice7-any-bytes-json.pietto",
        script=script,
        semantic_result=semantic_result,
        ir=ir,
    )
    source_types = {
        field.name: field.type for field in artifact.metadata.sources[0].schema.fields
    }

    assert source_types["anything"].support_posture == "current"
    assert source_types["raw"].support_posture == "deferred_builtin"
    assert source_types["payload"].support_posture == "deferred_builtin"


def test_bytes_json_direct_count_remains_accepted_and_sql_emitting() -> None:
    cases = (
        ("Bytes", "raw", 'COUNT("raw")', "COUNT(`raw`)"),
        ("Json", "payload", 'COUNT("payload")', "COUNT(`payload`)"),
    )

    for type_name, field_name, postgres_fragment, mysql_fragment in cases:
        postgres_result = emit_postgres_sql(
            _compile(_count_source(type_name, field_name, "postgres.table"))
        )
        mysql_result = emit_mysql_sql(
            _compile(_count_source(type_name, field_name, "mysql.table"))
        )

        assert postgres_result.diagnostics == ()
        assert mysql_result.diagnostics == ()
        assert postgres_fragment in postgres_result.artifacts[0].sql
        assert mysql_fragment in mysql_result.artifacts[0].sql


def test_any_count_and_boundary_aggregates_fail_with_pie_s2314() -> None:
    cases = [("count", "Any")]
    cases.extend(
        (function_name, type_name)
        for function_name in ("count_distinct", "min", "max", "sum", "avg")
        for type_name in BOUNDARY_TYPES
    )

    for function_name, type_name in cases:
        field_name = AGGREGATE_FIELDS[type_name]
        result = analyze(
            _parse(
                _aggregate_source(
                    type_name,
                    field_name,
                    f"value = {function_name}({field_name})",
                )
            )
        )
        relation = _relation(result)
        output_field = result.model.relation_row_schemas[relation].fields["value"]

        assert _error_codes(result) == ["PIE-S2314"]
        assert output_field.resolved_type.kind is TypeKind.UNKNOWN
        assert output_field.nullability is EffectiveNullability.UNKNOWN


def test_generic_shared_paths_are_current_risky_not_stable_guarantees() -> None:
    combined = _phase36_slice7_docs()

    for required in (
        "Comparison, ordering, `order by`, `group by`, and `satisfying` examples for Any / Bytes / Json are current generic accepted/risky shared paths",
        "not newly authorized stable type-specific semantics",
        "does not approve a compatibility guarantee",
    ):
        assert required in combined, required

    for type_name in BOUNDARY_TYPES:
        for source in (
            _projection_expression_source(type_name, "same = value == other"),
            _projection_expression_source(type_name, "before = value < other"),
            _order_by_source(type_name),
            _group_by_source(type_name),
            _satisfying_source(type_name),
        ):
            script = _parse(source)
            semantic_result = analyze(script)
            ir_result = build_ir(script, semantic_result.model)

            assert _error_codes(semantic_result) == []
            assert ir_result.diagnostics == ()
            assert ir_result.ir is not None


def test_no_special_carrier_or_output_schema_expansion_was_added() -> None:
    combined = _phase36_slice7_docs()
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)

    for required in (
        "There is no special carrier for Any in the semantic or IR model",
        "There is no special carrier for Bytes in the semantic or IR model",
        "There is no special carrier for Json in the semantic or IR model",
        "Existing semantic facts use the generic `ResolvedType` shape",
        "existing IR facts use the generic `TypeRefIR` shape",
    ):
        assert required in combined, required

    for required in (
        "class ResolvedType:",
        "name: str",
        "kind: TypeKind",
        "class ValueType:",
        "resolved_type: ResolvedType",
        "nullability: EffectiveNullability",
    ):
        assert required in semantic_model, required

    for required in (
        "class TypeRefIR:",
        "declared_name: str",
        "canonical_name: str",
        "kind: TypeKindIR",
        "canonical_kind: TypeKindIR",
        "nullability: NullabilityIR",
    ):
        assert required in ir_model, required

    sources = (
        semantic_model,
        ir_model,
        _read(METADATA_MODEL_PATH),
        _read(METADATA_SERIALIZER_PATH),
        _read(METADATA_TEXT_PATH),
        _read(CLI_JSON_PATH),
    )
    for source in sources:
        lowered = source.lower()
        for forbidden in (
            "json_path",
            "json_schema",
            "binary_encoding",
            "byte_order",
            "dynamic_type",
            "runtime_type",
            "native_json",
            "native_binary",
        ):
            assert forbidden not in lowered, forbidden


def test_unsupported_and_future_surfaces_remain_closed() -> None:
    combined = _phase36_slice7_docs()

    for required in (
        "dynamic Any behavior",
        "runtime casts",
        "permissive SQL fallback",
        "binary literals",
        "binary encoding policy",
        "byte functions and operators",
        "JSON structural typing",
        "JSON path extraction",
        "JSON operators and functions",
        "object/array schema validation",
        "native binary metadata",
        "native DB JSON metadata",
        "storage/DDL behavior",
        "schema introspection or db pull",
        "runtime/database execution",
        "Any-specific, Bytes-specific, or Json-specific JSON v1 fields",
        "Any-specific, Bytes-specific, or Json-specific Project JSON v2 fields",
        "Any-specific, Bytes-specific, or Json-specific Semantic Metadata Artifact v1",
        "SQL golden byte changes",
        "fixture or example changes",
        "package, workflow, release, publish/upload, signing, or attestation changes",
    ):
        assert required in combined, required


def _projection_source() -> str:
    return (
        "shape Flexible:\n"
        "    anything: Any nullable\n"
        "    raw: Bytes not null\n"
        "    payload: Json nullable\n"
        'source events: Flexible is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    select:\n"
        "        anything\n"
        "        raw\n"
        "        payload\n"
        "        alias_anything = anything\n"
        "        alias_raw = raw\n"
        "        alias_payload = payload\n"
    )


def _count_source(type_name: str, field_name: str, connector: str) -> str:
    return (
        "shape Flexible:\n"
        f"    {field_name}: {type_name} not null\n"
        f'source events: Flexible is {connector}("events")\n'
        "table counted:\n"
        "    from events\n"
        "    select:\n"
        f"        value = count({field_name})\n"
    )


def _aggregate_source(type_name: str, field_name: str, projection: str) -> str:
    return (
        "shape Flexible:\n"
        f"    {field_name}: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table aggregated:\n"
        "    from events\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _projection_expression_source(type_name: str, projection: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        f"    other: {type_name} nullable\n"
        'source events: Flexible is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _order_by_source(type_name: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table ordered:\n"
        "    from events\n"
        "    select:\n"
        "        value\n"
        "    order by:\n"
        "        value\n"
    )


def _group_by_source(type_name: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table grouped:\n"
        "    from events\n"
        "    group by:\n"
        "        value\n"
        "    select:\n"
        "        value\n"
        "        rows = count()\n"
    )


def _satisfying_source(type_name: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table grouped:\n"
        "    from events\n"
        "    group by:\n"
        "        value\n"
        "    select:\n"
        "        value\n"
        "        rows = count()\n"
        "    satisfying:\n"
        "        value == value\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
