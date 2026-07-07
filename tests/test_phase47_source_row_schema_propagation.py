from __future__ import annotations

from collections.abc import MutableMapping
import json
from pathlib import Path
import subprocess
from types import MappingProxyType
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, ShapeDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE5_GATE2_PATHS = {
    "src/pietto/_project/model.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
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


def test_source_row_schema_populates_from_resolved_shape_fields_in_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "type Email = Text not null\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "shape Row:\n"
        "    id: Int not null\n"
        "    email: Email nullable\n"
        "    status: Status\n"
        'source rows: Row is postgres.table("rows")\n',
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
        "shape Row:\n    id: Int not null\n    label: Text nullable\n",
    )
    _write(
        root,
        "models/b_source.pietto",
        'source rows: Row is postgres.table("rows")\n',
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


def test_source_row_schema_maps_field_nullability_without_deciding_implicit_default(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "nullability.pietto",
        "shape Row:\n"
        "    required: Int not null\n"
        "    optional: Text nullable\n"
        "    implicit: Bool\n"
        'source rows: Row is postgres.table("rows")\n',
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    schema = semantic_result.model.source_row_schemas[source]

    assert schema.fields["required"].nullability is ProjectRowFieldNullability.NON_NULL
    assert schema.fields["optional"].nullability is ProjectRowFieldNullability.NULLABLE
    assert schema.fields["implicit"].nullability is ProjectRowFieldNullability.UNKNOWN


def test_source_row_schema_skips_unresolved_shape_field_types_without_new_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "broken.pietto",
        "shape Broken:\n"
        "    missing: MissingType\n"
        'source rows: Broken is postgres.table("rows")\n',
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
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        missing_field\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    source = _source_definition(parse_result, "rows")
    assert source in semantic_result.model.source_row_schemas
    table = _derived_definition(parse_result, "projected")
    relation_schema = semantic_result.model.relation_row_schemas[table]
    assert relation_schema.is_unknown is True
    assert relation_schema.fields == {}
    assert "PIE-S2102" not in {
        diagnostic.code for diagnostic in semantic_result.diagnostics
    }


def test_phase47_slice4_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE5_GATE2_PATHS)


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _source_row_schema_project(tmp_path: Path) -> Path:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "models.pietto",
        "shape Row:\n"
        "    id: Int not null\n"
        'source rows: Row is postgres.table("rows")\n',
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


def _shape_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> ShapeDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, ShapeDef) and definition.name == name:
                return definition
    raise AssertionError(f"Shape definition not found: {name}")


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
