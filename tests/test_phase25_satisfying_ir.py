from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.cli as cli
from pietto.ast_nodes import Node
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    IrResult,
    LiteralIR,
    NullabilityIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    ResultPredicateIR,
    RowSchemaIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

SOURCE_PREFIX = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
SPAN = SourceSpan(
    path="phase25-satisfying-ir.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
ORDERS = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
TEXT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
BOOL_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Bool",
    canonical_name="Bool",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


def test_result_predicate_ir_is_frozen_and_frontend_independent() -> None:
    predicate = ResultPredicateIR(expression=_amount_sum_gt_1000(), span=SPAN)

    assert isinstance(predicate.expression, ExpressionIR)
    assert predicate.span is SPAN
    _assert_no_frontend_objects(predicate)
    with pytest.raises(FrozenInstanceError):
        predicate.span = SPAN


def test_relation_ir_result_predicate_defaults_to_none_for_existing_builds() -> None:
    result, _semantic_result = _compile_ir(
        SOURCE_PREFIX + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
    )

    relation = _relation_ir(result, "revenue")
    assert relation.result_predicate is None


def test_constructed_ir_fixture_models_aggregate_alias_normalization_shape() -> None:
    """Constructed only; source alias normalization remains deferred."""

    predicate = ResultPredicateIR(expression=_amount_sum_gt_1000(), span=SPAN)
    relation = _constructed_relation(predicate)

    assert relation.result_predicate is predicate
    expression = relation.result_predicate.expression
    assert isinstance(expression, ComparisonIR)
    left = expression.left
    assert isinstance(left, AggregateCallIR)
    assert left.function == "sum"
    assert len(left.arguments) == 1
    argument = left.arguments[0]
    assert isinstance(argument, FieldRefIR)
    assert argument.name == "amount"
    assert argument.field == FieldId(owner=ORDERS, name="amount")
    assert not (isinstance(left, FieldRefIR) and left.name == "total_amount")


def test_constructed_ir_fixture_models_group_key_alias_normalization_shape() -> None:
    """Constructed only; source alias normalization remains deferred."""

    predicate = ResultPredicateIR(expression=_region_ne_test(), span=SPAN)
    relation = _constructed_relation(predicate)

    assert relation.result_predicate is predicate
    expression = relation.result_predicate.expression
    assert isinstance(expression, ComparisonIR)
    left = expression.left
    assert isinstance(left, FieldRefIR)
    assert left.name == "region"
    assert left.name != "r"
    assert left.field == FieldId(owner=ORDERS, name="region")


def test_satisfying_source_still_fails_closed_and_does_not_lower_result_predicate() -> (
    None
):
    parse_result = parse_source(_valid_satisfying_source())
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert _errors(semantic_result) == [
        ("PIE-S2322", "`satisfying` IR/SQL lowering is deferred"),
    ]

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.ir is not None
    relation = _relation_ir(ir_result, "revenue")
    assert relation.result_predicate is None


def test_emit_sql_text_still_fails_before_ir_and_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2322 error: `satisfying` IR/SQL lowering is deferred" in captured.err


def test_emit_sql_json_still_fails_without_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "satisfying.pietto", _valid_satisfying_source())
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    assert result["ok"] is False
    assert result["artifacts"] == []
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2322"]


def _amount_sum_gt_1000() -> ComparisonIR:
    return ComparisonIR(
        left=AggregateCallIR(
            function="sum",
            arguments=(
                FieldRefIR(
                    name="amount",
                    qualifier=(),
                    field=FieldId(owner=ORDERS, name="amount"),
                    span=SPAN,
                    value_type=INT_NON_NULL,
                ),
            ),
            span=SPAN,
            value_type=INT_NULLABLE,
        ),
        operator=">",
        right=LiteralIR(value=1000, span=SPAN, value_type=INT_NON_NULL),
        span=SPAN,
        value_type=BOOL_NON_NULL,
    )


def _region_ne_test() -> ComparisonIR:
    return ComparisonIR(
        left=FieldRefIR(
            name="region",
            qualifier=(),
            field=FieldId(owner=ORDERS, name="region"),
            span=SPAN,
            value_type=TEXT_NON_NULL,
        ),
        operator="!=",
        right=LiteralIR(value="test", span=SPAN, value_type=TEXT_NON_NULL),
        span=SPAN,
        value_type=BOOL_NON_NULL,
    )


def _constructed_relation(predicate: ResultPredicateIR) -> RelationIR:
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, "revenue"),
        name="revenue",
        kind=RelationKindIR.TABLE,
        source=RelationSourceIR(target=ORDERS, name="orders", span=SPAN),
        filter=None,
        projections=(),
        row_schema=RowSchemaIR(fields=()),
        span=SPAN,
        result_predicate=predicate,
    )


def _valid_satisfying_source() -> str:
    return (
        SOURCE_PREFIX + "table revenue:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )


def _compile_ir(source: str) -> tuple[IrResult, SemanticResult]:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    assert _errors(semantic_result) == []
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result, semantic_result


def _relation_ir(result: IrResult, name: str) -> RelationIR:
    assert result.ir is not None
    matches = [
        definition
        for definition in result.ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("satisfying must still fail before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)


def _assert_no_frontend_objects(value: object, seen: set[int] | None = None) -> None:
    seen = set() if seen is None else seen
    identity = id(value)
    if identity in seen:
        return
    seen.add(identity)

    assert not isinstance(value, (Node, ParserRuleContext, Token))
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_frontend_objects(getattr(value, field.name), seen)
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_frontend_objects(key, seen)
            _assert_no_frontend_objects(item, seen)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            _assert_no_frontend_objects(item, seen)
