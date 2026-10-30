"""Closed relation lets of explicit-module projects: scope, identity, availability.

A let is its own owner with its own occurrence identity; it is never a module
declaration and shares one name scope with the module's relations and its
declaration's JOIN bindings. Any block of its declaration may read it any
number of times, before or after it, while the reads stay acyclic; a let no
block reads, or one nested deeper than 16 query blocks, is an error.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
from typing import Any

import pytest

import _pietto_sql_emission as probe
from pietto import cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssueStatus,
)
from pietto.semantic.model import ValueType

TARGETS = ("postgres", "mysql")
HEAD = """shape Row:
    id: Int
    key: Int | None
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
"""


def _check(tmp_path: Path, body: str, *, config: str = probe.CONFIG):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(config)
    (tmp_path / "main.pietto").write_text(HEAD + body)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    document = json.loads(out.getvalue())
    return code, [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ]


LET = "    let a:\n        from lhs\n        select:\n            id\n"
DIAGNOSTICS = {
    # A relation whose FROM does not resolve reports only why, as in a single
    # file; before, a PIE-S2333 at the relation followed.
    "duplicate_let": (
        "query q:\n" + LET + LET + "    from a\n    select:\n        id\n",
        [("PIE-S2001", "Duplicate symbol name in relation namespace: a", 11, 5)],
    ),
    "module_relation": (
        "query q:\n    let lhs:\n        from rhs\n        select:\n            id\n"
        "    from lhs\n    select:\n        id\n",
        [("PIE-S2001", "Duplicate symbol name in relation namespace: lhs", 7, 5)],
    ),
    "own_declaration": (
        "query q:\n    let q:\n        from rhs\n        select:\n            id\n"
        "    from q\n    select:\n        id\n",
        [("PIE-S2001", "Duplicate symbol name in relation namespace: q", 7, 5)],
    ),
    # Modern naming rejects both the duplicate local name and its ambiguous
    # JOIN input before the relation catalog selects any candidate.
    "join_binding": (
        "query q:\n" + LET + "    from lhs\n    let a = rhs\n"
        "    inner join a on lhs.id == a.id\n    select:\n        id = lhs.id\n",
        [
            ("PIE-S2604", "Duplicate query local name: a", 12, 5),
            ("PIE-S2604", "Ambiguous JOIN input: a", 13, 5),
        ],
    ),
    "cycle_through_parent": (
        "query q:\n    let a:\n        from q\n        select:\n            id\n"
        "    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> q -> a", 11, 5)],
    ),
    "outside_its_declaration": (
        "query q:\n" + LET + "    from a\n    select:\n        id\n"
        "query r:\n    from a\n    select:\n        id\n",
        [("PIE-S2301", "Unknown relation: a", 15, 5)],
    ),
    # Another declaration's let issue never stands in for this read's own;
    # the set that reads it reports no temporary admission text.
    "other_declarations_let_issue": (
        "query q:\n" + LET + "    from lhs\n    select:\n        id\n"
        "query r:\n    union all:\n        from a\n        from lhs\n",
        [
            ("PIE-S2359", "Let relation a is never read.", 7, 5),
            ("PIE-S2301", "Unknown relation: a", 16, 9),
        ],
    ),
    "capture": (
        "query q:\n    let a:\n        capture lhs\n        from rhs\n"
        "        select:\n            id\n    from a\n    select:\n        id\n",
        [
            (
                "PIE-S2366",
                "Capture lhs does not name one FROM or JOIN row input of q.",
                8,
                9,
            ),
            (
                "PIE-S2370",
                "Let a with capture lines can be read only once, by exists, scalar, "
                "in, collect or a join in the body of q.",
                12,
                5,
            ),
        ],
    ),
    # A named window shares the let namespace of its declaration and reads
    # only the value lets before it.
    "window_named_like_a_relation_let": (
        "query q:\n" + LET + "    from a\n    let a = window(order by id)\n"
        "    select:\n        id\n        n = row_number() window a\n",
        [("PIE-S2604", "Duplicate query local name: a", 12, 5)],
    ),
    "window_named_like_a_value_let": (
        "query q:\n" + LET + "    from a\n    let n = id\n"
        "    let n = window(order by id)\n"
        "    select:\n        id\n        r = row_number() window n\n",
        [("PIE-S2604", "Duplicate query local name: n", 13, 5)],
    ),
    "window_reads_a_later_value_let": (
        "query q:\n" + LET + "    from a\n    let w = window(order by k)\n"
        "    let k = id\n    select:\n        id\n        r = row_number() window w\n",
        [("PIE-S2330", "Let binding cannot reference a later binding: k", 12, 29)],
    ),
    # Nor may a window take the name of an input relation or field, as a value
    # let may not; a relation let's window is checked in its own body.
    "window_named_like_the_from_input": (
        "query q:\n    from lhs\n    let lhs = window(order by id)\n"
        "    select:\n        id\n        n = row_number() window lhs\n",
        [("PIE-S2329", "Let binding cannot shadow input relation: lhs", 8, 5)],
    ),
    "window_named_like_a_joined_field": (
        "query q:\n    from lhs\n    inner join rhs on lhs.id == rhs.id\n"
        "    let key = window(order by lhs.id)\n"
        "    select:\n        id = lhs.id\n        n = row_number() window key\n",
        [("PIE-S2329", "Let binding cannot shadow input field: key", 9, 5)],
    ),
    "window_named_like_a_let_output": (
        "query q:\n" + LET + "    from a\n    let id = window(order by id)\n"
        "    select:\n        id\n        n = row_number() window id\n",
        [("PIE-S2329", "Let binding cannot shadow input field: id", 12, 5)],
    ),
    "window_in_a_let_named_like_its_input_field": (
        "query q:\n    let a:\n        from lhs\n        let key = window(order by id)\n"
        "        select:\n            id\n            n = row_number() window key\n"
        "    from a\n    select:\n        id\n",
        [("PIE-S2329", "Let binding cannot shadow input field: key", 9, 9)],
    ),
    "window_named_like_a_table_function_column": (
        "query q:\n    from generate_series(1, 3, 1) as n\n"
        "    let n = window(order by n)\n"
        "    select:\n        n\n        r = row_number() window n\n",
        [("PIE-S2329", "Let binding cannot shadow input field: n", 8, 5)],
    ),
    "window_named_like_a_values_column": (
        "query q:\n    let seed:\n        values(code: Int):\n            1\n"
        "    from seed\n    let code = window(order by code)\n"
        "    select:\n        code\n        r = row_number() window code\n",
        [("PIE-S2329", "Let binding cannot shadow input field: code", 11, 5)],
    ),
    "window_named_like_a_set_label": (
        "query q:\n    let s1:\n        values(code: Int):\n            1\n"
        "    let s2:\n        values(code: Int):\n            2\n"
        "    let both:\n        union all s1, s2\n"
        "    from both\n    let code = window(order by code)\n"
        "    select:\n        code\n        r = row_number() window code\n",
        [("PIE-S2329", "Let binding cannot shadow input field: code", 16, 5)],
    ),
}


@pytest.mark.parametrize("case", sorted(DIAGNOSTICS))
def test_let_scope_and_readability_diagnostics(tmp_path: Path, case: str) -> None:
    body, expected = DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1, expected)


def _let_chains(count: int) -> str:
    """`count` lets in chains of 16 (the nesting limit), one operand per chain."""
    lets = "".join(
        f"    let l{i}:\n        from {f'l{i + 1}' if (i + 1) % 16 else 'lhs'}\n"
        "        select:\n            id\n"
        for i in range(count)
    )
    heads = "".join(f"        from l{i}\n" for i in range(0, count, 16))
    return f"query q:\n{lets}    union all:\n{heads}"


@pytest.mark.parametrize("count", (64, 65))
def test_a_declaration_declares_at_most_64_lets(tmp_path: Path, count: int) -> None:
    expected = [
        (
            "PIE-S2357",
            "A table or query declares at most 64 relation lets.",
            7 + 4 * 64,
            5,
        )
    ]
    assert _check(tmp_path, _let_chains(count)) == (
        (0, []) if count == 64 else (1, expected)
    )


def _let(name: str, source: str, *, where: str = "") -> str:
    """One relation let `name` projecting `id` from `source`."""
    return (
        f"    let {name}:\n        from {source}\n{where}"
        "        select:\n            id\n"
    )


def _set_let(name: str, *operands: str) -> str:
    """One relation let `name` that is a UNION ALL of `operands`."""
    reads = "".join(f"            from {operand}\n" for operand in operands)
    return f"    let {name}:\n        union all:\n{reads}"


def _chain(depth: int) -> str:
    """`query q` reading l0, each l(i) reading l(i+1) and the last one lhs."""
    lets = "".join(
        _let(f"l{i}", f"l{i + 1}" if i + 1 < depth else "lhs") for i in range(depth)
    )
    return "query q:\n" + lets + "    from l0\n    select:\n        id\n"


def test_lets_may_be_read_repeatedly_and_before_they_are_declared(
    tmp_path: Path,
) -> None:
    body = (
        "query q:\n"
        + _let("low", "base", where="        where id < 2\n")
        + _let("high", "base", where="        where id > 0\n")
        + _let("base", "lhs")
        + "    union all:\n        from low\n        from high\n"
    )
    assert _check(tmp_path, body) == (0, [])
    semantic = build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    assert semantic.module_catalogs is not None
    (catalog,) = semantic.module_catalogs.catalogs
    assert [let.definition.name for let in catalog.lets] == ["low", "high", "base"]
    # Relation-body readers meet each let after every let it reads; source
    # positions stay the let identities.
    assert [(o.definition.name, o.let_position) for o in catalog.relation_owners] == [
        ("Row", None),
        ("lhs", None),
        ("rhs", None),
        ("base", 2),
        ("low", 0),
        ("high", 1),
        ("q", None),
    ]
    # Sixteen nested query blocks below the body are the limit.
    assert _check(tmp_path / "deep", _chain(16)) == (0, [])


# Every let read error in full: one diagnostic per problem and no cascade.
READ_ERRORS = {
    "unread": (
        "query q:\n"
        + _let("a", "lhs")
        + _let("b", "a")
        + "    from lhs\n    select:\n        id\n",
        [("PIE-S2359", "Let relation b is never read.", 11, 5)],
    ),
    "self": (
        "query q:\n" + _let("a", "a") + "    from lhs\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> a", 8, 9)],
    ),
    "cycle": (
        "query q:\n"
        + _let("a", "c")
        + _let("b", "a")
        + _let("c", "b")
        + "    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> c -> b -> a", 12, 9)],
    ),
    # A cycle starts with its member written first, lets before their
    # declaration, even when `a` is read after `b` is.
    "cycle_through_parent_forward": (
        "query q:\n"
        + _let("a", "b")
        + _let("b", "q")
        + "    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> b -> q -> a", 15, 5)],
    ),
    "set_cycle_through_parent_forward": (
        "query q:\n"
        + _set_let("a", "lhs", "b")
        + _let("b", "q")
        + "    from a\n    select:\n        id\n",
        [
            ("PIE-S2302", "Relation cycle detected: a -> b -> q -> a", 15, 5),
        ],
    ),
    # a reads b and c, both read a: the message follows one of the cycles.
    "cycles_sharing_a_member": (
        "query q:\n"
        + _set_let("a", "b", "c")
        + _let("b", "a")
        + _let("c", "a")
        + "    from a\n    select:\n        id\n",
        [
            ("PIE-S2302", "Relation cycle detected: a -> b -> a", 12, 9),
        ],
    ),
    "nested_17": (
        _chain(17),
        [
            (
                "PIE-S2360",
                "Let relation l16 is nested 17 query blocks deep; the limit is 16.",
                71,
                5,
            )
        ],
    ),
    "nested_18": (
        _chain(18),
        [
            (
                "PIE-S2360",
                f"Let relation l{depth - 1} is nested {depth} query blocks deep; "
                "the limit is 16.",
                7 + 4 * (depth - 1),
                5,
            )
            for depth in (17, 18)
        ],
    ),
}


@pytest.mark.parametrize("case", sorted(READ_ERRORS))
def test_let_read_errors(tmp_path: Path, case: str) -> None:
    body, expected = READ_ERRORS[case]
    assert _check(tmp_path, body) == (1, expected)


def test_an_unread_let_keeps_its_own_static_checks(tmp_path: Path) -> None:
    unread = _let("b", "lhs").replace("            id\n", "            missing\n")
    body = "query q:\n" + unread + "    from lhs\n    select:\n        id\n"
    code, diagnostics = _check(tmp_path, body)
    assert code == 1
    assert diagnostics[0] == ("PIE-S2359", "Let relation b is never read.", 7, 5)
    assert ("PIE-S2102", "Unknown field: missing", 10, 13) in diagnostics


def _readers(name: str) -> str:
    """Both readers name the unknown relation directly, without inventing an alias."""
    return (
        f"query s:\n    union all:\n        from lhs\n        from {name}\n"
        f"query t:\n    from lhs\n    inner join {name} on lhs.id == {name}.id\n"
        "    select:\n        id = lhs.id\n"
    )


def _unknown_join_input(name: str) -> list[tuple[str, str, int, int]]:
    """What t reports when `name` is unknown in t: the JOIN's input, at the
    JOIN, as in a single file, and none of the JOIN's unavailable reads."""
    return [("PIE-S2301", f"Unknown relation: {name}", 12, 5)]


def _unknown_to_readers(name: str) -> list[tuple[str, str, int, int]]:
    """What `_readers(name)` reports when `name` is unknown in s, besides
    `_unknown_join_input(name)`: no temporary admission text of the set."""
    return [("PIE-S2301", f"Unknown relation: {name}", 9, 9)]


# `query q` after the readers has an error about the name they read; each
# reader still meets an unknown relation, exactly as without q.
ELSEWHERE = {
    "unread": (
        "a",
        "query q:\n" + _let("a", "lhs") + "    from lhs\n    select:\n        id\n",
        [
            *_unknown_join_input("a"),
            ("PIE-S2359", "Let relation a is never read.", 16, 5),
            *_unknown_to_readers("a"),
        ],
    ),
    "cycle": (
        "a",
        "query q:\n"
        + _let("a", "b")
        + _let("b", "a")
        + "    from a\n    select:\n        id\n",
        [
            *_unknown_join_input("a"),
            ("PIE-S2302", "Relation cycle detected: a -> b -> a", 21, 9),
            *_unknown_to_readers("a"),
        ],
    ),
    "unknown_read_in_a_let": (
        "zz",
        "query q:\n" + _let("a", "zz") + "    from a\n    select:\n        id\n",
        [
            *_unknown_join_input("zz"),
            # q, which reads the failed let, adds no fallback.
            ("PIE-S2301", "Unknown relation: zz", 17, 9),
            *_unknown_to_readers("zz"),
        ],
    ),
}


@pytest.mark.parametrize("case", sorted(ELSEWHERE))
def test_a_let_error_stays_in_its_own_declaration(tmp_path: Path, case: str) -> None:
    name, declaration, expected = ELSEWHERE[case]
    assert _check(tmp_path, _readers(name) + declaration) == (1, expected)
    semantic = build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    assert semantic.module_catalogs is not None
    assert semantic.module_relation_resolutions is not None
    (catalog,) = semantic.module_catalogs.catalogs
    (environment,) = semantic.module_relation_resolutions.environments
    owners = {o.definition.name: o for o in catalog.occurrences}
    assert environment.find_scoped_issues(owners["q"], name)
    assert environment.find_scoped_issues(owners["s"], name) == ()
    # t's only issue of the name is its own unknown JOIN input.
    assert [
        issue.status for issue in environment.find_scoped_issues(owners["t"], name)
    ] == [ProjectModuleRelationResolutionIssueStatus.UNKNOWN_JOIN_INPUT]


def _imported(tmp_path: Path, imports: str, let: str):
    items = imports.rstrip("\n").replace("\n", ",\n")
    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "base.pietto").write_text(
        HEAD + "query q:\n    from lhs\n    select:\n        id\n"
        "export (\n    query q,\n    source lhs)\n",
        encoding="utf-8",
    )
    (tmp_path / "main.pietto").write_text(
        f'from "base.pietto" import (\n{items})\n'
        f"query r:\n    let {let}:\n        from lhs\n        select:\n"
        f"            id\n    from {let}\n    select:\n        id\n",
        encoding="utf-8",
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    return code, [
        (d["code"], d["location"]["path"], d["location"]["line"])
        for d in json.loads(out.getvalue())["diagnostics"]
    ]


# A let collides with a relation import binding whether or not it resolves.
@pytest.mark.parametrize(
    "imports,let,expected",
    (
        (
            "    source lhs\n    query q as other\n",
            "other",
            [("PIE-S2001", "main.pietto", 5)],
        ),
        (
            "    source lhs\n    query nothere\n",
            "nothere",
            [("PIE-S2705", "main.pietto", 3), ("PIE-S2001", "main.pietto", 5)],
        ),
        (
            "    source lhs\n    query q as x\n    source lhs as x\n",
            "x",
            [("PIE-S2706", "main.pietto", 3), ("PIE-S2001", "main.pietto", 6)],
        ),
    ),
    ids=("resolved", "unknown", "ambiguous"),
)
def test_let_names_collide_with_imported_relations(
    tmp_path: Path, imports: str, let: str, expected: list
) -> None:
    assert _imported(tmp_path, imports, let) == (1, expected)


def test_a_let_is_neither_exported_nor_imported(tmp_path: Path) -> None:
    owner = "query q:\n" + LET + "    from a\n    select:\n        id\n"
    assert _check(tmp_path / "export", owner + "export (\n    query a)\n") == (
        1,
        [("PIE-S2704", "Unknown export binding: query a", 15, 11)],
    )
    root = tmp_path / "import"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    (root / "base.pietto").write_text(HEAD + owner + "export (\n    query q)\n")
    (root / "main.pietto").write_text(
        'from "base.pietto" import (\n    query a)\nquery r:\n    from a\n'
        "    select:\n        id\n"
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    first = json.loads(out.getvalue())["diagnostics"][0]
    assert (first["code"], first["message"]) == (
        "PIE-S2705",
        'Unknown imported declaration: query a from "base.pietto"',
    )


def test_two_declarations_keep_their_same_named_lets_apart(tmp_path: Path) -> None:
    body = (
        "query q:\n" + LET + "    from a\n    select:\n        id\n"
        "table t:\n    let a:\n        from rhs\n        select:\n            id\n"
        "    from a\n    select:\n        id\n"
    )
    code, diagnostics = _check(tmp_path, body)
    assert (code, diagnostics) == (0, [])
    semantic = build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    assert semantic.module_catalogs is not None
    assert semantic.module_relation_resolutions is not None
    (catalog,) = semantic.module_catalogs.catalogs
    first, second = catalog.lets
    assert first.identity == second.identity
    assert first != second
    assert (first.declaration_position, second.declaration_position) == (3, 4)
    assert [o.definition.name for o in catalog.occurrences] == [
        "Row",
        "lhs",
        "rhs",
        "q",
        "t",
    ]
    assert all(o.let_position is None for o in catalog.occurrences)
    (environment,) = semantic.module_relation_resolutions.environments
    targets = {
        resolution.reference.owner.definition.name: resolution.target_symbol
        for resolution in environment.resolutions
        if resolution.reference.owner.let_position is None
        and resolution.reference.owner.definition.name in {"q", "t"}
    }
    assert targets["q"].target_occurrence is first
    assert targets["t"].target_occurrence is second
    assert environment.find_relation_name("a") == ()


@pytest.mark.parametrize("schema_version", (1, 2))
def test_lets_are_available_only_in_explicit_module_projects(
    tmp_path: Path, schema_version: int
) -> None:
    body = "query q:\n" + LET + "    from a\n    select:\n        id\n"
    config = probe.CONFIG.replace(
        "schema_version = 2", f"schema_version = {schema_version}"
    )
    code, diagnostics = _check(tmp_path, body, config=config)
    if schema_version == 2:
        assert (code, diagnostics) == (0, [])
        # Project JSON v2 keeps its structure: lets add no key and no record.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["check", "--project", str(tmp_path), "--format", "json"])
        document = json.loads(out.getvalue())
        assert tuple(document) == (
            "schema_version",
            "command",
            "mode",
            "ok",
            "project",
            "inputs",
            "diagnostics",
            "cli_errors",
            "result",
        )
        assert document["result"] == {
            "check": {"files_total": 1, "files_ok": 1, "files_with_errors": 0}
        }
    else:
        assert code == 1
        assert diagnostics == [
            (
                "PIE-S2345",
                "Relation let declarations are available only in "
                "EXPLICIT_MODULES projects (schema version 2).",
                7,
                5,
            )
        ]


# An existence read names a relation like FROM does: the same scope, the same
# single-read availability for lets, and no winner for an unknown name.
EXISTS_DIAGNOSTICS = {
    "read_once": (
        "query q:\n" + LET + "    from lhs\n    where exists a\n    select:\n"
        "        id\n",
        [],
    ),
    # A let may be read any number of times, before or after it is written.
    "from_and_exists": (
        "query q:\n" + LET + "    from a\n    where exists a\n    select:\n"
        "        id\n",
        [],
    ),
    "forward": (
        "query q:\n    let b:\n        from rhs\n        where exists a\n"
        "        select:\n            id\n" + LET + "    from b\n    select:\n"
        "        id\n",
        [],
    ),
    # A read that closes a cycle through lets is reported at the read.
    "self": (
        "query q:\n    let a:\n        from lhs\n        where exists a\n"
        "        select:\n            id\n    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> a", 9, 15)],
    ),
    "mutual": (
        "query q:\n    let b:\n        from rhs\n        where exists a\n"
        "        select:\n            id\n    let a:\n        from b\n"
        "        select:\n            id\n    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: b -> a -> b", 9, 15)],
    ),
    # An existence read counts as a read; only the let no block reads is unread.
    "unread_beside": (
        "query q:\n" + LET + "    let c:\n        from lhs\n        select:\n"
        "            id\n    from lhs\n    where exists a\n    select:\n"
        "        id\n",
        [("PIE-S2359", "Let relation c is never read.", 11, 5)],
    ),
    "unknown": (
        "query q:\n    from lhs\n    where exists nowhere\n    select:\n        id\n",
        [("PIE-S2301", "Unknown relation: nowhere", 8, 11)],
    ),
}


@pytest.mark.parametrize("case", sorted(EXISTS_DIAGNOSTICS))
def test_an_existence_read_is_a_scoped_relation_read(tmp_path: Path, case: str) -> None:
    body, expected = EXISTS_DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1 if expected else 0, expected)


# Phase70 S10: a let starting with capture lines reads the current row of one
# FROM or JOIN input of its declaration body, by qualified names only.
CAPTURE = (
    "query q:\n    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "    from lhs\n    where exists m\n    select:\n        a = lhs.id\n"
)
READ_ONLY_BY_EXISTS = (
    "Let m with capture lines can be read only once, by exists, scalar, in, "
    "collect or a join in the body of q."
)
BODY_SHAPE = (
    "Let m with capture lines may use only FROM, WHERE and an ungrouped SELECT."
)
# The body rule's message when ORDER BY or LIMIT is all that breaks it (D71.01).
ORDERED_BODY_SHAPE = (
    BODY_SHAPE + " A let read by `collect`, `scalar`, `in` or `not in`, or joined, "
    "may also end in ORDER BY and LIMIT."
)
# The body rule of a let joined LATERAL or read by scalar, IN or NOT IN.
LATERAL_BODY_SHAPE = (
    "Let m with capture lines may use only FROM, WHERE, an ungrouped SELECT, "
    "an ungrouped ORDER BY without captured fields and LIMIT."
)
CAPTURE_DIAGNOSTICS = {
    "accepted": (CAPTURE, []),
    # A captured field may be the left value of an `in` read of another let.
    "in_left_value": (
        "query q:\n    let keys:\n        from rhs\n        select:\n"
        "            key\n"
        + CAPTURE.removeprefix("query q:\n").replace(
            "rhs.key == lhs.key", "lhs.key in keys"
        ),
        [],
    ),
    # An outer field is read by its qualified name only: a bare name stays an
    # inner field even when only the outer input has it.
    "bare_name_stays_inner": (
        "query q:\n    let ids:\n        from rhs\n        select:\n"
        "            id\n    let m:\n        capture lhs\n        from ids\n"
        "        where id == lhs.id and key == lhs.key\n        select:\n"
        "            id\n    from lhs\n    where exists m\n    select:\n"
        "        a = lhs.id\n",
        [("PIE-S2102", "Unknown field: key", 14, 32)],
    ),
    "duplicate_and_unknown": (
        CAPTURE.replace(
            "        capture lhs\n",
            "        capture lhs\n        capture lhs\n        capture nope\n",
        ),
        [
            ("PIE-S2367", "Capture lhs is written more than once in let m.", 9, 9),
            (
                "PIE-S2366",
                "Capture nope does not name one FROM or JOIN row input of q.",
                10,
                9,
            ),
        ],
    ),
    "self_correlation": (
        CAPTURE.replace("capture lhs", "capture rhs").replace("lhs.key\n", "rhs.id\n"),
        [
            (
                "PIE-S2368",
                "Capture rhs is also an input of let m; rename that input through "
                "another let.",
                8,
                9,
            )
        ],
    ),
    "renamed_self_correlation": (
        "query q:\n    let inner:\n        from lhs\n        select:\n"
        "            id\n            key\n    let m:\n        capture lhs\n"
        "        from inner\n        where inner.key == lhs.key\n"
        "        select:\n            id\n    from lhs\n    where exists m\n"
        "    select:\n        a = lhs.id\n",
        [],
    ),
    "unknown_field": (
        CAPTURE.replace("lhs.key\n", "lhs.nope\n"),
        [("PIE-S2369", "Captured input lhs has no row field nope.", 10, 26)],
    ),
    # A chain's inner operand is read by both comparisons, each its own copy.
    "chain_operand": (CAPTURE.replace("rhs.key == lhs.key", "0 < lhs.id < rhs.id"), []),
    "chain_operand_unknown_field": (
        CAPTURE.replace("rhs.key == lhs.key", "0 < lhs.nope < rhs.id"),
        [("PIE-S2369", "Captured input lhs has no row field nope.", 10, 19)],
    ),
    # A second read in a chain's inner operand, which both comparisons read,
    # is refused once.
    "chain_operand_second_read": (
        CAPTURE.replace(
            "where exists m", "where exists m and False == exists m == True"
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 14, 33)],
    ),
    # The binder of an `any` test is no row input, and `any` is not available
    # in a query whose let has capture lines.
    "semi_join_target": (
        CAPTURE.replace("capture lhs", "capture r")
        .replace("lhs.key\n", "r.key\n")
        .replace(
            "    from lhs\n    where",
            (
                "    from lhs\n"
                "    let r = rhs\n"
                "    where any(lhs.id == r.id for r in r) and"
            ),
        ),
        [
            (
                "PIE-S2366",
                "Capture r does not name one FROM or JOIN row input of q.",
                8,
                9,
            ),
            ("PIE-S2334", "ANY is not supported in this context", 15, 11),
        ],
    ),
    "set_body_declaration": (
        "query q:\n    let m:\n        capture lhs\n        from rhs\n"
        "        select:\n            id\n    union all:\n        from m\n"
        "        from lhs\n",
        [
            (
                "PIE-S2366",
                "Capture lhs does not name one FROM or JOIN row input of q.",
                8,
                9,
            ),
            ("PIE-S2370", READ_ONLY_BY_EXISTS, 13, 9),
        ],
    ),
    "body_shape": (
        CAPTURE.replace(
            "            id\n    from lhs",
            "            id\n        order by:\n            id\n        limit 1\n"
            "    from lhs",
        ),
        [("PIE-S2370", ORDERED_BODY_SHAPE, 7, 5)],
    ),
    "where_aggregate": (
        CAPTURE.replace("where rhs.key == lhs.key", "where count() > lhs.id"),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # Capture refusals take one source order with the file's pre-admission
    # diagnostics (here the header of a set-operation body); the query header
    # checks follow them.
    "pre_admission_order": (
        "query p(x: Foo):\n    from lhs\n    where id > x\n    select:\n"
        "        id\nquery q:\n    let m:\n        capture nope\n"
        "        from rhs\n        select:\n            id\n    from lhs\n"
        "    where exists m\n    select:\n        a = id\n"
        "query s(y: Int):\n    union all:\n        from lhs\n"
        "        from rhs\nquery r:\n    let m:\n        capture lhs\n"
        "        from rhs\n        select:\n            id\n    from m\n"
        "    select:\n        a = id\n",
        [
            (
                "PIE-S2366",
                "Capture nope does not name one FROM or JOIN row input of q.",
                13,
                9,
            ),
            (
                "PIE-S2346",
                "Query header parameters are available only in EXPLICIT_MODULES "
                "projects (schema version 2), on a query that reads a relation "
                "with FROM and has no relation let reading a table function.",
                21,
                9,
            ),
            (
                "PIE-S2366",
                "Capture lhs does not name one FROM or JOIN row input of r.",
                27,
                9,
            ),
            ("PIE-S2370", READ_ONLY_BY_EXISTS.replace("of q.", "of r."), 31, 5),
            (
                "PIE-S2353",
                "Query parameter type must be Bool, Int, Float or Text.",
                6,
                9,
            ),
        ],
    ),
    "join_body": (
        CAPTURE.replace(
            "        from rhs\n        where",
            (
                "        from rhs\n"
                "        let y = rhs\n"
                "        inner join y on rhs.id == y.id\n"
                "        where"
            ),
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    "row_let_body": (
        CAPTURE.replace(
            "        from rhs\n        where",
            ("        from rhs\n        let k = key\n        where"),
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # A typed VALUES body is admitted (S06), but never as a correlated body.
    "values_body": (
        "query q:\n    let m:\n        capture lhs\n"
        "        values(id: Int):\n            1\n"
        "    from lhs\n    where exists m\n    select:\n        a = lhs.id\n",
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # A let with capture lines reads the entry query's header like any other
    # let of it (Phase70 S11); the read renders inside the EXISTS subquery.
    "header_parameter": (
        CAPTURE.replace("query q:", "query q(cut: Int):").replace(
            "rhs.key == lhs.key", "rhs.key == lhs.key and rhs.id > cut"
        ),
        [],
    ),
    "distinct_body": (
        CAPTURE.replace(
            "        select:\n            id\n    from lhs",
            "        select distinct:\n            id\n    from lhs",
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # Only FROM and JOIN row fields are captured: never an outer row let value
    # or SELECT output.
    "outer_row_let_value": (
        CAPTURE.replace("lhs.key\n", "lhs.bumped\n").replace(
            "    from lhs\n    where exists m\n",
            ("    from lhs\n    let bumped = id + 1\n    where exists m\n"),
        ),
        [("PIE-S2369", "Captured input lhs has no row field bumped.", 10, 26)],
    ),
    "outer_select_output": (
        CAPTURE.replace("lhs.key\n", "lhs.a\n"),
        [("PIE-S2369", "Captured input lhs has no row field a.", 10, 26)],
    ),
    "grouped_body": (
        CAPTURE.replace(
            "        select:\n            id\n    from lhs",
            "        group by:\n            id\n        select:\n            id\n"
            "    from lhs",
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    "read_by_from": (
        CAPTURE.replace("    from lhs\n    where exists m\n", "    from m\n"),
        [
            (
                "PIE-S2366",
                "Capture lhs does not name one FROM or JOIN row input of q.",
                8,
                9,
            ),
            ("PIE-S2370", READ_ONLY_BY_EXISTS, 13, 5),
        ],
    ),
    # Phase70 S12: a JOIN of the declaration body reads the let LATERAL; the
    # kinds and capture positions it takes are below (LATERAL_DIAGNOSTICS).
    "read_by_join": (
        CAPTURE.replace(
            "    where exists m\n",
            ("    let x = m\n    inner join x on lhs.id == x.id\n"),
        ),
        [],
    ),
    # Nested correlation: no let reads a let with capture lines.
    "read_by_another_let": (
        CAPTURE.replace(
            "    from lhs\n    where exists m\n",
            "    let other:\n        from rhs\n        where exists m\n"
            "        select:\n            id\n    from lhs\n    where exists other\n",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 15, 15)],
    ),
    # Other lets may be read any number of times (S05); a let with capture
    # lines keeps exactly one read, the first in source order.
    "read_twice": (
        CAPTURE.replace("where exists m\n", "where exists m or exists m\n"),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 14, 23)],
    ),
    "read_in_where_and_select": (
        CAPTURE.replace(
            "        a = lhs.id\n", "        a = lhs.id\n        e = exists m\n"
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 17, 13)],
    ),
    "read_in_order_by": (
        CAPTURE.replace("    where exists m\n", "")
        + "    order by:\n        exists m\n",
        [
            (
                "PIE-S2349",
                "EXISTS relation reference is available only in WHERE and in the "
                "SELECT of an ungrouped query, not in ORDER BY.",
                17,
                9,
            )
        ],
    ),
    "select_read": (
        CAPTURE.replace("    where exists m\n", "").replace(
            "        a = lhs.id\n", "        a = lhs.id\n        e = exists m\n"
        ),
        [],
    ),
    # Captured field refusals keep source order with the other field errors.
    "unknown_fields_in_source_order": (
        CAPTURE.replace(
            "rhs.key == lhs.key", "rhs.zz == lhs.nope and lhs.a1 == lhs.a2"
        ),
        [
            ("PIE-S2102", "Unknown field: rhs.zz", 10, 15),
            ("PIE-S2369", "Captured input lhs has no row field nope.", 10, 25),
            ("PIE-S2369", "Captured input lhs has no row field a1.", 10, 38),
            ("PIE-S2369", "Captured input lhs has no row field a2.", 10, 48),
        ],
    ),
    # The columns of a set, an authored JOIN or a relation reading one are not
    # known before completion: each field read of such a captured input is
    # refused, whatever field it names; a capture whose fields are not read is
    # accepted.
    "set_let_input": (
        "query q:\n    let codes:\n        union all:\n            from lhs\n"
        "            from rhs\n"
        + CAPTURE.removeprefix("query q:\n")
        .replace("lhs", "codes")
        .replace("rhs.key == codes.key", "codes.nope == rhs.key and codes.id > 1"),
        [
            (
                "PIE-S2369",
                "Captured field codes.nope is not yet available: the columns of "
                "codes are not known before completion.",
                14,
                15,
            ),
            (
                "PIE-S2369",
                "Captured field codes.id is not yet available: the columns of "
                "codes are not known before completion.",
                14,
                41,
            ),
        ],
    ),
    "values_let_input": (
        (
            "query q:\n"
            "    let codes:\n"
            "        values(id: Int, key: Int | None):\n"
            "            1, 2\n"
        )
        + CAPTURE.removeprefix("query q:\n").replace("lhs", "codes"),
        [
            (
                "PIE-S2369",
                "Captured field codes.key is not yet available: the columns of "
                "codes are not known before completion.",
                13,
                26,
            ),
        ],
    ),
    "erroneous_table_input": (
        "table e:\n    from lhs\n    select:\n        id\n        key = nosuch\n"
        + CAPTURE.replace("lhs", "e"),
        [
            # The relation facts restate it; it is reported once, and `q`,
            # which reads `e`, adds no fallback.
            ("PIE-S2102", "Unknown field: nosuch", 10, 15),
            (
                "PIE-S2369",
                "Captured field e.key is not yet available: the columns of e are "
                "not known before completion.",
                15,
                26,
            ),
        ],
    ),
    # A grouped declaration body reads the let in its WHERE, before grouping.
    "grouped_body_where_read": (
        CAPTURE.replace(
            "    select:\n        a = lhs.id\n",
            "    group by:\n        id\n    select:\n        id\n        n = count()\n",
        ),
        [],
    ),
    "set_let_input_unread": (
        "query q:\n    let codes:\n        union all:\n            from lhs\n"
        "            from rhs\n"
        + CAPTURE.removeprefix("query q:\n")
        .replace("lhs", "codes")
        .replace("rhs.key == codes.key", "rhs.key > 1"),
        [],
    ),
    "join_table_input": (
        (
            "table pairs:\n"
            "    from lhs\n"
            "    let r = rhs\n"
            "    inner join r on lhs.id == r.id\n"
            "    select:\n"
            "        id = lhs.id\n"
            "        key = r.key\n"
        )
        + CAPTURE.replace("lhs", "pairs"),
        [
            (
                "PIE-S2369",
                "Captured field pairs.key is not yet available: the columns of "
                "pairs are not known before completion.",
                17,
                26,
            ),
        ],
    ),
    "table_over_set_input": (
        "table codes:\n    union all:\n        from lhs\n        from rhs\n"
        "table keyed:\n    from codes\n    select:\n        id\n        key\n"
        + CAPTURE.replace("lhs", "keyed"),
        [
            (
                "PIE-S2369",
                "Captured field keyed.key is not yet available: the columns of "
                "keyed are not known before completion.",
                19,
                26,
            ),
        ],
    ),
    "lateral_join_table_input": (
        (
            "table pairs:\n"
            "    from lhs\n"
            "    let r = rhs\n"
            "    inner join r on lhs.id == r.id\n"
            "    select:\n"
            "        id = lhs.id\n"
            "        key = r.key\n"
        )
        + CAPTURE.replace("lhs", "pairs").replace(
            "    where exists m\n",
            ("    let x = m\n    cross join x\n"),
        ),
        [
            (
                "PIE-S2369",
                "Captured field pairs.key is not yet available: the columns of "
                "pairs are not known before completion.",
                17,
                26,
            ),
            # A JOIN of a let with an error leaves its body incomplete, as for
            # any let JOIN input.
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                13,
                1,
            ),
        ],
    ),
}
# The let's own FROM relation may have columns known only after completion (a
# typed VALUES body, a set, an authored JOIN, read through a let or a module
# relation): its WHERE and SELECT are typed then, captured fields included,
# and report their errors in source order.
OWN_FROM_INPUTS = {
    "values": "query q:\n    let s:\n        values(id: Int):\n"
    "            1\n            2\n",
    "set": "query q:\n    let s:\n        union all:\n            from lhs\n"
    "            from rhs\n",
    "join": (
        "query q:\n"
        "    let s:\n"
        "        from lhs\n"
        "        let r = rhs\n"
        "        inner join r on r.id == lhs.id\n"
        "        select:\n"
        "            id = r.id\n"
    ),
    "table": "table s:\n    values(id: Int):\n        1\nquery q:\n",
}
OWN_FROM = (
    "    let m:\n        capture lhs\n        from s\n"
    "        where s.id <= lhs.id\n        select:\n            id\n"
    "            k = lhs.key\n    from lhs\n    where exists m\n    select:\n"
    "        a = lhs.id\n"
)
for _name, _input in OWN_FROM_INPUTS.items():
    _line = _input.count("\n") + 9
    CAPTURE_DIAGNOSTICS["own_from_" + _name] = (_input + OWN_FROM, [])
    CAPTURE_DIAGNOSTICS["own_from_" + _name + "_errors"] = (
        _input + OWN_FROM.replace("s.id <= lhs.id", "s.zz <= lhs.id and lhs.nope > 1"),
        [
            ("PIE-S2102", "Unknown field: s.zz", _line, 15),
            ("PIE-S2369", "Captured input lhs has no row field nope.", _line, 34),
        ],
    )


# Phase70 S15: a let with capture lines reads a table function through another
# let; a table function's columns are known only after completion, so a field
# read of a captured input over one is refused; its binding is no row input,
# while the JOINs of its body are.
SERIES_LET = (
    "    let s:\n        from generate_series(1, 3, 1) as n\n        select:\n"
    "            id = n\n            key = n\n"
)
SERIES_FROM = "    from generate_series(1, 3, 1) as n\n"
CAPTURE_DIAGNOSTICS |= {
    "own_from_series": ("query q:\n" + SERIES_LET + OWN_FROM, []),
    "series_input": (
        "query q:\n" + SERIES_LET + "    let m:\n        capture s\n        from rhs\n"
        "        where rhs.key == s.key and rhs.id > s.id\n        select:\n"
        "            id\n    from s\n    where exists m\n    select:\n        id\n",
        [
            (
                "PIE-S2369",
                "Captured field s.key is not yet available: the columns of s are "
                "not known before completion.",
                15,
                26,
            ),
            (
                "PIE-S2369",
                "Captured field s.id is not yet available: the columns of s are "
                "not known before completion.",
                15,
                45,
            ),
        ],
    ),
    "series_join_binding": (
        CAPTURE.replace("capture lhs", "capture l")
        .replace("rhs.key == lhs.key", "rhs.id == l.id")
        .replace(
            "    from lhs\n",
            SERIES_FROM + ("    let l = lhs\n    inner join l on n.n == l.id\n"),
        )
        .replace("a = lhs.id", "a = n.n"),
        [],
    ),
    "series_binding": (
        CAPTURE.replace("capture lhs", "capture n")
        .replace("rhs.key == lhs.key", "rhs.id == n.n")
        .replace("    from lhs\n", SERIES_FROM)
        .replace("a = lhs.id", "a = n.n"),
        [
            (
                "PIE-S2366",
                "Capture n does not name one FROM or JOIN row input of q.",
                8,
                9,
            )
        ],
    ),
    "series_capture_body": (
        CAPTURE.replace("        from rhs\n", "    " + SERIES_FROM)
        .replace("rhs.key == lhs.key", "n.n <= lhs.id")
        .replace("            id\n", "            n\n", 1),
        [
            (
                "PIE-S2370",
                "Let m with capture lines reads a table function; read it through "
                "another let.",
                7,
                5,
            )
        ],
    ),
}


@pytest.mark.parametrize("case", sorted(CAPTURE_DIAGNOSTICS))
def test_capture_lines_bind_outer_row_inputs_by_qualified_name(
    tmp_path: Path, case: str
) -> None:
    body, expected = CAPTURE_DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1 if expected else 0, expected)


# Phase70 S14: `scalar m.c`, `v in m` and `v not in m` read a let with capture
# lines like `exists m`: once, in WHERE or the SELECT of an ungrouped
# declaration body. The scalar (S07) and IN (S09) position, column and width
# rules are unchanged.
SCALAR_POSITION = (
    "Scalar relation read is available only in WHERE and in the SELECT of an "
    "ungrouped query, not in {}."
)
IN_POSITION = (
    "IN relation reference is available only in WHERE and in the SELECT of an "
    "ungrouped query, not in {}."
)
UNAVAILABLE = (
    "PIE-S2333",
    "Project relation semantic completion is unavailable: q",
    6,
    1,
)
GROUPED = "    group by:\n        key\n    select:\n        key\n        n = count()\n"


def _ordered(
    read: str, tail: str = "        order by:\n            id desc\n        limit 1\n"
) -> str:
    """CAPTURE whose let ends in ``tail`` and whose EXISTS read is ``read``."""
    return CAPTURE.replace(
        "            id\n    from lhs", "            id\n" + tail + "    from lhs"
    ).replace("exists m", read)


CORRELATED_READS = {
    "where_in": (CAPTURE.replace("exists m", "lhs.id in m"), []),
    "where_not_in": (CAPTURE.replace("exists m", "lhs.key not in m"), []),
    "where_scalar": (CAPTURE.replace("exists m", "lhs.id == scalar m.id"), []),
    "select_scalar": (
        CAPTURE.replace("    where exists m\n", "") + "        v = scalar m.id\n",
        [],
    ),
    "select_not_in": (
        CAPTURE.replace("    where exists m\n", "") + "        f = lhs.id not in m\n",
        [],
    ),
    "grouped_where_in": (
        CAPTURE.replace("exists m", "lhs.id in m").split("    select:\n        a")[0]
        + GROUPED,
        [],
    ),
    "grouped_select_scalar": (
        CAPTURE.replace("    where exists m\n", "").split("    select:\n        a")[0]
        + GROUPED
        + "        v = scalar m.id\n",
        # The read's own error stops q: no fallback beside it.
        [
            (
                "PIE-S2348",
                SCALAR_POSITION.format("the SELECT of a grouped query"),
                19,
                13,
            )
        ],
    ),
    "row_let_scalar": (
        CAPTURE.replace("    where exists m\n", "    let v = scalar m.id\n"),
        [("PIE-S2348", SCALAR_POSITION.format("a row let"), 14, 13)],
    ),
    "named_window_scalar": (
        CAPTURE.replace("    where exists m\n", "").replace(
            "    select:\n        a = lhs.id\n",
            (
                "    let ordered = window(order by scalar m.id)\n"
                "    select:\n"
                "        id\n"
                "        rn = row_number() window ordered\n"
            ),
        ),
        [
            ("PIE-S2348", SCALAR_POSITION.format("a window"), 14, 35),
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
                17,
                14,
            ),
        ],
    ),
    "window_in": (
        CAPTURE.replace("    where exists m\n", "").replace(
            "        a = lhs.id\n",
            ("        id\n        rn = row_number() window(order by lhs.id in m)\n"),
        ),
        [
            ("PIE-S2350", IN_POSITION.format("a window"), 16, 43),
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
                16,
                14,
            ),
        ],
    ),
    "order_by_in": (
        CAPTURE.replace("    where exists m\n", "")
        + "    order by:\n        lhs.id in m\n",
        [("PIE-S2350", IN_POSITION.format("ORDER BY"), 17, 9)],
    ),
    "join_on_in": (
        CAPTURE.replace(
            "    where exists m\n",
            ("    let r = rhs\n    inner join r on lhs.id in m\n"),
        ),
        [("PIE-S2350", IN_POSITION.format("JOIN ON"), 15, 21)],
    ),
    "two_columns": (
        CAPTURE.replace(
            "            id\n", "            id\n            key\n"
        ).replace("exists m", "lhs.id in m"),
        [
            (
                "PIE-S2105",
                "Invalid operands for operator in: expected a relation with one "
                "output column",
                15,
                11,
            )
        ],
    ),
    "unknown_column": (
        CAPTURE.replace("exists m", "lhs.id == scalar m.nope"),
        [("PIE-S2102", "Unknown field: m.nope", 14, 21)],
    ),
    # Read once: a second read in the body is refused like any later read.
    "scalar_and_in": (
        CAPTURE.replace("exists m", "lhs.id in m") + "        v = scalar m.id\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 17, 13)],
    ),
    "not_in_and_in": (
        CAPTURE.replace("exists m", "lhs.key not in m") + "        f = lhs.id in m\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 17, 13)],
    ),
    # Nested correlation: no other let reads it, by scalar or IN either.
    "scalar_in_another_let": (
        CAPTURE.replace(
            "    from lhs\n    where exists m\n",
            "    let other:\n        from rhs\n        where rhs.id == scalar m.id\n"
            "        select:\n            id\n    from lhs\n    where exists other\n",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 15, 25)],
    ),
    # Owner decision 2026-10-15 (D70.05): a scalar, IN or NOT IN read takes
    # the let's ORDER BY and LIMIT, a top-k per outer row whose ORDER BY reads
    # no captured field and no aggregate; an EXISTS read never does. The
    # program is valid on both targets (MySQL emission refuses the read).
    "ordered_read_by_in": (_ordered("lhs.id in m"), []),
    "ordered_read_by_scalar": (
        _ordered("lhs.id == scalar m.id", "        limit 1\n"),
        [],
    ),
    # ORDER BY alone, by a field the let does not select.
    "ordered_read_by_not_in": (
        _ordered("lhs.key not in m", "        order by:\n            key\n"),
        [],
    ),
    "ordered_limit_maximum": (
        _ordered("lhs.id in m", f"        limit {2**63 - 1}\n"),
        [],
    ),
    "ordered_limit_over_maximum": (
        _ordered("lhs.id in m", f"        limit {2**63}\n"),
        [
            (
                "PIE-S2307",
                "Limit must be a static integer from 0 to 9223372036854775807",
                13,
                15,
            )
        ],
    ),
    "ordered_read_by_exists": (
        _ordered("exists m"),
        [("PIE-S2370", ORDERED_BODY_SHAPE, 7, 5)],
    ),
    # D71.01: a `collect` read takes the ORDER BY and LIMIT too, as the
    # let's one read (S04), while every other read keeps its rules.
    "ordered_read_by_collect": (
        _ordered("exists m").replace("    where exists m\n", "")
        + "        rows_of_m = collect m\n",
        [],
    ),
    # A Collect is the let's one read too (S04): a second read is refused
    # before semantic analysis.
    "ordered_read_by_exists_and_collect": (
        _ordered("exists m") + "        rows_of_m = collect m\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 21)],
    ),
    "ordered_collected_twice": (
        _ordered("exists m").replace("    where exists m\n", "")
        + "        x = collect m\n        y = collect m\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 13)],
    ),
    # Source order decides: a Collect written first makes `exists` the second.
    "ordered_collect_then_exists": (
        _ordered("exists m").replace("    where exists m\n", "")
        + "        x = collect m\n        e = exists m\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 13)],
    ),
    "ordered_read_by_collect_in_another_let": (
        _ordered("exists m").replace(
            "    from lhs\n    where exists m\n",
            "    let other:\n        from rhs\n        select:\n            id\n"
            "            rows_of_m = collect m\n    from lhs\n    where exists other\n",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 25)],
    ),
    "ordered_captured_key_read_by_collect": (
        _ordered(
            "exists m", "        order by:\n            lhs.key\n        limit 1\n"
        ).replace("    where exists m\n", "")
        + "        rows_of_m = collect m\n",
        [("PIE-S2370", LATERAL_BODY_SHAPE, 7, 5)],
    ),
    "ordered_captured_key": (
        _ordered(
            "lhs.id in m", "        order by:\n            lhs.key\n        limit 1\n"
        ),
        [("PIE-S2370", LATERAL_BODY_SHAPE, 7, 5)],
    ),
    "ordered_aggregate_key": (
        _ordered("lhs.id == scalar m.id", "        order by:\n            count()\n"),
        [("PIE-S2370", LATERAL_BODY_SHAPE, 7, 5)],
    ),
    "ordered_read_twice": (
        _ordered("lhs.id in m") + "        v = scalar m.id\n",
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 13)],
    ),
    # A read in another let neither reads the let nor gives it ORDER BY.
    "ordered_read_in_another_let": (
        _ordered("exists m").replace(
            "    from lhs\n    where exists m\n",
            "    let other:\n        from rhs\n        where rhs.id == scalar m.id\n"
            "        select:\n            id\n    from lhs\n    where exists other\n",
        ),
        [
            ("PIE-S2370", ORDERED_BODY_SHAPE, 7, 5),
            ("PIE-S2370", READ_ONLY_BY_EXISTS, 18, 25),
        ],
    ),
    # A let over a relation whose columns are known only after completion has
    # such columns too: `scalar` cannot read it yet, `in` and `not in` can.
    "own_from_values_scalar": (
        OWN_FROM_INPUTS["values"]
        + OWN_FROM.replace("    where exists m\n", "")
        + "        v = scalar m.id\n",
        [
            (
                "PIE-S2348",
                "Scalar relation read m.id is not yet available: the columns of m "
                "are not known before completion.",
                21,
                13,
            )
        ],
    ),
    "own_from_set_not_in": (
        OWN_FROM_INPUTS["set"]
        + OWN_FROM.replace("            k = lhs.key\n", "").replace(
            "exists m", "lhs.id not in m"
        ),
        [],
    ),
}


@pytest.mark.parametrize("case", sorted(CORRELATED_READS))
def test_scalar_and_in_read_a_capturing_let_in_its_declaration_body(
    tmp_path: Path, case: str
) -> None:
    body, expected = CORRELATED_READS[case]
    assert _check(tmp_path, body) == (1 if expected else 0, expected)


TWO_READS = (
    "query q:\n    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "    let n:\n        capture lhs\n        from rhs\n"
    "        where rhs.id == lhs.id\n        select:\n            id\n"
    "    from lhs\n    where lhs.key not in m\n    select:\n        a = lhs.id\n"
    "        v = scalar n.id\n"
)
TWO_READS_GATED = [
    ("PIE-S2345", 7, 5),
    ("PIE-S2351", 8, 9),
    ("PIE-S2345", 13, 5),
    ("PIE-S2351", 14, 9),
    ("PIE-S2350", 20, 11),
    ("PIE-S2348", 23, 13),
]


# Both lets ending in ORDER BY and LIMIT (owner decision 2026-10-15): the
# gated modes keep their codes, each moved down by the tails above it.
ORDER_TAIL = "        order by:\n            id desc\n        limit 1\n"
TWO_ORDERED_READS = TWO_READS.replace(
    "            id\n    let n:", "            id\n" + ORDER_TAIL + "    let n:"
).replace(
    "            id\n    from lhs", "            id\n" + ORDER_TAIL + "    from lhs"
)
TWO_ORDERED_READS_GATED = [
    ("PIE-S2345", 7, 5),
    ("PIE-S2351", 8, 9),
    ("PIE-S2345", 16, 5),
    ("PIE-S2351", 17, 9),
    ("PIE-S2350", 26, 11),
    ("PIE-S2348", 29, 13),
]


@pytest.mark.parametrize("ordered", (False, True))
@pytest.mark.parametrize("mode", ("explicit_modules", "legacy_flat", "single_file"))
def test_correlated_scalar_and_in_reads_are_explicit_module_forms(
    tmp_path: Path, mode: str, ordered: bool
) -> None:
    body, gated = (
        (TWO_ORDERED_READS, TWO_ORDERED_READS_GATED)
        if ordered
        else (TWO_READS, TWO_READS_GATED)
    )
    if mode == "single_file":
        path = tmp_path / "single.pietto"
        path.write_text(HEAD + body, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["check", str(path), "--format", "json"])
        diagnostics = [
            (d["code"], d["location"]["line"], d["location"]["column"])
            for d in json.loads(out.getvalue())["diagnostics"]
        ]
        assert (code, diagnostics) == (1, gated)
        return
    version = 2 if mode == "explicit_modules" else 1
    code, diagnostics = _check(
        tmp_path,
        body,
        config=probe.CONFIG.replace(
            "schema_version = 2", f"schema_version = {version}"
        ),
    )
    if version == 2:
        assert (code, diagnostics) == (0, [])
    else:
        assert (code, [(c, line, column) for c, _, line, column in diagnostics]) == (
            1,
            gated,
        )


@pytest.mark.parametrize("schema_version", (1, 2))
def test_capture_lines_are_available_only_in_explicit_module_projects(
    tmp_path: Path, schema_version: int
) -> None:
    config = probe.CONFIG.replace(
        "schema_version = 2", f"schema_version = {schema_version}"
    )
    code, diagnostics = _check(tmp_path, CAPTURE, config=config)
    if schema_version == 2:
        assert (code, diagnostics) == (0, [])
        return
    assert (code, diagnostics) == (
        1,
        [
            (
                "PIE-S2345",
                "Relation let declarations are available only in "
                "EXPLICIT_MODULES projects (schema version 2).",
                7,
                5,
            ),
            (
                "PIE-S2351",
                "Capture lines are available only in EXPLICIT_MODULES projects "
                "(schema version 2).",
                8,
                9,
            ),
            (
                "PIE-S2349",
                "EXISTS relation reads are available only inside a FROM-based "
                "relation body in EXPLICIT_MODULES projects (schema version 2).",
                14,
                11,
            ),
        ],
    )


def test_a_single_file_keeps_capture_lines_gated(tmp_path: Path) -> None:
    path = tmp_path / "single.pietto"
    path.write_text(HEAD + CAPTURE, encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", str(path), "--format", "json"])
    assert code == 1
    assert [
        (d["code"], d["location"]["line"], d["location"]["column"])
        for d in json.loads(out.getvalue())["diagnostics"]
    ] == [("PIE-S2345", 7, 5), ("PIE-S2351", 8, 9), ("PIE-S2349", 14, 11)]


def _capture_facts(tmp_path: Path, body: str):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "main.pietto").write_text(HEAD + body)
    semantic = build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    assert semantic.module_semantic_facts is not None
    (environment,) = semantic.module_semantic_facts.environments
    return {fact.owner.definition.name: fact for fact in environment.relation_facts}


def _typed(values: Any) -> dict[Any, Any]:
    """Captured field types; every value is a known type in these cases."""
    return dict(values)


def test_a_captured_field_keeps_the_outer_type_and_join_null_extension(
    tmp_path: Path,
) -> None:
    body = (
        "query q:\n"
        "    let m:\n"
        "        capture lhs\n"
        "        capture r\n"
        "        from rhs\n"
        "        where rhs.id == lhs.id and rhs.id == r.id\n"
        "        select:\n"
        "            id\n"
        "    from lhs\n"
        "    let r = rhs\n"
        "    left join r on lhs.id == r.id\n"
        "    where exists m\n"
        "    select:\n"
        "        a = lhs.id\n"
    )
    assert _check(tmp_path / "check", body) == (0, [])
    facts = _capture_facts(tmp_path / "facts", body)["m"]
    types = {
        (read.capture, read.field): (
            value.resolved_type.name,
            value.nullability.value,
        )
        for read, value in _typed(facts.captured_value_types).items()
    }
    # lhs.id keeps NOT NULL; r.id may be null-extended by the LEFT JOIN.
    assert types == {
        ("lhs", "id"): ("Int", "non_null"),
        ("r", "id"): ("Int", "nullable"),
    }
    assert facts.where_fact is not None
    assert {
        type(node).__name__ for node in facts.where_fact.expression_value_types
    } >= {"CapturedFieldExpr"}
    # An INNER JOIN never null-extends, and its ON condition does not narrow a
    # nullable captured field.
    inner = (
        body.replace("left join", "inner join")
        .replace("on lhs.id == r.id", "on lhs.id == r.id and r.key is not None")
        .replace("rhs.id == r.id\n", "rhs.id == r.id and rhs.key == r.key\n")
    )
    assert _check(tmp_path / "inner-check", inner) == (0, [])
    facts = _capture_facts(tmp_path / "inner-facts", inner)["m"]
    assert {
        (read.capture, read.field): value.nullability.value
        for read, value in _typed(facts.captured_value_types).items()
    } == {("lhs", "id"): "non_null", ("r", "id"): "non_null", ("r", "key"): "nullable"}


# Phase70 S12: a JOIN of the declaration body that names a let with capture
# lines reads it LATERAL (D70.03): each capture line names a row input to the
# left of that JOIN and only kinds that keep every left row may take it.
LATERAL = (
    "query q:\n    let m:\n        capture lhs\n        from rhs\n"
    "        where rhs.key == lhs.key\n        select:\n            id\n"
    "    from lhs\n    let x = m\n    {kind} join x{on}\n"
    "    select:\n        a = lhs.id\n"
)
JOIN_KIND = "Let m with capture lines can be joined only by cross, inner or left join."


def _lateral(kind: str, on: str = "        on True\n") -> str:
    return LATERAL.format(kind=kind, on="" if kind == "cross" else " " + on.strip())


def _top_k(
    kind: str,
    *,
    on: str = "        on True\n",
    order: str = "        order by:\n            id desc\n",
    limit: str = "        limit 2\n",
) -> str:
    """The LATERAL let of ``_lateral`` ending in ORDER BY and LIMIT."""
    return _lateral(kind, on).replace(
        "            id\n    from lhs\n",
        "            id\n" + order + limit + "    from lhs\n",
    )


LATERAL_DIAGNOSTICS = {
    "cross": (_lateral("cross"), []),
    "inner_on_true": (_lateral("inner"), []),
    "inner_on_condition": (_lateral("inner", "        on x.id > lhs.id\n"), []),
    # Phase70 S13: LEFT keeps every left row and null-extends the let's.
    "left": (_lateral("left"), []),
    "left_on_condition": (_lateral("left", "        on x.id > lhs.id\n"), []),
    "right": (_lateral("right"), [("PIE-S2372", JOIN_KIND, 15, 5)]),
    "full": (_lateral("full"), [("PIE-S2372", JOIN_KIND, 15, 5)]),
    # An `any` test over the let is no JOIN of it and is not available yet.
    "semi": (
        _lateral("cross").replace(
            "    cross join x\n", "    where any(True for x in x)\n"
        ),
        [("PIE-S2334", "ANY is not supported in this context", 15, 11)],
    ),
    "anti": (
        _lateral("cross").replace(
            "    cross join x\n", "    where not any(True for x in x)\n"
        ),
        [("PIE-S2334", "ANY is not supported in this context", 15, 15)],
    ),
    # The let's own JOIN binding and a later JOIN's binding are not left of it.
    "own_binding": (
        _lateral("cross")
        .replace("capture lhs", "capture x")
        .replace("lhs.key\n", "x.id\n"),
        [
            (
                "PIE-S2371",
                "Capture x of let m is not a row input to the left of its join in q.",
                8,
                9,
            )
        ],
    ),
    "later_binding": (
        _lateral("cross")
        .replace("capture lhs", "capture lhs\n        capture z")
        .replace("lhs.key\n", "lhs.key and rhs.id == z.id\n")
        .replace(
            "    select:\n        a",
            ("    let z = rhs\n    cross join z\n    select:\n        a"),
        ),
        [
            (
                "PIE-S2371",
                "Capture z of let m is not a row input to the left of its join in q.",
                9,
                9,
            )
        ],
    ),
    # Like an exists read, a JOIN is the let's one read (Phase70 S05 reuse
    # does not apply): a later exists or JOIN of it is refused.
    "joined_and_exists": (
        _lateral("cross").replace(
            "    select:\n        a", "    where exists m\n    select:\n        a"
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 16, 11)],
    ),
    "joined_twice": (
        _lateral("cross").replace(
            "    select:\n        a",
            ("    let y = m\n    cross join y\n    select:\n        a"),
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 17, 5)],
    ),
    # A let joined LATERAL reads the entry query's header too (Phase70 S11).
    "header_parameter": (
        _lateral("cross")
        .replace("query q:", "query q(cut: Int):")
        .replace("rhs.key == lhs.key", "rhs.key == lhs.key and rhs.id > cut"),
        [],
    ),
    # A JOIN written in another let is nested correlation.
    "join_in_another_let": (
        _lateral("cross").replace(
            ("    from lhs\n    let x = m\n    cross join x\n"),
            (
                "    let other:\n"
                "        from rhs\n"
                "        let y = m\n"
                "        cross join y\n"
                "        select:\n"
                "            id\n"
                "    from lhs\n"
                "    let x = other\n"
                "    cross join x\n"
            ),
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 16, 9)],
    ),
    # A let joined LATERAL may end in an ungrouped ORDER BY that reads no
    # captured field, and LIMIT (a top-k per left row); LIMIT keeps its static
    # rule and OFFSET stays outside the grammar.
    "top_k_cross": (_top_k("cross"), []),
    "top_k_inner": (_top_k("inner"), []),
    "top_k_left": (_top_k("left", on="        on x.id > lhs.id\n"), []),
    "top_k_limit_only": (_top_k("cross", order=""), []),
    "top_k_order_only": (_top_k("cross", limit=""), []),
    "top_k_limit_maximum": (_top_k("cross", limit=f"        limit {2**63 - 1}\n"), []),
    "top_k_limit_over_maximum": (
        _top_k("cross", limit=f"        limit {2**63}\n"),
        [
            (
                "PIE-S2307",
                "Limit must be a static integer from 0 to 9223372036854775807",
                15,
                15,
            ),
        ],
    ),
    "top_k_captured_order": (
        _top_k("cross", order="        order by:\n            lhs.key\n"),
        [("PIE-S2370", LATERAL_BODY_SHAPE, 7, 5)],
    ),
    "top_k_aggregate_order": (
        _top_k("cross", order="        order by:\n            count()\n"),
        [("PIE-S2370", LATERAL_BODY_SHAPE, 7, 5)],
    ),
    # A known limitation: a key that is no field of the let's input, its own
    # output or an unknown name, is only the declaration's PIE-S2333.
    "top_k_output_order": (
        _top_k("cross", order="        order by:\n            out desc\n").replace(
            "            id\n        order by:",
            "            out = id\n        order by:",
        ),
        [UNAVAILABLE],
    ),
    "top_k_unknown_order": (
        _top_k("cross", order="        order by:\n            nope desc\n"),
        [("PIE-S2102", "Unknown field: nope", 14, 13), UNAVAILABLE],
    ),
    "top_k_right": (_top_k("right"), [("PIE-S2372", JOIN_KIND, 18, 5)]),
    # Joined twice, the let keeps its LATERAL body rule; the second JOIN is
    # refused like any later read.
    "top_k_joined_twice": (
        _top_k("cross").replace(
            "    select:\n        a =",
            ("    let y = m\n    cross join y\n    select:\n        a ="),
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 20, 5)],
    ),
    "top_k_offset": (
        _top_k("cross", limit="        limit 2\n        offset 1\n"),
        [
            (
                "PIE-P1000",
                "Unknown clause 'offset'; a relation body lists from, joins, let, "
                "where, group by, select, having, qualify, order by and limit in "
                "that order.",
                16,
                9,
            ),
        ],
    ),
}


@pytest.mark.parametrize("case", sorted(LATERAL_DIAGNOSTICS))
def test_a_join_reads_a_capturing_let_lateral(tmp_path: Path, case: str) -> None:
    body, expected = LATERAL_DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1 if expected else 0, expected)


@pytest.mark.parametrize("top_k", (False, True))
@pytest.mark.parametrize("schema_version", (1, 2))
def test_a_lateral_join_is_available_only_in_explicit_module_projects(
    tmp_path: Path, schema_version: int, top_k: bool
) -> None:
    config = probe.CONFIG.replace(
        "schema_version = 2", f"schema_version = {schema_version}"
    )
    body = _top_k("cross") if top_k else _lateral("cross")
    code, diagnostics = _check(tmp_path, body, config=config)
    gated = [
        (
            "PIE-S2345",
            "Relation let declarations are available only in "
            "EXPLICIT_MODULES projects (schema version 2).",
            7,
            5,
        ),
        (
            "PIE-S2351",
            "Capture lines are available only in EXPLICIT_MODULES projects "
            "(schema version 2).",
            8,
            9,
        ),
    ]
    assert (code, diagnostics) == ((0, []) if schema_version == 2 else (1, gated))
    path = tmp_path / "single.pietto"
    path.write_text(HEAD + body, encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert cli.main(["check", str(path), "--format", "json"]) == 1
    assert [
        (d["code"], d["location"]["line"], d["location"]["column"])
        for d in json.loads(out.getvalue())["diagnostics"]
    ] == [("PIE-S2345", 7, 5), ("PIE-S2351", 8, 9)]


def test_a_lateral_capture_types_only_the_joins_left_of_it(tmp_path: Path) -> None:
    # The LEFT JOIN left of the lateral JOIN may null-extend r; the RIGHT JOIN
    # after it never changes the row the let reads, unlike an EXISTS read.
    let = (
        "query q:\n"
        "    let m:\n"
        "        capture lhs\n"
        "        capture r\n"
        "        from rhs\n"
        "        where rhs.id == lhs.id and rhs.id == r.id\n"
        "        select:\n"
        "            id\n"
        "    from lhs\n"
        "    let r = rhs\n"
        "    left join r on lhs.id == r.id\n"
    )
    tail = (
        "    let z = rhs\n"
        "    right join z on z.id == lhs.id\n"
        "{where}    select:\n"
        "        a = z.id\n"
    )
    lateral = let + ("    let x = m\n    cross join x\n") + tail.format(where="")
    exists = let + tail.format(where="    where exists m\n")
    types = {}
    for name, body in (("lateral", lateral), ("exists", exists)):
        assert _check(tmp_path / name, body) == (0, [])
        facts = _capture_facts(tmp_path / f"{name}-facts", body)["m"]
        types[name] = {
            (read.capture, read.field): value.nullability.value
            for read, value in facts.captured_value_types.items()
            if isinstance(value, ValueType)
        }
    assert types == {
        "lateral": {("lhs", "id"): "non_null", ("r", "id"): "nullable"},
        "exists": {("lhs", "id"): "nullable", ("r", "id"): "nullable"},
    }


def test_a_capture_of_a_left_lateral_binding_is_null_extended(tmp_path: Path) -> None:
    # Phase70 S13: x may be null-extended by its own LEFT JOIN, so a later
    # lateral let and an EXISTS read both read x.id as nullable although the
    # let's id is NOT NULL.
    body = (
        "query q:\n"
        "    let m:\n"
        "        capture lhs\n"
        "        from rhs\n"
        "        where rhs.key == lhs.key\n"
        "        select:\n"
        "            id\n"
        "    let n:\n"
        "        capture x\n"
        "        from rhs\n"
        "        where rhs.id == x.id\n"
        "        select:\n"
        "            id\n"
        "    let e:\n"
        "        capture x\n"
        "        from rhs\n"
        "        where rhs.id == x.id\n"
        "        select:\n"
        "            id\n"
        "    from lhs\n"
        "    let x = m\n"
        "    left join x on True\n"
        "    let y = n\n"
        "    cross join y\n"
        "    where exists e\n"
        "    select:\n"
        "        a = lhs.id\n"
        "        b = x.id\n"
    )
    assert _check(tmp_path / "check", body) == (0, [])
    facts = _capture_facts(tmp_path / "facts", body)
    for name in ("n", "e"):
        assert {
            (read.capture, read.field): value.nullability.value
            for read, value in facts[name].captured_value_types.items()
            if isinstance(value, ValueType)
        } == {("x", "id"): "nullable"}, name


# VALUES lets, a forward let read and refused relation reads in one query: a
# let read only by a refused read is still read (`flags`, `seed`), and each
# refusal is reported once, in checking order, with no cascade.
REFUSED_READS = (
    "query p(c: Int):\n"
    "    from lhs\n"
    "    where id > c\n"
    "    select:\n"
    "        id\n"
    "query result:\n"
    "    let over:\n"
    "        from seed\n"
    "        select:\n"
    "            rid\n"
    "    let seed:\n"
    "        values(rid: Int):\n"
    "            1\n"
    "            2\n"
    "    let flags:\n"
    "        values(f: Bool | None):\n"
    "            True\n"
    "            None\n"
    "    let spare:\n"
    "        values(rid: Int)\n"
    "    from lhs\n"
    "    let r = rhs\n"
    "    inner join r on lhs.id == r.id and exists flags\n"
    "    where lhs.id <= scalar over.rid and lhs.id in p\n"
    "    select:\n"
    "        a = lhs.id\n"
    "        n = row_number() window(order by lhs.id)\n"
    "    qualify:\n"
    "        n in seed\n"
)
POSITION = "relation reference is available only in WHERE and in the SELECT of an "


def test_refused_reads_of_values_lets_report_one_ordered_list(tmp_path: Path) -> None:
    assert _check(tmp_path, REFUSED_READS) == (
        1,
        [
            ("PIE-S2359", "Let relation spare is never read.", 24, 5),
            ("PIE-S2349", f"EXISTS {POSITION}ungrouped query, not in JOIN ON.", 28, 40),
            ("PIE-S2350", f"IN {POSITION}ungrouped query, not in QUALIFY.", 34, 9),
            (
                "PIE-S2348",
                "Scalar relation read over.rid is not yet available: the columns "
                "of over are not known before completion.",
                29,
                21,
            ),
            (
                "PIE-S2356",
                "A query with parameters cannot be the input of another relation.",
                29,
                41,
            ),
        ],
    )


_MODERN_NAMED_CAPTURE = """shape Row:
    id: Int
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
query result(low: Int):
    let near:
        let input = rhs
        from input
        let adjusted = low + 1
        where input.id > adjusted
        select id = input.id
    let later:
        capture base
        from rhs
        where rhs.id == base.id
        select later_id = rhs.id
        order by later_id
        limit 1
    let base = lhs
    from base
    let n = near
    inner join n on base.id == n.id
    let l = later
    left join l on l.later_id > low
    where exists near and exists near
    select id = base.id
"""


def _modern_naming_project(root: Path, source: str) -> Path:
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    (root / "main.pietto").write_text(source, encoding="utf-8")
    return root


def test_modern_block_and_local_names_keep_header_capture_and_read_occurrences(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pietto import ast_nodes as ast
    from pietto._project import project_relationship_predicates as names
    from pietto._project.module_catalog import _build_project_module_catalog_set
    from pietto._project.module_relation_resolution import expression_block_reads
    from pietto._project.relation_captures import outer_row_bindings

    originals = []
    normalize = names.normalize_project_query_names

    def observe(parsed):
        originals.append(parsed)
        return normalize(parsed)

    monkeypatch.setattr(names, "normalize_project_query_names", observe)
    source = (
        _MODERN_NAMED_CAPTURE
        + """query other:
    let near:
        from rhs
        select id = rhs.id
    from lhs
    let n = near
    inner join n on lhs.id == n.id
    select id = lhs.id
"""
    )
    parsed = check_project_parse_only(
        _modern_naming_project(tmp_path / "project", source)
    )
    assert parsed.ok, parsed.diagnostics
    (original,) = originals
    raw = original.parsed_inputs[0].script
    current = parsed.parsed_inputs[0].script
    before, before_other = raw.definitions[-2:]
    after, after_other = current.definitions[-2:]
    assert isinstance(before, ast.BlockRelationDef)
    assert isinstance(after, ast.BlockRelationDef)
    assert isinstance(before_other, ast.BlockRelationDef)
    assert isinstance(after_other, ast.BlockRelationDef)
    assert after.parameters is before.parameters
    assert isinstance(before.body, ast.SelectBody)
    assert isinstance(after.body, ast.SelectBody)
    assert after.body.naming_declarations == ()
    assert isinstance(after.body.from_clause, ast.FromClause)
    assert after.body.where_clause is before.body.where_clause
    assert after.body.select_items is before.body.select_items
    assert after.body.from_clause.source_name == "lhs"
    assert after.body.from_clause.binding_name == "base"
    assert outer_row_bindings(after) == (("base", 0), ("n", 1), ("l", 2))
    assert [join.target_relation_name for join in after.body.join_clauses] == [
        "near",
        "later",
    ]
    assert [join.target_binding_name for join in after.body.join_clauses] == ["n", "l"]
    assert all(
        left.on_clause is right.on_clause
        for left, right in zip(
            before.body.join_clauses, after.body.join_clauses, strict=True
        )
    )
    assert after.let_relations[1] is before.let_relations[1]
    assert after.let_relations[1].captures is before.let_relations[1].captures
    near_before, near_after = before.let_relations[0].body, after.let_relations[0].body
    assert isinstance(near_before, ast.SelectBody)
    assert isinstance(near_after, ast.SelectBody)
    assert near_after.naming_declarations == () and near_after.let_clause is not None
    assert isinstance(near_after.from_clause, ast.FromClause)
    assert near_after.from_clause.source_name == "rhs"
    assert near_after.from_clause.binding_name == "input"
    assert near_after.where_clause is near_before.where_clause
    assert (
        near_after.let_clause.bindings[0].expression
        is near_before.naming_declarations[1].expression
    )
    catalog = _build_project_module_catalog_set(parsed.modules).catalogs[0]
    (owner,) = [item for item in catalog.occurrences if item.authored is after]
    (other,) = [item for item in catalog.occurrences if item.authored is after_other]
    assert isinstance(owner.definition, ast.QueryDef)
    assert owner.definition.parameters is before.parameters
    reads = expression_block_reads(owner)
    assert [read.relation_name for read in reads] == ["near", "near"]
    assert [read.ordinal for read in reads] == [0, 1]
    assert reads[0].expression is not reads[1].expression
    assert reads[0].owner is reads[1].owner is owner
    assert (
        catalog.find_lets(owner.declaration_position)[0].authored
        is after.let_relations[0]
    )
    assert (
        catalog.find_lets(other.declaration_position)[0].authored
        is after_other.let_relations[0]
    )
    assert (
        catalog.find_lets(owner.declaration_position)[0]
        is not catalog.find_lets(other.declaration_position)[0]
    )


@pytest.mark.parametrize(
    "variant", ("unknown", "duplicate", "future", "module_collision", "bad_file")
)
def test_modern_capture_admission_keeps_raw_diagnostics_when_naming_is_blocked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variant: str
) -> None:
    from pietto._project import check as project_check
    from pietto._project import project_relationship_predicates as names

    captured = []
    parse = project_check._parse_selected_input
    normalize = names.normalize_project_query_names
    normalizations = []

    def observe_parse(*args, **kwargs):
        result = parse(*args, **kwargs)
        captured[:] = kwargs["capture_diagnostics_out"]
        return result

    def observe_names(parsed):
        normalizations.append(parsed)
        return normalize(parsed)

    monkeypatch.setattr(project_check, "_parse_selected_input", observe_parse)
    monkeypatch.setattr(names, "normalize_project_query_names", observe_names)
    source = _MODERN_NAMED_CAPTURE
    if variant == "unknown":
        source = source.replace("    let l = later\n", "    let l = absent\n")
    elif variant == "duplicate":
        source = source.replace("    let l = later\n", "    let l = later\n" * 3)
    elif variant == "future":
        source = source.replace(
            "    let l = later\n", "    let l = future\n    let future = later\n"
        )
    elif variant == "module_collision":
        source = source.replace(
            "query result(", 'source near: Row = postgres.table("other")\nquery result('
        )
    root = _modern_naming_project(tmp_path / "project", source)
    if variant == "bad_file":
        (root / "a_bad.pietto").write_text(
            "shape Broken:\n    id Int\n", encoding="utf-8"
        )
    result = project_check.check_project_parse_only(root)
    assert not result.ok
    assert captured and all(
        any(item is old for item in result.diagnostics) for old in captured
    )
    assert all(item.code == "PIE-S2370" for item in captured)
    positions = {item.path: position for position, item in enumerate(result.inputs)}
    assert [
        positions[item.location.path or ""] for item in result.diagnostics
    ] == sorted(positions[item.location.path or ""] for item in result.diagnostics)
    if variant == "bad_file":
        assert normalizations == []
        assert any(
            item.code == "PIE-P1000" and item.location.path == "a_bad.pietto"
            for item in result.diagnostics
        )
    else:
        assert len(normalizations) == 1
        # The naming checks: a `let` that a JOIN reads names a relation, so
        # an unknown or later name there is PIE-S2301 or PIE-S2330.
        naming = [
            item
            for item in result.diagnostics
            if item.code in {"PIE-S2604", "PIE-S2301", "PIE-S2330"}
        ]
        assert naming
        assert [
            (item.location.line, item.location.column) for item in result.diagnostics
        ] == sorted(
            (item.location.line, item.location.column) for item in result.diagnostics
        )
        if variant == "duplicate":
            assert [item.message for item in naming] == [
                "Duplicate query local name: l"
            ] * 2
            assert naming[0].location != naming[1].location
        elif variant == "module_collision":
            assert any(
                item.message == "Ambiguous relation name: near" for item in naming
            )
        else:
            assert [(item.code, item.message) for item in naming] == [
                ("PIE-S2301", "Unknown relation: absent")
                if variant == "unknown"
                else (
                    "PIE-S2330",
                    "Let binding cannot reference a later binding: future",
                )
            ]


@pytest.mark.parametrize("module_relation", (False, True))
def test_modern_table_function_column_participates_in_query_name_role_resolution(
    tmp_path: Path, module_relation: bool
) -> None:
    from pietto import ast_nodes as ast

    source = (
        ('source n = postgres.table("n")\n' if module_relation else "")
        + """query q:
    from generate_series(1, 3, 1) as n
    let chosen = n
    select chosen
"""
    )
    parsed = check_project_parse_only(
        _modern_naming_project(tmp_path / "project", source)
    )
    if module_relation:
        assert not parsed.ok
        assert [(item.code, item.message) for item in parsed.diagnostics] == [
            ("PIE-S2604", "Ambiguous relation or scalar name: n")
        ]
    else:
        assert parsed.ok, parsed.diagnostics
        (owner,) = parsed.parsed_inputs[0].script.definitions
        assert isinstance(owner, ast.BlockRelationDef)
        assert isinstance(owner.body, ast.SelectBody)
        assert isinstance(owner.body.from_clause, ast.TableFunctionFromClause)
        assert owner.body.from_clause.binding_name == "n"
        assert (
            owner.body.naming_declarations == () and owner.body.let_clause is not None
        )
        (binding,) = owner.body.let_clause.bindings
        assert binding.name == "chosen"
        assert (
            isinstance(binding.expression, ast.NameExpr)
            and binding.expression.name == "n"
        )


def test_modern_local_scalar_names_do_not_hide_header_position_refusals(
    tmp_path: Path,
) -> None:
    source = """source rhs = postgres.table("rhs")
query result(low: Int):
    let nearby:
        from rhs
        let held = low + 1
        select n = row_number() window(order by held)
    from nearby
    select n
"""
    parsed = check_project_parse_only(
        _modern_naming_project(tmp_path / "project", source)
    )
    assert not parsed.ok
    (diagnostic,) = parsed.diagnostics
    assert diagnostic.code == "PIE-S2355"
    assert diagnostic.message == "Query parameters are not available in this position."
    assert diagnostic.location.path == "main.pietto"
    line = source.splitlines()[5]
    column = line.index("held") + 1
    assert (diagnostic.location.line, diagnostic.location.column) == (6, column)
    assert (diagnostic.location.end_line, diagnostic.location.end_column) == (
        6,
        column + 4,
    )


@pytest.mark.parametrize(
    ("imports", "lets", "expected"),
    (
        (
            "    source lhs,\n",
            "    let r = rhs\n",
            [
                (
                    "PIE-S2301",
                    "Unknown relation: rhs; rhs is a source exported by base.pietto: "
                    'import it with from "base.pietto" import (source rhs)',
                    "main.pietto",
                    7,
                    13,
                )
            ],
        ),
        (
            # The failed import, not the let, is the error, and the JOIN reads
            # the import's name as a direct `inner join rhz` would: the JOIN
            # stopped by that reported failure adds no follow-on error.
            "    source lhs,\n    source rhz,\n",
            "    let r = rhz\n",
            [
                (
                    "PIE-S2705",
                    'Unknown imported declaration: source rhz from "base.pietto"',
                    "main.pietto",
                    4,
                    12,
                ),
            ],
        ),
        (
            "    source lhs,\n    source rhs,\n",
            "    let r = nosuch\n",
            [("PIE-S2301", "Unknown relation: nosuch", "main.pietto", 8, 13)],
        ),
        (
            "    source lhs,\n    source rhs,\n",
            "    let r = later\n    let later = rhs\n",
            [
                (
                    "PIE-S2330",
                    "Let binding cannot reference a later binding: later",
                    "main.pietto",
                    8,
                    13,
                )
            ],
        ),
        ("    source lhs,\n    source rhs,\n", "    let r = rhs\n", []),
    ),
    ids=("not_imported", "failed_import", "unknown", "later", "imported"),
)
def test_a_let_that_a_join_reads_names_a_module_relation(
    tmp_path: Path, imports: str, lets: str, expected: list
) -> None:
    """`let r = rhs` names the relation the later JOIN of `r` reads, so a
    name the module neither declares nor imports is an unknown relation at
    the value, as for `from`, not a misplaced row-value let (PIE-S2604)."""

    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "base.pietto").write_text(
        HEAD + "export (\n    shape Row,\n    source lhs,\n    source rhs)\n"
    )
    (tmp_path / "main.pietto").write_text(
        f'from "base.pietto" import (\n    shape Row,\n{imports})\n'
        f"query q:\n    from lhs\n{lets}    inner join r on lhs.id == r.id\n"
        "    select:\n        id = lhs.id\n"
    )
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    assert (
        code,
        [
            (
                d["code"],
                d["message"],
                d["location"]["path"],
                d["location"]["line"],
                d["location"]["column"],
            )
            for d in json.loads(out.getvalue())["diagnostics"]
        ],
    ) == (1 if expected else 0, expected)


def test_a_naming_error_never_masks_the_module_errors_of_any_module(
    tmp_path: Path,
) -> None:
    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "base.pietto").write_text(
        HEAD + "export (\n    shape Row,\n    source lhs,\n    source rhs)\n"
    )
    (tmp_path / "main.pietto").write_text(
        'from "base.pietto" import (\n    source lhs)\n'
        "query q:\n    from lhs\n    let r = rhz\n"
        "    inner join r on lhs.id == r.id\n    select:\n        id = lhs.id\n"
    )
    (tmp_path / "other.pietto").write_text(
        'from "missing.pietto" import (\n    source lhs)\n'
    )
    parsed = check_project_parse_only(tmp_path)
    # The module errors, which semantic analysis would report first, come
    # ahead of the query-local naming error that stops the check before it.
    assert [
        (item.code, item.message, item.location.path, item.location.line)
        for item in parsed.diagnostics
    ] == [
        (
            "PIE-S2701",
            'Unresolved module import target: "missing.pietto"',
            "other.pietto",
            1,
        ),
        ("PIE-S2301", "Unknown relation: rhz", "main.pietto", 5),
    ]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        (
            "query p(cutoff: Int, cutoff: Int):\n    from lhs\n"
            "    select:\n        id\n",
            ("PIE-S2001", "Duplicate parameter name in query p: cutoff", 1),
        ),
        (
            "query p(key: Int):\n    from lhs\n    select:\n        key\n",
            (
                "PIE-S2354",
                "Query parameter name is also a field, let, relation, output"
                " or window name.",
                4,
            ),
        ),
        (
            "query p(cutoff: Int):\n    from lhs\n"
            "    select:\n        id\n    limit cutoff\n",
            (
                "PIE-S2355",
                "Query parameters are not available in this position.",
                5,
            ),
        ),
        (
            # A def that is not inlined keeps its declaration, which is no
            # module declaration.
            "def g(x: Int) -> Int:\n    return 1\n",
            (
                "PIE-S2397",
                "Def g parameter x is not used in its body; every parameter"
                " must be used",
                1,
            ),
        ),
    ],
)
def test_a_def_header_or_parameter_error_never_masks_the_module_errors(
    tmp_path: Path, query: str, expected: tuple[str, str, int]
) -> None:
    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "base.pietto").write_text(HEAD)
    (tmp_path / "main.pietto").write_text(HEAD + query)
    (tmp_path / "other.pietto").write_text(
        'from "base.pietto" import (\n    source lhs)\n'
        'from "missing.pietto" import (\n    source rhs)\n'
    )
    parsed = check_project_parse_only(tmp_path)
    code, message, line = expected
    # Semantic analysis, which reports every module's import errors first,
    # never runs after these errors, so the parse check reports them, with
    # their facts, ahead of the error of an unrelated module that stops it.
    assert [
        (item.code, item.message, item.location.path, item.location.line)
        for item in parsed.diagnostics
    ] == [
        (
            "PIE-S2701",
            'Unresolved module import target: "missing.pietto"',
            "other.pietto",
            3,
        ),
        (
            "PIE-S2705",
            "Imported declaration is private or not exported:"
            ' source lhs from "base.pietto"',
            "other.pietto",
            2,
        ),
        (code, message, "main.pietto", len(HEAD.splitlines()) + line),
    ]
    assert parsed.module_diagnostic_facts is not None
    assert (
        tuple(fact.diagnostic for fact in parsed.module_diagnostic_facts.facts)
        == parsed.diagnostics[:2]
    )


def _check_file(
    tmp_path: Path, body: str
) -> tuple[int, list[tuple[str, str, int, int]]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "single.pietto"
    path.write_text(HEAD + body, encoding="utf-8")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", str(path), "--format", "json"])
    return code, [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in json.loads(out.getvalue())["diagnostics"]
    ]


# The FROM input's name is the name written after `from`: after `let r = lhs`
# and `from r` a query reads `r.id` (language.md, Single-file JOINs), and a
# project reads it so in every clause. A project keeps reading `lhs.id` there
# too where 0.1.5 admitted it: in a query without a JOIN, outside `any(...)`;
# before, selecting `lhs.id` stopped `check --project` with a
# canonical-inspection ValueError. A single file refuses `lhs.id`.
_FROM_ALIAS = "query q:\n    let r = lhs\n    from r\n"
FROM_ALIAS_READS = {
    "select": (_FROM_ALIAS, "    select:\n        id = {}.id\n", "r", "lhs", ()),
    "select_unaliased": (_FROM_ALIAS, "    select:\n        {}.key\n", "r", "lhs", ()),
    "where": (
        _FROM_ALIAS,
        "    where {}.id > 1\n    select:\n        id\n",
        "r",
        "lhs",
        (),
    ),
    "expression": (
        _FROM_ALIAS,
        "    select:\n        id = {}.id + 1\n",
        "r",
        "lhs",
        (),
    ),
    "window": (
        _FROM_ALIAS,
        "    select:\n        id\n        n = row_number() window(order by {}.id)\n",
        "r",
        "lhs",
        (),
    ),
    "alias_of_an_alias": (
        "query q:\n    let r = lhs\n    let s = r\n    from s\n",
        "    select:\n        id = {}.id\n",
        "s",
        "lhs",
        ("r",),
    ),
    "alias_of_a_table": (
        "table base:\n    from lhs\n    select:\n        id\n"
        "query q:\n    let r = base\n    from r\n",
        "    select:\n        id = {}.id\n",
        "r",
        "base",
        ("lhs",),
    ),
}


@pytest.mark.parametrize("case", sorted(FROM_ALIAS_READS))
def test_a_from_alias_names_the_input_in_a_project_as_in_a_single_file(
    tmp_path: Path, case: str
) -> None:
    head, tail, alias, source_name, invalid_names = FROM_ALIAS_READS[case]
    field = "key" if case == "select_unaliased" else "id"
    body = head + tail.format(alias)
    assert _check(tmp_path / "project", body) == (0, [])
    assert _check_file(tmp_path / "file", body) == (0, [])
    source_body = head + tail.format(source_name)
    assert _check(tmp_path / "project-source", source_body) == (0, [])
    source = (HEAD + source_body).splitlines()
    line = next(
        number
        for number, text in enumerate(source, 1)
        if f"{source_name}.{field}" in text
    )
    column = source[line - 1].index(f"{source_name}.{field}") + 1
    assert _check_file(tmp_path / "file-source", source_body) == (
        1,
        [("PIE-S2102", f"Unknown field: {source_name}.{field}", line, column)],
    )
    for name in invalid_names:
        body = head + tail.format(name)
        source = (HEAD + body).splitlines()
        line = next(
            number for number, text in enumerate(source, 1) if f"{name}.{field}" in text
        )
        column = source[line - 1].index(f"{name}.{field}") + 1
        expected = (1, [("PIE-S2102", f"Unknown field: {name}.{field}", line, column)])
        assert _check(tmp_path / f"project-{name}", body) == expected
        assert _check_file(tmp_path / f"file-{name}", body) == expected


def test_a_from_alias_source_name_keeps_an_inner_any_binding(tmp_path: Path) -> None:
    body = (
        "query q:\n    let c = lhs\n    from c\n"
        "    where any(lhs.id == c.id for lhs in rhs)\n"
        "    select:\n        id\n"
    )
    assert _check(tmp_path, body) == (0, [])


def test_a_from_alias_source_name_stays_refused_when_an_any_shadows_the_alias(
    tmp_path: Path,
) -> None:
    body = (
        "query q:\n    let c = lhs\n    from c\n"
        "    where any(lhs.id == c.key for c in rhs)\n"
        "    select:\n        id\n"
    )
    expected = (
        1,
        [("PIE-S2102", "Unknown or unavailable field in ANY predicate: lhs.id", 9, 15)],
    )
    assert _check(tmp_path, body) == expected
    assert _check_file(tmp_path / "file", body) == expected


def test_a_from_alias_source_name_outside_an_any_still_reads_the_from_input(
    tmp_path: Path,
) -> None:
    body = (
        "query q:\n    let c = lhs\n    from c\n"
        "    where any(c.id == r.key for r in rhs) and lhs.id > 0\n"
        "    select:\n        id\n"
    )
    assert _check(tmp_path, body) == (0, [])


# Inside `any(...)` and in a query with a JOIN a project refuses the relation's
# own name, as 0.1.5 did; a self JOIN would otherwise pick the FROM occurrence
# of `lhs` over the JOINed one. Inside `any(...)` and in JOIN ON it reports
# what a single file reports.
_FROM_ALIAS_JOIN = _FROM_ALIAS + "    let o = rhs\n"
_ANY_UNKNOWN = "Unknown or unavailable field in ANY predicate: lhs.id"
FROM_ALIAS_REFUSED = {
    "any": (
        _FROM_ALIAS + "    where any(x.key == lhs.id for x in rhs)\n"
        "    select:\n        id\n",
        [("PIE-S2102", _ANY_UNKNOWN, 9, 24)],
    ),
    "nested_any": (
        _FROM_ALIAS
        + "    where any(any(y.id == x.id and y.key == lhs.id for y in rhs) "
        "for x in rhs)\n    select:\n        id\n",
        [("PIE-S2102", _ANY_UNKNOWN, 9, 45)],
    ),
    "join_on": (
        _FROM_ALIAS_JOIN + "    left join o on o.key == lhs.id\n"
        "    select:\n        id = r.id\n",
        [("PIE-S2335", "JOIN ON reference is unknown: lhs.id", 10, 29)],
    ),
    "join_where": (
        _FROM_ALIAS_JOIN + "    inner join o on o.key == r.id\n"
        "    where lhs.id > 1\n    select:\n        id = r.id\n",
        [("PIE-S2102", "Unknown field: lhs.id", 11, 11)],
    ),
    "join_select": (
        _FROM_ALIAS_JOIN + "    inner join o on o.key == r.id\n"
        "    select:\n        a = lhs.id\n",
        [("PIE-S2102", "Unknown field: lhs.id", 12, 13)],
    ),
    "self_join": (
        _FROM_ALIAS + "    let s = lhs\n    inner join s on s.id == r.id\n"
        "    select:\n        a = lhs.id\n",
        [("PIE-S2102", "Unknown field: lhs.id", 12, 13)],
    ),
}


@pytest.mark.parametrize("case", sorted(FROM_ALIAS_REFUSED))
def test_a_from_alias_source_name_stays_refused_in_any_and_join_scopes(
    tmp_path: Path, case: str
) -> None:
    body, expected = FROM_ALIAS_REFUSED[case]
    assert _check(tmp_path / "project", body) == (1, expected)
    file = _check_file(tmp_path / "file", body)
    assert file[0] == 1
    if case in {"any", "nested_any", "join_on"}:
        assert file == (1, expected)


def test_a_from_alias_source_name_keeps_an_unknown_field_diagnostic(
    tmp_path: Path,
) -> None:
    body = _FROM_ALIAS + "    select:\n        a = lhs.missing\n"
    source = (HEAD + body).splitlines()
    line = next(
        number for number, text in enumerate(source, 1) if "lhs.missing" in text
    )
    column = source[line - 1].index("lhs.missing") + 1
    assert _check(tmp_path, body) == (
        1,
        [("PIE-S2102", "Unknown field: lhs.missing", line, column)],
    )


@pytest.mark.parametrize("argument", ("{}.text", "lower({}.text)"))
def test_a_from_alias_source_name_keeps_inline_def_argument_checks(
    tmp_path: Path, argument: str
) -> None:
    prefix = (
        "shape TextRow:\n    text: Text\n"
        'source texts: TextRow = postgres.table("texts")\n'
        "def need_int(x: Int) -> Int: return x\n"
    )
    bodies = (
        "query q:\n    from texts\n    select:\n        a = need_int("
        + argument.format("texts")
        + ")\n",
        "query q:\n    let r = texts\n    from r\n"
        "    select:\n        a = need_int(" + argument.format("r") + ")\n",
        "query q:\n    let r = texts\n    from r\n"
        "    select:\n        a = need_int(" + argument.format("texts") + ")\n",
    )
    results = []
    for name, body in zip(("direct", "binding", "source"), bodies, strict=True):
        results.append(_check(tmp_path / name, prefix + body))
    assert [
        [(code, message) for code, message, _, _ in result[1]] for result in results
    ] == [
        [
            (
                "PIE-S2395",
                "Invalid argument for def need_int at position 1 (x): expected Int, got Text",
            )
        ]
    ] * 3


# Clauses whose refusal of a name that is no input differs between the two
# modes for any such name, or that only a project has: their reads by the
# alias are accepted in each mode that has them.
FROM_ALIAS_ACCEPTED = {
    "group_having": (
        _FROM_ALIAS + "    group by:\n        r.id\n    select:\n        id = r.id\n"
        "        n = count()\n    having:\n        n > 1\n",
        True,
    ),
    "aggregate": (_FROM_ALIAS + "    select:\n        m = max(r.key)\n", True),
    "aggregate_source": (
        _FROM_ALIAS + "    select:\n        m = max(lhs.key)\n",
        False,
    ),
    "distinct": (_FROM_ALIAS + "    select distinct:\n        id = r.id\n", False),
    "group_having_source": (
        _FROM_ALIAS
        + "    group by:\n        lhs.id\n    select:\n        id = lhs.id\n"
        "        n = count()\n    having:\n        n > 1\n",
        False,
    ),
    "relation_let_body": (
        "query q:\n    let a:\n        let r = lhs\n        from r\n"
        "        select:\n            id = r.id\n    from a\n    select:\n        id\n",
        False,
    ),
}


@pytest.mark.parametrize("case", sorted(FROM_ALIAS_ACCEPTED))
def test_a_from_alias_reads_in_every_clause_a_project_checks(
    tmp_path: Path, case: str
) -> None:
    body, single_file = FROM_ALIAS_ACCEPTED[case]
    assert _check(tmp_path / "project", body) == (0, [])
    if single_file:
        assert _check_file(tmp_path / "file", body) == (0, [])
