"""Single-file SQL of inline ``def`` calls: the SQL of each call written out.

The project form of the same law lives with the project scalar SQL owner.
"""

from __future__ import annotations

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_backend

SHAPES = (
    "shape Row:\n"
    "    id: Int\n"
    "    n: Int | None\n"
    "    text: Text\n"
    "    note: Text | None\n"
    "    lower: Text\n"
    "    price: Decimal(10, 2)\n"
    "    qty: Decimal(10, 2) | None\n"
    'source rows: Row = postgres.table("rows")\n'
)
# A program that calls defs, and the same program with each call written out
# by hand.
PROGRAMS = {
    "where_two_defs": (
        "def reachable(email: Text | None, coupon: Text | None) -> Bool | None: "
        'return email like "%@%" and coupon is None\n'
        "def positive(v: Int) -> Bool | None: return v > 0\n"
        "table t:\n    from rows\n    where positive(id) and reachable(note, note)\n"
        "    select:\n        id\n",
        "table t:\n    from rows\n"
        '    where (id > 0) and (note like "%@%" and note is None)\n'
        "    select:\n        id\n",
    ),
    "repeated_parameter_and_call": (
        "def small(v: Int) -> Bool | None: return v > 0 and v < 9\n"
        "def clean(s: Text) -> Text: return lower(trim(s))\n"
        "table t:\n    from rows\n    let c = clean(text)\n"
        "    where small(id) and clean(text) != clean(text)\n"
        "    select:\n        id\n        cc = c\n        d = clean(text)\n"
        "    order by id desc\n",
        "table t:\n    from rows\n    let c = (lower(trim(text)))\n"
        "    where (id > 0 and id < 9) and (lower(trim(text))) != (lower(trim(text)))\n"
        "    select:\n        id\n        cc = c\n        d = (lower(trim(text)))\n"
        "    order by id desc\n",
    ),
    "nested_defs": (
        "def tag(s: Text) -> Text: return upper(s)\n"
        "def label(s: Text, v: Int) -> Text: "
        'return tag(s) if v > 0 else "none"\n'
        "table t:\n    from rows\n    select:\n        id\n"
        "        l = label(text, id)\n",
        "table t:\n    from rows\n    select:\n        id\n"
        '        l = ((upper(text)) if id > 0 else "none")\n',
    ),
    "alias_typed_signature": (
        "type Count = Int\n"
        "def bump(v: Count) -> Count | None: return v + 1\n"
        "table t:\n    from rows\n    select:\n        id\n        v = bump(id)\n",
        "type Count = Int\n"
        "table t:\n    from rows\n    select:\n        id\n        v = (id + 1)\n",
    ),
    "parameter_named_like_a_function": (
        "def f(upper: Text) -> Text: return upper(upper)\n"
        "table t:\n    from rows\n    select:\n        id\n        v = f(lower)\n",
        "table t:\n    from rows\n    select:\n        id\n        v = upper(lower)\n",
    ),
    # A Decimal value in a list of Int options, as by hand.
    "decimal_int_membership": (
        "def cheap(p: Decimal) -> Bool | None: return p in (1, 2)\n"
        "def among(k: Int, p: Decimal | None) -> Bool | None: "
        "return k not in (p, 3)\n"
        "table t:\n    from rows\n    where cheap(price) or among(id, qty)\n"
        "    select:\n        id\n",
        "table t:\n    from rows\n    where (price in (1, 2)) or (id not in (qty, 3))\n"
        "    select:\n        id\n",
    ),
    # A Decimal product inside sum and avg, as by hand.
    "decimal_product_aggregate": (
        "def line(p: Decimal, q: Decimal | None) -> Decimal | None: "
        "return p * q\n"
        "table t:\n    from rows\n    group by id\n    select:\n        id\n"
        "        s = sum(line(price, qty))\n        a = avg(line(price, qty))\n",
        "table t:\n    from rows\n    group by id\n    select:\n        id\n"
        "        s = sum((price * qty))\n        a = avg((price * qty))\n",
    ),
}
EMITTERS = {
    "postgres": sql_api.emit_postgres_sql,
    "mysql": mysql_backend.emit_mysql_sql,
}


def _sql(source: str, dialect: str) -> tuple[str, ...]:
    parsed = parser_api.parse_source(source, path="m.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.diagnostics == ()
    built = ir_api.build_ir(semantic.script or parsed.ast, semantic.model)
    assert built.diagnostics == () and built.ir is not None
    emitted = EMITTERS[dialect](built.ir)
    assert emitted.diagnostics == ()
    return tuple(artifact.sql for artifact in emitted.artifacts)


@pytest.mark.parametrize("dialect", EMITTERS)
@pytest.mark.parametrize(("called", "written"), PROGRAMS.values(), ids=PROGRAMS)
def test_def_calls_emit_the_sql_of_the_calls_written_out(
    dialect: str, called: str, written: str
) -> None:
    prefix = SHAPES.replace("postgres.table", f"{dialect}.table")
    outputs = [_sql(prefix + relation, dialect) for relation in (called, written)]
    assert outputs[0] == outputs[1]
    assert "SELECT" in "\n\n".join(outputs[0])
