"""Typed VALUES relations of explicit-module projects: admission and semantics.

A VALUES body is its own zero-input relation with an independent declared row
schema: built-in column types with explicit nullability, one fixed literal per
cell, at most 1,000 rows and 64 columns. It is available only in
EXPLICIT_MODULES projects; every rejected shape has its own deterministic
diagnostic at the authored span.
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
from pietto._project.model import (
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_final_outputs import ProjectCompletedValuesOutput
from pietto._project.project_values import ProjectValuesRelation
from pietto.ast_nodes import ValuesRelationDef

HEAD = """shape Row:
    id: Int
    key: Int | None
source lhs: Row = postgres.table("lhs")
"""


def _write(tmp_path: Path, body: str, config: str = probe.CONFIG) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(config)
    (tmp_path / "main.pietto").write_text(HEAD + body)
    return tmp_path


def _check(tmp_path: Path, body: str, *, config: str = probe.CONFIG):
    root = _write(tmp_path, body, config)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main(["check", "--project", str(root), "--format", "json"])
    return code, [
        (
            d["code"],
            d["message"],
            d["location"]["line"],
            d["location"]["column"],
            d["location"]["end_line"],
            d["location"]["end_column"],
        )
        for d in json.loads(out.getvalue())["diagnostics"]
    ]


def _completed(tmp_path: Path, body: str):
    root = _write(tmp_path, body)
    return build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )


TYPED = (
    "query q:\n"
    "    values(id: Int, f: Float | None, b: Bool,"
    " t: Text | None):\n"
    '        -9223372036854775808, -2.5, True, "it\'s"\n'
    "        1, None, False, None\n"
    "        1, None, False, None\n"
)


def test_a_values_body_is_a_typed_zero_input_relation(tmp_path: Path) -> None:
    completed = _completed(tmp_path, TYPED)
    assert completed.ok, completed.diagnostics
    assert completed.effective_outputs is not None
    (entry,) = (
        e
        for e in completed.effective_outputs.entries
        if type(e.owner.definition) is ValuesRelationDef
    )
    assert type(entry) is ProjectCompletedValuesOutput
    assert entry.dependencies == ()
    assert [
        (f.name, f.resolved_type.name, f.resolved_type.kind, f.nullability)
        for f in entry.schema.fields.values()
    ] == [
        (
            "id",
            "Int",
            ProjectResolvedTypeKind.BUILTIN,
            ProjectRowFieldNullability.NON_NULL,
        ),
        (
            "f",
            "Float",
            ProjectResolvedTypeKind.BUILTIN,
            ProjectRowFieldNullability.NULLABLE,
        ),
        (
            "b",
            "Bool",
            ProjectResolvedTypeKind.BUILTIN,
            ProjectRowFieldNullability.NON_NULL,
        ),
        (
            "t",
            "Text",
            ProjectResolvedTypeKind.BUILTIN,
            ProjectRowFieldNullability.NULLABLE,
        ),
    ]
    # Rows keep source order and duplicates; a signed number is one literal.
    assert isinstance(entry.root, ProjectValuesRelation)
    assert entry.root.rows == (
        (-(1 << 63), -2.5, True, "it's"),
        (1, None, False, None),
        (1, None, False, None),
    )


def test_a_zero_row_header_keeps_its_complete_typed_schema(tmp_path: Path) -> None:
    completed = _completed(
        tmp_path, "table empty:\n    values(id: Int, t: Text | None)\n"
    )
    assert completed.ok, completed.diagnostics
    assert completed.effective_outputs is not None
    (entry,) = (
        e
        for e in completed.effective_outputs.entries
        if type(e) is ProjectCompletedValuesOutput
    )
    assert isinstance(entry.root, ProjectValuesRelation)
    assert entry.root.rows == ()
    assert tuple(entry.schema.fields) == ("id", "t")


def test_a_let_values_body_is_read_like_any_relation(tmp_path: Path) -> None:
    body = (
        "query q:\n    let seed:\n        values(rid: Int):\n"
        "            1\n    from lhs\n    let s = seed\n"
        "    inner join s on lhs.id == s.rid\n    select:\n        id\n"
    )
    assert _check(tmp_path, body) == (0, [])


def test_a_row_level_let_reads_the_values_schema(tmp_path: Path) -> None:
    body = (
        "table seed:\n    values(id: Int, t: Text | None):\n"
        '        1, "a"\n'
        "query q:\n    from seed\n    let missing = t is None\n"
        "    where id > 0\n    select:\n        id\n        missing\n"
    )
    assert _check(tmp_path, body) == (0, [])


DIAGNOSTICS = {
    "duplicate_column": (
        'query q:\n    values(id: Int, id: Text | None):\n        1, "a"\n',
        [("PIE-S2001", "Duplicate VALUES column name 'id'.", 6, 21, 6, 36)],
    ),
    # A bare column type is never None, so only the Decimal column is refused.
    "column_types": (
        "query q:\n    values(id: Decimal, t: Text)\n",
        [
            (
                "PIE-S2361",
                "VALUES column type must be Bool, Int, Float or Text, optionally "
                "followed by '| None'.",
                6,
                16,
                6,
                23,
            ),
        ],
    ),
    "row_width": (
        "query q:\n    values(id: Int, t: Text | None):\n        1\n"
        '        1, "a", 3\n',
        [
            ("PIE-S2362", "VALUES row has 1 values for 2 columns.", 7, 9, 7, 10),
            ("PIE-S2362", "VALUES row has 3 values for 2 columns.", 8, 9, 8, 18),
        ],
    ),
    "row_let_unknown_field": (
        "table seed:\n    values(id: Int):\n        1\n"
        "query q:\n    from seed\n    let x = nope\n"
        "    select:\n        x\n",
        [("PIE-S2102", "Unknown field: nope", 10, 13, 10, 17)],
    ),
    "not_a_literal": (
        "query q:\n    values(id: Int, t: Text | None):\n"
        '        1 + 1, upper("a")\n        id, None\n',
        [
            (
                "PIE-S2363",
                "VALUES cells accept fixed literals only, not parameters or "
                "expressions.",
                *span,
            )
            for span in ((7, 9, 7, 14), (7, 16, 7, 26), (8, 9, 8, 11))
        ],
    ),
    "cell_type": (
        "query q:\n    values(id: Int, f: Float | None, b: Bool):\n"
        "        1.5, 1, 1\n        None, None, None\n"
        "        9223372036854775808, -1.0, True\n",
        [
            (
                "PIE-S2364",
                f"VALUES cell does not match column '{name}' declared {declared}.",
                *span,
            )
            for name, declared, span in (
                ("id", "Int", (7, 9, 7, 12)),
                ("f", "Float | None", (7, 14, 7, 15)),
                ("b", "Bool", (7, 17, 7, 18)),
                ("id", "Int", (8, 9, 8, 13)),
                ("b", "Bool", (8, 21, 8, 25)),
                ("id", "Int", (9, 9, 9, 28)),
            )
        ],
    ),
    "column_limit": (
        "query q:\n    values(" + ", ".join(f"c{i}: Int" for i in range(65)) + ")\n",
        [
            (
                "PIE-S2365",
                "VALUES allows at most 1000 rows and 64 columns.",
                6,
                5,
                6,
                651,
            )
        ],
    ),
    "row_limit": (
        "query q:\n    values(id: Int):\n" + "        1\n" * 1001,
        [
            (
                "PIE-S2365",
                "VALUES allows at most 1000 rows and 64 columns.",
                6,
                5,
                1007,
                10,
            )
        ],
    ),
    "unread_let": (
        "query q:\n    let v:\n        values(id: Int):\n            1\n"
        "    from lhs\n    select:\n        id\n",
        [("PIE-S2359", "Let relation v is never read.", 6, 5, 8, 14)],
    ),
}


@pytest.mark.parametrize("case", sorted(DIAGNOSTICS))
def test_each_rejected_values_shape_has_its_own_diagnostic(
    tmp_path: Path, case: str
) -> None:
    body, expected = DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1, expected)


SEED_LET = (
    "    let seed:\n        values(id: Int, t: Text | None):\n"
    '            1, "a"\n            2, None\n'
)
SEED_QUERY = 'query v:\n    values(id: Int, t: Text | None):\n        1, "a"\n'
COMPUTED_KEY = (
    "    let big = 1 if id > 1 else 0\n    group by:\n        big\n"
    "    select:\n        b = big\n        total = count()\n"
)
# A VALUES input keeps the limits of a set operation input: grouping over it,
# by a field or a computed key, with or without JOIN, has no completion yet.
GROUPED = {
    "computed_key_over_a_let": (
        "query q:\n" + SEED_LET + "    from seed\n" + COMPUTED_KEY,
        (5, 16),
    ),
    "computed_key_over_a_values_query": (
        SEED_QUERY + "query q:\n    from v\n" + COMPUTED_KEY,
        (8, 15),
    ),
    "field_key_over_a_values_query": (
        SEED_QUERY + "query q:\n    from v\n    group by:\n        id\n"
        "    select:\n        id\n        total = count()\n",
        (8, 14),
    ),
    "joined_computed_key_over_a_let": (
        "query q:\n"
        + SEED_LET
        + "    from lhs\n    let s = seed\n    inner join s on lhs.id == s.id\n"
        + COMPUTED_KEY.replace("if id", "if s.id"),
        (5, 18),
    ),
}


@pytest.mark.parametrize("case", sorted(GROUPED))
def test_grouping_over_a_values_input_is_refused(tmp_path: Path, case: str) -> None:
    body, (line, end_line) = GROUPED[case]
    message = "Project relation semantic completion is unavailable: q"
    assert _check(tmp_path, body) == (
        1,
        [("PIE-S2333", message, line, 1, end_line, 24)],
    )


def test_a_values_let_may_be_read_twice_and_forward(tmp_path: Path) -> None:
    lets = "".join(
        f"    let {name}:\n        from seed\n        where id {test}\n"
        "        select:\n            id\n"
        for name, test in (("a", "> 1"), ("b", "< 3"))
    )
    body = (
        "query q:\n"
        + lets
        + SEED_LET
        + "    union all:\n        from a\n        from b\n"
    )
    assert _check(tmp_path, body) == (0, [])


def test_at_the_static_bounds_a_values_body_is_accepted(tmp_path: Path) -> None:
    columns = ", ".join(f"c{i}: Int" for i in range(64))
    row = ", ".join("0" for _ in range(64))
    body = "query q:\n    values(" + columns + "):\n" + f"        {row}\n" * 1000
    assert _check(tmp_path, body) == (0, [])


@pytest.mark.parametrize("schema_version", (1, 2))
def test_values_is_available_only_in_explicit_module_projects(
    tmp_path: Path, schema_version: int
) -> None:
    config = probe.CONFIG.replace(
        "schema_version = 2", f"schema_version = {schema_version}"
    )
    code, diagnostics = _check(
        tmp_path, "query q:\n    values(id: Int):\n        1\n", config=config
    )
    if schema_version == 2:
        assert (code, diagnostics) == (0, [])
    else:
        assert (code, diagnostics) == (
            1,
            [
                (
                    "PIE-S2347",
                    "Typed VALUES bodies are available only in EXPLICIT_MODULES "
                    "projects (schema version 2).",
                    6,
                    5,
                    7,
                    10,
                )
            ],
        )
