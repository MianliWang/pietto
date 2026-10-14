from __future__ import annotations

import json
from pathlib import Path
from typing import cast


import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import (
    project_check_result_to_json_dict,
    render_project_json_document,
)
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]

PROJECT_JSON_TOP_LEVEL_KEYS = (
    "schema_version",
    "command",
    "mode",
    "ok",
    "project",
    "inputs",
    "diagnostics",
    "cli_errors",
    "result",
)

PRIVATE_JSON_FACTS = (
    "ProjectRowFieldNullability",
    "ProjectRowFieldProvenanceKind",
    "ProjectRowFieldProvenance",
    "ProjectRowField",
    "ProjectRowSchema",
    "source_row_schemas",
    "relation_row_schemas",
    "SOURCE_FIELD",
    "source_field",
    "DIRECT_PROJECTION",
    "direct_projection",
    "EXPRESSION",
    "expression",
    "AGGREGATE",
    "aggregate",
    "type_resolutions",
    "source_shape_resolutions",
    "relation_resolutions",
    "ProjectRelationDependencyGraph",
    "ProjectRelationDependencyNode",
    "ProjectRelationDependencyEdge",
    "ProjectRelationDependencyCycle",
    "relation_dependency_graph",
    "cycles",
    "nodes",
    "edges",
    "origin",
    "target",
    "dependency_source",
)


def test_project_json_v2_shape_and_key_order_remain_stable_for_direct_row_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _direct_source_project(tmp_path, "        id\n        email\n")
    )
    document = _project_json_document(parse_result, semantic_result)
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.source_row_schemas
    assert semantic_result.model.relation_row_schemas
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    _assert_private_json_facts_absent(serialized)


def test_project_json_v2_unknown_direct_field_diagnostic_uses_existing_shape_without_private_leakage(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _direct_source_project(tmp_path, "        users.missing\n")
    )
    document = _project_json_document(parse_result, semantic_result)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    serialized = json.dumps(document)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert semantic_result.model.relation_row_schemas[projected].is_unknown is True
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is False
    assert document["cli_errors"] == []
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2102", "Unknown field: users.missing")
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["suggestion"] is None
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == "models.pietto"
    _assert_private_json_facts_absent(serialized)


def test_project_json_v2_grouped_relation_skip_keeps_private_schema_absent(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "shape User:\n"
            "    id: Int not null\n"
            "    email: Text nullable\n"
            'source users: User is postgres.table("users")\n'
            "table projected:\n"
            "    from users\n"
            "    group by:\n"
            "        email\n"
            "    select:\n"
            "        email\n",
        )
    )
    document = _project_json_document(parse_result, semantic_result)
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.source_row_schemas
    projected = _derived_definition(parse_result, "projected")
    assert projected not in semantic_result.model.relation_row_schemas
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is True
    assert document["diagnostics"] == []
    _assert_private_json_facts_absent(serialized)


def test_project_json_v2_cycle_and_row_schema_private_facts_remain_absent(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "table second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
        )
    )
    document = _project_json_document(parse_result, semantic_result)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    serialized = json.dumps(document)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_dependency_graph.cycles
    assert semantic_result.model.source_row_schemas == {}
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    assert diagnostics[0]["related_locations"] == []
    _assert_private_json_facts_absent(serialized)


def test_project_text_check_still_reports_pie_s2102_through_existing_flow(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _direct_source_project(tmp_path, "        missing\n")

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "models.pietto:9:9 PIE-S2102 error" in captured.err
    assert "Unknown field: missing" in captured.err


def test_project_json_v2_renderer_remains_single_line_ascii_document(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _direct_source_project(tmp_path, "        id\n")
    )
    document = _project_json_document(parse_result, semantic_result)
    rendered = render_project_json_document(document)

    assert rendered.endswith("\n")
    assert rendered.count("\n") == 1
    assert rendered.isascii()
    assert json.loads(rendered) == document
    _assert_private_json_facts_absent(rendered)


def _project_json_document(
    parse_result: ProjectParseCheckResult,
    semantic_result: ProjectSemanticResult,
) -> dict[str, object]:
    return project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _direct_source_project(tmp_path: Path, select_body: str) -> Path:
    return _project(
        tmp_path,
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


def _project(tmp_path: Path, source_text: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "models.pietto", source_text)
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


def _assert_private_json_facts_absent(serialized: str) -> None:
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized, private_fact


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
