from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tomllib

import pytest

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
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-let-visibility-order-shadowing-hardening-v1.md",
    "tests/test_phase49_let_visibility_order_shadowing_hardening.py",
}

FORBIDDEN_FILES = (
    "src/pietto/_project/json_v2.py",
    "src/pietto/_project/check.py",
    "src/pietto/_project/model.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/semantic/let_bindings.py",
)

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
    "missing_or_unknown_value_type",
)

SINGLE_FILE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int nullable\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_public_single_file_default_rejects_unaliased_selected_let_output() -> None:
    semantic = _analyze_single_file(
        "query projected:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross\n"
    )

    assert "PIE-S2329" in _error_codes(semantic)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        gross = amount - tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        amount = tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        orders = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = gross + tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net + tax\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = sum(amount)\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2308",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        net = orders.gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
        ),
    ],
)
def test_public_let_visibility_order_and_shadowing_fail_closed(
    body: str,
    expected_code: str,
) -> None:
    semantic = _analyze_single_file("query boundary:\n" + body)

    assert expected_code in _error_codes(semantic)


def test_project_private_exact_unaliased_selected_let_output_is_let_derived(
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
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    facts = semantic_result.model.relation_let_scope_facts[projected]
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert facts.status is ProjectLetScopeFactsStatus.CONCRETE
    assert facts.reason is ProjectLetScopeFactsReason.UPSTREAM_CONCRETE
    assert tuple(facts.value_types) == ("total",)
    _assert_let_derived_field(field)


def test_project_direct_input_field_keeps_priority_over_local_let(
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
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    projected = _derived_definition(parse_result, "projected")
    source_field = semantic_result.model.source_row_schemas[users].fields["score"]
    field = semantic_result.model.relation_row_schemas[projected].fields["score"]
    facts = semantic_result.model.relation_let_scope_facts[projected]

    assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
    assert field.field_def is source_field.field_def
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION


def test_project_aliased_selected_let_reference_is_let_derived(
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
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields[
        "exported_total"
    ]

    _assert_let_derived_field(field)


def test_project_alias_output_conflict_keeps_let_facts_non_concrete(
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
            "        total = id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    facts = semantic_result.model.relation_let_scope_facts[projected]
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert facts.status is ProjectLetScopeFactsStatus.UNKNOWN
    assert facts.reason is ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION


@pytest.mark.parametrize(
    ("relation_name", "relation_source", "expected_message"),
    [
        (
            "duplicate",
            "query duplicate:\n"
            "    from users\n"
            "    let:\n"
            "        total = score\n"
            "        total = bonus\n"
            "    select:\n"
            "        total\n",
            "Unknown field: total",
        ),
        (
            "source_shadow",
            "query source_shadow:\n"
            "    from users\n"
            "    let:\n"
            "        users = score\n"
            "    select:\n"
            "        users\n",
            "Unknown field: users",
        ),
        (
            "self_reference",
            "query self_reference:\n"
            "    from users\n"
            "    let:\n"
            "        total = total + bonus\n"
            "    select:\n"
            "        total\n",
            "Unknown field: total",
        ),
        (
            "later_reference",
            "query later_reference:\n"
            "    from users\n"
            "    let:\n"
            "        total = subtotal + bonus\n"
            "        subtotal = score\n"
            "    select:\n"
            "        total\n",
            "Unknown field: total",
        ),
        (
            "aggregate_let",
            "query aggregate_let:\n"
            "    from users\n"
            "    let:\n"
            "        total = sum(score)\n"
            "    select:\n"
            "        total\n",
            "Unknown field: total",
        ),
    ],
)
def test_project_invalid_let_cases_do_not_make_selected_outputs_concrete(
    tmp_path: Path,
    relation_name: str,
    relation_source: str,
    expected_message: str,
) -> None:
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
    assert ("PIE-S2102", expected_message) in _diagnostics(semantic_result)


def test_project_qualified_let_reference_stays_unknown(tmp_path: Path) -> None:
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


def test_project_grouped_selected_let_output_schema_remains_deferred(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
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

    assert semantic_result.ok
    assert semantic_result.model is not None
    grouped = _derived_definition(parse_result, "grouped")
    state = semantic_result.model.relation_row_schema_states[grouped]

    assert state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert state.reason is ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
    assert grouped not in semantic_result.model.relation_row_schemas


def test_project_multi_hop_let_derived_field_keeps_field_def_none(
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
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    seed_total = semantic_result.model.relation_row_schemas[seed].fields["total"]
    final_total = semantic_result.model.relation_row_schemas[exported].fields[
        "final_total"
    ]

    _assert_let_derived_field(seed_total)
    assert final_total.field_def is None
    assert final_total.provenance is not None
    assert (
        final_total.provenance.kind is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def test_project_computed_alias_remains_derived_expression(tmp_path: Path) -> None:
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
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    field = semantic_result.model.relation_row_schemas[projected].fields["total"]

    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION


def test_project_json_v2_keeps_slice8_private_facts_private(
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


def test_slice8_forbidden_files_have_no_diff() -> None:
    for relative_path in FORBIDDEN_FILES:
        assert _git_diff(relative_path) == ""


def test_slice8_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]

    assert project["version"] == "0.1.0"
    assert _git_status_paths() in (set(), ALLOWED_SLICE8_GATE2_PATHS)


def _analyze_single_file(source: str) -> SemanticResult:
    result = parse_source(SINGLE_FILE_PREFIX + source, path="slice8_let.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_let_derived_field(field: ProjectRowField) -> None:
    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED


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
