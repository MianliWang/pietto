from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRoot,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_relation_row_schema_state_vocabulary_is_private_and_readiness_oriented() -> (
    None
):
    assert [status.name for status in ProjectRelationRowSchemaStatus] == [
        "CONCRETE",
        "UNKNOWN",
        "DEFERRED",
        "BLOCKED",
    ]
    assert [status.value for status in ProjectRelationRowSchemaStatus] == [
        "concrete",
        "unknown",
        "deferred",
        "blocked",
    ]

    reason_names = {reason.name for reason in ProjectRelationRowSchemaReason}
    assert {
        "DIRECT_SOURCE_CONCRETE",
        "TABLE_UPSTREAM_CONCRETE",
        "RELATION_UPSTREAM_CONCRETE",
        "UNKNOWN_SCHEMA",
        "DUPLICATE_OUTPUT_NAME",
        "AUTHORED_JOIN_DEFERRED",
        "DEFERRED_PHASE48_BEHAVIOR",
        "UNRESOLVED_RELATION_BLOCKED",
        "CYCLE_BLOCKED",
        "UPSTREAM_UNKNOWN",
        "UPSTREAM_DEFERRED",
        "UPSTREAM_BLOCKED",
    }.issubset(reason_names)


def test_relation_row_schema_state_is_frozen_slots_dataclass() -> None:
    assert is_dataclass(ProjectRelationRowSchemaState)
    assert hasattr(ProjectRelationRowSchemaState, "__slots__")

    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=_row_schema("id"),
        reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )

    assert not hasattr(state, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(state, "schema", None)


def test_relation_row_schema_state_invariants_are_enforced() -> None:
    concrete_schema = _row_schema("id")
    unknown_schema = ProjectRowSchema(is_unknown=True)

    assert (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.CONCRETE,
            schema=concrete_schema,
            reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        ).schema
        is concrete_schema
    )
    assert (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=unknown_schema,
            reason=ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        ).schema
        is unknown_schema
    )
    assert (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
        ).schema
        is None
    )
    assert (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        ).schema
        is None
    )

    invalid_cases = (
        (ProjectRelationRowSchemaStatus.CONCRETE, None),
        (ProjectRelationRowSchemaStatus.CONCRETE, unknown_schema),
        (ProjectRelationRowSchemaStatus.UNKNOWN, None),
        (ProjectRelationRowSchemaStatus.UNKNOWN, concrete_schema),
        (ProjectRelationRowSchemaStatus.DEFERRED, concrete_schema),
        (ProjectRelationRowSchemaStatus.BLOCKED, unknown_schema),
    )
    for status, schema in invalid_cases:
        with pytest.raises(ValueError):
            ProjectRelationRowSchemaState(
                status=status,
                schema=schema,
                reason=ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
            )

    with pytest.raises(ValueError):
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.CONCRETE,
            schema=concrete_schema,
            reason=cast(ProjectRelationRowSchemaReason, None),
        )


def test_project_semantic_model_defaults_to_empty_state_map() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert isinstance(model.relation_row_schemas, MappingProxyType)
    assert isinstance(model.relation_row_schema_states, MappingProxyType)
    assert model.relation_row_schemas == {}
    assert model.relation_row_schema_states == {}


def test_project_semantic_model_accepts_private_state_map_without_population(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _row_schema_project(tmp_path)
    )
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[table]
    state = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=schema,
        reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )

    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=parse_result.parsed_inputs,
        catalog=ProjectSemanticCatalog(),
        relation_row_schemas={table: schema},
        relation_row_schema_states={table: state},
    )

    assert tuple(model.relation_row_schemas) == (table,)
    assert tuple(model.relation_row_schema_states) == (table,)
    assert model.relation_row_schema_states[table] is state
    with pytest.raises(TypeError):
        cast(
            MutableMapping[TableDef | QueryDef, ProjectRelationRowSchemaState],
            model.relation_row_schema_states,
        )[table] = state


def test_semantic_build_populates_direct_source_concrete_table_state(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _row_schema_project(tmp_path)
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    table = _derived_definition(parse_result, "projected")
    assert table in semantic_result.model.relation_row_schemas
    state = semantic_result.model.relation_row_schema_states[table]
    assert tuple(semantic_result.model.relation_row_schema_states) == (table,)
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    assert state.schema is semantic_result.model.relation_row_schemas[table]


def test_project_json_v2_does_not_expose_schema_availability_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _row_schema_project(tmp_path)
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.model is not None
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
    assert semantic_result.model.relation_row_schema_states
    for private_fact in (
        "relation_row_schema_states",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
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
    ):
        assert private_fact not in serialized


def _row_field(name: str) -> ProjectRowField:
    return ProjectRowField(
        name=name,
        resolved_type=ProjectResolvedType(
            name="Int",
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=ProjectRowFieldNullability.NON_NULL,
    )


def _row_schema(*field_names: str) -> ProjectRowSchema:
    return ProjectRowSchema(
        fields={field_name: _row_field(field_name) for field_name in field_names}
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _row_schema_project(tmp_path: Path) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
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
