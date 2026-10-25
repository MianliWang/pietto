"""Entry-query header parameters: admission per project mode and their diagnostics."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from pietto import cli
from pietto._project.check import check_project_parse_only

HEADER = """shape Row:
    id: Int
    plain: Int
    label: Text
source rows: Row = postgres.table("rows")
"""
FIRST = HEADER.count("\n") + 1
POSITION = "PIE-S2355"
POSITION_MESSAGE = "Query parameters are not available in this position."
COLLISION = "PIE-S2354"
DECLARATION = "PIE-S2353"
INPUT = "PIE-S2356"
INPUT_MESSAGE = "A query with parameters cannot be the input of another relation."
COUNT = "PIE-S2358"


def _project(root: Path, body: str, *, schema: int = 2) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n'
    )
    (root / "main.pietto").write_text(HEADER + body, encoding="utf-8")
    return root


def _check(root: Path, *, messages: bool = False) -> tuple[int, list[tuple]]:
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(["check", "--project", str(root), "--format", "json"])
    document = json.loads(out.getvalue())
    return code, [
        (
            item["code"],
            *((item["message"],) if messages else ()),
            item["location"]["line"] - FIRST + 1,
            item["location"]["column"],
        )
        for item in document["diagnostics"]
    ]


VALID = (
    "query q(cutoff: Int, label2: Text | None):\n"
    "    from rows\n"
    "    let next = cutoff + 1\n"
    "    where id > cutoff and label == label2\n"
    "    select:\n"
    "        id\n"
    "        bumped = next\n"
)


def test_only_an_explicit_module_project_admits_a_header(tmp_path: Path) -> None:
    assert _check(_project(tmp_path / "explicit", VALID)) == (0, [])
    assert _check(_project(tmp_path / "flat", VALID, schema=1)) == (
        1,
        [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 22)],
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "    let recent:\n        from rows\n        where id > cutoff\n"
            "        select:\n            id\n    union all:\n        from recent\n"
            "        from rows\n",
            [("PIE-S2346", 1)],
        ),
        ("    union all:\n        from rows\n        from rows\n", [("PIE-S2346", 1)]),
        (
            "    values(id: Int):\n        1\n",
            [("PIE-S2346", 1)],
        ),
        (
            "    from generate_series(1, 31, 1) as n\n    select:\n        n\n",
            [("PIE-S2346", 1)],
        ),
    ),
    ids=("let_set_operation", "set_operation", "values", "table_function"),
)
def test_a_header_without_a_relation_from_body_stays_unadmitted(
    tmp_path: Path, body: str, expected: list[tuple[str, int]]
) -> None:
    source = "query q(cutoff: Int):\n" + body
    parsed = check_project_parse_only(_project(tmp_path, source))
    assert [
        (d.code, d.location.line - FIRST + 1) for d in parsed.diagnostics
    ] == expected


SERIES_LET_READS = (
    "        where n > cutoff\n"
    "        select:\n"
    "            n\n"
    "            cutoff\n"
    "        limit cutoff\n"
)


@pytest.mark.parametrize(
    "series",
    (SERIES_LET_READS, "        select:\n            n\n"),
    ids=("reads_the_header", "reads_no_parameter"),
)
def test_a_let_reading_a_table_function_keeps_the_header_unadmitted(
    tmp_path: Path, series: str
) -> None:
    """Like a table-function body of its own, a let that reads one keeps every
    parameter PIE-S2346, whether or not the let reads it, and no other
    parameter diagnostic is reported beside it."""
    body = (
        "query q(cutoff: Int, label2: Text | None):\n"
        "    let s:\n        from generate_series(1, 5, 1) as n\n"
        + series
        + "    let a:\n        from rows\n        where label == label2\n"
        "        select:\n            id\n"
        "    from a\n    where id in s\n    select:\n        id\n"
    )
    unadmitted = (
        "Query header parameters are available only in EXPLICIT_MODULES "
        "projects (schema version 2), on a query that reads a relation "
        "with FROM and has no relation let reading a table function."
    )
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [("PIE-S2346", unadmitted, 1, 9), ("PIE-S2346", unadmitted, 1, 22)],
    )


@pytest.mark.parametrize(
    ("declaration", "expected"),
    (
        ("a: Int", []),
        ("a: Decimal(3, 1)", [(DECLARATION, 1, 9)]),
        ("a: UUID | None", [(DECLARATION, 1, 9)]),
        ("a: Int, a: Bool | None", [("PIE-S2001", 1, 17)]),
    ),
    ids=("bare_type_is_not_null", "type_arguments", "other_builtin", "duplicate"),
)
def test_header_declarations_are_checked_before_semantics(
    tmp_path: Path, declaration: str, expected: list[tuple[str, int, int]]
) -> None:
    body = f"query q({declaration}):\n    from rows\n    select:\n        id\n"
    assert _check(_project(tmp_path, body)) == (int(bool(expected)), expected)


def test_at_most_sixty_four_parameters(tmp_path: Path) -> None:
    allowed = ", ".join(f"p{i}: Int" for i in range(64))
    body = f"query q({allowed}, extra: Int):\n    from rows\n"
    body += "    select:\n        id\n"
    column = len("query q(") + len(allowed) + len(", ") + 1
    assert _check(_project(tmp_path, body)) == (1, [(DECLARATION, 1, column)])
    exact = f"query q({allowed}):\n    from rows\n    select:\n        id\n"
    assert _check(_project(tmp_path / "exact", exact)) == (0, [])
    # Each fault of one parameter is its own diagnostic at that parameter,
    # sorted by code: a repeated name, the limit and the type.
    extra = "p0: UUID, t: Decimal(3, 1) | None"
    stacked = f"query q({allowed}, {extra}):\n    from rows\n    select:\n        id\n"
    second = column + len("p0: UUID, ")
    limit = "A query declares at most 64 parameters."
    kind = "Query parameter type must be Bool, Int, Float or Text."
    assert _check(_project(tmp_path / "stacked", stacked), messages=True) == (
        1,
        [
            ("PIE-S2001", "Duplicate parameter name in query q: p0", 1, column),
            (DECLARATION, limit, 1, column),
            (DECLARATION, kind, 1, column),
            (DECLARATION, limit, 1, second),
            (DECLARATION, kind, 1, second),
        ],
    )


HEADER_QUERY = "query q(cutoff: Int, word: Text | None):\n    from rows\n"
ADMITTED = {
    "satisfying": (
        "    group by:\n        id\n    select:\n        id\n        n = count()\n"
        "    having:\n        n > cutoff\n"
    ),
    "qualify": (
        "    select:\n        id\n        r = row_number() window(order by id)\n    qualify:\n        r <= cutoff + 1\n"
    ),
    "order_key_through_let": (
        "    let s = id * cutoff\n    select:\n        id\n    order by:\n        s desc\n    limit 2\n"
    ),
    "order_key_matching_output": (
        "    select:\n        id\n        k = id + cutoff\n"
        "    order by:\n        id + cutoff\n"
    ),
    "let_aggregates": (
        "    let s = id + cutoff\n"
        "    group by:\n"
        "        plain\n"
        "    select:\n"
        "        plain\n"
        "        n = count(s)\n"
        "        a = avg(s)\n"
        "        m = max(s)\n"
        "        lo = min(s)\n"
        "    order by:\n"
        "        n\n"
    ),
    "computed_group_key": (
        "    let k = id * cutoff\n    group by:\n        k\n    select:\n        k\n        n = count()\n    having:\n        n > cutoff\n"
    ),
    "joined_satisfying": (
        "    let r = rows\n"
        "    inner join r on rows.id == r.id\n"
        "    group by:\n"
        "        rows.id\n"
        "    select:\n"
        "        k = rows.id\n"
        "        n = count()\n"
        "    having:\n"
        "        n > cutoff\n"
    ),
    "builtin_value_arguments": (
        "    where contains(label, word) and starts_with(word, label)\n"
        "    select:\n        id\n        a = lower(word)\n"
        "        b = coalesce(word, label)\n        c = nullif(cutoff, id)\n"
        "        d = sign(cutoff - id)\n        e = trim(word)\n"
    ),
}


@pytest.mark.parametrize("clauses", ADMITTED.values(), ids=tuple(ADMITTED))
def test_result_and_post_aggregate_positions_are_admitted(
    tmp_path: Path, clauses: str
) -> None:
    body = HEADER_QUERY + clauses
    assert _check(_project(tmp_path, body)) == (0, [])


GROUPED = "    group by:\n        plain\n    select:\n        plain\n"
REFUSED = {
    "limit": ("    select:\n        id\n    limit cutoff\n", [(POSITION, 5, 11)]),
    "call_argument": (
        "    where id > abs(cutoff)\n    select:\n        id\n",
        [(POSITION, 3, 20)],
    ),
    "fixed_value_argument": (
        "    select:\n        id\n        s = substr(label, 1, cutoff)\n",
        [(POSITION, 5, 30)],
    ),
    "length_argument": (
        "    where len(word) > 1\n    select:\n        id\n",
        [(POSITION, 3, 15)],
    ),
    "needle_rendered_twice": (
        "    where starts_with(label, word)\n    select:\n        id\n",
        [(POSITION, 3, 30)],
    ),
    "suffix_rendered_twice": (
        "    where ends_with(label, word)\n    select:\n        id\n",
        [(POSITION, 3, 28)],
    ),
    "replace_argument": (
        "    select:\n        id\n        r = replace(label, word, label)\n",
        [(POSITION, 5, 28)],
    ),
    "matches_argument": (
        "    where matches(label, word)\n    select:\n        id\n",
        [(POSITION, 3, 26)],
    ),
    "group_key": (
        "    group by:\n        cutoff\n    select:\n        n = count()\n",
        [(POSITION, 4, 9)],
    ),
    "group_key_let_alias": (
        "    let j = id + cutoff\n    let k = j\n    group by:\n        k\n    select:\n        k\n        n = count()\n",
        [(POSITION, 6, 9), (POSITION, 8, 9)],
    ),
    "group_key_with_join": (
        (
            "    let r = rows\n"
            "    inner join r on rows.id == r.id\n"
            "    let g = rows.id * cutoff\n"
            "    group by:\n"
            "        g\n"
            "    select:\n"
            "        g\n"
            "        n = count()\n"
        ),
        [(POSITION, 7, 9), (POSITION, 9, 9)],
    ),
    "grouped_select": (
        "    group by:\n        id\n    select:\n        id\n"
        "        n = count()\n        c = cutoff\n",
        [(POSITION, 8, 13)],
    ),
    "sum_of_dependent_let": (
        "    let s = id + cutoff\n" + GROUPED + "        t = sum(s)\n",
        [(POSITION, 8, 17)],
    ),
    "count_distinct_of_dependent_let": (
        "    let s = id + cutoff\n" + GROUPED + "        t = count_distinct(s)\n",
        [(POSITION, 8, 28)],
    ),
    "arithmetic_over_let_aggregate": (
        "    let s = id + cutoff\n" + GROUPED + "        n = count(s) + 1\n",
        [(POSITION, 8, 19)],
    ),
    "aggregate_of_parameter": (
        GROUPED + "        n = count(cutoff)\n",
        [(POSITION, 7, 19)],
    ),
    "aggregate_of_expression": (
        GROUPED + "        n = count(id + cutoff)\n",
        [(POSITION, 7, 24)],
    ),
    "grouped_order_key": (
        GROUPED + "        n = count()\n    order by:\n        cutoff\n",
        [(POSITION, 9, 9)],
    ),
    "constant_order_key": (
        "    select:\n        id\n    order by:\n        cutoff\n",
        [(POSITION, 6, 9)],
    ),
    "window_argument_operand": (
        "    select:\n        id\n        w = lag(id, cutoff + 1) window(order by id)\n",
        [(POSITION, 5, 21)],
    ),
    "window_partition": (
        "    select:\n        id\n        r = row_number() window(partition by cutoff order by id)\n",
        [(POSITION, 5, 46)],
    ),
    "grouped_window": (
        "    group by:\n        id\n    select:\n        id\n        w = lag(id, cutoff) window(order by id)\n",
        [(POSITION, 7, 21)],
    ),
    "window_order": (
        "    let s = cutoff * 2\n    select:\n        id\n        r = row_number() window(order by s)\n",
        [(POSITION, 6, 42)],
    ),
    "aggregate_without_group_by": (
        "    select:\n        n = count()\n        v = cutoff\n",
        [(POSITION, 5, 13)],
    ),
    "named_window": (
        "    let w = window(order by cutoff)\n    select:\n        id\n        r = row_number() window w\n",
        [(POSITION, 3, 29)],
    ),
    "frame_offset": (
        "    select:\n        id\n        f = first_value(id) window(order by id rows between cutoff preceding and current row)\n",
        [(POSITION, 5, 61)],
    ),
    "named_window_frame_offset": (
        (
            "    let w = window(order by id range between current row and cutoff following)\n    select:\n        id\n        f = first_value(id) window w\n"
        ),
        [(POSITION, 3, 62)],
    ),
    "frame_offset_through_let": (
        "    let k = cutoff\n    select:\n        id\n        f = first_value(id) window(order by id groups between k preceding and current row)\n",
        [(POSITION, 6, 63)],
    ),
    "named_window_through_let": (
        "    let s = id + cutoff\n    let ordered = window(order by s)\n    select:\n        id\n        r = row_number() window ordered\n",
        [(POSITION, 4, 35)],
    ),
    # A comparison chain reads its inner operand once per comparison; each
    # refused read there is reported once.
    "chain_order_key": (
        "    select:\n        id\n    order by 0 < cutoff < 3\n",
        [(POSITION, 5, 18)],
    ),
    "chain_order_key_block": (
        "    select:\n        id\n    order by:\n        0 < cutoff < 3\n",
        [(POSITION, 6, 13)],
    ),
}


@pytest.mark.parametrize(("clauses", "expected"), REFUSED.values(), ids=tuple(REFUSED))
def test_positions_outside_the_available_roles_are_refused(
    tmp_path: Path, clauses: str, expected: list[tuple[str, int, int]]
) -> None:
    body = HEADER_QUERY + clauses
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(code, POSITION_MESSAGE, line, column) for code, line, column in expected],
    )


def test_a_refused_read_in_a_def_argument_used_twice_is_reported_once(
    tmp_path: Path,
) -> None:
    """The expansion writes the argument once per use of its parameter; the
    refused read written there is one PIE-S2355."""
    body = (
        HEADER_QUERY
        + "    select:\n        id\n        x = dbl(len(substr(label, cutoff, 1)))\n"
        + "def dbl(v: Int) -> Int | None: return v + v\n"
    )
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(POSITION, POSITION_MESSAGE, 5, 35)],
    )


@pytest.mark.parametrize(
    ("header", "clauses", "expected"),
    (
        ("id: Int", "    select:\n        a = plain\n", [(COLLISION, 1, 9)]),
        ("rows: Int", "    select:\n        id\n", [(COLLISION, 1, 9)]),
        (
            "s: Int",
            "    let s = 1\n    select:\n        id\n",
            [(COLLISION, 1, 9)],
        ),
        ("a: Int", "    select:\n        a = plain\n", [(COLLISION, 1, 9)]),
        (
            "w: Int",
            "    let w = window(order by id)\n    select:\n        id\n",
            [(COLLISION, 1, 9)],
        ),
        (
            "c: Int",
            "    select:\n        id\n        c\n",
            [(COLLISION, 5, 9)],
        ),
    ),
    ids=("field", "relation", "let", "output", "named_window", "unaliased_read"),
)
def test_a_header_name_never_shadows_another_name(
    tmp_path: Path, header: str, clauses: str, expected: list[tuple[str, int, int]]
) -> None:
    body = f"query q({header}):\n    from rows\n" + clauses
    assert _check(_project(tmp_path, body)) == (1, expected)


def test_an_output_taints_only_the_clauses_that_read_outputs(tmp_path: Path) -> None:
    # Outside ORDER BY, QUALIFY, SATISFYING and LIMIT `label` reads the input
    # field that the output alias shadows.
    body = (
        "query q(p: Text):\n"
        "    from rows\n"
        "    let n = lower(label)\n"
        '    where lower(label) == "x"\n'
        "    select:\n"
        "        label = p\n"
        "        m = lower(label)\n"
    )
    assert _check(_project(tmp_path / "rows", body)) == (0, [])
    # ORDER BY resolves the output: a key named alone that is both the input
    # field and an output of another value is ambiguous (no winner), the
    # qualified key reads the input field, and a structural call argument or
    # LIMIT that reads the output is refused.
    ordered = body + "    order by:\n        label\n"
    assert _check(_project(tmp_path / "order", ordered), messages=True) == (
        1,
        [
            (
                "PIE-S2102",
                "Ambiguous field: label is both the input field rows.label and a "
                "SELECT output; write rows.label, or give the output another name",
                9,
                9,
            )
        ],
    )
    qualified = body + "    order by:\n        rows.label\n"
    assert _check(_project(tmp_path / "qualified", qualified)) == (0, [])
    structural = body + "    order by:\n        substr(label, 1, 2)\n"
    assert _check(_project(tmp_path / "substr", structural)) == (
        1,
        [(POSITION, 9, 16)],
    )
    limited = body + "    limit label\n"
    assert _check(_project(tmp_path / "limit", limited)) == (1, [(POSITION, 8, 11)])
    # A named window key reads the shadowed input field too; a name with no
    # input field is unknown there, as in an inline window.
    for clause in ("partition by", "order by"):
        for name, expected in (
            ("label", []),
            ("k", [("PIE-S2102", 4, 21 + len(clause))]),
        ):
            ordered_by_id = " order by id"
            windowed = (
                body.replace("label = p", f"{name} = p").replace(
                    "    where ",
                    f"    let w = window({clause} {name}"
                    + ordered_by_id * (clause == "partition by")
                    + ")\n    where ",
                )
                + "        r = row_number() window w\n"
            )
            root = tmp_path / f"{clause.split()[0]}-{name}"
            assert _check(_project(root, windowed)) == (int(bool(expected)), expected)


def test_a_join_binding_and_its_fields_are_collisions(tmp_path: Path) -> None:
    body = (
        "query q(r: Int, plain: Int):\n"
        "    from rows\n"
        "    let r = rows\n"
        "    inner join r on rows.id == r.id\n"
        "    select:\n"
        "        a = rows.id\n"
    )
    assert _check(_project(tmp_path, body)) == (
        1,
        [(COLLISION, 1, 9), (COLLISION, 1, 17)],
    )


def test_a_parameterized_query_is_never_a_relation_input(tmp_path: Path) -> None:
    body = (
        "query q(cutoff: Int):\n"
        "    from rows\n"
        "    where id > cutoff\n"
        "    select:\n"
        "        id\n"
        "table t:\n"
        "    from q\n"
        "    select:\n"
        "        id\n"
        "table u:\n"
        "    from rows\n"
        "    let k = q\n"
        "    inner join k on rows.id == k.id\n"
        "    select:\n"
        "        a = rows.id\n"
        "table v:\n"
        "    union all:\n"
        "        from t\n"
        "        from q\n"
    )
    code, diagnostics = _check(_project(tmp_path, body))
    assert code == 1
    assert [item for item in diagnostics if item[0] == INPUT] == [
        (INPUT, 7, 5),
        (INPUT, 13, 5),
        (INPUT, 19, 9),
    ]


PARAMETERIZED = (
    "query p(c: Int):\n    from rows\n    where id > c\n    select:\n        id\n"
)


@pytest.mark.parametrize(
    ("read", "column"),
    (("where False == exists p == True", 20), ("where 0 < scalar p.id < 3", 15)),
    ids=("exists", "scalar"),
)
def test_a_parameterized_query_read_in_a_chain_operand_is_refused_once(
    tmp_path: Path, read: str, column: int
) -> None:
    """A chain reads its inner operand once per comparison; the read of a
    parameterized query written there is one PIE-S2356."""
    body = (
        PARAMETERIZED
        + f"table t:\n    from rows\n    {read}\n    select:\n        id\n"
    )
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(INPUT, INPUT_MESSAGE, 8, column)],
    )


def test_a_relation_let_or_block_body_never_reads_a_parameterized_query(
    tmp_path: Path,
) -> None:
    body = PARAMETERIZED + (
        "query let_from:\n"
        "    let a:\n"
        "        from p\n"
        "        select:\n"
        "            id\n"
        "    from a\n"
        "    select:\n"
        "        id\n"
        "query let_join:\n"
        "    let a:\n"
        "        from rows\n"
        "        let k = p\n"
        "        inner join k on rows.id == k.id\n"
        "        select:\n"
        "            id = rows.id\n"
        "    from a\n"
        "    select:\n"
        "        id\n"
        "query body_from:\n"
        "    let a:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "    from p\n"
        "    let b = a\n"
        "    inner join b on p.id == b.id\n"
        "    select:\n"
        "        id = p.id\n"
        "table set_operand:\n"
        "    let a:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "    union all:\n"
        "        from a\n"
        "        from p\n"
    )
    assert _check(_project(tmp_path / "inputs", body)) == (
        1,
        [(INPUT, 8, 9), (INPUT, 18, 9), (INPUT, 29, 5), (INPUT, 41, 9)],
    )
    # A let named like the query hides nothing: its reads resolve to no relation.
    hiding = PARAMETERIZED + (
        "query r:\n"
        "    let p:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "    from p\n"
        "    select:\n"
        "        id\n"
    )
    assert _check(_project(tmp_path / "hiding", hiding)) == (1, [("PIE-S2001", 7, 5)])


LET_INPUT = (
    "query r:\n"
    "    let a:\n"
    "        from rows\n"
    "        select:\n"
    "            id\n"
    "            extra = plain\n"
    "    from a\n"
    "    select:\n"
    "        id\n"
    "        extra\n"
)


@pytest.mark.parametrize(
    ("inputs", "relation", "line"),
    (
        (LET_INPUT, "r", 11),
        (
            (
                "query r:\n"
                "    let a:\n"
                "        from rows\n"
                "        select:\n"
                "            id\n"
                "            extra = plain\n"
                "    from rows\n"
                "    let b = a\n"
                "    inner join b on rows.id == b.id\n"
                "    select:\n"
                "        id = rows.id\n"
                "        extra = b.extra\n"
            ),
            "r",
            13,
        ),
        (
            "table g:\n"
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        extra = count()\n",
            "g",
            8,
        ),
        (
            "table j:\n    from rows\n    let o = rows\n    inner join o on rows.id == o.id\n    select:\n        id = rows.id\n        extra = o.plain\n",
            "j",
            8,
        ),
    ),
    ids=("let_block", "let_join", "grouped", "join"),
)
def test_a_header_name_never_shadows_a_completed_input_field(
    tmp_path: Path, inputs: str, relation: str, line: int
) -> None:
    entry = (
        "query q(extra: Int):\n"
        f"    from {relation}\n"
        "    where id > extra\n"
        "    select:\n"
        "        id\n"
    )
    assert _check(_project(tmp_path / "field", inputs + entry)) == (
        1,
        [(COLLISION, line, 9)],
    )
    distinct = entry.replace("extra", "other")
    assert _check(_project(tmp_path / "distinct", inputs + distinct)) == (0, [])


VALUES_QUERY = "query v:\n    values(id: Int, extra: Int | None):\n        1, 2\n"
VALUES_FROM = (
    "query q(extra: Int):\n    from v\n    where id > extra\n    select:\n        id\n"
)


@pytest.mark.parametrize(
    ("inputs", "entry", "line"),
    (
        (VALUES_QUERY, VALUES_FROM, 4),
        (VALUES_QUERY.replace("query v", "table v"), VALUES_FROM, 4),
        (
            VALUES_QUERY,
            (
                "query q(extra: Int):\n"
                "    from rows\n"
                "    let w = v\n"
                "    inner join w on rows.id == w.id\n"
                "    where rows.id > extra\n"
                "    select:\n"
                "        id = rows.id\n"
            ),
            4,
        ),
        (
            "table v:\n"
            "    let seed:\n"
            "        values(id: Int, extra: Int | None):\n"
            "            1, 2\n"
            "    from seed\n"
            "    select:\n"
            "        id\n"
            "        extra\n",
            VALUES_FROM,
            9,
        ),
    ),
    ids=("values_query", "values_table", "values_join", "values_let"),
)
def test_a_header_name_never_shadows_a_values_column(
    tmp_path: Path, inputs: str, entry: str, line: int
) -> None:
    """A typed VALUES input names its columns like any completed input."""
    assert _check(_project(tmp_path / "column", inputs + entry)) == (
        1,
        [(COLLISION, line, 9)],
    )
    distinct = entry.replace("extra", "other")
    assert _check(_project(tmp_path / "distinct", inputs + distinct)) == (0, [])


def test_bare_reads_fill_window_values_defaults_and_counts(tmp_path: Path) -> None:
    body = (
        "query q(step: Int, fill: Int | None, seed: Int):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        a = lag(id, step, fill) window(order by id)\n"
        "        b = ntile(step) window(order by id)\n"
        "        c = nth_value(plain, step) window(order by id rows between unbounded preceding and unbounded following)\n"
        "        d = first_value(seed) window(order by id rows between unbounded preceding and current row)\n"
    )
    assert _check(_project(tmp_path, body)) == (0, [])


def test_a_window_count_parameter_is_int_not_null(tmp_path: Path) -> None:
    body = (
        "query q(n: Int | None, t: Text, r: Float):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        a = lag(id, n) window(order by id)\n"
        "        b = ntile(t) window(order by id)\n"
        "        c = nth_value(id, r) window(order by id rows between unbounded preceding and unbounded following)\n"
    )
    message = "A window count parameter must be declared Int, not Int | None."
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(COUNT, message, 5, 21), (COUNT, message, 6, 19), (COUNT, message, 7, 27)],
    )


def test_other_window_positions_never_read_a_parameter(tmp_path: Path) -> None:
    body = (
        "query q(cutoff: Int):\n"
        "    from rows\n"
        "    let s = cutoff * 2\n"
        "    let base = window(order by id groups between current row and s following)\n"
        "    select:\n"
        "        id\n"
        "        f = first_value(id) window(order by id rows between cutoff preceding and current row)\n"
        "        t = sum(cutoff) window(order by id)\n"
        "        p = row_number() window(partition by cutoff order by s)\n"
        "        n = lag(id, cutoff + 1) window(order by id)\n"
        "        g = first_value(id) window base\n"
    )
    message = "Query parameters are not available in this position."
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [
            (POSITION, message, line, column)
            for line, column in (
                (4, 66),  # named-window frame offset through a let
                (7, 61),  # frame offset
                (8, 17),  # an argument of another window function
                (9, 46),  # PARTITION BY key
                (9, 62),  # ORDER BY key through a let
                (10, 21),  # a read beneath an operator in an argument
            )
        ],
    )


LET_VALID = (
    "query q(cutoff: Int, label2: Text | None):\n"
    "    let recent:\n"
    "        from rows\n"
    "        let next = cutoff + 1\n"
    "        where id > next and label == label2\n"
    "        select:\n"
    "            id\n"
    "            bumped = next\n"
    "    from recent\n"
    "    where id > cutoff\n"
    "    select:\n"
    "        id\n"
    "        bumped\n"
)


def test_relation_lets_of_an_entry_query_read_its_header(tmp_path: Path) -> None:
    """Only EXPLICIT_MODULES admits a header beside relation lets; single-file
    analysis and LEGACY_FLAT keep the S01 refusals."""
    assert _check(_project(tmp_path / "explicit", LET_VALID)) == (0, [])
    assert _check(_project(tmp_path / "flat", LET_VALID, schema=1)) == (
        1,
        [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 22), ("PIE-S2345", 2, 5)],
    )
    single = tmp_path / "single.pietto"
    single.write_text(HEADER + LET_VALID, encoding="utf-8")
    out = io.StringIO()
    with redirect_stdout(out):
        code = cli.main(["check", str(single), "--format", "json"])
    document = json.loads(out.getvalue())
    assert code == 1
    assert [
        (d["code"], d["location"]["line"] - FIRST + 1, d["location"]["column"])
        for d in document["diagnostics"]
    ] == [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 22), ("PIE-S2345", 2, 5)]


@pytest.mark.parametrize(("clauses", "expected"), REFUSED.values(), ids=tuple(REFUSED))
def test_a_relation_let_reads_the_header_under_the_same_position_rules(
    tmp_path: Path, clauses: str, expected: list[tuple[str, int, int]]
) -> None:
    """Every refused position of the entry body is refused inside its let,
    one line lower and one block deeper."""
    body = (
        HEADER_QUERY.splitlines()[0]
        + "\n    let a:\n        from rows\n"
        + "".join("    " + line + "\n" for line in clauses.splitlines())
        + "    from a\n    select:\n        one = 1\n"
    )
    shifted = [(code, line + 1, column + 4) for code, line, column in expected]
    assert _check(_project(tmp_path, body)) == (1, shifted)


@pytest.mark.parametrize(
    ("header", "let", "expected"),
    (
        ("plain: Int", "        select:\n            id\n", [(1, 9)]),
        ("a: Int", "        select:\n            id\n", [(1, 9)]),
        (
            "z: Int",
            "        select:\n            id\n            z = plain\n",
            [(1, 9)],
        ),
        (
            "s: Int",
            "        let s = 1\n        select:\n            id\n",
            [(1, 9)],
        ),
        (
            "k: Int",
            "        let k = rows\n        inner join k on rows.id == k.id\n        select:\n            id = rows.id\n",
            [(1, 9)],
        ),
        (
            "w: Int",
            "        let w = window(order by id)\n        select:\n            id\n",
            [(1, 9)],
        ),
        (
            "c: Int",
            "        select:\n            id\n            c\n",
            [(6, 13)],
        ),
    ),
    ids=(
        "let_field",
        "let_name",
        "let_output",
        "let_row_let",
        "let_join_binding",
        "let_named_window",
        "let_unaliased_read",
    ),
)
def test_a_header_name_never_shadows_a_name_of_a_relation_let(
    tmp_path: Path, header: str, let: str, expected: list[tuple[int, int]]
) -> None:
    body = (
        f"query q({header}):\n    let a:\n        from rows\n"
        + let
        + "    from a\n    select:\n        one = 1\n"
    )
    assert _check(_project(tmp_path, body)) == (
        1,
        [(COLLISION, line, column) for line, column in expected],
    )


def test_a_header_with_relation_lets_declares_at_most_sixty_four(
    tmp_path: Path,
) -> None:
    allowed = ", ".join(f"p{i}: Int" for i in range(64))
    tail = "    let a:\n        from rows\n        where id > p0\n"
    tail += "        select:\n            id\n    from a\n    select:\n        id\n"
    assert _check(_project(tmp_path / "64", f"query q({allowed}):\n" + tail)) == (
        0,
        [],
    )
    body = f"query q({allowed}, extra: Int):\n" + tail
    column = len("query q(") + len(allowed) + len(", ") + 1
    assert _check(_project(tmp_path / "65", body)) == (1, [(DECLARATION, 1, column)])


def test_a_query_whose_lets_read_its_header_is_never_an_input(
    tmp_path: Path,
) -> None:
    body = (
        "query q(cutoff: Int):\n"
        "    let a:\n"
        "        from rows\n"
        "        where id > cutoff\n"
        "        select:\n"
        "            id\n"
        "    from a\n"
        "    select:\n"
        "        id\n"
        "table t:\n"
        "    let b:\n"
        "        from q\n"
        "        select:\n"
        "            id\n"
        "    from b\n"
        "    select:\n"
        "        id\n"
    )
    assert _check(_project(tmp_path, body)) == (1, [(INPUT, 12, 9)])


def test_a_grouped_window_never_reads_a_parameter_or_a_computed_key(
    tmp_path: Path,
) -> None:
    """A computed parameter key admits grouping, but a window over the grouped
    output reads neither the parameter nor the key that depends on it."""
    body = (
        "query q(step: Int):\n"
        "    from rows\n"
        "    let k = id * step\n"
        "    group by:\n"
        "        k\n"
        "    select:\n"
        "        k\n"
        "        n = count()\n"
        "        a = lag(n, step) window(order by k)\n"
    )
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(POSITION, POSITION_MESSAGE, 9, 20), (POSITION, POSITION_MESSAGE, 9, 42)],
    )


def test_gate_diagnostics_precede_header_diagnostics_in_each_file(
    tmp_path: Path,
) -> None:
    """Per file the pre-admission gate reports first, in source order, then the
    header checks in theirs; the two lists are not interleaved by location, and
    semantic analysis (the unknown field of `d`) does not run."""
    lets = "".join(
        f"    let l{i}:\n        from {'rows' if i == 0 else f'l{i - 1}'}\n"
        "        select:\n            id\n"
        for i in range(65)
    )
    body = (
        "query a(cutoff: Int):\n    from rows\n    select:\n        id\n"
        f"query b:\n{lets}    from l64\n    select:\n        id\n"
        "query c(n: Int, n: Bool | None):\n    from rows\n"
        "    select:\n        id\n"
        "query d:\n    from rows\n    select:\n        nothere\n"
    )
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [
            (
                "PIE-S2357",
                "A table or query declares at most 64 relation lets.",
                6 + 4 * 64,
                5,
            ),
            ("PIE-S2001", "Duplicate parameter name in query c: n", 6 + 4 * 65 + 3, 17),
        ],
    )


@pytest.fixture
def _header_admission_trace(monkeypatch: pytest.MonkeyPatch):
    from pietto._project import check as project_check
    from pietto._project import project_relationship_predicates as names

    raw = []
    normalizations = []
    initial_results = []
    make_result = project_check.ProjectParseCheckResult
    parse_input = project_check._parse_selected_input
    normalize = names.normalize_project_query_names

    def observe_result(*args, **kwargs):
        result = make_result(*args, **kwargs)
        initial_results.append(result)
        return result

    def observe_input(*args, **kwargs):
        result = parse_input(*args, **kwargs)
        # These are the returned, project-relative diagnostic objects.
        raw.extend(result[4])
        return result

    def observe_names(parsed):
        normalizations.append(parsed)
        return normalize(parsed)

    monkeypatch.setattr(project_check, "ProjectParseCheckResult", observe_result)
    monkeypatch.setattr(project_check, "_parse_selected_input", observe_input)
    monkeypatch.setattr(names, "normalize_project_query_names", observe_names)
    return raw, normalizations, initial_results


def _header_error_rows(diagnostics):
    return [
        (
            item.code,
            item.message,
            item.location.line - FIRST + 1,
            item.location.column,
        )
        for item in diagnostics
    ]


def test_mixed_parameter_refusals_retain_rebased_direct_diagnostic_identity(
    tmp_path: Path, _header_admission_trace
) -> None:
    body = (
        "query q(p: Int):\n"
        "    from rows\n"
        "    let held = p + 1\n"
        "    select:\n"
        "        n = lag(id, p + 1) window(order by held)\n"
    )
    parsed = check_project_parse_only(_project(tmp_path, body))
    raw, normalizations, initial_results = _header_admission_trace
    assert len(initial_results) == 1
    assert not parsed.ok and len(normalizations) == 1
    assert _header_error_rows(raw) == [(POSITION, POSITION_MESSAGE, 5, 21)]
    assert _header_error_rows(parsed.diagnostics) == [
        (POSITION, POSITION_MESSAGE, 5, 21),
        (POSITION, POSITION_MESSAGE, 5, 44),
    ]
    assert raw[0].location.path == "main.pietto"
    assert parsed.diagnostics[0] is raw[0]
    assert parsed.diagnostics[1] is not raw[0]


@pytest.mark.parametrize(
    ("header", "binding", "projection", "expected"),
    (
        (
            "p: UUID",
            "held = p + 1",
            "n = lag(id, p + 1) window(order by held)",
            [
                (
                    DECLARATION,
                    "Query parameter type must be Bool, Int, Float or Text.",
                    1,
                    9,
                ),
                (POSITION, POSITION_MESSAGE, 5, 21),
            ],
        ),
        (
            "p: Int, p: Int",
            "held = p + 1",
            "n = lag(id, p + 1) window(order by held)",
            [
                ("PIE-S2001", "Duplicate parameter name in query q: p", 1, 17),
                (POSITION, POSITION_MESSAGE, 5, 21),
            ],
        ),
        (
            "p: Text",
            "held = p",
            "n = lag(id, p) window(order by held)",
            [
                (
                    COUNT,
                    "A window count parameter must be declared Int, not Int | None.",
                    5,
                    21,
                )
            ],
        ),
        (
            "p: Int",
            "held = p + 1",
            "p",
            [
                (
                    COLLISION,
                    "Query parameter name is also a field, let, relation, output or window name.",
                    5,
                    9,
                )
            ],
        ),
    ),
    ids=("declaration", "duplicate", "count", "collision"),
)
def test_other_header_errors_keep_the_raw_result_and_diagnostic_objects(
    tmp_path: Path,
    _header_admission_trace,
    header: str,
    binding: str,
    projection: str,
    expected: list[tuple],
) -> None:
    body = (
        f"query q({header}):\n"
        "    from rows\n"
        f"    let {binding}\n"
        "    select:\n"
        f"        {projection}\n"
    )
    parsed = check_project_parse_only(_project(tmp_path, body))
    raw, normalizations, initial_results = _header_admission_trace
    assert len(initial_results) == 1
    assert not parsed.ok and normalizations == []
    assert parsed is initial_results[0]
    assert _header_error_rows(raw) == expected
    assert _header_error_rows(parsed.diagnostics) == expected
    assert all(
        current is original
        for current, original in zip(parsed.diagnostics, raw, strict=True)
    )
    from pietto.ast_nodes import QueryDef

    definition = parsed.parsed_inputs[0].script.definitions[-1]
    assert isinstance(definition, QueryDef)
    assert definition.naming_declarations and definition.let_clause is None


@pytest.mark.parametrize(
    ("bindings", "message", "naming_line", "read_line"),
    (
        (
            "    let held = p + 1\n    from rows\n",
            "A row-value let must follow FROM and every JOIN and precede WHERE",
            2,
            5,
        ),
        (
            "    from rows\n    let held = p + 1\n    let held = p + 2\n",
            "Duplicate query local name: held",
            4,
            6,
        ),
    ),
    ids=("before_from", "duplicate"),
)
def test_naming_refusal_restores_raw_parameter_errors_without_inventing_indirect_reads(
    tmp_path: Path,
    _header_admission_trace,
    bindings: str,
    message: str,
    naming_line: int,
    read_line: int,
) -> None:
    body = (
        "query q(p: Int):\n"
        + bindings
        + "    select:\n        n = lag(id, p + 1) window(order by held)\n"
    )
    parsed = check_project_parse_only(_project(tmp_path, body))
    raw, normalizations, initial_results = _header_admission_trace
    assert len(initial_results) == 1
    assert not parsed.ok and len(normalizations) == 1
    assert _header_error_rows(raw) == [(POSITION, POSITION_MESSAGE, read_line, 21)]
    assert _header_error_rows(parsed.diagnostics) == [
        ("PIE-S2604", message, naming_line, 5),
        (POSITION, POSITION_MESSAGE, read_line, 21),
    ]
    assert parsed.diagnostics[1] is raw[0]
