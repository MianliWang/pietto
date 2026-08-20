from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
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
    "source_row_schemas",
    "relation_row_schemas",
    "relation_row_schema_states",
    "ProjectRowSchema",
    "ProjectRowField",
    "ProjectRelationRowSchemaState",
    "ProjectRelationRowSchemaStatus",
    "ProjectRelationRowSchemaReason",
    "ProjectRelationDependencyGraph",
    "ProjectRelationDependencyNode",
    "ProjectRelationDependencyEdge",
    "ProjectRelationDependencyCycle",
    "ProjectRowFieldProvenance",
    "provenance",
    "lineage",
    "relation_dependency_graph",
    "dependency_source",
    "private ordering",
    "direct_source_concrete",
    "table_upstream_concrete",
    "relation_upstream_concrete",
    "unknown_schema",
    "duplicate_output_name",
    "deferred_phase48_behavior",
    "unresolved_relation_blocked",
    "cycle_blocked",
    "upstream_unknown",
    "upstream_deferred",
    "upstream_blocked",
)


def test_project_json_v2_top_level_key_order_remains_exact(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n    from users\n    select:\n        id\n",
        )
    )
    document = _project_json_document(parse_result, semantic_result)

    assert semantic_result.ok
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    _assert_private_json_facts_absent(json.dumps(document))


def test_project_json_v2_concrete_multi_hop_keeps_private_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query mid:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query final:\n"
            "    from mid\n"
            "    select:\n"
            "        id\n",
        )
    )
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")
    document = _project_json_document(parse_result, semantic_result)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        mid,
        final,
    )
    assert tuple(semantic_result.model.relation_row_schemas[final].fields) == ("id",)
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        final,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        schema_is_relation_schema=True,
    )
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["diagnostics"] == []
    _assert_private_json_facts_absent(json.dumps(document))


def test_project_json_v2_unknown_state_keeps_diagnostics_public_only(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n",
        )
    )
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    document = _project_json_document(parse_result, semantic_result)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas[seed].is_unknown is True
    assert semantic_result.model.relation_row_schemas[exported].is_unknown is True
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        exported,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        schema_is_relation_schema=True,
    )
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2102", "Unknown field: missing")
    ]
    _assert_private_json_facts_absent(json.dumps(document))


def test_project_json_v2_deferred_state_keeps_private_reasons_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query computed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query downstream:\n"
            "    from computed\n"
            "    select:\n"
            "        total\n",
        )
    )
    computed = _derived_definition(parse_result, "computed")
    downstream = _derived_definition(parse_result, "downstream")
    document = _project_json_document(parse_result, semantic_result)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert computed in semantic_result.model.relation_row_schemas
    assert downstream in semantic_result.model.relation_row_schemas
    assert tuple(semantic_result.model.relation_row_schemas[computed].fields) == (
        "total",
    )
    assert tuple(semantic_result.model.relation_row_schemas[downstream].fields) == (
        "total",
    )
    assert (
        semantic_result.model.relation_row_schemas[computed].fields["total"].field_def
        is None
    )
    _assert_state(
        semantic_result,
        computed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        downstream,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        schema_is_relation_schema=True,
    )
    assert document["ok"] is True
    assert document["diagnostics"] == []
    _assert_private_json_facts_absent(json.dumps(document))


def test_project_json_v2_unresolved_blocked_state_keeps_private_graph_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n"
            "    from missing_relation\n"
            "    select:\n"
            "        id\n"
            "query downstream:\n"
            "    from broken\n"
            "    select:\n"
            "        id\n",
        )
    )
    broken = _derived_definition(parse_result, "broken")
    downstream = _derived_definition(parse_result, "downstream")
    document = _project_json_document(parse_result, semantic_result)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert broken not in semantic_result.model.relation_row_schemas
    assert downstream not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_state(
        semantic_result,
        downstream,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
    )
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]
    _assert_private_json_facts_absent(json.dumps(document))


def test_project_json_v2_cycle_blocked_state_keeps_cycle_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
            include_source=False,
        )
    )
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    document = _project_json_document(parse_result, semantic_result)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_dependency_graph.cycles
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (first, second)
    for definition in (first, second):
        _assert_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        )
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    _assert_private_json_facts_absent(json.dumps(document))


def _project_json_document(
    parse_result: ProjectParseCheckResult,
    semantic_result: ProjectSemanticResult,
) -> dict[str, object]:
    return project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )


def _assert_private_json_facts_absent(serialized: str) -> None:
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized, private_fact


def _assert_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
    *,
    schema_is_relation_schema: bool = False,
) -> None:
    assert semantic_result.model is not None
    state = semantic_result.model.relation_row_schema_states[definition]
    assert state.status is status
    assert state.reason is reason
    if schema_is_relation_schema:
        assert state.schema is semantic_result.model.relation_row_schemas[definition]
    else:
        assert state.schema is None


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    assert semantic_result.model is not None
    return parse_result, semantic_result


def _project(
    tmp_path: Path,
    relation_body: str,
    *,
    include_source: bool = True,
) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    source_text = ""
    if include_source:
        source_text = (
            "shape User:\n"
            "    id: Int not null\n"
            "    score: Int\n"
            'source users: User is postgres.table("users")\n'
        )
    _write(root, "models.pietto", f"{source_text}{relation_body}")
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
