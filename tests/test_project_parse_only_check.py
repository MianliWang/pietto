from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import pietto.ir as ir_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
import pietto.sql.mysql as mysql_backend
from pietto._project.check import (
    check_legacy_flat_semantics,
    check_project_parse_only,
    project_recursion_limit_diagnostic,
)
from pietto._project.let_scope_facts import ProjectLetScopeFactsStatus
from pietto._project.model import (
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectRowFieldProvenanceKind,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import CallExpr, ComparisonExpr, QueryDef
from pietto.cli import main
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.parser_api import parse_source


def test_parse_only_project_check_parses_selected_sources_deterministically(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
    _write(root, "models/tmp/skip.pietto", "not parsed\n")

    result = check_project_parse_only(root)

    assert result.ok
    assert result.errors == ()
    assert result.diagnostics == ()
    assert result.inputs == (
        ProjectInput(path="models/a.pietto", status="parsed"),
        ProjectInput(path="models/z.pietto", status="parsed"),
        ProjectInput(path="root.pietto", status="parsed"),
    )


def test_parse_only_project_check_aggregates_project_relative_parser_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.errors == ()
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="models/good.pietto", status="parsed"),
    )
    assert result.diagnostics
    assert {diagnostic.location.path for diagnostic in result.diagnostics} == {
        "bad.pietto"
    }
    assert all(
        str(tmp_path) not in str(diagnostic) for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("schema", [1, 2], ids=["legacy_flat", "explicit_modules"])
def test_parse_only_project_check_adds_gate_diagnostics_beside_parse_errors(
    tmp_path: Path, schema: int
) -> None:
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", "table broken\n")
    _write(
        root,
        "b.pietto",
        "query q(a: Int):\n    from rows\n    select:\n        id\n"
        "query r:\n    from rows\n    where exists t and id == scalar t.c\n"
        "    select:\n        id\n"
        "type Age = Int:\n    ensure self > scalar t.c\n",
    )
    _write(root, "c.pietto", "query valid:\n    from rows\n    select:\n        id\n")

    result = check_project_parse_only(root)

    assert not result.ok and result.errors == ()
    assert result.inputs == (
        ProjectInput(path="a.pietto", status="error"),
        ProjectInput(path="b.pietto", status="parsed"),
        ProjectInput(path="c.pietto", status="parsed"),
    )
    paths = [diagnostic.location.path or "" for diagnostic in result.diagnostics]
    assert paths == sorted(paths) and set(paths) == {"a.pietto", "b.pietto"}
    assert {
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.location.path == "a.pietto"
    } == {"PIE-P1000"}
    # An explicit-module project admits a SELECT-body query header and the
    # relation reads inside a relation body; a read in a type rule stays gated.
    assert [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
        if diagnostic.location.path == "b.pietto"
    ] == [("PIE-S2346", 1, 9), ("PIE-S2349", 7, 11), ("PIE-S2348", 7, 30)] * (
        schema == 1
    ) + [("PIE-S2348", 11, 19)]


@pytest.mark.parametrize(
    ("schema", "expected"),
    ((1, (("PIE-S2801", 3, 5), ("PIE-S2801", 6, 18))), (2, ())),
)
def test_project_check_gates_collect_and_unnest_before_project_readers(
    tmp_path: Path, schema: int, expected: tuple[tuple[str, int, int], ...]
) -> None:
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(
        root,
        "nested.pietto",
        "query q:\n"
        "    from rows\n"
        "    let expanded = unnest(rows.children)\n"
        "    cross join expanded\n"
        "    select:\n"
        "        nested = collect children\n",
    )

    result = check_project_parse_only(root)

    assert [
        (d.code, d.location.line, d.location.column) for d in result.diagnostics
    ] == list(expected)


_RECURSION_LIMIT = "Semantic analysis recursion limit exceeded while processing source."


def test_parse_only_project_check_bounds_recursion_per_module(tmp_path: Path) -> None:
    # The capture checks of this LATERAL let used to raise RecursionError.
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    _write(root, "a.pietto", "query valid:\n    from rows\n    select:\n        id\n")
    condition = " and ".join(["ys.id == xs.id"] * 3000)
    _write(
        root,
        "b.pietto",
        "shape A:\n    id: Int\n"
        'source xs: A = postgres.table("xs")\n'
        'source ys: A = postgres.table("ys")\n'
        "query q:\n    let w:\n        capture xs\n        from ys\n"
        f"        where {condition}\n"
        "        select:\n            yid = id\n"
        "    from xs\n    let o = w\n    cross join o\n"
        "    select:\n        id\n        yid = o.yid\n",
    )

    result = check_project_parse_only(root)

    assert not result.ok and result.errors == ()
    assert result.inputs == (
        ProjectInput(path="a.pietto", status="parsed"),
        ProjectInput(path="b.pietto", status="parsed"),
    )
    assert result.diagnostics == (
        Diagnostic(
            code="PIE-S2006",
            severity=Severity.ERROR,
            message=_RECURSION_LIMIT,
            location=SourceLocation(
                path="b.pietto", line=1, column=1, end_line=17, end_column=20
            ),
        ),
    )


def test_recursion_limit_diagnostic_spans_the_first_most_nested_module(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    body = (
        "query {name}:\n    from rows\n    where {condition}\n    select:\n        id\n"
    )
    _write(root, "a.pietto", body.format(name="a", condition="id == 1"))
    _write(root, "b.pietto", body.format(name="b", condition="id == 1 and id == 2"))
    _write(root, "c.pietto", body.format(name="c", condition="id == 2 or id == 3"))

    result = check_project_parse_only(root)

    assert result.ok
    assert project_recursion_limit_diagnostic(result) == Diagnostic(
        code="PIE-S2006",
        severity=Severity.ERROR,
        message=_RECURSION_LIMIT,
        location=SourceLocation(
            path="b.pietto", line=1, column=1, end_line=5, end_column=11
        ),
    )


def test_recursion_limit_diagnostic_measures_modules_with_their_defs_inlined(
    tmp_path: Path,
) -> None:
    # As written, b.pietto nests deeper; with its six calls inlined, a.pietto
    # does, and every later reader walks the inlined module.
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    head = "shape Row:\n    id: Int\n" + ('source rows: Row = postgres.table("rows")\n')
    _write(
        root,
        "a.pietto",
        head + "def f(x: Int | None) -> Int | None: return (x + 1) * 2\n"
        "query a:\n    from rows\n    where f(f(f(f(f(f(id)))))) > 0\n"
        "    select:\n        id\n",
    )
    _write(
        root,
        "b.pietto",
        head.replace("rows", "others") + "query b:\n    from others\n"
        f"    where {'(' * 9}id{' + 1)' * 9} > 0\n    select:\n        id\n",
    )

    result = check_project_parse_only(root)

    assert result.ok
    assert project_recursion_limit_diagnostic(result) == Diagnostic(
        code="PIE-S2006",
        severity=Severity.ERROR,
        message=_RECURSION_LIMIT,
        location=SourceLocation(
            path="a.pietto", line=1, column=1, end_line=9, end_column=11
        ),
    )


def test_recursion_limit_diagnostic_measures_explicit_modules_as_normalized(
    tmp_path: Path,
) -> None:
    # Equal chains, a.pietto's in a SELECT item and b.pietto's in a query
    # let, which the project reads one level deeper as a `let:` binding; the
    # parsed scripts would tie and name a.pietto.
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    head = "shape Row:\n    id: Int\n" + ('source rows: Row = postgres.table("rows")\n')
    chain = "id + 1 + 1 + 1"
    _write(
        root,
        "a.pietto",
        head + f"query a:\n    from rows\n    select:\n        x = {chain}\n",
    )
    _write(
        root,
        "b.pietto",
        head.replace("rows", "others")
        + f"query b:\n    from others\n    let x = {chain}\n    select:\n        x\n",
    )

    result = check_project_parse_only(root)

    assert result.ok
    assert project_recursion_limit_diagnostic(result).location == SourceLocation(
        path="b.pietto", line=1, column=1, end_line=8, end_column=10
    )


def test_parse_only_project_check_reports_source_read_errors_and_continues(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    _write_bytes(root, "bad.pietto", b"\xff")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="good.pietto", status="parsed"),
    )
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.SOURCE_READ, "bad.pietto")
    ]
    assert result.diagnostics == ()


def test_parse_only_project_check_forwards_config_and_selection_errors(
    tmp_path: Path,
) -> None:
    missing_config_root = tmp_path / "missing-config"
    missing_config_root.mkdir()

    missing_config = check_project_parse_only(missing_config_root)

    assert missing_config.inputs == ()
    assert [error.kind for error in missing_config.errors] == [
        ProjectDiscoveryErrorKind.CONFIG_READ
    ]

    empty_selection_root = _project_root(
        tmp_path / "empty-selection", include=("*.pietto",)
    )

    empty_selection = check_project_parse_only(empty_selection_root)

    assert empty_selection.inputs == ()
    assert [error.kind for error in empty_selection.errors] == [
        ProjectDiscoveryErrorKind.PROJECT_GLOB
    ]


def test_parse_only_project_check_does_not_enter_compiler_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "semantically_invalid.pietto",
        "table report:\n    from missing\n    select:\n        id\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError(
            "parse-only project check must stop before compiler stages"
        )

    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(mysql_backend, "emit_mysql_sql", unexpected_call)

    result = check_project_parse_only(root)

    assert result.ok
    assert result.inputs == (
        ProjectInput(path="semantically_invalid.pietto", status="parsed"),
    )


FLAT_HEAD = (
    "shape User:\n"
    "    id: Int\n"
    "    score: Int\n"
    "    bonus: Int | None\n"
    'source users: User = postgres.table("users")\n'
)


def test_a_flat_project_resolves_query_names_in_its_shared_namespace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # The let of b.pietto names the source of a.pietto, as in one file.
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "a.pietto", FLAT_HEAD)
    _write(
        root,
        "b.pietto",
        "query totals:\n    let u = users\n    from u\n"
        "    let total = score + bonus\n    select:\n        total\n",
    )

    result = check_project_parse_only(root)

    assert result.ok and result.diagnostics == ()
    head, totals_input = result.parsed_inputs
    assert head.authored_script is None
    assert totals_input.authored_script is not None
    (authored,) = totals_input.authored_script.definitions
    (totals,) = totals_input.script.definitions
    assert isinstance(authored, QueryDef) and isinstance(totals, QueryDef)
    assert [item.name for item in authored.naming_declarations] == ["u", "total"]
    assert authored.let_clause is None
    assert totals.naming_declarations == ()
    assert (totals.from_clause.source_name, totals.from_clause.binding_name) == (
        "users",
        "u",
    )
    assert totals.let_clause is not None
    assert [
        (binding.name, binding.expression) for binding in totals.let_clause.bindings
    ] == [("total", authored.naming_declarations[1].expression)]
    assert all(
        module.parsed_input is parsed
        for module, parsed in zip(result.modules, result.parsed_inputs, strict=True)
    )

    semantic = build_empty_project_semantic_result(result)

    assert semantic.ok and semantic.model is not None
    assert (
        semantic.model.relation_let_scope_facts[totals].status
        is ProjectLetScopeFactsStatus.CONCRETE
    )
    fields = semantic.model.relation_row_schemas[totals].fields
    assert list(fields) == ["total"]
    assert fields["total"].resolved_type.name == "Int"
    assert fields["total"].provenance is not None
    assert fields["total"].provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED
    assert check_legacy_flat_semantics(semantic) == ((), True)
    assert main(["check", "--project", str(root)]) == 0
    assert capsys.readouterr().out == "Project check OK: .\nFiles checked: 2\n"


def test_a_flat_project_reports_query_name_errors_after_its_model_diagnostics(
    tmp_path: Path,
) -> None:
    # The model reads both lets of dup and its own let check leaves total
    # unknown; the analysis of the parsed files then reports each name error
    # at its let, as one file's analysis does.
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a.pietto",
        FLAT_HEAD + "query dup:\n    from users\n    let total = score\n"
        "    let total = bonus\n    select:\n        total\n"
        "query early:\n    let n = 1\n    from users\n    select:\n        id\n",
    )

    result = check_project_parse_only(root)

    assert result.ok and result.diagnostics == ()
    diagnostics, ok = check_legacy_flat_semantics(
        build_empty_project_semantic_result(result)
    )
    assert not ok
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ] == [
        ("PIE-S2102", "Unknown field: total", 11, 9),
        ("PIE-S2604", "Duplicate query local name: total", 9, 5),
        (
            "PIE-S2604",
            "A row-value let must follow FROM and every JOIN and precede WHERE",
            13,
            5,
        ),
    ]


def test_recursion_limit_diagnostic_measures_a_flat_project_as_parsed(
    tmp_path: Path,
) -> None:
    # Resolved, the let of b.pietto nests one level deeper than the same
    # condition in the WHERE of a.pietto; as parsed they tie.
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a.pietto",
        FLAT_HEAD
        + "query a:\n    from users\n    where id == 1\n    select:\n        id\n",
    )
    _write(
        root,
        "b.pietto",
        "query b:\n    from users\n    let big = id == 1\n    where big\n"
        "    select:\n        id\n",
    )

    result = check_project_parse_only(root)

    assert result.ok
    assert result.parsed_inputs[1].authored_script is not None
    assert project_recursion_limit_diagnostic(result) == Diagnostic(
        code="PIE-S2006",
        severity=Severity.ERROR,
        message=_RECURSION_LIMIT,
        location=SourceLocation(
            path="a.pietto", line=1, column=1, end_line=10, end_column=11
        ),
    )


DEF_HEAD = (
    "shape Row:\n"
    "    id: Int\n"
    "    n: Int | None\n"
    "    text: Text\n"
    "    row_key = unique(id)\n"
    "shape Other:\n"
    "    id: Int\n"
    "    row_id: Int\n"
    'source rows: Row = postgres.table("rows")\n'
    'source others: Other = postgres.table("others")\n'
    "def idi(x: Int) -> Int: return x\n"
    "def pos(x: Int | None) -> Bool | None: return x > 0\n"
)
# The first line written after DEF_HEAD.
DEF_LINE = 13


def _def_project(tmp_path: Path, source: str, schema: int = 2):
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        f'schema_version = {schema}\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(root, "a.pietto", DEF_HEAD + source)
    result = check_project_parse_only(root)
    assert result.errors == ()
    return [
        (diagnostic.code, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in result.diagnostics
    ], [diagnostic.message for diagnostic in result.diagnostics]


def test_a_flat_project_keeps_every_def_gated(tmp_path: Path) -> None:
    located, messages = _def_project(tmp_path, "", schema=1)
    assert located == [("PIE-S2379", DEF_LINE - 2, 1), ("PIE-S2379", DEF_LINE - 1, 1)]
    assert set(messages) == {
        "Inline `def` functions are available only in single files and "
        "EXPLICIT_MODULES projects (schema version 2)."
    }


DEF_POSITIONS = {
    "table_function": (
        "query q:\n    from generate_series(idi(1), 3, 1) as s\n"
        "    select:\n        s\n",
        [(DEF_LINE + 1, 26)],
        "in a table-function input",
    ),
    "table_function_itself": (
        "query q:\n    from idi(1) as s\n    select:\n        s\n",
        [(DEF_LINE + 1, 10)],
        "as a table function",
    ),
    "window_argument": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = lag(idi(n)) window(\n            order by id)\n",
        [(DEF_LINE + 4, 17)],
        "in a window computation",
    ),
    "window_key": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = row_number() window(\n            partition by idi(id)\n"
        "            order by idi(n))\n",
        [(DEF_LINE + 5, 26), (DEF_LINE + 6, 22)],
        "in a window computation",
    ),
    "window_frame": (
        "query q:\n    from rows\n    select:\n        id\n"
        "        r = sum(id) window(\n            order by id\n"
        "            rows between idi(1) preceding and current row)\n",
        [(DEF_LINE + 6, 26)],
        "in a window computation",
    ),
    "values_row": (
        "query q:\n    values(a: Int, b: Int):\n        idi(1), 2\n",
        [(DEF_LINE + 2, 9)],
        "in a VALUES row",
    ),
    "values_type_argument": (
        "query q:\n    values(a: Decimal(idi(9), 2)):\n        1\n",
        [(DEF_LINE + 1, 23)],
        "in a type argument",
    ),
}
# Two positions are retired with their spellings. Only the legacy
# `cast(x as T(...))` could put a type argument inside LIMIT (see
# test_a_retired_cast_type_argument_is_refused_before_any_def_check); a type
# argument inside another refused position is still named innermost, as
# values_type_argument shows. The condition of a source-bound relationship
# refused a def call; a typed relationship predicate inlines it instead (see
# test_a_def_call_in_a_relationship_predicate_is_inlined).


@pytest.mark.parametrize(
    ("source", "calls", "position"), DEF_POSITIONS.values(), ids=DEF_POSITIONS
)
def test_a_project_refuses_a_def_call_where_the_written_form_has_its_own_rule(
    tmp_path: Path, source: str, calls: list[tuple[int, int]], position: str
) -> None:
    located, messages = _def_project(tmp_path, source)
    assert located == [("PIE-S2397", line, column) for line, column in calls]
    assert set(messages) == {f"A def call is not available {position}: idi"}


# A def body can no longer hold a type argument: the legacy `cast(x as T(...))`
# was the only expression with one. A def call in a type argument is written
# in a declaration instead, such as a type alias, before or after that def,
# and no def reaches itself through a type argument any more, so the
# recursive vector is retired (see
# test_a_retired_cast_type_argument_is_refused_before_any_def_check).
TYPE_ARGUMENT_CALLS = {
    "called_before_its_def": (
        "type Amount = Decimal(g(9), 2)\ndef g(x: Int) -> Int: return x\n",
        [
            (
                "PIE-S2397",
                DEF_LINE,
                23,
                "A def call is not available in a type argument: g",
            )
        ],
    ),
    "called_after_its_def": (
        "def g(x: Int) -> Int: return x\ntype Amount = Decimal(g(9), 2)\n",
        [
            (
                "PIE-S2397",
                DEF_LINE + 1,
                23,
                "A def call is not available in a type argument: g",
            )
        ],
    ),
}


@pytest.mark.parametrize(
    ("defs", "expected"), TYPE_ARGUMENT_CALLS.values(), ids=TYPE_ARGUMENT_CALLS
)
def test_a_def_call_in_a_type_argument_is_refused_in_any_order(
    tmp_path: Path, defs: str, expected: list[tuple[str, int, int, str]]
) -> None:
    located, messages = _def_project(
        tmp_path,
        defs + "query q:\n    from rows\n    select:\n        v = g(id)\n",
    )
    assert [
        (*place, message) for place, message in zip(located, messages, strict=True)
    ] == expected


def test_a_retired_cast_type_argument_is_refused_before_any_def_check(
    tmp_path: Path,
) -> None:
    """The retired recursive vector as it was written: the parser refuses the
    legacy cast before any def is checked, so neither PIE-S2396 nor PIE-S2397
    is reached."""
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    _write(
        root,
        "a.pietto",
        DEF_HEAD + "def f(x: Int) -> Float: return cast(x as Float(f(1)))\n"
        "def g(x: Int) -> Int: return x\n"
        "query q:\n    from rows\n    select:\n        v = f(g(id))\n",
    )

    result = check_project_parse_only(root)

    assert (result.errors, result.inputs) == (
        (),
        (ProjectInput(path="a.pietto", status="error"),),
    )
    assert result.diagnostics == (
        Diagnostic(
            code="PIE-P1000",
            severity=Severity.ERROR,
            message="This spelling is not accepted by the modern syntax. "
            "Use 'Float(value)' for the supported Int-to-Float conversion; "
            "other conversions remain unsupported.",
            location=SourceLocation(path="a.pietto", line=DEF_LINE, column=32),
            suggestion=(
                "Use 'Float(value)' for the supported Int-to-Float conversion; "
                "other conversions remain unsupported."
            ),
        ),
    )


def test_a_def_call_in_a_relationship_predicate_is_inlined(tmp_path: Path) -> None:
    # A typed relationship predicate is an ordinary Bool expression, so a def
    # call there is inlined as anywhere else; the retired source-bound `on`
    # refused one (PIE-S2397, in a relationship condition).
    source = (
        DEF_HEAD + "relationship link(row: Row, other: Other):\n"
        "    idi(other.row_id) == row.id\n"
    )
    parsed = parse_source(source, path="a.pietto")
    assert parsed.ast is not None and parsed.diagnostics == ()
    (written,) = parsed.ast.relationship_templates
    assert isinstance(written.body, ComparisonExpr)
    assert isinstance(written.body.left, CallExpr)
    (argument,) = written.body.left.arguments
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    _write(root, "a.pietto", source)

    result = check_project_parse_only(root)

    assert (result.ok, result.errors, result.diagnostics) == (True, (), ())
    (module,) = result.parsed_inputs
    assert module.script.relationship_templates == (
        replace(written, body=replace(written.body, left=argument)),
    )


def test_a_def_argument_cannot_read_a_relation(tmp_path: Path) -> None:
    located, messages = _def_project(
        tmp_path,
        "query q:\n    let low:\n        from rows\n        select:\n"
        "            k = id\n    from rows\n    where pos(scalar low.k) and pos(id)\n"
        "    select:\n        id\n",
    )
    assert located == [("PIE-S2395", DEF_LINE + 6, 11)]
    assert messages == [
        "Invalid argument for def pos at position 1 (x): an argument cannot read "
        "a relation (exists, scalar or in) yet"
    ]


def test_a_def_body_reports_an_error_in_a_call_once(tmp_path: Path) -> None:
    """A body is checked at the def with the file's pre-admission diagnostics.
    The expansion finds an error in a call's argument at each use, which a
    single file reports at each; an explicit-module check reports a diagnostic
    equal to an earlier one once, at its first position."""
    located, messages = _def_project(
        tmp_path,
        "def twice(b: Bool | None) -> Bool | None: return b or b\n"
        "def h(y: Int | None) -> Bool | None: return twice(y == None)\n",
    )
    message = (
        "Invalid operands for operator ==: comparison with null is never true; "
        "write `is None` instead"
    )
    assert located == [("PIE-S2105", DEF_LINE + 1, 51)]
    assert messages == [message]


def test_a_def_cannot_be_an_export_item(tmp_path: Path) -> None:
    located, _ = _def_project(tmp_path, "export:\n    def idi\n")
    assert located == [("PIE-P1000", DEF_LINE + 1, 5)]


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
