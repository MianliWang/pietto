from __future__ import annotations

from dataclasses import fields

import pietto
import pietto._project as project_package
import pietto._project.package_graph as graph
import pietto._project.package_graph_inspection as graph_inspection


def test_identity_domains_and_private_snapshot_boundary_remain_exact() -> None:
    expected_ref_fields = {
        graph.PackageGraphPackageRef: ("scope", "position"),
        graph.PackageGraphDependencyRef: (
            "scope",
            "declaring_package",
            "declaration_position",
        ),
        graph.PackageGraphRequirementRef: ("scope", "package", "position"),
        graph.PackageGraphSelectorRef: ("scope", "package", "position"),
        graph.PackageGraphCapabilityEvaluationRef: (
            "scope",
            "requirement",
            "target_position",
        ),
        graph.PackageGraphCatalogEvidenceRef: (
            "scope",
            "selector",
            "target_position",
        ),
        graph.PackageGraphModuleRef: ("scope", "package", "position"),
        graph.PackageGraphDeclarationRef: ("scope", "module", "position"),
        graph.PackageGraphFieldRef: ("scope", "declaration", "position"),
        graph.PackageGraphLetRef: ("scope", "declaration", "position"),
        graph.PackageGraphNamedWindowRef: ("scope", "declaration", "position"),
    }
    assert all(
        tuple(field.name for field in fields(carrier)) == expected
        for carrier, expected in expected_ref_fields.items()
    )
    assert graph.PackageGraphScope() != graph.PackageGraphScope()
    assert tuple(field.name for field in fields(graph.PackageGraphPackage)) == (
        "ref",
        "coordinate",
        "content_digest",
        "role",
    )
    assert tuple(field.name for field in fields(graph.PackageGraphDependency)) == (
        "ref",
        "declaring_package",
        "resolved_package",
        "witness",
    )
    assert tuple(field.name for field in fields(graph.PackageGraphSnapshot)) == (
        "scope",
        "packages",
        "dependencies",
        "requirement_collections",
        "requirements",
        "selectors",
        "capability_evaluations",
        "catalog_evidence",
        "modules",
        "declarations",
        "semantic_authorities",
        "fields",
        "let_bindings",
        "source_lineage",
        "projection_lineage",
        "expression_lineage",
        "current_window_lineage",
        "relation_lineage_states",
        "let_lineage_states",
        "aggregate_lineage_states",
        "expression_lineage_states",
        "current_window_lineage_states",
        "named_windows",
        "window_semantic_provenance",
    )
    assert tuple(
        field.name for field in fields(graph_inspection.PackageGraphInspection)
    ) == (
        "records",
        "links",
        "states",
        "canonical_bytes",
    )
    assert graph.__all__ == graph_inspection.__all__ == project_package.__all__ == ()
    for name in ("PackageGraphSnapshot", "PackageGraphInspection"):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
