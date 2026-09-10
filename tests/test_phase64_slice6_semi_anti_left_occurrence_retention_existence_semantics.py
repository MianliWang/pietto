"""Authored existence JOINs retain left occurrences and predicate dependencies."""

from pathlib import Path
from collections.abc import Callable
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
    ProjectCurrentMultiFactRegion,
    ProjectActualGrainAuthorityKind,
)
from pietto._project.project_joined_aggregation import (
    ProjectNonConcreteJoinedAggregation,
    ProjectJoinedAggregationNonConcreteReason,
)
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_query_block_ir import (
    build_project_query_block_ir,
    ProjectIRQueryBlockTerminal,
)
from pietto._project.project_join_conditions import ProjectJoinConditionCompletion
from pietto._project.project_current_join_inputs import ProjectCurrentPreMatchInputs
from pietto import cli
from pietto.semantic.model import CheckMode
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.ir import build_ir
from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
    _two_current_globals_full,
    _unique_source,
)
from pietto.ast_nodes import AuthoredJoinKind
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)
from test_phase64_slice4_effective_output_join_first_generic_vertical_closure import (
    _output,
    _tail_source,
)


type Row = tuple[int, int | None]
type Predicate = Callable[[int | None, int | None], bool | None]


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_authored_existence_retains_exact_left_fields_and_both_input_uses(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(tmp_path, _source("lhs.id == r.id", kind=kind))
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    join = region.joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.kind is AuthoredJoinKind(kind)
    assert join.output is not join.left_input.output
    assert len(join.input_slots) == len(join.input_uses) == 2
    assert join.input_uses[0].output is join.left_input.output.occurrence
    assert join.input_uses[1].output is join.right_input.output.occurrence
    assert join.field_inputs == join.left_fields
    assert len(join.output.row_shape.fields) == len(join.left_input.fields)
    for actual, original in zip(
        join.output.row_shape.fields, join.left_input.fields, strict=True
    ):
        assert actual.evidence is original.evidence
        assert actual.effective_nullability is original.effective_nullability
        assert actual.introduction_use is join.input_uses[0]
        assert not actual.nulling_joins
    assert tuple(_output(completed, "result").schema.fields) == ("id",)
    assert len(region.ledger.bindings) == len(region.binding_introductions) == 2
    assert region.introduction(join.use.target_binding) is join.input_uses[1]
    assert not region.hidden_introductions
    assert any(
        item.evidence is join.use.target_binding
        for item in completed.effective_outputs.base.dependencies
    )


@pytest.mark.parametrize("kind", ("inner", "left", "cross", "right", "full"))
def test_old_kind_green_control(tmp_path: Path, kind: str) -> None:
    completed = _completed(
        tmp_path, _source(None if kind == "cross" else "lhs.id == r.id", kind=kind)
    )
    assert completed.ok, completed.diagnostics


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("where", ("on", "from", "via"))
def test_consumed_right_cannot_be_a_later_condition_source(
    tmp_path: Path, kind: str, where: str
) -> None:
    following = {
        "on": "    inner join rhs as next_right:\n        from lhs\n        on r.id == next_right.id\n",
        "from": "    inner join lhs as next_right:\n        from r\n        on next_right.id > 0\n",
        "via": "    inner join lhs as next_right:\n        from r\n        via link: r -> l\n",
    }[where]
    source = _source("lhs.id == r.id", kind=kind).replace(
        "    select:\n", following + "    select:\n"
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert not completed.effective_outputs.current_regions
    conditions = completed.effective_outputs.operative_conditions
    assert conditions is not None
    assert conditions.entries[0].ready
    assert not conditions.entries[1].ready
    assert len(conditions.entries[1].environment.bindings) == 3


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("later_kind", ("inner", "right", "full", "semi", "anti"))
def test_following_join_keeps_left_and_its_new_right_without_resurrection(
    tmp_path: Path, kind: str, later_kind: str
) -> None:
    source = _source("lhs.id == r.id", kind=kind).replace(
        "    select:\n",
        f"    {later_kind} join rhs as next_right:\n        from lhs\n"
        "        on lhs.id == next_right.id\n    select:\n",
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


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize(
    "predicate,via,mode",
    (
        (None, "", "M1"),
        (None, "        via link: l -> r\n", "M2"),
        ("r.key > 0 and r.key > 0", "        via link: l -> r\n", "M4"),
    ),
)
def test_direct_matching_modes_retain_base_and_refinement(
    tmp_path: Path, kind: str, predicate: str | None, via: str, mode: str
) -> None:
    completed = _completed(tmp_path, _source(predicate, kind=kind, via=via))
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    condition = join.condition
    assert condition.ready and condition.mode == mode
    assert len(condition.base_conditions) == 1
    assert condition.base_guarantee is not None
    if mode == "M4":
        assert (
            condition.expression is not condition.base_conditions[0].clause.expression
        )
        assert len(condition.conjuncts) == 2
        assert condition.conjuncts[0] is not condition.conjuncts[1]
        assert condition.refinement_guarantee is not None
        assert condition.refinement_guarantee.base is condition.base_guarantee
        assert condition.refinement_guarantee.minimum.value == "zero_allowed"
    witness = join.properties.relational.grain.witness
    assert isinstance(witness, ProjectCurrentJoinGrainWitness)
    assert witness.condition is condition


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize(
    "predicate",
    (
        "true",
        "false",
        "lhs.allow_any",
        "lhs.id > r.id",
        "lhs.key == r.key",
        "lhs.key == r.key or lhs.allow_any",
        "lhs.key is null and r.key is null",
        "lhs.id == r.id and r.allow_any",
    ),
)
def test_generic_predicates_keep_exact_bool_and_no_blanket_null_strengthening(
    tmp_path: Path, kind: str, predicate: str
) -> None:
    completed = _completed(tmp_path, _source(predicate, kind=kind))
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    condition = join.condition
    assert condition.ready and condition.mode == "M3"
    assert not condition.base_conditions and condition.base_guarantee is None
    assert condition.use.clause.on_clause is not None
    assert condition.expression is condition.use.clause.on_clause.expression
    assert condition.value_type is not None
    assert condition.value_type.resolved_type.name == "Bool"
    assert tuple(
        field.effective_nullability for field in join.output.row_shape.fields
    ) == tuple(field.effective_nullability for field in join.left_input.fields)


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
        "satisfying",
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
        "let": "    let:\n        value = r.id\n    select:\n        id = lhs.id\n",
        "where": "    where r.id > 0\n    select:\n        id = lhs.id\n",
        "group": "    group by:\n        r.id\n    select:\n        total = count()\n",
        "aggregate": "    select:\n        total = sum(r.id)\n",
        "satisfying": "    select:\n        total = count()\n    satisfying:\n        r.id > 0\n",
        "window": "    select:\n        rn = row_number() window:\n            order by:\n                r.id\n",
        "qualify": "    select:\n        id = lhs.id\n    qualify:\n        r.id > 0\n",
        "select": "    select:\n        id = r.id\n",
        "order": "    select:\n        id = lhs.id\n    order by:\n        r.id\n",
    }[tail]
    source = (
        _source("lhs.id == r.id", kind=kind).split("    select:\n", 1)[0] + replacement
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok and completed.diagnostics
    assert completed.effective_outputs.current_regions
    region = completed.effective_outputs.current_regions[0]
    assert len(region.final_properties.relational.fields) == 3
    assert not any(d.code == "PIE-S2334" for d in completed.diagnostics)


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_expanded_left_keeps_hidden_fields_duplicate_names_and_prior_nulling(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _source(
            None,
            kind="left",
            via="        via link: l -> r\n        via link: r -> l\n",
        )
        .replace("left join rhs as r:", "left join lhs as r:")
        .replace(
            "    select:\n",
            f"    {kind} join rhs as predicate_right:\n        from r\n        on r.id == predicate_right.id\n    select:\n",
        )
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    previous, join = region.joins[-2:]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert len(join.output.row_shape.fields) == 9
    assert len(region.hidden_introductions) == 1
    assert (
        tuple(field.evidence.name for field in join.output.row_shape.fields).count("id")
        == 3
    )
    for original, output in zip(
        previous.output.row_shape.fields, join.output.row_shape.fields, strict=True
    ):
        assert output.evidence is original.evidence
        assert output.introduction_use is original.introduction_use
        assert output.nulling_joins == original.nulling_joins
        assert output.effective_nullability is original.effective_nullability
    assert any(field.nulling_joins for field in join.output.row_shape.fields)
    assert (
        sum(
            field.introduction_use is region.hidden_introductions[0]
            for field in join.output.row_shape.fields
        )
        == 3
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_self_use_keeps_binding_role_and_does_not_make_unqualified_field_ambiguous(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _source("lhs.id == r.id", kind=kind)
        .replace("join rhs as r:", "join lhs as r:")
        .replace("id = lhs.id", "id = id")
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.left_input is join.right_input
    assert join.input_uses[0] is not join.input_uses[1]
    assert all(
        field.introduction_use is join.input_uses[0]
        for field in join.output.row_shape.fields
    )
    assert all(
        binding is not join.use.target_binding for binding, _ in join.field_inputs
    )
    assert _output(completed, "result").fields


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_c05_named_whole_path_and_multihop_new_kind_boundary(
    tmp_path: Path, kind: str
) -> None:
    source = _source("lhs.id == r.id").replace("query result:", "table whole_path:")
    source += f"""query result:
    from lhs
    {kind} join whole_path as path:
        from lhs
        on lhs.id == path.id
    select:
        id = lhs.id
"""
    completed = _completed(tmp_path / "named", source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[-1]
    assert region.input_scope is not None
    authority = region.input_scope.bindings[1].authority
    assert authority is not None and authority.entry is _output(completed, "whole_path")
    # Independent finite path witness: A2 has a first-hop match with no full path.
    left, first_hop, last_hop = ((0, 1), (1, 2)), ((1, 10), (2, 20)), (10,)
    direct = tuple(row for row in left if any(row[1] == b[0] for b in first_hop))
    whole = tuple(
        row
        for row in left
        if any(row[1] == b[0] and b[1] in last_hop for b in first_hop)
    )
    assert direct == left and whole == left[:1]
    for predicate in (None, "true"):
        rejected = _completed(
            tmp_path / str(predicate),
            _source(
                predicate,
                kind=kind,
                via="        via link: l -> r\n        via link: r -> l\n",
            ),
        )
        assert not rejected.ok
        assert any(d.code == "PIE-S2336" for d in rejected.diagnostics)
        assert not rejected.effective_outputs.current_regions


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_left_key_fd_and_grain_are_exact_subset_images(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(
        tmp_path, _unique_source(kind, "lhs.key == r.key or lhs.allow_any")
    )
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    join = region.joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    left, output = join.left_input, join.properties.relational
    assert left.keys and left.fds and left.grain.active
    assert tuple(key.strength for key in output.keys) == tuple(
        key.strength for key in left.keys
    )
    for before, after in zip(left.value_classes, output.value_classes, strict=True):
        assert tuple(f.field_position for f in before.members) == tuple(
            f.field_position for f in after.members
        )
        assert all(f.output is join.output for f in after.members)
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
    assert len(output.grain.dependencies) == len(left.grain.dependencies)
    assert all(
        isinstance(f, ProjectJoinGrainFactorIdentity)
        and f.introduction_use == join.input_uses[0].ref
        for f in output.grain.active
    )
    witness = output.grain.witness
    assert isinstance(witness, ProjectCurrentJoinGrainWitness)
    assert witness.left is left.grain and witness.right is join.right_input.grain
    assert witness.condition is join.condition
    candidates = ProjectCurrentMultiFactRegion(region=region).actual_candidates
    assert not any(
        a.kind is ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT
        for c in candidates
        for a in c.authorities
    )
    assert (
        not output.grain.dependencies
    )  # Generic ON does not establish a cross-side FD.


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("unknown_side", ("left", "right"))
@pytest.mark.parametrize("aggregate", (False, True))
def test_real_unknown_full_replay_obeys_left_subset_grain_and_typed_aggregate_terminal(
    tmp_path: Path, kind: str, unknown_side: str, aggregate: bool
) -> None:
    source = _two_current_globals_full("        total = left_global.total\n").replace(
        "query result:", "table unknown_rows:"
    )
    source += "table replay:\n    from unknown_rows\n    select:\n        total\n"
    left, right, field = (
        ("replay", "lhs", "total")
        if unknown_side == "left"
        else ("lhs", "replay", "id")
    )
    source += f"query result:\n    from {left}\n    {kind} join {right} as r:\n        from {left}\n        on true\n    select:\n"
    source += (
        "        total = count()\n"
        if aggregate
        else f"        value = {left}.{field}\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok is not (aggregate and unknown_side == "left"), (
        completed.diagnostics
    )
    join = completed.effective_outputs.current_regions[-1].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert (
        join.left_input if unknown_side == "left" else join.right_input
    ).grain.state is ProjectGrainBasisState.UNKNOWN
    expected = (
        ProjectGrainBasisState.UNKNOWN
        if unknown_side == "left"
        else ProjectGrainBasisState.FACTORIZED
    )
    assert join.properties.relational.grain.state is expected
    assert len(join.properties.relational.grain.factors) == len(
        join.left_input.grain.factors
    )
    if aggregate and unknown_side == "left":
        aggregation = (
            completed.effective_outputs.current_tails[-1]
            .results[0]
            .window_stage.input_aggregation
        )
        assert isinstance(aggregation, ProjectNonConcreteJoinedAggregation)
        assert (
            aggregation.reason
            is ProjectJoinedAggregationNonConcreteReason.INTRINSIC_GRAIN_NON_CONCRETE
        )
        assert aggregation.grain_blocker is join.properties.relational.grain


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_global_left_is_at_most_one_but_may_be_filtered_empty(
    tmp_path: Path, kind: str
) -> None:
    source = _two_current_globals_full("        total = left_global.total\n").replace(
        "full join right_global", f"{kind} join right_global"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[-1].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.left_input.grain.state is ProjectGrainBasisState.GLOBAL
    assert join.properties.relational.grain.state is ProjectGrainBasisState.GLOBAL
    assert not join.properties.relational.grain.active
    assert join.condition.base_guarantee is None


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize(
    "tail", ("row", "grouped", "global", "selected_window", "hidden_window")
)
@pytest.mark.parametrize("side", ("left", "right"))
def test_existing_completed_tails_in_both_roles_and_result_replay_join(
    tmp_path: Path, kind: str, tail: str, side: str
) -> None:
    source, field = _tail_source(tail)
    source = source.replace("inner join rhs as r:", f"{kind} join rhs as r:")
    left, right, selected = (
        ("upstream", "rhs", f"upstream.{field}")
        if side == "left"
        else ("lhs", "upstream", "lhs.id")
    )
    source += f"""table result:
    from {left}
    {kind} join {right} as fresh:
        from {left}
        on true
    select:
        value = {selected}
table replay:
    from result
    select:
        value
query last:
    from replay
    inner join lhs as newest:
        from replay
        on replay.value > 0
    select:
        value = replay.value
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    upstream, result = _output(completed, "upstream"), _output(completed, "result")
    region = next(
        r
        for r in completed.effective_outputs.current_regions
        if r.ledger.owner is result.owner
    )
    assert region.input_scope is not None
    authority = region.input_scope.bindings[0 if side == "left" else 1].authority
    assert authority is not None and authority.entry is upstream
    assert _output(completed, "replay").fields and _output(completed, "last").fields


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_existing_left_fanout_remains_an_aggregate_risk(
    tmp_path: Path, kind: str
) -> None:
    source = (
        _source("true")
        .replace(
            "    select:\n",
            f"    {kind} join rhs as predicate_right:\n        from lhs\n        on true\n    select:\n",
        )
        .replace("id = lhs.id", "total = sum(lhs.id)")
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert completed.effective_outputs.current_regions
    region = completed.effective_outputs.current_regions[0]
    join = region.joins[-1]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert (
        len(join.properties.relational.grain.active)
        == len(join.left_input.grain.active)
        == 2
    )
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
    assert any(d.code == "PIE-S2333" for d in completed.diagnostics)


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_right_dependency_cycle_blocks_owner_but_independent_branch_survives(
    tmp_path: Path, kind: str
) -> None:
    source = _source("true", kind=kind).replace("query result:", "query independent:")
    source += f"""table a:
    from lhs
    {kind} join b as dependency:
        from lhs
        on false
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
    assert {
        owner.definition.name for owner in completed.completion.topology.blocked_owners
    } == {"a", "b", "dependent"}
    assert tuple(
        region.ledger.owner.definition.name
        for region in completed.effective_outputs.current_regions
    ) == ("independent",)
    for entry in completed.effective_outputs.entries:
        if entry.owner.definition.name in {"a", "b", "dependent"}:
            assert isinstance(entry, ProjectEffectiveOutputTerminal)
            assert entry.output is None and entry.cycle_blocker is not None
            assert entry.cycle_blocker.is_cycle_member is (
                entry.owner.definition.name in {"a", "b"}
            )
            for cycle in entry.cycle_blocker.cycles:
                assert all(
                    any(d is retained for retained in completed.diagnostics)
                    for d in cycle.diagnostics
                )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_foreign_roots_roles_prefix_and_forged_positive_are_rejected(
    tmp_path: Path, kind: str
) -> None:
    source = _source("lhs.id == r.id", kind=kind).replace(
        "    select:\n",
        "    inner join rhs as next_right:\n        from lhs\n        on lhs.id == next_right.id\n    select:\n",
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
        tmp_path, f"mode {mode.value}\n" + _source("lhs.id == r.id", kind=kind)
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
def test_legacy_ir_rejects_while_combined_ir_retains_existence_inputs(
    tmp_path: Path, kind: str
) -> None:
    source = _source("true", kind=kind)
    parsed = parse_source(source)
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert any(d.code == "PIE-S2334" for d in semantic.diagnostics)
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is None
    assert any(d.code == "PIE-I1000" for d in lowered.diagnostics)
    completed = _completed(tmp_path, source)
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
    )

    snapshot = build_project_query_block_ir(completed)
    assert verify_project_query_block_ir(snapshot).verified
    entry = next(e for e in snapshot.entries if e.owner.definition.name == "result")
    assert isinstance(entry, ProjectIRCompletedQueryBlockOutput)
    assert entry.join_prefix is not None
    joined = entry.join_prefix.final_join
    assert joined.source is completed.effective_outputs.current_regions[0].joins[0]
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
        _source("false", kind=kind)
        .replace(
            "query result:\n",
            "table broken:\n    from rhs\n    select:\n        bad = missing\nquery result:\n",
        )
        .replace("join rhs as r:", "join broken as r:")
    )
    source += "query valid:\n    from lhs\n    select:\n        id\n"
    completed = _completed(tmp_path, source)
    assert not completed.ok
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
    dependencies = tuple(
        d for d in completed.completion.dependencies if d.consumer is result.owner
    )
    assert tuple(d.target.definition.name for d in dependencies) == ("lhs", "broken")
    valid = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "valid"
    )
    assert (
        isinstance(valid, ProjectExistingEffectiveOutput) and valid.output is not None
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("value,ok", (("true", True), ("1", False)))
def test_changed_right_producer_rebuilds_operative_type_evidence(
    tmp_path: Path, kind: str, value: str, ok: bool
) -> None:
    source = (
        _source("true")
        .replace("query result:", "table upstream:")
        .replace("id = lhs.id", f"flag = {value}")
    )
    source += f"query result:\n    from lhs\n    {kind} join upstream as r:\n        from lhs\n        on r.flag\n    select:\n        id = lhs.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok is ok, completed.diagnostics
    operative = completed.effective_outputs.operative_conditions
    assert isinstance(operative, ProjectJoinConditionCompletion)
    condition = operative.entries[-1]
    assert condition.inputs is not None
    assert condition is not operative.historical.entries[-1]
    assert condition.ready is ok
    assert condition.value_type is not None
    assert condition.value_type.resolved_type.name == ("Bool" if ok else "Int")
    assert condition.references[0].target is not None
    assert condition.references[0].target.binding is condition.use.target_binding
    if not ok:
        assert all(
            r.ledger.owner.definition.name != "result"
            for r in completed.effective_outputs.current_regions
        )


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_import_reexported_existence_output_retains_exact_dependency(
    tmp_path: Path, kind: str
) -> None:
    producer = _source("true", kind=kind).replace("query result:", "table upstream:")
    (tmp_path / "a.pietto").write_text(producer + "export:\n    table upstream\n")
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table upstream as Public\nexport:\n    table Public\n'
    )
    source = f"""import "b.pietto":
    table Public as Imported
shape Local:
    id: Int not null
source local_rows: Local is postgres.table("local")
query result:
    from local_rows
    {kind} join Imported as r:
        from local_rows
        on local_rows.id == r.id
    select:
        id = local_rows.id
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    upstream, result = _output(completed, "upstream"), _output(completed, "result")
    dependencies = tuple(d for d in result.dependencies if d.target is upstream.owner)
    assert len(dependencies) == 1
    region = next(
        r
        for r in completed.effective_outputs.current_regions
        if r.ledger.owner is result.owner
    )
    assert region.input_scope is not None
    binding = region.input_scope.bindings[1]
    assert binding.dependency is dependencies[0]
    assert binding.authority is not None and binding.authority.entry is upstream
    assert tuple(result.schema.fields) == ("id",)


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_duplicate_binding_name_is_not_reusable_after_existence(
    tmp_path: Path, kind: str
) -> None:
    source = _source("true", kind=kind).replace(
        "    select:\n",
        "    inner join rhs as r:\n        from lhs\n        on true\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert not completed.effective_outputs.current_regions
    assert len(completed.roots.join_conditions.entries[0].ledger.bindings) == 3


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_exact_retirement_preserves_unrelated_same_code_diagnostics(
    tmp_path: Path, kind: str
) -> None:
    source = _source("true", kind=kind)
    source += "query invalid:" + _source("1", kind=kind).split("query result:", 1)[1]
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert _output(completed, "result").fields
    admissions = completed.effective_outputs.join_admissions
    assert len(admissions) == 1 and len(admissions[0].diagnostics) == 2
    assert all(
        not any(d is retained for retained in completed.diagnostics)
        for d in admissions[0].diagnostics
    )
    facts = completed.semantic_result.module_semantic_facts
    assert facts is not None
    invalid = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "invalid"
    )
    diagnostics = facts.find_owner(invalid.owner)[0].helper_diagnostics
    assert len(diagnostics) == 2 and all(d.code == "PIE-S2334" for d in diagnostics)
    assert all(
        any(d is retained for retained in completed.diagnostics) for d in diagnostics
    )
    assert not isinstance(invalid, ProjectCompletedEffectiveOutput)


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_legacy_flat_and_explain_remain_at_existing_public_boundaries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    _completed(tmp_path, _source("true", kind=kind))
    assert cli.main(["explain", "--project", str(tmp_path), "--format", "json"]) == 2
    explanation = json.loads(capsys.readouterr().out)
    assert explanation["format"] == "pietto.project-explain.v1"
    assert explanation["payload"] is None
    assert explanation["diagnostics"][0]["code"] == "config_schema"
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n'
    )
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
    assert not document["ok"]
    assert any(d["code"] == "PIE-S2334" for d in document["diagnostics"])


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_package_root_does_not_admit_existence_sources(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 3\n[package]\npath = "pkg"\nnamespace = "test"\nname = "example"\nversion = "1.0.0"\nsha256 = "'
        + "a" * 64
        + '"\n'
    )
    (tmp_path / "main.pietto").write_text(_source("true", kind=kind))
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert not captured.err
    assert not json.loads(captured.out)["ok"]


@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_completed_self_use_preserves_nested_left_factor_roles(
    tmp_path: Path, kind: str
) -> None:
    source, _ = _tail_source("row")
    source += f"query result:\n    from upstream\n    {kind} join upstream as r:\n        from upstream\n        on upstream.id == r.id\n    select:\n        id = upstream.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[-1].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.left_input is join.right_input
    for original, retained in zip(
        join.left_input.grain.factors,
        join.properties.relational.grain.factors,
        strict=True,
    ):
        assert isinstance(retained.identity, ProjectJoinGrainFactorIdentity)
        assert retained.identity.source_factor is original.identity
        assert retained.identity.introduction_use == join.input_uses[0].ref
    assert all(
        f.introduction_use is join.input_uses[0] for f in join.output.row_shape.fields
    )


@pytest.mark.parametrize("kind", ("semi", "anti"))
@pytest.mark.parametrize("via", ("", "        via link: l -> r\n"))
def test_later_relationship_join_uses_retained_left_and_new_right(
    tmp_path: Path, kind: str, via: str
) -> None:
    source = _source("true", kind=kind).replace(
        "    select:\n",
        "    inner join rhs as next_right:\n        from lhs\n" + via + "    select:\n",
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
    source = _source("lhs.id == r.id", kind=kind).replace(
        "join rhs as r:", "join lhs as r:"
    )
    source = source.replace(
        "    select:\n",
        "    inner join rhs as next_right:\n        from lhs\n        on lhs.id == next_right.id\n    select:\n",
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
