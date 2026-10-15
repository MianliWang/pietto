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
    id: Int not null
    plain: Int not null
    label: Text not null
source rows: Row is postgres.table("rows")
"""
FIRST = HEADER.count("\n") + 1
POSITION = "PIE-S2355"
POSITION_MESSAGE = "Query parameters are not available in this position."
COLLISION = "PIE-S2354"
DECLARATION = "PIE-S2353"
INPUT = "PIE-S2356"
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
    "query q(cutoff: Int not null, label2: Text nullable):\n"
    "    from rows\n"
    "    let:\n"
    "        next = cutoff + 1\n"
    "    where id > cutoff and label == label2\n"
    "    select:\n"
    "        id\n"
    "        bumped = next\n"
)


def test_only_an_explicit_module_project_admits_a_header(tmp_path: Path) -> None:
    assert _check(_project(tmp_path / "explicit", VALID)) == (0, [])
    assert _check(_project(tmp_path / "flat", VALID, schema=1)) == (
        1,
        [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 31)],
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
            "    values(id: Int not null):\n        1\n",
            [("PIE-S2346", 1)],
        ),
        (
            "    from generate_series(1, 31, 1) as n\n    select:\n        n\n",
            [("PIE-S2346", 1), ("PIE-S2352", 2)],
        ),
    ),
    ids=("let_set_operation", "set_operation", "values", "table_function"),
)
def test_a_header_without_a_relation_from_body_stays_unadmitted(
    tmp_path: Path, body: str, expected: list[tuple[str, int]]
) -> None:
    source = "query q(cutoff: Int not null):\n" + body
    parsed = check_project_parse_only(_project(tmp_path, source))
    assert [
        (d.code, d.location.line - FIRST + 1) for d in parsed.diagnostics
    ] == expected


@pytest.mark.parametrize(
    ("declaration", "expected"),
    (
        ("a: Int", [(DECLARATION, 1, 9)]),
        ("a: Decimal(3, 1) not null", [(DECLARATION, 1, 9)]),
        ("a: UUID nullable", [(DECLARATION, 1, 9)]),
        ("a: Int not null, a: Bool nullable", [("PIE-S2001", 1, 26)]),
    ),
    ids=("implicit_nullability", "type_arguments", "other_builtin", "duplicate"),
)
def test_header_declarations_are_checked_before_semantics(
    tmp_path: Path, declaration: str, expected: list[tuple[str, int, int]]
) -> None:
    body = f"query q({declaration}):\n    from rows\n    select:\n        id\n"
    assert _check(_project(tmp_path, body)) == (1, expected)


def test_at_most_sixty_four_parameters(tmp_path: Path) -> None:
    allowed = ", ".join(f"p{i}: Int not null" for i in range(64))
    body = f"query q({allowed}, extra: Int not null):\n    from rows\n"
    body += "    select:\n        id\n"
    column = len("query q(") + len(allowed) + len(", ") + 1
    assert _check(_project(tmp_path, body)) == (1, [(DECLARATION, 1, column)])


HEADER_QUERY = "query q(cutoff: Int not null, word: Text nullable):\n    from rows\n"
ADMITTED = {
    "satisfying": (
        "    group by:\n        id\n    select:\n        id\n        n = count()\n"
        "    satisfying:\n        n > cutoff\n"
    ),
    "qualify": (
        "    select:\n        id\n        r = row_number() window:\n"
        "            order by:\n                id\n"
        "    qualify:\n        r <= cutoff + 1\n"
    ),
    "order_key_through_let": (
        "    let:\n        s = id * cutoff\n    select:\n        id\n"
        "    order by:\n        s desc\n    limit 2\n"
    ),
    "order_key_matching_output": (
        "    select:\n        id\n        k = id + cutoff\n"
        "    order by:\n        id + cutoff\n"
    ),
    "let_aggregates": (
        "    let:\n        s = id + cutoff\n    group by:\n        plain\n"
        "    select:\n        plain\n        n = count(s)\n        a = avg(s)\n"
        "        m = max(s)\n        lo = min(s)\n    order by:\n        n\n"
    ),
    "computed_group_key": (
        "    let:\n        k = id * cutoff\n    group by:\n        k\n"
        "    select:\n        k\n        n = count()\n"
        "    satisfying:\n        n > cutoff\n"
    ),
    "joined_satisfying": (
        "    inner join rows as r:\n        from rows\n        on rows.id == r.id\n"
        "    group by:\n        rows.id\n    select:\n        k = rows.id\n"
        "        n = count()\n    satisfying:\n        n > cutoff\n"
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
        "    let:\n        j = id + cutoff\n        k = j\n    group by:\n        k\n"
        "    select:\n        k\n        n = count()\n",
        [(POSITION, 7, 9), (POSITION, 9, 9)],
    ),
    "group_key_with_join": (
        "    inner join rows as r:\n        from rows\n        on rows.id == r.id\n"
        "    let:\n        g = rows.id * cutoff\n    group by:\n        g\n"
        "    select:\n        g\n        n = count()\n",
        [(POSITION, 9, 9), (POSITION, 11, 9)],
    ),
    "grouped_select": (
        "    group by:\n        id\n    select:\n        id\n"
        "        n = count()\n        c = cutoff\n",
        [(POSITION, 8, 13)],
    ),
    "sum_of_dependent_let": (
        "    let:\n        s = id + cutoff\n" + GROUPED + "        t = sum(s)\n",
        [(POSITION, 9, 17)],
    ),
    "count_distinct_of_dependent_let": (
        "    let:\n        s = id + cutoff\n"
        + GROUPED
        + "        t = count_distinct(s)\n",
        [(POSITION, 9, 28)],
    ),
    "arithmetic_over_let_aggregate": (
        "    let:\n        s = id + cutoff\n" + GROUPED + "        n = count(s) + 1\n",
        [(POSITION, 9, 19)],
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
        "    select:\n        id\n        w = lag(id, cutoff + 1) window:\n"
        "            order by:\n                id\n",
        [(POSITION, 5, 21)],
    ),
    "window_partition": (
        "    select:\n        id\n        r = row_number() window:\n"
        "            partition by:\n                cutoff\n"
        "            order by:\n                id\n",
        [(POSITION, 7, 17)],
    ),
    "grouped_window": (
        "    group by:\n        id\n    select:\n        id\n"
        "        w = lag(id, cutoff) window:\n            order by:\n"
        "                id\n",
        [(POSITION, 7, 21)],
    ),
    "window_order": (
        "    let:\n        s = cutoff * 2\n    select:\n        id\n"
        "        r = row_number() window:\n            order by:\n                s\n",
        [(POSITION, 9, 17)],
    ),
    "aggregate_without_group_by": (
        "    select:\n        n = count()\n        v = cutoff\n",
        [(POSITION, 5, 13)],
    ),
    "named_window": (
        "    select:\n        id\n        r = row_number() window w\n"
        "    window w:\n        order by:\n            cutoff\n",
        [(POSITION, 8, 13)],
    ),
    "frame_offset": (
        "    select:\n        id\n        f = first_value(id) window:\n"
        "            order by:\n                id\n"
        "            rows between cutoff preceding and current row\n",
        [(POSITION, 8, 26)],
    ),
    "named_window_frame_offset": (
        "    select:\n        id\n        f = first_value(id) window w\n"
        "    window w:\n        order by:\n            id\n"
        "        range between current row and cutoff following\n",
        [(POSITION, 9, 39)],
    ),
    "frame_offset_through_let": (
        "    let:\n        k = cutoff\n    select:\n        id\n"
        "        f = first_value(id) window:\n            order by:\n"
        "                id\n            groups between k preceding and current row\n",
        [(POSITION, 10, 28)],
    ),
    "named_window_through_let": (
        "    let:\n        s = id + cutoff\n    select:\n        id\n"
        "        r = row_number() window ordered\n"
        "    window ordered:\n        order by:\n            s\n",
        [(POSITION, 10, 13)],
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


@pytest.mark.parametrize(
    ("header", "clauses", "expected"),
    (
        ("id: Int not null", "    select:\n        a = plain\n", [(COLLISION, 1, 9)]),
        ("rows: Int not null", "    select:\n        id\n", [(COLLISION, 1, 9)]),
        (
            "s: Int not null",
            "    let:\n        s = 1\n    select:\n        id\n",
            [(COLLISION, 1, 9)],
        ),
        ("a: Int not null", "    select:\n        a = plain\n", [(COLLISION, 1, 9)]),
        (
            "w: Int not null",
            "    select:\n        id\n    window w:\n        order by:\n"
            "            id\n",
            [(COLLISION, 1, 9)],
        ),
        (
            "c: Int not null",
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
        "query q(p: Text not null):\n"
        "    from rows\n"
        "    let:\n"
        "        n = lower(label)\n"
        '    where lower(label) == "x"\n'
        "    select:\n"
        "        label = p\n"
        "        m = lower(label)\n"
    )
    assert _check(_project(tmp_path / "rows", body)) == (0, [])
    # ORDER BY resolves the output: a key may name it (emission decides; outside
    # a grouped query it refuses an output key), but a structural call argument
    # or LIMIT that reads it is refused.
    ordered = body + "    order by:\n        label\n"
    assert _check(_project(tmp_path / "order", ordered)) == (0, [])
    structural = body + "    order by:\n        substr(label, 1, 2)\n"
    assert _check(_project(tmp_path / "substr", structural)) == (
        1,
        [(POSITION, 10, 16)],
    )
    limited = body + "    limit label\n"
    assert _check(_project(tmp_path / "limit", limited)) == (1, [(POSITION, 9, 11)])
    # A named window key reads the shadowed input field too; a name with no
    # input field is unknown there, as in an inline window.
    for clause in ("partition by", "order by"):
        for name, expected in (("label", []), ("k", [("PIE-S2102", 12, 13)])):
            ordered_by_id = "        order by:\n            id\n"
            windowed = (
                body.replace("label = p", f"{name} = p")
                + "        r = row_number() window w\n"
                + f"    window w:\n        {clause}:\n            {name}\n"
                + ordered_by_id * (clause == "partition by")
            )
            root = tmp_path / f"{clause.split()[0]}-{name}"
            assert _check(_project(root, windowed)) == (int(bool(expected)), expected)


def test_a_join_binding_and_its_fields_are_collisions(tmp_path: Path) -> None:
    body = (
        "query q(r: Int not null, plain: Int not null):\n"
        "    from rows\n"
        "    inner join rows as r:\n"
        "        from rows\n"
        "        on rows.id == r.id\n"
        "    select:\n"
        "        a = rows.id\n"
    )
    assert _check(_project(tmp_path, body)) == (
        1,
        [(COLLISION, 1, 9), (COLLISION, 1, 26)],
    )


def test_a_parameterized_query_is_never_a_relation_input(tmp_path: Path) -> None:
    body = (
        "query q(cutoff: Int not null):\n"
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
        "    inner join q as k:\n"
        "        from rows\n"
        "        on rows.id == k.id\n"
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
        (INPUT, 12, 5),
        (INPUT, 20, 9),
    ]


PARAMETERIZED = (
    "query p(c: Int not null):\n"
    "    from rows\n"
    "    where id > c\n"
    "    select:\n"
    "        id\n"
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
        "        inner join p as k:\n"
        "            from rows\n"
        "            on rows.id == k.id\n"
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
        "    inner join a as b:\n"
        "        from p\n"
        "        on p.id == b.id\n"
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
        [(INPUT, 8, 9), (INPUT, 17, 9), (INPUT, 30, 5), (INPUT, 43, 9)],
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
    assert _check(_project(tmp_path / "hiding", hiding)) == (
        1,
        [("PIE-S2001", 7, 5), ("PIE-S2333", 6, 1)],
    )


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
            "query r:\n"
            "    let a:\n"
            "        from rows\n"
            "        select:\n"
            "            id\n"
            "            extra = plain\n"
            "    from rows\n"
            "    inner join a as b:\n"
            "        from rows\n"
            "        on rows.id == b.id\n"
            "    select:\n"
            "        id = rows.id\n"
            "        extra = b.extra\n",
            "r",
            14,
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
            "table j:\n"
            "    from rows\n"
            "    inner join rows as o:\n"
            "        from rows\n"
            "        on rows.id == o.id\n"
            "    select:\n"
            "        id = rows.id\n"
            "        extra = o.plain\n",
            "j",
            9,
        ),
    ),
    ids=("let_block", "let_join", "grouped", "join"),
)
def test_a_header_name_never_shadows_a_completed_input_field(
    tmp_path: Path, inputs: str, relation: str, line: int
) -> None:
    entry = (
        "query q(extra: Int not null):\n"
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


VALUES_QUERY = (
    "query v:\n    values(id: Int not null, extra: Int nullable):\n        1, 2\n"
)
VALUES_FROM = (
    "query q(extra: Int not null):\n"
    "    from v\n"
    "    where id > extra\n"
    "    select:\n"
    "        id\n"
)


@pytest.mark.parametrize(
    ("inputs", "entry", "line"),
    (
        (VALUES_QUERY, VALUES_FROM, 4),
        (VALUES_QUERY.replace("query v", "table v"), VALUES_FROM, 4),
        (
            VALUES_QUERY,
            "query q(extra: Int not null):\n"
            "    from rows\n"
            "    inner join v as w:\n"
            "        from rows\n"
            "        on rows.id == w.id\n"
            "    where rows.id > extra\n"
            "    select:\n"
            "        id = rows.id\n",
            4,
        ),
        (
            "table v:\n"
            "    let seed:\n"
            "        values(id: Int not null, extra: Int nullable):\n"
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
        "query q(step: Int not null, fill: Int nullable, seed: Int not null):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        a = lag(id, step, fill) window:\n"
        "            order by:\n                id\n"
        "        b = ntile(step) window:\n"
        "            order by:\n                id\n"
        "        c = nth_value(plain, step) window:\n"
        "            order by:\n                id\n"
        "            rows between unbounded preceding and unbounded following\n"
        "        d = first_value(seed) window:\n"
        "            order by:\n                id\n"
        "            rows between unbounded preceding and current row\n"
    )
    assert _check(_project(tmp_path, body)) == (0, [])


def test_a_window_count_parameter_is_int_not_null(tmp_path: Path) -> None:
    body = (
        "query q(n: Int nullable, t: Text not null, r: Float not null):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        a = lag(id, n) window:\n"
        "            order by:\n                id\n"
        "        b = ntile(t) window:\n"
        "            order by:\n                id\n"
        "        c = nth_value(id, r) window:\n"
        "            order by:\n                id\n"
        "            rows between unbounded preceding and unbounded following\n"
    )
    message = "A window count parameter must be declared Int not null."
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [(COUNT, message, 5, 21), (COUNT, message, 8, 19), (COUNT, message, 11, 27)],
    )


def test_other_window_positions_never_read_a_parameter(tmp_path: Path) -> None:
    body = (
        "query q(cutoff: Int not null):\n"
        "    from rows\n"
        "    let:\n"
        "        s = cutoff * 2\n"
        "    select:\n"
        "        id\n"
        "        f = first_value(id) window:\n"
        "            order by:\n                id\n"
        "            rows between cutoff preceding and current row\n"
        "        t = sum(cutoff) window:\n"
        "            order by:\n                id\n"
        "        p = row_number() window:\n"
        "            partition by:\n                cutoff\n"
        "            order by:\n                s\n"
        "        n = lag(id, cutoff + 1) window:\n"
        "            order by:\n                id\n"
        "        g = first_value(id) window base\n"
        "    window base:\n"
        "        order by:\n"
        "            id\n"
        "        groups between current row and s following\n"
    )
    message = "Query parameters are not available in this position."
    assert _check(_project(tmp_path, body), messages=True) == (
        1,
        [
            (POSITION, message, line, column)
            for line, column in (
                (10, 26),  # frame offset
                (11, 17),  # an argument of another window function
                (16, 17),  # PARTITION BY key
                (18, 17),  # ORDER BY key through a let
                (19, 21),  # a read beneath an operator in an argument
                (26, 40),  # named-window frame offset through a let
            )
        ],
    )


LET_VALID = (
    "query q(cutoff: Int not null, label2: Text nullable):\n"
    "    let recent:\n"
    "        from rows\n"
    "        let:\n"
    "            next = cutoff + 1\n"
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
        [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 31), ("PIE-S2345", 2, 5)],
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
    ] == [("PIE-S2346", 1, 9), ("PIE-S2346", 1, 31), ("PIE-S2345", 2, 5)]


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
        ("plain: Int not null", "        select:\n            id\n", [(1, 9)]),
        ("a: Int not null", "        select:\n            id\n", [(1, 9)]),
        (
            "z: Int not null",
            "        select:\n            id\n            z = plain\n",
            [(1, 9)],
        ),
        (
            "s: Int not null",
            "        let:\n            s = 1\n        select:\n            id\n",
            [(1, 9)],
        ),
        (
            "k: Int not null",
            "        inner join rows as k:\n            from rows\n"
            "            on rows.id == k.id\n        select:\n"
            "            id = rows.id\n",
            [(1, 9)],
        ),
        (
            "w: Int not null",
            "        select:\n            id\n        window w:\n"
            "            order by:\n                id\n",
            [(1, 9)],
        ),
        (
            "c: Int not null",
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
    allowed = ", ".join(f"p{i}: Int not null" for i in range(64))
    tail = "    let a:\n        from rows\n        where id > p0\n"
    tail += "        select:\n            id\n    from a\n    select:\n        id\n"
    assert _check(_project(tmp_path / "64", f"query q({allowed}):\n" + tail)) == (
        0,
        [],
    )
    body = f"query q({allowed}, extra: Int not null):\n" + tail
    column = len("query q(") + len(allowed) + len(", ") + 1
    assert _check(_project(tmp_path / "65", body)) == (1, [(DECLARATION, 1, column)])


def test_a_query_whose_lets_read_its_header_is_never_an_input(
    tmp_path: Path,
) -> None:
    body = (
        "query q(cutoff: Int not null):\n"
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
