from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ComparisonIR,
    EnumIR,
    FieldRefIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    TypeKindIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"

READINESS_HEADER = (
    "enum Status:\n"
    "    draft\n"
    "    paid\n"
    "shape Event:\n"
    "    id: UUID not null\n"
    "    optional_id: UUID nullable\n"
    "    status: Status not null\n"
    "    optional_status: Status nullable\n"
    "    amount: Int not null\n"
)


def test_uuid_builtin_field_projection_and_nullability_readiness_is_locked() -> None:
    script = _parse(
        _source(
            "postgres.table",
            "id\n        optional_id",
        )
    )
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    for name, expected_nullability in (
        ("id", EffectiveNullability.NON_NULL),
        ("optional_id", EffectiveNullability.NULLABLE),
    ):
        _assert_semantic_type(
            schema.fields[name],
            TypeKind.BUILTIN,
            "UUID",
            expected_nullability,
        )
        _assert_semantic_type(
            result.model.expression_value_types[_select_expression(relation, name)],
            TypeKind.BUILTIN,
            "UUID",
            expected_nullability,
        )

    script_ir = _compile(
        _source(
            "postgres.table",
            "id\n        optional_id",
        )
    )
    projections = {
        projection.name: projection
        for projection in _relation_ir(script_ir).projections
    }
    for name, expected_nullability in (
        ("id", NullabilityIR.NON_NULL),
        ("optional_id", NullabilityIR.NULLABLE),
    ):
        expression = projections[name].expression
        assert isinstance(expression, FieldRefIR)
        assert expression.value_type.canonical_kind is TypeKindIR.BUILTIN
        assert expression.value_type.canonical_name == "UUID"
        assert expression.value_type.nullability is expected_nullability

    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            ('"id" AS "id"', '"optional_id" AS "optional_id"'),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            ("`id` AS `id`", "`optional_id` AS `optional_id`"),
        ),
    )
    for connector, emitter, fragments in cases:
        sql_result = emitter(
            _compile(
                _source(
                    connector,
                    "id\n        optional_id",
                )
            )
        )
        assert sql_result.diagnostics == ()
        for fragment in fragments:
            assert fragment in sql_result.artifacts[0].sql


def test_uuid_direct_field_aggregate_readiness_matrix_is_locked() -> None:
    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            ('COUNT("id") AS "known_ids"', 'COUNT(DISTINCT "id") AS "unique_ids"'),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            ("COUNT(`id`) AS `known_ids`", "COUNT(DISTINCT `id`) AS `unique_ids`"),
        ),
    )
    for connector, emitter, fragments in cases:
        script_ir = _compile(
            _source(
                connector,
                "known_ids = count(id)\n        unique_ids = count_distinct(id)",
            )
        )
        projections = {
            projection.name: projection
            for projection in _relation_ir(script_ir).projections
        }
        for name, expected_function in (
            ("known_ids", "count"),
            ("unique_ids", "count_distinct"),
        ):
            aggregate = projections[name].expression
            assert isinstance(aggregate, AggregateCallIR)
            assert aggregate.function == expected_function
            assert aggregate.value_type.canonical_kind is TypeKindIR.BUILTIN
            assert aggregate.value_type.canonical_name == "Int"
            assert aggregate.value_type.nullability is NullabilityIR.NON_NULL
            assert len(aggregate.arguments) == 1
            argument = aggregate.arguments[0]
            assert isinstance(argument, FieldRefIR)
            assert argument.value_type.canonical_name == "UUID"

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        for fragment in fragments:
            assert fragment in sql_result.artifacts[0].sql

    for projection in (
        "value = min(id)",
        "value = max(id)",
        "value = sum(id)",
        "value = avg(id)",
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert _error_codes(result)
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_uuid_deferred_literals_casts_and_comparison_posture_is_locked() -> None:
    result = analyze(
        _parse(
            _source(
                "postgres.table",
                "same = id == optional_id",
            )
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, "same")

    assert _error_codes(result) == []
    _assert_semantic_type(
        result.model.relation_row_schemas[relation].fields["same"],
        TypeKind.BUILTIN,
        "Bool",
        EffectiveNullability.UNKNOWN,
    )
    _assert_semantic_type(
        result.model.expression_value_types[expression],
        TypeKind.BUILTIN,
        "Bool",
        EffectiveNullability.UNKNOWN,
    )
    comparison = (
        _relation_ir(
            _compile(
                _source(
                    "postgres.table",
                    "same = id == optional_id",
                )
            )
        )
        .projections[0]
        .expression
    )
    assert isinstance(comparison, ComparisonIR)

    for projection in (
        'value = UUID("00000000-0000-0000-0000-000000000000")',
        "value = cast(id)",
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        expression = _select_expression(relation, "value")
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert "PIE-S2103" in _error_codes(result)
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.UNKNOWN
        )


def test_enum_metadata_and_field_projection_readiness_is_locked() -> None:
    script = _parse(
        _source(
            "postgres.table",
            "status\n        optional_status",
        )
    )
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    for name, expected_nullability in (
        ("status", EffectiveNullability.NON_NULL),
        ("optional_status", EffectiveNullability.NULLABLE),
    ):
        _assert_semantic_type(
            schema.fields[name],
            TypeKind.ENUM,
            "Status",
            expected_nullability,
        )
        _assert_semantic_type(
            result.model.expression_value_types[_select_expression(relation, name)],
            TypeKind.ENUM,
            "Status",
            expected_nullability,
        )

    script_ir = _compile(
        _source(
            "postgres.table",
            "status\n        optional_status",
        )
    )
    enum_defs = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, EnumIR)
    ]
    assert len(enum_defs) == 1
    assert enum_defs[0].name == "Status"
    assert enum_defs[0].members == ("draft", "paid")
    projections = {
        projection.name: projection
        for projection in _relation_ir(script_ir).projections
    }
    for name, expected_nullability in (
        ("status", NullabilityIR.NON_NULL),
        ("optional_status", NullabilityIR.NULLABLE),
    ):
        expression = projections[name].expression
        assert isinstance(expression, FieldRefIR)
        assert expression.value_type.canonical_kind is TypeKindIR.ENUM
        assert expression.value_type.canonical_name == "Status"
        assert expression.value_type.nullability is expected_nullability

    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            ('"status" AS "status"', '"optional_status" AS "optional_status"'),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            ("`status` AS `status`", "`optional_status` AS `optional_status`"),
        ),
    )
    for connector, emitter, fragments in cases:
        sql_result = emitter(
            _compile(
                _source(
                    connector,
                    "status\n        optional_status",
                )
            )
        )
        assert sql_result.diagnostics == ()
        for fragment in fragments:
            assert fragment in sql_result.artifacts[0].sql

    assert '"Enum"' not in _read(CATALOG_PATH)


def test_enum_count_field_now_fails_closed_at_semantic_validation() -> None:
    for connector in ("postgres.table", "mysql.table"):
        script = _parse(
            _source(
                connector,
                "known_statuses = count(status)",
            )
        )
        semantic_result = analyze(script)
        ir_result = build_ir(script, semantic_result.model)

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert ir_result.ir is not None
        projection = _relation_ir(ir_result.ir).projections[0]
        assert not isinstance(projection.expression, AggregateCallIR)

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

        assert _error_codes(result)
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_enum_literal_cast_and_specific_comparison_boundaries_remain_absent() -> None:
    result = analyze(
        _parse(
            _source(
                "postgres.table",
                "same = status == optional_status",
            )
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, "same")

    assert _error_codes(result) == []
    _assert_semantic_type(
        result.model.relation_row_schemas[relation].fields["same"],
        TypeKind.BUILTIN,
        "Bool",
        EffectiveNullability.UNKNOWN,
    )
    _assert_semantic_type(
        result.model.expression_value_types[expression],
        TypeKind.BUILTIN,
        "Bool",
        EffectiveNullability.UNKNOWN,
    )
    comparison = (
        _relation_ir(
            _compile(
                _source(
                    "postgres.table",
                    "same = status == optional_status",
                )
            )
        )
        .projections[0]
        .expression
    )
    assert isinstance(comparison, ComparisonIR)

    bare_result = analyze(_parse(_source("postgres.table", "value = draft")))
    bare_relation = _relation(bare_result)
    bare_field = bare_result.model.relation_row_schemas[bare_relation].fields["value"]
    bare_expression = _select_expression(bare_relation, "value")
    assert bare_field.resolved_type.kind is TypeKind.UNKNOWN
    assert bare_result.model.expression_value_types[bare_expression].kind is (
        ValueTypeKind.UNKNOWN
    )

    for projection, expected_code in (
        ("value = Status.draft", "PIE-S2102"),
        ('value = Status("draft")', "PIE-S2103"),
        ("value = cast(status)", "PIE-S2103"),
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        expression = _select_expression(relation, "value")
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert expected_code in _error_codes(result)
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.UNKNOWN
        )


def test_static_audit_no_uuid_enum_runtime_metadata_or_output_surface_was_added() -> (
    None
):
    catalog = _read(CATALOG_PATH)
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)
    sql_api = _read(SQL_API_PATH)
    cli_json = _read(CLI_JSON_PATH)

    assert '"UUID"' in catalog
    assert '"Enum"' not in catalog
    assert 'ENUM = "enum"' in semantic_model
    assert "class EnumIR" in ir_model
    for forbidden in (
        'BuiltinFunction("UUID"',
        'BuiltinFunction("Enum"',
        'BuiltinFunction("Status"',
        'BuiltinFunction("cast"',
        'BuiltinFunction("uuid"',
        'BuiltinFunction("enum"',
    ):
        assert forbidden not in catalog

    for model_source in (semantic_model, ir_model):
        for forbidden in (
            "uuid_literal",
            "enum_literal",
            "native_database",
            "native_db",
            "database_metadata",
            "storage_metadata",
            "ddl_metadata",
            "uuid_storage",
            "enum_storage",
        ):
            assert forbidden not in model_source.lower()

    for renderer_source in (postgres, mysql):
        assert "_SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES = frozenset(" in (
            renderer_source
        )
        assert '"UUID"' in renderer_source
        assert '"Int", "Float", "Decimal", "Date", "Timestamp"' in renderer_source
        assert "concrete non-Any field arguments" in renderer_source
        for forbidden in (
            "enum aggregate",
            "enum storage",
            "native enum",
            "native uuid",
            "uuid literal",
            "enum literal",
            "uuid cast",
            "enum cast",
            "CREATE TYPE",
            "UUID(",
        ):
            assert forbidden.lower() not in renderer_source.lower()

    assert "emit_mysql_sql" not in sql_api
    assert '"types"' not in cli_json
    assert '"type_output"' not in cli_json


def _source(connector: str, projections: str) -> str:
    return (
        READINESS_HEADER
        + f'source events: Event is {connector}("events")\n'
        + "table projected:\n"
        + "    from events\n"
        + "    select:\n"
        + f"        {projections}\n"
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


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
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
        if item.alias is None and getattr(item.expression, "name", None) == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_semantic_type(
    value_type: object,
    expected_kind: TypeKind,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").kind is expected_kind
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
