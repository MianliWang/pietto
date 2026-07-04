from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import BinaryIR, ComparisonIR, FieldRefIR, RelationIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase40-let-binding-aggregate-interaction-boundary-v1.md"
)
IR_SURFACE_PATHS = (
    REPO_ROOT / "src/pietto/ir/model.py",
    REPO_ROOT / "src/pietto/ir/builder.py",
    REPO_ROOT / "src/pietto/ir/lowering.py",
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_aggregate_interaction_boundary_contract_doc_is_locked() -> None:
    assert SPEC_PATH.exists()
    text = SPEC_PATH.read_text(encoding="utf-8")

    for required in [
        "Phase 40 Slice 8 is docs/spec and tests/static-audit boundary hardening only.",
        "row-level `where`",
        "no-GROUP non-aggregate `select`",
        "no-GROUP input-scope `order by`",
        "Aggregate arguments do not see let names in Slice 8.",
        "`sum(gross)`",
        "`avg(gross)`",
        "`count(gross)`",
        "`count_distinct(gross)`",
        "deferred boundary, not a permanent language rejection",
        "explicit semantic aggregate-argument scope design",
        "IR aggregate-argument inline expansion design",
        "SQL stability proof",
        "`group by gross` remains fail-closed/deferred",
        "`satisfying: gross > 0` remains fail-closed/deferred",
        "grouped `order by gross` remains fail-closed/deferred",
        "`limit gross` remains fail-closed/deferred",
        "`where gross > 0` in a grouped query remains supported",
        "Projection aliases remain output names only.",
        "no `LetBindingIR`",
        "no `RelationLayerIR`",
        "no hidden CTE insertion",
        "no hidden subquery insertion",
        "no public `let_scopes` metadata key",
    ]:
        assert required in text

    assert "package version remains `0.1.0`" in text.lower()
    assert "no release, tag, publish, upload, signing, or attestation" in text


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        smallest = min(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        distinct_count = count_distinct(gross)\n",
            "PIE-S2315",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        total = sum(orders.gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        total = sum(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
    ],
)
def test_aggregate_and_result_scope_let_consumers_fail_closed(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query aggregate_boundary:\n" + body)
    codes = _error_codes(semantic)

    assert expected_code in codes
    assert "PIE-S2328" not in codes


def test_unsupported_min_max_aggregate_let_never_reaches_successful_ir() -> None:
    semantic = _semantic_for(
        "query aggregate_boundary:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        smallest = min(gross)\n"
    )

    assert "PIE-S2102" in _error_codes(semantic)
    assert semantic.diagnostics != ()


def test_grouped_row_level_where_still_inlines_before_aggregate() -> None:
    relation = _relation_ir(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount)\n"
    )

    assert relation.filter is not None
    assert isinstance(relation.filter.expression, ComparisonIR)
    assert isinstance(relation.filter.expression.left, BinaryIR)
    assert not _field_refs_named(relation, {"gross"})


def test_no_group_select_and_order_by_still_inline_row_level_let() -> None:
    relation = _relation_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n"
        "    order by:\n"
        "        gross\n"
    )

    assert isinstance(relation.projections[0].expression, BinaryIR)
    assert isinstance(relation.order_by[0].expression, BinaryIR)
    assert not _field_refs_named(relation, {"gross"})


def test_unsupported_aggregate_let_emit_sql_json_and_output_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "aggregate_let.pietto",
        "query aggregate_boundary:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        smallest = min(gross)\n",
    )
    missing_output = tmp_path / "missing.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(missing_output),
            ]
        )
        == 1
    )
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["ok"] is False
    assert document["artifacts"] == []
    assert document["output"] == {"path": str(missing_output), "written": False}
    assert "PIE-S2102" in [diagnostic["code"] for diagnostic in diagnostics]
    assert not missing_output.exists()

    existing_output = tmp_path / "existing.sql"
    existing_output.write_text("original SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(existing_output),
            ]
        )
        == 1
    )
    text_failure = capsys.readouterr()
    assert "PIE-S2102" in text_failure.err
    assert existing_output.read_text(encoding="utf-8") == "original SQL\n"


def test_supported_grouped_row_level_where_still_emits_inline_sql() -> None:
    sql = _postgres_sql(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(amount)\n"
    )

    assert '"gross"' not in sql
    assert '("amount" + "tax") > 0' in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()


def test_no_let_ir_or_hidden_layer_surface_is_authorized() -> None:
    combined_ir = "\n".join(
        path.read_text(encoding="utf-8") for path in IR_SURFACE_PATHS
    )

    assert "LetBindingIR" not in combined_ir
    assert "RelationLayerIR" not in combined_ir


def test_supported_row_level_explain_json_still_hides_let_scopes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "supported.pietto",
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n",
    )

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    document = _read_json(capsys)

    assert document["ok"] is True
    assert document["artifact"] == "Semantic Metadata Artifact v1"
    assert "metadata" in document
    assert "let_scopes" not in json.dumps(document)


def test_unsupported_aggregate_let_explain_json_fails_without_metadata(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "aggregate_let.pietto",
        "query aggregate_boundary:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        smallest = min(gross)\n",
    )

    assert cli.main(["explain", str(path), "--format", "json"]) == 1
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["ok"] is False
    assert "metadata" not in document
    assert cast(dict[str, object], document["error"])["stage"] == "semantic"
    assert "PIE-S2102" in [diagnostic["code"] for diagnostic in diagnostics]
    assert "let_scopes" not in json.dumps(document)


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="aggregate_boundary.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ir(source: str) -> RelationIR:
    result = parse_source(SOURCE_PREFIX + source, path="aggregate_boundary.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = ir_result.ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _postgres_sql(source: str) -> str:
    result = parse_source(SOURCE_PREFIX + source, path="aggregate_boundary.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    sql_result = emit_postgres_sql(ir_result.ir)
    assert sql_result.diagnostics == ()
    assert len(sql_result.artifacts) == 1
    assert sql_result.artifacts[0].kind is SqlArtifactKind.RELATION
    return sql_result.artifacts[0].sql


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _field_refs_named(relation: RelationIR, names: set[str]) -> bool:
    return any(ref.name in names for ref in _field_refs(relation))


def _field_refs(value: object) -> tuple[FieldRefIR, ...]:
    refs: list[FieldRefIR] = []
    if isinstance(value, FieldRefIR):
        refs.append(value)
    if isinstance(value, tuple):
        for item in value:
            refs.extend(_field_refs(item))
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            refs.extend(_field_refs(getattr(value, field.name)))
    return tuple(refs)
