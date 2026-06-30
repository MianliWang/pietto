from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-metadata-carrier-readiness-v1.md"
)

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


def _phase36_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_phase36_slice1_boundary_and_handoff_are_documented() -> None:
    combined = _phase36_docs()

    for required in (
        "Phase 36 Slice 1 is Candidate Decision And Type Expansion Boundary",
        "docs/spec/static-audit only",
        "implements no behavior change",
        "baseline HEAD: `2777b7f07908764f62e12d60cecaadd57cb08671`",
        "baseline commit: `Complete Phase 35 developer experience pipeline`",
        "latest completed phase: Phase 35 Developer Experience And Delivery Pipeline MVP",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation occurred",
    ):
        assert required in combined, required


def test_decimal_precision_scale_readiness_candidate_is_selected() -> None:
    combined = _phase36_docs()

    for required in (
        "Decimal precision-scale metadata carrier readiness/spec",
        "Chosen for Slice 1",
        "readiness/spec only",
        "no Decimal precision/scale carrier currently exists",
        "future Decimal precision/scale metadata carrier",
        "metadata first",
        "must not silently widen Decimal arithmetic",
    ):
        assert required in combined, required


def test_slice1_does_not_authorize_carrier_or_behavior_implementation() -> None:
    combined = _phase36_docs()

    for required in (
        "does not implement a carrier",
        "does not change source implementation",
        "does not change source/compiler behavior",
        "does not change Semantic Metadata Artifact v1 schema or output",
        "does not add Decimal precision/scale syntax semantics",
        "Decimal precision/scale carrier fields in semantic models",
        "Decimal precision/scale carrier fields in Semantic IR",
        "precision/scale propagation or validation",
        "SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` guarantees",
        "Decimal literal syntax",
        "casts",
        "Decimal multiplication or division expansion",
        "mixed Decimal/Int or Decimal/Float promotion",
        "Money or Currency primitives",
        "semantic/domain annotation syntax",
    ):
        assert required in combined, required

    for forbidden in (
        "Slice 1 implements a Decimal precision-scale carrier",
        "Slice 1 changes Decimal behavior",
        "Slice 1 changes SQL lowering",
        "Slice 1 changes JSON v1",
        "Slice 1 changes Semantic Metadata Artifact v1",
    ):
        assert forbidden not in combined, forbidden


def test_current_decimal_carrier_absence_is_grounded_in_existing_surfaces() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`ResolvedType` carries `name`, `kind`, and optional `definition`; it has no precision or scale fields",
        "`ValueType` carries resolved type, nullability, and known/unknown status; it has no precision or scale fields",
        "`TypeRefIR` carries declared/canonical type identity and nullability; it has no precision or scale fields",
        "Semantic Metadata Artifact v1 type objects expose type posture and `support_posture`; they have no precision or scale fields",
        "`Decimal(12, 2)` do not create accepted precision/scale semantics today",
    ):
        assert required in spec, required


def test_other_phase36_candidates_remain_deferred_or_behavior_adjacent() -> None:
    combined = _phase36_docs()

    for required in (
        "UUID remains limited/frozen readiness",
        "Enum remains metadata readiness",
        "DateTime, Time, Interval, timezone, and temporal arithmetic remain deferred",
        "Bytes and Json remain deferred behavior built-ins",
        "Any remains a boundary/top type",
        "Native DB type metadata remains deferred",
        "Money/Currency and semantic/domain annotations remain deferred",
        "Scalar/operator matrix changes remain outside Slice 1",
    ):
        assert required in combined, required


def test_status_housekeeping_is_deferred_to_later_slice() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "does not update `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
        "global status housekeeping remains future dedicated work",
    ):
        assert required in plan, required


def test_forbidden_surfaces_are_not_modified_by_slice1() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_file_is_not_part_of_slice1() -> None:
    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")
    assert "pyproject.toml" in FORBIDDEN_DIFF_PATHS
