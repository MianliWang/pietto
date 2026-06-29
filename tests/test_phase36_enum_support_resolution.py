from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import AggregateCallIR, EnumIR, RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"
SEMANTIC_SATISFYING_PATH = REPO_ROOT / "src/pietto/semantic/satisfying.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

ENUM_SOURCE_HEADER = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape EnumOrder:\n"
    "    status: Status not null\n"
    "    optional_status: Status nullable\n"
    "    amount: Int not null\n"
)


def _phase36_slice5_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice5_selects_narrow_fail_closed_option_c() -> None:
    combined = _phase36_slice5_docs()

    for required in (
        "Phase 36 Slice 5 selects Option C: narrow semantic fail-closed behavior change",
        "`count(Enum field)` now fails in semantic aggregate validation with existing diagnostic `PIE-S2314`",
        "instead of being accepted by semantic/IR and then reaching PostgreSQL/private MySQL SQL backend fail-closed output with `PIE-B1000`",
        "Enum remains metadata/readiness, not a builtin scalar",
        "Slice 5 does not make Enum a fully stable SQL scalar",
        "Slice 5 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_count_enum_field_fails_semantic_validation_with_pie_s2314() -> None:
    for connector in ("postgres.table", "mysql.table"):
        script = _parse(_source(connector, "known_statuses = count(status)"))
        semantic_result = analyze(script)
        relation = _relation(semantic_result)
        field = semantic_result.model.relation_row_schemas[relation].fields[
            "known_statuses"
        ]

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_count_enum_field_no_longer_reaches_backend_pie_b1000_path() -> None:
    for connector in ("postgres.table", "mysql.table"):
        script = _parse(_source(connector, "known_statuses = count(status)"))
        semantic_result = analyze(script)
        ir_result = build_ir(script, semantic_result.model)

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert ir_result.ir is not None
        projection = _relation_ir(ir_result.ir).projections[0]
        assert not isinstance(projection.expression, AggregateCallIR)


def test_other_enum_aggregate_boundaries_remain_rejected() -> None:
    for projection in (
        "value = count_distinct(status)",
        "value = min(status)",
        "value = max(status)",
        "value = sum(status)",
        "value = avg(status)",
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert _error_codes(result) == ["PIE-S2314"]
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_enum_metadata_readiness_remains_intact() -> None:
    script = _parse(_source("postgres.table", "status\n        optional_status"))
    semantic_result = analyze(script)
    relation = _relation(semantic_result)
    schema = semantic_result.model.relation_row_schemas[relation]

    assert _error_codes(semantic_result) == []
    assert schema.fields["status"].resolved_type.kind is TypeKind.ENUM
    assert schema.fields["status"].resolved_type.name == "Status"
    assert schema.fields["optional_status"].resolved_type.kind is TypeKind.ENUM
    assert schema.fields["optional_status"].nullability is (
        EffectiveNullability.NULLABLE
    )

    ir_result = build_ir(script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    assert any(
        isinstance(definition, EnumIR) for definition in ir_result.ir.definitions
    )

    artifact = build_semantic_metadata_artifact(
        path="phase36-slice5-enum.pietto",
        script=script,
        semantic_result=semantic_result,
        ir=ir_result.ir,
    )
    enum_type = next(
        type_ref
        for type_ref in artifact.metadata.types
        if type_ref.kind == "enum" and type_ref.name == "Status"
    )
    assert enum_type.canonical_kind == "enum"
    assert enum_type.support_posture == "metadata_only"


def test_enum_literal_cast_native_runtime_surfaces_remain_absent() -> None:
    catalog = _read(CATALOG_PATH)
    semantic_aggregates = _read(SEMANTIC_AGGREGATES_PATH)
    semantic_expressions = _read(SEMANTIC_EXPRESSIONS_PATH)
    semantic_group_by = _read(SEMANTIC_GROUP_BY_PATH)
    semantic_satisfying = _read(SEMANTIC_SATISFYING_PATH)
    ir_model = _read(IR_MODEL_PATH)
    metadata_model = _read(METADATA_MODEL_PATH)
    metadata_builder = _read(METADATA_BUILDER_PATH)
    metadata_serializer = _read(METADATA_SERIALIZER_PATH)
    cli_json = _read(CLI_JSON_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)

    assert '"Enum"' not in catalog
    assert "TypeKind.ENUM" in semantic_aggregates
    assert 'ENUM = "enum"' in ir_model
    assert "class EnumIR" in ir_model
    assert "metadata_only" in metadata_builder
    assert "support_posture: str" in metadata_model

    for source in (
        catalog,
        semantic_expressions,
        semantic_group_by,
        semantic_satisfying,
        ir_model,
        metadata_model,
        metadata_serializer,
        cli_json,
        postgres,
        mysql,
    ):
        lowered = source.lower()
        for forbidden in (
            "enum_literal",
            "enum cast",
            "enum_cast",
            "native enum",
            "native_enum",
            "enum storage",
            "enum_storage",
            "enum ddl",
            "enum_ddl",
            "create type",
        ):
            assert forbidden not in lowered, forbidden

    for projection, expected_code in (
        ("value = active", None),
        ("value = Status.active", "PIE-S2102"),
        ('value = Status("active")', "PIE-S2103"),
        ("value = cast(status)", "PIE-S2103"),
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        expression = _select_expression(relation, "value")

        if expected_code is not None:
            assert expected_code in _error_codes(result)
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.UNKNOWN
        )


def test_json_metadata_schema_expansion_is_not_authorized() -> None:
    combined = _phase36_slice5_docs()
    metadata_model = _read(METADATA_MODEL_PATH)
    metadata_serializer = _read(METADATA_SERIALIZER_PATH)
    cli_json = _read(CLI_JSON_PATH)

    for required in (
        "JSON v1 schema changes",
        "Project JSON v2 schema changes",
        "Semantic Metadata Artifact v1 schema or output changes",
        "package, workflow, or release changes",
    ):
        assert required in combined, required

    for source in (metadata_model, metadata_serializer, cli_json):
        for forbidden in (
            "enum_members",
            "enum_values",
            "native_enum",
            "database_enum",
            "storage_enum",
            "ddl_enum",
        ):
            assert forbidden not in source.lower(), forbidden


def test_forbidden_surfaces_are_not_modified_by_slice5() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def _source(connector: str, projections: str) -> str:
    return (
        ENUM_SOURCE_HEADER
        + f'source orders: EnumOrder is {connector}("orders")\n'
        + "table status_counts:\n"
        + "    from orders\n"
        + "    select:\n"
        + f"        {projections}\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


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


def _select_expression(relation: TableDef | QueryDef, alias: str) -> Expression:
    for item in relation.select_items:
        if item.alias == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
