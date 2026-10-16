from __future__ import annotations

import json
import re
from dataclasses import fields, replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ast_nodes import NameExpr, OrderByClause, QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, build_ir
from pietto.ir.model import OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, analyze
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_PREFIX = (
    "shape User:\n"
    "    id: Int not null\n"
    "    created_at: Int not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
MYSQL_PREFIX = POSTGRES_PREFIX.replace("postgres.table", "mysql.table")


@pytest.mark.parametrize("direction", [None, "asc", "desc"])
@pytest.mark.parametrize("relation_kind", ["query", "table"])
def test_parser_accepts_one_order_item_and_preserves_direction(
    direction: str | None,
    relation_kind: str,
) -> None:
    suffix = "" if direction is None else f" {direction}"
    result = parse_source(
        _relation_source(
            relation_kind=relation_kind,
            order_items=(f"created_at{suffix}",),
        ),
        path="order.pietto",
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef | TableDef, result.ast.definitions[0])
    assert isinstance(relation.order_by_clause, OrderByClause)
    assert len(relation.order_by_clause.items) == 1
    item = relation.order_by_clause.items[0]
    assert isinstance(item.expression, NameExpr)
    assert item.expression.name == "created_at"
    assert item.direction == direction


def test_parser_preserves_multiple_order_items_in_source_order() -> None:
    relation = cast(
        QueryDef,
        _parse(
            _relation_source(order_items=("created_at desc", "id", "lower(email) asc"))
        ).definitions[0],
    )

    assert relation.order_by_clause is not None
    assert [
        (
            item.expression.name
            if isinstance(item.expression, NameExpr)
            else type(item.expression).__name__,
            item.direction,
        )
        for item in relation.order_by_clause.items
    ] == [
        ("created_at", "desc"),
        ("id", None),
        ("CallExpr", "asc"),
    ]


@pytest.mark.parametrize(
    "body",
    [
        ("    from users\n    select:\n        id\n    order by:\n"),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id\n"
            "    order by:\n"
            "        created_at\n"
        ),
        ("    from users\n    order by:\n        id\n    select:\n        id\n"),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    limit 10\n"
            "    order by:\n"
            "        id\n"
        ),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id sideways\n"
        ),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id nulls first\n"
        ),
        (
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    order by:\n"
            "        id nulls last\n"
        ),
        ("    from users\n    select:\n        id\n    order by:\n        1\n"),
    ],
)
def test_invalid_order_by_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query selected:\n{body}", path="order.pietto")

    assert result.ast is None
    assert result.diagnostics
    assert all(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_grammar_keeps_relation_order_surface_narrow() -> None:
    grammar = (REPO_ROOT / "grammar/Pietto.g4").read_text(encoding="utf-8")

    for token in (
        "ORDER: 'order';",
        "BY: 'by';",
        "ASC: 'asc';",
        "DESC: 'desc';",
    ):
        assert grammar.count(token) == 1
    assert grammar.count("NULLS: 'nulls';") == 1

    order_item = re.search(
        r"^orderItem\s*\n\s*:\s*(?P<body>.*?)\n\s*;$",
        grammar,
        re.MULTILINE | re.DOTALL,
    )
    identifier = re.search(
        r"^identifier\s*\n\s*:\s*(?P<body>.*?)\n\s*;$",
        grammar,
        re.MULTILINE | re.DOTALL,
    )
    assert order_item is not None
    assert identifier is not None
    assert " ".join(order_item.group("body").split()) == (
        "expression (ASC | DESC)? NEWLINE"
    )
    assert "| NULLS" in identifier.group("body")


def test_new_order_keywords_remain_valid_in_identifier_positions() -> None:
    result = parse_source(
        "shape Keywords:\n"
        "    order: Int not null\n"
        "    by: Int not null\n"
        "    asc: Int not null\n"
        "    desc: Int not null\n"
        'source order: Keywords is postgres.table("keywords")\n'
        "query by:\n"
        "    from order\n"
        "    select:\n"
        "        asc = asc\n"
        "        desc = desc\n"
        "    order by:\n"
        "        order\n",
        path="soft-keywords.pietto",
    )

    assert result.diagnostics == ()
    assert result.ast is not None


def test_semantic_accepts_input_fields_and_existing_expression_typing() -> None:
    script = _parse(
        POSTGRES_PREFIX
        + _relation_source(
            where="active == true",
            order_items=("created_at + id desc", "lower(email)"),
        )
    )
    relation = cast(QueryDef, script.definitions[-1])
    assert relation.order_by_clause is not None

    result = analyze(script)

    assert not [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    assert all(
        item.expression in result.model.expression_value_types
        for item in relation.order_by_clause.items
    )


def test_projection_alias_is_not_an_order_by_name_scope() -> None:
    script = _parse(
        POSTGRES_PREFIX
        + _relation_source(
            projections=("sort_key = lower(email)",),
            order_items=("sort_key",),
        )
    )

    result = analyze(script)
    errors = [
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert [(diagnostic.code, diagnostic.message) for diagnostic in errors] == [
        (
            "PIE-S2102",
            "Unknown field: sort_key; outside a grouped query an ORDER BY key "
            "cannot name a SELECT output (restate its expression or bind it in "
            "`let:`)",
        )
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        # An unknown relation already has its error: no ORDER BY cascade.
        (
            "query selected:\n    from broken\n    select:\n        a = x\n"
            "    order by:\n        a asc\n",
            [("PIE-S2301", "Unknown relation: broken")],
        ),
        # A source without a shape: the unknown input row is not refused.
        (
            'source users is postgres.table("users")\n'
            "query selected:\n    from users\n    select:\n        a = lower(email)\n"
            "    order by:\n        a asc\n",
            [],
        ),
    ),
)
def test_order_by_over_an_unknown_input_row_names_no_select_output(
    source: str, expected: list[tuple[str, str]]
) -> None:
    result = analyze(_parse(source), mode_override=CheckMode.LOOSE)

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == expected


def test_alias_matching_an_input_field_still_resolves_the_input_field() -> None:
    script_ir = _compile_ir(
        POSTGRES_PREFIX
        + _relation_source(
            projections=("created_at = lower(email)",),
            order_items=("created_at",),
        )
    )
    relation = _relation_ir(script_ir)
    expression = relation.order_by[0].expression

    assert isinstance(expression, FieldRefIR)
    assert expression.name == "created_at"
    assert expression.field is not None
    assert expression.field.owner == relation.source.target


@pytest.mark.parametrize(
    ("body", "postgres_order", "mysql_order"),
    [
        (
            "    select:\n"
            "        id\n"
            "        created_at = lower(email)\n"
            "    order by:\n"
            "        created_at desc\n"
            "    limit 3\n",
            '"users"."created_at" DESC',
            "`users`.`created_at` DESC",
        ),
        (
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        key = id\n"
            "        id = count()\n"
            "    order by:\n"
            "        key\n",
            '"users"."id" ASC',
            "`users`.`id` ASC",
        ),
        (
            "    select:\n        Created_At = id\n    order by:\n        created_at\n",
            '"created_at" ASC',
            "`users`.`created_at` ASC",
        ),
        (
            "    let:\n"
            "        later = created_at + 1\n"
            "    select:\n"
            "        created_at = id\n"
            "    order by:\n"
            "        later\n",
            '"created_at" + 1 ASC',
            "`created_at` + 1 ASC",
        ),
        (
            "    select:\n        id\n        lower(email)\n    order by:\n        id\n",
            '"users"."id" ASC',
            "`id` ASC",
        ),
    ],
    ids=(
        "ungrouped",
        "grouped",
        "mysql-casefold",
        "expression-reads-input",
        "postgres-unaliased-computed-item",
    ),
)
def test_input_order_key_that_a_select_item_would_capture_is_qualified(
    body: str,
    postgres_order: str,
    mysql_order: str,
) -> None:
    # Before: a bare `ORDER BY "created_at"` sorted by the SELECT output.
    query = "query selected:\n    from users\n" + body
    postgres = sql_api.emit_postgres_sql(_compile_ir(POSTGRES_PREFIX + query))
    mysql = emit_mysql_sql(_compile_ir(MYSQL_PREFIX + query))

    assert postgres.diagnostics == () and mysql.diagnostics == ()
    for sql, quote, order in (
        (postgres.artifacts[0].sql, '"', postgres_order),
        (mysql.artifacts[0].sql, "`", mysql_order),
    ):
        assert f"ORDER BY\n    {order}" in sql
        assert f"\nFROM {quote}users{quote}\n" in sql


@pytest.mark.parametrize(
    ("function", "field"),
    [("lower(email)", "lower"), ('coalesce(email, "x")', "coalesce")],
)
def test_postgresql_implicit_column_name_of_an_unaliased_item_is_not_bound(
    function: str,
    field: str,
) -> None:
    query = (
        f"shape Row:\n    email: Text not null\n    {field}: Int not null\n"
        'source rows: Row is {connector}.table("sales.rows")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        f"        {function}\n"
        "    order by:\n"
        f"        {field}\n"
    )

    postgres = sql_api.emit_postgres_sql(
        _compile_ir(query.format(connector="postgres"))
    )
    mysql = emit_mysql_sql(_compile_ir(query.format(connector="mysql")))

    # Before: `ORDER BY "lower"` bound to PostgreSQL's implicit column name.
    assert postgres.artifacts[0].sql.endswith(
        f'FROM "sales"."rows"\nORDER BY\n    "rows"."{field}" ASC'
    )
    # MySQL names the unaliased item by its expression text, so it stays bare.
    assert mysql.artifacts[0].sql.endswith(
        f"FROM `sales`.`rows`\nORDER BY\n    `{field}` ASC"
    )


def test_captured_key_uses_the_name_from_already_gives_the_input() -> None:
    def source(connector: str, name: str, first: str) -> str:
        return (
            "shape Row:\n    id: Int not null\n    amount: Int not null\n"
            "    other: Int not null\n"
            f'source {name}: Row is {connector}.table("sales.orders")\n'
            f"query q:\n    from {name}\n    select:\n        {first}\n"
            "        amount = other\n    order by:\n        amount\n"
        )

    long_name = "s" * 70
    for connector, emitter, quote in (
        ("postgres", sql_api.emit_postgres_sql, '"'),
        ("mysql", emit_mysql_sql, "`"),
    ):
        unaliased = emitter(_compile_ir(source(connector, long_name, "id")))
        aliased = emitter(_compile_ir(source(connector, "o", "id = o.id")))

        def q(name: str) -> str:
            return f"{quote}{name}{quote}"

        # Before: FROM gained `AS <70-character source name>`, which both
        # targets refused as an identifier over their limit.
        assert unaliased.artifacts[0].sql.endswith(
            f"FROM {q('sales')}.{q('orders')}\n"
            f"ORDER BY\n    {q('orders')}.{q('amount')} ASC"
        )
        # An authored qualified field already aliases FROM; the key reuses it.
        assert aliased.artifacts[0].sql.endswith(
            f"FROM {q('sales')}.{q('orders')} AS {q('o')}\n"
            f"ORDER BY\n    {q('o')}.{q('amount')} ASC"
        )


@pytest.mark.parametrize(
    "select_items",
    [
        ("amount = count()", "n = count()"),
        ("m = count()", "n = count()"),
    ],
    ids=("colliding-output", "no-collision"),
)
def test_input_field_key_of_an_ungrouped_aggregate_query_is_refused(
    select_items: tuple[str, ...],
) -> None:
    source = (
        "shape Row:\n    amount: Int not null\n    other: Int not null\n"
        'source orders: Row is postgres.table("orders")\n'
        "query q:\n"
        "    from orders\n"
        "    select:\n"
        + "".join(f"        {item}\n" for item in select_items)
        + "    order by:\n"
        "        amount\n"
    )

    result = analyze(_parse(source))

    # Before: check passed and PostgreSQL rejects the ungrouped ORDER BY column.
    assert [(d.code, d.message) for d in result.diagnostics] == [
        (
            "PIE-S2380",
            "ORDER BY key reads an input field outside an aggregate in a query "
            "with aggregates and no GROUP BY, which SQL targets reject",
        )
    ]


def test_output_alias_reading_the_same_input_field_keeps_a_bare_order_key() -> None:
    query = _relation_source(
        projections=("id", "created_at = users.created_at"),
        order_items=("created_at",),
    )
    postgres = sql_api.emit_postgres_sql(_compile_ir(POSTGRES_PREFIX + query))
    mysql = emit_mysql_sql(_compile_ir(MYSQL_PREFIX + query))

    assert postgres.artifacts[0].sql.endswith('ORDER BY\n    "created_at" ASC')
    assert mysql.artifacts[0].sql.endswith("ORDER BY\n    `created_at` ASC")


def _keyed_body(key: str, let_lines: tuple[str, ...] = ()) -> str:
    let_clause = "".join(f"        {line}\n" for line in let_lines)
    return (
        "query selected:\n"
        "    from users\n"
        + ("    let:\n" + let_clause if let_clause else "")
        + "    select:\n"
        "        id\n"
        "    order by:\n"
        f"        {key} asc\n"
        "        id\n"
    )


@pytest.mark.parametrize(
    ("let_lines", "key"),
    [
        ((), '"x"'),
        ((), "-1"),
        ((), "+2"),
        ((), "2.5"),
        ((), "true"),
        ((), "null"),
        (("position = 2",), "position"),
        (("position = -2",), "position"),
        (("base = 2",), "-base"),
    ],
)
def test_bare_constant_order_key_is_refused_at_check(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    let_lines: tuple[str, ...],
    key: str,
) -> None:
    body = _keyed_body(key, let_lines)
    result = analyze(_parse(POSTGRES_PREFIX + body))

    key_line = 12 + (1 + len(let_lines) if let_lines else 0)
    assert [
        (diagnostic.code, diagnostic.location and diagnostic.location.line)
        for diagnostic in result.diagnostics
    ] == [("PIE-S2380", key_line)]
    # Before: `let: position = 2` emitted the ordinal `ORDER BY 2 ASC`.
    for prefix, dialect in ((POSTGRES_PREFIX, "postgres"), (MYSQL_PREFIX, "mysql")):
        path = tmp_path / f"{dialect}.pietto"
        path.write_text(prefix + body, encoding="utf-8")
        assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 1
        assert "PIE-S2380" in capsys.readouterr().err


@pytest.mark.parametrize("connector", ["postgres", "mysql"])
@pytest.mark.parametrize(
    ("let_lines", "key", "accepted"),
    [
        (("k = 2",), "k", False),
        ((), '"x"', False),
        ((), "-1", False),
        (("k = id + 1",), "k", True),
        ((), "1 + 1", True),
    ],
)
def test_bare_constant_key_is_refused_from_a_source_without_a_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    connector: str,
    let_lines: tuple[str, ...],
    key: str,
    accepted: bool,
) -> None:
    let_clause = "".join(f"        {line}\n" for line in let_lines)
    path = tmp_path / "loose.pietto"
    path.write_text(
        f'source raw is {connector}.table("raw")\n'
        "query selected:\n"
        "    from raw\n"
        + ("    let:\n" + let_clause if let_clause else "")
        + "    select:\n        id\n        amount\n"
        f"    order by:\n        {key}\n",
        encoding="utf-8",
    )

    checked = cli.main(["check", "--check-mode", "loose", str(path)])
    check_err = capsys.readouterr().err
    emitted = cli.main(
        ["emit-sql", "--check-mode", "loose", str(path), "--dialect", connector]
    )
    emit_out, emit_err = capsys.readouterr()

    # Before: with no shape the key went unchecked; `let: k = 2` emitted the
    # column position `ORDER BY 2 ASC`. Emission inlines `k` as the let.
    if accepted:
        assert (checked, emitted, check_err) == (0, 0, "")
        assert "ORDER BY" in emit_out
    else:
        assert (checked, emitted) == (1, 1)
        assert "PIE-S2380" in check_err and "PIE-S2380" in emit_err


def test_key_over_the_let_inline_limit_reports_only_that_error() -> None:
    lets = "".join(f"        l{i} = l{i - 1} + 1\n" for i in range(1, 301))
    source = (
        "shape Row:\n    amount: Int not null\n"
        'source rows: Row is postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    let:\n        l0 = amount\n" + lets + "    select:\n"
        "        n = count()\n"
        "    order by:\n"
        "        l300\n"
    )

    # Before: PIE-S2380 joined the key's own PIE-S2328.
    assert [diagnostic.code for diagnostic in analyze(_parse(source)).diagnostics] == [
        "PIE-S2328"
    ]


@pytest.mark.parametrize(
    ("let_lines", "key", "postgres_key", "mysql_key"),
    [
        ((), "1 + 1", "1 + 1", "1 + 1"),
        ((), 'lower("x")', "lower('x')", "LOWER('x')"),
        (("base = 2", "next = base + 1"), "next", "2 + 1", "2 + 1"),
    ],
)
def test_computed_constant_order_key_still_emits_as_a_no_op_sort(
    let_lines: tuple[str, ...],
    key: str,
    postgres_key: str,
    mysql_key: str,
) -> None:
    body = _keyed_body(key, let_lines)
    postgres = sql_api.emit_postgres_sql(_compile_ir(POSTGRES_PREFIX + body))
    mysql = emit_mysql_sql(_compile_ir(MYSQL_PREFIX + body))

    assert f"ORDER BY\n    {postgres_key} ASC," in postgres.artifacts[0].sql
    assert f"ORDER BY\n    {mysql_key} ASC," in mysql.artifacts[0].sql


@pytest.mark.parametrize(
    ("let_lines", "key", "code"),
    [
        ((), "foo()", "PIE-S2103"),
        ((), '-"x"', "PIE-S2105"),
        (("a = a + 1",), "a", "PIE-S2330"),
    ],
)
def test_order_key_with_its_own_error_gets_no_constant_key_error(
    let_lines: tuple[str, ...],
    key: str,
    code: str,
) -> None:
    result = analyze(_parse(POSTGRES_PREFIX + _keyed_body(key, let_lines)))

    assert [diagnostic.code for diagnostic in result.diagnostics] == [code]


def test_order_keys_reading_fields_lets_or_windows_are_not_constant() -> None:
    body = (
        "query selected:\n"
        "    from users\n"
        "    let:\n"
        "        bucket = id + 1\n"
        "    select:\n"
        "        id\n"
        "        position = row_number() window:\n"
        "            order by:\n"
        "                id\n"
        "    order by:\n"
        "        bucket\n"
        "        position\n"
        "        lower(email) desc\n"
    )

    assert analyze(_parse(POSTGRES_PREFIX + body)).diagnostics == ()


def test_ir_defaults_and_normalized_order_items_are_stable() -> None:
    no_order = _relation_ir(_compile_ir(POSTGRES_PREFIX + _relation_source()))
    ordered = _relation_ir(
        _compile_ir(
            POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )
    order_field = next(
        field for field in fields(RelationIR) if field.name == "order_by"
    )

    assert order_field.default == ()
    assert no_order.order_by == ()
    assert [item.direction for item in ordered.order_by] == [
        OrderDirectionIR.DESC,
        OrderDirectionIR.ASC,
    ]
    assert [cast(FieldRefIR, item.expression).name for item in ordered.order_by] == [
        "created_at",
        "id",
    ]
    assert [item.span.line for item in ordered.order_by] == [12, 13]
    assert all(item.span.end_column > item.span.column for item in ordered.order_by)


def test_postgres_and_mysql_render_exact_multiline_order_by() -> None:
    postgres = sql_api.emit_postgres_sql(
        _compile_ir(
            POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )
    mysql = emit_mysql_sql(
        _compile_ir(
            MYSQL_PREFIX + _relation_source(order_items=("created_at desc", "id"))
        )
    )

    assert postgres.diagnostics == ()
    assert postgres.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id"\n'
        'FROM "users"\n'
        "ORDER BY\n"
        '    "created_at" DESC,\n'
        '    "id" ASC'
    )
    assert mysql.diagnostics == ()
    assert mysql.artifacts[0].sql == (
        "SELECT\n"
        "    `id` AS `id`\n"
        "FROM `users`\n"
        "ORDER BY\n"
        "    `created_at` DESC,\n"
        "    `id` ASC"
    )
    assert not postgres.artifacts[0].sql.endswith("\n")
    assert not mysql.artifacts[0].sql.endswith("\n")


def test_both_backends_render_order_by_before_existing_limit() -> None:
    for prefix, emitter, quote in (
        (POSTGRES_PREFIX, sql_api.emit_postgres_sql, '"'),
        (MYSQL_PREFIX, emit_mysql_sql, "`"),
    ):
        result = emitter(
            _compile_ir(
                prefix
                + _relation_source(
                    order_items=("created_at desc", "id"),
                    limit="100",
                )
            )
        )

        assert result.diagnostics == ()
        assert result.artifacts[0].sql.endswith(
            "ORDER BY\n"
            f"    {quote}created_at{quote} DESC,\n"
            f"    {quote}id{quote} ASC\n"
            "LIMIT 100"
        )


def test_both_backends_fail_closed_for_malformed_order_direction() -> None:
    for prefix, emitter in (
        (POSTGRES_PREFIX, sql_api.emit_postgres_sql),
        (MYSQL_PREFIX, emit_mysql_sql),
    ):
        script_ir = _compile_ir(prefix + _relation_source(order_items=("created_at",)))
        relation = _relation_ir(script_ir)
        item = relation.order_by[0]
        malformed = replace(
            relation,
            order_by=(
                replace(
                    item,
                    direction=cast(OrderDirectionIR, "SIDEWAYS"),
                ),
            ),
        )
        replaced = ScriptIR(
            definitions=tuple(
                malformed if definition is relation else definition
                for definition in script_ir.definitions
            )
        )

        result = emitter(replaced)

        assert result.artifacts == ()
        assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]


def test_cli_text_and_json_v1_carry_order_sql_without_new_options(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    postgres_path = tmp_path / "postgres-order.pietto"
    postgres_path.write_text(
        POSTGRES_PREFIX + _relation_source(order_items=("created_at desc", "id")),
        encoding="utf-8",
    )
    mysql_path = tmp_path / "mysql-order.pietto"
    mysql_path.write_text(
        MYSQL_PREFIX + _relation_source(order_items=("created_at desc", "id")),
        encoding="utf-8",
    )

    assert cli.main(["emit-sql", str(postgres_path), "--dialect", "postgres"]) == 0
    text = capsys.readouterr()
    assert text.err == ""
    assert text.out.endswith('ORDER BY\n    "created_at" DESC,\n    "id" ASC\n')

    assert (
        cli.main(
            [
                "emit-sql",
                str(mysql_path),
                "--dialect",
                "mysql",
                "--format",
                "json",
            ]
        )
        == 0
    )
    json_output = capsys.readouterr()
    document = json.loads(json_output.out)
    assert json_output.err == ""
    assert document["schema_version"] == 1
    assert document["artifacts"][0]["sql"].endswith(
        "ORDER BY\n    `created_at` DESC,\n    `id` ASC"
    )


def test_internal_order_ir_types_are_not_public_exports() -> None:
    assert not hasattr(sql_api, "OrderItemIR")
    assert not hasattr(sql_api, "OrderDirectionIR")
    assert OrderItemIR.__module__ == "pietto.ir.model"
    assert OrderDirectionIR.__module__ == "pietto.ir.model"


def test_suffix_and_diagnostic_code_contracts_remain_canonical() -> None:
    repository_text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in ("src", "tests", "docs", "examples", "grammar")
        for path in sorted((REPO_ROOT / root).rglob("*"))
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix in {".py", ".md", ".pietto", ".g4"}
    )

    assert re.search(r"\." + "pie" + r"\b", repository_text) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository_text) is None


def _relation_source(
    *,
    relation_kind: str = "query",
    where: str | None = None,
    projections: tuple[str, ...] = ("id",),
    order_items: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    where_clause = "" if where is None else f"    where {where}\n"
    order_clause = ""
    if order_items:
        order_clause = "    order by:\n" + "".join(
            f"        {item}\n" for item in order_items
        )
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        f"{relation_kind} selected:\n"
        "    from users\n"
        f"{where_clause}"
        "    select:\n"
        + "".join(f"        {projection}\n" for projection in projections)
        + order_clause
        + limit_clause
    )


def _parse(source: str, *, path: str = "order.pietto"):
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile_ir(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    assert not [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    result = build_ir(script, semantic_result.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )
