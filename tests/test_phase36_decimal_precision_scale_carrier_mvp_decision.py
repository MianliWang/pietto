from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
DECIMAL_CONTRACT_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"

SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
SEMANTIC_ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
)


def _phase36_slice3_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice3_selects_exact_deferral_prerequisites_not_implementation() -> None:
    combined = _phase36_slice3_docs()

    for required in (
        "Phase 36 Slice 3 selects Option B: exact deferral prerequisites only",
        "Option B is selected",
        "deferred with exact prerequisites",
        "Slice 3 does not implement a carrier",
        "does not change source/compiler behavior",
        "does not change behavior",
        "Slice 3 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_option_a_private_carrier_skeleton_is_not_authorized() -> None:
    combined = _phase36_slice3_docs()

    for required in (
        "Option A: private internal carrier skeleton",
        "Not approved in Slice 3",
        "The private Decimal precision-scale carrier skeleton is not safely private yet",
        "`ResolvedType`",
        "`ValueType`",
        "`TypeRefIR`",
        "`SemanticMetadataType`",
        "metadata/explain output surfaces",
        "Existing Phase 30, Phase 31, and Phase 32 tests intentionally lock",
    ):
        assert required in combined, required

    for forbidden in (
        "Option A is selected",
        "Slice 3 implements a carrier",
        "Slice 3 authorizes a private carrier skeleton",
        "carrier skeleton is approved",
    ):
        assert forbidden not in combined, forbidden


def test_current_decimal_facts_remain_behavior_preserving() -> None:
    combined = _phase36_slice3_docs()

    for required in (
        "`Decimal` is a logical exact numeric scalar",
        "No precision/scale carrier exists",
        "`Decimal(12, 2)` generic `TypeExpr.arguments` do not create accepted precision/scale semantics",
        "Public outputs expose no precision/scale field",
        "`Decimal + Decimal` and `Decimal - Decimal` remain the current accepted scalar behavior",
        "Decimal multiplication remains unsupported/deferred",
        "Decimal division remains unsupported/deferred",
        "Mixed Decimal promotion remains unsupported/deferred",
        "Decimal literals remain unsupported/deferred",
        "Casts remain unsupported/deferred",
        "Decimal aggregate behavior remains unchanged",
    ):
        assert required in combined, required


def test_phase41_update_records_minimal_private_carrier_is_now_implemented() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "## Phase 41 Update",
        "This Phase 36 Slice 3 decision remains historical",
        "`Decimal(p,s)` semantic validation is implemented with `PIE-S2004`",
        "`DecimalPrecisionScale` is private to `pietto.semantic.model`",
        "`SemanticModel.decimal_precision_scales`",
        "`decimal_precision_scale_for(type_expr)` own the internal carrier surface",
        "safe alias-chain internal fact propagation is implemented",
        "IR, SQL, CLI JSON v1, Project JSON v2, explain output, and Semantic Metadata",
        "Artifact v1 remain precision-scale compatible",
        "Phase 41 still rejects public precision-scale fields",
        "metadata/explain precision-scale display",
        "aggregate precision propagation",
    ):
        assert required in spec, required


def test_no_precision_scale_carrier_exists_on_publicish_type_surfaces() -> None:
    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    metadata_model = _read(METADATA_MODEL_PATH)

    for required in (
        "class DecimalPrecisionScale:",
        "precision: int",
        "scale: int",
        "decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale]",
        "def decimal_precision_scale_for(",
    ):
        assert required in semantic_model, required

    for required in (
        "class ResolvedType:",
        "name: str",
        "kind: TypeKind",
        "definition: Node | None = None",
        "class ValueType:",
        "resolved_type: ResolvedType",
        "nullability: EffectiveNullability",
        "kind: ValueTypeKind = ValueTypeKind.KNOWN",
    ):
        assert required in semantic_model, required

    for forbidden in ("precision", "scale"):
        assert forbidden not in _class_body(semantic_model, "class ResolvedType:")
        assert forbidden not in _class_body(semantic_model, "class ValueType:")

    for required in (
        "class TypeRefIR:",
        "declared_name: str",
        "canonical_name: str",
        "kind: TypeKindIR",
        "canonical_kind: TypeKindIR",
        "nullability: NullabilityIR",
    ):
        assert required in ir_model, required
    for forbidden in ("precision", "scale"):
        assert forbidden not in _class_body(ir_model, "class TypeRefIR:")

    for required in (
        "class SemanticMetadataType:",
        "status: str",
        "name: str | None",
        "kind: str",
        "canonical_name: str | None",
        "canonical_kind: str",
        "nullability: str",
        "support_posture: str",
    ):
        assert required in metadata_model, required
    for forbidden in ("precision", "scale"):
        assert forbidden not in _class_body(
            metadata_model, "class SemanticMetadataType:"
        )


def test_decimal_type_arguments_have_phase41_validation_with_internal_carrier() -> None:
    decimal_contract = _normalized(DECIMAL_CONTRACT_PATH)
    analyzer = _read(SEMANTIC_ANALYZER_PATH)

    for required in (
        "`Decimal(12, 2)` may parse as a generic `TypeExpr` with arguments",
        "Future Decimal precision/scale work must be explicit",
    ):
        assert required in decimal_contract, required

    assert "type_expr.arguments" not in _function_body(
        analyzer,
        "def _resolve_type(",
    )
    decimal_validator = _function_body(
        analyzer,
        "def _decimal_precision_scale_fact(",
    )
    assert 'if type_expr.name != "Decimal":' in decimal_validator
    assert "arguments = type_expr.arguments" in decimal_validator
    assert "_DECIMAL_PRECISION_MAX = 38" in analyzer
    assert "PIE-S2004" in analyzer


def test_public_outputs_expose_no_precision_scale_fields() -> None:
    metadata_serializer = _read(METADATA_SERIALIZER_PATH)
    metadata_text = _read(METADATA_TEXT_PATH)
    cli_json = _read(CLI_JSON_PATH)

    for required in (
        '"status": type_ref.status',
        '"canonical_name": type_ref.canonical_name',
        '"support_posture": type_ref.support_posture',
    ):
        assert required in metadata_serializer, required

    assert "support={type_ref.support_posture}" in metadata_text
    assert '"schema_version": _SCHEMA_VERSION' in cli_json

    for output_source in (metadata_serializer, metadata_text, cli_json):
        for forbidden in (
            '"precision"',
            '"scale"',
            "precision_scale",
            "decimal_precision",
            "decimal_scale",
        ):
            assert forbidden not in output_source, forbidden


def test_future_carrier_prerequisites_are_listed() -> None:
    combined = _phase36_slice3_docs()

    for required in (
        "a private carrier ownership boundary",
        "the source of precision/scale facts",
        "unknown/missing/invalid precision/scale encoding",
        "propagation policy for fields, aliases, expressions, aggregates, and unknown facts",
        "public output compatibility policy",
        "Semantic Metadata Artifact v1 schema/output policy",
        "JSON v1 and Project JSON v2 compatibility policy",
        "SQL dialect policy without silent `DECIMAL(p, s)` or `NUMERIC(p, s)` promises",
        "diagnostic policy",
        "validation proving no accidental syntax, SQL, JSON, metadata, or arithmetic expansion",
    ):
        assert required in combined, required


def test_slice3_explicit_non_authorization_is_documented() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "carrier implementation",
        "source syntax changes",
        "Decimal precision/scale syntax semantics",
        "Decimal(precision, scale) validation",
        "Decimal literal support",
        "casts",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal promotion",
        "SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` guarantees",
        "CLI text changes",
        "CLI JSON v1 changes",
        "Project JSON v2 changes",
        "Semantic Metadata Artifact v1 schema or output changes",
        "public precision/scale fields",
        "metadata/explain output changes",
    ):
        assert required in spec, required


def test_forbidden_surfaces_are_not_modified_by_slice3() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()


def _class_body(source: str, marker: str) -> str:
    start = source.index(marker)
    next_class = source.find("\n\n@dataclass", start + len(marker))
    if next_class == -1:
        next_class = source.find("\n\nclass ", start + len(marker))
    if next_class == -1:
        return source[start:]
    return source[start:next_class]


def _function_body(source: str, marker: str) -> str:
    start = source.index(marker)
    next_function = source.find("\n\ndef ", start + len(marker))
    if next_function == -1:
        return source[start:]
    return source[start:next_function]
