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
from pietto.semantic.model import ValueType

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
            (
                "PIE-S2334",
                "Set operations are available only when an "
                "EXPLICIT_MODULES project (schema version 2) completes them.",
                15,
                5,
            ),
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
                "in or a join in the body of q.",
                12,
                5,
            ),
        ],
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
            (
                "PIE-S2334",
                "Set operations are available only when an "
                "EXPLICIT_MODULES project (schema version 2) completes them.",
                8,
                9,
            ),
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
            (
                "PIE-S2334",
                "Set operations are available only when an "
                "EXPLICIT_MODULES project (schema version 2) completes them.",
                8,
                9,
            ),
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
        (
            "PIE-S2334",
            "Set operations are available only when an "
            "EXPLICIT_MODULES project (schema version 2) completes them.",
            7,
            5,
        ),
        (
            "PIE-S2334",
            "JOIN-local ON is available only when an EXPLICIT_MODULES "
            "project (schema version 2) completes it.",
            14,
            9,
        ),
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
    "Let m with capture lines can be read only once, by exists, scalar, in or a "
    "join in the body of q."
)
BODY_SHAPE = (
    "Let m with capture lines may use only FROM, WHERE and an ungrouped SELECT."
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
    "semi_join_target": (
        CAPTURE.replace("capture lhs", "capture r")
        .replace("lhs.key\n", "r.key\n")
        .replace(
            "    from lhs\n    where",
            "    from lhs\n    semi join rhs as r:\n        from lhs\n"
            "        on lhs.id == r.id\n    where",
        ),
        [
            (
                "PIE-S2366",
                "Capture r does not name one FROM or JOIN row input of q.",
                8,
                9,
            )
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
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    "where_aggregate": (
        CAPTURE.replace("where rhs.key == lhs.key", "where count() > lhs.id"),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # Capture refusals take one source order with the file's pre-admission
    # diagnostics (here the header of a set-operation body); the query header
    # checks follow them.
    "pre_admission_order": (
        "query p(x: Foo not null):\n    from lhs\n    where id > x\n    select:\n"
        "        id\nquery q:\n    let m:\n        capture nope\n"
        "        from rhs\n        select:\n            id\n    from lhs\n"
        "    where exists m\n    select:\n        a = id\n"
        "query s(y: Int not null):\n    union all:\n        from lhs\n"
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
            "        from rhs\n        inner join rhs as y:\n            from rhs\n"
            "            on rhs.id == y.id\n        where",
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    "row_let_body": (
        CAPTURE.replace(
            "        from rhs\n        where",
            "        from rhs\n        let:\n            k = key\n        where",
        ),
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # A typed VALUES body is admitted (S06), but never as a correlated body.
    "values_body": (
        "query q:\n    let m:\n        capture lhs\n"
        "        values(id: Int not null):\n            1\n"
        "    from lhs\n    where exists m\n    select:\n        a = lhs.id\n",
        [("PIE-S2370", BODY_SHAPE, 7, 5)],
    ),
    # A let with capture lines reads the entry query's header like any other
    # let of it (Phase70 S11); the read renders inside the EXISTS subquery.
    "header_parameter": (
        CAPTURE.replace("query q:", "query q(cut: Int not null):").replace(
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
            "    from lhs\n    let:\n        bumped = id + 1\n    where exists m\n",
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
            "    inner join m as x:\n        from lhs\n        on lhs.id == x.id\n",
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
        "query q:\n    let codes:\n        values(id: Int not null, key: Int nullable):\n"
        "            1, 2\n"
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
            # The relation facts restate it; it is reported once.
            ("PIE-S2102", "Unknown field: nosuch", 10, 15),
            (
                "PIE-S2369",
                "Captured field e.key is not yet available: the columns of e are "
                "not known before completion.",
                15,
                26,
            ),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                11,
                1,
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
        "table pairs:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id\n    select:\n        id = lhs.id\n"
        "        key = r.key\n" + CAPTURE.replace("lhs", "pairs"),
        [
            (
                "PIE-S2369",
                "Captured field pairs.key is not yet available: the columns of "
                "pairs are not known before completion.",
                18,
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
        "table pairs:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.id == r.id\n    select:\n        id = lhs.id\n"
        "        key = r.key\n"
        + CAPTURE.replace("lhs", "pairs").replace(
            "    where exists m\n",
            "    cross join m as x:\n        from pairs\n",
        ),
        [
            (
                "PIE-S2369",
                "Captured field pairs.key is not yet available: the columns of "
                "pairs are not known before completion.",
                18,
                26,
            ),
            # A JOIN of a let with an error leaves its body incomplete, as for
            # any let JOIN input.
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                14,
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
    "values": "query q:\n    let s:\n        values(id: Int not null):\n"
    "            1\n            2\n",
    "set": "query q:\n    let s:\n        union all:\n            from lhs\n"
    "            from rhs\n",
    "join": "query q:\n    let s:\n        from lhs\n        inner join rhs as r:\n"
    "            from lhs\n            on r.id == lhs.id\n        select:\n"
    "            id = r.id\n",
    "table": "table s:\n    values(id: Int not null):\n        1\nquery q:\n",
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
            SERIES_FROM
            + "    inner join lhs as l:\n        from n\n        on n.n == l.id\n",
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
        [
            (
                "PIE-S2348",
                SCALAR_POSITION.format("the SELECT of a grouped query"),
                19,
                13,
            ),
            UNAVAILABLE,
        ],
    ),
    "row_let_scalar": (
        CAPTURE.replace("    where exists m\n", "    let:\n        v = scalar m.id\n"),
        [("PIE-S2348", SCALAR_POSITION.format("a row let"), 15, 13)],
    ),
    "named_window_scalar": (
        CAPTURE.replace("    where exists m\n", "").replace(
            "        a = lhs.id\n",
            "        id\n        rn = row_number() window ordered\n"
            "    window ordered:\n        order by:\n            scalar m.id\n",
        ),
        [
            ("PIE-S2348", SCALAR_POSITION.format("a window"), 19, 13),
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
                16,
                14,
            ),
        ],
    ),
    "window_in": (
        CAPTURE.replace("    where exists m\n", "").replace(
            "        a = lhs.id\n",
            "        id\n        rn = row_number() window:\n"
            "            order by:\n                lhs.id in m\n",
        ),
        [
            ("PIE-S2350", IN_POSITION.format("a window"), 18, 17),
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
            "    inner join rhs as r:\n        from lhs\n        on lhs.id in m\n",
        ),
        [("PIE-S2350", IN_POSITION.format("JOIN ON"), 16, 12)],
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
    "ordered_read_by_exists": (_ordered("exists m"), [("PIE-S2370", BODY_SHAPE, 7, 5)]),
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
        [("PIE-S2370", BODY_SHAPE, 7, 5), ("PIE-S2370", READ_ONLY_BY_EXISTS, 18, 25)],
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
        "query q:\n    let m:\n        capture lhs\n        capture r\n"
        "        from rhs\n        where rhs.id == lhs.id and rhs.id == r.id\n"
        "        select:\n            id\n    from lhs\n"
        "    left join rhs as r:\n        from lhs\n        on lhs.id == r.id\n"
        "    where exists m\n    select:\n        a = lhs.id\n"
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
        .replace("on lhs.id == r.id", "on lhs.id == r.id and r.key is not null")
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
    "    from lhs\n    {kind} join m as x:\n        from lhs\n{on}"
    "    select:\n        a = lhs.id\n"
)
JOIN_KIND = "Let m with capture lines can be joined only by cross, inner or left join."


def _lateral(kind: str, on: str = "        on true\n") -> str:
    return LATERAL.format(kind=kind, on="" if kind == "cross" else on)


def _top_k(
    kind: str,
    *,
    on: str = "        on true\n",
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
    "right": (_lateral("right"), [("PIE-S2372", JOIN_KIND, 14, 5)]),
    "full": (_lateral("full"), [("PIE-S2372", JOIN_KIND, 14, 5)]),
    "semi": (_lateral("semi"), [("PIE-S2372", JOIN_KIND, 14, 5)]),
    "anti": (_lateral("anti"), [("PIE-S2372", JOIN_KIND, 14, 5)]),
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
            "    cross join rhs as z:\n        from lhs\n    select:\n        a",
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
            "    cross join m as y:\n        from lhs\n    select:\n        a",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 16, 5)],
    ),
    # A let joined LATERAL reads the entry query's header too (Phase70 S11).
    "header_parameter": (
        _lateral("cross")
        .replace("query q:", "query q(cut: Int not null):")
        .replace("rhs.key == lhs.key", "rhs.key == lhs.key and rhs.id > cut"),
        [],
    ),
    # A JOIN written in another let is nested correlation.
    "join_in_another_let": (
        _lateral("cross").replace(
            "    from lhs\n    cross join m as x:\n        from lhs\n",
            "    let other:\n        from rhs\n        cross join m as y:\n"
            "            from rhs\n        select:\n            id\n"
            "    from lhs\n    cross join other as x:\n        from lhs\n",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 15, 9)],
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
            (
                "PIE-S2334",
                "CROSS JOIN is available only when an EXPLICIT_MODULES "
                "project (schema version 2) completes it.",
                17,
                5,
            ),
            ("PIE-S2335", JOIN_ON, 17, 5),
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
        [UNAVAILABLE],
    ),
    "top_k_right": (_top_k("right"), [("PIE-S2372", JOIN_KIND, 17, 5)]),
    # Joined twice, the let keeps its LATERAL body rule; the second JOIN is
    # refused like any later read.
    "top_k_joined_twice": (
        _top_k("cross").replace(
            "    select:\n        a =",
            "    cross join m as y:\n        from lhs\n    select:\n        a =",
        ),
        [("PIE-S2370", READ_ONLY_BY_EXISTS, 19, 5)],
    ),
    "top_k_offset": (
        _top_k("cross", limit="        limit 2\n        offset 1\n"),
        [
            (
                "PIE-P1000",
                "Unknown clause 'offset'; a relation body lists from, joins, let:, "
                "where, group by:, select:, windows, satisfying:, qualify:, "
                "order by: and limit in that order.",
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
        "query q:\n    let m:\n        capture lhs\n        capture r\n"
        "        from rhs\n        where rhs.id == lhs.id and rhs.id == r.id\n"
        "        select:\n            id\n    from lhs\n"
        "    left join rhs as r:\n        from lhs\n        on lhs.id == r.id\n"
    )
    tail = (
        "    right join rhs as z:\n        from lhs\n        on z.id == lhs.id\n"
        "{where}    select:\n        a = z.id\n"
    )
    lateral = let + "    cross join m as x:\n        from lhs\n" + tail.format(where="")
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
        "query q:\n    let m:\n        capture lhs\n        from rhs\n"
        "        where rhs.key == lhs.key\n        select:\n            id\n"
        "    let n:\n        capture x\n        from rhs\n"
        "        where rhs.id == x.id\n        select:\n            id\n"
        "    let e:\n        capture x\n        from rhs\n"
        "        where rhs.id == x.id\n        select:\n            id\n"
        "    from lhs\n    left join m as x:\n        from lhs\n        on true\n"
        "    cross join n as y:\n        from lhs\n    where exists e\n"
        "    select:\n        a = lhs.id\n        b = x.id\n"
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
    "query p(c: Int not null):\n    from lhs\n    where id > c\n    select:\n"
    "        id\n"
    "query result:\n"
    "    let over:\n        from seed\n        select:\n            rid\n"
    "    let seed:\n        values(rid: Int not null):\n            1\n"
    "            2\n"
    "    let flags:\n        values(f: Bool nullable):\n            true\n"
    "            null\n"
    "    let spare:\n        values(rid: Int not null)\n"
    "    from lhs\n    inner join rhs as r:\n        from lhs\n"
    "        on lhs.id == r.id and exists flags\n"
    "    where lhs.id <= scalar over.rid and lhs.id in p\n"
    "    select:\n        a = lhs.id\n"
    "        n = row_number() window:\n            order by:\n"
    "                lhs.id\n"
    "    qualify:\n        n in seed\n"
)
POSITION = "relation reference is available only in WHERE and in the SELECT of an "


def test_refused_reads_of_values_lets_report_one_ordered_list(tmp_path: Path) -> None:
    assert _check(tmp_path, REFUSED_READS) == (
        1,
        [
            ("PIE-S2359", "Let relation spare is never read.", 24, 5),
            ("PIE-S2349", f"EXISTS {POSITION}ungrouped query, not in JOIN ON.", 29, 31),
            ("PIE-S2350", f"IN {POSITION}ungrouped query, not in QUALIFY.", 37, 9),
            (
                "PIE-S2348",
                "Scalar relation read over.rid is not yet available: the columns "
                "of over are not known before completion.",
                30,
                21,
            ),
            (
                "PIE-S2356",
                "A query with parameters cannot be the input of another relation.",
                30,
                41,
            ),
        ],
    )
