from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
)
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.semantic.model import EffectiveNullability, ValueTypeKind

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE6_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-project-let-scope-value-facts-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "tests/test_phase49_project_let_scope_value_facts.py",
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
    "relation_let_scope_facts",
    "ProjectRelationLetScopeFacts",
    "ProjectLetScopeFactsStatus",
    "ProjectLetScopeFactsReason",
    "let_scope_facts",
    "binding_expressions",
    "value_types",
    "upstream_concrete",
    "upstream_unknown",
    "upstream_deferred",
    "upstream_blocked",
    "let_diagnostics_suppressed",
    "missing_or_unknown_value_type",
)


def test_legal_let_bindings_produce_private_value_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query enriched:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "        is_positive = total > 0\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    enriched = _derived_definition(parse_result, "enriched")
    facts = semantic_result.model.relation_let_scope_facts[enriched]

    assert facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert facts.reason is ProjectLetScopeFactsReason.UPSTREAM_CONCRETE
    assert facts.clause is enriched.let_clause
    assert tuple(binding.name for binding in facts.bindings) == (
        "total",
        "is_positive",
    )
    assert tuple(facts.binding_expressions) == ("total", "is_positive")
    assert facts.binding_expressions["total"] is facts.bindings[0].expression
    assert facts.binding_expressions["is_positive"] is facts.bindings[1].expression
    assert tuple(facts.value_types) == ("total", "is_positive")

    total_type = facts.value_types["total"]
    assert total_type.kind is ValueTypeKind.KNOWN
    assert total_type.resolved_type.name == "Int"
    assert total_type.nullability is EffectiveNullability.UNKNOWN

    positive_type = facts.value_types["is_positive"]
    assert positive_type.kind is ValueTypeKind.KNOWN
    assert positive_type.resolved_type.name == "Bool"
    assert positive_type.nullability is EffectiveNullability.UNKNOWN


def test_absent_let_clause_has_deterministic_absent_facts(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query passthrough:\n    from users\n    select:\n        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    passthrough = _derived_definition(parse_result, "passthrough")
    facts = semantic_result.model.relation_let_scope_facts[passthrough]

    assert facts.status is ProjectLetScopeFactsStatus.ABSENT
    assert facts.reason is ProjectLetScopeFactsReason.NO_LET_CLAUSE
    assert facts.clause is None
    assert facts.bindings == ()
    assert tuple(facts.binding_expressions) == ()
    assert tuple(facts.value_types) == ()


def test_selected_let_output_uses_concrete_private_let_facts(
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

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert field.resolved_type.name == "Int"
    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED

    facts = semantic_result.model.relation_let_scope_facts[projected]
    assert facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert facts.reason is ProjectLetScopeFactsReason.UPSTREAM_CONCRETE
    assert tuple(facts.binding_expressions) == ("total",)
    assert tuple(facts.value_types) == ("total",)


def test_upstream_non_concrete_states_short_circuit_let_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query unknown_seed:\n"
            "    from users\n"
            "    select:\n"
            "        missing\n"
            "query from_unknown:\n"
            "    from unknown_seed\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        id\n"
            "query deferred_seed:\n"
            "    from users\n"
            "    select:\n"
            "        ratio = score / bonus\n"
            "query from_deferred:\n"
            "    from deferred_seed\n"
            "    let:\n"
            "        total = ratio + 1\n"
            "    select:\n"
            "        ratio\n"
            "query unresolved:\n"
            "    from missing_relation\n"
            "    let:\n"
            "        total = id + 1\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    _assert_let_state(
        semantic_result,
        _derived_definition(parse_result, "from_unknown"),
        ProjectLetScopeFactsStatus.UNKNOWN,
        ProjectLetScopeFactsReason.UPSTREAM_UNKNOWN,
    )
    _assert_let_state(
        semantic_result,
        _derived_definition(parse_result, "from_deferred"),
        ProjectLetScopeFactsStatus.DEFERRED,
        ProjectLetScopeFactsReason.UPSTREAM_DEFERRED,
    )
    _assert_let_state(
        semantic_result,
        _derived_definition(parse_result, "unresolved"),
        ProjectLetScopeFactsStatus.BLOCKED,
        ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
    )


def test_computed_alias_behavior_from_slice5_is_unchanged(tmp_path: Path) -> None:
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


def test_direct_renamed_multi_hop_projection_behavior_is_unchanged(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        user_id = id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        final_id = user_id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    seed_field = semantic_result.model.relation_row_schemas[seed].fields["user_id"]
    final_field = semantic_result.model.relation_row_schemas[exported].fields[
        "final_id"
    ]

    _assert_direct_field_preserves_source_field_def(seed_field, source_field)
    _assert_direct_field_preserves_source_field_def(final_field, source_field)
    assert tuple(semantic_result.model.relation_let_scope_facts[seed].value_types) == ()
    assert (
        tuple(semantic_result.model.relation_let_scope_facts[exported].value_types)
        == ()
    )


def test_project_json_v2_keeps_let_scope_facts_private(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query enriched:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        id\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    enriched = _derived_definition(parse_result, "enriched")
    assert enriched in semantic_result.model.relation_let_scope_facts
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


def test_slice6_forbidden_project_files_are_untouched() -> None:
    for relative_path in (
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/row_expression_schema.py",
    ):
        assert _git_diff_names(relative_path) == ()


def test_slice6_helper_uses_narrow_private_let_analysis_only() -> None:
    helper = (REPO_ROOT / "src/pietto/_project/let_scope_facts.py").read_text(
        encoding="utf-8"
    )

    assert "analyze_relation_let_bindings" in helper
    assert "semantic_api.analyze" not in helper
    assert "from pietto.semantic import analyze" not in helper
    assert "import pietto.semantic as semantic_api" not in helper
    assert "infer_row_expression" not in helper


def test_phase49_slice6_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    dirty_paths = _git_status_paths()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert dirty_paths in (
        set(),
        ALLOWED_SLICE6_GATE2_PATHS,
        ALLOWED_SLICE7_GATE2_PATHS,
    )


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


def _assert_direct_field_preserves_source_field_def(
    relation_field: ProjectRowField,
    source_field: ProjectRowField,
) -> None:
    assert relation_field.resolved_type is source_field.resolved_type
    assert relation_field.nullability is source_field.nullability
    assert relation_field.field_def is source_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


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
        "    bonus: Int not null\n"
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
