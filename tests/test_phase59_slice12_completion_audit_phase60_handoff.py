from __future__ import annotations

import ast
from dataclasses import fields
from importlib.metadata import version
from pathlib import Path
import subprocess

import pietto
import pietto._project as project_package
import pietto._project.package_graph as graph
import pietto._project.package_graph_inspection as graph_inspection
import pietto._project_explain as project_explain_package
import test_active_phase_lifecycle as lifecycle
import test_phase59_slice11_differential_compatibility_assurance as differential
from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SEMANTIC_METADATA_COMMAND,
    SEMANTIC_METADATA_SCHEMA_VERSION,
)
from pietto._project_explain.model import ProjectExplainFormat


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase59-completion-audit-phase60-handoff-v1.md"
SOURCE = REPO_ROOT / "tests/test_phase59_slice12_completion_audit_phase60_handoff.py"
PHASE59_BASE = "d5487fe162d1ee47878284ea289f5d15f96bc49b"

_SLICE_AUTHORITIES = (
    (
        "phase59-graph-domains-identity-laws-route-lock-v1.md",
        "test_phase59_slice1_graph_domains_identity_laws_route_lock.py",
        (),
    ),
    (
        "phase59-slice2-private-package-graph-model-snapshot-identity-v1.md",
        "test_phase59_slice2_private_package_graph_model_snapshot_identity.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice3-canonical-package-graph-construction-v1.md",
        "test_phase59_slice3_canonical_package_graph_construction.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice4-requirement-selector-attribution-v1.md",
        "test_phase59_slice4_requirement_selector_attribution.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice5-capability-catalog-typed-negative-evidence-provenance-v1.md",
        "test_phase59_slice5_capability_catalog_typed_negative_evidence_provenance.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice6-direct-transitive-why-not-provenance-v1.md",
        "test_phase59_slice6_direct_transitive_why_not_provenance.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice7-package-to-module-attribution-bridge-v1.md",
        "test_phase59_slice7_package_to_module_attribution_bridge.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice8-semantic-field-lineage-integration-v1.md",
        "test_phase59_slice8_semantic_field_lineage_integration.py",
        ("src/pietto/_project/package_graph.py",),
    ),
    (
        "phase59-slice9-private-graph-integrity-inspection-query-canonical-pure-boundary-v1.md",
        "test_phase59_slice9_private_graph_integrity_inspection_query_canonical_pure_boundary.py",
        ("src/pietto/_project/package_graph_inspection.py",),
    ),
    (
        "phase59-slice10-real-multi-package-provenance-lineage-e2e-v1.md",
        "test_phase59_slice10_real_multi_package_provenance_lineage_e2e.py",
        (),
    ),
    (
        "phase59-slice11-differential-compatibility-assurance-v1.md",
        "test_phase59_slice11_differential_compatibility_assurance.py",
        (),
    ),
    (
        "phase59-completion-audit-phase60-handoff-v1.md",
        "test_phase59_slice12_completion_audit_phase60_handoff.py",
        (),
    ),
)

_PUBLISHED_SLICES = (
    (
        1,
        "830eaf9b27fcbe78926e4cebe407f7d61a2a16b5",
        "92ad2ea415f7cec5c8144536a398ac4b97063580",
        "32931588680",
        "Add Phase 59 graph identity route lock",
    ),
    (
        2,
        "cfb1cce6ed135ecf5103db67998cb7eaeb640563",
        "89a4c6f329a2db92c96e13a959537e8ff6bd4e4d",
        "32939652188",
        "Add private Phase 59 package graph model",
    ),
    (
        3,
        "4a7b701e6bde1ead4847625b09da8b0d4f823e91",
        "7bf3e2da3a59d9604499a205854907dd169715d9",
        "32944037727",
        "Construct canonical Phase 59 package graph",
    ),
    (
        4,
        "b363d2cacd4983c65d2b4c936655749404985ff2",
        "7b313c586c314d3a4cf7c3794e0f0ea13e0f64f7",
        "32951032568",
        "Add Phase 59 requirement selector attribution",
    ),
    (
        5,
        "6706107ef12e81a61df43451677dd9a66702c006",
        "be85b632aceb56301021f52781465a17c35e509b",
        "33002330206",
        "Attach Phase 59 capability catalog provenance",
    ),
    (
        6,
        "4c2dc11f352495620729ee824544f1384d9eb47c",
        "5b772d8773a3e74e8222237a8f58cec1435d8314",
        "33007951230",
        "Add Phase 59 direct and why-not provenance",
    ),
    (
        7,
        "25a3570db293d6b1991b6b0e425f32bf25500dc7",
        "b13a3b3d44e063d63be3945ff33f34e23405330a",
        "33010953704",
        "Add Phase 59 package-to-module attribution",
    ),
    (
        8,
        "f3dae0bc3b682f7319b9f5088f50a523158415ed",
        "f5c484323822c35f7a30233f02b4dc18da0fa4b4",
        "33033412721",
        "Add Phase 59 semantic field lineage",
    ),
    (
        9,
        "67f6a2a255a393bc0e7c6e804a6c56ec384bbba9",
        "7b012a79bfd6281c22e207389080934c9bc9110a",
        "33039837356",
        "Add Phase 59 private graph inspection",
    ),
    (
        10,
        "50a93cfbe1ba9e87d5322a9f17a54d33e371e8a0",
        "7d15780226038c9610e8433f823f318fe7f2d25d",
        "33042245138",
        "Add Phase 59 real multi-package E2E",
    ),
    (
        11,
        "380590421d34637e8a58d0bd4d227739628deb4e",
        "a3ec89ed8d32db1b2c3733ed04725f19d2b61520",
        "33047480433",
        "Add Phase 59 differential compatibility assurance",
    ),
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
    )[1:]


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _commit_is_available(commit: str) -> bool:
    result = subprocess.run(
        ("git", "cat-file", "-e", f"{commit}^{{commit}}"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def test_all_12_route_owners_have_exact_spec_test_and_production_authority() -> None:
    specs = {path.name for path in (REPO_ROOT / "docs/spec").glob("phase59*.md")}
    tests = {path.name for path in (REPO_ROOT / "tests").glob("test_phase59_slice*.py")}
    assert specs == {spec for spec, _test, _production in _SLICE_AUTHORITIES}
    assert tests == {test for _spec, test, _production in _SLICE_AUTHORITIES}
    assert len(_SLICE_AUTHORITIES) == len(lifecycle.EXPECTED_PHASE59_ROUTE) == 12
    assert all(
        (REPO_ROOT / path).is_file()
        for _spec, _test, production in _SLICE_AUTHORITIES
        for path in production
    )

    document = SPEC.read_text(encoding="utf-8")
    rows = _table(_section(document, "Final 12-Slice Completion Matrix"))
    assert tuple((row[0], row[1]) for row in rows) == lifecycle.EXPECTED_PHASE59_ROUTE
    assert tuple(row[2] for row in rows[:11]) == ("`COMPLETED / PUBLISHED`",) * 11
    assert rows[11][2] == "`CURRENT / PENDING NATURAL CI`"
    assert tuple(Path(row[3].strip("`")).name for row in rows) == tuple(
        spec for spec, _test, _production in _SLICE_AUTHORITIES
    )
    assert tuple(Path(row[4].strip("`")).name for row in rows) == tuple(
        test for _spec, test, _production in _SLICE_AUTHORITIES
    )
    assert "ownership obligations evidenced: 12 / 12" in document


def test_slices_1_through_11_have_exact_live_commit_tree_and_ci_chain() -> None:
    rows = _table(
        _section(SPEC.read_text(encoding="utf-8"), "Published Slice 1-11 Authority")
    )
    assert rows == tuple(
        (
            str(number),
            f"`{commit}`",
            f"`{tree}`",
            f"`{run_id}`",
            "`push / attempt 1 / success`",
            f"`{subject}`",
        )
        for number, commit, tree, run_id, subject in _PUBLISHED_SLICES
    )

    commits = tuple(row[1] for row in _PUBLISHED_SLICES)
    if all(_commit_is_available(commit) for commit in commits):
        assert (
            tuple(
                _git(
                    "log", "--reverse", "--format=%H", f"{PHASE59_BASE}..{commits[-1]}"
                ).splitlines()
            )
            == commits
        )
        for position, (_number, commit, tree, _run_id, subject) in enumerate(
            _PUBLISHED_SLICES
        ):
            assert _git("show", "-s", "--format=%T", commit) == tree
            assert _git("show", "-s", "--format=%s", commit) == subject
            expected_parent = PHASE59_BASE if position == 0 else commits[position - 1]
            assert _git("show", "-s", "--format=%P", commit) == expected_parent
    else:
        assert _git("rev-parse", "--is-shallow-repository") == "true"
        assert f"parent {commits[-1]}" in _git("cat-file", "-p", "HEAD")


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


def test_provenance_lineage_integrity_and_differential_owners_remain_live() -> None:
    required_owner_functions = {
        "test_phase59_slice3_canonical_package_graph_construction.py": {
            "test_real_parallel_equal_endpoint_declarations_remain_distinct_links",
        },
        "test_phase59_slice4_requirement_selector_attribution.py": {
            "test_equal_keys_in_distinct_packages_remain_distinct_authored_occurrences",
        },
        "test_phase59_slice5_capability_catalog_typed_negative_evidence_provenance.py": {
            "test_catalog_outcomes_sources_and_provider_evidence_remain_separate",
        },
        "test_phase59_slice6_direct_transitive_why_not_provenance.py": {
            "test_all_routes_keep_shorter_longer_and_authoritative_order",
            "test_missing_positive_edge_and_zero_targets_create_no_why_not",
        },
        "test_phase59_slice7_package_to_module_attribution_bridge.py": {
            "test_equal_module_paths_names_and_source_bytes_never_merge_packages",
        },
        "test_phase59_slice8_semantic_field_lineage_integration.py": {
            "test_current_window_lineage_retains_roles_order_multiplicity_without_frames",
            "test_non_concrete_states_retain_exact_typed_evidence_without_partial_edges",
        },
        "test_phase59_slice9_private_graph_integrity_inspection_query_canonical_pure_boundary.py": {
            "test_integrity_rejects_dangling_foreign_wrong_domain_and_cross_package_grafts",
            "test_direct_and_derived_queries_preserve_every_parallel_route_both_directions",
        },
        "test_phase59_slice10_real_multi_package_provenance_lineage_e2e.py": {
            "test_real_semantic_lineage_queries_integrity_and_package_islands",
        },
        "test_phase59_slice11_differential_compatibility_assurance.py": {
            "test_four_hash_seeds_preserve_complete_semantics_order_and_multiplicity",
            "test_isolated_installed_wheel_matches_source_and_proves_import_origin",
        },
    }
    assert all(
        required <= _function_names(REPO_ROOT / "tests" / filename)
        for filename, required in required_owner_functions.items()
    )


def test_exit_criteria_and_phase59_self_owned_open_are_closed() -> None:
    document = SPEC.read_text(encoding="utf-8")
    original = _table(
        _section(
            (
                REPO_ROOT
                / "docs/spec/phase59-graph-domains-identity-laws-route-lock-v1.md"
            ).read_text(encoding="utf-8"),
            "Exit-criterion Ledger",
        )
    )
    final_rows = _table(_section(document, "Final Exit-Criteria Ledger"))
    assert tuple(row[0] for row in final_rows) == tuple(row[0] for row in original)
    assert all(row[1] == "`PASS`" and row[2] for row in final_rows)
    lowered = document.lower()
    assert "passed criteria: 22" in lowered
    assert "total exit criteria: 22" in lowered

    self_owned = _table(_section(document, "Self-Owned-Open Ledger"))
    assert tuple(row[0] for row in self_owned) == (
        "`TODO` / `FIXME` in Phase 59 production and contracts",
        "Slice 1–11 implementation and compatibility owners",
        "Slice 2 future-domain placeholders",
        "Typed `BLOCKED` / `UNSUPPORTED` / non-concrete states",
        "Advanced windows and frame semantics",
        "Project IR through public lineage expansion",
        "Validation/test runtime optimization",
        "Phase 60 activation inside Phase 59",
    )
    terminal_states = {
        "CLOSED",
        "TRANSFERRED_TO_EXACT_LATER_OWNER",
        "INTENTIONALLY_OUT_OF_SCOPE",
        "INTENTIONALLY_NOT_REQUIRED",
    }
    assert all(row[1].strip("`") in terminal_states and row[2] for row in self_owned)
    assert not {"OPEN", "UNASSIGNED", "TBD", "UNKNOWN_OWNER"} & {
        row[1].strip("`") for row in self_owned
    }
    assert "PHASE59_SELF_OWNED_OPEN = 0" in document


def test_compatibility_public_behavior_and_central_assurance_remain_zero_delta() -> (
    None
):
    assert differential.SEEDS == ("0", "1", "7", "4294967295")
    assert differential.SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert differential.EXPECTED_COMMON_MANIFEST["runtime_refs_distinct"] is True
    assert differential.EXPECTED_COMMON_MANIFEST["integrity"] == "ok"
    assert ProjectExplainFormat.PROJECT_EXPLAIN_V1.value == (
        "pietto.project-explain.v1"
    )
    assert (
        SEMANTIC_METADATA_ARTIFACT_NAME,
        SEMANTIC_METADATA_SCHEMA_VERSION,
        SEMANTIC_METADATA_COMMAND,
    ) == ("Semantic Metadata Artifact v1", 1, "explain")
    assert version("pietto") == "0.1.0"
    assert project_explain_package.__all__ == ()
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    for required in (
        "installed private Phase 59 package graph import",
        "installed private Phase 59 package graph inspection import",
        "import pietto._project.package_graph",
        "import pietto._project.package_graph_inspection",
    ):
        assert required in smoke
    for path in (
        "scripts/validate.py",
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        ".github/workflows/ci.yml",
    ):
        assert (REPO_ROOT / path).is_file()


def test_deferred_readiness_ledger_matches_the_live_roadmap() -> None:
    later_owners = dict(lifecycle.EXPECTED_RETAINED_LATER_OWNERS)
    document = SPEC.read_text(encoding="utf-8")
    deferred_rows = _table(_section(document, "Deferred And Readiness Ledger"))
    assert tuple(row[0] for row in deferred_rows) == tuple(later_owners)
    assert all(
        row[1] == "`TRANSFERRED_TO_EXACT_LATER_OWNER`"
        and row[2] == later_owners[row[0]]
        and row[3]
        for row in deferred_rows
    )
    phase60 = deferred_rows[0][3]
    assert "frame facts can attach without identity migration" in phase60
    assert "no advanced frame semantics" in phase60


def test_performance_interlude_is_mandatory_next_and_phase60_is_not_active() -> None:
    document = SPEC.read_text(encoding="utf-8")
    interlude = _section(document, "Mandatory Performance Interlude")
    normalized = " ".join(interlude.split())
    assert (
        "Phase 59 completion -> Validation/Test Performance Optimization Interlude "
        "-> Phase 60 activation" in normalized
    )
    assert (
        "Evidence-backed optimization of Pietto's test/validation runtime without "
        "weakening validation semantics or deterministic authority" in normalized
    )
    for position, required in enumerate(
        (
            "profile pytest collection/setup/call/teardown and validator timing",
            "measure repeated repository filesystem/source/AST/import scanning",
            "identify duplicated historical repository-wide readers",
            "introduce an immutable session-scoped repository test index only if profiling supports it",
            "consolidate repeated scanners without weakening their policies",
            "audit determinism/isolation before benchmarking pytest-xdist",
            "enable parallel execution only if evidence proves it safe and beneficial",
            "preserve Python 3.12/3.13, generated, golden, package-smoke, reader-closure, and failure semantics",
            "do not rewrite the Python test suite in Rust merely for speed",
            "leave the first Rust-kernel decision to its later roadmap owner",
        ),
        start=1,
    ):
        assert f"{position}. {required}" in normalized
    assert "detailed Slice route remains evidence-driven and unfrozen" in normalized
    assert "| Slice |" not in interlude

    assert (
        "Validation/Test Performance Optimization Interlude",
        "`NEXT / UNSTARTED`",
    ) in lifecycle.EXPECTED_STATUS
    assert ("Phase 60", "`BLOCKED / NOT ACTIVATED`") in lifecycle.EXPECTED_STATUS
    assert "Interlude is next / unstarted" in lifecycle.EXPECTED_PHASE59_STATE
    assert "Phase 60 is blocked / not activated" in lifecycle.EXPECTED_PHASE59_STATE


def test_slice12_candidate_is_docs_static_tests_only_and_has_one_lifecycle_owner() -> (
    None
):
    changed_paths = lifecycle.EXPECTED_SLICE12_CHANGED_PATHS
    assert len(changed_paths) == 5
    assert all((REPO_ROOT / path).is_file() for path in changed_paths)
    assert not any(
        path.startswith(("src/", "scripts/", ".github/")) for path in changed_paths
    )
    source_tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "rglob"
        for node in ast.walk(source_tree)
    )
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(source_tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(source_tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not {"cProfile", "timeit", "pytest_xdist"} & imported_roots

    lifecycle_section = _section(
        SPEC.read_text(encoding="utf-8"),
        "Lifecycle And Publication Subject",
    )
    assert "no status-only follow-up commit" in lifecycle_section.lower()
    assert "Complete Phase 59 package graph provenance" in lifecycle_section
