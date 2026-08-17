from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from importlib.metadata import version
import inspect
import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

import pietto
import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_catalog as module_catalog
import pietto._project.module_exports as module_exports
import pietto.cli as cli
from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_expected_allowlist_paths,
    phase54_post_slice12_interlude_dirty_is_active,
    PHASE54_ACTIVE_GATE2_ADDED_PATHS,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_ACTIVE_GATE2_DELETED_PATHS,
    PHASE54_ACTIVE_GATE2_MARKER,
    PHASE54_ACTIVE_GATE2_MODIFIED_PATHS,
    PHASE54_SLICE10_ORIGINAL_ADDED_PATHS,
    PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS,
    PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PR_CI_REPAIR_BASE,
    PHASE54_SLICE12_PR_CI_REPAIR_BRANCH,
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH,
    PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS,
    PHASE54_SLICE11_PYTHON313_REPAIR_BASE,
    PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH,
    PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    PHASE55_SLICE2_GATE1_PROJECTED_ALLOWLIST_A2_M75_D0,
    PHASE55_SLICE2_GATE2_ALLOWLIST_A2_M76_D0,
    Phase54Gate2RepositoryState,
    _matches_phase54_active_gate2_manifest,
    phase54_active_gate2_manifest_is_active,
    phase54_slice11_pr_ci_repair_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_mechanical_repair3_clean_topic_is_active,
    phase54_slice12_mechanical_repair3_is_active,
    phase54_slice12_mechanical_repair4_clean_topic_is_active,
    phase54_slice12_mechanical_repair4_is_active,
    phase54_slice12_product_repair3_clean_topic_is_active,
    phase54_slice12_product_repair10_clean_topic_is_active,
    phase54_slice12_product_repair11_clean_topic_is_active,
    phase54_slice12_product_repair12_clean_topic_is_active,
    phase54_slice12_product_repair13_clean_topic_is_active,
    phase54_slice12_product_repair14_clean_topic_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
    phase54_slice12_product_repair12_is_active,
    phase54_slice12_product_repair13_is_active,
    phase54_slice12_product_repair14_is_active,
    phase54_slice11_python313_repair_is_active,
    phase54_slice11_substantive_recovery_is_active,
)
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
from pietto.ast_nodes import ImportStatement, Script, Span
from pietto.parser_api import parse_source


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice6-local-export-eligibility-visibility-explicit-"
    "named-reexport-and-facade-semantics-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_exports.py"
TEST_REL = "tests/test_phase54_local_export_visibility_module_facades.py"
HELPER_REL = "tests/_phase54_active_gate2_manifest.py"


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


EXPECTED_TEST_NAMES = (
    "test_export_carrier_enums_fields_privacy_and_exact_six_kind_mapping_are_locked",
    "test_export_carrier_constructors_reject_wrong_types_and_inconsistent_values",
    "test_no_export_block_builds_one_empty_private_facade_per_module_without_catalog_changes",
    "test_exact_six_local_declaration_kinds_resolve_and_constraint_derive_remain_private",
    "test_only_successful_explicit_local_exports_are_visible_without_catalog_mutation",
    "test_unique_exact_local_match_preserves_nominal_identity_occurrence_and_source_request",
    "test_missing_local_declaration_fails_closed_with_unresolved_issue",
    "test_duplicate_exact_local_identity_fails_closed_without_winner",
    "test_same_spelling_in_another_namespace_or_kind_does_not_match",
    "test_same_spelling_in_another_module_does_not_satisfy_local_export",
    "test_module_path_name_case_and_unicode_are_preserved_exactly",
    "test_multiple_export_blocks_and_items_preserve_statement_item_and_request_order",
    "test_repeated_exact_requests_remain_distinct_entries_and_duplicate_issue_facts",
    "test_requests_entries_issues_and_lookup_results_are_immutable_tuples",
    "test_facade_and_facade_set_are_frozen_slotted_value_equal_hashable_and_ordered",
    "test_unique_explicit_named_import_candidate_builds_direct_reexport_with_original_target",
    "test_reexport_exposed_name_is_local_binding_name_and_every_hop_requires_explicit_request",
    "test_no_imported_candidate_produces_no_reexport",
    "test_multiple_imported_candidates_fail_closed_without_winner",
    "test_local_and_imported_candidate_conflict_fails_closed_without_winner",
    "test_wrong_owner_namespace_kind_or_target_candidate_fails_closed",
    "test_candidate_seam_never_traverses_facades_import_targets_or_transitive_exports",
    "test_facade_exact_namespace_kind_name_and_target_identity_queries_return_complete_tuples",
    "test_local_visibility_query_distinguishes_local_exports_from_reexports_and_private_identities",
    "test_project_facade_set_preserves_selected_input_order_and_exact_module_lookup",
    "test_schema_v2_semantic_result_retains_catalogs_and_facades_with_unchanged_failure_posture",
    "test_schema_v2_parse_and_read_failures_and_manual_constructor_keep_exports_absent",
    "test_schema_v2_text_and_json_cli_remain_exact_and_serialize_no_export_facts",
    "test_schema_v1_semantics_cli_json_sql_and_module_export_absence_remain_exact",
    "test_retained_later_public_privacy_no_diagnostics_and_prohibited_surfaces_are_locked",
)

ALL_DEFINITIONS = (
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
ALL_EXPORTS = (
    "export:\n"
    "    type Email\n"
    "    enum Status\n"
    "    shape User\n"
    "    source users\n"
    "    table FirstRelation\n"
    "    query SecondRelation\n"
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


def _catalogs(
    *modules: ProjectLogicalModule,
) -> module_catalog.ProjectModuleCatalogSet:
    return module_catalog._build_project_module_catalog_set(tuple(modules))


def _surfaces(
    *modules: ProjectLogicalModule,
    candidates: tuple[module_exports.ProjectImportedExportCandidate, ...] = (),
) -> module_exports.ProjectModuleExportSurfaceSet:
    return module_exports._build_project_module_export_surface_set(
        _catalogs(*modules), imported_binding_candidates=candidates
    )


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


def _candidate(
    *,
    owner: str = "main.pietto",
    namespace: ProjectSymbolNamespace = ProjectSymbolNamespace.TYPE,
    declaration_kind: ProjectSymbolKind = ProjectSymbolKind.SHAPE,
    local_name: str = "Imported",
    target: module_catalog.ProjectNominalDeclarationIdentity | None = None,
) -> module_exports.ProjectImportedExportCandidate:
    return module_exports.ProjectImportedExportCandidate(
        owning_module_path=owner,
        namespace=namespace,
        declaration_kind=declaration_kind,
        local_binding_name=local_name,
        target_identity=target
        or _identity(
            module_path="library.pietto",
            namespace=namespace,
            declaration_kind=declaration_kind,
            declared_name="Original",
        ),
        proof=module_exports.ProjectImportedBindingCandidateProof.EXPLICIT_NAMED_IMPORT,
        module_statement_position=0,
        item_position=0,
        source_span=Span(
            path=owner,
            line=1,
            column=1,
            end_line=2,
            end_column=19,
        ),
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


def _one_surface(
    source: str,
    *,
    path: str = "main.pietto",
    candidates: tuple[module_exports.ProjectImportedExportCandidate, ...] = (),
) -> module_exports.ProjectModuleExportSurface:
    result = _surfaces(_module(source, path=path), candidates=candidates)
    assert len(result.surfaces) == 1
    return result.surfaces[0]


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


def test_export_carrier_enums_fields_privacy_and_exact_six_kind_mapping_are_locked() -> (
    None
):
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert module_exports.__all__ == ()
    assert tuple(module_exports.ProjectModuleExportEntryOrigin) == (
        module_exports.ProjectModuleExportEntryOrigin.LOCAL_DECLARATION,
        module_exports.ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT,
    )
    assert tuple(module_exports.ProjectModuleExportIssueStatus) == (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
        module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION,
        module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET,
        module_exports.ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE,
        module_exports.ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST,
    )
    assert {
        key.value: (namespace.value, kind.value)
        for key, (namespace, kind) in module_exports._ELIGIBLE_EXPORT_KIND_MAP.items()
    } == {
        "type": ("type", "type"),
        "enum": ("type", "enum"),
        "shape": ("type", "shape"),
        "source": ("relation", "source"),
        "table": ("relation", "table"),
        "query": ("relation", "query"),
    }
    assert tuple(
        field.name for field in fields(module_exports.ProjectModuleExportRequest)
    ) == (
        "owning_module_path",
        "namespace",
        "declaration_kind",
        "local_name",
        "module_statement_position",
        "item_position",
        "source_item",
    )
    assert tuple(
        field.name for field in fields(module_exports.ProjectImportedExportCandidate)
    ) == (
        "owning_module_path",
        "namespace",
        "declaration_kind",
        "local_binding_name",
        "target_identity",
        "proof",
        "module_statement_position",
        "item_position",
        "source_span",
    )


def test_export_carrier_constructors_reject_wrong_types_and_inconsistent_values() -> (
    None
):
    surface = _one_surface("type Shared = Int\nexport:\n    type Shared\n")
    request = surface.requests[0]
    occurrence = cast(
        module_catalog.ProjectDeclarationOccurrence,
        surface.entries[0].resolved_from,
    )
    with pytest.raises(ValueError):
        replace(request, owning_module_path="../main.pietto")
    with pytest.raises(ValueError):
        replace(request, local_name="Other")
    with pytest.raises(TypeError):
        replace(request, namespace="type")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        _candidate(declaration_kind=ProjectSymbolKind.CONSTRAINT)
    with pytest.raises(ValueError):
        replace(surface.entries[0], exposed_name="Other")
    wrong_identity = _identity(
        namespace=ProjectSymbolNamespace.TYPE,
        declaration_kind=ProjectSymbolKind.ENUM,
        declared_name="Shared",
    )
    with pytest.raises(ValueError):
        replace(
            surface.entries[0],
            target_identity=wrong_identity,
            resolved_from=replace(occurrence, identity=wrong_identity),
        )
    with pytest.raises(TypeError):
        module_exports.ProjectModuleExportEntry(
            owning_module_path="main.pietto",
            namespace=ProjectSymbolNamespace.TYPE,
            declaration_kind=ProjectSymbolKind.TYPE_ALIAS,
            exposed_name="Shared",
            origin=module_exports.ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT,
            target_identity=occurrence.identity,
            request=request,
            resolved_from=occurrence,
        )
    reexport = _one_surface(
        "export:\n    shape Imported\n",
        candidates=(_candidate(),),
    ).entries[0]
    assert isinstance(
        reexport.resolved_from, module_exports.ProjectImportedExportCandidate
    )
    with pytest.raises(ValueError):
        replace(
            reexport,
            resolved_from=replace(reexport.resolved_from, local_binding_name="Other"),
        )
    with pytest.raises(ValueError):
        module_exports.ProjectModuleExportIssue(
            status=module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET,
            request=request,
        )
    with pytest.raises(ValueError):
        module_exports.ProjectModuleExportIssue(
            status=module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
            request=request,
            local_occurrences=(occurrence,),
        )
    ambiguous_local = _one_surface(
        "shape Shared:\n"
        "    id: Int\n"
        "shape Shared:\n"
        "    id: Int\n"
        "export:\n"
        "    shape Shared\n"
    )
    with pytest.raises(ValueError):
        module_exports.ProjectModuleExportIssue(
            status=module_exports.ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE,
            request=ambiguous_local.requests[0],
            local_occurrences=ambiguous_local.issues[0].local_occurrences,
            imported_candidates=(
                _candidate(
                    local_name="Shared",
                    target=_identity(
                        module_path="library.pietto",
                        namespace=ProjectSymbolNamespace.RELATION,
                        declaration_kind=ProjectSymbolKind.SOURCE,
                    ),
                ),
            ),
        )


def test_no_export_block_builds_one_empty_private_facade_per_module_without_catalog_changes() -> (
    None
):
    module = _module(ALL_DEFINITIONS)
    catalogs = _catalogs(module)
    result = module_exports._build_project_module_export_surface_set(catalogs)

    assert len(result.surfaces) == 1
    assert result.surfaces[0].module == module
    assert result.surfaces[0].export_statements == ()
    assert result.surfaces[0].requests == ()
    assert result.surfaces[0].entries == ()
    assert result.surfaces[0].issues == ()
    assert len(catalogs.catalogs[0].occurrences) == 8


def test_exact_six_local_declaration_kinds_resolve_and_constraint_derive_remain_private() -> (
    None
):
    surface = _one_surface(ALL_DEFINITIONS + ALL_EXPORTS)

    assert tuple(
        (entry.namespace, entry.declaration_kind) for entry in surface.entries
    ) == (
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.TYPE_ALIAS),
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.ENUM),
        (ProjectSymbolNamespace.TYPE, ProjectSymbolKind.SHAPE),
        (ProjectSymbolNamespace.RELATION, ProjectSymbolKind.SOURCE),
        (ProjectSymbolNamespace.RELATION, ProjectSymbolKind.TABLE),
        (ProjectSymbolNamespace.RELATION, ProjectSymbolKind.QUERY),
    )
    assert tuple(entry.exposed_name for entry in surface.entries) == (
        "Email",
        "Status",
        "User",
        "users",
        "FirstRelation",
        "SecondRelation",
    )
    assert surface.issues == ()
    assert all(
        entry.target_identity.declaration_kind
        not in (ProjectSymbolKind.CONSTRAINT, ProjectSymbolKind.DERIVE)
        for entry in surface.entries
    )


def test_only_successful_explicit_local_exports_are_visible_without_catalog_mutation() -> (
    None
):
    module = _module(
        "type Public = Int\ntype Private = Text\nexport:\n    type Public\n"
    )
    catalogs = _catalogs(module)
    before = catalogs.catalogs[0].occurrences
    surface = module_exports._build_project_module_export_surface_set(
        catalogs
    ).surfaces[0]

    assert tuple(entry.exposed_name for entry in surface.entries) == ("Public",)
    assert catalogs.catalogs[0].occurrences == before
    private_identity = _identity(declared_name="Private")
    public_identity = _identity(declared_name="Public")
    assert surface.is_local_declaration_visible(public_identity)
    assert not surface.is_local_declaration_visible(private_identity)
    assert catalogs.find_identity(private_identity)


def test_unique_exact_local_match_preserves_nominal_identity_occurrence_and_source_request() -> (
    None
):
    surface = _one_surface("type Shared = Int\nexport:\n    type Shared\n")
    entry = surface.entries[0]
    occurrence = cast(module_catalog.ProjectDeclarationOccurrence, entry.resolved_from)

    assert (
        entry.origin is module_exports.ProjectModuleExportEntryOrigin.LOCAL_DECLARATION
    )
    assert entry.target_identity == occurrence.identity
    assert entry.request is surface.requests[0]
    assert entry.request.source_item.local_name == "Shared"
    assert entry.request.source_item.span == Span(
        path="main.pietto",
        line=3,
        column=5,
        end_line=3,
        end_column=16,
    )
    assert entry.request.module_statement_position == 0
    assert entry.request.item_position == 0


def test_missing_local_declaration_fails_closed_with_unresolved_issue() -> None:
    surface = _one_surface("export:\n    type Missing\n")

    assert surface.entries == ()
    assert tuple(issue.status for issue in surface.issues) == (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
    )
    assert surface.issues[0].local_occurrences == ()
    assert surface.issues[0].imported_candidates == ()


def test_duplicate_exact_local_identity_fails_closed_without_winner() -> None:
    surface = _one_surface(
        "type Shared = Int\ntype Shared = Text\nexport:\n    type Shared\n"
    )

    assert surface.entries == ()
    assert tuple(issue.status for issue in surface.issues) == (
        module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION,
    )
    assert len(surface.issues[0].local_occurrences) == 2
    assert tuple(
        occurrence.declaration_position
        for occurrence in surface.issues[0].local_occurrences
    ) == (0, 1)
    for forbidden in ("first", "last", "winner", "get_unique"):
        assert not hasattr(surface, forbidden)


def test_same_spelling_in_another_namespace_or_kind_does_not_match() -> None:
    enum_only = _one_surface("enum Shared:\n    one\nexport:\n    type Shared\n")
    relation_only = _one_surface(
        "shape Row:\n"
        "    id: Int\n"
        'source Shared: Row is postgres.table("public.shared")\n'
        "export:\n"
        "    type Shared\n"
    )

    for surface in (enum_only, relation_only):
        assert surface.entries == ()
        assert tuple(issue.status for issue in surface.issues) == (
            module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
        )


def test_same_spelling_in_another_module_does_not_satisfy_local_export() -> None:
    modules = (
        _module("export:\n    type Shared\n", path="a.pietto", position=0),
        _module("type Shared = Int\n", path="b.pietto", position=1),
    )
    surfaces = _surfaces(*modules)

    assert surfaces.surfaces[0].entries == ()
    assert surfaces.surfaces[0].issues[0].status is (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING
    )
    assert (
        len(_catalogs(*modules).find_identity(_identity(module_path="b.pietto"))) == 1
    )


def test_module_path_name_case_and_unicode_are_preserved_exactly() -> None:
    path = "Módels/Customer.pietto"
    surface = _one_surface(
        "type CaseName = Int\nexport:\n    type CaseName\n",
        path=path,
    )

    assert surface.module.path == path
    assert surface.requests[0].owning_module_path == path
    assert surface.entries[0].target_identity == _identity(
        module_path=path,
        declared_name="CaseName",
    )
    wrong_case = _one_surface(
        "type CaseName = Int\nexport:\n    type casename\n",
        path=path,
    )
    assert wrong_case.entries == ()


def test_multiple_export_blocks_and_items_preserve_statement_item_and_request_order() -> (
    None
):
    surface = _one_surface(
        "type First = Int\n"
        "type Second = Text\n"
        "enum Third:\n"
        "    one\n"
        "export:\n"
        "    type Second\n"
        "    type First\n"
        "export:\n"
        "    enum Third\n"
    )

    assert len(surface.export_statements) == 2
    assert tuple(request.local_name for request in surface.requests) == (
        "Second",
        "First",
        "Third",
    )
    assert tuple(
        (request.module_statement_position, request.item_position)
        for request in surface.requests
    ) == ((0, 0), (0, 1), (1, 0))
    assert tuple(entry.exposed_name for entry in surface.entries) == (
        "Second",
        "First",
        "Third",
    )


def test_repeated_exact_requests_remain_distinct_entries_and_duplicate_issue_facts() -> (
    None
):
    surface = _one_surface(
        "type Shared = Int\nexport:\n    type Shared\nexport:\n    type Shared\n"
    )

    assert len(surface.requests) == 2
    assert surface.requests[0] != surface.requests[1]
    assert len(surface.entries) == 2
    assert surface.entries[0].target_identity == surface.entries[1].target_identity
    assert tuple(issue.status for issue in surface.issues) == (
        module_exports.ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST,
    )
    assert surface.issues[0].request == surface.requests[1]
    assert surface.issues[0].prior_requests == (surface.requests[0],)


def test_requests_entries_issues_and_lookup_results_are_immutable_tuples() -> None:
    surface = _one_surface(
        "type Shared = Int\nexport:\n    type Shared\n    type Missing\n"
    )

    assert type(surface.requests) is tuple
    assert type(surface.entries) is tuple
    assert type(surface.issues) is tuple
    assert (
        type(
            surface.find_namespace_kind_name(
                ProjectSymbolNamespace.TYPE,
                ProjectSymbolKind.TYPE_ALIAS,
                "Shared",
            )
        )
        is tuple
    )
    assert (
        type(surface.find_target_identity(surface.entries[0].target_identity)) is tuple
    )
    with pytest.raises(FrozenInstanceError):
        surface.requests = ()  # type: ignore[misc]
    ordered = _one_surface(
        "type First = Int\n"
        "type Second = Int\n"
        "export:\n"
        "    type First\n"
        "    type Second\n"
    )
    with pytest.raises(ValueError):
        replace(ordered, entries=tuple(reversed(ordered.entries)))
    with pytest.raises(ValueError):
        replace(ordered, entries=(ordered.entries[0], ordered.entries[0]))
    duplicate_missing = _one_surface(
        "export:\n    shape Missing\nexport:\n    shape Missing\n"
    )
    assert tuple(issue.status for issue in duplicate_missing.issues) == (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
        module_exports.ProjectModuleExportIssueStatus.DUPLICATE_SOURCE_REQUEST,
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING,
    )
    with pytest.raises(ValueError):
        replace(
            duplicate_missing,
            issues=(
                duplicate_missing.issues[0],
                duplicate_missing.issues[2],
                duplicate_missing.issues[1],
            ),
        )


def test_facade_and_facade_set_are_frozen_slotted_value_equal_hashable_and_ordered() -> (
    None
):
    first = _surfaces(
        _module(
            "type A = Int\nexport:\n    type A\n",
            path="a.pietto",
            position=0,
        ),
        _module("type B = Text\n", path="b.pietto", position=1),
    )
    second = _surfaces(
        _module(
            "type A = Int\nexport:\n    type A\n",
            path="a.pietto",
            position=0,
        ),
        _module("type B = Text\n", path="b.pietto", position=1),
    )

    assert is_dataclass(first)
    assert not hasattr(first, "__dict__")
    assert first == second
    assert hash(first) == hash(second)
    assert tuple(surface.module.path for surface in first.surfaces) == (
        "a.pietto",
        "b.pietto",
    )
    with pytest.raises(FrozenInstanceError):
        first.surfaces = ()  # type: ignore[misc]


def test_unique_explicit_named_import_candidate_builds_direct_reexport_with_original_target() -> (
    None
):
    target = _identity(
        module_path="library.pietto",
        declaration_kind=ProjectSymbolKind.SHAPE,
        declared_name="Original",
    )
    candidate = _candidate(target=target)
    surface = _one_surface(
        "export:\n    shape Imported\n",
        candidates=(candidate,),
    )

    assert surface.issues == ()
    assert len(surface.entries) == 1
    entry = surface.entries[0]
    assert (
        entry.origin is module_exports.ProjectModuleExportEntryOrigin.EXPLICIT_REEXPORT
    )
    assert entry.exposed_name == "Imported"
    assert entry.target_identity == target
    assert entry.resolved_from is candidate


def test_reexport_exposed_name_is_local_binding_name_and_every_hop_requires_explicit_request() -> (
    None
):
    candidate = _candidate(local_name="LocalAlias")
    visible = _one_surface(
        "export:\n    shape LocalAlias\n",
        candidates=(candidate,),
    )
    private = _one_surface("", candidates=(candidate,))

    assert tuple(entry.exposed_name for entry in visible.entries) == ("LocalAlias",)
    assert visible.entries[0].target_identity.declared_name == "Original"
    assert private.requests == ()
    assert private.entries == ()
    assert private.issues == ()


def test_no_imported_candidate_produces_no_reexport() -> None:
    surface = _one_surface("export:\n    shape Imported\n")

    assert surface.entries == ()
    assert surface.issues[0].status is (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING
    )


def test_multiple_imported_candidates_fail_closed_without_winner() -> None:
    candidates = (
        _candidate(
            target=_identity(
                module_path="one.pietto", declaration_kind=ProjectSymbolKind.SHAPE
            )
        ),
        _candidate(
            target=_identity(
                module_path="two.pietto", declaration_kind=ProjectSymbolKind.SHAPE
            )
        ),
    )
    surface = _one_surface(
        "export:\n    shape Imported\n",
        candidates=candidates,
    )

    assert surface.entries == ()
    assert surface.issues[0].status is (
        module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET
    )
    assert surface.issues[0].imported_candidates == candidates


def test_local_and_imported_candidate_conflict_fails_closed_without_winner() -> None:
    candidate = _candidate(
        declaration_kind=ProjectSymbolKind.TYPE_ALIAS,
        local_name="Shared",
        target=_identity(module_path="library.pietto", declared_name="Shared"),
    )
    surface = _one_surface(
        "type Shared = Int\nexport:\n    type Shared\n",
        candidates=(candidate,),
    )

    assert surface.entries == ()
    assert surface.issues[0].status is (
        module_exports.ProjectModuleExportIssueStatus.AMBIGUOUS_CANDIDATE_SET
    )
    assert len(surface.issues[0].local_occurrences) == 1
    assert surface.issues[0].imported_candidates == (candidate,)


def test_wrong_owner_namespace_kind_or_target_candidate_fails_closed() -> None:
    wrong_owner = _candidate(owner="other.pietto")
    wrong_kind = _candidate(
        namespace=ProjectSymbolNamespace.TYPE,
        declaration_kind=ProjectSymbolKind.ENUM,
    )
    wrong_target = _candidate(
        target=_identity(
            module_path="library.pietto",
            namespace=ProjectSymbolNamespace.RELATION,
            declaration_kind=ProjectSymbolKind.SOURCE,
        )
    )

    owner_surface = _one_surface(
        "export:\n    shape Imported\n",
        candidates=(wrong_owner,),
    )
    assert owner_surface.entries == ()
    assert owner_surface.issues[0].status is (
        module_exports.ProjectModuleExportIssueStatus.UNRESOLVED_EXPORT_BINDING
    )
    for candidate in (wrong_kind, wrong_target):
        surface = _one_surface(
            "export:\n    shape Imported\n",
            candidates=(candidate,),
        )
        assert surface.entries == ()
        assert surface.issues[0].status is (
            module_exports.ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE
        )

    exact_candidates = (
        _candidate(),
        _candidate(
            target=_identity(
                module_path="second.pietto",
                declaration_kind=ProjectSymbolKind.SHAPE,
                declared_name="Two",
            )
        ),
    )
    mixed_surface = _one_surface(
        "export:\n    shape Imported\n",
        candidates=(*exact_candidates, wrong_target),
    )
    assert mixed_surface.entries == ()
    assert tuple(issue.status for issue in mixed_surface.issues) == (
        module_exports.ProjectModuleExportIssueStatus.INELIGIBLE_OR_INCONSISTENT_CANDIDATE,
    )
    assert mixed_surface.issues[0].imported_candidates == (
        *exact_candidates,
        wrong_target,
    )


def test_candidate_seam_never_traverses_facades_import_targets_or_transitive_exports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module(
        'import "does/not/exist.pietto":\n'
        "    shape Remote as Imported\n"
        "export:\n"
        "    shape Imported\n"
    )
    assert module.parsed_input is not None
    import_statement = cast(
        ImportStatement, module.parsed_input.script.module_statements[0]
    )
    candidate = replace(
        _candidate(),
        module_statement_position=0,
        source_span=import_statement.items[0].span,
    )
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("filesystem")),
    )

    surface = module_exports._build_project_module_export_surface_set(
        _catalogs(module),
        imported_binding_candidates=(candidate,),
    ).surfaces[0]
    assert surface.entries[0].target_identity == candidate.target_identity
    assert not hasattr(surface, "graph")
    assert not hasattr(surface, "cycles")


def test_facade_exact_namespace_kind_name_and_target_identity_queries_return_complete_tuples() -> (
    None
):
    surface = _one_surface(
        "type Shared = Int\nexport:\n    type Shared\nexport:\n    type Shared\n"
    )
    identity = surface.entries[0].target_identity

    assert (
        surface.find_namespace_kind_name(
            ProjectSymbolNamespace.TYPE,
            ProjectSymbolKind.TYPE_ALIAS,
            "Shared",
        )
        == surface.entries
    )
    assert surface.find_target_identity(identity) == surface.entries
    assert (
        surface.find_namespace_kind_name(
            ProjectSymbolNamespace.TYPE,
            ProjectSymbolKind.ENUM,
            "Shared",
        )
        == ()
    )
    assert surface.find_target_identity(_identity(declared_name="Missing")) == ()


def test_local_visibility_query_distinguishes_local_exports_from_reexports_and_private_identities() -> (
    None
):
    candidate = _candidate()
    surface = _one_surface(
        "type Local = Int\n"
        "type Private = Text\n"
        "export:\n"
        "    type Local\n"
        "    shape Imported\n",
        candidates=(candidate,),
    )

    local = _identity(declared_name="Local")
    private = _identity(declared_name="Private")
    assert surface.is_local_declaration_visible(local)
    assert not surface.is_local_declaration_visible(private)
    assert not surface.is_local_declaration_visible(candidate.target_identity)


def test_project_facade_set_preserves_selected_input_order_and_exact_module_lookup() -> (
    None
):
    result = _surfaces(
        _module("", path="z.pietto", position=0),
        _module("", path="a.pietto", position=1),
    )

    assert tuple(surface.module.path for surface in result.surfaces) == (
        "z.pietto",
        "a.pietto",
    )
    assert result.find_module_path("a.pietto") == (result.surfaces[1],)
    assert result.find_module_path("missing.pietto") == ()
    assert result.find_module_path("../a.pietto") == ()
    assert result.find_target_identity(_identity()) == ()


def test_schema_v2_semantic_result_retains_catalogs_and_facades_with_unchanged_failure_posture(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(
        root,
        "row.pietto",
        "shape Row:\n    id: Int\nexport:\n    shape Row\n",
    )
    parse_result, semantic = _project_semantic_result(root)

    assert parse_result.ok
    assert semantic.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES
    assert semantic.module_catalogs is not None
    assert semantic.module_exports is not None
    assert len(semantic.module_exports.surfaces) == 1
    assert tuple(
        entry.exposed_name for entry in semantic.module_exports.surfaces[0].entries
    ) == ("Row",)
    assert semantic.model is None
    assert semantic.diagnostics == ()
    assert not semantic.ok
    assert "module_exports" not in {
        field.name for field in fields(ProjectSemanticModel)
    }
    assert "module_exports" not in {
        field.name for field in fields(ProjectParseCheckResult)
    }


def test_schema_v2_parse_and_read_failures_and_manual_constructor_keep_exports_absent(
    tmp_path: Path,
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(root, "broken.pietto", "export:\n")
    parse_result, semantic = _project_semantic_result(root)
    assert not parse_result.ok
    assert semantic.module_catalogs is None
    assert semantic.module_exports is None

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
    assert build_empty_project_semantic_result(manual).module_exports is None
    default = ProjectSemanticResult(root=None, config_path=None, model=None)
    assert default.module_catalogs is None
    assert default.module_exports is None


def test_schema_v2_text_and_json_cli_remain_exact_and_serialize_no_export_facts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(tmp_path / "project", schema_version=2)
    _write(
        root,
        "row.pietto",
        "shape Row:\n    id: Int\nexport:\n    shape Row\n",
    )

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
        "module_exports",
        "ProjectModuleExport",
        "visibility",
        "target_identity",
        "explicit_reexport",
        "unresolved_export_binding",
    ):
        assert forbidden not in json_capture.out


def test_schema_v1_semantics_cli_json_sql_and_module_export_absence_remain_exact(
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
    assert semantic.module_exports is None
    assert tuple(diagnostic.code for diagnostic in semantic.diagnostics) == (
        "PIE-S2001",
    )
    assert semantic.model.catalog.type_symbols["Shared"].path == "a.pietto"
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic.diagnostics,
    )
    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == document
    assert captured.err == ""
    assert "module_exports" not in captured.out


def test_retained_later_public_privacy_no_diagnostics_and_prohibited_surfaces_are_locked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate2_active = phase54_active_gate2_manifest_is_active()
    repair_gate2_active = phase54_slice11_pr_ci_repair_is_active()
    slice12_repair_gate2_active = phase54_slice12_pr_ci_repair_is_active()
    slice12_product_repair3_active = phase54_slice12_product_repair3_is_active()
    slice12_product_repair3_clean_topic_active = (
        phase54_slice12_product_repair3_clean_topic_is_active()
    )
    slice12_product_repair10_active = phase54_slice12_product_repair10_is_active()
    slice12_product_repair10_clean_topic_active = (
        phase54_slice12_product_repair10_clean_topic_is_active()
    )
    slice12_product_repair11_active = phase54_slice12_product_repair11_is_active()
    slice12_product_repair11_clean_topic_active = (
        phase54_slice12_product_repair11_clean_topic_is_active()
    )
    slice12_product_repair12_active = phase54_slice12_product_repair12_is_active()
    slice12_product_repair12_clean_topic_active = (
        phase54_slice12_product_repair12_clean_topic_is_active()
    )
    slice12_product_repair13_active = phase54_slice12_product_repair13_is_active()
    slice12_product_repair13_clean_topic_active = (
        phase54_slice12_product_repair13_clean_topic_is_active()
    )
    slice12_mechanical_repair3_active = phase54_slice12_mechanical_repair3_is_active()
    slice12_mechanical_repair3_clean_topic_active = (
        phase54_slice12_mechanical_repair3_clean_topic_is_active()
    )
    slice12_mechanical_repair4_active = phase54_slice12_mechanical_repair4_is_active()
    slice12_mechanical_repair4_clean_topic_active = (
        phase54_slice12_mechanical_repair4_clean_topic_is_active()
    )
    slice12_product_repair14_active = phase54_slice12_product_repair14_is_active()
    slice12_product_repair14_clean_topic_active = (
        phase54_slice12_product_repair14_clean_topic_is_active()
    )
    python313_repair_active = phase54_slice11_python313_repair_is_active()
    recovery_gate2_active = phase54_slice11_substantive_recovery_is_active()
    interlude_active = phase54_post_slice12_interlude_dirty_is_active()
    interlude_expected_allowlist = set(
        phase54_post_slice12_interlude_expected_allowlist_paths()
    )
    assert _matches_phase54_active_gate2_manifest(_active_state())
    recovery_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BASE,
        branch_head=PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(recovery_state)
    python313_repair_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE11_PYTHON313_REPAIR_BASE,
        branch_head=PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE11_PYTHON313_REPAIR_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(python313_repair_state)
    slice12_repair_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PR_CI_REPAIR_BASE,
        branch_head=PHASE54_SLICE12_PR_CI_REPAIR_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PR_CI_REPAIR_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_repair_state)
    slice12_product_repair3_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PRODUCT_REPAIR3_BASE,
        branch_head=PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR3_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_product_repair3_state)
    slice12_product_repair10_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
        branch_head=PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_product_repair10_state)
    slice12_product_repair11_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
        branch_head=PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_product_repair11_state)
    slice12_product_repair12_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PRODUCT_REPAIR12_BASE,
        branch_head=PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR12_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_product_repair12_state)
    slice12_product_repair13_state = replace(
        _active_state(),
        branch_oid=PHASE54_SLICE12_PRODUCT_REPAIR13_BASE,
        branch_head=PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH,
        branch_upstream=f"origin/{PHASE54_SLICE12_PRODUCT_REPAIR13_BRANCH}",
        added_paths=frozenset(),
        modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS,
    )
    assert _matches_phase54_active_gate2_manifest(slice12_product_repair13_state)
    for changed in (
        replace(_active_state(), marker="PHASE54_SLICE9_GATE2"),
        replace(_active_state(), branch_oid="0" * 40),
        replace(_active_state(), added_paths=frozenset()),
        replace(
            _active_state(),
            added_paths=PHASE54_ACTIVE_GATE2_ADDED_PATHS | {"unrelated.txt"},
        ),
        replace(_active_state(), staged_paths=frozenset({"README.md"})),
        replace(_active_state(), other_paths=frozenset({"unrelated.txt"})),
        replace(_active_state(), branch_head="topic"),
        replace(_active_state(), worktree_count=2),
        replace(_active_state(), shallow=True),
        replace(_active_state(), active_git_operation=True),
        replace(
            slice12_product_repair13_state,
            modified_paths=PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS
            | {"unrelated.txt"},
        ),
        replace(slice12_product_repair13_state, branch_upstream="origin/main"),
    ):
        assert not _matches_phase54_active_gate2_manifest(changed)
    clean = replace(
        _active_state(),
        added_paths=frozenset(),
        modified_paths=frozenset(),
    )
    assert not _matches_phase54_active_gate2_manifest(clean)
    assert (
        tuple(inspect.signature(phase54_active_gate2_manifest_is_active).parameters)
        == ()
    )
    monkeypatch.setenv("PIETTO_PHASE54_ACTIVE_GATE2", PHASE54_ACTIVE_GATE2_MARKER)
    monkeypatch.setenv("PHASE54_ACTIVE_GATE2_MARKER", PHASE54_ACTIVE_GATE2_MARKER)
    monkeypatch.setattr(
        active_gate2_manifest,
        "_read_phase54_gate2_repository_state",
        lambda: clean,
    )
    assert not phase54_active_gate2_manifest_is_active()
    with pytest.raises(TypeError):
        phase54_active_gate2_manifest_is_active(
            lambda: _active_state()  # pyright: ignore[reportCallIssue]
        )

    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    graph_path = REPO_ROOT / "src/pietto/_project/module_graph.py"
    resolution_path = REPO_ROOT / "src/pietto/_project/module_resolution.py"
    relation_resolution_path = (
        REPO_ROOT / "src/pietto/_project/module_relation_resolution.py"
    )
    graph_source = graph_path.read_text(encoding="utf-8")
    non_graph_production = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src/pietto").rglob("*.py")
        if path not in {graph_path, resolution_path, relation_resolution_path}
    )
    public = "\n".join(
        (REPO_ROOT / relative).read_text(encoding="utf-8")
        for relative in (
            "src/pietto/__init__.py",
            "src/pietto/_project/json_v2.py",
            "src/pietto/cli_json.py",
            "src/pietto/ir/__init__.py",
            "src/pietto/sql/__init__.py",
        )
    )
    assert "ImportStatement.target" not in source
    assert "module graph" not in source.lower()
    for number in range(1, 8):
        code = f"PIE-S270{number}"
        assert code in graph_source
        assert code not in non_graph_production
        assert code not in public
    assert "ProjectModuleExport" not in public
    for name in (
        "ProjectModuleExportRequest",
        "ProjectImportedExportCandidate",
        "ProjectModuleExportEntry",
        "ProjectModuleExportIssue",
        "ProjectModuleExportSurface",
        "ProjectModuleExportSurfaceSet",
    ):
        assert not hasattr(pietto, name)
    assert version("pietto") == "0.1.0"
    assert not (REPO_ROOT / "Cargo.toml").exists()

    test_tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    tests = tuple(
        node
        for node in test_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tuple(node.name for node in tests) == EXPECTED_TEST_NAMES
    assert len(tests) == 30
    assert all(not node.decorator_list for node in tests)
    assert len(PHASE54_SLICE10_ORIGINAL_ADDED_PATHS) == 3
    assert len(PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS) == 69
    assert len(PHASE54_ACTIVE_GATE2_ADDED_PATHS) == 2
    assert len(PHASE54_ACTIVE_GATE2_MODIFIED_PATHS) == 51
    assert PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_MODIFIED_PATHS) == 52
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_ALLOWLIST_PATHS) == 55
    assert TEST_REL in active_gate2_manifest.PHASE55_ACTIVE_GATE2_READER_PATHS
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
    dirty = {
        *subprocess.run(
            ["git", "diff", "--name-only"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.splitlines(),
        *subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPO_ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.splitlines(),
    }
    active_allowlist = (
        PHASE54_ACTIVE_GATE2_ADDED_PATHS | PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    )
    phase55_active_allowlist = set(
        active_gate2_manifest.PHASE55_ACTIVE_GATE2_ALLOWLIST_PATHS
    )
    phase55_slice2_projected_allowlist = set(
        PHASE55_SLICE2_GATE1_PROJECTED_ALLOWLIST_A2_M75_D0
    )
    phase55_slice2_allowlist = set(PHASE55_SLICE2_GATE2_ALLOWLIST_A2_M76_D0)
    assert len(phase55_slice2_projected_allowlist) == 77
    assert "tests/test_phase50_import_module_export_readiness.py" not in (
        phase55_slice2_projected_allowlist
    )
    assert len(phase55_slice2_allowlist) == 78
    assert "tests/test_phase50_import_module_export_readiness.py" in (
        phase55_slice2_allowlist
    )
    repair_allowlist = set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS)
    slice12_repair_allowlist = set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS)
    slice12_product_repair3_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS
    )
    slice12_product_repair10_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS
    )
    slice12_product_repair11_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS
    )
    slice12_product_repair12_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR12_MODIFIED_PATHS
    )
    slice12_product_repair13_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR13_MODIFIED_PATHS
    )
    slice12_mechanical_repair3_allowlist = set(
        PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS
    )
    slice12_mechanical_repair4_allowlist = set(
        PHASE54_SLICE12_MECHANICAL_REPAIR4_MODIFIED_PATHS
    )
    slice12_product_repair14_allowlist = set(
        PHASE54_SLICE12_PRODUCT_REPAIR14_MODIFIED_PATHS
    )
    recovery_allowlist = set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS)
    python313_repair_allowlist = set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS)
    interlude_allowlist = interlude_expected_allowlist
    assert dirty in (
        set(),
        active_allowlist,
        phase55_active_allowlist,
        phase55_slice2_allowlist,
        repair_allowlist,
        slice12_repair_allowlist,
        slice12_product_repair3_allowlist,
        slice12_product_repair10_allowlist,
        slice12_product_repair11_allowlist,
        slice12_product_repair12_allowlist,
        slice12_product_repair13_allowlist,
        slice12_mechanical_repair4_allowlist,
        slice12_mechanical_repair3_allowlist,
        slice12_product_repair14_allowlist,
        recovery_allowlist,
        python313_repair_allowlist,
        interlude_allowlist,
    )
    if dirty == interlude_allowlist:
        assert interlude_active
    elif dirty == python313_repair_allowlist:
        assert python313_repair_active
    elif dirty == recovery_allowlist:
        assert recovery_gate2_active
    elif dirty == slice12_repair_allowlist:
        assert slice12_repair_gate2_active
    elif dirty == slice12_product_repair3_allowlist:
        assert slice12_product_repair3_active
    elif dirty == slice12_mechanical_repair4_allowlist:
        assert slice12_mechanical_repair4_active
        assert _git_output(["branch", "--show-current"]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR4_BRANCH
        )
        assert _git_output(["rev-parse", "HEAD"]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR4_BASE
        )
    elif dirty == slice12_mechanical_repair3_allowlist:
        assert slice12_mechanical_repair3_active
        assert _git_output(["branch", "--show-current"]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR3_BRANCH
        )
        assert _git_output(["rev-parse", "HEAD"]) == (
            PHASE54_SLICE12_MECHANICAL_REPAIR3_BASE
        )
    elif dirty == slice12_product_repair14_allowlist:
        assert slice12_product_repair14_active
        assert _git_output(["branch", "--show-current"]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR14_BRANCH
        )
        assert _git_output(["rev-parse", "HEAD"]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR14_BASE
        )
    elif dirty == slice12_product_repair13_allowlist:
        assert slice12_product_repair13_active
    elif dirty == slice12_product_repair12_allowlist:
        assert slice12_product_repair12_active
    elif dirty == slice12_product_repair11_allowlist:
        assert slice12_product_repair11_active
    elif dirty == slice12_product_repair10_allowlist:
        assert slice12_product_repair10_active
    elif dirty == repair_allowlist:
        assert repair_gate2_active
    elif dirty == phase55_active_allowlist:
        assert gate2_active
    elif dirty == phase55_slice2_allowlist:
        assert gate2_active
    elif dirty:
        assert gate2_active
        assert dirty == active_allowlist
    else:
        assert gate2_active is (
            slice12_mechanical_repair4_clean_topic_active
            or slice12_mechanical_repair3_clean_topic_active
            or slice12_product_repair3_clean_topic_active
            or slice12_product_repair10_clean_topic_active
            or slice12_product_repair11_clean_topic_active
            or slice12_product_repair12_clean_topic_active
            or slice12_product_repair13_clean_topic_active
            or slice12_product_repair14_clean_topic_active
        )
