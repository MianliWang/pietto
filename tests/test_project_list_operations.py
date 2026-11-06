"""List operations of one row over its collected field in a `schema_version =
2` project: `len(c.xs)`, `sum(... for o in c.xs [if TEST])` and
`any(TEST for o in c.xs)`.

Each is one value per row, typed Int, Int and Bool, None exactly when the
row may have no container; it is admitted in a SELECT item, a row `let` or the
WHERE of a table or query without JOIN, GROUP BY, aggregate, DISTINCT, window
or QUALIFY. Every other spelling or place reports one exact diagnostic.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.cli import main as cli_main

HEAD = """shape Row:
    id: Int
shape Kid:
    id: Int
    amount: Int | None
    paid: Bool | None
    price: Decimal
source rows: Row = postgres.table("rows")
source kids: Kid = postgres.table("kids")
query parent:
    let mine:
        capture rows
        from kids
        where kids.id == rows.id
        select:
            id
            amount
            paid
            price
        order by id
    from rows
    select:
        id
        xs = collect mine
"""


def _root(tmp_path: Path, body: str, schema_version: int = 2) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(HEAD + body, encoding="utf-8")
    return root


def _query(name: str, *items: str, tail: str = "") -> str:
    lines = [f"query {name}:", "    from parent", tail]
    lines += ["    select:", "        id", *(f"        {item}" for item in items)]
    return "\n".join(line for line in lines if line) + "\n"


def _checked(root: Path):
    parsed = check_project_parse_only(root)
    if not parsed.ok:
        return parsed.diagnostics, None
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    return completed.diagnostics, completed


def _outputs(completed, name: str) -> dict[str, tuple[str, str]]:
    """The output fields of the table or query ``name``: its completed schema
    where completion rebuilt it (a JOIN input), else its relation facts'."""

    completed_schemas = [
        entry.schema
        for entry in completed.effective_outputs.entries
        if getattr(entry, "schema", None) is not None
        and entry.owner.definition.name == name
        and entry.owner.let_position is None
    ]
    if completed_schemas:
        (schema,) = completed_schemas
        fields = tuple(schema.fields.items())
    else:
        (fact,) = (
            fact
            for environment in completed.semantic_result.module_semantic_facts.environments
            for fact in environment.relation_facts
            if fact.owner.definition.name == name and fact.owner.let_position is None
        )
        fields = tuple((item.output_name, item.field) for item in fact.select_facts)
    return {
        field_name: (field.resolved_type.name, field.nullability.value)
        for field_name, field in fields
    }


def _rows(diagnostics, source: str):
    """Each diagnostic as (code, written text at its start, message, hint)."""

    lines = source.splitlines()
    return [
        (
            d.code,
            lines[d.location.line - 1][d.location.column - 1 :],
            d.message,
            d.suggestion,
        )
        for d in diagnostics
    ]


ADMITTED = (
    "n = len(parent.xs)",
    "total = sum(o.amount for o in parent.xs)",
    "paid_total = sum(o.amount for o in parent.xs if o.paid)",
    "paid_count = sum(1 for o in parent.xs if o.paid)",
    "has_paid = any(o.paid for o in parent.xs)",
    "has_big = any(o.amount > 3 and o.id < 2 for o in parent.xs)",
    "plus = len(parent.xs) + 1",
)


def test_each_list_operation_checks_with_its_type(tmp_path: Path) -> None:
    root = _root(tmp_path, _query("stats", *ADMITTED))

    diagnostics, semantic = _checked(root)

    assert diagnostics == ()
    assert _outputs(semantic, "stats") == {
        "id": ("Int", "non_null"),
        "n": ("Int", "non_null"),
        "total": ("Int", "non_null"),
        "paid_total": ("Int", "non_null"),
        "paid_count": ("Int", "non_null"),
        "has_paid": ("Bool", "non_null"),
        "has_big": ("Bool", "non_null"),
        # Arithmetic keeps no known nullability yet, as for any Int field.
        "plus": ("Int", "unknown"),
    }


def test_a_container_that_may_be_missing_makes_each_result_nullable(
    tmp_path: Path,
) -> None:
    root = _root(
        tmp_path,
        "query kept_parents:\n    let p = parent\n    from rows\n"
        "    left join p on rows.id == p.id\n"
        "    select:\n        id = rows.id\n        kept = p.xs\n"
        "query stats:\n    from kept_parents\n    select:\n        id\n"
        "        n = len(kept_parents.kept)\n"
        "        total = sum(o.amount for o in kept_parents.kept)\n"
        "        has_paid = any(o.paid for o in kept_parents.kept)\n",
    )

    diagnostics, semantic = _checked(root)

    assert diagnostics == ()
    assert _outputs(semantic, "stats") == {
        "id": ("Int", "non_null"),
        "n": ("Int", "nullable"),
        "total": ("Int", "nullable"),
        "has_paid": ("Bool", "nullable"),
    }


# An element is another row than the one that reads the list: an outer read
# is never rewritten to a field of the element.
_OUTSIDE = (
    "read the element's fields as `o.f` and the row's values outside the generator"
)
# Spellings refused before semantic analysis: the first rule each breaks.
GATED = (
    (
        "b = sum(1 for o in parent.xs)",
        "sum(",
        "PIE-S2334",
        "sum(1 for o in parent.xs) counts every element",
        "write `len(parent.xs)`",
    ),
    (
        "b = sum(o.amount + 1 for o in parent.xs)",
        "sum(",
        "PIE-S2315",
        "sum of a list adds 1 or one field of o; expression bodies are not "
        "supported yet",
        None,
    ),
    (
        "b = sum(o.amount if o.paid else 0 for o in parent.xs)",
        "sum(",
        "PIE-S2315",
        "sum of a list adds 1 or one field of o; expression bodies are not "
        "supported yet",
        "filter with `if` after the source: `sum(o.f for o in parent.xs if ...)`",
    ),
    (
        "b = sum(amount for o in parent.xs)",
        "sum(",
        "PIE-S2315",
        "sum of a list adds 1 or one field of o; expression bodies are not "
        "supported yet",
        "read the element as `o.amount`",
    ),
    (
        "b = any(o.paid for o in parent.xs if o.id > 1)",
        "any(",
        "PIE-S2334",
        "any takes its test in the body",
        "write `any(p and q for o in parent.xs)`",
    ),
    (
        "b = len(o for o in parent.xs)",
        "len(",
        "PIE-S2334",
        "len takes no generator",
        "count the list with `len(parent.xs)`",
    ),
    (
        "b = count(1 for o in parent.xs if o.paid)",
        "count(",
        "PIE-S2334",
        "count takes no generator",
        "count the matching elements with `sum(1 for o in parent.xs if ...)`",
    ),
    (
        "b = max(o.amount for o in parent.xs)",
        "max(",
        "PIE-S2334",
        "max takes no generator; a list max is not available",
        "`sum` and `any` take a list generator",
    ),
    (
        "b = sum(o.amount for o in parent.xs if id > 1)",
        "id > 1",
        "PIE-S2334",
        "Generator reads id outside its member",
        _OUTSIDE,
    ),
    (
        "b = any(parent.id > 1 for o in parent.xs)",
        "parent.id",
        "PIE-S2334",
        "Generator reads parent.id outside its member",
        _OUTSIDE,
    ),
    (
        "b = any(len(parent.xs) > 0 for o in parent.xs)",
        "parent.xs) > 0",
        "PIE-S2334",
        "Generator reads parent.xs outside its member",
        _OUTSIDE,
    ),
    (
        "b = sum(1 for o in group if o.paid)",
        "sum(",
        "PIE-S2334",
        "sum(... for ...) is not available in a project yet",
        "a single file checks and emits the conditional count and sum of a group",
    ),
    (
        "b = len(xs)",
        "xs)",
        "PIE-S2334",
        "len reads a row's collected list through its row",
        "write `len(parent.xs)`",
    ),
    (
        "b = sum(o.amount for o in xs)",
        "xs)",
        "PIE-S2301",
        "Unknown or unavailable generator source: xs",
        "a row's collected list is read through its row: `for o in parent.xs`",
    ),
)


@pytest.mark.parametrize(("item", "at", "code", "message", "hint"), GATED)
def test_each_refused_list_spelling_reports_its_first_broken_rule(
    tmp_path: Path, item: str, at: str, code: str, message: str, hint: str | None
) -> None:
    body = _query("stats", item)
    diagnostics, _ = _checked(_root(tmp_path, body))

    ((found_code, written, found_message, found_hint),) = _rows(
        diagnostics, HEAD + body
    )
    assert (found_code, found_message, found_hint) == (
        code,
        message if hint is None else f"{message}; {hint}",
        hint,
    )
    assert written.startswith(at)


@pytest.mark.parametrize(
    "joined",
    (
        "    from rows\n    inner join parent on rows.id == parent.id\n",
        "    from parent\n    inner join rows on rows.id == parent.id\n",
    ),
    ids=("list_of_the_joined_row", "list_of_the_from_row"),
)
def test_an_unknown_list_source_beside_a_join_names_no_row(
    tmp_path: Path, joined: str
) -> None:
    """With JOIN inputs the list may be any input's, so the hint names none."""
    body = (
        f"query stats:\n{joined}    select:\n        id = rows.id\n"
        "        n = sum(1 for o in xs if o.paid)\n"
    )
    diagnostics, _ = _checked(_root(tmp_path, body))

    hint = "a row's collected list is read through its row: `for o in c.xs`"
    assert _rows(diagnostics, HEAD + body) == [
        (
            "PIE-S2301",
            "xs if o.paid)",
            f"Unknown or unavailable generator source: xs; {hint}",
            hint,
        )
    ]


_SUM_BOOL = "count with `sum(1 for o in parent.xs if o.paid)`"
# Spellings the project checks refuse with the element's or the field's types.
TYPED = (
    (
        "b = sum(o.paid for o in parent.xs)",
        "sum(",
        "PIE-S2314",
        f"sum of a list adds an Int field of o, got Bool; {_SUM_BOOL}",
        _SUM_BOOL,
    ),
    (
        "b = sum(o.price for o in parent.xs)",
        "sum(",
        "PIE-S2314",
        "sum of a list adds an Int field of o, got Decimal; a list sum adds Int values",
        "a list sum adds Int values",
    ),
    (
        "b = sum(o.nosuch for o in parent.xs)",
        "o.nosuch",
        "PIE-S2102",
        "Unknown field: o.nosuch",
        None,
    ),
    (
        "b = any(o.amount for o in parent.xs)",
        "o.amount",
        "PIE-S2202",
        "Expected Bool expression in any test",
        None,
    ),
    (
        "b = sum(1 for o in parent.xs if o.amount)",
        "o.amount)",
        "PIE-S2202",
        "Expected Bool expression in generator test",
        None,
    ),
    (
        "b = sum(o.amount for o in parent.id)",
        "sum(",
        "PIE-S2334",
        "Generator source parent.id is not a collected list; a generator over "
        "a row's field reads a field that a `collect` SELECT item outputs",
        None,
    ),
    (
        "b = sum(o.amount for o in parent.nosuch)",
        "parent.nosuch",
        "PIE-S2102",
        "Unknown field: parent.nosuch",
        None,
    ),
)


@pytest.mark.parametrize(("item", "at", "code", "message", "hint"), TYPED)
def test_each_mistyped_list_operation_reports_one_error(
    tmp_path: Path, item: str, at: str, code: str, message: str, hint: str | None
) -> None:
    body = _query("stats", item)
    diagnostics, _ = _checked(_root(tmp_path, body))

    ((found_code, written, found_message, found_hint),) = _rows(
        diagnostics, HEAD + body
    )
    assert (found_code, found_message, found_hint) == (code, message, hint)
    assert written.startswith(at)


_READ = (
    "Read the list with `len`, `sum` or `any` in a SELECT item, a row `let` or "
    "the WHERE of a table or query without JOIN, GROUP BY, an aggregate, "
    "DISTINCT, a window or QUALIFY, and order or group by that output in a "
    "later table or query that reads it with `from`."
)
_CARRY = (
    "A table or query with a JOIN reads no list yet: select the list as it is "
    "here, as in `xs = parent.xs`, and read it with `len`, `sum` or `any` in a "
    "later table or query that reads it with `from`."
)


def test_a_bare_len_is_refused_where_a_join_rebuilds_its_input(
    tmp_path: Path,
) -> None:
    """`len(xs)` reports its PIE-S2334 at the field, also when a JOIN query
    reads `parent` and completion rebuilds its schema."""
    body = (
        "query kept:\n    let p = parent\n    from rows\n"
        "    left join p on rows.id == p.id\n    select:\n"
        "        id = rows.id\n        xs = p.xs\n" + _query("stats", "b = len(xs)")
    )

    diagnostics, _ = _checked(_root(tmp_path, body))

    assert _rows(diagnostics, HEAD + body) == [
        (
            "PIE-S2334",
            "xs)",
            "len reads a row's collected list through its row; write `len(parent.xs)`",
            "write `len(parent.xs)`",
        )
    ]


def test_a_row_let_and_the_where_read_a_list_too(tmp_path: Path) -> None:
    body = _query(
        "stats",
        "k",
        tail="    let k = sum(1 for o in parent.xs if o.paid)\n"
        "    where any(o.amount > 3 for o in parent.xs) and len(parent.xs) > 1",
    )

    diagnostics, semantic = _checked(_root(tmp_path, body))

    assert diagnostics == ()
    assert _outputs(semantic, "stats") == {
        "id": ("Int", "non_null"),
        "k": ("Int", "non_null"),
    }


def _nested(place: str) -> str:
    return (
        f"Nested relation field parent.xs cannot be read in {place}: a collected "
        "relation has no comparison, ordering, grouping or scalar value."
    )


@pytest.mark.parametrize(
    ("body", "place", "hint"),
    (
        (
            "query stats:\n    from parent\n    group by id\n    select:\n"
            "        id\n        n = len(parent.xs)\n",
            "a SELECT expression",
            _READ,
        ),
        (
            "query stats:\n    from parent\n    select:\n        id\n"
            "        n = len(parent.xs)\n        k = count()\n",
            "a SELECT expression",
            _READ,
        ),
        (
            "query stats:\n    from parent\n    inner join rows on parent.id == rows.id\n"
            "    select:\n        id = parent.id\n"
            "        a = any(o.paid for o in parent.xs)\n",
            "a SELECT expression",
            _CARRY,
        ),
        (
            "query stats:\n    from parent\n    left join rows on parent.id == rows.id\n"
            "    where len(parent.xs) > 0\n    select:\n        id = parent.id\n",
            "WHERE",
            _CARRY,
        ),
        (
            "query stats:\n    from parent\n    right join rows on parent.id == rows.id\n"
            "    select:\n        id = rows.id\n"
            "        a = any(o.paid for o in parent.xs)\n",
            "a SELECT expression",
            _READ,
        ),
        (
            "query stats:\n    from parent\n    select:\n        id\n"
            "        n = count(parent.xs)\n",
            "a SELECT expression",
            "Count the list with `len(parent.xs)`.",
        ),
        (_query("stats") + "    order by len(parent.xs)\n", "ORDER BY", _READ),
        (
            _query("stats") + "    order by sum(o.amount for o in parent.xs), id\n",
            "ORDER BY",
            _READ,
        ),
        (
            _query("stats") + "    order by any(o.paid for o in parent.xs) desc\n"
            "    limit 2\n",
            "ORDER BY",
            _READ,
        ),
        (
            "query stats:\n    from parent\n    select distinct:\n        id\n"
            "    order by len(parent.xs)\n",
            "ORDER BY",
            _READ,
        ),
        (
            "query stats:\n    let sub:\n        capture parent\n        from kids\n"
            "        where kids.id == parent.id and len(parent.xs) > 0\n"
            "        select id\n        order by id\n    from parent\n"
            "    select:\n        id\n        ys = collect sub\n",
            "WHERE",
            _READ,
        ),
        (
            _query(
                "stats",
                tail="    where any(k.id == parent.id and k.id < len(parent.xs) "
                "for k in kids)",
            ),
            "an ANY test",
            _READ,
        ),
        (
            "query stats:\n    from parent\n    inner join rows on parent.id == rows.id\n"
            "    select:\n        id = parent.id\n        n = count(parent.xs)\n",
            "a SELECT expression",
            "Count the list with `len(parent.xs)`.",
        ),
        (
            "query stats:\n    from parent\n"
            "    inner join kids on kids.id == parent.id and len(parent.xs) > 0\n"
            "    select:\n        id = parent.id\n",
            "JOIN ON",
            _CARRY,
        ),
        (
            "query stats:\n    from parent\n    select:\n        id\n"
            "        w = count(parent.xs) window(order by id)\n",
            "a window",
            "Count the list with `len(parent.xs)`.",
        ),
        (
            "query stats:\n    from parent\n    select:\n        id\n"
            "        w = len(parent.xs) window(order by id)\n",
            "a window",
            _READ,
        ),
    ),
    ids=(
        "grouped",
        "aggregate",
        "join",
        "join-where",
        "right-join",
        "count",
        "order",
        "order-sum",
        "order-any-limit",
        "distinct-order",
        "capture-where",
        "relation-any",
        "join-count",
        "join-on",
        "window-count",
        "window-len",
    ),
)
def test_a_list_read_outside_its_place_stays_a_nested_read(
    tmp_path: Path, body: str, place: str, hint: str
) -> None:
    diagnostics, _ = _checked(_root(tmp_path, body))

    assert [
        (code, written.startswith(("parent.xs", "xs")), message, found)
        for code, written, message, found in _rows(diagnostics, HEAD + body)
        if code == "PIE-S2805"
    ] == [("PIE-S2805", True, _nested(place), hint)]


@pytest.mark.parametrize(
    ("body", "place", "hint"),
    (
        (_query("stats", "n = count(xs)"), "a SELECT expression", "parent"),
        (_query("stats") + "    order by count(xs)\n", "ORDER BY", "parent"),
        (
            "query stats:\n    let p:\n        from parent\n        select:\n"
            "            id\n            n = count(xs)\n    from rows\n"
            "    select:\n        id\n",
            "a SELECT expression",
            "parent",
        ),
        (
            "query stats:\n    from rows\n    inner join parent on rows.id == parent.id\n"
            "    select:\n        id = rows.id\n        n = count(xs)\n",
            "a SELECT expression",
            None,
        ),
    ),
    ids=("select", "order", "relation-let", "join"),
)
def test_a_bare_list_count_names_the_list_through_its_row(
    tmp_path: Path, body: str, place: str, hint: str | None
) -> None:
    """`count(xs)` suggests `len` of the list read through its FROM row; in a
    body with JOIN inputs, whose row the hint cannot name, the list route."""
    diagnostics, _ = _checked(_root(tmp_path, body))

    assert [
        (code, written.startswith("xs"), message, found)
        for code, written, message, found in _rows(diagnostics, HEAD + body)
        if code == "PIE-S2805"
    ] == [
        (
            "PIE-S2805",
            True,
            _nested(place).replace("parent.xs", "xs", 1),
            _READ if hint is None else f"Count the list with `len({hint}.xs)`.",
        )
    ]


def test_a_schema_version_1_project_refuses_a_list_generator(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    source = (
        "shape Row:\n    id: Int\n"
        'source rows: Row = postgres.table("rows")\n'
        "query stats:\n    from rows\n    select:\n        id\n"
        "        n = sum(1 for o in rows.xs if o.paid)\n"
    )
    (root / "main.pietto").write_text(source, encoding="utf-8")

    diagnostics, _ = _checked(root)

    assert [(d.code, d.location.line, d.location.column) for d in diagnostics] == [
        ("PIE-S2334", 8, 13)
    ]
    assert diagnostics[0].message.startswith(
        "sum(... for ...) is not available in a project yet"
    )


def test_the_project_check_json_reports_a_list_refusal_with_its_hint(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _root(tmp_path, _query("stats", *ADMITTED[:2], GATED[0][0]))

    assert cli_main(["check", "--project", str(root), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
    assert [
        (
            item["code"],
            item["location"]["line"],
            item["location"]["column"],
            item["suggestion"],
        )
        for item in document["diagnostics"]
    ] == [("PIE-S2334", 31, 13, "write `len(parent.xs)`")]
