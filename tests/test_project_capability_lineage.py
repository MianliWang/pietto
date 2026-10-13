from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import _pietto_semantic_fact_preservation as project_upstream
import _pietto_project_package_lineage as graph_upstream
import pytest

from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.package_graph_inspection import (
    PackageGraphInspectionLinkKind,
    PackageGraphInspectionRecordKind,
    _inspect_package_graph,
)
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowSemanticProvenance,
)
from pietto.ast_nodes import QueryDef, WindowExpr, WindowUseKind
from pietto.ir import build_ir
from pietto.ir.model import NamedWindowBaseIR, RelationIR, ScriptIR, WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.window_semantics import (
    ResolvedNamedWindowNamespace,
    WindowComponentOrigin,
    WindowExpressionAnalysis,
    WindowNullTreatment,
)
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.window_strategy import (
    NamedWindowLoweringStrategy,
    WindowTargetDialect,
    WindowTargetEvidenceKind,
    WindowTargetEvidenceOutcome,
    decide_named_window_lowering,
    window_runtime_semantically_equal,
)


PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    value: Int nullable\n"
    "    category: Text nullable\n"
)


def _source(
    *,
    connector: str = "postgres.table",
    selections: str,
    declarations: str,
) -> str:
    return (
        PREFIX + f'source rows: Row is {connector}("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        f"{selections}"
        f"{declarations}"
    )


def _compile(source: str) -> tuple[QueryDef, ScriptIR, RelationIR]:
    parsed = parse_source(source, path="slice10.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    definition = cast(QueryDef, parsed.ast.definitions[-1])
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.diagnostics == () and lowered.ir is not None
    relation = cast(RelationIR, lowered.ir.definitions[-1])
    return definition, lowered.ir, relation


def _window_calls(relation: RelationIR) -> tuple[WindowCallIR, ...]:
    return tuple(
        cast(WindowCallIR, projection.expression)
        for projection in relation.projections
        if type(projection.expression) is WindowCallIR
    )


def test_mysql_preserves_reachable_source_order_with_forward_references() -> None:
    _definition, script_ir, relation = _compile(
        _source(
            connector="mysql.table",
            selections="        result = row_number() window child\n",
            declarations=(
                "    window child = base\n"
                "    window unused:\n"
                "        order by:\n"
                "            value\n"
                "    window base:\n"
                "        order by:\n"
                "            id\n"
            ),
        )
    )
    decision = decide_named_window_lowering(relation, WindowTargetDialect.MYSQL)
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NATIVE_PRESERVE
    assert tuple(item.name for item in decision.reachable_declarations) == (
        "child",
        "base",
    )
    assert tuple(item.name for item in decision.emission_declarations) == (
        "child",
        "base",
    )
    with pytest.raises(ValueError, match="source order"):
        replace(
            decision,
            emission_declarations=tuple(reversed(decision.emission_declarations)),
        )
    with pytest.raises(ValueError, match="source order"):
        replace(
            decision,
            emission_declarations=(
                *decision.emission_declarations,
                decision.emission_declarations[-1],
            ),
        )
    result = emit_mysql_sql(script_ir)
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert "WINDOW\n    `child` AS (`base`),\n    `base` AS" in sql
    assert "unused" not in sql


def test_postgresql_uses_stable_base_first_topological_order() -> None:
    _definition, script_ir, relation = _compile(
        _source(
            selections=(
                "        first = row_number() window child\n"
                "        second = rank() window independent\n"
            ),
            declarations=(
                "    window child = base\n"
                "    window independent:\n"
                "        order by:\n"
                "            value\n"
                "    window base:\n"
                "        order by:\n"
                "            id\n"
            ),
        )
    )
    decision = decide_named_window_lowering(
        relation,
        WindowTargetDialect.POSTGRESQL,
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NATIVE_REORDER
    assert tuple(item.name for item in decision.emission_declarations) == (
        "independent",
        "base",
        "child",
    )
    with pytest.raises(ValueError, match="stable topology"):
        replace(decision, emission_declarations=decision.reachable_declarations)
    result = emit_postgres_sql(script_ir)
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    window_clause = sql.split("\nWINDOW\n", 1)[1]
    assert window_clause.index('"independent" AS') < window_clause.index('"base" AS')
    assert window_clause.index('"base" AS') < window_clause.index('"child" AS')


def test_native_window_clause_uses_grouped_inputs_and_exact_clause_order() -> None:
    source = (
        PREFIX + 'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    group by:\n"
        "        category\n"
        "    select:\n"
        "        category\n"
        "        total = sum(value)\n"
        "        ranking = rank() window ordered\n"
        "    window ordered:\n"
        "        order by:\n"
        "            total desc\n"
        "    satisfying:\n"
        "        total > 0\n"
        "    order by:\n"
        "        ranking\n"
        "    limit 5\n"
    )
    _definition, script_ir, _relation = _compile(source)
    result = emit_postgres_sql(script_ir)
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert '"ordered" AS (ORDER BY SUM("value") DESC)' in sql
    assert sql.index("\nHAVING\n") < sql.index("\nWINDOW\n")
    assert sql.index("\nWINDOW\n") < sql.index("\nORDER BY\n")
    assert sql.index("\nORDER BY\n") < sql.index("\nLIMIT 5")


def test_postgresql_framed_base_falls_back_to_exact_inline_bytes() -> None:
    named_source = _source(
        selections=(
            "        result = nth_value(value, 2) from first respect nulls "
            "window child\n"
        ),
        declarations=(
            "    window child = base\n"
            "    window base:\n"
            "        partition by:\n"
            "            category\n"
            "        order by:\n"
            "            id desc\n"
            "        rows between 1 preceding and current row exclude ties\n"
        ),
    )
    inline_source = _source(
        selections=(
            "        result = nth_value(value, 2) from first respect nulls window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                id desc\n"
            "            rows between 1 preceding and current row exclude ties\n"
        ),
        declarations="",
    )
    _named_definition, named_ir, named_relation = _compile(named_source)
    _inline_definition, inline_ir, inline_relation = _compile(inline_source)
    decision = decide_named_window_lowering(
        named_relation,
        WindowTargetDialect.POSTGRESQL,
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.INLINE_EXACT
    named_call = _window_calls(named_relation)[0]
    inline_call = _window_calls(inline_relation)[0]
    assert named_call != inline_call
    assert window_runtime_semantically_equal(named_call, inline_call)
    named_result = emit_postgres_sql(named_ir)
    inline_result = emit_postgres_sql(inline_ir)
    assert named_result.diagnostics == inline_result.diagnostics == ()
    assert named_result.artifacts[0].sql == inline_result.artifacts[0].sql
    assert "WINDOW" not in named_result.artifacts[0].sql


def test_direct_framed_reference_and_effective_default_remain_distinct() -> None:
    _definition, framed_ir, framed_relation = _compile(
        _source(
            selections="        result = first_value(value) window base\n",
            declarations=(
                "    window base:\n"
                "        order by:\n"
                "            id\n"
                "        rows current row\n"
            ),
        )
    )
    framed_decision = decide_named_window_lowering(
        framed_relation,
        WindowTargetDialect.POSTGRESQL,
    )
    assert framed_decision is not None
    assert framed_decision.strategy is NamedWindowLoweringStrategy.NATIVE_REORDER
    framed_sql = emit_postgres_sql(framed_ir).artifacts[0].sql
    assert 'OVER "base"' in framed_sql
    assert '"base" AS (ORDER BY "id" ASC ROWS CURRENT ROW EXCLUDE NO OTHERS)' in (
        framed_sql
    )

    _definition, default_ir, default_relation = _compile(
        _source(
            selections=(
                "        ranking = row_number() window base\n"
                "        result = first_value(value) window base\n"
            ),
            declarations=("    window base:\n        order by:\n            id\n"),
        )
    )
    default_sql = emit_postgres_sql(default_ir).artifacts[0].sql
    assert 'ROW_NUMBER() OVER "base" AS "ranking"' in default_sql
    assert (
        'OVER ("base" RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW '
        "EXCLUDE NO OTHERS)"
    ) in default_sql
    default_decision = decide_named_window_lowering(
        default_relation,
        WindowTargetDialect.POSTGRESQL,
    )
    assert default_decision is not None
    assert any(
        item.kind is WindowTargetEvidenceKind.EFFECTIVE_DEFAULT
        and "use-local" in item.detail
        for item in default_decision.evidence
    )


_DIALECTS = (
    ("postgres.table", WindowTargetDialect.POSTGRESQL),
    ("mysql.table", WindowTargetDialect.MYSQL),
)


def _emit(script_ir: ScriptIR, dialect: WindowTargetDialect) -> str:
    emitted = (
        emit_postgres_sql(script_ir)
        if dialect is WindowTargetDialect.POSTGRESQL
        else emit_mysql_sql(script_ir)
    )
    assert emitted.diagnostics == () and len(emitted.artifacts) == 1
    return emitted.artifacts[0].sql


def _unsupported_details(
    relation: RelationIR,
    dialect: WindowTargetDialect,
) -> tuple[NamedWindowLoweringStrategy, list[str]]:
    decision = decide_named_window_lowering(relation, dialect)
    assert decision is not None
    return decision.strategy, [
        item.detail
        for item in decision.evidence
        if item.outcome is WindowTargetEvidenceOutcome.UNSUPPORTED
    ]


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
def test_language_named_window_example_falls_back_to_exact_inline_sql(
    connector: str,
    dialect: WindowTargetDialect,
) -> None:
    _definition, script_ir, relation = _compile(
        _source(
            connector=connector,
            selections=(
                "        a = row_number() window ordered\n"
                "        b = row_number() window ordered:\n"
                "            partition by:\n"
                "                category\n"
                "        c = row_number() window per_category\n"
            ),
            declarations=(
                "    window ordered:\n"
                "        order by:\n"
                "            id\n"
                "    window per_category = ordered:\n"
                "        partition by:\n"
                "            category\n"
            ),
        )
    )
    assert _unsupported_details(relation, dialect) == (
        NamedWindowLoweringStrategy.INLINE_EXACT,
        [f"{dialect.value} cannot add PARTITION BY to a copied named base"],
    )
    sql = (
        "SELECT\n"
        '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "a",\n'
        '    ROW_NUMBER() OVER (PARTITION BY "category" ORDER BY "id" ASC) AS "b",\n'
        '    ROW_NUMBER() OVER (PARTITION BY "category" ORDER BY "id" ASC) AS "c"\n'
        'FROM "rows"'
    )
    if dialect is WindowTargetDialect.MYSQL:
        sql = sql.replace('"', "`")
    assert _emit(script_ir, dialect) == sql


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
@pytest.mark.parametrize(
    ("selections", "declarations", "inline", "detail"),
    (
        (
            "        b = row_number() window ordered:\n"
            "            partition by:\n"
            "                category\n",
            "    window ordered:\n        order by:\n            id\n",
            "        b = row_number() window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                id\n",
            "cannot add PARTITION BY to a copied named base",
        ),
        (
            "        a = row_number() window c\n",
            "    window a0:\n"
            "        order by:\n"
            "            id\n"
            "    window b = a0\n"
            "    window c = b:\n"
            "        partition by:\n"
            "            category\n",
            "        a = row_number() window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                id\n",
            "cannot add PARTITION BY to a copied named base",
        ),
        (
            "        a = first_value(value) window framed:\n"
            "            order by:\n"
            "                id\n",
            "    window framed:\n"
            "        partition by:\n"
            "            category\n"
            "        rows between 1 preceding and current row\n",
            "        a = first_value(value) window:\n"
            "            partition by:\n"
            "                category\n"
            "            order by:\n"
            "                id\n"
            "            rows between 1 preceding and current row\n",
            "cannot copy a named base carrying a frame",
        ),
        (
            "        a = first_value(value) window alias\n",
            "    window alias = framed\n"
            "    window framed:\n"
            "        order by:\n"
            "            id\n"
            "        rows between 1 preceding and current row\n",
            "        a = first_value(value) window:\n"
            "            order by:\n"
            "                id\n"
            "            rows between 1 preceding and current row\n",
            "cannot copy a named base carrying a frame",
        ),
    ),
    ids=("use-partition", "chain-partition", "use-copies-frame", "alias-copies-frame"),
)
def test_uncopyable_named_references_fall_back_to_exact_inline_sql(
    connector: str,
    dialect: WindowTargetDialect,
    selections: str,
    declarations: str,
    inline: str,
    detail: str,
) -> None:
    _definition, script_ir, relation = _compile(
        _source(connector=connector, selections=selections, declarations=declarations)
    )
    assert _unsupported_details(relation, dialect) == (
        NamedWindowLoweringStrategy.INLINE_EXACT,
        [f"{dialect.value} {detail}"],
    )
    _definition, inline_ir, _relation = _compile(
        _source(connector=connector, selections=inline, declarations="")
    )
    assert _emit(script_ir, dialect) == _emit(inline_ir, dialect)


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
def test_copyable_named_refinements_and_chains_stay_native(
    connector: str,
    dialect: WindowTargetDialect,
) -> None:
    _definition, script_ir, relation = _compile(
        _source(
            connector=connector,
            selections=(
                "        a = row_number() window ordered\n"
                "        b = first_value(value) window ordered:\n"
                "            rows between 1 preceding and current row\n"
                "        c = row_number() window parted:\n"
                "            order by:\n"
                "                id\n"
                "        d = last_value(value) window framed\n"
                "        e = rank() window alias\n"
            ),
            declarations=(
                "    window ordered:\n"
                "        order by:\n"
                "            id\n"
                "    window parted:\n"
                "        partition by:\n"
                "            category\n"
                "    window child = parted:\n"
                "        order by:\n"
                "            id desc\n"
                "    window alias = child\n"
                "    window framed = ordered:\n"
                "        rows current row\n"
                "    window unused = ordered:\n"
                "        partition by:\n"
                "            category\n"
            ),
        )
    )
    native, exclusion, quote = (
        (NamedWindowLoweringStrategy.NATIVE_REORDER, " EXCLUDE NO OTHERS", '"')
        if dialect is WindowTargetDialect.POSTGRESQL
        else (NamedWindowLoweringStrategy.NATIVE_PRESERVE, "", "`")
    )
    assert _unsupported_details(relation, dialect) == (native, [])
    sql = (
        "SELECT\n"
        '    ROW_NUMBER() OVER "ordered" AS "a",\n'
        '    FIRST_VALUE("value") OVER ("ordered" ROWS BETWEEN 1 PRECEDING AND '
        f'CURRENT ROW{exclusion}) AS "b",\n'
        '    ROW_NUMBER() OVER ("parted" ORDER BY "id" ASC) AS "c",\n'
        '    LAST_VALUE("value") OVER "framed" AS "d",\n'
        '    RANK() OVER "alias" AS "e"\n'
        'FROM "rows"\n'
        "WINDOW\n"
        '    "ordered" AS (ORDER BY "id" ASC),\n'
        '    "parted" AS (PARTITION BY "category"),\n'
        '    "child" AS ("parted" ORDER BY "id" DESC),\n'
        '    "alias" AS ("child"),\n'
        f'    "framed" AS ("ordered" ROWS CURRENT ROW{exclusion})'
    )
    assert _emit(script_ir, dialect) == sql.replace('"', quote)


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
@pytest.mark.parametrize(
    "copies",
    (
        "    window child = base\n",
        "    window child = mid\n    window mid = base\n",
    ),
    ids=("direct", "through-alias"),
)
def test_copy_adding_order_to_an_ordered_base_falls_back_inline(
    connector: str,
    dialect: WindowTargetDialect,
    copies: str,
) -> None:
    # Semantic composition rejects this shape; the target rule holds for any IR,
    # including a copied alias whose ORDER BY comes only from its own base.
    _definition, _script_ir, relation = _compile(
        _source(
            connector=connector,
            selections="        result = row_number() window child\n",
            declarations=(
                f"{copies}    window base:\n        order by:\n            id\n"
            ),
        )
    )
    child, *rest = relation.named_windows
    ordered_child = replace(
        child,
        local_spec=replace(child.local_spec, order_by=rest[-1].local_spec.order_by),
    )
    assert _unsupported_details(
        replace(relation, named_windows=(ordered_child, *rest)),
        dialect,
    ) == (
        NamedWindowLoweringStrategy.INLINE_EXACT,
        [f"{dialect.value} cannot add ORDER BY to an ordered named base"],
    )


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
def test_an_unordered_base_cycle_fails_closed(
    connector: str,
    dialect: WindowTargetDialect,
) -> None:
    # Semantic composition rejects cycles, but relation IR admits a two-node one;
    # the ORDER lookup through its bases must raise instead of looping.
    _definition, _script_ir, relation = _compile(
        _source(
            connector=connector,
            selections=(
                "        result = row_number() window a:\n"
                "            order by:\n"
                "                id\n"
            ),
            declarations=(
                "    window a = b\n"
                "    window b:\n"
                "        partition by:\n"
                "            category\n"
            ),
        )
    )
    a, b = relation.named_windows
    cyclic_b = replace(
        b,
        base=NamedWindowBaseIR("a", a.occurrence),
        local_spec=replace(b.local_spec, partition_by=()),
    )
    with pytest.raises(ValueError, match="no topological order"):
        decide_named_window_lowering(
            replace(relation, named_windows=(a, cyclic_b)), dialect
        )


@pytest.mark.parametrize(("connector", "dialect"), _DIALECTS)
def test_alias_chain_deeper_than_the_recursion_limit_stays_native(
    connector: str,
    dialect: WindowTargetDialect,
) -> None:
    depth = 1200
    _definition, script_ir, relation = _compile(
        _source(
            connector=connector,
            selections=f"        result = row_number() window w{depth}\n",
            declarations="    window w0:\n        order by:\n            id\n"
            + "".join(f"    window w{i} = w{i - 1}\n" for i in range(1, depth + 1)),
        )
    )
    native, quote = (
        (NamedWindowLoweringStrategy.NATIVE_REORDER, '"')
        if dialect is WindowTargetDialect.POSTGRESQL
        else (NamedWindowLoweringStrategy.NATIVE_PRESERVE, "`")
    )
    assert _unsupported_details(relation, dialect) == (native, [])
    assert _emit(script_ir, dialect).endswith(
        f'\n    "w{depth}" AS ("w{depth - 1}")'.replace('"', quote)
    )


def test_named_ir_preserves_declarations_uses_and_no_target_strategy() -> None:
    _definition, _script_ir, relation = _compile(
        _source(
            selections=(
                "        direct = row_number() window ordered\n"
                "        extended = row_number() window root:\n"
                "            order by:\n"
                "                id\n"
            ),
            declarations=(
                "    window root\n"
                "    window ordered:\n"
                "        order by:\n"
                "            value\n"
            ),
        )
    )
    assert tuple(item.name for item in relation.named_windows) == (
        "root",
        "ordered",
    )
    direct, extended = _window_calls(relation)
    assert direct.named_use is not None and extended.named_use is not None
    assert direct.named_use.occurrence.kind.value == "named_direct"
    assert extended.named_use.occurrence.kind.value == "named_extended"
    assert direct.named_use.target != extended.named_use.target
    assert not direct.named_use.local_spec.has_components
    assert extended.named_use.local_spec.has_components
    assert "strategy" not in {item.name for item in fields(RelationIR)}
    assert "strategy" not in {item.name for item in fields(WindowCallIR)}


def test_target_failure_keeps_project_lineage_and_semantic_provenance(
    tmp_path: Path,
) -> None:
    source = _source(
        selections=("        result = first_value(value) ignore nulls window framed\n"),
        declarations=(
            "    window unused:\n"
            "        order by:\n"
            "            value\n"
            "    window framed = base\n"
            "    window base:\n"
            "        partition by:\n"
            "            category\n"
            "        order by:\n"
            "            id\n"
            "        rows current row exclude ties\n"
        ),
    )
    definition, script_ir, relation_ir = _compile(source)
    decision = decide_named_window_lowering(
        relation_ir,
        WindowTargetDialect.POSTGRESQL,
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NOT_LOWERABLE
    assert any(
        item.kind is WindowTargetEvidenceKind.NULL_TREATMENT
        and item.outcome is WindowTargetEvidenceOutcome.UNSUPPORTED
        for item in decision.inline_decisions[0].evidence
    )
    emitted = emit_postgres_sql(script_ir)
    assert not emitted.artifacts
    assert [item.code for item in emitted.diagnostics] == ["PIE-B1000"]

    _parsed, project = project_upstream._semantic_project(
        tmp_path / "project",
        {"main.pietto": source},
    )
    project_relation = project_upstream._relation(project, "main.pietto", "result")
    output = project_relation.window_outputs[0]
    assert output.status is ProjectModuleCandidateBucketStatus.CONCRETE
    assert type(output.analysis) is WindowExpressionAnalysis
    assert output.analysis.authored_expression is output.item.expression
    assert output.project_fact is not None
    _flat_parsed, flat_project = project_upstream._semantic_project(
        tmp_path / "flat-project",
        {"main.pietto": source},
        schema_version=1,
    )
    assert flat_project.model is not None
    flat_definition = next(
        definition
        for parsed_input in flat_project.model.inputs
        for definition in parsed_input.script.definitions
        if type(definition) is QueryDef and definition.name == "result"
    )
    regular_facts = flat_project.model.relation_window_result_facts[flat_definition]
    assert regular_facts["result"].semantic_provenance.use_kind is (
        WindowUseKind.NAMED_DIRECT
    )
    provenance = output.project_fact.semantic_provenance
    assert type(provenance) is WindowSemanticProvenance
    assert provenance.use_kind is WindowUseKind.NAMED_DIRECT
    assert provenance.named_target is not None
    assert provenance.partition_origin is WindowComponentOrigin.INHERITED
    assert provenance.order_origin is WindowComponentOrigin.INHERITED
    assert provenance.frame_origin is WindowComponentOrigin.INHERITED
    assert provenance.null_treatment is WindowNullTreatment.IGNORE_NULLS
    assert provenance.null_treatment_is_explicit
    assert tuple(
        occurrence.role for occurrence in output.project_fact.dependency_occurrences
    ) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    declaration = cast(QueryDef, definition).named_windows[2]
    assert declaration.spec is not None
    partition_location = output.project_fact.dependency_occurrences[1].location
    order_location = output.project_fact.dependency_occurrences[2].location
    assert partition_location.line == declaration.spec.partition_by[0].span.line
    assert order_location.line == declaration.spec.order_by[0].expression.span.line

    snapshot = graph_upstream._snapshot(tmp_path / "graph", source.encode())
    assert tuple(item.name for item in snapshot.named_windows) == (
        "unused",
        "framed",
        "base",
    )
    assert len(snapshot.window_semantic_provenance) == 1
    assert snapshot.window_semantic_provenance[0].named_target is not None
    inspection = _inspect_package_graph(snapshot)
    named_records = tuple(
        item
        for item in inspection.records
        if item.kind is PackageGraphInspectionRecordKind.NAMED_WINDOW
    )
    semantic_records = tuple(
        item
        for item in inspection.records
        if item.kind is PackageGraphInspectionRecordKind.WINDOW_SEMANTIC
    )
    assert len(named_records) == 3
    assert len(semantic_records) == 1
    assert any(
        link.kind is PackageGraphInspectionLinkKind.NAMED_WINDOW_BASE
        for link in inspection.links
    )
    assert any(
        link.kind is PackageGraphInspectionLinkKind.WINDOW_NAMED_TARGET
        for link in inspection.links
    )
    assert not any(
        occurrence.role.value in {"frame", "exclude", "null_treatment", "nth_direction"}
        for occurrence in output.project_fact.dependency_occurrences
    )


@pytest.mark.parametrize(
    ("connector", "dialect", "call", "frame", "evidence_kind"),
    (
        (
            "postgres.table",
            WindowTargetDialect.POSTGRESQL,
            "nth_value(value, 2) from last",
            None,
            WindowTargetEvidenceKind.NTH_DIRECTION,
        ),
        (
            "postgres.table",
            WindowTargetDialect.POSTGRESQL,
            "first_value(value)",
            "range 1 preceding",
            WindowTargetEvidenceKind.FRAME_SHAPE,
        ),
        (
            "mysql.table",
            WindowTargetDialect.MYSQL,
            "first_value(value)",
            "groups current row",
            WindowTargetEvidenceKind.FRAME_SHAPE,
        ),
        (
            "mysql.table",
            WindowTargetDialect.MYSQL,
            "first_value(value)",
            "rows current row exclude no others",
            WindowTargetEvidenceKind.EXCLUSION,
        ),
        (
            "mysql.table",
            WindowTargetDialect.MYSQL,
            "first_value(value) ignore nulls",
            None,
            WindowTargetEvidenceKind.NULL_TREATMENT,
        ),
        (
            "mysql.table",
            WindowTargetDialect.MYSQL,
            "nth_value(value, 2) from last",
            None,
            WindowTargetEvidenceKind.NTH_DIRECTION,
        ),
        (
            "mysql.table",
            WindowTargetDialect.MYSQL,
            "first_value(value)",
            "range 1 preceding",
            WindowTargetEvidenceKind.FRAME_SHAPE,
        ),
    ),
)
def test_named_paths_cannot_bypass_slice9_target_restrictions(
    connector: str,
    dialect: WindowTargetDialect,
    call: str,
    frame: str | None,
    evidence_kind: WindowTargetEvidenceKind,
) -> None:
    frame_source = "" if frame is None else f"        {frame}\n"
    _definition, script_ir, relation = _compile(
        _source(
            connector=connector,
            selections=f"        result = {call} window restricted\n",
            declarations=(
                "    window restricted:\n"
                "        order by:\n"
                "            id\n"
                f"{frame_source}"
            ),
        )
    )
    decision = decide_named_window_lowering(relation, dialect)
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NOT_LOWERABLE
    assert any(
        item.kind is evidence_kind
        and item.outcome is WindowTargetEvidenceOutcome.UNSUPPORTED
        for item in decision.inline_decisions[0].evidence
    )
    emitted = (
        emit_postgres_sql(script_ir)
        if dialect is WindowTargetDialect.POSTGRESQL
        else emit_mysql_sql(script_ir)
    )
    assert not emitted.artifacts
    assert [item.code for item in emitted.diagnostics] == ["PIE-B1000"]


def test_one_unsupported_named_use_blocks_the_whole_relation_strategy() -> None:
    _definition, script_ir, relation = _compile(
        _source(
            selections=(
                "        safe = row_number() window ordered\n"
                "        blocked = nth_value(value, 2) from last window ordered\n"
            ),
            declarations=("    window ordered:\n        order by:\n            id\n"),
        )
    )
    decision = decide_named_window_lowering(
        relation,
        WindowTargetDialect.POSTGRESQL,
    )
    assert decision is not None
    assert len(decision.inline_decisions) == 2
    assert decision.strategy is NamedWindowLoweringStrategy.NOT_LOWERABLE
    emitted = emit_postgres_sql(script_ir)
    assert not emitted.artifacts
    assert [item.code for item in emitted.diagnostics] == ["PIE-B1000"]


def test_semantic_model_retains_exact_namespace_and_named_analysis() -> None:
    source = _source(
        selections="        result = row_number() window ordered\n",
        declarations=("    window ordered:\n        order by:\n            id\n"),
    )
    parsed = parse_source(source, path="slice10.pietto")
    assert parsed.ast is not None
    definition = cast(QueryDef, parsed.ast.definitions[-1])
    expression = cast(WindowExpr, definition.select_items[0].expression)
    semantic = analyze(parsed.ast)
    namespace = semantic.model.named_window_namespaces[definition]
    analysis = semantic.model.window_expression_analyses[expression]
    assert type(namespace) is ResolvedNamedWindowNamespace
    assert analysis.resolved_named_use is not None
    assert analysis.resolved_named_use.composed.namespace is namespace
    assert analysis.authored_expression is expression
