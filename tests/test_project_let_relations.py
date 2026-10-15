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

import pytest

import _pietto_sql_emission as probe
from pietto import cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result

TARGETS = ("postgres", "mysql")
HEAD = """shape Row:
    id: Int not null
    key: Int nullable
source lhs: Row is postgres.table("lhs")
source rhs: Row is postgres.table("rhs")
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
JOIN_ON = "JOIN pre-match input or relationship authority is unavailable."
DIAGNOSTICS = {
    "duplicate_let": (
        "query q:\n" + LET + LET + "    from a\n    select:\n        id\n",
        [
            ("PIE-S2001", "Duplicate symbol name in relation namespace: a", 11, 5),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "module_relation": (
        "query q:\n    let lhs:\n        from rhs\n        select:\n            id\n"
        "    from lhs\n    select:\n        id\n",
        [
            ("PIE-S2001", "Duplicate symbol name in relation namespace: lhs", 7, 5),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "own_declaration": (
        "query q:\n    let q:\n        from rhs\n        select:\n            id\n"
        "    from q\n    select:\n        id\n",
        [
            ("PIE-S2001", "Duplicate symbol name in relation namespace: q", 7, 5),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    # Only relation reads of the name resolve to nothing; the JOIN binding
    # still qualifies its own input.
    "join_binding": (
        "query q:\n" + LET + "    from lhs\n    inner join rhs as a:\n"
        "        from lhs\n        on lhs.id == a.id\n    select:\n        id = lhs.id\n",
        [("PIE-S2001", "Duplicate symbol name in relation namespace: a", 7, 5)],
    ),
    "cycle_through_parent": (
        "query q:\n    let a:\n        from q\n        select:\n            id\n"
        "    from a\n    select:\n        id\n",
        [("PIE-S2302", "Relation cycle detected: a -> q -> a", 11, 5)],
    ),
    "outside_its_declaration": (
        "query q:\n" + LET + "    from a\n    select:\n        id\n"
        "query r:\n    from a\n    select:\n        id\n",
        [
            ("PIE-S2301", "Unknown relation: a", 15, 5),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: r",
                14,
                1,
            ),
        ],
    ),
    # Another declaration's let issue never stands in for this read's own.
    "other_declarations_let_issue": (
        "query q:\n" + LET + "    from lhs\n    select:\n        id\n"
        "query r:\n    union all:\n        from a\n        from lhs\n",
        [
            ("PIE-S2359", "Let relation a is never read.", 7, 5),
            ("PIE-S2301", "Unknown relation: a", 16, 9),
            ("PIE-S2334", "Set-operation semantics are not implemented.", 15, 5),
        ],
    ),
    "capture": (
        "query q:\n    let a:\n        capture lhs\n        from rhs\n"
        "        select:\n            id\n    from a\n    select:\n        id\n",
        [("PIE-S2351", "Capture line semantics are not implemented.", 8, 9)],
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
            ("PIE-S2334", "Set-operation semantics are not implemented.", 8, 9),
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
            ("PIE-S2334", "Set-operation semantics are not implemented.", 8, 9),
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
    """`query s` reads `name` as a set operand and `query t` as a JOIN target."""
    return (
        f"query s:\n    union all:\n        from lhs\n        from {name}\n"
        f"query t:\n    from lhs\n    inner join {name} as x:\n        from lhs\n"
        "        on lhs.id == x.id\n    select:\n        id = lhs.id\n"
    )


JOIN_TAIL = [
    (
        "PIE-S2335",
        "JOIN pre-match input or relationship authority is unavailable.",
        12,
        5,
    ),
    ("PIE-S2335", "JOIN ON reference is unavailable.", 14, 22),
]


def _unknown_to_readers(name: str) -> list[tuple[str, str, int, int]]:
    """What `_readers(name)` reports when `name` is unknown in s and t."""
    return [
        ("PIE-S2301", f"Unknown relation: {name}", 9, 9),
        ("PIE-S2334", "Set-operation semantics are not implemented.", 7, 5),
        ("PIE-S2334", "JOIN-local ON semantics are not implemented.", 14, 9),
    ]


# `query q` after the readers has an error about the name they read; each
# reader still meets an unknown relation, exactly as without q.
ELSEWHERE = {
    "unread": (
        "a",
        "query q:\n" + _let("a", "lhs") + "    from lhs\n    select:\n        id\n",
        [
            ("PIE-S2359", "Let relation a is never read.", 18, 5),
            *_unknown_to_readers("a"),
            *JOIN_TAIL,
        ],
    ),
    "cycle": (
        "a",
        "query q:\n"
        + _let("a", "b")
        + _let("b", "a")
        + "    from a\n    select:\n        id\n",
        [
            ("PIE-S2302", "Relation cycle detected: a -> b -> a", 23, 9),
            *_unknown_to_readers("a"),
            *JOIN_TAIL,
        ],
    ),
    "unknown_read_in_a_let": (
        "zz",
        "query q:\n" + _let("a", "zz") + "    from a\n    select:\n        id\n",
        [
            ("PIE-S2301", "Unknown relation: zz", 19, 9),
            *_unknown_to_readers("zz"),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: a",
                18,
                5,
            ),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                17,
                1,
            ),
            *JOIN_TAIL,
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
    assert environment.find_scoped_issues(owners["t"], name) == ()


def _imported(tmp_path: Path, imports: str, let: str):
    (tmp_path / "pietto.toml").write_text(probe.CONFIG)
    (tmp_path / "base.pietto").write_text(
        HEAD + "query q:\n    from lhs\n    select:\n        id\n"
        "export:\n    query q\n    source lhs\n",
        encoding="utf-8",
    )
    (tmp_path / "main.pietto").write_text(
        f'import "base.pietto":\n{imports}'
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
            [("PIE-S2001", "main.pietto", 5), ("PIE-S2333", "main.pietto", 4)],
        ),
        (
            "    source lhs\n    query nothere\n",
            "nothere",
            [
                ("PIE-S2705", "main.pietto", 3),
                ("PIE-S2001", "main.pietto", 5),
                ("PIE-S2333", "main.pietto", 4),
            ],
        ),
        (
            "    source lhs\n    query q as x\n    source lhs as x\n",
            "x",
            [
                ("PIE-S2706", "main.pietto", 3),
                ("PIE-S2001", "main.pietto", 6),
                ("PIE-S2333", "main.pietto", 5),
            ],
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
    assert _check(tmp_path / "export", owner + "export:\n    query a\n") == (
        1,
        [("PIE-S2704", "Unknown export binding: query a", 15, 11)],
    )
    root = tmp_path / "import"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG)
    (root / "base.pietto").write_text(HEAD + owner + "export:\n    query q\n")
    (root / "main.pietto").write_text(
        'import "base.pietto":\n    query a\nquery r:\n    from a\n'
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
                "Let relation declaration semantics are not implemented.",
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
