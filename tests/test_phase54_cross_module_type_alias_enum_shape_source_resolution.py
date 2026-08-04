from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import json
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_resolution as module_resolution
import pietto.cli as cli
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectResolvedTypeKind,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice9-cross-module-type-alias-enum-shape-and-source-"
    "resolution-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_resolution.py"
TEST_REL = "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py"

EXPECTED_TEST_NAMES = (
    "test_carrier_enums_fields_privacy_and_manifest_are_exact",
    "test_local_imported_and_reexported_nominal_identities_remain_distinct",
    "test_environment_lookups_are_complete_tuple_backed_and_immutable",
    "test_dependency_order_uses_selected_position_for_ready_ties",
    "test_dependency_order_places_targets_before_importers",
    "test_dependency_order_is_deterministic_for_a_diamond",
    "test_cycle_members_are_excluded_and_retain_one_block_issue_each",
    "test_independent_acyclic_local_errors_remain_visible_with_a_cycle",
    "test_builtin_precedence_and_direct_type_kinds_are_preserved",
    "test_local_alias_chain_expands_to_builtin",
    "test_cross_module_alias_chain_expands_by_target_identity",
    "test_explicit_reexport_alias_chain_keeps_original_target_identity",
    "test_cyclic_direct_facade_reexports_are_no_winner_for_all_slice9_kinds",
    "test_direct_facade_cycle_precedes_nominal_owner_cycle_and_owner_fallback_remains",
    "test_imported_enums_are_nominal_and_not_flattened",
    "test_imported_shapes_are_nominal_and_field_types_resolve",
    "test_shape_field_reference_order_and_duplicates_are_preserved",
    "test_duplicate_local_type_name_is_one_pie_s2001_no_winner",
    "test_duplicate_local_source_name_is_one_pie_s2001_no_winner",
    "test_local_alias_cycle_emits_one_exact_pie_s2003",
    "test_multiple_alias_cycles_follow_dependency_and_source_order",
    "test_unknown_alias_target_emits_one_pie_s2002_without_cascade",
    "test_unknown_shape_field_type_emits_exact_pie_s2002",
    "test_unresolved_import_root_suppresses_derived_type_error",
    "test_private_import_root_suppresses_derived_type_error",
    "test_import_collision_is_no_winner_and_suppresses_consumers",
    "test_all_import_kind_local_candidate_collisions_are_no_winner",
    "test_export_and_inconsistent_facade_roots_suppress_consumers",
    "test_local_source_shape_resolves_direct_shape",
    "test_imported_source_and_shape_keep_both_local_and_target_identity",
    "test_source_unknown_and_wrong_kind_emit_exact_pie_s2303",
    "test_schema_v1_deferred_surfaces_and_public_privacy_are_exact",
    "test_text_json_status_docs_and_reader_fixed_point_are_exact",
)


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in sources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _semantic_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    project_root = _configured_project(root, sources, schema_version=schema_version)
    parse_result = project_check.check_project_parse_only(project_root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _required_set(
    semantic: ProjectSemanticResult,
) -> module_resolution.ProjectTypeSourceResolutionSet:
    result = semantic.module_type_source_resolutions
    assert result is not None
    return result


def _environment(
    semantic: ProjectSemanticResult,
    module_path: str,
) -> module_resolution.ProjectModuleTypeSourceResolutionEnvironment:
    matches = _required_set(semantic).find_module_path(module_path)
    assert len(matches) == 1
    return matches[0]


def _type_resolution(
    environment: module_resolution.ProjectModuleTypeSourceResolutionEnvironment,
    *,
    owner_name: str,
    type_name: str,
) -> module_resolution.ProjectResolvedModuleTypeReference:
    matches = tuple(
        item
        for item in environment.type_resolutions
        if item.reference.owner.identity.declared_name == owner_name
        and item.reference.type_expr.name == type_name
    )
    assert len(matches) == 1
    return matches[0]


def _diagnostic_pairs(
    semantic: ProjectSemanticResult,
) -> tuple[tuple[str, str], ...]:
    return tuple((item.code, item.message) for item in semantic.diagnostics)


def test_carrier_enums_fields_privacy_and_manifest_are_exact() -> None:
    assert module_resolution.__all__ == ()
    assert tuple(module_resolution.ProjectModuleTypeReferenceRole) == (
        module_resolution.ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE,
        module_resolution.ProjectModuleTypeReferenceRole.SHAPE_FIELD_TYPE,
    )
    assert tuple(module_resolution.ProjectTypeSourceResolutionIssueStatus) == (
        module_resolution.ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_TYPE_NAME,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_SOURCE_NAME,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.UNKNOWN_TYPE_REFERENCE,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.TYPE_ALIAS_CYCLE,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.UNKNOWN_SOURCE_SHAPE_REFERENCE,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.INCOMPATIBLE_SOURCE_SHAPE_KIND,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
    )
    expected_fields = {
        module_resolution.ProjectResolvedNominalSymbol: (
            "owning_module_path",
            "local_name",
            "target_identity",
            "target_occurrence",
            "local_occurrence",
            "imported_binding",
        ),
        module_resolution.ProjectModuleTypeReference: (
            "owner",
            "role",
            "member_position",
            "type_expr",
        ),
        module_resolution.ProjectResolvedModuleTypeReference: (
            "reference",
            "direct_kind",
            "direct_symbol",
            "canonical_kind",
            "canonical_name",
            "canonical_target_identity",
            "alias_chain",
        ),
        module_resolution.ProjectModuleSourceShapeReference: ("owner", "source"),
        module_resolution.ProjectResolvedModuleSourceShapeReference: (
            "reference",
            "target_symbol",
        ),
        module_resolution.ProjectTypeSourceResolutionIssue: (
            "status",
            "owning_module_path",
            "local_name",
            "location",
            "related_locations",
            "diagnostic",
            "occurrences",
            "type_reference",
            "source_reference",
            "binding_issues",
            "cycle",
            "alias_cycle",
            "suppressing_diagnostics",
        ),
        module_resolution.ProjectModuleTypeSourceResolutionEnvironment: (
            "module",
            "symbols",
            "type_resolutions",
            "source_shape_references",
            "source_shape_resolutions",
            "issues",
            "_type_symbols_by_name",
            "_source_symbols_by_name",
            "_type_resolutions_by_expr",
            "_source_resolutions_by_source",
        ),
        module_resolution.ProjectTypeSourceResolutionSet: (
            "dependency_order",
            "environments",
            "issues",
            "diagnostics",
            "_environments_by_path",
        ),
    }
    for carrier, expected in expected_fields.items():
        assert tuple(item.name for item in fields(carrier)) == expected
        assert carrier.__dataclass_params__.frozen
        assert "__dict__" not in carrier.__slots__
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE11_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "b81843acadb294630db361c09949868d004b1bca"
    )
    assert len(active_gate2_manifest.PHASE54_SLICE10_ORIGINAL_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS) == 69
    assert len(active_gate2_manifest.ADDED_PATHS) == 3
    assert len(active_gate2_manifest.MODIFIED_PATHS) == 69
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 64
    assert TEST_REL in active_gate2_manifest.MECHANICAL_READER_PATHS
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE == (
        "17a5b01e555930537334d4d0bcf3480e332b7e91"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE == (
        "3f057874a1bec524da38b58c243267f4590c167b"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE == (
        "fcdd02b5604c2b84d861b593a1887eaeb4620c91"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR6_BASE == (
        "c73e5ea0628d821ada5a8cbb93102bae69768600"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR6_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR7_BASE == (
        "a5df3ed264c443d902831fe532d265ac1e452158"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR7_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR8_BASE == (
        "7b96b416d963e67624a461ec906ab2fe14630380"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR8_MODIFIED_PATHS)
        == 43
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_BASE == (
        "38353a00bdaf6b1edb9a0eb53ada1a3249b6ae79"
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS)
        == 66
    )


def test_local_imported_and_reexported_nominal_identities_remain_distinct(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Mid as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Base as Mid\nexport:\n    type Mid\n'
            ),
            "c.pietto": "type Base = Text\nexport:\n    type Base\n",
        },
    )
    a_symbol = _environment(semantic, "a.pietto").find_type_name("Local")[0]
    b_symbol = _environment(semantic, "b.pietto").find_type_name("Mid")[0]
    c_symbol = _environment(semantic, "c.pietto").find_type_name("Base")[0]
    assert a_symbol.imported_binding is not None
    assert b_symbol.imported_binding is not None
    assert c_symbol.local_occurrence is c_symbol.target_occurrence
    assert a_symbol.local_name == "Local"
    assert b_symbol.local_name == "Mid"
    assert (
        a_symbol.target_identity == b_symbol.target_identity == c_symbol.target_identity
    )
    assert a_symbol.target_identity.module_path == "c.pietto"
    assert a_symbol.target_identity.declared_name == "Base"
    assert a_symbol.imported_binding.identity.local_binding_name == "Local"


def test_environment_lookups_are_complete_tuple_backed_and_immutable(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Label = Text\n"
                "shape Row:\n    label: Label\n"
                'source rows: Row is postgres.table("rows")\n'
            )
        },
    )
    resolution_set = _required_set(semantic)
    environment = _environment(semantic, "a.pietto")
    assert isinstance(environment._type_symbols_by_name, MappingProxyType)
    assert isinstance(environment._source_symbols_by_name, MappingProxyType)
    assert isinstance(resolution_set._environments_by_path, MappingProxyType)
    assert len(environment.find_type_name("Label")) == 1
    assert len(environment.find_type_name("Row")) == 1
    assert len(environment.find_source_name("rows")) == 1
    assert environment.find_type_name("missing") == ()
    with pytest.raises(TypeError):
        environment._type_symbols_by_name["Other"] = ()  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        environment.symbols = ()  # type: ignore[misc]


def test_dependency_order_uses_selected_position_for_ready_ties(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": "shape A:\n    id: Int\n",
            "b.pietto": "enum B:\n    ONE\n",
            "c.pietto": 'source c is postgres.table("c")\n',
        },
    )
    assert tuple(item.path for item in _required_set(semantic).dependency_order) == (
        "a.pietto",
        "b.pietto",
        "c.pietto",
    )


def test_dependency_order_places_targets_before_importers(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": ('import "z.pietto":\n    shape Z\nshape A:\n    z: Z\n'),
            "z.pietto": "shape Z:\n    id: Int\nexport:\n    shape Z\n",
        },
    )
    assert tuple(item.path for item in _required_set(semantic).dependency_order) == (
        "z.pietto",
        "a.pietto",
    )


def test_dependency_order_is_deterministic_for_a_diamond(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    shape B\nimport "c.pietto":\n    shape C\n'
            ),
            "b.pietto": (
                'import "d.pietto":\n    shape D\n'
                "shape B:\n    d: D\nexport:\n    shape B\n"
            ),
            "c.pietto": (
                'import "d.pietto":\n    shape D\n'
                "shape C:\n    d: D\nexport:\n    shape C\n"
            ),
            "d.pietto": "shape D:\n    id: Int\nexport:\n    shape D\n",
        },
    )
    assert tuple(item.path for item in _required_set(semantic).dependency_order) == (
        "d.pietto",
        "b.pietto",
        "c.pietto",
        "a.pietto",
    )


def test_cycle_members_are_excluded_and_retain_one_block_issue_each(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape A:\n    id: Int\nexport:\n    shape A\n"
                'import "b.pietto":\n    shape B\n'
            ),
            "b.pietto": (
                "shape B:\n    id: Int\nexport:\n    shape B\n"
                'import "a.pietto":\n    shape A\n'
            ),
        },
    )
    resolution_set = _required_set(semantic)
    assert resolution_set.dependency_order == ()
    assert resolution_set.environments == ()
    assert [item.status for item in resolution_set.issues] == [
        module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
    ]
    assert all(item.diagnostic is None for item in resolution_set.issues)
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2703", "Module import cycle detected: a.pietto -> b.pietto -> a.pietto"),
    )


def test_independent_acyclic_local_errors_remain_visible_with_a_cycle(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": "shape Bad:\n    value: Missing\n",
            "b.pietto": (
                "shape B:\n    id: Int\nexport:\n    shape B\n"
                'import "c.pietto":\n    shape C\n'
            ),
            "c.pietto": (
                "shape C:\n    id: Int\nexport:\n    shape C\n"
                'import "b.pietto":\n    shape B\n'
            ),
        },
    )
    assert tuple(item.path for item in _required_set(semantic).dependency_order) == (
        "a.pietto",
    )
    assert [item.code for item in semantic.diagnostics] == ["PIE-S2703", "PIE-S2002"]
    assert semantic.diagnostics[1].location.path == "a.pietto"


def test_builtin_precedence_and_direct_type_kinds_are_preserved(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "type Int = Text\nshape Row:\n    id: Int\n"},
    )
    environment = _environment(semantic, "a.pietto")
    field = _type_resolution(environment, owner_name="Row", type_name="Int")
    assert environment.find_type_name("Int")[0].declaration_kind is (
        ProjectSymbolKind.TYPE_ALIAS
    )
    assert field.direct_kind is ProjectResolvedTypeKind.BUILTIN
    assert field.direct_symbol is None
    assert field.canonical_kind is ProjectResolvedTypeKind.BUILTIN
    assert field.canonical_name == "Int"
    assert semantic.diagnostics == ()


def test_local_alias_chain_expands_to_builtin(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Email = Text\n"
                "type WorkEmail = Email\n"
                "shape User:\n    email: WorkEmail\n"
            )
        },
    )
    resolution = _type_resolution(
        _environment(semantic, "a.pietto"),
        owner_name="User",
        type_name="WorkEmail",
    )
    assert resolution.direct_kind is ProjectResolvedTypeKind.TYPE_ALIAS
    assert tuple(item.declared_name for item in resolution.alias_chain) == (
        "WorkEmail",
        "Email",
    )
    assert resolution.canonical_kind is ProjectResolvedTypeKind.BUILTIN
    assert resolution.canonical_name == "Text"


def test_cross_module_alias_chain_expands_by_target_identity(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "z.pietto":\n    type WorkEmail\n'
                "shape User:\n    email: WorkEmail\n"
            ),
            "z.pietto": (
                "type Email = Text\n"
                "type WorkEmail = Email\n"
                "export:\n    type WorkEmail\n"
            ),
        },
    )
    resolution = _type_resolution(
        _environment(semantic, "a.pietto"),
        owner_name="User",
        type_name="WorkEmail",
    )
    assert tuple(item.module_path for item in resolution.alias_chain) == (
        "z.pietto",
        "z.pietto",
    )
    assert tuple(item.declared_name for item in resolution.alias_chain) == (
        "WorkEmail",
        "Email",
    )
    assert resolution.canonical_name == "Text"


def test_explicit_reexport_alias_chain_keeps_original_target_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Base as Public\n'
                "export:\n    type Public\n"
            ),
            "c.pietto": "type Base = UUID\nexport:\n    type Base\n",
        },
    )
    resolution = _type_resolution(
        _environment(semantic, "a.pietto"),
        owner_name="Uses",
        type_name="Local",
    )
    assert resolution.direct_symbol is not None
    assert resolution.direct_symbol.local_name == "Local"
    assert resolution.direct_symbol.target_identity.module_path == "c.pietto"
    assert resolution.direct_symbol.target_identity.declared_name == "Base"
    assert tuple(item.module_path for item in resolution.alias_chain) == ("c.pietto",)
    assert resolution.canonical_name == "UUID"


def test_cyclic_direct_facade_reexports_are_no_winner_for_all_slice9_kinds(
    tmp_path: Path,
) -> None:
    def owner_definition(kind: str) -> str:
        if kind == "type":
            declaration = "type Base = Text\n"
        elif kind == "enum":
            declaration = "enum Base:\n    ONE\n"
        elif kind == "shape":
            declaration = "shape Base:\n    id: Int\n"
        else:
            declaration = 'source Base is postgres.table("base")\n'
        return declaration + f"export:\n    {kind} Base\n"

    for kind in ("type", "enum", "shape", "source"):
        for nominal_owner_first in (False, True):
            nominal_owner = "a.pietto" if nominal_owner_first else "c.pietto"
            importer = "z.pietto" if nominal_owner_first else "a.pietto"
            consumer = "" if kind == "source" else "shape Uses:\n    value: Local\n"
            _, semantic = _semantic_project(
                tmp_path / f"{kind}-{'owner' if nominal_owner_first else 'importer'}",
                {
                    nominal_owner: owner_definition(kind),
                    "b.pietto": (
                        f'import "{nominal_owner}":\n    {kind} Base as Public\n'
                        'import "d.pietto":\n    type D\n'
                        f"export:\n    {kind} Public\n"
                    ),
                    "d.pietto": (
                        "type D = Int\nexport:\n    type D\n"
                        f'import "b.pietto":\n    {kind} Public\n'
                    ),
                    importer: (
                        f'import "b.pietto":\n    {kind} Public as Local\n' + consumer
                    ),
                },
            )
            assert _diagnostic_pairs(semantic) == (
                (
                    "PIE-S2703",
                    "Module import cycle detected: b.pietto -> d.pietto -> b.pietto",
                ),
            )
            environment = _environment(semantic, importer)
            winners = (
                environment.find_source_name("Local")
                if kind == "source"
                else environment.find_type_name("Local")
            )
            assert winners == ()
            blockers = tuple(
                issue
                for issue in environment.issues
                if issue.status
                is module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
                and issue.local_name == "Local"
            )
            assert len(blockers) == 1
            blocker = blockers[0]
            assert blocker.cycle is not None
            assert tuple(
                member.identity.path for member in blocker.cycle.component.members
            ) == ("b.pietto", "d.pietto")
            assert tuple(
                (diagnostic.code, diagnostic.message)
                for diagnostic in blocker.suppressing_diagnostics
            ) == _diagnostic_pairs(semantic)
            if kind != "source":
                assert (
                    _type_resolution(
                        environment,
                        owner_name="Uses",
                        type_name="Local",
                    ).direct_kind
                    is ProjectResolvedTypeKind.UNKNOWN
                )


def test_direct_facade_cycle_precedes_nominal_owner_cycle_and_owner_fallback_remains(
    tmp_path: Path,
) -> None:
    _, owner_fallback = _semantic_project(
        tmp_path / "owner-fallback",
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Base as Public\n'
                "export:\n    type Public\n"
            ),
            "c.pietto": (
                "type Base = Text\nexport:\n    type Base\n"
                'import "d.pietto":\n    type D\n'
            ),
            "d.pietto": (
                'type D = Int\nexport:\n    type D\nimport "c.pietto":\n    type Base\n'
            ),
        },
    )
    fallback_environment = _environment(owner_fallback, "a.pietto")
    fallback_blocker = tuple(
        issue
        for issue in fallback_environment.issues
        if issue.status
        is module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
        and issue.local_name == "Local"
    )
    assert len(fallback_blocker) == 1
    assert fallback_blocker[0].cycle is not None
    assert tuple(
        member.identity.path for member in fallback_blocker[0].cycle.component.members
    ) == ("c.pietto", "d.pietto")
    assert fallback_environment.find_type_name("Local") == ()
    assert _diagnostic_pairs(owner_fallback) == (
        (
            "PIE-S2703",
            "Module import cycle detected: c.pietto -> d.pietto -> c.pietto",
        ),
    )

    _, both_cyclic = _semantic_project(
        tmp_path / "both-cyclic",
        {
            "a.pietto": (
                'import "b.pietto":\n    type Public as Local\n'
                "shape Uses:\n    value: Local\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    type Base as Public\n'
                'import "d.pietto":\n    type D\n'
                "export:\n    type Public\n"
            ),
            "c.pietto": (
                "type Base = Text\nexport:\n    type Base\n"
                'import "e.pietto":\n    type E\n'
            ),
            "d.pietto": (
                "type D = Int\nexport:\n    type D\n"
                'import "b.pietto":\n    type Public\n'
            ),
            "e.pietto": (
                'type E = Int\nexport:\n    type E\nimport "c.pietto":\n    type Base\n'
            ),
        },
    )
    both_environment = _environment(both_cyclic, "a.pietto")
    both_blocker = tuple(
        issue
        for issue in both_environment.issues
        if issue.status
        is module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
        and issue.local_name == "Local"
    )
    assert len(both_blocker) == 1
    assert both_blocker[0].cycle is not None
    assert tuple(
        member.identity.path for member in both_blocker[0].cycle.component.members
    ) == ("b.pietto", "d.pietto")
    assert tuple(
        (diagnostic.code, diagnostic.message)
        for diagnostic in both_blocker[0].suppressing_diagnostics
    ) == (
        (
            "PIE-S2703",
            "Module import cycle detected: b.pietto -> d.pietto -> b.pietto",
        ),
    )
    assert both_environment.find_type_name("Local") == ()
    assert (
        _type_resolution(
            both_environment,
            owner_name="Uses",
            type_name="Local",
        ).direct_kind
        is ProjectResolvedTypeKind.UNKNOWN
    )


def test_imported_enums_are_nominal_and_not_flattened(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    enum Status as BStatus\n'
                'import "c.pietto":\n    enum Status as CStatus\n'
                "shape Row:\n    left: BStatus\n    right: CStatus\n"
            ),
            "b.pietto": "enum Status:\n    ACTIVE\nexport:\n    enum Status\n",
            "c.pietto": "enum Status:\n    ACTIVE\nexport:\n    enum Status\n",
        },
    )
    environment = _environment(semantic, "a.pietto")
    left = _type_resolution(environment, owner_name="Row", type_name="BStatus")
    right = _type_resolution(environment, owner_name="Row", type_name="CStatus")
    assert left.direct_kind is right.direct_kind is ProjectResolvedTypeKind.ENUM
    assert left.canonical_target_identity is not None
    assert right.canonical_target_identity is not None
    assert left.canonical_target_identity.module_path == "b.pietto"
    assert right.canonical_target_identity.module_path == "c.pietto"
    assert left.canonical_target_identity != right.canonical_target_identity


def test_imported_shapes_are_nominal_and_field_types_resolve(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    shape User as RemoteUser\n'
                "type UserAlias = RemoteUser\n"
            ),
            "b.pietto": ("shape User:\n    id: UUID\nexport:\n    shape User\n"),
        },
    )
    imported = _type_resolution(
        _environment(semantic, "a.pietto"),
        owner_name="UserAlias",
        type_name="RemoteUser",
    )
    target_field = _type_resolution(
        _environment(semantic, "b.pietto"),
        owner_name="User",
        type_name="UUID",
    )
    assert imported.direct_kind is ProjectResolvedTypeKind.SHAPE
    assert imported.canonical_target_identity is not None
    assert imported.canonical_target_identity.module_path == "b.pietto"
    assert target_field.canonical_name == "UUID"


def test_shape_field_reference_order_and_duplicates_are_preserved(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "shape Row:\n    value: Int\n    value: Text\n"},
    )
    resolutions = tuple(
        item
        for item in _environment(semantic, "a.pietto").type_resolutions
        if item.reference.owner.identity.declared_name == "Row"
    )
    assert tuple(item.reference.member_position for item in resolutions) == (0, 1)
    assert tuple(item.reference.type_expr.name for item in resolutions) == (
        "Int",
        "Text",
    )
    assert semantic.diagnostics == ()


def test_duplicate_local_type_name_is_one_pie_s2001_no_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Shared = Int\n"
                "enum Shared:\n    ONE\n"
                "shape Uses:\n    value: Shared\n"
            )
        },
    )
    environment = _environment(semantic, "a.pietto")
    assert environment.find_type_name("Shared") == ()
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2001", "Duplicate symbol name in type namespace: Shared"),
    )
    resolution = _type_resolution(environment, owner_name="Uses", type_name="Shared")
    assert resolution.direct_kind is ProjectResolvedTypeKind.UNKNOWN


def test_duplicate_local_source_name_is_one_pie_s2001_no_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'source rows is postgres.table("first")\n'
                'source rows is postgres.table("second")\n'
            )
        },
    )
    environment = _environment(semantic, "a.pietto")
    assert environment.find_source_name("rows") == ()
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2001", "Duplicate symbol name in relation namespace: rows"),
    )


def test_local_alias_cycle_emits_one_exact_pie_s2003(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "type A = B\ntype B = A\n"},
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2003", "Type alias cycle involving A"),
    )
    environment = _environment(semantic, "a.pietto")
    assert all(
        item.canonical_kind is ProjectResolvedTypeKind.UNKNOWN
        for item in environment.type_resolutions
    )


def test_multiple_alias_cycles_follow_dependency_and_source_order(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": "type A = A\ntype C = C\n",
            "z.pietto": "type Z = Z\n",
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2003", "Type alias cycle involving A"),
        ("PIE-S2003", "Type alias cycle involving C"),
        ("PIE-S2003", "Type alias cycle involving Z"),
    )


def test_unknown_alias_target_emits_one_pie_s2002_without_cascade(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": ("type A = Missing\ntype B = A\nshape Row:\n    value: B\n")},
    )
    assert _diagnostic_pairs(semantic) == (("PIE-S2002", "Unknown type: Missing"),)
    environment = _environment(semantic, "a.pietto")
    assert all(
        item.canonical_kind is ProjectResolvedTypeKind.UNKNOWN
        for item in environment.type_resolutions
        if item.reference.type_expr.name in {"Missing", "A", "B"}
    )


def test_unknown_shape_field_type_emits_exact_pie_s2002(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "shape Row:\n    value: Missing\n"},
    )
    assert _diagnostic_pairs(semantic) == (("PIE-S2002", "Unknown type: Missing"),)
    diagnostic = semantic.diagnostics[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.location.path == "a.pietto"
    assert diagnostic.location.line == 2


def test_unresolved_import_root_suppresses_derived_type_error(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "missing.pietto":\n    type Missing as Local\n'
                "shape Row:\n    value: Local\n"
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2701", 'Unresolved module import target: "missing.pietto"'),
    )
    issues = _environment(semantic, "a.pietto").issues
    assert any(
        issue.status
        is module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED
        and tuple(item.code for item in issue.suppressing_diagnostics) == ("PIE-S2701",)
        for issue in issues
    )


def test_private_import_root_suppresses_derived_type_error(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n    type Hidden as Local\n'
                "shape Row:\n    value: Local\n"
            ),
            "b.pietto": "type Hidden = Text\n",
        },
    )
    assert [item.code for item in semantic.diagnostics] == ["PIE-S2705"]
    assert "private or not exported" in semantic.diagnostics[0].message
    resolution = _type_resolution(
        _environment(semantic, "a.pietto"),
        owner_name="Row",
        type_name="Local",
    )
    assert resolution.direct_kind is ProjectResolvedTypeKind.UNKNOWN


def test_import_collision_is_no_winner_and_suppresses_consumers(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Local = Text\n"
                'import "b.pietto":\n    type B as Local\n'
                "shape Row:\n    value: Local\n"
            ),
            "b.pietto": "type B = Int\nexport:\n    type B\n",
        },
    )
    assert [item.code for item in semantic.diagnostics] == ["PIE-S2706"]
    environment = _environment(semantic, "a.pietto")
    assert environment.find_type_name("Local") == ()
    assert (
        _type_resolution(
            environment,
            owner_name="Row",
            type_name="Local",
        ).direct_kind
        is ProjectResolvedTypeKind.UNKNOWN
    )


def test_all_import_kind_local_candidate_collisions_are_no_winner(
    tmp_path: Path,
) -> None:
    library_source = (
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "    inactive\n"
        "shape Customer:\n"
        "    id: UUID not null\n"
        'source customers: Customer is postgres.table("public.customers")\n'
        "table CustomerTable:\n"
        "    from customers\n"
        "    select:\n"
        "        id\n"
        "query CustomerQuery:\n"
        "    from CustomerTable\n"
        "    select:\n"
        "        id\n"
        "export:\n"
        "    type Email\n"
        "    enum Status\n"
        "    shape Customer\n"
        "    source customers\n"
        "    table CustomerTable\n"
        "    query CustomerQuery\n"
    )
    import_targets = (
        ("type", "Email"),
        ("enum", "Status"),
        ("shape", "Customer"),
        ("source", "customers"),
        ("table", "CustomerTable"),
        ("query", "CustomerQuery"),
    )
    local_candidates = {
        "type": "type X = Text\nshape Consumer:\n    value: X\n",
        "enum": "enum X:\n    one\nshape Consumer:\n    value: X\n",
        "shape": ("shape X:\n    value: Text\nshape Consumer:\n    value: X\n"),
        "source": (
            "shape LocalRow:\n"
            "    value: Text\n"
            'source X: LocalRow is postgres.table("local")\n'
        ),
    }

    for import_kind, exported_name in import_targets:
        for local_kind, local_source in local_candidates.items():
            _, semantic = _semantic_project(
                tmp_path / f"{import_kind}-{local_kind}",
                {
                    "a.pietto": (
                        local_source
                        + 'import "library.pietto":\n'
                        + f"    {import_kind} {exported_name} as X\n"
                    ),
                    "library.pietto": library_source,
                },
            )
            assert _diagnostic_pairs(semantic) == (
                (
                    "PIE-S2706",
                    "Import binding collides with a local declaration: X",
                ),
            )
            environment = _environment(semantic, "a.pietto")
            assert environment.find_type_name("X") == ()
            assert environment.find_source_name("X") == ()
            blockers = tuple(
                issue
                for issue in environment.issues
                if issue.status
                is module_resolution.ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED
                and issue.local_name == "X"
            )
            assert len(blockers) == 1
            assert tuple(item.code for item in blockers[0].suppressing_diagnostics) == (
                "PIE-S2706",
            )
            if local_kind != "source":
                resolution = _type_resolution(
                    environment,
                    owner_name="Consumer",
                    type_name="X",
                )
                assert resolution.direct_kind is ProjectResolvedTypeKind.UNKNOWN


def test_export_and_inconsistent_facade_roots_suppress_consumers(
    tmp_path: Path,
) -> None:
    _, duplicate = _semantic_project(
        tmp_path / "duplicate",
        {
            "a.pietto": (
                'import "b.pietto":\n    shape Shared\nshape Row:\n    value: Shared\n'
            ),
            "b.pietto": (
                "shape Shared:\n    id: Int\n"
                "export:\n    shape Shared\n    shape Shared\n"
            ),
        },
    )
    assert [item.code for item in duplicate.diagnostics] == ["PIE-S2704"]

    _, inconsistent = _semantic_project(
        tmp_path / "inconsistent",
        {
            "a.pietto": (
                'import "b.pietto":\n    shape Shared\nshape Row:\n    value: Shared\n'
            ),
            "b.pietto": (
                "query Shared:\n    from missing\n    select:\n        id\n"
                "export:\n    query Shared\n"
            ),
        },
    )
    assert [item.code for item in inconsistent.diagnostics] == [
        "PIE-S2707",
        "PIE-S2301",
    ]


def test_local_source_shape_resolves_direct_shape(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'shape Row:\n    id: Int\nsource rows: Row is postgres.table("rows")\n'
            )
        },
    )
    environment = _environment(semantic, "a.pietto")
    source_symbol = environment.find_source_name("rows")[0]
    assert source_symbol.declaration_kind is ProjectSymbolKind.SOURCE
    assert len(environment.source_shape_references) == 1
    resolution = environment.source_shape_resolutions[0]
    assert resolution.target_symbol.local_name == "Row"
    assert resolution.target_symbol.declaration_kind is ProjectSymbolKind.SHAPE
    assert semantic.diagnostics == ()


def test_imported_source_and_shape_keep_both_local_and_target_identity(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "b.pietto":\n'
                "    shape Row as RemoteRow\n"
                "    source rows as remote_rows\n"
                'source local_rows: RemoteRow is postgres.table("local")\n'
            ),
            "b.pietto": (
                "shape Row:\n    id: UUID\n"
                'source rows: Row is postgres.table("rows")\n'
                "export:\n    shape Row\n    source rows\n"
            ),
        },
    )
    environment = _environment(semantic, "a.pietto")
    imported_source = environment.find_source_name("remote_rows")[0]
    shape_resolution = environment.source_shape_resolutions[0]
    assert imported_source.imported_binding is not None
    assert imported_source.local_name == "remote_rows"
    assert imported_source.target_identity.module_path == "b.pietto"
    assert imported_source.target_identity.declared_name == "rows"
    assert shape_resolution.target_symbol.local_name == "RemoteRow"
    assert shape_resolution.target_symbol.target_identity.module_path == "b.pietto"
    assert shape_resolution.target_symbol.target_identity.declared_name == "Row"


def test_source_unknown_and_wrong_kind_emit_exact_pie_s2303(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "type Alias = Text\n"
                "enum Status:\n    ACTIVE\n"
                'source missing: Missing is postgres.table("missing")\n'
                'source alias_rows: Alias is postgres.table("alias")\n'
                'source status_rows: Status is postgres.table("status")\n'
                'source int_rows: Int is postgres.table("ints")\n'
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2303", "Unknown source shape: Missing"),
        ("PIE-S2303", "Source shape must refer to a shape: Alias"),
        ("PIE-S2303", "Source shape must refer to a shape: Status"),
        ("PIE-S2303", "Source shape must refer to a shape: Int"),
    )


def test_schema_v1_deferred_surfaces_and_public_privacy_are_exact(
    tmp_path: Path,
) -> None:
    _, legacy = _semantic_project(
        tmp_path / "legacy",
        {
            "a.pietto": "shape Row:\n    value: Shared\n",
            "b.pietto": "type Shared = Text\n",
        },
        schema_version=1,
    )
    assert legacy.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert legacy.model is not None
    assert legacy.module_type_source_resolutions is None
    assert legacy.diagnostics == ()

    parse_result, explicit = _semantic_project(
        tmp_path / "explicit",
        {
            "a.pietto": (
                'import "b.pietto":\n    type Shared\n'
                "constraint accepts(value: Shared) -> Bool:\n    true\n"
                "table deferred:\n    from missing\n    select:\n        value\n"
            ),
            "b.pietto": "type Shared = Text\nexport:\n    type Shared\n",
        },
    )
    environment = _environment(explicit, "a.pietto")
    assert environment.find_type_name("Shared")
    assert environment.type_resolutions == ()
    assert explicit.model is None
    assert _diagnostic_pairs(explicit) == (("PIE-S2301", "Unknown relation: missing"),)
    assert explicit.module_relation_resolutions is not None
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)
    assert "module_type_source_resolutions" not in serialized
    assert "ProjectResolvedNominalSymbol" not in serialized
    public_source = (REPO_ROOT / "src/pietto/__init__.py").read_text(encoding="utf-8")
    assert "ProjectTypeSourceResolutionSet" not in public_source


def test_text_json_status_docs_and_reader_fixed_point_are_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(
        tmp_path,
        {
            "a.pietto": (
                'import "missing.pietto":\n    type Missing as Blocked\n'
                "shape Bad:\n    value: Unknown\n"
                'source rows: MissingShape is postgres.table("rows")\n'
            )
        },
    )
    assert cli.main(["check", "--project", str(root)]) == 1
    text_result = capsys.readouterr()
    assert text_result.out == ""
    assert [
        text_result.err.index(code) for code in ("PIE-S2701", "PIE-S2002", "PIE-S2303")
    ] == sorted(
        text_result.err.index(code) for code in ("PIE-S2701", "PIE-S2002", "PIE-S2303")
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
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
    assert [item["code"] for item in diagnostics] == [
        "PIE-S2701",
        "PIE-S2002",
        "PIE-S2303",
    ]
    assert "module_type_source_resolutions" not in json.dumps(document)

    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    tests = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tests == EXPECTED_TEST_NAMES
    assert len(tests) == 33
    assert all(
        not node.decorator_list
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(active_gate2_manifest.PHASE54_ACTIVE_GATE2_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE54_ACTIVE_GATE2_MODIFIED_PATHS) == 69
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert len(active_gate2_manifest.VALIDATION_READER_PATHS) == 64
    assert len(active_gate2_manifest.MECHANICAL_READER_PATHS) == 64
    assert (
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py"
        in active_gate2_manifest.MECHANICAL_READER_PATHS
    )
    assert (
        "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py"
        in active_gate2_manifest.MECHANICAL_READER_PATHS
    )
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    registry = (REPO_ROOT / "docs/spec/diagnostics.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    whitepaper = (REPO_ROOT / "docs/spec/pietto-v0.9.md").read_text(encoding="utf-8")
    for required in (
        "dependency-first",
        "ProjectResolvedNominalSymbol",
        "PIE-S2001",
        "PIE-S2002",
        "PIE-S2003",
        "PIE-S2303",
        "Slice 10 retains",
        "Schema v1",
        "model=None",
    ):
        assert required in spec
    for code in ("PIE-S2001", "PIE-S2002", "PIE-S2003", "PIE-S2303"):
        assert code in registry
    assert "Slice 11 is the" in readme
    assert "PHASE54_SLICE11_GATE3" in readme
    assert "Status And Slice 11 Lifecycle" in plan
    assert "Current Phase 54 Slice 11 Module Attribution Status" in whitepaper
