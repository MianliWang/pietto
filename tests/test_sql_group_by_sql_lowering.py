from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import OrderDirectionIR, OrderItemIR, StaticValue
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
POSTGRES_INPUT = Path("tests/fixtures/phase21/postgres_group_by_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase21/mysql_group_by_aggregate.pietto")
POSTGRES_GOLDEN = "emit_sql_group_by_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_group_by_aggregate.sql"

SPAN = SourceSpan(
    path="phase21-group-by-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
TEXT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter"),
    [
        (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql),
        (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql),
    ],
)
def test_direct_group_by_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == "revenue_by_status"
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_text_group_by_sql_matches_reviewed_golden(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_group_by_sql_success_preserves_v1_shape(
    input_path: Path,
    dialect: str,
    golden_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert set(result) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "revenue_by_status",
            "sql": _golden_sql(golden_name),
        }
    ]


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name"),
    [
        (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN),
        (MYSQL_INPUT, "mysql", MYSQL_GOLDEN),
    ],
)
def test_cli_json_group_by_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-group-by.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["sql"] == _golden_sql(golden_name)
    assert output_path.read_bytes() == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect"),
    [
        (POSTGRES_INPUT, "postgres"),
        (MYSQL_INPUT, "mysql"),
    ],
)
def test_cli_check_succeeds_for_valid_grouped_relation(
    input_path: Path,
    dialect: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del dialect
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", str(input_path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {input_path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("body", "expected_codes"),
    [
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        customer_id\n"
            "        total = count()\n",
            ["PIE-S2318"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        label = lower(status)\n"
            "        total = count()\n",
            ["PIE-S2319"],
        ),
        (
            "    group by:\n        status\n    select:\n        status\n",
            ["PIE-S2320"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        sum(amount) desc\n",
            ["PIE-S2321"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "        orders.status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            ["PIE-S2317"],
        ),
        (
            "    group by:\n"
            "        missing\n"
            "    select:\n"
            "        missing\n"
            "        total = count()\n",
            ["PIE-S2102"],
        ),
        (
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        revenue = sum(1)\n",
            ["PIE-S2315"],
        ),
    ],
)
def test_invalid_grouped_relations_fail_semantically_before_sql(
    body: str,
    expected_codes: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "invalid-grouped.pietto"
    path.write_text(_invalid_grouped_source(body), encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == expected_codes
    assert "PIE-S2316" not in codes
    assert "PIE-B1000" not in codes
    assert result["artifacts"] == []


@pytest.mark.parametrize(
    ("input_path", "emitter"),
    [
        (POSTGRES_INPUT, emit_postgres_sql),
        (MYSQL_INPUT, emit_mysql_sql),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "unresolved_group_key",
        "non_field_group_key",
        "duplicate_group_key",
        "grouped_order_by",
        "unsupported_aggregate",
        "non_grouped_projection",
    ],
)
def test_malformed_grouped_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir, "revenue_by_status")
    bad_relation = _malformed_grouped_relation(relation, case)
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_from"),
    [
        ("postgres.table", emit_postgres_sql, 'FROM "grouped_orders"'),
        ("mysql.table", emit_mysql_sql, "FROM `grouped_orders`"),
    ],
)
def test_downstream_from_grouped_relation_defines_it_as_a_cte(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_from: str,
) -> None:
    result = emitter(_compile_source(_grouped_chain_source(connector)))

    assert result.diagnostics == ()
    assert [artifact.name for artifact in result.artifacts] == [
        "grouped_orders",
        "downstream",
    ]
    downstream_sql = result.artifacts[1].sql
    assert downstream_sql.endswith(expected_from)
    assert downstream_sql.startswith(
        f"WITH {expected_from.removeprefix('FROM ')} AS (\n"
        f"{result.artifacts[0].sql}\n)\nSELECT\n"
    )
    assert downstream_sql.count("SELECT") == 2
    assert downstream_sql.count("GROUP BY") == 1


def test_postgres_group_keys_render_in_ir_source_order_with_qualified_alias() -> None:
    result = emit_postgres_sql(
        _compile_source(
            "shape Order:\n"
            "    status: Text\n"
            "    region: Text | None\n"
            'source orders: Order = postgres.table("orders")\n'
            "table grouped_orders:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "        orders.region\n"
            "    select:\n"
            "        status\n"
            "        bucket = orders.region\n"
            "        total = count()\n"
            "    limit 10\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "status" AS "status",\n'
        '    "orders"."region" AS "bucket",\n'
        '    COUNT(*) AS "total"\n'
        'FROM "orders" AS "orders"\n'
        "GROUP BY\n"
        '    "status",\n'
        '    "orders"."region"\n'
        "LIMIT 10"
    )


_DIALECTS = (
    ("postgres.table", emit_postgres_sql, "PostgreSQL"),
    ("mysql.table", emit_mysql_sql, "MySQL"),
)


@pytest.mark.parametrize(("connector", "emitter", "target"), _DIALECTS)
def test_relation_over_a_source_without_a_shape_counting_its_rows_fails_closed(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    target: str,
) -> None:
    result = emitter(
        _compile_source(
            f'source items = {connector}("shop.items")\n'
            "query total:\n"
            "    from items\n"
            "    select:\n"
            "        n = count()\n"
            "    limit 1\n"
            "table kinds:\n"
            "    from items\n"
            "    group by:\n"
            "        kind\n"
            "        items.shop\n"
            "    select:\n"
            "        kind\n"
            "        n = count()\n"
            "    having:\n"
            "        n > 1 and n < 10\n"
            "query per_kind:\n"
            "    from kinds\n"
            "    group by kind\n"
            "    select:\n"
            "        k = kinds.kind\n"
            "        c = count()\n"
        )
    )

    assert result.artifacts == ()
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            f"{target} SQL emission is not implemented for RelationIR: {name}. "
            + reason,
            line,
            1,
        )
        for name, reason, line in (
            ("total", f"Unsupported {target} function identity: count", 2),
            ("kinds", f"{target} result predicate requires a known Bool type", 7),
            ("per_kind", f"Unsupported {target} function identity: count", 17),
        )
    ]


@pytest.mark.parametrize(("connector", "emitter", "target"), _DIALECTS)
@pytest.mark.parametrize("grouped", [False, True])
def test_reader_of_unknown_count_output_does_not_enable_aggregate_emission(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    target: str,
    grouped: bool,
) -> None:
    result = emitter(
        _compile_source(
            f'source items = {connector}("shop.items")\n'
            "query q:\n    from items\n"
            + ("    group by kind\n" if grouped else "")
            + "    select:\n        n = count()\n"
            "query r:\n    from q\n    where n\n"
            "    select:\n        m = len(n)\n"
        )
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        # r defines q, the query it reads, as a CTE, so q's refusal is r's too.
        (
            "PIE-B1000",
            f"{target} SQL emission is not implemented for RelationIR: {name}. "
            f"Unsupported {target} function identity: count",
            line,
            1,
        )
        for name, line in (("q", 2), ("r", 7 if grouped else 6))
    ]
    assert result.artifacts == ()


@pytest.mark.parametrize(("connector", "emitter", "target"), _DIALECTS)
def test_relation_over_a_source_without_a_shape_reading_its_fields_fails_as_before(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    target: str,
) -> None:
    result = emitter(
        _compile_source(
            f'source items = {connector}("shop.items")\n'
            "def f(v: Text) -> Int: return len(v)\n"
            "query a:\n"
            "    from items\n"
            "    where f(x) > 1\n"
            "    select:\n"
            "        n = count()\n"
            "query b:\n"
            "    from items\n"
            "    let x = 1\n"
            "    where len(items.x) > x\n"
            "    select:\n"
            "        n = count(items.x + 1)\n"
            "query q:\n"
            "    from items\n"
            "    select:\n"
            "        o3 = sum(y - 2)\n"
            "query r:\n"
            "    from q\n"
            "    select:\n"
            "        k = count(len(o3))\n"
            "query counted:\n"
            "    from items\n"
            "    group by kind\n"
            "    select:\n"
            "        kind\n"
            "        c = count(x)\n"
            "        s = sum(x)\n"
            "query ok:\n"
            "    from items\n"
            "    group by kind\n"
            "    select:\n"
            "        kind\n"
            "        n = count()\n"
        )
    )

    # Check passes; all aggregates retain the original emission refusal.
    def refused(name: str, function: str, line: int) -> tuple[str, str, int, int]:
        return (
            "PIE-B1000",
            f"{target} SQL emission is not implemented for RelationIR: {name}. "
            f"Unsupported {target} function identity: {function}",
            line,
            1,
        )

    assert [
        (
            diagnostic.code,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in result.diagnostics
    ] == [
        refused("a", "count", 3),
        refused("b", "count", 8),
        refused("q", "sum", 14),
        refused("r", "count", 18),
        refused("counted", "count", 22),
        refused("ok", "count", 29),
    ]
    assert result.artifacts == ()


def _compile(path: Path) -> ScriptIR:
    return _compile_path(REPO_ROOT / path)


def _compile_path(path: Path) -> ScriptIR:
    parse_result = parse_file(path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _compile_source(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="phase21-group-by-sql.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    # As the CLI does: the script with each `def` call inlined.
    ir_result = build_ir(
        semantic_result.script or parse_result.ast, semantic_result.model
    )
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _malformed_grouped_relation(relation: RelationIR, case: str) -> RelationIR:
    if case == "unresolved_group_key":
        return replace(
            relation,
            group_keys=(replace(relation.group_keys[0], field=None),),
        )
    if case == "non_field_group_key":
        return replace(
            relation,
            group_keys=cast(tuple[FieldRefIR, ...], (_literal(1),)),
        )
    if case == "duplicate_group_key":
        return replace(
            relation,
            group_keys=(relation.group_keys[0], relation.group_keys[0]),
        )
    if case == "grouped_order_by":
        return replace(
            relation,
            order_by=(
                OrderItemIR(
                    expression=_field("customer_id", TEXT_NON_NULL),
                    direction=OrderDirectionIR.ASC,
                    span=SPAN,
                ),
            ),
        )
    if case == "unsupported_aggregate":
        projection = relation.projections[2]
        assert isinstance(projection.expression, AggregateCallIR)
        return replace(
            relation,
            projections=(
                *relation.projections[:2],
                replace(
                    projection,
                    expression=replace(projection.expression, function="median"),
                ),
            ),
        )
    if case == "non_grouped_projection":
        projection = relation.projections[0]
        return replace(
            relation,
            projections=(
                replace(
                    projection,
                    name="customer_id",
                    expression=_field("customer_id", TEXT_NON_NULL),
                ),
                *relation.projections[1:],
            ),
        )
    raise AssertionError(f"Unknown malformed grouped IR case: {case}")


def _literal(value: StaticValue) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _invalid_grouped_source(body: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text\n"
        "    customer_id: Text\n"
        "    amount: Int\n"
        'source orders: Order = postgres.table("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        f"{body}"
    )


def _grouped_chain_source(connector: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text\n"
        "    amount: Int\n"
        f'source orders: Order = {connector}("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "query downstream:\n"
        "    from grouped_orders\n"
        "    select:\n"
        "        status\n"
        "        total\n"
    )


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_sql(name: str) -> str:
    """The SQL of a one-artifact golden, without its `--` name line and `;`."""

    return _golden_text(name).split("\n", 1)[1].removesuffix(";\n")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    """The artifacts as `emit-sql` text prints them: named, `;`-terminated."""

    return (
        "\n\n".join(f"-- {item.name}\n{item.sql};" for item in result.artifacts) + "\n"
    ).encode("utf-8")


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return cast(dict[str, object], json.loads(captured.out))
