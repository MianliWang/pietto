from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PHASE47_PLAN_PATH = REPO_ROOT / "docs/plan/phase-47-direct-row-schema-mvp.md"
PHASE47_SPEC_PATH = REPO_ROOT / "docs/spec/phase47-direct-row-schema-scope-lock-v1.md"

ALLOWED_SLICE9_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md",
    "docs/spec/phase48-table-to-table-table-to-query-propagation-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
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


def test_slice9_route_and_phase48_50_readiness_contract_are_locked() -> None:
    docs = (
        PHASE47_PLAN_PATH.read_text(encoding="utf-8")
        + "\n"
        + PHASE47_SPEC_PATH.read_text(encoding="utf-8")
    )

    for required in (
        "9. Downstream readiness hardening for Phase 48-50",
        "10. Project JSON/private-fact privacy and compatibility hardening",
        "11. Completion audit/status lock",
        "Phase 47 must not implement query-to-query propagation",
        "Phase 47 must not implement computed aliases",
        "must not implement aggregate or grouped",
        "Project JSON v2 shape must remain unchanged",
    ):
        assert required in docs, required


def test_phase48_table_to_query_row_schema_propagates_from_direct_table_seed(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (staged, exported)
    assert tuple(semantic_result.model.relation_row_schemas[staged].fields) == (
        "id",
        "email",
    )
    assert tuple(semantic_result.model.relation_row_schemas[exported].fields) == ("id",)


def test_phase49_computed_alias_remains_deferred_without_schema_or_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert projected not in semantic_result.model.relation_row_schemas
    assert "PIE-S2102" not in _diagnostic_codes(semantic_result)


def test_phase49_let_schema_remains_deferred_without_direct_schema_expansion(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + 1\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[projected]
    assert tuple(relation_schema.fields) == ("id",)
    assert "total" not in relation_schema.fields
    assert {
        field.provenance.kind
        for field in relation_schema.fields.values()
        if field.provenance is not None
    } == {ProjectRowFieldProvenanceKind.DIRECT_PROJECTION}


def test_phase49_private_provenance_vocabulary_keeps_expression_readiness_private() -> (
    None
):
    assert ProjectRowFieldProvenanceKind.EXPRESSION.value == "expression"
    assert ProjectRowFieldProvenanceKind.AGGREGATE.value == "aggregate"
    assert ProjectRowFieldProvenanceKind.DIRECT_PROJECTION.value == (
        "direct_projection"
    )


def test_phase50_aggregate_projection_schema_remains_absent(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n    from users\n    select:\n        total = count()\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert projected not in semantic_result.model.relation_row_schemas


def test_phase50_grouped_direct_field_schema_remains_absent(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n"
            "    from users\n"
            "    group by:\n"
            "        email\n"
            "    select:\n"
            "        email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert projected not in semantic_result.model.relation_row_schemas


def test_duplicate_output_names_remain_unknown_schema_without_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        id = users.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[projected]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert _diagnostic_codes(semantic_result).isdisjoint({"PIE-S2102", "PIE-S2305"})


def test_project_json_v2_privacy_remains_unchanged_for_private_row_schema_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n    from users\n    select:\n        id\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas
    for private_fact in (
        "relation_row_schemas",
        "source_row_schemas",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldNullability",
        "ProjectRowFieldProvenance",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def test_phase47_slice9_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE9_GATE2_PATHS)


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(tmp_path: Path, relation_body: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_body}",
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
