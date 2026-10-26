from __future__ import annotations

import json
import os
import re
import runpy
import shlex
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ConnectorIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    FilterIR,
    JoinEqualityIR,
    JoinHopIR,
    JoinIR,
    JoinKindIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    RelationInputIR,
    RelationInputRoleIR,
    RelationKindIR,
    RelationSourceIR,
    ResultPredicateIR,
    RowSchemaIR,
    ScriptIR,
    SourceIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import LimitIR, OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.joins import render_conjunction_sql, render_join_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.render import IdentifierTooLongError

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_INPUT = "tests/fixtures/postgres/join_mvp.pietto"
GOLDEN_SQL = "tests/fixtures/golden/emit_sql_join_mvp.sql"
SPAN = SourceSpan(
    path="join-emission.pietto", line=3, column=5, end_line=3, end_column=9
)
LONG_BINDING = "r" * 64
# The relation each binding reads, and the SQL name of each relation.
RELATIONS = {
    "orders": "orders",
    "o": "orders",
    "o2": "orders",
    "_pietto_any_1": "orders",
    "customers": "customers",
    "customer": "customers",
    "peer": "customers",
    "region": "regions",
    LONG_BINDING: "regions",
    "c": "named_customers",
    "lines": "lines",
    "ship": "shipments",
}
NAMES = {
    "orders": ("shop", "orders"),
    "customers": ("shop", "customers"),
    "regions": ("shop", "regions"),
    "named_customers": ("named_customers",),
    "lines": ("shop", "lines"),
    "shipments": ("shop", "shipments"),
}
INNER, LEFT, RIGHT, FULL, CROSS, SEMI, ANTI = (
    JoinKindIR.INNER,
    JoinKindIR.LEFT,
    JoinKindIR.RIGHT,
    JoinKindIR.FULL,
    JoinKindIR.CROSS,
    JoinKindIR.SEMI,
    JoinKindIR.ANTI,
)
# A relationship equality, source field first; both fields are Int unless the
# pair names their type.
Pair = tuple[str, str] | tuple[str, str, TypeRefIR]
JoinSpec = tuple[JoinKindIR, str, tuple[Pair, ...], ExpressionIR | None]
FULL_REFUSAL = (
    "PostgreSQL FULL JOIN {} needs an ON made only of equalities between Int "
    "fields of its two sides; Pietto does not rewrite other FULL JOIN conditions yet"
)


def _type(
    name: str,
    nullability: NullabilityIR = NullabilityIR.NON_NULL,
    *,
    alias: str | None = None,
) -> TypeRefIR:
    return TypeRefIR(
        symbol=SymbolId(SymbolNamespace.TYPE, alias or name),
        canonical_symbol=SymbolId(SymbolNamespace.TYPE, name),
        declared_name=alias or name,
        canonical_name=name,
        kind=TypeKindIR.BUILTIN if alias is None else TypeKindIR.TYPE_ALIAS,
        canonical_kind=TypeKindIR.BUILTIN,
        nullability=nullability,
    )


INT = _type("Int")
INT_NULLABLE = _type("Int", NullabilityIR.NULLABLE)
CUSTOMER_ID = _type("Int", alias="CustomerId")
TEXT = _type("Text")
FLOAT = _type("Float")
BOOL = _type("Bool")


def _read(
    bindings: tuple[str, ...], text: str, value_type: TypeRefIR = INT
) -> FieldRefIR:
    """The field `<binding>.<field>` of the input with that binding."""

    binding, name = text.split(".")
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(binding,),
        field=FieldId(
            owner=SymbolId(SymbolNamespace.RELATION, RELATIONS[binding]),
            name=name,
            input=bindings.index(binding),
        ),
    )


def _compare(left: ExpressionIR, operator: str, right: ExpressionIR) -> ComparisonIR:
    return ComparisonIR(
        span=SPAN, value_type=BOOL, left=left, operator=operator, right=right
    )


def _binary(
    left: ExpressionIR, operator: str, right: ExpressionIR, value_type: TypeRefIR = BOOL
) -> BinaryIR:
    return BinaryIR(
        span=SPAN, value_type=value_type, left=left, operator=operator, right=right
    )


def _literal(value: int | str, value_type: TypeRefIR = INT) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


def _join(
    kind: JoinKindIR,
    source: str,
    *pairs: Pair,
    on: ExpressionIR | None = None,
) -> JoinSpec:
    """A JOIN from `source`, with one hop of `pairs` (source = target) if any."""

    return (kind, source, pairs, on)


def _relation(
    bindings: tuple[str, ...], *joins: JoinSpec, name: str = "q"
) -> RelationIR:
    """A relation whose input k has the binding `bindings[k]`."""

    rows = [0]
    built: list[JoinIR] = []
    for ordinal, (kind, source, pairs, on) in enumerate(joins, start=1):
        source_input = bindings.index(source)
        equalities = tuple(
            JoinEqualityIR(
                left=_read(bindings, left, *value_type),
                right=_read(bindings, right, *value_type),
            )
            for left, right, *value_type in pairs
        )
        hop = JoinHopIR("link", source_input, ordinal, equalities, SPAN)
        built.append(
            JoinIR(
                ordinal=ordinal,
                kind=kind,
                source_input=source_input,
                source_inferred=False,
                target_input=ordinal,
                hops=(hop,) if equalities else (),
                condition=on,
                null_extends={
                    LEFT: (ordinal,),
                    RIGHT: tuple(rows),
                    FULL: (*rows, ordinal),
                }.get(kind, ()),
                span=SPAN,
            )
        )
        if kind not in (SEMI, ANTI):
            rows.append(ordinal)
    inputs = tuple(
        RelationInputIR(
            ordinal=ordinal,
            role=RelationInputRoleIR.TARGET if ordinal else RelationInputRoleIR.FROM,
            target=SymbolId(SymbolNamespace.RELATION, RELATIONS[binding]),
            binding=binding,
            visible=ordinal == 0 or joins[ordinal - 1][0] not in (SEMI, ANTI),
            span=SPAN,
        )
        for ordinal, binding in enumerate(bindings)
    )
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, name),
        name=name,
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(target=inputs[0].target, name=bindings[0], span=SPAN),
        filter=None,
        projections=(),
        row_schema=RowSchemaIR(fields=()),
        span=SPAN,
        inputs=inputs,
        joins=tuple(built),
    )


def _sql(relation: RelationIR) -> str:
    """The FROM and JOIN lines, then a WHERE of the pending filters, if any."""

    lines, filters = render_join_sql(
        relation, [NAMES[item.target.name] for item in relation.inputs]
    )
    if filters:
        lines = (*lines, f"WHERE {render_conjunction_sql(filters)}")
    return "\n".join(lines)


OC = ("orders", "customer")
OCR = ("orders", "customer", "region")
CO = ("customers", "o")
CP = ("customers", "peer")
COR = ("customers", "o", "region")
# A JOIN-prefix `any` is a hidden SEMI JOIN whose binding Pietto names.
CAR = ("customers", "_pietto_any_1", "region")
CORP = ("customers", "o", "region", "peer")
LS = ("lines", "ship")
ORDERS_FROM = 'FROM "shop"."orders" AS "orders"'
CUSTOMERS_FROM = 'FROM "shop"."customers" AS "customers"'
LINES_FROM = 'FROM "shop"."lines" AS "lines"'
CUSTOMER = '"shop"."customers" AS "customer"'
REGION = '"shop"."regions" AS "region"'
PEER = '"shop"."customers" AS "peer"'
SHIP = '"shop"."shipments" AS "ship"'
ORDER_CUSTOMER = ("orders.customer_id", "customer.id")
ORDER_BUYER = ("orders.buyer", "customer.name", TEXT)
CUSTOMER_ORDER = ("customers.id", "o.customer_id")
CUSTOMER_REGION = ("customers.region_id", "region.id")
LINE_SHIP = (("lines.ord_id", "ship.ord_id"), ("lines.line_no", "ship.line_no"))
ORDER_CUSTOMER_SQL = '"orders"."customer_id" = "customer"."id"'
CUSTOMER_REGION_SQL = '"customers"."region_id" = "region"."id"'
PEER_IS_CUSTOMER_SQL = '"peer"."id" = "customers"."id"'
LINE_SHIP_SQL = (
    '("lines"."ord_id" = "ship"."ord_id") AND ("lines"."line_no" = "ship"."line_no")'
)
HAS_ORDERS = (
    'EXISTS (SELECT 1 FROM "shop"."orders" AS "o" '
    'WHERE "customers"."id" = "o"."customer_id")'
)
HAS_NO_BIG_ORDERS = (
    'NOT EXISTS (SELECT 1 FROM "shop"."orders" AS "o" '
    'WHERE ("customers"."id" = "o"."customer_id") AND ("o"."amount" > 100))'
)
BIG_ORDER = _compare(_read(CORP, "o.amount"), ">", _literal(100))
PEER_IS_CUSTOMER = _compare(_read(CORP, "peer.id"), "==", _read(CORP, "customers.id"))


def _order_customer(left: TypeRefIR = INT, right: TypeRefIR = INT) -> ComparisonIR:
    return _compare(
        _read(OC, "orders.customer_id", left), "==", _read(OC, "customer.id", right)
    )


def _full_on(left: str, operator: str, right: ExpressionIR | str) -> JoinSpec:
    """A FULL JOIN of `customer` from `orders` on one comparison."""

    return _join(
        FULL,
        "orders",
        on=_compare(
            _read(OC, left),
            operator,
            _read(OC, right) if isinstance(right, str) else right,
        ),
    )


def _golden_artifacts() -> dict[str, str]:
    """Each query of the golden input and its artifact of the golden SQL."""

    source = (REPO_ROOT / GOLDEN_INPUT).read_text(encoding="utf-8")
    names = [
        line.removeprefix("query ").removesuffix(":")
        for line in source.splitlines()
        if line.startswith("query ")
    ]
    golden = (REPO_ROOT / GOLDEN_SQL).read_text(encoding="utf-8")
    # emit-sql text: a `-- <name>` line, then the SQL ending with `;`.
    statements = golden.removesuffix(";\n").split(";\n\n")
    return {
        name: statement.removeprefix(f"-- {name}\n")
        for name, statement in zip(names, statements, strict=True)
    }


GOLDEN_ARTIFACTS = _golden_artifacts()
# The JOIN relations of the golden as IR lowers them, with the lines their
# artifacts carry after the JOIN block: a tail sql/relations.py writes.
GOLDEN_JOINS = {
    "order_names": (_relation(OC, _join(INNER, "orders", ORDER_CUSTOMER)), ()),
    "customer_regions": (
        _relation(("customers", "region"), _join(LEFT, "customers", CUSTOMER_REGION)),
        (),
    ),
    "orders_or_customers": (
        _relation(OC, _join(RIGHT, "orders", on=_order_customer(INT_NULLABLE))),
        (),
    ),
    "order_customer_pairs": (
        _relation(OC, _join(FULL, "orders", on=_order_customer(INT_NULLABLE))),
        (),
    ),
    "order_region_pairs": (
        _relation(("orders", "region"), _join(CROSS, "orders")),
        (),
    ),
    "big_order_names": (
        _relation(
            OC,
            _join(
                INNER,
                "orders",
                on=_binary(
                    _order_customer(INT_NULLABLE),
                    "and",
                    _compare(_read(OC, "orders.amount"), ">", _literal(5)),
                ),
            ),
        ),
        (),
    ),
    "orders_with_named_customers": (
        _relation(
            OC,
            _join(
                LEFT,
                "orders",
                ORDER_CUSTOMER,
                on=_compare(
                    _read(OC, "customer.name", TEXT), "!=", _literal("x", TEXT)
                ),
            ),
        ),
        (),
    ),
    "recent_order_regions": (
        _relation(
            OCR,
            _join(INNER, "orders", ORDER_CUSTOMER),
            _join(LEFT, "customer", ("customer.region_id", "region.id")),
        ),
        (
            'WHERE "orders"."amount" > 1',
            "ORDER BY",
            '    "orders"."id" DESC',
            "LIMIT 10",
        ),
    ),
    "regions_and_ordering_customers": (
        _relation(
            CAR,
            _join(SEMI, "customers", ("customers.id", "_pietto_any_1.customer_id")),
            _join(RIGHT, "customers", CUSTOMER_REGION),
        ),
        (),
    ),
    "customer_peers": (
        _relation(
            CP,
            _join(
                LEFT,
                "customers",
                on=_binary(
                    _compare(
                        _read(CP, "peer.region_id"),
                        "==",
                        _read(CP, "customers.region_id"),
                    ),
                    "and",
                    _compare(_read(CP, "peer.id"), "!=", _read(CP, "customers.id")),
                ),
            ),
        ),
        (),
    ),
    "order_stats": (
        _relation(OC, _join(INNER, "orders", ORDER_CUSTOMER)),
        (
            "GROUP BY",
            '    "customer"."id",',
            '    "customer"."name"',
            "HAVING",
            "    COUNT(*) > 1",
        ),
    ),
    "orders_of_named_customers": (
        _relation(
            ("orders", "c"),
            _join(
                INNER,
                "orders",
                on=_compare(
                    _read(("orders", "c"), "orders.customer_id"),
                    "==",
                    _read(("orders", "c"), "c.id"),
                ),
            ),
        ),
        (),
    ),
}


# The golden's other queries have no JOIN: `named_customers`, and the two that
# filter with a tail `where [not] any(...)`, a correlated EXISTS read.
@pytest.mark.parametrize(
    "name", [name for name in GOLDEN_ARTIFACTS if name in GOLDEN_JOINS]
)
def test_each_golden_join_relation_renders_its_reviewed_from_and_join_lines(
    name: str,
) -> None:
    relation, tail = GOLDEN_JOINS[name]
    lines = GOLDEN_ARTIFACTS[name].split("\n")
    # The statement's own SELECT follows the CTEs it defines.
    if lines[0].startswith("WITH "):
        lines = lines[lines.index(")") + 1 :]
    start = next(index for index, line in enumerate(lines) if line.startswith("FROM "))

    assert lines[start:] == [*_sql(relation).split("\n"), *tail]


# The golden's last-position existence filters, once a SEMI and an ANTI JOIN:
# a tail `where [not] any(...)` reads its relation under its own value alias.
GOLDEN_TAIL_ANY = {
    "customers_with_orders": HAS_ORDERS.replace('"o"', '"_pietto_value_1"'),
    "customers_without_big_orders": HAS_NO_BIG_ORDERS.replace(
        '"o"', '"_pietto_value_2"'
    ),
}


@pytest.mark.parametrize(
    "name",
    [
        name
        for name in GOLDEN_ARTIFACTS
        if name not in GOLDEN_JOINS and name != "named_customers"
    ],
)
def test_each_golden_tail_any_renders_its_reviewed_exists_filter(name: str) -> None:
    lines = GOLDEN_ARTIFACTS[name].split("\n")
    start = next(index for index, line in enumerate(lines) if line.startswith("FROM "))

    assert lines[start:] == [CUSTOMERS_FROM, f"WHERE {GOLDEN_TAIL_ANY[name]}"]


@pytest.mark.parametrize(
    ("join", "expected"),
    [
        pytest.param(
            _join(INNER, "customers", CUSTOMER_REGION),
            f"INNER JOIN {REGION} ON {CUSTOMER_REGION_SQL}\nWHERE {HAS_ORDERS}",
            id="inner",
        ),
        pytest.param(
            _join(LEFT, "customers", CUSTOMER_REGION),
            f"LEFT JOIN {REGION} ON {CUSTOMER_REGION_SQL}\nWHERE {HAS_ORDERS}",
            id="left",
        ),
        pytest.param(
            _join(CROSS, "customers"),
            f"CROSS JOIN {REGION}\nWHERE {HAS_ORDERS}",
            id="cross",
        ),
        pytest.param(
            _join(SEMI, "customers", CUSTOMER_REGION),
            f"WHERE ({HAS_ORDERS}) AND "
            f"(EXISTS (SELECT 1 FROM {REGION} WHERE {CUSTOMER_REGION_SQL}))",
            id="semi",
        ),
        pytest.param(
            _join(ANTI, "customers", CUSTOMER_REGION),
            f"WHERE ({HAS_ORDERS}) AND "
            f"(NOT EXISTS (SELECT 1 FROM {REGION} WHERE {CUSTOMER_REGION_SQL}))",
            id="anti",
        ),
        pytest.param(
            _join(RIGHT, "customers", CUSTOMER_REGION),
            f"RIGHT JOIN {REGION} ON ({CUSTOMER_REGION_SQL}) AND ({HAS_ORDERS})",
            id="right",
        ),
    ],
)
def test_a_pending_filter_stays_until_a_right_join_takes_it_into_its_on(
    join: JoinSpec, expected: str
) -> None:
    relation = _relation(COR, _join(SEMI, "customers", CUSTOMER_ORDER), join)

    assert _sql(relation) == f"{CUSTOMERS_FROM}\n{expected}"


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        pytest.param(
            _relation(
                CORP,
                _join(SEMI, "customers", CUSTOMER_ORDER),
                _join(LEFT, "customers", CUSTOMER_REGION),
                _join(RIGHT, "customers", on=PEER_IS_CUSTOMER),
            ),
            f"LEFT JOIN {REGION} ON {CUSTOMER_REGION_SQL}\n"
            f"RIGHT JOIN {PEER} ON ({PEER_IS_CUSTOMER_SQL}) AND ({HAS_ORDERS})",
            id="semi-left-right",
        ),
        pytest.param(
            _relation(
                CORP,
                _join(SEMI, "customers", CUSTOMER_ORDER),
                _join(RIGHT, "customers", CUSTOMER_REGION),
                _join(FULL, "customers", on=PEER_IS_CUSTOMER),
            ),
            f"RIGHT JOIN {REGION} ON ({CUSTOMER_REGION_SQL}) AND ({HAS_ORDERS})\n"
            f"FULL JOIN {PEER} ON {PEER_IS_CUSTOMER_SQL}",
            id="semi-right-full",
        ),
        pytest.param(
            _relation(
                CORP,
                _join(ANTI, "customers", CUSTOMER_ORDER, on=BIG_ORDER),
                _join(INNER, "customers", CUSTOMER_REGION),
                _join(RIGHT, "customers", on=PEER_IS_CUSTOMER),
            ),
            f"INNER JOIN {REGION} ON {CUSTOMER_REGION_SQL}\n"
            f"RIGHT JOIN {PEER} ON ({PEER_IS_CUSTOMER_SQL}) AND ({HAS_NO_BIG_ORDERS})",
            id="anti-inner-right",
        ),
        pytest.param(
            _relation(
                ("customers", "o", "o2", "peer"),
                _join(SEMI, "customers", CUSTOMER_ORDER),
                _join(ANTI, "customers", ("customers.id", "o2.customer_id")),
                _join(RIGHT, "customers", on=PEER_IS_CUSTOMER),
            ),
            f"RIGHT JOIN {PEER} ON ({PEER_IS_CUSTOMER_SQL}) AND ({HAS_ORDERS}) AND "
            '(NOT EXISTS (SELECT 1 FROM "shop"."orders" AS "o2" '
            'WHERE "customers"."id" = "o2"."customer_id"))',
            id="semi-anti-right",
        ),
        pytest.param(
            _relation(
                ("customers", "region", "o"),
                _join(RIGHT, "customers", CUSTOMER_REGION),
                _join(SEMI, "customers", CUSTOMER_ORDER),
            ),
            f"RIGHT JOIN {REGION} ON {CUSTOMER_REGION_SQL}\nWHERE {HAS_ORDERS}",
            id="right-semi",
        ),
    ],
)
def test_pending_filters_enter_the_next_right_join_in_join_order(
    relation: RelationIR, expected: str
) -> None:
    assert _sql(relation) == f"{CUSTOMERS_FROM}\n{expected}"


@pytest.mark.parametrize(
    ("relation", "binding"),
    [
        pytest.param(
            _relation(
                COR,
                _join(SEMI, "customers", CUSTOMER_ORDER),
                _join(FULL, "customers", CUSTOMER_REGION),
            ),
            "region",
            id="semi-full",
        ),
        pytest.param(
            _relation(
                ("customers", "o", "region", "o2", "peer"),
                _join(SEMI, "customers", CUSTOMER_ORDER),
                _join(RIGHT, "customers", CUSTOMER_REGION),
                _join(SEMI, "customers", ("customers.id", "o2.customer_id")),
                _join(FULL, "customers", ("customers.id", "peer.id")),
            ),
            "peer",
            id="semi-right-semi-full",
        ),
        pytest.param(
            _relation(
                ("customers", "o", "peer"),
                _join(ANTI, "customers", CUSTOMER_ORDER),
                _join(
                    FULL,
                    "customers",
                    on=_compare(
                        _read(("customers", "o", "peer"), "peer.name", TEXT),
                        "==",
                        _read(("customers", "o", "peer"), "customers.name", TEXT),
                    ),
                ),
            ),
            "peer",
            id="anti-then-a-text-full",
        ),
    ],
)
def test_a_full_join_after_a_pending_filter_is_refused(
    relation: RelationIR, binding: str
) -> None:
    with pytest.raises(ValueError) as raised:
        _sql(relation)

    assert str(raised.value) == (
        f"A SEMI or ANTI JOIN before FULL JOIN {binding} is not available in "
        "PostgreSQL emission yet"
    )


@pytest.mark.parametrize(
    ("relation", "expected"),
    [
        pytest.param(
            _relation(OC, _join(FULL, "orders", on=_order_customer(INT_NULLABLE))),
            f"{ORDERS_FROM}\nFULL JOIN {CUSTOMER} ON {ORDER_CUSTOMER_SQL}",
            id="nullable-int",
        ),
        pytest.param(
            _relation(
                OC, _join(FULL, "orders", on=_order_customer(CUSTOMER_ID, CUSTOMER_ID))
            ),
            f"{ORDERS_FROM}\nFULL JOIN {CUSTOMER} ON {ORDER_CUSTOMER_SQL}",
            id="alias-of-int",
        ),
        pytest.param(
            _relation(OC, _full_on("customer.id", "==", "orders.customer_id")),
            f'{ORDERS_FROM}\nFULL JOIN {CUSTOMER} ON "customer"."id" = '
            '"orders"."customer_id"',
            id="target-side-first",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_binary(
                        _order_customer(),
                        "and",
                        _binary(
                            _compare(
                                _read(OC, "orders.amount"),
                                "==",
                                _read(OC, "customer.region_id"),
                            ),
                            "and",
                            _compare(
                                _read(OC, "orders.id"), "==", _read(OC, "customer.id")
                            ),
                        ),
                    ),
                ),
            ),
            f"{ORDERS_FROM}\nFULL JOIN {CUSTOMER} ON ({ORDER_CUSTOMER_SQL}) AND "
            '(("orders"."amount" = "customer"."region_id") AND '
            '("orders"."id" = "customer"."id"))',
            id="nested-and",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    ORDER_CUSTOMER,
                    on=_compare(
                        _read(OC, "customer.region_id"),
                        "==",
                        _read(OC, "orders.amount"),
                    ),
                ),
            ),
            f"{ORDERS_FROM}\nFULL JOIN {CUSTOMER} ON ({ORDER_CUSTOMER_SQL}) AND "
            '("customer"."region_id" = "orders"."amount")',
            id="int-hop-and-int-on",
        ),
        pytest.param(
            _relation(LS, _join(FULL, "lines", *LINE_SHIP)),
            f"{LINES_FROM}\nFULL JOIN {SHIP} ON {LINE_SHIP_SQL}",
            id="composite-hop",
        ),
        pytest.param(
            _relation(
                OCR,
                _join(INNER, "orders", ORDER_CUSTOMER),
                _join(
                    FULL,
                    "customer",
                    on=_compare(
                        _read(OCR, "region.id"), "==", _read(OCR, "customer.region_id")
                    ),
                ),
            ),
            f"{ORDERS_FROM}\nINNER JOIN {CUSTOMER} ON {ORDER_CUSTOMER_SQL}\n"
            f'FULL JOIN {REGION} ON "region"."id" = "customer"."region_id"',
            id="target-of-an-earlier-join",
        ),
    ],
)
def test_a_full_join_on_int_field_equalities_across_its_sides_is_native(
    relation: RelationIR, expected: str
) -> None:
    assert _sql(relation) == expected


@pytest.mark.parametrize(
    ("relation", "binding"),
    [
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_compare(
                        _read(OC, "orders.buyer", TEXT),
                        "==",
                        _read(OC, "customer.name", TEXT),
                    ),
                ),
            ),
            "customer",
            id="text-key",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_compare(
                        _read(OC, "orders.amount"),
                        "==",
                        _read(OC, "customer.score", FLOAT),
                    ),
                ),
            ),
            "customer",
            id="int-and-float",
        ),
        pytest.param(
            _relation(OC, _full_on("orders.customer_id", "==", _literal(1))),
            "customer",
            id="int-field-and-literal",
        ),
        pytest.param(
            _relation(OC, _full_on("customer.id", "==", "customer.region_id")),
            "customer",
            id="two-target-fields",
        ),
        pytest.param(
            _relation(
                OCR,
                _join(INNER, "orders", ORDER_CUSTOMER),
                _join(
                    FULL,
                    "orders",
                    on=_compare(
                        _read(OCR, "orders.customer_id"),
                        "==",
                        _read(OCR, "customer.id"),
                    ),
                ),
            ),
            "region",
            id="two-earlier-inputs",
        ),
        pytest.param(
            _relation(OC, _full_on("orders.customer_id", "<", "customer.id")),
            "customer",
            id="not-an-equality",
        ),
        pytest.param(
            _relation(OC, _full_on("orders.customer_id", "!=", "customer.id")),
            "customer",
            id="not-equal",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_binary(
                        _order_customer(),
                        "and",
                        _binary(
                            _order_customer(),
                            "and",
                            _compare(
                                _read(OC, "orders.id"), "!=", _read(OC, "customer.id")
                            ),
                        ),
                    ),
                ),
            ),
            "customer",
            id="nested-and-bad-leaf",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_binary(
                        _order_customer(),
                        "or",
                        _compare(
                            _read(OC, "orders.id"), "==", _read(OC, "customer.id")
                        ),
                    ),
                ),
            ),
            "customer",
            id="or",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    on=_compare(
                        _binary(_read(OC, "orders.customer_id"), "+", _literal(0), INT),
                        "==",
                        _read(OC, "customer.id"),
                    ),
                ),
            ),
            "customer",
            id="computed-operand",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    ORDER_CUSTOMER,
                    on=_compare(
                        _read(OC, "customer.name", TEXT),
                        "==",
                        _read(OC, "orders.buyer", TEXT),
                    ),
                ),
            ),
            "customer",
            id="int-hop-and-text-on",
        ),
        pytest.param(
            _relation(OC, _join(FULL, "orders", ORDER_BUYER)),
            "customer",
            id="text-hop",
        ),
        pytest.param(
            _relation(
                OC, _join(FULL, "orders", ("orders.score", "customer.score", FLOAT))
            ),
            "customer",
            id="float-hop",
        ),
        pytest.param(
            _relation(
                LS,
                _join(FULL, "lines", LINE_SHIP[0], ("lines.code", "ship.code", TEXT)),
            ),
            "ship",
            id="composite-hop-with-a-text-pair",
        ),
        pytest.param(
            _relation(
                OC,
                _join(
                    FULL,
                    "orders",
                    ORDER_BUYER,
                    on=_compare(
                        _read(OC, "customer.region_id"),
                        "==",
                        _read(OC, "orders.amount"),
                    ),
                ),
            ),
            "customer",
            id="text-hop-and-int-on",
        ),
    ],
)
def test_a_full_join_on_anything_else_is_refused(
    relation: RelationIR, binding: str
) -> None:
    with pytest.raises(ValueError) as raised:
        _sql(relation)

    assert str(raised.value) == FULL_REFUSAL.format(binding)


@pytest.mark.parametrize(
    ("join", "expected"),
    [
        pytest.param(
            _join(INNER, "lines", *LINE_SHIP),
            f"INNER JOIN {SHIP} ON {LINE_SHIP_SQL}",
            id="hop",
        ),
        pytest.param(
            _join(
                LEFT,
                "lines",
                *LINE_SHIP,
                on=_compare(_read(LS, "ship.qty"), ">", _read(LS, "lines.qty")),
            ),
            f'LEFT JOIN {SHIP} ON {LINE_SHIP_SQL} AND ("ship"."qty" > "lines"."qty")',
            id="hop-then-on",
        ),
    ],
)
def test_a_composite_relationship_matches_every_pair_in_declared_order(
    join: JoinSpec, expected: str
) -> None:
    assert _sql(_relation(LS, join)) == f"{LINES_FROM}\n{expected}"


@pytest.mark.parametrize(
    ("conjuncts", "expected"),
    [
        pytest.param(("a = b",), "a = b", id="one"),
        pytest.param(("a = b", "(c) OR (d)"), "(a = b) AND ((c) OR (d))", id="two"),
        pytest.param(("x", "y", "z"), "(x) AND (y) AND (z)", id="three"),
    ],
)
def test_one_conjunct_stays_bare_and_several_are_each_parenthesized(
    conjuncts: tuple[str, ...], expected: str
) -> None:
    assert render_conjunction_sql(conjuncts) == expected


def test_a_join_binding_postgresql_would_truncate_is_refused() -> None:
    relation = _relation(("orders", LONG_BINDING), _join(CROSS, "orders"))

    with pytest.raises(IdentifierTooLongError) as raised:
        _sql(relation)

    assert str(raised.value) == (
        f'PostgreSQL identifier "{"r" * 24}..." is 64 bytes, over the 63 bytes '
        "PostgreSQL keeps of a name"
    )


@pytest.mark.parametrize(
    ("kind", "null_extends", "message"),
    [
        pytest.param("full", (0, 1), FULL_REFUSAL.format("customer"), id="plain-full"),
        pytest.param("outer", (), "'outer' is not a valid JoinKindIR", id="unknown"),
    ],
)
def test_a_join_kind_is_read_as_its_join_kind_or_refused(
    kind: str, null_extends: tuple[int, ...], message: str
) -> None:
    relation = _relation(
        OC,
        _join(
            INNER,
            "orders",
            on=_compare(
                _read(OC, "orders.buyer", TEXT), "==", _read(OC, "customer.name", TEXT)
            ),
        ),
    )
    join = replace(relation.joins[0], kind=kind, null_extends=null_extends)

    with pytest.raises(ValueError) as raised:
        _sql(replace(relation, joins=(join,)))

    assert str(raised.value) == message


def test_mysql_refuses_each_join_relation_and_keeps_the_other_artifacts() -> None:
    script = ScriptIR(
        definitions=(
            _mysql_source("orders"),
            _mysql_source("customers"),
            _relation(OC, _join(INNER, "orders", ORDER_CUSTOMER), name="order_names"),
            _order_ids(),
            # Refused before its name, too long for MySQL, is read.
            _relation(OC, _join(INNER, "orders", ORDER_CUSTOMER), name="n" * 65),
        )
    )

    result = emit_mysql_sql(script)

    assert [(artifact.name, artifact.sql) for artifact in result.artifacts] == [
        ("order_ids", "SELECT\n    `id` AS `id`\nFROM `shop`.`orders`"),
    ]
    assert result.diagnostics == tuple(
        Diagnostic(
            code="PIE-B1000",
            severity=Severity.ERROR,
            message=(
                f"MySQL SQL emission is not implemented for RelationIR: {name}. "
                "MySQL JOIN emission is not available yet"
            ),
            location=SourceLocation(
                path="join-emission.pietto",
                line=3,
                column=5,
                end_line=3,
                end_column=9,
            ),
        )
        for name in ("order_names", "n" * 65)
    )


def _mysql_source(name: str) -> SourceIR:
    return SourceIR(
        symbol=SymbolId(SymbolNamespace.RELATION, name),
        name=name,
        shape_symbol=None,
        row_schema=RowSchemaIR(fields=()),
        connector=ConnectorIR(
            name="mysql.table", arguments=(f"shop.{name}",), span=SPAN
        ),
        span=SPAN,
    )


def _order_ids() -> RelationIR:
    orders = SymbolId(SymbolNamespace.RELATION, "orders")
    return RelationIR(
        symbol=SymbolId(SymbolNamespace.RELATION, "order_ids"),
        name="order_ids",
        kind=RelationKindIR.QUERY,
        source=RelationSourceIR(target=orders, name="orders", span=SPAN),
        filter=None,
        projections=(
            ProjectionIR(
                name="id",
                expression=FieldRefIR(
                    span=SPAN,
                    value_type=INT,
                    name="id",
                    qualifier=(),
                    field=FieldId(owner=orders, name="id"),
                ),
                type_ref=INT,
                span=SPAN,
            ),
        ),
        row_schema=RowSchemaIR(fields=()),
        span=SPAN,
    )


def _compile_source(source: str) -> ScriptIR:
    parsed = parse_source(source, path="join-emission.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert not any(d.severity is Severity.ERROR for d in semantic.diagnostics), (
        semantic.diagnostics
    )
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.diagnostics == ()
    assert lowered.ir is not None
    return lowered.ir


def test_complete_join_sql_matches_golden() -> None:
    result = emit_postgres_sql(_compile_source((REPO_ROOT / GOLDEN_INPUT).read_text()))

    assert result.diagnostics == ()
    assert [(a.name, a.sql) for a in result.artifacts] == list(GOLDEN_ARTIFACTS.items())
    assert (
        "\n\n".join(f"-- {a.name}\n{a.sql};" for a in result.artifacts) + "\n"
    ).encode() == (REPO_ROOT / GOLDEN_SQL).read_bytes()


@pytest.mark.parametrize("mode", ["loose", "checked", "strict"])
def test_cli_join_golden_checks_and_emits_in_every_mode(
    mode: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(REPO_ROOT)
    assert cli.main(["check", GOLDEN_INPUT, "--check-mode", mode]) == 0
    checked = capsys.readouterr()
    assert checked.err == ""
    assert (
        cli.main(
            ["emit-sql", GOLDEN_INPUT, "--dialect", "postgres", "--check-mode", mode]
        )
        == 0
    )
    emitted = capsys.readouterr()
    assert emitted.err == ""
    assert emitted.out.encode() == (REPO_ROOT / GOLDEN_SQL).read_bytes()


def test_readme_quick_start_checks_strictly_and_emits_the_sql_it_prints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The README quick start runs as written and prints the SQL it shows."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("## Quick start", 1)[1].split("\n## ", 1)[0]
    blocks = re.findall(r"```(\w+)\n(.*?)```", section, re.S)
    assert [language for language, _ in blocks] == ["pietto", "bash", "sql"]
    source, commands, sql = (body for _, body in blocks)
    assert "`check` prints `OK: shop.pietto`" in section
    (tmp_path / "shop.pietto").write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    check, emit = (shlex.split(line) for line in commands.splitlines())
    assert check[:2] == ["pietto", "check"] and emit[:2] == ["pietto", "emit-sql"]
    assert cli.main([*check[1:], "--check-mode", "strict", "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["diagnostics"] == []
    assert cli.main(check[1:]) == 0
    assert capsys.readouterr() == ("OK: shop.pietto\n", "")
    assert cli.main(emit[1:]) == 0
    assert capsys.readouterr() == (sql, "")


@pytest.mark.parametrize("output_format", ["text", "json"])
@pytest.mark.parametrize(
    ("dialect", "joins", "reason", "expect_warning"),
    [
        (
            "mysql",
            "    let p = peers\n    inner join p on rows.id == p.id\n",
            "MySQL JOIN emission is not available yet",
            False,
        ),
        (
            "postgres",
            "    let p = peers\n    full join p on rows.name == p.name\n",
            FULL_REFUSAL.format("p"),
            True,
        ),
        (
            "postgres",
            "    where any(rows.id == s.id for s in peers)\n"
            "    let p = peers\n    full join p on rows.id == p.id\n",
            "A SEMI or ANTI JOIN before FULL JOIN p is not available in PostgreSQL emission yet",
            False,
        ),
    ],
    ids=["mysql", "text-full", "semi-full"],
)
def test_cli_refuses_one_join_relation_and_keeps_other_artifacts(
    output_format: str,
    dialect: str,
    joins: str,
    reason: str,
    expect_warning: bool,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = (
        "shape Row:\n    id: Int\n    name: Text\n"
        f'source rows: Row = {dialect}.table("shop.rows")\n'
        f'source peers: Row = {dialect}.table("shop.peers")\n'
        "query okay:\n    from rows\n    select:\n        id\n"
        "query refused:\n    from rows\n" + joins + "    select:\n        rows.id\n"
    )
    path = tmp_path / "refusal.pietto"
    path.write_text(source)
    assert (
        cli.main(
            ["emit-sql", str(path), "--dialect", dialect, "--format", output_format]
        )
        == 1
    )
    captured = capsys.readouterr()
    quote = "`" if dialect == "mysql" else '"'
    expected_sql = (
        f"SELECT\n    {quote}id{quote} AS {quote}id{quote}\n"
        f"FROM {quote}shop{quote}.{quote}rows{quote}"
    )
    backend = "MySQL" if dialect == "mysql" else "PostgreSQL"
    message = (
        f"{backend} SQL emission is not implemented for RelationIR: refused. {reason}"
    )
    warning_message = (
        "Single-file SQL emission is unavailable because this FULL JOIN equality is "
        "not between canonical Int fields; this warning does not change check's "
        "exit status, but emit-sql will refuse this relation."
    )
    if output_format == "text":
        assert captured.out == f"-- okay\n{expected_sql};\n"
        assert captured.err == (
            (
                f"{path}:13:20 PIE-S2385 warning: {warning_message}\n"
                if expect_warning
                else ""
            )
            + f"{path}:10:1 PIE-B1000 error: {message}\n"
        )
    else:
        assert captured.err == ""
        payload = json.loads(captured.out)
        assert payload["ok"] is False
        assert payload["cli_errors"] == []
        assert payload["artifacts"] == [
            {"kind": "relation", "name": "okay", "sql": expected_sql}
        ]
        diagnostics = payload["diagnostics"]
        assert len(diagnostics) == 1 + expect_warning
        if expect_warning:
            warning = diagnostics.pop(0)
            assert (warning["code"], warning["severity"]) == (
                "PIE-S2385",
                "warning",
            )
            assert warning["message"] == warning_message
            assert warning["location"]["path"] == str(path)
            assert (warning["location"]["line"], warning["location"]["column"]) == (
                13,
                20,
            )
        diagnostic = diagnostics[0]
        assert diagnostic["code"] == "PIE-B1000"
        assert diagnostic["severity"] == "error"
        assert diagnostic["message"] == message
        assert diagnostic["location"]["path"] == str(path)
        assert diagnostic["location"]["line"] == 10
        assert diagnostic["location"]["column"] == 1


def _postgres_source(name: str) -> SourceIR:
    source = _mysql_source(name)
    return replace(source, connector=replace(source.connector, name="postgres.table"))


def _projection(name: str, expression: ExpressionIR) -> ProjectionIR:
    return ProjectionIR(
        name=name, expression=expression, type_ref=expression.value_type, span=SPAN
    )


@pytest.mark.parametrize("kind", [INNER, LEFT, RIGHT, SEMI, ANTI, FULL])
def test_join_and_exists_conditions_keep_the_text_null_guard(kind: JoinKindIR) -> None:
    null = LiteralIR(span=SPAN, value_type=BOOL, value=None)
    condition = CallIR(
        span=SPAN,
        value_type=BOOL,
        callee="coalesce",
        callee_symbol=None,
        arguments=(null, null),
    )
    relation = _relation(OC, _join(kind, "orders", on=condition))
    with pytest.raises(ValueError) as raised:
        _sql(relation)
    assert str(raised.value) == (
        FULL_REFUSAL.format("customer")
        if kind is FULL
        else "PostgreSQL types a CASE, COALESCE or NULLIF of only NULL values as text, "
        "which a condition does not take"
    )


@pytest.mark.parametrize("wrapped", [False, True])
def test_untyped_null_output_is_refused_when_a_join_target_reads_it(
    wrapped: bool,
) -> None:
    null = LiteralIR(span=SPAN, value_type=BOOL, value=None)
    expression: ExpressionIR = null
    if wrapped:
        expression = CallIR(
            span=SPAN,
            value_type=BOOL,
            callee="coalesce",
            callee_symbol=None,
            arguments=(null, null),
        )
    upstream = replace(
        _order_ids(),
        symbol=SymbolId(SymbolNamespace.RELATION, "named_customers"),
        name="named_customers",
        projections=(_projection("value", expression),),
    )
    joined = replace(
        _relation(("orders", "c"), _join(CROSS, "orders")),
        projections=(_projection("id", _read(("orders", "c"), "orders.id")),),
    )
    result = emit_postgres_sql(
        ScriptIR(definitions=(_postgres_source("orders"), upstream, joined))
    )
    # q defines named_customers, the JOIN target it reads, as a CTE.
    assert result.artifacts == ()
    assert result.diagnostics == tuple(
        Diagnostic(
            code="PIE-B1000",
            severity=Severity.ERROR,
            message=f"PostgreSQL SQL emission is not implemented for RelationIR: {name}. "
            "PostgreSQL types a NULL output that another relation reads as text, "
            "which Pietto leaves untyped",
            location=SourceLocation(
                path=SPAN.path, line=3, column=5, end_line=3, end_column=9
            ),
        )
        for name in ("named_customers", "q")
    )


def test_grouped_self_join_keeps_both_occurrence_keys_and_the_existing_tail() -> None:
    left, right = _read(CP, "customers.id"), _read(CP, "peer.id")
    count = AggregateCallIR(span=SPAN, value_type=INT, function="count", arguments=())
    relation = replace(
        _relation(CP, _join(CROSS, "customers")),
        projections=(
            _projection("left_id", left),
            _projection("right_id", right),
            _projection("n", count),
        ),
        group_keys=(left, right),
        result_predicate=ResultPredicateIR(
            expression=_compare(count, ">", _literal(1)), span=SPAN
        ),
        order_by=(
            OrderItemIR(expression=right, direction=OrderDirectionIR.DESC, span=SPAN),
        ),
        limit=LimitIR(value=5, span=SPAN),
    )
    result = emit_postgres_sql(
        ScriptIR(definitions=(_postgres_source("customers"), relation))
    )
    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        'SELECT\n    "customers"."id" AS "left_id",\n    "peer"."id" AS "right_id",\n'
        '    COUNT(*) AS "n"\nFROM "shop"."customers" AS "customers"\n'
        'CROSS JOIN "shop"."customers" AS "peer"\nGROUP BY\n'
        '    "customers"."id",\n    "peer"."id"\nHAVING\n    COUNT(*) > 1\n'
        'ORDER BY\n    "peer"."id" DESC\nLIMIT 5'
    )


def test_pending_exists_precedes_authored_where() -> None:
    condition = _compare(_read(CO, "customers.id"), ">", _literal(1))
    relation = replace(
        _relation(CO, _join(SEMI, "customers", CUSTOMER_ORDER)),
        projections=(_projection("id", _read(CO, "customers.id")),),
        filter=FilterIR(expression=condition, span=SPAN),
    )
    result = emit_postgres_sql(
        ScriptIR(
            definitions=(
                _postgres_source("customers"),
                _postgres_source("orders"),
                relation,
            )
        )
    )
    assert result.diagnostics == ()
    assert result.artifacts[0].sql == (
        'SELECT\n    "customers"."id" AS "id"\n' + CUSTOMERS_FROM + "\n"
        f'WHERE ({HAS_ORDERS}) AND ("customers"."id" > 1)'
    )


_GOLDEN_INVENTORY = runpy.run_path(str(REPO_ROOT / "scripts/check_goldens.py"))
_GOLDEN_PROGRAMS = sorted(
    {
        path
        for name, paths in _GOLDEN_INVENTORY["FIXTURE_INPUTS"].items()
        if name.endswith(".sql")
        for path in paths
    }
)


@pytest.mark.parametrize("input_path", _GOLDEN_PROGRAMS)
@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_appending_a_join_keeps_every_existing_golden_artifact(
    input_path: str, dialect: str
) -> None:
    source = (
        (REPO_ROOT / input_path)
        .read_text()
        .replace("mysql.table", "postgres.table")
        .replace("postgres.table", f"{dialect}.table")
    )
    original = _compile_source(source)
    shaped = next(
        (
            item
            for item in original.definitions
            if isinstance(item, SourceIR)
            and item.shape_symbol is not None
            and item.row_schema.fields
        ),
        None,
    )
    if shaped is None:
        pytest.skip("The golden input has no shaped source")
    name, binding = "join_probe", "join_probe_peer"
    while name in source or binding in source:
        name += "0"
        binding += "0"
    appended = _compile_source(
        source + f"\nquery {name}:\n    from {shaped.name}\n"
        f"    let {binding} = {shaped.name}\n    cross join {binding}\n"
        f"    select:\n        join_probe_key = {shaped.name}.{shaped.row_schema.fields[0].name}\n"
    )
    emitter = emit_postgres_sql if dialect == "postgres" else emit_mysql_sql
    before, after = emitter(original), emitter(appended)
    if dialect == "postgres":
        assert after.artifacts[:-1] == before.artifacts
        assert after.artifacts[-1].name == name
        assert "CROSS JOIN " in after.artifacts[-1].sql
        assert after.diagnostics == before.diagnostics
    else:
        assert after.artifacts == before.artifacts
        assert after.diagnostics[:-1] == before.diagnostics
        assert after.diagnostics[-1].code == "PIE-B1000"
        assert after.diagnostics[-1].message == (
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "MySQL JOIN emission is not available yet"
        )


@pytest.mark.parametrize("command", ["check", "emit-sql"])
def test_join_golden_is_deterministic_across_hash_seeds(command: str) -> None:
    arguments = [
        sys.executable,
        "-c",
        "from pietto.cli import main; raise SystemExit(main())",
        command,
        GOLDEN_INPUT,
    ]
    if command == "emit-sql":
        arguments.extend(["--dialect", "postgres"])
    outputs = []
    for seed in ("0", "1"):
        environment = {
            **os.environ,
            "PYTHONHASHSEED": seed,
            "PYTHONPATH": str(REPO_ROOT / "src"),
        }
        completed = subprocess.run(
            arguments, cwd=REPO_ROOT, env=environment, capture_output=True, check=False
        )
        assert completed.returncode == 0, completed.stderr
        outputs.append((completed.stdout, completed.stderr))
    assert outputs[0] == outputs[1]
