from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md"
BOUNDARY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md"
)
GRAIN_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-relationship-grain-contract-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar",
    "src/pietto/generated",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
    "tests/fixtures",
    "tests/goldens",
    "scripts",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase34_candidate_decision.py",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def test_phase34_slice2_artifacts_and_status_are_docs_only() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(GRAIN_SPEC_PATH)

    assert PLAN_PATH.is_file()
    assert GRAIN_SPEC_PATH.is_file()
    assert "Phase 34 Relationship Grain And Narrow JOIN MVP" in plan
    assert (
        "Phase 34 Slice 2 Relationship Grain Contract And Static Audit is the "
        "current docs/spec/static-audit/status-only contract slice"
    ) in plan
    assert (
        "Proceed with Phase 34 Slice 2 as docs/spec/static-audit/status-only: "
        "define relationship grain terminology, accepted future grain facts, "
        "non-goals, fail-closed requirements, and preservation boundaries; "
        "implement no grammar, semantic, IR, SQL, CLI, JSON, project, or "
        "runtime behavior"
    ) in plan
    assert "Slice 2 implements no JOIN" in plan
    assert "Slice 2 approved file scope is limited to" in plan
    assert "Phase 34 remains in progress after Slice 2" in plan
    assert (
        "This specification records the Phase 34 Slice 2 relationship grain contract"
    ) in spec
    assert "Slice 2 is docs/spec/static-audit/status-only work" in spec


def test_relationship_grain_definition_and_non_claims_are_locked() -> None:
    spec = _normalized(GRAIN_SPEC_PATH)

    for required in (
        "Relationship grain is a compile-time metadata contract around "
        "endpoint row identity and cardinality expectations",
        "It may later constrain whether a relationship edge is safe for narrow "
        "JOIN acceptance",
        "Relationship grain is compile-time metadata describing expected row "
        "identity/cardinality behavior around relationship endpoints",
        "Relationship grain is not runtime enforcement, not database constraint "
        "introspection, not authorization, not optimization proof, and not a "
        "security guarantee",
        "Slice 2 does not add a metadata carrier, source syntax, semantic "
        "validation, diagnostic code, IR field, SQL rendering, CLI output, "
        "JSON field, project output, or runtime behavior for grain",
    ):
        assert required in spec, required


def test_grain_levels_and_current_metadata_gaps_are_locked() -> None:
    spec = _normalized(GRAIN_SPEC_PATH)

    for required in (
        "Current relationship metadata does not carry grain, cardinality, "
        "fanout, optionality, multiplicity, identity, key, provenance, trust, "
        "or validation facts",
        "Endpoint grain",
        "Relationship-edge grain",
        "Relation grain",
        "One-row-per endpoint expectation",
        "Fanout risk",
        "These terms are not Pietto source syntax and do not add AST, semantic "
        "model, IR, SQL, CLI, or JSON behavior",
        "Slice 2 recommends contract separation between endpoint grain, "
        "relationship-edge grain, and relation grain",
    ):
        assert required in spec, required


def test_cardinality_and_fanout_vocabulary_is_contract_only() -> None:
    spec = _normalized(GRAIN_SPEC_PATH)

    for required in (
        "The following labels are contract vocabulary only",
        "not accepted Pietto syntax",
        "not reserved keywords",
        "not enum values in the semantic model",
        "`one`",
        "`zero-or-one`",
        "`many`",
        "`one-to-one`",
        "`many-to-one`",
        "`one-to-many`",
        "`many-to-many`",
        "`fanout-free`",
        "`fanout-producing`",
        "`unknown`",
        "`unsafe`",
        "`ambiguous`",
        "`cardinality-preserving`",
        "`optional-match`",
        "`required-match`",
    ):
        assert required in spec, required


def test_future_join_requires_grain_facts_before_acceptance() -> None:
    spec = _normalized(GRAIN_SPEC_PATH)

    for required in (
        "Before any later narrow JOIN slice accepts relationship-aware "
        "composition, the accepted source must have statically known grain "
        "facts",
        "a single validated relationship metadata edge",
        "explicit query opt-in",
        "exactly one base relation plus one joined endpoint",
        "deterministic endpoint role and endpoint name ownership",
        "deterministic endpoint qualification for fields and scopes",
        "statically known endpoint schemas",
        "endpoint and pairwise edge grain facts statically known",
        "endpoint grain facts for both participating endpoints",
        "relationship-edge grain facts for the selected pair of endpoints",
        "a declared, validated, or otherwise explicitly trusted basis for the "
        "grain facts",
        "fanout posture within the later approved MVP support boundary",
        "PostgreSQL/MySQL lowering capability for the same accepted semantic subset",
        "Unsupported, missing, contradictory, unsafe, or ambiguous grain facts "
        "must fail closed before SQL is emitted",
    ):
        assert required in spec, required


def test_unknown_unsafe_or_ambiguous_grain_fails_closed() -> None:
    spec = _normalized(GRAIN_SPEC_PATH)

    for required in (
        "Future relationship grain and narrow JOIN work must fail closed when",
        "missing grain",
        "unknown grain",
        "contradictory grain",
        "ambiguous endpoint ownership",
        "ambiguous qualification",
        "unsafe fanout",
        "unsupported cardinality",
        "unknown endpoint schema",
        "backend lowering cannot preserve semantics",
        "endpoint grain is missing for either endpoint",
        "relationship-edge grain is missing",
        "relation identity prerequisites are missing where the future contract "
        "requires them",
        "grain facts conflict with each other",
        "grain provenance, validation, or trust assumptions are unavailable",
        "the cardinality posture is `many-to-many`, `unknown`, `unsafe`, or "
        "`ambiguous` unless a later approved slice explicitly accepts that "
        "posture",
        "fanout is possible but not explicitly accepted by the later approved slice",
        "arbitrary multi-hop traversal",
        "relationship chaining",
        "relationship graph traversal",
        "automatic join inference",
        "Fail closed means deterministic compiler diagnostics and no approximate SQL",
    ):
        assert required in spec, required


def test_phase33_project_json_and_slice1_boundaries_are_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "single-file `pietto check --format json` remains JSON v1",
        "single-file `pietto emit-sql --format json` remains JSON v1",
        "single-file `pietto explain --format json` remains Semantic Metadata "
        "Artifact v1",
        "Slice 1 implements no JOIN and no relationship grain behavior",
        "Narrow JOIN is later-slice only",
    ):
        assert required in combined, required


def test_slice2_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = _phase34_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in combined
    assert "no tag/release/publish/upload/signing/attestation occurred" in combined
    assert "No tag/release/publish/upload/signing/attestation is performed" in combined

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in combined.lower(), forbidden


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase34_docs() -> str:
    return " ".join(
        _normalized(path) for path in (PLAN_PATH, BOUNDARY_SPEC_PATH, GRAIN_SPEC_PATH)
    )


def _git_diff_name_only(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()
