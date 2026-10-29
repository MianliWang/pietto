from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import json
from pathlib import Path
from types import MappingProxyType
from typing import cast

import pytest

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
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
    ProjectConcreteCompletedSemanticResult,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/_project/module_resolution.py"
TEST_REL = "tests/test_project_cross_module_type_alias_enum_shape_source_resolution.py"


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


def test_local_imported_and_reexported_nominal_identities_remain_distinct(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'from "b.pietto" import (\n'
                "    type Mid as Local)\n"
                "shape Uses:\n"
                "    value: Local\n"
            ),
            "b.pietto": (
                'from "c.pietto" import (\n    type Base as Mid)\nexport (\n    type Mid)\n'
            ),
            "c.pietto": "type Base = Text\nexport (\n    type Base)\n",
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
                "shape Row:\n"
                "    label: Label\n"
                'source rows: Row = postgres.table("rows")\n'
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
            "c.pietto": 'source c = postgres.table("c")\n',
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
            "a.pietto": (
                'from "z.pietto" import (\n    shape Z)\nshape A:\n    z: Z\n'
            ),
            "z.pietto": "shape Z:\n    id: Int\nexport (\n    shape Z)\n",
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
                'from "b.pietto" import (\n    shape B)\nfrom "c.pietto" import (\n    shape C)\n'
            ),
            "b.pietto": (
                'from "d.pietto" import (\n'
                "    shape D)\n"
                "shape B:\n"
                "    d: D\n"
                "export (\n"
                "    shape B)\n"
            ),
            "c.pietto": (
                'from "d.pietto" import (\n'
                "    shape D)\n"
                "shape C:\n"
                "    d: D\n"
                "export (\n"
                "    shape C)\n"
            ),
            "d.pietto": "shape D:\n    id: Int\nexport (\n    shape D)\n",
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
                "shape A:\n"
                "    id: Int\n"
                "export (\n"
                "    shape A)\n"
                'from "b.pietto" import (\n'
                "    shape B)\n"
            ),
            "b.pietto": (
                "shape B:\n"
                "    id: Int\n"
                "export (\n"
                "    shape B)\n"
                'from "a.pietto" import (\n'
                "    shape A)\n"
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
                "shape B:\n"
                "    id: Int\n"
                "export (\n"
                "    shape B)\n"
                'from "c.pietto" import (\n'
                "    shape C)\n"
            ),
            "c.pietto": (
                "shape C:\n"
                "    id: Int\n"
                "export (\n"
                "    shape C)\n"
                'from "b.pietto" import (\n'
                "    shape B)\n"
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
                'from "z.pietto" import (\n'
                "    type WorkEmail)\n"
                "shape User:\n"
                "    email: WorkEmail\n"
            ),
            "z.pietto": (
                "type Email = Text\n"
                "type WorkEmail = Email\n"
                "export (\n"
                "    type WorkEmail)\n"
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
                'from "b.pietto" import (\n'
                "    type Public as Local)\n"
                "shape Uses:\n"
                "    value: Local\n"
            ),
            "b.pietto": (
                'from "c.pietto" import (\n'
                "    type Base as Public)\n"
                "export (\n"
                "    type Public)\n"
            ),
            "c.pietto": "type Base = UUID\nexport (\n    type Base)\n",
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
            declaration = 'source Base = postgres.table("base")\n'
        return declaration + f"export (\n    {kind} Base)\n"

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
                        f'from "{nominal_owner}" import (\n    {kind} Base as Public)\nfrom "d.pietto" import (\n    type D)\nexport (\n    {kind} Public)\n'
                    ),
                    "d.pietto": (
                        f'type D = Int\nexport (\n    type D)\nfrom "b.pietto" import (\n    {kind} Public)\n'
                    ),
                    importer: (
                        f'from "b.pietto" import (\n    {kind} Public as Local)\n'
                        + consumer
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
                'from "b.pietto" import (\n'
                "    type Public as Local)\n"
                "shape Uses:\n"
                "    value: Local\n"
            ),
            "b.pietto": (
                'from "c.pietto" import (\n'
                "    type Base as Public)\n"
                "export (\n"
                "    type Public)\n"
            ),
            "c.pietto": (
                "type Base = Text\n"
                "export (\n"
                "    type Base)\n"
                'from "d.pietto" import (\n'
                "    type D)\n"
            ),
            "d.pietto": (
                'type D = Int\nexport (\n    type D)\nfrom "c.pietto" import (\n    type Base)\n'
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
                'from "b.pietto" import (\n'
                "    type Public as Local)\n"
                "shape Uses:\n"
                "    value: Local\n"
            ),
            "b.pietto": (
                'from "c.pietto" import (\n'
                "    type Base as Public)\n"
                'from "d.pietto" import (\n'
                "    type D)\n"
                "export (\n"
                "    type Public)\n"
            ),
            "c.pietto": (
                "type Base = Text\n"
                "export (\n"
                "    type Base)\n"
                'from "e.pietto" import (\n'
                "    type E)\n"
            ),
            "d.pietto": (
                "type D = Int\n"
                "export (\n"
                "    type D)\n"
                'from "b.pietto" import (\n'
                "    type Public)\n"
            ),
            "e.pietto": (
                'type E = Int\nexport (\n    type E)\nfrom "c.pietto" import (\n    type Base)\n'
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
                'from "b.pietto" import (\n'
                "    enum Status as BStatus)\n"
                'from "c.pietto" import (\n'
                "    enum Status as CStatus)\n"
                "shape Row:\n"
                "    left: BStatus\n"
                "    right: CStatus\n"
            ),
            "b.pietto": "enum Status:\n    ACTIVE\nexport (\n    enum Status)\n",
            "c.pietto": "enum Status:\n    ACTIVE\nexport (\n    enum Status)\n",
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
                'from "b.pietto" import (\n'
                "    shape User as RemoteUser)\n"
                "type UserAlias = RemoteUser\n"
            ),
            "b.pietto": ("shape User:\n    id: UUID\nexport (\n    shape User)\n"),
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
                'source rows = postgres.table("first")\n'
                'source rows = postgres.table("second")\n'
            )
        },
    )
    environment = _environment(semantic, "a.pietto")
    assert environment.find_source_name("rows") == ()
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2001", "Duplicate symbol name in relation namespace: rows"),
    )


_REPEATED_ENUM_MEMBER_SOURCES = {
    "a.pietto": (
        "enum Status:\n"
        "    active\n"
        "    held\n"
        "    active\n"
        "    held\n"
        "    active\n"
        "shape C:\n"
        "    id: Int\n"
        "    status: Status\n"
        "    k = unique(nosuch)\n"
        'source cs: C = postgres.table("cs")\n'
    ),
    "b.pietto": (
        "enum Kind:\n"
        "    x\n"
        "    x\n"
        "enum Kind:\n"
        "    y\n"
        "    y\n"
        "shape D:\n"
        "    id: Int\n"
        "    k = unique(id, id)\n"
    ),
}


def test_project_check_reports_repeated_enum_members_like_a_single_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, explicit = _semantic_project(
        tmp_path / "explicit", _REPEATED_ENUM_MEMBER_SOURCES
    )
    diagnostics = build_project_completed_semantic_result(explicit).diagnostics

    # Per module in selected-module order, after the semantic analysis
    # diagnostics and before the shape item diagnostics.
    assert [
        (
            item.code,
            item.message,
            item.location.path,
            item.location.line,
            item.location.column,
        )
        for item in diagnostics
    ] == [
        (
            "PIE-S2001",
            "Duplicate symbol name in type namespace: Kind",
            "b.pietto",
            4,
            1,
        ),
        ("PIE-S2001", "Duplicate member name in enum Status: active", "a.pietto", 1, 1),
        ("PIE-S2001", "Duplicate member name in enum Status: held", "a.pietto", 1, 1),
        ("PIE-S2001", "Duplicate member name in enum Kind: x", "b.pietto", 1, 1),
        ("PIE-S2001", "Duplicate member name in enum Kind: y", "b.pietto", 4, 1),
        ("PIE-S2502", "Unknown target field in shape C: nosuch", "a.pietto", 10, 5),
        ("PIE-S2503", "Duplicate target field in unique k: id", "b.pietto", 9, 5),
    ]
    for path, source in _REPEATED_ENUM_MEMBER_SOURCES.items():
        parsed = parse_source(source, path=path)
        assert parsed.ast is not None
        members = [
            item
            for item in analyze(parsed.ast).diagnostics
            if item.message.startswith("Duplicate member name")
        ]
        assert members == [
            item
            for item in diagnostics
            if item.location.path == path
            and item.message.startswith("Duplicate member name")
        ]

    # A LEGACY_FLAT check reports them and the shape item errors with the
    # single-file checks of its files, after its project
    # model's one diagnostic.
    _, legacy = _semantic_project(
        tmp_path / "legacy", _REPEATED_ENUM_MEMBER_SOURCES, schema_version=1
    )
    assert legacy.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert _diagnostic_pairs(legacy) == (
        ("PIE-S2001", "Duplicate symbol name in type namespace: Kind"),
    )
    command = ["check", "--project", str(tmp_path / "legacy"), "--format", "json"]
    assert cli.main(command) == 1
    document = json.loads(capsys.readouterr().out)
    assert [
        (
            item["code"],
            item["message"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in document["diagnostics"]
    ] == [
        (
            "PIE-S2001",
            "Duplicate symbol name in type namespace: Kind",
            "b.pietto",
            4,
            1,
        ),
        ("PIE-S2001", "Duplicate member name in enum Status: active", "a.pietto", 1, 1),
        ("PIE-S2001", "Duplicate member name in enum Status: held", "a.pietto", 1, 1),
        ("PIE-S2502", "Unknown target field in shape C: nosuch", "a.pietto", 10, 5),
        ("PIE-S2001", "Duplicate member name in enum Kind: x", "b.pietto", 1, 1),
        ("PIE-S2001", "Duplicate member name in enum Kind: y", "b.pietto", 4, 1),
        ("PIE-S2503", "Duplicate target field in unique k: id", "b.pietto", 9, 5),
    ]


def test_a_project_types_an_imported_enum_field_and_its_alias_as_the_enum(
    tmp_path: Path,
) -> None:
    """A field of an enum, also imported under another name or through a type
    alias of it, is read as that enum, as in a single file: a WHERE needs a
    Bool, an `in` list labels of the enum, `lower` a Text and a def its
    parameter's type, while a comparison stays Bool. Before, the field was of
    unknown type, so these passed or left the relation to PIE-S2333."""
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'from "b.pietto" import (\n'
                "    enum Status as BStatus)\n"
                "type St = BStatus\n"
                "shape U:\n"
                "    id: Int\n"
                "    st: BStatus\n"
                "    sa: St | None\n"
                'source us: U = postgres.table("us")\n'
                "def tn(x: Text) -> Text: return x\n"
                "query q:\n"
                "    from us\n"
                "    where st\n"
                "    select:\n"
                "        id\n"
                '        a = st in ("held", "gone")\n'
                "        b = tn(sa)\n"
                "        c = lower(st)\n"
                '        d = st == "active"\n'
                "        e = sa\n"
                '        f = sa in ("active", "held")\n'
            ),
            "b.pietto": "enum Status:\n    active\n    held\nexport (\n    enum Status)\n",
        },
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in build_project_completed_semantic_result(semantic).diagnostics
    ] == [
        ("PIE-S2202", "Expected Bool expression in where clause", 12, 11),
        (
            "PIE-S2105",
            "Invalid operands for operator in: expected same canonical membership "
            "operands",
            15,
            13,
        ),
        (
            "PIE-S2395",
            "Invalid argument for def tn at position 1 (x): expected Text, "
            "got Status | None",
            16,
            13,
        ),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: expected Text, "
            "got Status",
            17,
            13,
        ),
    ]


_SHAPE_FIELDS = """shape Address:
    city: Text
shape Customer:
    id: Int
    home: Address | None
    work: Address
shape Order:
    customer_id: Int
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
query q:
    from customers
"""
_NUMERIC = "Invalid operands for operator {}: expected numeric operand{}"
_JOINED = "    let o = orders\n    {} join o on o.customer_id == customers.id\n"


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "    where home + 1 > 2\n    select:\n        id\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 13, 11),
        ),
        (
            "    let b = work * 2\n    select:\n        id\n",
            ("PIE-S2105", _NUMERIC.format("*", "s"), 13, 13),
        ),
        (
            "    let h = home\n    where h + 1 > 2\n    select:\n        id\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 14, 11),
        ),
        (
            "    where any(o.customer_id == id and -work > 0 for o in orders)\n"
            "    select:\n        id\n",
            ("PIE-S2105", _NUMERIC.format("-", ""), 13, 39),
        ),
        (
            "    select:\n        id\n        x = home * 2\n",
            ("PIE-S2105", _NUMERIC.format("*", "s"), 15, 13),
        ),
        (
            "    select:\n        id\n        n = len(work)\n",
            (
                "PIE-S2104",
                "Invalid argument type for function len at position 1: expected "
                "Text, got Address",
                15,
                13,
            ),
        ),
        (
            _JOINED.format("inner") + "    where customers.home + 1 > 2\n"
            "    select:\n        id = customers.id\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 15, 11),
        ),
        (
            _JOINED.format("left") + "    where -customers.work > 0\n"
            "    select:\n        id = customers.id\n",
            ("PIE-S2105", _NUMERIC.format("-", ""), 15, 11),
        ),
        (
            _JOINED.format("inner") + '    where lower(customers.work) == "x"\n'
            "    select:\n        id = customers.id\n",
            (
                "PIE-S2104",
                "Invalid argument type for function lower at position 1: expected "
                "Text, got Address",
                15,
                11,
            ),
        ),
        # Before: a `let` value after a JOIN passed `check --project`, or
        # reported only PIE-S2333 at the query for arithmetic.
        (
            _JOINED.format("inner") + "    let s = len(customers.work)\n"
            "    where s > 0\n    select:\n        id = customers.id\n",
            (
                "PIE-S2104",
                "Invalid argument type for function len at position 1: expected "
                "Text, got Address",
                15,
                13,
            ),
        ),
        (
            _JOINED.format("inner") + "    let s = customers.work == 1\n"
            "    where s\n    select:\n        id = customers.id\n",
            (
                "PIE-S2105",
                "Invalid operands for operator ==: expected comparable operands",
                15,
                13,
            ),
        ),
        (
            _JOINED.format("inner") + "    let s = customers.home + 1\n"
            "    where s > 0\n    select:\n        id = customers.id\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 15, 13),
        ),
        # Before: the ungrouped ORDER BY of a relation without JOIN inputs
        # passed `check --project`, and project emission refused it.
        (
            "    select:\n        id\n    order by:\n        work + 1\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 16, 9),
        ),
        (
            "    select:\n        id\n    order by:\n        id\n        -work\n",
            ("PIE-S2105", _NUMERIC.format("-", ""), 17, 9),
        ),
        (
            "    let h = work\n    select:\n        id\n    order by:\n        h + 1\n",
            ("PIE-S2105", _NUMERIC.format("+", "s"), 17, 9),
        ),
        (
            "    let h = home\n    let g = h\n    select:\n        id\n"
            "    order by:\n        lower(g)\n",
            (
                "PIE-S2104",
                "Invalid argument type for function lower at position 1: expected "
                "Text, got Address",
                18,
                9,
            ),
        ),
    ),
)
def test_a_project_types_a_shape_field_as_that_shape(
    tmp_path: Path, body: str, expected: tuple[str, str, int, int]
) -> None:
    """A field of a shape, also through a `let` name or after a JOIN, is read
    as that shape, as in a single file, so arithmetic, `len` and `lower`
    refuse it. Before, the field was of unknown type: `check --project`
    passed these in a WHERE, `let` or `any(...)` and reported a select item
    with the bare PIE-S2333 only."""
    source = _SHAPE_FIELDS + body
    _, semantic = _semantic_project(tmp_path, {"a.pietto": source})
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in build_project_completed_semantic_result(semantic).diagnostics
    ] == [expected]
    parsed = parse_source(source, path="a.pietto")
    assert parsed.ast is not None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [expected]


# Before: a project listed the error of a shape field after the other errors
# of its expression, and kept the error that typing the field as unknown gave
# beside the one a single file reports (`lower(home) + 1`).
@pytest.mark.parametrize(
    "body",
    (
        "    where home + 1 > 2 and nosuch > 1\n    select:\n        id\n",
        "    where lower(home) + 1 > 0\n    select:\n        id\n",
        _JOINED.format("inner") + "    where customers.home + 1 > 2 and nosuch > 1\n"
        "    select:\n        id = customers.id\n",
    ),
    ids=("order", "nested-call", "joined-order"),
)
def test_a_project_reports_a_shape_field_error_as_a_single_file_does(
    tmp_path: Path, body: str
) -> None:
    source = _SHAPE_FIELDS + body
    _, semantic = _semantic_project(tmp_path, {"a.pietto": source})
    parsed = parse_source(source, path="a.pietto")
    assert parsed.ast is not None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in build_project_completed_semantic_result(semantic).diagnostics
    ] == [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ]


@pytest.mark.parametrize(
    "body",
    (
        "    let h = home\n    where home is None\n"
        "    select:\n        id\n        k = h is None\n        w = work\n",
        "    where any(o.customer_id == id for o in orders) and work is not None\n"
        "    select:\n        id\n",
        "    let h = home\n    select:\n        id\n        p = lag(h) window(order by id)\n",
        _JOINED.format("inner") + "    where customers.home is None\n"
        "    select:\n        id = customers.id\n",
        _JOINED.format("inner") + "    let s = customers.home is None\n"
        "    where s\n    select:\n        id = customers.id\n",
        "    select:\n        id\n    order by:\n        id + 1\n",
    ),
)
def test_a_project_keeps_the_reads_a_shape_field_admits(
    tmp_path: Path, body: str
) -> None:
    _, semantic = _semantic_project(tmp_path, {"a.pietto": _SHAPE_FIELDS + body})

    assert build_project_completed_semantic_result(semantic).diagnostics == ()


# A `select distinct` query and a captured outer field read a shape as that
# shape too; a single file accepts neither form, so only the project is shown.
@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "    from customers\n    where home + 1 > 2\n"
            "    select distinct:\n        id\n",
            [("PIE-S2105", _NUMERIC.format("+", "s"), 13, 11)],
        ),
        (
            "    let ords:\n        capture customers\n        from orders\n"
            "        where customers.work + 1 > 0\n"
            "        select:\n            customer_id\n"
            "    from customers\n    let o = ords\n    cross join o\n"
            "    select:\n        i = customers.id\n",
            [
                ("PIE-S2105", _NUMERIC.format("+", "s"), 15, 15),
                (
                    "PIE-S2333",
                    "Project relation semantic completion is unavailable: q",
                    11,
                    1,
                ),
            ],
        ),
        (
            "    let ords:\n        capture customers\n        from orders\n"
            "        where customers.home is None\n"
            "        select:\n            customer_id\n"
            "    from customers\n    let o = ords\n    cross join o\n"
            "    select:\n        i = customers.id\n",
            [],
        ),
    ),
    ids=("distinct", "captured", "captured_is_none"),
)
def test_a_project_types_a_distinct_or_captured_shape_field_as_that_shape(
    tmp_path: Path, body: str, expected: list[tuple[str, str, int, int]]
) -> None:
    source = _SHAPE_FIELDS.removesuffix("    from customers\n") + body
    _, semantic = _semantic_project(tmp_path, {"a.pietto": source})

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in build_project_completed_semantic_result(semantic).diagnostics
    ] == expected


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
                'from "missing.pietto" import (\n'
                "    type Missing as Local)\n"
                "shape Row:\n"
                "    value: Local\n"
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
                'from "b.pietto" import (\n'
                "    type Hidden as Local)\n"
                "shape Row:\n"
                "    value: Local\n"
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
                'from "b.pietto" import (\n'
                "    type B as Local)\n"
                "shape Row:\n"
                "    value: Local\n"
            ),
            "b.pietto": "type B = Int\nexport (\n    type B)\n",
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
        "type Email = Text\n"
        "enum Status:\n"
        "    active\n"
        "    inactive\n"
        "shape Customer:\n"
        "    id: UUID\n"
        'source customers: Customer = postgres.table("public.customers")\n'
        "table CustomerTable:\n"
        "    from customers\n"
        "    select:\n"
        "        id\n"
        "query CustomerQuery:\n"
        "    from CustomerTable\n"
        "    select:\n"
        "        id\n"
        "export (\n"
        "    type Email,\n"
        "    enum Status,\n"
        "    shape Customer,\n"
        "    source customers,\n"
        "    table CustomerTable,\n"
        "    query CustomerQuery)\n"
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
            'source X: LocalRow = postgres.table("local")\n'
        ),
    }

    for import_kind, exported_name in import_targets:
        for local_kind, local_source in local_candidates.items():
            _, semantic = _semantic_project(
                tmp_path / f"{import_kind}-{local_kind}",
                {
                    "a.pietto": (
                        local_source
                        + f'from "library.pietto" import {import_kind} {exported_name} as X\n'
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
                'from "b.pietto" import (\n    shape Shared)\nshape Row:\n    value: Shared\n'
            ),
            "b.pietto": (
                "shape Shared:\n"
                "    id: Int\n"
                "export (\n"
                "    shape Shared,\n"
                "    shape Shared)\n"
            ),
        },
    )
    assert [item.code for item in duplicate.diagnostics] == ["PIE-S2704"]

    _, inconsistent = _semantic_project(
        tmp_path / "inconsistent",
        {
            "a.pietto": (
                'from "b.pietto" import (\n    shape Shared)\nshape Row:\n    value: Shared\n'
            ),
            "b.pietto": (
                "query Shared:\n"
                "    from missing\n"
                "    select:\n"
                "        id\n"
                "export (\n"
                "    query Shared)\n"
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
                'shape Row:\n    id: Int\nsource rows: Row = postgres.table("rows")\n'
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
                'from "b.pietto" import (\n'
                "    shape Row as RemoteRow,\n"
                "    source rows as remote_rows)\n"
                'source local_rows: RemoteRow = postgres.table("local")\n'
            ),
            "b.pietto": (
                "shape Row:\n"
                "    id: UUID\n"
                'source rows: Row = postgres.table("rows")\n'
                "export (\n"
                "    shape Row,\n"
                "    source rows)\n"
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
                "enum Status:\n"
                "    ACTIVE\n"
                'source missing: Missing = postgres.table("missing")\n'
                'source alias_rows: Alias = postgres.table("alias")\n'
                'source status_rows: Status = postgres.table("status")\n'
                'source int_rows: Int = postgres.table("ints")\n'
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
                'from "b.pietto" import (\n'
                "    type Shared)\n"
                "constraint accepts(value: Shared) -> Bool:\n"
                "    return True\n"
                "table deferred:\n"
                "    from missing\n"
                "    select:\n"
                "        value\n"
            ),
            "b.pietto": "type Shared = Text\nexport (\n    type Shared)\n",
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


def test_text_json_cli_remains_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(
        tmp_path,
        {
            "a.pietto": (
                'from "missing.pietto" import (\n'
                "    type Missing as Blocked)\n"
                "shape Bad:\n"
                "    value: Unknown\n"
                'source rows: MissingShape = postgres.table("rows")\n'
            )
        },
    )
    assert cli.main(["check", "--project", str(root)]) == 1
    text_result = capsys.readouterr()
    assert text_result.out == ""
    codes = ("PIE-S2701", "PIE-S2002", "PIE-S2303", "PIE-S2333")
    assert [text_result.err.index(code) for code in codes] == sorted(
        text_result.err.index(code) for code in codes
    )
    assert "Project relation semantic completion is unavailable: rows" in (
        text_result.err
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
        "PIE-S2333",
    ]
    assert "module_type_source_resolutions" not in json.dumps(document)


def test_relationship_predicate_shapes_follow_declaring_modules_and_import_aliases(
    tmp_path: Path,
) -> None:
    from pietto._project.project_relationship_predicates import (
        ProjectRelationshipPredicateCatalog,
        declared_source_shape,
    )
    from pietto.ast_nodes import ShapeDef, SourceDef

    _, semantic = _semantic_project(
        tmp_path,
        {
            "shapes.pietto": ("shape Row:\n    id: Int\nexport shape Row\n"),
            "data.pietto": (
                'from "shapes.pietto" import shape Row as Declared\n'
                'source records: Declared = postgres.table("records")\n'
                "export source records\n"
            ),
            "main.pietto": (
                'from "shapes.pietto" import shape Row as Expected\n'
                'from "data.pietto" import source records as actual\n'
                "shape Row:\n    id: Text\n"
                "relationship Same(a: Expected, b: Expected):\n"
                "    a.id == b.id\n"
                "query result:\n    from actual\n    select actual.id\n"
            ),
        },
    )
    assert semantic.diagnostics == ()
    assert semantic.module_catalogs is not None
    data = semantic.module_catalogs.find_module_path("data.pietto")[0]
    source = next(
        item for item in data.occurrences if type(item.definition) is SourceDef
    )
    shape = declared_source_shape(semantic, source)
    catalog = ProjectRelationshipPredicateCatalog(semantic_result=semantic)
    (template,) = catalog.templates["main.pietto"]
    local = semantic.module_catalogs.find_module_path("main.pietto")[0]
    decoy = next(
        item.definition
        for item in local.occurrences
        if type(item.definition) is ShapeDef
    )

    assert catalog.diagnostics == ()
    assert shape is not None and shape is not decoy
    assert template.parameter_shapes[0] is template.parameter_shapes[1] is shape
    assert shape.span.path == "shapes.pietto"
    assert source.identity.module_path == "data.pietto"


def test_relationship_source_shape_rejects_an_equal_foreign_declaration(
    tmp_path: Path,
) -> None:
    from pietto._project.project_relationship_predicates import declared_source_shape
    from pietto.ast_nodes import SourceDef

    sources = {
        "main.pietto": (
            'shape Row:\n    id: Int\nsource records: Row = postgres.table("records")\n'
        )
    }
    _, local = _semantic_project(tmp_path / "local", sources)
    _, foreign = _semantic_project(tmp_path / "foreign", sources)
    assert foreign.module_catalogs is not None
    owner = next(
        item
        for item in foreign.module_catalogs.catalogs[0].occurrences
        if type(item.definition) is SourceDef
    )
    with pytest.raises(ValueError, match="exact declaration occurrence"):
        declared_source_shape(local, owner)


def test_project_predicate_local_owners_require_exact_retained_membership(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from pietto._project.project_relationship_predicates import (
        ProjectRelationshipPredicateCatalog,
        _bind_project_predicates,
        bind_project_no_join_relationship_predicates,
        declared_source_shape,
    )

    sources = {
        "main.pietto": """shape Row:
    id: Int
source records: Row = postgres.table("records")
relationship Positive(row: Row):
    row.id > 0
query output:
    let local:
        from records
        where Positive(records)
        select id
    let nested:
        from local
        select id
    from nested
    select id
"""
    }
    _, semantic = _semantic_project(tmp_path / "local", sources)
    _, foreign = _semantic_project(tmp_path / "foreign", sources)
    assert semantic.diagnostics == foreign.diagnostics == ()
    assert semantic.module_catalogs is not None
    assert foreign.module_catalogs is not None
    (module,) = semantic.module_catalogs.catalogs
    (foreign_module,) = foreign.module_catalogs.catalogs
    owners = (*module.lets, module.occurrences[-1])
    foreign_owners = (*foreign_module.lets, foreign_module.occurrences[-1])
    assert [owner.definition.name for owner in owners] == ["local", "nested", "output"]
    catalog = ProjectRelationshipPredicateCatalog(semantic_result=semantic)
    for owner, foreign_owner in zip(owners, foreign_owners, strict=True):
        records = bind_project_no_join_relationship_predicates(catalog, owner)
        assert records and all(record.owner is owner for record in records)
        assert sum(len(record.calls) for record in records) == (
            1 if owner.let_position == 0 else 0
        )
        assert declared_source_shape(semantic, owner) is None
        copied = replace(owner)
        assert copied == owner and copied is not owner
        assert foreign_owner.identity == owner.identity and foreign_owner is not owner
        for counterfeit in (copied, foreign_owner):
            with pytest.raises(ValueError, match="exact module catalog membership"):
                _bind_project_predicates(catalog, counterfeit, [])
            with pytest.raises(ValueError, match="exact declaration occurrence"):
                declared_source_shape(semantic, counterfeit)


def test_project_predicate_no_join_tail_reuses_one_exact_source_occurrence(
    tmp_path: Path,
) -> None:
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectConcreteNoJoinReplay,
        ProjectNoJoinScalarExpression,
    )
    from pietto.semantic.model import EffectiveNullability

    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n"
                "    id: Int\n"
                "    active: Bool | None\n"
                'source records: Row = postgres.table("records")\n'
                "relationship Same(a: Row, b: Row):\n"
                "    a.id == b.id and a.active\n"
                "query output:\n"
                "    let row = records\n"
                "    from row\n"
                "    where Same(row, row) or not Same(row, row)\n"
                "    select outcome = not Same(row, row)\n"
            )
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    entry = next(
        item
        for item in completed.roots.effective_outputs.entries
        if item.owner.definition.name == "output"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    assert isinstance(entry.root, ProjectConcreteNoJoinReplay)
    assert len(entry.root.predicate_expressions) == 2
    assert [len(record.calls) for record in entry.root.predicate_expressions] == [2, 1]
    for record in entry.root.predicate_expressions:
        for call, arguments in zip(record.calls, record.argument_bindings, strict=True):
            assert arguments[0] is arguments[1]
            assert call.arguments[0].occurrence is call.arguments[1].occurrence
            assert call.mandatory_equalities == ()
    value = entry.fields[0].source
    assert isinstance(value, ProjectNoJoinScalarExpression)
    assert value.expression is not value.normalized_expression
    assert value.predicate_expression is entry.root.predicate_expressions[1]
    assert value.value_type is not None
    assert value.value_type.resolved_type.name == "Bool"
    # The existing Bool operator kernel conservatively retains UNKNOWN.
    assert value.value_type.nullability is EffectiveNullability.UNKNOWN
    from pietto.ast_nodes import DottedNameExpr

    active_reads = tuple(
        value_type
        for expression, value_type in value.value_types.items()
        if isinstance(expression, DottedNameExpr)
        and expression.parts == ("row", "active")
    )
    assert active_reads
    assert all(
        item.nullability is EffectiveNullability.NULLABLE for item in active_reads
    )

    from pietto._project.row_expression_type_facts import scalar_field_reference_leaves

    (references,) = tuple(
        item for item in completed.roots.row_references if item.entry is entry
    )
    where_analysis = entry.root.where.expression_analysis
    assert where_analysis is not None
    for actual, normalized in (
        (references.selections[0], value.normalized_expression),
        (references.where, where_analysis.normalized_expression),
    ):
        expected = scalar_field_reference_leaves(normalized)
        assert len(actual) == len(expected)
        assert all(
            reference.expression is leaf
            for reference, leaf in zip(actual, expected, strict=True)
        )
        assert all(reference.status.value == "concrete" for reference in actual)
        assert all(
            reference.input_field
            is entry.root.input_schema.fields[reference.local_name]
            for reference in actual
        )


def test_project_imported_source_aliases_bind_distinct_predicate_inputs(
    tmp_path: Path,
) -> None:
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
    from pietto._project.project_scalar_namespaces import (
        ProjectConcreteJoinedNamespaceExpression,
    )

    _, semantic = _semantic_project(
        tmp_path,
        {
            "data.pietto": (
                "shape Row:\n    id: Int\n"
                'source records: Row = postgres.table("records")\n'
                "export shape Row, source records\n"
            ),
            "main.pietto": (
                'from "data.pietto" import shape Row as Expected, source records as actual\n'
                "relationship Same(a: Expected, b: Expected):\n"
                "    a.id == b.id\n"
                "query output:\n"
                "    let one = actual\n"
                "    let other = actual\n"
                "    from one\n"
                "    inner join other on Same(one, other)\n"
                "    where not Same(one, other) or Same(other, one)\n"
                "    select matched = not Same(one, other)\n"
            ),
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    assert [binding.name for binding in condition.ledger.bindings] == ["one", "other"]
    assert condition.ledger.bindings[0].target is not None
    assert condition.ledger.bindings[1].target is not None
    assert (
        condition.ledger.bindings[0].target.target_occurrence
        is condition.ledger.bindings[1].target.target_occurrence
    )
    record = condition.environment.predicate_expression
    assert record is not None
    assert record.argument_bindings[0][0] is not record.argument_bindings[0][1]
    entry = next(
        item
        for item in completed.roots.effective_outputs.entries
        if item.owner.definition.name == "output"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    value = entry.fields[0].source
    assert isinstance(value, ProjectConcreteJoinedNamespaceExpression)
    assert value.predicate_expression is not None
    assert value.normalized_expression is value.predicate_expression.expression
    assert value.value_type.resolved_type.name == "Bool"


@pytest.mark.parametrize(
    ("body", "supported"),
    (("a.active and b.active", True), ("a.id == b.id and a.active", False)),
    ids=("admitted_bool_fields", "comparison_keeps_existing_refusal"),
)
def test_project_predicate_boolean_argument_keeps_existing_count_semantics(
    tmp_path: Path,
    body: str,
    supported: bool,
) -> None:
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectConcreteNoJoinReplay,
    )

    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n    active: Bool | None\n"
                'source rows: Row = postgres.table("rows")\n'
                "relationship Same(a: Row, b: Row):\n"
                f"    {body}\n"
                "query output:\n    from rows\n"
                "    select total = count(Same(rows, rows))\n"
            )
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    if not supported:
        assert not completed.ok
        assert any(item.code == "PIE-S2333" for item in completed.diagnostics)
        _, expanded = _semantic_project(
            tmp_path / "expanded",
            {
                "main.pietto": (
                    "shape Row:\n    id: Int\n    active: Bool | None\n"
                    'source rows: Row = postgres.table("rows")\n'
                    "query output:\n    from rows\n"
                    "    select total = count(rows.id == rows.id and rows.active)\n"
                )
            },
        )
        expanded_result = build_project_completed_semantic_result(expanded)
        assert isinstance(expanded_result, ProjectConcreteCompletedSemanticResult)
        assert not expanded_result.ok
        return
    assert completed.ok, completed.diagnostics
    entry = next(
        item
        for item in completed.roots.effective_outputs.entries
        if item.owner.definition.name == "output"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    assert isinstance(entry.root, ProjectConcreteNoJoinReplay)
    assert entry.root.aggregate_readiness is not None
    (analysis,) = entry.root.aggregate_readiness.finalization.analyses
    assert analysis.predicate_expression is not None
    assert analysis.effective_argument is analysis.predicate_expression.expression
    assert entry.fields[0].field.resolved_type.name == "Int"
    assert entry.fields[0].field.nullability.value == "non_null"
    assert analysis.predicate_expression.calls[0].mandatory_equalities == ()

    from pietto._project.row_expression_type_facts import scalar_field_reference_leaves

    assert analysis.effective_argument is not None
    (references,) = tuple(
        item for item in completed.roots.row_references if item.entry is entry
    )
    expected = scalar_field_reference_leaves(analysis.effective_argument)
    assert len(references.selections[0]) == len(expected)
    assert all(
        reference.expression is leaf
        for reference, leaf in zip(references.selections[0], expected, strict=True)
    )


def test_project_retains_scalar_candidates_for_ambiguous_row_predicate_calls(
    tmp_path: Path,
) -> None:
    parsed, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n    rows: Int\n"
                'source rows: Row = postgres.table("rows")\n'
                "def Same(a: Int, b: Int) -> Bool: return a == b\n"
                "relationship Same(a: Row, b: Row):\n    a.id == b.id\n"
                "query output:\n    from rows\n"
                "    where Same(rows, rows)\n"
                "    select rows.id\n"
            )
        },
    )
    (original,) = parsed.parsed_inputs[0].scalar_callables
    assert original.name == "Same"
    completed = build_project_completed_semantic_result(semantic)
    assert not completed.ok
    assert (
        "PIE-S2604",
        "Ambiguous scalar or relationship call: Same",
        10,
        11,
    ) in [
        (item.code, item.message, item.location.line, item.location.column)
        for item in completed.diagnostics
    ]


def test_project_body_views_preserve_names_and_require_normalization() -> None:
    from dataclasses import dataclass, replace

    from pietto._project.module_catalog import _relation_block_view
    from pietto._project.module_relation_resolution import _expression_read_containers
    from pietto._project.query_parameters import _header_bodies
    from pietto.ast_nodes import (
        BlockRelationDef,
        Expression,
        ModuleDeclarationKind,
        QueryDef,
        SelectBody,
    )

    parsed = parse_source(
        "query output(n: Int):\n"
        "    let local = rows\n"
        "    from local\n"
        "    select local.id\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = parsed.ast.definitions[0]
    assert isinstance(query, QueryDef)
    assert query.naming_declarations
    body = SelectBody(
        span=query.span,
        from_clause=query.from_clause,
        where_clause=query.where_clause,
        group_by_clause=query.group_by_clause,
        select_items=query.select_items,
        naming_declarations=query.naming_declarations,
    )
    block = BlockRelationDef(
        span=query.span,
        name=query.name,
        kind=ModuleDeclarationKind.QUERY,
        parameters=query.parameters,
        let_relations=(),
        body=body,
    )
    view = _relation_block_view(
        span=block.span,
        name=block.name,
        kind=block.kind,
        body=body,
        parameters=block.parameters,
    )
    assert isinstance(view, QueryDef)
    (header_view,) = _header_bodies(block)
    assert view.naming_declarations is body.naming_declarations
    assert header_view.naming_declarations is body.naming_declarations
    with pytest.raises(ValueError, match="normalized query naming declarations"):
        _expression_read_containers(view)
    normalized = replace(view, naming_declarations=())
    containers = _expression_read_containers(normalized)
    assert [node for _, _, node in containers] == [
        query.from_clause,
        *query.select_items,
    ]

    @dataclass(frozen=True, slots=True, kw_only=True)
    class FutureQuery(QueryDef):
        unhandled_expression: Expression | None = None

    future = FutureQuery(
        **{item.name: getattr(normalized, item.name) for item in fields(normalized)}
    )
    with pytest.raises(ValueError, match="closed relation body shape"):
        _expression_read_containers(future)


@pytest.mark.parametrize("kind", ("right", "full"))
@pytest.mark.parametrize("negative", (False, True))
def test_project_any_filter_retains_its_prefix_before_outer_join(
    tmp_path: Path,
    kind: str,
    negative: bool,
) -> None:
    from pietto.ast_nodes import AuthoredJoinKind, JoinFilterClause

    parsed, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n"
                'source orders: Row = postgres.table("orders")\n'
                'source customers: Row = postgres.table("customers")\n'
                'source regions: Row = postgres.table("regions")\n'
                "relationship Same(a: Row, b: Row):\n    a.id == b.id\n"
                "query output:\n    from orders\n"
                f"    where {'not ' if negative else ''}any(Same(orders, buyer) for buyer in customers)\n"
                f"    {kind} join regions on orders.id == regions.id\n"
                "    select order_id = orders.id, region_id = regions.id\n"
            )
        },
    )
    (use,) = parsed.parsed_inputs[0].existence_generators
    assert isinstance(use.context, JoinFilterClause)
    assert use.preceding_join_count == 0 and use.input_ordinal == 1
    assert use.owner.join_clauses[0] is use.clause
    assert use.clause.kind is (
        AuthoredJoinKind.ANTI if negative else AuthoredJoinKind.SEMI
    )
    assert use.owner.join_filters == ()
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    conditions = completed.roots.join_conditions.entries
    assert [item.use.clause.kind for item in conditions] == [
        use.clause.kind,
        AuthoredJoinKind(kind),
    ]
    assert conditions[1].inputs is not None
    assert conditions[1].inputs.prefix[0].use.clause is use.clause


def test_project_any_binder_reuse_stays_local_across_import_aliases(
    tmp_path: Path,
) -> None:
    from pietto.ast_nodes import AuthoredJoinKind

    parsed, semantic = _semantic_project(
        tmp_path,
        {
            "data.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row = postgres.table("rows")\n'
                "export shape Row, source rows\n"
            ),
            "main.pietto": (
                'from "data.pietto" import shape Row, source rows as imported\n'
                "relationship Same(a: Row, b: Row):\n    a.id == b.id\n"
                "query output:\n"
                "    let buyer = imported\n"
                "    from imported\n"
                "    where any(Same(imported, buyer) for buyer in imported)\n"
                "    inner join buyer on imported.id == buyer.id\n"
                "    where not any(Same(imported, buyer) for buyer in imported)\n"
                "    select id = buyer.id\n"
            ),
        },
    )
    module = next(
        source for source in parsed.parsed_inputs if source.path == "main.pietto"
    )
    (first,) = module.existence_generators
    (last,) = module.existence_values
    assert first.expression.binding_name == last.expression.binding_name == "buyer"
    assert first.expression is not last.expression
    assert first.clause.target_binding_name != "buyer"
    assert first.owner is last.owner
    assert [join.kind for join in first.owner.join_clauses] == [
        AuthoredJoinKind.SEMI,
        AuthoredJoinKind.INNER,
    ]
    assert first.owner.join_clauses[1].target_binding_name == "buyer"
    assert first.owner.join_clauses[1].target_relation_name == "imported"
    assert first.input_ordinal == 1 and first.preceding_join_count == 0
    assert last.join_prefix_count == 2
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    assert all(condition.ready for condition in completed.roots.join_conditions.entries)


def test_project_float_constructor_scope_stays_local_to_its_module(
    tmp_path: Path,
) -> None:
    from pietto.ast_nodes import CastExpr, QueryDef
    from pietto._project.project_completion import ProjectExistingEffectiveOutput
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        _entry_schema,
    )

    parsed, semantic = _semantic_project(
        tmp_path,
        {
            "defs.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row = postgres.table("rows")\n'
                "def Float(x: Int) -> Int: return x\n"
                "query local:\n    from rows\n    select value = Float(1)\n"
                "export shape Row, source rows\n"
            ),
            "main.pietto": (
                'from "defs.pietto" import source rows\n'
                "query output:\n    from rows\n    select value = Float(1)\n"
            ),
        },
    )
    first, second = parsed.parsed_inputs
    assert first.scalar_callables[0].name == "Float"
    local = next(
        item for item in first.script.definitions if isinstance(item, QueryDef)
    )
    output = next(
        item for item in second.script.definitions if isinstance(item, QueryDef)
    )
    assert not isinstance(local.select_items[0].expression, CastExpr)
    assert isinstance(output.select_items[0].expression, CastExpr)
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    schemas = {
        entry.owner.definition.name: entry
        for entry in completed.roots.effective_outputs.entries
        if entry.owner.definition.name in {"local", "output"}
    }
    local_fields = _environment(semantic, "defs.pietto")
    assert local_fields.module.parsed_input is first
    assert set(schemas) == {"local", "output"}
    for name, expected in (("local", "Int"), ("output", "Float")):
        entry = schemas[name]
        assert isinstance(
            entry, (ProjectExistingEffectiveOutput, ProjectCompletedEffectiveOutput)
        )
        assert _entry_schema(entry).fields["value"].resolved_type.name == expected


def test_project_relationship_float_body_and_call_copies_use_imported_rows(
    tmp_path: Path,
) -> None:
    from pietto.ast_nodes import CastExpr, ComparisonExpr

    _, semantic = _semantic_project(
        tmp_path,
        {
            "data.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row = postgres.table("rows")\n'
                "export shape Row, source rows\n"
            ),
            "main.pietto": (
                'from "data.pietto" import shape Row, source rows\n'
                "relationship EqualFloat(a: Row, b: Row):\n"
                "    Float(a.id) == Float(b.id)\n"
                "query output:\n    let peer = rows\n    from rows\n"
                "    inner join peer on EqualFloat(rows, peer)\n"
                "    select id = rows.id\n"
            ),
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    record = condition.environment.predicate_expression
    assert record is not None
    (call,) = record.calls
    template = call.template.declaration.body
    expanded = condition.expression
    assert isinstance(template, ComparisonExpr) and isinstance(expanded, ComparisonExpr)
    for original, copied in (
        (template.left, expanded.left),
        (template.right, expanded.right),
    ):
        assert isinstance(original, CastExpr) and isinstance(copied, CastExpr)
        assert copied.target is not original.target
        assert copied.target.name == "Float"
        assert condition.value_types[copied].resolved_type.name == "Float"


def test_project_scalar_any_keeps_alias_origin_and_derived_iterator_dependency(
    tmp_path: Path,
) -> None:
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectNoJoinScalarExpression,
    )

    parsed, semantic = _semantic_project(
        tmp_path,
        {
            "data.pietto": (
                "shape Row:\n    id: Int\n"
                'source rows: Row = postgres.table("rows")\n'
                "export shape Row, source rows\n"
            ),
            "main.pietto": (
                'from "data.pietto" import source rows as orders\n'
                "query candidates:\n    from orders\n"
                "    where orders.id > 0\n    select id = orders.id\n"
                "query output:\n    let local_rows = candidates\n    from orders\n"
                "    where any(buyer.id == orders.id for buyer in local_rows) or orders.id > 5\n"
                "    select matched = any(buyer.id == orders.id for buyer in local_rows)\n"
            ),
        },
    )
    source = next(item for item in parsed.parsed_inputs if item.path == "main.pietto")
    assert len(source.existence_values) == 2
    assert all(
        value.authored_expression.relation_name == "local_rows"
        and value.expression.relation_name == "candidates"
        for value in source.existence_values
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    entry = next(
        item
        for item in completed.effective_outputs.entries
        if item.owner.definition.name == "output"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    analysis = entry.fields[0].source
    assert isinstance(analysis, ProjectNoJoinScalarExpression)
    (value,) = analysis.existence_values
    assert value.input.entry is not None
    assert value.input.entry.owner is value.input.binding.target
    assert value.input.binding.origin is source.existence_values[1]
    assert (
        value.input.binding.resolution.read.expression is value.input.binding.expression
    )
    assert value.authored_expression is source.existence_values[1].authored_expression
    schedule = completed.effective_outputs.schedule
    assert schedule.index(value.input.entry.owner) < schedule.index(entry.owner)


def test_project_unused_scalar_let_any_still_checks_its_predicate(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n"
                'source orders: Row = postgres.table("orders")\n'
                "query output:\n    from orders\n"
                "    let unused = any(buyer.missing == orders.id for buyer in orders)\n"
                "    select id = orders.id\n"
            )
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert not completed.ok
    assert any(
        diagnostic.code == "PIE-S2334"
        and "ANY predicate reference is unavailable" in diagnostic.message
        for diagnostic in completed.diagnostics
    )


def test_project_unused_function_parameter_rejects_any_argument_before_expansion(
    tmp_path: Path,
) -> None:
    root = _configured_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n"
                'source orders: Row = postgres.table("orders")\n'
                "def choose(value: Bool) -> Bool: return True\n"
                "query output:\n    from orders\n"
                "    select matched = choose(any(buyer.missing == orders.id for buyer in orders))\n"
            )
        },
    )
    parsed = project_check.check_project_parse_only(root)
    assert not parsed.ok
    assert any(
        diagnostic.code == "PIE-S2397"
        and "parameter value is not used" in diagnostic.message
        for diagnostic in parsed.diagnostics
    )


def test_project_scalar_any_none_predicate_has_bool_context(tmp_path: Path) -> None:
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectNoJoinScalarExpression,
    )
    from pietto.semantic.model import EffectiveNullability, ValueTypeKind

    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                "shape Row:\n    id: Int\n"
                'source orders: Row = postgres.table("orders")\n'
                "query output:\n    from orders\n"
                "    select matched = any(None for buyer in orders)\n"
            )
        },
    )
    completed = build_project_completed_semantic_result(semantic)
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok, completed.diagnostics
    entry = next(
        item
        for item in completed.effective_outputs.entries
        if item.owner.definition.name == "output"
    )
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    analysis = entry.fields[0].source
    assert isinstance(analysis, ProjectNoJoinScalarExpression)
    (value,) = analysis.existence_values
    predicate_type = value.value_types[value.predicate]
    assert predicate_type.kind is ValueTypeKind.KNOWN
    assert predicate_type.resolved_type.name == "Bool"
    assert predicate_type.nullability is EffectiveNullability.NULLABLE
    assert value.value_type.nullability is EffectiveNullability.NON_NULL
