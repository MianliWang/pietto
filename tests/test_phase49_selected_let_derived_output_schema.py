from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tomllib

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
)
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
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
)
from pietto._project.row_lineage import (
    ProjectRowLineageReason,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

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
    "relation_let_scope_facts",
    "ProjectRelationLetScopeFacts",
    "ProjectLetScopeFactsStatus",
    "ProjectLetScopeFactsReason",
    "relation_row_schemas",
    "ProjectRowSchema",
    "ProjectRowField",
    "ProjectRowFieldProvenance",
    "ProjectRowFieldProvenanceKind",
    "LET_DERIVED",
    "let_derived",
    "provenance",
    "origin",
    "dependency",
    "lineage",
    "value_types",
    "upstream_concrete",
    "let_diagnostics_suppressed",
)


def test_selected_bare_let_output_becomes_private_row_field(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    facts = semantic_result.model.relation_let_scope_facts[projected]
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert facts.reason is ProjectLetScopeFactsReason.UPSTREAM_CONCRETE
    assert tuple(facts.value_types) == ("total",)
    assert facts.value_types["total"].resolved_type.name == field.resolved_type.name
    assert field.name == "total"
    assert field.resolved_type.name == "Int"
    assert field.nullability is ProjectRowFieldNullability.UNKNOWN
    _assert_let_derived_field(field, expected_symbol_name="users")


def test_aliased_selected_let_reference_is_private_let_derived(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        exported_total = total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields[
        "exported_total"
    ]

    assert tuple(semantic_result.model.relation_row_schemas[projected].fields) == (
        "exported_total",
    )
    assert field.resolved_type.name == "Int"
    assert field.nullability is ProjectRowFieldNullability.UNKNOWN
    _assert_let_derived_field(field, expected_symbol_name="users")


def test_direct_input_field_keeps_priority_and_source_native_field_def(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        score = bonus\n"
            "    select:\n"
            "        score\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    users = _source_definition(parse_result, "users")
    relation_field = semantic_result.model.relation_row_schemas[projected].fields[
        "score"
    ]
    source_field = semantic_result.model.source_row_schemas[users].fields["score"]
    facts = semantic_result.model.relation_let_scope_facts[projected]

    assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
    assert relation_field.field_def is source_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def test_invalid_let_facts_do_not_make_selected_let_outputs_concrete(
    tmp_path: Path,
) -> None:
    cases = {
        "duplicate": (
            "query duplicate:\n"
            "    from users\n"
            "    let:\n"
            "        total = score\n"
            "        total = bonus\n"
            "    select:\n"
            "        total\n",
            "duplicate",
        ),
        "self_reference": (
            "query self_reference:\n"
            "    from users\n"
            "    let:\n"
            "        total = total + bonus\n"
            "    select:\n"
            "        total\n",
            "self_reference",
        ),
        "later_reference": (
            "query later_reference:\n"
            "    from users\n"
            "    let:\n"
            "        total = subtotal + bonus\n"
            "        subtotal = score\n"
            "    select:\n"
            "        total\n",
            "later_reference",
        ),
        "aggregate_let": (
            "query aggregate_let:\n"
            "    from users\n"
            "    let:\n"
            "        total = sum(score)\n"
            "    select:\n"
            "        total\n",
            "aggregate_let",
        ),
    }

    for relation_source, relation_name in cases.values():
        parse_result, semantic_result = _project_semantic_result(
            _project(tmp_path / relation_name, relation_source)
        )
        assert not semantic_result.ok
        assert semantic_result.model is not None
        definition = _derived_definition(parse_result, relation_name)
        facts = semantic_result.model.relation_let_scope_facts[definition]

        assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
        assert facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
        assert semantic_result.model.relation_row_schemas[definition].is_unknown
        assert _diagnostics(semantic_result) == [("PIE-S2102", "Unknown field: total")]


def test_alias_conflict_remains_non_concrete_let_fact(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        total = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    facts = semantic_result.model.relation_let_scope_facts[projected]
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
    assert field.field_def is not None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION


def test_qualified_let_reference_does_not_become_concrete(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        exported_total = users.total\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    assert semantic_result.model.relation_row_schemas[projected].is_unknown
    assert _diagnostics(semantic_result) == [
        ("PIE-S2102", "Unknown field: users.total")
    ]


def test_upstream_non_concrete_and_grouped_outputs_remain_non_concrete(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query missing_upstream:\n"
            "    from missing\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        total\n"
            "query grouped:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    group by:\n"
            "        email\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    missing_upstream = _derived_definition(parse_result, "missing_upstream")
    grouped = _derived_definition(parse_result, "grouped")

    _assert_state(
        semantic_result,
        missing_upstream,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_let_state(
        semantic_result,
        missing_upstream,
        ProjectLetScopeFactsStatus.BLOCKED,
        ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
    )
    _assert_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )
    grouped_schema = semantic_result.model.relation_row_schemas[grouped]
    assert grouped_schema.is_unknown
    assert grouped_schema.fields == {}
    assert grouped not in semantic_result.model.relation_aggregate_result_facts
    grouped_graph = semantic_result.model.relation_row_dependency_graphs[grouped]
    assert grouped_graph.status is ProjectRowDependencyGraphStatus.UNKNOWN
    assert grouped_graph.reason is (
        ProjectRowDependencyGraphReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    assert grouped_graph.nodes == ()
    assert grouped_graph.edges == ()
    grouped_lineage = semantic_result.model.relation_row_lineages[grouped]
    assert grouped_lineage.status is ProjectRowLineageStatus.UNKNOWN
    assert grouped_lineage.reason is (
        ProjectRowLineageReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    assert grouped_lineage.facts == ()


def test_multi_hop_projection_preserves_non_source_native_field_def(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        total\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        final_total = total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    seed_total = semantic_result.model.relation_row_schemas[seed].fields["total"]
    final_total = semantic_result.model.relation_row_schemas[exported].fields[
        "final_total"
    ]

    _assert_let_derived_field(seed_total, expected_symbol_name="users")
    assert final_total.field_def is None
    assert final_total.provenance is not None
    assert (
        final_total.provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def test_computed_aliases_stay_derived_expression(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    total = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert total.field_def is None
    assert total.provenance is not None
    assert total.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION


def test_project_json_v2_keeps_selected_let_schema_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

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


def test_slice7_forbidden_files_remain_unchanged() -> None:
    for relative_path in (
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
    ):
        assert _git_diff(relative_path) == ""


def test_slice7_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]

    assert project["version"] == "0.1.0"
    assert _git_status_paths() in (set(), ALLOWED_SLICE7_GATE2_PATHS)


def _assert_let_derived_field(
    field: ProjectRowField,
    *,
    expected_symbol_name: str,
) -> None:
    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    assert field.provenance.symbol is not None
    assert field.provenance.symbol.name == expected_symbol_name


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


def _assert_let_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectLetScopeFactsStatus,
    reason: ProjectLetScopeFactsReason,
) -> None:
    assert semantic_result.model is not None
    facts = semantic_result.model.relation_let_scope_facts[definition]
    assert facts.status is status
    assert facts.reason is reason
    assert tuple(facts.value_types) == ()


def _diagnostics(result: ProjectSemanticResult) -> list[tuple[str, str]]:
    return [(diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics]


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
        "    email: Text not null\n"
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


def _git_diff(relative_path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--", relative_path],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout
