from __future__ import annotations

from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Callable

from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import (
    SemanticMetadataAggregate,
    SemanticMetadataArtifact,
    SemanticMetadataFieldLeaf,
    SemanticMetadataRelation,
)
from pietto.ast_nodes import Node, Script
from pietto.errors import Severity
from pietto.ir import FieldId, ScriptIR, SymbolId, build_ir
from pietto.ir.model import DefinitionIR, ExpressionIR
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, SemanticResult, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
STATUS_DOCS = (
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs/spec/pietto-v0.9.md",
)

SOURCE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    created_at: Timestamp nullable\n"
    'source orders: Order is postgres.table("slice5_secret_orders")\n'
    "relationship order_link:\n"
    "    endpoint left: orders\n"
    "    endpoint right: orders\n"
    "table stats:\n"
    "    from orders\n"
    "    where created_at is not null\n"
    "    group by:\n"
    "        status\n"
    "    select:\n"
    "        status\n"
    "        rows = count()\n"
    "        known_amounts = count(amount)\n"
    "        statuses = count_distinct(lower(trim(status)))\n"
    "        total = sum(amount + tax)\n"
    "        weighted = avg(score * weight)\n"
    "        first_seen = min(created_at)\n"
    "        last_seen = max(created_at)\n"
    "    satisfying:\n"
    "        total > 0\n"
    "    order by:\n"
    "        total desc\n"
    "        status asc\n"
    "    limit 5\n"
    "table sorted_orders:\n"
    "    from orders\n"
    "    select:\n"
    "        amount\n"
    "    order by:\n"
    "        amount desc\n"
    "query report:\n"
    "    from stats\n"
    "    select:\n"
    "        status\n"
    "        total\n"
    "    order by:\n"
    "        total desc\n"
)


def test_query_posture_metadata_covers_where_group_satisfying_order_and_limit() -> None:
    artifact, _, _, _ = _artifact(SOURCE, path="slice5-query.pietto")
    stats = _relation(artifact, "stats")

    assert stats.query.where.present is True
    _assert_leaves(
        stats.query.group_keys,
        [("orders", "status", ())],
    )
    assert all(leaf.location is not None for leaf in stats.query.group_keys)
    assert stats.query.satisfying.present is True

    assert [
        (item.scope, item.direction, item.expression_kind)
        for item in stats.query.order_by
    ] == [
        ("grouped_result", "DESC", "aggregate_call"),
        ("grouped_result", "ASC", "field_ref"),
    ]
    _assert_leaves(
        stats.query.order_by[0].field_leaves,
        [("orders", "amount", ()), ("orders", "tax", ())],
    )
    _assert_leaves(
        stats.query.order_by[1].field_leaves,
        [("orders", "status", ())],
    )
    assert all(item.location is not None for item in stats.query.order_by)

    assert stats.query.limit is not None
    assert stats.query.limit.value == 5
    assert stats.query.limit.location is not None


def test_non_grouped_order_by_metadata_uses_input_scope() -> None:
    artifact, _, _, _ = _artifact(SOURCE)
    sorted_orders = _relation(artifact, "sorted_orders")
    report = _relation(artifact, "report")

    assert sorted_orders.query.where.present is False
    assert sorted_orders.query.group_keys == ()
    assert sorted_orders.query.satisfying.present is False
    assert sorted_orders.query.limit is None
    assert [
        (item.scope, item.direction, item.expression_kind)
        for item in sorted_orders.query.order_by
    ] == [("input", "DESC", "field_ref")]
    _assert_leaves(
        sorted_orders.query.order_by[0].field_leaves,
        [("orders", "amount", ())],
    )

    assert [
        (item.scope, item.direction, item.expression_kind)
        for item in report.query.order_by
    ] == [("input", "DESC", "field_ref")]
    _assert_leaves(
        report.query.order_by[0].field_leaves,
        [("stats", "total", ())],
    )


def test_aggregate_metadata_covers_current_functions_arguments_results_and_locations() -> (
    None
):
    artifact, _, _, _ = _artifact(SOURCE)
    stats = _relation(artifact, "stats")

    assert [
        (
            aggregate.function,
            aggregate.projection_name,
            aggregate.result_type.canonical_name,
            aggregate.result_type.nullability,
            aggregate.location is not None,
        )
        for aggregate in stats.aggregates
    ] == [
        ("count", "rows", "Int", "non_null", True),
        ("count", "known_amounts", "Int", "non_null", True),
        ("count_distinct", "statuses", "Int", "non_null", True),
        ("sum", "total", "Int", "nullable", True),
        ("avg", "weighted", "Float", "nullable", True),
        ("min", "first_seen", "Timestamp", "nullable", True),
        ("max", "last_seen", "Timestamp", "nullable", True),
    ]

    aggregates = {
        aggregate.projection_name: aggregate for aggregate in stats.aggregates
    }
    assert aggregates["rows"].arguments == ()
    _assert_argument(
        aggregates["known_amounts"],
        expression_kind="field_ref",
        canonical_name="Int",
        nullability="non_null",
        leaves=[("orders", "amount", ())],
    )
    _assert_argument(
        aggregates["statuses"],
        expression_kind="call",
        canonical_name="Text",
        nullability="unknown",
        leaves=[("orders", "status", ())],
    )
    _assert_argument(
        aggregates["total"],
        expression_kind="bounded_expression",
        canonical_name="Int",
        nullability="unknown",
        leaves=[("orders", "amount", ()), ("orders", "tax", ())],
    )
    _assert_argument(
        aggregates["weighted"],
        expression_kind="bounded_expression",
        canonical_name="Float",
        nullability="unknown",
        leaves=[("orders", "score", ()), ("orders", "weight", ())],
    )
    _assert_argument(
        aggregates["first_seen"],
        expression_kind="field_ref",
        canonical_name="Timestamp",
        nullability="nullable",
        leaves=[("orders", "created_at", ())],
    )
    _assert_argument(
        aggregates["last_seen"],
        expression_kind="field_ref",
        canonical_name="Timestamp",
        nullability="nullable",
        leaves=[("orders", "created_at", ())],
    )


def test_basic_lineage_captures_bounded_direct_leaves_without_transitive_claims() -> (
    None
):
    artifact, _, _, _ = _artifact(SOURCE)
    stats = _relation(artifact, "stats")
    report = _relation(artifact, "report")

    stats_lineage = {item.output: item.field_leaves for item in stats.lineage}
    _assert_leaves(stats_lineage["status"], [("orders", "status", ())])
    _assert_leaves(stats_lineage["rows"], [])
    _assert_leaves(stats_lineage["known_amounts"], [("orders", "amount", ())])
    _assert_leaves(stats_lineage["statuses"], [("orders", "status", ())])
    _assert_leaves(
        stats_lineage["total"],
        [("orders", "amount", ()), ("orders", "tax", ())],
    )
    _assert_leaves(
        stats_lineage["weighted"],
        [("orders", "score", ()), ("orders", "weight", ())],
    )
    _assert_leaves(stats_lineage["first_seen"], [("orders", "created_at", ())])
    _assert_leaves(stats_lineage["last_seen"], [("orders", "created_at", ())])

    report_lineage = {item.output: item.field_leaves for item in report.lineage}
    _assert_leaves(report_lineage["status"], [("stats", "status", ())])
    _assert_leaves(report_lineage["total"], [("stats", "total", ())])
    assert ("orders", "amount", ()) not in _leaf_signature(report_lineage["total"])
    assert ("orders", "tax", ()) not in _leaf_signature(report_lineage["total"])


def test_metadata_exposes_no_raw_ast_semantic_ir_symbol_field_or_relationship_objects() -> (
    None
):
    artifact, _, semantic_result, _ = _artifact(SOURCE)

    assert semantic_result.model.relationships != ()
    _assert_no_raw_objects(artifact)

    strings = _strings(artifact)
    assert "slice5_secret_orders" not in strings
    assert "postgres.table" not in strings
    assert "order_link" not in strings

    forbidden_field_names = {
        "connector",
        "config",
        "secret",
        "secrets",
        "relationship",
        "relationships",
        "join",
        "joins",
        "symbol",
        "field_id",
        "ast",
        "ir",
    }
    assert forbidden_field_names.isdisjoint(_field_names(artifact))


def test_existing_cli_json_v1_helper_output_remains_unchanged() -> None:
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


def test_slice5_status_docs_record_private_query_aggregate_lineage_completion_only() -> (
    None
):
    for path in STATUS_DOCS:
        status = _normalized(path)
        for required in (
            "Phase 32 Slice 5 Query Posture, Aggregate, And Basic Lineage Metadata is complete",
            "Slice 5 hardens private metadata query posture, aggregate, and bounded basic lineage coverage",
            "Phase 32 as a whole is not complete",
            "No `pietto explain` CLI behavior was implemented",
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
    path: str | Path | None = "slice5.pietto",
) -> tuple[SemanticMetadataArtifact, Script, SemanticResult, ScriptIR]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
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


def _relation(
    artifact: SemanticMetadataArtifact,
    name: str,
) -> SemanticMetadataRelation:
    return next(
        relation for relation in artifact.metadata.relations if relation.name == name
    )


def _assert_argument(
    aggregate: SemanticMetadataAggregate,
    *,
    expression_kind: str,
    canonical_name: str,
    nullability: str,
    leaves: list[tuple[str, str, tuple[str, ...]]],
) -> None:
    argument = aggregate.arguments[0]
    assert argument.expression_kind == expression_kind
    assert argument.type is not None
    assert argument.type.canonical_name == canonical_name
    assert argument.type.nullability == nullability
    assert argument.location is not None
    _assert_leaves(argument.field_leaves, leaves)


def _assert_leaves(
    leaves: Iterable[SemanticMetadataFieldLeaf],
    expected: list[tuple[str, str, tuple[str, ...]]],
) -> None:
    assert _leaf_signature(leaves) == expected


def _leaf_signature(
    leaves: Iterable[SemanticMetadataFieldLeaf],
) -> list[tuple[str, str, tuple[str, ...]]]:
    return [(leaf.relation, leaf.field, leaf.qualifier) for leaf in leaves]


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
