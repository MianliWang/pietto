from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"

REQUIRED_FEATURES = (
    "Aggregate expansion",
    "Numeric expression expansion",
    "DateTime/timezone/Time/Interval",
    "UUID",
    "Enum",
    "Decimal precision/scale",
    "Native DB type metadata",
    "DB pull/schema introspection",
    "Prisma bridge",
    "Project/multi-file",
    "Relationship/JOIN",
    "Relationship cardinality/grain/fanout diagnostics",
    "Semantic/domain annotations",
    "Explain/audit output",
    "LSP/playground",
    "Runtime/database execution",
    "Arrow/dataframe integration",
)

ALLOWED_BEFORE_V02_CATEGORIES = (
    "bug fixes only",
    "contracts/tests only",
    "readiness or narrow-MVP decision only",
    "Phase 30/31 stabilization only if explicitly approved",
    "implemented by Phase 41 for semantic validation and private carrier only",
    "no before v0.2",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice2_plan_status_and_register_link_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 29 Slice 2 is complete as deferred-feature register contract "
        "and static audit work only",
        "docs/spec/v02-deferred-feature-register-v1.md",
        "The register does not authorize implementation of any deferred feature",
        "Status: complete as deferred-feature register contract and static "
        "audit work only",
        "tests/test_phase29_v02_deferred_feature_register.py",
        "uv run pytest tests/test_phase29_v02_deferred_feature_register.py",
        "Document v0.2 deferred feature register",
    ):
        assert required in plan

    for planned_only in (
        "Slice 3: Aggregate Surface Freeze",
        "Slice 4: Core Type System Gap Matrix",
        "Slice 5: v0.2 Exit Criteria And Validation Strategy",
        "Slice 6: Completion Audit And Status Lock",
    ):
        assert planned_only in plan


def test_register_column_contract_and_allowed_categories_are_locked() -> None:
    register = _normalized(REGISTER_PATH)

    assert REGISTER_PATH.is_file()
    assert (
        "| Feature | Why deferred | Blocking prerequisites | Unfreeze condition | "
        "Target | Allowed before v0.2 | Explicit non-goals |"
    ) in register
    for category in ALLOWED_BEFORE_V02_CATEGORIES:
        assert category in register


def test_required_deferred_features_are_registered() -> None:
    register = _normalized(REGISTER_PATH)

    for feature in REQUIRED_FEATURES:
        assert f"| {feature} |" in register


def test_allowed_before_v02_decisions_are_locked() -> None:
    register = _normalized(REGISTER_PATH)

    expected_rows = {
        "Aggregate expansion": "bug fixes only",
        "Numeric expression expansion": "contracts/tests only",
        "DateTime/timezone/Time/Interval": "no before v0.2",
        "UUID": "readiness or narrow-MVP decision only",
        "Enum": "readiness or narrow-MVP decision only",
        "Decimal precision/scale": (
            "implemented by Phase 41 for semantic validation and private carrier only"
        ),
        "Native DB type metadata": "no before v0.2",
        "DB pull/schema introspection": "no before v0.2",
        "Prisma bridge": "no before v0.2",
        "Project/multi-file": "no before v0.2",
        "Relationship/JOIN": "no before v0.2",
        "Relationship cardinality/grain/fanout diagnostics": "no before v0.2",
        "Semantic/domain annotations": "no before v0.2",
        "Explain/audit output": "contracts/tests only",
        "LSP/playground": "no before v0.2",
        "Runtime/database execution": "no before v0.2",
        "Arrow/dataframe integration": "no before v0.2",
    }

    for feature, allowed_before_v02 in expected_rows.items():
        assert f"| {feature} |" in register
        row = next(
            line
            for line in _read(REGISTER_PATH).splitlines()
            if line.startswith(f"| {feature} |")
        )
        assert f"| {allowed_before_v02} |" in row


def test_blockers_unfreeze_targets_and_non_goals_are_locked() -> None:
    register = _normalized(REGISTER_PATH)

    for required in (
        "Phase 30/31 aggregate result, scalar type, and dialect matrix stabilization",
        "Phase 30 operator/comparison and Decimal contracts",
        "Phase 30 Date/Timestamp formalization",
        "Phase 31 UUID readiness or narrow-MVP decision",
        "Phase 31 enum readiness or lowering decision",
        "Phase 30 Decimal precision/scale contract",
        "Phase 41 Slices 2-6",
        "Phase 42 numeric/literal work",
        "schema-versioned public output contract",
        "Artifact v2/display contract",
        "Runtime threat model, connector auth policy, resource limits",
        "Project loader, path model, config model, cross-file semantics",
        "Relationship composition contract, JOIN SQL shape contract",
        "Relationship/JOIN model, grain model, and diagnostic contract",
        "Core type-system stabilization, annotation contract, and syntax approval",
        "v0.2 boundary, diagnostic model, output contract, and JSON/API decision",
        "v0.2 compiler stability, project/source model, and diagnostic transport",
        "Runtime threat model, connector auth, transaction policy",
        "Runtime/data model, Arrow dependency review",
        "v0.3+",
        "Phase 31 decision",
        "Phase 30/31",
        "post-v0.2",
        "v0.4+",
        "not v0.2",
    ):
        assert required in register


def test_register_hard_boundaries_do_not_authorize_implementation() -> None:
    register = _normalized(REGISTER_PATH)

    for required in (
        "This register records features that are outside the v0.2 stable "
        "single-file typed SQL authoring compiler boundary",
        "It does not authorize implementation",
        "JSON v2",
        "public MySQL API expansion",
        "runtime execution",
        "schema introspection",
        "DateTime primitives",
        "Currency/Money primitives",
        "semantic annotation syntax",
        "expand aggregate behavior",
        "No `DateTime`, timezone, `Time`, or `Interval` primitive",
        "Money and Currency are not primitive scalar types",
        "No Decimal literal typing, Int/Float/Decimal promotion matrix, "
        "Float/Decimal mixing, Decimal multiplication/division",
        "aggregate precision propagation",
        "SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output",
        "public JSON precision-scale fields",
        "metadata/explain precision-scale display",
        "non-Decimal type-argument policy",
        "No UUID functions, casts, literals, storage semantics, DDL, or SQL behavior",
        "No enum DDL, runtime mapping, SQL lowering, value validation changes",
        "No `pietto explain`, audit JSON, provenance output, CLI option, or JSON v2 output",
        "Phase 43 Slice 2 implements only direct `sum(let_name)` / `avg(let_name)` "
        "inline aggregate arguments",
        "Phase 43 Slice 3 implements only direct `count(let_name)` / "
        "`count_distinct(let_name)` inline aggregate arguments",
        "Phase 43 Slice 4 implements only direct `group by let_name` group keys",
        "expression/literal group keys, grouped let ordering, raw `satisfying` "
        "let-name behavior, and `limit let_name` behavior unfreeze only when a "
        "later implementation slice is explicitly approved",
    ):
        assert required in register

    for forbidden in (
        "Slice 2 implements all aggregate behavior",
        "Slice 3 implements all aggregate behavior",
        "Slice 3 implements grouped let keys",
        "Slice 3 implements broad count_distinct expression behavior",
        "Slice 4 implements all grouped let support",
        "Slice 4 implements expression group keys",
        "implementation authorized",
        "register authorizes",
        "DateTime primitive is allowed",
        "Currency primitive is allowed",
        "Money primitive is allowed",
        "JSON v2 is allowed",
        "public `emit_mysql_sql`",
    ):
        assert forbidden not in register
