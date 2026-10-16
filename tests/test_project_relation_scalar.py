"""Scalar relation reads of explicit-module projects: availability and typing.

``scalar r.c`` names a relation like FROM does and reads one output column of
it. Its type is that column's type made NULLABLE; it is available only in
WHERE and ungrouped SELECT values, and only in EXPLICIT_MODULES projects.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto import cli

HEAD = """shape Row:
    id: Int not null
    key: Int nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
"""
T = "    let t:\n        from rhs\n        select:\n            rid = id\n"
JOIN = "    from lhs\n    inner join rhs as r:\n        from lhs\n        on lhs.id == r.id\n"
SET = "query both:\n    union all:\n        from lhs\n        from rhs\n"
OVER = "query over:\n    from both\n    select:\n        id\n"
LATER = "are not known before completion."


def _check(tmp_path: Path, body: str, *, schema: int = 2):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(
        probe.CONFIG.replace("schema_version = 2", f"schema_version = {schema}")
    )
    (tmp_path / "main.pietto").write_text(HEAD + body)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    document = json.loads(out.getvalue())
    return code, [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ]


def _position(where: str, line: int, column: int):
    return (
        "PIE-S2348",
        f"Scalar relation read is available only in WHERE and in the SELECT of "
        f"an ungrouped query, not in {where}.",
        line,
        column,
    )


def _later(read: str, line: int, column: int):
    relation = read.split(".")[0]
    return (
        "PIE-S2348",
        f"Scalar relation read {read} is not yet available: the columns of "
        f"{relation} {LATER}",
        line,
        column,
    )


ACCEPTED = {
    "where_and_select": "query q:\n"
    + T
    + "    from lhs\n    where id == scalar t.rid\n"
    "    select:\n        id\n        k = scalar rhs.key\n",
    "grouped_where": "query q:\n" + T + "    from lhs\n    where id == scalar t.rid\n"
    "    group by:\n        id\n    select:\n        id\n        n = count()\n",
    "read_block_reads": "query q:\n" + T + "    let u:\n        from rhs\n"
    "        where id == scalar t.rid\n        select:\n            x = scalar lhs.key\n"
    "    from lhs\n    select:\n        id\n        y = scalar u.x + 1\n",
    "join_consumer": "query q:\n" + T + "    from lhs\n    inner join rhs as r:\n"
    "        from lhs\n        on lhs.id == r.id\n    where lhs.id == scalar t.rid\n"
    "    select:\n        id = lhs.id\n",
    "join_select": "query q:\n" + JOIN + "    select:\n        a = lhs.id\n"
    "        b = scalar rhs.key\n",
    "set_consumer": SET + "query q:\n    from both\n    where id == scalar rhs.id\n"
    "    select:\n        id\n",
    # A let may be read any number of times, before or after it is written.
    "let_read_twice": "query q:\n" + T + "    from lhs\n    where id == scalar t.rid\n"
    "    select:\n        id\n        s = scalar t.rid\n",
    "forward_let": "query q:\n    let u:\n        from lhs\n"
    "        where id == scalar t.rid\n        select:\n            id\n"
    + T
    + "    from u\n    select:\n        id\n",
    # A typed VALUES header declares its columns before completion.
    "values_let": "query q:\n    let v:\n        values(rid: Int not null):\n"
    "            1\n    from lhs\n    where id == scalar v.rid\n    select:\n"
    "        id\n        s = scalar v.rid\n",
}
# Every refused position and read, with its full ordered diagnostic list; a
# refused read stays untyped, so its own consumer may report a later cause.
REFUSED = {
    "row_let": (
        "query q:\n" + T + "    from lhs\n    let:\n        v = scalar t.rid\n"
        "    select:\n        id\n        w = v\n",
        [
            _position("a row let", 13, 13),
            ("PIE-S2102", "Unknown field: v", 16, 13),
        ],
    ),
    "join_on": (
        "query q:\n" + T + "    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == scalar t.rid\n    select:\n        id = lhs.id\n",
        [_position("JOIN ON", 14, 22)],
    ),
    "order_by": (
        "query q:\n" + T + "    from lhs\n    select:\n        id\n    order by:\n"
        "        scalar t.rid asc\n",
        [_position("ORDER BY", 15, 9)],
    ),
    "limit": (
        "query q:\n" + T + "    from lhs\n    select:\n        id\n"
        "    limit scalar t.rid\n",
        [
            _position("LIMIT", 14, 11),
            (
                "PIE-S2307",
                "Limit must be a static integer from 0 to 9223372036854775807",
                14,
                11,
            ),
        ],
    ),
    "grouped_select": (
        "query q:\n" + T + "    from lhs\n    group by:\n        id\n    select:\n"
        "        id\n        s = scalar t.rid\n",
        [
            _position("the SELECT of a grouped query", 16, 13),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "aggregate_select": (
        "query q:\n" + T + "    from lhs\n    select:\n        n = count()\n"
        "        s = scalar t.rid\n",
        [
            _position("the SELECT of a grouped query", 14, 13),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "satisfying": (
        "query q:\n" + T + "    from lhs\n    group by:\n        id\n    select:\n"
        "        id\n        n = count()\n    satisfying:\n        n > scalar t.rid\n",
        [
            _position("SATISFYING", 18, 13),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "window": (
        "query q:\n" + T + "    from lhs\n    select:\n        id\n"
        "        rn = row_number() window:\n            order by:\n"
        "                scalar t.rid\n",
        [
            _position("a window", 16, 17),
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
                14,
                14,
            ),
        ],
    ),
    "named_window": (
        "query q:\n" + T + "    from lhs\n    select:\n        id\n"
        "        rn = row_number() window ordered\n    window ordered:\n"
        "        order by:\n            scalar t.rid\n",
        [
            _position("a window", 17, 13),
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
                14,
                14,
            ),
        ],
    ),
    "qualify": (
        "query q:\n" + T + "    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id\n    select:\n        id = lhs.id\n"
        "        rn = row_number() window:\n            order by:\n"
        "                lhs.id\n    qualify:\n        rn == scalar t.rid\n",
        [_position("QUALIFY", 21, 15)],
    ),
    "unknown_column": (
        "query q:\n" + T + "    from lhs\n    where id == scalar t.nope\n"
        "    select:\n        id\n",
        [("PIE-S2102", "Unknown field: t.nope", 12, 17)],
    ),
    "unknown_relation": (
        "query q:\n    from lhs\n    where id == scalar nowhere.id\n"
        "    select:\n        id\n",
        [("PIE-S2301", "Unknown relation: nowhere", 8, 17)],
    ),
    "not_bool": (
        "query q:\n" + T + "    from lhs\n    where scalar t.rid\n    select:\n"
        "        id\n",
        [("PIE-S2202", "Expected Bool expression in where clause", 12, 11)],
    ),
    "operands": (
        "query q:\n    from lhs\n    where id + scalar rhs.id > 'x'\n"
        "    select:\n        id\n",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator >: expected comparable operands",
                8,
                11,
            )
        ],
    ),
    "set_block": (
        "query both:\n    union all:\n        from lhs\n        from rhs\n"
        "query q:\n    from lhs\n    where id == scalar both.id\n    select:\n"
        "        id\n",
        [
            (
                "PIE-S2348",
                f"Scalar relation read both.id is not yet available: the columns of both {LATER}",
                12,
                17,
            )
        ],
    ),
    "join_block": (
        "query pairs:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id\n    select:\n        a = lhs.id\n"
        "query q:\n    from lhs\n    select:\n        id\n        b = scalar pairs.a\n",
        [
            (
                "PIE-S2348",
                f"Scalar relation read pairs.a is not yet available: the columns of pairs {LATER}",
                17,
                13,
            )
        ],
    ),
    "erroneous_block": (
        "query t:\n    from rhs\n    select:\n        rid = id\n"
        "        bad = id > 'x'\nquery q:\n    from lhs\n"
        "    where id == scalar t.rid\n    select:\n        id\n",
        [
            (
                "PIE-S2105",
                "Invalid operands for operator >: expected comparable operands",
                10,
                15,
            ),
            (
                "PIE-S2348",
                f"Scalar relation read t.rid is not yet available: the columns of t {LATER}",
                13,
                17,
            ),
        ],
    ),
    # A relation over a set has no columns before completion either, whether
    # it is a module relation or a let, and whatever column the read names.
    "over_set_block": (
        SET + OVER + "query q:\n    from lhs\n    where id == scalar over.nope\n"
        "    select:\n        id\n",
        [_later("over.nope", 16, 17)],
    ),
    "let_over_set_block": (
        "query q:\n    let s:\n        union all:\n            from lhs\n"
        "            from rhs\n    let o:\n        from s\n        select:\n"
        "            id\n    from lhs\n    where id == scalar o.id\n"
        "    select:\n        id\n",
        [_later("o.id", 16, 17)],
    ),
    # A relation over a table function has no columns before completion.
    "let_over_table_function": (
        "query q:\n    let s:\n        from generate_series(1, 3, 1) as n\n"
        "        select:\n            n\n    from lhs\n    where id == scalar s.n\n"
        "    select:\n        id\n",
        [_later("s.n", 12, 17)],
    ),
    "unresolved_block": (
        "query t:\n    from nowhere\n    select:\n        rid = id\n"
        "query q:\n    from lhs\n    where id == scalar t.rid\n    select:\n"
        "        id\n",
        [
            ("PIE-S2301", "Unknown relation: nowhere", 7, 5),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: t",
                6,
                1,
            ),
            _later("t.rid", 12, 17),
        ],
    ),
    # An error that leaves the read relation's columns known is its own only.
    "block_where_error": (
        "query t:\n    from rhs\n    where nope > 1\n    select:\n        rid = id\n"
        "query q:\n    from lhs\n    where id == scalar t.rid\n    select:\n"
        "        id\n",
        [("PIE-S2102", "Unknown field: nope", 8, 11)],
    ),
    # A JOIN reader and a reader of a set report their reads like any reader.
    "join_unknown_column": (
        "query q:\n" + JOIN + "    where lhs.id == scalar rhs.nope\n"
        "    select:\n        a = lhs.id\n",
        [("PIE-S2102", "Unknown field: rhs.nope", 11, 21)],
    ),
    "join_select_unknown_column": (
        "query q:\n" + JOIN + "    select:\n        a = lhs.id\n"
        "        b = scalar rhs.nope\n",
        [("PIE-S2102", "Unknown field: rhs.nope", 13, 13)],
    ),
    "join_set_block": (
        SET + "query q:\n" + JOIN + "    where lhs.id == scalar both.id\n"
        "    select:\n        a = lhs.id\n",
        [_later("both.id", 15, 21)],
    ),
    "join_join_block": (
        "query pairs:\n" + JOIN + "    select:\n        a = lhs.id\n"
        "query q:\n" + JOIN + "    where lhs.id == scalar pairs.a\n"
        "    select:\n        a = lhs.id\n",
        [_later("pairs.a", 18, 21)],
    ),
    "set_reader_unknown_column": (
        SET + "query q:\n    from both\n    where id == scalar rhs.nope\n"
        "    select:\n        id\n",
        [("PIE-S2102", "Unknown field: rhs.nope", 12, 17)],
    ),
    # A read that closes a cycle through lets is reported at the read.
    "self_read": (
        "query q:\n    let t:\n        from rhs\n        where id == scalar t.rid\n"
        "        select:\n            rid = id\n    from t\n    select:\n"
        "        rid\n",
        [("PIE-S2302", "Relation cycle detected: t -> t", 9, 21)],
    ),
    # A relation over a VALUES body, like one over a set, completes its row.
    "over_values": (
        "query seeds:\n    values(rid: Int not null):\n        1\n"
        "query over:\n    from seeds\n    select:\n        rid\n"
        "query q:\n    from lhs\n    where id == scalar over.rid\n    select:\n"
        "        id\n",
        [
            (
                "PIE-S2348",
                "Scalar relation read over.rid is not yet available: the columns "
                "of over " + LATER,
                15,
                17,
            )
        ],
    ),
    "values_unknown_column": (
        "query q:\n    let v:\n        values(rid: Int not null):\n            1\n"
        "    from lhs\n    where id == scalar v.nope\n    select:\n        id\n",
        [("PIE-S2102", "Unknown field: v.nope", 11, 17)],
    ),
}


@pytest.mark.parametrize("case", sorted(ACCEPTED))
def test_scalar_reads_in_where_and_ungrouped_select_check(
    tmp_path: Path, case: str
) -> None:
    assert _check(tmp_path, ACCEPTED[case]) == (0, [])


@pytest.mark.parametrize("case", sorted(REFUSED))
def test_every_refused_scalar_read_reports_its_ordered_diagnostics(
    tmp_path: Path, case: str
) -> None:
    body, expected = REFUSED[case]
    assert _check(tmp_path, body) == (1, expected)


def test_legacy_flat_projects_keep_the_scalar_read_gate(tmp_path: Path) -> None:
    gate = (
        "PIE-S2348",
        "Scalar relation reads are available only inside a FROM-based "
        "relation body in EXPLICIT_MODULES projects (schema version 2).",
    )
    assert _check(tmp_path, ACCEPTED["where_and_select"], schema=1) == (
        1,
        [
            (
                "PIE-S2345",
                "Relation let declarations are available only in "
                "EXPLICIT_MODULES projects (schema version 2).",
                7,
                5,
            ),
            (*gate, 12, 17),
            (*gate, 15, 13),
        ],
    )
