from __future__ import annotations

import json
from collections.abc import MutableMapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import NameExpr, QueryDef, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, ValueType, ValueTypeKind, analyze


REPO_ROOT = Path(__file__).resolve().parents[1]
IR_SURFACE_PATHS = (
    REPO_ROOT / "src/pietto/ir/model.py",
    REPO_ROOT / "src/pietto/ir/builder.py",
    REPO_ROOT / "src/pietto/ir/lowering.py",
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int nullable\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_semantic_model_let_scopes_is_empty_for_relations_without_let() -> None:
    relation, semantic = _analyze_relation(
        "query plain_orders:\n    from orders\n    select:\n        amount\n"
    )

    assert isinstance(relation, QueryDef)
    assert semantic.diagnostics == ()
    assert len(semantic.model.let_scopes) == 0
    assert relation not in semantic.model.let_scopes


@pytest.mark.parametrize("keyword", ["table", "query"])
def test_table_and_query_let_scopes_store_clause_and_bindings(
    keyword: str,
) -> None:
    relation, semantic = _analyze_relation(
        f"{keyword} enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )

    assert isinstance(relation, (TableDef, QueryDef))
    assert relation.let_clause is not None
    assert _error_codes(semantic) == []

    scope = semantic.model.let_scopes[relation]
    assert scope.clause is relation.let_clause
    assert scope.bindings == tuple(relation.let_clause.bindings)
    assert scope.bindings[0] is relation.let_clause.bindings[0]


def test_source_ordered_bindings_and_value_types_are_preserved() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        normalized = lower(trim(status))\n"
        "        status_len = len(normalized)\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        normalized_value = normalized\n"
        "        status_length = status_len\n"
        "        gross_value = gross\n"
    )

    assert relation.let_clause is not None
    scope = semantic.model.let_scopes[relation]

    assert [binding.name for binding in scope.bindings] == [
        "normalized",
        "status_len",
        "gross",
    ]
    assert tuple(scope.value_types) == ("normalized", "status_len", "gross")
    assert _scope_value_type_name(scope.value_types["normalized"]) == "Text"
    assert _scope_value_type_name(scope.value_types["status_len"]) == "Int"
    assert _scope_value_type_name(scope.value_types["gross"]) == "Int"


def test_binding_expression_value_types_remain_in_semantic_model() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )

    assert relation.let_clause is not None
    binding_expr = relation.let_clause.bindings[0].expression
    assert _model_value_type_name(semantic, binding_expr) == "Int"

    select_expr = relation.select_items[0].expression
    assert isinstance(select_expr, NameExpr)
    assert _model_value_type_name(semantic, select_expr) == "Int"


def test_invalid_binding_names_are_excluded_from_admitted_value_types() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        gross = amount - tax\n"
        "        amount = tax\n"
        "    select:\n"
        "        amount\n"
    )

    assert relation.let_clause is not None
    codes = _error_codes(semantic)
    assert codes.count("PIE-S2329") == 2

    scope = semantic.model.let_scopes[relation]
    assert [binding.name for binding in scope.bindings] == [
        "gross",
        "gross",
        "amount",
    ]
    assert tuple(scope.value_types) == ()


def test_dependency_order_storage_is_deterministic() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        normalized = lower(trim(status))\n"
        "        status_len = len(normalized)\n"
        "    select:\n"
        "        status_length = status_len\n"
    )

    assert _error_codes(semantic) == []
    scope = semantic.model.let_scopes[relation]
    assert tuple(scope.value_types) == ("normalized", "status_len")
    assert _scope_value_type_name(scope.value_types["normalized"]) == "Text"
    assert _scope_value_type_name(scope.value_types["status_len"]) == "Int"


def test_semantic_model_let_scope_mappings_are_read_only() -> None:
    relation, semantic = _analyze_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )

    scope = semantic.model.let_scopes[relation]
    assert isinstance(semantic.model.let_scopes, MappingProxyType)
    assert isinstance(scope.value_types, MappingProxyType)

    with pytest.raises(TypeError):
        cast(MutableMapping[object, object], semantic.model.let_scopes)[object()] = (
            object()
        )
    with pytest.raises(TypeError):
        cast(MutableMapping[str, object], scope.value_types)["other"] = object()


def test_pie_s2328_is_not_emitted_for_supported_row_level_let_relations() -> None:
    result = parse_source(
        SOURCE_PREFIX
        + "table enriched_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        gross = amount + tax\n"
        + "    select:\n"
        + "        gross_value = gross\n"
        + "query filtered_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        net = amount - tax\n"
        + "    select:\n"
        + "        net_value = net\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None

    semantic = analyze(result.ast)

    assert _error_codes(semantic).count("PIE-S2328") == 0


def test_cli_check_succeeds_for_supported_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_let_source(tmp_path)

    exit_code = cli.main(["check", str(source_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert f"OK: {source_path}" in captured.out


def test_emit_sql_succeeds_for_supported_let_with_sql_artifact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_let_source(tmp_path)

    exit_code = cli.main(
        [
            "emit-sql",
            str(source_path),
            "--dialect",
            "postgres",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    document = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert document["ok"] is True
    assert len(document["artifacts"]) == 1
    assert document["diagnostics"] == []
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics == []


def test_explain_succeeds_for_supported_let_without_schema_churn(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_let_source(tmp_path)

    exit_code = cli.main(["explain", str(source_path), "--format", "json"])
    captured = capsys.readouterr()
    document = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert document["ok"] is True
    assert "metadata" in document
    assert "let_scopes" not in json.dumps(document)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics == []


def test_non_let_explain_json_schema_remains_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "plain_orders.pietto"
    source_path.write_text(
        SOURCE_PREFIX
        + "query plain_orders:\n"
        + "    from orders\n"
        + "    select:\n"
        + "        amount\n",
        encoding="utf-8",
    )

    exit_code = cli.main(["explain", str(source_path), "--format", "json"])
    captured = capsys.readouterr()
    document = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert set(document) == {
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    }
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert document["schema_version"] == 1
    assert document["command"] == "explain"
    assert document["ok"] is True
    assert "let_scopes" not in json.dumps(document)


def test_no_let_ir_or_relation_layer_ir_surface_is_introduced() -> None:
    combined_ir = "\n".join(
        path.read_text(encoding="utf-8") for path in IR_SURFACE_PATHS
    )

    assert "LetBindingIR" not in combined_ir
    assert "RelationLayerIR" not in combined_ir


def _analyze_relation(source: str) -> tuple[TableDef | QueryDef, SemanticResult]:
    result = parse_source(SOURCE_PREFIX + source, path="let_model.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(TableDef | QueryDef, result.ast.definitions[-1])
    return relation, analyze(result.ast)


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _scope_value_type_name(value_type: ValueType) -> str:
    assert value_type.kind is ValueTypeKind.KNOWN
    return value_type.resolved_type.name


def _model_value_type_name(semantic: SemanticResult, expression: object) -> str:
    value_type = semantic.model.expression_value_types[cast(NameExpr, expression)]
    assert value_type.kind is ValueTypeKind.KNOWN
    return value_type.resolved_type.name


def _write_let_source(tmp_path: Path) -> Path:
    source_path = tmp_path / "with_let.pietto"
    source_path.write_text(
        SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        gross = amount + tax\n"
        + "    select:\n"
        + "        gross_value = gross\n",
        encoding="utf-8",
    )
    return source_path
