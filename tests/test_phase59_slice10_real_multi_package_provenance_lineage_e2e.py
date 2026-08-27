from __future__ import annotations

import inspect
from pathlib import Path

import test_phase58_slice13_project_explain_runtime_builder as runtime_fixture

import pietto._project.check as project_check
import pietto._project_explain.runtime_builder as runtime_builder
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    build_package_capability_checking_matrix,
)
from pietto._project.config import load_project_config
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_package_neutral_identity import (
    ProjectModulePackageNeutralIdentityFactSet,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_graph import (
    PackageGraphExpressionLineageKind,
    PackageGraphOutcome,
    PackageGraphSnapshot,
    _build_package_graph,
    _derive_package_graph_provenance_paths,
    _derive_package_graph_why_not,
    _package_graph_direct_provenance_steps,
)
from pietto._project.package_graph_inspection import (
    PackageGraphInspectionLinkKind,
    _inspect_package_graph,
    _inspection_ref,
    _query_package_graph_direct_downstream,
    _query_package_graph_direct_upstream,
    _query_package_graph_paths,
    _query_package_graph_why_not,
    _validate_package_graph_integrity,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import (
    LoadedPackage,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.project_capability_environment import (
    _build_project_capability_environment,
)
from pietto._project_explain.runtime_builder import ProjectExplainRuntimeOutcome
from pietto.semantic.capability_facts import CapabilityDomain


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase59-slice10-real-multi-package-provenance-lineage-e2e-v1.md"
)

MODULE_SOURCE = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    quantity: Int not null\n"
    "    category: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
    "query projections:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        renamed = amount\n"
    "query calculations:\n"
    "    from rows\n"
    "    let:\n"
    "        gross = amount * quantity\n"
    "    select:\n"
    "        doubled = amount + amount\n"
    "        gross\n"
    "query aggregates:\n"
    "    from rows\n"
    "    select:\n"
    "        total = sum(amount + amount)\n"
    "query windows:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        previous = lag(amount, 2, amount) window:\n"
    "            partition by:\n"
    "                category\n"
    "            order by:\n"
    "                id desc\n"
).encode()


def _write_semantic_config(package_root: Path) -> None:
    (package_root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )


def _write_real_project(tmp_path: Path, name: str) -> Path:
    project = tmp_path / name
    dependency_manifest = runtime_fixture._manifest(
        3,
        namespace="example",
        name="dependency",
        requirements=(
            runtime_fixture.EXTENSION_REQUIREMENT,
            runtime_fixture.LOGICAL_REQUIREMENT,
        ),
        selectors=(runtime_fixture.EXTENSION_SELECTOR,),
    )
    dependency_digest = runtime_fixture._write_package(
        project / "dependency",
        dependency_manifest,
        MODULE_SOURCE,
    )
    root_manifest = runtime_fixture._manifest(
        1,
        dependencies=(
            (
                "example",
                "dependency",
                "1.0.0",
                dependency_digest,
                "../dependency",
            ),
        ),
    )
    root_digest = runtime_fixture._write_package(
        project / "root",
        root_manifest,
        MODULE_SOURCE,
    )
    _write_semantic_config(project / "dependency")
    _write_semantic_config(project / "root")
    (project / "pietto.toml").write_text(
        runtime_fixture._project_config("root", root_digest, targets=True),
        encoding="utf-8",
    )
    return project


def _semantic_authority(
    package_root: Path,
) -> ProjectModulePackageNeutralIdentityFactSet:
    parse_result = project_check.check_project_parse_only(package_root)
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
    authority = semantic.module_package_identity_facts
    assert authority is not None
    return authority


def _real_graph(
    project_root: Path,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
    PackageGraphSnapshot,
]:
    config_result = load_project_config(project_root)
    assert config_result.ok and config_result.config is not None
    assert config_result.root is not None and config_result.pinned_root is not None
    activation = config_result.config.root_package
    assert activation is not None
    location = _locate_root_package(config_result.pinned_root, activation)
    assert location.ok and type(location.located_root) is LocatedRootPackage
    loaded = _load_root_package(location.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    plan = _build_package_load_plan(loaded.loaded_package)
    package_facts = _build_package_inspection_fact_set(plan)
    assert package_facts.inspection.outcome is PackageInspectionOutcome.SUCCESS

    environment_result = _build_project_capability_environment(
        config_result.root,
        config_result.config,
    )
    assert environment_result.ok and environment_result.environment is not None
    environment = environment_result.environment
    packages: tuple[LoadedPackage, ...] = tuple(
        package.entry.package for package in package_facts.inspection.packages
    )
    bindings = tuple(
        _package_capability_requirement_binding(package) for package in packages
    )
    selectors = tuple(
        _package_extension_signature_requirement_selectors(package, binding)
        for package, binding in zip(packages, bindings, strict=True)
    )
    contexts: list[tuple[CapabilityCheckingTargetContext, ...]] = []
    for package_position, (binding, package_selectors) in enumerate(
        zip(bindings, selectors, strict=True)
    ):
        package_contexts, diagnostics = runtime_builder._package_contexts(
            package_position,
            binding,
            package_selectors,
            environment,
        )
        assert diagnostics == ()
        contexts.append(package_contexts)
    matrices = tuple(
        build_package_capability_checking_matrix(package, binding, package_contexts)
        for package, binding, package_contexts in zip(
            packages,
            bindings,
            contexts,
            strict=True,
        )
    )
    capability_facts = tuple(build_capability_inspection(matrix) for matrix in matrices)
    catalog_facts = runtime_builder._extension_catalog_fact_slots(matrices)
    semantic_facts = tuple(
        _semantic_authority(project_root / package.project_path)
        for package in package_facts.inspection.packages
    )
    result = _build_package_graph(
        package_facts,
        capability_facts=capability_facts,
        extension_catalog_facts=catalog_facts,
        module_identity_facts=semantic_facts,
    )
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return package_facts, capability_facts, result.snapshot


def test_real_authored_multi_package_chain_preserves_exact_ownership_and_identity(
    tmp_path: Path,
) -> None:
    project = _write_real_project(tmp_path, "ownership")
    package_facts, _capabilities, snapshot = _real_graph(project)

    assert tuple(package.coordinate.identity.name for package in snapshot.packages) == (
        "dependency",
        "root",
    )
    assert tuple(package.ref.position for package in snapshot.packages) == (0, 1)
    dependency = snapshot.dependencies[0]
    assert dependency.witness is (
        package_facts.inspection.packages[1].dependencies[0].edge.occurrence
    )
    assert dependency.declaring_package == snapshot.packages[1].ref
    assert dependency.resolved_package == snapshot.packages[0].ref
    assert snapshot.package(dependency.resolved_package).coordinate == (
        dependency.witness.coordinate
    )

    dependency_module, root_module = snapshot.modules
    assert dependency_module.witness.identity == root_module.witness.identity
    assert dependency_module.ref != root_module.ref
    assert dependency_module.package != root_module.package
    projection_declarations = tuple(
        item for item in snapshot.declarations if item.witness.name == "projections"
    )
    assert tuple(
        (item.ref.module.package.position, item.witness.name)
        for item in projection_declarations
    ) == ((0, "projections"), (1, "projections"))
    projection_refs = tuple(item.ref for item in projection_declarations)
    projection_fields = tuple(
        field
        for field in snapshot.fields
        if field.name == "id" and field.declaration in projection_refs
    )
    assert len(projection_fields) == 2
    assert projection_fields[0].ref != projection_fields[1].ref
    assert tuple(
        field.ref.declaration.module.package.position for field in projection_fields
    ) == (0, 1)
    for field in snapshot.fields:
        assert snapshot.field(field.ref) is field
        declaration = snapshot.declaration(field.declaration)
        module = snapshot.module(declaration.module)
        assert (
            snapshot.package(module.package).ref == field.ref.declaration.module.package
        )


def test_real_requirement_selector_capability_catalog_and_why_not_provenance(
    tmp_path: Path,
) -> None:
    project = _write_real_project(tmp_path, "capability")
    _packages, _capabilities, snapshot = _real_graph(project)
    dependency = snapshot.packages[0].ref
    root = snapshot.packages[1].ref
    extension_requirement = next(
        item
        for item in snapshot.requirements
        if item.witness.key.domain is CapabilityDomain.EXTENSION_SIGNATURE
    )
    logical_requirement = next(
        item
        for item in snapshot.requirements
        if item.witness.key.domain is CapabilityDomain.LOGICAL_TYPE
    )
    selector = next(
        item
        for item in snapshot.selectors
        if item.requirement == extension_requirement.ref
    )
    extension_evaluation = next(
        item
        for item in snapshot.capability_evaluations
        if item.ref.requirement == extension_requirement.ref
    )
    catalog = next(
        item
        for item in snapshot.catalog_evidence
        if item.capability == extension_evaluation.ref
    )
    logical_evaluation = next(
        item
        for item in snapshot.capability_evaluations
        if item.ref.requirement == logical_requirement.ref
    )

    direct_witnesses = tuple(
        step.witness for step in _package_graph_direct_provenance_steps(snapshot)
    )
    for witness in (
        extension_requirement,
        selector,
        extension_evaluation,
        catalog,
    ):
        assert any(item is witness for item in direct_witnesses)
    paths = _derive_package_graph_provenance_paths(snapshot, dependency, catalog.ref)
    assert len(paths) == 1
    assert tuple(step.witness for step in paths[0].steps) == (
        extension_requirement,
        selector,
        extension_evaluation,
        catalog,
    )
    root_paths = _derive_package_graph_provenance_paths(snapshot, root, catalog.ref)
    assert len(root_paths) == 1
    assert root_paths[0].steps[0].witness is snapshot.dependencies[0]

    why_not = _derive_package_graph_why_not(
        snapshot,
        dependency,
        logical_evaluation.ref,
    )
    assert why_not
    assert all(
        item.terminal_evidence is logical_evaluation.evidence for item in why_not
    )
    assert (
        _derive_package_graph_why_not(
            snapshot,
            dependency,
            extension_evaluation.ref,
        )
        == ()
    )


def test_real_semantic_lineage_queries_integrity_and_package_islands(
    tmp_path: Path,
) -> None:
    project = _write_real_project(tmp_path, "lineage")
    _packages, _capabilities, snapshot = _real_graph(project)
    _validate_package_graph_integrity(snapshot)

    assert snapshot.source_lineage
    assert {item.kind.value for item in snapshot.projection_lineage} == {
        "direct",
        "renamed",
    }
    expression_kinds = {item.kind for item in snapshot.expression_lineage}
    assert {
        PackageGraphExpressionLineageKind.COMPUTED,
        PackageGraphExpressionLineageKind.LET_OUTPUT,
        PackageGraphExpressionLineageKind.LET_EXPRESSION,
        PackageGraphExpressionLineageKind.AGGREGATE,
    } <= expression_kinds
    assert snapshot.current_window_lineage
    repeated = tuple(
        item
        for item in snapshot.expression_lineage
        if item.kind
        in {
            PackageGraphExpressionLineageKind.COMPUTED,
            PackageGraphExpressionLineageKind.AGGREGATE,
        }
        and item.output.declaration.module.package.position == 0
    )
    repeated_pairs = tuple(
        (left, right)
        for position, left in enumerate(repeated)
        for right in repeated[position + 1 :]
        if left.output == right.output and left.upstream == right.upstream
    )
    assert repeated_pairs
    assert all(
        left.input_position != right.input_position for left, right in repeated_pairs
    )

    inspection = _inspect_package_graph(snapshot)
    expression_links = tuple(
        link
        for link in inspection.links
        if link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
    )
    output = expression_links[0].source
    upstream = expression_links[0].target
    assert _query_package_graph_direct_upstream(inspection, output)
    assert _query_package_graph_direct_downstream(inspection, upstream)
    dependency_package = _inspection_ref(snapshot.packages[0].ref)
    paths = _query_package_graph_paths(inspection, dependency_package, upstream)
    assert paths
    assert any(
        any(
            link.kind is PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE
            for link in path.links
        )
        for path in paths
    )
    assert all(
        link.source.positions[0] == link.target.positions[0]
        for link in inspection.links
        if link.kind
        in {
            PackageGraphInspectionLinkKind.SOURCE_LINEAGE,
            PackageGraphInspectionLinkKind.PROJECTION_LINEAGE,
            PackageGraphInspectionLinkKind.EXPRESSION_LINEAGE,
            PackageGraphInspectionLinkKind.CURRENT_WINDOW_LINEAGE,
        }
    )

    logical_evaluation = next(
        item
        for item in snapshot.capability_evaluations
        if item.ref.requirement.position == 1
    )
    assert _query_package_graph_why_not(
        inspection,
        dependency_package,
        _inspection_ref(logical_evaluation.ref),
    )


def test_repeated_real_authored_builds_are_scope_distinct_and_canonically_equal(
    tmp_path: Path,
) -> None:
    first_project = _write_real_project(tmp_path, "first")
    second_project = _write_real_project(tmp_path, "second")
    _first_packages, _first_capabilities, first = _real_graph(first_project)
    _second_packages, _second_capabilities, second = _real_graph(second_project)

    assert first.scope is not second.scope
    assert tuple(package.ref for package in first.packages) != tuple(
        package.ref for package in second.packages
    )
    first_inspection = _inspect_package_graph(first)
    second_inspection = _inspect_package_graph(second)
    assert first_inspection == second_inspection
    assert first_inspection.canonical_bytes == second_inspection.canonical_bytes
    assert repr(first.scope).encode() not in first_inspection.canonical_bytes
    assert str(id(first.scope)).encode() not in first_inspection.canonical_bytes


def test_real_project_explain_stays_successful_and_principal_graph_is_not_hand_built(
    tmp_path: Path,
) -> None:
    project = _write_real_project(tmp_path, "public-zero-delta")
    result = runtime_builder._build_project_explain_runtime(project)
    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    assert result.envelope.ok and result.envelope.payload is not None
    assert result.envelope.payload.package_requirements.requirements

    helper = inspect.getsource(_real_graph) + inspect.getsource(_semantic_authority)
    for forbidden in (
        "PackageGraphSnapshot(",
        "PackageGraphPackage(",
        "PackageGraphModule(",
        "PackageGraphField(",
        "PackageGraphExpressionLineage(",
        "object.__new__",
    ):
        assert forbidden not in helper
    for required in (
        "load_project_config",
        "_locate_root_package",
        "_load_root_package",
        "_build_package_load_plan",
        "_build_package_inspection_fact_set",
        "_build_project_capability_environment",
        "build_package_capability_checking_matrix",
        "build_capability_inspection",
        "check_project_parse_only",
        "build_empty_project_semantic_result",
        "_build_package_graph",
    ):
        assert required in helper


def test_slice10_spec_and_lifecycle_freeze_real_e2e_without_later_behavior() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "real authored project/package/module inputs",
        "no final PackageGraphSnapshot is hand-built",
        "source, direct, renamed, computed, let, aggregate, and current-window",
        "real typed why-not",
        "package dependency grants no semantic visibility",
        "Project Explain v1 and CLI remain zero-delta",
        "Slice 10 current",
        "Slice 11 next/unstarted",
        "Add Phase 59 real multi-package E2E",
    ):
        assert required in normalized
