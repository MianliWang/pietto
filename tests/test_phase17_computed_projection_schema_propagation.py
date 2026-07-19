from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

from pietto.ast_nodes import Expression, Script, SelectItem, TableDef
from pietto.errors import Severity
from pietto.ir import (
    FieldRefIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_HASH = "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
GENERATED_HASH = "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4"

SOURCE_PREFIX = (
    "shape Row:\n"
    "    text: Text not null\n"
    "    count: Int not null\n"
    "    active: Bool not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source mysql_rows: Row is mysql.table("rows")\n'
)


def test_computed_aliases_propagate_known_schema_and_ir_types() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
        "        label = lower(text)\n"
        "        active = count > 0\n"
    )
    relation = _relation(script, "enriched")
    relation_ir = _relation_ir(script_ir, "enriched")

    schema = semantic.model.relation_row_schemas[relation]

    assert list(schema.fields) == ["value", "label", "active"]
    assert [schema.fields[name].resolved_type.name for name in schema.fields] == [
        "Int",
        "Text",
        "Bool",
    ]
    assert [
        field.type_ref.canonical_name for field in relation_ir.row_schema.fields
    ] == [
        "Int",
        "Text",
        "Bool",
    ]
    assert [
        cast(TypeRefIR, projection.type_ref).canonical_kind
        for projection in relation_ir.projections
    ] == [
        TypeKindIR.BUILTIN,
        TypeKindIR.BUILTIN,
        TypeKindIR.BUILTIN,
    ]


def test_mixed_numeric_computed_alias_propagates_float_schema() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1.5\n"
    )
    relation = _relation(script, "enriched")
    relation_ir = _relation_ir(script_ir, "enriched")

    assert (
        semantic.model.relation_row_schemas[relation].fields["value"].resolved_type.name
        == "Float"
    )
    assert relation_ir.row_schema.fields[0].type_ref.canonical_name == "Float"


def test_downstream_relation_reads_precise_computed_alias_schema() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
        "        label = lower(text)\n"
        "        active = count > 0\n"
        "table filtered:\n"
        "    from enriched\n"
        "    where value > 10\n"
        "    select:\n"
        "        value\n"
        "        label\n"
        "        active\n"
    )
    filtered = _relation(script, "filtered")
    filtered_ir = _relation_ir(script_ir, "filtered")
    where_expression = _where_expression(filtered)

    schema = semantic.model.relation_row_schemas[filtered]

    assert list(schema.fields) == ["value", "label", "active"]
    assert schema.fields["value"].resolved_type.name == "Int"
    assert schema.fields["label"].resolved_type.name == "Text"
    assert schema.fields["active"].resolved_type.name == "Bool"
    assert semantic.model.expression_value_types[
        where_expression
    ].resolved_type.name == ("Bool")
    value_projection = cast(FieldRefIR, filtered_ir.projections[0].expression)
    assert value_projection.value_type.canonical_name == "Int"


def test_multi_layer_computed_alias_propagation_reaches_fixed_point() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table first:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        next_value = value + 1\n"
        "table third:\n"
        "    from second\n"
        "    select:\n"
        "        final_value = next_value + 1\n"
    )
    third = _relation(script, "third")

    assert (
        semantic.model.relation_row_schemas[third]
        .fields["final_value"]
        .resolved_type.name
        == "Int"
    )


def test_unary_computed_alias_preserves_expression_nullability() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = -count\n"
    )
    relation = _relation(script, "enriched")
    relation_ir = _relation_ir(script_ir, "enriched")

    field = semantic.model.relation_row_schemas[relation].fields["value"]
    ir_expression = relation_ir.projections[0].expression

    assert field.resolved_type.name == "Int"
    assert field.nullability is EffectiveNullability.NON_NULL
    assert relation_ir.row_schema.fields[0].nullability is NullabilityIR.NON_NULL
    assert isinstance(ir_expression, UnaryIR)
    assert ir_expression.value_type.nullability is NullabilityIR.NON_NULL


def test_deferred_division_alias_remains_unknown_without_poisoning_schema() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count / 2\n"
    )
    relation = _relation(script, "enriched")
    expression = _select_expression(relation, 0)

    semantic = analyze(script)
    field = semantic.model.relation_row_schemas[relation].fields["value"]
    value_type = semantic.model.expression_value_types[expression]

    assert semantic.diagnostics == ()
    assert semantic.model.relation_row_schemas[relation].is_unknown is False
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.kind is ValueTypeKind.UNKNOWN


def test_unknown_computed_alias_preserves_alias_and_existing_diagnostic_only() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = missing + 1\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script)
    field = semantic.model.relation_row_schemas[relation].fields["value"]

    assert _errors(semantic) == [("PIE-S2102", "Unknown field: missing")]
    assert semantic.model.relation_row_schemas[relation].is_unknown is False
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_invalid_computed_alias_preserves_alias_and_s2105() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = text + 1\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script)
    field = semantic.model.relation_row_schemas[relation].fields["value"]

    assert _errors(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands",
        )
    ]
    assert semantic.model.relation_row_schemas[relation].is_unknown is False
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_unaliased_computed_projection_keeps_existing_s2304_policy() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        count + 1\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script, mode_override=CheckMode.CHECKED)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic.diagnostics
    ] == [
        (
            "PIE-S2304",
            Severity.WARNING,
            "Computed projection requires an explicit alias",
        )
    ]
    assert semantic.model.relation_row_schemas[relation].fields == {}


def test_duplicate_computed_aliases_keep_first_field_and_s2305() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
        "        value = count + 1.5\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script)
    field = semantic.model.relation_row_schemas[relation].fields["value"]

    assert _errors(semantic) == [("PIE-S2305", "Duplicate projection field: value")]
    assert field.resolved_type.name == "Int"


def test_projection_alias_does_not_enter_same_relation_where_scope() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    where value > 10\n"
        "    select:\n"
        "        value = count + 1\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script)

    assert _errors(semantic) == [("PIE-S2102", "Unknown field: value")]
    assert (
        semantic.model.relation_row_schemas[relation].fields["value"].resolved_type.name
        == "Int"
    )


def test_projection_alias_does_not_enter_same_relation_order_by_scope() -> None:
    script = _parse(
        SOURCE_PREFIX + "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
        "    order by:\n"
        "        value\n"
    )
    relation = _relation(script, "enriched")

    semantic = analyze(script)

    assert _errors(semantic) == [("PIE-S2102", "Unknown field: value")]
    assert (
        semantic.model.relation_row_schemas[relation].fields["value"].resolved_type.name
        == "Int"
    )


def test_qualified_projection_behavior_remains_stable() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = rows.count\n"
    )
    relation = _relation(script, "selected")

    field = semantic.model.relation_row_schemas[relation].fields["value"]

    assert field.resolved_type.name == "Int"
    assert field.nullability is EffectiveNullability.NON_NULL


def test_relationship_metadata_remains_ignored_by_schema_binding() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "relationship membership:\n"
        "    endpoint member: rows\n"
        "    endpoint group: rows\n"
        "table enriched:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
    )
    relation = _relation(script, "enriched")

    assert len(semantic.model.relationships) == 1
    assert (
        semantic.model.relation_row_schemas[relation].fields["value"].resolved_type.name
        == "Int"
    )


def test_existing_sql_bytes_remain_stable() -> None:
    _, _, postgres_ir = _compile(
        SOURCE_PREFIX + "table selected:\n    from rows\n    select:\n        text\n"
    )
    _, _, mysql_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from mysql_rows\n"
        "    select:\n"
        "        text\n"
    )
    _, _, qualified_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    where rows.active == true\n"
        "    select:\n"
        "        rows.text\n"
    )

    postgres = emit_postgres_sql(postgres_ir)
    mysql = emit_mysql_sql(mysql_ir)
    qualified = emit_postgres_sql(qualified_ir)

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == 'SELECT\n    "text" AS "text"\nFROM "rows"'
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == "SELECT\n    `text` AS `text`\nFROM `rows`"
    assert qualified.diagnostics == ()
    assert qualified.artifacts[0].sql == (
        'SELECT\n    "rows"."text" AS "text"\nFROM "rows" AS "rows"\n'
        'WHERE "rows"."active" = TRUE'
    )


def test_phase17_slice3_changes_no_grammar_or_generated_antlr() -> None:
    assert _sha256(REPO_ROOT / "grammar/Pietto.g4") == GRAMMAR_HASH
    generated = tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
    )
    assert _aggregate_sha256(generated) == GENERATED_HASH


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic = analyze(script)
    assert all(
        diagnostic.severity is not Severity.ERROR for diagnostic in semantic.diagnostics
    )
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _parse(source: str) -> Script:
    parse_result = parse_source(source, path="computed-schema.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _relation(script: Script, name: str) -> TableDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, TableDef) and definition.name == name
    )


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _where_expression(relation: TableDef) -> Expression:
    assert relation.where_clause is not None
    return relation.where_clause.expression


def _select_expression(relation: TableDef, index: int) -> Expression:
    item = relation.select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
