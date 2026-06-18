from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    Expression,
    SelectItem,
    Script,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir import BinaryIR, RelationIR, ScriptIR, TypeKindIR, UnaryIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_HASH = "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
GENERATED_HASH = "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1"

SOURCE_PREFIX = (
    "shape Row:\n"
    "    text: Text not null\n"
    "    count: Int not null\n"
    "    active: Bool not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source mysql_rows: Row is mysql.table("rows")\n'
)


def test_boolean_binary_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where count > 1 and active == true\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BinaryExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_between_where_resolves_to_known_bool() -> None:
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where count between 1 and 5\n"
        "    select:\n"
        "        text\n"
    )
    expression = _where_expression(script)

    value_type = semantic.model.expression_value_types[expression]

    assert isinstance(expression, BetweenExpr)
    assert value_type.resolved_type.name == "Bool"
    assert value_type.kind is ValueTypeKind.KNOWN
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_invalid_bool_binary_reports_s2105_at_full_span() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table filtered:\n"
        "    from rows\n"
        "    where text and true\n"
        "    select:\n"
        "        text\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    expression = _where_expression(parse_result.ast)

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator and: expected Bool operands",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


def test_int_arithmetic_projection_has_semantic_and_ir_type() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.UNKNOWN
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.canonical_kind is TypeKindIR.BUILTIN


def test_mixed_numeric_projection_promotes_to_float() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count + 1.5\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Float"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Float"


def test_unary_numeric_projection_preserves_type_and_nullability() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = -count\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, UnaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert semantic_type.nullability is EffectiveNullability.NON_NULL
    assert isinstance(ir_expression, UnaryIR)
    assert ir_expression.value_type.canonical_name == "Int"
    assert ir_expression.value_type.nullability.value == "non_null"


def test_modulo_projection_requires_int_and_returns_int() -> None:
    script, semantic, script_ir = _compile(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count % 2\n"
    )
    expression = _select_expression(script, 0)

    semantic_type = semantic.model.expression_value_types[expression]
    ir_expression = _relation_ir(script_ir).projections[0].expression

    assert isinstance(expression, BinaryExpr)
    assert semantic_type.resolved_type.name == "Int"
    assert isinstance(ir_expression, BinaryIR)
    assert ir_expression.value_type.canonical_name == "Int"


def test_invalid_arithmetic_reports_s2105() -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = text + 1\n",
        path="scalar.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)
    expression = _select_expression(parse_result.ast, 0)

    assert _diagnostics(semantic) == [
        (
            "PIE-S2105",
            "Invalid operands for operator +: expected numeric operands",
        )
    ]
    _assert_diagnostic_span(semantic.diagnostics[0], expression)


@pytest.mark.parametrize(
    "body",
    [
        "    select:\n        value = missing + 1\n",
        "    where missing and true\n    select:\n        text\n",
        "    where missing between 1 and 5\n    select:\n        text\n",
    ],
)
def test_unknown_children_suppress_s2105_cascades(body: str) -> None:
    parse_result = parse_source(
        SOURCE_PREFIX + "table validated:\n    from rows\n" + body,
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic = analyze(parse_result.ast)

    assert _diagnostics(semantic) == [("PIE-S2102", "Unknown field: missing")]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in semantic.diagnostics]


def test_division_remains_semantically_deferred_without_s2105() -> None:
    script = _parse(
        SOURCE_PREFIX + "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        value = count / 2\n"
    )
    expression = _select_expression(script, 0)

    semantic = analyze(script)
    value_type = semantic.model.expression_value_types[expression]

    assert semantic.diagnostics == ()
    assert isinstance(expression, BinaryExpr)
    assert value_type.kind is ValueTypeKind.UNKNOWN
    assert value_type.resolved_type.kind is TypeKind.UNKNOWN


def test_existing_unqualified_sql_bytes_remain_stable() -> None:
    _, _, script_ir = _compile(
        SOURCE_PREFIX + "table selected:\n    from rows\n    select:\n        text\n"
    )

    postgres = emit_postgres_sql(script_ir)
    mysql = emit_mysql_sql(
        _compile(
            SOURCE_PREFIX + "table selected:\n"
            "    from mysql_rows\n"
            "    select:\n"
            "        text\n"
        )[2]
    )

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == 'SELECT\n    "text" AS "text"\nFROM "rows"'
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == "SELECT\n    `text` AS `text`\nFROM `rows`"


def test_qualified_sql_bytes_from_slice1_remain_stable() -> None:
    _, _, postgres_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from rows\n"
        "    where rows.active == true\n"
        "    select:\n"
        "        rows.text\n"
    )
    _, _, mysql_ir = _compile(
        SOURCE_PREFIX + "table selected:\n"
        "    from mysql_rows\n"
        "    where mysql_rows.active == true\n"
        "    select:\n"
        "        mysql_rows.text\n"
    )

    postgres = emit_postgres_sql(postgres_ir)
    mysql = emit_mysql_sql(mysql_ir)

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        'SELECT\n    "rows"."text" AS "text"\nFROM "rows" AS "rows"\n'
        'WHERE "rows"."active" = TRUE'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n    `mysql_rows`.`text` AS `text`\n"
        "FROM `rows` AS `mysql_rows`\n"
        "WHERE `mysql_rows`.`active` = TRUE"
    )


def test_relationship_metadata_does_not_participate_in_scalar_expression_binding() -> (
    None
):
    script, semantic, _ = _compile(
        SOURCE_PREFIX + "relationship membership:\n"
        "    endpoint member: rows\n"
        "    endpoint group: rows\n"
        "table selected:\n"
        "    from rows\n"
        "    where count > 1 and active == true\n"
        "    select:\n"
        "        value = count % 2\n"
    )

    assert len(semantic.model.relationships) == 1
    assert semantic.model.expression_value_types[
        _where_expression(script)
    ].resolved_type.name == ("Bool")
    assert semantic.model.expression_value_types[
        _select_expression(script, 0)
    ].resolved_type.name == ("Int")


def test_phase17_slice2_changes_no_grammar_or_generated_antlr() -> None:
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
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _relation(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )


def _where_expression(script: Script) -> Expression:
    relation = _relation(script)
    assert relation.where_clause is not None
    return relation.where_clause.expression


def _select_expression(script: Script, index: int) -> Expression:
    item = _relation(script).select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _diagnostics(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_diagnostic_span(diagnostic: Diagnostic, expression: Expression) -> None:
    assert diagnostic.location.path == expression.span.path
    assert diagnostic.location.line == expression.span.line
    assert diagnostic.location.column == expression.span.column
    assert diagnostic.location.end_line == expression.span.end_line
    assert diagnostic.location.end_column == expression.span.end_column


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
