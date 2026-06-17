from __future__ import annotations

import importlib.util
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ExpressionIR,
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
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts" / "check_goldens.py"

POSTGRES_INPUT = Path("tests/fixtures/phase22/postgres_min_max_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase22/mysql_min_max_aggregate.pietto")
POSTGRES_GROUPED_INPUT = Path(
    "tests/fixtures/phase22/postgres_grouped_min_max_aggregate.pietto"
)
MYSQL_GROUPED_INPUT = Path(
    "tests/fixtures/phase22/mysql_grouped_min_max_aggregate.pietto"
)
POSTGRES_GOLDEN = "emit_sql_min_max_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_min_max_aggregate.sql"
POSTGRES_GROUPED_GOLDEN = "emit_sql_grouped_min_max_aggregate.sql"
MYSQL_GROUPED_GOLDEN = "emit_mysql_grouped_min_max_aggregate.sql"

MIN_MAX_CLI_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN, "order_extremes"),
    (MYSQL_INPUT, "mysql", MYSQL_GOLDEN, "order_extremes"),
    (
        POSTGRES_GROUPED_INPUT,
        "postgres",
        POSTGRES_GROUPED_GOLDEN,
        "order_extremes_by_status",
    ),
    (
        MYSQL_GROUPED_INPUT,
        "mysql",
        MYSQL_GROUPED_GOLDEN,
        "order_extremes_by_status",
    ),
)

HISTORICAL_SQL_CASES: tuple[tuple[Path, str, Callable[[ScriptIR], SqlResult]], ...] = (
    (
        Path("tests/fixtures/phase19/postgres_count_aggregate.pietto"),
        "emit_sql_count_aggregate.sql",
        emit_postgres_sql,
    ),
    (
        Path("tests/fixtures/phase19/mysql_count_aggregate.pietto"),
        "emit_mysql_count_aggregate.sql",
        emit_mysql_sql,
    ),
    (
        Path("tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto"),
        "emit_sql_sum_avg_aggregate.sql",
        emit_postgres_sql,
    ),
    (
        Path("tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto"),
        "emit_mysql_sum_avg_aggregate.sql",
        emit_mysql_sql,
    ),
)

SPAN = SourceSpan(
    path="phase22-min-max-sql.pietto",
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
INT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
FLOAT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
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
TEXT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter", "artifact_name"),
    [
        (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql, "order_extremes"),
        (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql, "order_extremes"),
        (
            POSTGRES_GROUPED_INPUT,
            POSTGRES_GROUPED_GOLDEN,
            emit_postgres_sql,
            "order_extremes_by_status",
        ),
        (
            MYSQL_GROUPED_INPUT,
            MYSQL_GROUPED_GOLDEN,
            emit_mysql_sql,
            "order_extremes_by_status",
        ),
    ],
)
def test_direct_backend_min_max_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
    artifact_name: str,
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == artifact_name
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    MIN_MAX_CLI_CASES,
)
def test_cli_text_min_max_sql_matches_reviewed_golden(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del artifact_name
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    MIN_MAX_CLI_CASES,
)
def test_cli_json_min_max_sql_success_preserves_v1_shape(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
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
    assert result["path"] == input_path.as_posix()
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    sql = cast(str, artifacts[0]["sql"])
    assert "MIN" in sql
    assert "MAX" in sql


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    MIN_MAX_CLI_CASES,
)
def test_cli_json_min_max_sql_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-{artifact_name}.sql"
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
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["name"] == artifact_name
    assert artifacts[0]["sql"] == _golden_text(golden_name).removesuffix("\n")
    assert output_path.read_bytes() == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("golden_name", "expected_fragments"),
    [
        (
            POSTGRES_GOLDEN,
            (
                'MIN("amount") AS "smallest_amount"',
                'MAX("score") AS "highest_score"',
                'MIN("orders"."order_date") AS "first_order_date"',
                'MAX("orders"."created_at") AS "latest_created_at"',
            ),
        ),
        (
            MYSQL_GOLDEN,
            (
                "MIN(`amount`) AS `smallest_amount`",
                "MAX(`score`) AS `highest_score`",
                "MIN(`orders`.`order_date`) AS `first_order_date`",
                "MAX(`orders`.`created_at`) AS `latest_created_at`",
            ),
        ),
        (
            POSTGRES_GROUPED_GOLDEN,
            (
                'MIN("amount") AS "smallest_amount"',
                'MAX("created_at") AS "latest_created_at"',
                "GROUP BY",
            ),
        ),
        (
            MYSQL_GROUPED_GOLDEN,
            (
                "MIN(`amount`) AS `smallest_amount`",
                "MAX(`created_at`) AS `latest_created_at`",
                "GROUP BY",
            ),
        ),
    ],
)
def test_min_max_goldens_lock_extrema_function_and_qualification_shape(
    golden_name: str,
    expected_fragments: tuple[str, ...],
) -> None:
    sql = _golden_text(golden_name)

    for fragment in expected_fragments:
        assert fragment in sql


@pytest.mark.parametrize(("input_path", "golden_name", "emitter"), HISTORICAL_SQL_CASES)
def test_historical_count_sum_avg_sql_goldens_remain_byte_stable(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("dialect", "connector"),
    [
        ("postgres", "postgres.table"),
        ("mysql", "mysql.table"),
    ],
)
@pytest.mark.parametrize(
    ("case_name", "select_body", "expected_code"),
    [
        ("unsupported_type", "        value = max(status)\n", "PIE-S2314"),
        (
            "expression_argument",
            "        value = min(amount + amount)\n",
            "PIE-S2315",
        ),
    ],
)
def test_invalid_min_max_emit_sql_json_output_fails_before_sql_without_writing(
    dialect: str,
    connector: str,
    case_name: str,
    select_body: str,
    expected_code: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / f"{dialect}-{case_name}.pietto"
    output_path = tmp_path / f"{dialect}-{case_name}.sql"
    output_path.write_text("existing SQL\n", encoding="utf-8")
    source_path.write_text(
        _invalid_min_max_source(connector, select_body),
        encoding="utf-8",
    )
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "existing SQL\n"
    assert codes == [expected_code]
    assert expected_code.startswith("PIE-S")
    assert "PIE-B1000" not in codes


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
        "unsupported_function",
        "wrong_arity",
        "non_field_argument",
        "unresolved_field_argument",
        "unsupported_type",
        "malformed_result_type",
        "malformed_result_nullability",
    ],
)
def test_malformed_hand_built_min_max_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir)
    projection = relation.projections[0]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_aggregate(case)),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert result.diagnostics[0].severity is Severity.ERROR


def test_phase22_min_max_goldens_are_registered_and_audited() -> None:
    goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(goldens, "SQL_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(goldens, "FIXTURE_INPUTS"),
    )
    reference_tests = cast(tuple[Path, ...], getattr(goldens, "REFERENCE_TESTS"))
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(goldens, "audit"))

    assert {
        POSTGRES_GOLDEN,
        MYSQL_GOLDEN,
        POSTGRES_GROUPED_GOLDEN,
        MYSQL_GROUPED_GOLDEN,
    } <= sql_fixtures
    assert fixture_inputs[POSTGRES_GOLDEN] == (POSTGRES_INPUT.as_posix(),)
    assert fixture_inputs[MYSQL_GOLDEN] == (MYSQL_INPUT.as_posix(),)
    assert fixture_inputs[POSTGRES_GROUPED_GOLDEN] == (
        POSTGRES_GROUPED_INPUT.as_posix(),
    )
    assert fixture_inputs[MYSQL_GROUPED_GOLDEN] == (MYSQL_GROUPED_INPUT.as_posix(),)
    assert Path("tests/test_phase22_min_max_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()


def _compile(path: Path) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
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


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _malformed_aggregate(case: str) -> AggregateCallIR:
    if case == "unsupported_function":
        return _aggregate("median", INT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "wrong_arity":
        return _aggregate("min", INT_NULLABLE)
    if case == "non_field_argument":
        return _aggregate("min", INT_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "unresolved_field_argument":
        return _aggregate(
            "min",
            INT_NULLABLE,
            _field("amount", INT_NON_NULL, resolved=False),
        )
    if case == "unsupported_type":
        return _aggregate("max", TEXT_NULLABLE, _field("status", TEXT_NON_NULL))
    if case == "malformed_result_type":
        return _aggregate("min", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
    if case == "malformed_result_nullability":
        return _aggregate("max", INT_NON_NULL, _field("amount", INT_NON_NULL))
    raise AssertionError(f"Unknown malformed aggregate case: {case}")


def _aggregate(
    function: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> AggregateCallIR:
    return AggregateCallIR(
        span=SPAN,
        value_type=value_type,
        function=function,
        arguments=arguments,
    )


def _field(
    name: str,
    value_type: TypeRefIR,
    *,
    resolved: bool = True,
) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name) if resolved else None,
    )


def _literal(value: StaticValue, value_type: TypeRefIR) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


def _invalid_min_max_source(connector: str, select_body: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int not null\n"
        f'source orders: Order is {connector}("orders")\n'
        "table order_extremes:\n"
        "    from orders\n"
        "    select:\n"
        f"{select_body}"
    )


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase22_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return cast(dict[str, object], document)
