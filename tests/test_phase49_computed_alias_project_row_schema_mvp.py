from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE4_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-computed-alias-project-row-schema-mvp-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_upstream_non_concrete_schema_propagation.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_project_json_private_fact_privacy_readiness.py",
    "tests/test_phase48_downstream_diagnostics_ordering_hardening.py",
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

PRIVATE_JSON_FACTS = (
    "source_row_schemas",
    "relation_row_schemas",
    "relation_row_schema_states",
    "ProjectRowSchema",
    "ProjectRowField",
    "ProjectRowFieldProvenance",
    "row_expression_schema",
    "row_expression_type_facts",
    "dependency_placeholders",
    "lineage_placeholders",
    "derived_expression",
    "expression_value_types",
)


def test_computed_alias_over_concrete_source_schema_becomes_private_row_field(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query scored:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    scored = _derived_definition(parse_result, "scored")
    source_schema = semantic_result.model.source_row_schemas[users]
    row_schema = semantic_result.model.relation_row_schemas[scored]

    assert tuple(row_schema.fields) == ("id", "total")
    _assert_direct_field_preserves_source_field_def(
        relation_field=row_schema.fields["id"],
        source_field=source_schema.fields["id"],
    )
    total = row_schema.fields["total"]
    assert total.name == "total"
    assert total.resolved_type.name == "Int"
    assert total.nullability is ProjectRowFieldNullability.UNKNOWN
    assert total.field_def is None
    assert total.provenance is not None
    assert total.provenance.kind is ProjectRowFieldProvenanceKind.EXPRESSION
    assert (
        total.provenance.symbol
        is semantic_result.model.relation_resolutions[scored.from_clause]
    )
    _assert_state(
        semantic_result,
        scored,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )


def test_renamed_direct_projection_still_preserves_source_native_field_def(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query scored:\n"
            "    from users\n"
            "    select:\n"
            "        user_id = id\n"
            "        total = score + 1\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    scored = _derived_definition(parse_result, "scored")
    source_schema = semantic_result.model.source_row_schemas[users]
    row_schema = semantic_result.model.relation_row_schemas[scored]

    assert tuple(row_schema.fields) == ("user_id", "total")
    _assert_direct_field_preserves_source_field_def(
        relation_field=row_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        expected_name="user_id",
    )
    assert row_schema.fields["total"].field_def is None


def test_computed_alias_schema_propagates_through_query_to_query_multi_hop(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n"
            "query final:\n"
            "    from exported\n"
            "    select:\n"
            "        final_total = total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    final = _derived_definition(parse_result, "final")
    seed_schema = semantic_result.model.relation_row_schemas[seed]
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    final_schema = semantic_result.model.relation_row_schemas[final]

    assert tuple(seed_schema.fields) == ("total",)
    assert tuple(exported_schema.fields) == ("total",)
    assert tuple(final_schema.fields) == ("final_total",)
    assert seed_schema.fields["total"].field_def is None
    assert exported_schema.fields["total"].field_def is None
    assert final_schema.fields["final_total"].field_def is None
    assert final_schema.fields["final_total"].resolved_type.name == "Int"
    _assert_state(
        semantic_result,
        final,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
    )


def test_unknown_null_division_and_aggregate_surfaces_remain_non_concrete(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query nullish:\n"
            "    from users\n"
            "    select:\n"
            "        nothing = null\n"
            "query divided:\n"
            "    from users\n"
            "    select:\n"
            "        ratio = score / bonus\n"
            "query missing:\n"
            "    from users\n"
            "    select:\n"
            "        total = missing + 1\n"
            "query aggregate:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "query grouped:\n"
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
    for name in ("nullish", "divided", "missing", "aggregate", "grouped"):
        definition = _derived_definition(parse_result, name)
        assert definition not in semantic_result.model.relation_row_schemas
        _assert_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
        )


def test_bare_let_selected_output_does_not_become_concrete_in_slice4(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + 1\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert semantic_result.model.relation_row_schemas[projected].is_unknown is True
    assert [(item.code, item.message) for item in semantic_result.diagnostics] == [
        ("PIE-S2102", "Unknown field: total")
    ]


def test_project_json_v2_keeps_computed_row_schema_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query scored:\n    from users\n    select:\n        total = score + 1\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    scored = _derived_definition(parse_result, "scored")
    assert scored in semantic_result.model.relation_row_schemas
    assert tuple(document) == (
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
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized


def test_slice4_keeps_forbidden_project_files_untouched() -> None:
    for relative_path in (
        "src/pietto/_project/check.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/row_expression_schema.py",
    ):
        assert _git_diff_names(relative_path) == ()


def test_slice4_helper_uses_narrow_private_inference_only() -> None:
    helper = (REPO_ROOT / "src/pietto/_project/row_expression_type_facts.py").read_text(
        encoding="utf-8"
    )
    model = (REPO_ROOT / "src/pietto/_project/model.py").read_text(encoding="utf-8")

    assert "infer_row_expression" in helper
    assert "semantic_api" not in helper
    assert "semantic_api" not in model
    assert "from pietto.semantic" not in model
    assert "import pietto.semantic" not in model


def test_phase49_slice4_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    dirty_paths = _git_status_paths()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert dirty_paths in (set(), ALLOWED_SLICE4_GATE2_PATHS)


def _assert_direct_field_preserves_source_field_def(
    *,
    relation_field: ProjectRowField,
    source_field: ProjectRowField,
    expected_name: str | None = None,
) -> None:
    assert relation_field.name == (expected_name or source_field.name)
    assert relation_field.resolved_type is source_field.resolved_type
    assert relation_field.nullability is source_field.nullability
    assert relation_field.field_def is source_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def _assert_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    assert semantic_result.model is not None
    state = semantic_result.model.relation_row_schema_states[definition]
    assert state.status is status
    assert state.reason is reason


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(tmp_path: Path, relation_source: str) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int not null\n"
        "    bonus: Int nullable\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_source}",
    )
    return root


def _source_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> SourceDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, SourceDef) and definition.name == name:
                return definition
    raise AssertionError(f"Source definition not found: {name}")


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


def _git_diff_names(relative_path: str) -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", relative_path],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return tuple(result.stdout.splitlines())
