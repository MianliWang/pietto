from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import (
    DottedNameExpr,
    GroupByClause,
    GroupByItem,
    LimitClause,
    NameExpr,
    OrderByClause,
    QueryDef,
    Span,
    TableDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, TypeKind, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parser_accepts_group_by_bare_field() -> None:
    relation = _parse_relation(
        "query grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
    )

    assert isinstance(relation.group_by_clause, GroupByClause)
    assert len(relation.group_by_clause.items) == 1
    item = relation.group_by_clause.items[0]
    assert isinstance(item, GroupByItem)
    assert isinstance(item.key, NameExpr)
    assert item.key.name == "status"


def test_parser_accepts_group_by_qualified_field_after_where() -> None:
    relation = _parse_relation(
        "table revenue_by_region:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    group by:\n"
        "        orders.region\n"
        "    select:\n"
        "        region = orders.region\n"
    )

    assert isinstance(relation, TableDef)
    assert relation.where_clause is not None
    assert isinstance(relation.group_by_clause, GroupByClause)
    item = relation.group_by_clause.items[0]
    assert isinstance(item.key, DottedNameExpr)
    assert item.key.parts == ("orders", "region")


def test_parser_accepts_group_by_before_order_by_and_limit() -> None:
    relation = _parse_relation(
        "query grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "    order by:\n"
        "        status\n"
        "    limit 10\n"
    )

    assert isinstance(relation.group_by_clause, GroupByClause)
    assert isinstance(relation.order_by_clause, OrderByClause)
    assert isinstance(relation.limit_clause, LimitClause)


def test_group_by_spans_and_duplicate_source_order_are_preserved() -> None:
    path = Path("examples/grouped/span.pietto")
    relation = _parse_relation(
        "query grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "        orders.status\n"
        "        status\n"
        "    select:\n"
        "        status\n",
        path=path,
    )

    clause = relation.group_by_clause
    assert isinstance(clause, GroupByClause)
    assert clause.span.line == 3
    assert clause.span.column == 5
    assert len(clause.items) == 3
    assert [item.span.line for item in clause.items] == [4, 5, 6]

    first, second, third = clause.items
    assert isinstance(first.key, NameExpr)
    assert isinstance(second.key, DottedNameExpr)
    assert isinstance(third.key, NameExpr)
    assert first.key.name == "status"
    assert second.key.parts == ("orders", "status")
    assert third.key.name == "status"
    assert first.key.span == Span(
        path=str(path),
        line=4,
        column=9,
        end_line=4,
        end_column=15,
    )
    assert second.key.span == Span(
        path=str(path),
        line=5,
        column=9,
        end_line=5,
        end_column=22,
    )


@pytest.mark.parametrize(
    "body",
    [
        (
            "    from orders\n"
            "    select:\n"
            "        status\n"
            "    group by:\n"
            "        status\n"
        ),
        "    from orders\n    group by:\n    select:\n        status\n",
        "    from orders\n    group by:\n        lower(status)\n    select:\n        status\n",
        "    from orders\n    group by:\n        count()\n    select:\n        status\n",
        "    from orders\n    group by:\n        1\n    select:\n        status\n",
    ],
)
def test_invalid_group_by_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query grouped_orders:\n{body}", path="group-by.pietto")

    assert result.ast is None
    assert result.diagnostics
    assert all(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_group_remains_soft_identifier_and_name_part() -> None:
    relation = _parse_relation(
        "query group:\n"
        "    from group\n"
        "    group by:\n"
        "        group.group\n"
        "    select:\n"
        "        group\n"
    )

    assert relation.name == "group"
    assert relation.from_clause.source_name == "group"
    assert relation.group_by_clause is not None
    item = relation.group_by_clause.items[0]
    assert isinstance(item.key, DottedNameExpr)
    assert item.key.parts == ("group", "group")


@pytest.mark.parametrize("relation_kind", ["query", "table"])
def test_semantic_accepts_valid_grouped_relation_after_sql_lowering(
    relation_kind: str,
) -> None:
    result = parse_source(_grouped_program(relation_kind), path="grouped.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef | TableDef, result.ast.definitions[-1])

    semantic = analyze(result.ast)
    errors = [
        diagnostic
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert [(diagnostic.code, diagnostic.message) for diagnostic in errors] == []
    assert relation.group_by_clause is not None
    schema = semantic.model.relation_row_schemas[relation]
    assert schema.is_unknown is False
    assert list(schema.fields) == ["status", "total"]
    assert schema.fields["status"].resolved_type.kind is TypeKind.BUILTIN
    assert schema.fields["status"].resolved_type.name == "Text"
    assert schema.fields["status"].nullability is EffectiveNullability.NON_NULL
    assert schema.fields["total"].resolved_type.kind is TypeKind.BUILTIN
    assert schema.fields["total"].resolved_type.name == "Int"
    assert schema.fields["total"].nullability is EffectiveNullability.NON_NULL


def test_cli_check_accepts_valid_grouped_relation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "grouped.pietto", _grouped_program("query"))

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_emit_sql_json_succeeds_with_group_by_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "grouped.pietto", _grouped_program("query"))

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = json.loads(captured.out)
    assert result["ok"] is True
    assert result["diagnostics"] == []
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert len(artifacts) == 1
    assert "GROUP BY" in cast(str, artifacts[0]["sql"])


def test_group_by_grammar_and_diagnostics_are_registered() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")

    assert grammar.count("GROUP: 'group';") == 1
    for required in (
        "groupByClause",
        "groupByBody",
        "groupByItem",
        ": GROUP BY COLON NEWLINE NEWLINE* INDENT groupByBody DEDENT",
        ": dottedName NEWLINE",
    ):
        assert required in grammar


def _parse_relation(
    source: str,
    *,
    path: str | Path | None = None,
) -> QueryDef | TableDef:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = result.ast.definitions[0]
    assert isinstance(relation, (QueryDef, TableDef))
    return relation


def _grouped_program(relation_kind: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int not null\n"
        'source orders: Order is postgres.table("orders")\n'
        f"{relation_kind} grouped_orders:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
