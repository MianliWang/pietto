from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import cast

from _pietto_project_explain_scenarios import _CLI_PAIR_CODE, _run_cli_pair
import test_phase54_semantic_fact_preservation as project_upstream
import test_phase59_slice8_semantic_field_lineage_integration as graph_upstream

from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.package_graph import (
    PackageGraphFieldRef,
    PackageGraphNamedWindowRef,
    PackageGraphWindowSemanticProvenance,
    _package_graph_direct_provenance_steps,
)
from pietto._project.package_graph_inspection import (
    PackageGraphInspectionLink,
    PackageGraphInspectionLinkKind,
    PackageGraphInspectionRecord,
    PackageGraphInspectionRecordKind,
    PackageGraphPureStatus,
    _evaluate_package_graph_inspection,
    _inspect_package_graph,
)
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowSemanticProvenance,
)
from pietto.ast_nodes import QueryDef, Span, WindowExpr, WindowUseKind
from pietto.errors import SourceLocation
from pietto.ir import build_ir
from pietto.ir.model import (
    RelationIR,
    WindowCallIR,
    WindowFrameExclusionIR,
    WindowFrameUnitIR,
    WindowNthDirectionIR,
    WindowNullTreatmentIR,
    WindowUseKindIR,
)
from pietto.parser_api import parse_file
from pietto.semantic import SemanticResult, analyze
from pietto.semantic.window_semantics import (
    ResolvedNamedWindowNamespace,
    WindowComponentOrigin,
    WindowExpressionAnalysis,
    WindowFrameApplicability,
    WindowFrameExclusion,
    WindowFrameUnit,
    WindowNthDirection,
    WindowNullTreatment,
)
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.window_strategy import (
    NamedWindowLoweringDecision,
    NamedWindowLoweringStrategy,
    WindowTargetDialect,
    decide_named_window_lowering,
    window_runtime_semantically_equal,
)


PREFIX = """shape Row:
    id: Int not null
    value: Int nullable
    category: Text nullable
"""

POSTGRES_NATIVE = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    group by:
        category
    select:
        group_name = category
        total = sum(value)
        ranking = row_number() window child
        first = first_value(group_name) respect nulls window child
        nth = nth_value(group_name, 2) from first respect nulls window child
        previous = lag(group_name, 1, group_name) respect nulls window child
    window child = base
    window unused:
        order by:
            id
    window base:
        partition by:
            group_name
        order by:
            total desc
    satisfying:
        total > 0
    order by:
        ranking
    limit 5
"""
)

POSTGRES_FALLBACK = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window derived
    window derived = framed
    window framed:
        partition by:
            category
        order by:
            id desc
        groups between 1 preceding and current row exclude ties
"""
)

POSTGRES_FALLBACK_INLINE = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window:
            partition by:
                category
            order by:
                id desc
            groups between 1 preceding and current row exclude ties
"""
)

POSTGRES_FRAMES = (
    PREFIX
    + """source rows: Row is postgres.table("rows")
query result:
    from rows
    select:
        rows_value = last_value(value) respect nulls window:
            order by:
                id
            rows between 1 preceding and current row exclude current row
        range_value = first_value(value) window:
            order by:
                id
            range current row exclude group
"""
)

MYSQL_NATIVE = (
    PREFIX
    + """source rows: Row is mysql.table("rows")
query result:
    from rows
    select:
        result = nth_value(value, 2) from first respect nulls window child:
            rows between 1 preceding and current row
    window child = base
    window unused:
        order by:
            value
    window base:
        partition by:
            category
        order by:
            id desc
"""
)

POSTGRES_NATIVE_SQL = """SELECT
    "category" AS "group_name",
    SUM("value") AS "total",
    ROW_NUMBER() OVER "child" AS "ranking",
    FIRST_VALUE("category") OVER ("child" RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS) AS "first",
    NTH_VALUE("category", 2) OVER ("child" RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS) AS "nth",
    LAG("category", 1, "category") OVER "child" AS "previous"
FROM "rows"
GROUP BY
    "category"
HAVING
    SUM("value") > 0
WINDOW
    "base" AS (PARTITION BY "category" ORDER BY SUM("value") DESC),
    "child" AS ("base")
ORDER BY
    "ranking" ASC
LIMIT 5"""

POSTGRES_FALLBACK_SQL = '''SELECT
    NTH_VALUE("value", 2) OVER (PARTITION BY "category" ORDER BY "id" DESC GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE TIES) AS "result"
FROM "rows"'''

POSTGRES_FRAMES_SQL = '''SELECT
    LAST_VALUE("value") OVER (ORDER BY "id" ASC ROWS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE CURRENT ROW) AS "rows_value",
    FIRST_VALUE("value") OVER (ORDER BY "id" ASC RANGE CURRENT ROW EXCLUDE GROUP) AS "range_value"
FROM "rows"'''

MYSQL_NATIVE_SQL = """SELECT
    NTH_VALUE(`value`, 2) FROM FIRST RESPECT NULLS OVER (`child` ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS `result`
FROM `rows`
WINDOW
    `child` AS (`base`),
    `base` AS (PARTITION BY `category` ORDER BY `id` DESC)"""


def _write_source(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


def _compile_authored(
    path: Path,
    dialect: WindowTargetDialect,
) -> tuple[
    QueryDef,
    SemanticResult,
    RelationIR,
    str,
    NamedWindowLoweringDecision | None,
]:
    parsed = parse_file(path)
    assert parsed.ast is not None and parsed.diagnostics == ()
    definition = next(
        definition
        for definition in parsed.ast.definitions
        if type(definition) is QueryDef
    )
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    relation = next(
        definition
        for definition in lowered.ir.definitions
        if type(definition) is RelationIR
    )
    emitted = (
        emit_postgres_sql(lowered.ir)
        if dialect is WindowTargetDialect.POSTGRESQL
        else emit_mysql_sql(lowered.ir)
    )
    assert emitted.diagnostics == () and len(emitted.artifacts) == 1
    return (
        definition,
        semantic,
        relation,
        emitted.artifacts[0].sql,
        decide_named_window_lowering(relation, dialect),
    )


def _window_calls(relation: RelationIR) -> tuple[WindowCallIR, ...]:
    return tuple(
        cast(WindowCallIR, projection.expression)
        for projection in relation.projections
        if type(projection.expression) is WindowCallIR
    )


def _inspection_value(
    item: PackageGraphInspectionRecord | PackageGraphInspectionLink,
    name: str,
) -> object:
    matches = tuple(field.value for field in item.fields if field.name == name)
    assert len(matches) == 1
    return matches[0]


def _source_location(span: Span) -> SourceLocation:
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def test_e2e_authority_starts_from_authored_files_and_production_entry_points() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden_constructors = {
        "WindowCallIR",
        "RelationIR",
        "NamedWindowLoweringDecision",
        "WindowResultProjectFact",
        "PackageGraphSnapshot",
        "PackageGraphInspectionRecord",
        "PackageGraphInspectionLink",
    }
    called = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert forbidden_constructors.isdisjoint(called)
    assert "from pietto.cli import main" in _CLI_PAIR_CODE
    assert "main(arguments)" in _CLI_PAIR_CODE

    configured = inspect.getsource(project_upstream._configured_project)
    semantic = inspect.getsource(project_upstream._semantic_project)
    snapshot = inspect.getsource(graph_upstream._snapshot)
    assert all(token in configured for token in ("pietto.toml", "write_text"))
    assert all(
        token in semantic
        for token in (
            "_configured_project",
            "check_project_parse_only",
            "build_empty_project_semantic_result",
        )
    )
    assert all(
        token in snapshot
        for token in (
            "_write_package",
            "_build_package_inspection_fact_set",
            "_semantic_project",
            "_build_package_graph",
        )
    )
    assert "PackageGraphSnapshot(" not in snapshot


def test_postgresql_native_reorder_is_proved_from_real_authored_source(
    tmp_path: Path,
) -> None:
    _definition, _semantic, relation, sql, decision = _compile_authored(
        _write_source(tmp_path, "native.pietto", POSTGRES_NATIVE),
        WindowTargetDialect.POSTGRESQL,
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NATIVE_REORDER
    assert tuple(item.name for item in decision.reachable_declarations) == (
        "child",
        "base",
    )
    assert tuple(item.name for item in decision.emission_declarations) == (
        "base",
        "child",
    )
    assert sql == POSTGRES_NATIVE_SQL
    assert "unused" not in sql
    assert sql.index("\nHAVING\n") < sql.index("\nWINDOW\n")
    assert sql.index("\nWINDOW\n") < sql.index("\nORDER BY\n")
    assert sql.index("\nORDER BY\n") < sql.index("\nLIMIT 5")

    ranking, first, nth, previous = _window_calls(relation)
    assert all(
        call.named_use is not None
        and call.named_use.occurrence.kind is WindowUseKindIR.NAMED_DIRECT
        for call in (ranking, first, nth, previous)
    )
    assert ranking.spec.frame is None
    assert first.spec.frame is not None and not first.spec.frame.frame_is_explicit
    assert first.spec.frame.unit is WindowFrameUnitIR.RANGE
    assert first.spec.frame.exclusion is WindowFrameExclusionIR.NO_OTHERS
    assert nth.spec.frame == first.spec.frame


def test_postgresql_exact_inline_fallback_matches_independent_authored_source(
    tmp_path: Path,
) -> None:
    named_definition, named_semantic, named_relation, named_sql, decision = (
        _compile_authored(
            _write_source(tmp_path, "named.pietto", POSTGRES_FALLBACK),
            WindowTargetDialect.POSTGRESQL,
        )
    )
    inline_definition, inline_semantic, inline_relation, inline_sql, inline_decision = (
        _compile_authored(
            _write_source(tmp_path, "inline.pietto", POSTGRES_FALLBACK_INLINE),
            WindowTargetDialect.POSTGRESQL,
        )
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.INLINE_EXACT
    assert inline_decision is None
    assert named_sql == inline_sql == POSTGRES_FALLBACK_SQL
    assert "\nWINDOW\n" not in named_sql

    named_expression = cast(WindowExpr, named_definition.select_items[0].expression)
    inline_expression = cast(WindowExpr, inline_definition.select_items[0].expression)
    named_analysis = named_semantic.model.window_expression_analyses[named_expression]
    inline_analysis = inline_semantic.model.window_expression_analyses[
        inline_expression
    ]
    named_call = _window_calls(named_relation)[0]
    inline_call = _window_calls(inline_relation)[0]
    assert named_analysis.authored_expression is named_expression
    assert inline_analysis.authored_expression is inline_expression
    assert named_analysis.resolved_named_use is not None
    assert inline_analysis.resolved_named_use is None
    assert (
        named_analysis.semantic_fact.occurrence
        != inline_analysis.semantic_fact.occurrence
    )
    assert named_call.named_use is not None and inline_call.named_use is None
    assert named_call != inline_call
    assert window_runtime_semantically_equal(named_call, inline_call)
    assert named_call.null_treatment is WindowNullTreatmentIR.RESPECT_NULLS
    assert named_call.null_treatment_is_explicit
    assert named_call.nth_direction is WindowNthDirectionIR.FROM_FIRST
    assert named_call.nth_direction_is_explicit


def test_postgresql_authored_frame_corpus_reaches_analysis_ir_and_exact_sql(
    tmp_path: Path,
) -> None:
    _a_definition, _a_semantic, a_relation, _a_sql, _a_decision = _compile_authored(
        _write_source(tmp_path, "default.pietto", POSTGRES_NATIVE),
        WindowTargetDialect.POSTGRESQL,
    )
    b_definition, b_semantic, b_relation, _b_sql, _b_decision = _compile_authored(
        _write_source(tmp_path, "groups.pietto", POSTGRES_FALLBACK),
        WindowTargetDialect.POSTGRESQL,
    )
    c_definition, c_semantic, c_relation, c_sql, c_decision = _compile_authored(
        _write_source(tmp_path, "rows-range.pietto", POSTGRES_FRAMES),
        WindowTargetDialect.POSTGRESQL,
    )
    assert c_decision is None
    assert c_sql == POSTGRES_FRAMES_SQL

    frames = tuple(
        call.spec.frame
        for call in (
            _window_calls(a_relation)[1],
            _window_calls(b_relation)[0],
            *_window_calls(c_relation),
        )
    )
    assert all(frame is not None for frame in frames)
    concrete_frames = tuple(frame for frame in frames if frame is not None)
    assert {frame.unit for frame in concrete_frames} == {
        WindowFrameUnitIR.ROWS,
        WindowFrameUnitIR.RANGE,
        WindowFrameUnitIR.GROUPS,
    }
    assert {frame.exclusion for frame in concrete_frames} == {
        WindowFrameExclusionIR.NO_OTHERS,
        WindowFrameExclusionIR.CURRENT_ROW,
        WindowFrameExclusionIR.GROUP,
        WindowFrameExclusionIR.TIES,
    }
    for definition, semantic in (
        (b_definition, b_semantic),
        (c_definition, c_semantic),
    ):
        for item in definition.select_items:
            expression = cast(WindowExpr, item.expression)
            analysis = semantic.model.window_expression_analyses[expression]
            assert type(analysis) is WindowExpressionAnalysis
            assert analysis.authored_expression is expression
            assert analysis.validated_specification.resolved.frame.applicability is (
                WindowFrameApplicability.APPLICABLE
            )


def test_mysql_native_preserve_is_proved_from_real_authored_source(
    tmp_path: Path,
) -> None:
    _definition, _semantic, relation, sql, decision = _compile_authored(
        _write_source(tmp_path, "mysql.pietto", MYSQL_NATIVE),
        WindowTargetDialect.MYSQL,
    )
    assert decision is not None
    assert decision.strategy is NamedWindowLoweringStrategy.NATIVE_PRESERVE
    assert tuple(item.name for item in relation.named_windows) == (
        "child",
        "unused",
        "base",
    )
    assert tuple(item.name for item in decision.reachable_declarations) == (
        "child",
        "base",
    )
    assert tuple(item.name for item in decision.emission_declarations) == (
        "child",
        "base",
    )
    assert sql == MYSQL_NATIVE_SQL
    assert "unused" not in sql
    call = _window_calls(relation)[0]
    assert call.named_use is not None
    assert call.named_use.occurrence.kind is WindowUseKindIR.NAMED_EXTENDED
    assert call.null_treatment is WindowNullTreatmentIR.RESPECT_NULLS
    assert call.null_treatment_is_explicit
    assert call.nth_direction is WindowNthDirectionIR.FROM_FIRST
    assert call.nth_direction_is_explicit


def test_real_cli_pair_emits_exact_postgresql_and_mysql_sql(tmp_path: Path) -> None:
    _write_source(tmp_path, "postgres.pietto", POSTGRES_NATIVE)
    _write_source(tmp_path, "mysql.pietto", MYSQL_NATIVE)
    postgres, mysql = _run_cli_pair(
        ("emit-sql", "postgres.pietto", "--dialect", "postgres"),
        ("emit-sql", "mysql.pietto", "--dialect", "mysql"),
        tmp_path,
    )
    assert (postgres.returncode, postgres.stdout, postgres.stderr) == (
        0,
        f"{POSTGRES_NATIVE_SQL}\n".encode(),
        b"",
    )
    assert (mysql.returncode, mysql.stdout, mysql.stderr) == (
        0,
        f"{MYSQL_NATIVE_SQL}\n".encode(),
        b"",
    )


def test_real_project_lineage_and_private_inspection_retain_authorship(
    tmp_path: Path,
) -> None:
    _parsed, project = project_upstream._semantic_project(
        tmp_path / "project",
        {"main.pietto": POSTGRES_NATIVE},
    )
    relation = project_upstream._relation(project, "main.pietto", "result")
    definition = cast(QueryDef, relation.owner.definition)
    namespace = relation.named_window_namespace
    assert type(namespace) is ResolvedNamedWindowNamespace
    child = next(
        template
        for template in namespace.templates
        if template.declaration.name == "child"
    )
    base = next(item for item in definition.named_windows if item.name == "base")
    assert base.spec is not None
    partition_location = _source_location(base.spec.partition_by[0].span)
    order_location = _source_location(base.spec.order_by[0].expression.span)

    outputs = {output.output_name: output for output in relation.window_outputs}
    assert tuple(outputs) == ("ranking", "first", "nth", "previous")
    for output in outputs.values():
        assert output.status is ProjectModuleCandidateBucketStatus.CONCRETE
        assert type(output.analysis) is WindowExpressionAnalysis
        assert output.analysis.authored_expression is output.item.expression
        assert output.analysis.resolved_named_use is not None
        assert output.analysis.resolved_named_use.composed.namespace is namespace
        assert output.project_fact is not None
        assert output.project_fact.analysis is output.analysis
        provenance = output.project_fact.semantic_provenance
        assert type(provenance) is WindowSemanticProvenance
        assert provenance.analysis is output.analysis
        assert provenance.use_kind is WindowUseKind.NAMED_DIRECT
        assert provenance.named_target is child.occurrence
        assert provenance.partition_origin is WindowComponentOrigin.INHERITED
        assert provenance.order_origin is WindowComponentOrigin.INHERITED
        occurrences = output.project_fact.dependency_occurrences
        assert (
            next(
                item.location
                for item in occurrences
                if item.role is WindowDependencyRole.WINDOW_PARTITION
            )
            == partition_location
        )
        assert (
            next(
                item.location
                for item in occurrences
                if item.role is WindowDependencyRole.WINDOW_ORDER
            )
            == order_location
        )

    ranking = outputs["ranking"].project_fact
    first = outputs["first"].project_fact
    nth = outputs["nth"].project_fact
    previous = outputs["previous"].project_fact
    assert ranking is not None and first is not None and nth is not None
    assert previous is not None
    assert tuple(item.role for item in ranking.dependency_occurrences) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.role for item in first.dependency_occurrences) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.role for item in nth.dependency_occurrences) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.role for item in previous.dependency_occurrences) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    first_provenance = first.semantic_provenance
    assert first_provenance.frame_origin is WindowComponentOrigin.EFFECTIVE_DEFAULT
    assert first_provenance.frame_applicability is WindowFrameApplicability.APPLICABLE
    assert first_provenance.frame_unit is WindowFrameUnit.RANGE
    assert first_provenance.frame_exclusion is WindowFrameExclusion.NO_OTHERS
    assert first_provenance.null_treatment is WindowNullTreatment.RESPECT_NULLS
    assert first_provenance.null_treatment_is_explicit
    assert first_provenance.nth_direction is None
    assert not first_provenance.nth_direction_is_explicit
    nth_provenance = nth.semantic_provenance
    assert nth_provenance.frame_origin is WindowComponentOrigin.EFFECTIVE_DEFAULT
    assert nth_provenance.frame_unit is WindowFrameUnit.RANGE
    assert nth_provenance.frame_exclusion is WindowFrameExclusion.NO_OTHERS
    assert nth_provenance.null_treatment is WindowNullTreatment.RESPECT_NULLS
    assert nth_provenance.null_treatment_is_explicit
    assert nth_provenance.nth_direction is WindowNthDirection.FROM_FIRST
    assert nth_provenance.nth_direction_is_explicit

    snapshot = graph_upstream._snapshot(
        tmp_path / "graph-first", POSTGRES_NATIVE.encode()
    )
    second_snapshot = graph_upstream._snapshot(
        tmp_path / "graph-second", POSTGRES_NATIVE.encode()
    )
    assert snapshot.scope is not second_snapshot.scope
    assert snapshot.named_windows[0].ref != second_snapshot.named_windows[0].ref
    assert tuple(item.name for item in snapshot.named_windows) == (
        "child",
        "unused",
        "base",
    )
    assert tuple(item.ref.position for item in snapshot.named_windows) == (0, 1, 2)
    assert all(
        type(item.ref) is PackageGraphNamedWindowRef
        and item.ref.declaration
        == snapshot.window_semantic_provenance[0].output.declaration
        for item in snapshot.named_windows
    )
    assert len(snapshot.window_semantic_provenance) == 4
    assert all(
        type(item) is PackageGraphWindowSemanticProvenance
        and type(item.output) is PackageGraphFieldRef
        and snapshot.field(item.output).ref == item.output
        for item in snapshot.window_semantic_provenance
    )
    assert not any(
        type(step.witness) is PackageGraphWindowSemanticProvenance
        for step in _package_graph_direct_provenance_steps(snapshot)
    )

    first_inspection = _inspect_package_graph(snapshot)
    second_inspection = _inspect_package_graph(second_snapshot)
    assert first_inspection == second_inspection
    assert first_inspection.canonical_bytes == second_inspection.canonical_bytes
    assert (
        _evaluate_package_graph_inspection(first_inspection).status
        is PackageGraphPureStatus.OK
    )
    named_records = tuple(
        record
        for record in first_inspection.records
        if record.kind is PackageGraphInspectionRecordKind.NAMED_WINDOW
    )
    semantic_records = tuple(
        record
        for record in first_inspection.records
        if record.kind is PackageGraphInspectionRecordKind.WINDOW_SEMANTIC
    )
    assert tuple(_inspection_value(record, "name") for record in named_records) == (
        "child",
        "unused",
        "base",
    )
    assert tuple(
        _inspection_value(record, "function") for record in semantic_records
    ) == ("row_number", "first_value", "nth_value", "lag")
    records = {record.ref: record for record in first_inspection.records}
    base_links = tuple(
        link
        for link in first_inspection.links
        if link.kind is PackageGraphInspectionLinkKind.NAMED_WINDOW_BASE
    )
    use_links = tuple(
        link
        for link in first_inspection.links
        if link.kind is PackageGraphInspectionLinkKind.WINDOW_NAMED_TARGET
    )
    assert len(base_links) == 1
    assert _inspection_value(records[base_links[0].source], "name") == "child"
    assert _inspection_value(records[base_links[0].target], "name") == "base"
    assert _inspection_value(base_links[0], "base_spelling") == "base"
    assert len(use_links) == 4
    assert all(
        _inspection_value(records[link.target], "name") == "child"
        and _inspection_value(records[link.source], "name")
        in {"ranking", "first", "nth", "previous"}
        and _inspection_value(link, "reference_spelling") == "child"
        and _inspection_value(link, "use_kind") == "named_direct"
        for link in use_links
    )
