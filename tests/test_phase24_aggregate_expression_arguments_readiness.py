from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-24-aggregate-function-expansion-ii.md"

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Decimal not null\n"
    "    quantity: Int not null\n"
    "    score: Float not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    customer_id: UUID not null\n"
    'source orders: Order is postgres.table("orders")\n'
)

LOCKED_BOUNDARY_SURFACES = {
    "semantic": (
        "src/pietto/semantic",
        20,
        "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "59c3921f21de398e06f6deca28f18871120bbf411110974c3df6ba7fa85970c4",
    ),
    "fixtures": (
        "tests/fixtures",
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        "tests/fixtures/golden",
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "4078b89d21126706746e07052ac8870a70f7275bd02dfc0433552f5edf06c082",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "63e99f989500f83686963fba853fed27d76bc5e0c0ac2e58827fb336b2bb044a",
    ),
    "pyproject": (
        "pyproject.toml",
        1,
        "cf5894a9cb7ef0399126a7d424da4e3958fc92d8e6bed295939a6e6bac469099",
    ),
    "uv_lock": (
        "uv.lock",
        1,
        "b48bb27656ff3344a95ba92347f45173904801cd8bdccfd2b55106549c445ac0",
    ),
    "github": (
        ".github",
        1,
        "129f96212b5025e66254b2485195977770cf7765bd8977215c6dfaefd9e6e5ae",
    ),
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "readme": (
        "README.md",
        1,
        "bb2abac2646218daa0d67157d40acda237b9a2072c0a2482a7cbc7249c57806c",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "6639d453d7b7ef3ebd926e72b2c05ec94c2018cc858968ea584d5bbd97750fce",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "aa0b2c3889c67b7c71c3deba8e2daa54297bf154c3922aed4c9a31b095a9ecc9",
    ),
}


def test_slice7_status_is_docs_static_audit_only() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 24 Slice 7 is complete as an aggregate expression arguments readiness audit",
        "It records the future design questions for aggregate expression arguments",
        "proves that `PIE-S2315` still guards aggregate expression arguments",
        "keeps implementation deferred to separate authorization",
        "Slice 7 changes no production behavior, semantic implementation, Semantic IR, IR model, SQL renderer, CLI behavior, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency, lockfile, package metadata, CI",
        "runtime/database behavior, connector execution, schema introspection",
        "public API, Decimal arithmetic, Decimal precision/scale modeling, casts",
        "generic DISTINCT syntax, `count(distinct field)`, aggregate modifier behavior",
    ):
        assert required in plan


def test_slice7_records_future_expression_argument_design_questions() -> None:
    plan = _normalized_plan()

    for required in (
        "Required future design questions before aggregate expression arguments can be implemented",
        "type inference for aggregate argument expressions",
        "nullability propagation from expression operands into aggregate results",
        "the allowed expression subset for aggregate arguments",
        "deterministic PostgreSQL/MySQL SQL rendering for expression arguments",
        "Decimal arithmetic policy, including whether Decimal operands are admitted",
        "scalar function arguments such as `count_distinct(lower(status))`",
        "expression aliasing and projection-alias visibility rules",
        "preserving the nested aggregate prohibition",
        "cross-dialect portability for expression semantics",
        "diagnostics, cascade suppression, and fail-closed malformed IR behavior",
    ):
        assert required in plan


def test_slice7_records_expression_arguments_as_deferred_behind_s2315() -> None:
    plan = _normalized_plan()

    for required in (
        "Aggregate expression arguments remain readiness/contract-only in Phase 24",
        "`sum(amount + tax)`",
        "`avg(amount + tax)`",
        "`min(date_expr)`",
        "`max(timestamp_expr)`",
        "`count_distinct(lower(status))`",
        "The current behavior remains locked",
        "`sum(amount + amount)` remains `PIE-S2315`",
        "`avg(amount + amount)` remains `PIE-S2315`",
        "`min(amount + amount)` remains `PIE-S2315`",
        "`max(amount + amount)` remains `PIE-S2315`",
    ):
        assert required in plan


def test_slice7_preserves_decimal_and_runtime_non_goals() -> None:
    plan = _normalized_plan()

    for required in (
        "direct-field Decimal aggregates from Slice 6 remain accepted",
        "Decimal arithmetic outside aggregate arguments is not enabled",
        "Decimal precision/scale modeling, casts, schema introspection, and runtime/database execution remain out of scope",
        "Slice 8: CLI/JSON/Output Hardening**: future tests/audit slice",
        "Slice 9: Completion Audit And Status Lock**: future audit/status slice",
    ):
        assert required in plan


@pytest.mark.parametrize(
    ("projection", "function_name"),
    [
        ("value = sum(amount + 1)", "sum"),
        ("value = avg(amount / amount)", "avg"),
        ("value = min(amount + amount)", "min"),
        ("value = max(amount + amount)", "max"),
        ("value = count_distinct(len(status))", "count_distinct"),
    ],
)
def test_aggregate_expression_arguments_still_fail_with_s2315(
    projection: str,
    function_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            f"Aggregate function {function_name} requires a direct field argument; "
            "expression arguments are deferred",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(avg(amount))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = sum(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around sum() is deferred",
            ),
        ),
        (
            "sum(amount)",
            ("PIE-S2313", "Aggregate sum() projection requires an explicit alias"),
        ),
    ],
)
def test_existing_invalid_aggregate_shapes_keep_existing_diagnostics(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def test_invalid_aggregate_context_still_fails_with_s2308() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    where sum(amount) > 0\n"
            "    select:\n"
            "        amount\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in where clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_direct_field_aggregate_vocabulary_remains_accepted() -> None:
    script = _parse(
        SOURCE_PREFIX + "table direct_aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        row_count = count()\n"
        "        known_amounts = count(amount)\n"
        "        unique_statuses = count_distinct(status)\n"
        "        total_quantity = sum(quantity)\n"
        "        average_quantity = avg(quantity)\n"
        "        total_score = sum(score)\n"
        "        average_score = avg(score)\n"
        "        smallest_quantity = min(quantity)\n"
        "        largest_score = max(score)\n"
        "        total_amount = sum(amount)\n"
        "        average_amount = avg(amount)\n"
        "        smallest_amount = min(amount)\n"
        "        largest_amount = max(amount)\n"
        "        first_order_date = min(order_date)\n"
        "        latest_created_at = max(created_at)\n"
    )
    relation = _relation(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["row_count"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["known_amounts"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["unique_statuses"], "Int", EffectiveNullability.NON_NULL
    )
    _assert_field(schema.fields["total_quantity"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_quantity"], "Float", EffectiveNullability.NULLABLE
    )
    _assert_field(schema.fields["total_score"], "Float", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_score"], "Float", EffectiveNullability.NULLABLE
    )
    _assert_field(
        schema.fields["smallest_quantity"], "Int", EffectiveNullability.NULLABLE
    )
    _assert_field(
        schema.fields["largest_score"], "Float", EffectiveNullability.NULLABLE
    )
    for name in (
        "total_amount",
        "average_amount",
        "smallest_amount",
        "largest_amount",
    ):
        _assert_field(schema.fields[name], "Decimal", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["first_order_date"], "Date", EffectiveNullability.NULLABLE
    )
    _assert_field(
        schema.fields["latest_created_at"], "Timestamp", EffectiveNullability.NULLABLE
    )


def test_slice7_boundary_surfaces_remain_post_slice6_hash_locked() -> None:
    for _name, (
        path_or_paths,
        expected_count,
        expected_hash,
    ) in LOCKED_BOUNDARY_SURFACES.items():
        paths = _paths(path_or_paths)

        assert len(paths) == expected_count
        assert _digest(paths) == expected_hash


def _read_plan() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized_plan() -> str:
    return " ".join(_read_plan().split())


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _paths(path_or_paths: str | tuple[str, ...]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, tuple):
        return tuple(REPO_ROOT / path for path in path_or_paths)

    path = REPO_ROOT / path_or_paths
    if path.is_file():
        return (path,)
    return tuple(
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and "__pycache__" not in item.parts
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix().encode()
        digest.update(relative_path + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
