from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md",
    "docs/spec/phase48-table-to-table-table-to-query-propagation-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}


def test_unknown_bare_field_emits_pie_s2102_and_unknown_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        missing\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: missing",
    )


def test_unknown_qualified_field_emits_pie_s2102_with_full_dotted_name(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        users.missing\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: users.missing",
    )


def test_unknown_renamed_bare_field_uses_expression_name_not_alias(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        alias = missing\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: missing",
        expected_column=17,
    )


def test_unknown_renamed_qualified_field_uses_expression_text(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        alias = users.missing\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: users.missing",
        expected_column=17,
    )


def test_wrong_qualifier_emits_pie_s2102_for_full_dotted_name(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        orders.id\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: orders.id",
    )


def test_wrong_qualifier_in_rename_emits_pie_s2102_for_expression(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        alias = orders.id\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: orders.id",
        expected_column=17,
    )


def test_multi_part_dotted_projection_emits_pie_s2102(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        db.users.id\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: db.users.id",
    )


def test_multi_part_dotted_rename_emits_pie_s2102(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        alias = db.users.id\n")
    )

    _assert_unknown_direct_field(
        parse_result,
        semantic_result,
        expected_message="Unknown field: db.users.id",
        expected_column=17,
    )


def test_duplicate_output_remains_unknown_schema_without_pie_s2305_or_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        id\n        id = users.id\n")
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert _diagnostic_codes(semantic_result).isdisjoint({"PIE-S2102", "PIE-S2305"})


def test_computed_alias_remains_deferred_without_direct_field_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        total = missing + 1\n")
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    assert table not in semantic_result.model.relation_row_schemas


def test_phase48_table_to_query_unknown_field_emits_pie_s2102(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        'source users: User is postgres.table("users")\n'
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        missing\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (staged, exported)
    relation_schema = semantic_result.model.relation_row_schemas[exported]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: missing")]


def test_direct_field_diagnostics_are_ordered_by_file_definition_and_select_item(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a_first.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        'source users: User is postgres.table("users")\n'
        "table first:\n"
        "    from users\n"
        "    select:\n"
        "        first_missing\n"
        "        users.second_missing\n"
        "table second:\n"
        "    from users\n"
        "    select:\n"
        "        second_table_missing\n",
    )
    _write(
        root,
        "b_third.pietto",
        "table third:\n    from users\n    select:\n        third_missing\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert _diagnostic_messages(semantic_result) == [
        "Unknown field: first_missing",
        "Unknown field: users.second_missing",
        "Unknown field: second_table_missing",
        "Unknown field: third_missing",
    ]


def test_project_json_v2_receives_unknown_field_diagnostics_without_private_fact_leakage(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_select(tmp_path, "        users.missing\n")
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas
    assert document["ok"] is False
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2102", "Unknown field: users.missing")
    ]
    assert diagnostics[0]["related_locations"] == []
    for private_fact in (
        "relation_row_schemas",
        "source_row_schemas",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldNullability",
        "ProjectRowFieldProvenance",
    ):
        assert private_fact not in serialized


def test_project_text_check_reports_unknown_direct_field_diagnostic_through_existing_flow(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "text.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        missing\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "text.pietto" in captured.err
    assert "PIE-S2102 error" in captured.err
    assert "Unknown field: missing" in captured.err


def test_phase47_slice8_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE8_GATE2_PATHS)


def _assert_unknown_direct_field(
    parse_result: ProjectParseCheckResult,
    semantic_result: ProjectSemanticResult,
    *,
    expected_message: str,
    expected_column: int = 9,
) -> None:
    assert not semantic_result.ok
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", Severity.ERROR, expected_message)]
    location = semantic_result.diagnostics[0].location
    assert location.path == "models.pietto"
    assert location.line == 9
    assert location.column == expected_column


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project_with_select(tmp_path: Path, select_body: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        f"{select_body}",
    )
    return root


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived relation not found: {name}")


def _diagnostic_codes(semantic_result: ProjectSemanticResult) -> set[str]:
    return {diagnostic.code for diagnostic in semantic_result.diagnostics}


def _diagnostic_messages(semantic_result: ProjectSemanticResult) -> list[str]:
    return [diagnostic.message for diagnostic in semantic_result.diagnostics]


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths
