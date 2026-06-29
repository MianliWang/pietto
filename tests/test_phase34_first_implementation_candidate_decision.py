from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md"
BOUNDARY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md"
)
GRAIN_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-relationship-grain-contract-v1.md"
JOIN_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md"
)
READINESS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-parser-ast-readiness-contract-v1.md"
)
SEMANTIC_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-semantic-readiness-contract-v1.md"
CANDIDATE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-first-implementation-candidate-decision-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
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


def test_phase34_slice6_plan_status_and_scope_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 6 First Implementation Candidate Decision For Narrow JOIN "
        "Parser / AST Surface is the current docs/spec/static-audit/status-only "
        "candidate decision slice",
        "Proceed with Phase 34 Slice 6 as docs/spec/static-audit/status-only: "
        "decide that actual narrow JOIN parser/AST implementation is not "
        "approved yet; lock first-implementation entry criteria, smallest "
        "future implementation surface, generated-file implications, semantic "
        "fail-closed requirements, and forbidden behaviors; implement no "
        "grammar, generated parser, parser behavior, AST nodes, semantic model "
        "changes, semantic validation, diagnostics, IR, SQL, CLI, JSON, "
        "project, or runtime behavior",
        "Slice 6 approved file scope is limited to",
        "`docs/spec/phase-34-first-implementation-candidate-decision-v1.md`",
        "`tests/test_phase34_first_implementation_candidate_decision.py`",
        "Slice 6 is the current docs/spec/static-audit/status-only candidate "
        "decision slice",
        "Phase 34 remains in progress after Slice 6",
        "Phase 34 is not complete",
    ):
        assert required in plan, required


def test_first_implementation_candidate_contract_exists_and_defers_work() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    assert CANDIDATE_SPEC_PATH.is_file()
    for required in (
        "This specification records the Phase 34 Slice 6 first implementation "
        "candidate decision",
        "Slice 6 is docs/spec/static-audit/status-only work",
        "Phase 34 is not ready for actual narrow JOIN parser/AST implementation "
        "in Slice 6",
        "Implementation is deferred",
        "Current unsupported join-like syntax must remain unsupported unless a "
        "later approved implementation slice changes it",
        "Parser/AST acceptance without semantic fail-closed behavior is unsafe",
        "Actual parser/AST implementation is not approved by Slice 6",
    ):
        assert required in spec, required


def test_current_grammar_and_generated_baseline_is_recorded() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "relationshipDefinition",
        "relationshipBody",
        "relationshipEndpoint",
        "tableBody",
        "fromClause",
        "There is no accepted join production",
        "There is no accepted grain syntax",
        "Any `grammar/Pietto.g4` change requires regenerating the tracked ANTLR "
        "outputs",
        "`Pietto.interp`",
        "`Pietto.tokens`",
        "`PiettoLexer.interp`",
        "`PiettoLexer.py`",
        "`PiettoLexer.tokens`",
        "`PiettoParser.py`",
        "`PiettoVisitor.py`",
        "`scripts/check_generated.py` must verify the generated inventory "
        "byte-for-byte",
    ):
        assert required in spec, required


def test_current_ast_builder_baseline_is_recorded() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "`TableDef`",
        "`QueryDef`",
        "`FromClause(source_name)`",
        "`RelationshipMetadata`",
        "`RelationshipEndpoint`",
        "there is no join list",
        "there is no endpoint scope",
        "there is no relationship edge selection",
        "there is no grain carrier",
        "there is no multi-input field owner",
        "`visitTableDefinition`",
        "`visitQueryDefinition`",
        "`_relation_body`",
        "`visitFromClause`",
        "Slice 6 changes none of them",
    ):
        assert required in spec, required


def test_implementation_entry_criteria_are_locked() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "syntax shape is explicitly bounded",
        "grammar diff is small",
        "generated-file regeneration path is clear",
        "AST carrier is minimal and private/internal enough",
        "semantic behavior remains fail-closed",
        "no IR/SQL/CLI/JSON/project behavior changes are needed",
        "no fixtures/goldens are needed",
        "no diagnostic code additions are needed, unless separately approved",
        "existing Phase 33 and Phase 34 tests remain untouched",
        "If any criterion is not met, implementation must remain deferred",
    ):
        assert required in spec, required


def test_future_implementation_surface_is_non_binding_and_not_approved() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "A future minimal parser/AST implementation surface could involve",
        "`grammar/Pietto.g4`",
        "tracked generated ANTLR files under `src/pietto/generated/`",
        "`src/pietto/ast_nodes.py`",
        "`src/pietto/ast_builder.py`",
        "new Phase 34 parser/AST tests",
        "This future surface is non-binding and not approved by Slice 6",
        "must not include semantic source, IR, SQL, CLI, JSON, fixtures, "
        "goldens, scripts, package metadata, dependency, workflow, release, "
        "tag, publish, upload, signing, or attestation surfaces",
    ):
        assert required in spec, required


def test_parser_ast_risks_and_semantic_fail_closed_requirements_are_locked() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "final token spelling is still deferred",
        "final grammar productions are still deferred",
        "final AST class names/fields are still deferred",
        "parser acceptance can change failure mode from `PIE-P1000` parse "
        "failure to semantic rejection",
        "semantic rejection would require approved diagnostics and fail-closed "
        "validation",
        "generated-file hash/status locks may churn",
        "parser span/order diagnostics can affect CLI outputs",
        "relationship selection validation",
        "endpoint ownership validation",
        "endpoint qualification validation",
        "grain prerequisites",
        "unsupported fanout/cardinality behavior",
        "self-relationship disambiguation",
        "duplicate field owner behavior",
        "backend capability handling",
        "deterministic diagnostics before IR or SQL",
    ):
        assert required in spec, required


def test_slice1_to_slice5_boundaries_and_current_behavior_are_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "Narrow JOIN is later-slice only",
        "Relationship grain prerequisites remain required future inputs before "
        "any narrow JOIN acceptance",
        "Final JOIN syntax is deferred and requires a later approved slice",
        "Final token spelling",
        "Slice 5 established semantic readiness boundaries",
        "Unsupported join-like syntax remains unsupported",
        "Relationship metadata remains metadata-only",
        "Relationship metadata is not lowered to IR/SQL",
        "Current single-input relation behavior remains unchanged",
        "`RelationIR` remains single-source",
        "PostgreSQL/MySQL render one `FROM` input",
        "CLI JSON v1 is unchanged",
        "Project JSON v2 is unchanged",
        "Semantic Metadata Artifact v1 is unchanged",
    ):
        assert required in combined, required


def test_phase33_project_json_boundaries_remain_preserved() -> None:
    spec = _normalized(CANDIDATE_SPEC_PATH)

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "TOML schema parsing remains deferred",
        "glob expansion remains deferred",
        "project source parsing remains deferred",
        "multi-file semantic analysis remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "project metadata aggregation remains deferred",
        "single-file `pietto check --format json` remains JSON v1",
        "single-file `pietto emit-sql --format json` remains JSON v1",
        "single-file `pietto explain --format json` remains Semantic Metadata "
        "Artifact v1",
    ):
        assert required in spec, required


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

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


def _phase34_docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            BOUNDARY_SPEC_PATH,
            GRAIN_SPEC_PATH,
            JOIN_SPEC_PATH,
            READINESS_SPEC_PATH,
            SEMANTIC_SPEC_PATH,
            CANDIDATE_SPEC_PATH,
        )
    )
