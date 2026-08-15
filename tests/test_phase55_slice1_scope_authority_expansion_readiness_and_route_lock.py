"""Phase 55 Slice 1 static scope, authority, audit, and route lock."""

from __future__ import annotations

import ast
import re
import tomllib
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import _phase54_active_gate2_manifest as active_gate


REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = (
    "tests/test_phase55_slice1_scope_authority_expansion_readiness_and_route_lock.py"
)
PLAN_REL = "docs/plan/phase-55-semantic-package-asset-schema-and-deterministic-local-loading.md"
SPEC_REL = (
    "docs/spec/phase55-slice1-scope-authority-expansion-readiness-and-route-lock-v1.md"
)
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v2.md"
README_REL = "README.md"
LANGUAGE_REL = "docs/spec/pietto-v0.9.md"

PHASE_TITLE = "Semantic Package Asset Schema And Deterministic Local Loading"
SLICE_TITLE = (
    "Scope, Authority, Phase-start Expansion Audit, Package Decisions, Activation,"
    " And Route Lock"
)

CLASSIFICATIONS = (
    "IMPLEMENT_NOW",
    "PRIVATE_READINESS_NOW",
    "CONTRACT_ONLY_NOW",
    "DEFER_BY_NECESSITY",
    "OUT_OF_SCOPE",
)
EXPECTED_CLASSIFICATION_IDS = (
    *(f"I{position:02}" for position in range(1, 12)),
    *(f"P{position:02}" for position in range(1, 10)),
    *(f"C{position:02}" for position in range(1, 9)),
    *(f"D{position:02}" for position in range(1, 18)),
    "O01",
    "O02",
)
EXPECTED_CLASSIFICATION_TOTALS = {
    "IMPLEMENT_NOW": 11,
    "PRIVATE_READINESS_NOW": 9,
    "CONTRACT_ONLY_NOW": 8,
    "DEFER_BY_NECESSITY": 17,
    "OUT_OF_SCOPE": 2,
}
EXPECTED_OWNER_CLASSIFICATION = {
    **{f"I{position:02}": ("55", "IMPLEMENT_NOW") for position in range(1, 11)},
    "I11": ("66", "IMPLEMENT_NOW"),
    "P01": ("55", "PRIVATE_READINESS_NOW"),
    "P02": ("55", "PRIVATE_READINESS_NOW"),
    "P03": ("56", "PRIVATE_READINESS_NOW"),
    "P04": ("59", "PRIVATE_READINESS_NOW"),
    "P05": ("60", "PRIVATE_READINESS_NOW"),
    "P06": ("64", "PRIVATE_READINESS_NOW"),
    "P07": ("65", "PRIVATE_READINESS_NOW"),
    "P08": ("67", "PRIVATE_READINESS_NOW"),
    "P09": ("68", "PRIVATE_READINESS_NOW"),
    "C01": ("56", "CONTRACT_ONLY_NOW"),
    "C02": ("57", "CONTRACT_ONLY_NOW"),
    "C03": ("61", "CONTRACT_ONLY_NOW"),
    "C04": ("62", "CONTRACT_ONLY_NOW"),
    "C05": ("63", "CONTRACT_ONLY_NOW"),
    "C06": ("68", "CONTRACT_ONLY_NOW"),
    "C07": ("69", "CONTRACT_ONLY_NOW"),
    "C08": ("70", "CONTRACT_ONLY_NOW"),
    "D01": ("56", "DEFER_BY_NECESSITY"),
    "D02": ("57", "DEFER_BY_NECESSITY"),
    "D03": ("58", "DEFER_BY_NECESSITY"),
    "D04": ("59", "DEFER_BY_NECESSITY"),
    "D05": ("60", "DEFER_BY_NECESSITY"),
    "D06": ("60", "DEFER_BY_NECESSITY"),
    "D07": ("61", "DEFER_BY_NECESSITY"),
    "D08": ("62", "DEFER_BY_NECESSITY"),
    "D09": ("63", "DEFER_BY_NECESSITY"),
    "D10": ("64", "DEFER_BY_NECESSITY"),
    "D11": ("65", "DEFER_BY_NECESSITY"),
    "D12": ("66", "DEFER_BY_NECESSITY"),
    "D13": ("67", "DEFER_BY_NECESSITY"),
    "D14": ("68", "DEFER_BY_NECESSITY"),
    "D15": ("68", "DEFER_BY_NECESSITY"),
    "D16": ("69", "DEFER_BY_NECESSITY"),
    "D17": ("70", "DEFER_BY_NECESSITY"),
    "O01": ("57", "OUT_OF_SCOPE"),
    "O02": ("67", "OUT_OF_SCOPE"),
}
LEDGER_ANCHORS = {
    "Current Production Ledger": {
        "CP01": "schema-v1 exact legacy-flat project discovery",
        "CP02": "schema-v2 explicit local modules; schema-v2 is not package activation",
        "CP03": "strict `pietto.toml` loading, deterministic selected-input order",
        "CP04": "pinned-root, containment, no-follow, opened-identity, TOCTOU",
        "CP05": "contextual local module imports/exports/aliases",
        "CP06": "per-module catalogs, facades, binding environments, graph, resolution",
        "CP07": "complete module attribution/dependency/origin/provenance/lineage",
        "CP08": "current CLI, Project JSON v2, Semantic Metadata Artifact v1",
        "CP09": "Python package `0.1.0` with one runtime dependency",
    },
    "Current Readiness Ledger": {
        "CR01": "historical Phase 50 strict-TOML, namespace/name, exact-version",
        "CR02": "stable root-relative `ProjectModuleIdentity`",
        "CR03": "per-opened-source SHA-256 and filesystem identity facts",
        "CR04": "package-neutral local owner/asset/digest seams",
        "CR05": "fail-closed loader-readiness facts, explicitly not a loader",
        "CR06": "one private module inspection projection",
        "CR07": "one pure total evaluator, closed normalized rejection pattern",
        "CR08": "Phase 54 fact preservation sufficient to carry existing capability/window/type/aggregate facts",
    },
    "Retained Later Ledger": {
        "RL56": "capability-profile language/schema/checker",
        "RL57": "PostgreSQL extension catalog schema/content/matching",
        "RL58": "independently versioned public explain/portability/package-inspection artifact",
        "RL59": "package graph, attribution, provenance, and lineage product",
        "RL60": "advanced window frames and ecosystem checkpoint",
        "RL61": "production Project IR",
        "RL62": "relationship/JOIN/grain/fanout semantics",
        "RL63": "multi-relation SQL, project emit-SQL, and QUALIFY",
        "RL64": "advanced generic/coercion/temporal/Decimal/native mapping",
        "RL65": "advanced aggregation/grouping",
        "RL66": "wildcard/qualified/export-from/callable/constraint/derive/relationship assets",
        "RL67": "remote registry/fetch/install/cache/trust",
        "RL68": "ranges/solver/canonical lockfile/production Rust",
        "RL69": "extension lowering and additional dialects",
        "RL70": "public schema/lineage/attribution expansion, ecosystem completion",
    },
}
DEFERRED_ANCHORS = {
    "D01": "profile schema/language/checker: missing approved profile identity",
    "D02": "extension catalog schema/content/matching: missing Phase 56 profile contract",
    "D03": "public package inspection artifact: requires independently versioned public schema/privacy authority",
    "D04": "package graph/attribution/provenance/lineage product: requires stable Phase 55 loader output",
    "D05": "advanced window frames: requires new language, semantic, IR, and dialect authority",
    "D06": "ecosystem checkpoint: requires completed Phase 51-59 evidence",
    "D07": "Project IR: requires settled package/project composition",
    "D08": "relationship/JOIN/grain/fanout: requires Project IR",
    "D09": "multi-relation SQL/project emit-SQL/QUALIFY: requires Phase 61/62 semantics and IR",
    "D10": "advanced types/native mapping: type/coercion/precision/backend matrices remain unresolved",
    "D11": "advanced aggregation/grouping: requires separate grammar/semantic/IR/SQL decisions",
    "D12": "advanced assets/facades: callable/constraint/derive/relationship",
    "D13": "remote registry/fetch/install/cache/trust: requires network, persistence, threat-model",
    "D14": "ranges/solver/canonical lockfile: requires solving policy, conflict objectives",
    "D15": "production Rust kernel: requires stable pure parity evidence",
    "D16": "extension lowering/additional dialect: requires Phase 57 catalog",
    "D17": "public expansion/ecosystem completion/release decisions: requires public schema",
}

ROUTE = (
    SLICE_TITLE,
    "Explicit Package Activation, Compatibility, And Immutable Package Carrier",
    "Package Manifest Input Schema And Canonical Normalization",
    "Package Identity, Exact Version, And Content Digest",
    "Closed Typed Asset Model And Asset Catalog",
    "Trusted Local Package Locator And Containment Boundary",
    "Deterministic Local Manifest Loading And Package/Module Integration",
    "Exact Dependency Declarations And Deterministic Local Load Plan",
    "Dependency Collision, Cycle, Diamond, And Rejection Diagnostics",
    "Private Package Inspection And Canonical Serialization",
    "Pure Package Boundary, Differential Vectors, Compatibility, And E2E Hardening",
    "Completion Audit, Status Lock, And Phase56 Handoff",
)
ROUTE_DETAILS = (
    (
        "verified Phase 54 completion and maintenance baseline",
        "authority plan/spec/roadmap/active-Gate contract only; no product code",
        "focused static Slice 1 audit plus reader/hash/topology closure",
        "none",
        "Gate 3 exact reviewed-tree publication makes Phase 55 `ACTIVE` and Slice 1 `COMPLETED`",
    ),
    (
        "S01",
        "project config/model/carrier",
        "schema1/schema2/schema3 activation and immutable carrier tests",
        "none before public input boundary is frozen",
        "exclusive activation and exact legacy/package-absent compatibility pass",
    ),
    (
        "S02",
        "manifest parser/validator/normalized document",
        "strict TOML, field, ordering, multiplicity, size, and forward-compatibility tests",
        "none",
        "one strict v1 authority document is accepted/rejected deterministically",
    ),
    (
        "S03",
        "identity/version/digest values and canonical framing",
        "slug/SemVer/relocation/substitution/foreign-root property tests",
        "may proceed in parallel with S06 after S03 interfaces freeze; publication sequential",
        "orthogonal release identity and derived digest invariants pass",
    ),
    (
        "S04",
        "`MODULE_SOURCE` asset identity/catalog",
        "cardinality/duplicate/missing/unknown/cross-kind property tests",
        "may overlap late S06 with disjoint files after shared path/identity types freeze; publication sequential",
        "source/module-level closed set and Phase 66 extension rule pass",
    ),
    (
        "S03",
        "local locator and trusted package-root/manifest open procedures",
        "escape/symlink/retarget/replacement/TOCTOU/duplicate-physical tests",
        "may run beside S04/S05 after manifest path interface freezes; publication sequential",
        "every accepted locator is pinned, contained, stable, and local-only",
    ),
    (
        "S02-S06",
        "package loader, per-package selected inputs, module-island orchestration",
        "manifest-to-module loading, multi-module, same-inner-path, compatibility tests",
        "none",
        "one root package and its exact local assets load without rewriting module identity",
    ),
    (
        "S04,S06,S07",
        "dependency occurrence ledger, closure, SCC, dependency-first plan",
        "0/1/N/direct/multihop/order/hash-seed/termination tests",
        "none",
        "exact local closure/load order is complete, deterministic, and private",
    ),
    (
        "S08",
        "conflict/cycle/rejection/cascade adapter",
        "duplicate/pin/physical/self-cycle/multi-cycle/diamond/blocker-root tests",
        "none",
        "no-winner algebra and existing module diagnostic compatibility pass",
    ),
    (
        "S05,S08,S09",
        "single package inspection projection/serializer",
        "canonical bytes/root-mixing/order/multiplicity/privacy tests",
        "none",
        "one deterministic private root-derived representation passes",
    ),
    (
        "S02-S10",
        "pure value/evaluator/reference harness and integration hardening",
        "differential/property/schema1/schema2/E2E/package-smoke tests",
        "vector authoring may parallelize by disjoint dimensions after interfaces freeze; merge/publication sequential",
        "all behavioral matrices and compatibility locks converge on one exact tree",
    ),
    (
        "S01-S11 completed",
        "status/completion/handoff authority only",
        "completion, inventory, privacy, retained-owner, reader/hash/topology audit",
        "none",
        "exact reviewed publication proves Phase 55 `COMPLETED` and next Phase 56 Gate 0/Gate 1",
    ),
)

REJECTION_VALUES = (
    "ACTIVATION_SCHEMA",
    "MANIFEST_MISSING",
    "MANIFEST_NOT_REGULAR",
    "MANIFEST_CHANGED",
    "MANIFEST_TOO_LARGE",
    "MANIFEST_INVALID_UTF8",
    "MANIFEST_INVALID_TOML",
    "MANIFEST_SCHEMA",
    "PACKAGE_IDENTITY",
    "PACKAGE_VERSION",
    "ASSET_SCHEMA",
    "ASSET_UNKNOWN_KIND",
    "ASSET_DUPLICATE",
    "ASSET_MISSING",
    "LOCATOR_INVALID",
    "LOCATOR_ESCAPE",
    "ROOT_OR_LOCATOR_MUTATED",
    "OPENED_IDENTITY_MISMATCH",
    "ASSET_CHANGED",
    "PACKAGE_DIGEST_MISMATCH",
    "DEPENDENCY_DUPLICATE",
    "DEPENDENCY_PIN_CONFLICT",
    "DEPENDENCY_MISSING",
    "RELEASE_PHYSICAL_CONFLICT",
    "DEPENDENCY_CYCLE",
    "DEPENDENCY_BLOCKED",
    "MODULE_REJECTED",
)

ADDED_PATHS = {
    PLAN_REL,
    SPEC_REL,
    SELF_REL,
}
NON_READER_MODIFIED_PATHS = {
    README_REL,
    ROADMAP_REL,
    LANGUAGE_REL,
    "tests/_phase54_active_gate2_manifest.py",
    "tests/test_phase54_completion_audit_status_lock_and_phase55_handoff.py",
}


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _section(relative: str, heading: str) -> str:
    text = _read(relative)
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^## (?!#)|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, (relative, heading)
    return match.group("body")


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(relative),
            flags=re.MULTILINE,
        )
    )


def _decision(heading: str) -> str:
    text = _read(SPEC_REL)
    match = re.search(
        rf"^### {re.escape(heading)}\s*$\n(?P<body>.*?)(?=^#{{2,3}} (?!#)|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, heading
    return match.group("body")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _classification_rows() -> tuple[tuple[str, str, str, str], ...]:
    section = _section(
        SPEC_REL, "Phase-start Expansion Pull-forward And Readiness Audit"
    )
    rows: list[tuple[str, str, str, str]] = []
    for line in section.splitlines():
        match = re.fullmatch(
            r"\| ([IPCDO]\d{2}) \| ([^|]+?) \| `([A-Z_]+)` \| (.+) \|",
            line,
        )
        if match is not None:
            rows.append(
                (
                    match.group(1).strip(),
                    match.group(2).strip(),
                    match.group(3).strip(),
                    match.group(4).strip(),
                )
            )
    return tuple(rows)


def test_slice1_titles_headings_and_unpublished_lifecycle_are_exact() -> None:
    assert _headings(PLAN_REL, 1) == (f"Phase 55 — {PHASE_TITLE}",)
    assert _headings(SPEC_REL, 1) == (f"Phase 55 Slice 1 {SLICE_TITLE} v1",)
    lifecycle = _flat(_section(SPEC_REL, "Gate 2 Lifecycle And Conditional Activation"))
    for phrase in (
        "Phase 54 is `COMPLETED`",
        "Phase 55 is `UNSTARTED`",
        "`IMPLEMENTED_UNPUBLISHED`",
        "`PHASE55_SLICE1_GATE3`",
        "Phase 55 ACTIVE / Slice 1 COMPLETED",
        "`next=PHASE55_SLICE2_GATE0_GATE1`",
    ):
        assert phrase in lifecycle
    roadmap = _flat(
        _section(ROADMAP_REL, "Phase 55 Slice 1 Gate 2 Candidate And Pending Gate 3")
    )
    assert (
        "Where it names `PHASE55_GATE0_GATE1` as the sole next authorization, this section supersedes it"
        in roadmap
    )


def test_authority_hierarchy_baseline_and_historical_dispositions_are_exact() -> None:
    authority = _section(SPEC_REL, "Authority Hierarchy And Historical Dispositions")
    expected = (
        "AGENTS.md",
        "live Git and repository state",
        "active roadmap and current phase authorities",
        "immutable evidence",
        "live GitHub and CI",
        "initiating request",
        "historical summaries and runtime journals",
    )
    assert tuple(authority.index(item) for item in expected) == tuple(
        sorted(authority.index(item) for item in expected)
    )
    baseline = _section(SPEC_REL, "Trusted Baseline And Binding Evidence")
    for identity in (
        "364296e69f7e289395661518031dafeb66a216cc",
        "4c9c784851c948bd535f8d3a6e12a936e0dd70bf",
        "2f0ea671d1325029d10ccb6694eef648e1d6c6ed",
        "a18c4ed55b952889965df3484cd71ec3d26c32cea932cbbbaef5ad2ea07cbec9",
    ):
        assert identity in baseline
    assert "NON_LOAD_BEARING_HISTORICAL_RECORD_ERROR" in authority
    assert "one-run fixture setup error" in authority


def test_current_production_readiness_and_retained_later_ledgers_are_complete() -> None:
    ledgers = (
        ("Current Production Ledger", tuple(f"CP{i:02}" for i in range(1, 10))),
        ("Current Readiness Ledger", tuple(f"CR{i:02}" for i in range(1, 9))),
        ("Retained Later Ledger", tuple(f"RL{i}" for i in range(56, 71))),
    )
    for heading, identifiers in ledgers:
        section = _section(SPEC_REL, heading)
        positions = tuple(section.index(identifier) for identifier in identifiers)
        assert positions == tuple(sorted(positions))
        assert all(section.count(identifier) == 1 for identifier in identifiers)
        for identifier, anchor in LEDGER_ANCHORS[heading].items():
            assert f"{identifier} — {anchor}" in section
    boundary = _flat(_section(SPEC_REL, "Current Production Ledger"))
    assert "no semantic package manifest or loader" in boundary
    inherited = _section(SPEC_REL, "Phase 54 Inherited-asset Dispositions")
    inherited_rows = tuple(
        tuple(part.strip() for part in line.strip("|").split("|"))
        for line in inherited.splitlines()
        if re.match(r"^\| (?:0[1-9]|1[0-9]|20) \|", line)
    )
    assert tuple(row[0] for row in inherited_rows) == tuple(
        f"{position:02}" for position in range(1, 21)
    )
    assert tuple(row[2] for row in inherited_rows) == (
        "`DIRECTLY_REUSABLE`",
        "`DIRECTLY_REUSABLE`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`DIRECTLY_REUSABLE`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`DIRECTLY_REUSABLE`",
        "`DIRECTLY_REUSABLE`",
        "`READINESS_ONLY_NOT_PRODUCT`",
        "`DIRECTLY_REUSABLE`",
        "`MISMATCHED_REQUIRES_PHASE55_REDESIGN`",
        "`MISMATCHED_REQUIRES_PHASE55_REDESIGN`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`READINESS_ONLY_NOT_PRODUCT`",
        "`READINESS_ONLY_NOT_PRODUCT`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`REUSABLE_AFTER_PHASE55_EXTENSION`",
        "`READINESS_ONLY_NOT_PRODUCT`",
        "`IRRELEVANT_TO_PHASE55`",
    )
    assert (
        inherited_rows[12][1]
        == "`ProjectLayeredAssetKind` `MODULE_SOURCE`/`NOMINAL_DECLARATION` carrier as final package taxonomy"
    )


def test_five_way_ledger_is_complete_unique_and_necessity_based() -> None:
    rows = _classification_rows()
    assert tuple(row[0] for row in rows) == EXPECTED_CLASSIFICATION_IDS
    assert len(rows) == len({row[0] for row in rows}) == 47
    assert {
        identifier: (owner, classification)
        for identifier, owner, classification, _detail in rows
    } == EXPECTED_OWNER_CLASSIFICATION
    assert set(row[2] for row in rows) == set(CLASSIFICATIONS)
    assert Counter(row[2] for row in rows) == EXPECTED_CLASSIFICATION_TOTALS
    for identifier, _owner, classification, detail in rows:
        if classification == "DEFER_BY_NECESSITY":
            assert identifier.startswith("D")
            assert DEFERRED_ANCHORS[identifier] in detail
            assert any(
                term in detail for term in ("requires", "missing", "remain unresolved")
            )
            assert not re.fullmatch(r"Phase \d+", detail)


def test_maximum_safe_pull_forward_is_exactly_twenty_eight_rows() -> None:
    section = _flat(_section(SPEC_REL, "Maximum Safe Pull-forward Boundary"))
    assert "exactly 28 rows" in section
    assert "`I01-I11 + P01-P09 + C01-C08`" in section
    for excluded in (
        "public artifact",
        "package graph product",
        "remote operation",
        "solver",
        "lockfile",
        "production Rust",
        "dialect",
        "release",
    ):
        assert excluded in section


def test_product_decisions_p01_through_p04_activation_manifest_are_exact() -> None:
    sections = tuple(
        _flat(_decision(heading))
        for heading in (
            "P01 — Explicit Activation",
            "P02 — Compatibility",
            "P03 — Root Activation Form",
            "P04 — Manifest Form",
        )
    )
    assert (
        "`pietto.toml` `schema_version = 3` is the sole package activation"
        in sections[0]
    )
    assert "exactly one `[package]`" in sections[0]
    assert "Schema v1 remains exact legacy-flat" in sections[1]
    assert "Schema v2 remains exact explicit-modules" in sections[1]
    for phrase in (
        "Schema v3 rejects `[sources]`",
        "schema v1/v2 reject package keys",
        "A manifest present without schema v3 is ignored",
        "Schema v3 with a missing manifest fails",
    ):
        assert phrase in sections[1]
    assert (
        "Heuristic, ambient, directory, and mixed activation are forbidden"
        in sections[1]
    )
    for field in ("`path`", "`namespace`", "`name`", "`version`", "`sha256`"):
        assert field in sections[2]
    for phrase in (
        "`pietto-package.toml`",
        "strict UTF-8 TOML",
        "`schema_version = 1`",
        "ordered `[[assets]]`",
        "ordered `[[dependencies]]`",
        "1048576 bytes",
    ):
        assert phrase in sections[3]


def test_product_decisions_p05_through_p08_identity_modules_assets_are_exact() -> None:
    normalization = _flat(_decision("P05 — Normalization"))
    assert "[a-z0-9]+(?:-[a-z0-9]+)*" in normalization
    assert "canonical SemVer 2.0.0 string" in normalization
    assert "compared by exact string" in normalization
    identity = _flat(_decision("P06 — Package Identity"))
    assert "Locator/physical inode and digest never become logical identity" in identity
    modules = _flat(_decision("P07 — Module Ownership And Identity"))
    assert "Existing `ProjectModuleIdentity` remains path-only" in modules
    assert (
        "`PackageModuleIdentity = (PackageReleaseIdentity, ProjectModuleIdentity)`"
        in modules
    )
    assets = _flat(_decision("P08 — Closed Typed Assets"))
    assert "`{module_source}` (`MODULE_SOURCE`)" in assets
    assert "not parallel assets" in assets
    assert "Phase 66 may add kinds only through a new manifest schema" in assets


def test_product_decisions_p09_through_p12_dependencies_locators_loading_are_exact() -> (
    None
):
    dependencies = _flat(_decision("P09 — Exact Dependencies"))
    for phrase in (
        "declaration ordinal",
        "required lowercase SHA-256",
        "Source order and multiplicity",
        "There are no aliases, optional/dev/peer roles, ranges, feature flags, asset selectors, solving, lockfile, or preferred-version selection",
    ):
        assert phrase in dependencies
    locators = _flat(_decision("P10 — Local Locators"))
    for phrase in (
        "`LOCAL_DIRECTORY` only",
        "project-relative",
        "manifest-directory-relative",
        "package-root-relative",
    ):
        assert phrase in locators
    for phrase in (
        "once-pinned project root",
        "cannot escape",
        "Absolute paths",
        "URIs",
        "unchecked symlinks",
    ):
        assert phrase in locators
    loading = _flat(_decision("P11 — Trusted Loading"))
    assert (
        "Compose the Phase 54 trust operations rather than duplicating them" in loading
    )
    for phrase in (
        "regular non-symlink manifest",
        "no-follow descriptor traversal",
        "final fstat",
        "reverify roots and leaves",
    ):
        assert phrase in loading
    assert "no partial accepted package" in loading
    closure = _flat(_decision("P12 — Dependency Closure Ordering And Conflicts"))
    for phrase in (
        "finite iterative worklist",
        "SCC analysis is iterative",
        "dependency-first topological order",
        "fails with no winner",
    ):
        assert phrase in closure
    for phrase in (
        "`(namespace, name, exact_version)`",
        "reached by a diamond loads once",
        "same release/digest at different physical roots",
        "Different exact versions are distinct and may coexist",
    ):
        assert phrase in closure


def test_product_decisions_p13_p14_diagnostics_privacy_and_boundary_are_exact() -> None:
    diagnostics = _flat(_decision("P13 — Diagnostics And Rejections"))
    assert "No new `PIE-*` range is created by this decision" in diagnostics
    assert (
        "`PIE-S2701` through `PIE-S2707` retain their exact module meanings"
        in diagnostics
    )
    privacy = _flat(_decision("P14 — Public Private And Later Ownership"))
    assert "user-authored input schemas" in privacy
    for private in (
        "Normalized carriers",
        "content digests",
        "load plans",
        "rejection values",
        "vectors",
    ):
        assert private in privacy
    static = _flat(_section(SPEC_REL, "Static-only Slice 1 Boundary"))
    assert "implements no Phase 55 package behavior" in _flat(_read(SPEC_REL))
    for forbidden in (
        "production source",
        "grammar",
        "generated parser",
        "dependency",
        "workflow",
        "version",
    ):
        assert forbidden in static


def test_architecture_decisions_a01_through_a04_root_identity_islands_digest_are_exact() -> (
    None
):
    root = _flat(_decision("A01 — One Authority Root And Derived Projections"))
    assert "never independent authorities" in root
    identities = _flat(_decision("A02 — Layered Identities"))
    assert "never alias one another" in identities
    islands = _flat(_decision("A03 — Package Compilation Islands"))
    assert "root-package output remains the only project result" in islands
    digest = _flat(_decision("A04 — Domain-separated Content Digest"))
    for phrase in (
        "`pietto.package.content.v1`",
        "length-framed",
        "relocation",
        "never embeds its own digest",
    ):
        assert phrase in digest


def test_architecture_decisions_a05_through_a08_algebras_are_exact() -> None:
    collections = _flat(_decision("A05 — Collection Algebra"))
    assert "tuples preserving exact order and multiplicity" in collections
    closure = _flat(_decision("A06 — Iterative Deterministic Closure"))
    assert "dict/set iteration is never observable order" in closure
    conflicts = _flat(_decision("A07 — No-winner Conflict Algebra"))
    assert "have no preferred package, locator, version, or edge" in conflicts
    algebra = _decision("A08 — Closed Private Rejection Algebra")
    actual = tuple(line for line in algebra.splitlines() if line in REJECTION_VALUES)
    assert actual == REJECTION_VALUES
    assert len(actual) == len(set(actual)) == 27
    for host_fact in (
        "host path",
        "inode",
        "exception",
        "locale",
        "timestamp",
        "rendered diagnostic payload",
    ):
        assert host_fact in algebra


def test_architecture_decisions_a09_through_a11_private_pure_gate_are_exact() -> None:
    inspection = _flat(_decision("A09 — One Private Inspection Family"))
    assert "Exactly one deterministic package projection/serializer" in inspection
    assert (
        "neither the Phase 58 public artifact nor a manifest reserializer" in inspection
    )
    pure = _flat(_decision("A10 — Pure And Differential Boundary"))
    assert "One total pure evaluator" in pure
    assert "No Rust, Cargo, or FFI production exists" in pure
    gate = _flat(_decision("A11 — Active Gate And Publication Workflow"))
    for phrase in (
        "dirty `main`",
        "empty real index",
        "Gate 3 alone owns the topic branch",
        "every frozen Phase 54 historical projection remains unchanged",
    ):
        assert phrase in gate


def test_phase55_phase59_phase67_phase68_and_later_boundaries_are_exact() -> None:
    section = _flat(_section(SPEC_REL, "Phase 55 Versus Phase 59 67 And 68"))
    for phrase in (
        "Phase 59 retains a queryable package graph",
        "`PackageLoadPlan` is not that product",
        "Phase 67 retains registry",
        "`LOCAL_DIRECTORY` is the only Phase 55 locator kind",
        "Phase 68 retains ranges",
        "Exact release/digest pins",
    ):
        assert phrase in section
    readiness = _section(SPEC_REL, "Phase 56 Through 70 Readiness Pulled Forward")
    for phase in range(56, 71):
        if phase in (60, 61, 62, 63, 64, 65, 69, 70):
            continue
        assert f"Phase {phase}" in readiness
    assert "Phases 60-65" in readiness
    assert "Phases 69-70" in readiness


def test_route_screen_and_selected_twelve_slice_route_are_exact() -> None:
    screen = _section(SPEC_REL, "Route Screen Eight Through Sixteen")
    expected_screen_rows = (
        (
            "8",
            "`REJECTED_HARD_GATE`",
            "not scored",
            "over-merges activation/manifest and dependency/trust/conflict owners",
        ),
        (
            "9",
            "`QUALIFIED`",
            "48; `4/3/4/3/3/3/3/3/4`",
            "merges identity/assets and loader/load-plan owners",
        ),
        (
            "10",
            "`QUALIFIED`",
            "54; `4/4/4/4/3/4/3/4/4`",
            "merges dependency declaration with conflict/cycle diagnostics",
        ),
        (
            "11",
            "`QUALIFIED`",
            "60; `4/4/5/4/4/4/4/4/5`",
            "merges inspection with pure/differential/compatibility hardening",
        ),
        (
            "12",
            "`QUALIFIED_SELECTED`",
            "67; `5/5/5/5/4/5/4/4/5`",
            "every authority root has a coherent production/test boundary",
        ),
        (
            "13",
            "`QUALIFIED_EXCEPTIONAL`",
            "65; `5/5/5/5/4/5/3/3/5`",
            "valid loader/module split adds reader/CI cost without improvement",
        ),
        (
            "14",
            "`QUALIFIED_EXCEPTIONAL`",
            "64; `5/5/5/5/4/5/3/2/5`",
            "valid dependency/traversal split adds an unjustified publication boundary",
        ),
        (
            "15",
            "`REJECTED_HARD_GATE`",
            "not scored",
            "splits one rejection algebra into an unverifiable slice",
        ),
        (
            "16",
            "`REJECTED_HARD_GATE`",
            "not scored",
            "divides one asset authority root as padding",
        ),
    )
    screen_rows = tuple(
        tuple(part.strip() for part in line.strip("|").split("|"))
        for line in screen.splitlines()
        if re.match(r"^\| (?:8|9|10|11|12|13|14|15|16) \|", line)
    )
    assert screen_rows == expected_screen_rows
    route = _section(SPEC_REL, "Exact Twelve-slice Route Ownership And Prerequisites")
    route_rows = tuple(
        tuple(part.strip() for part in line.strip("|").split("|"))
        for line in route.splitlines()
        if re.match(r"^\| (?:[1-9]|1[0-2]) \|", line)
    )
    assert len(route_rows) == 12
    assert tuple(
        (int(number), title, prerequisites, production, test, parallelism, completion)
        for number, title, prerequisites, production, test, parallelism, completion in route_rows
    ) == tuple(
        (number, ROUTE[number - 1], *ROUTE_DETAILS[number - 1])
        for number in range(1, 13)
    )
    assert "publication is sequential" in _flat(route).lower()
    workflow = _flat(_section(SPEC_REL, "Three-round Risk-adaptive Workflow"))
    assert "Slices 1 through 10 use three rounds" in workflow
    assert "Slices 11 and 12 remain risk-adaptive" in workflow
    assert (
        "purely test/docs hardening or completion tree may combine Round 1 planning"
        in workflow
    )
    assert "only when that Slice's own Gate 1 explicitly authorizes" in workflow


def test_active_gate_allowlist_and_static_non_behavior_guards_are_exact() -> None:
    assert active_gate.PHASE55_ACTIVE_GATE2_MARKER == "PHASE55_SLICE1_GATE2"
    assert (
        active_gate.PHASE55_ACTIVE_GATE2_BASE
        == "364296e69f7e289395661518031dafeb66a216cc"
    )
    assert (
        active_gate.PHASE55_ACTIVE_GATE2_BRANCH
        == "phase55/slice1-scope-authority-expansion-readiness-route-lock"
    )
    assert (
        active_gate.PHASE55_ACTIVE_GATE2_SUBJECT
        == "Add Phase 55 scope authority and route lock"
    )
    assert active_gate.PHASE55_ACTIVE_GATE3_AUTHORIZED_DIRECT_PARENTS == frozenset(
        {
            "364296e69f7e289395661518031dafeb66a216cc",
            "e835a14ac0dda2448c50307bb7ca3814931d2fbf",
            "512220ae2c176e3f2793b174907d4125fc27b2f4",
            "8ea4ead07d29b7ff08bc798bbee15fc002fba4d0",
        }
    )
    assert (
        active_gate.phase54_publication_topic_branch()
        == active_gate.PHASE55_ACTIVE_GATE2_BRANCH
    )
    assert set(active_gate.PHASE55_ACTIVE_GATE2_ADDED_PATHS) == ADDED_PATHS
    assert (
        set(active_gate.PHASE55_ACTIVE_GATE2_NON_READER_MODIFIED_PATHS)
        == NON_READER_MODIFIED_PATHS
    )
    assert len(active_gate.PHASE55_ACTIVE_GATE2_READER_PATHS) == 47
    assert len(active_gate.PHASE55_ACTIVE_GATE2_MODIFIED_PATHS) == 52
    assert len(active_gate.PHASE55_ACTIVE_GATE2_ALLOWLIST_PATHS) == 55
    assert (
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py"
        in active_gate.PHASE55_ACTIVE_GATE2_READER_PATHS
    )
    assert active_gate.PHASE55_ACTIVE_GATE2_DELETED_PATHS == frozenset()
    assert not ADDED_PATHS & set(active_gate.PHASE55_ACTIVE_GATE2_MODIFIED_PATHS)
    assert all(
        path.startswith("tests/")
        for path in active_gate.PHASE55_ACTIVE_GATE2_READER_PATHS
    )
    for path in active_gate.PHASE55_ACTIVE_GATE2_ALLOWLIST_PATHS:
        assert not path.startswith(
            ("src/", "grammar/", "tests/fixtures/", ".github/", "scripts/")
        )

    head = "a" * 40
    tree = "b" * 40
    git_outputs = {
        ("rev-parse", "HEAD"): head,
        ("rev-list", "--parents", "-n", "1", head): (
            f"{head} {active_gate.PHASE55_ACTIVE_GATE2_BASE}"
        ),
        ("show", "-s", "--format=%s", head): active_gate.PHASE55_ACTIVE_GATE2_SUBJECT,
        ("rev-parse", f"{head}^{{tree}}"): tree,
        ("rev-parse", "--is-shallow-repository"): "false",
    }

    def output(arguments: list[str]) -> str:
        return git_outputs[tuple(arguments)]

    with (
        patch.object(active_gate, "PHASE55_ACTIVE_GATE2_REVIEWED_TREE_TRAILER", "P55"),
        patch.object(active_gate, "PHASE54_ACTIVE_GATE2_REVIEWED_TREE_TRAILER", "P54"),
        patch.object(active_gate, "_git_output", side_effect=output),
        patch.object(
            active_gate,
            "_git_commit_message",
            return_value=f"{active_gate.PHASE55_ACTIVE_GATE2_SUBJECT}\n\nP55: {tree}\n",
        ) as commit_message_mock,
    ):
        assert active_gate.phase54_active_gate2_publication_commit_is_head()
        commit_message_mock.return_value = (
            f"{active_gate.PHASE55_ACTIVE_GATE2_SUBJECT}\n\nP54: {tree}\n"
        )
        assert not active_gate.phase54_active_gate2_publication_commit_is_head()

    repair_head = "c" * 40
    repair_parent = active_gate.PHASE55_ACTIVE_GATE2_BASE
    repair_tree = "e" * 40
    repair_state = active_gate.Phase54Gate2RepositoryState(
        marker=active_gate.PHASE55_ACTIVE_GATE2_MARKER,
        branch_oid=repair_head,
        branch_head=active_gate.PHASE55_ACTIVE_GATE2_BRANCH,
        branch_upstream=f"origin/{active_gate.PHASE55_ACTIVE_GATE2_BRANCH}",
        ahead=0,
        behind=0,
        added_paths=frozenset(),
        modified_paths=frozenset(),
        deleted_paths=frozenset(),
        staged_paths=frozenset(),
        other_paths=frozenset(),
        worktree_count=1,
        shallow=False,
        active_git_operation=False,
    )
    repair_git_outputs = {
        ("rev-parse", "--abbrev-ref", "HEAD"): active_gate.PHASE55_ACTIVE_GATE2_BRANCH,
        ("rev-parse", "HEAD"): repair_head,
        ("rev-list", "--parents", "-n", "1", repair_head): (
            f"{repair_head} {repair_parent}"
        ),
        ("show", "-s", "--format=%s", repair_head): (
            active_gate.PHASE55_ACTIVE_GATE2_SUBJECT
        ),
        ("rev-parse", f"{repair_head}^{{tree}}"): repair_tree,
        ("rev-parse", "--verify", "refs/heads/main"): (
            active_gate.PHASE55_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--verify", "refs/remotes/origin/main"): (
            active_gate.PHASE55_ACTIVE_GATE2_BASE
        ),
        ("rev-parse", "--is-shallow-repository"): "false",
        ("rev-list", "--first-parent", repair_head): (
            f"{repair_head} {repair_parent} {active_gate.PHASE55_ACTIVE_GATE2_BASE}"
        ),
    }

    def repair_output(arguments: list[str]) -> str:
        return repair_git_outputs[tuple(arguments)]

    with (
        patch.object(active_gate, "_git_output", side_effect=repair_output),
        patch.object(
            active_gate,
            "_git_commit_message",
            return_value=(
                f"{active_gate.PHASE55_ACTIVE_GATE2_SUBJECT}\n\n"
                f"{active_gate.PHASE55_ACTIVE_GATE2_REVIEWED_TREE_TRAILER}: "
                f"{repair_tree}\n"
            ),
        ),
    ):
        for repair_parent in active_gate.PHASE55_ACTIVE_GATE3_AUTHORIZED_DIRECT_PARENTS:
            repair_git_outputs[("rev-list", "--parents", "-n", "1", repair_head)] = (
                f"{repair_head} {repair_parent}"
            )
            assert active_gate._matches_phase55_active_gate2_clean_topic(repair_state)
            assert active_gate.phase54_active_gate2_publication_commit_is_head()
        assert not active_gate._matches_phase55_active_gate2_clean_topic(
            replace(repair_state, branch_oid="f" * 40)
        )
        repair_parent = "d" * 40
        repair_git_outputs[("rev-list", "--parents", "-n", "1", repair_head)] = (
            f"{repair_head} {repair_parent}"
        )
        repair_git_outputs[("rev-list", "--first-parent", repair_head)] = (
            f"{repair_head} {repair_parent} {active_gate.PHASE55_ACTIVE_GATE2_BASE}"
        )
        assert not active_gate._matches_phase55_active_gate2_clean_topic(repair_state)
        assert not active_gate.phase54_active_gate2_publication_commit_is_head()
        repair_git_outputs[("rev-list", "--parents", "-n", "1", repair_head)] = (
            f"{repair_head} {active_gate.PHASE55_ACTIVE_GATE2_BASE} {'f' * 40}"
        )
        assert not active_gate._matches_phase55_active_gate2_clean_topic(repair_state)
        assert not active_gate.phase54_active_gate2_publication_commit_is_head()

    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert project["version"] == "0.1.0"
    assert project["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert tuple(
        path.name for path in (REPO_ROOT / ".github/workflows").glob("*.yml")
    ) == ("ci.yml",)
    assert not any(
        (REPO_ROOT / name).exists()
        for name in ("Cargo.toml", "Cargo.lock", "pietto.lock")
    )

    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    tests = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(tests) == len({node.name for node in tests}) == 15
    assert all(not node.decorator_list for node in tests)

    evidence = _flat(_section(SPEC_REL, "Evidence And Gate 3 Contract"))
    assert (
        "pietto-phase55-slice1-gate2-scope-authority-expansion-readiness-and-route-lock.txt"
        in evidence
    )
    assert "O_CREAT | O_EXCL | O_NOFOLLOW" in evidence
    assert "exactly one terminal at EOF" in evidence
