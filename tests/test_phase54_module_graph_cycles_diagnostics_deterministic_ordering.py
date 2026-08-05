from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_slice11_gate2_is_active,
)

import pytest

import _phase54_active_gate2_manifest as active_gate2_manifest
import pietto._project.check as project_check
import pietto._project.module_graph as module_graph
import pietto.cli as cli
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
)
from pietto.errors import Severity


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_REL = (
    "docs/spec/phase54-slice8-module-graph-cycles-diagnostics-and-"
    "deterministic-ordering-v1.md"
)
SOURCE_REL = "src/pietto/_project/module_graph.py"
TEST_REL = (
    "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py"
)

EXPECTED_TEST_NAMES = (
    "test_graph_carrier_enums_fields_privacy_and_manifest_are_exact",
    "test_vertex_identity_immutability_and_hash_are_logical",
    "test_evidence_and_canonical_edge_invariants_reject_rewrites",
    "test_graph_lookups_adjacency_and_collections_are_immutable",
    "test_modules_without_imports_form_selected_singleton_components",
    "test_selected_modules_define_vertex_and_component_order",
    "test_exact_selected_targets_create_source_evidence_edges",
    "test_unresolved_targets_create_no_edges_and_group_statement_evidence",
    "test_repeated_requests_retain_evidence_but_share_one_canonical_edge",
    "test_adjacency_uses_target_order_not_import_text_order",
    "test_direct_self_import_is_one_component_cycle",
    "test_two_module_cycle_has_one_canonical_witness",
    "test_longer_cycle_uses_lowest_selected_member_as_witness_start",
    "test_multiple_independent_cycles_are_selected_ordered",
    "test_dag_diamond_is_not_a_cycle",
    "test_repeated_cycle_requests_do_not_duplicate_cycles_or_witness_edges",
    "test_complex_scc_chooses_shortest_then_selected_order_witness",
    "test_graph_value_equality_hash_and_evidence_sensitivity_are_exact",
    "test_graph_builder_uses_only_retained_inputs_and_performs_no_io",
    "test_pie_s2701_mapping_message_span_and_statement_deduplication",
    "test_pie_s2702_conflicting_identity_adapter_boundary_is_fail_closed",
    "test_pie_s2703_cycle_message_primary_and_private_related_spans",
    "test_pie_s2704_export_issue_mappings_and_duplicate_precedence",
    "test_pie_s2705_unknown_private_import_mappings_are_exact",
    "test_pie_s2706_collision_mapping_is_one_per_local_name_bucket",
    "test_pie_s2707_facade_and_unsupported_adapter_mappings_are_exact",
    "test_unresolved_target_and_import_export_cascades_are_suppressed",
    "test_target_export_root_suppresses_downstream_facade_diagnostic",
    "test_diagnostic_order_text_cli_and_project_json_v2_are_exact",
    "test_schema_v1_privacy_status_reader_fixed_point_and_slice9_boundary",
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


def _required_graph(semantic: ProjectSemanticResult) -> module_graph.ProjectModuleGraph:
    assert semantic.module_graph is not None
    return semantic.module_graph


def _required_diagnostics(
    semantic: ProjectSemanticResult,
) -> module_graph.ProjectModuleDiagnosticSet:
    assert semantic.module_diagnostic_facts is not None
    return semantic.module_diagnostic_facts


def _module_source(name: str, imports: tuple[tuple[str, str], ...] = ()) -> str:
    source = f"shape {name}:\n    id: Int\nexport:\n    shape {name}\n"
    return source + "".join(
        f'import "{target}":\n    shape {target_name}\n'
        for target, target_name in imports
    )


def _paths(cycle: module_graph.ProjectModuleCycle) -> tuple[str, ...]:
    return tuple(vertex.identity.path for vertex in cycle.witness.vertices)


def _diagnostic_pairs(
    semantic: ProjectSemanticResult,
) -> tuple[tuple[str, str], ...]:
    return tuple((item.code, item.message) for item in semantic.diagnostics)


def test_graph_carrier_enums_fields_privacy_and_manifest_are_exact() -> None:
    assert module_graph.__all__ == ()
    assert tuple(module_graph.ProjectModuleGraphIssueStatus) == (
        module_graph.ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE,
        module_graph.ProjectModuleGraphIssueStatus.DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY,
        module_graph.ProjectModuleGraphIssueStatus.MODULE_IMPORT_CYCLE,
        module_graph.ProjectModuleGraphIssueStatus.UNSUPPORTED_EXPLICIT_MODULE_REFERENCE,
    )
    assert tuple(module_graph.ProjectModuleDiagnosticOrigin) == (
        module_graph.ProjectModuleDiagnosticOrigin.GRAPH,
        module_graph.ProjectModuleDiagnosticOrigin.EXPORT,
        module_graph.ProjectModuleDiagnosticOrigin.BINDING,
    )
    expected_fields = {
        module_graph.ProjectModuleGraphVertex: ("identity", "position", "module"),
        module_graph.ProjectModuleImportEvidenceEdge: ("origin", "target", "request"),
        module_graph.ProjectModuleDependencyEdge: (
            "origin",
            "target",
            "evidence_edges",
        ),
        module_graph.ProjectModuleStronglyConnectedComponent: (
            "members",
            "internal_edges",
        ),
        module_graph.ProjectModuleCycleWitness: ("vertices", "edges"),
        module_graph.ProjectModuleCycle: ("component", "witness"),
        module_graph.ProjectModuleGraphIssue: (
            "status",
            "owning_vertex",
            "requests",
            "cycle",
            "conflicting_vertices",
            "binding_issues",
        ),
        module_graph.ProjectModuleGraph: (
            "binding_authority",
            "_canonical_authority",
            "vertices",
            "evidence_edges",
            "edges",
            "components",
            "cycles",
            "issues",
            "_vertices_by_path",
            "_outgoing_by_vertex",
        ),
        module_graph.ProjectModuleDiagnosticFact: (
            "origin",
            "diagnostic",
            "module_position",
            "module_statement_position",
            "item_position",
            "related_locations",
            "graph_issues",
            "export_issues",
            "binding_issues",
        ),
        module_graph.ProjectModuleDiagnosticSet: (
            "_canonical_authority",
            "facts",
            "diagnostics",
        ),
    }
    for carrier, names in expected_fields.items():
        assert is_dataclass(carrier)
        assert tuple(item.name for item in fields(carrier)) == names
    authority_field = fields(module_graph.ProjectModuleGraph)[0]
    assert not authority_field.repr
    assert not authority_field.compare
    assert authority_field.hash is False
    canonical_authority_field = fields(module_graph.ProjectModuleGraph)[1]
    assert not canonical_authority_field.repr
    assert not canonical_authority_field.compare
    assert canonical_authority_field.hash is False
    canonical_authority = module_graph._ProjectModuleGraphCanonicalAuthority
    assert is_dataclass(canonical_authority)
    assert tuple(item.name for item in fields(canonical_authority)) == (
        "binding_authority",
        "vertices",
        "evidence_edges",
        "edges",
        "components",
        "cycles",
        "issues",
    )
    assert tuple(inspect.signature(canonical_authority).parameters) == (
        "binding_authority",
    )
    assert all(
        not item.init
        for item in fields(canonical_authority)
        if item.name
        in {"vertices", "evidence_edges", "edges", "components", "cycles", "issues"}
    )
    diagnostic_authority = module_graph._ProjectModuleDiagnosticCanonicalAuthority
    assert is_dataclass(diagnostic_authority)
    assert tuple(item.name for item in fields(diagnostic_authority)) == (
        "graph",
        "exports",
        "binding_authority",
        "facts",
        "diagnostics",
    )
    assert tuple(inspect.signature(diagnostic_authority).parameters) == (
        "graph",
        "exports",
        "binding_authority",
    )
    assert all(
        not item.init
        for item in fields(diagnostic_authority)
        if item.name in {"facts", "diagnostics"}
    )
    diagnostic_set_authority = fields(module_graph.ProjectModuleDiagnosticSet)[0]
    assert not diagnostic_set_authority.repr
    assert not diagnostic_set_authority.compare
    assert diagnostic_set_authority.hash is False
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_MARKER == (
        "PHASE54_SLICE11_GATE2"
    )
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_BASE == (
        "b81843acadb294630db361c09949868d004b1bca"
    )


def test_vertex_identity_immutability_and_hash_are_logical(tmp_path: Path) -> None:
    _, semantic = _semantic_project(tmp_path, {"a.pietto": _module_source("A")})
    vertex = _required_graph(semantic).vertices[0]
    assert vertex.identity.path == "a.pietto"
    assert vertex.position == 0
    assert hash(vertex) == hash(replace(vertex, module=vertex.module))
    with pytest.raises(FrozenInstanceError):
        setattr(vertex, "position", 1)
    with pytest.raises(ValueError, match="match one parsed module"):
        replace(vertex, position=1)


def test_evidence_and_canonical_edge_invariants_reject_rewrites(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B"),
        },
    )
    graph = _required_graph(semantic)
    evidence = graph.evidence_edges[0]
    edge = graph.edges[0]
    with pytest.raises(ValueError, match="exact endpoints"):
        replace(evidence, target=graph.vertices[0])
    with pytest.raises(ValueError, match="requires source evidence"):
        replace(edge, evidence_edges=())
    with pytest.raises(ValueError, match="match its endpoints"):
        replace(edge, origin=graph.vertices[1])
    with pytest.raises(ValueError, match="exactly match binding authority evidence"):
        replace(graph, edges=())
    with pytest.raises(ValueError, match="partition all vertices"):
        replace(graph, components=())
    cloned_evidence = replace(evidence)
    cloned_edge = replace(edge, evidence_edges=(cloned_evidence,))
    with pytest.raises(ValueError, match="exact canonical authority objects"):
        replace(
            graph,
            evidence_edges=(cloned_evidence,),
            edges=(cloned_edge,),
        )
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(
            graph._canonical_authority,
            evidence_edges=(cloned_evidence,),
            edges=(cloned_edge,),
        )

    rebuilt_authority = replace(graph._canonical_authority)
    assert rebuilt_authority.binding_authority is graph.binding_authority
    for name in (
        "vertices",
        "evidence_edges",
        "edges",
        "components",
        "cycles",
        "issues",
    ):
        assert getattr(rebuilt_authority, name) == getattr(
            graph._canonical_authority, name
        )
    for name in ("vertices", "evidence_edges", "edges", "components"):
        assert getattr(rebuilt_authority, name) is not getattr(
            graph._canonical_authority, name
        )
    rebuilt_graph = replace(
        graph,
        _canonical_authority=rebuilt_authority,
        vertices=rebuilt_authority.vertices,
        evidence_edges=rebuilt_authority.evidence_edges,
        edges=rebuilt_authority.edges,
        components=rebuilt_authority.components,
        cycles=rebuilt_authority.cycles,
        issues=rebuilt_authority.issues,
    )
    assert rebuilt_graph == graph
    assert rebuilt_graph.vertices is rebuilt_authority.vertices
    assert rebuilt_graph.edges is rebuilt_authority.edges

    _, foreign_semantic = _semantic_project(
        tmp_path / "foreign",
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B"),
        },
    )
    assert foreign_semantic.module_bindings is not None
    with pytest.raises(ValueError, match="exactly match binding authority"):
        replace(graph, binding_authority=foreign_semantic.module_bindings)
    foreign_authority = replace(
        graph._canonical_authority,
        binding_authority=foreign_semantic.module_bindings,
    )
    with pytest.raises(ValueError, match="exactly match binding authority root"):
        replace(graph, _canonical_authority=foreign_authority)
    with pytest.raises(ValueError, match="exactly match binding authority"):
        replace(
            graph,
            binding_authority=foreign_semantic.module_bindings,
            _canonical_authority=foreign_authority,
        )


def test_graph_lookups_adjacency_and_collections_are_immutable(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B"),
        },
    )
    graph = _required_graph(semantic)
    origin = graph.find_path("a.pietto")[0]
    assert graph.find_path("missing.pietto") == ()
    assert graph.find_path("../bad.pietto") == ()
    assert graph.outgoing(origin) == graph.edges
    assert isinstance(graph._vertices_by_path, MappingProxyType)
    assert isinstance(graph._outgoing_by_vertex, MappingProxyType)
    with pytest.raises(TypeError):
        graph._vertices_by_path["x.pietto"] = origin  # type: ignore[index]


def test_modules_without_imports_form_selected_singleton_components(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _module_source("A"), "b.pietto": _module_source("B")},
    )
    graph = _required_graph(semantic)
    assert graph.evidence_edges == graph.edges == graph.cycles == graph.issues == ()
    assert tuple(
        tuple(v.identity.path for v in item.members) for item in graph.components
    ) == (
        ("a.pietto",),
        ("b.pietto",),
    )
    assert all(not item.is_cyclic for item in graph.components)


def test_selected_modules_define_vertex_and_component_order(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "z.pietto": _module_source("Z"),
            "a.pietto": _module_source("A"),
            "m.pietto": _module_source("M"),
        },
    )
    graph = _required_graph(semantic)
    assert tuple(vertex.identity.path for vertex in graph.vertices) == (
        "a.pietto",
        "m.pietto",
        "z.pietto",
    )
    assert tuple(component.members[0].position for component in graph.components) == (
        0,
        1,
        2,
    )


def test_exact_selected_targets_create_source_evidence_edges(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source(
                "A",
                (("b.pietto", "B"), ("c.pietto", "C")),
            ),
            "b.pietto": _module_source("B"),
            "c.pietto": _module_source("C"),
        },
    )
    graph = _required_graph(semantic)
    assert tuple(
        (edge.origin.identity.path, edge.target.identity.path)
        for edge in graph.evidence_edges
    ) == (("a.pietto", "b.pietto"), ("a.pietto", "c.pietto"))
    assert len(graph.edges) == 2


def test_unresolved_targets_create_no_edges_and_group_statement_evidence(
    tmp_path: Path,
) -> None:
    source = (
        "shape A:\n    id: Int\n"
        'import "missing.pietto":\n'
        "    shape Missing\n"
        "    type MissingType\n"
    )
    _, semantic = _semantic_project(tmp_path, {"a.pietto": source})
    graph = _required_graph(semantic)
    assert graph.edges == graph.evidence_edges == ()
    assert len(graph.issues) == 1
    issue = graph.issues[0]
    assert (
        issue.status
        is module_graph.ProjectModuleGraphIssueStatus.UNRESOLVED_TARGET_MODULE
    )
    assert len(issue.requests) == len(issue.binding_issues) == 2
    with pytest.raises(ValueError, match="issues must exactly match"):
        replace(graph, issues=())


def test_repeated_requests_retain_evidence_but_share_one_canonical_edge(
    tmp_path: Path,
) -> None:
    source = (
        "shape A:\n    id: Int\n"
        'import "b.pietto":\n    shape B\n'
        'import "b.pietto":\n    shape B as OtherB\n'
    )
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": source, "b.pietto": _module_source("B")},
    )
    graph = _required_graph(semantic)
    assert len(graph.evidence_edges) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].evidence_edges == graph.evidence_edges


def test_adjacency_uses_target_order_not_import_text_order(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source(
                "A",
                (("c.pietto", "C"), ("b.pietto", "B")),
            ),
            "b.pietto": _module_source("B"),
            "c.pietto": _module_source("C"),
        },
    )
    graph = _required_graph(semantic)
    assert tuple(edge.target.identity.path for edge in graph.evidence_edges) == (
        "c.pietto",
        "b.pietto",
    )
    assert tuple(
        edge.target.identity.path for edge in graph.outgoing(graph.vertices[0])
    ) == (
        "b.pietto",
        "c.pietto",
    )


def test_direct_self_import_is_one_component_cycle(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": _module_source("A", (("a.pietto", "A"),))},
    )
    graph = _required_graph(semantic)
    assert len(graph.components) == len(graph.cycles) == 1
    assert _paths(graph.cycles[0]) == ("a.pietto",)
    assert (
        graph.cycles[0].witness.edges[0].origin
        == graph.cycles[0].witness.edges[0].target
    )


def test_two_module_cycle_has_one_canonical_witness(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B", (("a.pietto", "A"),)),
        },
    )
    graph = _required_graph(semantic)
    assert len(graph.cycles) == 1
    assert _paths(graph.cycles[0]) == ("a.pietto", "b.pietto")
    assert tuple(
        edge.target.identity.path for edge in graph.cycles[0].witness.edges
    ) == (
        "b.pietto",
        "a.pietto",
    )
    with pytest.raises(ValueError, match="cover every cyclic component"):
        replace(graph, cycles=())


def test_longer_cycle_uses_lowest_selected_member_as_witness_start(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B", (("c.pietto", "C"),)),
            "c.pietto": _module_source("C", (("a.pietto", "A"),)),
        },
    )
    graph = _required_graph(semantic)
    cycle = graph.cycles[0]
    assert _paths(cycle) == ("a.pietto", "b.pietto", "c.pietto")
    assert tuple(member.position for member in cycle.component.members) == (0, 1, 2)


def test_multiple_independent_cycles_are_selected_ordered(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B", (("a.pietto", "A"),)),
            "c.pietto": _module_source("C", (("d.pietto", "D"),)),
            "d.pietto": _module_source("D", (("c.pietto", "C"),)),
        },
    )
    cycles = _required_graph(semantic).cycles
    assert tuple(_paths(cycle) for cycle in cycles) == (
        ("a.pietto", "b.pietto"),
        ("c.pietto", "d.pietto"),
    )


def test_dag_diamond_is_not_a_cycle(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source(
                "A",
                (("b.pietto", "B"), ("c.pietto", "C")),
            ),
            "b.pietto": _module_source("B", (("d.pietto", "D"),)),
            "c.pietto": _module_source("C", (("d.pietto", "D"),)),
            "d.pietto": _module_source("D"),
        },
    )
    graph = _required_graph(semantic)
    assert len(graph.edges) == 4
    assert graph.cycles == ()
    assert all(not item.is_cyclic for item in graph.components)


def test_repeated_cycle_requests_do_not_duplicate_cycles_or_witness_edges(
    tmp_path: Path,
) -> None:
    a_source = (
        _module_source("A", (("b.pietto", "B"),))
        + 'import "b.pietto":\n    shape B as OtherB\n'
    )
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": a_source,
            "b.pietto": _module_source("B", (("a.pietto", "A"),)),
        },
    )
    graph = _required_graph(semantic)
    assert len(graph.evidence_edges) == 3
    assert len(graph.edges) == 2
    assert len(graph.cycles) == 1
    assert len(graph.cycles[0].witness.edges) == 2


def test_complex_scc_chooses_shortest_then_selected_order_witness(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source(
                "A",
                (("b.pietto", "B"), ("c.pietto", "C")),
            ),
            "b.pietto": _module_source("B", (("a.pietto", "A"),)),
            "c.pietto": _module_source("C", (("d.pietto", "D"),)),
            "d.pietto": _module_source("D", (("a.pietto", "A"),)),
        },
    )
    graph = _required_graph(semantic)
    cycle = graph.cycles[0]
    assert tuple(member.identity.path for member in cycle.component.members) == (
        "a.pietto",
        "b.pietto",
        "c.pietto",
        "d.pietto",
    )
    assert _paths(cycle) == ("a.pietto", "b.pietto")
    edges_by_pair = {
        (edge.origin.identity.path, edge.target.identity.path): edge
        for edge in graph.edges
    }
    alternate_witness = module_graph.ProjectModuleCycleWitness(
        vertices=(graph.vertices[0], graph.vertices[2], graph.vertices[3]),
        edges=(
            edges_by_pair[("a.pietto", "c.pietto")],
            edges_by_pair[("c.pietto", "d.pietto")],
            edges_by_pair[("d.pietto", "a.pietto")],
        ),
    )
    alternate_cycle = module_graph.ProjectModuleCycle(
        component=cycle.component,
        witness=alternate_witness,
    )
    with pytest.raises(ValueError, match="exactly match canonical components"):
        replace(graph, cycles=(alternate_cycle,))


def test_graph_value_equality_hash_and_evidence_sensitivity_are_exact(
    tmp_path: Path,
) -> None:
    sources = {
        "a.pietto": _module_source("A", (("b.pietto", "B"),)),
        "b.pietto": _module_source("B"),
    }
    _, first = _semantic_project(tmp_path / "first", sources)
    _, second = _semantic_project(tmp_path / "second", sources)
    first_graph = _required_graph(first)
    second_graph = _required_graph(second)
    assert first_graph == second_graph
    assert hash(first_graph) == hash(second_graph)
    first_diagnostics = _required_diagnostics(first)
    second_diagnostics = _required_diagnostics(second)
    assert first_diagnostics == second_diagnostics
    assert hash(first_diagnostics) == hash(second_diagnostics)
    assert (
        first_diagnostics._canonical_authority
        is not second_diagnostics._canonical_authority
    )
    assert (
        first_diagnostics._canonical_authority.graph is first_graph
        and first_diagnostics._canonical_authority.exports is first.module_exports
        and first_diagnostics._canonical_authority.binding_authority
        is first.module_bindings
    )
    with pytest.raises(ValueError, match="exact diagnostic authority"):
        replace(first, module_diagnostic_facts=second_diagnostics)

    _, first_nonempty = _semantic_project(
        tmp_path / "first-nonempty",
        {"a.pietto": 'import "missing.pietto":\n    shape Missing\n'},
    )
    _, second_nonempty = _semantic_project(
        tmp_path / "second-nonempty",
        {"a.pietto": 'import "missing.pietto":\n    shape Missing\n'},
    )
    first_nonempty_diagnostics = _required_diagnostics(first_nonempty)
    second_nonempty_diagnostics = _required_diagnostics(second_nonempty)
    assert first_nonempty_diagnostics == second_nonempty_diagnostics
    assert (
        first_nonempty_diagnostics._canonical_authority
        is not second_nonempty_diagnostics._canonical_authority
    )
    with pytest.raises(ValueError, match="canonical authority objects"):
        replace(
            first_nonempty_diagnostics,
            _canonical_authority=second_nonempty_diagnostics._canonical_authority,
        )
    with pytest.raises(ValueError, match="exact diagnostic authority"):
        replace(
            first_nonempty,
            module_diagnostic_facts=second_nonempty_diagnostics,
        )
    _, reordered = _semantic_project(
        tmp_path / "reordered",
        {
            "a.pietto": (
                _module_source("A", (("b.pietto", "B"),))
                + 'import "b.pietto":\n    shape B as OtherB\n'
            ),
            "b.pietto": _module_source("B"),
        },
    )
    assert first_graph != _required_graph(reordered)


def test_graph_builder_uses_only_retained_inputs_and_performs_no_io(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _configured_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B"),
        },
    )
    parse_result = project_check.check_project_parse_only(root)
    assert parse_result.ok

    def forbidden(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("graph construction must not perform filesystem I/O")

    monkeypatch.setattr(Path, "open", forbidden)
    monkeypatch.setattr(Path, "read_text", forbidden)
    semantic = build_empty_project_semantic_result(parse_result)
    assert len(_required_graph(semantic).edges) == 1


def test_pie_s2701_mapping_message_span_and_statement_deduplication(
    tmp_path: Path,
) -> None:
    source = (
        "shape A:\n    id: Int\n"
        'import "missing.pietto":\n'
        "    shape Missing\n"
        "    type MissingType\n"
    )
    _, semantic = _semantic_project(tmp_path, {"a.pietto": source})
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2701", 'Unresolved module import target: "missing.pietto"'),
    )
    diagnostic = semantic.diagnostics[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.suggestion is None
    assert diagnostic.location.path == "a.pietto"
    assert diagnostic.location.line == 3
    fact = _required_diagnostics(semantic).facts[0]
    assert len(fact.graph_issues[0].requests) == 2


def test_pie_s2702_conflicting_identity_adapter_boundary_is_fail_closed(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(tmp_path, {"a.pietto": _module_source("A")})
    vertex = _required_graph(semantic).vertices[0]
    other_module = ProjectLogicalModule(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        path=vertex.module.path,
        position=1,
        project_input=vertex.module.project_input,
        parsed_input=vertex.module.parsed_input,
    )
    conflicting = module_graph.ProjectModuleGraphVertex(
        identity=vertex.identity,
        position=1,
        module=other_module,
    )
    issue = module_graph.ProjectModuleGraphIssue(
        status=module_graph.ProjectModuleGraphIssueStatus.DUPLICATE_OR_CONFLICTING_MODULE_IDENTITY,
        owning_vertex=vertex,
        conflicting_vertices=(vertex, conflicting),
    )
    fact = module_graph._diagnostic_fact_from_graph_issue(issue)
    assert (fact.diagnostic.code, fact.diagnostic.message) == (
        "PIE-S2702",
        "Duplicate or conflicting module identity: a.pietto",
    )
    assert fact.diagnostic.location.line == fact.diagnostic.location.column == 1


def test_pie_s2703_cycle_message_primary_and_private_related_spans(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": _module_source("A", (("b.pietto", "B"),)),
            "b.pietto": _module_source("B", (("a.pietto", "A"),)),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        (
            "PIE-S2703",
            "Module import cycle detected: a.pietto -> b.pietto -> a.pietto",
        ),
    )
    fact = _required_diagnostics(semantic).facts[0]
    assert fact.diagnostic.location.path == "b.pietto"
    assert tuple(item.path for item in fact.related_locations) == ("a.pietto",)


def test_pie_s2704_export_issue_mappings_and_duplicate_precedence(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape D:\n    id: Int\n"
                "shape Ambiguous:\n    id: Int\n"
                "shape Ambiguous:\n    id: Int\n"
                "export:\n"
                "    shape Missing\n"
                "    shape Ambiguous\n"
                "    shape D\n"
                "    shape D\n"
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2704", "Unknown export binding: shape Missing"),
        ("PIE-S2704", "Ambiguous local export declaration: shape Ambiguous"),
        ("PIE-S2704", "Duplicate export request: shape D"),
    )
    duplicate_fact = _required_diagnostics(semantic).facts[-1]
    assert len(duplicate_fact.export_issues) == 1
    assert len(duplicate_fact.related_locations) == 1


def test_pie_s2705_unknown_private_import_mappings_are_exact(tmp_path: Path) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": ('import "b.pietto":\n    shape Missing\n    shape Private\n'),
            "b.pietto": "shape Private:\n    id: Int\n",
        },
    )
    assert _diagnostic_pairs(semantic) == (
        (
            "PIE-S2705",
            'Unknown imported declaration: shape Missing from "b.pietto"',
        ),
        (
            "PIE-S2705",
            "Imported declaration is private or not exported: "
            'shape Private from "b.pietto"',
        ),
    )


def test_pie_s2706_collision_mapping_is_one_per_local_name_bucket(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Local:\n    id: Int\n"
                'import "b.pietto":\n'
                "    shape B as Local\n"
                "    shape C as Shared\n"
                "    shape D as Shared\n"
            ),
            "b.pietto": (
                "shape B:\n    id: Int\n"
                "shape C:\n    id: Int\n"
                "shape D:\n    id: Int\n"
                "export:\n    shape B\n    shape C\n    shape D\n"
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        (
            "PIE-S2706",
            "Import binding collides with a local declaration: Local",
        ),
        ("PIE-S2706", "Import binding name is ambiguous: Shared"),
    )
    facts = _required_diagnostics(semantic).facts
    assert len(facts[0].binding_issues) == 1
    assert len(facts[1].binding_issues) == 2


def test_pie_s2707_facade_and_unsupported_adapter_mappings_are_exact(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "b.pietto":\n    shape Shared\n',
            "b.pietto": (
                "shape Shared:\n    id: Int\n"
                "query Shared:\n    from missing\n    select:\n        id\n"
                "export:\n    query Shared\n"
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        (
            "PIE-S2707",
            'Inconsistent explicit-module target facade: "b.pietto"',
        ),
        ("PIE-S2301", "Unknown relation: missing"),
    )
    graph = _required_graph(semantic)
    assert semantic.module_bindings is not None
    request = semantic.module_bindings.environments[0].requests[0]
    unsupported = module_graph.ProjectModuleGraphIssue(
        status=module_graph.ProjectModuleGraphIssueStatus.UNSUPPORTED_EXPLICIT_MODULE_REFERENCE,
        owning_vertex=graph.vertices[0],
        requests=(request,),
    )
    fact = module_graph._diagnostic_fact_from_graph_issue(unsupported)
    assert (fact.diagnostic.code, fact.diagnostic.message) == (
        "PIE-S2707",
        'Unsupported explicit-module reference: "b.pietto"',
    )


def test_unresolved_target_and_import_export_cascades_are_suppressed(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": (
                'import "missing.pietto":\n    shape Missing as Shared\n'
                "export:\n    shape Shared\n"
            )
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2701", 'Unresolved module import target: "missing.pietto"'),
    )
    graph_issue = _required_graph(semantic).issues[0]
    assert len(graph_issue.binding_issues) == 1
    assert semantic.module_exports is not None
    assert len(semantic.module_exports.surfaces[0].issues) == 1


def test_target_export_root_suppresses_downstream_facade_diagnostic(
    tmp_path: Path,
) -> None:
    _, semantic = _semantic_project(
        tmp_path,
        {
            "a.pietto": 'import "b.pietto":\n    shape Shared\n',
            "b.pietto": (
                "shape Shared:\n    id: Int\n"
                "export:\n    shape Shared\n    shape Shared\n"
            ),
        },
    )
    assert _diagnostic_pairs(semantic) == (
        ("PIE-S2704", "Duplicate export request: shape Shared"),
    )
    assert semantic.module_bindings is not None
    assert any(
        issue.status.value == "ambiguous_target_facade"
        for issue in semantic.module_bindings.environments[0].issues
    )


def test_diagnostic_order_text_cli_and_project_json_v2_are_exact(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _configured_project(
        tmp_path,
        {
            "a.pietto": (
                "shape Local:\n    id: Int\n"
                'import "missing.pietto":\n    shape Missing\n'
                'import "b.pietto":\n    shape Private\n    shape B as Local\n'
                "export:\n    shape Unknown\n"
            ),
            "b.pietto": "shape Private:\n    id: Int\nshape B:\n    id: Int\nexport:\n    shape B\n",
        },
    )
    parse_result = project_check.check_project_parse_only(root)
    semantic = build_empty_project_semantic_result(parse_result)
    assert [item.code for item in semantic.diagnostics] == [
        "PIE-S2701",
        "PIE-S2704",
        "PIE-S2705",
        "PIE-S2706",
    ]
    assert cli.main(["check", "--project", str(root)]) == 1
    text_result = capsys.readouterr()
    assert text_result.out == ""
    assert [
        text_result.err.index(code)
        for code in (
            "PIE-S2701",
            "PIE-S2704",
            "PIE-S2705",
            "PIE-S2706",
        )
    ] == sorted(
        text_result.err.index(code)
        for code in (
            "PIE-S2701",
            "PIE-S2704",
            "PIE-S2705",
            "PIE-S2706",
        )
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
        "PIE-S2704",
        "PIE-S2705",
        "PIE-S2706",
    ]
    assert all(item["related_locations"] == [] for item in diagnostics)
    assert "module_graph" not in json.dumps(document)


def test_schema_v1_privacy_status_reader_fixed_point_and_slice9_boundary(
    tmp_path: Path,
) -> None:
    parse_result, semantic = _semantic_project(
        tmp_path,
        {"a.pietto": "shape A:\n    id: Int\n"},
        schema_version=1,
    )
    assert parse_result.compilation_mode is ProjectCompilationMode.LEGACY_FLAT
    assert semantic.ok
    assert semantic.module_graph is None
    assert semantic.module_diagnostic_facts is None
    assert semantic.diagnostics == ()
    assert all(
        "PIE-S270" not in source
        for source in (
            (REPO_ROOT / "src/pietto/_project/module_bindings.py").read_text(
                encoding="utf-8"
            ),
            (REPO_ROOT / "src/pietto/_project/module_exports.py").read_text(
                encoding="utf-8"
            ),
        )
    )
    spec = (REPO_ROOT / SPEC_REL).read_text(encoding="utf-8")
    source = (REPO_ROOT / SOURCE_REL).read_text(encoding="utf-8")
    registry = (REPO_ROOT / "docs/spec/diagnostics.md").read_text(encoding="utf-8")
    assert all(
        f"PIE-S270{position}" in source and f"PIE-S270{position}" in registry
        for position in range(1, 8)
    )
    assert (
        "Slice 9 retains cross-module type alias, enum, shape, and source resolution"
        in spec
    )
    tree = ast.parse((REPO_ROOT / TEST_REL).read_text(encoding="utf-8"))
    tests = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tests == EXPECTED_TEST_NAMES
    assert len(tests) == 30
    assert all(
        not node.decorator_list
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(active_gate2_manifest.PHASE54_SLICE10_ORIGINAL_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE54_SLICE10_ORIGINAL_MODIFIED_PATHS) == 69
    assert len(active_gate2_manifest.PHASE54_ACTIVE_GATE2_ADDED_PATHS) == 3
    assert len(active_gate2_manifest.PHASE54_ACTIVE_GATE2_MODIFIED_PATHS) == 72
    assert SOURCE_REL in active_gate2_manifest.PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    assert SPEC_REL in active_gate2_manifest.PHASE54_ACTIVE_GATE2_MODIFIED_PATHS
    assert active_gate2_manifest.PHASE54_ACTIVE_GATE2_DELETED_PATHS == frozenset()
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
        active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS
        == active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_SEED_PATHS
        | active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_READER_PATHS
    )
    assert (
        len(active_gate2_manifest.PHASE54_POST_REVIEW_PRODUCT_REPAIR9_MODIFIED_PATHS)
        == 66
    )
