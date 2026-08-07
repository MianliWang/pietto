from __future__ import annotations

import ast
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice11_pr_ci_repair_is_active,
    phase54_slice12_pr_ci_repair_is_active,
    phase54_slice12_mechanical_repair3_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
    phase54_slice11_python313_repair_is_active,
    phase54_slice11_substantive_recovery_is_active,
)

from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase50-import-module-export-readiness-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
AST_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
PROJECT_CONFIG_PATH = REPO_ROOT / "src/pietto/_project/config.py"
PROJECT_DISCOVERY_PATH = REPO_ROOT / "src/pietto/_project/discovery.py"
PROJECT_SOURCE_SELECTION_PATH = REPO_ROOT / "src/pietto/_project/source_selection.py"
PROJECT_CHECK_PATH = REPO_ROOT / "src/pietto/_project/check.py"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"
PHASE54_STATE_PATH = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"

SLICE5_SHA = "d79c5c422cb7f54ae5e5587694e49389536419cb"
SLICE5_CI_RUN_ID = "29115612846"
SLICE6_TITLE = "# Phase 50 Slice 6 Import / Module / Export Readiness v1"

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Multi-file Project Model",
    "Current Namespace And Visibility Model",
    "Current Declaration-kind Matrix",
    "Import / Export / Module Evidence Inventory",
    "Conceptual Vocabulary",
    "Module-model Route Comparison",
    "Recommended Module Boundary",
    "Module Identity And Canonical Path Readiness",
    "Import Binding Readiness",
    "Export And Visibility Readiness",
    "Reference And Qualification Readiness",
    "Module Graph And Deterministic Ordering",
    "Cycle Taxonomy And Fail-closed Posture",
    "Duplicate Ambiguity And Shadowing",
    "Legacy Project Compatibility",
    "Local Module And Semantic Package Boundary",
    "Public And Private Metadata Boundary",
    "Diagnostic And Fail-closed Matrix",
    "Cross-phase Dependencies",
    "Bounded Phase 54 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

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
    REPO_ROOT / "tests/test_phase50_window_function_readiness.py",
)

PROTECTED_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/phase50-semantic-package-extension-capability-scope-lock-v1.md",
    "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
    "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "docs/spec/phase50-window-function-readiness-v1.md",
    "docs/plan/phase-4[4-9]*",
    "docs/spec/phase4[4-9]*",
    "tests/test_phase4[4-9]*.py",
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


def _phase54_slice9_gate2_paths() -> set[str]:
    tree = ast.parse(PHASE54_STATE_PATH.read_text(encoding="utf-8"))
    assignments = {
        node.targets[0].id: node.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
    }

    def resolve(node: ast.expr) -> set[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value}
        if isinstance(node, ast.Name):
            return resolve(assignments[node.id])
        if isinstance(node, ast.Starred):
            return resolve(node.value)
        if isinstance(node, ast.Set):
            return set().union(*(resolve(element) for element in node.elts))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "set"
            and not node.args
            and not node.keywords
        ):
            return set()
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return resolve(node.left) | resolve(node.right)
        raise AssertionError(ast.dump(node))

    return resolve(assignments["ALLOWLIST_PATHS"])


def _section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    remainder = text[start + len(f"## {heading}") :]
    next_offset = remainder.find("\n## ")
    return remainder if next_offset == -1 else remainder[:next_offset]


def _normalized_section(path: Path, heading: str) -> str:
    return " ".join(_section(_read(path), heading).split())


def _plain_section(path: Path, heading: str) -> str:
    return _normalized_section(path, heading).replace("`", "")


def _text_class_assignment_names(source: str, class_name: str) -> tuple[str, ...]:
    marker = f"class {class_name}(StrEnum):"
    start = source.index(marker) + len(marker)
    remainder = source[start:]
    end_offsets = (
        remainder.find("\n\nclass "),
        remainder.find("\n\n@dataclass"),
    )
    valid_end_offsets = tuple(offset for offset in end_offsets if offset != -1)
    assert valid_end_offsets
    class_body = remainder[: min(valid_end_offsets)]
    return tuple(
        line.strip().split(" = ", maxsplit=1)[0]
        for line in class_body.splitlines()
        if line.startswith("    ") and " = " in line
    )


def _string_set_assignment(source: str, assignment_name: str) -> set[str]:
    module = ast.parse(source)
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == assignment_name
            for target in node.targets
        ):
            continue

        assert isinstance(node.value, ast.Set)
        values: set[str] = set()
        for element in node.value.elts:
            assert isinstance(element, ast.Constant)
            assert isinstance(element.value, str)
            values.add(element.value)
        return values

    raise AssertionError(f"assignment not found: {assignment_name}")


def test_slice6_artifacts_baseline_and_current_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    spec = _read(SPEC_PATH)
    status = _normalized_section(PLAN_PATH, "Status")
    assert spec.splitlines()[0] == SLICE6_TITLE
    for required in (
        "Phase 50 Slice 5 **Window-Function Readiness** completed",
        SLICE5_SHA,
        SLICE5_CI_RUN_ID,
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
        assert required in status, required

    for forbidden in (
        "Slice 7 completed",
        "Phase 50 is complete after Slice 11 Gate 2",
        "Phase 54 has started",
        "Phase 54 is started",
        "Phase 55 has started",
        "Phase 55 is started",
    ):
        assert forbidden not in status, forbidden


def test_spec_exact_sections_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        line.removeprefix("## ") for line in spec.splitlines() if line.startswith("## ")
    )

    assert headings == REQUIRED_SPEC_SECTIONS
    assert spec.count("Slice 6 implements no compiler or runtime behavior.") == 1
    purpose = _normalized_section(SPEC_PATH, "Purpose And Slice Identity")
    for required in (
        "docs/spec/static-audit-only readiness work",
        "Slices 1 through 5 are complete",
        "Slice 6 is current but incomplete in Gate 2",
        "Slices 7 through 11 remain pending and separately authorized",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains unstarted",
    ):
        assert required in purpose, required


def test_current_project_model_namespaces_and_declaration_ownership_are_locked() -> (
    None
):
    model_source = _read(PROJECT_MODEL_PATH)
    project_model = _plain_section(SPEC_PATH, "Current Multi-file Project Model")
    namespace_model = _plain_section(
        SPEC_PATH, "Current Namespace And Visibility Model"
    )
    declaration_matrix = _read(SPEC_PATH)

    assert _text_class_assignment_names(model_source, "ProjectSymbolNamespace") == (
        "TYPE",
        "RELATION",
        "CALLABLE",
    )
    assert _text_class_assignment_names(model_source, "ProjectSymbolKind") == (
        "TYPE_ALIAS",
        "ENUM",
        "SHAPE",
        "SOURCE",
        "TABLE",
        "QUERY",
        "CONSTRAINT",
        "DERIVE",
    )
    for required in (
        "collect supported top-level definitions into one ProjectSemanticCatalog",
        "All supported top-level definitions are collected before supported project references are resolved",
        "Supported cross-file references require no import",
        "Files are semantically transparent after discovery",
        "It does not create file-local visibility",
    ):
        assert required in project_model, required
    for required in (
        "exactly three flat project-global namespaces",
        "TYPE | type aliases, enums, shapes",
        "RELATION | sources, tables, queries",
        "CALLABLE | constraints, derives",
        "same spelling may occur once in each different namespace",
        "no import/export/module visibility",
    ):
        assert required in namespace_model, required

    for row in (
        "| type alias | TYPE |",
        "| enum | TYPE |",
        "| shape | TYPE |",
        "| constraint | CALLABLE |",
        "| derive | CALLABLE |",
        "| source | RELATION |",
        "| table | RELATION |",
        "| query | RELATION |",
        "| relationship metadata | separate metadata, not ProjectSymbol |",
    ):
        assert row in declaration_matrix, row


def test_current_collection_path_and_project_input_identity_evidence_are_locked() -> (
    None
):
    source_selection = _read(PROJECT_SOURCE_SELECTION_PATH)
    project_check = _read(PROJECT_CHECK_PATH)
    project_model = _read(PROJECT_MODEL_PATH)

    assert '_PIETTO_SUFFIX = ".pietto"' in source_selection
    assert "for relative_path in sorted(selected_paths):" in source_selection
    assert "resolved_path.relative_to(pinned_root.canonical_path)" in source_selection
    assert "identity = final_target_state.physical_identity" in source_selection
    assert "for entry in selected_input_index.entries:" in project_check
    assert "trusted_source.source_text" in project_check
    assert "path=selected_input.identity.path," in project_check
    assert "for parsed_input in parsed_inputs:" in project_model
    assert "for definition in parsed_input.script.definitions:" in project_model
    assert 'code="PIE-S2001"' in project_model

    for path in (PROJECT_CONFIG_PATH, PROJECT_DISCOVERY_PATH, CLI_PATH):
        assert path.is_file()


def test_no_current_language_or_production_module_carrier_is_claimed() -> None:
    grammar = _read(GRAMMAR_PATH)
    ast_source = _read(AST_PATH)
    model_source = _read(PROJECT_MODEL_PATH)
    json_source = _read(PROJECT_JSON_V2_PATH)
    inventory = _plain_section(SPEC_PATH, "Import / Export / Module Evidence Inventory")

    for present_rule in (
        "moduleStatement",
        "importStatement",
        "exportStatement",
        "importItem",
        "exportItem",
        "IMPORT:",
        "EXPORT:",
        "AS:",
    ):
        assert present_rule in grammar, present_rule
    for absent_rule in (
        "importDefinition",
        "exportDefinition",
        "moduleDefinition",
        "visibilityDefinition",
        "reexportDefinition",
        "MODULE:",
        "VISIBILITY:",
        "REEXPORT:",
    ):
        assert absent_rule not in grammar, absent_rule
    for present_class in (
        "class ImportItem(",
        "class ImportStatement(",
        "class ExportItem(",
        "class ExportStatement(",
    ):
        assert present_class in ast_source, present_class
    for absent_class in (
        "class ImportDef(",
        "class ExportDef(",
        "class ModuleDef(",
        "class VisibilityDef(",
    ):
        assert absent_class not in ast_source, absent_class
    for absent_carrier in (
        "class ProjectModule",
        "ProjectImport",
        "ProjectExport",
        "ProjectVisibility",
    ):
        assert absent_carrier not in model_source, absent_carrier
    for absent_key in ('"modules"', '"imports"', '"exports"', '"visibility"'):
        assert absent_key not in json_source, absent_key

    for required in (
        "Python imports are implementation-language imports, not Pietto language imports",
        "Relation from is relation lookup and dependency, not a module import",
        "source connector declaration is a static source declaration, not a module import, semantic-package import, or runtime connector load",
        "not module loading",
    ):
        assert required in inventory, required


def test_route_d_module_identity_and_legacy_compatibility_are_locked() -> None:
    route = _plain_section(SPEC_PATH, "Module-model Route Comparison")
    boundary = _plain_section(SPEC_PATH, "Recommended Module Boundary")
    identity = _plain_section(SPEC_PATH, "Module Identity And Canonical Path Readiness")
    compatibility = _plain_section(SPEC_PATH, "Legacy Project Compatibility")

    assert "D: hybrid compatibility" in route
    assert "selected readiness direction" in route
    assert "Current flat project-global behavior remains unchanged" in route
    for required in (
        "future separately activated explicit-module mode",
        "one selected .pietto file as one local module",
        "No current file becomes a module",
        "No logical module spans multiple files initially",
        "No directory automatically becomes a module",
        "No manifest is introduced",
    ):
        assert required in boundary, required
    for required in (
        "exact current normalized project-relative selected input path, including the .pietto suffix",
        "not a source-language module name",
        "not a public Project JSON module identity",
        "not a semantic-package identity",
        "not a package-qualified name",
        "preserves current root containment and invalid-path rejection",
        "preserves symlink/root-escape protection",
        "preserves duplicate physical-file handling",
        "Case folding, Unicode normalization, cross-platform case-collision rules",
        "Slice 6 changes no discovery, path, symlink, or filesystem behavior",
    ):
        assert required in identity, required
    for required in (
        "Route D preserves current flat behavior",
        "must be additive and separately activated",
        "selects no compatibility mode flag",
        "automated migration",
        "automatic legacy import",
        "source rewrite",
    ):
        assert required in compatibility, required


def test_import_export_eligibility_and_qualification_readiness_are_locked() -> None:
    imports = _plain_section(SPEC_PATH, "Import Binding Readiness")
    exports = _plain_section(SPEC_PATH, "Export And Visibility Readiness")
    references = _plain_section(SPEC_PATH, "Reference And Qualification Readiness")

    for required in (
        "explicit named imports only",
        "optional local alias",
        "one explicitly exported declaration creates one local imported binding",
        "every imported binding must be unique",
        "textual import ordering does not change meaning",
        "no transitive visibility",
        "no implicit re-export",
        "no automatic import of legacy project-global declarations",
        "type aliases, enums, shapes, sources, tables, and queries",
        "Constraints and derives are deferred",
        "Relationship metadata is excluded",
        "Wildcard/star, namespace/module-object, side-effect, type-only, relation-only, package-qualified, implicit, transitive",
    ):
        assert required in imports, required
    for required in (
        "declarations are private by default",
        "explicit export list",
        "only local declarations may be exported",
        "imported bindings are excluded",
        "Implicit export-all, public-by-default, wildcard exports, export aliases, re-exports",
        "does not imply Project JSON serialization",
    ):
        assert required in exports, required
    for required in (
        "local declaration and future explicit imported binding are distinct lookup sources",
        "No local declaration shadows an imported binding",
        "No imported binding shadows a local declaration",
        "No ambiguous reference receives a winner",
        "Module-qualified, file-path-qualified, and package-qualified source references remain deferred",
    ):
        assert required in references, required


def test_graph_cycle_collision_and_diagnostic_boundaries_are_locked() -> None:
    graph = _plain_section(SPEC_PATH, "Module Graph And Deterministic Ordering")
    cycles = _plain_section(SPEC_PATH, "Cycle Taxonomy And Fail-closed Posture")
    collisions = _plain_section(SPEC_PATH, "Duplicate Ambiguity And Shadowing")
    diagnostics = _plain_section(SPEC_PATH, "Diagnostic And Fail-closed Matrix")

    for required in (
        "one canonical local module identity",
        "one explicit named import",
        "separate from relation dependency graphs, row dependency graphs, row lineage, type-alias cycles, package dependency graphs",
        "canonical project input order",
        "declaration source order per input",
        "import source order per future module",
        "Imported binding order never changes semantics",
    ):
        assert required in graph, required
    for required in (
        "module import | none | fail closed initially",
        "re-export | none; feature deferred | fail closed if later introduced",
        "There is no initial type-only module-cycle exception",
        "PIE-S2302 is not reused for module cycles",
        "adds or reserves no diagnostic code",
    ):
        assert required in cycles, required
    for required in (
        "duplicate module identity",
        "duplicate local declaration within one namespace",
        "duplicate export",
        "duplicate imported binding",
        "local/import collision",
        "two imports exposing one local name",
        "alias collision",
        "ambiguous unqualified reference",
        "private-symbol access",
        "missing export",
        "unresolved module",
        "There is no semantic winner after a collision",
        "do not shadow each other",
    ):
        assert required in collisions, required
    for required in (
        "Existing PIE-S2001, PIE-S2002, PIE-S2301, and PIE-S2302 categories are not automatically reused",
        "Slice 6 adds no diagnostic",
    ):
        assert required in diagnostics, required


def test_local_module_package_public_metadata_and_phase_handoff_are_locked() -> None:
    package_boundary = _plain_section(
        SPEC_PATH, "Local Module And Semantic Package Boundary"
    )
    public_boundary = _plain_section(SPEC_PATH, "Public And Private Metadata Boundary")
    dependencies = _plain_section(SPEC_PATH, "Cross-phase Dependencies")
    handoff = _plain_section(SPEC_PATH, "Bounded Phase 54 Handoff")

    for required in (
        "Slice 6 and Phase 54 local-module concerns are project-local",
        "Slice 7 and Phase 55 semantic-package concerns are package identity, package version, asset kinds/schema",
        "Registry access, remote fetch, installation, cache management, dependency solving, lockfiles, executable package code",
        "package-qualified target only after package identity and asset resolution are separately defined",
        "defines no package target grammar or package resolver",
    ):
        assert required in package_boundary, required
    for required in (
        "Project JSON v2 currently exposes project root/config facts",
        "exposes no project catalog, module identity, import binding, export surface",
        "Future module facts remain private initially",
        "Phase 58 is the public-exposure prerequisite",
        "Slice 6 adds no Project JSON field",
    ):
        assert required in public_boundary, required
    for required in (
        "Phase 52 is unrelated to local binding behavior and remains unstarted",
        "Phase 53 is unrelated to local module resolution, remains unstarted, and remains READINESS_CONTRACT_ONLY",
        "Phase 54 receives this bounded readiness handoff and remains unstarted",
        "Phase 55 owns semantic package assets and remains unstarted",
        "No dependency starts or authorizes another phase",
    ):
        assert required in dependencies, required
    for required in (
        "remains readiness-only and unstarted",
        "It is separately authorized",
        "Route D compatibility direction",
        "private file-as-module identity candidate",
        "explicit named imports plus optional aliases",
        "explicit private-by-default export lists",
        "local-module versus semantic-package separation",
        "excludes grammar, exact source syntax, generated parser changes, AST, production carriers, resolver behavior",
        "does not upgrade Phase 54 into an implementation phase",
    ):
        assert required in handoff, required


def test_non_goals_package_version_and_release_boundaries_are_locked() -> None:
    non_goals = _plain_section(SPEC_PATH, "Explicit Deferrals And Non-goals")
    release = _plain_section(SPEC_PATH, "Package Version And Release Boundary")
    stop = _plain_section(SPEC_PATH, "Separate Authorization And Stop Conditions")

    for required in (
        "exact syntax, activation/migration mechanism",
        "logical/manifest/package identity",
        "case and Unicode normalization",
        "module-qualified references",
        "namespace/wildcard/",
        "side-effect/type-only/relation-only/package imports",
        "ProjectSemanticModel fact",
        "no grammar, generated parser, AST, project discovery/loading, namespace behavior, semantic resolution",
        "Runtime imports, dynamic loading, Python plugins, hooks, arbitrary code, network",
    ):
        assert required in non_goals, required
    for required in (
        "Package version remains 0.1.0",
        "changes no dependency, package metadata, lockfile, build, workflow, or release surface",
        "No tag, release, publish, upload, signing, or attestation is authorized",
        "does not stage, commit, push",
    ):
        assert required in release, required
    for required in (
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains unstarted",
        "Slices 7 through 11 remain pending",
        "No production module API is designed",
        "validation fails",
        "Slice 7 or Phase 52-55 work appears necessary",
    ):
        assert required in stop, required


def test_all_phase50_compatibility_allowlists_are_exact() -> None:
    for compatibility_path in COMPATIBILITY_TEST_PATHS:
        compatibility = _read(compatibility_path)
        assert (
            _string_set_assignment(compatibility, "ALLOWED_PHASE50_SLICE6_GATE2_PATHS")
            == ALLOWED_PHASE50_SLICE6_GATE2_PATHS
        ), compatibility_path
        assert (
            _string_set_assignment(compatibility, "ALLOWED_PHASE50_SLICE7_GATE2_PATHS")
            == ALLOWED_PHASE50_SLICE7_GATE2_PATHS
        ), compatibility_path
        assert (
            _string_set_assignment(compatibility, "ALLOWED_PHASE50_SLICE8_GATE2_PATHS")
            == ALLOWED_PHASE50_SLICE8_GATE2_PATHS
        ), compatibility_path


def test_protected_surfaces_version_tag_staging_and_dirty_set_are_locked() -> None:
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    assert project["version"] == "0.1.0"
    assert _git_output(["tag", "--points-at", "HEAD"]) == ""
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = _dirty_paths()
    phase54_slice9_gate2 = _phase54_slice9_gate2_paths()
    if dirty not in (
        phase54_slice9_gate2,
        set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS),
    ):
        for relative_path in PROTECTED_PATHS:
            assert _git_output(["diff", "--", relative_path]) == "", relative_path
    assert dirty in (
        set(),
        ALLOWED_PHASE50_SLICE6_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE7_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE9_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE10_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE11_GATE2_PATHS,
        phase54_slice9_gate2,
        set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS),
        set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS),
        set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS),
        set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS),
    )
    if dirty == set(PHASE54_SLICE11_PYTHON313_REPAIR_MODIFIED_PATHS):
        assert phase54_slice11_python313_repair_is_active()
    elif dirty == set(PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS):
        assert phase54_slice11_substantive_recovery_is_active()
    elif dirty == set(PHASE54_SLICE12_PR_CI_REPAIR_MODIFIED_PATHS):
        assert phase54_slice12_pr_ci_repair_is_active()
    elif dirty == set(PHASE54_SLICE12_MECHANICAL_REPAIR3_MODIFIED_PATHS):
        assert phase54_slice12_mechanical_repair3_is_active()
    elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS):
        assert phase54_slice12_product_repair3_is_active()
    elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS):
        assert phase54_slice12_product_repair10_is_active()
    elif dirty == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS):
        assert phase54_slice12_product_repair11_is_active()
    elif dirty == set(PHASE54_SLICE11_PR_CI_REPAIR_MODIFIED_PATHS):
        assert phase54_slice11_pr_ci_repair_is_active()


def test_plan_slice6_scope_and_exact_allowlist_are_locked() -> None:
    slice6 = _plain_section(PLAN_PATH, "Slice 6 Import / Module / Export Readiness")
    allowlist = _normalized_section(PLAN_PATH, "Slice 6 Gate 2 Allowlist")

    for required in (
        "Route D decision",
        "current flat project-global behavior unchanged",
        "private documentation-only candidate",
        "explicit named imports",
        "declarations are private by default",
        "No collision receives a semantic winner",
        "Phase 54 Import / Module / Export Readiness as an unstarted, separately authorized, readiness-only phase",
        "Slice 6 implements no compiler or runtime behavior",
    ):
        assert required in slice6, required
    assert "limited to exactly:" in allowlist
    assert len(ALLOWED_PHASE50_SLICE6_GATE2_PATHS) == 8
    for relative_path in ALLOWED_PHASE50_SLICE6_GATE2_PATHS:
        assert relative_path in allowlist, relative_path
    assert "No ninth repository path is approved" in allowlist
