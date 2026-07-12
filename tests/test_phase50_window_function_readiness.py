from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase50-window-function-readiness-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
GENERATED_PARSER_PATH = REPO_ROOT / "src/pietto/generated/PiettoParser.py"
AST_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
SEMANTIC_CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
PARSER_RELATIONS_TEST_PATH = REPO_ROOT / "tests/test_parser_relations.py"
SEMANTIC_FUNCTIONS_TEST_PATH = REPO_ROOT / "tests/test_semantic_functions.py"
PHASE37_WINDOW_REJECTION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase37_grouped_aggregate_interaction_hardening.py"
)

SLICE4_SHA = "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b"
SLICE4_CI_RUN_ID = "29097916311"
SLICE5_TITLE = "# Phase 50 Slice 5 Window-Function Readiness v1"

INITIAL_RANKING_CATALOG = ("row_number", "rank", "dense_rank")

DEFERRED_WINDOW_FUNCTIONS = (
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
    "first_value",
    "last_value",
    "nth_value",
    "aggregate-as-window",
    "count_distinct as window",
    "percentile/statistical functions",
    "ordered-set and hypothetical-set functions",
    "dialect-specific analytics",
)

WINDOW_SPEC_COMPONENTS = (
    "function call",
    "arguments",
    "partition list",
    "window-local order list",
    "ordering direction",
    "frame unit",
    "frame start/end",
    "exclusion",
    "named-window reference",
    "inheritance/extension",
)

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Window-Surface Evidence",
    "Window Function Taxonomy",
    "Ranking Function Readiness",
    "Navigation And Value Function Readiness",
    "Aggregate-as-Window Readiness",
    "Window Specification Components",
    "Partition Expression Readiness",
    "Window-local Ordering Readiness",
    "Frame Readiness",
    "Named Window Readiness",
    "Query Phase And Clause Placement",
    "Grouped / Aggregate / Let Interaction",
    "Type And Nullability Matrix",
    "Capability Prerequisites",
    "Output Identity And Project Schema",
    "Dependency And Lineage Readiness",
    "Diagnostic And Fail-closed Matrix",
    "Dialect And SQL-Lowering Boundary",
    "Cross-phase Dependencies",
    "Bounded Phase 53 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

ALLOWED_PHASE50_SLICE5_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-window-function-readiness-v1.md",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
}

ALLOWED_PHASE50_SLICE6_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-import-module-export-readiness-v1.md",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
}

ALLOWED_PHASE50_SLICE7_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-semantic-package-model-readiness-v1.md",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
}

ALLOWED_PHASE50_SLICE8_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-postgresql-extension-capability-readiness-v1.md",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
}

ALLOWED_PHASE50_SLICE9_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-multi-dialect-capability-ecosystem-readiness-v1.md",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
}

ALLOWED_PHASE50_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
}

ALLOWED_PHASE50_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-completion-audit-and-status-lock-v1.md",
    "tests/test_phase50_completion_audit_and_status_lock.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_window_function_readiness.py",
    "tests/test_phase50_import_module_export_readiness.py",
    "tests/test_phase50_semantic_package_model_readiness.py",
    "tests/test_phase50_postgresql_extension_capability_readiness.py",
    "tests/test_phase50_multi_dialect_capability_ecosystem_readiness.py",
    "tests/test_phase50_explain_public_metadata_package_integration_boundary.py",
}

COMPATIBILITY_TEST_PATHS = (
    REPO_ROOT
    / "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    REPO_ROOT / "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    REPO_ROOT
    / "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
    REPO_ROOT / "tests/test_phase50_type_system_gap_capability_readiness.py",
)

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
    "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "src",
    "grammar",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "examples",
)


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.rstrip()


def _dirty_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths


def _section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    remainder = text[start + len(f"## {heading}") :]
    next_offset = remainder.find("\n## ")
    return remainder if next_offset == -1 else remainder[:next_offset]


def test_slice5_artifacts_baseline_and_current_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _read(SPEC_PATH)

    assert SLICE5_TITLE in spec
    for required in (
        "Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed",
        SLICE4_SHA,
        SLICE4_CI_RUN_ID,
        "CI / push",
        "completed / success",
        "exact `headSha` match",
        "Phase 50 Slice 5 **Window-Function Readiness** completed",
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "29115612846",
        "Phase 50 Slice 6 **Import / Module / Export Readiness** completed",
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "29139545163",
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "29141663534",
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "29157374991",
        "Slice 8 completed",
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed",
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "29170827348",
        "Slice 9 completed",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 53 remains `READINESS_CONTRACT_ONLY`",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in plan, required

    historical_spec = _normalized(SPEC_PATH)
    combined = f"{plan} {historical_spec}"
    for forbidden in (
        "Phase 50 is complete after Slice 11 Gate 2",
        "Phase 52 has started",
        "Phase 53 has started",
        "Phase 53 implementation is authorized",
    ):
        assert forbidden not in combined, forbidden
    assert "Slice 5 is current but incomplete in Gate 2." in historical_spec
    assert "Slice 5 is complete" not in historical_spec


def test_spec_section_order_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    offsets = [spec.index(f"## {section}") for section in REQUIRED_SPEC_SECTIONS]

    assert offsets == sorted(offsets)
    assert "Slice 5 implements no compiler or runtime behavior." in spec
    normalized = _normalized(SPEC_PATH)
    for required in (
        "Generic call syntax is not window support.",
        "Ordinary aggregate support is not aggregate-as-window support.",
        "Phase 52 remains unstarted.",
        "Phase 53 remains unstarted.",
        "Phase 53 remains READINESS_CONTRACT_ONLY under the current finalized route.",
        "Slices 6 through 11 remain pending",
        "Package version remains `0.1.0`.",
        "No production window API is designed.",
    ):
        assert required in normalized, required


def test_current_source_has_generic_calls_but_no_window_model() -> None:
    grammar = _read(GRAMMAR_PATH)
    generated_parser = _read(GENERATED_PARSER_PATH)
    ast_source = _read(AST_PATH)
    catalog = _read(SEMANTIC_CATALOG_PATH)
    aggregates = _read(AGGREGATES_PATH)
    ir_model = _read(IR_MODEL_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)
    project_model = _read(PROJECT_MODEL_PATH)
    metadata_builder = _read(METADATA_BUILDER_PATH)

    assert "dottedName callSuffix?" in grammar
    assert "class CallExpr(Expression):" in ast_source
    assert "class CallIR(ExpressionIR):" in ir_model
    assert "class AggregateCallIR(ExpressionIR):" in ir_model

    for token in (
        "OVER",
        "WINDOW",
        "PARTITION",
        "QUALIFY",
        "ROWS",
        "RANGE",
        "GROUPS",
        "PRECEDING",
        "FOLLOWING",
    ):
        assert f"{token}:" not in grammar, token
        assert f"'{token}'" not in generated_parser, token

    assert "class Window" not in ast_source
    assert "class Window" not in ir_model
    assert "OVER" not in postgres
    assert "OVER" not in mysql

    for name in INITIAL_RANKING_CATALOG:
        assert f'"{name}"' not in catalog, name
        assert f'"{name}"' not in aggregates, name

    for vocabulary in (
        "WINDOW_RESULT",
        "WINDOW_ARGUMENT",
        "WINDOW_PARTITION",
        "WINDOW_ORDER",
        "WINDOW_FRAME",
        "WINDOW_DEFAULT",
    ):
        assert vocabulary not in project_model, vocabulary
        assert vocabulary not in metadata_builder, vocabulary


def test_generic_call_aggregate_and_parser_rejection_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    parser_relations = _read(PARSER_RELATIONS_TEST_PATH)
    semantic_functions = _read(SEMANTIC_FUNCTIONS_TEST_PATH)
    phase37 = _read(PHASE37_WINDOW_REJECTION_TEST_PATH)

    for required in (
        "generic function-shaped calls may parse as ordinary calls",
        "`row_number()` is not a recognized window function",
        "unknown generic function follows the current fail-closed unknown-function path",
        "current relation `order by` is final query order, not window-local order",
        "current grouped `satisfying` is GROUP/HAVING behavior, not QUALIFY",
    ):
        assert required in spec, required

    assert '"    window recent\\n"' in parser_relations
    assert "PIE-P1000" in parser_relations
    assert '"total = sum(amount) over (region)"' in phase37
    assert "PIE-P1000" in phase37
    assert "test_unknown_function_reports_pie_s2103" in semantic_functions
    assert "PIE-S2103" in semantic_functions


def test_exact_initial_catalog_and_deferred_families_are_locked() -> None:
    spec = _read(SPEC_PATH)
    ranking = _section(spec, "Ranking Function Readiness")
    normalized = _normalized(SPEC_PATH)
    normalized_without_code_ticks = normalized.replace("`", "")

    assert (
        "The exact initial readiness catalog is `row_number`, `rank`, and "
        "`dense_rank` only."
    ) in normalized
    for name in INITIAL_RANKING_CATALOG:
        assert ranking.count(f"| `{name}` |") == 1, name
    for name in DEFERRED_WINDOW_FUNCTIONS:
        assert name in normalized_without_code_ticks, name
        assert f"| `{name}` |" not in ranking, name

    for name in INITIAL_RANKING_CATALOG:
        row = next(
            line for line in ranking.splitlines() if line.startswith(f"| `{name}` |")
        )
        for fact in ("zero", "`Int`", "`NON_NULL`", "optional", "mandatory"):
            assert fact in row, (name, fact)
        assert "readiness-only, not implemented" in row

    assert "No function is implemented or reserved by this readiness catalog." in spec


def test_window_components_partition_order_frame_and_names_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    components = _section(_read(SPEC_PATH), "Window Specification Components")

    for component in WINDOW_SPEC_COMPONENTS:
        assert component in components, component
    for required in (
        "initial posture is inline and unnamed",
        "optional direct-field partition list",
        "mandatory direct-field window order",
        "optional `asc` / `desc`",
        "no explicit frame",
        "no null-ordering control",
        "no exclusion",
        "no named-window reference",
        "no inheritance",
        "Slice 5 reserves no exact future source spelling",
        "Partitioning is optional",
        "direct bare fields or current single-input-qualified direct fields",
        "Window-local ordering is mandatory",
        "No backend-default frame is promoted",
        "Named windows, named-window references, inheritance, and extension remain deferred",
    ):
        assert required in spec, required


def test_query_phase_and_clause_placement_are_locked() -> None:
    section = _section(_read(SPEC_PATH), "Query Phase And Clause Placement")
    normalized = " ".join(section.split())

    phases = (
        "input relation and relation-local let facts",
        "row-level where",
        "grouping and ordinary aggregate calculation",
        "satisfying/HAVING",
        "window calculation",
        "final relation order",
        "limit",
    )
    offsets = [normalized.index(phase) for phase in phases]
    assert offsets == sorted(offsets)

    for required in (
        "direct top-level explicitly aliased `select` projection | permit",
        "unaliased output | reject",
        "`let` | defer",
        "`where` | reject",
        "group key | reject",
        "aggregate argument | reject",
        "`satisfying` | reject",
        "another-window argument | reject",
        "nested scalar expression | reject initially",
        "same-select alias reuse | defer",
        "selected window alias in final order | defer",
        "direct window expression in final order | reject/defer",
        "QUALIFY-like filtering | defer; no syntax",
    ):
        assert required in normalized, required


def test_group_type_nullability_and_capability_prerequisites_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    type_matrix = _section(_read(SPEC_PATH), "Type And Nullability Matrix")

    for required in (
        "Ungrouped ranking is the initial readiness candidate",
        "Grouped ranking remains deferred until Phase 51 and Phase 52 evidence exists",
        "Aggregate-as-window and window aggregate over grouped output remain deferred",
        "Let-bound partition or window-order expressions and selected alias reuse remain deferred",
        "Repeated dependencies must be deterministic and first-occurrence deduplicated",
        "Logical result type, compiler nullability, runtime numbering/tie behavior, backend spelling, and dialect behavior are separate facts",
        "Phase 52 remains unstarted",
        "Slice 5 adds no production capability carrier",
    ):
        assert required in spec, required

    for name in INITIAL_RANKING_CATALOG:
        row = next(
            line
            for line in type_matrix.splitlines()
            if line.startswith(f"| `{name}` |")
        )
        assert "`Int`" in row
        assert "`NON_NULL`" in row


def test_output_dependency_lineage_and_privacy_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Every initial candidate projection requires an explicit alias",
        "There is no default output name",
        "Selected output order follows source `select` order",
        "`WINDOW_RESULT` is documentation-only private result vocabulary",
        "distinct from `GROUP_KEY` and `AGGREGATE_RESULT`",
        "Immediate provenance remains derived-expression posture",
        "No production enum, class, field, carrier, serializer, Project JSON field, public metadata, public lineage, explain output, or public API",
        "`WINDOW_ARGUMENT`",
        "`WINDOW_PARTITION`",
        "`WINDOW_ORDER`",
        "`WINDOW_FRAME`",
        "`WINDOW_DEFAULT`",
        "relation-input dependency for argument-less ranking functions",
        "Final relation order remains separate from window-local order",
    ):
        assert required in spec, required


def test_diagnostic_dialect_and_bounded_phase53_handoff_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "No window-specific diagnostic code exists",
        "Slice 5 adds or reserves no public diagnostic code",
        "PostgreSQL and private MySQL receive no current window support claim",
        "Each exact feature must fail closed independently",
        "Phase 53 — Window Function Syntax And Capability Contract remains `READINESS_CONTRACT_ONLY`",
        "Phase 53 remains unstarted",
        "Concrete window implementation remains outside Phase 51–60 until an evidence-backed append-only replan separately authorizes it",
        "That handoff excludes production grammar, generated parser changes, AST, semantic carriers, IR, SQL, diagnostics",
    ):
        assert required in spec, required


def test_compatibility_guards_protected_surfaces_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    for compatibility_path in COMPATIBILITY_TEST_PATHS:
        compatibility = _read(compatibility_path)
        assert "ALLOWED_PHASE50_SLICE5_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE6_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE7_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE8_GATE2_PATHS" in compatibility
        for relative_path in ALLOWED_PHASE50_SLICE5_GATE2_PATHS:
            assert f'"{relative_path}"' in compatibility, (
                compatibility_path,
                relative_path,
            )
        for relative_path in ALLOWED_PHASE50_SLICE6_GATE2_PATHS:
            assert f'"{relative_path}"' in compatibility, (
                compatibility_path,
                relative_path,
            )
        for relative_path in ALLOWED_PHASE50_SLICE7_GATE2_PATHS:
            assert f'"{relative_path}"' in compatibility, (
                compatibility_path,
                relative_path,
            )
        for relative_path in ALLOWED_PHASE50_SLICE8_GATE2_PATHS:
            assert f'"{relative_path}"' in compatibility, (
                compatibility_path,
                relative_path,
            )

    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    for relative_path in PROTECTED_PATHS:
        assert _git_output(["diff", "--", relative_path]) == "", relative_path
    assert _dirty_paths() in (
        set(),
        ALLOWED_PHASE50_SLICE5_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE6_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE7_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
    )
