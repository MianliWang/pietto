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
SEMANTIC_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-semantic-readiness-contract-v1.md"
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


def test_phase34_slice5_plan_status_and_scope_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 5 Semantic Readiness Contract And Static Audit is "
        "the current docs/spec/static-audit/status-only readiness slice",
        "Proceed with Phase 34 Slice 5 as docs/spec/static-audit/status-only: "
        "define Semantic Readiness Contract for future relationship grain and "
        "narrow JOIN semantic validation/model integration; implement no "
        "semantic model changes, no semantic validation, no diagnostics, no "
        "JOIN, no grain behavior, no IR/SQL lowering, and no CLI/JSON/project/"
        "runtime behavior",
        "Slice 5 approved file scope is limited to",
        "`docs/spec/phase-34-semantic-readiness-contract-v1.md`",
        "`tests/test_phase34_semantic_readiness_contract.py`",
        "Slice 5 is the current docs/spec/static-audit/status-only readiness slice",
        "Phase 34 remains in progress after Slice 5",
        "Phase 34 is not complete",
    ):
        assert required in plan, required


def test_semantic_readiness_contract_exists_and_is_non_implementation() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    assert SEMANTIC_SPEC_PATH.is_file()
    for required in (
        "This specification records the Phase 34 Slice 5 Semantic Readiness Contract",
        "Slice 5 is docs/spec/static-audit/status-only work",
        "This document does not implement JOIN, does not implement JOIN "
        "syntax, does not implement grain syntax, does not implement grain "
        "semantic storage, does not change the semantic model, does not add "
        "semantic validation, does not add diagnostics, and does not change "
        "IR, SQL, CLI, JSON, project, runtime, or database behavior",
        "This spec does not change grammar, generated files, AST, parser "
        "behavior, semantic model, semantic validation, diagnostics, IR, SQL, "
        "CLI, JSON, fixtures, goldens, scripts, package metadata, "
        "dependencies, workflows, public API, project behavior, runtime "
        "behavior, or database behavior",
    ):
        assert required in spec, required


def test_slice1_to_slice4_boundaries_are_preserved() -> None:
    combined = _phase34_docs()

    for required in (
        "Narrow JOIN is later-slice only",
        "Relationship grain is a compile-time metadata contract around "
        "endpoint row identity and cardinality expectations",
        "Relationship grain prerequisites remain required future inputs before "
        "any narrow JOIN acceptance",
        "Final JOIN syntax is deferred and requires a later approved slice",
        "Final token spelling",
        "AST class names/fields",
        "Slice 5 preserves those boundaries",
        "JOIN implementation",
        "JOIN syntax implementation",
        "grain syntax implementation",
        "parser behavior changes",
    ):
        assert required in combined, required


def test_current_relationship_semantic_model_baseline_is_recorded() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "`RelationshipSemanticEndpointInfo(local_name, relation_name, relation)`",
        "`RelationshipSemanticInfo(name, endpoints)`",
        "`SemanticModel.relationships: tuple[RelationshipSemanticInfo, ...] = ()`",
        "endpoint `relation` is resolved `SourceDef | TableDef | QueryDef`",
        "there is no endpoint grain",
        "there is no relationship-edge grain",
        "there are no relation identity/key facts",
        "there is no cardinality/fanout posture",
        "there is no endpoint role ownership",
        "there is no JOIN scope owner",
        "there is no backend lowering capability fact",
        "They do not enter relation, type, callable, or field lookup",
        "They are not lowered to IR or SQL",
    ):
        assert required in spec, required


def test_current_relationship_validation_baseline_is_recorded() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "`PIE-S2601`: unknown endpoint relation",
        "`PIE-S2602`: duplicate relationship metadata name",
        "`PIE-S2603`: duplicate endpoint local name within one relationship",
        "Valid relationship metadata is stored in source order",
        "Invalid relationships do not enter `SemanticModel.relationships`",
        "Duplicate relationship scenarios preserve earlier valid metadata facts",
        "Self-relationship is currently allowed if endpoint local names are distinct",
        "Slice 5 adds no additional validation",
        "It adds no relationship selection validation",
        "no narrow JOIN semantic validation",
    ):
        assert required in spec, required


def test_current_single_input_field_lookup_constraints_are_recorded() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "`resolve_relation_inputs` resolves one `from_clause.source_name`",
        "field inference uses the current single input qualifier",
        "two-part dotted field references only bind when the qualifier is the "
        "current input qualifier",
        "unrelated relation names and relationship names do not participate in "
        "qualifier lookup",
        "projection aliases do not enter same-relation `where` or input-scope "
        "`order by`",
        "Future endpoint qualification and field ownership cannot be treated "
        "as a trivial extension of current single-input lookup",
    ):
        assert required in spec, required


def test_future_semantic_prerequisites_are_recorded_without_implementation() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "selected relationship edge binding",
        "base endpoint ownership",
        "joined endpoint ownership",
        "endpoint role disambiguation, including self-relationship",
        "endpoint schema visibility for multi-owner fields",
        "endpoint grain",
        "pairwise relationship-edge grain",
        "fanout/cardinality posture",
        "supported/unsupported semantic subset marker",
        "backend lowering capability proof",
        "deterministic fail-closed diagnostics for unknown/unsafe/ambiguous facts",
        "These are future prerequisites only",
        "Slice 5 does not add fields, classes, semantic facts, validators, "
        "diagnostics, IR shape, or SQL lowering",
    ):
        assert required in spec, required


def test_endpoint_field_ownership_and_qualification_remain_future_only() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "decide which endpoint owns each visible field",
        "decide how qualified fields select endpoint owner",
        "Duplicate field names must fail closed or resolve deterministically",
        "Self-relationship must use endpoint-local names or another explicit "
        "mechanism to disambiguate endpoint ownership",
        "Future `where`, `select`, and `order by` visibility must be specified "
        "before implementation",
        "Endpoint ownership, field ownership, endpoint qualification, "
        "self-relationship disambiguation, and duplicate field owner behavior "
        "are future-only in Slice 5",
    ):
        assert required in spec, required


def test_diagnostics_boundary_adds_no_new_codes() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "Slice 5 adds no diagnostic code additions",
        "Future diagnostic families may be needed for relationship selection",
        "endpoint ownership",
        "field ownership",
        "missing grain",
        "unknown grain",
        "unsafe grain",
        "contradictory grain",
        "unsupported fanout/cardinality",
        "backend capability",
        "ambiguous scope",
        "Adding actual diagnostic codes, messages, severities, spans, ordering, "
        "and JSON presentation is deferred",
        "Diagnostics can affect CLI JSON v1, Project JSON v2, Semantic "
        "Metadata Artifact v1, and stability audits",
    ):
        assert required in spec, required

    for allowed_code in ("PIE-S2601", "PIE-S2602", "PIE-S2603"):
        assert allowed_code in spec


def test_phase33_project_json_and_output_boundaries_remain_preserved() -> None:
    spec = _normalized(SEMANTIC_SPEC_PATH)

    for required in (
        "`RelationIR` remains single-source",
        "Slice 5 adds no SQL JOIN lowering",
        "Slice 5 changes no fixtures or goldens",
        "CLI JSON v1 is unchanged",
        "Project JSON v2 remains project check root/config-only",
        "Project emit-sql and project explain remain rejected",
        "Single-file explain JSON remains Semantic Metadata Artifact v1",
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
            SEMANTIC_SPEC_PATH,
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
