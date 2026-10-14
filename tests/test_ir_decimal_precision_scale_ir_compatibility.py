from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import fields
from pathlib import Path

from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import SemanticMetadataType
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryResult,
    ProjectRoot,
)
from pietto.ast_nodes import FieldDef, Script, ShapeDef
from pietto.ir import (
    AggregateCallIR,
    ExpressionIR,
    FieldRefIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.semantic.model import DecimalPrecisionScale
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

_FORBIDDEN_PUBLIC_OUTPUT_TOKENS = ("DECIMAL(", "NUMERIC(", "precision", "scale")


def test_decimal_precision_scale_ir_type_refs_remain_logical_decimal() -> None:
    script, semantic_result, script_ir = _compile(_source("postgres.table"))

    fields_by_name = _shape_fields(script, "Order")
    assert semantic_result.model.decimal_precision_scale_for(
        fields_by_name["direct"].type_expr
    ) == DecimalPrecisionScale(12, 2)
    assert semantic_result.model.decimal_precision_scale_for(
        fields_by_name["money"].type_expr
    ) == DecimalPrecisionScale(12, 2)
    assert semantic_result.model.decimal_precision_scale_for(
        fields_by_name["price"].type_expr
    ) == DecimalPrecisionScale(12, 2)
    assert (
        semantic_result.model.decimal_precision_scale_for(
            fields_by_name["plain"].type_expr
        )
        is None
    )
    assert (
        semantic_result.model.decimal_precision_scale_for(
            fields_by_name["empty"].type_expr
        )
        is None
    )

    assert {"precision", "scale"}.isdisjoint(
        {field.name for field in fields(TypeRefIR)}
    )
    source_ir = _source_ir(script_ir, "orders")
    source_fields = {field.name: field for field in source_ir.row_schema.fields}

    _assert_decimal_type_ref(
        source_fields["direct"].type_ref,
        declared_name="Decimal",
        nullability=NullabilityIR.NON_NULL,
    )
    _assert_decimal_type_ref(
        source_fields["money"].type_ref,
        declared_name="Money",
        nullability=NullabilityIR.NON_NULL,
    )
    _assert_decimal_type_ref(
        source_fields["price"].type_ref,
        declared_name="Price",
        nullability=NullabilityIR.NULLABLE,
    )
    _assert_decimal_type_ref(
        source_fields["plain"].type_ref,
        declared_name="Decimal",
        nullability=NullabilityIR.NON_NULL,
    )
    _assert_decimal_type_ref(
        source_fields["empty"].type_ref,
        declared_name="Decimal",
        nullability=NullabilityIR.NULLABLE,
    )

    projected = _relation_ir(script_ir, "order_projection")
    projected_fields = {field.name: field for field in projected.row_schema.fields}
    for field_name, declared_name in (
        ("direct", "Decimal"),
        ("money", "Money"),
        ("price", "Price"),
        ("plain", "Decimal"),
        ("empty", "Decimal"),
    ):
        _assert_decimal_type_ref(
            projected_fields[field_name].type_ref,
            declared_name=declared_name,
            nullability=source_fields[field_name].nullability,
        )


def test_decimal_precision_scale_aggregate_ir_and_sql_remain_unchanged() -> None:
    for connector, emitter in (
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ):
        _, _, script_ir = _compile(_source(connector))
        totals = _relation_ir(script_ir, "order_totals")
        projections = {projection.name: projection for projection in totals.projections}

        for projection_name, function_name in (
            ("direct_total", "sum"),
            ("direct_average", "avg"),
        ):
            expression = projections[projection_name].expression
            assert isinstance(expression, AggregateCallIR)
            assert expression.function == function_name
            assert len(expression.arguments) == 1
            assert isinstance(expression.arguments[0], FieldRefIR)
            _assert_decimal_type_ref(
                expression.value_type,
                declared_name="Decimal",
                nullability=NullabilityIR.NULLABLE,
            )
            _assert_decimal_type_ref(
                expression.arguments[0].value_type,
                declared_name="Decimal",
                nullability=NullabilityIR.NON_NULL,
            )

        for field in totals.row_schema.fields:
            _assert_decimal_type_ref(
                field.type_ref,
                declared_name="Decimal",
                nullability=NullabilityIR.NULLABLE,
            )

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        assert len(sql_result.artifacts) == 2
        _assert_public_text_has_no_precision_scale(
            "\n".join(artifact.sql for artifact in sql_result.artifacts)
        )


def test_alias_decimal_aggregate_boundary_remains_existing_fail_closed() -> None:
    parse_result = parse_source(
        _source("postgres.table").replace(
            "direct_average = avg(direct)",
            "money_average = avg(money)",
        ),
        path="slice4.pietto",
    )
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)

    assert [diagnostic.code for diagnostic in semantic_result.diagnostics] == [
        "PIE-S2314"
    ]
    assert "Money" in semantic_result.diagnostics[0].message


def test_decimal_precision_scale_public_json_and_metadata_shapes_are_unchanged() -> (
    None
):
    script, semantic_result, script_ir = _compile(_source("postgres.table"))
    sql_result = emit_postgres_sql(script_ir)
    assert sql_result.diagnostics == ()

    check_json = cli_json.check_result_to_json_dict(
        path="slice4.pietto",
        diagnostics=(),
        cli_errors=(),
    )
    emit_json = cli_json.emit_sql_result_to_json_dict(
        path="slice4.pietto",
        dialect="postgres",
        diagnostics=(),
        cli_errors=(),
        artifacts=sql_result.artifacts,
    )
    project_json = project_check_result_to_json_dict(
        ProjectDiscoveryResult(
            root=ProjectRoot(path="."),
            config_path=ProjectConfigPath(path="pietto.toml"),
            inputs=(),
            errors=(),
        )
    )
    artifact = build_semantic_metadata_artifact(
        path="slice4.pietto",
        script=script,
        semantic_result=semantic_result,
        ir=script_ir,
        diagnostics=(),
    )
    metadata_json = semantic_metadata_artifact_to_json_dict(artifact)

    for document in (check_json, emit_json, project_json, metadata_json):
        _assert_public_text_has_no_precision_scale(json.dumps(document))

    assert {"precision", "scale"}.isdisjoint(
        {field.name for field in fields(SemanticMetadataType)}
    )
    metadata_types = artifact.metadata.types
    assert any(
        metadata_type.name == "Money"
        and metadata_type.canonical_name == "Decimal"
        and metadata_type.nullability == "non_null"
        for metadata_type in metadata_types
    )
    assert any(
        metadata_type.name == "Price"
        and metadata_type.canonical_name == "Decimal"
        and metadata_type.nullability == "nullable"
        for metadata_type in metadata_types
    )


def test_ir_layer_does_not_consume_decimal_precision_scale_carrier() -> None:
    ir_text = " ".join(
        (path).read_text(encoding="utf-8")
        for path in (
            _repo_file("src/pietto/ir/model.py"),
            _repo_file("src/pietto/ir/builder.py"),
            _repo_file("src/pietto/ir/lowering.py"),
        )
    )

    for forbidden in (
        "DecimalPrecisionScale",
        "decimal_precision_scales",
        "decimal_precision_scale_for",
    ):
        assert forbidden not in ir_text

    lowering_text = _repo_file("src/pietto/ir/lowering.py").read_text(encoding="utf-8")
    for required in ("type_resolutions", "type_expansions", "type_nullability"):
        assert required in lowering_text


def _source(connector: str) -> str:
    return (
        "type Money = Decimal(12, 2) not null\n"
        "type Price = Money nullable\n"
        "shape Order:\n"
        "    direct: Decimal(12, 2) not null\n"
        "    money: Money not null\n"
        "    price: Price nullable\n"
        "    plain: Decimal not null\n"
        "    empty: Decimal() nullable\n"
        f'source orders: Order is {connector}("orders")\n'
        "table order_projection:\n"
        "    from orders\n"
        "    select:\n"
        "        direct\n"
        "        money\n"
        "        price\n"
        "        plain\n"
        "        empty\n"
        "table order_totals:\n"
        "    from orders\n"
        "    select:\n"
        "        direct_total = sum(direct)\n"
        "        direct_average = avg(direct)\n"
    )


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path="slice4.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return parse_result.ast, semantic_result, ir_result.ir


def _shape_fields(script: Script, name: str) -> dict[str, FieldDef]:
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef) and definition.name == name
    )
    return {field.name: field for field in shape.fields}


def _source_ir(script_ir: ScriptIR, name: str) -> SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR) and definition.name == name
    )


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _assert_decimal_type_ref(
    type_ref: TypeRefIR,
    *,
    declared_name: str,
    nullability: NullabilityIR,
) -> None:
    assert type_ref.declared_name == declared_name
    assert type_ref.canonical_name == "Decimal"
    assert type_ref.kind in {TypeKindIR.BUILTIN, TypeKindIR.TYPE_ALIAS}
    assert type_ref.canonical_kind is TypeKindIR.BUILTIN
    assert type_ref.nullability is nullability
    assert not hasattr(type_ref, "precision")
    assert not hasattr(type_ref, "scale")


def _assert_public_text_has_no_precision_scale(text: str) -> None:
    for forbidden in _FORBIDDEN_PUBLIC_OUTPUT_TOKENS:
        assert forbidden not in text, forbidden


def _walk_expressions(expression: ExpressionIR) -> Iterable[ExpressionIR]:
    yield expression
    if isinstance(expression, AggregateCallIR):
        for argument in expression.arguments:
            yield from _walk_expressions(argument)


def _all_relation_expressions(relation: RelationIR) -> Iterable[ExpressionIR]:
    for projection in relation.projections:
        yield from _walk_expressions(projection.expression)


def _repo_file(relative_path: str) -> Path:
    return Path(__file__).resolve().parents[1] / relative_path
