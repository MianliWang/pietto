from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, replace
import inspect
import json
from pathlib import Path

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_package_neutral_identity as layering
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaStatus,
    ProjectSemanticResult,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectModuleIdentity
from pietto._project.module_catalog import ProjectNominalDeclarationIdentity
from pietto._project.module_inspection import (
    _build_project_module_inspection_fact_set,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssueStatus,
    _build_project_module_relation_resolution_set,
)
from pietto._project.module_semantic_fact_preservation import (
    _build_project_module_semantic_fact_set,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice13-package-neutral-identity-layering-owner-asset-"
    "carriers-source-digest-and-loader-readiness-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_package_neutral_identity.py"
TEST_REL = "tests/test_phase54_package_neutral_identity_layering.py"

EXPECTED_TEST_NAMES = (
    "test_slice13_contract_status_active_manifest_and_allowlist_are_exact",
    "test_package_neutral_vocabulary_carriers_fields_and_privacy_are_exact",
    "test_owner_identity_rejects_package_namespace_and_named_project_root",
    "test_module_owner_identity_requires_an_exact_normalized_module_path",
    "test_source_digest_identity_requires_exact_lowercase_sha256_and_byte_count",
    "test_schema_v1_has_no_layered_sidecar_and_public_bytes_remain_exact",
    "test_schema_v2_builds_the_layered_sidecar_from_six_exact_shared_roots",
    "test_shared_authority_root_predicate_rejects_value_equal_foreign_fact_sets",
    "test_shared_authority_root_predicate_rejects_coordinated_mixed_root_products",
    "test_shared_authority_root_predicate_rejects_partial_or_misaligned_roots",
    "test_layered_authority_derives_products_and_rejects_grafted_derived_tuples",
    "test_module_asset_digest_reaches_through_its_exact_trusted_snapshot",
    "test_byte_equal_modules_share_one_digest_identity_and_stay_distinct_assets",
    "test_digest_and_module_lookups_return_complete_buckets_without_a_winner",
    "test_ready_loader_readiness_is_atomic_with_its_reason_and_empty_evidence",
    "test_module_cycle_publishes_blocked_readiness_with_exact_issue_roots",
    "test_loader_readiness_atomicity_rejects_every_mismatched_combination",
    "test_declaration_assets_share_the_exact_module_readiness_object",
    "test_concrete_relation_declaration_retains_its_exact_slice12_state",
    "test_unknown_relation_declaration_propagates_without_child_inference",
    "test_deferred_relation_declaration_propagates_without_concretization",
    "test_blocked_relation_declaration_retains_its_exact_blocked_state",
    "test_non_relation_declaration_is_absent_rather_than_unknown",
    "test_repeated_nominal_identity_is_ambiguous_and_publishes_no_winner",
    "test_loader_blocked_module_publishes_no_semantic_or_relation_product",
    "test_availability_atomicity_rejects_every_inconsistent_combination",
    "test_module_and_declaration_cardinalities_zero_one_two_three_are_complete",
    "test_module_assets_and_declaration_assets_follow_exact_authority_order",
    "test_same_spelling_declarations_in_two_modules_never_merge",
    "test_declaration_lookup_returns_complete_buckets_and_rejects_foreign_keys",
    "test_layered_fact_set_rejects_dropped_injected_reordered_or_foreign_products",
    "test_tenth_sidecar_all_or_none_boundary_is_exact_and_fail_closed",
    "test_slice11_and_slice12_products_remain_independent_and_unchanged",
    "test_layered_builder_is_pure_over_preloaded_inputs_and_performs_no_io",
    "test_schema_v2_public_api_cli_json_ir_sql_dependencies_and_goldens_unchanged",
)

_SHAPE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    category: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
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
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, sources, schema_version=schema_version)
    )
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _layered(
    semantic: ProjectSemanticResult,
) -> layering.ProjectModulePackageNeutralIdentityFactSet:
    facts = semantic.module_package_identity_facts
    assert facts is not None
    return facts


def _declaration(
    semantic: ProjectSemanticResult,
    module_path: str,
    declared_name: str,
) -> layering.ProjectLayeredDeclarationAsset:
    matches = tuple(
        asset
        for asset in _layered(semantic).declaration_assets
        if asset.identity.module_path == module_path
        and asset.identity.declared_name == declared_name
    )
    assert len(matches) == 1
    return matches[0]


def _module_asset(
    semantic: ProjectSemanticResult,
    module_path: str,
) -> layering.ProjectLayeredModuleAsset:
    matches = _layered(semantic).find_module(ProjectModuleIdentity(path=module_path))
    assert len(matches) == 1
    return matches[0]


def _build_layered(
    result: ProjectSemanticResult,
    **overrides: object,
) -> layering.ProjectModulePackageNeutralIdentityFactSet:
    parse_roots: dict[str, object] = {
        "selected_input_index": result.selected_input_index,
        "trusted_source_snapshots": result.trusted_source_snapshots,
        "modules": result.modules,
        "catalogs": result.module_catalogs,
        "attribution": result.module_attribution_facts,
        "semantic": result.module_semantic_facts,
    }
    parse_roots.update(overrides)
    return layering._build_project_module_package_neutral_identity_fact_set(
        parse_roots["selected_input_index"],  # pyright: ignore[reportArgumentType]
        parse_roots["trusted_source_snapshots"],  # pyright: ignore[reportArgumentType]
        parse_roots["modules"],  # pyright: ignore[reportArgumentType]
        parse_roots["catalogs"],  # pyright: ignore[reportArgumentType]
        parse_roots["attribution"],  # pyright: ignore[reportArgumentType]
        parse_roots["semantic"],  # pyright: ignore[reportArgumentType]
    )


def _query_module(body: str) -> str:
    return _SHAPE_PREFIX + "query result:\n    from rows\n" + body


def _cycle_sources() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    shape S\nexport:\n    shape T\nshape T:\n'
            "    id: Int\n"
        ),
        "b.pietto": (
            'import "a.pietto":\n    shape T\nexport:\n    shape S\nshape S:\n'
            "    id: Int\n"
        ),
    }


def test_slice13_contract_status_active_manifest_and_allowlist_are_exact() -> None:
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    plan = (
        REPO_ROOT / "docs/plan/phase-54-local-import-module-export-foundation.md"
    ).read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    whitepaper = (REPO_ROOT / "docs/spec/pietto-v0.9.md").read_text(encoding="utf-8")
    assert "Slice 13 is the first authorized join" in spec
    assert "shared exact-authority-root predicate" in spec
    assert "reserved empty local namespace" in spec
    assert "no loader is implemented" in spec
    assert "private module inspection or canonical serialization (Slice 14)" in spec
    assert "PHASE54_SLICE14_GATE2_COMPLETED_AWAITING_PUBLICATION" in plan
    assert "Slice 13" in readme
    assert "Current Phase 54 Completion Status" in whitepaper
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE16_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "1f69c0316086a2236cee03a96cca95218fbd50fc"
    )
    # A historical benchmark reads the frozen Slice 13 record, never the active
    # Gate 2 sets, which move with every later Slice.
    historical_added = active_gate2_manifest.PHASE54_SLICE13_HISTORICAL_ADDED_PATHS
    historical_non_reader = (
        active_gate2_manifest.PHASE54_SLICE13_HISTORICAL_NON_READER_PATHS
    )
    historical_readers = active_gate2_manifest.PHASE54_SLICE13_HISTORICAL_READER_PATHS
    historical_modified = historical_non_reader | historical_readers
    historical_allowlist = historical_added | historical_modified
    assert historical_added == {SPEC_REL, SOURCE_REL, TEST_REL}
    assert historical_non_reader == {
        "README.md",
        "docs/plan/phase-54-local-import-module-export-foundation.md",
        "docs/spec/pietto-v0.9.md",
        "src/pietto/_project/model.py",
        "tests/_phase54_active_gate2_manifest.py",
    }
    assert len(historical_readers) == 60
    assert len(historical_modified) == 65
    assert len(historical_allowlist) == 68
    assert sum(path.endswith(".py") for path in historical_allowlist) == 64
    assert not (historical_non_reader & historical_readers)
    assert not (historical_added & historical_modified)
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert "60-reader" in spec
    assert "exact 64 Python paths" in spec
    assert "exact `A3_M65_D0`" in spec
    assert active_gate2_manifest.PHASE55_ACTIVE_GATE2_MARKER == "PHASE55_SLICE1_GATE2"
    assert active_gate2_manifest.PHASE55_ACTIVE_GATE2_BASE == (
        "364296e69f7e289395661518031dafeb66a216cc"
    )
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_MODIFIED_PATHS) == 52
    assert len(active_gate2_manifest.PHASE55_ACTIVE_GATE2_ALLOWLIST_PATHS) == 55
    assert TEST_REL in active_gate2_manifest.PHASE55_ACTIVE_GATE2_READER_PATHS


def test_package_neutral_vocabulary_carriers_fields_and_privacy_are_exact() -> None:
    assert layering.__all__ == ()
    assert tuple(member.value for member in layering.ProjectLayeredOwnerKind) == (
        "local_project_root",
        "local_module",
    )
    assert tuple(member.value for member in layering.ProjectLayeredAssetKind) == (
        "module_source",
        "nominal_declaration",
    )
    assert tuple(member.value for member in layering.ProjectLayeredAvailability) == (
        "concrete",
        "unknown",
        "deferred",
        "blocked",
        "absent",
        "ambiguous",
    )
    assert tuple(member.value for member in layering.ProjectLayeredLoaderReadiness) == (
        "ready",
        "blocked",
    )
    assert tuple(
        member.value for member in layering.ProjectLayeredLoaderReadinessReason
    ) == ("trusted_local_source_resolved", "module_cycle_blocked")
    assert tuple(member.value for member in layering.ProjectLayeredDigestAlgorithm) == (
        "sha256_opened_bytes",
    )

    expected_fields = {
        layering.ProjectLayeredOwnerIdentity: ("kind", "namespace", "name"),
        layering.ProjectLayeredSourceDigestIdentity: (
            "algorithm",
            "digest",
            "byte_count",
        ),
        layering.ProjectLayeredLoaderReadinessFact: (
            "status",
            "reason",
            "blocking_issues",
        ),
        layering.ProjectLayeredModuleAsset: (
            "owner",
            "asset_kind",
            "module",
            "position",
            "digest",
            "readiness",
            "selected_input",
            "snapshot",
            "readiness_authority",
        ),
        layering.ProjectLayeredDeclarationAsset: (
            "owner",
            "asset_kind",
            "identity",
            "occurrence",
            "identity_occurrences",
            "attribution",
            "semantic_facts",
            "readiness",
            "availability",
            "relation_state",
            "declaration_position",
            "identity_bucket_authority",
            "readiness_authority",
        ),
    }
    for carrier, names in expected_fields.items():
        assert tuple(item.name for item in fields(carrier)) == names
        parameters = inspect.signature(carrier).parameters
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in parameters.values()
        )
        assert carrier.__dataclass_params__.frozen
        assert getattr(carrier, "__slots__", None) is not None

    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    for forbidden in (
        "package_name",
        "manifest",
        "registry",
        "lockfile",
        "requests",
        "urllib",
        "socket",
        "subprocess",
    ):
        assert forbidden not in source


def test_owner_identity_rejects_package_namespace_and_named_project_root() -> None:
    root_owner = layering.ProjectLayeredOwnerIdentity(
        kind=layering.ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT,
        namespace="",
        name="",
    )
    assert root_owner.namespace == ""
    assert root_owner.name == ""
    with pytest.raises(ValueError, match="reserved empty local"):
        layering.ProjectLayeredOwnerIdentity(
            kind=layering.ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT,
            namespace="acme",
            name="",
        )
    with pytest.raises(ValueError, match="must remain unnamed"):
        layering.ProjectLayeredOwnerIdentity(
            kind=layering.ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT,
            namespace="",
            name="acme-package",
        )
    with pytest.raises(TypeError, match="exact owner kind"):
        layering.ProjectLayeredOwnerIdentity(
            kind="local_project_root",  # pyright: ignore[reportArgumentType]
            namespace="",
            name="",
        )
    with pytest.raises(FrozenInstanceError):
        root_owner.name = "acme"  # pyright: ignore[reportAttributeAccessIssue]


def test_module_owner_identity_requires_an_exact_normalized_module_path() -> None:
    owner = layering.ProjectLayeredOwnerIdentity(
        kind=layering.ProjectLayeredOwnerKind.LOCAL_MODULE,
        namespace="",
        name="lib/a.pietto",
    )
    assert owner.name == "lib/a.pietto"
    for invalid in ("", "/abs.pietto", "../a.pietto", "a.txt", "a.pietto/"):
        with pytest.raises(ValueError):
            layering.ProjectLayeredOwnerIdentity(
                kind=layering.ProjectLayeredOwnerKind.LOCAL_MODULE,
                namespace="",
                name=invalid,
            )
    assert owner != layering.ProjectLayeredOwnerIdentity(
        kind=layering.ProjectLayeredOwnerKind.LOCAL_MODULE,
        namespace="",
        name="lib/b.pietto",
    )


def test_source_digest_identity_requires_exact_lowercase_sha256_and_byte_count() -> (
    None
):
    digest = layering.ProjectLayeredSourceDigestIdentity(
        algorithm=layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES,
        digest="0" * 64,
        byte_count=0,
    )
    assert digest.byte_count == 0
    for invalid_digest in ("0" * 63, "0" * 65, "A" * 64, "g" * 64, ""):
        with pytest.raises(ValueError, match="lowercase hexadecimal"):
            layering.ProjectLayeredSourceDigestIdentity(
                algorithm=(layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES),
                digest=invalid_digest,
                byte_count=1,
            )
    with pytest.raises(ValueError, match="non-negative"):
        layering.ProjectLayeredSourceDigestIdentity(
            algorithm=layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES,
            digest="0" * 64,
            byte_count=-1,
        )
    with pytest.raises(TypeError, match="exact algorithm"):
        layering.ProjectLayeredSourceDigestIdentity(
            algorithm="sha256_opened_bytes",  # pyright: ignore[reportArgumentType]
            digest="0" * 64,
            byte_count=1,
        )


def test_schema_v1_has_no_layered_sidecar_and_public_bytes_remain_exact(
    tmp_path: Path,
) -> None:
    legacy_parse, legacy_semantic = _semantic_project(
        tmp_path / "legacy",
        {"main.pietto": _query_module("    select:\n        id\n")},
        schema_version=1,
    )
    assert legacy_semantic.module_package_identity_facts is None
    assert legacy_semantic.module_attribution_facts is None
    assert legacy_semantic.module_semantic_facts is None
    assert legacy_semantic.model is not None
    payload = json.dumps(
        project_check_result_to_json_dict(legacy_parse), sort_keys=True
    )
    assert "package_identity" not in payload
    assert "layered" not in payload
    assert "digest" not in payload
    with pytest.raises(ValueError, match="forbid module sidecars"):
        replace(
            legacy_semantic,
            module_package_identity_facts=object(),  # pyright: ignore[reportArgumentType]
        )


def test_schema_v2_builds_the_layered_sidecar_from_six_exact_shared_roots(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    facts = _layered(semantic)
    authority = facts.authority
    assert authority.selected_input_index is semantic.selected_input_index
    assert authority.trusted_source_snapshots is semantic.trusted_source_snapshots
    assert authority.modules is semantic.modules
    assert authority.catalogs is semantic.module_catalogs
    assert authority.attribution is semantic.module_attribution_facts
    assert authority.semantic is semantic.module_semantic_facts
    assert facts.owner is authority.owner
    assert facts.module_assets is authority.module_assets
    assert facts.declaration_assets is authority.declaration_assets
    assert facts.owner.kind is layering.ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT
    assert len(facts.module_assets) == 1
    assert len(facts.declaration_assets) == 3
    assert all(
        asset.asset_kind is layering.ProjectLayeredAssetKind.MODULE_SOURCE
        for asset in facts.module_assets
    )
    assert all(
        asset.asset_kind is layering.ProjectLayeredAssetKind.NOMINAL_DECLARATION
        for asset in facts.declaration_assets
    )
    rebuilt = _build_layered(semantic)
    assert rebuilt.module_assets == facts.module_assets
    assert rebuilt.module_assets is not facts.module_assets


def test_shared_authority_root_predicate_rejects_value_equal_foreign_fact_sets(
    tmp_path: Path,
) -> None:
    sources = {"main.pietto": _query_module("    select:\n        id\n")}
    _, semantic = _semantic_project(tmp_path / "one", sources)
    _, foreign = _semantic_project(tmp_path / "two", sources)
    assert semantic.module_attribution_facts == foreign.module_attribution_facts
    assert semantic.module_attribution_facts is not foreign.module_attribution_facts

    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(semantic, attribution=foreign.module_attribution_facts)
    with pytest.raises(ValueError, match="exact Slice 12 module and catalog roots"):
        _build_layered(semantic, semantic=foreign.module_semantic_facts)
    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(semantic, catalogs=foreign.module_catalogs)
    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(
            semantic,
            selected_input_index=foreign.selected_input_index,
        )
    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(
            semantic,
            trusted_source_snapshots=foreign.trusted_source_snapshots,
        )


def test_shared_authority_root_predicate_rejects_coordinated_mixed_root_products(
    tmp_path: Path,
) -> None:
    sources = {"main.pietto": _query_module("    select:\n        id\n")}
    _, semantic = _semantic_project(tmp_path / "one", sources)
    _, foreign = _semantic_project(tmp_path / "two", sources)

    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(
            semantic,
            selected_input_index=foreign.selected_input_index,
            trusted_source_snapshots=foreign.trusted_source_snapshots,
            modules=foreign.modules,
            catalogs=foreign.module_catalogs,
            attribution=semantic.module_attribution_facts,
            semantic=semantic.module_semantic_facts,
        )
    with pytest.raises(ValueError, match="exact Slice 12 module and catalog roots"):
        _build_layered(
            semantic,
            selected_input_index=foreign.selected_input_index,
            trusted_source_snapshots=foreign.trusted_source_snapshots,
            modules=foreign.modules,
            catalogs=foreign.module_catalogs,
            attribution=foreign.module_attribution_facts,
            semantic=semantic.module_semantic_facts,
        )
    catalogs = semantic.module_catalogs
    exports = semantic.module_exports
    bindings = semantic.module_bindings
    graph = semantic.module_graph
    diagnostic_facts = semantic.module_diagnostic_facts
    type_source_resolutions = semantic.module_type_source_resolutions
    assert catalogs is not None
    assert exports is not None
    assert bindings is not None
    assert graph is not None
    assert diagnostic_facts is not None
    assert type_source_resolutions is not None
    rebuilt_resolutions = _build_project_module_relation_resolution_set(
        semantic.modules,
        catalogs,
        exports,
        bindings,
        graph,
        diagnostic_facts,
        type_source_resolutions,
    )
    assert rebuilt_resolutions == semantic.module_relation_resolutions
    assert rebuilt_resolutions is not semantic.module_relation_resolutions
    rebuilt_semantic_facts = _build_project_module_semantic_fact_set(
        semantic.modules,
        catalogs,
        rebuilt_resolutions,
    )
    with pytest.raises(ValueError, match="one shared exact Slice 10 relation root"):
        _build_layered(semantic, semantic=rebuilt_semantic_facts)
    every_foreign = _build_layered(
        semantic,
        selected_input_index=foreign.selected_input_index,
        trusted_source_snapshots=foreign.trusted_source_snapshots,
        modules=foreign.modules,
        catalogs=foreign.module_catalogs,
        attribution=foreign.module_attribution_facts,
        semantic=foreign.module_semantic_facts,
    )
    assert every_foreign.authority.modules is foreign.modules
    with pytest.raises(ValueError, match="both exact sidecar roots"):
        replace(semantic, module_package_identity_facts=every_foreign)
    # The eleventh sidecar anchors this one, so substituting the layered product
    # also requires the inspection product derived from that exact substitute.
    foreign_catalogs = foreign.module_catalogs
    foreign_exports = foreign.module_exports
    foreign_bindings = foreign.module_bindings
    foreign_graph = foreign.module_graph
    foreign_type_source = foreign.module_type_source_resolutions
    foreign_relations = foreign.module_relation_resolutions
    foreign_attribution = foreign.module_attribution_facts
    foreign_semantic = foreign.module_semantic_facts
    assert foreign_catalogs is not None
    assert foreign_exports is not None
    assert foreign_bindings is not None
    assert foreign_graph is not None
    assert foreign_type_source is not None
    assert foreign_relations is not None
    assert foreign_attribution is not None
    assert foreign_semantic is not None
    foreign_inspection = _build_project_module_inspection_fact_set(
        foreign.modules,
        foreign_catalogs,
        foreign_exports,
        foreign_bindings,
        foreign_graph,
        foreign_type_source,
        foreign_relations,
        foreign_attribution,
        foreign_semantic,
        every_foreign,
    )
    assert (
        replace(
            foreign,
            module_package_identity_facts=every_foreign,
            module_inspection_facts=foreign_inspection,
        ).module_package_identity_facts
        is every_foreign
    )


def test_shared_authority_root_predicate_rejects_partial_or_misaligned_roots(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _SHAPE_PREFIX,
            "b.pietto": _SHAPE_PREFIX,
        },
    )
    snapshots = semantic.trusted_source_snapshots
    modules = semantic.modules
    assert len(snapshots) == 2

    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(semantic, trusted_source_snapshots=snapshots[:1])
    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(semantic, modules=modules[:1])
    with pytest.raises(TypeError, match="exact selected-input index"):
        _build_layered(semantic, selected_input_index=None)
    with pytest.raises(TypeError, match="exact Slice 11 fact set"):
        _build_layered(semantic, attribution=None)
    with pytest.raises(TypeError, match="exact Slice 12 fact set"):
        _build_layered(semantic, semantic=None)
    with pytest.raises(TypeError, match="trusted source snapshots"):
        _build_layered(semantic, trusted_source_snapshots=list(snapshots))
    with pytest.raises(ValueError, match="exact Slice 11 input and module roots"):
        _build_layered(
            semantic,
            trusted_source_snapshots=(snapshots[1], snapshots[0], snapshots[0]),
        )
    assert len(modules) == 2


def test_layered_authority_derives_products_and_rejects_grafted_derived_tuples(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    facts = _layered(semantic)
    authority = facts.authority
    derived = {"owner", "module_assets", "declaration_assets"}
    for item in fields(authority):
        if item.name in derived:
            assert item.init is False
    # The refusal is the contract; its exception class differs across the
    # supported interpreter matrix, so only the behavior is asserted here.
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(authority, module_assets=())  # pyright: ignore[reportCallIssue]
    rebuilt = replace(authority)
    assert rebuilt.module_assets == authority.module_assets
    assert rebuilt.module_assets is not authority.module_assets
    with pytest.raises(ValueError, match="exact derived module assets"):
        replace(facts, module_assets=rebuilt.module_assets)
    with pytest.raises(ValueError, match="exact derived declaration assets"):
        replace(facts, declaration_assets=rebuilt.declaration_assets)
    with pytest.raises(ValueError, match="exact derived owner"):
        replace(facts, owner=rebuilt.owner)


def test_module_asset_digest_reaches_through_its_exact_trusted_snapshot(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    asset = _module_asset(semantic, "main.pietto")
    snapshot = semantic.trusted_source_snapshots[0]
    selected_input_index = semantic.selected_input_index
    assert selected_input_index is not None
    entry = selected_input_index.entries[0]
    assert asset.snapshot is snapshot
    assert asset.selected_input is entry
    assert snapshot.selected_input is entry
    assert asset.digest.digest == snapshot.sha256
    assert asset.digest.byte_count == snapshot.byte_count
    assert asset.digest.algorithm is (
        layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES
    )
    assert asset.position == entry.position == 0
    with pytest.raises(ValueError, match="reach through its snapshot"):
        replace(
            asset,
            digest=layering.ProjectLayeredSourceDigestIdentity(
                algorithm=(layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES),
                digest="0" * 64,
                byte_count=snapshot.byte_count,
            ),
        )
    with pytest.raises(ValueError, match="reach through its snapshot"):
        replace(
            asset,
            digest=layering.ProjectLayeredSourceDigestIdentity(
                algorithm=(layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES),
                digest=snapshot.sha256,
                byte_count=snapshot.byte_count + 1,
            ),
        )
    with pytest.raises(ValueError, match="match its selected entry"):
        replace(asset, module=ProjectModuleIdentity(path="other.pietto"))


def test_byte_equal_modules_share_one_digest_identity_and_stay_distinct_assets(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    first = _module_asset(semantic, "a.pietto")
    second = _module_asset(semantic, "b.pietto")
    assert first.digest == second.digest
    assert first.digest.digest == second.digest.digest
    assert first is not second
    assert first != second
    assert first.module != second.module
    assert _layered(semantic).find_digest(first.digest) == (first, second)


def test_digest_and_module_lookups_return_complete_buckets_without_a_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _SHAPE_PREFIX,
            "b.pietto": _SHAPE_PREFIX,
            "c.pietto": _SHAPE_PREFIX + "\n",
        },
    )
    facts = _layered(semantic)
    first = _module_asset(semantic, "a.pietto")
    third = _module_asset(semantic, "c.pietto")
    assert len(facts.find_digest(first.digest)) == 2
    assert facts.find_digest(third.digest) == (third,)
    absent = layering.ProjectLayeredSourceDigestIdentity(
        algorithm=layering.ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES,
        digest="0" * 64,
        byte_count=0,
    )
    assert facts.find_digest(absent) == ()
    assert facts.find_module(ProjectModuleIdentity(path="zzz.pietto")) == ()
    with pytest.raises(TypeError, match="module identity"):
        facts.find_module("a.pietto")  # pyright: ignore[reportArgumentType]
    with pytest.raises(TypeError, match="digest identity"):
        facts.find_digest("0" * 64)  # pyright: ignore[reportArgumentType]


def test_ready_loader_readiness_is_atomic_with_its_reason_and_empty_evidence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    readiness = _module_asset(semantic, "main.pietto").readiness
    assert readiness.status is layering.ProjectLayeredLoaderReadiness.READY
    assert readiness.reason is (
        layering.ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
    )
    assert readiness.blocking_issues == ()


def test_module_cycle_publishes_blocked_readiness_with_exact_issue_roots(
    tmp_path: Path,
) -> None:
    sources = _cycle_sources()
    sources["c.pietto"] = _SHAPE_PREFIX
    _, semantic = _semantic_project(tmp_path, sources)
    resolutions = semantic.module_relation_resolutions
    assert resolutions is not None
    cycle_issues = tuple(
        issue
        for issue in resolutions.issues
        if issue.status
        is ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
    )
    assert len(cycle_issues) == 2
    for path in ("a.pietto", "b.pietto"):
        readiness = _module_asset(semantic, path).readiness
        assert readiness.status is layering.ProjectLayeredLoaderReadiness.BLOCKED
        assert readiness.reason is (
            layering.ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED
        )
        assert len(readiness.blocking_issues) == 2
        assert all(
            any(retained is issue for issue in cycle_issues)
            for retained in readiness.blocking_issues
        )
        assert all(
            retained.module_cycle is not None
            and any(
                member.identity.path == path
                for member in retained.module_cycle.component.members
            )
            for retained in readiness.blocking_issues
        )
    healthy = _module_asset(semantic, "c.pietto").readiness
    assert healthy.status is layering.ProjectLayeredLoaderReadiness.READY

    # A second, disjoint module cycle's evidence is foreign to the first cycle's
    # modules and must not be grafted onto them.
    _, disjoint = _semantic_project(
        tmp_path / "disjoint",
        {
            "a.pietto": (
                'import "b.pietto":\n    shape S\nexport:\n    shape T\n'
                "shape T:\n    id: Int\n"
            ),
            "b.pietto": (
                'import "a.pietto":\n    shape T\nexport:\n    shape S\n'
                "shape S:\n    id: Int\n"
            ),
            "c.pietto": (
                'import "d.pietto":\n    shape V\nexport:\n    shape U\n'
                "shape U:\n    id: Int\n"
            ),
            "d.pietto": (
                'import "c.pietto":\n    shape U\nexport:\n    shape V\n'
                "shape V:\n    id: Int\n"
            ),
        },
    )
    first = _module_asset(disjoint, "a.pietto")
    other = _module_asset(disjoint, "c.pietto")
    assert first.readiness.blocking_issues != other.readiness.blocking_issues
    with pytest.raises(ValueError, match="exact derived readiness"):
        replace(first, readiness=other.readiness)
    first_declaration = _declaration(disjoint, "a.pietto", "T")
    with pytest.raises(ValueError, match="exact derived readiness"):
        replace(first_declaration, readiness=other.readiness)

    # A foreign project with the same module paths and the same cycle shape
    # produces a value-equal readiness whose evidence belongs to another
    # authority; object identity, not value, decides.
    _, foreign_cycle = _semantic_project(tmp_path / "foreigncycle", _cycle_sources())
    foreign_first = _module_asset(foreign_cycle, "a.pietto")
    local_first = _module_asset(semantic, "a.pietto")
    assert foreign_first.readiness == local_first.readiness
    assert foreign_first.readiness is not local_first.readiness
    with pytest.raises(ValueError, match="exact derived readiness"):
        replace(local_first, readiness=foreign_first.readiness)
    assert _module_asset(semantic, "a.pietto").digest.byte_count > 0

    _, referencing = _semantic_project(
        tmp_path / "referencing",
        {
            "a.pietto": (
                'import "b.pietto":\n    table Public as Local\n'
                "query result:\n    from Local\n    select:\n        id\n"
            ),
            "b.pietto": (
                'import "c.pietto":\n    table projected as Public\n'
                'import "d.pietto":\n    query D\n'
                "export:\n    table Public\n"
            ),
            "c.pietto": (
                _SHAPE_PREFIX
                + "table projected:\n    from rows\n    select:\n        id\n"
                "export:\n    table projected\n"
            ),
            "d.pietto": (
                "query D:\n    from missing\n    select:\n        id\n"
                "export:\n    query D\n"
                'import "b.pietto":\n    table Public\n'
            ),
        },
    )
    referencing_resolutions = referencing.module_relation_resolutions
    assert referencing_resolutions is not None
    assert any(
        issue.owning_module_path == "a.pietto"
        and issue.status
        is ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
        for issue in referencing_resolutions.issues
    )
    referencing_readiness = _module_asset(referencing, "a.pietto").readiness
    assert referencing_readiness.status is (
        layering.ProjectLayeredLoaderReadiness.READY
    )
    assert referencing_readiness.blocking_issues == ()
    for cyclic_path in ("b.pietto", "d.pietto"):
        cyclic = _module_asset(referencing, cyclic_path).readiness
        assert cyclic.status is layering.ProjectLayeredLoaderReadiness.BLOCKED
        assert len(cyclic.blocking_issues) == 3


def test_loader_readiness_atomicity_rejects_every_mismatched_combination(
    tmp_path: Path,
) -> None:
    sources = _cycle_sources()
    _, semantic = _semantic_project(tmp_path, sources)
    blocked = _module_asset(semantic, "a.pietto").readiness
    issue = blocked.blocking_issues[0]

    with pytest.raises(ValueError, match="forbids blocking evidence"):
        layering.ProjectLayeredLoaderReadinessFact(
            status=layering.ProjectLayeredLoaderReadiness.READY,
            reason=(
                layering.ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
            ),
            blocking_issues=(issue,),
        )
    with pytest.raises(ValueError, match="requires its exact reason"):
        layering.ProjectLayeredLoaderReadinessFact(
            status=layering.ProjectLayeredLoaderReadiness.READY,
            reason=layering.ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED,
        )
    with pytest.raises(ValueError, match="requires blocking evidence"):
        layering.ProjectLayeredLoaderReadinessFact(
            status=layering.ProjectLayeredLoaderReadiness.BLOCKED,
            reason=layering.ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED,
        )
    with pytest.raises(ValueError, match="requires its exact reason"):
        layering.ProjectLayeredLoaderReadinessFact(
            status=layering.ProjectLayeredLoaderReadiness.BLOCKED,
            reason=(
                layering.ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
            ),
            blocking_issues=(issue,),
        )
    _, unrelated = _semantic_project(
        tmp_path / "unrelated",
        {
            "main.pietto": _SHAPE_PREFIX + "query result:\n    from missing\n"
            "    select:\n        id\n"
        },
    )
    unrelated_resolutions = unrelated.module_relation_resolutions
    assert unrelated_resolutions is not None
    other_issue = unrelated_resolutions.issues[0]
    assert other_issue.status is (
        ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE
    )
    with pytest.raises(ValueError, match="exact module-cycle evidence"):
        layering.ProjectLayeredLoaderReadinessFact(
            status=layering.ProjectLayeredLoaderReadiness.BLOCKED,
            reason=layering.ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED,
            blocking_issues=(other_issue,),
        )


def test_declaration_assets_share_the_exact_module_readiness_object(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    readiness = _module_asset(semantic, "main.pietto").readiness
    assets = _layered(semantic).declaration_assets
    assert len(assets) == 3
    assert all(asset.readiness is readiness for asset in assets)
    assert all(
        asset.owner.kind is layering.ProjectLayeredOwnerKind.LOCAL_MODULE
        and asset.owner.name == "main.pietto"
        for asset in assets
    )


def test_concrete_relation_declaration_retains_its_exact_slice12_state(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    asset = _declaration(semantic, "main.pietto", "result")
    assert asset.availability is layering.ProjectLayeredAvailability.CONCRETE
    assert len(asset.semantic_facts) == 1
    fact = asset.semantic_facts[0]
    assert fact.owner is asset.occurrence
    assert asset.relation_state is fact.state
    assert fact.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert asset.attribution.occurrence is asset.occurrence
    assert asset.identity_occurrences == (asset.occurrence,)


def test_unknown_relation_declaration_propagates_without_child_inference(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        nope\n")},
    )
    asset = _declaration(semantic, "main.pietto", "result")
    assert asset.availability is layering.ProjectLayeredAvailability.UNKNOWN
    assert asset.relation_state is not None
    assert asset.relation_state.status is ProjectRelationRowSchemaStatus.UNKNOWN
    assert asset.relation_state is asset.semantic_facts[0].state
    upstream = _declaration(semantic, "main.pietto", "rows")
    assert upstream.availability is layering.ProjectLayeredAvailability.CONCRETE


def test_deferred_relation_declaration_propagates_without_concretization(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                _SHAPE_PREFIX + "query pending:\n    from rows\n    select:\n"
                "        divided = amount / 2\n"
                "query result:\n    from pending\n    select:\n        divided\n"
            )
        },
    )
    for name in ("pending", "result"):
        asset = _declaration(semantic, "main.pietto", name)
        assert asset.availability is layering.ProjectLayeredAvailability.DEFERRED
        assert asset.relation_state is not None
        assert asset.relation_state.status is ProjectRelationRowSchemaStatus.DEFERRED
        assert asset.relation_state is asset.semantic_facts[0].state


def test_blocked_relation_declaration_retains_its_exact_blocked_state(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": _SHAPE_PREFIX
            + "query result:\n    from missing\n    select:\n        id\n"
        },
    )
    asset = _declaration(semantic, "main.pietto", "result")
    assert asset.availability is layering.ProjectLayeredAvailability.BLOCKED
    assert asset.relation_state is not None
    assert asset.relation_state.status is ProjectRelationRowSchemaStatus.BLOCKED
    assert asset.readiness.status is layering.ProjectLayeredLoaderReadiness.READY


def test_non_relation_declaration_is_absent_rather_than_unknown(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    asset = _declaration(semantic, "main.pietto", "Row")
    assert asset.identity.namespace is ProjectSymbolNamespace.TYPE
    assert asset.availability is layering.ProjectLayeredAvailability.ABSENT
    assert asset.availability is not layering.ProjectLayeredAvailability.UNKNOWN
    assert asset.semantic_facts == ()
    assert asset.relation_state is None


def test_repeated_nominal_identity_is_ambiguous_and_publishes_no_winner(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "main.pietto": (
                _SHAPE_PREFIX + "table t:\n    from rows\n    select:\n        id\n"
                "table t:\n    from rows\n    select:\n        id\n"
            )
        },
    )
    facts = _layered(semantic)
    identity = ProjectNominalDeclarationIdentity(
        module_path="main.pietto",
        namespace=ProjectSymbolNamespace.RELATION,
        declaration_kind=facts.declaration_assets[2].identity.declaration_kind,
        declared_name="t",
    )
    bucket = facts.find_declaration(identity)
    assert len(bucket) == 2
    assert bucket[0].declaration_position < bucket[1].declaration_position
    for asset in bucket:
        assert asset.availability is layering.ProjectLayeredAvailability.AMBIGUOUS
        assert asset.relation_state is None
        assert len(asset.identity_occurrences) == 2
        assert len(asset.semantic_facts) == 1
    assert bucket[0].occurrence is not bucket[1].occurrence
    assert bucket[0].identity == bucket[1].identity
    # One canonical bucket is derived once and shared by every occurrence of the
    # identity rather than re-derived per declaration.
    assert bucket[0].identity_occurrences is bucket[1].identity_occurrences


def test_loader_blocked_module_publishes_no_semantic_or_relation_product(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, _cycle_sources())
    for path, name in (("a.pietto", "T"), ("b.pietto", "S")):
        asset = _declaration(semantic, path, name)
        assert asset.availability is layering.ProjectLayeredAvailability.BLOCKED
        assert asset.semantic_facts == ()
        assert asset.relation_state is None
        assert asset.readiness.status is layering.ProjectLayeredLoaderReadiness.BLOCKED
        assert asset.attribution.occurrence is asset.occurrence


def test_availability_atomicity_rejects_every_inconsistent_combination(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    relation_asset = _declaration(semantic, "main.pietto", "result")
    type_asset = _declaration(semantic, "main.pietto", "Row")

    with pytest.raises(ValueError, match="map its exact Slice 12 status"):
        replace(
            relation_asset, availability=layering.ProjectLayeredAvailability.UNKNOWN
        )
    with pytest.raises(ValueError, match="requires a repeated nominal identity"):
        replace(
            relation_asset,
            availability=layering.ProjectLayeredAvailability.AMBIGUOUS,
            relation_state=None,
        )
    relation_state = relation_asset.relation_state
    assert relation_state is not None
    with pytest.raises(ValueError, match="retain its exact Slice 12 state"):
        replace(relation_asset, relation_state=replace(relation_state))
    with pytest.raises(ValueError, match="one exact semantic fact"):
        replace(relation_asset, semantic_facts=())
    with pytest.raises(ValueError, match="no applicable relation fact"):
        replace(type_asset, availability=layering.ProjectLayeredAvailability.UNKNOWN)
    with pytest.raises(ValueError, match="publishes no relation product"):
        replace(type_asset, relation_state=relation_asset.relation_state)
    with pytest.raises(ValueError, match="exact derived bucket"):
        replace(relation_asset, identity_occurrences=(type_asset.occurrence,))
    with pytest.raises(ValueError, match="exact derived bucket"):
        replace(
            relation_asset,
            identity_occurrences=(
                *relation_asset.identity_occurrences,
                type_asset.occurrence,
            ),
            availability=layering.ProjectLayeredAvailability.AMBIGUOUS,
            relation_state=None,
        )
    with pytest.raises(ValueError, match="retain the exact occurrence"):
        replace(relation_asset, attribution=type_asset.attribution)
    with pytest.raises(ValueError, match="must be the local module"):
        replace(relation_asset, owner=_layered(semantic).owner)


def test_module_and_declaration_cardinalities_zero_one_two_three_are_complete(
    tmp_path: Path,
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir(parents=True, exist_ok=True)
    (empty_root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (empty_root / "zero.pietto").write_text("\n", encoding="utf-8")
    zero_parse = project_check.check_project_parse_only(empty_root)
    assert zero_parse.ok
    zero = build_empty_project_semantic_result(zero_parse)
    zero_facts = _layered(zero)
    assert len(zero_facts.module_assets) == 1
    assert zero_facts.declaration_assets == ()

    for count in (1, 2, 3):
        _, semantic = _semantic_project(
            tmp_path / f"count{count}",
            {
                f"m{index}.pietto": (
                    "shape Row:\n    id: Int not null\n"
                    'source rows: Row is postgres.table("rows")\n'
                )
                for index in range(count)
            },
        )
        facts = _layered(semantic)
        assert len(facts.module_assets) == count
        assert len(facts.declaration_assets) == 2 * count
        assert tuple(asset.position for asset in facts.module_assets) == tuple(
            range(count)
        )


def test_module_assets_and_declaration_assets_follow_exact_authority_order(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "b.pietto": _SHAPE_PREFIX,
            "a.pietto": _SHAPE_PREFIX + "table t:\n    from rows\n    select:\n"
            "        id\n",
        },
    )
    facts = _layered(semantic)
    assert tuple(asset.module.path for asset in facts.module_assets) == tuple(
        module.path for module in semantic.modules
    )
    catalogs = semantic.module_catalogs
    assert catalogs is not None
    expected = tuple(
        (catalog.module_path, occurrence.declaration_position)
        for catalog in catalogs.catalogs
        for occurrence in catalog.occurrences
    )
    actual = tuple(
        (asset.identity.module_path, asset.declaration_position)
        for asset in facts.declaration_assets
    )
    assert actual == expected
    attribution = semantic.module_attribution_facts
    assert attribution is not None
    assert tuple(asset.attribution for asset in facts.declaration_assets) == (
        attribution.declarations
    )


def test_same_spelling_declarations_in_two_modules_never_merge(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    first = _declaration(semantic, "a.pietto", "rows")
    second = _declaration(semantic, "b.pietto", "rows")
    assert first.identity != second.identity
    assert first.owner != second.owner
    assert first.identity_occurrences == (first.occurrence,)
    assert second.identity_occurrences == (second.occurrence,)
    facts = _layered(semantic)
    assert facts.find_declaration(first.identity) == (first,)
    assert facts.find_declaration(second.identity) == (second,)
    assert first.availability is second.availability


def test_declaration_lookup_returns_complete_buckets_and_rejects_foreign_keys(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    facts = _layered(semantic)
    absent = ProjectNominalDeclarationIdentity(
        module_path="main.pietto",
        namespace=ProjectSymbolNamespace.RELATION,
        declaration_kind=facts.declaration_assets[1].identity.declaration_kind,
        declared_name="absent_relation",
    )
    assert facts.find_declaration(absent) == ()
    with pytest.raises(TypeError, match="nominal identity"):
        facts.find_declaration("rows")  # pyright: ignore[reportArgumentType]
    for asset in facts.declaration_assets:
        assert facts.find_declaration(asset.identity) == (asset,)


def test_layered_fact_set_rejects_dropped_injected_reordered_or_foreign_products(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _SHAPE_PREFIX, "b.pietto": _SHAPE_PREFIX},
    )
    facts = _layered(semantic)
    module_assets = facts.module_assets
    declaration_assets = facts.declaration_assets
    for invalid in (
        (),
        module_assets[:1],
        (module_assets[0], *module_assets),
        tuple(reversed(module_assets)),
    ):
        with pytest.raises(ValueError, match="exact derived module assets"):
            replace(facts, module_assets=invalid)
    for invalid in (
        (),
        declaration_assets[:1],
        tuple(reversed(declaration_assets)),
    ):
        with pytest.raises(ValueError, match="exact derived declaration assets"):
            replace(facts, declaration_assets=invalid)
    with pytest.raises(TypeError, match="exact private authority"):
        replace(facts, authority=None)

    # A coordinated graft forges an asset together with the validation mappings
    # it was handed; the fact set anchors the whole set to this authority.
    from types import MappingProxyType

    forged_readiness = MappingProxyType(dict(facts.authority.readiness_projection))
    forged_module = replace(module_assets[0], readiness_authority=forged_readiness)
    assert forged_module.readiness_authority is not (
        facts.authority.readiness_projection
    )
    with pytest.raises(ValueError, match="exact derived module assets"):
        replace(facts, module_assets=(forged_module, *module_assets[1:]))
    forged_buckets = MappingProxyType(dict(facts.authority.identity_bucket_projection))
    forged_declaration = replace(
        declaration_assets[0], identity_bucket_authority=forged_buckets
    )
    assert forged_declaration.identity_bucket_authority is not (
        facts.authority.identity_bucket_projection
    )
    with pytest.raises(ValueError, match="exact derived declaration assets"):
        replace(
            facts,
            declaration_assets=(forged_declaration, *declaration_assets[1:]),
        )


def test_tenth_sidecar_all_or_none_boundary_is_exact_and_fail_closed(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    sidecar_names = (
        "module_catalogs",
        "module_exports",
        "module_bindings",
        "module_graph",
        "module_diagnostic_facts",
        "module_type_source_resolutions",
        "module_relation_resolutions",
        "module_semantic_facts",
        "module_attribution_facts",
        "module_package_identity_facts",
        "module_inspection_facts",
    )
    assert len(sidecar_names) == 11
    assert all(getattr(semantic, name) is not None for name in sidecar_names)
    for name in sidecar_names:
        with pytest.raises(ValueError, match="require all module sidecars"):
            replace(semantic, **{name: None})
    empty = replace(semantic, **{name: None for name in sidecar_names}, diagnostics=())
    assert empty.module_package_identity_facts is None
    with pytest.raises(TypeError, match="exact layered fact set"):
        replace(
            semantic,
            module_package_identity_facts=object(),  # pyright: ignore[reportArgumentType]
        )


def test_slice11_and_slice12_products_remain_independent_and_unchanged(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    attribution = semantic.module_attribution_facts
    preservation = semantic.module_semantic_facts
    assert attribution is not None
    assert preservation is not None
    assert attribution._authority.catalogs is preservation.authority.catalogs
    assert not hasattr(attribution, "module_package_identity_facts")
    assert not hasattr(preservation, "module_package_identity_facts")
    attribution_source = (
        REPO_ROOT / "src/pietto/_project/module_attribution.py"
    ).read_text(encoding="utf-8")
    preservation_source = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    ).read_text(encoding="utf-8")
    assert "module_package_neutral_identity" not in attribution_source
    assert "module_package_neutral_identity" not in preservation_source
    facts = _layered(semantic)
    assert all(
        any(fact.owner is asset.occurrence for fact in asset.semantic_facts)
        or asset.semantic_facts == ()
        for asset in facts.declaration_assets
    )


def test_layered_builder_is_pure_over_preloaded_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )

    def _forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("Slice 13 performs no input or output operation.")

    monkeypatch.setattr("builtins.open", _forbidden)
    monkeypatch.setattr("pathlib.Path.open", _forbidden)
    monkeypatch.setattr("pathlib.Path.read_text", _forbidden)
    monkeypatch.setattr("pathlib.Path.read_bytes", _forbidden)
    monkeypatch.setattr("os.stat", _forbidden)
    monkeypatch.setattr("os.open", _forbidden)
    first = _build_layered(semantic)
    second = _build_layered(semantic)
    assert first.module_assets == second.module_assets
    assert first.declaration_assets == second.declaration_assets
    assert first.owner == second.owner


def test_schema_v2_public_api_cli_json_ir_sql_dependencies_and_goldens_unchanged(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"main.pietto": _query_module("    select:\n        id\n")},
    )
    assert semantic.model is None
    encoded = json.dumps(
        project_check_result_to_json_dict(parse_result), sort_keys=True
    )
    for forbidden in (
        "module_package_identity_facts",
        "package_neutral",
        "layered",
        "owner_kind",
        "asset_kind",
        "sha256",
    ):
        assert forbidden not in encoded
    project_init = (REPO_ROOT / "src/pietto/_project/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "module_package_neutral_identity" not in project_init
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    actual = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert actual == EXPECTED_TEST_NAMES
    assert len(EXPECTED_TEST_NAMES) == 35
    assert all(
        not node.decorator_list
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
