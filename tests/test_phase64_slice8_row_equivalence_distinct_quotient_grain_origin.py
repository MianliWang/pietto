"""Real authored DISTINCT over canonical completed outputs and exact evidence."""

from pathlib import Path
from dataclasses import replace
import json

import pytest

from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedSetOutput,
)
from pietto._project.project_final_outputs import (
    ProjectEffectiveOutputCompletionTerminal,
    ProjectCompletedRowDomainKind,
)
from pietto._project.project_grain import (
    ProjectGrainOriginKind,
    ProjectGrainBasisState,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
)
from pietto._project.project_final_outputs import ProjectDistinctUnsupported
from pietto._project.project_row_equivalence import ProjectRowEquivalenceReason
from pietto.parser_api import parse_source
from pietto.ast_nodes import QueryDef, TableDef
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode
from pietto.errors import Severity
from pietto.ir import build_ir
from pietto import cli
from pietto._project.check import check_project_parse_only
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_completed_semantics import (
    with_project_single_match_requests,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchState,
    ProjectSingleMatchProofKind,
)
from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
    _two_current_globals_full,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _source as _join_source,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
)


def _source(type_name: str = "Int", *, distinct: bool = True) -> str:
    return f"""shape Row:
    value: {type_name} nullable
    hidden: Float nullable
source rows: Row is postgres.table("rows")
query result:
    from rows
    select{" distinct" if distinct else ""}:
        value
"""


@pytest.mark.parametrize("distinct", (False, True))
def test_visible_int_completes(tmp_path: Path, distinct: bool) -> None:
    result = _completed(tmp_path, _source(distinct=distinct))
    assert result.ok, result.diagnostics
    if distinct:
        assert isinstance(
            result.effective_outputs.entries[-1], ProjectCompletedEffectiveOutput
        )


def test_visible_float_is_unsupported(tmp_path: Path) -> None:
    result = _completed(tmp_path, _source("Float"))
    assert not result.ok
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]


def _entry(completed, name="result") -> ProjectCompletedEffectiveOutput:
    matches = tuple(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == name
    )
    assert len(matches) == 1
    entry = matches[0]
    assert isinstance(entry, ProjectCompletedEffectiveOutput), (
        entry,
        completed.diagnostics,
    )
    return entry


@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("distinct", (False, True))
def test_ast_retains_exact_token(kind: str, distinct: bool) -> None:
    source = _source(distinct=distinct).replace("query result:", f"{kind} result:")
    parsed = parse_source(source, path="syntax.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    definition = parsed.ast.definitions[-1]
    assert isinstance(definition, (TableDef, QueryDef))
    clause = definition.distinct_clause
    if distinct:
        assert clause is not None
        span = clause.span
        assert (span.path, span.line, span.column, span.end_line, span.end_column) == (
            "syntax.pietto",
            7,
            12,
            7,
            20,
        )
        assert (
            source.splitlines()[span.line - 1][span.column - 1 : span.end_column - 1]
            == "distinct"
        )
    else:
        assert clause is None


@pytest.mark.parametrize(
    "spelling",
    (
        "select all:",
        "select distinct distinct:",
        "select distinct on:",
        "select keep first:",
        "select distinct",
    ),
)
def test_unapproved_spellings_rejected(spelling: str) -> None:
    parsed = parse_source(_source().replace("select distinct:", spelling))
    assert parsed.diagnostics and parsed.diagnostics[0].code == "PIE-P1000"


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize(
    "type_name", ("Int", "Bool", "Text", "Date", "Timestamp", "UUID", "Decimal(12, 2)")
)
def test_support_domain(tmp_path: Path, mode: CheckMode, type_name: str) -> None:
    result = _completed(tmp_path, f"mode {mode.value}\n" + _source(type_name))
    assert result.ok, result.diagnostics
    entry = _entry(result)
    distinct = entry.row_domain.distinct
    assert distinct is not None and distinct.fields is entry.fields
    assert distinct.equivalence.supported
    assert distinct.uniqueness.fields is entry.fields
    assert distinct.uniqueness.equivalence is distinct.equivalence
    assert distinct.uniqueness.nulls_equal
    assert distinct.origin.kind is ProjectGrainOriginKind.DISTINCT_QUOTIENT
    assert distinct.origin.factor is not None and not distinct.global_input
    assert distinct.equivalence.evidence[0].selected is entry.fields[0]
    assert entry.fields[0].identity.kind.value == "relation_output"
    assert entry.fields[0].field.nullability.value == "nullable"
    if type_name.startswith("Decimal"):
        evidence = distinct.equivalence.evidence[0]
        assert evidence.decimal is not None
        assert (evidence.decimal.precision, evidence.decimal.scale) == (12, 2)
        assert entry.fields[0].field.field_def is not None
        assert evidence.decimal_type_expr is entry.fields[0].field.field_def.type_expr


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize(
    "type_name",
    ("Float", "Any", "Bytes", "Json", "Decimal", "Decimal(0, 2)", "Decimal(8, 9)"),
)
@pytest.mark.parametrize("nullability", ("nullable", "not null"))
def test_unsupported_domains_never_publish_proofs(
    tmp_path: Path, mode: CheckMode, type_name: str, nullability: str
) -> None:
    result = _completed(
        tmp_path,
        f"mode {mode.value}\n"
        + _source(type_name).replace(
            f"{type_name} nullable", f"{type_name} {nullability}"
        ),
    )
    assert not result.ok
    assert all(
        d.code == "PIE-S2339" and d.severity is Severity.ERROR
        for d in result.diagnostics
    )
    terminal = result.effective_outputs.entries[-1]
    assert isinstance(terminal, ProjectEffectiveOutputCompletionTerminal)
    assert terminal.output is None
    failure = terminal.blocker
    assert isinstance(failure, ProjectDistinctUnsupported)
    assert not failure.equivalence.supported
    assert not hasattr(failure, "origin") and not hasattr(failure, "uniqueness")
    if type_name == "Float":
        assert (
            failure.equivalence.evidence[0].reason
            is ProjectRowEquivalenceReason.FLOAT_EQUIVALENCE_DEFERRED
        )


@pytest.mark.parametrize("expression", ("1.25", "value + 1.0", "avg(value)"))
def test_float_computed_and_finite_literal_not_exempt(
    tmp_path: Path, expression: str
) -> None:
    source = _source().replace(
        "        value\n", f"        result_value = {expression}\n"
    )
    result = _completed(tmp_path, source)
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    assert "Float" in result.diagnostics[0].message


@pytest.mark.parametrize("type_name", ("Float", "Decimal(10, 2)"))
def test_alias_chain_uses_existing_resolution(tmp_path: Path, type_name: str) -> None:
    source = f"type Base = {type_name}\ntype Alias = Base\n" + _source("Alias")
    result = _completed(tmp_path, source)
    if type_name == "Float":
        assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
        terminal = result.effective_outputs.entries[-1]
        assert isinstance(terminal, ProjectEffectiveOutputCompletionTerminal)
        assert isinstance(terminal.blocker, ProjectDistinctUnsupported)
        assessment = terminal.blocker.equivalence
    else:
        assert result.ok, result.diagnostics
        distinct = _entry(result).row_domain.distinct
        assert distinct is not None
        assessment = distinct.equivalence
    resolution = assessment.evidence[0].resolution
    assert resolution is not None
    assert [i.declared_name for i in resolution.alias_chain] == ["Alias", "Base"]


@pytest.mark.parametrize(
    "kind", ("inner", "left", "cross", "right", "full", "semi", "anti")
)
def test_join_outputs_compare_only_visible_projection(
    tmp_path: Path, kind: str
) -> None:
    source = _join_source(None if kind == "cross" else "true", kind=kind).replace(
        "select:", "select distinct:"
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entry = _entry(result)
    distinct = entry.row_domain.distinct
    assert distinct is not None and len(distinct.equivalence.fields) == 1
    assert distinct.fields is entry.fields
    assert [f.output_name for f in entry.fields] == ["id"]
    assert distinct.origin.factor is not None
    assert distinct.input_domain.preserved is not None


@pytest.mark.parametrize("kind", ("inner", "left"))
@pytest.mark.parametrize("predicate", (None, "r.key is not null"))
def test_historical_and_refined_joins(
    tmp_path: Path, kind: str, predicate: str | None
) -> None:
    source = _join_source(
        predicate, kind=kind, via="        via link: l -> r\n"
    ).replace("select:", "select distinct:")
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    assert _entry(result).row_domain.distinct is not None


@pytest.mark.parametrize("grouped", (False, True))
@pytest.mark.parametrize("joined", (False, True))
def test_grouped_global_postures(tmp_path: Path, grouped: bool, joined: bool) -> None:
    source = _join_source("lhs.id == r.id") if joined else _source(distinct=False)
    field_name = "lhs.id" if joined else "value"
    original_projection = "        id = lhs.id\n" if joined else "        value\n"
    projection = (
        f"        key_value = {field_name}\n" if grouped else ""
    ) + "        total = count()\n"
    source = source.replace(original_projection, projection)
    source = source.replace(
        "    select:",
        (f"    group by:\n        {field_name}\n" if grouped else "")
        + "    select distinct:",
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entry = _entry(result)
    distinct = entry.row_domain.distinct
    assert distinct is not None
    assert distinct.global_input is not grouped
    assert (distinct.origin.factor is None) is not grouped
    assert entry.row_domain.kind is (
        ProjectCompletedRowDomainKind.DISTINCT
        if grouped
        else ProjectCompletedRowDomainKind.GLOBAL
    )


@pytest.mark.parametrize("selected", (False, True))
def test_window_qualify_visible_boundary(tmp_path: Path, selected: bool) -> None:
    source = _source()
    if selected:
        source += "        rn = row_number() window:\n            order by:\n                value\n    qualify:\n        rn <= 2\n"
    else:
        source += "    qualify:\n        row_number() window:\n            order by:\n                hidden\n        <= 2\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entry = _entry(result)
    assert len(entry.fields) == (2 if selected else 1)
    assert entry.row_domain.distinct is not None
    assert len(entry.row_domain.distinct.equivalence.fields) == len(entry.fields)


@pytest.mark.parametrize("order", ("value", "hidden"))
def test_no_winner_order(tmp_path: Path, order: str) -> None:
    result = _completed(tmp_path, _source() + f"    order by:\n        {order}\n")
    if order == "value":
        assert result.ok, result.diagnostics
        distinct = _entry(result).row_domain.distinct
        assert distinct is not None and len(distinct.order_proofs) == 1
    else:
        assert [d.code for d in result.diagnostics] == ["PIE-S2340"]


def test_hidden_order_with_exact_strict_fd(tmp_path: Path) -> None:
    source = _source().replace(
        "value: Int nullable", "value: Int not null\n    unique by_value on value"
    )
    result = _completed(tmp_path, source + "    order by:\n        hidden\n")
    assert result.ok, result.diagnostics
    distinct = _entry(result).row_domain.distinct
    assert distinct is not None and distinct.order_proofs


@pytest.mark.parametrize("side", ("left", "right", "self"))
def test_distinct_named_input_replay_join_occurrences(
    tmp_path: Path, side: str
) -> None:
    source = _source().replace("query result:", "table dedup:")
    source += "table replay:\n    from dedup\n    select:\n        value\n"
    left, right = (
        ("replay", "rows")
        if side == "left"
        else ("rows", "replay")
        if side == "right"
        else ("replay", "replay")
    )
    source += f"query result:\n    from {left}\n    inner join {right} as r:\n        from {left}\n        on true\n    select:\n        v = {left}.value\n        w = r.value\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result, "dedup").row_domain.distinct
    assert distinct is not None
    grain = result.effective_outputs.current_regions[
        -1
    ].final_properties.relational.grain
    active = tuple(
        g
        for g in grain.active
        if isinstance(g, ProjectJoinGrainFactorIdentity)
        and g.base is distinct.origin.factor
    )
    assert len(active) == (2 if side == "self" else 1)
    if side == "self":
        assert (
            active[0] is not active[1]
            and active[0].introduction_use != active[1].introduction_use
        )


def test_repeated_distinct_retains_authored_authority(tmp_path: Path) -> None:
    source = _source().replace("query result:", "table first:")
    source += "query result:\n    from first\n    select distinct:\n        value\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    first, second = _entry(result, "first"), _entry(result)
    assert (
        first.row_domain.distinct is not None and second.row_domain.distinct is not None
    )
    assert first.row_domain.distinct.clause is not second.row_domain.distinct.clause
    assert second.row_domain.distinct.input_domain.preserved is first.row_domain


def test_null_bag_and_hidden_field_oracle(tmp_path: Path) -> None:
    source = _source().replace(
        "        value\n", "        value\n        absent = null\n"
    )
    # Use a typed nullable field, not an untyped NULL projection.
    source = (
        _source()
        .replace(
            "    hidden: Float nullable",
            "    absent: Int nullable\n    hidden: Float nullable",
        )
        .replace("        value\n", "        value\n        absent\n")
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result).row_domain.distinct
    assert distinct is not None
    names = tuple(f.output_name for f in distinct.fields)
    rows = (
        {"value": 1, "absent": None, "hidden": 10},
        {"value": 1, "absent": None, "hidden": 20},
        {"value": 2, "absent": None, "hidden": 30},
    )
    classes: list[tuple[int | None, ...]] = []
    for row in rows:
        visible = tuple(row[name] for name in names)
        if not any(
            all(
                (a is None and b is None)
                or (a is not None and b is not None and a == b)
                for a, b in zip(visible, previous, strict=True)
            )
            for previous in classes
        ):
            classes.append(visible)
    assert classes == [(1, None), (2, None)]
    assert len(rows) == 3


def test_legacy_ir_rejects_and_combined_ir_retains_distinct(tmp_path: Path) -> None:
    parsed = parse_source(_source())
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2334" for d in semantic.diagnostics)
    ir = build_ir(parsed.ast, semantic.model)
    assert ir.ir is None and [d.code for d in ir.diagnostics] == ["PIE-I1000"]
    result = _completed(tmp_path, _source())
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
        ProjectIRDistinctComparison,
    )

    snapshot = build_project_query_block_ir(result)
    assert verify_project_query_block_ir(snapshot).verified
    entry = next(e for e in snapshot.entries if e.owner is _entry(result).owner)
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    operator = next(op for op in entry.operators if op.kind.value == "distinct")
    assert isinstance(operator.evidence, ProjectIRDistinctComparison)
    assert operator.evidence.semantic is _entry(result).row_domain.distinct


def test_foreign_and_equal_looking_authority_cannot_graft(tmp_path: Path) -> None:
    result = _completed(tmp_path / "a", _source())
    foreign = _completed(tmp_path / "b", _source())
    entry, other = _entry(result), _entry(foreign)
    distinct = entry.row_domain.distinct
    assert distinct is not None and other.row_domain.distinct is not None
    with pytest.raises(ValueError):
        replace(distinct, clause=replace(distinct.clause))
    with pytest.raises(ValueError):
        replace(entry, row_domain=other.row_domain)
    with pytest.raises(ValueError):
        replace(entry, fields=tuple(replace(f) for f in entry.fields))
    for field_name, value in (
        ("equivalence", other.row_domain.distinct.equivalence),
        ("origin", other.row_domain.distinct.origin),
        ("uniqueness", other.row_domain.distinct.uniqueness),
    ):
        with pytest.raises((TypeError, ValueError), match="init=False"):
            replace(distinct, **{field_name: value})


def test_unknown_upstream_gets_quotient_factor(tmp_path: Path) -> None:
    source = _two_current_globals_full(
        "        left_total = left_global.total\n        right_total = r.total\n"
    )
    source = source.replace("query result:", "table dedup:")
    start = source.index("table dedup:")
    source = source[:start] + source[start:].replace("select:", "select distinct:")
    source += "query result:\n    from dedup\n    inner join lhs as l:\n        from dedup\n        on true\n    select:\n        total = dedup.left_total\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result, "dedup").row_domain.distinct
    assert distinct is not None and distinct.input_domain.preserved is not None
    assert isinstance(distinct.input_domain.preserved, ProjectIRProvidedIntrinsicGrain)
    assert distinct.input_domain.preserved.state is ProjectGrainBasisState.UNKNOWN
    assert distinct.origin.factor is not None and not distinct.global_input
    incoming = result.effective_outputs.current_regions[-1].joins[0].left_input
    assert incoming.grain.state is ProjectGrainBasisState.FACTORIZED
    assert incoming.grain.active == (distinct.origin.factor,)
    assert not incoming.keys


@pytest.mark.parametrize(
    "limit_on_right,limit_after_join", ((None, None), (1, None), (None, 1), (0, None))
)
def test_distinct_and_limit_keep_single_match_laws(
    tmp_path: Path, limit_on_right: int | None, limit_after_join: int | None
) -> None:
    source = _source().replace("query result:", "table dedup:")
    if limit_on_right is not None:
        source += f"    limit {limit_on_right}\n"
    source += "query result:\n    from rows\n    inner join dedup as d:\n        from rows\n        on true\n    select:\n        value = rows.value\n"
    if limit_after_join is not None:
        source += f"    limit {limit_after_join}\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    condition = result.roots.join_conditions.entries[0]
    request = ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)
    checked = with_project_single_match_requests(result, (request,))
    assessment = checked.single_matches.entries[0]
    if limit_on_right is None:
        assert assessment.state is ProjectSingleMatchState.LEGAL_UNPROVED
        assert [d.code for d in checked.diagnostics] == ["PIE-S2337"]
    else:
        assert assessment.state is ProjectSingleMatchState.PROVED
        limit = _entry(result, "dedup").limit
        assert limit is not None
        assert any(
            p.kind is ProjectSingleMatchProofKind.RIGHT_LIMIT
            and any(r is limit for r in p.roots)
            for p in assessment.proofs
        )


@pytest.mark.parametrize("source_limit", (0, 1))
def test_distinct_retains_exact_upstream_limit_posture(
    tmp_path: Path, source_limit: int
) -> None:
    source = _source(distinct=False).replace("query result:", "table bounded:")
    source += f"    limit {source_limit}\nquery result:\n    from bounded\n    select distinct:\n        value\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result).row_domain.distinct
    assert distinct is not None and distinct.global_input
    assert distinct.origin.factor is None


def test_decimal_parameters_are_exact_not_nullable_or_widened(tmp_path: Path) -> None:
    source = (
        _source("Decimal(10, 2)")
        .replace(
            "    hidden: Float nullable",
            "    same: Decimal(10, 2) not null\n    wider: Decimal(12, 2) nullable\n    scale: Decimal(10, 3) nullable",
        )
        .replace(
            "        value\n",
            "        value\n        same\n        wider\n        scale\n",
        )
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result).row_domain.distinct
    assert distinct is not None
    first, same, wider, scale = distinct.equivalence.evidence
    assert first.decimal == same.decimal
    assert first.decimal != wider.decimal and first.decimal != scale.decimal
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(first, decimal=wider.decimal)


def test_unpropagated_decimal_computation_fails_closed(tmp_path: Path) -> None:
    source = _source("Decimal(10, 2)").replace(
        "        value\n", "        computed = value + value\n"
    )
    result = _completed(tmp_path, source)
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    assert "missing_or_unpropagated" in result.diagnostics[0].message


@pytest.mark.parametrize("type_name", ("Float", "Decimal(9, 2)"))
def test_imported_alias_resolution(tmp_path: Path, type_name: str) -> None:
    (tmp_path / "types.pietto").write_text(
        f"type Base = {type_name}\nexport:\n    type Base\n"
    )
    (tmp_path / "facade.pietto").write_text(
        'import "types.pietto":\n    type Base as Public\nexport:\n    type Public\n'
    )
    source = 'import "facade.pietto":\n    type Public as Alias\n' + _source("Alias")
    result = _completed(tmp_path, source)
    if type_name == "Float":
        assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    else:
        assert result.ok, result.diagnostics
        distinct = _entry(result).row_domain.distinct
        assert distinct is not None
        evidence = distinct.equivalence.evidence[0]
        assert evidence.decimal is not None and evidence.decimal.precision == 9
        assert (
            evidence.resolution is not None
            and evidence.resolution.direct_symbol is not None
        )
        assert (
            evidence.resolution.direct_symbol.target_identity.module_path
            == "types.pietto"
        )


def test_distinct_import_reexport_and_downstream_join(tmp_path: Path) -> None:
    (tmp_path / "producer.pietto").write_text(
        _source().replace("query result:", "table dedup:")
        + "export:\n    table dedup\n"
    )
    (tmp_path / "facade.pietto").write_text(
        'import "producer.pietto":\n    table dedup as Public\nexport:\n    table Public\n'
    )
    source = 'import "facade.pietto":\n    table Public as Input\nquery result:\n    from Input\n    inner join Input as again:\n        from Input\n        on true\n    select:\n        left_value = Input.value\n        right_value = again.value\n'
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result, "dedup").row_domain.distinct
    assert distinct is not None
    grain = result.effective_outputs.current_regions[
        -1
    ].final_properties.relational.grain
    assert len(grain.active) == 2
    assert all(
        isinstance(f, ProjectJoinGrainFactorIdentity)
        and f.base is distinct.origin.factor
        for f in grain.active
    )


def test_float_window_result_is_deferred(tmp_path: Path) -> None:
    source = _source().replace(
        "        value\n",
        "        fraction = percent_rank() window:\n            order by:\n                value\n",
    )
    result = _completed(tmp_path, source)
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    assert "Float" in result.diagnostics[0].message


def test_unrelated_branch_and_diagnostics_survive(tmp_path: Path) -> None:
    source = _source("Float").replace("query result:", "query unsupported:")
    source += "query result:\n    from rows\n    select distinct:\n        yes = true\n"
    result = _completed(tmp_path, source)
    assert not result.ok
    assert [d.code for d in result.diagnostics] == ["PIE-S2339"]
    assert _entry(result).row_domain.distinct is not None


def test_unknown_type_keeps_original_diagnostic(tmp_path: Path) -> None:
    ordinary = _completed(tmp_path / "plain", _source("Missing", distinct=False))
    distinct = _completed(tmp_path / "distinct", _source("Missing"))
    assert not ordinary.ok and not distinct.ok
    assert [d.code for d in distinct.diagnostics] == [
        d.code for d in ordinary.diagnostics
    ]
    assert all(d.code != "PIE-S2339" for d in distinct.diagnostics)


@pytest.mark.parametrize("nullable_key", (False, True))
def test_order_counterexample_and_nullable_key_do_not_choose_winner(
    tmp_path: Path, nullable_key: bool
) -> None:
    source = (
        _source().replace("value", "customer_id").replace("hidden: Float", "score: Int")
    )
    if nullable_key:
        source = source.replace(
            "    score: Int nullable",
            "    score: Int nullable\n    unique customer_key on customer_id",
        )
    result = _completed(tmp_path, source + "    order by:\n        score\n")
    assert [d.code for d in result.diagnostics] == ["PIE-S2340"]
    rows = ((None, 10), (None, 20)) if nullable_key else ((1, 10), (1, 20))
    assert rows[0][0] == rows[1][0] and rows[0][1] != rows[1][1]


@pytest.mark.parametrize("kind", ("inner", "left"))
def test_join_order_selected_vs_hidden(tmp_path: Path, kind: str) -> None:
    source = _join_source("true", kind=kind).replace("select:", "select distinct:")
    good = _completed(tmp_path / "good", source + "    order by:\n        lhs.id\n")
    bad = _completed(tmp_path / "bad", source + "    order by:\n        r.key\n")
    assert good.ok, good.diagnostics
    assert [d.code for d in bad.diagnostics] == ["PIE-S2340"]


@pytest.mark.parametrize("producer", ("grouped", "global", "window"))
@pytest.mark.parametrize("side", ("left", "right"))
def test_tail_distinct_output_is_consumable(
    tmp_path: Path, producer: str, side: str
) -> None:
    source = _source().replace("query result:", "table dedup:")
    if producer == "grouped":
        source = source.replace(
            "    select distinct:", "    group by:\n        value\n    select distinct:"
        )
        source += "        total = count()\n"
    elif producer == "global":
        source = source.replace("        value\n", "        total = count()\n")
    else:
        source += "        total = row_number() window:\n            order by:\n                value\n    qualify:\n        total <= 3\n"
    left, right = ("dedup", "rows") if side == "left" else ("rows", "dedup")
    reference = "dedup.total" if side == "left" else "d.total"
    source += f"query result:\n    from {left}\n    inner join {right} as d:\n        from {left}\n        on true\n    select:\n        result_value = {reference}\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    distinct = _entry(result, "dedup").row_domain.distinct
    assert distinct is not None
    join = result.effective_outputs.current_regions[-1].joins[0]
    incoming = join.left_input if side == "left" else join.right_input
    assert incoming.grain.origin_set is distinct.origin
    assert incoming.grain.state is (
        ProjectGrainBasisState.GLOBAL
        if producer == "global"
        else ProjectGrainBasisState.FACTORIZED
    )


def test_decimal_source_type_evidence_cannot_be_substituted(tmp_path: Path) -> None:
    source = (
        _source("Decimal(10, 2)")
        .replace("    hidden: Float nullable", "    other: Decimal(12, 3) nullable")
        .replace("        value\n", "        value\n        other\n")
    )
    completed = _completed(tmp_path, source)
    entry = _entry(completed)
    distinct = entry.row_domain.distinct
    assert distinct is not None
    first, second = entry.fields
    forged = replace(
        first, field=replace(first.field, field_def=second.field.field_def)
    )
    forged_fields = (forged, second)
    with pytest.raises(ValueError, match="field|type|source"):
        forged_distinct = replace(distinct, fields=forged_fields)
        replace(
            entry,
            fields=forged_fields,
            schema=replace(
                entry.schema, fields={f.output_name: f.field for f in forged_fields}
            ),
            row_domain=replace(entry.row_domain, distinct=forged_distinct),
        )


def test_order_evidence_cannot_be_removed(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source() + "    order by:\n        value\n")
    entry = _entry(completed)
    distinct = entry.row_domain.distinct
    assert distinct is not None
    with pytest.raises(ValueError, match="ORDER|order"):
        replace(
            entry,
            row_domain=replace(
                entry.row_domain, distinct=replace(distinct, order_proofs=())
            ),
        )


@pytest.mark.parametrize("mode", tuple(CheckMode))
@pytest.mark.parametrize("type_name", ("Int", "Float"))
def test_public_explicit_check_keeps_json_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: CheckMode, type_name: str
) -> None:
    _completed(tmp_path, f"mode {mode.value}\n" + _source(type_name))
    code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert not captured.err
    assert code == (0 if type_name == "Int" else 1)
    assert document["ok"] is (type_name == "Int")
    assert set(document) == {
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    }
    if type_name == "Float":
        assert [(d["code"], d["severity"]) for d in document["diagnostics"]] == [
            ("PIE-S2339", "error")
        ]


def test_legacy_flat_and_explain_keep_existing_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _completed(tmp_path, _source())
    assert cli.main(["explain", "--project", str(tmp_path), "--format", "json"]) == 2
    capsys.readouterr()
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
    assert not document["ok"]
    assert any(d["code"] == "PIE-S2334" for d in document["diagnostics"])


def test_package_root_keeps_pre_selection_boundary(tmp_path: Path) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 3\n[package]\npath = "pkg"\nnamespace = "test"\nname = "example"\nversion = "1.0.0"\nsha256 = "'
        + "a" * 64
        + '"\n'
    )
    (tmp_path / "main.pietto").write_text(_source())
    parsed = check_project_parse_only(tmp_path)
    assert not parsed.ok and not parsed.parsed_inputs
    assert any(
        "does not use project source selection" in e.message for e in parsed.errors
    )


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_single_file_emit_never_omits_distinct(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dialect: str
) -> None:
    path = tmp_path / "main.pietto"
    path.write_text(_source().replace("postgres.table", f"{dialect}.table"))
    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 1
    captured = capsys.readouterr()
    assert "SELECT" not in captured.out
    assert "PIE-S2334" in captured.err


@pytest.mark.parametrize("operator", ("union", "intersect", "except"))
@pytest.mark.parametrize("quantifier", ("all", "distinct"))
def test_distinct_inputs_and_repeated_set_uses_are_retained(
    tmp_path: Path, operator: str, quantifier: str
) -> None:
    source = _source().replace("query result:", "table dedup:")
    source += f"query unavailable:\n    {operator} {quantifier}:\n        from dedup\n        from dedup\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    assert _entry(result, "dedup").row_domain.distinct is not None
    output = result.effective_outputs.entries[-1]
    assert isinstance(output, ProjectCompletedSetOutput)
    assert all(
        use.authority.entry is _entry(result, "dedup") for use in output.root.uses
    )
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedSetOperationOutput,
    )

    snapshot = build_project_query_block_ir(result)
    assert verify_project_query_block_ir(snapshot).verified
    entry = next(e for e in snapshot.entries if e.owner is output.owner)
    assert isinstance(entry, ProjectIRCompletedSetOperationOutput)
    assert entry.semantic_entry is output
    assert len(entry.operands) == 2
    assert entry.operands[0].producer is entry.operands[1].producer
    assert entry.uses[0] is not entry.uses[1]


def test_hidden_multihop_fields_do_not_enter_equivalence(tmp_path: Path) -> None:
    source = _join_source(
        None, via="        via link: l -> r\n        via link: r -> l\n"
    )
    source = source.replace("inner join rhs as r:", "inner join lhs as r:").replace(
        "select:", "select distinct:"
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entry = _entry(result)
    assert entry.row_domain.distinct is not None and len(entry.fields) == 1
    root = entry.root
    from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify

    assert isinstance(root, ProjectConcreteJoinedQualify)
    environment = (
        root.window_stage.input_aggregation.input_filter.namespace.binding_environment
    )
    assert environment.hidden_fields
    assert len(entry.row_domain.distinct.equivalence.fields) == 1


def test_nullable_predicate_equality_is_not_strengthened(tmp_path: Path) -> None:
    source = _source().replace(
        "    select distinct:",
        "    where value == value\n    select distinct:",
    )
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entry = _entry(result)
    assert entry.fields[0].field.nullability.value == "nullable"
    assert (
        entry.row_domain.distinct is not None
        and entry.row_domain.distinct.uniqueness.nulls_equal
    )
    from pietto._project.project_final_outputs import ProjectConcreteNoJoinReplay

    assert isinstance(entry.root, ProjectConcreteNoJoinReplay)
    assert entry.root.where.expression_analysis is not None
    value_type = entry.root.where.expression_analysis.value_type
    assert value_type is not None and value_type.resolved_type.name == "Bool"
    assert value_type.nullability.value == "unknown"


@pytest.mark.parametrize("mutation", ("root", "global", "order"))
def test_distinct_producer_itself_requires_closed_roots(
    tmp_path: Path, mutation: str
) -> None:
    entry = _entry(_completed(tmp_path, _source() + "    order by:\n        value\n"))
    distinct = entry.row_domain.distinct
    assert distinct is not None
    changes = (
        {"root": object()}
        if mutation == "root"
        else {"global_input": True}
        if mutation == "global"
        else {"order_proofs": ()}
    )
    with pytest.raises((TypeError, ValueError)):
        replace(distinct, **changes)
