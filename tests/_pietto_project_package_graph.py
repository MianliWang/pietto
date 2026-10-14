from __future__ import annotations

from pathlib import Path


from pietto._project.package_graph import (
    PackageGraphDependency,
    PackageGraphDependencyRef,
    PackageGraphPackage,
    PackageGraphPackageRef,
    PackageGraphScope,
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
    "PackageGraphModuleRef",
    "PackageGraphDeclarationRef",
    "PackageGraphModule",
    "PackageGraphDeclaration",
    "PackageGraphSemanticAuthority",
    "PackageGraphFieldRef",
    "PackageGraphLetRef",
    "PackageGraphNamedWindowRef",
    "PackageGraphField",
    "PackageGraphLetBinding",
    "PackageGraphNamedWindow",
    "PackageGraphWindowSemanticProvenance",
    "PackageGraphSourceLineage",
    "PackageGraphProjectionLineage",
    "PackageGraphExpressionLineageKind",
    "PackageGraphExpressionLineage",
    "PackageGraphCurrentWindowLineage",
    "PackageGraphRelationLineageState",
    "PackageGraphLetLineageState",
    "PackageGraphAggregateLineageState",
    "PackageGraphExpressionLineageState",
    "PackageGraphCurrentWindowLineageState",
    "PackageGraphCapabilityEvaluationRef",
    "PackageGraphCatalogEvidenceRef",
    "PackageGraphCapabilityEvaluation",
    "PackageGraphCatalogEvidence",
    "PackageGraphSnapshot",
    "PackageGraphOutcome",
    "PackageGraphResult",
    "PackageGraphDirectProvenanceStep",
    "PackageGraphProvenancePath",
    "PackageGraphWhyNot",
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
