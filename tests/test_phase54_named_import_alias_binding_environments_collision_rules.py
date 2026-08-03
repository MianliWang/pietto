from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
import os
from pathlib import Path
from types import MappingProxyType

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_product_repair1_gate2_is_active,
)

import pytest

import pietto
import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_bindings as module_bindings
import pietto._project.module_catalog as module_catalog
import pietto._project.module_exports as module_exports
import pietto.cli as cli
from _phase54_active_gate2_manifest import (
    PHASE54_ACTIVE_GATE2_ADDED_PATHS,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_ACTIVE_GATE2_DELETED_PATHS,
    PHASE54_ACTIVE_GATE2_MARKER,
    PHASE54_ACTIVE_GATE2_MODIFIED_PATHS,
    PHASE54_SLICE10_ORIGINAL_ADDED_PATHS,
    PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS,
    Phase54Gate2RepositoryState,
    _matches_phase54_active_gate2_manifest,
)
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectCompilationMode


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice7-named-imports-aliases-binding-environments-"
    "and-collision-rules-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_bindings.py"
TEST_REL = (
    "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py"
)

EXPECTED_TEST_NAMES = (
    "test_binding_carrier_enums_fields_privacy_and_manifest_are_locked",
    "test_binding_carrier_constructors_reject_wrong_types_and_identity_rewrites",
    "test_modules_without_imports_build_empty_ordered_environments",
    "test_exact_six_named_import_kinds_resolve_from_direct_facade",
    "test_unaliased_import_uses_exported_name_for_local_identity",
    "test_alias_changes_only_local_binding_name_and_preserves_target_identity",
    "test_target_resolution_preserves_exact_path_case_and_unicode",
    "test_unselected_target_fails_closed_without_filesystem_discovery",
    "test_unknown_exported_name_retains_issue_without_winner",
    "test_private_or_unexported_declaration_is_not_importable",
    "test_namespace_or_kind_disagreement_retains_inconsistent_facade_issue",
    "test_ambiguous_target_facade_retains_all_entries_without_winner",
    "test_local_declaration_and_import_collision_has_no_winner",
    "test_repeated_local_binding_name_has_no_first_or_last_winner",
    "test_distinct_exported_names_aliased_to_same_local_name_collide",
    "test_exact_duplicate_requests_remain_distinct_with_prior_evidence",
    "test_import_order_changes_evidence_order_not_collision_meaning",
    "test_environment_set_preserves_selected_input_and_source_order",
    "test_environment_values_lookups_and_collections_are_immutable",
    "test_resolved_binding_keeps_separate_local_and_nominal_identities",
    "test_direct_explicit_reexport_entry_is_importable_without_identity_rewrite",
    "test_single_backfill_does_not_recurse_or_build_facade_fixed_point",
    "test_slice6_candidate_proof_positions_and_alias_span_are_exact",
    "test_matching_export_request_consumes_real_candidate_for_reexport",
    "test_schema_v2_semantic_result_retains_private_bindings_and_fail_closed_posture",
    "test_schema_v2_text_and_json_remain_exact_and_private",
    "test_schema_v1_semantics_json_and_binding_absence_remain_exact",
    "test_builder_uses_only_preloaded_inputs_and_performs_no_io",
    "test_no_public_diagnostics_graph_ir_sql_or_serialized_binding_surface",
    "test_slice7_contract_test_inventory_and_active_gate_manifest_are_exact",
)

SIX_KIND_SOURCE = (
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
)
SIX_KIND_EXPORTS = (
    "export:\n"
    "    type Email\n"
    "    enum Status\n"
    "    shape Customer\n"
    "    source customers\n"
    "    table CustomerTable\n"
    "    query CustomerQuery\n"
)
SIX_KIND_IMPORTS = (
    'import "library.pietto":\n'
    "    type Email\n"
    "    enum Status\n"
    "    shape Customer\n"
    "    source customers\n"
    "    table CustomerTable\n"
    "    query CustomerQuery\n"
)


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True)
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
    project_root = _configured_project(
        root,
        sources,
        schema_version=schema_version,
    )
    parse_result = project_check.check_project_parse_only(project_root)
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
    return parse_result, semantic


def _required_bindings(
    semantic: ProjectSemanticResult,
) -> module_bindings.ProjectModuleBindingEnvironmentSet:
    assert semantic.module_bindings is not None
    return semantic.module_bindings


def _environment(
    semantic: ProjectSemanticResult,
    path: str,
) -> module_bindings.ProjectModuleBindingEnvironment:
    matches = _required_bindings(semantic).find_module_path(path)
    assert len(matches) == 1
    return matches[0]


def _simple_semantic(
    tmp_path: Path,
    main_source: str,
    *,
    library_source: str = SIX_KIND_SOURCE + SIX_KIND_EXPORTS,
) -> ProjectSemanticResult:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "library.pietto": library_source,
            "main.pietto": main_source,
        },
    )
    return semantic


def _active_state() -> Phase54Gate2RepositoryState:
    return Phase54Gate2RepositoryState(
        marker=PHASE54_ACTIVE_GATE2_MARKER,
        branch_oid=PHASE54_ACTIVE_GATE2_BASE,
        branch_head="main",
        branch_upstream="origin/main",
        ahead=0,
        behind=0,
        added_paths=PHASE54_SLICE10_ORIGINAL_ADDED_PATHS,
        modified_paths=PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS,
        deleted_paths=PHASE54_ACTIVE_GATE2_DELETED_PATHS,
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )


def test_binding_carrier_enums_fields_privacy_and_manifest_are_locked() -> None:
    assert module_bindings.__all__ == ()
    assert tuple(module_bindings.ProjectModuleBindingIssueStatus) == (
        module_bindings.ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE,
        module_bindings.ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME,
        module_bindings.ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION,
        module_bindings.ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE,
        module_bindings.ProjectModuleBindingIssueStatus.AMBIGUOUS_TARGET_FACADE,
        module_bindings.ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION,
        module_bindings.ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
        module_bindings.ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST,
    )
    expected_fields = {
        module_bindings.ProjectImportedBindingIdentity: (
            "owning_module_path",
            "namespace",
            "declaration_kind",
            "local_binding_name",
        ),
        module_bindings.ProjectModuleImportRequest: (
            "identity",
            "target_module_path",
            "exported_name",
            "module_statement_position",
            "item_position",
            "source_statement",
            "source_item",
        ),
        module_bindings.ProjectResolvedImportedBinding: (
            "identity",
            "target_module_path",
            "target_identity",
            "request",
            "resolved_entry",
        ),
        module_bindings.ProjectModuleBindingIssue: (
            "status",
            "request",
            "target_surfaces",
            "target_entries",
            "target_occurrences",
            "local_occurrences",
            "competing_requests",
            "prior_requests",
        ),
        module_bindings.ProjectModuleBindingEnvironment: (
            "module",
            "requests",
            "bindings",
            "issues",
            "_bindings_by_identity",
        ),
        module_bindings.ProjectModuleBindingEnvironmentSet: (
            "environments",
            "imported_export_candidates",
            "_environments_by_path",
        ),
    }
    for carrier, names in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(field.name for field in fields(carrier)) == names
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in getattr(carrier, "__slots__")


def test_binding_carrier_constructors_reject_wrong_types_and_identity_rewrites(
    tmp_path: Path,
) -> None:
    semantic = _simple_semantic(tmp_path, SIX_KIND_IMPORTS)
    environment = _environment(semantic, "main.pietto")
    binding = environment.bindings[0]
    with pytest.raises(ValueError):
        module_bindings.ProjectImportedBindingIdentity(
            owning_module_path="main.pietto",
            namespace=ProjectSymbolNamespace.CALLABLE,
            declaration_kind=ProjectSymbolKind.CONSTRAINT,
            local_binding_name="bad",
        )
    with pytest.raises(ValueError, match="exact identities"):
        replace(binding, target_module_path="main.pietto")
    with pytest.raises(ValueError, match="resolution outcome"):
        replace(environment, bindings=(), issues=())
    with pytest.raises(ValueError, match="exact Slice 6 candidates"):
        replace(_required_bindings(semantic), imported_export_candidates=())

    def resolved_binding(
        semantic_result: ProjectSemanticResult,
        request: module_bindings.ProjectModuleImportRequest,
    ) -> module_bindings.ProjectResolvedImportedBinding:
        assert semantic_result.module_exports is not None
        target_surface = semantic_result.module_exports.find_module_path(
            request.target_module_path
        )[0]
        target_entry = next(
            entry
            for entry in target_surface.entries
            if entry.exposed_name == request.exported_name
            and entry.namespace is request.identity.namespace
            and entry.declaration_kind is request.identity.declaration_kind
        )
        return module_bindings.ProjectResolvedImportedBinding(
            identity=request.identity,
            target_module_path=request.target_module_path,
            target_identity=target_entry.target_identity,
            request=request,
            resolved_entry=target_entry,
        )

    local_collision_semantic = _simple_semantic(
        tmp_path / "local-collision",
        (
            "shape Local:\n"
            "    id: Int\n"
            "shape Other:\n"
            "    id: Int\n"
            'import "library.pietto":\n'
            "    shape Customer as Local\n"
        ),
    )
    local_collision = _environment(local_collision_semantic, "main.pietto")
    forged_local_winner = resolved_binding(
        local_collision_semantic,
        local_collision.requests[0],
    )
    with pytest.raises(ValueError, match="collision"):
        replace(local_collision, bindings=(forged_local_winner,), issues=())

    assert local_collision_semantic.module_catalogs is not None
    owner_catalog = local_collision_semantic.module_catalogs.find_module_path(
        "main.pietto"
    )[0]
    other_occurrence = next(
        occurrence
        for occurrence in owner_catalog.occurrences
        if occurrence.identity.declared_name == "Other"
    )
    local_issue = local_collision.issues[0]
    with pytest.raises(ValueError, match="importing binding"):
        replace(local_issue, local_occurrences=(other_occurrence,))
    assert local_collision_semantic.module_exports is not None
    library_surface = local_collision_semantic.module_exports.find_module_path(
        "library.pietto"
    )[0]
    with pytest.raises(ValueError, match="prove its status"):
        replace(local_issue, target_surfaces=(library_surface,))

    import_collision_semantic = _simple_semantic(
        tmp_path / "import-collision",
        (
            'import "library.pietto":\n'
            "    shape Customer as Shared\n"
            "    type Email as Shared\n"
        ),
    )
    import_collision = _environment(import_collision_semantic, "main.pietto")
    forged_import_winner = resolved_binding(
        import_collision_semantic,
        import_collision.requests[0],
    )
    second_request_issues = tuple(
        issue
        for issue in import_collision.issues
        if issue.request == import_collision.requests[1]
    )
    with pytest.raises(ValueError, match="collisions require exact evidence"):
        replace(
            import_collision,
            bindings=(forged_import_winner,),
            issues=second_request_issues,
        )


def test_modules_without_imports_build_empty_ordered_environments(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "a.pietto": "shape A:\n    id: Int\n",
            "b.pietto": "shape B:\n    id: Int\n",
        },
    )
    environments = _required_bindings(semantic).environments
    assert tuple(item.module.path for item in environments) == (
        "a.pietto",
        "b.pietto",
    )
    assert all(
        item.requests == item.bindings == item.issues == () for item in environments
    )


def test_exact_six_named_import_kinds_resolve_from_direct_facade(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(tmp_path, SIX_KIND_IMPORTS),
        "main.pietto",
    )
    assert len(environment.requests) == 6
    assert len(environment.bindings) == 6
    assert environment.issues == ()
    assert tuple(
        binding.identity.declaration_kind for binding in environment.bindings
    ) == (
        ProjectSymbolKind.TYPE_ALIAS,
        ProjectSymbolKind.ENUM,
        ProjectSymbolKind.SHAPE,
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    )


def test_unaliased_import_uses_exported_name_for_local_identity(
    tmp_path: Path,
) -> None:
    binding = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Customer\n',
        ),
        "main.pietto",
    ).bindings[0]
    assert binding.request.source_item.local_name is None
    assert binding.identity.local_binding_name == "Customer"
    assert binding.target_identity.declared_name == "Customer"


def test_alias_changes_only_local_binding_name_and_preserves_target_identity(
    tmp_path: Path,
) -> None:
    binding = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Customer as Buyer\n',
        ),
        "main.pietto",
    ).bindings[0]
    assert binding.identity.local_binding_name == "Buyer"
    assert binding.identity.owning_module_path == "main.pietto"
    assert binding.target_identity == module_catalog.ProjectNominalDeclarationIdentity(
        module_path="library.pietto",
        namespace=ProjectSymbolNamespace.TYPE,
        declaration_kind=ProjectSymbolKind.SHAPE,
        declared_name="Customer",
    )


def test_target_resolution_preserves_exact_path_case_and_unicode(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "Mód.pietto": "shape Row:\n    id: Int\nexport:\n    shape Row\n",
            "main.pietto": (
                'import "Mód.pietto":\n'
                "    shape Row as Exact\n"
                'import "mód.pietto":\n'
                "    shape Row as Folded\n"
            ),
        },
    )
    environment = _environment(semantic, "main.pietto")
    assert tuple(
        binding.identity.local_binding_name for binding in environment.bindings
    ) == ("Exact",)
    assert environment.bindings[0].target_module_path == "Mód.pietto"
    assert environment.issues[0].status is (
        module_bindings.ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE
    )


def test_unselected_target_fails_closed_without_filesystem_discovery(
    tmp_path: Path,
) -> None:
    raw_targets = (
        "missing.pietto",
        "../outside/../shared.pietto",
        "https://example.invalid/module.pietto",
        "missing/./module.pietto",
        "",
    )
    for position, raw_target in enumerate(raw_targets):
        semantic = _simple_semantic(
            tmp_path / f"target-{position}",
            f'import "{raw_target}":\n    shape Customer\n',
        )
        environment = _environment(semantic, "main.pietto")
        assert environment.bindings == ()
        assert environment.requests[0].target_module_path == raw_target
        assert tuple(issue.status for issue in environment.issues) == (
            module_bindings.ProjectModuleBindingIssueStatus.UNRESOLVED_TARGET_MODULE,
        )


def test_unknown_exported_name_retains_issue_without_winner(tmp_path: Path) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Missing\n',
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    issue = environment.issues[0]
    assert (
        issue.status
        is module_bindings.ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME
    )
    assert len(issue.target_surfaces) == 1
    assert issue.target_entries == issue.target_occurrences == ()


def test_private_or_unexported_declaration_is_not_importable(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Customer\n',
            library_source=SIX_KIND_SOURCE,
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    issue = environment.issues[0]
    assert issue.status is (
        module_bindings.ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION
    )
    assert tuple(item.identity.declared_name for item in issue.target_occurrences) == (
        "Customer",
    )


def test_namespace_or_kind_disagreement_retains_inconsistent_facade_issue(
    tmp_path: Path,
) -> None:
    library = (
        "shape Shared:\n"
        "    id: Int\n"
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("public.rows")\n'
        "query Shared:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "export:\n"
        "    query Shared\n"
    )
    environment = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Shared\n',
            library_source=library,
        ),
        "main.pietto",
    )
    issue = environment.issues[0]
    assert issue.status is (
        module_bindings.ProjectModuleBindingIssueStatus.INCONSISTENT_TARGET_FACADE
    )
    assert tuple(entry.declaration_kind for entry in issue.target_entries) == (
        ProjectSymbolKind.QUERY,
    )
    assert tuple(
        occurrence.identity.declaration_kind for occurrence in issue.target_occurrences
    ) == (ProjectSymbolKind.SHAPE, ProjectSymbolKind.QUERY)
    exact_private_occurrence = issue.target_occurrences[0]
    with pytest.raises(ValueError, match="prove its status"):
        module_bindings.ProjectModuleBindingIssue(
            status=(
                module_bindings.ProjectModuleBindingIssueStatus.PRIVATE_OR_UNEXPORTED_DECLARATION
            ),
            request=issue.request,
            target_surfaces=issue.target_surfaces,
            target_occurrences=(exact_private_occurrence,),
        )


def test_ambiguous_target_facade_retains_all_entries_without_winner(
    tmp_path: Path,
) -> None:
    library = (
        "shape Shared:\n    id: Int\nexport:\n    shape Shared\n    shape Shared\n"
    )
    environment = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Shared\n',
            library_source=library,
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    issue = environment.issues[0]
    assert issue.status is (
        module_bindings.ProjectModuleBindingIssueStatus.AMBIGUOUS_TARGET_FACADE
    )
    assert len(issue.target_entries) == 2


def test_local_declaration_and_import_collision_has_no_winner(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            (
                "shape Local:\n"
                "    id: Int\n"
                'import "library.pietto":\n'
                "    shape Customer as Local\n"
            ),
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    issue = environment.issues[0]
    assert issue.status is (
        module_bindings.ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION
    )
    assert tuple(item.identity.declared_name for item in issue.local_occurrences) == (
        "Local",
    )


def test_repeated_local_binding_name_has_no_first_or_last_winner(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            (
                'import "library.pietto":\n'
                "    shape Customer as Shared\n"
                "    type Email as Shared\n"
            ),
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    assert tuple(issue.status for issue in environment.issues) == (
        module_bindings.ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
        module_bindings.ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
    )
    assert all(len(issue.competing_requests) == 1 for issue in environment.issues)


def test_distinct_exported_names_aliased_to_same_local_name_collide(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            (
                'import "library.pietto":\n'
                "    shape Customer as Shared\n"
                "    enum Status as Shared\n"
            ),
        ),
        "main.pietto",
    )
    assert environment.bindings == ()
    assert {request.exported_name for request in environment.requests} == {
        "Customer",
        "Status",
    }
    assert all(
        issue.status
        is module_bindings.ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION
        for issue in environment.issues
    )


def test_exact_duplicate_requests_remain_distinct_with_prior_evidence(
    tmp_path: Path,
) -> None:
    environment = _environment(
        _simple_semantic(
            tmp_path,
            (
                'import "library.pietto":\n'
                "    shape Customer as Shared\n"
                "    shape Customer as Shared\n"
            ),
        ),
        "main.pietto",
    )
    assert len(environment.requests) == 2
    assert environment.requests[0] != environment.requests[1]
    duplicate = next(
        issue
        for issue in environment.issues
        if issue.status
        is module_bindings.ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST
    )
    assert duplicate.request is environment.requests[1]
    assert duplicate.prior_requests == (environment.requests[0],)
    assert environment.bindings == ()


def test_import_order_changes_evidence_order_not_collision_meaning(
    tmp_path: Path,
) -> None:
    first = _environment(
        _simple_semantic(
            tmp_path / "first",
            (
                'import "library.pietto":\n'
                "    shape Customer as Shared\n"
                "    enum Status as Shared\n"
            ),
        ),
        "main.pietto",
    )
    second = _environment(
        _simple_semantic(
            tmp_path / "second",
            (
                'import "library.pietto":\n'
                "    enum Status as Shared\n"
                "    shape Customer as Shared\n"
            ),
        ),
        "main.pietto",
    )
    assert first.bindings == second.bindings == ()
    assert sorted(issue.status for issue in first.issues) == sorted(
        issue.status for issue in second.issues
    )
    assert tuple(request.exported_name for request in first.requests) == (
        "Customer",
        "Status",
    )
    assert tuple(request.exported_name for request in second.requests) == (
        "Status",
        "Customer",
    )


def test_environment_set_preserves_selected_input_and_source_order(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "a-library.pietto": "shape A:\n    id: Int\nexport:\n    shape A\n",
            "b-library.pietto": "shape B:\n    id: Int\nexport:\n    shape B\n",
            "z-main.pietto": (
                'import "b-library.pietto":\n'
                "    shape B\n"
                'import "a-library.pietto":\n'
                "    shape A\n"
            ),
        },
    )
    environments = _required_bindings(semantic).environments
    assert tuple(item.module.path for item in environments) == (
        "a-library.pietto",
        "b-library.pietto",
        "z-main.pietto",
    )
    main = environments[-1]
    assert tuple(request.target_module_path for request in main.requests) == (
        "b-library.pietto",
        "a-library.pietto",
    )
    assert tuple(binding.identity.local_binding_name for binding in main.bindings) == (
        "B",
        "A",
    )


def test_environment_values_lookups_and_collections_are_immutable(
    tmp_path: Path,
) -> None:
    semantic = _simple_semantic(
        tmp_path,
        'import "library.pietto":\n    shape Customer\n',
    )
    environment_set = _required_bindings(semantic)
    environment = _environment(semantic, "main.pietto")
    binding = environment.bindings[0]
    assert type(environment_set.environments) is tuple
    assert type(environment.requests) is tuple
    assert type(environment.bindings) is tuple
    assert isinstance(environment._bindings_by_identity, MappingProxyType)
    assert isinstance(environment_set._environments_by_path, MappingProxyType)
    assert environment.find_identity(binding.identity) == (binding,)
    with pytest.raises(FrozenInstanceError):
        setattr(binding, "target_module_path", "other.pietto")
    with pytest.raises(TypeError):
        environment._bindings_by_identity[binding.identity] = ()  # type: ignore[index]


def test_resolved_binding_keeps_separate_local_and_nominal_identities(
    tmp_path: Path,
) -> None:
    binding = _environment(
        _simple_semantic(
            tmp_path,
            'import "library.pietto":\n    shape Customer as LocalCustomer\n',
        ),
        "main.pietto",
    ).bindings[0]
    assert binding.identity == module_bindings.ProjectImportedBindingIdentity(
        owning_module_path="main.pietto",
        namespace=ProjectSymbolNamespace.TYPE,
        declaration_kind=ProjectSymbolKind.SHAPE,
        local_binding_name="LocalCustomer",
    )
    assert binding.target_identity.module_path == "library.pietto"
    assert binding.target_identity.declared_name == "Customer"
    assert binding.identity != binding.target_identity


def test_direct_explicit_reexport_entry_is_importable_without_identity_rewrite(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "a-origin.pietto": (
                "shape Original:\n    id: Int\nexport:\n    shape Original\n"
            ),
            "b-middle.pietto": (
                'import "a-origin.pietto":\n'
                "    shape Original as Shared\n"
                "export:\n"
                "    shape Shared\n"
            ),
            "c-consumer.pietto": (
                'import "b-middle.pietto":\n    shape Shared as Local\n'
            ),
        },
    )
    binding = _environment(semantic, "c-consumer.pietto").bindings[0]
    assert binding.resolved_entry.origin is (
        module_exports.ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT
    )
    assert binding.target_identity.module_path == "a-origin.pietto"
    assert binding.target_identity.declared_name == "Original"
    assert binding.identity.local_binding_name == "Local"


def test_single_backfill_does_not_recurse_or_build_facade_fixed_point(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "a-origin.pietto": (
                "shape Original:\n    id: Int\nexport:\n    shape Original\n"
            ),
            "b-one.pietto": (
                'import "a-origin.pietto":\n'
                "    shape Original as One\n"
                "export:\n"
                "    shape One\n"
            ),
            "c-two.pietto": (
                'import "b-one.pietto":\n    shape One as Two\nexport:\n    shape Two\n'
            ),
            "d-consumer.pietto": ('import "c-two.pietto":\n    shape Two as Final\n'),
        },
    )
    assert len(_environment(semantic, "c-two.pietto").bindings) == 1
    consumer = _environment(semantic, "d-consumer.pietto")
    assert consumer.bindings == ()
    assert consumer.issues[0].status is (
        module_bindings.ProjectModuleBindingIssueStatus.UNKNOWN_EXPORTED_NAME
    )
    assert not hasattr(_required_bindings(semantic), "graph")
    assert not hasattr(_required_bindings(semantic), "cycles")


def test_slice6_candidate_proof_positions_and_alias_span_are_exact(
    tmp_path: Path,
) -> None:
    semantic = _simple_semantic(
        tmp_path,
        'import "library.pietto":\n    shape Customer as Buyer\n',
    )
    binding = _environment(semantic, "main.pietto").bindings[0]
    candidate = _required_bindings(semantic).imported_export_candidates[-1]
    assert candidate.owning_module_path == "main.pietto"
    assert candidate.local_binding_name == "Buyer"
    assert candidate.target_identity == binding.target_identity
    assert candidate.proof is (
        module_exports.ProjectImportedBindingCandidateProof.EXPLICIT_NAMED_IMPORT
    )
    assert candidate.module_statement_position == 0
    assert candidate.item_position == 0
    assert candidate.source_span == binding.request.source_item.local_name_span


def test_matching_export_request_consumes_real_candidate_for_reexport(
    tmp_path: Path,
) -> None:
    semantic = _simple_semantic(
        tmp_path,
        (
            'import "library.pietto":\n'
            "    shape Customer as Buyer\n"
            "export:\n"
            "    shape Buyer\n"
        ),
    )
    assert semantic.module_exports is not None
    surface = semantic.module_exports.find_module_path("main.pietto")[0]
    assert len(surface.entries) == 1
    entry = surface.entries[0]
    assert (
        entry.origin is module_exports.ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT
    )
    assert entry.target_identity.module_path == "library.pietto"
    assert isinstance(
        entry.resolved_from, module_exports.ProjectImportedExportCandidate
    )


def test_schema_v2_semantic_result_retains_private_bindings_and_fail_closed_posture(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path / "project",
        {
            "library.pietto": SIX_KIND_SOURCE + SIX_KIND_EXPORTS,
            "main.pietto": 'import "library.pietto":\n    shape Customer\n',
        },
    )
    assert parse_result.ok
    assert semantic.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert semantic.selected_input_index is not None
    assert semantic.module_catalogs is not None
    assert semantic.module_bindings is not None
    assert semantic.module_exports is not None
    assert semantic.module_graph is not None
    assert semantic.module_diagnostic_facts is not None
    assert semantic.model is None
    assert semantic.diagnostics == ()
    assert not semantic.ok
    assert (
        ProjectSemanticResult(root=None, config_path=None, model=None).module_bindings
        is None
    )
    assert (
        ProjectSemanticResult(root=None, config_path=None, model=None).module_graph
        is None
    )


def test_schema_v2_text_and_json_remain_exact_and_private(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(
        tmp_path / "project",
        {
            "library.pietto": SIX_KIND_SOURCE + SIX_KIND_EXPORTS,
            "main.pietto": 'import "library.pietto":\n    shape Customer\n',
        },
    )
    assert cli.main(["check", "--project", str(root)]) == 1
    text_capture = capsys.readouterr()
    assert text_capture.out == text_capture.err == ""
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    capture = capsys.readouterr()
    document = json.loads(capture.out)
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
    assert capture.err == ""
    for forbidden in (
        "module_bindings",
        "module_graph",
        "ProjectModuleBinding",
        "local_binding_name",
        "unresolved_target_module",
        "import_binding_collision",
    ):
        assert forbidden not in capture.out


def test_schema_v1_semantics_json_and_binding_absence_remain_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(
        tmp_path / "project",
        {
            "a.pietto": "type Shared = Int\n",
            "b.pietto": "type Shared = Text\n",
        },
        schema_version=1,
    )
    parse_result = project_check.check_project_parse_only(root)
    semantic = build_empty_project_semantic_result(parse_result)
    assert semantic.model is not None
    assert semantic.module_catalogs is None
    assert semantic.module_exports is None
    assert semantic.module_bindings is None
    assert semantic.module_graph is None
    assert semantic.module_diagnostic_facts is None
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2001",)
    assert semantic.model.catalog.type_symbols["Shared"].path == "a.pietto"
    expected = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic.diagnostics,
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    capture = capsys.readouterr()
    assert json.loads(capture.out) == expected
    assert capture.err == ""
    assert "module_bindings" not in capture.out


def test_builder_uses_only_preloaded_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parse_result, _ = _semantic_project(
        tmp_path / "project",
        {
            "library.pietto": SIX_KIND_SOURCE + SIX_KIND_EXPORTS,
            "main.pietto": 'import "library.pietto":\n    shape Customer\n',
        },
    )
    assert parse_result.selected_input_index is not None
    catalogs = module_catalog._build_project_module_catalog_set(parse_result.modules)

    def forbid_io(*args: object, **kwargs: object) -> object:
        raise AssertionError("binding builder performed filesystem I/O")

    monkeypatch.setattr(Path, "open", forbid_io)
    monkeypatch.setattr(os, "stat", forbid_io)
    result = module_bindings._build_project_module_binding_environment_set(
        parse_result.selected_input_index,
        parse_result.modules,
        catalogs,
    )
    assert len(result.find_module_path("main.pietto")[0].bindings) == 1


def test_no_public_diagnostics_graph_ir_sql_or_serialized_binding_surface(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path / "project",
        {
            "library.pietto": SIX_KIND_SOURCE + SIX_KIND_EXPORTS,
            "main.pietto": 'import "library.pietto":\n    shape Missing\n',
        },
    )
    assert tuple(item.code for item in semantic.diagnostics) == ("PIE-S2705",)
    assert semantic.model is None
    assert semantic.module_graph is not None
    assert semantic.module_diagnostic_facts is not None
    environment_set = _required_bindings(semantic)
    assert not hasattr(environment_set, "graph")
    assert not hasattr(environment_set, "cycles")
    assert not hasattr(environment_set, "ir")
    assert not hasattr(environment_set, "sql")
    for name in (
        "ProjectImportedBindingIdentity",
        "ProjectModuleImportRequest",
        "ProjectResolvedImportedBinding",
        "ProjectModuleBindingIssue",
        "ProjectModuleBindingEnvironment",
        "ProjectModuleBindingEnvironmentSet",
    ):
        assert not hasattr(pietto, name)
    binding_source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    graph_source = (REPO_ROOT / "src/pietto/_project/module_graph.py").read_text(
        encoding="utf-8"
    )
    assert all(f"PIE-S270{number}" not in binding_source for number in range(1, 8))
    assert all(f"PIE-S270{number}" in graph_source for number in range(1, 8))


def test_slice7_contract_test_inventory_and_active_gate_manifest_are_exact() -> None:
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert (REPO_ROOT / SOURCE_REL).is_file()
    source = (REPO_ROOT / TEST_REL).read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert names == EXPECTED_TEST_NAMES
    assert len(names) == 30
    assert not any(
        node.decorator_list
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert PHASE54_ACTIVE_GATE2_MARKER == "PHASE54_SLICE10_GATE2"
    assert PHASE54_ACTIVE_GATE2_BASE == "fadb1924af057cfc901a1658e117810d699e2358"
    assert len(PHASE54_SLICE10_ORIGINAL_ADDED_PATHS) == 3
    assert len(PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS) == 69
    assert PHASE54_ACTIVE_GATE2_ADDED_PATHS == frozenset()
    assert len(PHASE54_ACTIVE_GATE2_MODIFIED_PATHS) == 43
    assert PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert _matches_phase54_active_gate2_manifest(_active_state())
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR3_BASE == (
        "17a5b01e555930537334d4d0bcf3480e332b7e91"
    )
    assert (
        active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR3_MODIFIED_PATHS
        == PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR4_BASE == (
        "3f057874a1bec524da38b58c243267f4590c167b"
    )
    assert (
        active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR4_MODIFIED_PATHS
        == PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    )
    assert active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR5_BASE == (
        "fcdd02b5604c2b84d861b593a1887eaeb4620c91"
    )
    assert (
        active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR5_MODIFIED_PATHS
        == PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    )
    assert "ImportStatement.target" not in inspect.getsource(module_exports)
    assert "_build_project_module_binding_environment_set" not in pietto.__dict__
    assert active_gate2_manifest.ALLOWLIST_PATHS == (
        active_gate2_manifest.ADDED_PATHS | active_gate2_manifest.MODIFIED_PATHS
    )
