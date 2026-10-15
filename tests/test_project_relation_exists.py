"""Where an EXISTS read may be written in an EXPLICIT_MODULES project.

A read is available only in WHERE and in the SELECT of an ungrouped query
(D70.04). Every other place is PIE-S2349 at the read, from relation name
resolution, and the read never becomes an expression block use. Later
diagnostics of the same clause keep their own codes and order.
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
WINDOW = "        n = row_number() window:\n            order by:\n"
COMPLETION = (
    "PIE-S2333",
    "Project relation semantic completion is unavailable: q",
    6,
    1,
)
# body, (line, column) of the read, refused place, the clause's own diagnostics
REFUSED = {
    "join_on": (
        "query q:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id and exists rhs\n    select:\n        id = lhs.id\n",
        (10, 31),
        "JOIN ON",
        [],
    ),
    "row_let": (
        "query q:\n    from lhs\n    let:\n        f = exists rhs\n"
        "    select:\n        id\n        f\n",
        (9, 13),
        "a row let",
        [],
    ),
    "grouped_select": (
        "query q:\n    from lhs\n    group by:\n        id\n"
        "    select:\n        id\n        e = exists rhs\n",
        (12, 13),
        "the SELECT of a grouped query",
        [COMPLETION],
    ),
    "aggregate_select": (
        "query q:\n    from lhs\n    select:\n        n = count()\n        e = exists rhs\n",
        (10, 13),
        "the SELECT of a grouped query",
        [COMPLETION],
    ),
    "satisfying": (
        "query q:\n    from lhs\n    group by:\n        id\n    select:\n        id\n"
        "        n = count()\n    satisfying:\n        n > 0 and exists rhs\n",
        (14, 19),
        "SATISFYING",
        [COMPLETION],
    ),
    "window_order": (
        "query q:\n    from lhs\n    select:\n        id\n"
        + WINDOW
        + "                exists rhs\n",
        (12, 17),
        "a window",
        [("PIE-S2103", "Unknown function: row_number", 10, 13)],
    ),
    "window_argument": (
        "query q:\n    from lhs\n    select:\n        id\n"
        "        n = first_value(exists rhs) window:\n            order by:\n"
        "                id\n",
        (10, 25),
        "a window",
        [
            (
                "PIE-S2104",
                "Invalid arguments for function first_value: value must be a direct"
                " field or Bool, Text, Int, Float, or NULL literal",
                10,
                13,
            )
        ],
    ),
    "named_window": (
        "query q:\n    from lhs\n    select:\n        id\n"
        "        n = row_number() window w\n    window w:\n        order by:\n"
        "            exists rhs\n",
        (13, 13),
        "a window",
        [("PIE-S2103", "Unknown function: row_number", 10, 13)],
    ),
    "qualify": (
        "query q:\n    from lhs\n    select:\n        id\n    qualify:\n"
        "        row_number() window:\n            order by:\n                id\n"
        "        <= 3 and exists rhs\n",
        (14, 18),
        "QUALIFY",
        [],
    ),
    "order_by": (
        "query q:\n    from lhs\n    select:\n        id\n    order by:\n"
        "        exists rhs\n",
        (11, 9),
        "ORDER BY",
        [],
    ),
    "limit": (
        "query q:\n    from lhs\n    select:\n        id\n    limit exists rhs\n",
        (10, 11),
        "LIMIT",
        [
            (
                "PIE-S2307",
                "Limit must be a static integer from 0 to 9223372036854775807",
                10,
                11,
            )
        ],
    ),
    "let_body_order_by": (
        "query q:\n    let picked:\n        from rhs\n        select:\n"
        "            id\n        order by:\n            exists lhs\n"
        "    from picked\n    select:\n        id\n",
        (12, 13),
        "ORDER BY",
        [],
    ),
}
ADMITTED = {
    "grouped_where": "query q:\n    from lhs\n    where exists rhs\n    group by:\n"
    "        id\n    select:\n        id\n        n = count()\n",
    "nested_values": "query q:\n    from lhs\n"
    "    where id > 0 and (exists rhs or not exists rhs)\n    select:\n        id\n"
    "        a = 1 if exists rhs else 0\n        b = coalesce(exists rhs, false)\n"
    "        c = (exists rhs) is null\n",
    "joined_where": "query q:\n    from lhs\n    left join rhs as r:\n        from lhs\n"
    "        on lhs.id == r.id\n    where exists rhs and r.id is null\n"
    "    select:\n        id = lhs.id\n        e = not exists rhs\n",
    "let_body": "query q:\n    let picked:\n        from rhs\n        where exists lhs\n"
    "        select:\n            id\n            e = exists lhs\n    from lhs\n"
    "    where exists picked\n    select:\n        id\n",
    "parameterized_where": "query q(cut: Int not null):\n    from lhs\n"
    "    where id > cut and exists rhs\n    select:\n        id\n",
}


def _check(tmp_path: Path, body: str, config: str = probe.CONFIG):
    (tmp_path / "pietto.toml").write_text(config)
    (tmp_path / "main.pietto").write_text(HEAD + body)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    return code, json.loads(out.getvalue())["diagnostics"]


@pytest.mark.parametrize("case", sorted(REFUSED))
def test_a_read_outside_where_and_an_ungrouped_select_is_refused_at_the_read(
    tmp_path: Path, case: str
) -> None:
    body, (line, column), where, others = REFUSED[case]
    code, diagnostics = _check(tmp_path, body)
    assert code == 1
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in diagnostics
    ] == [
        (
            "PIE-S2349",
            "EXISTS relation reference is available only in WHERE and in the SELECT "
            f"of an ungrouped query, not in {where}.",
            line,
            column,
        ),
        *others,
    ]


@pytest.mark.parametrize("case", sorted(ADMITTED))
def test_where_and_ungrouped_select_reads_are_available(
    tmp_path: Path, case: str
) -> None:
    assert _check(tmp_path, ADMITTED[case]) == (0, [])


def test_a_legacy_flat_project_keeps_the_pre_admission_diagnostic(
    tmp_path: Path,
) -> None:
    code, diagnostics = _check(
        tmp_path,
        ADMITTED["grouped_where"],
        probe.CONFIG.replace("schema_version = 2", "schema_version = 1"),
    )
    assert code == 1
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in diagnostics
    ] == [
        (
            "PIE-S2349",
            "EXISTS relation reference semantics are not implemented.",
            8,
            11,
        )
    ]


PARAMETERIZED = (
    "query p(cut: Int not null):\n    from rhs\n    where id > cut\n"
    "    select:\n        id\n"
)


@pytest.mark.parametrize(
    ("reader", "line", "column"),
    [
        (
            "query q:\n    from lhs\n    where exists p\n    select:\n        id\n",
            13,
            11,
        ),
        (
            "query q:\n    let l:\n        from lhs\n        where exists p\n"
            "        select:\n            id\n    from l\n    select:\n        id\n",
            14,
            15,
        ),
    ],
    ids=["body", "let"],
)
def test_an_existence_read_of_a_parameterized_query_is_refused_at_the_read(
    tmp_path: Path, reader: str, line: int, column: int
) -> None:
    """A query with parameters is only an entry query, never a read block."""
    code, diagnostics = _check(tmp_path, PARAMETERIZED + reader)
    assert code == 1
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in diagnostics
    ] == [
        (
            "PIE-S2356",
            "A query with parameters cannot be the input of another relation.",
            line,
            column,
        )
    ]
