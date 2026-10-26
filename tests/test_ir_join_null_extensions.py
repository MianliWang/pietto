"""CROSS/RIGHT/FULL current rows, properties, tails, and project-check closure."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveJoinInputAuthority,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_joined_aggregation import (
    ProjectJoinedAggregationNonConcreteReason,
    ProjectNonConcreteJoinedAggregation,
)
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_join_conditions import ProjectJoinConditionCompletion
from pietto._project.project_join_conditions import ProjectRelationshipMaximumBound
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto._project.project_completion import ProjectEffectiveOutputTerminal
from pietto._project.project_query_block_ir import (
    build_project_query_block_ir,
    ProjectIRQueryBlockTerminal,
)
from pietto import cli
from pietto.ast_nodes import AuthoredJoinKind
from pietto.ir import RelationIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode
from _pietto_project_join_output import (
    _output,
    _tail_source,
)
from _pietto_project_join import (
    _completed,
    _prefix_existence_source,
    _source,
)
from _pietto_project_join_full import _two_current_globals_full, _unique_source


@pytest.mark.parametrize(
    "kind,predicate,left_nullability,right_nullability",
    (
        (
            "cross",
            None,
            ProjectRowFieldNullability.NON_NULL,
            ProjectRowFieldNullability.NON_NULL,
        ),
        (
            "right",
            "lhs.id == r.id",
            ProjectRowFieldNullability.NULLABLE,
            ProjectRowFieldNullability.NON_NULL,
        ),
        (
            "full",
            "lhs.id == r.id",
            ProjectRowFieldNullability.NULLABLE,
            ProjectRowFieldNullability.NULLABLE,
        ),
    ),
)
def test_minimal_new_kinds_complete_exact_rows(
    tmp_path: Path,
    kind: str,
    predicate: str | None,
    left_nullability: ProjectRowFieldNullability,
    right_nullability: ProjectRowFieldNullability,
) -> None:
    result = _completed(
        tmp_path,
        _source(predicate, kind=kind) + "        right_id = r.id\n",
    )
    assert result.ok, result.diagnostics
    regions = result.effective_outputs.current_regions
    assert len(regions) == 1 and len(regions[0].joins) == 1
    join = regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.use.kind is AuthoredJoinKind(kind)
    if kind == "cross":
        assert join.condition.expression is None
    else:
        on_clause = join.condition.use.clause.on_clause
        assert on_clause is not None
        assert join.condition.expression is on_clause.expression
    assert tuple(
        field.effective_nullability for field in join.output.row_shape.fields
    ) == (
        left_nullability,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.NULLABLE,
        right_nullability,
        ProjectRowFieldNullability.NULLABLE,
        ProjectRowFieldNullability.NULLABLE,
    )
    entries = tuple(
        entry
        for entry in result.effective_outputs.entries
        if entry.owner.definition.name == "result"
    )
    assert len(entries) == 1 and isinstance(entries[0], ProjectCompletedEffectiveOutput)
    assert tuple(entries[0].schema.fields) == ("id", "right_id")
    assert entries[0].schema.fields["id"].nullability is left_nullability
    assert entries[0].schema.fields["right_id"].nullability is right_nullability


@pytest.mark.parametrize(
    "kind,predicate",
    (
        ("inner", "lhs.id == r.id"),
        ("left", "lhs.id == r.id"),
        ("left", "Link(lhs, r) and r.key is not None"),
    ),
)
def test_existing_inner_left_and_refinement_controls_remain_green(
    tmp_path: Path, kind: str, predicate: str
) -> None:
    assert _completed(tmp_path, _source(predicate, kind=kind)).ok


type _BagRow = tuple[int | None, int | None, int | None, int | None]


def _expected_join_bag(
    kind: str, left: tuple[int | None, ...], right: tuple[int | None, ...]
) -> tuple[_BagRow, ...]:
    """Independent finite occurrence oracle; production has no evaluator."""
    if kind == "cross":
        return tuple(
            (left_position, left_value, right_position, right_value)
            for left_position, left_value in enumerate(left)
            for right_position, right_value in enumerate(right)
        )
    rows: list[_BagRow] = []
    matched_right: set[int] = set()
    for left_position, left_value in enumerate(left):
        matched_left = False
        for right_position, right_value in enumerate(right):
            if (
                left_value is not None
                and right_value is not None
                and left_value == right_value
            ):
                rows.append((left_position, left_value, right_position, right_value))
                matched_left = True
                matched_right.add(right_position)
        if not matched_left and kind in {"left", "full"}:
            rows.append((left_position, left_value, None, None))
    if kind in {"right", "full"}:
        rows.extend(
            (None, None, right_position, right_value)
            for right_position, right_value in enumerate(right)
            if right_position not in matched_right
        )
    return tuple(rows)


def test_independent_finite_bag_reference_covers_duplicates_nulls_and_empty_sides() -> (
    None
):
    values = (1, 1, None)
    bags = {
        kind: _expected_join_bag(kind, values, values)
        for kind in ("inner", "left", "cross", "right", "full")
    }
    assert {kind: len(rows) for kind, rows in bags.items()} == {
        "inner": 4,
        "left": 5,
        "cross": 9,
        "right": 5,
        "full": 6,
    }
    assert bags["inner"] == (
        (0, 1, 0, 1),
        (0, 1, 1, 1),
        (1, 1, 0, 1),
        (1, 1, 1, 1),
    )
    assert bags["full"][-2:] == (
        (2, None, None, None),
        (None, None, 2, None),
    )
    assert len(_expected_join_bag("full", (None, None), (None, None))) == 4
    assert _expected_join_bag("cross", (), values) == ()
    assert _expected_join_bag("cross", values, ()) == ()
    assert _expected_join_bag("right", (), (1, None)) == (
        (None, None, 0, 1),
        (None, None, 1, None),
    )
    assert _expected_join_bag("full", (1, None), ()) == (
        (0, 1, None, None),
        (1, None, None, None),
    )
    assert _expected_join_bag("full", (), ()) == ()
    asymmetric = _expected_join_bag("right", (1, 2), (1, 3, 3))
    assert asymmetric == (
        (0, 1, 0, 1),
        (None, None, 1, 3),
        (None, None, 2, 3),
    )


@pytest.mark.parametrize("kind", ("right", "full"))
@pytest.mark.parametrize(
    "predicate", ("Link(lhs, r)", "Link(lhs, r) and False", "Link(lhs, r) and r.id > 0")
)
def test_predicate_and_filter_forms_keep_exact_condition_authority(
    tmp_path: Path, kind: str, predicate: str
) -> None:
    completed = _completed(tmp_path, _source(predicate, kind=kind))
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.condition is condition and join.kind is AuthoredJoinKind(kind)
    assert condition.mode == "M3"
    assert len(condition.mandatory_equalities) == 1
    predicate_fact = condition.environment.predicate_expression
    assert (
        predicate_fact is not None
        and condition.mandatory_equalities[0].calls == predicate_fact.calls
    )


def test_full_nulls_every_authored_prefix_binding_and_following_on_sees_it(
    tmp_path: Path,
) -> None:
    source = (
        _source("Link(lhs, r)")
        .replace(
            "    let r = rhs\n    inner join r on Link(lhs, r)\n",
            "    let mid = rhs\n    inner join mid on Link(lhs, mid)\n"
            "    let r = lhs\n    inner join r on Link(r, mid)\n",
        )
        .replace(
            "    select:\n",
            "    let c = rhs\n    full join c on r.id == c.id\n    let d = rhs\n    inner join d on lhs.id == d.id\n    select:\n",
        )
    )
    source += "        c_id = c.id\n        d_id = d.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    assert len(region.joins) == 4
    full, following = region.joins[2:]
    assert isinstance(full, ProjectCurrentBinaryJoin)
    assert isinstance(following, ProjectCurrentBinaryJoin)
    assert full.kind is AuthoredJoinKind.FULL
    left_count = len(full.left_input.fields)
    assert left_count == 9
    assert all(
        field.nulling_joins[-1] is full.node.ref
        for field in full.output.row_shape.fields[:left_count]
    )
    assert all(
        field.nulling_joins == (full.node.ref,)
        for field in full.output.row_shape.fields[left_count:]
    )
    middle = tuple(
        field
        for field in full.output.row_shape.fields[:left_count]
        if field.introduction_use is region.joins[0].input_uses[1]
    )
    assert len(middle) == 3 and all(
        field.nulling_joins[-1] is full.node.ref for field in middle
    )
    following_condition = completed.roots.join_conditions.entries[3]
    lhs_reference = following_condition.references[0]
    assert lhs_reference.target is not None
    assert lhs_reference.target.nullability is ProjectRowFieldNullability.NULLABLE
    assert lhs_reference.target.null_extensions[-1] is full.use.identity


@pytest.mark.parametrize("kind", ("right", "full"))
def test_outer_append_preserves_prior_left_nulling_history(
    tmp_path: Path, kind: str
) -> None:
    source = _source("lhs.id == r.id", kind="left")
    source = source.replace(
        "    select:\n",
        f"""    let last = rhs
    {kind} join last on r.id == last.id
    select:
""",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    first, outer = completed.effective_outputs.current_regions[0].joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(outer, ProjectCurrentBinaryJoin)
    first_right = first.output.row_shape.fields[len(first.left_input.fields) :]
    carried_right = outer.output.row_shape.fields[
        len(first.left_input.fields) : len(first.output.row_shape.fields)
    ]
    assert all(field.nulling_joins == (first.node.ref,) for field in first_right)
    assert all(
        field.nulling_joins == (first.node.ref, outer.node.ref)
        for field in carried_right
    )
    outer_right = outer.output.row_shape.fields[len(outer.left_input.fields) :]
    assert all(
        field.nulling_joins == ((outer.node.ref,) if kind == "full" else ())
        for field in outer_right
    )


@pytest.mark.parametrize(
    "kind,expected_strength",
    (
        ("cross", ProjectRowUniquenessStrength.STRICT),
        ("right", ProjectRowUniquenessStrength.LAX),
        ("full", ProjectRowUniquenessStrength.LAX),
    ),
)
def test_generic_products_keep_only_sound_composite_keys_and_no_cross_classes(
    tmp_path: Path, kind: str, expected_strength: ProjectRowUniquenessStrength
) -> None:
    # `key` is no key, so its equality proves no match bound.
    predicate = None if kind == "cross" else "lhs.key == r.key"
    completed = _completed(tmp_path, _unique_source(kind, predicate))
    properties = completed.effective_outputs.current_regions[
        0
    ].final_properties.relational
    assert len(properties.keys) == 1
    key = properties.keys[0]
    assert tuple(
        member.field_position
        for value_class in key.determinants
        for member in value_class.members
    ) == (0, 3)
    assert key.strength is expected_strength
    assert all(
        not (
            any(member.field_position < 3 for member in value_class.members)
            and any(member.field_position >= 3 for member in value_class.members)
        )
        for value_class in properties.value_classes
    )
    condition = completed.roots.join_conditions.entries[0]
    if kind == "cross":
        assert condition.expression is None and not condition.null_rejections


@pytest.mark.parametrize("kind", ("right", "full"))
def test_relationship_bounds_transfer_keys_with_exact_side_strength(
    tmp_path: Path, kind: str
) -> None:
    # A hand-written ON equality transfers the keys the relationship does.
    for name, predicate in (
        ("call", "Link(lhs, r)"),
        ("handwritten", "lhs.id == r.id"),
    ):
        completed = _completed(tmp_path / name, _unique_source(kind, predicate))
        properties = completed.effective_outputs.current_regions[
            0
        ].final_properties.relational
        singleton = {
            tuple(
                member.field_position
                for item in key.determinants
                for member in item.members
            ): key
            for key in properties.keys
            if len(key.determinants) == 1
        }
        assert set(singleton) == {(0,), (3,)}
        assert singleton[(0,)].strength is ProjectRowUniquenessStrength.LAX
        assert singleton[(3,)].strength is (
            ProjectRowUniquenessStrength.STRICT
            if kind == "right"
            else ProjectRowUniquenessStrength.LAX
        )


@pytest.mark.parametrize("kind", ("right", "full"))
def test_left_nulling_match_gives_no_left_to_right_grain_dependency(
    tmp_path: Path, kind: str
) -> None:
    """Each right row that matches no left row is kept beside one NULL left
    part, so with NULL as a value the left side determines no right row: the
    at-most-one match keeps its keys but gives no left-to-right grain
    dependency. RIGHT keeps the reverse one, which FULL never had."""

    completed = _completed(tmp_path, _unique_source(kind, "Link(lhs, r)"))
    assert completed.ok, completed.diagnostics
    (join,) = completed.effective_outputs.current_regions[0].joins
    assert isinstance(join, ProjectCurrentBinaryJoin)
    matches = tuple(
        m
        for m in join.condition.key_matches
        if m.binding is join.condition.use.target_binding
    )
    assert len(matches) == 1
    assert matches[0].maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    grain = join.properties.relational.grain
    left, right = (
        tuple(
            factor
            for factor in grain.active
            if isinstance(factor, ProjectJoinGrainFactorIdentity)
            and factor.introduction_use == use.ref
        )
        for use in join.input_uses
    )
    assert len(left) == len(right) == 1 and grain.active == (*left, *right)
    assert [(item.determinants, item.dependents) for item in grain.dependencies] == (
        [(right, left)] if kind == "right" else []
    )


def test_source_entity_reverse_bound_does_not_cover_duplicated_accumulated_left(
    tmp_path: Path,
) -> None:
    source = _unique_source("cross", None).replace(
        "let r = rhs\n    cross join r", "let duplicate = lhs\n    cross join duplicate"
    )
    source = source.replace(
        "    select:\n",
        """    let r = rhs
    right join r on Link(lhs, r)
    select:
""",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    region = completed.effective_outputs.current_regions[0]
    first, right = region.joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(right, ProjectCurrentBinaryJoin)
    right_offset = len(right.left_input.fields)
    assert not any(
        all(
            member.field_position >= right_offset
            for determinant in key.determinants
            for member in determinant.members
        )
        for key in right.properties.relational.keys
    )
    right_factors = {
        factor
        for factor in right.properties.relational.grain.active
        if isinstance(factor, ProjectJoinGrainFactorIdentity)
        and factor.introduction_use == right.input_uses[1].ref
    }
    assert right_factors
    assert not any(
        set(dependency.determinants) == right_factors
        and set(dependency.dependents) >= set(right.left_input.grain.active)
        for dependency in right.properties.relational.grain.dependencies
    )


def test_full_of_two_global_inputs_keeps_explicit_unknown_grain(
    tmp_path: Path,
) -> None:
    source = _two_current_globals_full(
        "        left_total = left_global.total\n        right_total = r.total\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    join = completed.effective_outputs.current_regions[-1].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.left_input.grain.state is ProjectGrainBasisState.GLOBAL
    assert join.right_input.grain.state is ProjectGrainBasisState.GLOBAL
    grain = join.properties.relational.grain
    assert grain.state is ProjectGrainBasisState.UNKNOWN
    assert not grain.active
    assert grain.factors
    assert all(
        isinstance(factor.identity, ProjectJoinGrainFactorIdentity)
        for factor in grain.factors
    )
    assert not join.properties.relational.keys
    with pytest.raises((ValueError, TypeError), match="init=False"):
        replace(
            join.properties,
            relational=replace(grain, state=ProjectGrainBasisState.GLOBAL),
        )


def test_unknown_full_grain_reaches_a_typed_aggregate_safety_terminal(
    tmp_path: Path,
) -> None:
    source = _two_current_globals_full("        combined = count()\n")
    completed = _completed(tmp_path / "local", source)
    assert not completed.ok
    tail = completed.effective_outputs.current_tails[-1].results[0]
    aggregation = tail.window_stage.input_aggregation
    assert isinstance(aggregation, ProjectNonConcreteJoinedAggregation)
    assert (
        aggregation.reason
        is ProjectJoinedAggregationNonConcreteReason.INTRINSIC_GRAIN_NON_CONCRETE
    )
    assert aggregation.grain_blocker is not None
    assert aggregation.grain_blocker.state is ProjectGrainBasisState.UNKNOWN
    assert any(diagnostic.code == "PIE-S2333" for diagnostic in completed.diagnostics)
    assert not any(
        diagnostic.code == "PIE-S2334" for diagnostic in completed.diagnostics
    )
    foreign = _completed(tmp_path / "foreign", source)
    foreign_tail = foreign.effective_outputs.current_tails[-1].results[0]
    foreign_aggregation = foreign_tail.window_stage.input_aggregation
    assert isinstance(foreign_aggregation, ProjectNonConcreteJoinedAggregation)
    assert foreign_aggregation.grain_blocker is not None
    with pytest.raises(ValueError, match="exact"):
        replace(aggregation, grain_blocker=foreign_aggregation.grain_blocker)


def test_unknown_full_grain_propagates_through_replay_and_both_join_roles(
    tmp_path: Path,
) -> None:
    source = _two_current_globals_full(
        "        left_total = left_global.total\n        right_total = r.total\n"
    )
    source += """query replay:
    from result
    select:
        left_total
        right_total
query chained_left:
    from replay
    let extra = lhs
    cross join extra
    select:
        left_total = replay.left_total
        extra = extra.id
query chained_right:
    from lhs
    let extra = replay
    cross join extra
    select:
        id = lhs.id
        extra = extra.left_total
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    regions = {
        region.ledger.owner.definition.name: region
        for region in completed.effective_outputs.current_regions
    }
    for name in ("chained_left", "chained_right"):
        grain = regions[name].final_properties.relational.grain
        assert grain.state is ProjectGrainBasisState.UNKNOWN
        assert grain.active
        assert _output(completed, name).fields


@pytest.mark.parametrize(
    "kind,producer,side",
    (
        ("cross", "joined", "right"),
        ("right", "grouped", "right"),
        ("full", "joined", "left"),
        ("full", "grouped", "left"),
        ("right", "joined", "left"),
        ("cross", "grouped", "left"),
    ),
)
def test_completed_inputs_in_both_roles_replay_and_feed_a_following_join(
    tmp_path: Path, kind: str, producer: str, side: str
) -> None:
    parent = _source("lhs.id == r.id" if producer == "joined" else "Link(lhs, r)")
    parent = parent.replace("query result:", "table upstream:")
    if producer == "grouped":
        parent = parent.replace(
            "    select:\n", "    group by:\n        lhs.id\n    select:\n"
        )
        parent += "        total = count()\n"
    on = "" if kind == "cross" else " on lhs.id == u.id"
    if side == "right":
        child = f"""query result:
    from lhs
    let u = upstream
    {kind} join u{on}
    select:
        id = lhs.id
        incoming = u.id
"""
    else:
        on = "" if kind == "cross" else " on upstream.id == u.id"
        child = f"""query result:
    from upstream
    let u = rhs
    {kind} join u{on}
    select:
        id = upstream.id
        incoming = u.id
"""
    downstream = """query replay:
    from result
    select:
        echoed = incoming
query chained:
    from replay
    let r = rhs
    inner join r on replay.echoed == r.id
    select:
        echoed = replay.echoed
"""
    completed = _completed(tmp_path, parent + child + downstream)
    assert completed.ok, completed.diagnostics
    upstream = _output(completed, "upstream")
    result = _output(completed, "result")
    replay = _output(completed, "replay")
    chained = _output(completed, "chained")
    assert result.fields and replay.fields and chained.fields
    region = tuple(
        item
        for item in completed.effective_outputs.current_regions
        if item.ledger.owner.definition.name == "result"
    )[0]
    binding_position = 1 if side == "right" else 0
    authority = region.input_scope
    assert authority is not None
    producer_authority = authority.bindings[binding_position].authority
    assert isinstance(producer_authority, ProjectEffectiveJoinInputAuthority)
    assert producer_authority.entry is upstream


@pytest.mark.parametrize(
    "kind,tail",
    (
        ("cross", "row"),
        ("right", "grouped"),
        ("full", "global"),
        ("right", "selected_window"),
        ("full", "hidden_window"),
    ),
)
def test_new_kinds_use_the_existing_tail_builders(
    tmp_path: Path, kind: str, tail: str
) -> None:
    source, field_name = _tail_source(tail)
    source = source.replace(
        "let r = rhs\n    inner join r", f"let r = rhs\n    {kind} join r"
    )
    if kind == "cross":
        source = source.replace(" on lhs.id == r.id", "")
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    output = _output(completed, "upstream")
    assert field_name in output.schema.fields
    region = completed.effective_outputs.current_regions[0]
    assert region.joins[-1].use.kind is AuthoredJoinKind(kind)
    assert len(completed.effective_outputs.current_tails) == 1
    if tail == "row":
        assert output.ordering is not None and output.limit is not None
    if tail == "hidden_window":
        assert tuple(output.schema.fields) == ("id",)


@pytest.mark.parametrize(
    "kind,tail",
    (
        ("right", "row"),
        ("full", "selected_window"),
        ("cross", "hidden_window"),
    ),
)
def test_completed_order_limit_window_and_qualify_outputs_are_new_kind_inputs(
    tmp_path: Path, kind: str, tail: str
) -> None:
    source, field_name = _tail_source(tail)
    condition = "" if kind == "cross" else f" on u.{field_name} > 0"
    source += f"""query result:
    from lhs
    let u = upstream
    {kind} join u{condition}
    select:
        id = lhs.id
        incoming = u.{field_name}
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    upstream = _output(completed, "upstream")
    result = _output(completed, "result")
    assert result.fields
    region = completed.effective_outputs.current_regions[-1]
    assert region.input_scope is not None
    authority = region.input_scope.bindings[1].authority
    assert isinstance(authority, ProjectEffectiveJoinInputAuthority)
    assert authority.entry is upstream
    if tail == "row":
        assert upstream.ordering is not None and upstream.limit is not None
    else:
        assert isinstance(upstream.root, ProjectConcreteJoinedQualify)
        assert upstream.root.qualify_clause is not None


@pytest.mark.parametrize("kind", ("cross", "right", "full"))
@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_real_project_check_json_succeeds_for_each_kind_and_mode(
    tmp_path: Path, capsys, kind: str, mode: CheckMode
) -> None:
    predicate = None if kind == "cross" else "lhs.id == r.id"
    completed = _completed(
        tmp_path, f"mode {mode.value}\n" + _source(predicate, kind=kind)
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


@pytest.mark.parametrize("kind", ("cross", "right", "full"))
def test_single_file_and_combined_ir_retain_current_joins(
    tmp_path: Path, kind: str
) -> None:
    predicate = None if kind == "cross" else "lhs.id == r.id"
    source = _source(predicate, kind=kind)
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and lowered.diagnostics == ()
    relation = lowered.ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    assert len(relation.inputs) == 2
    assert len(relation.joins) == 1
    completed = _completed(tmp_path, source)
    assert completed.ok
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
def test_invalid_existence_conditions_remain_precisely_unavailable(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(tmp_path, _prefix_existence_source("1", kind))
    assert not completed.ok
    facts = completed.semantic_result.module_semantic_facts
    assert facts is not None
    owner = completed.completion.owners[-1]
    semantic = facts.find_owner(owner)
    assert len(semantic) == 1
    diagnostics = semantic[0].helper_diagnostics
    # The hidden SEMI/ANTI JOIN of the `any`, its ON and the later JOIN's ON.
    assert len(diagnostics) == 3
    assert all(diagnostic.code == "PIE-S2334" for diagnostic in diagnostics)
    hidden, later = completed.roots.join_conditions.entries
    assert [(d.code, d.message) for d in hidden.diagnostics] == [
        ("PIE-S2202", "Expected Bool expression in JOIN ON")
    ]
    # The typed ON's own error replaces only that ON's gate: the published
    # objects are the kind gate, the later JOIN's ON gate and the errors of
    # both conditions.
    published = (
        diagnostics[0],
        diagnostics[2],
        *hidden.diagnostics,
        *later.diagnostics,
    )
    assert len(completed.diagnostics) == len(published)
    assert all(a is b for a, b in zip(completed.diagnostics, published, strict=True))
    assert not completed.effective_outputs.current_regions


def test_success_retires_only_its_exact_temporary_diagnostics(tmp_path: Path) -> None:
    supported = _source("lhs.id == r.id", kind="full")
    unsupported = _prefix_existence_source("1", "semi").split("query result:", 1)[1]
    completed = _completed(tmp_path, supported + "query unsupported:" + unsupported)
    assert not completed.ok
    admissions = completed.effective_outputs.join_admissions
    assert len(admissions) == 1 and len(admissions[0].diagnostics) == 2
    retired = admissions[0].diagnostics
    assert not any(
        diagnostic is retained
        for diagnostic in retired
        for retained in completed.diagnostics
    )
    entries = {
        entry.owner.definition.name: entry
        for entry in completed.effective_outputs.entries
    }
    facts = completed.semantic_result.module_semantic_facts
    assert facts is not None
    unsupported_facts = facts.find_owner(entries["unsupported"].owner)
    assert len(unsupported_facts) == 1
    kind_gate, _, later_gate = unsupported_facts[0].helper_diagnostics
    hidden, later = (
        condition
        for condition in completed.roots.join_conditions.entries
        if condition.ledger.owner is entries["unsupported"].owner
    )
    # Its typed ON error replaces only its own ON gate; its same-code kind
    # gate, the later JOIN's ON gate and the conditions' errors stay the
    # published objects.
    published = (kind_gate, later_gate, *hidden.diagnostics, *later.diagnostics)
    assert len(completed.diagnostics) == len(published)
    assert all(a is b for a, b in zip(completed.diagnostics, published, strict=True))


@pytest.mark.parametrize(
    "source",
    (
        _source("True", kind="cross"),
        _source("1", kind="full"),
    ),
)
def test_invalid_combinations_or_conditions_allocate_no_current_region(
    tmp_path: Path, source: str
) -> None:
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert not completed.effective_outputs.current_regions
    assert not completed.effective_outputs.allocation_events
    assert any(
        diagnostic.code in {"PIE-S2202", "PIE-S2336"}
        for diagnostic in completed.diagnostics
    )


def test_outer_current_binary_rejects_foreign_side_condition_and_allocation_roots(
    tmp_path: Path,
) -> None:
    local = _completed(tmp_path / "local", _source("lhs.id == r.id", kind="full"))
    foreign = _completed(tmp_path / "foreign", _source("lhs.id == r.id", kind="full"))
    left = local.effective_outputs.current_regions[0].joins[0]
    other = foreign.effective_outputs.current_regions[0].joins[0]
    assert isinstance(left, ProjectCurrentBinaryJoin)
    assert isinstance(other, ProjectCurrentBinaryJoin)
    for values in (
        {"condition": other.condition},
        {"left_input": other.left_input},
        {"right_input": other.right_input},
        {"left_fields": other.left_fields},
        {"starting_allocation": other.starting_allocation},
        {"left_input": left.right_input},
    ):
        with pytest.raises(ValueError, match="exact|authority|root|scope|input"):
            replace(left, **values)


def test_cycles_block_members_and_dependents_without_blocking_independent_full(
    tmp_path: Path,
) -> None:
    source = _source("lhs.id == r.id", kind="full").replace(
        "query result:", "query independent:"
    )
    source += """table a:
    from b
    let extra = lhs
    right join extra on b.id == extra.id
    select:
        id = b.id
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
    topology = completed.completion.topology
    assert {owner.definition.name for owner in topology.blocked_owners} == {
        "a",
        "b",
        "dependent",
    }
    blocked = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name in {"a", "b", "dependent"}
    )
    assert all(
        isinstance(entry, ProjectEffectiveOutputTerminal) and entry.output is None
        for entry in blocked
    )
    assert tuple(
        region.ledger.owner.definition.name
        for region in completed.effective_outputs.current_regions
    ) == ("independent",)
    for entry in blocked:
        assert isinstance(entry, ProjectEffectiveOutputTerminal)
        blocker = entry.cycle_blocker
        assert blocker is not None
        assert blocker.is_cycle_member is (entry.owner.definition.name in {"a", "b"})
        assert all(
            any(diagnostic is retained for retained in completed.diagnostics)
            for cycle in blocker.cycles
            for diagnostic in cycle.diagnostics
        )


@pytest.mark.parametrize("kind", ("right", "full"))
def test_nullable_or_condition_produces_no_unconditional_cross_side_fact(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(
        tmp_path, _source("lhs.key == r.key or lhs.allow_any", kind=kind)
    )
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    assert condition.ready and condition.conjuncts == (condition.expression,)
    assert not condition.null_rejections
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    split = len(join.left_input.fields)
    assert all(
        not (
            any(member.field_position < split for member in value_class.members)
            and any(member.field_position >= split for member in value_class.members)
        )
        for value_class in join.properties.relational.value_classes
    )


@pytest.mark.parametrize("kind", ("right", "full"))
def test_null_extended_local_fds_keep_only_sound_strength(
    tmp_path: Path, kind: str
) -> None:
    completed = _completed(tmp_path, _unique_source(kind, "Link(lhs, r)"))
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    split = len(join.left_input.fields)
    left_local = tuple(
        fact
        for fact in join.properties.relational.fds
        if all(
            member.field_position < split
            for value_class in (*fact.determinants, *fact.dependents)
            for member in value_class.members
        )
    )
    right_local = tuple(
        fact
        for fact in join.properties.relational.fds
        if all(
            member.field_position >= split
            for value_class in (*fact.determinants, *fact.dependents)
            for member in value_class.members
        )
    )
    assert left_local and right_local
    assert all(fact.strength is ProjectRowUniquenessStrength.LAX for fact in left_local)
    assert all(
        fact.strength
        is (
            ProjectRowUniquenessStrength.STRICT
            if kind == "right"
            else ProjectRowUniquenessStrength.LAX
        )
        for fact in right_local
    )
    assert all(fact.determinants for fact in join.properties.relational.fds)


def test_full_filtered_predicate_keeps_key_upper_bound_without_coverage(
    tmp_path: Path,
) -> None:
    completed = _completed(tmp_path, _unique_source("full", "Link(lhs, r) and False"))
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    matches = tuple(
        m for m in condition.key_matches if m.binding is condition.use.target_binding
    )
    assert len(matches) == 1
    assert matches[0].maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert matches[0].minimum.value == "zero_allowed"
    join = completed.effective_outputs.current_regions[0].joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert all(
        field.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for field in join.output.row_shape.fields
    )


def test_join_on_and_later_where_keep_separate_authority(tmp_path: Path) -> None:
    source = _source("False", kind="full").replace(
        "    select:\n", "    where lhs.id > 0\n    select:\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    tail = completed.effective_outputs.current_tails[0].results[0]
    row_filter = tail.window_stage.input_aggregation.input_filter
    assert row_filter.where_clause is not None
    on_clause = condition.use.clause.on_clause
    assert on_clause is not None
    assert condition.expression is on_clause.expression
    assert row_filter.where_clause.expression is not condition.expression
    assert all(
        field.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for field in completed.effective_outputs.current_regions[0]
        .joins[0]
        .output.row_shape.fields
    )


def test_cross_fanout_does_not_manufacture_aggregate_permission(
    tmp_path: Path,
) -> None:
    source = _source(None, kind="cross").replace("id = lhs.id", "total = sum(lhs.id)")
    completed = _completed(tmp_path, source)
    assert not completed.ok
    aggregation = (
        completed.effective_outputs.current_tails[0]
        .results[0]
        .window_stage.input_aggregation
    )
    assert aggregation.grain_linkages
    assert any(link.requirements for link in aggregation.grain_linkages)
    assert any(
        diagnostic.severity.value == "error" for diagnostic in completed.diagnostics
    )


@pytest.mark.parametrize("kind", ("cross", "full"))
def test_repeated_completed_self_use_keeps_distinct_input_occurrences(
    tmp_path: Path, kind: str
) -> None:
    parent = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    condition = "" if kind == "cross" else " on False"
    source = (
        parent
        + f"""query result:
    from upstream
    let again = upstream
    {kind} join again{condition}
    select:
        id = upstream.id
        repeated = again.id
"""
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    parent_region, region = completed.effective_outputs.current_regions
    original = parent_region.final_properties.relational.grain.active
    factors = region.final_properties.relational.grain.active
    assert len(original) == 2 and len(factors) == len(set(factors)) == 4
    assert all(
        isinstance(factor, ProjectJoinGrainFactorIdentity)
        and any(factor.source_factor is source_factor for source_factor in original)
        for factor in factors
    )
    join = region.joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert join.left_input is join.right_input
    assert join.input_uses[0] is not join.input_uses[1]
    assert region.binding_introductions[0] is not region.binding_introductions[1]
    if kind == "full":
        assert all(
            field.nulling_joins == (join.node.ref,)
            for field in join.output.row_shape.fields
        )


def test_import_and_reexport_keep_exact_completed_input_dependency(
    tmp_path: Path,
) -> None:
    parent = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    (tmp_path / "a.pietto").write_text(parent + "export table upstream\n")
    (tmp_path / "b.pietto").write_text(
        'from "a.pietto" import table upstream as Public\nexport table Public\n'
    )
    main = """from "b.pietto" import table Public as Imported
shape Local:
    id: Int
source local_rows: Local = postgres.table("local")
query result:
    from local_rows
    let incoming = Imported
    full join incoming on local_rows.id == incoming.id
    select:
        id = local_rows.id
        imported = incoming.id
"""
    completed = _completed(tmp_path, main)
    assert completed.ok, completed.diagnostics
    upstream = _output(completed, "upstream")
    output = _output(completed, "result")
    dependencies = tuple(
        item for item in output.dependencies if item.target is upstream.owner
    )
    assert len(dependencies) == 1
    region = tuple(
        item
        for item in completed.effective_outputs.current_regions
        if item.ledger.owner is output.owner
    )[0]
    assert region.input_scope is not None
    binding = region.input_scope.bindings[1]
    assert binding.dependency is dependencies[0]
    assert binding.binding.relation_name == "Imported"
    assert binding.authority is not None and binding.authority.entry is upstream


@pytest.mark.parametrize("value,ok", (("True", True), ("1", False)))
def test_changed_completed_input_type_rebuilds_right_condition(
    tmp_path: Path, value: str, ok: bool
) -> None:
    source = (
        _source("lhs.id == r.id")
        .replace("query result:", "table upstream:")
        .replace("id = lhs.id", f"flag = {value}")
    )
    source += """query result:
    from lhs
    let incoming = upstream
    right join incoming on incoming.flag
    select:
        id = lhs.id
"""
    completed = _completed(tmp_path, source)
    assert completed.ok is ok
    conditions = completed.roots.join_conditions
    assert isinstance(conditions, ProjectJoinConditionCompletion)
    current, historical = conditions.entries[-1], conditions.historical.entries[-1]
    assert current is not historical and not historical.ready
    assert current.ready is ok and current.inputs is not None
    if not ok:
        assert any(diagnostic.code == "PIE-S2202" for diagnostic in current.diagnostics)
        assert not any(
            region.ledger.owner is current.use.owner
            for region in completed.effective_outputs.current_regions
        )


def test_project_explain_keeps_schema4_and_does_not_observe_new_current_ir(
    tmp_path: Path, capsys
) -> None:
    assert _completed(tmp_path, _source("False", kind="full")).ok
    assert cli.main(["explain", "--project", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "schema version 4" in captured.err


@pytest.mark.parametrize("outer_after", (False, True))
def test_inner_relationship_with_extra_on_retains_complete_non_null_facts(
    tmp_path: Path, outer_after: bool
) -> None:
    source = (
        "shape Row:\n    id: Int\n    key: Int | None\n    row_key = unique(id)\n"
        'source rows: Row = postgres.table("rows")\n'
        "relationship Link(many: Row, one: Row):\n    many.key == one.id\n"
        "query result:\n    from rows\n    let matched = rows\n    inner join matched on Link(matched, rows) and matched.id > 0\n"
    )
    if outer_after:
        source += "    let later = rows\n    right join later on Link(matched, later)\n"
    source += "    select:\n        value = matched.key\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    (region,) = completed.effective_outputs.current_regions
    inner = region.joins[0]
    assert isinstance(inner, ProjectCurrentBinaryJoin)
    assert (
        inner.right_input.fields[1].effective_nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    matched = inner.output.row_shape.fields[len(inner.left_input.fields) + 1]
    assert matched.evidence.nullability is ProjectRowFieldNullability.NULLABLE
    assert matched.effective_nullability is ProjectRowFieldNullability.NON_NULL
    final = region.joins[-1].output.row_shape.fields[matched.field_position]
    assert final.introduction_use is matched.introduction_use
    assert final.effective_nullability is (
        ProjectRowFieldNullability.NULLABLE
        if outer_after
        else ProjectRowFieldNullability.NON_NULL
    )


def test_match_non_null_facts_keep_exact_equivalent_field_occurrences(
    tmp_path: Path,
) -> None:
    source = (
        "shape Row:\n    id: Int\n    key: Int | None\n    row_key = unique(id)\n"
        'source rows: Row = postgres.table("rows")\n'
        "query aliased:\n    from rows\n    select:\n        id\n        key\n        sibling = key\n"
        "query result:\n    from rows\n    let matched = aliased\n    inner join matched on matched.key == rows.id and matched.id > 0\n"
        "    select:\n        value = matched.key\n        sibling = matched.sibling\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    (region,) = completed.effective_outputs.current_regions
    (join,) = region.joins
    assert isinstance(join, ProjectCurrentBinaryJoin)
    assert any(
        len(value_class.members) == 2 for value_class in join.right_input.value_classes
    )
    fields = join.output.row_shape.fields[len(join.left_input.fields) :]
    assert tuple(field.effective_nullability for field in fields) == (
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NON_NULL,
        ProjectRowFieldNullability.NULLABLE,
    )


@pytest.mark.parametrize("unique_match", (False, True))
def test_self_relationship_reverse_grain_uses_endpoint_identity(
    tmp_path: Path, unique_match: bool
) -> None:
    source = (
        "shape Row:\n    id: Int\n    key: Int | None\n    flag: Bool\n"
        "    row_key = unique(id)\n"
        + ("    match_key = unique(key)\n" if unique_match else "")
        + 'source agg: Row = postgres.table("agg")\n'
        + "relationship Link(many: Row, one: Row):\n    many.key == one.id\n"
        "query result:\n    from agg\n    let r = agg\n    right join r on Link(agg, r) and r.flag\n"
        "    let p = agg\n    inner join p on Link(p, r) and p.id > 0\n    select:\n        n = count()\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    (region,) = completed.effective_outputs.current_regions
    right, inner = region.joins
    assert isinstance(right, ProjectCurrentBinaryJoin)
    assert isinstance(inner, ProjectCurrentBinaryJoin)
    # Without match_key only the inner join keeps the local p -> r dependency
    # proved by r's own key (row_key); nothing reaches the right join's left.
    for join, expected, expected_without_match_key in (
        (right, (((1,), (0,)),), ()),
        (inner, (((1,), (0,)), ((0, 1), (2,)), ((2,), (0, 1))), (((2,), (1,)),)),
    ):
        grain = join.properties.relational.grain
        positions = {factor.identity: i for i, factor in enumerate(grain.factors)}
        assert tuple(
            (
                tuple(positions[f] for f in fact.determinants),
                tuple(positions[f] for f in fact.dependents),
            )
            for fact in grain.dependencies
        ) == (expected if unique_match else expected_without_match_key)
