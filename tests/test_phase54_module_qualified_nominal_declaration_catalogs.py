from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from importlib.metadata import version
import json
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto._project.check as project_check
import pietto._project.module_catalog as module_catalog
import pietto.cli as cli
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
)
from pietto.ast_nodes import (
    ConstraintDef,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice5-module-qualified-nominal-declaration-identity-"
    "and-per-module-catalogs-v1.md"
)
MODEL_REL = "src/pietto/_project/model.py"
CATALOG_REL = "src/pietto/_project/module_catalog.py"
TEST_REL = "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py"

EXPECTED_TEST_NAMES = (
    "test_nominal_declaration_identity_is_exact_frozen_slotted_four_component_value",
    "test_nominal_declaration_identity_preserves_exact_module_path_case_suffix_and_unicode",
    "test_each_nominal_identity_component_independently_controls_equality_and_hash",
    "test_occurrence_span_ast_object_positions_and_trust_payload_do_not_change_nominal_identity",
    "test_nominal_identity_and_occurrence_constructors_reject_wrong_exact_types_and_mismatches",
    "test_all_eight_definition_classes_map_to_exact_namespace_kind_and_declared_name",
    "test_relationships_imports_and_exports_are_excluded_from_local_declaration_occurrences",
    "test_occurrences_retain_exact_module_and_declaration_positions_and_definition_values",
    "test_module_catalog_is_frozen_slotted_tuple_backed_and_retains_exact_owner",
    "test_module_catalog_rejects_wrong_mode_unparsed_owner_and_incomplete_or_misordered_occurrences",
    "test_project_catalog_set_builds_one_catalog_per_module_in_exact_selected_input_order",
    "test_project_catalog_set_rejects_duplicate_module_paths_and_noncontiguous_or_missing_modules",
    "test_empty_catalog_set_and_lookup_results_are_exact_immutable_empty_tuples",
    "test_project_module_path_lookup_returns_exact_zero_or_one_element_tuple",
    "test_exact_nominal_identity_lookup_returns_all_source_ordered_occurrences",
    "test_exact_namespace_declared_name_lookup_returns_zero_one_or_multiple_occurrences",
    "test_catalog_construction_never_reopens_sources_or_consults_import_targets_or_registries",
    "test_same_declaration_spelling_in_different_modules_has_distinct_nominal_identities",
    "test_same_spelling_in_different_namespaces_has_distinct_identity_and_lookup_buckets",
    "test_same_namespace_and_name_across_different_kinds_preserves_one_ambiguous_bucket",
    "test_repeated_exact_nominal_identity_preserves_every_occurrence_in_source_order",
    "test_declaration_order_changes_only_occurrence_order_and_never_creates_precedence_or_winner",
    "test_schema_v2_catalog_collisions_emit_one_pie_s2001_and_no_pie_s2701_through_pie_s2707",
    "test_schema_v2_success_retains_catalogs_privately_without_changing_model_diagnostics_ok_or_defaults",
    "test_schema_v2_parse_or_read_failure_builds_no_complete_or_partial_catalog_set",
    "test_current_zero_selected_input_project_remains_project_glob_failure_without_catalogs",
    "test_schema_v2_text_and_json_cli_remain_fail_closed_with_exact_envelope_and_no_catalog_fields",
    "test_schema_v1_legacy_flat_catalog_duplicate_diagnostics_and_cli_json_remain_exact",
    "test_import_export_blocks_do_not_add_remove_rename_reorder_or_link_local_declarations",
    "test_private_public_dependency_version_and_retained_later_surfaces_remain_exact",
)

EIGHT_KIND_SOURCE = (
    "type Email = Text not null\n"
    "enum Status:\n"
    "    active\n"
    "    inactive\n"
    "constraint valid_email(value: Text not null) -> Bool not null:\n"
    '    matches(value, "@")\n'
    "derive normalized_email(value: Text not null) -> Text not null:\n"
    "    lower(trim(value))\n"
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("public.users")\n'
    "table FirstRelation:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
    "query SecondRelation:\n"
    "    from FirstRelation\n"
    "    select:\n"
    "        id\n"
)


def _parsed(source: str, *, path: str = "main.pietto") -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    return result.ast


def _module(
    source: str,
    *,
    path: str = "main.pietto",
    position: int = 0,
    mode: ProjectCompilationMode = ProjectCompilationMode.EXPLICIT_MODULES,
    parsed: bool = True,
) -> ProjectLogicalModule:
    project_input = ProjectInput(path=path, status="selected")
    parsed_input = (
        ProjectParsedInput(path=path, script=_parsed(source, path=path))
        if parsed
        else None
    )
    return ProjectLogicalModule(
        compilation_mode=mode,
        path=path,
        position=position,
        project_input=project_input,
        parsed_input=parsed_input,
    )


def _catalog(
    source: str,
    *,
    path: str = "main.pietto",
) -> module_catalog.ProjectModuleCatalog:
    catalog_set = module_catalog._build_project_module_catalog_set(
        (_module(source, path=path),)
    )
    assert len(catalog_set.catalogs) == 1
    return catalog_set.catalogs[0]


def _identity(
    *,
    module_path: str = "main.pietto",
    namespace: ProjectSymbolNamespace = ProjectSymbolNamespace.TYPE,
    declaration_kind: ProjectSymbolKind = ProjectSymbolKind.TYPE_ALIAS,
    declared_name: str = "Shared",
) -> module_catalog.ProjectNominalDeclarationIdentity:
    return module_catalog.ProjectNominalDeclarationIdentity(
        module_path=module_path,
        namespace=namespace,
        declaration_kind=declaration_kind,
        declared_name=declared_name,
    )


def _configured_project(
    root: Path,
    *,
    schema_version: int,
    include: tuple[str, ...] = ("*.pietto",),
) -> Path:
    root.mkdir(parents=True)
    patterns = ", ".join(json.dumps(pattern) for pattern in include)
    (root / "pietto.toml").write_text(
        f"schema_version = {schema_version}\n\n[sources]\ninclude = [{patterns}]\n",
        encoding="utf-8",
    )
    return root


def _write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = project_check.check_project_parse_only(root)
    return parse_result, build_empty_project_semantic_result(parse_result)


def test_nominal_declaration_identity_is_exact_frozen_slotted_four_component_value() -> (
    None
):
    identity = _identity()

    assert is_dataclass(identity)
    assert tuple(field.name for field in fields(identity)) == (
        "module_path",
        "namespace",
        "declaration_kind",
        "declared_name",
    )
    assert not hasattr(identity, "__dict__")
    assert identity == _identity()
    assert hash(identity) == hash(_identity())
    with pytest.raises(FrozenInstanceError):
        identity.declared_name = "Changed"  # type: ignore[misc]


def test_nominal_declaration_identity_preserves_exact_module_path_case_suffix_and_unicode() -> (
    None
):
    values = (
        "models/Customer.pietto",
        "models/custómer.pietto",
        "models/custómer.pietto",
    )

    identities = tuple(_identity(module_path=value) for value in values)
    assert tuple(identity.module_path for identity in identities) == values
    assert len(set(identities)) == 3
    for invalid in ("", "/main.pietto", "../main.pietto", "main.sql"):
        with pytest.raises(ValueError):
            _identity(module_path=invalid)


def test_each_nominal_identity_component_independently_controls_equality_and_hash() -> (
    None
):
    base = _identity()
    variants = (
        _identity(module_path="other.pietto"),
        _identity(namespace=ProjectSymbolNamespace.RELATION),
        _identity(declaration_kind=ProjectSymbolKind.ENUM),
        _identity(declared_name="Other"),
    )

    assert all(variant != base for variant in variants)
    assert len({base, *variants}) == 5


def test_occurrence_span_ast_object_positions_and_trust_payload_do_not_change_nominal_identity() -> (
    None
):
    first = _parsed("type Shared = Int\n", path="first.pietto").definitions[0]
    second = _parsed("type Shared = Int\n", path="second.pietto").definitions[0]
    identity = _identity()
    first_occurrence = module_catalog.ProjectDeclarationOccurrence(
        identity=identity,
        module_position=0,
        declaration_position=0,
        definition=first,
    )
    second_occurrence = module_catalog.ProjectDeclarationOccurrence(
        identity=_identity(),
        module_position=9,
        declaration_position=7,
        definition=second,
    )

    assert first is not second
    assert first.span != second.span
    assert first_occurrence != second_occurrence
    assert first_occurrence.identity == second_occurrence.identity
    assert hash(first_occurrence.identity) == hash(second_occurrence.identity)


def test_nominal_identity_and_occurrence_constructors_reject_wrong_exact_types_and_mismatches() -> (
    None
):
    definition = _parsed("type Shared = Int\n").definitions[0]

    with pytest.raises(TypeError):
        _identity(namespace="type")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        _identity(declaration_kind="type")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _identity(declared_name="")
    with pytest.raises(TypeError):
        module_catalog.ProjectDeclarationOccurrence(
            identity="Shared",  # type: ignore[arg-type]
            module_position=0,
            declaration_position=0,
            definition=definition,
        )
    with pytest.raises(ValueError):
        module_catalog.ProjectDeclarationOccurrence(
            identity=_identity(declared_name="Other"),
            module_position=0,
            declaration_position=0,
            definition=definition,
        )
    with pytest.raises(ValueError):
        module_catalog.ProjectDeclarationOccurrence(
            identity=_identity(),
            module_position=True,
            declaration_position=0,
            definition=definition,
        )


def test_all_eight_definition_classes_map_to_exact_namespace_kind_and_declared_name() -> (
    None
):
    catalog = _catalog(EIGHT_KIND_SOURCE)

    assert tuple(type(item.definition) for item in catalog.occurrences) == (
        TypeDef,
        EnumDef,
        ConstraintDef,
        DeriveDef,
        ShapeDef,
        SourceDef,
        TableDef,
        QueryDef,
    )
    assert tuple(
        (
            item.identity.namespace,
            item.identity.declaration_kind,
            item.identity.declared_name,
        )
        for item in catalog.occurrences
    ) == (
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.TYPE_ALIAS, "Email"),
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.ENUM, "Status"),
        (
            ProjectSymbolNamespace.CALLABLE,
            ProjectSymbolKind.CONSTRAINT,
            "valid_email",
        ),
        (
            ProjectSymbolNamespace.CALLABLE,
            ProjectSymbolKind.DERIVE,
            "normalized_email",
        ),
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.SHAPE, "User"),
        (ProjectSymbolNamespace.RELATION, ProjectSymbolKind.SOURCE, "users"),
        (
            ProjectSymbolNamespace.RELATION,
            ProjectSymbolKind.TABLE,
            "FirstRelation",
        ),
        (
            ProjectSymbolNamespace.RELATION,
            ProjectSymbolKind.QUERY,
            "SecondRelation",
        ),
    )


def test_relationships_imports_and_exports_are_excluded_from_local_declaration_occurrences() -> (
    None
):
    source = (
        "shape User:\n"
        "    id: Int\n"
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
        'import "missing.pietto":\n'
        "    shape External as Imported\n"
        "export:\n"
        "    shape User\n"
    )
    module = _module(source)
    catalog = module_catalog._build_project_module_catalog_set((module,)).catalogs[0]

    assert module.parsed_input is not None
    assert len(module.parsed_input.script.relationships) == 1
    assert len(module.parsed_input.script.module_statements) == 2
    assert tuple(item.identity.declared_name for item in catalog.occurrences) == (
        "User",
    )


def test_occurrences_retain_exact_module_and_declaration_positions_and_definition_values() -> (
    None
):
    module = _module(
        "type First = Int\ntype Second = Text\n",
        path="types/shared.pietto",
        position=3,
    )
    catalog = module_catalog.ProjectModuleCatalog(
        module=module,
        occurrences=tuple(
            module_catalog.ProjectDeclarationOccurrence(
                identity=module_catalog.ProjectNominalDeclarationIdentity(
                    module_path=module.path,
                    namespace=ProjectSymbolNamespace.TYPE,
                    declaration_kind=ProjectSymbolKind.TYPE_ALIAS,
                    declared_name=definition.name,
                ),
                module_position=module.position,
                declaration_position=position,
                definition=definition,
            )
            for position, definition in enumerate(
                module.parsed_input.script.definitions  # type: ignore[union-attr]
            )
        ),
    )

    assert tuple(item.module_position for item in catalog.occurrences) == (3, 3)
    assert tuple(item.declaration_position for item in catalog.occurrences) == (0, 1)
    assert module.parsed_input is not None
    assert tuple(item.definition for item in catalog.occurrences) == (
        module.parsed_input.script.definitions
    )


def test_module_catalog_is_frozen_slotted_tuple_backed_and_retains_exact_owner() -> (
    None
):
    module = _module("type Shared = Int\n")
    catalog = module_catalog._build_project_module_catalog_set((module,)).catalogs[0]

    assert is_dataclass(catalog)
    assert tuple(field.name for field in fields(catalog)) == ("module", "occurrences")
    assert not hasattr(catalog, "__dict__")
    assert catalog.module is module
    assert catalog.module_path == "main.pietto"
    assert type(catalog.occurrences) is tuple
    with pytest.raises(FrozenInstanceError):
        catalog.occurrences = ()  # type: ignore[misc]


def test_module_catalog_rejects_wrong_mode_unparsed_owner_and_incomplete_or_misordered_occurrences() -> (
    None
):
    source = "type Shared = Int\n"
    with pytest.raises(ValueError):
        module_catalog.ProjectModuleCatalog(
            module=_module(source, mode=ProjectCompilationMode.LEGACY_FLAT),
        )
    with pytest.raises(ValueError):
        module_catalog.ProjectModuleCatalog(module=_module(source, parsed=False))

    module = _module(source)
    valid = module_catalog._build_project_module_catalog_set((module,)).catalogs[0]
    with pytest.raises(ValueError):
        module_catalog.ProjectModuleCatalog(module=module, occurrences=())
    with pytest.raises(ValueError):
        module_catalog.ProjectModuleCatalog(
            module=module,
            occurrences=(replace(valid.occurrences[0], declaration_position=1),),
        )


def test_project_catalog_set_builds_one_catalog_per_module_in_exact_selected_input_order() -> (
    None
):
    modules = (
        _module("type A = Int\n", path="a.pietto", position=0),
        _module("type B = Int\n", path="b.pietto", position=1),
        _module("type C = Int\n", path="nested/c.pietto", position=2),
    )
    catalogs = module_catalog._build_project_module_catalog_set(modules)

    assert tuple(catalog.module for catalog in catalogs.catalogs) == modules
    assert tuple(catalog.module_path for catalog in catalogs.catalogs) == (
        "a.pietto",
        "b.pietto",
        "nested/c.pietto",
    )


def test_project_catalog_set_rejects_duplicate_module_paths_and_noncontiguous_or_missing_modules() -> (
    None
):
    source = "type Shared = Int\n"
    with pytest.raises(ValueError):
        module_catalog._build_project_module_catalog_set((_module(source, position=1),))
    with pytest.raises(ValueError):
        module_catalog._build_project_module_catalog_set(
            (
                _module(source, path="same.pietto", position=0),
                _module(source, path="same.pietto", position=1),
            )
        )
    with pytest.raises(ValueError):
        module_catalog._build_project_module_catalog_set(
            (_module(source, parsed=False),)
        )

    first = _catalog(source, path="same.pietto")
    second_module = _module(source, path="same.pietto", position=1)
    second_occurrence = replace(
        first.occurrences[0],
        module_position=1,
        definition=second_module.parsed_input.script.definitions[0],  # type: ignore[union-attr]
    )
    second = module_catalog.ProjectModuleCatalog(
        module=second_module,
        occurrences=(second_occurrence,),
    )
    with pytest.raises(ValueError):
        module_catalog.ProjectModuleCatalogSet(catalogs=(first, second))


def test_empty_catalog_set_and_lookup_results_are_exact_immutable_empty_tuples() -> (
    None
):
    catalogs = module_catalog.ProjectModuleCatalogSet()

    assert catalogs.catalogs == ()
    assert type(catalogs.catalogs) is tuple
    assert catalogs.find_module_path("missing.pietto") == ()
    assert catalogs.find_identity(_identity()) == ()
    with pytest.raises(FrozenInstanceError):
        catalogs.catalogs = ()  # type: ignore[misc]
    with pytest.raises(TypeError):
        catalogs.find_identity("Shared")  # type: ignore[arg-type]


def test_project_module_path_lookup_returns_exact_zero_or_one_element_tuple() -> None:
    catalogs = module_catalog._build_project_module_catalog_set(
        (
            _module("type A = Int\n", path="a.pietto", position=0),
            _module("type B = Int\n", path="b.pietto", position=1),
        )
    )

    assert catalogs.find_module_path("a.pietto") == (catalogs.catalogs[0],)
    assert catalogs.find_module_path("missing.pietto") == ()
    assert catalogs.find_module_path("../a.pietto") == ()
    assert catalogs.find_module_path(1) == ()  # type: ignore[arg-type]


def test_exact_nominal_identity_lookup_returns_all_source_ordered_occurrences() -> None:
    catalogs = module_catalog._build_project_module_catalog_set(
        (_module("type Shared = Int\ntype Shared = Text\n"),)
    )
    identity = _identity()
    matches = catalogs.find_identity(identity)

    assert len(matches) == 2
    assert tuple(item.declaration_position for item in matches) == (0, 1)
    assert all(item.identity == identity for item in matches)


def test_exact_namespace_declared_name_lookup_returns_zero_one_or_multiple_occurrences() -> (
    None
):
    catalog = _catalog(
        "type Shared = Int\n"
        "enum Shared:\n"
        "    active\n"
        "shape Shared:\n"
        "    id: Int\n"
        "type Other = Int\n"
    )

    assert catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "Missing") == ()
    assert len(catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "Other")) == 1
    matches = catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "Shared")
    assert len(matches) == 3
    assert tuple(item.identity.declaration_kind for item in matches) == (
        ProjectSymbolKind.TYPE_ALIAS,
        ProjectSymbolKind.ENUM,
        ProjectSymbolKind.SHAPE,
    )


def test_catalog_construction_never_reopens_sources_or_consults_import_targets_or_registries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module(
        'type Local = Int\nimport "does/not/exist.pietto":\n    type Remote as Alias\n'
    )

    def forbidden(*_args: object, **_kwargs: object) -> Any:
        raise AssertionError("catalog construction attempted filesystem access")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    monkeypatch.setattr(Path, "read_bytes", forbidden)
    catalogs = module_catalog._build_project_module_catalog_set((module,))

    assert tuple(
        item.identity.declared_name for item in catalogs.catalogs[0].occurrences
    ) == ("Local",)


def test_same_declaration_spelling_in_different_modules_has_distinct_nominal_identities() -> (
    None
):
    catalogs = module_catalog._build_project_module_catalog_set(
        (
            _module("type Shared = Int\n", path="a.pietto", position=0),
            _module("type Shared = Int\n", path="b.pietto", position=1),
        )
    )
    identities = tuple(catalog.occurrences[0].identity for catalog in catalogs.catalogs)

    assert identities[0] != identities[1]
    assert tuple(identity.module_path for identity in identities) == (
        "a.pietto",
        "b.pietto",
    )


def test_same_spelling_in_different_namespaces_has_distinct_identity_and_lookup_buckets() -> (
    None
):
    catalog = _catalog(
        "type shared = Int\nconstraint shared(value: Int) -> Bool:\n    value > 0\n"
    )
    identities = tuple(item.identity for item in catalog.occurrences)

    assert identities[0].declared_name == identities[1].declared_name == "shared"
    assert identities[0] != identities[1]
    assert len(catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "shared")) == 1
    assert (
        len(
            catalog.find_namespace_name(
                ProjectSymbolNamespace.CALLABLE,
                "shared",
            )
        )
        == 1
    )


def test_same_namespace_and_name_across_different_kinds_preserves_one_ambiguous_bucket() -> (
    None
):
    catalog = _catalog(
        "type Shared = Int\nenum Shared:\n    active\nshape Shared:\n    id: Int\n"
    )
    matches = catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "Shared")

    assert len({item.identity for item in matches}) == 3
    assert len(matches) == 3
    assert not hasattr(catalog, "first")
    assert not hasattr(catalog, "get_unique")


def test_repeated_exact_nominal_identity_preserves_every_occurrence_in_source_order() -> (
    None
):
    catalog = _catalog("type Shared = Int\ntype Shared = Float\ntype Shared = Text\n")
    matches = catalog.find_namespace_name(ProjectSymbolNamespace.TYPE, "Shared")

    assert len(matches) == 3
    assert len({item.identity for item in matches}) == 1
    assert tuple(item.declaration_position for item in matches) == (0, 1, 2)


def test_declaration_order_changes_only_occurrence_order_and_never_creates_precedence_or_winner() -> (
    None
):
    first = _catalog("type Shared = Int\ntype Shared = Text\n")
    second = _catalog("type Shared = Text\ntype Shared = Int\n")

    assert tuple(item.identity for item in first.occurrences) == tuple(
        item.identity for item in second.occurrences
    )
    assert tuple(
        cast(TypeDef, item.definition).base.name for item in first.occurrences
    ) == (
        "Int",
        "Text",
    )
    assert tuple(
        cast(TypeDef, item.definition).base.name for item in second.occurrences
    ) == (
        "Text",
        "Int",
    )
    for forbidden in ("first", "last", "winner", "resolve", "get_unique"):
        assert not hasattr(first, forbidden)


def test_schema_v2_catalog_collisions_emit_one_pie_s2001_and_no_pie_s2701_through_pie_s2707(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "a.pietto", "type Shared = Int\ntype Shared = Text\n")
    _write(root, "b.pietto", "type Shared = Float\n")
    parse_result, semantic = _project_semantic_result(root)

    assert parse_result.ok
    assert semantic.module_catalogs is not None
    assert tuple(
        (diagnostic.code, diagnostic.message) for diagnostic in semantic.diagnostics
    ) == (("PIE-S2001", "Duplicate symbol name in type namespace: Shared"),)
    diagnostic = semantic.diagnostics[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.location.path == "a.pietto"
    assert diagnostic.location.line == 2
    assert semantic.model is None
    assert not semantic.ok
    assert len(semantic.module_catalogs.catalogs) == 2
    assert (
        len(
            semantic.module_catalogs.catalogs[0].find_namespace_name(
                ProjectSymbolNamespace.TYPE,
                "Shared",
            )
        )
        == 2
    )
    assert {diagnostic.code for diagnostic in semantic.diagnostics}.isdisjoint(
        {f"PIE-S270{number}" for number in range(1, 8)}
    )


def test_schema_v2_success_retains_catalogs_privately_without_changing_model_diagnostics_ok_or_defaults(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")
    parse_result, semantic = _project_semantic_result(root)

    assert parse_result.ok
    assert semantic.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert semantic.module_catalogs is not None
    assert semantic.module_catalogs.catalogs[0].module is semantic.modules[0]
    assert semantic.model is None
    assert semantic.diagnostics == ()
    assert not semantic.ok
    assert (
        ProjectSemanticResult(root=None, config_path=None, model=None).module_catalogs
        is None
    )
    assert "module_catalogs" not in {
        field.name for field in fields(ProjectSemanticModel)
    }
    assert "module_catalogs" not in {
        field.name for field in fields(ProjectParseCheckResult)
    }


def test_schema_v2_parse_or_read_failure_builds_no_complete_or_partial_catalog_set(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "good.pietto", "type Good = Int\n")
    _write(root, "bad.pietto", "shape Broken:\n")
    parse_result, semantic = _project_semantic_result(root)

    assert not parse_result.ok
    assert semantic.module_catalogs is None

    missing = _module("", path="missing.pietto", parsed=False)
    manual = ProjectParseCheckResult(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(missing.project_input,),
        errors=(
            ProjectDiscoveryError(
                kind=ProjectDiscoveryErrorKind.SOURCE_READ,
                message="unreadable",
                path="missing.pietto",
            ),
        ),
        diagnostics=(),
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        modules=(missing,),
    )
    assert build_empty_project_semantic_result(manual).module_catalogs is None


def test_current_zero_selected_input_project_remains_project_glob_failure_without_catalogs(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "empty", schema_version=2)
    parse_result, semantic = _project_semantic_result(root)

    assert not parse_result.ok
    assert tuple(error.kind for error in parse_result.errors) == (
        ProjectDiscoveryErrorKind.PROJECT_GLOB,
    )
    assert parse_result.modules == ()
    assert semantic.module_catalogs is None
    assert module_catalog.ProjectModuleCatalogSet().catalogs == ()


def test_schema_v2_text_and_json_cli_remain_fail_closed_with_exact_envelope_and_no_catalog_fields(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "row.pietto", "shape Row:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 1
    text_capture = capsys.readouterr()
    assert text_capture.out == ""
    assert text_capture.err == ""

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    json_capture = capsys.readouterr()
    document = json.loads(json_capture.out)
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
    assert document["ok"] is True
    assert json_capture.err == ""
    for forbidden in (
        "module_catalogs",
        "ProjectModuleCatalog",
        "declaration_kind",
        "declared_name",
        "collision",
    ):
        assert forbidden not in json_capture.out


def test_schema_v1_legacy_flat_catalog_duplicate_diagnostics_and_cli_json_remain_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=1)
    _write(root, "a.pietto", "type Shared = Int\n")
    _write(root, "b.pietto", "type Shared = Text\n")
    parse_result, semantic = _project_semantic_result(root)

    assert parse_result.ok
    assert semantic.model is not None
    assert semantic.module_catalogs is None
    assert tuple(diagnostic.code for diagnostic in semantic.diagnostics) == (
        "PIE-S2001",
    )
    assert semantic.model.catalog.type_symbols["Shared"].path == "a.pietto"
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic.diagnostics,
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
    assert document["ok"] is False

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == document
    assert captured.err == ""


def test_import_export_blocks_do_not_add_remove_rename_reorder_or_link_local_declarations() -> (
    None
):
    definitions = (
        'shape Row:\n    id: Int\nsource rows: Row is postgres.table("public.rows")\n'
    )
    module_statements = (
        'import "missing.pietto":\n'
        "    shape External as Imported\n"
        "export:\n"
        "    shape Row\n"
    )
    plain = _catalog(definitions)
    enriched_module = _module(definitions + module_statements)
    enriched = module_catalog._build_project_module_catalog_set(
        (enriched_module,)
    ).catalogs[0]

    assert enriched_module.parsed_input is not None
    assert len(enriched_module.parsed_input.script.module_statements) == 2
    assert tuple(item.identity for item in enriched.occurrences) == tuple(
        item.identity for item in plain.occurrences
    )
    assert tuple(type(item.definition) for item in enriched.occurrences) == (
        ShapeDef,
        SourceDef,
    )
    assert enriched.find_namespace_name(ProjectSymbolNamespace.TYPE, "Imported") == ()
    assert not hasattr(enriched, "imports")
    assert not hasattr(enriched, "exports")


def test_private_public_dependency_version_and_retained_later_surfaces_remain_exact() -> (
    None
):
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert module_catalog.__all__ == ()
    assert tuple(
        field.name for field in fields(module_catalog.ProjectNominalDeclarationIdentity)
    ) == (
        "module_path",
        "namespace",
        "declaration_kind",
        "declared_name",
    )
    assert tuple(
        field.name for field in fields(module_catalog.ProjectDeclarationOccurrence)
    ) == (
        "identity",
        "module_position",
        "declaration_position",
        "definition",
    )
    assert tuple(
        field.name for field in fields(module_catalog.ProjectModuleCatalog)
    ) == (
        "module",
        "occurrences",
    )
    assert tuple(
        field.name for field in fields(module_catalog.ProjectModuleCatalogSet)
    ) == ("catalogs",)
    for name in (
        "ProjectNominalDeclarationIdentity",
        "ProjectDeclarationOccurrence",
        "ProjectModuleCatalog",
        "ProjectModuleCatalogSet",
    ):
        assert not hasattr(pietto, name)

    test_tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    assert (
        tuple(
            node.name
            for node in test_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
        == EXPECTED_TEST_NAMES
    )
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    model_source = (REPO_ROOT / MODEL_REL).read_text(encoding="utf-8")
    catalog_source = (REPO_ROOT / CATALOG_REL).read_text(encoding="utf-8")
    public_surfaces = "\n".join(
        (REPO_ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "src/pietto/__init__.py",
            "src/pietto/_project/json_v2.py",
            "src/pietto/cli.py",
            "src/pietto/ir/__init__.py",
            "src/pietto/sql/__init__.py",
        )
    )
    assert "module_catalogs: ProjectModuleCatalogSet | None = None" in model_source
    assert "from pietto._project.module_catalog import" in model_source
    assert "__all__: tuple[str, ...] = ()" in catalog_source
    assert "script.definitions" in catalog_source
    assert "module_statements" not in catalog_source
    assert "relationships" not in catalog_source
    assert "ProjectModuleCatalog" not in public_surfaces
    assert "PIE-S2701" not in catalog_source
    assert "winner" not in catalog_source
    assert "Slice 6" in spec and "export eligibility" in spec
    assert "Slice 7" in spec and "binding environments" in spec
    assert "Slice 8" in spec and "PIE-S2701" in spec
    assert not hasattr(pietto, "__version__")
    assert version("pietto") == "0.1.0"
