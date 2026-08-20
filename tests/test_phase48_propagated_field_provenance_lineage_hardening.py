from __future__ import annotations

import json
from pathlib import Path

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowField,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase48-propagated-field-provenance-lineage-hardening-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def test_slice6_contract_document_exists_and_locks_private_scope() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    docs = " ".join(
        (
            PLAN_PATH.read_text(encoding="utf-8")
            + "\n"
            + SPEC_PATH.read_text(encoding="utf-8")
        ).split()
    )

    for required in (
        "Phase 48 Slice 6",
        "Propagated field provenance / lineage hardening",
        "docs/spec/tests-only",
        "Provenance means immediate semantic projection metadata",
        "Lineage means a future explain/export chain",
        "no private lineage scaffold",
        "Project JSON v2 top-level shape remains unchanged",
        "no selector syntax expansion",
        "no computed alias schema",
        "No other file is approved in Slice 6 Gate 2",
    ):
        assert required in docs, required


def test_direct_source_and_direct_relation_provenance_baseline(
    tmp_path: Path,
) -> None:
    source = "query seed:\n    from users\n    select:\n        id\n"
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    seed = _derived_definition(parse_result, "seed")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    seed_field = semantic_result.model.relation_row_schemas[seed].fields["id"]

    assert source_field.provenance is not None
    assert source_field.provenance.kind is ProjectRowFieldProvenanceKind.SOURCE_FIELD
    assert (
        source_field.provenance.symbol
        is semantic_result.model.source_shape_resolutions[users]
    )
    assert source_field.provenance.location is not None
    assert source_field.provenance.location.path == "models.pietto"

    _assert_direct_projection(
        relation_field=seed_field,
        origin_field=source_field,
        expected_name="id",
        expected_symbol=semantic_result.model.relation_resolutions[seed.from_clause],
        expected_line=_line_containing(text, "        id\n"),
    )


def test_table_to_query_provenance_is_immediate_upstream(
    tmp_path: Path,
) -> None:
    source = (
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        exported_id = staged.id\n"
    )
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "exported_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="exported_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        exported_id = staged.id\n"),
    )
    assert exported_field.provenance is not None
    assert (
        exported_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[staged.from_clause]
    )


def test_query_to_query_provenance_is_immediate_upstream(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        exported_id = seed.id\n"
    )
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "exported_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="exported_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        exported_id = seed.id\n"),
    )


def test_multi_hop_final_field_keeps_origin_facts_but_not_lineage_path(
    tmp_path: Path,
) -> None:
    source = (
        "table staged:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        user_id = staged.id\n"
        "table materialized:\n"
        "    from exported\n"
        "    select:\n"
        "        published_user_id = exported.user_id\n"
        "query final:\n"
        "    from materialized\n"
        "    select:\n"
        "        final_user_id = materialized.published_user_id\n"
    )
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    final = _derived_definition(parse_result, "final")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    final_field = semantic_result.model.relation_row_schemas[final].fields[
        "final_user_id"
    ]

    _assert_direct_projection(
        relation_field=final_field,
        origin_field=source_field,
        expected_name="final_user_id",
        expected_symbol=semantic_result.model.relation_resolutions[final.from_clause],
        expected_line=_line_containing(
            text,
            "        final_user_id = materialized.published_user_id\n",
        ),
    )
    assert final_field.provenance is not None
    assert (
        final_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[staged.from_clause]
    )
    assert (
        final_field.provenance.symbol
        is not semantic_result.model.relation_resolutions[exported.from_clause]
    )
    assert (
        final_field.provenance.symbol
        is semantic_result.model.relation_resolutions[final.from_clause]
    )


def test_renamed_bare_projection_preserves_origin_facts(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        user_id = id\n"
    )
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "user_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="user_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        user_id = id\n"),
    )


def test_renamed_qualified_projection_preserves_origin_facts(
    tmp_path: Path,
) -> None:
    source = (
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from seed\n"
        "    select:\n"
        "        user_id = seed.id\n"
    )
    parse_result, semantic_result, text = _project_semantic_result(tmp_path, source)

    assert semantic_result.ok
    assert semantic_result.model is not None
    users = _source_definition(parse_result, "users")
    exported = _derived_definition(parse_result, "exported")
    source_field = semantic_result.model.source_row_schemas[users].fields["id"]
    exported_field = semantic_result.model.relation_row_schemas[exported].fields[
        "user_id"
    ]

    _assert_direct_projection(
        relation_field=exported_field,
        origin_field=source_field,
        expected_name="user_id",
        expected_symbol=semantic_result.model.relation_resolutions[
            exported.from_clause
        ],
        expected_line=_line_containing(text, "        user_id = seed.id\n"),
    )


def test_original_source_qualifier_remains_invalid_after_propagation(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _project_semantic_result(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: users.id")]


def test_multi_part_lineage_selector_remains_invalid_after_propagation(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _project_semantic_result(
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    published = _derived_definition(parse_result, "published")
    assert semantic_result.model.relation_row_schemas[published].is_unknown is True
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [("PIE-S2102", "Unknown field: exported.staged.id")]


def test_project_json_v2_does_not_expose_slice6_private_facts(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result, _text = _project_semantic_result(
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
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_schemas
    assert semantic_result.model.relation_row_schema_states
    for private_fact in (
        "relation_row_schemas",
        "relation_row_schema_states",
        "provenance",
        "lineage",
        "ProjectRowSchema",
        "ProjectRowField",
        "ProjectRowFieldProvenance",
        "DIRECT_PROJECTION",
        "direct_projection",
    ):
        assert private_fact not in serialized


def test_package_version_is_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject


def _assert_direct_projection(
    *,
    relation_field: ProjectRowField,
    origin_field: ProjectRowField,
    expected_name: str,
    expected_symbol: object,
    expected_line: int,
) -> None:
    assert relation_field.name == expected_name
    assert relation_field.resolved_type is origin_field.resolved_type
    assert relation_field.nullability is origin_field.nullability
    assert relation_field.field_def is origin_field.field_def
    assert relation_field.provenance is not None
    assert (
        relation_field.provenance.kind
        is ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
    )
    assert relation_field.provenance.symbol is expected_symbol
    assert relation_field.provenance.location is not None
    assert relation_field.provenance.location.path == "models.pietto"
    assert relation_field.provenance.location.line == expected_line


def _project_semantic_result(
    tmp_path: Path,
    relation_body: str,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult, str]:
    root, source = _project(tmp_path, relation_body)
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result), source


def _project(tmp_path: Path, relation_body: str) -> tuple[Path, str]:
    root = _project_root(tmp_path, include=("*.pietto",))
    source = (
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int\n"
        'source users: User is postgres.table("users")\n'
        f"{relation_body}"
    )
    _write(root, "models.pietto", source)
    return root, source


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


def _line_containing(source: str, marker: str) -> int:
    lines = source.splitlines(keepends=True)
    matches = [
        line_number for line_number, line in enumerate(lines, start=1) if line == marker
    ]
    assert len(matches) == 1, marker
    return matches[0]
