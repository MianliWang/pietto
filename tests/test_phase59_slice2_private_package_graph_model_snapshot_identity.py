from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
import runpy
from typing import cast

import pytest

import pietto
import pietto._project as project_package
from pietto._project.model import ProjectDiscoveryError, ProjectDiscoveryErrorKind
from pietto._project.package_graph import (
    PackageGraphCapabilityEvaluation,
    PackageGraphCapabilityEvaluationRef,
    PackageGraphCatalogEvidence,
    PackageGraphCatalogEvidenceRef,
    PackageGraphDependency,
    PackageGraphDependencyRef,
    PackageGraphOutcome,
    PackageGraphPackage,
    PackageGraphPackageRef,
    PackageGraphResult,
    PackageGraphScope,
    PackageGraphSnapshot,
)
from pietto._project.package_inspection import PackageInspectionPackageRole
from pietto._project.package_load_plan import (
    DependencyLocatorKind,
    PackageDependencyOccurrence,
    PackageLoadPlanBlocker,
    PackageLoadPlanBlockerKind,
)
from pietto._project.package_manifest import (
    PackageCoordinate,
    PackageIdentity,
    PackageManifestDependency,
)
from pietto.errors import Diagnostic, Severity, SourceLocation


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "src/pietto/_project/package_graph.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase59-slice2-private-package-graph-model-snapshot-identity-v1.md"
)
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

MODEL_TYPES = (
    "PackageGraphScope",
    "PackageGraphPackageRef",
    "PackageGraphDependencyRef",
    "PackageGraphPackage",
    "PackageGraphDependency",
    "PackageGraphRequirementDeclaration",
    "PackageGraphRequirementRef",
    "PackageGraphSelectorRef",
    "PackageGraphRequirementCollection",
    "PackageGraphRequirement",
    "PackageGraphSelector",
    "PackageGraphCapabilityEvaluationRef",
    "PackageGraphCatalogEvidenceRef",
    "PackageGraphCapabilityEvaluation",
    "PackageGraphCatalogEvidence",
    "PackageGraphSnapshot",
    "PackageGraphOutcome",
    "PackageGraphResult",
)


def _package(
    scope: PackageGraphScope,
    position: int,
    *,
    namespace: str = "example",
    name: str = "package",
    version: str = "1.0.0",
    digest: str = "a" * 64,
    role: PackageInspectionPackageRole = PackageInspectionPackageRole.DEPENDENCY,
) -> PackageGraphPackage:
    return PackageGraphPackage(
        ref=PackageGraphPackageRef(scope, position),
        coordinate=PackageCoordinate(PackageIdentity(namespace, name), version),
        content_digest=digest,
        role=role,
    )


def _witness(
    position: int,
    target: PackageGraphPackage,
) -> PackageDependencyOccurrence:
    occurrence = object.__new__(PackageDependencyOccurrence)
    object.__setattr__(occurrence, "declaring_package", object())
    object.__setattr__(
        occurrence,
        "declaration",
        PackageManifestDependency(
            namespace=target.coordinate.identity.namespace,
            name=target.coordinate.identity.name,
            version=target.coordinate.exact_version,
            sha256=target.content_digest,
            path=f"deps/{position}",
        ),
    )
    object.__setattr__(occurrence, "position", position)
    object.__setattr__(occurrence, "coordinate", target.coordinate)
    object.__setattr__(occurrence, "content_digest_pin", target.content_digest)
    object.__setattr__(
        occurrence,
        "locator_kind",
        DependencyLocatorKind.LOCAL_DIRECTORY,
    )
    object.__setattr__(occurrence, "resolved_project_path", f"deps/{position}")
    return occurrence


def _dependency(
    source: PackageGraphPackage,
    target: PackageGraphPackage,
    position: int,
) -> PackageGraphDependency:
    scope = source.ref.scope
    return PackageGraphDependency(
        ref=PackageGraphDependencyRef(scope, source.ref, position),
        declaring_package=source.ref,
        resolved_package=target.ref,
        witness=_witness(position, target),
    )


def _blocker(witness: PackageDependencyOccurrence) -> PackageLoadPlanBlocker:
    blocker = object.__new__(PackageLoadPlanBlocker)
    object.__setattr__(blocker, "kind", PackageLoadPlanBlockerKind.CYCLE)
    object.__setattr__(blocker, "occurrences", (witness,))
    object.__setattr__(blocker, "location", object())
    object.__setattr__(blocker, "packages", ())
    return blocker


def _diagnostic(severity: Severity) -> Diagnostic:
    return Diagnostic(
        code="PIE-P1000",
        severity=severity,
        message="evidence",
        location=SourceLocation(path="package.pietto", line=1, column=1),
    )


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def test_runtime_scope_is_opaque_identity_and_refs_are_hashable() -> None:
    first_scope = PackageGraphScope()
    second_scope = PackageGraphScope()
    first = PackageGraphPackageRef(first_scope, 0)
    same = PackageGraphPackageRef(first_scope, 0)
    foreign = PackageGraphPackageRef(second_scope, 0)

    assert first_scope is not second_scope
    assert first_scope != second_scope
    assert repr(first_scope) == repr(second_scope) == "PackageGraphScope()"
    assert fields(PackageGraphScope) == ()
    assert first == same and hash(first) == hash(same)
    assert first != foreign
    assert len({first, same, foreign}) == 2
    dependency = PackageGraphDependencyRef(first_scope, first, 0)
    same_dependency = PackageGraphDependencyRef(first_scope, same, 0)
    foreign_dependency = PackageGraphDependencyRef(second_scope, foreign, 0)
    assert dependency == same_dependency
    assert hash(dependency) == hash(same_dependency)
    assert dependency != foreign_dependency
    assert dependency != first
    with pytest.raises((FrozenInstanceError, TypeError)):
        first_scope.value = 1  # type: ignore[attr-defined]


def test_foreign_scope_and_attached_equal_facts_do_not_merge_occurrences() -> None:
    first_scope = PackageGraphScope()
    second_scope = PackageGraphScope()
    first_package = _package(first_scope, 0)
    second_package = _package(second_scope, 0)
    first = PackageGraphSnapshot(first_scope, (first_package,), ())
    second = PackageGraphSnapshot(second_scope, (second_package,), ())

    assert first_package.coordinate == second_package.coordinate
    assert first_package.content_digest == second_package.content_digest
    assert first_package.role is second_package.role
    assert first_package.ref != second_package.ref
    assert first.package(first_package.ref) is first_package
    assert second.package(second_package.ref) is second_package
    with pytest.raises(ValueError, match="foreign snapshot"):
        first.package(second_package.ref)
    with pytest.raises(ValueError, match="foreign snapshot"):
        second.package(first_package.ref)


def test_package_positions_are_identity_and_input_order_is_not_sorted() -> None:
    scope = PackageGraphScope()
    first = _package(scope, 0, namespace="z", name="same", digest="d" * 64)
    second = _package(scope, 1, namespace="a", name="same", digest="d" * 64)
    snapshot = PackageGraphSnapshot(scope, (first, second), ())

    assert first.ref != second.ref
    assert first.content_digest == second.content_digest
    assert snapshot.packages == (first, second)
    assert tuple(
        package.coordinate.identity.namespace for package in snapshot.packages
    ) == (
        "z",
        "a",
    )
    assert snapshot.package(PackageGraphPackageRef(scope, 1)) is second
    with pytest.raises(ValueError, match="does not resolve"):
        snapshot.package(PackageGraphPackageRef(scope, 2))

    equal_scope = PackageGraphScope()
    equal_first = _package(equal_scope, 0, digest="e" * 64)
    equal_second = _package(equal_scope, 1, digest="e" * 64)
    equal_snapshot = PackageGraphSnapshot(
        equal_scope,
        (equal_first, equal_second),
        (),
    )
    assert equal_first.coordinate == equal_second.coordinate
    assert equal_first.content_digest == equal_second.content_digest
    assert equal_first.role is equal_second.role
    assert equal_first.ref != equal_second.ref
    assert equal_snapshot.package(equal_first.ref) is equal_first
    assert equal_snapshot.package(equal_second.ref) is equal_second


def test_dependency_refs_preserve_authored_parallel_links_witnesses_and_order() -> None:
    scope = PackageGraphScope()
    source = _package(scope, 0, name="source")
    target = _package(scope, 1, name="target")
    later = _dependency(source, target, 1)
    earlier = _dependency(source, target, 0)
    snapshot = PackageGraphSnapshot(
        scope,
        (source, target),
        (later, earlier),
    )

    assert type(later.ref) is PackageGraphDependencyRef
    assert type(later.resolved_package) is PackageGraphPackageRef
    assert later.ref != later.resolved_package
    assert later.ref != earlier.ref
    assert later.declaring_package == earlier.declaring_package == source.ref
    assert later.resolved_package == earlier.resolved_package == target.ref
    assert later.witness.position == 1
    assert earlier.witness.position == 0
    assert snapshot.dependencies == (later, earlier)
    assert snapshot.dependency(later.ref) is later
    assert snapshot.dependency(earlier.ref) is earlier

    foreign_scope = PackageGraphScope()
    foreign_source = _package(foreign_scope, 0, name="source")
    foreign_target = _package(foreign_scope, 1, name="target")
    foreign_link = _dependency(foreign_source, foreign_target, 1)
    PackageGraphSnapshot(
        foreign_scope,
        (foreign_source, foreign_target),
        (foreign_link,),
    )
    with pytest.raises(ValueError, match="foreign snapshot"):
        snapshot.dependency(foreign_link.ref)


def test_snapshot_rejects_wrong_domain_foreign_grafted_and_duplicate_refs() -> None:
    scope = PackageGraphScope()
    source = _package(scope, 0, name="source")
    target = _package(scope, 1, name="target")
    link = _dependency(source, target, 0)
    snapshot = PackageGraphSnapshot(scope, (source, target), (link,))

    with pytest.raises(TypeError, match="package ref"):
        snapshot.package(cast(PackageGraphPackageRef, link.ref))
    with pytest.raises(TypeError, match="dependency ref"):
        snapshot.dependency(cast(PackageGraphDependencyRef, source.ref))
    with pytest.raises(ValueError, match="not found"):
        snapshot.dependency(PackageGraphDependencyRef(scope, source.ref, 1))
    with pytest.raises(ValueError, match="at least one package"):
        PackageGraphSnapshot(scope, (), ())
    with pytest.raises(ValueError, match="dense package positions"):
        PackageGraphSnapshot(scope, (target, source), ())
    with pytest.raises(ValueError, match="unique package refs"):
        PackageGraphSnapshot(scope, (source, source), ())
    with pytest.raises(ValueError, match="unique dependency refs"):
        PackageGraphSnapshot(scope, (source, target), (link, link))

    foreign_scope = PackageGraphScope()
    foreign_source = _package(foreign_scope, 0, name="source")
    with pytest.raises(ValueError, match="same snapshot scope"):
        PackageGraphDependency(
            ref=PackageGraphDependencyRef(foreign_scope, foreign_source.ref, 0),
            declaring_package=foreign_source.ref,
            resolved_package=target.ref,
            witness=_witness(0, target),
        )

    other_target = _package(scope, 1, name="other", digest="b" * 64)
    with pytest.raises(ValueError, match="witness must resolve"):
        PackageGraphSnapshot(scope, (source, other_target), (link,))


def test_refs_and_carriers_reject_invalid_intrinsic_shapes() -> None:
    scope = PackageGraphScope()
    package_ref = PackageGraphPackageRef(scope, 0)
    target = _package(scope, 1)

    with pytest.raises(ValueError, match="non-negative"):
        PackageGraphPackageRef(scope, -1)
    with pytest.raises(ValueError, match="non-negative"):
        PackageGraphDependencyRef(scope, package_ref, -1)
    with pytest.raises(ValueError, match="same scope"):
        PackageGraphDependencyRef(PackageGraphScope(), package_ref, 0)
    with pytest.raises(ValueError, match="SHA-256"):
        _package(scope, 0, digest="not-a-digest")
    with pytest.raises(ValueError, match="authored position"):
        PackageGraphDependency(
            ref=PackageGraphDependencyRef(scope, package_ref, 1),
            declaring_package=package_ref,
            resolved_package=target.ref,
            witness=_witness(0, target),
        )


def test_result_outcomes_are_exact_and_never_carry_partial_failure_graphs() -> None:
    scope = PackageGraphScope()
    package = _package(scope, 0, role=PackageInspectionPackageRole.ROOT)
    snapshot = PackageGraphSnapshot(scope, (package,), ())
    witness = _witness(0, package)
    blocker = _blocker(witness)
    error = ProjectDiscoveryError(ProjectDiscoveryErrorKind.PROJECT_PATH, "bad")
    warning = _diagnostic(Severity.WARNING)
    error_diagnostic = _diagnostic(Severity.ERROR)

    success = PackageGraphResult(
        PackageGraphOutcome.SUCCESS,
        snapshot,
        diagnostics=(warning,),
    )
    rejected = PackageGraphResult(
        PackageGraphOutcome.REJECTED,
        blockers=(blocker,),
        diagnostics=(warning,),
    )
    failed_by_error = PackageGraphResult(PackageGraphOutcome.ERROR, errors=(error,))
    failed_by_diagnostic = PackageGraphResult(
        PackageGraphOutcome.ERROR,
        diagnostics=(error_diagnostic,),
    )

    assert success.snapshot is snapshot
    assert rejected.snapshot is failed_by_error.snapshot is None
    assert failed_by_diagnostic.snapshot is None
    for outcome, kwargs in (
        (PackageGraphOutcome.SUCCESS, {}),
        (PackageGraphOutcome.SUCCESS, {"snapshot": snapshot, "blockers": (blocker,)}),
        (PackageGraphOutcome.SUCCESS, {"snapshot": snapshot, "errors": (error,)}),
        (
            PackageGraphOutcome.SUCCESS,
            {"snapshot": snapshot, "diagnostics": (error_diagnostic,)},
        ),
        (PackageGraphOutcome.REJECTED, {}),
        (
            PackageGraphOutcome.REJECTED,
            {"snapshot": snapshot, "blockers": (blocker,)},
        ),
        (PackageGraphOutcome.REJECTED, {"blockers": (blocker,), "errors": (error,)}),
        (PackageGraphOutcome.ERROR, {}),
        (PackageGraphOutcome.ERROR, {"snapshot": snapshot, "errors": (error,)}),
        (PackageGraphOutcome.ERROR, {"blockers": (blocker,), "errors": (error,)}),
    ):
        with pytest.raises(ValueError):
            PackageGraphResult(outcome, **kwargs)


def test_model_shape_is_private_typed_and_contains_no_deferred_products() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SOURCE))
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }

    assert classes == set(MODEL_TYPES)
    assert (
        not {
            "pietto._project.package_loader",
            "pietto._project.package_locator",
            "pietto._project.package_rejection",
            "json",
            "uuid",
            "hashlib",
            "random",
            "time",
        }
        & imported_modules
    )
    assert tuple(field.name for field in fields(PackageGraphPackageRef)) == (
        "scope",
        "position",
    )
    assert tuple(field.name for field in fields(PackageGraphDependencyRef)) == (
        "scope",
        "declaring_package",
        "declaration_position",
    )
    assert tuple(field.name for field in fields(PackageGraphSnapshot)) == (
        "scope",
        "packages",
        "dependencies",
        "requirement_collections",
        "requirements",
        "selectors",
        "capability_evaluations",
        "catalog_evidence",
    )
    assert tuple(field.name for field in fields(PackageGraphResult)) == (
        "outcome",
        "snapshot",
        "blockers",
        "errors",
        "diagnostics",
    )
    assert PackageGraphOutcome.__members__ == {
        "SUCCESS": PackageGraphOutcome.SUCCESS,
        "REJECTED": PackageGraphOutcome.REJECTED,
        "ERROR": PackageGraphOutcome.ERROR,
    }
    assert project_package.__all__ == ()
    assert not any(hasattr(pietto, name) for name in MODEL_TYPES)
    assert not any(hasattr(project_package, name) for name in MODEL_TYPES)
    for carrier in (
        PackageGraphScope,
        PackageGraphPackageRef,
        PackageGraphDependencyRef,
        PackageGraphPackage,
        PackageGraphDependency,
        PackageGraphCapabilityEvaluationRef,
        PackageGraphCatalogEvidenceRef,
        PackageGraphCapabilityEvaluation,
        PackageGraphCatalogEvidence,
        PackageGraphSnapshot,
        PackageGraphResult,
    ):
        assert hasattr(carrier, "__slots__")
        assert not any(
            hasattr(carrier, name)
            for name in ("to_json", "from_json", "canonical_bytes", "digest")
        )


def test_public_project_explain_and_package_smoke_boundaries_are_structural() -> None:
    public_readers = (
        REPO_ROOT / "src/pietto/__init__.py",
        REPO_ROOT / "src/pietto/_project/__init__.py",
        REPO_ROOT / "src/pietto/cli.py",
        *(REPO_ROOT / "src/pietto/_project_explain").glob("*.py"),
    )
    for path in public_readers:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert "pietto._project.package_graph" not in imports

    smoke = runpy.run_path(str(PACKAGE_SMOKE))
    required_runtime_files = cast(object, smoke["_required_runtime_files"])
    assert callable(required_runtime_files)
    assert "pietto/_project/package_graph.py" in required_runtime_files("pietto")  # type: ignore[operator]

    smoke_tree = ast.parse(PACKAGE_SMOKE.read_text(encoding="utf-8"))
    literals = {
        node.value
        for node in ast.walk(smoke_tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "installed private Phase 59 package graph import" in literals
    assert "import pietto._project.package_graph" in literals


def test_slice2_spec_freezes_exact_model_scope_and_lifecycle() -> None:
    document = SPEC.read_text(encoding="utf-8")
    type_rows = _table(_section(document, "Typed Runtime References"))[1:]
    carrier_rows = _table(_section(document, "Occurrence Carriers"))[1:]
    result_rows = _table(_section(document, "Outcome Model"))[1:]

    assert tuple(row[0].strip("`") for row in type_rows) == (
        "PackageGraphPackageRef",
        "PackageGraphDependencyRef",
    )
    assert tuple(row[0].strip("`") for row in carrier_rows) == (
        "PackageGraphPackage",
        "PackageGraphDependency",
    )
    assert tuple(row[0].strip("`") for row in result_rows) == (
        "SUCCESS",
        "REJECTED",
        "ERROR",
    )
    scope = " ".join(_section(document, "Runtime Scope").split())
    assert "identity-equal runtime owner" in scope
    assert "no UUID, timestamp, global counter" in scope
    deferred = " ".join(_section(document, "Non-goals And Deferred Ownership").split())
    for forbidden in (
        "generic node/edge base",
        "builder, resolver, loader, planner",
        "BFS/DFS",
        "JSON, canonical bytes, graph digest",
        "future requirement/selector/evidence/module/declaration/field/lineage ref",
    ):
        assert forbidden in deferred
    lifecycle = " ".join(_section(document, "Workflow And Lifecycle").split())
    assert "Slice 2 current, Slice 3 next/unstarted" in lifecycle
    assert "unchanged 12-slice route" in lifecycle
    assert "Slice 3 remains unimplemented and unauthorized" in lifecycle
    assert "Add private Phase 59 package graph model" in document
