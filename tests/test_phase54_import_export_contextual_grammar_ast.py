from __future__ import annotations

import ast
import json
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Any

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto.cli as cli
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto.ast_nodes import (
    ExportItem,
    ExportStatement,
    ImportItem,
    ImportStatement,
    ModuleDeclarationKind,
    Script,
    Span,
)
from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice4-import-export-contextual-grammar-generated-"
    "parser-and-immutable-ast-v1.md"
)
PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
GRAMMAR_REL = "grammar/Pietto.g4"
AST_REL = "src/pietto/ast_nodes.py"
BUILDER_REL = "src/pietto/ast_builder.py"
TOPOLOGY_REL = (
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_"
    "let_visibility_contract.py"
)
GENERATED_RELS = (
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/generated/__init__.py",
)
EXPECTED_TEST_NAMES = (
    "test_slice4_contract_artifacts_ast_surface_and_test_inventory_are_exact",
    "test_minimal_import_block_preserves_decoded_target_item_and_exact_spans",
    "test_import_block_accepts_exact_six_declaration_kinds_in_source_order",
    "test_import_alias_direction_preserves_exported_and_local_names_and_spans",
    "test_multiple_import_blocks_preserve_module_statement_source_order",
    "test_import_comments_blank_lines_and_string_escape_policy_are_preserved",
    "test_import_target_is_retained_without_path_normalization_or_filesystem_lookup",
    "test_minimal_export_block_preserves_item_and_exact_spans",
    "test_export_block_accepts_exact_six_declaration_kinds_in_source_order",
    "test_multiple_export_blocks_preserve_module_statement_source_order",
    "test_import_export_blocks_interleave_with_definitions_and_relationships_without_reclassification",
    "test_script_without_module_syntax_keeps_empty_module_statements_and_equal_existing_ast",
    "test_module_ast_is_frozen_slots_tuple_backed_value_equal_and_hashable",
    "test_module_ast_contains_no_antlr_nodes_or_semantic_identity_fields",
    "test_import_export_as_remain_contextual_identifiers_across_existing_definition_positions",
    "test_import_export_as_remain_contextual_in_relationship_let_aggregate_and_window_positions",
    "test_existing_parser_ast_corpus_representatives_remain_accepted_and_unchanged",
    "test_import_export_top_level_blocks_do_not_change_semantic_catalog_or_diagnostics",
    "test_import_export_top_level_blocks_do_not_change_ir_or_postgres_mysql_sql",
    "test_import_export_top_level_blocks_do_not_change_public_cli_json_or_metadata_shape",
    "test_schema_v1_preserves_module_ast_without_import_binding_or_catalog_effect",
    "test_schema_v2_retains_module_ast_and_stops_before_legacy_flat_catalog",
    "test_module_diagnostics_remain_private_without_serializer_or_dependency_surfaces",
    "test_invalid_import_forms_fail_with_existing_parser_diagnostics_and_spans",
    "test_invalid_export_forms_fail_with_existing_parser_diagnostics_and_spans",
    "test_import_and_export_require_nonempty_indented_bodies",
    "test_import_and_export_are_rejected_outside_top_level",
    "test_tabs_and_malformed_module_indentation_use_existing_diagnostics",
    "test_generated_inventory_rules_and_contextual_token_order_are_exact",
    "test_reader_allowlist_retained_later_and_publication_topology_contracts_are_exact",
)
KINDS = (
    ModuleDeclarationKind.TYPE,
    ModuleDeclarationKind.ENUM,
    ModuleDeclarationKind.SHAPE,
    ModuleDeclarationKind.SOURCE,
    ModuleDeclarationKind.TABLE,
    ModuleDeclarationKind.QUERY,
)
BASE_PROGRAM = (
    "shape Row:\n"
    "    id: Int not null\n"
    'source rows: Row is postgres.table("public.rows")\n'
    "query selected:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
)
MODULE_SUFFIX = (
    'import "models/shared.pietto":\n'
    "    shape SharedRow as ImportedRow\n"
    "    query shared_query\n"
    "\n"
    "export:\n"
    "    shape Row\n"
    "    query selected\n"
)
NEGATIVE_DIAGNOSTICS = {
    "invalid-import-0.pietto": (
        ("PIE-P1000", 1, 18, None, None),
        ("PIE-P1000", 2, 1, None, None),
    ),
    "invalid-import-1.pietto": (("PIE-P1000", 1, 8, None, None),),
    "invalid-import-2.pietto": (
        ("PIE-P1000", 2, 5, None, None),
        ("PIE-P1000", 3, 1, None, None),
    ),
    "invalid-import-3.pietto": (("PIE-P1000", 2, 13, None, None),),
    "invalid-import-4.pietto": (("PIE-P1000", 2, 18, None, None),),
    "invalid-import-5.pietto": (("PIE-P1000", 2, 25, None, None),),
    "invalid-import-6.pietto": (
        ("PIE-P1000", 2, 5, None, None),
        ("PIE-P1000", 2, 17, None, None),
        ("PIE-P1000", 3, 1, None, None),
    ),
    "invalid-import-7.pietto": (
        ("PIE-P1000", 1, 19, None, None),
        ("PIE-P1005", 1, 19, None, None),
        ("PIE-P1005", 1, 28, None, None),
    ),
    "invalid-import-8.pietto": (("PIE-P1000", 2, 11, None, None),),
    "invalid-import-9.pietto": (("PIE-P1000", 1, 1, None, None),),
    "invalid-import-10.pietto": (("PIE-P1000", 1, 8, None, None),),
    "invalid-export-0.pietto": (("PIE-P1000", 1, 8, None, None),),
    "invalid-export-1.pietto": (("PIE-P1000", 2, 12, None, None),),
    "invalid-export-2.pietto": (
        ("PIE-P1000", 2, 5, None, None),
        ("PIE-P1000", 3, 1, None, None),
    ),
    "invalid-export-3.pietto": (("PIE-P1000", 2, 13, None, None),),
    "invalid-export-4.pietto": (("PIE-P1000", 1, 8, None, None),),
    "invalid-export-5.pietto": (
        ("PIE-P1000", 2, 5, None, None),
        ("PIE-P1000", 2, 17, None, None),
        ("PIE-P1000", 3, 1, None, None),
    ),
    "invalid-export-6.pietto": (
        ("PIE-P1000", 1, 8, None, None),
        ("PIE-P1005", 1, 8, None, None),
        ("PIE-P1005", 1, 17, None, None),
    ),
    "invalid-export-7.pietto": (("PIE-P1000", 2, 11, None, None),),
    "empty-module-0.pietto": (("PIE-P1000", 2, 1, None, None),),
    "empty-module-1.pietto": (("PIE-P1000", 3, 1, None, None),),
    "empty-module-2.pietto": (("PIE-P1000", 2, 1, None, None),),
    "empty-module-3.pietto": (("PIE-P1000", 3, 1, None, None),),
    "nested-module-0.pietto": (
        ("PIE-P1000", 2, 12, None, None),
        ("PIE-P1000", 2, 23, None, None),
        ("PIE-P1000", 3, 9, None, None),
        ("PIE-P1000", 4, 1, None, None),
    ),
    "nested-module-1.pietto": (
        ("PIE-P1000", 3, 5, None, None),
        ("PIE-P1000", 5, 1, None, None),
    ),
    "nested-module-2.pietto": (
        ("PIE-P1000", 3, 5, None, None),
        ("PIE-P1000", 5, 1, None, None),
    ),
    "nested-module-3.pietto": (
        ("PIE-P1000", 3, 5, None, None),
        ("PIE-P1000", 5, 1, None, None),
    ),
    "module-indent-0.pietto": (("PIE-P1004", 2, 1, None, None),),
    "module-indent-1.pietto": (
        ("PIE-P1003", 3, 3, None, None),
        ("PIE-P1000", 3, 10, None, None),
        ("PIE-P1000", 4, 1, None, None),
    ),
    "module-indent-2.pietto": (
        ("PIE-P1000", 3, 9, None, None),
        ("PIE-P1000", 3, 16, None, None),
        ("PIE-P1000", 4, 1, None, None),
    ),
}


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _parsed(source: str, *, path: str | Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    return result.ast


def _assert_parse_failure(source: str, *, path: str) -> None:
    result = parse_source(source, path=path)
    assert result.ast is None
    assert all(
        diagnostic.severity is Severity.ERROR for diagnostic in result.diagnostics
    )
    assert all(diagnostic.location.path == path for diagnostic in result.diagnostics)
    assert (
        tuple(
            (
                diagnostic.code,
                diagnostic.location.line,
                diagnostic.location.column,
                diagnostic.location.end_line,
                diagnostic.location.end_column,
            )
            for diagnostic in result.diagnostics
        )
        == NEGATIVE_DIAGNOSTICS[path]
    )
    assert set(NEGATIVE_DIAGNOSTICS) == {
        *(f"invalid-import-{index}.pietto" for index in range(11)),
        *(f"invalid-export-{index}.pietto" for index in range(8)),
        *(f"empty-module-{index}.pietto" for index in range(4)),
        *(f"nested-module-{index}.pietto" for index in range(4)),
        *(f"module-indent-{index}.pietto" for index in range(3)),
    }
    assert len(NEGATIVE_DIAGNOSTICS) == 30


def _write_project(root: Path, *, schema_version: int) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(BASE_PROGRAM + MODULE_SUFFIX, encoding="utf-8")
    return root


def _pipeline(source: str) -> tuple[Script, Any, Any]:
    script = _parsed(source, path="pipeline.pietto")
    semantic = analyze(script)
    assert semantic.diagnostics == ()
    ir = build_ir(script, semantic.model)
    assert ir.diagnostics == ()
    assert ir.ir is not None
    return script, semantic, ir.ir


def test_slice4_contract_artifacts_ast_surface_and_test_inventory_are_exact() -> None:
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert tuple(ModuleDeclarationKind) == KINDS
    assert tuple(field.name for field in fields(ImportItem)) == (
        "span",
        "declaration_kind",
        "exported_name",
        "local_name",
        "declaration_kind_span",
        "exported_name_span",
        "local_name_span",
    )
    assert tuple(field.name for field in fields(ImportStatement)) == (
        "span",
        "target",
        "target_span",
        "items",
    )
    assert tuple(field.name for field in fields(ExportItem)) == (
        "span",
        "declaration_kind",
        "local_name",
        "declaration_kind_span",
        "local_name_span",
    )
    assert tuple(field.name for field in fields(ExportStatement)) == ("span", "items")
    assert tuple(field.name for field in fields(Script))[-1] == "module_statements"

    tree = ast.parse(_read(__file__.removeprefix(str(REPO_ROOT) + "/")))
    names = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert names == EXPECTED_TEST_NAMES


def test_minimal_import_block_preserves_decoded_target_item_and_exact_spans() -> None:
    path = Path("modules/main.pietto")
    script = _parsed(
        'import "models/customer.pietto":\n    shape Customer\n',
        path=path,
    )
    assert script.module_statements == (
        ImportStatement(
            span=Span(
                path=str(path),
                line=1,
                column=1,
                end_line=2,
                end_column=19,
            ),
            target="models/customer.pietto",
            target_span=Span(
                path=str(path),
                line=1,
                column=8,
                end_line=1,
                end_column=32,
            ),
            items=(
                ImportItem(
                    span=Span(
                        path=str(path),
                        line=2,
                        column=5,
                        end_line=2,
                        end_column=19,
                    ),
                    declaration_kind=ModuleDeclarationKind.SHAPE,
                    exported_name="Customer",
                    local_name=None,
                    declaration_kind_span=Span(
                        path=str(path),
                        line=2,
                        column=5,
                        end_line=2,
                        end_column=10,
                    ),
                    exported_name_span=Span(
                        path=str(path),
                        line=2,
                        column=11,
                        end_line=2,
                        end_column=19,
                    ),
                    local_name_span=None,
                ),
            ),
        ),
    )


def test_import_block_accepts_exact_six_declaration_kinds_in_source_order() -> None:
    script = _parsed(
        'import "all.pietto":\n'
        "    type T\n"
        "    enum E\n"
        "    shape S\n"
        "    source src\n"
        "    table tbl\n"
        "    query qry\n"
    )
    statement = script.module_statements[0]
    assert isinstance(statement, ImportStatement)
    assert tuple(item.declaration_kind for item in statement.items) == KINDS
    assert tuple(item.exported_name for item in statement.items) == (
        "T",
        "E",
        "S",
        "src",
        "tbl",
        "qry",
    )


def test_import_alias_direction_preserves_exported_and_local_names_and_spans() -> None:
    script = _parsed(
        'import "aliases.pietto":\n    query exported_name as local_name\n'
    )
    statement = script.module_statements[0]
    assert isinstance(statement, ImportStatement)
    item = statement.items[0]
    assert (item.exported_name, item.local_name) == ("exported_name", "local_name")
    assert item.exported_name_span == Span(
        path=None, line=2, column=11, end_line=2, end_column=24
    )
    assert item.local_name_span == Span(
        path=None, line=2, column=28, end_line=2, end_column=38
    )


def test_multiple_import_blocks_preserve_module_statement_source_order() -> None:
    script = _parsed(
        'import "z.pietto":\n    type Z\n\nimport "a.pietto":\n    type A\n'
    )
    assert tuple(
        statement.target
        for statement in script.module_statements
        if isinstance(statement, ImportStatement)
    ) == ("z.pietto", "a.pietto")


def test_import_comments_blank_lines_and_string_escape_policy_are_preserved() -> None:
    script = _parsed(
        'import "models\\tshared.pietto": # target\n'
        "\n"
        "    # first declaration\n"
        "    shape Shared\n"
        "\n"
        "    query report as local_report # alias\n"
    )
    statement = script.module_statements[0]
    assert isinstance(statement, ImportStatement)
    assert statement.target == "models\tshared.pietto"
    assert [(item.exported_name, item.local_name) for item in statement.items] == [
        ("Shared", None),
        ("report", "local_report"),
    ]


def test_import_target_is_retained_without_path_normalization_or_filesystem_lookup() -> (
    None
):
    targets = (
        "../outside/../shared.pietto",
        "https://example.invalid/pkg.pietto",
        "missing/./module.pietto",
    )
    for target in targets:
        script = _parsed(f'import "{target}":\n    type Value\n')
        statement = script.module_statements[0]
        assert isinstance(statement, ImportStatement)
        assert statement.target == target


def test_minimal_export_block_preserves_item_and_exact_spans() -> None:
    script = _parsed("export:\n    type UserId\n", path="exports.pietto")
    assert script.module_statements == (
        ExportStatement(
            span=Span(
                path="exports.pietto",
                line=1,
                column=1,
                end_line=2,
                end_column=16,
            ),
            items=(
                ExportItem(
                    span=Span(
                        path="exports.pietto",
                        line=2,
                        column=5,
                        end_line=2,
                        end_column=16,
                    ),
                    declaration_kind=ModuleDeclarationKind.TYPE,
                    local_name="UserId",
                    declaration_kind_span=Span(
                        path="exports.pietto",
                        line=2,
                        column=5,
                        end_line=2,
                        end_column=9,
                    ),
                    local_name_span=Span(
                        path="exports.pietto",
                        line=2,
                        column=10,
                        end_line=2,
                        end_column=16,
                    ),
                ),
            ),
        ),
    )


def test_export_block_accepts_exact_six_declaration_kinds_in_source_order() -> None:
    script = _parsed(
        "export:\n"
        "    type T\n"
        "    enum E\n"
        "    shape S\n"
        "    source src\n"
        "    table tbl\n"
        "    query qry\n"
    )
    statement = script.module_statements[0]
    assert isinstance(statement, ExportStatement)
    assert tuple(item.declaration_kind for item in statement.items) == KINDS
    assert tuple(item.local_name for item in statement.items) == (
        "T",
        "E",
        "S",
        "src",
        "tbl",
        "qry",
    )


def test_multiple_export_blocks_preserve_module_statement_source_order() -> None:
    script = _parsed("export:\n    type First\n\nexport:\n    query Second\n")
    first, second = script.module_statements
    assert isinstance(first, ExportStatement)
    assert isinstance(second, ExportStatement)
    assert first.items[0].local_name == "First"
    assert second.items[0].local_name == "Second"


def test_import_export_blocks_interleave_with_definitions_and_relationships_without_reclassification() -> (
    None
):
    script = _parsed(
        'import "row.pietto":\n'
        "    shape ImportedRow\n"
        "\n"
        "shape LocalRow:\n"
        "    id: Int not null\n"
        "\n"
        "export:\n"
        "    shape LocalRow\n"
        "\n"
        'source rows: LocalRow is postgres.table("rows")\n'
        "relationship self_link:\n"
        "    endpoint left: rows\n"
        "    endpoint right: rows\n"
    )
    assert [definition.name for definition in script.definitions] == [
        "LocalRow",
        "rows",
    ]
    assert [relationship.name for relationship in script.relationships] == ["self_link"]
    assert [type(statement) for statement in script.module_statements] == [
        ImportStatement,
        ExportStatement,
    ]


def test_script_without_module_syntax_keeps_empty_module_statements_and_equal_existing_ast() -> (
    None
):
    script = _parsed(BASE_PROGRAM, path="existing.pietto")
    rebuilt = Script(
        span=script.span,
        header=script.header,
        definitions=script.definitions,
        relationships=script.relationships,
    )
    assert script.module_statements == ()
    assert script == rebuilt
    assert hash(script) == hash(rebuilt)


def test_module_ast_is_frozen_slots_tuple_backed_value_equal_and_hashable() -> None:
    first = _parsed(MODULE_SUFFIX)
    second = _parsed(MODULE_SUFFIX)
    assert first == second
    assert hash(first) == hash(second)
    assert isinstance(first.module_statements, tuple)
    assert all(
        isinstance(statement.items, tuple) for statement in first.module_statements
    )
    for value in (
        first,
        *first.module_statements,
        *(item for statement in first.module_statements for item in statement.items),
    ):
        assert is_dataclass(value)
        assert hasattr(type(value), "__slots__")
        assert not hasattr(value, "__dict__")
        assert isinstance(hash(value), int)
    with pytest.raises(FrozenInstanceError):
        first.module_statements[0].span = first.span  # type: ignore[misc]


def test_module_ast_contains_no_antlr_nodes_or_semantic_identity_fields() -> None:
    script = _parsed(MODULE_SUFFIX)
    forbidden = {
        "physical_path",
        "inode",
        "digest",
        "selected_input",
        "module_identity",
        "declaration_identity",
        "binding",
        "visibility",
        "catalog",
        "graph",
    }
    for statement in script.module_statements:
        assert type(statement).__module__ == "pietto.ast_nodes"
        assert not forbidden.intersection(field.name for field in fields(statement))
        for item in statement.items:
            assert type(item).__module__ == "pietto.ast_nodes"
            assert not forbidden.intersection(field.name for field in fields(item))
            assert "antlr" not in repr(item).lower()


def test_import_export_as_remain_contextual_identifiers_across_existing_definition_positions() -> (
    None
):
    script = _parsed(
        "type import = Int\n"
        "enum export:\n"
        "    as\n"
        "shape as:\n"
        "    import: export\n"
        'source import: as is postgres.table("contextual")\n'
        "table export:\n"
        "    from import\n"
        "    select:\n"
        "        import\n"
        "query as:\n"
        "    from export\n"
        "    select:\n"
        "        import\n"
    )
    assert [definition.name for definition in script.definitions] == [
        "import",
        "export",
        "as",
        "import",
        "export",
        "as",
    ]


def test_import_export_as_remain_contextual_in_relationship_let_aggregate_and_window_positions() -> (
    None
):
    script = _parsed(
        "shape Row:\n"
        "    import: Int not null\n"
        "    export: Int not null\n"
        "    as: Int not null\n"
        'source import: Row is postgres.table("contextual")\n'
        "relationship export:\n"
        "    endpoint as: import\n"
        "    endpoint import: import\n"
        "query as:\n"
        "    from import\n"
        "    let:\n"
        "        export = import\n"
        "    select:\n"
        "        import\n"
        "        as = sum(export)\n"
        "        export = row_number() window:\n"
        "            partition by:\n"
        "                import\n"
        "            order by:\n"
        "                export asc\n"
    )
    assert script.relationships[0].name == "export"
    assert script.definitions[-1].name == "as"


def test_existing_parser_ast_corpus_representatives_remain_accepted_and_unchanged() -> (
    None
):
    corpus = (
        "type Age = Int ensure self between 0 and 130\n",
        "enum Status:\n    active\n    archived\n",
        "shape Row:\n    id: Int not null\n    name: Text nullable\n",
        ("relationship edge:\n    endpoint left: rows\n    endpoint right: rows\n"),
        BASE_PROGRAM,
    )
    for source in corpus:
        first = _parsed(source, path="corpus.pietto")
        second = _parsed(source, path="corpus.pietto")
        assert first == second
        assert first.module_statements == ()


def test_import_export_top_level_blocks_do_not_change_semantic_catalog_or_diagnostics() -> (
    None
):
    baseline = _parsed(BASE_PROGRAM)
    with_modules = _parsed(BASE_PROGRAM + MODULE_SUFFIX)
    baseline_result = analyze(baseline)
    module_result = analyze(with_modules)
    assert baseline_result == module_result
    assert module_result.diagnostics == ()
    assert tuple(module_result.model.type_symbols) == ("Row",)
    assert tuple(module_result.model.relation_symbols) == ("rows", "selected")
    assert "ImportedRow" not in module_result.model.type_symbols


def test_import_export_top_level_blocks_do_not_change_ir_or_postgres_mysql_sql() -> (
    None
):
    _, _, baseline_ir = _pipeline(BASE_PROGRAM)
    _, _, module_ir = _pipeline(BASE_PROGRAM + MODULE_SUFFIX)
    assert baseline_ir == module_ir
    assert emit_postgres_sql(baseline_ir) == emit_postgres_sql(module_ir)
    assert emit_mysql_sql(baseline_ir) == emit_mysql_sql(module_ir)


def test_import_export_top_level_blocks_do_not_change_public_cli_json_or_metadata_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "module.pietto"
    path.write_text(BASE_PROGRAM + MODULE_SUFFIX, encoding="utf-8")
    assert cli.main(["check", str(path), "--format", "json"]) == 0
    document = json.loads(capsys.readouterr().out)
    assert tuple(document) == (
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    )
    assert "module" not in document
    assert "imports" not in document
    assert "exports" not in document

    script, semantic, script_ir = _pipeline(BASE_PROGRAM + MODULE_SUFFIX)
    artifact = build_semantic_metadata_artifact(
        path=path,
        script=script,
        semantic_result=semantic,
        ir=script_ir,
    )
    metadata_document = semantic_metadata_artifact_to_json_dict(artifact)
    assert tuple(metadata_document) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    serialized_metadata = json.dumps(metadata_document, sort_keys=True)
    assert '"module":' not in serialized_metadata
    assert '"imports":' not in serialized_metadata
    assert '"exports":' not in serialized_metadata


def test_schema_v1_preserves_module_ast_without_import_binding_or_catalog_effect(
    tmp_path: Path,
) -> None:
    result = check_project_parse_only(
        _write_project(tmp_path / "legacy", schema_version=1)
    )
    assert result.ok
    assert result.parsed_inputs[0].script.module_statements
    semantic = build_empty_project_semantic_result(result)
    assert semantic.ok
    assert semantic.model is not None
    assert tuple(semantic.model.catalog.type_symbols) == ("Row",)
    assert tuple(semantic.model.catalog.relation_symbols) == ("rows", "selected")
    assert "ImportedRow" not in semantic.model.catalog.type_symbols
    assert semantic.module_graph is None
    assert semantic.module_diagnostic_facts is None


def test_schema_v2_retains_module_ast_and_stops_before_legacy_flat_catalog(
    tmp_path: Path,
) -> None:
    result = check_project_parse_only(
        _write_project(tmp_path / "explicit", schema_version=2)
    )
    assert result.ok
    assert result.modules[0].parsed_input is result.parsed_inputs[0]
    assert result.parsed_inputs[0].script.module_statements
    semantic = build_empty_project_semantic_result(result)
    assert not semantic.ok
    assert semantic.model is None
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2701",)
    assert semantic.module_graph is not None
    assert semantic.module_diagnostic_facts is not None


def test_module_diagnostics_remain_private_without_serializer_or_dependency_surfaces() -> (
    None
):
    for name in (
        "ImportItem",
        "ImportStatement",
        "ExportItem",
        "ExportStatement",
        "ModuleDeclarationKind",
        "ProjectModuleGraph",
        "ProjectModuleDiagnosticFact",
    ):
        assert not hasattr(pietto, name)

    graph_path = REPO_ROOT / "src/pietto/_project/module_graph.py"
    resolution_path = REPO_ROOT / "src/pietto/_project/module_resolution.py"
    relation_resolution_path = (
        REPO_ROOT / "src/pietto/_project/module_relation_resolution.py"
    )
    graph_source = graph_path.read_text(encoding="utf-8")
    non_graph_production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
        and path not in {graph_path, resolution_path, relation_resolution_path}
    )
    for number in range(2701, 2708):
        code = f"PIE-S{number}"
        assert code in graph_source
        assert code not in non_graph_production

    pyproject = _read("pyproject.toml")
    assert "phase54" not in pyproject.lower()
    assert "module_statement" not in pyproject


def test_invalid_import_forms_fail_with_existing_parser_diagnostics_and_spans() -> None:
    cases = (
        'import "x.pietto"\n',
        "import target:\n    type T\n",
        'import "x.pietto":\n    *\n',
        'import "x.pietto":\n    type pkg.Value\n',
        'import "x.pietto":\n    type Value as\n',
        'import "x.pietto":\n    type Value as Local extra\n',
        'import "x.pietto":\n    constraint C\n',
        'import "x.pietto" { type T }\n',
        'import "x.pietto":\n    type T, enum E\n',
        'from "x.pietto" import type T\n',
        "import package remote:\n    type T\n",
    )
    for index, source in enumerate(cases):
        _assert_parse_failure(source, path=f"invalid-import-{index}.pietto")


def test_invalid_export_forms_fail_with_existing_parser_diagnostics_and_spans() -> None:
    cases = (
        'export "x.pietto":\n    type T\n',
        "export:\n    type T as Local\n",
        "export:\n    *\n",
        "export:\n    type pkg.Value\n",
        "export from:\n    type T\n",
        "export:\n    constraint C\n",
        "export { type T }\n",
        "export:\n    type T, enum E\n",
    )
    for index, source in enumerate(cases):
        _assert_parse_failure(source, path=f"invalid-export-{index}.pietto")


def test_import_and_export_require_nonempty_indented_bodies() -> None:
    cases = (
        'import "x.pietto":\n',
        'import "x.pietto":\n\n',
        "export:\n",
        "export:\n\n",
    )
    for index, source in enumerate(cases):
        _assert_parse_failure(source, path=f"empty-module-{index}.pietto")


def test_import_and_export_are_rejected_outside_top_level() -> None:
    cases = (
        'shape Row:\n    import "x.pietto":\n        type T\n',
        "query q:\n    from rows\n    export:\n        query q\n",
        (
            "relationship edge:\n"
            "    endpoint left: rows\n"
            '    import "x.pietto":\n'
            "        type T\n"
        ),
        'import "x.pietto":\n    type T\n    export:\n        type T\n',
    )
    for index, source in enumerate(cases):
        _assert_parse_failure(source, path=f"nested-module-{index}.pietto")


def test_tabs_and_malformed_module_indentation_use_existing_diagnostics() -> None:
    cases = (
        'import "x.pietto":\n\ttype T\n',
        "export:\n    type T\n  query q\n",
        'import "x.pietto":\n    type T\n        query q\n',
    )
    for index, source in enumerate(cases):
        _assert_parse_failure(source, path=f"module-indent-{index}.pietto")


def test_generated_inventory_rules_and_contextual_token_order_are_exact() -> None:
    assert tuple(
        str(path.relative_to(REPO_ROOT))
        for path in sorted((REPO_ROOT / "src/pietto/generated").glob("*"))
        if path.is_file()
    ) == tuple(sorted(GENERATED_RELS))
    assert (REPO_ROOT / "src/pietto/generated/__init__.py").read_bytes() == b""

    grammar = _read(GRAMMAR_REL)
    identifier_token = grammar.index("\nIDENTIFIER\n    :")
    assert grammar.index("IMPORT: 'import';") < identifier_token
    assert grammar.index("EXPORT: 'export';") < identifier_token
    assert grammar.index("AS: 'as';") < identifier_token
    identifier_rule = grammar[
        grammar.index("identifier\n") : grammar.index("callSuffix\n")
    ]
    assert all(f"| {token}" in identifier_rule for token in ("IMPORT", "EXPORT", "AS"))
    visitor = _read("src/pietto/generated/PiettoVisitor.py")
    assert "def visitImportStatement" in visitor
    assert "def visitExportStatement" in visitor


def test_reader_allowlist_retained_later_and_publication_topology_contracts_are_exact() -> (
    None
):
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    topology = _read(TOPOLOGY_REL)
    ast_source = _read(AST_REL)
    builder_source = _read(BUILDER_REL)

    assert "A2_M138_D0" in spec
    assert "125\nmechanical reader tests" in spec
    assert "128 literal handwritten Python paths" in spec
    assert "10886 passed" in spec
    assert "## Status And Slice 14 Lifecycle" in plan
    assert "PHASE54_SLICE14_GATE2_COMPLETED_AWAITING_PUBLICATION" in plan
    assert "PHASE54_SLICE14_GATE3" in plan
    assert "Slice 5 owns module-qualified nominal declaration identity" in spec
    assert "PIE-S2701" in spec and "remain absent and un-emitted" in spec
    assert "Add Phase 54 import export grammar and AST" in topology
    assert "Add Phase 54 module export surfaces" in topology
    assert 'PHASE54_SLICE4_BRANCH = "phase54/slice4-import-export-grammar-ast"' in (
        topology
    )
    assert 'PHASE54_SLICE5_HEAD = "c44a4271d9592cb393d2232f127a59d8466cc60a"' in (
        topology
    )
    assert 'PHASE54_SLICE6_HEAD = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"' in (
        topology
    )
    assert 'PHASE54_SLICE7_HEAD = "027b33cafcfd58916a89e299487dad38d24ade6c"' in (
        topology
    )
    assert 'PHASE54_SLICE8_HEAD = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"' in (
        topology
    )
    assert (
        'PHASE54_SLICE6_BRANCH = "phase54/slice6-export-visibility-facade"' in topology
    )
    assert "Add Phase 54 named import binding environments" in topology
    assert (
        'PHASE54_SLICE7_BRANCH = "phase54/slice7-named-import-binding-environments"'
        in topology
    )
    assert "Add Phase 54 module graph and diagnostics" in topology
    assert (
        'PHASE54_SLICE8_BRANCH = "phase54/slice8-module-graph-cycles-diagnostics"'
        in topology
    )
    assert "Add Phase 54 cross-module type and source resolution" in topology
    assert (
        'PHASE54_SLICE9_BRANCH = "phase54/slice9-cross-module-type-source-resolution"'
        in topology
    )
    assert 'assert base_ref == "main"' in topology
    assert "assert candidate_ref == PHASE54_SLICE4_BRANCH" in topology
    assert "assert head != candidate_sha" in topology
    assert "assert parents == (README_REFRESH_HEAD, candidate_sha)" in topology
    assert "assert parents == (PHASE54_SLICE5_HEAD, candidate_sha)" in topology
    assert "assert parents == (PHASE54_SLICE6_HEAD, candidate_sha)" in topology
    assert "assert parents == (PHASE54_SLICE7_HEAD, candidate_sha)" in topology
    assert "assert parents == (PHASE54_SLICE8_HEAD, candidate_sha)" in topology
    assert "module_statements: tuple[ModuleStatement, ...] = ()" in ast_source
    assert "def visitImportStatement" in builder_source
    assert "def visitExportStatement" in builder_source
