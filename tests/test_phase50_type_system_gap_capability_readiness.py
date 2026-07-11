from __future__ import annotations

import ast
import re
import subprocess
import tomllib
from pathlib import Path
from typing import cast

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase50-type-system-gap-capability-readiness-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"

SLICE4_TITLE = "# Phase 50 Slice 4 Type-System Gap And Capability Readiness v1"
SLICE3_SHA = "7bd50022859a5e3d202c26d67bed1a723388048a"
SLICE3_SUBJECT = "Add Phase 50 aggregate grouped schema readiness"
SLICE3_CI_RUN_ID = "29082580976"

BUILTIN_TYPE_NAMES = (
    "Any",
    "Bool",
    "Bytes",
    "Date",
    "Decimal",
    "Float",
    "Int",
    "Json",
    "Text",
    "Timestamp",
    "UUID",
)

TYPE_KINDS = ("BUILTIN", "TYPE_ALIAS", "ENUM", "SHAPE", "UNKNOWN")
NULLABILITY_STATES = ("NON_NULL", "NULLABLE", "UNKNOWN")
INVENTORY_CLASSIFICATIONS = (
    "IMPLEMENTED_STABLE",
    "IMPLEMENTED_LIMITED",
    "PRIVATE_FOUNDATION",
    "READINESS_CONTRACT_ONLY",
    "EXPLICITLY_DEFERRED",
    "OUT_OF_SCOPE",
    "NOT_EVIDENCED",
)
PUBLIC_SUPPORT_POSTURES = (
    "current",
    "limited_frozen",
    "deferred_builtin",
    "metadata_only",
    "unknown",
)

CAPABILITY_DIMENSIONS = (
    "Identity and classification",
    "Declaration and resolution",
    "Literal construction",
    "Cast/coercion",
    "Projection/reference",
    "Null-check behavior",
    "Equality/comparison",
    "Ordering/grouping",
    "Arithmetic",
    "Scalar function",
    "Aggregate argument",
    "Aggregate result",
    "General nullability propagation",
    "Window readiness",
    "Private project representation",
    "IR representability",
    "Backend expression lowering",
    "Public metadata posture",
    "Native database mapping",
)

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Canonical Type Inventory",
    "Classification Vocabulary",
    "Layer-by-layer Support Matrix",
    "Core Scalar Types",
    "Temporal Types",
    "Decimal Precision And Scale",
    "UUID And Enum",
    "Any Bytes And Json",
    "Aliases Domains And Refinements",
    "Operator And Type-pair Capabilities",
    "Aggregate Type Capabilities",
    "Nullability Capabilities",
    "IR SQL And Backend Boundaries",
    "Native Database Mapping Boundary",
    "Private Capability Dimension Model",
    "Cross-phase Dependencies",
    "Bounded Phase 52 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)

ALLOWED_PHASE50_SLICE4_GATE2_PATHS = {
    "docs/plan/phase-50-semantic-readiness-consolidation.md",
    "docs/spec/phase50-type-system-gap-capability-readiness-v1.md",
    "tests/test_phase50_type_system_gap_capability_readiness.py",
    "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
}

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

COMPATIBILITY_TEST_PATHS = (
    REPO_ROOT
    / "tests/test_phase50_semantic_package_extension_capability_scope_lock.py",
    REPO_ROOT / "tests/test_phase50_post_v02_deferred_readiness_inventory.py",
    REPO_ROOT
    / "tests/test_phase50_aggregate_grouped_project_output_schema_readiness.py",
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


def _normalized_section(text: str, heading: str) -> str:
    return " ".join(_section(text, heading).split())


def _class_assignment_names(source: str, class_name: str) -> tuple[str, ...]:
    module = ast.parse(source)
    for node in module.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue

        names: list[str] = []
        for statement in node.body:
            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        names.append(target.id)
            elif isinstance(statement, ast.AnnAssign) and isinstance(
                statement.target, ast.Name
            ):
                names.append(statement.target.id)
        return tuple(names)

    raise AssertionError(f"class not found: {class_name}")


def _catalog_builtin_names() -> tuple[str, ...]:
    catalog = _read(CATALOG_PATH)
    match = re.search(
        r"BUILTIN_TYPE_NAMES = frozenset\(\s*\{(?P<body>.*?)\}\s*\)",
        catalog,
        flags=re.DOTALL,
    )
    assert match is not None
    return tuple(re.findall(r'"([A-Za-z]+)"', match.group("body")))


def test_slice4_artifacts_baseline_and_current_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    spec = _read(SPEC_PATH)
    plan = _normalized(PLAN_PATH)
    combined = f"{plan} {_normalized(SPEC_PATH)}"

    assert SLICE4_TITLE in spec
    for required in (
        SLICE3_SHA,
        SLICE3_SUBJECT,
        SLICE3_CI_RUN_ID,
        "CI / push",
        "completed/success",
        "exact `headSha` match",
    ):
        assert required in combined, required

    for required in (
        "Phase 50 Slice 1 **Roadmap Reconciliation And Strategic Scope Lock** completed",
        "Phase 50 Slice 2 **Post-v0.2 Deferred Inventory And Phase 50-60 Replan** completed",
        "Phase 50 Slice 3 **Aggregate / Grouped Project Output-Schema Readiness** completed",
        "Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed",
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "29097916311",
        "Phase 50 Slice 5 **Window-Function Readiness** completed",
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "29115612846",
        "Phase 50 Slice 6 **Import / Module / Export Readiness** completed",
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "29139545163",
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "29141663534",
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** is the current",
        "Slice 8 is not complete in Gate 2",
        "Slices 9 through 11 remain pending",
        "Phase 50 remains in progress",
        "Phases 52 through 57 remain unstarted",
        "Phase 53 remains `READINESS_CONTRACT_ONLY`",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
    ):
        assert required in plan, required

    for forbidden in (
        "Phase 50 is complete",
        "Phase 52 has started",
        "Phase 52 is started",
        "Phase 53 has started",
        "Phase 53 is started",
    ):
        assert forbidden not in combined, forbidden


def test_spec_section_order_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    offsets = [spec.index(f"## {section}") for section in REQUIRED_SPEC_SECTIONS]

    assert offsets == sorted(offsets)
    assert "Slice 4 implements no compiler or runtime behavior." in spec
    normalized = _normalized(SPEC_PATH)
    normalized_lower = normalized.lower()
    for required in (
        "docs/spec/static-audit-only readiness work",
        "Slice 4 is not complete before successful Gate 3",
        "Phase 52 remains unstarted",
        "Every implementation requires separate authorization",
        "No production capability API is designed",
    ):
        assert required in normalized, required
    assert "missing or conflicting capability evidence fails closed" in normalized_lower


def test_exact_builtin_inventory_and_nonbuiltin_kinds_are_locked() -> None:
    spec = _read(SPEC_PATH)
    inventory = _normalized_section(spec, "Canonical Type Inventory")
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)

    assert _catalog_builtin_names() == BUILTIN_TYPE_NAMES
    offsets = [inventory.index(f"`{name}`") for name in BUILTIN_TYPE_NAMES]
    assert offsets == sorted(offsets)
    assert "exactly 11 names" in inventory
    assert "`Enum` is not a builtin" in inventory

    for kind in TYPE_KINDS:
        assert f"    {kind} =" in semantic_model, kind
        assert f"    {kind} =" in ir_model, kind

    for required in (
        "Type aliases retain their declared identity and canonical expansion",
        "Shapes are schema/type definitions, not scalar builtin names",
        "`UNKNOWN` is a sentinel and non-concrete state",
        "`Null` is not a canonical scalar type",
        "DateTime, Time, and Interval are not current builtin names",
        "Money, Currency, domains, native database types",
    ):
        assert required in inventory, required


def test_classification_and_public_posture_vocabularies_remain_separate() -> None:
    classification = _normalized_section(_read(SPEC_PATH), "Classification Vocabulary")
    metadata_builder = _read(METADATA_BUILDER_PATH)

    for token in INVENTORY_CLASSIFICATIONS:
        assert classification.count(f"`{token}`") == 1, token
    for posture in PUBLIC_SUPPORT_POSTURES:
        assert f"`{posture}`" in classification, posture
        assert f'return "{posture}"' in metadata_builder, posture

    for required in (
        "inventory/readiness classifications only",
        "do not replace or reinterpret",
        "introduces no public classification schema",
    ):
        assert required in classification, required


def test_layered_core_and_temporal_boundaries_are_locked() -> None:
    spec = _read(SPEC_PATH)
    layered = _section(spec, "Layer-by-layer Support Matrix")
    core = _normalized_section(spec, "Core Scalar Types")
    temporal = _normalized_section(spec, "Temporal Types")

    for identity in (*BUILTIN_TYPE_NAMES, "Enum", "type alias", "shape", "unknown"):
        assert identity in layered, identity
    for layer in (
        "Resolution / declaration",
        "Literal",
        "Projection / reference",
        "Operator / scalar call",
        "Aggregate",
        "Semantic / IR",
        "Private project",
        "Public metadata",
        "Backend expression lowering",
        "Native mapping",
    ):
        assert layer in layered, layer

    catalog = _read(CATALOG_PATH)
    for signature in (
        'BuiltinFunction("lower", ("Text",), "Text")',
        'BuiltinFunction("trim", ("Text",), "Text")',
        'BuiltinFunction("len", ("Text",), "Int")',
        'BuiltinFunction("matches", ("Text", "Text"), "Bool")',
    ):
        assert signature in catalog, signature
    assert "Text concatenation is not implemented" in core

    for required in (
        "Date and Timestamp are current builtin identities",
        "DateTime is not a builtin or alias",
        "Time and Interval are unsupported/non-builtin",
        "no Date/Timestamp typed literal syntax",
        "temporal arithmetic",
        "timezone semantics",
        "timestamp precision model",
        "interval algebra",
        "native mapping contract",
        "does not authorize DateTime, Time, or Interval implementation",
    ):
        assert required in temporal, required


def test_decimal_logical_private_and_public_backend_boundaries_are_locked() -> None:
    decimal = _normalized_section(_read(SPEC_PATH), "Decimal Precision And Scale")
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    type_ref_ir = ir_model.split("class TypeRefIR:", maxsplit=1)[1].split(
        "\n\n", maxsplit=1
    )[0]

    for required in (
        "Current logical Decimal behavior",
        "Current private facts",
        "Absent or deferred guarantees",
        "precision range is `1..38`",
        "scale range is `0..precision`",
        "`PIE-S2004`",
        "private `DecimalPrecisionScale`",
        "direct Decimal field references only",
        "no computed-expression precision fusion",
        "no aggregate-result precision fusion",
        "no Float/Decimal promotion",
        "no SQL `DECIMAL(p,s)` guarantee",
        "no overflow or rounding formula",
    ):
        assert required in decimal, required

    assert "class DecimalPrecisionScale:" in semantic_model
    assert "precision: int" in semantic_model
    assert "scale: int" in semantic_model
    assert "precision" not in type_ref_ir
    assert "scale" not in type_ref_ir


def test_boundary_types_aliases_domains_and_refinements_are_locked() -> None:
    spec = _read(SPEC_PATH)
    uuid_enum = _normalized_section(spec, "UUID And Enum")
    boundary = _normalized_section(spec, "Any Bytes And Json")
    aliases = _normalized_section(spec, "Aliases Domains And Refinements")

    for required in (
        "UUID is a builtin identity",
        "`limited_frozen`",
        "direct count",
        "direct count_distinct",
        "Enum is a declaration-backed non-builtin",
        "`metadata_only`",
        "`count(Enum field)` fails closed with `PIE-S2314`",
        "no Enum member literals/references",
    ):
        assert required in uuid_enum, required

    for required in (
        "Any is a boundary/top-like logical identity, not runtime dynamic typing",
        "`count(Bytes field)`",
        "`count(Json field)`",
        "`deferred_builtin`",
        "no Bytes/Json literal",
        "No operation support is inferred from builtin membership",
    ):
        assert required in boundary, required

    for required in (
        "preserve declared and canonical identity",
        "`PIE-S2003`",
        "Canonical expansion does not automatically grant every operation",
        "Parsed `ensure` syntax is not evidence of a completed domain type system",
        "Money, Currency, units, user domains",
        "outside the current Phase 51-60 route",
        "designs no domain syntax or API",
    ):
        assert required in aliases, required


def test_operator_type_pair_and_scalar_function_model_is_locked() -> None:
    operator = _normalized_section(
        _read(SPEC_PATH), "Operator And Type-pair Capabilities"
    )

    for required in (
        "unary `+`, `-`",
        "binary `+`, `-`, `*`",
        "Int/Float current matrix",
        "Decimal/Decimal",
        "Decimal/Int or Int/Decimal",
        "`%`",
        "`/`",
        "`and`, `or`",
        "comparisons",
        "`between`",
        "`is null`, `is not null`",
        "`PIE-S2105`",
        "Result",
        "Nullability",
        "Context / dialect boundary",
        "Phase 52 relevance",
    ):
        assert required in operator, required

    for function_name in ("lower", "trim", "len", "matches"):
        assert f"| `{function_name}` |" in operator, function_name
    assert "equivalent universal boolean" in operator
    assert "Slice 4 widens no operator" in operator


def test_aggregate_type_and_nullability_matrices_are_locked() -> None:
    spec = _read(SPEC_PATH)
    aggregates = _section(spec, "Aggregate Type Capabilities")
    normalized_aggregates = " ".join(aggregates.split())
    nullability = _normalized_section(spec, "Nullability Capabilities")
    aggregate_source = _read(AGGREGATES_PATH)

    for required in (
        "| `count()` | no argument | Int | `NON_NULL` |",
        "| direct `count(field)` | Bool, Bytes, Date, Decimal, Float, Int, Json, Text, Timestamp, UUID | Int | `NON_NULL` |",
        "| bounded `count(expression)` | current field-bearing accepted typed expression | Int | `NON_NULL` |",
        "| direct `count_distinct` | Bool, Int, Float, Decimal, Text, Date, Timestamp, UUID | Int | `NON_NULL` |",
        "| `sum(Int)` |",
        "| `sum(Float)` |",
        "| `sum(Decimal)` |",
        "| `avg(Int/Float)` |",
        "| `avg(Decimal)` |",
        "| direct `min/max` | Int, Float, Decimal, Date, Timestamp | same canonical type | `NULLABLE` |",
    ):
        assert required in aggregates, required

    for required in (
        "`PIE-S2314`",
        "no aggregate Decimal precision/scale fact",
        "no whole-type `aggregate-capable` flag",
    ):
        assert required in normalized_aggregates, required

    for source_fact in (
        '("Int", "Float", "Decimal")',
        '("Int", "Float", "Decimal", "Date", "Timestamp")',
        '"Bool",\n            "Int",\n            "Float",\n            "Decimal",\n            "Text",\n            "Date",\n            "Timestamp",\n            "UUID",',
    ):
        assert source_fact in aggregate_source, source_fact

    for state in NULLABILITY_STATES:
        assert nullability.count(f"`{state}`") >= 1, state
    for required in (
        "Unknown type identity, unknown nullability, SQL three-valued-logic",
        "non-concrete project schema availability are distinct",
        "source fields preserve known nullability",
        "the null literal has no concrete canonical type fact",
        "Compile-time nullability is not runtime truth",
    ):
        assert required in nullability, required

    project_model = _read(PROJECT_MODEL_PATH)
    assert (
        _class_assignment_names(project_model, "ProjectRowFieldNullability")
        == NULLABILITY_STATES
    )


def test_ir_native_capability_dimensions_and_phase52_handoff_are_locked() -> None:
    spec = _read(SPEC_PATH)
    ir_boundary = _normalized_section(spec, "IR SQL And Backend Boundaries")
    native = _normalized_section(spec, "Native Database Mapping Boundary")
    dimensions = _normalized_section(spec, "Private Capability Dimension Model")
    dependencies = _normalized_section(spec, "Cross-phase Dependencies")
    handoff = _normalized_section(spec, "Bounded Phase 52 Handoff")

    for required in (
        "`TypeRefIR` carries declared/canonical identity and nullability",
        "no Decimal precision/scale",
        "independent dimensions",
        "expression-specific",
        "emits no DDL/type catalog",
        "Project JSON v2",
        "no Slice 4 field or vocabulary change",
    ):
        assert required in ir_boundary, required

    for required in (
        "No complete physical/native type table exists",
        "No schema introspection",
        "`db pull`",
        "driver conversion",
        "storage precision",
        "extension discovery",
        "outside the current Phase 51-60 route",
    ):
        assert required in native, required

    offsets = [
        dimensions.index(f"{index}. {name}")
        for index, name in enumerate(CAPABILITY_DIMENSIONS, start=1)
    ]
    assert offsets == sorted(offsets)
    assert "exactly these 19 orthogonal" in dimensions
    for required in (
        "Slice 4 adds no production carrier",
        "optional right-hand type",
        "optional dialect/extension overlay",
        "fail-closed reason",
        "Missing or conflicting capability evidence fails closed",
        "No public enum, JSON schema, manifest field, or Python API",
    ):
        assert required in dimensions, required

    for phase in (51, 53, 55, 56, 57, 58, 59, 60):
        assert f"Phase {phase}" in dependencies
    assert "None of these dependencies starts a phase" in dependencies

    for required in (
        "Phase 52 — Core Type-System Capability Foundation",
        "Phase 52 remains unstarted",
        "private, immutable, deterministic, current-behavior-only capability facts",
        "exact 11 builtins",
        "fail-closed missing capability lookup",
        "no acceptance/rejection change",
        "no DateTime/Time/Interval implementation",
        "no Decimal fusion/formula",
        "does not finalize Phase 52 implementation slices",
    ):
        assert required in handoff, required


def test_compatibility_guards_protected_surfaces_version_and_dirty_set_are_locked() -> (
    None
):
    pyproject = tomllib.loads(_read(PYPROJECT_PATH))
    project = cast(dict[str, object], pyproject["project"])

    for compatibility_path in COMPATIBILITY_TEST_PATHS:
        compatibility = _read(compatibility_path)
        assert "ALLOWED_PHASE50_SLICE4_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE5_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE6_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE7_GATE2_PATHS" in compatibility
        assert "ALLOWED_PHASE50_SLICE8_GATE2_PATHS" in compatibility
        for relative_path in ALLOWED_PHASE50_SLICE4_GATE2_PATHS:
            assert f'"{relative_path}"' in compatibility, (
                compatibility_path,
                relative_path,
            )
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
        ALLOWED_PHASE50_SLICE4_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE5_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE6_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE7_GATE2_PATHS,
        ALLOWED_PHASE50_SLICE8_GATE2_PATHS,
    )
