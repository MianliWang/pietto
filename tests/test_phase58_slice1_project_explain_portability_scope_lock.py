from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.model as project_explain_model
import pietto._project.capability_inspection as capability_inspection
import pietto._project.capability_pure_boundary as capability_pure
import pietto._project.extension_catalog_inspection as catalog_inspection
import pietto._project.extension_catalog_inspection_pure_boundary as catalog_pure
import pietto._project.package_inspection as package_inspection
import pietto._project.package_pure_boundary as package_pure
import pietto.semantic as semantic_package
from pietto._metadata.model import (
    SEMANTIC_METADATA_ARTIFACT_NAME,
    SEMANTIC_METADATA_COMMAND,
    SEMANTIC_METADATA_SCHEMA_VERSION,
    SemanticMetadataArtifact,
    SemanticMetadataPayload,
    SemanticMetadataSourceIdentity,
)
from pietto._metadata.serializer import (
    build_semantic_metadata_error_envelope,
    semantic_metadata_artifact_to_json_dict,
)
from pietto._metadata.text import render_semantic_metadata_text
from pietto._project.capability_checking import CapabilityRequirementStatus
from pietto._project.capability_inspection import (
    CapabilityInspectionColumnVariant,
    CapabilityInspectionFactSet,
    CapabilityInspectionFormat,
)
from pietto._project.capability_matrix import PackageCapabilityCheckingMatrix
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    ExtensionCatalogInspectionFormat,
)
from pietto._project.model import ProjectConfigPath, ProjectInput, ProjectRoot
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionFormat,
)
from pietto.semantic.capability_profiles import CapabilityRequirementOccurrence


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase58-project-explain-portability-scope-lock-v1.md"

EXPECTED_ROUTE = (
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
    (
        "9",
        "`pietto explain --project` text/JSON integration; existing single-file explain zero-delta",
    ),
    (
        "10",
        "Real multi-target E2E scenarios spanning package, capability, catalog, all evaluation states, and all checked result classes",
    ),
    (
        "11",
        "Public pure/differential compatibility boundary; goldens; Python 3.12/3.13; hash seed; relocation; installed wheel",
    ),
    (
        "12",
        "Completion audit; Phase 59 handoff; Phase 60/64/69 readiness reconciliation",
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


def _headings(document: str) -> tuple[str, ...]:
    return tuple(
        line.removeprefix("## ")
        for line in document.splitlines()
        if line.startswith("## ")
    )


def _function_names(path: Path) -> frozenset[str]:
    tree = ast.parse(_read(path), filename=path.as_posix())
    return frozenset(
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    )


def _argument_names(source: str, function_name: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    )
    names: list[str] = []
    for node in ast.walk(function):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.append(node.args[0].value)
    return tuple(names)


def test_existing_single_file_explain_identity_and_envelopes_are_zero_delta() -> None:
    assert (
        SEMANTIC_METADATA_ARTIFACT_NAME,
        SEMANTIC_METADATA_SCHEMA_VERSION,
        SEMANTIC_METADATA_COMMAND,
    ) == ("Semantic Metadata Artifact v1", 1, "explain")
    assert tuple(field.name for field in fields(SemanticMetadataArtifact)) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )

    payload = SemanticMetadataPayload(
        source=SemanticMetadataSourceIdentity(path="model.pietto"),
        definitions=(),
        sources=(),
        relations=(),
        types=(),
    )
    artifact = SemanticMetadataArtifact(
        artifact=SEMANTIC_METADATA_ARTIFACT_NAME,
        schema_version=SEMANTIC_METADATA_SCHEMA_VERSION,
        command=SEMANTIC_METADATA_COMMAND,
        ok=True,
        path="model.pietto",
        diagnostics=(),
        metadata=payload,
    )
    success = semantic_metadata_artifact_to_json_dict(artifact)
    assert tuple(success) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "metadata",
    )
    assert render_semantic_metadata_text(artifact).splitlines()[:4] == [
        "Semantic Metadata Artifact v1",
        "schema_version: 1",
        "command: explain",
        "path: model.pietto",
    ]

    failure = build_semantic_metadata_error_envelope(
        path="bad.pietto",
        stage="parse",
        message="Semantic Metadata Artifact v1 metadata is unavailable.",
    )
    assert tuple(failure) == (
        "artifact",
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "error",
    )
    assert failure["ok"] is False
    assert "metadata" not in failure

    cli_source = _read(REPO_ROOT / "src/pietto/cli.py")
    assert _argument_names(cli_source, "_configure_explain_parser") == (
        "path",
        "--format",
    )
    assert "return _run_explain(namespace.path, output_format=namespace.format)" in (
        cli_source
    )

    scope = _read(SPEC)
    for required in (
        "Project Explain Artifact v1",
        "pietto.project-explain.v1",
        "pietto explain --project <root>",
        "pietto explain --project <root> --format json",
        "existing single-file surface is exact zero-delta",
    ):
        assert required in scope


def test_existing_explain_behavior_remains_owned_by_current_compatibility_tests() -> (
    None
):
    expected = {
        "tests/test_phase33_cli_package_compatibility_hardening.py": {
            "test_single_file_json_v1_and_artifact_v1_surfaces_remain_separate",
            "test_project_flag_remains_rejected_outside_check",
        },
        "tests/test_phase33_project_check_cli.py": {
            "test_project_flag_is_not_accepted_by_emit_sql_or_explain",
            "test_single_file_emit_sql_json_v1_and_explain_artifact_v1_remain_available",
        },
        "tests/test_phase40_let_binding_cli_json_metadata.py": {
            "test_supported_let_explain_text_and_json_preserve_artifact_v1",
            "test_unsupported_let_explain_json_fails_without_metadata",
            "test_non_let_cli_json_metadata_shape_remains_stable",
        },
        "tests/test_phase43_cli_json_metadata_sql_compatibility.py": {
            "test_combined_phase43_check_json_and_explain_shapes_remain_stable",
            "test_failed_explain_json_keeps_artifact_error_envelope_without_metadata",
        },
    }
    for relative_path, function_names in expected.items():
        assert function_names <= _function_names(REPO_ROOT / relative_path)

    package_smoke = _read(REPO_ROOT / "scripts/package_smoke.py")
    for retained in (
        '"explain"',
        "Semantic Metadata Artifact v1\\n",
        'explain_document.get("schema_version") != 1',
        'explain_document.get("command") != "explain"',
    ):
        assert retained in package_smoke


def test_project_explain_marker_and_private_exports_remain_exact() -> None:
    production_sources = tuple(sorted((REPO_ROOT / "src/pietto").rglob("*.py")))
    production_text = "\n".join(_read(path) for path in production_sources)
    for forbidden in (
        "explain-project",
        "explain_project",
    ):
        assert forbidden not in production_text
    for public_path in (
        "src/pietto/cli.py",
        "src/pietto/__init__.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/_metadata/__init__.py",
        "src/pietto/semantic/__init__.py",
    ):
        assert "project_explain" not in _read(REPO_ROOT / public_path)

    marker_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in production_sources
        if "pietto.project-explain.v1" in _read(path)
    }
    assert marker_paths == {"src/pietto/_project_explain/model.py"}
    assert metadata_package.__all__ == ()
    assert project_package.__all__ == ()
    assert project_explain_package.__all__ == project_explain_model.__all__ == ()
    assert package_inspection.__all__ == package_pure.__all__ == ()
    assert capability_inspection.__all__ == capability_pure.__all__ == ()
    assert catalog_inspection.__all__ == catalog_pure.__all__ == ()
    for module in (pietto, semantic_package, project_package):
        assert not hasattr(module, "ProjectExplainArtifact")
        assert not hasattr(module, "PROJECT_EXPLAIN_FORMAT_MARKER")
        assert not hasattr(module, "ProjectExplainEnvelope")
        assert not hasattr(module, "ProjectExplainPackageRequirementProjection")


def test_snapshot_and_three_private_authorities_are_separate_and_exact() -> None:
    document = _read(SPEC)
    assert "one deterministic compiler-analysis\nsnapshot" in _section(
        document, "Deterministic Snapshot Boundary"
    )
    composition = _section(document, "Independent Private Authority Composition")
    for required in (
        "PackageInspectionFactSet",
        "pietto.package-inspection.v1",
        "CapabilityInspectionFactSet",
        "pietto.capability-inspection.v1",
        "PackageCapabilityCheckingMatrix",
        "ExtensionCatalogInspectionFactSet",
        "pietto.extension-catalog-inspection.v1",
        "explicit public projections",
        "artifact-local cross-references",
        "deterministic portability derivation",
    ):
        assert required in composition
    assert "does not merge or replace private fact ownership" in composition

    assert PackageInspectionFormat.PACKAGE_INSPECTION_V1.value == (
        "pietto.package-inspection.v1"
    )
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1.value == (
        "pietto.extension-catalog-inspection.v1"
    )
    for carrier in (
        PackageInspectionFactSet,
        CapabilityInspectionFactSet,
        ExtensionCatalogInspectionFactSet,
    ):
        assert tuple(field.name for field in fields(carrier)) == (
            "inspection",
            "canonical_bytes",
            "authority",
        )
    assert tuple(field.name for field in fields(PackageCapabilityCheckingMatrix)) == (
        "package",
        "binding",
        "contexts",
        "columns",
        "rows",
    )


def test_request_resolution_result_and_bounded_provenance_are_exact() -> None:
    document = _read(SPEC)
    rows = _table_rows(_section(document, "Public Requirement Model"))[1:]
    assert tuple(row[0].strip("`") for row in rows) == (
        "REQUEST",
        "RESOLUTION",
        "RESULT",
    )
    assert tuple(field.name for field in fields(CapabilityRequirementOccurrence)) == (
        "owner",
        "position",
        "key",
    )
    request = rows[0][1]
    for required in (
        "Exact requirement occurrence",
        "CapabilityKey",
        "exact declaring package",
        "requested-by/root context",
        "source order",
    ):
        assert required in request
    provenance = _section(document, "Bounded Requirement Provenance")
    for required in (
        "root/project package",
        "declaring package",
        "requirement occurrence",
        "`declared_by`",
        "`requested_by`",
        "package role",
        "requirement position",
        "artifact-local positions",
        "Phase 59",
    ):
        assert required in provenance
    assert "does not construct a transitive provenance graph" in provenance


def test_explicit_target_denominator_and_normative_matrix_are_exact() -> None:
    document = _read(SPEC)
    denominator = _section(document, "Explicit Evaluated Target Denominator")
    for required in (
        "one explicit ordered evaluated\ntarget set retained in the artifact",
        "lower-level artifact builder consumes an\nexplicit resolved target set",
        "materialize the resolved set",
        "There is no implicit universal target set",
        "An\nunqualified `portable: true` is invalid",
    ):
        assert required in denominator

    matrix = _section(document, "Normative Requirement By Target Matrix")
    tables = _table_rows(matrix)
    assert tables[:4] == (
        ("Evaluation state", "Meaning"),
        (
            "`UNDECLARED`",
            "The requirement collection is not declared for checking",
        ),
        (
            "`BLOCKED`",
            "Declared checking is blocked before a checked result exists",
        ),
        ("`CHECKED`", "A canonical checked result exists"),
    )
    assert tables[4:] == (
        ("Checked status", "Portability evidence"),
        ("`SATISFIED`", "Positive checked evidence"),
        ("`UNSUPPORTED`", "Definite compatibility gap"),
        ("`ABSENT`", "Definite compatibility gap"),
        ("`UNKNOWN`", "Indeterminate evidence"),
        ("`CONFLICT`", "Indeterminate evidence"),
    )
    assert tuple(item.name for item in CapabilityInspectionColumnVariant) == (
        "UNDECLARED",
        "BLOCKED",
        "CHECKED",
    )
    assert tuple(item.name for item in CapabilityRequirementStatus) == (
        "SATISFIED",
        "UNSUPPORTED",
        "ABSENT",
        "UNKNOWN",
        "CONFLICT",
    )
    assert "never become a fabricated checked `UNKNOWN`" in matrix
    assert "raw ordered requirement-by-target matrix is normative" in matrix


def test_portability_rules_and_edge_cases_are_closed_and_conservative() -> None:
    section = _section(_read(SPEC), "Portability Derivation")
    rows = _table_rows(section)
    assert rows[:4] == (
        ("Condition", "Classification"),
        (
            "Non-empty target set and every cell is `CHECKED / SATISFIED`",
            "`PORTABLE`",
        ),
        (
            "At least one cell is `CHECKED / UNSUPPORTED` or `CHECKED / ABSENT`",
            "`NOT_PORTABLE`",
        ),
        ("Otherwise", "`INDETERMINATE`"),
    )
    assert rows[4:] == (
        ("Condition", "Classification"),
        ("Any requirement is `NOT_PORTABLE`", "`NOT_PORTABLE`"),
        (
            "Otherwise, any requirement is `INDETERMINATE`",
            "`INDETERMINATE`",
        ),
        ("Otherwise", "`PORTABLE`"),
    )
    for required in (
        "definite gap is sufficient for `NOT_PORTABLE`",
        "empty evaluated target set is `INDETERMINATE`",
        "no-evaluated-targets reason",
        "Zero declared requirements over a non-empty",
        "`requirements_evaluated == 0`",
    ):
        assert required in section
    assert (
        "There is no `PARTIALLY_PORTABLE`, `MOSTLY_PORTABLE`, `BEST_TARGET`,\n"
        "`WORST_TARGET`, target ranking, or recommendation."
    ) in section


def test_evidence_provenance_paths_envelope_and_compatibility_are_bounded() -> None:
    document = _read(SPEC)
    evidence_rows = _table_rows(_section(document, "Public Evidence Posture"))[1:]
    assert evidence_rows == (
        ("`SOURCE_FACT`", "Retained upstream or authored source fact"),
        (
            "`DETERMINISTIC_DERIVATION`",
            "Provider result, matrix projection, or portability classification derived from exact authority",
        ),
        (
            "`UNAVAILABLE`",
            "Required authority is undeclared or unavailable",
        ),
        (
            "`CONFLICTING`",
            "Same-scope evidence conflicts without an arbitrary winner",
        ),
    )
    assert all("REVIEWED_INTERPRETATION" not in row[0] for row in evidence_rows)

    provenance = _section(document, "Bounded Public Provenance")
    for required in (
        "catalog content digest",
        "source authority",
        "source revision",
        "source locator",
        "artifact-local references",
        "not global IDs",
    ):
        assert required in provenance
    paths = _section(document, "Logical Paths And Privacy")
    for required in (
        "project-relative paths",
        "package-relative paths",
        "upstream source locators",
        "host absolute paths",
        "symlink-resolved",
        "virtual-environment",
        "relocation-stable",
    ):
        assert required in paths
    assert tuple(field.name for field in fields(ProjectRoot)) == ("path",)
    assert tuple(field.name for field in fields(ProjectConfigPath)) == ("path",)
    assert tuple(field.name for field in fields(ProjectInput)) == ("path", "status")

    envelope = _section(document, "Success And Failure Envelope")
    for required in (
        "one versioned top-level envelope for success\nand failure",
        "exact format marker",
        "success Boolean",
        "ordered diagnostics",
        "optional project-explain payload",
        "does not produce fabricated\npartial success facts",
    ):
        assert required in envelope
    compatibility = _section(document, "JSON Text And Schema Evolution")
    assert "JSON is the stable public machine contract" in compatibility
    assert "Human-readable text is not a machine compatibility contract" in (
        compatibility
    )
    for breaking in (
        "field removal",
        "field rename",
        "field type\nchange",
        "required-field addition",
        "existing enum semantic change",
        "existing\nordering semantic change",
    ):
        assert breaking in compatibility

    assert _table_rows(_section(document, "Deterministic Ordering"))[1:] == (
        ("Packages", "Existing private package-inspection authority order"),
        ("Requirements", "Exact source occurrence order"),
        ("Targets", "Explicit resolved target order"),
        ("Matrix", "Requirement order by target order"),
        (
            "Catalog and evidence tables",
            "Deterministic private/content-derived order",
        ),
        ("Source evidence", "Retained source-occurrence order"),
    )


def test_exact_route_and_expansion_policy_are_immutable() -> None:
    document = _read(SPEC)
    assert _table_rows(_section(document, "Exact 12-Slice Route"))[1:] == (
        EXPECTED_ROUTE
    )
    assert "Current expansion candidate: `NONE`" in document


def test_later_readiness_non_goals_and_heading_boundaries_are_exact() -> None:
    document = _read(SPEC)
    readiness = _table_rows(_section(document, "Later Readiness"))[1:]
    assert tuple(row[0] for row in readiness) == ("59", "60", "64", "69")
    expected_terms = {
        "59": ("artifact-local", "graph nodes", "global IDs"),
        "60": ("capability-domain agnostic", "WINDOW_FUNCTION"),
        "64": ("exact structured type", "unmodeled source spelling", "typmods"),
        "69": (
            "Database family/release",
            "catalog identity/release",
            "installed-extension",
        ),
    }
    for phase, description in readiness:
        assert all(term in description for term in expected_terms[phase])

    lessons = _section(document, "Package Manager Lessons And Non-goals")
    for required in (
        "request is distinct from resolution and installation",
        "exact selected source, version, and content identity",
        "bounded explanation",
        "target/environment context affects resolution",
        "version ranges",
        "solver",
        "lockfile",
        "registry",
        "remote fetching",
        "installation state",
    ):
        assert required in lessons

    non_goals = _section(document, "Explicit Non-goals")
    for required in (
        "universal portability",
        "database connections",
        "CREATE EXTENSION",
        "public provenance or lineage graphs",
        "SQL lowering",
        "PostGIS",
        "TimescaleDB",
        "version bump",
        "GitHub Release",
        "signing",
        "attestation",
    ):
        assert required in non_goals
    assert {
        "Reviewed Interpretation",
        "Public Provenance Graph",
        "Target Ranking",
    }.isdisjoint(_headings(document))

    boundary = _section(document, "Slice 1 Change And Release Boundary")
    assert "documentation and static tests only" in boundary
    assert "Production source, CLI,\nserializers, JSON contracts, public exports" in (
        boundary
    )
    assert "version remains `0.1.0`" in boundary
    assert "Slice 2 remains `UNSTARTED / NOT AUTHORIZED`" in boundary
