from __future__ import annotations

import json
from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsReason,
    ProjectLetScopeFactsStatus,
)
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
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
)
from pietto._project.row_lineage import ProjectRowLineageReason, ProjectRowLineageStatus
from pietto.ast_nodes import QueryDef, ShapeDef, SourceDef, TableDef


def test_project_row_schema_carriers_are_frozen_slots_dataclasses() -> None:
    for model_type in (
        ProjectRowFieldProvenance,
        ProjectRowField,
        ProjectRowSchema,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    provenance = ProjectRowFieldProvenance(
        kind=ProjectRowFieldProvenanceKind.SOURCE_FIELD,
    )
    field = _row_field("id", provenance=provenance)
    schema = ProjectRowSchema(fields={"id": field})

    assert not hasattr(provenance, "__dict__")
    assert not hasattr(field, "__dict__")
    assert not hasattr(schema, "__dict__")
    assert field.nullability is ProjectRowFieldNullability.NON_NULL
    assert field.provenance is provenance
    assert schema.fields["id"] is field
    with pytest.raises(FrozenInstanceError):
        setattr(field, "name", "other")
    with pytest.raises(FrozenInstanceError):
        setattr(schema, "is_unknown", True)


def test_project_row_schema_fields_are_copied_and_readonly() -> None:
    fields = {"id": _row_field("id")}
    schema = ProjectRowSchema(fields=fields)

    fields["email"] = _row_field("email")

    assert isinstance(schema.fields, MappingProxyType)
    assert tuple(schema.fields) == ("id",)
    with pytest.raises(TypeError):
        cast(MutableMapping[str, ProjectRowField], schema.fields)["other"] = _row_field(
            "other"
        )


def test_project_semantic_model_defaults_to_empty_row_schema_maps() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert isinstance(model.source_row_schemas, MappingProxyType)
    assert isinstance(model.relation_row_schemas, MappingProxyType)
    assert model.source_row_schemas == {}
    assert model.relation_row_schemas == {}


def test_project_row_schema_maps_accept_ast_definition_keys_as_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, _ = _project_semantic_result(_row_schema_project(tmp_path))
    source = _source_definition(parse_result, "rows")
    table = _derived_definition(parse_result, "projected")
    schema = ProjectRowSchema(fields={"id": _row_field("id")})

    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=parse_result.parsed_inputs,
        catalog=ProjectSemanticCatalog(),
        source_row_schemas={source: schema},
        relation_row_schemas={table: schema},
    )

    assert tuple(model.source_row_schemas) == (source,)
    assert tuple(model.relation_row_schemas) == (table,)
    with pytest.raises(TypeError):
        cast(MutableMapping[SourceDef, ProjectRowSchema], model.source_row_schemas)[
            source
        ] = schema
    with pytest.raises(TypeError):
        cast(
            MutableMapping[TableDef | QueryDef, ProjectRowSchema],
            model.relation_row_schemas,
        )[table] = schema


def test_project_semantic_build_populates_source_and_direct_relation_row_schemas(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _row_schema_project(tmp_path)
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert semantic_result.model.source_shape_resolutions
    assert semantic_result.model.relation_resolutions
    source = _source_definition(parse_result, "rows")
    schema = semantic_result.model.source_row_schemas[source]
    field = schema.fields["id"]
    assert tuple(schema.fields) == ("id",)
    assert field.name == "id"
    assert field.field_def is not None
    assert field.field_def.name == "id"
    # The bare declared `id: Int` is never None.
    assert field.nullability is ProjectRowFieldNullability.NON_NULL
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.SOURCE_FIELD
    assert (
        field.provenance.symbol
        is semantic_result.model.source_shape_resolutions[source]
    )
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    relation_field = relation_schema.fields["id"]
    assert tuple(relation_schema.fields) == ("id",)
    assert relation_field.name == "id"
    assert relation_field.resolved_type is field.resolved_type
    assert relation_field.nullability is field.nullability
    assert relation_field.field_def is field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )


def test_project_json_v2_does_not_expose_row_schema_private_facts(
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
    for private_fact in (
        "source_row_schemas",
        "relation_row_schemas",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldNullability",
        "ProjectRowFieldProvenance",
    ):
        assert private_fact not in serialized


def _row_field(
    name: str,
    *,
    provenance: ProjectRowFieldProvenance | None = None,
) -> ProjectRowField:
    return ProjectRowField(
        name=name,
        resolved_type=ProjectResolvedType(
            name="Int",
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=ProjectRowFieldNullability.NON_NULL,
        provenance=provenance,
    )


def _row_schema_project(tmp_path: Path) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
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


def _row_schema(*field_names: str) -> ProjectRowSchema:
    return ProjectRowSchema(
        fields={field_name: _row_field(field_name) for field_name in field_names}
    )


def test_source_row_schema_populates_from_resolved_shape_fields_in_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "type Email = Text\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "shape Row:\n"
        "    id: Int\n"
        "    email: Email | None\n"
        "    status: Status\n"
        'source rows: Row = postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    shape = _shape_definition(parse_result, "Row")
    schema = semantic_result.model.source_row_schemas[source]
    shape_fields = {field.name: field for field in shape.fields}

    assert isinstance(semantic_result.model.source_row_schemas, MappingProxyType)
    assert isinstance(schema.fields, MappingProxyType)
    assert tuple(semantic_result.model.source_row_schemas) == (source,)
    assert tuple(schema.fields) == ("id", "email", "status")
    assert tuple(schema.fields) == tuple(field.name for field in shape.fields)
    assert semantic_result.model.relation_row_schemas == {}
    with pytest.raises(TypeError):
        cast(MutableMapping[str, ProjectRowField], schema.fields)["extra"] = (
            schema.fields["id"]
        )

    assert schema.fields["id"].resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
    assert (
        schema.fields["email"].resolved_type.kind is ProjectResolvedTypeKind.TYPE_ALIAS
    )
    assert schema.fields["status"].resolved_type.kind is ProjectResolvedTypeKind.ENUM

    for row_field in schema.fields.values():
        field_def = shape_fields[row_field.name]
        assert row_field.name == field_def.name
        assert row_field.field_def is field_def
        assert (
            row_field.resolved_type
            is semantic_result.model.type_resolutions[field_def.type_expr]
        )
        assert row_field.provenance is not None
        assert row_field.provenance.kind is ProjectRowFieldProvenanceKind.SOURCE_FIELD
        assert (
            row_field.provenance.symbol
            is (semantic_result.model.source_shape_resolutions[source])
        )
        assert row_field.provenance.location is not None
        assert row_field.provenance.location.path == "models.pietto"


def test_source_row_schema_preserves_cross_file_shape_source_resolution(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a_shape.pietto",
        "shape Row:\n    id: Int\n    label: Text | None\n",
    )
    _write(
        root,
        "models/b_source.pietto",
        'source rows: Row = postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    schema = semantic_result.model.source_row_schemas[source]

    assert tuple(semantic_result.model.source_row_schemas) == (source,)
    assert tuple(schema.fields) == ("id", "label")
    assert semantic_result.model.source_shape_resolutions[source].path == (
        "models/a_shape.pietto"
    )
    assert semantic_result.model.relation_row_schemas == {}


def test_source_row_schema_maps_bare_fields_to_non_null_and_none_to_nullable(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "nullability.pietto",
        "shape Row:\n"
        "    required: Int\n"
        "    optional: Text | None\n"
        "    flag: Bool\n"
        'source rows: Row = postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    schema = semantic_result.model.source_row_schemas[source]

    assert schema.fields["required"].nullability is ProjectRowFieldNullability.NON_NULL
    assert schema.fields["optional"].nullability is ProjectRowFieldNullability.NULLABLE
    assert schema.fields["flag"].nullability is ProjectRowFieldNullability.NON_NULL


def test_source_row_schema_skips_unresolved_shape_field_types_without_new_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "broken.pietto",
        "shape Broken:\n"
        "    missing: MissingType\n"
        'source rows: Broken = postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    assert source in semantic_result.model.source_shape_resolutions
    assert source not in semantic_result.model.source_row_schemas
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2002", "Unknown type: MissingType")]


def test_source_row_schema_private_facts_do_not_leak_to_project_json_v2(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _source_row_schema_project(tmp_path)
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.source_row_schemas
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
    for private_fact in (
        "source_row_schemas",
        "relation_row_schemas",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldNullability",
        "ProjectRowFieldProvenance",
    ):
        assert private_fact not in serialized


def test_source_row_schema_missing_direct_projection_stays_private_without_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "projection_deferred.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        missing_field\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    assert source in semantic_result.model.source_row_schemas
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: missing_field")]


def _source_row_schema_project(tmp_path: Path) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        'shape Row:\n    id: Int\nsource rows: Row = postgres.table("rows")\n',
    )
    return root


def _shape_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> ShapeDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, ShapeDef) and definition.name == name:
                return definition
    raise AssertionError(f"Shape definition not found: {name}")


def test_table_from_direct_source_table_propagates_bare_and_qualified_fields(
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
            "table curated:\n"
            "    from staged\n"
            "    select:\n"
            "        staged.email\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    curated = _derived_definition(parse_result, "curated")
    source_schema = semantic_result.model.source_row_schemas[source]
    staged_schema = semantic_result.model.relation_row_schemas[staged]
    curated_schema = semantic_result.model.relation_row_schemas[curated]

    assert tuple(semantic_result.model.relation_row_schemas) == (staged, curated)
    assert tuple(staged_schema.fields) == ("id", "email")
    assert tuple(curated_schema.fields) == ("email", "id")
    _assert_projection_field(
        relation_field=curated_schema.fields["email"],
        source_field=source_schema.fields["email"],
        source_symbol=semantic_result.model.relation_resolutions[curated.from_clause],
        expected_name="email",
    )
    _assert_projection_field(
        relation_field=curated_schema.fields["id"],
        source_field=source_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[curated.from_clause],
        expected_name="id",
    )


def test_query_from_direct_source_table_propagates_renamed_fields(
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
            "        user_id = id\n"
            "        contact = staged.email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    source_schema = semantic_result.model.source_row_schemas[source]
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (staged, exported)
    assert tuple(exported_schema.fields) == ("user_id", "contact")
    _assert_projection_field(
        relation_field=exported_schema.fields["user_id"],
        source_field=source_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="user_id",
    )
    _assert_projection_field(
        relation_field=exported_schema.fields["contact"],
        source_field=source_schema.fields["email"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="contact",
    )


def test_concrete_states_cover_direct_source_and_relation_upstream_schemas(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query source_query:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    source_query = _derived_definition(parse_result, "source_query")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    states = semantic_result.model.relation_row_schema_states

    assert tuple(semantic_result.model.relation_row_schemas) == (
        source_query,
        staged,
        exported,
    )
    assert tuple(states) == (source_query, staged, exported)
    assert states[source_query].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[source_query].reason
        is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    )
    assert (
        states[source_query].schema
        is semantic_result.model.relation_row_schemas[source_query]
    )
    assert states[staged].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[staged].reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    )
    assert states[staged].schema is semantic_result.model.relation_row_schemas[staged]
    assert states[exported].status is ProjectRelationRowSchemaStatus.CONCRETE
    assert (
        states[exported].reason
        is ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    assert (
        states[exported].schema is semantic_result.model.relation_row_schemas[exported]
    )


def test_wrong_original_source_qualifier_over_table_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    assert exported_schema.is_unknown is True
    state = semantic_result.model.relation_row_schema_states[exported]
    assert state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert state.reason is ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
    assert state.schema is exported_schema
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_multi_part_lineage_selector_over_table_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        staged.users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    assert exported_schema.is_unknown is True
    assert exported_schema.fields == {}
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: staged.users.id")]


def test_query_to_query_and_table_from_query_propagate_concrete_schemas(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query query_seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from query_seed\n"
            "    select:\n"
            "        id\n"
            "table table_from_query:\n"
            "    from query_seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    query_seed = _derived_definition(parse_result, "query_seed")
    exported = _derived_definition(parse_result, "exported")
    table_from_query = _derived_definition(parse_result, "table_from_query")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        query_seed,
        exported,
        table_from_query,
    )
    assert tuple(semantic_result.model.relation_row_schemas[exported].fields) == ("id",)
    assert tuple(
        semantic_result.model.relation_row_schemas[table_from_query].fields
    ) == ("id",)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        query_seed,
        exported,
        table_from_query,
    )


def test_propagated_table_schema_is_used_as_multi_hop_seed(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table curated:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n"
            "query published:\n"
            "    from curated\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    curated = _derived_definition(parse_result, "curated")
    published = _derived_definition(parse_result, "published")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        staged,
        curated,
        published,
    )
    assert tuple(semantic_result.model.relation_row_schemas[published].fields) == (
        "id",
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        staged,
        curated,
        published,
    )


def test_table_upstream_computed_alias_is_concrete_without_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        total = id + 1\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (staged, exported)
    exported_schema = semantic_result.model.relation_row_schemas[exported]
    field = exported_schema.fields["total"]
    assert tuple(exported_schema.fields) == ("total",)
    assert field.resolved_type.name == "Int"
    assert field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION


def test_project_json_v2_does_not_expose_table_upstream_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
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
    assert semantic_result.model.relation_row_schema_states
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
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "source_row_schemas",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "direct_source_concrete",
        "table_upstream_concrete",
        "relation_upstream_concrete",
        "ProjectRowSchema",
        "ProjectRowField",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def _assert_projection_field(
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
    assert relation_field.provenance.location is not None
    assert relation_field.provenance.location.path == "models.pietto"


def test_query_from_direct_source_query_propagates_concrete_schema(
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
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    seed_schema = semantic_result.model.relation_row_schemas[seed]
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    assert tuple(seed_schema.fields) == ("id",)
    assert tuple(exported_schema.fields) == ("id",)
    _assert_projection_field(
        relation_field=exported_schema.fields["id"],
        source_field=seed_schema.fields["id"],
        source_symbol=semantic_result.model.relation_resolutions[exported.from_clause],
        expected_name="id",
    )
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (exported, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_query_from_propagated_query_supports_multi_hop(
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

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schemas[final].fields) == ("id",)
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (mid, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
            (final, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_table_from_query_propagates_concrete_schema(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "table materialized:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    materialized = _derived_definition(parse_result, "materialized")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, materialized)
    assert tuple(semantic_result.model.relation_row_schemas[materialized].fields) == (
        "id",
    )
    _assert_concrete_states(
        semantic_result,
        (
            (seed, ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE),
            (materialized, ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE),
        ),
    )


def test_mixed_table_query_multi_hop_chain_propagates_in_dependency_order(
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
            "        user_id = id\n"
            "        contact = staged.email\n"
            "table materialized:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.user_id\n"
            "query final:\n"
            "    from materialized\n"
            "    select:\n"
            "        user_id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    materialized = _derived_definition(parse_result, "materialized")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        staged,
        exported,
        materialized,
        final,
    )
    assert tuple(semantic_result.model.relation_row_schemas[exported].fields) == (
        "user_id",
        "contact",
    )
    assert tuple(semantic_result.model.relation_row_schemas[final].fields) == (
        "user_id",
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        staged,
        exported,
        materialized,
        final,
    )


def test_qualified_and_renamed_projection_through_query_upstream(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query exported:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        email\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.id\n"
            "        user_id = id\n"
            "        contact = exported.email\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    published_schema = semantic_result.model.relation_row_schemas[published]

    assert tuple(published_schema.fields) == ("id", "user_id", "contact")


def test_original_source_qualifier_over_query_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query exported:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        users.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_lineage_path_selector_over_query_upstream_uses_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table staged:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query exported:\n"
            "    from staged\n"
            "    select:\n"
            "        id\n"
            "query published:\n"
            "    from exported\n"
            "    select:\n"
            "        exported.staged.id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: exported.staged.id")]


def test_dependency_first_order_does_not_depend_on_definition_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query final:\n"
            "    from mid\n"
            "    select:\n"
            "        id\n"
            "query mid:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (seed, mid, final)


def test_duplicate_output_names_through_query_upstream_remain_unknown_without_diagnostics(
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
            "        id\n"
            "        id = seed.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    exported_schema = semantic_result.model.relation_row_schemas[exported]

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    assert exported_schema.is_unknown is True
    assert exported_schema.fields == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (seed, exported)
    state = semantic_result.model.relation_row_schema_states[exported]
    assert state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert state.reason is ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
    assert state.schema is exported_schema


def test_non_concrete_upstreams_get_private_states(
    tmp_path: Path,
) -> None:
    unknown_root = _project(
        tmp_path / "unknown",
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        missing\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        id\n",
    )
    unknown_parse, unknown_semantic = _project_semantic_result(unknown_root)
    unknown_seed = _derived_definition(unknown_parse, "seed")
    unknown_exported = _derived_definition(unknown_parse, "exported")
    assert not unknown_semantic.ok
    assert unknown_semantic.model is not None
    assert unknown_semantic.model.relation_row_schemas[unknown_seed].is_unknown is True
    assert unknown_semantic.model.relation_row_schemas[unknown_exported].is_unknown
    assert (
        unknown_semantic.model.relation_row_schema_states[unknown_seed].status
        is ProjectRelationRowSchemaStatus.UNKNOWN
    )
    assert (
        unknown_semantic.model.relation_row_schema_states[unknown_exported].reason
        is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    )
    assert [(item.code, item.message) for item in unknown_semantic.diagnostics] == [
        ("PIE-S2102", "Unknown field: missing")
    ]

    deferred_root = _project(
        tmp_path / "deferred",
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        total = score + 1\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        total\n",
    )
    deferred_parse, deferred_semantic = _project_semantic_result(deferred_root)
    deferred_seed = _derived_definition(deferred_parse, "seed")
    deferred_exported = _derived_definition(deferred_parse, "exported")
    assert deferred_semantic.ok
    assert deferred_semantic.model is not None
    seed_schema = deferred_semantic.model.relation_row_schemas[deferred_seed]
    exported_schema = deferred_semantic.model.relation_row_schemas[deferred_exported]
    assert tuple(deferred_semantic.model.relation_row_schemas) == (
        deferred_seed,
        deferred_exported,
    )
    assert tuple(seed_schema.fields) == ("total",)
    assert tuple(exported_schema.fields) == ("total",)
    assert seed_schema.fields["total"].field_def is None
    assert exported_schema.fields["total"].field_def is None
    assert exported_schema.fields["total"].resolved_type.name == "Int"
    assert (
        exported_schema.fields["total"].nullability
        is ProjectRowFieldNullability.UNKNOWN
    )
    assert (
        deferred_semantic.model.relation_row_schema_states[deferred_seed].status
        is ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert (
        deferred_semantic.model.relation_row_schema_states[deferred_exported].reason
        is ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )

    cycle_root = _project(
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
    _, cycle_semantic = _project_semantic_result(cycle_root)
    assert not cycle_semantic.ok
    assert cycle_semantic.model is not None
    assert cycle_semantic.model.relation_row_schemas == {}
    assert {
        state.reason
        for state in cycle_semantic.model.relation_row_schema_states.values()
    } == {ProjectRelationRowSchemaReason.CYCLE_BLOCKED}
    assert [(item.code, item.message) for item in cycle_semantic.diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_computed_alias_let_and_aggregate_are_concrete_while_pure_grouping_stays_deferred(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query computed:\n"
            "    from seed\n"
            "    select:\n"
            "        total = id + 1\n"
            "query with_let:\n"
            "    from seed\n"
            "    let total = id + 1\n"
            "    select:\n"
            "        id\n"
            "query aggregate:\n"
            "    from seed\n"
            "    select:\n"
            "        total = count()\n"
            "query grouped:\n"
            "    from seed\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    computed = _derived_definition(parse_result, "computed")
    with_let = _derived_definition(parse_result, "with_let")
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")

    assert tuple(semantic_result.model.relation_row_schemas) == (
        seed,
        computed,
        with_let,
        aggregate,
    )
    computed_schema = semantic_result.model.relation_row_schemas[computed]
    assert tuple(computed_schema.fields) == ("total",)
    assert computed_schema.fields["total"].field_def is None
    assert computed_schema.fields["total"].resolved_type.name == "Int"
    assert tuple(semantic_result.model.relation_row_schemas[with_let].fields) == ("id",)
    assert tuple(semantic_result.model.relation_row_schemas[aggregate].fields) == (
        "total",
    )
    aggregate_state = semantic_result.model.relation_row_schema_states[aggregate]
    assert aggregate_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert aggregate_state.reason is (
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    assert tuple(semantic_result.model.relation_aggregate_result_facts[aggregate]) == (
        "total",
    )
    assert grouped not in semantic_result.model.relation_row_schemas
    grouped_state = semantic_result.model.relation_row_schema_states[grouped]
    assert grouped_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert grouped_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )


def test_project_json_v2_does_not_expose_query_upstream_private_facts(
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
    assert semantic_result.model.relation_row_schemas
    assert semantic_result.model.relation_row_schema_states
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
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "source_row_schemas",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "direct_source_concrete",
        "relation_upstream_concrete",
        "provenance",
        "ProjectRowSchema",
        "ProjectRowField",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def _assert_concrete_states(
    semantic_result: ProjectSemanticResult,
    expected: tuple[tuple[TableDef | QueryDef, ProjectRelationRowSchemaReason], ...],
) -> None:
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.relation_row_schema_states) == tuple(
        definition for definition, _reason in expected
    )
    for definition, reason in expected:
        state = semantic_result.model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is reason
        assert state.schema is semantic_result.model.relation_row_schemas[definition]


def test_direct_missing_field_gets_unknown_state_with_existing_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n    from users\n    select:\n        missing\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    assert schema.is_unknown is True
    assert schema.fields == {}
    _assert_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        schema_is_relation_schema=True,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]


def test_duplicate_output_gets_unknown_state_without_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        id = users.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    assert schema.is_unknown is True
    assert schema.fields == {}
    _assert_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        schema_is_relation_schema=True,
    )


def test_downstream_from_unknown_gets_unknown_state_without_extra_diagnostics(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
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
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]


def test_computed_alias_and_aggregate_are_concrete_while_pure_grouping_stays_deferred(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query computed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query with_let:\n"
            "    from users\n"
            "    let total = score + 1\n"
            "    select:\n"
            "        id\n"
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
    computed = _derived_definition(parse_result, "computed")
    with_let = _derived_definition(parse_result, "with_let")
    aggregate = _derived_definition(parse_result, "aggregate")
    grouped = _derived_definition(parse_result, "grouped")

    computed_schema = semantic_result.model.relation_row_schemas[computed]
    assert tuple(computed_schema.fields) == ("total",)
    assert computed_schema.fields["total"].resolved_type.name == "Int"
    assert computed_schema.fields["total"].field_def is None
    aggregate_schema = semantic_result.model.relation_row_schemas[aggregate]
    assert tuple(aggregate_schema.fields) == ("total",)
    assert tuple(semantic_result.model.relation_aggregate_result_facts[aggregate]) == (
        "total",
    )
    assert grouped not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        computed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        aggregate,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.DEFERRED,
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )

    with_let_schema = semantic_result.model.relation_row_schemas[with_let]
    assert tuple(with_let_schema.fields) == ("id",)
    assert "total" not in with_let_schema.fields
    _assert_state(
        semantic_result,
        with_let,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )


def test_unresolved_relation_gets_private_blocked_state_with_existing_pie_s2301(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query broken:\n    from missing_relation\n    select:\n        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    broken = _derived_definition(parse_result, "broken")
    assert broken not in semantic_result.model.relation_row_schemas
    _assert_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_cycle_members_get_private_blocked_states_with_existing_pie_s2302(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (first, second)
    for definition in (first, second):
        _assert_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_downstream_from_blocked_gets_blocked_state_without_extra_diagnostics(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    broken = _derived_definition(parse_result, "broken")
    downstream = _derived_definition(parse_result, "downstream")
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
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_downstream_from_computed_alias_gets_concrete_schema(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query downstream:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    downstream = _derived_definition(parse_result, "downstream")
    seed_schema = semantic_result.model.relation_row_schemas[seed]
    downstream_schema = semantic_result.model.relation_row_schemas[downstream]
    assert tuple(seed_schema.fields) == ("total",)
    assert tuple(downstream_schema.fields) == ("total",)
    assert downstream_schema.fields["total"].field_def is None
    assert (
        downstream_schema.fields["total"].nullability
        is ProjectRowFieldNullability.UNKNOWN
    )
    _assert_state(
        semantic_result,
        seed,
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


def test_existing_concrete_query_to_query_propagation_remains_concrete(
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
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
    assert tuple(semantic_result.model.relation_row_schemas) == (seed, exported)
    _assert_state(
        semantic_result,
        seed,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        schema_is_relation_schema=True,
    )
    _assert_state(
        semantic_result,
        exported,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE,
        schema_is_relation_schema=True,
    )


def test_project_json_v2_does_not_expose_non_concrete_state_facts(
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
            "        id\n"
            "query computed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schema_states
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
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "ProjectRowSchema",
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


def _diagnostic_pairs(semantic_result: ProjectSemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ]


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
            "    id: Int\n"
            "    email: Text | None\n"
            "    score: Int\n"
            'source users: User = postgres.table("users")\n'
        )
    _write(root, "models.pietto", f"{source_text}{relation_body}")
    return root


def test_table_to_query_row_schema_propagates_from_direct_table_seed(
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


def test_computed_alias_is_concrete_without_diagnostics(
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
    relation_schema = semantic_result.model.relation_row_schemas[projected]
    field = relation_schema.fields["total"]
    assert tuple(relation_schema.fields) == ("total",)
    assert field.resolved_type.name == "Int"
    assert field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert field.field_def is None
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert "PIE-S2102" not in _diagnostic_codes(semantic_result)


def test_let_schema_remains_deferred_without_direct_schema_expansion(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "table projected:\n"
            "    from users\n"
            "    let total = score + 1\n"
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


def test_private_provenance_vocabulary_keeps_expression_readiness_private() -> None:
    assert (
        ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION.value == "derived_expression"
    )
    assert ProjectRowFieldProvenanceKind.EXPRESSION.value == "expression"
    assert ProjectRowFieldProvenanceKind.AGGREGATE.value == "aggregate"
    assert ProjectRowFieldProvenanceKind.DIRECT_PROJECTION.value == (
        "direct_projection"
    )


def test_aggregate_projection_schema_is_concrete_with_persisted_fact(
    tmp_path: Path,
) -> None:
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
    schema = semantic_result.model.relation_row_schemas[projected]
    assert tuple(schema.fields) == ("total",)
    assert schema.fields["total"].resolved_type.name == "Int"
    assert schema.fields["total"].result_role is (ProjectRowResultRole.AGGREGATE_RESULT)
    assert tuple(semantic_result.model.relation_aggregate_result_facts[projected]) == (
        "total",
    )


def test_grouped_direct_field_schema_remains_absent(tmp_path: Path) -> None:
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


def _diagnostic_codes(semantic_result: ProjectSemanticResult) -> set[str]:
    return {diagnostic.code for diagnostic in semantic_result.diagnostics}


def test_multiple_invalid_direct_fields_keep_select_item_order(
    tmp_path: Path,
) -> None:
    _, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        first_missing\n"
            "        users.second_missing\n"
            "        db.users.third_missing\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: first_missing"),
        ("PIE-S2102", "Unknown field: users.second_missing"),
        ("PIE-S2102", "Unknown field: db.users.third_missing"),
    ]


def test_downstream_invalid_fields_follow_dependency_and_project_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query bad_first:\n"
            "    from seed\n"
            "    select:\n"
            "        missing_first\n"
            "query bad_second:\n"
            "    from seed\n"
            "    select:\n"
            "        seed.missing_second\n"
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    bad_first = _derived_definition(parse_result, "bad_first")
    bad_second = _derived_definition(parse_result, "bad_second")
    assert tuple(semantic_result.model.relation_row_schemas) == (
        seed,
        bad_first,
        bad_second,
    )
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        bad_first,
        bad_second,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing_first"),
        ("PIE-S2102", "Unknown field: seed.missing_second"),
    ]


def test_out_of_order_definitions_keep_dependency_first_private_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query final:\n"
            "    from mid\n"
            "    select:\n"
            "        id\n"
            "query mid:\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")

    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        mid,
        final,
    )


def test_independent_relations_tie_break_by_canonical_definition_order(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query second:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "query first:\n"
            "    from users\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    second = _derived_definition(parse_result, "second")
    first = _derived_definition(parse_result, "first")

    assert tuple(semantic_result.model.relation_row_schemas) == (second, first)
    assert tuple(semantic_result.model.relation_row_schema_states) == (second, first)


def test_unknown_propagation_does_not_emit_downstream_pie_s2102(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    exported = _derived_definition(parse_result, "exported")
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
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]


def test_deferred_propagation_remains_diagnostic_free(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + 1\n"
            "query downstream:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    seed = _derived_definition(parse_result, "seed")
    downstream = _derived_definition(parse_result, "downstream")
    assert seed in semantic_result.model.relation_row_schemas
    assert downstream in semantic_result.model.relation_row_schemas
    assert tuple(semantic_result.model.relation_row_schemas[seed].fields) == ("total",)
    assert tuple(semantic_result.model.relation_row_schemas[downstream].fields) == (
        "total",
    )
    _assert_state(
        semantic_result,
        seed,
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


def test_blocked_propagation_uses_unresolved_relation_diagnostic_only(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    broken = _derived_definition(parse_result, "broken")
    downstream = _derived_definition(parse_result, "downstream")
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
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_cycle_members_are_blocked_without_pie_s2102(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        also_missing\n",
            include_source=False,
        )
    )

    assert not semantic_result.ok
    assert semantic_result.model is not None
    first = _derived_definition(parse_result, "first")
    second = _derived_definition(parse_result, "second")
    assert semantic_result.model.relation_row_schemas == {}
    assert tuple(semantic_result.model.relation_row_schema_states) == (first, second)
    _assert_state(
        semantic_result,
        first,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
    )
    _assert_state(
        semantic_result,
        second,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
    )
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]


def test_duplicate_output_remains_unknown_and_diagnostic_free(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        id = users.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    schema = semantic_result.model.relation_row_schemas[projected]
    assert schema.is_unknown is True
    assert schema.fields == {}
    _assert_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        schema_is_relation_schema=True,
    )


def test_multi_file_source_selection_keeps_dependency_first_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a_source.pietto",
        "shape User:\n"
        "    id: Int\n"
        "    score: Int\n"
        'source users: User = postgres.table("users")\n',
    )
    _write(
        root,
        "models/b_final.pietto",
        "query final:\n    from mid\n    select:\n        id\n",
    )
    _write(
        root,
        "models/c_seed.pietto",
        "query seed:\n    from users\n    select:\n        id\n",
    )
    _write(
        root,
        "models/d_mid.pietto",
        "query mid:\n    from seed\n    select:\n        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert tuple(parsed_input.path for parsed_input in parse_result.parsed_inputs) == (
        "models/a_source.pietto",
        "models/b_final.pietto",
        "models/c_seed.pietto",
        "models/d_mid.pietto",
    )
    seed = _derived_definition(parse_result, "seed")
    mid = _derived_definition(parse_result, "mid")
    final = _derived_definition(parse_result, "final")
    assert tuple(semantic_result.model.relation_row_schemas) == (seed, mid, final)
    assert tuple(semantic_result.model.relation_row_schema_states) == (
        seed,
        mid,
        final,
    )


def test_project_json_v2_keeps_private_ordering_facts_private(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_without_email(
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
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schema_states
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
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2102", "Unknown field: missing")
    ]
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "ProjectRelationRowSchemaState",
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "ProjectRowSchema",
        "ProjectRowField",
        "provenance",
        "relation_dependency_graph",
        "ProjectRelationDependencyGraph",
        "cycle_blocked",
        "unknown_schema",
        "upstream_unknown",
        "deferred_phase48_behavior",
        "unresolved_relation_blocked",
        "dependency-first",
        "private ordering",
    ):
        assert private_fact not in serialized


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    assert semantic_result.model is not None
    return parse_result, semantic_result


def _project_without_email(
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
            "    id: Int\n"
            "    score: Int\n"
            'source users: User = postgres.table("users")\n'
        )
    _write(root, "models.pietto", f"{source_text}{relation_body}")
    return root


PRIVATE_JSON_FACTS = (
    "relation_row_schema_states",
    "relation_let_scope_facts",
    "relation_row_dependency_graphs",
    "relation_row_lineages",
    "ProjectRelationRowSchemaState",
    "ProjectRelationLetScopeFacts",
    "ProjectRelationRowDependencyGraph",
    "ProjectRelationRowLineage",
    "UNKNOWN_SCHEMA",
    "DEFERRED_PHASE48_BEHAVIOR",
    "UNRESOLVED_RELATION_BLOCKED",
    "CYCLE_BLOCKED",
    "DUPLICATE_OUTPUT_NAME",
    "LET_DIAGNOSTICS_SUPPRESSED",
    "unknown_schema",
    "deferred_phase48_behavior",
    "unresolved_relation_blocked",
    "cycle_blocked",
    "duplicate_output_name",
    "let_diagnostics_suppressed",
    "dependency",
    "lineage",
    "provenance",
    "origin",
)


def test_missing_field_unknown_schema_keeps_single_public_diagnostic(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2102", "Unknown field: missing")
    ]
    broken = _derived_definition(parse_result, "broken")
    _assert_row_schema_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
    )
    _assert_dependency_graph_state(
        semantic_result,
        broken,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA,
    )
    _assert_lineage_state(
        semantic_result,
        broken,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.UNKNOWN_SCHEMA,
    )


def test_unresolved_relation_blocks_private_carriers_without_extra_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query broken:\n"
            "    from missing_relation\n"
            "    let total = id + 1\n"
            "    select:\n"
            "        id\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]
    broken = _derived_definition(parse_result, "broken")
    _assert_row_schema_state(
        semantic_result,
        broken,
        ProjectRelationRowSchemaStatus.BLOCKED,
        ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_let_state(
        semantic_result,
        broken,
        ProjectLetScopeFactsStatus.BLOCKED,
        ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
    )
    _assert_dependency_graph_state(
        semantic_result,
        broken,
        ProjectRowDependencyGraphStatus.BLOCKED,
        ProjectRowDependencyGraphReason.UNRESOLVED_RELATION_BLOCKED,
    )
    _assert_lineage_state(
        semantic_result,
        broken,
        ProjectRowLineageStatus.BLOCKED,
        ProjectRowLineageReason.UNRESOLVED_RELATION_BLOCKED,
    )


def test_relation_cycle_blocks_private_carriers_without_missing_field_noise(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query first:\n"
            "    from second\n"
            "    let total = id + 1\n"
            "    select:\n"
            "        missing\n"
            "query second:\n"
            "    from first\n"
            "    let other = id + 1\n"
            "    select:\n"
            "        also_missing\n",
            include_source=False,
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    for relation_name in ("first", "second"):
        definition = _derived_definition(parse_result, relation_name)
        _assert_row_schema_state(
            semantic_result,
            definition,
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CYCLE_BLOCKED,
        )
        _assert_let_state(
            semantic_result,
            definition,
            ProjectLetScopeFactsStatus.BLOCKED,
            ProjectLetScopeFactsReason.UPSTREAM_BLOCKED,
        )
        _assert_dependency_graph_state(
            semantic_result,
            definition,
            ProjectRowDependencyGraphStatus.BLOCKED,
            ProjectRowDependencyGraphReason.CYCLE_BLOCKED,
        )
        _assert_lineage_state(
            semantic_result,
            definition,
            ProjectRowLineageStatus.BLOCKED,
            ProjectRowLineageReason.CYCLE_BLOCKED,
        )


def test_duplicate_output_names_stay_private_unknown_and_diagnostic_free(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        id = users.id\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    projected = _derived_definition(parse_result, "projected")
    _assert_row_schema_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
    )
    _assert_dependency_graph_state(
        semantic_result,
        projected,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.DUPLICATE_OUTPUT_NAME,
    )
    _assert_lineage_state(
        semantic_result,
        projected,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.DUPLICATE_OUTPUT_NAME,
    )


def test_grouped_aggregate_schema_graph_and_lineage_are_concrete_without_public_diagnostics(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    grouped = _derived_definition(parse_result, "grouped")
    _assert_row_schema_state(
        semantic_result,
        grouped,
        ProjectRelationRowSchemaStatus.CONCRETE,
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )
    _assert_dependency_graph_state(
        semantic_result,
        grouped,
        ProjectRowDependencyGraphStatus.CONCRETE,
        ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE,
    )
    _assert_lineage_state(
        semantic_result,
        grouped,
        ProjectRowLineageStatus.CONCRETE,
        ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE,
    )
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.relation_row_schemas[grouped].fields) == (
        "status",
        "total",
    )
    assert tuple(semantic_result.model.relation_aggregate_result_facts[grouped]) == (
        "total",
    )


def test_invalid_selected_let_helper_diagnostics_stay_private_and_ordered(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project_with_status(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let total = subtotal + bonus\n"
            "    let subtotal = score\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert not semantic_result.ok
    assert _diagnostic_pairs(semantic_result) == [("PIE-S2102", "Unknown field: total")]
    projected = _derived_definition(parse_result, "projected")
    _assert_let_state(
        semantic_result,
        projected,
        ProjectLetScopeFactsStatus.UNKNOWN,
        ProjectLetScopeFactsReason.LET_DIAGNOSTICS_SUPPRESSED,
    )
    _assert_row_schema_state(
        semantic_result,
        projected,
        ProjectRelationRowSchemaStatus.UNKNOWN,
        ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
    )
    _assert_dependency_graph_state(
        semantic_result,
        projected,
        ProjectRowDependencyGraphStatus.UNKNOWN,
        ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA,
    )
    _assert_lineage_state(
        semantic_result,
        projected,
        ProjectRowLineageStatus.UNKNOWN,
        ProjectRowLineageReason.UNKNOWN_SCHEMA,
    )


def test_project_json_v2_keeps_private_carrier_facts_private(
    tmp_path: Path,
) -> None:
    valid_parse, valid_semantic = _project_semantic_result(
        _project_with_status(
            tmp_path / "valid",
            "query projected:\n    from users\n    select:\n        id\n",
        )
    )
    invalid_parse, invalid_semantic = _project_semantic_result(
        _project_with_status(
            tmp_path / "invalid",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )

    for parse_result, semantic_result in (
        (valid_parse, valid_semantic),
        (invalid_parse, invalid_semantic),
    ):
        document = project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
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
        _assert_private_json_facts_absent(document)


def _assert_row_schema_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    assert semantic_result.model is not None
    state = semantic_result.model.relation_row_schema_states[definition]
    assert state.status is status
    assert state.reason is reason
    if status is ProjectRelationRowSchemaStatus.CONCRETE:
        assert state.schema is not None
    elif status is ProjectRelationRowSchemaStatus.UNKNOWN:
        assert state.schema is not None
        assert state.schema.is_unknown is True
    else:
        assert state.schema is None


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


def _assert_dependency_graph_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRowDependencyGraphStatus,
    reason: ProjectRowDependencyGraphReason,
) -> None:
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_row_dependency_graphs[definition]
    assert graph.status is status
    assert graph.reason is reason
    if status is not ProjectRowDependencyGraphStatus.CONCRETE:
        assert graph.nodes == ()
        assert graph.edges == ()


def _assert_lineage_state(
    semantic_result: ProjectSemanticResult,
    definition: TableDef | QueryDef,
    status: ProjectRowLineageStatus,
    reason: ProjectRowLineageReason,
) -> None:
    assert semantic_result.model is not None
    lineage = semantic_result.model.relation_row_lineages[definition]
    assert lineage.status is status
    assert lineage.reason is reason
    if status is not ProjectRowLineageStatus.CONCRETE:
        assert lineage.facts == ()


def _assert_private_json_facts_absent(document: dict[str, object]) -> None:
    serialized = json.dumps(document)
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized
    assert _json_paths_for_key(document, "reason") == ()
    assert _json_paths_for_key(document, "status") == ("inputs[].status",)


def _json_paths_for_key(value: object, key: str, path: str = "") -> tuple[str, ...]:
    if isinstance(value, dict):
        paths: list[str] = []
        for child_key, child_value in value.items():
            child_path = child_key if not path else f"{path}.{child_key}"
            if child_key == key:
                paths.append(child_path)
            paths.extend(_json_paths_for_key(child_value, key, child_path))
        return tuple(paths)
    if isinstance(value, list):
        normalized_path = f"{path}[]" if path else "[]"
        paths = []
        for item in value:
            paths.extend(_json_paths_for_key(item, key, normalized_path))
        return tuple(dict.fromkeys(paths))
    return ()


def _project_with_status(
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
        "    id: Int\n"
        "    email: Text\n"
        "    score: Int\n"
        "    bonus: Int\n"
        "    status: Text\n"
    )
    if include_source:
        source_prefix += 'source users: User = postgres.table("users")\n'
    (root / "models.pietto").write_text(
        source_prefix + relation_source,
        encoding="utf-8",
    )
    return root
