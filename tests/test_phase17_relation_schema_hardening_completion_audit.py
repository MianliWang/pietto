from __future__ import annotations

from pathlib import Path
from typing import cast

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, TypeKindIR, build_ir
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
SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: UUID not null\n"
    "    text: Text nullable\n"
    "    count: Int not null\n"
    "    amount: Float nullable\n"
    "    active: Bool not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source mysql_rows: Row is mysql.table("rows")\n'
)


def test_mixed_relation_chain_preserves_semantic_and_ir_row_schema() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        text = rows.text\n"
        "        value = count + 1\n"
        "        score = count + amount\n"
        "        label = lower(text)\n"
        "        active_value = active and true\n"
        "        negative_count = -count\n"
        "query normalized:\n"
        "    from selected\n"
        "    where value > 1 and active_value == true\n"
        "    select:\n"
        "        selected.id\n"
        "        label = label\n"
        "        value\n"
        "        score\n"
        "        active_value\n"
        "        negative_count\n"
        "table final:\n"
        "    from normalized\n"
        "    where value > 2\n"
        "    select:\n"
        "        normalized.id\n"
        "        output_label = label\n"
        "        next_value = value + 1\n"
        "        score\n"
        "        active_value\n"
        "        negative_count\n"
    )

    final = _relation(script, "final", TableDef)
    normalized = _relation(script, "normalized", QueryDef)
    final_ir = _relation_ir(script_ir, "final")
    normalized_ir = _relation_ir(script_ir, "normalized")

    expected = [
        ("id", "UUID", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        ("output_label", "Text", TypeKind.BUILTIN, EffectiveNullability.UNKNOWN),
        ("next_value", "Int", TypeKind.BUILTIN, EffectiveNullability.UNKNOWN),
        ("score", "Float", TypeKind.BUILTIN, EffectiveNullability.UNKNOWN),
        ("active_value", "Bool", TypeKind.BUILTIN, EffectiveNullability.UNKNOWN),
        (
            "negative_count",
            "Int",
            TypeKind.BUILTIN,
            EffectiveNullability.NON_NULL,
        ),
    ]

    assert _semantic_schema_facts(semantic, final) == expected
    assert _ir_schema_facts(final_ir) == [
        (name, type_name, TypeKindIR(kind), nullability)
        for name, type_name, kind, nullability in expected
    ]
    assert (
        semantic.model.expression_value_types[
            _where_expression(normalized)
        ].resolved_type.name
        == "Bool"
    )
    assert (
        semantic.model.expression_value_types[
            _where_expression(final)
        ].resolved_type.name
        == "Bool"
    )

    normalized_field = cast(FieldRefIR, normalized_ir.projections[0].expression)
    final_field = cast(FieldRefIR, final_ir.projections[0].expression)
    assert normalized_field.qualifier == ("selected",)
    assert normalized_field.field is not None
    assert normalized_field.field.name == "id"
    assert final_field.qualifier == ("normalized",)
    assert final_field.field is not None
    assert final_field.field.name == "id"


def test_unknown_and_invalid_computed_aliases_do_not_fake_downstream_precision() -> (
    None
):
    script = _parse(
        SOURCE_PREFIX + "table first:\n"
        "    from rows\n"
        "    select:\n"
        "        value = missing + 1\n"
        "        bad = text + 1\n"
        "        kept = count\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        next_value = value + 1\n"
        "        next_bad = bad + 1\n"
        "        kept\n"
    )
    first = _relation(script, "first", TableDef)
    second = _relation(script, "second", TableDef)

    semantic = analyze(script)

    assert _diagnostics(semantic) == [
        ("PIE-S2102", Severity.ERROR, "Unknown field: missing"),
        (
            "PIE-S2105",
            Severity.ERROR,
            "Invalid operands for operator +: expected numeric operands",
        ),
    ]
    assert [diagnostic.code for diagnostic in semantic.diagnostics].count(
        "PIE-S2105"
    ) == 1
    assert semantic.model.relation_row_schemas[first].is_unknown is False
    assert semantic.model.relation_row_schemas[second].is_unknown is False
    assert _field_kind(semantic, first, "value") is TypeKind.UNKNOWN
    assert _field_kind(semantic, first, "bad") is TypeKind.UNKNOWN
    assert _field_kind(semantic, second, "next_value") is TypeKind.UNKNOWN
    assert _field_kind(semantic, second, "next_bad") is TypeKind.UNKNOWN
    assert _field_type(semantic, second, "kept") == "Int"


def test_duplicate_projection_combinations_keep_first_field_and_s2305() -> None:
    script = _parse(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = rows.count\n"
        "        value = count + 1.5\n"
        "        count\n"
        "        count = lower(text)\n"
        "        label = lower(text)\n"
        "        label = rows.count\n"
    )
    relation = _relation(script, "projected", TableDef)

    semantic = analyze(script)

    assert _diagnostics(semantic) == [
        ("PIE-S2305", Severity.ERROR, "Duplicate projection field: value"),
        ("PIE-S2305", Severity.ERROR, "Duplicate projection field: count"),
        ("PIE-S2305", Severity.ERROR, "Duplicate projection field: label"),
    ]
    assert _field_type(semantic, relation, "value") == "Int"
    assert _field_type(semantic, relation, "count") == "Int"
    assert _field_type(semantic, relation, "label") == "Text"
    assert list(semantic.model.relation_row_schemas[relation].fields) == [
        "value",
        "count",
        "label",
    ]


def test_computed_alias_cycles_fail_closed_without_diagnostic_cascade() -> None:
    script = _parse(
        "table first:\n"
        "    from second\n"
        "    where missing_where and true\n"
        "    select:\n"
        "        value = missing_first + 1\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        next_value = value + 1\n"
    )
    first = _relation(script, "first", TableDef)
    second = _relation(script, "second", TableDef)

    semantic = analyze(script)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: first -> second -> first",
        )
    ]
    assert semantic.model.relation_row_schemas[first].is_unknown is True
    assert semantic.model.relation_row_schemas[second].is_unknown is True


def test_diagnostics_keep_source_order_and_refinement_diagnostics_are_not_duplicated() -> (
    None
):
    script = _parse(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    where missing_where and true\n"
        "    select:\n"
        "        count + 1\n"
        "        value = text + 1\n"
        "        value = count + 1\n"
    )

    semantic = analyze(script)

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
    ] == [
        (11, "PIE-S2102", "Unknown field: missing_where"),
        (13, "PIE-S2304", "Computed projection requires an explicit alias"),
        (
            14,
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands",
        ),
        (15, "PIE-S2305", "Duplicate projection field: value"),
    ]
    assert [diagnostic.code for diagnostic in semantic.diagnostics].count(
        "PIE-S2105"
    ) == 1


def test_representative_postgres_and_mysql_sql_bytes_remain_exact() -> None:
    _, _, postgres_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    where rows.active == true\n"
        "    select:\n"
        "        rows.text\n"
        "        value = count + 1\n"
    )
    _, _, mysql_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from mysql_rows\n"
        "    where mysql_rows.active == true\n"
        "    select:\n"
        "        mysql_rows.text\n"
        "        value = count + 1\n"
    )

    postgres = emit_postgres_sql(postgres_ir)
    mysql = emit_mysql_sql(mysql_ir)

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        "SELECT\n"
        '    "rows"."text" AS "text",\n'
        '    "count" + 1 AS "value"\n'
        'FROM "rows" AS "rows"\n'
        'WHERE "rows"."active" = TRUE'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n"
        "    `mysql_rows`.`text` AS `text`,\n"
        "    `count` + 1 AS `value`\n"
        "FROM `rows` AS `mysql_rows`\n"
        "WHERE `mysql_rows`.`active` = TRUE"
    )


def test_relationship_metadata_remains_outside_schema_ir_and_sql_behavior() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "relationship membership:\n"
        "    endpoint member: rows\n"
        "    endpoint group: rows\n"
        "table selected:\n"
        "    from rows\n"
        "    select:\n"
        "        rows.id\n"
        "        value = count + 1\n"
    )
    relation = _relation(script, "selected", TableDef)
    relation_ir = _relation_ir(script_ir, "selected")

    assert len(semantic.model.relationships) == 1
    assert _semantic_schema_facts(semantic, relation) == [
        ("id", "UUID", TypeKind.BUILTIN, EffectiveNullability.NON_NULL),
        ("value", "Int", TypeKind.BUILTIN, EffectiveNullability.UNKNOWN),
    ]
    field = cast(FieldRefIR, relation_ir.projections[0].expression)
    assert field.qualifier == ("rows",)
    assert field.field is not None
    assert field.field.name == "id"

    sql = emit_postgres_sql(script_ir)
    assert sql.diagnostics == ()
    assert sql.artifacts[0].sql == (
        "SELECT\n"
        '    "rows"."id" AS "id",\n'
        '    "count" + 1 AS "value"\n'
        'FROM "rows" AS "rows"'
    )


def test_slice3_refinement_loop_contract_stays_bounded_and_final_only() -> None:
    analyzer = (REPO_ROOT / "src/pietto/semantic/analyzer.py").read_text(
        encoding="utf-8",
    )
    loop_start = analyzer.index("for _ in range(iteration_limit):")
    loop_end = analyzer.index(
        "relation_value_types, relation_expression_diagnostics",
    )
    loop_body = analyzer[loop_start:loop_end]
    fingerprint_start = analyzer.index("def _relation_schema_fingerprint")
    fingerprint_body = analyzer[fingerprint_start:]

    assert "iteration_limit = derived_relation_count + 1" in analyzer
    assert "temporary_value_types, _ = type_relation_expressions" in loop_body
    assert "refined_schemas, _ = propagate_relation_schemas" in loop_body
    assert "diagnostics.extend" not in loop_body
    assert "_relation_schema_fingerprint(refined_schemas)" in loop_body
    assert "field.resolved_type.name" in fingerprint_body
    assert "field.resolved_type.kind" in fingerprint_body
    assert "field.nullability" in fingerprint_body
    assert "id(" not in fingerprint_body
    assert "final_schemas, schema_diagnostics = propagate_relation_schemas" in analyzer
    assert "expression_value_types=relation_value_types" in analyzer


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
    parse_result = parse_source(source, path="phase17-slice4.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _relation[RelationT: (TableDef, QueryDef)](
    script: Script,
    name: str,
    expected_type: type[RelationT],
) -> RelationT:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, expected_type) and definition.name == name
    )


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _where_expression(relation: TableDef | QueryDef) -> Expression:
    assert relation.where_clause is not None
    return relation.where_clause.expression


def _semantic_schema_facts(
    semantic: SemanticResult,
    relation: TableDef | QueryDef,
) -> list[tuple[str, str, TypeKind, EffectiveNullability]]:
    return [
        (
            field.name,
            field.resolved_type.name,
            field.resolved_type.kind,
            field.nullability,
        )
        for field in semantic.model.relation_row_schemas[relation].fields.values()
    ]


def _ir_schema_facts(
    relation_ir: RelationIR,
) -> list[tuple[str, str, TypeKindIR, EffectiveNullability]]:
    return [
        (
            field.name,
            field.type_ref.canonical_name,
            field.type_ref.canonical_kind,
            EffectiveNullability(field.nullability),
        )
        for field in relation_ir.row_schema.fields
    ]


def _field_type(
    semantic: SemanticResult,
    relation: TableDef | QueryDef,
    name: str,
) -> str:
    return semantic.model.relation_row_schemas[relation].fields[name].resolved_type.name


def _field_kind(
    semantic: SemanticResult,
    relation: TableDef | QueryDef,
    name: str,
) -> TypeKind:
    return semantic.model.relation_row_schemas[relation].fields[name].resolved_type.kind


def _diagnostics(
    result: SemanticResult,
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ]
