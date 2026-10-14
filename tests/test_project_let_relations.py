"""Closed relation lets of explicit-module projects: scope, identity, availability.

A let is its own owner with its own occurrence identity; it is never a module
declaration, shares one name scope with the module's relations and its
declaration's JOIN bindings, and until reuse is available is read exactly once
by a later let or by its declaration body.
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
    "unread": (
        "query q:\n" + LET + "    from lhs\n    select:\n        id\n",
        [
            (
                "PIE-S2345",
                "Let relation a is never read; an unread let is not yet available.",
                7,
                5,
            )
        ],
    ),
    "read_twice": (
        "query q:\n" + LET + "    from a\n    inner join a as b:\n        from a\n"
        "        on a.id == b.id\n    select:\n        id = a.id\n",
        [
            (
                "PIE-S2345",
                "Let relation a is read more than once; let reuse is not yet "
                "available.",
                7,
                5,
            ),
            ("PIE-S2334", "JOIN-local ON semantics are not implemented.", 14, 9),
            ("PIE-S2335", JOIN_ON, 12, 5),
            ("PIE-S2335", "JOIN ON reference is unavailable.", 14, 12),
            ("PIE-S2335", "JOIN ON reference is unavailable.", 14, 20),
        ],
    ),
    "forward": (
        "query q:\n    let b:\n        from a\n        select:\n            id\n"
        + LET
        + "    from b\n    select:\n        id\n",
        [
            (
                "PIE-S2345",
                "Let relation a is read before it is declared; a forward let read is "
                "not yet available.",
                11,
                5,
            ),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: b",
                7,
                5,
            ),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: q",
                6,
                1,
            ),
        ],
    ),
    "self": (
        "query q:\n    let a:\n        from a\n        select:\n            id\n"
        "    from lhs\n    select:\n        id\n",
        [
            (
                "PIE-S2345",
                "Let relation a is read before it is declared; a forward let read is "
                "not yet available.",
                7,
                5,
            ),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: a",
                7,
                5,
            ),
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
            (
                "PIE-S2345",
                "Let relation a is never read; an unread let is not yet available.",
                7,
                5,
            ),
            ("PIE-S2301", "Unknown relation: a", 16, 9),
            ("PIE-S2334", "Set-operation semantics are not implemented.", 15, 5),
        ],
    ),
    "values_body": (
        "query q:\n    let a:\n        values(id: Int not null):\n            1\n"
        "    from a\n    select:\n        id\n",
        [("PIE-S2347", "VALUES body semantics are not implemented.", 8, 9)],
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


def _let_chain(count: int) -> str:
    lets = "".join(
        f"    let l{i}:\n        from {'lhs' if i == 0 else f'l{i - 1}'}\n"
        "        select:\n            id\n"
        for i in range(count)
    )
    return f"query q:\n{lets}    from l{count - 1}\n    select:\n        id\n"


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
    assert _check(tmp_path, _let_chain(count)) == (
        (0, []) if count == 64 else (1, expected)
    )


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
