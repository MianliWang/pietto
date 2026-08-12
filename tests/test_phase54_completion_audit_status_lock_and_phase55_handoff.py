"""Phase 54 Slice 16 completion audit, status lock, and Phase 55 handoff.

Every assertion here is static. The module reads repository authority documents,
the published Python package surface, and tracked inventories; it starts no
process that mutates the repository and it asserts no Phase 55 behavior.
"""

from __future__ import annotations

import ast
import hashlib
import re
import tomllib
from pathlib import Path

from _phase54_active_gate2_manifest import (
    ADDED_PATHS,
    MECHANICAL_READER_PATHS,
    NON_READER_MODIFIED_PATHS,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_ACTIVE_GATE2_BRANCH,
    PHASE54_ACTIVE_GATE2_MARKER,
    PHASE54_ACTIVE_GATE2_SUBJECT,
)

import pietto
import pietto.ir as ir_package
import pietto.semantic as semantic_package
import pietto.sql as sql_package
from pietto._project.model import ProjectSemanticResult


REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = "tests/test_phase54_completion_audit_status_lock_and_phase55_handoff.py"
SPEC_REL = (
    "docs/spec/phase54-slice16-completion-audit-status-lock-and-phase55-handoff-v1.md"
)
SPEC_TITLE = "Phase 54 Slice 16 Completion Audit, Status Lock, And Phase 55 Handoff v1"
PLAN_REL = "docs/plan/phase-54-local-import-module-export-foundation.md"
ROADMAP_REL = "docs/spec/pietto-active-roadmap-phase53-70-v2.md"
README_REL = "README.md"
LANGUAGE_SPEC_REL = "docs/spec/pietto-v0.9.md"
GOVERNANCE_REL = (
    "docs/spec/pietto-phase-start-expansion-pull-forward-readiness-governance-v1.md"
)
CONVERGENCE_REL = "docs/spec/pietto-semantic-slice-convergence-governance-v1.md"

PHASE53_COMPLETION_COMMIT = "af92f30c22e5d3df5219554a0663855a5b9f51a6"
SLICE15_COMMIT = "1f69c0316086a2236cee03a96cca95218fbd50fc"
SLICE15_TREE = "205a087963a52d046cd79ede443c81191e9206af"
SLICE15_PARENT = "93f0f591e28a01f32d1698fcd4b8c57d41c6d714"

# The exact ordered Phase 54 slice publication commits, Slice 1 through Slice 15.
SLICE_PUBLICATION_COMMITS: tuple[str, ...] = (
    "53d8767fc3bdbe5e3f631178652222bbe51f6a33",
    "d8a5e9ab3de70ce30575513c73560c86430eca63",
    "2752985c3f6343519b7d7d6fe400d16251e64d85",
    "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
    "c44a4271d9592cb393d2232f127a59d8466cc60a",
    "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
    "027b33cafcfd58916a89e299487dad38d24ade6c",
    "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
    "fadb1924af057cfc901a1658e117810d699e2358",
    "b81843acadb294630db361c09949868d004b1bca",
    "bc46faff1c9aa71f583ed7d2964b651cc659bc90",
    "bd6bdcf17361b11d3067beec534432d37ffe6f05",
    "040ab19c56519c39c56541979c850484f9cc47f0",
    "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
    "1f69c0316086a2236cee03a96cca95218fbd50fc",
)

# Non-slice first-parent commits inside the Phase 54 range.
NON_SLICE_COMMITS: tuple[str, ...] = (
    "15bae172ee151e370fe59d3bf909d735aee6aa90",
    "f280bd7c21ffbf8354356f1e1b7391beb52cd911",
    "0bad854253e22347e2aff93e2eabcbe2fda55aed",
)

PHASE54_ROUTE: tuple[str, ...] = (
    "Scope, Authority, Phase-start Expansion Audit, Decisions, Activation, And Route Lock",
    "Schema-v2 Explicit-module Activation And Immutable Project / Module Carrier",
    "Module Identity, Selected-input Index, Trusted Local Loader, And Path / Symlink Boundary",
    "Import / Export Contextual Grammar, Generated Parser, And Immutable AST",
    "Module-qualified Nominal Declaration Identity And Per-module Catalogs",
    "Local Export Eligibility, Visibility, Explicit Named Re-export, And Facade Semantics",
    "Named Imports, Aliases, Binding Environments, And Collision Rules",
    "Module Graph, Cycles, Diagnostics, And Deterministic Ordering",
    "Cross-module Type Alias, Enum, Shape, And Source Resolution",
    "Cross-module Table / Query / Relation Resolution, Row Facts, And Legacy Compatibility",
    "Module Attribution, Dependency, Origin, Provenance, And Lineage",
    "Generic-signature, Nullability, Aggregate, Grouped, Window, Result-role, And Capability-fact Preservation",
    "Package-neutral Identity Layering, Owner / Asset-compatible Carriers, Source Digest, And Loader Readiness",
    "Private Module Inspection And Canonical Serialization",
    "Rust-ready Pure Boundaries, Differential Vectors, And End-to-end Hardening",
    "Completion Audit, Status Lock, And Phase 55 Handoff",
)

# The eleven all-or-none private module sidecars on ProjectSemanticResult.
MODULE_SIDECAR_FIELDS: tuple[str, ...] = (
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

MODULE_DIAGNOSTIC_CODES: tuple[str, ...] = tuple(
    f"PIE-S270{position}" for position in range(1, 8)
)

BYTE_IDENTICAL_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    "Makefile",
    "grammar/Pietto.g4",
    "pyproject.toml",
    "pyrightconfig.json",
    "pyrightconfig.tests.json",
    "uv.lock",
    ".python-version",
    ".github/workflows/ci.yml",
)

PHASE55_70_OWNERS: tuple[tuple[int, str], ...] = (
    (55, "Semantic Package Asset Schema And Deterministic Local Loading"),
    (56, "Capability Profile Static Schema And Declared Checking"),
    (57, "PostgreSQL Extension Signature Catalog Foundation"),
    (58, "Public Explain / Portability / Package Inspection Artifact v1"),
    (59, "Local Package Graph, Attribution, Provenance, And Lineage"),
    (
        60,
        "Advanced Window Frames And Phase 51–60 Ecosystem / Release Readiness Checkpoint",
    ),
    (61, "Project IR And Semantic Composition Foundation"),
    (62, "Relationship, JOIN, Grain, And Fanout-safe Semantics"),
    (63, "Multi-relation SQL Artifacts, Project Emit-SQL, And QUALIFY Lowering"),
    (64, "Advanced Generic Types, Coercion, Temporal, Decimal, And Native Mapping"),
    (65, "Advanced Aggregation And Grouping"),
    (66, "Advanced Module And Semantic-package Assets"),
    (67, "Remote Package Manager, Registry, Fetch, Install, Cache, And Trust Boundary"),
    (
        68,
        "Dependency Ranges, Version Solver, Canonical Lockfile, And First Rust Kernel",
    ),
    (69, "Extension-specific Lowering And Additional Dialect Backend Foundation"),
    (
        70,
        "Public Schema / Lineage / Attribution Expansion, Ecosystem Completion Audit,"
        " Rust Migration Decision, And v0.2 Release Readiness",
    ),
)

FORBIDDEN_REPOSITORY_PATHS: tuple[str, ...] = (
    "Cargo.toml",
    "Cargo.lock",
    "rust-toolchain.toml",
    "src/lib.rs",
    "pietto.lock",
    "pietto-lock.toml",
)

PUBLIC_SERIALIZER_PATHS: tuple[str, ...] = (
    "src/pietto/cli_json.py",
    "src/pietto/_project/json_v2.py",
    "src/pietto/_metadata/serializer.py",
)

FORBIDDEN_PRODUCTION_IMPORTS: tuple[str, ...] = (
    "http",
    "httpx",
    "requests",
    "socket",
    "ssl",
    "subprocess",
    "urllib",
    "urllib3",
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    """Return the exact headings at one level, never a lower or deeper level."""

    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$", _read(relative), flags=re.MULTILINE
        )
    )


def _flat(text: str) -> str:
    """Collapse whitespace so a prose lock survives Markdown reflow."""

    return re.sub(r"\s+", " ", text).strip()


def _section(relative: str, heading: str) -> str:
    source = _read(relative)
    marker = f"## {heading}\n"
    start = source.index(marker) + len(marker)
    end = source.find("\n## ", start)
    return source[start:] if end < 0 else source[start:end]


def _production_python_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts and "__pycache__" not in path.parts
    )


def _top_level_test_functions(relative: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    return tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )


def _imported_root_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_completion_specification_title_and_heading_structure_are_exact() -> None:
    assert _headings(SPEC_REL, 1) == (SPEC_TITLE,)
    spec_h2 = _headings(SPEC_REL, 2)
    assert spec_h2[:4] == (
        "Purpose And Slice Identity",
        "Status And Completion Authority",
        "Trusted Slice 15 Baseline",
        "Phase 54 Sixteen-slice Route Ledger",
    )
    assert spec_h2[-4:] == (
        "Completion Invariants And Drift Locks",
        "Validation And Clean-CI Boundary",
        "Separate Authorization Boundary",
        "Stop Conditions",
    )
    for required in (
        "Publication And Repair Evidence Ledger",
        "Schema-v2 Module Foundation Closure",
        "Legacy-flat Schema-v1 Compatibility Closure",
        "Diagnostic And Behavior Closure",
        "Privacy And Public-surface Closure",
        "Serializer And Metadata Boundary Audit",
        "Generated Golden And Fixture Stability",
        "Package Workflow Dependency And Release Audit",
        "Rust And Remote-package Deferral",
        "Workflow-hardening And Evidence-governance Closure",
        "Future-owner Audit",
        "Fail-closed Non-owned Boundary Audit",
        "Reader Fixed Point And Test Accounting",
        "Completion Encoding Decision",
        "Gate 2 Pre-completion State",
        "Gate 3 Completion Condition",
        "Phase 55 Handoff",
        "Post-completion Phase 55–70 Status",
        "Exact Gate 2 Allowlist",
    ):
        assert required in spec_h2, required
    assert len(spec_h2) == len(set(spec_h2))
    # A level-2 assertion must never be satisfied by a level-3 heading.
    assert not set(_headings(SPEC_REL, 3)) & set(spec_h2)


def test_phase54_route_ledger_is_exactly_sixteen_rows_in_order() -> None:
    ledger = _section(SPEC_REL, "Phase 54 Sixteen-slice Route Ledger")
    rows = re.findall(r"^(\d+)\. (.+)$", ledger, flags=re.MULTILINE)
    assert tuple(int(index) for index, _ in rows) == tuple(range(1, 17))
    assert tuple(title for _, title in rows) == PHASE54_ROUTE
    assert len(PHASE54_ROUTE) == len(set(PHASE54_ROUTE)) == 16
    roadmap = _read(ROADMAP_REL)
    for index, title in enumerate(PHASE54_ROUTE, start=1):
        assert f"| {index} | {title} |" in roadmap, title
    plan_slice_headings = tuple(
        heading
        for heading in _headings(PLAN_REL, 2)
        if re.match(r"^Slice \d+ — ", heading)
    )
    assert plan_slice_headings == tuple(
        f"Slice {index} — {title}"
        for index, title in enumerate(PHASE54_ROUTE[1:], start=2)
    )


def test_publication_ledger_records_the_exact_first_parent_chain() -> None:
    ledger = _section(SPEC_REL, "Publication And Repair Evidence Ledger")
    assert PHASE53_COMPLETION_COMMIT in ledger
    ordered = re.findall(r"^\d+\. `([0-9a-f]{40})`$", ledger, flags=re.MULTILINE)
    assert tuple(ordered) == SLICE_PUBLICATION_COMMITS
    assert len(set(SLICE_PUBLICATION_COMMITS)) == 15
    assert SLICE_PUBLICATION_COMMITS[-1] == SLICE15_COMMIT
    assert SLICE_PUBLICATION_COMMITS[-2] == SLICE15_PARENT
    for commit in NON_SLICE_COMMITS:
        assert commit in ledger, commit
    flat_ledger = _flat(ledger)
    assert "exactly 18 commits" in flat_ledger
    assert "no merge commit, no direct `main` push, and no Dependabot merge" in (
        flat_ledger
    )
    for closed in ("38", "47", "50"):
        assert closed in ledger
    roadmap_section = _section(
        ROADMAP_REL, "Phase 54 Completion And Phase 55 Entry State"
    )
    for commit in SLICE_PUBLICATION_COMMITS:
        assert commit in roadmap_section, commit


def test_status_lock_is_consistent_across_every_live_authority_surface() -> None:
    plan_status = _section(PLAN_REL, "Status And Slice 16 Lifecycle")
    flat_plan = _flat(plan_status)
    assert "Phase 54 is `COMPLETED`" in flat_plan
    assert "Slices 1 through 16 plus the unnumbered post-Slice-12" in flat_plan
    assert "IMPLEMENTED_UNPUBLISHED" in flat_plan
    assert "PHASE55_GATE0_GATE1" in flat_plan
    assert "Slice 16 starts no Phase 55 implementation" in flat_plan
    assert "there is no post-CI status-flip commit" in flat_plan

    roadmap_status = _section(
        ROADMAP_REL, "Phase 54 Completion And Phase 55 Entry State"
    )
    flat_roadmap = _flat(roadmap_status)
    assert "Phase 54 is `COMPLETED`" in flat_roadmap
    assert "Phases 55 through 70 remain `UNSTARTED`" in flat_roadmap
    assert "PHASE55_GATE0_GATE1" in flat_roadmap
    assert "this section supersedes it" in flat_roadmap

    flat_readme = _flat(_read(README_REL))
    assert "Phase 54 is **COMPLETED**" in flat_readme
    assert "Slices 1 through 16 are **COMPLETED**" in flat_readme
    assert "PHASE55_GATE0_GATE1" in flat_readme
    assert "Gate 2 candidate" not in flat_readme
    assert "Phase 54 is **ACTIVE**" not in flat_readme

    flat_language = _flat(
        _section(LANGUAGE_SPEC_REL, "Current Phase 54 Completion Status")
    )
    assert "Phase 54 is complete and Slices 1 through 16 are complete" in flat_language
    assert "Phases 55 through 70 remain unstarted" in flat_language
    assert "Gate 2 candidate" not in flat_language

    flat_spec_status = _flat(_section(SPEC_REL, "Status And Completion Authority"))
    assert "IMPLEMENTED_UNPUBLISHED" in flat_spec_status
    assert "only through the separately authorized Gate 3 publication" in (
        flat_spec_status
    )


def test_historical_checkpoints_are_retained_and_explicitly_superseded() -> None:
    plan_status = _flat(_section(PLAN_REL, "Status And Slice 16 Lifecycle"))
    assert "retained unchanged" in plan_status
    assert "this section supersedes" in plan_status
    # The Slice 15 and Slice 14 Gate 2 checkpoints survive verbatim.
    assert "PHASE54_SLICE15_GATE2_COMPLETED_AWAITING_PUBLICATION" in plan_status
    assert "PHASE54_SLICE14_GATE2_COMPLETED_AWAITING_PUBLICATION" in plan_status
    plan = _read(PLAN_REL)
    for retained in (
        "## Slice 12 Publication Outcome And Post-Slice-12 Workflow Hardening Interlude",
        "## Slice 14 Publication Outcome And Slice 15 Gate 2 Candidate",
        "## Slice 15 Publication Outcome And Phase 54 Completion",
    ):
        assert retained in plan, retained
    outcome = _section(PLAN_REL, "Slice 15 Publication Outcome And Phase 54 Completion")
    assert SLICE15_TREE in outcome
    assert SLICE15_COMMIT in outcome
    assert SLICE15_PARENT in outcome
    assert "A5_M64_D0" in outcome
    assert "0 unresolved review threads" in outcome
    # Predecessor roadmap lineage stays immutable.
    assert (
        _sha256("docs/spec/pietto-active-roadmap-phase53-70-v1.md")
        == "67c886a05234d4513d2083a12fc0f95ad550fdd892565a6ef7c52de9631743e3"
    )


def test_every_published_slice_binds_a_specification_and_a_focused_test() -> None:
    specs = tuple(
        path.name
        for path in sorted((REPO_ROOT / "docs/spec").glob("phase54-slice*-v1.md"))
    )
    numbers = sorted(
        int(match.group(1))
        for match in (re.match(r"^phase54-slice(\d+)-", name) for name in specs)
        if match
    )
    assert numbers == list(range(1, 17))
    assert SPEC_REL.split("/")[-1] in specs
    for relative in (
        "tests/test_phase54_local_import_module_export_foundation_scope_lock.py",
        "tests/test_phase54_schema_v2_explicit_module_carrier.py",
        "tests/test_phase54_module_identity_selected_input_index_trusted_local_loader.py",
        "tests/test_phase54_import_export_contextual_grammar_ast.py",
        "tests/test_phase54_module_qualified_nominal_declaration_catalogs.py",
        "tests/test_phase54_local_export_visibility_module_facades.py",
        "tests/test_phase54_named_import_alias_binding_environments_collision_rules.py",
        "tests/test_phase54_module_graph_cycles_diagnostics_deterministic_ordering.py",
        "tests/test_phase54_cross_module_type_alias_enum_shape_source_resolution.py",
        "tests/test_phase54_cross_module_table_query_relation_resolution_row_facts_legacy_compatibility.py",
        "tests/test_phase54_module_attribution_dependency_origin_provenance_lineage.py",
        "tests/test_phase54_semantic_fact_preservation.py",
        "tests/test_phase54_package_neutral_identity_layering.py",
        "tests/test_phase54_private_module_inspection_canonical_serialization.py",
        "tests/test_phase54_rust_ready_pure_boundaries_differential_vectors.py",
        SELF_REL,
    ):
        assert (REPO_ROOT / relative).is_file(), relative


def test_eleven_private_module_sidecars_exist_and_stay_all_or_none() -> None:
    annotations = ProjectSemanticResult.__annotations__
    for field in MODULE_SIDECAR_FIELDS:
        assert field in annotations, field
    assert len(MODULE_SIDECAR_FIELDS) == len(set(MODULE_SIDECAR_FIELDS)) == 11
    model_source = _read("src/pietto/_project/model.py")
    sidecar_block = model_source[model_source.index("module_sidecars = (") :]
    for field in MODULE_SIDECAR_FIELDS:
        assert f"self.{field}," in sidecar_block, field
    closure = _section(SPEC_REL, "Schema-v2 Module Foundation Closure")
    assert "exactly eleven all-or-none module sidecars" in closure
    assert "adds no twelfth sidecar" in closure
    assert "`model=None`" in closure


def test_module_surface_is_entirely_private() -> None:
    for package in (pietto, ir_package, semantic_package, sql_package):
        declared = tuple(getattr(package, "__all__", ()))
        exported = declared or tuple(
            name for name in dir(package) if not name.startswith("_")
        )
        assert exported, package.__name__
        for name in exported:
            lowered = name.lower()
            for term in ("module", "inspect", "boundary", "vector", "facade", "import"):
                assert term not in lowered, (package.__name__, name)
    for relative in PUBLIC_SERIALIZER_PATHS:
        source = _read(relative)
        assert "module" not in source.lower(), relative
    private_modules = sorted((REPO_ROOT / "src/pietto/_project").glob("module_*.py"))
    assert len(private_modules) == 12
    for path in private_modules:
        source = path.read_text(encoding="utf-8")
        assert "__all__: tuple[str, ...] = ()" in source, path.name


def test_module_diagnostics_are_exactly_pie_s2701_through_pie_s2707() -> None:
    graph_source = _read("src/pietto/_project/module_graph.py")
    for code in MODULE_DIAGNOSTIC_CODES:
        assert code in graph_source, code
    production = "\n".join(
        path.read_text(encoding="utf-8") for path in _production_python_paths()
    )
    emitted = sorted(set(re.findall(r"PIE-S27\d\d", production)))
    assert emitted == list(MODULE_DIAGNOSTIC_CODES)
    closure = _flat(_section(SPEC_REL, "Diagnostic And Behavior Closure"))
    assert "adds, removes, renumbers, and rewords no diagnostic code" in closure
    assert "`PIE-I1000` remains the missing-semantic-fact IR boundary" in closure
    assert "`PIE-B1000` remains the malformed backend IR boundary" in closure


def test_package_version_release_and_supply_chain_posture_is_unchanged() -> None:
    with (REPO_ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    for relative in FORBIDDEN_REPOSITORY_PATHS:
        assert not (REPO_ROOT / relative).exists(), relative
    workflows = tuple(sorted((REPO_ROOT / ".github/workflows").glob("*.yml")))
    assert tuple(path.name for path in workflows) == ("ci.yml",)
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    assert len(generated) == 8
    goldens = tuple(
        path
        for path in (REPO_ROOT / "tests/fixtures/golden").rglob("*")
        if path.is_file()
    )
    assert len(goldens) == 37
    audit = _flat(_section(SPEC_REL, "Package Workflow Dependency And Release Audit"))
    for phrase in (
        "remain `0.1.0`",
        "no tag, GitHub Release, PyPI or TestPyPI publication, signing, attestation,"
        " or package upload",
        "No v1.0 readiness is claimed",
    ):
        assert phrase in audit, phrase


def test_production_source_has_no_network_or_native_boundary() -> None:
    for path in _production_python_paths():
        roots = _imported_root_modules(path)
        for forbidden in FORBIDDEN_PRODUCTION_IMPORTS:
            assert forbidden not in roots, (path.name, forbidden)
    deferral = _flat(_section(SPEC_REL, "Rust And Remote-package Deferral"))
    for phrase in (
        "No big-bang Rust rewrite",
        "`Cargo.toml`",
        "PyO3",
        "WebAssembly or C ABI",
        "subprocess protocol",
        "Phase 68 remains the preferred first production Rust component",
    ):
        assert phrase in deferral, phrase


def test_slice16_changes_no_protected_repository_fingerprint() -> None:
    for relative in BYTE_IDENTICAL_PATHS:
        assert (REPO_ROOT / relative).is_file(), relative
        assert relative not in ADDED_PATHS
        assert relative not in NON_READER_MODIFIED_PATHS
        assert relative not in MECHANICAL_READER_PATHS
    for relative in ADDED_PATHS | NON_READER_MODIFIED_PATHS | MECHANICAL_READER_PATHS:
        assert not relative.startswith("src/"), relative
        assert not relative.startswith("examples/"), relative
        assert not relative.startswith("scripts/"), relative
        assert not relative.startswith("tests/fixtures/"), relative
    invariants = _flat(_section(SPEC_REL, "Completion Invariants And Drift Locks"))
    assert "No production source byte under `src/pietto/` changes" in invariants
    assert "No file is deleted" in invariants
    assert "check-only over exact literal paths" in invariants


def test_active_gate2_manifest_targets_slice16_exactly() -> None:
    assert PHASE54_ACTIVE_GATE2_MARKER == "PHASE54_SLICE16_GATE2"
    assert PHASE54_ACTIVE_GATE2_BASE == SLICE15_COMMIT
    assert PHASE54_ACTIVE_GATE2_BRANCH == "phase54/slice16-completion-audit-status-lock"
    assert (
        PHASE54_ACTIVE_GATE2_SUBJECT == "Complete Phase 54 status and Phase 55 handoff"
    )
    assert ADDED_PATHS == {SPEC_REL, SELF_REL}
    assert NON_READER_MODIFIED_PATHS == {
        README_REL,
        PLAN_REL,
        ROADMAP_REL,
        LANGUAGE_SPEC_REL,
        "tests/_phase54_active_gate2_manifest.py",
    }
    assert not (ADDED_PATHS & MECHANICAL_READER_PATHS)
    assert not (NON_READER_MODIFIED_PATHS & MECHANICAL_READER_PATHS)
    assert all(path.startswith("tests/") for path in MECHANICAL_READER_PATHS)
    gate2 = _flat(_section(SPEC_REL, "Gate 2 Pre-completion State"))
    assert PHASE54_ACTIVE_GATE2_BRANCH in gate2
    assert PHASE54_ACTIVE_GATE2_BASE in gate2
    assert "the repository stays on `main`" in gate2
    assert "is created only at Gate 3" in gate2
    assert "empty real index" in gate2
    gate3 = _flat(_section(SPEC_REL, "Gate 3 Completion Condition"))
    assert PHASE54_ACTIVE_GATE2_SUBJECT in gate3
    assert "squash parent exactly" in gate3
    assert "fast-forward-only" in gate3


def test_workflow_hardening_and_evidence_governance_remain_closed() -> None:
    assert (REPO_ROOT / CONVERGENCE_REL).is_file()
    assert (REPO_ROOT / GOVERNANCE_REL).is_file()
    assert "## Semantic Slice Convergence" in _read("AGENTS.md")
    assert CONVERGENCE_REL in _read("AGENTS.md")
    skills_root = REPO_ROOT / ".claude/skills"
    directories = tuple(sorted(entry.name for entry in skills_root.iterdir()))
    assert directories == (
        "pietto-mechanical-closure",
        "pietto-publication-topology",
        "pietto-semantic-convergence",
    )
    for name in directories:
        files = tuple(sorted(entry.name for entry in (skills_root / name).iterdir()))
        assert files == ("SKILL.md", "reference.md"), name
        assert "disable-model-invocation: true" in _read(
            f".claude/skills/{name}/SKILL.md"
        )
    for helper in (
        "tests/_pietto_reader_closure.py",
        "tests/_pietto_publication_topology.py",
        "tests/_pietto_runtime_journal.py",
    ):
        assert (REPO_ROOT / helper).is_file(), helper
    closure = _flat(
        _section(SPEC_REL, "Workflow-hardening And Evidence-governance Closure")
    )
    assert "exactly three explicit-invocation project skills" in closure
    assert "immutable and create-once" in closure
    assert (
        "no consumed Git, GitHub, CI, review, or merge action was replayed" in closure
    )


def test_phase55_handoff_is_precise_and_starts_no_implementation() -> None:
    handoff = _flat(_section(SPEC_REL, "Phase 55 Handoff"))
    assert "Semantic Package Asset Schema And Deterministic Local Loading" in handoff
    assert "It remains `UNSTARTED`" in handoff
    assert "nothing in Slice 16 begins it" in handoff
    assert "Phase 55 entry state is the Phase 54 completion commit" in handoff
    for inherited in (
        "selected-input index",
        "trusted descriptor loader",
        "binding environments",
        "`PIE-S2701` through `PIE-S2707`",
        "loader-readiness facts with no loader",
        "inspection projection",
        "pure value boundary",
    ):
        assert inherited in handoff, inherited
    assert "Phase-start Expansion, Pull-forward, And Readiness Audit" in handoff
    assert GOVERNANCE_REL in handoff
    assert "must not expand prematurely" in handoff
    for phase in range(56, 71):
        assert f"({phase})" in handoff, phase
    assert "creates no tag, Release, publication, signing, or attestation" in handoff
    assert "`PHASE55_GATE0_GATE1`" in handoff
    post = _flat(_section(SPEC_REL, "Post-completion Phase 55–70 Status"))
    assert "Phase 55 through Phase 70 remain `UNSTARTED`" in post
    assert "Slice 16 starts no Phase 55 implementation" in post


def test_retained_later_owners_are_unchanged_by_slice16() -> None:
    roadmap = _read(ROADMAP_REL)
    for phase, title in PHASE55_70_OWNERS:
        assert f"| {phase} | {title} |" in roadmap, phase
    audit = _flat(_section(SPEC_REL, "Future-owner Audit"))
    assert "basic explicit named re-export is Phase 54 and is delivered" in audit
    assert "No owner is added, renamed, removed, or transferred by Slice 16" in audit
    completion = _flat(
        _section(ROADMAP_REL, "Phase 54 Completion And Phase 55 Entry State")
    )
    assert "changes no owner in the Phase 55-70 route below" in completion
    assert "adds no implementation authority to any later phase" in completion


def test_this_module_is_static_undecorated_and_declares_no_phase55_behavior() -> None:
    source = _read(SELF_REL)
    tree = ast.parse(source, filename=SELF_REL)
    nodes = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert tuple(node.name for node in nodes) == _top_level_test_functions(SELF_REL)
    assert all(not node.decorator_list for node in nodes)
    assert len(nodes) == 17
    assert len({node.name for node in nodes}) == 17
    # The audit reads the repository; it never spawns a process or mutates it.
    assert _imported_root_modules(REPO_ROOT / SELF_REL) == {
        "__future__",
        "_phase54_active_gate2_manifest",
        "ast",
        "hashlib",
        "pathlib",
        "pietto",
        "re",
        "tomllib",
    }
    boundary = _flat(_section(SPEC_REL, "Separate Authorization Boundary"))
    assert "authorizes no Phase 55–70 work" in boundary
    assert "never implies compiler, serializer, loader, or backend support" in boundary
