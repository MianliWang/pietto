"""Set output composition and exact-root adversaries using real authored inputs."""

from pathlib import Path
from dataclasses import replace
import json

import pytest

from pietto._project.project_final_outputs import (
    ProjectCompletedSetOutput,
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletionTerminal,
)
from pietto._project.project_completion import ProjectEffectiveOutputTerminal
from pietto._project.project_grain import ProjectJoinGrainFactorIdentity
from pietto._project.project_row_equivalence import ProjectRowEquivalenceField
from pietto._project.project_completed_semantics import (
    with_project_single_match_requests,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchRequest,
    ProjectSingleMatchState,
    ProjectSingleMatchProofKind,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto.ast_nodes import SetRelationDef
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import CheckMode
from pietto.ir import build_ir
from pietto import cli

from test_phase64_slice9_set_operations_explicit_all_distinct_output_identity import (
    _source,
    _entry,
    _completed,
)
from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
    _source as _join_source,
)
from test_phase64_slice5_cross_right_full_output_shapes_null_extension_property_transfer import (
    _two_current_globals_full,
)


@pytest.mark.parametrize(
    "producer",
    (
        "join",
        "grouped_join",
        "global_join",
        "filtered_join",
        "grouped",
        "global",
        "window_qualify",
        "distinct",
    ),
)
def test_completed_operand_kinds_keep_provenance_not_local_computation_role(
    tmp_path: Path, producer: str
) -> None:
    if producer.endswith("join"):
        source = _join_source("true").replace("query result:", "table operand:")
        if producer == "grouped_join":
            source = source.replace(
                "    select:", "    group by:\n        lhs.id\n    select:"
            )
            source += "        total = count()\n"
        elif producer == "global_join":
            source = source.replace("        id = lhs.id", "        total = count()")
        elif producer == "filtered_join":
            source = source.replace(
                "    select:",
                "    let:\n        next_id = lhs.id + 1\n    where next_id > 0\n    select:",
            ).replace("        id = lhs.id", "        value = next_id")
            source += "    order by:\n        next_id\n    limit 2\n"
    else:
        source = (
            _source().split("table combined:", 1)[0] + "table operand:\n    from lhs\n"
        )
        if producer == "grouped":
            source += "    group by:\n        id\n    select:\n        id\n        total = count()\n"
        elif producer == "global":
            source += "    select:\n        total = count()\n"
        elif producer == "window_qualify":
            source += "    select:\n        id\n        rn = row_number() window:\n            order by:\n                id\n    qualify:\n        rn <= 3\n"
        else:
            source += "    select distinct:\n        id\n"
    source += (
        "table combined:\n    union all:\n        from operand\n        from operand\n"
    )
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    output = _entry(completed)
    assert isinstance(output, ProjectCompletedSetOutput)
    assert output.ordering is output.limit is None
    assert all(
        field.field.result_role.value == "ordinary_row_value"
        and field.field.field_def is None
        for field in output.fields
    )
    assert all(field.source.uses is output.root.uses for field in output.fields)
    assert output.root.uses[0].authority.entry is output.root.uses[1].authority.entry
    if producer in {"grouped", "global", "grouped_join", "global_join"}:
        assert any(
            field.selected.field.result_role.value == "aggregate_result"
            for field in output.root.uses[0].fields
        )
    if producer == "window_qualify":
        assert any(
            field.selected.field.result_role.value == "window_result"
            for field in output.root.uses[0].fields
        )


@pytest.mark.parametrize("side", ("left", "right", "self"))
def test_set_replay_current_join_and_distinct(tmp_path: Path, side: str) -> None:
    source = _source()
    left, right = (
        ("result", "lhs")
        if side == "left"
        else ("lhs", "result")
        if side == "right"
        else ("result", "result")
    )
    source += f"query final:\n    from {left}\n    left join {right} as r:\n        from {left}\n        on true\n    select distinct:\n        left_id = {left}.id\n        right_id = r.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    final = _entry(completed, "final")
    assert (
        isinstance(final, ProjectCompletedEffectiveOutput)
        and final.row_domain.distinct is not None
    )
    combined = _entry(completed)
    assert isinstance(combined, ProjectCompletedSetOutput)
    origin = combined.row_domain.set_origin
    assert origin is not None
    region = completed.effective_outputs.current_regions[-1]
    factors = tuple(
        f
        for f in region.final_properties.relational.grain.active
        if isinstance(f, ProjectJoinGrainFactorIdentity) and f.base is origin.factor
    )
    assert len(factors) == (2 if side == "self" else 1)
    if side == "self":
        assert factors[0].introduction_use != factors[1].introduction_use


def test_decimal_set_replay_join_distinct_and_nested_set(tmp_path: Path) -> None:
    source = _source(right_type="Decimal(10, 2)").replace(
        "id: Int not null", "id: Decimal(10, 2) nullable"
    )
    source += "table joined:\n    from result\n    inner join result as r:\n        from result\n        on true\n    select distinct:\n        price = result.id\ntable final:\n    union distinct:\n        from joined\n        from joined\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    joined = _entry(completed, "joined")
    assert (
        isinstance(joined, ProjectCompletedEffectiveOutput)
        and joined.row_domain.distinct is not None
    )
    evidence = joined.row_domain.distinct.equivalence.evidence[0]
    assert evidence.decimal is not None and (
        evidence.decimal.precision,
        evidence.decimal.scale,
    ) == (10, 2)
    assert evidence.parents and all(p.decimal is not None for p in evidence.parents)
    final = _entry(completed, "final")
    assert isinstance(final, ProjectCompletedSetOutput) and final.uniqueness is not None
    assert final.root.uses[0].authority.entry is joined


def test_import_reexport_preserves_operand_uses_and_labels(tmp_path: Path) -> None:
    parent = _source(replay=False) + "export:\n    table combined\n"
    (tmp_path / "a.pietto").write_text(parent)
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    table combined as Public\nexport:\n    table Public\n'
    )
    source = 'import "b.pietto":\n    table Public as Local\ntable nested:\n    union all:\n        from Local\n        from Local\nquery final:\n    from nested\n    select distinct:\n        id\n'
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    nested = _entry(completed, "nested")
    assert isinstance(nested, ProjectCompletedSetOutput)
    uses = nested.root.uses
    assert uses[0] is not uses[1] and uses[0].authority.entry is uses[1].authority.entry
    assert all(
        use.resolution.target_symbol is not None
        and use.resolution.target_symbol.local_name == "Local"
        for use in uses
    )
    assert all(use.authority.owner.identity.module_path == "a.pietto" for use in uses)
    assert tuple(nested.schema.fields) == ("id",)


def test_cycle_crosses_from_join_and_set_without_blocking_independent(
    tmp_path: Path,
) -> None:
    source = _source().split("table combined:", 1)[0]
    source += """table a:
    from b
    select:
        id
table b:
    union all:
        from c
        from lhs
table c:
    from lhs
    inner join a as x:
        from lhs
        on true
    select:
        id = lhs.id
query dependent:
    from b
    select:
        id
table combined:
    union all:
        from lhs
        from lhs
"""
    completed = _completed(tmp_path, source)
    assert not completed.ok
    topology = completed.completion.topology
    assert [
        {owner.definition.name for owner in cycle.members} for cycle in topology.cycles
    ] == [{"a", "b", "c"}]
    assert {owner.definition.name for owner in topology.blocked_owners} == {
        "a",
        "b",
        "c",
        "dependent",
    }
    entries = {e.owner.definition.name: e for e in completed.effective_outputs.entries}
    assert isinstance(entries["combined"], ProjectCompletedSetOutput)
    for name in ("a", "b", "c", "dependent"):
        entry = entries[name]
        assert (
            isinstance(entry, ProjectEffectiveOutputTerminal) and entry.output is None
        )
        assert entry.cycle_blocker is not None
        assert entry.cycle_blocker.is_cycle_member is (name != "dependent")
    assert not completed.effective_outputs.allocation_events
    assert any(d.code == "PIE-S2302" for d in completed.diagnostics)


@pytest.mark.parametrize("which", ("first", "later"))
def test_missing_operand_has_no_first_available_fallback(
    tmp_path: Path, which: str
) -> None:
    operands = ("missing", "rhs") if which == "first" else ("lhs", "missing")
    completed = _completed(tmp_path, _source(operands=operands, replay=False))
    assert not completed.ok
    output = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "combined"
    )
    assert (
        isinstance(output, ProjectEffectiveOutputCompletionTerminal)
        and output.output is None
    )
    assert not hasattr(output, "schema")
    assert any(d.code == "PIE-S2301" for d in completed.diagnostics)


def test_invalid_upstream_aggregation_is_not_repaired_by_set(tmp_path: Path) -> None:
    source = _two_current_globals_full("        total = count()\n").replace(
        "query result:", "table invalid:"
    )
    source += "table combined:\n    union distinct:\n        from invalid\n        from invalid\n"
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert any(d.code == "PIE-S2333" for d in completed.diagnostics)
    output = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "combined"
    )
    assert isinstance(output, ProjectEffectiveOutputCompletionTerminal)


def test_set_dedup_does_not_discharge_original_matching_obligation(
    tmp_path: Path,
) -> None:
    source = _join_source("true").replace("query result:", "table parent:")
    source += "table combined:\n    union distinct:\n        from parent\n        from parent\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    request = ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use)
    checked = with_project_single_match_requests(completed, (request,))
    assessment = checked.single_matches.entries[0]
    assert checked.ok and assessment.state is ProjectSingleMatchState.LEGAL_UNPROVED
    assert [d.code for d in checked.diagnostics] == ["PIE-S2337"]
    assert assessment.joins[0].condition is condition


@pytest.mark.parametrize("bounded", (False, True))
def test_set_is_not_a_single_match_proof_but_downstream_own_limit_is(
    tmp_path: Path, bounded: bool
) -> None:
    source = _source(replay=False)
    right = "combined"
    if bounded:
        source += (
            "table limited:\n    from combined\n    select:\n        id\n    limit 1\n"
        )
        right = "limited"
    source += f"query final:\n    from lhs\n    inner join {right} as r:\n        from lhs\n        on true\n    select:\n        id = lhs.id\n"
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    condition = completed.roots.join_conditions.entries[0]
    checked = with_project_single_match_requests(
        completed,
        (ProjectSingleMatchRequest(owner=condition.use.owner, use=condition.use),),
    )
    result = checked.single_matches.entries[0]
    if bounded:
        assert result.state is ProjectSingleMatchState.PROVED
        limit = _entry(completed, "limited").limit
        assert any(
            p.kind is ProjectSingleMatchProofKind.RIGHT_LIMIT
            and any(root is limit for root in p.roots)
            for p in result.proofs
        )
    else:
        assert (
            result.state is ProjectSingleMatchState.LEGAL_UNPROVED and not result.proofs
        )


@pytest.mark.parametrize("mode", tuple(CheckMode))
def test_real_explicit_check_text_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: CheckMode
) -> None:
    completed = _completed(tmp_path, f"mode {mode.value}\n" + _source())
    assert completed.ok, completed.diagnostics
    assert cli.main(["check", "--project", str(tmp_path)]) == 0
    capsys.readouterr()
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 0
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert not captured.err and document["ok"]
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


def test_legacy_and_combined_ir_do_not_drop_set_or_replay(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = _source()
    parsed = parse_source(source)
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    ir = build_ir(parsed.ast, semantic.model)
    assert ir.ir is None and any(d.code == "PIE-I1000" for d in ir.diagnostics)
    completed = _completed(tmp_path, source)
    assert completed.ok
    assert not completed.effective_outputs.current_regions
    with pytest.raises(ValueError, match="Set operations"):
        build_project_query_block_ir(completed)
    assert cli.main(["explain", "--project", str(tmp_path), "--format", "json"]) == 2
    capsys.readouterr()
    assert (
        cli.main(["emit-sql", str(tmp_path / "main.pietto"), "--dialect", "postgres"])
        == 1
    )
    assert "SELECT" not in capsys.readouterr().out


def test_foreign_operand_and_field_authority_cannot_graft(tmp_path: Path) -> None:
    local = _completed(tmp_path / "local", _source(replay=False))
    foreign = _completed(tmp_path / "foreign", _source(replay=False))
    entry, other = _entry(local), _entry(foreign)
    assert isinstance(entry, ProjectCompletedSetOutput) and isinstance(
        other, ProjectCompletedSetOutput
    )
    first, second = entry.root.uses
    for changes in (
        {"resolution": second.resolution},
        {"dependency": second.dependency},
        {"authority": other.root.uses[0].authority},
    ):
        with pytest.raises(ValueError):
            replace(first, **changes)
    with pytest.raises(ValueError):
        replace(entry.root, uses=(first, first))
    with pytest.raises(ValueError):
        replace(entry.fields[0], source=other.root.columns[0])
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(entry, fields=other.fields)
    with pytest.raises(ValueError):
        replace(
            local.effective_outputs,
            entries=tuple(
                other if e is entry else e for e in local.effective_outputs.entries
            ),
        )
    assert isinstance(entry.owner.definition, SetRelationDef)


def test_scope_cannot_claim_current_owner_is_already_available(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source(replay=False))
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    with pytest.raises(ValueError):
        scope = replace(
            entry.root.scope, available=(*entry.root.scope.available, entry)
        )
        uses = tuple(replace(use, scope=scope) for use in entry.root.uses)
        forged = ProjectCompletedSetOutput(
            root=replace(entry.root, scope=scope, uses=uses)
        )
        replace(
            completed.effective_outputs,
            entries=tuple(
                forged if e is entry else e for e in completed.effective_outputs.entries
            ),
        )


def test_foreign_unused_scope_entry_is_still_a_graft(tmp_path: Path) -> None:
    local = _completed(tmp_path / "local", _source(replay=False))
    foreign = _completed(tmp_path / "foreign", _source(replay=False))
    entry = _entry(local)
    assert isinstance(entry, ProjectCompletedSetOutput)
    with pytest.raises(ValueError):
        replace(
            entry.root.scope,
            available=(
                *entry.root.scope.available,
                foreign.effective_outputs.entries[0],
            ),
        )


def test_duplicate_set_owner_is_not_published_as_concrete(tmp_path: Path) -> None:
    source = _source(replay=False)
    source += "table combined:\n    union all:\n        from lhs\n        from rhs\n"
    completed = _completed(tmp_path, source)
    assert not completed.ok
    assert not any(
        isinstance(e, ProjectCompletedSetOutput)
        for e in completed.effective_outputs.entries
    )
    assert any(d.code == "PIE-S2001" for d in completed.diagnostics)


def test_foreign_type_root_cannot_certify_computed_input(tmp_path: Path) -> None:
    source = _source(replay=False)
    before, after = source.split("table combined:", 1)
    source = (
        before
        + "table computed:\n    from lhs\n    select:\n        value = 1\n"
        + "table combined:"
        + after.replace("from lhs", "from computed").replace(
            "from rhs", "from computed"
        )
    )
    local = _completed(tmp_path / "local", source)
    foreign = _completed(tmp_path / "foreign", source)
    entry = _entry(local)
    assert isinstance(entry, ProjectCompletedSetOutput)
    evidence = entry.root.uses[0].fields[0]
    foreign_types = (
        foreign.completion.plan.attribution._authority.type_source_resolutions
    )
    with pytest.raises(ValueError):
        ProjectRowEquivalenceField(selected=evidence.selected, types=foreign_types)


def test_except_right_is_membership_dependency_not_value_lineage(
    tmp_path: Path,
) -> None:
    completed = _completed(tmp_path, _source("except", "all", replay=False))
    entry = _entry(completed)
    assert isinstance(entry, ProjectCompletedSetOutput)
    column = entry.fields[0].source
    assert column.value_sources == ((entry.root.uses[0], column.inputs[0]),)
    assert column.membership_sources == tuple(
        zip(entry.root.uses, column.inputs, strict=True)
    )
    assert len(entry.dependencies) == 2


def test_failed_set_keeps_exact_owner_held_availability_cause(tmp_path: Path) -> None:
    completed = _completed(tmp_path, _source(quantifier="", replay=False))
    terminal = next(
        e
        for e in completed.effective_outputs.entries
        if e.owner.definition.name == "combined"
    )
    assert isinstance(terminal, ProjectEffectiveOutputCompletionTerminal)
    base = terminal.base_entry
    assert isinstance(base, ProjectEffectiveOutputTerminal)
    original = base.fragment.semantic_facts.helper_diagnostics
    assert original and all(d.code == "PIE-S2334" for d in original)
    assert all(any(actual is d for actual in completed.diagnostics) for d in original)
