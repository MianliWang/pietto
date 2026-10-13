from __future__ import annotations

from pathlib import Path

import _pietto_project_explain_runtime as runtime_fixture

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
    PackageGraphOutcome,
    PackageGraphSnapshot,
    _build_package_graph,
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
