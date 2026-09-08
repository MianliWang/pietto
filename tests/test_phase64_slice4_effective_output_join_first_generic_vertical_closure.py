"""Real effective-input INNER/LEFT completion through the existing SELECT tail."""

from pathlib import Path
from dataclasses import replace
import json

import pytest

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput
from pietto._project.project_final_outputs import (
    ProjectEffectiveJoinInputAuthority,
    build_project_effective_output_completion,
)
from pietto._project.project_current_join_inputs import ProjectCurrentInputField
from pietto._project.project_current_join_inputs import ProjectCurrentMaterializedInput
from pietto._project.project_join_conditions import ProjectJoinConditionCompletion
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto import cli
from pietto.semantic.model import CheckMode
from pietto._project.project_grain import ProjectJoinGrainFactorIdentity
from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
from pietto._project.project_relationship_match_guarantees import (
    ProjectRelationshipMaximumBound,
    ProjectRelationshipMinimumBound,
)
from pietto._project.project_completion import ProjectEffectiveOutputTerminal
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockTerminal,
    ProjectIRQueryBlockTerminalReason,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationIssueKind,
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _completed,
    _source,
)


@pytest.mark.parametrize("via", ("", "        via link: l -> r\n"))
def test_historical_m1_m2_remain_complete(tmp_path: Path, via: str) -> None:
    result = _completed(tmp_path, _source(None, via=via))
    assert result.ok


@pytest.mark.parametrize(
    "kind,predicate,via",
    (
        ("inner", "lhs.id == r.id", ""),
        ("left", "lhs.id == r.id", ""),
        ("left", "r.key is not null", "        via link: l -> r\n"),
    ),
)
def test_minimal_generic_and_refined_vertical_completion(
    tmp_path: Path, kind: str, predicate: str, via: str
) -> None:
    source = _source(predicate, kind=kind, via=via) + "        right_id = r.id\n"
    result = _completed(tmp_path, source)
    assert result.ok, result.diagnostics
    entries = tuple(
        entry
        for entry in result.effective_outputs.entries
        if entry.owner.definition.name == "result"
    )
    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, ProjectCompletedEffectiveOutput)
    assert tuple(field.output_name for field in entry.fields) == ("id", "right_id")
    assert entry.schema.fields["id"].nullability is ProjectRowFieldNullability.NON_NULL
    expected = (
        ProjectRowFieldNullability.NULLABLE
        if kind == "left"
        else ProjectRowFieldNullability.NON_NULL
    )
    assert entry.schema.fields["right_id"].nullability is expected
    assert result.roots.join_conditions.entries[0].ready


def test_current_join_check_does_not_claim_combined_ir_or_inspection(
    tmp_path: Path,
) -> None:
    completed = _completed(tmp_path, _source("lhs.id == r.id"))
    assert completed.ok
    snapshot = build_project_query_block_ir(completed)
    assert snapshot.ending_allocation is snapshot.starting_allocation
    assert not snapshot.structural.nodes
    terminals = tuple(
        entry
        for entry in snapshot.entries
        if isinstance(entry, ProjectIRQueryBlockTerminal)
    )
    assert len(terminals) == 1
    assert (
        terminals[0].reason
        is ProjectIRQueryBlockTerminalReason.CURRENT_JOIN_COMPOSITION_UNSUPPORTED
    )
    assert terminals[0].blocker is completed.effective_outputs.current_regions
    verification = verify_project_query_block_ir(snapshot)
    assert verification.status is ProjectIRQueryBlockVerificationStatus.INVALID
    assert tuple(issue.kind for issue in verification.issues) == (
        ProjectIRQueryBlockVerificationIssueKind.CURRENT_JOIN_COMPOSITION_UNSUPPORTED,
    )
    with pytest.raises(ValueError, match="unavailable"):
        build_project_query_block_ir_analysis_bundle(verification)
    with pytest.raises(ValueError, match="not VERIFIED"):
        replace(
            verification,
            status=ProjectIRQueryBlockVerificationStatus.VERIFIED,
            issues=(),
        )


def test_retirement_preserves_unrelated_same_code_errors(tmp_path: Path) -> None:
    source = _source("lhs.id == r.id")
    unsupported = _source("1", kind="semi").split("query result:", 1)[1]
    completed = _completed(tmp_path, source + "query unsupported:" + unsupported)
    assert not completed.ok
    entries = {
        entry.owner.definition.name: entry
        for entry in completed.effective_outputs.entries
    }
    assert isinstance(entries["result"], ProjectCompletedEffectiveOutput)
    facts = completed.semantic_result.module_semantic_facts
    assert facts is not None
    unsupported_facts = facts.find_owner(entries["unsupported"].owner)
    assert len(unsupported_facts) == 1
    errors = unsupported_facts[0].helper_diagnostics
    assert len(errors) == 2 and all(
        diagnostic.code == "PIE-S2334" for diagnostic in errors
    )
    assert all(
        any(actual is retained for retained in completed.diagnostics)
        for actual in errors
    )
    retired = tuple(
        d
        for admission in completed.effective_outputs.join_admissions
        for d in admission.diagnostics
    )
    assert len(retired) == 1
    assert not any(d is actual for d in retired for actual in completed.diagnostics)


@pytest.mark.parametrize("producer", ("joined", "grouped"))
@pytest.mark.parametrize("side", ("right", "left"))
def test_completed_inputs_replay_and_subsequent_join(
    tmp_path: Path, producer: str, side: str
) -> None:
    parent = _source("lhs.id == r.id" if producer == "joined" else None)
    parent = parent.replace("query result:", "table upstream:")
    if producer == "grouped":
        parent = parent.replace(
            "    select:\n", "    group by:\n        lhs.id\n    select:\n"
        )
        parent += "        total = count()\n"
    if side == "right":
        child = """query result:
    from lhs
    left join upstream as u:
        from lhs
        on lhs.id == u.id
    select:
        id = lhs.id
        incoming = u.id
"""
    else:
        child = """query result:
    from upstream
    left join rhs as r:
        from upstream
        on upstream.id == r.id
    select:
        id = upstream.id
        incoming = r.id
"""
    downstream = """query replay:
    from result
    select:
        echoed = incoming
query chained:
    from replay
    inner join rhs as r:
        from replay
        on replay.echoed == r.id
    select:
        echoed = replay.echoed
"""
    completed = _completed(tmp_path, parent + child + downstream)
    assert completed.ok, completed.diagnostics
    entries = {
        entry.owner.definition.name: entry
        for entry in completed.effective_outputs.entries
    }
    assert all(
        isinstance(entries[name], ProjectCompletedEffectiveOutput)
        for name in ("upstream", "result", "replay", "chained")
    )
    upstream, replay, chained = (
        entries["upstream"],
        entries["replay"],
        entries["chained"],
    )
    assert isinstance(upstream, ProjectCompletedEffectiveOutput)
    assert isinstance(replay, ProjectCompletedEffectiveOutput)
    assert isinstance(chained, ProjectCompletedEffectiveOutput)
    assert (
        replay.schema.fields["echoed"].nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    assert (
        chained.schema.fields["echoed"].nullability
        is ProjectRowFieldNullability.NON_NULL
    )
    historical = completed.completion.find_owner(entries["upstream"].owner)
    assert len(historical) == 1
    assert historical[0] is upstream.base_entry


@pytest.mark.parametrize(
    "layout", ("relationship_first", "generic_first", "multihop_first")
)
def test_mixed_authored_modes_keep_real_paths_and_bindings(
    tmp_path: Path, layout: str
) -> None:
    if layout == "generic_first":
        source = _source("lhs.id == r.id")
        extra = (
            "    inner join lhs as next:\n        from r\n        via link: r -> l\n"
        )
    else:
        via = "        via link: l -> r\n"
        if layout == "multihop_first":
            via += "        via link: r -> l\n"
        source = _source(None, via=via)
        if layout == "multihop_first":
            source = source.replace("inner join rhs as r:", "inner join lhs as r:")
        extra = (
            "    left join rhs as next:\n        from r\n        on r.id == next.id\n"
        )
    source = source.replace("    select:\n", extra + "    select:\n")
    source += "        other = next.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    regions = completed.effective_outputs.current_regions
    assert len(regions) == 1
    region = regions[0]
    assert len(region.joins) == (3 if layout == "multihop_first" else 2)
    assert len(region.binding_introductions) == 3
    assert bool(region.hidden_introductions) is (layout == "multihop_first")


def _output(
    completed: ProjectConcreteCompletedSemanticResult, name: str
) -> ProjectCompletedEffectiveOutput:
    entries = tuple(
        entry
        for entry in completed.effective_outputs.entries
        if entry.owner.definition.name == name
    )
    assert len(entries) == 1 and isinstance(entries[0], ProjectCompletedEffectiveOutput)
    return entries[0]


def _tail_source(tail: str) -> tuple[str, str]:
    source = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    field_name = "id"
    if tail == "row":
        source = source.replace(
            "    select:\n",
            "    let:\n        adjusted = lhs.id + 1\n    where adjusted > 0\n    select:\n",
        )
        source += "        adjusted_value = adjusted\n    order by:\n        lhs.id desc\n    limit 2\n"
        field_name = "adjusted_value"
    elif tail == "grouped":
        source = source.replace(
            "    select:\n", "    group by:\n        lhs.id\n    select:\n"
        )
        source += "        total = count()\n    satisfying:\n        total > 0\n"
        field_name = "total"
    elif tail == "global":
        source = source.replace("id = lhs.id", "total = count()")
        field_name = "total"
    elif tail == "selected_window":
        source += "        rn = row_number() window:\n            order by:\n                lhs.id\n    qualify:\n        rn <= 2\n"
        field_name = "rn"
    elif tail == "hidden_window":
        source += "    qualify:\n        row_number() window:\n            order by:\n                lhs.id\n        <= 2\n"
    else:
        raise AssertionError(tail)
    return source, field_name


@pytest.mark.parametrize(
    "tail", ("row", "grouped", "global", "selected_window", "hidden_window")
)
def test_existing_tail_results_are_ordinary_current_join_inputs(
    tmp_path: Path, tail: str
) -> None:
    source, field_name = _tail_source(tail)
    source += f"""query result:
    from lhs
    left join upstream as u:
        from lhs
        on u.{field_name} > 0
    select:
        id = lhs.id
        value = u.{field_name}
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    upstream = _output(completed, "upstream")
    output = _output(completed, "result")
    assert (
        output.schema.fields["value"].nullability is ProjectRowFieldNullability.NULLABLE
    )
    fact = completed.roots.join_conditions.entries[-1]
    assert fact.ready and fact.inputs is not None
    authority = fact.inputs.scope.bindings[1].authority
    assert isinstance(authority, ProjectEffectiveJoinInputAuthority)
    assert authority.entry is upstream
    reference = fact.references[0]
    assert reference.target is not None
    current_field = reference.target.input_field
    assert isinstance(current_field, ProjectCurrentInputField)
    assert current_field.original is upstream.fields[current_field.field_position]
    if tail == "row":
        assert upstream.limit is not None and upstream.limit.value == 2
        assert upstream.ordering is not None
    if tail == "hidden_window":
        assert tuple(upstream.schema.fields) == ("id",)


@pytest.mark.parametrize("tail,code", (("row", "PIE-S2329"), ("global", "PIE-S2323")))
def test_current_tail_keeps_existing_scope_restrictions(
    tmp_path: Path, tail: str, code: str
) -> None:
    source, _ = _tail_source(tail)
    if tail == "row":
        source = source.replace("adjusted_value = adjusted", "adjusted = adjusted")
    else:
        source += "    satisfying:\n        total > 0\n"
    completed = _completed(tmp_path, source)
    assert not completed.ok and any(
        diagnostic.code == code for diagnostic in completed.diagnostics
    )


def test_import_and_reexport_retain_exact_dependency_producer(tmp_path: Path) -> None:
    parent = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    (tmp_path / "a.pietto").write_text(parent + "export:\n    table upstream\n")
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table upstream as Public\nexport:\n    table Public\n'
    )
    main = """import "b.pietto":
    table Public as Imported
shape Local:
    id: Int not null
source local_rows: Local is postgres.table("local")
query result:
    from local_rows
    left join Imported as u:
        from local_rows
        on local_rows.id == u.id
    select:
        id = local_rows.id
        incoming = u.id
"""
    completed = _completed(tmp_path, main)
    assert completed.ok, completed.diagnostics
    upstream = _output(completed, "upstream")
    output = _output(completed, "result")
    dependencies = tuple(
        item for item in output.dependencies if item.target is upstream.owner
    )
    assert len(dependencies) == 1
    fact = tuple(
        item
        for item in completed.roots.join_conditions.entries
        if item.use.owner is output.owner
    )[0]
    assert fact.inputs is not None
    binding = fact.inputs.scope.bindings[1]
    assert binding.dependency is dependencies[0]
    assert binding.binding.relation_name == "Imported"
    assert binding.authority is not None and binding.authority.entry is upstream


@pytest.mark.parametrize("value,ok", (("true", True), ("1", False)))
def test_changed_upstream_type_rebuilds_condition_readiness(
    tmp_path: Path, value: str, ok: bool
) -> None:
    source = (
        _source("lhs.id == r.id")
        .replace("query result:", "table upstream:")
        .replace("id = lhs.id", f"flag = {value}")
    )
    source += "query result:\n    from lhs\n    inner join upstream as u:\n        from lhs\n        on u.flag\n    select:\n        id = lhs.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok is ok
    conditions = completed.roots.join_conditions
    assert isinstance(conditions, ProjectJoinConditionCompletion)
    current, historical = conditions.entries[-1], conditions.historical.entries[-1]
    assert current is not historical and not historical.ready
    assert current.ready is ok and current.inputs is not None
    if not ok:
        assert any(d.code == "PIE-S2202" for d in current.diagnostics)
        assert not any(
            region.ledger.owner is current.use.owner
            for region in completed.effective_outputs.current_regions
        )


def test_foreign_stale_field_condition_dependency_and_allocation_roots_fail(
    tmp_path: Path,
) -> None:
    parent = _source("lhs.id == r.id").replace("query result:", "table upstream:")
    source = (
        parent
        + "query result:\n    from lhs\n    inner join upstream as u:\n        from lhs\n        on lhs.id == u.id\n    select:\n        id = lhs.id\n"
    )
    local = _completed(tmp_path / "local", source)
    foreign = _completed(tmp_path / "foreign", source)
    assert local.ok and foreign.ok
    fact = local.roots.join_conditions.entries[-1]
    assert fact.inputs is not None
    scope = fact.inputs.scope
    binding = scope.bindings[1]
    authority = binding.authority
    assert isinstance(authority, ProjectEffectiveJoinInputAuthority)
    with pytest.raises(ValueError, match="exact|detached"):
        replace(authority, entry=_output(foreign, "upstream"))
    with pytest.raises(ValueError, match="binding role"):
        replace(binding, dependency=scope.bindings[0].dependency)
    with pytest.raises(ValueError, match="exact|root"):
        replace(fact, inputs=foreign.roots.join_conditions.entries[-1].inputs)
    field = authority.fields[0]
    assert isinstance(field, ProjectCurrentInputField)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(field, original=_output(foreign, "upstream").fields[0])
    with pytest.raises(ValueError, match="membership"):
        replace(field, field_position=100)
    region = local.effective_outputs.current_regions[-1]
    with pytest.raises(ValueError, match="allocation|prefix"):
        replace(
            region.joins[0],
            starting_allocation=foreign.effective_outputs.current_regions[
                -1
            ].starting_allocation,
        )
    historical = local.effective_outputs.condition_authority
    assert historical is not None
    alternate = build_project_effective_output_completion(
        local.completion,
        local.effective_outputs.joined_qualifies,
        join_conditions=historical,
    )
    alternate_parent = tuple(
        entry
        for entry in alternate.entries
        if entry.owner is _output(local, "upstream").owner
    )[0]
    assert isinstance(alternate_parent, ProjectCompletedEffectiveOutput)
    graft = ProjectEffectiveJoinInputAuthority(
        completion=local.completion, entry=alternate_parent
    )
    graft_binding = replace(binding, authority=graft)
    with pytest.raises(ValueError, match="available entry"):
        replace(scope, bindings=(scope.bindings[0], graft_binding))
    with pytest.raises(ValueError, match="exact|prefix|producer"):
        replace(
            local.effective_outputs,
            entries=tuple(
                alternate_parent if entry.owner is alternate_parent.owner else entry
                for entry in local.effective_outputs.entries
            ),
        )


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_real_project_check_json_success_in_each_mode(
    tmp_path: Path, capsys, mode: CheckMode
) -> None:
    completed = _completed(tmp_path, f"mode {mode.value}\n" + _source("lhs.id == r.id"))
    assert completed.ok
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


def test_repeated_effective_self_use_retains_every_input_factor(tmp_path: Path) -> None:
    parent = (
        _source("lhs.id == r.id")
        .replace("inner join rhs as r", "inner join lhs as r")
        .replace("query result:", "table upstream:")
    )
    source = (
        parent
        + "query result:\n    from upstream\n    inner join upstream as again:\n        from upstream\n        on true\n    select:\n        id = upstream.id\n        repeated = again.id\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    parent_region, region = completed.effective_outputs.current_regions
    original = parent_region.final_properties.relational.grain.active
    factors = region.final_properties.relational.grain.active
    assert len(original) == 2 and len(factors) == len(set(factors)) == 4
    assert all(
        isinstance(factor, ProjectJoinGrainFactorIdentity)
        and any(factor.source_factor is source for source in original)
        for factor in factors
    )
    join = region.joins[0]
    assert join.left_input is join.right_input
    assert join.input_uses[0] is not join.input_uses[1]
    assert region.binding_introductions[0] is not region.binding_introductions[1]


def test_c04_nullable_disjunction_and_independent_bag_witness(tmp_path: Path) -> None:
    source = _source("lhs.key == r.key or lhs.allow_any").replace(
        "id = lhs.id", "key = lhs.key"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok
    output = _output(completed, "result")
    assert (
        output.schema.fields["key"].nullability is ProjectRowFieldNullability.NULLABLE
    )
    fact = completed.roots.join_conditions.entries[0]
    assert not fact.null_rejections and fact.base_guarantee is None
    region = completed.effective_outputs.current_regions[0]
    join = region.joins[0]
    assert isinstance(join, ProjectCurrentBinaryJoin)
    for value_class in region.final_properties.relational.value_classes:
        bindings = {
            id(join.field_inputs[member.field_position][0])
            for member in value_class.members
        }
        assert len(bindings) == 1
    # Independent finite BAG/TRUE-only witness; this is not database execution.
    left = ((None, True),)
    right = ((1, "same"), (1, "same"))
    matches = tuple(
        (key, payload)
        for key, allow_any in left
        for other, payload in right
        if allow_any is True or (key is not None and key == other)
    )
    assert matches == ((None, "same"), (None, "same"))


def test_c03_false_refinement_preserves_upper_root_and_left_nulling(
    tmp_path: Path,
) -> None:
    source = _source("false", kind="left", via="        via link: l -> r\n").replace(
        "    allow_any: Bool nullable\n",
        "    allow_any: Bool nullable\n    unique id_key on id\n",
    )
    source += "        right_id = r.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok
    fact = completed.roots.join_conditions.entries[0]
    refined = fact.refinement_guarantee
    assert refined is not None and fact.base_guarantee is not None
    assert refined.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    assert refined.maximum_evidence is fact.base_guarantee.maximum_evidence
    assert refined.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
    assert (
        _output(completed, "result").schema.fields["right_id"].nullability
        is ProjectRowFieldNullability.NULLABLE
    )


def test_generic_fanout_does_not_manufacture_aggregate_permission(
    tmp_path: Path,
) -> None:
    source = _source("lhs.id == r.id").replace("id = lhs.id", "total = sum(lhs.id)")
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


def test_cycles_preserve_true_members_dependents_diagnostics_and_independent_success(
    tmp_path: Path,
) -> None:
    source = _source("lhs.id == r.id").replace("query result:", "query independent:")
    source += """table a:
    from b
    inner join lhs as extra:
        from b
        on b.id == extra.id
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
    assert all(
        region.ledger.owner.definition.name == "independent"
        for region in completed.effective_outputs.current_regions
    )
    for entry in blocked:
        assert isinstance(entry, ProjectEffectiveOutputTerminal)
        blocker = entry.cycle_blocker
        assert blocker is not None
        assert blocker.is_cycle_member is (entry.owner.definition.name in {"a", "b"})
        for cycle in blocker.cycles:
            assert all(
                any(diagnostic is retained for retained in completed.diagnostics)
                for diagnostic in cycle.diagnostics
            )


def test_project_explain_keeps_its_original_schema_boundary(
    tmp_path: Path, capsys
) -> None:
    assert _completed(tmp_path, _source("lhs.id == r.id")).ok
    assert cli.main(["explain", "--project", str(tmp_path)]) == 2
    captured = capsys.readouterr()
    assert "schema version 4" in captured.err


def test_failed_input_cannot_borrow_another_dependency_blocker(tmp_path: Path) -> None:
    source = (
        _source("true")
        .replace("query result:", "table bad1:")
        .replace("id = lhs.id", "id = missing1")
    )
    source += """table bad2:
    from lhs
    inner join rhs as r:
        from lhs
        on true
    select:
        id = missing2
query consumer:
    from bad1
    inner join bad2 as b:
        from bad1
        on true
    select:
        id = bad1.id
"""
    completed = _completed(tmp_path, source)
    assert not completed.ok
    scope = tuple(
        item
        for item in completed.effective_outputs.input_scopes
        if item.ledger.owner.definition.name == "consumer"
    )[0]
    assert scope.bindings[0].blocker is not scope.bindings[1].blocker
    with pytest.raises(ValueError, match="target|dependency"):
        wrong = replace(scope.bindings[0], blocker=scope.bindings[1].blocker)
        replace(scope, bindings=(wrong, scope.bindings[1]))


def test_current_region_rejects_equal_looking_alternate_prefix_condition(
    tmp_path: Path,
) -> None:
    source = _source("true").replace(
        "    select:\n",
        "    left join lhs as next:\n        from lhs\n        on lhs.id == next.id\n    select:\n",
    )
    completed = _completed(tmp_path, source)
    assert completed.ok
    region = completed.effective_outputs.current_regions[0]
    first, second = region.operative
    assert second.inputs is not None
    with pytest.raises(ValueError, match="prefix"):
        inputs = replace(second.inputs, prefix=(replace(first),))
        altered = replace(second, inputs=inputs)
        replace(region, operative=(first, altered))


def test_replay_materialization_rejects_equal_looking_property_copy(
    tmp_path: Path,
) -> None:
    source = _source("true").replace("query result:", "table joined:")
    source += """table replay:
    from joined
    select:
        id
query consumer:
    from lhs
    inner join replay as p:
        from lhs
        on lhs.id == p.id
    select:
        id = lhs.id
"""
    completed = _completed(tmp_path, source)
    assert completed.ok
    events = tuple(
        event
        for event in completed.effective_outputs.allocation_events
        if isinstance(event, ProjectCurrentMaterializedInput)
        and event.authority.owner.definition.name == "replay"
    )
    assert len(events) == 1 and events[0].incoming is not None
    with pytest.raises(ValueError, match="stale|exact"):
        replace(events[0], incoming=replace(events[0].incoming))
