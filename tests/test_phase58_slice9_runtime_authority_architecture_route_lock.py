from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice9-runtime-authority-architecture-route-lock-v1.md"
)
SCOPE = REPO_ROOT / "docs/spec/phase58-project-explain-portability-scope-lock-v1.md"

CURRENT_ROUTE = (
    (
        "1",
        "Architecture/scope/route lock; artifact identity; target denominator; single-file explain compatibility",
    ),
    (
        "2",
        "Public common model and success/failure envelope; logical paths; evidence posture; request/resolution/result vocabulary",
    ),
    (
        "3",
        "Package and requirement provenance projection; `declared_by`/`requested_by`",
    ),
    (
        "4",
        "Public requirement/target compatibility matrix; evaluation states; five checked statuses and reasons",
    ),
    (
        "5",
        "Public extension-catalog evidence projection; catalog coordinate/target/digest; selection; matchability/exposure; bounded provenance",
    ),
    ("6", "Conservative requirement/project portability derivation"),
    (
        "7",
        "Cross-section composition; artifact-local references; integrity; deterministic ordering; authority separation",
    ),
    (
        "8",
        "Public JSON v1 schema; deterministic serialization; success/failure envelopes; privacy and schema-evolution locks",
    ),
    ("9", "Runtime authority architecture and evidence-backed route expansion lock"),
    ("10", "Package-owned capability requirement declaration authority"),
    (
        "11",
        "Project-owned evaluated-target, profile, and catalog-availability authority",
    ),
    ("12", "Project Explain runtime authority builder and exact orchestration"),
    (
        "13",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "14",
        "Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes",
    ),
    (
        "15",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "16",
        "Completion audit; Phase 59 handoff; Phase 60/64/67/69 readiness reconciliation",
    ),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _table_rows(section: str) -> tuple[tuple[str, ...], ...]:
    return tuple(
        tuple(cell.strip() for cell in line.strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    )


def _top_level_assignment(path: Path, name: str) -> ast.expr:
    tree = ast.parse(_read(path), filename=str(path))
    matches = tuple(
        node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        )
    )
    assert len(matches) == 1
    return matches[0]


def test_original_history_and_current_16_slice_route_are_exact() -> None:
    spec = _read(SPEC)
    scope = _read(SCOPE)
    original = _table_rows(_section(scope, "Exact 12-Slice Route"))[1:]
    current_spec = _table_rows(_section(spec, "Current 16-Slice Route"))[1:]
    current_scope = _table_rows(
        _section(scope, "Evidence-backed Route Expansion After Published Slice 8")
    )[1:]

    assert len(original) == 12
    assert current_spec == current_scope == CURRENT_ROUTE
    assert current_spec[:8] == original[:8]
    assert tuple(row[1] for row in current_spec[12:15]) == tuple(
        row[1] for row in original[8:11]
    )
    assert original[11][0] == "12" and current_spec[15][0] == "16"

    history = _section(spec, "Historical Route And Expansion")
    for required in (
        "original Phase 58 route contained exactly 12 slices",
        "After published Slice 8",
        "expands from 12 to\nexactly 16 slices",
        "Published Slices 1–8 are not renumbered",
        "Original planned\nSlices 9–12 move to current Slices 13–16",
        "no named pseudo-slice",
        "Current expansion candidate after Slice 9:\n`NONE`",
    ):
        assert required in history


def test_package_requirement_ownership_and_manifest_versioning_are_frozen() -> None:
    spec = _read(SPEC)
    ownership = _table_rows(_section(spec, "Frozen Ownership Split"))[1:]
    assert ownership == (
        (
            "Capability requirement declaration, collection identity, ordered occurrences, exact `CapabilityKey`",
            "Declaring package",
            "Project override or synthesis for a dependency package",
        ),
        (
            "Ordered evaluated-target denominator, project-provided profiles, target-to-profile selection, supplied overlays",
            "Project",
            "Package-selected project denominator",
        ),
        (
            "Exact availability declarations for existing bundled extension catalogs",
            "Compiler/catalog boundary",
            "Availability treated as selection, installation, preference, or default target",
        ),
    )

    package_section = _section(spec, "Slice 10 Package Requirement Authority")
    for required in (
        "schema version 1 remains exact zero-delta",
        "schema version 2",
        "declaration absent -> UNDECLARED",
        "declaration present, zero entries -> DECLARED EMPTY",
        "DECLARED WITH ORDERED OCCURRENCES",
        "Schema v1 is not reinterpreted as a declared-empty collection",
        "Each package\nowns only its own requirements",
        "domain`, `subject`, `operation`, `operands`, `context`,\n`dialect`, and `extension",
        "does not freeze those future field names",
    ):
        assert required in package_section


def test_project_target_profile_catalog_and_empty_denominator_owners_are_exact() -> (
    None
):
    section = _section(
        _read(SPEC), "Slice 11 Project Target Profile And Catalog Authority"
    )
    for required in (
        "schemas 1, 2, and 3 remain exact zero-delta",
        "schema version 4",
        "one exact ordered evaluated-target sequence",
        "There is no sorting, deduplication, implicit target",
        "exact database family/release",
        "one exact\nbase profile",
        "ordered supplied overlays",
        "StaticCapabilityProfile",
        "explicitly declared empty target sequence is valid",
        "INDETERMINATE / no-evaluated-targets",
        "no compiler default profile or target",
        "compiler profile\navailability ledger may remain empty",
        "pgvector and pg_trgm",
        "It does not select a catalog",
        "Remote/project catalog acquisition",
        "freezes only semantics and ownership",
    ):
        assert required in section


def test_slice12_builder_zero_context_failure_and_slice13_cli_owners_are_exact() -> (
    None
):
    spec = _read(SPEC)
    builder = _section(spec, "Slice 12 Runtime Authority Builder")
    for required in (
        "project root",
        "PackageInspectionFactSet",
        "Slice 10 package requirement bindings",
        "Slice 11 target/profile/catalog authority",
        "PackageCapabilityCheckingMatrix per package",
        "CapabilityInspectionFactSet per package",
        "ExtensionSignatureProviderContext where required",
        "ProjectExplainEnvelope[ProjectExplainPayload]",
        "adds no second package loader",
        "Zero-context compatibility extension",
        "one row per requirement",
        "every row.cells = ()",
        "Existing non-empty Phase 56 behavior remains exact zero-delta",
        "No\n`UNKNOWN` cell, dummy target, hidden profile, or Slice 3 bypass",
        "SUCCESS\nDIAGNOSTIC_ERROR\nUSAGE_OR_RESOURCE_ERROR",
        "does\nnot gain an exit-code field",
        "No\npartial payload or host path",
    ):
        assert required in builder

    cli = _section(spec, "Slice 13 CLI And Text")
    for required in (
        "consumes only the Slice 12 build result",
        "Existing `pietto explain <file>`\nremains exact zero-delta",
        "positional `path` XOR `--project`",
        "usage error with exit 2",
        "serialize_project_explain_json_document",
        "success to exit 0",
        "diagnostic\nfailure to exit 1",
        "usage/resource failure to exit 2",
        "exactly one stdout document",
    ):
        assert required in cli


def test_shifted_owners_and_phase59_67_69_boundaries_are_exact() -> None:
    spec = _read(SPEC)
    shifted = _section(spec, "Shifted Assurance And Completion Owners")
    for required in (
        "Slice 14 owns real full-chain",
        "every checked status",
        "empty target denominator",
        "Slice 15 owns public pure/differential compatibility",
        "Python 3.12/3.13 parity",
        "new Slice 10–13 runtime path",
        "Slice 16 owns Phase 58 completion",
        "Phase 60/64/67/69 readiness",
    ):
        assert required in shifted

    later = _section(spec, "Later Phase Boundaries")
    for required in (
        "Phase 59",
        "package-owned requirement declarations",
        "Project targets/profiles remain environment authority",
        "non-global IDs",
        "Phase 67",
        "transport package manifest v2 without rewriting",
        "no solver, lockfile, range, registry, or remote",
        "Phase 69",
        "release-aware PostgreSQL builtin catalogs",
        "backend-specific\ncompiler profiles",
        "request, resolution, availability, selection, and installation",
    ):
        assert required in later


def test_slice9_is_docs_static_only_and_current_production_contracts_are_zero_delta() -> (
    None
):
    config_path = REPO_ROOT / "src/pietto/_project/config.py"
    manifest_path = REPO_ROOT / "src/pietto/_project/package_manifest.py"
    config_modes = _top_level_assignment(
        config_path,
        "_COMPILATION_MODE_BY_SCHEMA_VERSION",
    )
    assert isinstance(config_modes, ast.Dict)
    assert tuple(
        key.value for key in config_modes.keys if isinstance(key, ast.Constant)
    ) == (1, 2, 3)

    manifest_keys = _top_level_assignment(manifest_path, "_TOP_LEVEL_KEYS")
    assert ast.literal_eval(manifest_keys) == (
        "schema_version",
        "namespace",
        "name",
        "version",
        "assets",
        "dependencies",
    )
    manifest_source = _read(manifest_path)
    assert "schema version must be exact integer 1" in manifest_source
    assert "capability_requirements" not in manifest_source

    assert not (REPO_ROOT / "src/pietto/_project_explain/runtime_builder.py").exists()
    assert not (REPO_ROOT / "src/pietto/_project_explain/text.py").exists()
    cli_source = _read(REPO_ROOT / "src/pietto/cli.py")
    explain_start = cli_source.index("def _configure_explain_parser")
    explain_end = cli_source.index("\ndef ", explain_start + 1)
    assert '"--project"' not in cli_source[explain_start:explain_end]

    compatibility = _section(_read(SPEC), "Compatibility And Non-goals")
    for forbidden_change in (
        "production\nsource",
        "package/project parser",
        "matrix",
        "Project Explain model",
        "JSON",
        "CLI",
        "public export",
        "generated artifact",
        "golden",
        "dependency",
        "workflow",
        "version",
    ):
        assert forbidden_change in compatibility
    for release_boundary in ("tags", "Releases", "package publication"):
        assert release_boundary in compatibility
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_self_owned_open_and_slice10_handoff_are_closed() -> None:
    spec = _read(SPEC)
    assert "PHASE58_SLICE9_SELF_OWNED_OPEN = 0" in spec
    assert "Slice 10 remains unstarted and unauthorized" in spec
