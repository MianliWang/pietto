"""FROM and JOIN dependency cycles remain typed, complete compiler failures."""

from __future__ import annotations

import json
from copy import copy
from dataclasses import replace
from pathlib import Path

import pytest

from pietto import cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    _build_phase62_verification,
    build_project_completed_semantic_result,
)
from pietto._project.project_completion import (
    ProjectCompletionTopology,
    ProjectEffectiveOutputTerminal,
    ProjectEffectiveOutputTerminalReason,
    build_project_completion,
)
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockTerminal,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_query_block_ir_inspection import (
    build_project_query_block_ir_inspection,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    evaluate_project_query_block_ir_document,
)
from test_phase63_slice13_completed_project_semantic_result_public_check_boundaries import (
    POSITIVE_SOURCE,
)


BASE = """shape Row:
    id: Int not null
source rows: Row is postgres.table("rows")
"""


def _query(name: str, source: str = "rows", joins: tuple[str, ...] = ()) -> str:
    result = f"query {name}:\n    from {source}\n"
    for position, target in enumerate(joins):
        result += f"    inner join {target} as b{position}:\n        from {source}\n"
    return result + "    select:\n        id\n"


def _project(root: Path, source: str):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(BASE + source, encoding="utf-8")
    parsed = check_project_parse_only(root)
    assert parsed.ok
    return build_empty_project_semantic_result(parsed)


CYCLES = (
    _query("a", "a"),
    _query("a", "b") + _query("b", "a"),
    _query("a", joins=("a",)),
    _query("a", joins=("b",)) + _query("b", joins=("a",)),
    _query("a", "b") + _query("b", joins=("a",)),
)


@pytest.mark.parametrize("source", CYCLES)
def test_cycles_are_diagnostic_failures_not_exceptions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    semantic = _project(tmp_path, source)
    result = build_project_completed_semantic_result(semantic)
    assert not result.ok
    assert any(d.code == "PIE-S2302" for d in result.diagnostics)
    assert not any(d.code == "PIE-S2333" for d in result.diagnostics)
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    assert not document["ok"]
    assert document["schema_version"] == 2
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
    assert captured.err == ""


def test_acyclic_control_keeps_completed_success(tmp_path: Path) -> None:
    semantic = _project(tmp_path, _query("a") + _query("b", "a"))
    assert not semantic.ok
    result = build_project_completed_semantic_result(semantic)
    assert result.ok and not result.diagnostics


def _names(owners):
    return tuple(owner.identity.declared_name for owner in owners)


@pytest.mark.parametrize(
    ("source", "components", "blocked"),
    (
        (CYCLES[0], (("a",),), ("a",)),
        (CYCLES[1], (("a", "b"),), ("a", "b")),
        (CYCLES[2], (("a",),), ("a",)),
        (CYCLES[3], (("a", "b"),), ("a", "b")),
        (CYCLES[4], (("a", "b"),), ("a", "b")),
        (
            CYCLES[3] + _query("down", "a") + _query("later", "down"),
            (("a", "b"),),
            ("a", "b", "down", "later"),
        ),
        (
            CYCLES[1]
            + _query("c", joins=("c",))
            + _query("down", "a", ("c",))
            + _query("good")
            + _query("final", "good"),
            (("a", "b"), ("c",)),
            ("a", "b", "c", "down"),
        ),
        (
            _query("a", joins=("b", "c")) + _query("b", "a") + _query("c", "a"),
            (("a", "b", "c"),),
            ("a", "b", "c"),
        ),
    ),
)
def test_component_causes_and_all_downstream_observers_close(
    tmp_path: Path,
    source: str,
    components: tuple[tuple[str, ...], ...],
    blocked: tuple[str, ...],
) -> None:
    semantic = _project(tmp_path, source)
    # Exercise the direct completion boundary independently of completed roots.
    direct = build_project_completion(_build_phase62_verification(semantic))
    assert (
        tuple(_names(cycle.members) for cycle in direct.topology.cycles) == components
    )
    result = build_project_completed_semantic_result(semantic)
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    assert not result.ok
    base = result.completion
    topology = base.topology
    assert _names(topology.blocked_owners) == blocked
    assert tuple(_names(cycle.members) for cycle in topology.cycles) == components
    assert _names(base.entries[i].owner for i in range(len(base.entries))) == _names(
        base.owners
    )
    assert set(_names(base.schedule)).isdisjoint(blocked)
    assert len(base.schedule) + len(blocked) == len(base.owners)
    for cycle in topology.cycles:
        members = {id(owner) for owner in cycle.members}
        assert cycle.dependencies == tuple(
            edge
            for edge in base.dependencies
            if id(edge.consumer) in members and id(edge.target) in members
        )
        assert cycle.witness
        for left, right in zip(
            cycle.witness, (*cycle.witness[1:], cycle.witness[0]), strict=True
        ):
            assert left.target is right.consumer
            assert left in cycle.dependencies
        assert all(d.code == "PIE-S2302" for d in cycle.diagnostics)
        if not semantic.diagnostics:
            # Newly detected JOIN/mixed cycles locate a real closing use.
            closing = cycle.witness[-1].evidence
            site = (
                closing.reference.from_clause
                if isinstance(closing, ProjectResolvedModuleRelationReference)
                else closing.site
            )
            assert cycle.diagnostics[0].location.line == site.span.line
            assert cycle.diagnostics[0].location.column == site.span.column
            assert cycle.diagnostics[0].location.path == site.span.path
    for entry, effective in zip(
        base.entries, result.effective_outputs.entries, strict=True
    ):
        if entry.owner.identity.declared_name in blocked:
            assert type(entry) is ProjectEffectiveOutputTerminal
            assert entry is effective and entry.output is None
            assert entry.cycle_blocker is not None
            assert entry.cycle_blocker.topology is topology
            assert entry.reason is (
                ProjectEffectiveOutputTerminalReason.DEPENDENCY_CYCLE
                if any(entry.owner in c.members for c in topology.cycles)
                else ProjectEffectiveOutputTerminalReason.UPSTREAM_DEPENDENCY_CYCLE
            )
            assert not entry.pending_entries
        elif entry.owner.identity.declared_name in {"rows", "good", "final"}:
            assert not isinstance(effective, ProjectEffectiveOutputTerminal)
    # Two independent components must both remain causes of a common dependent.
    if len(components) == 2:
        dependent = next(
            entry
            for entry in base.entries
            if entry.owner.identity.declared_name == "down"
        )
        assert isinstance(dependent, ProjectEffectiveOutputTerminal)
        assert dependent.cycle_blocker is not None
        assert dependent.cycle_blocker.cycles == topology.cycles
    for original in semantic.diagnostics:
        assert any(d is original for d in result.diagnostics)
    assert not any(d.code == "PIE-S2333" for d in result.diagnostics)
    snapshot = build_project_query_block_ir(result)
    checked = verify_project_query_block_ir(snapshot)
    assert checked.status is ProjectIRQueryBlockVerificationStatus.VERIFIED, (
        checked.issues
    )
    assert not result.ok  # Verified terminal structure is not semantic success.
    for entry in snapshot.entries:
        if entry.owner.identity.declared_name in blocked:
            assert type(entry) is ProjectIRQueryBlockTerminal
            assert entry.output is None and entry.result_properties is None
            assert entry.starting_allocation is entry.ending_allocation
            assert entry.blocker is entry.semantic_entry
    observed = build_project_query_block_ir_inspection(
        build_project_query_block_ir_analysis_bundle(checked)
    )
    assert observed.inspection.project_completion is base
    assert observed.inspection.dependencies is base.dependencies
    assert (
        evaluate_project_query_block_ir_document(observed.document).canonical_bytes
        == observed.canonical_bytes
    )


def test_diamond_and_repeated_target_uses_are_not_cycles(tmp_path: Path) -> None:
    source = (
        _query("left") + _query("right") + _query("diamond", "left", ("right", "right"))
    )
    result = build_project_completed_semantic_result(_project(tmp_path, source))
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    topology = result.completion.topology
    assert not topology.cycles and not topology.blocked_owners
    assert _names(topology.schedule) == ("rows", "left", "right", "diamond")
    uses = tuple(
        edge
        for edge in topology.dependencies
        if edge.consumer.identity.declared_name == "diamond"
    )
    assert _names(edge.target for edge in uses) == ("left", "right", "right")
    assert tuple(edge.dependency_ordinal for edge in uses) == (0, 1, 2)
    assert not result.ok
    assert tuple(d.code for d in result.diagnostics) == ("PIE-S2333",)


def test_existing_joined_and_replay_controls_remain_completed(tmp_path: Path) -> None:
    result = build_project_completed_semantic_result(
        _project(tmp_path, POSITIVE_SOURCE)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    assert result.ok and not result.diagnostics
    assert not result.completion.topology.blocked_owners
    assert _names(result.completion.schedule) == _names(
        result.completion.topology.schedule
    )


def _unsafe(value, **changes):
    changed = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(changed, name, replacement)
    return changed


def test_foreign_edges_duplicate_owners_and_forged_topology_are_rejected(
    tmp_path: Path,
) -> None:
    source = CYCLES[3] + _query("good")
    result = build_project_completed_semantic_result(_project(tmp_path / "one", source))
    foreign = build_project_completed_semantic_result(
        _project(tmp_path / "two", source)
    )
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    assert isinstance(foreign, ProjectConcreteCompletedSemanticResult)
    completion = result.completion
    topology = completion.topology
    with pytest.raises(ValueError, match="topology authority"):
        replace(completion, topology=foreign.completion.topology)
    with pytest.raises(ValueError, match="canonical fragment order"):
        replace(completion, owners=(*completion.owners, completion.owners[0]))
    corruptions = (
        _unsafe(
            topology,
            dependencies=(
                foreign.completion.dependencies[0],
                *topology.dependencies[1:],
            ),
        ),
        _unsafe(topology, dependencies=topology.dependencies[:-1]),
        _unsafe(topology, schedule=(*topology.schedule, topology.blocked_owners[0])),
        _unsafe(topology, cycles=()),
        _unsafe(
            topology,
            cycles=(
                _unsafe(topology.cycles[0], members=topology.cycles[0].members[:-1]),
            ),
        ),
    )
    for corrupted in corruptions:
        with pytest.raises(ValueError):
            corrupted.validate()
        snapshot = build_project_query_block_ir(result)
        bad_completion = _unsafe(completion, topology=corrupted)
        bad_result = _unsafe(result, completion=bad_completion)
        bad_snapshot = _unsafe(snapshot, completed=bad_result)
        assert (
            verify_project_query_block_ir(bad_snapshot).status
            is ProjectIRQueryBlockVerificationStatus.INVALID
        )
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(topology, schedule=topology.schedule)
    assert isinstance(topology, ProjectCompletionTopology)


def test_diagnostic_identity_and_text_failure_are_preserved(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    semantic = _project(
        tmp_path,
        CYCLES[1]
        + _query("down", "a")
        + _query("bad").replace("        id", "        missing"),
    )
    result = build_project_completed_semantic_result(semantic)
    assert isinstance(result, ProjectConcreteCompletedSemanticResult)
    original = next(d for d in semantic.diagnostics if d.code == "PIE-S2302")
    assert result.completion.topology.cycles[0].diagnostics[0] is original
    assert sum(d is original for d in result.diagnostics) == 1
    equal_errors = tuple(d for d in result.diagnostics if d.code == "PIE-S2102")
    assert len(equal_errors) == 2
    assert equal_errors[0] == equal_errors[1]
    assert equal_errors[0] is not equal_errors[1]
    assert cli.main(["check", "--project", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2302" in captured.err and "Traceback" not in captured.err


def test_filesystem_creation_order_does_not_change_cycle_observation(
    tmp_path: Path,
) -> None:
    files = {"a.pietto": CYCLES[3] + _query("down", "a"), "z.pietto": _query("valid")}
    observations = []
    for index, items in enumerate(
        (tuple(files.items()), tuple(reversed(tuple(files.items()))))
    ):
        root = tmp_path / str(index)
        _project(root, "")
        for name, source in items:
            (root / name).write_text(BASE + source, encoding="utf-8")
        semantic = build_empty_project_semantic_result(check_project_parse_only(root))
        result = build_project_completed_semantic_result(semantic)
        assert isinstance(result, ProjectConcreteCompletedSemanticResult)
        snapshot = build_project_query_block_ir(result)
        product = build_project_query_block_ir_inspection(
            build_project_query_block_ir_analysis_bundle(
                verify_project_query_block_ir(snapshot)
            )
        )
        observations.append(
            (
                product.canonical_bytes,
                tuple((d.code, d.message, d.location) for d in result.diagnostics),
            )
        )
    assert observations[0] == observations[1]
