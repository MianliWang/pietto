from __future__ import annotations

from pathlib import Path
from typing import cast


from pietto._project.package_graph_inspection import (
    PackageGraphInspectionLink,
    PackageGraphInspectionRecord,
)
from pietto.ast_nodes import QueryDef, Span
from pietto.errors import SourceLocation
from pietto.ir import build_ir
from pietto.ir.model import (
    RelationIR,
    WindowCallIR,
)
from pietto.parser_api import parse_file
from pietto.semantic import SemanticResult, analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.window_strategy import (
    NamedWindowLoweringDecision,
    WindowTargetDialect,
    decide_named_window_lowering,
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
