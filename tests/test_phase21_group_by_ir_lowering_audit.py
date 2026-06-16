from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
IR_BUILDER_PATH = REPO_ROOT / "src/pietto/ir/builder.py"
IR_LOWERING_PATH = REPO_ROOT / "src/pietto/ir/lowering.py"
POSTGRES_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/relations.py"
MYSQL_RELATIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_relations.py"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"


def _plan() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized_plan() -> str:
    return " ".join(_plan().split())


def test_phase21_slice6_status_and_boundaries_are_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 21 Slice 6 is complete as IR group key lowering with SQL fail-closed guards",
        "It adds `RelationIR.group_keys: tuple[FieldRefIR, ...] = ()`",
        "lowers accepted unique grouped keys into source-ordered `FieldRefIR` values",
        "keeps `PIE-S2316` as an unconditional semantic error",
        "PostgreSQL and MySQL renderers now reject grouped IR and downstream-from-grouped IR through the existing `PIE-B1000` backend diagnostic path",
        "Slice 6 does not render SQL `GROUP BY`, add SQL goldens, add grouped `emit-sql` success, change CLI/JSON behavior",
        "Existing no-GROUP SQL bytes remain the compatibility baseline",
    ):
        assert required in plan


def test_relation_ir_group_keys_field_is_defaulted_and_field_ref_based() -> None:
    source = IR_MODEL_PATH.read_text(encoding="utf-8")

    assert "group_keys: tuple[FieldRefIR, ...] = ()" in source
    assert "GroupKeyIR" not in source


def test_group_key_lowering_uses_source_order_and_skips_invalid_precise_keys() -> None:
    builder = IR_BUILDER_PATH.read_text(encoding="utf-8")
    lowering = IR_LOWERING_PATH.read_text(encoding="utf-8")

    for required in (
        "group_keys = _lower_group_keys(",
        "clause = definition.group_by_clause",
        "group_keys: list[FieldRefIR] = []",
        "seen_identities: set[str] = set()",
        "if field is None:",
        "continue",
        "if identity in seen_identities:",
        "lower_group_key_ref(",
        "group_keys=group_keys",
    ):
        assert required in builder
    for required in (
        "def lower_group_key_ref(",
        "expression: NameExpr | DottedNameExpr",
        "field: RowField",
        "field_owner: SymbolId",
        "FieldId(owner=field_owner, name=field.name)",
        "value_type = lower_value_type(",
    ):
        assert required in lowering


def test_sql_backends_render_group_by_and_guard_malformed_grouped_ir() -> None:
    postgres = POSTGRES_RELATIONS_PATH.read_text(encoding="utf-8")
    mysql = MYSQL_RELATIONS_PATH.read_text(encoding="utf-8")

    assert "if relation.group_keys:" in postgres
    assert "_validate_grouped_relation(relation)" in postgres
    assert "def _render_group_key(key: FieldRefIR) -> str:" in postgres
    assert '"GROUP BY"' in postgres
    assert "PostgreSQL grouped ORDER BY is not supported" in postgres
    assert "PostgreSQL GROUP BY keys must be resolved fields" in postgres
    assert "PostgreSQL GROUP BY keys must be unique" in postgres
    assert "if upstream.group_keys:" not in postgres
    assert "PostgreSQL grouped relation SQL lowering is not implemented" not in postgres
    assert (
        "PostgreSQL relation input depends on unsupported grouped lowering"
        not in postgres
    )

    assert "if relation.group_keys:" in mysql
    assert "_validate_grouped_relation(relation)" in mysql
    assert "def _render_group_key(key: FieldRefIR) -> str:" in mysql
    assert '"GROUP BY"' in mysql
    assert "MySQL grouped ORDER BY is not supported" in mysql
    assert "MySQL GROUP BY keys must be resolved fields" in mysql
    assert "MySQL GROUP BY keys must be unique" in mysql
    assert "if upstream.group_keys:" not in mysql
    assert "MySQL grouped relation SQL lowering is not implemented" not in mysql
    assert "MySQL relation input depends on unsupported grouped lowering" not in mysql


def test_pie_s2316_semantic_gate_is_retired_noop() -> None:
    source = SEMANTIC_GROUP_BY_PATH.read_text(encoding="utf-8")

    for required in (
        'GROUP_BY_DEFERRED_CODE = "PIE-S2316"',
        "GROUP BY lowering gate is retired; valid GROUP BY lowers to SQL",
        "def check_group_by_deferred(script: Script) -> list[Diagnostic]:",
        "del script",
        "return []",
    ):
        assert required in source
    assert (
        "diagnostics.append("
        not in source.split(
            "def check_group_by_deferred(script: Script) -> list[Diagnostic]:",
            maxsplit=1,
        )[1].split("def project_grouped_schema(", maxsplit=1)[0]
    )


def test_slice6_keeps_sql_lowering_and_golden_work_out_of_scope() -> None:
    plan = _normalized_plan()

    for required in (
        "Slice 6 explicitly does not implement SQL `GROUP BY` lowering",
        "SQL goldens",
        "grouped SQL success",
        "grouped `order by`",
        "HAVING user syntax",
        "`satisfying`",
        "`filter`",
        "JOIN",
        "relationship-driven query behavior",
        "aggregate expression arguments",
        "Decimal aggregate semantics",
        "runtime/database execution",
    ):
        assert required in plan

    for forbidden in (
        "SQL GROUP BY lowering is complete",
        "grouped emit-sql success is implemented",
        "grouped `emit-sql` success path is implemented",
        "GROUP BY implementation is complete",
        "Phase 21 implements GROUP BY",
    ):
        assert forbidden not in plan


def test_slice7_sql_lowering_status_and_boundaries_are_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 21 Slice 7 is complete as PostgreSQL/MySQL SQL GROUP BY lowering and golden coverage",
        "Valid grouped relations no longer emit the unconditional `PIE-S2316` gate",
        "group keys render from `RelationIR.group_keys` in source order using the existing field rendering and identifier quoting rules",
        "malformed hand-built grouped IR still fails closed through backend `PIE-B1000` diagnostics",
        "downstream relations reading from grouped relations use the existing quoted relation name as input and do not inline, expand CTEs, or create subqueries",
    ):
        assert required in plan
