import pytest
from typing import cast
from dataclasses import fields

from pietto.ir import (
    AggregateCallIR,
    AggregateWindowCallIR,
    CallIR,
    ExpressionIR,
    FieldRefIR,
    RelationIR,
    build_ir,
)
from pietto.ir.model import (
    WindowFrameBoundIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameIR,
    WindowFrameUnitIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.expressions import render_window_components_sql


def test_postgres_emits_an_aggregate_window_with_its_explicit_frame():
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        running = sum(id) window(order by id rows between unbounded preceding and current row)
"""
    postgres_parsed = parse_source(source)
    assert postgres_parsed.ast is not None
    postgres_lowered = build_ir(postgres_parsed.ast, analyze(postgres_parsed.ast).model)
    assert postgres_lowered.ir is not None
    postgres = emit_postgres_sql(postgres_lowered.ir)
    assert (
        'SUM("id") OVER (ORDER BY "id" ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS)'
        in postgres.artifacts[0].sql
    )


def test_named_aggregate_window_preserves_its_inherited_specification():
    parsed = parse_source("""shape Row:
    id: Int
    account: Int
    value: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let recent = window(partition by account order by id)
    select:
        running = sum(value) window recent
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None, lowered.diagnostics
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'SUM("value") OVER "recent"' in sql
    assert '"recent" AS (PARTITION BY "account" ORDER BY "id" ASC)' in sql


def test_postgres_aggregate_windows_reuse_ordinary_count_and_avg_rendering():
    parsed = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    select:
        all_rows = count() window()
        average_id = avg(id) window(order by id)
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'COUNT(*) OVER () AS "all_rows"' in sql
    assert 'AVG(CAST("id" AS double precision)) OVER (ORDER BY "id" ASC)' in sql


def test_named_aggregate_window_with_framed_base_inlines_instead_of_copying_it():
    parsed = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let framed = window(order by id rows between unbounded preceding and current row)
    let child = window framed
    select:
        total = sum(id) window child
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert (
        'SUM("id") OVER (ORDER BY "id" ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS)'
        in sql
    )
    assert "WINDOW" not in sql


_MYSQL_AGGREGATE_WINDOWS = (
    "shape Row:\n"
    "    id: Int\n"
    "    account: Int\n"
    "    score: Float | None\n"
    "    note: Text | None\n"
    'source rows: Row = mysql.table("rows")\n'
    "table before:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "table totals:\n"
    "    from rows\n"
    "    select:\n"
    "        total = sum(id) window()\n"
    "        running = sum(id) window(order by id rows between unbounded preceding and current row)\n"
    "table counts:\n"
    "    from rows\n"
    "    select:\n"
    "        all_rows = count() window(order by id)\n"
    "        notes = count(note) window(partition by account)\n"
    "table moving:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        mean = avg(id) window(order by id rows between 1 preceding and current row)\n"
    "        float_mean = avg(score) window(order by id rows between 1 preceding and 1 following)\n"
    "        float_sum = sum(score) window(order by id rows between 1 preceding and 1 following)\n"
    "        lo = min(score) window(partition by account order by id)\n"
    "        hi = max(id) window(partition by account order by id groups between unbounded preceding and current row)\n"
    "table named:\n"
    "    from rows\n"
    "    let recent = window(partition by account order by id)\n"
    "    select:\n"
    "        running = sum(id) window recent\n"
    "        n = count() window recent\n"
    "table grouped:\n"
    "    from rows\n"
    "    group by account\n"
    "    select:\n"
    "        account\n"
    "        n = count()\n"
    "        running = sum(account) window(order by account)\n"
    "table qualified:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "    qualify:\n"
    "        count() window(partition by account) > 1"
)


def test_mysql_emits_each_aggregate_window_as_postgresql_does():
    parsed = parse_source(_MYSQL_AGGREGATE_WINDOWS + "\n")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    result = emit_mysql_sql(lowered.ir)
    assert result.diagnostics == ()
    assert [(artifact.name, artifact.sql) for artifact in result.artifacts] == [
        (
            "before",
            ("SELECT\n    `id` AS `id`\nFROM `rows`"),
        ),
        (
            "totals",
            (
                "SELECT\n"
                "    SUM(`id`) OVER () AS `total`,\n"
                "    SUM(`id`) OVER (ORDER BY `id` ASC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS `running`\n"
                "FROM `rows`"
            ),
        ),
        (
            "counts",
            (
                "SELECT\n"
                "    COUNT(*) OVER (ORDER BY `id` ASC) AS `all_rows`,\n"
                "    COUNT(`note`) OVER (PARTITION BY `account`) AS `notes`\n"
                "FROM `rows`"
            ),
        ),
        (
            "moving",
            (
                "SELECT\n"
                "    `id` AS `id`,\n"
                "    AVG(CAST(`id` AS DOUBLE)) OVER (ORDER BY `id` ASC ROWS BETWEEN 1 PRECEDING AND CURRENT ROW) AS `mean`,\n"
                "    AVG(`score`) OVER (ORDER BY `id` ASC ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS `float_mean`,\n"
                "    SUM(`score`) OVER (ORDER BY `id` ASC ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING) AS `float_sum`,\n"
                "    MIN(`score`) OVER (PARTITION BY `account` ORDER BY `id` ASC) AS `lo`,\n"
                "    MAX(`id`) OVER (PARTITION BY `account` ORDER BY `id` ASC RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS `hi`\n"
                "FROM `rows`"
            ),
        ),
        (
            "named",
            (
                "SELECT\n"
                "    SUM(`id`) OVER `recent` AS `running`,\n"
                "    COUNT(*) OVER `recent` AS `n`\n"
                "FROM `rows`\n"
                "WINDOW\n"
                "    `recent` AS (PARTITION BY `account` ORDER BY `id` ASC)"
            ),
        ),
        (
            "grouped",
            (
                "SELECT\n"
                "    `account` AS `account`,\n"
                "    COUNT(*) AS `n`,\n"
                "    SUM(`account`) OVER (ORDER BY `account` ASC) AS `running`\n"
                "FROM `rows`\n"
                "GROUP BY\n"
                "    `account`"
            ),
        ),
        (
            "qualified",
            (
                "SELECT\n"
                "    `id`\n"
                "FROM (\n"
                "SELECT\n"
                "    `id` AS `id`,\n"
                "    COUNT(*) OVER (PARTITION BY `account`) AS `__pietto_qualify_0`\n"
                "FROM `rows`\n"
                ") AS `__pietto_qualify`\n"
                "WHERE\n"
                "    `__pietto_qualify_0` > 1"
            ),
        ),
    ]


def test_postgres_carries_aggregate_windows_through_qualify_and_grouped_order_aliases():
    qualify = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table qualified:
    from rows
    select:
        id
    qualify:
        count() window() > 0
""")
    assert qualify.ast is not None
    qualify_lowered = build_ir(qualify.ast, analyze(qualify.ast).model)
    assert qualify_lowered.ir is not None
    qualify_sql = emit_postgres_sql(qualify_lowered.ir).artifacts[0].sql
    assert 'COUNT(*) OVER () AS "__pietto_qualify_0"' in qualify_sql
    assert 'WHERE\n    "__pietto_qualify_0" > 0' in qualify_sql

    grouped = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table grouped:
    from rows
    group by id
    select:
        id
        total = sum(id)
        running = count() window(order by id)
    order by:
        running desc
""")
    assert grouped.ast is not None
    grouped_lowered = build_ir(grouped.ast, analyze(grouped.ast).model)
    assert grouped_lowered.ir is not None
    grouped_sql = emit_postgres_sql(grouped_lowered.ir).artifacts[0].sql
    assert 'COUNT(*) OVER (ORDER BY "id" ASC) AS "running"' in grouped_sql
    assert 'ORDER BY\n    "running" DESC' in grouped_sql


def test_postgres_aggregate_windows_read_completed_grouped_aggregate_outputs():
    parsed = parse_source("""shape Row:
    id: Int
    category: Int
source rows: Row = postgres.table("rows")
table grouped:
    from rows
    group by category
    select:
        category
        total = sum(id)
        summed = sum(total) window(order by total)
        averaged = avg(total) window(order by total)
        counted = count(total) window(order by total)
        smallest = min(total) window(order by total)
        largest = max(total) window(order by total)
        adjusted = sum(total + 1) window(order by total)
    order by:
        summed desc
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'SUM(SUM("id")) OVER (ORDER BY SUM("id") ASC) AS "summed"' in sql
    assert (
        'AVG(CAST(SUM("id") AS double precision)) OVER (ORDER BY SUM("id") ASC) AS "averaged"'
        in sql
    )
    assert 'COUNT(SUM("id")) OVER (ORDER BY SUM("id") ASC) AS "counted"' in sql
    assert 'MIN(SUM("id")) OVER (ORDER BY SUM("id") ASC) AS "smallest"' in sql
    assert 'MAX(SUM("id")) OVER (ORDER BY SUM("id") ASC) AS "largest"' in sql
    assert 'SUM((SUM("id") + 1)) OVER (ORDER BY SUM("id") ASC) AS "adjusted"' in sql


def test_postgres_recursively_carries_grouped_outputs_into_count_transforms():
    parsed = parse_source("""shape Row:
    category: Text
source rows: Row = postgres.table("rows")
table grouped:
    from rows
    group by category
    select:
        k = category
        total = count()
        measured = count(len(k)) window(order by k)
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert (
        'COUNT(length("category")) OVER (ORDER BY "category" ASC) AS "measured"' in sql
    )


def test_postgres_reads_completed_grouped_count_distinct_outputs():
    parsed = parse_source("""shape Row:
    id: Int
    category: Int
source rows: Row = postgres.table("rows")
table grouped:
    from rows
    group by category
    select:
        category
        total = count_distinct(id)
        running = sum(total) window(order by total)
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'SUM(COUNT(DISTINCT "id")) OVER (ORDER BY COUNT(DISTINCT "id") ASC)' in sql


def test_postgres_qualify_windows_read_completed_grouped_outputs():
    parsed = parse_source("""shape Row:
    value: Int
    category: Int
    peer_key: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    group by category, peer_key
    select:
        category
        grouped_peer = peer_key
        total = sum(value)
    qualify:
        sum(total) window(order by grouped_peer) > 6 and first_value(total) window(order by grouped_peer rows current row) > 0 and sum(total + 1) window(order by grouped_peer) > 0
    order by:
        total desc
    limit 2
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'SUM(SUM("value")) OVER (ORDER BY "peer_key" ASC)' in sql
    assert (
        'FIRST_VALUE(SUM("value")) OVER (ORDER BY "peer_key" ASC ROWS CURRENT ROW EXCLUDE NO OTHERS)'
        in sql
    )
    assert 'SUM((SUM("value") + 1)) OVER (ORDER BY "peer_key" ASC)' in sql
    assert 'ORDER BY\n    "__pietto_qualify_3" DESC\nLIMIT 2' in sql


def test_postgres_joined_grouped_qualify_windows_keep_completed_value_identities():
    parsed = parse_source("""shape Row:
    id: Int
    row_key = unique(id)
    label: Text
    amount: Int
source rows: Row = postgres.table("rows")
query result:
    from rows
    let right = rows
    inner join right on rows.id == right.id
    group by rows.label
    select:
        key = rows.label
        total = sum(right.amount)
    qualify:
        sum(total) window(order by key) > 0 and count(len(key)) window(order by key) > 0
""")
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.script is not None
    assert not semantic.diagnostics, semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None, lowered.diagnostics
    relation = lowered.ir.definitions[-1]
    assert type(relation) is RelationIR
    assert relation.qualify is not None

    windows: list[AggregateWindowCallIR] = []
    pending = [relation.qualify.expression]
    while pending:
        expression = pending.pop()
        if type(expression) is AggregateWindowCallIR:
            windows.append(expression)
            continue
        for field in fields(expression):
            value = getattr(expression, field.name)
            if isinstance(value, ExpressionIR):
                pending.append(value)
            elif type(value) is tuple:
                pending.extend(item for item in value if isinstance(item, ExpressionIR))

    summed = next(call for call in windows if call.function == "sum")
    assert type(summed.arguments[0]) is AggregateCallIR
    assert type(summed.arguments[0].arguments[0]) is FieldRefIR
    assert summed.arguments[0].arguments[0].field is not None
    assert summed.arguments[0].arguments[0].field.input == 1
    counted = next(call for call in windows if call.function == "count")
    assert type(counted.arguments[0]) is CallIR
    assert type(counted.arguments[0].arguments[0]) is FieldRefIR
    assert counted.arguments[0].arguments[0].field is not None
    assert counted.arguments[0].arguments[0].field.input == 0

    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert 'SUM(SUM("right"."amount")) OVER (ORDER BY "rows"."label" ASC)' in sql
    assert 'COUNT(length("rows"."label")) OVER (ORDER BY "rows"."label" ASC)' in sql


def test_postgres_refuses_a_hand_built_groups_frame_without_order_by():
    groups = WindowFrameIR(
        unit=WindowFrameUnitIR.GROUPS,
        start=WindowFrameBoundIR(WindowFrameBoundKindIR.UNBOUNDED_PRECEDING),
        end=WindowFrameBoundIR(WindowFrameBoundKindIR.CURRENT_ROW),
        exclusion=WindowFrameExclusionIR.NO_OTHERS,
        frame_is_explicit=True,
        end_is_explicit=True,
        exclusion_is_explicit=False,
    )
    with pytest.raises(ValueError, match="PostgreSQL GROUPS frames require ORDER BY"):
        render_window_components_sql((), (), groups)
    rows = WindowFrameIR(
        unit=WindowFrameUnitIR.ROWS,
        start=WindowFrameBoundIR(WindowFrameBoundKindIR.UNBOUNDED_PRECEDING),
        end=WindowFrameBoundIR(WindowFrameBoundKindIR.CURRENT_ROW),
        exclusion=WindowFrameExclusionIR.NO_OTHERS,
        frame_is_explicit=True,
        end_is_explicit=True,
        exclusion_is_explicit=False,
    )
    assert render_window_components_sql((), (), rows) == (
        "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS",
    )
    with pytest.raises(ValueError, match="PostgreSQL window frame must be exact"):
        render_window_components_sql((), (), cast(WindowFrameIR, object()))


def test_postgres_named_aggregate_groups_frame_uses_the_inherited_order():
    parsed = parse_source("""shape Row:
    id: Int
source rows: Row = postgres.table("rows")
table totals:
    from rows
    let base = window(order by id)
    select:
        total = sum(id) window base(groups between unbounded preceding and current row)
""")
    assert parsed.ast is not None
    lowered = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert lowered.ir is not None
    sql = emit_postgres_sql(lowered.ir).artifacts[0].sql
    assert (
        'SUM("id") OVER ("base" GROUPS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW EXCLUDE NO OTHERS)'
        in sql
    )
    assert '"base" AS (ORDER BY "id" ASC)' in sql
