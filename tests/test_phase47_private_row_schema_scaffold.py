from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRoot,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowSchema,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE4_GATE2_PATHS = {
    "src/pietto/_project/model.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_source_row_schema_propagation.py",
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


def test_project_semantic_build_populates_source_row_schemas_only(
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
    assert field.nullability is ProjectRowFieldNullability.UNKNOWN
    assert field.provenance is not None
    assert field.provenance.kind is ProjectRowFieldProvenanceKind.SOURCE_FIELD
    assert (
        field.provenance.symbol
        is semantic_result.model.source_shape_resolutions[source]
    )
    assert semantic_result.model.relation_row_schemas == {}


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


def test_phase47_slice3_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE4_GATE2_PATHS)


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
