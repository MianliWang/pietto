from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
import subprocess
import tomllib

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFact,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
    ProjectRowLineageSegment,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import QueryDef, TableDef
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_lineage.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
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

ALLOWED_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-computed-let-multi-hop-row-lineage-v1.md",
    "src/pietto/_project/row_lineage.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
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

FORBIDDEN_FILES = (
    "src/pietto/_project/json_v2.py",
    "src/pietto/_project/check.py",
    "src/pietto/_project/row_dependency_graph.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/semantic/let_bindings.py",
)

PRIVATE_JSON_FACTS = (
    "relation_row_lineages",
    "ProjectRelationRowLineage",
    "ProjectRowLineageSegment",
    "ProjectRowLineageFact",
    "ProjectRowLineageStatus",
    "ProjectRowLineageReason",
    "let_binding",
    "source_field",
    "upstream_field",
    "output_field",
    "direct_projection",
    "renamed_projection",
    "computed_expression",
    "let_output",
    "let_expression",
    "transitive_dependency",
    "lineage",
    "dependency",
    "relation_row_dependency_graphs",
    "relation_row_schemas",
    "relation_let_scope_facts",
    "ProjectRowSchema",
    "ProjectRowField",
    "provenance",
    "direct_source_concrete",
    "missing_dependency_graph",
)

SLICE14_BASE_HEAD = "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52"
SLICE15_BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
SLICE14_ALLOWED_FORBIDDEN_DIFF_PATHS = {
    "src/pietto/_project/row_dependency_graph.py",
}


def _phase53_gate2_paths(name: str) -> set[str]:
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


def test_row_lineage_carriers_are_private_frozen_dataclasses() -> None:
    for model_type in (
        ProjectRowLineageSegment,
        ProjectRowLineageFact,
        ProjectRelationRowLineage,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    output_segment = ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.OUTPUT_FIELD,
        name="id",
        relation_name="projected",
        output_name="id",
    )
    source_segment = ProjectRowLineageSegment(
        kind=ProjectRowLineageSegmentKind.SOURCE_FIELD,
        name="users.id",
        source_name="users",
        field_name="id",
    )
    fact = ProjectRowLineageFact(
        kind=ProjectRowLineageFactKind.DIRECT_PROJECTION,
        output_segment=output_segment,
        upstream_segment=source_segment,
    )
    lineage = ProjectRelationRowLineage(
        status=ProjectRowLineageStatus.CONCRETE,
        reason=ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
        facts=(fact,),
    )

    assert lineage.facts == (fact,)
    assert not hasattr(lineage, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(lineage, "facts", ())


def test_direct_and_renamed_source_projection_lineage_is_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert lineage.status is ProjectRowLineageStatus.CONCRETE
    assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert _fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.RENAMED_PROJECTION,
            "user_email",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.email",
        ),
    )


def test_relation_backed_lineage_preserves_immediate_and_adds_transitive(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        user_id = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    lineage = semantic_result.model.relation_row_lineages[exported]

    assert lineage.status is ProjectRowLineageStatus.CONCRETE
    assert lineage.reason is ProjectRowLineageReason.RELATION_UPSTREAM_CONCRETE
    assert _fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.RENAMED_PROJECTION,
            "user_id",
            ProjectRowLineageSegmentKind.UPSTREAM_FIELD,
            "seed.id",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "user_id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
    )


def test_computed_alias_lineage_is_recorded_after_slice11(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert _fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.COMPUTED_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_selected_let_derived_lineage_is_recorded_after_slice11(
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
            "        id\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]
    lineage = semantic_result.model.relation_row_lineages[projected]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    assert _fact_values(lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "id",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.id",
        ),
        (
            ProjectRowLineageFactKind.LET_OUTPUT,
            "total",
            ProjectRowLineageSegmentKind.LET_BINDING,
            "total",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.TRANSITIVE_DEPENDENCY,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
        (
            ProjectRowLineageFactKind.LET_EXPRESSION,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.bonus",
        ),
    )


def test_non_concrete_row_schema_states_produce_non_concrete_lineage(
    tmp_path: Path,
) -> None:
    unknown_parse, unknown_semantic = _project_semantic_result(
        _project(
            tmp_path / "unknown",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )
    grouped_parse, grouped_semantic = _project_semantic_result(
        _project(
            tmp_path / "grouped",
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )
    cycle_parse, cycle_semantic = _project_semantic_result(
        _project(
            tmp_path / "cycle",
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

    assert unknown_semantic.model is not None
    broken = _derived_definition(unknown_parse, "broken")
    broken_lineage = unknown_semantic.model.relation_row_lineages[broken]
    assert broken_lineage.status is ProjectRowLineageStatus.UNKNOWN
    assert broken_lineage.reason is ProjectRowLineageReason.UNKNOWN_SCHEMA
    assert broken_lineage.facts == ()

    assert grouped_semantic.model is not None
    grouped = _derived_definition(grouped_parse, "grouped")
    grouped_lineage = grouped_semantic.model.relation_row_lineages[grouped]
    assert grouped_lineage.status is ProjectRowLineageStatus.CONCRETE
    assert grouped_lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
    assert _fact_values(grouped_lineage) == (
        (
            ProjectRowLineageFactKind.DIRECT_PROJECTION,
            "status",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.status",
        ),
        (
            ProjectRowLineageFactKind.AGGREGATE_ARGUMENT,
            "total",
            ProjectRowLineageSegmentKind.SOURCE_FIELD,
            "users.score",
        ),
    )

    assert cycle_semantic.model is not None
    first = _derived_definition(cycle_parse, "first")
    first_lineage = cycle_semantic.model.relation_row_lineages[first]
    assert first_lineage.status is ProjectRowLineageStatus.BLOCKED
    assert first_lineage.reason is ProjectRowLineageReason.CYCLE_BLOCKED
    assert first_lineage.facts == ()


def test_project_json_v2_keeps_row_lineage_private(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_lineages
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


def test_row_lineage_module_does_not_call_full_semantic_analyze() -> None:
    module = (REPO_ROOT / "src/pietto/_project/row_lineage.py").read_text(
        encoding="utf-8"
    )

    assert "semantic_api.analyze" not in module
    assert "from pietto.semantic import analyze" not in module
    assert "import pietto.semantic as semantic_api" not in module


def test_slice10_forbidden_files_have_no_diff() -> None:
    status_lines = _git_output(
        ["status", "--porcelain=v1", "--untracked-files=all"]
    ).splitlines()
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    exact_slice14_dirty = (
        {line[3:] for line in status_lines if line.startswith(" M ")}
        == slice14_modified
        and {line[3:] for line in status_lines if line.startswith("?? ")}
        == slice14_added
        and len(status_lines) == len(slice14_modified | slice14_added)
    )
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    assert SLICE14_ALLOWED_FORBIDDEN_DIFF_PATHS <= set(FORBIDDEN_FILES)
    if exact_slice14_dirty:
        assert _git_output(["branch", "--show-current"]) == "main"
        assert (
            tuple(
                _git_output(["rev-parse", reference])
                for reference in (
                    "HEAD",
                    "refs/heads/main",
                    "refs/remotes/origin/main",
                )
            )
            == (SLICE15_BASE_HEAD,) * 3
        )
        assert _git_output(["rev-parse", "--is-shallow-repository"]) == "false"
        worktrees = _git_output(["worktree", "list", "--porcelain"])
        assert sum(line.startswith("worktree ") for line in worktrees.splitlines()) == 1
    for relative_path in FORBIDDEN_FILES:
        if (
            _git_output(["rev-parse", "HEAD"]) == SLICE14_BASE_HEAD
            and relative_path in SLICE14_ALLOWED_FORBIDDEN_DIFF_PATHS
        ):
            assert _git_diff(relative_path) != ""
            continue
        assert _git_diff(relative_path) == ""


def test_slice10_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    phase53_gate2_paths = _phase53_gate2_paths("ADDED_PATHS") | _phase53_gate2_paths(
        "MODIFIED_PATHS"
    )

    assert project["version"] == "0.1.0"
    assert (
        _git_status_paths()
        in (
            set(),
            ALLOWED_SLICE10_GATE2_PATHS,
            ALLOWED_SLICE11_GATE2_PATHS,
            phase53_gate2_paths,
        )
    ) or _slice5_gate2()


def _fact_values(
    lineage: ProjectRelationRowLineage,
) -> tuple[
    tuple[
        ProjectRowLineageFactKind,
        str,
        ProjectRowLineageSegmentKind,
        str,
    ],
    ...,
]:
    return tuple(
        (
            fact.kind,
            fact.output_segment.name,
            fact.upstream_segment.kind,
            fact.upstream_segment.name,
        )
        for fact in lineage.facts
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(
    root: Path,
    relation_source: str,
    *,
    include_source: bool = True,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    source_prefix = (
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int not null\n"
        "    bonus: Int nullable\n"
        "    status: Text not null\n"
    )
    if include_source:
        source_prefix += 'source users: User is postgres.table("users")\n'
    (root / "models.pietto").write_text(
        source_prefix + relation_source,
        encoding="utf-8",
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
    raise AssertionError(f"Missing derived definition: {name}")


def _git_diff(relative_path: str) -> str:
    return _git_output(["diff", "--", relative_path])


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--short", "--untracked-files=all"])
    return {line[3:] for line in output.splitlines() if line}


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.rstrip()
