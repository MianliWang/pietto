"""Bounded table-function inputs of explicit-module projects: admission and identity.

`from generate_series(start, stop, step) as n` is its own zero-input relation.
Its call, binding, one-column row schema, closed function identity and effects
evidence are kept apart: `n` names the rows and their only `Int`
column inside the body that wrote it and is never looked up as a relation name.
The three arguments are fixed int64 literals, the step is not zero and the
static row count is at most 1,048,576; every rejected shape has its own
deterministic diagnostic at the authored span.
"""

from __future__ import annotations

import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto import cli
from pietto._project import project_table_function as functions
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
from pietto.ast_nodes import TableFunctionRelationDef

HEAD = """shape Row:
    id: Int
source lhs: Row = postgres.table("lhs")
"""
NOT_A_FIXED_INTEGER = (
    "generate_series arguments are fixed non-null Int literals within the signed "
    "64-bit range, not parameters or expressions."
)
NOT_ADMITTED = "Only generate_series(Int, Int, Int) is an admitted table function."


def _write(tmp_path: Path, body: str, config: str = probe.CONFIG) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "pietto.toml").write_text(config)
    (tmp_path / "main.pietto").write_text(HEAD + body)
    return tmp_path


def _cli(*arguments: str) -> tuple[int, dict]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main([*arguments, "--format", "json"])
    return code, json.loads(out.getvalue())


def _diagnostics(document: dict) -> list[tuple[str, str, int, int, int, int]]:
    return [
        (
            d["code"],
            d["message"],
            d["location"]["line"],
            d["location"]["column"],
            d["location"]["end_line"],
            d["location"]["end_column"],
        )
        for d in document["diagnostics"]
    ]


def _check(tmp_path: Path, body: str, *, config: str = probe.CONFIG):
    code, document = _cli("check", "--project", str(_write(tmp_path, body, config)))
    return code, _diagnostics(document)


def _completed(tmp_path: Path, body: str):
    return build_project_completed_semantic_result(
        build_empty_project_semantic_result(
            check_project_parse_only(_write(tmp_path, body))
        )
    )


def _series(arguments: str, binding: str = "n") -> str:
    return (
        f"query q:\n    from generate_series({arguments}) as {binding}\n"
        f"    select:\n        {binding}\n"
    )


def test_a_series_is_a_typed_zero_input_relation_with_its_own_facts(
    tmp_path: Path,
) -> None:
    completed = _completed(tmp_path, _series("10, 1, -3", "k"))
    assert completed.ok, completed.diagnostics
    assert completed.effective_outputs is not None
    (entry,) = (
        e
        for e in completed.effective_outputs.entries
        if type(e.owner.definition) is TableFunctionRelationDef
    )
    assert type(entry) is ProjectCompletedValuesOutput
    assert entry.dependencies == ()
    root = entry.root
    assert isinstance(root, functions.ProjectTableFunctionRelation)
    assert root.signature is functions.GENERATE_SERIES
    assert functions.GENERATE_SERIES.identity == (
        "pg_catalog.generate_series(pg_catalog.int8,pg_catalog.int8,pg_catalog.int8)"
    )
    assert (root.arguments, root.row_count) == ((10, 1, -3), 4)
    # The binding is the only column: Int not null, from no relation or source.
    assert [
        (f.name, f.resolved_type.name, f.resolved_type.kind, f.nullability)
        for f in entry.schema.fields.values()
    ] == [
        (
            "k",
            "Int",
            ProjectResolvedTypeKind.BUILTIN,
            ProjectRowFieldNullability.NON_NULL,
        )
    ]
    # The occurrence is the function input itself, not a module declaration.
    owner = entry.owner
    assert owner.table_function is root.definition.source
    assert owner.authored is owner.table_function and owner.block_local
    assert owner.let_position is None


@pytest.mark.parametrize(
    ("arguments", "rows"),
    (
        ("1, 3, 1", 3),
        ("3, 1, -1", 3),
        ("1, 3, -1", 0),
        ("5, 5, 7", 1),
        ("1, 1048576, 1", 1_048_576),
        ("0, -1048575, -1", 1_048_576),
        ("-9223372036854775808, 9223372036854775807, 9223372036854775807", 3),
    ),
)
def test_the_static_row_count_is_exact_up_to_the_bound(
    tmp_path: Path, arguments: str, rows: int
) -> None:
    completed = _completed(tmp_path, _series(arguments))
    assert completed.ok, completed.diagnostics
    assert completed.effective_outputs is not None
    (entry,) = (
        e
        for e in completed.effective_outputs.entries
        if type(e) is ProjectCompletedValuesOutput
    )
    assert isinstance(entry.root, functions.ProjectTableFunctionRelation)
    assert entry.root.row_count == rows


FOLLOW_ON = ("PIE-S2333", "Project relation semantic completion is unavailable: q")
DIAGNOSTICS = {
    "other_function": (
        _series("1, 3, 1").replace("generate_series", "generate_seriez"),
        [("PIE-S2373", NOT_ADMITTED, 5, 10, 5, 25), (*FOLLOW_ON, 4, 1, 7, 10)],
    ),
    "too_few_arguments": (
        _series("1, 3"),
        [
            (
                "PIE-S2374",
                "generate_series takes exactly 3 arguments, not 2.",
                5,
                10,
                5,
                31,
            ),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    "no_arguments": (
        _series(""),
        [
            (
                "PIE-S2374",
                "generate_series takes exactly 3 arguments, not 0.",
                5,
                10,
                5,
                27,
            ),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    # NULL, a Float overload, a name or parameter: each argument at its span.
    "null_float_name": (
        _series("None, 1.5, x"),
        [
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 26, 5, 30),
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 32, 5, 35),
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 37, 5, 38),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    "expressions": (
        _series('1 + 1, True, "3"'),
        [
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 26, 5, 31),
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 33, 5, 37),
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 39, 5, 42),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    "int64_overflow": (
        _series("9223372036854775808, 1, 1"),
        [
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 26, 5, 45),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    # The step and the bound are derived only from three valid arguments.
    "invalid_argument_and_zero_step": (
        _series("None, 3, 0"),
        [
            ("PIE-S2375", NOT_A_FIXED_INTEGER, 5, 26, 5, 30),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    # As for a VALUES upstream, aggregating directly over the input waits.
    "aggregated": (
        "query q:\n    from generate_series(1, 3, 1) as n\n    select:\n"
        "        c = count()\n",
        [(*FOLLOW_ON, 4, 1, 7, 20)],
    ),
    "grouped": (
        "query q:\n    from generate_series(1, 3, 1) as n\n    group by:\n"
        "        n\n    select:\n        n\n        c = count()\n",
        [(*FOLLOW_ON, 4, 1, 10, 20)],
    ),
    "zero_step": (
        _series("1, 3, 0"),
        [
            ("PIE-S2376", "generate_series step cannot be zero.", 5, 32, 5, 33),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    "above_the_bound": (
        _series("1, 1048577, 1"),
        [
            (
                "PIE-S2377",
                "generate_series produces 1048577 rows; at most 1048576 are allowed.",
                5,
                10,
                5,
                40,
            ),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    "descending_above_the_bound": (
        _series("0, -1048576, -1"),
        [
            (
                "PIE-S2377",
                "generate_series produces 1048577 rows; at most 1048576 are allowed.",
                5,
                10,
                5,
                42,
            ),
            (*FOLLOW_ON, 4, 1, 7, 10),
        ],
    ),
    # Every body is analyzed on its own, in source order.
    "two_bodies": (
        _series("1, 3, 0")
        + "query r:\n    from generate_seriez(1) as m\n    select:\n        m\n",
        [
            ("PIE-S2376", "generate_series step cannot be zero.", 5, 32, 5, 33),
            (*FOLLOW_ON, 4, 1, 7, 10),
            ("PIE-S2373", NOT_ADMITTED, 9, 10, 9, 25),
            (
                "PIE-S2333",
                "Project relation semantic completion is unavailable: r",
                8,
                1,
                11,
                10,
            ),
        ],
    ),
    # A let named like a body's function binding shares its scope, as with a
    # JOIN binding: no winner, and the let then resolves to nothing.
    "let_named_like_the_binding": (
        "query q:\n    let n:\n        from lhs\n        select:\n            id\n"
        "    from generate_series(1, 3, 1) as n\n    select:\n        n\n",
        [
            (
                "PIE-S2001",
                "Duplicate symbol name in relation namespace: n",
                5,
                5,
                8,
                15,
            )
        ],
    ),
    "unknown_field": (
        _series("1, 3, 1").replace("        n\n", "        m\n"),
        [("PIE-S2102", "Unknown field: m", 7, 9, 7, 10)],
    ),
}


@pytest.mark.parametrize("case", sorted(DIAGNOSTICS))
def test_each_rejected_table_function_shape_has_its_own_diagnostic(
    tmp_path: Path, case: str
) -> None:
    body, expected = DIAGNOSTICS[case]
    assert _check(tmp_path, body) == (1, expected)


def test_a_binding_is_not_a_relation_name_in_any_scope(tmp_path: Path) -> None:
    """Two bodies bind `n` to their own calls; neither is read by name, the
    binding may equal its declaration's name, and the selected query reads its
    let by name only."""
    body = (
        "query n:\n    from generate_series(1, 3, 1) as n\n    select:\n        n\n"
        "query q:\n    let a:\n        from generate_series(1, 3, 1) as n\n"
        "        select:\n            n\n"
        "    from generate_series(1, 2, 1) as n\n    let t = a\n"
        "    inner join t on n.n == t.n\n    select:\n        x = n.n\n"
    )
    assert _check(tmp_path, body) == (0, [])
    completed = _completed(tmp_path / "facts", body)
    assert completed.effective_outputs is not None
    occurrences = [
        e.owner
        for e in completed.effective_outputs.entries
        if type(e.owner.definition) is TableFunctionRelationDef
    ]
    assert [(o.declaration_position, o.let_position) for o in occurrences] == [
        (2, None),
        (3, 0),
        (3, None),
    ]
    assert len({id(o.table_function) for o in occurrences}) == 3


def test_only_the_occurrence_flag_separates_a_function_input_from_its_reader(
    tmp_path: Path,
) -> None:
    """`query n` over `as n` shares its nominal identity and positions with its
    function input; the flag alone keeps both lineages, and only the reader is
    attributed as a declaration."""
    body = _series("1, 3, 1").replace("query q:", "query n:")
    semantic = build_empty_project_semantic_result(
        check_project_parse_only(_write(tmp_path, body))
    )
    facts = semantic.module_attribution_facts
    assert facts is not None
    function, reader = sorted(
        (
            lineage.owner
            for lineage in facts.row_lineages
            if lineage.owner.identity.declared_name == "n"
        ),
        key=lambda owner: not owner.table_function,
    )
    assert (function.table_function, reader.table_function) == (True, False)
    assert function != reader
    assert replace(function, table_function=False) == reader
    assert (function.block_local, reader.block_local) == (True, False)
    assert [len(facts.find_row_lineage(o)) for o in (function, reader)] == [1, 1]
    assert [
        d.identity
        for d in facts.declarations
        if d.identity.identity.declared_name == "n"
    ] == [reader]


@pytest.mark.parametrize(
    ("name", "expected"),
    (
        ("q", (0, "VERIFIED", None, [])),
        # A binding names rows inside its body only; it is never an owner.
        (
            "k",
            (
                2,
                "INPUT_REJECTED",
                [
                    {
                        "kind": "emission_selector",
                        "message": "Selected owner is absent or ambiguous.",
                        "path": None,
                    }
                ],
                [],
            ),
        ),
    ),
)
def test_only_declarations_are_selectable(
    tmp_path: Path, name: str, expected: tuple[object, ...]
) -> None:
    root = _write(tmp_path, _series("1, 3, 1", "k"))
    contract = json.loads(probe.join_witness("postgres", "")["contract"])
    contract["sources"] = []
    (root / "contract.json").write_text(json.dumps(contract))
    code, document = _cli(
        "emit-sql",
        "--project",
        str(root),
        "--module",
        "main.pietto",
        "--kind",
        "query",
        "--name",
        name,
        "--dialect",
        "postgres",
        "--emission-contract",
        "contract.json",
    )
    assert (
        code,
        document["status"],
        document.get("cli_errors"),
        _diagnostics(document),
    ) == expected


def test_admission_consumes_explicit_effects_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A08: a catalog entry whose determinism or side effects are unknown is
    not admitted, though its name, arguments and row bound are; existing
    scalar calls are untouched."""
    for change in (
        {"determinism": "unknown"},
        {"side_effects": "unknown"},
        {"determinism": "volatile"},
    ):
        unknown = functions.ProjectTableFunctionSignature(
            **{
                **{
                    name: getattr(functions.GENERATE_SERIES, name)
                    for name in functions.ProjectTableFunctionSignature.__dataclass_fields__
                },
                **change,
            }
        )
        monkeypatch.setitem(functions.CATALOG, "generate_series", unknown)
        assert _check(tmp_path / "series", _series("1, 3, 1")) == (
            1,
            [("PIE-S2373", NOT_ADMITTED, 5, 10, 5, 25), (*FOLLOW_ON, 4, 1, 7, 10)],
        )
        scalar = "query q:\n    from lhs\n    select:\n        k = sign(id)\n"
        assert _check(tmp_path / "scalar", scalar) == (0, [])


@pytest.mark.parametrize("schema_version", (1, 2))
def test_table_functions_are_available_only_in_explicit_module_projects(
    tmp_path: Path, schema_version: int
) -> None:
    config = probe.CONFIG.replace(
        "schema_version = 2", f"schema_version = {schema_version}"
    )
    code, diagnostics = _check(tmp_path, _series("1, 3, 1"), config=config)
    if schema_version == 2:
        assert (code, diagnostics) == (0, [])
    else:
        assert (code, diagnostics) == (
            1,
            [
                (
                    "PIE-S2352",
                    "Table-function FROM inputs are available only in "
                    "EXPLICIT_MODULES projects (schema version 2).",
                    5,
                    5,
                    5,
                    39,
                )
            ],
        )


@pytest.mark.parametrize(
    "command", (("check",), ("emit-sql", "--dialect", "postgres"), ("explain",))
)
def test_single_file_commands_keep_the_pre_admission_gate(
    tmp_path: Path, command: tuple[str, ...]
) -> None:
    path = tmp_path / "single.pietto"
    path.write_text(HEAD + _series("1, 3, 1"))
    code, document = _cli(command[0], str(path), *command[1:])
    assert (code, _diagnostics(document)) == (
        1,
        [
            (
                "PIE-S2352",
                "Table-function FROM inputs are available only in "
                "EXPLICIT_MODULES projects (schema version 2).",
                5,
                5,
                5,
                39,
            )
        ],
    )
