from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ComparisonIR,
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
PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"

EVENT_SHAPE = (
    "shape Event:\n"
    "    category: Text not null\n"
    "    event_date: Date nullable\n"
    "    required_event_date: Date not null\n"
    "    created_at: Timestamp not null\n"
    "    optional_created_at: Timestamp nullable\n"
    "    amount: Int not null\n"
)


def test_phase31_slice4_plan_and_spec_lock_tests_static_audit_scope() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    combined = f"{plan} {spec}"

    for required in (
        "Phase 31 Slice 4 is complete as Date / Timestamp SQL compatibility "
        "audit, tests, static audit, and status work only",
        "Slice 4 is complete. Slices 5 through 8 are planned only",
        "Phase 29 aggregate freeze remains active",
        "Phase 30 Date/Timestamp contracts are carried forward",
        "Direct-field `min(Date)`, `max(Date)`, `min(Timestamp)`, and "
        "`max(Timestamp)` remain current accepted behavior",
        "`count(Date)`, `count(Timestamp)`, `count_distinct(Date)`, and "
        "`count_distinct(Timestamp)` remain current direct-field accepted "
        "behavior",
        "Date/Timestamp comparisons remain current generic known-child "
        "comparison behavior producing `Bool UNKNOWN`",
        "not a Date/Timestamp-specific comparison compatibility matrix",
        "SQL renderers add no casts, temporal functions, timezone terms, "
        "precision terms, or native database metadata",
    ):
        assert required in combined

    for forbidden in (
        "behavior fix",
        "new SQL dialect behavior",
        "aggregate expansion",
        "v0.2 completion declaration in Slice 4",
        "Phase 32 implementation",
        "Slice 5 work",
        "DateTime primitive or alias",
        "Time type",
        "Interval type",
        "timezone semantics",
        "Date/Timestamp literal implementation",
        "temporal arithmetic implementation",
        "temporal function implementation",
        "timestamp precision modeling",
        "native database metadata",
    ):
        assert forbidden in combined


def test_semantic_date_timestamp_field_and_nullability_matrix_is_locked() -> None:
    result = analyze(
        _parse(
            _projected_source(
                "postgres.table",
                "event_date\n"
                "        required_event_date\n"
                "        created_at\n"
                "        optional_created_at",
            )
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    expected = {
        "event_date": ("Date", EffectiveNullability.NULLABLE),
        "required_event_date": ("Date", EffectiveNullability.NON_NULL),
        "created_at": ("Timestamp", EffectiveNullability.NON_NULL),
        "optional_created_at": ("Timestamp", EffectiveNullability.NULLABLE),
    }
    for name, (expected_type, expected_nullability) in expected.items():
        _assert_semantic_type(schema.fields[name], expected_type, expected_nullability)
        expression = _select_expression(relation, name)
        _assert_semantic_type(
            result.model.expression_value_types[expression],
            expected_type,
            expected_nullability,
        )
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.KNOWN
        )


def test_semantic_date_timestamp_extrema_matrix_is_locked() -> None:
    source = _projected_source(
        "postgres.table",
        "first_event_date = min(event_date)\n"
        "        latest_event_date = max(event_date)\n"
        "        first_created_at = min(created_at)\n"
        "        latest_created_at = max(created_at)\n"
        "        first_qualified_date = min(events.event_date)\n"
        "        latest_qualified_created = max(events.created_at)",
    )
    script = _parse(source)
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    for name, expected_type in (
        ("first_event_date", "Date"),
        ("latest_event_date", "Date"),
        ("first_created_at", "Timestamp"),
        ("latest_created_at", "Timestamp"),
        ("first_qualified_date", "Date"),
        ("latest_qualified_created", "Timestamp"),
    ):
        _assert_semantic_type(
            schema.fields[name],
            expected_type,
            EffectiveNullability.NULLABLE,
        )
        _assert_semantic_type(
            result.model.expression_value_types[_select_expression(relation, name)],
            expected_type,
            EffectiveNullability.NULLABLE,
        )

    unsupported = analyze(
        _parse(
            _projected_source(
                "postgres.table",
                "value = min(event_date == event_date)",
            )
        )
    )
    assert _error_codes(unsupported)
    unsupported_relation = _relation(unsupported)
    unsupported_field = unsupported.model.relation_row_schemas[
        unsupported_relation
    ].fields["value"]
    assert unsupported_field.resolved_type.kind is TypeKind.UNKNOWN
    assert unsupported_field.nullability is EffectiveNullability.UNKNOWN


def test_ir_date_timestamp_extrema_aggregate_calls_match_semantics() -> None:
    for grouped in (False, True):
        script_ir = _compile(_extrema_source("postgres.table", grouped=grouped))
        relation = _relation_ir(script_ir)
        projections = {
            projection.name: projection for projection in relation.projections
        }

        if grouped:
            assert [key.name for key in relation.group_keys] == ["category"]

        _assert_aggregate(
            projections["first_event_date"].expression,
            "min",
            "Date",
            ("event_date",),
        )
        _assert_aggregate(
            projections["latest_event_date"].expression,
            "max",
            "Date",
            ("event_date",),
        )
        _assert_aggregate(
            projections["first_created_at"].expression,
            "min",
            "Timestamp",
            ("created_at",),
        )
        _assert_aggregate(
            projections["latest_created_at"].expression,
            "max",
            "Timestamp",
            ("created_at",),
        )


def test_postgres_and_private_mysql_date_timestamp_extrema_sql_is_stable() -> None:
    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                'MIN("event_date") AS "first_event_date"',
                'MAX("event_date") AS "latest_event_date"',
                'MIN("created_at") AS "first_created_at"',
                'MAX("created_at") AS "latest_created_at"',
                'MIN("events"."event_date") AS "first_qualified_date"',
                'MAX("events"."created_at") AS "latest_qualified_created"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "MIN(`event_date`) AS `first_event_date`",
                "MAX(`event_date`) AS `latest_event_date`",
                "MIN(`created_at`) AS `first_created_at`",
                "MAX(`created_at`) AS `latest_created_at`",
                "MIN(`events`.`event_date`) AS `first_qualified_date`",
                "MAX(`events`.`created_at`) AS `latest_qualified_created`",
            ),
        ),
    )

    for connector, emitter, expected_fragments in cases:
        result = emitter(_compile(_extrema_source(connector, grouped=False)))

        assert result.diagnostics == ()
        assert len(result.artifacts) == 1
        sql = result.artifacts[0].sql
        for fragment in expected_fragments:
            assert fragment in sql
        for forbidden in (
            "CAST(",
            "::",
            "AT TIME ZONE",
            "DATE_TRUNC",
            "EXTRACT(",
            "INTERVAL",
            "DATETIME",
            "TIMESTAMP(",
            "TIMEZONE",
            "PRECISION",
        ):
            assert forbidden not in sql.upper()


def test_date_timestamp_count_and_count_distinct_current_behavior_is_locked() -> None:
    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                'COUNT("event_date") AS "count_date"',
                'COUNT("created_at") AS "count_timestamp"',
                'COUNT(DISTINCT "event_date") AS "unique_date"',
                'COUNT(DISTINCT "created_at") AS "unique_timestamp"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "COUNT(`event_date`) AS `count_date`",
                "COUNT(`created_at`) AS `count_timestamp`",
                "COUNT(DISTINCT `event_date`) AS `unique_date`",
                "COUNT(DISTINCT `created_at`) AS `unique_timestamp`",
            ),
        ),
    )

    for connector, emitter, expected_fragments in cases:
        result = emitter(
            _compile(
                _projected_source(
                    connector,
                    "count_date = count(event_date)\n"
                    "        count_timestamp = count(created_at)\n"
                    "        unique_date = count_distinct(event_date)\n"
                    "        unique_timestamp = count_distinct(created_at)",
                )
            )
        )

        assert result.diagnostics == ()
        sql = result.artifacts[0].sql
        for fragment in expected_fragments:
            assert fragment in sql


def test_date_timestamp_generic_comparison_posture_is_locked() -> None:
    result = analyze(
        _parse(
            _projected_source(
                "postgres.table",
                "same_date = event_date == event_date\n"
                "        before_created = created_at < created_at",
            )
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    for name in ("same_date", "before_created"):
        expression = _select_expression(relation, name)
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.KNOWN
        )
        _assert_semantic_type(
            schema.fields[name],
            "Bool",
            EffectiveNullability.UNKNOWN,
        )
        _assert_semantic_type(
            result.model.expression_value_types[expression],
            "Bool",
            EffectiveNullability.UNKNOWN,
        )

    script_ir = _compile(
        _projected_source(
            "postgres.table",
            "same_date = event_date == event_date\n"
            "        before_created = created_at < created_at",
        )
    )
    projections = {
        projection.name: projection
        for projection in _relation_ir(script_ir).projections
    }
    assert isinstance(projections["same_date"].expression, ComparisonIR)
    assert isinstance(projections["before_created"].expression, ComparisonIR)

    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"
    assert (
        "current generic known-child comparison behavior producing `Bool UNKNOWN`"
        in combined
    )
    assert "not a Date/Timestamp-specific comparison compatibility matrix" in combined


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = event_date + 1", "PIE-S2105"),
        ("value = created_at + 1", "PIE-S2105"),
        ("value = event_date - event_date", "PIE-S2105"),
        ("value = created_at - created_at", "PIE-S2105"),
        ('value = Date("2024-01-01")', "PIE-S2103"),
        ('value = Timestamp("2024-01-01T00:00:00")', "PIE-S2103"),
    ],
)
def test_temporal_arithmetic_literals_and_functions_fail_closed(
    projection: str,
    expected_code: str,
) -> None:
    result = analyze(_parse(_projected_source("postgres.table", projection)))
    relation = _relation(result)
    expression = _select_expression(relation, "value")
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert expected_code in _error_codes(result)
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize("type_name", ["DateTime", "Time", "Interval"])
def test_temporal_type_names_remain_unsupported(type_name: str) -> None:
    result = analyze(
        _parse(
            "shape TemporalBoundary:\n"
            f"    value: {type_name} not null\n"
            'source events: TemporalBoundary is postgres.table("events")\n'
            "table projected:\n"
            "    from events\n"
            "    select:\n"
            "        value\n"
        )
    )
    relation = _relation(result)
    source_schema = next(iter(result.model.source_row_schemas.values()))
    expression = _select_expression(relation, "value")

    assert "PIE-S2002" in _error_codes(result)
    assert source_schema.fields["value"].resolved_type.kind is TypeKind.UNKNOWN
    assert source_schema.fields["value"].resolved_type.name == type_name
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


def test_static_audit_no_temporal_runtime_or_metadata_surface_was_added() -> None:
    catalog = _read(CATALOG_PATH)
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)
    sql_api = _read(SQL_API_PATH)
    cli_json = _read(CLI_JSON_PATH)
    combined_docs = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    assert '"Date"' in catalog
    assert '"Timestamp"' in catalog
    for forbidden in ('"DateTime"', '"Time"', '"Interval"'):
        assert forbidden not in catalog
    for forbidden in (
        'BuiltinFunction("Date"',
        'BuiltinFunction("Timestamp"',
        'BuiltinFunction("DateTime"',
        'BuiltinFunction("Time"',
        'BuiltinFunction("Interval"',
        'BuiltinFunction("timezone"',
        'BuiltinFunction("cast"',
    ):
        assert forbidden not in catalog

    for model_source in (semantic_model, ir_model):
        for forbidden in (
            "timezone",
            "time_zone",
            "precision",
            "native_database",
            "native_db",
            "database_metadata",
            "temporal_metadata",
        ):
            assert forbidden not in model_source

    for renderer_source in (postgres, mysql):
        assert (
            "_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES = frozenset("
            in renderer_source
        )
        assert '"Date", "Timestamp"' in renderer_source
        for forbidden in (
            "AT TIME ZONE",
            "DATE_TRUNC",
            "EXTRACT(",
            "TIMESTAMP(",
            "DATETIME",
            "INTERVAL",
            "timezone",
            "precision",
            "native_database",
            "native_db",
        ):
            assert forbidden not in renderer_source

    assert "emit_mysql_sql" not in sql_api
    assert '"types"' not in cli_json
    assert '"type_output"' not in cli_json
    for required in (
        "DateTime, Time, Interval, or timezone semantics",
        "no Date/Timestamp literal implementation",
        "no temporal arithmetic implementation",
        "no temporal function implementation",
        "no timestamp precision modeling",
        "no native database metadata",
        "no public MySQL API expansion",
    ):
        assert required in combined_docs


def _projected_source(connector: str, projections: str) -> str:
    return (
        EVENT_SHAPE
        + f'source events: Event is {connector}("events")\n'
        + "table projected:\n"
        + "    from events\n"
        + "    select:\n"
        + f"        {projections}\n"
    )


def _extrema_source(connector: str, *, grouped: bool) -> str:
    projections = (
        "        category\n"
        "        first_event_date = min(event_date)\n"
        "        latest_event_date = max(event_date)\n"
        "        first_created_at = min(created_at)\n"
        "        latest_created_at = max(created_at)\n"
        if grouped
        else "        first_event_date = min(event_date)\n"
        "        latest_event_date = max(event_date)\n"
        "        first_created_at = min(created_at)\n"
        "        latest_created_at = max(created_at)\n"
        "        first_qualified_date = min(events.event_date)\n"
        "        latest_qualified_created = max(events.created_at)\n"
    )
    group_by = "    group by:\n        category\n" if grouped else ""
    return (
        EVENT_SHAPE
        + f'source events: Event is {connector}("events")\n'
        + "table extrema:\n"
        + "    from events\n"
        + group_by
        + "    select:\n"
        + projections
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
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _assert_aggregate(
    expression: object,
    function: str,
    expected_type: str,
    expected_field_names: tuple[str, ...],
) -> None:
    assert isinstance(expression, AggregateCallIR)
    assert expression.function == function
    assert expression.value_type.canonical_kind is TypeKindIR.BUILTIN
    assert expression.value_type.canonical_name == expected_type
    assert expression.value_type.nullability is NullabilityIR.NULLABLE
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, FieldRefIR)
    assert argument.field is not None
    assert (".".join((*argument.qualifier, argument.name)),) == expected_field_names


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())
