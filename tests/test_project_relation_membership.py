"""Where a `[not] in` relation read may be written in an EXPLICIT_MODULES project.

Inside a table or query body the read is resolved like a `from` name and is
available only in WHERE and in the SELECT of an ungrouped query (D70.04); every
other place is PIE-S2350 at the read, from relation name resolution. Outside a
relation body, in single-file and in LEGACY_FLAT projects the read keeps its
pre-admission PIE-S2350.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto import cli
from pietto.parser_api import parse_source
from pietto.semantic import analyze

IDS = "query ids:\n    from rhs\n    select:\n        id\n"


POSITION = (
    "IN relation reference is available only in WHERE and in the SELECT of an "
    "ungrouped query, not in {}."
)
COMPLETION = (
    "PIE-S2333",
    "Project relation semantic completion is unavailable: result",
    10,
    1,
)


@pytest.mark.parametrize(
    ("body", "diagnostics"),
    (
        (
            IDS + "query result:\n    from lhs\n    let:\n        f = id in ids\n"
            "    select:\n        id\n        f\n",
            [("PIE-S2350", POSITION.format("a row let"), 13, 13)],
        ),
        (
            IDS + "query result:\n    from lhs\n    inner join rhs as r:\n"
            "        from lhs\n        on lhs.id == r.id and r.key in ids\n"
            "    select:\n        a = lhs.id\n",
            [("PIE-S2350", POSITION.format("JOIN ON"), 14, 31)],
        ),
        (
            IDS + "query result:\n    from lhs\n    select:\n        a = lhs.id\n"
            "    order by:\n        a in ids\n",
            [("PIE-S2350", POSITION.format("ORDER BY"), 15, 9)],
        ),
        (
            IDS + "query result:\n    from lhs\n    group by:\n        id\n"
            "    select:\n        id\n        f = id in ids\n",
            [
                ("PIE-S2350", POSITION.format("the SELECT of a grouped query"), 16, 13),
                COMPLETION,
            ],
        ),
        (
            IDS + "query result:\n    from lhs\n    select:\n        n = count()\n"
            "        f = 1 in ids\n",
            [
                ("PIE-S2350", POSITION.format("the SELECT of a grouped query"), 14, 13),
                COMPLETION,
            ],
        ),
        (
            IDS + "query result:\n    from lhs\n    select:\n        a = lhs.id\n"
            "        n = count()\n    satisfying:\n        n in ids\n",
            [("PIE-S2350", POSITION.format("SATISFYING"), 16, 9), COMPLETION],
        ),
        (
            IDS + "query result:\n    from lhs\n    select:\n        id\n"
            "        r = row_number() window:\n            order by:\n"
            "                id\n    qualify:\n        r in ids\n",
            [("PIE-S2350", POSITION.format("QUALIFY"), 18, 9)],
        ),
        (
            IDS + "query result:\n    from lhs\n    select:\n        id\n"
            "        r = row_number() window:\n            order by:\n"
            "                id in ids\n",
            [
                ("PIE-S2350", POSITION.format("a window"), 16, 17),
                ("PIE-S2103", "Unknown function: row_number", 14, 13),
            ],
        ),
    ),
    ids=(
        "row_let",
        "join_on",
        "order_by",
        "grouped_select",
        "aggregate_select",
        "satisfying",
        "qualify",
        "window_order",
    ),
)
def test_reads_outside_where_and_ungrouped_select_are_refused(
    tmp_path: Path, body: str, diagnostics: list
) -> None:
    assert _check(tmp_path, body) == (1, diagnostics)


def _check(tmp_path: Path, text: str, *, schema_version: int = 2):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(
        probe.CONFIG.replace("schema_version = 2", f"schema_version = {schema_version}")
    )
    (tmp_path / "main.pietto").write_text(
        probe.JOIN_WITNESS_HEADER.format(target="postgres") + text
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    document = json.loads(out.getvalue())
    return code, [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ]


GATE = "IN relation reference semantics are not implemented."


def test_reads_outside_relation_bodies_keep_their_gate(tmp_path: Path) -> None:
    text = (
        IDS
        + "constraint Known(x: Int) -> Bool:\n    x in ids\n"
        + "derive known(x: Int) -> Bool:\n    x not in ids\n"
        + "shape Checked:\n    id: Int not null\n    check known_id:\n"
        + "        id in ids\n"
        + "relationship link:\n    endpoint l: lhs\n    endpoint r: rhs\n"
        + "    on l.id in ids\n"
        + "type Small = Int ensure value in ids\n"
        + "source odd: Row is postgres.table(1 in ids)\n"
    )
    assert _check(tmp_path, text) == (
        1,
        [
            ("PIE-S2350", GATE, 11, 5),
            ("PIE-S2350", GATE, 13, 5),
            ("PIE-S2350", GATE, 17, 9),
            ("PIE-S2350", GATE, 21, 8),
            ("PIE-S2350", GATE, 22, 25),
            ("PIE-S2350", GATE, 23, 35),
        ],
    )


def test_single_file_and_legacy_flat_keep_the_gate(tmp_path: Path) -> None:
    body = (
        IDS
        + "query result:\n    from lhs\n    where id in ids\n    select:\n        id\n"
    )
    parsed = parse_source(
        probe.JOIN_WITNESS_HEADER.format(target="postgres") + body, path="one.pietto"
    )
    assert parsed.ast is not None
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(parsed.ast).diagnostics
    ] == [("PIE-S2350", GATE, 12, 11)]
    assert _check(tmp_path / "flat", body, schema_version=1) == (
        1,
        [("PIE-S2350", GATE, 12, 11)],
    )
    assert _check(tmp_path / "modules", body) == (0, [])


def test_unknown_and_cyclic_reads_are_semantic_errors(tmp_path: Path) -> None:
    assert _check(
        tmp_path / "unknown",
        "query result:\n    from lhs\n    where id in missing\n    select:\n"
        "        id\n",
    ) == (1, [("PIE-S2301", "Unknown relation: missing", 8, 11)])
    assert _check(
        tmp_path / "cycle",
        "query result:\n    from lhs\n    where id in result\n    select:\n"
        "        id\n",
    ) == (1, [("PIE-S2302", "Relation cycle detected: result -> result", 8, 11)])


def test_a_let_read_by_in_is_read_like_any_other_input(tmp_path: Path) -> None:
    """A let read only by `in` is read; it may be read again by any block."""
    let = "    let picked:\n        from rhs\n        select:\n            id\n"
    assert _check(
        tmp_path / "once",
        "query result:\n" + let + "    from lhs\n    where id in picked\n"
        "    select:\n        id\n",
    ) == (0, [])
    assert _check(
        tmp_path / "twice",
        "query result:\n" + let + "    from picked\n    where id in picked\n"
        "    select:\n        id\n",
    ) == (0, [])
    assert _check(
        tmp_path / "self",
        "query result:\n    let picked:\n        from rhs\n"
        "        where id in picked\n        select:\n            id\n"
        "    from picked\n    select:\n        id\n",
    ) == (1, [("PIE-S2302", "Relation cycle detected: picked -> picked", 9, 15)])


PAIR = "Invalid operands for operator {}: expected same canonical membership operands"


def test_a_left_value_must_pair_with_the_read_column_like_a_literal_list(
    tmp_path: Path,
) -> None:
    """The read block's one known column types the test like a literal-list
    option, wherever the read is written; a block whose columns are known only
    after completion is paired at emission instead."""
    labels = 'query labels:\n    from rhs\n    select:\n        t = "x"\n'
    let = "    let picked:\n        from rhs\n        select:\n            id\n"
    union = "query u:\n    union all:\n        from ids\n        from ids\n"
    assert _check(
        tmp_path / "where",
        IDS + 'query result:\n    from lhs\n    where "a" in ids\n    select:\n'
        "        id\n",
    ) == (1, [("PIE-S2105", PAIR.format("in"), 12, 11)])
    assert _check(
        tmp_path / "select",
        labels + "query result:\n    from lhs\n    select:\n        id\n"
        "        f = key not in labels\n",
    ) == (1, [("PIE-S2105", PAIR.format("not in"), 14, 13)])
    assert _check(
        tmp_path / "let",
        "query result:\n" + let + '    from lhs\n    where "z" not in picked\n'
        "    select:\n        id\n",
    ) == (1, [("PIE-S2105", PAIR.format("not in"), 12, 11)])
    assert _check(
        tmp_path / "join",
        IDS + "query result:\n    from lhs\n    inner join rhs as r:\n"
        '        from lhs\n        on lhs.id == r.id\n    where "x" in ids\n'
        "    select:\n        a = lhs.id\n",
    ) == (1, [("PIE-S2105", PAIR.format("in"), 15, 11)])
    assert _check(
        tmp_path / "set",
        union + IDS + 'query result:\n    from lhs\n    where "a" in u\n'
        "    select:\n        id\n",
    ) == (0, [])
    # A typed VALUES header declares its column before completion.
    assert _check(
        tmp_path / "values",
        "query result:\n    let v:\n        values(t: Text not null):\n"
        '            "x"\n    from lhs\n    where id in v\n    select:\n'
        "        id\n",
    ) == (1, [("PIE-S2105", PAIR.format("in"), 11, 11)])


WIDTH = "Invalid operands for operator {}: expected a relation with one output column"


def test_a_block_with_known_columns_is_read_only_with_exactly_one(
    tmp_path: Path,
) -> None:
    """The width of a block whose columns are known before completion is
    checked at the test, and a bare NULL takes the type of its one column like
    a NULL in a literal list; a set is checked at emission instead."""
    where = "query result:\n    from lhs\n    where {} in {}\n    select:\n        a = lhs.id\n"
    pairs = "query pairs:\n    from rhs\n    select:\n        id\n        key\n"
    let = (
        "query result:\n    let picked:\n        from rhs\n        select:\n"
        "            id\n            key\n    from lhs\n    where id in picked\n"
        "    select:\n        a = lhs.id\n"
    )
    union = "query u:\n    union all:\n        from rhs\n        from rhs\n"
    assert _check(tmp_path / "source", where.format("id", "rhs")) == (
        1,
        [("PIE-S2105", WIDTH.format("in"), 8, 11)],
    )
    assert _check(
        tmp_path / "query",
        pairs + "query result:\n    from lhs\n    select:\n        a = lhs.id\n"
        "        f = key not in pairs\n",
    ) == (1, [("PIE-S2105", WIDTH.format("not in"), 15, 13)])
    assert _check(tmp_path / "let", let) == (
        1,
        [("PIE-S2105", WIDTH.format("in"), 13, 11)],
    )
    # The width is reported before the errors of the left value.
    assert _check(tmp_path / "left", where.format("nope", "rhs")) == (
        1,
        [
            ("PIE-S2105", WIDTH.format("in"), 8, 11),
            ("PIE-S2102", "Unknown field: nope", 8, 11),
        ],
    )
    assert _check(tmp_path / "null_width", where.format("null", "rhs")) == (
        1,
        [("PIE-S2105", WIDTH.format("in"), 8, 11)],
    )
    assert _check(tmp_path / "null", IDS + where.format("null", "ids")) == (0, [])
    assert _check(
        tmp_path / "null_not_in",
        IDS + "query result:\n    from lhs\n    select:\n        a = lhs.id\n"
        "        f = null not in ids\n",
    ) == (0, [])
    assert _check(tmp_path / "set", union + where.format("id", "u")) == (0, [])
    values = "query v:\n    values(a: Int not null, b: Int nullable):\n        1, 2\n"
    assert _check(tmp_path / "values", values + where.format("id", "v")) == (
        1,
        [("PIE-S2105", WIDTH.format("in"), 11, 11)],
    )
    one = "query w:\n    values(a: Int nullable):\n        null\n"
    assert _check(tmp_path / "values_one", one + where.format("null", "w")) == (
        0,
        [],
    )


def test_header_parameters_and_reads_keep_their_own_positions(
    tmp_path: Path,
) -> None:
    """A parameter is not a left value of `in`, and a parameterized query is
    never read by `exists`, `scalar` or `in`."""
    assert _check(
        tmp_path / "operand",
        IDS + "query result(cutoff: Int not null):\n    from lhs\n"
        "    where cutoff in ids\n    select:\n        id\n",
    ) == (
        1,
        [("PIE-S2355", "Query parameters are not available in this position.", 12, 11)],
    )
    parameterized = (
        "query p(cutoff: Int not null):\n    from rhs\n    where id > cutoff\n"
        "    select:\n        id\n"
    )
    read = (
        "PIE-S2356",
        "A query with parameters cannot be the input of another relation.",
    )
    assert _check(
        tmp_path / "target",
        parameterized + "query result:\n    from lhs\n"
        "    where id in p and exists p and id <= scalar p.id\n    select:\n"
        "        id\n",
    ) == (1, [(*read, 13, 11), (*read, 13, 23), (*read, 13, 42)])
