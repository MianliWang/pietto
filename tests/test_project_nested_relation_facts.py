"""Nested relation facts: typed Collect and Unnest occurrences (S03), Collect
admission, its read facts and the nested-field boundary (S04), before lowering
exists."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.nested_relation_facts import (
    ProjectNestedRelationFactReason,
    ProjectNestedRelationFactSet,
    ProjectNestedRelationFactStatus,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_pipeline import build_project_ir_pipeline
from pietto._project.project_row_equivalence import same_canonical_type
from pietto._project.project_row_keys import build_project_row_keys
from pietto._project.project_value_fds import build_project_value_fds
from pietto._syntax_admission import unnest_lets
from pietto.ast_nodes import QueryDef
from pietto.cli import main as cli_main


def _parsed_files(tmp_path: Path, sources: dict[str, str]) -> ProjectParseCheckResult:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for name, source in sources.items():
        (root / name).write_text(source, encoding="utf-8")
    return check_project_parse_only(root)


def _semantic_files(tmp_path: Path, sources: dict[str, str]) -> ProjectSemanticResult:
    parsed = _parsed_files(tmp_path, sources)
    assert parsed.ok, parsed.diagnostics
    return build_empty_project_semantic_result(parsed)


def _semantic(tmp_path: Path, source: str) -> ProjectSemanticResult:
    return _semantic_files(tmp_path, {"main.pietto": source})


def _facts(semantic: ProjectSemanticResult) -> ProjectNestedRelationFactSet:
    facts = semantic.nested_relation_facts
    assert facts is not None
    return facts


def _located(diagnostics) -> list[tuple[str, int, int]]:
    return [(d.code, d.location.line, d.location.column) for d in diagnostics]


def _checked(semantic: ProjectSemanticResult) -> list[tuple[str, int, int]]:
    """The project check's diagnostics: semantic, then completion."""

    return _located(build_project_completed_semantic_result(semantic).diagnostics)


HEAD = """shape Row:
    id: Int
    note: Text | None
source rows: Row = postgres.table("rows")
"""
# A collected let ends in ORDER BY (D71.03); these keep the line numbers of
# the block-SELECT form.
SOURCE = (
    HEAD
    + """query parent:
    let children:
        from rows
        select id, note
        order by:
            id
    from rows
    select:
        nested = collect children
"""
)
JOINED = (
    HEAD
    + """query joined:
    let children:
        from rows
        select id
        order by id
    let peer = rows
    from rows
    inner join peer on rows.id == peer.id
"""
)


def _expanded(join: str, binding: str = "parent") -> str:
    return (
        SOURCE
        + f"""query expanded:
    from parent
    let child = unnest({binding}.nested)
    {join}
    select:
        id
"""
    )


def test_collect_retains_one_layer_child_occurrences_and_scalar_boundary(
    tmp_path: Path,
) -> None:
    semantic = _semantic(tmp_path, SOURCE)

    facts = _facts(semantic)
    (collect,) = facts.collect_facts
    assert collect.status is ProjectNestedRelationFactStatus.AVAILABLE
    assert collect.reason is ProjectNestedRelationFactReason.SCALAR_BOUNDARY
    assert collect.nested_type is not None
    assert collect.output is not None
    assert collect.output.name == "nested"
    assert collect.target == collect.nested_type.element_relation
    assert collect.nested_type.collection_depth == 1
    # A direct Collect is never None; its field, not its type, says so (S04).
    assert not hasattr(collect.nested_type, "container_nullability")
    assert [field.identity.name for field in collect.nested_type.element_fields] == [
        "id",
        "note",
    ]
    assert [
        field.field.nullability.value for field in collect.nested_type.element_fields
    ] == [
        "non_null",
        "nullable",
    ]
    assert _located(facts.diagnostics) == [("PIE-S2802", 13, 18)]
    assert not semantic.ok
    # The relation's own Collect read reports it; no completion fallback.
    assert _checked(semantic) == [("PIE-S2802", 13, 18)]


@pytest.mark.parametrize(
    "sibling",
    ["incremented = id + 1", "bad = note + 1"],
    ids=["scalar", "erroneous"],
)
def test_collect_quarantines_only_the_nested_output_from_scalar_inference(
    tmp_path: Path, sibling: str
) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE.replace(
            "nested = collect children", f"nested = collect children\n        {sibling}"
        ),
    )

    assert _located(semantic.diagnostics) == [("PIE-S2802", 13, 18)]
    assert _checked(semantic) == [("PIE-S2802", 13, 18)] + (
        [("PIE-S2105", 14, 15)] if sibling.startswith("bad") else []
    )


@pytest.mark.parametrize(
    "tail",
    [
        "    select:\n        rows.id\n        nested = collect children\n",
        "    select:\n        rows.id\n        bad = rows.note + 1\n"
        "        nested = collect children\n",
        "    where rows.id > 1\n    select:\n        rows.id\n"
        "        nested = collect children\n    order by rows.id\n    limit 3\n",
        "    select distinct:\n        rows.id\n        nested = collect children\n",
        "    group by rows.id\n    select:\n        rows.id\n        n = count()\n"
        "        nested = collect children\n",
        "    select:\n        n = count()\n        nested = collect children\n",
        "    select:\n        rows.id\n"
        "        r = row_number() window(order by rows.id)\n"
        "        nested = collect children\n    qualify:\n        r == 1\n",
    ],
    ids=["plain", "sibling-error", "tail", "distinct", "grouped", "global", "window"],
)
def test_joined_collect_owner_completes_or_reports_its_own_diagnostics(
    tmp_path: Path, tail: str
) -> None:
    # S04: a JOIN relation with a Collect read completes like any other; a
    # grouped or global SELECT refuses the read (PIE-S2803) before PIE-S2802,
    # and SELECT DISTINCT cannot compare it (PIE-S2805).
    semantic = _semantic(tmp_path, JOINED + tail)

    (collect,) = _facts(semantic).collect_facts
    line = 13 + tail.count("\n", 0, tail.index("collect children"))
    expected = {
        "    select:\n        rows.id\n        nested": [("PIE-S2802", line, 18)],
        "    select:\n        rows.id\n        bad": [
            ("PIE-S2802", line, 18),
            ("PIE-S2105", 15, 15),
        ],
        "    where": [("PIE-S2802", line, 18)],
        "    select distinct": [("PIE-S2802", line, 18), ("PIE-S2805", line, 18)],
        "    group by": [("PIE-S2803", line, 18), ("PIE-S2802", line, 18)],
        "    select:\n        n = count()": [
            ("PIE-S2803", line, 18),
            ("PIE-S2802", line, 18),
        ],
        "    select:\n        rows.id\n        r =": [("PIE-S2802", line, 18)],
    }
    (diagnostics,) = (value for key, value in expected.items() if tail.startswith(key))
    assert _checked(semantic) == diagnostics
    refused = diagnostics[0][0] == "PIE-S2803"
    assert (collect.status is ProjectNestedRelationFactStatus.AVAILABLE) is not refused


def test_a_reader_selecting_a_collect_output_reports_the_nested_field(
    tmp_path: Path,
) -> None:
    # The Collect owner completes (S04), so its reader reads its nested field
    # and is told only the collecting relation outputs it yet; no fallback.
    semantic = _semantic(
        tmp_path,
        SOURCE + "query reader:\n    from parent\n    select:\n        nested\n",
    )

    assert _checked(semantic) == [("PIE-S2802", 13, 18), ("PIE-S2805", 17, 9)]
    # The refused selection leaves the reader's row unknown, as any SELECT
    # item with an error of its own does, so a relation reading it follows
    # its reported error and never reads the nested field again.
    assert _relation_facts(semantic, "reader").state.status.value == "unknown"
    downstream = _semantic(
        tmp_path / "down",
        SOURCE + "query reader:\n    from parent\n    select:\n        id = nested\n"
        "query down:\n    from reader\n    where id == 1\n    select:\n        id\n",
    )
    assert _checked(downstream) == [
        ("PIE-S2802", 13, 18),
        ("PIE-S2805", 17, 14),
    ]


@pytest.mark.parametrize(
    ("select", "reason", "target"),
    [
        ("nested = collect base", "target_not_local_let", "base"),
        ("nested = collect ghost", "target_unavailable", None),
        (
            "nested = collect children\n        nested = id",
            "output_unavailable",
            "children",
        ),
    ],
    ids=["module-relation", "unknown", "output-collision"],
)
def test_unavailable_collect_retains_its_resolved_target_and_exact_reason(
    tmp_path: Path, select: str, reason: str, target: str | None
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD
        + "query base:\n    from rows\n    select:\n        id\n"
        + SOURCE.removeprefix(HEAD).replace("nested = collect children", select),
    )

    (collect,) = _facts(semantic).collect_facts
    assert collect.status is ProjectNestedRelationFactStatus.UNAVAILABLE
    assert collect.reason.value == reason
    assert collect.nested_type is None
    assert (
        None if collect.target is None else collect.target.identity.declared_name
    ) == target


def test_unnest_retains_the_exact_nested_output_occurrence(tmp_path: Path) -> None:
    semantic = _semantic(tmp_path, _expanded("cross join child"))

    facts = _facts(semantic)
    (collect,) = facts.collect_facts
    (unnest,) = facts.unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE
    # S05 (D-S05-7): the Unnest's link is the S04 Collect read fact itself.
    assert unnest.source_field == collect.output
    assert unnest.collect_read is collect.collect_read
    assert unnest.nested_type is collect.nested_type
    assert unnest.query_let.name == "child"
    assert _located(facts.diagnostics) == [("PIE-S2802", 13, 18), ("PIE-S2802", 16, 5)]


def test_unnest_resolves_the_authored_from_alias_not_the_source_name(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE
        + """query expanded:
    let p = parent
    from p
    let child = unnest(p.nested)
    cross join child
    select:
        id
""",
    )
    (unnest,) = _facts(semantic).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE
    assert unnest.source_binding_name == "p"
    assert unnest.source_target is not None
    assert len(unnest.binding_candidates) == 1
    assert unnest.source_target.target_occurrence.identity.declared_name == "parent"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            _expanded("cross join child", binding="ghost"),
            ("PIE-S2806", 16, 24, "ghost.nested", "ghost", "child"),
        ),
        (
            SOURCE
            + """query expanded:
    let p = parent
    let child = unnest(p.nested)
    from p
    cross join child
    select:
        id
""",
            ("PIE-S2806", 16, 24, "p.nested", "p", "child"),
        ),
    ],
    ids=["unknown-binding", "binding-after-let"],
)
def test_unnest_without_a_row_binding_written_before_it_is_refused_first(
    tmp_path: Path, source: str, expected: tuple[str, int, int, str, str, str]
) -> None:
    # S05 (D-S05-2): a binding that is no FROM or earlier JOIN binding is
    # refused before semantics (PIE-S2806 B1), so no fact claims it.
    code, line, column, argument, binding, let = expected
    parsed = _parsed_files(tmp_path, {"main.pietto": source})
    assert [
        (d.code, d.location.line, d.location.column, d.message, d.suggestion)
        for d in parsed.diagnostics
    ] == [
        (
            code,
            line,
            column,
            f"Unnest argument {argument} is not available: {binding} is not the "
            f"FROM input or a CROSS, INNER or LEFT JOIN written before let {let}.",
            f"Write `let {let} = unnest(binding.field)` after the FROM or JOIN "
            "whose binding has the nested field.",
        )
    ]


@pytest.mark.parametrize(
    ("sources", "candidates"),
    [
        (
            {
                "main.pietto": SOURCE
                + """query expanded:
    from ghost
    let child = unnest(ghost.nested)
    cross join child
    select:
        id
"""
            },
            1,
        ),
        # The visible FROM input is blocked by an import collision
        # (PIE-S2706): the binding is retained, not dropped as unknown.
        (
            {
                "a.pietto": SOURCE + "export (\n    query parent,\n)\n",
                "b.pietto": 'from "a.pietto" import (\n    query parent,\n)\n'
                + HEAD.replace("rows", "others").replace("Row", "Other")
                + "query parent:\n    from others\n    select:\n        id\n"
                + _expanded("cross join child").removeprefix(SOURCE),
            },
            1,
        ),
    ],
    ids=["unknown-input", "blocked-input"],
)
def test_unnest_without_one_resolved_binding_retains_its_visible_inputs(
    tmp_path: Path, sources: dict[str, str], candidates: int
) -> None:
    # A visible binding whose relation does not resolve is kept as None, and
    # neither case claims a nested output it never resolved.
    facts = _facts(_semantic_files(tmp_path, sources))
    (unnest,) = (
        item
        for item in facts.unnest_inputs
        if item.owner.identity.declared_name == "expanded"
    )
    assert unnest.status is ProjectNestedRelationFactStatus.UNAVAILABLE
    assert unnest.reason is ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
    assert unnest.source_target is None and unnest.source_field is None
    assert unnest.binding_candidates == (None,) * candidates


def test_unnest_resolves_a_preceding_join_binding(tmp_path: Path) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE
        + """query expanded:
    from parent
    let p = parent
    inner join p on parent.id == p.id
    let child = unnest(p.nested)
    cross join child
    select:
        id
""",
    )
    (unnest,) = _facts(semantic).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE
    assert unnest.source_binding_name == "p"
    assert unnest.source_target is not None


def test_unnest_with_multiple_join_candidates_is_unavailable_not_first_match(
    tmp_path: Path,
) -> None:
    # S05 (D-S05-4): one JOIN reads an Unnest; every later one is refused
    # before semantics (PIE-S2807 M), and none wins.
    parsed = _parsed_files(
        tmp_path,
        {"main.pietto": _expanded("cross join child\n    left join child on True")},
    )

    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in parsed.diagnostics
    ] == [
        (
            "PIE-S2807",
            18,
            5,
            "Unnest child is joined more than once: one JOIN reads an Unnest.",
        )
    ]


_WRITE_ON = (
    "PIE-S2333",
    "Project relation semantic completion is unavailable: expanded "
    "(JOIN child: write `on` with the condition that matches parent to child)",
)
_UNNEST_GATE = (
    "Unnest relation reads are not supported by the current scalar-only project "
    "boundary."
)


def _messages(semantic: ProjectSemanticResult) -> list[tuple[str, int, int, str]]:
    return [
        (d.code, d.location.line, d.location.column, d.message)
        for d in build_project_completed_semantic_result(semantic).diagnostics
    ]


def _beside_alias(
    tmp_path: Path, source: str
) -> tuple[list[tuple[str, int, int, str]], list[tuple[str, int, int, str]]]:
    """The checked diagnostics of ``source`` and of its alias-let control.

    S05 (D-S05-1): the control reads `kids`, a query of the collected let's
    fields appended after every line, through an alias let in the Unnest's
    place; its write-on hints name `kids` where the Unnest's name its let.
    """

    unnest = _messages(_semantic(tmp_path / "unnest", source))
    alias = _messages(
        _semantic(
            tmp_path / "alias",
            source.replace("unnest(parent.nested)", "kids")
            + "query kids:\n    from rows\n    select id, note\n",
        )
    )
    return unnest, [
        (code, line, column, message.replace(" to kids)", " to child)"))
        for code, line, column, message in alias
    ]


@pytest.mark.parametrize(
    "join",
    [
        "cross join child",
        "cross join child on True",
        "inner join child",
        "inner join child on True",
        "left join child",
        "left join child on True",
        "right join child",
        "right join child on True",
        "full join child",
    ],
)
def test_an_unnest_join_reports_what_a_join_of_an_alias_let_reports(
    tmp_path: Path, join: str
) -> None:
    # S05 (D-S05-1, PIE-S2802 row): a CROSS, INNER or LEFT Unnest JOIN reads
    # the rows of its nested field in its place, so it reports what a JOIN of
    # an alias let of the same fields reports, in the same order, after its
    # gate; a JOIN without `on` of another kind than CROSS names the inputs
    # its `on` would match. A RIGHT or FULL one is refused before semantics
    # (PIE-S2807 K, D71.04).
    if join.startswith(("right", "full")):
        parsed = _parsed_files(tmp_path, {"main.pietto": _expanded(join)})
        assert [
            (d.code, d.location.line, d.location.column, d.message, d.suggestion)
            for d in parsed.diagnostics
        ] == [
            (
                "PIE-S2807",
                17,
                5,
                "Unnest child can be joined only by cross, inner or left join.",
                "Write `cross join child`, `inner join child on ...` or "
                "`left join child on True`.",
            )
        ]
        return
    unnest, alias = _beside_alias(tmp_path, _expanded(join))

    gate = ("PIE-S2802", 16, 5, _UNNEST_GATE)
    hint = ("PIE-S2333", 17, 5, _WRITE_ON[1])
    writes_on = not join.startswith("cross") and " on " not in join
    cross_on = join == "cross join child on True"
    assert unnest == [alias[0], gate, *alias[1:]]
    assert (hint in unnest) is writes_on
    assert (("PIE-S2336", 17, 5, "CROSS JOIN cannot have ON or VIA.") in unnest) is (
        cross_on
    )
    # A legal Unnest JOIN reports only the lowering boundary (AC-03).
    assert len(unnest) == 2 + writes_on + cross_on


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # A table-function FROM has no nested field (S05, PIE-S2806).
        (
            "query q:\n    from generate_series(1, 3, 1) as n\n"
            "    let child = unnest(n.nested)\n    cross join child\n"
            "    select:\n        v = n.value\n",
            ("PIE-S2806", 16, 24),
        ),
        # A relation let beside the Unnest let.
        (
            "query q:\n    let extra:\n        from rows\n        select:\n"
            "            id\n    from parent\n    let child = unnest(parent.nested)\n"
            "    cross join child\n    where parent.id in extra\n"
            "    select:\n        id = parent.id\n",
            ("PIE-S2802", 20, 5),
        ),
        # An Unnest let inside a relation let is refused before semantics
        # (S05, PIE-S2807).
        (
            "query q:\n    let sub:\n        from parent\n"
            "        let child = unnest(parent.nested)\n        cross join child\n"
            "        select:\n            id = parent.id\n    from sub\n"
            "    select:\n        id\n",
            ("PIE-S2807", 17, 9),
        ),
    ],
)
def test_an_unnest_join_of_a_block_body_is_no_unknown_relation(
    tmp_path: Path, body: str, expected: tuple[str, int, int]
) -> None:
    # D71.02 holds in every relation body: the JOIN is the Unnest let's one
    # input in its place, never a named relation the module lacks.
    parsed = _parsed_files(tmp_path / "parsed", {"main.pietto": SOURCE + body})
    checked = (
        _checked(_semantic(tmp_path, SOURCE + body))
        if parsed.ok
        else [
            (d.code, d.location.line, d.location.column)
            for d in parsed.diagnostics
            if d.location is not None
        ]
    )

    assert "PIE-S2301" not in {code for code, _, _ in checked}
    assert expected in checked


def test_unnest_join_diagnostics_take_the_completion_place_of_any_join(
    tmp_path: Path,
) -> None:
    semantic = _semantic_files(
        tmp_path,
        {
            "a.pietto": HEAD.replace("rows", "others").replace("Row", "Other")
            + "query plain:\n    let peer = others\n    from others\n"
            "    inner join peer\n    select:\n        id\n",
            "b.pietto": _expanded("inner join child"),
        },
    )

    checked = [
        (d.code, d.location.path, d.location.line)
        for d in build_project_completed_semantic_result(semantic).diagnostics
    ]
    # Both JOINs without `on` report in the completion stage, in its relation
    # order, after every semantic-stage diagnostic.
    assert checked == [
        ("PIE-S2802", "b.pietto", 13),
        ("PIE-S2802", "b.pietto", 16),
        ("PIE-S2333", "a.pietto", 8),
        ("PIE-S2333", "b.pietto", 17),
    ]


def test_joins_beside_an_unnest_join_name_it_in_source_order(tmp_path: Path) -> None:
    # Each JOIN reports in its written place, and a later JOIN without `on`
    # names the Unnest binding among the inputs its `on` would match, as it
    # names an alias let's.
    unnest, alias = _beside_alias(
        tmp_path,
        SOURCE
        + "query expanded:\n    from parent\n"
        + "    let child = unnest(parent.nested)\n    inner join child\n"
        + "    let other = rows\n    left join other\n"
        + "    select:\n        id\n",
    )

    later = (
        "PIE-S2333",
        19,
        5,
        "Project relation semantic completion is unavailable: expanded "
        "(JOIN other: write `on` with the condition that matches parent or child "
        "to rows)",
    )
    hint = ("PIE-S2333", 17, 5, _WRITE_ON[1])
    assert alias[1:] == [hint, later]
    assert unnest == [alias[0], ("PIE-S2802", 16, 5, _UNNEST_GATE), hint, later]


@pytest.mark.parametrize(
    ("body", "let_line"),
    [
        (
            "    let c = rows\n    inner join c\n"
            "    let child = unnest(parent.nested)\n    cross join child\n"
            "    let d = rows\n    left join d\n",
            18,
        ),
        (
            "    let child = unnest(parent.nested)\n    cross join child\n"
            "    let c = rows\n    inner join c on c.id == child.id\n",
            16,
        ),
        (
            "    let child = unnest(parent.nested)\n    cross join child on True\n"
            "    let x = rows\n    left join x\n",
            16,
        ),
    ],
    ids=["between-joins", "on-reads-it", "cross-on-first"],
)
def test_joins_beside_an_unnest_join_report_what_they_report_beside_an_alias_let(
    tmp_path: Path, body: str, let_line: int
) -> None:
    # The Unnest JOIN stays one JOIN input in its place (D71.02), bound to its
    # occurrence (S05): every JOIN of the relation reports what it reports
    # beside an alias let in that place, in the same order.
    unnest, alias = _beside_alias(
        tmp_path,
        SOURCE
        + "query expanded:\n    from parent\n"
        + body
        + "    select:\n        id\n",
    )

    assert unnest == [alias[0], ("PIE-S2802", let_line, 5, _UNNEST_GATE), *alias[1:]]
    assert not any("unknown" in message for _, _, _, message in unnest)


def test_an_unnest_beside_a_where_any_is_refused_before_semantics(
    tmp_path: Path,
) -> None:
    # S05 (D-S05-4): `any(...)` beside an Unnest in one body is PIE-S2807 S,
    # the S03 after-any shape.
    parsed = _parsed_files(
        tmp_path,
        {
            "main.pietto": SOURCE + "query expanded:\n    from parent\n"
            "    where any(r.id == 1 for r in rows)\n"
            "    let child = unnest(parent.nested)\n    cross join child\n"
            "    let c = rows\n    left join c on c.id == child.id\n"
            "    select:\n        id\n"
        },
    )

    assert [
        (d.code, d.location.line, d.location.column) for d in parsed.diagnostics
    ] == [("PIE-S2807", 17, 5)]
    assert "beside any(...)" in parsed.diagnostics[0].message


@pytest.mark.parametrize(
    "join", ["inner join child on True", "left join child on True"]
)
def test_unnest_inner_and_left_joins_with_on_are_available(
    tmp_path: Path, join: str
) -> None:
    (unnest,) = _facts(_semantic(tmp_path, _expanded(join))).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            HEAD + "query q:\n    from rows\n    let x = unnest(rows.note)\n"
            "    select:\n        id\n        y = x\n",
            [("PIE-S2103", 7, 13)],
        ),
        (
            HEAD + "def unnest(value: Text | None) -> Text | None: return value\n"
            "query q:\n    from rows\n    let child = unnest(rows.note)\n"
            "    cross join child\n    select:\n        id\n",
            None,
        ),
    ],
    ids=["not-a-join-target", "local-def"],
)
def test_an_ordinary_unnest_call_is_no_nested_input(
    tmp_path: Path, source: str, expected: list[tuple[str, int, int]] | None
) -> None:
    root = tmp_path / "project"
    if expected is None:
        # A local `def unnest` keeps the 0.1.5 meaning: a row-value let the
        # JOIN cannot read, refused before semantics.
        root.mkdir()
        (root / "pietto.toml").write_text(
            'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n',
            encoding="utf-8",
        )
        (root / "main.pietto").write_text(source, encoding="utf-8")
        assert [d.code for d in check_project_parse_only(root).diagnostics] == [
            "PIE-S2604"
        ]
        return
    semantic = _semantic(tmp_path, source)

    assert _facts(semantic).unnest_inputs == ()
    assert _checked(semantic) == expected


def test_a_let_name_declared_twice_is_no_unnest_let(tmp_path: Path) -> None:
    # No candidate wins the JOIN, so each let keeps the 0.1.5 meaning of a
    # row-value let the JOIN cannot read, refused before semantics.
    let = "    let child = unnest(rows.note)\n"
    parsed = _parsed_files(
        tmp_path,
        {
            "main.pietto": HEAD
            + "query q:\n    from rows\n"
            + let
            + let
            + "    cross join child\n    select:\n        id\n"
        },
    )

    row_value = "A row-value let must follow FROM and every JOIN and precede WHERE"
    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in parsed.diagnostics
    ] == [
        ("PIE-S2604", 7, 5, row_value),
        ("PIE-S2604", 8, 5, "Duplicate query local name: child"),
        ("PIE-S2604", 8, 5, row_value),
    ]


def test_another_modules_unnest_def_does_not_shadow_the_nested_form(
    tmp_path: Path,
) -> None:
    semantic = _semantic_files(
        tmp_path,
        {
            "a.pietto": "def unnest(value: Int) -> Int: return value\n",
            "main.pietto": _expanded("cross join child"),
        },
    )

    (unnest,) = _facts(semantic).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE


@pytest.mark.parametrize("type_name", ["Any", "Bytes", "Json"])
def test_collect_rejects_non_admitted_builtin_child_leaves(
    tmp_path: Path, type_name: str
) -> None:
    semantic = _semantic(tmp_path, SOURCE.replace("id: Int", f"id: {type_name}"))

    (collect,) = _facts(semantic).collect_facts
    assert collect.status is ProjectNestedRelationFactStatus.UNAVAILABLE
    assert collect.reason is ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
    assert collect.nested_type is None


def test_table_function_bodies_keep_one_collect_occurrence(tmp_path: Path) -> None:
    body = """query q:
    let children:
        from rows
        select:
            id
    from generate_series(1, 3, 1) as n
    let child = unnest(n.nested)
    cross join child
    select:
        n
        nested = collect children
"""
    # S05 (D-S05-4): the Unnest beside that Collect read is refused before
    # semantics (PIE-S2807 S).
    parsed = _parsed_files(tmp_path / "beside", {"main.pietto": HEAD + body})
    assert [
        (d.code, d.location.line, d.location.column) for d in parsed.diagnostics
    ] == [("PIE-S2807", 11, 5)]
    assert "beside a Collect read" in parsed.diagnostics[0].message
    semantic = _semantic(
        tmp_path,
        HEAD
        + body.replace("    let child = unnest(n.nested)\n    cross join child\n", ""),
    )
    assert len(_facts(semantic).collect_facts) == 1
    # The table function binding is visible, and has no nested output
    # (PIE-S2806 B3).
    parsed = _parsed_files(
        tmp_path / "function",
        {"main.pietto": HEAD + body.replace("        nested = collect children\n", "")},
    )
    assert [
        (d.code, d.location.line, d.location.column, d.message)
        for d in parsed.diagnostics
    ] == [
        (
            "PIE-S2806",
            11,
            24,
            "Unnest argument n.nested is not available: n is a table function, "
            "which has no nested fields.",
        )
    ]


def test_fact_set_rejects_omitted_reordered_and_foreign_occurrences(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE.replace(
            "nested = collect children",
            "first = collect children\n        second = collect children",
        ),
    )
    facts = _facts(semantic)
    assert len(facts.collect_facts) == 2
    with pytest.raises(ValueError, match="every Collect occurrence"):
        replace(facts, collect_facts=facts.collect_facts[:1])
    with pytest.raises(ValueError, match="every Collect occurrence"):
        replace(facts, collect_facts=tuple(reversed(facts.collect_facts)))
    other = _facts(_semantic(tmp_path / "other", SOURCE))
    with pytest.raises(ValueError, match="semantic catalog authority"):
        replace(facts, semantic=other.semantic)
    with pytest.raises(ValueError, match="every Collect occurrence"):
        replace(other, collect_facts=facts.collect_facts[:1])


def test_fact_set_derives_every_status_reason_target_and_type(tmp_path: Path) -> None:
    semantic = _semantic(
        tmp_path,
        _expanded("cross join child")
        + "query other:\n    let children:\n        from rows\n        select:\n"
        "            id\n        order by id\n    from rows\n    select:\n        id\n"
        "        mine = collect children\n",
    )
    facts = _facts(semantic)
    collect, other = facts.collect_facts
    (unnest,) = facts.unnest_inputs
    unavailable = ProjectNestedRelationFactStatus.UNAVAILABLE
    nested = collect.nested_type
    assert nested is not None and other.nested_type is not None

    def rejected(**changes: object) -> None:
        # The fact may be well formed alone; the set derives it from the root.
        forged = replace(collect, **changes)
        with pytest.raises(ValueError, match="every Collect occurrence"):
            replace(facts, collect_facts=(forged, other))

    # Status and reason are bound, and the root decides them.
    with pytest.raises(ValueError, match="availability must match its reason"):
        replace(collect, status=unavailable)
    rejected(
        status=unavailable,
        reason=ProjectNestedRelationFactReason.TARGET_UNAVAILABLE,
        nested_type=None,
    )
    # The target is the resolved relation, and an available one a local let.
    with pytest.raises(ValueError, match="resolved relation"):
        replace(collect, target=collect.owner)
    # The output keeps its selected name.
    assert collect.output is not None
    with pytest.raises(ValueError, match="selected occurrence"):
        replace(collect, output=replace(collect.output, name="renamed"))
    # A collected relation has exactly one layer.
    with pytest.raises(ValueError, match="one collection layer"):
        replace(nested, collection_depth=True)
    # Another Collect's child type is not this one's, and an equal copy is not
    # the type its Collect read fact holds (S04: the fact is a view of it).
    with pytest.raises(ValueError, match="resolved local let"):
        replace(collect, nested_type=other.nested_type)
    with pytest.raises(ValueError, match="resolved local let"):
        replace(
            collect,
            nested_type=replace(
                nested,
                element_fields=tuple(
                    replace(item, field=replace(item.field))
                    for item in nested.element_fields
                ),
            ),
        )
    # An Unnest keeps the root's decision and its own Collect authority.
    with pytest.raises(ValueError, match="every Unnest occurrence"):
        replace(
            facts,
            unnest_inputs=(
                replace(
                    unnest,
                    status=unavailable,
                    reason=ProjectNestedRelationFactReason.JOIN_UNAVAILABLE,
                ),
            ),
        )
    # S05 (D-S05-7): the set holds the semantic root's own Unnest facts; an
    # equal copy, even one keeping the Collect authority, is no fact of it.
    with pytest.raises(ValueError, match="every Unnest occurrence"):
        replace(
            facts,
            unnest_inputs=(
                replace(
                    unnest,
                    source_field=replace(collect.output),
                    nested_type=nested,
                ),
            ),
        )
    assert unnest.collect_read is collect.collect_read


def test_semantic_result_requires_the_nested_relation_sidecar(tmp_path: Path) -> None:
    semantic = _semantic(tmp_path, _expanded("cross join child"))
    nested = _facts(semantic)

    with pytest.raises(ValueError, match="require all module sidecars"):
        replace(
            semantic,
            nested_relation_facts=None,
            diagnostics=tuple(
                item for item in semantic.diagnostics if item not in nested.diagnostics
            ),
        )
    with pytest.raises(ValueError, match="exact ordered root projection"):
        replace(semantic, diagnostics=semantic.diagnostics[:-1])
    # A look-alike on the same roots that omits every fact is no fact set.
    with pytest.raises(TypeError, match="exact fact set"):
        replace(
            semantic,
            nested_relation_facts=SimpleNamespace(
                catalogs=nested.catalogs,
                semantic=nested.semantic,
                collect_facts=(),
                unnest_inputs=(),
                diagnostics=nested.diagnostics,
            ),
        )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            SOURCE.replace(
                "nested = collect children",
                "nested = collect children\n        id\n        id",
            ),
            [("PIE-S2802", 13, 18), ("PIE-S2305", 15, 9)],
        ),
        (
            SOURCE.replace(
                "nested = collect children",
                "id\n        id\n        nested = collect children",
            ),
            [("PIE-S2802", 15, 18), ("PIE-S2305", 14, 9)],
        ),
        # A colliding Collect/scalar output of a JOIN relation, in both
        # orders: no winner, and PIE-S2305 once at the later occurrence.
        (
            JOINED + "    select:\n        same = collect children\n"
            "        same = rows.id\n",
            [("PIE-S2802", 14, 16), ("PIE-S2305", 15, 9)],
        ),
        (
            JOINED + "    select:\n        same = rows.id\n"
            "        same = collect children\n",
            [("PIE-S2802", 15, 16), ("PIE-S2305", 15, 9)],
        ),
    ],
    ids=[
        "collect-first",
        "collect-last",
        "joined-collect-first",
        "joined-collect-last",
    ],
)
def test_nested_diagnostics_precede_completion_diagnostics(
    tmp_path: Path, source: str, expected: list[tuple[str, int, int]]
) -> None:
    # Project stage order: the semantic stage's PIE-S2802 comes before the
    # completion stage's PIE-S2305 wherever each is written.
    assert _checked(_semantic(tmp_path, source)) == expected


@pytest.mark.parametrize("collect_module", ["a.pietto", "b.pietto"])
def test_nested_diagnostics_follow_relation_resolution_in_module_order(
    tmp_path: Path, collect_module: str
) -> None:
    unread = (
        HEAD + "query old:\n    let unused:\n        from rows\n        select:\n"
        "            id\n    from rows\n"
        "    select:\n        id\n"
    )
    other_module = "b.pietto" if collect_module == "a.pietto" else "a.pietto"
    semantic = _semantic_files(
        tmp_path,
        {
            collect_module: SOURCE.replace(
                "    from rows\n    select:\n        nested",
                "    from ghost\n    select:\n        nested",
            ),
            other_module: unread.replace("shape Row", "shape Other")
            .replace("source rows: Row", "source others: Other")
            .replace("from rows", "from others"),
        },
    )

    diagnostics = semantic.diagnostics
    codes = [d.code for d in diagnostics]
    nested = _facts(semantic).diagnostics
    # The nested producer follows every older producer, which keep their
    # own relative order; no unrelated diagnostic moves it.
    assert tuple(diagnostics[len(diagnostics) - len(nested) :]) == nested
    assert codes.count("PIE-S2802") == 1
    old = diagnostics[: len(diagnostics) - len(nested)]
    assert {d.code for d in old} >= {"PIE-S2301", "PIE-S2359"}


def test_nested_diagnostics_follow_relation_resolution_in_dependency_order(
    tmp_path: Path,
) -> None:
    # a.pietto imports z.pietto, so the semantic stage reports z first; the
    # nested producer keeps that module order, not the selected path order.
    def module(name: str) -> str:
        return (
            f"query q{name}:\n    let kids:\n        from zrows\n        select:\n"
            "            id\n    from zrows\n    select:\n        id\n"
            f"        n = collect kids\nquery q{name}_bad:\n    from ghost_{name}\n"
            "    select:\n        id\n"
        )

    semantic = _semantic_files(
        tmp_path,
        {
            "a.pietto": 'from "z.pietto" import (\n    source zrows,\n)\n'
            + module("a"),
            "z.pietto": 'shape Row:\n    id: Int\nsource zrows: Row = postgres.table("rows")\n'
            + module("z")
            + "export (\n    source zrows,\n)\n",
        },
    )

    assert [(d.code, d.location.path) for d in semantic.diagnostics] == [
        ("PIE-S2301", "z.pietto"),
        ("PIE-S2301", "a.pietto"),
        ("PIE-S2802", "z.pietto"),
        ("PIE-S2802", "a.pietto"),
    ]
    assert [
        fact.owner.identity.declared_name for fact in _facts(semantic).collect_facts
    ] == ["qz", "qa"]


_COLLIDING_UNNEST = """query expanded:
    from parent
    let {name} = unnest(parent.nested)
    cross join {name}
    select:
        id
"""


@pytest.mark.parametrize(
    ("sources", "name", "line"),
    [
        (
            {
                "main.pietto": SOURCE
                + "query o:\n    from rows\n    select:\n        id\n"
                + _COLLIDING_UNNEST.format(name="o")
            },
            "o",
            21,
        ),
        (
            {"main.pietto": SOURCE + _COLLIDING_UNNEST.format(name="parent")},
            "parent",
            17,
        ),
        (
            {
                "lib.pietto": HEAD.replace("rows", "others").replace("Row", "Other")
                + "query other:\n    from others\n    select:\n        id\n"
                + "export (\n    query other,\n)\n",
                "main.pietto": 'from "lib.pietto" import (\n    query other as o,\n)\n'
                + SOURCE
                + _COLLIDING_UNNEST.format(name="o"),
            },
            "o",
            20,
        ),
    ],
    ids=["module-relation", "from-input", "import-alias"],
)
def test_unnest_join_name_collision_is_ambiguous_like_an_alias_let(
    tmp_path: Path, sources: dict[str, str], name: str, line: int
) -> None:
    # The Unnest let is one local input of its JOIN's name: another relation
    # of that name makes the JOIN ambiguous before any semantic fact exists,
    # exactly as an alias let of that name does; no candidate wins.
    def diagnostics(root: Path, value: str) -> list[tuple[str, int, int, str]]:
        parsed = _parsed_files(
            root,
            {
                path: text.replace("unnest(parent.nested)", value)
                for path, text in sources.items()
            },
        )
        return [
            (d.code, d.location.line, d.location.column, d.message)
            for d in parsed.diagnostics
        ]

    expected = [("PIE-S2604", line, 5, f"Ambiguous JOIN input: {name}")]
    assert diagnostics(tmp_path / "unnest", "unnest(parent.nested)") == expected
    assert diagnostics(tmp_path / "alias", "parent") == expected


@pytest.mark.parametrize(
    ("body", "kinds", "ordinal"),
    [
        (
            "    where any(x.id == rows.id for x in rows)\n"
            "    let child = unnest(rows.note)\n    cross join child\n",
            ["semi", "cross"],
            1,
        ),
        (
            "    let child = unnest(rows.note)\n    cross join child\n"
            "    where any(x.id == rows.id for x in rows)\n"
            "    let peer = rows\n    inner join peer on peer.id == rows.id\n",
            ["cross", "semi", "inner"],
            2,
        ),
        (
            "    let peer = rows\n    inner join peer on peer.id == rows.id\n"
            "    where any(x.id == rows.id for x in rows)\n"
            "    let child = unnest(rows.note)\n    cross join child\n",
            ["inner", "semi", "cross"],
            2,
        ),
    ],
    ids=["any-first", "any-after-unnest", "any-between-joins"],
)
def test_a_join_filter_any_keeps_its_hidden_join_beside_an_unnest(
    tmp_path: Path, body: str, kinds: list[str], ordinal: int
) -> None:
    # The project keeps the Unnest JOIN in its place among the relation's
    # JOINs, reading no relation; the hidden JOIN of a `where any(...)`
    # written before a later JOIN keeps its own place. S05 (D-S05-4) then
    # refuses the Unnest beside `any(...)` before semantics (PIE-S2807 S).
    parsed = _parsed_files(
        tmp_path,
        {
            "main.pietto": HEAD
            + "query ex:\n    from rows\n"
            + body
            + "    select:\n        rows.id\n"
        },
    )
    let_line = 7 + body.count("\n", 0, body.index("let child"))
    assert [
        (d.code, d.location.line, d.location.column) for d in parsed.diagnostics
    ] == [("PIE-S2807", let_line, 5)]
    assert "beside any(...)" in parsed.diagnostics[0].message
    (source,) = parsed.parsed_inputs
    (use,) = source.existence_generators
    assert [join.kind.value for join in use.owner.join_clauses] == kinds
    assert use.input_ordinal == ordinal
    assert use.owner.join_clauses[ordinal - 1] is use.clause
    assert use.clause.target_relation_name == "rows"
    (unnest_join,) = (
        join for join in use.owner.join_clauses if join.kind.value == "cross"
    )
    assert unnest_join.target_relation_name == "child"


def test_a_hidden_any_join_over_an_unnest_name_is_no_unnest_join(
    tmp_path: Path,
) -> None:
    # A `where any(...)` before the JOIN reads its name as a relation; only
    # the written JOIN is the Unnest's. S05 (D-S05-4) refuses `any(...)`
    # beside an Unnest once, at the let, and never as another read of it.
    parsed = _parsed_files(
        tmp_path,
        {
            "main.pietto": SOURCE
            + """query expanded:
    from parent
    let child = unnest(parent.nested)
    where any(x.id == 1 for x in child)
    cross join child
    select:
        id
"""
        },
    )

    assert [
        (d.code, d.location.line, d.location.column) for d in parsed.diagnostics
    ] == [("PIE-S2807", 16, 5)]
    assert "beside any(...)" in parsed.diagnostics[0].message
    (source,) = parsed.parsed_inputs
    expanded = (source.authored_script or source.script).definitions[-1]
    assert isinstance(expanded, QueryDef)
    ((let, joins),) = unnest_lets(expanded)
    assert let.name == "child"
    assert [join.kind.value for join in joins] == ["cross"]


# --- S04: Collect admission, its read facts and the nested-field boundary ---

ADMISSION_HEAD = """type Id = Int
type Money = Decimal(12, 2)
enum Status:
    open
    closed
shape Address:
    city: Text
shape Customer:
    id: Int
    region: Text
    home: Address
shape Order:
    id: Id
    customer_id: Int
    total: Money
    status: Status
    note: Text | None
    payload: Json
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
"""
ORDERED_RECENT = (
    "        from orders\n        select:\n            id\n            note\n"
    "        order by id\n"
)


def _collecting(let_body: str, select: str = "        id\n") -> str:
    """A query collecting its relation let `recent` (``let_body``)."""

    return (
        ADMISSION_HEAD
        + "query parent:\n    let recent:\n"
        + let_body
        + "    from customers\n    select:\n"
        + select
        + "        recent_orders = collect recent\n"
    )


def _relation_facts(
    semantic: ProjectSemanticResult, name: str, let: bool = False
) -> Any:
    facts = semantic.module_semantic_facts
    assert facts is not None
    (found,) = (
        item
        for environment in facts.environments
        for item in environment.relation_facts
        if item.owner.identity.declared_name == name
        and (item.owner.let_position is not None) is let
    )
    return found


def test_a_collect_value_is_a_nested_relation_type_of_its_let_occurrence(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE.replace(
            "nested = collect children",
            "first = collect children\n        second = collect children",
        )
        + "query twin:\n    let children:\n        from rows\n        select id, note\n"
        "        order by:\n            id\n    from rows\n    select:\n"
        "        nested = collect children\n",
    )

    assert len(ProjectResolvedTypeKind) == 6
    assert ProjectResolvedTypeKind.NESTED_RELATION.value == "nested_relation"
    first, second = _relation_facts(semantic, "parent").collect_reads
    (twin,) = _relation_facts(semantic, "twin").collect_reads
    field = _relation_facts(semantic, "parent").state.schema.fields["first"]
    resolved = field.resolved_type
    assert resolved.kind is ProjectResolvedTypeKind.NESTED_RELATION
    assert (resolved.name, resolved.symbol) == ("<nested relation>", None)
    assert resolved.nested is first.nested_type
    assert field.nullability is ProjectRowFieldNullability.NON_NULL
    # A type is its let occurrence and ordered child fields, not their spelling.
    assert first.resolved_type == second.resolved_type
    assert hash(first.resolved_type) == hash(second.resolved_type)
    assert first.resolved_type != twin.resolved_type
    assert not hasattr(first.nested_type, "container_nullability")
    nested = first.nested_type
    with pytest.raises(ValueError, match="nested descriptor"):
        ProjectResolvedType(
            name="<nested relation>", kind=ProjectResolvedTypeKind.NESTED_RELATION
        )
    with pytest.raises(ValueError, match="nested descriptor"):
        ProjectResolvedType(
            name="Int", kind=ProjectResolvedTypeKind.BUILTIN, nested=nested
        )
    with pytest.raises(TypeError, match="exact descriptor"):
        ProjectResolvedType(
            name="<nested relation>",
            kind=ProjectResolvedTypeKind.NESTED_RELATION,
            nested=SimpleNamespace(),  # type: ignore[arg-type]
        )
    # A nested value is no scalar: no type is the same as it, itself included.
    assert not same_canonical_type(resolved, resolved)


def test_a_collect_owner_completes_with_its_read_as_the_output_source(
    tmp_path: Path,
) -> None:
    # `parent` keeps its module row and replays its body, `joined` completes
    # its JOIN, and `reader` replays its body over the completed `joined`.
    semantic = _semantic(
        tmp_path,
        SOURCE
        + JOINED.removeprefix(HEAD)
        + "    select:\n        id = rows.id\n        nested = collect children\n"
        + "query reader:\n    let mine:\n        from rows\n        select id\n"
        "        order by id\n    from joined\n    select:\n        id\n"
        "        again = collect mine\n",
    )

    parent = _relation_facts(semantic, "parent")
    assert parent.state.status.value == "concrete"
    assert (
        parent.state.reason
        is not ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
    )
    completed: Any = build_project_completed_semantic_result(semantic)
    entries = {
        entry.owner.identity.declared_name: entry
        for entry in completed.effective_outputs.entries
        if entry.owner.let_position is None
    }
    for name, ordinal in (("parent", 0), ("joined", 1), ("reader", 1)):
        entry = entries[name]
        assert type(entry).__name__ == "ProjectCompletedEffectiveOutput"
        output = entry.fields[ordinal]
        (read,) = _relation_facts(semantic, name).collect_reads
        assert output.source is read
        assert output.selected_output_ordinal == ordinal
        assert output.field.resolved_type == read.resolved_type
        assert output.field.nullability is ProjectRowFieldNullability.NON_NULL
    assert [code for code, _, _ in _located(completed.diagnostics)] == ["PIE-S2802"] * 3
    assert not completed.ok


def test_a_captured_field_of_an_outer_joined_input_is_nullable_in_its_let(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        HEAD + "query parent:\n    let mine:\n        capture o\n        from rows\n"
        "        where rows.id == o.id\n        select:\n            id\n"
        "        order by id\n    from rows\n    let o = rows\n"
        "    left join o on rows.id == o.id\n    select:\n        id = rows.id\n"
        "        mine_rows = collect mine\n",
    )

    let = _relation_facts(semantic, "mine", let=True)
    (captured,) = let.captured_value_types.values()
    assert captured.nullability.value == "nullable"
    assert _checked(semantic) == [("PIE-S2802", 18, 21)]


def test_emit_sql_still_blocks_every_collect_program(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _parsed_files(tmp_path, {"main.pietto": SOURCE}).ok
    root = tmp_path / "project"
    (root / "contract.json").write_text("{}", encoding="utf-8")

    code = cli_main(
        [
            "emit-sql",
            "--project",
            str(root),
            "--module",
            "main.pietto",
            "--kind",
            "query",
            "--name",
            "parent",
            "--dialect",
            "postgres",
            "--emission-contract",
            "contract.json",
        ]
    )

    document = json.loads(capsys.readouterr().out)
    assert code == 1
    assert (document["status"], document["artifact"]) == ("BLOCKED", None)
    assert [item["code"] for item in document["diagnostics"]] == ["PIE-S2802"]


@pytest.mark.parametrize(
    ("source", "expected", "message"),
    [
        (
            _collecting(ORDERED_RECENT, "        region\n        n = count()\n")
            .replace(
                "    from customers\n", "    from customers\n    group by region\n"
            )
            .replace("    select:\n        region", "    select:\n        region"),
            [("PIE-S2803", 33, 25), ("PIE-S2802", 33, 25)],
            "Collect relation read is available only as a SELECT item of an ungrouped "
            "table or query, not in the SELECT of a grouped query.",
        ),
        (
            _collecting(ORDERED_RECENT, "        n = count()\n"),
            [("PIE-S2803", 31, 25), ("PIE-S2802", 31, 25)],
            "Collect relation read is available only as a SELECT item of an ungrouped "
            "table or query, not in the SELECT of a grouped query.",
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    let inner_orders:\n"
            + ORDERED_RECENT
            + "    let wrapper:\n        from customers\n        select:\n"
            "            id\n            x = collect inner_orders\n    from wrapper\n"
            "    select:\n        id\n",
            # The relation reports its own error inside it, so no completion
            # fallback beside it.
            [("PIE-S2803", 32, 17), ("PIE-S2802", 32, 17)],
            "Collect relation read is available only as a SELECT item of an ungrouped "
            "table or query, not in a relation let.",
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    from customers\n    select:\n        id\n"
            "        everything = collect orders\n",
            [("PIE-S2803", 25, 22), ("PIE-S2802", 25, 22)],
            "Collect relation read orders is not a relation let of parent: collect "
            "reads a relation let declared in the same table or query.",
        ),
        (
            _collecting("        union all orders, orders\n"),
            [("PIE-S2802", 27, 25), ("PIE-S2803", 27, 25)],
            "Collect relation read recent is not yet available: the columns of recent "
            "are not known before completion.",
        ),
        (
            _collecting(
                '        values(id: Int, label: Text | None):\n            1, "new"\n'
                "            2, None\n"
            ),
            [("PIE-S2802", 29, 25), ("PIE-S2803", 29, 25)],
            "Collect relation read recent is not yet available: the columns of recent "
            "are not known before completion.",
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    let both:\n        union all orders, orders\n"
            "    let recent:\n        from both\n        select:\n            id\n"
            "        order by id\n    from customers\n    select:\n        id\n"
            "        recent_orders = collect recent\n",
            [("PIE-S2802", 32, 25), ("PIE-S2803", 32, 25)],
            "Collect relation read recent is not yet available: the columns of recent "
            "are not known before completion.",
        ),
        (
            _collecting(
                ORDERED_RECENT.replace("            note\n", "            status\n")
            ),
            [("PIE-S2802", 31, 25), ("PIE-S2803", 31, 25)],
            "Collect relation read recent is not available: field status of recent has "
            "type Status; a collected field must be Bool, Date, Decimal, Float, Int, "
            "Text, Timestamp or UUID.",
        ),
        (
            _collecting(
                "        from customers\n        select:\n            id\n"
                "            home\n        order by id\n"
            ),
            [("PIE-S2802", 31, 25), ("PIE-S2803", 31, 25)],
            "Collect relation read recent is not available: field home of recent has "
            "type Address; a collected field must be Bool, Date, Decimal, Float, Int, "
            "Text, Timestamp or UUID.",
        ),
        (
            _collecting(
                ORDERED_RECENT.replace("            note\n", "            payload\n")
            ),
            [("PIE-S2802", 31, 25), ("PIE-S2803", 31, 25)],
            "Collect relation read recent is not available: field payload of recent "
            "has type Json; a collected field must be Bool, Date, Decimal, Float, Int, "
            "Text, Timestamp or UUID.",
        ),
        (
            _collecting(ORDERED_RECENT)
            + "query twice:\n    let inner:\n        from parent\n        select:\n"
            "            id\n            recent_orders\n        order by id\n"
            "    from customers\n    select:\n        id\n        all = collect inner\n",
            [
                ("PIE-S2802", 31, 25),
                ("PIE-S2802", 42, 15),
                ("PIE-S2805", 37, 13),
                ("PIE-S2803", 42, 15),
            ],
            # Selecting the nested field is the let's own error (PIE-S2805), and
            # the read names the one collection layer (AC-04).
            "Collect relation read inner is not available: field recent_orders of "
            "inner is itself a collected relation, and only one collection layer is "
            "supported.",
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    from customers\n    select:\n        id\n"
            "        r = collect ghost\n",
            [("PIE-S2301", 25, 13), ("PIE-S2802", 25, 13)],
            None,
        ),
        (
            ADMISSION_HEAD + "query parent:\n    from customers\n    group by region\n"
            "    select:\n        region\n        r = collect ghost\n",
            [("PIE-S2803", 26, 13), ("PIE-S2802", 26, 13)],
            "Collect relation read is available only as a SELECT item of an ungrouped "
            "table or query, not in the SELECT of a grouped query.",
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    from customers\n    select:\n        id\n"
            "        r = collect parent\n",
            [("PIE-S2302", 25, 13), ("PIE-S2802", 25, 13)],
            None,
        ),
        (
            ADMISSION_HEAD
            + "query parent:\n    from customers\n    select:\n        id\n"
            "        r = collect child\nquery child:\n    from parent\n"
            "    select:\n        id\n",
            [("PIE-S2302", 25, 13), ("PIE-S2802", 25, 13)],
            None,
        ),
        (
            _collecting(
                ORDERED_RECENT.replace("            note\n", "            bogus\n")
            ),
            # A read of a let that fails reports nothing of its own, as a scalar
            # read of one does.
            [("PIE-S2102", 26, 13), ("PIE-S2802", 31, 25)],
            None,
        ),
        (
            _collecting(
                ORDERED_RECENT.replace("            note\n", "            x = id + 1\n")
            ),
            [("PIE-S2802", 31, 25), ("PIE-S2803", 31, 25)],
            "Collect relation read recent is not available: the type or nullability "
            "of field x of recent is not known.",
        ),
    ],
    ids=[
        "grouped",
        "global-aggregate",
        "let-body",
        "not-a-let",
        "set-operation-let",
        "values-let",
        "let-reading-a-set",
        "enum-leaf",
        "shape-leaf",
        "json-leaf",
        "collected-leaf",
        "unknown-target",
        "grouped-unknown-target",
        "self-cyclic-target",
        "cyclic-target",
        "let-own-error",
        "computed-field",
    ],
)
def test_collect_admission_refuses_each_read_once_in_check_order(
    tmp_path: Path,
    source: str,
    expected: list[tuple[str, int, int]],
    message: str | None,
) -> None:
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, source)
    ).diagnostics

    assert _located(diagnostics) == expected
    refusals = [d for d in diagnostics if d.code == "PIE-S2803"]
    assert [d.message for d in refusals] == ([] if message is None else [message])


@pytest.mark.parametrize("leaf", ["Any", "Bytes"])
def test_collect_refuses_every_unadmitted_builtin_leaf(
    tmp_path: Path, leaf: str
) -> None:
    source = _collecting(
        ORDERED_RECENT.replace("            note\n", "            payload\n")
    )
    semantic = _semantic(tmp_path, source.replace("payload: Json", f"payload: {leaf}"))

    (diagnostic,) = (
        d
        for d in build_project_completed_semantic_result(semantic).diagnostics
        if d.code == "PIE-S2803"
    )
    assert f"has type {leaf};" in diagnostic.message


def test_an_alias_leaf_is_collected_as_the_type_it_names(tmp_path: Path) -> None:
    semantic = _semantic(
        tmp_path,
        _collecting(
            ORDERED_RECENT.replace("            note\n", "            total\n")
        ),
    )

    (read,) = _relation_facts(semantic, "parent").collect_reads
    assert read.nested_type is not None and read.diagnostic is None
    ids, totals = read.nested_type.element_fields
    assert (ids.field.resolved_type.name, totals.field.resolved_type.name) == (
        "Int",
        "Decimal",
    )
    # The alias is kept on the child field's own written type.
    assert ids.field.field_def.type_expr.name == "Id"
    assert totals.field.field_def.type_expr.name == "Money"
    assert _checked(semantic) == [("PIE-S2802", 31, 25)]


@pytest.mark.parametrize(
    "let_body",
    [
        "        from orders\n        select:\n            id\n",
        "        capture customers\n        from orders\n"
        "        where orders.customer_id == customers.id\n        select:\n"
        "            id\n",
    ],
    ids=["closed", "captured"],
)
def test_a_collected_let_without_order_by_is_refused_with_its_remedy(
    tmp_path: Path, let_body: str
) -> None:
    semantic = _semantic(tmp_path, _collecting(let_body))

    diagnostics = build_project_completed_semantic_result(semantic).diagnostics
    line = 26 + let_body.count("\n")
    assert _located(diagnostics) == [("PIE-S2802", line, 25), ("PIE-S2804", line, 25)]
    refusal = diagnostics[1]
    assert refusal.message == (
        "Relation let recent read by `collect` has no ORDER BY: add `order by` to "
        "recent and end it with a unique field, such as a key, because rows that "
        "tie on every key have no promised order."
    )
    assert (
        refusal.suggestion
        == "Add `order by` to let recent, ending with a unique field."
    )
    (read,) = _relation_facts(semantic, "parent").collect_reads
    assert read.nested_type is None and read.diagnostic is refusal
    assert read.closed is ("capture" not in let_body)


def test_a_captured_top_k_let_is_collected_with_its_order_and_limit(
    tmp_path: Path,
) -> None:
    semantic = _semantic(
        tmp_path,
        _collecting(
            "        capture customers\n        from orders\n"
            "        where orders.customer_id == customers.id\n        select:\n"
            "            id\n        order by id\n        limit 3\n"
        ),
    )

    (read,) = _relation_facts(semantic, "parent").collect_reads
    assert read.nested_type is not None and not read.closed
    assert read.limit_clause is not None and read.order_by_clause is not None
    assert _checked(semantic) == [("PIE-S2802", 33, 25)]


def test_the_collected_order_reaches_its_let_keys_including_unselected_fields(
    tmp_path: Path,
) -> None:
    source = _collecting(
        "        from orders\n        select:\n            id\n"
        "        order by customer_id desc, id\n"
    )
    semantic = _semantic(tmp_path, source)

    (read,) = _relation_facts(semantic, "parent").collect_reads
    assert read.target is not None
    completed: Any = build_project_completed_semantic_result(semantic)
    (ordering,) = (
        facts.ordering
        for facts in completed.roots.order_facts
        if facts.entry.owner is read.target.owner
    )
    first, second = ordering.items
    assert [item.expression.name for item in ordering.items] == ["customer_id", "id"]
    assert [item.direction.value for item in ordering.items] == ["desc", "asc"]
    # The unselected key reads the let's exact input field.
    assert first.source.input_schema is read.target.input_state.schema
    assert "customer_id" not in read.target.state.schema.fields
    assert first.source.input_schema.fields["customer_id"].name == "customer_id"
    assert second.source.input_schema is read.target.input_state.schema


def test_collect_read_facts_are_the_one_authority_of_each_read(tmp_path: Path) -> None:
    semantic = _semantic(
        tmp_path,
        SOURCE.replace(
            "    from rows\n    select:\n        nested = collect children",
            "    let ids:\n        from rows\n        select id\n        order by id\n"
            "    from rows\n    select:\n        nested = collect children\n"
            "        just_ids = collect ids",
        ),
    )

    reads = _relation_facts(semantic, "parent").collect_reads
    first, second = reads
    for read in reads:
        assert read.nested_type is not None and read.diagnostic is None
        assert read.closed
        assert read.multiplicity == "bag"
        assert read.empty_value == ()
        assert read.container_nullability is ProjectRowFieldNullability.NON_NULL
        assert read.nested_type.collection_depth == 1
        assert read.order_by_clause is read.target.owner.definition.order_by_clause
        assert read.nested_type.element_relation.let_position == (
            read.target.owner.let_position
        )
    assert first.target.owner is not second.target.owner
    assert [field.identity.name for field in second.nested_type.element_fields] == [
        "id"
    ]
    # The nested-relation sidecar is a view of these very facts.
    collects = _facts(semantic).collect_facts
    assert [item.collect_read for item in collects] == list(reads)
    assert all(
        item.collect_read is read for item, read in zip(collects, reads, strict=True)
    )
    assert all(
        item.nested_type is read.nested_type
        for item, read in zip(collects, reads, strict=True)
    )
    # A typed read has no diagnostic, an untyped local one names why.
    with pytest.raises(ValueError, match="no diagnostic"):
        replace(first, diagnostic=_facts(semantic).diagnostics[0])
    with pytest.raises(ValueError, match="names why"):
        replace(first, nested_type=None)


MATRIX_HEAD = """shape Customer:
    id: Int
    region: Text
shape Order:
    id: Int
    customer_id: Int
    note: Text | None
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
query parent:
    let recent:
        from orders
        select:
            id
            note
        order by id
    from customers
    select:
        id
        region
        recent_orders = collect recent
"""
_NO_JOIN = "query reader:\n    from parent\n"
_JOIN = (
    "query reader:\n    from customers\n    let p = parent\n"
    "    inner join p on customers.id == p.id\n"
)
_SELECT_ID = "    select:\n        id\n"
_SELECT_JOINED = "    select:\n        id = customers.id\n"
# Each case: the reader written after the parent, and every diagnostic after
# the parent's own PIE-S2802 at 21:25 (a PIE-S2805 at each read of a nested
# field, at the field reference; S04 D-S04-2).
NESTED_READS = {
    "where-eq": (
        _NO_JOIN + "    where recent_orders == recent_orders\n" + _SELECT_ID,
        [("PIE-S2805", 24, 11), ("PIE-S2805", 24, 28)],
    ),
    "where-arith": (
        _NO_JOIN + "    where recent_orders + 1 > 2\n" + _SELECT_ID,
        [("PIE-S2805", 24, 11)],
    ),
    "where-is-none": (
        _NO_JOIN + "    where recent_orders is None\n" + _SELECT_ID,
        [("PIE-S2805", 24, 11)],
    ),
    "where-like": (
        _NO_JOIN + '    where recent_orders like "a%"\n' + _SELECT_ID,
        [("PIE-S2805", 24, 11)],
    ),
    "where-in-list": (
        _NO_JOIN + "    where recent_orders in (1, 2)\n" + _SELECT_ID,
        [("PIE-S2805", 24, 11)],
    ),
    "where-qualified": (
        _NO_JOIN + "    where parent.recent_orders == 1\n" + _SELECT_ID,
        [("PIE-S2805", 24, 11)],
    ),
    "select-direct": (
        _NO_JOIN + "    select:\n        id\n        recent_orders\n",
        [("PIE-S2805", 26, 9)],
    ),
    "select-renamed": (
        _NO_JOIN + "    select:\n        id\n        r = recent_orders\n",
        [("PIE-S2805", 26, 13)],
    ),
    "select-expression": (
        _NO_JOIN + "    select:\n        id\n        x = recent_orders == 1\n",
        [("PIE-S2805", 26, 13)],
    ),
    "select-count": (
        _NO_JOIN + "    select:\n        n = count(recent_orders)\n",
        [("PIE-S2805", 25, 19)],
    ),
    "select-max": (
        _NO_JOIN + "    select:\n        m = max(recent_orders)\n",
        [("PIE-S2805", 25, 17)],
    ),
    "row-let": (
        _NO_JOIN + "    let x = recent_orders\n" + _SELECT_ID,
        [("PIE-S2805", 24, 13)],
    ),
    "group-by": (
        _NO_JOIN + "    group by recent_orders\n    select:\n        n = count()\n",
        [("PIE-S2805", 24, 14)],
    ),
    "having": (
        _NO_JOIN
        + "    group by region\n    select:\n        region\n        n = count()\n"
        "    having count(recent_orders) > 0\n",
        [("PIE-S2805", 28, 18)],
    ),
    "group-by-select-key": (
        _NO_JOIN + "    group by recent_orders\n    select:\n        recent_orders\n"
        "        n = count()\n",
        [("PIE-S2805", 24, 14), ("PIE-S2805", 26, 9)],
    ),
    "grouped-select-renamed": (
        _NO_JOIN + "    group by region\n    select:\n        region\n"
        "        x = recent_orders\n        n = count()\n",
        [("PIE-S2805", 27, 13)],
    ),
    "global-select": (
        _NO_JOIN + "    select:\n        x = recent_orders\n        n = count()\n",
        [("PIE-S2805", 25, 13)],
    ),
    "order-field": (
        _NO_JOIN + _SELECT_ID + "    order by recent_orders\n",
        [("PIE-S2805", 26, 14)],
    ),
    "order-expression": (
        _NO_JOIN + _SELECT_ID + "    order by recent_orders + 1\n",
        [("PIE-S2805", 26, 14)],
    ),
    "grouped-order-field": (
        _NO_JOIN + "    group by region\n    select:\n        region\n"
        "        n = count()\n    order by recent_orders\n",
        [("PIE-S2805", 28, 14)],
    ),
    "window-partition": (
        _NO_JOIN
        + _SELECT_ID
        + "        r = row_number() window(partition by recent_orders order by id)\n",
        [("PIE-S2805", 26, 46)],
    ),
    "window-order": (
        _NO_JOIN
        + _SELECT_ID
        + "        r = row_number() window(order by recent_orders)\n",
        [("PIE-S2805", 26, 42)],
    ),
    "window-lag": (
        _NO_JOIN + _SELECT_ID + "        l = lag(recent_orders) window(order by id)\n",
        [("PIE-S2805", 26, 17)],
    ),
    "qualify": (
        _NO_JOIN + _SELECT_ID + "        r = row_number() window(order by id)\n"
        "    qualify recent_orders == 1\n",
        [("PIE-S2805", 27, 13)],
    ),
    "named-window": (
        _NO_JOIN
        + "    let w = window(partition by recent_orders order by id)\n"
        + _SELECT_ID
        + "        r = row_number() window w\n",
        [("PIE-S2805", 24, 33)],
    ),
    "named-window-base": (
        _NO_JOIN
        + "    let w = window(order by recent_orders)\n"
        + "    let w2 = window w(partition by region)\n"
        + _SELECT_ID
        + "        r = row_number() window w2\n",
        [("PIE-S2805", 24, 29)],
    ),
    "any": (
        "query reader:\n    from customers\n"
        "    where any(o.recent_orders == 1 for o in parent)\n" + _SELECT_ID,
        [("PIE-S2805", 24, 15)],
    ),
    "scalar-read": (
        "query reader:\n    from customers\n"
        + _SELECT_ID
        + "        t = scalar parent.recent_orders\n",
        [("PIE-S2805", 26, 13)],
    ),
    "in-read": (
        "query only_nested:\n    let mine:\n        from orders\n        select:\n"
        "            id\n        order by id\n    from customers\n    select:\n"
        "        mine_all = collect mine\n"
        "query reader:\n    from customers\n    where id in only_nested\n" + _SELECT_ID,
        [("PIE-S2802", 30, 20), ("PIE-S2805", 33, 11)],
    ),
    "captured": (
        "query reader:\n    let t:\n        capture parent\n        from orders\n"
        "        where orders.customer_id == parent.id and parent.recent_orders == 1\n"
        "        select:\n            id\n    from parent\n    where exists t\n"
        + _SELECT_ID,
        [("PIE-S2805", 26, 51)],
    ),
    "join-where-eq": (
        _JOIN + "    where p.recent_orders == p.recent_orders\n" + _SELECT_JOINED,
        [("PIE-S2805", 26, 11), ("PIE-S2805", 26, 30)],
    ),
    "join-where-arith": (
        _JOIN + "    where p.recent_orders + 1 > 2\n" + _SELECT_JOINED,
        [("PIE-S2805", 26, 11)],
    ),
    "join-select-renamed": (
        _JOIN + _SELECT_JOINED + "        r = p.recent_orders\n",
        [("PIE-S2805", 28, 13)],
    ),
    "join-select-expression": (
        _JOIN + _SELECT_JOINED + "        x = p.recent_orders == 1\n",
        [("PIE-S2805", 28, 13)],
    ),
    # A JOIN aggregate of the field itself reports only the field.
    "join-select-count": (
        _JOIN + "    select:\n        n = count(p.recent_orders)\n",
        [("PIE-S2805", 27, 19)],
    ),
    "join-select-max": (
        _JOIN + "    select:\n        m = max(p.recent_orders)\n",
        [("PIE-S2805", 27, 17)],
    ),
    "join-row-let": (
        _JOIN + "    let x = p.recent_orders\n" + _SELECT_JOINED,
        [("PIE-S2805", 26, 13)],
    ),
    "join-group-by": (
        _JOIN + "    group by p.recent_orders\n    select:\n        n = count()\n",
        [("PIE-S2805", 26, 14)],
    ),
    "join-group-by-select-key": (
        _JOIN + "    group by p.recent_orders\n    select:\n        p.recent_orders\n"
        "        n = count()\n",
        [("PIE-S2805", 26, 14), ("PIE-S2805", 28, 9)],
    ),
    "join-grouped-select-renamed": (
        _JOIN + "    group by p.region\n    select:\n        p.region\n"
        "        x = p.recent_orders\n        n = count()\n",
        [("PIE-S2805", 29, 13)],
    ),
    "join-grouped-select-expression": (
        _JOIN + "    group by p.region\n    select:\n        p.region\n"
        "        x = p.recent_orders == 1\n        n = count()\n",
        [("PIE-S2805", 29, 13)],
    ),
    "join-global-select": (
        _JOIN + "    select:\n        x = p.recent_orders\n        n = count()\n",
        [("PIE-S2805", 27, 13)],
    ),
    "join-order": (
        _JOIN + _SELECT_JOINED + "    order by p.recent_orders\n",
        [("PIE-S2805", 28, 14)],
    ),
    "join-window-partition": (
        _JOIN + _SELECT_JOINED + "        r = row_number() window(partition by "
        "p.recent_orders order by customers.id)\n",
        [("PIE-S2805", 28, 46)],
    ),
    "join-window-order": (
        _JOIN
        + _SELECT_JOINED
        + "        r = row_number() window(order by p.recent_orders)\n",
        [("PIE-S2805", 28, 42)],
    ),
    "join-window-lag": (
        _JOIN
        + _SELECT_JOINED
        + "        l = lag(p.recent_orders) window(order by customers.id)\n",
        [("PIE-S2805", 28, 17)],
    ),
    "join-qualify": (
        _JOIN
        + _SELECT_JOINED
        + "        r = row_number() window(order by customers.id)\n"
        "    qualify p.recent_orders == 1\n",
        [("PIE-S2805", 29, 13)],
    ),
    # A JOIN-local ON that is not complete keeps its availability diagnostic.
    "join-on": (
        "query reader:\n    from customers\n    let p = parent\n"
        "    inner join p on customers.id == p.id and p.recent_orders == 1\n"
        + _SELECT_JOINED,
        [("PIE-S2805", 25, 46)],
    ),
    "join-any": (
        _JOIN
        + "    where any(o.recent_orders == 1 for o in parent)\n"
        + _SELECT_JOINED,
        [("PIE-S2805", 26, 15)],
    ),
    "qualify-window-argument": (
        _NO_JOIN
        + _SELECT_ID
        + "    qualify lag(recent_orders) window(order by id) == 1\n",
        [("PIE-S2805", 26, 17)],
    ),
    "qualify-window-partition": (
        _NO_JOIN
        + _SELECT_ID
        + "    qualify row_number() window(partition by recent_orders order by id)"
        " == 1\n",
        [("PIE-S2805", 26, 46)],
    ),
    "parent-order-by-output": (
        "    order by recent_orders\n",
        [("PIE-S2805", 22, 14)],
    ),
    "parent-qualify-output": (
        "        r = row_number() window(order by id)\n    qualify recent_orders == 1\n",
        [("PIE-S2805", 23, 13)],
    ),
}


@pytest.mark.parametrize("case", sorted(NESTED_READS))
def test_every_read_of_a_nested_field_reports_it_once_at_the_field(
    tmp_path: Path, case: str
) -> None:
    reader, expected = NESTED_READS[case]
    semantic = _semantic(tmp_path, MATRIX_HEAD + reader)

    diagnostics = build_project_completed_semantic_result(semantic).diagnostics
    assert _located(diagnostics) == [("PIE-S2802", 21, 25), *expected]
    # The reference keeps its target: never an unknown field, and the reader
    # has its own error, so no completion fallback beside it.
    for diagnostic in diagnostics:
        assert diagnostic.code not in {"PIE-S2102", "PIE-S2333"}
        for text in (diagnostic.message, diagnostic.suggestion or ""):
            assert "nested_relation" not in text and "<nested" not in text
    for diagnostic in diagnostics:
        if diagnostic.code == "PIE-S2805":
            assert diagnostic.message.startswith("Nested relation field ")


# The same parent with JOIN inputs: two lines longer, so a reader without JOIN
# inputs replays its clauses over the parent's completed row.
JOINED_PARENT_HEAD = MATRIX_HEAD.replace(
    "    from customers\n    select:\n        id\n        region\n",
    "    from customers\n    let peer = customers\n"
    "    inner join peer on customers.id == peer.id\n"
    "    select:\n        id = customers.id\n        region = customers.region\n",
)


@pytest.mark.parametrize(
    "case",
    sorted(
        case
        for case, (reader, _) in NESTED_READS.items()
        if reader.startswith(_NO_JOIN)
    ),
)
def test_a_replayed_reader_reports_each_nested_read_once_at_the_field(
    tmp_path: Path, case: str
) -> None:
    reader, expected = NESTED_READS[case]
    semantic = _semantic(tmp_path, JOINED_PARENT_HEAD + reader)

    diagnostics = build_project_completed_semantic_result(semantic).diagnostics
    assert _located(diagnostics) == [
        ("PIE-S2802", 23, 25),
        *((code, line + 2, column) for code, line, column in expected),
    ]


# A reader collecting its own let, read with `from` (directly, or replayed
# over the parent with JOIN inputs, two lines later), then one clause naming
# its Collect output.
OWN_OUTPUT = (
    "query reader:\n    let mine:\n        from orders\n        select:\n"
    "            id\n        order by id\n    from parent\n    select:\n"
    "        id\n        again = collect mine\n"
)


@pytest.mark.parametrize(
    ("head", "shift"),
    [(MATRIX_HEAD, 0), (JOINED_PARENT_HEAD, 2)],
    ids=["direct", "replayed"],
)
@pytest.mark.parametrize(
    ("clause", "expected"),
    [
        ("    order by again\n", [("PIE-S2805", 32, 14)]),
        ("    order by id, again desc\n", [("PIE-S2805", 32, 18)]),
        (
            "        r = row_number() window(order by id)\n    qualify again\n",
            [("PIE-S2805", 33, 13)],
        ),
    ],
    ids=["order-by", "order-by-second-key", "qualify"],
)
def test_a_name_of_the_own_collect_output_reports_only_the_nested_read(
    tmp_path: Path,
    head: str,
    shift: int,
    clause: str,
    expected: list[tuple[str, int, int]],
) -> None:
    semantic = _semantic(tmp_path, head + OWN_OUTPUT + clause)

    diagnostics = build_project_completed_semantic_result(semantic).diagnostics
    assert _located(diagnostics) == [
        ("PIE-S2802", 21 + shift, 25),
        ("PIE-S2802", 31 + shift, 17),
        *((code, line + shift, column) for code, line, column in expected),
    ]


# Each case: the parent, its reader, and every diagnostic after the parent's
# PIE-S2802. A nested field read reports beside the diagnostics of the clause
# that checks its expression, in source order with them; a relation that an
# earlier clause stops first does not reach it, as for an unknown field.
CLAUSE_ORDER = {
    "where-then-select": (
        MATRIX_HEAD,
        _NO_JOIN + "    where bogus == 1\n    select:\n        id\n"
        "        y = recent_orders == zzz\n",
        [("PIE-S2102", 24, 11), ("PIE-S2805", 27, 13), ("PIE-S2102", 27, 30)],
    ),
    "unknown-before-nested": (
        MATRIX_HEAD,
        _NO_JOIN + "    select:\n        id\n        y = zzz == recent_orders\n",
        [("PIE-S2102", 26, 13), ("PIE-S2805", 26, 20)],
    ),
    "let-same-expression": (
        MATRIX_HEAD,
        _NO_JOIN + "    let x = recent_orders == zzz\n" + _SELECT_ID,
        [("PIE-S2805", 24, 13), ("PIE-S2102", 24, 30)],
    ),
    "where-then-order": (
        MATRIX_HEAD,
        _NO_JOIN
        + '    where id + "a" > 1\n'
        + _SELECT_ID
        + "    order by recent_orders\n",
        [("PIE-S2105", 24, 11)],
    ),
    "window-then-order": (
        MATRIX_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "        r = row_number() window(order by zzz)\n"
        + "    order by recent_orders\n",
        [("PIE-S2102", 26, 42)],
    ),
    "select-direct-then-unknown": (
        MATRIX_HEAD,
        _NO_JOIN + "    select:\n        recent_orders\n        zzz\n",
        [("PIE-S2805", 25, 9), ("PIE-S2102", 26, 9)],
    ),
    "select-rename-then-unknown": (
        MATRIX_HEAD,
        _NO_JOIN + _SELECT_ID + "        r = recent_orders\n        z = zzz\n",
        [("PIE-S2805", 26, 13), ("PIE-S2102", 27, 13)],
    ),
    # A window computation stops at its first refused step, as in a single
    # file: what it refuses before the step reading a nested field stays,
    # and a nested field read stops it as an unknown field would.
    "window-refused-before-nested": (
        MATRIX_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "        r = lag(recent_orders) window(partition by zzz order by id)\n",
        [("PIE-S2805", 26, 17), ("PIE-S2102", 26, 52)],
    ),
    "window-without-order": (
        MATRIX_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "        r = lag(recent_orders) window(partition by region)\n",
        [("PIE-S2103", 26, 13), ("PIE-S2805", 26, 17)],
    ),
    "window-stopped-at-nested": (
        MATRIX_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "        r = lag(zzz) window(partition by recent_orders order by id)\n",
        [("PIE-S2805", 26, 42)],
    ),
    "hidden-window-refused-before-nested": (
        MATRIX_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "    qualify lag(recent_orders) window(partition by zzz order by id) == 1\n",
        [("PIE-S2805", 26, 17), ("PIE-S2102", 26, 52)],
    ),
    "join-window-refused-before-nested": (
        MATRIX_HEAD,
        _JOIN
        + _SELECT_JOINED
        + "        r = lag(p.recent_orders) window(partition by zzz order by"
        " customers.id)\n",
        [("PIE-S2805", 28, 17), ("PIE-S2102", 28, 54)],
    ),
    "join-qualify-same-expression": (
        MATRIX_HEAD,
        _JOIN
        + _SELECT_JOINED
        + "        r = row_number() window(order by customers.id)\n"
        + "    qualify p.recent_orders == 1 and zzz == 1\n",
        [("PIE-S2805", 29, 13), ("PIE-S2332", 29, 38)],
    ),
    "join-select-same-expression": (
        MATRIX_HEAD,
        _JOIN + _SELECT_JOINED + "        v = zzz + p.recent_orders\n",
        [("PIE-S2102", 28, 13), ("PIE-S2805", 28, 19)],
    ),
    "join-row-let-same-expression": (
        MATRIX_HEAD,
        _JOIN + "    let v = zzz + p.recent_orders\n" + _SELECT_JOINED,
        [("PIE-S2102", 26, 13), ("PIE-S2805", 26, 19)],
    ),
    "join-where-same-expression": (
        MATRIX_HEAD,
        _JOIN
        + "    where zzz == 1 and p.recent_orders == 1 and yyy == 2\n"
        + _SELECT_JOINED,
        [("PIE-S2102", 26, 11), ("PIE-S2805", 26, 24), ("PIE-S2102", 26, 49)],
    ),
    "replayed-where-same-expression": (
        JOINED_PARENT_HEAD,
        _NO_JOIN + "    where recent_orders == 1 and zzz == 2\n" + _SELECT_ID,
        [("PIE-S2805", 26, 11), ("PIE-S2102", 26, 34)],
    ),
    "replayed-qualify-same-expression": (
        JOINED_PARENT_HEAD,
        _NO_JOIN + _SELECT_ID + "        r = row_number() window(order by id)\n"
        "    qualify recent_orders == 1 and zzz == 1\n",
        [("PIE-S2805", 29, 13), ("PIE-S2332", 29, 36)],
    ),
    "replayed-window-refused-before-nested": (
        JOINED_PARENT_HEAD,
        _NO_JOIN
        + _SELECT_ID
        + "        r = lag(recent_orders) window(partition by zzz order by id)\n",
        [("PIE-S2805", 28, 17), ("PIE-S2102", 28, 52)],
    ),
    "replayed-where-stops-first": (
        JOINED_PARENT_HEAD,
        _NO_JOIN + "    where bogus == 1\n    select:\n        id\n"
        "        y = recent_orders == 1\n",
        [("PIE-S2102", 26, 11)],
    ),
    "replayed-order-after-unreported-select": (
        JOINED_PARENT_HEAD,
        _NO_JOIN + '    select:\n        id\n        z = id + "a"\n'
        "    order by recent_orders\n",
        [("PIE-S2805", 29, 14)],
    ),
}


@pytest.mark.parametrize("case", sorted(CLAUSE_ORDER))
def test_a_nested_read_reports_with_the_clause_that_checks_it(
    tmp_path: Path, case: str
) -> None:
    head, reader, expected = CLAUSE_ORDER[case]
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, head + reader)
    ).diagnostics

    parent = ("PIE-S2802", 21, 25) if head == MATRIX_HEAD else ("PIE-S2802", 23, 25)
    assert _located(diagnostics) == [parent, *expected]


@pytest.mark.parametrize(
    ("reader", "expected"),
    [
        (
            "query u:\n    union all parent, parent\n",
            [("PIE-S2805", 23, 15), ("PIE-S2805", 23, 23)],
        ),
        (
            "query u:\n    union distinct parent, parent\n",
            [("PIE-S2805", 23, 20), ("PIE-S2805", 23, 28)],
        ),
        (
            "query u:\n    intersect distinct parent, parent\n",
            [("PIE-S2805", 23, 24), ("PIE-S2805", 23, 32)],
        ),
        (
            "query u:\n    except all parent, parent\n",
            [("PIE-S2805", 23, 16), ("PIE-S2805", 23, 24)],
        ),
        (
            "query flat:\n    from customers\n    select:\n        id\n        region\n"
            "        n = id\nquery u:\n    union all flat, parent\n",
            [("PIE-S2805", 29, 21)],
        ),
    ],
    ids=["union-all", "union", "intersect", "except-all", "one-operand"],
)
def test_each_set_operand_with_a_nested_field_is_refused(
    tmp_path: Path, reader: str, expected: list[tuple[str, int, int]]
) -> None:
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, MATRIX_HEAD + reader)
    ).diagnostics

    assert _located(diagnostics) == [("PIE-S2802", 21, 25), *expected]
    assert diagnostics[1].message == (
        "Set operand parent outputs nested relation field recent_orders: a set "
        "operation over a collected relation is not available."
    )


@pytest.mark.parametrize("joined", [False, True], ids=["no-join", "join"])
def test_select_distinct_with_a_collect_read_is_refused_at_the_read(
    tmp_path: Path, joined: bool
) -> None:
    source = (
        JOINED
        + "    select distinct:\n        rows.id\n        nested = collect children\n"
        if joined
        else SOURCE.replace(
            "    select:\n        nested", "    select distinct:\n        nested"
        )
    )
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, source)
    ).diagnostics

    line, column = (15, 18) if joined else (13, 18)
    assert _located(diagnostics) == [
        ("PIE-S2802", line, column),
        ("PIE-S2805", line, column),
    ]
    assert diagnostics[1].message == (
        "Collect relation read children cannot be part of SELECT DISTINCT: a "
        "collected relation has no equality."
    )


def test_each_collect_read_under_select_distinct_is_refused_whatever_its_name(
    tmp_path: Path,
) -> None:
    source = SOURCE.replace(
        "    select:\n        nested = collect children\n",
        "    select distinct:\n        nested = collect children\n"
        "        nested = collect children\n",
    )
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, source)
    ).diagnostics

    # The duplicate name is its own error; neither read wins over the other.
    assert _located(diagnostics) == [
        ("PIE-S2802", 13, 18),
        ("PIE-S2802", 14, 18),
        ("PIE-S2805", 13, 18),
        ("PIE-S2305", 14, 9),
        ("PIE-S2805", 14, 18),
    ]


@pytest.mark.parametrize(
    "reader",
    [
        "query reader:\n    from customers\n    where exists parent\n" + _SELECT_ID,
        "query reader:\n    from customers\n"
        + _SELECT_ID
        + "        t = scalar parent.id\n",
        _NO_JOIN + _SELECT_ID,
        _JOIN + _SELECT_JOINED + "        region = p.region\n",
        "query reader:\n    from customers\n    let p = parent\n"
        "    right join p on customers.id == p.id\n    select:\n        id = p.id\n",
    ],
    ids=["exists", "scalar-column", "from", "join", "right-join"],
)
def test_reading_a_collect_owner_without_its_nested_field_completes(
    tmp_path: Path, reader: str
) -> None:
    semantic = _semantic(tmp_path, MATRIX_HEAD + reader)

    completed: Any = build_project_completed_semantic_result(semantic)
    assert _located(completed.diagnostics) == [("PIE-S2802", 21, 25)]
    (entry,) = (
        item
        for item in completed.effective_outputs.entries
        if item.owner.identity.declared_name == "reader"
    )
    assert type(entry).__name__ in {
        "ProjectExistingEffectiveOutput",
        "ProjectCompletedEffectiveOutput",
    }


_SHAPES = MATRIX_HEAD.split("query parent:\n")[0]
_RECENT = "query parent:\n    let recent:\n        from orders\n        select id\n"
_ORDERED = _RECENT + "        order by id\n"
_LEFT_JOIN = (
    "    from customers\n    let o = orders\n"
    "    left join o on customers.id == o.customer_id\n"
)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            _RECENT
            + _LEFT_JOIN
            + "    select:\n        id = customers.id\n        x = collect recent\n"
            "        y = customers.nope\n",
            [("PIE-S2802", 19, 13), ("PIE-S2102", 20, 13), ("PIE-S2804", 19, 13)],
        ),
        (
            "query parent:\n"
            + _LEFT_JOIN
            + "    select:\n        id = customers.id\n        x = collect orders\n"
            "        y = customers.nope\n",
            [("PIE-S2803", 16, 13), ("PIE-S2802", 16, 13), ("PIE-S2102", 17, 13)],
        ),
        (
            _ORDERED + _LEFT_JOIN + "    select distinct:\n        id = customers.id\n"
            "        x = collect recent\n        y = customers.nope\n",
            [("PIE-S2802", 20, 13), ("PIE-S2805", 20, 13), ("PIE-S2102", 21, 13)],
        ),
        (
            _ORDERED + "    from customers\n    where nope > 1\n    group by region\n"
            "    select:\n        region\n        x = collect recent\n",
            [("PIE-S2803", 20, 13), ("PIE-S2802", 20, 13), ("PIE-S2102", 16, 11)],
        ),
        (
            _ORDERED + "    from customers\n    group by region\n    select:\n"
            "        region\n        bad = region + 1\n        x = collect recent\n",
            [("PIE-S2803", 20, 13), ("PIE-S2802", 20, 13), ("PIE-S2105", 19, 15)],
        ),
    ],
    ids=[
        "join-unordered",
        "join-not-a-let",
        "join-distinct",
        "grouped-where",
        "grouped-select",
    ],
)
def test_a_refused_collect_read_keeps_the_other_diagnostics_of_its_body(
    tmp_path: Path, source: str, expected: list[tuple[str, int, int]]
) -> None:
    # A Collect item that does not type stops neither the SELECT items after
    # it nor, in a grouped body, its WHERE and SELECT; a JOIN body's DISTINCT
    # refusal stands in source order with its SELECT diagnostics.
    diagnostics = build_project_completed_semantic_result(
        _semantic(tmp_path, _SHAPES + source)
    ).diagnostics

    assert _located(diagnostics) == expected


_COLLECT_X = "    from customers\n    select:\n        id\n        x = collect recent\n"


@pytest.mark.parametrize(
    ("source", "owner", "expected"),
    [
        (
            _SHAPES + _RECENT + "        order by nothing\n" + _COLLECT_X,
            "parent",
            [("PIE-S2802", 18, 13), ("PIE-S2102", 14, 18)],
        ),
        # A key named alone may name a SELECT output, which completion does not
        # order by yet: no unknown field, the owner's completion fallback.
        (
            _SHAPES
            + _RECENT.replace("select id", "select oid = id")
            + "        order by oid\n"
            + _COLLECT_X,
            "parent",
            # Its Collect read's own PIE-S2802 is the owner's error, so no
            # completion fallback beside it.
            [("PIE-S2802", 18, 13)],
        ),
        # A key that reads a nested field is the reader's own error: no
        # completion fallback beside it.
        (
            MATRIX_HEAD + "query reader:\n    let x:\n        from parent\n"
            "        select id\n        order by id, recent_orders\n"
            "    from customers\n    select:\n        id\n        n = collect x\n",
            "reader",
            [("PIE-S2802", 21, 25), ("PIE-S2802", 30, 13), ("PIE-S2805", 26, 22)],
        ),
    ],
    ids=["unknown-key", "output-name-key", "nested-key"],
)
def test_a_collected_let_whose_order_does_not_resolve_is_not_collected(
    tmp_path: Path, source: str, owner: str, expected: list[tuple[str, int, int]]
) -> None:
    completed: Any = build_project_completed_semantic_result(
        _semantic(tmp_path, source)
    )
    # The owner's row is known only over its let's completed order (D-S04-4
    # R4), so the let's ORDER BY error is the owner's.
    assert _located(completed.diagnostics) == expected
    (entry,) = (
        item
        for item in completed.effective_outputs.entries
        if item.owner.identity.declared_name == owner
        and item.owner.let_position is None
    )
    assert type(entry).__name__ == "ProjectEffectiveOutputTerminal"


@pytest.mark.parametrize("join_reader", [False, True], ids=["alone", "join-reader"])
def test_readers_of_an_owner_whose_collected_let_does_not_order_wait_for_it(
    tmp_path: Path, join_reader: bool
) -> None:
    # Its columns are not known before completion and its error is reported,
    # so each reader follows it, as a reader of any relation that fails,
    # whatever else reads it.
    source = (
        _SHAPES
        + _RECENT
        + "        order by nothing\n"
        + _COLLECT_X
        + "query reader:\n    from parent\n    select:\n        id\n"
        + "query scalar_reader:\n    from customers\n    select:\n"
        + "        id\n        s = scalar parent.id\n"
        + (
            "query join_reader:\n    from customers\n    let p = parent\n"
            "    inner join p on customers.id == p.id\n"
            "    select:\n        id = customers.id\n"
            if join_reader
            else ""
        )
    )
    completed: Any = build_project_completed_semantic_result(
        _semantic(tmp_path, source)
    )

    assert _located(completed.diagnostics) == [
        ("PIE-S2802", 18, 13),
        ("PIE-S2102", 14, 18),
    ]
    entries = {
        item.owner.identity.declared_name: type(item).__name__
        for item in completed.effective_outputs.entries
        if item.owner.let_position is None
    }
    assert (
        entries["reader"]
        == entries["scalar_reader"]
        == ("ProjectEffectiveOutputTerminal")
    )


@pytest.mark.parametrize(
    ("condition", "ref"),
    [
        ("o.recent_orders == 1 for o in parent", "o.recent_orders"),
        ("o.id == parent.recent_orders for o in orders", "parent.recent_orders"),
    ],
)
def test_an_any_before_a_later_join_names_its_nested_read_as_written(
    tmp_path: Path, condition: str, ref: str
) -> None:
    diagnostics = build_project_completed_semantic_result(
        _semantic(
            tmp_path,
            MATRIX_HEAD + "query reader:\n    let o2 = orders\n    from parent\n"
            f"    where any({condition})\n"
            "    inner join o2 on parent.id == o2.customer_id\n"
            "    select:\n        x = parent.id\n",
        )
    ).diagnostics

    # The SEMI JOIN this ANY becomes is still an ANY test (S04 §5.3).
    assert [d.message for d in diagnostics if d.code == "PIE-S2805"] == [
        f"Nested relation field {ref} cannot be read in an ANY test: a collected "
        "relation has no comparison, ordering, grouping or scalar value."
    ]
    assert not any("_pietto_any" in d.message for d in diagnostics)


def test_a_nested_field_passed_to_a_def_is_a_read_not_a_selection(
    tmp_path: Path,
) -> None:
    # `f` returns its argument, so the call inlines to the field itself; the
    # field is still read in a SELECT expression, not selected.
    diagnostics = build_project_completed_semantic_result(
        _semantic(
            tmp_path,
            MATRIX_HEAD
            + "def f(x: Int) -> Int: return x\n"
            + _NO_JOIN
            + "    select:\n        id\n        v = f(recent_orders)\n",
        )
    ).diagnostics

    assert _located(diagnostics) == [("PIE-S2802", 21, 25), ("PIE-S2805", 27, 15)]
    assert "cannot be read in a SELECT expression" in diagnostics[1].message


def _key_facts(semantic: ProjectSemanticResult) -> tuple[object, ...]:
    """The phase-62 key and FD subjects with their key and FD counts, and the
    parent's IR keys, FDs, value classes and FD universe, by name."""

    keys = build_project_row_keys(semantic)
    fds = build_project_value_fds(keys)
    subjects: Any = keys.subjects
    completed: Any = build_project_completed_semantic_result(semantic)
    (properties,) = (
        entry.properties
        for entry in completed.effective_outputs.base.entries
        if entry.owner.identity.declared_name == "parent"
        and entry.owner.let_position is None
    )

    def names(classes: Any) -> tuple[tuple[str, ...], ...]:
        return tuple(
            tuple(member.evidence.name for member in item.members) for item in classes
        )

    return (
        tuple(subject.identity.source.identity.declared_name for subject in subjects),
        repr(keys.candidate_keys).count("Candidate"),
        tuple(basis.universe.scope.owner.identity.declared_name for basis in fds.bases),
        repr(fds).count("FunctionalDependency"),
        tuple(names(key.determinants) for key in properties.keys),
        tuple((names(fd.determinants), names(fd.dependents)) for fd in properties.fds),
        names(properties.value_classes),
        names(properties.fd_index.universe),
    )


def test_nested_fields_never_reach_keys_dependencies_or_inspection_kinds(
    tmp_path: Path,
) -> None:
    keyed = SOURCE.replace(
        "    note: Text | None\n", "    note: Text | None\n    row_key = unique(id)\n"
    ).replace(
        "        nested = collect children\n",
        "        id\n        note\n        nested = collect children\n",
    )
    with_collect = _semantic(tmp_path / "with", keyed)
    without = _semantic(
        tmp_path / "without", keyed.replace("        nested = collect children\n", "")
    )

    # The keys and FDs are those of the relation without its Collect item: a
    # nested value has no equality, so no key determines it (AC-10). Phase-62
    # keys and FDs hold only for source rows, so the parent is none of their
    # subjects; its IR keys and FDs are its own.
    observed = _key_facts(with_collect)
    assert observed == _key_facts(without)
    assert observed[0] == observed[2] == ("rows",)
    assert observed[4] == ((("id",),),)
    assert observed[5] == (((("id",),), (("note",),)),)
    assert observed[6] == observed[7] == (("id",), ("note",))
    assert "nested" not in repr(observed)
    # The phase-62 IR inspection document has a closed type-kind vocabulary
    # (S06 owns its nested encoding): it refuses the program deterministically.
    with pytest.raises(ValueError, match="unknown_enumeration"):
        build_project_ir_pipeline(
            semantic_result=with_collect,
            allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
        )


def test_the_check_outputs_name_no_internal_nested_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _parsed_files(
        tmp_path,
        {
            "main.pietto": MATRIX_HEAD
            + NESTED_READS["join-where-eq"][0]
            + "query u:\n    union all parent, parent\n"
        },
    ).ok
    root = tmp_path / "project"
    for output in ("text", "json"):
        assert cli_main(["check", "--project", str(root), "--format", output]) == 1
        captured = capsys.readouterr()
        printed = captured.out + captured.err
        assert "PIE-S2805" in printed
        assert "nested_relation" not in printed and "<nested" not in printed


def test_an_unnest_argument_is_no_nested_field_read(tmp_path: Path) -> None:
    # The language reference example, in an EXPLICIT_MODULES project: S05
    # binds the Unnest let, so only the lowering boundary remains (AC-03).
    source = (
        "shape Order:\n    id: Int\n    customer_id: Int\nsource orders: Order = "
        'postgres.table("orders")\nquery customers_with_orders:\n    let recent:\n'
        "        from orders\n        select:\n            id\n        order by id\n"
        "    from orders\n    select:\n        customer_id\n"
        "        recent_orders = collect recent\nquery expanded:\n"
        "    from customers_with_orders\n"
        "    let o = unnest(customers_with_orders.recent_orders)\n    cross join o\n"
        "    select:\n        customer_id\n"
    )
    semantic = _semantic(tmp_path, source)

    assert _checked(semantic) == [
        ("PIE-S2802", 14, 25),
        ("PIE-S2802", 17, 5),
    ]
    (unnest,) = _facts(semantic).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE


@pytest.mark.parametrize(
    "source",
    [
        # A query header parameter read inside the collected let.
        "query parent(cutoff: Int):\n    let recent:\n        from orders\n"
        "        where id > cutoff\n        select:\n            id\n"
        "        order by id\n    from customers\n    select:\n        id\n"
        "        recent_orders = collect recent\n",
        # Group in another query, read it with `from`, collect a capturing let.
        "query g:\n    from orders\n    group by customer_id\n    select:\n"
        "        customer_id\n        n = count()\nquery parent:\n    let top:\n"
        "        capture g\n        from orders\n"
        "        where orders.customer_id == g.customer_id\n        select:\n"
        "            id\n        order by id\n        limit 3\n    from g\n"
        "    select:\n        customer_id\n        top_orders = collect top\n",
    ],
    ids=["header-parameter", "grouped-stage"],
)
def test_admitted_collect_shapes_report_only_the_lowering_boundary(
    tmp_path: Path, source: str
) -> None:
    semantic = _semantic(tmp_path, ADMISSION_HEAD + source)

    semantic_facts = semantic.module_semantic_facts
    assert semantic_facts is not None
    reads = [
        read
        for environment in semantic_facts.environments
        for facts in environment.relation_facts
        for read in facts.collect_reads
    ]
    assert len(reads) == 1 and reads[0].nested_type is not None
    assert [code for code, _, _ in _checked(semantic)] == ["PIE-S2802"]
    # Rows that tie and rows that repeat stay a bag; no row is the empty bag,
    # and a child field keeps its own nullability.
    assert reads[0].multiplicity == "bag" and reads[0].empty_value == ()
