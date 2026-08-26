from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase59-graph-domains-identity-laws-route-lock-v1.md"

OWNER = "Local package graph, attribution, provenance, and lineage"
HEADINGS = (
    "Answer And Exact Owner",
    "Non-goals",
    "Existing Authority Inputs",
    "Identity Categories",
    "Eight Identity Laws",
    "Graph-snapshot Scope",
    "Private Graph Root And Domain Taxonomy",
    "Typed Link Taxonomy",
    "Direct-link Occurrence And Witness Law",
    "Ordered And N-ary Fact Law",
    "Package And Semantic Lineage Separation",
    "Positive Topology And Typed Evidence",
    "Root Outcomes And Domain-specific Cycles",
    "Ordering And Multiplicity",
    "Direct And Transitive Why",
    "Path-materialization Law",
    "Why-not Provenance",
    "Reverse Queries And Indexes",
    "Referential Integrity",
    "Physical And Logical Privacy Boundary",
    "Private Canonical And Public Boundary",
    "Project Explain v1 Zero-delta",
    "First Missing Production Edge",
    "Exact 12-slice Route",
    "Route Expansion Rule",
    "Exit-criterion Ledger",
    "Phase 60–70 Readiness",
    "Release And Rust Boundary",
    "Gate And Workflow Contract",
    "Lifecycle Candidate And Publication Subject",
)
IDENTITY_CATEGORIES = (
    "Semantic identity",
    "Release identity",
    "Authored occurrence identity",
    "Resolved/loaded occurrence identity",
    "Content identity",
    "Graph-local occurrence identity",
    "Presentation-local identity",
    "Physical trust/location evidence",
)
IDENTITY_LAWS = (
    "Every Identity Has An Explicit Scope",
    "Separate Identity Categories",
    "Authored Request Is Not Resolved Occurrence",
    "Content Identity Never Becomes Occurrence Identity",
    "Names, Aliases, Paths, And Display Syntax Are Not Occurrence Identity",
    "Mutable Or Expandable Facts Do Not Participate In Occurrence Equality",
    "Graph-local Reference And Canonical Coordinate Are Different Concepts",
    "Content Addressing Is Optional Evidence, Not The Default Graph-ID Strategy",
)
DOMAINS = (
    "Package occurrences and direct dependency occurrences",
    "Requirement and selector attribution",
    "Capability, catalog, and source provenance",
    "Package-qualified module, declaration, and field occurrences",
    "Semantic and field lineage",
    "Direct why and derived transitive why/why-not",
    "Typed rejection, blocker, error, and negative evidence",
)
LINKS = (
    "Dependency resolution",
    "Requirement ownership",
    "Capability/catalog provenance",
    "Package-to-module bridge",
    "Semantic dependency",
    "Field lineage",
)
ROUTE = (
    ("1", "Graph Domains, Identity Laws, And Route Lock"),
    ("2", "Private Package Graph Model And Snapshot Identity"),
    ("3", "Canonical Package Graph Construction"),
    ("4", "Requirement And Selector Attribution"),
    ("5", "Capability, Catalog, And Typed Negative Evidence Provenance"),
    ("6", "Direct, Transitive, And Why-Not Provenance"),
    ("7", "Package-to-Module Attribution Bridge"),
    ("8", "Semantic And Field-Lineage Integration"),
    (
        "9",
        "Private Graph Integrity, Inspection, Query, And Canonical Pure Boundary",
    ),
    ("10", "Real Multi-Package Provenance And Lineage E2E"),
    ("11", "Differential Compatibility Assurance"),
    ("12", "Completion Audit And Phase 60 Handoff"),
)
EXIT_SLICES = (
    "2",
    "2",
    "2",
    "3",
    "3",
    "3",
    "4",
    "5",
    "6",
    "6",
    "7",
    "8",
    "8",
    "9",
    "9",
    "9",
    "9",
    "11",
    "11",
    "10",
    "11",
    "12",
)
PRODUCTION_PATHS = frozenset(
    {
        "src/pietto/_project/package_manifest.py",
        "src/pietto/_project/package_loader.py",
        "src/pietto/_project/package_load_plan.py",
        "src/pietto/_project/package_inspection.py",
        "src/pietto/semantic/capability_facts.py",
        "src/pietto/semantic/capability_profiles.py",
        "src/pietto/semantic/extension_signature_requirements.py",
        "src/pietto/_project_explain/package_requirement_projection.py",
        "src/pietto/_project/module_carrier.py",
        "src/pietto/_project/module_attribution.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/_project/model.py",
        "src/pietto/_project_explain/composition.py",
    }
)


def _read() -> str:
    return SPEC.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _tables(section: str) -> tuple[tuple[tuple[str, ...], ...], ...]:
    tables: list[tuple[tuple[str, ...], ...]] = []
    rows: list[tuple[str, ...]] = []
    for line in (*section.splitlines(), ""):
        if line.startswith("| "):
            if not line.startswith("| ---"):
                rows.append(tuple(cell.strip() for cell in line.strip("|").split("|")))
        elif rows:
            tables.append(tuple(rows))
            rows = []
    return tuple(tables)


def _normalized(section: str) -> str:
    return " ".join(section.split())


def test_exact_owner_heading_inventory_and_static_scope() -> None:
    document = _read()
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == HEADINGS
    )
    answer = _section(document, "Answer And Exact Owner")
    assert answer.count(OWNER) == 1
    assert _tables(answer)[0][1:] == (
        ("Production changes", "`0`"),
        ("Public behavior changes", "`0`"),
        ("Public schema changes", "`0`"),
        ("Generated paths", "`0`"),
        ("Golden paths", "`0`"),
        ("Package/build metadata paths", "`0`"),
        ("Graph implementation", "`FORBIDDEN`"),
        ("Public graph or CLI", "`FORBIDDEN`"),
        ("Current version", "`0.1.0`"),
    )
    non_goals = _normalized(_section(document, "Non-goals"))
    for boundary in (
        "resolver or loading reimplementation",
        "cross-package semantic import/export",
        "a solver",
        "a lockfile",
        "persistent/public UUIDs",
        "Rust implementation",
    ):
        assert boundary in non_goals


def test_existing_inputs_are_exact_live_production_owners() -> None:
    section = _section(_read(), "Existing Authority Inputs")
    assert frozenset(re.findall(r"`(src/pietto/[^`]+\.py)`", section)) == (
        PRODUCTION_PATHS
    )
    assert all((REPO_ROOT / path).is_file() for path in PRODUCTION_PATHS)
    assert "test-only helper types are not architecture authority" in section
    assert "without reloading, replanning, rechecking, reselection" in section


def test_identity_categories_and_all_eight_laws_are_structural() -> None:
    document = _read()
    categories = _tables(_section(document, "Identity Categories"))[0][1:]
    assert tuple(row[0] for row in categories) == IDENTITY_CATEGORIES
    assert all(row[1] for row in categories)

    laws = _section(document, "Eight Identity Laws")
    assert (
        tuple(
            line.split(" — ", 1)[1]
            for line in laws.splitlines()
            if line.startswith("### Identity Law ")
        )
        == IDENTITY_LAWS
    )
    law_rows = _tables(laws)[0][1:]
    assert tuple(row[0] for row in law_rows) == tuple(str(i) for i in range(1, 9))
    assert tuple(row[1] for row in law_rows) == IDENTITY_LAWS
    assert "AuthoredDependencyOccurrence != ResolvedLoadedPackageOccurrence" in laws
    assert "same content != same occurrence" in laws
    assert "NodeId = sha256(node facts)" in laws


def test_snapshot_domains_typed_links_and_occurrence_witnesses_are_exact() -> None:
    document = _read()
    scope = _normalized(_section(document, "Graph-snapshot Scope"))
    for required in (
        "One private Phase 59 graph snapshot",
        "Foreign-snapshot, dangling, wrong-domain",
        "not persistent/global identities",
        "runtime owner tokens",
    ):
        assert required in scope

    domain_rows = _tables(_section(document, "Private Graph Root And Domain Taxonomy"))[
        0
    ][1:]
    assert tuple(row[0] for row in domain_rows) == tuple(str(i) for i in range(1, 8))
    assert tuple(row[1] for row in domain_rows) == DOMAINS
    domains = _section(document, "Private Graph Root And Domain Taxonomy")
    for forbidden_generic in ("`Node[Any]`", "`Edge[Any]`", "`kind: str`"):
        assert forbidden_generic in domains

    link_rows = _tables(_section(document, "Typed Link Taxonomy"))[0][1:]
    assert tuple(row[0] for row in link_rows) == LINKS
    assert all(row[1] and row[2] for row in link_rows)
    links = _normalized(_section(document, "Direct-link Occurrence And Witness Law"))
    assert "not merely `(source_ref, target_ref, kind)`" in links
    assert "Parallel authoritative declarations" in links
    assert "Inference alone cannot create direct authority" in links

    ordered = _normalized(_section(document, "Ordered And N-ary Fact Law"))
    for required in ("not flattened", "operand/input/source position", "explicit"):
        assert required in ordered
    separation = _normalized(
        _section(document, "Package And Semantic Lineage Separation")
    )
    assert "Package dependency does not grant cross-package semantic imports" in (
        separation
    )


def test_negative_evidence_cycles_order_and_all_path_laws_are_exact() -> None:
    document = _read()
    evidence = _normalized(_section(document, "Positive Topology And Typed Evidence"))
    for status in (
        "`UNDECLARED`",
        "`UNKNOWN`",
        "`ABSENT`",
        "`UNSUPPORTED`",
        "`CONFLICT`",
        "`BLOCKED`",
    ):
        assert status in evidence
    assert "absence of an edge implies no specific negative state" in evidence

    outcome_tables = _tables(
        _section(document, "Root Outcomes And Domain-specific Cycles")
    )
    assert tuple(row[0] for row in outcome_tables[0][1:]) == (
        "Successful complete graph",
        "Rejected graph authority",
        "Error authority",
    )
    assert tuple(row[0] for row in outcome_tables[1][1:]) == (
        "Package dependency",
        "Package loading/trust",
        "Module import",
        "Relation dependency",
        "Row/let lineage",
        "Requirement attribution",
    )
    assert all(row[1] for table in outcome_tables for row in table[1:])

    order_rows = _tables(_section(document, "Ordering And Multiplicity"))[0][1:]
    assert tuple(row[0] for row in order_rows) == (
        "Package occurrences",
        "Dependency links",
        "Requirements",
        "Selectors",
        "Capability evidence",
        "Catalog/source evidence",
        "Modules/declarations",
        "Lineage",
    )
    why = _normalized(_section(document, "Direct And Transitive Why"))
    assert "Every authoritative path and duplicate occurrence path" in why
    assert "no shortest, preferred, best, alphabetical" in why
    materialization = _normalized(_section(document, "Path-materialization Law"))
    assert "need not eagerly store every transitive path" in materialization
    assert "eager exponential path corpus" in materialization
    why_not = _normalized(_section(document, "Why-not Provenance"))
    assert "positive authoritative provenance path followed by typed terminal" in (
        why_not
    )
    assert "no fake negative edge" in why_not


def test_integrity_indexes_privacy_and_public_zero_delta_are_locked() -> None:
    document = _read()
    indexes = _normalized(_section(document, "Reverse Queries And Indexes"))
    assert "not graph authority" in indexes
    assert "no public/CLI query API" in indexes

    integrity = _normalized(_section(document, "Referential Integrity"))
    assert "Slice 9 must validate" in integrity
    for required in (
        "right typed domain and owning snapshot",
        "wrong-domain",
        "foreign-snapshot",
        "grafted",
        "package-qualified",
    ):
        assert required in integrity
    privacy = _normalized(_section(document, "Physical And Logical Privacy Boundary"))
    assert "do not participate in graph equality" in privacy
    assert "cannot publish physical trust data" in privacy
    private = _normalized(_section(document, "Private Canonical And Public Boundary"))
    assert "no runtime address/scope token" in private
    assert "no public compatibility commitment" in private
    assert "private-first" in private
    assert "neither a content digest, public marker, nor final field inventory" in (
        private
    )
    explain = _normalized(_section(document, "Project Explain v1 Zero-delta"))
    assert "sibling consumers" in explain
    assert "not reconstructed from Project Explain JSON" in explain
    assert "`pietto.project-explain.v1`" in explain


def test_route_expansion_exit_ledger_and_readiness_are_exact() -> None:
    document = _read()
    route_rows = _tables(_section(document, "Exact 12-slice Route"))[0][1:]
    assert tuple((row[0], row[1]) for row in route_rows) == ROUTE
    assert all(row[2] for row in route_rows)
    assert "undeclared vs declared-empty" in route_rows[3][2]
    assert "parallel equal semantic keys" in route_rows[3][2]
    assert "same module path in different packages remains distinct" in route_rows[6][2]
    assert "computed/let/aggregate/current-window lineage" in route_rows[7][2]
    expansion = _normalized(_section(document, "Route Expansion Rule"))
    for required in (
        "exactly 12 slices",
        "genuinely independent Phase 59-owned",
        "cannot fit an existing Slice",
        "Reader omissions",
        "external infrastructure failure",
        "speculative persistence",
    ):
        assert required in expansion

    exit_rows = _tables(_section(document, "Exit-criterion Ledger"))[0][1:]
    assert tuple(row[0] for row in exit_rows) == tuple(str(i) for i in range(1, 23))
    assert all(row[1] for row in exit_rows)
    assert tuple(row[2] for row in exit_rows) == EXIT_SLICES

    readiness_rows = _tables(_section(document, "Phase 60–70 Readiness"))[0][1:]
    assert tuple(row[0] for row in readiness_rows) == tuple(
        str(phase) for phase in range(60, 71)
    )
    assert all(row[1] for row in readiness_rows)
    assert "occurrence identity and lineage" in readiness_rows[0][1]
    assert "IR identity never becomes graph identity" in readiness_rows[1][1]


def test_missing_edge_workflow_lifecycle_release_and_rust_boundaries_are_exact() -> (
    None
):
    document = _read()
    missing = _normalized(_section(document, "First Missing Production Edge"))
    for authority in (
        "PackageInspectionFactSet",
        "exact PackageLoadPlan authority",
        "package-owned loaded-module authority",
        "package-aware private Phase 59 graph root",
    ):
        assert authority in missing
    assert "Slice 1 implements neither" in missing

    workflow = _normalized(_section(document, "Gate And Workflow Contract"))
    for required in (
        "one foreground Ponytail FULL review",
        "at most one causal repair generation",
        "UV_PYTHON=3.13 uv run python scripts/validate.py --timings",
        "starts exactly once",
        "two independent temporary indexes",
        "committed once, pushed once",
        "natural exact-head push CI attempt 1",
    ):
        assert required in workflow

    lifecycle = _normalized(
        _section(document, "Lifecycle Candidate And Publication Subject")
    )
    assert "Phase 58 as completed, Phase 59 as active" in lifecycle
    assert "Slice 2 remains unimplemented and unauthorized" in lifecycle
    assert "Add Phase 59 graph identity route lock" in lifecycle

    release = _normalized(_section(document, "Release And Rust Boundary"))
    assert "no version bump, tag, GitHub Release, package publication" in release
    assert "Version remains `0.1.0`" in release
    assert "Phase 68 retains the first Rust-kernel decision" in release
