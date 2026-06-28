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
JOIN_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md"
)
READINESS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-parser-ast-readiness-contract-v1.md"
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
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase34_candidate_decision.py",
    "tests/test_phase34_relationship_grain_contract.py",
    "tests/test_phase34_narrow_join_contract.py",
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


def test_phase34_slice4_plan_status_and_scope_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 4 Parser / AST Readiness Contract And Static Audit is "
        "the current docs/spec/static-audit/status-only readiness slice",
        "Proceed with Phase 34 Slice 4 as docs/spec/static-audit/status-only: "
        "define Parser / AST readiness requirements for future narrow JOIN "
        "work, preserving current single-input grammar and AST behavior and "
        "deferring final token spelling, grammar productions, AST class "
        "names/fields, semantic model changes, diagnostics, IR shape, SQL "
        "lowering, CLI/JSON/project behavior, fixtures/goldens, scripts, "
        "package/dependency/workflow changes, and release operations",
        "Slice 4 approved file scope is limited to",
        "`docs/spec/phase-34-parser-ast-readiness-contract-v1.md`",
        "`tests/test_phase34_parser_ast_readiness_contract.py`",
        "Slice 4 is the current docs/spec/static-audit/status-only readiness slice",
        "Phase 34 remains in progress after Slice 4",
        "Phase 34 is not complete",
    ):
        assert required in plan, required


def test_parser_ast_readiness_contract_exists_and_is_non_implementation() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    assert READINESS_SPEC_PATH.is_file()
    for required in (
        "This specification records the Phase 34 Slice 4 Parser / AST "
        "readiness contract",
        "Slice 4 is docs/spec/static-audit/status-only work",
        "This document does not implement JOIN, does not implement JOIN "
        "syntax, does not implement grain syntax, does not implement parser "
        "behavior, and does not define accepted Pietto syntax",
        "This spec does not change grammar, generated files, AST, parser "
        "behavior, semantic model, IR, SQL, CLI, JSON, fixtures, goldens, "
        "scripts, package metadata, dependencies, workflows, public API, "
        "project behavior, runtime behavior, or database behavior",
    ):
        assert required in spec, required


def test_slice1_to_slice3_boundaries_and_grain_prerequisites_are_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "Narrow JOIN is later-slice only",
        "Relationship grain is a compile-time metadata contract around "
        "endpoint row identity and cardinality expectations",
        "relationship grain prerequisites remain required future inputs before "
        "any narrow JOIN acceptance",
        "Final JOIN syntax is deferred and requires a later approved slice",
        "final token spelling is deferred",
        "JOIN implementation",
        "JOIN syntax implementation",
        "grain syntax implementation",
        "Slice 4 preserves those boundaries",
    ):
        assert required in combined, required


def test_current_grammar_constraints_are_recorded() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "`script` accepts top-level `definition` and `relationshipDefinition` entries",
        "`relationshipDefinition` is top-level relationship metadata",
        "relationship metadata currently has exactly two endpoints",
        "endpoint syntax currently records a local endpoint name and a relation name",
        "relation body currently has one `fromClause`",
        "`fromClause` is single-input",
        "Pietto blocks use colon, newline, indentation, and dedentation",
        "there is no accepted join production",
        "there is no accepted grain syntax",
    ):
        assert required in spec, required


def test_current_ast_constraints_are_recorded() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "`RelationshipMetadata`",
        "`RelationshipEndpoint`",
        "`FromClause(source_name)`",
        "`TableDef` has one `from_clause`",
        "`QueryDef` has one `from_clause`",
        "there is no AST node for a join list",
        "there is no AST node for endpoint scope",
        "there is no AST node for relationship edge selection",
        "there is no AST node for a grain carrier",
        "there is no AST behavior for a multi-input field owner",
        "Slice 4 does not modify `src/pietto/ast_nodes.py` or "
        "`src/pietto/ast_builder.py`",
    ):
        assert required in spec, required


def test_generated_file_implications_are_locked() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "Changes to `grammar/Pietto.g4` require regenerating the tracked ANTLR "
        "outputs under `src/pietto/generated/`",
        "The `src/pietto/generated/` inventory must remain byte-for-byte "
        "verified by `scripts/check_generated.py`",
        "Slice 4 does not modify grammar or generated files",
        "Slice 4 does not modify `grammar/Pietto.g4`",
    ):
        assert required in spec, required


def test_future_readiness_requirements_are_deferred_without_final_syntax() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "Future parser and AST implementation remains deferred",
        "final token spelling is deferred",
        "final grammar productions are deferred",
        "final AST class names/fields are deferred",
        "future AST/source shape must represent the selected relationship edge",
        "future AST/source shape must represent one base relation or endpoint owner",
        "future AST/source shape must represent exactly one joined endpoint",
        "future AST/source shape must represent deterministic endpoint qualification",
        "future AST/source shape must leave room for field ownership",
        "future AST/source shape must leave room for grain prerequisite "
        "references or semantic binding",
        "future AST/source shape must handle self-relationship disambiguation",
        "future AST/source shape must preserve single-input compatibility",
        "These requirements do not define final syntax, do not define final "
        "class names, and do not approve implementation",
    ):
        assert required in spec, required


def test_semantic_ir_sql_cli_json_project_boundaries_are_locked() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "Slice 4 adds no semantic validation and no diagnostic codes",
        "Later semantic work must separately decide relationship selection, "
        "endpoint ownership, field ownership, grain requirements, unsupported "
        "fanout/cardinality behavior, backend capability handling, and "
        "fail-closed diagnostics",
        "Slice 4 changes no `RelationIR` shape and adds no SQL JOIN lowering",
        "Slice 4 changes no fixtures or goldens",
        "no CLI behavior",
        "no JSON v1 behavior",
        "no Project JSON v2 behavior",
        "no Semantic Metadata Artifact v1 behavior",
    ):
        assert required in spec, required


def test_phase33_project_json_boundaries_remain_preserved() -> None:
    spec = _normalized(READINESS_SPEC_PATH)

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "TOML schema parsing remains deferred",
        "glob expansion remains deferred",
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
        _normalized(path)
        for path in (
            PLAN_PATH,
            BOUNDARY_SPEC_PATH,
            GRAIN_SPEC_PATH,
            JOIN_SPEC_PATH,
            READINESS_SPEC_PATH,
        )
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
