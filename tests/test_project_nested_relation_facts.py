"""S03 nested relation facts retain typed occurrences before lowering exists."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectParseCheckResult,
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
SOURCE = (
    HEAD
    + """query parent:
    let children:
        from rows
        select:
            id
            note
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
        select:
            id
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
    assert collect.nested_type.container_nullability.value == "non_null"
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
def test_joined_collect_owner_fails_closed_with_its_own_diagnostics(
    tmp_path: Path, tail: str
) -> None:
    semantic = _semantic(tmp_path, JOINED + tail)

    (collect,) = _facts(semantic).collect_facts
    assert collect.status is ProjectNestedRelationFactStatus.AVAILABLE
    checked = _checked(semantic)
    assert [code for code, _, _ in checked if code == "PIE-S2802"] == ["PIE-S2802"]
    assert {code for code, _, _ in checked} <= {"PIE-S2802", "PIE-S2105"}
    assert ("PIE-S2105" in {code for code, _, _ in checked}) == ("bad =" in tail)


def test_a_collect_owner_reader_follows_the_owner_error(
    tmp_path: Path,
) -> None:
    # The reader of a relation that fails reports nothing of its own, as the
    # reader of any relation whose failure is reported.
    semantic = _semantic(
        tmp_path,
        SOURCE + "query reader:\n    from parent\n    select:\n        nested\n",
    )

    assert _checked(semantic) == [("PIE-S2802", 13, 18)]


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
    assert unnest.source_field is collect.output
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
    ("sources", "candidates"),
    [
        ({"main.pietto": _expanded("cross join child", binding="ghost")}, 0),
        (
            {
                "main.pietto": SOURCE
                + """query expanded:
    let p = parent
    let child = unnest(p.nested)
    from p
    cross join child
    select:
        id
"""
            },
            0,
        ),
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
    ids=["unknown-binding", "binding-after-let", "unknown-input", "blocked-input"],
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
    semantic = _semantic(
        tmp_path, _expanded("cross join child\n    left join child on True")
    )

    (unnest,) = _facts(semantic).unnest_inputs
    assert unnest.status is ProjectNestedRelationFactStatus.UNAVAILABLE
    assert unnest.reason is ProjectNestedRelationFactReason.JOIN_UNAVAILABLE
    assert len(unnest.join_candidates) == 2


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

    The control names `parent` instead, an input whose rows a Collect read
    keeps unavailable, as the rows of an Unnest are until S05 binds them.
    """

    unnest = _messages(_semantic(tmp_path / "unnest", source))
    alias = _messages(
        _semantic(tmp_path / "alias", source.replace("unnest(parent.nested)", "parent"))
    )
    return unnest, alias


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
    # D71.02: until S05 binds it, an Unnest JOIN is one JOIN input in its
    # place, so it reports what any JOIN of an unavailable input reports, in
    # the same order. A JOIN without `on` of another kind than CROSS also
    # names the inputs its `on` would match, as for a known input, in place
    # of the relation's fallback.
    unnest, alias = _beside_alias(tmp_path, _expanded(join))

    gate = ("PIE-S2802", 16, 5, _UNNEST_GATE)
    hint = ("PIE-S2333", 17, 5, _WRITE_ON[1])
    fallback = (
        "PIE-S2333",
        14,
        1,
        "Project relation semantic completion is unavailable: expanded",
    )
    writes_on = not join.startswith("cross") and " on " not in join
    assert (hint in unnest) is writes_on
    # The control's input `parent` fails with its own PIE-S2802, so its
    # relation reports no fallback beside it.
    assert fallback not in alias
    assert [item for item in unnest if item != hint] == [
        alias[0],
        gate,
        *(item for item in alias[1:] if item != fallback),
    ]
    cross_on = ("PIE-S2336", 17, 5, "CROSS JOIN cannot have ON or VIA.")
    assert (cross_on in unnest) is (join == "cross join child on True")


@pytest.mark.parametrize(
    ("body", "let_line"),
    [
        # A table-function FROM.
        (
            "query q:\n    from generate_series(1, 3, 1) as n\n"
            "    let child = unnest(n.nested)\n    cross join child\n"
            "    select:\n        v = n.value\n",
            16,
        ),
        # A relation let beside the Unnest let.
        (
            "query q:\n    let extra:\n        from rows\n        select:\n"
            "            id\n    from parent\n    let child = unnest(parent.nested)\n"
            "    cross join child\n    where parent.id in extra\n"
            "    select:\n        id = parent.id\n",
            20,
        ),
        # An Unnest let inside a relation let.
        (
            "query q:\n    let sub:\n        from parent\n"
            "        let child = unnest(parent.nested)\n        cross join child\n"
            "        select:\n            id = parent.id\n    from sub\n"
            "    select:\n        id\n",
            17,
        ),
    ],
)
def test_an_unnest_join_of_a_block_body_is_no_unknown_relation(
    tmp_path: Path, body: str, let_line: int
) -> None:
    # D71.02 holds in every relation body: the JOIN is the Unnest let's one
    # input in its place, never a named relation the module lacks.
    checked = _checked(_semantic(tmp_path, SOURCE + body))

    assert "PIE-S2301" not in {code for code, _, _ in checked}
    assert ("PIE-S2802", let_line, 5 if let_line != 17 else 9) in checked


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
    assert alias[1:] == [later]
    assert unnest == [
        alias[0],
        ("PIE-S2802", 16, 5, _UNNEST_GATE),
        ("PIE-S2333", 17, 5, _WRITE_ON[1]),
        later,
    ]


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
        (
            "    where any(r.id == 1 for r in rows)\n"
            "    let child = unnest(parent.nested)\n    cross join child\n"
            "    let c = rows\n    left join c on c.id == child.id\n",
            17,
        ),
    ],
    ids=["between-joins", "on-reads-it", "cross-on-first", "after-any"],
)
def test_joins_beside_an_unnest_join_report_what_they_report_beside_an_alias_let(
    tmp_path: Path, body: str, let_line: int
) -> None:
    # The Unnest JOIN stays one JOIN input in its place (D71.02): no other
    # JOIN of the relation reads it as missing, and every diagnostic keeps the
    # order an alias let in that place gives.
    unnest, alias = _beside_alias(
        tmp_path,
        SOURCE
        + "query expanded:\n    from parent\n"
        + body
        + "    select:\n        id\n",
    )

    assert unnest == [alias[0], ("PIE-S2802", let_line, 5, _UNNEST_GATE), *alias[1:]]
    assert not any("unknown" in message for _, _, _, message in unnest)


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
    semantic = _semantic(
        tmp_path,
        HEAD
        + """query q:
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
""",
    )

    facts = _facts(semantic)
    assert len(facts.collect_facts) == 1
    (unnest,) = facts.unnest_inputs
    # The table function binding is visible, and has no nested output.
    assert unnest.source_target is not None
    assert unnest.source_target.target_occurrence.table_function is not None
    assert unnest.status is ProjectNestedRelationFactStatus.UNAVAILABLE
    assert unnest.reason is ProjectNestedRelationFactReason.OUTPUT_UNAVAILABLE


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
        "            id\n    from rows\n    select:\n        id\n"
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
    # A collected relation is never None, and has exactly one layer.
    with pytest.raises(ValueError, match="never None"):
        replace(nested, container_nullability=ProjectRowFieldNullability.NULLABLE)
    with pytest.raises(ValueError, match="one collection layer"):
        replace(nested, collection_depth=True)
    # Another Collect's child type is not this one's, and equal copies of the
    # child fields are not the semantic root's field facts.
    with pytest.raises(ValueError, match="resolved local let"):
        replace(collect, nested_type=other.nested_type)
    rejected(
        nested_type=replace(
            nested,
            element_fields=tuple(
                replace(item, field=replace(item.field))
                for item in nested.element_fields
            ),
        )
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
    with pytest.raises(ValueError, match="one exact Collect authority"):
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
    # written before a later JOIN keeps its own place.
    parsed = _parsed_files(
        tmp_path,
        {
            "main.pietto": HEAD
            + "query ex:\n    from rows\n"
            + body
            + "    select:\n        rows.id\n"
        },
    )
    assert parsed.ok, parsed.diagnostics
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

    semantic = build_empty_project_semantic_result(parsed)
    (unnest,) = _facts(semantic).unnest_inputs
    assert [join.kind.value for join in unnest.join_candidates] == ["cross"]
    let_line = 7 + body.count("\n", 0, body.index("let child"))
    assert ("PIE-S2802", let_line, 5) in _checked(semantic)


def test_a_hidden_any_join_over_an_unnest_name_is_no_unnest_join(
    tmp_path: Path,
) -> None:
    # A `where any(...)` before the JOIN reads its name as a relation; only
    # the written JOIN is the Unnest's.
    semantic = _semantic(
        tmp_path,
        SOURCE
        + """query expanded:
    from parent
    let child = unnest(parent.nested)
    where any(x.id == 1 for x in child)
    cross join child
    select:
        id
""",
    )

    (unnest,) = _facts(semantic).unnest_inputs
    assert [join.kind.value for join in unnest.join_candidates] == ["cross"]
    assert unnest.status is ProjectNestedRelationFactStatus.AVAILABLE
