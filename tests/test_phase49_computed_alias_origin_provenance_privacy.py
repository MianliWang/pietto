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

ALLOWED_SLICE5_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-computed-alias-origin-provenance-privacy-v1.md",
    "src/pietto/_project/model.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
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

ALLOWED_SLICE7_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-selected-let-derived-output-schema-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/semantic/let_bindings.py",
    "tests/test_phase49_selected_let_derived_output_schema.py",
    "tests/test_phase49_project_let_scope_value_facts.py",
    "tests/test_phase49_computed_alias_project_row_schema_mvp.py",
    "tests/test_phase49_computed_alias_origin_provenance_privacy.py",
    "tests/test_phase40_let_binding_row_level_semantics.py",
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
    "ProjectRowFieldProvenanceKind",
    "provenance",
    "origin",
    "DERIVED_EXPRESSION",
    "derived_expression",
    "row_expression_schema",
    "row_expression_type_facts",
    "dependency_placeholders",
    "lineage_placeholders",
)


def test_computed_alias_uses_private_derived_expression_provenance(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query scored:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    scored = _derived_definition(parse_result, "scored")
    total = semantic_result.model.relation_row_schemas[scored].fields["total"]

    assert total.name == "total"
    assert total.resolved_type.name == "Int"
    assert total.nullability is ProjectRowFieldNullability.UNKNOWN
    assert total.field_def is None
    assert total.provenance is not None
    assert total.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert (
        total.provenance.symbol
        is semantic_result.model.relation_resolutions[scored.from_clause]
    )
    assert total.provenance.location is not None
    assert total.provenance.location.path == "models.pietto"
    _assert_state(
        semantic_result,
        scored,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )


def test_direct_and_renamed_projection_keep_existing_source_native_behavior(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query renamed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_id = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    renamed = _derived_definition(parse_result, "renamed")
    source_schema = semantic_result.model.source_row_schemas[users]
    row_schema = semantic_result.model.relation_row_schemas[renamed]
    source_symbol = semantic_result.model.relation_resolutions[renamed.from_clause]

    _assert_direct_projection_field(
        relation_field=row_schema.fields["id"],
        source_field=source_schema.fields["id"],
        source_symbol=source_symbol,
        expected_name="id",
    )
    _assert_direct_projection_field(
        relation_field=row_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=source_symbol,
        expected_name="user_id",
    )


def test_multi_hop_computed_alias_stays_derived_and_non_source_native(
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
    seed_total = semantic_result.model.relation_row_schemas[seed].fields["total"]
    exported_total = semantic_result.model.relation_row_schemas[exported].fields[
        "total"
    ]
    final_total = semantic_result.model.relation_row_schemas[final].fields[
        "final_total"
    ]

    assert seed_total.field_def is None
    assert seed_total.provenance is not None
    assert (
        seed_total.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    )
    assert exported_total.field_def is None
    assert final_total.field_def is None
    assert final_total.resolved_type.name == "Int"


def test_let_aggregate_and_grouped_outputs_remain_out_of_scope(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query let_output:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + 1\n"
            "    select:\n"
            "        total\n"
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
    let_output = _derived_definition(parse_result, "let_output")
    total = semantic_result.model.relation_row_schemas[let_output].fields["total"]
    assert total.field_def is None
    assert total.provenance is not None
    assert total.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    aggregate = _derived_definition(parse_result, "aggregate")
    aggregate_schema = semantic_result.model.relation_row_schemas[aggregate]
    assert tuple(aggregate_schema.fields) == ("total",)
    assert aggregate_schema.fields["total"].field_def is None
    assert aggregate_schema.fields["total"].provenance is not None
    assert aggregate_schema.fields["total"].provenance.kind is (
        ProjectRowFieldProvenanceKind.AGGREGATE
    )
    assert tuple(semantic_result.model.relation_aggregate_result_facts[aggregate]) == (
        "total",
    )
    _assert_state(
        semantic_result,
        aggregate,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )

    grouped = _derived_definition(parse_result, "grouped")
    assert grouped not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.DEFERRED,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )


def test_project_json_v2_keeps_derived_expression_provenance_private(
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


def test_slice5_forbidden_project_files_are_untouched() -> None:
    for relative_path in (
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
    ):
        assert _git_diff_names(relative_path) == ()


def test_slice5_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    dirty_paths = _git_status_paths()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert dirty_paths in (
        set(),
        ALLOWED_SLICE5_GATE2_PATHS,
        ALLOWED_SLICE7_GATE2_PATHS,
    )


def _assert_direct_projection_field(
    *,
    relation_field: ProjectRowField,
    source_field: ProjectRowField,
    source_symbol: object,
    expected_name: str,
) -> None:
    assert relation_field.name == expected_name
    assert relation_field.resolved_type is source_field.resolved_type
    assert relation_field.nullability is source_field.nullability
    assert relation_field.field_def is source_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )
    assert relation_field.provenance.symbol is source_symbol


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
        "    email: Text\n"
        "    score: Int\n"
        "    bonus: Int\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_source}",
    )
    return root


def _project_root(path: Path, *, include: tuple[str, ...]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    include_text = ", ".join(f'"{pattern}"' for pattern in include)
    _write(
        path,
        "pietto.toml",
        f"schema_version = 1\n\n[sources]\ninclude = [{include_text}]\n",
    )
    return path


def _write(root: Path, relative_path: str, text: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    raise AssertionError(f"Derived definition not found: {name}")


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _git_diff_names(relative_path: str) -> tuple[str, ...]:
    return tuple(_git_output(["diff", "--name-only", "--", relative_path]).splitlines())


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout
