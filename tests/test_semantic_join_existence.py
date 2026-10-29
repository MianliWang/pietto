"""Authored existence JOINs retain left occurrences and predicate dependencies."""

from pathlib import Path
from collections.abc import Callable, Sequence
from dataclasses import replace
import json

import pytest

from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    ProjectCurrentJoinGrainWitness,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_multifact import (
    ProjectActualGrainAuthorityKind,
    ProjectCurrentMultiFactRegion,
)
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_current_join_inputs import ProjectCurrentPreMatchInputs
from pietto import cli
from pietto.errors import Diagnostic, Severity
from pietto.semantic.model import CheckMode
from pietto.parser_api import parse_source
from pietto.semantic.analyzer import analyze_project_namespace
from pietto.semantic import analyze
from pietto.ir import build_ir
from pietto.ast_nodes import AuthoredJoinKind, QueryDef
from _pietto_project_join import (
    _completed,
    _parsed,
    _source,
)
from _pietto_project_join_full import _two_current_globals_full, _unique_source
from _pietto_project_join_output import (
    _output,
    _tail_source,
)
from _pietto_semantic_joins import JOIN_PREFIX, located, run_joins


type Row = tuple[int, int | None]
type Predicate = Callable[[int | None, int | None], bool | None]


def _existence(kind: str, name: str, predicate: str) -> str:
    """The `where any(...)` filter that replaces a retired semi or anti JOIN."""
    negation = "not " if kind == "anti" else ""
    return f"where {negation}any({predicate} for {name} in {name})"


def _existence_source(predicate: str, kind: str) -> str:
    """`_source` with its JOIN of `r` replaced by an existence filter of `r`."""
    return _source(predicate).replace(
        f"    inner join r on {predicate}\n",
        f"    {_existence(kind, 'r', predicate)}\n",
    )


@pytest.mark.parametrize("kind", ("inner", "left", "cross", "right", "full"))
def test_old_kind_green_control(tmp_path: Path, kind: str) -> None:
    completed = _completed(
        tmp_path, _source(None if kind == "cross" else "lhs.id == r.id", kind=kind)
    )
    assert completed.ok, completed.diagnostics


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("predicate", ("r.id == next_right.id", "Link(r, next_right)"))
def test_consumed_right_cannot_be_a_later_condition_source(
    tmp_path: Path, kind: str, predicate: str
) -> None:
    following = f"    let next_right = rhs\n    inner join next_right on {predicate}\n"
    source = _existence_source("lhs.id == r.id", kind).replace(
        "    select:\n", following + "    select:\n"
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok and not completed.effective_outputs.current_regions
    conditions = completed.effective_outputs.operative_conditions
    assert conditions is not None and conditions.entries[0].ready
    assert not conditions.entries[1].ready
    assert len(conditions.entries[1].environment.bindings) == 3


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("later_kind", ("inner", "right", "full"))
def test_following_join_keeps_left_and_its_new_right_without_resurrection(
    tmp_path: Path, kind: str, later_kind: str
) -> None:
    source = _existence_source("lhs.id == r.id", kind).replace(
        "    select:\n",
        "    let next_right = rhs\n"
        f"    {later_kind} join next_right on lhs.id == next_right.id\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    first, second = region.joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(second, ProjectCurrentBinaryJoin)
    assert all(
        field.binding is not first.use.target_binding
        for field in second.condition.environment.fields
    )
    assert tuple(b.identity.binding_position for b in region.ledger.bindings) == (
        0,
        1,
        2,
    )
    assert all(
        field.introduction_use is not first.input_uses[1]
        for field in second.output.row_shape.fields
    )
    assert len(second.input_uses) == 2


# A JOIN-prefix `[not] any` is one hidden SEMI/ANTI JOIN, the only way left to
# reach the existence JOIN that `semi join`/`anti join` authored before S6: its
# output is the left row, so the left keys, FDs, grain and nulling carry over.
_LATER_JOIN = "    let later = rhs\n    cross join later\n"


def _prefix_existence(source: str, join: str, kind: str, predicate: str) -> str:
    """``source`` with the JOIN line ``join`` of `r` replaced by a JOIN-prefix
    existence filter of `r`, followed by a later JOIN."""
    assert source.count(join) == 1
    return source.replace(
        join, f"    {_existence(kind, 'r', predicate)}\n" + _LATER_JOIN
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_prefix_any_keeps_left_keys_fds_and_grain_as_exact_images(
    tmp_path: Path, kind: str
) -> None:
    predicate = "lhs.key == r.key or lhs.allow_any"
    source = _prefix_existence(
        _unique_source("inner", predicate),
        f"    inner join r on {predicate}\n",
        kind,
        predicate,
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    join, later = region.joins
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.kind is AuthoredJoinKind(kind)
    assert (
        later.kind is AuthoredJoinKind.CROSS and later.left_input.output is join.output
    )
    left, output = join.left_input, join.properties.relational
    assert left.keys and left.fds and left.grain.active
    assert len(join.output.row_shape.fields) == len(left.fields)
    assert tuple(key.strength for key in output.keys) == tuple(
        key.strength for key in left.keys
    )
    for before, after in zip(left.fds, output.fds, strict=True):
        assert before.strength is after.strength
        assert tuple(
            tuple(f.field_position for f in c.members) for c in before.determinants
        ) == tuple(
            tuple(f.field_position for f in c.members) for c in after.determinants
        )
        assert tuple(
            tuple(f.field_position for f in c.members) for c in before.dependents
        ) == tuple(tuple(f.field_position for f in c.members) for c in after.dependents)
    assert output.grain.state is left.grain.state
    assert len(output.grain.factors) == len(left.grain.factors)
    assert len(output.grain.active) == len(left.grain.active)
    assert all(
        isinstance(f, ProjectJoinGrainFactorIdentity)
        and f.introduction_use == join.input_uses[0].ref
        for f in output.grain.active
    )
    witness = output.grain.witness
    assert isinstance(witness, ProjectCurrentJoinGrainWitness)
    assert witness.left is left.grain and witness.right is join.right_input.grain
    assert witness.condition is join.condition
    # Only the later JOIN's right input is a grain authority: the existence
    # test's right rows never reach its output.
    candidates = ProjectCurrentMultiFactRegion(region=region).actual_candidates
    assert [
        a.evidence[0]
        for c in candidates
        for a in c.authorities
        if a.kind is ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT
    ] == [later]
    # A generic predicate establishes no cross-side FD.
    assert not output.grain.dependencies


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_prefix_any_keeps_prior_nulling_and_a_global_left_at_most_one(
    tmp_path: Path, kind: str
) -> None:
    chained = _source("Link(lhs, r)", kind="left").replace(
        "    let r = rhs\n    left join r on Link(lhs, r)\n",
        "    let mid = rhs\n    left join mid on Link(lhs, mid)\n"
        "    let nulled = lhs\n    left join nulled on Link(nulled, mid)\n"
        "    let r = rhs\n    inner join r on nulled.id == r.id\n",
    )
    source = _prefix_existence(
        chained, "    inner join r on nulled.id == r.id\n", kind, "nulled.id == r.id"
    )
    completed = _completed(tmp_path / "nulling", source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    previous, join, _ = region.joins[-3:]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.kind is AuthoredJoinKind(kind)
    assert len(join.output.row_shape.fields) == 9
    for original, output in zip(
        previous.output.row_shape.fields, join.output.row_shape.fields, strict=True
    ):
        assert output.evidence is original.evidence
        assert output.introduction_use is original.introduction_use
        assert output.nulling_joins == original.nulling_joins
        assert output.effective_nullability is original.effective_nullability
    assert any(field.nulling_joins for field in join.output.row_shape.fields)
    assert all(
        field.introduction_use is not join.input_uses[1]
        for field in join.output.row_shape.fields
    )
    # A global left keeps at most one row, which the existence test may drop.
    source = _prefix_existence(
        _two_current_globals_full("        total = left_global.total\n"),
        "    full join r on False\n",
        kind,
        "False",
    )
    completed = _completed(tmp_path / "global", source)
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[-1].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.kind is AuthoredJoinKind(kind)
    assert join.left_input.grain.state is ProjectGrainBasisState.GLOBAL
    assert join.properties.relational.grain.state is ProjectGrainBasisState.GLOBAL
    assert not join.properties.relational.grain.active


def test_finite_bag_null_reference_and_metamorphics() -> None:
    import sqlite3

    def equality(left: int | None, right: int | None) -> bool | None:
        return None if left is None or right is None else left == right

    def existence(
        kind: str,
        left: tuple[Row, ...],
        right: tuple[int | None, ...],
        predicate: Predicate,
    ) -> tuple[Row, ...]:
        return tuple(
            row
            for row in left
            if any(predicate(row[1], value) is True for value in right)
            == (kind == "semi")
        )

    left = ((0, 1), (1, 1), (2, None))
    right = (1, 1, None)
    assert existence("semi", left, right, equality) == left[:2]
    assert existence("anti", left, right, equality) == left[2:]
    for kind in ("semi", "anti"):
        global_row = ((0, 5),)
        assert existence(kind, global_row, (), equality) == (
            () if kind == "semi" else global_row
        )
        assert existence(kind, global_row, (5, 5), equality) == (
            global_row if kind == "semi" else ()
        )
        assert existence(kind, (), right, equality) == ()
        assert existence(kind, left, (), equality) == (() if kind == "semi" else left)
        for predicate in (
            equality,
            lambda left_value, right_value: True,
            lambda left_value, right_value: False,
            lambda left_value, right_value: None,
            lambda left_value, right_value: left_value is None and right_value is None,
        ):
            retained = existence(kind, left, right, predicate)
            assert existence(kind, left, right * 3, predicate) == retained
            assert existence(kind, left * 2, right, predicate) == retained * 2
            assert existence(kind, retained, right, predicate) == retained
            semi = existence("semi", left, right, predicate)
            anti = existence("anti", left, right, predicate)
            assert tuple(sorted((*semi, *anti), key=lambda row: row[0])) == left
    # A TRUE and a FALSE match coexist: ANTI is not SEMI of the negated predicate.
    assert existence("anti", ((0, 1),), (1, 2), equality) == ()
    assert existence(
        "semi",
        ((0, 1),),
        (1, 2),
        lambda left_value, right_value: left_value != right_value,
    ) == ((0, 1),)
    assert (
        existence(
            "semi",
            left,
            right,
            lambda left_value, right_value: left_value is None and right_value is None,
        )
        == left[2:]
    )
    with sqlite3.connect(":memory:") as db:
        db.execute("create table l(occ integer, value integer)")
        db.execute("create table r(value integer)")
        db.executemany("insert into l values (?, ?)", left)
        db.executemany("insert into r values (?)", ((value,) for value in right))
        for kind, negation in (("semi", ""), ("anti", "not ")):
            observed = tuple(
                db.execute(
                    f"select occ, value from l where {negation}exists "
                    "(select 1 from r where l.value = r.value) order by occ"
                )
            )
            assert observed == existence(kind, left, right, equality)


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize(
    "tail",
    (
        "let",
        "where",
        "group",
        "aggregate",
        "having",
        "window",
        "qualify",
        "select",
        "order",
    ),
)
def test_predicate_only_right_is_absent_from_every_later_tail_scope(
    tmp_path: Path, kind: str, tail: str
) -> None:
    replacement = {
        "let": "    select:\n        id = lhs.id\n",
        "where": "    select:\n        id = lhs.id\n",
        "group": "    group by:\n        r.id\n    select:\n        total = count()\n",
        "aggregate": "    select:\n        total = sum(r.id)\n",
        "having": "    select:\n        total = count()\n    having:\n        r.id > 0\n",
        "window": "    select:\n        rn = row_number() window(order by r.id)\n",
        "qualify": "    select:\n        id = lhs.id\n    qualify:\n        r.id > 0\n",
        "select": "    select:\n        id = r.id\n",
        "order": "    select:\n        id = lhs.id\n    order by:\n        r.id\n",
    }[tail]
    existence = f"    {_existence(kind, 'r', 'lhs.id == r.id')}\n"
    source = _existence_source("lhs.id == r.id", kind).split("    select:\n", 1)[0]
    if tail == "let":  # The relation's lets precede its one tail WHERE.
        source = source.replace(existence, "    let value = r.id\n" + existence)
    elif tail == "where":
        source = source.replace(existence, existence[:-1] + " and r.id > 0\n")
    completed = _completed(tmp_path, source + replacement)
    unavailable = "Project relation semantic completion is unavailable: result"
    expected = {
        "let": [("PIE-S2102", "Unknown field: r.id", 12, 17)],
        "where": [
            ("PIE-S2102", "Unknown field: r.id", 12, 50 if kind == "anti" else 46)
        ],
        "group": [("PIE-S2333", unavailable, 9, 1)],
        "aggregate": [("PIE-S2333", unavailable, 9, 1)],
        "having": [("PIE-S2323", "`having` requires GROUP BY", 15, 5)],
        "window": [("PIE-S2102", "Unknown field: r.id", 14, 43)],
        "qualify": [
            (
                "PIE-S2331",
                "QUALIFY requires at least one selected or predicate window computation",
                15,
                5,
            ),
            ("PIE-S2332", "Unknown QUALIFY reference: r.id", 16, 9),
        ],
        "select": [("PIE-S2102", "Unknown field: r.id", 14, 14)],
        "order": [("PIE-S2102", "Unknown field: r.id", 16, 9)],
    }[tail]
    assert not completed.ok
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == expected
    assert not completed.effective_outputs.current_regions


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_self_use_keeps_binding_role_and_does_not_make_unqualified_field_ambiguous(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _existence_source("lhs.id == r.id", kind)
        .replace("let r = rhs", "let r = lhs")
        .replace("id = lhs.id", "id = id")
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    assert not completed.effective_outputs.current_regions
    assert tuple(_output(completed, "result").schema.fields) == ("id",)


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize(
    "tail", ("row", "grouped", "global", "selected_window", "hidden_window")
)
@pytest.mark.parametrize("side", ("left", "right"))
def test_existing_completed_tails_in_both_roles_and_result_replay_join(
    tmp_path: Path, kind: str, tail: str, side: str
) -> None:
    source, field = _tail_source(tail)
    existence = _existence(kind, "r", "lhs.id == r.id")
    source = source.replace("    inner join r on lhs.id == r.id\n", "")
    if "    where adjusted > 0\n" in source:  # One tail WHERE follows the lets.
        source = source.replace(
            "    where adjusted > 0\n", f"    {existence} and adjusted > 0\n"
        )
    else:
        source = source.replace(
            "    let r = rhs\n", f"    let r = rhs\n    {existence}\n"
        )
    left, right, selected = (
        ("upstream", "rhs", f"upstream.{field}")
        if side == "left"
        else ("lhs", "upstream", "lhs.id")
    )
    source += f"""table result:
    from {left}
    let fresh = {right}
    {_existence(kind, "fresh", "True")}
    select:
        value = {selected}
table replay:
    from result
    select:
        value
query last:
    from replay
    let newest = lhs
    inner join newest on replay.value > 0
    select:
        value = replay.value
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    assert _output(completed, "upstream").fields and _output(completed, "result").fields
    assert tuple(
        region.ledger.owner.definition.name
        for region in completed.effective_outputs.current_regions
    ) == ("last",)
    assert _output(completed, "replay").fields and _output(completed, "last").fields


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_existing_left_fanout_remains_an_aggregate_risk(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _source("True")
        .replace(
            "    select:\n",
            f"    let predicate_right = rhs\n    {_existence(kind, 'predicate_right', 'True')}\n    select:\n",
        )
        .replace("id = lhs.id", "total = sum(lhs.id)")
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert completed.effective_outputs.current_regions
    region = completed.effective_outputs.current_regions[0]
    (join,) = region.joins
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.kind is AuthoredJoinKind.INNER
    assert len(join.properties.relational.grain.active) == 2
    aggregation = (
        completed.effective_outputs.current_tails[0]
        .results[0]
        .window_stage.input_aggregation
    )
    assert aggregation.grain_linkages
    assert any(
        link.requirements and link.multiplicity_risks
        for link in aggregation.grain_linkages
    )
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == [
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: result (an aggregate "
            "may read rows repeated by JOIN r; match a unique key of r in `on`, "
            "use `any(...)` for an input that only filters rows, or aggregate in a "
            "separate query first)",
            9,
            1,
        )
    ]


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_right_dependency_cycle_blocks_owner_but_independent_branch_survives(
    tmp_path: Path, kind: str
) -> None:
    source = _existence_source("True", kind).replace(
        "query result:", "query independent:"
    )
    source += f"""table a:
    from lhs
    let dependency = b
    {_existence(kind, "dependency", "False")}
    select:
        id = lhs.id
table b:
    from a
    select:
        id
query dependent:
    from a
    select:
        id
"""
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert _output(completed, "independent").fields
    column = 15 if kind == "anti" else 11
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2302", "Relation cycle detected: a -> b -> a", 18, column),
        ("PIE-S2334", "ANY input relation is unavailable.", 18, column),
    ]
    assert not completed.effective_outputs.current_regions
    blocked = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name in {"a", "b", "dependent"}
    )
    assert len(blocked) == 3
    for entry in blocked:
        assert isinstance(entry, ProjectEffectiveOutputCompletionTerminal)
        assert entry.output is None


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_foreign_roots_roles_prefix_and_forged_positive_are_rejected(
    tmp_path: Path, kind: str
) -> None:
    source = _existence_source("lhs.id == r.id", kind).replace(
        "    select:\n",
        "    let next_right = rhs\n    inner join next_right on lhs.id == next_right.id\n    select:\n",
    )
    local = _completed(tmp_path / "local", source)
    foreign = _completed(tmp_path / "foreign", source)
    region = local.effective_outputs.current_regions[0]
    first, second = region.joins
    other = foreign.effective_outputs.current_regions[0].joins[0]
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(second, ProjectCurrentBinaryJoin)
    assert isinstance(other, ProjectCurrentBinaryJoin)
    for changes in (
        {"condition": other.condition},
        {"right_input": other.right_input},
        {"left_input": other.left_input},
        {"starting_allocation": other.starting_allocation},
        {"left_input": first.right_input},
    ):
        with pytest.raises((ValueError, TypeError)):
            replace(first, **changes)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(first.properties, relational=other.properties.relational)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(first, field_inputs=other.field_inputs)
    assert second.prefix is not None
    with pytest.raises(ValueError, match="prefix"):
        replace(second, left_fields=tuple(reversed(second.left_fields)))
    assert region.input_scope is not None
    with pytest.raises(ValueError, match="prefix"):
        ProjectCurrentPreMatchInputs(
            scope=region.input_scope, use=second.use, prefix=(other.condition,)
        )
    with pytest.raises(ValueError, match="prefix"):
        replace(second, starting_allocation=first.starting_allocation)


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_real_explicit_project_check_and_unchanged_json_shape(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str, mode: CheckMode
) -> None:
    completed = _completed(
        tmp_path, f"mode {mode.value}\n" + _existence_source("lhs.id == r.id", kind)
    )
    assert completed.ok, completed.diagnostics
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 0
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert document["ok"] and not captured.err
    assert set(document) == {
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    }
    assert not completed.diagnostics


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_single_file_and_combined_ir_retain_existence_inputs(
    tmp_path: Path, kind: str
) -> None:
    # A tail existence filter is a scalar value of the row; before a later JOIN
    # it is the hidden SEMI/ANTI JOIN of that JOIN prefix (a semi/anti JOIN
    # before S6), which only a completed project admits.
    tail = _existence_source("True", kind)
    prefix = _prefix_existence(
        _source("True"), "    inner join r on True\n", kind, "True"
    )
    for source, joins in ((tail, 0), (prefix, 1)):
        parsed = parse_source(source)
        assert parsed.ast is not None
        semantic = analyze(parsed.ast)
        assert semantic.diagnostics == ()
        assert len(semantic.model.relation_joins) == joins
        assert semantic.script is not None
        lowered = build_ir(semantic.script, semantic.model)
        assert lowered.ir is not None and lowered.diagnostics == ()
    # A schema_version = 1 project model refuses the any(...) and the JOIN
    # (PIE-S2334), so its namespace analysis reports neither.
    legacy = analyze_project_namespace(parsed.ast)
    assert legacy.diagnostics == ()
    legacy_lowered = build_ir(parsed.ast, legacy.model)
    assert legacy_lowered.ir is None
    assert any(d.code == "PIE-I1000" for d in legacy_lowered.diagnostics)
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
        ProjectIRQueryBlockTerminal,
    )

    entries = []
    for name, source in (("tail", tail), ("prefix", prefix)):
        completed = _completed(tmp_path / name, source)
        snapshot = build_project_query_block_ir(completed)
        assert verify_project_query_block_ir(snapshot).verified
        entry = next(e for e in snapshot.entries if e.owner.definition.name == "result")
        assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        entries.append((completed, snapshot, entry))
    assert entries[0][2].join_prefix is None
    completed, snapshot, entry = entries[1]
    assert entry.join_prefix is not None
    hidden, later = completed.effective_outputs.current_regions[0].joins
    assert hidden.kind is AuthoredJoinKind(kind)
    assert entry.join_prefix.final_join.source is later
    joined = entry.join_prefix.joins[0]
    assert joined.source is hidden
    assert tuple(image.source for image in joined.inputs) == joined.source.input_uses
    assert len(joined.inputs) == 2
    for image in joined.inputs:
        producer = next(e for e in snapshot.entries if e.owner is image.producer)
        assert not isinstance(producer, ProjectIRQueryBlockTerminal)
        assert image.use.output is producer.active_output.occurrence


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_consumed_right_producer_failure_still_blocks_even_constant_condition(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _existence_source("False", kind)
        .replace(
            "query result:\n",
            "table broken:\n    from rhs\n    select:\n        bad = missing\nquery result:\n",
        )
        .replace("let r = rhs", "let r = broken")
    )
    source += "query valid:\n    from lhs\n    select:\n        id\n"
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2102", "Unknown field: missing", 12, 15),
        (
            "PIE-S2334",
            "ANY input relation is unavailable.",
            16,
            15 if kind == "anti" else 11,
        ),
    ]
    assert not completed.effective_outputs.current_regions
    assert not completed.effective_outputs.allocation_events
    result = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "result"
    )
    assert isinstance(
        result,
        (ProjectEffectiveOutputTerminal, ProjectEffectiveOutputCompletionTerminal),
    )
    assert result.output is None
    valid = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "valid"
    )
    assert (
        isinstance(valid, ProjectExistingEffectiveOutput) and valid.output is not None
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("value,ok", (("True", True), ("1", False)))
def test_changed_right_producer_rebuilds_operative_type_evidence(
    tmp_path: Path, kind: str, value: str, ok: bool
) -> None:
    source = (
        _source("True")
        .replace("query result:", "table upstream:")
        .replace("id = lhs.id", f"flag = {value}")
    )
    source += f"query result:\n    from lhs\n    let r = upstream\n    {_existence(kind, 'r', 'r.flag')}\n    select:\n        id = lhs.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok is ok, completed.diagnostics
    # The predicate is typed by the completed producer's `flag`, not its source.
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == (
        []
        if ok
        else [
            (
                "PIE-S2202",
                "Expected Bool expression in ANY",
                18,
                19 if kind == "anti" else 15,
            )
        ]
    )
    assert tuple(
        r.ledger.owner.definition.name
        for r in completed.effective_outputs.current_regions
    ) == ("upstream",)


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_duplicate_binding_name_is_not_reusable_after_existence(
    tmp_path: Path, kind: str
) -> None:
    source = _existence_source("True", kind).replace(
        "    select:\n",
        "    let r = rhs\n    inner join r on True\n    select:\n",
    )
    authored = parse_source(source, path="main.pietto")
    assert authored.ast is not None and authored.diagnostics == ()
    query = authored.ast.definitions[-1]
    assert isinstance(query, QueryDef)
    first, duplicate = query.naming_declarations
    assert first.name == duplicate.name == "r" and first is not duplicate
    assert tuple(join.kind for join in query.join_clauses) == (AuthoredJoinKind.INNER,)
    assert tuple(f.preceding_join_count for f in query.join_filters) == (0,)
    parsed = _parsed(tmp_path, source)
    assert not parsed.ok and not parsed.errors
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in parsed.diagnostics
    ] == [
        (
            "PIE-S2604",
            "Duplicate query local name: r",
            duplicate.span.line,
            duplicate.span.column,
        )
    ]


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_legacy_flat_and_explain_remain_at_existing_public_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    _completed(tmp_path, _existence_source("True", kind))
    assert cli.main(["explain", "--project", str(tmp_path), "--format", "json"]) == 2
    explanation = json.loads(capsys.readouterr().out)
    assert explanation["format"] == "pietto.project-explain.v1"
    assert explanation["payload"] is None
    assert explanation["diagnostics"][0]["code"] == "config_schema"
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    # A legacy flat project has no any(...) in the current syntax: a tail any
    # value is one PIE-S2334 at the any(...).
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
    column = 11 if kind == "semi" else 15
    assert (document["ok"], document["diagnostics"]) == (
        False,
        [
            {
                "code": "PIE-S2334",
                "severity": "error",
                "message": "any(...): a schema_version = 1 project has no any(...) "
                "in the current syntax; set schema_version = 2 to check it.",
                "location": {
                    "path": "main.pietto",
                    "line": 12,
                    "column": column,
                    "end_line": 12,
                    "end_column": column + 20,
                },
                "suggestion": None,
                "related_locations": [],
            }
        ],
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_package_root_does_not_admit_existence_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 3\n[package]\npath = "pkg"\nnamespace = "test"\nname = "example"\nversion = "1.0.0"\nsha256 = "'
        + "a" * 64
        + '"\n'
    )
    (tmp_path / "main.pietto").write_text(_existence_source("True", kind))
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert not captured.err
    assert not json.loads(captured.out)["ok"]


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_later_predicate_join_uses_retained_left_and_new_right(
    tmp_path: Path, kind: str
) -> None:
    source = _existence_source("True", kind).replace(
        "    select:\n",
        "    let next_right = rhs\n    inner join next_right on Link(lhs, next_right)\n    select:\n",
    )
    source += "        other = next_right.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    assert tuple(_output(completed, "result").schema.fields) == ("id", "other")
    region = completed.effective_outputs.current_regions[0]
    assert len(region.joins) == 2
    assert all(
        f.introduction_use is not region.joins[0].input_uses[1]
        for f in region.joins[-1].output.row_shape.fields
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_prefix_cannot_graft_consumed_right_role_with_identical_field_evidence(
    tmp_path: Path, kind: str
) -> None:
    source = _existence_source("lhs.id == r.id", kind).replace(
        "let r = rhs", "let r = lhs"
    )
    source = source.replace(
        "    select:\n",
        "    let next_right = rhs\n    inner join next_right on lhs.id == next_right.id\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    first, second = completed.effective_outputs.current_regions[0].joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(second, ProjectCurrentBinaryJoin) and second.prefix is not None
    assert first.left_input is first.right_input
    with pytest.raises(ValueError, match="field-role"):
        replace(
            second.prefix,
            origins=tuple(
                (first.use.target_binding, field) for _, field in second.prefix.origins
            ),
        )


@pytest.mark.parametrize("negation", ("", "not "), ids=("semi", "anti"))
def test_single_file_existence_binding_is_read_only_by_its_own_on(
    negation: str,
) -> None:
    """The hidden SEMI/ANTI JOIN of a JOIN-prefix `any` binds its input under a
    generated name only its own ON reads; the binder's name reaches nothing."""
    run = run_joins(
        JOIN_PREFIX + "query q:\n    from orders\n    let s = customers\n"
        f"    where {negation}any(s.id == orders.customer_id for s in s)\n"
        "    let r = regions\n"
        '    inner join r on r.id == s.region_id and r.label != ""\n'
        "    select:\n        n = s.name\n        name\n        label\n"
    )
    checks, _ = run.checks()
    # The tail row holds no field of s, so a bare `name` is no binding read.
    assert located(checks.reads) == [
        ("PIE-S2102", "Unknown field: s.name", 25, 13),
        ("PIE-S2335", "JOIN ON reference is unknown: s.region_id", 23, 29),
    ]
    rows = run.rows("q")
    assert rows is not None
    assert list(rows.tail.fields) == [
        "orders.id",
        "orders.customer_id",
        "orders.amount",
        "r.id",
        "r.label",
    ]
    assert list(rows.on[0].fields)[-4:] == [
        "_pietto_any_1.id",
        "_pietto_any_1.name",
        "_pietto_any_1.region_id",
        "_pietto_any_1.active",
    ]
    assert not any(name.startswith("_pietto_any_1.") for name in rows.on[1].fields)
    assert checks.facts == {}


_ANY_SOURCE = """shape Order:
    id: Int
    customer_id: Int | None
shape Customer:
    id: Int
    floor: Int
    active: Bool | None
source orders: Order = postgres.table("shop.orders")
source customers: Customer = postgres.table("shop.customers")
relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id and customer.active
"""


def _any_semantics(body: str):
    parsed = parse_source(_ANY_SOURCE + body, path="any.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    return parsed.ast, analyze(parsed.ast)


@pytest.mark.parametrize("negative", (False, True))
def test_any_generator_uses_exact_hidden_occurrence_and_keeps_authored_provenance(
    negative: bool,
) -> None:
    from pietto import ast_nodes as ast

    authored, result = _any_semantics(
        "query q:\n    from orders\n    where "
        + ("not " if negative else "")
        + "any(OrderCustomer(orders, buyer) for buyer in customers)\n    let next = customers\n    cross join next\n    select:\n        id = orders.id\n"
    )
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (use,) = result.model.existence_generators
    assert use.authored_owner is authored.definitions[-1]
    assert use.owner is query and use.clause is query.join_clauses[0]
    assert use.expression.binding_name == "buyer"
    assert use.input_ordinal == 1 and use.preceding_join_count == 0
    assert use.clause.kind is (
        ast.AuthoredJoinKind.ANTI if negative else ast.AuthoredJoinKind.SEMI
    )
    assert use.clause.source_binding_name is None and use.clause.uses_named_input
    assert query.where_clause is None and query.join_filters == ()
    assert tuple(result.model.relation_row_schemas[query].fields) == ("id",)
    info = result.model.relation_joins[query]
    assert not info.inputs[1].visible
    (call,) = result.model.relationship_calls
    assert call.owner is query and call.context is use.clause.on_clause
    assert call.arguments[1].occurrence is use.clause


def test_repeated_any_binder_names_are_independent_and_do_not_leak() -> None:
    _, result = _any_semantics("""query q:
    from orders
    where any(OrderCustomer(orders, buyer) for buyer in customers) and not any(OrderCustomer(orders, buyer) for buyer in customers)
    select:
        id = orders.id
""")
    assert result.diagnostics == ()
    first, second = result.model.any_values.values()
    assert (
        first.use.expression.binding_name
        == second.use.expression.binding_name
        == "buyer"
    )
    assert first.use.expression is not second.use.expression
    _, leaked = _any_semantics("""query q:
    from orders
    where any(OrderCustomer(orders, buyer) for buyer in customers)
    select:
        id = buyer.id
""")
    assert [(item.code, item.message) for item in leaked.diagnostics] == [
        ("PIE-S2102", "Unknown field: buyer.id")
    ]


def test_any_local_binding_shadows_outer_binding_only_inside_body() -> None:
    from pietto import ast_nodes as ast

    _, result = _any_semantics("""query q:
    from orders
    where any(orders.id > 0 for orders in orders)
    select:
        id = orders.id
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (info,) = result.model.any_values.values()
    condition = info.predicate
    assert isinstance(condition, ast.ComparisonExpr)
    assert info.field_reads[condition.left].occurrence is info.use.expression
    assert info.captures == ()


def test_any_tail_captures_checked_scalar_let_in_its_declared_scope() -> None:
    from pietto import ast_nodes as ast

    _, result = _any_semantics("""query q:
    from orders
    let floor = orders.id
    where any(buyer.id > floor for buyer in customers)
    select:
        id = orders.id
""")
    assert result.diagnostics == () and result.script is not None
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (info,) = result.model.any_values.values()
    assert isinstance(info.predicate, ast.ComparisonExpr)
    assert info.predicate.right not in info.field_reads
    assert (
        result.model.expression_value_types[info.predicate.right].resolved_type.name
        == "Int"
    )
    assert info.captures[0].occurrence is query.from_clause
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None


def test_any_between_joins_captures_the_actual_nullable_prefix() -> None:
    from pietto import ast_nodes as ast
    from pietto.semantic.model import EffectiveNullability

    _, result = _any_semantics("""query q:
    from orders
    let buyer = customers
    left join buyer on OrderCustomer(orders, buyer)
    where any(other.id == buyer.id for other in customers)
    let last = customers
    right join last on last.id == orders.id
    select:
        id = last.id
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (use,) = result.model.existence_generators
    assert isinstance(use.context, ast.JoinFilterClause)
    assert use.preceding_join_count == 1 and use.input_ordinal == 2
    assert use.clause is query.join_clauses[1]
    on = use.clause.on_clause
    assert on is not None and isinstance(on.expression, ast.ComparisonExpr)
    assert (
        result.model.expression_value_types[on.expression.right].nullability
        is EffectiveNullability.NULLABLE
    )


def test_any_target_requires_an_existing_relation_and_generates_no_output() -> None:
    _, result = _any_semantics("""query q:
    from orders
    where any(buyer.id > 0 for buyer in missing)
    select:
        id = orders.id
""")
    assert [(item.code, item.message) for item in result.diagnostics] == [
        ("PIE-S2301", "Unknown or unavailable ANY relation: missing")
    ]


def _placed_any(where: str, *, before_join: bool, alias: str = "") -> str:
    """Query `q` with `where` before its JOIN (a hidden input) or at its tail."""
    join = "    let next = customers\n    cross join next\n"
    body = where + join if before_join else join + where
    return (
        f"query q:\n{alias}    from orders\n{body}    select:\n        id = orders.id\n"
    )


@pytest.mark.parametrize("negation", ("", "not "))
@pytest.mark.parametrize(
    ("iterable", "alias"),
    (
        pytest.param("customers", "", id="relation"),
        pytest.param("buyers", "    let buyers = customers\n", id="alias"),
    ),
)
@pytest.mark.parametrize("before_join", (True, False))
def test_any_binder_hides_a_nested_iterable_of_its_name_also_when_lowered(
    before_join: bool, iterable: str, alias: str, negation: str
) -> None:
    where = f"    where {negation}any(any(True for other in {iterable}) for {iterable} in orders)\n"
    _, result = _any_semantics(_placed_any(where, before_join=before_join, alias=alias))
    line = 14 + bool(alias) + (0 if before_join else 2)
    assert located(result.diagnostics) == [
        (
            "PIE-S2301",
            f"Unknown or unavailable ANY relation: {iterable}",
            line,
            37 + len(negation),
        )
    ]


@pytest.mark.parametrize("before_join", (True, False))
def test_any_binder_does_not_hide_a_nested_alias_of_a_relation_of_its_name(
    before_join: bool,
) -> None:
    where = "    where any(any(other.id == customers.id for other in buyers) for customers in orders)\n"
    _, result = _any_semantics(
        _placed_any(
            where, before_join=before_join, alias="    let buyers = customers\n"
        )
    )
    assert result.diagnostics == ()
    (inner,) = (
        info
        for info in result.model.any_values.values()
        if info.use.authored_expression.binding_name == "other"
    )
    assert inner.iterator is result.model.relation_symbols["customers"]


def test_any_tail_let_capture_keeps_existing_inline_expansion_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pietto.semantic import let_bindings

    monkeypatch.setattr(let_bindings, "_MAX_INLINE_NODES", 2)
    _, result = _any_semantics("""query q:
    from orders
    let floor = orders.id + 1
    where any(buyer.id > floor for buyer in customers)
    select:
        id = orders.id
""")
    assert [item.code for item in result.diagnostics] == ["PIE-S2328"]


def test_any_iterable_name_and_repeated_local_binders_do_not_reserve_outer_scalar_lets() -> (
    None
):
    _, result = _any_semantics("""query q:
    from orders
    let customers = orders.id
    let buyer = orders.id + 1
    where any(buyer.id > customers for buyer in customers) and not any(buyer.id < customers for buyer in customers)
    select:
        captured = customers
        outer_buyer = buyer
""")
    assert result.diagnostics == () and result.script is not None
    uses = tuple(result.model.any_values.values())
    assert len(uses) == 2 and uses[0].use.expression is not uses[1].use.expression
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None


def test_any_internal_binding_cannot_capture_an_authored_alias() -> None:
    _, result = _any_semantics("""query q:
    let _pietto_any_1 = orders
    from _pietto_any_1
    where any(OrderCustomer(_pietto_any_1, buyer) for buyer in customers)
    select:
        id = _pietto_any_1.id
""")
    assert result.diagnostics == ()
    (info,) = result.model.any_values.values()
    assert info.captures[0].binding == "_pietto_any_1"
    assert info.captures[0].occurrence is info.use.owner.from_clause


def test_any_between_joins_cannot_read_a_future_binding() -> None:
    _, result = _any_semantics("""query q:
    from orders
    where any(candidate.id == later.id for candidate in customers)
    let later = customers
    left join later on later.id == orders.id
    select:
        id = orders.id
""")
    assert [(item.code, item.message) for item in result.diagnostics] == [
        ("PIE-S2335", "JOIN ON reference is forward: later.id")
    ]


@pytest.mark.parametrize(
    ("condition", "code", "message", "column"),
    (
        (
            "not any(buyer for buyer in customers)",
            "PIE-S2335",
            "JOIN ON reference is unknown: buyer",
            19,
        ),
        (
            "any(buyer.missing == 1 for buyer in customers)",
            "PIE-S2335",
            "JOIN ON reference is unknown: buyer.missing",
            15,
        ),
        (
            "any(id == 1 for buyer in customers)",
            "PIE-S2335",
            "JOIN ON reference is ambiguous: id; write orders.id or buyer.id",
            15,
        ),
        # The binder hides the FROM input's name, so no spelling picks either.
        (
            "any(id == 1 for orders in customers)",
            "PIE-S2335",
            "JOIN ON reference is ambiguous: id",
            15,
        ),
        (
            "any(any(o.id == buyer.missing for o in orders) for buyer in customers)",
            "PIE-S2102",
            "Unknown or unavailable field in ANY predicate: buyer.missing",
            27,
        ),
    ),
)
def test_any_before_a_later_join_names_its_binder_as_written(
    condition: str, code: str, message: str, column: int
) -> None:
    # The hidden JOIN binds the rows under a generated name, never shown.
    _, result = _any_semantics(
        f"query q:\n    from orders\n    where {condition}\n"
        "    let next = customers\n    cross join next\n"
        "    select:\n        id = orders.id\n"
    )
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [(code, message, 14, column)]


# Before: an `any(...)` that read a field of a FROM row of unknown type passed
# check, and lowering it failed (PIE-I1000); one whose generator row is of
# unknown type keeps its one PIE-S2334.
@pytest.mark.parametrize(
    ("orders", "expected"),
    (
        (
            "orders: Ord",
            (
                "PIE-S2102",
                "Unknown or unavailable field in ANY predicate: items.id",
                28,
            ),
        ),
        ("orders", ("PIE-S2334", "ANY over orders requires known input fields.", 46)),
    ),
)
def test_any_never_reads_a_field_of_a_from_row_of_unknown_type(
    orders: str, expected: tuple[str, str, int]
) -> None:
    parsed = parse_source(
        "shape Ord:\n    id: Int\n    item_id: Int\n"
        'source items = postgres.table("items")\n'
        f'source {orders} = postgres.table("orders")\n'
        "table w:\n    from items\n"
        "    where any(o.item_id == items.id for o in orders)\n"
        "    select:\n        id\n",
        path="any.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
        if item.severity is Severity.ERROR
    ] == [(expected[0], expected[1], 8, expected[2])]


# Before: an `any(...)` that read an output of no type, such as `x = None`,
# passed check, and lowering it failed (PIE-I1000); one that reads only typed
# outputs of that relation is lowered.
@pytest.mark.parametrize(
    ("predicate", "column"),
    (
        ("o.x == items.id", 15),
        ("o.id == items.id and o.x is None", 36),
        ("o.id == items.id", None),
    ),
    ids=("compared", "null-test", "typed"),
)
def test_any_never_reads_an_output_of_no_type(
    predicate: str, column: int | None
) -> None:
    parsed = parse_source(
        "shape Row:\n    id: Int\n"
        'source items: Row = postgres.table("items")\n'
        "table t:\n    from items\n    select:\n        id\n        x = None\n"
        f"table q:\n    from items\n    where any({predicate} for o in t)\n"
        "    select:\n        id\n",
        path="any.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    result = analyze(parsed.ast)
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == (
        []
        if column is None
        else [
            (
                "PIE-S2102",
                "Unknown or unavailable field in ANY predicate: o.x",
                11,
                column,
            )
        ]
    )
    if column is None:
        assert result.script is not None
        lowered = build_ir(result.script, result.model)
        assert lowered.diagnostics == ()


@pytest.mark.parametrize(
    ("relations", "expected"),
    (
        (
            "table t:\n    from items\n    select:\n        id\n"
            "        x = nosuch + 1\n",
            [("PIE-S2102", "Unknown field: nosuch", 9)],
        ),
        (
            "table t:\n    from items\n    select:\n        id\n        x = cat * 2\n",
            [
                (
                    "PIE-S2105",
                    "Invalid operands for operator *: expected numeric operands",
                    9,
                )
            ],
        ),
        (
            "table t:\n    from t\n    select:\n        id\n        x = id\n",
            [("PIE-S2302", "Relation cycle detected: t -> t", 6)],
        ),
    ),
    ids=("unknown-field", "invalid-operands", "cycle"),
)
def test_any_adds_no_error_for_an_output_whose_own_error_is_reported(
    relations: str, expected: list[tuple[str, str, int]]
) -> None:
    parsed = parse_source(
        "shape Row:\n    id: Int\n    cat: Text\n"
        'source items: Row = postgres.table("items")\n'
        + relations
        + "table q:\n    from items\n    where any(o.x == items.id for o in t)\n"
        "    select:\n        id\n",
        path="any.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert [
        (item.code, item.message, item.location.line)
        for item in analyze(parsed.ast).diagnostics
        if item.severity is Severity.ERROR
    ] == expected


@pytest.mark.parametrize("relationship", (False, True))
def test_any_local_binder_does_not_rename_same_named_callable(
    relationship: bool,
) -> None:
    from pietto import ast_nodes as ast

    declaration = (
        "relationship buyer(order: Order, customer: Customer):\n    order.customer_id == customer.id\n"
        if relationship
        else "def buyer(x: Int) -> Bool | None: return x > 0\n"
    )
    call = "buyer(orders, buyer)" if relationship else "buyer(buyer.id)"
    _, result = _any_semantics(
        declaration
        + "query q:\n    from orders\n    where any("
        + call
        + " for buyer in customers)\n    select:\n        id = orders.id\n"
    )
    assert result.diagnostics == () and result.script is not None
    (info,) = result.model.any_values.values()
    authored = info.use.authored_expression
    assert isinstance(authored.predicate, ast.CallExpr)
    assert isinstance(authored.predicate.callee, ast.NameExpr)
    assert authored.predicate.callee.name == "buyer"
    if relationship:
        (bound,) = result.model.relationship_calls
        assert bound.template.declaration.name == "buyer"
        assert bound.arguments[1].occurrence is info.use.expression
    lowered = build_ir(result.script, result.model)
    assert lowered.diagnostics == () and lowered.ir is not None


def test_any_value_select_keeps_outer_row_and_exact_capture_occurrences() -> None:
    from pietto import ast_nodes as ast
    from pietto.semantic.model import EffectiveNullability

    authored, result = _any_semantics("""query q:
    from orders
    select:
        matched = any(OrderCustomer(orders, buyer) for buyer in customers)
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    ((expression, info),) = result.model.any_values.items()
    assert query.join_clauses == () and result.model.existence_generators == ()
    assert expression is query.select_items[0].expression
    authored_query = authored.definitions[-1]
    assert isinstance(authored_query, ast.QueryDef)
    assert info.use.authored_expression is authored_query.select_items[0].expression
    assert info.use.owner is query and info.use.context is query.select_items[0]
    assert info.use.join_prefix_count == 0
    assert (
        result.model.expression_value_types[expression].nullability
        is EffectiveNullability.NON_NULL
    )
    assert info.captures and all(
        read.occurrence is query.from_clause for read in info.captures
    )
    assert all(
        any(read is candidate for candidate in info.field_reads.values())
        for read in info.captures
    )
    assert tuple(result.model.relation_row_schemas[query].fields) == ("matched",)


def test_any_value_on_uses_target_and_exact_pre_match_nullability() -> None:
    from pietto import ast_nodes as ast
    from pietto.semantic.model import EffectiveNullability

    _, result = _any_semantics("""query q:
    from orders
    let first = customers
    left join first on orders.customer_id == first.id
    let second = customers
    left join second on any(candidate.id == first.id and candidate.id == second.id for candidate in customers)
    select:
        id = orders.id
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (info,) = result.model.any_values.values()
    assert info.use.context is query.join_clauses[1].on_clause
    assert info.use.join_prefix_count == 2
    assert [(read.binding, read.value_type.nullability) for read in info.captures] == [
        ("first", EffectiveNullability.NULLABLE),
        ("second", EffectiveNullability.NON_NULL),
    ]
    assert info.captures[0].occurrence is query.join_clauses[0]
    assert info.captures[1].occurrence is query.join_clauses[1]


def test_any_value_nested_binders_shadow_independently_and_capture_parent_identity() -> (
    None
):
    from pietto import ast_nodes as ast

    _, result = _any_semantics("""query q:
    from orders
    select:
        matched = any(any(other.id == buyer.id and other.id == orders.id for other in customers) for buyer in customers)
        shadowed = any(any(buyer.id > 0 for buyer in orders) for buyer in customers)
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    first = query.select_items[0].expression
    assert isinstance(first, ast.AnyExpr) and isinstance(first.predicate, ast.AnyExpr)
    parent, child = (
        result.model.any_values[first],
        result.model.any_values[first.predicate],
    )
    assert child.captures[0].occurrence is first
    assert child.captures[1].occurrence is query.from_clause
    assert parent.captures == (child.captures[1],)
    second = query.select_items[1].expression
    assert isinstance(second, ast.AnyExpr) and isinstance(second.predicate, ast.AnyExpr)
    assert result.model.any_values[second].captures == ()
    assert result.model.any_values[second.predicate].iterator.name == "orders"


_SHADOW_HEAD = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query result:
"""
_NESTED = "any(any(True for nested_row in {inner}) for {outer} in rows)"
_ALIAS = "    let candidates = rows\n    from rows\n"
_UNKNOWN = "Unknown relation: {}"
_UNAVAILABLE = "Unknown or unavailable ANY relation: {}"
_NO_INPUT = "ANY input relation is unavailable."
# A WHERE before a later JOIN: its ANY is lowered to a hidden SEMI/ANTI input.
_JOIN_AFTER_WHERE = "\n    let next = rows\n    cross join next\n    select rows.id"
_INCOMPLETE = "{} is available only when an EXPLICIT_MODULES project (schema version 2) completes it."
_NO_PREMATCH = "JOIN pre-match input or relationship authority is unavailable."


def _lowered_unknown(
    name: str, kind: str, line: int, outer: tuple[int, int], inner: tuple[int, int]
) -> list[tuple[str, str, int, int, int, int]]:
    """A project's refusal of an unknown nested ANY relation in a lowered WHERE
    ANY (outer and inner are the two ANYs' column spans on `line`)."""

    hidden = (line, outer[0], line, outer[1])
    read = (line, inner[0], line, inner[1])
    join = (line + 2, 5, line + 2, 20)
    return [
        ("PIE-S2301", _UNKNOWN.format(name), *read),
        ("PIE-S2334", _INCOMPLETE.format(kind), *hidden),
        ("PIE-S2334", _INCOMPLETE.format("JOIN-local ON"), *read),
        ("PIE-S2334", _INCOMPLETE.format("CROSS JOIN"), *join),
        ("PIE-S2334", _NO_INPUT, *read),
        ("PIE-S2335", _NO_PREMATCH, *join),
    ]


@pytest.mark.parametrize(
    ("body", "project", "single_file"),
    (
        pytest.param(
            _ALIAS
            + "    select found = "
            + _NESTED.format(inner="candidates", outer="candidates"),
            [
                ("PIE-S2301", _UNKNOWN.format("candidates"), 7, 24, 7, 62),
                ("PIE-S2334", _NO_INPUT, 7, 24, 7, 62),
            ],
            [("PIE-S2301", _UNAVAILABLE.format("candidates"), 7, 51, 7, 61)],
            id="let_alias",
        ),
        pytest.param(
            _ALIAS
            + "    where "
            + _NESTED.format(inner="candidates", outer="candidates")
            + "\n    select rows.id",
            [
                ("PIE-S2301", _UNKNOWN.format("candidates"), 7, 15, 7, 53),
                ("PIE-S2334", _NO_INPUT, 7, 15, 7, 53),
            ],
            [("PIE-S2301", _UNAVAILABLE.format("candidates"), 7, 42, 7, 52)],
            id="where_let_alias",
        ),
        pytest.param(
            "    from rows\n    select found = "
            + _NESTED.format(inner="rows", outer="rows"),
            [
                ("PIE-S2301", _UNKNOWN.format("rows"), 6, 24, 6, 56),
                ("PIE-S2334", _NO_INPUT, 6, 24, 6, 56),
            ],
            [("PIE-S2301", _UNAVAILABLE.format("rows"), 6, 51, 6, 55)],
            id="module_relation",
        ),
        pytest.param(
            _ALIAS
            + "    select found = "
            + _NESTED.format(inner="candidates", outer="other"),
            [],
            [],
            id="unshadowed_let_alias",
        ),
        pytest.param(
            _ALIAS
            + "    select found = "
            + _NESTED.format(inner="candidates", outer="rows"),
            [],
            [],
            id="let_alias_of_the_binder_name",
        ),
        pytest.param(
            _ALIAS
            + "    where "
            + _NESTED.format(inner="candidates", outer="candidates")
            + _JOIN_AFTER_WHERE,
            _lowered_unknown("candidates", "SEMI JOIN", 7, (11, 77), (15, 53)),
            [("PIE-S2301", _UNAVAILABLE.format("candidates"), 7, 42, 7, 52)],
            id="prefix_let_alias",
        ),
        pytest.param(
            "    from rows\n    where "
            + _NESTED.format(inner="rows", outer="rows")
            + _JOIN_AFTER_WHERE,
            _lowered_unknown("rows", "SEMI JOIN", 6, (11, 65), (15, 47)),
            [("PIE-S2301", _UNAVAILABLE.format("rows"), 6, 42, 6, 46)],
            id="prefix_module_relation",
        ),
        pytest.param(
            "    from rows\n    where not "
            + _NESTED.format(inner="rows", outer="rows")
            + _JOIN_AFTER_WHERE,
            _lowered_unknown("rows", "ANTI JOIN", 6, (11, 69), (19, 51)),
            [("PIE-S2301", _UNAVAILABLE.format("rows"), 6, 46, 6, 50)],
            id="prefix_not_module_relation",
        ),
        pytest.param(
            _ALIAS
            + "    where "
            + _NESTED.format(inner="candidates", outer="rows")
            + _JOIN_AFTER_WHERE,
            [],
            [],
            id="prefix_let_alias_of_the_binder_name",
        ),
    ),
)
def test_any_binder_hides_its_name_from_nested_iterables_in_both_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    project: list[tuple[str, str, int, int, int, int]],
    single_file: list[tuple[str, str, int, int, int, int]],
) -> None:
    """An enclosing binder hides the relations of its name, let aliases included,
    also from a WHERE ANY lowered to a hidden input; it compares the iterable's
    name as written, so an alias of the relation it names is not hidden."""

    _parsed(tmp_path, _SHADOW_HEAD + body + "\n")
    observed = []
    for argv in (
        ["check", "--project", str(tmp_path)],
        ["check", str(tmp_path / "main.pietto")],
    ):
        code = cli.main([*argv, "--format", "json"])
        document = json.loads(capsys.readouterr().out)
        diagnostics = [
            (
                item["code"],
                item["message"],
                item["location"]["line"],
                item["location"]["column"],
                item["location"]["end_line"],
                item["location"]["end_column"],
            )
            for item in document["diagnostics"]
        ]
        observed.append((code, diagnostics))
    assert observed == [
        (1 if project else 0, project),
        (1 if single_file else 0, single_file),
    ]


def test_every_any_body_is_checked_even_when_let_value_is_unused() -> None:
    _, result = _any_semantics("""query q:
    from orders
    let unused = any(candidate.missing > 0 for candidate in customers)
    select:
        id = orders.id
""")
    assert any(
        item.code == "PIE-S2102" and "missing" in item.message
        for item in result.diagnostics
    )


def test_def_cannot_discard_an_any_argument() -> None:
    _, result = _any_semantics("""def Ignore(value: Bool) -> Bool:
    return True
query q:
    from orders
    select:
        ok = Ignore(any(OrderCustomer(orders, candidate) for candidate in customers))
""")
    assert [item.code for item in result.diagnostics] == ["PIE-S2397"]
    assert result.model.any_values == {}


def test_scalar_wrapper_duplicates_any_occurrences_without_losing_authored_origin() -> (
    None
):
    _, result = _any_semantics("""def Twice(value: Bool) -> Bool | None:
    return value and value
query q:
    from orders
    select:
        ok = Twice(any(OrderCustomer(orders, candidate) for candidate in customers))
""")
    assert result.diagnostics == ()
    values = tuple(result.model.any_values.values())
    assert len(values) == 2
    assert values[0].use.expression is not values[1].use.expression
    assert values[0].use.authored_expression is values[1].use.authored_expression


def test_any_iterable_dependencies_include_cycles_and_unused_let_reads() -> None:
    _, result = _any_semantics("""table first:
    from orders
    let unused = any(candidate.id > 0 for candidate in second)
    select:
        id = orders.id
table second:
    from orders
    select:
        ok = any(candidate.id > 0 for candidate in first)
""")
    assert any(item.code == "PIE-S2302" for item in result.diagnostics)


def test_any_on_cannot_capture_future_or_hidden_inputs() -> None:
    for hidden in (False, True):
        body = (
            "query q:\n    from orders\n    let first = customers\n    where any(orders.id == first.id for first in first)\n    select:\n        ok = any(candidate.id == first.id for candidate in customers)\n"
            if hidden
            else "query q:\n    from orders\n    let first = customers\n    inner join first on any(candidate.id == later.id for candidate in customers)\n    let later = customers\n    cross join later\n    select:\n        id = orders.id\n"
        )
        _, result = _any_semantics(body)
        assert any(item.code == "PIE-S2102" for item in result.diagnostics)


def test_any_scalar_let_capture_retains_declared_scope_under_local_shadow() -> None:
    from pietto import ast_nodes as ast

    _, result = _any_semantics("""query q:
    from orders
    let floor = orders.id + 1
    select:
        ok = any(orders.floor > floor for orders in customers)
""")
    assert result.diagnostics == ()
    query = result.model.relation_symbols["q"]
    assert isinstance(query, ast.QueryDef)
    (info,) = result.model.any_values.values()
    assert info.captures[0].binding == "orders"
    assert info.captures[0].relation.name == "orders"
    assert info.captures[0].occurrence is query.from_clause
    assert any(
        read.occurrence is info.use.expression and read.relation.name == "customers"
        for read in info.field_reads.values()
    )


@pytest.mark.parametrize("reference", ("accepted", "later"))
@pytest.mark.parametrize("wrapped", (False, True))
def test_any_in_let_preserves_previous_binding_only_scope(
    reference: str, wrapped: bool
) -> None:
    prefix = "def Identity(value: Bool) -> Bool:\n    return value\n" if wrapped else ""
    expression = f"any({reference} for candidate in customers)"
    if wrapped:
        expression = f"Identity({expression})"
    _, result = _any_semantics(
        prefix
        + "query q:\n    from orders\n    let accepted = "
        + expression
        + "\n    let later = True\n    select:\n        id = orders.id\n"
    )
    assert any(
        item.code == "PIE-S2330" and reference in item.message
        for item in result.diagnostics
    )


_AGGREGATE_ANY_SOURCE = """shape Row:
    id: Int

source rows: Row = postgres.table("rows")

query result:
    from rows
"""
_JOINED = "    let other = rows\n    inner join other on rows.id == other.id\n"
_ON_GATE = (
    "PIE-S2334",
    "JOIN-local ON is available only when an EXPLICIT_MODULES project "
    "(schema version 2) completes it.",
    9,
    22,
    9,
    63,
)


def _spans(diagnostics: Sequence[Diagnostic]) -> list[tuple[str | int | None, ...]]:
    return [
        (
            item.code,
            item.message,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in diagnostics
    ]


@pytest.mark.parametrize(
    ("body", "span", "project_gates"),
    (
        pytest.param(
            "    select found = any(count() is None for candidate in rows)\n",
            (8, 24, 8, 39),
            (),
            id="select_is_none",
        ),
        pytest.param(
            "    select found = any(count() > 0 for candidate in rows)\n",
            (8, 24, 8, 35),
            (),
            id="select_comparison",
        ),
        pytest.param(
            "    where not any(min(candidate.id) is None for candidate in rows)\n"
            "    select:\n        id = rows.id\n",
            (8, 19, 8, 44),
            (),
            id="where",
        ),
        pytest.param(
            "    let flag = any(count() > 0 for candidate in rows)\n"
            "    select:\n        id = rows.id\n        ok = flag\n",
            (8, 20, 8, 31),
            (),
            id="let",
        ),
        pytest.param(
            "    select found = any(candidate.id > 0 and any("
            "count_distinct(inner.id) > 1 for inner in rows) for candidate in rows)\n",
            (8, 49, 8, 77),
            (),
            id="nested",
        ),
        pytest.param(
            "    let other = rows\n"
            "    inner join other on any(count() > 0 for candidate in rows)\n"
            "    select:\n        id = rows.id\n",
            (9, 29, 9, 40),
            # The rejected ON keeps this project's canonical ON gate.
            (_ON_GATE,),
            id="on",
        ),
        pytest.param(
            _JOINED + "    where any(count() > 0 for candidate in rows)\n"
            "    select:\n        id = rows.id\n",
            (10, 15, 10, 26),
            (),
            id="joined_where",
        ),
        pytest.param(
            _JOINED + "    select:\n        id = rows.id\n"
            "        found = any(count() > 0 for candidate in rows)\n",
            (12, 21, 12, 32),
            (),
            id="joined_select",
        ),
        pytest.param(
            "    select found = any(candidate.id > 0 for candidate in rows)\n",
            None,
            (),
            id="control",
        ),
    ),
)
def test_project_any_predicate_refuses_an_aggregate_as_a_single_file_does(
    tmp_path: Path,
    body: str,
    span: tuple[int, int, int, int] | None,
    project_gates: tuple[tuple[str | int, ...], ...],
) -> None:
    source = _AGGREGATE_ANY_SOURCE + body
    expected = (
        []
        if span is None
        else [
            (
                "PIE-S2335",
                "Aggregate expressions are unavailable in ANY predicates.",
                *span,
            )
        ]
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    assert _spans(analyze(parsed.ast).diagnostics) == expected
    completed = _completed(tmp_path, source)
    assert _spans(completed.diagnostics) == [*project_gates, *expected]
    assert completed.ok is (span is None)
