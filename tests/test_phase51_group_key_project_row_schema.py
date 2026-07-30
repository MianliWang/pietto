from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, fields, is_dataclass
import inspect
import json
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
from pietto._project.aggregate_grouped_schema import (
    ProjectGroupKeyFact,
    ProjectGroupKeySchemaFacts,
    build_project_group_key_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_schema.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase51-group-key-project-row-schema-foundation-v1.md"
)

EXPECTED_PROJECT_JSON_V2_KEYS = (
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


def test_group_key_carriers_are_exact_frozen_slots_and_fail_closed(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, definition, input_schema, upstream_symbol = (
        _group_key_inputs(
            tmp_path,
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
        )
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)
    assert parse_result.ok
    assert semantic_result.model is not None
    assert tuple(field.name for field in fields(ProjectGroupKeyFact)) == (
        "item",
        "effective_expression",
        "field_identity",
        "input_field",
    )
    assert tuple(field.name for field in fields(ProjectGroupKeySchemaFacts)) == (
        "group_keys",
        "selected_fields",
    )
    assert is_dataclass(ProjectGroupKeyFact)
    assert is_dataclass(ProjectGroupKeySchemaFacts)
    assert hasattr(ProjectGroupKeyFact, "__slots__")
    assert hasattr(ProjectGroupKeySchemaFacts, "__slots__")
    assert not hasattr(facts, "__dict__")

    with pytest.raises(FrozenInstanceError):
        setattr(facts, "group_keys", ())
    with pytest.raises(ValueError, match="tuple"):
        ProjectGroupKeySchemaFacts(
            group_keys=cast(Any, list(facts.group_keys)),
            selected_fields=facts.selected_fields,
        )
    with pytest.raises(ValueError, match="GROUP_KEY"):
        ProjectGroupKeySchemaFacts(
            group_keys=facts.group_keys,
            selected_fields={
                next(iter(facts.selected_fields)): facts.group_keys[0].input_field
            },
        )


def test_selected_fields_are_defensive_readonly_and_keep_select_item_order(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        first = status\n"
        "        second = users.status\n"
        "        total = count()\n",
    )
    built = _build_facts(definition, input_schema, upstream_symbol)
    caller_fields = dict(built.selected_fields)
    copied = ProjectGroupKeySchemaFacts(
        group_keys=built.group_keys,
        selected_fields=caller_fields,
    )
    caller_fields.clear()

    assert isinstance(copied.selected_fields, MappingProxyType)
    assert tuple(item.alias for item in copied.selected_fields) == ("first", "second")
    assert tuple(field.name for field in copied.selected_fields.values()) == (
        "first",
        "second",
    )
    with pytest.raises(TypeError):
        cast(
            MutableMapping[SelectItem, ProjectRowField],
            copied.selected_fields,
        )[next(iter(copied.selected_fields))] = built.group_keys[0].input_field


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_bare_qualified_renamed_and_repeated_selected_keys_are_exact(
    tmp_path: Path,
    relation_kind: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        f"{relation_kind} grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.region\n"
        "    select:\n"
        "        renamed = status\n"
        "        users.region\n"
        "        second_status = users.status\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert isinstance(facts.group_keys[0].effective_expression, NameExpr)
    assert isinstance(facts.group_keys[1].effective_expression, DottedNameExpr)
    assert tuple(field.name for field in facts.selected_fields.values()) == (
        "renamed",
        "region",
        "second_status",
    )
    selected_items = tuple(facts.selected_fields)
    selected_fields = tuple(facts.selected_fields.values())
    assert tuple(item.alias for item in selected_items) == (
        "renamed",
        None,
        "second_status",
    )

    status_field = selected_fields[0]
    region_field = selected_fields[1]
    assert status_field.resolved_type is input_schema.fields["status"].resolved_type
    assert status_field.nullability is ProjectRowFieldNullability.NON_NULL
    assert status_field.field_def is input_schema.fields["status"].field_def
    assert region_field.resolved_type is input_schema.fields["region"].resolved_type
    assert region_field.nullability is ProjectRowFieldNullability.NULLABLE
    assert region_field.field_def is input_schema.fields["region"].field_def
    for item, field in facts.selected_fields.items():
        assert field.result_role is ProjectRowResultRole.GROUP_KEY
        assert field.provenance is not None
        assert field.provenance.kind.value == "direct_projection"
        assert field.provenance.symbol is upstream_symbol
        assert field.provenance.location == _location(
            item, fallback_path="models.pietto"
        )


def test_unselected_keys_and_aggregate_only_select_have_no_selected_fields(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "table grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        region\n"
        "    select:\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert facts.selected_fields == {}
    group_key_builder_source = inspect.getsource(build_project_group_key_schema_facts)
    assert "ProjectAggregateResultFact" not in group_key_builder_source
    assert "build_project_aggregate_schema_facts" not in group_key_builder_source


def test_direct_and_chained_let_keys_preserve_clause_and_selected_identity(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "        region_key = users.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        key\n"
        "        bucket\n"
        "    select:\n"
        "        status\n"
        "        renamed = users.region\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert tuple(_group_item_text(fact) for fact in facts.group_keys) == (
        "key",
        "bucket",
    )
    assert tuple(fact.field_identity for fact in facts.group_keys) == (
        "status",
        "region",
    )
    assert isinstance(facts.group_keys[0].effective_expression, NameExpr)
    assert facts.group_keys[0].effective_expression.name == "status"
    assert isinstance(facts.group_keys[1].effective_expression, DottedNameExpr)
    assert facts.group_keys[1].effective_expression.parts == ("users", "region")
    assert tuple(field.name for field in facts.selected_fields.values()) == (
        "status",
        "renamed",
    )


def test_selecting_let_name_is_not_selected_underlying_group_key(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        key\n"
        "        total = count()\n",
    )

    assert (
        build_project_group_key_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


@pytest.mark.parametrize(
    "relation_body",
    (
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        wrong.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        catalog.users.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status + status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = lower(status)\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = 1\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        users.key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        missing\n"
        "    select:\n"
        "        total = count()\n",
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = lower(status)\n"
        "        total = count()\n",
    ),
)
def test_invalid_qualifier_let_key_unknown_and_scalar_select_return_no_candidate(
    tmp_path: Path,
    relation_body: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        relation_body,
    )

    assert (
        build_project_group_key_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


@pytest.mark.parametrize(
    "group_keys",
    (
        ("status", "users.status"),
        ("status", "key"),
        ("users.status", "key"),
    ),
)
def test_duplicate_equivalent_group_keys_have_no_first_winner(
    tmp_path: Path,
    group_keys: tuple[str, str],
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        f"        {group_keys[0]}\n"
        f"        {group_keys[1]}\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )

    assert (
        build_project_group_key_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )


def test_repeated_selected_key_duplicate_output_names_are_not_overwritten(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        duplicate = status\n"
        "        duplicate = users.status\n"
        "        total = count()\n",
    )
    facts = _build_facts(definition, input_schema, upstream_symbol)

    assert len(facts.selected_fields) == 2
    assert tuple(field.name for field in facts.selected_fields.values()) == (
        "duplicate",
        "duplicate",
    )


def test_unknown_incomplete_and_no_group_inputs_fail_closed(tmp_path: Path) -> None:
    _, _, grouped, input_schema, upstream_symbol = _group_key_inputs(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "query ordinary:\n"
        "    from users\n"
        "    select:\n"
        "        status\n",
        definition_name="grouped",
    )
    ordinary = _derived_definition(
        check_project_parse_only(tmp_path),
        "ordinary",
    )

    assert (
        build_project_group_key_schema_facts(
            definition=grouped,
            input_schema=ProjectRowSchema(is_unknown=True),
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    assert (
        build_project_group_key_schema_facts(
            definition=grouped,
            input_schema=ProjectRowSchema(fields={}),
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    unknown_field = ProjectRowField(
        name="status",
        resolved_type=ProjectResolvedType(
            name="<unknown>",
            kind=ProjectResolvedTypeKind.UNKNOWN,
        ),
        nullability=ProjectRowFieldNullability.UNKNOWN,
    )
    assert (
        build_project_group_key_schema_facts(
            definition=grouped,
            input_schema=ProjectRowSchema(fields={"status": unknown_field}),
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    with pytest.raises(ValueError, match="GROUP BY"):
        build_project_group_key_schema_facts(
            definition=ordinary,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )


def test_pure_grouping_stays_deferred_while_grouped_aggregate_is_concrete(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table pure:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "query mixed:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    model = semantic_result.model
    pure = _derived_definition(parse_result, "pure")
    mixed = _derived_definition(parse_result, "mixed")

    assert pure not in model.relation_row_schemas
    assert pure not in model.relation_aggregate_result_facts
    pure_state = model.relation_row_schema_states[pure]
    assert pure_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert pure_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_state.schema is None

    mixed_state = model.relation_row_schema_states[mixed]
    assert mixed_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert mixed_state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    mixed_schema = mixed_state.schema
    assert mixed_schema is not None
    assert mixed_schema is model.relation_row_schemas[mixed]
    assert tuple(mixed_schema.fields) == ("status", "total")
    assert mixed_schema.fields["status"].result_role is (ProjectRowResultRole.GROUP_KEY)
    assert mixed_schema.fields["total"].result_role is (
        ProjectRowResultRole.AGGREGATE_RESULT
    )
    assert tuple(model.relation_aggregate_result_facts[mixed]) == ("total",)


def test_helper_facts_are_not_persisted_exported_or_serialized(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        "query grouped:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)
    model_source = MODEL_PATH.read_text(encoding="utf-8")

    assert tuple(document) == EXPECTED_PROJECT_JSON_V2_KEYS
    assert project_package.__all__ == ()
    assert "aggregate_grouped_schema" not in model_source
    for name in (
        "ProjectGroupKeyFact",
        "ProjectGroupKeySchemaFacts",
        "build_project_group_key_schema_facts",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized


def test_contract_plan_and_helper_only_boundaries_are_locked() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    helper = HELPER_PATH.read_text(encoding="utf-8")
    group_key_builder_source = inspect.getsource(build_project_group_key_schema_facts)

    plan_lines = plan.splitlines()
    assert "### Slice 3 Gate 2 Bounded Implementation Status" in plan_lines
    assert "## Slice 3 Gate 2 Bounded Implementation Status" not in plan_lines
    for required in (
        "helper-only",
        "unpersisted",
        "ProjectGroupKeyFact",
        "ProjectGroupKeySchemaFacts",
        "build_project_group_key_schema_facts",
        "ProjectRowResultRole.GROUP_KEY",
        "DEFERRED_PHASE48_BEHAVIOR",
        "Phase 51 remains ACTIVE",
        "Phase 52–60 remain UNSTARTED",
        "/tmp/pietto-phase51-slice3-gate2-evidence-and-diff.txt",
    ):
        assert required in f"{plan}\n{spec}", required
    assert "ProjectAggregateResultFact(" not in group_key_builder_source
    assert "build_project_aggregate_schema_facts" not in group_key_builder_source
    assert "ProjectSemanticModel" not in helper


def test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff() -> None:
    forbidden_paths = (
        "src/pietto/_project/model.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/let_scope_facts.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/errors.py",
        "src/pietto/semantic",
        "src/pietto/ir",
        "src/pietto/sql",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_metadata",
        "grammar",
    )
    result = subprocess.run(
        ["git", "diff", "--exit-code", "--", *forbidden_paths],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert (result.returncode == 0) or _slice5_gate2()
    assert (result.stdout == "") or _slice5_gate2()
    assert result.stderr == ""


def _group_key_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "grouped",
) -> tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
]:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    assert semantic_result.model is not None
    definition = _derived_definition(parse_result, definition_name)
    source = _source_definition(parse_result, "users")
    input_schema = semantic_result.model.source_row_schemas[source]
    upstream_symbol = semantic_result.model.relation_resolutions[definition.from_clause]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
    )


def _build_facts(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> ProjectGroupKeySchemaFacts:
    facts = build_project_group_key_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert facts is not None
    return facts


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "shape User:\n"
        "    id: Int not null\n"
        "    status: Text not null\n"
        "    region: Text nullable\n"
        "    score: Int not null\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
        encoding="utf-8",
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


def _group_item_text(fact: ProjectGroupKeyFact) -> str:
    key = fact.item.key
    if isinstance(key, NameExpr):
        return key.name
    return ".".join(key.parts)


def _location(item: SelectItem, *, fallback_path: str) -> SourceLocation:
    span = item.expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
